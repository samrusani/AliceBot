"""SQLite on-ramp: MCP backend dispatch, core-tool behavior, and alice-memory CLI.

Everything here runs against temp-dir SQLite files; no Postgres, Redis, or
network services. One test spawns the real ``python -m alicebot_api.onramp``
process and speaks MCP over stdio.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from uuid import UUID

import pytest

import alicebot_api.mcp_tools as mcp_tools_module
from alicebot_api.mcp_tools import (
    MCPRuntimeContext,
    MCPToolError,
    _sqlite_path_from_url,
    _store_context,
    _vnext_store_context,
    call_mcp_tool,
)
from alicebot_api.onramp import (
    _normalized_argv,
    bootstrap_database,
    main as onramp_main,
    resolve_db_path,
    sqlite_url_for_path,
)
from alicebot_api.sqlite_store import SQLiteVNextStore, sqlite_user_connection
from alicebot_api.vnext_embeddings import (
    EMBEDDINGS_API_KEY_ENV,
    EMBEDDINGS_BASE_URL_ENV,
    EMBEDDINGS_MODEL_ENV,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
USER_ID = UUID("11111111-1111-4111-8111-111111111111")

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

TRUSTED_AGENT = {
    "agent_id": "hermes",
    "agent_type": "personal_assistant",
    "permission_profile": "trusted_local_agent",
}


@pytest.fixture
def sqlite_context(tmp_path, monkeypatch) -> MCPRuntimeContext:
    for env_name in (EMBEDDINGS_BASE_URL_ENV, EMBEDDINGS_MODEL_ENV, EMBEDDINGS_API_KEY_ENV):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.delenv(mcp_tools_module.MCP_LEGACY_TOOLS_ENV, raising=False)
    monkeypatch.delenv(mcp_tools_module.AGENT_API_KEY_ENV, raising=False)

    db_path = resolve_db_path(data_dir=str(tmp_path), db=None)
    bootstrap_database(db_path, user_id=USER_ID, user_email="local@alice")
    return MCPRuntimeContext(database_url=sqlite_url_for_path(db_path), user_id=USER_ID)


def _db_path(context: MCPRuntimeContext) -> str:
    return _sqlite_path_from_url(context.database_url)


def _capture_decision(context: MCPRuntimeContext, text: str) -> str:
    """Capture one 'Decision: ...' line and return the candidate memory id."""
    captured = call_mcp_tool(
        context,
        name="alice_capture",
        arguments={"raw_text": f"Decision: {text}", "domain": "project", "sensitivity": "internal"},
    )
    assert captured["status"] == "imported"
    assert captured["candidate_memory_count"] == 1

    review = call_mcp_tool(context, name="alice_memory_review", arguments={})
    for item in review["items"]:
        if item["memory_type"] == "decision" and text in str(item["canonical_text"]):
            return str(item["id"])
    raise AssertionError(f"captured decision candidate not found in review queue: {text}")


# --- backend dispatch ---------------------------------------------------------


def test_vnext_store_context_yields_sqlite_store_for_sqlite_urls(sqlite_context) -> None:
    with _vnext_store_context(sqlite_context) as store:
        assert isinstance(store, SQLiteVNextStore)
        assert store.user_id == str(USER_ID)


def test_store_context_raises_informative_error_in_sqlite_mode(sqlite_context) -> None:
    with pytest.raises(MCPToolError, match="requires the Postgres backend"):
        with _store_context(sqlite_context):
            pass


def test_legacy_tool_in_sqlite_mode_reports_postgres_requirement(sqlite_context, monkeypatch) -> None:
    monkeypatch.setenv(mcp_tools_module.MCP_LEGACY_TOOLS_ENV, "1")
    with pytest.raises(MCPToolError, match="requires the Postgres backend"):
        call_mcp_tool(sqlite_context, name="alice_brief", arguments={})


def test_sqlite_path_from_url_accepts_three_and_four_slash_forms() -> None:
    assert _sqlite_path_from_url("sqlite:///Users/x/.alice/memory.db") == "/Users/x/.alice/memory.db"
    assert _sqlite_path_from_url("sqlite:////Users/x/.alice/memory.db") == "/Users/x/.alice/memory.db"
    assert _sqlite_path_from_url("sqlite:///a/di%20r/m.db") == "/a/di r/m.db"
    with pytest.raises(MCPToolError, match="database file path"):
        _sqlite_path_from_url("sqlite:///")
    with pytest.raises(MCPToolError, match="sqlite"):
        _sqlite_path_from_url("postgresql://localhost/alicebot")


def test_sqlite_url_for_path_round_trips(tmp_path) -> None:
    db_path = tmp_path / "memory.db"
    assert _sqlite_path_from_url(sqlite_url_for_path(db_path)) == str(db_path)


# --- core tools end-to-end through call_mcp_tool ------------------------------


def test_capture_review_approve_recall_explain_flow(sqlite_context) -> None:
    memory_id = _capture_decision(sqlite_context, "Ship the SQLite on-ramp for local agents")

    # Candidate shows up in the review queue with compact fields.
    review = call_mcp_tool(sqlite_context, name="alice_memory_review", arguments={})
    assert review["mode"] == "vnext_candidates"
    assert review["count"] == 1
    item = review["items"][0]
    assert item["id"] == memory_id
    assert item["status"] == "candidate"
    assert item["provenance_count"] == 1

    # Candidates are not searchable until promoted.
    recall_before = call_mcp_tool(
        sqlite_context, name="alice_recall", arguments={"query": "SQLite on-ramp"}
    )
    assert recall_before["count"] == 0

    corrected = call_mcp_tool(
        sqlite_context,
        name="alice_memory_correct",
        arguments={"review_item_id": memory_id, "action": "approve", "reason": "Confirmed by user"},
    )
    assert corrected["mode"] == "vnext"
    assert corrected["review_action"] == {
        "requested_action": "approve",
        "resolved_action": "confirm",
        "memory_id": memory_id,
    }
    assert corrected["memory"]["status"] == "active"
    assert corrected["replacement_object"] is None

    recall = call_mcp_tool(
        sqlite_context,
        name="alice_recall",
        arguments={"query": "SQLite on-ramp", "debug": True},
    )
    assert recall["count"] >= 1
    assert recall["results"][0]["id"] == memory_id
    assert recall["results"][0]["provenance_count"] == 1
    assert recall["retrieval"]["fusion"] == {"algorithm": "reciprocal_rank_fusion", "k": 60}
    assert recall["retrieval"]["stages"]["fts"]["candidate_count"] >= 1

    audit = call_mcp_tool(sqlite_context, name="alice_explain", arguments={"memory_id": memory_id})
    assert set(audit) == {"memory", "revisions", "events", "provenance_links"}
    assert audit["memory"]["id"] == memory_id
    assert [revision["revision_type"] for revision in audit["revisions"]] == ["promoted"]
    assert any(event["event_type"] == "memory.reviewed" for event in audit["events"])
    assert audit["provenance_links"][0]["evidence_role"] == "quoted_from"


def test_context_pack_includes_promoted_memory(sqlite_context) -> None:
    memory_id = _capture_decision(sqlite_context, "Adopt reciprocal rank fusion for retrieval")
    call_mcp_tool(
        sqlite_context,
        name="alice_memory_correct",
        arguments={"review_item_id": memory_id, "action": "approve"},
    )
    pack = call_mcp_tool(
        sqlite_context,
        name="alice_context_pack",
        arguments={"query": "rank fusion retrieval"},
    )
    assert pack["query"] == "rank fusion retrieval"
    assert any(memory["id"] == memory_id for memory in pack["memories"])
    assert pack["context_pack_id"]
    assert pack["trace_id"]


def test_memory_commit_recall_undo_and_forget_flow(sqlite_context) -> None:
    committed = call_mcp_tool(
        sqlite_context,
        name="alice_memory_commit",
        arguments={
            **TRUSTED_AGENT,
            "title": "Espresso preference",
            "canonical_text": "Sami prefers a single espresso before standup.",
            "memory_type": "preference",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
            "rationale": "User said: remember this",
        },
    )
    assert committed["status"] == "committed"
    assert committed["write_mode"] == "commit"
    memory_id = str(committed["memory"]["id"])
    assert committed["memory"]["status"] == "active"
    assert committed["memory"]["memory_type"] == "preference"

    recall = call_mcp_tool(
        sqlite_context, name="alice_recall", arguments={"query": "espresso before standup"}
    )
    assert [row["id"] for row in recall["results"]] == [memory_id]

    typed = call_mcp_tool(
        sqlite_context,
        name="alice_recall",
        arguments={"query": "espresso before standup", "memory_types": ["preference"]},
    )
    assert [row["id"] for row in typed["results"]] == [memory_id]
    filtered_out = call_mcp_tool(
        sqlite_context,
        name="alice_recall",
        arguments={"query": "espresso before standup", "memory_types": ["decision"]},
    )
    assert filtered_out["count"] == 0

    audit = call_mcp_tool(sqlite_context, name="alice_explain", arguments={"memory_id": memory_id})
    assert [revision["revision_type"] for revision in audit["revisions"]] == ["created"]
    assert audit["revisions"][0]["action"] == "agentic_memory_commit"
    assert any(event["event_type"] == "agent.memory_committed" for event in audit["events"])

    undone = call_mcp_tool(
        sqlite_context,
        name="alice_memory_manage",
        arguments={**TRUSTED_AGENT, "action": "undo", "memory_id": memory_id, "reason": "Wrong fact"},
    )
    assert undone["status"] == "undone"
    assert undone["memory"]["status"] == "superseded"

    gone = call_mcp_tool(
        sqlite_context, name="alice_recall", arguments={"query": "espresso before standup"}
    )
    assert gone["count"] == 0

    second = call_mcp_tool(
        sqlite_context,
        name="alice_memory_commit",
        arguments={
            **TRUSTED_AGENT,
            "title": "Forgettable fact",
            "canonical_text": "The forgettable retro window is Thursdays.",
            "memory_type": "semantic",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    second_id = str(second["memory"]["id"])
    forgotten = call_mcp_tool(
        sqlite_context,
        name="alice_memory_manage",
        arguments={**TRUSTED_AGENT, "action": "forget", "memory_id": second_id, "reason": "User asked"},
    )
    assert forgotten["status"] == "forgotten"
    assert forgotten["memory"]["status"] == "superseded"

    # Forget is soft: the memory leaves recall, but revisions and the event
    # log keep the full history, including the original text.
    assert (
        call_mcp_tool(sqlite_context, name="alice_recall", arguments={"query": "forgettable retro"})[
            "count"
        ]
        == 0
    )
    forget_audit = call_mcp_tool(
        sqlite_context, name="alice_explain", arguments={"memory_id": second_id}
    )
    assert [revision["revision_type"] for revision in forget_audit["revisions"]] == [
        "created",
        "archived",
    ]
    assert forget_audit["revisions"][-1]["text_before"] == "The forgettable retro window is Thursdays."
    assert any(event["event_type"] == "agent.memory_forgotten" for event in forget_audit["events"])


def test_memory_commit_confirmation_flow(sqlite_context) -> None:
    pending = call_mcp_tool(
        sqlite_context,
        name="alice_memory_commit",
        arguments={
            **TRUSTED_AGENT,
            "title": "Health fact",
            "canonical_text": "Sami is allergic to penicillin.",
            "memory_type": "identity_fact",
            "domain": "health",
            "sensitivity": "confidential",
            "confidence": 0.95,
        },
    )
    assert pending["status"] == "confirmation_required"
    assert pending["write_mode"] == "confirm_inline"
    confirmation_id = pending["confirmation_id"]
    assert pending["memory"]["status"] == "needs_review"

    # Unconfirmed memories are not searchable.
    assert (
        call_mcp_tool(sqlite_context, name="alice_recall", arguments={"query": "penicillin"})["count"]
        == 0
    )

    confirmed = call_mcp_tool(
        sqlite_context,
        name="alice_memory_manage",
        arguments={**TRUSTED_AGENT, "action": "confirm", "confirmation_id": confirmation_id},
    )
    assert confirmed["status"] == "committed"
    assert confirmed["memory"]["status"] == "active"

    # Confidential content stays outside the default sensitivity gate and
    # must be requested explicitly.
    default_gate = call_mcp_tool(
        sqlite_context, name="alice_recall", arguments={"query": "penicillin"}
    )
    assert default_gate["count"] == 0
    recall = call_mcp_tool(
        sqlite_context,
        name="alice_recall",
        arguments={
            "query": "penicillin",
            "sensitivity_allowed": ["public", "internal", "private", "confidential"],
        },
    )
    assert recall["count"] == 1
    audit = call_mcp_tool(
        sqlite_context,
        name="alice_explain",
        arguments={"memory_id": str(confirmed["memory"]["id"])},
    )
    assert any(event["event_type"] == "agent.memory_confirmed" for event in audit["events"])


def test_memory_commit_review_required_lands_in_review_queue(sqlite_context) -> None:
    proposed = call_mcp_tool(
        sqlite_context,
        name="alice_memory_commit",
        arguments={
            **TRUSTED_AGENT,
            "title": "Uncertain fact",
            "canonical_text": "The vendor contract renewal might be in March.",
            "confidence": 0.3,
        },
    )
    assert proposed["status"] == "review_required"
    assert proposed["write_mode"] == "propose_review"
    memory_id = str(proposed["memory"]["id"])
    assert proposed["memory"]["status"] == "candidate"

    review = call_mcp_tool(sqlite_context, name="alice_memory_review", arguments={})
    assert any(item["id"] == memory_id for item in review["items"])

    approved = call_mcp_tool(
        sqlite_context,
        name="alice_memory_correct",
        arguments={"review_item_id": memory_id, "action": "approve", "reason": "Confirmed by user"},
    )
    assert approved["memory"]["status"] == "active"


def test_memory_commit_without_identity_is_rejected(sqlite_context) -> None:
    rejected = call_mcp_tool(
        sqlite_context,
        name="alice_memory_commit",
        arguments={"title": "No identity", "canonical_text": "Anonymous writes are rejected."},
    )
    assert rejected["status"] == "rejected"
    assert rejected["write_mode"] == "reject"
    assert "agent_identity_required" in rejected["reasons"]


def test_memory_commit_resolves_agent_identity_from_api_key(sqlite_context, monkeypatch) -> None:
    from alicebot_api.vnext_agent_keys import create_agent_key

    with sqlite_user_connection(_db_path(sqlite_context), USER_ID) as conn:
        store = SQLiteVNextStore(conn, USER_ID)
        _record, raw_key = create_agent_key(
            store,
            user_id=USER_ID,
            agent_id="hermes",
            permission_profile="trusted_local_agent",
            label="onramp test",
        )
    monkeypatch.setenv(mcp_tools_module.AGENT_API_KEY_ENV, raw_key)

    # No identity fields in the payload: agent_id and profile come from the key.
    committed = call_mcp_tool(
        sqlite_context,
        name="alice_memory_commit",
        arguments={
            "title": "Key-authenticated commit",
            "canonical_text": "Agent API keys also govern MCP commits in SQLite mode.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    assert committed["status"] == "committed"
    identity = committed["memory"]["metadata_json"]["agentic_memory"]["agent_identity"]
    assert identity["agent_id"] == "hermes"
    assert identity["permission_profile"] == "trusted_local_agent"
    assert identity["auth"] == "agent_api_key"

    # Claiming a different agent than the key was issued to is rejected.
    with pytest.raises(MCPToolError, match="issued to agent 'hermes'"):
        call_mcp_tool(
            sqlite_context,
            name="alice_memory_commit",
            arguments={
                "agent_id": "openclaw",
                "title": "Impersonation attempt",
                "canonical_text": "This should not be written.",
            },
        )


def test_recent_decisions_filters_query_project_and_window(sqlite_context) -> None:
    first_id = _capture_decision(sqlite_context, "Use SQLite for the local on-ramp")
    second_id = _capture_decision(sqlite_context, "Keep Postgres for the hosted tier")

    payload = call_mcp_tool(sqlite_context, name="alice_recent_decisions", arguments={})
    assert payload["mode"] == "vnext"
    assert payload["count"] == 2
    assert [row["id"] for row in payload["decisions"]] == [second_id, first_id]
    row = payload["decisions"][0]
    assert set(row) == {
        "id",
        "title",
        "canonical_text",
        "created_at",
        "domain",
        "status",
        "memory_type",
        "confidence",
        "provenance_count",
    }

    filtered = call_mcp_tool(
        sqlite_context, name="alice_recent_decisions", arguments={"query": "hosted tier"}
    )
    assert [item["id"] for item in filtered["decisions"]] == [second_id]

    by_project = call_mcp_tool(
        sqlite_context, name="alice_recent_decisions", arguments={"project": "project"}
    )
    assert by_project["count"] == 2  # matches the memories' domain

    windowed = call_mcp_tool(
        sqlite_context,
        name="alice_recent_decisions",
        arguments={"until": "2000-01-01T00:00:00+00:00"},
    )
    assert windowed["count"] == 0

    ignored = call_mcp_tool(
        sqlite_context,
        name="alice_recent_decisions",
        arguments={"person": "Priya"},
    )
    assert ignored["filters_ignored"] == ["person"]


def test_open_loops_list_and_close_actions(sqlite_context) -> None:
    with sqlite_user_connection(_db_path(sqlite_context), USER_ID) as conn:
        store = SQLiteVNextStore(conn, USER_ID)
        loop = store.create_open_loop(
            {
                "title": "Publish the alice-memory entrypoint",
                "description": "Add [project.scripts] and release",
                "priority": "high",
                "domain": "project",
                "sensitivity": "internal",
            }
        )
    loop_id = str(loop["id"])

    listed = call_mcp_tool(sqlite_context, name="alice_open_loops", arguments={})
    assert listed["count"] == 1
    assert listed["items"][0]["id"] == loop_id

    closed = call_mcp_tool(
        sqlite_context,
        name="alice_open_loops",
        arguments={"action": "close", "loop_id": loop_id, "resolution_note": "Shipped"},
    )
    assert closed["action"] == "close"
    assert closed["open_loop"]["status"] == "resolved"

    relisted = call_mcp_tool(sqlite_context, name="alice_open_loops", arguments={})
    assert relisted["count"] == 0


def test_resume_brief_shape_and_content(sqlite_context) -> None:
    decision_id = _capture_decision(sqlite_context, "Resume briefs come from the vNext store")
    with sqlite_user_connection(_db_path(sqlite_context), USER_ID) as conn:
        store = SQLiteVNextStore(conn, USER_ID)
        loop = store.create_open_loop(
            {"title": "Wire the resume brief", "domain": "project", "sensitivity": "internal"}
        )

    payload = call_mcp_tool(
        sqlite_context,
        name="alice_resume",
        arguments={"max_open_loops": 5, "max_recent_changes": 5, "person": "Priya"},
    )
    brief = payload["brief"]
    assert set(brief) == {
        "last_decision",
        "next_action",
        "open_loops",
        "recent_changes",
        "generated_at",
        "mode",
        "filters_ignored",
    }
    assert brief["mode"] == "vnext"
    assert brief["filters_ignored"] == ["person"]
    assert brief["last_decision"]["id"] == decision_id
    assert brief["last_decision"]["kind"] == "memory"
    assert brief["next_action"]["kind"] == "open_loop"
    assert brief["next_action"]["id"] == str(loop["id"])
    assert [item["id"] for item in brief["open_loops"]] == [str(loop["id"])]
    assert 0 < len(brief["recent_changes"]) <= 5
    assert {"id", "event_type", "actor_type", "target_type", "target_id", "occurred_at"} == set(
        brief["recent_changes"][0]
    )
    assert brief["generated_at"].endswith("Z")


def test_memory_review_detail_and_status_mapping(sqlite_context) -> None:
    memory_id = _capture_decision(sqlite_context, "Review detail should include revisions")

    detail = call_mcp_tool(
        sqlite_context, name="alice_memory_review", arguments={"review_item_id": memory_id}
    )
    assert detail["mode"] == "vnext_detail"
    assert detail["review"]["memory"]["id"] == memory_id
    assert detail["review"]["revisions"] == []
    assert len(detail["review"]["provenance_links"]) == 1

    pending = call_mcp_tool(
        sqlite_context, name="alice_memory_review", arguments={"status": "pending_review"}
    )
    assert pending["count"] == 1

    active = call_mcp_tool(sqlite_context, name="alice_memory_review", arguments={"status": "active"})
    assert active["count"] == 0

    everything = call_mcp_tool(sqlite_context, name="alice_memory_review", arguments={"status": "all"})
    assert everything["count"] == 1

    stale = call_mcp_tool(sqlite_context, name="alice_memory_review", arguments={"status": "stale"})
    assert stale == {
        "items": [],
        "count": 0,
        "mode": "vnext_candidates",
        "note": (
            "status 'stale' has no SQLite on-ramp equivalent; "
            "use pending_review, correction_ready, active, or all"
        ),
    }

    with pytest.raises(MCPToolError, match="status must be one of"):
        call_mcp_tool(sqlite_context, name="alice_memory_review", arguments={"status": "bogus"})

    missing = "99999999-9999-4999-8999-999999999999"
    with pytest.raises(MCPToolError, match="was not found"):
        call_mcp_tool(sqlite_context, name="alice_memory_review", arguments={"review_item_id": missing})


def test_memory_correct_reject_edit_and_supersede(sqlite_context) -> None:
    reject_id = _capture_decision(sqlite_context, "Reject this stray decision")
    rejected = call_mcp_tool(
        sqlite_context,
        name="alice_memory_correct",
        arguments={"review_item_id": reject_id, "action": "reject", "reason": "Not a decision"},
    )
    assert rejected["review_action"]["resolved_action"] == "delete"
    assert rejected["memory"]["status"] == "rejected"
    audit = call_mcp_tool(sqlite_context, name="alice_explain", arguments={"memory_id": reject_id})
    assert [revision["revision_type"] for revision in audit["revisions"]] == ["rejected"]

    edit_id = _capture_decision(sqlite_context, "Edit this decision before approval")
    edited = call_mcp_tool(
        sqlite_context,
        name="alice_memory_correct",
        arguments={
            "review_item_id": edit_id,
            "action": "edit-and-approve",
            "title": "Corrected decision",
            "body": {"text": "Edit then approve the decision"},
            "reason": "Fix wording",
        },
    )
    assert edited["review_action"]["resolved_action"] == "edit"
    assert edited["memory"]["status"] == "active"
    assert edited["memory"]["title"] == "Corrected decision"
    assert edited["memory"]["canonical_text"] == "Edit then approve the decision"
    assert edited["memory"]["value"] == {"text": "Edit then approve the decision"}

    superseded = call_mcp_tool(
        sqlite_context,
        name="alice_memory_correct",
        arguments={
            "review_item_id": edit_id,
            "action": "supersede-existing",
            "reason": "Newer decision recorded",
            "replacement_title": "Decision: final wording",
            "replacement_body": {"text": "The final decision wording"},
            "replacement_confidence": 0.97,
        },
    )
    assert superseded["review_action"]["resolved_action"] == "supersede"
    assert superseded["mode"] == "vnext"
    assert superseded["memory"]["status"] == "superseded"
    replacement = superseded["replacement_object"]
    assert replacement is not None
    assert replacement["status"] == "active"
    assert replacement["canonical_text"] == "The final decision wording"
    assert replacement["metadata_json"]["supersedes"] == edit_id
    assert superseded["memory"]["metadata_json"]["superseded_by"] == replacement["id"]

    old_audit = call_mcp_tool(sqlite_context, name="alice_explain", arguments={"memory_id": edit_id})
    assert [revision["revision_type"] for revision in old_audit["revisions"]] == [
        "edited",
        "superseded",
    ]
    new_audit = call_mcp_tool(
        sqlite_context, name="alice_explain", arguments={"memory_id": str(replacement["id"])}
    )
    assert [revision["revision_type"] for revision in new_audit["revisions"]] == ["created"]


def test_memory_correct_validation_errors(sqlite_context) -> None:
    missing = "99999999-9999-4999-8999-999999999999"
    with pytest.raises(MCPToolError, match="was not found"):
        call_mcp_tool(
            sqlite_context,
            name="alice_memory_correct",
            arguments={"review_item_id": missing, "action": "approve"},
        )

    memory_id = _capture_decision(sqlite_context, "Validation coverage decision")
    with pytest.raises(MCPToolError, match="replacement_title or replacement_body"):
        call_mcp_tool(
            sqlite_context,
            name="alice_memory_correct",
            arguments={"review_item_id": memory_id, "action": "supersede-existing"},
        )
    with pytest.raises(MCPToolError, match="at least one of title, body, or confidence"):
        call_mcp_tool(
            sqlite_context,
            name="alice_memory_correct",
            arguments={"review_item_id": memory_id, "action": "edit-and-approve"},
        )
    with pytest.raises(MCPToolError, match="not supported on the SQLite on-ramp"):
        call_mcp_tool(
            sqlite_context,
            name="alice_memory_correct",
            arguments={"review_item_id": memory_id, "action": "mark_stale"},
        )


def test_explain_entity_and_continuity_branches_require_postgres(sqlite_context) -> None:
    with pytest.raises(MCPToolError, match="available on the Postgres backend"):
        call_mcp_tool(
            sqlite_context,
            name="alice_explain",
            arguments={"entity_id": "22222222-2222-4222-8222-222222222222"},
        )
    with pytest.raises(MCPToolError, match="available on the Postgres backend"):
        call_mcp_tool(
            sqlite_context,
            name="alice_explain",
            arguments={"continuity_object_id": "22222222-2222-4222-8222-222222222222"},
        )


def test_sqlite_constraint_violation_maps_to_mcp_tool_error(sqlite_context) -> None:
    # 'not-a-domain' passes tool-level parsing but violates the persisted
    # sources.domain CHECK constraint, raising sqlite3.IntegrityError inside
    # the store; call_mcp_tool must translate it like psycopg CheckViolation.
    with pytest.raises(MCPToolError, match="persisted schema constraint"):
        call_mcp_tool(
            sqlite_context,
            name="alice_capture",
            arguments={"raw_text": "Fact: constraint check", "domain": "not-a-domain"},
        )


# --- alice-memory CLI ----------------------------------------------------------


def test_normalized_argv_defaults_to_mcp_subcommand() -> None:
    assert _normalized_argv([]) == ["mcp"]
    assert _normalized_argv(["--data-dir", "/tmp/x"]) == ["mcp", "--data-dir", "/tmp/x"]
    assert _normalized_argv(["mcp", "--db", "x.db"]) == ["mcp", "--db", "x.db"]
    assert _normalized_argv(["export", "--out", "o.jsonl"]) == ["export", "--out", "o.jsonl"]
    assert _normalized_argv(["--version"]) == ["--version"]


def test_version_flag_prints_package_version(capsys) -> None:
    from alicebot_api import __version__

    with pytest.raises(SystemExit) as excinfo:
        onramp_main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"alice-memory {__version__}"


def test_export_writes_jsonl_records(sqlite_context, tmp_path) -> None:
    memory_id = _capture_decision(sqlite_context, "Export this decision as JSONL")
    with sqlite_user_connection(_db_path(sqlite_context), USER_ID) as conn:
        SQLiteVNextStore(conn, USER_ID).create_open_loop(
            {"title": "Exportable loop", "domain": "project"}
        )

    out_path = tmp_path / "export" / "dump.jsonl"
    exit_code = onramp_main(
        [
            "export",
            "--db",
            _db_path(sqlite_context),
            "--user-id",
            str(USER_ID),
            "--out",
            str(out_path),
        ]
    )
    assert exit_code == 0

    records = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    by_type: dict[str, list[dict[str, object]]] = {}
    for record in records:
        assert set(record) == {"record_type", "record"}
        by_type.setdefault(record["record_type"], []).append(record["record"])

    assert set(by_type) == {"memory", "source", "open_loop", "event"}
    assert any(row["id"] == memory_id for row in by_type["memory"])
    assert len(by_type["source"]) == 1
    assert by_type["open_loop"][0]["title"] == "Exportable loop"
    assert any(row["event_type"] == "source.captured" for row in by_type["event"])


def test_export_fails_cleanly_when_database_missing(tmp_path, capsys) -> None:
    exit_code = onramp_main(["export", "--db", str(tmp_path / "nope.db")])
    assert exit_code == 1
    assert "does not exist" in capsys.readouterr().err


# --- true subprocess smoke over stdio ------------------------------------------


def _write_mcp_message(stream, payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    stream.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
    stream.write(encoded)
    stream.flush()


def _read_mcp_message(stream) -> dict[str, object]:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if line == b"":
            raise RuntimeError("MCP server closed stdout unexpectedly")
        if line in {b"\r\n", b"\n"}:
            break
        decoded = line.decode("utf-8").strip()
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    content_length = int(headers["content-length"])
    body = stream.read(content_length)
    return json.loads(body.decode("utf-8"))


class _StdioClient:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process
        self._next_id = 1

    def request(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        request_id = self._next_id
        self._next_id += 1
        payload: dict[str, object] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        _write_mcp_message(self.process.stdin, payload)
        try:
            response = _read_mcp_message(self.process.stdout)
        except RuntimeError as exc:
            stderr_text = ""
            if self.process.stderr is not None:
                stderr_text = self.process.stderr.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{exc}\nstderr:\n{stderr_text}") from exc
        assert response.get("id") == request_id
        return response

    def call_tool(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        response = self.request("tools/call", params={"name": name, "arguments": arguments})
        result = response["result"]
        assert result.get("isError") is False, result
        return json.loads(result["content"][0]["text"])


def test_alice_memory_mcp_subprocess_smoke(tmp_path, monkeypatch) -> None:
    import os

    env = os.environ.copy()
    for env_name in (
        EMBEDDINGS_BASE_URL_ENV,
        EMBEDDINGS_MODEL_ENV,
        EMBEDDINGS_API_KEY_ENV,
        mcp_tools_module.MCP_LEGACY_TOOLS_ENV,
        mcp_tools_module.AGENT_API_KEY_ENV,
    ):
        env.pop(env_name, None)
    pythonpath_entries = [str(REPO_ROOT / "apps" / "api" / "src"), str(REPO_ROOT / "workers")]
    if env.get("PYTHONPATH"):
        pythonpath_entries.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)

    process = subprocess.Popen(
        [sys.executable, "-m", "alicebot_api.onramp", "mcp", "--data-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    watchdog = threading.Timer(60, process.kill)
    watchdog.start()
    try:
        client = _StdioClient(process)
        initialize = client.request(
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "pytest-onramp-client", "version": "1.0"},
                "capabilities": {},
            },
        )
        assert initialize["result"]["protocolVersion"] == "2024-11-05"

        tools_list = client.request("tools/list")
        assert [tool["name"] for tool in tools_list["result"]["tools"]] == CORE_TOOL_NAMES

        captured = client.call_tool(
            "alice_capture",
            {"raw_text": "Decision: Smoke the on-ramp over stdio", "domain": "project"},
        )
        assert captured["status"] == "imported"
        assert captured["candidate_memory_count"] == 1

        review = client.call_tool("alice_memory_review", {})
        assert review["count"] == 1
        memory_id = review["items"][0]["id"]

        approved = client.call_tool(
            "alice_memory_correct", {"review_item_id": memory_id, "action": "approve"}
        )
        assert approved["memory"]["status"] == "active"

        recall = client.call_tool("alice_recall", {"query": "smoke the on-ramp", "debug": True})
        assert recall["count"] >= 1
        assert recall["results"][0]["id"] == memory_id
        assert recall["retrieval"]["fusion"]["algorithm"] == "reciprocal_rank_fusion"

        committed = client.call_tool(
            "alice_memory_commit",
            {
                "agent_id": "hermes",
                "agent_type": "personal_assistant",
                "permission_profile": "trusted_local_agent",
                "title": "Stdio commit smoke",
                "canonical_text": "Explicit commits work over stdio in SQLite mode.",
                "domain": "professional",
                "sensitivity": "internal",
                "confidence": 0.96,
            },
        )
        assert committed["status"] == "committed"
        undone = client.call_tool(
            "alice_memory_manage",
            {
                "agent_id": "hermes",
                "agent_type": "personal_assistant",
                "permission_profile": "trusted_local_agent",
                "action": "undo",
                "memory_id": committed["memory"]["id"],
            },
        )
        assert undone["status"] == "undone"

        # The database landed in the requested data dir and the startup
        # notice went to stderr, keeping stdout protocol-clean.
        assert (tmp_path / "memory.db").exists()
    finally:
        watchdog.cancel()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    stderr_text = process.stderr.read().decode("utf-8", errors="replace")
    assert "alice-memory: serving MCP over stdio" in stderr_text
