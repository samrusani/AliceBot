from __future__ import annotations

import json
import sqlite3

import pytest

from alicebot_api import sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user


def _table_statement(name: str) -> str:
    marker = f"CREATE TABLE IF NOT EXISTS {name} ("
    return next(statement for statement in sqlite_schema._TABLE_STATEMENTS if marker in statement)


def _v0_7_memories_statement() -> str:
    """The v0.7 memory shape at the columns/constraint that later changed."""
    statement = _table_statement("memories")
    for line in (
        "      project_id TEXT NULL,\n",
        "      created_by_agent_id TEXT NULL,\n",
        "      run_id TEXT NULL,\n",
        "      superseded_by TEXT NULL,\n",
        "      supersedes TEXT NULL,\n",
        "      fact_keys TEXT NULL,\n",
    ):
        statement = statement.replace(line, "")
    return statement.replace(", 'stale'", "")


def test_v0_7_data_bearing_file_upgrades_status_check_and_preserves_children() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(_table_statement("users"))
    conn.execute(_table_statement("sources"))
    conn.execute(_v0_7_memories_statement())
    conn.execute(_table_statement("memory_revisions"))
    conn.execute(_table_statement("open_loops"))

    user_id = "00000000-0000-0000-0000-000000000201"
    memory_id = "00000000-0000-0000-0000-000000000202"
    revision_id = "00000000-0000-0000-0000-000000000203"
    loop_id = "00000000-0000-0000-0000-000000000204"
    conn.execute(
        "INSERT INTO users (id, email, display_name) VALUES (?, ?, ?)",
        (user_id, "sqlite-upgrade@example.com", "SQLite Upgrade"),
    )
    conn.execute(
        """
        INSERT INTO memories (
          id, user_id, memory_key, value, status, source_event_ids,
          memory_type, canonical_text
        )
        VALUES (?, ?, 'upgrade.seed', '{"text":"before"}', 'active',
                '[]', 'semantic', 'Preserve this seeded memory')
        """,
        (memory_id, user_id),
    )
    conn.execute(
        """
        INSERT INTO memory_revisions (
          id, user_id, memory_id, sequence_no, action, memory_key,
          source_event_ids, candidate, revision_number, revision_type,
          text_after, metadata_json
        )
        VALUES (?, ?, ?, 1, 'ADD', 'upgrade.seed', '[]', '{}', 1,
                'created', 'Preserve this seeded memory', '{}')
        """,
        (revision_id, user_id, memory_id),
    )
    conn.execute(
        """
        INSERT INTO open_loops (id, user_id, memory_id, title, status)
        VALUES (?, ?, ?, 'Verify public release', 'open')
        """,
        (loop_id, user_id, memory_id),
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="memories_status_check"):
        conn.execute("UPDATE memories SET status = 'stale' WHERE id = ?", (memory_id,))
    conn.rollback()

    sqlite_schema.bootstrap_sqlite_schema(conn)
    conn.execute("UPDATE memories SET status = 'stale' WHERE id = ?", (memory_id,))
    conn.commit()

    assert conn.execute(
        "SELECT status, canonical_text FROM memories WHERE id = ?", (memory_id,)
    ).fetchone() == ("stale", "Preserve this seeded memory")
    assert conn.execute(
        "SELECT memory_id, text_after FROM memory_revisions WHERE id = ?", (revision_id,)
    ).fetchone() == (memory_id, "Preserve this seeded memory")
    assert conn.execute(
        "SELECT memory_id, title FROM open_loops WHERE id = ?", (loop_id,)
    ).fetchone() == (memory_id, "Verify public release")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert {
        "project_id",
        "created_by_agent_id",
        "run_id",
        "superseded_by",
        "supersedes",
        "fact_keys",
    }.issubset({row[1] for row in conn.execute("PRAGMA table_info(memories)")})

    # Opening the upgraded file again is idempotent and leaves the row intact.
    traced: list[str] = []
    conn.set_trace_callback(traced.append)
    sqlite_schema.bootstrap_sqlite_schema(conn)
    conn.set_trace_callback(None)
    assert conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 1
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert not [statement for statement in traced if "ROW_NUMBER() OVER" in statement]


def test_bootstrap_canonicalizes_legacy_duplicate_retry_identifiers() -> None:
    conn = sqlite3.connect(":memory:")
    sqlite_schema.bootstrap_sqlite_schema(conn)
    conn.execute("DROP INDEX memories_user_commit_digest_unique_idx")
    conn.execute("DROP INDEX memories_user_confirmation_id_unique_idx")
    user_id = "00000000-0000-0000-0000-000000000211"
    first_id = "00000000-0000-0000-0000-000000000212"
    second_id = "00000000-0000-0000-0000-000000000213"
    conn.execute(
        "INSERT INTO users (id, email) VALUES (?, ?)",
        (user_id, "duplicate-retry@example.com"),
    )
    for memory_id, key, created_at in (
        (first_id, "retry.first", "2026-01-01T00:00:00Z"),
        (second_id, "retry.second", "2026-01-02T00:00:00Z"),
    ):
        conn.execute(
            """
            INSERT INTO memories (
              id, user_id, memory_key, value, status, source_event_ids,
              memory_type, canonical_text, commit_digest, confirmation_id,
              metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, '{"text":"same retry"}', 'active', '[]',
                    'semantic', 'Same retry', 'duplicate-digest',
                    'duplicate-confirmation',
                    '{"agentic_memory":{"idempotency_key":"duplicate-digest","confirmation":{"confirmation_id":"duplicate-confirmation"}}}',
                    ?, ?)
            """,
            (memory_id, user_id, key, created_at, created_at),
        )
    conn.commit()

    sqlite_schema.bootstrap_sqlite_schema(conn)

    rows = conn.execute(
        """
        SELECT id, commit_digest, confirmation_id, metadata_json
        FROM memories
        ORDER BY created_at, id
        """
    ).fetchall()
    assert rows[0][0:3] == (first_id, "duplicate-digest", "duplicate-confirmation")
    assert rows[1][0:3] == (second_id, None, None)
    assert first_id in rows[1][3]
    with pytest.raises(sqlite3.IntegrityError, match="memories.user_id, memories.commit_digest"):
        conn.execute(
            """
            INSERT INTO memories (
              id, user_id, memory_key, value, status, source_event_ids,
              memory_type, canonical_text, commit_digest
            )
            VALUES ('00000000-0000-0000-0000-000000000214', ?,
                    'retry.third', '{}', 'active', '[]', 'semantic',
                    'Third retry', 'duplicate-digest')
            """,
            (user_id,),
        )


def test_bootstrap_promotes_and_reads_legacy_nested_multi_project_scope() -> None:
    conn = sqlite3.connect(":memory:")
    sqlite_schema.bootstrap_sqlite_schema(conn)
    user_id = "00000000-0000-0000-0000-000000000231"
    memory_id = "00000000-0000-0000-0000-000000000232"
    ensure_sqlite_user(conn, user_id, "legacy-scope@example.com")
    conn.execute(
        """
        INSERT INTO memories (
          id, user_id, memory_key, value, status, source_event_ids,
          memory_type, canonical_text, domain, sensitivity, metadata_json
        )
        VALUES (?, ?, 'legacy.nested.scope', '{}', 'active', '[]',
                'semantic', 'Legacy nested scope memory', 'project', 'internal',
                '{"agentic_memory":{"project_scope":[" alicebot ","hermes","alicebot"]}}')
        """,
        (memory_id, user_id),
    )
    conn.commit()

    legacy_store = SQLiteVNextStore(conn, user_id)
    legacy_row = legacy_store.get_memory(memory_id)
    assert legacy_row is not None
    assert legacy_row["project_scope"] == ["alicebot", "hermes"]
    assert [
        row["id"]
        for row in legacy_store.search_memories(
            query="legacy nested scope",
            projects=("hermes",),
        )
    ] == [memory_id]

    sqlite_schema.bootstrap_sqlite_schema(conn)

    raw_project_id, raw_metadata = conn.execute(
        "SELECT project_id, metadata_json FROM memories WHERE id = ?", (memory_id,)
    ).fetchone()
    assert raw_project_id is None
    assert json.loads(raw_metadata)["project_scope"] == ["alicebot", "hermes"]

    store = SQLiteVNextStore(conn, user_id)
    upgraded = store.get_memory(memory_id)
    assert upgraded is not None
    assert upgraded["project_scope"] == ["alicebot", "hermes"]
    assert [row["id"] for row in store.search_memories(query="legacy nested scope", projects=("hermes",))] == [
        memory_id
    ]
    assert (
        store.search_memories(
            query="legacy nested scope",
            projects=("unrelated",),
        )
        == []
    )


def test_content_update_transactionally_expires_only_derived_entity_edges() -> None:
    conn = sqlite3.connect(":memory:")
    sqlite_schema.bootstrap_sqlite_schema(conn)
    user_id = "00000000-0000-0000-0000-000000000221"
    ensure_sqlite_user(conn, user_id, "derived-edge@example.com")
    store = SQLiteVNextStore(conn, user_id)
    memory = store.create_memory(
        {
            "memory_key": "edge.seed",
            "value": {"text": "Sami Rusani said hello."},
            "status": "active",
            "memory_type": "semantic",
            "canonical_text": "Sami Rusani said hello.",
        }
    )
    mention = store.create_graph_edge(
        {
            "from_type": "memory",
            "from_id": str(memory["id"]),
            "to_type": "entity",
            "to_id": "00000000-0000-0000-0000-000000000222",
            "edge_type": "mentions",
        }
    )
    manual = store.create_graph_edge(
        {
            "from_type": "memory",
            "from_id": str(memory["id"]),
            "to_type": "memory",
            "to_id": "00000000-0000-0000-0000-000000000223",
            "edge_type": "supports",
        }
    )

    store.update_memory(
        memory_id=str(memory["id"]),
        patch={"canonical_text": "Zara Quill said hello."},
    )

    assert [str(edge["id"]) for edge in store.list_edges(from_id=str(memory["id"]))] == [
        str(manual["id"])
    ]
    assert conn.execute(
        "SELECT valid_to IS NOT NULL FROM graph_edges WHERE id = ?", (str(mention["id"]),)
    ).fetchone() == (1,)
