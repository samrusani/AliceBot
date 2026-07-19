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
from alicebot_api.vnext_stores.sqlite.vector_scan import bump_embedding_stamp

VNextRow = dict[str, object]

# Point-read backing the resident-vector-cache invalidation contract: only a
# write that OVERWRITES or CLEARS an existing non-NULL embedding bumps the
# embedding_stamp token (in the same transaction as the write). Embed-on-write
# for a row without a vector must NOT bump -- the cache upserts new ids
# without a rebuild.
#
# The read is only sound while it shares a transaction with the UPDATE and
# the bump: executed in autocommit, a concurrent embed-on-write can commit
# NULL -> vector between the read and the UPDATE, turning this write into an
# overwrite whose bump the stale read skips (the cache then serves the dead
# vector forever). Both callers therefore take the writer lock (BEGIN
# IMMEDIATE, unless the caller already opened a transaction) BEFORE reading.
_EMBEDDING_PRESENT_SQL = """
                SELECT (embedding IS NOT NULL) AS embedding_present
                FROM memories
                WHERE id = ?
                  AND user_id = ?
                  AND deleted_at IS NULL
                """


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
    if not self.conn.in_transaction:
        # Writer lock BEFORE the presence read: the read decides bump vs
        # no-bump, so it must be atomic with the UPDATE and the bump.
        self.conn.execute("BEGIN IMMEDIATE")
    existing = self._fetch_optional_one(_EMBEDDING_PRESENT_SQL, (str(memory_id), self.user_id))
    overwrites_existing_vector = bool(existing and existing.get("embedding_present"))
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
    if overwrites_existing_vector:
        # Reindex/backfill overwrite of a live vector: evict every resident
        # cache built over the old bytes, atomically with this write.
        bump_embedding_stamp(self._execute)
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
    if not self.conn.in_transaction:
        # Writer lock BEFORE the presence read: the read decides bump vs
        # no-bump, so it must be atomic with the UPDATE and the bump.
        self.conn.execute("BEGIN IMMEDIATE")
    existing = self._fetch_optional_one(_EMBEDDING_PRESENT_SQL, (str(memory_id), self.user_id))
    had_vector = bool(existing and existing.get("embedding_present"))
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
    if had_vector:
        # THE CLEAR-THEN-RE-EMBED HOLE: the commit service clears and then
        # re-embeds on text updates. The re-embed sees a NULL column and does
        # not bump, the id is already resident, and the top-k content-sha
        # recheck cannot catch a same-id vector swap -- so the CLEAR must
        # evict, in the same transaction as the NULLing write.
        bump_embedding_stamp(self._execute)
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
