from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict, TypeVar, cast
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]
RowT = TypeVar("RowT")


class UserRow(TypedDict):
    id: UUID
    email: str
    display_name: str | None
    created_at: datetime


class ThreadRow(TypedDict):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class SessionRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class EventRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    session_id: UUID | None
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: datetime


class TraceRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    kind: str
    compiler_version: str
    status: str
    limits: JsonObject
    created_at: datetime


class TraceEventRow(TypedDict):
    id: UUID
    user_id: UUID
    trace_id: UUID
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: datetime


class TraceReviewRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    kind: str
    compiler_version: str
    status: str
    limits: JsonObject
    created_at: datetime
    trace_event_count: int


class MemoryRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_key: str
    value: JsonValue
    status: str
    source_event_ids: list[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MemoryRevisionRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    sequence_no: int
    action: str
    memory_key: str
    previous_value: JsonValue | None
    new_value: JsonValue | None
    source_event_ids: list[str]
    candidate: JsonObject
    created_at: datetime


class MemoryReviewLabelRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    label: str
    note: str | None
    created_at: datetime


class EmbeddingConfigRow(TypedDict):
    id: UUID
    user_id: UUID
    provider: str
    model: str
    version: str
    dimensions: int
    status: str
    metadata: JsonObject
    created_at: datetime


class MemoryEmbeddingRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_id: UUID
    embedding_config_id: UUID
    dimensions: int
    vector: list[float]
    created_at: datetime
    updated_at: datetime


class SemanticMemoryRetrievalRow(TypedDict):
    id: UUID
    user_id: UUID
    memory_key: str
    value: JsonValue
    status: str
    source_event_ids: list[str]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    score: float


class EntityRow(TypedDict):
    id: UUID
    user_id: UUID
    entity_type: str
    name: str
    source_memory_ids: list[str]
    created_at: datetime


class EntityEdgeRow(TypedDict):
    id: UUID
    user_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    valid_from: datetime | None
    valid_to: datetime | None
    source_memory_ids: list[str]
    created_at: datetime


class ConsentRow(TypedDict):
    id: UUID
    user_id: UUID
    consent_key: str
    status: str
    metadata: JsonObject
    created_at: datetime
    updated_at: datetime


class PolicyRow(TypedDict):
    id: UUID
    user_id: UUID
    name: str
    action: str
    scope: str
    effect: str
    priority: int
    active: bool
    conditions: JsonObject
    required_consents: list[str]
    created_at: datetime
    updated_at: datetime


class ToolRow(TypedDict):
    id: UUID
    user_id: UUID
    tool_key: str
    name: str
    description: str
    version: str
    metadata_version: str
    active: bool
    tags: list[str]
    action_hints: list[str]
    scope_hints: list[str]
    domain_hints: list[str]
    risk_hints: list[str]
    metadata: JsonObject
    created_at: datetime


class ApprovalRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    task_step_id: UUID | None
    status: str
    request: JsonObject
    tool: JsonObject
    routing: JsonObject
    routing_trace_id: UUID
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None


class TaskRow(TypedDict):
    id: UUID
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    status: str
    request: JsonObject
    tool: JsonObject
    latest_approval_id: UUID | None
    latest_execution_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TaskWorkspaceRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    status: str
    local_path: str
    created_at: datetime
    updated_at: datetime


class GmailAccountRow(TypedDict):
    id: UUID
    user_id: UUID
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: datetime
    updated_at: datetime


class CalendarAccountRow(TypedDict):
    id: UUID
    user_id: UUID
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: datetime
    updated_at: datetime


class ProtectedGmailCredentialRow(TypedDict):
    gmail_account_id: UUID
    user_id: UUID
    auth_kind: str
    credential_kind: str
    secret_manager_kind: str
    secret_ref: str | None
    credential_blob: JsonObject | None
    created_at: datetime
    updated_at: datetime


class ProtectedCalendarCredentialRow(TypedDict):
    calendar_account_id: UUID
    user_id: UUID
    auth_kind: str
    credential_kind: str
    secret_manager_kind: str
    secret_ref: str | None
    credential_blob: JsonObject | None
    created_at: datetime
    updated_at: datetime


class TaskArtifactRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    task_workspace_id: UUID
    status: str
    ingestion_status: str
    relative_path: str
    media_type_hint: str | None
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkRow(TypedDict):
    id: UUID
    user_id: UUID
    task_artifact_id: UUID
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkEmbeddingRow(TypedDict):
    id: UUID
    user_id: UUID
    task_artifact_id: UUID
    task_artifact_chunk_id: UUID
    task_artifact_chunk_sequence_no: int
    embedding_config_id: UUID
    dimensions: int
    vector: list[float]
    created_at: datetime
    updated_at: datetime


class TaskArtifactChunkSemanticRetrievalRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    task_artifact_id: UUID
    relative_path: str
    media_type_hint: str | None
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: datetime
    updated_at: datetime
    embedding_config_id: UUID
    score: float


class TaskStepRow(TypedDict):
    id: UUID
    user_id: UUID
    task_id: UUID
    sequence_no: int
    parent_step_id: UUID | None
    source_approval_id: UUID | None
    source_execution_id: UUID | None
    kind: str
    status: str
    request: JsonObject
    outcome: JsonObject
    trace_id: UUID
    trace_kind: str
    created_at: datetime
    updated_at: datetime


class ToolExecutionRow(TypedDict):
    id: UUID
    user_id: UUID
    approval_id: UUID
    task_step_id: UUID
    thread_id: UUID
    tool_id: UUID
    trace_id: UUID
    request_event_id: UUID | None
    result_event_id: UUID | None
    status: str
    handler_key: str | None
    request: JsonObject
    tool: JsonObject
    result: JsonObject
    executed_at: datetime


class ExecutionBudgetRow(TypedDict):
    id: UUID
    user_id: UUID
    tool_key: str | None
    domain_hint: str | None
    max_completed_executions: int
    rolling_window_seconds: int | None
    status: str
    deactivated_at: datetime | None
    superseded_by_budget_id: UUID | None
    supersedes_budget_id: UUID | None
    created_at: datetime


class CountRow(TypedDict):
    count: int


class LabelCountRow(TypedDict):
    label: str
    count: int


INSERT_USER_SQL = """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, %s, %s)
                RETURNING id, email, display_name, created_at
                """

GET_USER_SQL = """
                SELECT id, email, display_name, created_at
                FROM users
                WHERE id = %s
                """

INSERT_THREAD_SQL = """
                INSERT INTO threads (user_id, title)
                VALUES (app.current_user_id(), %s)
                RETURNING id, user_id, title, created_at, updated_at
                """

GET_THREAD_SQL = """
                SELECT id, user_id, title, created_at, updated_at
                FROM threads
                WHERE id = %s
                """

LIST_THREADS_SQL = """
                SELECT id, user_id, title, created_at, updated_at
                FROM threads
                ORDER BY created_at DESC, id DESC
                """

INSERT_SESSION_SQL = """
                INSERT INTO sessions (user_id, thread_id, status)
                VALUES (app.current_user_id(), %s, %s)
                RETURNING id, user_id, thread_id, status, started_at, ended_at, created_at
                """

LIST_THREAD_SESSIONS_SQL = """
                SELECT id, user_id, thread_id, status, started_at, ended_at, created_at
                FROM sessions
                WHERE thread_id = %s
                ORDER BY started_at ASC, created_at ASC, id ASC
                """

LOCK_THREAD_EVENTS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 0))"
LOCK_TASK_STEPS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 2))"
LOCK_TASK_WORKSPACES_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 3))"
LOCK_TASK_ARTIFACTS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 4))"

INSERT_EVENT_SQL = """
                WITH next_sequence AS (
                  SELECT COALESCE(MAX(sequence_no) + 1, 1) AS sequence_no
                  FROM events
                  WHERE thread_id = %s
                    AND user_id = app.current_user_id()
                )
                INSERT INTO events (user_id, thread_id, session_id, sequence_no, kind, payload)
                SELECT app.current_user_id(), %s, %s, next_sequence.sequence_no, %s, %s
                FROM next_sequence
                RETURNING id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                """

LIST_THREAD_EVENTS_SQL = """
                SELECT id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                FROM events
                WHERE thread_id = %s
                ORDER BY sequence_no ASC
                """

LIST_EVENTS_BY_IDS_SQL = """
                SELECT id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                FROM events
                WHERE id = ANY(%s)
                ORDER BY sequence_no ASC
                """

INSERT_TRACE_SQL = """
                INSERT INTO traces (user_id, thread_id, kind, compiler_version, status, limits)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, thread_id, kind, compiler_version, status, limits, created_at
                """

GET_TRACE_SQL = """
                SELECT id, user_id, thread_id, kind, compiler_version, status, limits, created_at
                FROM traces
                WHERE id = %s
                """

LIST_TRACE_REVIEWS_SQL = """
                SELECT
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at,
                  COUNT(trace_events.id) AS trace_event_count
                FROM traces
                LEFT JOIN trace_events
                  ON trace_events.trace_id = traces.id
                 AND trace_events.user_id = traces.user_id
                GROUP BY
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at
                ORDER BY traces.created_at DESC, traces.id DESC
                """

GET_TRACE_REVIEW_SQL = """
                SELECT
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at,
                  COUNT(trace_events.id) AS trace_event_count
                FROM traces
                LEFT JOIN trace_events
                  ON trace_events.trace_id = traces.id
                 AND trace_events.user_id = traces.user_id
                WHERE traces.id = %s
                GROUP BY
                  traces.id,
                  traces.user_id,
                  traces.thread_id,
                  traces.kind,
                  traces.compiler_version,
                  traces.status,
                  traces.limits,
                  traces.created_at
                """

INSERT_TRACE_EVENT_SQL = """
                INSERT INTO trace_events (user_id, trace_id, sequence_no, kind, payload)
                VALUES (app.current_user_id(), %s, %s, %s, %s)
                RETURNING id, user_id, trace_id, sequence_no, kind, payload, created_at
                """

LIST_TRACE_EVENTS_SQL = """
                SELECT id, user_id, trace_id, sequence_no, kind, payload, created_at
                FROM trace_events
                WHERE trace_id = %s
                ORDER BY sequence_no ASC, id ASC
                """

INSERT_MEMORY_SQL = """
                INSERT INTO memories (
                  user_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                """

GET_MEMORY_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                WHERE id = %s
                """

LIST_MEMORIES_BY_IDS_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                WHERE id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """

GET_MEMORY_BY_KEY_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                WHERE memory_key = %s
                """

LIST_MEMORIES_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                ORDER BY created_at ASC, id ASC
                """

COUNT_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                """

COUNT_MEMORIES_BY_STATUS_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = %s
                """

COUNT_UNLABELED_REVIEW_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE status = 'active'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM memory_review_labels
                    WHERE memory_review_labels.memory_id = memories.id
                  )
                """

LIST_REVIEW_MEMORIES_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_REVIEW_MEMORIES_BY_STATUS_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                WHERE status = %s
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_UNLABELED_REVIEW_MEMORIES_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                WHERE status = 'active'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM memory_review_labels
                    WHERE memory_review_labels.memory_id = memories.id
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_CONTEXT_MEMORIES_SQL = """
                SELECT id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                FROM memories
                ORDER BY updated_at ASC, created_at ASC, id ASC
                """

UPDATE_MEMORY_SQL = """
                UPDATE memories
                SET value = %s,
                    status = %s,
                    source_event_ids = %s,
                    updated_at = clock_timestamp(),
                    deleted_at = CASE
                      WHEN %s = 'deleted' THEN clock_timestamp()
                      ELSE NULL
                    END
                WHERE id = %s
                RETURNING id, user_id, memory_key, value, status, source_event_ids, created_at, updated_at, deleted_at
                """

LOCK_MEMORY_REVISIONS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 1))"

INSERT_MEMORY_REVISION_SQL = """
                WITH next_sequence AS (
                  SELECT COALESCE(MAX(sequence_no) + 1, 1) AS sequence_no
                  FROM memory_revisions
                  WHERE memory_id = %s
                    AND user_id = app.current_user_id()
                )
                INSERT INTO memory_revisions (
                  user_id,
                  memory_id,
                  sequence_no,
                  action,
                  memory_key,
                  previous_value,
                  new_value,
                  source_event_ids,
                  candidate
                )
                SELECT
                  app.current_user_id(),
                  %s,
                  next_sequence.sequence_no,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                FROM next_sequence
                RETURNING id, user_id, memory_id, sequence_no, action, memory_key, previous_value, new_value, source_event_ids, candidate, created_at
                """

LIST_MEMORY_REVISIONS_SQL = """
                SELECT id, user_id, memory_id, sequence_no, action, memory_key, previous_value, new_value, source_event_ids, candidate, created_at
                FROM memory_revisions
                WHERE memory_id = %s
                ORDER BY sequence_no ASC
                """

COUNT_MEMORY_REVISIONS_SQL = """
                SELECT COUNT(*) AS count
                FROM memory_revisions
                WHERE memory_id = %s
                """

LIST_LIMITED_MEMORY_REVISIONS_SQL = """
                SELECT id, user_id, memory_id, sequence_no, action, memory_key, previous_value, new_value, source_event_ids, candidate, created_at
                FROM memory_revisions
                WHERE memory_id = %s
                ORDER BY sequence_no ASC
                LIMIT %s
                """

INSERT_MEMORY_REVIEW_LABEL_SQL = """
                INSERT INTO memory_review_labels (user_id, memory_id, label, note)
                VALUES (app.current_user_id(), %s, %s, %s)
                RETURNING id, user_id, memory_id, label, note, created_at
                """

LIST_MEMORY_REVIEW_LABELS_SQL = """
                SELECT id, user_id, memory_id, label, note, created_at
                FROM memory_review_labels
                WHERE memory_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL = """
                SELECT label, COUNT(*) AS count
                FROM memory_review_labels
                WHERE memory_id = %s
                GROUP BY label
                ORDER BY label ASC
                """

COUNT_LABELED_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE EXISTS (
                  SELECT 1
                  FROM memory_review_labels
                  WHERE memory_review_labels.memory_id = memories.id
                )
                """

COUNT_UNLABELED_MEMORIES_SQL = """
                SELECT COUNT(*) AS count
                FROM memories
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM memory_review_labels
                  WHERE memory_review_labels.memory_id = memories.id
                )
                """

LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL = """
                SELECT label, COUNT(*) AS count
                FROM memory_review_labels
                GROUP BY label
                ORDER BY label ASC
                """

INSERT_EMBEDDING_CONFIG_SQL = """
                INSERT INTO embedding_configs (
                  user_id,
                  provider,
                  model,
                  version,
                  dimensions,
                  status,
                  metadata,
                  created_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, clock_timestamp())
                RETURNING id, user_id, provider, model, version, dimensions, status, metadata, created_at
                """

GET_EMBEDDING_CONFIG_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                WHERE id = %s
                """

GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                WHERE provider = %s
                  AND model = %s
                  AND version = %s
                """

LIST_EMBEDDING_CONFIGS_SQL = """
                SELECT id, user_id, provider, model, version, dimensions, status, metadata, created_at
                FROM embedding_configs
                ORDER BY created_at ASC, id ASC
                """

INSERT_MEMORY_EMBEDDING_SQL = """
                INSERT INTO memory_embeddings (
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                """

GET_MEMORY_EMBEDDING_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE id = %s
                """

GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE memory_id = %s
                  AND embedding_config_id = %s
                """

LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE memory_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL = """
                SELECT
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                FROM memory_embeddings
                WHERE embedding_config_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPDATE_MEMORY_EMBEDDING_SQL = """
                UPDATE memory_embeddings
                SET dimensions = %s,
                    vector = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  memory_id,
                  embedding_config_id,
                  dimensions,
                  vector,
                  created_at,
                  updated_at
                """

RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL = """
                SELECT
                  memories.id,
                  memories.user_id,
                  memories.memory_key,
                  memories.value,
                  memories.status,
                  memories.source_event_ids,
                  memories.created_at,
                  memories.updated_at,
                  memories.deleted_at,
                  1 - (
                    replace(memory_embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM memory_embeddings
                JOIN memories
                  ON memories.id = memory_embeddings.memory_id
                 AND memories.user_id = memory_embeddings.user_id
                WHERE memory_embeddings.embedding_config_id = %s
                  AND memory_embeddings.dimensions = %s
                  AND memories.status = 'active'
                ORDER BY score DESC, memories.created_at ASC, memories.id ASC
                LIMIT %s
                """

RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL = """
                SELECT
                  chunks.id,
                  chunks.user_id,
                  artifacts.task_id,
                  artifacts.id AS task_artifact_id,
                  artifacts.relative_path,
                  artifacts.media_type_hint,
                  chunks.sequence_no,
                  chunks.char_start,
                  chunks.char_end_exclusive,
                  chunks.text,
                  chunks.created_at,
                  chunks.updated_at,
                  embeddings.embedding_config_id,
                  1 - (
                    replace(embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                JOIN task_artifacts AS artifacts
                  ON artifacts.id = chunks.task_artifact_id
                 AND artifacts.user_id = chunks.user_id
                WHERE embeddings.embedding_config_id = %s
                  AND embeddings.dimensions = %s
                  AND artifacts.task_id = %s
                  AND artifacts.ingestion_status = 'ingested'
                ORDER BY score DESC, artifacts.relative_path ASC, chunks.sequence_no ASC, chunks.id ASC
                LIMIT %s
                """

RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL = """
                SELECT
                  chunks.id,
                  chunks.user_id,
                  artifacts.task_id,
                  artifacts.id AS task_artifact_id,
                  artifacts.relative_path,
                  artifacts.media_type_hint,
                  chunks.sequence_no,
                  chunks.char_start,
                  chunks.char_end_exclusive,
                  chunks.text,
                  chunks.created_at,
                  chunks.updated_at,
                  embeddings.embedding_config_id,
                  1 - (
                    replace(embeddings.vector::text, ' ', '')::vector <=> %s::vector
                  ) AS score
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                JOIN task_artifacts AS artifacts
                  ON artifacts.id = chunks.task_artifact_id
                 AND artifacts.user_id = chunks.user_id
                WHERE embeddings.embedding_config_id = %s
                  AND embeddings.dimensions = %s
                  AND artifacts.id = %s
                  AND artifacts.ingestion_status = 'ingested'
                ORDER BY score DESC, artifacts.relative_path ASC, chunks.sequence_no ASC, chunks.id ASC
                LIMIT %s
                """

INSERT_ENTITY_SQL = """
                INSERT INTO entities (user_id, entity_type, name, source_memory_ids, created_at)
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp())
                RETURNING id, user_id, entity_type, name, source_memory_ids, created_at
                """

GET_ENTITY_SQL = """
                SELECT id, user_id, entity_type, name, source_memory_ids, created_at
                FROM entities
                WHERE id = %s
                """

LIST_ENTITIES_SQL = """
                SELECT id, user_id, entity_type, name, source_memory_ids, created_at
                FROM entities
                ORDER BY created_at ASC, id ASC
                """

INSERT_ENTITY_EDGE_SQL = """
                INSERT INTO entity_edges (
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                """

LIST_ENTITY_EDGES_FOR_ENTITY_SQL = """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = %s OR to_entity_id = %s
                ORDER BY created_at ASC, id ASC
                """

LIST_ENTITY_EDGES_FOR_ENTITIES_SQL = """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = ANY(%s) OR to_entity_id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """

INSERT_CONSENT_SQL = """
                INSERT INTO consents (
                  user_id,
                  consent_key,
                  status,
                  metadata,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING id, user_id, consent_key, status, metadata, created_at, updated_at
                """

GET_CONSENT_BY_KEY_SQL = """
                SELECT id, user_id, consent_key, status, metadata, created_at, updated_at
                FROM consents
                WHERE consent_key = %s
                """

LIST_CONSENTS_SQL = """
                SELECT id, user_id, consent_key, status, metadata, created_at, updated_at
                FROM consents
                ORDER BY consent_key ASC, created_at ASC, id ASC
                """

UPDATE_CONSENT_SQL = """
                UPDATE consents
                SET status = %s,
                    metadata = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING id, user_id, consent_key, status, metadata, created_at, updated_at
                """

INSERT_POLICY_SQL = """
                INSERT INTO policies (
                  user_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp(), clock_timestamp())
                RETURNING
                  id,
                  user_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                """

GET_POLICY_SQL = """
                SELECT
                  id,
                  user_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE id = %s
                """

LIST_POLICIES_SQL = """
                SELECT
                  id,
                  user_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                ORDER BY priority ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_POLICIES_SQL = """
                SELECT
                  id,
                  user_id,
                  name,
                  action,
                  scope,
                  effect,
                  priority,
                  active,
                  conditions,
                  required_consents,
                  created_at,
                  updated_at
                FROM policies
                WHERE active = TRUE
                ORDER BY priority ASC, created_at ASC, id ASC
                """

INSERT_TOOL_SQL = """
                INSERT INTO tools (
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                )
                VALUES (
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
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                """

GET_TOOL_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                WHERE id = %s
                """

LIST_TOOLS_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                ORDER BY tool_key ASC, version ASC, created_at ASC, id ASC
                """

LIST_ACTIVE_TOOLS_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata,
                  created_at
                FROM tools
                WHERE active = TRUE
                ORDER BY tool_key ASC, version ASC, created_at ASC, id ASC
                """

INSERT_APPROVAL_SQL = """
                INSERT INTO approvals (
                  user_id,
                  thread_id,
                  tool_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

GET_APPROVAL_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                FROM approvals
                WHERE id = %s
                """

LIST_APPROVALS_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                FROM approvals
                ORDER BY created_at ASC, id ASC
                """

UPDATE_APPROVAL_RESOLUTION_SQL = """
                UPDATE approvals
                SET status = %s,
                    resolved_at = clock_timestamp(),
                    resolved_by_user_id = app.current_user_id()
                WHERE id = %s
                  AND status = 'pending'
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

UPDATE_APPROVAL_TASK_STEP_SQL = """
                UPDATE approvals
                SET task_step_id = %s
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  created_at,
                  resolved_at,
                  resolved_by_user_id
                """

INSERT_TASK_SQL = """
                INSERT INTO tasks (
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

GET_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                WHERE id = %s
                """

GET_TASK_BY_APPROVAL_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                WHERE latest_approval_id = %s
                """

LIST_TASKS_SQL = """
                SELECT
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                FROM tasks
                ORDER BY created_at ASC, id ASC
                """

UPDATE_TASK_STATUS_BY_APPROVAL_SQL = """
                UPDATE tasks
                SET status = %s,
                    updated_at = clock_timestamp()
                WHERE latest_approval_id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL = """
                UPDATE tasks
                SET status = %s,
                    latest_execution_id = %s,
                    updated_at = clock_timestamp()
                WHERE latest_approval_id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

UPDATE_TASK_STATUS_SQL = """
                UPDATE tasks
                SET status = %s,
                    latest_approval_id = %s,
                    latest_execution_id = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id,
                  created_at,
                  updated_at
                """

INSERT_GMAIL_ACCOUNT_SQL = """
                INSERT INTO gmail_accounts (
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                """

INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                INSERT INTO gmail_account_credentials (
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

GET_GMAIL_ACCOUNT_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                WHERE id = %s
                """

GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                WHERE provider_account_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

GET_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                SELECT
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """

UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL = """
                UPDATE gmail_account_credentials
                SET
                  auth_kind = %s,
                  credential_kind = %s,
                  secret_manager_kind = %s,
                  secret_ref = %s,
                  credential_blob = %s,
                  updated_at = clock_timestamp()
                WHERE gmail_account_id = %s
                RETURNING
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

LIST_GMAIL_ACCOUNTS_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM gmail_accounts
                ORDER BY created_at ASC, id ASC
                """

INSERT_CALENDAR_ACCOUNT_SQL = """
                INSERT INTO calendar_accounts (
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                """

INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL = """
                INSERT INTO calendar_account_credentials (
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                )
                VALUES (
                  %s,
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                """

GET_CALENDAR_ACCOUNT_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                WHERE id = %s
                """

GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                WHERE provider_account_id = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL = """
                SELECT
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob,
                  created_at,
                  updated_at
                FROM calendar_account_credentials
                WHERE calendar_account_id = %s
                """

LIST_CALENDAR_ACCOUNTS_SQL = """
                SELECT
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  created_at,
                  updated_at
                FROM calendar_accounts
                ORDER BY created_at ASC, id ASC
                """

INSERT_TASK_WORKSPACE_SQL = """
                INSERT INTO task_workspaces (
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                """

GET_TASK_WORKSPACE_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                WHERE id = %s
                """

GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                WHERE task_id = %s
                  AND status = 'active'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

LIST_TASK_WORKSPACES_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                ORDER BY created_at ASC, id ASC
                """

INSERT_TASK_ARTIFACT_SQL = """
                INSERT INTO task_artifacts (
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                """

GET_TASK_ARTIFACT_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE id = %s
                """

GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE task_workspace_id = %s
                  AND relative_path = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """

LIST_TASK_ARTIFACTS_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                ORDER BY created_at ASC, id ASC
                """

LIST_TASK_ARTIFACTS_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE task_id = %s
                ORDER BY created_at ASC, id ASC
                """

LOCK_TASK_ARTIFACT_INGESTION_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 5))"

INSERT_TASK_ARTIFACT_CHUNK_SQL = """
                INSERT INTO task_artifact_chunks (
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                """

LIST_TASK_ARTIFACT_CHUNKS_SQL = """
                SELECT
                  id,
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                FROM task_artifact_chunks
                WHERE task_artifact_id = %s
                ORDER BY sequence_no ASC, id ASC
                """

GET_TASK_ARTIFACT_CHUNK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_artifact_id,
                  sequence_no,
                  char_start,
                  char_end_exclusive,
                  text,
                  created_at,
                  updated_at
                FROM task_artifact_chunks
                WHERE id = %s
                """

INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL = """
                WITH inserted AS (
                  INSERT INTO task_artifact_chunk_embeddings (
                    user_id,
                    task_artifact_chunk_id,
                    embedding_config_id,
                    dimensions,
                    vector,
                    created_at,
                    updated_at
                  )
                  VALUES (
                    app.current_user_id(),
                    %s,
                    %s,
                    %s,
                    %s,
                    clock_timestamp(),
                    clock_timestamp()
                  )
                  RETURNING
                    id,
                    user_id,
                    task_artifact_chunk_id,
                    embedding_config_id,
                    dimensions,
                    vector,
                    created_at,
                    updated_at
                )
                SELECT
                  inserted.id,
                  inserted.user_id,
                  chunks.task_artifact_id,
                  inserted.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  inserted.embedding_config_id,
                  inserted.dimensions,
                  inserted.vector,
                  inserted.created_at,
                  inserted.updated_at
                FROM inserted
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = inserted.task_artifact_chunk_id
                 AND chunks.user_id = inserted.user_id
                """

GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE embeddings.id = %s
                """

GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE embeddings.task_artifact_chunk_id = %s
                  AND embeddings.embedding_config_id = %s
                """

LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE embeddings.task_artifact_chunk_id = %s
                ORDER BY chunks.sequence_no ASC, embeddings.created_at ASC, embeddings.id ASC
                """

LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL = """
                SELECT
                  embeddings.id,
                  embeddings.user_id,
                  chunks.task_artifact_id,
                  embeddings.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  embeddings.embedding_config_id,
                  embeddings.dimensions,
                  embeddings.vector,
                  embeddings.created_at,
                  embeddings.updated_at
                FROM task_artifact_chunk_embeddings AS embeddings
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = embeddings.task_artifact_chunk_id
                 AND chunks.user_id = embeddings.user_id
                WHERE chunks.task_artifact_id = %s
                ORDER BY chunks.sequence_no ASC, embeddings.created_at ASC, embeddings.id ASC
                """

UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL = """
                WITH updated AS (
                  UPDATE task_artifact_chunk_embeddings
                  SET dimensions = %s,
                      vector = %s,
                      updated_at = clock_timestamp()
                  WHERE id = %s
                  RETURNING
                    id,
                    user_id,
                    task_artifact_chunk_id,
                    embedding_config_id,
                    dimensions,
                    vector,
                    created_at,
                    updated_at
                )
                SELECT
                  updated.id,
                  updated.user_id,
                  chunks.task_artifact_id,
                  updated.task_artifact_chunk_id,
                  chunks.sequence_no AS task_artifact_chunk_sequence_no,
                  updated.embedding_config_id,
                  updated.dimensions,
                  updated.vector,
                  updated.created_at,
                  updated.updated_at
                FROM updated
                JOIN task_artifact_chunks AS chunks
                  ON chunks.id = updated.task_artifact_chunk_id
                 AND chunks.user_id = updated.user_id
                """

UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL = """
                UPDATE task_artifacts
                SET ingestion_status = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                """

INSERT_TASK_STEP_SQL = """
                INSERT INTO task_steps (
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                )
                VALUES (
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
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                """

GET_TASK_STEP_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                FROM task_steps
                WHERE id = %s
                """

GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                FROM task_steps
                WHERE task_id = %s
                  AND sequence_no = %s
                """

LIST_TASK_STEPS_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                FROM task_steps
                WHERE task_id = %s
                ORDER BY sequence_no ASC, created_at ASC, id ASC
                """

UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL = """
                UPDATE task_steps
                SET status = %s,
                    outcome = %s,
                    trace_id = %s,
                    trace_kind = %s,
                    updated_at = clock_timestamp()
                WHERE task_id = %s
                  AND sequence_no = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                """

UPDATE_TASK_STEP_SQL = """
                UPDATE task_steps
                SET status = %s,
                    outcome = %s,
                    trace_id = %s,
                    trace_kind = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  parent_step_id,
                  source_approval_id,
                  source_execution_id,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind,
                  created_at,
                  updated_at
                """

INSERT_TOOL_EXECUTION_SQL = """
                INSERT INTO tool_executions (
                  user_id,
                  approval_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  request,
                  tool,
                  result,
                  executed_at
                )
                VALUES (
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
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  approval_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  request,
                  tool,
                  result,
                  executed_at
                """

GET_TOOL_EXECUTION_SQL = """
                SELECT
                  id,
                  user_id,
                  approval_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  request,
                  tool,
                  result,
                  executed_at
                FROM tool_executions
                WHERE id = %s
                """

LIST_TOOL_EXECUTIONS_SQL = """
                SELECT
                  id,
                  user_id,
                  approval_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  request,
                  tool,
                  result,
                  executed_at
                FROM tool_executions
                ORDER BY executed_at ASC, id ASC
                """

INSERT_EXECUTION_BUDGET_SQL = """
                INSERT INTO execution_budgets (
                  id,
                  user_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  supersedes_budget_id
                )
                VALUES (
                  COALESCE(%s, gen_random_uuid()),
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                """

GET_EXECUTION_BUDGET_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                FROM execution_budgets
                WHERE id = %s
                """

LIST_EXECUTION_BUDGETS_SQL = """
                SELECT
                  id,
                  user_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                FROM execution_budgets
                ORDER BY created_at ASC, id ASC
                """

DEACTIVATE_EXECUTION_BUDGET_SQL = """
                UPDATE execution_budgets
                SET status = 'inactive',
                    deactivated_at = now()
                WHERE id = %s
                  AND status = 'active'
                RETURNING
                  id,
                  user_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                """

SUPERSEDE_EXECUTION_BUDGET_SQL = """
                UPDATE execution_budgets
                SET status = 'superseded',
                    deactivated_at = now(),
                    superseded_by_budget_id = %s
                WHERE id = %s
                  AND status = 'active'
                RETURNING
                  id,
                  user_id,
                  tool_key,
                  domain_hint,
                  max_completed_executions,
                  rolling_window_seconds,
                  status,
                  deactivated_at,
                  superseded_by_budget_id,
                  supersedes_budget_id,
                  created_at
                """

UPDATE_EVENT_ERROR = "events are append-only and must be superseded by new records"
DELETE_EVENT_ERROR = "events are append-only and must not be deleted in place"
UPDATE_TRACE_EVENT_ERROR = "trace events are append-only and must be superseded by new records"
DELETE_TRACE_EVENT_ERROR = "trace events are append-only and must not be deleted in place"


class AppendOnlyViolation(RuntimeError):
    """Raised when a caller attempts to mutate an immutable event."""


class ContinuityStoreInvariantError(RuntimeError):
    """Raised when a write query does not return the row its contract promises."""


class ContinuityStore:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def _fetch_one(
        self,
        operation_name: str,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> RowT:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                f"{operation_name} did not return a row from the database",
            )

        return cast(RowT, row)

    def _fetch_all(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> list[RowT]:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return cast(list[RowT], list(cur.fetchall()))

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> RowT | None:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
        return cast(RowT | None, row)

    def _fetch_count(
        self,
        query: str,
        params: tuple[object, ...] | None = None,
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                "count query did not return a row from the database",
            )

        return cast(CountRow, row)["count"]

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        return "[" + ",".join(repr(value) for value in vector) + "]"

    def create_user(self, user_id: UUID, email: str, display_name: str | None = None) -> UserRow:
        return self._fetch_one(
            "create_user",
            INSERT_USER_SQL,
            (user_id, email, display_name),
        )

    def get_user(self, user_id: UUID) -> UserRow:
        return self._fetch_one("get_user", GET_USER_SQL, (user_id,))

    def create_thread(self, title: str) -> ThreadRow:
        return self._fetch_one("create_thread", INSERT_THREAD_SQL, (title,))

    def get_thread(self, thread_id: UUID) -> ThreadRow:
        return self._fetch_one("get_thread", GET_THREAD_SQL, (thread_id,))

    def get_thread_optional(self, thread_id: UUID) -> ThreadRow | None:
        return self._fetch_optional_one(GET_THREAD_SQL, (thread_id,))

    def list_threads(self) -> list[ThreadRow]:
        return self._fetch_all(LIST_THREADS_SQL)

    def create_session(self, thread_id: UUID, status: str = "active") -> SessionRow:
        return self._fetch_one("create_session", INSERT_SESSION_SQL, (thread_id, status))

    def list_thread_sessions(self, thread_id: UUID) -> list[SessionRow]:
        return self._fetch_all(LIST_THREAD_SESSIONS_SQL, (thread_id,))

    def append_event(
        self,
        thread_id: UUID,
        session_id: UUID | None,
        kind: str,
        payload: JsonObject,
    ) -> EventRow:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_THREAD_EVENTS_SQL, (str(thread_id),))
            cur.execute(
                INSERT_EVENT_SQL,
                (thread_id, thread_id, session_id, kind, Jsonb(payload)),
            )
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                "append_event did not return a row from the database",
            )

        return cast(EventRow, row)

    def list_thread_events(self, thread_id: UUID) -> list[EventRow]:
        return self._fetch_all(LIST_THREAD_EVENTS_SQL, (thread_id,))

    def list_events_by_ids(self, event_ids: list[UUID]) -> list[EventRow]:
        if not event_ids:
            return []
        return self._fetch_all(LIST_EVENTS_BY_IDS_SQL, (event_ids,))

    def create_trace(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        kind: str,
        compiler_version: str,
        status: str,
        limits: JsonObject,
    ) -> TraceRow:
        return self._fetch_one(
            "create_trace",
            INSERT_TRACE_SQL,
            (user_id, thread_id, kind, compiler_version, status, Jsonb(limits)),
        )

    def get_trace(self, trace_id: UUID) -> TraceRow:
        return self._fetch_one("get_trace", GET_TRACE_SQL, (trace_id,))

    def get_trace_review_optional(self, trace_id: UUID) -> TraceReviewRow | None:
        return self._fetch_optional_one(GET_TRACE_REVIEW_SQL, (trace_id,))

    def list_trace_reviews(self) -> list[TraceReviewRow]:
        return self._fetch_all(LIST_TRACE_REVIEWS_SQL)

    def append_trace_event(
        self,
        *,
        trace_id: UUID,
        sequence_no: int,
        kind: str,
        payload: JsonObject,
    ) -> TraceEventRow:
        return self._fetch_one(
            "append_trace_event",
            INSERT_TRACE_EVENT_SQL,
            (trace_id, sequence_no, kind, Jsonb(payload)),
        )

    def list_trace_events(self, trace_id: UUID) -> list[TraceEventRow]:
        return self._fetch_all(LIST_TRACE_EVENTS_SQL, (trace_id,))

    def create_memory(
        self,
        *,
        memory_key: str,
        value: JsonValue,
        status: str,
        source_event_ids: list[str],
    ) -> MemoryRow:
        return self._fetch_one(
            "create_memory",
            INSERT_MEMORY_SQL,
            (memory_key, Jsonb(value), status, Jsonb(source_event_ids)),
        )

    def get_memory(self, memory_id: UUID) -> MemoryRow:
        return self._fetch_one("get_memory", GET_MEMORY_SQL, (memory_id,))

    def get_memory_optional(self, memory_id: UUID) -> MemoryRow | None:
        return self._fetch_optional_one(GET_MEMORY_SQL, (memory_id,))

    def list_memories_by_ids(self, memory_ids: list[UUID]) -> list[MemoryRow]:
        if not memory_ids:
            return []
        return self._fetch_all(LIST_MEMORIES_BY_IDS_SQL, (memory_ids,))

    def get_memory_by_key(self, memory_key: str) -> MemoryRow | None:
        return self._fetch_optional_one(GET_MEMORY_BY_KEY_SQL, (memory_key,))

    def list_memories(self) -> list[MemoryRow]:
        return self._fetch_all(LIST_MEMORIES_SQL)

    def count_memories(self, *, status: str | None = None) -> int:
        if status is None:
            return self._fetch_count(COUNT_MEMORIES_SQL)
        return self._fetch_count(COUNT_MEMORIES_BY_STATUS_SQL, (status,))

    def count_unlabeled_review_memories(self) -> int:
        return self._fetch_count(COUNT_UNLABELED_REVIEW_MEMORIES_SQL)

    def list_review_memories(self, *, status: str | None = None, limit: int) -> list[MemoryRow]:
        if status is None:
            return self._fetch_all(LIST_REVIEW_MEMORIES_SQL, (limit,))
        return self._fetch_all(LIST_REVIEW_MEMORIES_BY_STATUS_SQL, (status, limit))

    def list_unlabeled_review_memories(self, *, limit: int) -> list[MemoryRow]:
        return self._fetch_all(LIST_UNLABELED_REVIEW_MEMORIES_SQL, (limit,))

    def list_context_memories(self) -> list[MemoryRow]:
        return self._fetch_all(LIST_CONTEXT_MEMORIES_SQL)

    def update_memory(
        self,
        *,
        memory_id: UUID,
        value: JsonValue,
        status: str,
        source_event_ids: list[str],
    ) -> MemoryRow:
        return self._fetch_one(
            "update_memory",
            UPDATE_MEMORY_SQL,
            (Jsonb(value), status, Jsonb(source_event_ids), status, memory_id),
        )

    def append_memory_revision(
        self,
        *,
        memory_id: UUID,
        action: str,
        memory_key: str,
        previous_value: JsonValue | None,
        new_value: JsonValue | None,
        source_event_ids: list[str],
        candidate: JsonObject,
    ) -> MemoryRevisionRow:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_MEMORY_REVISIONS_SQL, (str(memory_id),))
            cur.execute(
                INSERT_MEMORY_REVISION_SQL,
                (
                    memory_id,
                    memory_id,
                    action,
                    memory_key,
                    Jsonb(previous_value),
                    Jsonb(new_value),
                    Jsonb(source_event_ids),
                    Jsonb(candidate),
                ),
            )
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                "append_memory_revision did not return a row from the database",
            )

        return cast(MemoryRevisionRow, row)

    def count_memory_revisions(self, memory_id: UUID) -> int:
        return self._fetch_count(COUNT_MEMORY_REVISIONS_SQL, (memory_id,))

    def list_memory_revisions(
        self,
        memory_id: UUID,
        *,
        limit: int | None = None,
    ) -> list[MemoryRevisionRow]:
        if limit is None:
            return self._fetch_all(LIST_MEMORY_REVISIONS_SQL, (memory_id,))
        return self._fetch_all(LIST_LIMITED_MEMORY_REVISIONS_SQL, (memory_id, limit))

    def create_memory_review_label(
        self,
        *,
        memory_id: UUID,
        label: str,
        note: str | None,
    ) -> MemoryReviewLabelRow:
        return self._fetch_one(
            "create_memory_review_label",
            INSERT_MEMORY_REVIEW_LABEL_SQL,
            (memory_id, label, note),
        )

    def list_memory_review_labels(self, memory_id: UUID) -> list[MemoryReviewLabelRow]:
        return self._fetch_all(LIST_MEMORY_REVIEW_LABELS_SQL, (memory_id,))

    def list_memory_review_label_counts(self, memory_id: UUID) -> list[LabelCountRow]:
        return self._fetch_all(LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL, (memory_id,))

    def count_labeled_memories(self) -> int:
        return self._fetch_count(COUNT_LABELED_MEMORIES_SQL)

    def count_unlabeled_memories(self) -> int:
        return self._fetch_count(COUNT_UNLABELED_MEMORIES_SQL)

    def list_all_memory_review_label_counts(self) -> list[LabelCountRow]:
        return self._fetch_all(LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL)

    def create_embedding_config(
        self,
        *,
        provider: str,
        model: str,
        version: str,
        dimensions: int,
        status: str,
        metadata: JsonObject,
    ) -> EmbeddingConfigRow:
        return self._fetch_one(
            "create_embedding_config",
            INSERT_EMBEDDING_CONFIG_SQL,
            (provider, model, version, dimensions, status, Jsonb(metadata)),
        )

    def get_embedding_config_optional(self, embedding_config_id: UUID) -> EmbeddingConfigRow | None:
        return self._fetch_optional_one(GET_EMBEDDING_CONFIG_SQL, (embedding_config_id,))

    def get_embedding_config_by_identity_optional(
        self,
        *,
        provider: str,
        model: str,
        version: str,
    ) -> EmbeddingConfigRow | None:
        return self._fetch_optional_one(
            GET_EMBEDDING_CONFIG_BY_IDENTITY_SQL,
            (provider, model, version),
        )

    def list_embedding_configs(self) -> list[EmbeddingConfigRow]:
        return self._fetch_all(LIST_EMBEDDING_CONFIGS_SQL)

    def create_memory_embedding(
        self,
        *,
        memory_id: UUID,
        embedding_config_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> MemoryEmbeddingRow:
        return self._fetch_one(
            "create_memory_embedding",
            INSERT_MEMORY_EMBEDDING_SQL,
            (memory_id, embedding_config_id, dimensions, Jsonb(vector)),
        )

    def get_memory_embedding_optional(self, memory_embedding_id: UUID) -> MemoryEmbeddingRow | None:
        return self._fetch_optional_one(GET_MEMORY_EMBEDDING_SQL, (memory_embedding_id,))

    def get_memory_embedding_by_memory_and_config_optional(
        self,
        *,
        memory_id: UUID,
        embedding_config_id: UUID,
    ) -> MemoryEmbeddingRow | None:
        return self._fetch_optional_one(
            GET_MEMORY_EMBEDDING_BY_MEMORY_AND_CONFIG_SQL,
            (memory_id, embedding_config_id),
        )

    def list_memory_embeddings_for_memory(self, memory_id: UUID) -> list[MemoryEmbeddingRow]:
        return self._fetch_all(LIST_MEMORY_EMBEDDINGS_FOR_MEMORY_SQL, (memory_id,))

    def list_memory_embeddings_for_config(
        self,
        embedding_config_id: UUID,
    ) -> list[MemoryEmbeddingRow]:
        return self._fetch_all(LIST_MEMORY_EMBEDDINGS_FOR_CONFIG_SQL, (embedding_config_id,))

    def update_memory_embedding(
        self,
        *,
        memory_embedding_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> MemoryEmbeddingRow:
        return self._fetch_one(
            "update_memory_embedding",
            UPDATE_MEMORY_EMBEDDING_SQL,
            (dimensions, Jsonb(vector), memory_embedding_id),
        )

    def retrieve_semantic_memory_matches(
        self,
        *,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[SemanticMemoryRetrievalRow]:
        return self._fetch_all(
            RETRIEVE_SEMANTIC_MEMORY_MATCHES_SQL,
            (
                self._vector_literal(query_vector),
                embedding_config_id,
                len(query_vector),
                limit,
            ),
        )

    def retrieve_task_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_id: UUID,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[TaskArtifactChunkSemanticRetrievalRow]:
        return self._fetch_all(
            RETRIEVE_TASK_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
            (
                self._vector_literal(query_vector),
                embedding_config_id,
                len(query_vector),
                task_id,
                limit,
            ),
        )

    def retrieve_artifact_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_artifact_id: UUID,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[TaskArtifactChunkSemanticRetrievalRow]:
        return self._fetch_all(
            RETRIEVE_ARTIFACT_SCOPED_SEMANTIC_ARTIFACT_CHUNK_MATCHES_SQL,
            (
                self._vector_literal(query_vector),
                embedding_config_id,
                len(query_vector),
                task_artifact_id,
                limit,
            ),
        )

    def create_entity(
        self,
        *,
        entity_type: str,
        name: str,
        source_memory_ids: list[str],
    ) -> EntityRow:
        return self._fetch_one(
            "create_entity",
            INSERT_ENTITY_SQL,
            (entity_type, name, Jsonb(source_memory_ids)),
        )

    def get_entity_optional(self, entity_id: UUID) -> EntityRow | None:
        return self._fetch_optional_one(GET_ENTITY_SQL, (entity_id,))

    def list_entities(self) -> list[EntityRow]:
        return self._fetch_all(LIST_ENTITIES_SQL)

    def create_entity_edge(
        self,
        *,
        from_entity_id: UUID,
        to_entity_id: UUID,
        relationship_type: str,
        valid_from: datetime | None,
        valid_to: datetime | None,
        source_memory_ids: list[str],
    ) -> EntityEdgeRow:
        return self._fetch_one(
            "create_entity_edge",
            INSERT_ENTITY_EDGE_SQL,
            (
                from_entity_id,
                to_entity_id,
                relationship_type,
                valid_from,
                valid_to,
                Jsonb(source_memory_ids),
            ),
        )

    def list_entity_edges_for_entity(self, entity_id: UUID) -> list[EntityEdgeRow]:
        return self._fetch_all(LIST_ENTITY_EDGES_FOR_ENTITY_SQL, (entity_id, entity_id))

    def list_entity_edges_for_entities(self, entity_ids: list[UUID]) -> list[EntityEdgeRow]:
        if not entity_ids:
            return []
        return self._fetch_all(LIST_ENTITY_EDGES_FOR_ENTITIES_SQL, (entity_ids, entity_ids))

    def create_consent(
        self,
        *,
        consent_key: str,
        status: str,
        metadata: JsonObject,
    ) -> ConsentRow:
        return self._fetch_one(
            "create_consent",
            INSERT_CONSENT_SQL,
            (consent_key, status, Jsonb(metadata)),
        )

    def get_consent_by_key_optional(self, consent_key: str) -> ConsentRow | None:
        return self._fetch_optional_one(GET_CONSENT_BY_KEY_SQL, (consent_key,))

    def list_consents(self) -> list[ConsentRow]:
        return self._fetch_all(LIST_CONSENTS_SQL)

    def update_consent(
        self,
        *,
        consent_id: UUID,
        status: str,
        metadata: JsonObject,
    ) -> ConsentRow:
        return self._fetch_one(
            "update_consent",
            UPDATE_CONSENT_SQL,
            (status, Jsonb(metadata), consent_id),
        )

    def create_policy(
        self,
        *,
        name: str,
        action: str,
        scope: str,
        effect: str,
        priority: int,
        active: bool,
        conditions: JsonObject,
        required_consents: list[str],
    ) -> PolicyRow:
        return self._fetch_one(
            "create_policy",
            INSERT_POLICY_SQL,
            (
                name,
                action,
                scope,
                effect,
                priority,
                active,
                Jsonb(conditions),
                Jsonb(required_consents),
            ),
        )

    def get_policy_optional(self, policy_id: UUID) -> PolicyRow | None:
        return self._fetch_optional_one(GET_POLICY_SQL, (policy_id,))

    def list_policies(self) -> list[PolicyRow]:
        return self._fetch_all(LIST_POLICIES_SQL)

    def list_active_policies(self) -> list[PolicyRow]:
        return self._fetch_all(LIST_ACTIVE_POLICIES_SQL)

    def create_tool(
        self,
        *,
        tool_key: str,
        name: str,
        description: str,
        version: str,
        metadata_version: str,
        active: bool,
        tags: list[str],
        action_hints: list[str],
        scope_hints: list[str],
        domain_hints: list[str],
        risk_hints: list[str],
        metadata: JsonObject,
    ) -> ToolRow:
        return self._fetch_one(
            "create_tool",
            INSERT_TOOL_SQL,
            (
                tool_key,
                name,
                description,
                version,
                metadata_version,
                active,
                Jsonb(tags),
                Jsonb(action_hints),
                Jsonb(scope_hints),
                Jsonb(domain_hints),
                Jsonb(risk_hints),
                Jsonb(metadata),
            ),
        )

    def get_tool_optional(self, tool_id: UUID) -> ToolRow | None:
        return self._fetch_optional_one(GET_TOOL_SQL, (tool_id,))

    def list_tools(self) -> list[ToolRow]:
        return self._fetch_all(LIST_TOOLS_SQL)

    def list_active_tools(self) -> list[ToolRow]:
        return self._fetch_all(LIST_ACTIVE_TOOLS_SQL)

    def create_approval(
        self,
        *,
        thread_id: UUID,
        tool_id: UUID,
        task_step_id: UUID | None,
        status: str,
        request: JsonObject,
        tool: JsonObject,
        routing: JsonObject,
        routing_trace_id: UUID,
    ) -> ApprovalRow:
        return self._fetch_one(
            "create_approval",
            INSERT_APPROVAL_SQL,
            (
                thread_id,
                tool_id,
                task_step_id,
                status,
                Jsonb(request),
                Jsonb(tool),
                Jsonb(routing),
                routing_trace_id,
            ),
        )

    def get_approval_optional(self, approval_id: UUID) -> ApprovalRow | None:
        return self._fetch_optional_one(GET_APPROVAL_SQL, (approval_id,))

    def list_approvals(self) -> list[ApprovalRow]:
        return self._fetch_all(LIST_APPROVALS_SQL)

    def resolve_approval_optional(
        self,
        *,
        approval_id: UUID,
        status: str,
    ) -> ApprovalRow | None:
        return self._fetch_optional_one(
            UPDATE_APPROVAL_RESOLUTION_SQL,
            (status, approval_id),
        )

    def update_approval_task_step_optional(
        self,
        *,
        approval_id: UUID,
        task_step_id: UUID,
    ) -> ApprovalRow | None:
        return self._fetch_optional_one(
            UPDATE_APPROVAL_TASK_STEP_SQL,
            (task_step_id, approval_id),
        )

    def create_task(
        self,
        *,
        thread_id: UUID,
        tool_id: UUID,
        status: str,
        request: JsonObject,
        tool: JsonObject,
        latest_approval_id: UUID | None,
        latest_execution_id: UUID | None,
    ) -> TaskRow:
        return self._fetch_one(
            "create_task",
            INSERT_TASK_SQL,
            (
                thread_id,
                tool_id,
                status,
                Jsonb(request),
                Jsonb(tool),
                latest_approval_id,
                latest_execution_id,
            ),
        )

    def get_task_optional(self, task_id: UUID) -> TaskRow | None:
        return self._fetch_optional_one(GET_TASK_SQL, (task_id,))

    def get_task_by_approval_optional(self, approval_id: UUID) -> TaskRow | None:
        return self._fetch_optional_one(GET_TASK_BY_APPROVAL_SQL, (approval_id,))

    def list_tasks(self) -> list[TaskRow]:
        return self._fetch_all(LIST_TASKS_SQL)

    def update_task_status_by_approval_optional(
        self,
        *,
        approval_id: UUID,
        status: str,
    ) -> TaskRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STATUS_BY_APPROVAL_SQL,
            (status, approval_id),
        )

    def update_task_execution_by_approval_optional(
        self,
        *,
        approval_id: UUID,
        latest_execution_id: UUID,
        status: str,
    ) -> TaskRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_EXECUTION_BY_APPROVAL_SQL,
            (status, latest_execution_id, approval_id),
        )

    def update_task_status_optional(
        self,
        *,
        task_id: UUID,
        status: str,
        latest_approval_id: UUID | None,
        latest_execution_id: UUID | None,
    ) -> TaskRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STATUS_SQL,
            (status, latest_approval_id, latest_execution_id, task_id),
        )

    def create_gmail_account(
        self,
        *,
        provider_account_id: str,
        email_address: str,
        display_name: str | None,
        scope: str,
    ) -> GmailAccountRow:
        return self._fetch_one(
            "create_gmail_account",
            INSERT_GMAIL_ACCOUNT_SQL,
            (provider_account_id, email_address, display_name, scope),
        )

    def create_gmail_account_credential(
        self,
        *,
        gmail_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: JsonObject | None,
    ) -> ProtectedGmailCredentialRow:
        return self._fetch_one(
            "create_gmail_account_credential",
            INSERT_GMAIL_ACCOUNT_CREDENTIAL_SQL,
            (
                gmail_account_id,
                auth_kind,
                credential_kind,
                secret_manager_kind,
                secret_ref,
                None if credential_blob is None else Jsonb(credential_blob),
            ),
        )

    def get_gmail_account_optional(self, gmail_account_id: UUID) -> GmailAccountRow | None:
        return self._fetch_optional_one(GET_GMAIL_ACCOUNT_SQL, (gmail_account_id,))

    def get_gmail_account_credential_optional(
        self,
        gmail_account_id: UUID,
    ) -> ProtectedGmailCredentialRow | None:
        return self._fetch_optional_one(GET_GMAIL_ACCOUNT_CREDENTIAL_SQL, (gmail_account_id,))

    def update_gmail_account_credential(
        self,
        *,
        gmail_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: JsonObject | None,
    ) -> ProtectedGmailCredentialRow:
        return self._fetch_one(
            "update_gmail_account_credential",
            UPDATE_GMAIL_ACCOUNT_CREDENTIAL_SQL,
            (
                auth_kind,
                credential_kind,
                secret_manager_kind,
                secret_ref,
                None if credential_blob is None else Jsonb(credential_blob),
                gmail_account_id,
            ),
        )

    def get_gmail_account_by_provider_account_id_optional(
        self,
        provider_account_id: str,
    ) -> GmailAccountRow | None:
        return self._fetch_optional_one(
            GET_GMAIL_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
            (provider_account_id,),
        )

    def list_gmail_accounts(self) -> list[GmailAccountRow]:
        return self._fetch_all(LIST_GMAIL_ACCOUNTS_SQL)

    def create_calendar_account(
        self,
        *,
        provider_account_id: str,
        email_address: str,
        display_name: str | None,
        scope: str,
    ) -> CalendarAccountRow:
        return self._fetch_one(
            "create_calendar_account",
            INSERT_CALENDAR_ACCOUNT_SQL,
            (provider_account_id, email_address, display_name, scope),
        )

    def create_calendar_account_credential(
        self,
        *,
        calendar_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: JsonObject | None,
    ) -> ProtectedCalendarCredentialRow:
        return self._fetch_one(
            "create_calendar_account_credential",
            INSERT_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
            (
                calendar_account_id,
                auth_kind,
                credential_kind,
                secret_manager_kind,
                secret_ref,
                None if credential_blob is None else Jsonb(credential_blob),
            ),
        )

    def get_calendar_account_optional(self, calendar_account_id: UUID) -> CalendarAccountRow | None:
        return self._fetch_optional_one(GET_CALENDAR_ACCOUNT_SQL, (calendar_account_id,))

    def get_calendar_account_credential_optional(
        self,
        calendar_account_id: UUID,
    ) -> ProtectedCalendarCredentialRow | None:
        return self._fetch_optional_one(
            GET_CALENDAR_ACCOUNT_CREDENTIAL_SQL,
            (calendar_account_id,),
        )

    def get_calendar_account_by_provider_account_id_optional(
        self,
        provider_account_id: str,
    ) -> CalendarAccountRow | None:
        return self._fetch_optional_one(
            GET_CALENDAR_ACCOUNT_BY_PROVIDER_ACCOUNT_ID_SQL,
            (provider_account_id,),
        )

    def list_calendar_accounts(self) -> list[CalendarAccountRow]:
        return self._fetch_all(LIST_CALENDAR_ACCOUNTS_SQL)

    def lock_task_workspaces(self, task_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_WORKSPACES_SQL, (str(task_id),))

    def create_task_workspace(
        self,
        *,
        task_id: UUID,
        status: str,
        local_path: str,
    ) -> TaskWorkspaceRow:
        return self._fetch_one(
            "create_task_workspace",
            INSERT_TASK_WORKSPACE_SQL,
            (task_id, status, local_path),
        )

    def get_task_workspace_optional(self, task_workspace_id: UUID) -> TaskWorkspaceRow | None:
        return self._fetch_optional_one(GET_TASK_WORKSPACE_SQL, (task_workspace_id,))

    def get_active_task_workspace_for_task_optional(self, task_id: UUID) -> TaskWorkspaceRow | None:
        return self._fetch_optional_one(GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL, (task_id,))

    def list_task_workspaces(self) -> list[TaskWorkspaceRow]:
        return self._fetch_all(LIST_TASK_WORKSPACES_SQL)

    def lock_task_artifacts(self, task_workspace_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_ARTIFACTS_SQL, (str(task_workspace_id),))

    def create_task_artifact(
        self,
        *,
        task_id: UUID,
        task_workspace_id: UUID,
        status: str,
        ingestion_status: str,
        relative_path: str,
        media_type_hint: str | None,
    ) -> TaskArtifactRow:
        return self._fetch_one(
            "create_task_artifact",
            INSERT_TASK_ARTIFACT_SQL,
            (
                task_id,
                task_workspace_id,
                status,
                ingestion_status,
                relative_path,
                media_type_hint,
            ),
        )

    def get_task_artifact_optional(self, task_artifact_id: UUID) -> TaskArtifactRow | None:
        return self._fetch_optional_one(GET_TASK_ARTIFACT_SQL, (task_artifact_id,))

    def get_task_artifact_by_workspace_relative_path_optional(
        self,
        *,
        task_workspace_id: UUID,
        relative_path: str,
    ) -> TaskArtifactRow | None:
        return self._fetch_optional_one(
            GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL,
            (task_workspace_id, relative_path),
        )

    def list_task_artifacts(self) -> list[TaskArtifactRow]:
        return self._fetch_all(LIST_TASK_ARTIFACTS_SQL)

    def list_task_artifacts_for_task(self, task_id: UUID) -> list[TaskArtifactRow]:
        return self._fetch_all(LIST_TASK_ARTIFACTS_FOR_TASK_SQL, (task_id,))

    def lock_task_artifact_ingestion(self, task_artifact_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_ARTIFACT_INGESTION_SQL, (str(task_artifact_id),))

    def create_task_artifact_chunk(
        self,
        *,
        task_artifact_id: UUID,
        sequence_no: int,
        char_start: int,
        char_end_exclusive: int,
        text: str,
    ) -> TaskArtifactChunkRow:
        return self._fetch_one(
            "create_task_artifact_chunk",
            INSERT_TASK_ARTIFACT_CHUNK_SQL,
            (task_artifact_id, sequence_no, char_start, char_end_exclusive, text),
        )

    def get_task_artifact_chunk_optional(self, task_artifact_chunk_id: UUID) -> TaskArtifactChunkRow | None:
        return self._fetch_optional_one(GET_TASK_ARTIFACT_CHUNK_SQL, (task_artifact_chunk_id,))

    def list_task_artifact_chunks(self, task_artifact_id: UUID) -> list[TaskArtifactChunkRow]:
        return self._fetch_all(LIST_TASK_ARTIFACT_CHUNKS_SQL, (task_artifact_id,))

    def create_task_artifact_chunk_embedding(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> TaskArtifactChunkEmbeddingRow:
        return self._fetch_one(
            "create_task_artifact_chunk_embedding",
            INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
            (task_artifact_chunk_id, embedding_config_id, dimensions, Jsonb(vector)),
        )

    def get_task_artifact_chunk_embedding_optional(
        self,
        task_artifact_chunk_embedding_id: UUID,
    ) -> TaskArtifactChunkEmbeddingRow | None:
        return self._fetch_optional_one(
            GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
            (task_artifact_chunk_embedding_id,),
        )

    def get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
    ) -> TaskArtifactChunkEmbeddingRow | None:
        return self._fetch_optional_one(
            GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL,
            (task_artifact_chunk_id, embedding_config_id),
        )

    def list_task_artifact_chunk_embeddings_for_chunk(
        self,
        task_artifact_chunk_id: UUID,
    ) -> list[TaskArtifactChunkEmbeddingRow]:
        return self._fetch_all(
            LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL,
            (task_artifact_chunk_id,),
        )

    def list_task_artifact_chunk_embeddings_for_artifact(
        self,
        task_artifact_id: UUID,
    ) -> list[TaskArtifactChunkEmbeddingRow]:
        return self._fetch_all(
            LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL,
            (task_artifact_id,),
        )

    def update_task_artifact_chunk_embedding(
        self,
        *,
        task_artifact_chunk_embedding_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> TaskArtifactChunkEmbeddingRow:
        return self._fetch_one(
            "update_task_artifact_chunk_embedding",
            UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL,
            (dimensions, Jsonb(vector), task_artifact_chunk_embedding_id),
        )

    def update_task_artifact_ingestion_status(
        self,
        *,
        task_artifact_id: UUID,
        ingestion_status: str,
    ) -> TaskArtifactRow:
        return self._fetch_one(
            "update_task_artifact_ingestion_status",
            UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL,
            (ingestion_status, task_artifact_id),
        )

    def lock_task_steps(self, task_id: UUID) -> None:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_STEPS_SQL, (str(task_id),))

    def create_task_step(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
        parent_step_id: UUID | None = None,
        source_approval_id: UUID | None = None,
        source_execution_id: UUID | None = None,
        kind: str,
        status: str,
        request: JsonObject,
        outcome: JsonObject,
        trace_id: UUID,
        trace_kind: str,
    ) -> TaskStepRow:
        with self.conn.cursor() as cur:
            cur.execute(LOCK_TASK_STEPS_SQL, (str(task_id),))
            cur.execute(
                INSERT_TASK_STEP_SQL,
                (
                    task_id,
                    sequence_no,
                    parent_step_id,
                    source_approval_id,
                    source_execution_id,
                    kind,
                    status,
                    Jsonb(request),
                    Jsonb(outcome),
                    trace_id,
                    trace_kind,
                ),
            )
            row = cur.fetchone()

        if row is None:
            raise ContinuityStoreInvariantError(
                "create_task_step did not return a row from the database",
            )

        return cast(TaskStepRow, row)

    def get_task_step_optional(self, task_step_id: UUID) -> TaskStepRow | None:
        return self._fetch_optional_one(GET_TASK_STEP_SQL, (task_step_id,))

    def get_task_step_for_task_sequence_optional(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
    ) -> TaskStepRow | None:
        return self._fetch_optional_one(
            GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL,
            (task_id, sequence_no),
        )

    def list_task_steps_for_task(self, task_id: UUID) -> list[TaskStepRow]:
        return self._fetch_all(LIST_TASK_STEPS_FOR_TASK_SQL, (task_id,))

    def update_task_step_for_task_sequence_optional(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
        status: str,
        outcome: JsonObject,
        trace_id: UUID,
        trace_kind: str,
    ) -> TaskStepRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL,
            (
                status,
                Jsonb(outcome),
                trace_id,
                trace_kind,
                task_id,
                sequence_no,
            ),
        )

    def update_task_step_optional(
        self,
        *,
        task_step_id: UUID,
        status: str,
        outcome: JsonObject,
        trace_id: UUID,
        trace_kind: str,
    ) -> TaskStepRow | None:
        return self._fetch_optional_one(
            UPDATE_TASK_STEP_SQL,
            (
                status,
                Jsonb(outcome),
                trace_id,
                trace_kind,
                task_step_id,
            ),
        )

    def create_tool_execution(
        self,
        *,
        approval_id: UUID,
        task_step_id: UUID,
        thread_id: UUID,
        tool_id: UUID,
        trace_id: UUID,
        request_event_id: UUID | None,
        result_event_id: UUID | None,
        status: str,
        handler_key: str | None,
        request: JsonObject,
        tool: JsonObject,
        result: JsonObject,
    ) -> ToolExecutionRow:
        return self._fetch_one(
            "create_tool_execution",
            INSERT_TOOL_EXECUTION_SQL,
            (
                approval_id,
                task_step_id,
                thread_id,
                tool_id,
                trace_id,
                request_event_id,
                result_event_id,
                status,
                handler_key,
                Jsonb(request),
                Jsonb(tool),
                Jsonb(result),
            ),
        )

    def get_tool_execution_optional(self, execution_id: UUID) -> ToolExecutionRow | None:
        return self._fetch_optional_one(GET_TOOL_EXECUTION_SQL, (execution_id,))

    def list_tool_executions(self) -> list[ToolExecutionRow]:
        return self._fetch_all(LIST_TOOL_EXECUTIONS_SQL)

    def create_execution_budget(
        self,
        *,
        budget_id: UUID | None = None,
        tool_key: str | None,
        domain_hint: str | None,
        max_completed_executions: int,
        rolling_window_seconds: int | None = None,
        supersedes_budget_id: UUID | None = None,
    ) -> ExecutionBudgetRow:
        return self._fetch_one(
            "create_execution_budget",
            INSERT_EXECUTION_BUDGET_SQL,
            (
                budget_id,
                tool_key,
                domain_hint,
                max_completed_executions,
                rolling_window_seconds,
                supersedes_budget_id,
            ),
        )

    def get_execution_budget_optional(self, execution_budget_id: UUID) -> ExecutionBudgetRow | None:
        return self._fetch_optional_one(GET_EXECUTION_BUDGET_SQL, (execution_budget_id,))

    def list_execution_budgets(self) -> list[ExecutionBudgetRow]:
        return self._fetch_all(LIST_EXECUTION_BUDGETS_SQL)

    def deactivate_execution_budget_optional(
        self,
        execution_budget_id: UUID,
    ) -> ExecutionBudgetRow | None:
        return self._fetch_optional_one(DEACTIVATE_EXECUTION_BUDGET_SQL, (execution_budget_id,))

    def supersede_execution_budget_optional(
        self,
        *,
        execution_budget_id: UUID,
        superseded_by_budget_id: UUID,
    ) -> ExecutionBudgetRow | None:
        return self._fetch_optional_one(
            SUPERSEDE_EXECUTION_BUDGET_SQL,
            (
                superseded_by_budget_id,
                execution_budget_id,
            ),
        )

    def update_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(UPDATE_EVENT_ERROR)

    def delete_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(DELETE_EVENT_ERROR)

    def update_trace_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(UPDATE_TRACE_EVENT_ERROR)

    def delete_trace_event(self, *_args: Any, **_kwargs: Any) -> None:
        raise AppendOnlyViolation(DELETE_TRACE_EVENT_ERROR)
