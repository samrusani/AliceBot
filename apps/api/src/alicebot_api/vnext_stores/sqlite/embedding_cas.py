"""SQLite embedding compare-and-swap store seam."""

from __future__ import annotations

import json
import sqlite3

import numpy as np

from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_embeddings import (
    EMBEDDING_SIGNATURE_METADATA_KEY,
    memory_embedding_content_sha256,
    pad_embedding_vector,
)
from alicebot_api.vnext_stores.sqlite.columns import MEMORY_COLUMNS

VNextRow = dict[str, object]


def _embedding_content_sha256_sqlite(
    title: object,
    canonical_text: object,
    summary: object,
) -> str:
    """SQLite UDF for the exact normalized text embedded by production."""
    return memory_embedding_content_sha256(
        {
            "title": title,
            "canonical_text": canonical_text,
            "summary": summary,
        }
    )


def _ensure_embedding_content_sha256_sqlite(conn: sqlite3.Connection) -> None:
    """Register the deterministic digest UDF once per SQLite connection."""
    cursor = conn.execute(
        "SELECT 1 FROM pragma_function_list WHERE name = 'alice_embedding_content_sha256' AND narg = 3 LIMIT 1"
    )
    try:
        registered = cursor.fetchone() is not None
    finally:
        cursor.close()
    if registered:
        return
    conn.create_function(
        "alice_embedding_content_sha256",
        3,
        _embedding_content_sha256_sqlite,
        deterministic=True,
    )


def update_memory_embedding(
    self,
    *,
    memory_id: str,
    vector: list[float],
    provider: str | None = None,
    model: str | None = None,
    endpoint: str | None = None,
    content_sha256: str | None = None,
    signature_version: int = 1,
) -> VNextRow | None:
    if not vector:
        raise ContinuityStoreInvariantError("embedding vectors must not be empty")
    padded = pad_embedding_vector(vector)
    blob = np.asarray(padded, dtype=np.float32).tobytes()
    signature_values = (provider, model, content_sha256)
    if any(value is not None for value in signature_values):
        if not all(isinstance(value, str) and value for value in signature_values):
            raise ContinuityStoreInvariantError(
                "embedding provider, model, and content_sha256 must be supplied together"
            )
        signature_metadata = {
            "version": signature_version,
            "provider": provider,
            "model": model,
            "endpoint": endpoint if isinstance(endpoint, str) else "",
            "content_sha256": content_sha256,
        }
        cursor = self._execute(
            """
                    UPDATE memories
                    SET embedding = ?,
                        metadata_json = json_set(metadata_json, ?, json(?))
                    WHERE id = ?
                      AND user_id = ?
                      AND deleted_at IS NULL
                      AND alice_embedding_content_sha256(title, canonical_text, summary) = ?
                    """,
            (
                blob,
                f"$.{EMBEDDING_SIGNATURE_METADATA_KEY}",
                json.dumps(signature_metadata, sort_keys=True, separators=(",", ":")),
                str(memory_id),
                self.user_id,
                content_sha256,
            ),
        )
    else:
        cursor = self._execute(
            """
                    UPDATE memories
                    SET embedding = ?
                    WHERE id = ?
                      AND user_id = ?
                      AND deleted_at IS NULL
                    """,
            (blob, str(memory_id), self.user_id),
        )
    if cursor.rowcount == 0:
        return None
    return self._fetch_optional_one(
        """
                SELECT id
                FROM memories
                WHERE id = ?
                  AND user_id = ?
                """,
        (str(memory_id), self.user_id),
    )


def clear_memory_embedding(self, *, memory_id: str) -> VNextRow | None:
    """Invalidate an embedding derived from text that is about to change."""
    cursor = self._execute(
        f"""
                UPDATE memories
                SET embedding = NULL,
                    metadata_json = json_remove(
                      metadata_json,
                      '$.{EMBEDDING_SIGNATURE_METADATA_KEY}'
                    )
                WHERE id = ?
                  AND user_id = ?
                  AND deleted_at IS NULL
                """,
        (str(memory_id), self.user_id),
    )
    if cursor.rowcount == 0:
        return None
    return self._fetch_optional_one(
        """
                SELECT id
                FROM memories
                WHERE id = ?
                  AND user_id = ?
                """,
        (str(memory_id), self.user_id),
    )


def list_memories_missing_embeddings(
    self,
    *,
    limit: int = 100,
    after_id: str | None = None,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
    embedding_endpoint: str | None = None,
    embedding_signature_version: int | None = None,
) -> list[VNextRow]:
    """Rows missing a vector or carrying an incompatible signature."""
    if limit < 1:
        raise ContinuityStoreInvariantError("embedding backfill limit must be positive")
    signature_sql = ""
    signature_params: list[object] = []
    if embedding_provider is not None or embedding_model is not None:
        if not embedding_provider or not embedding_model:
            raise ContinuityStoreInvariantError("embedding_provider and embedding_model must be supplied together")
        signature_sql = (
            " OR json_extract(metadata_json, ?) IS NOT ?"
            " OR json_extract(metadata_json, ?) IS NOT ?"
            " OR json_extract(metadata_json, ?) IS NOT "
            "alice_embedding_content_sha256(title, canonical_text, summary)"
        )
        signature_params.extend(
            (
                f"$.{EMBEDDING_SIGNATURE_METADATA_KEY}.provider",
                embedding_provider,
                f"$.{EMBEDDING_SIGNATURE_METADATA_KEY}.model",
                embedding_model,
                f"$.{EMBEDDING_SIGNATURE_METADATA_KEY}.content_sha256",
            )
        )
        if embedding_endpoint is not None:
            # Re-embed rows whose stored endpoint differs from the current one.
            signature_sql += " OR json_extract(metadata_json, ?) IS NOT ?"
            signature_params.extend(
                (
                    f"$.{EMBEDDING_SIGNATURE_METADATA_KEY}.endpoint",
                    embedding_endpoint,
                )
            )
        if embedding_signature_version is not None:
            signature_sql += " OR json_extract(metadata_json, ?) IS NOT ?"
            signature_params.extend(
                (
                    f"$.{EMBEDDING_SIGNATURE_METADATA_KEY}.version",
                    embedding_signature_version,
                )
            )
    params: list[object] = [self.user_id, *signature_params, after_id, after_id, limit]
    return self._fetch_all(
        f"""
                SELECT {", ".join(MEMORY_COLUMNS)},
                  (embedding IS NOT NULL) AS embedding_present
                FROM memories
                WHERE user_id = ?
                  AND deleted_at IS NULL
                  AND (
                    embedding IS NULL
                    {signature_sql}
                  )
                  AND (? IS NULL OR id > ?)
                ORDER BY id ASC
                LIMIT ?
                """,
        tuple(params),
    )


for _embedding_method in (
    update_memory_embedding,
    clear_memory_embedding,
    list_memories_missing_embeddings,
):
    _embedding_method.__module__ = "alicebot_api.sqlite_store"
    _embedding_method.__qualname__ = f"SQLiteVNextStore.{_embedding_method.__name__}"
del _embedding_method
