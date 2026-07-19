"""Process-local resident vector cache for the SQLite store (Stage 2).

``search_memories_vector`` Stage 1 (memory_access.py) made the scan
vectorized but still streams every embedding blob out of SQLite on every
query. Stage 2 keeps the per-user embedding matrix resident in process
memory and re-validates it against a one-row ``embedding_stamp`` token
before every use:

- The registry is keyed by ``(resolved main database file, user_id)`` and
  is DISABLED for ``:memory:`` databases (no stable identity, and other
  connections cannot share the data anyway).
- The ``embedding_stamp`` token is REWRITTEN to a fresh ``uuid4().hex``
  (never incremented) in the same transaction as every write that changes
  or destroys an existing non-NULL embedding: overwrites via
  ``update_memory_embedding`` (reindex/backfill), ``clear_memory_embedding``
  (the clear-then-re-embed text-update flow), and the redaction/lifecycle
  paths that NULL embeddings inline (owner-decided prompt eviction).
  Rewriting instead of incrementing means a restored database snapshot can
  never alias a token a live cache entry was built at.
- Embed-on-write (NULL -> vector) intentionally does NOT bump: the row id
  is new to the cache, so the query path fetches it as a missing candidate
  and upserts it without a rebuild.
- The cache holds ONLY vectors, norms, and the id -> row map. Every
  query-time predicate -- lifecycle, scope, AND the embedding-signature
  json_extract clauses -- runs as fresh candidate SQL on every query,
  exactly like the stateless path. Nothing predicate-shaped is ever
  captured into the resident data, so a metadata_json rewrite (e.g.
  ``update_memory`` patching the signature without touching the embedding
  column) cannot go stale: the next candidate SELECT simply sees it.
- The cached scan only ever produces the approximate RANKING. The final
  ``vector_distance`` of every returned row is recomputed by the Stage 1
  hydrate from the hydrated row's own blob (never from cache bytes), and
  the hydrate re-applies the full predicate SQL, so results stay
  bit-identical to the stateless path and concurrent-mutation semantics
  are unchanged.

Configuration (read per query so operators and tests can flip it live):

- ``ALICEBOT_SQLITE_VECTOR_CACHE=off`` disables the cache entirely.
- ``ALICEBOT_SQLITE_VECTOR_CACHE_MAX_MB`` caps the resident matrix bytes
  per (database, user); above the cap the store silently stays on the
  stateless Stage 1 scan. Default 1024.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from typing import cast
from uuid import uuid4

import numpy as np

from alicebot_api.vnext_embeddings import EMBEDDING_VECTOR_DIMENSIONS

VECTOR_CACHE_ENV = "ALICEBOT_SQLITE_VECTOR_CACHE"
VECTOR_CACHE_MAX_MB_ENV = "ALICEBOT_SQLITE_VECTOR_CACHE_MAX_MB"
DEFAULT_VECTOR_CACHE_MAX_MB = 1024

_OFF_VALUES = frozenset({"off", "0", "false", "no", "disabled"})

#: Bytes one cached row occupies in the float32 matrix.
_ROW_BYTES = EMBEDDING_VECTOR_DIMENSIONS * 4

#: Row batch for streaming SELECTs, the chunked row-norm computation, and
#: the float64 matvec. Per-row results are independent of the chunk size
#: (each output element is its own dot/norm), so this is purely a memory
#: knob: 2048 rows keeps every transient -- one chunk of ~6 KiB SQLite
#: blobs (~12 MiB), the squared-norm temporary (~12 MiB), and the reusable
#: float64 matvec scratch (~24 MiB) -- small enough that allocator-retained
#: churn pages stay negligible next to the resident matrix.
_SCAN_CHUNK_ROWS = 2048

#: Rebuild instead of serving when live embedding rows fall below this
#: fraction of cached rows (dead soft-deleted/cleared rows dominate).
_COMPACT_LIVE_FRACTION = 0.5

#: Conservative SQLITE_MAX_VARIABLE_NUMBER budget (mirrors Stage 1 hydrate).
_MAX_SQL_VARIABLES = 900

_EMBEDDING_STAMP_SELECT_SQL = "SELECT token FROM embedding_stamp WHERE id = 1"
_EMBEDDING_STAMP_BUMP_SQL = "UPDATE embedding_stamp SET token = ? WHERE id = 1"


class _VectorCacheEntry:
    """Resident vectors for one (database file, user_id).

    The entry object is created once and mutated in place under its lock;
    ``rebuilds`` counts full rebuilds so tests can prove the embed-on-write
    upsert path did not silently trigger one.
    """

    __slots__ = ("lock", "token", "matrix", "norms", "row_index", "rebuilds")

    def __init__(self) -> None:
        self.lock = threading.Lock()
        #: Stamp token the resident data was built/validated at.
        self.token: str | None = None
        #: Contiguous float32 (N, 1536) matrix of stored vectors, already
        #: padded/truncated to storage width exactly like
        #: ``_embedding_blob_distance`` does.
        self.matrix: np.ndarray = np.empty((0, EMBEDDING_VECTOR_DIMENSIONS), dtype=np.float32)
        #: float32 row norms of ``matrix`` (axis=1).
        self.norms: np.ndarray = np.empty(0, dtype=np.float32)
        #: memory id -> row position in ``matrix``.
        self.row_index: dict[str, int] = {}
        self.rebuilds = 0


_REGISTRY: dict[tuple[str, str], _VectorCacheEntry] = {}
_REGISTRY_LOCK = threading.Lock()


def _cache_disabled() -> bool:
    return os.environ.get(VECTOR_CACHE_ENV, "").strip().lower() in _OFF_VALUES


def _cache_max_bytes() -> int:
    raw = os.environ.get(VECTOR_CACHE_MAX_MB_ENV, "").strip()
    try:
        max_mb = int(raw) if raw else DEFAULT_VECTOR_CACHE_MAX_MB
    except ValueError:
        max_mb = DEFAULT_VECTOR_CACHE_MAX_MB
    return max(max_mb, 0) * 1024 * 1024


def _resolve_database_file(conn: sqlite3.Connection) -> str | None:
    """Resolved filesystem path of the ``main`` database, or ``None``.

    ``PRAGMA database_list`` reports an empty file for ``:memory:`` (and
    unnamed temporary) databases; those have no stable cross-connection
    identity, so the cache stays off for them.
    """
    cursor = conn.execute("PRAGMA database_list")
    cursor.row_factory = None  # bypass any installed dict row factory
    try:
        for _seq, name, file in cursor.fetchall():
            if name == "main":
                if not file:
                    return None
                return os.path.realpath(str(file))
    finally:
        cursor.close()
    return None


def bump_embedding_stamp(execute) -> None:
    """Rewrite the invalidation token to a fresh random value.

    ``execute`` is the store's statement runner (``self._execute``), so the
    bump joins whatever transaction the surrounding embedding write is in:
    the token and the vector change commit -- or roll back -- together.
    """
    try:
        execute(_EMBEDDING_STAMP_BUMP_SQL, (uuid4().hex,))
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            # Pre-stamp database file: the cache never activates on such
            # files (the stamp read fails identically), so skipping the bump
            # cannot produce stale cached results.
            return
        raise


def _read_stamp_token(conn: sqlite3.Connection) -> str | None:
    try:
        cursor = conn.execute(_EMBEDDING_STAMP_SELECT_SQL)
    except sqlite3.OperationalError:
        return None
    cursor.row_factory = None
    try:
        row = cursor.fetchone()
    finally:
        cursor.close()
    if row is None or row[0] is None:
        return None
    return str(row[0])


def _decode_blob_into(out_row: np.ndarray, blob: object) -> None:
    """Decode one stored blob straight into a preallocated matrix row.

    Slice assignment COPIES the float32 values, so nothing retains the
    ``np.frombuffer`` view (whose ``base`` would keep the whole blob bytes
    object alive); the blob is released with its source row chunk.
    Pads/truncates non-conforming blobs with exactly the resize logic of
    ``_embedding_blob_distance`` so the cached row holds the same float32
    values the exact per-row scoring would parse from the blob.
    """
    vector: np.ndarray = np.frombuffer(cast(bytes, blob), dtype=np.float32)
    if vector.size == EMBEDDING_VECTOR_DIMENSIONS:
        out_row[:] = vector
        return
    out_row[:] = 0.0
    width = min(vector.size, EMBEDDING_VECTOR_DIMENSIONS)
    out_row[:width] = vector[:width]


def _chunked_row_norms(matrix: np.ndarray) -> np.ndarray:
    """Float32 row norms of ``matrix`` computed chunk by chunk.

    ``np.linalg.norm(matrix, axis=1)`` materializes a full-matrix-sized
    squared temporary (~another 600 MB at 100k rows); chunking keeps that
    transient at ~48 MiB. Rows are independent, so the per-row values are
    bit-identical to the whole-matrix call.
    """
    norms = np.empty(matrix.shape[0], dtype=np.float32)
    for start in range(0, matrix.shape[0], _SCAN_CHUNK_ROWS):
        stop = min(start + _SCAN_CHUNK_ROWS, matrix.shape[0])
        norms[start:stop] = np.linalg.norm(matrix[start:stop], axis=1)
    return norms


def _exact_row_distance(row: np.ndarray, query_array: np.ndarray, query_norm: float) -> float:
    """Exact float32 cosine distance for one cached row.

    Bit-identical to ``_embedding_blob_distance`` on the row's source blob:
    the cached row holds the same float32 values, and the norm/dot use the
    same float32 BLAS calls.
    """
    vector_norm = float(np.linalg.norm(row))
    if query_norm == 0.0 or vector_norm == 0.0:
        return 1.0
    similarity = float(np.dot(query_array, row)) / (query_norm * vector_norm)
    return 1.0 - similarity


def _drop_entry(key: tuple[str, str]) -> None:
    with _REGISTRY_LOCK:
        _REGISTRY.pop(key, None)


def _count_live_embedding_rows(conn: sqlite3.Connection, user_id: str) -> int:
    cursor = conn.execute(
        """
        SELECT COUNT(*)
        FROM memories
        WHERE user_id = ?
          AND deleted_at IS NULL
          AND embedding IS NOT NULL
        """,
        (user_id,),
    )
    cursor.row_factory = None
    try:
        row = cursor.fetchone()
    finally:
        cursor.close()
    return int(row[0]) if row else 0


def _rebuild_entry(
    entry: _VectorCacheEntry,
    conn: sqlite3.Connection,
    user_id: str,
    token: str,
    expected_rows: int,
) -> None:
    """Full ids+embedding scan streamed into ONE preallocated matrix.

    The scan predicate is the cache-base superset (user, not deleted,
    embedding present); every query-time predicate -- status, domain,
    sensitivity, scope, signature -- is applied per query as fresh SQL
    against the candidate id set, never baked into the resident data.

    Memory discipline: the float32 (N, 1536) matrix is allocated ONCE from
    the caller's live-row COUNT and each fetchmany chunk's blobs are
    decoded straight into their rows (slice assignment copies), so at no
    point is more than one chunk of blob bytes alive alongside the matrix.
    The previous accumulate-then-``np.stack`` shape kept every blob (via
    the frombuffer views' ``base``) PLUS the stacked copy resident at once
    -- ~3x the matrix bytes at peak on a 100k-row corpus.

    ``expected_rows`` can go stale between the COUNT and this scan
    (autocommit reads see concurrent commits):

    - Fewer live rows: the owning matrix is shrunk in place
      (``resize(refcheck=False)`` -- no copy, no view).
    - More live rows: the scan stops at capacity. Uncached rows are just
      missing candidates; the caller's upsert step fetches them in the
      SAME query before any ranking is produced, so results are unchanged.
    """
    matrix: np.ndarray = np.empty((expected_rows, EMBEDDING_VECTOR_DIMENSIONS), dtype=np.float32)
    row_index: dict[str, int] = {}
    filled = 0
    cursor = conn.execute(
        """
        SELECT id, embedding
        FROM memories
        WHERE user_id = ?
          AND deleted_at IS NULL
          AND embedding IS NOT NULL
        """,
        (user_id,),
    )
    cursor.row_factory = None
    try:
        while filled < expected_rows:
            chunk = cursor.fetchmany(min(_SCAN_CHUNK_ROWS, expected_rows - filled))
            if not chunk:
                break
            for memory_id, blob in chunk:
                _decode_blob_into(matrix[filled], blob)
                row_index[str(memory_id or "")] = filled
                filled += 1
    finally:
        cursor.close()
    if filled != expected_rows:
        matrix.resize((filled, EMBEDDING_VECTOR_DIMENSIONS), refcheck=False)
    entry.matrix = matrix
    entry.norms = _chunked_row_norms(matrix)
    entry.row_index = row_index
    entry.token = token
    entry.rebuilds += 1


def _upsert_missing_rows(
    entry: _VectorCacheEntry,
    conn: sqlite3.Connection,
    user_id: str,
    missing_ids: list[str],
) -> None:
    """Fetch-and-append vectors for candidate ids the cache has not seen.

    This is the embed-on-write path: a NULL -> vector write does not bump
    the stamp, so the new row arrives here instead of forcing a rebuild.
    The entry object is mutated in place (no rebuild is counted).

    Same streaming discipline as ``_rebuild_entry``: the block is
    preallocated once (``len(missing_ids)`` is an upper bound on the rows
    the batched SELECTs can return) and each batch's blobs are decoded
    straight into it, so no frombuffer view retains blob bytes past its
    own <=900-row batch.
    """
    block: np.ndarray = np.empty((len(missing_ids), EMBEDDING_VECTOR_DIMENSIONS), dtype=np.float32)
    new_ids: list[str] = []
    for start in range(0, len(missing_ids), _MAX_SQL_VARIABLES):
        batch = missing_ids[start : start + _MAX_SQL_VARIABLES]
        placeholders = ", ".join("?" for _id in batch)
        cursor = conn.execute(
            f"""
            SELECT id, embedding
            FROM memories
            WHERE user_id = ?
              AND deleted_at IS NULL
              AND embedding IS NOT NULL
              AND id IN ({placeholders})
            """,
            (user_id, *batch),
        )
        cursor.row_factory = None
        try:
            rows = cursor.fetchall()
        finally:
            cursor.close()
        for memory_id, blob in rows:
            candidate_id = str(memory_id or "")
            if candidate_id in entry.row_index:
                continue
            _decode_blob_into(block[len(new_ids)], blob)
            new_ids.append(candidate_id)
    if not new_ids:
        # A candidate row whose embedding vanished between the candidate
        # SELECT and this fetch simply stays out of the cache; the ranking
        # skips it and the hydrate re-check would have dropped it anyway.
        return
    if len(new_ids) != block.shape[0]:
        block.resize((len(new_ids), EMBEDDING_VECTOR_DIMENSIONS), refcheck=False)
    base = entry.matrix.shape[0]
    entry.matrix = np.concatenate([entry.matrix, block])
    entry.norms = np.concatenate([entry.norms, _chunked_row_norms(block)])
    for offset, candidate_id in enumerate(new_ids):
        entry.row_index[candidate_id] = base + offset


def _candidate_id_rows(
    conn: sqlite3.Connection,
    predicate_sql: str,
    predicate_params: tuple[object, ...],
) -> list[tuple[str, str]]:
    """(id, updated_at) for every row matching the scan's FULL predicate set.

    ``predicate_sql`` is the exact WHERE clause of the stateless Stage 1
    scan, including the embedding-signature json_extract clauses, so
    predicate evaluation always reads the live row -- it cannot go stale
    no matter how metadata_json is rewritten.
    """
    cursor = conn.execute(
        f"""
        SELECT id, updated_at
        FROM memories
        WHERE {predicate_sql}
        """,
        predicate_params,
    )
    cursor.row_factory = None
    candidates: list[tuple[str, str]] = []
    try:
        while True:
            chunk = cursor.fetchmany(_SCAN_CHUNK_ROWS)
            if not chunk:
                break
            candidates.extend((str(memory_id or ""), str(updated_at or "")) for memory_id, updated_at in chunk)
    finally:
        cursor.close()
    return candidates


def _ranked_from_entry(
    entry: _VectorCacheEntry,
    candidates: list[tuple[str, str]],
    query_array: np.ndarray,
    query_norm: float,
    tiny_norm_threshold: float,
) -> list[tuple[float, str, str]]:
    """Approximate (distance, updated_at, id) ranking from resident vectors.

    Scoring math mirrors Stage 1 exactly: float64 dot over the float32
    matrix (chunked, one row per output -- masking non-candidates instead
    of gathering selects identical per-row results), float32 norms upcast
    to float64, and the exact per-row float32 path for near-subnormal norms
    where the vectorized error bound does not hold.
    """
    ranked: list[tuple[float, str, str]] = []
    total_rows = entry.matrix.shape[0]
    if total_rows == 0 or not candidates:
        return ranked
    dots: np.ndarray | None = None
    norms64: np.ndarray | None = None
    if query_norm != 0.0:
        query64: np.ndarray = query_array.astype(np.float64)
        dots = np.empty(total_rows, dtype=np.float64)
        # One reusable float64 scratch for the chunked upcast: ``copyto``
        # performs the same float32 -> float64 cast ``astype`` would, into
        # the same buffer every iteration, so the matvec allocates nothing
        # per chunk (a fresh ``astype`` per chunk leaves allocator-retained
        # churn pages behind at large row counts).
        scratch: np.ndarray = np.empty((min(_SCAN_CHUNK_ROWS, total_rows), entry.matrix.shape[1]), dtype=np.float64)
        for start in range(0, total_rows, _SCAN_CHUNK_ROWS):
            stop = min(start + _SCAN_CHUNK_ROWS, total_rows)
            width = stop - start
            np.copyto(scratch[:width], entry.matrix[start:stop])
            dots[start:stop] = scratch[:width] @ query64
        norms64 = entry.norms.astype(np.float64)
    for candidate_id, updated_key in candidates:
        position = entry.row_index.get(candidate_id)
        if position is None:
            # Vanished between the candidate SELECT and the upsert fetch.
            continue
        if dots is None or norms64 is None:
            distance = 1.0
        elif entry.norms[position] < tiny_norm_threshold:
            distance = _exact_row_distance(entry.matrix[position], query_array, query_norm)
        else:
            distance = 1.0 - float(dots[position]) / (query_norm * float(norms64[position]))
        ranked.append((distance, updated_key, candidate_id))
    ranked.sort()
    return ranked


def cached_vector_ranked(
    store,
    *,
    predicate_sql: str,
    predicate_params: tuple[object, ...],
    query_array: np.ndarray,
    query_norm: float,
    tiny_norm_threshold: float,
) -> list[tuple[float, str, str]] | None:
    """Ranked (approx_distance, updated_at, id) list from the resident cache.

    Returns ``None`` whenever the cache must not serve -- disabled via env,
    ``:memory:`` database, over the byte cap, stamp table unavailable, or a
    scan error -- and the caller falls back to the stateless Stage 1 scan.
    """
    if _cache_disabled():
        return None
    conn = store.conn
    try:
        db_path = _resolve_database_file(conn)
    except sqlite3.Error:
        return None
    if db_path is None:
        return None
    key = (db_path, str(store.user_id))
    with _REGISTRY_LOCK:
        entry = _REGISTRY.get(key)
        if entry is None:
            entry = _VectorCacheEntry()
            _REGISTRY[key] = entry
    with entry.lock:
        # Read-validate-serve is atomic per query under the entry lock: the
        # token read here and the data served below come from this
        # connection's current snapshot.
        token = _read_stamp_token(conn)
        if token is None:
            _drop_entry(key)
            return None
        max_bytes = _cache_max_bytes()
        try:
            rebuilt = entry.token != token
            if rebuilt:
                # Cap pre-check before building: estimated matrix bytes over
                # the cap keep the store on the stateless path.
                live_rows = _count_live_embedding_rows(conn, str(store.user_id))
                if live_rows * _ROW_BYTES > max_bytes:
                    _drop_entry(key)
                    return None
                _rebuild_entry(entry, conn, str(store.user_id), token, live_rows)
            elif entry.matrix.nbytes > max_bytes:
                # Warm serve: the resident byte count is exact and free.
                _drop_entry(key)
                return None
            candidates = _candidate_id_rows(conn, predicate_sql, predicate_params)
            if not rebuilt and entry.row_index and len(candidates) < _COMPACT_LIVE_FRACTION * len(entry.row_index):
                # Few candidates relative to cached rows: EITHER the query is
                # narrowly filtered OR the cache is mostly dead rows
                # (soft-deleted/cleared without a bump). Only now pay the
                # live-row count to tell them apart, and compact when live
                # rows really fell below the fraction. Broad queries -- the
                # hot retrieval path -- never pay this count.
                live_rows = _count_live_embedding_rows(conn, str(store.user_id))
                if live_rows < _COMPACT_LIVE_FRACTION * len(entry.row_index):
                    if live_rows * _ROW_BYTES > max_bytes:
                        _drop_entry(key)
                        return None
                    _rebuild_entry(entry, conn, str(store.user_id), token, live_rows)
            missing = [candidate_id for candidate_id, _updated in candidates if candidate_id not in entry.row_index]
            if missing:
                if (len(entry.row_index) + len(missing)) * _ROW_BYTES > max_bytes:
                    _drop_entry(key)
                    return None
                _upsert_missing_rows(entry, conn, str(store.user_id), missing)
        except (sqlite3.Error, ValueError, TypeError):
            # Any malformed row or SQL failure degrades to the stateless
            # scan, which fails (or succeeds) exactly like Stage 1 would.
            _drop_entry(key)
            return None
        return _ranked_from_entry(
            entry,
            candidates,
            query_array,
            query_norm,
            tiny_norm_threshold,
        )
