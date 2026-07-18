"""Conversation and memory legacy-store carrier."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from psycopg.types.json import Jsonb

if TYPE_CHECKING:
    from alicebot_api.store import (
        AgentProfileRow,
        AppendOnlyViolation,
        EventRow,
        FactPatternRow,
        FactPlaybookRow,
        JsonObject,
        JsonValue,
        LabelCountRow,
        MemoryReviewLabelRow,
        MemoryRevisionRow,
        MemoryRow,
        OpenLoopRow,
        SessionRow,
        ThreadRow,
        TraceEventRow,
        TraceReviewRow,
        TraceRow,
        UserRow,
    )

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
                INSERT INTO threads (user_id, title, agent_profile_id)
                VALUES (app.current_user_id(), %s, %s)
                RETURNING id, user_id, title, agent_profile_id, created_at, updated_at
                """

GET_THREAD_SQL = """
                SELECT id, user_id, title, agent_profile_id, created_at, updated_at
                FROM threads
                WHERE id = %s
                """

LIST_THREADS_SQL = """
                SELECT id, user_id, title, agent_profile_id, created_at, updated_at
                FROM threads
                ORDER BY created_at DESC, id DESC
                """

LIST_AGENT_PROFILES_SQL = """
                SELECT id, name, description, model_provider, model_name
                FROM agent_profiles
                ORDER BY id ASC
                """

GET_AGENT_PROFILE_SQL = """
                SELECT id, name, description, model_provider, model_name
                FROM agent_profiles
                WHERE id = %s
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

GET_THREAD_EVENT_TAIL_SQL = """
                SELECT id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                FROM events
                WHERE thread_id = %s
                ORDER BY sequence_no DESC
                LIMIT 1
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
                  agent_profile_id,
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
                  created_at,
                  updated_at,
                  deleted_at
                """

GET_MEMORY_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE id = %s
                """

LIST_MEMORIES_BY_IDS_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """

GET_MEMORY_BY_KEY_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE memory_key = %s
                """

GET_MEMORY_BY_KEY_AND_PROFILE_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE memory_key = %s
                  AND agent_profile_id = %s
                """

LIST_MEMORIES_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
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
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_REVIEW_MEMORIES_BY_STATUS_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE status = %s
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_UNLABELED_REVIEW_MEMORIES_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE status = 'active'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM memory_review_labels
                    WHERE memory_review_labels.memory_id = memories.id
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """

LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
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
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                ORDER BY updated_at ASC, created_at ASC, id ASC
                """

LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL = """
                SELECT
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
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE agent_profile_id = %s
                ORDER BY updated_at ASC, created_at ASC, id ASC
                """

UPDATE_MEMORY_SQL = """
                UPDATE memories
                SET value = %s,
                    status = %s,
                    source_event_ids = %s,
                    memory_type = %s,
                    confidence = %s,
                    salience = %s,
                    confirmation_status = %s,
                    trust_class = %s,
                    promotion_eligibility = %s,
                    evidence_count = %s,
                    independent_source_count = %s,
                    extracted_by_model = %s,
                    trust_reason = %s,
                    valid_from = %s,
                    valid_to = %s,
                    last_confirmed_at = %s,
                    updated_at = clock_timestamp(),
                    deleted_at = CASE
                      WHEN %s = 'deleted' THEN clock_timestamp()
                      ELSE NULL
                    END
                WHERE id = %s
                RETURNING
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
                  created_at,
                  updated_at,
                  deleted_at
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
                  revision_number,
                  revision_type,
                  action,
                  memory_key,
                  previous_value,
                  new_value,
                  source_event_ids,
                  candidate,
                  text_before,
                  text_after
                )
                SELECT
                  app.current_user_id(),
                  %s,
                  next_sequence.sequence_no,
                  next_sequence.sequence_no,
                  CASE %s
                    WHEN 'ADD' THEN 'created'
                    WHEN 'UPDATE' THEN 'edited'
                    WHEN 'DELETE' THEN 'archived'
                    ELSE 'edited'
                  END,
                  %s,
                  %s,
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

UPSERT_FACT_PATTERN_SQL = """
                INSERT INTO fact_patterns (
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
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
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                ON CONFLICT (user_id, pattern_key)
                DO UPDATE SET
                  id = EXCLUDED.id,
                  title = EXCLUDED.title,
                  memory_type = EXCLUDED.memory_type,
                  namespace_key = EXCLUDED.namespace_key,
                  fact_count = EXCLUDED.fact_count,
                  source_fact_ids = EXCLUDED.source_fact_ids,
                  evidence_chain = EXCLUDED.evidence_chain,
                  explanation = EXCLUDED.explanation,
                  updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
                  created_at,
                  updated_at
                """

LIST_FACT_PATTERNS_SQL = """
                SELECT
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_patterns
                ORDER BY memory_type ASC, namespace_key ASC, title ASC, id ASC
                LIMIT %s
                """

COUNT_FACT_PATTERNS_SQL = """
                SELECT COUNT(*) AS count
                FROM fact_patterns
                """

GET_FACT_PATTERN_SQL = """
                SELECT
                  id,
                  user_id,
                  pattern_key,
                  title,
                  memory_type,
                  namespace_key,
                  fact_count,
                  source_fact_ids,
                  evidence_chain,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_patterns
                WHERE id = %s
                """

DELETE_FACT_PATTERNS_NOT_IN_SQL = """
                DELETE FROM fact_patterns
                WHERE user_id = app.current_user_id()
                  AND NOT (id = ANY(%s))
                """

DELETE_ALL_FACT_PATTERNS_SQL = """
                DELETE FROM fact_patterns
                WHERE user_id = app.current_user_id()
                """

UPSERT_FACT_PLAYBOOK_SQL = """
                INSERT INTO fact_playbooks (
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
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
                  %s,
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                ON CONFLICT (user_id, playbook_key)
                DO UPDATE SET
                  id = EXCLUDED.id,
                  pattern_id = EXCLUDED.pattern_id,
                  pattern_key = EXCLUDED.pattern_key,
                  title = EXCLUDED.title,
                  memory_type = EXCLUDED.memory_type,
                  source_fact_ids = EXCLUDED.source_fact_ids,
                  source_pattern_ids = EXCLUDED.source_pattern_ids,
                  steps = EXCLUDED.steps,
                  explanation = EXCLUDED.explanation,
                  updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
                  created_at,
                  updated_at
                """

LIST_FACT_PLAYBOOKS_SQL = """
                SELECT
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_playbooks
                ORDER BY memory_type ASC, pattern_key ASC, title ASC, id ASC
                LIMIT %s
                """

COUNT_FACT_PLAYBOOKS_SQL = """
                SELECT COUNT(*) AS count
                FROM fact_playbooks
                """

GET_FACT_PLAYBOOK_SQL = """
                SELECT
                  id,
                  user_id,
                  playbook_key,
                  pattern_id,
                  pattern_key,
                  title,
                  memory_type,
                  source_fact_ids,
                  source_pattern_ids,
                  steps,
                  explanation,
                  created_at,
                  updated_at
                FROM fact_playbooks
                WHERE id = %s
                """

DELETE_FACT_PLAYBOOKS_NOT_IN_SQL = """
                DELETE FROM fact_playbooks
                WHERE user_id = app.current_user_id()
                  AND NOT (id = ANY(%s))
                """

DELETE_ALL_FACT_PLAYBOOKS_SQL = """
                DELETE FROM fact_playbooks
                WHERE user_id = app.current_user_id()
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

LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL = """
                SELECT memory_review_labels.label, COUNT(*) AS count
                FROM memory_review_labels
                INNER JOIN memories ON memories.id = memory_review_labels.memory_id
                WHERE memories.status = 'active'
                GROUP BY memory_review_labels.label
                ORDER BY memory_review_labels.label ASC
                """

INSERT_OPEN_LOOP_SQL = """
                INSERT INTO open_loops (
                  user_id,
                  memory_id,
                  title,
                  status,
                  opened_at,
                  due_at,
                  resolved_at,
                  resolution_note,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  COALESCE(%s, clock_timestamp()),
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
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
                  updated_at
                """

GET_OPEN_LOOP_SQL = """
                SELECT
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
                  updated_at
                FROM open_loops
                WHERE id = %s
                """

LIST_OPEN_LOOPS_SQL = """
                SELECT
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
                  updated_at
                FROM open_loops
                ORDER BY opened_at DESC, created_at DESC, id DESC
                """

LIST_OPEN_LOOPS_BY_STATUS_SQL = """
                SELECT
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
                  updated_at
                FROM open_loops
                WHERE status = %s
                ORDER BY opened_at DESC, created_at DESC, id DESC
                """

LIST_LIMITED_OPEN_LOOPS_SQL = """
                SELECT
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
                  updated_at
                FROM open_loops
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL = """
                SELECT
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
                  updated_at
                FROM open_loops
                WHERE status = %s
                ORDER BY opened_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_OPEN_LOOPS_SQL = """
                SELECT COUNT(*) AS count
                FROM open_loops
                """

COUNT_OPEN_LOOPS_BY_STATUS_SQL = """
                SELECT COUNT(*) AS count
                FROM open_loops
                WHERE status = %s
                """

UPDATE_OPEN_LOOP_STATUS_SQL = """
                UPDATE open_loops
                SET status = %s,
                    resolved_at = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE COALESCE(%s, clock_timestamp())
                    END,
                    resolution_note = CASE
                      WHEN %s = 'open' THEN NULL
                      ELSE %s
                    END,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
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
                  updated_at
                """

UPDATE_EVENT_ERROR = "events are append-only and must be superseded by new records"
DELETE_EVENT_ERROR = "events are append-only and must not be deleted in place"
UPDATE_TRACE_EVENT_ERROR = "trace events are append-only and must be superseded by new records"
DELETE_TRACE_EVENT_ERROR = "trace events are append-only and must not be deleted in place"

__all__ = [
    'INSERT_USER_SQL',
    'GET_USER_SQL',
    'INSERT_THREAD_SQL',
    'GET_THREAD_SQL',
    'LIST_THREADS_SQL',
    'LIST_AGENT_PROFILES_SQL',
    'GET_AGENT_PROFILE_SQL',
    'INSERT_SESSION_SQL',
    'LIST_THREAD_SESSIONS_SQL',
    'LOCK_THREAD_EVENTS_SQL',
    'INSERT_EVENT_SQL',
    'LIST_THREAD_EVENTS_SQL',
    'GET_THREAD_EVENT_TAIL_SQL',
    'LIST_EVENTS_BY_IDS_SQL',
    'INSERT_TRACE_SQL',
    'GET_TRACE_SQL',
    'LIST_TRACE_REVIEWS_SQL',
    'GET_TRACE_REVIEW_SQL',
    'INSERT_TRACE_EVENT_SQL',
    'LIST_TRACE_EVENTS_SQL',
    'INSERT_MEMORY_SQL',
    'GET_MEMORY_SQL',
    'LIST_MEMORIES_BY_IDS_SQL',
    'GET_MEMORY_BY_KEY_SQL',
    'GET_MEMORY_BY_KEY_AND_PROFILE_SQL',
    'LIST_MEMORIES_SQL',
    'COUNT_MEMORIES_SQL',
    'COUNT_MEMORIES_BY_STATUS_SQL',
    'COUNT_UNLABELED_REVIEW_MEMORIES_SQL',
    'LIST_REVIEW_MEMORIES_SQL',
    'LIST_REVIEW_MEMORIES_BY_STATUS_SQL',
    'LIST_UNLABELED_REVIEW_MEMORIES_SQL',
    'LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL',
    'LIST_CONTEXT_MEMORIES_SQL',
    'LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL',
    'UPDATE_MEMORY_SQL',
    'LOCK_MEMORY_REVISIONS_SQL',
    'INSERT_MEMORY_REVISION_SQL',
    'LIST_MEMORY_REVISIONS_SQL',
    'COUNT_MEMORY_REVISIONS_SQL',
    'LIST_LIMITED_MEMORY_REVISIONS_SQL',
    'UPSERT_FACT_PATTERN_SQL',
    'LIST_FACT_PATTERNS_SQL',
    'COUNT_FACT_PATTERNS_SQL',
    'GET_FACT_PATTERN_SQL',
    'DELETE_FACT_PATTERNS_NOT_IN_SQL',
    'DELETE_ALL_FACT_PATTERNS_SQL',
    'UPSERT_FACT_PLAYBOOK_SQL',
    'LIST_FACT_PLAYBOOKS_SQL',
    'COUNT_FACT_PLAYBOOKS_SQL',
    'GET_FACT_PLAYBOOK_SQL',
    'DELETE_FACT_PLAYBOOKS_NOT_IN_SQL',
    'DELETE_ALL_FACT_PLAYBOOKS_SQL',
    'INSERT_MEMORY_REVIEW_LABEL_SQL',
    'LIST_MEMORY_REVIEW_LABELS_SQL',
    'LIST_MEMORY_REVIEW_LABEL_COUNTS_SQL',
    'COUNT_LABELED_MEMORIES_SQL',
    'COUNT_UNLABELED_MEMORIES_SQL',
    'LIST_ALL_MEMORY_REVIEW_LABEL_COUNTS_SQL',
    'LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL',
    'INSERT_OPEN_LOOP_SQL',
    'GET_OPEN_LOOP_SQL',
    'LIST_OPEN_LOOPS_SQL',
    'LIST_OPEN_LOOPS_BY_STATUS_SQL',
    'LIST_LIMITED_OPEN_LOOPS_SQL',
    'LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL',
    'COUNT_OPEN_LOOPS_SQL',
    'COUNT_OPEN_LOOPS_BY_STATUS_SQL',
    'UPDATE_OPEN_LOOP_STATUS_SQL',
    'UPDATE_EVENT_ERROR',
    'DELETE_EVENT_ERROR',
    'UPDATE_TRACE_EVENT_ERROR',
    'DELETE_TRACE_EVENT_ERROR',
]

def create_user(self, user_id: UUID, email: str, display_name: str | None = None) -> UserRow:
    return self._fetch_one(
        "create_user",
        INSERT_USER_SQL,
        (user_id, email, display_name),
    )

def get_user(self, user_id: UUID) -> UserRow:
    return self._fetch_one("get_user", GET_USER_SQL, (user_id,))

def create_thread(self, title: str, agent_profile_id: str = "assistant_default") -> ThreadRow:
    return self._fetch_one("create_thread", INSERT_THREAD_SQL, (title, agent_profile_id))

def get_thread(self, thread_id: UUID) -> ThreadRow:
    return self._fetch_one("get_thread", GET_THREAD_SQL, (thread_id,))

def get_thread_optional(self, thread_id: UUID) -> ThreadRow | None:
    return self._fetch_optional_one(GET_THREAD_SQL, (thread_id,))

def list_threads(self) -> list[ThreadRow]:
    return self._fetch_all(LIST_THREADS_SQL)

def list_agent_profiles(self) -> list[AgentProfileRow]:
    return self._fetch_all(LIST_AGENT_PROFILES_SQL)

def get_agent_profile_optional(self, profile_id: str) -> AgentProfileRow | None:
    return self._fetch_optional_one(GET_AGENT_PROFILE_SQL, (profile_id,))

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
    return self._fetch_one_with_lock(
        operation_name="append_event",
        lock_query=LOCK_THREAD_EVENTS_SQL,
        lock_key=thread_id,
        query=INSERT_EVENT_SQL,
        params=(thread_id, thread_id, session_id, kind, Jsonb(payload)),
    )

def append_event_if_tail(
    self,
    thread_id: UUID,
    session_id: UUID | None,
    kind: str,
    payload: JsonObject,
    *,
    expected_event_id: UUID,
    expected_sequence_no: int,
) -> EventRow | None:
    """Append only when the prepared user turn is still the thread tail.

        The same transaction-scoped advisory lock used by ``append_event``
        makes the tail comparison and insert one atomic conversation action.
        """

    self._acquire_advisory_lock(LOCK_THREAD_EVENTS_SQL, thread_id)
    tail = self._fetch_optional_one(GET_THREAD_EVENT_TAIL_SQL, (thread_id,))
    if tail is None or tail["id"] != expected_event_id or tail["sequence_no"] != expected_sequence_no:
        return None
    return self._fetch_one(
        "append_event_if_tail",
        INSERT_EVENT_SQL,
        (thread_id, thread_id, session_id, kind, Jsonb(payload)),
    )

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
    memory_type: str = "preference",
    confidence: float | None = None,
    salience: float | None = None,
    confirmation_status: str = "unconfirmed",
    trust_class: str = "deterministic",
    promotion_eligibility: str = "promotable",
    evidence_count: int | None = None,
    independent_source_count: int | None = None,
    extracted_by_model: str | None = None,
    trust_reason: str | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    last_confirmed_at: datetime | None = None,
    agent_profile_id: str = "assistant_default",
) -> MemoryRow:
    return self._fetch_one(
        "create_memory",
        INSERT_MEMORY_SQL,
        (
            memory_key,
            Jsonb(value),
            status,
            Jsonb(source_event_ids),
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
            agent_profile_id,
        ),
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

def get_memory_by_key_and_profile(
    self,
    *,
    memory_key: str,
    agent_profile_id: str,
) -> MemoryRow | None:
    return self._fetch_optional_one(
        GET_MEMORY_BY_KEY_AND_PROFILE_SQL,
        (memory_key, agent_profile_id),
    )

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

def list_unlabeled_review_memories(self, *, limit: int | None = None) -> list[MemoryRow]:
    if limit is None:
        return self._fetch_all(LIST_UNLABELED_REVIEW_MEMORIES_SQL)
    return self._fetch_all(LIST_LIMITED_UNLABELED_REVIEW_MEMORIES_SQL, (limit,))

def list_context_memories(self) -> list[MemoryRow]:
    return self._fetch_all(LIST_CONTEXT_MEMORIES_SQL)

def list_context_memories_for_profile(self, *, agent_profile_id: str) -> list[MemoryRow]:
    return self._fetch_all(LIST_CONTEXT_MEMORIES_FOR_PROFILE_SQL, (agent_profile_id,))

def update_memory(
    self,
    *,
    memory_id: UUID,
    value: JsonValue,
    status: str,
    source_event_ids: list[str],
    memory_type: str = "preference",
    confidence: float | None = None,
    salience: float | None = None,
    confirmation_status: str = "unconfirmed",
    trust_class: str = "deterministic",
    promotion_eligibility: str = "promotable",
    evidence_count: int | None = None,
    independent_source_count: int | None = None,
    extracted_by_model: str | None = None,
    trust_reason: str | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    last_confirmed_at: datetime | None = None,
) -> MemoryRow:
    return self._fetch_one(
        "update_memory",
        UPDATE_MEMORY_SQL,
        (
            Jsonb(value),
            status,
            Jsonb(source_event_ids),
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
            status,
            memory_id,
        ),
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
    return self._fetch_one_with_lock(
        operation_name="append_memory_revision",
        lock_query=LOCK_MEMORY_REVISIONS_SQL,
        lock_key=memory_id,
        query=INSERT_MEMORY_REVISION_SQL,
        params=(
            memory_id,
            memory_id,
            action,
            action,
            memory_key,
            Jsonb(previous_value),
            Jsonb(new_value),
            Jsonb(source_event_ids),
            Jsonb(candidate),
            None if previous_value is None else json.dumps(previous_value, sort_keys=True),
            "{}" if new_value is None else json.dumps(new_value, sort_keys=True),
        ),
    )

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

def upsert_fact_pattern(
    self,
    *,
    pattern_id: UUID,
    pattern_key: str,
    title: str,
    memory_type: str,
    namespace_key: str,
    fact_count: int,
    source_fact_ids: list[str],
    evidence_chain: JsonValue,
    explanation: str,
) -> FactPatternRow:
    return self._fetch_one(
        "upsert_fact_pattern",
        UPSERT_FACT_PATTERN_SQL,
        (
            pattern_id,
            pattern_key,
            title,
            memory_type,
            namespace_key,
            fact_count,
            Jsonb(source_fact_ids),
            Jsonb(evidence_chain),
            explanation,
        ),
    )

def list_fact_patterns(self, *, limit: int) -> list[FactPatternRow]:
    return self._fetch_all(LIST_FACT_PATTERNS_SQL, (limit,))

def count_fact_patterns(self) -> int:
    return self._fetch_count(COUNT_FACT_PATTERNS_SQL)

def get_fact_pattern_optional(self, pattern_id: UUID) -> FactPatternRow | None:
    return self._fetch_optional_one(GET_FACT_PATTERN_SQL, (pattern_id,))

def delete_fact_patterns_not_in(self, pattern_ids: list[UUID]) -> None:
    if not pattern_ids:
        self._execute("delete_all_fact_patterns", DELETE_ALL_FACT_PATTERNS_SQL)
        return
    self._execute("delete_fact_patterns_not_in", DELETE_FACT_PATTERNS_NOT_IN_SQL, (pattern_ids,))

def upsert_fact_playbook(
    self,
    *,
    playbook_id: UUID,
    playbook_key: str,
    pattern_id: UUID,
    pattern_key: str,
    title: str,
    memory_type: str,
    source_fact_ids: list[str],
    source_pattern_ids: list[str],
    steps: JsonValue,
    explanation: str,
) -> FactPlaybookRow:
    return self._fetch_one(
        "upsert_fact_playbook",
        UPSERT_FACT_PLAYBOOK_SQL,
        (
            playbook_id,
            playbook_key,
            pattern_id,
            pattern_key,
            title,
            memory_type,
            Jsonb(source_fact_ids),
            Jsonb(source_pattern_ids),
            Jsonb(steps),
            explanation,
        ),
    )

def list_fact_playbooks(self, *, limit: int) -> list[FactPlaybookRow]:
    return self._fetch_all(LIST_FACT_PLAYBOOKS_SQL, (limit,))

def count_fact_playbooks(self) -> int:
    return self._fetch_count(COUNT_FACT_PLAYBOOKS_SQL)

def get_fact_playbook_optional(self, playbook_id: UUID) -> FactPlaybookRow | None:
    return self._fetch_optional_one(GET_FACT_PLAYBOOK_SQL, (playbook_id,))

def delete_fact_playbooks_not_in(self, playbook_ids: list[UUID]) -> None:
    if not playbook_ids:
        self._execute("delete_all_fact_playbooks", DELETE_ALL_FACT_PLAYBOOKS_SQL)
        return
    self._execute("delete_fact_playbooks_not_in", DELETE_FACT_PLAYBOOKS_NOT_IN_SQL, (playbook_ids,))

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

def list_active_memory_review_label_counts(self) -> list[LabelCountRow]:
    return self._fetch_all(LIST_ACTIVE_MEMORY_REVIEW_LABEL_COUNTS_SQL)

def create_open_loop(
    self,
    *,
    memory_id: UUID | None,
    title: str,
    status: str,
    opened_at: datetime | None,
    due_at: datetime | None,
    resolved_at: datetime | None,
    resolution_note: str | None,
) -> OpenLoopRow:
    return self._fetch_one(
        "create_open_loop",
        INSERT_OPEN_LOOP_SQL,
        (
            memory_id,
            title,
            status,
            opened_at,
            due_at,
            resolved_at,
            resolution_note,
        ),
    )

def get_open_loop(self, open_loop_id: UUID) -> OpenLoopRow:
    return self._fetch_one("get_open_loop", GET_OPEN_LOOP_SQL, (open_loop_id,))

def get_open_loop_optional(self, open_loop_id: UUID) -> OpenLoopRow | None:
    return self._fetch_optional_one(GET_OPEN_LOOP_SQL, (open_loop_id,))

def list_open_loops(
    self,
    *,
    status: str | None = None,
    limit: int | None = None,
) -> list[OpenLoopRow]:
    if status is None and limit is None:
        return self._fetch_all(LIST_OPEN_LOOPS_SQL)
    if status is None:
        return self._fetch_all(LIST_LIMITED_OPEN_LOOPS_SQL, (limit,))
    if limit is None:
        return self._fetch_all(LIST_OPEN_LOOPS_BY_STATUS_SQL, (status,))
    return self._fetch_all(LIST_LIMITED_OPEN_LOOPS_BY_STATUS_SQL, (status, limit))

def count_open_loops(self, *, status: str | None = None) -> int:
    if status is None:
        return self._fetch_count(COUNT_OPEN_LOOPS_SQL)
    return self._fetch_count(COUNT_OPEN_LOOPS_BY_STATUS_SQL, (status,))

def update_open_loop_status_optional(
    self,
    *,
    open_loop_id: UUID,
    status: str,
    resolved_at: datetime | None,
    resolution_note: str | None,
) -> OpenLoopRow | None:
    return self._fetch_optional_one(
        UPDATE_OPEN_LOOP_STATUS_SQL,
        (
            status,
            status,
            resolved_at,
            status,
            resolution_note,
            open_loop_id,
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
