from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from alicebot_api.db import UserConnection
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_embeddings import (
    EMBEDDING_SIGNATURE_METADATA_KEY,
    memory_embedding_signature_is_current,
)
from alicebot_api.vnext_entity_names import ENTITY_IMMUTABLE_PATCH_FIELDS, normalize_entity_name
from alicebot_api.vnext_event_log import build_event_log_record
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_project_scope import (
    canonical_memory_metadata,
    expose_memory_project_scope,
    normalize_project_scope,
)
from alicebot_api.vnext_repositories import JsonObject


JsonList = list[object]
VNextRow = dict[str, object]
MAX_SOURCE_CHUNKS_PER_READ = 501

# Statuses the memory read path returns. Everything else -- including
# 'stale' (demoted by maintenance), 'superseded', and 'rejected' -- is
# excluded-by-default from retrieval. Mirrors
# sqlite_store._MEMORY_SEARCHABLE_STATUSES_SQL; keep the two in sync.
_MEMORY_SEARCHABLE_STATUSES_SQL = "('active', 'accepted')"


def _jsonb_project_scope_values_sql(
    metadata_expression: str,
    *,
    legacy_keys: tuple[str, ...],
    project_id_expression: str | None = None,
) -> str:
    """Return one non-widening JSON array expression for project scope.

    Presence of the canonical top-level ``project_scope`` key is
    authoritative, including an explicit empty array.  Legacy nested and
    singular representations are consulted only when that key is absent.
    Malformed canonical values fail closed instead of resurrecting stale
    legacy scope.
    """

    canonical_scope = f"{metadata_expression} -> 'project_scope'"
    nested_scope = f"{metadata_expression} #> '{{agentic_memory,project_scope}}'"
    project_id_branch = ""
    if project_id_expression is not None:
        project_id_branch = f"""
  WHEN {project_id_expression} IS NOT NULL
    THEN jsonb_build_array({project_id_expression})"""
    legacy_values = ",\n      ".join(
        f"{metadata_expression} #> '{{{','.join(key.split('.'))}}}'" for key in legacy_keys
    )
    return f"""
CASE
  WHEN {metadata_expression} ? 'project_scope'
    THEN CASE
      WHEN jsonb_typeof({canonical_scope}) = 'array' THEN {canonical_scope}
      ELSE '[]'::jsonb
    END
  WHEN jsonb_typeof({nested_scope}) = 'array'
       AND jsonb_array_length({nested_scope}) > 0
    THEN {nested_scope}{project_id_branch}
  ELSE jsonb_path_query_array(
    jsonb_build_array(
      {legacy_values}
    ),
    'strict $.** ? (@.type() == "string")'
  )
END
"""


# The canonical overlap-aware scope is the top-level metadata array.  The
# nested agentic array covers early commit rows; project_id and its metadata
# predecessor remain singular legacy/index fallbacks.  CASE precedence is
# intentionally non-widening: stale lower-priority representations cannot add
# projects once a higher-priority array is present.
_MEMORY_PROJECT_SCOPE_SQL = _jsonb_project_scope_values_sql(
    "metadata_json",
    legacy_keys=("project_id",),
    project_id_expression="project_id",
)

_MEMORY_DIRECT_PEOPLE_SQL = """
EXISTS (
  SELECT 1
  FROM jsonb_path_query(
    jsonb_build_array(
      metadata_json -> 'person_id',
      metadata_json -> 'person_ids',
      metadata_json -> 'person',
      metadata_json -> 'people',
      metadata_json -> 'people_ids'
    ),
    'strict $.** ? (@.type() == "string")'
  ) AS scoped_person(value)
  WHERE lower(trim(both '"' FROM scoped_person.value::text)) = ANY(%s::text[])
)
"""

_MEMORY_SCOPE_EVENT_TIME_SQL = "COALESCE(valid_from, last_seen_at, updated_at, first_seen_at, created_at)"

_SCOPED_MEMORY_PROJECT_SQL = _jsonb_project_scope_values_sql(
    "m.metadata_json",
    legacy_keys=("project_id",),
    project_id_expression="m.project_id",
)

_SCOPED_MEMORY_DIRECT_PEOPLE_SQL = """
EXISTS (
  SELECT 1
  FROM jsonb_path_query(
    jsonb_build_array(
      m.metadata_json -> 'person_id',
      m.metadata_json -> 'person_ids',
      m.metadata_json -> 'person',
      m.metadata_json -> 'people',
      m.metadata_json -> 'people_ids'
    ),
    'strict $.** ? (@.type() == "string")'
  ) AS scoped_person(value)
  WHERE lower(trim(both '"' FROM scoped_person.value::text)) = ANY(%s::text[])
)
"""

_SCOPED_MEMORY_EVENT_TIME_SQL = "COALESCE(m.valid_from, m.last_seen_at, m.updated_at, m.first_seen_at, m.created_at)"


def _jsonb_scope_values_sql(metadata_expression: str, keys: tuple[str, ...]) -> str:
    """SQL predicate matching normalized string leaves under selected keys."""
    values = ",\n      ".join(f"{metadata_expression} #> '{{{','.join(key.split('.'))}}}'" for key in keys)
    return f"""
EXISTS (
  SELECT 1
  FROM jsonb_path_query(
    jsonb_build_array(
      {values}
    ),
    'strict $.** ? (@.type() == "string")'
  ) AS scoped_value(value)
  WHERE lower(trim(both '"' FROM scoped_value.value::text)) = ANY(%s::text[])
)
"""


_SOURCE_SCOPE_PROJECT_SQL = _jsonb_project_scope_values_sql(
    "metadata_json",
    legacy_keys=("project_id", "project", "projects"),
)
_SOURCE_SCOPE_PEOPLE_SQL = _jsonb_scope_values_sql(
    "metadata_json",
    ("person_id", "person_ids", "person", "people", "people_ids"),
)
_SOURCE_SCOPE_EVENT_TIME_SQL = """
COALESCE(
  source_created_at,
  CASE
    WHEN pg_input_is_valid(metadata_json ->> 'session_date', 'timestamptz')
    THEN (metadata_json ->> 'session_date')::timestamptz
  END,
  CASE
    WHEN pg_input_is_valid(metadata_json ->> 'event_date', 'timestamptz')
    THEN (metadata_json ->> 'event_date')::timestamptz
  END,
  CASE
    WHEN pg_input_is_valid(metadata_json ->> 'date', 'timestamptz')
    THEN (metadata_json ->> 'date')::timestamptz
  END,
  captured_at
)
"""
_ARTIFACT_SCOPE_PROJECT_SQL = _jsonb_project_scope_values_sql(
    "metadata_json",
    legacy_keys=("project_id", "project", "projects"),
)
_OPEN_LOOP_SCOPE_PROJECT_SQL = _jsonb_project_scope_values_sql(
    "metadata_json",
    legacy_keys=("project_id", "project", "projects"),
    project_id_expression="project_id",
)
_OPEN_LOOP_SCOPE_PEOPLE_SQL = _jsonb_scope_values_sql(
    "metadata_json",
    ("person_id", "person_ids", "person", "people", "people_ids"),
)
_OPEN_LOOP_SCOPE_EVENT_TIME_SQL = "COALESCE(opened_at, updated_at, created_at)"

# Exact SQL mirror of vnext_embeddings.memory_embedding_text/content_sha256:
# trim title/canonical/summary, omit blanks, and preserve the first occurrence
# when fields contain identical text.
_MEMORY_EMBEDDING_CONTENT_SHA256_SQL = """
encode(
  digest(
    concat_ws(
      E'\\n',
      NULLIF(btrim(title), ''),
      CASE
        WHEN NULLIF(btrim(canonical_text), '') IS DISTINCT FROM NULLIF(btrim(title), '')
          THEN NULLIF(btrim(canonical_text), '')
      END,
      CASE
        WHEN NULLIF(btrim(summary), '') IS DISTINCT FROM NULLIF(btrim(title), '')
         AND NULLIF(btrim(summary), '') IS DISTINCT FROM NULLIF(btrim(canonical_text), '')
          THEN NULLIF(btrim(summary), '')
      END
    ),
    'sha256'
  ),
  'hex'
)
"""

# Canonical true-redaction marker. Content columns are replaced with this
# literal (text columns) or with {"redacted": True} (JSON columns) so the
# audit skeleton proves something existed and was redacted without
# retaining what it said. Keep in lockstep with Postgres migration
# 20260706_0079 (the append-only triggers only admit marker-shaped
# updates) and with sqlite_store, which re-exports this constant.
REDACTION_MARKER = "[REDACTED]"

# JSON replacement written into redacted JSON content columns.
REDACTED_JSON_VALUE: JsonObject = {"redacted": True}

# metadata_json keys that survive memory redaction: pure structure and
# references (consolidation ids, scope pointers, run/agent attribution),
# never prose. Everything else in metadata_json is treated as
# content-bearing and dropped.
REDACTION_METADATA_STRUCTURAL_KEYS = frozenset(
    {
        "consolidation_digest",
        "project_id",
        "project_scope",
        "superseded_by",
        "supersedes",
        "source_refs",
        "run_id",
        "agent_id",
        "created_by_agent_id",
    }
)


def redacted_memory_metadata(metadata: object, *, redacted_at: str) -> JsonObject:
    """Scrub a memory's metadata_json down to structural keys.

    Keeps only ``REDACTION_METADATA_STRUCTURAL_KEYS``, then stamps the
    ``redacted`` flag and ``redacted_at`` timestamp. Shared by both store
    backends so the scrub policy cannot drift.
    """
    scrubbed: JsonObject = {}
    if isinstance(metadata, dict):
        for key in sorted(REDACTION_METADATA_STRUCTURAL_KEYS):
            if key in metadata:
                scrubbed[key] = metadata[key]
    scrubbed["redacted"] = True
    scrubbed["redacted_at"] = redacted_at
    return scrubbed


def _vector_literal(vector: list[float]) -> str:
    if not vector:
        raise ContinuityStoreInvariantError("embedding vectors must not be empty")
    values: list[float] = []
    for value in vector:
        try:
            normalized = float(value)
        except (TypeError, ValueError) as exc:
            raise ContinuityStoreInvariantError("embedding vectors must contain only numbers") from exc
        if not math.isfinite(normalized):
            raise ContinuityStoreInvariantError("embedding vectors must contain only finite numbers")
        values.append(normalized)
    return "[" + ",".join(repr(value) for value in values) + "]"


def _search_patterns(query: str) -> list[str]:
    """LIKE/ILIKE patterns for the keyword-fallback search paths.

    The full normalized phrase always leads (exact matches rank first);
    per-term fallback patterns are added for every token that is not an
    ``FTS_QUERY_STOPWORDS`` member, so the LIKE paths drop the same
    question words the FTS paths drop instead of matching every row that
    contains e.g. "about" or "your".
    """
    normalized = " ".join(str(query).split()).strip()
    if len(normalized) >= 2 and (
        (normalized[0] == normalized[-1] and normalized[0] in {"'", '"'})
        or (normalized[0], normalized[-1]) in {("\u201c", "\u201d"), ("\u2018", "\u2019")}
    ):
        normalized = normalized[1:-1].strip()

    patterns: list[str] = []
    if normalized:
        patterns.append(f"%{normalized}%")
    seen = {pattern.casefold() for pattern in patterns}
    for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", normalized):
        folded = term.casefold()
        if folded in FTS_QUERY_STOPWORDS:
            continue
        pattern = f"%{folded}%"
        if pattern.casefold() not in seen:
            patterns.append(pattern)
            seen.add(pattern.casefold())
    return patterns or ["%%"]


# The snowball English stopword list -- the same list the Postgres
# 'english' text-search configuration applies inside websearch_to_tsquery()
# and to_tsquery(). Shared with sqlite_store (whose FTS5 MATCH builder
# re-imports it -- FTS5 has no stopword support of its own), with the
# retrieval service's OR-fallback trigger, and with ``_search_patterns``
# above (the LIKE keyword fallback), so every query path agrees on what
# counts as a content-bearing token.
FTS_QUERY_STOPWORDS = frozenset(
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


def fts_fallback_tokens(query: str) -> list[str]:
    """Sanitized non-stopword tokens for the OR-fallback FTS pass.

    ``\\w+`` extraction strips every tsquery/FTS5 metacharacter (quotes,
    ``& | ! ( ) : * -`` and friends), so no user input can inject query
    syntax on either backend.
    """
    return [token for token in re.findall(r"\w+", str(query)) if token.casefold() not in FTS_QUERY_STOPWORDS]


def _tsquery_any_expression(query: str) -> str | None:
    """OR-of-lexemes tsquery text for the ``match_any`` fallback pass.

    Each ``\\w+`` token is individually single-quoted so Postgres parses it
    as one literal lexeme; ``to_tsquery('english', ...)`` then stems it the
    same way the strict ``websearch_to_tsquery()`` pass does.
    """
    tokens = fts_fallback_tokens(query)
    if not tokens:
        return None
    return " | ".join(f"'{token}'" for token in tokens)


EVENT_LOG_COLUMNS = """
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
                """

CONNECTOR_SETTINGS_COLUMNS = """
                  id,
                  user_id,
                  connector_name,
                  enabled,
                  configured,
                  default_domain,
                  default_sensitivity,
                  sync_mode,
                  poll_interval_seconds,
                  secret_ref,
                  validation_errors_json,
                  metadata_json,
                  created_at,
                  updated_at,
                  last_configured_at
                """

CONNECTOR_STATE_COLUMNS = """
                  id,
                  user_id,
                  connector_id,
                  connector_name,
                  cursor_type,
                  cursor_value,
                  last_sync_at,
                  last_success_at,
                  last_failure_at,
                  last_error,
                  items_seen,
                  items_captured,
                  items_deduped,
                  items_failed,
                  average_processing_time_ms,
                  state_json,
                  updated_at
                """

SOURCE_COLUMNS = """
                  id,
                  user_id,
                  source_type,
                  title,
                  author,
                  uri,
                  raw_path,
                  content_hash,
                  dedupe_key,
                  captured_at,
                  source_created_at,
                  source_modified_at,
                  connector_name,
                  external_id,
                  domain,
                  sensitivity,
                  metadata_json,
                  deleted_at
                """

SOURCE_CHUNK_COLUMNS = """
                  id,
                  user_id,
                  source_id,
                  chunk_index,
                  text,
                  token_count,
                  metadata_json,
                  created_at
                """

# c.-prefixed chunk columns for search_source_chunks, whose JOIN to
# sources would otherwise make id/user_id/metadata_json/created_at
# ambiguous.
_SOURCE_CHUNK_SEARCH_COLUMNS = ", ".join(f"c.{column.strip()}" for column in SOURCE_CHUNK_COLUMNS.split(","))

MEMORY_COLUMNS = """
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
                  project_id,
                  created_by_agent_id,
                  run_id,
                  superseded_by,
                  supersedes,
                  created_at,
                  updated_at,
                  deleted_at
                """

REVISION_COLUMNS = """
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
                """

PROVENANCE_COLUMNS = """
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
                """

GRAPH_EDGE_COLUMNS = """
                  id,
                  user_id,
                  from_type,
                  from_id,
                  to_type,
                  to_id,
                  edge_type,
                  confidence,
                  explanation,
                  created_by,
                  created_at,
                  observed_at,
                  valid_from,
                  valid_to,
                  metadata_json
                """

PROJECT_COLUMNS = """
                  id,
                  user_id,
                  name,
                  slug,
                  status,
                  description,
                  current_state,
                  domain,
                  sensitivity,
                  created_at,
                  updated_at,
                  metadata_json
                """

PERSON_COLUMNS = """
                  id,
                  user_id,
                  name,
                  aliases_json,
                  relationship_type,
                  organization,
                  sensitivity,
                  notes,
                  created_at,
                  updated_at,
                  metadata_json
                """

ENTITY_COLUMNS = """
                  id,
                  user_id,
                  entity_type,
                  name,
                  normalized_name,
                  aliases,
                  metadata_json,
                  created_at,
                  updated_at,
                  deleted_at,
                  first_observed_at,
                  last_observed_at,
                  mention_count
                """

ENTITY_RELATIONSHIP_EVENT_COLUMNS = """
                  id,
                  user_id,
                  entity_id,
                  relationship_type_before,
                  relationship_type_after,
                  changed_at,
                  source_id,
                  metadata_json
                """

BELIEF_COLUMNS = """
                  id,
                  user_id,
                  memory_id,
                  claim,
                  status,
                  confidence,
                  first_seen_at,
                  last_reinforced_at,
                  last_challenged_at,
                  superseded_by,
                  metadata_json
                """

OPEN_LOOP_COLUMNS = """
                  id,
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at,
                  description,
                  priority,
                  project_id,
                  person_id,
                  source_id,
                  closed_at,
                  domain,
                  sensitivity,
                  metadata_json
                """

ARTIFACT_COLUMNS = """
                  id,
                  user_id,
                  artifact_type,
                  title,
                  content_markdown,
                  status,
                  domain,
                  sensitivity,
                  generated_by,
                  prompt_hash,
                  model_info_json,
                  created_at,
                  reviewed_at,
                  promoted_at,
                  metadata_json
                """

QUALITY_RATING_COLUMNS = """
                  id,
                  user_id,
                  artifact_id,
                  reviewer_id,
                  usefulness,
                  accuracy,
                  source_grounding,
                  novel_connections,
                  actionability,
                  hallucination_risk,
                  verbosity,
                  missed_context,
                  comments,
                  created_at,
                  metadata_json
                """

TASK_COLUMNS = """
                  id,
                  user_id,
                  title,
                  task_type,
                  instructions,
                  status,
                  requested_by,
                  scope_json,
                  allowed_sources_json,
                  domain,
                  sensitivity,
                  write_policy,
                  scheduled_for,
                  started_at,
                  completed_at,
                  failed_at,
                  error_message,
                  output_artifact_id,
                  created_at,
                  updated_at,
                  metadata_json
                """

BRAIN_CHARTER_COLUMNS = """
                  id,
                  user_id,
                  content_markdown,
                  owner_json,
                  memory_philosophy_json,
                  life_domains_json,
                  active_projects_json,
                  communication_style_json,
                  priorities_json,
                  autonomous_rules_json,
                  quality_standard_json,
                  sensitivity,
                  created_at,
                  updated_at
                """

AGENT_IDENTITY_COLUMNS = """
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
                """

AGENT_API_KEY_COLUMNS = """
                  id,
                  user_id,
                  agent_id,
                  permission_profile,
                  project_scope,
                  key_hash,
                  key_prefix,
                  label,
                  created_at,
                  revoked_at,
                  last_used_at
                """

SCHEDULER_WORKFLOW_COLUMNS = """
                  id,
                  user_id,
                  workflow_type,
                  enabled,
                  paused,
                  schedule_json,
                  timezone,
                  next_run_at,
                  last_run_id,
                  last_run_at,
                  last_result,
                  last_error,
                  claim_token,
                  claim_version,
                  claim_expires_at,
                  created_at,
                  updated_at,
                  metadata_json
                """

SCHEDULER_RUN_COLUMNS = """
                  id,
                  user_id,
                  workflow_id,
                  workflow_type,
                  status,
                  triggered_by,
                  trace_id,
                  started_at,
                  finished_at,
                  artifact_id,
                  error_message,
                  claim_token,
                  claim_version,
                  claim_expires_at,
                  scheduled_for,
                  policy_decision_json,
                  agent_identity_json,
                  metadata_json
                """


def _json_object(value: object | None) -> Jsonb:
    if value is None:
        value = {}
    return Jsonb(_json_safe(value))


def _json_list(value: object | None) -> Jsonb:
    if value is None:
        value = []
    return Jsonb(_json_safe(value))


def _json_safe(value: object) -> object:
    return json_safe(value)


def _sorted_field_names(record: JsonObject) -> list[str]:
    return sorted(str(key) for key in record)


class PostgresVNextStore:
    """SQL-backed vNext repository facade for the second-brain kernel."""

    def __init__(self, conn: UserConnection):
        self.conn = conn

    def _fetch_one(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> VNextRow:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )

        return expose_memory_project_scope(cast(VNextRow, row))

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> VNextRow | None:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        if row is None:
            return None
        return expose_memory_project_scope(cast(VNextRow, row))

    def _fetch_all(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> list[VNextRow]:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [expose_memory_project_scope(cast(VNextRow, row)) for row in rows]

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
                payload=cast(JsonObject, _json_safe(payload)),
                trace_id=trace_id,
                run_id=run_id,
            )
        )

    def append_event(self, event: JsonObject) -> VNextRow:
        return self._fetch_one(
            "append_event",
            f"""
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
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {EVENT_LOG_COLUMNS}
                """,
            (
                event.get("id"),
                event["event_type"],
                event["actor_type"],
                event.get("actor_id"),
                event.get("target_type"),
                event.get("target_id"),
                event.get("occurred_at"),
                _json_object(event.get("payload_json")),
                event.get("trace_id"),
                event.get("run_id"),
                event.get("integrity_hash"),
            ),
        )

    def list_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int | None = None,
    ) -> list[VNextRow]:
        if target_type is None and target_id is None:
            if limit is not None:
                return self._fetch_all(
                    f"""
                    SELECT {EVENT_LOG_COLUMNS}
                    FROM event_log
                    ORDER BY occurred_at DESC, id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            return self._fetch_all(
                f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                ORDER BY occurred_at DESC, id DESC
                """
            )
        if limit is not None:
            return self._fetch_all(
                f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                WHERE (%s::text IS NULL OR target_type = %s)
                  AND (%s::text IS NULL OR target_id = %s)
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
                (target_type, target_type, target_id, target_id, limit),
            )
        return self._fetch_all(
            f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                WHERE (%s::text IS NULL OR target_type = %s)
                  AND (%s::text IS NULL OR target_id = %s)
                ORDER BY occurred_at DESC, id DESC
            """,
            (target_type, target_type, target_id, target_id),
        )

    def list_events_for_source_trace(
        self,
        *,
        source_id: str,
        memory_ids: Sequence[str] = (),
        artifact_ids: Sequence[str] = (),
        open_loop_ids: Sequence[str] = (),
        limit: int = 500,
    ) -> list[VNextRow]:
        """Bound source-trace events with relationship predicates before LIMIT."""

        if limit < 1:
            raise ValueError("limit must be positive")
        memories = list(dict.fromkeys(str(value) for value in memory_ids if value)) or None
        artifacts = list(dict.fromkeys(str(value) for value in artifact_ids if value)) or None
        open_loops = list(dict.fromkeys(str(value) for value in open_loop_ids if value)) or None
        source_ref = f"source:{source_id}"
        return self._fetch_all(
            f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                WHERE (
                  (target_type = 'source' AND target_id = %s)
                  OR (%s::text[] IS NOT NULL AND target_type = 'memory' AND target_id = ANY(%s::text[]))
                  OR (%s::text[] IS NOT NULL AND target_type = 'artifact' AND target_id = ANY(%s::text[]))
                  OR (%s::text[] IS NOT NULL AND target_type = 'open_loop' AND target_id = ANY(%s::text[]))
                  OR payload_json ->> 'source_id' = %s
                  OR payload_json ->> 'source_ref' IN (%s, %s)
                  OR payload_json -> 'source_ids' ? %s
                  OR payload_json -> 'source_refs' ? %s
                  OR payload_json -> 'source_refs' ? %s
                  OR payload_json -> 'source_references' ? %s
                  OR payload_json -> 'source_references' ? %s
                  OR payload_json -> 'selected_source_ids' ? %s
                )
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
            (
                source_id,
                memories,
                memories,
                artifacts,
                artifacts,
                open_loops,
                open_loops,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_ref,
                source_id,
                limit,
            ),
        )

    def list_memory_events(
        self,
        *,
        event_type_prefix: str | None = None,
        scope_projects: tuple[str, ...] = (),
        scope_people: tuple[str, ...] = (),
        scope_person_memory_ids: tuple[str, ...] = (),
        scope_window_start: datetime | None = None,
        scope_window_end: datetime | None = None,
        limit: int = 20,
    ) -> list[VNextRow]:
        """Return memory-targeted events with target scope applied pre-LIMIT."""
        if limit < 1:
            raise ValueError("limit must be positive")
        project_list = list(normalize_project_scope(scope_projects)) or None
        people_list = [str(value).strip().casefold() for value in scope_people if str(value).strip()] or None
        person_memory_ids = [str(value) for value in scope_person_memory_ids if str(value)] or None
        prefix_pattern = f"{event_type_prefix}%" if event_type_prefix is not None else None
        return self._fetch_all(
            f"""
                SELECT
                  e.id,
                  e.user_id,
                  e.event_type,
                  e.actor_type,
                  e.actor_id,
                  e.target_type,
                  e.target_id,
                  e.occurred_at,
                  e.payload_json,
                  e.trace_id,
                  e.run_id,
                  e.integrity_hash
                FROM event_log e
                JOIN memories m
                  ON e.target_type = 'memory'
                 AND e.target_id = m.id::text
                 AND e.user_id = m.user_id
                WHERE m.deleted_at IS NULL
                  AND (%s::text IS NULL OR e.event_type LIKE %s)
                  AND (%s::text[] IS NULL OR ({_SCOPED_MEMORY_PROJECT_SQL}) ?| %s::text[])
                  AND (
                    %s::text[] IS NULL
                    OR m.id::text = ANY(%s::text[])
                    OR {_SCOPED_MEMORY_DIRECT_PEOPLE_SQL}
                  )
                  AND (%s::timestamptz IS NULL OR e.occurred_at >= %s::timestamptz)
                  AND (%s::timestamptz IS NULL OR e.occurred_at <= %s::timestamptz)
                ORDER BY e.occurred_at DESC, e.id DESC
                LIMIT %s
                """,
            (
                prefix_pattern,
                prefix_pattern,
                project_list,
                project_list,
                people_list,
                person_memory_ids,
                people_list,
                scope_window_start,
                scope_window_start,
                scope_window_end,
                scope_window_end,
                limit,
            ),
        )

    def count_events(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
    ) -> int:
        """Count matching event rows without materializing the append-only log."""
        row = self._fetch_one(
            "count events",
            """
                SELECT COUNT(*)::bigint AS count
                FROM event_log
                WHERE (%s::text IS NULL OR target_type = %s)
                  AND (%s::text IS NULL OR target_id = %s)
                """,
            (target_type, target_type, target_id, target_id),
        )
        return int(cast(int, row["count"]))

    def count_sources(self) -> int:
        row = self._fetch_one("count sources", "SELECT COUNT(*)::bigint AS count FROM sources WHERE deleted_at IS NULL")
        return int(cast(int, row["count"]))

    def count_artifacts(self) -> int:
        row = self._fetch_one("count artifacts", "SELECT COUNT(*)::bigint AS count FROM generated_artifacts")
        return int(cast(int, row["count"]))

    def count_artifacts_by_status(self) -> dict[str, int]:
        rows = self._fetch_all(
            "SELECT status, COUNT(*)::bigint AS count FROM generated_artifacts GROUP BY status ORDER BY status"
        )
        return {str(row["status"]): int(cast(int, row["count"])) for row in rows}

    def count_artifact_quality_ratings(self) -> int:
        row = self._fetch_one(
            "count artifact quality ratings",
            "SELECT COUNT(*)::bigint AS count FROM artifact_quality_ratings",
        )
        return int(cast(int, row["count"]))

    def count_projects(self) -> int:
        row = self._fetch_one("count projects", "SELECT COUNT(*)::bigint AS count FROM projects")
        return int(cast(int, row["count"]))

    def count_open_loops(self, *, status: str | None = None) -> int:
        row = self._fetch_one(
            "count open loops",
            "SELECT COUNT(*)::bigint AS count FROM open_loops WHERE (%s::text IS NULL OR status = %s)",
            (status, status),
        )
        return int(cast(int, row["count"]))

    def count_open_loops_by_status(self) -> dict[str, int]:
        rows = self._fetch_all(
            "SELECT status, COUNT(*)::bigint AS count FROM open_loops GROUP BY status ORDER BY status"
        )
        return {str(row["status"]): int(cast(int, row["count"])) for row in rows}

    def count_agent_identities(self) -> int:
        row = self._fetch_one(
            "count agent identities",
            "SELECT COUNT(*)::bigint AS count FROM agent_identities",
        )
        return int(cast(int, row["count"]))

    def list_connector_settings(self) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {CONNECTOR_SETTINGS_COLUMNS}
                FROM connector_settings
                ORDER BY connector_name ASC
            """
        )

    def get_connector_setting(self, connector_name: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {CONNECTOR_SETTINGS_COLUMNS}
                FROM connector_settings
                WHERE connector_name = %s
                """,
            (connector_name,),
        )

    def upsert_connector_setting(self, setting: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "upsert_connector_setting",
            f"""
                INSERT INTO connector_settings (
                  user_id,
                  connector_name,
                  enabled,
                  configured,
                  default_domain,
                  default_sensitivity,
                  sync_mode,
                  poll_interval_seconds,
                  secret_ref,
                  validation_errors_json,
                  metadata_json,
                  last_configured_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  COALESCE(%s, false),
                  COALESCE(%s, false),
                  %s,
                  %s,
                  COALESCE(%s, 'manual'),
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp())
                )
                ON CONFLICT (user_id, connector_name)
                DO UPDATE SET
                  enabled = EXCLUDED.enabled,
                  configured = EXCLUDED.configured,
                  default_domain = EXCLUDED.default_domain,
                  default_sensitivity = EXCLUDED.default_sensitivity,
                  sync_mode = EXCLUDED.sync_mode,
                  poll_interval_seconds = EXCLUDED.poll_interval_seconds,
                  secret_ref = COALESCE(EXCLUDED.secret_ref, connector_settings.secret_ref),
                  validation_errors_json = EXCLUDED.validation_errors_json,
                  metadata_json = connector_settings.metadata_json || EXCLUDED.metadata_json,
                  updated_at = clock_timestamp(),
                  last_configured_at = EXCLUDED.last_configured_at
                RETURNING {CONNECTOR_SETTINGS_COLUMNS}
                """,
            (
                setting["connector_name"],
                setting.get("enabled"),
                setting.get("configured"),
                setting["default_domain"],
                setting["default_sensitivity"],
                setting.get("sync_mode", "manual"),
                setting.get("poll_interval_seconds"),
                setting.get("secret_ref"),
                _json_list(setting.get("validation_errors_json")),
                _json_object(setting.get("metadata_json")),
                setting.get("last_configured_at"),
            ),
        )
        self._append_mutation_event(
            event_type="connector.settings_updated",
            actor_type=actor_type,
            target_type="connector",
            target_id=row["connector_name"],
            payload={
                "connector_id": row["id"],
                "connector_name": row["connector_name"],
                "enabled": row["enabled"],
                "configured": row["configured"],
                "default_domain": row["default_domain"],
                "default_sensitivity": row["default_sensitivity"],
                "sync_mode": row["sync_mode"],
                "poll_interval_seconds": row["poll_interval_seconds"],
                "secret_ref": row["secret_ref"],
                "validation_errors_json": row["validation_errors_json"],
            },
        )
        return row

    def list_connector_states(self) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {CONNECTOR_STATE_COLUMNS}
                FROM connector_state
                ORDER BY connector_name ASC, cursor_type ASC
            """
        )

    def get_connector_state(self, connector_name: str, *, cursor_type: str = "sync_cursor") -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {CONNECTOR_STATE_COLUMNS}
                FROM connector_state
                WHERE connector_name = %s
                  AND cursor_type = %s
                """,
            (connector_name, cursor_type),
        )

    def upsert_connector_state(self, state: JsonObject, *, actor_type: str = "system") -> VNextRow:
        connector_name = str(state["connector_name"])
        cursor_type = str(state.get("cursor_type") or "sync_cursor")
        row = self._fetch_one(
            "upsert_connector_state",
            f"""
                INSERT INTO connector_state (
                  user_id,
                  connector_id,
                  connector_name,
                  cursor_type,
                  cursor_value,
                  last_sync_at,
                  last_success_at,
                  last_failure_at,
                  last_error,
                  items_seen,
                  items_captured,
                  items_deduped,
                  items_failed,
                  average_processing_time_ms,
                  state_json
                )
                VALUES (
                  app.current_user_id(),
                  (
                    SELECT id
                    FROM connector_settings
                    WHERE user_id = app.current_user_id()
                      AND connector_name = %s
                    LIMIT 1
                  ),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s, 0),
                  COALESCE(%s, 0),
                  COALESCE(%s, 0),
                  COALESCE(%s, 0),
                  %s,
                  %s
                )
                ON CONFLICT (user_id, connector_name, cursor_type)
                DO UPDATE SET
                  connector_id = COALESCE(connector_state.connector_id, EXCLUDED.connector_id),
                  cursor_value = COALESCE(EXCLUDED.cursor_value, connector_state.cursor_value),
                  last_sync_at = COALESCE(EXCLUDED.last_sync_at, connector_state.last_sync_at),
                  last_success_at = COALESCE(EXCLUDED.last_success_at, connector_state.last_success_at),
                  last_failure_at = COALESCE(EXCLUDED.last_failure_at, connector_state.last_failure_at),
                  last_error = EXCLUDED.last_error,
                  items_seen = connector_state.items_seen + EXCLUDED.items_seen,
                  items_captured = connector_state.items_captured + EXCLUDED.items_captured,
                  items_deduped = connector_state.items_deduped + EXCLUDED.items_deduped,
                  items_failed = connector_state.items_failed + EXCLUDED.items_failed,
                  average_processing_time_ms = COALESCE(
                    EXCLUDED.average_processing_time_ms,
                    connector_state.average_processing_time_ms
                  ),
                  state_json = connector_state.state_json || EXCLUDED.state_json,
                  updated_at = clock_timestamp()
                RETURNING {CONNECTOR_STATE_COLUMNS}
                """,
            (
                connector_name,
                connector_name,
                cursor_type,
                state.get("cursor_value"),
                state.get("last_sync_at"),
                state.get("last_success_at"),
                state.get("last_failure_at"),
                state.get("last_error"),
                state.get("items_seen_delta", state.get("items_seen", 0)),
                state.get("items_captured_delta", state.get("items_captured", 0)),
                state.get("items_deduped_delta", state.get("items_deduped", 0)),
                state.get("items_failed_delta", state.get("items_failed", 0)),
                state.get("average_processing_time_ms"),
                _json_object(state.get("state_json")),
            ),
        )
        self._append_mutation_event(
            event_type="connector.state_updated",
            actor_type=actor_type,
            target_type="connector",
            target_id=row["connector_name"],
            payload={
                "connector_id": row["connector_id"],
                "connector_name": row["connector_name"],
                "cursor_type": row["cursor_type"],
                "cursor_value": row["cursor_value"],
                "last_sync_at": row["last_sync_at"],
                "last_success_at": row["last_success_at"],
                "last_failure_at": row["last_failure_at"],
                "items_seen": row["items_seen"],
                "items_captured": row["items_captured"],
                "items_deduped": row["items_deduped"],
                "items_failed": row["items_failed"],
            },
        )
        return row

    def connector_storage_status(self) -> VNextRow:
        return self._fetch_one(
            "connector_storage_status",
            """
                SELECT
                  to_regclass('public.connector_settings') IS NOT NULL AS connector_settings_exists,
                  to_regclass('public.connector_state') IS NOT NULL AS connector_state_exists,
                  to_regclass('public.artifact_quality_ratings') IS NOT NULL AS artifact_quality_ratings_exists,
                  to_regclass('public.scheduler_workflows') IS NOT NULL AS scheduler_workflows_exists,
                  to_regclass('public.scheduler_runs') IS NOT NULL AS scheduler_runs_exists,
                  (SELECT extversion FROM pg_extension WHERE extname = 'vector') AS pgvector_version,
                  NULL::text AS migration_revision
                """,
        )

    def list_sources(
        self,
        *,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 20,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE deleted_at IS NULL
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                ORDER BY captured_at DESC, id DESC
                LIMIT %s
                """,
            (domains, domains, sensitivity_allowed, sensitivity_allowed, limit),
        )

    def create_source(self, source: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_source",
            f"""
                INSERT INTO sources (
                  id,
                  user_id,
                  source_type,
                  title,
                  author,
                  uri,
                  raw_path,
                  content_hash,
                  dedupe_key,
                  captured_at,
                  source_created_at,
                  source_modified_at,
                  connector_name,
                  external_id,
                  domain,
                  sensitivity,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {SOURCE_COLUMNS}
                """,
            (
                source.get("id"),
                source["source_type"],
                source.get("title"),
                source.get("author"),
                source.get("uri"),
                source.get("raw_path"),
                source["content_hash"],
                source.get("dedupe_key", source["content_hash"]),
                source.get("captured_at"),
                source.get("source_created_at"),
                source.get("source_modified_at"),
                source.get("connector_name"),
                source.get("external_id"),
                source.get("domain", "unknown"),
                source.get("sensitivity", "unknown"),
                _json_object(source.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="source.created",
            actor_type=actor_type,
            target_type="source",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(source)},
        )
        return row

    def get_or_create_source(
        self,
        source: JsonObject,
        *,
        actor_type: str = "system",
    ) -> tuple[VNextRow, bool]:
        """Atomically claim one live capture identity and return its source."""
        dedupe_key = str(source.get("dedupe_key") or source["content_hash"])
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                    INSERT INTO sources (
                      id, user_id, source_type, title, author, uri, raw_path,
                      content_hash, dedupe_key, captured_at, source_created_at,
                      source_modified_at, connector_name, external_id, domain,
                      sensitivity, metadata_json
                    )
                    VALUES (
                      COALESCE(%s::uuid, gen_random_uuid()), app.current_user_id(),
                      %s, %s, %s, %s, %s, %s, %s,
                      COALESCE(%s::timestamptz, clock_timestamp()),
                      %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (user_id, dedupe_key)
                      WHERE deleted_at IS NULL AND dedupe_key IS NOT NULL
                    DO NOTHING
                    RETURNING {SOURCE_COLUMNS}
                    """,
                (
                    source.get("id"),
                    source["source_type"],
                    source.get("title"),
                    source.get("author"),
                    source.get("uri"),
                    source.get("raw_path"),
                    source["content_hash"],
                    dedupe_key,
                    source.get("captured_at"),
                    source.get("source_created_at"),
                    source.get("source_modified_at"),
                    source.get("connector_name"),
                    source.get("external_id"),
                    source.get("domain", "unknown"),
                    source.get("sensitivity", "unknown"),
                    _json_object(source.get("metadata_json")),
                ),
            )
            raw_row = cur.fetchone()
            created = raw_row is not None
            if raw_row is None:
                cur.execute(
                    f"""
                        SELECT {SOURCE_COLUMNS}
                        FROM sources
                        WHERE dedupe_key = %s
                          AND deleted_at IS NULL
                        ORDER BY captured_at DESC, id DESC
                        LIMIT 1
                        """,
                    (dedupe_key,),
                )
                raw_row = cur.fetchone()
        if raw_row is None:  # pragma: no cover - unique-index invariant backstop
            raise ContinuityStoreInvariantError("get_or_create_source did not return a source")
        row = cast(VNextRow, raw_row)
        if created:
            self._append_mutation_event(
                event_type="source.created",
                actor_type=actor_type,
                target_type="source",
                target_id=row["id"],
                payload={"operation": "create", "fields": _sorted_field_names(source)},
            )
        return row, created

    def get_source(self, source_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                """,
            (source_id,),
        )

    def get_sources_by_ids(self, source_ids: Sequence[str]) -> list[VNextRow]:
        ids = list(dict.fromkeys(str(source_id) for source_id in source_ids if source_id))
        if not ids:
            return []
        return self._fetch_all(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE deleted_at IS NULL
                  AND id = ANY(%s::uuid[])
                """,
            (ids,),
        )

    def get_source_by_content_hash(self, content_hash: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE content_hash = %s
                  AND deleted_at IS NULL
                ORDER BY captured_at DESC, id DESC
                LIMIT 1
                """,
            (content_hash,),
        )

    def get_sources_by_content_hash(self, content_hash: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE content_hash = %s
                  AND deleted_at IS NULL
                ORDER BY captured_at DESC, id DESC
                """,
            (content_hash,),
        )

    def get_source_by_dedupe_key(self, dedupe_key: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE dedupe_key = %s
                  AND deleted_at IS NULL
                ORDER BY captured_at DESC, id DESC
                LIMIT 1
                """,
            (dedupe_key,),
        )

    def update_source(self, *, source_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_source",
            f"""
                UPDATE sources
                SET title = COALESCE(%s, title),
                    author = COALESCE(%s, author),
                    uri = COALESCE(%s, uri),
                    raw_path = COALESCE(%s, raw_path),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    metadata_json = COALESCE(%s, metadata_json)
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {SOURCE_COLUMNS}
                """,
            (
                patch.get("title"),
                patch.get("author"),
                patch.get("uri"),
                patch.get("raw_path"),
                patch.get("domain"),
                patch.get("sensitivity"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                source_id,
            ),
        )
        self._append_mutation_event(
            event_type="source.updated",
            actor_type=actor_type,
            target_type="source",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def delete_source(self, *, source_id: str, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "delete_source",
            f"""
                UPDATE sources
                SET deleted_at = clock_timestamp()
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {SOURCE_COLUMNS}
                """,
            (source_id,),
        )
        self._append_mutation_event(
            event_type="source.deleted",
            actor_type=actor_type,
            target_type="source",
            target_id=row["id"],
            payload={"operation": "delete"},
        )
        return row

    def create_source_chunk(self, chunk: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_source_chunk",
            f"""
                INSERT INTO source_chunks (
                  id,
                  user_id,
                  source_id,
                  chunk_index,
                  text,
                  token_count,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {SOURCE_CHUNK_COLUMNS}
                """,
            (
                chunk.get("id"),
                chunk["source_id"],
                chunk["chunk_index"],
                chunk["text"],
                chunk.get("token_count"),
                _json_object(chunk.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="source_chunk.created",
            actor_type=actor_type,
            target_type="source_chunk",
            target_id=row["id"],
            payload={"operation": "create", "source_id": str(row["source_id"])},
        )
        return row

    def list_source_chunks(self, source_id: str, *, limit: int = 500) -> list[VNextRow]:
        if limit < 1:
            raise ValueError("limit must be positive")
        bounded_limit = min(limit, MAX_SOURCE_CHUNKS_PER_READ)
        return self._fetch_all(
            f"""
                SELECT {SOURCE_CHUNK_COLUMNS}
                FROM source_chunks
                WHERE source_id = %s::uuid
                ORDER BY chunk_index ASC, id ASC
                LIMIT %s
                """,
            (source_id, bounded_limit),
        )

    def search_source_chunks(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        match_any: bool = False,
        scope_projects: tuple[str, ...] = (),
        scope_people: tuple[str, ...] = (),
        scope_window_start: datetime | None = None,
        scope_window_end: datetime | None = None,
    ) -> list[VNextRow]:
        """Content search over source_chunks.text; best chunk hit first.

        Rank comes back as ``fts_score`` on each chunk row (row order IS
        the rank), and every row carries ``source_id`` so the retrieval
        service can promote the parent source. The domain/sensitivity
        gates live on the parent source row, so the query joins sources
        and applies them there, mirroring ``search_sources``. Strict
        pass: ``websearch_to_tsquery`` ANDs every non-stopword term;
        ``match_any`` ORs the sanitized lexemes instead (the retrieval
        service's one-shot fallback for multi-word questions the strict
        pass missed). Uses the ``search_tsv`` generated column + GIN
        index from migration 20260707_0081.
        """
        if match_any:
            tsquery_sql = "to_tsquery('english', %s)"
            tsquery_text = _tsquery_any_expression(query)
            if tsquery_text is None:
                return []
        else:
            tsquery_sql = "websearch_to_tsquery('english', %s)"
            tsquery_text = query
        scope_projects_list = list(scope_projects) or None
        scope_people_list = list(scope_people) or None
        project_scope_sql = _SOURCE_SCOPE_PROJECT_SQL.replace("metadata_json", "s.metadata_json")
        people_scope_sql = _SOURCE_SCOPE_PEOPLE_SQL.replace("metadata_json", "s.metadata_json")
        event_time_sql = (
            _SOURCE_SCOPE_EVENT_TIME_SQL.replace("source_created_at", "s.source_created_at")
            .replace("captured_at", "s.captured_at")
            .replace("metadata_json", "s.metadata_json")
        )
        return self._fetch_all(
            f"""
                SELECT {_SOURCE_CHUNK_SEARCH_COLUMNS},
                  ts_rank(c.search_tsv, {tsquery_sql}) AS fts_score
                FROM source_chunks c
                JOIN sources s ON s.id = c.source_id AND s.user_id = c.user_id
                WHERE s.deleted_at IS NULL
                  AND (%s::text[] IS NULL OR s.domain = ANY(%s::text[]) OR s.domain = 'unknown')
                  AND (%s::text[] IS NULL OR s.sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({project_scope_sql}) ?| %s::text[])
                  AND (%s::text[] IS NULL OR {people_scope_sql})
                  AND (%s::timestamptz IS NULL OR {event_time_sql} >= %s::timestamptz)
                  AND (%s::timestamptz IS NULL OR {event_time_sql} <= %s::timestamptz)
                  AND c.search_tsv @@ {tsquery_sql}
                ORDER BY fts_score DESC, c.created_at DESC, c.id DESC
                LIMIT %s
                """,
            (
                tsquery_text,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                scope_projects_list,
                scope_projects_list,
                scope_people_list,
                scope_people_list,
                scope_window_start,
                scope_window_start,
                scope_window_end,
                scope_window_end,
                tsquery_text,
                limit,
            ),
        )

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_memory",
            f"""
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
                  project_id,
                  created_by_agent_id,
                  run_id,
                  superseded_by,
                  supersedes,
                  created_at,
                  updated_at
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::uuid,
                  %s::uuid,
                  clock_timestamp(),
                  clock_timestamp()
                )
                -- Targetless form stays executable while migration tests
                -- run current code against pre-0083 schemas, where the
                -- commit-digest UNIQUE index does not exist yet. Once 0083
                -- is installed, that index still makes retries atomic.
                ON CONFLICT DO NOTHING
                RETURNING {MEMORY_COLUMNS}
                """,
            (
                memory.get("id"),
                memory.get("agent_profile_id", "assistant_default"),
                memory["memory_key"],
                _json_object(memory.get("value")),
                memory.get("status", "candidate"),
                _json_list(memory.get("source_event_ids")),
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
                memory.get("valid_from"),
                memory.get("valid_to"),
                memory.get("last_confirmed_at"),
                memory.get("title"),
                memory.get("canonical_text", ""),
                memory.get("summary"),
                memory.get("domain", "unknown"),
                memory.get("sensitivity", "unknown"),
                memory.get("first_seen_at"),
                memory.get("last_seen_at"),
                memory.get("last_reviewed_at"),
                _json_object(canonical_memory_metadata(memory)),
                memory.get("commit_digest"),
                memory.get("confirmation_id"),
                memory.get("project_id"),
                memory.get("created_by_agent_id"),
                memory.get("run_id"),
                memory.get("superseded_by"),
                memory.get("supersedes"),
            ),
        )
        self._append_mutation_event(
            event_type="memory.created",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(memory)},
        )
        return row

    def get_memory_by_key(
        self,
        *,
        memory_key: str,
        agent_profile_id: str = "assistant_default",
    ) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE agent_profile_id = %s
                  AND memory_key = %s
                  AND deleted_at IS NULL
                LIMIT 1
                """,
            (agent_profile_id, memory_key),
        )

    def upsert_memory_by_key(self, memory: JsonObject, *, actor_type: str = "system") -> VNextRow:
        """Create a deterministic-key memory or replay its existing row."""

        memory_key = str(memory.get("memory_key") or "").strip()
        if memory_key == "":
            raise ValueError("memory_key must not be empty")
        agent_profile_id = str(memory.get("agent_profile_id") or "assistant_default")
        try:
            return self.create_memory(memory, actor_type=actor_type)
        except ContinuityStoreInvariantError:
            # ``create_memory`` uses INSERT ... ON CONFLICT DO NOTHING.  A
            # conflict is therefore a successful, transaction-safe no-op;
            # resolve only the exact tenant/profile/key identity so unrelated
            # uniqueness conflicts still fail closed.
            existing = self.get_memory_by_key(
                memory_key=memory_key,
                agent_profile_id=agent_profile_id,
            )
            if existing is None:
                raise
            return existing

    def get_memory(self, memory_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                """,
            (memory_id,),
        )

    def get_memories_by_ids(self, memory_ids: Sequence[str]) -> list[VNextRow]:
        ids = list(dict.fromkeys(str(memory_id) for memory_id in memory_ids if memory_id))
        if not ids:
            return []
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND id = ANY(%s::uuid[])
                """,
            (ids,),
        )

    def list_memories_referencing_source(self, *, source_id: str, limit: int = 500) -> list[VNextRow]:
        """Bound memories related to one source, including provenance links."""

        if limit < 1:
            raise ValueError("limit must be positive")
        source_ref = f"source:{source_id}"
        qualified_columns = ", ".join(f"m.{column.strip()}" for column in MEMORY_COLUMNS.split(",") if column.strip())
        return self._fetch_all(
            f"""
                SELECT {qualified_columns}
                FROM memories AS m
                WHERE m.deleted_at IS NULL
                  AND (
                    m.source_event_ids ? %s
                    OR EXISTS (
                      SELECT 1
                      FROM provenance_links AS p
                      WHERE p.target_type = 'memory'
                        AND p.target_id = m.id::text
                        AND p.source_id = %s::uuid
                    )
                    OR m.metadata_json ->> 'source_id' = %s
                    OR m.metadata_json ->> 'source_ref' IN (%s, %s)
                    OR m.metadata_json -> 'source_ids' ? %s
                    OR m.metadata_json -> 'source_refs' ? %s
                    OR m.metadata_json -> 'source_refs' ? %s
                    OR m.metadata_json -> 'source_references' ? %s
                    OR m.metadata_json -> 'source_references' ? %s
                    OR m.metadata_json -> 'selected_source_ids' ? %s
                  )
                ORDER BY m.updated_at DESC, m.created_at DESC, m.id DESC
                LIMIT %s
                """,
            (
                source_id,
                source_id,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_ref,
                source_id,
                limit,
            ),
        )

    def get_memory_for_update(self, memory_id: str) -> VNextRow | None:
        """Load and lock one memory for a review/lifecycle decision."""
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                FOR UPDATE
                """,
            (memory_id,),
        )

    def list_pending_derived_candidates_for_member(
        self,
        *,
        member_id: str,
        exclude_memory_id: str | None = None,
    ) -> list[VNextRow]:
        """Lock pending consolidation/roll-up candidates derived from a member.

        New derived candidates persist their reviewed inputs under
        ``consolidation.member_snapshots``. Querying that bounded pending set
        lets a correction or retirement invalidate stale review work in the
        same transaction as the source-memory mutation.
        """
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories AS candidate
                WHERE candidate.deleted_at IS NULL
                  AND candidate.status IN ('candidate', 'needs_review')
                  AND (%s::uuid IS NULL OR candidate.id <> %s::uuid)
                  AND EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                      CASE
                        WHEN jsonb_typeof(
                          candidate.metadata_json #> '{{consolidation,member_snapshots}}'
                        ) = 'array'
                        THEN candidate.metadata_json #> '{{consolidation,member_snapshots}}'
                        ELSE '[]'::jsonb
                      END
                    ) AS member_snapshot(value)
                    WHERE member_snapshot.value ->> 'id' = %s
                  )
                ORDER BY candidate.id
                FOR UPDATE OF candidate
                """,
            (exclude_memory_id, exclude_memory_id, str(member_id)),
        )

    def list_memories(
        self,
        *,
        status: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        projects: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> list[VNextRow]:
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive")
        status_sql = ""
        params: list[object] = []
        if status is not None:
            status_sql = " AND status = %s"
            params.append(status)
        domains_sql = ""
        if domains:
            domains_sql = " AND (domain = ANY(%s::text[]) OR domain = 'unknown')"
            params.append(domains)
        sensitivity_sql = ""
        if sensitivity_allowed is not None:
            if not sensitivity_allowed:
                return []
            sensitivity_sql = " AND COALESCE(sensitivity, 'unknown') = ANY(%s::text[])"
            params.append(sensitivity_allowed)
        projects_sql = ""
        project_list = list(normalize_project_scope(projects or ())) or None
        if project_list is not None:
            projects_sql = f" AND ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[]"
            params.append(project_list)
        limit_sql = ""
        if limit is not None:
            limit_sql = " LIMIT %s"
            params.append(limit)
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL{status_sql}{domains_sql}{sensitivity_sql}{projects_sql}
                ORDER BY updated_at DESC, created_at DESC, id DESC
                {limit_sql}
                """,
            tuple(params),
        )

    def list_memories_by_statuses(
        self,
        *,
        statuses: Sequence[str],
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 30,
    ) -> list[VNextRow]:
        """Return a bounded review/workspace slice for several statuses.

        Callers previously materialized the entire memory corpus and filtered
        it in Python.  Keep the status predicate, tenant RLS, ordering, and
        limit in PostgreSQL so dashboard latency and memory use stay bounded.
        """
        if limit < 1:
            raise ValueError("limit must be positive")
        normalized_statuses = list(dict.fromkeys(str(value) for value in statuses if str(value)))
        if not normalized_statuses:
            return []
        if sensitivity_allowed is not None and not sensitivity_allowed:
            return []
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status = ANY(%s::text[])
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR COALESCE(sensitivity, 'unknown') = ANY(%s::text[]))
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                normalized_statuses,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                limit,
            ),
        )

    def count_memories_by_status(
        self,
        *,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
    ) -> dict[str, int]:
        """Return exact status counts without loading memory rows."""
        if sensitivity_allowed is not None and not sensitivity_allowed:
            return {}
        rows = self._fetch_all(
            """
                SELECT status, COUNT(*)::bigint AS count
                FROM memories
                WHERE deleted_at IS NULL
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR COALESCE(sensitivity, 'unknown') = ANY(%s::text[]))
                GROUP BY status
                ORDER BY status
                """,
            (domains, domains, sensitivity_allowed, sensitivity_allowed),
        )
        return {str(row["status"]): int(cast(int, row["count"])) for row in rows}

    def list_recent_agentic_commits(self, *, limit: int = 20) -> list[VNextRow]:
        """Bounded replacement for scanning all memories in ``recent_commits``."""
        if limit < 1:
            raise ValueError("limit must be positive")
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND metadata_json #>> '{{agentic_memory,kind}}' = 'agentic_memory_commit'
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (limit,),
        )

    def list_pending_inline_confirmations(self, *, limit: int = 20) -> list[VNextRow]:
        """Return only actionable inline confirmations, never resolved rows."""
        if limit < 1:
            raise ValueError("limit must be positive")
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status = 'needs_review'
                  AND confirmation_status = 'unconfirmed'
                  AND metadata_json #>> '{{agentic_memory,kind}}' = 'agentic_memory_commit'
                  AND metadata_json #>> '{{agentic_memory,confirmation,status}}' = 'pending'
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (limit,),
        )

    def find_live_memory_by_canonical_text(
        self,
        canonical_text: str,
        *,
        domain: str,
        sensitivity: str,
        project_scope: Sequence[str] = (),
    ) -> VNextRow | None:
        """Find one live, exactly-scoped duplicate without an O(N) scan."""
        normalized_text = str(canonical_text).strip()
        if not normalized_text:
            return None
        normalized_scope = list(normalize_project_scope(project_scope))
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status IN ('candidate', 'active', 'accepted', 'needs_review', 'private_only')
                  AND md5(lower(canonical_text)) = md5(lower(%s))
                  AND lower(canonical_text) = lower(%s)
                  AND domain = %s
                  AND sensitivity = %s
                  AND {_MEMORY_PROJECT_SCOPE_SQL} = %s::jsonb
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT 1
                """,
            (
                normalized_text,
                normalized_text,
                str(domain),
                str(sensitivity),
                _json_list(normalized_scope),
            ),
        )

    def list_memories_for_staleness_sweep(
        self,
        *,
        reference_time: datetime,
        confirmation_before: datetime,
        review_memory_types: Sequence[str],
        limit: int,
        projects: Sequence[str] | None = None,
    ) -> list[VNextRow]:
        """Read only active rows that actually cross a staleness threshold."""
        if limit < 1:
            raise ValueError("limit must be positive")
        memory_types = list(dict.fromkeys(str(value) for value in review_memory_types if str(value)))
        project_list = list(normalize_project_scope(projects or ())) or None
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status = 'active'
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                  AND (
                    (valid_to IS NOT NULL AND valid_to < %s::timestamptz)
                    OR (
                      memory_type = ANY(%s::text[])
                      AND COALESCE(last_confirmed_at, last_seen_at, created_at) < %s::timestamptz
                    )
                  )
                ORDER BY
                  CASE WHEN valid_to IS NOT NULL AND valid_to < %s::timestamptz THEN 0 ELSE 1 END,
                  COALESCE(valid_to, last_confirmed_at, last_seen_at, created_at) ASC,
                  id ASC
                LIMIT %s
                """,
            (
                project_list,
                project_list,
                reference_time,
                memory_types,
                confirmation_before,
                reference_time,
                limit,
            ),
        )

    def count_memories(
        self,
        *,
        status: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        projects: Sequence[str] | None = None,
    ) -> int:
        """Count the exact in-scope memory corpus without materializing it."""
        status_sql = ""
        params: list[object] = []
        if status is not None:
            status_sql = " AND status = %s"
            params.append(status)
        domains_sql = ""
        if domains:
            domains_sql = " AND (domain = ANY(%s::text[]) OR domain = 'unknown')"
            params.append(domains)
        sensitivity_sql = ""
        if sensitivity_allowed is not None:
            if not sensitivity_allowed:
                return 0
            sensitivity_sql = " AND COALESCE(sensitivity, 'unknown') = ANY(%s::text[])"
            params.append(sensitivity_allowed)
        projects_sql = ""
        project_list = list(normalize_project_scope(projects or ())) or None
        if project_list is not None:
            projects_sql = f" AND ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[]"
            params.append(project_list)
        row = self._fetch_one(
            "count memories",
            f"""
                SELECT COUNT(*) AS count
                FROM memories
                WHERE deleted_at IS NULL{status_sql}{domains_sql}{sensitivity_sql}{projects_sql}
                """,
            tuple(params),
        )
        return cast(int, row["count"])

    def list_rollup_input_memories(
        self,
        *,
        domains: list[str] | None,
        sensitivity_allowed: list[str],
        excluded_candidate_kind: str,
        limit: int,
        projects: Sequence[str] | None = None,
    ) -> list[VNextRow]:
        """Return the newest bounded roll-up inputs, excluding cards in SQL."""
        if limit < 1:
            raise ValueError("limit must be positive")
        if not sensitivity_allowed:
            return []
        domain_filter = domains or None
        project_list = list(normalize_project_scope(projects or ())) or None
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}
                  AND COALESCE(metadata_json ->> 'candidate_kind', '') <> %s
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND COALESCE(sensitivity, 'unknown') = ANY(%s::text[])
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
            (
                excluded_candidate_kind,
                domain_filter,
                domain_filter,
                sensitivity_allowed,
                project_list,
                project_list,
                limit,
            ),
        )

    def count_rollup_input_memories(
        self,
        *,
        domains: list[str] | None,
        sensitivity_allowed: list[str],
        excluded_candidate_kind: str,
        projects: Sequence[str] | None = None,
    ) -> int:
        """Return the authoritative total behind the bounded roll-up read."""
        if not sensitivity_allowed:
            return 0
        domain_filter = domains or None
        project_list = list(normalize_project_scope(projects or ())) or None
        row = self._fetch_one(
            "count rollup input memories",
            f"""
                SELECT COUNT(*) AS count
                FROM memories
                WHERE deleted_at IS NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}
                  AND COALESCE(metadata_json ->> 'candidate_kind', '') <> %s
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND COALESCE(sensitivity, 'unknown') = ANY(%s::text[])
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                """,
            (
                excluded_candidate_kind,
                domain_filter,
                domain_filter,
                sensitivity_allowed,
                project_list,
                project_list,
            ),
        )
        return cast(int, row["count"])

    def list_pending_rollup_candidates(
        self,
        *,
        rollup_digests: tuple[str, ...],
        domains: list[str] | None,
        sensitivity_allowed: list[str],
        candidate_kind: str,
        limit: int,
        projects: Sequence[str] | None = None,
    ) -> list[VNextRow]:
        """Return at most one newest pending candidate per requested digest."""
        unique_digests = tuple(sorted(set(rollup_digests)))
        if not unique_digests or not sensitivity_allowed:
            return []
        if limit < 1:
            raise ValueError("limit must be positive")
        bounded_limit = min(limit, len(unique_digests))
        domain_filter = domains or None
        project_list = list(normalize_project_scope(projects or ())) or None
        return self._fetch_all(
            f"""
                SELECT DISTINCT ON (metadata_json ->> 'rollup_digest') {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status = 'candidate'
                  AND metadata_json ->> 'candidate_kind' = %s
                  AND metadata_json ->> 'rollup_digest' = ANY(%s::text[])
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND COALESCE(sensitivity, 'unknown') = ANY(%s::text[])
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                ORDER BY metadata_json ->> 'rollup_digest', updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                candidate_kind,
                list(unique_digests),
                domain_filter,
                domain_filter,
                sensitivity_allowed,
                project_list,
                project_list,
                bounded_limit,
            ),
        )

    def list_accepted_rollup_cards(
        self,
        *,
        rollup_keys: tuple[str, ...],
        domains: list[str] | None,
        sensitivity_allowed: list[str],
        candidate_kind: str,
        limit: int,
        projects: Sequence[str] | None = None,
    ) -> list[VNextRow]:
        """Return at most one active/accepted card per requested roll-up key."""
        unique_keys = tuple(sorted(set(rollup_keys)))
        if not unique_keys or not sensitivity_allowed:
            return []
        if limit < 1:
            raise ValueError("limit must be positive")
        bounded_limit = min(limit, len(unique_keys))
        domain_filter = domains or None
        project_list = list(normalize_project_scope(projects or ())) or None
        return self._fetch_all(
            f"""
                SELECT DISTINCT ON (metadata_json ->> 'rollup_key') {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}
                  AND metadata_json ->> 'candidate_kind' = %s
                  AND metadata_json ->> 'rollup_key' = ANY(%s::text[])
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND COALESCE(sensitivity, 'unknown') = ANY(%s::text[])
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                ORDER BY
                  metadata_json ->> 'rollup_key',
                  CASE WHEN status = 'active' THEN 0 ELSE 1 END,
                  updated_at DESC,
                  created_at DESC,
                  id DESC
                LIMIT %s
                """,
            (
                candidate_kind,
                list(unique_keys),
                domain_filter,
                domain_filter,
                sensitivity_allowed,
                project_list,
                project_list,
                bounded_limit,
            ),
        )

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
    ) -> list[VNextRow]:
        patterns = _search_patterns(query)
        exact_pattern = patterns[0]
        memory_type_list = list(memory_types) or None
        project_list = list(projects) or None
        created_by_list = list(created_by_agent_ids) or None
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR memory_type = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                  AND (%s::text[] IS NULL OR created_by_agent_id = ANY(%s::text[]))
                  AND (%s::text IS NULL OR run_id = %s)
                  AND (%s::boolean OR valid_to IS NULL OR valid_to >= clock_timestamp())
                  AND (
                    memory_key ILIKE ANY(%s::text[])
                    OR title ILIKE ANY(%s::text[])
                    OR canonical_text ILIKE ANY(%s::text[])
                    OR summary ILIKE ANY(%s::text[])
                    OR value::text ILIKE ANY(%s::text[])
                  )
                ORDER BY
                  CASE
                    WHEN canonical_text ILIKE %s THEN 0
                    WHEN title ILIKE %s THEN 1
                    WHEN canonical_text ILIKE ANY(%s::text[]) THEN 2
                    WHEN title ILIKE ANY(%s::text[]) THEN 3
                    ELSE 4
                  END,
                  updated_at DESC,
                  created_at DESC,
                  id DESC
                LIMIT %s
                """,
            (
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                memory_type_list,
                memory_type_list,
                project_list,
                project_list,
                created_by_list,
                created_by_list,
                run_id,
                run_id,
                include_expired,
                patterns,
                patterns,
                patterns,
                patterns,
                patterns,
                exact_pattern,
                exact_pattern,
                patterns,
                patterns,
                limit,
            ),
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
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
        match_any: bool = False,
        scope_thread_id: str | None = None,
        scope_task_id: str | None = None,
        scope_people: tuple[str, ...] = (),
        scope_person_memory_ids: tuple[str, ...] = (),
        scope_window_start: datetime | None = None,
        scope_window_end: datetime | None = None,
    ) -> list[VNextRow]:
        memory_type_list = list(memory_types) or None
        project_list = list(projects) or None
        created_by_list = list(created_by_agent_ids) or None
        scope_people_list = list(scope_people) or None
        scope_person_id_list = list(scope_person_memory_ids) or None
        # Strict pass: websearch_to_tsquery ANDs every non-stopword term.
        # match_any (the retrieval OR-fallback): a to_tsquery OR of the
        # sanitized lexemes, so a natural-language question still reaches
        # keyword-findable memories when the AND pass returns nothing.
        if match_any:
            tsquery_sql = "to_tsquery('english', %s)"
            tsquery_text = _tsquery_any_expression(query)
            if tsquery_text is None:
                return []
        else:
            tsquery_sql = "websearch_to_tsquery('english', %s)"
            tsquery_text = query
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS},
                  ts_rank(search_tsv, {tsquery_sql}) AS fts_score
                FROM memories
                WHERE deleted_at IS NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR memory_type = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                  AND (%s::text[] IS NULL OR created_by_agent_id = ANY(%s::text[]))
                  AND (%s::text IS NULL OR run_id = %s)
                  AND (%s::boolean OR valid_to IS NULL OR valid_to >= clock_timestamp())
                  AND (
                    %s::text IS NULL
                    OR lower(trim(metadata_json ->> 'thread_id')) = lower(trim(%s::text))
                  )
                  AND (
                    %s::text IS NULL
                    OR lower(trim(metadata_json ->> 'task_id')) = lower(trim(%s::text))
                  )
                  AND (
                    %s::text[] IS NULL
                    OR id::text = ANY(%s::text[])
                    OR {_MEMORY_DIRECT_PEOPLE_SQL}
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_MEMORY_SCOPE_EVENT_TIME_SQL} >= %s::timestamptz
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_MEMORY_SCOPE_EVENT_TIME_SQL} <= %s::timestamptz
                  )
                  AND search_tsv @@ {tsquery_sql}
                ORDER BY fts_score DESC, updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                tsquery_text,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                memory_type_list,
                memory_type_list,
                project_list,
                project_list,
                created_by_list,
                created_by_list,
                run_id,
                run_id,
                include_expired,
                scope_thread_id,
                scope_thread_id,
                scope_task_id,
                scope_task_id,
                scope_people_list,
                scope_person_id_list,
                scope_people_list,
                scope_window_start,
                scope_window_start,
                scope_window_end,
                scope_window_end,
                tsquery_text,
                limit,
            ),
        )

    def search_memories_vector(
        self,
        *,
        query_vector: list[float],
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        embedding_endpoint: str | None = None,
        embedding_signature_version: int | None = None,
        scope_thread_id: str | None = None,
        scope_task_id: str | None = None,
        scope_people: tuple[str, ...] = (),
        scope_person_memory_ids: tuple[str, ...] = (),
        scope_window_start: datetime | None = None,
        scope_window_end: datetime | None = None,
    ) -> list[VNextRow]:
        vector_param = _vector_literal(query_vector)
        memory_type_list = list(memory_types) or None
        project_list = list(projects) or None
        created_by_list = list(created_by_agent_ids) or None
        scope_people_list = list(scope_people) or None
        scope_person_id_list = list(scope_person_memory_ids) or None
        signature_sql = ""
        signature_params: list[object] = []
        if embedding_provider is not None or embedding_model is not None:
            if not embedding_provider or not embedding_model:
                raise ContinuityStoreInvariantError("embedding_provider and embedding_model must be supplied together")
            signature_sql = f"""
                  AND metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'provider' = %s
                  AND metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'model' = %s
            """
            signature_params.extend((embedding_provider, embedding_model))
            if embedding_endpoint is not None:
                # Vectors carry an endpoint fingerprint; only pool those from the
                # same endpoint as the query so distinct coordinate spaces that
                # share provider/model labels are never compared.
                signature_sql += f"""
                  AND metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'endpoint' = %s
                """
                signature_params.append(embedding_endpoint)
            if embedding_signature_version is not None:
                signature_sql += f"""
                  AND metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'version' = %s
                """
                signature_params.append(str(embedding_signature_version))
            # Content freshness belongs in the indexed candidate query, not
            # after its LIMIT.  Filtering stale signatures only in Python let
            # four stale nearest neighbors exhaust a limit=1 overfetch and
            # report zero vector candidates even when a current row followed.
            signature_sql += f"""
                  AND metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'content_sha256'
                    = ({_MEMORY_EMBEDDING_CONTENT_SHA256_SQL})
            """
        params: list[object] = [
            vector_param,
            domains,
            domains,
            sensitivity_allowed,
            sensitivity_allowed,
            memory_type_list,
            memory_type_list,
            project_list,
            project_list,
            created_by_list,
            created_by_list,
            run_id,
            run_id,
            scope_thread_id,
            scope_thread_id,
            scope_task_id,
            scope_task_id,
            scope_people_list,
            scope_person_id_list,
            scope_people_list,
            scope_window_start,
            scope_window_start,
            scope_window_end,
            scope_window_end,
        ]
        params.extend(signature_params)
        candidate_limit = max(limit, min(limit * 4, 1000)) if signature_sql else limit
        base_params = [*params, include_expired, vector_param]
        # Enable iterative HNSW scan so the lifecycle/scope/signature filters
        # applied alongside the approximate ORDER BY do not silently underfill
        # the result set (a plain filtered HNSW scan can return far fewer than
        # LIMIT valid rows). ``hnsw.iterative_scan`` is a dotted custom GUC, so
        # this is a harmless no-op on pgvector < 0.8 rather than an error, and
        # SET LOCAL scopes it to the current transaction.
        with self.conn.cursor() as cur:
            cur.execute("SET LOCAL hnsw.iterative_scan = 'strict_order'")
        vector_query = f"""
                SELECT {MEMORY_COLUMNS},
                  (embedding_vector <=> %s::vector) AS vector_distance
                FROM memories
                WHERE deleted_at IS NULL
                  AND embedding_vector IS NOT NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR memory_type = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                  AND (%s::text[] IS NULL OR created_by_agent_id = ANY(%s::text[]))
                  AND (%s::text IS NULL OR run_id = %s)
                  AND (
                    %s::text IS NULL
                    OR lower(trim(metadata_json ->> 'thread_id')) = lower(trim(%s::text))
                  )
                  AND (
                    %s::text IS NULL
                    OR lower(trim(metadata_json ->> 'task_id')) = lower(trim(%s::text))
                  )
                  AND (
                    %s::text[] IS NULL
                    OR id::text = ANY(%s::text[])
                    OR {_MEMORY_DIRECT_PEOPLE_SQL}
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_MEMORY_SCOPE_EVENT_TIME_SQL} >= %s::timestamptz
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_MEMORY_SCOPE_EVENT_TIME_SQL} <= %s::timestamptz
                  )
                  {signature_sql}
                  AND (%s::boolean OR valid_to IS NULL OR valid_to >= clock_timestamp())
                ORDER BY embedding_vector <=> %s::vector
                LIMIT %s
                """
        while True:
            rows = self._fetch_all(vector_query, tuple((*base_params, candidate_limit)))
            if not signature_sql:
                return rows
            current_rows = [row for row in rows if memory_embedding_signature_is_current(row)]
            if len(current_rows) >= limit:
                return current_rows[:limit]
            # The SQL freshness predicate should make every row current. This
            # bounded deepening is a defensive compatibility path for older
            # pgcrypto/text-normalization behavior and test doubles: expand
            # until PostgreSQL reports exhaustion rather than treating a
            # fixed four-times overfetch as authoritative.
            if len(rows) < candidate_limit or candidate_limit >= 1000:
                return current_rows[:limit]
            candidate_limit = min(candidate_limit * 2, 1000)

    def search_memories_by_time(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        window_center: datetime | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 50,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
    ) -> list[VNextRow]:
        """Memories whose event window intersects ``[window_start, window_end)``.

        Event time is ``COALESCE(valid_from, first_seen_at, created_at)``:
        ``valid_from`` is the explicit event-validity start when a writer
        recorded one (the honest event signal); ``first_seen_at`` — when
        the fact was first observed — is the fallback for rows without
        one, and ``created_at`` (row write time) is the last resort for
        legacy rows. A row matches when that event time falls inside the
        window, or when a closed ``[valid_from, valid_to)`` validity
        interval overlaps it. Results order by proximity of the event
        time to ``window_center`` (default: the window midpoint; open
        "before X"/"since X" windows pass their closed edge), so the
        tightest temporal matches lead the RRF list. Same scoping
        discipline as the sibling search methods (deleted/status gates,
        domain/sensitivity/scope filters); note the default expiry gate
        still hides rows whose ``valid_to`` has passed — pass
        ``include_expired=True`` to recall facts that were only true
        historically.
        """
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=UTC)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=UTC)
        if window_center is None:
            window_center = window_start + (window_end - window_start) / 2
        elif window_center.tzinfo is None:
            window_center = window_center.replace(tzinfo=UTC)
        memory_type_list = list(memory_types) or None
        project_list = list(projects) or None
        created_by_list = list(created_by_agent_ids) or None
        event_time_sql = "COALESCE(valid_from, first_seen_at, created_at)"
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status IN {_MEMORY_SEARCHABLE_STATUSES_SQL}
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR memory_type = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({_MEMORY_PROJECT_SCOPE_SQL}) ?| %s::text[])
                  AND (%s::text[] IS NULL OR created_by_agent_id = ANY(%s::text[]))
                  AND (%s::text IS NULL OR run_id = %s)
                  AND (%s::boolean OR valid_to IS NULL OR valid_to >= clock_timestamp())
                  AND (
                    ({event_time_sql} >= %s::timestamptz AND {event_time_sql} < %s::timestamptz)
                    OR (
                      valid_from IS NOT NULL
                      AND valid_to IS NOT NULL
                      AND valid_from < %s::timestamptz
                      AND valid_to > %s::timestamptz
                    )
                  )
                ORDER BY
                  ABS(EXTRACT(EPOCH FROM ({event_time_sql} - %s::timestamptz))) ASC,
                  updated_at DESC,
                  created_at DESC,
                  id DESC
                LIMIT %s
                """,
            (
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                memory_type_list,
                memory_type_list,
                project_list,
                project_list,
                created_by_list,
                created_by_list,
                run_id,
                run_id,
                include_expired,
                window_start,
                window_end,
                window_end,
                window_start,
                window_center,
                limit,
            ),
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
        signature_values = (provider, model, content_sha256)
        if any(value is not None for value in signature_values):
            if not all(isinstance(value, str) and value for value in signature_values):
                raise ContinuityStoreInvariantError(
                    "embedding provider, model, and content_sha256 must be supplied together"
                )
            signature_metadata: JsonObject = {
                "version": signature_version,
                "provider": provider,
                "model": model,
                "endpoint": endpoint if isinstance(endpoint, str) else "",
                "content_sha256": content_sha256,
            }
            return self._fetch_optional_one(
                f"""
                    UPDATE memories
                    SET embedding_vector = %s::vector,
                        metadata_json = jsonb_set(
                          metadata_json,
                          '{{{EMBEDDING_SIGNATURE_METADATA_KEY}}}',
                          %s::jsonb,
                          true
                        )
                    WHERE id = %s::uuid
                      AND deleted_at IS NULL
                      AND ({_MEMORY_EMBEDDING_CONTENT_SHA256_SQL}) = %s
                    RETURNING id
                    """,
                (
                    _vector_literal(vector),
                    Jsonb(signature_metadata),
                    memory_id,
                    content_sha256,
                ),
            )
        return self._fetch_optional_one(
            f"""
                UPDATE memories
                SET embedding_vector = %s::vector
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING id
                """,
            (_vector_literal(vector), memory_id),
        )

    def clear_memory_embedding(self, *, memory_id: str) -> VNextRow | None:
        """Invalidate content-derived vector state before a text mutation.

        The caller may immediately repopulate it through the configured
        provider. A missing/failed provider must leave NULL, never an
        embedding for the memory's previous text.
        """
        return self._fetch_optional_one(
            f"""
                UPDATE memories
                SET embedding_vector = NULL,
                    metadata_json = metadata_json - '{EMBEDDING_SIGNATURE_METADATA_KEY}'
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING id
                """,
            (memory_id,),
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
        signature_sql = ""
        signature_params: list[object] = []
        if embedding_provider is not None or embedding_model is not None:
            if not embedding_provider or not embedding_model:
                raise ContinuityStoreInvariantError("embedding_provider and embedding_model must be supplied together")
            signature_sql = f"""
                  OR metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'provider'
                       IS DISTINCT FROM %s
                  OR metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'model'
                       IS DISTINCT FROM %s
                  OR metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'content_sha256'
                       IS DISTINCT FROM ({_MEMORY_EMBEDDING_CONTENT_SHA256_SQL})
            """
            signature_params.extend((embedding_provider, embedding_model))
            if embedding_endpoint is not None:
                # A vector embedded via a different endpoint is stale and must be
                # re-embedded for the current endpoint's coordinate space.
                signature_sql += f"""
                  OR metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'endpoint'
                       IS DISTINCT FROM %s
                """
                signature_params.append(embedding_endpoint)
            if embedding_signature_version is not None:
                signature_sql += f"""
                  OR metadata_json -> '{EMBEDDING_SIGNATURE_METADATA_KEY}' ->> 'version'
                       IS DISTINCT FROM %s
                """
                signature_params.append(str(embedding_signature_version))
        params: list[object] = [*signature_params, after_id, after_id, limit]
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS},
                  (embedding_vector IS NOT NULL) AS embedding_present
                FROM memories
                WHERE deleted_at IS NULL
                  AND (
                    embedding_vector IS NULL
                    {signature_sql}
                  )
                  AND (%s::uuid IS NULL OR id > %s::uuid)
                ORDER BY id ASC
                LIMIT %s
                """,
            tuple(params),
        )

    def lock_graph_mutation(self) -> None:
        """Serialize lifecycle graph/candidate mutation per user.

        A transaction-scoped advisory lock keyed on the current user so two
        concurrent supersessions cannot each pass an unlocked cycle check and
        together close a cycle. The same pre-row boundary also serializes
        consolidation candidate acceptance/invalidation against member
        correction, forgetting, and transitions. Released automatically at
        commit/rollback.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_xact_lock(hashtext('vnext_supersession'), hashtext(app.current_user_id()::text))"
            )

    def list_memory_ids_with_embeddings(self, ids: "Sequence[str]") -> set[str]:
        """Exact-ID embedding-presence read for a specific set of memory IDs.

        Consolidation and rollups must know which *selected* rows have stored
        vectors. A global ANN probe returns nearest neighbors, not a presence
        test, so selected rows can be missed when unrelated neighbors dominate.
        This reads presence directly by ID.
        """
        id_list = [str(value) for value in ids if str(value)]
        if not id_list:
            return set()
        rows = self._fetch_all(
            """
                SELECT id
                FROM memories
                WHERE id = ANY(%s::uuid[])
                  AND deleted_at IS NULL
                  AND embedding_vector IS NOT NULL
                """,
            (id_list,),
        )
        return {str(row["id"]) for row in rows}

    def update_memory_fact_keys(self, *, memory_id: str, fact_keys: str | None) -> VNextRow | None:
        """Store derived retrieval keys; the generated ``search_tsv`` column
        (migration ``20260707_0082``) re-indexes them at 'D' weight.

        ``None`` resets the row to the "never derived" state the backfill
        pass scans for; ``""`` marks "derived, nothing to add". Mirrors
        ``update_memory_embedding``: a plain indexing write, no revision.
        """
        if fact_keys is not None and not isinstance(fact_keys, str):
            raise ContinuityStoreInvariantError("fact_keys must be a string or None")
        normalized = re.sub(r"\s+", " ", fact_keys).strip() if isinstance(fact_keys, str) else None
        return self._fetch_optional_one(
            """
                UPDATE memories
                SET fact_keys = %s
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING id
                """,
            (normalized, memory_id),
        )

    def list_memories_missing_fact_keys(self, *, limit: int = 100, after_id: str | None = None) -> list[VNextRow]:
        """Backfill pagination over rows whose fact_keys was never derived."""
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND fact_keys IS NULL
                  AND (%s::uuid IS NULL OR id > %s::uuid)
                ORDER BY id ASC
                LIMIT %s
                """,
            (after_id, after_id, limit),
        )

    def get_memory_by_commit_digest(self, commit_digest: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE commit_digest = %s
                  AND deleted_at IS NULL
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
            (commit_digest,),
        )

    def get_memory_by_confirmation_id(self, confirmation_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE confirmation_id = %s
                  AND deleted_at IS NULL
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
            (confirmation_id,),
        )

    def latest_agentic_commit_memory(self, *, agent_id: str | None = None) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND status = 'active'
                  AND metadata_json #>> '{{agentic_memory,kind}}' = 'agentic_memory_commit'
                  AND (
                    %s::text IS NULL
                    OR metadata_json #>> '{{agentic_memory,agent_id}}' = %s
                    OR metadata_json #>> '{{agentic_memory,agent_identity,agent_id}}' = %s
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT 1
                """,
            (agent_id, agent_id, agent_id),
        )

    def update_memory(self, *, memory_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_memory",
            f"""
                UPDATE memories
                SET value = COALESCE(%s, value),
                    status = COALESCE(%s, status),
                    source_event_ids = COALESCE(%s, source_event_ids),
                    memory_type = COALESCE(%s, memory_type),
                    confidence = COALESCE(%s, confidence),
                    salience = COALESCE(%s, salience),
                    confirmation_status = COALESCE(%s, confirmation_status),
                    trust_class = COALESCE(%s, trust_class),
                    promotion_eligibility = COALESCE(%s, promotion_eligibility),
                    evidence_count = COALESCE(%s, evidence_count),
                    independent_source_count = COALESCE(%s, independent_source_count),
                    extracted_by_model = COALESCE(%s, extracted_by_model),
                    trust_reason = COALESCE(%s, trust_reason),
                    valid_from = COALESCE(%s, valid_from),
                    valid_to = COALESCE(%s, valid_to),
                    last_confirmed_at = COALESCE(%s, last_confirmed_at),
                    title = COALESCE(%s, title),
                    canonical_text = COALESCE(%s, canonical_text),
                    summary = COALESCE(%s, summary),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    last_seen_at = COALESCE(%s, last_seen_at),
                    last_reviewed_at = COALESCE(%s, last_reviewed_at),
                    metadata_json = COALESCE(%s, metadata_json),
                    project_id = COALESCE(%s, project_id),
                    superseded_by = COALESCE(%s::uuid, superseded_by),
                    supersedes = COALESCE(%s::uuid, supersedes),
                    updated_at = clock_timestamp(),
                    deleted_at = CASE
                      WHEN %s = 'archived' THEN clock_timestamp()
                      ELSE deleted_at
                    END
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {MEMORY_COLUMNS}
                """,
            (
                _json_object(patch["value"]) if "value" in patch else None,
                patch.get("status"),
                _json_list(patch["source_event_ids"]) if "source_event_ids" in patch else None,
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
                patch.get("valid_from"),
                patch.get("valid_to"),
                patch.get("last_confirmed_at"),
                patch.get("title"),
                patch.get("canonical_text"),
                patch.get("summary"),
                patch.get("domain"),
                patch.get("sensitivity"),
                patch.get("last_seen_at"),
                patch.get("last_reviewed_at"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                patch.get("project_id"),
                patch.get("superseded_by"),
                patch.get("supersedes"),
                patch.get("status"),
                memory_id,
            ),
        )
        self._append_mutation_event(
            event_type="memory.updated",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def append_revision(self, revision: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "append_revision",
            f"""
                WITH locked_memory AS (
                  SELECT id
                  FROM memories
                  WHERE id = %s::uuid
                    AND user_id = app.current_user_id()
                  FOR UPDATE
                ),
                next_revision AS (
                  SELECT
                    COALESCE(MAX(sequence_no) + 1, 1) AS sequence_no,
                    COALESCE(MAX(revision_number) + 1, 1) AS revision_number
                  FROM memory_revisions
                  WHERE memory_id = (SELECT id FROM locked_memory)
                    AND user_id = app.current_user_id()
                )
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
                  metadata_json
                )
                SELECT
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  COALESCE(%s, next_revision.sequence_no),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s, next_revision.revision_number),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                FROM next_revision
                RETURNING {REVISION_COLUMNS}
                """,
            (
                revision["memory_id"],
                revision.get("id"),
                revision["memory_id"],
                revision.get("sequence_no"),
                revision.get("action", "UPDATE"),
                revision["memory_key"],
                _json_object(revision["previous_value"]) if "previous_value" in revision else None,
                _json_object(revision.get("new_value")),
                _json_list(revision.get("source_event_ids")),
                _json_object(revision.get("candidate")),
                revision.get("revision_number"),
                revision.get("revision_type", "edited"),
                revision.get("text_before"),
                revision.get("text_after", ""),
                revision.get("reason"),
                revision.get("actor_type", actor_type),
                revision.get("actor_id"),
                _json_object(revision.get("metadata_json")),
            ),
        )
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
                SELECT {REVISION_COLUMNS}
                FROM memory_revisions
                WHERE memory_id = %s::uuid
                ORDER BY revision_number ASC, sequence_no ASC, id ASC
                """,
            (memory_id,),
        )

    # -- true redaction ----------------------------------------------------
    #
    # Alice's forget is a soft delete; redaction expunges CONTENT while
    # preserving the audit SKELETON (ids, timestamps, event/revision
    # types, actor columns). The append-only triggers on event_log and
    # memory_revisions (replaced by migration 20260706_0079) only admit
    # these updates while the app.redaction_in_progress session flag is
    # 'on' AND the change is marker-shaped; _redaction_mode manages the
    # flag and resets it even on error paths.

    @contextmanager
    def _redaction_mode(self) -> Iterator[None]:
        """Set/reset the privileged redaction session flag around a block."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT set_config('app.redaction_in_progress', 'on', false)")
        try:
            yield
        finally:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT set_config('app.redaction_in_progress', 'off', false)")
            except Exception:
                # The failing statement aborted the transaction, so the
                # reset statement cannot run -- but the rollback that
                # follows discards the session-scoped flag with it
                # (set_config assignments are transactional).
                pass

    def redact_memory_content(self, *, memory_id: str, actor_type: str = "user") -> VNextRow:
        """Expunge a memory's content in place, keeping the skeleton.

        Content columns (title, canonical_text, summary, trust_reason,
        value) become the redaction marker, metadata_json is scrubbed to
        structural keys plus redacted_at, the content-derived columns
        (embedding, fact_keys) are cleared, and the row is archived.
        Applies to already-archived (soft-deleted) rows too -- that is
        the primary redaction target.
        """
        current = self._fetch_optional_one(
            """
                SELECT metadata_json
                FROM memories
                WHERE id = %s::uuid
                """,
            (memory_id,),
        )
        if current is None:
            raise ContinuityStoreInvariantError(
                "redact_memory_content did not find the memory to redact",
            )
        redacted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        scrubbed = redacted_memory_metadata(current.get("metadata_json"), redacted_at=redacted_at)
        with self._redaction_mode():
            row = self._fetch_one(
                "redact_memory_content",
                f"""
                    UPDATE memories
                    SET title = CASE WHEN title IS NULL THEN NULL ELSE %s END,
                        canonical_text = %s,
                        summary = CASE WHEN summary IS NULL THEN NULL ELSE %s END,
                        trust_reason = CASE WHEN trust_reason IS NULL THEN NULL ELSE %s END,
                        value = %s,
                        metadata_json = %s,
                        embedding_vector = NULL,
                        fact_keys = NULL,
                        status = 'archived',
                        deleted_at = COALESCE(deleted_at, clock_timestamp()),
                        updated_at = clock_timestamp()
                    WHERE id = %s::uuid
                    RETURNING {MEMORY_COLUMNS}
                    """,
                (
                    REDACTION_MARKER,
                    REDACTION_MARKER,
                    REDACTION_MARKER,
                    REDACTION_MARKER,
                    _json_object(REDACTED_JSON_VALUE),
                    _json_object(scrubbed),
                    memory_id,
                ),
            )
        self._append_mutation_event(
            event_type="memory.redacted",
            actor_type=actor_type,
            target_type="memory",
            target_id=row["id"],
            payload={"operation": "redact_memory_content"},
        )
        return row

    def redact_memory_revisions(self, *, memory_id: str, actor_type: str = "user") -> VNextRow:
        """Expunge revision content for a memory, keeping the skeleton.

        text_before/text_after/reason become the marker (reasons can
        carry content, so they are redacted too); previous_value/
        new_value/candidate/metadata_json become {"redacted": true}.
        NULL content stays NULL so the created-vs-edited shape survives.
        ids, sequence/revision numbers, revision_type, actor columns,
        and created_at are untouched.
        """
        with self._redaction_mode():
            redacted = self._fetch_all(
                """
                    UPDATE memory_revisions
                    SET previous_value = CASE WHEN previous_value IS NULL THEN NULL ELSE %s END,
                        new_value = CASE WHEN new_value IS NULL THEN NULL ELSE %s END,
                        candidate = %s,
                        text_before = CASE WHEN text_before IS NULL THEN NULL ELSE %s END,
                        text_after = %s,
                        reason = CASE WHEN reason IS NULL THEN NULL ELSE %s END,
                        metadata_json = %s
                    WHERE memory_id = %s::uuid
                    RETURNING id
                    """,
                (
                    _json_object(REDACTED_JSON_VALUE),
                    _json_object(REDACTED_JSON_VALUE),
                    _json_object(REDACTED_JSON_VALUE),
                    REDACTION_MARKER,
                    REDACTION_MARKER,
                    REDACTION_MARKER,
                    _json_object(REDACTED_JSON_VALUE),
                    memory_id,
                ),
            )
        self._append_mutation_event(
            event_type="memory.redacted",
            actor_type=actor_type,
            target_type="memory",
            target_id=memory_id,
            payload={"operation": "redact_memory_revisions", "redacted_revisions": len(redacted)},
        )
        return {"memory_id": memory_id, "redacted_revisions": len(redacted)}

    def redact_memory_events(self, *, memory_id: str, actor_type: str = "user") -> VNextRow:
        """Expunge event payloads that reference a memory.

        Matching rows keep event_type, actor columns, target columns,
        occurred_at, and trace/run references; payload_json becomes
        {"redacted": true, "memory_id": ..., "event_type": <own column>}
        and integrity_hash is cleared (it derives from the payload, so
        keeping it would allow confirming guesses of redacted content).
        """
        with self._redaction_mode():
            redacted = self._fetch_all(
                """
                    UPDATE event_log
                    SET payload_json = jsonb_build_object(
                          'redacted', true,
                          'memory_id', %s::text,
                          'event_type', event_type
                        ),
                        integrity_hash = NULL
                    WHERE (target_type = 'memory' AND target_id = %s)
                       OR payload_json::text LIKE %s
                    RETURNING id
                    """,
                (memory_id, memory_id, f"%{memory_id}%"),
            )
        self._append_mutation_event(
            event_type="memory.redacted",
            actor_type=actor_type,
            target_type="memory",
            target_id=memory_id,
            payload={"operation": "redact_memory_events", "redacted_events": len(redacted)},
        )
        return {"memory_id": memory_id, "redacted_events": len(redacted)}

    def create_provenance_link(self, link: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_provenance_link",
            f"""
                INSERT INTO provenance_links (
                  id,
                  user_id,
                  target_type,
                  target_id,
                  source_id,
                  source_chunk_id,
                  quote,
                  evidence_role,
                  confidence
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s::uuid,
                  %s::uuid,
                  %s,
                  %s,
                  %s
                )
                RETURNING {PROVENANCE_COLUMNS}
                """,
            (
                link.get("id"),
                link["target_type"],
                link["target_id"],
                link.get("source_id"),
                link.get("source_chunk_id"),
                link.get("quote"),
                link.get("evidence_role", "supports"),
                link.get("confidence", 0.5),
            ),
        )
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
                SELECT {PROVENANCE_COLUMNS}
                FROM provenance_links
                WHERE target_type = %s
                  AND target_id = %s
                ORDER BY created_at DESC, id DESC
                """,
            (target_type, target_id),
        )

    def list_provenance_links_for_targets(
        self,
        *,
        target_type: str,
        target_ids: Sequence[str],
    ) -> list[VNextRow]:
        ids = list(dict.fromkeys(str(target_id) for target_id in target_ids if target_id))
        if not ids:
            return []
        return self._fetch_all(
            f"""
                SELECT {PROVENANCE_COLUMNS}
                FROM provenance_links
                WHERE target_type = %s
                  AND target_id = ANY(%s::text[])
                ORDER BY created_at DESC, id DESC
                """,
            (target_type, ids),
        )

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
        scope_projects: tuple[str, ...] = (),
        scope_people: tuple[str, ...] = (),
        scope_window_start: datetime | None = None,
        scope_window_end: datetime | None = None,
    ) -> list[VNextRow]:
        patterns = _search_patterns(query)
        exact_pattern = patterns[0]
        scope_projects_list = list(scope_projects) or None
        scope_people_list = list(scope_people) or None
        return self._fetch_all(
            f"""
                SELECT {SOURCE_COLUMNS}
                FROM sources
                WHERE deleted_at IS NULL
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({_SOURCE_SCOPE_PROJECT_SQL}) ?| %s::text[])
                  AND (%s::text[] IS NULL OR {_SOURCE_SCOPE_PEOPLE_SQL})
                  AND (
                    %s::timestamptz IS NULL
                    OR {_SOURCE_SCOPE_EVENT_TIME_SQL} >= %s::timestamptz
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_SOURCE_SCOPE_EVENT_TIME_SQL} <= %s::timestamptz
                  )
                  AND (
                    title ILIKE ANY(%s::text[])
                    OR author ILIKE ANY(%s::text[])
                    OR uri ILIKE ANY(%s::text[])
                    OR raw_path ILIKE ANY(%s::text[])
                    OR content_hash ILIKE ANY(%s::text[])
                    OR metadata_json::text ILIKE ANY(%s::text[])
                  )
                ORDER BY
                  CASE
                    WHEN title ILIKE %s THEN 0
                    WHEN title ILIKE ANY(%s::text[]) THEN 1
                    ELSE 2
                  END,
                  captured_at DESC,
                  id DESC
                LIMIT %s
                """,
            (
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                scope_projects_list,
                scope_projects_list,
                scope_people_list,
                scope_people_list,
                scope_window_start,
                scope_window_start,
                scope_window_end,
                scope_window_end,
                patterns,
                patterns,
                patterns,
                patterns,
                patterns,
                patterns,
                exact_pattern,
                patterns,
                limit,
            ),
        )

    def create_edge(self, edge: JsonObject, *, actor_type: str = "system") -> VNextRow:
        # observed_at is event time: when the observation the edge encodes
        # actually happened (callers pass the source's source_created_at,
        # falling back to captured_at). Creation sites without source
        # context fall back to write time, noted in the edge metadata so
        # as-of readers can tell real event time from an ingestion-time
        # stand-in. valid_from defaults to observed_at so the validity
        # interval starts when the observation happened, not when it was
        # written. now() is transaction-stable, so defaulted observed_at
        # and valid_from land on the same instant.
        metadata_value = edge.get("metadata_json")
        metadata = dict(metadata_value) if isinstance(metadata_value, Mapping) else {}
        if edge.get("observed_at") is None:
            metadata.setdefault("observed_at_source", "now")
        row = self._fetch_one(
            "create_edge",
            f"""
                INSERT INTO graph_edges (
                  id,
                  user_id,
                  from_type,
                  from_id,
                  to_type,
                  to_id,
                  edge_type,
                  confidence,
                  explanation,
                  created_by,
                  observed_at,
                  valid_from,
                  valid_to,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, %s::timestamptz, now()),
                  %s,
                  %s
                )
                RETURNING {GRAPH_EDGE_COLUMNS}
                """,
            (
                edge.get("id"),
                edge["from_type"],
                edge["from_id"],
                edge["to_type"],
                edge["to_id"],
                edge["edge_type"],
                edge.get("confidence", 0.5),
                edge.get("explanation"),
                edge.get("created_by", actor_type),
                edge.get("observed_at"),
                edge.get("valid_from"),
                edge.get("observed_at"),
                edge.get("valid_to"),
                _json_object(metadata),
            ),
        )
        self._append_mutation_event(
            event_type="graph_edge.created",
            actor_type=actor_type,
            target_type="graph_edge",
            target_id=row["id"],
            payload={"operation": "create", "edge_type": str(row["edge_type"])},
        )
        return row

    def find_edge_by_idempotency_digest(self, *, digest: str) -> VNextRow | None:
        """Resolve one workflow-produced graph edge by its logical identity."""

        normalized_digest = str(digest).strip()
        if not normalized_digest:
            return None
        return self._fetch_optional_one(
            f"""
                SELECT {GRAPH_EDGE_COLUMNS}
                FROM graph_edges
                WHERE metadata_json ->> 'idempotency_digest' = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
            (normalized_digest,),
        )

    def upsert_edge_by_idempotency_digest(
        self,
        edge: JsonObject,
        *,
        digest: str,
        actor_type: str = "system",
    ) -> VNextRow:
        """Atomically create or replay one workflow-produced graph edge."""

        normalized_digest = str(digest).strip()
        if not normalized_digest:
            raise ValueError("digest must not be empty")
        existing = self.find_edge_by_idempotency_digest(digest=normalized_digest)
        if existing is not None:
            return existing
        metadata_value = edge.get("metadata_json")
        metadata = dict(metadata_value) if isinstance(metadata_value, Mapping) else {}
        metadata["idempotency_digest"] = normalized_digest
        if edge.get("observed_at") is None:
            metadata.setdefault("observed_at_source", "now")
        row = self._fetch_optional_one(
            f"""
                INSERT INTO graph_edges (
                  id,
                  user_id,
                  from_type,
                  from_id,
                  to_type,
                  to_id,
                  edge_type,
                  confidence,
                  explanation,
                  created_by,
                  observed_at,
                  valid_from,
                  valid_to,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, %s::timestamptz, now()),
                  %s,
                  %s
                )
                ON CONFLICT DO NOTHING
                RETURNING {GRAPH_EDGE_COLUMNS}
                """,
            (
                edge.get("id"),
                edge["from_type"],
                edge["from_id"],
                edge["to_type"],
                edge["to_id"],
                edge["edge_type"],
                edge.get("confidence", 0.5),
                edge.get("explanation"),
                edge.get("created_by", actor_type),
                edge.get("observed_at"),
                edge.get("valid_from"),
                edge.get("observed_at"),
                edge.get("valid_to"),
                _json_object(metadata),
            ),
        )
        created = row is not None
        if row is None:
            row = self.find_edge_by_idempotency_digest(digest=normalized_digest)
        if row is None:
            raise ContinuityStoreInvariantError(
                "upsert_edge_by_idempotency_digest could not resolve the persisted edge"
            )
        if created:
            self._append_mutation_event(
                event_type="graph_edge.created",
                actor_type=actor_type,
                target_type="graph_edge",
                target_id=row["id"],
                payload={"operation": "create", "edge_type": str(row["edge_type"])},
            )
        return row

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {GRAPH_EDGE_COLUMNS}
                FROM graph_edges
                WHERE (%s::text IS NULL OR from_id = %s)
                  AND (%s::text IS NULL OR to_id = %s)
                  AND valid_to IS NULL
                ORDER BY created_at DESC, id DESC
                """,
            (from_id, from_id, to_id, to_id),
        )

    def list_memory_entity_edges(
        self,
        *,
        entity_ids: Sequence[str],
        edge_types: Sequence[str] = ("mentions", "about"),
    ) -> list[VNextRow]:
        ids = list(dict.fromkeys(str(entity_id) for entity_id in entity_ids if entity_id))
        types = list(dict.fromkeys(str(edge_type) for edge_type in edge_types if edge_type))
        if not ids or not types:
            return []
        return self._fetch_all(
            f"""
                SELECT {GRAPH_EDGE_COLUMNS}
                FROM graph_edges
                WHERE valid_to IS NULL
                  AND edge_type = ANY(%s::text[])
                  AND (
                    (from_type = 'memory' AND to_type = 'entity' AND to_id = ANY(%s::text[]))
                    OR
                    (from_type = 'entity' AND to_type = 'memory' AND from_id = ANY(%s::text[]))
                  )
                ORDER BY created_at DESC, id DESC
                """,
            (types, ids, ids),
        )

    def list_edges_as_of(self, at: object, *, limit: int = 50) -> list[VNextRow]:
        """Edges that were in effect at ``at``: valid_from <= at < valid_to.

        User scoping comes from the graph_edges RLS policy, like every
        other read. Edges written before the temporal slice carry NULL
        ``valid_from`` and are excluded (their event time was never
        recorded).
        """
        return self._fetch_all(
            f"""
                SELECT {GRAPH_EDGE_COLUMNS}
                FROM graph_edges
                WHERE valid_from IS NOT NULL
                  AND valid_from <= %s::timestamptz
                  AND (valid_to IS NULL OR valid_to > %s::timestamptz)
                ORDER BY valid_from DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (at, at, limit),
        )

    def update_edge_status(self, *, edge_id: str, status: str, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_edge_status",
            f"""
                UPDATE graph_edges
                SET metadata_json = metadata_json || %s,
                    valid_to = CASE
                      WHEN %s = 'rejected' THEN clock_timestamp()
                      ELSE valid_to
                    END
                WHERE id = %s::uuid
                RETURNING {GRAPH_EDGE_COLUMNS}
                """,
            (_json_object({"status": status, "candidate": status != "accepted"}), status, edge_id),
        )
        self._append_mutation_event(
            event_type="graph_edge.updated",
            actor_type=actor_type,
            target_type="graph_edge",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def expire_edge(self, *, edge_id: str, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "expire_edge",
            f"""
                UPDATE graph_edges
                SET valid_to = clock_timestamp()
                WHERE id = %s::uuid
                  AND valid_to IS NULL
                RETURNING {GRAPH_EDGE_COLUMNS}
                """,
            (edge_id,),
        )
        self._append_mutation_event(
            event_type="graph_edge.expired",
            actor_type=actor_type,
            target_type="graph_edge",
            target_id=row["id"],
            payload={"operation": "expire"},
        )
        return row

    def create_project(self, project: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_project",
            f"""
                INSERT INTO projects (
                  id,
                  user_id,
                  name,
                  slug,
                  status,
                  description,
                  current_state,
                  domain,
                  sensitivity,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {PROJECT_COLUMNS}
                """,
            (
                project.get("id"),
                project["name"],
                project["slug"],
                project.get("status", "active"),
                project.get("description"),
                project.get("current_state"),
                project.get("domain", "professional"),
                project.get("sensitivity", "private"),
                _json_object(project.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="project.created",
            actor_type=actor_type,
            target_type="project",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(project)},
        )
        return row

    def get_project(self, project_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {PROJECT_COLUMNS}
                FROM projects
                WHERE id = %s::uuid
                """,
            (project_id,),
        )

    def get_project_for_update(self, project_id: str) -> VNextRow | None:
        """Lock a project while an artifact review applies its state."""

        return self._fetch_optional_one(
            f"""
                SELECT {PROJECT_COLUMNS}
                FROM projects
                WHERE id = %s::uuid
                FOR UPDATE
                """,
            (project_id,),
        )

    def list_projects(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        scope_projects: Sequence[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        project_scope = list(normalize_project_scope(scope_projects or ())) or None
        normalized_scope = [value.casefold() for value in project_scope] if project_scope else None
        return self._fetch_all(
            f"""
                SELECT {PROJECT_COLUMNS}
                FROM projects
                WHERE (%s::text IS NULL OR status = %s)
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (
                    %s::text[] IS NULL
                    OR id::text = ANY(%s::text[])
                    OR lower(slug) = ANY(%s::text[])
                    OR lower(name) = ANY(%s::text[])
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                status,
                status,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                project_scope,
                project_scope,
                normalized_scope,
                normalized_scope,
                limit,
            ),
        )

    def update_project(self, *, project_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_project",
            f"""
                UPDATE projects
                SET name = COALESCE(%s, name),
                    status = COALESCE(%s, status),
                    description = COALESCE(%s, description),
                    current_state = COALESCE(%s, current_state),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {PROJECT_COLUMNS}
                """,
            (
                patch.get("name"),
                patch.get("status"),
                patch.get("description"),
                patch.get("current_state"),
                patch.get("domain"),
                patch.get("sensitivity"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                project_id,
            ),
        )
        self._append_mutation_event(
            event_type="project.updated",
            actor_type=actor_type,
            target_type="project",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def create_person(self, person: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_person",
            f"""
                INSERT INTO people (
                  id,
                  user_id,
                  name,
                  aliases_json,
                  relationship_type,
                  organization,
                  sensitivity,
                  notes,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {PERSON_COLUMNS}
                """,
            (
                person.get("id"),
                person["name"],
                _json_list(person.get("aliases_json")),
                person.get("relationship_type"),
                person.get("organization"),
                person.get("sensitivity", "private"),
                person.get("notes"),
                _json_object(person.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="person.created",
            actor_type=actor_type,
            target_type="person",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(person)},
        )
        return row

    def get_person(self, person_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {PERSON_COLUMNS}
                FROM people
                WHERE id = %s::uuid
            """,
            (person_id,),
        )

    def list_people(
        self,
        *,
        sensitivity_allowed: list[str] | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {PERSON_COLUMNS}
                FROM people
                WHERE (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (sensitivity_allowed, sensitivity_allowed, limit),
        )

    def update_person(self, *, person_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_person",
            f"""
                UPDATE people
                SET name = COALESCE(%s, name),
                    aliases_json = COALESCE(%s, aliases_json),
                    relationship_type = COALESCE(%s, relationship_type),
                    organization = COALESCE(%s, organization),
                    sensitivity = COALESCE(%s, sensitivity),
                    notes = COALESCE(%s, notes),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {PERSON_COLUMNS}
                """,
            (
                patch.get("name"),
                _json_list(patch["aliases_json"]) if "aliases_json" in patch else None,
                patch.get("relationship_type"),
                patch.get("organization"),
                patch.get("sensitivity"),
                patch.get("notes"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                person_id,
            ),
        )
        self._append_mutation_event(
            event_type="person.updated",
            actor_type=actor_type,
            target_type="person",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    # -- entities ----------------------------------------------------------
    #
    # Generic entity substrate (migration 20260705_0078): one row per
    # resolved real-world thing, keyed for resolution by
    # (entity_type, normalized_name). Entities participate in the graph
    # without edge changes: graph_edges.from_type/from_id and
    # to_type/to_id are free-text node references (no FK, no node-type
    # CHECK), so an edge can point at an entity with
    # from_type='entity', from_id=<entity id> today; only edge_type is
    # constrained (to EDGE_TYPES from migration 20260510_0067).

    def create_entity(self, entity: JsonObject, *, actor_type: str = "system") -> VNextRow:
        name = str(entity["name"])
        normalized_name = str(entity.get("normalized_name") or normalize_entity_name(name))
        row = self._fetch_one(
            "create_entity",
            f"""
                INSERT INTO vnext_entities (
                  id,
                  user_id,
                  entity_type,
                  name,
                  normalized_name,
                  aliases,
                  metadata_json,
                  first_observed_at,
                  last_observed_at,
                  mention_count
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::timestamptz,
                  %s::timestamptz,
                  %s
                )
                RETURNING {ENTITY_COLUMNS}
                """,
            (
                entity.get("id"),
                entity["entity_type"],
                name,
                normalized_name,
                _json_list(entity.get("aliases")),
                _json_object(entity.get("metadata_json")),
                entity.get("first_observed_at"),
                entity.get("last_observed_at"),
                entity.get("mention_count", 0),
            ),
        )
        self._append_mutation_event(
            event_type="entity.created",
            actor_type=actor_type,
            target_type="entity",
            target_id=row["id"],
            payload={
                "operation": "create",
                "entity_type": str(row["entity_type"]),
                "fields": _sorted_field_names(entity),
            },
        )
        return row

    def get_entity(self, entity_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {ENTITY_COLUMNS}
                FROM vnext_entities
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                """,
            (entity_id,),
        )

    def get_entity_by_normalized_name(self, entity_type: str, normalized_name: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {ENTITY_COLUMNS}
                FROM vnext_entities
                WHERE entity_type = %s
                  AND normalized_name = %s
                  AND deleted_at IS NULL
                LIMIT 1
                """,
            (entity_type, normalized_name),
        )

    def find_entities_by_names(self, normalized_names: tuple[str, ...]) -> list[VNextRow]:
        """One-round-trip resolution lookup for query-time entity linking.

        Matches ``normalized_name`` OR any element of the ``aliases``
        jsonb array (``?|`` = "array contains any of these strings").
        Alias values are expected to already be normalized via
        ``normalize_entity_name`` -- matching is exact string equality.
        Most-mentioned entities sort first so callers can take the top
        match per name.
        """
        if not normalized_names:
            return []
        names = [str(name) for name in normalized_names]
        return self._fetch_all(
            f"""
                SELECT {ENTITY_COLUMNS}
                FROM vnext_entities
                WHERE deleted_at IS NULL
                  AND (normalized_name = ANY(%s::text[]) OR aliases ?| %s::text[])
                ORDER BY mention_count DESC, updated_at DESC, id DESC
                """,
            (names, names),
        )

    def list_entities(
        self,
        *,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {ENTITY_COLUMNS}
                FROM vnext_entities
                WHERE (%s::text IS NULL OR entity_type = %s)
                  AND deleted_at IS NULL
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (entity_type, entity_type, limit),
        )

    def update_entity(self, *, entity_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        immutable = sorted(set(patch) & ENTITY_IMMUTABLE_PATCH_FIELDS)
        if immutable:
            raise ContinuityStoreInvariantError(f"update_entity cannot modify immutable fields: {', '.join(immutable)}")
        row = self._fetch_one(
            "update_entity",
            f"""
                UPDATE vnext_entities
                SET name = COALESCE(%s, name),
                    aliases = COALESCE(%s, aliases),
                    metadata_json = COALESCE(%s, metadata_json),
                    mention_count = COALESCE(%s, mention_count),
                    first_observed_at = COALESCE(%s::timestamptz, first_observed_at),
                    last_observed_at = COALESCE(%s::timestamptz, last_observed_at),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {ENTITY_COLUMNS}
                """,
            (
                patch.get("name"),
                _json_list(patch["aliases"]) if "aliases" in patch else None,
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                patch.get("mention_count"),
                patch.get("first_observed_at"),
                patch.get("last_observed_at"),
                entity_id,
            ),
        )
        self._append_mutation_event(
            event_type="entity.updated",
            actor_type=actor_type,
            target_type="entity",
            target_id=row["id"],
            payload={"operation": "update", "changes": patch},
        )
        return row

    def record_entity_mention(
        self,
        *,
        entity_id: str,
        observed_at: object,
        source_id: str | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        """Count a mention and widen the observation window.

        ``first_observed_at``/``last_observed_at`` take COALESCE min/max
        semantics: out-of-order observations only ever widen the window.
        """
        if observed_at is None:
            raise ContinuityStoreInvariantError("record_entity_mention requires observed_at")
        row = self._fetch_one(
            "record_entity_mention",
            f"""
                UPDATE vnext_entities
                SET mention_count = mention_count + 1,
                    first_observed_at = LEAST(COALESCE(first_observed_at, %s::timestamptz), %s::timestamptz),
                    last_observed_at = GREATEST(COALESCE(last_observed_at, %s::timestamptz), %s::timestamptz),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING {ENTITY_COLUMNS}
                """,
            (observed_at, observed_at, observed_at, observed_at, entity_id),
        )
        self._append_mutation_event(
            event_type="entity.mention_recorded",
            actor_type=actor_type,
            target_type="entity",
            target_id=row["id"],
            payload={
                "operation": "record_mention",
                "observed_at": observed_at,
                "source_id": source_id,
            },
        )
        return row

    def record_relationship_change(
        self,
        *,
        entity_id: str,
        relationship_type: str,
        changed_at: object | None = None,
        source_id: str | None = None,
        metadata_json: JsonObject | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        """Append a relationship transition and update the entity.

        update_person overwrites relationship_type in place; this keeps
        the "advisor -> investor" history in the append-only
        entity_relationship_events table while the entity's
        metadata_json carries the current relationship_type.
        """
        current = self._fetch_optional_one(
            """
                SELECT metadata_json ->> 'relationship_type' AS relationship_type_before
                FROM vnext_entities
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                """,
            (entity_id,),
        )
        if current is None:
            raise ContinuityStoreInvariantError("record_relationship_change requires an existing entity")
        before = current.get("relationship_type_before")
        row = self._fetch_one(
            "record_relationship_change",
            f"""
                INSERT INTO entity_relationship_events (
                  id,
                  user_id,
                  entity_id,
                  relationship_type_before,
                  relationship_type_after,
                  changed_at,
                  source_id,
                  metadata_json
                )
                VALUES (
                  gen_random_uuid(),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s::uuid,
                  %s
                )
                RETURNING {ENTITY_RELATIONSHIP_EVENT_COLUMNS}
                """,
            (entity_id, before, relationship_type, changed_at, source_id, _json_object(metadata_json)),
        )
        self._fetch_one(
            "record_relationship_change",
            """
                UPDATE vnext_entities
                SET metadata_json = metadata_json || %s,
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                  AND deleted_at IS NULL
                RETURNING id
                """,
            (_json_object({"relationship_type": relationship_type}), entity_id),
        )
        self._append_mutation_event(
            event_type="entity.relationship_changed",
            actor_type=actor_type,
            target_type="entity",
            target_id=entity_id,
            payload={
                "operation": "record_relationship_change",
                "relationship_type_before": before,
                "relationship_type_after": relationship_type,
                "relationship_event_id": str(row["id"]),
                "source_id": source_id,
            },
        )
        return row

    def list_relationship_events(self, entity_id: str) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {ENTITY_RELATIONSHIP_EVENT_COLUMNS}
                FROM entity_relationship_events
                WHERE entity_id = %s::uuid
                ORDER BY changed_at DESC, id DESC
                """,
            (entity_id,),
        )

    def create_belief(self, belief: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_belief",
            f"""
                INSERT INTO beliefs (
                  id,
                  user_id,
                  memory_id,
                  claim,
                  status,
                  confidence,
                  first_seen_at,
                  last_reinforced_at,
                  last_challenged_at,
                  superseded_by,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s::uuid,
                  %s
                )
                RETURNING {BELIEF_COLUMNS}
                """,
            (
                belief.get("id"),
                belief["memory_id"],
                belief["claim"],
                belief.get("status", "active"),
                belief.get("confidence", 0.5),
                belief.get("first_seen_at"),
                belief.get("last_reinforced_at"),
                belief.get("last_challenged_at"),
                belief.get("superseded_by"),
                _json_object(belief.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="belief.created",
            actor_type=actor_type,
            target_type="belief",
            target_id=row["id"],
            payload={"operation": "create", "memory_id": str(row["memory_id"])},
        )
        return row

    def get_belief(self, belief_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {BELIEF_COLUMNS}
                FROM beliefs
                WHERE id = %s::uuid
                """,
            (belief_id,),
        )

    def list_beliefs(
        self,
        *,
        status: str | None = "active",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        scope_projects: tuple[str, ...] = (),
        scope_people: tuple[str, ...] = (),
        scope_person_memory_ids: tuple[str, ...] = (),
        scope_window_start: datetime | None = None,
        scope_window_end: datetime | None = None,
        limit: int = 8,
    ) -> list[VNextRow]:
        project_list = list(normalize_project_scope(scope_projects)) or None
        people_list = [str(value).strip().casefold() for value in scope_people if str(value).strip()] or None
        person_memory_ids = [str(value) for value in scope_person_memory_ids if str(value)] or None
        return self._fetch_all(
            f"""
                SELECT
                  b.id,
                  b.user_id,
                  b.memory_id,
                  b.claim,
                  b.status,
                  b.confidence,
                  b.first_seen_at,
                  b.last_reinforced_at,
                  b.last_challenged_at,
                  b.superseded_by,
                  b.metadata_json,
                  m.domain,
                  m.sensitivity,
                  m.memory_type,
                  m.canonical_text AS memory_canonical_text
                FROM beliefs b
                JOIN memories m
                  ON m.id = b.memory_id
                 AND m.user_id = b.user_id
                WHERE (%s::text IS NULL OR b.status = %s)
                  AND m.deleted_at IS NULL
                  AND (%s::text[] IS NULL OR m.domain = ANY(%s::text[]) OR m.domain = 'unknown')
                  AND (%s::text[] IS NULL OR m.sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({_SCOPED_MEMORY_PROJECT_SQL}) ?| %s::text[])
                  AND (
                    %s::text[] IS NULL
                    OR m.id::text = ANY(%s::text[])
                    OR {_SCOPED_MEMORY_DIRECT_PEOPLE_SQL}
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_SCOPED_MEMORY_EVENT_TIME_SQL} >= %s::timestamptz
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_SCOPED_MEMORY_EVENT_TIME_SQL} <= %s::timestamptz
                  )
                ORDER BY
                  b.last_challenged_at DESC NULLS LAST,
                  b.last_reinforced_at DESC NULLS LAST,
                  b.first_seen_at DESC,
                  b.id DESC
                LIMIT %s
                """,
            (
                status,
                status,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                project_list,
                project_list,
                people_list,
                person_memory_ids,
                people_list,
                scope_window_start,
                scope_window_start,
                scope_window_end,
                scope_window_end,
                limit,
            ),
        )

    def update_belief_status(
        self,
        *,
        belief_id: str,
        status: str,
        confidence: float | None = None,
        superseded_by: str | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        row = self._fetch_one(
            "update_belief_status",
            f"""
                UPDATE beliefs
                SET status = %s,
                    confidence = COALESCE(%s, confidence),
                    last_reinforced_at = CASE
                      WHEN %s = 'active' THEN clock_timestamp()
                      ELSE last_reinforced_at
                    END,
                    last_challenged_at = CASE
                      WHEN %s = 'challenged' THEN clock_timestamp()
                      ELSE last_challenged_at
                    END,
                    superseded_by = COALESCE(%s::uuid, superseded_by)
                WHERE id = %s::uuid
                RETURNING {BELIEF_COLUMNS}
                """,
            (status, confidence, status, status, superseded_by, belief_id),
        )
        self._append_mutation_event(
            event_type="belief.updated",
            actor_type=actor_type,
            target_type="belief",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def create_open_loop(self, loop: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_open_loop",
            f"""
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
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  COALESCE(%s::timestamptz, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::uuid,
                  %s::uuid,
                  %s::uuid,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                ON CONFLICT DO NOTHING
                RETURNING {OPEN_LOOP_COLUMNS}
                """,
            (
                loop.get("id"),
                loop.get("memory_id"),
                loop["title"],
                loop.get("status", "open"),
                loop.get("opened_at"),
                loop.get("due_at"),
                loop.get("resolved_at"),
                loop.get("resolution_note"),
                loop.get("description"),
                loop.get("priority", "normal"),
                loop.get("project_id"),
                loop.get("person_id"),
                loop.get("source_id"),
                loop.get("closed_at"),
                loop.get("domain", "unknown"),
                loop.get("sensitivity", "unknown"),
                _json_object(loop.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="open_loop.created",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "create", "fields": _sorted_field_names(loop)},
        )
        return row

    def upsert_open_loop_by_automation_digest(
        self,
        loop: JsonObject,
        *,
        digest: str,
        actor_type: str = "system",
    ) -> VNextRow:
        """Create or replay one exact automation-discovered open loop."""

        normalized_digest = str(digest).strip()
        if normalized_digest == "":
            raise ValueError("digest must not be empty")
        existing = self.find_open_loop_by_automation_digest(
            digest=normalized_digest,
            project_id=str(loop["project_id"]) if loop.get("project_id") is not None else None,
            person_id=str(loop["person_id"]) if loop.get("person_id") is not None else None,
        )
        if existing is not None:
            return existing
        metadata_value = loop.get("metadata_json")
        metadata: JsonObject = dict(metadata_value) if isinstance(metadata_value, dict) else {}
        metadata.update(
            {
                "automation_digest": normalized_digest,
                "idempotency_digest": normalized_digest,
            }
        )
        record: JsonObject = {**loop, "metadata_json": metadata}
        try:
            return self.create_open_loop(record, actor_type=actor_type)
        except ContinuityStoreInvariantError:
            existing = self.find_open_loop_by_automation_digest(
                digest=normalized_digest,
                project_id=str(loop["project_id"]) if loop.get("project_id") is not None else None,
                person_id=str(loop["person_id"]) if loop.get("person_id") is not None else None,
            )
            if existing is None:
                raise
            return existing

    def get_open_loop(self, loop_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {OPEN_LOOP_COLUMNS}
                FROM open_loops
                WHERE id = %s::uuid
                """,
            (loop_id,),
        )

    def find_open_loop_by_automation_digest(
        self,
        *,
        digest: str,
        project_id: str | None = None,
        person_id: str | None = None,
    ) -> VNextRow | None:
        """Find an exact automation result with scope predicates in SQL."""
        normalized_digest = str(digest).strip()
        if not normalized_digest:
            return None
        return self._fetch_optional_one(
            f"""
                SELECT {OPEN_LOOP_COLUMNS}
                FROM open_loops
                WHERE COALESCE(
                    metadata_json ->> 'idempotency_digest',
                    metadata_json ->> 'automation_digest'
                  ) = %s
                  AND (%s::uuid IS NULL OR project_id = %s::uuid)
                  AND (%s::uuid IS NULL OR person_id = %s::uuid)
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
            (
                normalized_digest,
                project_id,
                project_id,
                person_id,
                person_id,
            ),
        )

    def list_open_loops_referencing_source(self, *, source_id: str, limit: int = 500) -> list[VNextRow]:
        """Bound open loops related to one source before LIMIT."""

        if limit < 1:
            raise ValueError("limit must be positive")
        source_ref = f"source:{source_id}"
        return self._fetch_all(
            f"""
                SELECT {OPEN_LOOP_COLUMNS}
                FROM open_loops
                WHERE source_id = %s::uuid
                  OR metadata_json ->> 'source_id' = %s
                  OR metadata_json ->> 'source_ref' IN (%s, %s)
                  OR metadata_json -> 'source_ids' ? %s
                  OR metadata_json -> 'source_refs' ? %s
                  OR metadata_json -> 'source_refs' ? %s
                  OR metadata_json -> 'source_references' ? %s
                  OR metadata_json -> 'source_references' ? %s
                  OR metadata_json -> 'selected_source_ids' ? %s
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                source_id,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_ref,
                source_id,
                limit,
            ),
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
        scope_projects: Sequence[str] | None = None,
        scope_people: tuple[str, ...] = (),
        scope_window_start: datetime | None = None,
        scope_window_end: datetime | None = None,
    ) -> list[VNextRow]:
        scope_projects_list = list(normalize_project_scope(scope_projects or ())) or None
        scope_people_list = list(scope_people) or None
        return self._fetch_all(
            f"""
                SELECT {OPEN_LOOP_COLUMNS}
                FROM open_loops
                WHERE (%s::text IS NULL OR status = %s)
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::uuid IS NULL OR project_id = %s::uuid)
                  AND (%s::uuid IS NULL OR person_id = %s::uuid)
                  AND (
                    %s::text[] IS NULL
                    OR ({_OPEN_LOOP_SCOPE_PROJECT_SQL}) ?| %s::text[]
                  )
                  AND (
                    %s::text[] IS NULL
                    OR person_id::text = ANY(%s::text[])
                    OR {_OPEN_LOOP_SCOPE_PEOPLE_SQL}
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_OPEN_LOOP_SCOPE_EVENT_TIME_SQL} >= %s::timestamptz
                  )
                  AND (
                    %s::timestamptz IS NULL
                    OR {_OPEN_LOOP_SCOPE_EVENT_TIME_SQL} <= %s::timestamptz
                  )
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (
                status,
                status,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                project_id,
                project_id,
                person_id,
                person_id,
                scope_projects_list,
                scope_projects_list,
                scope_people_list,
                scope_people_list,
                scope_people_list,
                scope_window_start,
                scope_window_start,
                scope_window_end,
                scope_window_end,
                limit,
            ),
        )

    def update_open_loop(self, *, loop_id: str, patch: JsonObject, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "update_open_loop",
            f"""
                UPDATE open_loops
                SET title = COALESCE(%s, title),
                    description = COALESCE(%s, description),
                    priority = COALESCE(%s, priority),
                    due_at = COALESCE(%s::timestamptz, due_at),
                    project_id = COALESCE(%s::uuid, project_id),
                    person_id = COALESCE(%s::uuid, person_id),
                    domain = COALESCE(%s, domain),
                    sensitivity = COALESCE(%s, sensitivity),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {OPEN_LOOP_COLUMNS}
                """,
            (
                patch.get("title"),
                patch.get("description"),
                patch.get("priority"),
                patch.get("due_at"),
                patch.get("project_id"),
                patch.get("person_id"),
                patch.get("domain"),
                patch.get("sensitivity"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                loop_id,
            ),
        )
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
        row = self._fetch_one(
            "update_open_loop_status",
            f"""
                UPDATE open_loops
                SET status = %s,
                    resolved_at = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE clock_timestamp()
                    END,
                    closed_at = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE clock_timestamp()
                    END,
                    resolution_note = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE %s
                    END,
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {OPEN_LOOP_COLUMNS}
                """,
            (status, status, status, status, resolution_note, loop_id),
        )
        self._append_mutation_event(
            event_type="open_loop.updated",
            actor_type=actor_type,
            target_type="open_loop",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def create_artifact(self, artifact: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_artifact",
            f"""
                INSERT INTO generated_artifacts (
                  id,
                  user_id,
                  artifact_type,
                  title,
                  content_markdown,
                  status,
                  domain,
                  sensitivity,
                  generated_by,
                  prompt_hash,
                  model_info_json,
                  reviewed_at,
                  promoted_at,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::timestamptz,
                  %s
                )
                RETURNING {ARTIFACT_COLUMNS}
                """,
            (
                artifact.get("id"),
                artifact["artifact_type"],
                artifact["title"],
                artifact["content_markdown"],
                artifact.get("status", "draft"),
                artifact.get("domain", "unknown"),
                artifact.get("sensitivity", "unknown"),
                artifact.get("generated_by", actor_type),
                artifact.get("prompt_hash"),
                _json_object(artifact.get("model_info_json")),
                artifact.get("reviewed_at"),
                artifact.get("promoted_at"),
                _json_object(artifact.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="artifact.created",
            actor_type=actor_type,
            target_type="artifact",
            target_id=row["id"],
            payload={"operation": "create", "artifact_type": str(row["artifact_type"])},
        )
        return row

    def upsert_artifact_by_workflow_digest(
        self,
        artifact: JsonObject,
        *,
        workflow: str,
        digest: str,
        actor_type: str = "system",
    ) -> VNextRow:
        """Atomically persist or replay one workflow artifact.

        New writes carry the canonical ``idempotency_digest`` protected by a
        unique partial index.  The fallback lookup also recognizes legacy
        workflow-specific digest keys so upgrades replay an existing result
        without rewriting historical rows.
        """

        normalized_workflow = str(workflow).strip()
        normalized_digest = str(digest).strip()
        if not normalized_workflow or not normalized_digest:
            raise ValueError("workflow and digest must not be empty")
        existing = self.find_artifact_by_workflow_digest(
            artifact_type=str(artifact["artifact_type"]),
            workflow=normalized_workflow,
            digest=normalized_digest,
        )
        if existing is not None:
            return existing
        metadata_value = artifact.get("metadata_json")
        metadata: JsonObject = dict(metadata_value) if isinstance(metadata_value, dict) else {}
        metadata.update(
            {
                "workflow": normalized_workflow,
                "idempotency_digest": normalized_digest,
            }
        )
        row = self._fetch_optional_one(
            f"""
                INSERT INTO generated_artifacts (
                  id,
                  user_id,
                  artifact_type,
                  title,
                  content_markdown,
                  status,
                  domain,
                  sensitivity,
                  generated_by,
                  prompt_hash,
                  model_info_json,
                  reviewed_at,
                  promoted_at,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::timestamptz,
                  %s,
                  %s
                )
                ON CONFLICT DO NOTHING
                RETURNING {ARTIFACT_COLUMNS}
                """,
            (
                artifact.get("id"),
                artifact["artifact_type"],
                artifact["title"],
                artifact["content_markdown"],
                artifact.get("status", "draft"),
                artifact.get("domain", "unknown"),
                artifact.get("sensitivity", "unknown"),
                artifact.get("generated_by", actor_type),
                artifact.get("prompt_hash"),
                _json_object(artifact.get("model_info_json")),
                artifact.get("reviewed_at"),
                artifact.get("promoted_at"),
                _json_object(metadata),
            ),
        )
        created = row is not None
        if row is None:
            row = self.find_artifact_by_workflow_digest(
                artifact_type=str(artifact["artifact_type"]),
                workflow=normalized_workflow,
                digest=normalized_digest,
            )
        if row is None:
            raise ContinuityStoreInvariantError(
                "upsert_artifact_by_workflow_digest could not resolve the persisted artifact"
            )
        if created:
            self._append_mutation_event(
                event_type="artifact.created",
                actor_type=actor_type,
                target_type="artifact",
                target_id=row["id"],
                payload={"operation": "create", "artifact_type": str(row["artifact_type"])},
            )
        return row

    def get_artifact(self, artifact_id: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {ARTIFACT_COLUMNS}
                FROM generated_artifacts
                WHERE id = %s::uuid
                """,
            (artifact_id,),
        )

    def get_artifact_for_update(self, artifact_id: str) -> VNextRow | None:
        """Lock one persisted artifact before an authorized side effect."""

        return self._fetch_optional_one(
            f"""
                SELECT {ARTIFACT_COLUMNS}
                FROM generated_artifacts
                WHERE id = %s::uuid
                FOR UPDATE
                """,
            (artifact_id,),
        )

    def list_artifacts(
        self,
        *,
        artifact_type: str | None = None,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        scope_projects: tuple[str, ...] = (),
        limit: int = 8,
    ) -> list[VNextRow]:
        project_list = list(normalize_project_scope(scope_projects)) or None
        return self._fetch_all(
            f"""
                SELECT {ARTIFACT_COLUMNS}
                FROM generated_artifacts
                WHERE (%s::text IS NULL OR artifact_type = %s)
                  AND (%s::text[] IS NULL OR domain = ANY(%s::text[]) OR domain = 'unknown')
                  AND (%s::text[] IS NULL OR sensitivity = ANY(%s::text[]))
                  AND (%s::text[] IS NULL OR ({_ARTIFACT_SCOPE_PROJECT_SQL}) ?| %s::text[])
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
            (
                artifact_type,
                artifact_type,
                domains,
                domains,
                sensitivity_allowed,
                sensitivity_allowed,
                project_list,
                project_list,
                limit,
            ),
        )

    def list_artifacts_referencing_source(self, *, source_id: str, limit: int = 500) -> list[VNextRow]:
        """Bound artifacts related to one source before ordering and LIMIT."""

        if limit < 1:
            raise ValueError("limit must be positive")
        source_ref = f"source:{source_id}"
        qualified_columns = ", ".join(f"a.{column.strip()}" for column in ARTIFACT_COLUMNS.split(",") if column.strip())
        return self._fetch_all(
            f"""
                SELECT {qualified_columns}
                FROM generated_artifacts AS a
                WHERE (
                  EXISTS (
                    SELECT 1
                    FROM provenance_links AS p
                    WHERE p.target_type = 'artifact'
                      AND p.target_id = a.id::text
                      AND p.source_id = %s::uuid
                  )
                  OR a.metadata_json ->> 'source_id' = %s
                  OR a.metadata_json ->> 'source_ref' IN (%s, %s)
                  OR a.metadata_json -> 'source_ids' ? %s
                  OR a.metadata_json -> 'source_refs' ? %s
                  OR a.metadata_json -> 'source_refs' ? %s
                  OR a.metadata_json -> 'source_references' ? %s
                  OR a.metadata_json -> 'source_references' ? %s
                  OR a.metadata_json -> 'selected_source_ids' ? %s
                )
                ORDER BY a.created_at DESC, a.id DESC
                LIMIT %s
                """,
            (
                source_id,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_id,
                source_ref,
                source_id,
                source_ref,
                source_id,
                limit,
            ),
        )

    def find_artifact_by_workflow_digest(
        self,
        *,
        artifact_type: str,
        workflow: str,
        digest: str,
        scope_projects: Sequence[str] | None = None,
    ) -> VNextRow | None:
        """Find one exact idempotency artifact without scanning a recent prefix."""
        normalized_digest = str(digest).strip()
        if not normalized_digest:
            return None
        project_list = list(normalize_project_scope(scope_projects or ())) or None
        return self._fetch_optional_one(
            f"""
                SELECT {ARTIFACT_COLUMNS}
                FROM generated_artifacts
                WHERE artifact_type = %s
                  AND metadata_json ->> 'workflow' = %s
                  AND COALESCE(
                    metadata_json ->> 'idempotency_digest',
                    metadata_json ->> 'workflow_digest',
                    metadata_json ->> 'automation_digest',
                    metadata_json ->> 'consolidation_digest'
                  ) = %s
                  AND (%s::text[] IS NULL OR ({_ARTIFACT_SCOPE_PROJECT_SQL}) ?| %s::text[])
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
            (
                str(artifact_type),
                str(workflow),
                normalized_digest,
                project_list,
                project_list,
            ),
        )

    def update_artifact_status(
        self,
        *,
        artifact_id: str,
        status: str,
        expected_status: str | None = None,
        metadata_json: JsonObject | None = None,
        actor_type: str = "system",
    ) -> VNextRow | None:
        """Apply a compare-and-set artifact transition.

        ``expected_status`` is optional for compatibility with lower-level
        callers, but review services always provide it after locking the row.
        A lost comparison returns ``None`` instead of overwriting the winner.
        """

        row = self._fetch_optional_one(
            f"""
                UPDATE generated_artifacts
                SET status = %s,
                    reviewed_at = CASE
                      WHEN %s IN ('reviewed', 'accepted', 'rejected') THEN clock_timestamp()
                      ELSE reviewed_at
                    END,
                    promoted_at = CASE
                      WHEN %s = 'promoted_to_memory' THEN clock_timestamp()
                      ELSE promoted_at
                    END,
                    metadata_json = CASE
                      WHEN %s::jsonb IS NULL THEN metadata_json
                      ELSE metadata_json || %s::jsonb
                    END
                WHERE id = %s::uuid
                  AND (%s::text IS NULL OR status = %s)
                RETURNING {ARTIFACT_COLUMNS}
                """,
            (
                status,
                status,
                status,
                _json_object(metadata_json) if metadata_json is not None else None,
                _json_object(metadata_json) if metadata_json is not None else None,
                artifact_id,
                expected_status,
                expected_status,
            ),
        )
        if row is None:
            return None
        self._append_mutation_event(
            event_type="artifact.updated",
            actor_type=actor_type,
            target_type="artifact",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status},
        )
        return row

    def create_artifact_quality_rating(self, rating: JsonObject, *, actor_type: str = "user") -> VNextRow:
        row = self._fetch_one(
            "create_artifact_quality_rating",
            f"""
                INSERT INTO artifact_quality_ratings (
                  id,
                  user_id,
                  artifact_id,
                  reviewer_id,
                  usefulness,
                  accuracy,
                  source_grounding,
                  novel_connections,
                  actionability,
                  hallucination_risk,
                  verbosity,
                  missed_context,
                  comments,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {QUALITY_RATING_COLUMNS}
                """,
            (
                rating.get("id"),
                rating["artifact_id"],
                rating.get("reviewer_id"),
                rating.get("usefulness"),
                rating.get("accuracy"),
                rating.get("source_grounding"),
                rating.get("novel_connections"),
                rating.get("actionability"),
                rating.get("hallucination_risk"),
                rating.get("verbosity"),
                rating.get("missed_context"),
                rating.get("comments"),
                _json_object(rating.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="artifact.quality_rated",
            actor_type=actor_type,
            target_type="artifact",
            target_id=row["artifact_id"],
            payload={
                "operation": "create_quality_rating",
                "quality_rating_id": str(row["id"]),
                "artifact_id": str(row["artifact_id"]),
                "reviewer_id": row.get("reviewer_id"),
            },
        )
        return row

    def list_artifact_quality_ratings(
        self,
        *,
        artifact_id: str | None = None,
        scope_projects: Sequence[str] | None = None,
        limit: int = 100,
    ) -> list[VNextRow]:
        project_list = list(normalize_project_scope(scope_projects or ())) or None
        return self._fetch_all(
            f"""
                SELECT {QUALITY_RATING_COLUMNS}
                FROM artifact_quality_ratings
                WHERE (%s::uuid IS NULL OR artifact_id = %s::uuid)
                  AND (
                    %s::text[] IS NULL
                    OR artifact_id IN (
                      SELECT id
                      FROM generated_artifacts
                      WHERE ({_ARTIFACT_SCOPE_PROJECT_SQL}) ?| %s::text[]
                    )
                  )
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
            (artifact_id, artifact_id, project_list, project_list, limit),
        )

    def create_task(self, task: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "create_task",
            f"""
                INSERT INTO task_queue (
                  id,
                  user_id,
                  title,
                  task_type,
                  instructions,
                  status,
                  requested_by,
                  scope_json,
                  allowed_sources_json,
                  domain,
                  sensitivity,
                  write_policy,
                  scheduled_for,
                  output_artifact_id,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s::uuid,
                  %s
                )
                RETURNING {TASK_COLUMNS}
                """,
            (
                task.get("id"),
                task["title"],
                task["task_type"],
                task["instructions"],
                task.get("status", "pending"),
                task.get("requested_by", actor_type),
                _json_object(task.get("scope_json")),
                _json_list(task.get("allowed_sources_json")),
                task.get("domain", "unknown"),
                task.get("sensitivity", "unknown"),
                task.get("write_policy", "proposal_only"),
                task.get("scheduled_for"),
                task.get("output_artifact_id"),
                _json_object(task.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="task.created",
            actor_type=actor_type,
            target_type="task",
            target_id=row["id"],
            payload={"operation": "create", "task_type": str(row["task_type"])},
        )
        return row

    def claim_next_task(self, *, actor_type: str = "system") -> VNextRow | None:
        row = self._fetch_optional_one(
            f"""
                WITH next_task AS (
                  SELECT id
                  FROM task_queue
                  WHERE status = 'pending'
                    AND (scheduled_for IS NULL OR scheduled_for <= clock_timestamp())
                  ORDER BY scheduled_for ASC NULLS FIRST, created_at ASC, id ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE task_queue
                SET status = 'running',
                    started_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                FROM next_task
                WHERE task_queue.id = next_task.id
                RETURNING {TASK_COLUMNS}
                """
        )
        if row is not None:
            self._append_mutation_event(
                event_type="task.claimed",
                actor_type=actor_type,
                target_type="task",
                target_id=row["id"],
                payload={"operation": "claim"},
            )
        return row

    def update_task_status(
        self,
        *,
        task_id: str,
        status: str,
        details: JsonObject | None = None,
        actor_type: str = "system",
    ) -> VNextRow:
        details = details or {}
        row = self._fetch_one(
            "update_task_status",
            f"""
                UPDATE task_queue
                SET status = %s,
                    completed_at = CASE
                      WHEN %s = 'completed' THEN clock_timestamp()
                      ELSE completed_at
                    END,
                    failed_at = CASE
                      WHEN %s = 'failed' THEN clock_timestamp()
                      ELSE failed_at
                    END,
                    error_message = COALESCE(%s, error_message),
                    output_artifact_id = COALESCE(%s::uuid, output_artifact_id),
                    metadata_json = COALESCE(%s, metadata_json),
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {TASK_COLUMNS}
                """,
            (
                status,
                status,
                status,
                details.get("error_message"),
                details.get("output_artifact_id"),
                _json_object(details["metadata_json"]) if "metadata_json" in details else None,
                task_id,
            ),
        )
        self._append_mutation_event(
            event_type="task.updated",
            actor_type=actor_type,
            target_type="task",
            target_id=row["id"],
            payload={"operation": "update_status", "status": status, "details": details},
        )
        return row

    def list_tasks(self, *, status: str | None = None, limit: int = 8) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {TASK_COLUMNS}
                FROM task_queue
                WHERE (%s::text IS NULL OR status = %s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (status, status, limit),
        )

    def upsert_brain_charter(self, charter: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_one(
            "upsert_brain_charter",
            f"""
                INSERT INTO brain_charters (
                  id,
                  user_id,
                  content_markdown,
                  owner_json,
                  memory_philosophy_json,
                  life_domains_json,
                  active_projects_json,
                  communication_style_json,
                  priorities_json,
                  autonomous_rules_json,
                  quality_standard_json,
                  sensitivity
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id)
                DO UPDATE SET
                  content_markdown = EXCLUDED.content_markdown,
                  owner_json = EXCLUDED.owner_json,
                  memory_philosophy_json = EXCLUDED.memory_philosophy_json,
                  life_domains_json = EXCLUDED.life_domains_json,
                  active_projects_json = EXCLUDED.active_projects_json,
                  communication_style_json = EXCLUDED.communication_style_json,
                  priorities_json = EXCLUDED.priorities_json,
                  autonomous_rules_json = EXCLUDED.autonomous_rules_json,
                  quality_standard_json = EXCLUDED.quality_standard_json,
                  sensitivity = EXCLUDED.sensitivity,
                  updated_at = clock_timestamp()
                RETURNING {BRAIN_CHARTER_COLUMNS}
                """,
            (
                charter.get("id"),
                charter["content_markdown"],
                _json_object(charter.get("owner_json")),
                _json_object(charter.get("memory_philosophy_json")),
                _json_object(charter.get("life_domains_json")),
                _json_list(charter.get("active_projects_json")),
                _json_object(charter.get("communication_style_json")),
                _json_object(charter.get("priorities_json")),
                _json_list(charter.get("autonomous_rules_json")),
                _json_list(charter.get("quality_standard_json")),
                charter.get("sensitivity", "private"),
            ),
        )
        self._append_mutation_event(
            event_type="brain_charter.upserted",
            actor_type=actor_type,
            target_type="brain_charter",
            target_id=row["id"],
            payload={"operation": "upsert", "fields": _sorted_field_names(charter)},
        )
        return row

    def get_brain_charter(self) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {BRAIN_CHARTER_COLUMNS}
                FROM brain_charters
                LIMIT 1
                """
        )

    def upsert_agent_identity(self, agent: JsonObject, *, actor_type: str = "agent") -> VNextRow:
        row = self._fetch_one(
            "upsert_agent_identity",
            f"""
                INSERT INTO agent_identities (
                  id,
                  user_id,
                  agent_id,
                  agent_type,
                  permission_profile,
                  display_name,
                  project_scope_json,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, agent_id)
                DO UPDATE SET
                  agent_type = EXCLUDED.agent_type,
                  permission_profile = EXCLUDED.permission_profile,
                  display_name = COALESCE(EXCLUDED.display_name, agent_identities.display_name),
                  project_scope_json = EXCLUDED.project_scope_json,
                  metadata_json = agent_identities.metadata_json || EXCLUDED.metadata_json,
                  updated_at = clock_timestamp()
                RETURNING {AGENT_IDENTITY_COLUMNS}
                """,
            (
                agent.get("id"),
                agent["agent_id"],
                agent.get("agent_type", "unknown"),
                agent.get("permission_profile", "read_only_agent"),
                agent.get("display_name"),
                _json_list(agent.get("project_scope_json") or agent.get("project_scope")),
                _json_object(agent.get("metadata_json")),
            ),
        )
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
                SELECT {AGENT_IDENTITY_COLUMNS}
                FROM agent_identities
                ORDER BY updated_at DESC, id DESC
                LIMIT %s
                """,
            (limit,),
        )

    def list_agent_events(self, *, agent_id: str | None = None, limit: int = 50) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {EVENT_LOG_COLUMNS}
                FROM event_log
                WHERE actor_type = 'agent'
                  AND (%s::text IS NULL OR actor_id = %s)
                ORDER BY occurred_at DESC, id DESC
                LIMIT %s
                """,
            (agent_id, agent_id, limit),
        )

    def list_agent_policy_artifacts(
        self,
        *,
        agent_id: str | None = None,
        limit: int = 200,
    ) -> list[VNextRow]:
        """Bound only agent-generated artifacts for policy telemetry."""

        if limit < 1:
            raise ValueError("limit must be positive")
        return self._fetch_all(
            f"""
                SELECT {ARTIFACT_COLUMNS}
                FROM generated_artifacts
                WHERE metadata_json ->> 'generated_by' = 'agent'
                  AND (%s::text IS NULL OR metadata_json ->> 'agent_id' = %s)
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
            (agent_id, agent_id, limit),
        )

    def list_agent_policy_memories(
        self,
        *,
        agent_id: str | None = None,
        limit: int = 200,
    ) -> list[VNextRow]:
        """Bound only agent-attributed memory proposals for telemetry."""

        if limit < 1:
            raise ValueError("limit must be positive")
        return self._fetch_all(
            f"""
                SELECT {MEMORY_COLUMNS}
                FROM memories
                WHERE deleted_at IS NULL
                  AND metadata_json ->> 'agent_id' IS NOT NULL
                  AND (%s::text IS NULL OR metadata_json ->> 'agent_id' = %s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
            (agent_id, agent_id, limit),
        )

    def create_agent_api_key(self, key: JsonObject, *, actor_type: str = "user") -> VNextRow:
        row = self._fetch_one(
            "create_agent_api_key",
            f"""
                INSERT INTO agent_api_keys (
                  id,
                  user_id,
                  agent_id,
                  permission_profile,
                  project_scope,
                  key_hash,
                  key_prefix,
                  label
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {AGENT_API_KEY_COLUMNS}
                """,
            (
                key.get("id"),
                key["agent_id"],
                key["permission_profile"],
                key.get("project_scope"),
                key["key_hash"],
                key["key_prefix"],
                key.get("label"),
            ),
        )
        self._append_mutation_event(
            event_type="agent.key_created",
            actor_type=actor_type,
            target_type="agent_api_key",
            target_id=row["id"],
            payload={
                "operation": "create",
                "agent_id": str(row["agent_id"]),
                "permission_profile": str(row["permission_profile"]),
                "project_scope": row.get("project_scope"),
                "key_prefix": str(row["key_prefix"]),
                "label": row.get("label"),
            },
        )
        return row

    def get_agent_api_key_by_hash(self, key_hash: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {AGENT_API_KEY_COLUMNS}
                FROM agent_api_keys
                WHERE key_hash = %s
                """,
            (key_hash,),
        )

    def list_agent_api_keys(self, *, limit: int = 50) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {AGENT_API_KEY_COLUMNS}
                FROM agent_api_keys
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
            (limit,),
        )

    def revoke_agent_api_key(self, *, key_id: str, actor_type: str = "user") -> VNextRow | None:
        row = self._fetch_optional_one(
            f"""
                UPDATE agent_api_keys
                SET revoked_at = clock_timestamp()
                WHERE id = %s::uuid
                  AND revoked_at IS NULL
                RETURNING {AGENT_API_KEY_COLUMNS}
                """,
            (key_id,),
        )
        if row is None:
            return None
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
        return self._fetch_one(
            "touch_agent_api_key",
            f"""
                UPDATE agent_api_keys
                SET last_used_at = clock_timestamp()
                WHERE id = %s::uuid
                RETURNING {AGENT_API_KEY_COLUMNS}
                """,
            (key_id,),
        )

    def count_active_agent_api_keys(self) -> int:
        row = self._fetch_one(
            "count_active_agent_api_keys",
            """
                SELECT count(*) AS active_count
                FROM agent_api_keys
                WHERE revoked_at IS NULL
                """,
        )
        return int(cast(int, row["active_count"]))

    def upsert_scheduler_workflow(self, workflow: JsonObject, *, actor_type: str = "system") -> VNextRow:
        row = self._fetch_optional_one(
            f"""
                INSERT INTO scheduler_workflows (
                  id,
                  user_id,
                  workflow_type,
                  enabled,
                  paused,
                  schedule_json,
                  timezone,
                  next_run_at,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  COALESCE(%s, false),
                  COALESCE(%s, false),
                  %s,
                  COALESCE(%s, 'UTC'),
                  %s,
                  %s
                )
                ON CONFLICT (user_id, workflow_type)
                DO UPDATE SET
                  enabled = EXCLUDED.enabled,
                  paused = EXCLUDED.paused,
                  schedule_json = EXCLUDED.schedule_json,
                  timezone = EXCLUDED.timezone,
                  next_run_at = EXCLUDED.next_run_at,
                  metadata_json = scheduler_workflows.metadata_json || EXCLUDED.metadata_json,
                  claim_token = NULL,
                  claim_version = scheduler_workflows.claim_version + 1,
                  claim_expires_at = NULL,
                  updated_at = clock_timestamp()
                WHERE scheduler_workflows.enabled IS DISTINCT FROM EXCLUDED.enabled
                   OR scheduler_workflows.paused IS DISTINCT FROM EXCLUDED.paused
                   OR scheduler_workflows.schedule_json IS DISTINCT FROM EXCLUDED.schedule_json
                   OR scheduler_workflows.timezone IS DISTINCT FROM EXCLUDED.timezone
                   OR scheduler_workflows.next_run_at IS DISTINCT FROM EXCLUDED.next_run_at
                   OR NOT (scheduler_workflows.metadata_json @> EXCLUDED.metadata_json)
                RETURNING {SCHEDULER_WORKFLOW_COLUMNS}
                """,
            (
                workflow.get("id"),
                workflow["workflow_type"],
                workflow.get("enabled"),
                workflow.get("paused"),
                _json_object(workflow.get("schedule_json")),
                workflow.get("timezone"),
                workflow.get("next_run_at"),
                _json_object(workflow.get("metadata_json")),
            ),
        )
        mutated = row is not None
        if row is None:
            row = self.get_scheduler_workflow(str(workflow["workflow_type"]))
        if row is None:
            raise ContinuityStoreInvariantError("upsert_scheduler_workflow could not resolve the persisted workflow")
        if mutated:
            self._append_mutation_event(
                event_type="scheduler.workflow_upserted",
                actor_type=actor_type,
                target_type="scheduler_workflow",
                target_id=row["id"],
                payload={
                    "operation": "upsert",
                    "workflow_type": str(row["workflow_type"]),
                    "enabled": bool(row["enabled"]),
                    "paused": bool(row["paused"]),
                },
            )
        return row

    def update_scheduler_workflow(
        self, *, workflow_type: str, patch: JsonObject, actor_type: str = "system"
    ) -> VNextRow:
        result_keys = {
            "last_run_id",
            "last_run_at",
            "last_result",
            "last_error",
            "next_run_at",
        }
        preserve_live_claim = "last_run_id" in patch and set(patch) <= result_keys
        row = self._fetch_one(
            "update_scheduler_workflow",
            f"""
                UPDATE scheduler_workflows
                SET enabled = COALESCE(%s, enabled),
                    paused = COALESCE(%s, paused),
                    schedule_json = COALESCE(%s, schedule_json),
                    timezone = COALESCE(%s, timezone),
                    next_run_at = CASE
                      WHEN %s THEN %s::timestamptz
                      ELSE next_run_at
                    END,
                    last_run_id = COALESCE(%s::uuid, last_run_id),
                    last_run_at = COALESCE(%s::timestamptz, last_run_at),
                    last_result = COALESCE(%s, last_result),
                    last_error = CASE
                      WHEN %s THEN %s
                      ELSE last_error
                    END,
                    metadata_json = COALESCE(%s, metadata_json),
                    claim_token = CASE WHEN %s THEN claim_token ELSE NULL END,
                    claim_version = claim_version + CASE WHEN %s THEN 0 ELSE 1 END,
                    claim_expires_at = CASE WHEN %s THEN claim_expires_at ELSE NULL END,
                    updated_at = clock_timestamp()
                WHERE workflow_type = %s
                RETURNING {SCHEDULER_WORKFLOW_COLUMNS}
                """,
            (
                patch.get("enabled"),
                patch.get("paused"),
                _json_object(patch["schedule_json"]) if "schedule_json" in patch else None,
                patch.get("timezone"),
                "next_run_at" in patch,
                patch.get("next_run_at"),
                patch.get("last_run_id"),
                patch.get("last_run_at"),
                patch.get("last_result"),
                "last_error" in patch,
                patch.get("last_error"),
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                preserve_live_claim,
                preserve_live_claim,
                preserve_live_claim,
                workflow_type,
            ),
        )
        self._append_mutation_event(
            event_type="scheduler.workflow_updated",
            actor_type=actor_type,
            target_type="scheduler_workflow",
            target_id=row["id"],
            payload={"operation": "update", "workflow_type": workflow_type, "changes": patch},
        )
        return row

    def get_scheduler_workflow(self, workflow_type: str) -> VNextRow | None:
        return self._fetch_optional_one(
            f"""
                SELECT {SCHEDULER_WORKFLOW_COLUMNS}
                FROM scheduler_workflows
                WHERE workflow_type = %s
                """,
            (workflow_type,),
        )

    def list_scheduler_workflows(self) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SCHEDULER_WORKFLOW_COLUMNS}
                FROM scheduler_workflows
                ORDER BY workflow_type ASC
                """
        )

    def create_scheduler_run(self, run: JsonObject, *, actor_type: str = "scheduler") -> VNextRow:
        row = self._fetch_one(
            "create_scheduler_run",
            f"""
                INSERT INTO scheduler_runs (
                  id,
                  user_id,
                  workflow_id,
                  workflow_type,
                  status,
                  triggered_by,
                  trace_id,
                  claim_token,
                  claim_version,
                  claim_expires_at,
                  scheduled_for,
                  policy_decision_json,
                  agent_identity_json,
                  metadata_json
                )
                VALUES (
                  COALESCE(%s::uuid, gen_random_uuid()),
                  app.current_user_id(),
                  %s::uuid,
                  %s,
                  COALESCE(%s, 'started'),
                  COALESCE(%s, 'scheduler'),
                  %s,
                  %s,
                  COALESCE(%s, 0),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING {SCHEDULER_RUN_COLUMNS}
                """,
            (
                run.get("id"),
                run.get("workflow_id"),
                run["workflow_type"],
                run.get("status"),
                run.get("triggered_by"),
                run["trace_id"],
                run.get("claim_token"),
                run.get("claim_version"),
                run.get("claim_expires_at"),
                run.get("scheduled_for"),
                _json_object(run.get("policy_decision_json")),
                _json_object(run.get("agent_identity_json")),
                _json_object(run.get("metadata_json")),
            ),
        )
        self._append_mutation_event(
            event_type="scheduler.run_started",
            actor_type=actor_type,
            target_type="scheduler_run",
            target_id=row["id"],
            trace_id=str(row["trace_id"]),
            run_id=str(row["id"]),
            payload={"workflow_type": str(row["workflow_type"]), "triggered_by": str(row["triggered_by"])},
        )
        return row

    def update_scheduler_run(self, *, run_id: str, patch: JsonObject, actor_type: str = "scheduler") -> VNextRow:
        row = self._fetch_one(
            "update_scheduler_run",
            f"""
                UPDATE scheduler_runs
                SET status = COALESCE(%s, status),
                    finished_at = CASE
                      WHEN %s IN ('succeeded', 'failed') THEN clock_timestamp()
                      ELSE finished_at
                    END,
                    artifact_id = COALESCE(%s::uuid, artifact_id),
                    error_message = COALESCE(%s, error_message),
                    policy_decision_json = COALESCE(%s, policy_decision_json),
                    agent_identity_json = COALESCE(%s, agent_identity_json),
                    metadata_json = CASE
                      WHEN %s::jsonb IS NULL THEN metadata_json
                      ELSE metadata_json || %s::jsonb
                    END
                WHERE id = %s::uuid
                RETURNING {SCHEDULER_RUN_COLUMNS}
                """,
            (
                patch.get("status"),
                patch.get("status"),
                patch.get("artifact_id"),
                patch.get("error_message"),
                _json_object(patch["policy_decision_json"]) if "policy_decision_json" in patch else None,
                _json_object(patch["agent_identity_json"]) if "agent_identity_json" in patch else None,
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                _json_object(patch["metadata_json"]) if "metadata_json" in patch else None,
                run_id,
            ),
        )
        event_type = (
            "scheduler.run_succeeded"
            if row["status"] == "succeeded"
            else "scheduler.run_failed"
            if row["status"] == "failed"
            else "scheduler.run_updated"
        )
        self._append_mutation_event(
            event_type=event_type,
            actor_type=actor_type,
            target_type="scheduler_run",
            target_id=row["id"],
            trace_id=str(row["trace_id"]),
            run_id=str(row["id"]),
            payload={
                "workflow_type": str(row["workflow_type"]),
                "status": str(row["status"]),
                "artifact_id": str(row["artifact_id"]) if row.get("artifact_id") is not None else None,
                "error_message": row.get("error_message"),
            },
        )
        return row

    def list_scheduler_runs(self, *, workflow_type: str | None = None, limit: int = 20) -> list[VNextRow]:
        return self._fetch_all(
            f"""
                SELECT {SCHEDULER_RUN_COLUMNS}
                FROM scheduler_runs
                WHERE (%s::text IS NULL OR workflow_type = %s)
                ORDER BY started_at DESC, id DESC
                LIMIT %s
                """,
            (workflow_type, workflow_type, limit),
        )

    def claim_due_scheduler_workflow(
        self,
        *,
        checked_at: datetime,
        lease_expires_at: datetime,
        triggered_by: str,
        policy_decision_json: JsonObject | None = None,
        agent_identity_json: JsonObject | None = None,
    ) -> VNextRow | None:
        """Atomically claim the next due workflow and create its durable run."""

        candidate = self._fetch_optional_one(
            f"""
                SELECT {SCHEDULER_WORKFLOW_COLUMNS}
                FROM scheduler_workflows
                WHERE enabled = true
                  AND paused = false
                  AND next_run_at IS NOT NULL
                  AND next_run_at <= %s::timestamptz
                  AND (claim_expires_at IS NULL OR claim_expires_at <= %s::timestamptz)
                ORDER BY next_run_at ASC, workflow_type ASC, id ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """,
            (checked_at, checked_at),
        )
        if candidate is None:
            return None
        workflow_type = str(candidate["workflow_type"])
        if not self.try_scheduler_workflow_lock(workflow_type):
            return None
        # Re-read after both locks.  A configuration transaction may have
        # changed enabled/paused/next_run_at between the daemon's snapshot and
        # this claim attempt.
        current = self._fetch_optional_one(
            f"""
                SELECT {SCHEDULER_WORKFLOW_COLUMNS}
                FROM scheduler_workflows
                WHERE id = %s::uuid
                  AND enabled = true
                  AND paused = false
                  AND next_run_at IS NOT NULL
                  AND next_run_at <= %s::timestamptz
                  AND (claim_expires_at IS NULL OR claim_expires_at <= %s::timestamptz)
                FOR UPDATE
                """,
            (str(candidate["id"]), checked_at, checked_at),
        )
        if current is None:
            return None
        scheduled_for = current["next_run_at"]
        claim_token = str(uuid4())
        claimed_workflow = self._fetch_one(
            "claim_due_scheduler_workflow",
            f"""
                UPDATE scheduler_workflows
                SET claim_token = %s,
                    claim_version = claim_version + 1,
                    claim_expires_at = %s::timestamptz,
                    updated_at = clock_timestamp()
                WHERE id = %s::uuid
                  AND enabled = true
                  AND paused = false
                  AND next_run_at = %s::timestamptz
                  AND (claim_expires_at IS NULL OR claim_expires_at <= %s::timestamptz)
                RETURNING {SCHEDULER_WORKFLOW_COLUMNS}
                """,
            (
                claim_token,
                lease_expires_at,
                str(current["id"]),
                scheduled_for,
                checked_at,
            ),
        )
        claim_version = int(cast(int, claimed_workflow["claim_version"]))
        trace_id = str(uuid4())
        run = self.create_scheduler_run(
            {
                "workflow_id": claimed_workflow["id"],
                "workflow_type": workflow_type,
                "status": "started",
                "triggered_by": triggered_by,
                "trace_id": trace_id,
                "claim_token": claim_token,
                "claim_version": claim_version,
                "claim_expires_at": lease_expires_at,
                "scheduled_for": scheduled_for,
                "policy_decision_json": policy_decision_json or {},
                "agent_identity_json": agent_identity_json or {},
                "metadata_json": {
                    "durable_claim": True,
                    "scheduled_for": scheduled_for,
                },
            },
            actor_type=triggered_by,
        )
        return {
            "workflow": claimed_workflow,
            "run": run,
            "claim_token": claim_token,
            "claim_version": claim_version,
            "claim_expires_at": lease_expires_at,
            "scheduled_for": scheduled_for,
        }

    def heartbeat_scheduler_claim(
        self,
        *,
        run_id: str,
        claim_token: str,
        claim_version: int,
        lease_expires_at: datetime,
    ) -> bool:
        row = self._fetch_one(
            "heartbeat_scheduler_claim",
            """
                WITH eligible AS (
                  SELECT r.id AS run_id, r.workflow_id
                  FROM scheduler_runs AS r
                  JOIN scheduler_workflows AS w
                    ON w.id = r.workflow_id
                   AND w.user_id = r.user_id
                  WHERE r.id = %s::uuid
                    AND r.status = 'started'
                    AND r.claim_token = %s
                    AND r.claim_version = %s
                    AND r.claim_expires_at > clock_timestamp()
                    AND w.claim_token = %s
                    AND w.claim_version = %s
                    AND w.claim_expires_at > clock_timestamp()
                  FOR UPDATE OF r, w
                ),
                updated_run AS (
                  UPDATE scheduler_runs AS r
                  SET claim_expires_at = %s::timestamptz
                  FROM eligible AS e
                  WHERE r.id = e.run_id
                  RETURNING r.id
                ),
                updated_workflow AS (
                  UPDATE scheduler_workflows AS w
                  SET claim_expires_at = %s::timestamptz,
                      updated_at = clock_timestamp()
                  FROM eligible AS e
                  WHERE w.id = e.workflow_id
                    AND EXISTS (SELECT 1 FROM updated_run)
                  RETURNING w.id
                )
                SELECT (
                  EXISTS (SELECT 1 FROM updated_run)
                  AND EXISTS (SELECT 1 FROM updated_workflow)
                ) AS renewed
                """,
            (
                run_id,
                claim_token,
                claim_version,
                claim_token,
                claim_version,
                lease_expires_at,
                lease_expires_at,
            ),
        )
        return bool(row.get("renewed"))

    def lock_scheduler_claim_for_publish(
        self,
        *,
        run_id: str,
        claim_token: str,
        claim_version: int,
    ) -> bool:
        """Lock and validate the live claim before publishing staged writes."""

        row = self._fetch_optional_one(
            """
                SELECT r.id AS run_id
                FROM scheduler_runs AS r
                JOIN scheduler_workflows AS w
                  ON w.id = r.workflow_id
                 AND w.user_id = r.user_id
                WHERE r.id = %s::uuid
                  AND r.status = 'started'
                  AND r.claim_token = %s
                  AND r.claim_version = %s
                  AND r.claim_expires_at > clock_timestamp()
                  AND w.claim_token = %s
                  AND w.claim_version = %s
                  AND w.claim_expires_at > clock_timestamp()
                FOR UPDATE OF r, w
                """,
            (
                run_id,
                claim_token,
                claim_version,
                claim_token,
                claim_version,
            ),
        )
        return row is not None

    def finalize_scheduler_claim(
        self,
        *,
        run_id: str,
        claim_token: str,
        claim_version: int,
        status: str,
        artifact_id: str | None,
        error_message: str | None,
        next_run_at: str | None,
        metadata_json: JsonObject,
        actor_type: str = "scheduler",
    ) -> VNextRow | None:
        """Finalize only the still-live matching scheduler fence."""

        if status not in {"succeeded", "failed"}:
            raise ValueError("status must be succeeded or failed")
        row = self._fetch_optional_one(
            f"""
                WITH eligible AS (
                  SELECT r.id AS run_id, r.workflow_id
                  FROM scheduler_runs AS r
                  JOIN scheduler_workflows AS w
                    ON w.id = r.workflow_id
                   AND w.user_id = r.user_id
                  WHERE r.id = %s::uuid
                    AND r.status = 'started'
                    AND r.claim_token = %s
                    AND r.claim_version = %s
                    AND r.claim_expires_at > clock_timestamp()
                    AND w.claim_token = %s
                    AND w.claim_version = %s
                    AND w.claim_expires_at > clock_timestamp()
                  FOR UPDATE OF r, w
                ),
                updated_run AS (
                  UPDATE scheduler_runs AS r
                  SET status = %s,
                      finished_at = clock_timestamp(),
                      artifact_id = %s::uuid,
                      error_message = %s,
                      claim_token = NULL,
                      claim_expires_at = NULL,
                      metadata_json = r.metadata_json || %s::jsonb
                  FROM eligible AS e
                  WHERE r.id = e.run_id
                  RETURNING r.*
                ),
                updated_workflow AS (
                  UPDATE scheduler_workflows AS w
                  SET last_run_id = r.id,
                      last_run_at = r.finished_at,
                      last_result = r.status,
                      last_error = r.error_message,
                      next_run_at = %s::timestamptz,
                      claim_token = NULL,
                      claim_expires_at = NULL,
                      updated_at = clock_timestamp()
                  FROM updated_run AS r
                  WHERE w.id = r.workflow_id
                    AND w.claim_token = %s
                    AND w.claim_version = %s
                  RETURNING w.id
                )
                SELECT {SCHEDULER_RUN_COLUMNS}
                FROM updated_run
                WHERE EXISTS (SELECT 1 FROM updated_workflow)
                """,
            (
                run_id,
                claim_token,
                claim_version,
                claim_token,
                claim_version,
                status,
                artifact_id,
                error_message,
                _json_object(metadata_json),
                next_run_at,
                claim_token,
                claim_version,
            ),
        )
        if row is None:
            return None
        self._append_mutation_event(
            event_type="scheduler.run_succeeded" if status == "succeeded" else "scheduler.run_failed",
            actor_type=actor_type,
            target_type="scheduler_run",
            target_id=row["id"],
            trace_id=str(row["trace_id"]),
            run_id=str(row["id"]),
            payload={
                "workflow_type": str(row["workflow_type"]),
                "status": status,
                "artifact_id": artifact_id,
                "error_message": error_message,
                "claim_version": claim_version,
            },
        )
        return row

    def reap_expired_scheduler_claims(
        self,
        *,
        reference_time: datetime,
        limit: int = 100,
        actor_type: str = "scheduler",
    ) -> list[VNextRow]:
        """Fence abandoned runs and release their workflow leases."""

        if limit < 1:
            raise ValueError("limit must be positive")
        rows = self._fetch_all(
            f"""
                WITH expired AS MATERIALIZED (
                  SELECT r.id, r.workflow_id, r.claim_token, r.claim_version
                  FROM scheduler_runs AS r
                  WHERE r.status = 'started'
                    AND r.claim_token IS NOT NULL
                    AND r.claim_expires_at <= %s::timestamptz
                  ORDER BY r.claim_expires_at ASC, r.id ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT %s
                ),
                updated_runs AS (
                  UPDATE scheduler_runs AS r
                  SET status = 'failed',
                      finished_at = clock_timestamp(),
                      error_message = COALESCE(r.error_message, 'scheduler claim lease expired'),
                      claim_token = NULL,
                      claim_expires_at = NULL,
                      metadata_json = r.metadata_json || jsonb_build_object(
                        'claim_reaped', true,
                        'claim_reaped_at', %s::timestamptz
                      )
                  FROM expired AS e
                  WHERE r.id = e.id
                    AND r.status = 'started'
                    AND r.claim_token = e.claim_token
                    AND r.claim_version = e.claim_version
                  RETURNING r.*, e.claim_token AS expired_claim_token,
                    e.claim_version AS expired_claim_version
                ),
                cleared_workflows AS (
                  UPDATE scheduler_workflows AS w
                  SET last_run_id = r.id,
                      last_run_at = r.finished_at,
                      last_result = 'failed',
                      last_error = r.error_message,
                      claim_token = NULL,
                      claim_expires_at = NULL,
                      updated_at = clock_timestamp()
                  FROM updated_runs AS r
                  WHERE w.id = r.workflow_id
                    AND w.claim_token = r.expired_claim_token
                    AND w.claim_version = r.expired_claim_version
                  RETURNING w.id
                )
                SELECT {SCHEDULER_RUN_COLUMNS}
                FROM updated_runs
                ORDER BY finished_at ASC, id ASC
                """,
            (reference_time, limit, reference_time),
        )
        for row in rows:
            self._append_mutation_event(
                event_type="scheduler.run_failed",
                actor_type=actor_type,
                target_type="scheduler_run",
                target_id=row["id"],
                trace_id=str(row["trace_id"]),
                run_id=str(row["id"]),
                payload={
                    "workflow_type": str(row["workflow_type"]),
                    "status": "failed",
                    "error_message": row.get("error_message"),
                    "claim_reaped": True,
                },
            )
        return rows

    def try_scheduler_workflow_lock(self, workflow_type: str) -> bool:
        row = self._fetch_one(
            "try_scheduler_workflow_lock",
            """
                SELECT pg_try_advisory_xact_lock(
                  hashtextextended(
                    concat_ws(':', 'vnext_scheduler', app.current_user_id()::text, %s::text),
                    17
                  )
                ) AS acquired
                """,
            (workflow_type,),
        )
        return bool(row.get("acquired"))


__all__ = [
    "PostgresVNextStore",
    "VNextRow",
]
