from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from psycopg.types.json import Jsonb

from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_event_log import build_event_log_record
from alicebot_api.vnext_store import PostgresVNextStore, _search_patterns


class RecordingCursor:
    def __init__(self, fetchone_results: list[dict[str, Any]], fetchall_result: list[dict[str, Any]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_result = fetchall_result or []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        if params is not None:
            assert query.count("%s") == len(params)
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        return self.fetchall_result


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def _event_row(target_id: object | None = None) -> dict[str, object]:
    return {
        "id": uuid4(),
        "event_type": "audit",
        "target_id": str(target_id) if target_id is not None else None,
    }


def _event_log_insert_count(cursor: RecordingCursor) -> int:
    return sum(1 for query, _params in cursor.executed if "INSERT INTO event_log" in query)


def test_source_crud_and_chunks_write_audit_events() -> None:
    source_id = str(uuid4())
    chunk_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": source_id},
            _event_row(source_id),
            {"id": source_id},
            {"id": source_id},
            _event_row(source_id),
            {"id": source_id},
            _event_row(source_id),
            {"id": chunk_id, "source_id": source_id},
            _event_row(chunk_id),
        ],
        fetchall_result=[{"id": chunk_id, "source_id": source_id}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    created = store.create_source(
        {
            "id": source_id,
            "source_type": "document",
            "title": "Spec",
            "content_hash": "sha256:abc",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"path": "docs/spec.md"},
        }
    )
    fetched = store.get_source(source_id)
    updated = store.update_source(source_id=source_id, patch={"title": "Spec v2", "metadata_json": {"rev": 2}})
    deleted = store.delete_source(source_id=source_id)
    chunk = store.create_source_chunk(
        {
            "id": chunk_id,
            "source_id": source_id,
            "chunk_index": 0,
            "text": "Alice vNext",
            "token_count": 3,
            "metadata_json": {"section": "intro"},
        }
    )
    chunks = store.list_source_chunks(source_id)

    assert created["id"] == source_id
    assert fetched is not None
    assert updated["id"] == source_id
    assert deleted["id"] == source_id
    assert chunk["source_id"] == source_id
    assert chunks == [{"id": chunk_id, "source_id": source_id}]
    assert _event_log_insert_count(cursor) == 4

    source_insert_query, source_insert_params = cursor.executed[0]
    assert "INSERT INTO sources" in source_insert_query
    assert source_insert_params is not None
    assert isinstance(source_insert_params[-1], Jsonb)
    assert source_insert_params[-1].obj == {"path": "docs/spec.md"}

    source_update_query, source_update_params = cursor.executed[3]
    assert "UPDATE sources" in source_update_query
    assert source_update_params is not None
    assert isinstance(source_update_params[6], Jsonb)
    assert source_update_params[6].obj == {"rev": 2}


def test_get_source_by_content_hash_uses_dedupe_lookup() -> None:
    source_id = str(uuid4())
    cursor = RecordingCursor(fetchone_results=[{"id": source_id, "content_hash": "sha256:abc"}])
    store = PostgresVNextStore(RecordingConnection(cursor))

    source = store.get_source_by_content_hash("sha256:abc")

    assert source is not None
    assert source["id"] == source_id
    query, params = cursor.executed[0]
    assert "FROM sources" in query
    assert "content_hash = %s" in query
    assert "deleted_at IS NULL" in query
    assert params == ("sha256:abc",)


def test_search_patterns_strip_quotes_and_add_keyword_fallbacks() -> None:
    patterns = _search_patterns('"agent-first /vnext audit correction cockpit"')

    assert patterns[0] == "%agent-first /vnext audit correction cockpit%"
    assert "%agent-first%" in patterns
    assert "%vnext%" in patterns
    assert "%audit%" in patterns
    assert "%correction%" in patterns
    assert "%cockpit%" in patterns


def test_keyword_search_methods_apply_domain_sensitivity_and_limit_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {"id": "matched-1", "domain": "project", "sensitivity": "private"},
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    memories = store.search_memories(
        query="Alice provenance",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=4,
    )
    sources = store.search_sources(
        query="Alice provenance",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=3,
    )
    open_loops = store.list_open_loops(
        status="open",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=2,
    )

    assert memories[0]["id"] == "matched-1"
    assert sources[0]["id"] == "matched-1"
    assert open_loops[0]["id"] == "matched-1"
    memory_query, memory_params = cursor.executed[0]
    source_query, source_params = cursor.executed[1]
    open_loop_query, open_loop_params = cursor.executed[2]
    assert "FROM memories" in memory_query
    assert "status IN ('active', 'accepted')" in memory_query
    assert "domain = ANY" in memory_query
    assert "sensitivity = ANY" in memory_query
    assert "memory_type = ANY" in memory_query
    assert "COALESCE(project_id, metadata_json ->> 'project_id')" in memory_query
    assert "created_by_agent_id = ANY" in memory_query
    assert "run_id = %s" in memory_query
    assert "valid_to IS NULL OR valid_to >= clock_timestamp()" in memory_query
    assert "ILIKE ANY" in memory_query
    assert memory_params is not None
    # Unset filters arrive as NULLs, expiry defaults to excluded (False).
    assert memory_params[4] is None  # memory_types
    assert memory_params[6] is None  # projects
    assert memory_params[8] is None  # created_by_agent_ids
    assert memory_params[10] is None  # run_id
    assert memory_params[12] is False  # include_expired
    assert memory_params[13] == ["%Alice provenance%", "%alice%", "%provenance%"]
    assert memory_params[-1] == 4
    assert "FROM sources" in source_query
    assert "ILIKE ANY" in source_query
    assert source_params is not None
    assert source_params[4] == ["%Alice provenance%", "%alice%", "%provenance%"]
    assert source_params[-1] == 3
    assert "FROM open_loops" in open_loop_query
    assert "%s::text IS NULL OR status = %s" in open_loop_query
    assert "%s::uuid IS NULL OR project_id = %s::uuid" in open_loop_query
    assert "%s::uuid IS NULL OR person_id = %s::uuid" in open_loop_query
    assert open_loop_params == (
        "open",
        "open",
        ["project"],
        ["project"],
        ["public", "private"],
        ["public", "private"],
        None,
        None,
        None,
        None,
        2,
    )


def test_list_artifacts_applies_type_domain_sensitivity_and_limit_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {"id": "artifact-1", "artifact_type": "daily_brief", "domain": "project", "sensitivity": "private"},
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    artifacts = store.list_artifacts(
        artifact_type="daily_brief",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=5,
    )

    assert artifacts[0]["id"] == "artifact-1"
    query, params = cursor.executed[0]
    assert "FROM generated_artifacts" in query
    assert "%s::text IS NULL OR artifact_type = %s" in query
    assert "domain = ANY" in query
    assert "sensitivity = ANY" in query
    assert params == (
        "daily_brief",
        "daily_brief",
        ["project"],
        ["project"],
        ["public", "private"],
        ["public", "private"],
        5,
    )


def test_artifact_quality_ratings_insert_and_export_json_safe_payloads() -> None:
    artifact_id = str(uuid4())
    rating_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": rating_id, "artifact_id": artifact_id, "reviewer_id": "samir"},
            _event_row(artifact_id),
        ],
        fetchall_result=[{"id": rating_id, "artifact_id": artifact_id, "usefulness": 5}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    created = store.create_artifact_quality_rating(
        {
            "id": rating_id,
            "artifact_id": artifact_id,
            "reviewer_id": "samir",
            "usefulness": 5,
            "accuracy": 4,
            "source_grounding": 5,
            "novel_connections": 3,
            "actionability": 4,
            "hallucination_risk": 1,
            "verbosity": "right_sized",
            "missed_context": "Needs one more source.",
            "comments": "Useful artifact.",
            "metadata_json": {"prompt_hash": "sha256:test"},
        }
    )
    rows = store.list_artifact_quality_ratings(artifact_id=artifact_id, limit=10)

    assert created["id"] == rating_id
    assert rows == [{"id": rating_id, "artifact_id": artifact_id, "usefulness": 5}]
    assert _event_log_insert_count(cursor) == 1
    insert_query, insert_params = cursor.executed[0]
    assert "INSERT INTO artifact_quality_ratings" in insert_query
    assert insert_params is not None
    assert isinstance(insert_params[-1], Jsonb)
    assert insert_params[-1].obj == {"prompt_hash": "sha256:test"}
    list_query, list_params = cursor.executed[2]
    assert "FROM artifact_quality_ratings" in list_query
    assert list_params == (artifact_id, artifact_id, 10)


def test_list_beliefs_joins_memory_domain_sensitivity_filters() -> None:
    belief_id = str(uuid4())
    memory_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {
                "id": belief_id,
                "memory_id": memory_id,
                "claim": "Alice should preserve provenance.",
                "domain": "project",
                "sensitivity": "private",
            },
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    beliefs = store.list_beliefs(
        status="active",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=6,
    )

    assert beliefs[0]["id"] == belief_id
    query, params = cursor.executed[0]
    assert "FROM beliefs b" in query
    assert "JOIN memories m" in query
    assert "%s::text IS NULL OR b.status = %s" in query
    assert "m.domain = ANY" in query
    assert "m.sensitivity = ANY" in query
    assert params == (
        "active",
        "active",
        ["project"],
        ["project"],
        ["public", "private"],
        ["public", "private"],
        6,
    )


def test_memory_revision_provenance_and_graph_methods_write_audit_events() -> None:
    memory_id = str(uuid4())
    revision_id = str(uuid4())
    provenance_id = str(uuid4())
    edge_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": memory_id},
            _event_row(memory_id),
            {"id": memory_id},
            {"id": memory_id},
            _event_row(memory_id),
            {"id": revision_id, "memory_id": memory_id},
            _event_row(memory_id),
            {"id": provenance_id, "target_type": "memory", "target_id": memory_id},
            _event_row(memory_id),
            {"id": edge_id, "edge_type": "supports"},
            _event_row(edge_id),
            {"id": edge_id, "edge_type": "supports"},
            _event_row(edge_id),
            {"id": edge_id, "edge_type": "supports", "metadata_json": {"status": "accepted"}},
            _event_row(edge_id),
        ],
        fetchall_result=[{"id": memory_id}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_memory(
        {
            "id": memory_id,
            "memory_key": "project.alice.status",
            "value": {"status": "building"},
            "canonical_text": "Alice vNext is being built.",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"source": "spec"},
        }
    )
    store.get_memory(memory_id)
    store.update_memory(memory_id=memory_id, patch={"status": "active", "metadata_json": {"reviewed": True}})
    store.list_memories(status="active")
    store.append_revision(
        {
            "id": revision_id,
            "memory_id": memory_id,
            "memory_key": "project.alice.status",
            "previous_value": {"status": "candidate"},
            "new_value": {"status": "active"},
            "text_after": "Alice vNext is active.",
            "revision_type": "promoted",
        }
    )
    store.list_revisions(memory_id)
    store.create_provenance_link(
        {
            "id": provenance_id,
            "target_type": "memory",
            "target_id": memory_id,
            "evidence_role": "supports",
            "confidence": 0.9,
        }
    )
    store.list_provenance_links(target_type="memory", target_id=memory_id)
    store.create_edge(
        {
            "id": edge_id,
            "from_type": "memory",
            "from_id": memory_id,
            "to_type": "project",
            "to_id": "alice-vnext",
            "edge_type": "supports",
            "created_by": "system",
        }
    )
    store.list_edges(from_id=memory_id)
    store.update_edge_status(edge_id=edge_id, status="accepted")
    store.expire_edge(edge_id=edge_id)

    assert _event_log_insert_count(cursor) == 7
    memory_insert_query = cursor.executed[0][0]
    assert "INSERT INTO memories" in memory_insert_query
    assert "canonical_text" in memory_insert_query
    assert "domain" in memory_insert_query
    assert "sensitivity" in memory_insert_query
    assert "metadata_json" in memory_insert_query
    assert any("WITH next_revision" in query for query, _params in cursor.executed)
    assert any("INSERT INTO provenance_links" in query for query, _params in cursor.executed)
    assert any("INSERT INTO graph_edges" in query for query, _params in cursor.executed)
    assert any("UPDATE graph_edges" in query for query, _params in cursor.executed)
    assert any("%s::text IS NULL OR from_id = %s" in query for query, _params in cursor.executed)
    update_edge_query, update_edge_params = cursor.executed[-4]
    assert "metadata_json = metadata_json || %s" in update_edge_query
    assert update_edge_params is not None
    assert update_edge_params[1] == "accepted"


def test_project_people_belief_and_open_loop_methods_write_audit_events() -> None:
    project_id = str(uuid4())
    person_id = str(uuid4())
    memory_id = str(uuid4())
    belief_id = str(uuid4())
    loop_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": project_id},
            _event_row(project_id),
            {"id": project_id},
            {"id": project_id},
            _event_row(project_id),
            {"id": person_id},
            _event_row(person_id),
            {"id": person_id},
            {"id": person_id},
            _event_row(person_id),
            {"id": belief_id, "memory_id": memory_id},
            _event_row(belief_id),
            {"id": belief_id, "memory_id": memory_id},
            {"id": belief_id, "memory_id": memory_id},
            _event_row(belief_id),
            {"id": loop_id},
            _event_row(loop_id),
            {"id": loop_id},
            {"id": loop_id},
            _event_row(loop_id),
            {"id": loop_id},
            _event_row(loop_id),
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_project({"id": project_id, "name": "Alice vNext", "slug": "alice-vnext"})
    store.get_project(project_id)
    store.list_projects(status="active", domains=["project"], sensitivity_allowed=["private"], limit=3)
    store.update_project(project_id=project_id, patch={"current_state": "Sprint 1"})
    store.create_person({"id": person_id, "name": "Samir", "aliases_json": ["owner"]})
    store.get_person(person_id)
    store.update_person(person_id=person_id, patch={"notes": "Project owner"})
    store.create_belief({"id": belief_id, "memory_id": memory_id, "claim": "Provenance is mandatory."})
    store.get_belief(belief_id)
    store.update_belief_status(belief_id=belief_id, status="challenged", confidence=0.4)
    store.create_open_loop({"id": loop_id, "title": "Validate migration on Postgres", "priority": "high"})
    store.get_open_loop(loop_id)
    store.update_open_loop_status(loop_id=loop_id, status="resolved", resolution_note="Covered by CI")
    store.update_open_loop(loop_id=loop_id, patch={"title": "Validate migration", "priority": "normal"})

    assert _event_log_insert_count(cursor) == 9
    assert "INSERT INTO projects" in cursor.executed[0][0]
    assert "FROM projects" in cursor.executed[3][0]
    assert "%s::text IS NULL OR status = %s" in cursor.executed[3][0]
    assert cursor.executed[3][1] == ("active", "active", ["project"], ["project"], ["private"], ["private"], 3)
    assert "UPDATE projects" in cursor.executed[4][0]
    assert "INSERT INTO people" in cursor.executed[6][0]
    assert "UPDATE people" in cursor.executed[9][0]
    assert "INSERT INTO beliefs" in cursor.executed[11][0]
    assert "UPDATE beliefs" in cursor.executed[14][0]
    assert "INSERT INTO open_loops" in cursor.executed[16][0]
    assert "UPDATE open_loops" in cursor.executed[19][0]
    assert "UPDATE open_loops" in cursor.executed[21][0]


def test_artifact_task_and_brain_charter_methods_write_audit_events() -> None:
    artifact_id = str(uuid4())
    task_id = str(uuid4())
    charter_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": artifact_id, "artifact_type": "context_pack"},
            _event_row(artifact_id),
            {"id": artifact_id, "artifact_type": "context_pack"},
            {"id": artifact_id, "artifact_type": "context_pack"},
            _event_row(artifact_id),
            {"id": task_id, "task_type": "synthesize"},
            _event_row(task_id),
            {"id": task_id, "task_type": "synthesize"},
            _event_row(task_id),
            {"id": task_id, "task_type": "synthesize"},
            _event_row(task_id),
            {"id": charter_id},
            _event_row(charter_id),
            {"id": charter_id},
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_artifact(
        {
            "id": artifact_id,
            "artifact_type": "context_pack",
            "title": "Sprint 1 Context",
            "content_markdown": "# Context",
            "generated_by": "system",
        }
    )
    store.get_artifact(artifact_id)
    store.update_artifact_status(artifact_id=artifact_id, status="reviewed")
    store.create_task(
        {
            "id": task_id,
            "title": "Synthesize evidence",
            "task_type": "synthesize",
            "instructions": "Create a context pack.",
            "scope_json": {"project": "alice-vnext"},
        }
    )
    claimed = store.claim_next_task()
    store.update_task_status(task_id=task_id, status="completed", details={"metadata_json": {"ok": True}})
    store.upsert_brain_charter(
        {
            "id": charter_id,
            "content_markdown": "# ALICE.md - Brain Charter",
            "owner_json": {"name": "Owner"},
            "autonomous_rules_json": ["Always preserve provenance."],
            "quality_standard_json": ["Do not fabricate."],
        }
    )
    store.get_brain_charter()

    assert claimed is not None
    assert _event_log_insert_count(cursor) == 6
    assert "INSERT INTO generated_artifacts" in cursor.executed[0][0]
    assert "UPDATE generated_artifacts" in cursor.executed[3][0]
    assert "INSERT INTO task_queue" in cursor.executed[5][0]
    assert "FOR UPDATE SKIP LOCKED" in cursor.executed[7][0]
    assert "UPDATE task_queue" in cursor.executed[9][0]
    assert "ON CONFLICT (user_id)" in cursor.executed[11][0]


def test_append_and_list_event_log_records_use_integrity_payload() -> None:
    event = build_event_log_record(
        event_type="memory.created",
        actor_type="system",
        target_type="memory",
        target_id="memory-1",
        payload={"b": 2, "a": 1},
        occurred_at="2026-05-10T12:00:00Z",
    )
    cursor = RecordingCursor(fetchone_results=[_event_row("memory-1")], fetchall_result=[_event_row("memory-1")])
    store = PostgresVNextStore(RecordingConnection(cursor))

    appended = store.append_event(event)
    events = store.list_events(target_type="memory", target_id="memory-1")
    all_events = store.list_events()

    assert appended["target_id"] == "memory-1"
    assert events[0]["target_id"] == "memory-1"
    assert all_events[0]["target_id"] == "memory-1"
    event_insert_query, event_insert_params = cursor.executed[0]
    assert "INSERT INTO event_log" in event_insert_query
    assert event_insert_params is not None
    assert event_insert_params[1:6] == (
        "memory.created",
        "system",
        None,
        "memory",
        "memory-1",
    )
    assert isinstance(event_insert_params[7], Jsonb)
    assert event_insert_params[7].obj == {"b": 2, "a": 1}
    assert event_insert_params[10] == event["integrity_hash"]
    event_list_query = cursor.executed[1][0]
    assert "%s::text IS NULL OR target_type = %s" in event_list_query
    assert "%s::text IS NULL OR target_id = %s" in event_list_query


def test_connector_settings_and_state_methods_use_dedicated_tables_and_audit_events() -> None:
    setting_id = str(uuid4())
    state_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": setting_id,
                "connector_name": "telegram",
                "enabled": True,
                "configured": True,
                "default_domain": "personal",
                "default_sensitivity": "private",
                "sync_mode": "polling",
                "poll_interval_seconds": 60,
                "secret_ref": "telegram.bot_token.default",
                "validation_errors_json": [],
            },
            _event_row("telegram"),
            {"id": setting_id, "connector_name": "telegram"},
                {
                    "id": state_id,
                    "connector_id": setting_id,
                    "connector_name": "telegram",
                    "cursor_type": "sync_cursor",
                    "cursor_value": "42",
                    "last_sync_at": "2026-05-11T12:00:00Z",
                    "last_success_at": "2026-05-11T12:00:00Z",
                    "last_failure_at": None,
                    "items_seen": 3,
                    "items_captured": 1,
                    "items_deduped": 1,
                "items_failed": 1,
            },
            _event_row("telegram"),
            {"id": state_id, "connector_name": "telegram", "cursor_value": "42"},
            {"connector_settings_exists": True, "connector_state_exists": True, "migration_revision": "20260511_0070"},
        ],
        fetchall_result=[{"id": setting_id, "connector_name": "telegram"}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    setting = store.upsert_connector_setting(
        {
            "connector_name": "telegram",
            "enabled": True,
            "configured": True,
            "default_domain": "personal",
            "default_sensitivity": "private",
            "sync_mode": "polling",
            "poll_interval_seconds": 60,
            "secret_ref": "telegram.bot_token.default",
            "validation_errors_json": [],
            "metadata_json": {"config_json": {"allowed_chat_ids": ["999001"]}},
        }
    )
    settings = store.list_connector_settings()
    fetched_setting = store.get_connector_setting("telegram")
    state = store.upsert_connector_state(
        {
            "connector_name": "telegram",
            "cursor_value": "42",
            "last_sync_at": "2026-05-11T12:00:00Z",
            "last_success_at": "2026-05-11T12:00:00Z",
            "items_seen_delta": 3,
            "items_captured_delta": 1,
            "items_deduped_delta": 1,
            "items_failed_delta": 1,
            "average_processing_time_ms": 12.5,
            "state_json": {"last_status": "partial"},
        }
    )
    fetched_state = store.get_connector_state("telegram")
    storage_status = store.connector_storage_status()

    assert setting["id"] == setting_id
    assert settings == [{"id": setting_id, "connector_name": "telegram"}]
    assert fetched_setting is not None
    assert state["cursor_value"] == "42"
    assert fetched_state is not None
    assert storage_status["connector_settings_exists"] is True
    assert _event_log_insert_count(cursor) == 2
    setting_query, setting_params = cursor.executed[0]
    assert "INSERT INTO connector_settings" in setting_query
    assert "ON CONFLICT (user_id, connector_name)" in setting_query
    assert setting_params is not None
    assert isinstance(setting_params[8], Jsonb)
    assert setting_params[8].obj == []
    assert isinstance(setting_params[9], Jsonb)
    assert setting_params[9].obj == {"config_json": {"allowed_chat_ids": ["999001"]}}
    state_query, state_params = cursor.executed[4]
    assert "INSERT INTO connector_state" in state_query
    assert "items_seen = connector_state.items_seen + EXCLUDED.items_seen" in state_query
    assert state_params is not None
    assert isinstance(state_params[-1], Jsonb)
    assert state_params[-1].obj == {"last_status": "partial"}


def test_workspace_list_methods_apply_bounded_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[
            {"id": "workspace-row-1", "status": "active", "sensitivity": "private"},
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    sources = store.list_sources(domains=["project"], sensitivity_allowed=["private"], limit=7)
    people = store.list_people(sensitivity_allowed=["private"], limit=5)
    tasks = store.list_tasks(status=None, limit=4)
    events = store.list_events(limit=3)

    assert sources[0]["id"] == "workspace-row-1"
    assert people[0]["id"] == "workspace-row-1"
    assert tasks[0]["id"] == "workspace-row-1"
    assert events[0]["id"] == "workspace-row-1"

    source_query, source_params = cursor.executed[0]
    people_query, people_params = cursor.executed[1]
    task_query, task_params = cursor.executed[2]
    event_query, event_params = cursor.executed[3]
    assert "FROM sources" in source_query
    assert "deleted_at IS NULL" in source_query
    assert source_params == (["project"], ["project"], ["private"], ["private"], 7)
    assert "FROM people" in people_query
    assert people_params == (["private"], ["private"], 5)
    assert "FROM task_queue" in task_query
    assert task_params == (None, None, 4)
    assert "FROM event_log" in event_query
    assert "LIMIT %s" in event_query
    assert event_params == (3,)


def test_jsonb_and_event_hash_normalize_postgres_scalar_values() -> None:
    project_id = uuid4()
    captured_at = datetime(2026, 5, 10, 12, 30, tzinfo=UTC)
    event = build_event_log_record(
        event_type="project.update_candidate_created",
        actor_type="system",
        target_type="project",
        target_id=str(project_id),
        payload={
            "project_id": project_id,
            "source": {
                "captured_at": captured_at,
            },
        },
    )
    cursor = RecordingCursor(fetchone_results=[{"id": str(project_id)}, _event_row(project_id)])
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_project(
        {
            "id": str(project_id),
            "name": "Alice vNext",
            "slug": "alice-vnext",
            "metadata_json": {
                "candidate_memory_id": project_id,
                "source_captured_at": captured_at,
            },
        }
    )

    assert event["payload_json"] == {
        "project_id": str(project_id),
        "source": {
            "captured_at": "2026-05-10T12:30:00+00:00",
        },
    }
    project_insert_params = cursor.executed[0][1]
    assert project_insert_params is not None
    assert isinstance(project_insert_params[-1], Jsonb)
    assert project_insert_params[-1].obj == {
        "candidate_memory_id": str(project_id),
        "source_captured_at": "2026-05-10T12:30:00+00:00",
    }


def test_fts_search_builds_websearch_tsquery_with_pushed_down_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[{"id": "memory-1", "fts_score": 0.42}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    rows = store.search_memories_fts(
        query="Alice provenance retrieval",
        domains=["project"],
        sensitivity_allowed=["public", "private"],
        limit=25,
    )

    assert rows[0]["id"] == "memory-1"
    query, params = cursor.executed[0]
    assert "FROM memories" in query
    assert "websearch_to_tsquery('english', %s)" in query
    assert "search_tsv @@ websearch_to_tsquery('english', %s)" in query
    assert "ts_rank(search_tsv, websearch_to_tsquery('english', %s)) AS fts_score" in query
    assert "status IN ('active', 'accepted')" in query
    assert "deleted_at IS NULL" in query
    assert "domain = ANY" in query
    assert "sensitivity = ANY" in query
    assert "memory_type = ANY" in query
    assert "COALESCE(project_id, metadata_json ->> 'project_id')" in query
    assert "created_by_agent_id = ANY" in query
    assert "run_id = %s" in query
    assert "valid_to IS NULL OR valid_to >= clock_timestamp()" in query
    assert "ORDER BY fts_score DESC" in query
    assert params == (
        "Alice provenance retrieval",
        ["project"],
        ["project"],
        ["public", "private"],
        ["public", "private"],
        None,  # memory_types unset
        None,
        None,  # projects unset
        None,
        None,  # created_by_agent_ids unset
        None,
        None,  # run_id unset
        None,
        False,  # include_expired defaults to excluded
        "Alice provenance retrieval",
        25,
    )


def test_fts_search_pushes_down_memory_type_project_agent_run_and_expiry_filters() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[{"id": "memory-1", "fts_score": 0.42}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.search_memories_fts(
        query="Alice provenance retrieval",
        domains=["project"],
        sensitivity_allowed=["private"],
        limit=25,
        memory_types=("decision", "procedure"),
        projects=("alicebot",),
        created_by_agent_ids=("openclaw", "hermes"),
        run_id="run-2026-07-04-001",
        include_expired=True,
    )

    _query, params = cursor.executed[0]
    assert params == (
        "Alice provenance retrieval",
        ["project"],
        ["project"],
        ["private"],
        ["private"],
        ["decision", "procedure"],
        ["decision", "procedure"],
        ["alicebot"],
        ["alicebot"],
        ["openclaw", "hermes"],
        ["openclaw", "hermes"],
        "run-2026-07-04-001",
        "run-2026-07-04-001",
        True,
        "Alice provenance retrieval",
        25,
    )


def test_vector_search_orders_by_cosine_distance_and_skips_null_embeddings() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[{"id": "memory-1", "vector_distance": 0.12}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    rows = store.search_memories_vector(
        query_vector=[0.25, -1.0],
        domains=["project"],
        sensitivity_allowed=["private"],
        limit=12,
    )

    assert rows[0]["id"] == "memory-1"
    query, params = cursor.executed[0]
    assert "FROM memories" in query
    assert "embedding_vector IS NOT NULL" in query
    assert "status IN ('active', 'accepted')" in query
    assert "memory_type = ANY" in query
    assert "COALESCE(project_id, metadata_json ->> 'project_id')" in query
    assert "created_by_agent_id = ANY" in query
    assert "run_id = %s" in query
    assert "valid_to IS NULL OR valid_to >= clock_timestamp()" in query
    assert "ORDER BY embedding_vector <=> %s::vector" in query
    assert "(embedding_vector <=> %s::vector) AS vector_distance" in query
    assert params == (
        "[0.25,-1.0]",
        ["project"],
        ["project"],
        ["private"],
        ["private"],
        None,  # memory_types unset
        None,
        None,  # projects unset
        None,
        None,  # created_by_agent_ids unset
        None,
        None,  # run_id unset
        None,
        False,  # include_expired defaults to excluded
        "[0.25,-1.0]",
        12,
    )


def test_update_memory_embedding_and_missing_embedding_listing() -> None:
    memory_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[{"id": memory_id}],
        fetchall_result=[{"id": memory_id}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    updated = store.update_memory_embedding(memory_id=memory_id, vector=[1.0, 0.5])
    missing = store.list_memories_missing_embeddings(limit=64, after_id=memory_id)

    assert updated == {"id": memory_id}
    assert missing[0]["id"] == memory_id
    update_query, update_params = cursor.executed[0]
    assert "SET embedding_vector = %s::vector" in update_query
    assert update_params == ("[1.0,0.5]", memory_id)
    missing_query, missing_params = cursor.executed[1]
    assert "embedding_vector IS NULL" in missing_query
    assert "%s::uuid IS NULL OR id > %s::uuid" in missing_query
    assert "ORDER BY id ASC" in missing_query
    assert missing_params == (memory_id, memory_id, 64)


def test_targeted_memory_lookups_use_indexed_columns() -> None:
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": "memory-digest"},
            {"id": "memory-confirmation"},
            {"id": "memory-latest"},
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    by_digest = store.get_memory_by_commit_digest("digest-1")
    by_confirmation = store.get_memory_by_confirmation_id("confirm-1")
    latest = store.latest_agentic_commit_memory(agent_id="hermes")

    assert by_digest == {"id": "memory-digest"}
    assert by_confirmation == {"id": "memory-confirmation"}
    assert latest == {"id": "memory-latest"}
    digest_query, digest_params = cursor.executed[0]
    assert "WHERE commit_digest = %s" in digest_query
    assert "LIMIT 1" in digest_query
    assert digest_params == ("digest-1",)
    confirmation_query, confirmation_params = cursor.executed[1]
    assert "WHERE confirmation_id = %s" in confirmation_query
    assert "LIMIT 1" in confirmation_query
    assert confirmation_params == ("confirm-1",)
    latest_query, latest_params = cursor.executed[2]
    assert "metadata_json #>> '{agentic_memory,kind}' = 'agentic_memory_commit'" in latest_query
    assert "status = 'active'" in latest_query
    assert "metadata_json #>> '{agentic_memory,agent_identity,agent_id}' = %s" in latest_query
    assert "ORDER BY updated_at DESC, created_at DESC, id DESC" in latest_query
    assert latest_params == ("hermes", "hermes", "hermes")


def test_create_memory_persists_commit_digest_and_confirmation_id_columns() -> None:
    memory_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": memory_id, "memory_key": "agentic_memory.semantic.digest-1"},
            _event_row(memory_id),
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_memory(
        {
            "memory_key": "agentic_memory.semantic.digest-1",
            "value": {"text": "Fact"},
            "canonical_text": "Fact",
            "commit_digest": "digest-1",
            "confirmation_id": "confirm-1",
        }
    )

    insert_query, insert_params = cursor.executed[0]
    assert "commit_digest" in insert_query
    assert "confirmation_id" in insert_query
    assert insert_params is not None
    # Tail: commit_digest, confirmation_id, then the (unset) scope and
    # supersession-pointer columns.
    assert insert_params[-7:] == ("digest-1", "confirm-1", None, None, None, None, None)


def test_create_memory_persists_first_class_scope_columns() -> None:
    memory_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": memory_id, "memory_key": "agentic_memory.project_fact.scope-1"},
            _event_row(memory_id),
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_memory(
        {
            "memory_key": "agentic_memory.project_fact.scope-1",
            "value": {"text": "Scoped fact"},
            "canonical_text": "Scoped fact",
            "project_id": "alicebot",
            "created_by_agent_id": "openclaw",
            "run_id": "run-2026-07-04-001",
        }
    )

    insert_query, insert_params = cursor.executed[0]
    assert "project_id" in insert_query
    assert "created_by_agent_id" in insert_query
    assert "run_id" in insert_query
    assert insert_params is not None
    # Tail: the scope columns, then the (unset) supersession pointers.
    assert insert_params[-5:] == ("alicebot", "openclaw", "run-2026-07-04-001", None, None)


def test_create_agent_api_key_persists_project_scope_binding() -> None:
    key_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": key_id,
                "agent_id": "openclaw",
                "permission_profile": "project_scoped_agent",
                "project_scope": "alicebot",
                "key_prefix": "alice_sk_abc",
                "label": None,
            },
            _event_row(key_id),
        ],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    row = store.create_agent_api_key(
        {
            "agent_id": "openclaw",
            "permission_profile": "project_scoped_agent",
            "project_scope": "alicebot",
            "key_hash": "a" * 64,
            "key_prefix": "alice_sk_abc",
        }
    )

    assert row["project_scope"] == "alicebot"
    insert_query, insert_params = cursor.executed[0]
    assert "INSERT INTO agent_api_keys" in insert_query
    assert "project_scope" in insert_query
    assert insert_params is not None
    assert insert_params[3] == "alicebot"
    # Unbound keys keep a NULL project_scope.
    cursor.executed.clear()
    cursor.fetchone_results = [
        {"id": key_id, "agent_id": "hermes", "permission_profile": "trusted_local_agent", "project_scope": None, "key_prefix": "alice_sk_def", "label": None},
        _event_row(key_id),
    ]
    unbound = store.create_agent_api_key(
        {
            "agent_id": "hermes",
            "permission_profile": "trusted_local_agent",
            "key_hash": "b" * 64,
            "key_prefix": "alice_sk_def",
        }
    )
    assert unbound["project_scope"] is None
    assert cursor.executed[0][1][3] is None


# -- temporal slice: edge event time, as-of reads, supersession pointers -------


def test_create_edge_populates_observed_at_and_defaults_valid_from_to_event_time() -> None:
    edge_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": edge_id, "edge_type": "supports"},
            _event_row(edge_id),
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_edge(
        {
            "id": edge_id,
            "from_type": "source",
            "from_id": "source-1",
            "to_type": "memory",
            "to_id": "memory-1",
            "edge_type": "supports",
            "created_by": "system",
            "observed_at": "2026-07-01T00:00:00Z",
        }
    )

    insert_query, insert_params = cursor.executed[0]
    assert "observed_at" in insert_query
    # observed_at defaults to write time; valid_from defaults to observed_at
    # (then write time), so the validity interval starts at event time.
    assert "COALESCE(%s::timestamptz, now())" in insert_query
    assert "COALESCE(%s::timestamptz, %s::timestamptz, now())" in insert_query
    assert insert_params is not None
    assert insert_params[9] == "2026-07-01T00:00:00Z"  # observed_at
    assert insert_params[10] is None  # valid_from not passed explicitly...
    assert insert_params[11] == "2026-07-01T00:00:00Z"  # ...so it falls back to observed_at
    metadata_param = insert_params[-1]
    assert isinstance(metadata_param, Jsonb)
    # Real event time was provided: no write-time fallback note.
    assert "observed_at_source" not in metadata_param.obj


def test_create_edge_without_event_time_notes_the_write_time_fallback_in_metadata() -> None:
    edge_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": edge_id, "edge_type": "belongs_to_project"},
            _event_row(edge_id),
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_edge(
        {
            "id": edge_id,
            "from_type": "memory",
            "from_id": "memory-1",
            "to_type": "project",
            "to_id": "alice-vnext",
            "edge_type": "belongs_to_project",
            "created_by": "user",
            "metadata_json": {"review_action": "assign_project"},
        }
    )

    _insert_query, insert_params = cursor.executed[0]
    assert insert_params is not None
    metadata_param = insert_params[-1]
    assert isinstance(metadata_param, Jsonb)
    assert metadata_param.obj["observed_at_source"] == "now"
    # Caller metadata is preserved alongside the note.
    assert metadata_param.obj["review_action"] == "assign_project"


def test_list_edges_as_of_filters_on_the_validity_interval_with_limit() -> None:
    cursor = RecordingCursor(fetchone_results=[], fetchall_result=[])
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.list_edges_as_of("2026-07-01T00:00:00Z", limit=5)

    query, params = cursor.executed[0]
    assert "FROM graph_edges" in query
    # Half-open interval: valid_from <= at < valid_to; NULL valid_from
    # (pre-slice edges with unrecorded event time) never matches.
    assert "valid_from IS NOT NULL" in query
    assert "valid_from <= %s::timestamptz" in query
    assert "valid_to IS NULL OR valid_to > %s::timestamptz" in query
    assert "LIMIT %s" in query
    assert params == ("2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z", 5)


def test_memory_writes_accept_supersession_pointer_columns() -> None:
    memory_id = str(uuid4())
    successor_id = str(uuid4())
    predecessor_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": memory_id},
            _event_row(memory_id),
            {"id": memory_id},
            _event_row(memory_id),
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    store.create_memory(
        {
            "memory_key": "agentic_memory.semantic.replacement-1",
            "value": {"text": "Replacement fact"},
            "canonical_text": "Replacement fact",
            "supersedes": predecessor_id,
        }
    )
    store.update_memory(
        memory_id=memory_id,
        patch={"status": "superseded", "superseded_by": successor_id},
    )

    insert_query, insert_params = cursor.executed[0]
    assert "supersedes" in insert_query
    assert insert_params is not None
    assert insert_params[-2:] == (None, predecessor_id)  # (superseded_by, supersedes)

    update_query, update_params = cursor.executed[2]
    assert "superseded_by = COALESCE(%s::uuid, superseded_by)" in update_query
    assert "supersedes = COALESCE(%s::uuid, supersedes)" in update_query
    assert update_params is not None
    assert successor_id in update_params


# -- entity substrate: resolution, mentions, relationship history ---------------


def test_entity_crud_methods_normalize_names_and_write_audit_events() -> None:
    entity_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": entity_id, "entity_type": "organization"},
            _event_row(entity_id),
            {"id": entity_id},
            {"id": entity_id},
            {"id": entity_id},
            _event_row(entity_id),
        ],
        fetchall_result=[{"id": entity_id, "entity_type": "organization"}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    created = store.create_entity(
        {
            "id": entity_id,
            "entity_type": "organization",
            "name": "OpenAI, Inc.",
            "aliases": ["open ai"],
            "metadata_json": {"hq": "sf"},
        }
    )
    fetched = store.get_entity(entity_id)
    by_name = store.get_entity_by_normalized_name("organization", "openai inc")
    listed = store.list_entities(entity_type="organization", limit=7)
    updated = store.update_entity(
        entity_id=entity_id, patch={"name": "OpenAI", "aliases": ["oai"]}
    )

    assert created["id"] == entity_id
    assert fetched is not None
    assert by_name is not None
    assert listed[0]["id"] == entity_id
    assert updated["id"] == entity_id
    assert _event_log_insert_count(cursor) == 2

    insert_query, insert_params = cursor.executed[0]
    assert "INSERT INTO vnext_entities" in insert_query
    assert "app.current_user_id()" in insert_query
    assert insert_params is not None
    assert insert_params[0] == entity_id
    assert insert_params[1] == "organization"
    assert insert_params[2] == "OpenAI, Inc."  # display name keeps its casing
    assert insert_params[3] == "openai inc"  # resolution key computed via normalize_entity_name
    assert isinstance(insert_params[4], Jsonb)
    assert insert_params[4].obj == ["open ai"]
    assert isinstance(insert_params[5], Jsonb)
    assert insert_params[5].obj == {"hq": "sf"}
    assert insert_params[8] == 0  # mention_count defaults to zero

    get_query, get_params = cursor.executed[2]
    assert "FROM vnext_entities" in get_query
    assert "WHERE id = %s::uuid" in get_query
    assert "deleted_at IS NULL" in get_query
    assert get_params == (entity_id,)

    by_name_query, by_name_params = cursor.executed[3]
    assert "entity_type = %s" in by_name_query
    assert "normalized_name = %s" in by_name_query
    assert "LIMIT 1" in by_name_query
    assert by_name_params == ("organization", "openai inc")

    list_query, list_params = cursor.executed[4]
    assert "%s::text IS NULL OR entity_type = %s" in list_query
    assert "ORDER BY updated_at DESC, created_at DESC, id DESC" in list_query
    assert list_params == ("organization", "organization", 7)

    update_query, update_params = cursor.executed[5]
    assert "UPDATE vnext_entities" in update_query
    assert "name = COALESCE(%s, name)" in update_query
    assert "aliases = COALESCE(%s, aliases)" in update_query
    assert "deleted_at IS NULL" in update_query
    assert update_params is not None
    assert update_params[0] == "OpenAI"
    assert isinstance(update_params[1], Jsonb)
    assert update_params[1].obj == ["oai"]
    assert update_params[-1] == entity_id


def test_update_entity_rejects_immutable_patch_fields_before_touching_sql() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = PostgresVNextStore(RecordingConnection(cursor))

    for immutable_patch in (
        {"normalized_name": "hijacked"},
        {"entity_type": "person"},
        {"id": str(uuid4())},
        {"user_id": str(uuid4())},
    ):
        with pytest.raises(ContinuityStoreInvariantError, match="immutable"):
            store.update_entity(entity_id=str(uuid4()), patch=immutable_patch)
    assert cursor.executed == []


def test_find_entities_by_names_matches_normalized_names_and_aliases_in_one_query() -> None:
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[{"id": "entity-1", "normalized_name": "openai"}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    rows = store.find_entities_by_names(("openai", "type3.capital"))

    assert rows[0]["id"] == "entity-1"
    assert len(cursor.executed) == 1  # one round trip covers both match paths
    query, params = cursor.executed[0]
    assert "FROM vnext_entities" in query
    assert "normalized_name = ANY(%s::text[])" in query
    assert "aliases ?| %s::text[]" in query
    assert "deleted_at IS NULL" in query
    assert "ORDER BY mention_count DESC, updated_at DESC, id DESC" in query
    assert params == (["openai", "type3.capital"], ["openai", "type3.capital"])

    # An empty name tuple short-circuits without touching the database.
    assert store.find_entities_by_names(()) == []
    assert len(cursor.executed) == 1


def test_record_entity_mention_increments_count_and_widens_window() -> None:
    entity_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": entity_id},
            _event_row(entity_id),
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    row = store.record_entity_mention(
        entity_id=entity_id, observed_at="2026-05-01T00:00:00Z", source_id="source-1"
    )

    assert row["id"] == entity_id
    assert _event_log_insert_count(cursor) == 1
    query, params = cursor.executed[0]
    assert "mention_count = mention_count + 1" in query
    assert "LEAST(COALESCE(first_observed_at, %s::timestamptz), %s::timestamptz)" in query
    assert "GREATEST(COALESCE(last_observed_at, %s::timestamptz), %s::timestamptz)" in query
    assert "deleted_at IS NULL" in query
    assert params == (
        "2026-05-01T00:00:00Z",
        "2026-05-01T00:00:00Z",
        "2026-05-01T00:00:00Z",
        "2026-05-01T00:00:00Z",
        entity_id,
    )

    # Missing observed_at fails loudly before any SQL runs.
    fresh_cursor = RecordingCursor(fetchone_results=[])
    fresh_store = PostgresVNextStore(RecordingConnection(fresh_cursor))
    with pytest.raises(ContinuityStoreInvariantError, match="observed_at"):
        fresh_store.record_entity_mention(entity_id=entity_id, observed_at=None)
    assert fresh_cursor.executed == []


def test_record_relationship_change_appends_history_and_updates_current_pointer() -> None:
    entity_id = str(uuid4())
    event_id = str(uuid4())
    source_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[
            {"relationship_type_before": "advisor"},
            {"id": event_id, "relationship_type_after": "investor"},
            {"id": entity_id},
            _event_row(entity_id),
        ]
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    row = store.record_relationship_change(
        entity_id=entity_id,
        relationship_type="investor",
        changed_at="2026-02-01T00:00:00Z",
        source_id=source_id,
        metadata_json={"round": "seed"},
    )

    assert row["id"] == event_id
    assert _event_log_insert_count(cursor) == 1

    before_query, before_params = cursor.executed[0]
    assert "metadata_json ->> 'relationship_type'" in before_query
    assert "deleted_at IS NULL" in before_query
    assert before_params == (entity_id,)

    insert_query, insert_params = cursor.executed[1]
    assert "INSERT INTO entity_relationship_events" in insert_query
    assert "app.current_user_id()" in insert_query
    assert insert_params is not None
    assert insert_params[0] == entity_id
    assert insert_params[1] == "advisor"  # before comes from the current pointer
    assert insert_params[2] == "investor"
    assert insert_params[3] == "2026-02-01T00:00:00Z"
    assert insert_params[4] == source_id
    assert isinstance(insert_params[5], Jsonb)
    assert insert_params[5].obj == {"round": "seed"}

    pointer_query, pointer_params = cursor.executed[2]
    assert "UPDATE vnext_entities" in pointer_query
    assert "metadata_json = metadata_json || %s" in pointer_query
    assert pointer_params is not None
    assert isinstance(pointer_params[0], Jsonb)
    assert pointer_params[0].obj == {"relationship_type": "investor"}
    assert pointer_params[1] == entity_id

    event_query, event_params = cursor.executed[3]
    assert "INSERT INTO event_log" in event_query
    assert event_params is not None
    assert isinstance(event_params[7], Jsonb)
    assert event_params[7].obj["relationship_type_before"] == "advisor"
    assert event_params[7].obj["relationship_type_after"] == "investor"
    assert event_params[7].obj["relationship_event_id"] == event_id

    # A missing entity aborts after the lookup, before any history is written.
    missing_cursor = RecordingCursor(fetchone_results=[])
    missing_store = PostgresVNextStore(RecordingConnection(missing_cursor))
    with pytest.raises(ContinuityStoreInvariantError, match="existing entity"):
        missing_store.record_relationship_change(entity_id=entity_id, relationship_type="advisor")
    assert len(missing_cursor.executed) == 1


def test_list_relationship_events_reads_history_most_recent_first() -> None:
    entity_id = str(uuid4())
    cursor = RecordingCursor(
        fetchone_results=[],
        fetchall_result=[{"id": "event-1", "relationship_type_after": "investor"}],
    )
    store = PostgresVNextStore(RecordingConnection(cursor))

    rows = store.list_relationship_events(entity_id)

    assert rows[0]["id"] == "event-1"
    query, params = cursor.executed[0]
    assert "FROM entity_relationship_events" in query
    assert "WHERE entity_id = %s::uuid" in query
    assert "ORDER BY changed_at DESC, id DESC" in query
    assert params == (entity_id,)
