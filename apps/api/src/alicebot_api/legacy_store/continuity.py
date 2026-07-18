"""Continuity-domain legacy-store carrier."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from psycopg.types.json import Jsonb

if TYPE_CHECKING:
    from alicebot_api.store import (
        ContinuityArtifactCopyRow,
        ContinuityArtifactRow,
        ContinuityArtifactSegmentRow,
        ContinuityCaptureEventRow,
        ContinuityCorrectionEventRow,
        ContinuityObjectEvidenceLinkRow,
        ContinuityObjectEvidenceRow,
        ContinuityObjectRow,
        ContinuityRecallCandidateRow,
        ContinuityStoreInvariantError,
        ContradictionCaseRow,
        EvalCaseRow,
        EvalResultRow,
        EvalRunRow,
        EvalSuiteRow,
        JsonObject,
        MemoryOperationCandidateRow,
        MemoryOperationRow,
        RetrievalCandidateRow,
        RetrievalRunRow,
        TrustSignalRow,
    )

INSERT_CONTINUITY_CAPTURE_EVENT_SQL = """
                INSERT INTO continuity_capture_events (
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason,
                  created_at
                """

GET_CONTINUITY_CAPTURE_EVENT_SQL = """
                SELECT
                  id,
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason,
                  created_at
                FROM continuity_capture_events
                WHERE id = %s
                """

LIST_CONTINUITY_CAPTURE_EVENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  raw_content,
                  explicit_signal,
                  admission_posture,
                  admission_reason,
                  created_at
                FROM continuity_capture_events
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

COUNT_CONTINUITY_CAPTURE_EVENTS_SQL = """
                SELECT COUNT(*) AS count
                FROM continuity_capture_events
                """

INSERT_CONTINUITY_OBJECT_SQL = """
                INSERT INTO continuity_objects (
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id
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
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                """

GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE capture_event_id = %s
                """

GET_CONTINUITY_OBJECT_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE id = %s
                """

GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE provenance ->> 'sync_fingerprint' = %s
                  AND provenance ->> 'candidate_id' = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """

LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE capture_event_id = ANY(%s)
                ORDER BY created_at DESC, id DESC
                """

LIST_CONTINUITY_REVIEW_QUEUE_SQL = """
                SELECT
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                FROM continuity_objects
                WHERE status = ANY(%s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_CONTINUITY_REVIEW_QUEUE_SQL = """
                SELECT COUNT(*) AS count
                FROM continuity_objects
                WHERE status = ANY(%s)
                """

LIST_CONTINUITY_RECALL_CANDIDATES_SQL = """
                SELECT
                  continuity_objects.id,
                  continuity_objects.user_id,
                  continuity_objects.capture_event_id,
                  continuity_objects.object_type,
                  continuity_objects.status,
                  continuity_objects.is_preserved,
                  continuity_objects.is_searchable,
                  continuity_objects.is_promotable,
                  continuity_objects.title,
                  continuity_objects.body,
                  continuity_objects.provenance,
                  continuity_objects.confidence,
                  continuity_objects.last_confirmed_at,
                  continuity_objects.supersedes_object_id,
                  continuity_objects.superseded_by_object_id,
                  continuity_objects.created_at AS object_created_at,
                  continuity_objects.updated_at AS object_updated_at,
                  continuity_capture_events.admission_posture,
                  continuity_capture_events.admission_reason,
                  continuity_capture_events.explicit_signal,
                  continuity_capture_events.created_at AS capture_created_at
                FROM continuity_objects
                JOIN continuity_capture_events
                  ON continuity_capture_events.id = continuity_objects.capture_event_id
                 AND continuity_capture_events.user_id = continuity_objects.user_id
                ORDER BY continuity_objects.created_at DESC, continuity_objects.id DESC
                """

INSERT_RETRIEVAL_RUN_SQL = """
                INSERT INTO retrieval_runs (
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until
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
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until,
                  created_at
                """

LIST_RETRIEVAL_RUNS_SQL = """
                SELECT
                  id,
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until,
                  created_at
                FROM retrieval_runs
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

GET_RETRIEVAL_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  source_surface,
                  ranking_strategy,
                  query_text,
                  request_scope,
                  result_ids,
                  exclusion_summary,
                  candidate_count,
                  selected_count,
                  debug_enabled,
                  retention_until,
                  created_at
                FROM retrieval_runs
                WHERE id = %s
                """

UPSERT_EVAL_SUITE_SQL = """
                INSERT INTO eval_suites (
                  user_id,
                  suite_key,
                  title,
                  description,
                  evaluator_kind,
                  fixture_schema_version,
                  fixture_source_path,
                  case_count,
                  suite_order,
                  metadata
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
                  %s
                )
                ON CONFLICT (user_id, suite_key)
                DO UPDATE
                SET title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    evaluator_kind = EXCLUDED.evaluator_kind,
                    fixture_schema_version = EXCLUDED.fixture_schema_version,
                    fixture_source_path = EXCLUDED.fixture_source_path,
                    case_count = EXCLUDED.case_count,
                    suite_order = EXCLUDED.suite_order,
                    metadata = EXCLUDED.metadata,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  suite_key,
                  title,
                  description,
                  evaluator_kind,
                  fixture_schema_version,
                  fixture_source_path,
                  case_count,
                  suite_order,
                  metadata,
                  created_at,
                  updated_at
                """

LIST_EVAL_SUITES_SQL = """
                SELECT
                  id,
                  user_id,
                  suite_key,
                  title,
                  description,
                  evaluator_kind,
                  fixture_schema_version,
                  fixture_source_path,
                  case_count,
                  suite_order,
                  metadata,
                  created_at,
                  updated_at
                FROM eval_suites
                ORDER BY suite_order ASC, suite_key ASC
                """

DELETE_EVAL_SUITES_NOT_IN_SQL = """
                DELETE FROM eval_suites
                WHERE user_id = app.current_user_id()
                  AND NOT (suite_key = ANY(%s))
                """

UPSERT_EVAL_CASE_SQL = """
                INSERT INTO eval_cases (
                  user_id,
                  suite_id,
                  case_key,
                  title,
                  evaluator_kind,
                  case_order,
                  fixture,
                  expectations
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, suite_id, case_key)
                DO UPDATE
                SET title = EXCLUDED.title,
                    evaluator_kind = EXCLUDED.evaluator_kind,
                    case_order = EXCLUDED.case_order,
                    fixture = EXCLUDED.fixture,
                    expectations = EXCLUDED.expectations,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  suite_id,
                  case_key,
                  title,
                  evaluator_kind,
                  case_order,
                  fixture,
                  expectations,
                  created_at,
                  updated_at
                """

LIST_EVAL_CASES_FOR_SUITE_SQL = """
                SELECT
                  id,
                  user_id,
                  suite_id,
                  case_key,
                  title,
                  evaluator_kind,
                  case_order,
                  fixture,
                  expectations,
                  created_at,
                  updated_at
                FROM eval_cases
                WHERE suite_id = %s
                ORDER BY case_order ASC, case_key ASC
                """

DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL = """
                DELETE FROM eval_cases
                WHERE user_id = app.current_user_id()
                  AND suite_id = %s
                  AND NOT (case_key = ANY(%s))
                """

INSERT_EVAL_RUN_SQL = """
                INSERT INTO eval_runs (
                  user_id,
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest
                )
                VALUES (
                  app.current_user_id(),
                  %s,
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
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest,
                  created_at
                """

LIST_EVAL_RUNS_SQL = """
                SELECT
                  id,
                  user_id,
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest,
                  created_at
                FROM eval_runs
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

GET_EVAL_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  fixture_schema_version,
                  fixture_source_path,
                  requested_suite_keys,
                  status,
                  summary,
                  report,
                  report_digest,
                  created_at
                FROM eval_runs
                WHERE id = %s
                """

INSERT_EVAL_RESULT_SQL = """
                INSERT INTO eval_results (
                  user_id,
                  eval_run_id,
                  suite_key,
                  case_key,
                  status,
                  score,
                  summary,
                  details
                )
                VALUES (
                  app.current_user_id(),
                  %s,
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
                  eval_run_id,
                  suite_key,
                  case_key,
                  status,
                  score,
                  summary,
                  details,
                  created_at
                """

LIST_EVAL_RESULTS_FOR_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  eval_run_id,
                  suite_key,
                  case_key,
                  status,
                  score,
                  summary,
                  details,
                  created_at
                FROM eval_results
                WHERE eval_run_id = %s
                ORDER BY suite_key ASC, case_key ASC, created_at ASC, id ASC
                """

INSERT_RETRIEVAL_CANDIDATE_SQL = """
                INSERT INTO retrieval_candidates (
                  user_id,
                  retrieval_run_id,
                  continuity_object_id,
                  rank,
                  selected,
                  exclusion_reason,
                  lexical_score,
                  semantic_score,
                  entity_edge_score,
                  temporal_score,
                  trust_score,
                  relevance,
                  scope_matches,
                  stage_details,
                  ordering,
                  title,
                  object_type,
                  status
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
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  retrieval_run_id,
                  continuity_object_id,
                  rank,
                  selected,
                  exclusion_reason,
                  lexical_score,
                  semantic_score,
                  entity_edge_score,
                  temporal_score,
                  trust_score,
                  relevance,
                  scope_matches,
                  stage_details,
                  ordering,
                  title,
                  object_type,
                  status,
                  created_at
                """

LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL = """
                SELECT
                  id,
                  user_id,
                  retrieval_run_id,
                  continuity_object_id,
                  rank,
                  selected,
                  exclusion_reason,
                  lexical_score,
                  semantic_score,
                  entity_edge_score,
                  temporal_score,
                  trust_score,
                  relevance,
                  scope_matches,
                  stage_details,
                  ordering,
                  title,
                  object_type,
                  status,
                  created_at
                FROM retrieval_candidates
                WHERE retrieval_run_id = %s
                ORDER BY selected DESC, rank ASC NULLS LAST, relevance DESC, id ASC
                """

UPSERT_CONTINUITY_ARTIFACT_SQL = """
                INSERT INTO continuity_artifacts (
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, source_kind, import_source_path, relative_path)
                DO NOTHING
                RETURNING
                  id,
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type,
                  created_at
                """

GET_CONTINUITY_ARTIFACT_SQL = """
                SELECT
                  id,
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type,
                  created_at
                FROM continuity_artifacts
                WHERE id = %s
                """

GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL = """
                SELECT
                  id,
                  user_id,
                  source_kind,
                  import_source_path,
                  relative_path,
                  display_name,
                  media_type,
                  created_at
                FROM continuity_artifacts
                WHERE source_kind = %s
                  AND import_source_path = %s
                  AND relative_path = %s
                """

UPSERT_CONTINUITY_ARTIFACT_COPY_SQL = """
                INSERT INTO continuity_artifact_copies (
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  %s,
                  %s
                )
                ON CONFLICT (user_id, artifact_id, checksum_sha256)
                DO NOTHING
                RETURNING
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                """

GET_CONTINUITY_ARTIFACT_COPY_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                FROM continuity_artifact_copies
                WHERE id = %s
                """

GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                FROM continuity_artifact_copies
                WHERE artifact_id = %s
                  AND checksum_sha256 = %s
                """

LIST_CONTINUITY_ARTIFACT_COPIES_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  checksum_sha256,
                  content_text,
                  content_length_bytes,
                  content_encoding,
                  created_at
                FROM continuity_artifact_copies
                WHERE artifact_id = %s
                ORDER BY created_at ASC, id ASC
                """

UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL = """
                INSERT INTO continuity_artifact_segments (
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256
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
                  %s
                )
                ON CONFLICT (user_id, artifact_copy_id, source_item_id)
                DO NOTHING
                RETURNING
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                """

GET_CONTINUITY_ARTIFACT_SEGMENT_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                FROM continuity_artifact_segments
                WHERE id = %s
                """

GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                FROM continuity_artifact_segments
                WHERE artifact_copy_id = %s
                  AND source_item_id = %s
                """

LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  artifact_id,
                  artifact_copy_id,
                  source_item_id,
                  sequence_no,
                  segment_kind,
                  locator,
                  raw_content,
                  checksum_sha256,
                  created_at
                FROM continuity_artifact_segments
                WHERE artifact_id = %s
                ORDER BY sequence_no ASC, created_at ASC, id ASC
                """

INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL = """
                INSERT INTO continuity_object_evidence_links (
                  user_id,
                  continuity_object_id,
                  artifact_id,
                  artifact_copy_id,
                  artifact_segment_id,
                  relationship
                )
                VALUES (
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
                  continuity_object_id,
                  artifact_id,
                  artifact_copy_id,
                  artifact_segment_id,
                  relationship,
                  created_at
                """

LIST_CONTINUITY_OBJECT_EVIDENCE_SQL = """
                SELECT
                  links.id,
                  links.user_id,
                  links.continuity_object_id,
                  links.artifact_id,
                  links.artifact_copy_id,
                  links.artifact_segment_id,
                  links.relationship,
                  links.created_at,
                  artifacts.source_kind,
                  artifacts.import_source_path,
                  artifacts.relative_path,
                  artifacts.display_name,
                  artifacts.media_type,
                  artifacts.created_at AS artifact_created_at,
                  copies.checksum_sha256 AS artifact_copy_checksum_sha256,
                  copies.content_text AS artifact_copy_content_text,
                  copies.content_length_bytes AS artifact_copy_content_length_bytes,
                  copies.content_encoding AS artifact_copy_content_encoding,
                  copies.created_at AS artifact_copy_created_at,
                  segments.source_item_id AS segment_source_item_id,
                  segments.sequence_no AS segment_sequence_no,
                  segments.segment_kind,
                  segments.locator AS segment_locator,
                  segments.raw_content AS segment_raw_content,
                  segments.checksum_sha256 AS segment_checksum_sha256,
                  segments.created_at AS segment_created_at
                FROM continuity_object_evidence_links AS links
                JOIN continuity_artifacts AS artifacts
                  ON artifacts.id = links.artifact_id
                 AND artifacts.user_id = links.user_id
                JOIN continuity_artifact_copies AS copies
                  ON copies.id = links.artifact_copy_id
                 AND copies.user_id = links.user_id
                LEFT JOIN continuity_artifact_segments AS segments
                  ON segments.id = links.artifact_segment_id
                 AND segments.user_id = links.user_id
                WHERE links.continuity_object_id = %s
                ORDER BY links.created_at ASC, links.id ASC
                """

UPDATE_CONTINUITY_OBJECT_SQL = """
                UPDATE continuity_objects
                SET status = %s,
                    is_preserved = %s,
                    is_searchable = %s,
                    is_promotable = %s,
                    title = %s,
                    body = %s,
                    provenance = %s,
                    confidence = %s,
                    last_confirmed_at = %s,
                    supersedes_object_id = %s,
                    superseded_by_object_id = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  capture_event_id,
                  object_type,
                  status,
                  is_preserved,
                  is_searchable,
                  is_promotable,
                  title,
                  body,
                  provenance,
                  confidence,
                  last_confirmed_at,
                  supersedes_object_id,
                  superseded_by_object_id,
                  created_at,
                  updated_at
                """

INSERT_CONTINUITY_CORRECTION_EVENT_SQL = """
                INSERT INTO continuity_correction_events (
                  user_id,
                  continuity_object_id,
                  action,
                  reason,
                  before_snapshot,
                  after_snapshot,
                  payload
                )
                VALUES (
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
                  continuity_object_id,
                  action,
                  reason,
                  before_snapshot,
                  after_snapshot,
                  payload,
                  created_at
                """

LIST_CONTINUITY_CORRECTION_EVENTS_SQL = """
                SELECT
                  id,
                  user_id,
                  continuity_object_id,
                  action,
                  reason,
                  before_snapshot,
                  after_snapshot,
                  payload,
                  created_at
                FROM continuity_correction_events
                WHERE continuity_object_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

INSERT_CONTRADICTION_CASE_SQL = """
                INSERT INTO contradiction_cases (
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at
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
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                """

UPDATE_CONTRADICTION_CASE_SQL = """
                UPDATE contradiction_cases
                SET continuity_object_id = %s,
                    counterpart_object_id = %s,
                    kind = %s,
                    status = %s,
                    rationale = %s,
                    detection_payload = %s,
                    resolution_action = %s,
                    resolution_note = %s,
                    continuity_object_updated_at = %s,
                    counterpart_object_updated_at = %s,
                    resolved_at = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                """

GET_CONTRADICTION_CASE_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE id = %s
                """

GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE canonical_key = %s
                """

LIST_CONTRADICTION_CASES_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE status = ANY(%s)
                  AND (%s::uuid IS NULL OR continuity_object_id = %s OR counterpart_object_id = %s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_CONTRADICTION_CASES_SQL = """
                SELECT COUNT(*) AS count
                FROM contradiction_cases
                WHERE status = ANY(%s)
                  AND (%s::uuid IS NULL OR continuity_object_id = %s OR counterpart_object_id = %s)
                """

LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL = """
                SELECT
                  id,
                  user_id,
                  canonical_key,
                  continuity_object_id,
                  counterpart_object_id,
                  kind,
                  status,
                  rationale,
                  detection_payload,
                  resolution_action,
                  resolution_note,
                  continuity_object_updated_at,
                  counterpart_object_updated_at,
                  resolved_at,
                  created_at,
                  updated_at
                FROM contradiction_cases
                WHERE status = ANY(%s)
                  AND (
                    continuity_object_id = ANY(%s)
                    OR counterpart_object_id = ANY(%s)
                  )
                ORDER BY updated_at DESC, created_at DESC, id DESC
                """

UPSERT_TRUST_SIGNAL_SQL = """
                INSERT INTO trust_signals (
                  user_id,
                  continuity_object_id,
                  signal_key,
                  signal_type,
                  signal_state,
                  direction,
                  magnitude,
                  reason,
                  contradiction_case_id,
                  related_continuity_object_id,
                  payload
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
                  %s
                )
                ON CONFLICT (user_id, signal_key)
                DO UPDATE
                SET continuity_object_id = EXCLUDED.continuity_object_id,
                    signal_type = EXCLUDED.signal_type,
                    signal_state = EXCLUDED.signal_state,
                    direction = EXCLUDED.direction,
                    magnitude = EXCLUDED.magnitude,
                    reason = EXCLUDED.reason,
                    contradiction_case_id = EXCLUDED.contradiction_case_id,
                    related_continuity_object_id = EXCLUDED.related_continuity_object_id,
                    payload = EXCLUDED.payload,
                    updated_at = clock_timestamp()
                RETURNING
                  id,
                  user_id,
                  continuity_object_id,
                  signal_key,
                  signal_type,
                  signal_state,
                  direction,
                  magnitude,
                  reason,
                  contradiction_case_id,
                  related_continuity_object_id,
                  payload,
                  created_at,
                  updated_at
                """

LIST_TRUST_SIGNALS_SQL = """
                SELECT
                  id,
                  user_id,
                  continuity_object_id,
                  signal_key,
                  signal_type,
                  signal_state,
                  direction,
                  magnitude,
                  reason,
                  contradiction_case_id,
                  related_continuity_object_id,
                  payload,
                  created_at,
                  updated_at
                FROM trust_signals
                WHERE (%s::uuid IS NULL OR continuity_object_id = %s)
                  AND (%s::text IS NULL OR signal_state = %s)
                  AND (%s::text IS NULL OR signal_type = %s)
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """

COUNT_TRUST_SIGNALS_SQL = """
                SELECT COUNT(*) AS count
                FROM trust_signals
                WHERE (%s::uuid IS NULL OR continuity_object_id = %s)
                  AND (%s::text IS NULL OR signal_state = %s)
                  AND (%s::text IS NULL OR signal_type = %s)
                """

INSERT_MEMORY_OPERATION_CANDIDATE_SQL = """
                INSERT INTO memory_operation_candidates (
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot
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
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                """

GET_MEMORY_OPERATION_CANDIDATE_SQL = """
                SELECT
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                FROM memory_operation_candidates
                WHERE id = %s
                """

GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL = """
                SELECT
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                FROM memory_operation_candidates
                WHERE sync_fingerprint = %s
                  AND source_candidate_id = %s
                """

LIST_MEMORY_OPERATION_CANDIDATES_SQL = """
                SELECT
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                FROM memory_operation_candidates
                WHERE (%s::text IS NULL OR policy_action = %s::text)
                  AND (%s::text IS NULL OR operation_type = %s::text)
                  AND (%s::text IS NULL OR sync_fingerprint = %s::text)
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

COUNT_MEMORY_OPERATION_CANDIDATES_SQL = """
                SELECT COUNT(*) AS count
                FROM memory_operation_candidates
                WHERE (%s::text IS NULL OR policy_action = %s::text)
                  AND (%s::text IS NULL OR operation_type = %s::text)
                  AND (%s::text IS NULL OR sync_fingerprint = %s::text)
                """

UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL = """
                UPDATE memory_operation_candidates
                SET applied_operation_id = %s,
                    applied_at = %s
                WHERE id = %s
                RETURNING
                  id,
                  user_id,
                  sync_fingerprint,
                  source_kind,
                  source_candidate_id,
                  source_candidate_type,
                  candidate_payload,
                  source_scope,
                  operation_type,
                  operation_reason,
                  policy_action,
                  policy_reason,
                  target_continuity_object_id,
                  target_snapshot,
                  applied_operation_id,
                  created_at,
                  applied_at
                """

INSERT_MEMORY_OPERATION_SQL = """
                INSERT INTO memory_operations (
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details
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
                  %s
                )
                RETURNING
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details,
                  created_at
                """

GET_MEMORY_OPERATION_SQL = """
                SELECT
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details,
                  created_at
                FROM memory_operations
                WHERE id = %s
                """

LIST_MEMORY_OPERATIONS_SQL = """
                SELECT
                  id,
                  user_id,
                  candidate_id,
                  operation_type,
                  status,
                  sync_fingerprint,
                  target_continuity_object_id,
                  resulting_continuity_object_id,
                  correction_event_id,
                  before_snapshot,
                  after_snapshot,
                  details,
                  created_at
                FROM memory_operations
                WHERE (%s::text IS NULL OR sync_fingerprint = %s::text)
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """

COUNT_MEMORY_OPERATIONS_SQL = """
                SELECT COUNT(*) AS count
                FROM memory_operations
                WHERE (%s::text IS NULL OR sync_fingerprint = %s::text)
                """

__all__ = [
    'INSERT_CONTINUITY_CAPTURE_EVENT_SQL',
    'GET_CONTINUITY_CAPTURE_EVENT_SQL',
    'LIST_CONTINUITY_CAPTURE_EVENTS_SQL',
    'COUNT_CONTINUITY_CAPTURE_EVENTS_SQL',
    'INSERT_CONTINUITY_OBJECT_SQL',
    'GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL',
    'GET_CONTINUITY_OBJECT_SQL',
    'GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL',
    'LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL',
    'LIST_CONTINUITY_REVIEW_QUEUE_SQL',
    'COUNT_CONTINUITY_REVIEW_QUEUE_SQL',
    'LIST_CONTINUITY_RECALL_CANDIDATES_SQL',
    'INSERT_RETRIEVAL_RUN_SQL',
    'LIST_RETRIEVAL_RUNS_SQL',
    'GET_RETRIEVAL_RUN_SQL',
    'UPSERT_EVAL_SUITE_SQL',
    'LIST_EVAL_SUITES_SQL',
    'DELETE_EVAL_SUITES_NOT_IN_SQL',
    'UPSERT_EVAL_CASE_SQL',
    'LIST_EVAL_CASES_FOR_SUITE_SQL',
    'DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL',
    'INSERT_EVAL_RUN_SQL',
    'LIST_EVAL_RUNS_SQL',
    'GET_EVAL_RUN_SQL',
    'INSERT_EVAL_RESULT_SQL',
    'LIST_EVAL_RESULTS_FOR_RUN_SQL',
    'INSERT_RETRIEVAL_CANDIDATE_SQL',
    'LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL',
    'UPSERT_CONTINUITY_ARTIFACT_SQL',
    'GET_CONTINUITY_ARTIFACT_SQL',
    'GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL',
    'UPSERT_CONTINUITY_ARTIFACT_COPY_SQL',
    'GET_CONTINUITY_ARTIFACT_COPY_SQL',
    'GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL',
    'LIST_CONTINUITY_ARTIFACT_COPIES_SQL',
    'UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL',
    'GET_CONTINUITY_ARTIFACT_SEGMENT_SQL',
    'GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL',
    'LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL',
    'INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL',
    'LIST_CONTINUITY_OBJECT_EVIDENCE_SQL',
    'UPDATE_CONTINUITY_OBJECT_SQL',
    'INSERT_CONTINUITY_CORRECTION_EVENT_SQL',
    'LIST_CONTINUITY_CORRECTION_EVENTS_SQL',
    'INSERT_CONTRADICTION_CASE_SQL',
    'UPDATE_CONTRADICTION_CASE_SQL',
    'GET_CONTRADICTION_CASE_SQL',
    'GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL',
    'LIST_CONTRADICTION_CASES_SQL',
    'COUNT_CONTRADICTION_CASES_SQL',
    'LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL',
    'UPSERT_TRUST_SIGNAL_SQL',
    'LIST_TRUST_SIGNALS_SQL',
    'COUNT_TRUST_SIGNALS_SQL',
    'INSERT_MEMORY_OPERATION_CANDIDATE_SQL',
    'GET_MEMORY_OPERATION_CANDIDATE_SQL',
    'GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL',
    'LIST_MEMORY_OPERATION_CANDIDATES_SQL',
    'COUNT_MEMORY_OPERATION_CANDIDATES_SQL',
    'UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL',
    'INSERT_MEMORY_OPERATION_SQL',
    'GET_MEMORY_OPERATION_SQL',
    'LIST_MEMORY_OPERATIONS_SQL',
    'COUNT_MEMORY_OPERATIONS_SQL',
]

def create_continuity_capture_event(
    self,
    *,
    raw_content: str,
    explicit_signal: str | None,
    admission_posture: str,
    admission_reason: str,
) -> ContinuityCaptureEventRow:
    return self._fetch_one(
        "create_continuity_capture_event",
        INSERT_CONTINUITY_CAPTURE_EVENT_SQL,
        (
            raw_content,
            explicit_signal,
            admission_posture,
            admission_reason,
        ),
    )
def get_continuity_capture_event_optional(
    self,
    capture_event_id: UUID,
) -> ContinuityCaptureEventRow | None:
    return self._fetch_optional_one(
        GET_CONTINUITY_CAPTURE_EVENT_SQL,
        (capture_event_id,),
    )

def list_continuity_capture_events(self, *, limit: int) -> list[ContinuityCaptureEventRow]:
    return self._fetch_all(LIST_CONTINUITY_CAPTURE_EVENTS_SQL, (limit,))

def count_continuity_capture_events(self) -> int:
    return self._fetch_count(COUNT_CONTINUITY_CAPTURE_EVENTS_SQL)

def create_continuity_object(
    self,
    *,
    capture_event_id: UUID,
    object_type: str,
    status: str,
    title: str,
    body: JsonObject,
    provenance: JsonObject,
    confidence: float,
    is_preserved: bool | None = None,
    is_searchable: bool | None = None,
    is_promotable: bool | None = None,
    last_confirmed_at: datetime | None = None,
    supersedes_object_id: UUID | None = None,
    superseded_by_object_id: UUID | None = None,
) -> ContinuityObjectRow:
    resolved_is_preserved = True if is_preserved is None else is_preserved
    resolved_is_searchable = (
        self._default_continuity_searchable(object_type) if is_searchable is None else is_searchable
    )
    resolved_is_promotable = (
        self._default_continuity_promotable(object_type) if is_promotable is None else is_promotable
    )
    return self._fetch_one(
        "create_continuity_object",
        INSERT_CONTINUITY_OBJECT_SQL,
        (
            capture_event_id,
            object_type,
            status,
            resolved_is_preserved,
            resolved_is_searchable,
            resolved_is_promotable,
            title,
            Jsonb(body),
            Jsonb(provenance),
            confidence,
            last_confirmed_at,
            supersedes_object_id,
            superseded_by_object_id,
        ),
    )

def get_continuity_object_by_capture_event_optional(
    self,
    capture_event_id: UUID,
) -> ContinuityObjectRow | None:
    return self._fetch_optional_one(
        GET_CONTINUITY_OBJECT_BY_CAPTURE_EVENT_SQL,
        (capture_event_id,),
    )

def list_continuity_objects_for_capture_events(
    self,
    capture_event_ids: list[UUID],
) -> list[ContinuityObjectRow]:
    if not capture_event_ids:
        return []
    return self._fetch_all(
        LIST_CONTINUITY_OBJECTS_FOR_CAPTURE_EVENTS_SQL,
        (capture_event_ids,),
    )

def get_continuity_object_optional(
    self,
    continuity_object_id: UUID,
) -> ContinuityObjectRow | None:
    return self._fetch_optional_one(
        GET_CONTINUITY_OBJECT_SQL,
        (continuity_object_id,),
    )

def get_continuity_object_by_commit_fingerprint_optional(
    self,
    *,
    sync_fingerprint: str,
    candidate_id: str,
) -> ContinuityObjectRow | None:
    return self._fetch_optional_one(
        GET_CONTINUITY_OBJECT_BY_COMMIT_FINGERPRINT_SQL,
        (sync_fingerprint, candidate_id),
    )

def list_continuity_review_queue(
    self,
    *,
    statuses: Sequence[str],
    limit: int,
) -> list[ContinuityObjectRow]:
    return self._fetch_all(
        LIST_CONTINUITY_REVIEW_QUEUE_SQL,
        (statuses, limit),
    )

def count_continuity_review_queue(
    self,
    *,
    statuses: Sequence[str],
) -> int:
    return self._fetch_count(
        COUNT_CONTINUITY_REVIEW_QUEUE_SQL,
        (statuses,),
    )

def list_continuity_recall_candidates(self) -> list[ContinuityRecallCandidateRow]:
    return self._fetch_all(LIST_CONTINUITY_RECALL_CANDIDATES_SQL)

def upsert_eval_suite(
    self,
    *,
    suite_key: str,
    title: str,
    description: str,
    evaluator_kind: str,
    fixture_schema_version: str,
    fixture_source_path: str,
    case_count: int,
    suite_order: int,
    metadata: JsonObject,
) -> EvalSuiteRow:
    return self._fetch_one(
        "upsert_eval_suite",
        UPSERT_EVAL_SUITE_SQL,
        (
            suite_key,
            title,
            description,
            evaluator_kind,
            fixture_schema_version,
            fixture_source_path,
            case_count,
            suite_order,
            Jsonb(metadata),
        ),
    )

def list_eval_suites(self) -> list[EvalSuiteRow]:
    return self._fetch_all(LIST_EVAL_SUITES_SQL)

def delete_eval_suites_not_in(self, suite_keys: list[str]) -> None:
    self._execute("delete_eval_suites_not_in", DELETE_EVAL_SUITES_NOT_IN_SQL, (suite_keys,))

def upsert_eval_case(
    self,
    *,
    suite_id: UUID,
    case_key: str,
    title: str,
    evaluator_kind: str,
    case_order: int,
    fixture: JsonObject,
    expectations: JsonObject,
) -> EvalCaseRow:
    return self._fetch_one(
        "upsert_eval_case",
        UPSERT_EVAL_CASE_SQL,
        (
            suite_id,
            case_key,
            title,
            evaluator_kind,
            case_order,
            Jsonb(fixture),
            Jsonb(expectations),
        ),
    )

def list_eval_cases_for_suite(self, suite_id: UUID) -> list[EvalCaseRow]:
    return self._fetch_all(LIST_EVAL_CASES_FOR_SUITE_SQL, (suite_id,))

def delete_eval_cases_for_suite_not_in(self, *, suite_id: UUID, case_keys: list[str]) -> None:
    self._execute(
        "delete_eval_cases_for_suite_not_in",
        DELETE_EVAL_CASES_FOR_SUITE_NOT_IN_SQL,
        (suite_id, case_keys),
    )

def create_eval_run(
    self,
    *,
    fixture_schema_version: str,
    fixture_source_path: str,
    requested_suite_keys: list[str],
    status: str,
    summary: JsonObject,
    report: JsonObject,
    report_digest: str,
) -> EvalRunRow:
    return self._fetch_one(
        "create_eval_run",
        INSERT_EVAL_RUN_SQL,
        (
            fixture_schema_version,
            fixture_source_path,
            Jsonb(requested_suite_keys),
            status,
            Jsonb(summary),
            Jsonb(report),
            report_digest,
        ),
    )

def list_eval_runs(self, *, limit: int) -> list[EvalRunRow]:
    return self._fetch_all(LIST_EVAL_RUNS_SQL, (limit,))

def get_eval_run_optional(self, eval_run_id: UUID) -> EvalRunRow | None:
    return self._fetch_optional_one(GET_EVAL_RUN_SQL, (eval_run_id,))

def create_eval_result(
    self,
    *,
    eval_run_id: UUID,
    suite_key: str,
    case_key: str,
    status: str,
    score: float,
    summary: JsonObject,
    details: JsonObject,
) -> EvalResultRow:
    return self._fetch_one(
        "create_eval_result",
        INSERT_EVAL_RESULT_SQL,
        (
            eval_run_id,
            suite_key,
            case_key,
            status,
            score,
            Jsonb(summary),
            Jsonb(details),
        ),
    )

def list_eval_results_for_run(self, eval_run_id: UUID) -> list[EvalResultRow]:
    return self._fetch_all(LIST_EVAL_RESULTS_FOR_RUN_SQL, (eval_run_id,))

def create_retrieval_run(
    self,
    *,
    source_surface: str,
    ranking_strategy: str,
    query_text: str | None,
    request_scope: JsonObject,
    result_ids: list[str],
    exclusion_summary: JsonObject,
    candidate_count: int,
    selected_count: int,
    debug_enabled: bool,
    retention_until: datetime,
) -> RetrievalRunRow:
    return self._fetch_one(
        "create_retrieval_run",
        INSERT_RETRIEVAL_RUN_SQL,
        (
            source_surface,
            ranking_strategy,
            query_text,
            Jsonb(request_scope),
            Jsonb(result_ids),
            Jsonb(exclusion_summary),
            candidate_count,
            selected_count,
            debug_enabled,
            retention_until,
        ),
    )

def list_retrieval_runs(self, *, limit: int) -> list[RetrievalRunRow]:
    return self._fetch_all(LIST_RETRIEVAL_RUNS_SQL, (limit,))

def get_retrieval_run_optional(self, retrieval_run_id: UUID) -> RetrievalRunRow | None:
    return self._fetch_optional_one(GET_RETRIEVAL_RUN_SQL, (retrieval_run_id,))

def create_retrieval_candidate(
    self,
    *,
    retrieval_run_id: UUID,
    continuity_object_id: UUID,
    rank: int | None,
    selected: bool,
    exclusion_reason: str | None,
    lexical_score: float,
    semantic_score: float,
    entity_edge_score: float,
    temporal_score: float,
    trust_score: float,
    relevance: float,
    scope_matches: list[JsonObject],
    stage_details: JsonObject,
    ordering: JsonObject,
    title: str,
    object_type: str,
    status: str,
) -> RetrievalCandidateRow:
    return self._fetch_one(
        "create_retrieval_candidate",
        INSERT_RETRIEVAL_CANDIDATE_SQL,
        (
            retrieval_run_id,
            continuity_object_id,
            rank,
            selected,
            exclusion_reason,
            lexical_score,
            semantic_score,
            entity_edge_score,
            temporal_score,
            trust_score,
            relevance,
            Jsonb(scope_matches),
            Jsonb(stage_details),
            Jsonb(ordering),
            title,
            object_type,
            status,
        ),
    )

def list_retrieval_candidates_for_run(
    self,
    retrieval_run_id: UUID,
) -> list[RetrievalCandidateRow]:
    return self._fetch_all(LIST_RETRIEVAL_CANDIDATES_FOR_RUN_SQL, (retrieval_run_id,))

def upsert_continuity_artifact(
    self,
    *,
    source_kind: str,
    import_source_path: str,
    relative_path: str,
    display_name: str,
    media_type: str,
) -> ContinuityArtifactRow:
    created = self._fetch_optional_one(
        UPSERT_CONTINUITY_ARTIFACT_SQL,
        (
            source_kind,
            import_source_path,
            relative_path,
            display_name,
            media_type,
        ),
    )
    if created is not None:
        return created
    existing = self._fetch_optional_one(
        GET_CONTINUITY_ARTIFACT_BY_SOURCE_SQL,
        (source_kind, import_source_path, relative_path),
    )
    if existing is None:
        raise ContinuityStoreInvariantError(
            "upsert_continuity_artifact did not return or reveal an artifact row",
        )
    return existing

def get_continuity_artifact_optional(
    self,
    artifact_id: UUID,
) -> ContinuityArtifactRow | None:
    return self._fetch_optional_one(
        GET_CONTINUITY_ARTIFACT_SQL,
        (artifact_id,),
    )

def upsert_continuity_artifact_copy(
    self,
    *,
    artifact_id: UUID,
    checksum_sha256: str,
    content_text: str,
    content_length_bytes: int,
    content_encoding: str,
) -> ContinuityArtifactCopyRow:
    created = self._fetch_optional_one(
        UPSERT_CONTINUITY_ARTIFACT_COPY_SQL,
        (
            artifact_id,
            checksum_sha256,
            content_text,
            content_length_bytes,
            content_encoding,
        ),
    )
    if created is not None:
        return created
    existing = self._fetch_optional_one(
        GET_CONTINUITY_ARTIFACT_COPY_BY_CHECKSUM_SQL,
        (artifact_id, checksum_sha256),
    )
    if existing is None:
        raise ContinuityStoreInvariantError(
            "upsert_continuity_artifact_copy did not return or reveal an artifact copy row",
        )
    return existing

def get_continuity_artifact_copy_optional(
    self,
    artifact_copy_id: UUID,
) -> ContinuityArtifactCopyRow | None:
    return self._fetch_optional_one(
        GET_CONTINUITY_ARTIFACT_COPY_SQL,
        (artifact_copy_id,),
    )

def list_continuity_artifact_copies(
    self,
    artifact_id: UUID,
) -> list[ContinuityArtifactCopyRow]:
    return self._fetch_all(
        LIST_CONTINUITY_ARTIFACT_COPIES_SQL,
        (artifact_id,),
    )

def upsert_continuity_artifact_segment(
    self,
    *,
    artifact_id: UUID,
    artifact_copy_id: UUID,
    source_item_id: str,
    sequence_no: int,
    segment_kind: str,
    locator: JsonObject,
    raw_content: str,
    checksum_sha256: str,
) -> ContinuityArtifactSegmentRow:
    created = self._fetch_optional_one(
        UPSERT_CONTINUITY_ARTIFACT_SEGMENT_SQL,
        (
            artifact_id,
            artifact_copy_id,
            source_item_id,
            sequence_no,
            segment_kind,
            Jsonb(locator),
            raw_content,
            checksum_sha256,
        ),
    )
    if created is not None:
        return created
    existing = self._fetch_optional_one(
        GET_CONTINUITY_ARTIFACT_SEGMENT_BY_SOURCE_ITEM_SQL,
        (artifact_copy_id, source_item_id),
    )
    if existing is None:
        raise ContinuityStoreInvariantError(
            "upsert_continuity_artifact_segment did not return or reveal a segment row",
        )
    return existing

def get_continuity_artifact_segment_optional(
    self,
    artifact_segment_id: UUID,
) -> ContinuityArtifactSegmentRow | None:
    return self._fetch_optional_one(
        GET_CONTINUITY_ARTIFACT_SEGMENT_SQL,
        (artifact_segment_id,),
    )

def list_continuity_artifact_segments(
    self,
    artifact_id: UUID,
) -> list[ContinuityArtifactSegmentRow]:
    return self._fetch_all(
        LIST_CONTINUITY_ARTIFACT_SEGMENTS_SQL,
        (artifact_id,),
    )

def create_continuity_object_evidence_link(
    self,
    *,
    continuity_object_id: UUID,
    artifact_id: UUID,
    artifact_copy_id: UUID,
    artifact_segment_id: UUID | None,
    relationship: str,
) -> ContinuityObjectEvidenceLinkRow:
    return self._fetch_one(
        "create_continuity_object_evidence_link",
        INSERT_CONTINUITY_OBJECT_EVIDENCE_LINK_SQL,
        (
            continuity_object_id,
            artifact_id,
            artifact_copy_id,
            artifact_segment_id,
            relationship,
        ),
    )

def list_continuity_object_evidence(
    self,
    continuity_object_id: UUID,
) -> list[ContinuityObjectEvidenceRow]:
    return self._fetch_all(
        LIST_CONTINUITY_OBJECT_EVIDENCE_SQL,
        (continuity_object_id,),
    )

def update_continuity_object_optional(
    self,
    *,
    continuity_object_id: UUID,
    status: str,
    is_preserved: bool,
    is_searchable: bool,
    is_promotable: bool,
    title: str,
    body: JsonObject,
    provenance: JsonObject,
    confidence: float,
    last_confirmed_at: datetime | None,
    supersedes_object_id: UUID | None,
    superseded_by_object_id: UUID | None,
) -> ContinuityObjectRow | None:
    return self._fetch_optional_one(
        UPDATE_CONTINUITY_OBJECT_SQL,
        (
            status,
            is_preserved,
            is_searchable,
            is_promotable,
            title,
            Jsonb(body),
            Jsonb(provenance),
            confidence,
            last_confirmed_at,
            supersedes_object_id,
            superseded_by_object_id,
            continuity_object_id,
        ),
    )

def create_continuity_correction_event(
    self,
    *,
    continuity_object_id: UUID,
    action: str,
    reason: str | None,
    before_snapshot: JsonObject,
    after_snapshot: JsonObject,
    payload: JsonObject,
) -> ContinuityCorrectionEventRow:
    return self._fetch_one(
        "create_continuity_correction_event",
        INSERT_CONTINUITY_CORRECTION_EVENT_SQL,
        (
            continuity_object_id,
            action,
            reason,
            Jsonb(before_snapshot),
            Jsonb(after_snapshot),
            Jsonb(payload),
        ),
    )

def list_continuity_correction_events(
    self,
    *,
    continuity_object_id: UUID,
    limit: int,
) -> list[ContinuityCorrectionEventRow]:
    return self._fetch_all(
        LIST_CONTINUITY_CORRECTION_EVENTS_SQL,
        (continuity_object_id, limit),
    )

def create_contradiction_case(
    self,
    *,
    canonical_key: str,
    continuity_object_id: UUID,
    counterpart_object_id: UUID,
    kind: str,
    status: str,
    rationale: str,
    detection_payload: JsonObject,
    resolution_action: str | None,
    resolution_note: str | None,
    continuity_object_updated_at: datetime,
    counterpart_object_updated_at: datetime,
    resolved_at: datetime | None,
) -> ContradictionCaseRow:
    return self._fetch_one(
        "create_contradiction_case",
        INSERT_CONTRADICTION_CASE_SQL,
        (
            canonical_key,
            continuity_object_id,
            counterpart_object_id,
            kind,
            status,
            rationale,
            Jsonb(detection_payload),
            resolution_action,
            resolution_note,
            continuity_object_updated_at,
            counterpart_object_updated_at,
            resolved_at,
        ),
    )

def update_contradiction_case_optional(
    self,
    *,
    contradiction_case_id: UUID,
    continuity_object_id: UUID,
    counterpart_object_id: UUID,
    kind: str,
    status: str,
    rationale: str,
    detection_payload: JsonObject,
    resolution_action: str | None,
    resolution_note: str | None,
    continuity_object_updated_at: datetime,
    counterpart_object_updated_at: datetime,
    resolved_at: datetime | None,
) -> ContradictionCaseRow | None:
    return self._fetch_optional_one(
        UPDATE_CONTRADICTION_CASE_SQL,
        (
            continuity_object_id,
            counterpart_object_id,
            kind,
            status,
            rationale,
            Jsonb(detection_payload),
            resolution_action,
            resolution_note,
            continuity_object_updated_at,
            counterpart_object_updated_at,
            resolved_at,
            contradiction_case_id,
        ),
    )

def get_contradiction_case_optional(
    self,
    contradiction_case_id: UUID,
) -> ContradictionCaseRow | None:
    return self._fetch_optional_one(
        GET_CONTRADICTION_CASE_SQL,
        (contradiction_case_id,),
    )

def get_contradiction_case_by_canonical_key_optional(
    self,
    *,
    canonical_key: str,
) -> ContradictionCaseRow | None:
    return self._fetch_optional_one(
        GET_CONTRADICTION_CASE_BY_CANONICAL_KEY_SQL,
        (canonical_key,),
    )

def list_contradiction_cases(
    self,
    *,
    statuses: Sequence[str],
    limit: int,
    continuity_object_id: UUID | None = None,
) -> list[ContradictionCaseRow]:
    return self._fetch_all(
        LIST_CONTRADICTION_CASES_SQL,
        (
            statuses,
            continuity_object_id,
            continuity_object_id,
            continuity_object_id,
            limit,
        ),
    )

def count_contradiction_cases(
    self,
    *,
    statuses: list[str],
    continuity_object_id: UUID | None = None,
) -> int:
    return self._fetch_count(
        COUNT_CONTRADICTION_CASES_SQL,
        (
            statuses,
            continuity_object_id,
            continuity_object_id,
            continuity_object_id,
        ),
    )

def list_contradiction_cases_for_objects(
    self,
    *,
    continuity_object_ids: list[UUID],
    statuses: Sequence[str],
) -> list[ContradictionCaseRow]:
    if not continuity_object_ids:
        return []
    return self._fetch_all(
        LIST_CONTRADICTION_CASES_FOR_OBJECTS_SQL,
        (
            statuses,
            continuity_object_ids,
            continuity_object_ids,
        ),
    )

def upsert_trust_signal(
    self,
    *,
    continuity_object_id: UUID,
    signal_key: str,
    signal_type: str,
    signal_state: str,
    direction: str,
    magnitude: float,
    reason: str,
    contradiction_case_id: UUID | None,
    related_continuity_object_id: UUID | None,
    payload: JsonObject,
) -> TrustSignalRow:
    return self._fetch_one(
        "upsert_trust_signal",
        UPSERT_TRUST_SIGNAL_SQL,
        (
            continuity_object_id,
            signal_key,
            signal_type,
            signal_state,
            direction,
            magnitude,
            reason,
            contradiction_case_id,
            related_continuity_object_id,
            Jsonb(payload),
        ),
    )

def list_trust_signals(
    self,
    *,
    limit: int,
    continuity_object_id: UUID | None = None,
    signal_state: str | None = None,
    signal_type: str | None = None,
) -> list[TrustSignalRow]:
    return self._fetch_all(
        LIST_TRUST_SIGNALS_SQL,
        (
            continuity_object_id,
            continuity_object_id,
            signal_state,
            signal_state,
            signal_type,
            signal_type,
            limit,
        ),
    )

def count_trust_signals(
    self,
    *,
    continuity_object_id: UUID | None = None,
    signal_state: str | None = None,
    signal_type: str | None = None,
) -> int:
    return self._fetch_count(
        COUNT_TRUST_SIGNALS_SQL,
        (
            continuity_object_id,
            continuity_object_id,
            signal_state,
            signal_state,
            signal_type,
            signal_type,
        ),
    )

def create_memory_operation_candidate(
    self,
    *,
    sync_fingerprint: str,
    source_kind: str,
    source_candidate_id: str,
    source_candidate_type: str,
    candidate_payload: JsonObject,
    source_scope: JsonObject,
    operation_type: str,
    operation_reason: str,
    policy_action: str,
    policy_reason: str,
    target_continuity_object_id: UUID | None,
    target_snapshot: JsonObject,
) -> MemoryOperationCandidateRow:
    return self._fetch_one(
        "create_memory_operation_candidate",
        INSERT_MEMORY_OPERATION_CANDIDATE_SQL,
        (
            sync_fingerprint,
            source_kind,
            source_candidate_id,
            source_candidate_type,
            Jsonb(candidate_payload),
            Jsonb(source_scope),
            operation_type,
            operation_reason,
            policy_action,
            policy_reason,
            target_continuity_object_id,
            Jsonb(target_snapshot),
        ),
    )

def get_memory_operation_candidate_optional(
    self,
    candidate_id: UUID,
) -> MemoryOperationCandidateRow | None:
    return self._fetch_optional_one(
        GET_MEMORY_OPERATION_CANDIDATE_SQL,
        (candidate_id,),
    )

def get_memory_operation_candidate_by_sync_source_optional(
    self,
    *,
    sync_fingerprint: str,
    source_candidate_id: str,
) -> MemoryOperationCandidateRow | None:
    return self._fetch_optional_one(
        GET_MEMORY_OPERATION_CANDIDATE_BY_SYNC_SOURCE_SQL,
        (sync_fingerprint, source_candidate_id),
    )

def list_memory_operation_candidates(
    self,
    *,
    limit: int,
    policy_action: str | None = None,
    operation_type: str | None = None,
    sync_fingerprint: str | None = None,
) -> list[MemoryOperationCandidateRow]:
    return self._fetch_all(
        LIST_MEMORY_OPERATION_CANDIDATES_SQL,
        (
            policy_action,
            policy_action,
            operation_type,
            operation_type,
            sync_fingerprint,
            sync_fingerprint,
            limit,
        ),
    )

def count_memory_operation_candidates(
    self,
    *,
    policy_action: str | None = None,
    operation_type: str | None = None,
    sync_fingerprint: str | None = None,
) -> int:
    return self._fetch_count(
        COUNT_MEMORY_OPERATION_CANDIDATES_SQL,
        (
            policy_action,
            policy_action,
            operation_type,
            operation_type,
            sync_fingerprint,
            sync_fingerprint,
        ),
    )

def update_memory_operation_candidate_application(
    self,
    *,
    candidate_id: UUID,
    applied_operation_id: UUID,
    applied_at: datetime,
) -> MemoryOperationCandidateRow | None:
    return self._fetch_optional_one(
        UPDATE_MEMORY_OPERATION_CANDIDATE_APPLICATION_SQL,
        (
            applied_operation_id,
            applied_at,
            candidate_id,
        ),
    )

def create_memory_operation(
    self,
    *,
    operation_id: UUID,
    candidate_id: UUID,
    operation_type: str,
    status: str,
    sync_fingerprint: str,
    target_continuity_object_id: UUID | None,
    resulting_continuity_object_id: UUID | None,
    correction_event_id: UUID | None,
    before_snapshot: JsonObject,
    after_snapshot: JsonObject,
    details: JsonObject,
) -> MemoryOperationRow:
    return self._fetch_one(
        "create_memory_operation",
        INSERT_MEMORY_OPERATION_SQL,
        (
            operation_id,
            candidate_id,
            operation_type,
            status,
            sync_fingerprint,
            target_continuity_object_id,
            resulting_continuity_object_id,
            correction_event_id,
            Jsonb(before_snapshot),
            Jsonb(after_snapshot),
            Jsonb(details),
        ),
    )

def get_memory_operation_optional(
    self,
    operation_id: UUID,
) -> MemoryOperationRow | None:
    return self._fetch_optional_one(
        GET_MEMORY_OPERATION_SQL,
        (operation_id,),
    )

def list_memory_operations(
    self,
    *,
    limit: int,
    sync_fingerprint: str | None = None,
) -> list[MemoryOperationRow]:
    return self._fetch_all(
        LIST_MEMORY_OPERATIONS_SQL,
        (
            sync_fingerprint,
            sync_fingerprint,
            limit,
        ),
    )

def count_memory_operations(
    self,
    *,
    sync_fingerprint: str | None = None,
) -> int:
    return self._fetch_count(
        COUNT_MEMORY_OPERATIONS_SQL,
        (
            sync_fingerprint,
            sync_fingerprint,
        ),
    )
