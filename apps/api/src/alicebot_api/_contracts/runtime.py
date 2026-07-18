from __future__ import annotations

from dataclasses import dataclass
import sys as _sys
from typing import TYPE_CHECKING as _TYPE_CHECKING, Literal, NotRequired, TypeAlias, TypedDict
from uuid import UUID

from alicebot_api._contracts.common import (
    ArtifactSelectionSource,
    DEFAULT_AGENT_PROFILE_ID,
    DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    DEFAULT_MAX_ENTITIES,
    DEFAULT_MAX_ENTITY_EDGES,
    DEFAULT_MAX_EVENTS,
    DEFAULT_MAX_MEMORIES,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    DecisionKind,
    EntityType,
    MemoryConfirmationStatus,
    MemoryPromotionEligibility,
    MemorySelectionSource,
    MemoryStatus,
    MemoryTrustClass,
    MemoryType,
    ModelFinishReason,
    ModelProvider,
    ModelProviderStatus,
    OpenLoopStatus,
    PromptSectionName,
    ProviderAdapterKey,
    ProviderCapabilityDiscoveryStatus,
    TaskArtifactChunkRetrievalScopeKind,
    TaskArtifactIngestionStatus,
)
from alicebot_api.store import JsonObject, JsonValue

if _TYPE_CHECKING:
    from alicebot_api.contracts import (
        TaskArtifactChunkRetrievalMatch,
        TaskArtifactChunkRetrievalScope,
    )


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


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


ThreadActivityPosture = Literal["recent", "current", "stale"]
ThreadRiskPosture = Literal["normal", "watch", "risky"]
ThreadHealthPosture = Literal["healthy", "watch", "critical"]


class ThreadHealthThresholdsRecord(TypedDict):
    recent_window_hours: float
    stale_window_hours: float
    risky_score_threshold: int


class ThreadHealthRecord(TypedDict):
    thread: ThreadRecord
    health_posture: ThreadHealthPosture
    activity_posture: ThreadActivityPosture
    risk_posture: ThreadRiskPosture
    risk_score: int
    last_activity_at: str | None
    last_conversation_at: str | None
    hours_since_last_activity: float | None
    conversation_event_count: int
    operational_event_count: int
    active_session_count: int
    open_loop_count: int
    stale_open_loop_count: int
    unresolved_contradiction_count: int
    weak_trust_signal_count: int
    reasons: list[str]
    recommended_action: str


class ThreadHealthDashboardSummary(TypedDict):
    posture: ThreadHealthPosture
    total_thread_count: int
    recent_thread_count: int
    stale_thread_count: int
    risky_thread_count: int
    watch_thread_count: int
    thresholds: ThreadHealthThresholdsRecord
    recent_threads: list[ThreadHealthRecord]
    stale_threads: list[ThreadHealthRecord]
    risky_threads: list[ThreadHealthRecord]
    items: list[ThreadHealthRecord]
    sources: list[str]


class ThreadHealthDashboardResponse(TypedDict):
    dashboard: ThreadHealthDashboardSummary


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
    trust_class: NotRequired[MemoryTrustClass]
    promotion_eligibility: NotRequired[MemoryPromotionEligibility]
    evidence_count: NotRequired[int | None]
    independent_source_count: NotRequired[int | None]
    extracted_by_model: NotRequired[str | None]
    trust_reason: NotRequired[str | None]
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
    trust_class: NotRequired[MemoryTrustClass]
    promotion_eligibility: NotRequired[MemoryPromotionEligibility]


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


class ProviderCapabilityRecord(TypedDict):
    provider_id: str
    adapter_key: ProviderAdapterKey
    discovery_status: ProviderCapabilityDiscoveryStatus
    capability_version: str
    snapshot: JsonObject
    discovery_error: str | None
    discovered_at: str


class ModelProviderRecord(TypedDict):
    id: str
    workspace_id: str
    created_by_user_account_id: str
    provider_key: ProviderAdapterKey
    model_provider: ModelProvider
    display_name: str
    base_url: str
    auth_mode: str
    default_model: str
    status: ModelProviderStatus
    model_list_path: str
    healthcheck_path: str
    invoke_path: str
    azure_api_version: str
    metadata: JsonObject
    created_at: str
    updated_at: str


class ProviderRegistrationResponse(TypedDict):
    provider: ModelProviderRecord
    capabilities: ProviderCapabilityRecord


class ProviderListSummary(TypedDict):
    total_count: int
    order: list[str]


class ProviderListResponse(TypedDict):
    items: list[ModelProviderRecord]
    summary: ProviderListSummary


class ProviderDetailResponse(TypedDict):
    provider: ModelProviderRecord
    capabilities: ProviderCapabilityRecord | None


class ProviderTestResultRecord(TypedDict):
    provider: ModelProvider
    model: str
    response_id: str | None
    finish_reason: ModelFinishReason
    text: str
    usage: ModelUsagePayload


class ProviderTestResponse(TypedDict):
    provider: ModelProviderRecord
    capabilities: ProviderCapabilityRecord | None
    result: ProviderTestResultRecord


class RuntimeInvokeAssistantRecord(TypedDict):
    event_id: str
    sequence_no: int
    provider_id: str
    provider_key: ProviderAdapterKey
    model_provider: ModelProvider
    model: str
    response_id: str | None
    finish_reason: ModelFinishReason
    text: str
    usage: ModelUsagePayload


class RuntimeInvokeResponse(TypedDict):
    assistant: RuntimeInvokeAssistantRecord
    trace: ResponseTraceSummary


__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
