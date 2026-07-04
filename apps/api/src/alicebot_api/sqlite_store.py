"""SQLite-backed vNext store for the zero-infrastructure on-ramp.

``SQLiteVNextStore`` mirrors the method signatures and return shapes of
``alicebot_api.vnext_store.PostgresVNextStore`` for the store surface the
nine core MCP tools use, backed by a local SQLite file instead of
Postgres.

Tenancy: Postgres scopes every statement with row-level security bound to
``app.current_user_id()``. SQLite has no RLS, so this store binds the
``user_id`` given at construction into EVERY statement it issues. A query
without the ``user_id`` predicate is a security bug.

Value conventions (differences forced by SQLite storage types):
- ids and timestamps come back as TEXT (``str(uuid)`` / ISO-8601 UTC with
  a trailing ``Z``) instead of ``uuid.UUID`` / ``datetime`` objects.
  Callers already run rows through ``vnext_json.json_safe`` which maps
  those objects to exactly these strings.
- JSON columns are decoded back into dicts/lists, matching psycopg jsonb.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import numpy as np

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_embeddings import EMBEDDING_VECTOR_DIMENSIONS, pad_embedding_vector
from alicebot_api.vnext_event_log import build_event_log_record
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_store import _search_patterns

VNextRow = dict[str, object]

EVENT_LOG_COLUMNS = (
    "id",
    "user_id",
    "event_type",
    "actor_type",
    "actor_id",
    "target_type",
    "target_id",
    "occurred_at",
    "payload_json",
    "trace_id",
    "run_id",
    "integrity_hash",
)

SOURCE_COLUMNS = (
    "id",
    "user_id",
    "source_type",
    "title",
    "author",
    "uri",
    "raw_path",
    "content_hash",
    "captured_at",
    "source_created_at",
    "source_modified_at",
    "connector_name",
    "external_id",
    "domain",
    "sensitivity",
    "metadata_json",
    "deleted_at",
)

SOURCE_CHUNK_COLUMNS = (
    "id",
    "user_id",
    "source_id",
    "chunk_index",
    "text",
    "token_count",
    "metadata_json",
    "created_at",
)

MEMORY_COLUMNS = (
    "id",
    "user_id",
    "agent_profile_id",
    "memory_key",
    "value",
    "status",
    "source_event_ids",
    "memory_type",
    "confidence",
    "salience",
    "confirmation_status",
    "trust_class",
    "promotion_eligibility",
    "evidence_count",
    "independent_source_count",
    "extracted_by_model",
    "trust_reason",
    "valid_from",
    "valid_to",
    "last_confirmed_at",
    "title",
    "canonical_text",
    "summary",
    "domain",
    "sensitivity",
    "first_seen_at",
    "last_seen_at",
    "last_reviewed_at",
    "metadata_json",
    "commit_digest",
    "confirmation_id",
    "created_at",
    "updated_at",
    "deleted_at",
)

REVISION_COLUMNS = (
    "id",
    "user_id",
    "memory_id",
    "sequence_no",
    "action",
    "memory_key",
    "previous_value",
    "new_value",
    "source_event_ids",
    "candidate",
    "revision_number",
    "revision_type",
    "text_before",
    "text_after",
    "reason",
    "actor_type",
    "actor_id",
    "metadata_json",
    "created_at",
)

PROVENANCE_COLUMNS = (
    "id",
    "user_id",
    "target_type",
    "target_id",
    "source_id",
    "source_chunk_id",
    "quote",
    "evidence_role",
    "confidence",
    "created_at",
)

OPEN_LOOP_COLUMNS = (
    "id",
    "user_id",
    "memory_id",
    "title",
    "status",
    "opened_at",
    "due_at",
    "resolved_at",
    "resolution_note",
    "created_at",
    "updated_at",
    "description",
    "priority",
    "project_id",
    "person_id",
    "source_id",
    "closed_at",
    "domain",
    "sensitivity",
    "metadata_json",
)

AGENT_IDENTITY_COLUMNS = (
    "id",
    "user_id",
    "agent_id",
    "agent_type",
    "permission_profile",
    "display_name",
    "project_scope_json",
    "metadata_json",
    "created_at",
    "updated_at",
)

AGENT_API_KEY_COLUMNS = (
    "id",
    "user_id",
    "agent_id",
    "permission_profile",
    "key_hash",
    "key_prefix",
    "label",
    "created_at",
    "revoked_at",
    "last_used_at",
)

# Columns stored as JSON TEXT that must decode back to dicts/lists so
# returned rows match psycopg's jsonb decoding.
_JSON_COLUMNS = frozenset(
    {
        "candidate",
        "metadata_json",
        "new_value",
        "payload_json",
        "previous_value",
        "project_scope_json",
        "source_event_ids",
        "value",
    }
)

# Statuses the memory read path returns. Everything else -- including
# 'stale' (demoted by maintenance), 'superseded', and 'rejected' -- is
# excluded-by-default from retrieval. Mirrors
# vnext_store._MEMORY_SEARCHABLE_STATUSES_SQL; keep the two in sync.
_MEMORY_SEARCHABLE_STATUSES_SQL = "('active', 'accepted')"

# Seam for the Wave-2 memories.project_id column: project filtering reads
# the project id from metadata_json today. When the real column lands,
# swapping this template for "{prefix}project_id" updates every memory
# search in one line.
_MEMORY_PROJECT_ID_SQL_TEMPLATE = "json_extract({prefix}metadata_json, '$.project_id')"

# The snowball English stopword list -- the same list the Postgres
# 'english' text-search configuration applies inside
# websearch_to_tsquery(). FTS5 has no stopword support of its own, so
# AND-ing raw natural-language tokens ("what", "did", "the") would demand
# words the stored text never contains and return nothing. Bare terms in
# this set are dropped before the MATCH expression is built; quoted
# phrases are preserved verbatim.
_FTS_QUERY_STOPWORDS = frozenset(
    """
    i me my myself we our ours ourselves you your yours yourself yourselves
    he him his himself she her hers herself it its itself they them their
    theirs themselves what which who whom this that these those am is are
    was were be been being have has had having do does did doing a an the
    and but if or because as until while of at by for with about against
    between into through during before after above below to from up down in
    out on off over under again further then once here there when where why
    how all any both each few more most other some such no nor not only own
    same so than too very s t can will just don should now
    """.split()
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _iso_or_none(value: object | None) -> str | None:
    """Normalize timestamps to ISO-8601 UTC TEXT with a trailing ``Z``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _iso_or_now(value: object | None) -> str:
    return _iso_or_none(value) or _utc_now_iso()


def _new_id(value: object | None) -> str:
    if value is None or value == "":
        return str(uuid4())
    return str(value)


def _uuid_text(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _json_object_text(value: object | None) -> str:
    if value is None:
        value = {}
    return json.dumps(json_safe(value), ensure_ascii=False, separators=(",", ":"))


def _json_list_text(value: object | None) -> str:
    if value is None:
        value = []
    return json.dumps(json_safe(value), ensure_ascii=False, separators=(",", ":"))


def _sorted_field_names(record: JsonObject) -> list[str]:
    return sorted(str(key) for key in record)


def _fts_match_expression(query: str) -> str | None:
    """Translate a websearch-style query into a safe FTS5 MATCH expression.

    Quoted phrases are preserved as FTS5 phrase queries; bare terms are
    AND-ed after English stopwords are dropped, mirroring what
    ``websearch_to_tsquery('english', ...)`` does on the Postgres path (a
    query made only of stopwords matches nothing there too). Every token is
    individually double-quoted so FTS5 syntax metacharacters
    (``: * ^ ( ) - NEAR AND OR NOT``) cannot produce a parse error or
    operator injection.
    """
    normalized = " ".join(str(query).split())
    if not normalized:
        return None
    parts: list[str] = []
    for phrase in re.findall(r'"([^"]*)"', normalized):
        words = re.findall(r"\w+", phrase)
        if words:
            parts.append('"' + " ".join(words) + '"')
    remainder = re.sub(r'"[^"]*"', " ", normalized)
    for term in re.findall(r"\w+", remainder):
        if term.casefold() in _FTS_QUERY_STOPWORDS:
            continue
        parts.append(f'"{term}"')
    if not parts:
        return None
    return " AND ".join(parts)


def _dict_row_factory(cursor: sqlite3.Cursor, row: tuple[object, ...]) -> dict[str, object]:
    return {description[0]: row[index] for index, description in enumerate(cursor.description)}


def _row_as_dict(cursor: sqlite3.Cursor, row: object) -> VNextRow:
    if isinstance(row, Mapping):
        return dict(row)
    if isinstance(row, sqlite3.Row):
        return dict(row)
    names = [description[0] for description in cursor.description]
    return dict(zip(names, cast(tuple[object, ...], row)))


def ensure_sqlite_user(
    conn: sqlite3.Connection,
    user_id: UUID | str,
    email: str,
    display_name: str | None = None,
) -> VNextRow:
    """Bootstrap the local user row this store scopes everything to."""
    uid = str(user_id)
    cursor = conn.execute(
        "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
        (uid,),
    )
    row = cursor.fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO users (id, email, display_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (uid, email, display_name, _utc_now_iso()),
        )
        cursor = conn.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (uid,),
        )
        row = cursor.fetchone()
    if row is None:  # pragma: no cover - defensive
        raise ContinuityStoreInvariantError("ensure_sqlite_user did not return a row from the database")
    return _row_as_dict(cursor, row)


@contextmanager
def sqlite_user_connection(path: str | Path, user_id: UUID | str) -> Iterator[sqlite3.Connection]:
    """Open a bootstrapped SQLite connection wrapped in one transaction.

    Mirrors ``alicebot_api.db.user_connection`` semantics: dict rows, the
    schema is present, statements run inside a transaction that commits on
    clean exit and rolls back on error. The ``user_id`` is validated here;
    binding it into statements is the job of ``SQLiteVNextStore``.
    """
    if str(user_id).strip() == "":
        raise ContinuityStoreInvariantError("sqlite_user_connection requires a non-empty user_id")
    conn = sqlite3.connect(str(path))
    conn.row_factory = _dict_row_factory
    try:
        bootstrap_sqlite_schema(conn)
        conn.commit()
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


class SQLiteVNextStore:
    """SQLite-backed vNext repository facade for the second-brain kernel."""

    def __init__(self, conn: sqlite3.Connection, user_id: UUID | str):
        if str(user_id).strip() == "":
            raise ContinuityStoreInvariantError("SQLiteVNextStore requires a non-empty user_id")
        self.conn = conn
        self.user_id = str(user_id)

    # -- fetch helpers (mirror PostgresVNextStore conventions) ------------

    def _execute(self, query: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        return self.conn.execute(query, params)

    def _decode_row(self, row: VNextRow) -> VNextRow:
        decoded: VNextRow = {}
        for key, value in row.items():
            if key in _JSON_COLUMNS and isinstance(value, str):
                decoded[key] = json.loads(value)
            else:
                decoded[key] = value
        return decoded

    def _fetch_one(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] = (),
    ) -> VNextRow:
        row = self._fetch_optional_one(query, params)
        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )
        return row

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[object, ...] = (),
    ) -> VNextRow | None:
        cursor = self._execute(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return self._decode_row(_row_as_dict(cursor, row))

    def _fetch_all(
        self,
        query: str,
        params: tuple[object, ...] = (),
    ) -> list[VNextRow]:
        cursor = self._execute(query, params)
        return [self._decode_row(_row_as_dict(cursor, row)) for row in cursor.fetchall()]

    def _get_row(
        self,
        operation_name: str,
        table: str,
        columns: tuple[str, ...],
        row_id: str,
    ) -> VNextRow:
        return self._fetch_one(
            operation_name,
            f"""
                SELECT {", ".join(columns)}
                FROM {table}
                WHERE id = ?
                  AND user_id = ?
                """,
            (row_id, self.user_id),
        )

    # -- filter helpers ----------------------------------------------------

    @staticmethod
    def _placeholders(values: list[str]) -> str:
        return ", ".join("?" for _ in values)

    def _domain_clause(self, domains: list[str] | None, *, prefix: str = "") -> tuple[str, list[object]]:
        if domains is None:
            return "", []
        clause = (
            f" AND ({prefix}domain IN ({self._placeholders(domains)})"
            f" OR {prefix}domain = 'unknown')"
        )
        return clause, list(domains)

    def _sensitivity_clause(
        self,
        sensitivity_allowed: list[str] | None,
        *,
        prefix: str = "",
    ) -> tuple[str, list[object]]:
        if sensitivity_allowed is None:
            return "", []
        clause = f" AND {prefix}sensitivity IN ({self._placeholders(sensitivity_allowed)})"
        return clause, list(sensitivity_allowed)

    def _memory_type_clause(
        self,
        memory_types: tuple[str, ...],
        *,
        prefix: str = "",
    ) -> tuple[str, list[object]]:
        if not memory_types:
            return "", []
        values = list(memory_types)
        clause = f" AND {prefix}memory_type IN ({self._placeholders(values)})"
        return clause, list(values)

    def _project_clause(
        self,
        projects: tuple[str, ...],
        *,
        prefix: str = "",
    ) -> tuple[str, list[object]]:
        if not projects:
            return "", []
        values = list(projects)
        project_id_sql = _MEMORY_PROJECT_ID_SQL_TEMPLATE.format(prefix=prefix)
        clause = f" AND {project_id_sql} IN ({self._placeholders(values)})"
        return clause, list(values)

    @staticmethod
    def _expiry_clause(include_expired: bool, *, prefix: str = "") -> tuple[str, list[object]]:
        """Exclude memories whose validity window has closed (valid_to < now)."""
        if include_expired:
            return "", []
        clause = f" AND ({prefix}valid_to IS NULL OR {prefix}valid_to >= ?)"
        return clause, [_utc_now_iso()]

    @staticmethod
    def _like_any(column: str, pattern_count: int) -> str:
        predicate = f"LOWER(COALESCE({column}, '')) LIKE ?"
        return "(" + " OR ".join([predicate] * pattern_count) + ")"

    # -- event log ----------------------------------------------------------

    def _append_mutation_event(
        self,
        *,
        event_type: str,
        actor_type: str,
        target_type: str,
        target_id: object,
        payload: JsonObject,
        actor_id: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> VNextRow:
        return self.append_event(
            build_event_log_record(
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                target_type=target_type,
                target_id=str(target_id),
                payload=cast(JsonObject, json_safe(payload)),
                trace_id=trace_id,
                run_id=run_id,
            )
        )

    def append_event(self, event: JsonObject) -> VNextRow:
        event_id = _new_id(event.get("id"))
        self._execute(
            """
                INSERT INTO event_log (
                  id,
                  user_id,
                  event_type,
                  actor_type,
                  actor_id,
                  target_type,
                  target_id,
                  occurred_at,
                  payload_json,
                  trace_id,
                  run_id,
                  integrity_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                event_id,
                self.user_id,
                event["event_type"],
                event["actor_type"],
                event.get("actor_id"),
                event.get("target_type"),
                event.get("target_id"),
                _iso_or_now(event.get("occurred_at")),
                _json_object_text(event.get("payload_json")),
                event.get("trace_id"),
                event.get("run_id"),
                event.get("integrity_hash"),
            ),
        )
        return self._get_row("append_event", "event_log", EVENT_LOG_COLUMNS, event_id)

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[VNextRow]:
        clauses = ["user_id = ?"]
        params: list[object] = [self.user_id]
        if target_type is not None:
            clauses.append("target_type = ?")
            params.append(target_type)
        if target_id is not None:
            clauses.append("target_id = ?")
            params.append(target_id)
        limit_sql = ""
        if limit is not None:
            limit_sql = " LIMIT ?"
            params.append(limit)
        return self._fetch_all(
            f"""
                SELECT {", ".join(EVENT_LOG_COLUMNS)}
                FROM event_log
                WHERE {" AND ".join(clauses)}
                ORDER BY occurred_at DESC, id DESC{limit_sql}
                """,
            tuple(params),
        )

    # -- sources -------------------------------------------------------------

    def create_source(self, source: JsonObject, *, actor_type: str = "system") -> VNextRow:
        source_id = _new_id(source.get("id"))
        self._execute(
            """
                INSERT INTO sources (
                  id,
                  user_id,
                  source_type,
                  title,
                  author,
                  uri,
                  raw_path,
                  content_hash,
                  captured_at,
                  source_created_at,
                  source_modified_at,
                  connector_name,
                  external_id,
                  domain,
                  sensitivity,
                  metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                source_id,
                self.user_id,
                source["source_type"],
                source.get("title"),
                source.get("author"),
                source.get("uri"),
                source.get("raw_path"),
                source["content_hash"],
                _iso_or_now(source.get("captured_at")),
                _iso_or_none(source.get("source_created_at")),
                _iso_or_none(source.get("source_modified_at")),
                source.get("connector_name"),
                source.get("external_id"),
                source.get("domain", "unknown"),
                source.get("sensitivity", "unknown"),
                _json_object_text(source.get("metadata_json")),
            ),
        )
        row = self._get_row("create_source", "sources", SOURCE_COLUMNS, source_id)
        self._append_mutation_event(
            event_type="source.created",
            actor_type=actor_type,
            target_type="source",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(source)},
        )
        return row

    def get_source(self, source_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {", ".join(SOURCE_COLUMNS)}
                FROM sources
                WHERE id = ?
                  AND user_id = ?
                  AND deleted_at IS NULL
                """,
            (str(source_id), self.user_id),
        )

    def get_source_by_content_hash(self, content_hash: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {", ".join(SOURCE_COLUMNS)}
                FROM sources
                WHERE content_hash = ?
                  AND user_id = ?
                  AND deleted_at IS NULL
                ORDER BY captured_at DESC, id DESC
                LIMIT 1
                """,
            (content_hash, self.user_id),
        )

    def create_source_chunk(self, chunk: JsonObject, *, actor_type: str = "system") -> VNextRow:
        chunk_id = _new_id(chunk.get("id"))
        self._execute(
            """
                INSERT INTO source_chunks (
                  id,
                  user_id,
                  source_id,
                  chunk_index,
                  text,
                  token_count,
                  metadata_json,
                  created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                chunk_id,
                self.user_id,
                _uuid_text(chunk["source_id"]),
                chunk["chunk_index"],
                chunk["text"],
                chunk.get("token_count"),
                _json_object_text(chunk.get("metadata_json")),
                _utc_now_iso(),
            ),
        )
        row = self._get_row("create_source_chunk", "source_chunks", SOURCE_CHUNK_COLUMNS, chunk_id)
        self._append_mutation_event(
            event_type="source_chunk.created",
            actor_type=actor_type,
            target_type="source_chunk",
            target_id=row["id"],
            payload={"operation": "create", "source_id": str(row["source_id"])},
        )
        return row

    def list_source_chunks(self, source_id: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {", ".join(SOURCE_CHUNK_COLUMNS)}
                FROM source_chunks
                WHERE source_id = ?
                  AND user_id = ?
                ORDER BY chunk_index ASC, id ASC
                """,
            (str(source_id), self.user_id),
        )

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        patterns = [pattern.casefold() for pattern in _search_patterns(query)]
        exact_pattern = patterns[0]
        domain_sql, domain_params = self._domain_clause(domains)
        sensitivity_sql, sensitivity_params = self._sensitivity_clause(sensitivity_allowed)
        count = len(patterns)
        match_columns = ("title", "author", "uri", "raw_path", "content_hash", "metadata_json")
        match_sql = " OR ".join(self._like_any(column, count) for column in match_columns)
        params: list[object] = [self.user_id]
        params.extend(domain_params)
        params.extend(sensitivity_params)
        for _column in match_columns:
            params.extend(patterns)
        params.append(exact_pattern)
        params.extend(patterns)
        params.append(limit)
        return self._fetch_all(
            f"""
                SELECT {", ".join(SOURCE_COLUMNS)}
                FROM sources
                WHERE user_id = ?
                  AND deleted_at IS NULL{domain_sql}{sensitivity_sql}
                  AND ({match_sql})
                ORDER BY
                  CASE
                    WHEN LOWER(COALESCE(title, '')) LIKE ? THEN 0
                    WHEN {self._like_any("title", count)} THEN 1
                    ELSE 2
                  END,
                  captured_at DESC,
                  id DESC
                LIMIT ?
                """,
            tuple(params),
        )

    # -- memories -------------------------------------------------------------

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> VNextRow:
        memory_id = _new_id(memory.get("id"))
        now = _utc_now_iso()
        self._execute(
            """
                INSERT INTO memories (
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  title,
                  canonical_text,
                  summary,
                  domain,
                  sensitivity,
                  first_seen_at,
                  last_seen_at,
                  last_reviewed_at,
                  metadata_json,
                  commit_digest,
                  confirmation_id,
                  created_at,
                  updated_at
                )
                VALUES (
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
            (
                memory_id,
                self.user_id,
                memory.get("agent_profile_id", "assistant_default"),
                memory["memory_key"],
                _json_object_text(memory.get("value")),
                memory.get("status", "candidate"),
                _json_list_text(memory.get("source_event_ids")),
                memory.get("memory_type", "semantic"),
                memory.get("confidence"),
                memory.get("salience"),
                memory.get("confirmation_status", "unconfirmed"),
                memory.get("trust_class", "deterministic"),
                memory.get("promotion_eligibility", "promotable"),
                memory.get("evidence_count"),
                memory.get("independent_source_count"),
                memory.get("extracted_by_model"),
                memory.get("trust_reason"),
                _iso_or_none(memory.get("valid_from")),
                _iso_or_none(memory.get("valid_to")),
                _iso_or_none(memory.get("last_confirmed_at")),
                memory.get("title"),
                memory.get("canonical_text", ""),
                memory.get("summary"),
                memory.get("domain", "unknown"),
                memory.get("sensitivity", "unknown"),
                _iso_or_now(memory.get("first_seen_at")),
                _iso_or_now(memory.get("last_seen_at")),
                _iso_or_none(memory.get("last_reviewed_at")),
                _json_object_text(memory.get("metadata_json")),
                memory.get("commit_digest"),
                memory.get("confirmation_id"),
                now,
                now,
            ),
        )
        row = self._get_row("create_memory", "memories", MEMORY_COLUMNS, memory_id)
        self._append_mutation_event(
            event_type="memory.created",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(memory)},
        )
        return row

    def get_memory(self, memory_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {", ".join(MEMORY_COLUMNS)}
                FROM memories
                WHERE id = ?
                  AND user_id = ?
                  AND deleted_at IS NULL
                """,
            (str(memory_id), self.user_id),
        )

    def list_memories(self, *, status: str | None = None) -> list[VNextRow]:
        status_sql = ""
        params: list[object] = [self.user_id]
        if status is not None:
            status_sql = " AND status = ?"
            params.append(status)
        return self._fetch_all(
            f"""
                SELECT {", ".join(MEMORY_COLUMNS)}
                FROM memories
                WHERE user_id = ?{status_sql}
                  AND deleted_at IS NULL
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """,
            tuple(params),
        )

    def update_memory(self, *, memory_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        cursor = self._execute(
            """
                UPDATE memories
                SET value = COALESCE(?, value),
                    status = COALESCE(?, status),
                    source_event_ids = COALESCE(?, source_event_ids),
                    memory_type = COALESCE(?, memory_type),
                    confidence = COALESCE(?, confidence),
                    salience = COALESCE(?, salience),
                    confirmation_status = COALESCE(?, confirmation_status),
                    trust_class = COALESCE(?, trust_class),
                    promotion_eligibility = COALESCE(?, promotion_eligibility),
                    evidence_count = COALESCE(?, evidence_count),
                    independent_source_count = COALESCE(?, independent_source_count),
                    extracted_by_model = COALESCE(?, extracted_by_model),
                    trust_reason = COALESCE(?, trust_reason),
                    valid_from = COALESCE(?, valid_from),
                    valid_to = COALESCE(?, valid_to),
                    last_confirmed_at = COALESCE(?, last_confirmed_at),
                    title = COALESCE(?, title),
                    canonical_text = COALESCE(?, canonical_text),
                    summary = COALESCE(?, summary),
                    domain = COALESCE(?, domain),
                    sensitivity = COALESCE(?, sensitivity),
                    last_seen_at = COALESCE(?, last_seen_at),
                    last_reviewed_at = COALESCE(?, last_reviewed_at),
                    metadata_json = COALESCE(?, metadata_json),
                    updated_at = ?,
                    deleted_at = CASE
                      WHEN ? = 'archived' THEN ?
                      ELSE deleted_at
                    END
                WHERE id = ?
                  AND user_id = ?
                  AND deleted_at IS NULL
                """,
            (
                _json_object_text(patch["value"]) if "value" in patch else None,
                patch.get("status"),
                _json_list_text(patch["source_event_ids"]) if "source_event_ids" in patch else None,
                patch.get("memory_type"),
                patch.get("confidence"),
                patch.get("salience"),
                patch.get("confirmation_status"),
                patch.get("trust_class"),
                patch.get("promotion_eligibility"),
                patch.get("evidence_count"),
                patch.get("independent_source_count"),
                patch.get("extracted_by_model"),
                patch.get("trust_reason"),
                _iso_or_none(patch.get("valid_from")),
                _iso_or_none(patch.get("valid_to")),
                _iso_or_none(patch.get("last_confirmed_at")),
                patch.get("title"),
                patch.get("canonical_text"),
                patch.get("summary"),
                patch.get("domain"),
                patch.get("sensitivity"),
                _iso_or_none(patch.get("last_seen_at")),
                _iso_or_none(patch.get("last_reviewed_at")),
                _json_object_text(patch["metadata_json"]) if "metadata_json" in patch else None,
                _utc_now_iso(),
                patch.get("status"),
                _utc_now_iso(),
                str(memory_id),
                self.user_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ContinuityStoreInvariantError(
                "update_memory did not return a row from the database",
            )
        row = self._get_row("update_memory", "memories", MEMORY_COLUMNS, str(memory_id))
        self._append_mutation_event(
            event_type="memory.updated",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    # -- memory search ---------------------------------------------------------

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        include_expired: bool = False,
    ) -> list[VNextRow]:
        patterns = [pattern.casefold() for pattern in _search_patterns(query)]
        exact_pattern = patterns[0]
        domain_sql, domain_params = self._domain_clause(domains)
        sensitivity_sql, sensitivity_params = self._sensitivity_clause(sensitivity_allowed)
        type_sql, type_params = self._memory_type_clause(memory_types)
        project_sql, project_params = self._project_clause(projects)
        expiry_sql, expiry_params = self._expiry_clause(include_expired)
        count = len(patterns)
        match_columns = ("memory_key", "title", "canonical_text", "summary", "value")
        match_sql = " OR ".join(self._like_any(column, count) for column in match_columns)
        params: list[object] = [self.user_id]
        params.extend(domain_params)
        params.extend(sensitivity_params)
        params.extend(type_params)
        params.extend(project_params)
        params.extend(expiry_params)
        for _column in match_columns:
            params.extend(patterns)
        params.append(exact_pattern)
        params.append(exact_pattern)
        params.extend(patterns)
        params.extend(patterns)
        params.append(limit)
        return self._fetch_all(
            f"""
                SELECT {", ".join(MEMORY_COLUMNS)}
                FROM memories
                WHERE user_id = ?
                  AND deleted_at IS NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}{domain_sql}{sensitivity_sql}{type_sql}{project_sql}{expiry_sql}
                  AND ({match_sql})
                ORDER BY
                  CASE
                    WHEN LOWER(COALESCE(canonical_text, '')) LIKE ? THEN 0
                    WHEN LOWER(COALESCE(title, '')) LIKE ? THEN 1
                    WHEN {self._like_any("canonical_text", count)} THEN 2
                    WHEN {self._like_any("title", count)} THEN 3
                    ELSE 4
                  END,
                  updated_at DESC,
                  created_at DESC,
                  id DESC
                LIMIT ?
                """,
            tuple(params),
        )

    def search_memories_fts(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        include_expired: bool = False,
    ) -> list[VNextRow]:
        match_expression = _fts_match_expression(query)
        if match_expression is None:
            return []
        domain_sql, domain_params = self._domain_clause(domains, prefix="m.")
        sensitivity_sql, sensitivity_params = self._sensitivity_clause(sensitivity_allowed, prefix="m.")
        type_sql, type_params = self._memory_type_clause(memory_types, prefix="m.")
        project_sql, project_params = self._project_clause(projects, prefix="m.")
        expiry_sql, expiry_params = self._expiry_clause(include_expired, prefix="m.")
        prefixed_columns = ", ".join(f"m.{column}" for column in MEMORY_COLUMNS)
        params: list[object] = [match_expression, self.user_id]
        params.extend(domain_params)
        params.extend(sensitivity_params)
        params.extend(type_params)
        params.extend(project_params)
        params.extend(expiry_params)
        params.append(limit)
        try:
            return self._fetch_all(
                f"""
                    SELECT {prefixed_columns},
                      -bm25(memories_fts, 1.0, 0.4, 0.2, 0.4) AS fts_score
                    FROM memories_fts
                    JOIN memories m ON m.rowid = memories_fts.rowid
                    WHERE memories_fts MATCH ?
                      AND m.user_id = ?
                      AND m.deleted_at IS NULL
                      AND m.status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}{domain_sql}{sensitivity_sql}{type_sql}{project_sql}{expiry_sql}
                    ORDER BY fts_score DESC, m.updated_at DESC, m.created_at DESC, m.id DESC
                    LIMIT ?
                    """,
                tuple(params),
            )
        except sqlite3.OperationalError as exc:  # pragma: no cover - sanitizer backstop
            if "fts5" in str(exc).lower() or "syntax" in str(exc).lower():
                return []
            raise

    def search_memories_vector(
        self,
        *,
        query_vector: list[float],
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        include_expired: bool = False,
    ) -> list[VNextRow]:
        if not query_vector:
            raise ContinuityStoreInvariantError("embedding vectors must not be empty")
        padded = pad_embedding_vector(query_vector)
        query_array = np.asarray(padded, dtype=np.float32)
        query_norm = float(np.linalg.norm(query_array))
        domain_sql, domain_params = self._domain_clause(domains)
        sensitivity_sql, sensitivity_params = self._sensitivity_clause(sensitivity_allowed)
        type_sql, type_params = self._memory_type_clause(memory_types)
        project_sql, project_params = self._project_clause(projects)
        expiry_sql, expiry_params = self._expiry_clause(include_expired)
        params: list[object] = [self.user_id]
        params.extend(domain_params)
        params.extend(sensitivity_params)
        params.extend(type_params)
        params.extend(project_params)
        params.extend(expiry_params)
        candidates = self._fetch_all(
            f"""
                SELECT {", ".join(MEMORY_COLUMNS)}, embedding
                FROM memories
                WHERE user_id = ?
                  AND deleted_at IS NULL
                  AND embedding IS NOT NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}{domain_sql}{sensitivity_sql}{type_sql}{project_sql}{expiry_sql}
                """,
            tuple(params),
        )
        scored: list[VNextRow] = []
        for row in candidates:
            blob = cast(bytes, row.pop("embedding"))
            vector = np.frombuffer(blob, dtype=np.float32)
            if vector.size != EMBEDDING_VECTOR_DIMENSIONS:
                resized = np.zeros(EMBEDDING_VECTOR_DIMENSIONS, dtype=np.float32)
                resized[: min(vector.size, EMBEDDING_VECTOR_DIMENSIONS)] = vector[:EMBEDDING_VECTOR_DIMENSIONS]
                vector = resized
            vector_norm = float(np.linalg.norm(vector))
            if query_norm == 0.0 or vector_norm == 0.0:
                distance = 1.0
            else:
                similarity = float(np.dot(query_array, vector)) / (query_norm * vector_norm)
                distance = 1.0 - similarity
            row["vector_distance"] = distance
            scored.append(row)
        scored.sort(
            key=lambda item: (
                cast(float, item["vector_distance"]),
                str(item.get("updated_at") or ""),
                str(item.get("id") or ""),
            )
        )
        return scored[:limit]

    def update_memory_embedding(self, *, memory_id: str, vector: list[float]) -> VNextRow | None:
        if not vector:
            raise ContinuityStoreInvariantError("embedding vectors must not be empty")
        padded = pad_embedding_vector(vector)
        blob = np.asarray(padded, dtype=np.float32).tobytes()
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

    # -- revisions ---------------------------------------------------------------

    def append_revision(self, revision: JsonObject, *, actor_type: str = "system") -> VNextRow:
        revision_id = _new_id(revision.get("id"))
        memory_id = _uuid_text(revision["memory_id"])
        next_numbers = self._fetch_one(
            "append_revision",
            """
                SELECT
                  COALESCE(MAX(sequence_no) + 1, 1) AS next_sequence_no,
                  COALESCE(MAX(revision_number) + 1, 1) AS next_revision_number
                FROM memory_revisions
                WHERE memory_id = ?
                  AND user_id = ?
                """,
            (memory_id, self.user_id),
        )
        sequence_no = revision.get("sequence_no")
        if sequence_no is None:
            sequence_no = next_numbers["next_sequence_no"]
        revision_number = revision.get("revision_number")
        if revision_number is None:
            revision_number = next_numbers["next_revision_number"]
        self._execute(
            """
                INSERT INTO memory_revisions (
                  id,
                  user_id,
                  memory_id,
                  sequence_no,
                  action,
                  memory_key,
                  previous_value,
                  new_value,
                  source_event_ids,
                  candidate,
                  revision_number,
                  revision_type,
                  text_before,
                  text_after,
                  reason,
                  actor_type,
                  actor_id,
                  metadata_json,
                  created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                revision_id,
                self.user_id,
                memory_id,
                sequence_no,
                revision.get("action", "UPDATE"),
                revision["memory_key"],
                _json_object_text(revision["previous_value"]) if "previous_value" in revision else None,
                _json_object_text(revision.get("new_value")),
                _json_list_text(revision.get("source_event_ids")),
                _json_object_text(revision.get("candidate")),
                revision_number,
                revision.get("revision_type", "edited"),
                revision.get("text_before"),
                revision.get("text_after", ""),
                revision.get("reason"),
                revision.get("actor_type", actor_type),
                revision.get("actor_id"),
                _json_object_text(revision.get("metadata_json")),
                _utc_now_iso(),
            ),
        )
        row = self._get_row("append_revision", "memory_revisions", REVISION_COLUMNS, revision_id)
        self._append_mutation_event(
            event_type="memory_revision.created",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["memory_id"],
            payload={"operation": "create_revision", "revision_id": str(row["id"])},
        )
        return row

    def list_revisions(self, memory_id: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {", ".join(REVISION_COLUMNS)}
                FROM memory_revisions
                WHERE memory_id = ?
                  AND user_id = ?
                ORDER BY revision_number ASC, sequence_no ASC, id ASC
                """,
            (str(memory_id), self.user_id),
        )

    # -- provenance ----------------------------------------------------------------

    def create_provenance_link(self, link: JsonObject, *, actor_type: str = "system") -> VNextRow:
        link_id = _new_id(link.get("id"))
        self._execute(
            """
                INSERT INTO provenance_links (
                  id,
                  user_id,
                  target_type,
                  target_id,
                  source_id,
                  source_chunk_id,
                  quote,
                  evidence_role,
                  confidence,
                  created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                link_id,
                self.user_id,
                link["target_type"],
                link["target_id"],
                _uuid_text(link.get("source_id")),
                _uuid_text(link.get("source_chunk_id")),
                link.get("quote"),
                link.get("evidence_role", "supports"),
                link.get("confidence", 0.5),
                _utc_now_iso(),
            ),
        )
        row = self._get_row("create_provenance_link", "provenance_links", PROVENANCE_COLUMNS, link_id)
        self._append_mutation_event(
            event_type="provenance_link.created",
            actor_type=actor_type,
            target_type=str(row["target_type"]),
            target_id=str(row["target_id"]),
            payload={"operation": "create", "provenance_link_id": str(row["id"])},
        )
        return row

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {", ".join(PROVENANCE_COLUMNS)}
                FROM provenance_links
                WHERE target_type = ?
                  AND target_id = ?
                  AND user_id = ?
                ORDER BY created_at DESC, id DESC
                """,
            (target_type, target_id, self.user_id),
        )

    # -- open loops -------------------------------------------------------------------

    def create_open_loop(self, loop: JsonObject, *, actor_type: str = "system") -> VNextRow:
        loop_id = _new_id(loop.get("id"))
        now = _utc_now_iso()
        self._execute(
            """
                INSERT INTO open_loops (
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  description,
                  priority,
                  project_id,
                  person_id,
                  source_id,
                  closed_at,
                  domain,
                  sensitivity,
                  metadata_json,
                  created_at,
                  updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                loop_id,
                self.user_id,
                _uuid_text(loop.get("memory_id")),
                loop["title"],
                loop.get("status", "open"),
                _iso_or_now(loop.get("opened_at")),
                _iso_or_none(loop.get("due_at")),
                _iso_or_none(loop.get("resolved_at")),
                loop.get("resolution_note"),
                loop.get("description"),
                loop.get("priority", "normal"),
                _uuid_text(loop.get("project_id")),
                _uuid_text(loop.get("person_id")),
                _uuid_text(loop.get("source_id")),
                _iso_or_none(loop.get("closed_at")),
                loop.get("domain", "unknown"),
                loop.get("sensitivity", "unknown"),
                _json_object_text(loop.get("metadata_json")),
                now,
                now,
            ),
        )
        row = self._get_row("create_open_loop", "open_loops", OPEN_LOOP_COLUMNS, loop_id)
        self._append_mutation_event(
            event_type="open_loop.created",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(loop)},
        )
        return row

    def get_open_loop(self, loop_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {", ".join(OPEN_LOOP_COLUMNS)}
                FROM open_loops
                WHERE id = ?
                  AND user_id = ?
                """,
            (str(loop_id), self.user_id),
        )

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        project_id: str | None = None,
        person_id: str | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        domain_sql, domain_params = self._domain_clause(domains)
        sensitivity_sql, sensitivity_params = self._sensitivity_clause(sensitivity_allowed)
        clauses = ["user_id = ?"]
        params: list[object] = [self.user_id]
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        params.extend(domain_params)
        params.extend(sensitivity_params)
        extra_sql = ""
        if project_id is not None:
            extra_sql += " AND project_id = ?"
            params.append(str(project_id))
        if person_id is not None:
            extra_sql += " AND person_id = ?"
            params.append(str(person_id))
        params.append(limit)
        return self._fetch_all(
            f"""
                SELECT {", ".join(OPEN_LOOP_COLUMNS)}
                FROM open_loops
                WHERE {" AND ".join(clauses)}{domain_sql}{sensitivity_sql}{extra_sql}
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT ?
                """,
            tuple(params),
        )

    def update_open_loop(self, *, loop_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        cursor = self._execute(
            """
                UPDATE open_loops
                SET title = COALESCE(?, title),
                    description = COALESCE(?, description),
                    priority = COALESCE(?, priority),
                    due_at = COALESCE(?, due_at),
                    project_id = COALESCE(?, project_id),
                    person_id = COALESCE(?, person_id),
                    domain = COALESCE(?, domain),
                    sensitivity = COALESCE(?, sensitivity),
                    metadata_json = COALESCE(?, metadata_json),
                    updated_at = ?
                WHERE id = ?
                  AND user_id = ?
                """,
            (
                patch.get("title"),
                patch.get("description"),
                patch.get("priority"),
                _iso_or_none(patch.get("due_at")),
                _uuid_text(patch.get("project_id")),
                _uuid_text(patch.get("person_id")),
                patch.get("domain"),
                patch.get("sensitivity"),
                _json_object_text(patch["metadata_json"]) if "metadata_json" in patch else None,
                _utc_now_iso(),
                str(loop_id),
                self.user_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ContinuityStoreInvariantError(
                "update_open_loop did not return a row from the database",
            )
        row = self._get_row("update_open_loop", "open_loops", OPEN_LOOP_COLUMNS, str(loop_id))
        self._append_mutation_event(
            event_type="open_loop.updated",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def update_open_loop_status(
        self,
        *,
        loop_id: str,
        status: str,
        resolution_note: str | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        now = _utc_now_iso()
        cursor = self._execute(
            """
                UPDATE open_loops
                SET status = ?,
                    resolved_at = CASE
                      WHEN ? = 'open' THEN NULL
                      ELSE ?
                    END,
                    closed_at = CASE
                      WHEN ? = 'open' THEN NULL
                      ELSE ?
                    END,
                    resolution_note = CASE
                      WHEN ? = 'open' THEN NULL
                      ELSE ?
                    END,
                    updated_at = ?
                WHERE id = ?
                  AND user_id = ?
                """,
            (
                status,
                status,
                now,
                status,
                now,
                status,
                resolution_note,
                now,
                str(loop_id),
                self.user_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ContinuityStoreInvariantError(
                "update_open_loop_status did not return a row from the database",
            )
        row = self._get_row("update_open_loop_status", "open_loops", OPEN_LOOP_COLUMNS, str(loop_id))
        self._append_mutation_event(
            event_type="open_loop.updated",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    # -- agent identities and API keys ---------------------------------------------

    def upsert_agent_identity(self, agent: JsonObject, *, actor_type: str = "agent") -> VNextRow:
        agent_id = str(agent["agent_id"])
        agent_type = agent.get("agent_type", "unknown")
        permission_profile = agent.get("permission_profile", "read_only_agent")
        display_name = agent.get("display_name")
        project_scope = _json_list_text(agent.get("project_scope_json") or agent.get("project_scope"))
        metadata = cast(JsonObject, json_safe(agent.get("metadata_json") or {}))
        existing = self._fetch_optional_one(
            f"""
                SELECT {", ".join(AGENT_IDENTITY_COLUMNS)}
                FROM agent_identities
                WHERE user_id = ?
                  AND agent_id = ?
                """,
            (self.user_id, agent_id),
        )
        if existing is None:
            identity_id = _new_id(agent.get("id"))
            now = _utc_now_iso()
            self._execute(
                """
                    INSERT INTO agent_identities (
                      id,
                      user_id,
                      agent_id,
                      agent_type,
                      permission_profile,
                      display_name,
                      project_scope_json,
                      metadata_json,
                      created_at,
                      updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                (
                    identity_id,
                    self.user_id,
                    agent_id,
                    agent_type,
                    permission_profile,
                    display_name,
                    project_scope,
                    json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                    now,
                    now,
                ),
            )
        else:
            identity_id = str(existing["id"])
            existing_metadata = cast(dict[str, object], existing.get("metadata_json") or {})
            # Shallow merge mirrors Postgres jsonb `||` semantics.
            merged_metadata = {**existing_metadata, **metadata}
            self._execute(
                """
                    UPDATE agent_identities
                    SET agent_type = ?,
                        permission_profile = ?,
                        display_name = COALESCE(?, display_name),
                        project_scope_json = ?,
                        metadata_json = ?,
                        updated_at = ?
                    WHERE user_id = ?
                      AND agent_id = ?
                    """,
                (
                    agent_type,
                    permission_profile,
                    display_name,
                    project_scope,
                    json.dumps(merged_metadata, ensure_ascii=False, separators=(",", ":")),
                    _utc_now_iso(),
                    self.user_id,
                    agent_id,
                ),
            )
        row = self._get_row("upsert_agent_identity", "agent_identities", AGENT_IDENTITY_COLUMNS, identity_id)
        self._append_mutation_event(
            event_type="agent.identity_upserted",
            actor_type=actor_type,
            actor_id=str(row["agent_id"]),
            target_type="agent_identity",
            target_id=row["id"],
            payload={"operation": "upsert", "agent_id": str(row["agent_id"])},
        )
        return row

    def list_agent_identities(self, *, limit: int = 20) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {", ".join(AGENT_IDENTITY_COLUMNS)}
                FROM agent_identities
                WHERE user_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
            (self.user_id, limit),
        )

    def list_agent_events(self, *, agent_id: str | None = None, limit: int = 50) -> list[VNextRow]:
        clauses = ["user_id = ?", "actor_type = 'agent'"]
        params: list[object] = [self.user_id]
        if agent_id is not None:
            clauses.append("actor_id = ?")
            params.append(agent_id)
        params.append(limit)
        return self._fetch_all(
            f"""
                SELECT {", ".join(EVENT_LOG_COLUMNS)}
                FROM event_log
                WHERE {" AND ".join(clauses)}
                ORDER BY occurred_at DESC, id DESC
                LIMIT ?
                """,
            tuple(params),
        )

    def create_agent_api_key(self, key: JsonObject, *, actor_type: str = "user") -> VNextRow:
        key_id = _new_id(key.get("id"))
        self._execute(
            """
                INSERT INTO agent_api_keys (
                  id,
                  user_id,
                  agent_id,
                  permission_profile,
                  key_hash,
                  key_prefix,
                  label,
                  created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                key_id,
                self.user_id,
                key["agent_id"],
                key["permission_profile"],
                key["key_hash"],
                key["key_prefix"],
                key.get("label"),
                _utc_now_iso(),
            ),
        )
        row = self._get_row("create_agent_api_key", "agent_api_keys", AGENT_API_KEY_COLUMNS, key_id)
        self._append_mutation_event(
            event_type="agent.key_created",
            actor_type=actor_type,
            target_type="agent_api_key",
            target_id=row["id"],
            payload={
                "operation": "create",
                "agent_id": str(row["agent_id"]),
                "permission_profile": str(row["permission_profile"]),
                "key_prefix": str(row["key_prefix"]),
                "label": row.get("label"),
            },
        )
        return row

    def get_agent_api_key_by_hash(self, key_hash: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {", ".join(AGENT_API_KEY_COLUMNS)}
                FROM agent_api_keys
                WHERE key_hash = ?
                  AND user_id = ?
                """,
            (key_hash, self.user_id),
        )

    def list_agent_api_keys(self, *, limit: int = 50) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {", ".join(AGENT_API_KEY_COLUMNS)}
                FROM agent_api_keys
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
            (self.user_id, limit),
        )

    def revoke_agent_api_key(self, *, key_id: str, actor_type: str = "user") -> VNextRow | None:
        cursor = self._execute(
            """
                UPDATE agent_api_keys
                SET revoked_at = ?
                WHERE id = ?
                  AND user_id = ?
                  AND revoked_at IS NULL
                """,
            (_utc_now_iso(), str(key_id), self.user_id),
        )
        if cursor.rowcount == 0:
            return None
        row = self._get_row("revoke_agent_api_key", "agent_api_keys", AGENT_API_KEY_COLUMNS, str(key_id))
        self._append_mutation_event(
            event_type="agent.key_revoked",
            actor_type=actor_type,
            target_type="agent_api_key",
            target_id=row["id"],
            payload={
                "operation": "revoke",
                "agent_id": str(row["agent_id"]),
                "permission_profile": str(row["permission_profile"]),
                "key_prefix": str(row["key_prefix"]),
            },
        )
        return row

    def touch_agent_api_key(self, *, key_id: str) -> VNextRow:
        cursor = self._execute(
            """
                UPDATE agent_api_keys
                SET last_used_at = ?
                WHERE id = ?
                  AND user_id = ?
                """,
            (_utc_now_iso(), str(key_id), self.user_id),
        )
        if cursor.rowcount == 0:
            raise ContinuityStoreInvariantError(
                "touch_agent_api_key did not return a row from the database",
            )
        return self._get_row("touch_agent_api_key", "agent_api_keys", AGENT_API_KEY_COLUMNS, str(key_id))

    def count_active_agent_api_keys(self) -> int:
        row = self._fetch_one(
            "count_active_agent_api_keys",
            """
                SELECT count(*) AS active_count
                FROM agent_api_keys
                WHERE revoked_at IS NULL
                  AND user_id = ?
                """,
            (self.user_id,),
        )
        return int(cast(int, row["active_count"]))


__all__ = [
    "SQLiteVNextStore",
    "ensure_sqlite_user",
    "sqlite_user_connection",
]
