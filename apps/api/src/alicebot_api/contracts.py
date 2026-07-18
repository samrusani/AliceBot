from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import FunctionType as _FunctionType
from typing import Literal, NotRequired, TypeAlias, TypedDict
from uuid import UUID

from alicebot_api.store import JsonObject, JsonValue

from alicebot_api._contracts.common import (
    DecisionKind,
    AdmissionAction,
    MemoryStatus,
    OpenLoopStatus,
    OpenLoopStatusFilter,
    MemoryType,
    MemoryConfirmationStatus,
    MemoryTrustClass,
    MemoryPromotionEligibility,
    ContinuityPreservationStatus,
    ContinuitySearchabilityStatus,
    ContinuityPromotionStatus,
    ContinuityRecallFreshnessPosture,
    ContinuityRecallProvenancePosture,
    ContinuityRecallSupersessionPosture,
    RetrievalEvaluationStatus,
    MemoryReviewStatusFilter,
    MemoryReviewLabelValue,
    MemoryQualityGateStatus,
    MemoryQualityReviewAction,
    MemoryReviewQueuePriorityMode,
    EntityType,
    EmbeddingConfigStatus,
    ConsentStatus,
    ApprovalStatus,
    ApprovalResolutionAction,
    ApprovalResolutionOutcome,
    TaskStatus,
    TaskRunStatus,
    TaskRunStopReason,
    TaskRunFailureClass,
    TaskRunRetryPosture,
    TaskWorkspaceStatus,
    TaskArtifactStatus,
    TaskArtifactIngestionStatus,
    TaskArtifactChunkRetrievalScopeKind,
    TaskArtifactChunkEmbeddingListScopeKind,
    TaskLifecycleSource,
    TaskStepKind,
    TaskStepStatus,
    ProxyExecutionStatus,
    ExecutionBudgetStatus,
    ExecutionBudgetDecision,
    ExecutionBudgetDecisionReason,
    ExecutionBudgetContextResolution,
    ExecutionBudgetCountScope,
    ExecutionBudgetLifecycleAction,
    ExecutionBudgetLifecycleOutcome,
    PolicyEffect,
    PolicyEvaluationReasonCode,
    ToolMetadataVersion,
    ToolAllowlistReasonCode,
    ToolAllowlistDecision,
    ToolRoutingDecision,
    PromptSectionName,
    ModelProvider,
    ProviderAdapterKey,
    ModelProviderStatus,
    ProviderCapabilityDiscoveryStatus,
    ModelFinishReason,
    TaskBriefMode,
    TaskBriefingStrategy,
    ContinuityBriefType,
    ExplicitPreferencePattern,
    ExplicitCommitmentPattern,
    ContinuityObjectType,
    ContinuityCaptureExplicitSignal,
    ContinuityCaptureAdmissionPosture,
    ContinuityCaptureCandidateType,
    ContinuityCaptureCommitMode,
    ContinuityCaptureCommitDecision,
    ContinuityCaptureProposedAction,
    MemoryOperationType,
    MemoryOperationPolicyAction,
    MemoryOperationStatus,
    ContinuityRecallScopeKind,
    ContinuityCorrectionAction,
    ContinuityReviewStatus,
    ContinuityReviewStatusFilter,
    ContradictionKind,
    ContradictionStatus,
    ContradictionResolutionAction,
    TrustSignalType,
    TrustSignalState,
    TrustSignalDirection,
    ContinuityOpenLoopPosture,
    ContinuityOpenLoopReviewAction,
    RecommendationConfidencePosture,
    ExplicitCommitmentOpenLoopDecision,
    MemorySelectionSource,
    ArtifactSelectionSource,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_EVENTS,
    DEFAULT_MAX_MEMORIES,
    DEFAULT_MAX_ENTITIES,
    DEFAULT_MAX_ENTITY_EDGES,
    DEFAULT_MEMORY_REVIEW_LIMIT,
    MAX_MEMORY_REVIEW_LIMIT,
    DEFAULT_OPEN_LOOP_LIMIT,
    MAX_OPEN_LOOP_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_EVENT_LIMIT,
    MAX_RESUMPTION_BRIEF_EVENT_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    MAX_RESUMPTION_BRIEF_OPEN_LOOP_LIMIT,
    DEFAULT_RESUMPTION_BRIEF_MEMORY_LIMIT,
    MAX_RESUMPTION_BRIEF_MEMORY_LIMIT,
    DEFAULT_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    MAX_SEMANTIC_MEMORY_RETRIEVAL_LIMIT,
    DEFAULT_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    MAX_ARTIFACT_CHUNK_RETRIEVAL_LIMIT,
    DEFAULT_CONTINUITY_CAPTURE_LIMIT,
    MAX_CONTINUITY_CAPTURE_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    MAX_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT,
    MAX_CONTINUITY_DAILY_BRIEF_LIMIT,
    DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    DEFAULT_CALENDAR_EVENT_LIST_LIMIT,
    MAX_CALENDAR_EVENT_LIST_LIMIT,
    COMPILER_VERSION_V0,
    PROMPT_ASSEMBLY_VERSION_V0,
    RESPONSE_GENERATION_VERSION_V0,
    PROVIDER_CAPABILITY_VERSION_V1,
    TRACE_KIND_CONTEXT_COMPILE,
    TRACE_KIND_RESPONSE_GENERATE,
    TRACE_REVIEW_LIST_ORDER,
    TRACE_REVIEW_EVENT_LIST_ORDER,
    THREAD_LIST_ORDER,
    AGENT_PROFILE_LIST_ORDER,
    THREAD_SESSION_LIST_ORDER,
    THREAD_EVENT_LIST_ORDER,
    PROVIDER_LIST_ORDER,
    DEFAULT_AGENT_PROFILE_ID,
    RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0,
    CONTINUITY_RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0,
    TASK_BRIEF_ASSEMBLY_VERSION_V0,
    TASK_BRIEF_COMPARISON_VERSION_V0,
    CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0,
    CONTINUITY_DAILY_BRIEF_ASSEMBLY_VERSION_V0,
    CONTINUITY_WEEKLY_REVIEW_ASSEMBLY_VERSION_V0,
    RESUMPTION_BRIEF_CONVERSATION_EVENT_KINDS,
    RESUMPTION_BRIEF_CONVERSATION_ORDER,
    RESUMPTION_BRIEF_MEMORY_ORDER,
    MEMORY_REVIEW_ORDER,
    MEMORY_REVIEW_QUEUE_ORDER,
    DEFAULT_MEMORY_REVIEW_QUEUE_PRIORITY_MODE,
    MEMORY_REVIEW_QUEUE_PRIORITY_MODES,
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    TASK_BRIEF_MODE_ORDER,
    CONTINUITY_BRIEF_TYPE_ORDER,
    TASK_BRIEF_SECTION_ITEM_ORDER,
    TASK_BRIEFING_STRATEGIES,
    MEMORY_REVIEW_QUEUE_ORDER_BY_PRIORITY_MODE,
    MEMORY_QUALITY_PRECISION_TARGET,
    MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE,
    MEMORY_QUALITY_HIGH_RISK_CONFIDENCE_THRESHOLD,
    MEMORY_REVISION_REVIEW_ORDER,
    MEMORY_REVIEW_LABEL_VALUES,
    MEMORY_REVIEW_LABEL_ORDER,
    OPEN_LOOP_REVIEW_ORDER,
    MEMORY_TYPES,
    MEMORY_CONFIRMATION_STATUSES,
    MEMORY_TRUST_CLASSES,
    MEMORY_PROMOTION_ELIGIBILITIES,
    OPEN_LOOP_STATUSES,
    DEFAULT_MEMORY_TYPE,
    DEFAULT_MEMORY_CONFIRMATION_STATUS,
    DEFAULT_MEMORY_TRUST_CLASS,
    DEFAULT_MEMORY_PROMOTION_ELIGIBILITY,
    DEFAULT_CONTINUITY_LIFECYCLE_LIMIT,
    MAX_CONTINUITY_LIFECYCLE_LIMIT,
    DEFAULT_RETRIEVAL_RUN_LIST_LIMIT,
    MAX_RETRIEVAL_RUN_LIST_LIMIT,
    DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT,
    MAX_TRUSTED_FACT_PROMOTION_LIMIT,
    ENTITY_TYPES,
    ENTITY_LIST_ORDER,
    ENTITY_EDGE_LIST_ORDER,
    TEMPORAL_TIMELINE_ORDER,
    TRUSTED_FACT_PATTERN_ORDER,
    TRUSTED_FACT_PLAYBOOK_ORDER,
    EMBEDDING_CONFIG_LIST_ORDER,
    MEMORY_EMBEDDING_LIST_ORDER,
    SEMANTIC_MEMORY_RETRIEVAL_ORDER,
    RETRIEVAL_EVALUATION_FIXTURE_ORDER,
    RETRIEVAL_EVALUATION_RESULT_ORDER,
    RETRIEVAL_RUN_LIST_ORDER,
    RETRIEVAL_TRACE_CANDIDATE_ORDER,
    EMBEDDING_CONFIG_STATUSES,
    CONSENT_STATUSES,
    CONSENT_LIST_ORDER,
    POLICY_EFFECTS,
    POLICY_LIST_ORDER,
    POLICY_EVALUATION_VERSION_V0,
    TRACE_KIND_POLICY_EVALUATE,
    TOOL_METADATA_VERSION_V0,
    TOOL_LIST_ORDER,
    TOOL_ALLOWLIST_EVALUATION_VERSION_V0,
    TRACE_KIND_TOOL_ALLOWLIST_EVALUATE,
    TOOL_ROUTING_VERSION_V0,
    TRACE_KIND_TOOL_ROUTE,
    APPROVAL_LIST_ORDER,
    TASK_LIST_ORDER,
    TASK_WORKSPACE_LIST_ORDER,
    GMAIL_ACCOUNT_LIST_ORDER,
    CALENDAR_ACCOUNT_LIST_ORDER,
    CALENDAR_EVENT_LIST_ORDER,
    TASK_ARTIFACT_LIST_ORDER,
    TASK_ARTIFACT_CHUNK_LIST_ORDER,
    TASK_ARTIFACT_CHUNK_EMBEDDING_LIST_ORDER,
    TASK_ARTIFACT_CHUNK_RETRIEVAL_ORDER,
    TASK_ARTIFACT_CHUNK_SEMANTIC_RETRIEVAL_ORDER,
    TASK_STEP_LIST_ORDER,
    TOOL_EXECUTION_LIST_ORDER,
    EXECUTION_BUDGET_LIST_ORDER,
    EXECUTION_BUDGET_MATCH_ORDER,
    EXECUTION_BUDGET_STATUSES,
    TASK_STATUSES,
    TASK_RUN_STATUSES,
    TASK_RUN_STOP_REASONS,
    TASK_RUN_FAILURE_CLASSES,
    TASK_RUN_RETRY_POSTURES,
    TASK_RUN_LIST_ORDER,
    CONTINUITY_CAPTURE_LIST_ORDER,
    CONTINUITY_OBJECT_LIST_ORDER,
    CONTINUITY_REVIEW_QUEUE_ORDER,
    CONTINUITY_CORRECTION_EVENT_ORDER,
    CONTRADICTION_CASE_LIST_ORDER,
    TRUST_SIGNAL_LIST_ORDER,
    CONTINUITY_RECALL_LIST_ORDER,
    CONTINUITY_LIFECYCLE_LIST_ORDER,
    CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER,
    CONTINUITY_RESUMPTION_OPEN_LOOP_ORDER,
    CONTINUITY_OPEN_LOOP_POSTURE_ORDER,
    CONTINUITY_OPEN_LOOP_ITEM_ORDER,
    TASK_WORKSPACE_STATUSES,
    TASK_ARTIFACT_STATUSES,
    TASK_ARTIFACT_INGESTION_STATUSES,
    TASK_STEP_KINDS,
    TASK_STEP_STATUSES,
    APPROVAL_REQUEST_VERSION_V0,
    TRACE_KIND_APPROVAL_REQUEST,
    APPROVAL_RESOLUTION_VERSION_V0,
    TRACE_KIND_APPROVAL_RESOLUTION,
    TRACE_KIND_APPROVAL_RESOLVE,
    PROXY_EXECUTION_VERSION_V0,
    TRACE_KIND_PROXY_EXECUTE,
    GMAIL_PROVIDER,
    GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN,
    GMAIL_READONLY_SCOPE,
    GMAIL_PROTECTED_CREDENTIAL_KIND,
    GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND,
    CALENDAR_PROVIDER,
    CALENDAR_AUTH_KIND_OAUTH_ACCESS_TOKEN,
    CALENDAR_READONLY_SCOPE,
    CALENDAR_PROTECTED_CREDENTIAL_KIND,
    TASK_STEP_SEQUENCE_VERSION_V0,
    TRACE_KIND_TASK_STEP_SEQUENCE,
    TASK_STEP_CONTINUATION_VERSION_V0,
    TRACE_KIND_TASK_STEP_CONTINUATION,
    TASK_STEP_TRANSITION_VERSION_V0,
    TRACE_KIND_TASK_STEP_TRANSITION,
    EXECUTION_BUDGET_LIFECYCLE_VERSION_V0,
    TRACE_KIND_EXECUTION_BUDGET_LIFECYCLE,
    CONTINUITY_OBJECT_TYPES,
    CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
    CONTINUITY_CAPTURE_CANDIDATE_TYPES,
    CONTINUITY_CAPTURE_COMMIT_MODES,
    CONTINUITY_CAPTURE_ASSIST_AUTOSAVE_TYPES,
    CONTINUITY_CAPTURE_REVIEW_REQUIRED_TYPES,
    MEMORY_OPERATION_TYPES,
    MEMORY_OPERATION_POLICY_ACTIONS,
    MEMORY_OPERATION_STATUSES,
    CONTINUITY_CORRECTION_ACTIONS,
    CONTINUITY_PRESERVATION_STATUSES,
    CONTINUITY_SEARCHABILITY_STATUSES,
    CONTINUITY_PROMOTION_STATUSES,
    CONTINUITY_REVIEW_STATUSES,
    CONTRADICTION_KINDS,
    CONTRADICTION_STATUSES,
    CONTRADICTION_RESOLUTION_ACTIONS,
    TRUST_SIGNAL_TYPES,
    TRUST_SIGNAL_STATES,
    TRUST_SIGNAL_DIRECTIONS,
    CONTINUITY_OPEN_LOOP_POSTURES,
    CONTINUITY_OPEN_LOOP_REVIEW_ACTIONS,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    MAX_TEMPORAL_TIMELINE_LIMIT,
)
from alicebot_api._contracts.common import isoformat_or_none as _common_isoformat_or_none


def _clone_contract_function(
    source: _FunctionType,
    *,
    qualname: str,
) -> _FunctionType:
    rebound = _FunctionType(
        source.__code__.replace(co_qualname=qualname),
        globals(),
        source.__name__,
        source.__defaults__,
        source.__closure__,
    )
    rebound.__kwdefaults__ = source.__kwdefaults__
    rebound.__dict__.update(source.__dict__)
    rebound.__doc__ = source.__doc__
    rebound.__module__ = __name__
    rebound.__qualname__ = qualname

    type_params = getattr(source, "__type_params__", None)
    if type_params is not None:
        setattr(rebound, "__type_params__", type_params)

    source_annotate = getattr(source, "__annotate__", None)
    if isinstance(source_annotate, _FunctionType):
        rebound_annotate = _FunctionType(
            source_annotate.__code__.replace(
                co_qualname=source_annotate.__code__.co_qualname,
            ),
            globals(),
            source_annotate.__name__,
            source_annotate.__defaults__,
            source_annotate.__closure__,
        )
        rebound_annotate.__kwdefaults__ = source_annotate.__kwdefaults__
        rebound_annotate.__dict__.update(source_annotate.__dict__)
        rebound_annotate.__doc__ = source_annotate.__doc__
        rebound_annotate.__module__ = __name__
        rebound_annotate.__qualname__ = source_annotate.__qualname__
        setattr(rebound, "__annotate__", rebound_annotate)
    else:
        rebound.__annotations__ = source.__annotations__
    return rebound


def _clone_generated_contract_function(source: _FunctionType) -> _FunctionType:
    rebound = _FunctionType(
        source.__code__,
        globals(),
        source.__name__,
        source.__defaults__,
        source.__closure__,
    )
    rebound.__kwdefaults__ = source.__kwdefaults__
    rebound.__dict__.update(source.__dict__)
    rebound.__doc__ = source.__doc__
    rebound.__module__ = source.__module__
    rebound.__qualname__ = source.__qualname__

    type_params = getattr(source, "__type_params__", None)
    if type_params is not None:
        setattr(rebound, "__type_params__", type_params)

    source_annotate = getattr(source, "__annotate__", None)
    if isinstance(source_annotate, _FunctionType):
        setattr(rebound, "__annotate__", source_annotate)
    else:
        rebound.__annotations__ = source.__annotations__
    return rebound


from alicebot_api._contracts.runtime import (
    ContextCompilerLimits,
    CompileContextSemanticRetrievalInput,
    CompileContextTaskScopedArtifactRetrievalInput,
    CompileContextArtifactScopedArtifactRetrievalInput,
    CompileContextArtifactRetrievalInput,
    CompileContextTaskScopedSemanticArtifactRetrievalInput,
    CompileContextArtifactScopedSemanticArtifactRetrievalInput,
    CompileContextSemanticArtifactRetrievalInput,
    TraceCreate,
    TraceEventRecord,
    AgentProfileRecord,
    AgentProfileListSummary,
    AgentProfileListResponse,
    ThreadCreateInput,
    ThreadRecord,
    ThreadCreateResponse,
    ThreadListSummary,
    ThreadListResponse,
    ThreadActivityPosture,
    ThreadRiskPosture,
    ThreadHealthPosture,
    ThreadHealthThresholdsRecord,
    ThreadHealthRecord,
    ThreadHealthDashboardSummary,
    ThreadHealthDashboardResponse,
    ThreadDetailResponse,
    ThreadSessionRecord,
    ThreadSessionListSummary,
    ThreadSessionListResponse,
    ThreadEventRecord,
    ThreadEventListSummary,
    ThreadEventListResponse,
    ResumptionBriefRequestInput,
    TraceReviewSummaryRecord,
    TraceReviewRecord,
    TraceReviewListSummary,
    TraceReviewListResponse,
    TraceReviewDetailResponse,
    TraceReviewEventRecord,
    TraceReviewEventListSummary,
    TraceReviewEventListResponse,
    CompilerDecision,
    ContextPackScope,
    ContextPackLimits,
    ContextPackUser,
    ContextPackThread,
    ContextPackSession,
    ContextPackEvent,
    ContextPackMemory,
    ContextPackMemorySourceProvenance,
    ContextPackHybridMemorySummary,
    ContextPackArtifactChunk,
    ContextPackArtifactChunkSourceProvenance,
    ContextPackArtifactChunkSummary,
    ArtifactRetrievalDecisionTracePayload,
    HybridArtifactRetrievalDecisionTracePayload,
    ContextPackMemorySummary,
    ContextPackOpenLoop,
    ContextPackOpenLoopSummary,
    HybridMemoryDecisionTracePayload,
    ContextPackEntity,
    ContextPackEntitySummary,
    EntityDecisionTracePayload,
    ContextPackEntityEdge,
    ContextPackEntityEdgeSummary,
    EntityEdgeDecisionTracePayload,
    CompiledContextPack,
    CompilerRunResult,
    PromptAssemblyInput,
    PromptSection,
    PromptAssemblyTracePayload,
    PromptAssemblyResult,
    ModelInvocationRequestPayload,
    ModelInvocationRequest,
    ModelUsagePayload,
    ModelInvocationTracePayload,
    ModelInvocationResponse,
    AssistantResponseModelRecord,
    AssistantResponsePromptRecord,
    AssistantResponseEventPayload,
    GeneratedAssistantRecord,
    ResponseTraceSummary,
    GenerateResponseSuccess,
    ProviderCapabilityRecord,
    ModelProviderRecord,
    ProviderRegistrationResponse,
    ProviderListSummary,
    ProviderListResponse,
    ProviderDetailResponse,
    ProviderTestResultRecord,
    ProviderTestResponse,
    RuntimeInvokeAssistantRecord,
    RuntimeInvokeResponse,
)

_RUNTIME_CONTRACT_CLASS_NAMES = (
    "ContextCompilerLimits",
    "CompileContextSemanticRetrievalInput",
    "CompileContextTaskScopedArtifactRetrievalInput",
    "CompileContextArtifactScopedArtifactRetrievalInput",
    "CompileContextTaskScopedSemanticArtifactRetrievalInput",
    "CompileContextArtifactScopedSemanticArtifactRetrievalInput",
    "TraceCreate",
    "TraceEventRecord",
    "AgentProfileRecord",
    "AgentProfileListSummary",
    "AgentProfileListResponse",
    "ThreadCreateInput",
    "ThreadRecord",
    "ThreadCreateResponse",
    "ThreadListSummary",
    "ThreadListResponse",
    "ThreadHealthThresholdsRecord",
    "ThreadHealthRecord",
    "ThreadHealthDashboardSummary",
    "ThreadHealthDashboardResponse",
    "ThreadDetailResponse",
    "ThreadSessionRecord",
    "ThreadSessionListSummary",
    "ThreadSessionListResponse",
    "ThreadEventRecord",
    "ThreadEventListSummary",
    "ThreadEventListResponse",
    "ResumptionBriefRequestInput",
    "TraceReviewSummaryRecord",
    "TraceReviewRecord",
    "TraceReviewListSummary",
    "TraceReviewListResponse",
    "TraceReviewDetailResponse",
    "TraceReviewEventRecord",
    "TraceReviewEventListSummary",
    "TraceReviewEventListResponse",
    "CompilerDecision",
    "ContextPackScope",
    "ContextPackLimits",
    "ContextPackUser",
    "ContextPackThread",
    "ContextPackSession",
    "ContextPackEvent",
    "ContextPackMemory",
    "ContextPackMemorySourceProvenance",
    "ContextPackHybridMemorySummary",
    "ContextPackArtifactChunk",
    "ContextPackArtifactChunkSourceProvenance",
    "ContextPackArtifactChunkSummary",
    "ArtifactRetrievalDecisionTracePayload",
    "HybridArtifactRetrievalDecisionTracePayload",
    "ContextPackMemorySummary",
    "ContextPackOpenLoop",
    "ContextPackOpenLoopSummary",
    "HybridMemoryDecisionTracePayload",
    "ContextPackEntity",
    "ContextPackEntitySummary",
    "EntityDecisionTracePayload",
    "ContextPackEntityEdge",
    "ContextPackEntityEdgeSummary",
    "EntityEdgeDecisionTracePayload",
    "CompiledContextPack",
    "CompilerRunResult",
    "PromptAssemblyInput",
    "PromptSection",
    "PromptAssemblyTracePayload",
    "PromptAssemblyResult",
    "ModelInvocationRequestPayload",
    "ModelInvocationRequest",
    "ModelUsagePayload",
    "ModelInvocationTracePayload",
    "ModelInvocationResponse",
    "AssistantResponseModelRecord",
    "AssistantResponsePromptRecord",
    "AssistantResponseEventPayload",
    "GeneratedAssistantRecord",
    "ResponseTraceSummary",
    "GenerateResponseSuccess",
    "ProviderCapabilityRecord",
    "ModelProviderRecord",
    "ProviderRegistrationResponse",
    "ProviderListSummary",
    "ProviderListResponse",
    "ProviderDetailResponse",
    "ProviderTestResultRecord",
    "ProviderTestResponse",
    "RuntimeInvokeAssistantRecord",
    "RuntimeInvokeResponse",
)
_RUNTIME_EXPLICIT_METHODS = (
    ("ContextCompilerLimits", "as_payload"),
    ("CompileContextSemanticRetrievalInput", "as_payload"),
    ("CompileContextTaskScopedArtifactRetrievalInput", "as_payload"),
    ("CompileContextArtifactScopedArtifactRetrievalInput", "as_payload"),
    ("CompileContextTaskScopedSemanticArtifactRetrievalInput", "as_payload"),
    ("CompileContextArtifactScopedSemanticArtifactRetrievalInput", "as_payload"),
    ("CompilerDecision", "to_trace_event"),
    ("ModelInvocationRequest", "as_payload"),
    ("ModelInvocationResponse", "to_trace_payload"),
)

for _runtime_class_name, _runtime_method_name in _RUNTIME_EXPLICIT_METHODS:
    _runtime_class = globals()[_runtime_class_name]
    _runtime_method = getattr(_runtime_class, _runtime_method_name)
    setattr(
        _runtime_class,
        _runtime_method_name,
        _clone_contract_function(
            _runtime_method,
            qualname=_runtime_method.__qualname__,
        ),
    )

for _runtime_class_name in _RUNTIME_CONTRACT_CLASS_NAMES:
    _runtime_class = globals()[_runtime_class_name]
    if not hasattr(_runtime_class, "__dataclass_fields__"):
        continue
    for _runtime_generated_name, _runtime_generated_method in vars(_runtime_class).items():
        if (
            isinstance(_runtime_generated_method, _FunctionType)
            and _runtime_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.runtime"
        ):
            setattr(
                _runtime_class,
                _runtime_generated_name,
                _clone_generated_contract_function(_runtime_generated_method),
            )

del _runtime_class
del _runtime_class_name
del _runtime_generated_method
del _runtime_generated_name
del _runtime_method
del _runtime_method_name


import alicebot_api._contracts.continuity as _continuity_contracts
from alicebot_api._contracts.continuity import (
    OpenLoopCandidateInput,
    MemoryCandidateInput,
    ExplicitPreferenceExtractionRequestInput,
    ExplicitCommitmentExtractionRequestInput,
    ExplicitSignalCaptureRequestInput,
    ContinuityCaptureCreateInput,
    ContinuityCaptureCandidatesInput,
    ContinuityCaptureCommitInput,
    MemoryOperationGenerateInput,
    MemoryOperationCommitInput,
    MemoryOperationListInput,
    ContinuityReviewQueueQueryInput,
    ContinuityCorrectionInput,
    ContradictionCaseListQueryInput,
    ContradictionSyncInput,
    ContradictionResolveInput,
    TrustSignalListQueryInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    ContinuityBriefRequestInput,
    TaskBriefCompileRequestInput,
    TaskBriefComparisonRequestInput,
    ContinuityLifecycleQueryInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityDailyBriefRequestInput,
    ContinuityWeeklyReviewRequestInput,
    ContinuityOpenLoopReviewActionInput,
    OpenLoopCreateInput,
    OpenLoopStatusUpdateInput,
    ExtractedPreferenceCandidateRecord,
    ExtractedCommitmentCandidateRecord,
)

_CONTINUITY_CONTRACT_CLASS_NAMES = (
    "OpenLoopCandidateInput",
    "MemoryCandidateInput",
    "ExplicitPreferenceExtractionRequestInput",
    "ExplicitCommitmentExtractionRequestInput",
    "ExplicitSignalCaptureRequestInput",
    "ContinuityCaptureCreateInput",
    "ContinuityCaptureCandidatesInput",
    "ContinuityCaptureCommitInput",
    "MemoryOperationGenerateInput",
    "MemoryOperationCommitInput",
    "MemoryOperationListInput",
    "ContinuityReviewQueueQueryInput",
    "ContinuityCorrectionInput",
    "ContradictionCaseListQueryInput",
    "ContradictionSyncInput",
    "ContradictionResolveInput",
    "TrustSignalListQueryInput",
    "ContinuityRecallQueryInput",
    "ContinuityResumptionBriefRequestInput",
    "ContinuityBriefRequestInput",
    "TaskBriefCompileRequestInput",
    "TaskBriefComparisonRequestInput",
    "ContinuityLifecycleQueryInput",
    "ContinuityOpenLoopDashboardQueryInput",
    "ContinuityDailyBriefRequestInput",
    "ContinuityWeeklyReviewRequestInput",
    "ContinuityOpenLoopReviewActionInput",
    "OpenLoopCreateInput",
    "OpenLoopStatusUpdateInput",
    "ExtractedPreferenceCandidateRecord",
    "ExtractedCommitmentCandidateRecord",
    "PersistedMemoryRecord",
    "PersistedMemoryRevisionRecord",
    "AdmissionDecisionOutput",
    "ExplicitPreferenceAdmissionRecord",
    "ExplicitPreferenceExtractionSummary",
    "ExplicitPreferenceExtractionResponse",
    "ExplicitCommitmentOpenLoopOutcome",
    "ExplicitCommitmentAdmissionRecord",
    "ExplicitCommitmentExtractionSummary",
    "ExplicitCommitmentExtractionResponse",
    "ExplicitSignalCaptureSummary",
    "ExplicitSignalCaptureResponse",
    "ContinuityCaptureEventRecord",
    "ContinuityCaptureCandidateRecord",
    "ContinuityCaptureCandidatesSummary",
    "ContinuityCaptureCandidatesResponse",
    "ContinuityCaptureCommitRecord",
    "ContinuityCaptureCommitSummary",
    "ContinuityCaptureCommitResponse",
    "MemoryOperationCandidateRecord",
    "MemoryOperationRecord",
    "MemoryOperationCandidateGenerateSummary",
    "MemoryOperationCandidateGenerateResponse",
    "MemoryOperationCommitSummary",
    "MemoryOperationCommitResponse",
    "MemoryOperationListSummary",
    "MemoryOperationCandidateListResponse",
    "MemoryOperationListResponse",
    "ContinuityLifecycleStateRecord",
    "ContinuityObjectRecord",
    "ContinuityReviewObjectRecord",
    "ContinuityCorrectionEventRecord",
    "ContinuityCaptureInboxItem",
    "ContinuityCaptureInboxSummary",
    "ContinuityCaptureCreateResponse",
    "ContinuityCaptureInboxResponse",
    "ContinuityCaptureDetailResponse",
    "ContinuityReviewQueueSummary",
    "ContinuityReviewQueueResponse",
    "ContinuitySupersessionChain",
    "ContinuityReviewDetail",
    "ContinuityReviewDetailResponse",
    "ContradictionCaseRecord",
    "ContradictionCaseListSummary",
    "ContradictionCaseListResponse",
    "ContradictionCaseDetailResponse",
    "ContradictionSyncSummary",
    "ContradictionSyncResponse",
    "ContradictionResolveResponse",
    "TrustSignalRecord",
    "TrustSignalListSummary",
    "TrustSignalListResponse",
    "ContinuityEvidenceArtifactRecord",
    "ContinuityEvidenceArtifactCopyRecord",
    "ContinuityEvidenceArtifactSegmentRecord",
    "ContinuityEvidenceLinkRecord",
    "ContinuityExplanationSourceFactRecord",
    "ContinuityExplanationEvidenceSegmentRecord",
    "ContinuityExplanationSupersessionNoteRecord",
    "ContinuityExplanationContradictionRecord",
    "ContinuityExplanationTrustRecord",
    "ContinuityExplanationTimestampsRecord",
    "ContinuityExplanationRecord",
    "ContinuityExplainRecord",
    "ContinuityExplainResponse",
    "ContinuityArtifactDetailRecord",
    "ContinuityArtifactDetailResponse",
    "ContinuityRecallScopeFilters",
    "ContinuityRecallScopeMatch",
    "ContinuityRecallProvenanceReference",
    "ContinuityRecallOrderingMetadata",
    "ContinuityRetrievalStageScoreRecord",
    "ContinuityRetrievalDebugCandidateRecord",
    "ContinuityRetrievalDebugRecord",
    "ContinuityRecallResultRecord",
    "ContinuityRecallSummary",
    "ContinuityRecallResponse",
    "ContinuityLifecycleCounts",
    "ContinuityLifecycleListSummary",
    "ContinuityLifecycleListResponse",
    "ContinuityLifecycleDetailResponse",
    "ContinuityResumptionEmptyState",
    "ContinuityResumptionSingleSection",
    "ContinuityResumptionListSection",
    "ContinuityResumptionBriefRecord",
    "ContinuityResumptionDebugRecord",
    "ContinuityResumptionBriefResponse",
    "ContinuityBriefRelevantFactsSummary",
    "ContinuityBriefRelevantFactsSection",
    "ContinuityBriefConflictSummary",
    "ContinuityBriefConflictSection",
    "ContinuityBriefTimelineHighlightRecord",
    "ContinuityBriefTimelineSection",
    "ContinuityBriefSuggestedActionRecord",
    "ContinuityBriefSelectionStrategyRecord",
    "ContinuityBriefProvenanceSummary",
    "ContinuityBriefProvenanceBundle",
    "ContinuityBriefTrustPostureRecord",
    "ContinuityBriefRecord",
    "ContinuityBriefResponse",
    "TaskBriefEmptyState",
    "TaskBriefSectionSummary",
    "TaskBriefSectionRecord",
    "TaskBriefStrategyRecord",
    "TaskBriefSummary",
    "TaskBriefRecord",
    "TaskBriefPersistenceRecord",
    "TaskBriefResponse",
    "TaskBriefComparisonStats",
    "TaskBriefComparisonResponse",
    "ContinuityOpenLoopSectionSummary",
    "ContinuityOpenLoopSection",
    "ContinuityOpenLoopDashboardSummary",
    "ContinuityOpenLoopDashboardRecord",
    "ContinuityOpenLoopDashboardResponse",
    "ContinuityDailyBriefRecord",
    "ContinuityDailyBriefResponse",
    "ContinuityWeeklyReviewRollup",
    "ContinuityWeeklyReviewRecord",
    "ContinuityWeeklyReviewResponse",
    "ContinuityOpenLoopReviewActionResponse",
    "ContinuityCorrectionApplyResponse",
    "MemoryReviewRecord",
    "MemoryReviewListSummary",
    "MemoryReviewListResponse",
    "MemoryReviewDetailResponse",
    "OpenLoopRecord",
    "OpenLoopListSummary",
    "OpenLoopListResponse",
    "OpenLoopDetailResponse",
    "OpenLoopCreateResponse",
    "OpenLoopStatusUpdateResponse",
    "MemoryRevisionReviewRecord",
    "MemoryRevisionReviewListSummary",
    "MemoryRevisionReviewListResponse",
    "MemoryReviewLabelCounts",
    "MemoryReviewLabelRecord",
    "MemoryReviewLabelSummary",
    "MemoryReviewLabelCreateResponse",
    "MemoryReviewLabelListResponse",
    "MemoryReviewQueueItem",
    "MemoryReviewQueueSummary",
    "MemoryReviewQueueResponse",
    "MemoryQualityGateComputationCounts",
    "MemoryQualityGateSummary",
    "MemoryQualityGateResponse",
    "MemoryTrustQueueAgingSummary",
    "MemoryTrustQueuePostureSummary",
    "MemoryTrustCorrectionFreshnessSummary",
    "MemoryTrustRecommendedReview",
    "MemoryDuplicateGroupRecord",
    "MemoryReviewQueuePressureSummary",
    "MemoryHygieneFocusRecord",
    "MemoryHygieneDashboardSummary",
    "MemoryHygieneDashboardResponse",
    "MemoryTrustDashboardSummary",
    "MemoryTrustDashboardResponse",
    "MemoryEvaluationSummary",
    "MemoryEvaluationSummaryResponse",
)
_CONTINUITY_EXPLICIT_METHODS = (
    ("OpenLoopCandidateInput", "as_payload"),
    ("MemoryCandidateInput", "as_payload"),
    ("ExplicitPreferenceExtractionRequestInput", "as_payload"),
    ("ExplicitCommitmentExtractionRequestInput", "as_payload"),
    ("ExplicitSignalCaptureRequestInput", "as_payload"),
    ("ContinuityCaptureCreateInput", "as_payload"),
    ("ContinuityCaptureCandidatesInput", "as_payload"),
    ("ContinuityCaptureCommitInput", "as_payload"),
    ("MemoryOperationGenerateInput", "as_payload"),
    ("MemoryOperationCommitInput", "as_payload"),
    ("MemoryOperationListInput", "as_payload"),
    ("ContinuityReviewQueueQueryInput", "as_payload"),
    ("ContinuityCorrectionInput", "as_payload"),
    ("ContradictionCaseListQueryInput", "as_payload"),
    ("ContradictionSyncInput", "as_payload"),
    ("ContradictionResolveInput", "as_payload"),
    ("TrustSignalListQueryInput", "as_payload"),
    ("ContinuityRecallQueryInput", "as_payload"),
    ("ContinuityResumptionBriefRequestInput", "as_payload"),
    ("ContinuityBriefRequestInput", "as_payload"),
    ("TaskBriefCompileRequestInput", "as_payload"),
    ("TaskBriefComparisonRequestInput", "as_payload"),
    ("ContinuityLifecycleQueryInput", "as_payload"),
    ("ContinuityOpenLoopDashboardQueryInput", "as_payload"),
    ("ContinuityDailyBriefRequestInput", "as_payload"),
    ("ContinuityWeeklyReviewRequestInput", "as_payload"),
    ("ContinuityOpenLoopReviewActionInput", "as_payload"),
    ("OpenLoopCreateInput", "as_payload"),
    ("OpenLoopStatusUpdateInput", "as_payload"),
)

for _continuity_class_name, _continuity_method_name in _CONTINUITY_EXPLICIT_METHODS:
    _continuity_class = getattr(_continuity_contracts, _continuity_class_name)
    _continuity_method = getattr(_continuity_class, _continuity_method_name)
    setattr(
        _continuity_class,
        _continuity_method_name,
        _clone_contract_function(
            _continuity_method,
            qualname=_continuity_method.__qualname__,
        ),
    )

for _continuity_class_name in _CONTINUITY_CONTRACT_CLASS_NAMES:
    _continuity_class = getattr(_continuity_contracts, _continuity_class_name)
    if not hasattr(_continuity_class, "__dataclass_fields__"):
        continue
    for _continuity_generated_name, _continuity_generated_method in vars(
        _continuity_class
    ).items():
        if (
            isinstance(_continuity_generated_method, _FunctionType)
            and _continuity_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.continuity"
        ):
            setattr(
                _continuity_class,
                _continuity_generated_name,
                _clone_generated_contract_function(_continuity_generated_method),
            )

del _continuity_class
del _continuity_class_name
del _continuity_generated_method
del _continuity_generated_name
del _continuity_method
del _continuity_method_name


import alicebot_api._contracts.knowledge as _knowledge_contracts
from alicebot_api._contracts.knowledge import (
    EntityCreateInput,
    EntityEdgeCreateInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
    TemporalExplainQueryInput,
    TrustedFactPatternListQueryInput,
    TrustedFactPlaybookListQueryInput,
)

_KNOWLEDGE_CONTRACT_CLASS_NAMES = (
    "EntityCreateInput",
    "EntityEdgeCreateInput",
    "TemporalStateAtQueryInput",
    "TemporalTimelineQueryInput",
    "TemporalExplainQueryInput",
    "TrustedFactPatternListQueryInput",
    "TrustedFactPlaybookListQueryInput",
    "EntityRecord",
    "EntityCreateResponse",
    "EntityListSummary",
    "EntityListResponse",
    "EntityDetailResponse",
    "EntityEdgeRecord",
    "EntityEdgeCreateResponse",
    "EntityEdgeListSummary",
    "EntityEdgeListResponse",
    "TemporalValidityRecord",
    "TemporalStateFactRecord",
    "TemporalStateEdgeRecord",
    "TemporalStateSummary",
    "TemporalStateAtRecord",
    "TemporalStateAtResponse",
    "TemporalTimelineEventRecord",
    "TemporalTimelineSummary",
    "TemporalTimelineRecord",
    "TemporalTimelineResponse",
    "TemporalTrustRecord",
    "TemporalProvenanceRecord",
    "TemporalFactSupersessionRecord",
    "TemporalFactExplainRecord",
    "TemporalEdgeSupersessionRecord",
    "TemporalEdgeExplainRecord",
    "TemporalExplainSummary",
    "TemporalExplainRecord",
    "TemporalExplainResponse",
    "TrustedFactEvidenceLinkRecord",
    "TrustedFactPatternRecord",
    "TrustedFactPatternListSummary",
    "TrustedFactPatternListResponse",
    "TrustedFactPatternExplainResponse",
    "TrustedFactPlaybookStepRecord",
    "TrustedFactPlaybookRecord",
    "TrustedFactPlaybookListSummary",
    "TrustedFactPlaybookListResponse",
    "TrustedFactPlaybookExplainResponse",
)
_KNOWLEDGE_EXPLICIT_METHODS = (
    ("EntityCreateInput", "as_payload"),
    ("EntityEdgeCreateInput", "as_payload"),
    ("TemporalStateAtQueryInput", "as_payload"),
    ("TemporalTimelineQueryInput", "as_payload"),
    ("TemporalExplainQueryInput", "as_payload"),
    ("TrustedFactPatternListQueryInput", "as_payload"),
    ("TrustedFactPlaybookListQueryInput", "as_payload"),
)

for _knowledge_class_name, _knowledge_method_name in _KNOWLEDGE_EXPLICIT_METHODS:
    _knowledge_class = getattr(_knowledge_contracts, _knowledge_class_name)
    _knowledge_method = getattr(_knowledge_class, _knowledge_method_name)
    setattr(
        _knowledge_class,
        _knowledge_method_name,
        _clone_contract_function(
            _knowledge_method,
            qualname=_knowledge_method.__qualname__,
        ),
    )

for _knowledge_class_name in _KNOWLEDGE_CONTRACT_CLASS_NAMES:
    _knowledge_class = getattr(_knowledge_contracts, _knowledge_class_name)
    if not hasattr(_knowledge_class, "__dataclass_fields__"):
        continue
    for _knowledge_generated_name, _knowledge_generated_method in vars(
        _knowledge_class
    ).items():
        if (
            isinstance(_knowledge_generated_method, _FunctionType)
            and _knowledge_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.knowledge"
        ):
            setattr(
                _knowledge_class,
                _knowledge_generated_name,
                _clone_generated_contract_function(_knowledge_generated_method),
            )

del _knowledge_class
del _knowledge_class_name
del _knowledge_generated_method
del _knowledge_generated_name
del _knowledge_method
del _knowledge_method_name


import alicebot_api._contracts.retrieval as _retrieval_contracts
from alicebot_api._contracts.retrieval import (
    EmbeddingConfigCreateInput,
    MemoryEmbeddingUpsertInput,
)

_RETRIEVAL_CONTRACT_CLASS_NAMES = (
    "EmbeddingConfigCreateInput",
    "MemoryEmbeddingUpsertInput",
    "SemanticMemoryRetrievalRequestInput",
    "RetrievalRunRecord",
    "RetrievalRunListSummary",
    "RetrievalRunListResponse",
    "RetrievalTraceSummary",
    "RetrievalTraceResponse",
    "EmbeddingConfigRecord",
    "EmbeddingConfigCreateResponse",
    "EmbeddingConfigListSummary",
    "EmbeddingConfigListResponse",
    "MemoryEmbeddingRecord",
    "MemoryEmbeddingUpsertResponse",
    "MemoryEmbeddingDetailResponse",
    "MemoryEmbeddingListSummary",
    "MemoryEmbeddingListResponse",
    "SemanticMemoryRetrievalResultItem",
    "SemanticMemoryRetrievalSummary",
    "SemanticMemoryRetrievalResponse",
    "RetrievalEvaluationFixtureResult",
    "RetrievalEvaluationSummary",
    "RetrievalEvaluationResponse",
    "PublicEvalSuiteDefinitionRecord",
    "PublicEvalSuiteDefinitionListResponse",
    "PublicEvalRunRecord",
    "PublicEvalResultRecord",
    "PublicEvalRunListResponse",
    "PublicEvalRunDetailResponse",
)
_RETRIEVAL_EXPLICIT_METHODS = (
    ("EmbeddingConfigCreateInput", "as_payload"),
    ("MemoryEmbeddingUpsertInput", "as_payload"),
    ("SemanticMemoryRetrievalRequestInput", "as_payload"),
)

for _retrieval_class_name, _retrieval_method_name in _RETRIEVAL_EXPLICIT_METHODS:
    _retrieval_class = getattr(_retrieval_contracts, _retrieval_class_name)
    _retrieval_method = getattr(_retrieval_class, _retrieval_method_name)
    setattr(
        _retrieval_class,
        _retrieval_method_name,
        _clone_contract_function(
            _retrieval_method,
            qualname=_retrieval_method.__qualname__,
        ),
    )

for _retrieval_class_name in _RETRIEVAL_CONTRACT_CLASS_NAMES:
    _retrieval_class = getattr(_retrieval_contracts, _retrieval_class_name)
    if not hasattr(_retrieval_class, "__dataclass_fields__"):
        continue
    for _retrieval_generated_name, _retrieval_generated_method in vars(
        _retrieval_class
    ).items():
        if (
            isinstance(_retrieval_generated_method, _FunctionType)
            and _retrieval_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.retrieval"
        ):
            setattr(
                _retrieval_class,
                _retrieval_generated_name,
                _clone_generated_contract_function(_retrieval_generated_method),
            )

del _retrieval_class
del _retrieval_class_name
del _retrieval_generated_method
del _retrieval_generated_name
del _retrieval_method
del _retrieval_method_name


import alicebot_api._contracts.tasks as _task_contracts
from alicebot_api._contracts.tasks import TaskArtifactChunkEmbeddingUpsertInput

_TASK_CONTRACT_CLASS_NAMES = (
    "TaskArtifactChunkEmbeddingUpsertInput",
    "TaskCreateInput",
    "TaskRecord",
    "TaskCreateResponse",
    "TaskStepCreateInput",
    "TaskStepNextCreateInput",
    "TaskStepTransitionInput",
    "TaskStepLineageInput",
    "TaskListSummary",
    "TaskListResponse",
    "TaskDetailResponse",
    "TaskRunCreateInput",
    "TaskRunTickInput",
    "TaskRunPauseInput",
    "TaskRunResumeInput",
    "TaskRunCancelInput",
    "TaskRunRecord",
    "TaskRunCreateResponse",
    "TaskRunListSummary",
    "TaskRunListResponse",
    "TaskRunDetailResponse",
    "TaskRunMutationResponse",
    "TaskWorkspaceCreateInput",
    "TaskWorkspaceRecord",
    "TaskWorkspaceCreateResponse",
    "TaskWorkspaceListSummary",
    "TaskWorkspaceListResponse",
    "TaskWorkspaceDetailResponse",
    "TaskArtifactRegisterInput",
    "TaskArtifactIngestInput",
    "TaskScopedArtifactChunkRetrievalInput",
    "ArtifactScopedArtifactChunkRetrievalInput",
    "TaskScopedSemanticArtifactChunkRetrievalInput",
    "ArtifactScopedSemanticArtifactChunkRetrievalInput",
    "TaskArtifactRecord",
    "TaskArtifactCreateResponse",
    "TaskArtifactListSummary",
    "TaskArtifactListResponse",
    "TaskArtifactDetailResponse",
    "TaskArtifactChunkRecord",
    "TaskArtifactChunkListSummary",
    "TaskArtifactChunkListResponse",
    "TaskArtifactChunkEmbeddingRecord",
    "TaskArtifactChunkEmbeddingWriteResponse",
    "TaskArtifactChunkEmbeddingDetailResponse",
    "TaskArtifactChunkEmbeddingListScope",
    "TaskArtifactChunkEmbeddingListSummary",
    "TaskArtifactChunkEmbeddingListResponse",
    "TaskArtifactIngestionResponse",
    "TaskArtifactChunkRetrievalMatch",
    "TaskArtifactChunkRetrievalItem",
    "TaskArtifactChunkRetrievalScope",
    "TaskArtifactChunkRetrievalSummary",
    "TaskArtifactChunkRetrievalResponse",
    "TaskArtifactChunkSemanticRetrievalItem",
    "TaskArtifactChunkSemanticRetrievalSummary",
    "TaskArtifactChunkSemanticRetrievalResponse",
    "TaskStepTraceLink",
    "TaskStepOutcomeSnapshot",
    "TaskStepLineageRecord",
    "TaskStepRecord",
    "TaskStepCreateResponse",
    "TaskStepSequencingSummary",
    "TaskStepListSummary",
    "TaskStepListResponse",
    "TaskStepDetailResponse",
    "TaskStepMutationTraceSummary",
    "TaskStepNextCreateResponse",
    "TaskStepTransitionResponse",
    "ResumptionBriefSectionSummary",
    "ResumptionBriefConversationSummary",
    "ResumptionBriefConversationSection",
    "ResumptionBriefOpenLoopSection",
    "ResumptionBriefMemoryHighlightSection",
    "ResumptionBriefWorkflowSummary",
    "ResumptionBriefWorkflowPosture",
    "ResumptionBriefRecord",
    "ResumptionBriefResponse",
    "TaskLifecycleStateTracePayload",
    "TaskLifecycleSummaryTracePayload",
    "TaskStepLifecycleStateTracePayload",
    "TaskStepLifecycleSummaryTracePayload",
    "TaskStepSequenceRequestTracePayload",
    "TaskStepSequenceStateTracePayload",
    "TaskStepSequenceSummaryTracePayload",
    "TaskStepContinuationRequestTracePayload",
    "TaskStepContinuationLineageTracePayload",
    "TaskStepContinuationSummaryTracePayload",
    "TaskStepTransitionRequestTracePayload",
    "TaskStepTransitionStateTracePayload",
    "TaskStepTransitionSummaryTracePayload",
)
_TASK_EXPLICIT_METHODS = (
    ("TaskArtifactChunkEmbeddingUpsertInput", "as_payload"),
    ("TaskScopedSemanticArtifactChunkRetrievalInput", "as_payload"),
    ("ArtifactScopedSemanticArtifactChunkRetrievalInput", "as_payload"),
)

for _task_class_name, _task_method_name in _TASK_EXPLICIT_METHODS:
    _task_class = getattr(_task_contracts, _task_class_name)
    _task_method = getattr(_task_class, _task_method_name)
    setattr(
        _task_class,
        _task_method_name,
        _clone_contract_function(
            _task_method,
            qualname=_task_method.__qualname__,
        ),
    )

for _task_class_name in _TASK_CONTRACT_CLASS_NAMES:
    _task_class = getattr(_task_contracts, _task_class_name)
    if not hasattr(_task_class, "__dataclass_fields__"):
        continue
    for _task_generated_name, _task_generated_method in vars(_task_class).items():
        if (
            isinstance(_task_generated_method, _FunctionType)
            and _task_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.tasks"
        ):
            setattr(
                _task_class,
                _task_generated_name,
                _clone_generated_contract_function(_task_generated_method),
            )

del _task_class
del _task_class_name
del _task_generated_method
del _task_generated_name
del _task_method
del _task_method_name


from alicebot_api._contracts.retrieval import SemanticMemoryRetrievalRequestInput


import alicebot_api._contracts.governance as _governance_contracts
from alicebot_api._contracts.governance import (
    ConsentUpsertInput,
    PolicyCreateInput,
    PolicyEvaluationRequestInput,
    ToolCreateInput,
    ToolAllowlistEvaluationRequestInput,
    ToolRoutingRequestInput,
    ApprovalRequestCreateInput,
    ApprovalApproveInput,
    ApprovalRejectInput,
)

_GOVERNANCE_CONTRACT_CLASS_NAMES = (
    "ConsentUpsertInput",
    "PolicyCreateInput",
    "PolicyEvaluationRequestInput",
    "ToolCreateInput",
    "ToolAllowlistEvaluationRequestInput",
    "ToolRoutingRequestInput",
    "ApprovalRequestCreateInput",
    "ApprovalApproveInput",
    "ApprovalRejectInput",
    "ConsentRecord",
    "ConsentUpsertResponse",
    "ConsentListSummary",
    "ConsentListResponse",
    "PolicyRecord",
    "PolicyCreateResponse",
    "PolicyListSummary",
    "PolicyListResponse",
    "PolicyDetailResponse",
    "PolicyEvaluationReason",
    "PolicyEvaluationSummary",
    "PolicyEvaluationTraceSummary",
    "PolicyEvaluationResponse",
    "ToolRecord",
    "ToolCreateResponse",
    "ToolListSummary",
    "ToolListResponse",
    "ToolDetailResponse",
    "ToolAllowlistReason",
    "ToolAllowlistDecisionRecord",
    "ToolAllowlistEvaluationSummary",
    "ToolAllowlistTraceSummary",
    "ToolAllowlistEvaluationResponse",
    "ToolRoutingRequestRecord",
    "ToolRoutingRequestTracePayload",
    "ToolRoutingDecisionTracePayload",
    "ToolRoutingSummaryTracePayload",
    "ToolRoutingSummary",
    "ToolRoutingTraceSummary",
    "ToolRoutingResponse",
    "ApprovalRoutingRecord",
    "ApprovalResolutionRecord",
    "ApprovalRecord",
    "ApprovalRequestTraceSummary",
    "ApprovalResolutionTraceSummary",
    "ApprovalResolutionRequestTracePayload",
    "ApprovalResolutionStateTracePayload",
    "ApprovalResolutionSummaryTracePayload",
    "ApprovalRequestCreateResponse",
    "ApprovalListSummary",
    "ApprovalListResponse",
    "ApprovalDetailResponse",
    "ApprovalResolutionResponse",
)
_GOVERNANCE_EXPLICIT_METHODS = (
    ("ConsentUpsertInput", "as_payload"),
    ("PolicyCreateInput", "as_payload"),
    ("PolicyEvaluationRequestInput", "as_payload"),
    ("ToolCreateInput", "as_payload"),
    ("ToolAllowlistEvaluationRequestInput", "as_payload"),
    ("ToolRoutingRequestInput", "as_payload"),
    ("ApprovalRequestCreateInput", "as_payload"),
    ("ApprovalApproveInput", "as_payload"),
    ("ApprovalRejectInput", "as_payload"),
)

for _governance_class_name, _governance_method_name in _GOVERNANCE_EXPLICIT_METHODS:
    _governance_class = getattr(_governance_contracts, _governance_class_name)
    _governance_method = getattr(_governance_class, _governance_method_name)
    setattr(
        _governance_class,
        _governance_method_name,
        _clone_contract_function(
            _governance_method,
            qualname=_governance_method.__qualname__,
        ),
    )

for _governance_class_name in _GOVERNANCE_CONTRACT_CLASS_NAMES:
    _governance_class = getattr(_governance_contracts, _governance_class_name)
    if not hasattr(_governance_class, "__dataclass_fields__"):
        continue
    for _governance_generated_name, _governance_generated_method in vars(
        _governance_class
    ).items():
        if (
            isinstance(_governance_generated_method, _FunctionType)
            and _governance_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.governance"
        ):
            setattr(
                _governance_class,
                _governance_generated_name,
                _clone_generated_contract_function(_governance_generated_method),
            )

del _governance_class
del _governance_class_name
del _governance_generated_method
del _governance_generated_name
del _governance_method
del _governance_method_name


import alicebot_api._contracts.execution as _execution_contracts
from alicebot_api._contracts.execution import (
    ProxyExecutionRequestInput,
    ExecutionBudgetCreateInput,
    ExecutionBudgetDeactivateInput,
    ExecutionBudgetSupersedeInput,
)


from alicebot_api._contracts.continuity import (
    PersistedMemoryRecord,
    PersistedMemoryRevisionRecord,
    AdmissionDecisionOutput,
    ExplicitPreferenceAdmissionRecord,
    ExplicitPreferenceExtractionSummary,
    ExplicitPreferenceExtractionResponse,
    ExplicitCommitmentOpenLoopOutcome,
    ExplicitCommitmentAdmissionRecord,
    ExplicitCommitmentExtractionSummary,
    ExplicitCommitmentExtractionResponse,
    ExplicitSignalCaptureSummary,
    ExplicitSignalCaptureResponse,
    ContinuityCaptureEventRecord,
    ContinuityCaptureCandidateRecord,
    ContinuityCaptureCandidatesSummary,
    ContinuityCaptureCandidatesResponse,
    ContinuityCaptureCommitRecord,
    ContinuityCaptureCommitSummary,
    ContinuityCaptureCommitResponse,
    MemoryOperationCandidateRecord,
    MemoryOperationRecord,
    MemoryOperationCandidateGenerateSummary,
    MemoryOperationCandidateGenerateResponse,
    MemoryOperationCommitSummary,
    MemoryOperationCommitResponse,
    MemoryOperationListSummary,
    MemoryOperationCandidateListResponse,
    MemoryOperationListResponse,
    ContinuityLifecycleStateRecord,
    ContinuityObjectRecord,
    ContinuityReviewObjectRecord,
    ContinuityCorrectionEventRecord,
    ContinuityCaptureInboxItem,
    ContinuityCaptureInboxSummary,
    ContinuityCaptureCreateResponse,
    ContinuityCaptureInboxResponse,
    ContinuityCaptureDetailResponse,
    ContinuityReviewQueueSummary,
    ContinuityReviewQueueResponse,
    ContinuitySupersessionChain,
    ContinuityReviewDetail,
    ContinuityReviewDetailResponse,
    ContradictionCaseRecord,
    ContradictionCaseListSummary,
    ContradictionCaseListResponse,
    ContradictionCaseDetailResponse,
    ContradictionSyncSummary,
    ContradictionSyncResponse,
    ContradictionResolveResponse,
    TrustSignalRecord,
    TrustSignalListSummary,
    TrustSignalListResponse,
    ContinuityEvidenceArtifactRecord,
    ContinuityEvidenceArtifactCopyRecord,
    ContinuityEvidenceArtifactSegmentRecord,
    ContinuityEvidenceLinkRecord,
    ContinuityExplanationSourceFactRecord,
    ContinuityExplanationEvidenceSegmentRecord,
    ContinuityExplanationSupersessionNoteRecord,
    ContinuityExplanationContradictionRecord,
    ContinuityExplanationTrustRecord,
    ContinuityExplanationTimestampsRecord,
    ContinuityExplanationRecord,
    ContinuityExplainRecord,
    ContinuityExplainResponse,
    ContinuityArtifactDetailRecord,
    ContinuityArtifactDetailResponse,
    ContinuityRecallScopeFilters,
    ContinuityRecallScopeMatch,
    ContinuityRecallProvenanceReference,
    ContinuityRecallOrderingMetadata,
    ContinuityRetrievalStageScoreRecord,
    ContinuityRetrievalDebugCandidateRecord,
    ContinuityRetrievalDebugRecord,
    ContinuityRecallResultRecord,
    ContinuityRecallSummary,
    ContinuityRecallResponse,
    ContinuityLifecycleCounts,
    ContinuityLifecycleListSummary,
    ContinuityLifecycleListResponse,
    ContinuityLifecycleDetailResponse,
    ContinuityResumptionEmptyState,
    ContinuityResumptionSingleSection,
    ContinuityResumptionListSection,
    ContinuityResumptionBriefRecord,
    ContinuityResumptionDebugRecord,
    ContinuityResumptionBriefResponse,
    ContinuityBriefRelevantFactsSummary,
    ContinuityBriefRelevantFactsSection,
    ContinuityBriefConflictSummary,
    ContinuityBriefConflictSection,
    ContinuityBriefTimelineHighlightRecord,
    ContinuityBriefTimelineSection,
    ContinuityBriefSuggestedActionRecord,
    ContinuityBriefSelectionStrategyRecord,
    ContinuityBriefProvenanceSummary,
    ContinuityBriefProvenanceBundle,
    ContinuityBriefTrustPostureRecord,
    ContinuityBriefRecord,
    ContinuityBriefResponse,
    TaskBriefEmptyState,
    TaskBriefSectionSummary,
    TaskBriefSectionRecord,
    TaskBriefStrategyRecord,
    TaskBriefSummary,
    TaskBriefRecord,
    TaskBriefPersistenceRecord,
    TaskBriefResponse,
    TaskBriefComparisonStats,
    TaskBriefComparisonResponse,
)


from alicebot_api._contracts.retrieval import (
    RetrievalRunRecord,
    RetrievalRunListSummary,
    RetrievalRunListResponse,
    RetrievalTraceSummary,
    RetrievalTraceResponse,
)


from alicebot_api._contracts.continuity import (
    ContinuityOpenLoopSectionSummary,
    ContinuityOpenLoopSection,
    ContinuityOpenLoopDashboardSummary,
    ContinuityOpenLoopDashboardRecord,
    ContinuityOpenLoopDashboardResponse,
    ContinuityDailyBriefRecord,
    ContinuityDailyBriefResponse,
    ContinuityWeeklyReviewRollup,
    ContinuityWeeklyReviewRecord,
    ContinuityWeeklyReviewResponse,
    ContinuityOpenLoopReviewActionResponse,
    ContinuityCorrectionApplyResponse,
    MemoryReviewRecord,
    MemoryReviewListSummary,
    MemoryReviewListResponse,
    MemoryReviewDetailResponse,
    OpenLoopRecord,
    OpenLoopListSummary,
    OpenLoopListResponse,
    OpenLoopDetailResponse,
    OpenLoopCreateResponse,
    OpenLoopStatusUpdateResponse,
    MemoryRevisionReviewRecord,
    MemoryRevisionReviewListSummary,
    MemoryRevisionReviewListResponse,
    MemoryReviewLabelCounts,
    MemoryReviewLabelRecord,
    MemoryReviewLabelSummary,
    MemoryReviewLabelCreateResponse,
    MemoryReviewLabelListResponse,
    MemoryReviewQueueItem,
    MemoryReviewQueueSummary,
    MemoryReviewQueueResponse,
    MemoryQualityGateComputationCounts,
    MemoryQualityGateSummary,
    MemoryQualityGateResponse,
    MemoryTrustQueueAgingSummary,
    MemoryTrustQueuePostureSummary,
    MemoryTrustCorrectionFreshnessSummary,
    MemoryTrustRecommendedReview,
    MemoryHygienePosture,
    MemoryHygieneFocusKind,
    MemoryDuplicateGroupRecord,
    MemoryReviewQueuePressureSummary,
    MemoryHygieneFocusRecord,
    MemoryHygieneDashboardSummary,
    MemoryHygieneDashboardResponse,
    MemoryTrustDashboardSummary,
    MemoryTrustDashboardResponse,
    MemoryEvaluationSummary,
    MemoryEvaluationSummaryResponse,
)


from alicebot_api._contracts.knowledge import (
    EntityRecord,
    EntityCreateResponse,
    EntityListSummary,
    EntityListResponse,
    EntityDetailResponse,
    EntityEdgeRecord,
    EntityEdgeCreateResponse,
    EntityEdgeListSummary,
    EntityEdgeListResponse,
    TemporalValidityRecord,
    TemporalStateFactRecord,
    TemporalStateEdgeRecord,
    TemporalStateSummary,
    TemporalStateAtRecord,
    TemporalStateAtResponse,
    TemporalTimelineEventRecord,
    TemporalTimelineSummary,
    TemporalTimelineRecord,
    TemporalTimelineResponse,
    TemporalTrustRecord,
    TemporalProvenanceRecord,
    TemporalFactSupersessionRecord,
    TemporalFactExplainRecord,
    TemporalEdgeSupersessionRecord,
    TemporalEdgeExplainRecord,
    TemporalExplainSummary,
    TemporalExplainRecord,
    TemporalExplainResponse,
    TrustedFactEvidenceLinkRecord,
    TrustedFactPatternRecord,
    TrustedFactPatternListSummary,
    TrustedFactPatternListResponse,
    TrustedFactPatternExplainResponse,
    TrustedFactPlaybookStepRecord,
    TrustedFactPlaybookRecord,
    TrustedFactPlaybookListSummary,
    TrustedFactPlaybookListResponse,
    TrustedFactPlaybookExplainResponse,
)


from alicebot_api._contracts.retrieval import (
    EmbeddingConfigRecord,
    EmbeddingConfigCreateResponse,
    EmbeddingConfigListSummary,
    EmbeddingConfigListResponse,
    MemoryEmbeddingRecord,
    MemoryEmbeddingUpsertResponse,
    MemoryEmbeddingDetailResponse,
    MemoryEmbeddingListSummary,
    MemoryEmbeddingListResponse,
    SemanticMemoryRetrievalResultItem,
    SemanticMemoryRetrievalSummary,
    SemanticMemoryRetrievalResponse,
    RetrievalEvaluationFixtureResult,
    RetrievalEvaluationSummary,
    RetrievalEvaluationResponse,
    PublicEvalSuiteDefinitionRecord,
    PublicEvalSuiteDefinitionListResponse,
    PublicEvalRunRecord,
    PublicEvalResultRecord,
    PublicEvalRunListResponse,
    PublicEvalRunDetailResponse,
)


from alicebot_api._contracts.governance import (
    ConsentRecord,
    ConsentUpsertResponse,
    ConsentListSummary,
    ConsentListResponse,
    PolicyRecord,
    PolicyCreateResponse,
    PolicyListSummary,
    PolicyListResponse,
    PolicyDetailResponse,
    PolicyEvaluationReason,
    PolicyEvaluationSummary,
    PolicyEvaluationTraceSummary,
    PolicyEvaluationResponse,
    ToolRecord,
    ToolCreateResponse,
    ToolListSummary,
    ToolListResponse,
    ToolDetailResponse,
    ToolAllowlistReason,
    ToolAllowlistDecisionRecord,
    ToolAllowlistEvaluationSummary,
    ToolAllowlistTraceSummary,
    ToolAllowlistEvaluationResponse,
    ToolRoutingRequestRecord,
    ToolRoutingRequestTracePayload,
    ToolRoutingDecisionTracePayload,
    ToolRoutingSummaryTracePayload,
    ToolRoutingSummary,
    ToolRoutingTraceSummary,
    ToolRoutingResponse,
    ApprovalRoutingRecord,
    ApprovalResolutionRecord,
    ApprovalRecord,
    ApprovalRequestTraceSummary,
    ApprovalResolutionTraceSummary,
    ApprovalResolutionRequestTracePayload,
    ApprovalResolutionStateTracePayload,
    ApprovalResolutionSummaryTracePayload,
)


from alicebot_api._contracts.tasks import (
    TaskCreateInput,
    TaskRecord,
    TaskCreateResponse,
    TaskStepCreateInput,
    TaskStepNextCreateInput,
    TaskStepTransitionInput,
    TaskStepLineageInput,
    TaskListSummary,
    TaskListResponse,
    TaskDetailResponse,
    TaskRunCreateInput,
    TaskRunTickInput,
    TaskRunPauseInput,
    TaskRunResumeInput,
    TaskRunCancelInput,
    TaskRunRecord,
    TaskRunCreateResponse,
    TaskRunListSummary,
    TaskRunListResponse,
    TaskRunDetailResponse,
    TaskRunMutationResponse,
)


import alicebot_api._contracts.integrations as _integration_contracts
from alicebot_api._contracts.integrations import (
    GmailAccountConnectInput,
    GmailMessageIngestInput,
    GmailAccountRecord,
    GmailAccountConnectResponse,
    GmailAccountListSummary,
    GmailAccountListResponse,
    GmailAccountDetailResponse,
    GmailMessageIngestionRecord,
    GmailMessageIngestionResponse,
    CalendarAccountConnectInput,
    CalendarEventIngestInput,
    CalendarEventListInput,
    CalendarAccountRecord,
    CalendarAccountConnectResponse,
    CalendarAccountListSummary,
    CalendarAccountListResponse,
    CalendarAccountDetailResponse,
    CalendarEventIngestionRecord,
    CalendarEventIngestionResponse,
    CalendarEventSummaryRecord,
    CalendarEventListSummary,
    CalendarEventListResponse,
)

_INTEGRATION_CONTRACT_CLASS_NAMES = (
    "GmailAccountConnectInput",
    "GmailMessageIngestInput",
    "GmailAccountRecord",
    "GmailAccountConnectResponse",
    "GmailAccountListSummary",
    "GmailAccountListResponse",
    "GmailAccountDetailResponse",
    "GmailMessageIngestionRecord",
    "GmailMessageIngestionResponse",
    "CalendarAccountConnectInput",
    "CalendarEventIngestInput",
    "CalendarEventListInput",
    "CalendarAccountRecord",
    "CalendarAccountConnectResponse",
    "CalendarAccountListSummary",
    "CalendarAccountListResponse",
    "CalendarAccountDetailResponse",
    "CalendarEventIngestionRecord",
    "CalendarEventIngestionResponse",
    "CalendarEventSummaryRecord",
    "CalendarEventListSummary",
    "CalendarEventListResponse",
)

for _integration_class_name in _INTEGRATION_CONTRACT_CLASS_NAMES:
    _integration_class = getattr(_integration_contracts, _integration_class_name)
    if not hasattr(_integration_class, "__dataclass_fields__"):
        continue
    for _integration_generated_name, _integration_generated_method in vars(
        _integration_class
    ).items():
        if (
            isinstance(_integration_generated_method, _FunctionType)
            and _integration_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.integrations"
        ):
            setattr(
                _integration_class,
                _integration_generated_name,
                _clone_generated_contract_function(_integration_generated_method),
            )

del _integration_class
del _integration_class_name
del _integration_generated_method
del _integration_generated_name


from alicebot_api._contracts.tasks import (
    TaskWorkspaceCreateInput,
    TaskWorkspaceRecord,
    TaskWorkspaceCreateResponse,
    TaskWorkspaceListSummary,
    TaskWorkspaceListResponse,
    TaskWorkspaceDetailResponse,
    TaskArtifactRegisterInput,
    TaskArtifactIngestInput,
    TaskScopedArtifactChunkRetrievalInput,
    ArtifactScopedArtifactChunkRetrievalInput,
    TaskScopedSemanticArtifactChunkRetrievalInput,
    ArtifactScopedSemanticArtifactChunkRetrievalInput,
    TaskArtifactRecord,
    TaskArtifactCreateResponse,
    TaskArtifactListSummary,
    TaskArtifactListResponse,
    TaskArtifactDetailResponse,
    TaskArtifactChunkRecord,
    TaskArtifactChunkListSummary,
    TaskArtifactChunkListResponse,
    TaskArtifactChunkEmbeddingRecord,
    TaskArtifactChunkEmbeddingWriteResponse,
    TaskArtifactChunkEmbeddingDetailResponse,
    TaskArtifactChunkEmbeddingListScope,
    TaskArtifactChunkEmbeddingListSummary,
    TaskArtifactChunkEmbeddingListResponse,
    TaskArtifactIngestionResponse,
    TaskArtifactChunkRetrievalMatch,
    TaskArtifactChunkRetrievalItem,
    TaskArtifactChunkRetrievalScope,
    TaskArtifactChunkRetrievalSummary,
    TaskArtifactChunkRetrievalResponse,
    TaskArtifactChunkSemanticRetrievalItem,
    TaskArtifactChunkSemanticRetrievalSummary,
    TaskArtifactChunkSemanticRetrievalResponse,
    TaskStepTraceLink,
    TaskStepOutcomeSnapshot,
    TaskStepLineageRecord,
    TaskStepRecord,
    TaskStepCreateResponse,
    TaskStepSequencingSummary,
    TaskStepListSummary,
    TaskStepListResponse,
    TaskStepDetailResponse,
    TaskStepMutationTraceSummary,
    TaskStepNextCreateResponse,
    TaskStepTransitionResponse,
    ResumptionBriefSectionSummary,
    ResumptionBriefConversationSummary,
    ResumptionBriefConversationSection,
    ResumptionBriefOpenLoopSection,
    ResumptionBriefMemoryHighlightSection,
    ResumptionBriefWorkflowSummary,
    ResumptionBriefWorkflowPosture,
    ResumptionBriefRecord,
    ResumptionBriefResponse,
    TaskLifecycleStateTracePayload,
    TaskLifecycleSummaryTracePayload,
    TaskStepLifecycleStateTracePayload,
    TaskStepLifecycleSummaryTracePayload,
    TaskStepSequenceRequestTracePayload,
    TaskStepSequenceStateTracePayload,
    TaskStepSequenceSummaryTracePayload,
    TaskStepContinuationRequestTracePayload,
    TaskStepContinuationLineageTracePayload,
    TaskStepContinuationSummaryTracePayload,
    TaskStepTransitionRequestTracePayload,
    TaskStepTransitionStateTracePayload,
    TaskStepTransitionSummaryTracePayload,
)


from alicebot_api._contracts.governance import (
    ApprovalRequestCreateResponse,
    ApprovalListSummary,
    ApprovalListResponse,
    ApprovalDetailResponse,
    ApprovalResolutionResponse,
)


from alicebot_api._contracts.execution import (
    ExecutionBudgetRecord,
    ExecutionBudgetCreateResponse,
    ExecutionBudgetListSummary,
    ExecutionBudgetListResponse,
    ExecutionBudgetDetailResponse,
    ExecutionBudgetLifecycleTraceSummary,
    ExecutionBudgetDeactivateResponse,
    ExecutionBudgetSupersedeResponse,
    ExecutionBudgetDecisionRecord,
    ExecutionBudgetLifecycleRequestTracePayload,
    ExecutionBudgetLifecycleStateTracePayload,
    ExecutionBudgetLifecycleSummaryTracePayload,
    ToolExecutionCreateInput,
    ToolExecutionRecord,
    ToolExecutionListSummary,
    ToolExecutionListResponse,
    ToolExecutionDetailResponse,
    ProxyExecutionRequestRecord,
    ProxyExecutionRequestEventPayload,
    ProxyExecutionResultRecord,
    ProxyExecutionResultEventPayload,
    ToolExecutionResultRecord,
    ProxyExecutionEventSummary,
    ProxyExecutionTraceSummary,
    ProxyExecutionBudgetPrecheckTracePayload,
    ProxyExecutionApprovalTracePayload,
    ProxyExecutionBudgetContextTracePayload,
    ProxyExecutionDispatchTracePayload,
    ProxyExecutionSummaryTracePayload,
    ProxyExecutionResponse,
    ProxyExecutionBudgetBlockedResponse,
)

_EXECUTION_CONTRACT_CLASS_NAMES = (
    "ProxyExecutionRequestInput",
    "ExecutionBudgetCreateInput",
    "ExecutionBudgetDeactivateInput",
    "ExecutionBudgetSupersedeInput",
    "ExecutionBudgetRecord",
    "ExecutionBudgetCreateResponse",
    "ExecutionBudgetListSummary",
    "ExecutionBudgetListResponse",
    "ExecutionBudgetDetailResponse",
    "ExecutionBudgetLifecycleTraceSummary",
    "ExecutionBudgetDeactivateResponse",
    "ExecutionBudgetSupersedeResponse",
    "ExecutionBudgetDecisionRecord",
    "ExecutionBudgetLifecycleRequestTracePayload",
    "ExecutionBudgetLifecycleStateTracePayload",
    "ExecutionBudgetLifecycleSummaryTracePayload",
    "ToolExecutionCreateInput",
    "ToolExecutionRecord",
    "ToolExecutionListSummary",
    "ToolExecutionListResponse",
    "ToolExecutionDetailResponse",
    "ProxyExecutionRequestRecord",
    "ProxyExecutionRequestEventPayload",
    "ProxyExecutionResultRecord",
    "ProxyExecutionResultEventPayload",
    "ToolExecutionResultRecord",
    "ProxyExecutionEventSummary",
    "ProxyExecutionTraceSummary",
    "ProxyExecutionBudgetPrecheckTracePayload",
    "ProxyExecutionApprovalTracePayload",
    "ProxyExecutionBudgetContextTracePayload",
    "ProxyExecutionDispatchTracePayload",
    "ProxyExecutionSummaryTracePayload",
    "ProxyExecutionResponse",
    "ProxyExecutionBudgetBlockedResponse",
)

_EXECUTION_EXPLICIT_METHODS = (
    ("ProxyExecutionRequestInput", "as_payload"),
    ("ExecutionBudgetCreateInput", "as_payload"),
    ("ExecutionBudgetDeactivateInput", "as_payload"),
    ("ExecutionBudgetSupersedeInput", "as_payload"),
)

for _execution_class_name, _execution_method_name in _EXECUTION_EXPLICIT_METHODS:
    _execution_class = getattr(_execution_contracts, _execution_class_name)
    _execution_method = getattr(_execution_class, _execution_method_name)
    setattr(
        _execution_class,
        _execution_method_name,
        _clone_contract_function(
            _execution_method,
            qualname=_execution_method.__qualname__,
        ),
    )

for _execution_class_name in _EXECUTION_CONTRACT_CLASS_NAMES:
    _execution_class = getattr(_execution_contracts, _execution_class_name)
    if not hasattr(_execution_class, "__dataclass_fields__"):
        continue
    for _execution_generated_name, _execution_generated_method in vars(
        _execution_class
    ).items():
        if (
            isinstance(_execution_generated_method, _FunctionType)
            and _execution_generated_method.__globals__.get("__name__")
            == "alicebot_api._contracts.execution"
        ):
            setattr(
                _execution_class,
                _execution_generated_name,
                _clone_generated_contract_function(_execution_generated_method),
            )

del _execution_class
del _execution_class_name
del _execution_generated_method
del _execution_generated_name
del _execution_method
del _execution_method_name


isoformat_or_none = _clone_contract_function(
    _common_isoformat_or_none,  # type: ignore[arg-type]
    qualname="isoformat_or_none",
)
