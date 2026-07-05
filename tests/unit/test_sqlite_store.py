from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import (
    SQLiteVNextStore,
    ensure_sqlite_user,
    sqlite_user_connection,
)
from alicebot_api.store import ContinuityStoreInvariantError


def _open_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    return conn


def _make_store(conn: sqlite3.Connection, *, email: str | None = None) -> SQLiteVNextStore:
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, email or f"{user_id}@example.com", "Test User")
    return SQLiteVNextStore(conn, user_id)


def _create_source(store: SQLiteVNextStore, **overrides: object) -> dict[str, object]:
    source: dict[str, object] = {
        "source_type": "document",
        "title": "Spec",
        "content_hash": f"sha256:{uuid4()}",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {"path": "docs/spec.md"},
    }
    source.update(overrides)
    return store.create_source(source)


def _create_memory(store: SQLiteVNextStore, **overrides: object) -> dict[str, object]:
    memory: dict[str, object] = {
        "memory_key": f"memory.{uuid4()}",
        "value": {"text": "Alice remembers"},
        "status": "active",
        "title": "Alice memory",
        "canonical_text": "Alice remembers everything important",
        "summary": "a memory",
        "domain": "project",
        "sensitivity": "private",
    }
    memory.update(overrides)
    return store.create_memory(memory)


# -- schema ------------------------------------------------------------------


def test_bootstrap_sqlite_schema_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    bootstrap_sqlite_schema(conn)
    bootstrap_sqlite_schema(conn)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    for expected in (
        "users",
        "sources",
        "source_chunks",
        "memories",
        "memory_revisions",
        "provenance_links",
        "open_loops",
        "event_log",
        "agent_identities",
        "agent_api_keys",
        "memories_fts",
    ):
        assert expected in tables
    conn.close()


def test_bootstrap_sqlite_schema_is_idempotent_across_file_connections(tmp_path: Path) -> None:
    db_path = tmp_path / "alice.db"
    for _ in range(2):
        conn = sqlite3.connect(str(db_path))
        bootstrap_sqlite_schema(conn)
        conn.commit()
        conn.close()
    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    assert conn.execute("SELECT count(*) FROM memories").fetchone()[0] == 0
    conn.close()


def test_ensure_sqlite_user_is_idempotent() -> None:
    conn = _open_connection()
    user_id = str(uuid4())
    first = ensure_sqlite_user(conn, user_id, "sam@example.com", "Sam")
    second = ensure_sqlite_user(conn, user_id, "sam@example.com", "Sam")
    assert first["id"] == user_id
    assert second == first
    assert conn.execute("SELECT count(*) FROM users").fetchone()[0] == 1
    conn.close()


def test_sqlite_user_connection_commits_on_success_and_rolls_back_on_error(tmp_path: Path) -> None:
    db_path = tmp_path / "alice.db"
    user_id = str(uuid4())

    with sqlite_user_connection(db_path, user_id) as conn:
        ensure_sqlite_user(conn, user_id, "sam@example.com", "Sam")
        store = SQLiteVNextStore(conn, user_id)
        committed = _create_source(store, content_hash="sha256:committed")

    with pytest.raises(RuntimeError, match="boom"):
        with sqlite_user_connection(db_path, user_id) as conn:
            store = SQLiteVNextStore(conn, user_id)
            _create_source(store, content_hash="sha256:rolled-back")
            raise RuntimeError("boom")

    with sqlite_user_connection(db_path, user_id) as conn:
        store = SQLiteVNextStore(conn, user_id)
        assert store.get_source_by_content_hash("sha256:committed") is not None
        assert store.get_source_by_content_hash("sha256:rolled-back") is None
        assert store.get_source(committed["id"]) is not None


def test_sqlite_user_connection_rejects_empty_user_id(tmp_path: Path) -> None:
    with pytest.raises(ContinuityStoreInvariantError):
        with sqlite_user_connection(tmp_path / "alice.db", ""):
            pass  # pragma: no cover
    with pytest.raises(ContinuityStoreInvariantError):
        SQLiteVNextStore(sqlite3.connect(":memory:"), " ")


# -- user scoping --------------------------------------------------------------


def test_every_read_method_is_scoped_to_the_bound_user() -> None:
    conn = _open_connection()
    alice = _make_store(conn)
    mallory = _make_store(conn)

    source = _create_source(alice, content_hash="sha256:scoped")
    chunk = alice.create_source_chunk({"source_id": source["id"], "chunk_index": 0, "text": "chunk text"})
    memory = _create_memory(alice, canonical_text="Kubernetes deployment pipeline notes")
    alice.update_memory_embedding(memory_id=memory["id"], vector=[1.0, 0.0, 0.0])
    revision = alice.append_revision(
        {"memory_id": memory["id"], "memory_key": memory["memory_key"], "text_after": "after"}
    )
    alice.create_provenance_link(
        {"target_type": "memory", "target_id": memory["id"], "source_id": source["id"]}
    )
    loop = alice.create_open_loop({"title": "Ship the SQLite on-ramp"})
    alice.upsert_agent_identity({"agent_id": "hermes"})
    key = alice.create_agent_api_key(
        {
            "agent_id": "hermes",
            "permission_profile": "read_only_agent",
            "key_hash": "a" * 64,
            "key_prefix": "ak_live_a",
        }
    )

    # Alice sees her own data.
    assert alice.get_memory(memory["id"]) is not None
    assert alice.list_memories()
    assert alice.list_events()
    assert [row["id"] for row in alice.list_source_chunks(source["id"])] == [chunk["id"]]

    # Mallory must see none of it, on every read method.
    assert mallory.list_events() == []
    assert mallory.list_events(target_type="memory", target_id=str(memory["id"])) == []
    assert mallory.get_source(source["id"]) is None
    assert mallory.get_source_by_content_hash("sha256:scoped") is None
    assert mallory.list_source_chunks(source["id"]) == []
    assert mallory.search_sources(query="spec") == []
    assert mallory.get_memory(memory["id"]) is None
    assert mallory.list_memories() == []
    assert mallory.list_memories(status="active") == []
    assert mallory.search_memories(query="kubernetes") == []
    assert mallory.search_memories_fts(query="kubernetes") == []
    assert mallory.search_memories_vector(query_vector=[1.0, 0.0, 0.0]) == []
    assert mallory.list_revisions(memory["id"]) == []
    assert mallory.list_provenance_links(target_type="memory", target_id=str(memory["id"])) == []
    assert mallory.list_open_loops() == []
    assert mallory.get_open_loop(loop["id"]) is None
    assert mallory.get_agent_api_key_by_hash("a" * 64) is None
    assert mallory.list_agent_api_keys() == []
    assert mallory.count_active_agent_api_keys() == 0
    assert mallory.list_agent_identities() == []
    assert mallory.list_agent_events() == []

    # Mallory cannot mutate Alice's rows either.
    with pytest.raises(ContinuityStoreInvariantError):
        mallory.update_memory(memory_id=memory["id"], patch={"title": "stolen"})
    with pytest.raises(ContinuityStoreInvariantError):
        mallory.update_open_loop(loop_id=loop["id"], patch={"title": "stolen"})
    with pytest.raises(ContinuityStoreInvariantError):
        mallory.update_open_loop_status(loop_id=loop["id"], status="resolved")
    with pytest.raises(ContinuityStoreInvariantError):
        mallory.touch_agent_api_key(key_id=key["id"])
    assert mallory.revoke_agent_api_key(key_id=key["id"]) is None
    assert mallory.update_memory_embedding(memory_id=memory["id"], vector=[1.0]) is None

    # Nothing Mallory attempted altered Alice's view.
    assert alice.get_memory(memory["id"])["title"] == memory["title"]
    assert alice.count_active_agent_api_keys() == 1
    assert [row["id"] for row in alice.list_revisions(memory["id"])] == [revision["id"]]
    conn.close()


# -- capture-shaped flow --------------------------------------------------------


def test_capture_flow_source_chunks_memory_provenance_and_events() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    source = _create_source(store, content_hash="sha256:capture")
    assert store.get_source_by_content_hash("sha256:capture")["id"] == source["id"]

    chunk_one = store.create_source_chunk(
        {"source_id": source["id"], "chunk_index": 0, "text": "first", "token_count": 1}
    )
    chunk_two = store.create_source_chunk(
        {"source_id": source["id"], "chunk_index": 1, "text": "second", "metadata_json": {"kind": "para"}}
    )
    chunks = store.list_source_chunks(source["id"])
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]
    assert chunks[0]["id"] == chunk_one["id"]
    assert chunks[1]["metadata_json"] == {"kind": "para"}

    memory = _create_memory(store, memory_type="decision", status="active")
    assert memory["memory_type"] == "decision"
    assert memory["value"] == {"text": "Alice remembers"}
    assert memory["source_event_ids"] == []
    assert memory["metadata_json"] == {}
    assert isinstance(memory["id"], str)
    assert isinstance(memory["created_at"], str)
    assert memory["created_at"].endswith("Z")

    link = store.create_provenance_link(
        {
            "target_type": "memory",
            "target_id": memory["id"],
            "source_id": source["id"],
            "source_chunk_id": chunk_one["id"],
            "quote": "first",
        }
    )
    assert link["evidence_role"] == "supports"
    assert link["confidence"] == 0.5
    links = store.list_provenance_links(target_type="memory", target_id=str(memory["id"]))
    assert [row["id"] for row in links] == [link["id"]]

    event_types = [event["event_type"] for event in store.list_events()]
    assert event_types.count("source.created") == 1
    assert event_types.count("source_chunk.created") == 2
    assert event_types.count("memory.created") == 1
    assert event_types.count("provenance_link.created") == 1

    memory_events = store.list_events(target_type="memory", target_id=str(memory["id"]))
    assert {event["event_type"] for event in memory_events} == {
        "memory.created",
        "provenance_link.created",
    }
    limited = store.list_events(limit=2)
    assert len(limited) == 2
    conn.close()


def test_mutation_events_carry_payload_and_integrity_fields() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    source = _create_source(store)
    events = store.list_events(target_type="source", target_id=str(source["id"]))
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "source.created"
    assert event["actor_type"] == "system"
    assert event["payload_json"]["operation"] == "create"
    assert "content_hash" in event["payload_json"]["fields"]
    assert event["integrity_hash"]
    assert event["user_id"] == store.user_id
    conn.close()


# -- event log append-only --------------------------------------------------------


def test_event_log_rejects_update_and_delete() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    _create_source(store)
    assert conn.execute("SELECT count(*) FROM event_log").fetchone()[0] >= 1
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE event_log SET event_type = 'tampered'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM event_log")
    conn.close()


def test_memory_revisions_reject_update_and_delete() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store)
    store.append_revision({"memory_id": memory["id"], "memory_key": memory["memory_key"], "text_after": "x"})
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE memory_revisions SET reason = 'tampered'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM memory_revisions")
    conn.close()


# -- memory CRUD and constraints ---------------------------------------------------


def test_create_memory_rejects_invalid_enum_values() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _create_memory(store, memory_type="not_a_type")
    with pytest.raises(sqlite3.IntegrityError):
        _create_memory(store, status="not_a_status")
    with pytest.raises(sqlite3.IntegrityError):
        _create_memory(store, domain="not_a_domain")
    with pytest.raises(sqlite3.IntegrityError):
        _create_memory(store, sensitivity="not_a_sensitivity")
    with pytest.raises(sqlite3.IntegrityError):
        _create_memory(store, trust_class="not_a_trust_class")
    with pytest.raises(sqlite3.IntegrityError):
        _create_memory(store, confidence=1.5)
    conn.close()


def test_duplicate_memory_key_for_same_profile_is_rejected() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    _create_memory(store, memory_key="memory.duplicate")
    with pytest.raises(sqlite3.IntegrityError):
        _create_memory(store, memory_key="memory.duplicate")
    conn.close()


def test_update_memory_applies_patch_and_archives() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store, status="candidate")

    updated = store.update_memory(
        memory_id=memory["id"],
        patch={"status": "active", "title": "Updated title", "metadata_json": {"reviewed": True}},
    )
    assert updated["status"] == "active"
    assert updated["title"] == "Updated title"
    assert updated["metadata_json"] == {"reviewed": True}
    assert updated["canonical_text"] == memory["canonical_text"]
    assert updated["updated_at"] >= memory["updated_at"]

    update_events = [
        event
        for event in store.list_events(target_type="memory", target_id=str(memory["id"]))
        if event["event_type"] == "memory.updated"
    ]
    assert len(update_events) == 1
    assert update_events[0]["payload_json"]["changes"]["status"] == "active"

    archived = store.update_memory(memory_id=memory["id"], patch={"status": "archived"})
    assert archived["deleted_at"] is not None
    assert store.get_memory(memory["id"]) is None
    assert store.list_memories() == []

    with pytest.raises(ContinuityStoreInvariantError):
        store.update_memory(memory_id=memory["id"], patch={"title": "gone"})
    with pytest.raises(ContinuityStoreInvariantError):
        store.update_memory(memory_id=str(uuid4()), patch={"title": "missing"})
    conn.close()


def test_list_memories_filters_by_status_and_orders_by_recency() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    first = _create_memory(store, status="candidate")
    second = _create_memory(store, status="active")
    store.update_memory(memory_id=first["id"], patch={"salience": 0.9})

    everything = store.list_memories()
    assert {row["id"] for row in everything} == {first["id"], second["id"]}
    assert everything[0]["id"] == first["id"]  # most recently updated first

    candidates = store.list_memories(status="candidate")
    assert [row["id"] for row in candidates] == [first["id"]]
    conn.close()


# -- revisions -----------------------------------------------------------------------


def test_append_revision_assigns_sequential_numbers_and_lists_in_order() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store)

    first = store.append_revision(
        {
            "memory_id": memory["id"],
            "memory_key": memory["memory_key"],
            "new_value": {"text": "v1"},
            "revision_type": "created",
            "text_after": "v1",
        }
    )
    second = store.append_revision(
        {
            "memory_id": memory["id"],
            "memory_key": memory["memory_key"],
            "previous_value": {"text": "v1"},
            "new_value": {"text": "v2"},
            "text_after": "v2",
            "reason": "correction",
        }
    )

    assert first["sequence_no"] == 1
    assert first["revision_number"] == 1
    assert first["revision_type"] == "created"
    assert second["sequence_no"] == 2
    assert second["revision_number"] == 2
    assert second["revision_type"] == "edited"
    assert second["previous_value"] == {"text": "v1"}
    assert second["new_value"] == {"text": "v2"}
    assert second["candidate"] == {}

    listed = store.list_revisions(memory["id"])
    assert [row["id"] for row in listed] == [first["id"], second["id"]]

    revision_events = [
        event
        for event in store.list_events(target_type="memory", target_id=str(memory["id"]))
        if event["event_type"] == "memory_revision.created"
    ]
    assert len(revision_events) == 2
    conn.close()


# -- keyword (LIKE) search --------------------------------------------------------------


def test_search_memories_like_fallback_matches_text_and_json_value() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    match = _create_memory(
        store,
        title="Deployment runbook",
        canonical_text="The Kubernetes deployment pipeline uses ArgoCD",
        value={"tool": "argocd"},
    )
    _create_memory(store, title="Groceries", canonical_text="Buy oat milk", value={"list": True})
    _create_memory(store, title="Hidden candidate", status="candidate", canonical_text="ArgoCD secrets")

    rows = store.search_memories(query="argocd")
    assert [row["id"] for row in rows] == [match["id"]]

    quoted = store.search_memories(query='"Kubernetes deployment"')
    assert [row["id"] for row in quoted] == [match["id"]]

    # value::text JSON match
    value_rows = store.search_memories(query="tool")
    assert [row["id"] for row in value_rows] == [match["id"]]
    conn.close()


def test_search_memories_applies_domain_and_sensitivity_filters() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    project = _create_memory(store, canonical_text="shared keyword alpha", domain="project", sensitivity="private")
    unknown = _create_memory(store, canonical_text="shared keyword beta", domain="unknown", sensitivity="private")
    _create_memory(store, canonical_text="shared keyword gamma", domain="health", sensitivity="highly_sensitive")

    rows = store.search_memories(
        query="shared keyword",
        domains=["project"],
        sensitivity_allowed=["private", "internal"],
    )
    assert {row["id"] for row in rows} == {project["id"], unknown["id"]}  # unknown domain passes through
    conn.close()


def test_search_sources_matches_metadata_and_ranks_title_first() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    titled = _create_source(store, title="Retrieval design", content_hash="sha256:t1")
    metadata_only = _create_source(
        store,
        title="Other",
        content_hash="sha256:t2",
        metadata_json={"topic": "retrieval design"},
    )
    rows = store.search_sources(query="retrieval design")
    assert [row["id"] for row in rows][0] == titled["id"]
    assert {row["id"] for row in rows} == {titled["id"], metadata_only["id"]}
    conn.close()


# -- FTS search ---------------------------------------------------------------------------


def test_search_memories_fts_ranks_relevant_memory_first() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    relevant = _create_memory(
        store,
        title="Kubernetes deployment",
        canonical_text="Kubernetes deployment pipeline promotes builds through staging",
        summary="Kubernetes deployment notes",
    )
    _create_memory(
        store,
        title="Cooking",
        canonical_text="Slow-cooked ragu recipe with pasta",
        summary="dinner ideas",
    )
    weaker = _create_memory(
        store,
        title="Infra weekly",
        canonical_text="Notes that mention deployment once",
        summary="weekly notes",
    )

    rows = store.search_memories_fts(query="kubernetes deployment")
    assert [row["id"] for row in rows] == [relevant["id"]]

    rows = store.search_memories_fts(query="deployment")
    assert {row["id"] for row in rows} == {relevant["id"], weaker["id"]}
    assert rows[0]["id"] == relevant["id"]
    assert all("fts_score" in row for row in rows)
    assert rows[0]["fts_score"] >= rows[-1]["fts_score"]
    conn.close()


def test_search_memories_fts_supports_quoted_phrases() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    phrase = _create_memory(store, canonical_text="continuity layer for AI agents")
    _create_memory(store, canonical_text="agents crave a layer of continuity eventually")

    rows = store.search_memories_fts(query='"continuity layer"')
    assert [row["id"] for row in rows] == [phrase["id"]]
    conn.close()


def test_search_memories_fts_is_safe_against_fts5_metacharacters() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store, canonical_text="deployment notes with NEAR misses")

    hostile_queries = [
        'col:*(NEAR "unclosed AND ^',
        "a AND OR NOT (",
        "\"unbalanced",
        "title:deployment*",
        "x ^ y NEAR/3 z",
        "(((((",
        "-deployment",
        '"" "" ""',
    ]
    for hostile in hostile_queries:
        rows = store.search_memories_fts(query=hostile)  # must not raise
        assert isinstance(rows, list)

    # Sanitized empty queries return no rows instead of erroring.
    assert store.search_memories_fts(query="") == []
    assert store.search_memories_fts(query="   ") == []
    assert store.search_memories_fts(query="()^*:") == []

    # A hostile query containing a real term still matches.
    rows = store.search_memories_fts(query="deployment:*(")
    assert [row["id"] for row in rows] == [memory["id"]]
    conn.close()


def test_search_memories_fts_reflects_updates_and_archives() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store, canonical_text="original searchable phrase")

    store.update_memory(memory_id=memory["id"], patch={"canonical_text": "replacement wording"})
    assert store.search_memories_fts(query="searchable") == []
    assert [row["id"] for row in store.search_memories_fts(query="replacement")] == [memory["id"]]

    store.update_memory(memory_id=memory["id"], patch={"status": "archived"})
    assert store.search_memories_fts(query="replacement") == []
    conn.close()


def test_search_memories_fts_applies_domain_and_sensitivity_filters() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    visible = _create_memory(store, canonical_text="filtered term", domain="project", sensitivity="private")
    _create_memory(store, canonical_text="filtered term", domain="health", sensitivity="sacred")

    rows = store.search_memories_fts(
        query="filtered",
        domains=["project"],
        sensitivity_allowed=["private"],
    )
    assert [row["id"] for row in rows] == [visible["id"]]
    conn.close()


# -- memory_type / project / staleness read filters ------------------------------------


def test_search_memories_filters_by_memory_type_across_all_three_methods() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    decision = _create_memory(store, memory_type="decision", canonical_text="shared retrieval keyword decision")
    procedure = _create_memory(store, memory_type="procedure", canonical_text="shared retrieval keyword procedure")
    _create_memory(store, memory_type="preference", canonical_text="shared retrieval keyword preference")
    store.update_memory_embedding(memory_id=decision["id"], vector=[1.0, 0.0])
    store.update_memory_embedding(memory_id=procedure["id"], vector=[0.0, 1.0])

    like_rows = store.search_memories(query="shared retrieval", memory_types=("decision", "procedure"))
    assert {row["id"] for row in like_rows} == {decision["id"], procedure["id"]}

    fts_rows = store.search_memories_fts(query="retrieval", memory_types=("decision",))
    assert [row["id"] for row in fts_rows] == [decision["id"]]

    vector_rows = store.search_memories_vector(query_vector=[1.0, 0.0], memory_types=("procedure",))
    assert [row["id"] for row in vector_rows] == [procedure["id"]]

    # Empty tuple means no filter.
    assert len(store.search_memories(query="shared retrieval", memory_types=())) == 3
    conn.close()


def test_search_memories_filters_by_project_id_in_metadata_json() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    alicebot = _create_memory(
        store,
        canonical_text="project keyword alicebot",
        metadata_json={"project_id": "alicebot"},
    )
    hermes = _create_memory(
        store,
        canonical_text="project keyword hermes",
        metadata_json={"project_id": "hermes"},
    )
    unscoped = _create_memory(store, canonical_text="project keyword unscoped")
    store.update_memory_embedding(memory_id=alicebot["id"], vector=[1.0, 0.0])
    store.update_memory_embedding(memory_id=hermes["id"], vector=[0.0, 1.0])

    rows = store.search_memories(query="project keyword", projects=("alicebot",))
    assert [row["id"] for row in rows] == [alicebot["id"]]

    rows = store.search_memories(query="project keyword", projects=("alicebot", "hermes"))
    assert {row["id"] for row in rows} == {alicebot["id"], hermes["id"]}

    fts_rows = store.search_memories_fts(query="keyword", projects=("hermes",))
    assert [row["id"] for row in fts_rows] == [hermes["id"]]

    vector_rows = store.search_memories_vector(query_vector=[1.0, 0.0], projects=("alicebot",))
    assert [row["id"] for row in vector_rows] == [alicebot["id"]]

    # No projects filter returns everything, including unscoped memories.
    rows = store.search_memories(query="project keyword")
    assert {row["id"] for row in rows} == {alicebot["id"], hermes["id"], unscoped["id"]}
    conn.close()


def test_search_memories_project_filter_prefers_the_real_column_over_metadata() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    column_scoped = _create_memory(
        store,
        canonical_text="scope column keyword one",
        project_id="alicebot",
    )
    metadata_scoped = _create_memory(
        store,
        canonical_text="scope column keyword two",
        metadata_json={"project_id": "alicebot"},
    )
    # Column wins over stale metadata when both are present.
    column_wins = _create_memory(
        store,
        canonical_text="scope column keyword three",
        project_id="hermes",
        metadata_json={"project_id": "alicebot"},
    )

    rows = store.search_memories(query="scope column keyword", projects=("alicebot",))
    assert {row["id"] for row in rows} == {column_scoped["id"], metadata_scoped["id"]}

    rows = store.search_memories(query="scope column keyword", projects=("hermes",))
    assert [row["id"] for row in rows] == [column_wins["id"]]
    conn.close()


def test_create_memory_persists_scope_columns_and_rows_return_them() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    scoped = _create_memory(
        store,
        canonical_text="scoped fact",
        project_id="alicebot",
        created_by_agent_id="openclaw",
        run_id="run-2026-07-04-001",
    )
    unscoped = _create_memory(store, canonical_text="unscoped fact")

    fetched = store.get_memory(scoped["id"])
    assert fetched is not None
    assert fetched["project_id"] == "alicebot"
    assert fetched["created_by_agent_id"] == "openclaw"
    assert fetched["run_id"] == "run-2026-07-04-001"
    plain = store.get_memory(unscoped["id"])
    assert plain is not None
    assert plain["project_id"] is None
    assert plain["created_by_agent_id"] is None
    assert plain["run_id"] is None
    conn.close()


def test_search_memories_filters_by_created_by_agent_and_run_across_all_three_methods() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    openclaw_run_1 = _create_memory(
        store,
        canonical_text="agent scope keyword alpha",
        created_by_agent_id="openclaw",
        run_id="run-1",
    )
    openclaw_run_2 = _create_memory(
        store,
        canonical_text="agent scope keyword beta",
        created_by_agent_id="openclaw",
        run_id="run-2",
    )
    hermes = _create_memory(
        store,
        canonical_text="agent scope keyword gamma",
        created_by_agent_id="hermes",
        run_id="run-3",
    )
    user_written = _create_memory(store, canonical_text="agent scope keyword delta")
    store.update_memory_embedding(memory_id=openclaw_run_1["id"], vector=[1.0, 0.0])
    store.update_memory_embedding(memory_id=hermes["id"], vector=[0.0, 1.0])

    rows = store.search_memories(query="agent scope keyword", created_by_agent_ids=("openclaw",))
    assert {row["id"] for row in rows} == {openclaw_run_1["id"], openclaw_run_2["id"]}

    rows = store.search_memories(
        query="agent scope keyword", created_by_agent_ids=("openclaw", "hermes")
    )
    assert {row["id"] for row in rows} == {openclaw_run_1["id"], openclaw_run_2["id"], hermes["id"]}

    rows = store.search_memories(query="agent scope keyword", run_id="run-2")
    assert [row["id"] for row in rows] == [openclaw_run_2["id"]]

    fts_rows = store.search_memories_fts(query="keyword", created_by_agent_ids=("hermes",))
    assert [row["id"] for row in fts_rows] == [hermes["id"]]
    fts_rows = store.search_memories_fts(query="keyword", run_id="run-1")
    assert [row["id"] for row in fts_rows] == [openclaw_run_1["id"]]

    vector_rows = store.search_memories_vector(
        query_vector=[1.0, 0.0], created_by_agent_ids=("openclaw",)
    )
    assert [row["id"] for row in vector_rows] == [openclaw_run_1["id"]]
    vector_rows = store.search_memories_vector(query_vector=[1.0, 0.0], run_id="run-3")
    assert [row["id"] for row in vector_rows] == [hermes["id"]]

    # No filter returns every writer's memories, including the user's own.
    rows = store.search_memories(query="agent scope keyword")
    assert {row["id"] for row in rows} == {
        openclaw_run_1["id"],
        openclaw_run_2["id"],
        hermes["id"],
        user_written["id"],
    }
    conn.close()


def test_create_agent_api_key_round_trips_project_scope_binding() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    bound = store.create_agent_api_key(
        {
            "agent_id": "openclaw",
            "permission_profile": "project_scoped_agent",
            "project_scope": "alicebot",
            "key_hash": "c" * 64,
            "key_prefix": "alice_sk_ghi",
        }
    )
    unbound = store.create_agent_api_key(
        {
            "agent_id": "hermes",
            "permission_profile": "trusted_local_agent",
            "key_hash": "d" * 64,
            "key_prefix": "alice_sk_jkl",
        }
    )

    assert bound["project_scope"] == "alicebot"
    assert unbound["project_scope"] is None
    fetched = store.get_agent_api_key_by_hash("c" * 64)
    assert fetched is not None
    assert fetched["project_scope"] == "alicebot"
    listed = {row["id"]: row for row in store.list_agent_api_keys()}
    assert listed[bound["id"]]["project_scope"] == "alicebot"
    assert listed[unbound["id"]]["project_scope"] is None
    conn.close()


def test_bootstrap_upgrades_a_pre_existing_db_file_with_scope_columns(tmp_path: Path) -> None:
    """Existing sqlite files (created before the scope columns shipped) are
    upgraded in place by the PRAGMA-guarded ALTER TABLE in bootstrap."""
    db_path = tmp_path / "alice.db"
    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    # Rewind the file to the pre-scope-column schema: drop the new index and
    # columns so the file looks like it was created by the old bootstrap.
    conn.execute("DROP INDEX IF EXISTS memories_user_project_idx")
    for table, column in (
        ("memories", "project_id"),
        ("memories", "created_by_agent_id"),
        ("memories", "run_id"),
        ("agent_api_keys", "project_scope"),
    ):
        conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
    conn.commit()
    old_memory_columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    assert "project_id" not in old_memory_columns
    conn.close()

    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    memory_columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    assert {"project_id", "created_by_agent_id", "run_id"} <= memory_columns
    key_columns = {row[1] for row in conn.execute("PRAGMA table_info(agent_api_keys)")}
    assert "project_scope" in key_columns
    index_names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    }
    assert "memories_user_project_idx" in index_names

    # The upgraded file is fully usable, including the new filters.
    store = _make_store(conn)
    scoped = _create_memory(
        store,
        canonical_text="upgraded db keyword",
        project_id="alicebot",
        created_by_agent_id="openclaw",
        run_id="run-1",
    )
    rows = store.search_memories(query="upgraded db keyword", projects=("alicebot",))
    assert [row["id"] for row in rows] == [scoped["id"]]
    rows = store.search_memories(query="upgraded db keyword", created_by_agent_ids=("openclaw",))
    assert [row["id"] for row in rows] == [scoped["id"]]
    conn.close()


def test_search_memories_excludes_expired_valid_to_unless_include_expired() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    current = _create_memory(store, canonical_text="expiry keyword current")
    future = _create_memory(
        store,
        canonical_text="expiry keyword future",
        valid_from="2020-01-01T00:00:00Z",
        valid_to="2999-01-01T00:00:00Z",
    )
    expired = _create_memory(
        store,
        canonical_text="expiry keyword expired",
        valid_from="2020-01-01T00:00:00Z",
        valid_to="2021-01-01T00:00:00Z",
    )
    store.update_memory_embedding(memory_id=current["id"], vector=[1.0, 0.0])
    store.update_memory_embedding(memory_id=expired["id"], vector=[0.0, 1.0])

    rows = store.search_memories(query="expiry keyword")
    assert {row["id"] for row in rows} == {current["id"], future["id"]}

    rows = store.search_memories(query="expiry keyword", include_expired=True)
    assert {row["id"] for row in rows} == {current["id"], future["id"], expired["id"]}

    fts_rows = store.search_memories_fts(query="expiry")
    assert {row["id"] for row in fts_rows} == {current["id"], future["id"]}
    fts_rows = store.search_memories_fts(query="expiry", include_expired=True)
    assert {row["id"] for row in fts_rows} == {current["id"], future["id"], expired["id"]}

    vector_rows = store.search_memories_vector(query_vector=[1.0, 0.0])
    assert [row["id"] for row in vector_rows] == [current["id"]]
    vector_rows = store.search_memories_vector(query_vector=[1.0, 0.0], include_expired=True)
    assert {row["id"] for row in vector_rows} == {current["id"], expired["id"]}
    conn.close()


def test_stale_status_is_valid_in_schema_but_excluded_from_search() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    active = _create_memory(store, canonical_text="staleness keyword active")
    stale = _create_memory(store, canonical_text="staleness keyword stale", status="stale")
    store.update_memory_embedding(memory_id=active["id"], vector=[1.0, 0.0])
    store.update_memory_embedding(memory_id=stale["id"], vector=[1.0, 0.0])

    # 'stale' passes the CHECK constraint (Wave-1 sibling writes it) ...
    assert stale["status"] == "stale"
    # ... but the read path treats it like superseded/rejected.
    assert [row["id"] for row in store.search_memories(query="staleness keyword")] == [active["id"]]
    assert [row["id"] for row in store.search_memories_fts(query="staleness")] == [active["id"]]
    assert [row["id"] for row in store.search_memories_vector(query_vector=[1.0, 0.0])] == [active["id"]]
    conn.close()


# -- vector search ---------------------------------------------------------------------


def test_vector_store_and_search_roundtrip_with_dimension_padding() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    close = _create_memory(store, canonical_text="vector close")
    far = _create_memory(store, canonical_text="vector far")
    _create_memory(store, canonical_text="no embedding")

    # Short vectors are zero-padded to the 1536-dim storage convention.
    assert store.update_memory_embedding(memory_id=close["id"], vector=[1.0, 0.0, 0.0]) == {"id": close["id"]}
    assert store.update_memory_embedding(memory_id=far["id"], vector=[0.0, 1.0, 0.0]) == {"id": far["id"]}

    blob = conn.execute(
        "SELECT embedding FROM memories WHERE id = ?", (close["id"],)
    ).fetchone()[0]
    assert len(blob) == 1536 * 4  # float32 payload at storage width

    rows = store.search_memories_vector(query_vector=[0.9, 0.1, 0.0])
    assert [row["id"] for row in rows] == [close["id"], far["id"]]
    assert rows[0]["vector_distance"] < rows[1]["vector_distance"]
    assert rows[0]["vector_distance"] == pytest.approx(1.0 - 0.9 / (0.9**2 + 0.1**2) ** 0.5, abs=1e-6)
    assert "embedding" not in rows[0]

    # Same-direction query at full storage width matches the padded vector exactly.
    full_width = [1.0, 0.0, 0.0] + [0.0] * 1533
    exact = store.search_memories_vector(query_vector=full_width, limit=1)
    assert [row["id"] for row in exact] == [close["id"]]
    assert exact[0]["vector_distance"] == pytest.approx(0.0, abs=1e-6)

    filtered = store.search_memories_vector(query_vector=[1.0, 0.0], sensitivity_allowed=["public"])
    assert filtered == []

    with pytest.raises(ContinuityStoreInvariantError):
        store.search_memories_vector(query_vector=[])
    with pytest.raises(ContinuityStoreInvariantError):
        store.update_memory_embedding(memory_id=close["id"], vector=[])
    assert store.update_memory_embedding(memory_id=str(uuid4()), vector=[1.0]) is None
    conn.close()


# -- open loops -------------------------------------------------------------------------


def test_open_loop_crud_lifecycle() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store)

    loop = store.create_open_loop(
        {
            "title": "Follow up with the design partner",
            "memory_id": memory["id"],
            "priority": "high",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"origin": "capture"},
        }
    )
    assert loop["status"] == "open"
    assert loop["priority"] == "high"
    assert loop["metadata_json"] == {"origin": "capture"}
    assert store.get_open_loop(loop["id"])["id"] == loop["id"]

    listed = store.list_open_loops()
    assert [row["id"] for row in listed] == [loop["id"]]
    assert store.list_open_loops(status="resolved") == []
    assert [row["id"] for row in store.list_open_loops(status=None)] == [loop["id"]]

    updated = store.update_open_loop(
        loop_id=loop["id"],
        patch={"description": "Ping them Friday", "priority": "urgent"},
    )
    assert updated["description"] == "Ping them Friday"
    assert updated["priority"] == "urgent"
    assert updated["title"] == loop["title"]

    resolved = store.update_open_loop_status(
        loop_id=loop["id"], status="resolved", resolution_note="Partner confirmed"
    )
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None
    assert resolved["closed_at"] is not None
    assert resolved["resolution_note"] == "Partner confirmed"
    assert store.list_open_loops() == []

    reopened = store.update_open_loop_status(loop_id=loop["id"], status="open")
    assert reopened["resolved_at"] is None
    assert reopened["closed_at"] is None
    assert reopened["resolution_note"] is None

    loop_events = [
        event["event_type"]
        for event in store.list_events(target_type="open_loop", target_id=str(loop["id"]))
    ]
    assert loop_events.count("open_loop.created") == 1
    assert loop_events.count("open_loop.updated") == 3

    with pytest.raises(sqlite3.IntegrityError):
        store.create_open_loop({"title": "bad", "priority": "someday"})
    with pytest.raises(sqlite3.IntegrityError):
        store.create_open_loop({"title": "bad", "status": "unknown_status"})
    conn.close()


def test_list_open_loops_applies_domain_and_sensitivity_filters() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    visible = store.create_open_loop({"title": "visible", "domain": "project", "sensitivity": "private"})
    unknown = store.create_open_loop({"title": "unknown-domain", "domain": "unknown", "sensitivity": "private"})
    store.create_open_loop({"title": "hidden", "domain": "health", "sensitivity": "sacred"})

    rows = store.list_open_loops(domains=["project"], sensitivity_allowed=["private"])
    assert {row["id"] for row in rows} == {visible["id"], unknown["id"]}
    conn.close()


# -- agent identities and keys --------------------------------------------------------------


def test_upsert_agent_identity_merges_metadata_and_keeps_display_name() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    first = store.upsert_agent_identity(
        {
            "agent_id": "hermes",
            "agent_type": "coding_agent",
            "permission_profile": "trusted_local_agent",
            "display_name": "Hermes",
            "metadata_json": {"a": 1, "keep": True},
        }
    )
    assert first["agent_type"] == "coding_agent"
    assert first["project_scope_json"] == []

    second = store.upsert_agent_identity(
        {
            "agent_id": "hermes",
            "agent_type": "coding_agent",
            "permission_profile": "read_only_agent",
            "metadata_json": {"a": 2, "b": 3},
            "project_scope": ["alicebot"],
        }
    )
    assert second["id"] == first["id"]
    assert second["permission_profile"] == "read_only_agent"
    assert second["display_name"] == "Hermes"  # COALESCE keeps the existing name
    assert second["metadata_json"] == {"a": 2, "b": 3, "keep": True}
    assert second["project_scope_json"] == ["alicebot"]
    assert second["updated_at"] >= first["updated_at"]

    identities = store.list_agent_identities()
    assert [row["id"] for row in identities] == [first["id"]]

    with pytest.raises(sqlite3.IntegrityError):
        store.upsert_agent_identity({"agent_id": "bad", "permission_profile": "root"})
    conn.close()


def test_agent_api_key_create_verify_touch_revoke_and_count() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    key = store.create_agent_api_key(
        {
            "agent_id": "hermes",
            "permission_profile": "read_only_agent",
            "key_hash": "b" * 64,
            "key_prefix": "ak_live_b",
            "label": "laptop",
        }
    )
    assert key["label"] == "laptop"
    assert key["revoked_at"] is None
    assert key["last_used_at"] is None

    fetched = store.get_agent_api_key_by_hash("b" * 64)
    assert fetched["id"] == key["id"]
    assert store.get_agent_api_key_by_hash("c" * 64) is None

    touched = store.touch_agent_api_key(key_id=key["id"])
    assert touched["last_used_at"] is not None

    assert store.count_active_agent_api_keys() == 1
    listed = store.list_agent_api_keys()
    assert [row["id"] for row in listed] == [key["id"]]

    revoked = store.revoke_agent_api_key(key_id=key["id"])
    assert revoked["revoked_at"] is not None
    assert store.count_active_agent_api_keys() == 0
    assert store.revoke_agent_api_key(key_id=key["id"]) is None  # already revoked

    key_events = [
        event["event_type"]
        for event in store.list_events(target_type="agent_api_key", target_id=str(key["id"]))
    ]
    assert key_events.count("agent.key_created") == 1
    assert key_events.count("agent.key_revoked") == 1

    with pytest.raises(sqlite3.IntegrityError):  # duplicate hash
        store.create_agent_api_key(
            {
                "agent_id": "other",
                "permission_profile": "read_only_agent",
                "key_hash": "b" * 64,
                "key_prefix": "ak_live_b2",
            }
        )
    with pytest.raises(sqlite3.IntegrityError):  # invalid profile
        store.create_agent_api_key(
            {
                "agent_id": "other",
                "permission_profile": "root",
                "key_hash": "d" * 64,
                "key_prefix": "ak_live_d",
            }
        )
    conn.close()


# -- events --------------------------------------------------------------------------------


def test_append_event_and_list_events_roundtrip() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    row = store.append_event(
        {
            "event_type": "capture.completed",
            "actor_type": "agent",
            "actor_id": "hermes",
            "target_type": "source",
            "target_id": "abc",
            "payload_json": {"items": 3},
            "trace_id": "trace-1",
            "run_id": "run-1",
            "integrity_hash": "deadbeef",
        }
    )
    assert row["event_type"] == "capture.completed"
    assert row["payload_json"] == {"items": 3}
    assert row["user_id"] == store.user_id
    assert isinstance(row["occurred_at"], str) and row["occurred_at"].endswith("Z")

    by_target = store.list_events(target_type="source", target_id="abc")
    assert [event["id"] for event in by_target] == [row["id"]]
    assert store.list_events(target_type="memory", target_id="abc") == []

    agent_events = store.list_agent_events(agent_id="hermes")
    assert [event["id"] for event in agent_events] == [row["id"]]

    with pytest.raises(sqlite3.IntegrityError):  # empty event_type violates length CHECK
        store.append_event({"event_type": "", "actor_type": "system"})
    conn.close()


# -- temporal slice: graph edges, as-of reads, supersession pointers -----------


def _create_edge(store: SQLiteVNextStore, **overrides: object) -> dict[str, object]:
    edge: dict[str, object] = {
        "from_type": "source",
        "from_id": "source-1",
        "to_type": "memory",
        "to_id": "memory-1",
        "edge_type": "supports",
        "confidence": 0.7,
        "created_by": "system",
    }
    edge.update(overrides)
    return store.create_graph_edge(edge)


def test_create_graph_edge_defaults_event_time_to_now_and_notes_the_fallback() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    edge = _create_edge(store)

    assert isinstance(edge["observed_at"], str) and edge["observed_at"].endswith("Z")
    # valid_from starts the validity interval at event time, so it is no
    # longer a dead column.
    assert edge["valid_from"] == edge["observed_at"]
    assert edge["valid_to"] is None
    # No source context was available, so write time stands in and the
    # fallback is recorded on the edge.
    assert edge["metadata_json"]["observed_at_source"] == "now"
    events = store.list_events(target_type="graph_edge", target_id=str(edge["id"]))
    assert [event["event_type"] for event in events] == ["graph_edge.created"]
    conn.close()


def test_create_graph_edge_keeps_provided_event_time_and_metadata() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    edge = _create_edge(
        store,
        observed_at="2026-01-05T08:00:00Z",
        metadata_json={"observed_at_source": "source_created_at", "status": "candidate"},
    )

    assert edge["observed_at"] == "2026-01-05T08:00:00Z"
    assert edge["valid_from"] == "2026-01-05T08:00:00Z"
    assert edge["metadata_json"]["observed_at_source"] == "source_created_at"
    assert edge["metadata_json"]["status"] == "candidate"

    # An explicit valid_from wins over the observed_at default.
    explicit = _create_edge(
        store,
        observed_at="2026-01-05T08:00:00Z",
        valid_from="2026-01-06T08:00:00Z",
        edge_type="similar_to",
    )
    assert explicit["valid_from"] == "2026-01-06T08:00:00Z"
    conn.close()


def test_create_graph_edge_rejects_invalid_edge_type() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    with pytest.raises(sqlite3.IntegrityError):
        _create_edge(store, edge_type="not-an-edge-type")
    conn.close()


def test_list_edges_filters_by_endpoint_and_excludes_closed_edges() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    open_edge = _create_edge(store, from_id="source-1", to_id="memory-1")
    other_edge = _create_edge(store, from_id="source-2", to_id="memory-2", edge_type="mentions")
    _closed = _create_edge(
        store,
        from_id="source-1",
        to_id="memory-3",
        edge_type="contradicts",
        observed_at="2026-01-01T00:00:00Z",
        valid_to="2026-02-01T00:00:00Z",
    )

    assert {row["id"] for row in store.list_edges()} == {open_edge["id"], other_edge["id"]}
    assert [row["id"] for row in store.list_edges(from_id="source-1")] == [open_edge["id"]]
    assert [row["id"] for row in store.list_edges(to_id="memory-2")] == [other_edge["id"]]
    conn.close()


def test_list_edges_as_of_returns_the_graph_as_it_was_at_that_instant() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    early = _create_edge(store, observed_at="2026-01-01T00:00:00Z")
    closed = _create_edge(
        store,
        edge_type="contradicts",
        observed_at="2026-01-01T00:00:00Z",
        valid_to="2026-02-01T00:00:00Z",
    )
    late = _create_edge(store, edge_type="similar_to", observed_at="2026-03-01T00:00:00Z")

    # Mid-January: both January edges were in effect; March's did not exist yet.
    assert {row["id"] for row in store.list_edges_as_of("2026-01-15T00:00:00Z")} == {
        early["id"],
        closed["id"],
    }
    # The interval is half-open: an edge closed exactly at 'at' is out.
    assert {row["id"] for row in store.list_edges_as_of("2026-02-01T00:00:00Z")} == {early["id"]}
    # After March both open edges are in effect, and limit caps the result.
    assert {row["id"] for row in store.list_edges_as_of("2026-03-02T00:00:00Z")} == {
        early["id"],
        late["id"],
    }
    assert len(store.list_edges_as_of("2026-03-02T00:00:00Z", limit=1)) == 1
    # Before any edge existed the graph was empty.
    assert store.list_edges_as_of("2025-12-31T00:00:00Z") == []
    conn.close()


def test_edge_reads_are_scoped_to_the_bound_user() -> None:
    conn = _open_connection()
    alice = _make_store(conn)
    mallory = _make_store(conn)

    edge = _create_edge(alice, observed_at="2026-01-01T00:00:00Z")

    assert [row["id"] for row in alice.list_edges()] == [edge["id"]]
    assert [row["id"] for row in alice.list_edges_as_of("2026-01-02T00:00:00Z")] == [edge["id"]]
    assert mallory.list_edges() == []
    assert mallory.list_edges_as_of("2026-01-02T00:00:00Z") == []
    conn.close()


def test_memory_supersession_pointer_columns_roundtrip() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    old = _create_memory(store, canonical_text="superseded fact original")
    replacement = _create_memory(
        store,
        canonical_text="superseded fact replacement",
        supersedes=old["id"],
    )

    updated = store.update_memory(
        memory_id=str(old["id"]),
        patch={"status": "superseded", "superseded_by": replacement["id"]},
    )

    assert replacement["supersedes"] == old["id"]
    assert replacement["superseded_by"] is None
    assert updated["superseded_by"] == replacement["id"]
    assert store.get_memory(str(old["id"]))["superseded_by"] == replacement["id"]
    assert store.get_memory(str(replacement["id"]))["supersedes"] == old["id"]
    conn.close()


def test_bootstrap_upgrades_a_pre_existing_db_file_with_the_temporal_slice(tmp_path: Path) -> None:
    """Files created before the temporal slice shipped gain the supersession
    pointer columns (backfilled from the metadata_json copies, mirroring
    Postgres migration 20260704_0077) and the graph_edges substrate."""
    db_path = tmp_path / "alice.db"
    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, f"{user_id}@example.com", "Test User")
    store = SQLiteVNextStore(conn, user_id)
    # Rows whose supersession was recorded in metadata only (the pre-column
    # convention of the supersede-existing review flow).
    old = _create_memory(
        store,
        canonical_text="pre-column original",
        status="superseded",
        metadata_json={"superseded_by": "11111111-1111-4111-8111-111111111111"},
    )
    replacement = _create_memory(
        store,
        canonical_text="pre-column replacement",
        metadata_json={"supersedes": str(old["id"])},
    )
    conn.commit()

    # Rewind the file to the pre-temporal-slice schema.
    conn.execute("DROP INDEX IF EXISTS memories_user_superseded_by_idx")
    conn.execute("DROP INDEX IF EXISTS graph_edges_user_edge_idx")
    conn.execute("DROP TABLE graph_edges")
    conn.execute("ALTER TABLE memories DROP COLUMN superseded_by")
    conn.execute("ALTER TABLE memories DROP COLUMN supersedes")
    conn.commit()
    assert "superseded_by" not in {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    conn.close()

    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)

    memory_columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    assert {"superseded_by", "supersedes"} <= memory_columns
    table_names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert "graph_edges" in table_names
    index_names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    }
    assert {"memories_user_superseded_by_idx", "graph_edges_user_edge_idx"} <= index_names

    # The metadata-only pointers were backfilled into the real columns.
    upgraded = SQLiteVNextStore(conn, user_id)
    assert (
        upgraded.get_memory(str(old["id"]))["superseded_by"]
        == "11111111-1111-4111-8111-111111111111"
    )
    assert upgraded.get_memory(str(replacement["id"]))["supersedes"] == old["id"]

    # A second bootstrap does not re-run the backfill or fail.
    bootstrap_sqlite_schema(conn)
    assert upgraded.get_memory(str(replacement["id"]))["supersedes"] == old["id"]

    # The upgraded file has the full graph substrate.
    edge = upgraded.create_graph_edge(
        {
            "from_type": "memory",
            "from_id": str(replacement["id"]),
            "to_type": "memory",
            "to_id": str(old["id"]),
            "edge_type": "supersedes",
            "created_by": "system",
        }
    )
    assert [row["id"] for row in upgraded.list_edges()] == [edge["id"]]
    conn.close()


# -- entity substrate: resolution, mentions, relationship history ---------------


def _create_entity(store: SQLiteVNextStore, **overrides: object) -> dict[str, object]:
    entity: dict[str, object] = {
        "entity_type": "organization",
        "name": "OpenAI",
    }
    entity.update(overrides)
    return store.create_entity(entity)


def test_create_entity_get_roundtrip_computes_normalized_name_and_defaults() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    created = _create_entity(store, name="OpenAI, Inc.")
    assert created["name"] == "OpenAI, Inc."
    assert created["normalized_name"] == "openai inc"
    assert created["entity_type"] == "organization"
    assert created["aliases"] == []
    assert created["metadata_json"] == {}
    assert created["mention_count"] == 0
    assert created["first_observed_at"] is None
    assert created["last_observed_at"] is None
    assert created["deleted_at"] is None
    assert isinstance(created["created_at"], str) and created["created_at"].endswith("Z")

    fetched = store.get_entity(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["normalized_name"] == "openai inc"
    assert store.get_entity(str(uuid4())) is None

    by_name = store.get_entity_by_normalized_name("organization", "openai inc")
    assert by_name is not None
    assert by_name["id"] == created["id"]
    assert store.get_entity_by_normalized_name("person", "openai inc") is None
    assert store.get_entity_by_normalized_name("organization", "OpenAI, Inc.") is None

    # A caller-provided normalized_name wins over the computed one.
    explicit = _create_entity(store, name="Whatever Display Name", normalized_name="custom key")
    assert explicit["normalized_name"] == "custom key"
    assert store.get_entity_by_normalized_name("organization", "custom key")["id"] == explicit["id"]

    # Creates emit a mutation event with the audited field list.
    events = store.list_events(target_type="entity", target_id=str(created["id"]))
    assert [event["event_type"] for event in events] == ["entity.created"]
    assert events[0]["payload_json"]["operation"] == "create"
    assert events[0]["payload_json"]["entity_type"] == "organization"
    assert "name" in events[0]["payload_json"]["fields"]
    conn.close()


def test_create_entity_enforces_normalized_name_uniqueness_per_user_and_type() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    _create_entity(store, name="OpenAI")

    # Different surface spellings of the same normalized name collide.
    with pytest.raises(sqlite3.IntegrityError):
        _create_entity(store, name='"OpenAI,"')

    # The same normalized name under another entity_type is a new entity.
    topic = _create_entity(store, name="OpenAI", entity_type="topic")
    assert topic["normalized_name"] == "openai"

    # Another user's namespace is independent.
    other = _make_store(conn)
    assert _create_entity(other, name="openai")["normalized_name"] == "openai"

    with pytest.raises(sqlite3.IntegrityError):
        _create_entity(store, name="Acme", entity_type="not_a_type")
    # A pure-punctuation name normalizes to "" and fails the length CHECK.
    with pytest.raises(sqlite3.IntegrityError):
        _create_entity(store, name="...")
    conn.close()


def test_find_entities_by_names_matches_normalized_names_and_aliases_in_one_call() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    openai = _create_entity(store, name="OpenAI", aliases=["open ai"])
    type3 = _create_entity(store, name="Type3 Capital")
    _create_entity(store, name="Anthropic")

    # Mentions push type3 ahead in the mention_count DESC ordering.
    store.record_entity_mention(entity_id=type3["id"], observed_at="2026-07-01T00:00:00Z")

    rows = store.find_entities_by_names(("type3 capital", "open ai"))
    assert [row["id"] for row in rows] == [type3["id"], openai["id"]]

    # Alias matching is exact string equality, not substring.
    assert store.find_entities_by_names(("open",)) == []
    assert store.find_entities_by_names(()) == []
    conn.close()


def test_update_entity_replaces_aliases_and_rejects_immutable_fields() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    created = _create_entity(store, name="OpenAI", aliases=["oai"])

    updated = store.update_entity(
        entity_id=created["id"],
        patch={"name": "OpenAI (research lab)", "aliases": ["oai", "open ai"]},
    )
    assert updated["name"] == "OpenAI (research lab)"
    assert updated["aliases"] == ["oai", "open ai"]
    assert updated["normalized_name"] == created["normalized_name"]  # resolution key untouched
    assert updated["updated_at"] >= created["updated_at"]
    assert [row["id"] for row in store.find_entities_by_names(("open ai",))] == [created["id"]]

    update_events = [
        event
        for event in store.list_events(target_type="entity", target_id=str(created["id"]))
        if event["event_type"] == "entity.updated"
    ]
    assert len(update_events) == 1
    assert update_events[0]["payload_json"]["changes"]["aliases"] == ["oai", "open ai"]

    for immutable_patch in (
        {"normalized_name": "hijacked"},
        {"entity_type": "person"},
        {"id": str(uuid4())},
        {"user_id": str(uuid4())},
    ):
        with pytest.raises(ContinuityStoreInvariantError, match="immutable"):
            store.update_entity(entity_id=created["id"], patch=immutable_patch)
    with pytest.raises(ContinuityStoreInvariantError):
        store.update_entity(entity_id=str(uuid4()), patch={"name": "missing"})
    conn.close()


def test_record_entity_mention_counts_and_widens_the_observation_window() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    entity = _create_entity(store)

    first = store.record_entity_mention(entity_id=entity["id"], observed_at="2026-02-01T00:00:00Z")
    assert first["mention_count"] == 1
    assert first["first_observed_at"] == "2026-02-01T00:00:00Z"
    assert first["last_observed_at"] == "2026-02-01T00:00:00Z"

    # An out-of-order earlier mention widens the start but not the end.
    earlier = store.record_entity_mention(entity_id=entity["id"], observed_at="2026-01-01T00:00:00Z")
    assert earlier["mention_count"] == 2
    assert earlier["first_observed_at"] == "2026-01-01T00:00:00Z"
    assert earlier["last_observed_at"] == "2026-02-01T00:00:00Z"

    later = store.record_entity_mention(
        entity_id=entity["id"], observed_at="2026-03-01T00:00:00Z", source_id=str(uuid4())
    )
    assert later["mention_count"] == 3
    assert later["first_observed_at"] == "2026-01-01T00:00:00Z"
    assert later["last_observed_at"] == "2026-03-01T00:00:00Z"

    with pytest.raises(ContinuityStoreInvariantError, match="observed_at"):
        store.record_entity_mention(entity_id=entity["id"], observed_at=None)
    with pytest.raises(ContinuityStoreInvariantError):
        store.record_entity_mention(entity_id=str(uuid4()), observed_at="2026-03-01T00:00:00Z")

    mention_events = [
        event
        for event in store.list_events(target_type="entity", target_id=str(entity["id"]))
        if event["event_type"] == "entity.mention_recorded"
    ]
    assert len(mention_events) == 3
    assert mention_events[0]["payload_json"]["operation"] == "record_mention"
    conn.close()


def test_record_relationship_change_appends_history_and_tracks_current_type() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    entity = _create_entity(store, name="Jane Advisor", entity_type="person", metadata_json={"note": "keep"})

    first = store.record_relationship_change(
        entity_id=entity["id"], relationship_type="advisor", changed_at="2026-01-01T00:00:00Z"
    )
    assert first["relationship_type_before"] is None
    assert first["relationship_type_after"] == "advisor"
    assert first["changed_at"] == "2026-01-01T00:00:00Z"
    assert first["metadata_json"] == {}

    second = store.record_relationship_change(
        entity_id=entity["id"],
        relationship_type="investor",
        changed_at="2026-02-01T00:00:00Z",
        metadata_json={"round": "seed"},
    )
    assert second["relationship_type_before"] == "advisor"
    assert second["relationship_type_after"] == "investor"
    assert second["metadata_json"] == {"round": "seed"}

    # The entity carries the current pointer; caller metadata survives the merge.
    current = store.get_entity(entity["id"])
    assert current["metadata_json"] == {"note": "keep", "relationship_type": "investor"}

    # History lists most recent change first.
    listed = store.list_relationship_events(entity["id"])
    assert [row["id"] for row in listed] == [second["id"], first["id"]]

    with pytest.raises(ContinuityStoreInvariantError, match="existing entity"):
        store.record_relationship_change(entity_id=str(uuid4()), relationship_type="advisor")

    change_events = [
        event
        for event in store.list_events(target_type="entity", target_id=str(entity["id"]))
        if event["event_type"] == "entity.relationship_changed"
    ]
    assert len(change_events) == 2
    payloads = {event["payload_json"]["relationship_event_id"]: event["payload_json"] for event in change_events}
    assert payloads[str(second["id"])]["relationship_type_before"] == "advisor"
    assert payloads[str(second["id"])]["relationship_type_after"] == "investor"
    conn.close()


def test_entity_relationship_events_reject_update_and_delete() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    entity = _create_entity(store)
    store.record_relationship_change(entity_id=entity["id"], relationship_type="advisor")
    assert conn.execute("SELECT count(*) FROM entity_relationship_events").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE entity_relationship_events SET relationship_type_after = 'tampered'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM entity_relationship_events")
    conn.close()


def test_list_entities_filters_by_type_and_orders_by_recency() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    org = _create_entity(store, name="Type3 Capital")
    person = _create_entity(store, name="Sam Rusani", entity_type="person")
    store.update_entity(entity_id=org["id"], patch={"name": "Type3.Capital"})

    everything = store.list_entities()
    assert [row["id"] for row in everything] == [org["id"], person["id"]]  # most recently updated first
    assert [row["id"] for row in store.list_entities(entity_type="person")] == [person["id"]]
    assert store.list_entities(entity_type="market") == []
    assert len(store.list_entities(limit=1)) == 1
    conn.close()


def test_entity_reads_and_writes_are_scoped_to_the_bound_user() -> None:
    conn = _open_connection()
    alice = _make_store(conn)
    mallory = _make_store(conn)

    entity = _create_entity(alice, name="OpenAI", aliases=["open ai"])
    event = alice.record_relationship_change(entity_id=entity["id"], relationship_type="vendor")

    # Every new read method comes back empty for the other user.
    assert mallory.get_entity(entity["id"]) is None
    assert mallory.get_entity_by_normalized_name("organization", "openai") is None
    assert mallory.find_entities_by_names(("openai",)) == []
    assert mallory.find_entities_by_names(("open ai",)) == []
    assert mallory.list_entities() == []
    assert mallory.list_relationship_events(entity["id"]) == []

    # Mutations against another user's entity fail loudly.
    with pytest.raises(ContinuityStoreInvariantError):
        mallory.update_entity(entity_id=entity["id"], patch={"name": "stolen"})
    with pytest.raises(ContinuityStoreInvariantError):
        mallory.record_entity_mention(entity_id=entity["id"], observed_at="2026-07-01T00:00:00Z")
    with pytest.raises(ContinuityStoreInvariantError):
        mallory.record_relationship_change(entity_id=entity["id"], relationship_type="stolen")

    # Nothing Mallory attempted altered Alice's view.
    assert alice.get_entity(entity["id"])["name"] == "OpenAI"
    assert alice.get_entity(entity["id"])["mention_count"] == 0
    assert [row["id"] for row in alice.list_relationship_events(entity["id"])] == [event["id"]]
    conn.close()


def test_bootstrap_upgrades_a_pre_existing_db_file_with_the_entity_substrate(tmp_path: Path) -> None:
    """Files created before the entity substrate shipped gain the entities and
    entity_relationship_events tables (with their indexes and append-only
    triggers) from the idempotent bootstrap."""
    db_path = tmp_path / "alice.db"
    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    # Rewind the file to the pre-entity-substrate schema (dropping a table
    # drops its indexes and triggers with it).
    conn.execute("DROP TABLE entity_relationship_events")
    conn.execute("DROP TABLE vnext_entities")
    conn.commit()
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert "vnext_entities" not in tables
    conn.close()

    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert {"vnext_entities", "entity_relationship_events"} <= tables
    index_names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    }
    assert "vnext_entities_user_normalized_name_idx" in index_names
    assert "entity_relationship_events_entity_changed_idx" in index_names
    trigger_names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall()
    }
    assert "entity_relationship_events_append_only_update" in trigger_names
    assert "entity_relationship_events_append_only_delete" in trigger_names

    # The upgraded file is fully usable, append-only enforcement included.
    store = _make_store(conn)
    entity = _create_entity(store, name="Type3 Capital")
    store.record_relationship_change(entity_id=entity["id"], relationship_type="portfolio")
    assert [row["relationship_type_after"] for row in store.list_relationship_events(entity["id"])] == [
        "portfolio"
    ]
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM entity_relationship_events")
    conn.close()


# -- true redaction ------------------------------------------------------------


def _secret_memory(store: SQLiteVNextStore) -> dict[str, object]:
    return _create_memory(
        store,
        title="SECRET-TITLE quantum sprocket",
        canonical_text="SECRET-BODY the quantum sprocket calibration ritual",
        summary="SECRET-SUMMARY sprocket notes",
        value={"text": "SECRET-VALUE sprocket"},
        trust_reason="user said SECRET-TRUST",
        metadata_json={
            "note": "SECRET-META",
            "project_id": "proj-123",
            "consolidation_digest": "digest-abc",
        },
    )


def _secret_revision(store: SQLiteVNextStore, memory: dict[str, object]) -> dict[str, object]:
    return store.append_revision(
        {
            "memory_id": memory["id"],
            "memory_key": memory["memory_key"],
            "previous_value": {"text": "SECRET-OLD"},
            "new_value": {"text": "SECRET-NEW"},
            "candidate": {"text": "SECRET-CAND"},
            "text_before": "SECRET-BEFORE",
            "text_after": "SECRET-AFTER",
            "reason": "correcting SECRET-REASON",
            "revision_type": "edited",
            "metadata_json": {"note": "SECRET-REV-META"},
        }
    )


def _table_dump(conn: sqlite3.Connection, table: str) -> str:
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    return repr(rows)


def test_redact_memory_content_expunges_content_and_archives() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _secret_memory(store)
    store.update_memory_embedding(memory_id=str(memory["id"]), vector=[0.5, 0.25])

    row = store.redact_memory_content(memory_id=str(memory["id"]))

    assert row["title"] == "[REDACTED]"
    assert row["canonical_text"] == "[REDACTED]"
    assert row["summary"] == "[REDACTED]"
    assert row["trust_reason"] == "[REDACTED]"
    assert row["value"] == {"redacted": True}
    assert row["status"] == "archived"
    assert row["deleted_at"] is not None
    metadata = row["metadata_json"]
    assert metadata["redacted"] is True
    assert metadata["redacted_at"]
    # Structural keys survive; content-bearing keys are gone.
    assert metadata["project_id"] == "proj-123"
    assert metadata["consolidation_digest"] == "digest-abc"
    assert "note" not in metadata
    # Skeleton is intact and the embedding is really gone.
    direct = conn.execute(
        "SELECT id, memory_key, created_at, embedding FROM memories WHERE id = ?",
        (str(memory["id"]),),
    ).fetchone()
    assert direct[0] == memory["id"]
    assert direct[1] == memory["memory_key"]
    assert direct[2] == memory["created_at"]
    assert direct[3] is None
    assert "SECRET" not in _table_dump(conn, "memories")
    # Exactly one memory.redacted event was appended, itself content-free.
    redaction_events = [
        event for event in store.list_events(target_type="memory", target_id=str(memory["id"]))
        if event["event_type"] == "memory.redacted"
    ]
    assert len(redaction_events) == 1
    assert redaction_events[0]["payload_json"] == {"operation": "redact_memory_content"}
    conn.close()


def test_redact_memory_content_works_on_soft_deleted_memories() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _secret_memory(store)
    store.update_memory(memory_id=str(memory["id"]), patch={"status": "archived"})

    row = store.redact_memory_content(memory_id=str(memory["id"]))

    assert row["status"] == "archived"
    assert row["canonical_text"] == "[REDACTED]"
    assert "SECRET" not in _table_dump(conn, "memories")
    conn.close()


def test_redact_memory_content_missing_memory_raises() -> None:
    conn = _open_connection()
    store = _make_store(conn)

    with pytest.raises(ContinuityStoreInvariantError, match="did not find the memory"):
        store.redact_memory_content(memory_id=str(uuid4()))
    conn.close()


def test_redact_memory_revisions_scrubs_content_and_preserves_skeleton() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _secret_memory(store)
    created = store.append_revision(
        {
            "memory_id": memory["id"],
            "memory_key": memory["memory_key"],
            "new_value": {"text": "SECRET-FIRST"},
            "candidate": {"text": "SECRET-FIRST"},
            "text_after": "SECRET-FIRST",
            "revision_type": "created",
            "action": "ADD",
        }
    )
    edited = _secret_revision(store, memory)
    before = store.list_revisions(str(memory["id"]))
    assert len(before) == 2

    result = store.redact_memory_revisions(memory_id=str(memory["id"]))

    assert result == {"memory_id": str(memory["id"]), "redacted_revisions": 2}
    after = store.list_revisions(str(memory["id"]))
    assert len(after) == 2
    # Audit skeleton intact: ids, ordering numbers, types, actors, timestamps.
    for before_row, after_row in zip(before, after):
        for column in (
            "id",
            "memory_id",
            "sequence_no",
            "action",
            "memory_key",
            "source_event_ids",
            "revision_number",
            "revision_type",
            "actor_type",
            "actor_id",
            "created_at",
        ):
            assert after_row[column] == before_row[column]
    by_id = {row["id"]: row for row in after}
    created_after = by_id[created["id"]]
    edited_after = by_id[edited["id"]]
    # NULL content stays NULL so the created-vs-edited shape survives.
    assert created_after["previous_value"] is None
    assert created_after["text_before"] is None
    assert created_after["reason"] is None
    assert created_after["text_after"] == "[REDACTED]"
    assert created_after["new_value"] == {"redacted": True}
    assert created_after["candidate"] == {"redacted": True}
    assert edited_after["previous_value"] == {"redacted": True}
    assert edited_after["new_value"] == {"redacted": True}
    assert edited_after["candidate"] == {"redacted": True}
    assert edited_after["text_before"] == "[REDACTED]"
    assert edited_after["text_after"] == "[REDACTED]"
    assert edited_after["reason"] == "[REDACTED]"
    assert edited_after["metadata_json"] == {"redacted": True}
    assert "SECRET" not in _table_dump(conn, "memory_revisions")
    redaction_events = [
        event for event in store.list_events(target_type="memory", target_id=str(memory["id"]))
        if event["event_type"] == "memory.redacted"
    ]
    assert len(redaction_events) == 1
    assert redaction_events[0]["payload_json"] == {
        "operation": "redact_memory_revisions",
        "redacted_revisions": 2,
    }
    conn.close()


def test_redact_memory_events_scrubs_payloads_and_preserves_skeleton() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _secret_memory(store)
    # memory.updated carries the content patch in its payload.
    store.update_memory(memory_id=str(memory["id"]), patch={"summary": "SECRET-PATCH"})
    # An event referencing the memory only inside its payload.
    store.append_event(
        {
            "event_type": "custom.note",
            "actor_type": "system",
            "payload_json": {"memory_id": str(memory["id"]), "text": "SECRET-EVT"},
            "integrity_hash": "hash-abc",
        }
    )
    unrelated = store.append_event(
        {
            "event_type": "custom.other",
            "actor_type": "system",
            "payload_json": {"text": "UNRELATED-SECRET"},
        }
    )
    before = {
        row["id"]: row
        for row in store.list_events()
        if str(memory["id"]) in json.dumps(row["payload_json"])
        or (row["target_type"] == "memory" and row["target_id"] == str(memory["id"]))
    }
    assert len(before) >= 3

    result = store.redact_memory_events(memory_id=str(memory["id"]))

    assert result["redacted_events"] == len(before)
    after = {row["id"]: row for row in store.list_events()}
    for event_id, before_row in before.items():
        after_row = after[event_id]
        # Skeleton intact.
        for column in ("event_type", "actor_type", "actor_id", "target_type", "target_id", "occurred_at", "trace_id", "run_id"):
            assert after_row[column] == before_row[column]
        # Content gone: exactly the redaction shape, hash cleared.
        assert after_row["payload_json"] == {
            "redacted": True,
            "memory_id": str(memory["id"]),
            "event_type": before_row["event_type"],
        }
        assert after_row["integrity_hash"] is None
    # Unrelated events are untouched.
    assert after[unrelated["id"]]["payload_json"] == {"text": "UNRELATED-SECRET"}
    dump = _table_dump(conn, "event_log")
    assert "SECRET-PATCH" not in dump
    assert "SECRET-EVT" not in dump
    assert "hash-abc" not in dump
    redaction_events = [
        row for row in after.values() if row["event_type"] == "memory.redacted"
    ]
    assert len(redaction_events) == 1
    assert redaction_events[0]["payload_json"] == {
        "operation": "redact_memory_events",
        "redacted_events": len(before),
    }
    conn.close()


def test_append_only_still_enforced_for_normal_updates_after_redaction_support() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _secret_memory(store)
    revision = _secret_revision(store, memory)
    event = store.append_event(
        {"event_type": "custom.note", "actor_type": "system", "payload_json": {"text": "x"}}
    )

    # Without redaction mode: every UPDATE and DELETE is rejected.
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE event_log SET payload_json = '{}' WHERE id = ?", (event["id"],))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM event_log WHERE id = ?", (event["id"],))
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute(
            "UPDATE memory_revisions SET text_after = 'tampered' WHERE id = ?",
            (revision["id"],),
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM memory_revisions WHERE id = ?", (revision["id"],))

    # Even WITH redaction mode on: skeleton mutations and non-marker
    # content are still rejected, and DELETE stays impossible.
    conn.execute("UPDATE redaction_mode SET enabled = 1 WHERE id = 1")
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute(
                "UPDATE event_log SET event_type = 'evil' WHERE id = ?", (event["id"],)
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute(
                "UPDATE event_log SET payload_json = '{\"free\": \"rewrite\"}' WHERE id = ?",
                (event["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute(
                "UPDATE memory_revisions SET text_after = 'rewritten history' WHERE id = ?",
                (revision["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            conn.execute("DELETE FROM event_log WHERE id = ?", (event["id"],))
    finally:
        conn.execute("UPDATE redaction_mode SET enabled = 0 WHERE id = 1")
    conn.close()


def test_redaction_mode_resets_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _secret_memory(store)
    _secret_revision(store, memory)
    original_execute = store._execute

    def failing_execute(query: str, params: tuple[object, ...] = ()):
        if "UPDATE memory_revisions" in query:
            raise RuntimeError("boom mid-redaction")
        return original_execute(query, params)

    monkeypatch.setattr(store, "_execute", failing_execute)
    with pytest.raises(RuntimeError, match="boom mid-redaction"):
        store.redact_memory_revisions(memory_id=str(memory["id"]))

    enabled = conn.execute("SELECT enabled FROM redaction_mode WHERE id = 1").fetchone()[0]
    assert enabled == 0
    # And append-only is still enforced afterwards.
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE memory_revisions SET text_after = 'tampered'")
    conn.close()


def test_redaction_is_user_scoped() -> None:
    conn = _open_connection()
    store_a = _make_store(conn)
    store_b = _make_store(conn)
    memory = _secret_memory(store_a)
    _secret_revision(store_a, memory)

    with pytest.raises(ContinuityStoreInvariantError, match="did not find the memory"):
        store_b.redact_memory_content(memory_id=str(memory["id"]))
    # B sees none of A's events referencing the memory. (Run before the
    # revisions call: that call appends B's own memory.redacted audit
    # event, which a later redact_memory_events would legitimately match.)
    assert store_b.redact_memory_events(memory_id=str(memory["id"]))["redacted_events"] == 0
    assert store_b.redact_memory_revisions(memory_id=str(memory["id"]))["redacted_revisions"] == 0

    # User A's content is untouched.
    assert "SECRET-TITLE" in _table_dump(conn, "memories")
    assert "SECRET-BEFORE" in _table_dump(conn, "memory_revisions")
    assert [
        row for row in store_a.list_events() if row["event_type"] == "memory.redacted"
    ] == []
    conn.close()


def test_redacted_memory_is_invisible_to_search() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _secret_memory(store)
    store.update_memory_embedding(memory_id=str(memory["id"]), vector=[0.5, 0.25])
    assert store.search_memories(query="sprocket") != []
    assert store.search_memories_fts(query="sprocket") != []
    assert store.search_memories_vector(query_vector=[0.5, 0.25]) != []

    store.redact_memory_content(memory_id=str(memory["id"]))

    assert store.search_memories(query="sprocket") == []
    assert store.search_memories_fts(query="sprocket") == []
    assert store.search_memories_vector(query_vector=[0.5, 0.25]) == []
    # The FTS shadow index itself no longer matches the redacted content.
    assert conn.execute(
        "SELECT count(*) FROM memories_fts WHERE memories_fts MATCH 'sprocket'"
    ).fetchone()[0] == 0
    conn.close()


def test_bootstrap_upgrades_legacy_strict_append_only_triggers() -> None:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    # Simulate a database file created before the redaction-aware triggers.
    for table in ("event_log", "memory_revisions"):
        conn.execute(f"DROP TRIGGER {table}_append_only_update")
        conn.execute(
            f"""
            CREATE TRIGGER {table}_append_only_update
            BEFORE UPDATE ON {table}
            BEGIN
              SELECT RAISE(ABORT, '{table} is append-only');
            END
            """
        )

    bootstrap_sqlite_schema(conn)

    for table in ("event_log", "memory_revisions"):
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (f"{table}_append_only_update",),
        ).fetchone()[0]
        assert "redaction_mode" in sql
        assert "[REDACTED]" in sql or table == "event_log"
        delete_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (f"{table}_append_only_delete",),
        ).fetchone()[0]
        assert "redaction_mode" not in delete_sql
    # The flag row exists and is off.
    assert conn.execute("SELECT enabled FROM redaction_mode WHERE id = 1").fetchone()[0] == 0
    conn.close()
