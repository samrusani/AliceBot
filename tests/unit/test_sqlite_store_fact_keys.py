"""SQLite side of the derived-retrieval-keys (fact_keys) substrate.

Covers the sqlite_schema FTS definition (fact_keys column + trigger sync +
legacy-file upgrade/rebuild), the SQLiteVNextStore indexing surface
(``update_memory_fact_keys`` / ``list_memories_missing_fact_keys``), the
strict-FTS retrieval proof (no vectors involved), the memory-commit
integration hook, and the backfill entry points. The Postgres mirror
lives in ``tests/integration/test_memory_fact_keys_postgres.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_fact_keys import (
    apply_fact_keys,
    attach_memory_fact_keys,
    backfill_memory_fact_keys,
    fact_keys_text,
)
from alicebot_api.vnext_memory_commit import MemoryCommitRequest, VNextMemoryCommitService


REPO_ROOT = Path(__file__).resolve().parents[2]

# The retrieval gap this substrate closes: the memory's own text shares
# ZERO tokens with the category-phrased question.
CATEGORY_QUERY = "charity event fundraising total"
INSTANCE_TEXT = "The Bike-a-Thon raised $5,000 for the hospital."


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch) -> None:
    for name in (
        "ALICE_FACT_KEYS_BASE_URL",
        "ALICE_FACT_KEYS_MODEL",
        "ALICE_FACT_KEYS_API_KEY",
        "ALICE_EMBEDDINGS_BASE_URL",
        "ALICE_EMBEDDINGS_MODEL",
        "ALICE_EMBEDDINGS_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _open_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    return conn


def _make_store(conn: sqlite3.Connection) -> SQLiteVNextStore:
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, f"{user_id}@example.com", "Test User")
    return SQLiteVNextStore(conn, user_id)


def _create_memory(store: SQLiteVNextStore, **overrides: object) -> dict[str, object]:
    memory: dict[str, object] = {
        "memory_key": f"memory.{uuid4()}",
        "value": {"text": INSTANCE_TEXT},
        "status": "active",
        "title": "Bike-a-Thon result",
        "canonical_text": INSTANCE_TEXT,
        "summary": "Bike-a-Thon outcome",
        "domain": "personal",
        "sensitivity": "private",
    }
    memory.update(overrides)
    return store.create_memory(memory)


# -- schema: FTS definition and legacy-file upgrade ----------------------------


def test_memories_fts_declares_fact_keys_column() -> None:
    conn = _open_connection()
    columns = [row[1] for row in conn.execute("PRAGMA table_info(memories_fts)")]
    assert columns == ["title", "canonical_text", "summary", "memory_key", "fact_keys"]
    memory_columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
    assert "fact_keys" in memory_columns
    conn.close()


def test_bootstrap_upgrades_legacy_fts_shape_and_rebuilds(tmp_path: Path) -> None:
    # Simulate a database file written before fact_keys shipped: memories
    # without the column, memories_fts with the old four-column shape.
    db_path = tmp_path / "alice.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = lambda cursor, row: {desc[0]: row[index] for index, desc in enumerate(cursor.description)}
    bootstrap_sqlite_schema(conn)
    store = _make_store(conn)
    user_id = store.user_id
    legacy = _create_memory(store, canonical_text="the walkathon went well", title="Walkathon")
    for trigger in ("memories_fts_after_insert", "memories_fts_after_delete", "memories_fts_after_update"):
        conn.execute(f"DROP TRIGGER {trigger}")
    conn.execute("DROP TABLE memories_fts")
    conn.execute("ALTER TABLE memories DROP COLUMN fact_keys")
    conn.execute(
        """
        CREATE VIRTUAL TABLE memories_fts USING fts5(
          title, canonical_text, summary, memory_key,
          content='memories', tokenize='porter unicode61'
        )
        """
    )
    conn.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    # Re-bootstrap: the stale table AND its triggers are replaced, the
    # column comes back, and the one-shot rebuild re-indexes legacy rows.
    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(memories_fts)")]
    assert columns == ["title", "canonical_text", "summary", "memory_key", "fact_keys"]
    store = SQLiteVNextStore(conn, user_id)
    assert [row["id"] for row in store.search_memories_fts(query="walkathon")] == [legacy["id"]]

    # The recreated triggers must carry fact_keys: attach + category query.
    assert apply_fact_keys(store, legacy["id"]) is True
    assert [row["id"] for row in store.search_memories_fts(query="charity event")] == [legacy["id"]]

    # Idempotent: a matching FTS table is left alone on the next bootstrap.
    bootstrap_sqlite_schema(conn)
    assert [row["id"] for row in store.search_memories_fts(query="charity event")] == [legacy["id"]]
    conn.close()


def test_bootstrap_upgrade_preserves_previously_attached_fact_keys(tmp_path: Path) -> None:
    # A current-shape file keeps indexed fact keys across re-bootstraps.
    db_path = tmp_path / "alice.db"
    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    store = _make_store(conn)
    user_id = store.user_id
    memory = _create_memory(store)
    attach_memory_fact_keys(store, memory)
    conn.commit()
    conn.close()

    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    store = SQLiteVNextStore(conn, user_id)
    assert [row["id"] for row in store.search_memories_fts(query=CATEGORY_QUERY)] == [memory["id"]]
    conn.close()


# -- store: indexing surface ----------------------------------------------------


def test_update_memory_fact_keys_round_trip_and_reset() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store)

    assert store.update_memory_fact_keys(memory_id=memory["id"], fact_keys="alpha; beta") is not None
    assert conn.execute("SELECT fact_keys FROM memories").fetchone()[0] == "alpha; beta"

    # Whitespace collapses to one line (the column is one indexable line).
    store.update_memory_fact_keys(memory_id=memory["id"], fact_keys="alpha;\n  beta\tgamma ")
    assert conn.execute("SELECT fact_keys FROM memories").fetchone()[0] == "alpha; beta gamma"

    # '' marks processed-but-empty; None resets to the backfill target.
    store.update_memory_fact_keys(memory_id=memory["id"], fact_keys="")
    assert conn.execute("SELECT fact_keys FROM memories").fetchone()[0] == ""
    store.update_memory_fact_keys(memory_id=memory["id"], fact_keys=None)
    assert conn.execute("SELECT fact_keys FROM memories").fetchone()[0] is None

    assert store.update_memory_fact_keys(memory_id=str(uuid4()), fact_keys="x") is None
    with pytest.raises(ContinuityStoreInvariantError):
        store.update_memory_fact_keys(memory_id=memory["id"], fact_keys=123)  # type: ignore[arg-type]
    conn.close()


def test_update_memory_fact_keys_is_user_scoped_and_skips_deleted() -> None:
    conn = _open_connection()
    owner = _make_store(conn)
    other = _make_store(conn)
    memory = _create_memory(owner)

    assert other.update_memory_fact_keys(memory_id=memory["id"], fact_keys="x") is None

    conn.execute("UPDATE memories SET deleted_at = '2026-07-01T00:00:00Z' WHERE id = ?", (memory["id"],))
    assert owner.update_memory_fact_keys(memory_id=memory["id"], fact_keys="x") is None
    conn.close()


def test_list_memories_missing_fact_keys_pages_and_excludes_processed() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    ids = sorted(_create_memory(store)["id"] for _ in range(5))
    processed = ids[2]
    store.update_memory_fact_keys(memory_id=processed, fact_keys="")

    first = store.list_memories_missing_fact_keys(limit=2)
    second = store.list_memories_missing_fact_keys(limit=2, after_id=first[-1]["id"])
    collected = [row["id"] for row in first + second]
    assert collected == [memory_id for memory_id in ids if memory_id != processed]
    assert store.list_memories_missing_fact_keys(limit=2, after_id=collected[-1]) == []
    conn.close()


# -- retrieval proof: strict FTS, no vectors -------------------------------------


def test_category_phrased_query_finds_instance_memory_only_after_fact_keys() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    target = _create_memory(store)
    decoy = _create_memory(
        store,
        title="Grocery run",
        canonical_text="Bought oat milk and bread at the market.",
        summary="groceries",
        value={"text": "Bought oat milk and bread at the market."},
    )

    # Strict AND pass: zero shared tokens => no match before derivation.
    assert store.search_memories_fts(query=CATEGORY_QUERY) == []

    assert attach_memory_fact_keys(store, target) is True
    assert attach_memory_fact_keys(store, decoy) is True

    rows = store.search_memories_fts(query=CATEGORY_QUERY)
    assert [row["id"] for row in rows] == [target["id"]]

    # The instance phrasing keeps working, and the decoy stays reachable
    # by its own text -- derived keys never hide direct matches.
    assert [row["id"] for row in store.search_memories_fts(query="Bike-a-Thon")] == [target["id"]]
    assert [row["id"] for row in store.search_memories_fts(query="oat milk")] == [decoy["id"]]
    conn.close()


def test_fact_key_matches_rank_below_direct_text_matches() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    direct = _create_memory(
        store,
        title="Fundraising update",
        canonical_text="Fundraising for the library is at half its goal.",
        summary="fundraising status",
        value={"text": "Fundraising for the library is at half its goal."},
    )
    derived = _create_memory(store)  # only says "Bike-a-Thon raised $5,000"
    attach_memory_fact_keys(store, derived)

    rows = store.search_memories_fts(query="fundraising")
    assert [row["id"] for row in rows] == [direct["id"], derived["id"]]
    assert rows[0]["fts_score"] > rows[1]["fts_score"]
    conn.close()


def test_fts_stays_consistent_when_memory_text_changes_after_fact_keys() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store)
    attach_memory_fact_keys(store, memory)

    store.update_memory(
        memory_id=memory["id"],
        patch={"canonical_text": "The Bike-a-Thon total was corrected to $6,000."},
    )

    # The five-column update trigger kept the external-content index in
    # sync: old and new text plus the (unchanged) fact keys all resolve.
    assert [row["id"] for row in store.search_memories_fts(query="corrected")] == [memory["id"]]
    assert [row["id"] for row in store.search_memories_fts(query=CATEGORY_QUERY)] == [memory["id"]]
    conn.close()


def test_redaction_clears_derived_fact_keys() -> None:
    # fact_keys are DERIVED FROM content ("5000 dollars", "charity event"
    # echo what the memory said), so true redaction must clear them the
    # same way it clears the content-derived embedding.
    conn = _open_connection()
    store = _make_store(conn)
    memory = _create_memory(store)
    attach_memory_fact_keys(store, memory)
    assert conn.execute("SELECT fact_keys FROM memories").fetchone()[0] != ""

    store.redact_memory_content(memory_id=memory["id"])

    assert conn.execute("SELECT fact_keys FROM memories").fetchone()[0] is None
    assert store.search_memories_fts(query=CATEGORY_QUERY) == []
    conn.close()


# -- write-path integration and backfill -----------------------------------------


def test_memory_commit_service_attaches_fact_keys_on_auto_commit() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    service = VNextMemoryCommitService(store)
    request = MemoryCommitRequest(
        user_id=store.user_id,
        title="Bike-a-Thon total",
        canonical_text="I finished the Bike-a-Thon and we raised $5,000.",
        domain="professional",
        sensitivity="internal",
        confidence=0.95,
    )

    result = service.commit(request=request, identity=None)

    assert result["status"] == "committed"
    stored = conn.execute("SELECT fact_keys FROM memories").fetchone()[0]
    assert "charity event fundraiser fundraising" in stored
    assert [row["id"] for row in store.search_memories_fts(query=CATEGORY_QUERY)] == [
        str(result["memory"]["id"])
    ]
    conn.close()


def test_backfill_covers_pre_existing_rows_on_the_real_store() -> None:
    conn = _open_connection()
    store = _make_store(conn)
    memories = [_create_memory(store) for _ in range(3)]
    blank = _create_memory(
        store,
        title=None,
        canonical_text="",
        summary=None,
        value={"text": ""},
    )

    summary = backfill_memory_fact_keys(store, batch_size=2, use_env_provider=False)

    assert summary["updated"] == 4
    assert summary["empty"] == 1
    found = {row["id"] for row in store.search_memories_fts(query=CATEGORY_QUERY)}
    assert found == {memory["id"] for memory in memories}
    assert conn.execute(
        "SELECT fact_keys FROM memories WHERE id = ?", (blank["id"],)
    ).fetchone()[0] == ""

    assert backfill_memory_fact_keys(store, use_env_provider=False)["updated"] == 0
    conn.close()


def test_backfill_script_runs_against_a_sqlite_database(tmp_path: Path) -> None:
    db_path = tmp_path / "alice.db"
    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    store = _make_store(conn)
    user_id = store.user_id
    memory = _create_memory(store)
    conn.commit()
    conn.close()

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "backfill_memory_fact_keys.py"),
            "--database-url",
            f"sqlite:///{db_path}",
            "--user-id",
            user_id,
            "--deterministic-only",
        ],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "ALICEBOT_FACT_KEYS_BACKFILL_REEXEC": "1"},
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["updated"] == 1
    assert payload["user_id"] == user_id

    conn = sqlite3.connect(str(db_path))
    bootstrap_sqlite_schema(conn)
    store = SQLiteVNextStore(conn, user_id)
    assert [row["id"] for row in store.search_memories_fts(query=CATEGORY_QUERY)] == [memory["id"]]
    conn.close()
