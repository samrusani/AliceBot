from __future__ import annotations

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
