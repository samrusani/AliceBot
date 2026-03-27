from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, NotRequired, TypeAlias, TypedDict
from uuid import UUID

from alicebot_api.store import JsonObject, JsonValue

DecisionKind = Literal["included", "excluded"]
AdmissionAction = Literal["NOOP", "ADD", "UPDATE", "DELETE"]
MemoryStatus = Literal["active", "deleted"]
OpenLoopStatus = Literal["open", "resolved", "dismissed"]
OpenLoopStatusFilter = Literal["open", "resolved", "dismissed", "all"]
MemoryType = Literal[
    "preference",
    "identity_fact",
    "relationship_fact",
    "project_fact",
    "decision",
    "commitment",
    "routine",
    "constraint",
    "working_style",
]
MemoryConfirmationStatus = Literal["unconfirmed", "confirmed", "contested"]
MemoryReviewStatusFilter = Literal["active", "deleted", "all"]
MemoryReviewLabelValue = Literal["correct", "incorrect", "outdated", "insufficient_evidence"]
EntityType = Literal["person", "merchant", "product", "project", "routine"]
EmbeddingConfigStatus = Literal["active", "deprecated", "disabled"]
ConsentStatus = Literal["granted", "revoked"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
ApprovalResolutionAction = Literal["approve", "reject"]
ApprovalResolutionOutcome = Literal["resolved", "duplicate_rejected", "conflict_rejected"]
TaskStatus = Literal["pending_approval", "approved", "executed", "denied", "blocked"]
TaskRunStatus = Literal["queued", "running", "waiting", "waiting_approval", "paused", "completed", "cancelled"]
TaskRunStopReason = Literal["wait_state", "waiting_approval", "budget_exhausted", "paused", "completed", "cancelled"]
TaskWorkspaceStatus = Literal["active"]
TaskArtifactStatus = Literal["registered"]
TaskArtifactIngestionStatus = Literal["pending", "ingested"]
TaskArtifactChunkRetrievalScopeKind = Literal["task", "artifact"]
TaskArtifactChunkEmbeddingListScopeKind = Literal["artifact", "chunk"]
TaskLifecycleSource = Literal[
    "approval_request",
    "approval_resolution",
    "proxy_execution",
    "task_step_continuation",
    "task_step_sequence",
    "task_step_transition",
]
TaskStepKind = Literal["governed_request"]
TaskStepStatus = Literal["created", "approved", "executed", "blocked", "denied"]
ProxyExecutionStatus = Literal["completed", "blocked"]
ExecutionBudgetStatus = Literal["active", "inactive", "superseded"]
ExecutionBudgetDecision = Literal["allow", "block"]
ExecutionBudgetDecisionReason = Literal[
    "no_matching_budget",
    "within_budget",
    "budget_exceeded",
    "invalid_request_context",
]
ExecutionBudgetContextResolution = Literal["resolved", "invalid"]
ExecutionBudgetCountScope = Literal["lifetime", "rolling_window"]
ExecutionBudgetLifecycleAction = Literal["deactivate", "supersede"]
ExecutionBudgetLifecycleOutcome = Literal["deactivated", "superseded", "rejected"]
PolicyEffect = Literal["allow", "deny", "require_approval"]
PolicyEvaluationReasonCode = Literal[
    "matched_policy",
    "policy_effect_allow",
    "policy_effect_deny",
    "policy_effect_require_approval",
    "consent_missing",
    "consent_revoked",
    "no_matching_policy",
]
ToolMetadataVersion = Literal["tool_metadata_v0"]
ToolAllowlistReasonCode = Literal[
    "tool_metadata_matched",
    "tool_action_unsupported",
    "tool_scope_unsupported",
    "tool_domain_mismatch",
    "tool_risk_mismatch",
    "matched_policy",
    "policy_effect_allow",
    "policy_effect_deny",
    "policy_effect_require_approval",
    "consent_missing",
    "consent_revoked",
    "no_matching_policy",
]
ToolAllowlistDecision = Literal["allowed", "denied", "approval_required"]
ToolRoutingDecision = Literal["ready", "denied", "approval_required"]
PromptSectionName = Literal["system", "developer", "context", "conversation"]
ModelProvider = Literal["openai_responses"]
ModelFinishReason = Literal["completed", "incomplete"]
ExplicitPreferencePattern = Literal[
    "i_like",
    "i_dont_like",
    "i_prefer",
    "remember_that_i_like",
    "remember_that_i_dont_like",
    "remember_that_i_prefer",
]
ExplicitCommitmentPattern = Literal[
    "remind_me_to",
    "i_need_to",
    "dont_let_me_forget_to",
    "remember_to",
]
ExplicitCommitmentOpenLoopDecision = Literal[
    "CREATED",
    "NOOP_ACTIVE_EXISTS",
    "NOOP_MEMORY_NOT_PERSISTED",
]
MemorySelectionSource = Literal["symbolic", "semantic"]
ArtifactSelectionSource = Literal["lexical", "semantic"]

DEFAULT_MAX_SESSIONS = 3
DEFAULT_MAX_EVENTS = 8
DEFAULT_MAX_MEMORIES = 5
DEFAULT_MAX_ENTITIES = 5
DEFAULT_MAX_ENTITY_EDGES = 10
DEFAULT_MEMORY_REVIEW_LIMIT = 20
MAX_MEMORY_REVIEW_LIMIT = 100
DEFAULT_OPEN_LOOP_LIMIT = 20
MAX_OPEN_LOOP_LIMIT = 100
DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT = 8
MAX_RESUMPTION_BRIEF_EVENT_LIMIT = 50
DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT = 5
MAX_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT = 20
DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT = 5
MAX_RESUMPTION_BRIEF_MEMORY_LIMIT = 20
DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT = 5
MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT = 50
DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT = 5
MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT = 50
DEFAULT_CALENDAR_EVENT_LIST_LIMIT = 20
MAX_CALENDAR_EVENT_LIST_LIMIT = 50
COMPILER_VERSION_V0 = "continuity_v0"
PROMPT_ASSEMBLY_VERSION_V0 = "prompt_assembly_v0"
RESPONSE_GENERATION_VERSION_V0 = "response_generation_v0"
TRACE_KIND_CONTEXT_COMPILE = "context.compile"
TRACE_KIND_RESPONSE_GENERATE = "response.generate"
TRACE_REVIEW_LIST_ORDER = ["created_at_desc", "id_desc"]
TRACE_REVIEW_EVENT_LIST_ORDER = ["sequence_no_asc", "id_asc"]
THREAD_LIST_ORDER = ["created_at_desc", "id_desc"]
AGENT_PROFILE_LIST_ORDER = ["id_asc"]
THREAD_SESSION_LIST_ORDER = ["started_at_asc", "created_at_asc", "id_asc"]
THREAD_EVENT_LIST_ORDER = ["sequence_no_asc"]
DEFAULT_AGENT_PROFILE_ID = "assistant_default"
RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0 = "resumption_brief_v0"
RESUMPTION_BRIEF_CONVERSATION_EVENT_KINDS = ["message.user", "message.assistant"]
RESUMPTION_BRIEF_CONVERSATION_ORDER = ["sequence_no_asc"]
RESUMPTION_BRIEF_MEMORY_ORDER = ["updated_at_asc", "created_at_asc", "id_asc"]
MEMORY_REVIEW_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
MEMORY_REVIEW_QUEUE_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
MEMORY_REVISION_REVIEW_ORDER = ["sequence_no_asc"]
MEMORY_REVIEW_LABEL_VALUES = [
    "correct",
    "incorrect",
    "outdated",
    "insufficient_evidence",
]
MEMORY_REVIEW_LABEL_ORDER = ["created_at_asc", "id_asc"]
OPEN_LOOP_REVIEW_ORDER = ["opened_at_desc", "created_at_desc", "id_desc"]
MEMORY_TYPES = [
    "preference",
    "identity_fact",
    "relationship_fact",
    "project_fact",
    "decision",
    "commitment",
    "routine",
    "constraint",
    "working_style",
]
MEMORY_CONFIRMATION_STATUSES = [
    "unconfirmed",
    "confirmed",
    "contested",
]
OPEN_LOOP_STATUSES = [
    "open",
    "resolved",
    "dismissed",
]
DEFAULT_MEMORY_TYPE: MemoryType = "preference"
DEFAULT_MEMORY_CONFIRMATION_STATUS: MemoryConfirmationStatus = "unconfirmed"
ENTITY_TYPES = [
    "person",
    "merchant",
    "product",
    "project",
    "routine",
]
ENTITY_LIST_ORDER = ["created_at_asc", "id_asc"]
ENTITY_EDGE_LIST_ORDER = ["created_at_asc", "id_asc"]
EMBEDDING_CONFIG_LIST_ORDER = ["created_at_asc", "id_asc"]
MEMORY_EMBEDDING_LIST_ORDER = ["created_at_asc", "id_asc"]
SEMANTIC_MEMORY_RETRIEVAL_ORDER = ["score_desc", "created_at_asc", "id_asc"]
EMBEDDING_CONFIG_STATUSES = ["active", "deprecated", "disabled"]
CONSENT_STATUSES = ["granted", "revoked"]
CONSENT_LIST_ORDER = ["consent_key_asc", "created_at_asc", "id_asc"]
POLICY_EFFECTS = ["allow", "deny", "require_approval"]
POLICY_LIST_ORDER = ["priority_asc", "created_at_asc", "id_asc"]
POLICY_EVALUATION_VERSION_V0 = "policy_evaluation_v0"
TRACE_KIND_POLICY_EVALUATE = "policy.evaluate"
TOOL_METADATA_VERSION_V0 = "tool_metadata_v0"
TOOL_LIST_ORDER = ["tool_key_asc", "version_asc", "created_at_asc", "id_asc"]
TOOL_ALLOWLIST_EVALUATION_VERSION_V0 = "tool_allowlist_evaluation_v0"
TRACE_KIND_TOOL_ALLOWLIST_EVALUATE = "tool.allowlist.evaluate"
TOOL_ROUTING_VERSION_V0 = "tool_routing_v0"
TRACE_KIND_TOOL_ROUTE = "tool.route"
APPROVAL_LIST_ORDER = ["created_at_asc", "id_asc"]
TASK_LIST_ORDER = ["created_at_asc", "id_asc"]
TASK_WORKSPACE_LIST_ORDER = ["created_at_asc", "id_asc"]
GMAIL_ACCOUNT_LIST_ORDER = ["created_at_asc", "id_asc"]
CALENDAR_ACCOUNT_LIST_ORDER = ["created_at_asc", "id_asc"]
CALENDAR_EVENT_LIST_ORDER = ["start_time_asc", "provider_event_id_asc"]
TASK_ARTIFACT_LIST_ORDER = ["created_at_asc", "id_asc"]
TASK_ARTIFACT_CHUNK_LIST_ORDER = ["sequence_no_asc", "id_asc"]
TASK_ARTIFACT_CHUNK_EMBEDDING_LIST_ORDER = [
    "task_artifact_chunk_sequence_no_asc",
    "created_at_asc",
    "id_asc",
]
TASK_ARTIFACT_CHUNK_RETRIEVAL_ORDER = [
    "matched_query_term_count_desc",
    "first_match_char_start_asc",
    "relative_path_asc",
    "sequence_no_asc",
    "id_asc",
]
TASK_ARTIFACT_CHUNK_SEMANTIC_RETRIEVAL_ORDER = [
    "score_desc",
    "relative_path_asc",
    "sequence_no_asc",
    "id_asc",
]
TASK_STEP_LIST_ORDER = ["sequence_no_asc", "created_at_asc", "id_asc"]
TOOL_EXECUTION_LIST_ORDER = ["executed_at_asc", "id_asc"]
EXECUTION_BUDGET_LIST_ORDER = ["created_at_asc", "id_asc"]
EXECUTION_BUDGET_MATCH_ORDER = ["specificity_desc", "created_at_asc", "id_asc"]
EXECUTION_BUDGET_STATUSES = ["active", "inactive", "superseded"]
TASK_STATUSES = ["pending_approval", "approved", "executed", "denied", "blocked"]
TASK_RUN_STATUSES = ["queued", "running", "waiting", "waiting_approval", "paused", "completed", "cancelled"]
TASK_RUN_STOP_REASONS = ["wait_state", "waiting_approval", "budget_exhausted", "paused", "completed", "cancelled"]
TASK_RUN_LIST_ORDER = ["created_at_asc", "id_asc"]
TASK_WORKSPACE_STATUSES = ["active"]
TASK_ARTIFACT_STATUSES = ["registered"]
TASK_ARTIFACT_INGESTION_STATUSES = ["pending", "ingested"]
TASK_STEP_KINDS = ["governed_request"]
TASK_STEP_STATUSES = ["created", "approved", "executed", "blocked", "denied"]
APPROVAL_REQUEST_VERSION_V0 = "approval_request_v0"
TRACE_KIND_APPROVAL_REQUEST = "approval.request"
APPROVAL_RESOLUTION_VERSION_V0 = "approval_resolution_v0"
TRACE_KIND_APPROVAL_RESOLUTION = "approval.resolve"
TRACE_KIND_APPROVAL_RESOLVE = TRACE_KIND_APPROVAL_RESOLUTION
PROXY_EXECUTION_VERSION_V0 = "proxy_execution_v0"
TRACE_KIND_PROXY_EXECUTE = "tool.proxy.execute"
GMAIL_PROVIDER = "gmail"
GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN = "oauth_access_token"
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_PROTECTED_CREDENTIAL_KIND = "gmail_oauth_access_token_v1"
GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND = "gmail_oauth_refresh_token_v2"
CALENDAR_PROVIDER = "google_calendar"
CALENDAR_AUTH_KIND_OAUTH_ACCESS_TOKEN = "oauth_access_token"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
CALENDAR_PROTECTED_CREDENTIAL_KIND = "calendar_oauth_access_token_v1"
TASK_STEP_SEQUENCE_VERSION_V0 = "task_step_sequence_v0"
TRACE_KIND_TASK_STEP_SEQUENCE = "task.step.sequence"
TASK_STEP_CONTINUATION_VERSION_V0 = "task_step_continuation_v0"
TRACE_KIND_TASK_STEP_CONTINUATION = "task.step.continuation"
TASK_STEP_TRANSITION_VERSION_V0 = "task_step_transition_v0"
TRACE_KIND_TASK_STEP_TRANSITION = "task.step.transition"
EXECUTION_BUDGET_LIFECYCLE_VERSION_V0 = "execution_budget_lifecycle_v0"
TRACE_KIND_EXECUTION_BUDGET_LIFECYCLE = "execution_budget.lifecycle"


@dataclass(frozen=True, slots=True)
class ContextCompilerLimits:
    max_sessions: int = DEFAULT_MAX_SESSIONS
    max_events: int = DEFAULT_MAX_EVENTS
    max_memories: int = DEFAULT_MAX_MEMORIES
    max_entities: int = DEFAULT_MAX_ENTITIES
    max_entity_edges: int = DEFAULT_MAX_ENTITY_EDGES

    def as_payload(self) -> JsonObject:
        return {
            "max_sessions": self.max_sessions,
            "max_events": self.max_events,
            "max_memories": self.max_memories,
            "max_entities": self.max_entities,
            "max_entity_edges": self.max_entity_edges,
        }


@dataclass(frozen=True, slots=True)
class CompileContextSemanticRetrievalInput:
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class CompileContextTaskScopedArtifactRetrievalInput:
    task_id: UUID
    query: str
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "kind": "task",
            "task_id": str(self.task_id),
            "query": self.query,
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class CompileContextArtifactScopedArtifactRetrievalInput:
    task_artifact_id: UUID
    query: str
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "kind": "artifact",
            "task_artifact_id": str(self.task_artifact_id),
            "query": self.query,
            "limit": self.limit,
        }


CompileContextArtifactRetrievalInput: TypeAlias = (
    CompileContextTaskScopedArtifactRetrievalInput
    | CompileContextArtifactScopedArtifactRetrievalInput
)


@dataclass(frozen=True, slots=True)
class CompileContextTaskScopedSemanticArtifactRetrievalInput:
    task_id: UUID
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "kind": "task",
            "task_id": str(self.task_id),
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class CompileContextArtifactScopedSemanticArtifactRetrievalInput:
    task_artifact_id: UUID
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "kind": "artifact",
            "task_artifact_id": str(self.task_artifact_id),
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


CompileContextSemanticArtifactRetrievalInput: TypeAlias = (
    CompileContextTaskScopedSemanticArtifactRetrievalInput
    | CompileContextArtifactScopedSemanticArtifactRetrievalInput
)


@dataclass(frozen=True, slots=True)
class TraceCreate:
    user_id: UUID
    thread_id: UUID
    kind: str
    compiler_version: str
    status: str
    limits: ContextCompilerLimits


@dataclass(frozen=True, slots=True)
class TraceEventRecord:
    kind: str
    payload: JsonObject


class AgentProfileRecord(TypedDict):
    id: str
    name: str
    description: str
    model_provider: ModelProvider | None
    model_name: str | None


class AgentProfileListSummary(TypedDict):
    total_count: int
    order: list[str]


class AgentProfileListResponse(TypedDict):
    items: list[AgentProfileRecord]
    summary: AgentProfileListSummary


@dataclass(frozen=True, slots=True)
class ThreadCreateInput:
    title: str
    agent_profile_id: str = DEFAULT_AGENT_PROFILE_ID


class ThreadRecord(TypedDict):
    id: str
    title: str
    agent_profile_id: str
    created_at: str
    updated_at: str


class ThreadCreateResponse(TypedDict):
    thread: ThreadRecord


class ThreadListSummary(TypedDict):
    total_count: int
    order: list[str]


class ThreadListResponse(TypedDict):
    items: list[ThreadRecord]
    summary: ThreadListSummary


class ThreadDetailResponse(TypedDict):
    thread: ThreadRecord


class ThreadSessionRecord(TypedDict):
    id: str
    thread_id: str
    status: str
    started_at: str | None
    ended_at: str | None
    created_at: str


class ThreadSessionListSummary(TypedDict):
    thread_id: str
    total_count: int
    order: list[str]


class ThreadSessionListResponse(TypedDict):
    items: list[ThreadSessionRecord]
    summary: ThreadSessionListSummary


class ThreadEventRecord(TypedDict):
    id: str
    thread_id: str
    session_id: str | None
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: str


class ThreadEventListSummary(TypedDict):
    thread_id: str
    total_count: int
    order: list[str]


class ThreadEventListResponse(TypedDict):
    items: list[ThreadEventRecord]
    summary: ThreadEventListSummary


@dataclass(frozen=True, slots=True)
class ResumptionBriefRequestInput:
    thread_id: UUID
    max_events: int = DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT
    max_open_loops: int = DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT
    max_memories: int = DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT


class TraceReviewSummaryRecord(TypedDict):
    id: str
    thread_id: str
    kind: str
    compiler_version: str
    status: str
    created_at: str
    trace_event_count: int


class TraceReviewRecord(TraceReviewSummaryRecord):
    limits: JsonObject


class TraceReviewListSummary(TypedDict):
    total_count: int
    order: list[str]


class TraceReviewListResponse(TypedDict):
    items: list[TraceReviewSummaryRecord]
    summary: TraceReviewListSummary


class TraceReviewDetailResponse(TypedDict):
    trace: TraceReviewRecord


class TraceReviewEventRecord(TypedDict):
    id: str
    trace_id: str
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: str


class TraceReviewEventListSummary(TypedDict):
    trace_id: str
    total_count: int
    order: list[str]


class TraceReviewEventListResponse(TypedDict):
    items: list[TraceReviewEventRecord]
    summary: TraceReviewEventListSummary


@dataclass(frozen=True, slots=True)
class CompilerDecision:
    kind: DecisionKind
    entity_type: str
    entity_id: UUID
    reason: str
    position: int
    metadata: JsonObject | None = None

    def to_trace_event(self) -> TraceEventRecord:
        payload: JsonObject = {
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "reason": self.reason,
            "position": self.position,
        }
        if self.metadata is not None:
            payload.update(self.metadata)
        return TraceEventRecord(kind=f"context.{self.kind}", payload=payload)


class ContextPackScope(TypedDict):
    user_id: str
    thread_id: str


class ContextPackLimits(TypedDict):
    max_sessions: int
    max_events: int
    max_memories: int
    max_entities: int
    max_entity_edges: int


class ContextPackUser(TypedDict):
    id: str
    email: str
    display_name: str | None
    created_at: str


class ContextPackThread(TypedDict):
    id: str
    title: str
    created_at: str
    updated_at: str


class ContextPackSession(TypedDict):
    id: str
    status: str
    started_at: str | None
    ended_at: str | None
    created_at: str


class ContextPackEvent(TypedDict):
    id: str
    session_id: str | None
    sequence_no: int
    kind: str
    payload: JsonObject
    created_at: str


class ContextPackMemory(TypedDict):
    id: str
    memory_key: str
    value: JsonValue
    status: MemoryStatus
    source_event_ids: list[str]
    memory_type: NotRequired[MemoryType]
    confidence: NotRequired[float | None]
    salience: NotRequired[float | None]
    confirmation_status: NotRequired[MemoryConfirmationStatus]
    valid_from: NotRequired[str | None]
    valid_to: NotRequired[str | None]
    last_confirmed_at: NotRequired[str | None]
    created_at: str
    updated_at: str
    source_provenance: "ContextPackMemorySourceProvenance"


class ContextPackMemorySourceProvenance(TypedDict):
    sources: list[MemorySelectionSource]
    semantic_score: float | None


class ContextPackHybridMemorySummary(TypedDict):
    requested: bool
    embedding_config_id: str | None
    query_vector_dimensions: int
    semantic_limit: int
    symbolic_selected_count: int
    semantic_selected_count: int
    merged_candidate_count: int
    deduplicated_count: int
    included_symbolic_only_count: int
    included_semantic_only_count: int
    included_dual_source_count: int
    similarity_metric: Literal["cosine_similarity"] | None
    source_precedence: list[MemorySelectionSource]
    symbolic_order: list[str]
    semantic_order: list[str]


class ContextPackArtifactChunk(TypedDict):
    id: str
    task_id: str
    task_artifact_id: str
    relative_path: str
    media_type: str
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    source_provenance: "ContextPackArtifactChunkSourceProvenance"


class ContextPackArtifactChunkSourceProvenance(TypedDict):
    sources: list[ArtifactSelectionSource]
    lexical_match: "TaskArtifactChunkRetrievalMatch | None"
    semantic_score: float | None


class ContextPackArtifactChunkSummary(TypedDict):
    requested: bool
    lexical_requested: bool
    semantic_requested: bool
    scope: TaskArtifactChunkRetrievalScope | None
    query: str | None
    query_terms: list[str]
    embedding_config_id: str | None
    query_vector_dimensions: int
    limit: int
    lexical_limit: int
    semantic_limit: int
    searched_artifact_count: int
    lexical_candidate_count: int
    semantic_candidate_count: int
    merged_candidate_count: int
    deduplicated_count: int
    included_count: int
    included_lexical_only_count: int
    included_semantic_only_count: int
    included_dual_source_count: int
    excluded_uningested_artifact_count: int
    excluded_limit_count: int
    matching_rule: str | None
    similarity_metric: Literal["cosine_similarity"] | None
    source_precedence: list[ArtifactSelectionSource]
    lexical_order: list[str]
    semantic_order: list[str]
    merged_order: list[str]


class ArtifactRetrievalDecisionTracePayload(TypedDict):
    scope_kind: TaskArtifactChunkRetrievalScopeKind
    task_id: str
    task_artifact_id: str
    relative_path: str
    media_type: str | None
    ingestion_status: TaskArtifactIngestionStatus
    limit: int
    matched_query_terms: NotRequired[list[str]]
    matched_query_term_count: NotRequired[int]
    first_match_char_start: NotRequired[int]
    sequence_no: NotRequired[int]
    char_start: NotRequired[int]
    char_end_exclusive: NotRequired[int]


class HybridArtifactRetrievalDecisionTracePayload(TypedDict):
    scope_kind: TaskArtifactChunkRetrievalScopeKind
    task_id: str
    task_artifact_id: str
    relative_path: str
    media_type: str | None
    ingestion_status: TaskArtifactIngestionStatus
    limit: int
    selected_sources: list[ArtifactSelectionSource]
    embedding_config_id: str | None
    query_vector_dimensions: int
    matched_query_terms: NotRequired[list[str]]
    matched_query_term_count: NotRequired[int]
    first_match_char_start: NotRequired[int]
    score: NotRequired[float]
    similarity_metric: NotRequired[Literal["cosine_similarity"]]
    sequence_no: NotRequired[int]
    char_start: NotRequired[int]
    char_end_exclusive: NotRequired[int]


class ContextPackMemorySummary(TypedDict):
    candidate_count: int
    included_count: int
    excluded_deleted_count: int
    excluded_limit_count: int
    hybrid_retrieval: ContextPackHybridMemorySummary


class ContextPackOpenLoop(TypedDict):
    id: str
    memory_id: str | None
    title: str
    status: OpenLoopStatus
    opened_at: str
    due_at: str | None
    resolved_at: str | None
    resolution_note: str | None
    created_at: str
    updated_at: str


class ContextPackOpenLoopSummary(TypedDict):
    candidate_count: int
    included_count: int
    excluded_limit_count: int
    order: list[str]


class HybridMemoryDecisionTracePayload(TypedDict):
    embedding_config_id: str | None
    memory_key: str
    status: MemoryStatus
    source_event_ids: list[str]
    selected_sources: list[MemorySelectionSource]
    semantic_score: float | None


class ContextPackEntity(TypedDict):
    id: str
    entity_type: EntityType
    name: str
    source_memory_ids: list[str]
    created_at: str


class ContextPackEntitySummary(TypedDict):
    candidate_count: int
    included_count: int
    excluded_limit_count: int


class EntityDecisionTracePayload(TypedDict):
    entity_type: str
    entity_id: str
    reason: str
    position: int
    record_entity_type: EntityType
    name: str
    source_memory_ids: list[str]


class ContextPackEntityEdge(TypedDict):
    id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    valid_from: str | None
    valid_to: str | None
    source_memory_ids: list[str]
    created_at: str


class ContextPackEntityEdgeSummary(TypedDict):
    anchor_entity_count: int
    candidate_count: int
    included_count: int
    excluded_limit_count: int


class EntityEdgeDecisionTracePayload(TypedDict):
    entity_type: str
    entity_id: str
    reason: str
    position: int
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    valid_from: str | None
    valid_to: str | None
    source_memory_ids: list[str]
    attached_included_entity_ids: list[str]


class CompiledContextPack(TypedDict):
    compiler_version: str
    scope: ContextPackScope
    limits: ContextPackLimits
    user: ContextPackUser
    thread: ContextPackThread
    sessions: list[ContextPackSession]
    events: list[ContextPackEvent]
    memories: list[ContextPackMemory]
    memory_summary: ContextPackMemorySummary
    open_loops: NotRequired[list[ContextPackOpenLoop]]
    open_loop_summary: NotRequired[ContextPackOpenLoopSummary]
    artifact_chunks: list[ContextPackArtifactChunk]
    artifact_chunk_summary: ContextPackArtifactChunkSummary
    entities: list[ContextPackEntity]
    entity_summary: ContextPackEntitySummary
    entity_edges: list[ContextPackEntityEdge]
    entity_edge_summary: ContextPackEntityEdgeSummary


@dataclass(frozen=True, slots=True)
class CompilerRunResult:
    context_pack: CompiledContextPack
    trace_events: list[TraceEventRecord]


@dataclass(frozen=True, slots=True)
class PromptAssemblyInput:
    context_pack: CompiledContextPack
    system_instruction: str
    developer_instruction: str


@dataclass(frozen=True, slots=True)
class PromptSection:
    name: PromptSectionName
    content: str


class PromptAssemblyTracePayload(TypedDict):
    version: str
    compile_trace_id: str
    compiler_version: str
    prompt_sha256: str
    prompt_char_count: int
    section_order: list[PromptSectionName]
    section_characters: dict[PromptSectionName, int]
    included_session_count: int
    included_event_count: int
    included_memory_count: int
    included_entity_count: int
    included_entity_edge_count: int


@dataclass(frozen=True, slots=True)
class PromptAssemblyResult:
    sections: tuple[PromptSection, ...]
    prompt_text: str
    prompt_sha256: str
    trace_payload: PromptAssemblyTracePayload


class ModelInvocationRequestPayload(TypedDict):
    provider: ModelProvider
    model: str
    tool_choice: Literal["none"]
    tools: list[JsonObject]
    store: bool
    sections: list[PromptSectionName]
    prompt: str


@dataclass(frozen=True, slots=True)
class ModelInvocationRequest:
    provider: ModelProvider
    model: str
    prompt: PromptAssemblyResult
    tool_choice: Literal["none"] = "none"
    store: bool = False

    def as_payload(self) -> ModelInvocationRequestPayload:
        return {
            "provider": self.provider,
            "model": self.model,
            "tool_choice": self.tool_choice,
            "tools": [],
            "store": self.store,
            "sections": [section.name for section in self.prompt.sections],
            "prompt": self.prompt.prompt_text,
        }


class ModelUsagePayload(TypedDict):
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cached_input_tokens: NotRequired[int | None]


class ModelInvocationTracePayload(TypedDict):
    provider: ModelProvider
    model: str
    tool_choice: Literal["none"]
    tools_enabled: Literal[False]
    response_id: str | None
    finish_reason: ModelFinishReason
    output_text_char_count: int
    usage: ModelUsagePayload
    error_message: str | None


@dataclass(frozen=True, slots=True)
class ModelInvocationResponse:
    provider: ModelProvider
    model: str
    response_id: str | None
    finish_reason: ModelFinishReason
    output_text: str
    usage: ModelUsagePayload

    def to_trace_payload(self, *, error_message: str | None = None) -> ModelInvocationTracePayload:
        return {
            "provider": self.provider,
            "model": self.model,
            "tool_choice": "none",
            "tools_enabled": False,
            "response_id": self.response_id,
            "finish_reason": self.finish_reason,
            "output_text_char_count": len(self.output_text),
            "usage": self.usage,
            "error_message": error_message,
        }


class AssistantResponseModelRecord(TypedDict):
    provider: ModelProvider
    model: str
    response_id: str | None
    finish_reason: ModelFinishReason
    usage: ModelUsagePayload


class AssistantResponsePromptRecord(TypedDict):
    assembly_version: str
    prompt_sha256: str
    section_order: list[PromptSectionName]


class AssistantResponseEventPayload(TypedDict):
    text: str
    model: AssistantResponseModelRecord
    prompt: AssistantResponsePromptRecord


class GeneratedAssistantRecord(TypedDict):
    event_id: str
    sequence_no: int
    text: str
    model_provider: ModelProvider
    model: str


class ResponseTraceSummary(TypedDict):
    compile_trace_id: str
    compile_trace_event_count: int
    response_trace_id: str
    response_trace_event_count: int


class GenerateResponseSuccess(TypedDict):
    assistant: GeneratedAssistantRecord
    trace: ResponseTraceSummary


@dataclass(frozen=True, slots=True)
class OpenLoopCandidateInput:
    title: str
    due_at: datetime | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "title": self.title,
        }
        payload["due_at"] = isoformat_or_none(self.due_at)
        return payload


@dataclass(frozen=True, slots=True)
class MemoryCandidateInput:
    memory_key: str
    value: JsonValue | None
    source_event_ids: tuple[UUID, ...]
    agent_profile_id: str | None = None
    delete_requested: bool = False
    memory_type: str | None = None
    confidence: float | None = None
    salience: float | None = None
    confirmation_status: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    last_confirmed_at: datetime | None = None
    open_loop: OpenLoopCandidateInput | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "memory_key": self.memory_key,
            "source_event_ids": [str(source_event_id) for source_event_id in self.source_event_ids],
            "delete_requested": self.delete_requested,
        }
        if self.agent_profile_id is not None:
            payload["agent_profile_id"] = self.agent_profile_id
        payload["value"] = self.value
        if self.memory_type is not None:
            payload["memory_type"] = self.memory_type
        if self.confidence is not None:
            payload["confidence"] = self.confidence
        if self.salience is not None:
            payload["salience"] = self.salience
        if self.confirmation_status is not None:
            payload["confirmation_status"] = self.confirmation_status
        if self.valid_from is not None:
            payload["valid_from"] = isoformat_or_none(self.valid_from)
        if self.valid_to is not None:
            payload["valid_to"] = isoformat_or_none(self.valid_to)
        if self.last_confirmed_at is not None:
            payload["last_confirmed_at"] = isoformat_or_none(self.last_confirmed_at)
        if self.open_loop is not None:
            payload["open_loop"] = self.open_loop.as_payload()
        return payload


@dataclass(frozen=True, slots=True)
class ExplicitPreferenceExtractionRequestInput:
    source_event_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "source_event_id": str(self.source_event_id),
        }


@dataclass(frozen=True, slots=True)
class ExplicitCommitmentExtractionRequestInput:
    source_event_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "source_event_id": str(self.source_event_id),
        }


@dataclass(frozen=True, slots=True)
class ExplicitSignalCaptureRequestInput:
    source_event_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "source_event_id": str(self.source_event_id),
        }


@dataclass(frozen=True, slots=True)
class OpenLoopCreateInput:
    title: str
    memory_id: UUID | None = None
    due_at: datetime | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "title": self.title,
            "memory_id": None if self.memory_id is None else str(self.memory_id),
        }
        payload["due_at"] = isoformat_or_none(self.due_at)
        return payload


@dataclass(frozen=True, slots=True)
class OpenLoopStatusUpdateInput:
    status: OpenLoopStatus
    resolution_note: str | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "status": self.status,
        }
        payload["resolution_note"] = self.resolution_note
        return payload


class ExtractedPreferenceCandidateRecord(TypedDict):
    memory_key: str
    value: JsonValue
    source_event_ids: list[str]
    delete_requested: bool
    pattern: ExplicitPreferencePattern
    subject_text: str


class ExtractedCommitmentCandidateRecord(TypedDict):
    memory_key: str
    value: JsonValue
    source_event_ids: list[str]
    delete_requested: bool
    pattern: ExplicitCommitmentPattern
    commitment_text: str
    open_loop_title: str


@dataclass(frozen=True, slots=True)
class EntityCreateInput:
    entity_type: EntityType
    name: str
    source_memory_ids: tuple[UUID, ...]

    def as_payload(self) -> JsonObject:
        return {
            "entity_type": self.entity_type,
            "name": self.name,
            "source_memory_ids": [str(source_memory_id) for source_memory_id in self.source_memory_ids],
        }


@dataclass(frozen=True, slots=True)
class EntityEdgeCreateInput:
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    valid_from: datetime | None
    valid_to: datetime | None
    source_memory_ids: tuple[UUID, ...]

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "from_entity_id": str(self.from_entity_id),
            "to_entity_id": str(self.to_entity_id),
            "relationship_type": self.relationship_type,
            "source_memory_ids": [str(source_memory_id) for source_memory_id in self.source_memory_ids],
        }
        payload["valid_from"] = isoformat_or_none(self.valid_from)
        payload["valid_to"] = isoformat_or_none(self.valid_to)
        return payload


@dataclass(frozen=True, slots=True)
class EmbeddingConfigCreateInput:
    provider: str
    model: str
    version: str
    dimensions: int
    status: EmbeddingConfigStatus
    metadata: JsonObject

    def as_payload(self) -> JsonObject:
        return {
            "provider": self.provider,
            "model": self.model,
            "version": self.version,
            "dimensions": self.dimensions,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class MemoryEmbeddingUpsertInput:
    memory_id: UUID
    embedding_config_id: UUID
    vector: tuple[float, ...]

    def as_payload(self) -> JsonObject:
        return {
            "memory_id": str(self.memory_id),
            "embedding_config_id": str(self.embedding_config_id),
            "vector": [float(value) for value in self.vector],
        }


@dataclass(frozen=True, slots=True)
class TaskArtifactChunkEmbeddingUpsertInput:
    task_artifact_chunk_id: UUID
    embedding_config_id: UUID
    vector: tuple[float, ...]

    def as_payload(self) -> JsonObject:
        return {
            "task_artifact_chunk_id": str(self.task_artifact_chunk_id),
            "embedding_config_id": str(self.embedding_config_id),
            "vector": [float(value) for value in self.vector],
        }


@dataclass(frozen=True, slots=True)
class SemanticMemoryRetrievalRequestInput:
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ConsentUpsertInput:
    consent_key: str
    status: ConsentStatus
    metadata: JsonObject

    def as_payload(self) -> JsonObject:
        return {
            "consent_key": self.consent_key,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class PolicyCreateInput:
    name: str
    action: str
    scope: str
    effect: PolicyEffect
    priority: int
    active: bool
    conditions: JsonObject
    required_consents: tuple[str, ...]
    agent_profile_id: str | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "name": self.name,
            "action": self.action,
            "scope": self.scope,
            "effect": self.effect,
            "priority": self.priority,
            "active": self.active,
            "conditions": self.conditions,
            "required_consents": list(self.required_consents),
        }
        if self.agent_profile_id is not None:
            payload["agent_profile_id"] = self.agent_profile_id
        return payload


@dataclass(frozen=True, slots=True)
class PolicyEvaluationRequestInput:
    thread_id: UUID
    action: str
    scope: str
    attributes: JsonObject

    def as_payload(self) -> JsonObject:
        return {
            "thread_id": str(self.thread_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }


@dataclass(frozen=True, slots=True)
class ToolCreateInput:
    tool_key: str
    name: str
    description: str
    version: str
    metadata_version: ToolMetadataVersion = TOOL_METADATA_VERSION_V0
    active: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)
    action_hints: tuple[str, ...] = field(default_factory=tuple)
    scope_hints: tuple[str, ...] = field(default_factory=tuple)
    domain_hints: tuple[str, ...] = field(default_factory=tuple)
    risk_hints: tuple[str, ...] = field(default_factory=tuple)
    metadata: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        return {
            "tool_key": self.tool_key,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "metadata_version": self.metadata_version,
            "active": self.active,
            "tags": list(self.tags),
            "action_hints": list(self.action_hints),
            "scope_hints": list(self.scope_hints),
            "domain_hints": list(self.domain_hints),
            "risk_hints": list(self.risk_hints),
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ToolAllowlistEvaluationRequestInput:
    thread_id: UUID
    action: str
    scope: str
    domain_hint: str | None = None
    risk_hint: str | None = None
    attributes: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "thread_id": str(self.thread_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }
        payload["domain_hint"] = self.domain_hint
        payload["risk_hint"] = self.risk_hint
        return payload


@dataclass(frozen=True, slots=True)
class ToolRoutingRequestInput:
    thread_id: UUID
    tool_id: UUID
    action: str
    scope: str
    domain_hint: str | None = None
    risk_hint: str | None = None
    attributes: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "thread_id": str(self.thread_id),
            "tool_id": str(self.tool_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }
        payload["domain_hint"] = self.domain_hint
        payload["risk_hint"] = self.risk_hint
        return payload


@dataclass(frozen=True, slots=True)
class ApprovalRequestCreateInput:
    thread_id: UUID
    tool_id: UUID
    action: str
    scope: str
    task_run_id: UUID | None = None
    domain_hint: str | None = None
    risk_hint: str | None = None
    attributes: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "thread_id": str(self.thread_id),
            "tool_id": str(self.tool_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }
        payload["task_run_id"] = None if self.task_run_id is None else str(self.task_run_id)
        payload["domain_hint"] = self.domain_hint
        payload["risk_hint"] = self.risk_hint
        return payload


@dataclass(frozen=True, slots=True)
class ApprovalApproveInput:
    approval_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "approval_id": str(self.approval_id),
            "requested_action": "approve",
        }


@dataclass(frozen=True, slots=True)
class ApprovalRejectInput:
    approval_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "approval_id": str(self.approval_id),
            "requested_action": "reject",
        }


@dataclass(frozen=True, slots=True)
class ProxyExecutionRequestInput:
    approval_id: UUID
    task_run_id: UUID | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "approval_id": str(self.approval_id),
        }
        payload["task_run_id"] = None if self.task_run_id is None else str(self.task_run_id)
        return payload


@dataclass(frozen=True, slots=True)
class ExecutionBudgetCreateInput:
    max_completed_executions: int
    tool_key: str | None = None
    domain_hint: str | None = None
    rolling_window_seconds: int | None = None
    agent_profile_id: str | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "max_completed_executions": self.max_completed_executions,
        }
        payload["tool_key"] = self.tool_key
        payload["domain_hint"] = self.domain_hint
        payload["rolling_window_seconds"] = self.rolling_window_seconds
        payload["agent_profile_id"] = self.agent_profile_id
        return payload


@dataclass(frozen=True, slots=True)
class ExecutionBudgetDeactivateInput:
    thread_id: UUID
    execution_budget_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "thread_id": str(self.thread_id),
            "execution_budget_id": str(self.execution_budget_id),
            "requested_action": "deactivate",
        }


@dataclass(frozen=True, slots=True)
class ExecutionBudgetSupersedeInput:
    thread_id: UUID
    execution_budget_id: UUID
    max_completed_executions: int

    def as_payload(self) -> JsonObject:
        return {
            "thread_id": str(self.thread_id),
            "execution_budget_id": str(self.execution_budget_id),
            "requested_action": "supersede",
            "max_completed_executions": self.max_completed_executions,
        }


class PersistedMemoryRecord(TypedDict):
    id: str
    user_id: str
    memory_key: str
    value: JsonValue
    status: MemoryStatus
    source_event_ids: list[str]
    memory_type: NotRequired[MemoryType]
    confidence: NotRequired[float | None]
    salience: NotRequired[float | None]
    confirmation_status: NotRequired[MemoryConfirmationStatus]
    valid_from: NotRequired[str | None]
    valid_to: NotRequired[str | None]
    last_confirmed_at: NotRequired[str | None]
    created_at: str
    updated_at: str
    deleted_at: str | None


class PersistedMemoryRevisionRecord(TypedDict):
    id: str
    user_id: str
    memory_id: str
    sequence_no: int
    action: AdmissionAction
    memory_key: str
    previous_value: JsonValue | None
    new_value: JsonValue | None
    source_event_ids: list[str]
    candidate: JsonObject
    created_at: str


@dataclass(frozen=True, slots=True)
class AdmissionDecisionOutput:
    action: AdmissionAction
    reason: str
    memory: PersistedMemoryRecord | None
    revision: PersistedMemoryRevisionRecord | None
    open_loop: OpenLoopRecord | None = None


class ExplicitPreferenceAdmissionRecord(TypedDict):
    decision: AdmissionAction
    reason: str
    memory: PersistedMemoryRecord | None
    revision: PersistedMemoryRevisionRecord | None


class ExplicitPreferenceExtractionSummary(TypedDict):
    source_event_id: str
    source_event_kind: str
    candidate_count: int
    admission_count: int
    persisted_change_count: int
    noop_count: int


class ExplicitPreferenceExtractionResponse(TypedDict):
    candidates: list[ExtractedPreferenceCandidateRecord]
    admissions: list[ExplicitPreferenceAdmissionRecord]
    summary: ExplicitPreferenceExtractionSummary


class ExplicitCommitmentOpenLoopOutcome(TypedDict):
    decision: ExplicitCommitmentOpenLoopDecision
    reason: str
    open_loop: OpenLoopRecord | None


class ExplicitCommitmentAdmissionRecord(TypedDict):
    decision: AdmissionAction
    reason: str
    memory: PersistedMemoryRecord | None
    revision: PersistedMemoryRevisionRecord | None
    open_loop: ExplicitCommitmentOpenLoopOutcome


class ExplicitCommitmentExtractionSummary(TypedDict):
    source_event_id: str
    source_event_kind: str
    candidate_count: int
    admission_count: int
    persisted_change_count: int
    noop_count: int
    open_loop_created_count: int
    open_loop_noop_count: int


class ExplicitCommitmentExtractionResponse(TypedDict):
    candidates: list[ExtractedCommitmentCandidateRecord]
    admissions: list[ExplicitCommitmentAdmissionRecord]
    summary: ExplicitCommitmentExtractionSummary


class ExplicitSignalCaptureSummary(TypedDict):
    source_event_id: str
    source_event_kind: str
    candidate_count: int
    admission_count: int
    persisted_change_count: int
    noop_count: int
    open_loop_created_count: int
    open_loop_noop_count: int
    preference_candidate_count: int
    preference_admission_count: int
    commitment_candidate_count: int
    commitment_admission_count: int


class ExplicitSignalCaptureResponse(TypedDict):
    preferences: ExplicitPreferenceExtractionResponse
    commitments: ExplicitCommitmentExtractionResponse
    summary: ExplicitSignalCaptureSummary


class MemoryReviewRecord(TypedDict):
    id: str
    memory_key: str
    value: JsonValue
    status: MemoryStatus
    source_event_ids: list[str]
    memory_type: NotRequired[MemoryType]
    confidence: NotRequired[float | None]
    salience: NotRequired[float | None]
    confirmation_status: NotRequired[MemoryConfirmationStatus]
    valid_from: NotRequired[str | None]
    valid_to: NotRequired[str | None]
    last_confirmed_at: NotRequired[str | None]
    created_at: str
    updated_at: str
    deleted_at: str | None


class MemoryReviewListSummary(TypedDict):
    status: MemoryReviewStatusFilter
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class MemoryReviewListResponse(TypedDict):
    items: list[MemoryReviewRecord]
    summary: MemoryReviewListSummary


class MemoryReviewDetailResponse(TypedDict):
    memory: MemoryReviewRecord


class OpenLoopRecord(TypedDict):
    id: str
    memory_id: str | None
    title: str
    status: OpenLoopStatus
    opened_at: str
    due_at: str | None
    resolved_at: str | None
    resolution_note: str | None
    created_at: str
    updated_at: str


class OpenLoopListSummary(TypedDict):
    status: OpenLoopStatusFilter
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class OpenLoopListResponse(TypedDict):
    items: list[OpenLoopRecord]
    summary: OpenLoopListSummary


class OpenLoopDetailResponse(TypedDict):
    open_loop: OpenLoopRecord


class OpenLoopCreateResponse(TypedDict):
    open_loop: OpenLoopRecord


class OpenLoopStatusUpdateResponse(TypedDict):
    open_loop: OpenLoopRecord


class MemoryRevisionReviewRecord(TypedDict):
    id: str
    memory_id: str
    sequence_no: int
    action: AdmissionAction
    memory_key: str
    previous_value: JsonValue | None
    new_value: JsonValue | None
    source_event_ids: list[str]
    created_at: str


class MemoryRevisionReviewListSummary(TypedDict):
    memory_id: str
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class MemoryRevisionReviewListResponse(TypedDict):
    items: list[MemoryRevisionReviewRecord]
    summary: MemoryRevisionReviewListSummary


class MemoryReviewLabelCounts(TypedDict):
    correct: int
    incorrect: int
    outdated: int
    insufficient_evidence: int


class MemoryReviewLabelRecord(TypedDict):
    id: str
    memory_id: str
    reviewer_user_id: str
    label: MemoryReviewLabelValue
    note: str | None
    created_at: str


class MemoryReviewLabelSummary(TypedDict):
    memory_id: str
    total_count: int
    counts_by_label: MemoryReviewLabelCounts
    order: list[str]


class MemoryReviewLabelCreateResponse(TypedDict):
    label: MemoryReviewLabelRecord
    summary: MemoryReviewLabelSummary


class MemoryReviewLabelListResponse(TypedDict):
    items: list[MemoryReviewLabelRecord]
    summary: MemoryReviewLabelSummary


class MemoryReviewQueueItem(TypedDict):
    id: str
    memory_key: str
    value: JsonValue
    status: Literal["active"]
    source_event_ids: list[str]
    memory_type: NotRequired[MemoryType]
    confidence: NotRequired[float | None]
    salience: NotRequired[float | None]
    confirmation_status: NotRequired[MemoryConfirmationStatus]
    valid_from: NotRequired[str | None]
    valid_to: NotRequired[str | None]
    last_confirmed_at: NotRequired[str | None]
    created_at: str
    updated_at: str


class MemoryReviewQueueSummary(TypedDict):
    memory_status: Literal["active"]
    review_state: Literal["unlabeled"]
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class MemoryReviewQueueResponse(TypedDict):
    items: list[MemoryReviewQueueItem]
    summary: MemoryReviewQueueSummary


class MemoryEvaluationSummary(TypedDict):
    total_memory_count: int
    active_memory_count: int
    deleted_memory_count: int
    labeled_memory_count: int
    unlabeled_memory_count: int
    total_label_row_count: int
    label_row_counts_by_value: MemoryReviewLabelCounts
    label_value_order: list[MemoryReviewLabelValue]


class MemoryEvaluationSummaryResponse(TypedDict):
    summary: MemoryEvaluationSummary


class EntityRecord(TypedDict):
    id: str
    entity_type: EntityType
    name: str
    source_memory_ids: list[str]
    created_at: str


class EntityCreateResponse(TypedDict):
    entity: EntityRecord


class EntityListSummary(TypedDict):
    total_count: int
    order: list[str]


class EntityListResponse(TypedDict):
    items: list[EntityRecord]
    summary: EntityListSummary


class EntityDetailResponse(TypedDict):
    entity: EntityRecord


class EntityEdgeRecord(ContextPackEntityEdge):
    pass


class EntityEdgeCreateResponse(TypedDict):
    edge: EntityEdgeRecord


class EntityEdgeListSummary(TypedDict):
    entity_id: str
    total_count: int
    order: list[str]


class EntityEdgeListResponse(TypedDict):
    items: list[EntityEdgeRecord]
    summary: EntityEdgeListSummary


class EmbeddingConfigRecord(TypedDict):
    id: str
    provider: str
    model: str
    version: str
    dimensions: int
    status: EmbeddingConfigStatus
    metadata: JsonObject
    created_at: str


class EmbeddingConfigCreateResponse(TypedDict):
    embedding_config: EmbeddingConfigRecord


class EmbeddingConfigListSummary(TypedDict):
    total_count: int
    order: list[str]


class EmbeddingConfigListResponse(TypedDict):
    items: list[EmbeddingConfigRecord]
    summary: EmbeddingConfigListSummary


class MemoryEmbeddingRecord(TypedDict):
    id: str
    memory_id: str
    embedding_config_id: str
    dimensions: int
    vector: list[float]
    created_at: str
    updated_at: str


class MemoryEmbeddingUpsertResponse(TypedDict):
    embedding: MemoryEmbeddingRecord
    write_mode: Literal["created", "updated"]


class MemoryEmbeddingDetailResponse(TypedDict):
    embedding: MemoryEmbeddingRecord


class MemoryEmbeddingListSummary(TypedDict):
    memory_id: str
    total_count: int
    order: list[str]


class MemoryEmbeddingListResponse(TypedDict):
    items: list[MemoryEmbeddingRecord]
    summary: MemoryEmbeddingListSummary


class SemanticMemoryRetrievalResultItem(TypedDict):
    memory_id: str
    memory_key: str
    value: JsonValue
    source_event_ids: list[str]
    memory_type: NotRequired[MemoryType]
    confidence: NotRequired[float | None]
    salience: NotRequired[float | None]
    confirmation_status: NotRequired[MemoryConfirmationStatus]
    valid_from: NotRequired[str | None]
    valid_to: NotRequired[str | None]
    last_confirmed_at: NotRequired[str | None]
    created_at: str
    updated_at: str
    score: float


class SemanticMemoryRetrievalSummary(TypedDict):
    embedding_config_id: str
    limit: int
    returned_count: int
    similarity_metric: Literal["cosine_similarity"]
    order: list[str]


class SemanticMemoryRetrievalResponse(TypedDict):
    items: list[SemanticMemoryRetrievalResultItem]
    summary: SemanticMemoryRetrievalSummary


class ConsentRecord(TypedDict):
    id: str
    consent_key: str
    status: ConsentStatus
    metadata: JsonObject
    created_at: str
    updated_at: str


class ConsentUpsertResponse(TypedDict):
    consent: ConsentRecord
    write_mode: Literal["created", "updated"]


class ConsentListSummary(TypedDict):
    total_count: int
    order: list[str]


class ConsentListResponse(TypedDict):
    items: list[ConsentRecord]
    summary: ConsentListSummary


class PolicyRecord(TypedDict):
    id: str
    agent_profile_id: str | None
    name: str
    action: str
    scope: str
    effect: PolicyEffect
    priority: int
    active: bool
    conditions: JsonObject
    required_consents: list[str]
    created_at: str
    updated_at: str


class PolicyCreateResponse(TypedDict):
    policy: PolicyRecord


class PolicyListSummary(TypedDict):
    total_count: int
    order: list[str]


class PolicyListResponse(TypedDict):
    items: list[PolicyRecord]
    summary: PolicyListSummary


class PolicyDetailResponse(TypedDict):
    policy: PolicyRecord


class PolicyEvaluationReason(TypedDict):
    code: PolicyEvaluationReasonCode
    source: Literal["policy", "consent", "system"]
    message: str
    policy_id: str | None
    consent_key: str | None


class PolicyEvaluationSummary(TypedDict):
    action: str
    scope: str
    evaluated_policy_count: int
    matched_policy_id: str | None
    order: list[str]


class PolicyEvaluationTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class PolicyEvaluationResponse(TypedDict):
    decision: PolicyEffect
    matched_policy: PolicyRecord | None
    reasons: list[PolicyEvaluationReason]
    evaluation: PolicyEvaluationSummary
    trace: PolicyEvaluationTraceSummary


class ToolRecord(TypedDict):
    id: str
    tool_key: str
    name: str
    description: str
    version: str
    metadata_version: ToolMetadataVersion
    active: bool
    tags: list[str]
    action_hints: list[str]
    scope_hints: list[str]
    domain_hints: list[str]
    risk_hints: list[str]
    metadata: JsonObject
    created_at: str


class ToolCreateResponse(TypedDict):
    tool: ToolRecord


class ToolListSummary(TypedDict):
    total_count: int
    order: list[str]


class ToolListResponse(TypedDict):
    items: list[ToolRecord]
    summary: ToolListSummary


class ToolDetailResponse(TypedDict):
    tool: ToolRecord


class ToolAllowlistReason(TypedDict):
    code: ToolAllowlistReasonCode
    source: Literal["tool", "policy", "consent", "system"]
    message: str
    tool_id: str | None
    policy_id: str | None
    consent_key: str | None


class ToolAllowlistDecisionRecord(TypedDict):
    decision: ToolAllowlistDecision
    tool: ToolRecord
    reasons: list[ToolAllowlistReason]


class ToolAllowlistEvaluationSummary(TypedDict):
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    evaluated_tool_count: int
    allowed_count: int
    denied_count: int
    approval_required_count: int
    order: list[str]


class ToolAllowlistTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ToolAllowlistEvaluationResponse(TypedDict):
    allowed: list[ToolAllowlistDecisionRecord]
    denied: list[ToolAllowlistDecisionRecord]
    approval_required: list[ToolAllowlistDecisionRecord]
    summary: ToolAllowlistEvaluationSummary
    trace: ToolAllowlistTraceSummary


class ToolRoutingRequestRecord(TypedDict):
    thread_id: str
    tool_id: str
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    attributes: JsonObject


class ToolRoutingRequestTracePayload(TypedDict):
    thread_id: str
    tool_id: str
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    attributes: JsonObject


class ToolRoutingDecisionTracePayload(TypedDict):
    tool_id: str
    tool_key: str
    tool_version: str
    allowlist_decision: ToolAllowlistDecision
    routing_decision: ToolRoutingDecision
    matched_policy_id: str | None
    reasons: list[ToolAllowlistReason]


class ToolRoutingSummaryTracePayload(TypedDict):
    decision: ToolRoutingDecision
    evaluated_tool_count: int
    active_policy_count: int
    consent_count: int


class ToolRoutingSummary(TypedDict):
    thread_id: str
    tool_id: str
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    decision: ToolRoutingDecision
    evaluated_tool_count: int
    active_policy_count: int
    consent_count: int
    order: list[str]


class ToolRoutingTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ToolRoutingResponse(TypedDict):
    request: ToolRoutingRequestRecord
    decision: ToolRoutingDecision
    tool: ToolRecord
    reasons: list[ToolAllowlistReason]
    summary: ToolRoutingSummary
    trace: ToolRoutingTraceSummary


class ApprovalRoutingRecord(TypedDict):
    decision: ToolRoutingDecision
    reasons: list[ToolAllowlistReason]
    trace: ToolRoutingTraceSummary


class ApprovalResolutionRecord(TypedDict):
    resolved_at: str
    resolved_by_user_id: str


class ApprovalRecord(TypedDict):
    id: str
    thread_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str | None
    status: ApprovalStatus
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    routing: ApprovalRoutingRecord
    created_at: str
    resolution: ApprovalResolutionRecord | None


class ApprovalRequestTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ApprovalResolutionTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ApprovalResolutionRequestTracePayload(TypedDict):
    approval_id: str
    task_step_id: str | None
    requested_action: ApprovalResolutionAction


class ApprovalResolutionStateTracePayload(TypedDict):
    approval_id: str
    task_step_id: str | None
    requested_action: ApprovalResolutionAction
    previous_status: ApprovalStatus
    outcome: ApprovalResolutionOutcome
    current_status: ApprovalStatus
    resolved_at: str | None
    resolved_by_user_id: str | None


class ApprovalResolutionSummaryTracePayload(TypedDict):
    approval_id: str
    task_step_id: str | None
    requested_action: ApprovalResolutionAction
    outcome: ApprovalResolutionOutcome
    final_status: ApprovalStatus


@dataclass(frozen=True, slots=True)
class TaskCreateInput:
    thread_id: UUID
    tool_id: UUID
    status: TaskStatus
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    latest_approval_id: UUID | None = None
    latest_execution_id: UUID | None = None


class TaskRecord(TypedDict):
    id: str
    thread_id: str
    tool_id: str
    status: TaskStatus
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    latest_approval_id: str | None
    latest_execution_id: str | None
    created_at: str
    updated_at: str


class TaskCreateResponse(TypedDict):
    task: TaskRecord


@dataclass(frozen=True, slots=True)
class TaskStepCreateInput:
    task_id: UUID
    sequence_no: int
    kind: TaskStepKind
    status: TaskStepStatus
    request: ToolRoutingRequestRecord
    outcome: "TaskStepOutcomeSnapshot"
    trace_id: UUID
    trace_kind: str


@dataclass(frozen=True, slots=True)
class TaskStepNextCreateInput:
    task_id: UUID
    kind: TaskStepKind
    status: TaskStepStatus
    request: ToolRoutingRequestRecord
    outcome: "TaskStepOutcomeSnapshot"
    lineage: "TaskStepLineageInput"


@dataclass(frozen=True, slots=True)
class TaskStepTransitionInput:
    task_step_id: UUID
    status: TaskStepStatus
    outcome: "TaskStepOutcomeSnapshot"


@dataclass(frozen=True, slots=True)
class TaskStepLineageInput:
    parent_step_id: UUID
    source_approval_id: UUID | None = None
    source_execution_id: UUID | None = None


class TaskListSummary(TypedDict):
    total_count: int
    order: list[str]


class TaskListResponse(TypedDict):
    items: list[TaskRecord]
    summary: TaskListSummary


class TaskDetailResponse(TypedDict):
    task: TaskRecord


@dataclass(frozen=True, slots=True)
class TaskRunCreateInput:
    task_id: UUID
    checkpoint: JsonObject = field(default_factory=dict)
    max_ticks: int = 1


@dataclass(frozen=True, slots=True)
class TaskRunTickInput:
    task_run_id: UUID


@dataclass(frozen=True, slots=True)
class TaskRunPauseInput:
    task_run_id: UUID


@dataclass(frozen=True, slots=True)
class TaskRunResumeInput:
    task_run_id: UUID


@dataclass(frozen=True, slots=True)
class TaskRunCancelInput:
    task_run_id: UUID


class TaskRunRecord(TypedDict):
    id: str
    task_id: str
    status: TaskRunStatus
    checkpoint: JsonObject
    tick_count: int
    step_count: int
    max_ticks: int
    stop_reason: TaskRunStopReason | None
    created_at: str
    updated_at: str


class TaskRunCreateResponse(TypedDict):
    task_run: TaskRunRecord


class TaskRunListSummary(TypedDict):
    task_id: str
    total_count: int
    order: list[str]


class TaskRunListResponse(TypedDict):
    items: list[TaskRunRecord]
    summary: TaskRunListSummary


class TaskRunDetailResponse(TypedDict):
    task_run: TaskRunRecord


class TaskRunMutationResponse(TypedDict):
    task_run: TaskRunRecord
    previous_status: TaskRunStatus


@dataclass(frozen=True, slots=True)
class GmailAccountConnectInput:
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    access_token: str
    refresh_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    access_token_expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class GmailMessageIngestInput:
    gmail_account_id: UUID
    task_workspace_id: UUID
    provider_message_id: str


class GmailAccountRecord(TypedDict):
    id: str
    provider: str
    auth_kind: str
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: str
    updated_at: str


class GmailAccountConnectResponse(TypedDict):
    account: GmailAccountRecord


class GmailAccountListSummary(TypedDict):
    total_count: int
    order: list[str]


class GmailAccountListResponse(TypedDict):
    items: list[GmailAccountRecord]
    summary: GmailAccountListSummary


class GmailAccountDetailResponse(TypedDict):
    account: GmailAccountRecord


class GmailMessageIngestionRecord(TypedDict):
    provider_message_id: str
    artifact_relative_path: str
    media_type: str


class GmailMessageIngestionResponse(TypedDict):
    account: GmailAccountRecord
    message: GmailMessageIngestionRecord
    artifact: TaskArtifactRecord
    summary: TaskArtifactChunkListSummary


@dataclass(frozen=True, slots=True)
class CalendarAccountConnectInput:
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    access_token: str


@dataclass(frozen=True, slots=True)
class CalendarEventIngestInput:
    calendar_account_id: UUID
    task_workspace_id: UUID
    provider_event_id: str


@dataclass(frozen=True, slots=True)
class CalendarEventListInput:
    calendar_account_id: UUID
    limit: int = DEFAULT_CALENDAR_EVENT_LIST_LIMIT
    time_min: datetime | None = None
    time_max: datetime | None = None


class CalendarAccountRecord(TypedDict):
    id: str
    provider: str
    auth_kind: str
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: str
    updated_at: str


class CalendarAccountConnectResponse(TypedDict):
    account: CalendarAccountRecord


class CalendarAccountListSummary(TypedDict):
    total_count: int
    order: list[str]


class CalendarAccountListResponse(TypedDict):
    items: list[CalendarAccountRecord]
    summary: CalendarAccountListSummary


class CalendarAccountDetailResponse(TypedDict):
    account: CalendarAccountRecord


class CalendarEventIngestionRecord(TypedDict):
    provider_event_id: str
    artifact_relative_path: str
    media_type: str


class CalendarEventIngestionResponse(TypedDict):
    account: CalendarAccountRecord
    event: CalendarEventIngestionRecord
    artifact: TaskArtifactRecord
    summary: TaskArtifactChunkListSummary


class CalendarEventSummaryRecord(TypedDict):
    provider_event_id: str
    status: str | None
    summary: str | None
    start_time: str | None
    end_time: str | None
    html_link: str | None
    updated_at: str | None


class CalendarEventListSummary(TypedDict):
    total_count: int
    limit: int
    order: list[str]
    time_min: str | None
    time_max: str | None


class CalendarEventListResponse(TypedDict):
    account: CalendarAccountRecord
    items: list[CalendarEventSummaryRecord]
    summary: CalendarEventListSummary


@dataclass(frozen=True, slots=True)
class TaskWorkspaceCreateInput:
    task_id: UUID
    status: TaskWorkspaceStatus


class TaskWorkspaceRecord(TypedDict):
    id: str
    task_id: str
    status: TaskWorkspaceStatus
    local_path: str
    created_at: str
    updated_at: str


class TaskWorkspaceCreateResponse(TypedDict):
    workspace: TaskWorkspaceRecord


class TaskWorkspaceListSummary(TypedDict):
    total_count: int
    order: list[str]


class TaskWorkspaceListResponse(TypedDict):
    items: list[TaskWorkspaceRecord]
    summary: TaskWorkspaceListSummary


class TaskWorkspaceDetailResponse(TypedDict):
    workspace: TaskWorkspaceRecord


@dataclass(frozen=True, slots=True)
class TaskArtifactRegisterInput:
    task_workspace_id: UUID
    local_path: str
    media_type_hint: str | None = None


@dataclass(frozen=True, slots=True)
class TaskArtifactIngestInput:
    task_artifact_id: UUID


@dataclass(frozen=True, slots=True)
class TaskScopedArtifactChunkRetrievalInput:
    task_id: UUID
    query: str


@dataclass(frozen=True, slots=True)
class ArtifactScopedArtifactChunkRetrievalInput:
    task_artifact_id: UUID
    query: str


@dataclass(frozen=True, slots=True)
class TaskScopedSemanticArtifactChunkRetrievalInput:
    task_id: UUID
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "task_id": str(self.task_id),
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ArtifactScopedSemanticArtifactChunkRetrievalInput:
    task_artifact_id: UUID
    embedding_config_id: UUID
    query_vector: tuple[float, ...]
    limit: int = DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "task_artifact_id": str(self.task_artifact_id),
            "embedding_config_id": str(self.embedding_config_id),
            "query_vector": [float(value) for value in self.query_vector],
            "limit": self.limit,
        }


class TaskArtifactRecord(TypedDict):
    id: str
    task_id: str
    task_workspace_id: str
    status: TaskArtifactStatus
    ingestion_status: TaskArtifactIngestionStatus
    relative_path: str
    media_type_hint: str | None
    created_at: str
    updated_at: str


class TaskArtifactCreateResponse(TypedDict):
    artifact: TaskArtifactRecord


class TaskArtifactListSummary(TypedDict):
    total_count: int
    order: list[str]


class TaskArtifactListResponse(TypedDict):
    items: list[TaskArtifactRecord]
    summary: TaskArtifactListSummary


class TaskArtifactDetailResponse(TypedDict):
    artifact: TaskArtifactRecord


class TaskArtifactChunkRecord(TypedDict):
    id: str
    task_artifact_id: str
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    created_at: str
    updated_at: str


class TaskArtifactChunkListSummary(TypedDict):
    total_count: int
    total_characters: int
    media_type: str
    chunking_rule: str
    order: list[str]


class TaskArtifactChunkListResponse(TypedDict):
    items: list[TaskArtifactChunkRecord]
    summary: TaskArtifactChunkListSummary


class TaskArtifactChunkEmbeddingRecord(TypedDict):
    id: str
    task_artifact_id: str
    task_artifact_chunk_id: str
    task_artifact_chunk_sequence_no: int
    embedding_config_id: str
    dimensions: int
    vector: list[float]
    created_at: str
    updated_at: str


class TaskArtifactChunkEmbeddingWriteResponse(TypedDict):
    embedding: TaskArtifactChunkEmbeddingRecord
    write_mode: Literal["created", "updated"]


class TaskArtifactChunkEmbeddingDetailResponse(TypedDict):
    embedding: TaskArtifactChunkEmbeddingRecord


class TaskArtifactChunkEmbeddingListScope(TypedDict):
    kind: TaskArtifactChunkEmbeddingListScopeKind
    task_artifact_id: str
    task_artifact_chunk_id: NotRequired[str]


class TaskArtifactChunkEmbeddingListSummary(TypedDict):
    total_count: int
    order: list[str]
    scope: TaskArtifactChunkEmbeddingListScope


class TaskArtifactChunkEmbeddingListResponse(TypedDict):
    items: list[TaskArtifactChunkEmbeddingRecord]
    summary: TaskArtifactChunkEmbeddingListSummary


class TaskArtifactIngestionResponse(TypedDict):
    artifact: TaskArtifactRecord
    summary: TaskArtifactChunkListSummary


class TaskArtifactChunkRetrievalMatch(TypedDict):
    matched_query_terms: list[str]
    matched_query_term_count: int
    first_match_char_start: int


class TaskArtifactChunkRetrievalItem(TypedDict):
    id: str
    task_id: str
    task_artifact_id: str
    relative_path: str
    media_type: str
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    match: TaskArtifactChunkRetrievalMatch


class TaskArtifactChunkRetrievalScope(TypedDict):
    kind: TaskArtifactChunkRetrievalScopeKind
    task_id: str
    task_artifact_id: NotRequired[str]


class TaskArtifactChunkRetrievalSummary(TypedDict):
    total_count: int
    searched_artifact_count: int
    query: str
    query_terms: list[str]
    matching_rule: str
    order: list[str]
    scope: TaskArtifactChunkRetrievalScope


class TaskArtifactChunkRetrievalResponse(TypedDict):
    items: list[TaskArtifactChunkRetrievalItem]
    summary: TaskArtifactChunkRetrievalSummary


class TaskArtifactChunkSemanticRetrievalItem(TypedDict):
    id: str
    task_id: str
    task_artifact_id: str
    relative_path: str
    media_type: str
    sequence_no: int
    char_start: int
    char_end_exclusive: int
    text: str
    score: float


class TaskArtifactChunkSemanticRetrievalSummary(TypedDict):
    embedding_config_id: str
    query_vector_dimensions: int
    limit: int
    returned_count: int
    searched_artifact_count: int
    similarity_metric: Literal["cosine_similarity"]
    order: list[str]
    scope: TaskArtifactChunkRetrievalScope


class TaskArtifactChunkSemanticRetrievalResponse(TypedDict):
    items: list[TaskArtifactChunkSemanticRetrievalItem]
    summary: TaskArtifactChunkSemanticRetrievalSummary


class TaskStepTraceLink(TypedDict):
    trace_id: str
    trace_kind: str


class TaskStepOutcomeSnapshot(TypedDict):
    routing_decision: ToolRoutingDecision
    approval_id: str | None
    approval_status: ApprovalStatus | None
    execution_id: str | None
    execution_status: ProxyExecutionStatus | None
    blocked_reason: str | None


class TaskStepLineageRecord(TypedDict):
    parent_step_id: str | None
    source_approval_id: str | None
    source_execution_id: str | None


class TaskStepRecord(TypedDict):
    id: str
    task_id: str
    sequence_no: int
    kind: TaskStepKind
    status: TaskStepStatus
    request: ToolRoutingRequestRecord
    outcome: TaskStepOutcomeSnapshot
    lineage: TaskStepLineageRecord
    trace: TaskStepTraceLink
    created_at: str
    updated_at: str


class TaskStepCreateResponse(TypedDict):
    task_step: TaskStepRecord


class TaskStepSequencingSummary(TypedDict):
    task_id: str
    total_count: int
    latest_sequence_no: int | None
    latest_status: TaskStepStatus | None
    next_sequence_no: int
    append_allowed: bool
    order: list[str]


class TaskStepListSummary(TaskStepSequencingSummary):
    pass


class TaskStepListResponse(TypedDict):
    items: list[TaskStepRecord]
    summary: TaskStepListSummary


class TaskStepDetailResponse(TypedDict):
    task_step: TaskStepRecord


class TaskStepMutationTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class TaskStepNextCreateResponse(TypedDict):
    task: TaskRecord
    task_step: TaskStepRecord
    sequencing: TaskStepSequencingSummary
    trace: TaskStepMutationTraceSummary


class TaskStepTransitionResponse(TypedDict):
    task: TaskRecord
    task_step: TaskStepRecord
    sequencing: TaskStepSequencingSummary
    trace: TaskStepMutationTraceSummary


class ResumptionBriefSectionSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ResumptionBriefConversationSummary(ResumptionBriefSectionSummary):
    kinds: list[str]


class ResumptionBriefConversationSection(TypedDict):
    items: list[ThreadEventRecord]
    summary: ResumptionBriefConversationSummary


class ResumptionBriefOpenLoopSection(TypedDict):
    items: list[OpenLoopRecord]
    summary: ResumptionBriefSectionSummary


class ResumptionBriefMemoryHighlightSection(TypedDict):
    items: list[ContextPackMemory]
    summary: ResumptionBriefSectionSummary


class ResumptionBriefWorkflowSummary(TypedDict):
    present: bool
    task_order: list[str]
    task_step_order: list[str]


class ResumptionBriefWorkflowPosture(TypedDict):
    task: TaskRecord
    latest_task_step: TaskStepRecord | None
    summary: ResumptionBriefWorkflowSummary


class ResumptionBriefRecord(TypedDict):
    assembly_version: str
    thread: ThreadRecord
    conversation: ResumptionBriefConversationSection
    open_loops: ResumptionBriefOpenLoopSection
    memory_highlights: ResumptionBriefMemoryHighlightSection
    workflow: ResumptionBriefWorkflowPosture | None
    sources: list[str]


class ResumptionBriefResponse(TypedDict):
    brief: ResumptionBriefRecord


class TaskLifecycleStateTracePayload(TypedDict):
    task_id: str
    source: TaskLifecycleSource
    previous_status: TaskStatus | None
    current_status: TaskStatus
    latest_approval_id: str | None
    latest_execution_id: str | None


class TaskLifecycleSummaryTracePayload(TypedDict):
    task_id: str
    source: TaskLifecycleSource
    final_status: TaskStatus
    latest_approval_id: str | None
    latest_execution_id: str | None


class TaskStepLifecycleStateTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    source: TaskLifecycleSource
    sequence_no: int
    kind: TaskStepKind
    previous_status: TaskStepStatus | None
    current_status: TaskStepStatus
    trace: TaskStepTraceLink


class TaskStepLifecycleSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    source: TaskLifecycleSource
    sequence_no: int
    kind: TaskStepKind
    final_status: TaskStepStatus
    trace: TaskStepTraceLink


class TaskStepSequenceRequestTracePayload(TypedDict):
    task_id: str
    previous_task_step_id: str
    previous_sequence_no: int
    previous_status: TaskStepStatus
    requested_kind: TaskStepKind
    requested_status: TaskStepStatus


class TaskStepSequenceStateTracePayload(TypedDict):
    task_id: str
    previous_task_step_id: str
    previous_sequence_no: int
    previous_status: TaskStepStatus
    task_step_id: str
    assigned_sequence_no: int
    kind: TaskStepKind
    current_status: TaskStepStatus


class TaskStepSequenceSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    latest_sequence_no: int
    next_sequence_no: int
    append_allowed: bool


class TaskStepContinuationRequestTracePayload(TypedDict):
    task_id: str
    parent_task_step_id: str
    parent_sequence_no: int
    parent_status: TaskStepStatus
    requested_kind: TaskStepKind
    requested_status: TaskStepStatus
    requested_source_approval_id: str | None
    requested_source_execution_id: str | None


class TaskStepContinuationLineageTracePayload(TypedDict):
    task_id: str
    parent_task_step_id: str
    parent_sequence_no: int
    parent_status: TaskStepStatus
    source_approval_id: str | None
    source_execution_id: str | None


class TaskStepContinuationSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    latest_sequence_no: int
    next_sequence_no: int
    append_allowed: bool
    lineage: TaskStepLineageRecord


class TaskStepTransitionRequestTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    sequence_no: int
    previous_status: TaskStepStatus
    requested_status: TaskStepStatus


class TaskStepTransitionStateTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    sequence_no: int
    previous_status: TaskStepStatus
    current_status: TaskStepStatus
    allowed_next_statuses: list[TaskStepStatus]
    trace: TaskStepTraceLink


class TaskStepTransitionSummaryTracePayload(TypedDict):
    task_id: str
    task_step_id: str
    sequence_no: int
    final_status: TaskStepStatus
    parent_task_status: TaskStatus
    trace: TaskStepTraceLink


class ApprovalRequestCreateResponse(TypedDict):
    request: ToolRoutingRequestRecord
    decision: ToolRoutingDecision
    tool: ToolRecord
    reasons: list[ToolAllowlistReason]
    task: TaskRecord
    approval: ApprovalRecord | None
    routing_trace: ToolRoutingTraceSummary
    trace: ApprovalRequestTraceSummary


class ApprovalListSummary(TypedDict):
    total_count: int
    order: list[str]


class ApprovalListResponse(TypedDict):
    items: list[ApprovalRecord]
    summary: ApprovalListSummary


class ApprovalDetailResponse(TypedDict):
    approval: ApprovalRecord


class ApprovalResolutionResponse(TypedDict):
    approval: ApprovalRecord
    trace: ApprovalResolutionTraceSummary


class ExecutionBudgetRecord(TypedDict):
    id: str
    agent_profile_id: str | None
    tool_key: str | None
    domain_hint: str | None
    max_completed_executions: int
    rolling_window_seconds: int | None
    status: ExecutionBudgetStatus
    deactivated_at: str | None
    superseded_by_budget_id: str | None
    supersedes_budget_id: str | None
    created_at: str


class ExecutionBudgetCreateResponse(TypedDict):
    execution_budget: ExecutionBudgetRecord


class ExecutionBudgetListSummary(TypedDict):
    total_count: int
    order: list[str]


class ExecutionBudgetListResponse(TypedDict):
    items: list[ExecutionBudgetRecord]
    summary: ExecutionBudgetListSummary


class ExecutionBudgetDetailResponse(TypedDict):
    execution_budget: ExecutionBudgetRecord


class ExecutionBudgetLifecycleTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ExecutionBudgetDeactivateResponse(TypedDict):
    execution_budget: ExecutionBudgetRecord
    trace: ExecutionBudgetLifecycleTraceSummary


class ExecutionBudgetSupersedeResponse(TypedDict):
    superseded_budget: ExecutionBudgetRecord
    replacement_budget: ExecutionBudgetRecord
    trace: ExecutionBudgetLifecycleTraceSummary


class ExecutionBudgetDecisionRecord(TypedDict):
    matched_budget_id: str | None
    tool_key: str
    domain_hint: str | None
    budget_tool_key: str | None
    budget_domain_hint: str | None
    max_completed_executions: int | None
    rolling_window_seconds: int | None
    count_scope: ExecutionBudgetCountScope
    window_started_at: str | None
    completed_execution_count: int
    projected_completed_execution_count: int
    decision: ExecutionBudgetDecision
    reason: ExecutionBudgetDecisionReason
    order: list[str]
    history_order: list[str]
    request_thread_id: NotRequired[str | None]
    context_resolution: NotRequired[ExecutionBudgetContextResolution]
    context_reason: NotRequired[str | None]


class ExecutionBudgetLifecycleRequestTracePayload(TypedDict):
    thread_id: str
    execution_budget_id: str
    requested_action: ExecutionBudgetLifecycleAction
    replacement_max_completed_executions: int | None


class ExecutionBudgetLifecycleStateTracePayload(TypedDict):
    execution_budget_id: str
    requested_action: ExecutionBudgetLifecycleAction
    previous_status: ExecutionBudgetStatus
    current_status: ExecutionBudgetStatus
    tool_key: str | None
    domain_hint: str | None
    max_completed_executions: int
    rolling_window_seconds: int | None
    deactivated_at: str | None
    superseded_by_budget_id: str | None
    supersedes_budget_id: str | None
    replacement_budget_id: str | None
    replacement_status: ExecutionBudgetStatus | None
    replacement_max_completed_executions: int | None
    replacement_rolling_window_seconds: int | None
    rejection_reason: str | None


class ExecutionBudgetLifecycleSummaryTracePayload(TypedDict):
    execution_budget_id: str
    requested_action: ExecutionBudgetLifecycleAction
    outcome: ExecutionBudgetLifecycleOutcome
    replacement_budget_id: str | None
    active_budget_id: str | None


@dataclass(frozen=True, slots=True)
class ToolExecutionCreateInput:
    approval_id: UUID
    task_step_id: UUID
    thread_id: UUID
    tool_id: UUID
    trace_id: UUID
    request_event_id: UUID | None
    result_event_id: UUID | None
    status: ProxyExecutionStatus
    handler_key: str | None
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    result: "ToolExecutionResultRecord"
    task_run_id: UUID | None = None
    idempotency_key: str | None = None


class ToolExecutionRecord(TypedDict):
    id: str
    approval_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str
    thread_id: str
    tool_id: str
    trace_id: str
    request_event_id: str | None
    result_event_id: str | None
    status: ProxyExecutionStatus
    handler_key: str | None
    idempotency_key: NotRequired[str | None]
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    result: "ToolExecutionResultRecord"
    executed_at: str


class ToolExecutionListSummary(TypedDict):
    total_count: int
    order: list[str]


class ToolExecutionListResponse(TypedDict):
    items: list[ToolExecutionRecord]
    summary: ToolExecutionListSummary


class ToolExecutionDetailResponse(TypedDict):
    execution: ToolExecutionRecord


class ProxyExecutionRequestRecord(TypedDict):
    approval_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str


class ProxyExecutionRequestEventPayload(TypedDict):
    approval_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str
    tool_id: str
    tool_key: str
    request: ToolRoutingRequestRecord


class ProxyExecutionResultRecord(TypedDict):
    handler_key: str
    status: ProxyExecutionStatus
    output: JsonObject | None


class ProxyExecutionResultEventPayload(TypedDict):
    approval_id: str
    task_step_id: str
    tool_id: str
    tool_key: str
    handler_key: str
    status: Literal["completed"]
    output: JsonObject


class ToolExecutionResultRecord(TypedDict):
    handler_key: str | None
    status: ProxyExecutionStatus
    output: JsonObject | None
    reason: str | None
    budget_decision: NotRequired[ExecutionBudgetDecisionRecord]


class ProxyExecutionEventSummary(TypedDict):
    request_event_id: str
    request_sequence_no: int
    result_event_id: str
    result_sequence_no: int


class ProxyExecutionTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ProxyExecutionBudgetPrecheckTracePayload(ExecutionBudgetDecisionRecord):
    pass


class ProxyExecutionApprovalTracePayload(TypedDict):
    approval_id: str
    task_step_id: str
    approval_status: ApprovalStatus
    eligible_for_execution: bool


class ProxyExecutionBudgetContextTracePayload(TypedDict):
    request_thread_id: str | None
    context_resolution: ExecutionBudgetContextResolution
    context_reason: str | None


class ProxyExecutionDispatchTracePayload(TypedDict):
    approval_id: str
    task_step_id: str
    tool_id: str
    tool_key: str
    handler_key: str | None
    dispatch_status: Literal["executed", "blocked"]
    reason: str | None
    result_status: ProxyExecutionStatus | None
    output: JsonObject | None
    budget_context: NotRequired[ProxyExecutionBudgetContextTracePayload]


class ProxyExecutionSummaryTracePayload(TypedDict):
    approval_id: str
    task_step_id: str
    tool_id: str
    tool_key: str
    approval_status: ApprovalStatus
    execution_status: Literal["completed", "blocked"]
    handler_key: str | None
    request_event_id: str | None
    result_event_id: str | None


class ProxyExecutionResponse(TypedDict):
    request: ProxyExecutionRequestRecord
    approval: ApprovalRecord
    tool: ToolRecord
    result: ProxyExecutionResultRecord | ToolExecutionResultRecord
    events: ProxyExecutionEventSummary | None
    trace: ProxyExecutionTraceSummary


class ProxyExecutionBudgetBlockedResponse(TypedDict):
    request: ProxyExecutionRequestRecord
    approval: ApprovalRecord
    tool: ToolRecord
    result: ToolExecutionResultRecord
    events: None
    trace: ProxyExecutionTraceSummary


def isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
