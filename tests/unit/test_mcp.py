from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from datetime import UTC, datetime
from io import BytesIO
import json
import sqlite3
from uuid import UUID, uuid4

import pytest
from psycopg.errors import CheckViolation

import alicebot_api.mcp_server as mcp_server
import alicebot_api.mcp_tools as mcp_tools_module
import alicebot_api.vnext_retrieval as vnext_retrieval_module
from alicebot_api.mcp_tools import MCPRuntimeContext, MCPToolError, MCPToolNotFoundError, call_mcp_tool, list_mcp_tools
from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.vnext_embeddings import (
    EMBEDDINGS_API_KEY_ENV,
    EMBEDDINGS_BASE_URL_ENV,
    EMBEDDINGS_MODEL_ENV,
)
from alicebot_api.vnext_project_scope import memory_project_scope
from alicebot_api.vnext_retrieval import VECTOR_STAGE_DISABLED_NO_PROVIDER, VECTOR_STAGE_ENABLED


CORE_TOOL_NAMES = [
    "alice_capture",
    "alice_memory_commit",
    "alice_recall",
    "alice_resume",
    "alice_context_pack",
    "alice_open_loops",
    "alice_recent_decisions",
    "alice_memory_review",
    "alice_memory_correct",
    "alice_memory_manage",
    "alice_explain",
]

_DESCRIPTION_JARGON = ("continuity object", "bridge policy", "posture", "vnext", "deterministic")

_INVALID_CONFIDENCE_CASES = [
    pytest.param(-0.1, r"between 0 and 1", id="below-minimum"),
    pytest.param(1.1, r"between 0 and 1", id="above-maximum"),
    pytest.param(1.5, r"between 0 and 1", id="far-above-maximum"),
    pytest.param(True, r"type number", id="true-is-not-a-number"),
    pytest.param(False, r"type number", id="false-is-not-a-number"),
    pytest.param(float("nan"), r"type number", id="nan-is-not-finite"),
    pytest.param(float("inf"), r"type number", id="positive-infinity-is-not-finite"),
    pytest.param(float("-inf"), r"type number", id="negative-infinity-is-not-finite"),
]


@pytest.fixture
def core_surface(monkeypatch) -> None:
    monkeypatch.delenv(mcp_tools_module.MCP_LEGACY_TOOLS_ENV, raising=False)


@pytest.fixture
def legacy_tools_enabled(monkeypatch) -> None:
    monkeypatch.setenv(mcp_tools_module.MCP_LEGACY_TOOLS_ENV, "1")


@pytest.fixture
def no_embedding_provider(monkeypatch) -> None:
    for env_name in (EMBEDDINGS_BASE_URL_ENV, EMBEDDINGS_MODEL_ENV, EMBEDDINGS_API_KEY_ENV):
        monkeypatch.delenv(env_name, raising=False)


def test_default_mcp_tool_surface_is_exactly_the_eleven_core_tools(core_surface) -> None:
    tools = list_mcp_tools()
    assert [tool["name"] for tool in tools] == CORE_TOOL_NAMES

    for tool in tools:
        assert isinstance(tool["inputSchema"], dict)
        assert tool["inputSchema"].get("type") == "object"
        assert tool["inputSchema"].get("additionalProperties") is False


def test_core_tool_descriptions_are_plain_language(core_surface) -> None:
    for tool in list_mcp_tools():
        description = tool["description"]
        assert isinstance(description, str) and description.strip() != ""
        lowered = description.casefold()
        for marker in _DESCRIPTION_JARGON:
            assert marker not in lowered, f"{tool['name']} description contains jargon: {marker}"


def test_every_core_tool_property_has_a_description(core_surface) -> None:
    for tool in list_mcp_tools():
        properties = tool["inputSchema"]["properties"]
        assert isinstance(properties, dict) and properties
        for property_name, property_schema in properties.items():
            assert isinstance(property_schema, dict), f"{tool['name']}.{property_name}"
            description = property_schema.get("description")
            assert isinstance(description, str) and description.strip() != "", (
                f"{tool['name']}.{property_name} is missing a description"
            )


def test_legacy_flag_exposes_the_long_tail_after_the_core_tools(legacy_tools_enabled) -> None:
    tools = list_mcp_tools()
    names = [tool["name"] for tool in tools]

    assert names[: len(CORE_TOOL_NAMES)] == CORE_TOOL_NAMES
    assert len(names) == len(set(names)) == 76
    for legacy_name in (
        "alice_brief",
        "alice_recall_debug",
        "alice_resume_debug",
        "alice_review_queue",
        "alice_review_apply",
        "alice_vnext_context_pack",
        "alice_vnext_commit_memory",
        "alice_vnext_ingest_agent_output",
        "alice_vnext_scheduler_resume",
    ):
        assert legacy_name in names


def test_every_tool_definition_has_a_handler_and_vice_versa() -> None:
    defined = set(mcp_tools_module._CORE_TOOL_NAMES) | set(mcp_tools_module._LEGACY_TOOL_NAMES)
    assert defined == set(mcp_tools_module._TOOL_HANDLERS)
    assert not (set(mcp_tools_module._CORE_TOOL_NAMES) & set(mcp_tools_module._LEGACY_TOOL_NAMES))


def test_calling_a_legacy_tool_without_the_flag_mentions_the_flag(core_surface) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    with pytest.raises(MCPToolNotFoundError, match="ALICE_MCP_LEGACY_TOOLS"):
        call_mcp_tool(context, name="alice_brief", arguments={})


def test_call_mcp_tool_rejects_unknown_tool() -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    with pytest.raises(MCPToolNotFoundError, match="unknown tool"):
        call_mcp_tool(context, name="alice_nonexistent", arguments={})


def test_call_mcp_tool_enforces_closed_advertised_input_schema(core_surface) -> None:
    with pytest.raises(MCPToolError, match="does not accept additional properties: surprise"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_recall",
            arguments={"query": "schema contract", "surprise": True},
        )


def test_every_nested_mcp_object_schema_is_closed(legacy_tools_enabled) -> None:
    def walk(schema: object, *, path: str) -> None:
        if not isinstance(schema, dict):
            return
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False, path
            properties = schema.get("properties", {})
            assert isinstance(properties, dict), path
            for key, child in properties.items():
                walk(child, path=f"{path}.{key}")
        items = schema.get("items")
        if items is not None:
            walk(items, path=f"{path}[]")

    for tool in list_mcp_tools():
        walk(tool["inputSchema"], path=str(tool["name"]))


def test_nested_mcp_schemas_reject_unknown_candidate_and_provenance_fields(
    legacy_tools_enabled,
) -> None:
    candidate = {
        "candidate_id": "candidate-1",
        "candidate_type": "decision",
        "object_type": "Decision",
        "normalized_text": "Ship only after review.",
        "confidence": 0.95,
        "trust_class": "human_curated",
        "evidence_snippet": "Ship only after review.",
        "explicit": True,
        "source_role": "user",
        "admission_reason": "explicit_prefix_decision",
        "proposed_action": "auto_save_candidate",
        "surprise": True,
    }
    with pytest.raises(MCPToolError, match=r"arguments\.candidates\[0\].*surprise"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_commit_captures",
            arguments={"mode": "assist", "candidates": [candidate]},
        )

    with pytest.raises(MCPToolError, match=r"arguments\.provenance.*surprise"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "action": "edit-and-approve",
                "review_item_id": str(uuid4()),
                "provenance": {"source_id": str(uuid4()), "surprise": True},
            },
        )


def test_nested_mcp_schemas_enforce_candidate_and_provenance_requirements(
    legacy_tools_enabled,
) -> None:
    with pytest.raises(MCPToolError, match=r"arguments\.candidates\[0\].*candidate_id"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_commit_captures",
            arguments={
                "candidates": [
                    {
                        "candidate_type": "decision",
                        "object_type": "Decision",
                        "normalized_text": "Ship only after review.",
                        "confidence": 0.95,
                        "trust_class": "human_curated",
                        "evidence_snippet": "Ship only after review.",
                        "explicit": True,
                        "source_role": "user",
                        "admission_reason": "explicit_prefix_decision",
                        "proposed_action": "auto_save_candidate",
                    }
                ]
            },
        )

    with pytest.raises(MCPToolError, match=r"arguments\.provenance.*source_id"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "action": "edit-and-approve",
                "review_item_id": str(uuid4()),
                "provenance": {"evidence_role": "supports"},
            },
        )


def _valid_capture_candidate() -> dict[str, object]:
    return {
        "candidate_id": "candidate-valid",
        "candidate_type": "no_op",
        "object_type": None,
        "normalized_text": "",
        "confidence": 0.0,
        "trust_class": "deterministic",
        "evidence_snippet": "",
        "explicit": False,
        "source_role": "combined",
        "admission_reason": "no_actionable_candidate",
        "proposed_action": "no_op",
    }


@pytest.mark.parametrize(
    "field, invalid_value, error_pattern",
    [
        ("candidate_id", 42, r"candidate_id.*type string"),
        ("candidate_type", "not-real", r"candidate_type.*must be one of"),
        ("object_type", 7, r"object_type.*type string or null"),
        ("normalized_text", False, r"normalized_text.*type string"),
        ("confidence", "0.95", r"confidence.*type number"),
        ("confidence", 1.1, r"confidence.*between 0 and 1"),
        ("trust_class", "not-real", r"trust_class.*must be one of"),
        ("evidence_snippet", 7, r"evidence_snippet.*type string"),
        ("explicit", 1, r"explicit.*type boolean"),
        ("source_role", 7, r"source_role.*type string"),
        ("admission_reason", False, r"admission_reason.*type string"),
        ("proposed_action", "not-real", r"proposed_action.*must be one of"),
    ],
)
def test_capture_candidate_schema_rejects_invalid_nested_values_before_handler(
    monkeypatch,
    legacy_tools_enabled,
    field: str,
    invalid_value: object,
    error_pattern: str,
) -> None:
    handler_calls = 0

    def should_not_run(_context, _arguments):
        nonlocal handler_calls
        handler_calls += 1
        raise AssertionError("schema-invalid candidate must not reach the handler")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_commit_captures", should_not_run)
    candidate = _valid_capture_candidate()
    candidate[field] = invalid_value
    before = deepcopy(candidate)

    with pytest.raises(MCPToolError, match=error_pattern):
        call_mcp_tool(
            _mcp_context(),
            name="alice_commit_captures",
            arguments={"mode": "assist", "candidates": [candidate]},
        )

    assert candidate == before
    assert handler_calls == 0


@pytest.mark.parametrize(
    "body, error_pattern",
    [
        ([], r"arguments\.body.*body must have type object"),
        ({"text": 7}, r"body\.text.*text must have type string"),
        ({"explicit_signal": 7}, r"explicit_signal.*type string or null"),
        ({}, r"requires at least 1 properties at arguments\.body"),
    ],
)
def test_correction_body_schema_rejects_values_without_mutating_candidate(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    body: object,
    error_pattern: str,
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    before = deepcopy(store.get_memory(memory_id))

    with pytest.raises(MCPToolError, match=error_pattern):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "review_item_id": memory_id,
                "action": "edit-and-approve",
                "body": body,
            },
        )

    assert store.get_memory(memory_id) == before
    assert store.revisions == []


@pytest.mark.parametrize(
    "provenance_patch, error_pattern",
    [
        ({"source_id": 42}, r"source_id.*type string"),
        ({"source_id": "not-a-uuid"}, r"source_id.*UUID string"),
        (
            {"source_id": "11111111-1111-4111-8111-111111111111", "source_chunk_id": "bad"},
            r"source_chunk_id.*UUID string",
        ),
        (
            {"source_id": "11111111-1111-4111-8111-111111111111", "evidence_role": "bad"},
            r"evidence_role.*must be one of",
        ),
        (
            {"source_id": "11111111-1111-4111-8111-111111111111", "confidence": True},
            r"confidence.*type number",
        ),
        (
            {"source_id": "11111111-1111-4111-8111-111111111111", "confidence": -0.1},
            r"confidence.*between 0 and 1",
        ),
        (
            {"source_id": "11111111-1111-4111-8111-111111111111", "quote": []},
            r"quote.*type string",
        ),
    ],
)
def test_review_provenance_schema_rejects_values_without_mutation(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    provenance_patch: dict[str, object],
    error_pattern: str,
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    before = deepcopy(store.get_memory(memory_id))

    with pytest.raises(MCPToolError, match=error_pattern):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "review_item_id": memory_id,
                "action": "edit-and-approve",
                "provenance": provenance_patch,
            },
        )

    assert store.get_memory(memory_id) == before
    assert store.revisions == []


def test_requested_review_confidence_schemas_advertise_closed_unit_interval(
    legacy_tools_enabled,
) -> None:
    core_properties = mcp_tools_module._TOOL_DEFINITIONS_BY_NAME["alice_memory_correct"]["inputSchema"]["properties"]
    legacy_properties = mcp_tools_module._TOOL_DEFINITIONS_BY_NAME["alice_review_apply"]["inputSchema"]["properties"]

    assert core_properties["confidence"] == {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
        "description": "For edit-and-approve: corrected confidence, between 0 and 1.",
    }
    assert core_properties["replacement_confidence"] == {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
        "description": ("For supersede-existing: confidence of the replacement memory, between 0 and 1."),
    }
    assert legacy_properties["confidence"] == {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
    }
    assert legacy_properties["replacement_confidence"] == {
        "type": "number",
        "minimum": 0.0,
        "maximum": 1.0,
    }


@pytest.mark.parametrize("invalid_confidence,error_detail", _INVALID_CONFIDENCE_CASES)
def test_core_review_confidence_bounds_reject_before_mutation(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    invalid_confidence: object,
    error_detail: str,
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    before = deepcopy(store.get_memory(memory_id))

    with pytest.raises(MCPToolError, match=rf"confidence.*{error_detail}"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "review_item_id": memory_id,
                "action": "edit-and-approve",
                "confidence": invalid_confidence,
            },
        )

    assert store.get_memory(memory_id) == before
    assert store.revisions == []
    assert store.list_provenance_links(target_type="memory", target_id=memory_id) == []


@pytest.mark.parametrize("boundary_confidence", [0.0, 1.0])
def test_core_review_confidence_boundary_values_remain_accepted(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    boundary_confidence: float,
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)

    result = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "edit-and-approve",
            "confidence": boundary_confidence,
        },
    )

    assert result["memory"]["status"] == "active"
    assert result["memory"]["confidence"] == boundary_confidence
    assert len(store.revisions) == 1
    assert store.list_provenance_links(target_type="memory", target_id=memory_id) == []


@pytest.mark.parametrize("invalid_confidence,error_detail", _INVALID_CONFIDENCE_CASES)
def test_core_replacement_confidence_bounds_reject_before_mutation(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    invalid_confidence: object,
    error_detail: str,
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    before_memory = deepcopy(store.get_memory(memory_id))
    before_memories = deepcopy(store.memories)
    before_events = deepcopy(store.events)

    with pytest.raises(MCPToolError, match=rf"replacement_confidence.*{error_detail}"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "review_item_id": memory_id,
                "action": "supersede-existing",
                "replacement_title": "Replacement",
                "replacement_confidence": invalid_confidence,
            },
        )

    assert store.get_memory(memory_id) == before_memory
    assert store.memories == before_memories
    assert store.events == before_events
    assert store.revisions == []
    assert store.list_provenance_links(target_type="memory", target_id=memory_id) == []


@pytest.mark.parametrize("boundary_confidence", [0.0, 1.0])
def test_core_replacement_confidence_boundary_values_remain_accepted(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    boundary_confidence: float,
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)

    result = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "supersede-existing",
            "replacement_title": "Replacement",
            "replacement_confidence": boundary_confidence,
        },
    )

    assert result["memory"]["status"] == "superseded"
    assert result["replacement_object"]["status"] == "active"
    assert result["replacement_object"]["confidence"] == boundary_confidence
    assert len(store.memories) == 2
    assert len(store.revisions) == 2


@pytest.mark.parametrize("invalid_confidence,error_detail", _INVALID_CONFIDENCE_CASES)
def test_legacy_confidence_bounds_reject_before_handler_or_mutation(
    monkeypatch,
    legacy_tools_enabled,
    invalid_confidence: object,
    error_detail: str,
) -> None:
    state = {"status": "needs_review", "confidence": 0.5}
    revisions: list[object] = []
    provenance: list[object] = []
    before = deepcopy(state)
    handler_calls = 0

    def should_not_run(_context, _arguments):
        nonlocal handler_calls
        handler_calls += 1
        state["status"] = "active"
        revisions.append("mutated")
        provenance.append("mutated")
        raise AssertionError("out-of-range confidence must not reach the handler")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_review_apply", should_not_run)
    with pytest.raises(MCPToolError, match=rf"confidence.*{error_detail}"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_review_apply",
            arguments={
                "review_item_id": str(uuid4()),
                "action": "edit-and-approve",
                "confidence": invalid_confidence,
            },
        )

    assert handler_calls == 0
    assert state == before
    assert revisions == []
    assert provenance == []


@pytest.mark.parametrize("boundary_confidence", [0.0, 1.0])
def test_legacy_confidence_boundary_values_remain_accepted(
    monkeypatch,
    legacy_tools_enabled,
    boundary_confidence: float,
) -> None:
    def validated(_context, arguments):
        return {"validated": True, "confidence": arguments["confidence"]}

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_review_apply", validated)
    result = call_mcp_tool(
        _mcp_context(),
        name="alice_review_apply",
        arguments={
            "review_item_id": str(uuid4()),
            "action": "edit-and-approve",
            "confidence": boundary_confidence,
        },
    )
    assert result == {"validated": True, "confidence": boundary_confidence}


@pytest.mark.parametrize("invalid_confidence,error_detail", _INVALID_CONFIDENCE_CASES)
def test_legacy_replacement_confidence_bounds_reject_before_handler_or_mutation(
    monkeypatch,
    legacy_tools_enabled,
    invalid_confidence: object,
    error_detail: str,
) -> None:
    state = {"status": "active", "confidence": 0.5}
    revisions: list[object] = []
    provenance: list[object] = []
    before = deepcopy(state)
    handler_calls = 0

    def should_not_run(_context, _arguments):
        nonlocal handler_calls
        handler_calls += 1
        state["status"] = "superseded"
        revisions.append("mutated")
        provenance.append("mutated")
        raise AssertionError("out-of-range confidence must not reach the handler")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_review_apply", should_not_run)
    with pytest.raises(MCPToolError, match=rf"replacement_confidence.*{error_detail}"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_review_apply",
            arguments={
                "review_item_id": str(uuid4()),
                "action": "supersede-existing",
                "replacement_title": "Replacement",
                "replacement_confidence": invalid_confidence,
            },
        )

    assert handler_calls == 0
    assert state == before
    assert revisions == []
    assert provenance == []


@pytest.mark.parametrize("boundary_confidence", [0.0, 1.0])
def test_legacy_replacement_confidence_boundary_values_remain_accepted(
    monkeypatch,
    legacy_tools_enabled,
    boundary_confidence: float,
) -> None:
    def validated(_context, arguments):
        return {"validated": True, "replacement_confidence": arguments["replacement_confidence"]}

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_review_apply", validated)
    result = call_mcp_tool(
        _mcp_context(),
        name="alice_review_apply",
        arguments={
            "review_item_id": str(uuid4()),
            "action": "supersede-existing",
            "replacement_title": "Replacement",
            "replacement_confidence": boundary_confidence,
        },
    )
    assert result == {"validated": True, "replacement_confidence": boundary_confidence}


@pytest.mark.parametrize(
    "tool_name, arguments, error_pattern",
    [
        ("alice_recall", {"query": "schema", "projects": "Apollo"}, r"projects.*type array"),
        ("alice_recall", {"query": "schema", "projects": [7]}, r"projects\[0\].*type string"),
        ("alice_recall", {"query": "schema", "limit": True}, r"limit.*type integer"),
        ("alice_recall", {"query": "schema", "limit": 0}, r"limit.*between 1 and"),
        (
            "alice_context_pack",
            {"query": "schema", "projects": [f"project-{index}" for index in range(51)]},
            r"projects.*at most 50 items",
        ),
        (
            "alice_recall",
            {"query": "schema", "thread_id": "not-a-uuid"},
            r"thread_id.*UUID string",
        ),
        (
            "alice_recall",
            {"query": "schema", "since": "2026-07-13"},
            r"since.*RFC 3339 date-time",
        ),
        (
            "alice_recall",
            {"query": "schema", "until": "2026-02-30T00:00:00Z"},
            r"until.*valid RFC 3339 date-time",
        ),
        (
            "alice_context_pack",
            {"query": "schema", "time_window": "yesterday"},
            r"time_window.*match pattern",
        ),
        (
            "alice_memory_commit",
            {"title": "Schema", "canonical_text": "Schema", "domain": "not-real"},
            r"domain.*must be one of",
        ),
    ],
)
def test_advertised_schema_rejects_array_bound_format_pattern_and_enum_values(
    monkeypatch,
    core_surface,
    tool_name: str,
    arguments: dict[str, object],
    error_pattern: str,
) -> None:
    handler_calls = 0

    def should_not_run(_context, _arguments):
        nonlocal handler_calls
        handler_calls += 1
        raise AssertionError("schema-invalid call must not reach the handler")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, tool_name, should_not_run)
    with pytest.raises(MCPToolError, match=error_pattern):
        call_mcp_tool(_mcp_context(), name=tool_name, arguments=arguments)
    assert handler_calls == 0


@pytest.mark.parametrize(
    "tool_name,invalid_date",
    [
        pytest.param("alice_generate_daily_brief", "not-a-date", id="daily-malformed"),
        pytest.param("alice_generate_daily_brief", "2026-02-30", id="daily-impossible"),
        pytest.param("alice_generate_weekly_synthesis", "not-a-date", id="weekly-malformed"),
        pytest.param("alice_generate_weekly_synthesis", "2026-02-30", id="weekly-impossible"),
    ],
)
def test_generated_for_date_format_rejects_before_handler(
    monkeypatch,
    legacy_tools_enabled,
    tool_name: str,
    invalid_date: str,
) -> None:
    handler_calls = 0

    def should_not_run(_context, _arguments):
        nonlocal handler_calls
        handler_calls += 1
        raise AssertionError("invalid generated_for must not reach the handler")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, tool_name, should_not_run)
    with pytest.raises(MCPToolError, match=r"generated_for.*RFC 3339 full-date"):
        call_mcp_tool(
            _mcp_context(),
            name=tool_name,
            arguments={"generated_for": invalid_date},
        )
    assert handler_calls == 0


@pytest.mark.parametrize(
    "tool_name,valid_date",
    [
        pytest.param("alice_generate_daily_brief", "0001-01-01", id="daily-minimum"),
        pytest.param("alice_generate_daily_brief", "2024-02-29", id="daily-leap-day"),
        pytest.param("alice_generate_daily_brief", "2026-07-13", id="daily-ordinary"),
        pytest.param("alice_generate_daily_brief", "9999-12-31", id="daily-maximum"),
        pytest.param("alice_generate_weekly_synthesis", "0001-01-01", id="weekly-minimum"),
        pytest.param("alice_generate_weekly_synthesis", "2024-02-29", id="weekly-leap-day"),
        pytest.param("alice_generate_weekly_synthesis", "2026-07-13", id="weekly-ordinary"),
        pytest.param("alice_generate_weekly_synthesis", "9999-12-31", id="weekly-maximum"),
    ],
)
def test_generated_for_date_format_accepts_leap_and_boundary_dates(
    monkeypatch,
    legacy_tools_enabled,
    tool_name: str,
    valid_date: str,
) -> None:
    handler_calls = 0

    def validated(_context, arguments):
        nonlocal handler_calls
        handler_calls += 1
        return {"generated_for": arguments["generated_for"]}

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, tool_name, validated)
    assert call_mcp_tool(
        _mcp_context(),
        name=tool_name,
        arguments={"generated_for": valid_date},
    ) == {"generated_for": valid_date}
    assert handler_calls == 1


def test_advertised_schema_formats_are_known_and_unknown_formats_fail_closed(monkeypatch, legacy_tools_enabled) -> None:
    formats: set[str] = set()

    def collect(schema: object) -> None:
        if not isinstance(schema, dict):
            return
        schema_format = schema.get("format")
        if isinstance(schema_format, str):
            formats.add(schema_format)
        for child in schema.get("properties", {}).values():
            collect(child)
        collect(schema.get("items"))

    for definition in mcp_tools_module._TOOL_DEFINITIONS_BY_NAME.values():
        collect(definition["inputSchema"])
    assert formats == {"date", "date-time", "uuid"}

    generated_for_schema = mcp_tools_module._TOOL_DEFINITIONS_BY_NAME["alice_generate_daily_brief"]["inputSchema"][
        "properties"
    ]["generated_for"]
    monkeypatch.setitem(generated_for_schema, "format", "future-unsupported-format")
    handler_calls = 0

    def should_not_run(_context, _arguments):
        nonlocal handler_calls
        handler_calls += 1
        raise AssertionError("unsupported advertised formats must fail closed")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_generate_daily_brief", should_not_run)
    with pytest.raises(MCPToolError, match=r"unsupported advertised format"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_generate_daily_brief",
            arguments={"generated_for": "2026-07-13"},
        )
    assert handler_calls == 0


def test_schema_enforces_min_items_and_max_properties_before_handler(monkeypatch, core_surface) -> None:
    recall_schema = mcp_tools_module._TOOL_DEFINITIONS_BY_NAME["alice_recall"]["inputSchema"]
    projects_schema = recall_schema["properties"]["projects"]
    monkeypatch.setitem(projects_schema, "minItems", 1)
    with pytest.raises(MCPToolError, match=r"projects.*at least 1 items"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_recall",
            arguments={"query": "schema", "projects": []},
        )

    correction_schema = mcp_tools_module._TOOL_DEFINITIONS_BY_NAME["alice_memory_correct"]["inputSchema"]
    body_schema = correction_schema["properties"]["body"]
    monkeypatch.setitem(body_schema, "maxProperties", 1)
    with pytest.raises(MCPToolError, match=r"body.*at most 1 properties"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "review_item_id": str(uuid4()),
                "action": "edit-and-approve",
                "body": {"text": "valid", "body": "second"},
            },
        )


def test_schema_rejects_legacy_nested_array_item_types_before_handler(monkeypatch, legacy_tools_enabled) -> None:
    handler_calls = 0

    def should_not_run(_context, _arguments):
        nonlocal handler_calls
        handler_calls += 1
        raise AssertionError("schema-invalid provenance must not reach the handler")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_review_apply", should_not_run)
    with pytest.raises(MCPToolError, match=r"source_event_ids\[0\].*type string"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_review_apply",
            arguments={
                "review_item_id": str(uuid4()),
                "action": "edit-and-approve",
                "provenance": {"thread_id": str(uuid4()), "source_event_ids": [7]},
            },
        )
    assert handler_calls == 0


def test_schema_value_validation_preserves_valid_nested_calls(monkeypatch, legacy_tools_enabled) -> None:
    def validated(_context, arguments):
        return {"validated": True, "arguments": arguments}

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_commit_captures", validated)
    committed = call_mcp_tool(
        _mcp_context(),
        name="alice_commit_captures",
        arguments={"mode": "assist", "candidates": [_valid_capture_candidate()]},
    )
    assert committed["validated"] is True

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_recall", validated)
    recalled = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={
            "query": "schema",
            "thread_id": "11111111-1111-4111-8111-111111111111",
            "since": "2026-07-01T00:00:00Z",
            "projects": ["Apollo"],
            "limit": 5,
        },
    )
    assert recalled["validated"] is True

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_memory_correct", validated)
    corrected = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": "22222222-2222-4222-8222-222222222222",
            "action": "edit-and-approve",
            "body": {"text": "Reviewed text", "explicit_signal": None},
            "provenance": {
                "source_id": "33333333-3333-4333-8333-333333333333",
                "evidence_role": "supports",
                "confidence": 0.9,
            },
        },
    )
    assert corrected["validated"] is True


def test_call_mcp_tool_requires_object_arguments() -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    with pytest.raises(MCPToolError, match="tool arguments must be a JSON object"):
        call_mcp_tool(context, name="alice_recall", arguments=["not-a-json-object"])


def test_call_mcp_tool_converts_postgres_check_violation(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    def raise_check_violation(_context, _arguments):
        raise CheckViolation("memories_memory_type_check")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_recall", raise_check_violation)

    with pytest.raises(MCPToolError, match="persisted schema constraint"):
        call_mcp_tool(context, name="alice_recall", arguments={})


def test_call_mcp_tool_maps_sqlite_integrity_errors_by_constraint_kind(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    def _install_raiser(message: str) -> None:
        def raise_integrity_error(_context, _arguments):
            raise sqlite3.IntegrityError(message)

        monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_recall", raise_integrity_error)

    # CHECK violations keep the enum-vocabulary guidance.
    _install_raiser("CHECK constraint failed: memories.memory_type")
    with pytest.raises(MCPToolError, match="schema-backed enum values"):
        call_mcp_tool(context, name="alice_recall", arguments={})

    # FOREIGN KEY violations point at the missing referenced row, not enum vocabulary.
    _install_raiser("FOREIGN KEY constraint failed")
    with pytest.raises(MCPToolError, match="alice-memory init") as excinfo:
        call_mcp_tool(context, name="alice_recall", arguments={})
    assert "enum values" not in str(excinfo.value)

    # Anything else surfaces the SQLite message verbatim.
    _install_raiser("UNIQUE constraint failed: users.email")
    with pytest.raises(MCPToolError, match="UNIQUE constraint failed: users.email"):
        call_mcp_tool(context, name="alice_recall", arguments={})


class FakeVNextMCPStore:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.sources: list[dict[str, object]] = []
        self.chunks: list[dict[str, object]] = []
        self.memories: list[dict[str, object]] = []
        self.artifacts: dict[str, dict[str, object]] = {}
        self.open_loops: list[dict[str, object]] = []
        self.edges: dict[str, dict[str, object]] = {}
        self.workflows: dict[str, dict[str, object]] = {}
        self.runs: dict[str, dict[str, object]] = {}
        self.agent_identities: dict[str, dict[str, object]] = {}
        self.projects: dict[str, dict[str, object]] = {
            "project-1": {
                "id": "project-1",
                "name": "Alice vNext",
                "slug": "alice-vnext",
                "status": "active",
                "current_state": "Sprint 7 complete.",
                "domain": "project",
                "sensitivity": "private",
            }
        }
        self.revisions: list[dict[str, object]] = []
        self.beliefs: dict[str, dict[str, object]] = {
            "belief-1": {
                "id": "belief-1",
                "memory_id": "memory-belief-1",
                "claim": "Alice should auto-promote generated artifacts into memory.",
                "status": "active",
                "confidence": 0.8,
                "domain": "project",
                "sensitivity": "private",
                "memory_type": "belief",
            }
        }

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def upsert_agent_identity(self, identity: dict[str, object], **_kwargs) -> dict[str, object]:
        self.agent_identities[str(identity["agent_id"])] = identity
        return identity

    def create_artifact(self, artifact: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**artifact, "id": f"artifact-{len(self.artifacts) + 1}"}
        self.artifacts[str(row["id"])] = row
        return row

    def get_source_by_content_hash(self, content_hash: str) -> dict[str, object] | None:
        return next((source for source in self.sources if source.get("content_hash") == content_hash), None)

    def create_source(self, source: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**source, "id": f"source-{len(self.sources) + 1}"}
        self.sources.append(row)
        return row

    def create_source_chunk(self, chunk: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**chunk, "id": f"chunk-{len(self.chunks) + 1}"}
        self.chunks.append(row)
        return row

    def get_artifact(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def get_artifact_for_update(self, artifact_id: str) -> dict[str, object] | None:
        return self.artifacts.get(artifact_id)

    def update_artifact_status(self, *, artifact_id: str, status: str, **_kwargs) -> dict[str, object]:
        artifact = self.artifacts[artifact_id]
        artifact["status"] = status
        return artifact

    def create_memory(self, memory: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**memory, "id": f"memory-{len(self.memories) + 2}"}
        self.memories.append(row)
        return row

    def update_memory(self, *, memory_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        for memory in self.memories:
            if memory["id"] == memory_id:
                memory.update(patch)
                return memory
        raise AssertionError(memory_id)

    def get_memory(self, memory_id: str) -> dict[str, object] | None:
        return next((memory for memory in self.memories if memory["id"] == memory_id), None)

    def get_memory_for_update(self, memory_id: str) -> dict[str, object] | None:
        return self.get_memory(memory_id)

    def list_memories(self, *, status: str | None = None) -> list[dict[str, object]]:
        return [memory for memory in self.memories if status is None or memory.get("status") == status]

    def list_rollup_input_memories(
        self,
        *,
        domains: list[str] | None,
        sensitivity_allowed: list[str],
        excluded_candidate_kind: str,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [
            memory
            for memory in self.memories
            if memory.get("status") in {"active", "accepted"}
            and (not domains or memory.get("domain") in {*domains, "unknown"})
            and memory.get("sensitivity", "unknown") in sensitivity_allowed
            and not (
                isinstance(memory.get("metadata_json"), dict)
                and memory["metadata_json"].get("candidate_kind") == excluded_candidate_kind
            )
        ]
        rows.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("id"))), reverse=True)
        return [dict(row) for row in rows[:limit]]

    def list_pending_rollup_candidates(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def list_accepted_rollup_cards(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def append_revision(self, revision: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**revision, "id": f"revision-{len(self.revisions) + 1}"}
        self.revisions.append(row)
        return row

    def list_revisions(self, memory_id: str) -> list[dict[str, object]]:
        return [revision for revision in self.revisions if revision["memory_id"] == memory_id]

    def create_open_loop(self, loop: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**loop, "id": f"loop-{len(self.open_loops) + 1}", "status": loop.get("status", "open")}
        self.open_loops.append(row)
        return row

    def create_edge(self, edge: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**edge, "id": f"edge-{len(self.edges) + 1}"}
        self.edges[str(row["id"])] = row
        return row

    def update_edge_status(self, *, edge_id: str, status: str, **_kwargs) -> dict[str, object]:
        edge = self.edges[edge_id]
        metadata = edge.get("metadata_json")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.update({"status": status, "candidate": status != "accepted"})
        edge["metadata_json"] = metadata
        if status == "rejected":
            edge["valid_to"] = "now"
        return edge

    def search_memories(self, **_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": "memory-1",
                "memory_type": "semantic",
                "canonical_text": "Alice vNext MCP context packs preserve provenance.",
                "status": "active",
                "confidence": 0.9,
                "domain": "project",
                "project_id": "project-1",
                "sensitivity": "private",
                "first_seen_at": "2026-05-10T00:00:00Z",
                "last_seen_at": "2026-05-10T00:00:00Z",
            }
        ][: _kwargs.get("limit", 8)]

    def search_sources(self, **_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": "source-1",
                "source_type": "manual_text",
                "title": "Alice vNext MCP source",
                "content_hash": "sha256:abc",
                "captured_at": "2026-05-10T00:00:00Z",
                "domain": "project",
                "project_id": "project-1",
                "sensitivity": "private",
                "metadata_json": {
                    "raw_text": (
                        "TODO: validate MCP brief generation Owner: Samir\n"
                        "Alice should not auto-promote generated artifacts into memory."
                    )
                },
            }
        ][: _kwargs.get("limit", 8)]

    def list_open_loops(self, **_kwargs) -> list[dict[str, object]]:
        status = _kwargs.get("status", "open")
        project_id = _kwargs.get("project_id")
        return [
            row
            for row in self.open_loops
            if (status is None or row.get("status") == status)
            and (project_id is None or row.get("project_id") == project_id)
        ]

    def get_open_loop(self, loop_id: str) -> dict[str, object] | None:
        for loop in self.open_loops:
            if loop["id"] == loop_id:
                return loop
        return None

    def update_open_loop(self, *, loop_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        loop = self.get_open_loop(loop_id)
        if loop is None:
            raise AssertionError(loop_id)
        loop.update(patch)
        return loop

    def update_open_loop_status(
        self,
        *,
        loop_id: str,
        status: str,
        resolution_note: str | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        loop = self.update_open_loop(loop_id=loop_id, patch={"status": status})
        if resolution_note is not None:
            loop["resolution_note"] = resolution_note
        return loop

    def list_artifacts(self, **_kwargs) -> list[dict[str, object]]:
        return list(self.artifacts.values())[: _kwargs.get("limit", 4)]

    def get_project(self, project_id: str) -> dict[str, object] | None:
        return self.projects.get(project_id)

    def get_project_for_update(self, project_id: str) -> dict[str, object] | None:
        return self.get_project(project_id)

    def list_projects(self, **kwargs) -> list[dict[str, object]]:
        status = kwargs.get("status", "active")
        limit = kwargs.get("limit", 8)
        return [row for row in self.projects.values() if status is None or row.get("status") == status][:limit]

    def update_project(self, *, project_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        project = self.projects[project_id]
        project.update(patch)
        return project

    def list_edges(self, **kwargs) -> list[dict[str, object]]:
        from_id = kwargs.get("from_id")
        to_id = kwargs.get("to_id")
        return [
            edge
            for edge in self.edges.values()
            if (from_id is None or edge.get("from_id") == from_id)
            and (to_id is None or edge.get("to_id") == to_id)
            and edge.get("valid_to") is None
        ]

    def list_beliefs(self, **kwargs) -> list[dict[str, object]]:
        status = kwargs.get("status", "active")
        return [row for row in self.beliefs.values() if status is None or row.get("status") == status]

    def get_belief(self, belief_id: str) -> dict[str, object] | None:
        return self.beliefs.get(belief_id)

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
        **_kwargs,
    ) -> dict[str, object]:
        belief = self.beliefs[belief_id]
        belief["status"] = status
        if confidence is not None:
            belief["confidence"] = confidence
        if superseded_by is not None:
            belief["superseded_by"] = superseded_by
        self.append_event(
            {
                "event_type": "belief.updated",
                "target_type": "belief",
                "target_id": belief_id,
                "payload_json": {"status": status},
            }
        )
        return belief

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        rows = [
            event
            for event in self.events
            if (target_type is None or event.get("target_type") == target_type)
            and (target_id is None or event.get("target_id") == target_id)
        ]
        return rows[:limit] if limit is not None else rows

    def upsert_scheduler_workflow(self, workflow: dict[str, object], **_kwargs) -> dict[str, object]:
        workflow_type = str(workflow["workflow_type"])
        row = {
            **workflow,
            "id": f"workflow-{workflow_type}",
            "last_run_id": None,
            "last_run_at": None,
            "last_result": None,
            "last_error": None,
        }
        self.workflows[workflow_type] = row
        return row

    def update_scheduler_workflow(
        self, *, workflow_type: str, patch: dict[str, object], **_kwargs
    ) -> dict[str, object]:
        workflow = self.workflows[workflow_type]
        workflow.update(patch)
        return workflow

    def get_scheduler_workflow(self, workflow_type: str) -> dict[str, object] | None:
        return self.workflows.get(workflow_type)

    def list_scheduler_workflows(self) -> list[dict[str, object]]:
        return list(self.workflows.values())

    def create_scheduler_run(self, run: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**run, "id": f"run-{len(self.runs) + 1}", "finished_at": None}
        self.runs[str(row["id"])] = row
        return row

    def update_scheduler_run(self, *, run_id: str, patch: dict[str, object], **_kwargs) -> dict[str, object]:
        run = self.runs[run_id]
        run.update(patch)
        if run.get("status") in {"succeeded", "failed"}:
            run["finished_at"] = "2026-05-10T00:01:00Z"
        return run

    def list_scheduler_runs(self, *, workflow_type: str | None = None, limit: int = 20) -> list[dict[str, object]]:
        return [
            row for row in self.runs.values() if workflow_type is None or row.get("workflow_type") == workflow_type
        ][:limit]

    def try_scheduler_workflow_lock(self, _workflow_type: str) -> bool:
        return True

    def list_artifact_quality_ratings(self, **kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": "rating-1",
                "artifact_id": "artifact-1",
                "usefulness": 4,
                "source_grounding": 5,
            }
        ][: kwargs.get("limit", 20)]

    def list_provenance_links(self, **_kwargs) -> list[dict[str, object]]:
        return []

    def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
        row = {**link, "id": f"provenance-{len(self.events) + 1}"}
        return row


def test_alice_vnext_context_pack_mcp_tool(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_context_pack",
        arguments={"query": "Alice vNext MCP provenance", "domains": ["project"]},
    )

    assert payload["relevant_memories"][0]["id"] == "memory-1"
    assert payload["sources"][0]["id"] == "source-1"
    assert payload["trace_id"] == payload["trace"]["trace_id"]
    assert store.events[-1]["event_type"] == "retrieval.context_pack_compiled"


def test_alice_vnext_context_tree_mcp_tool_returns_read_only_groups(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_context_tree",
        arguments={"query": "Alice vNext", "domains": ["project"], "limit": 4},
    )

    root_ids = [root["id"] for root in payload["roots"]]
    assert payload["schema_version"] == "vnext_context_tree_v0"
    assert payload["read_only"] is True
    assert "root:projects" in root_ids
    assert "root:memories" in root_ids
    assert payload["summary"]["projects"] == 1
    assert store.events[-1]["event_type"] == "context_tree.generated"


def test_alice_vnext_context_pack_mcp_tool_normalizes_row_scalars(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()
    memory_id = uuid4()
    source_id = uuid4()
    captured_at = datetime(2026, 5, 10, 9, 0, tzinfo=UTC)

    def search_memories(**_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": memory_id,
                "memory_type": "semantic",
                "canonical_text": "Coffee preference is pour over.",
                "status": "active",
                "confidence": 0.9,
                "domain": "personal",
                "sensitivity": "private",
                "first_seen_at": captured_at,
                "last_seen_at": captured_at,
            }
        ]

    def search_sources(**_kwargs) -> list[dict[str, object]]:
        return [
            {
                "id": source_id,
                "source_type": "manual_text",
                "title": "Coffee note",
                "content_hash": "sha256:coffee",
                "captured_at": captured_at,
                "domain": "personal",
                "sensitivity": "private",
            }
        ]

    store.search_memories = search_memories  # type: ignore[method-assign]
    store.search_sources = search_sources  # type: ignore[method-assign]

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_context_pack",
        arguments={"query": "coffee preference"},
    )

    json.dumps(payload)
    assert payload["relevant_memories"][0]["id"] == str(memory_id)
    assert payload["relevant_memories"][0]["first_seen_at"] == "2026-05-10T09:00:00+00:00"
    assert payload["sources"][0]["id"] == str(source_id)


def test_alice_vnext_agentic_memory_commit_mcp_tools(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    commit_payload = call_mcp_tool(
        context,
        name="alice_vnext_commit_memory",
        arguments={
            "agent_id": "hermes",
            "agent_type": "personal_assistant",
            "permission_profile": "trusted_local_agent",
            "title": "MCP memory commit",
            "canonical_text": "Hermes commits explicit memories through Alice.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )

    assert commit_payload["status"] == "committed"
    memory_id = commit_payload["memory"]["id"]

    recent_payload = call_mcp_tool(
        context,
        name="alice_vnext_recent_memory_commits",
        arguments={"agent_id": "hermes", "permission_profile": "trusted_local_agent"},
    )
    assert recent_payload["recent_commits"][0]["id"] == memory_id

    audit_payload = call_mcp_tool(
        context,
        name="alice_vnext_memory_audit",
        arguments={"agent_id": "hermes", "permission_profile": "trusted_local_agent", "memory_id": memory_id},
    )
    assert audit_payload["memory"]["id"] == memory_id
    assert audit_payload["revisions"][0]["action"] == "agentic_memory_commit"


def test_alice_vnext_agentic_memory_commit_accepts_documented_quote_shape(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_commit_memory",
        arguments={
            "agent_id": "hermes",
            "agent_type": "personal_assistant",
            "permission_profile": "trusted_local_agent",
            "title": "Quote to remember",
            "canonical_text": "Control your emotions or someone else will. - Unknown",
            "memory_type": "semantic",
            "domain": "learning",
            "sensitivity": "private",
            "confidence": 0.96,
        },
    )

    assert payload["status"] == "committed"
    assert payload["memory"]["memory_type"] == "semantic"
    assert payload["memory"]["domain"] == "learning"
    assert payload["memory"]["sensitivity"] == "private"


def test_alice_vnext_agentic_memory_commit_accepts_procedure_type(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_commit_memory",
        arguments={
            "agent_id": "hermes",
            "agent_type": "personal_assistant",
            "permission_profile": "trusted_local_agent",
            "title": "Release evidence procedure",
            "canonical_text": "Procedure: collect evidence, run gates, review artifact, then record follow-up loops.",
            "memory_type": "procedure",
            "domain": "project",
            "sensitivity": "private",
            "confidence": 0.94,
        },
    )

    assert payload["status"] == "committed"
    assert payload["memory"]["memory_type"] == "procedure"


def test_alice_vnext_agentic_memory_commit_rejects_invalid_enum_before_store(monkeypatch, legacy_tools_enabled) -> None:
    def fail_if_store_opened(_context):
        raise AssertionError("store should not be opened for invalid enum input")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fail_if_store_opened)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    with pytest.raises(MCPToolError, match="memory_type must be one of"):
        call_mcp_tool(
            context,
            name="alice_vnext_commit_memory",
            arguments={
                "agent_id": "hermes",
                "agent_type": "personal_assistant",
                "permission_profile": "trusted_local_agent",
                "title": "Invalid typed memory",
                "canonical_text": "This should be rejected before Postgres.",
                "memory_type": "totally_invalid_type",
                "domain": "unknown",
                "sensitivity": "unknown",
            },
        )


def test_alice_vnext_agentic_memory_confirm_mcp_tool(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    confirmation_payload = call_mcp_tool(
        context,
        name="alice_vnext_commit_memory",
        arguments={
            "agent_id": "hermes",
            "agent_type": "personal_assistant",
            "permission_profile": "trusted_local_agent",
            "title": "MCP sensitive memory",
            "canonical_text": "Sensitive health facts need inline confirmation.",
            "domain": "health",
            "sensitivity": "confidential",
            "confidence": 0.94,
        },
    )
    assert confirmation_payload["status"] == "confirmation_required"

    confirmed_payload = call_mcp_tool(
        context,
        name="alice_vnext_confirm_memory",
        arguments={
            "agent_id": "hermes",
            "permission_profile": "trusted_local_agent",
            "confirmation_id": confirmation_payload["confirmation_id"],
        },
    )

    assert confirmed_payload["status"] == "committed"
    assert confirmed_payload["memory"]["status"] == "active"


def test_postgres_core_review_and_correct_round_trip_the_canonical_vnext_memory(monkeypatch, core_surface) -> None:
    store = FakeVNextMCPStore()
    memory_id = str(uuid4())
    store.memories.append(
        {
            "id": memory_id,
            "memory_key": "capture.canonical-review",
            "value": {"text": "Ship canonical review."},
            "source_event_ids": [],
            "status": "candidate",
            "confirmation_status": "unconfirmed",
            "memory_type": "decision",
            "confidence": 0.9,
            "title": "Canonical review",
            "canonical_text": "Ship canonical review.",
            "summary": "Ship canonical review.",
            "domain": "project",
            "sensitivity": "internal",
            "project_id": "alicebot",
            "metadata_json": {"review_required": True},
        }
    )

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    def fail_legacy_store_context(_context):
        raise AssertionError("core review/correct must not use deprecated continuity tables")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(mcp_tools_module, "_store_context", fail_legacy_store_context)
    context = _mcp_context()

    queue = call_mcp_tool(context, name="alice_memory_review", arguments={})
    assert [item["id"] for item in queue["items"]] == [memory_id]

    detail = call_mcp_tool(
        context,
        name="alice_memory_review",
        arguments={"review_item_id": memory_id},
    )
    assert detail["review"]["memory"]["id"] == memory_id

    corrected = call_mcp_tool(
        context,
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "approve",
            "reason": "Reviewed against source evidence.",
        },
    )
    assert corrected["memory"]["id"] == memory_id
    assert corrected["memory"]["status"] == "active"
    assert corrected["memory"]["confirmation_status"] == "confirmed"
    assert corrected["memory"]["metadata_json"]["review_required"] is False


def test_alice_generate_daily_and_weekly_brief_mcp_tools(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    daily_payload = call_mcp_tool(
        context,
        name="alice_generate_daily_brief",
        arguments={"generated_for": "2026-05-10", "domains": ["project"]},
    )
    weekly_payload = call_mcp_tool(
        context,
        name="alice_generate_weekly_synthesis",
        arguments={"generated_for": "2026-05-10", "domains": ["project"]},
    )

    assert daily_payload["artifact_type"] == "daily_brief"
    assert daily_payload["metadata_json"]["candidate_open_loop_ids"] == ["loop-1"]
    assert weekly_payload["artifact_type"] == "weekly_synthesis"
    assert weekly_payload["metadata_json"]["candidate_memory_ids"] == ["memory-2"]
    assert store.events[-1]["event_type"] == "artifact.generated"


@pytest.mark.parametrize(
    "tool_name",
    [
        "alice_generate_daily_brief",
        "alice_generate_weekly_synthesis",
        "alice_generate_connections",
        "alice_generate_contradictions",
    ],
)
def test_report_tool_schemas_expose_both_project_scope_aliases(
    monkeypatch,
    legacy_tools_enabled,
    tool_name: str,
) -> None:
    schema = mcp_tools_module._TOOL_DEFINITIONS_BY_NAME[tool_name]["inputSchema"]
    properties = schema["properties"]
    assert properties["project_scope"] == {
        "type": "array",
        "items": {"type": "string"},
    }
    assert properties["projects"] == {
        "type": "array",
        "items": {"type": "string"},
    }

    monkeypatch.setitem(
        mcp_tools_module._TOOL_HANDLERS,
        tool_name,
        lambda _context, arguments: dict(arguments),
    )
    payload = call_mcp_tool(
        _mcp_context(),
        name=tool_name,
        arguments={"project_scope": ["project-a"], "projects": ["project-b"]},
    )
    assert payload == {
        "project_scope": ["project-a"],
        "projects": ["project-b"],
    }


def test_alice_vnext_generate_artifact_supports_model_backed_agent_options(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_generate_artifact",
        arguments={
            "workflow_type": "daily_brief",
            "generated_for": "2026-05-10",
            "domains": ["project"],
            "sensitivity_allowed": ["public", "internal", "private"],
            "generation_mode": "model_backed",
            "model_route_mode": "local_only",
            "agent_id": "hermes",
            "permission_profile": "trusted_local_agent",
            "agent_run_id": "run-1",
        },
    )

    assert payload["artifact_type"] == "daily_brief"
    assert payload["status"] == "needs_review"
    assert payload["prompt_hash"]
    assert payload["model_info_json"]["provider"] == "deterministic_local"
    assert payload["metadata_json"]["generation_mode"] == "model_backed"
    assert payload["metadata_json"]["agent_id"] == "hermes"
    assert payload["metadata_json"]["policy_decision"]["decision"] == "allowed"
    assert "source:source-1" in payload["metadata_json"]["source_refs"]


def test_alice_vnext_generate_artifact_supports_memory_consolidation(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(
        mcp_tools_module,
        "run_now_durable",
        lambda **kwargs: mcp_tools_module.VNextSchedulerService(store).run_now(kwargs["request"]),
    )
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_generate_artifact",
        arguments={
            "workflow_type": "memory_consolidation",
            "generated_for": "2026-05-10",
            "domains": ["project"],
            "sensitivity_allowed": ["public", "internal", "private"],
            "agent_id": "hermes",
            "permission_profile": "trusted_local_agent",
        },
    )

    artifact = payload["artifact"]
    assert payload["run"]["status"] == "succeeded"
    assert artifact["artifact_type"] == "memory_consolidation"
    assert artifact["status"] == "needs_review"
    assert artifact["metadata_json"]["workflow_type"] == "memory_consolidation"
    # Without an embedding provider the consolidation run performs no
    # clustering: it emits a review-only report with explicit skip reasons
    # and creates no placeholder candidates.
    assert artifact["metadata_json"]["candidate_memory_ids"] == []
    assert artifact["metadata_json"]["consolidation"]["skipped"]
    assert all(memory["status"] != "candidate" for memory in store.memories)


def test_alice_vnext_ingest_agent_output_creates_review_only_records(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    payload = call_mcp_tool(
        context,
        name="alice_vnext_ingest_agent_output",
        arguments={
            "agent_id": "openclaw",
            "agent_type": "coding_agent",
            "permission_profile": "project_scoped_agent",
            "agent_run_id": "run-1",
            "project_scope": ["Alice"],
            "title": "Sprint summary",
            "content": "Decision: Agent outputs remain review-only.",
            "output_type": "sprint_summary",
            "domain": "project",
            "sensitivity": "private",
            "propose_memory": True,
        },
    )

    assert payload["status"] == "imported"
    assert payload["source_id"] == "source-1"
    assert payload["artifact_id"] == "artifact-1"
    assert payload["memory_id"] is not None
    assert store.artifacts["artifact-1"]["status"] == "needs_review"
    assert store.artifacts["artifact-1"]["metadata_json"]["project_scope"] == ["Alice"]
    assert store.memories[-1]["status"] == "candidate"
    assert store.memories[-1]["project_scope"] == ["Alice"]
    assert any(event["event_type"] == "agent.output_ingested" for event in store.events)


def test_alice_generate_connections_and_graph_mcp_tools(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    connection_payload = call_mcp_tool(
        context,
        name="alice_generate_connections",
        arguments={"domains": ["project"], "max_connections": 1},
    )
    review_payload = call_mcp_tool(
        context,
        name="alice_graph_edge_review",
        arguments={"edge_id": "edge-1", "action": "accept"},
    )
    neighborhood_payload = call_mcp_tool(
        context,
        name="alice_graph_neighborhood",
        arguments={"target_id": "source-1"},
    )

    assert connection_payload["artifact_type"] == "connection_report"
    assert connection_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_payload["metadata_json"]["status"] == "accepted"
    assert neighborhood_payload["edge_count"] == 1
    assert neighborhood_payload["from_edges"][0]["id"] == "edge-1"


def test_alice_generate_contradictions_and_belief_mcp_tools(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    contradiction_payload = call_mcp_tool(
        context,
        name="alice_generate_contradictions",
        arguments={"domains": ["project"], "max_contradictions": 1},
    )
    review_payload = call_mcp_tool(
        context,
        name="alice_belief_review",
        arguments={"belief_id": "belief-1", "action": "challenge", "confidence": 0.2},
    )
    state_payload = call_mcp_tool(
        context,
        name="alice_belief_state",
        arguments={"belief_id": "belief-1"},
    )

    assert contradiction_payload["artifact_type"] == "contradiction_report"
    assert contradiction_payload["metadata_json"]["candidate_edge_ids"] == ["edge-1"]
    assert review_payload["status"] == "challenged"
    assert review_payload["confidence"] == 0.2
    assert state_payload["current"]["status"] == "challenged"
    assert "challenged" in state_payload["previous_statuses"]


def test_alice_project_and_open_loop_mcp_tools(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()

    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    update_payload = call_mcp_tool(
        context,
        name="alice_project_update_candidate",
        arguments={"project_id": "project-1", "domains": ["project"]},
    )
    extract_payload = call_mcp_tool(
        context,
        name="alice_open_loop_extract",
        arguments={"project_id": "project-1", "domains": ["project"]},
    )
    review_update_payload = call_mcp_tool(
        context,
        name="alice_project_update_review",
        arguments={
            "artifact_id": "artifact-1",
            "action": "edit",
            "edited_current_state": "Project automation reviewed.",
        },
    )
    review_loop_payload = call_mcp_tool(
        context,
        name="alice_open_loop_review",
        arguments={
            "loop_id": extract_payload["open_loops"][0]["id"],
            "action": "snooze",
            "due_at": "2026-05-12T09:00:00Z",
        },
    )
    dashboard_payload = call_mcp_tool(
        context,
        name="alice_project_dashboard",
        arguments={"project_id": "project-1"},
    )

    assert update_payload["artifact_type"] == "project_update"
    assert update_payload["metadata_json"]["candidate_memory_id"] == "memory-2"
    assert extract_payload["created_count"] == 1
    assert extract_payload["open_loops"][0]["metadata_json"]["owner"] == "Samir"
    assert review_update_payload["status"] == "accepted"
    assert store.projects["project-1"]["current_state"] == "Project automation reviewed."
    assert review_loop_payload["due_at"] == "2026-05-12T09:00:00Z"
    assert dashboard_payload["counts"]["open_loops"] == 1


def _mcp_context() -> MCPRuntimeContext:
    return MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )


@pytest.mark.parametrize(
    ("handler", "arguments"),
    (
        (mcp_tools_module._handle_alice_vnext_scheduler_status, {}),
        (
            mcp_tools_module._handle_alice_vnext_scheduler_run_now,
            {"workflow_type": "daily_brief"},
        ),
        (mcp_tools_module._handle_alice_vnext_scheduler_run_due, {}),
        (mcp_tools_module._handle_alice_vnext_scheduler_pause, {}),
        (mcp_tools_module._handle_alice_vnext_scheduler_resume, {}),
    ),
)
def test_scheduler_mcp_tools_fail_closed_on_sqlite(handler, arguments) -> None:
    context = MCPRuntimeContext(
        database_url="sqlite:///tmp/alice.db",
        user_id=uuid4(),
    )

    with pytest.raises(MCPToolError, match="require the Postgres backend"):
        handler(context, arguments)


def test_scheduler_mcp_due_execution_starts_after_policy_transaction(monkeypatch) -> None:
    transaction_open = False
    calls: list[str] = []

    @contextmanager
    def fake_vnext_store_context(_context):
        nonlocal transaction_open
        transaction_open = True
        calls.append("policy_open")
        try:
            yield object()
        finally:
            transaction_open = False
            calls.append("policy_closed")

    class Decision:
        decision = "allowed"

        def to_record(self):
            return {"decision": "allowed"}

    def fake_policy_checked(*_args, **_kwargs):
        assert transaction_open is True
        return "scheduler", None, Decision()

    def fake_run_due(**_kwargs):
        assert transaction_open is False
        calls.append("durable_execute")
        return {"due_count": 0, "failed_count": 0, "runs": []}

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(mcp_tools_module, "_policy_checked", fake_policy_checked)
    monkeypatch.setattr(
        mcp_tools_module,
        "run_due_workflows_durable",
        fake_run_due,
    )

    payload = mcp_tools_module._handle_alice_vnext_scheduler_run_due(
        _mcp_context(),
        {"limit": 1},
    )

    assert payload["due_count"] == 0
    assert calls == ["policy_open", "policy_closed", "durable_execute"]


def test_scheduler_mcp_run_now_starts_after_policy_transaction(monkeypatch) -> None:
    transaction_open = False
    calls: list[str] = []

    @contextmanager
    def fake_vnext_store_context(_context):
        nonlocal transaction_open
        transaction_open = True
        calls.append("policy_open")
        try:
            yield object()
        finally:
            transaction_open = False
            calls.append("policy_closed")

    class Decision:
        decision = "allowed"
        effective_domains = ("project",)
        effective_project_scope = ("alice",)
        effective_sensitivity_allowed = ("private",)

        def to_record(self):
            return {"decision": "allowed"}

    def fake_policy_checked(*_args, **_kwargs):
        assert transaction_open is True
        return "user", None, Decision()

    def fake_run_now(**kwargs):
        assert transaction_open is False
        calls.append("durable_execute")
        request = kwargs["request"]
        assert request.workflow_type == "daily_brief"
        assert request.projects == ("alice",)
        return {"run": {"status": "succeeded"}, "artifact": {"id": "artifact-1"}}

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(mcp_tools_module, "_policy_checked", fake_policy_checked)
    monkeypatch.setattr(mcp_tools_module, "run_now_durable", fake_run_now)

    payload = mcp_tools_module._handle_alice_vnext_scheduler_run_now(
        _mcp_context(),
        {"workflow_type": "daily_brief"},
    )

    assert payload["run"]["status"] == "succeeded"
    assert calls == ["policy_open", "policy_closed", "durable_execute"]


def _resolved_scoped_agent_context(*, profile: str, project: str) -> MCPRuntimeContext:
    return MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        agent_identity=mcp_tools_module.AgentIdentity(
            agent_id=f"{profile}-{project}",
            permission_profile=profile,
            project_scope=(project,),
            project_scope_locked=True,
            auth="agent_api_key",
        ),
        agent_identity_resolved=True,
    )


def _patch_vnext_store(monkeypatch, store: FakeVNextMCPStore) -> None:
    @contextmanager
    def fake_vnext_store_context(_context):
        yield store

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)


def test_vnext_artifact_get_authorizes_persisted_scope_and_sensitivity(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()
    artifact = store.create_artifact(
        {
            "artifact_type": "daily_brief",
            "title": "Project B private brief",
            "content_markdown": "# Project B private brief\n\nSensitive body.",
            "status": "needs_review",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_id": "project-b"},
        }
    )
    artifact_id = str(artifact["id"])
    _patch_vnext_store(monkeypatch, store)

    with pytest.raises(MCPToolError, match="project_scope_binding_violation") as excinfo:
        call_mcp_tool(
            _resolved_scoped_agent_context(profile="trusted_local_agent", project="project-a"),
            name="alice_vnext_artifact_get",
            arguments={"artifact_id": artifact_id},
        )
    assert "Sensitive body" not in str(excinfo.value)

    with pytest.raises(MCPToolError, match="artifact_target_filtering_not_permitted"):
        call_mcp_tool(
            _resolved_scoped_agent_context(profile="read_only_agent", project="project-b"),
            name="alice_vnext_artifact_get",
            arguments={"artifact_id": artifact_id},
        )

    payload = call_mcp_tool(
        _resolved_scoped_agent_context(profile="trusted_local_agent", project="project-b"),
        name="alice_vnext_artifact_get",
        arguments={"artifact_id": artifact_id},
    )
    assert payload["id"] == artifact_id
    assert payload["content_markdown"].endswith("Sensitive body.")


def test_vnext_artifact_review_locks_and_authorizes_persisted_scope(monkeypatch, legacy_tools_enabled) -> None:
    store = FakeVNextMCPStore()
    artifact = store.create_artifact(
        {
            "artifact_type": "daily_brief",
            "title": "Project B review target",
            "content_markdown": "# Review target",
            "status": "needs_review",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_id": "project-b"},
        }
    )
    artifact_id = str(artifact["id"])
    _patch_vnext_store(monkeypatch, store)

    with pytest.raises(MCPToolError, match="project_scope_binding_violation"):
        call_mcp_tool(
            _resolved_scoped_agent_context(profile="admin_agent", project="project-a"),
            name="alice_vnext_artifact_review",
            arguments={"artifact_id": artifact_id, "action": "accept"},
        )
    assert store.artifacts[artifact_id]["status"] == "needs_review"

    payload = call_mcp_tool(
        _resolved_scoped_agent_context(profile="admin_agent", project="project-b"),
        name="alice_vnext_artifact_review",
        arguments={"artifact_id": artifact_id, "action": "accept"},
    )
    assert payload["status"] == "accepted"
    assert store.artifacts[artifact_id]["status"] == "accepted"


def test_generic_mcp_artifact_review_preserves_applied_project_update_state(
    monkeypatch, legacy_tools_enabled
) -> None:
    store = FakeVNextMCPStore()
    artifact = mcp_tools_module.VNextProjectService(store).generate_project_update_candidate(
        mcp_tools_module.ProjectAutomationRequest(project_id="project-1", domains=("project",))
    )
    artifact_id = str(artifact["id"])
    metadata = artifact["metadata_json"]
    assert isinstance(metadata, dict)
    candidate_memory_id = str(metadata["candidate_memory_id"])
    expected_state = str(metadata["suggested_current_state"])
    _patch_vnext_store(monkeypatch, store)
    context = _resolved_scoped_agent_context(profile="admin_agent", project="project-1")

    accepted = call_mcp_tool(
        context,
        name="alice_vnext_artifact_review",
        arguments={"artifact_id": artifact_id, "action": "accept"},
    )
    with pytest.raises(MCPToolError, match="cannot be rejected"):
        call_mcp_tool(
            context,
            name="alice_vnext_artifact_review",
            arguments={"artifact_id": artifact_id, "action": "reject"},
        )

    assert accepted["status"] == "accepted"
    assert store.artifacts[artifact_id]["status"] == "accepted"
    assert store.projects["project-1"]["current_state"] == expected_state
    assert store.get_memory(candidate_memory_id)["status"] == "active"
    assert not any(event.get("event_type") == "project.update_candidate_rejected" for event in store.events)


class FakeEmbeddingProvider:
    provider = "fake"
    model = "fake-embed"

    def __init__(self) -> None:
        self.embedded: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.embedded.append(text)
        return [0.1, 0.2, 0.3]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


def _recall_memory_row(memory_id: str, text: str) -> dict[str, object]:
    return {
        "id": memory_id,
        "memory_type": "semantic",
        "canonical_text": text,
        "status": "active",
        "confidence": 0.9,
        "domain": "project",
        "sensitivity": "private",
    }


class HybridRetrievalStore(FakeVNextMCPStore):
    def __init__(self) -> None:
        super().__init__()
        self.fts_calls: list[dict[str, object]] = []
        self.vector_calls: list[dict[str, object]] = []

    def search_memories_fts(self, **kwargs) -> list[dict[str, object]]:
        self.fts_calls.append(kwargs)
        return [
            _recall_memory_row("memory-a", "Alice ships hybrid retrieval."),
            _recall_memory_row("memory-b", "Recall fuses FTS and vector stages."),
        ]

    def search_memories_vector(self, **kwargs) -> list[dict[str, object]]:
        self.vector_calls.append(kwargs)
        return [
            _recall_memory_row("memory-b", "Recall fuses FTS and vector stages."),
            _recall_memory_row("memory-c", "Vector-only neighbor about retrieval."),
        ]


def test_alice_recall_fuses_fts_and_vector_stages(monkeypatch, core_surface) -> None:
    store = HybridRetrievalStore()
    _patch_vnext_store(monkeypatch, store)
    provider = FakeEmbeddingProvider()
    monkeypatch.setattr(vnext_retrieval_module, "get_embedding_provider", lambda: provider)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={"query": "hybrid retrieval", "limit": 5, "debug": True},
    )

    # memory-b appears in both stages, so reciprocal-rank fusion ranks it first.
    assert [result["id"] for result in payload["results"]] == ["memory-b", "memory-a", "memory-c"]
    assert payload["count"] == 3
    assert provider.embedded == ["hybrid retrieval"]
    assert store.fts_calls and store.vector_calls
    assert "query_vector" in store.vector_calls[0]
    assert payload["retrieval"]["vector_stage"] == VECTOR_STAGE_ENABLED
    assert payload["retrieval"]["stages"]["fts"]["source"] == "postgres_fts"
    assert payload["retrieval"]["stages"]["vector"]["status"] == VECTOR_STAGE_ENABLED
    assert payload["retrieval"]["fusion"]["algorithm"] == "reciprocal_rank_fusion"


def test_alice_recall_degrades_to_lexical_without_embedding_provider(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={"query": "provenance", "debug": True},
    )

    assert payload["results"][0]["id"] == "memory-1"
    assert payload["retrieval"]["vector_stage"] == VECTOR_STAGE_DISABLED_NO_PROVIDER
    assert payload["retrieval"]["stages"]["vector"]["candidate_count"] == 0
    assert payload["retrieval"]["stages"]["fts"]["source"] == "store_lexical"


def test_alice_recall_results_are_compact_and_trace_is_debug_only(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={"query": "provenance"},
    )

    assert "retrieval" not in payload
    assert set(payload) == {"query", "results", "count"}
    result = payload["results"][0]
    assert set(result) == {
        "id",
        "type",
        "text",
        "score",
        "domain",
        "status",
        "confidence",
        "provenance_count",
    }
    assert result["text"] == "Alice vNext MCP context packs preserve provenance."
    assert result["provenance_count"] == 0
    assert result["score"] > 0


def test_alice_context_pack_is_compact_and_gates_trace_behind_debug(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    compact = call_mcp_tool(
        _mcp_context(),
        name="alice_context_pack",
        arguments={"query": "Alice provenance", "domains": ["project"]},
    )

    assert compact["memories"][0]["id"] == "memory-1"
    assert compact["sources"][0]["id"] == "source-1"
    for stripped_key in ("trace", "query_interpretation", "agent_identity", "policy_decision"):
        assert stripped_key not in compact
    # Per-item boilerplate such as raw metadata is stripped from compact rows.
    assert "metadata_json" not in compact["sources"][0]
    assert isinstance(compact["trace_id"], str)
    assert compact["token_report"]["serialized_token_estimate_scope"] == "compact_mcp_tool_payload"
    assert compact["token_report"]["serialized_token_estimate"] == (
        vnext_retrieval_module.estimate_item_tokens(compact)
    )
    assert "full_pack_serialized_token_estimate" in compact["token_report"]

    debug = call_mcp_tool(
        _mcp_context(),
        name="alice_context_pack",
        arguments={"query": "Alice provenance", "domains": ["project"], "debug": True},
    )
    assert debug["trace"]["trace_id"] == debug["trace_id"]
    assert debug["query_interpretation"]["query_type"]
    assert debug["token_report"]["serialized_token_estimate"] == (vnext_retrieval_module.estimate_item_tokens(debug))


class EntityGraphRetrievalStore(FakeVNextMCPStore):
    """Fake store with the entity substrate the graph stage duck-types."""

    def __init__(self) -> None:
        super().__init__()
        self.entities: dict[str, dict[str, object]] = {}
        self.entity_lookup_calls: list[tuple[str, ...]] = []

    def find_entities_by_names(self, normalized_names: tuple[str, ...]) -> list[dict[str, object]]:
        self.entity_lookup_calls.append(tuple(normalized_names))
        names = set(normalized_names)
        matched = [
            entity
            for entity in self.entities.values()
            if entity.get("normalized_name") in names or any(alias in names for alias in entity.get("aliases", []))
        ]
        return sorted(matched, key=lambda entity: -int(entity.get("mention_count", 0) or 0))

    def get_entity(self, entity_id: str) -> dict[str, object] | None:
        return self.entities.get(entity_id)


def _seed_entity_connected_memory(store: EntityGraphRetrievalStore) -> None:
    # Zero lexical overlap with the "Meridian" queries used below: only the
    # graph hop through the entity can surface this memory.
    store.memories.append(
        {
            "id": "memory-meridian",
            "memory_type": "semantic",
            "canonical_text": "Legal review is blocking the Q3 close.",
            "status": "active",
            "confidence": 0.9,
            "domain": "project",
            "sensitivity": "private",
        }
    )
    store.entities["entity-meridian"] = {
        "id": "entity-meridian",
        "entity_type": "organization",
        "name": "Meridian",
        "normalized_name": "meridian",
        "aliases": ["meridian bank"],
        "mention_count": 4,
    }
    store.create_edge(
        {
            "from_type": "memory",
            "from_id": "memory-meridian",
            "to_type": "entity",
            "to_id": "entity-meridian",
            "edge_type": "mentions",
            "observed_at": "2026-07-01T00:00:00Z",
        }
    )


def test_alice_recall_graph_stage_finds_entity_connected_memory(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = EntityGraphRetrievalStore()
    _seed_entity_connected_memory(store)
    _patch_vnext_store(monkeypatch, store)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={"query": "Meridian update", "debug": True},
    )

    assert "memory-meridian" in [result["id"] for result in payload["results"]]
    assert payload["entities"] == [
        {"id": "entity-meridian", "name": "Meridian", "entity_type": "organization", "mention_count": 4}
    ]
    graph_stage = payload["retrieval"]["stages"]["graph"]
    assert graph_stage["status"] == "enabled"
    assert graph_stage["candidate_count"] == 1
    assert graph_stage["matched_entities"] == payload["entities"]
    # Resolution is one round-trip over the query's candidate names.
    assert len(store.entity_lookup_calls) == 1
    assert "meridian" in store.entity_lookup_calls[0]

    # Without an entity match the stage reports itself disabled and the
    # payload stays free of an empty entities section.
    unmatched = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={"query": "provenance", "debug": True},
    )
    assert "entities" not in unmatched
    assert unmatched["retrieval"]["stages"]["graph"]["status"] == "disabled: no entity match"


def test_alice_context_pack_lists_the_entities_the_query_resolved_to(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = EntityGraphRetrievalStore()
    _seed_entity_connected_memory(store)
    _patch_vnext_store(monkeypatch, store)

    pack = call_mcp_tool(
        _mcp_context(),
        name="alice_context_pack",
        arguments={"query": "Meridian update", "domains": ["project"]},
    )

    assert pack["entities"] == [
        {"id": "entity-meridian", "name": "Meridian", "entity_type": "organization", "mention_count": 4}
    ]
    assert "memory-meridian" in [memory["id"] for memory in pack["memories"]]

    no_match = call_mcp_tool(
        _mcp_context(),
        name="alice_context_pack",
        arguments={"query": "provenance", "domains": ["project"]},
    )
    assert "entities" not in no_match


def test_alice_explain_timeline_and_chain_entity_links(monkeypatch, core_surface, no_embedding_provider) -> None:
    store = EntityGraphRetrievalStore()
    _patch_vnext_store(monkeypatch, store)

    original = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Meridian deal is on track",
            "canonical_text": "The Meridian acquisition closes in Q3.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    replacement = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Meridian deal slipped",
            "canonical_text": "The Meridian acquisition slipped to Q4.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    old_id = str(original["memory"]["id"])
    new_id = str(replacement["memory"]["id"])
    store.entities["entity-meridian"] = {
        "id": "entity-meridian",
        "entity_type": "organization",
        "name": "Meridian",
        "normalized_name": "meridian",
        "aliases": [],
        "mention_count": 2,
    }
    store.create_edge(
        {
            "from_type": "memory",
            "from_id": new_id,
            "to_type": "entity",
            "to_id": "entity-meridian",
            "edge_type": "about",
            "observed_at": "2026-07-01T00:00:00Z",
        }
    )
    call_mcp_tool(
        _mcp_context(),
        name="alice_memory_manage",
        arguments={
            **_trusted_identity_arguments(),
            "action": "undo",
            "memory_id": old_id,
            "reason": "deal slipped",
            "superseded_by": new_id,
        },
    )

    explained = call_mcp_tool(_mcp_context(), name="alice_explain", arguments={"memory_id": old_id})

    # Chain nodes list their linked entities when the store supports them.
    chain = {entry["id"]: entry for entry in explained["supersession_chain"]}
    assert chain[old_id]["entities"] == []
    assert chain[new_id]["entities"] == [
        {"id": "entity-meridian", "name": "Meridian", "entity_type": "organization", "mention_count": 2}
    ]
    # The timeline merges the chain with the revision history: created, then
    # replaced. The 'superseded' revision is folded into the successor entry.
    assert [(entry["kind"], entry["memory_id"]) for entry in explained["timeline"]] == [
        ("created", old_id),
        ("superseded_by", new_id),
    ]
    assert explained["timeline"][1]["summary"] == "Replaced by: Meridian deal slipped"
    # The fake store does not stamp created_at, but the shape is stable.
    assert all(set(entry) == {"at", "kind", "memory_id", "summary"} for entry in explained["timeline"])

    # A correction shows up as its own timeline entry on the successor
    # (seeded through the store surface the commit service writes to).
    store.append_revision(
        {
            "memory_id": new_id,
            "revision_type": "corrected",
            "reason": "date confirmed by counsel",
            "created_at": "2026-07-03T00:00:00Z",
        }
    )
    corrected = call_mcp_tool(_mcp_context(), name="alice_explain", arguments={"memory_id": new_id})
    kinds = [entry["kind"] for entry in corrected["timeline"]]
    assert "corrected" in kinds
    corrected_entry = next(entry for entry in corrected["timeline"] if entry["kind"] == "corrected")
    assert corrected_entry["memory_id"] == new_id
    assert corrected_entry["summary"] == "date confirmed by counsel"


def test_alice_recall_passes_memory_types_and_projects_to_retrieval_stages(monkeypatch, core_surface) -> None:
    store = HybridRetrievalStore()
    _patch_vnext_store(monkeypatch, store)
    provider = FakeEmbeddingProvider()
    monkeypatch.setattr(vnext_retrieval_module, "get_embedding_provider", lambda: provider)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={
            "query": "hybrid retrieval",
            "memory_types": ["decision", "procedure"],
            "projects": ["Alice"],
            "debug": True,
        },
    )

    for stage_calls in (store.fts_calls, store.vector_calls):
        assert stage_calls, "retrieval stage was not invoked"
        assert tuple(stage_calls[0]["memory_types"]) == ("decision", "procedure")
        assert tuple(stage_calls[0]["projects"]) == ("Alice",)
    assert payload["retrieval"]["filters"] == {
        "memory_types": ["decision", "procedure"],
        "projects": ["Alice"],
    }

    # Without the filters, the optional kwargs are omitted so store defaults apply.
    call_mcp_tool(_mcp_context(), name="alice_recall", arguments={"query": "hybrid retrieval"})
    assert store.fts_calls[-1].get("memory_types") in (None, ())
    assert store.fts_calls[-1].get("projects") in (None, ())
    assert store.fts_calls[-1].get("created_by_agent_ids") in (None, ())


def test_alice_recall_passes_created_by_agents_to_retrieval_stages(monkeypatch, core_surface) -> None:
    store = HybridRetrievalStore()
    _patch_vnext_store(monkeypatch, store)
    provider = FakeEmbeddingProvider()
    monkeypatch.setattr(vnext_retrieval_module, "get_embedding_provider", lambda: provider)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_recall",
        arguments={
            "query": "hybrid retrieval",
            "created_by_agents": ["openclaw", "hermes"],
            "debug": True,
        },
    )

    for stage_calls in (store.fts_calls, store.vector_calls):
        assert stage_calls, "retrieval stage was not invoked"
        assert tuple(stage_calls[0]["created_by_agent_ids"]) == ("openclaw", "hermes")
    assert payload["retrieval"]["filters"] == {"created_by_agent_ids": ["openclaw", "hermes"]}


def test_alice_context_pack_passes_created_by_agents_to_the_compiler(monkeypatch, core_surface) -> None:
    store = HybridRetrievalStore()
    _patch_vnext_store(monkeypatch, store)
    provider = FakeEmbeddingProvider()
    monkeypatch.setattr(vnext_retrieval_module, "get_embedding_provider", lambda: provider)

    call_mcp_tool(
        _mcp_context(),
        name="alice_context_pack",
        arguments={"query": "Alice retrieval status", "created_by_agents": ["openclaw"]},
    )

    assert store.fts_calls, "context pack did not reach the FTS stage"
    assert tuple(store.fts_calls[0]["created_by_agent_ids"]) == ("openclaw",)

    # Omitted filter is not forwarded, so store defaults apply.
    call_mcp_tool(
        _mcp_context(),
        name="alice_context_pack",
        arguments={"query": "Alice retrieval status"},
    )
    assert store.fts_calls[-1].get("created_by_agent_ids") in (None, ())


def test_alice_recall_rejects_invalid_memory_types_before_store(monkeypatch, core_surface) -> None:
    def fail_if_store_opened(_context):
        raise AssertionError("store should not be opened for invalid memory_types input")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fail_if_store_opened)

    with pytest.raises(MCPToolError, match=r"memory_types\[0\] must be one of"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_recall",
            arguments={"query": "anything", "memory_types": ["totally_invalid_type"]},
        )


def test_alice_context_pack_passes_memory_types_to_the_compiler(monkeypatch, core_surface) -> None:
    store = HybridRetrievalStore()
    _patch_vnext_store(monkeypatch, store)
    provider = FakeEmbeddingProvider()
    monkeypatch.setattr(vnext_retrieval_module, "get_embedding_provider", lambda: provider)

    call_mcp_tool(
        _mcp_context(),
        name="alice_context_pack",
        arguments={"query": "Alice retrieval status", "memory_types": ["decision"]},
    )

    assert store.fts_calls, "context pack did not reach the FTS stage"
    assert tuple(store.fts_calls[0]["memory_types"]) == ("decision",)


def test_alice_context_pack_surfaces_the_token_report(monkeypatch, core_surface) -> None:
    report = {
        "token_budget": 900,
        "token_estimate": 842,
        "truncated": True,
        "dropped_item_count": 3,
        "serialized_token_estimate": 1_400,
        "excluded_token_estimate": 558,
    }
    derived_values = {
        "reference_time": "2026-07-11T10:00:00+00:00",
        "lines": ["The source was captured 2 days before the reference time."],
    }

    def fake_pack_payload(_context, _arguments):
        return {
            "context_pack_id": "pack-1",
            "query_interpretation": {"query": "budget", "query_type": "strategic_synthesis"},
            "relevant_memories": [],
            "open_loops": [],
            "sources": [],
            "trace_id": "trace-1",
            "token_report": dict(report),
            "derived_values": dict(derived_values),
        }

    monkeypatch.setattr(mcp_tools_module, "_vnext_context_pack_payload", fake_pack_payload)
    nested = call_mcp_tool(_mcp_context(), name="alice_context_pack", arguments={"query": "budget", "max_tokens": 900})
    assert nested["derived_values"] == derived_values
    assert nested["token_report"] == {
        "token_budget": 900,
        "token_estimate": 842,
        "truncated": True,
        "dropped_item_count": 3,
        "full_pack_serialized_token_estimate": 1_400,
        "full_pack_excluded_token_estimate": 558,
        "serialized_token_estimate_scope": "compact_mcp_tool_payload",
        "serialized_token_estimate": vnext_retrieval_module.estimate_item_tokens(nested),
    }

    def fake_pack_payload_flat(_context, _arguments):
        return {
            "context_pack_id": "pack-2",
            "query_interpretation": {"query": "budget", "query_type": "strategic_synthesis"},
            "relevant_memories": [],
            "open_loops": [],
            "sources": [],
            "trace_id": "trace-2",
            **report,
        }

    monkeypatch.setattr(mcp_tools_module, "_vnext_context_pack_payload", fake_pack_payload_flat)
    flat = call_mcp_tool(_mcp_context(), name="alice_context_pack", arguments={"query": "budget"})
    assert flat["token_report"]["serialized_token_estimate"] == (vnext_retrieval_module.estimate_item_tokens(flat))
    assert flat["token_report"]["full_pack_serialized_token_estimate"] == 1_400
    assert flat["token_report"]["full_pack_excluded_token_estimate"] == 558
    assert "excluded_token_estimate" not in flat["token_report"]


def test_alice_context_pack_forwards_the_grounding_statistic(monkeypatch, core_surface) -> None:
    # pack["grounding"] exists only when a salient query entity has zero
    # corpus support; the compact view must forward it, and its absence
    # must leave the response schema untouched (ungated byte-identical).
    base_pack = {
        "context_pack_id": "pack-1",
        "query_interpretation": {"query": "Did Zorblatt Nine ship?", "query_type": "recall"},
        "relevant_memories": [],
        "open_loops": [],
        "sources": [],
        "trace_id": "trace-1",
    }

    def gated_pack(_context, _arguments):
        return {
            **base_pack,
            "grounding": {"unsupported_entities": ["Zorblatt Nine"], "checked": 1},
        }

    monkeypatch.setattr(mcp_tools_module, "_vnext_context_pack_payload", gated_pack)
    gated = call_mcp_tool(_mcp_context(), name="alice_context_pack", arguments={"query": "Did Zorblatt Nine ship?"})
    assert gated["grounding"] == {"unsupported_entities": ["Zorblatt Nine"], "checked": 1}

    monkeypatch.setattr(mcp_tools_module, "_vnext_context_pack_payload", lambda _c, _a: dict(base_pack))
    ungated = call_mcp_tool(_mcp_context(), name="alice_context_pack", arguments={"query": "Did Zorblatt Nine ship?"})
    assert "grounding" not in ungated


def _trusted_identity_arguments() -> dict[str, object]:
    return {
        "agent_id": "hermes",
        "agent_type": "personal_assistant",
        "permission_profile": "trusted_local_agent",
    }


def test_alice_memory_commit_is_a_core_tool_and_commits(monkeypatch, core_surface, no_embedding_provider) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Core memory commit",
            "canonical_text": "Explicit agent writes go through alice_memory_commit.",
            "memory_type": "decision",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )

    assert payload["status"] == "committed"
    assert payload["write_mode"] == "commit"
    memory_id = payload["memory"]["id"]
    assert payload["memory"]["memory_type"] == "decision"

    audit = call_mcp_tool(_mcp_context(), name="alice_explain", arguments={"memory_id": memory_id})
    assert audit["memory"]["id"] == memory_id
    assert audit["revisions"][0]["action"] == "agentic_memory_commit"
    assert any(event["event_type"] == "agent.memory_committed" for event in store.events)


def test_alice_memory_commit_defers_embedding_until_after_primary_transaction(monkeypatch) -> None:
    transaction_open = False
    calls: list[str] = []
    deferred_input = object()

    @contextmanager
    def fake_vnext_store_context(_context):
        nonlocal transaction_open
        transaction_open = True
        calls.append("primary_open")
        try:
            yield object()
        finally:
            transaction_open = False
            calls.append("primary_closed")

    class FakeMemoryCommitService:
        def __init__(self, _store, *, defer_embeddings: bool = False) -> None:
            assert transaction_open is True
            assert defer_embeddings is True
            self.deferred_embedding_inputs = (deferred_input,)

        def commit(self, *, identity, request):
            assert transaction_open is True
            assert identity is None
            assert request.canonical_text == "Embedding work happens after commit."
            calls.append("commit")
            return {"status": "committed"}

    def fake_persist(_context, inputs, **_kwargs) -> None:
        assert transaction_open is False
        assert inputs == (deferred_input,)
        calls.append("embedding")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(mcp_tools_module, "VNextMemoryCommitService", FakeMemoryCommitService)
    monkeypatch.setattr(
        mcp_tools_module,
        "_persist_vnext_deferred_embedding_inputs",
        fake_persist,
    )

    payload = mcp_tools_module._handle_alice_vnext_commit_memory(
        _mcp_context(),
        {
            "title": "Transaction boundary",
            "canonical_text": "Embedding work happens after commit.",
        },
    )

    assert payload == {"status": "committed"}
    assert calls == ["primary_open", "commit", "primary_closed", "embedding"]


def test_alice_memory_review_defers_embedding_until_primary_transaction_closes(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = FakeVNextMCPStore()
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    transaction_depth = 0
    calls: list[str] = []

    @contextmanager
    def fake_vnext_store_context(_context):
        nonlocal transaction_depth
        transaction_depth += 1
        try:
            yield store
        finally:
            transaction_depth -= 1

    def fake_persist(_context, deferred_inputs, **_kwargs) -> None:
        assert transaction_depth == 0
        assert len(deferred_inputs) == 1
        calls.append("embedding")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(mcp_tools_module, "_persist_vnext_deferred_embedding_inputs", fake_persist)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={"review_item_id": memory_id, "action": "approve"},
    )

    assert payload["memory"]["status"] == "active"
    assert calls == ["embedding"]


def test_alice_consolidation_defers_embedding_until_primary_transaction_closes(monkeypatch) -> None:
    transaction_depth = 0
    calls: list[str] = []
    deferred_input = object()

    @contextmanager
    def fake_vnext_store_context(_context):
        nonlocal transaction_depth
        transaction_depth += 1
        try:
            yield object()
        finally:
            transaction_depth -= 1

    class FakeMemoryService:
        def __init__(self, _store, *, defer_embeddings: bool = False) -> None:
            assert transaction_depth == 1
            assert defer_embeddings is True
            self.deferred_embedding_inputs = (deferred_input,)

        def accept_consolidation_candidate(self, memory_id: str, **_kwargs):
            assert transaction_depth == 1
            calls.append("accept")
            return {"memory": {"id": memory_id, "status": "active"}}

    def fake_persist(_context, deferred_inputs, **_kwargs) -> None:
        assert transaction_depth == 0
        assert deferred_inputs == (deferred_input,)
        calls.append("embedding")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(mcp_tools_module, "VNextMemoryCommitService", FakeMemoryService)
    monkeypatch.setattr(mcp_tools_module, "_persist_vnext_deferred_embedding_inputs", fake_persist)

    payload = mcp_tools_module._handle_alice_vnext_accept_consolidation(
        _mcp_context(),
        {"memory_id": "memory-1", "reason": "Merge duplicates."},
    )

    assert payload["memory"]["status"] == "active"
    assert calls == ["accept", "embedding"]


def test_alice_project_review_defers_embedding_until_primary_transaction_closes(monkeypatch) -> None:
    transaction_depth = 0
    calls: list[str] = []
    deferred_input = object()

    @contextmanager
    def fake_vnext_store_context(_context):
        nonlocal transaction_depth
        transaction_depth += 1
        try:
            yield object()
        finally:
            transaction_depth -= 1

    class FakeProjectService:
        def __init__(self, _store, *, defer_embeddings: bool = False) -> None:
            assert transaction_depth == 1
            assert defer_embeddings is True
            self.deferred_embedding_inputs = (deferred_input,)

        def review_project_update(self, **_kwargs):
            assert transaction_depth == 1
            calls.append("review")
            return {"id": "artifact-1", "status": "accepted"}

    def fake_persist(_context, deferred_inputs, **_kwargs) -> None:
        assert transaction_depth == 0
        assert deferred_inputs == (deferred_input,)
        calls.append("embedding")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_vnext_store_context)
    monkeypatch.setattr(mcp_tools_module, "VNextProjectService", FakeProjectService)
    monkeypatch.setattr(mcp_tools_module, "_persist_vnext_deferred_embedding_inputs", fake_persist)

    payload = mcp_tools_module._handle_alice_project_update_review(
        _mcp_context(),
        {"artifact_id": "artifact-1", "action": "accept"},
    )

    assert payload["status"] == "accepted"
    assert calls == ["review", "embedding"]


def test_alice_memory_commit_outcome_vocabulary(monkeypatch, core_surface, no_embedding_provider) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    direct = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={"title": "No identity", "canonical_text": "Direct human commits need no agent identity."},
    )
    assert direct["status"] == "committed"
    assert direct["write_mode"] == "commit"
    assert direct["policy_decision"]["policy_decision"]["permission_profile"] == "user_or_system"

    rejected = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            "agent_id": "unknown-agent",
            "title": "Read-only agent",
            "canonical_text": "Self-declared unknown agents still cannot write.",
        },
    )
    assert rejected["status"] == "rejected"
    assert rejected["write_mode"] == "reject"
    assert "read_only_agent_cannot_write" in rejected["reasons"]

    review = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Low confidence",
            "canonical_text": "Uncertain facts go to human review.",
            "confidence": 0.3,
        },
    )
    assert review["status"] == "review_required"
    assert review["write_mode"] == "propose_review"
    assert review["memory"]["status"] == "candidate"

    confirmation = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Sensitive memory",
            "canonical_text": "Health facts need inline confirmation.",
            "domain": "health",
            "sensitivity": "confidential",
            "confidence": 0.95,
        },
    )
    assert confirmation["status"] == "confirmation_required"
    assert confirmation["write_mode"] == "confirm_inline"
    assert confirmation["confirmation_id"]


def test_alice_memory_manage_confirms_a_pending_commit(monkeypatch, core_surface, no_embedding_provider) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    confirmation = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Pending confirmation",
            "canonical_text": "Sensitive content awaits confirmation.",
            "domain": "health",
            "sensitivity": "confidential",
            "confidence": 0.95,
        },
    )
    assert confirmation["status"] == "confirmation_required"

    confirmed = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_manage",
        arguments={
            **_trusted_identity_arguments(),
            "action": "confirm",
            "confirmation_id": confirmation["confirmation_id"],
        },
    )
    assert confirmed["status"] == "committed"
    assert confirmed["memory"]["status"] == "active"


def test_alice_memory_manage_confirm_with_text_records_a_correction(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    confirmation = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Pending confirmation",
            "canonical_text": "Original proposed text.",
            "domain": "health",
            "sensitivity": "confidential",
            "confidence": 0.95,
        },
    )

    confirmed = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_manage",
        arguments={
            **_trusted_identity_arguments(),
            "action": "confirm",
            "confirmation_id": confirmation["confirmation_id"],
            "canonical_text": "Corrected text confirmed by the user.",
            "reason": "User rephrased the fact",
        },
    )
    assert confirmed["status"] == "committed"
    assert confirmed["memory"]["canonical_text"] == "Corrected text confirmed by the user."
    assert store.revisions[-1]["revision_type"] == "corrected"
    assert store.revisions[-1]["reason"] == "User rephrased the fact"


def _seed_pending_inline_confirmation(store: FakeVNextMCPStore) -> tuple[str, str]:
    """Seed a row shaped exactly like ``_create_confirmation`` output.

    The review path requires UUID ids, so this mirrors the commit service's
    inline-confirmation row (status ``needs_review``, nested confirmation flag
    ``pending``) with a real UUID.
    """
    memory_id = str(uuid4())
    confirmation_id = f"confirm-{uuid4()}"
    text = "A fact that awaits inline confirmation."
    store.memories.append(
        {
            "id": memory_id,
            "memory_key": f"capture.pending.{uuid4().hex[:8]}",
            "value": {"text": text},
            "source_event_ids": [],
            "status": "needs_review",
            "confirmation_status": "unconfirmed",
            "confirmation_id": confirmation_id,
            "memory_type": "semantic",
            "confidence": 0.7,
            "title": "Pending fact",
            "canonical_text": text,
            "summary": text,
            "domain": "professional",
            "sensitivity": "internal",
            "project_id": None,
            "metadata_json": {
                "agentic_memory": {
                    "kind": "agentic_memory_commit",
                    "status": "confirmation_required",
                    "write_mode": "confirm_inline",
                    "lifecycle_status": "pending_inline_confirmation",
                    "confirmation": {
                        "confirmation_id": confirmation_id,
                        "status": "pending",
                        "expires_at": "2099-01-01T00:00:00Z",
                        "proposed_text": text,
                    },
                }
            },
        }
    )
    return memory_id, confirmation_id


def test_review_approval_closes_nested_inline_confirmation_metadata(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)

    approved = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "approve",
            "reason": "Reviewer accepted the pending fact.",
        },
    )

    agentic = approved["memory"]["metadata_json"]["agentic_memory"]
    assert approved["memory"]["status"] == "active"
    assert agentic["confirmation"]["status"] == "confirmed"
    assert agentic["confirmation"]["confirmed_at"]


def test_review_edit_synchronizes_text_views_and_honors_provenance(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    class ProvenanceStore(FakeVNextMCPStore):
        def __init__(self) -> None:
            super().__init__()
            self.created_provenance_links: list[dict[str, object]] = []

        def get_source(self, source_id: str) -> dict[str, object] | None:
            return next((row for row in self.sources if row.get("id") == source_id), None)

        def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
            row = {**link, "id": f"provenance-{len(self.created_provenance_links) + 1}"}
            self.created_provenance_links.append(row)
            return row

    store = ProvenanceStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    source_id = str(uuid4())
    store.sources.append({"id": source_id, "content_hash": "sha256:review-source"})
    corrected = "The corrected fact now matches its reviewed source."

    result = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "edit-and-approve",
            "body": {"text": corrected},
            "provenance": {"source_id": source_id, "evidence_role": "supports"},
        },
    )

    memory = result["memory"]
    assert memory["canonical_text"] == corrected
    assert memory["title"] == corrected
    assert memory["summary"] == corrected
    assert memory["metadata_json"]["provenance"]["source_id"] == source_id
    assert store.created_provenance_links[0]["source_id"] == source_id


@pytest.mark.parametrize(
    "provenance_factory, error_pattern",
    [
        (
            lambda source_id, _chunk_id: {
                "source_id": str(uuid4()),
                "evidence_role": "supports",
            },
            "was not found in the current user scope",
        ),
        (
            lambda source_id, _chunk_id: {
                "source_id": source_id,
                "source_chunk_id": str(uuid4()),
                "evidence_role": "supports",
            },
            "does not belong to source",
        ),
        (
            lambda source_id, _chunk_id: {
                "source_id": source_id,
                "evidence_role": "untrusted_role",
            },
            "evidence_role must be one of",
        ),
        (
            lambda source_id, _chunk_id: {
                "source_id": source_id,
                "evidence_role": "supports",
                "confidence": 1.5,
            },
            "confidence must be between 0 and 1",
        ),
    ],
)
def test_invalid_review_provenance_is_atomic_before_candidate_activation(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    provenance_factory,
    error_pattern: str,
) -> None:
    class ProvenanceValidationStore(FakeVNextMCPStore):
        def __init__(self) -> None:
            super().__init__()
            self.created_provenance_links: list[dict[str, object]] = []

        def get_source(self, source_id: str) -> dict[str, object] | None:
            return next((row for row in self.sources if row.get("id") == source_id), None)

        def list_source_chunks(self, source_id: str) -> list[dict[str, object]]:
            return [row for row in self.chunks if row.get("source_id") == source_id]

        def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
            self.created_provenance_links.append(dict(link))
            return dict(link)

    store = ProvenanceValidationStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    source_id = str(uuid4())
    chunk_id = str(uuid4())
    store.sources.append({"id": source_id, "content_hash": "sha256:review-source"})
    store.chunks.append({"id": chunk_id, "source_id": source_id})
    before = deepcopy(store.get_memory(memory_id))

    with pytest.raises(MCPToolError, match=error_pattern):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={
                "review_item_id": memory_id,
                "action": "edit-and-approve",
                "provenance": provenance_factory(source_id, chunk_id),
            },
        )

    assert store.get_memory(memory_id) == before
    assert store.created_provenance_links == []
    assert store.revisions == []


def test_review_provenance_validates_chunk_ownership_before_activation(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    class ChunkedProvenanceStore(FakeVNextMCPStore):
        def __init__(self) -> None:
            super().__init__()
            self.created_provenance_links: list[dict[str, object]] = []

        def get_source(self, source_id: str) -> dict[str, object] | None:
            return next((row for row in self.sources if row.get("id") == source_id), None)

        def list_source_chunks(self, source_id: str) -> list[dict[str, object]]:
            return [row for row in self.chunks if row.get("source_id") == source_id]

        def create_provenance_link(self, link: dict[str, object], **_kwargs) -> dict[str, object]:
            self.created_provenance_links.append(dict(link))
            return dict(link)

    store = ChunkedProvenanceStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)
    source_id = str(uuid4())
    chunk_id = str(uuid4())
    store.sources.append({"id": source_id, "content_hash": "sha256:review-source"})
    store.chunks.append({"id": chunk_id, "source_id": source_id})

    result = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "edit-and-approve",
            "provenance": {
                "source_id": source_id,
                "source_chunk_id": chunk_id,
                "evidence_role": "quoted_from",
                "confidence": 0.88,
                "quote": "Reviewed source quote.",
            },
        },
    )

    assert result["memory"]["status"] == "active"
    assert store.created_provenance_links == [
        {
            "target_type": "memory",
            "target_id": memory_id,
            "source_id": source_id,
            "source_chunk_id": chunk_id,
            "quote": "Reviewed source quote.",
            "evidence_role": "quoted_from",
            "confidence": 0.88,
        }
    ]


def test_review_supersession_locks_graph_before_target_row(monkeypatch, core_surface, no_embedding_provider) -> None:
    class OrderedLockStore(FakeVNextMCPStore):
        def __init__(self) -> None:
            super().__init__()
            self.lock_order: list[str] = []

        def lock_graph_mutation(self) -> None:
            self.lock_order.append("graph")

        def get_memory_for_update(self, memory_id: str) -> dict[str, object] | None:
            self.lock_order.append(f"row:{memory_id}")
            return self.get_memory(memory_id)

    store = OrderedLockStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)

    call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "supersede-existing",
            "replacement_title": "Fresh fact",
            "replacement_body": {"text": "The corrected replacement value."},
            "reason": "Reviewer replaced the pending fact.",
        },
    )

    assert store.lock_order == ["graph", f"row:{memory_id}"]


@pytest.mark.parametrize(
    "action_arguments",
    [
        {"action": "approve"},
        {"action": "edit-and-approve", "body": {"text": "Reviewed edit."}},
        {"action": "reject"},
    ],
)
def test_every_non_superseding_review_action_locks_graph_before_target_row(
    monkeypatch,
    core_surface,
    no_embedding_provider,
    action_arguments: dict[str, object],
) -> None:
    class OrderedLockStore(FakeVNextMCPStore):
        def __init__(self) -> None:
            super().__init__()
            self.lock_order: list[str] = []

        def lock_graph_mutation(self) -> None:
            self.lock_order.append("graph")

        def get_memory_for_update(self, memory_id: str) -> dict[str, object] | None:
            self.lock_order.append(f"row:{memory_id}")
            return self.get_memory(memory_id)

    store = OrderedLockStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, _confirmation_id = _seed_pending_inline_confirmation(store)

    call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={"review_item_id": memory_id, **action_arguments},
    )

    assert store.lock_order == ["graph", f"row:{memory_id}"]


def test_review_rejection_then_confirm_cannot_reactivate_the_memory(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    """Audit #1(a) end-to-end: a review rejection must not be undone by confirm."""
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, confirmation_id = _seed_pending_inline_confirmation(store)

    rejected = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "reject",
            "reason": "Reviewer rejected the pending fact.",
        },
    )
    assert rejected["memory"]["status"] == "rejected"

    # Confirming the rejected row must be impossible.
    with pytest.raises(MCPToolError):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_manage",
            arguments={
                "action": "confirm",
                "confirmation_id": confirmation_id,
            },
        )
    assert store.get_memory(memory_id)["status"] == "rejected"


def test_review_supersede_then_confirm_cannot_create_two_active_memories(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    """Audit #1(b) end-to-end: a superseded row must not be reconfirmed to active."""
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)
    memory_id, confirmation_id = _seed_pending_inline_confirmation(store)

    superseded = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_correct",
        arguments={
            "review_item_id": memory_id,
            "action": "supersede-existing",
            "replacement_title": "Fresh fact",
            "replacement_body": {"text": "The corrected replacement value."},
            "reason": "Reviewer replaced the pending fact.",
        },
    )
    assert superseded["memory"]["status"] == "superseded"
    replacement_id = superseded["replacement_object"]["id"]

    with pytest.raises(MCPToolError):
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_manage",
            arguments={
                "action": "confirm",
                "confirmation_id": confirmation_id,
            },
        )
    assert store.get_memory(memory_id)["status"] == "superseded"
    active_ids = {row["id"] for row in store.memories if row.get("status") == "active"}
    assert memory_id not in active_ids
    assert replacement_id in active_ids


def test_alice_memory_manage_undo_and_forget_keep_the_audit_trail(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    first = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Undo target",
            "canonical_text": "This commit will be undone.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )

    # Undo without memory_id targets the calling agent's most recent commit.
    undone = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_manage",
        arguments={**_trusted_identity_arguments(), "action": "undo", "reason": "wrong fact"},
    )
    assert undone["status"] == "undone"
    assert undone["memory"]["id"] == first["memory"]["id"]
    assert undone["memory"]["status"] == "superseded"

    second = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Forget target",
            "canonical_text": "This commit will be forgotten.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    forgotten = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_manage",
        arguments={
            **_trusted_identity_arguments(),
            "action": "forget",
            "memory_id": second["memory"]["id"],
            "reason": "user asked to forget",
        },
    )
    assert forgotten["status"] == "forgotten"
    assert forgotten["memory"]["status"] == "superseded"

    # Forget is a soft retirement: revisions and events survive for audit.
    audit = call_mcp_tool(_mcp_context(), name="alice_explain", arguments={"memory_id": second["memory"]["id"]})
    assert [revision["revision_type"] for revision in audit["revisions"]] == ["created", "archived"]
    assert any(event["event_type"] == "agent.memory_forgotten" for event in store.events)


def test_alice_memory_manage_undo_links_the_replacing_memory(monkeypatch, core_surface, no_embedding_provider) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    original = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Stale fact",
            "canonical_text": "The standup is at 10am.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    replacement = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_commit",
        arguments={
            **_trusted_identity_arguments(),
            "title": "Fresh fact",
            "canonical_text": "The standup moved to 9am.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    old_id = str(original["memory"]["id"])
    new_id = str(replacement["memory"]["id"])

    undone = call_mcp_tool(
        _mcp_context(),
        name="alice_memory_manage",
        arguments={
            **_trusted_identity_arguments(),
            "action": "undo",
            "memory_id": old_id,
            "reason": "standup moved",
            "superseded_by": new_id,
        },
    )
    assert undone["status"] == "undone"
    assert undone["memory"]["status"] == "superseded"

    # Both rows carry real pointer columns plus the metadata copies.
    old_row = store.get_memory(old_id)
    new_row = store.get_memory(new_id)
    assert old_row["superseded_by"] == new_id
    assert new_row["supersedes"] == old_id
    assert old_row["metadata_json"]["superseded_by"] == new_id
    assert new_row["metadata_json"]["supersedes"] == old_id

    # alice_explain surfaces the linked history from either side.
    explained = call_mcp_tool(_mcp_context(), name="alice_explain", arguments={"memory_id": old_id})
    assert [(entry["id"], entry["relation"]) for entry in explained["supersession_chain"]] == [
        (old_id, "self"),
        (new_id, "successor"),
    ]
    from_new = call_mcp_tool(_mcp_context(), name="alice_explain", arguments={"memory_id": new_id})
    assert [(entry["id"], entry["relation"]) for entry in from_new["supersession_chain"]] == [
        (old_id, "predecessor"),
        (new_id, "self"),
    ]


def test_alice_memory_manage_rejects_unknown_actions(monkeypatch, core_surface) -> None:
    def fail_if_store_opened(_context):
        raise AssertionError("store should not be opened for an invalid action")

    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fail_if_store_opened)

    with pytest.raises(MCPToolError, match="action must be one of"):
        call_mcp_tool(_mcp_context(), name="alice_memory_manage", arguments={"action": "erase"})
    with pytest.raises(MCPToolError, match="action must be one of"):
        call_mcp_tool(_mcp_context(), name="alice_memory_manage", arguments={})


def test_new_core_tool_schemas_reuse_canonical_enums(core_surface) -> None:
    from alicebot_api.vnext_memory_commit import VNEXT_MEMORY_TYPES

    tools = {tool["name"]: tool for tool in list_mcp_tools()}

    commit_schema = tools["alice_memory_commit"]["inputSchema"]
    assert commit_schema["required"] == ["title", "canonical_text"]
    assert commit_schema["properties"]["memory_type"]["enum"] == list(VNEXT_MEMORY_TYPES)

    manage_schema = tools["alice_memory_manage"]["inputSchema"]
    assert manage_schema["required"] == ["action"]
    assert manage_schema["properties"]["action"]["enum"] == [
        "confirm",
        "undo",
        "forget",
        "expire",
        "unexpire",
        "accept_consolidation",
        "redact",
    ]
    assert "valid_to" in manage_schema["properties"]

    from alicebot_api.vnext_retrieval import BUDGET_STRATEGIES, CONTEXT_DEPTHS

    for tool_name in ("alice_recall", "alice_context_pack"):
        tuning_properties = tools[tool_name]["inputSchema"]["properties"]
        assert tuning_properties["context_depth"]["enum"] == list(CONTEXT_DEPTHS)
        assert tuning_properties["budget_strategy"]["enum"] == list(BUDGET_STRATEGIES)

    for tool_name in ("alice_recall", "alice_context_pack"):
        memory_types_schema = tools[tool_name]["inputSchema"]["properties"]["memory_types"]
        assert memory_types_schema["items"]["enum"] == list(VNEXT_MEMORY_TYPES)
        created_by_schema = tools[tool_name]["inputSchema"]["properties"]["created_by_agents"]
        assert created_by_schema["type"] == "array"
        assert created_by_schema["items"] == {"type": "string"}
        assert "agent ids" in created_by_schema["description"]
    assert "projects" in tools["alice_recall"]["inputSchema"]["properties"]


def test_alice_capture_stores_reviewable_source_evidence(monkeypatch, core_surface, no_embedding_provider) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    payload = call_mcp_tool(
        _mcp_context(),
        name="alice_capture",
        arguments={
            "raw_text": "Decision: The default MCP surface is nine tools.",
            "title": "MCP surface decision",
            "domain": "project",
            "sensitivity": "private",
        },
    )

    assert payload["status"] == "imported"
    assert payload["source_id"] == "source-1"
    assert payload["chunk_count"] >= 1
    assert store.sources[0]["title"] == "MCP surface decision"
    assert any(event["event_type"] == "source.captured" for event in store.events)


def _sqlite_mcp_store() -> SQLiteVNextStore:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, "capture-scope-mcp@example.com")
    return SQLiteVNextStore(conn, user_id)


def test_alice_capture_threads_project_scoped_agent_scope_into_recall(
    monkeypatch, core_surface, no_embedding_provider
) -> None:
    # Audit P1 #4: a project-scoped agent's alice_capture validated the bound
    # scope but, before the fix, dropped it into capture -- the memory persisted
    # with an empty scope, so the owning project's filtered recall found nothing.
    # A real SQLite store exercises the recall filter end to end.
    store = _sqlite_mcp_store()
    _patch_vnext_store(monkeypatch, store)
    context = _resolved_scoped_agent_context(profile="project_scoped_agent", project="project-helios")

    payload = call_mcp_tool(
        context,
        name="alice_capture",
        arguments={
            "raw_text": "Decision: The Helios launch ships behind a staged rollout flag.",
            "title": "Helios launch decision",
            "domain": "project",
            "sensitivity": "internal",
        },
    )
    assert payload["status"] == "imported"

    candidates = store.list_memories(status="candidate")
    assert candidates, "capture must promote at least one candidate memory"
    assert memory_project_scope(candidates[0]) == ("project-helios",)
    for memory in candidates:
        store.update_memory(memory_id=str(memory["id"]), patch={"status": "active"}, actor_type="system")

    owning = store.search_memories_fts(query="Helios staged rollout", projects=("project-helios",), limit=10)
    other = store.search_memories_fts(query="Helios staged rollout", projects=("project-decoy",), limit=10)
    unscoped = store.search_memories_fts(query="Helios staged rollout", limit=10)

    assert len(owning) == 1, "the owning project's filtered recall must retrieve the captured memory"
    assert len(other) == 0, "another project must not see the captured memory"
    assert len(unscoped) == 1


def test_alice_open_loops_lists_and_manages_loops(monkeypatch, core_surface) -> None:
    store = FakeVNextMCPStore()
    store.create_open_loop({"title": "Follow up with tester", "status": "open", "domain": "project"})
    _patch_vnext_store(monkeypatch, store)

    listed = call_mcp_tool(_mcp_context(), name="alice_open_loops", arguments={})
    assert listed["count"] == 1
    assert listed["items"][0]["id"] == "loop-1"

    closed = call_mcp_tool(
        _mcp_context(),
        name="alice_open_loops",
        arguments={"action": "close", "loop_id": "loop-1", "resolution_note": "Tester replied."},
    )
    assert closed["action"] == "close"
    assert closed["open_loop"]["status"] == "resolved"
    assert closed["open_loop"]["resolution_note"] == "Tester replied."

    with pytest.raises(MCPToolError, match="action must be one of"):
        call_mcp_tool(_mcp_context(), name="alice_open_loops", arguments={"action": "archive"})
    with pytest.raises(MCPToolError, match="loop_id"):
        call_mcp_tool(_mcp_context(), name="alice_open_loops", arguments={"action": "close"})


@pytest.mark.parametrize("profile", ["read_only_agent", "memory_proposal_agent"])
def test_non_mutating_agent_profiles_cannot_change_open_loops(monkeypatch, core_surface, profile: str) -> None:
    store = FakeVNextMCPStore()
    store.create_open_loop({"title": "Protected follow-up", "status": "open", "domain": "project"})
    _patch_vnext_store(monkeypatch, store)

    with pytest.raises(MCPToolError, match="cannot_(?:write|mutate)"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_open_loops",
            arguments={
                "agent_id": "limited-agent",
                "permission_profile": profile,
                "action": "close",
                "loop_id": "loop-1",
            },
        )
    assert store.get_open_loop("loop-1")["status"] == "open"


def test_alice_explain_routes_memory_id_to_memory_audit(monkeypatch, core_surface) -> None:
    store = FakeVNextMCPStore()
    store.create_memory(
        {
            "memory_type": "semantic",
            "canonical_text": "Hybrid retrieval is the default recall path.",
            "status": "active",
        }
    )
    memory_id = store.memories[0]["id"]
    _patch_vnext_store(monkeypatch, store)

    payload = call_mcp_tool(_mcp_context(), name="alice_explain", arguments={"memory_id": memory_id})

    assert payload["memory"]["id"] == memory_id
    for section in ("supersession_chain", "revisions", "events", "provenance_links"):
        assert section in payload
    # No supersession happened, so the chain is just the memory itself.
    assert [(entry["id"], entry["relation"]) for entry in payload["supersession_chain"]] == [(memory_id, "self")]

    with pytest.raises(MCPToolError, match="exactly one"):
        call_mcp_tool(
            _mcp_context(),
            name="alice_explain",
            arguments={"memory_id": memory_id, "entity_id": str(uuid4())},
        )


def test_alice_resume_reports_legacy_debug_flag_as_ignored(monkeypatch, core_surface) -> None:
    store = FakeVNextMCPStore()
    _patch_vnext_store(monkeypatch, store)

    payload = call_mcp_tool(_mcp_context(), name="alice_resume", arguments={"debug": True})
    assert payload["brief"]["mode"] == "vnext"
    assert "debug" in payload["brief"]["filters_ignored"]

    payload = call_mcp_tool(_mcp_context(), name="alice_resume", arguments={})
    assert payload["brief"]["filters_ignored"] == []


def test_mcp_server_initialize_and_tools_list(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    server = mcp_server.MCPServer(context=context, input_stream=BytesIO(), output_stream=BytesIO())

    initialize_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }
    )
    assert initialize_response is not None
    assert initialize_response["result"]["protocolVersion"] == "2024-11-05"
    assert initialize_response["result"]["serverInfo"]["name"] == "alice-core-mcp"

    monkeypatch.setattr(
        mcp_server,
        "list_mcp_tools",
        lambda: [{"name": "alice_recall", "description": "Recall", "inputSchema": {"type": "object"}}],
    )
    list_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
    )
    assert list_response is not None
    assert list_response["result"]["tools"] == [
        {"name": "alice_recall", "description": "Recall", "inputSchema": {"type": "object"}}
    ]


def test_mcp_runtime_flags_precede_scoped_production_validation(monkeypatch) -> None:
    user_id = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(
        mcp_server,
        "get_settings",
        lambda: (_ for _ in ()).throw(AssertionError("cached full settings must not load")),
    )
    args = mcp_server.build_parser().parse_args(
        [
            "--database-url",
            "postgresql://runtime:secret@db/alice",
            "--user-id",
            user_id,
        ]
    )

    context = mcp_server._build_runtime_context(args)

    assert context.database_url == "postgresql://runtime:secret@db/alice"
    assert context.user_id == UUID(user_id)


def test_mcp_runtime_accepts_environment_only_production_configuration(
    monkeypatch,
) -> None:
    user_id = "11111111-1111-4111-8111-111111111111"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://runtime:secret@db/alice")
    monkeypatch.setenv("ALICEBOT_AUTH_USER_ID", user_id)
    for key in (
        "DATABASE_ADMIN_URL",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "TELEGRAM_WEBHOOK_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        mcp_server,
        "get_settings",
        lambda: (_ for _ in ()).throw(AssertionError("hosted settings must not load")),
    )

    context = mcp_server._build_runtime_context(mcp_server.build_parser().parse_args([]))

    assert context.database_url == "postgresql://runtime:secret@db/alice"
    assert context.user_id == UUID(user_id)


def test_mcp_server_tools_call_success_and_error_paths(monkeypatch) -> None:
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    server = mcp_server.MCPServer(context=context, input_stream=BytesIO(), output_stream=BytesIO())

    monkeypatch.setattr(mcp_server, "call_mcp_tool", lambda *_args, **_kwargs: {"ok": True})
    success_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "alice_recall", "arguments": {}},
        }
    )
    assert success_response is not None
    assert success_response["result"]["isError"] is False
    # The payload is serialized exactly once: JSON text in content, no
    # duplicate structuredContent copy.
    assert json.loads(success_response["result"]["content"][0]["text"]) == {"ok": True}
    assert "structuredContent" not in success_response["result"]

    def raise_tool_error(*_args, **_kwargs):
        raise MCPToolError("invalid input")

    monkeypatch.setattr(mcp_server, "call_mcp_tool", raise_tool_error)
    error_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "alice_recall", "arguments": {}},
        }
    )
    assert error_response is not None
    assert error_response["result"]["isError"] is True
    assert error_response["result"]["content"][0]["text"] == "invalid input"

    def raise_unexpected_error(*_args, **_kwargs):
        raise RuntimeError("database connection dropped")

    monkeypatch.setattr(mcp_server, "call_mcp_tool", raise_unexpected_error)
    unexpected_response = server._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {"name": "alice_vnext_commit_memory", "arguments": {}},
        }
    )
    assert unexpected_response is not None
    assert unexpected_response["result"]["isError"] is True
    assert "Tool execution failed unexpectedly" in unexpected_response["result"]["content"][0]["text"]


class FakeAgentKeyStore:
    """Minimal AgentKeyStore fake for MCP identity resolution tests."""

    def __init__(self, record: dict[str, object] | None) -> None:
        self.record = record
        self.events: list[dict[str, object]] = []

    def append_event(self, event: dict[str, object]) -> dict[str, object]:
        self.events.append(event)
        return event

    def get_agent_api_key_by_hash(self, key_hash: str) -> dict[str, object] | None:
        if self.record is not None and self.record.get("key_hash") == key_hash:
            return dict(self.record)
        return None

    def touch_agent_api_key(self, *, key_id: str) -> dict[str, object]:
        assert self.record is not None and str(self.record["id"]) == key_id
        return dict(self.record)

    def count_active_agent_api_keys(self) -> int:
        return 1 if self.record is not None else 0


def _key_bound_context_and_store(monkeypatch, *, profile: str = "trusted_local_agent"):
    from contextlib import contextmanager

    from alicebot_api import vnext_agent_keys

    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    raw_key = "alice_sk_test-mcp-key"
    store = FakeAgentKeyStore(
        {
            "id": "22222222-2222-4222-8222-222222222222",
            "user_id": str(context.user_id),
            "agent_id": "hermes",
            "permission_profile": profile,
            "key_hash": vnext_agent_keys.hash_agent_key(raw_key),
            "key_prefix": raw_key[:12],
            "revoked_at": None,
        }
    )

    @contextmanager
    def fake_store_context(_context):
        yield store

    monkeypatch.setenv(mcp_tools_module.AGENT_API_KEY_ENV, raw_key)
    monkeypatch.setattr(mcp_tools_module, "_vnext_store_context", fake_store_context)
    return context, store


def test_agent_identity_without_key_env_is_self_asserted_local(monkeypatch) -> None:
    monkeypatch.delenv(mcp_tools_module.AGENT_API_KEY_ENV, raising=False)
    context = MCPRuntimeContext(
        database_url="postgresql://localhost/alicebot",
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    identity = mcp_tools_module._agent_identity_from_arguments(
        context, {"agent_id": "hermes", "permission_profile": "trusted_local_agent"}
    )
    assert identity is not None
    assert identity.agent_id == "hermes"
    assert identity.auth == "unauthenticated_local"


def test_agent_identity_with_key_env_binds_to_key_record(monkeypatch) -> None:
    context, _store = _key_bound_context_and_store(monkeypatch)
    identity = mcp_tools_module._agent_identity_from_arguments(context, {})
    assert identity is not None
    assert identity.agent_id == "hermes"
    assert identity.permission_profile == "trusted_local_agent"
    assert identity.auth == "agent_api_key"


@pytest.mark.parametrize("tool_name", CORE_TOOL_NAMES)
def test_every_core_mcp_tool_authenticates_the_configured_agent_key(monkeypatch, tool_name: str) -> None:
    context, _store = _key_bound_context_and_store(monkeypatch)
    captured: dict[str, object] = {}

    def handler(resolved_context, _arguments):
        captured["identity"] = resolved_context.agent_identity
        captured["resolved"] = resolved_context.agent_identity_resolved
        return {"ok": True}

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, tool_name, handler)

    assert call_mcp_tool(context, name=tool_name, arguments={}) == {"ok": True}
    identity = captured["identity"]
    assert identity is not None
    assert identity.agent_id == "hermes"
    assert identity.auth == "agent_api_key"
    assert captured["resolved"] is True


def test_core_mcp_authentication_fails_before_the_tool_handler(monkeypatch) -> None:
    context, _store = _key_bound_context_and_store(monkeypatch)
    monkeypatch.setenv(mcp_tools_module.AGENT_API_KEY_ENV, "alice_sk_wrong-key")

    def should_not_run(_context, _arguments):
        raise AssertionError("tool handler must not run before authentication")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_recall", should_not_run)

    with pytest.raises(MCPToolError, match="invalid or has been revoked"):
        call_mcp_tool(context, name="alice_recall", arguments={})


def test_key_bound_mcp_server_hides_and_rejects_the_legacy_surface(monkeypatch) -> None:
    context, _store = _key_bound_context_and_store(monkeypatch)
    monkeypatch.setenv(mcp_tools_module.MCP_LEGACY_TOOLS_ENV, "1")

    listed = {str(tool["name"]) for tool in list_mcp_tools()}
    assert listed == set(CORE_TOOL_NAMES)
    assert "alice_recall_debug" not in listed

    def should_not_run(_context, _arguments):
        raise AssertionError("legacy handler must not run on a key-bound server")

    monkeypatch.setitem(mcp_tools_module._TOOL_HANDLERS, "alice_recall_debug", should_not_run)
    with pytest.raises(MCPToolNotFoundError, match="disabled whenever ALICE_AGENT_API_KEY"):
        call_mcp_tool(context, name="alice_recall_debug", arguments={})


def test_agent_identity_with_key_env_rejects_profile_escalation(monkeypatch) -> None:
    context, store = _key_bound_context_and_store(monkeypatch, profile="project_scoped_agent")
    with pytest.raises(MCPToolError, match="which is higher"):
        mcp_tools_module._agent_identity_from_arguments(
            context, {"agent_id": "hermes", "permission_profile": "admin_agent"}
        )
    assert any("escalation" in str(event) for event in store.events)


def test_agent_identity_with_key_env_rejects_agent_id_mismatch(monkeypatch) -> None:
    context, _store = _key_bound_context_and_store(monkeypatch)
    with pytest.raises(MCPToolError, match="issued to agent 'hermes'"):
        mcp_tools_module._agent_identity_from_arguments(
            context, {"agent_id": "openclaw", "permission_profile": "trusted_local_agent"}
        )


def test_alice_memory_correct_invalid_action_error_matches_schema_enum(core_surface) -> None:
    schema = {tool["name"]: tool for tool in list_mcp_tools()}["alice_memory_correct"]
    schema_enum = schema["inputSchema"]["properties"]["action"]["enum"]

    with pytest.raises(MCPToolError) as excinfo:
        call_mcp_tool(
            _mcp_context(),
            name="alice_memory_correct",
            arguments={"action": "not-an-action"},
        )

    expected = ", ".join(json.dumps(item) for item in schema_enum)
    assert str(excinfo.value) == (
        f"tool 'alice_memory_correct' has invalid value at arguments.action: action must be one of: {expected}"
    )
