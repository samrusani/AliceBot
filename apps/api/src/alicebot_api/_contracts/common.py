from __future__ import annotations

from datetime import datetime
from typing import Literal

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
    "procedure",
    "constraint",
    "working_style",
]
MemoryConfirmationStatus = Literal["unconfirmed", "confirmed", "contested"]
MemoryTrustClass = Literal[
    "deterministic",
    "llm_single_source",
    "llm_corroborated",
    "human_curated",
]
MemoryPromotionEligibility = Literal["promotable", "not_promotable"]
ContinuityPreservationStatus = Literal["preserved", "not_preserved"]
ContinuitySearchabilityStatus = Literal["searchable", "not_searchable"]
ContinuityPromotionStatus = Literal["promotable", "not_promotable"]
ContinuityRecallFreshnessPosture = Literal["fresh", "aging", "stale", "superseded", "unknown"]
ContinuityRecallProvenancePosture = Literal["strong", "partial", "weak", "missing"]
ContinuityRecallSupersessionPosture = Literal["current", "historical", "superseded", "deleted"]
RetrievalEvaluationStatus = Literal["pass", "fail"]
MemoryReviewStatusFilter = Literal["active", "deleted", "all"]
MemoryReviewLabelValue = Literal["correct", "incorrect", "outdated", "insufficient_evidence"]
MemoryQualityGateStatus = Literal["healthy", "needs_review", "insufficient_sample", "degraded"]
MemoryQualityReviewAction = Literal[
    "adjudicate_minimum_sample",
    "review_high_risk_queue",
    "review_stale_truth_queue",
    "drain_unlabeled_queue",
    "investigate_correction_recurrence",
    "remediate_freshness_drift",
    "monitor_quality_posture",
]
MemoryReviewQueuePriorityMode = Literal[
    "oldest_first",
    "recent_first",
    "high_risk_first",
    "stale_truth_first",
]
EntityType = Literal["person", "merchant", "product", "project", "routine"]
EmbeddingConfigStatus = Literal["active", "deprecated", "disabled"]
ConsentStatus = Literal["granted", "revoked"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
ApprovalResolutionAction = Literal["approve", "reject"]
ApprovalResolutionOutcome = Literal["resolved", "duplicate_rejected", "conflict_rejected"]
TaskStatus = Literal["pending_approval", "approved", "executed", "denied", "blocked"]
TaskRunStatus = Literal[
    "queued",
    "running",
    "waiting_approval",
    "waiting_user",
    "paused",
    "failed",
    "done",
    "cancelled",
]
TaskRunStopReason = Literal[
    "waiting_approval",
    "waiting_user",
    "paused",
    "budget_exhausted",
    "approval_rejected",
    "policy_blocked",
    "retry_exhausted",
    "fatal_error",
    "done",
    "cancelled",
]
TaskRunFailureClass = Literal["transient", "policy", "approval", "budget", "fatal"]
TaskRunRetryPosture = Literal[
    "none",
    "retryable",
    "exhausted",
    "terminal",
    "paused",
    "awaiting_approval",
    "awaiting_user",
]
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
ProviderAdapterKey = Literal["openai_compatible", "ollama", "llamacpp", "vllm", "azure"]
ModelProviderStatus = Literal["active"]
ProviderCapabilityDiscoveryStatus = Literal["ready", "failed"]
ModelFinishReason = Literal["completed", "incomplete"]
TaskBriefMode = Literal["user_recall", "resume", "worker_subtask", "agent_handoff"]
TaskBriefingStrategy = Literal["balanced", "compact", "detailed"]
ContinuityBriefType = Literal[
    "general",
    "resume",
    "agent_handoff",
    "coding_context",
    "operator_context",
]
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
ContinuityObjectType = Literal[
    "Note",
    "MemoryFact",
    "Decision",
    "Commitment",
    "WaitingFor",
    "Blocker",
    "NextAction",
]
ContinuityCaptureExplicitSignal = Literal[
    "remember_this",
    "task",
    "decision",
    "commitment",
    "waiting_for",
    "blocker",
    "next_action",
    "note",
]
ContinuityCaptureAdmissionPosture = Literal["DERIVED", "TRIAGE"]
ContinuityCaptureCandidateType = Literal[
    "decision",
    "commitment",
    "waiting_for",
    "blocker",
    "preference",
    "correction",
    "note",
    "no_op",
]
ContinuityCaptureCommitMode = Literal["manual", "assist", "auto"]
ContinuityCaptureCommitDecision = Literal[
    "auto_saved",
    "queued_for_review",
    "no_op",
    "duplicate_noop",
]
ContinuityCaptureProposedAction = Literal["auto_save_candidate", "queue_for_review", "no_op"]
MemoryOperationType = Literal["ADD", "UPDATE", "SUPERSEDE", "DELETE", "NOOP"]
MemoryOperationPolicyAction = Literal["auto_apply", "review_required", "skip"]
MemoryOperationStatus = Literal["applied", "no_op", "skipped", "duplicate"]
ContinuityRecallScopeKind = Literal["thread", "task", "project", "person"]
ContinuityCorrectionAction = Literal["confirm", "edit", "delete", "supersede", "mark_stale"]
ContinuityReviewStatus = Literal["active", "stale", "superseded", "deleted"]
ContinuityReviewStatusFilter = Literal["correction_ready", "active", "stale", "superseded", "deleted", "all"]
ContradictionKind = Literal[
    "direct_fact_conflict",
    "preference_conflict",
    "temporal_conflict",
    "source_hierarchy_conflict",
]
ContradictionStatus = Literal["open", "resolved", "dismissed"]
ContradictionResolutionAction = Literal[
    "confirm_primary",
    "confirm_counterpart",
    "mark_historical",
    "dismiss_false_positive",
    "auto_resolved",
]
TrustSignalType = Literal["correction", "corroboration", "contradiction", "weak_inference"]
TrustSignalState = Literal["active", "inactive"]
TrustSignalDirection = Literal["positive", "negative", "neutral"]
ContinuityOpenLoopPosture = Literal["waiting_for", "blocker", "stale", "next_action"]
ContinuityOpenLoopReviewAction = Literal["done", "deferred", "still_blocked"]
RecommendationConfidencePosture = Literal["high", "medium", "low"]
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
DEFAULT_CONTINUITY_CAPTURE_LIMIT = 20
MAX_CONTINUITY_CAPTURE_LIMIT = 100
DEFAULT_CONTINUITY_REVIEW_LIMIT = 20
MAX_CONTINUITY_REVIEW_LIMIT = 100
DEFAULT_CONTINUITY_RECALL_LIMIT = 20
MAX_CONTINUITY_RECALL_LIMIT = 100
DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT = 5
MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT = 20
DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT = 5
MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT = 20
DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT = 6
MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT = 20
DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT = 5
MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT = 20
DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT = 5
MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT = 20
DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT = 20
MAX_CONTINUITY_OPEN_LOOP_LIMIT = 100
DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT = 3
MAX_CONTINUITY_DAILY_BRIEF_LIMIT = 20
DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT = 5
MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT = 50
DEFAULT_CALENDAR_EVENT_LIST_LIMIT = 20
MAX_CALENDAR_EVENT_LIST_LIMIT = 50
COMPILER_VERSION_V0 = "continuity_v0"
PROMPT_ASSEMBLY_VERSION_V0 = "prompt_assembly_v0"
RESPONSE_GENERATION_VERSION_V0 = "response_generation_v0"
PROVIDER_CAPABILITY_VERSION_V1 = "provider_capability_v1"
TRACE_KIND_CONTEXT_COMPILE = "context.compile"
TRACE_KIND_RESPONSE_GENERATE = "response.generate"
TRACE_REVIEW_LIST_ORDER = ["created_at_desc", "id_desc"]
TRACE_REVIEW_EVENT_LIST_ORDER = ["sequence_no_asc", "id_asc"]
THREAD_LIST_ORDER = ["created_at_desc", "id_desc"]
AGENT_PROFILE_LIST_ORDER = ["id_asc"]
THREAD_SESSION_LIST_ORDER = ["started_at_asc", "created_at_asc", "id_asc"]
THREAD_EVENT_LIST_ORDER = ["sequence_no_asc"]
PROVIDER_LIST_ORDER = ["created_at_asc", "id_asc"]
DEFAULT_AGENT_PROFILE_ID = "assistant_default"
RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0 = "resumption_brief_v0"
CONTINUITY_RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0 = "continuity_resumption_brief_v0"
TASK_BRIEF_ASSEMBLY_VERSION_V0 = "task_brief_v0"
TASK_BRIEF_COMPARISON_VERSION_V0 = "task_brief_comparison_v0"
CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0 = "continuity_brief_v0"
CONTINUITY_DAILY_BRIEF_ASSEMBLY_VERSION_V0 = "continuity_daily_brief_v0"
CONTINUITY_WEEKLY_REVIEW_ASSEMBLY_VERSION_V0 = "continuity_weekly_review_v0"
RESUMPTION_BRIEF_CONVERSATION_EVENT_KINDS = ["message.user", "message.assistant"]
RESUMPTION_BRIEF_CONVERSATION_ORDER = ["sequence_no_asc"]
RESUMPTION_BRIEF_MEMORY_ORDER = ["updated_at_asc", "created_at_asc", "id_asc"]
MEMORY_REVIEW_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
MEMORY_REVIEW_QUEUE_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
DEFAULT_MEMORY_REVIEW_QUEUE_PRIORITY_MODE: MemoryReviewQueuePriorityMode = "recent_first"
MEMORY_REVIEW_QUEUE_PRIORITY_MODES: list[MemoryReviewQueuePriorityMode] = [
    "oldest_first",
    "recent_first",
    "high_risk_first",
    "stale_truth_first",
]
DEFAULT_TASK_BRIEF_TOKEN_BUDGET = 220
MAX_TASK_BRIEF_TOKEN_BUDGET = 4000
TASK_BRIEF_MODE_ORDER: list[TaskBriefMode] = [
    "user_recall",
    "resume",
    "worker_subtask",
    "agent_handoff",
]
CONTINUITY_BRIEF_TYPE_ORDER: list[ContinuityBriefType] = [
    "general",
    "resume",
    "agent_handoff",
    "coding_context",
    "operator_context",
]
TASK_BRIEF_SECTION_ITEM_ORDER = ["created_at_desc", "id_desc"]
TASK_BRIEFING_STRATEGIES: list[TaskBriefingStrategy] = [
    "balanced",
    "compact",
    "detailed",
]
MEMORY_REVIEW_QUEUE_ORDER_BY_PRIORITY_MODE: dict[MemoryReviewQueuePriorityMode, list[str]] = {
    "oldest_first": ["updated_at_asc", "created_at_asc", "id_asc"],
    "recent_first": ["updated_at_desc", "created_at_desc", "id_desc"],
    "high_risk_first": [
        "is_high_risk_desc",
        "confidence_asc_nulls_first",
        "updated_at_desc",
        "created_at_desc",
        "id_desc",
    ],
    "stale_truth_first": [
        "is_stale_truth_desc",
        "valid_to_asc_nulls_last",
        "updated_at_desc",
        "created_at_desc",
        "id_desc",
    ],
}
MEMORY_QUALITY_PRECISION_TARGET = 0.8
MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE = 10
MEMORY_QUALITY_HIGH_RISK_CONFIDENCE_THRESHOLD = 0.7
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
MEMORY_TRUST_CLASSES = [
    "deterministic",
    "llm_single_source",
    "llm_corroborated",
    "human_curated",
]
MEMORY_PROMOTION_ELIGIBILITIES = [
    "promotable",
    "not_promotable",
]
OPEN_LOOP_STATUSES = [
    "open",
    "resolved",
    "dismissed",
]
DEFAULT_MEMORY_TYPE: MemoryType = "preference"
DEFAULT_MEMORY_CONFIRMATION_STATUS: MemoryConfirmationStatus = "unconfirmed"
DEFAULT_MEMORY_TRUST_CLASS: MemoryTrustClass = "deterministic"
DEFAULT_MEMORY_PROMOTION_ELIGIBILITY: MemoryPromotionEligibility = "promotable"
DEFAULT_CONTINUITY_LIFECYCLE_LIMIT = 50
MAX_CONTINUITY_LIFECYCLE_LIMIT = 200
DEFAULT_RETRIEVAL_RUN_LIST_LIMIT = 20
MAX_RETRIEVAL_RUN_LIST_LIMIT = 100
DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT = 50
MAX_TRUSTED_FACT_PROMOTION_LIMIT = 200
ENTITY_TYPES = [
    "person",
    "merchant",
    "product",
    "project",
    "routine",
]
ENTITY_LIST_ORDER = ["created_at_asc", "id_asc"]
ENTITY_EDGE_LIST_ORDER = ["created_at_asc", "id_asc"]
TEMPORAL_TIMELINE_ORDER = ["occurred_at_asc", "event_type_asc", "id_asc"]
TRUSTED_FACT_PATTERN_ORDER = ["memory_type_asc", "namespace_key_asc", "title_asc", "id_asc"]
TRUSTED_FACT_PLAYBOOK_ORDER = ["memory_type_asc", "pattern_key_asc", "title_asc", "id_asc"]
EMBEDDING_CONFIG_LIST_ORDER = ["created_at_asc", "id_asc"]
MEMORY_EMBEDDING_LIST_ORDER = ["created_at_asc", "id_asc"]
SEMANTIC_MEMORY_RETRIEVAL_ORDER = ["score_desc", "created_at_asc", "id_asc"]
RETRIEVAL_EVALUATION_FIXTURE_ORDER = ["fixture_id_asc"]
RETRIEVAL_EVALUATION_RESULT_ORDER = [
    "precision_at_k_desc",
    "precision_lift_at_k_desc",
    "fixture_id_asc",
]
RETRIEVAL_RUN_LIST_ORDER = ["created_at_desc", "id_desc"]
RETRIEVAL_TRACE_CANDIDATE_ORDER = [
    "selected_desc",
    "rank_asc",
    "relevance_desc",
    "id_asc",
]
EMBEDDING_CONFIG_STATUSES = ["active", "deprecated", "disabled"]
CONSENT_STATUSES = ["granted", "revoked"]
CONSENT_LIST_ORDER = ["consent_key_asc", "created_at_asc", "id_asc"]
POLICY_EFFECTS = ["allow", "deny", "require_approval"]
POLICY_LIST_ORDER = ["priority_asc", "created_at_asc", "id_asc"]
POLICY_EVALUATION_VERSION_V0 = "policy_evaluation_v0"
TRACE_KIND_POLICY_EVALUATE = "policy.evaluate"
TOOL_METADATA_VERSION_V0: ToolMetadataVersion = "tool_metadata_v0"
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
TASK_RUN_STATUSES = [
    "queued",
    "running",
    "waiting_approval",
    "waiting_user",
    "paused",
    "failed",
    "done",
    "cancelled",
]
TASK_RUN_STOP_REASONS = [
    "waiting_approval",
    "waiting_user",
    "paused",
    "budget_exhausted",
    "approval_rejected",
    "policy_blocked",
    "retry_exhausted",
    "fatal_error",
    "done",
    "cancelled",
]
TASK_RUN_FAILURE_CLASSES = ["transient", "policy", "approval", "budget", "fatal"]
TASK_RUN_RETRY_POSTURES = [
    "none",
    "retryable",
    "exhausted",
    "terminal",
    "paused",
    "awaiting_approval",
    "awaiting_user",
]
TASK_RUN_LIST_ORDER = ["created_at_asc", "id_asc"]
CONTINUITY_CAPTURE_LIST_ORDER = ["created_at_desc", "id_desc"]
CONTINUITY_OBJECT_LIST_ORDER = ["created_at_desc", "id_desc"]
CONTINUITY_REVIEW_QUEUE_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
CONTINUITY_CORRECTION_EVENT_ORDER = ["created_at_desc", "id_desc"]
CONTRADICTION_CASE_LIST_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
TRUST_SIGNAL_LIST_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
CONTINUITY_RECALL_LIST_ORDER = ["relevance_desc", "created_at_desc", "id_desc"]
CONTINUITY_LIFECYCLE_LIST_ORDER = ["updated_at_desc", "id_desc"]
CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER = ["created_at_desc", "id_desc"]
CONTINUITY_RESUMPTION_OPEN_LOOP_ORDER = ["created_at_desc", "id_desc"]
CONTINUITY_OPEN_LOOP_POSTURE_ORDER = ["waiting_for", "blocker", "stale", "next_action"]
CONTINUITY_OPEN_LOOP_ITEM_ORDER = ["created_at_desc", "id_desc"]
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
CONTINUITY_OBJECT_TYPES = [
    "Note",
    "MemoryFact",
    "Decision",
    "Commitment",
    "WaitingFor",
    "Blocker",
    "NextAction",
]
CONTINUITY_CAPTURE_EXPLICIT_SIGNALS = [
    "remember_this",
    "task",
    "decision",
    "commitment",
    "waiting_for",
    "blocker",
    "next_action",
    "note",
]
CONTINUITY_CAPTURE_CANDIDATE_TYPES = [
    "decision",
    "commitment",
    "waiting_for",
    "blocker",
    "preference",
    "correction",
    "note",
    "no_op",
]
CONTINUITY_CAPTURE_COMMIT_MODES = ["manual", "assist", "auto"]
CONTINUITY_CAPTURE_ASSIST_AUTOSAVE_TYPES = [
    "correction",
    "preference",
    "decision",
    "commitment",
    "waiting_for",
    "blocker",
]
CONTINUITY_CAPTURE_REVIEW_REQUIRED_TYPES = ["note"]
MEMORY_OPERATION_TYPES = ["ADD", "UPDATE", "SUPERSEDE", "DELETE", "NOOP"]
MEMORY_OPERATION_POLICY_ACTIONS = ["auto_apply", "review_required", "skip"]
MEMORY_OPERATION_STATUSES = ["applied", "no_op", "skipped", "duplicate"]
CONTINUITY_CORRECTION_ACTIONS = [
    "confirm",
    "edit",
    "delete",
    "supersede",
    "mark_stale",
]
CONTINUITY_PRESERVATION_STATUSES = [
    "preserved",
    "not_preserved",
]
CONTINUITY_SEARCHABILITY_STATUSES = [
    "searchable",
    "not_searchable",
]
CONTINUITY_PROMOTION_STATUSES = [
    "promotable",
    "not_promotable",
]
CONTINUITY_REVIEW_STATUSES = [
    "active",
    "stale",
    "superseded",
    "deleted",
]
CONTRADICTION_KINDS = [
    "direct_fact_conflict",
    "preference_conflict",
    "temporal_conflict",
    "source_hierarchy_conflict",
]
CONTRADICTION_STATUSES = [
    "open",
    "resolved",
    "dismissed",
]
CONTRADICTION_RESOLUTION_ACTIONS = [
    "confirm_primary",
    "confirm_counterpart",
    "mark_historical",
    "dismiss_false_positive",
    "auto_resolved",
]
TRUST_SIGNAL_TYPES = [
    "correction",
    "corroboration",
    "contradiction",
    "weak_inference",
]
TRUST_SIGNAL_STATES = [
    "active",
    "inactive",
]
TRUST_SIGNAL_DIRECTIONS = [
    "positive",
    "negative",
    "neutral",
]
CONTINUITY_OPEN_LOOP_POSTURES = [
    "waiting_for",
    "blocker",
    "stale",
    "next_action",
]
CONTINUITY_OPEN_LOOP_REVIEW_ACTIONS = [
    "done",
    "deferred",
    "still_blocked",
]

DEFAULT_TEMPORAL_TIMELINE_LIMIT = 100
MAX_TEMPORAL_TIMELINE_LIMIT = 500


def isoformat_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
