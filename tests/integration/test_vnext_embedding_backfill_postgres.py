"""Live PostgreSQL regression for content-stale vector backfill selection."""

from __future__ import annotations

from uuid import uuid4

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_embeddings import (
    memory_embedding_content_sha256,
    pad_embedding_vector,
)
from alicebot_api.vnext_store import PostgresVNextStore


def test_backfill_selects_vector_whose_content_signature_is_stale(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    user_id = uuid4()
    with user_connection(app_url, user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"embedding-backfill-{user_id}@example.invalid",
            "Embedding backfill",
        )
        store = PostgresVNextStore(conn)
        memory = store.create_memory(
            {
                "memory_key": f"embedding.backfill.{uuid4()}",
                "value": {"text": "Original fact"},
                "status": "active",
                "title": "Signed memory",
                "canonical_text": "Original fact",
                "summary": "A signed vector",
                "domain": "project",
                "sensitivity": "private",
            }
        )
        store.update_memory_embedding(
            memory_id=str(memory["id"]),
            vector=pad_embedding_vector([1.0, 0.0]),
            provider="openai_compatible",
            model="embed-v1",
            endpoint="host-a",
            content_sha256=memory_embedding_content_sha256(memory),
            signature_version=2,
        )
        assert store.list_memories_missing_embeddings(
            embedding_provider="openai_compatible",
            embedding_model="embed-v1",
            embedding_endpoint="host-a",
            embedding_signature_version=2,
        ) == []

        # Simulate an old snapshot/direct adapter bypassing lifecycle hooks.
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE memories SET canonical_text = %s WHERE id = %s::uuid",
                ("Changed fact", str(memory["id"])),
            )

        stale = store.list_memories_missing_embeddings(
            embedding_provider="openai_compatible",
            embedding_model="embed-v1",
            embedding_endpoint="host-a",
            embedding_signature_version=2,
        )

    assert [str(row["id"]) for row in stale] == [str(memory["id"])]
    assert stale[0]["embedding_present"] is True
