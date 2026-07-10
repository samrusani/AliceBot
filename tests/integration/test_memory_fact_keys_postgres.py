"""Derived retrieval keys (fact_keys) against a real migrated Postgres.

Unit tests cover the SQLite FTS5 mirror; only a live-Postgres run
exercises migration ``20260707_0082`` -- the ``fact_keys`` column, the
rebuilt ``search_tsv`` generated column with its ``'D'`` weight, and the
GIN index -- plus ``update_memory_fact_keys`` /
``list_memories_missing_fact_keys`` and the commit-path attach hook on
``PostgresVNextStore``. Everything here is strict FTS: the embedding env
is cleared, so no vectors participate.
"""

from __future__ import annotations

from uuid import uuid4

from alembic import command
import psycopg

from alicebot_api.db import user_connection
from alicebot_api.migrations import make_alembic_config
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_fact_keys import backfill_memory_fact_keys
from alicebot_api.vnext_memory_commit import MemoryCommitRequest, VNextMemoryCommitService
from alicebot_api.vnext_store import PostgresVNextStore


CATEGORY_QUERY = "charity event fundraising total"
INSTANCE_TEXT = "The Bike-a-Thon raised $5,000 for the hospital."


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


def _create_instance_memory(store: PostgresVNextStore, **overrides: object) -> dict[str, object]:
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


def _memories_columns(admin_url: str) -> set[str]:
    with psycopg.connect(admin_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'memories'"
            )
            return {row[0] for row in cur.fetchall()}


def test_migration_up_backfill_and_downgrade_round_trip(database_urls, monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    config = make_alembic_config(database_urls["admin"])
    user_id = uuid4()

    # A row written BEFORE fact_keys shipped.
    command.upgrade(config, "20260707_0081")
    with user_connection(database_urls["app"], user_id) as conn:
        ContinuityStore(conn).create_user(user_id, "fact-keys@example.invalid", "Fact Keys")
        store = PostgresVNextStore(conn)
        legacy = _create_instance_memory(store)

    command.upgrade(config, "head")
    columns = _memories_columns(database_urls["admin"])
    assert "fact_keys" in columns
    assert "search_tsv" in columns

    with user_connection(database_urls["app"], user_id) as conn:
        store = PostgresVNextStore(conn)

        # ADD COLUMN computed the regenerated search_tsv for existing rows:
        # the pre-migration row is still findable by its own text ...
        assert [str(row["id"]) for row in store.search_memories_fts(query="Bike-a-Thon")] == [
            str(legacy["id"])
        ]
        # ... but shares zero tokens with the category phrasing.
        assert store.search_memories_fts(query=CATEGORY_QUERY) == []

        # Deterministic backfill derives and stores the keys ...
        assert [str(row["id"]) for row in store.list_memories_missing_fact_keys()] == [
            str(legacy["id"])
        ]
        summary = backfill_memory_fact_keys(store, use_env_provider=False)
        assert summary["updated"] == 1
        assert store.list_memories_missing_fact_keys() == []

        # ... and the generated column + GIN index now bridge the gap.
        assert [str(row["id"]) for row in store.search_memories_fts(query=CATEGORY_QUERY)] == [
            str(legacy["id"])
        ]

    # Downgrade restores the 0072 expression and drops the column; the
    # instance phrasing keeps working without fact keys.
    command.downgrade(config, "20260707_0081")
    columns = _memories_columns(database_urls["admin"])
    assert "fact_keys" not in columns
    assert "search_tsv" in columns
    with user_connection(database_urls["app"], user_id) as conn:
        store = PostgresVNextStore(conn)
        assert [str(row["id"]) for row in store.search_memories_fts(query="Bike-a-Thon")] == [
            str(legacy["id"])
        ]
        assert store.search_memories_fts(query=CATEGORY_QUERY) == []


def test_fact_keys_rank_below_direct_matches_and_scope_by_user(migrated_database_urls, monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    user_id = uuid4()
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        ContinuityStore(conn).create_user(user_id, "fact-keys-rank@example.invalid", "Rank")
        store = PostgresVNextStore(conn)
        direct = _create_instance_memory(
            store,
            title="Fundraising update",
            canonical_text="Fundraising for the library is at half its goal.",
            summary="fundraising status",
            value={"text": "Fundraising for the library is at half its goal."},
        )
        derived = _create_instance_memory(store)
        decoy = _create_instance_memory(
            store,
            title="Grocery run",
            canonical_text="Bought oat milk and bread at the market.",
            summary="groceries",
            value={"text": "Bought oat milk and bread at the market."},
        )
        backfill_memory_fact_keys(store, use_env_provider=False)

        rows = store.search_memories_fts(query="fundraising")
        assert [str(row["id"]) for row in rows] == [str(direct["id"]), str(derived["id"])]
        assert rows[0]["fts_score"] > rows[1]["fts_score"]

        # Category phrasing reaches exactly the instance memory; the decoy
        # keeps matching only its own vocabulary.
        assert [str(row["id"]) for row in store.search_memories_fts(query=CATEGORY_QUERY)] == [
            str(derived["id"])
        ]
        assert [str(row["id"]) for row in store.search_memories_fts(query="oat milk")] == [
            str(decoy["id"])
        ]

        # update_memory_fact_keys: '' marks processed, None resets.
        assert store.update_memory_fact_keys(memory_id=str(derived["id"]), fact_keys=None) is not None
        assert [str(row["id"]) for row in store.list_memories_missing_fact_keys()] == [
            str(derived["id"])
        ]
        assert store.search_memories_fts(query=CATEGORY_QUERY) == []
        assert store.update_memory_fact_keys(memory_id=str(derived["id"]), fact_keys="") is not None
        assert store.list_memories_missing_fact_keys() == []


def test_memory_commit_attaches_fact_keys_on_postgres(migrated_database_urls, monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    user_id = uuid4()
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        ContinuityStore(conn).create_user(user_id, "fact-keys-commit@example.invalid", "Commit")
        store = PostgresVNextStore(conn)
        service = VNextMemoryCommitService(store)
        request = MemoryCommitRequest(
            user_id=str(user_id),
            title="Bike-a-Thon total",
            canonical_text="I finished the Bike-a-Thon and we raised $5,000.",
            domain="professional",
            sensitivity="internal",
            confidence=0.95,
        )

        result = service.commit(request=request, identity=None)

        assert result["status"] == "committed"
        assert [str(row["id"]) for row in store.search_memories_fts(query=CATEGORY_QUERY)] == [
            str(result["memory"]["id"])
        ]
        # The commit path already processed the row: nothing left to backfill.
        assert store.list_memories_missing_fact_keys() == []

        # True redaction clears the content-derived keys alongside the
        # content itself (they echo what the memory said).
        store.redact_memory_content(memory_id=str(result["memory"]["id"]))
        with conn.cursor() as cur:
            cur.execute("SELECT fact_keys FROM memories WHERE id = %s::uuid", (str(result["memory"]["id"]),))
            assert cur.fetchone()["fact_keys"] is None
        assert store.search_memories_fts(query=CATEGORY_QUERY) == []
