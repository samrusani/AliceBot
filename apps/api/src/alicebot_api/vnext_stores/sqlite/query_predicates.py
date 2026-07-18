"""SQLite query predicates and deterministic project-scope helpers."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Mapping
from datetime import datetime
from typing import cast

from alicebot_api.vnext_project_scope import (
    project_scope_identity,
    resolve_project_scope,
    resolve_source_metadata_project_scope,
)
from alicebot_api.vnext_stores.retrieval_common import (
    FTS_QUERY_STOPWORDS as _FTS_QUERY_STOPWORDS,
    fts_fallback_tokens,
)
from alicebot_api.vnext_stores.sqlite.primitives import _iso_or_none, _utc_now_iso

def _project_scope_value_sqlite(value: object) -> str | None:
    identity = project_scope_identity(value)
    return identity[0] if len(identity) == 1 else None


def _project_scope_identity_json_sqlite(
    metadata_json: object,
    direct_project_id: object,
) -> str:
    if isinstance(metadata_json, Mapping):
        metadata = dict(metadata_json)
    elif isinstance(metadata_json, str):
        try:
            decoded = json.loads(metadata_json)
        except (TypeError, ValueError):
            decoded = {}
        metadata = decoded if isinstance(decoded, dict) else {}
    else:
        metadata = {}
    identity = resolve_project_scope(
        {
            "metadata_json": metadata,
            "project_id": direct_project_id,
        }
    ).identity
    return json.dumps(identity, ensure_ascii=False, separators=(",", ":"))


def _source_project_scope_identity_json_sqlite(metadata_json: object) -> str:
    """Resolve the complete persisted-source scope envelope for SQLite."""

    if isinstance(metadata_json, Mapping):
        metadata = dict(metadata_json)
    elif isinstance(metadata_json, str):
        try:
            decoded = json.loads(metadata_json)
        except (TypeError, ValueError):
            decoded = {}
        metadata = decoded if isinstance(decoded, dict) else {}
    else:
        metadata = {}
    identity = resolve_source_metadata_project_scope(metadata).identity
    return json.dumps(identity, ensure_ascii=False, separators=(",", ":"))


def _ensure_project_scope_identity_sqlite(conn: sqlite3.Connection) -> None:
    """Install the deterministic project identity functions per connection."""

    cursor = conn.execute(
        """
        SELECT count(*)
        FROM pragma_function_list
        WHERE name IN (
          'alice_project_scope_value',
          'alice_project_scope_identity',
          'alice_source_project_scope_identity'
        )
        """
    )
    try:
        row = cursor.fetchone()
        if row is not None:
            count = next(iter(row.values())) if isinstance(row, Mapping) else row[0]
            if int(count) == 3:
                return
    finally:
        cursor.close()
    conn.create_function(
        "alice_project_scope_value",
        1,
        _project_scope_value_sqlite,
        deterministic=True,
    )
    conn.create_function(
        "alice_project_scope_identity",
        2,
        _project_scope_identity_json_sqlite,
        deterministic=True,
    )
    conn.create_function(
        "alice_source_project_scope_identity",
        1,
        _source_project_scope_identity_json_sqlite,
        deterministic=True,
    )


def _escape_like_literal(value: str) -> str:
    """Escape one literal substring for SQL LIKE with backslash ESCAPE."""

    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _sqlite_ascii_literal_contains_sql(value_expression: str) -> str:
    """Build SQLite's ASCII-folded, literal substring predicate."""

    return f"lower({value_expression}) LIKE '%' || lower(?) || '%' ESCAPE '\\'"


# SQLite FTS5 has no built-in English stopword filtering. Keep the
# strict MATCH builder and OR-fallback tied to retrieval_common so
# both backends agree on content-bearing tokens and safe syntax.

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


def _fts_match_any_expression(query: str) -> str | None:
    """OR-of-terms FTS5 MATCH expression for the ``match_any`` fallback pass.

    Same sanitization discipline as the strict path: only ``\\w+`` tokens
    survive and each is individually double-quoted, so FTS5 metacharacters
    cannot produce a parse error or operator injection; stopwords are
    dropped so bare question words do not match everything.
    """
    tokens = fts_fallback_tokens(query)
    if not tokens:
        return None
    return " OR ".join(f'"{token}"' for token in tokens)


# These helpers remain descriptor-compatible with their original class
# positions; the facade grafts them directly without wrappers.

@staticmethod  # type: ignore[misc]  # intentionally graft the descriptor into the facade
def _placeholders(values: list[str]) -> str:
    return ", ".join("?" for _ in values)


def _domain_clause(self, domains: list[str] | None, *, prefix: str = "") -> tuple[str, list[object]]:
    if domains is None:
        return "", []
    clause = f" AND ({prefix}domain IN ({self._placeholders(domains)}) OR {prefix}domain = 'unknown')"
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
    values: list[object] = list(project_scope_identity(projects))
    if not values:
        return "", []
    placeholders = self._placeholders(cast(list[str], values))
    clause = (
        " AND EXISTS (SELECT 1 FROM json_each("
        f"alice_project_scope_identity({prefix}metadata_json, {prefix}project_id)"
        ") AS scoped_project "
        f"WHERE CAST(scoped_project.value AS TEXT) IN ({placeholders}))"
    )
    return clause, values


def _created_by_clause(
    self,
    created_by_agent_ids: tuple[str, ...],
    *,
    prefix: str = "",
) -> tuple[str, list[object]]:
    if not created_by_agent_ids:
        return "", []
    values = list(created_by_agent_ids)
    clause = f" AND {prefix}created_by_agent_id IN ({self._placeholders(values)})"
    return clause, list(values)


@staticmethod  # type: ignore[misc]  # intentionally graft the descriptor into the facade
def _run_clause(run_id: str | None, *, prefix: str = "") -> tuple[str, list[object]]:
    if run_id is None:
        return "", []
    return f" AND {prefix}run_id = ?", [run_id]


@staticmethod  # type: ignore[misc]  # intentionally graft the descriptor into the facade
def _expiry_clause(include_expired: bool, *, prefix: str = "") -> tuple[str, list[object]]:
    """Exclude memories whose validity window has closed (valid_to < now)."""
    if include_expired:
        return "", []
    clause = f" AND ({prefix}valid_to IS NULL OR {prefix}valid_to >= ?)"
    return clause, [_utc_now_iso()]


def _retrieval_scope_clause(
    self,
    *,
    scope_thread_id: str | None = None,
    scope_task_id: str | None = None,
    scope_people: tuple[str, ...] = (),
    scope_person_memory_ids: tuple[str, ...] = (),
    scope_window_start: datetime | None = None,
    scope_window_end: datetime | None = None,
    prefix: str = "",
) -> tuple[str, list[object]]:
    """Complete people/time predicate applied before ranked LIMIT."""
    clauses: list[str] = []
    params: list[object] = []
    if scope_thread_id is not None:
        clauses.append(f" AND LOWER(TRIM(CAST(json_extract({prefix}metadata_json, '$.thread_id') AS TEXT))) = ?")
        params.append(scope_thread_id.casefold())
    if scope_task_id is not None:
        clauses.append(f" AND LOWER(TRIM(CAST(json_extract({prefix}metadata_json, '$.task_id') AS TEXT))) = ?")
        params.append(scope_task_id.casefold())
    if scope_people:
        people = list(scope_people)
        person_ids = list(scope_person_memory_ids)
        alternatives: list[str] = []
        if person_ids:
            alternatives.append(f"{prefix}id IN ({self._placeholders(person_ids)})")
            params.extend(person_ids)
        json_values = ", ".join(
            f"json_extract({prefix}metadata_json, '$.{key}')"
            for key in ("person_id", "person_ids", "person", "people", "people_ids")
        )
        alternatives.append(
            "EXISTS (SELECT 1 FROM json_tree(json_array("
            + json_values
            + ")) AS scoped_person "
            + "WHERE scoped_person.type = 'text' "
            + f"AND LOWER(TRIM(CAST(scoped_person.value AS TEXT))) IN ({self._placeholders(people)}))"
        )
        params.extend(people)
        clauses.append(" AND (" + " OR ".join(alternatives) + ")")
    if scope_window_start is not None or scope_window_end is not None:
        event_time = (
            f"COALESCE(julianday({prefix}valid_from), julianday({prefix}last_seen_at), "
            f"julianday({prefix}updated_at), julianday({prefix}first_seen_at), "
            f"julianday({prefix}created_at))"
        )
    if scope_window_start is not None:
        clauses.append(f" AND {event_time} >= julianday(?)")
        params.append(_iso_or_none(scope_window_start))
    if scope_window_end is not None:
        clauses.append(f" AND {event_time} <= julianday(?)")
        params.append(_iso_or_none(scope_window_end))
    return "".join(clauses), params


def _metadata_scope_clause(
    self,
    *,
    metadata_expression: str,
    scope_projects: tuple[str, ...] = (),
    scope_people: tuple[str, ...] = (),
    direct_project_expression: str | None = None,
    direct_person_expression: str | None = None,
    persisted_source_envelope: bool = False,
    event_time_expression: str,
    scope_window_start: datetime | None = None,
    scope_window_end: datetime | None = None,
) -> tuple[str, list[object]]:
    """Project/people/time predicate for source and open-loop reads."""

    clauses: list[str] = []
    params: list[object] = []

    def _metadata_values(keys: tuple[str, ...], values: tuple[str, ...]) -> str:
        json_values = ", ".join(f"json_extract({metadata_expression}, '$.{key}')" for key in keys)
        params.extend(values)
        return (
            "EXISTS (SELECT 1 FROM json_tree(json_array("
            + json_values
            + ")) AS scoped_value WHERE scoped_value.type = 'text' "
            + "AND LOWER(TRIM(CAST(scoped_value.value AS TEXT))) "
            + f"IN ({self._placeholders(list(values))}))"
        )

    project_identity = project_scope_identity(scope_projects)
    if project_identity:
        if persisted_source_envelope:
            project_scope_expression = f"alice_source_project_scope_identity({metadata_expression})"
        else:
            direct_project = direct_project_expression or "NULL"
            project_scope_expression = f"alice_project_scope_identity({metadata_expression}, {direct_project})"
        clauses.append(
            " AND EXISTS (SELECT 1 FROM json_each("
            f"{project_scope_expression}"
            ") AS scoped_project WHERE CAST(scoped_project.value AS TEXT) "
            f"IN ({self._placeholders(list(project_identity))}))"
        )
        params.extend(project_identity)
    if scope_people:
        alternatives = [
            _metadata_values(
                ("person_id", "person_ids", "person", "people", "people_ids"),
                scope_people,
            )
        ]
        if direct_person_expression is not None:
            insertion_index = len(params) - len(scope_people)
            alternatives.insert(
                0,
                f"LOWER(TRIM(CAST({direct_person_expression} AS TEXT))) "
                f"IN ({self._placeholders(list(scope_people))})",
            )
            params[insertion_index:insertion_index] = list(scope_people)
        clauses.append(" AND (" + " OR ".join(alternatives) + ")")
    if scope_window_start is not None:
        clauses.append(f" AND {event_time_expression} >= julianday(?)")
        params.append(_iso_or_none(scope_window_start))
    if scope_window_end is not None:
        clauses.append(f" AND {event_time_expression} <= julianday(?)")
        params.append(_iso_or_none(scope_window_end))
    return "".join(clauses), params


@staticmethod  # type: ignore[misc]  # intentionally graft the descriptor into the facade
def _like_any(column: str, pattern_count: int) -> str:
    predicate = f"LOWER(COALESCE({column}, '')) LIKE ?"
    return "(" + " OR ".join([predicate] * pattern_count) + ")"


for _query_helper in (
    _project_scope_value_sqlite,
    _project_scope_identity_json_sqlite,
    _source_project_scope_identity_json_sqlite,
    _ensure_project_scope_identity_sqlite,
    _escape_like_literal,
    _sqlite_ascii_literal_contains_sql,
    _fts_match_expression,
    _fts_match_any_expression,
):
    _query_helper.__module__ = "alicebot_api.sqlite_store"
    _query_helper.__qualname__ = _query_helper.__name__
del _query_helper


for _store_helper in (
    _domain_clause,
    _sensitivity_clause,
    _memory_type_clause,
    _project_clause,
    _created_by_clause,
    _retrieval_scope_clause,
    _metadata_scope_clause,
):
    _store_helper.__module__ = "alicebot_api.sqlite_store"
    _store_helper.__qualname__ = f"SQLiteVNextStore.{_store_helper.__name__}"
del _store_helper

for _store_descriptor in (_placeholders, _run_clause, _expiry_clause, _like_any):
    _store_descriptor.__module__ = "alicebot_api.sqlite_store"
    _store_descriptor.__qualname__ = f"SQLiteVNextStore.{_store_descriptor.__name__}"
    _store_descriptor.__func__.__module__ = "alicebot_api.sqlite_store"  # type: ignore[union-attr]
    _store_descriptor.__func__.__qualname__ = (  # type: ignore[union-attr]
        f"SQLiteVNextStore.{_store_descriptor.__name__}"
    )
del _store_descriptor
