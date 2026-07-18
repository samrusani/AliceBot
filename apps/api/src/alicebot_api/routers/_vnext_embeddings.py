from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

from alicebot_api.db import user_connection
from alicebot_api.vnext_embeddings import (
    persist_deferred_memory_embeddings_best_effort,
)
from alicebot_api.vnext_store import PostgresVNextStore


@contextmanager
def _vnext_embedding_store_context(database_url: str, user_id: UUID):
    with user_connection(database_url, user_id) as conn:
        yield PostgresVNextStore(conn)


def _persist_vnext_deferred_embeddings(
    *,
    database_url: str,
    user_id: UUID,
    result: object,
    actor_type: str = "system",
    actor_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Prepare vectors without a connection, then persist in a short transaction."""

    deferred_inputs = getattr(result, "deferred_embedding_inputs", ())
    persist_deferred_memory_embeddings_best_effort(
        deferred_inputs,
        store_context=lambda: _vnext_embedding_store_context(database_url, user_id),
        actor_type=actor_type,
        actor_id=actor_id,
        trace_id=trace_id,
    )
