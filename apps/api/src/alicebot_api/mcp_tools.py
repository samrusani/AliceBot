from __future__ import annotations

import json as json
import math as math
import os as os
import re as re
import sqlite3 as sqlite3
from collections.abc import (
    Mapping as Mapping,
    Sequence as Sequence,
)
from contextlib import contextmanager as contextmanager
from dataclasses import (
    dataclass as dataclass,
    replace as replace,
)
from datetime import (
    UTC as UTC,
    date as date,
    datetime as datetime,
)
from typing import (
    Protocol as Protocol,
    TypedDict as TypedDict,
    cast as cast,
)
from urllib.parse import (
    unquote as unquote,
    urlparse as urlparse,
)
from uuid import (
    UUID as UUID,
    uuid4 as uuid4,
)
from psycopg.errors import CheckViolation as CheckViolation
from alicebot_api.continuity_capture import (
    ContinuityCaptureValidationError as ContinuityCaptureValidationError,
    capture_continuity_candidates as capture_continuity_candidates,
    commit_continuity_captures as commit_continuity_captures,
)
from alicebot_api.continuity_brief import (
    ContinuityBriefValidationError as ContinuityBriefValidationError,
    compile_continuity_brief as compile_continuity_brief,
)
from alicebot_api.continuity_evidence import (
    ContinuityEvidenceNotFoundError as ContinuityEvidenceNotFoundError,
    build_continuity_explain as build_continuity_explain,
    get_continuity_artifact_detail as get_continuity_artifact_detail,
)
from alicebot_api.continuity_contradictions import (
    ContinuityContradictionNotFoundError as ContinuityContradictionNotFoundError,
    ContinuityContradictionValidationError as ContinuityContradictionValidationError,
    get_contradiction_case as get_contradiction_case,
    list_contradiction_cases as list_contradiction_cases,
    resolve_contradiction_case as resolve_contradiction_case,
    sync_contradictions as sync_contradictions,
)
from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError as ContinuityRecallValidationError,
    RetrievalTraceNotFoundError as RetrievalTraceNotFoundError,
    get_retrieval_trace as get_retrieval_trace,
    query_continuity_recall as query_continuity_recall,
)
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError as ContinuityResumptionValidationError,
    compile_continuity_resumption_brief as compile_continuity_resumption_brief,
)
from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError as ContinuityReviewNotFoundError,
    ContinuityReviewValidationError as ContinuityReviewValidationError,
    apply_continuity_correction as apply_continuity_correction,
    get_continuity_review_detail as get_continuity_review_detail,
    list_continuity_review_queue as list_continuity_review_queue,
)
from alicebot_api.continuity_trust import list_trust_signals as list_trust_signals
from alicebot_api.memory_mutations import (
    MemoryMutationValidationError as MemoryMutationValidationError,
    commit_memory_operations as commit_memory_operations,
    generate_memory_operation_candidates as generate_memory_operation_candidates,
    list_memory_operation_candidates as list_memory_operation_candidates,
    list_memory_operations as list_memory_operations,
)
from alicebot_api.contracts import (
    CONTINUITY_CAPTURE_CANDIDATE_TYPES as CONTINUITY_CAPTURE_CANDIDATE_TYPES,
    CONTINUITY_CAPTURE_COMMIT_MODES as CONTINUITY_CAPTURE_COMMIT_MODES,
    CONTINUITY_CORRECTION_ACTIONS as CONTINUITY_CORRECTION_ACTIONS,
    CONTINUITY_BRIEF_TYPE_ORDER as CONTINUITY_BRIEF_TYPE_ORDER,
    CONTRADICTION_RESOLUTION_ACTIONS as CONTRADICTION_RESOLUTION_ACTIONS,
    CONTINUITY_REVIEW_QUEUE_ORDER as CONTINUITY_REVIEW_QUEUE_ORDER,
    CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER as CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER,
    CONTINUITY_OBJECT_TYPES as CONTINUITY_OBJECT_TYPES,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT as DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT as DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT as DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT as DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT as DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT as DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET as DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    DEFAULT_CONTINUITY_REVIEW_LIMIT as DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT as DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT as MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT as MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT as MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT as MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT as MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT as MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET as MAX_TASK_BRIEF_TOKEN_BUDGET,
    MAX_CONTINUITY_REVIEW_LIMIT as MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_TEMPORAL_TIMELINE_LIMIT as MAX_TEMPORAL_TIMELINE_LIMIT,
    MEMORY_TRUST_CLASSES as MEMORY_TRUST_CLASSES,
    ContinuityCaptureCandidatesInput as ContinuityCaptureCandidatesInput,
    ContinuityCaptureCommitInput as ContinuityCaptureCommitInput,
    ContinuityBriefRequestInput as ContinuityBriefRequestInput,
    ContradictionResolutionAction as ContradictionResolutionAction,
    ContradictionStatus as ContradictionStatus,
    ContradictionCaseListQueryInput as ContradictionCaseListQueryInput,
    ContradictionResolveInput as ContradictionResolveInput,
    ContradictionSyncInput as ContradictionSyncInput,
    ContinuityCorrectionInput as ContinuityCorrectionInput,
    ContinuityCorrectionAction as ContinuityCorrectionAction,
    ContinuityRecallQueryInput as ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput as ContinuityResumptionBriefRequestInput,
    ContinuityReviewQueueQueryInput as ContinuityReviewQueueQueryInput,
    ContinuityReviewStatusFilter as ContinuityReviewStatusFilter,
    MemoryOperationCommitInput as MemoryOperationCommitInput,
    MemoryOperationGenerateInput as MemoryOperationGenerateInput,
    MemoryOperationListInput as MemoryOperationListInput,
    TaskBriefCompileRequestInput as TaskBriefCompileRequestInput,
    TaskBriefingStrategy as TaskBriefingStrategy,
    TemporalExplainQueryInput as TemporalExplainQueryInput,
    TemporalStateAtQueryInput as TemporalStateAtQueryInput,
    TemporalTimelineQueryInput as TemporalTimelineQueryInput,
    TrustSignalState as TrustSignalState,
    TrustSignalType as TrustSignalType,
    TrustSignalListQueryInput as TrustSignalListQueryInput,
)
from alicebot_api.config import get_settings as get_settings
from alicebot_api.db import user_connection as user_connection
from alicebot_api.sqlite_store import (
    SQLiteVNextStore as SQLiteVNextStore,
    ensure_sqlite_user as ensure_sqlite_user,
    sqlite_user_connection as sqlite_user_connection,
)
from alicebot_api.store import (
    ContinuityStore as ContinuityStore,
    JsonObject as JsonObject,
    JsonValue as JsonValue,
)
from alicebot_api.surface_flags import (
    LEGACY_SURFACES_ENV as LEGACY_SURFACES_ENV,
    MCP_LEGACY_TOOLS_ENV as MCP_LEGACY_TOOLS_ENV,
    legacy_surfaces_enabled as legacy_surfaces_enabled,
    mcp_legacy_tools_enabled as mcp_legacy_tools_enabled,
)
from alicebot_api.temporal_state import (
    TemporalStateValidationError as TemporalStateValidationError,
    get_temporal_explain as get_temporal_explain,
    get_temporal_state_at as get_temporal_state_at,
    get_temporal_timeline as get_temporal_timeline,
)
from alicebot_api.task_briefing import (
    TaskBriefNotFoundError as TaskBriefNotFoundError,
    TaskBriefValidationError as TaskBriefValidationError,
    compare_task_briefs as compare_task_briefs,
    compile_and_persist_task_brief as compile_and_persist_task_brief,
    get_persisted_task_brief as get_persisted_task_brief,
)
from alicebot_api.vnext_agent_control import (
    AgentIdentity as AgentIdentity,
    AgentIdentityValidationError as AgentIdentityValidationError,
    AgentPolicyBlockedError as AgentPolicyBlockedError,
    PolicyDecision as PolicyDecision,
    agent_metadata as agent_metadata,
    append_policy_events as append_policy_events,
    evaluate_agent_policy as evaluate_agent_policy,
    resource_project_scope as resource_project_scope,
)
from alicebot_api.vnext_agent_keys import (
    AgentKeyAuthenticationError as AgentKeyAuthenticationError,
    resolve_agent_identity as resolve_agent_identity,
)
from alicebot_api.vnext_artifact_review import dispatch_vnext_artifact_review as dispatch_vnext_artifact_review
from alicebot_api.vnext_brain import (
    BrainArtifactRequest as BrainArtifactRequest,
    VNextBrainService as VNextBrainService,
)
from alicebot_api.vnext_capture import VNextCaptureService as VNextCaptureService
from alicebot_api.vnext_embeddings import (
    DeferredMemoryEmbedding as DeferredMemoryEmbedding,
    persist_deferred_memory_embeddings_best_effort as persist_deferred_memory_embeddings_best_effort,
)
from alicebot_api.vnext_connections import (
    ConnectionFinderRequest as ConnectionFinderRequest,
    VNextConnectionService as VNextConnectionService,
)
from alicebot_api.vnext_context_tree import (
    ContextTreeRequest as ContextTreeRequest,
    VNextContextTreeService as VNextContextTreeService,
)
from alicebot_api.vnext_connectors import VNextConnectorService as VNextConnectorService
from alicebot_api.vnext_contradictions import (
    ContradictionFinderRequest as ContradictionFinderRequest,
    VNextContradictionService as VNextContradictionService,
)
from alicebot_api.vnext_event_log import append_event as append_event
from alicebot_api.vnext_lifecycle import (
    REVIEW_APPROVE as REVIEW_APPROVE,
    REVIEW_REJECT as REVIEW_REJECT,
    REVIEW_SUPERSEDE as REVIEW_SUPERSEDE,
    LifecycleTransitionError as LifecycleTransitionError,
    resolve_transition as resolve_transition,
)
from alicebot_api.vnext_memory_commit import (
    VNextMemoryCommitService as VNextMemoryCommitService,
    VNextMemoryCommitValidationError as VNextMemoryCommitValidationError,
    VNEXT_DOMAINS as VNEXT_DOMAINS,
    VNEXT_MEMORY_TYPES as VNEXT_MEMORY_TYPES,
    VNEXT_SENSITIVITY_LEVELS as VNEXT_SENSITIVITY_LEVELS,
    is_pending_consolidation_candidate as is_pending_consolidation_candidate,
    memory_commit_request_from_payload as memory_commit_request_from_payload,
)
from alicebot_api.vnext_project_update_guard import (
    PENDING_PROJECT_UPDATE_MEMORY_MUTATION_MESSAGE as PENDING_PROJECT_UPDATE_MEMORY_MUTATION_MESSAGE,
    is_pending_project_update_memory as is_pending_project_update_memory,
)
from alicebot_api.vnext_project_scope import (
    project_identifier_identity as project_identifier_identity,
    project_scopes_overlap as project_scopes_overlap,
    resolve_project_scope as resolve_project_scope,
    source_project_scope as source_project_scope,
)
from alicebot_api.vnext_projects import (
    OPEN_LOOP_ACTIONS as OPEN_LOOP_ACTIONS,
    ProjectAutomationRequest as ProjectAutomationRequest,
    VNextProjectService as VNextProjectService,
)
from alicebot_api.vnext_queue import (
    QueueTaskRequest as QueueTaskRequest,
    VNextQueueService as VNextQueueService,
)
from alicebot_api.vnext_repositories import JsonObject as VNextJsonObject
from alicebot_api.vnext_retrieval import (
    BUDGET_STRATEGIES as BUDGET_STRATEGIES,
    BUDGET_STRATEGY_BALANCED as BUDGET_STRATEGY_BALANCED,
    CONTEXT_DEPTHS as CONTEXT_DEPTHS,
    CONTEXT_DEPTH_LOW as CONTEXT_DEPTH_LOW,
    CONTEXT_DEPTH_MINIMAL as CONTEXT_DEPTH_MINIMAL,
    CONTEXT_DEPTH_MINIMAL_MAX_ITEMS as CONTEXT_DEPTH_MINIMAL_MAX_ITEMS,
    GRAPH_STAGE_ENABLED as GRAPH_STAGE_ENABLED,
    MAX_CONTEXT_PACK_ITEMS as MAX_CONTEXT_PACK_ITEMS,
    MAX_CONTEXT_PACK_TOKENS as MAX_CONTEXT_PACK_TOKENS,
    MAX_CONTEXT_SCOPE_VALUES as MAX_CONTEXT_SCOPE_VALUES,
    MAX_TIME_WINDOW_DAYS as MAX_TIME_WINDOW_DAYS,
    MEMORY_ENTITY_EDGE_TYPES as MEMORY_ENTITY_EDGE_TYPES,
    RRF_K as RRF_K,
    STAGE_DISABLED_MINIMAL as STAGE_DISABLED_MINIMAL,
    VECTOR_STAGE_ENABLED as VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest as VNextRetrievalRequest,
    VNextRetrievalService as VNextRetrievalService,
    _order_memories_for_strategy as _order_memories_for_strategy,
    estimate_item_tokens as estimate_item_tokens,
    reciprocal_rank_fusion as reciprocal_rank_fusion,
)
from alicebot_api.vnext_scheduler import (
    SchedulerRunRequest as SchedulerRunRequest,
    VNextSchedulerService as VNextSchedulerService,
)
from alicebot_api.vnext_scheduler_runtime import (
    run_due_workflows_durable as run_due_workflows_durable,
    run_now_durable as run_now_durable,
)
from alicebot_api.vnext_json import json_safe as json_safe
from alicebot_api.vnext_store import (
    REDACTED_JSON_VALUE as REDACTED_JSON_VALUE,
    REDACTION_MARKER as REDACTION_MARKER,
    is_redacted_memory as is_redacted_memory,
    PostgresVNextStore as PostgresVNextStore,
    is_redacted_project_update_artifact as is_redacted_project_update_artifact,
)

from alicebot_api.mcp.shared import (
    _REVIEW_STATUS_CHOICES as _REVIEW_STATUS_CHOICES,
    _REVIEW_STATUS_ALIASES as _REVIEW_STATUS_ALIASES,
    _REVIEW_APPLY_ACTION_CHOICES as _REVIEW_APPLY_ACTION_CHOICES,
    _REVIEW_APPLY_ACTION_ALIASES as _REVIEW_APPLY_ACTION_ALIASES,
    _PROVENANCE_EVIDENCE_ROLES as _PROVENANCE_EVIDENCE_ROLES,
    _REVIEW_APPLY_TO_CORRECTION_ACTION as _REVIEW_APPLY_TO_CORRECTION_ACTION,
    _DEFAULT_SENSITIVITY_ALLOWED as _DEFAULT_SENSITIVITY_ALLOWED,
    _RECALL_DEFAULT_LIMIT as _RECALL_DEFAULT_LIMIT,
    _RECALL_MAX_LIMIT as _RECALL_MAX_LIMIT,
    _OPEN_LOOP_TOOL_ACTIONS as _OPEN_LOOP_TOOL_ACTIONS,
    _PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0 as _PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0,
    _MODEL_GENERATION_MODES as _MODEL_GENERATION_MODES,
    _MODEL_ROUTE_MODES as _MODEL_ROUTE_MODES,
    _MODEL_GENERATION_SCHEMA_PROPERTIES as _MODEL_GENERATION_SCHEMA_PROPERTIES,
    MCPToolError as MCPToolError,
    MCPToolNotFoundError as MCPToolNotFoundError,
    _json_value as _json_value,
    _json_object as _json_object,
    MCPRuntimeContext as MCPRuntimeContext,
    _SQLITE_POSTGRES_ONLY_MESSAGE as _SQLITE_POSTGRES_ONLY_MESSAGE,
    _SQLITE_DEFAULT_USER_EMAIL as _SQLITE_DEFAULT_USER_EMAIL,
    _SQLITE_DEFAULT_USER_DISPLAY_NAME as _SQLITE_DEFAULT_USER_DISPLAY_NAME,
    _is_sqlite_backend as _is_sqlite_backend,
    _sqlite_path_from_url as _sqlite_path_from_url,
    _store_context as _store_context,
    _vnext_store_context as _vnext_store_context,
    _persist_vnext_deferred_embedding_inputs as _persist_vnext_deferred_embedding_inputs,
    _normalize_arguments as _normalize_arguments,
    _parse_optional_text as _parse_optional_text,
    _parse_required_text as _parse_required_text,
    _parse_optional_uuid as _parse_optional_uuid,
    _parse_required_uuid as _parse_required_uuid,
    _parse_optional_datetime as _parse_optional_datetime,
    _parse_int as _parse_int,
    _parse_optional_json_object as _parse_optional_json_object,
    _parse_string_list as _parse_string_list,
    _parse_memory_types as _parse_memory_types,
    _RetrievalFilterKwargs as _RetrievalFilterKwargs,
    _retrieval_filter_kwargs as _retrieval_filter_kwargs,
    AGENT_API_KEY_ENV as AGENT_API_KEY_ENV,
    _agent_identity_from_arguments as _agent_identity_from_arguments,
    _policy_checked as _policy_checked,
    _raise_mcp_policy_blocked as _raise_mcp_policy_blocked,
    _mcp_agent_policy_preflight as _mcp_agent_policy_preflight,
    _parse_task_brief_request as _parse_task_brief_request,
    _parse_continuity_brief_request as _parse_continuity_brief_request,
    _parse_optional_float as _parse_optional_float,
    _parse_bool as _parse_bool,
    _parse_optional_bool as _parse_optional_bool,
    _parse_context_pack_tuning as _parse_context_pack_tuning,
    _ModelGenerationKwargs as _ModelGenerationKwargs,
    _parse_model_generation_kwargs as _parse_model_generation_kwargs,
    _parse_review_status as _parse_review_status,
    _parse_review_item_id as _parse_review_item_id,
    _resolve_review_apply_action as _resolve_review_apply_action,
    _build_recall_query as _build_recall_query,
    _canonicalize_json as _canonicalize_json,
    _recency_sort_key as _recency_sort_key,
    _extract_prefetch_single_title as _extract_prefetch_single_title,
    _extract_prefetch_titles as _extract_prefetch_titles,
    _render_prefetch_context_text as _render_prefetch_context_text,
)
from alicebot_api.mcp.retrieval_shared import (
    _SQLITE_REVIEWABLE_STATUSES as _SQLITE_REVIEWABLE_STATUSES,
    _SQLITE_NEXT_ACTION_MEMORY_TYPES as _SQLITE_NEXT_ACTION_MEMORY_TYPES,
    _SQLITE_OPEN_LOOP_ACTIVE_STATUSES as _SQLITE_OPEN_LOOP_ACTIVE_STATUSES,
    _ASCII_QUERY_CASE_TRANSLATION as _ASCII_QUERY_CASE_TRANSLATION,
    _utc_now_iso_text as _utc_now_iso_text,
    _row_datetime as _row_datetime,
    _row_in_window as _row_in_window,
    _memory_matches_query as _memory_matches_query,
    _memory_matches_project as _memory_matches_project,
    _created_at_sort_key as _created_at_sort_key,
    _compact_vnext_memory as _compact_vnext_memory,
    _compact_vnext_open_loop as _compact_vnext_open_loop,
    _compact_vnext_event as _compact_vnext_event,
    _provenance_count as _provenance_count,
    _resource_matches_project_scope as _resource_matches_project_scope,
)
from alicebot_api.mcp.capture_mutations import (
    _handle_alice_capture_candidates as _handle_alice_capture_candidates,
    _handle_alice_commit_captures as _handle_alice_commit_captures,
    _handle_alice_memory_mutations_generate as _handle_alice_memory_mutations_generate,
    _handle_alice_memory_mutations_list_candidates as _handle_alice_memory_mutations_list_candidates,
    _handle_alice_memory_mutations_commit as _handle_alice_memory_mutations_commit,
    _handle_alice_memory_mutations_list_operations as _handle_alice_memory_mutations_list_operations,
)
from alicebot_api.mcp.evidence_artifacts import (
    _authorize_continuity_explain_target as _authorize_continuity_explain_target,
    _authorize_entity_explain_target as _authorize_entity_explain_target,
    _handle_alice_explain as _handle_alice_explain,
    _handle_alice_artifact_inspect as _handle_alice_artifact_inspect,
    _MEMORY_TIMELINE_MAX_ENTRIES as _MEMORY_TIMELINE_MAX_ENTRIES,
    _EXPLAIN_UNAVAILABLE_MESSAGE as _EXPLAIN_UNAVAILABLE_MESSAGE,
    _ExplainAuthorizationError as _ExplainAuthorizationError,
    _is_key_bound_explain as _is_key_bound_explain,
    _raise_explain_authorization_error as _raise_explain_authorization_error,
    _authorize_explain_resource as _authorize_explain_resource,
    _backing_memory_project_scope as _backing_memory_project_scope,
    _continuity_object_project_scope as _continuity_object_project_scope,
    _continuity_object_classification as _continuity_object_classification,
    _authorize_memory_audit_provenance as _authorize_memory_audit_provenance,
    _entity_backing_is_fully_authorized as _entity_backing_is_fully_authorized,
    _authorized_memory_audit_entity_ids as _authorized_memory_audit_entity_ids,
    _timeline_sort_key as _timeline_sort_key,
    _memory_linked_entity_ids as _memory_linked_entity_ids,
    _memory_linked_entities as _memory_linked_entities,
    _memory_evolution_timeline as _memory_evolution_timeline,
    _extend_memory_audit as _extend_memory_audit,
    _handle_alice_vnext_memory_audit as _handle_alice_vnext_memory_audit,
    _handle_alice_vnext_review_items as _handle_alice_vnext_review_items,
    _authorize_vnext_artifact_target as _authorize_vnext_artifact_target,
    _handle_alice_vnext_artifact_get as _handle_alice_vnext_artifact_get,
    _handle_alice_vnext_artifact_review as _handle_alice_vnext_artifact_review,
)
from alicebot_api.mcp.review import (
    _vnext_memory_review as _vnext_memory_review,
    _canonical_text_from_body as _canonical_text_from_body,
    _canonical_json_dumps as _canonical_json_dumps,
    _validated_review_provenance as _validated_review_provenance,
    _accepted_review_metadata as _accepted_review_metadata,
    _retired_review_metadata as _retired_review_metadata,
    _RevisionStore as _RevisionStore,
    _vnext_review_revision as _vnext_review_revision,
    _vnext_memory_correct as _vnext_memory_correct,
    _review_queue_payload as _review_queue_payload,
    _handle_alice_review_queue as _handle_alice_review_queue,
    _handle_alice_memory_review as _handle_alice_memory_review,
    _review_apply_payload as _review_apply_payload,
    _handle_alice_review_apply as _handle_alice_review_apply,
    _handle_alice_memory_correct as _handle_alice_memory_correct,
    _handle_alice_contradictions_detect as _handle_alice_contradictions_detect,
    _handle_alice_contradictions_list as _handle_alice_contradictions_list,
    _handle_alice_contradictions_resolve as _handle_alice_contradictions_resolve,
    _handle_alice_trust_signals as _handle_alice_trust_signals,
)
from alicebot_api.mcp.synthesis import (
    _brain_artifact_request_from_arguments as _brain_artifact_request_from_arguments,
    _handle_alice_generate_daily_brief as _handle_alice_generate_daily_brief,
    _handle_alice_generate_weekly_synthesis as _handle_alice_generate_weekly_synthesis,
    _connection_request_from_arguments as _connection_request_from_arguments,
    _handle_alice_generate_connections as _handle_alice_generate_connections,
    _handle_alice_graph_edge_review as _handle_alice_graph_edge_review,
    _handle_alice_graph_neighborhood as _handle_alice_graph_neighborhood,
    _contradiction_request_from_arguments as _contradiction_request_from_arguments,
    _handle_alice_generate_contradictions as _handle_alice_generate_contradictions,
    _handle_alice_belief_review as _handle_alice_belief_review,
    _handle_alice_belief_state as _handle_alice_belief_state,
)
from alicebot_api.mcp.projects import (
    _project_request_from_arguments as _project_request_from_arguments,
    _handle_alice_project_update_candidate as _handle_alice_project_update_candidate,
    _handle_alice_project_update_review as _handle_alice_project_update_review,
    _handle_alice_project_dashboard as _handle_alice_project_dashboard,
    _handle_alice_open_loop_extract as _handle_alice_open_loop_extract,
    _handle_alice_open_loop_review as _handle_alice_open_loop_review,
    _handle_alice_vnext_open_loops as _handle_alice_vnext_open_loops,
)
from alicebot_api.mcp.retrieval import (
    _compact_recall_result as _compact_recall_result,
    _handle_alice_recall as _handle_alice_recall,
    _handle_alice_recall_debug as _handle_alice_recall_debug,
    _handle_alice_state_at as _handle_alice_state_at,
    _handle_alice_resume as _handle_alice_resume,
    _handle_alice_resume_debug as _handle_alice_resume_debug,
    _handle_alice_brief as _handle_alice_brief,
    _handle_alice_task_brief as _handle_alice_task_brief,
    _handle_alice_task_brief_show as _handle_alice_task_brief_show,
    _handle_alice_task_brief_compare as _handle_alice_task_brief_compare,
    _handle_alice_retrieval_trace as _handle_alice_retrieval_trace,
    _handle_alice_prefetch_context as _handle_alice_prefetch_context,
    _handle_alice_open_loops as _handle_alice_open_loops,
    _vnext_recent_decisions as _vnext_recent_decisions,
    _vnext_resume as _vnext_resume,
    _handle_alice_recent_decisions as _handle_alice_recent_decisions,
    _handle_alice_recent_changes as _handle_alice_recent_changes,
    _handle_alice_timeline as _handle_alice_timeline,
)
from alicebot_api.mcp.context import (
    _COMPACT_MEMORY_FIELDS as _COMPACT_MEMORY_FIELDS,
    _COMPACT_OPEN_LOOP_FIELDS as _COMPACT_OPEN_LOOP_FIELDS,
    _COMPACT_SOURCE_FIELDS as _COMPACT_SOURCE_FIELDS,
    _compact_fields as _compact_fields,
    _compact_items as _compact_items,
    _handle_alice_context_pack as _handle_alice_context_pack,
    _TOKEN_REPORT_FIELDS as _TOKEN_REPORT_FIELDS,
    _context_pack_token_report as _context_pack_token_report,
    _attach_compact_context_pack_token_report as _attach_compact_context_pack_token_report,
    _ContextPackRequestKwargs as _ContextPackRequestKwargs,
    _vnext_context_pack_payload as _vnext_context_pack_payload,
    _handle_alice_vnext_context_pack as _handle_alice_vnext_context_pack,
    _handle_alice_vnext_context_tree as _handle_alice_vnext_context_tree,
)
from alicebot_api.mcp.memories import (
    _handle_alice_vnext_propose_memory as _handle_alice_vnext_propose_memory,
    _handle_alice_vnext_commit_memory as _handle_alice_vnext_commit_memory,
    _handle_alice_vnext_confirm_memory as _handle_alice_vnext_confirm_memory,
    _handle_alice_vnext_undo_memory as _handle_alice_vnext_undo_memory,
    _handle_alice_vnext_correct_memory as _handle_alice_vnext_correct_memory,
    _handle_alice_vnext_forget_memory as _handle_alice_vnext_forget_memory,
    _REDACT_RETIRED_STATUSES as _REDACT_RETIRED_STATUSES,
    _memory_redaction_is_exact as _memory_redaction_is_exact,
    redact_memory_flow as redact_memory_flow,
    _handle_alice_vnext_expire_memory as _handle_alice_vnext_expire_memory,
    _handle_alice_vnext_unexpire_memory as _handle_alice_vnext_unexpire_memory,
    _handle_alice_vnext_accept_consolidation as _handle_alice_vnext_accept_consolidation,
    _handle_alice_vnext_redact_memory as _handle_alice_vnext_redact_memory,
    _MEMORY_MANAGE_ACTIONS as _MEMORY_MANAGE_ACTIONS,
    _handle_alice_memory_manage as _handle_alice_memory_manage,
    _handle_alice_vnext_recent_memory_commits as _handle_alice_vnext_recent_memory_commits,
)
from alicebot_api.mcp.scheduler import (
    _handle_alice_vnext_scheduler_status as _handle_alice_vnext_scheduler_status,
    _handle_alice_vnext_scheduler_run_now as _handle_alice_vnext_scheduler_run_now,
    _handle_alice_vnext_scheduler_run_due as _handle_alice_vnext_scheduler_run_due,
    _handle_alice_vnext_scheduler_pause as _handle_alice_vnext_scheduler_pause,
    _handle_alice_vnext_scheduler_resume as _handle_alice_vnext_scheduler_resume,
)
from alicebot_api.mcp.capture_automation import (
    _handle_alice_vnext_capture as _handle_alice_vnext_capture,
    _handle_alice_vnext_ingest_agent_output as _handle_alice_vnext_ingest_agent_output,
    _handle_alice_vnext_queue_task as _handle_alice_vnext_queue_task,
    _handle_alice_vnext_generate_artifact as _handle_alice_vnext_generate_artifact,
)
from alicebot_api.mcp.definitions import (
    _VNEXT_AGENT_SCHEMA_PROPERTIES as _VNEXT_AGENT_SCHEMA_PROPERTIES,
    _vnext_agent_tool_schema as _vnext_agent_tool_schema,
    _AGENT_IDENTITY_SCHEMA_PROPERTIES as _AGENT_IDENTITY_SCHEMA_PROPERTIES,
    _DOMAINS_FILTER_SCHEMA as _DOMAINS_FILTER_SCHEMA,
    _MEMORY_TYPES_FILTER_SCHEMA as _MEMORY_TYPES_FILTER_SCHEMA,
    _SENSITIVITY_ALLOWED_SCHEMA as _SENSITIVITY_ALLOWED_SCHEMA,
    _CORRECTION_BODY_SCHEMA as _CORRECTION_BODY_SCHEMA,
    _REVIEW_PROVENANCE_SCHEMA as _REVIEW_PROVENANCE_SCHEMA,
    _CONTINUITY_PROVENANCE_SCHEMA as _CONTINUITY_PROVENANCE_SCHEMA,
    _CONTINUITY_CAPTURE_CANDIDATE_SCHEMA as _CONTINUITY_CAPTURE_CANDIDATE_SCHEMA,
    _CORE_TOOL_DEFINITIONS as _CORE_TOOL_DEFINITIONS,
    _LEGACY_TOOL_DEFINITIONS as _LEGACY_TOOL_DEFINITIONS,
)
from alicebot_api.mcp.registry import (
    _TOOL_HANDLERS as _TOOL_HANDLERS,
    _CORE_TOOL_NAMES as _CORE_TOOL_NAMES,
    _LEGACY_TOOL_NAMES as _LEGACY_TOOL_NAMES,
    _TASK_BRIEF_TOOL_NAMES as _TASK_BRIEF_TOOL_NAMES,
    _TOOL_DEFINITIONS_BY_NAME as _TOOL_DEFINITIONS_BY_NAME,
    _validate_mcp_arguments_against_advertised_schema as _validate_mcp_arguments_against_advertised_schema,
    _legacy_tools_enabled as _legacy_tools_enabled,
    _enabled_tool_definitions as _enabled_tool_definitions,
    list_mcp_tools as list_mcp_tools,
    call_mcp_tool as call_mcp_tool,
)

__annotations__ = {
    "_MODEL_GENERATION_SCHEMA_PROPERTIES": "dict[str, object]",
    "_VNEXT_AGENT_SCHEMA_PROPERTIES": "dict[str, object]",
    "_AGENT_IDENTITY_SCHEMA_PROPERTIES": "dict[str, object]",
    "_DOMAINS_FILTER_SCHEMA": "dict[str, object]",
    "_MEMORY_TYPES_FILTER_SCHEMA": "dict[str, object]",
    "_SENSITIVITY_ALLOWED_SCHEMA": "dict[str, object]",
    "_CORRECTION_BODY_SCHEMA": "dict[str, object]",
    "_REVIEW_PROVENANCE_SCHEMA": "dict[str, object]",
    "_CONTINUITY_PROVENANCE_SCHEMA": "dict[str, object]",
    "_CONTINUITY_CAPTURE_CANDIDATE_SCHEMA": "dict[str, object]",
    "_CORE_TOOL_DEFINITIONS": "list[dict[str, object]]",
    "_LEGACY_TOOL_DEFINITIONS": "list[dict[str, object]]",
}

# Preserve the historical public callable metadata while exposing direct aliases.
MCPRuntimeContext.__module__ = __name__
MCPToolError.__module__ = __name__
MCPToolNotFoundError.__module__ = __name__
call_mcp_tool.__module__ = __name__
list_mcp_tools.__module__ = __name__
redact_memory_flow.__module__ = __name__

__all__ = [
    "MCP_LEGACY_TOOLS_ENV",
    "MCPRuntimeContext",
    "MCPToolError",
    "MCPToolNotFoundError",
    "call_mcp_tool",
    "list_mcp_tools",
    "redact_memory_flow",
]
