"""Task execution legacy-store carrier."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from psycopg.types.json import Jsonb

if TYPE_CHECKING:
    from alicebot_api.store import (
        JsonObject,
        TaskWorkspaceRow,
        TaskArtifactRow,
        TaskArtifactChunkRow,
        TaskArtifactChunkEmbeddingRow,
        TaskStepRow,
        TaskRunRow,
        ToolExecutionRow,
        ExecutionBudgetRow,
    )

LOCK_TASK_STEPS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 2))"
LOCK_TASK_WORKSPACES_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 3))"
LOCK_TASK_ARTIFACTS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 4))"
LOCK_TASK_RUNS_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 5))"

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

INSERT_TASK_RUN_SQL = """
                INSERT INTO task_runs (
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
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
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                """

GET_TASK_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                FROM task_runs
                WHERE id = %s
                """

LIST_TASK_RUNS_FOR_TASK_SQL = """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                FROM task_runs
                WHERE task_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPDATE_TASK_RUN_SQL = """
                UPDATE task_runs
                SET status = %s,
                    checkpoint = %s,
                    tick_count = %s,
                    step_count = %s,
                    retry_count = %s,
                    retry_cap = %s,
                    retry_posture = %s,
                    failure_class = %s,
                    stop_reason = %s,
                    last_transitioned_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                """

ACQUIRE_NEXT_TASK_RUN_SQL = """
                WITH candidate AS (
                  SELECT id
                  FROM task_runs
                  WHERE status IN ('queued', 'running')
                  ORDER BY updated_at ASC, created_at ASC, id ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE task_runs
                SET status = 'running',
                    retry_posture = 'none',
                    failure_class = NULL,
                    stop_reason = NULL,
                    last_transitioned_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = (SELECT id FROM candidate)
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  checkpoint,
                  tick_count,
                  step_count,
                  max_ticks,
                  retry_count,
                  retry_cap,
                  retry_posture,
                  failure_class,
                  stop_reason,
                  last_transitioned_at,
                  created_at,
                  updated_at
                """

INSERT_TOOL_EXECUTION_SQL = """
                INSERT INTO tool_executions (
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
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
                  %s,
                  %s,
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
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
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
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
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
                  request,
                  tool,
                  result,
                  executed_at
                FROM tool_executions
                ORDER BY executed_at ASC, id ASC
                """

GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL = """
                SELECT
                  id,
                  user_id,
                  approval_id,
                  task_run_id,
                  task_step_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  idempotency_key,
                  request,
                  tool,
                  result,
                  executed_at
                FROM tool_executions
                WHERE task_run_id = %s
                  AND approval_id = %s
                  AND idempotency_key = %s
                ORDER BY executed_at ASC, id ASC
                LIMIT 1
                """

INSERT_EXECUTION_BUDGET_SQL = """
                INSERT INTO execution_budgets (
                  id,
                  user_id,
                  agent_profile_id,
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
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  agent_profile_id,
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
                  agent_profile_id,
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
                  agent_profile_id,
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
                  agent_profile_id,
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
                  agent_profile_id,
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

__all__ = [
    'LOCK_TASK_STEPS_SQL',
    'LOCK_TASK_WORKSPACES_SQL',
    'LOCK_TASK_ARTIFACTS_SQL',
    'LOCK_TASK_RUNS_SQL',
    'INSERT_TASK_WORKSPACE_SQL',
    'GET_TASK_WORKSPACE_SQL',
    'GET_ACTIVE_TASK_WORKSPACE_FOR_TASK_SQL',
    'LIST_TASK_WORKSPACES_SQL',
    'INSERT_TASK_ARTIFACT_SQL',
    'GET_TASK_ARTIFACT_SQL',
    'GET_TASK_ARTIFACT_BY_WORKSPACE_RELATIVE_PATH_SQL',
    'LIST_TASK_ARTIFACTS_SQL',
    'LIST_TASK_ARTIFACTS_FOR_TASK_SQL',
    'LOCK_TASK_ARTIFACT_INGESTION_SQL',
    'INSERT_TASK_ARTIFACT_CHUNK_SQL',
    'LIST_TASK_ARTIFACT_CHUNKS_SQL',
    'GET_TASK_ARTIFACT_CHUNK_SQL',
    'INSERT_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL',
    'GET_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL',
    'GET_TASK_ARTIFACT_CHUNK_EMBEDDING_BY_CHUNK_AND_CONFIG_SQL',
    'LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_CHUNK_SQL',
    'LIST_TASK_ARTIFACT_CHUNK_EMBEDDINGS_FOR_ARTIFACT_SQL',
    'UPDATE_TASK_ARTIFACT_CHUNK_EMBEDDING_SQL',
    'UPDATE_TASK_ARTIFACT_INGESTION_STATUS_SQL',
    'INSERT_TASK_STEP_SQL',
    'GET_TASK_STEP_SQL',
    'GET_TASK_STEP_FOR_TASK_SEQUENCE_SQL',
    'LIST_TASK_STEPS_FOR_TASK_SQL',
    'UPDATE_TASK_STEP_FOR_TASK_SEQUENCE_SQL',
    'UPDATE_TASK_STEP_SQL',
    'INSERT_TASK_RUN_SQL',
    'GET_TASK_RUN_SQL',
    'LIST_TASK_RUNS_FOR_TASK_SQL',
    'UPDATE_TASK_RUN_SQL',
    'ACQUIRE_NEXT_TASK_RUN_SQL',
    'INSERT_TOOL_EXECUTION_SQL',
    'GET_TOOL_EXECUTION_SQL',
    'LIST_TOOL_EXECUTIONS_SQL',
    'GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL',
    'INSERT_EXECUTION_BUDGET_SQL',
    'GET_EXECUTION_BUDGET_SQL',
    'LIST_EXECUTION_BUDGETS_SQL',
    'DEACTIVATE_EXECUTION_BUDGET_SQL',
    'SUPERSEDE_EXECUTION_BUDGET_SQL',
]

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
    self._acquire_advisory_lock(LOCK_TASK_STEPS_SQL, task_id)

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
    return self._fetch_one_with_lock(
        operation_name="create_task_step",
        lock_query=LOCK_TASK_STEPS_SQL,
        lock_key=task_id,
        query=INSERT_TASK_STEP_SQL,
        params=(
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

def lock_task_runs(self, task_id: UUID) -> None:
    self._acquire_advisory_lock(LOCK_TASK_RUNS_SQL, task_id)

def create_task_run(
    self,
    *,
    task_id: UUID,
    status: str,
    checkpoint: JsonObject,
    tick_count: int,
    step_count: int,
    max_ticks: int,
    retry_count: int,
    retry_cap: int,
    retry_posture: str,
    failure_class: str | None,
    stop_reason: str | None,
) -> TaskRunRow:
    return self._fetch_one(
        "create_task_run",
        INSERT_TASK_RUN_SQL,
        (
            task_id,
            status,
            Jsonb(checkpoint),
            tick_count,
            step_count,
            max_ticks,
            retry_count,
            retry_cap,
            retry_posture,
            failure_class,
            stop_reason,
        ),
    )

def get_task_run_optional(self, task_run_id: UUID) -> TaskRunRow | None:
    return self._fetch_optional_one(GET_TASK_RUN_SQL, (task_run_id,))

def list_task_runs_for_task(self, task_id: UUID) -> list[TaskRunRow]:
    return self._fetch_all(LIST_TASK_RUNS_FOR_TASK_SQL, (task_id,))

def update_task_run_optional(
    self,
    *,
    task_run_id: UUID,
    status: str,
    checkpoint: JsonObject,
    tick_count: int,
    step_count: int,
    retry_count: int,
    retry_cap: int,
    retry_posture: str,
    failure_class: str | None,
    stop_reason: str | None,
) -> TaskRunRow | None:
    return self._fetch_optional_one(
        UPDATE_TASK_RUN_SQL,
        (
            status,
            Jsonb(checkpoint),
            tick_count,
            step_count,
            retry_count,
            retry_cap,
            retry_posture,
            failure_class,
            stop_reason,
            task_run_id,
        ),
    )

def acquire_next_task_run_optional(self) -> TaskRunRow | None:
    return self._fetch_optional_one(ACQUIRE_NEXT_TASK_RUN_SQL)

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
    task_run_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> ToolExecutionRow:
    return self._fetch_one(
        "create_tool_execution",
        INSERT_TOOL_EXECUTION_SQL,
        (
            approval_id,
            task_run_id,
            task_step_id,
            thread_id,
            tool_id,
            trace_id,
            request_event_id,
            result_event_id,
            status,
            handler_key,
            idempotency_key,
            Jsonb(request),
            Jsonb(tool),
            Jsonb(result),
        ),
    )

def get_tool_execution_optional(self, execution_id: UUID) -> ToolExecutionRow | None:
    return self._fetch_optional_one(GET_TOOL_EXECUTION_SQL, (execution_id,))

def list_tool_executions(self) -> list[ToolExecutionRow]:
    return self._fetch_all(LIST_TOOL_EXECUTIONS_SQL)

def get_tool_execution_by_idempotency_optional(
    self,
    *,
    task_run_id: UUID,
    approval_id: UUID,
    idempotency_key: str,
) -> ToolExecutionRow | None:
    return self._fetch_optional_one(
        GET_TOOL_EXECUTION_BY_IDEMPOTENCY_SQL,
        (task_run_id, approval_id, idempotency_key),
    )

def create_execution_budget(
    self,
    *,
    budget_id: UUID | None = None,
    agent_profile_id: str | None = None,
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
            agent_profile_id,
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
