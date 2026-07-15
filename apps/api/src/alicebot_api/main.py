from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import ipaddress
import json
import logging
import re
import time
from typing import Annotated, Any, Awaitable, Callable, Literal, TypedDict, cast
from uuid import UUID, uuid4
from fastapi import FastAPI, Header, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, TypeAdapter, model_validator
from fastapi.responses import JSONResponse
import psycopg
from psycopg.rows import dict_row
from starlette.concurrency import run_in_threadpool
from starlette.routing import Match
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alicebot_api import __version__
from alicebot_api.surface_flags import legacy_surfaces_enabled
from alicebot_api.compiler import compile_and_persist_trace, compile_resumption_brief
from alicebot_api.config import Settings, get_settings
from alicebot_api.continuity_brief import (
    ContinuityBriefValidationError,
    compile_continuity_brief,
)
from alicebot_api.contracts import (
    AGENT_PROFILE_LIST_ORDER,
    ApprovalApproveInput,
    ApprovalRejectInput,
    ApprovalRequestCreateInput,
    AgentProfileListResponse,
    AgentProfileListSummary,
    ArtifactScopedSemanticArtifactChunkRetrievalInput,
    CompileContextArtifactScopedSemanticArtifactRetrievalInput,
    CompileContextArtifactScopedArtifactRetrievalInput,
    CompileContextTaskScopedArtifactRetrievalInput,
    CompileContextTaskScopedSemanticArtifactRetrievalInput,
    ConsentStatus,
    ConsentUpsertInput,
    CompileContextSemanticRetrievalInput,
    DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    DEFAULT_AGENT_PROFILE_ID,
    DEFAULT_CALENDAR_EVENT_LIST_LIMIT,
    DEFAULT_CONTINUITY_CAPTURE_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_RETRIEVAL_RUN_LIST_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT,
    DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
    DEFAULT_MAX_EVENTS,
    DEFAULT_MAX_ENTITY_EDGES,
    DEFAULT_MAX_ENTITIES,
    DEFAULT_MAX_MEMORIES,
    DEFAULT_MEMORY_REVIEW_LIMIT,
    DEFAULT_MEMORY_REVIEW_QUEUE_PRIORITY_MODE,
    DEFAULT_OPEN_LOOP_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    MAX_MEMORY_REVIEW_LIMIT,
    MAX_OPEN_LOOP_LIMIT,
    MAX_RESUMPTION_BRIEF_EVENT_LIMIT,
    MAX_RESUMPTION_BRIEF_MEMORY_LIMIT,
    MAX_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    MAX_CALENDAR_EVENT_LIST_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_CAPTURE_LIMIT,
    MAX_CONTINUITY_LIFECYCLE_LIMIT,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_RETRIEVAL_RUN_LIST_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_DAILY_BRIEF_LIMIT,
    MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    ContextCompilerLimits,
    ContinuityArtifactDetailResponse,
    ContinuityBriefRequestInput,
    ContinuityBriefResponse,
    ContinuityCaptureCandidatesInput,
    ContinuityCaptureCommitInput,
    ContinuityCaptureCreateInput,
    ContinuityCaptureExplicitSignal,
    ContradictionCaseDetailResponse,
    ContradictionCaseListQueryInput,
    ContradictionCaseListResponse,
    ContradictionResolveInput,
    ContradictionResolveResponse,
    ContradictionSyncInput,
    ContradictionSyncResponse,
    ContinuityExplainResponse,
    ContinuityLifecycleDetailResponse,
    ContinuityLifecycleListResponse,
    ContinuityLifecycleQueryInput,
    ContinuityDailyBriefRequestInput,
    ContinuityDailyBriefResponse,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityOpenLoopDashboardResponse,
    ContinuityOpenLoopReviewActionInput,
    ContinuityOpenLoopReviewActionResponse,
    ContinuityCorrectionInput,
    ContinuityRecallQueryInput,
    ContinuityRecallResponse,
    ContinuityReviewDetailResponse,
    ContinuityReviewQueueQueryInput,
    ContinuityReviewQueueResponse,
    ContinuityResumptionBriefRequestInput,
    ContinuityResumptionBriefResponse,
    TaskBriefComparisonResponse,
    TaskBriefCompileRequestInput,
    TaskBriefResponse,
    MemoryOperationCommitInput,
    MemoryOperationGenerateInput,
    MemoryOperationListInput,
    TemporalExplainQueryInput,
    TemporalExplainResponse,
    TemporalStateAtQueryInput,
    TemporalStateAtResponse,
    TemporalTimelineQueryInput,
    TemporalTimelineResponse,
    TrustedFactPatternExplainResponse,
    TrustedFactPatternListQueryInput,
    TrustedFactPatternListResponse,
    TrustedFactPlaybookExplainResponse,
    TrustedFactPlaybookListQueryInput,
    TrustedFactPlaybookListResponse,
    ContinuityWeeklyReviewRequestInput,
    ContinuityWeeklyReviewResponse,
    MemoryHygieneDashboardResponse,
    MemoryTrustDashboardResponse,
    RetrievalEvaluationResponse,
    RetrievalRunListResponse,
    RetrievalTraceResponse,
    ThreadHealthDashboardResponse,
    TrustSignalListQueryInput,
    TrustSignalListResponse,
    EmbeddingConfigStatus,
    EmbeddingConfigCreateInput,
    ExecutionBudgetCreateInput,
    ExecutionBudgetDeactivateInput,
    ExecutionBudgetSupersedeInput,
    EntityEdgeCreateInput,
    EntityCreateInput,
    EntityType,
    ExplicitCommitmentExtractionRequestInput,
    ExplicitPreferenceExtractionRequestInput,
    ExplicitSignalCaptureRequestInput,
    CalendarAccountConnectInput,
    CalendarEventListInput,
    CalendarEventIngestInput,
    GmailAccountConnectInput,
    GmailMessageIngestInput,
    MemoryCandidateInput,
    ModelInvocationRequest,
    ModelInvocationResponse,
    GenerateResponseSuccess,
    OpenLoopCandidateInput,
    MemoryEmbeddingUpsertInput,
    THREAD_EVENT_LIST_ORDER,
    PROVIDER_LIST_ORDER,
    THREAD_LIST_ORDER,
    THREAD_SESSION_LIST_ORDER,
    MemoryReviewLabelValue,
    MemoryReviewQueuePriorityMode,
    MemoryReviewStatusFilter,
    OpenLoopStatusFilter,
    OpenLoopCreateInput,
    OpenLoopStatusUpdateInput,
    PolicyCreateInput,
    PolicyEffect,
    PolicyEvaluationRequestInput,
    SemanticMemoryRetrievalRequestInput,
    TaskArtifactChunkEmbeddingUpsertInput,
    TOOL_METADATA_VERSION_V0,
    ApprovalStatus,
    ArtifactScopedArtifactChunkRetrievalInput,
    ProxyExecutionStatus,
    ToolAllowlistEvaluationRequestInput,
    ProxyExecutionRequestInput,
    PublicEvalRunDetailResponse,
    PublicEvalRunListResponse,
    PublicEvalSuiteDefinitionListResponse,
    TaskArtifactIngestInput,
    TaskArtifactRegisterInput,
    TaskScopedSemanticArtifactChunkRetrievalInput,
    TaskScopedArtifactChunkRetrievalInput,
    TaskStepKind,
    TaskStepLineageInput,
    TaskStepNextCreateInput,
    TaskStepOutcomeSnapshot,
    TaskStepStatus,
    TaskStepTransitionInput,
    TaskRunCancelInput,
    TaskRunCreateInput,
    TaskRunPauseInput,
    TaskRunResumeInput,
    TaskRunTickInput,
    TaskWorkspaceCreateInput,
    ToolRoutingDecision,
    ToolRoutingRequestInput,
    ToolRoutingRequestRecord,
    ToolCreateInput,
    ThreadCreateInput,
    ThreadCreateResponse,
    ThreadDetailResponse,
    ThreadEventListResponse,
    ThreadEventListSummary,
    ThreadEventRecord,
    ThreadListResponse,
    ThreadListSummary,
    ThreadRecord,
    ResumptionBriefRequestInput,
    ResumptionBriefResponse,
    ThreadSessionListResponse,
    ThreadSessionListSummary,
    ThreadSessionRecord,
)
from alicebot_api.phase3_profiles import (
    get_agent_profile as get_registered_agent_profile,
    list_agent_profile_ids as list_registered_agent_profile_ids,
    list_agent_profiles as list_registered_agent_profiles,
)
from alicebot_api.artifacts import (
    TaskArtifactAlreadyExistsError,
    TaskArtifactChunkRetrievalValidationError,
    TaskArtifactNotFoundError,
    TaskArtifactValidationError,
    get_task_artifact_record,
    ingest_task_artifact_record,
    list_task_artifact_chunk_records,
    list_task_artifact_records,
    register_task_artifact_record,
    retrieve_artifact_scoped_artifact_chunk_records,
    retrieve_task_scoped_artifact_chunk_records,
)
from alicebot_api.approvals import (
    ApprovalNotFoundError,
    ApprovalResolutionConflictError,
    approve_approval_record,
    get_approval_record,
    list_approval_records,
    reject_approval_record,
    submit_approval_request,
)
from alicebot_api.db import (
    ping_database,
    set_current_user_account,
    user_connection,
)
from alicebot_api.local_workspace import (
    ensure_local_workspace,
    get_local_workspace,
    serialize_local_workspace,
)
from alicebot_api.executions import (
    ToolExecutionNotFoundError,
    get_tool_execution_record,
    list_tool_execution_records,
)
from alicebot_api.tasks import (
    TaskNotFoundError,
    TaskStepApprovalLinkageError,
    TaskStepExecutionLinkageError,
    TaskStepLifecycleBoundaryError,
    TaskStepSequenceError,
    TaskStepNotFoundError,
    TaskStepTransitionError,
    create_next_task_step_record,
    get_task_record,
    get_task_step_record,
    list_task_records,
    list_task_step_records,
    transition_task_step_record,
)
from alicebot_api.task_runs import (
    TaskRunNotFoundError,
    TaskRunTransitionError,
    TaskRunValidationError,
    cancel_task_run_record,
    create_task_run_record,
    get_task_run_record,
    list_task_run_records,
    pause_task_run_record,
    resume_task_run_record,
    tick_task_run_record,
)
from alicebot_api.workspaces import (
    TaskWorkspaceAlreadyExistsError,
    TaskWorkspaceNotFoundError,
    TaskWorkspaceProvisioningError,
    create_task_workspace_record,
    get_task_workspace_record,
    list_task_workspace_records,
)
from alicebot_api.execution_budgets import (
    ExecutionBudgetLifecycleError,
    ExecutionBudgetNotFoundError,
    ExecutionBudgetValidationError,
    create_execution_budget_record,
    deactivate_execution_budget_record,
    get_execution_budget_record,
    list_execution_budget_records,
    supersede_execution_budget_record,
)
from alicebot_api.gmail import (
    GmailAccountAlreadyExistsError,
    GmailCredentialInvalidError,
    GmailCredentialNotFoundError,
    GmailCredentialPersistenceError,
    GmailCredentialRefreshError,
    GmailCredentialValidationError,
    GmailAccountNotFoundError,
    GmailMessageFetchError,
    GmailMessageNotFoundError,
    GmailMessageUnsupportedError,
    create_gmail_account_record,
    get_gmail_account_record,
    ingest_gmail_message_record,
    list_gmail_account_records,
)
from alicebot_api.calendar import (
    CalendarAccountAlreadyExistsError,
    CalendarAccountNotFoundError,
    CalendarCredentialInvalidError,
    CalendarCredentialNotFoundError,
    CalendarCredentialPersistenceError,
    CalendarCredentialValidationError,
    CalendarEventFetchError,
    CalendarEventListValidationError,
    CalendarEventNotFoundError,
    CalendarEventUnsupportedError,
    create_calendar_account_record,
    get_calendar_account_record,
    ingest_calendar_event_record,
    list_calendar_account_records,
    list_calendar_event_records,
)
from alicebot_api.calendar_secret_manager import build_calendar_secret_manager
from alicebot_api.gmail_secret_manager import build_gmail_secret_manager
from alicebot_api.embedding import (
    EmbeddingConfigValidationError,
    MemoryEmbeddingNotFoundError,
    MemoryEmbeddingValidationError,
    TaskArtifactChunkEmbeddingNotFoundError,
    TaskArtifactChunkEmbeddingValidationError,
    create_embedding_config_record,
    get_memory_embedding_record,
    get_task_artifact_chunk_embedding_record,
    list_embedding_config_records,
    list_memory_embedding_records,
    list_task_artifact_chunk_embedding_records_for_artifact,
    list_task_artifact_chunk_embedding_records_for_chunk,
    upsert_task_artifact_chunk_embedding_record,
    upsert_memory_embedding_record,
)
from alicebot_api.entity import (
    EntityNotFoundError,
    EntityValidationError,
    create_entity_record,
    get_entity_record,
    list_entity_records,
)
from alicebot_api.entity_edge import (
    EntityEdgeValidationError,
    create_entity_edge_record,
    list_entity_edge_records,
)
from alicebot_api.explicit_preferences import (
    ExplicitPreferenceExtractionValidationError,
    extract_and_admit_explicit_preferences,
)
from alicebot_api.explicit_commitments import (
    ExplicitCommitmentExtractionValidationError,
    extract_and_admit_explicit_commitments,
)
from alicebot_api.explicit_signal_capture import (
    ExplicitSignalCaptureValidationError,
    extract_and_admit_explicit_signals,
)
from alicebot_api.continuity_capture import (
    ContinuityCaptureNotFoundError,
    ContinuityCaptureValidationError,
    capture_continuity_candidates,
    capture_continuity_input,
    commit_continuity_captures,
    get_continuity_capture_detail,
    list_continuity_capture_inbox,
)
from alicebot_api.memory_mutations import (
    MemoryMutationValidationError,
    commit_memory_operations,
    generate_memory_operation_candidates,
    list_memory_operation_candidates,
    list_memory_operations,
)
from alicebot_api.continuity_contradictions import (
    ContinuityContradictionNotFoundError,
    ContinuityContradictionValidationError,
    get_contradiction_case,
    list_contradiction_cases,
    resolve_contradiction_case,
    sync_contradictions,
)
from alicebot_api.continuity_evidence import (
    ContinuityEvidenceNotFoundError,
    build_continuity_explain,
    get_continuity_artifact_detail,
)
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.temporal_state import (
    TemporalStateNotFoundError,
    TemporalStateValidationError,
    get_temporal_explain,
    get_temporal_state_at,
    get_temporal_timeline,
)
from alicebot_api.trusted_fact_promotions import (
    TrustedFactPromotionNotFoundError,
    get_trusted_fact_pattern,
    get_trusted_fact_playbook,
    list_trusted_fact_patterns,
    list_trusted_fact_playbooks,
)
from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    AgentIdentityValidationError,
    AgentPolicyBlockedError,
    PolicyDecision,
    agent_metadata,
    append_policy_events,
    evaluate_agent_policy,
    resource_project_scope,
    summarize_agent_policy_telemetry,
)
from alicebot_api.vnext_agent_keys import (
    AgentKeyAuthenticationError,
    agent_key_from_authorization,
    resolve_protected_agent_identity,
)
from alicebot_api.vnext_project_scope import source_project_scope
from alicebot_api.vnext_artifact_review import dispatch_vnext_artifact_review
from alicebot_api.vnext_brain import BrainArtifactRequest, VNextBrainService, VNextBrainValidationError
from alicebot_api.vnext_capture import VNextCaptureService, VNextCaptureValidationError
from alicebot_api.vnext_embeddings import (
    persist_deferred_memory_embeddings_best_effort,
)
from alicebot_api.vnext_connections import (
    ConnectionFinderRequest,
    VNextConnectionService,
    VNextConnectionValidationError,
)
from alicebot_api.vnext_connectors import (
    VNextConnectorService,
    VNextConnectorValidationError,
    list_connector_definitions,
    scan_local_folder,
)
from alicebot_api.vnext_context_tree import (
    ContextTreeRequest,
    VNextContextTreeService,
    VNextContextTreeStore,
    VNextContextTreeValidationError,
)
from alicebot_api.vnext_contradictions import (
    ContradictionFinderRequest,
    VNextContradictionService,
    VNextContradictionValidationError,
)
from alicebot_api.vnext_dogfooding import VNextDogfoodingService
from alicebot_api.vnext_doctor import VNextDoctorService
from alicebot_api.vnext_event_log import append_event
from alicebot_api.mcp_tools import redact_memory_flow
from alicebot_api.vnext_memory_commit import (
    VNextMemoryCommitService,
    VNextMemoryCommitValidationError,
    is_pending_consolidation_candidate,
    memory_commit_request_from_payload,
)
from alicebot_api.vnext_projects import (
    PROJECT_UPDATE_TERMINAL_CONSISTENCY_MESSAGE,
    ProjectAutomationRequest,
    VNextProjectService,
    VNextProjectTerminalConsistencyError,
    VNextProjectValidationError,
)
from alicebot_api.vnext_queue import (
    QueueTaskRequest,
    VNextQueueNotFoundError,
    VNextQueueService,
    VNextQueueValidationError,
)
from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService, VNextRetrievalValidationError
from alicebot_api.vnext_scheduler import (
    SchedulerRunRequest,
    VNextSchedulerService,
    VNextSchedulerValidationError,
    validate_schedule,
)
from alicebot_api.vnext_scheduler_runtime import (
    daemon_status,
    run_due_workflows_durable,
    run_now_durable,
)
from alicebot_api.vnext_store import PostgresVNextStore
from alicebot_api.continuity_lifecycle import (
    ContinuityLifecycleNotFoundError,
    ContinuityLifecycleValidationError,
    get_continuity_lifecycle_state,
    list_continuity_lifecycle_state,
)
from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError,
    RetrievalTraceNotFoundError,
    get_retrieval_trace,
    list_retrieval_runs,
    query_continuity_recall,
)
from alicebot_api.public_evals import (
    get_public_eval_run,
    list_public_eval_runs,
    list_public_eval_suites,
    run_public_evals,
)
from alicebot_api.retrieval_evaluation import get_retrieval_evaluation_summary
from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError,
    ContinuityReviewValidationError,
    apply_continuity_correction,
    get_continuity_review_detail,
    list_continuity_review_queue,
)
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError,
    compile_continuity_resumption_brief,
)
from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopNotFoundError,
    ContinuityOpenLoopValidationError,
    apply_continuity_open_loop_review_action,
    compile_continuity_daily_brief,
    compile_continuity_open_loop_dashboard,
    compile_continuity_weekly_review,
)
from alicebot_api.conversation_health import get_thread_health_dashboard
from alicebot_api.continuity_objects import ContinuityObjectValidationError
from alicebot_api.memory import (
    MemoryAdmissionValidationError,
    MemoryReviewNotFoundError,
    OpenLoopNotFoundError,
    OpenLoopValidationError,
    admit_memory_candidate,
    create_open_loop_record,
    create_memory_review_label_record,
    get_open_loop_record,
    get_memory_evaluation_summary,
    get_memory_hygiene_dashboard_summary,
    get_memory_quality_gate_summary,
    get_memory_trust_dashboard_summary,
    get_memory_review_record,
    list_open_loop_records,
    list_memory_review_queue_records,
    list_memory_review_label_records,
    list_memory_review_records,
    list_memory_revision_review_records,
    update_open_loop_status_record,
)
from alicebot_api.policy import (
    PolicyEvaluationValidationError,
    PolicyNotFoundError,
    PolicyValidationError,
    create_policy_record,
    evaluate_policy_request,
    get_policy_record,
    list_consent_records,
    list_policy_records,
    upsert_consent_record,
)
from alicebot_api.tools import (
    ToolAllowlistValidationError,
    ToolNotFoundError,
    ToolRoutingValidationError,
    ToolValidationError,
    create_tool_record,
    evaluate_tool_allowlist,
    get_tool_record,
    list_tool_records,
    route_tool_invocation,
)
from alicebot_api.semantic_retrieval import (
    SemanticArtifactChunkRetrievalValidationError,
    SemanticMemoryRetrievalValidationError,
    retrieve_artifact_scoped_semantic_artifact_chunk_records,
    retrieve_semantic_memory_records,
    retrieve_task_scoped_semantic_artifact_chunk_records,
)
from alicebot_api.response_generation import (
    DEVELOPER_INSTRUCTION,
    ModelInvocationError,
    ModelProviderUnavailableError,
    ResponseGenerationConflictError,
    ResponseFailure,
    SYSTEM_INSTRUCTION,
    complete_response_generation,
    fail_response_generation,
    prepare_response_generation,
)
from alicebot_api.response_jobs import (
    RESPONSE_JOB_ENDPOINT_RUNTIME,
    RESPONSE_JOB_LEASE_SECONDS,
    ResponseGenerationJobRow,
    ResponseGenerationJobStore,
    ResponseJobFenceLostError,
    normalize_idempotency_key,
    request_fingerprint,
)
from alicebot_api.azure_provider_helpers import (
    AZURE_AUTH_MODE_AD_TOKEN,
    AZURE_AUTH_MODE_API_KEY,
    DEFAULT_AZURE_API_VERSION,
)
from alicebot_api.provider_runtime import (
    AZURE_ADAPTER_KEY,
    LLAMACPP_ADAPTER_KEY,
    OLLAMA_ADAPTER_KEY,
    VLLM_ADAPTER_KEY,
    OPENAI_RESPONSES_PROVIDER,
    ProviderAdapter,
    ProviderAdapterNotFoundError,
    ProviderCapabilitySnapshot,
    RuntimeProviderConfig,
    build_provider_test_model_request,
    make_provider_adapter_registry,
    normalized_capability_snapshot,
    resolve_runtime_provider_config_secrets,
)
from alicebot_api.provider_configuration import provider_config_fingerprint
from alicebot_api.openapi_operation_contracts import (
    OPENAPI_INTENTIONALLY_POLYMORPHIC_OPERATIONS,
    OPENAPI_OPEN_RESPONSE_OPERATIONS,
    OPENAPI_OPERATION_RESPONSE_SCHEMAS,
    OPENAPI_SOURCE_VERIFIED_OPERATIONS,
)
from alicebot_api.task_briefing import (
    TaskBriefNotFoundError,
    TaskBriefValidationError,
    compare_task_briefs,
    compile_and_persist_task_brief,
    get_persisted_task_brief,
)
from alicebot_api.provider_secrets import (
    ProviderSecretManagerError,
    build_provider_secret_ref,
    decode_provider_secret_ref,
    delete_provider_api_key,
    encode_provider_secret_ref,
    is_provider_secret_ref,
    write_provider_api_key,
)
from alicebot_api.provider_security import (
    sanitize_provider_error_message,
    validate_provider_base_url,
)
from alicebot_api.store import (
    ContinuityStore,
    ContinuityStoreInvariantError,
    EventRow,
    JsonObject,
    JsonValue,
    ModelProviderRow,
    ProviderCapabilityRow,
    SessionRow,
    ThreadRow,
)
from alicebot_api.traces import (
    TraceNotFoundError,
    get_trace_record,
    list_trace_event_records,
    list_trace_records,
)

LOGGER = logging.getLogger(__name__)


class BaseModel(PydanticBaseModel):
    """Fail-closed request model shared by all HTTP body contracts."""

    model_config = ConfigDict(extra="forbid")


def _openapi_tag_for_path(path: str) -> str:
    if path in {"/healthz", "/readyz", "/version"}:
        return "Operations"
    if path.startswith("/v0/vnext"):
        return "vNext memory"
    if path.startswith("/v0"):
        return "Continuity v0"
    if path.startswith("/v1/providers") or path.startswith("/v1/workspaces") or path.startswith("/v1/runtime"):
        return "Providers"
    return "Alice API"


_OPENAPI_EXACT_RESPONSE_CONTRACTS: dict[tuple[str, str], tuple[str, object]] = {
    ("GET", "/v0/agent-profiles"): ("AgentProfileListResponse", AgentProfileListResponse),
    ("POST", "/v0/threads"): ("ThreadCreateResponse", ThreadCreateResponse),
    ("GET", "/v0/threads"): ("ThreadListResponse", ThreadListResponse),
    ("GET", "/v0/threads/health-dashboard"): ("ThreadHealthDashboardResponse", ThreadHealthDashboardResponse),
    ("GET", "/v0/threads/{thread_id}"): ("ThreadDetailResponse", ThreadDetailResponse),
    ("GET", "/v0/threads/{thread_id}/sessions"): ("ThreadSessionListResponse", ThreadSessionListResponse),
    ("GET", "/v0/threads/{thread_id}/events"): ("ThreadEventListResponse", ThreadEventListResponse),
    ("GET", "/v0/threads/{thread_id}/resumption-brief"): ("ResumptionBriefResponse", ResumptionBriefResponse),
    ("GET", "/v0/admin/debug/continuity/lifecycle"): (
        "ContinuityLifecycleListResponse",
        ContinuityLifecycleListResponse,
    ),
    ("GET", "/v0/admin/debug/continuity/lifecycle/{continuity_object_id}"): (
        "ContinuityLifecycleDetailResponse",
        ContinuityLifecycleDetailResponse,
    ),
    ("GET", "/v0/continuity/review-queue"): ("ContinuityReviewQueueResponse", ContinuityReviewQueueResponse),
    ("GET", "/v0/continuity/review-queue/{continuity_object_id}"): (
        "ContinuityReviewDetailResponse",
        ContinuityReviewDetailResponse,
    ),
    ("GET", "/v0/continuity/explain/{continuity_object_id}"): (
        "ContinuityExplainResponse",
        ContinuityExplainResponse,
    ),
    ("POST", "/v1/contradictions/detect"): ("ContradictionSyncResponse", ContradictionSyncResponse),
    ("GET", "/v1/contradictions/cases"): ("ContradictionCaseListResponse", ContradictionCaseListResponse),
    ("GET", "/v1/contradictions/cases/{contradiction_case_id}"): (
        "ContradictionCaseDetailResponse",
        ContradictionCaseDetailResponse,
    ),
    ("POST", "/v1/contradictions/cases/{contradiction_case_id}/resolve"): (
        "ContradictionResolveResponse",
        ContradictionResolveResponse,
    ),
    ("GET", "/v1/trust/signals"): ("TrustSignalListResponse", TrustSignalListResponse),
    ("GET", "/v0/state-at"): ("TemporalStateAtResponse", TemporalStateAtResponse),
    ("GET", "/v0/timeline"): ("TemporalTimelineResponse", TemporalTimelineResponse),
    ("GET", "/v0/explain"): ("TemporalExplainResponse", TemporalExplainResponse),
    ("GET", "/v0/patterns"): ("TrustedFactPatternListResponse", TrustedFactPatternListResponse),
    ("GET", "/v0/patterns/{pattern_id}"): ("TrustedFactPatternExplainResponse", TrustedFactPatternExplainResponse),
    ("GET", "/v0/playbooks"): ("TrustedFactPlaybookListResponse", TrustedFactPlaybookListResponse),
    ("GET", "/v0/playbooks/{playbook_id}"): (
        "TrustedFactPlaybookExplainResponse",
        TrustedFactPlaybookExplainResponse,
    ),
    ("GET", "/v0/admin/debug/continuity/artifacts/{artifact_id}"): (
        "ContinuityArtifactDetailResponse",
        ContinuityArtifactDetailResponse,
    ),
    ("GET", "/v0/continuity/open-loops"): (
        "ContinuityOpenLoopDashboardResponse",
        ContinuityOpenLoopDashboardResponse,
    ),
    ("GET", "/v0/continuity/daily-brief"): ("ContinuityDailyBriefResponse", ContinuityDailyBriefResponse),
    ("GET", "/v0/continuity/weekly-review"): (
        "ContinuityWeeklyReviewResponse",
        ContinuityWeeklyReviewResponse,
    ),
    ("POST", "/v0/continuity/open-loops/{continuity_object_id}/review-action"): (
        "ContinuityOpenLoopReviewActionResponse",
        ContinuityOpenLoopReviewActionResponse,
    ),
    ("GET", "/v0/continuity/recall"): ("ContinuityRecallResponse", ContinuityRecallResponse),
    ("GET", "/v0/continuity/retrieval-runs"): ("RetrievalRunListResponse", RetrievalRunListResponse),
    ("GET", "/v0/continuity/retrieval-runs/{retrieval_run_id}"): (
        "RetrievalTraceResponse",
        RetrievalTraceResponse,
    ),
    ("GET", "/v0/continuity/retrieval-evaluation"): (
        "RetrievalEvaluationResponse",
        RetrievalEvaluationResponse,
    ),
    ("GET", "/v1/evals/suites"): ("PublicEvalSuiteDefinitionListResponse", PublicEvalSuiteDefinitionListResponse),
    ("POST", "/v1/evals/runs"): ("PublicEvalRunDetailResponse", PublicEvalRunDetailResponse),
    ("GET", "/v1/evals/runs"): ("PublicEvalRunListResponse", PublicEvalRunListResponse),
    ("GET", "/v1/evals/runs/{eval_run_id}"): ("PublicEvalRunDetailResponse", PublicEvalRunDetailResponse),
    ("GET", "/v0/continuity/resumption-brief"): (
        "ContinuityResumptionBriefResponse",
        ContinuityResumptionBriefResponse,
    ),
    ("POST", "/v1/continuity/brief"): ("ContinuityBriefResponse", ContinuityBriefResponse),
    ("POST", "/v0/task-briefs/compile"): ("TaskBriefResponse", TaskBriefResponse),
    ("POST", "/v0/task-briefs/compare"): ("TaskBriefComparisonResponse", TaskBriefComparisonResponse),
    ("GET", "/v0/memories/trust-dashboard"): ("MemoryTrustDashboardResponse", MemoryTrustDashboardResponse),
    ("GET", "/v0/memories/hygiene-dashboard"): ("MemoryHygieneDashboardResponse", MemoryHygieneDashboardResponse),
}


_OPENAPI_CREATED_ONLY_OPERATIONS = {
    ("POST", "/v0/threads"),
    ("POST", "/v0/open-loops"),
    ("POST", "/v0/policies"),
    ("POST", "/v0/tools"),
    ("POST", "/v0/tasks/{task_id}/runs"),
    ("POST", "/v0/gmail-accounts"),
    ("POST", "/v0/calendar-accounts"),
    ("POST", "/v0/tasks/{task_id}/workspace"),
    ("POST", "/v0/task-workspaces/{task_workspace_id}/artifacts"),
    ("POST", "/v0/tasks/{task_id}/steps"),
    ("POST", "/v0/execution-budgets"),
    ("POST", "/v0/continuity/captures"),
    ("POST", "/v0/vnext/sources"),
    ("POST", "/v0/vnext/projects"),
    ("POST", "/v0/vnext/connectors/telegram/sync"),
    ("POST", "/v0/vnext/connectors/local-folder/sync"),
    ("POST", "/v0/vnext/connectors/browser-clipper/capture"),
    ("POST", "/v0/vnext/agents/ingest-output"),
    ("POST", "/v0/vnext/artifacts/{artifact_id}/insight-feedback"),
    ("POST", "/v0/vnext/context-packs"),
    ("POST", "/v0/vnext/memory-proposals"),
    ("POST", "/v0/vnext/artifacts/generate/daily-brief"),
    ("POST", "/v0/vnext/artifacts/generate/weekly-synthesis"),
    ("POST", "/v0/vnext/artifacts/generate/connections"),
    ("POST", "/v0/vnext/artifacts/generate/contradictions"),
    ("POST", "/v0/vnext/queue/tasks"),
    ("POST", "/v0/vnext/artifacts/{artifact_id}/quality-ratings"),
    ("POST", "/v0/vnext/projects/update-candidates"),
    ("POST", "/v0/vnext/open-loops"),
    ("POST", "/v0/vnext/scheduler/workflows/{workflow_type}/run-now"),
    ("POST", "/v0/vnext/scheduler/run-due"),
    ("POST", "/v0/vnext/open-loops/extract"),
    ("POST", "/v0/task-briefs/compile"),
    ("POST", "/v0/memories/{memory_id}/labels"),
    ("POST", "/v0/embedding-configs"),
    ("POST", "/v0/memory-embeddings"),
    ("POST", "/v0/task-artifact-chunk-embeddings"),
    ("POST", "/v0/entities"),
    ("POST", "/v0/entity-edges"),
    ("POST", "/v1/providers"),
    ("POST", "/v1/providers/ollama/register"),
    ("POST", "/v1/providers/llamacpp/register"),
    ("POST", "/v1/providers/vllm/register"),
    ("POST", "/v1/providers/azure/register"),
}


_OPENAPI_CONDITIONAL_SUCCESS_OPERATIONS: dict[tuple[str, str], tuple[int, ...]] = {
    ("POST", "/v0/consents"): (200, 201),
    ("POST", "/v0/vnext/memories/commit"): (200, 201),
    ("POST", "/v0/vnext/connectors/{connector_name}/sync"): (201, 207),
    ("POST", "/v1/runtime/invoke"): (200, 202),
}


LEGACY_HTTP_OPERATION_KEYS: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/v0/tools"),
        ("GET", "/v0/tools"),
        ("GET", "/v0/tools/{tool_id}"),
        ("POST", "/v0/tools/allowlist/evaluate"),
        ("POST", "/v0/tools/route"),
        ("POST", "/v0/approvals/requests"),
        ("GET", "/v0/approvals"),
        ("GET", "/v0/approvals/{approval_id}"),
        ("POST", "/v0/approvals/{approval_id}/approve"),
        ("POST", "/v0/approvals/{approval_id}/reject"),
        ("POST", "/v0/approvals/{approval_id}/execute"),
        ("GET", "/v0/tasks"),
        ("GET", "/v0/tasks/{task_id}"),
        ("POST", "/v0/tasks/{task_id}/runs"),
        ("GET", "/v0/tasks/{task_id}/runs"),
        ("POST", "/v0/tasks/{task_id}/workspace"),
        ("GET", "/v0/tasks/{task_id}/steps"),
        ("POST", "/v0/tasks/{task_id}/artifact-chunks/retrieve"),
        ("POST", "/v0/tasks/{task_id}/artifact-chunks/semantic-retrieval"),
        ("POST", "/v0/tasks/{task_id}/steps"),
        ("GET", "/v0/task-runs/{task_run_id}"),
        ("POST", "/v0/task-runs/{task_run_id}/tick"),
        ("POST", "/v0/task-runs/{task_run_id}/pause"),
        ("POST", "/v0/task-runs/{task_run_id}/resume"),
        ("POST", "/v0/task-runs/{task_run_id}/cancel"),
        ("GET", "/v0/task-workspaces"),
        ("GET", "/v0/task-workspaces/{task_workspace_id}"),
        ("POST", "/v0/task-workspaces/{task_workspace_id}/artifacts"),
        ("GET", "/v0/task-steps/{task_step_id}"),
        ("POST", "/v0/task-steps/{task_step_id}/transition"),
        ("POST", "/v0/execution-budgets"),
        ("GET", "/v0/execution-budgets"),
        ("GET", "/v0/execution-budgets/{execution_budget_id}"),
        ("POST", "/v0/execution-budgets/{execution_budget_id}/deactivate"),
        ("POST", "/v0/execution-budgets/{execution_budget_id}/supersede"),
        ("GET", "/v0/tool-executions"),
        ("GET", "/v0/tool-executions/{execution_id}"),
        ("POST", "/v0/task-briefs/compile"),
        ("GET", "/v0/task-briefs/{task_brief_id}"),
        ("POST", "/v0/task-briefs/compare"),
        ("POST", "/v0/gmail-accounts"),
        ("GET", "/v0/gmail-accounts"),
        ("GET", "/v0/gmail-accounts/{gmail_account_id}"),
        ("POST", "/v0/gmail-accounts/{gmail_account_id}/messages/{provider_message_id}/ingest"),
        ("POST", "/v0/calendar-accounts"),
        ("GET", "/v0/calendar-accounts"),
        ("GET", "/v0/calendar-accounts/{calendar_account_id}"),
        ("GET", "/v0/calendar-accounts/{calendar_account_id}/events"),
        ("POST", "/v0/calendar-accounts/{calendar_account_id}/events/{provider_event_id}/ingest"),
    }
)
LEGACY_SURFACES_ENABLED = legacy_surfaces_enabled()


def _openapi_live_operation_keys(schema: dict[str, Any]) -> set[tuple[str, str]]:
    operation_keys: set[tuple[str, str]] = set()
    for path, path_item in schema.get("paths", {}).items():
        if not isinstance(path, str) or not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method in {"get", "post", "put", "patch", "delete"} and isinstance(operation, dict):
                operation_keys.add((method.upper(), path))
    return operation_keys


class AliceFastAPI(FastAPI):
    """FastAPI app with concrete success contracts for every JSON route."""

    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is not None:
            return self.openapi_schema
        schema = get_openapi(
            title=self.title,
            version=self.version,
            description=self.description,
            routes=self.routes,
        )
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        live_operation_keys = _openapi_live_operation_keys(schema)
        registered_operation_keys = set(_OPENAPI_EXACT_RESPONSE_CONTRACTS) | set(OPENAPI_OPERATION_RESPONSE_SCHEMAS)
        expected_live_operation_keys = (
            registered_operation_keys
            if LEGACY_SURFACES_ENABLED
            else registered_operation_keys - LEGACY_HTTP_OPERATION_KEYS
        )
        if live_operation_keys != expected_live_operation_keys:
            missing = sorted(live_operation_keys - expected_live_operation_keys)
            extra = sorted(expected_live_operation_keys - live_operation_keys)
            raise RuntimeError(
                f"OpenAPI success-contract registry drifted from live routes; missing={missing}, extra={extra}"
            )
        if not LEGACY_HTTP_OPERATION_KEYS <= registered_operation_keys:
            missing_legacy = sorted(LEGACY_HTTP_OPERATION_KEYS - registered_operation_keys)
            raise RuntimeError(f"legacy OpenAPI operation inventory is incomplete: {missing_legacy}")
        live_registry = {
            operation_key: contract
            for operation_key, contract in OPENAPI_OPERATION_RESPONSE_SCHEMAS.items()
            if operation_key in live_operation_keys
        }
        live_exact_contracts = {
            operation_key: contract
            for operation_key, contract in _OPENAPI_EXACT_RESPONSE_CONTRACTS.items()
            if operation_key in live_operation_keys
        }
        component_names = [
            component_name for component_name, _component_schema in live_registry.values()
        ]
        if len(component_names) != len(set(component_names)):
            raise RuntimeError("OpenAPI per-operation success component names must be unique")
        non_closed_operation_keys = {
            operation_key
            for operation_key, (_component_name, component_schema) in live_registry.items()
            if component_schema.get("additionalProperties") is not False
        }
        closed_operation_keys = set(live_registry) - non_closed_operation_keys
        expected_closed_operation_keys = set(OPENAPI_SOURCE_VERIFIED_OPERATIONS) & live_operation_keys
        if closed_operation_keys != expected_closed_operation_keys:
            raise RuntimeError("OpenAPI source-verified operation inventory drifted from closed schemas")
        expected_open_operation_keys = set(OPENAPI_OPEN_RESPONSE_OPERATIONS) & live_operation_keys
        if non_closed_operation_keys != expected_open_operation_keys:
            raise RuntimeError("OpenAPI open operation inventory drifted from permissive schemas")
        if not set(OPENAPI_INTENTIONALLY_POLYMORPHIC_OPERATIONS) <= non_closed_operation_keys:
            raise RuntimeError("OpenAPI polymorphic operations must use permissive schemas")
        if any(not justification.strip() for justification in OPENAPI_INTENTIONALLY_POLYMORPHIC_OPERATIONS.values()):
            raise RuntimeError("OpenAPI polymorphic operations require individual justifications")
        for component_name, component_schema in live_registry.values():
            components[component_name] = component_schema
        for component_name, contract in live_exact_contracts.values():
            contract_schema = TypeAdapter(contract).json_schema(
                ref_template="#/components/schemas/{model}",
            )
            definitions = contract_schema.pop("$defs", {})
            if isinstance(definitions, dict):
                for definition_name, definition in definitions.items():
                    components.setdefault(definition_name, definition)
            contract_schema["additionalProperties"] = False
            components[component_name] = contract_schema
        components["APIErrorResponse"] = {
            "title": "API error response",
            "type": "object",
            "required": ["detail"],
            "properties": {
                "detail": {
                    "description": "Human-readable detail or structured error payload.",
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object", "additionalProperties": True},
                        {"type": "array", "items": {}},
                    ],
                }
            },
        }
        tag_descriptions = {
            "Operations": "Health, readiness, and build identity.",
            "vNext memory": "Agentic memory, retrieval, project, and scheduler workflows.",
            "Continuity v0": "Deterministic continuity and memory APIs.",
            "Providers": "Model-provider discovery, configuration, and invocation.",
            "Alice API": "Local-first agent interface and continuity operations.",
        }
        schema["tags"] = [{"name": name, "description": description} for name, description in tag_descriptions.items()]
        for path, path_item in schema.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                operation_key = (method.upper(), path)
                operation.setdefault("tags", [_openapi_tag_for_path(path)])
                summary = operation.get("summary")
                operation.setdefault(
                    "description",
                    f"{summary}." if isinstance(summary, str) and summary else "AliceBot API operation.",
                )
                responses = operation.get("responses")
                if not isinstance(responses, dict):
                    continue
                expected_statuses: tuple[int, ...] | None = None
                if operation_key in _OPENAPI_CREATED_ONLY_OPERATIONS:
                    expected_statuses = (201,)
                elif operation_key in _OPENAPI_CONDITIONAL_SUCCESS_OPERATIONS:
                    expected_statuses = _OPENAPI_CONDITIONAL_SUCCESS_OPERATIONS[operation_key]
                if expected_statuses is not None:
                    for status_code in tuple(responses):
                        if str(status_code).startswith("2") and int(status_code) not in expected_statuses:
                            responses.pop(status_code)
                    for status_code in expected_statuses:
                        responses.setdefault(str(status_code), {"description": "Successful response"})

                exact_contract = _OPENAPI_EXACT_RESPONSE_CONTRACTS.get(operation_key)
                if exact_contract is not None:
                    schema_name = exact_contract[0]
                else:
                    operation_contract = live_registry.get(operation_key)
                    if operation_contract is None:  # pragma: no cover - inventory fence above
                        raise RuntimeError(f"OpenAPI operation {operation_key!r} has no success contract")
                    schema_name = operation_contract[0]
                for status_code, response in responses.items():
                    if not str(status_code).startswith("2") or not isinstance(response, dict):
                        continue
                    content = response.setdefault("content", {})
                    if isinstance(content, dict):
                        json_content = content.setdefault("application/json", {})
                        if isinstance(json_content, dict):
                            json_content["schema"] = {"$ref": f"#/components/schemas/{schema_name}"}
                if path == "/healthz":
                    responses["503"] = {
                        "description": "Service is degraded or unavailable",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/HealthcheckSuccessResponse"}}
                        },
                    }
                responses.setdefault(
                    "default",
                    {
                        "description": "Error response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/APIErrorResponse"}}},
                    },
                )
        self.openapi_schema = schema
        return self.openapi_schema


app = AliceFastAPI(
    title="AliceBot API",
    version=__version__,
    description="AliceBot local-first continuity, retrieval, and agentic-memory API.",
)
provider_adapter_registry = make_provider_adapter_registry()
HealthStatus = Literal["ok", "degraded"]
ServiceStatus = Literal["ok", "unreachable", "not_checked"]


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        output: JsonObject = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            output[key] = _json_value(item)
        return output
    raise ValueError(f"value of type {type(value).__name__} is not JSON-compatible")


def _json_object(value: object) -> JsonObject:
    normalized = _json_value(value)
    if not isinstance(normalized, dict):
        raise ValueError("expected a JSON object")
    return normalized


def _object_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("expected a mapping row")
    output: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError("row keys must be strings")
        output[key] = item
    return output


class DatabaseServicePayload(TypedDict):
    status: Literal["ok", "unreachable"]


class RedisServicePayload(TypedDict):
    status: Literal["not_checked"]
    url: str


class ObjectStorageServicePayload(TypedDict):
    status: Literal["not_checked"]


class HealthServicesPayload(TypedDict):
    database: DatabaseServicePayload
    redis: RedisServicePayload
    object_storage: ObjectStorageServicePayload


class HealthcheckPayload(TypedDict):
    status: HealthStatus
    environment: str
    services: HealthServicesPayload


AUTH_USER_HEADER = "X-AliceBot-User-Id"


def _resolve_authenticated_user_id(settings: Settings, request: Request) -> UUID | None:
    if settings.auth_user_id != "":
        return UUID(settings.auth_user_id)

    header_value = request.headers.get(AUTH_USER_HEADER)
    if header_value is None or header_value.strip() == "":
        if settings.app_env in {"development", "test"}:
            return None
        raise ValueError(
            "request authentication is not configured; set ALICEBOT_AUTH_USER_ID or provide X-AliceBot-User-Id"
        )

    try:
        return UUID(header_value)
    except ValueError as exc:
        raise ValueError("X-AliceBot-User-Id must be a valid UUID") from exc


def _rewrite_user_id_query_param(request: Request, authenticated_user_id: UUID) -> None:
    raw_query = request.scope.get("query_string", b"")
    query_items = parse_qsl(raw_query.decode("utf-8"), keep_blank_values=True)
    expected_user_id = str(authenticated_user_id)
    for key, value in query_items:
        if key == "user_id" and value != expected_user_id:
            raise ValueError("query user_id does not match authenticated user")
    rewritten_items = [(key, value) for key, value in query_items if key != "user_id"]
    rewritten_items.append(("user_id", expected_user_id))
    request.scope["query_string"] = urlencode(rewritten_items, doseq=True).encode("utf-8")


async def _rewrite_user_id_json_body(request: Request, authenticated_user_id: UUID) -> Request:
    if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return request

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return request

    raw_body = await request.body()
    if raw_body == b"":
        return request

    try:
        parsed_body = json.loads(raw_body)
    except json.JSONDecodeError:
        return request

    if not isinstance(parsed_body, dict):
        return request

    expected_user_id = str(authenticated_user_id)
    existing_user_id = parsed_body.get("user_id")
    if existing_user_id is not None and str(existing_user_id) != expected_user_id:
        raise ValueError("request user_id does not match authenticated user")
    parsed_body["user_id"] = expected_user_id
    rewritten_body = json.dumps(parsed_body, separators=(",", ":"), ensure_ascii=True).encode("utf-8")

    async def receive() -> dict[str, object]:
        return {
            "type": "http.request",
            "body": rewritten_body,
            "more_body": False,
        }

    return Request(request.scope, receive)


class CompileContextSemanticRequest(BaseModel):
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    )


class CompileContextTaskScopedArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["task"]
    task_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


class CompileContextArtifactScopedArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["artifact"]
    task_artifact_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


CompileContextArtifactRetrievalRequest = Annotated[
    CompileContextTaskScopedArtifactRetrievalRequest | CompileContextArtifactScopedArtifactRetrievalRequest,
    Field(discriminator="kind"),
]


class CompileContextTaskScopedSemanticArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["task"]
    task_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


class CompileContextArtifactScopedSemanticArtifactRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["artifact"]
    task_artifact_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


CompileContextSemanticArtifactRetrievalRequest = Annotated[
    CompileContextTaskScopedSemanticArtifactRetrievalRequest
    | CompileContextArtifactScopedSemanticArtifactRetrievalRequest,
    Field(discriminator="kind"),
]


class CompileContextRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    max_sessions: int = Field(default=DEFAULT_MAX_SESSIONS, ge=0, le=25)
    max_events: int = Field(default=DEFAULT_MAX_EVENTS, ge=0, le=200)
    max_memories: int = Field(default=DEFAULT_MAX_MEMORIES, ge=0, le=50)
    max_entities: int = Field(default=DEFAULT_MAX_ENTITIES, ge=0, le=50)
    max_entity_edges: int = Field(default=DEFAULT_MAX_ENTITY_EDGES, ge=0, le=100)
    semantic: CompileContextSemanticRequest | None = None
    artifact_retrieval: CompileContextArtifactRetrievalRequest | None = None
    semantic_artifact_retrieval: CompileContextSemanticArtifactRetrievalRequest | None = None


class CreateThreadRequest(BaseModel):
    user_id: UUID
    title: str = Field(min_length=1, max_length=200)
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)


class AdmitMemoryOpenLoopRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=280)
    due_at: datetime | None = None


class AdmitMemoryRequest(BaseModel):
    user_id: UUID
    memory_key: str = Field(min_length=1, max_length=200)
    value: object | None = None
    source_event_ids: list[UUID] = Field(min_length=1)
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)
    delete_requested: bool = False
    memory_type: str | None = Field(default=None, min_length=1, max_length=100)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    salience: float | None = Field(default=None, ge=0.0, le=1.0)
    confirmation_status: str | None = Field(default=None, min_length=1, max_length=100)
    trust_class: str | None = Field(default=None, min_length=1, max_length=100)
    promotion_eligibility: str | None = Field(default=None, min_length=1, max_length=100)
    evidence_count: int | None = Field(default=None, ge=0)
    independent_source_count: int | None = Field(default=None, ge=0)
    extracted_by_model: str | None = Field(default=None, min_length=1, max_length=200)
    trust_reason: str | None = Field(default=None, min_length=1, max_length=500)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    last_confirmed_at: datetime | None = None
    open_loop: AdmitMemoryOpenLoopRequest | None = None

    @model_validator(mode="after")
    def validate_temporal_range(self) -> "AdmitMemoryRequest":
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be greater than or equal to valid_from")
        return self


class ExtractExplicitPreferencesRequest(BaseModel):
    user_id: UUID
    source_event_id: UUID


class ExtractExplicitCommitmentsRequest(BaseModel):
    user_id: UUID
    source_event_id: UUID


class CaptureExplicitSignalsRequest(BaseModel):
    user_id: UUID
    source_event_id: UUID


class ContinuityCaptureRequest(BaseModel):
    user_id: UUID
    raw_content: str = Field(min_length=1, max_length=4000)
    explicit_signal: ContinuityCaptureExplicitSignal | None = None


VNextDomain = Literal[
    "professional",
    "personal",
    "family",
    "health",
    "spiritual",
    "financial",
    "legal",
    "learning",
    "relationship",
    "project",
    "agent_run",
    "system",
    "unknown",
]
VNextSensitivity = Literal[
    "public",
    "internal",
    "private",
    "confidential",
    "highly_sensitive",
    "sacred",
    "regulated",
    "unknown",
]


class VNextAgentIdentityRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=120)
    agent_type: str = Field(default="unknown", min_length=1, max_length=80)
    agent_run_id: str | None = Field(default=None, min_length=1, max_length=160)
    task_id: str | None = Field(default=None, min_length=1, max_length=160)
    project_scope: list[str] = Field(default_factory=list)
    permission_profile: str | None = Field(default=None, min_length=1, max_length=80)


class VNextAgentRequest(BaseModel):
    agent: VNextAgentIdentityRequest | None = None
    agent_identity: VNextAgentIdentityRequest | None = None
    agent_id: str | None = Field(default=None, min_length=1, max_length=120)
    agent_type: str | None = Field(default=None, min_length=1, max_length=80)
    agent_run_id: str | None = Field(default=None, min_length=1, max_length=160)
    task_id: str | None = Field(default=None, min_length=1, max_length=160)
    project_scope: list[str] = Field(default_factory=list)
    permission_profile: str | None = Field(default=None, min_length=1, max_length=80)
    trace_id: str | None = Field(default=None, min_length=1, max_length=160)


class VNextSourceCaptureRequest(VNextAgentRequest):
    user_id: UUID
    raw_text: str = Field(min_length=1, max_length=200_000)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    domain: VNextDomain = "unknown"
    sensitivity: VNextSensitivity = "unknown"


class VNextSourceReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    domain: VNextDomain | None = None
    sensitivity: VNextSensitivity | None = None
    project_id: str | None = Field(default=None, min_length=1, max_length=120)
    review_note: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextConnectorSyncRequest(VNextAgentRequest):
    user_id: UUID
    items: list[dict[str, object]] = Field(default_factory=list)
    default_domain: VNextDomain | None = None
    default_sensitivity: VNextSensitivity | None = None


class VNextConnectorConfigRequest(VNextAgentRequest):
    user_id: UUID
    enabled: bool | None = None
    default_domain: VNextDomain | None = None
    default_sensitivity: VNextSensitivity | None = None
    secret_ref: str | None = Field(default=None, min_length=1, max_length=240)
    sync_mode: str | None = Field(default=None, min_length=1, max_length=40)
    poll_interval_seconds: int | None = Field(default=None, ge=1, le=86_400)
    config_json: dict[str, object] = Field(default_factory=dict)


class VNextTelegramSyncRequest(VNextAgentRequest):
    user_id: UUID
    updates: list[dict[str, object]] = Field(min_length=1)
    allowed_chat_ids: list[str] = Field(min_length=1)
    default_domain: VNextDomain | None = None
    default_sensitivity: VNextSensitivity | None = None


class VNextLocalFolderSyncRequest(VNextAgentRequest):
    user_id: UUID
    paths: list[str] = Field(default_factory=list)
    recursive: bool = True
    extensions: list[str] = Field(default_factory=lambda: [".md", ".txt"])
    ignore_patterns: list[str] = Field(default_factory=list)
    default_domain: VNextDomain | None = None
    default_sensitivity: VNextSensitivity | None = None


class VNextBrowserClipperCaptureRequest(VNextAgentRequest):
    user_id: UUID
    url: str = Field(min_length=1, max_length=4000)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    selected_text: str | None = Field(default=None, min_length=1, max_length=200_000)
    page_text: str | None = Field(default=None, min_length=1, max_length=500_000)
    user_note: str | None = Field(default=None, min_length=1, max_length=20_000)
    capture_token: str | None = Field(default=None, min_length=1, max_length=500)
    captured_at: str | None = Field(default=None, min_length=1, max_length=120)
    domain: VNextDomain = "professional"
    sensitivity: VNextSensitivity = "private"


class VNextAgentOutputIngestRequest(VNextAgentRequest):
    user_id: UUID
    agent_id: str = Field(min_length=1, max_length=160)
    agent_type: str = Field(default="unknown", min_length=1, max_length=80)
    agent_run_id: str | None = Field(default=None, min_length=1, max_length=160)
    task_id: str | None = Field(default=None, min_length=1, max_length=160)
    project_scope: list[str] = Field(default_factory=list)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=500_000)
    output_type: str = Field(default="general", min_length=1, max_length=80)
    domain: VNextDomain = "project"
    sensitivity: VNextSensitivity = "private"
    source_refs: list[object] = Field(default_factory=list)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    propose_memory: bool = False


class VNextArtifactInsightFeedbackRequest(VNextAgentRequest):
    user_id: UUID
    useful_insight: str = Field(min_length=1, max_length=20)
    surfaced_missed: str | None = Field(default=None, min_length=1, max_length=20)
    comments: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextContextPackRequest(VNextAgentRequest):
    user_id: UUID
    query: str = Field(min_length=1, max_length=4000)
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextBrainArtifactGenerateRequest(VNextAgentRequest):
    user_id: UUID
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextConnectionReportGenerateRequest(VNextAgentRequest):
    user_id: UUID
    query: str = Field(default="", max_length=4000)
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextContradictionReportGenerateRequest(VNextAgentRequest):
    user_id: UUID
    query: str = Field(default="", max_length=4000)
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextProjectAutomationRequest(VNextAgentRequest):
    user_id: UUID
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextProjectCreateRequest(VNextAgentRequest):
    user_id: UUID
    name: str = Field(min_length=1, max_length=280)
    slug: str | None = Field(default=None, min_length=1, max_length=280)
    status: str = Field(default="active", min_length=1, max_length=40)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    current_state: str | None = Field(default=None, min_length=1, max_length=4000)
    domain: VNextDomain = "project"
    sensitivity: VNextSensitivity = "private"


class VNextProjectUpdateReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    edited_current_state: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextOpenLoopReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    due_at: str | None = Field(default=None, min_length=1, max_length=120)
    priority: str | None = Field(default=None, min_length=1, max_length=80)
    resolution_note: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextOpenLoopCreateRequest(VNextAgentRequest):
    user_id: UUID
    title: str = Field(min_length=1, max_length=280)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    due_at: str | None = Field(default=None, min_length=1, max_length=120)
    priority: str = Field(default="normal", min_length=1, max_length=80)
    memory_id: str | None = Field(default=None, min_length=1, max_length=120)
    project_id: str | None = Field(default=None, min_length=1, max_length=120)
    source_id: str | None = Field(default=None, min_length=1, max_length=120)
    domain: VNextDomain = "unknown"
    sensitivity: VNextSensitivity = "unknown"


class VNextMemoryReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    canonical_text: str | None = Field(default=None, min_length=1, max_length=4000)
    summary: str | None = Field(default=None, min_length=1, max_length=4000)
    domain: VNextDomain | None = None
    sensitivity: VNextSensitivity | None = None
    project_id: str | None = Field(default=None, min_length=1, max_length=120)
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextQueueTaskCreateRequest(VNextAgentRequest):
    user_id: UUID
    title: str = Field(min_length=1, max_length=280)
    task_type: str = Field(min_length=1, max_length=80)
    instructions: str = Field(min_length=1, max_length=20_000)
    domain: VNextDomain = "unknown"
    sensitivity: VNextSensitivity = "unknown"
    write_policy: str = Field(default="proposal_only", min_length=1, max_length=80)
    scope_json: dict[str, object] = Field(default_factory=dict)
    allowed_sources_json: list[object] = Field(default_factory=list)


class VNextQueueProcessNextRequest(VNextAgentRequest):
    user_id: UUID


class VNextArtifactReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)


class VNextArtifactQualityRatingRequest(VNextAgentRequest):
    user_id: UUID
    reviewer_id: str | None = Field(default=None, min_length=1, max_length=120)
    usefulness: int | None = Field(default=None, ge=1, le=5)
    accuracy: int | None = Field(default=None, ge=1, le=5)
    source_grounding: int | None = Field(default=None, ge=1, le=5)
    novel_connections: int | None = Field(default=None, ge=1, le=5)
    actionability: int | None = Field(default=None, ge=1, le=5)
    hallucination_risk: int | None = Field(default=None, ge=1, le=5)
    verbosity: str = Field(default="unknown", min_length=1, max_length=40)
    missed_context: str | None = Field(default=None, min_length=1, max_length=4000)
    comments: str | None = Field(default=None, min_length=1, max_length=4000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class VNextGraphEdgeReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)


class VNextBeliefReviewRequest(VNextAgentRequest):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    superseded_by: str | None = Field(default=None, min_length=1, max_length=120)


class VNextArtifactExportRequest(VNextAgentRequest):
    user_id: UUID
    output_dir: str = Field(min_length=1, max_length=1000)


class VNextBrainCharterUpsertRequest(VNextAgentRequest):
    user_id: UUID
    content_markdown: str = Field(min_length=1, max_length=200_000)
    owner_json: dict[str, object] = Field(default_factory=dict)
    memory_philosophy_json: dict[str, object] = Field(default_factory=dict)
    life_domains_json: dict[str, object] = Field(default_factory=dict)
    active_projects_json: list[object] = Field(default_factory=list)
    communication_style_json: dict[str, object] = Field(default_factory=dict)
    priorities_json: dict[str, object] = Field(default_factory=dict)
    autonomous_rules_json: list[object] = Field(default_factory=list)
    quality_standard_json: list[object] = Field(default_factory=list)
    sensitivity: VNextSensitivity = "private"


class VNextMemoryProposalRequest(VNextAgentRequest):
    user_id: UUID
    proposal_type: str = Field(default="candidate_memory", min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=280)
    canonical_text: str = Field(min_length=1, max_length=20_000)
    source_refs: list[object] = Field(default_factory=list)
    domain: VNextDomain = "unknown"
    sensitivity: VNextSensitivity = "unknown"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    review_required: bool = True


class VNextMemoryCommitRequest(VNextAgentRequest):
    user_id: UUID
    intent: str = Field(default="explicit_remember", min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=280)
    canonical_text: str = Field(min_length=1, max_length=20_000)
    memory_type: str = Field(default="semantic", min_length=1, max_length=80)
    domain: VNextDomain = "unknown"
    sensitivity: VNextSensitivity = "unknown"
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    source_type: str = Field(default="direct_user_instruction", min_length=1, max_length=120)
    source_refs: list[object] = Field(default_factory=list)
    conversation_excerpt: str | None = Field(default=None, min_length=1, max_length=4000)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)
    contradiction_refs: list[str] = Field(default_factory=list)


class VNextMemoryConfirmRequest(VNextAgentRequest):
    user_id: UUID
    confirmation_id: str = Field(min_length=1, max_length=160)
    action: str = Field(default="confirm", min_length=1, max_length=40)
    canonical_text: str | None = Field(default=None, min_length=1, max_length=20_000)
    rationale: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextMemoryUndoRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextMemoryCorrectRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    canonical_text: str = Field(min_length=1, max_length=20_000)
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextMemoryForgetRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    reason: str | None = Field(default=None, min_length=1, max_length=4000)


class VNextMemoryExpireRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    valid_to: str | None = Field(default=None, min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=4000)


class VNextMemoryUnexpireRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    reason: str = Field(min_length=1, max_length=4000)


class VNextMemoryAcceptConsolidationRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    reason: str = Field(min_length=1, max_length=4000)


class VNextMemoryRedactRequest(VNextAgentRequest):
    user_id: UUID
    memory_id: UUID
    reason: str = Field(min_length=1, max_length=4000)


class VNextSchedulerWorkflowPatchRequest(VNextAgentRequest):
    user_id: UUID
    enabled: bool | None = None
    paused: bool | None = None
    schedule_json: dict[str, object] | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=120)
    model_options: dict[str, object] = Field(default_factory=dict)


class VNextSchedulerRunNowRequest(VNextAgentRequest):
    user_id: UUID
    scope: dict[str, object] = Field(default_factory=dict)
    options: dict[str, object] = Field(default_factory=dict)


class VNextSchedulerRunDueRequest(VNextAgentRequest):
    user_id: UUID
    limit: int = Field(default=10, ge=1, le=50)


class VNextSchedulerControlRequest(VNextAgentRequest):
    user_id: UUID


class VNextDoctorRunRequest(BaseModel):
    user_id: UUID
    fix_safe: bool = False
    ci: bool = True


def _vnext_public_error_response(*, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def _vnext_terminal_review_metadata(
    existing_metadata: dict[str, object],
    *,
    outcome: Literal["confirmed", "rejected"],
    terminal_at: str,
) -> dict[str, object]:
    """Close nested review/confirmation state with the outer row decision."""
    metadata: dict[str, object] = {**existing_metadata, "review_required": False}
    agentic_raw = metadata.get("agentic_memory")
    if not isinstance(agentic_raw, dict):
        return metadata

    agentic: dict[str, object] = {**agentic_raw}
    confirmation_raw = agentic.get("confirmation")
    if isinstance(confirmation_raw, dict) and confirmation_raw.get("status") == "pending":
        timestamp_key = "confirmed_at" if outcome == "confirmed" else "rejected_at"
        agentic["confirmation"] = {
            **confirmation_raw,
            "status": outcome,
            timestamp_key: terminal_at,
        }

    if outcome == "confirmed":
        agentic.update(
            {
                "status": "committed",
                "write_mode": "commit",
                "lifecycle_status": "dashboard_review_accepted",
                "confirmed_at": terminal_at,
                "requires_dashboard_review": False,
            }
        )
    else:
        agentic.update(
            {
                "status": "rejected",
                "lifecycle_status": "review_rejected",
                "requires_dashboard_review": False,
            }
        )
    metadata["agentic_memory"] = agentic
    return metadata


def _vnext_string_list(mapping: dict[str, object], key: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped,) if stripped else ()
    if not isinstance(value, list):
        return ()
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        stripped = item.strip()
        if stripped:
            output.append(stripped)
    return tuple(output)


def _vnext_bool(mapping: dict[str, object], key: str, default: bool) -> bool:
    value = mapping.get(key)
    return value if isinstance(value, bool) else default


def _vnext_optional_bool(mapping: dict[str, object], key: str) -> bool | None:
    """Tri-state option: absent (or non-boolean) means "caller did not say".

    Retrieval flags such as ``include_sources`` treat None as "let the
    context_depth tier decide", so absence must stay distinguishable from an
    explicit false.
    """
    value = mapping.get(key)
    return value if isinstance(value, bool) else None


def _vnext_text_option(mapping: dict[str, object], key: str) -> str | None:
    value = mapping.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _vnext_int(mapping: dict[str, object], key: str, default: int) -> int:
    value = mapping.get(key)
    return value if isinstance(value, int) else default


def _vnext_float(mapping: dict[str, object], key: str) -> float | None:
    value = mapping.get(key)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


class _VNextModelGenerationOptions(TypedDict):
    generation_mode: str
    model_route_mode: str | None
    model_provider: str | None
    model: str | None
    model_temperature: float
    allow_cloud_private: bool


def _vnext_model_generation_options(options: dict[str, object]) -> _VNextModelGenerationOptions:
    generation_mode = options.get("generation_mode")
    route_mode = options.get("model_route_mode")
    provider = options.get("model_provider")
    model = options.get("model")
    temperature = _vnext_float(options, "model_temperature")
    if temperature is None or temperature < 0.0 or temperature > 2.0:
        temperature = 0.2
    return {
        "generation_mode": generation_mode if generation_mode in {"deterministic", "model_backed"} else "deterministic",
        "model_route_mode": route_mode
        if route_mode in {"local_only", "cloud_allowed", "cloud_requires_approval", "model_disabled"}
        else None,
        "model_provider": provider if isinstance(provider, str) else None,
        "model": model if isinstance(model, str) else None,
        "model_temperature": temperature,
        "allow_cloud_private": _vnext_bool(options, "allow_cloud_private", False),
    }


def _vnext_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "project"


def _vnext_status_counts(rows: list[dict[str, object]], *, field: str = "status") -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get(field, "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _vnext_metadata(row: dict[str, object] | None) -> dict[str, object]:
    if row is None:
        return {}
    value = row.get("metadata_json")
    return value if isinstance(value, dict) else {}


def _vnext_payload(row: dict[str, object]) -> dict[str, object]:
    value = row.get("payload_json")
    return value if isinstance(value, dict) else {}


def _vnext_ref_values(value: object) -> list[str]:
    refs: list[str] = []
    if isinstance(value, str):
        if value.strip():
            refs.append(value.strip())
    elif isinstance(value, dict):
        for key in ("source_id", "id", "ref", "source_ref"):
            candidate = value.get(key)
            if isinstance(candidate, (str, int)):
                refs.append(str(candidate))
        for nested_key in ("source_ids", "source_refs", "sources"):
            refs.extend(_vnext_ref_values(value.get(nested_key)))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_vnext_ref_values(item))
    return refs


def _vnext_ref_matches_source(value: object, source_id: str) -> bool:
    normalized = str(source_id)
    return any(ref == normalized or ref == f"source:{normalized}" for ref in _vnext_ref_values(value))


def _vnext_row_references_source(row: dict[str, object], source_id: str) -> bool:
    if str(row.get("source_id") or "") == str(source_id):
        return True
    metadata = _vnext_metadata(row)
    for key in ("source_id", "source_ids", "source_ref", "source_refs", "source_references", "selected_source_ids"):
        if _vnext_ref_matches_source(metadata.get(key), source_id):
            return True
    return _vnext_ref_matches_source(row.get("source_event_ids"), source_id)


def _vnext_event_references(
    event: dict[str, object],
    *,
    source_id: str,
    memory_ids: set[str],
    artifact_ids: set[str],
    open_loop_ids: set[str],
) -> bool:
    target_type = str(event.get("target_type") or "")
    target_id = str(event.get("target_id") or "")
    if target_type == "source" and target_id == source_id:
        return True
    if target_type == "memory" and target_id in memory_ids:
        return True
    if target_type == "artifact" and target_id in artifact_ids:
        return True
    if target_type == "open_loop" and target_id in open_loop_ids:
        return True
    payload = _vnext_payload(event)
    return any(
        _vnext_ref_matches_source(payload.get(key), source_id)
        for key in ("source_id", "source_ids", "source_ref", "source_refs", "source_references", "selected_source_ids")
    )


_VNEXT_SOURCE_TRACE_COLLECTION_LIMIT = 500


def _vnext_bounded_trace_rows(
    rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], bool]:
    limit = _VNEXT_SOURCE_TRACE_COLLECTION_LIMIT
    return rows[:limit], len(rows) <= limit


def _vnext_source_chunks(
    store: PostgresVNextStore,
    source_id: str,
) -> tuple[list[dict[str, object]], bool]:
    if not hasattr(store, "list_source_chunks"):
        return [], True
    rows = list(
        store.list_source_chunks(
            source_id,
            limit=_VNEXT_SOURCE_TRACE_COLLECTION_LIMIT + 1,
        )
    )
    return _vnext_bounded_trace_rows(rows)


def _vnext_source_trace(
    *,
    store: PostgresVNextStore,
    source: dict[str, object],
    memories: list[dict[str, object]],
    artifacts: list[dict[str, object]],
    open_loops: list[dict[str, object]],
    events: list[dict[str, object]],
    memory_scope: str = "complete",
    collection_completeness: dict[str, bool] | None = None,
) -> dict[str, object]:
    source_id = str(source["id"])
    related_memories = [memory for memory in memories if _vnext_row_references_source(memory, source_id)]
    related_artifacts = [artifact for artifact in artifacts if _vnext_row_references_source(artifact, source_id)]
    related_open_loops = [loop for loop in open_loops if _vnext_row_references_source(loop, source_id)]
    memory_ids = {str(memory["id"]) for memory in related_memories}
    artifact_ids = {str(artifact["id"]) for artifact in related_artifacts}
    open_loop_ids = {str(loop["id"]) for loop in related_open_loops}
    related_events = [
        event
        for event in events
        if _vnext_event_references(
            event,
            source_id=source_id,
            memory_ids=memory_ids,
            artifact_ids=artifact_ids,
            open_loop_ids=open_loop_ids,
        )
    ]
    trace_id = next((str(event.get("trace_id")) for event in related_events if event.get("trace_id")), None)
    chunks, chunks_complete = _vnext_source_chunks(store, source_id)
    default_complete = memory_scope == "complete"
    completeness = {
        "chunks": chunks_complete,
        "candidate_memories": default_complete,
        "artifacts": default_complete,
        "open_loops": default_complete,
        "events": default_complete,
    }
    if collection_completeness is not None:
        completeness.update(collection_completeness)
        completeness["chunks"] = chunks_complete
    truncated_collections = [
        collection_name for collection_name, is_complete in completeness.items() if not is_complete
    ]
    return {
        "trace_id": trace_id or f"source:{source_id}",
        "trace_kind": "capture_to_brief",
        "source": source,
        "chunks": chunks,
        "candidate_memories": related_memories,
        "artifacts": related_artifacts,
        "open_loops": related_open_loops,
        "events": related_events,
        "sampling": {
            "memory_scope": memory_scope,
            "collection_limit": _VNEXT_SOURCE_TRACE_COLLECTION_LIMIT,
            "collection_complete": completeness,
            "truncated_collections": truncated_collections,
            "trace_complete": len(truncated_collections) == 0,
            "memory_history_complete": completeness["candidate_memories"],
        },
        "summary": {
            "source_id": source_id,
            "chunk_count": len(chunks),
            "candidate_memory_count": len(related_memories),
            "artifact_count": len(related_artifacts),
            "open_loop_count": len(related_open_loops),
            "event_count": len(related_events),
        },
    }


def _vnext_load_source_trace(
    *,
    store: PostgresVNextStore,
    source: dict[str, object],
) -> dict[str, object]:
    """Load one bounded source trace and disclose per-collection truncation."""

    source_id = str(source["id"])
    memories, memories_complete = _vnext_bounded_trace_rows(
        store.list_memories_referencing_source(
            source_id=source_id,
            limit=_VNEXT_SOURCE_TRACE_COLLECTION_LIMIT + 1,
        )
    )
    artifacts, artifacts_complete = _vnext_bounded_trace_rows(
        store.list_artifacts_referencing_source(
            source_id=source_id,
            limit=_VNEXT_SOURCE_TRACE_COLLECTION_LIMIT + 1,
        )
    )
    open_loops, open_loops_complete = _vnext_bounded_trace_rows(
        store.list_open_loops_referencing_source(
            source_id=source_id,
            limit=_VNEXT_SOURCE_TRACE_COLLECTION_LIMIT + 1,
        )
    )
    events, direct_events_complete = _vnext_bounded_trace_rows(
        store.list_events_for_source_trace(
            source_id=source_id,
            memory_ids=[str(memory["id"]) for memory in memories],
            artifact_ids=[str(artifact["id"]) for artifact in artifacts],
            open_loop_ids=[str(open_loop["id"]) for open_loop in open_loops],
            limit=_VNEXT_SOURCE_TRACE_COLLECTION_LIMIT + 1,
        )
    )
    events_complete = direct_events_complete and memories_complete and artifacts_complete and open_loops_complete
    return _vnext_source_trace(
        store=store,
        source=source,
        memories=memories,
        artifacts=artifacts,
        open_loops=open_loops,
        events=events,
        collection_completeness={
            "candidate_memories": memories_complete,
            "artifacts": artifacts_complete,
            "open_loops": open_loops_complete,
            "events": events_complete,
        },
    )


def _vnext_artifact_trace(
    *,
    artifact: dict[str, object],
    sources: list[dict[str, object]],
    quality_evals: list[dict[str, object]],
    events: list[dict[str, object]],
) -> dict[str, object]:
    artifact_id = str(artifact["id"])
    metadata = _vnext_metadata(artifact)
    source_refs = _vnext_ref_values(metadata.get("source_refs")) + _vnext_ref_values(metadata.get("source_ids"))
    related_sources = [
        source
        for source in sources
        if str(source.get("id")) in source_refs or f"source:{source.get('id')}" in source_refs
    ]
    related_evals = [rating for rating in quality_evals if str(rating.get("artifact_id")) == artifact_id]
    related_events = [
        event
        for event in events
        if str(event.get("target_type") or "") == "artifact" and str(event.get("target_id") or "") == artifact_id
    ]
    return {
        "trace_id": metadata.get("trace_id") or metadata.get("scheduler_run_id") or f"artifact:{artifact_id}",
        "trace_kind": "artifact_review",
        "artifact": artifact,
        "sources": related_sources,
        "quality_evals": related_evals,
        "events": related_events,
        "summary": {
            "artifact_id": artifact_id,
            "source_count": len(related_sources),
            "quality_eval_count": len(related_evals),
            "event_count": len(related_events),
            "scheduler_run_id": metadata.get("scheduler_run_id"),
            "agent_run_id": metadata.get("agent_run_id"),
        },
    }


def _vnext_agent_identity(request: VNextAgentRequest) -> AgentIdentity | None:
    payload = request.model_dump(mode="json")
    if payload.get("agent_identity") is None and isinstance(payload.get("agent"), dict):
        payload["agent_identity"] = payload["agent"]
    return AgentIdentity.from_payload(payload)


def _vnext_authenticated_agent_identity(
    store: PostgresVNextStore,
    request: VNextAgentRequest,
    *,
    user_id: UUID,
    authorization: str | None,
) -> AgentIdentity | None:
    payload = request.model_dump(mode="json")
    if payload.get("agent_identity") is None and isinstance(payload.get("agent"), dict):
        payload["agent_identity"] = payload["agent"]
    return resolve_protected_agent_identity(
        store,
        user_id=user_id,
        raw_key=agent_key_from_authorization(authorization),
        payload=payload,
    )


def _vnext_agent_auth_error_response(exc: AgentKeyAuthenticationError) -> JSONResponse:
    return _vnext_public_error_response(status_code=exc.status_code, detail=str(exc))


def _vnext_permission_response(decision: PolicyDecision) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=jsonable_encoder(
            {
                "detail": "agent policy blocked this action",
                "policy_decision": decision.to_record(),
            }
        ),
    )


_VNEXT_ROUTE_LOCAL_POLICY = frozenset(
    {
        ("POST", "/v0/vnext/sources"),
        ("POST", "/v0/vnext/agents/ingest-output"),
        ("POST", "/v0/vnext/artifacts/{artifact_id}/insight-feedback"),
        ("GET", "/v0/vnext/artifacts/{artifact_id}"),
        ("GET", "/v0/vnext/traces/artifacts/{artifact_id}"),
        ("POST", "/v0/vnext/artifacts/{artifact_id}/export"),
        ("POST", "/v0/vnext/context-packs"),
        ("POST", "/v0/vnext/memories/{memory_id}/review"),
        ("POST", "/v0/vnext/memory-proposals"),
        ("POST", "/v0/vnext/memories/commit"),
        ("POST", "/v0/vnext/memories/confirm"),
        ("POST", "/v0/vnext/memories/undo"),
        ("POST", "/v0/vnext/memories/correct"),
        ("POST", "/v0/vnext/memories/forget"),
        ("POST", "/v0/vnext/memories/expire"),
        ("POST", "/v0/vnext/memories/unexpire"),
        ("POST", "/v0/vnext/memories/accept-consolidation"),
        ("POST", "/v0/vnext/memories/redact"),
        ("POST", "/v0/vnext/artifacts/generate/daily-brief"),
        ("POST", "/v0/vnext/artifacts/generate/weekly-synthesis"),
        ("POST", "/v0/vnext/artifacts/generate/connections"),
        ("POST", "/v0/vnext/artifacts/generate/contradictions"),
        ("POST", "/v0/vnext/queue/tasks"),
        ("POST", "/v0/vnext/artifacts/{artifact_id}/review"),
        ("POST", "/v0/vnext/artifacts/{artifact_id}/quality-ratings"),
        ("POST", "/v0/vnext/projects/update-candidates"),
        ("POST", "/v0/vnext/open-loops"),
        ("PATCH", "/v0/vnext/scheduler/workflows/{workflow_type}"),
        ("POST", "/v0/vnext/scheduler/workflows/{workflow_type}/run-now"),
        ("POST", "/v0/vnext/scheduler/run-due"),
        ("POST", "/v0/vnext/scheduler/pause"),
        ("POST", "/v0/vnext/scheduler/resume"),
        ("POST", "/v0/vnext/open-loops/{loop_id}/review"),
    }
)

# Routes without a target/scope-specific policy are the operator-console
# surface.  Keep this inventory explicit: adding a route without classifying
# it must fail closed at runtime and fail the route-inventory regression.
_VNEXT_CENTRAL_OPERATOR_ROUTES = frozenset(
    {
        ("DELETE", "/v0/vnext/sources/{source_id}"),
        ("GET", "/v0/vnext/agents/policy-telemetry"),
        ("GET", "/v0/vnext/artifacts"),
        ("GET", "/v0/vnext/beliefs/{belief_id}/state"),
        ("GET", "/v0/vnext/connectors"),
        ("GET", "/v0/vnext/connectors/health"),
        ("GET", "/v0/vnext/connectors/{connector_name}/status"),
        ("GET", "/v0/vnext/context-tree"),
        ("GET", "/v0/vnext/doctor"),
        ("GET", "/v0/vnext/dogfooding"),
        ("GET", "/v0/vnext/graph/neighborhood/{target_id}"),
        ("GET", "/v0/vnext/memories/recent-commits"),
        ("GET", "/v0/vnext/memories/{memory_id}/audit"),
        ("GET", "/v0/vnext/projects"),
        ("GET", "/v0/vnext/projects/{project_id}/dashboard"),
        ("GET", "/v0/vnext/quality-evals"),
        ("GET", "/v0/vnext/scheduler/failures"),
        ("GET", "/v0/vnext/scheduler/runs"),
        ("GET", "/v0/vnext/scheduler/status"),
        ("GET", "/v0/vnext/settings/brain-charter"),
        ("GET", "/v0/vnext/sources/{source_id}"),
        ("GET", "/v0/vnext/traces/sources/{source_id}"),
        ("GET", "/v0/vnext/workspace"),
        ("PATCH", "/v0/vnext/connectors/{connector_name}/config"),
        ("POST", "/v0/vnext/beliefs/{belief_id}/review"),
        ("POST", "/v0/vnext/connectors/browser-clipper/capture"),
        ("POST", "/v0/vnext/connectors/local-folder/sync"),
        ("POST", "/v0/vnext/connectors/telegram/sync"),
        ("POST", "/v0/vnext/connectors/{connector_name}/sync"),
        ("POST", "/v0/vnext/doctor/run"),
        ("POST", "/v0/vnext/graph/edges/{edge_id}/review"),
        ("POST", "/v0/vnext/open-loops/extract"),
        ("POST", "/v0/vnext/projects"),
        ("POST", "/v0/vnext/projects/update-candidates/{artifact_id}/review"),
        ("POST", "/v0/vnext/queue/process-next"),
        ("POST", "/v0/vnext/sources/{source_id}/review"),
        ("PUT", "/v0/vnext/settings/brain-charter"),
    }
)


def _matched_vnext_route_path(request: Request) -> str:
    for route in app.router.routes:
        match, _child_scope = route.matches(request.scope)
        if match is Match.FULL:
            return str(getattr(route, "path", request.url.path))
    return request.url.path


def _vnext_central_route_policy(
    *,
    identity: AgentIdentity | None,
    method: str,
    route_path: str,
) -> PolicyDecision | None:
    """Authorize one classified local-policy or central-operator route."""

    route_key = (method.upper(), route_path)
    if route_key in _VNEXT_ROUTE_LOCAL_POLICY:
        return None
    if route_key not in _VNEXT_CENTRAL_OPERATOR_ROUTES:
        return PolicyDecision(
            decision="blocked",
            action="http.route.unclassified",
            permission_profile=(identity.permission_profile if identity is not None else "user_or_system"),
            reasons=("vnext_route_not_classified",),
        )
    if identity is None:
        # Zero-key local installs retain their explicit human/operator path.
        return None
    return evaluate_agent_policy(identity=identity, action="http.operator.access")


def _resolve_vnext_http_auth(
    *,
    settings: Settings,
    user_id: UUID,
    raw_key: str | None,
    payload: dict[str, object],
    method: str,
    route_path: str,
) -> tuple[AgentIdentity | None, PolicyDecision | None]:
    """Run protected-route database authentication off the event-loop thread."""

    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        identity = resolve_protected_agent_identity(
            store,
            user_id=user_id,
            raw_key=raw_key,
            payload=payload,
        )
        route_decision = _vnext_central_route_policy(
            identity=identity,
            method=method,
            route_path=route_path,
        )
        if route_decision is not None and route_decision.decision == "blocked":
            append_policy_events(
                store,
                identity=identity,
                decision=route_decision,
                target_type="http_route",
                target_id=route_path,
            )
    return identity, route_decision


async def _vnext_protected_http_auth(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Authenticate the complete protected ``/v0/vnext`` route surface."""

    if not request.url.path.startswith("/v0/vnext"):
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)

    payload: dict[str, object] = {}
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        try:
            candidate = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError):
            candidate = None
        if isinstance(candidate, dict):
            payload = candidate

    query_user_id = request.query_params.get("user_id")
    body_user_id = payload.get("user_id")
    if query_user_id is not None and body_user_id is not None and str(body_user_id) != query_user_id:
        return _vnext_public_error_response(
            status_code=400,
            detail="vNext user_id values do not match",
        )
    raw_user_id = body_user_id if body_user_id is not None else query_user_id
    if raw_user_id is None:
        return _vnext_public_error_response(
            status_code=400,
            detail="protected vNext requests require user_id",
        )
    try:
        user_id = UUID(str(raw_user_id))
    except ValueError:
        return _vnext_public_error_response(status_code=400, detail="vNext user_id is invalid")

    try:
        settings = get_settings()
        route_path = _matched_vnext_route_path(request)
        identity, route_decision = await run_in_threadpool(
            _resolve_vnext_http_auth,
            settings=settings,
            user_id=user_id,
            raw_key=agent_key_from_authorization(request.headers.get("authorization")),
            payload=payload,
            method=request.method,
            route_path=route_path,
        )
        if route_decision is not None and route_decision.decision == "blocked":
            return _vnext_permission_response(route_decision)
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    request.state.vnext_agent_identity = identity
    return await call_next(request)


app.middleware("http")(_vnext_protected_http_auth)


def _vnext_agent_actor(identity: AgentIdentity | None, *, fallback: str = "user") -> tuple[str, str | None]:
    if identity is None:
        return fallback, None
    return identity.actor_type, identity.agent_id


def _vnext_agent_record(store: PostgresVNextStore, identity: AgentIdentity | None) -> None:
    if identity is None:
        return
    store.upsert_agent_identity(
        {
            "agent_id": identity.agent_id,
            "agent_type": identity.agent_type,
            "permission_profile": identity.permission_profile,
            "project_scope_json": list(identity.project_scope),
            "metadata_json": {
                "last_agent_run_id": identity.agent_run_id,
                "last_task_id": identity.task_id,
            },
        },
        actor_type="agent",
    )


def _vnext_policy_checked(
    *,
    store: PostgresVNextStore,
    identity: AgentIdentity | None,
    action: str,
    domains: tuple[str, ...] = (),
    sensitivity_allowed: tuple[str, ...] = ("public", "internal", "private", "unknown"),
    project_scope: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    require_explicit_project_scope: bool = False,
) -> PolicyDecision:
    _vnext_agent_record(store, identity)
    decision = evaluate_agent_policy(
        identity=identity,
        action=action,
        domains=domains,
        sensitivity_allowed=sensitivity_allowed,
        project_scope=project_scope,
        workflow_type=workflow_type,
        write_policy=write_policy,
        require_explicit_project_scope=require_explicit_project_scope,
    )
    append_policy_events(store, identity=identity, decision=decision, target_type=target_type, target_id=target_id)
    return decision


def _vnext_exact_resource_policy(
    *,
    identity: AgentIdentity | None,
    action: str,
    resource: dict[str, object],
    source_resource: bool = False,
) -> PolicyDecision:
    domain = " ".join(str(resource.get("domain") or "unknown").split()).strip() or "unknown"
    sensitivity = " ".join(str(resource.get("sensitivity") or "unknown").split()).strip() or "unknown"
    decision = evaluate_agent_policy(
        identity=identity,
        action=action,
        domains=(domain,),
        sensitivity_allowed=(sensitivity,),
        project_scope=source_project_scope(resource) if source_resource else resource_project_scope(resource),
        require_explicit_project_scope=bool(identity is not None and identity.project_scope_locked),
    )
    if decision.decision == "allowed_with_filtering":
        decision = replace(
            decision,
            decision="blocked",
            reasons=tuple(dict.fromkeys((*decision.reasons, "exact_target_filtering_not_permitted"))),
        )
    return decision


def _vnext_authorized_artifact(
    *,
    store: PostgresVNextStore,
    identity: AgentIdentity | None,
    artifact_id: str,
    action: str,
    for_update: bool,
) -> tuple[dict[str, object], PolicyDecision]:
    """Load and authorize a persisted artifact before any content is returned.

    Side-effecting handlers lock the target first so the project/domain/
    sensitivity attributes used for authorization remain stable through the
    mutation.  A single artifact cannot be partially filtered: if policy
    removes its domain or sensitivity, access is denied rather than returning
    the unfiltered row.
    """

    artifact = store.get_artifact_for_update(artifact_id) if for_update else store.get_artifact(artifact_id)
    if artifact is None:
        raise VNextQueueNotFoundError(f"artifact {artifact_id} was not found")

    _vnext_agent_record(store, identity)
    decision = _vnext_exact_resource_policy(
        identity=identity,
        action=action,
        resource=artifact,
    )
    append_policy_events(
        store,
        identity=identity,
        decision=decision,
        target_type="artifact",
        target_id=artifact_id,
    )
    if decision.decision == "blocked":
        raise AgentPolicyBlockedError(decision)
    return artifact, decision


def _vnext_workspace_payload(store: PostgresVNextStore) -> dict[str, object]:
    sensitivity_allowed = ["public", "internal", "private", "unknown"]
    review_statuses = ["candidate", "needs_review", "private_only", "accepted", "rejected"]
    sources = store.list_sources(sensitivity_allowed=sensitivity_allowed, limit=20)
    source_count = store.count_sources()
    list_memories_by_statuses = getattr(store, "list_memories_by_statuses", None)
    if callable(list_memories_by_statuses):
        review_memories = list_memories_by_statuses(
            statuses=review_statuses,
            sensitivity_allowed=sensitivity_allowed,
            limit=30,
        )
    else:  # Compatibility for external/test stores implementing the older protocol.
        review_memories = [
            memory for memory in store.list_memories(status=None) if str(memory.get("status")) in set(review_statuses)
        ][:30]
    count_memories_by_status = getattr(store, "count_memories_by_status", None)
    memory_status_counts = (
        count_memories_by_status(sensitivity_allowed=sensitivity_allowed)
        if callable(count_memories_by_status)
        else _vnext_status_counts(review_memories)
    )
    review_memory_total = sum(memory_status_counts.get(status, 0) for status in review_statuses)
    artifacts = store.list_artifacts(sensitivity_allowed=sensitivity_allowed, limit=30)
    artifact_count = store.count_artifacts()
    artifact_status_counts = store.count_artifacts_by_status()
    quality_evals = store.list_artifact_quality_ratings(limit=50)
    quality_eval_count = store.count_artifact_quality_ratings()
    projects = store.list_projects(status=None, sensitivity_allowed=sensitivity_allowed, limit=20)
    project_count = store.count_projects()
    open_loops = store.list_open_loops(status=None, sensitivity_allowed=sensitivity_allowed, limit=30)
    open_loop_count = store.count_open_loops(status="open")
    open_loop_status_counts = store.count_open_loops_by_status()
    people = store.list_people(sensitivity_allowed=sensitivity_allowed, limit=12)
    beliefs = store.list_beliefs(status=None, sensitivity_allowed=sensitivity_allowed, limit=12)
    tasks = store.list_tasks(status=None, limit=12)
    recent_events = store.list_events(limit=20)
    count_events = getattr(store, "count_events", None)
    event_count = count_events() if callable(count_events) else len(recent_events)
    agent_identities = store.list_agent_identities(limit=20)
    agent_count = store.count_agent_identities()
    agent_events = store.list_agent_events(limit=50)
    list_recent_agentic_commits = getattr(store, "list_recent_agentic_commits", None)
    list_pending_inline_confirmations = getattr(store, "list_pending_inline_confirmations", None)
    memory_commit_service = VNextMemoryCommitService(store)
    recent_memory_commits = (
        list_recent_agentic_commits(limit=20)
        if callable(list_recent_agentic_commits)
        else memory_commit_service.recent_commits(limit=20)["recent_commits"]
    )
    inline_confirmations = (
        list_pending_inline_confirmations(limit=20)
        if callable(list_pending_inline_confirmations)
        else memory_commit_service.inline_confirmations(limit=20)
    )
    scheduler_status = VNextSchedulerService(store).status()
    scheduler_status = {**scheduler_status, "daemon": daemon_status()}
    connector_health = VNextConnectorService(store).connector_health_all()
    dogfooding = VNextDogfoodingService(store).dashboard()
    doctor = VNextDoctorService(store).run(ci=True)
    policy_telemetry = summarize_agent_policy_telemetry(
        agent_events=agent_events,
        artifacts=artifacts,
        memories=review_memories,
    )
    project_service = VNextProjectService(store)
    project_dashboards: list[dict[str, object]] = []
    for project in projects[:5]:
        try:
            project_dashboards.append(project_service.project_dashboard(project_id=str(project["id"])))
        except VNextProjectValidationError:
            continue
    trace_items = [
        _vnext_source_trace(
            store=store,
            source=source,
            memories=review_memories,
            artifacts=artifacts,
            open_loops=open_loops,
            events=recent_events,
            memory_scope="bounded_workspace_review_sample",
        )
        for source in sources[:8]
    ]
    return {
        "mode": "live",
        "summary": {
            "source_count": source_count,
            "candidate_memory_count": memory_status_counts.get("candidate", 0),
            "review_memory_count": review_memory_total,
            "artifact_count": artifact_count,
            "open_loop_count": open_loop_count,
            "project_count": project_count,
            "event_count": event_count,
            "agent_count": agent_count,
            "scheduler_enabled_count": _vnext_int(scheduler_status, "enabled_count", 0),
            "memory_status_counts": memory_status_counts,
            "artifact_status_counts": artifact_status_counts,
            "quality_eval_count": quality_eval_count,
            "open_loop_status_counts": open_loop_status_counts,
        },
        "sources": sources,
        "review_memories": review_memories,
        "samples": {
            "sources": {
                "returned_count": len(sources),
                "total_count": source_count,
                "limit": 20,
                "has_more": source_count > len(sources),
            },
            "review_memories": {
                "returned_count": len(review_memories),
                "total_count": review_memory_total,
                "limit": 30,
                "has_more": review_memory_total > len(review_memories),
            },
            "recent_events": {
                "returned_count": len(recent_events),
                "total_count": event_count,
                "limit": 20,
                "has_more": event_count > len(recent_events),
            },
            "artifacts": {
                "returned_count": len(artifacts),
                "total_count": artifact_count,
                "limit": 30,
                "has_more": artifact_count > len(artifacts),
            },
            "quality_evals": {
                "returned_count": len(quality_evals),
                "total_count": quality_eval_count,
                "limit": 50,
                "has_more": quality_eval_count > len(quality_evals),
            },
            "projects": {
                "returned_count": len(projects),
                "total_count": project_count,
                "limit": 20,
                "has_more": project_count > len(projects),
            },
            "open_loops": {
                "returned_count": len(open_loops),
                "total_count": sum(open_loop_status_counts.values()),
                "limit": 30,
                "has_more": sum(open_loop_status_counts.values()) > len(open_loops),
            },
            "agent_identities": {
                "returned_count": len(agent_identities),
                "total_count": agent_count,
                "limit": 20,
                "has_more": agent_count > len(agent_identities),
            },
        },
        "artifacts": artifacts,
        "quality_evals": quality_evals,
        "connector_health": connector_health,
        "dogfooding": dogfooding,
        "doctor": doctor,
        "traceability": {
            "items": trace_items,
            "count": len(trace_items),
            "order": [str(trace.get("trace_id")) for trace in trace_items],
        },
        "projects": projects,
        "project_dashboards": project_dashboards,
        "open_loops": open_loops,
        "people": people,
        "beliefs": beliefs,
        "tasks": tasks,
        "recent_events": recent_events,
        "agent_activity": {
            "agents": agent_identities,
            "recent_events": agent_events,
            "policy_blocks": [
                event
                for event in agent_events
                if event.get("event_type") in {"agent.policy_blocked", "agent.policy_filtered"}
            ],
            "generated_artifacts": [
                artifact
                for artifact in artifacts
                if isinstance((artifact_metadata := artifact.get("metadata_json")), dict)
                and artifact_metadata.get("generated_by") == "agent"
            ],
            "pending_review_items": [
                memory
                for memory in review_memories
                if isinstance((memory_metadata := memory.get("metadata_json")), dict)
                and memory_metadata.get("agent_id") is not None
            ],
            "recent_commits": recent_memory_commits,
            "inline_confirmations": inline_confirmations,
        },
        "policy_telemetry": policy_telemetry,
        "scheduler": scheduler_status,
        "brain_charter": store.get_brain_charter(),
    }


@contextmanager
def _vnext_embedding_store_context(database_url: str, user_id: UUID):
    with user_connection(database_url, user_id) as conn:
        yield PostgresVNextStore(conn)


def _persist_vnext_deferred_embeddings(
    *,
    database_url: str,
    user_id: UUID,
    result: object,
    actor_type: str = "system",
    actor_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Prepare vectors without a connection, then persist in a short transaction."""

    deferred_inputs = getattr(result, "deferred_embedding_inputs", ())
    persist_deferred_memory_embeddings_best_effort(
        deferred_inputs,
        store_context=lambda: _vnext_embedding_store_context(database_url, user_id),
        actor_type=actor_type,
        actor_id=actor_id,
        trace_id=trace_id,
    )


def _vnext_brain_artifact_request(
    request: VNextBrainArtifactGenerateRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> BrainArtifactRequest:
    scope = request.scope
    options = request.options
    generated_for = options.get("generated_for") or scope.get("generated_for")
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return BrainArtifactRequest(
        domains=decision.effective_domains if decision is not None else _vnext_string_list(scope, "domains"),
        projects=decision.effective_project_scope
        if decision is not None
        else tuple(request.project_scope) or _vnext_string_list(scope, "projects"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        generated_for=str(generated_for) if isinstance(generated_for, str) else None,
        source_limit=_vnext_int(options, "source_limit", 8),
        memory_limit=_vnext_int(options, "memory_limit", 8),
        open_loop_limit=_vnext_int(options, "open_loop_limit", 8),
        artifact_limit=_vnext_int(options, "artifact_limit", 4),
        discover_open_loops=_vnext_bool(options, "discover_open_loops", True),
        create_candidate_memories=_vnext_bool(options, "create_candidate_memories", True),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


def _vnext_connection_request(
    request: VNextConnectionReportGenerateRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> ConnectionFinderRequest:
    options = request.options
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return ConnectionFinderRequest(
        query=request.query,
        domains=decision.effective_domains if decision is not None else _vnext_string_list(request.scope, "domains"),
        projects=decision.effective_project_scope
        if decision is not None
        else tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        max_connections=_vnext_int(options, "max_connections", 8),
        auto_accept_threshold=_vnext_float(options, "auto_accept_threshold"),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


def _vnext_contradiction_request(
    request: VNextContradictionReportGenerateRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> ContradictionFinderRequest:
    options = request.options
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return ContradictionFinderRequest(
        query=request.query,
        domains=decision.effective_domains if decision is not None else _vnext_string_list(request.scope, "domains"),
        projects=decision.effective_project_scope
        if decision is not None
        else tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        max_contradictions=_vnext_int(options, "max_contradictions", 8),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


def _vnext_project_automation_request(
    request: VNextProjectAutomationRequest,
    *,
    identity: AgentIdentity | None = None,
    decision: PolicyDecision | None = None,
) -> ProjectAutomationRequest:
    options = request.options
    scope = request.scope
    explicit_project_id = options.get("project_id") or scope.get("project_id")
    canonical_projects = (
        decision.effective_project_scope
        if decision is not None
        else tuple(request.project_scope) or _vnext_string_list(scope, "projects")
    )
    if isinstance(explicit_project_id, str) and explicit_project_id.strip():
        project_id = explicit_project_id.strip()
        if canonical_projects and project_id not in canonical_projects:
            raise ValueError("project_id must be contained in the canonical project_scope")
    elif len(canonical_projects) == 1:
        project_id = canonical_projects[0]
    elif len(canonical_projects) > 1:
        raise ValueError("project automation requires one project_id when project_scope contains multiple projects")
    else:
        project_id = None
    person_id = options.get("person_id") or scope.get("person_id")
    actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
    return ProjectAutomationRequest(
        domains=decision.effective_domains if decision is not None else _vnext_string_list(scope, "domains"),
        sensitivity_allowed=decision.effective_sensitivity_allowed
        if decision is not None
        else _vnext_string_list(options, "sensitivity_allowed") or ("public", "internal", "private", "unknown"),
        project_id=project_id,
        person_id=str(person_id) if isinstance(person_id, str) else None,
        max_items=_vnext_int(options, "max_items", 8),
        generated_by=actor_type,
        actor_id=actor_id,
        trace_id=request.trace_id,
        run_id=identity.agent_run_id if identity is not None else None,
        agent_identity=identity.to_record() if identity is not None else None,
        policy_decision=decision.to_record() if decision is not None else None,
        metadata_json=agent_metadata(identity, decision),
        **_vnext_model_generation_options(options),
    )


class ContinuityCaptureCandidatesRequest(BaseModel):
    user_id: UUID
    user_content: str = Field(default="", max_length=4000)
    assistant_content: str = Field(default="", max_length=4000)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_kind: str = Field(default="sync_turn", min_length=1, max_length=80)


class ContinuityCaptureCommitRequest(BaseModel):
    user_id: UUID
    mode: str = Field(default="assist", min_length=1, max_length=20)
    candidates: list[dict[str, object]] = Field(default_factory=list)
    sync_fingerprint: str | None = Field(default=None, min_length=1, max_length=200)
    source_kind: str = Field(default="sync_turn", min_length=1, max_length=80)


class MemoryOperationGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_content: str = Field(default="", max_length=4000)
    assistant_content: str = Field(default="", max_length=4000)
    mode: str = Field(default="assist", min_length=1, max_length=20)
    sync_fingerprint: str | None = Field(default=None, min_length=1, max_length=200)
    source_kind: str = Field(default="sync_turn", min_length=1, max_length=80)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)
    target_continuity_object_id: UUID | None = None


class MemoryOperationCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[UUID] = Field(default_factory=list)
    sync_fingerprint: str | None = Field(default=None, min_length=1, max_length=200)
    include_review_required: bool = False


class ContinuityBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief_type: str = Field(default="general", min_length=1, max_length=40)
    query: str | None = Field(default=None, min_length=1, max_length=4000)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)
    since: datetime | None = None
    until: datetime | None = None
    max_relevant_facts: int = Field(
        default=DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    )
    max_recent_changes: int = Field(
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops: int = Field(
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )
    max_conflicts: int = Field(
        default=DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    )
    max_timeline_highlights: int = Field(
        default=DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    )
    include_non_promotable_facts: bool = False


class ContinuityCorrectionRequest(BaseModel):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    title: str | None = Field(default=None, min_length=1, max_length=280)
    body: dict[str, object] | None = None
    provenance: dict[str, object] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    replacement_title: str | None = Field(default=None, min_length=1, max_length=280)
    replacement_body: dict[str, object] | None = None
    replacement_provenance: dict[str, object] | None = None
    replacement_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ContradictionDetectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    continuity_object_id: UUID | None = None
    limit: int = Field(default=DEFAULT_CONTINUITY_REVIEW_LIMIT, ge=1, le=MAX_CONTINUITY_REVIEW_LIMIT)


class ContradictionResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=60)
    note: str | None = Field(default=None, min_length=1, max_length=1000)


class ContinuityOpenLoopReviewActionRequest(BaseModel):
    user_id: UUID
    action: str = Field(min_length=1, max_length=40)
    note: str | None = Field(default=None, min_length=1, max_length=500)


class CreateMemoryReviewLabelRequest(BaseModel):
    user_id: UUID
    label: MemoryReviewLabelValue
    note: str | None = Field(default=None, min_length=1, max_length=280)


class CreateOpenLoopRequest(BaseModel):
    user_id: UUID
    memory_id: UUID | None = None
    title: str = Field(min_length=1, max_length=280)
    due_at: datetime | None = None


class UpdateOpenLoopStatusRequest(BaseModel):
    user_id: UUID
    status: str = Field(min_length=1, max_length=100)
    resolution_note: str | None = Field(default=None, min_length=1, max_length=2000)


class CreateEntityRequest(BaseModel):
    user_id: UUID
    entity_type: EntityType
    name: str = Field(min_length=1, max_length=200)
    source_memory_ids: list[UUID] = Field(min_length=1)


class CreateEntityEdgeRequest(BaseModel):
    user_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str = Field(min_length=1, max_length=100)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source_memory_ids: list[UUID] = Field(min_length=1)


class CreateEmbeddingConfigRequest(BaseModel):
    user_id: UUID
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    dimensions: int = Field(ge=1, le=20000)
    status: EmbeddingConfigStatus = "active"
    metadata: dict[str, object] = Field(default_factory=dict)


class UpsertMemoryEmbeddingRequest(BaseModel):
    user_id: UUID
    memory_id: UUID
    embedding_config_id: UUID
    vector: list[float] = Field(min_length=1, max_length=20000)


class UpsertTaskArtifactChunkEmbeddingRequest(BaseModel):
    user_id: UUID
    task_artifact_chunk_id: UUID
    embedding_config_id: UUID
    vector: list[float] = Field(min_length=1, max_length=20000)


class RetrieveSemanticMemoriesRequest(BaseModel):
    user_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    )


class RetrieveSemanticArtifactChunksRequest(BaseModel):
    user_id: UUID
    embedding_config_id: UUID
    query_vector: list[float] = Field(min_length=1, max_length=20000)
    limit: int = Field(
        default=DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
        ge=1,
        le=MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    )


class UpsertConsentRequest(BaseModel):
    user_id: UUID
    consent_key: str = Field(min_length=1, max_length=200)
    status: ConsentStatus
    metadata: dict[str, object] = Field(default_factory=dict)


class CreatePolicyRequest(BaseModel):
    user_id: UUID
    name: str = Field(min_length=1, max_length=200)
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    effect: PolicyEffect
    priority: int = Field(ge=0, le=1000000)
    active: bool = True
    conditions: dict[str, object] = Field(default_factory=dict)
    required_consents: list[str] = Field(default_factory=list)
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)


class EvaluatePolicyRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    attributes: dict[str, object] = Field(default_factory=dict)


class CreateToolRequest(BaseModel):
    user_id: UUID
    tool_key: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    version: str = Field(min_length=1, max_length=100)
    metadata_version: Literal["tool_metadata_v0"] = TOOL_METADATA_VERSION_V0
    active: bool = True
    tags: list[str] = Field(default_factory=list)
    action_hints: list[str] = Field(default_factory=list, min_length=1)
    scope_hints: list[str] = Field(default_factory=list, min_length=1)
    domain_hints: list[str] = Field(default_factory=list)
    risk_hints: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class EvaluateToolAllowlistRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class RouteToolRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class CreateApprovalRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    tool_id: UUID
    task_run_id: UUID | None = None
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class ResolveApprovalRequest(BaseModel):
    user_id: UUID


class ExecuteApprovedProxyRequest(BaseModel):
    user_id: UUID
    task_run_id: UUID | None = None


class ConnectGmailAccountRequest(BaseModel):
    user_id: UUID
    provider_account_id: str = Field(min_length=1, max_length=320)
    email_address: str = Field(min_length=1, max_length=320)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    scope: Literal["https://www.googleapis.com/auth/gmail.readonly"] = "https://www.googleapis.com/auth/gmail.readonly"
    access_token: str = Field(min_length=1, max_length=8000)
    refresh_token: str | None = Field(default=None, min_length=1, max_length=8000)
    client_id: str | None = Field(default=None, min_length=1, max_length=2000)
    client_secret: str | None = Field(default=None, min_length=1, max_length=8000)
    access_token_expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_refresh_bundle(self) -> ConnectGmailAccountRequest:
        refresh_bundle = (
            self.refresh_token,
            self.client_id,
            self.client_secret,
            self.access_token_expires_at,
        )
        if all(value is None for value in refresh_bundle):
            return self
        if any(value is None for value in refresh_bundle):
            raise ValueError(
                "gmail refresh credentials must include refresh_token, client_id, "
                "client_secret, and access_token_expires_at"
            )
        return self


class IngestGmailMessageRequest(BaseModel):
    user_id: UUID
    task_workspace_id: UUID


class ConnectCalendarAccountRequest(BaseModel):
    user_id: UUID
    provider_account_id: str = Field(min_length=1, max_length=320)
    email_address: str = Field(min_length=1, max_length=320)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    scope: Literal["https://www.googleapis.com/auth/calendar.readonly"] = (
        "https://www.googleapis.com/auth/calendar.readonly"
    )
    access_token: str = Field(min_length=1, max_length=8000)


class IngestCalendarEventRequest(BaseModel):
    user_id: UUID
    task_workspace_id: UUID


class CreateTaskWorkspaceRequest(BaseModel):
    user_id: UUID


class RegisterTaskArtifactRequest(BaseModel):
    user_id: UUID
    local_path: str = Field(min_length=1, max_length=4000)
    media_type_hint: str | None = Field(default=None, min_length=1, max_length=200)


class IngestTaskArtifactRequest(BaseModel):
    user_id: UUID


class RetrieveArtifactChunksRequest(BaseModel):
    user_id: UUID
    query: str = Field(min_length=1, max_length=1000)


class TaskStepRequestSnapshot(BaseModel):
    thread_id: UUID
    tool_id: UUID
    action: str = Field(min_length=1, max_length=100)
    scope: str = Field(min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    risk_hint: str | None = Field(default=None, min_length=1, max_length=100)
    attributes: dict[str, object] = Field(default_factory=dict)


class TaskStepOutcomeRequest(BaseModel):
    routing_decision: ToolRoutingDecision
    approval_id: UUID | None = None
    approval_status: ApprovalStatus | None = None
    execution_id: UUID | None = None
    execution_status: ProxyExecutionStatus | None = None
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=500)


class TaskStepLineageRequest(BaseModel):
    parent_step_id: UUID
    source_approval_id: UUID | None = None
    source_execution_id: UUID | None = None


class CreateNextTaskStepRequest(BaseModel):
    user_id: UUID
    kind: TaskStepKind = "governed_request"
    status: TaskStepStatus
    request: TaskStepRequestSnapshot
    outcome: TaskStepOutcomeRequest
    lineage: TaskStepLineageRequest


class TransitionTaskStepRequest(BaseModel):
    user_id: UUID
    status: TaskStepStatus
    outcome: TaskStepOutcomeRequest


def _task_step_request_record(
    request: TaskStepRequestSnapshot,
) -> ToolRoutingRequestRecord:
    return {
        "thread_id": str(request.thread_id),
        "tool_id": str(request.tool_id),
        "action": request.action,
        "scope": request.scope,
        "domain_hint": request.domain_hint,
        "risk_hint": request.risk_hint,
        "attributes": _json_object(request.attributes),
    }


def _task_step_outcome_snapshot(
    outcome: TaskStepOutcomeRequest,
) -> TaskStepOutcomeSnapshot:
    return {
        "routing_decision": outcome.routing_decision,
        "approval_id": str(outcome.approval_id) if outcome.approval_id is not None else None,
        "approval_status": outcome.approval_status,
        "execution_id": str(outcome.execution_id) if outcome.execution_id is not None else None,
        "execution_status": outcome.execution_status,
        "blocked_reason": outcome.blocked_reason,
    }


class CreateTaskRunRequest(BaseModel):
    user_id: UUID
    max_ticks: int = Field(default=1, ge=1, le=1_000_000)
    retry_cap: int | None = Field(default=None, ge=1, le=1_000_000)
    checkpoint: dict[str, object] = Field(default_factory=dict)


class MutateTaskRunRequest(BaseModel):
    user_id: UUID


class CreateExecutionBudgetRequest(BaseModel):
    user_id: UUID
    agent_profile_id: str | None = Field(default=None, min_length=1, max_length=100)
    tool_key: str | None = Field(default=None, min_length=1, max_length=200)
    domain_hint: str | None = Field(default=None, min_length=1, max_length=200)
    max_completed_executions: int = Field(ge=1, le=1000000)
    rolling_window_seconds: int | None = Field(default=None, ge=1)


class DeactivateExecutionBudgetRequest(BaseModel):
    user_id: UUID
    thread_id: UUID


class SupersedeExecutionBudgetRequest(BaseModel):
    user_id: UUID
    thread_id: UUID
    max_completed_executions: int = Field(ge=1, le=1000000)


def _serialize_thread(thread: ThreadRow) -> ThreadRecord:
    agent_profile_id = _thread_agent_profile_id(thread)
    return {
        "id": str(thread["id"]),
        "title": thread["title"],
        "agent_profile_id": agent_profile_id,
        "created_at": thread["created_at"].isoformat(),
        "updated_at": thread["updated_at"].isoformat(),
    }


def _thread_agent_profile_id(thread: ThreadRow) -> str:
    return str(thread.get("agent_profile_id", DEFAULT_AGENT_PROFILE_ID))


def _serialize_thread_session(session: SessionRow) -> ThreadSessionRecord:
    return {
        "id": str(session["id"]),
        "thread_id": str(session["thread_id"]),
        "status": session["status"],
        "started_at": None if session["started_at"] is None else session["started_at"].isoformat(),
        "ended_at": None if session["ended_at"] is None else session["ended_at"].isoformat(),
        "created_at": session["created_at"].isoformat(),
    }


def _serialize_thread_event(event: EventRow) -> ThreadEventRecord:
    return {
        "id": str(event["id"]),
        "thread_id": str(event["thread_id"]),
        "session_id": None if event["session_id"] is None else str(event["session_id"]),
        "sequence_no": event["sequence_no"],
        "kind": event["kind"],
        "payload": event["payload"],
        "created_at": event["created_at"].isoformat(),
    }


def _serialize_model_provider(provider: ModelProviderRow) -> dict[str, object]:
    return {
        "id": str(provider["id"]),
        "workspace_id": str(provider["workspace_id"]),
        "created_by_user_account_id": str(provider["created_by_user_account_id"]),
        "provider_key": provider["provider_key"],
        "model_provider": provider["model_provider"],
        "display_name": provider["display_name"],
        "base_url": redact_url_credentials(provider["base_url"]),
        "auth_mode": provider["auth_mode"],
        "default_model": provider["default_model"],
        "status": provider["status"],
        "model_list_path": provider["model_list_path"],
        "healthcheck_path": provider["healthcheck_path"],
        "invoke_path": provider["invoke_path"],
        "azure_api_version": provider["azure_api_version"],
        "metadata": provider["metadata"],
        "config_revision": provider["config_revision"],
        "created_at": provider["created_at"].isoformat(),
        "updated_at": provider["updated_at"].isoformat(),
    }


def _serialize_provider_capability(capability: ProviderCapabilityRow) -> dict[str, object]:
    snapshot = capability["capability_snapshot"]
    capability_version = snapshot.get("capability_version")
    if not isinstance(capability_version, str) or capability_version == "":
        capability_version = "provider_capability_v1"
    return {
        "provider_id": str(capability["provider_id"]),
        "adapter_key": capability["adapter_key"],
        "discovery_status": capability["discovery_status"],
        "capability_version": capability_version,
        "snapshot": snapshot,
        "discovery_error": capability["discovery_error"],
        "provider_config_revision": capability["provider_config_revision"],
        "discovered_at": capability["discovered_at"].isoformat(),
    }


def _runtime_provider_config_or_none(
    *,
    store: ContinuityStore,
    provider_id: UUID,
    workspace_id: UUID,
    settings: Settings,
) -> RuntimeProviderConfig | None:
    row = store.get_model_provider_for_workspace_optional(
        provider_id=provider_id,
        workspace_id=workspace_id,
    )
    if row is None:
        return None
    validate_provider_base_url(row["base_url"])
    return resolve_runtime_provider_config_secrets(
        config=RuntimeProviderConfig.from_row(_object_dict(row)),
        settings=settings,
    )


def _normalize_provider_path(*, field_name: str, value: str) -> str:
    path = value.strip()
    if path == "":
        raise ValueError(f"{field_name} is required")
    return path if path.startswith("/") else f"/{path}"


def _provider_config_fingerprint(
    *,
    provider_key: str,
    model_provider: str,
    display_name: str,
    base_url: str,
    api_key: str,
    auth_mode: str,
    default_model: str,
    status: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    azure_api_version: str,
    azure_auth_secret_ref: str,
    metadata: JsonObject,
) -> str:
    return provider_config_fingerprint(
        provider_key=provider_key,
        model_provider=model_provider,
        display_name=display_name,
        base_url=base_url,
        api_key=api_key,
        auth_mode=auth_mode,
        default_model=default_model,
        status=status,
        model_list_path=model_list_path,
        healthcheck_path=healthcheck_path,
        invoke_path=invoke_path,
        azure_api_version=azure_api_version,
        azure_auth_secret_ref=azure_auth_secret_ref,
        metadata=metadata,
    )


def _fallback_provider_capability_snapshot(
    *,
    adapter_key: str,
    runtime_provider: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    extra_snapshot_fields: dict[str, str] | None = None,
) -> ProviderCapabilitySnapshot:
    snapshot = normalized_capability_snapshot(
        adapter_key=adapter_key,
        runtime_provider=runtime_provider,
        supports_tool_calls=False,
        supports_reasoning=False,
        supports_streaming=False,
        supports_store=False,
        supports_vision_input=False,
        supports_audio_input=False,
    )
    snapshot["health_status"] = "unreachable"
    snapshot["health_endpoint"] = healthcheck_path
    snapshot["models_endpoint"] = model_list_path
    snapshot["invoke_endpoint"] = invoke_path
    snapshot["model_count"] = 0
    snapshot["models"] = []
    if extra_snapshot_fields:
        azure_api_version = extra_snapshot_fields.get("azure_api_version")
        azure_auth_mode = extra_snapshot_fields.get("azure_auth_mode")
        if azure_api_version is not None:
            snapshot["azure_api_version"] = azure_api_version
        if azure_auth_mode is not None:
            snapshot["azure_auth_mode"] = azure_auth_mode
    return snapshot


@dataclass(frozen=True, slots=True)
class _ProviderDiscoveryOutcome:
    adapter_key: str
    discovery_status: str
    capability_snapshot: JsonObject
    discovery_error: str | None


def _discover_provider_capability(
    *,
    provider: ModelProviderRow,
    settings: Settings,
) -> _ProviderDiscoveryOutcome:
    """Perform provider discovery without holding a database transaction."""

    runtime_provider = resolve_runtime_provider_config_secrets(
        config=RuntimeProviderConfig.from_row(_object_dict(provider)),
        settings=settings,
    )
    adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
    try:
        snapshot = adapter.discover_capabilities(
            config=runtime_provider,
            settings=settings,
        )
    except ModelInvocationError as exc:
        discovery_error = sanitize_provider_error_message(str(exc))
        extra_snapshot_fields = None
        if runtime_provider.provider_key == AZURE_ADAPTER_KEY:
            extra_snapshot_fields = {
                "azure_api_version": runtime_provider.azure_api_version.strip() or DEFAULT_AZURE_API_VERSION,
                "azure_auth_mode": runtime_provider.auth_mode,
            }
        snapshot = _fallback_provider_capability_snapshot(
            adapter_key=adapter.adapter_key,
            runtime_provider=adapter.runtime_provider,
            model_list_path=runtime_provider.model_list_path,
            healthcheck_path=runtime_provider.healthcheck_path,
            invoke_path=runtime_provider.invoke_path,
            extra_snapshot_fields=extra_snapshot_fields,
        )
        return _ProviderDiscoveryOutcome(
            adapter_key=adapter.adapter_key,
            discovery_status="failed",
            capability_snapshot=_json_object(snapshot),
            discovery_error=discovery_error,
        )
    return _ProviderDiscoveryOutcome(
        adapter_key=adapter.adapter_key,
        discovery_status="ready",
        capability_snapshot=_json_object(snapshot),
        discovery_error=None,
    )


def _persist_discovered_provider_capability(
    *,
    settings: Settings,
    user_account_id: UUID,
    workspace_id: UUID,
    provider: ModelProviderRow,
    outcome: _ProviderDiscoveryOutcome,
) -> ProviderCapabilityRow | None:
    """Persist discovery only if the exact provider configuration is current."""

    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            context = get_local_workspace(conn, user_account_id=user_account_id)
            if context is None or context["workspace"]["id"] != workspace_id:
                return None
            return ContinuityStore(conn).upsert_provider_capability_if_current(
                workspace_id=workspace_id,
                provider_id=provider["id"],
                discovered_by_user_account_id=user_account_id,
                adapter_key=outcome.adapter_key,
                discovery_status=outcome.discovery_status,
                capability_snapshot=outcome.capability_snapshot,
                discovery_error=outcome.discovery_error,
                expected_config_revision=provider["config_revision"],
                expected_config_fingerprint_sha256=provider["config_fingerprint_sha256"],
            )


@dataclass(frozen=True, slots=True)
class _RuntimeProviderInvocationOutcome:
    response: ModelInvocationResponse | None
    error: ModelInvocationError | None
    latency_ms: int
    error_detail: str | None


def _attempt_runtime_provider_model(
    *,
    adapter: ProviderAdapter,
    runtime_provider: RuntimeProviderConfig,
    settings: Settings,
    model_request: ModelInvocationRequest,
) -> _RuntimeProviderInvocationOutcome:
    """Perform only the external provider call; no persistence handle is required."""

    started_at = time.monotonic()
    try:
        model_response = adapter.invoke(
            config=runtime_provider,
            settings=settings,
            request=model_request,
        )
    except ValueError as exc:
        error_detail = str(exc)
        return _RuntimeProviderInvocationOutcome(
            response=None,
            error=ModelInvocationError(error_detail),
            latency_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            error_detail=error_detail,
        )
    except ModelInvocationError as exc:
        sanitized_error = sanitize_provider_error_message(str(exc))
        error: ModelInvocationError
        if isinstance(exc, ModelProviderUnavailableError):
            error = ModelProviderUnavailableError(sanitized_error)
        else:
            error = ModelInvocationError(sanitized_error)
        return _RuntimeProviderInvocationOutcome(
            response=None,
            error=error,
            latency_ms=max(0, int((time.monotonic() - started_at) * 1000)),
            error_detail=sanitized_error,
        )
    return _RuntimeProviderInvocationOutcome(
        response=model_response,
        error=None,
        latency_ms=max(0, int((time.monotonic() - started_at) * 1000)),
        error_detail=None,
    )


def _record_runtime_provider_invocation(
    *,
    store: ContinuityStore,
    workspace_id: UUID,
    invoked_by_user_account_id: UUID,
    thread_id: UUID | None,
    invocation_kind: str,
    adapter: ProviderAdapter,
    runtime_provider: RuntimeProviderConfig,
    model_request: ModelInvocationRequest,
    outcome: _RuntimeProviderInvocationOutcome,
) -> None:
    """Persist provider telemetry after the network call has finished."""

    model_response = outcome.response
    store.record_provider_invocation_telemetry(
        workspace_id=workspace_id,
        provider_id=runtime_provider.provider_id,
        thread_id=thread_id,
        invoked_by_user_account_id=invoked_by_user_account_id,
        invocation_kind=invocation_kind,
        adapter_key=adapter.adapter_key,
        runtime_provider=runtime_provider.model_provider,
        requested_model=model_request.model,
        response_model=model_response.model if model_response is not None else None,
        response_id=model_response.response_id if model_response is not None else None,
        status="succeeded" if model_response is not None else "failed",
        latency_ms=outcome.latency_ms,
        usage=_json_object(model_response.usage)
        if model_response is not None
        else {"input_tokens": None, "output_tokens": None, "total_tokens": None},
        error_detail=outcome.error_detail,
    )


class ProviderConfigurationChangedError(RuntimeError):
    """Raised when mutable provider write context changes across an I/O gap."""


@dataclass(frozen=True, slots=True)
class _StagedProviderSecret:
    secret_ref: str
    encoded_reference: str


def _stage_provider_secret(
    *,
    settings: Settings,
    workspace_id: UUID,
    credential: str,
) -> _StagedProviderSecret:
    normalized_credential = credential.strip()
    if normalized_credential == "":
        raise ValueError("provider credential is required")
    secret_ref = build_provider_secret_ref(workspace_id=workspace_id)
    write_provider_api_key(
        settings=settings,
        secret_ref=secret_ref,
        api_key=normalized_credential,
    )
    return _StagedProviderSecret(
        secret_ref=secret_ref,
        encoded_reference=encode_provider_secret_ref(secret_ref=secret_ref),
    )


def _retire_provider_secret_if_unreferenced(
    *,
    settings: Settings,
    workspace_id: UUID,
    user_account_id: UUID,
    encoded_reference: str,
) -> None:
    if not is_provider_secret_ref(encoded_reference):
        return

    # A commit acknowledgement can be lost after the database has durably
    # stored the staged reference. Treat any inability to prove non-reference
    # as "in use" so compensation can only leak an orphan, never delete a live
    # credential.
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                _assert_provider_write_context(
                    conn=conn,
                    expected_workspace_id=workspace_id,
                    expected_user_account_id=user_account_id,
                )
                in_use = ContinuityStore(conn).is_provider_secret_reference_in_use(
                    workspace_id=workspace_id,
                    encoded_reference=encoded_reference,
                )
    except Exception:
        LOGGER.warning(
            "provider secret retirement skipped because reference state was unavailable",
            exc_info=True,
        )
        return
    if in_use:
        return

    try:
        delete_provider_api_key(
            settings=settings,
            secret_ref=decode_provider_secret_ref(encoded_reference),
        )
    except ProviderSecretManagerError:
        LOGGER.warning("unreferenced provider secret could not be retired", exc_info=True)


def _discard_staged_provider_secret(
    *,
    settings: Settings,
    workspace_id: UUID,
    user_account_id: UUID,
    staged_secret: _StagedProviderSecret | None,
) -> None:
    if staged_secret is None:
        return
    _retire_provider_secret_if_unreferenced(
        settings=settings,
        workspace_id=workspace_id,
        user_account_id=user_account_id,
        encoded_reference=staged_secret.encoded_reference,
    )


def _resolve_owned_provider_workspace(
    *,
    settings: Settings,
    user_account_id: UUID,
) -> tuple[UUID, UUID]:
    return _require_local_provider_workspace(settings=settings, user_account_id=user_account_id)


def _assert_provider_write_context(
    *,
    conn: Any,
    expected_workspace_id: UUID,
    expected_user_account_id: UUID,
) -> None:
    context = get_local_workspace(conn, user_account_id=expected_user_account_id)
    if context is None or context["workspace"]["id"] != expected_workspace_id:
        raise ProviderConfigurationChangedError(
            "provider write context changed while credential storage was being prepared"
        )


def _create_workspace_provider_durable(
    *,
    settings: Settings,
    authenticated_user_id: UUID,
    provider_key: str,
    display_name: str,
    base_url: str,
    api_key: str,
    auth_mode: str,
    default_model: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    metadata: dict[str, object],
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    workspace_id, user_account_id = _resolve_owned_provider_workspace(
        settings=settings,
        user_account_id=authenticated_user_id,
    )
    normalized_base_url = validate_provider_base_url(base_url)
    normalized_auth_mode = auth_mode.strip().lower()
    normalized_api_key = api_key.strip()
    staged_secret: _StagedProviderSecret | None = None
    if normalized_auth_mode == "bearer":
        staged_secret = _stage_provider_secret(
            settings=settings,
            workspace_id=workspace_id,
            credential=normalized_api_key,
        )
        api_key_field = staged_secret.encoded_reference
    elif normalized_auth_mode == "none":
        if normalized_api_key != "":
            raise ValueError("api_key must be empty when auth_mode is none")
        api_key_field = "auth_mode_none"
    else:
        raise ValueError(f"unsupported auth_mode: {auth_mode}")

    provider_persisted = False
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                _assert_provider_write_context(
                    conn=conn,
                    expected_workspace_id=workspace_id,
                    expected_user_account_id=user_account_id,
                )
                provider, capability = _register_workspace_provider(
                    store=ContinuityStore(conn),
                    workspace_id=workspace_id,
                    created_by_user_account_id=user_account_id,
                    provider_key=provider_key,
                    display_name=display_name,
                    base_url=normalized_base_url,
                    api_key_field=api_key_field,
                    auth_mode=auth_mode,
                    default_model=default_model,
                    model_list_path=model_list_path,
                    healthcheck_path=healthcheck_path,
                    invoke_path=invoke_path,
                    metadata=metadata,
                )
        provider_persisted = True
        return provider, capability
    finally:
        if not provider_persisted:
            _discard_staged_provider_secret(
                settings=settings,
                workspace_id=workspace_id,
                user_account_id=user_account_id,
                staged_secret=staged_secret,
            )


def _register_workspace_provider(
    *,
    store: ContinuityStore,
    workspace_id: UUID,
    created_by_user_account_id: UUID,
    provider_key: str,
    display_name: str,
    base_url: str,
    api_key_field: str,
    auth_mode: str,
    default_model: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    metadata: dict[str, object],
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    normalized_display_name = display_name.strip()
    normalized_base_url = base_url.strip()
    normalized_api_key_field = api_key_field.strip()
    normalized_default_model = default_model.strip()
    normalized_auth_mode = auth_mode.strip().lower()
    normalized_model_list_path = _normalize_provider_path(
        field_name="model_list_path",
        value=model_list_path,
    )
    normalized_healthcheck_path = _normalize_provider_path(
        field_name="healthcheck_path",
        value=healthcheck_path,
    )
    normalized_invoke_path = _normalize_provider_path(
        field_name="invoke_path",
        value=invoke_path,
    )

    if normalized_display_name == "":
        raise ValueError("display_name is required")
    normalized_base_url = validate_provider_base_url(
        normalized_base_url,
        require_dns_resolution=False,
    )
    if normalized_default_model == "":
        raise ValueError("default_model is required")
    if normalized_auth_mode not in {"bearer", "none"}:
        raise ValueError(f"unsupported auth_mode: {auth_mode}")
    if normalized_auth_mode == "bearer" and not is_provider_secret_ref(normalized_api_key_field):
        raise ValueError("api_key must be a staged secret reference when auth_mode is bearer")
    if normalized_auth_mode == "none" and normalized_api_key_field != "auth_mode_none":
        raise ValueError("api_key must be empty when auth_mode is none")

    encoded_api_key = normalized_api_key_field

    normalized_metadata = _json_object(metadata)
    config_fingerprint = _provider_config_fingerprint(
        provider_key=provider_key,
        model_provider=OPENAI_RESPONSES_PROVIDER,
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key=encoded_api_key,
        auth_mode=normalized_auth_mode,
        default_model=normalized_default_model,
        status="active",
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version="",
        azure_auth_secret_ref="",
        metadata=normalized_metadata,
    )
    provider = store.create_model_provider(
        workspace_id=workspace_id,
        created_by_user_account_id=created_by_user_account_id,
        provider_key=provider_key,
        model_provider=OPENAI_RESPONSES_PROVIDER,
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key=encoded_api_key,
        default_model=normalized_default_model,
        status="active",
        metadata=normalized_metadata,
        auth_mode=normalized_auth_mode,
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version="",
        # Non-Azure providers intentionally store an empty Azure secret ref.
        azure_auth_secret_ref="",  # nosec B106
        config_fingerprint_sha256=config_fingerprint,
    )

    adapter = provider_adapter_registry.resolve(provider_key)
    capability = store.upsert_provider_capability_if_current(
        workspace_id=workspace_id,
        provider_id=provider["id"],
        discovered_by_user_account_id=created_by_user_account_id,
        adapter_key=adapter.adapter_key,
        discovery_status="failed",
        capability_snapshot=_json_object(
            _fallback_provider_capability_snapshot(
                adapter_key=adapter.adapter_key,
                runtime_provider=adapter.runtime_provider,
                model_list_path=normalized_model_list_path,
                healthcheck_path=normalized_healthcheck_path,
                invoke_path=normalized_invoke_path,
            )
        ),
        discovery_error="capability discovery pending",
        expected_config_revision=provider["config_revision"],
        expected_config_fingerprint_sha256=provider["config_fingerprint_sha256"],
    )
    if capability is None:  # pragma: no cover - same-transaction invariant
        raise ContinuityStoreInvariantError("new provider configuration changed before capability initialization")
    return provider, capability


def _normalize_azure_api_version(value: str) -> str:
    api_version = value.strip()
    if api_version == "":
        raise ValueError("api_version is required")
    return api_version


def _register_workspace_azure_provider(
    *,
    store: ContinuityStore,
    workspace_id: UUID,
    created_by_user_account_id: UUID,
    display_name: str,
    base_url: str,
    credential_secret_ref: str,
    auth_mode: str,
    default_model: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    api_version: str,
    metadata: dict[str, object],
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    normalized_display_name = display_name.strip()
    normalized_base_url = base_url.strip()
    normalized_credential_secret_ref = credential_secret_ref.strip()
    normalized_default_model = default_model.strip()
    normalized_auth_mode = auth_mode.strip().lower()
    normalized_api_version = _normalize_azure_api_version(api_version)
    normalized_model_list_path = _normalize_provider_path(
        field_name="model_list_path",
        value=model_list_path,
    )
    normalized_healthcheck_path = _normalize_provider_path(
        field_name="healthcheck_path",
        value=healthcheck_path,
    )
    normalized_invoke_path = _normalize_provider_path(
        field_name="invoke_path",
        value=invoke_path,
    )

    if normalized_display_name == "":
        raise ValueError("display_name is required")
    normalized_base_url = validate_provider_base_url(
        normalized_base_url,
        require_dns_resolution=False,
    )
    if normalized_default_model == "":
        raise ValueError("default_model is required")
    if normalized_auth_mode not in {AZURE_AUTH_MODE_API_KEY, AZURE_AUTH_MODE_AD_TOKEN}:
        raise ValueError(f"unsupported auth_mode: {auth_mode}")
    if not is_provider_secret_ref(normalized_credential_secret_ref):
        raise ValueError("azure credential must be a staged secret reference")

    encoded_secret_ref = normalized_credential_secret_ref

    normalized_metadata = _json_object(metadata)
    config_fingerprint = _provider_config_fingerprint(
        provider_key=AZURE_ADAPTER_KEY,
        model_provider=OPENAI_RESPONSES_PROVIDER,
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key="auth_mode_azure_secret_ref",
        auth_mode=normalized_auth_mode,
        default_model=normalized_default_model,
        status="active",
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version=normalized_api_version,
        azure_auth_secret_ref=encoded_secret_ref,
        metadata=normalized_metadata,
    )
    provider = store.create_model_provider(
        workspace_id=workspace_id,
        created_by_user_account_id=created_by_user_account_id,
        provider_key=AZURE_ADAPTER_KEY,
        model_provider=OPENAI_RESPONSES_PROVIDER,
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key="auth_mode_azure_secret_ref",
        default_model=normalized_default_model,
        status="active",
        metadata=normalized_metadata,
        auth_mode=normalized_auth_mode,
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version=normalized_api_version,
        azure_auth_secret_ref=encoded_secret_ref,
        config_fingerprint_sha256=config_fingerprint,
    )

    adapter = provider_adapter_registry.resolve(AZURE_ADAPTER_KEY)
    capability = store.upsert_provider_capability_if_current(
        workspace_id=workspace_id,
        provider_id=provider["id"],
        discovered_by_user_account_id=created_by_user_account_id,
        adapter_key=adapter.adapter_key,
        discovery_status="failed",
        capability_snapshot=_json_object(
            _fallback_provider_capability_snapshot(
                adapter_key=adapter.adapter_key,
                runtime_provider=adapter.runtime_provider,
                model_list_path=normalized_model_list_path,
                healthcheck_path=normalized_healthcheck_path,
                invoke_path=normalized_invoke_path,
                extra_snapshot_fields={
                    "azure_api_version": normalized_api_version,
                    "azure_auth_mode": normalized_auth_mode,
                },
            )
        ),
        discovery_error="capability discovery pending",
        expected_config_revision=provider["config_revision"],
        expected_config_fingerprint_sha256=provider["config_fingerprint_sha256"],
    )
    if capability is None:  # pragma: no cover - same-transaction invariant
        raise ContinuityStoreInvariantError("new Azure provider configuration changed before capability initialization")
    return provider, capability


def _create_workspace_azure_provider_durable(
    *,
    settings: Settings,
    authenticated_user_id: UUID,
    display_name: str,
    base_url: str,
    credential: str,
    auth_mode: str,
    default_model: str,
    model_list_path: str,
    healthcheck_path: str,
    invoke_path: str,
    api_version: str,
    metadata: dict[str, object],
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    workspace_id, user_account_id = _resolve_owned_provider_workspace(
        settings=settings,
        user_account_id=authenticated_user_id,
    )
    normalized_base_url = validate_provider_base_url(base_url)
    staged_secret = _stage_provider_secret(
        settings=settings,
        workspace_id=workspace_id,
        credential=credential,
    )
    provider_persisted = False
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                _assert_provider_write_context(
                    conn=conn,
                    expected_workspace_id=workspace_id,
                    expected_user_account_id=user_account_id,
                )
                provider, capability = _register_workspace_azure_provider(
                    store=ContinuityStore(conn),
                    workspace_id=workspace_id,
                    created_by_user_account_id=user_account_id,
                    display_name=display_name,
                    base_url=normalized_base_url,
                    credential_secret_ref=staged_secret.encoded_reference,
                    auth_mode=auth_mode,
                    default_model=default_model,
                    model_list_path=model_list_path,
                    healthcheck_path=healthcheck_path,
                    invoke_path=invoke_path,
                    api_version=api_version,
                    metadata=metadata,
                )
        provider_persisted = True
        return provider, capability
    finally:
        if not provider_persisted:
            _discard_staged_provider_secret(
                settings=settings,
                workspace_id=workspace_id,
                user_account_id=user_account_id,
                staged_secret=staged_secret,
            )


def _update_workspace_provider(
    *,
    store: ContinuityStore,
    existing_provider: ModelProviderRow,
    updated_by_user_account_id: UUID,
    display_name: str | None,
    base_url: str | None,
    api_key: str | None,
    ad_token: str | None,
    credential_secret_ref: str | None,
    auth_mode: str | None,
    default_model: str | None,
    model_list_path: str | None,
    healthcheck_path: str | None,
    invoke_path: str | None,
    api_version: str | None,
    metadata: dict[str, object] | None,
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    provider_key = existing_provider["provider_key"]
    normalized_display_name = existing_provider["display_name"] if display_name is None else display_name.strip()
    normalized_base_url = existing_provider["base_url"] if base_url is None else base_url.strip()
    normalized_default_model = existing_provider["default_model"] if default_model is None else default_model.strip()
    normalized_model_list_path = (
        existing_provider["model_list_path"]
        if model_list_path is None
        else _normalize_provider_path(field_name="model_list_path", value=model_list_path)
    )
    normalized_healthcheck_path = (
        existing_provider["healthcheck_path"]
        if healthcheck_path is None
        else _normalize_provider_path(field_name="healthcheck_path", value=healthcheck_path)
    )
    normalized_invoke_path = (
        existing_provider["invoke_path"]
        if invoke_path is None
        else _normalize_provider_path(field_name="invoke_path", value=invoke_path)
    )
    normalized_metadata: JsonObject = existing_provider["metadata"] if metadata is None else _json_object(metadata)

    if normalized_display_name == "":
        raise ValueError("display_name is required")
    normalized_base_url = validate_provider_base_url(
        normalized_base_url,
        require_dns_resolution=False,
    )
    if normalized_default_model == "":
        raise ValueError("default_model is required")

    encoded_api_key = existing_provider["api_key"]
    normalized_auth_mode = existing_provider["auth_mode"] if auth_mode is None else auth_mode.strip().lower()
    normalized_api_version = existing_provider["azure_api_version"]
    normalized_azure_secret_ref = existing_provider["azure_auth_secret_ref"]

    if provider_key == AZURE_ADAPTER_KEY:
        if normalized_auth_mode not in {AZURE_AUTH_MODE_API_KEY, AZURE_AUTH_MODE_AD_TOKEN}:
            raise ValueError(f"unsupported auth_mode: {normalized_auth_mode}")
        credential_update = api_key if normalized_auth_mode == AZURE_AUTH_MODE_API_KEY else ad_token
        if normalized_auth_mode != existing_provider["auth_mode"] and (
            credential_update is None or credential_update.strip() == "" or credential_secret_ref is None
        ):
            credential_field = "api_key" if normalized_auth_mode == AZURE_AUTH_MODE_API_KEY else "ad_token"
            raise ValueError(f"{credential_field} is required when changing Azure auth_mode")
        if api_version is not None:
            normalized_api_version = _normalize_azure_api_version(api_version)
        if credential_update is not None and credential_update.strip() != "":
            if credential_secret_ref is None or not is_provider_secret_ref(credential_secret_ref):
                raise ValueError("azure credential must be staged before provider update")
            encoded_api_key = "auth_mode_azure_secret_ref"
            normalized_azure_secret_ref = credential_secret_ref
    else:
        if normalized_auth_mode not in {"bearer", "none"}:
            raise ValueError(f"unsupported auth_mode: {normalized_auth_mode}")
        if normalized_auth_mode == "none":
            if api_key is not None and api_key.strip() != "":
                raise ValueError("api_key must be empty when auth_mode is none")
            encoded_api_key = "auth_mode_none"
        else:
            if api_key is not None:
                if api_key.strip() == "":
                    raise ValueError("api_key is required when auth_mode is bearer")
                if credential_secret_ref is None or not is_provider_secret_ref(credential_secret_ref):
                    raise ValueError("api_key must be staged before provider update")
                encoded_api_key = credential_secret_ref
            elif existing_provider["auth_mode"] != "bearer":
                raise ValueError("api_key is required when auth_mode is bearer")
        normalized_api_version = ""
        normalized_azure_secret_ref = ""

    config_fingerprint = _provider_config_fingerprint(
        provider_key=provider_key,
        model_provider=existing_provider["model_provider"],
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key=encoded_api_key,
        auth_mode=normalized_auth_mode,
        default_model=normalized_default_model,
        status=existing_provider["status"],
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version=normalized_api_version,
        azure_auth_secret_ref=normalized_azure_secret_ref,
        metadata=normalized_metadata,
    )
    provider = store.update_model_provider(
        provider_id=existing_provider["id"],
        workspace_id=existing_provider["workspace_id"],
        provider_key=provider_key,
        model_provider=existing_provider["model_provider"],
        display_name=normalized_display_name,
        base_url=normalized_base_url,
        api_key=encoded_api_key,
        auth_mode=normalized_auth_mode,
        default_model=normalized_default_model,
        status=existing_provider["status"],
        model_list_path=normalized_model_list_path,
        healthcheck_path=normalized_healthcheck_path,
        invoke_path=normalized_invoke_path,
        azure_api_version=normalized_api_version,
        azure_auth_secret_ref=normalized_azure_secret_ref,
        metadata=normalized_metadata,
        config_fingerprint_sha256=config_fingerprint,
        expected_config_revision=existing_provider["config_revision"],
        expected_config_fingerprint_sha256=existing_provider["config_fingerprint_sha256"],
    )
    if provider is None:
        raise ProviderConfigurationChangedError("provider configuration changed while the update was being committed")

    adapter = provider_adapter_registry.resolve(provider_key)
    extra_snapshot_fields = None
    if provider_key == AZURE_ADAPTER_KEY:
        extra_snapshot_fields = {
            "azure_api_version": normalized_api_version,
            "azure_auth_mode": normalized_auth_mode,
        }
    capability = store.upsert_provider_capability_if_current(
        workspace_id=existing_provider["workspace_id"],
        provider_id=provider["id"],
        discovered_by_user_account_id=updated_by_user_account_id,
        adapter_key=adapter.adapter_key,
        discovery_status="failed",
        capability_snapshot=_json_object(
            _fallback_provider_capability_snapshot(
                adapter_key=adapter.adapter_key,
                runtime_provider=adapter.runtime_provider,
                model_list_path=normalized_model_list_path,
                healthcheck_path=normalized_healthcheck_path,
                invoke_path=normalized_invoke_path,
                extra_snapshot_fields=extra_snapshot_fields,
            )
        ),
        discovery_error="capability discovery pending",
        expected_config_revision=provider["config_revision"],
        expected_config_fingerprint_sha256=provider["config_fingerprint_sha256"],
    )
    if capability is None:  # pragma: no cover - same-transaction invariant
        raise ContinuityStoreInvariantError("updated provider configuration changed before capability initialization")
    return provider, capability


def _update_workspace_provider_durable(
    *,
    settings: Settings,
    authenticated_user_id: UUID,
    provider_id: UUID,
    display_name: str | None,
    base_url: str | None,
    api_key: str | None,
    ad_token: str | None,
    auth_mode: str | None,
    default_model: str | None,
    model_list_path: str | None,
    healthcheck_path: str | None,
    invoke_path: str | None,
    api_version: str | None,
    metadata: dict[str, object] | None,
) -> tuple[ModelProviderRow, ProviderCapabilityRow]:
    workspace_id, user_account_id = _resolve_owned_provider_workspace(
        settings=settings,
        user_account_id=authenticated_user_id,
    )
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            _assert_provider_write_context(
                conn=conn,
                expected_workspace_id=workspace_id,
                expected_user_account_id=user_account_id,
            )
            existing_provider = ContinuityStore(conn).get_model_provider_for_workspace_optional(
                provider_id=provider_id,
                workspace_id=workspace_id,
            )
            if existing_provider is None:
                raise LookupError(f"provider {provider_id} was not found")

    validated_base_url = validate_provider_base_url(existing_provider["base_url"] if base_url is None else base_url)

    final_auth_mode = existing_provider["auth_mode"] if auth_mode is None else auth_mode.strip().lower()
    credential: str | None = None
    if existing_provider["provider_key"] == AZURE_ADAPTER_KEY:
        if final_auth_mode == AZURE_AUTH_MODE_API_KEY:
            if ad_token is not None and ad_token.strip() != "":
                raise ValueError("ad_token must be empty when auth_mode is azure_api_key")
            credential = api_key
        elif final_auth_mode == AZURE_AUTH_MODE_AD_TOKEN:
            if api_key is not None and api_key.strip() != "":
                raise ValueError("api_key must be empty when auth_mode is azure_ad_token")
            credential = ad_token
        else:
            raise ValueError(f"unsupported auth_mode: {final_auth_mode}")
        if final_auth_mode != existing_provider["auth_mode"] and (credential is None or credential.strip() == ""):
            credential_field = "api_key" if final_auth_mode == AZURE_AUTH_MODE_API_KEY else "ad_token"
            raise ValueError(f"{credential_field} is required when changing Azure auth_mode")
    else:
        if ad_token is not None and ad_token.strip() != "":
            raise ValueError("ad_token is only supported by Azure providers")
        if final_auth_mode not in {"bearer", "none"}:
            raise ValueError(f"unsupported auth_mode: {final_auth_mode}")
        if final_auth_mode == "none" and api_key is not None and api_key.strip() != "":
            raise ValueError("api_key must be empty when auth_mode is none")
        if final_auth_mode == "bearer":
            credential = api_key

    staged_secret: _StagedProviderSecret | None = None
    if credential is not None:
        if credential.strip() == "":
            if existing_provider["provider_key"] != AZURE_ADAPTER_KEY:
                raise ValueError("api_key is required when auth_mode is bearer")
        else:
            staged_secret = _stage_provider_secret(
                settings=settings,
                workspace_id=workspace_id,
                credential=credential,
            )

    old_secret_reference = (
        existing_provider["azure_auth_secret_ref"]
        if existing_provider["provider_key"] == AZURE_ADAPTER_KEY
        else existing_provider["api_key"]
    )
    provider_persisted = False
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                _assert_provider_write_context(
                    conn=conn,
                    expected_workspace_id=workspace_id,
                    expected_user_account_id=user_account_id,
                )
                store = ContinuityStore(conn)
                current_provider = store.get_model_provider_for_workspace_optional(
                    provider_id=provider_id,
                    workspace_id=workspace_id,
                )
                if current_provider is None:
                    raise LookupError(f"provider {provider_id} was not found")
                if (
                    current_provider["config_revision"] != existing_provider["config_revision"]
                    or current_provider["config_fingerprint_sha256"] != existing_provider["config_fingerprint_sha256"]
                ):
                    raise ProviderConfigurationChangedError(
                        "provider configuration changed while credential storage was being prepared"
                    )
                provider, capability = _update_workspace_provider(
                    store=store,
                    existing_provider=current_provider,
                    updated_by_user_account_id=user_account_id,
                    display_name=display_name,
                    base_url=validated_base_url,
                    api_key=api_key,
                    ad_token=ad_token,
                    credential_secret_ref=(None if staged_secret is None else staged_secret.encoded_reference),
                    auth_mode=auth_mode,
                    default_model=default_model,
                    model_list_path=model_list_path,
                    healthcheck_path=healthcheck_path,
                    invoke_path=invoke_path,
                    api_version=api_version,
                    metadata=metadata,
                )
        provider_persisted = True
        new_secret_reference = (
            provider["azure_auth_secret_ref"] if provider["provider_key"] == AZURE_ADAPTER_KEY else provider["api_key"]
        )
        if old_secret_reference != new_secret_reference:
            _retire_provider_secret_if_unreferenced(
                settings=settings,
                workspace_id=workspace_id,
                user_account_id=user_account_id,
                encoded_reference=old_secret_reference,
            )
        return provider, capability
    finally:
        if not provider_persisted:
            _discard_staged_provider_secret(
                settings=settings,
                workspace_id=workspace_id,
                user_account_id=user_account_id,
                staged_secret=staged_secret,
            )


def _seed_workspace_provider_configs(
    *,
    settings: Settings,
    user_account_id: UUID,
    workspace_id: UUID,
) -> list[ModelProviderRow]:
    if len(settings.workspace_provider_configs) == 0:
        return []
    resolved_workspace_id, resolved_user_account_id = _resolve_owned_provider_workspace(
        settings=settings,
        user_account_id=user_account_id,
    )
    if resolved_workspace_id != workspace_id:
        raise ProviderConfigurationChangedError("workspace selection changed before provider bootstrap")
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            _assert_provider_write_context(
                conn=conn,
                expected_workspace_id=workspace_id,
                expected_user_account_id=resolved_user_account_id,
            )
            existing_provider_keys = {
                (provider["provider_key"], provider["display_name"])
                for provider in ContinuityStore(conn).list_model_providers_for_workspace(workspace_id=workspace_id)
            }

    seeded_providers: list[ModelProviderRow] = []
    for provider_config in settings.workspace_provider_configs:
        provider_identity = (provider_config.provider_key, provider_config.display_name)
        if provider_identity in existing_provider_keys:
            continue
        provider, _capability = _create_workspace_provider_durable(
            settings=settings,
            authenticated_user_id=resolved_user_account_id,
            provider_key=provider_config.provider_key,
            display_name=provider_config.display_name,
            base_url=provider_config.base_url,
            api_key=provider_config.api_key,
            auth_mode=provider_config.auth_mode,
            default_model=provider_config.default_model,
            model_list_path=provider_config.model_list_path,
            healthcheck_path=provider_config.healthcheck_path,
            invoke_path=provider_config.invoke_path,
            metadata={} if provider_config.metadata is None else dict(provider_config.metadata),
        )
        seeded_providers.append(provider)
        existing_provider_keys.add(provider_identity)
    return seeded_providers


def redact_url_credentials(raw_url: str) -> str:
    parsed = urlsplit(raw_url)

    if parsed.hostname is None or (parsed.username is None and parsed.password is None):
        return raw_url

    hostname = parsed.hostname
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    netloc = hostname
    if parsed.port is not None:
        netloc = f"{hostname}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def build_healthcheck_payload(settings: Settings, database_ok: bool) -> HealthcheckPayload:
    status: HealthStatus = "ok" if database_ok else "degraded"
    database_status: Literal["ok", "unreachable"] = "ok" if database_ok else "unreachable"

    return {
        "status": status,
        "environment": settings.app_env,
        "services": {
            "database": {
                "status": database_status,
            },
            "redis": {
                "status": "not_checked",
                "url": redact_url_credentials(settings.redis_url),
            },
            "object_storage": {
                "status": "not_checked",
            },
        },
    }


def _response_job_headers(
    job: ResponseGenerationJobRow,
    *,
    replayed: bool,
) -> dict[str, str]:
    headers = {"Response-Job-Id": str(job["id"])}
    if replayed:
        headers["Idempotency-Replayed"] = "true"
    return headers


def _response_job_public_status(job: ResponseGenerationJobRow) -> JsonObject:
    return {
        "id": str(job["id"]),
        "state": job["state"],
        "endpoint": job["endpoint"],
        "created_at": job["created_at"].isoformat(),
        "updated_at": job["updated_at"].isoformat(),
        "completed_at": None if job["completed_at"] is None else job["completed_at"].isoformat(),
    }


def _terminal_response_job_replay(job: ResponseGenerationJobRow) -> JSONResponse:
    payload = job["response_payload"] if job["state"] == "succeeded" else job["error_payload"]
    status_code = job["response_status_code"]
    if payload is None or status_code is None:
        raise RuntimeError("terminal response job is missing its persisted outcome")
    return JSONResponse(
        status_code=status_code,
        headers=_response_job_headers(job, replayed=True),
        content=jsonable_encoder(payload),
    )


def _response_job_replay_or_in_progress(
    *,
    store: ResponseGenerationJobStore,
    job: ResponseGenerationJobRow,
    expected_request_fingerprint: str,
) -> JSONResponse | None:
    if job["request_fingerprint_sha256"] != expected_request_fingerprint:
        return JSONResponse(
            status_code=409,
            content={
                "detail": {
                    "code": "idempotency_key_reused",
                    "message": "Idempotency-Key was already used for a different request",
                }
            },
        )
    if job["state"] in {"succeeded", "failed"}:
        return _terminal_response_job_replay(job)
    if job["state"] == "pending":
        return None
    if job["state"] != "running":
        raise RuntimeError(f"unsupported response job state: {job['state']}")

    abandoned_payload: JsonObject = {
        "detail": {
            "code": "provider_outcome_unknown",
            "message": (
                "the original provider call did not finalize before its lease expired; "
                "AliceBot will not invoke it again under the same Idempotency-Key"
            ),
        },
        "response_job": {**_response_job_public_status(job), "state": "failed"},
    }
    abandoned = store.fail_if_abandoned(
        job_id=job["id"],
        error_payload=abandoned_payload,
    )
    if abandoned is not None:
        return _terminal_response_job_replay(abandoned)
    return JSONResponse(
        status_code=202,
        headers={
            **_response_job_headers(job, replayed=True),
            "Retry-After": "2",
        },
        content=jsonable_encoder(
            {
                "detail": {
                    "code": "response_generation_in_progress",
                    "message": "response generation is already in progress for this Idempotency-Key",
                },
                "response_job": _response_job_public_status(job),
            }
        ),
    )


def _request_client_identifier(request: Request, settings: Settings) -> str:
    peer_host = ""
    if request.client is not None:
        peer_host = (request.client.host or "").strip()

    if settings.trust_proxy_headers and peer_host != "" and peer_host in settings.trusted_proxy_ips:
        forwarded_for = request.headers.get("x-forwarded-for", "").strip()
        if forwarded_for != "":
            first_hop = forwarded_for.split(",", maxsplit=1)[0].strip()
            if first_hop != "":
                return first_hop

    if peer_host == "":
        return "unknown"
    return peer_host


def _request_client_is_loopback(request: Request, settings: Settings) -> bool:
    client_identifier = _request_client_identifier(request, settings)
    try:
        client_ip = ipaddress.ip_address(client_identifier)
    except ValueError:
        return client_identifier in {"localhost", "localhost.localdomain"}
    return client_ip.is_loopback


def _append_vary_header(response: Response, value: str) -> None:
    existing = response.headers.get("Vary", "")
    values = [item.strip() for item in existing.split(",") if item.strip() != ""]
    if value not in values:
        values.append(value)
    response.headers["Vary"] = ", ".join(values)


def _cors_origin_allowed(origin: str, allowed_origins: tuple[str, ...]) -> bool:
    if len(allowed_origins) == 0:
        return False
    if "*" in allowed_origins:
        return True
    return origin in allowed_origins


def _resolve_cors_allow_origin_value(settings: Settings, origin: str) -> str:
    if "*" in settings.cors_allowed_origins and not settings.cors_allow_credentials:
        return "*"
    return origin


def _apply_cors_headers(
    *,
    response: Response,
    settings: Settings,
    origin: str,
    preflight: bool,
) -> None:
    allow_origin = _resolve_cors_allow_origin_value(settings, origin)
    response.headers["Access-Control-Allow-Origin"] = allow_origin
    if allow_origin != "*":
        _append_vary_header(response, "Origin")
    if settings.cors_allow_credentials:
        response.headers["Access-Control-Allow-Credentials"] = "true"

    if not preflight:
        return

    response.headers["Access-Control-Allow-Methods"] = ", ".join(settings.cors_allowed_methods)
    response.headers["Access-Control-Allow-Headers"] = ", ".join(settings.cors_allowed_headers)
    response.headers["Access-Control-Max-Age"] = str(settings.cors_preflight_max_age_seconds)
    _append_vary_header(response, "Access-Control-Request-Method")
    _append_vary_header(response, "Access-Control-Request-Headers")


def _apply_security_headers(*, response: Response, settings: Settings, request: Request) -> None:
    if not settings.security_headers_enabled:
        return

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), "
            "microphone=(), payment=(), usb=()"
        ),
    )

    if request.url.scheme != "https" or settings.app_env in {"development", "test"}:
        return

    hsts_value = f"max-age={settings.security_headers_hsts_max_age_seconds}"
    if settings.security_headers_hsts_include_subdomains:
        hsts_value += "; includeSubDomains"
    response.headers.setdefault("Strict-Transport-Security", hsts_value)


@app.middleware("http")
async def apply_http_security_posture(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = get_settings()
    origin = request.headers.get("origin", "").strip()
    is_preflight = (
        request.method.upper() == "OPTIONS" and request.headers.get("access-control-request-method", "").strip() != ""
    )
    response: Response

    if is_preflight:
        if origin == "" or not _cors_origin_allowed(origin, settings.cors_allowed_origins):
            response = JSONResponse(status_code=403, content={"detail": "CORS origin is not allowed"})
            _apply_security_headers(response=response, settings=settings, request=request)
            return response
        response = Response(status_code=204)
        _apply_cors_headers(response=response, settings=settings, origin=origin, preflight=True)
        _apply_security_headers(response=response, settings=settings, request=request)
        return response

    response = await call_next(request)
    if origin != "" and _cors_origin_allowed(origin, settings.cors_allowed_origins):
        _apply_cors_headers(response=response, settings=settings, origin=origin, preflight=False)
    _apply_security_headers(response=response, settings=settings, request=request)
    return response


@app.middleware("http")
async def enforce_authenticated_user_identity(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not request.url.path.startswith("/v0/"):
        return await call_next(request)

    settings = get_settings()

    if settings.app_env not in {"development", "test"}:
        if not settings.legacy_v0_enabled_outside_dev:
            return JSONResponse(
                status_code=404,
                content={"detail": "legacy v0 API is disabled outside development and test"},
            )
        if not _request_client_is_loopback(request, settings):
            return JSONResponse(
                status_code=403,
                content={"detail": "legacy v0 API is restricted to loopback clients"},
            )

    try:
        authenticated_user_id = _resolve_authenticated_user_id(settings, request)
        if authenticated_user_id is not None:
            request.scope.setdefault("state", {})["authenticated_user_id"] = str(authenticated_user_id)
            _rewrite_user_id_query_param(request, authenticated_user_id)
            request = await _rewrite_user_id_json_body(request, authenticated_user_id)
    except ValueError as exc:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    return await call_next(request)


class RegisterProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_key: Literal["openai_compatible"] = "openai_compatible"
    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=8000)
    auth_mode: Literal["bearer"] = "bearer"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/models", min_length=1, max_length=200)
    invoke_path: str = Field(default="/responses", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterOllamaProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(default="http://127.0.0.1:11434", min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)
    auth_mode: Literal["bearer", "none"] = "none"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/api/tags", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/api/version", min_length=1, max_length=200)
    invoke_path: str = Field(default="/api/chat", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterLlamaCppProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(default="http://127.0.0.1:8080", min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)
    auth_mode: Literal["bearer", "none"] = "none"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/v1/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/health", min_length=1, max_length=200)
    invoke_path: str = Field(default="/v1/chat/completions", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterVllmProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(default="http://127.0.0.1:8001", min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)
    auth_mode: Literal["bearer", "none"] = "none"
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/v1/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/health", min_length=1, max_length=200)
    invoke_path: str = Field(default="/v1/chat/completions", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)


class RegisterAzureProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=500)
    auth_mode: Literal["azure_api_key", "azure_ad_token"] = "azure_api_key"
    api_key: str | None = Field(default=None, max_length=8000)
    ad_token: str | None = Field(default=None, max_length=16000)
    api_version: str = Field(default=DEFAULT_AZURE_API_VERSION, min_length=1, max_length=40)
    default_model: str = Field(min_length=1, max_length=200)
    model_list_path: str = Field(default="/openai/models", min_length=1, max_length=200)
    healthcheck_path: str = Field(default="/openai/models", min_length=1, max_length=200)
    invoke_path: str = Field(default="/openai/responses", min_length=1, max_length=200)
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_auth_payload(self) -> "RegisterAzureProviderRequest":
        api_key = None if self.api_key is None else self.api_key.strip()
        ad_token = None if self.ad_token is None else self.ad_token.strip()

        if self.auth_mode == AZURE_AUTH_MODE_API_KEY:
            if api_key in (None, ""):
                raise ValueError("api_key is required when auth_mode is azure_api_key")
            if ad_token not in (None, ""):
                raise ValueError("ad_token must be empty when auth_mode is azure_api_key")
            return self

        if ad_token in (None, ""):
            raise ValueError("ad_token is required when auth_mode is azure_ad_token")
        if api_key not in (None, ""):
            raise ValueError("api_key must be empty when auth_mode is azure_ad_token")
        return self


class TestProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: UUID
    model: str | None = Field(default=None, min_length=1, max_length=200)
    prompt: str = Field(
        default="Reply with a concise provider connectivity confirmation.",
        min_length=1,
        max_length=1000,
    )


class UpdateProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    auth_mode: str | None = Field(default=None, min_length=1, max_length=40)
    api_key: str | None = Field(default=None, max_length=8000)
    ad_token: str | None = Field(default=None, max_length=16000)
    api_version: str | None = Field(default=None, min_length=1, max_length=40)
    default_model: str | None = Field(default=None, min_length=1, max_length=200)
    model_list_path: str | None = Field(default=None, min_length=1, max_length=200)
    healthcheck_path: str | None = Field(default=None, min_length=1, max_length=200)
    invoke_path: str | None = Field(default=None, min_length=1, max_length=200)
    metadata: dict[str, object] | None = None


class TaskBriefCompileSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["user_recall", "resume", "worker_subtask", "agent_handoff"]
    query: str | None = Field(default=None, min_length=1, max_length=4000)
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = Field(default=None, min_length=1, max_length=200)
    person: str | None = Field(default=None, min_length=1, max_length=200)
    since: datetime | None = None
    until: datetime | None = None
    include_non_promotable_facts: bool = False
    provider_strategy: str | None = Field(default=None, min_length=1, max_length=80)
    briefing_strategy: Literal["balanced", "compact", "detailed"] | None = None
    token_budget: int | None = Field(default=None, ge=1, le=MAX_TASK_BRIEF_TOKEN_BUDGET)


class TaskBriefCompileRequest(TaskBriefCompileSpec):
    user_id: UUID


class TaskBriefCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    primary: TaskBriefCompileSpec
    secondary: TaskBriefCompileSpec


class RuntimeInvokeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: UUID
    thread_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    max_sessions: int = Field(default=DEFAULT_MAX_SESSIONS, ge=1, le=50)
    max_events: int = Field(default=DEFAULT_MAX_EVENTS, ge=1, le=200)
    max_memories: int = Field(default=DEFAULT_MAX_MEMORIES, ge=1, le=200)
    max_entities: int = Field(default=DEFAULT_MAX_ENTITIES, ge=1, le=200)
    max_entity_edges: int = Field(default=DEFAULT_MAX_ENTITY_EDGES, ge=1, le=400)


def _resolve_authenticated_v1_user_id(settings: Settings, request: Request) -> UUID:
    user_account_id = _resolve_authenticated_user_id(settings, request)
    if user_account_id is None:
        raise ValueError(
            "local identity is required; set ALICEBOT_AUTH_USER_ID or provide X-AliceBot-User-Id"
        )
    return user_account_id


def _require_local_provider_workspace(
    *,
    settings: Settings,
    user_account_id: UUID,
) -> tuple[UUID, UUID]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.transaction():
            context = get_local_workspace(conn, user_account_id=user_account_id)
    if context is None:
        raise LookupError("local workspace is not bootstrapped; POST /v1/workspaces/bootstrap first")
    return context["workspace"]["id"], user_account_id


def _allow_raw_evidence_debug_access(settings: Settings) -> bool:
    return settings.app_env in {"development", "test"}


def _audit_raw_evidence_access(
    *,
    request: Request,
    settings: Settings,
    route: str,
    user_id: UUID,
) -> None:
    LOGGER.info(
        "raw evidence content requested route=%s user_id=%s client=%s",
        route,
        user_id,
        _request_client_identifier(request, settings),
    )


@app.get("/healthz")
def healthcheck() -> JSONResponse:
    settings = get_settings()
    database_ok = ping_database(
        settings.database_url,
        settings.healthcheck_timeout_seconds,
    )
    payload = build_healthcheck_payload(settings, database_ok)
    status_code = 200 if payload["status"] == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content=payload,
    )


@app.get("/v0/agent-profiles")
def list_agent_profiles() -> JSONResponse:
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        items = list_registered_agent_profiles(ContinuityStore(conn))
    summary: AgentProfileListSummary = {
        "total_count": len(items),
        "order": list(AGENT_PROFILE_LIST_ORDER),
    }
    payload: AgentProfileListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/context/compile")
def compile_context(request: CompileContextRequest) -> JSONResponse:
    settings = get_settings()
    artifact_retrieval: (
        CompileContextTaskScopedArtifactRetrievalInput | CompileContextArtifactScopedArtifactRetrievalInput | None
    ) = None
    semantic_artifact_retrieval: (
        CompileContextTaskScopedSemanticArtifactRetrievalInput
        | CompileContextArtifactScopedSemanticArtifactRetrievalInput
        | None
    ) = None
    if isinstance(request.artifact_retrieval, CompileContextTaskScopedArtifactRetrievalRequest):
        artifact_retrieval = CompileContextTaskScopedArtifactRetrievalInput(
            task_id=request.artifact_retrieval.task_id,
            query=request.artifact_retrieval.query,
            limit=request.artifact_retrieval.limit,
        )
    elif isinstance(
        request.artifact_retrieval,
        CompileContextArtifactScopedArtifactRetrievalRequest,
    ):
        artifact_retrieval = CompileContextArtifactScopedArtifactRetrievalInput(
            task_artifact_id=request.artifact_retrieval.task_artifact_id,
            query=request.artifact_retrieval.query,
            limit=request.artifact_retrieval.limit,
        )
    if isinstance(
        request.semantic_artifact_retrieval,
        CompileContextTaskScopedSemanticArtifactRetrievalRequest,
    ):
        semantic_artifact_retrieval = CompileContextTaskScopedSemanticArtifactRetrievalInput(
            task_id=request.semantic_artifact_retrieval.task_id,
            embedding_config_id=request.semantic_artifact_retrieval.embedding_config_id,
            query_vector=tuple(request.semantic_artifact_retrieval.query_vector),
            limit=request.semantic_artifact_retrieval.limit,
        )
    elif isinstance(
        request.semantic_artifact_retrieval,
        CompileContextArtifactScopedSemanticArtifactRetrievalRequest,
    ):
        semantic_artifact_retrieval = CompileContextArtifactScopedSemanticArtifactRetrievalInput(
            task_artifact_id=request.semantic_artifact_retrieval.task_artifact_id,
            embedding_config_id=request.semantic_artifact_retrieval.embedding_config_id,
            query_vector=tuple(request.semantic_artifact_retrieval.query_vector),
            limit=request.semantic_artifact_retrieval.limit,
        )

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = ContinuityStore(conn)
            thread = store.get_thread(request.thread_id)
            result = compile_and_persist_trace(
                store,
                user_id=request.user_id,
                thread_id=request.thread_id,
                limits=ContextCompilerLimits(
                    max_sessions=request.max_sessions,
                    max_events=request.max_events,
                    max_memories=request.max_memories,
                    max_entities=request.max_entities,
                    max_entity_edges=request.max_entity_edges,
                ),
                semantic_retrieval=(
                    None
                    if request.semantic is None
                    else CompileContextSemanticRetrievalInput(
                        embedding_config_id=request.semantic.embedding_config_id,
                        query_vector=tuple(request.semantic.query_vector),
                        limit=request.semantic.limit,
                    )
                ),
                artifact_retrieval=artifact_retrieval,
                semantic_artifact_retrieval=semantic_artifact_retrieval,
            )
    except TaskArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except SemanticArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except SemanticMemoryRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (TaskNotFoundError, TaskArtifactNotFoundError) as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ContinuityStoreInvariantError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "trace_id": result.trace_id,
                "trace_event_count": result.trace_event_count,
                "context_pack": result.context_pack,
                "metadata": {"agent_profile_id": _thread_agent_profile_id(thread)},
            }
        ),
    )


@app.post("/v0/threads")
def create_thread(request: CreateThreadRequest) -> JSONResponse:
    settings = get_settings()
    agent_profile_id = request.agent_profile_id if request.agent_profile_id is not None else DEFAULT_AGENT_PROFILE_ID
    thread_input = ThreadCreateInput(
        title=request.title,
        agent_profile_id=agent_profile_id,
    )

    with user_connection(settings.database_url, request.user_id) as conn:
        store = ContinuityStore(conn)
        if get_registered_agent_profile(store, agent_profile_id) is None:
            allowed_agent_profile_ids = list_registered_agent_profile_ids(store)
            return JSONResponse(
                status_code=422,
                content={
                    "detail": {
                        "code": "invalid_agent_profile_id",
                        "message": ("agent_profile_id must be one of: " + ", ".join(allowed_agent_profile_ids)),
                        "allowed_agent_profile_ids": allowed_agent_profile_ids,
                    }
                },
            )

        created = store.create_thread(
            thread_input.title,
            thread_input.agent_profile_id,
        )

    payload: ThreadCreateResponse = {"thread": _serialize_thread(created)}
    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads")
def list_threads(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        items = [_serialize_thread(thread) for thread in ContinuityStore(conn).list_threads()]

    summary: ThreadListSummary = {
        "total_count": len(items),
        "order": list(THREAD_LIST_ORDER),
    }
    payload: ThreadListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/health-dashboard")
def get_threads_health_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: ThreadHealthDashboardResponse = get_thread_health_dashboard(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}")
def get_thread(thread_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        thread = ContinuityStore(conn).get_thread_optional(thread_id)

    if thread is None:
        return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})

    payload: ThreadDetailResponse = {"thread": _serialize_thread(thread)}
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}/sessions")
def list_thread_sessions(thread_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        thread = store.get_thread_optional(thread_id)
        if thread is None:
            return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})
        items = [_serialize_thread_session(session) for session in store.list_thread_sessions(thread_id)]

    summary: ThreadSessionListSummary = {
        "thread_id": str(thread["id"]),
        "total_count": len(items),
        "order": list(THREAD_SESSION_LIST_ORDER),
    }
    payload: ThreadSessionListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}/events")
def list_thread_events(thread_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        thread = store.get_thread_optional(thread_id)
        if thread is None:
            return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})
        items = [_serialize_thread_event(event) for event in store.list_thread_events(thread_id)]

    summary: ThreadEventListSummary = {
        "thread_id": str(thread["id"]),
        "total_count": len(items),
        "order": list(THREAD_EVENT_LIST_ORDER),
    }
    payload: ThreadEventListResponse = {
        "items": items,
        "summary": summary,
    }
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/threads/{thread_id}/resumption-brief")
def get_thread_resumption_brief(
    thread_id: UUID,
    user_id: UUID,
    max_events: Annotated[
        int,
        Query(ge=0, le=MAX_RESUMPTION_BRIEF_EVENT_LIMIT),
    ] = DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT,
    max_open_loops: Annotated[
        int,
        Query(
            ge=0,
            le=MAX_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
        ),
    ] = DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    max_memories: Annotated[
        int,
        Query(ge=0, le=MAX_RESUMPTION_BRIEF_MEMORY_LIMIT),
    ] = DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT,
) -> JSONResponse:
    settings = get_settings()
    request = ResumptionBriefRequestInput(
        thread_id=thread_id,
        max_events=max_events,
        max_open_loops=max_open_loops,
        max_memories=max_memories,
    )

    with user_connection(settings.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        thread = store.get_thread_optional(thread_id)
        if thread is None:
            return JSONResponse(status_code=404, content={"detail": f"thread {thread_id} was not found"})
        brief = compile_resumption_brief(
            store,
            thread=thread,
            event_limit=request.max_events,
            open_loop_limit=request.max_open_loops,
            memory_limit=request.max_memories,
        )

    payload: ResumptionBriefResponse = {"brief": brief}
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/traces")
def list_traces(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_trace_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/traces/{trace_id}")
def get_trace(trace_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_trace_record(
                ContinuityStore(conn),
                user_id=user_id,
                trace_id=trace_id,
            )
    except TraceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/traces/{trace_id}/events")
def list_trace_events(trace_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_trace_event_records(
                ContinuityStore(conn),
                user_id=user_id,
                trace_id=trace_id,
            )
    except TraceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/admit")
def admit_memory(request: AdmitMemoryRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            decision = admit_memory_candidate(
                ContinuityStore(conn),
                user_id=request.user_id,
                candidate=MemoryCandidateInput(
                    memory_key=request.memory_key,
                    value=_json_value(request.value),
                    source_event_ids=tuple(request.source_event_ids),
                    agent_profile_id=request.agent_profile_id,
                    delete_requested=request.delete_requested,
                    memory_type=request.memory_type,
                    confidence=request.confidence,
                    salience=request.salience,
                    confirmation_status=request.confirmation_status,
                    trust_class=request.trust_class,
                    promotion_eligibility=request.promotion_eligibility,
                    evidence_count=request.evidence_count,
                    independent_source_count=request.independent_source_count,
                    extracted_by_model=request.extracted_by_model,
                    trust_reason=request.trust_reason,
                    valid_from=request.valid_from,
                    valid_to=request.valid_to,
                    last_confirmed_at=request.last_confirmed_at,
                    open_loop=(
                        None
                        if request.open_loop is None
                        else OpenLoopCandidateInput(
                            title=request.open_loop.title,
                            due_at=request.open_loop.due_at,
                        )
                    ),
                ),
            )
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    payload: dict[str, object] = {
        "decision": decision.action,
        "reason": decision.reason,
        "memory": decision.memory,
        "revision": decision.revision,
    }
    if decision.open_loop is not None:
        payload["open_loop"] = decision.open_loop

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/open-loops")
def list_open_loops(
    user_id: UUID,
    status: OpenLoopStatusFilter = Query(default="open"),
    limit: int = Query(default=DEFAULT_OPEN_LOOP_LIMIT, ge=1, le=MAX_OPEN_LOOP_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_open_loop_records(
            ContinuityStore(conn),
            user_id=user_id,
            status=status,
            limit=limit,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/open-loops/{open_loop_id}")
def get_open_loop(
    open_loop_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_open_loop_record(
                ContinuityStore(conn),
                user_id=user_id,
                open_loop_id=open_loop_id,
            )
    except OpenLoopNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/open-loops")
def create_open_loop(request: CreateOpenLoopRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_open_loop_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                open_loop=OpenLoopCreateInput(
                    memory_id=request.memory_id,
                    title=request.title,
                    due_at=request.due_at,
                ),
            )
    except OpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/open-loops/{open_loop_id}/status")
def update_open_loop_status(
    open_loop_id: UUID,
    request: UpdateOpenLoopStatusRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = update_open_loop_status_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                open_loop_id=open_loop_id,
                request=OpenLoopStatusUpdateInput(
                    status=request.status,  # type: ignore[arg-type]
                    resolution_note=request.resolution_note,
                ),
            )
    except OpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except OpenLoopNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/consents")
def upsert_consent(request: UpsertConsentRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = upsert_consent_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                consent=ConsentUpsertInput(
                    consent_key=request.consent_key,
                    status=request.status,
                    metadata=_json_object(request.metadata),
                ),
            )
    except PolicyValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    status_code = 201 if payload["write_mode"] == "created" else 200
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/consents")
def list_consents(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_consent_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/policies")
def create_policy(request: CreatePolicyRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = ContinuityStore(conn)
            if (
                request.agent_profile_id is not None
                and get_registered_agent_profile(store, request.agent_profile_id) is None
            ):
                allowed_agent_profile_ids = list_registered_agent_profile_ids(store)
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": {
                            "code": "invalid_agent_profile_id",
                            "message": ("agent_profile_id must be one of: " + ", ".join(allowed_agent_profile_ids)),
                            "allowed_agent_profile_ids": allowed_agent_profile_ids,
                        }
                    },
                )

            payload = create_policy_record(
                store,
                user_id=request.user_id,
                policy=PolicyCreateInput(
                    name=request.name,
                    action=request.action,
                    scope=request.scope,
                    effect=request.effect,
                    priority=request.priority,
                    active=request.active,
                    conditions=_json_object(request.conditions),
                    required_consents=tuple(request.required_consents),
                    agent_profile_id=request.agent_profile_id,
                ),
            )
    except PolicyValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/policies")
def list_policies(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_policy_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/policies/{policy_id}")
def get_policy(policy_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_policy_record(
                ContinuityStore(conn),
                user_id=user_id,
                policy_id=policy_id,
            )
    except PolicyNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/policies/evaluate")
def evaluate_policy(request: EvaluatePolicyRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = evaluate_policy_request(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=PolicyEvaluationRequestInput(
                    thread_id=request.thread_id,
                    action=request.action,
                    scope=request.scope,
                    attributes=_json_object(request.attributes),
                ),
            )
    except PolicyEvaluationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tools")
def create_tool(request: CreateToolRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_tool_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                tool=ToolCreateInput(
                    tool_key=request.tool_key,
                    name=request.name,
                    description=request.description,
                    version=request.version,
                    metadata_version=request.metadata_version,
                    active=request.active,
                    tags=tuple(request.tags),
                    action_hints=tuple(request.action_hints),
                    scope_hints=tuple(request.scope_hints),
                    domain_hints=tuple(request.domain_hints),
                    risk_hints=tuple(request.risk_hints),
                    metadata=_json_object(request.metadata),
                ),
            )
    except ToolValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tools")
def list_tools(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_tool_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tools/allowlist/evaluate")
def evaluate_tools_allowlist(request: EvaluateToolAllowlistRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = evaluate_tool_allowlist(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ToolAllowlistEvaluationRequestInput(
                    thread_id=request.thread_id,
                    action=request.action,
                    scope=request.scope,
                    domain_hint=request.domain_hint,
                    risk_hint=request.risk_hint,
                    attributes=_json_object(request.attributes),
                ),
            )
    except ToolAllowlistValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tools/route")
def route_tool(request: RouteToolRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = route_tool_invocation(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ToolRoutingRequestInput(
                    thread_id=request.thread_id,
                    tool_id=request.tool_id,
                    action=request.action,
                    scope=request.scope,
                    domain_hint=request.domain_hint,
                    risk_hint=request.risk_hint,
                    attributes=_json_object(request.attributes),
                ),
            )
    except ToolRoutingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/requests")
def create_approval_request(request: CreateApprovalRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = submit_approval_request(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ApprovalRequestCreateInput(
                    thread_id=request.thread_id,
                    tool_id=request.tool_id,
                    task_run_id=request.task_run_id,
                    action=request.action,
                    scope=request.scope,
                    domain_hint=request.domain_hint,
                    risk_hint=request.risk_hint,
                    attributes=_json_object(request.attributes),
                ),
            )
    except ToolRoutingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/approvals")
def list_approvals(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_approval_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/approvals/{approval_id}")
def get_approval(approval_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_approval_record(
                ContinuityStore(conn),
                user_id=user_id,
                approval_id=approval_id,
            )
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/{approval_id}/approve")
def approve_approval(approval_id: UUID, request: ResolveApprovalRequest) -> JSONResponse:
    settings = get_settings()
    resolution_error: (
        ApprovalResolutionConflictError | TaskStepApprovalLinkageError | TaskStepLifecycleBoundaryError | None
    ) = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = approve_approval_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ApprovalApproveInput(approval_id=approval_id),
                )
            except (
                ApprovalResolutionConflictError,
                TaskStepApprovalLinkageError,
                TaskStepLifecycleBoundaryError,
            ) as exc:
                resolution_error = exc
                payload = None
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if resolution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(resolution_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/{approval_id}/reject")
def reject_approval(approval_id: UUID, request: ResolveApprovalRequest) -> JSONResponse:
    settings = get_settings()
    resolution_error: (
        ApprovalResolutionConflictError | TaskStepApprovalLinkageError | TaskStepLifecycleBoundaryError | None
    ) = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = reject_approval_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ApprovalRejectInput(approval_id=approval_id),
                )
            except (
                ApprovalResolutionConflictError,
                TaskStepApprovalLinkageError,
                TaskStepLifecycleBoundaryError,
            ) as exc:
                resolution_error = exc
                payload = None
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if resolution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(resolution_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/approvals/{approval_id}/execute")
def execute_approved_proxy(approval_id: UUID, request: ExecuteApprovedProxyRequest) -> JSONResponse:
    from alicebot_api import proxy_execution

    settings = get_settings()
    execution_error: Exception | None = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = proxy_execution.execute_approved_proxy_request(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ProxyExecutionRequestInput(
                        approval_id=approval_id,
                        task_run_id=request.task_run_id,
                    ),
                )
            except (
                proxy_execution.ProxyExecutionApprovalStateError,
                proxy_execution.ProxyExecutionHandlerNotFoundError,
                proxy_execution.ProxyExecutionIdempotencyError,
                TaskStepApprovalLinkageError,
                TaskStepExecutionLinkageError,
            ) as exc:
                execution_error = exc
                payload = None
    except ApprovalNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if execution_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(execution_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks")
def list_tasks(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_task_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks/{task_id}")
def get_task(task_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_id=task_id,
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/runs")
def create_task_run(task_id: UUID, request: CreateTaskRunRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_task_run_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskRunCreateInput(
                    task_id=task_id,
                    max_ticks=request.max_ticks,
                    retry_cap=request.retry_cap,
                    checkpoint=_json_object(request.checkpoint),
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskRunValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks/{task_id}/runs")
def list_task_runs(task_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_run_records(
                ContinuityStore(conn),
                user_id=user_id,
                task_id=task_id,
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-runs/{task_run_id}")
def get_task_run(task_run_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_run_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_run_id=task_run_id,
            )
    except TaskRunNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


def _mutate_task_run(
    *,
    task_run_id: UUID,
    request: MutateTaskRunRequest,
    mutation_handler: Callable[..., object],
    mutation_input_model: type[TaskRunTickInput]
    | type[TaskRunPauseInput]
    | type[TaskRunResumeInput]
    | type[TaskRunCancelInput],
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = mutation_handler(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=mutation_input_model(task_run_id=task_run_id),
            )
    except TaskRunValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except TaskRunNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskRunTransitionError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-runs/{task_run_id}/tick")
def tick_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=tick_task_run_record,
        mutation_input_model=TaskRunTickInput,
    )


@app.post("/v0/task-runs/{task_run_id}/pause")
def pause_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=pause_task_run_record,
        mutation_input_model=TaskRunPauseInput,
    )


@app.post("/v0/task-runs/{task_run_id}/resume")
def resume_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=resume_task_run_record,
        mutation_input_model=TaskRunResumeInput,
    )


@app.post("/v0/task-runs/{task_run_id}/cancel")
def cancel_task_run(task_run_id: UUID, request: MutateTaskRunRequest) -> JSONResponse:
    return _mutate_task_run(
        task_run_id=task_run_id,
        request=request,
        mutation_handler=cancel_task_run_record,
        mutation_input_model=TaskRunCancelInput,
    )


@app.post("/v0/gmail-accounts")
def connect_gmail_account(request: ConnectGmailAccountRequest) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_gmail_secret_manager(settings.gmail_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_gmail_account_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=GmailAccountConnectInput(
                    provider_account_id=request.provider_account_id,
                    email_address=request.email_address,
                    display_name=request.display_name,
                    scope=request.scope,
                    access_token=request.access_token,
                    refresh_token=request.refresh_token,
                    client_id=request.client_id,
                    client_secret=request.client_secret,
                    access_token_expires_at=request.access_token_expires_at,
                ),
            )
    except GmailCredentialValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except GmailCredentialPersistenceError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except GmailAccountAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/gmail-accounts")
def list_gmail_accounts(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_gmail_account_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/gmail-accounts/{gmail_account_id}")
def get_gmail_account(gmail_account_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_gmail_account_record(
                ContinuityStore(conn),
                user_id=user_id,
                gmail_account_id=gmail_account_id,
            )
    except GmailAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/gmail-accounts/{gmail_account_id}/messages/{provider_message_id}/ingest")
def ingest_gmail_message(
    gmail_account_id: UUID,
    provider_message_id: str,
    request: IngestGmailMessageRequest,
) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_gmail_secret_manager(settings.gmail_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = ingest_gmail_message_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=GmailMessageIngestInput(
                    gmail_account_id=gmail_account_id,
                    task_workspace_id=request.task_workspace_id,
                    provider_message_id=provider_message_id,
                ),
            )
    except GmailAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except GmailMessageNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except GmailMessageUnsupportedError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (
        GmailCredentialNotFoundError,
        GmailCredentialInvalidError,
        GmailCredentialPersistenceError,
    ) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (GmailMessageFetchError, GmailCredentialRefreshError) as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
    except TaskArtifactAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/calendar-accounts")
def connect_calendar_account(request: ConnectCalendarAccountRequest) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_calendar_secret_manager(settings.calendar_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_calendar_account_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=CalendarAccountConnectInput(
                    provider_account_id=request.provider_account_id,
                    email_address=request.email_address,
                    display_name=request.display_name,
                    scope=request.scope,
                    access_token=request.access_token,
                ),
            )
    except CalendarCredentialValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except CalendarCredentialPersistenceError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except CalendarAccountAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/calendar-accounts")
def list_calendar_accounts(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_calendar_account_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/calendar-accounts/{calendar_account_id}")
def get_calendar_account(calendar_account_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_calendar_account_record(
                ContinuityStore(conn),
                user_id=user_id,
                calendar_account_id=calendar_account_id,
            )
    except CalendarAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/calendar-accounts/{calendar_account_id}/events")
def list_calendar_events(
    calendar_account_id: UUID,
    user_id: UUID,
    limit: int = Query(default=DEFAULT_CALENDAR_EVENT_LIST_LIMIT, ge=1, le=MAX_CALENDAR_EVENT_LIST_LIMIT),
    time_min: datetime | None = Query(default=None),
    time_max: datetime | None = Query(default=None),
) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_calendar_secret_manager(settings.calendar_secret_manager_url)

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_calendar_event_records(
                ContinuityStore(conn),
                secret_manager,
                user_id=user_id,
                request=CalendarEventListInput(
                    calendar_account_id=calendar_account_id,
                    limit=limit,
                    time_min=time_min,
                    time_max=time_max,
                ),
            )
    except CalendarAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except (
        CalendarCredentialNotFoundError,
        CalendarCredentialInvalidError,
        CalendarCredentialPersistenceError,
    ) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except CalendarEventListValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except CalendarEventFetchError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/calendar-accounts/{calendar_account_id}/events/{provider_event_id}/ingest")
def ingest_calendar_event(
    calendar_account_id: UUID,
    provider_event_id: str,
    request: IngestCalendarEventRequest,
) -> JSONResponse:
    settings = get_settings()
    secret_manager = build_calendar_secret_manager(settings.calendar_secret_manager_url)

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = ingest_calendar_event_record(
                ContinuityStore(conn),
                secret_manager,
                user_id=request.user_id,
                request=CalendarEventIngestInput(
                    calendar_account_id=calendar_account_id,
                    task_workspace_id=request.task_workspace_id,
                    provider_event_id=provider_event_id,
                ),
            )
    except CalendarAccountNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except CalendarEventNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except CalendarEventUnsupportedError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (
        CalendarCredentialNotFoundError,
        CalendarCredentialInvalidError,
        CalendarCredentialPersistenceError,
    ) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except CalendarEventFetchError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
    except TaskArtifactAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/workspace")
def create_task_workspace(task_id: UUID, request: CreateTaskWorkspaceRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_task_workspace_record(
                ContinuityStore(conn),
                settings=settings,
                user_id=request.user_id,
                request=TaskWorkspaceCreateInput(
                    task_id=task_id,
                    status="active",
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except (TaskWorkspaceAlreadyExistsError, TaskWorkspaceProvisioningError) as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-workspaces")
def list_task_workspaces(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_task_workspace_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-workspaces/{task_workspace_id}")
def get_task_workspace(task_workspace_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_workspace_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_workspace_id=task_workspace_id,
            )
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tasks/{task_id}/steps")
def list_task_steps(task_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_step_records(
                ContinuityStore(conn),
                user_id=user_id,
                task_id=task_id,
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-steps/{task_step_id}")
def get_task_step(task_step_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_step_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_step_id=task_step_id,
            )
    except TaskStepNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-workspaces/{task_workspace_id}/artifacts")
def register_task_artifact(
    task_workspace_id: UUID,
    request: RegisterTaskArtifactRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = register_task_artifact_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskArtifactRegisterInput(
                    task_workspace_id=task_workspace_id,
                    local_path=request.local_path,
                    media_type_hint=request.media_type_hint,
                ),
            )
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except TaskArtifactAlreadyExistsError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts")
def list_task_artifacts(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_task_artifact_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts/{task_artifact_id}")
def get_task_artifact(task_artifact_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_artifact_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_id=task_artifact_id,
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifacts/{task_artifact_id}/ingest")
def ingest_task_artifact(
    task_artifact_id: UUID,
    request: IngestTaskArtifactRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = ingest_task_artifact_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskArtifactIngestInput(task_artifact_id=task_artifact_id),
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskWorkspaceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts/{task_artifact_id}/chunks")
def list_task_artifact_chunks(task_artifact_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_id=task_artifact_id,
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/artifact-chunks/retrieve")
def retrieve_task_artifact_chunks(
    task_id: UUID,
    request: RetrieveArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_task_scoped_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskScopedArtifactChunkRetrievalInput(
                    task_id=task_id,
                    query=request.query,
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifacts/{task_artifact_id}/chunks/retrieve")
def retrieve_task_artifact_chunks_for_artifact(
    task_artifact_id: UUID,
    request: RetrieveArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_artifact_scoped_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ArtifactScopedArtifactChunkRetrievalInput(
                    task_artifact_id=task_artifact_id,
                    query=request.query,
                ),
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/artifact-chunks/semantic-retrieval")
def retrieve_semantic_task_artifact_chunks(
    task_id: UUID,
    request: RetrieveSemanticArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_task_scoped_semantic_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskScopedSemanticArtifactChunkRetrievalInput(
                    task_id=task_id,
                    embedding_config_id=request.embedding_config_id,
                    query_vector=tuple(request.query_vector),
                    limit=request.limit,
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except SemanticArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifacts/{task_artifact_id}/chunks/semantic-retrieval")
def retrieve_semantic_artifact_chunks_for_artifact(
    task_artifact_id: UUID,
    request: RetrieveSemanticArtifactChunksRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_artifact_scoped_semantic_artifact_chunk_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ArtifactScopedSemanticArtifactChunkRetrievalInput(
                    task_artifact_id=task_artifact_id,
                    embedding_config_id=request.embedding_config_id,
                    query_vector=tuple(request.query_vector),
                    limit=request.limit,
                ),
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except SemanticArtifactChunkRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/tasks/{task_id}/steps")
def create_next_task_step(task_id: UUID, request: CreateNextTaskStepRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_next_task_step_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskStepNextCreateInput(
                    task_id=task_id,
                    kind=request.kind,
                    status=request.status,
                    request=_task_step_request_record(request.request),
                    outcome=_task_step_outcome_snapshot(request.outcome),
                    lineage=TaskStepLineageInput(
                        parent_step_id=request.lineage.parent_step_id,
                        source_approval_id=request.lineage.source_approval_id,
                        source_execution_id=request.lineage.source_execution_id,
                    ),
                ),
            )
    except TaskNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskStepSequenceError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-steps/{task_step_id}/transition")
def transition_task_step(task_step_id: UUID, request: TransitionTaskStepRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = transition_task_step_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskStepTransitionInput(
                    task_step_id=task_step_id,
                    status=request.status,
                    outcome=_task_step_outcome_snapshot(request.outcome),
                ),
            )
    except TaskStepNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except TaskStepTransitionError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/execution-budgets")
def create_execution_budget(request: CreateExecutionBudgetRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_execution_budget_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExecutionBudgetCreateInput(
                    agent_profile_id=request.agent_profile_id,
                    tool_key=request.tool_key,
                    domain_hint=request.domain_hint,
                    max_completed_executions=request.max_completed_executions,
                    rolling_window_seconds=request.rolling_window_seconds,
                ),
            )
    except ExecutionBudgetValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/execution-budgets")
def list_execution_budgets(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_execution_budget_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/execution-budgets/{execution_budget_id}")
def get_execution_budget(execution_budget_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_execution_budget_record(
                ContinuityStore(conn),
                user_id=user_id,
                execution_budget_id=execution_budget_id,
            )
    except ExecutionBudgetNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/execution-budgets/{execution_budget_id}/deactivate")
def deactivate_execution_budget(
    execution_budget_id: UUID,
    request: DeactivateExecutionBudgetRequest,
) -> JSONResponse:
    settings = get_settings()
    lifecycle_error: ExecutionBudgetLifecycleError | None = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = deactivate_execution_budget_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ExecutionBudgetDeactivateInput(
                        thread_id=request.thread_id,
                        execution_budget_id=execution_budget_id,
                    ),
                )
            except ExecutionBudgetLifecycleError as exc:
                lifecycle_error = exc
                payload = None
    except ExecutionBudgetValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ExecutionBudgetNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if lifecycle_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(lifecycle_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/execution-budgets/{execution_budget_id}/supersede")
def supersede_execution_budget(
    execution_budget_id: UUID,
    request: SupersedeExecutionBudgetRequest,
) -> JSONResponse:
    settings = get_settings()
    lifecycle_error: ExecutionBudgetLifecycleError | None = None

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            try:
                payload = supersede_execution_budget_record(
                    ContinuityStore(conn),
                    user_id=request.user_id,
                    request=ExecutionBudgetSupersedeInput(
                        thread_id=request.thread_id,
                        execution_budget_id=execution_budget_id,
                        max_completed_executions=request.max_completed_executions,
                    ),
                )
            except ExecutionBudgetLifecycleError as exc:
                lifecycle_error = exc
                payload = None
    except ExecutionBudgetValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ExecutionBudgetNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    if lifecycle_error is not None:
        return JSONResponse(status_code=409, content={"detail": str(lifecycle_error)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tool-executions")
def list_tool_executions(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_tool_execution_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tool-executions/{execution_id}")
def get_tool_execution(execution_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_tool_execution_record(
                ContinuityStore(conn),
                user_id=user_id,
                execution_id=execution_id,
            )
    except ToolExecutionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/tools/{tool_id}")
def get_tool(tool_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_tool_record(
                ContinuityStore(conn),
                user_id=user_id,
                tool_id=tool_id,
            )
    except ToolNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/extract-explicit-preferences")
def extract_explicit_preferences(request: ExtractExplicitPreferencesRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = extract_and_admit_explicit_preferences(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExplicitPreferenceExtractionRequestInput(
                    source_event_id=request.source_event_id,
                ),
            )
    except ExplicitPreferenceExtractionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/open-loops/extract-explicit-commitments")
def extract_explicit_commitments(request: ExtractExplicitCommitmentsRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = extract_and_admit_explicit_commitments(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExplicitCommitmentExtractionRequestInput(
                    source_event_id=request.source_event_id,
                ),
            )
    except ExplicitCommitmentExtractionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/capture-explicit-signals")
def capture_explicit_signals(request: CaptureExplicitSignalsRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = extract_and_admit_explicit_signals(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ExplicitSignalCaptureRequestInput(
                    source_event_id=request.source_event_id,
                ),
            )
    except ExplicitSignalCaptureValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryAdmissionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/captures")
def create_continuity_capture(request: ContinuityCaptureRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = capture_continuity_input(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ContinuityCaptureCreateInput(
                    raw_content=request.raw_content,
                    explicit_signal=request.explicit_signal,
                ),
            )
    except (ContinuityCaptureValidationError, ContinuityObjectValidationError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/workspace")
def get_vnext_workspace(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = _vnext_workspace_payload(PostgresVNextStore(conn))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/sources")
def create_vnext_source(
    request: VNextSourceCaptureRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="source.capture",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")
            capture_result = VNextCaptureService(
                store,
                actor_type=actor_type,
                actor_id=actor_id,
                trace_id=request.trace_id or decision.trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
                agent_identity=identity.to_record() if identity is not None else None,
                policy_decision=decision.to_record(),
                defer_embeddings=True,
            ).capture_text(
                request.raw_text,
                title=request.title,
                domain=request.domain,
                sensitivity=request.sensitivity,
                project_scope=decision.effective_project_scope,
            )
            payload = capture_result.to_record()
            if identity is not None:
                append_policy_events(
                    store,
                    identity=identity,
                    decision=decision,
                    target_type="source",
                    target_id=str(payload.get("source_id")),
                )
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=capture_result,
            actor_type=actor_type,
            actor_id=actor_id,
            trace_id=request.trace_id or decision.trace_id,
        )
    except VNextCaptureValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext source capture request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/projects")
def create_vnext_project(request: VNextProjectCreateRequest) -> JSONResponse:
    settings = get_settings()
    slug = request.slug or _vnext_slug(request.name)

    with user_connection(settings.database_url, request.user_id) as conn:
        payload = PostgresVNextStore(conn).create_project(
            {
                "name": request.name.strip(),
                "slug": slug,
                "status": request.status,
                "description": request.description,
                "current_state": request.current_state,
                "domain": request.domain,
                "sensitivity": request.sensitivity,
                "metadata_json": {"created_from": "vnext_workspace"},
            },
            actor_type="user",
        )

    return JSONResponse(status_code=201, content=jsonable_encoder({"project": payload}))


@app.get("/v0/vnext/projects")
def list_vnext_projects(user_id: UUID, status: str | None = "active", limit: int = 20) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).list_projects(status=status, limit=limit)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"items": payload, "count": len(payload), "order": ["updated_at_desc", "id_desc"]}),
    )


@app.get("/v0/vnext/connectors")
def list_vnext_connectors(user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        service = VNextConnectorService(PostgresVNextStore(conn))
        definitions = list_connector_definitions()
        payload = {
            "items": [
                {
                    **definition.to_record(),
                    "config": service.get_config(definition.name),
                    "health": service.connector_health(definition.name),
                }
                for definition in definitions
            ],
            "count": len(definitions),
            "order": [definition.name for definition in definitions],
        }
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/connectors/health")
def get_vnext_connectors_health(user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextConnectorService(PostgresVNextStore(conn)).connector_health_all()
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/connectors/{connector_name}/status")
def get_vnext_connector_status(connector_name: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, user_id) as conn:
            store = PostgresVNextStore(conn)
            service = VNextConnectorService(store)
            sources = [
                source for source in store.list_sources(limit=50) if source.get("connector_name") == connector_name
            ]
            failures = [
                event
                for event in store.list_events(target_type="connector", target_id=connector_name, limit=50)
                if event.get("event_type") in {"connector.item_failed", "connector.sync_failed"}
            ]
            payload = {
                "config": service.get_config(connector_name),
                "health": service.connector_health(connector_name),
                "recent_captures": sources[:10],
                "recent_failures": failures[:10],
            }
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=404, detail="vNext connector was not found")
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.patch("/v0/vnext/connectors/{connector_name}/config")
def update_vnext_connector_config(connector_name: str, request: VNextConnectorConfigRequest) -> JSONResponse:
    settings = get_settings()
    if connector_name == "telegram" and (
        request.secret_ref is not None
        or request.poll_interval_seconds is not None
        or request.sync_mode not in {None, "on_demand"}
    ):
        return _vnext_public_error_response(
            status_code=400,
            detail="Telegram source ingestion is on-demand and does not accept polling or secret configuration",
        )
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextConnectorService(PostgresVNextStore(conn)).update_config(
                connector_name,
                enabled=request.enabled,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
                secret_ref=request.secret_ref,
                sync_mode=request.sync_mode,
                poll_interval_seconds=request.poll_interval_seconds,
                config_json=request.config_json,
            )
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext connector config request is invalid")
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/connectors/{connector_name}/sync")
def sync_vnext_connector(connector_name: str, request: VNextConnectorSyncRequest) -> JSONResponse:
    settings = get_settings()
    if connector_name == "telegram":
        return _vnext_public_error_response(
            status_code=400,
            detail="use /v0/vnext/connectors/telegram/sync for allowlist-aware Telegram ingestion",
        )

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            result = VNextConnectorService(PostgresVNextStore(conn), defer_embeddings=True).sync_items(
                connector_name,
                request.items,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
            )
            payload = result.to_record()
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=result,
        )
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext connector sync request is invalid")

    status_code = 201
    if payload["status"] == "partial":
        status_code = 207
    elif payload["status"] == "failed":
        status_code = 400
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


@app.post("/v0/vnext/connectors/telegram/sync")
def sync_vnext_telegram_connector(request: VNextTelegramSyncRequest) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            service = VNextConnectorService(PostgresVNextStore(conn), defer_embeddings=True)
            result = service.sync_telegram_updates(
                request.updates,
                allowed_chat_ids=request.allowed_chat_ids,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
            )
            payload = result.to_record()
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=result,
        )
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext Telegram sync request is invalid")
    return JSONResponse(
        status_code=201 if payload["status"] in {"ok", "partial"} else 400, content=jsonable_encoder(payload)
    )


@app.post("/v0/vnext/connectors/local-folder/sync")
def sync_vnext_local_folder_connector(request: VNextLocalFolderSyncRequest) -> JSONResponse:
    settings = get_settings()
    try:
        paths = list(request.paths)
        with user_connection(settings.database_url, request.user_id) as conn:
            if not paths:
                config = VNextConnectorService(PostgresVNextStore(conn)).get_config("local_folder")
                config_json_value = config.get("config_json")
                config_json: dict[str, object] = config_json_value if isinstance(config_json_value, dict) else {}
                configured_paths_value = config_json.get("paths")
                configured_paths = configured_paths_value if isinstance(configured_paths_value, list) else []
                paths = [str(path) for path in configured_paths if isinstance(path, str)]

        # File traversal and reads are intentionally outside the transaction so
        # slow or remote mounts cannot monopolize a pooled database connection.
        scan = scan_local_folder(
            paths,
            recursive=request.recursive,
            extensions=request.extensions,
            ignore_patterns=request.ignore_patterns,
        )
        with user_connection(settings.database_url, request.user_id) as conn:
            result = VNextConnectorService(PostgresVNextStore(conn), defer_embeddings=True).sync_local_folder_scan(
                scan,
                default_domain=request.default_domain,
                default_sensitivity=request.default_sensitivity,
            )
            payload = result.to_record()
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=result,
        )
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext local folder sync request is invalid")
    return JSONResponse(
        status_code=201 if payload["status"] in {"ok", "partial", "duplicate"} else 400,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/connectors/browser-clipper/capture")
def capture_vnext_browser_clip(request: VNextBrowserClipperCaptureRequest) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            result = VNextConnectorService(PostgresVNextStore(conn), defer_embeddings=True).capture_browser_clip(
                request.model_dump(mode="json"),
                default_domain=request.domain,
                default_sensitivity=request.sensitivity,
            )
            payload = result.to_record()
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=result,
        )
    except VNextConnectorValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext browser clip capture request is invalid")
    return JSONResponse(
        status_code=201 if payload["status"] in {"ok", "partial", "duplicate"} else 400,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/agents/ingest-output")
def ingest_vnext_agent_output(
    request: VNextAgentOutputIngestRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            _vnext_agent_record(store, identity)
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="source.capture",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
                target_type="connector",
                target_id="agent_output",
                write_policy="proposal_only" if request.propose_memory else None,
            )
            ingest_payload = request.model_dump(mode="json")
            ingest_payload["project_scope"] = list(decision.effective_project_scope)
            result = VNextConnectorService(store, defer_embeddings=True).ingest_agent_output(
                ingest_payload,
                policy_decision=decision.to_record(),
            )
            payload = result.to_record()
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=result,
            actor_type="agent",
            actor_id=identity.agent_id if identity is not None else None,
            trace_id=decision.trace_id,
        )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except (AgentIdentityValidationError, VNextConnectorValidationError):
        return _vnext_public_error_response(status_code=400, detail="vNext agent output ingest request is invalid")
    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v0/vnext/dogfooding")
def get_vnext_dogfooding_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextDogfoodingService(PostgresVNextStore(conn)).dashboard()
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/doctor")
def get_vnext_doctor(user_id: UUID, ci: bool = True) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextDoctorService(PostgresVNextStore(conn)).run(ci=ci)
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/doctor/run")
def run_vnext_doctor(request: VNextDoctorRunRequest) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, request.user_id) as conn:
        payload = VNextDoctorService(PostgresVNextStore(conn)).run(fix_safe=request.fix_safe, ci=request.ci)
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/artifacts/{artifact_id}/insight-feedback")
def record_vnext_artifact_insight_feedback(
    artifact_id: UUID,
    request: VNextArtifactInsightFeedbackRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            _artifact, _decision = _vnext_authorized_artifact(
                store=store,
                identity=identity,
                artifact_id=str(artifact_id),
                action="artifact.feedback",
                for_update=True,
            )
            actor_type, actor_id = _vnext_agent_actor(identity)
            payload = VNextDogfoodingService(store).record_insight_feedback(
                artifact_id=str(artifact_id),
                useful_insight=request.useful_insight,
                surfaced_missed=request.surfaced_missed,
                comments=request.comments,
                actor_type=actor_type,
                actor_id=actor_id,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except ValueError:
        return _vnext_public_error_response(
            status_code=400, detail="vNext artifact insight feedback request is invalid"
        )
    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v0/vnext/sources/{source_id}")
def get_vnext_source(source_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).get_source(str(source_id))

    if payload is None:
        return JSONResponse(status_code=404, content={"detail": f"vNext source {source_id} was not found"})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/sources/{source_id}/review")
def review_vnext_source(source_id: UUID, request: VNextSourceReviewRequest) -> JSONResponse:
    settings = get_settings()
    action = request.action.strip().casefold()
    if action not in {"review", "update", "assign_project", "archive"}:
        return _vnext_public_error_response(status_code=400, detail="vNext source review action is invalid")

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            existing = store.get_source(str(source_id))
            if existing is None:
                return _vnext_public_error_response(status_code=404, detail="vNext source was not found")
            if action == "archive":
                archived = store.delete_source(source_id=str(source_id), actor_type="user")
                append_event(
                    store,
                    event_type="source.archived",
                    actor_type="user",
                    target_type="source",
                    target_id=str(source_id),
                    payload={"action": action, "review_note": request.review_note},
                )
                trace = _vnext_load_source_trace(
                    store=store,
                    source=archived,
                )
                return JSONResponse(
                    status_code=200,
                    content=jsonable_encoder({"source": archived, "archived": True, "trace": trace}),
                )

            if action == "assign_project" and request.project_id is None:
                return _vnext_public_error_response(status_code=400, detail="project_id is required")

            metadata = {
                **_vnext_metadata(existing),
                "review_status": "reviewed" if action == "review" else "updated",
                "reviewed_at": datetime.now(UTC).isoformat(),
                "review_note": request.review_note,
                "updated_from": "vnext_workspace",
            }
            if request.project_id is not None:
                metadata["project_id"] = request.project_id
                if action == "assign_project":
                    # project_scope is the canonical, overlap-aware scope used by
                    # retrieval.  Replace it together with the singular legacy
                    # pointer so a reassignment cannot leave the source readable
                    # through its previous project.
                    metadata["project_scope"] = [request.project_id]
            patch: dict[str, object] = {"metadata_json": metadata}
            if request.title is not None:
                patch["title"] = request.title
            if request.domain is not None:
                patch["domain"] = request.domain
            if request.sensitivity is not None:
                patch["sensitivity"] = request.sensitivity
            updated = store.update_source(source_id=str(source_id), patch=patch, actor_type="user")
            if action == "assign_project":
                store.create_edge(
                    {
                        "from_type": "source",
                        "from_id": str(source_id),
                        "to_type": "project",
                        "to_id": request.project_id,
                        "edge_type": "belongs_to_project",
                        "confidence": 1.0,
                        "explanation": "Assigned from live /vnext source review.",
                        "created_by": "user",
                        "metadata_json": {"review_action": action},
                    },
                    actor_type="user",
                )
            append_event(
                store,
                event_type={
                    "review": "source.reviewed",
                    "update": "source.updated_from_workspace",
                    "assign_project": "source.assigned_project",
                }[action],
                actor_type="user",
                target_type="source",
                target_id=str(source_id),
                payload={"action": action, "project_id": request.project_id, "review_note": request.review_note},
            )
            trace = _vnext_load_source_trace(
                store=store,
                source=updated,
            )
    except ContinuityStoreInvariantError as exc:
        return _vnext_public_error_response(status_code=409, detail=str(exc))

    return JSONResponse(
        status_code=200, content=jsonable_encoder({"source": updated, "archived": False, "trace": trace})
    )


@app.get("/v0/vnext/traces/sources/{source_id}")
def get_vnext_source_trace(source_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.get_source(str(source_id))
        if source is None:
            return _vnext_public_error_response(status_code=404, detail="vNext source was not found")
        payload = _vnext_load_source_trace(
            store=store,
            source=source,
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/traces/artifacts/{artifact_id}")
def get_vnext_artifact_trace(
    artifact_id: UUID,
    user_id: UUID,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = resolve_protected_agent_identity(
                store,
                user_id=user_id,
                raw_key=agent_key_from_authorization(authorization),
                payload={},
            )
            artifact, _decision = _vnext_authorized_artifact(
                store=store,
                identity=identity,
                artifact_id=str(artifact_id),
                action="artifact.lookup",
                for_update=False,
            )
            metadata = _vnext_metadata(artifact)
            source_refs = _vnext_ref_values(metadata.get("source_refs")) + _vnext_ref_values(metadata.get("source_ids"))
            source_ids: list[str] = []
            for source_ref in source_refs:
                source_id = source_ref.removeprefix("source:")
                try:
                    UUID(source_id)
                except ValueError:
                    continue
                if source_id not in source_ids:
                    source_ids.append(source_id)
            authorized_sources: list[dict[str, object]] = []
            for source in store.get_sources_by_ids(source_ids):
                source_id = str(source.get("id"))
                source_decision = _vnext_exact_resource_policy(
                    identity=identity,
                    action="artifact.lookup",
                    resource=source,
                    source_resource=True,
                )
                append_policy_events(
                    store,
                    identity=identity,
                    decision=source_decision,
                    target_type="source",
                    target_id=source_id,
                )
                if source_decision.decision != "blocked":
                    authorized_sources.append(source)
            payload = _vnext_artifact_trace(
                artifact=artifact,
                sources=authorized_sources,
                quality_evals=store.list_artifact_quality_ratings(artifact_id=str(artifact_id), limit=100),
                events=store.list_events(
                    target_type="artifact",
                    target_id=str(artifact_id),
                    limit=100,
                ),
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.delete("/v0/vnext/sources/{source_id}")
def delete_vnext_source(source_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        existing = store.get_source(str(source_id))
        if existing is None:
            return JSONResponse(status_code=404, content={"detail": f"vNext source {source_id} was not found"})
        payload = store.delete_source(source_id=str(source_id))

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/context-packs")
def create_vnext_context_pack(
    request: VNextContextPackRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    scope = request.scope
    options = request.options
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        requested_domains = _vnext_string_list(scope, "domains")
        requested_sensitivity = _vnext_string_list(options, "sensitivity_allowed") or (
            "public",
            "internal",
            "private",
            "unknown",
        )
        # Only forwarded when the caller sets them, so the retrieval request
        # dataclass stays the source of truth for the tier defaults.
        tuning_kwargs: dict[str, object] = {}
        context_depth = _vnext_text_option(options, "context_depth")
        if context_depth is not None:
            tuning_kwargs["context_depth"] = context_depth
        budget_strategy = _vnext_text_option(options, "budget_strategy")
        if budget_strategy is not None:
            tuning_kwargs["budget_strategy"] = budget_strategy
        retrieval_request = VNextRetrievalRequest(
            query=request.query,
            domains=requested_domains,
            projects=_vnext_string_list(scope, "projects"),
            people=_vnext_string_list(scope, "people"),
            time_window=str(scope.get("time_window", "all")),
            sensitivity_allowed=requested_sensitivity,
            # Tri-state: absent means "let the context_depth tier decide";
            # an explicit true/false always wins.
            include_sources=_vnext_optional_bool(options, "include_sources"),
            include_contradictions=_vnext_optional_bool(options, "include_contradictions"),
            max_items=_vnext_int(options, "max_items", 8),
            max_tokens=_vnext_int(options, "max_tokens", 8000),
            **tuning_kwargs,  # type: ignore[arg-type]
        )
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="context_pack.request",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="system")
            payload = VNextRetrievalService(store).compile_context_pack(
                VNextRetrievalRequest(
                    query=retrieval_request.query,
                    domains=decision.effective_domains,
                    projects=decision.effective_project_scope,
                    people=retrieval_request.people,
                    time_window=retrieval_request.time_window,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    include_sources=retrieval_request.include_sources,
                    include_contradictions=retrieval_request.include_contradictions,
                    context_depth=retrieval_request.context_depth,
                    budget_strategy=retrieval_request.budget_strategy,
                    max_items=retrieval_request.max_items,
                    max_tokens=retrieval_request.max_tokens,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                    trace_id=request.trace_id or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                )
            )
    except VNextRetrievalValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext context-pack request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/context-tree")
def get_vnext_context_tree(
    user_id: UUID,
    query: str = "",
    domains: Annotated[list[str] | None, Query()] = None,
    sensitivity_allowed: Annotated[list[str] | None, Query()] = None,
    limit: int = 12,
    include_events: bool = True,
) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, user_id) as conn:
            store = PostgresVNextStore(conn)
            payload = VNextContextTreeService(cast(VNextContextTreeStore, store)).build_tree(
                ContextTreeRequest(
                    query=query,
                    domains=tuple(domains or ()),
                    sensitivity_allowed=tuple(sensitivity_allowed or ("public", "internal", "private", "unknown")),
                    limit=limit,
                    include_events=include_events,
                    generated_by="user",
                )
            )
    except VNextContextTreeValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/{memory_id}/review")
def review_vnext_memory(
    memory_id: UUID,
    request: VNextMemoryReviewRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    action = request.action.strip().casefold()
    if action not in {"accept", "edit", "reject", "private", "assign_project", "promote"}:
        return _vnext_public_error_response(status_code=400, detail="vNext memory review action is invalid")

    try:
        _vnext_agent_identity(request)
        with user_connection(settings.database_url, request.user_id) as conn:
            auth_store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                auth_store,
                request,
                user_id=request.user_id,
                authorization=authorization,
            )
            target = auth_store.get_memory(str(memory_id))
            if target is None:
                return _vnext_public_error_response(status_code=404, detail="vNext memory was not found")
            target_scope = resource_project_scope(target)
            if action == "assign_project" and request.project_id is not None:
                target_scope = tuple(dict.fromkeys((*target_scope, request.project_id)))
            decision = _vnext_policy_checked(
                store=auth_store,
                identity=identity,
                action="memory.review",
                domains=(str(target.get("domain") or "unknown"),),
                sensitivity_allowed=(str(target.get("sensitivity") or "unknown"),),
                project_scope=target_scope,
                target_type="memory",
                target_id=str(memory_id),
                require_explicit_project_scope=True,
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)

    actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")

    # Consolidation acceptance has its own graph-wide locking protocol. Run it
    # in a complete primary transaction, then perform optional embedding work
    # only after that transaction has committed.
    if is_pending_consolidation_candidate(target) and action in {"accept", "promote"}:
        if action == "edit" or any(
            value is not None
            for value in (
                request.title,
                request.canonical_text,
                request.summary,
                request.domain,
                request.sensitivity,
                request.project_id,
            )
        ):
            return _vnext_public_error_response(
                status_code=400,
                detail=(
                    "pending consolidation candidates cannot be edited during approval; "
                    "regenerate the candidate or accept it unchanged"
                ),
            )
        try:
            with user_connection(settings.database_url, request.user_id) as conn:
                consolidation_service = VNextMemoryCommitService(
                    PostgresVNextStore(conn),
                    defer_embeddings=True,
                )
                # Preserve the route-level graph boundary before the service
                # reacquires it and locks the candidate/member rows.
                consolidation_service.lock_supersession_graph()
                acceptance = consolidation_service.accept_consolidation_candidate(
                    str(memory_id),
                    reason=request.reason or "Approved through vNext memory review.",
                    identity=identity,
                )
        except AgentPolicyBlockedError as exc:
            return _vnext_permission_response(exc.decision)
        except VNextMemoryCommitValidationError as exc:
            return _vnext_public_error_response(status_code=400, detail=str(exc))
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=consolidation_service,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "memory": acceptance["memory"],
                    "consolidation_acceptance": acceptance,
                }
            ),
        )

    with user_connection(settings.database_url, request.user_id) as conn:
        store = PostgresVNextStore(conn)
        memory_service = VNextMemoryCommitService(store, defer_embeddings=True)
        # Review can promote a consolidation candidate or mutate a member
        # referenced by pending derived work. Establish the shared per-user
        # graph boundary before the route takes any candidate/member row lock;
        # delegated service calls may safely reacquire the transaction lock.
        memory_service.lock_supersession_graph()
        preview = store.get_memory(str(memory_id))
        if preview is None:
            return _vnext_public_error_response(status_code=404, detail="vNext memory was not found")
        # Delegate consolidation approval before this adapter takes a row lock.
        # The service reacquires the already-held transaction advisory lock
        # (non-blocking/re-entrant) and then owns all candidate/member locks.
        if is_pending_consolidation_candidate(preview):
            if action == "edit" or any(
                value is not None
                for value in (
                    request.title,
                    request.canonical_text,
                    request.summary,
                    request.domain,
                    request.sensitivity,
                    request.project_id,
                )
            ):
                return _vnext_public_error_response(
                    status_code=400,
                    detail=(
                        "pending consolidation candidates cannot be edited during approval; "
                        "regenerate the candidate or accept it unchanged"
                    ),
                )
            if action in {"accept", "promote"}:
                return _vnext_public_error_response(
                    status_code=409,
                    detail="vNext memory became a consolidation candidate during review; retry the approval",
                )
        get_memory_for_update = getattr(store, "get_memory_for_update", None)
        existing = (
            get_memory_for_update(str(memory_id))
            if callable(get_memory_for_update)
            else store.get_memory(str(memory_id))
        )
        if existing is None:
            return _vnext_public_error_response(status_code=404, detail="vNext memory was not found")
        # Re-authorize the locked record so a concurrent reassignment cannot
        # move it outside the bound agent project between the first check and
        # this mutation.
        locked_scope = resource_project_scope(existing)
        if action == "assign_project" and request.project_id is not None:
            locked_scope = tuple(dict.fromkeys((*locked_scope, request.project_id)))
        locked_decision = _vnext_policy_checked(
            store=store,
            identity=identity,
            action="memory.review",
            domains=(str(existing.get("domain") or "unknown"),),
            sensitivity_allowed=(str(existing.get("sensitivity") or "unknown"),),
            project_scope=locked_scope,
            target_type="memory",
            target_id=str(memory_id),
            require_explicit_project_scope=True,
        )
        if locked_decision.decision == "blocked":
            return _vnext_permission_response(locked_decision)
        if str(existing.get("status") or "") in {"archived", "rejected", "superseded"}:
            return _vnext_public_error_response(
                status_code=409,
                detail=f"vNext memory cannot be reviewed from status '{existing.get('status')}'",
            )
        if is_pending_consolidation_candidate(existing):
            if action == "edit" or any(
                value is not None
                for value in (
                    request.title,
                    request.canonical_text,
                    request.summary,
                    request.domain,
                    request.sensitivity,
                    request.project_id,
                )
            ):
                return _vnext_public_error_response(
                    status_code=400,
                    detail=(
                        "pending consolidation candidates cannot be edited during approval; "
                        "regenerate the candidate or accept it unchanged"
                    ),
                )
            if action in {"accept", "promote"}:
                return _vnext_public_error_response(
                    status_code=409,
                    detail="vNext memory became a consolidation candidate during review; retry the approval",
                )

        existing_metadata_value = existing.get("metadata_json")
        existing_metadata: dict[str, object] = (
            existing_metadata_value if isinstance(existing_metadata_value, dict) else {}
        )
        reviewed_at = datetime.now(UTC).isoformat()
        patch: dict[str, object] = {
            "last_reviewed_at": reviewed_at,
        }
        revision_type = "edited"
        if action == "accept":
            patch["status"] = "active"
            revision_type = "promoted"
        elif action == "reject":
            patch["status"] = "rejected"
            patch["metadata_json"] = _vnext_terminal_review_metadata(
                existing_metadata,
                outcome="rejected",
                terminal_at=reviewed_at,
            )
            revision_type = "rejected"
        elif action == "private":
            patch["status"] = "private_only"
            patch["sensitivity"] = "private"
        elif action == "promote":
            patch["status"] = "active"
            patch["confirmation_status"] = "confirmed"
            revision_type = "promoted"
        elif action == "assign_project":
            if request.project_id is None:
                return _vnext_public_error_response(status_code=400, detail="project_id is required")
            # Keep every current scope representation in the same UPDATE.  A
            # metadata-only project_id write leaves an older project_scope in
            # place, and canonical retrieval correctly gives that array
            # precedence over the legacy singular fallback.
            patch["project_id"] = request.project_id
            patch["metadata_json"] = {
                **existing_metadata,
                "project_id": request.project_id,
                "project_scope": [request.project_id],
                "assigned_from": "vnext_workspace",
            }
        else:
            patch["status"] = "active"

        if action in {"accept", "edit", "promote"}:
            patch.update(
                {
                    "confirmation_status": "confirmed",
                    "last_confirmed_at": reviewed_at,
                    "metadata_json": _vnext_terminal_review_metadata(
                        existing_metadata,
                        outcome="confirmed",
                        terminal_at=reviewed_at,
                    ),
                }
            )

        if request.title is not None:
            patch["title"] = request.title
        if request.canonical_text is not None:
            patch["canonical_text"] = request.canonical_text
            existing_value = existing.get("value")
            patch["value"] = {
                **(existing_value if isinstance(existing_value, dict) else {}),
                "text": request.canonical_text,
            }
            # Capture-generated title/summary are denormalized views of the
            # canonical text.  Editing only the body must not leave those
            # user-visible fields describing the pre-edit value.
            if request.title is None:
                patch["title"] = (
                    request.canonical_text
                    if len(request.canonical_text) <= 120
                    else request.canonical_text[:117].rstrip() + "..."
                )
            if request.summary is None:
                patch["summary"] = (
                    request.canonical_text
                    if len(request.canonical_text) <= 280
                    else request.canonical_text[:277].rstrip() + "..."
                )
        if request.summary is not None:
            patch["summary"] = request.summary
        if request.domain is not None:
            patch["domain"] = request.domain
        if request.sensitivity is not None:
            patch["sensitivity"] = request.sensitivity

        updated = store.update_memory(memory_id=str(memory_id), patch=patch, actor_type=actor_type)
        if action in ("accept", "edit", "promote"):
            memory_service.refresh_memory_derived_state(
                updated,
                identity=identity,
                stage=f"http_review_{action}",
            )
        if action == "assign_project" and request.project_id is not None:
            store.create_edge(
                {
                    "from_type": "memory",
                    "from_id": str(memory_id),
                    "to_type": "project",
                    "to_id": request.project_id,
                    "edge_type": "belongs_to_project",
                    "confidence": 1.0,
                    "explanation": "Assigned from live /vnext memory review.",
                    "created_by": "user",
                    "metadata_json": {"review_action": action},
                },
                actor_type=actor_type,
            )
        store.append_revision(
            {
                "memory_id": str(memory_id),
                "memory_key": str(updated["memory_key"]),
                "previous_value": existing.get("value"),
                "new_value": updated.get("value"),
                "source_event_ids": updated.get("source_event_ids"),
                "revision_type": revision_type,
                "action": f"memory_review_{action}",
                "text_before": existing.get("canonical_text"),
                "text_after": str(updated.get("canonical_text", "")),
                "reason": request.reason or f"vNext workspace memory review action: {action}",
                "actor_type": actor_type,
                "actor_id": actor_id,
                "metadata_json": {"action": action, "project_id": request.project_id},
            },
            actor_type=actor_type,
        )
        review_event = {
            "accept": "review.item_accepted",
            "promote": "review.item_accepted",
            "reject": "review.item_rejected",
            "edit": "review.item_edited",
            "private": "review.item_edited",
            "assign_project": "review.item_edited",
        }[action]
        append_event(
            store,
            event_type=review_event,
            actor_type=actor_type,
            actor_id=actor_id,
            target_type="memory",
            target_id=str(memory_id),
            payload={"action": action, "project_id": request.project_id},
        )

    _persist_vnext_deferred_embeddings(
        database_url=settings.database_url,
        user_id=request.user_id,
        result=memory_service,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return JSONResponse(status_code=200, content=jsonable_encoder({"memory": updated}))


def _vnext_memory_type_for_proposal(proposal_type: str) -> str:
    mapping = {
        "candidate_memory": "semantic",
        "project_update": "project_state",
        "open_loop": "open_loop",
        "belief_update": "belief",
        "contradiction": "contradiction",
        "graph_edge": "semantic",
        "artifact_summary": "artifact_summary",
        "decision": "decision",
        "recent_change": "semantic",
    }
    return mapping.get(proposal_type, "semantic")


@app.post("/v0/vnext/memory-proposals")
def create_vnext_memory_proposal(
    request: VNextMemoryProposalRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            if identity is None:
                return _vnext_public_error_response(
                    status_code=400, detail="agent identity is required for memory proposals"
                )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="memory.propose",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            proposal_id = str(uuid4())
            metadata = {
                "proposal_id": proposal_id,
                "proposal_type": request.proposal_type,
                "source_refs": request.source_refs,
                "project_scope": list(decision.effective_project_scope),
                "rationale": request.rationale,
                "review_required": True,
                **agent_metadata(identity, decision),
            }
            memory = store.create_memory(
                {
                    "memory_type": _vnext_memory_type_for_proposal(request.proposal_type),
                    "memory_key": f"agent_proposal.{request.proposal_type}.{proposal_id}",
                    "value": {
                        "proposal_type": request.proposal_type,
                        "text": request.canonical_text,
                        "source_refs": request.source_refs,
                        "rationale": request.rationale,
                    },
                    "status": "candidate",
                    "project_id": (
                        decision.effective_project_scope[0] if len(decision.effective_project_scope) == 1 else None
                    ),
                    "confidence": request.confidence,
                    "title": request.title,
                    "canonical_text": request.canonical_text,
                    "summary": request.canonical_text[:280],
                    "domain": request.domain,
                    "sensitivity": request.sensitivity,
                    "metadata_json": metadata,
                },
                actor_type="agent",
            )
            store.append_revision(
                {
                    "memory_id": str(memory["id"]),
                    "memory_key": str(memory["memory_key"]),
                    "new_value": memory.get("value"),
                    "revision_type": "created",
                    "action": "agent_memory_proposal",
                    "text_after": request.canonical_text,
                    "reason": request.rationale or "Agent proposed memory for human review.",
                    "actor_type": "agent",
                    "actor_id": identity.agent_id,
                    "metadata_json": metadata,
                },
                actor_type="agent",
            )
            append_event(
                store,
                event_type="agent.memory_proposed",
                actor_type="agent",
                actor_id=identity.agent_id,
                target_type="memory",
                target_id=str(memory["id"]),
                trace_id=request.trace_id or decision.trace_id,
                run_id=identity.agent_run_id,
                payload={
                    "proposal_type": request.proposal_type,
                    "agent_identity": identity.to_record(),
                    "policy_decision": decision.to_record(),
                },
            )
            append_event(
                store,
                event_type="review.item_created",
                actor_type="agent",
                actor_id=identity.agent_id,
                target_type="memory",
                target_id=str(memory["id"]),
                trace_id=request.trace_id or decision.trace_id,
                run_id=identity.agent_run_id,
                payload={"review_required": True, "proposal_type": request.proposal_type},
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {"proposal": memory, "policy_decision": decision.to_record(), "review_required": True}
        ),
    )


@app.post("/v0/vnext/memories/commit")
def commit_vnext_memory(
    request: VNextMemoryCommitRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        commit_request = memory_commit_request_from_payload(
            request.model_dump(mode="json", exclude={"agent", "agent_identity"}),
            user_id=request.user_id,
        )
    except (AgentIdentityValidationError, VNextMemoryCommitValidationError) as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            service = VNextMemoryCommitService(store, defer_embeddings=True)
            payload = service.commit(identity=identity, request=commit_request)
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    _persist_vnext_deferred_embeddings(
        database_url=settings.database_url,
        user_id=request.user_id,
        result=service,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
        trace_id=commit_request.trace_id,
    )
    status_code = 201 if payload.get("status") in {"committed", "confirmation_required", "review_required"} else 200
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/confirm")
def confirm_vnext_memory(
    request: VNextMemoryConfirmRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            service = VNextMemoryCommitService(store, defer_embeddings=True)
            payload = service.confirm(
                identity=identity,
                confirmation_id=request.confirmation_id,
                action=request.action,
                canonical_text=request.canonical_text,
                rationale=request.rationale,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    _persist_vnext_deferred_embeddings(
        database_url=settings.database_url,
        user_id=request.user_id,
        result=service,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/undo")
def undo_vnext_memory(
    request: VNextMemoryUndoRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            payload = VNextMemoryCommitService(store).undo(
                identity=identity,
                memory_id=str(request.memory_id) if request.memory_id is not None else None,
                reason=request.reason,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/correct")
def correct_vnext_memory(
    request: VNextMemoryCorrectRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            service = VNextMemoryCommitService(store, defer_embeddings=True)
            payload = service.correct(
                identity=identity,
                memory_id=str(request.memory_id),
                canonical_text=request.canonical_text,
                reason=request.reason,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    _persist_vnext_deferred_embeddings(
        database_url=settings.database_url,
        user_id=request.user_id,
        result=service,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/forget")
def forget_vnext_memory(
    request: VNextMemoryForgetRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            payload = VNextMemoryCommitService(store).forget(
                identity=identity,
                memory_id=str(request.memory_id),
                reason=request.reason,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/expire")
def expire_vnext_memory(
    request: VNextMemoryExpireRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            # The commit service policy-checks memory.expire itself (and
            # appends the policy events); returning from inside the store
            # context keeps the blocked-decision audit events committed.
            try:
                payload = VNextMemoryCommitService(store).expire(
                    str(request.memory_id),
                    valid_to=request.valid_to,
                    reason=request.reason,
                    identity=identity,
                )
            except AgentPolicyBlockedError as exc:
                return _vnext_permission_response(exc.decision)
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/unexpire")
def unexpire_vnext_memory(
    request: VNextMemoryUnexpireRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            try:
                payload = VNextMemoryCommitService(store).unexpire(
                    str(request.memory_id),
                    reason=request.reason,
                    identity=identity,
                )
            except AgentPolicyBlockedError as exc:
                return _vnext_permission_response(exc.decision)
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/accept-consolidation")
def accept_vnext_memory_consolidation(
    request: VNextMemoryAcceptConsolidationRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    service: VNextMemoryCommitService | None = None
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            # Acceptance is a review decision: the commit service
            # policy-checks it internally (human or admin agent only).
            try:
                service = VNextMemoryCommitService(store, defer_embeddings=True)
                payload = service.accept_consolidation_candidate(
                    str(request.memory_id),
                    reason=request.reason,
                    identity=identity,
                )
            except AgentPolicyBlockedError as exc:
                return _vnext_permission_response(exc.decision)
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    if service is not None:
        actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=service,
            actor_type=actor_type,
            actor_id=actor_id,
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/memories/redact")
def redact_vnext_memory(
    request: VNextMemoryRedactRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            if store.get_memory(str(request.memory_id)) is None:
                return _vnext_public_error_response(status_code=404, detail="vNext memory was not found")
            try:
                payload = redact_memory_flow(
                    store,
                    memory_id=str(request.memory_id),
                    reason=request.reason,
                    identity=identity,
                )
            except AgentPolicyBlockedError as exc:
                return _vnext_permission_response(exc.decision)
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/memories/recent-commits")
def list_vnext_recent_memory_commits(user_id: UUID, limit: int = Query(default=20, ge=1, le=100)) -> JSONResponse:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        payload = VNextMemoryCommitService(store).recent_commits(limit=limit)
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/memories/{memory_id}/audit")
def get_vnext_memory_audit(memory_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, user_id) as conn:
            store = PostgresVNextStore(conn)
            payload = VNextMemoryCommitService(store).audit(memory_id=str(memory_id))
    except VNextMemoryCommitValidationError as exc:
        return _vnext_public_error_response(status_code=404, detail=str(exc))
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/artifacts/generate/daily-brief")
def generate_vnext_daily_brief(
    request: VNextBrainArtifactGenerateRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextBrainService(store).generate_daily_brief(
                _vnext_brain_artifact_request(request, identity=identity, decision=decision)
            )
    except VNextBrainValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext daily brief request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/generate/weekly-synthesis")
def generate_vnext_weekly_synthesis(
    request: VNextBrainArtifactGenerateRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextBrainService(store).generate_weekly_synthesis(
                _vnext_brain_artifact_request(request, identity=identity, decision=decision)
            )
    except VNextBrainValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext weekly synthesis request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/generate/connections")
def generate_vnext_connection_report(
    request: VNextConnectionReportGenerateRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
                workflow_type="connection_report",
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextConnectionService(store).generate_connection_report(
                _vnext_connection_request(request, identity=identity, decision=decision)
            )
    except VNextConnectionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext connection report request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/generate/contradictions")
def generate_vnext_contradiction_report(
    request: VNextContradictionReportGenerateRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
                workflow_type="contradiction_report",
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextContradictionService(store).generate_contradiction_report(
                _vnext_contradiction_request(request, identity=identity, decision=decision)
            )
    except VNextContradictionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext contradiction report request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/queue/tasks")
def create_vnext_queue_task(
    request: VNextQueueTaskCreateRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="queue_task.create",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
                write_policy=request.write_policy,
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = VNextQueueService(store).enqueue_task(
                QueueTaskRequest(
                    title=request.title,
                    task_type=request.task_type,
                    instructions=request.instructions,
                    requested_by=identity.agent_id if identity is not None else "api",
                    scope_json=request.scope_json,
                    allowed_sources_json=request.allowed_sources_json,
                    domain=request.domain,
                    sensitivity=request.sensitivity,
                    write_policy=request.write_policy,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    trace_id=request.trace_id or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                )
            )
    except VNextQueueValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext queue task request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/queue/process-next")
def process_next_vnext_queue_task(request: VNextQueueProcessNextRequest) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, request.user_id) as conn:
        payload = VNextQueueService(PostgresVNextStore(conn)).process_next_task().to_record()

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/artifacts")
def list_vnext_artifacts(user_id: UUID, artifact_type: str | None = None, limit: int = 30) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).list_artifacts(artifact_type=artifact_type, limit=limit)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"items": payload, "count": len(payload), "order": ["created_at_desc", "id_desc"]}),
    )


@app.get("/v0/vnext/artifacts/{artifact_id}")
def get_vnext_artifact(
    artifact_id: UUID,
    user_id: UUID,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        with user_connection(settings.database_url, user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = resolve_protected_agent_identity(
                store,
                user_id=user_id,
                raw_key=agent_key_from_authorization(authorization),
                payload={},
            )
            payload, _decision = _vnext_authorized_artifact(
                store=store,
                identity=identity,
                artifact_id=str(artifact_id),
                action="artifact.lookup",
                for_update=False,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/{artifact_id}/review")
def review_vnext_artifact(
    artifact_id: UUID,
    request: VNextArtifactReviewRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    review_result = None
    reviewer_actor_type = "user"
    reviewer_actor_id: str | None = None
    reviewer_trace_id: str | None = request.trace_id
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            _artifact, decision = _vnext_authorized_artifact(
                store=store,
                identity=identity,
                artifact_id=str(artifact_id),
                action="artifact.review",
                for_update=True,
            )
            reviewer_actor_type, reviewer_actor_id = _vnext_agent_actor(identity, fallback="user")
            if reviewer_actor_id is None:
                reviewer_actor_id = str(request.user_id)
            reviewer_trace_id = request.trace_id or decision.trace_id
            review_result = dispatch_vnext_artifact_review(
                store,
                artifact_id=str(artifact_id),
                action=request.action,
                actor_type=reviewer_actor_type,
                actor_id=reviewer_actor_id,
                trace_id=reviewer_trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
            )
            payload = review_result.artifact
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except VNextProjectTerminalConsistencyError:
        return _vnext_public_error_response(
            status_code=409,
            detail=PROJECT_UPDATE_TERMINAL_CONSISTENCY_MESSAGE,
        )
    except (VNextQueueValidationError, VNextProjectValidationError):
        return _vnext_public_error_response(status_code=400, detail="vNext artifact review request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    if review_result is not None and review_result.deferred_embedding_inputs:
        _persist_vnext_deferred_embeddings(
            database_url=settings.database_url,
            user_id=request.user_id,
            result=review_result,
            actor_type=reviewer_actor_type,
            actor_id=reviewer_actor_id,
            trace_id=reviewer_trace_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/artifacts/{artifact_id}/quality-ratings")
def rate_vnext_artifact_quality(
    artifact_id: UUID,
    request: VNextArtifactQualityRatingRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    verbosity = request.verbosity.strip().casefold()
    if verbosity not in {"too_shallow", "right_sized", "too_verbose", "unknown"}:
        return _vnext_public_error_response(status_code=400, detail="vNext artifact quality verbosity is invalid")
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            existing, decision = _vnext_authorized_artifact(
                store=store,
                identity=identity,
                artifact_id=str(artifact_id),
                action="artifact.feedback",
                for_update=True,
            )
            actor_type, actor_id = _vnext_agent_actor(identity, fallback="user")
            existing_metadata = existing.get("metadata_json")
            payload = store.create_artifact_quality_rating(
                {
                    "artifact_id": str(artifact_id),
                    "reviewer_id": request.reviewer_id or actor_id,
                    "usefulness": request.usefulness,
                    "accuracy": request.accuracy,
                    "source_grounding": request.source_grounding,
                    "novel_connections": request.novel_connections,
                    "actionability": request.actionability,
                    "hallucination_risk": request.hallucination_risk,
                    "verbosity": verbosity,
                    "missed_context": request.missed_context,
                    "comments": request.comments,
                    "metadata_json": {
                        **request.metadata_json,
                        "artifact_type": existing.get("artifact_type"),
                        "generation_mode": existing_metadata.get("generation_mode")
                        if isinstance(existing_metadata, dict)
                        else None,
                        "agent_identity": identity.to_record() if identity is not None else None,
                        "policy_decision": decision.to_record(),
                    },
                },
                actor_type=actor_type,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.get("/v0/vnext/quality-evals")
def list_vnext_quality_evals(user_id: UUID, artifact_id: UUID | None = None, limit: int = 100) -> JSONResponse:
    settings = get_settings()
    bounded_limit = max(1, min(limit, 200))
    with user_connection(settings.database_url, user_id) as conn:
        rows = PostgresVNextStore(conn).list_artifact_quality_ratings(
            artifact_id=str(artifact_id) if artifact_id is not None else None,
            limit=bounded_limit,
        )
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": rows,
                "count": len(rows),
                "order": ["created_at_desc", "id_desc"],
                "export": {
                    "format": "json",
                    "rating_fields": [
                        "usefulness",
                        "accuracy",
                        "source_grounding",
                        "novel_connections",
                        "actionability",
                        "hallucination_risk",
                        "verbosity",
                        "missed_context",
                    ],
                },
            }
        ),
    )


@app.post("/v0/vnext/artifacts/{artifact_id}/export")
def export_vnext_artifact(
    artifact_id: UUID,
    request: VNextArtifactExportRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            _artifact, _decision = _vnext_authorized_artifact(
                store=store,
                identity=identity,
                artifact_id=str(artifact_id),
                action="artifact.export",
                for_update=True,
            )
            output_path = VNextQueueService(store).export_artifact_markdown(
                artifact_id=str(artifact_id),
                output_dir=request.output_dir,
            )
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except VNextQueueValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext artifact export request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({"artifact_id": str(artifact_id), "output_path": str(output_path)}),
    )


@app.post("/v0/vnext/graph/edges/{edge_id}/review")
def review_vnext_graph_edge(edge_id: str, request: VNextGraphEdgeReviewRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextConnectionService(PostgresVNextStore(conn)).review_edge(
                edge_id=edge_id,
                action=request.action,
            )
    except VNextConnectionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext graph edge review request is invalid")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/graph/neighborhood/{target_id}")
def get_vnext_graph_neighborhood(target_id: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextConnectionService(PostgresVNextStore(conn)).graph_neighborhood(target_id=target_id)

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/beliefs/{belief_id}/review")
def review_vnext_belief(belief_id: str, request: VNextBeliefReviewRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = VNextContradictionService(PostgresVNextStore(conn)).review_belief(
                belief_id=belief_id,
                action=request.action,
                confidence=request.confidence,
                superseded_by=request.superseded_by,
            )
    except VNextContradictionValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext belief review request is invalid")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/vnext/beliefs/{belief_id}/state")
def get_vnext_belief_state(belief_id: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = VNextContradictionService(PostgresVNextStore(conn)).belief_state(belief_id=belief_id)
    except VNextContradictionValidationError:
        return _vnext_public_error_response(status_code=404, detail="vNext belief was not found")

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/vnext/projects/update-candidates")
def generate_vnext_project_update_candidate(
    request: VNextProjectAutomationRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            requested_domains = _vnext_string_list(request.scope, "domains")
            requested_sensitivity = _vnext_string_list(request.options, "sensitivity_allowed") or (
                "public",
                "internal",
                "private",
                "unknown",
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="artifact.generate",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(request.scope, "projects"),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextProjectService(store).generate_project_update_candidate(
                _vnext_project_automation_request(request, identity=identity, decision=decision)
            )
    except (ValueError, VNextProjectValidationError):
        return _vnext_public_error_response(status_code=400, detail="vNext project update request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder(payload))


@app.post("/v0/vnext/projects/update-candidates/{artifact_id}/review")
def review_vnext_project_update_candidate(
    artifact_id: str,
    request: VNextProjectUpdateReviewRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    reviewer_actor_type = "user"
    reviewer_actor_id: str | None = None
    reviewer_trace_id: str | None = request.trace_id

    try:
        _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            _artifact, decision = _vnext_authorized_artifact(
                store=store,
                identity=identity,
                artifact_id=artifact_id,
                action="artifact.review",
                for_update=True,
            )
            reviewer_actor_type, reviewer_actor_id = _vnext_agent_actor(identity, fallback="user")
            if reviewer_actor_id is None:
                reviewer_actor_id = str(request.user_id)
            reviewer_trace_id = request.trace_id or decision.trace_id
            service = VNextProjectService(store, defer_embeddings=True)
            payload = service.review_project_update(
                artifact_id=artifact_id,
                action=request.action,
                edited_current_state=request.edited_current_state,
                actor_type=reviewer_actor_type,
                actor_id=reviewer_actor_id,
                trace_id=reviewer_trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
            )
    except VNextQueueNotFoundError:
        return _vnext_public_error_response(status_code=404, detail="vNext artifact was not found")
    except VNextProjectTerminalConsistencyError:
        return _vnext_public_error_response(
            status_code=409,
            detail=PROJECT_UPDATE_TERMINAL_CONSISTENCY_MESSAGE,
        )
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext project update review request is invalid")
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    _persist_vnext_deferred_embeddings(
        database_url=settings.database_url,
        user_id=request.user_id,
        result=service,
        actor_type=reviewer_actor_type,
        actor_id=reviewer_actor_id,
        trace_id=reviewer_trace_id,
    )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/projects/{project_id}/dashboard")
def get_vnext_project_dashboard(project_id: str, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = VNextProjectService(PostgresVNextStore(conn)).project_dashboard(project_id=project_id)
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=404, detail="vNext project was not found")

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/vnext/open-loops")
def create_vnext_open_loop(
    request: VNextOpenLoopCreateRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="open_loop.create",
                domains=(request.domain,),
                sensitivity_allowed=(request.sensitivity,),
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = store.create_open_loop(
                {
                    "title": request.title.strip(),
                    "description": request.description,
                    "due_at": request.due_at,
                    "priority": request.priority,
                    "memory_id": request.memory_id,
                    "project_id": request.project_id,
                    "source_id": request.source_id,
                    "domain": request.domain,
                    "sensitivity": request.sensitivity,
                    "metadata_json": {
                        "created_from": "vnext_workspace",
                        **agent_metadata(identity, decision),
                    },
                },
                actor_type=actor_type,
            )
            if identity is not None:
                append_event(
                    store,
                    event_type="agent.open_loop_created",
                    actor_type="agent",
                    actor_id=identity.agent_id,
                    target_type="open_loop",
                    target_id=str(payload["id"]),
                    trace_id=request.trace_id or decision.trace_id,
                    run_id=identity.agent_run_id,
                    payload={"agent_identity": identity.to_record(), "policy_decision": decision.to_record()},
                )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder({"open_loop": payload}))


@app.get("/v0/vnext/settings/brain-charter")
def get_vnext_brain_charter(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).get_brain_charter()

    return JSONResponse(status_code=200, content=jsonable_encoder({"brain_charter": payload}))


@app.put("/v0/vnext/settings/brain-charter")
def upsert_vnext_brain_charter(request: VNextBrainCharterUpsertRequest) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, request.user_id) as conn:
        payload = PostgresVNextStore(conn).upsert_brain_charter(
            {
                "content_markdown": request.content_markdown,
                "owner_json": request.owner_json,
                "memory_philosophy_json": request.memory_philosophy_json,
                "life_domains_json": request.life_domains_json,
                "active_projects_json": request.active_projects_json,
                "communication_style_json": request.communication_style_json,
                "priorities_json": request.priorities_json,
                "autonomous_rules_json": request.autonomous_rules_json,
                "quality_standard_json": request.quality_standard_json,
                "sensitivity": request.sensitivity,
            },
            actor_type="user",
        )

    return JSONResponse(status_code=200, content=jsonable_encoder({"brain_charter": payload}))


@app.get("/v0/vnext/scheduler/status")
def get_vnext_scheduler_status(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = VNextSchedulerService(PostgresVNextStore(conn)).status()
    payload = {**payload, "daemon": daemon_status()}

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/vnext/scheduler/runs")
def list_vnext_scheduler_runs(user_id: UUID, workflow_type: str | None = None, limit: int = 20) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = PostgresVNextStore(conn).list_scheduler_runs(workflow_type=workflow_type, limit=limit)

    return JSONResponse(status_code=200, content=jsonable_encoder({"items": payload, "count": len(payload)}))


@app.get("/v0/vnext/scheduler/failures")
def list_vnext_scheduler_failures(user_id: UUID, workflow_type: str | None = None, limit: int = 20) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        runs = [
            run
            for run in PostgresVNextStore(conn).list_scheduler_runs(
                workflow_type=workflow_type,
                limit=max(limit * 4, limit),
            )
            if run.get("status") == "failed"
        ][:limit]

    return JSONResponse(status_code=200, content=jsonable_encoder({"items": runs, "count": len(runs)}))


@app.get("/v0/vnext/agents/policy-telemetry")
def get_vnext_agent_policy_telemetry(
    user_id: UUID,
    agent_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> JSONResponse:
    settings = get_settings()
    bounded_limit = min(max(limit, 1), 200)

    with user_connection(settings.database_url, user_id) as conn:
        store = PostgresVNextStore(conn)
        payload = summarize_agent_policy_telemetry(
            agent_events=store.list_agent_events(agent_id=agent_id, limit=bounded_limit),
            artifacts=store.list_agent_policy_artifacts(agent_id=agent_id, limit=bounded_limit),
            memories=store.list_agent_policy_memories(agent_id=agent_id, limit=bounded_limit),
        )

    return JSONResponse(status_code=200, content=jsonable_encoder({"summary": payload}))


@app.patch("/v0/vnext/scheduler/workflows/{workflow_type}")
def patch_vnext_scheduler_workflow(
    workflow_type: str,
    request: VNextSchedulerWorkflowPatchRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
        if request.schedule_json is not None:
            validate_schedule(workflow_type, request.schedule_json)
    except (AgentIdentityValidationError, VNextSchedulerValidationError) as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="scheduler.configure",
                workflow_type=workflow_type,
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="user")
            payload = VNextSchedulerService(store).configure_workflow(
                workflow_type=workflow_type,
                enabled=request.enabled,
                paused=request.paused,
                schedule_json=request.schedule_json,
                timezone=request.timezone,
                metadata_json={"model_options": _vnext_model_generation_options(request.model_options)}
                if request.model_options
                else None,
                actor_type=actor_type,
            )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(
        status_code=200, content=jsonable_encoder({"workflow": payload, "policy_decision": decision.to_record()})
    )


@app.post("/v0/vnext/scheduler/workflows/{workflow_type}/run-now")
def run_vnext_scheduler_workflow_now(
    workflow_type: str,
    request: VNextSchedulerRunNowRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    scope = request.scope
    options = request.options
    requested_domains = _vnext_string_list(scope, "domains")
    requested_sensitivity = _vnext_string_list(options, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="scheduler.run_now",
                domains=requested_domains,
                sensitivity_allowed=requested_sensitivity,
                project_scope=tuple(request.project_scope) or _vnext_string_list(scope, "projects"),
                workflow_type=workflow_type,
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            triggered_by = "agent" if identity is not None else "user"
            scheduler_request = SchedulerRunRequest(
                workflow_type=workflow_type,
                domains=decision.effective_domains,
                projects=decision.effective_project_scope,
                sensitivity_allowed=decision.effective_sensitivity_allowed,
                generated_for=str(options["generated_for"]) if isinstance(options.get("generated_for"), str) else None,
                triggered_by=triggered_by,
                agent_identity=identity,
                policy_decision=decision,
                options=options,
            )
        payload = run_now_durable(
            database_url=settings.database_url,
            user_id=request.user_id,
            request=scheduler_request,
        )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder({**payload, "policy_decision": decision.to_record()}))


@app.post("/v0/vnext/scheduler/run-due")
def run_vnext_scheduler_due(
    request: VNextSchedulerRunDueRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    actor_type = "scheduler"
    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="scheduler.run_due",
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="scheduler")
        payload = run_due_workflows_durable(
            database_url=settings.database_url,
            user_id=request.user_id,
            limit=request.limit,
            triggered_by=actor_type,
            agent_identity=identity,
            policy_decision=decision,
        )
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=201, content=jsonable_encoder({**payload, "policy_decision": decision.to_record()}))


@app.post("/v0/vnext/scheduler/pause")
def pause_vnext_scheduler(
    request: VNextSchedulerControlRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    return _vnext_scheduler_global_control(request, action="scheduler.pause", pause=True, authorization=authorization)


@app.post("/v0/vnext/scheduler/resume")
def resume_vnext_scheduler(
    request: VNextSchedulerControlRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    return _vnext_scheduler_global_control(request, action="scheduler.resume", pause=False, authorization=authorization)


def _vnext_scheduler_global_control(
    request: VNextSchedulerControlRequest,
    *,
    action: str,
    pause: bool,
    authorization: str | None = None,
) -> JSONResponse:
    settings = get_settings()
    try:
        identity = _vnext_agent_identity(request)
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store, request, user_id=request.user_id, authorization=authorization
            )
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action=action,
                project_scope=tuple(request.project_scope),
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            actor_type, _actor_id = _vnext_agent_actor(identity, fallback="user")
            service = VNextSchedulerService(store)
            payload = service.pause_all(actor_type=actor_type) if pause else service.resume_all(actor_type=actor_type)
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except VNextSchedulerValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)

    return JSONResponse(status_code=200, content=jsonable_encoder({**payload, "policy_decision": decision.to_record()}))


@app.post("/v0/vnext/open-loops/extract")
def extract_vnext_open_loops(request: VNextProjectAutomationRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            loops = VNextProjectService(PostgresVNextStore(conn)).extract_open_loops(
                _vnext_project_automation_request(request)
            )
    except (ValueError, VNextProjectValidationError):
        return _vnext_public_error_response(status_code=400, detail="vNext open-loop extraction request is invalid")

    return JSONResponse(status_code=201, content=jsonable_encoder({"open_loops": loops, "created_count": len(loops)}))


@app.post("/v0/vnext/open-loops/{loop_id}/review")
def review_vnext_open_loop(
    loop_id: str,
    request: VNextOpenLoopReviewRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    settings = get_settings()

    try:
        _vnext_agent_identity(request)
        with user_connection(settings.database_url, request.user_id) as conn:
            store = PostgresVNextStore(conn)
            identity = _vnext_authenticated_agent_identity(
                store,
                request,
                user_id=request.user_id,
                authorization=authorization,
            )
            target = store.get_open_loop(loop_id)
            if target is None:
                return _vnext_public_error_response(status_code=404, detail="vNext open loop was not found")
            decision = _vnext_policy_checked(
                store=store,
                identity=identity,
                action="open_loop.update",
                domains=(str(target.get("domain") or "unknown"),),
                sensitivity_allowed=(str(target.get("sensitivity") or "unknown"),),
                project_scope=resource_project_scope(target),
                target_type="open_loop",
                target_id=loop_id,
                require_explicit_project_scope=True,
            )
            if decision.decision == "blocked":
                return _vnext_permission_response(decision)
            payload = VNextProjectService(store).review_open_loop(
                loop_id=loop_id,
                action=request.action,
                title=request.title,
                description=request.description,
                due_at=request.due_at,
                priority=request.priority,
                resolution_note=request.resolution_note,
            )
    except AgentIdentityValidationError as exc:
        return _vnext_public_error_response(status_code=400, detail=str(exc))
    except AgentKeyAuthenticationError as exc:
        return _vnext_agent_auth_error_response(exc)
    except AgentPolicyBlockedError as exc:
        return _vnext_permission_response(exc.decision)
    except VNextProjectValidationError:
        return _vnext_public_error_response(status_code=400, detail="vNext open-loop review request is invalid")

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v0/continuity/captures/candidates")
def create_continuity_capture_candidates(request: ContinuityCaptureCandidatesRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = capture_continuity_candidates(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ContinuityCaptureCandidatesInput(
                    user_content=request.user_content,
                    assistant_content=request.assistant_content,
                    session_id=request.session_id,
                    source_kind=request.source_kind,
                ),
            )
    except ContinuityCaptureValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/captures/commit")
def commit_continuity_capture_candidates(request: ContinuityCaptureCommitRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = commit_continuity_captures(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=ContinuityCaptureCommitInput(
                    mode=request.mode,  # type: ignore[arg-type]
                    candidates=[_json_object(candidate) for candidate in request.candidates],
                    sync_fingerprint=request.sync_fingerprint,
                    source_kind=request.source_kind,
                ),
            )
    except (ContinuityCaptureValidationError, ContinuityObjectValidationError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/memory/operations/candidates/generate")
def generate_memory_operation_candidates_endpoint(
    http_request: Request,
    request: MemoryOperationGenerateRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = generate_memory_operation_candidates(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationGenerateInput(
                    user_content=request.user_content,
                    assistant_content=request.assistant_content,
                    mode=request.mode,  # type: ignore[arg-type]
                    sync_fingerprint=request.sync_fingerprint,
                    source_kind=request.source_kind,
                    session_id=request.session_id,
                    thread_id=request.thread_id,
                    task_id=request.task_id,
                    project=request.project,
                    person=request.person,
                    target_continuity_object_id=request.target_continuity_object_id,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityCaptureValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/memory/operations/candidates")
def list_memory_operation_candidates_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_CONTINUITY_CAPTURE_LIMIT, ge=1, le=100),
    policy_action: str | None = Query(default=None, min_length=1, max_length=40),
    operation_type: str | None = Query(default=None, min_length=1, max_length=40),
    sync_fingerprint: str | None = Query(default=None, min_length=1, max_length=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_operation_candidates(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationListInput(
                    limit=limit,
                    policy_action=policy_action,  # type: ignore[arg-type]
                    operation_type=operation_type,  # type: ignore[arg-type]
                    sync_fingerprint=sync_fingerprint,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/memory/operations/commit")
def commit_memory_operations_endpoint(
    http_request: Request,
    request: MemoryOperationCommitRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = commit_memory_operations(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationCommitInput(
                    candidate_ids=request.candidate_ids,
                    sync_fingerprint=request.sync_fingerprint,
                    include_review_required=request.include_review_required,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/memory/operations")
def list_memory_operations_endpoint(
    request: Request,
    limit: int = Query(default=DEFAULT_CONTINUITY_CAPTURE_LIMIT, ge=1, le=100),
    sync_fingerprint: str | None = Query(default=None, min_length=1, max_length=200),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_operations(
                ContinuityStore(conn),
                user_id=user_id,
                request=MemoryOperationListInput(
                    limit=limit,
                    sync_fingerprint=sync_fingerprint,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except MemoryMutationValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/captures")
def list_continuity_captures(
    user_id: UUID,
    limit: int = Query(default=DEFAULT_CONTINUITY_CAPTURE_LIMIT, ge=1, le=MAX_CONTINUITY_CAPTURE_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_continuity_capture_inbox(
            ContinuityStore(conn),
            user_id=user_id,
            limit=limit,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/captures/{capture_event_id}")
def get_continuity_capture(capture_event_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_continuity_capture_detail(
                ContinuityStore(conn),
                user_id=user_id,
                capture_event_id=capture_event_id,
            )
    except ContinuityCaptureNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/admin/debug/continuity/lifecycle")
def list_continuity_lifecycle_endpoint(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_LIFECYCLE_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityLifecycleListResponse = list_continuity_lifecycle_state(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityLifecycleQueryInput(limit=limit),
            )
    except ContinuityLifecycleValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/admin/debug/continuity/lifecycle/{continuity_object_id}")
def get_continuity_lifecycle_endpoint(
    continuity_object_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityLifecycleDetailResponse = get_continuity_lifecycle_state(
                ContinuityStore(conn),
                user_id=user_id,
                continuity_object_id=continuity_object_id,
            )
    except ContinuityLifecycleNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/review-queue")
def list_continuity_review_queue_endpoint(
    user_id: UUID,
    status: str = Query(default="correction_ready", min_length=1, max_length=40),
    limit: int = Query(
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityReviewQueueResponse = list_continuity_review_queue(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityReviewQueueQueryInput(
                    status=status,  # type: ignore[arg-type]
                    limit=limit,
                ),
            )
    except ContinuityReviewValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/review-queue/{continuity_object_id}")
def get_continuity_review_detail_endpoint(
    continuity_object_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityReviewDetailResponse = get_continuity_review_detail(
                ContinuityStore(conn),
                user_id=user_id,
                continuity_object_id=continuity_object_id,
            )
    except ContinuityReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/explain/{continuity_object_id}")
def get_continuity_explain_endpoint(
    continuity_object_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityExplainResponse = build_continuity_explain(
                ContinuityStore(conn),
                user_id=user_id,
                continuity_object_id=continuity_object_id,
                include_raw_content=False,
            )
    except ContinuityEvidenceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/contradictions/detect")
def detect_contradictions_endpoint(
    http_request: Request,
    request: ContradictionDetectRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionSyncResponse = sync_contradictions(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContradictionSyncInput(
                    continuity_object_id=request.continuity_object_id,
                    limit=request.limit,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityContradictionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/contradictions/cases")
def list_contradiction_cases_endpoint(
    request: Request,
    status: str = Query(default="open", min_length=1, max_length=40),
    continuity_object_id: UUID | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionCaseListResponse = list_contradiction_cases(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContradictionCaseListQueryInput(
                    status=status,  # type: ignore[arg-type]
                    limit=limit,
                    continuity_object_id=continuity_object_id,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityContradictionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/contradictions/cases/{contradiction_case_id}")
def get_contradiction_case_endpoint(
    contradiction_case_id: UUID,
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionCaseDetailResponse = get_contradiction_case(
                ContinuityStore(conn),
                user_id=user_id,
                contradiction_case_id=contradiction_case_id,
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityContradictionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.post("/v1/contradictions/cases/{contradiction_case_id}/resolve")
def resolve_contradiction_case_endpoint(
    contradiction_case_id: UUID,
    http_request: Request,
    request: ContradictionResolveRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContradictionResolveResponse = resolve_contradiction_case(
                ContinuityStore(conn),
                user_id=user_id,
                contradiction_case_id=contradiction_case_id,
                request=ContradictionResolveInput(
                    action=request.action,  # type: ignore[arg-type]
                    note=request.note,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityContradictionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityContradictionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v1/trust/signals")
def list_trust_signals_endpoint(
    request: Request,
    continuity_object_id: UUID | None = None,
    signal_state: str = Query(default="active", min_length=1, max_length=40),
    signal_type: str | None = Query(default=None, min_length=1, max_length=40),
    limit: int = Query(
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: TrustSignalListResponse = list_trust_signals(
                ContinuityStore(conn),
                user_id=user_id,
                request=TrustSignalListQueryInput(
                    limit=limit,
                    continuity_object_id=continuity_object_id,
                    signal_state=signal_state,  # type: ignore[arg-type]
                    signal_type=signal_type,  # type: ignore[arg-type]
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/state-at")
def get_temporal_state_at_endpoint(
    entity_id: UUID,
    user_id: UUID,
    at: datetime | None = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TemporalStateAtResponse = get_temporal_state_at(
                ContinuityStore(conn),
                user_id=user_id,
                request=TemporalStateAtQueryInput(
                    entity_id=entity_id,
                    at=at,
                ),
            )
    except (TemporalStateNotFoundError, TemporalStateValidationError) as exc:
        status_code = 404 if isinstance(exc, TemporalStateNotFoundError) else 400
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/timeline")
def get_temporal_timeline_endpoint(
    entity_id: UUID,
    user_id: UUID,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=DEFAULT_TEMPORAL_TIMELINE_LIMIT, ge=1, le=MAX_TEMPORAL_TIMELINE_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TemporalTimelineResponse = get_temporal_timeline(
                ContinuityStore(conn),
                user_id=user_id,
                request=TemporalTimelineQueryInput(
                    entity_id=entity_id,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except (TemporalStateNotFoundError, TemporalStateValidationError) as exc:
        status_code = 404 if isinstance(exc, TemporalStateNotFoundError) else 400
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/explain")
def get_temporal_explain_endpoint(
    entity_id: UUID,
    user_id: UUID,
    at: datetime | None = None,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TemporalExplainResponse = get_temporal_explain(
                ContinuityStore(conn),
                user_id=user_id,
                request=TemporalExplainQueryInput(
                    entity_id=entity_id,
                    at=at,
                ),
            )
    except (TemporalStateNotFoundError, TemporalStateValidationError) as exc:
        status_code = 404 if isinstance(exc, TemporalStateNotFoundError) else 400
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/patterns")
def list_trusted_fact_patterns_endpoint(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        ge=1,
        le=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: TrustedFactPatternListResponse = list_trusted_fact_patterns(
            ContinuityStore(conn),
            user_id=user_id,
            request=TrustedFactPatternListQueryInput(limit=limit),
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/patterns/{pattern_id}")
def get_trusted_fact_pattern_endpoint(
    pattern_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TrustedFactPatternExplainResponse = get_trusted_fact_pattern(
                ContinuityStore(conn),
                user_id=user_id,
                pattern_id=pattern_id,
            )
    except TrustedFactPromotionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/playbooks")
def list_trusted_fact_playbooks_endpoint(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
        ge=1,
        le=MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: TrustedFactPlaybookListResponse = list_trusted_fact_playbooks(
            ContinuityStore(conn),
            user_id=user_id,
            request=TrustedFactPlaybookListQueryInput(limit=limit),
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/playbooks/{playbook_id}")
def get_trusted_fact_playbook_endpoint(
    playbook_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: TrustedFactPlaybookExplainResponse = get_trusted_fact_playbook(
                ContinuityStore(conn),
                user_id=user_id,
                playbook_id=playbook_id,
            )
    except TrustedFactPromotionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(status_code=200, content=jsonable_encoder(payload))


@app.get("/v0/admin/debug/continuity/artifacts/{artifact_id}")
def get_continuity_artifact_detail_endpoint(
    request: Request,
    artifact_id: UUID,
    user_id: UUID,
    include_raw_content: bool = Query(default=False),
) -> JSONResponse:
    settings = get_settings()
    if include_raw_content and not _allow_raw_evidence_debug_access(settings):
        return JSONResponse(
            status_code=403,
            content={"detail": "raw evidence content access is restricted to development/test"},
        )

    if include_raw_content:
        _audit_raw_evidence_access(
            request=request,
            settings=settings,
            route="/v0/admin/debug/continuity/artifacts/{artifact_id}",
            user_id=user_id,
        )

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityArtifactDetailResponse = get_continuity_artifact_detail(
                ContinuityStore(conn),
                user_id=user_id,
                artifact_id=artifact_id,
                include_raw_content=include_raw_content,
            )
    except ContinuityEvidenceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/review-queue/{continuity_object_id}/corrections")
def apply_continuity_correction_endpoint(
    continuity_object_id: UUID,
    request: ContinuityCorrectionRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = apply_continuity_correction(
                ContinuityStore(conn),
                user_id=request.user_id,
                continuity_object_id=continuity_object_id,
                request=ContinuityCorrectionInput(
                    action=request.action,  # type: ignore[arg-type]
                    reason=request.reason,
                    title=request.title,
                    body=request.body,  # type: ignore[arg-type]
                    provenance=request.provenance,  # type: ignore[arg-type]
                    confidence=request.confidence,
                    replacement_title=request.replacement_title,
                    replacement_body=request.replacement_body,  # type: ignore[arg-type]
                    replacement_provenance=request.replacement_provenance,  # type: ignore[arg-type]
                    replacement_confidence=request.replacement_confidence,
                ),
            )
    except ContinuityReviewValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/open-loops")
def get_continuity_open_loop_dashboard(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityOpenLoopDashboardResponse = compile_continuity_open_loop_dashboard(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityOpenLoopDashboardQueryInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/daily-brief")
def get_continuity_daily_brief(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_DAILY_BRIEF_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityDailyBriefResponse = compile_continuity_daily_brief(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityDailyBriefRequestInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/weekly-review")
def get_continuity_weekly_review(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityWeeklyReviewResponse = compile_continuity_weekly_review(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityWeeklyReviewRequestInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/continuity/open-loops/{continuity_object_id}/review-action")
def apply_continuity_open_loop_review_action_endpoint(
    continuity_object_id: UUID,
    request: ContinuityOpenLoopReviewActionRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload: ContinuityOpenLoopReviewActionResponse = apply_continuity_open_loop_review_action(
                ContinuityStore(conn),
                user_id=request.user_id,
                continuity_object_id=continuity_object_id,
                request=ContinuityOpenLoopReviewActionInput(
                    action=request.action,  # type: ignore[arg-type]
                    note=request.note,
                ),
            )
    except ContinuityOpenLoopValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityOpenLoopNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/recall")
def list_continuity_recall(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        ge=1,
        le=MAX_CONTINUITY_RECALL_LIMIT,
    ),
    debug: bool = False,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityRecallResponse = query_continuity_recall(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityRecallQueryInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    limit=limit,
                    debug=debug,
                ),
            )
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/retrieval-runs")
def get_continuity_retrieval_runs(
    user_id: UUID,
    limit: int = Query(
        default=DEFAULT_RETRIEVAL_RUN_LIST_LIMIT,
        ge=1,
        le=MAX_RETRIEVAL_RUN_LIST_LIMIT,
    ),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: RetrievalRunListResponse = list_retrieval_runs(
                ContinuityStore(conn),
                user_id=user_id,
                limit=limit,
            )
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/retrieval-runs/{retrieval_run_id}")
def get_continuity_retrieval_trace(
    retrieval_run_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: RetrievalTraceResponse = get_retrieval_trace(
                ContinuityStore(conn),
                user_id=user_id,
                retrieval_run_id=retrieval_run_id,
            )
    except RetrievalTraceNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/retrieval-evaluation")
def get_continuity_retrieval_evaluation(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: RetrievalEvaluationResponse = get_retrieval_evaluation_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/evals/suites")
def get_public_eval_suites(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalSuiteDefinitionListResponse = list_public_eval_suites(
                ContinuityStore(conn),
                user_id=user_id,
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/evals/runs")
def create_public_eval_run(
    request: Request,
    suite_key: list[str] | None = Query(default=None),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalRunDetailResponse = run_public_evals(
                ContinuityStore(conn),
                user_id=user_id,
                suite_keys=suite_key,
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/evals/runs")
def get_public_eval_runs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalRunListResponse = list_public_eval_runs(
                ContinuityStore(conn),
                user_id=user_id,
                limit=limit,
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v1/evals/runs/{eval_run_id}")
def get_public_eval_run_detail(
    eval_run_id: UUID,
    request: Request,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: PublicEvalRunDetailResponse = get_public_eval_run(
                ContinuityStore(conn),
                user_id=user_id,
                eval_run_id=eval_run_id,
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/continuity/resumption-brief")
def get_continuity_resumption_brief(
    user_id: UUID,
    query_text: str | None = Query(default=None, alias="query", min_length=1, max_length=4000),
    thread_id: UUID | None = None,
    task_id: UUID | None = None,
    project: str | None = Query(default=None, min_length=1, max_length=200),
    person: str | None = Query(default=None, min_length=1, max_length=200),
    since: datetime | None = None,
    until: datetime | None = None,
    max_recent_changes: int = Query(
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    ),
    max_open_loops: int = Query(
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ge=0,
        le=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    ),
    include_non_promotable_facts: bool = False,
    debug: bool = False,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityResumptionBriefResponse = compile_continuity_resumption_brief(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityResumptionBriefRequestInput(
                    query=query_text,
                    thread_id=thread_id,
                    task_id=task_id,
                    project=project,
                    person=person,
                    since=since,
                    until=until,
                    max_recent_changes=max_recent_changes,
                    max_open_loops=max_open_loops,
                    include_non_promotable_facts=include_non_promotable_facts,
                    debug=debug,
                ),
            )
    except ContinuityResumptionValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ContinuityRecallValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/continuity/brief")
def post_continuity_brief(
    http_request: Request,
    request: ContinuityBriefRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_id = _resolve_authenticated_v1_user_id(settings, http_request)
        with user_connection(settings.database_url, user_id) as conn:
            payload: ContinuityBriefResponse = compile_continuity_brief(
                ContinuityStore(conn),
                user_id=user_id,
                request=ContinuityBriefRequestInput(
                    brief_type=request.brief_type,  # type: ignore[arg-type]
                    query=request.query,
                    thread_id=request.thread_id,
                    task_id=request.task_id,
                    project=request.project,
                    person=request.person,
                    since=request.since,
                    until=request.until,
                    max_relevant_facts=request.max_relevant_facts,
                    max_recent_changes=request.max_recent_changes,
                    max_open_loops=request.max_open_loops,
                    max_conflicts=request.max_conflicts,
                    max_timeline_highlights=request.max_timeline_highlights,
                    include_non_promotable_facts=request.include_non_promotable_facts,
                ),
            )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except (
        ContinuityBriefValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
        TaskBriefValidationError,
    ) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-briefs/compile")
def post_v0_task_brief_compile(body: TaskBriefCompileRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, body.user_id) as conn:
            payload: TaskBriefResponse = compile_and_persist_task_brief(
                ContinuityStore(conn),
                user_id=body.user_id,
                request=TaskBriefCompileRequestInput(
                    mode=body.mode,
                    query=body.query,
                    thread_id=body.thread_id,
                    task_id=body.task_id,
                    project=body.project,
                    person=body.person,
                    since=body.since,
                    until=body.until,
                    include_non_promotable_facts=body.include_non_promotable_facts,
                    provider_strategy=body.provider_strategy,
                    briefing_strategy=body.briefing_strategy,
                    token_budget=body.token_budget,
                ),
            )
    except (
        TaskBriefValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
    ) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-briefs/{task_brief_id}")
def get_v0_task_brief(task_brief_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_persisted_task_brief(
                ContinuityStore(conn),
                task_brief_id=task_brief_id,
            )
    except TaskBriefNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-briefs/compare")
def post_v0_task_brief_compare(body: TaskBriefCompareRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, body.user_id) as conn:
            payload: TaskBriefComparisonResponse = compare_task_briefs(
                ContinuityStore(conn),
                user_id=body.user_id,
                primary_request=TaskBriefCompileRequestInput(
                    mode=body.primary.mode,
                    query=body.primary.query,
                    thread_id=body.primary.thread_id,
                    task_id=body.primary.task_id,
                    project=body.primary.project,
                    person=body.primary.person,
                    since=body.primary.since,
                    until=body.primary.until,
                    include_non_promotable_facts=body.primary.include_non_promotable_facts,
                    provider_strategy=body.primary.provider_strategy,
                    briefing_strategy=body.primary.briefing_strategy,
                    token_budget=body.primary.token_budget,
                ),
                secondary_request=TaskBriefCompileRequestInput(
                    mode=body.secondary.mode,
                    query=body.secondary.query,
                    thread_id=body.secondary.thread_id,
                    task_id=body.secondary.task_id,
                    project=body.secondary.project,
                    person=body.secondary.person,
                    since=body.secondary.since,
                    until=body.secondary.until,
                    include_non_promotable_facts=body.secondary.include_non_promotable_facts,
                    provider_strategy=body.secondary.provider_strategy,
                    briefing_strategy=body.secondary.briefing_strategy,
                    token_budget=body.secondary.token_budget,
                ),
            )
    except (
        TaskBriefValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
    ) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories")
def list_memories(
    user_id: UUID,
    status: MemoryReviewStatusFilter = Query(default="active"),
    limit: int = Query(default=DEFAULT_MEMORY_REVIEW_LIMIT, ge=1, le=MAX_MEMORY_REVIEW_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_memory_review_records(
            ContinuityStore(conn),
            user_id=user_id,
            status=status,
            limit=limit,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/review-queue")
def list_memory_review_queue(
    user_id: UUID,
    limit: int = Query(default=DEFAULT_MEMORY_REVIEW_LIMIT, ge=1, le=MAX_MEMORY_REVIEW_LIMIT),
    priority_mode: MemoryReviewQueuePriorityMode = Query(default=DEFAULT_MEMORY_REVIEW_QUEUE_PRIORITY_MODE),
) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_memory_review_queue_records(
            ContinuityStore(conn),
            user_id=user_id,
            limit=limit,
            priority_mode=priority_mode,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/quality-gate")
def get_memories_quality_gate(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = get_memory_quality_gate_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/trust-dashboard")
def get_memories_trust_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: MemoryTrustDashboardResponse = get_memory_trust_dashboard_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/hygiene-dashboard")
def get_memories_hygiene_dashboard(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload: MemoryHygieneDashboardResponse = get_memory_hygiene_dashboard_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/evaluation-summary")
def get_memories_evaluation_summary(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = get_memory_evaluation_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/semantic-retrieval")
def retrieve_semantic_memories(request: RetrieveSemanticMemoriesRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = retrieve_semantic_memory_records(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=SemanticMemoryRetrievalRequestInput(
                    embedding_config_id=request.embedding_config_id,
                    query_vector=tuple(request.query_vector),
                    limit=request.limit,
                ),
            )
    except SemanticMemoryRetrievalValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}")
def get_memory(
    memory_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_memory_review_record(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}/revisions")
def list_memory_revisions(
    memory_id: UUID,
    user_id: UUID,
    limit: int = Query(default=DEFAULT_MEMORY_REVIEW_LIMIT, ge=1, le=MAX_MEMORY_REVIEW_LIMIT),
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_revision_review_records(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
                limit=limit,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memories/{memory_id}/labels")
def create_memory_review_label(
    memory_id: UUID,
    request: CreateMemoryReviewLabelRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_memory_review_label_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                memory_id=memory_id,
                label=request.label,
                note=request.note,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}/labels")
def list_memory_review_labels(
    memory_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_review_label_records(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
            )
    except MemoryReviewNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/embedding-configs")
def create_embedding_config(request: CreateEmbeddingConfigRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_embedding_config_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                config=EmbeddingConfigCreateInput(
                    provider=request.provider,
                    model=request.model,
                    version=request.version,
                    dimensions=request.dimensions,
                    status=request.status,
                    metadata=_json_object(request.metadata),
                ),
            )
    except EmbeddingConfigValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/embedding-configs")
def list_embedding_configs(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_embedding_config_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/memory-embeddings")
def upsert_memory_embedding(request: UpsertMemoryEmbeddingRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = upsert_memory_embedding_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=MemoryEmbeddingUpsertInput(
                    memory_id=request.memory_id,
                    embedding_config_id=request.embedding_config_id,
                    vector=tuple(request.vector),
                ),
            )
    except MemoryEmbeddingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/task-artifact-chunk-embeddings")
def upsert_task_artifact_chunk_embedding(
    request: UpsertTaskArtifactChunkEmbeddingRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = upsert_task_artifact_chunk_embedding_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                request=TaskArtifactChunkEmbeddingUpsertInput(
                    task_artifact_chunk_id=request.task_artifact_chunk_id,
                    embedding_config_id=request.embedding_config_id,
                    vector=tuple(request.vector),
                ),
            )
    except TaskArtifactChunkEmbeddingValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memories/{memory_id}/embeddings")
def list_memory_embeddings(memory_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_memory_embedding_records(
                ContinuityStore(conn),
                user_id=user_id,
                memory_id=memory_id,
            )
    except MemoryEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifacts/{task_artifact_id}/chunk-embeddings")
def list_task_artifact_chunk_embeddings_for_artifact(
    task_artifact_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_artifact_chunk_embedding_records_for_artifact(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_id=task_artifact_id,
            )
    except TaskArtifactNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifact-chunks/{task_artifact_chunk_id}/embeddings")
def list_task_artifact_chunk_embeddings(
    task_artifact_chunk_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_task_artifact_chunk_embedding_records_for_chunk(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_chunk_id=task_artifact_chunk_id,
            )
    except TaskArtifactChunkEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/memory-embeddings/{memory_embedding_id}")
def get_memory_embedding(memory_embedding_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_memory_embedding_record(
                ContinuityStore(conn),
                user_id=user_id,
                memory_embedding_id=memory_embedding_id,
            )
    except MemoryEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/task-artifact-chunk-embeddings/{task_artifact_chunk_embedding_id}")
def get_task_artifact_chunk_embedding(
    task_artifact_chunk_embedding_id: UUID,
    user_id: UUID,
) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_task_artifact_chunk_embedding_record(
                ContinuityStore(conn),
                user_id=user_id,
                task_artifact_chunk_embedding_id=task_artifact_chunk_embedding_id,
            )
    except TaskArtifactChunkEmbeddingNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/entities")
def create_entity(request: CreateEntityRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_entity_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                entity=EntityCreateInput(
                    entity_type=request.entity_type,
                    name=request.name,
                    source_memory_ids=tuple(request.source_memory_ids),
                ),
            )
    except EntityValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.post("/v0/entity-edges")
def create_entity_edge(request: CreateEntityEdgeRequest) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, request.user_id) as conn:
            payload = create_entity_edge_record(
                ContinuityStore(conn),
                user_id=request.user_id,
                edge=EntityEdgeCreateInput(
                    from_entity_id=request.from_entity_id,
                    to_entity_id=request.to_entity_id,
                    relationship_type=request.relationship_type,
                    valid_from=request.valid_from,
                    valid_to=request.valid_to,
                    source_memory_ids=tuple(request.source_memory_ids),
                ),
            )
    except EntityEdgeValidationError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/entities")
def list_entities(user_id: UUID) -> JSONResponse:
    settings = get_settings()

    with user_connection(settings.database_url, user_id) as conn:
        payload = list_entity_records(
            ContinuityStore(conn),
            user_id=user_id,
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/entities/{entity_id}/edges")
def list_entity_edges(entity_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = list_entity_edge_records(
                ContinuityStore(conn),
                user_id=user_id,
                entity_id=entity_id,
            )
    except EntityNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.get("/v0/entities/{entity_id}")
def get_entity(entity_id: UUID, user_id: UUID) -> JSONResponse:
    settings = get_settings()

    try:
        with user_connection(settings.database_url, user_id) as conn:
            payload = get_entity_record(
                ContinuityStore(conn),
                user_id=user_id,
                entity_id=entity_id,
            )
    except EntityNotFoundError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(payload),
    )


@app.post("/v1/workspaces/bootstrap")
def bootstrap_v1_workspace(request: Request) -> JSONResponse:
    settings = get_settings()
    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                context = ensure_local_workspace(conn, user_account_id=user_account_id)
        workspace_id = context["workspace"]["id"]
        seeded_providers = _seed_workspace_provider_configs(
            settings=settings,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
        )
        for provider in seeded_providers:
            discovery = _discover_provider_capability(provider=provider, settings=settings)
            _persist_discovered_provider_capability(
                settings=settings,
                user_account_id=user_account_id,
                workspace_id=workspace_id,
                provider=provider,
                outcome=discovery,
            )
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "workspace": serialize_local_workspace(context["workspace"]),
                "bootstrap": {
                    "workspace_id": str(workspace_id),
                    "status": "ready",
                    "bootstrapped_at": (
                        None
                        if context["workspace"]["bootstrapped_at"] is None
                        else context["workspace"]["bootstrapped_at"].isoformat()
                    ),
                },
                "seeded_provider_count": len(seeded_providers),
            }
        ),
    )


@app.get("/v1/workspaces/bootstrap/status")
def get_v1_workspace_bootstrap_status(request: Request) -> JSONResponse:
    settings = get_settings()
    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                context = get_local_workspace(conn, user_account_id=user_account_id)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    if context is None:
        return JSONResponse(
            status_code=404,
            content={"detail": "local workspace is not bootstrapped; POST /v1/workspaces/bootstrap first"},
        )
    workspace = context["workspace"]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "workspace": serialize_local_workspace(workspace),
                "bootstrap": {
                    "workspace_id": str(workspace["id"]),
                    "status": workspace["bootstrap_status"],
                    "bootstrapped_at": (
                        None if workspace["bootstrapped_at"] is None else workspace["bootstrapped_at"].isoformat()
                    ),
                },
            }
        ),
    )


@app.post("/v1/providers")
def register_v1_provider(request: Request, body: RegisterProviderRequest) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        provider, capability = _create_workspace_provider_durable(
            settings=settings,
            authenticated_user_id=user_account_id,
            provider_key=body.provider_key,
            display_name=body.display_name,
            base_url=body.base_url,
            api_key=body.api_key,
            auth_mode=body.auth_mode,
            default_model=body.default_model,
            model_list_path=body.model_list_path,
            healthcheck_path=body.healthcheck_path,
            invoke_path=body.invoke_path,
            metadata=body.metadata,
        )
        discovery = _discover_provider_capability(provider=provider, settings=settings)
        refreshed_capability = _persist_discovered_provider_capability(
            settings=settings,
            user_account_id=user_account_id,
            workspace_id=provider["workspace_id"],
            provider=provider,
            outcome=discovery,
        )
        if refreshed_capability is None:
            return JSONResponse(
                status_code=409,
                content={"detail": "provider configuration changed during capability discovery"},
            )
        capability = refreshed_capability
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ProviderConfigurationChangedError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/ollama/register")
def register_v1_ollama_provider(
    request: Request,
    body: RegisterOllamaProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        provider, capability = _create_workspace_provider_durable(
            settings=settings,
            authenticated_user_id=user_account_id,
            provider_key=OLLAMA_ADAPTER_KEY,
            display_name=body.display_name,
            base_url=body.base_url,
            api_key=body.api_key or "",
            auth_mode=body.auth_mode,
            default_model=body.default_model,
            model_list_path=body.model_list_path,
            healthcheck_path=body.healthcheck_path,
            invoke_path=body.invoke_path,
            metadata=body.metadata,
        )
        discovery = _discover_provider_capability(provider=provider, settings=settings)
        refreshed_capability = _persist_discovered_provider_capability(
            settings=settings,
            user_account_id=user_account_id,
            workspace_id=provider["workspace_id"],
            provider=provider,
            outcome=discovery,
        )
        if refreshed_capability is None:
            return JSONResponse(
                status_code=409,
                content={"detail": "provider configuration changed during capability discovery"},
            )
        capability = refreshed_capability
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ProviderConfigurationChangedError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/llamacpp/register")
def register_v1_llamacpp_provider(
    request: Request,
    body: RegisterLlamaCppProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        provider, capability = _create_workspace_provider_durable(
            settings=settings,
            authenticated_user_id=user_account_id,
            provider_key=LLAMACPP_ADAPTER_KEY,
            display_name=body.display_name,
            base_url=body.base_url,
            api_key=body.api_key or "",
            auth_mode=body.auth_mode,
            default_model=body.default_model,
            model_list_path=body.model_list_path,
            healthcheck_path=body.healthcheck_path,
            invoke_path=body.invoke_path,
            metadata=body.metadata,
        )
        discovery = _discover_provider_capability(provider=provider, settings=settings)
        refreshed_capability = _persist_discovered_provider_capability(
            settings=settings,
            user_account_id=user_account_id,
            workspace_id=provider["workspace_id"],
            provider=provider,
            outcome=discovery,
        )
        if refreshed_capability is None:
            return JSONResponse(
                status_code=409,
                content={"detail": "provider configuration changed during capability discovery"},
            )
        capability = refreshed_capability
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ProviderConfigurationChangedError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/vllm/register")
def register_v1_vllm_provider(
    request: Request,
    body: RegisterVllmProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        provider, capability = _create_workspace_provider_durable(
            settings=settings,
            authenticated_user_id=user_account_id,
            provider_key=VLLM_ADAPTER_KEY,
            display_name=body.display_name,
            base_url=body.base_url,
            api_key=body.api_key or "",
            auth_mode=body.auth_mode,
            default_model=body.default_model,
            model_list_path=body.model_list_path,
            healthcheck_path=body.healthcheck_path,
            invoke_path=body.invoke_path,
            metadata=body.metadata,
        )
        discovery = _discover_provider_capability(provider=provider, settings=settings)
        refreshed_capability = _persist_discovered_provider_capability(
            settings=settings,
            user_account_id=user_account_id,
            workspace_id=provider["workspace_id"],
            provider=provider,
            outcome=discovery,
        )
        if refreshed_capability is None:
            return JSONResponse(
                status_code=409,
                content={"detail": "provider configuration changed during capability discovery"},
            )
        capability = refreshed_capability
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ProviderConfigurationChangedError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/azure/register")
def register_v1_azure_provider(
    request: Request,
    body: RegisterAzureProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    if body.auth_mode == AZURE_AUTH_MODE_API_KEY:
        credential = body.api_key
    else:
        credential = body.ad_token
    if credential is None:
        return JSONResponse(status_code=400, content={"detail": "azure credential is required"})

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        provider, capability = _create_workspace_azure_provider_durable(
            settings=settings,
            authenticated_user_id=user_account_id,
            display_name=body.display_name,
            base_url=body.base_url,
            credential=credential,
            auth_mode=body.auth_mode,
            default_model=body.default_model,
            model_list_path=body.model_list_path,
            healthcheck_path=body.healthcheck_path,
            invoke_path=body.invoke_path,
            api_version=body.api_version,
            metadata=body.metadata,
        )
        discovery = _discover_provider_capability(provider=provider, settings=settings)
        refreshed_capability = _persist_discovered_provider_capability(
            settings=settings,
            user_account_id=user_account_id,
            workspace_id=provider["workspace_id"],
            provider=provider,
            outcome=discovery,
        )
        if refreshed_capability is None:
            return JSONResponse(
                status_code=409,
                content={"detail": "provider configuration changed during capability discovery"},
            )
        capability = refreshed_capability
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ProviderConfigurationChangedError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=201,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.get("/v1/providers")
def list_v1_providers(request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        workspace_id, _ = _require_local_provider_workspace(
            settings=settings,
            user_account_id=user_account_id,
        )
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                context = get_local_workspace(conn, user_account_id=user_account_id)
                if context is None or context["workspace"]["id"] != workspace_id:
                    raise LookupError("local workspace is not bootstrapped")
                store = ContinuityStore(conn)
                providers = store.list_model_providers_for_workspace(workspace_id=workspace_id)
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    items = [_serialize_model_provider(provider) for provider in providers]
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "items": items,
                "summary": {
                    "total_count": len(items),
                    "order": list(PROVIDER_LIST_ORDER),
                },
            }
        ),
    )


@app.get("/v1/providers/{provider_id}")
def get_v1_provider(provider_id: UUID, request: Request) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        workspace_id, _ = _require_local_provider_workspace(
            settings=settings,
            user_account_id=user_account_id,
        )
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                context = get_local_workspace(conn, user_account_id=user_account_id)
                if context is None or context["workspace"]["id"] != workspace_id:
                    raise LookupError("local workspace is not bootstrapped")
                store = ContinuityStore(conn)
                provider = store.get_model_provider_for_workspace_optional(
                    provider_id=provider_id,
                    workspace_id=workspace_id,
                )
                if provider is None:
                    return JSONResponse(status_code=404, content={"detail": f"provider {provider_id} was not found"})
                capability = store.get_provider_capability_for_provider_optional(
                    provider_id=provider_id,
                    workspace_id=workspace_id,
                )
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": None if capability is None else _serialize_provider_capability(capability),
            }
        ),
    )


@app.patch("/v1/providers/{provider_id}")
def update_v1_provider(
    provider_id: UUID,
    request: Request,
    body: UpdateProviderRequest,
) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        provider, capability = _update_workspace_provider_durable(
            settings=settings,
            authenticated_user_id=user_account_id,
            provider_id=provider_id,
            display_name=body.display_name,
            base_url=body.base_url,
            api_key=body.api_key,
            ad_token=body.ad_token,
            auth_mode=body.auth_mode,
            default_model=body.default_model,
            model_list_path=body.model_list_path,
            healthcheck_path=body.healthcheck_path,
            invoke_path=body.invoke_path,
            api_version=body.api_version,
            metadata=body.metadata,
        )
        discovery = _discover_provider_capability(provider=provider, settings=settings)
        refreshed_capability = _persist_discovered_provider_capability(
            settings=settings,
            user_account_id=user_account_id,
            workspace_id=provider["workspace_id"],
            provider=provider,
            outcome=discovery,
        )
        if refreshed_capability is None:
            return JSONResponse(
                status_code=409,
                content={"detail": "provider configuration changed during capability discovery"},
            )
        capability = refreshed_capability
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ProviderConfigurationChangedError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
    except psycopg.errors.UniqueViolation:
        return JSONResponse(
            status_code=409,
            content={"detail": "provider display_name must be unique within the workspace"},
        )
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
            }
        ),
    )


@app.post("/v1/providers/test")
def test_v1_provider(request: Request, body: TestProviderRequest) -> JSONResponse:
    settings = get_settings()

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        workspace_id, _ = _require_local_provider_workspace(
            settings=settings,
            user_account_id=user_account_id,
        )
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                context = get_local_workspace(conn, user_account_id=user_account_id)
                if context is None or context["workspace"]["id"] != workspace_id:
                    raise LookupError("local workspace is not bootstrapped")
                provider = ContinuityStore(conn).get_model_provider_for_workspace_optional(
                    provider_id=body.provider_id,
                    workspace_id=workspace_id,
                )
                if provider is None:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": f"provider {body.provider_id} was not found"},
                    )

        runtime_provider = resolve_runtime_provider_config_secrets(
            config=RuntimeProviderConfig.from_row(_object_dict(provider)),
            settings=settings,
        )
        adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
        model_name = (body.model or runtime_provider.default_model).strip()
        if model_name == "":
            raise ValueError("model is required")

        discovery = _discover_provider_capability(provider=provider, settings=settings)
        invocation_outcome: _RuntimeProviderInvocationOutcome | None = None
        model_response: ModelInvocationResponse | None = None
        if discovery.discovery_status == "ready":
            model_request = build_provider_test_model_request(
                runtime_provider=runtime_provider.model_provider,
                model=model_name,
                prompt_text=body.prompt.strip(),
            )
            invocation_outcome = _attempt_runtime_provider_model(
                adapter=adapter,
                runtime_provider=runtime_provider,
                settings=settings,
                model_request=model_request,
            )
            model_response = invocation_outcome.response
            if invocation_outcome.error is not None:
                discovery = _ProviderDiscoveryOutcome(
                    adapter_key=discovery.adapter_key,
                    discovery_status="failed",
                    capability_snapshot=discovery.capability_snapshot,
                    discovery_error=invocation_outcome.error_detail,
                )

        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            with conn.transaction():
                persisted_context = get_local_workspace(conn, user_account_id=user_account_id)
                if persisted_context is None or persisted_context["workspace"]["id"] != workspace_id:
                    raise LookupError("local workspace is not bootstrapped")
                store = ContinuityStore(conn)
                capability = store.upsert_provider_capability_if_current(
                    workspace_id=workspace_id,
                    provider_id=provider["id"],
                    discovered_by_user_account_id=user_account_id,
                    adapter_key=discovery.adapter_key,
                    discovery_status=discovery.discovery_status,
                    capability_snapshot=discovery.capability_snapshot,
                    discovery_error=discovery.discovery_error,
                    expected_config_revision=provider["config_revision"],
                    expected_config_fingerprint_sha256=provider["config_fingerprint_sha256"],
                )
                if capability is None:
                    return JSONResponse(
                        status_code=409,
                        content={"detail": "provider configuration changed during provider test"},
                    )
                if invocation_outcome is not None:
                    _record_runtime_provider_invocation(
                        store=store,
                        workspace_id=workspace_id,
                        invoked_by_user_account_id=user_account_id,
                        thread_id=None,
                        invocation_kind="provider_test",
                        adapter=adapter,
                        runtime_provider=runtime_provider,
                        model_request=model_request,
                        outcome=invocation_outcome,
                    )
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})
    except PermissionError as exc:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    if discovery.discovery_status != "ready" or model_response is None:
        return JSONResponse(
            status_code=502,
            content=jsonable_encoder(
                {
                    "detail": discovery.discovery_error or "provider test failed",
                    "provider": _serialize_model_provider(provider),
                    "capabilities": _serialize_provider_capability(capability),
                }
            ),
        )

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            {
                "provider": _serialize_model_provider(provider),
                "capabilities": _serialize_provider_capability(capability),
                "result": {
                    "provider": model_response.provider,
                    "model": model_response.model,
                    "response_id": model_response.response_id,
                    "finish_reason": model_response.finish_reason,
                    "text": model_response.output_text,
                    "usage": model_response.usage,
                },
            }
        ),
    )


@app.post("/v1/runtime/invoke")
def invoke_v1_runtime(request: Request, body: RuntimeInvokeRequest) -> JSONResponse:
    settings = get_settings()
    raw_idempotency_key = request.headers.get("idempotency-key")
    if raw_idempotency_key is None or raw_idempotency_key.strip() == "":
        return JSONResponse(
            status_code=428,
            content={"detail": "Idempotency-Key header is required"},
        )
    try:
        normalized_idempotency_key = normalize_idempotency_key(raw_idempotency_key)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    workspace_id: UUID | None = None
    user_account_id: UUID | None = None
    unresolved_runtime_provider: RuntimeProviderConfig | None = None
    runtime_provider: RuntimeProviderConfig | None = None

    try:
        user_account_id = _resolve_authenticated_v1_user_id(settings, request)
        workspace_id, _ = _require_local_provider_workspace(
            settings=settings,
            user_account_id=user_account_id,
        )
    except LookupError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    if workspace_id is None or user_account_id is None:
        return JSONResponse(status_code=500, content={"detail": "runtime context could not be resolved"})

    fingerprint = request_fingerprint(
        cast(
            JsonObject,
            {
                "workspace_id": str(workspace_id),
                "body": body.model_dump(mode="json"),
            },
        )
    )

    # Atomically reserve or lock the stable request identity before touching
    # provider configuration, secret files, DNS, or adapters. This
    # closes the absent-row lookup/create race while preserving terminal replay
    # even if mutable runtime configuration is later removed.
    try:
        with user_connection(settings.database_url, user_account_id) as conn:
            set_current_user_account(conn, user_account_id)
            job_store = ResponseGenerationJobStore(conn)
            initial_lookup = job_store.create_or_get_for_update(
                user_id=user_account_id,
                workspace_id=workspace_id,
                endpoint=RESPONSE_JOB_ENDPOINT_RUNTIME,
                idempotency_key=normalized_idempotency_key,
                request_fingerprint_sha256=fingerprint,
            )
            replay = _response_job_replay_or_in_progress(
                store=job_store,
                job=initial_lookup.job,
                expected_request_fingerprint=fingerprint,
            )
            if replay is not None:
                return replay
    except ResponseJobFenceLostError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    # Fetch only database-backed provider state while the transaction
    # is open. Credential resolution and network-address validation happen after
    # the connection is released.
    try:
        with user_connection(settings.database_url, user_account_id) as conn:
            set_current_user_account(conn, user_account_id)
            store = ContinuityStore(conn)
            provider_row = store.get_model_provider_for_workspace_optional(
                provider_id=body.provider_id,
                workspace_id=workspace_id,
            )
            if provider_row is None:
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"provider {body.provider_id} was not found"},
                )
            unresolved_runtime_provider = RuntimeProviderConfig.from_row(_object_dict(provider_row))

        validate_provider_base_url(unresolved_runtime_provider.base_url)
        runtime_provider = resolve_runtime_provider_config_secrets(
            config=unresolved_runtime_provider,
            settings=settings,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except ProviderSecretManagerError as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    if runtime_provider is None:
        return JSONResponse(status_code=500, content={"detail": "runtime provider could not be resolved"})

    selected_model = (body.model or runtime_provider.default_model).strip()
    if selected_model == "":
        return JSONResponse(status_code=400, content={"detail": "model is required"})

    runtime_limits = ContextCompilerLimits(
        max_sessions=body.max_sessions,
        max_events=body.max_events,
        max_memories=body.max_memories,
        max_entities=body.max_entities,
        max_entity_edges=body.max_entity_edges,
    )
    try:
        adapter = provider_adapter_registry.resolve(runtime_provider.provider_key)
    except ProviderAdapterNotFoundError as exc:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    try:
        with user_connection(settings.database_url, user_account_id) as conn:
            set_current_user_account(conn, user_account_id)
            store = ContinuityStore(conn)
            job_store = ResponseGenerationJobStore(conn)
            lookup = job_store.create_or_get_for_update(
                user_id=user_account_id,
                workspace_id=workspace_id,
                endpoint=RESPONSE_JOB_ENDPOINT_RUNTIME,
                idempotency_key=normalized_idempotency_key,
                request_fingerprint_sha256=fingerprint,
            )
            replay = _response_job_replay_or_in_progress(
                store=job_store,
                job=lookup.job,
                expected_request_fingerprint=fingerprint,
            )
            if replay is not None:
                return replay
            prepared = prepare_response_generation(
                store=store,
                settings=settings,
                user_id=user_account_id,
                thread_id=body.thread_id,
                message_text=body.message,
                limits=runtime_limits,
                runtime_override=(runtime_provider.model_provider, selected_model),
                system_instruction=SYSTEM_INSTRUCTION,
                developer_instruction=DEVELOPER_INSTRUCTION,
            )
            lease_token = uuid4()
            claimed_job = job_store.claim_pending(
                job_id=lookup.job["id"],
                lease_token=lease_token,
                lease_seconds=RESPONSE_JOB_LEASE_SECONDS,
                user_event_id=prepared.user_event_id,
                user_event_sequence_no=prepared.user_event_sequence_no,
            )
    except ContinuityStoreInvariantError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ResponseJobFenceLostError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    outcome = _attempt_runtime_provider_model(
        adapter=adapter,
        runtime_provider=runtime_provider,
        settings=settings,
        model_request=prepared.model_request,
    )

    try:
        with user_connection(settings.database_url, user_account_id) as conn:
            set_current_user_account(conn, user_account_id)
            store = ContinuityStore(conn)
            _record_runtime_provider_invocation(
                store=store,
                workspace_id=workspace_id,
                invoked_by_user_account_id=user_account_id,
                thread_id=body.thread_id,
                invocation_kind="runtime_invoke",
                adapter=adapter,
                runtime_provider=runtime_provider,
                model_request=prepared.model_request,
                outcome=outcome,
            )
            response_conflict = False
            result: GenerateResponseSuccess | ResponseFailure
            if outcome.error is not None:
                result = fail_response_generation(
                    store=store,
                    prepared=prepared,
                    error=outcome.error,
                )
            else:
                model_response = outcome.response
                if model_response is None:  # pragma: no cover - outcome invariant
                    raise ModelInvocationError("model provider returned no outcome")
                try:
                    result = complete_response_generation(
                        store=store,
                        prepared=prepared,
                        model_response=model_response,
                    )
                except ResponseGenerationConflictError as exc:
                    response_conflict = True
                    result = fail_response_generation(
                        store=store,
                        prepared=prepared,
                        error=ModelInvocationError(str(exc)),
                    )
            response_metadata: JsonObject = {
                "workspace_id": str(workspace_id),
            }
            if isinstance(result, ResponseFailure):
                status_code = 409 if response_conflict else 502
                response_payload = cast(
                    JsonObject,
                    jsonable_encoder(
                        {
                            "detail": result.detail,
                            "trace": result.trace,
                            "metadata": {
                                **response_metadata,
                                "provider_id": str(runtime_provider.provider_id),
                                "provider_key": runtime_provider.provider_key,
                            },
                        }
                    ),
                )
                terminal_state = "failed"
            else:
                successful_model_response = outcome.response
                if successful_model_response is None:  # pragma: no cover - outcome invariant
                    raise ModelInvocationError("model provider returned no outcome")
                response_payload = cast(
                    JsonObject,
                    jsonable_encoder(
                        {
                            "assistant": {
                                "event_id": result["assistant"]["event_id"],
                                "sequence_no": result["assistant"]["sequence_no"],
                                "provider_id": str(runtime_provider.provider_id),
                                "provider_key": runtime_provider.provider_key,
                                "model_provider": result["assistant"]["model_provider"],
                                "model": result["assistant"]["model"],
                                "response_id": successful_model_response.response_id,
                                "finish_reason": successful_model_response.finish_reason,
                                "text": result["assistant"]["text"],
                                "usage": successful_model_response.usage,
                            },
                            "trace": result["trace"],
                            "metadata": response_metadata,
                        }
                    ),
                )
                status_code = 200
                terminal_state = "succeeded"

            terminal_job = ResponseGenerationJobStore(conn).finalize(
                job_id=claimed_job["id"],
                lease_token=lease_token,
                state=terminal_state,
                status_code=status_code,
                payload=response_payload,
            )
    except ContinuityStoreInvariantError as exc:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    except ResponseJobFenceLostError as exc:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    return JSONResponse(
        status_code=status_code,
        headers=_response_job_headers(terminal_job, replayed=False),
        content=response_payload,
    )


def _apply_legacy_surface_mount_policy() -> None:
    if LEGACY_SURFACES_ENABLED:
        return

    retained_routes = []
    for route in app.router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not isinstance(path, str) or not isinstance(methods, set):
            retained_routes.append(route)
            continue
        operation_keys = {
            (method, path)
            for method in methods
            if method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        }
        gated_keys = operation_keys & LEGACY_HTTP_OPERATION_KEYS
        if gated_keys:
            if operation_keys != gated_keys:  # pragma: no cover - one-operation route invariant
                raise RuntimeError(f"legacy surface route mixes gated and retained methods: {path}")
            continue
        retained_routes.append(route)
    app.router.routes[:] = retained_routes


_apply_legacy_surface_mount_policy()
