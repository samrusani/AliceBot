"""Live PostgreSQL regression for content-stale vector backfill selection."""

from __future__ import annotations

from uuid import uuid4

import pytest

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
        assert (
            store.list_memories_missing_embeddings(
                embedding_provider="openai_compatible",
                embedding_model="embed-v1",
                embedding_endpoint="host-a",
                embedding_signature_version=2,
            )
            == []
        )

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


@pytest.mark.parametrize(
    ("boundary", "title", "canonical_text", "summary"),
    [
        ("nbsp", "\u00a0Signed memory\u00a0", "\u00a0Whitespace fact\u00a0", "\u00a0Whitespace fact\u00a0"),
        ("u001c", "\u001cSigned memory\u001c", "\u001cWhitespace fact\u001c", "\u001cWhitespace fact\u001c"),
        (
            "mixed_blank",
            "\u00a0\u001c",
            "\u001cMixed whitespace fact\u00a0",
            "\u00a0Mixed whitespace fact\u001c",
        ),
    ],
)
def test_embedding_cas_matches_python_strip_for_unicode_boundaries(
    migrated_database_urls,
    boundary: str,
    title: str,
    canonical_text: str,
    summary: str,
) -> None:
    user_id = uuid4()
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"embedding-whitespace-{boundary}-{user_id}@example.invalid",
            f"Embedding whitespace {boundary}",
        )
        store = PostgresVNextStore(conn)
        memory = store.create_memory(
            {
                "memory_key": f"embedding.whitespace.{uuid4()}",
                "value": {"text": "Whitespace fact"},
                "status": "active",
                "title": title,
                "canonical_text": canonical_text,
                "summary": summary,
                "domain": "project",
                "sensitivity": "private",
            }
        )
        digest = memory_embedding_content_sha256(memory)
        updated = store.update_memory_embedding(
            memory_id=str(memory["id"]),
            vector=pad_embedding_vector([1.0, 0.0]),
            provider="openai_compatible",
            model="embed-v1",
            endpoint="host-a",
            content_sha256=digest,
            signature_version=2,
        )

        assert updated is not None
        assert (
            store.list_memories_missing_embeddings(
                embedding_provider="openai_compatible",
                embedding_model="embed-v1",
                embedding_endpoint="host-a",
                embedding_signature_version=2,
            )
            == []
        )
        vector_rows = store.search_memories_vector(
            query_vector=pad_embedding_vector([1.0, 0.0]),
            embedding_provider="openai_compatible",
            embedding_model="embed-v1",
            embedding_endpoint="host-a",
            embedding_signature_version=2,
            limit=5,
        )
        assert str(memory["id"]) in {str(row["id"]) for row in vector_rows}
