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
HostedAuthSessionStatus = Literal["active", "revoked", "expired"]
HostedMagicLinkChallengeStatus = Literal["pending", "consumed", "expired"]
HostedDeviceLinkChallengeStatus = Literal["pending", "confirmed", "expired"]
HostedDeviceStatus = Literal["active", "revoked"]
HostedWorkspaceBootstrapStatus = Literal["pending", "ready"]
HostedWorkspaceMemberRole = Literal["owner", "member"]
ChannelTransportType = Literal["telegram"]
ChannelIdentityStatus = Literal["linked", "unlinked"]
ChannelLinkChallengeStatus = Literal["pending", "confirmed", "expired", "cancelled"]
ChannelMessageDirection = Literal["inbound", "outbound"]
ChannelMessageRouteStatus = Literal["resolved", "unresolved"]
ChatIntentKind = Literal[
    "inbound_message",
    "capture",
    "recall",
    "resume",
    "correction",
    "open_loops",
    "open_loop_review",
    "approvals",
    "approval_approve",
    "approval_reject",
    "unknown",
]
ChatIntentStatus = Literal["pending", "recorded", "handled", "failed"]
ChannelDeliveryReceiptStatus = Literal["delivered", "failed", "simulated", "suppressed"]
TelegramSchedulerJobKind = Literal["daily_brief", "open_loop_prompt"]
TelegramSchedulerPromptKind = Literal["waiting_for", "stale"]
TelegramSchedulerJobStatus = Literal[
    "scheduled",
    "delivered",
    "simulated",
    "suppressed_quiet_hours",
    "suppressed_disabled",
    "suppressed_outside_window",
    "failed",
]
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
ProviderAdapterKey = Literal["openai_compatible", "ollama", "llamacpp", "azure"]
ModelProviderStatus = Literal["active"]
ProviderCapabilityDiscoveryStatus = Literal["ready", "failed"]
ModelPackFamily = Literal[
    "llama",
    "qwen",
    "gemma",
    "gpt-oss",
    "deepseek",
    "kimi",
    "mistral",
    "custom",
]
ModelPackStatus = Literal["active"]
ModelPackBindingSource = Literal["manual", "runtime_override"]
ModelPackBriefingStrategy = Literal["balanced", "compact", "detailed"]
ModelFinishReason = Literal["completed", "incomplete"]
TaskBriefMode = Literal["user_recall", "resume", "worker_subtask", "agent_handoff"]
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
ChiefOfStaffPriorityPosture = Literal["urgent", "important", "waiting", "blocked", "stale", "defer"]
ChiefOfStaffRecommendationConfidencePosture = Literal["high", "medium", "low"]
ChiefOfStaffRecommendedActionType = Literal[
    "execute_next_action",
    "progress_commitment",
    "follow_up_waiting_for",
    "unblock_blocker",
    "refresh_stale_item",
    "review_and_defer",
    "capture_new_priority",
]
ChiefOfStaffFollowThroughPosture = Literal["overdue", "stale_waiting_for", "slipped_commitment"]
ChiefOfStaffFollowThroughRecommendationAction = Literal[
    "nudge",
    "defer",
    "escalate",
    "close_loop_candidate",
]
ChiefOfStaffEscalationPosture = Literal["watch", "elevated", "critical"]
ChiefOfStaffResumptionRecommendationAction = Literal[
    "execute_next_action",
    "progress_commitment",
    "follow_up_waiting_for",
    "unblock_blocker",
    "refresh_stale_item",
    "review_and_defer",
    "capture_new_priority",
    "nudge",
    "defer",
    "escalate",
    "close_loop_candidate",
    "review_scope",
]
ChiefOfStaffRecommendationOutcome = Literal["accept", "defer", "ignore", "rewrite"]
ChiefOfStaffWeeklyReviewGuidanceAction = Literal["close", "defer", "escalate"]
ChiefOfStaffPatternDriftPosture = Literal["improving", "stable", "drifting", "insufficient_signal"]
ChiefOfStaffActionHandoffSourceKind = Literal[
    "recommended_next_action",
    "follow_through",
    "prep_checklist",
    "weekly_review",
]
ChiefOfStaffActionHandoffAction = Literal[
    "execute_next_action",
    "progress_commitment",
    "follow_up_waiting_for",
    "unblock_blocker",
    "refresh_stale_item",
    "review_and_defer",
    "capture_new_priority",
    "nudge",
    "defer",
    "escalate",
    "close_loop_candidate",
    "review_scope",
    "weekly_review_close",
    "weekly_review_defer",
    "weekly_review_escalate",
]
ChiefOfStaffExecutionPosture = Literal["approval_bounded_artifact_only"]
ChiefOfStaffExecutionReadinessPosture = Literal["approval_required_draft_only"]
ChiefOfStaffExecutionRouteTarget = Literal[
    "task_workflow_draft",
    "approval_workflow_draft",
    "follow_up_draft_only",
]
ChiefOfStaffExecutionRoutingTransition = Literal["routed", "reaffirmed"]
ChiefOfStaffHandoffQueueLifecycleState = Literal[
    "ready",
    "pending_approval",
    "executed",
    "stale",
    "expired",
]
ChiefOfStaffHandoffReviewAction = Literal[
    "mark_ready",
    "mark_pending_approval",
    "mark_executed",
    "mark_stale",
    "mark_expired",
]
ChiefOfStaffHandoffOutcomeStatus = Literal[
    "reviewed",
    "approved",
    "rejected",
    "rewritten",
    "executed",
    "ignored",
    "expired",
]
ChiefOfStaffClosureQualityPosture = Literal["insufficient_signal", "healthy", "watch", "critical"]
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
DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT = 12
MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT = 100
DEFAULT_CALENDAR_EVENT_LIST_LIMIT = 20
MAX_CALENDAR_EVENT_LIST_LIMIT = 50
DEFAULT_CHANNEL_MESSAGE_LIMIT = 50
MAX_CHANNEL_MESSAGE_LIMIT = 200
COMPILER_VERSION_V0 = "continuity_v0"
PROMPT_ASSEMBLY_VERSION_V0 = "prompt_assembly_v0"
RESPONSE_GENERATION_VERSION_V0 = "response_generation_v0"
PROVIDER_CAPABILITY_VERSION_V1 = "provider_capability_v1"
MODEL_PACK_CONTRACT_VERSION_V1 = "model_pack_contract_v1"
TRACE_KIND_CONTEXT_COMPILE = "context.compile"
TRACE_KIND_RESPONSE_GENERATE = "response.generate"
TRACE_REVIEW_LIST_ORDER = ["created_at_desc", "id_desc"]
TRACE_REVIEW_EVENT_LIST_ORDER = ["sequence_no_asc", "id_asc"]
THREAD_LIST_ORDER = ["created_at_desc", "id_desc"]
AGENT_PROFILE_LIST_ORDER = ["id_asc"]
THREAD_SESSION_LIST_ORDER = ["started_at_asc", "created_at_asc", "id_asc"]
THREAD_EVENT_LIST_ORDER = ["sequence_no_asc"]
PROVIDER_LIST_ORDER = ["created_at_asc", "id_asc"]
MODEL_PACK_LIST_ORDER = ["pack_id_asc", "created_at_desc", "id_desc"]
DEFAULT_AGENT_PROFILE_ID = "assistant_default"
RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0 = "resumption_brief_v0"
CONTINUITY_RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0 = "continuity_resumption_brief_v0"
TASK_BRIEF_ASSEMBLY_VERSION_V0 = "task_brief_v0"
TASK_BRIEF_COMPARISON_VERSION_V0 = "task_brief_comparison_v0"
CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0 = "continuity_brief_v0"
CONTINUITY_DAILY_BRIEF_ASSEMBLY_VERSION_V0 = "continuity_daily_brief_v0"
CONTINUITY_WEEKLY_REVIEW_ASSEMBLY_VERSION_V0 = "continuity_weekly_review_v0"
CHIEF_OF_STAFF_PRIORITY_BRIEF_ASSEMBLY_VERSION_V0 = "chief_of_staff_priority_brief_v0"
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
MODEL_PACK_BRIEFING_STRATEGIES: list[ModelPackBriefingStrategy] = [
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
CHANNEL_IDENTITY_LIST_ORDER = ["updated_at_desc", "created_at_desc", "id_desc"]
CHANNEL_LINK_CHALLENGE_LIST_ORDER = ["created_at_desc", "id_desc"]
CHANNEL_THREAD_LIST_ORDER = ["last_message_at_desc", "id_desc"]
CHANNEL_MESSAGE_LIST_ORDER = ["created_at_desc", "id_desc"]
CHANNEL_DELIVERY_RECEIPT_LIST_ORDER = ["recorded_at_desc", "id_desc"]
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
CHIEF_OF_STAFF_PRIORITY_POSTURE_ORDER = ["urgent", "important", "waiting", "blocked", "stale", "defer"]
CHIEF_OF_STAFF_PRIORITY_ITEM_ORDER = ["score_desc", "created_at_desc", "id_desc"]
CHIEF_OF_STAFF_RECOMMENDATION_CONFIDENCE_ORDER = ["high", "medium", "low"]
CHIEF_OF_STAFF_RECOMMENDED_ACTION_TYPES = [
    "execute_next_action",
    "progress_commitment",
    "follow_up_waiting_for",
    "unblock_blocker",
    "refresh_stale_item",
    "review_and_defer",
    "capture_new_priority",
]
CHIEF_OF_STAFF_FOLLOW_THROUGH_POSTURE_ORDER = [
    "overdue",
    "stale_waiting_for",
    "slipped_commitment",
]
CHIEF_OF_STAFF_FOLLOW_THROUGH_ITEM_ORDER = [
    "recommendation_action_desc",
    "age_hours_desc",
    "created_at_desc",
    "id_desc",
]
CHIEF_OF_STAFF_FOLLOW_THROUGH_RECOMMENDATION_ACTIONS = [
    "nudge",
    "defer",
    "escalate",
    "close_loop_candidate",
]
CHIEF_OF_STAFF_ESCALATION_POSTURE_ORDER = ["watch", "elevated", "critical"]
CHIEF_OF_STAFF_PREPARATION_ITEM_ORDER = ["rank_asc", "created_at_desc", "id_desc"]
CHIEF_OF_STAFF_RESUMPTION_SUPERVISION_ITEM_ORDER = ["rank_asc"]
CHIEF_OF_STAFF_RESUMPTION_RECOMMENDATION_ACTIONS = [
    "execute_next_action",
    "progress_commitment",
    "follow_up_waiting_for",
    "unblock_blocker",
    "refresh_stale_item",
    "review_and_defer",
    "capture_new_priority",
    "nudge",
    "defer",
    "escalate",
    "close_loop_candidate",
    "review_scope",
]
CHIEF_OF_STAFF_RECOMMENDATION_OUTCOMES = ["accept", "defer", "ignore", "rewrite"]
CHIEF_OF_STAFF_WEEKLY_REVIEW_GUIDANCE_ACTIONS = ["close", "defer", "escalate"]
CHIEF_OF_STAFF_RECOMMENDATION_OUTCOME_ORDER = ["created_at_desc", "id_desc"]
CHIEF_OF_STAFF_OUTCOME_HOTSPOT_ORDER = ["count_desc", "key_asc"]
CHIEF_OF_STAFF_ACTION_HANDOFF_SOURCE_ORDER = [
    "recommended_next_action",
    "follow_through",
    "prep_checklist",
    "weekly_review",
]
CHIEF_OF_STAFF_ACTION_HANDOFF_ITEM_ORDER = ["score_desc", "source_order_asc", "source_reference_id_asc"]
CHIEF_OF_STAFF_ACTION_HANDOFF_ACTIONS = [
    "execute_next_action",
    "progress_commitment",
    "follow_up_waiting_for",
    "unblock_blocker",
    "refresh_stale_item",
    "review_and_defer",
    "capture_new_priority",
    "nudge",
    "defer",
    "escalate",
    "close_loop_candidate",
    "review_scope",
    "weekly_review_close",
    "weekly_review_defer",
    "weekly_review_escalate",
]
CHIEF_OF_STAFF_EXECUTION_POSTURE_ORDER = ["approval_bounded_artifact_only"]
CHIEF_OF_STAFF_EXECUTION_READINESS_POSTURE_ORDER = ["approval_required_draft_only"]
CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER = [
    "task_workflow_draft",
    "approval_workflow_draft",
    "follow_up_draft_only",
]
CHIEF_OF_STAFF_EXECUTION_ROUTED_ITEM_ORDER = ["handoff_rank_asc", "handoff_item_id_asc"]
CHIEF_OF_STAFF_EXECUTION_ROUTING_AUDIT_ORDER = ["created_at_desc", "id_desc"]
CHIEF_OF_STAFF_EXECUTION_ROUTING_TRANSITIONS = ["routed", "reaffirmed"]
CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER = [
    "ready",
    "pending_approval",
    "executed",
    "stale",
    "expired",
]
CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER = [
    "queue_rank_asc",
    "handoff_rank_asc",
    "score_desc",
    "handoff_item_id_asc",
]
CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS = [
    "mark_ready",
    "mark_pending_approval",
    "mark_executed",
    "mark_stale",
    "mark_expired",
]
CHIEF_OF_STAFF_HANDOFF_OUTCOME_STATUSES = [
    "reviewed",
    "approved",
    "rejected",
    "rewritten",
    "executed",
    "ignored",
    "expired",
]
CHIEF_OF_STAFF_HANDOFF_OUTCOME_ORDER = ["created_at_desc", "id_desc"]
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


class ModelPackRecord(TypedDict):
    id: str
    workspace_id: str
    created_by_user_account_id: str
    pack_id: str
    pack_version: str
    display_name: str
    family: ModelPackFamily
    description: str
    status: ModelPackStatus
    briefing_strategy: ModelPackBriefingStrategy
    briefing_max_tokens: int | None
    contract: JsonObject
    metadata: JsonObject
    created_at: str
    updated_at: str


class ModelPackListSummary(TypedDict):
    total_count: int
    order: list[str]


class ModelPackListResponse(TypedDict):
    items: list[ModelPackRecord]
    summary: ModelPackListSummary


class ModelPackDetailResponse(TypedDict):
    model_pack: ModelPackRecord


class WorkspaceModelPackBindingRecord(TypedDict):
    id: str
    workspace_id: str
    model_pack_id: str
    bound_by_user_account_id: str
    binding_source: ModelPackBindingSource
    metadata: JsonObject
    created_at: str
    model_pack: ModelPackRecord


class WorkspaceModelPackBindingResponse(TypedDict):
    binding: WorkspaceModelPackBindingRecord | None


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
    trust_class: str | None = None
    promotion_eligibility: str | None = None
    evidence_count: int | None = None
    independent_source_count: int | None = None
    extracted_by_model: str | None = None
    trust_reason: str | None = None
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
        if self.trust_class is not None:
            payload["trust_class"] = self.trust_class
        if self.promotion_eligibility is not None:
            payload["promotion_eligibility"] = self.promotion_eligibility
        if self.evidence_count is not None:
            payload["evidence_count"] = self.evidence_count
        if self.independent_source_count is not None:
            payload["independent_source_count"] = self.independent_source_count
        if self.extracted_by_model is not None:
            payload["extracted_by_model"] = self.extracted_by_model
        if self.trust_reason is not None:
            payload["trust_reason"] = self.trust_reason
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
class ContinuityCaptureCreateInput:
    raw_content: str
    explicit_signal: ContinuityCaptureExplicitSignal | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "raw_content": self.raw_content,
        }
        payload["explicit_signal"] = self.explicit_signal
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityCaptureCandidatesInput:
    user_content: str
    assistant_content: str
    session_id: str | None = None
    source_kind: str = "sync_turn"

    def as_payload(self) -> JsonObject:
        return {
            "user_content": self.user_content,
            "assistant_content": self.assistant_content,
            "session_id": self.session_id,
            "source_kind": self.source_kind,
        }


@dataclass(frozen=True, slots=True)
class ContinuityCaptureCommitInput:
    mode: ContinuityCaptureCommitMode = "assist"
    candidates: list[JsonObject] = field(default_factory=list)
    sync_fingerprint: str | None = None
    source_kind: str = "sync_turn"

    def as_payload(self) -> JsonObject:
        return {
            "mode": self.mode,
            "candidates": self.candidates,
            "sync_fingerprint": self.sync_fingerprint,
            "source_kind": self.source_kind,
        }


@dataclass(frozen=True, slots=True)
class MemoryOperationGenerateInput:
    user_content: str
    assistant_content: str
    mode: ContinuityCaptureCommitMode = "assist"
    sync_fingerprint: str | None = None
    source_kind: str = "sync_turn"
    session_id: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    target_continuity_object_id: UUID | None = None

    def as_payload(self) -> JsonObject:
        return {
            "user_content": self.user_content,
            "assistant_content": self.assistant_content,
            "mode": self.mode,
            "sync_fingerprint": self.sync_fingerprint,
            "source_kind": self.source_kind,
            "session_id": self.session_id,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "target_continuity_object_id": (
                None if self.target_continuity_object_id is None else str(self.target_continuity_object_id)
            ),
        }


@dataclass(frozen=True, slots=True)
class MemoryOperationCommitInput:
    candidate_ids: list[UUID] = field(default_factory=list)
    sync_fingerprint: str | None = None
    include_review_required: bool = False

    def as_payload(self) -> JsonObject:
        return {
            "candidate_ids": [str(candidate_id) for candidate_id in self.candidate_ids],
            "sync_fingerprint": self.sync_fingerprint,
            "include_review_required": self.include_review_required,
        }


@dataclass(frozen=True, slots=True)
class MemoryOperationListInput:
    limit: int = DEFAULT_CONTINUITY_CAPTURE_LIMIT
    policy_action: MemoryOperationPolicyAction | None = None
    operation_type: MemoryOperationType | None = None
    sync_fingerprint: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
            "policy_action": self.policy_action,
            "operation_type": self.operation_type,
            "sync_fingerprint": self.sync_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ContinuityReviewQueueQueryInput:
    status: ContinuityReviewStatusFilter = "correction_ready"
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "status": self.status,
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ContinuityCorrectionInput:
    action: ContinuityCorrectionAction
    reason: str | None = None
    title: str | None = None
    body: JsonObject | None = None
    provenance: JsonObject | None = None
    confidence: float | None = None
    replacement_title: str | None = None
    replacement_body: JsonObject | None = None
    replacement_provenance: JsonObject | None = None
    replacement_confidence: float | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "action": self.action,
            "reason": self.reason,
            "title": self.title,
            "body": self.body,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "replacement_title": self.replacement_title,
            "replacement_body": self.replacement_body,
            "replacement_provenance": self.replacement_provenance,
            "replacement_confidence": self.replacement_confidence,
        }
        return payload


@dataclass(frozen=True, slots=True)
class ContradictionCaseListQueryInput:
    status: ContradictionStatus = "open"
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT
    continuity_object_id: UUID | None = None

    def as_payload(self) -> JsonObject:
        return {
            "status": self.status,
            "limit": self.limit,
            "continuity_object_id": (
                None if self.continuity_object_id is None else str(self.continuity_object_id)
            ),
        }


@dataclass(frozen=True, slots=True)
class ContradictionSyncInput:
    continuity_object_id: UUID | None = None
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "continuity_object_id": (
                None if self.continuity_object_id is None else str(self.continuity_object_id)
            ),
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ContradictionResolveInput:
    action: ContradictionResolutionAction
    note: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "action": self.action,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class TrustSignalListQueryInput:
    limit: int = DEFAULT_CONTINUITY_REVIEW_LIMIT
    continuity_object_id: UUID | None = None
    signal_state: TrustSignalState = "active"
    signal_type: TrustSignalType | None = None

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
            "continuity_object_id": (
                None if self.continuity_object_id is None else str(self.continuity_object_id)
            ),
            "signal_state": self.signal_state,
            "signal_type": self.signal_type,
        }


@dataclass(frozen=True, slots=True)
class ContinuityRecallQueryInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_RECALL_LIMIT
    debug: bool = False

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
            "debug": self.debug,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityResumptionBriefRequestInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    max_recent_changes: int = DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT
    max_open_loops: int = DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT
    include_non_promotable_facts: bool = False
    debug: bool = False

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "max_recent_changes": self.max_recent_changes,
            "max_open_loops": self.max_open_loops,
            "include_non_promotable_facts": self.include_non_promotable_facts,
            "debug": self.debug,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityBriefRequestInput:
    brief_type: ContinuityBriefType = "general"
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    max_relevant_facts: int = DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT
    max_recent_changes: int = DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT
    max_open_loops: int = DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT
    max_conflicts: int = DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT
    max_timeline_highlights: int = DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT
    include_non_promotable_facts: bool = False

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "brief_type": self.brief_type,
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "max_relevant_facts": self.max_relevant_facts,
            "max_recent_changes": self.max_recent_changes,
            "max_open_loops": self.max_open_loops,
            "max_conflicts": self.max_conflicts,
            "max_timeline_highlights": self.max_timeline_highlights,
            "include_non_promotable_facts": self.include_non_promotable_facts,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class TaskBriefCompileRequestInput:
    mode: TaskBriefMode
    query: str | None = None
    workspace_id: UUID | None = None
    pack_id: str | None = None
    pack_version: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    include_non_promotable_facts: bool = False
    provider_strategy: str | None = None
    model_pack_strategy: str | None = None
    token_budget: int | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "mode": self.mode,
            "query": self.query,
            "workspace_id": None if self.workspace_id is None else str(self.workspace_id),
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "include_non_promotable_facts": self.include_non_promotable_facts,
            "provider_strategy": self.provider_strategy,
            "model_pack_strategy": self.model_pack_strategy,
            "token_budget": self.token_budget,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class TaskBriefComparisonRequestInput:
    primary: TaskBriefCompileRequestInput
    secondary: TaskBriefCompileRequestInput

    def as_payload(self) -> JsonObject:
        return {
            "primary": self.primary.as_payload(),
            "secondary": self.secondary.as_payload(),
        }


@dataclass(frozen=True, slots=True)
class ContinuityLifecycleQueryInput:
    limit: int = DEFAULT_CONTINUITY_LIFECYCLE_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class ContinuityOpenLoopDashboardQueryInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityDailyBriefRequestInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ContinuityWeeklyReviewRequestInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CONTINUITY_WEEKLY_REVIEW_LIMIT

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ChiefOfStaffPriorityBriefRequestInput:
    query: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "query": self.query,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
            "limit": self.limit,
        }
        payload["since"] = isoformat_or_none(self.since)
        payload["until"] = isoformat_or_none(self.until)
        return payload


@dataclass(frozen=True, slots=True)
class ChiefOfStaffRecommendationOutcomeCaptureInput:
    outcome: ChiefOfStaffRecommendationOutcome
    recommendation_action_type: ChiefOfStaffRecommendedActionType
    recommendation_title: str
    rationale: str | None = None
    rewritten_title: str | None = None
    target_priority_id: UUID | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "outcome": self.outcome,
            "recommendation_action_type": self.recommendation_action_type,
            "recommendation_title": self.recommendation_title,
            "rationale": self.rationale,
            "rewritten_title": self.rewritten_title,
            "target_priority_id": None if self.target_priority_id is None else str(self.target_priority_id),
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
        }


@dataclass(frozen=True, slots=True)
class ChiefOfStaffHandoffReviewActionInput:
    handoff_item_id: str
    review_action: ChiefOfStaffHandoffReviewAction
    note: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "handoff_item_id": self.handoff_item_id,
            "review_action": self.review_action,
            "note": self.note,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
        }


@dataclass(frozen=True, slots=True)
class ChiefOfStaffExecutionRoutingActionInput:
    handoff_item_id: str
    route_target: ChiefOfStaffExecutionRouteTarget
    note: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "handoff_item_id": self.handoff_item_id,
            "route_target": self.route_target,
            "note": self.note,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
        }


@dataclass(frozen=True, slots=True)
class ChiefOfStaffHandoffOutcomeCaptureInput:
    handoff_item_id: str
    outcome_status: ChiefOfStaffHandoffOutcomeStatus
    note: str | None = None
    thread_id: UUID | None = None
    task_id: UUID | None = None
    project: str | None = None
    person: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "handoff_item_id": self.handoff_item_id,
            "outcome_status": self.outcome_status,
            "note": self.note,
            "thread_id": None if self.thread_id is None else str(self.thread_id),
            "task_id": None if self.task_id is None else str(self.task_id),
            "project": self.project,
            "person": self.person,
        }


@dataclass(frozen=True, slots=True)
class ContinuityOpenLoopReviewActionInput:
    action: ContinuityOpenLoopReviewAction
    note: str | None = None

    def as_payload(self) -> JsonObject:
        return {
            "action": self.action,
            "note": self.note,
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
class TemporalStateAtQueryInput:
    entity_id: UUID
    at: datetime | None = None

    def as_payload(self) -> JsonObject:
        return {
            "entity_id": str(self.entity_id),
            "at": isoformat_or_none(self.at),
        }


@dataclass(frozen=True, slots=True)
class TemporalTimelineQueryInput:
    entity_id: UUID
    since: datetime | None = None
    until: datetime | None = None
    limit: int = DEFAULT_TEMPORAL_TIMELINE_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "entity_id": str(self.entity_id),
            "since": isoformat_or_none(self.since),
            "until": isoformat_or_none(self.until),
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class TemporalExplainQueryInput:
    entity_id: UUID
    at: datetime | None = None

    def as_payload(self) -> JsonObject:
        return {
            "entity_id": str(self.entity_id),
            "at": isoformat_or_none(self.at),
        }


@dataclass(frozen=True, slots=True)
class TrustedFactPatternListQueryInput:
    limit: int = DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class TrustedFactPlaybookListQueryInput:
    limit: int = DEFAULT_TRUSTED_FACT_PROMOTION_LIMIT

    def as_payload(self) -> JsonObject:
        return {
            "limit": self.limit,
        }


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


class ContinuityCaptureEventRecord(TypedDict):
    id: str
    raw_content: str
    explicit_signal: ContinuityCaptureExplicitSignal | None
    admission_posture: ContinuityCaptureAdmissionPosture
    admission_reason: str
    created_at: str


class ContinuityCaptureCandidateRecord(TypedDict):
    candidate_id: str
    candidate_type: ContinuityCaptureCandidateType
    object_type: ContinuityObjectType | None
    normalized_text: str
    confidence: float
    trust_class: MemoryTrustClass
    evidence_snippet: str
    explicit: bool
    source_role: str
    admission_reason: str
    proposed_action: ContinuityCaptureProposedAction


class ContinuityCaptureCandidatesSummary(TypedDict):
    candidate_count: int
    explicit_count: int
    high_confidence_count: int
    no_op_count: int


class ContinuityCaptureCandidatesResponse(TypedDict):
    candidates: list[ContinuityCaptureCandidateRecord]
    summary: ContinuityCaptureCandidatesSummary


class ContinuityCaptureCommitRecord(TypedDict):
    candidate_id: str
    candidate_type: ContinuityCaptureCandidateType
    decision: ContinuityCaptureCommitDecision
    reason: str
    persistence_target: str
    capture_event: ContinuityCaptureEventRecord | None
    continuity_object: ContinuityObjectRecord | None


class ContinuityCaptureCommitSummary(TypedDict):
    mode: ContinuityCaptureCommitMode
    candidate_count: int
    auto_saved_count: int
    review_queued_count: int
    noop_count: int
    duplicate_noop_count: int
    auto_saved_types: list[str]
    review_queued_types: list[str]


class ContinuityCaptureCommitResponse(TypedDict):
    commits: list[ContinuityCaptureCommitRecord]
    summary: ContinuityCaptureCommitSummary


class MemoryOperationCandidateRecord(TypedDict):
    id: str
    sync_fingerprint: str
    source_kind: str
    source_candidate_id: str
    source_candidate_type: str
    candidate_payload: JsonObject
    source_scope: JsonObject
    operation_type: MemoryOperationType
    operation_reason: str
    policy_action: MemoryOperationPolicyAction
    policy_reason: str
    target_continuity_object_id: str | None
    target_snapshot: JsonObject
    applied_operation_id: str | None
    created_at: str
    applied_at: str | None


class MemoryOperationRecord(TypedDict):
    id: str
    candidate_id: str
    operation_type: MemoryOperationType
    status: MemoryOperationStatus
    sync_fingerprint: str
    target_continuity_object_id: str | None
    resulting_continuity_object_id: str | None
    correction_event_id: str | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    details: JsonObject
    created_at: str


class MemoryOperationCandidateGenerateSummary(TypedDict):
    candidate_count: int
    auto_apply_count: int
    review_required_count: int
    noop_count: int
    operation_types: list[str]


class MemoryOperationCandidateGenerateResponse(TypedDict):
    items: list[MemoryOperationCandidateRecord]
    summary: MemoryOperationCandidateGenerateSummary


class MemoryOperationCommitSummary(TypedDict):
    requested_count: int
    applied_count: int
    no_op_count: int
    skipped_count: int
    duplicate_count: int
    operation_types: list[str]


class MemoryOperationCommitResponse(TypedDict):
    candidates: list[MemoryOperationCandidateRecord]
    operations: list[MemoryOperationRecord]
    summary: MemoryOperationCommitSummary


class MemoryOperationListSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    policy_action: MemoryOperationPolicyAction | None
    operation_type: MemoryOperationType | None
    sync_fingerprint: str | None


class MemoryOperationCandidateListResponse(TypedDict):
    items: list[MemoryOperationCandidateRecord]
    summary: MemoryOperationListSummary


class MemoryOperationListResponse(TypedDict):
    items: list[MemoryOperationRecord]
    summary: MemoryOperationListSummary


class ContinuityLifecycleStateRecord(TypedDict):
    is_preserved: bool
    preservation_status: ContinuityPreservationStatus
    is_searchable: bool
    searchability_status: ContinuitySearchabilityStatus
    is_promotable: bool
    promotion_status: ContinuityPromotionStatus


class ContinuityObjectRecord(TypedDict):
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    lifecycle: ContinuityLifecycleStateRecord
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    created_at: str
    updated_at: str


class ContinuityReviewObjectRecord(TypedDict):
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    lifecycle: ContinuityLifecycleStateRecord
    title: str
    body: JsonObject
    provenance: JsonObject
    confidence: float
    last_confirmed_at: str | None
    supersedes_object_id: str | None
    superseded_by_object_id: str | None
    created_at: str
    updated_at: str
    explanation: NotRequired["ContinuityExplanationRecord"]


class ContinuityCorrectionEventRecord(TypedDict):
    id: str
    continuity_object_id: str
    action: ContinuityCorrectionAction
    reason: str | None
    before_snapshot: JsonObject
    after_snapshot: JsonObject
    payload: JsonObject
    created_at: str


class ContinuityCaptureInboxItem(TypedDict):
    capture_event: ContinuityCaptureEventRecord
    derived_object: ContinuityObjectRecord | None


class ContinuityCaptureInboxSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    derived_count: int
    triage_count: int
    order: list[str]


class ContinuityCaptureCreateResponse(TypedDict):
    capture: ContinuityCaptureInboxItem


class ContinuityCaptureInboxResponse(TypedDict):
    items: list[ContinuityCaptureInboxItem]
    summary: ContinuityCaptureInboxSummary


class ContinuityCaptureDetailResponse(TypedDict):
    capture: ContinuityCaptureInboxItem


class ContinuityReviewQueueSummary(TypedDict):
    status: ContinuityReviewStatusFilter
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityReviewQueueResponse(TypedDict):
    items: list[ContinuityReviewObjectRecord]
    summary: ContinuityReviewQueueSummary


class ContinuitySupersessionChain(TypedDict):
    supersedes: ContinuityReviewObjectRecord | None
    superseded_by: ContinuityReviewObjectRecord | None


class ContinuityReviewDetail(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    correction_events: list[ContinuityCorrectionEventRecord]
    supersession_chain: ContinuitySupersessionChain


class ContinuityReviewDetailResponse(TypedDict):
    review: ContinuityReviewDetail


class ContradictionCaseRecord(TypedDict):
    id: str
    canonical_key: str
    status: ContradictionStatus
    kind: ContradictionKind
    rationale: str
    detection_payload: JsonObject
    resolution_action: ContradictionResolutionAction | None
    resolution_note: str | None
    resolved_at: str | None
    continuity_object_updated_at: str
    counterpart_object_updated_at: str
    created_at: str
    updated_at: str
    continuity_object: ContinuityReviewObjectRecord
    counterpart_object: ContinuityReviewObjectRecord


class ContradictionCaseListSummary(TypedDict):
    status: ContradictionStatus
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContradictionCaseListResponse(TypedDict):
    items: list[ContradictionCaseRecord]
    summary: ContradictionCaseListSummary


class ContradictionCaseDetailResponse(TypedDict):
    contradiction_case: ContradictionCaseRecord


class ContradictionSyncSummary(TypedDict):
    continuity_object_id: str | None
    scanned_object_count: int
    open_case_count: int
    resolved_case_count: int
    updated_case_count: int


class ContradictionSyncResponse(TypedDict):
    items: list[ContradictionCaseRecord]
    summary: ContradictionSyncSummary


class ContradictionResolveResponse(TypedDict):
    contradiction_case: ContradictionCaseRecord


class TrustSignalRecord(TypedDict):
    id: str
    continuity_object_id: str
    signal_key: str
    signal_type: TrustSignalType
    signal_state: TrustSignalState
    direction: TrustSignalDirection
    magnitude: float
    reason: str
    contradiction_case_id: str | None
    related_continuity_object_id: str | None
    payload: JsonObject
    created_at: str
    updated_at: str


class TrustSignalListSummary(TypedDict):
    continuity_object_id: str | None
    signal_state: TrustSignalState
    signal_type: TrustSignalType | None
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class TrustSignalListResponse(TypedDict):
    items: list[TrustSignalRecord]
    summary: TrustSignalListSummary


class ContinuityEvidenceArtifactRecord(TypedDict):
    id: str
    source_kind: str
    import_source_path: str
    relative_path: str
    display_name: str
    media_type: str
    created_at: str


class ContinuityEvidenceArtifactCopyRecord(TypedDict):
    id: str
    checksum_sha256: str
    content_length_bytes: int
    content_encoding: str
    content_text: str
    created_at: str


class ContinuityEvidenceArtifactSegmentRecord(TypedDict):
    id: str
    source_item_id: str
    sequence_no: int
    segment_kind: str
    locator: JsonObject
    raw_content: str
    checksum_sha256: str
    created_at: str


class ContinuityEvidenceLinkRecord(TypedDict):
    id: str
    relationship: str
    created_at: str
    artifact: ContinuityEvidenceArtifactRecord
    artifact_copy: ContinuityEvidenceArtifactCopyRecord
    artifact_segment: ContinuityEvidenceArtifactSegmentRecord | None


class ContinuityExplanationSourceFactRecord(TypedDict):
    kind: str
    label: str
    value: str


class ContinuityExplanationEvidenceSegmentRecord(TypedDict):
    relationship: str
    source_kind: str
    source_id: str
    display_name: str
    relative_path: str | None
    segment_kind: str | None
    locator: JsonObject | None
    snippet: str
    created_at: str | None


class ContinuityExplanationSupersessionNoteRecord(TypedDict):
    kind: str
    note: str
    action: str | None
    related_object_id: str | None
    created_at: str | None


class ContinuityExplanationContradictionRecord(TypedDict):
    open_case_count: int
    resolved_case_count: int
    open_case_ids: list[str]
    kinds: list[ContradictionKind]
    counterpart_object_ids: list[str]
    penalty_score: float


class ContinuityExplanationTrustRecord(TypedDict):
    trust_class: MemoryTrustClass
    trust_reason: str
    confirmation_status: MemoryConfirmationStatus
    confidence: float
    provenance_posture: ContinuityRecallProvenancePosture
    evidence_segment_count: int
    correction_count: int
    active_signal_count: int


class ContinuityExplanationTimestampsRecord(TypedDict):
    capture_created_at: str | None
    created_at: str
    updated_at: str
    last_confirmed_at: str | None


class ContinuityExplanationRecord(TypedDict):
    source_facts: list[ContinuityExplanationSourceFactRecord]
    trust: ContinuityExplanationTrustRecord
    contradictions: ContinuityExplanationContradictionRecord
    evidence_segments: list[ContinuityExplanationEvidenceSegmentRecord]
    supersession_notes: list[ContinuityExplanationSupersessionNoteRecord]
    timestamps: ContinuityExplanationTimestampsRecord
    proposal_rationale: NotRequired[str]


class ContinuityExplainRecord(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    explanation: ContinuityExplanationRecord
    evidence_chain: list[ContinuityEvidenceLinkRecord]


class ContinuityExplainResponse(TypedDict):
    explain: ContinuityExplainRecord


class ContinuityArtifactDetailRecord(TypedDict):
    artifact: ContinuityEvidenceArtifactRecord
    copies: list[ContinuityEvidenceArtifactCopyRecord]
    segments: list[ContinuityEvidenceArtifactSegmentRecord]


class ContinuityArtifactDetailResponse(TypedDict):
    artifact_detail: ContinuityArtifactDetailRecord


class ContinuityRecallScopeFilters(TypedDict):
    thread_id: NotRequired[str]
    task_id: NotRequired[str]
    project: NotRequired[str]
    person: NotRequired[str]
    since: str | None
    until: str | None


class ContinuityRecallScopeMatch(TypedDict):
    kind: ContinuityRecallScopeKind
    value: str


class ContinuityRecallProvenanceReference(TypedDict):
    source_kind: str
    source_id: str


class ContinuityRecallOrderingMetadata(TypedDict):
    scope_match_count: int
    query_term_match_count: int
    semantic_similarity_score: float
    exact_match_score: float
    recency_score: float
    temporal_overlap_score: float
    entity_match_count: int
    confirmation_rank: int
    trust_class: MemoryTrustClass
    trust_rank: int
    freshness_posture: ContinuityRecallFreshnessPosture
    freshness_rank: int
    provenance_posture: ContinuityRecallProvenancePosture
    provenance_rank: int
    supersession_posture: ContinuityRecallSupersessionPosture
    supersession_rank: int
    supersession_freshness_score: float
    posture_rank: int
    lifecycle_rank: int
    open_contradiction_count: int
    contradiction_penalty_score: float
    confidence: float


class ContinuityRetrievalStageScoreRecord(TypedDict):
    raw_score: float
    normalized_score: float
    matched: bool
    reason: str


class ContinuityRetrievalDebugCandidateRecord(TypedDict):
    object_id: str
    title: str
    object_type: ContinuityObjectType
    status: str
    selected: bool
    rank: int | None
    exclusion_reason: str | None
    scope_matches: list[ContinuityRecallScopeMatch]
    ordering: ContinuityRecallOrderingMetadata
    stage_scores: dict[str, ContinuityRetrievalStageScoreRecord]
    relevance: float


class ContinuityRetrievalDebugRecord(TypedDict):
    retrieval_run_id: str | None
    source_surface: str
    ranking_strategy: str
    query_terms: list[str]
    entity_anchor_names: list[str]
    entity_expansion_names: list[str]
    candidate_count: int
    selected_count: int
    candidates: list[ContinuityRetrievalDebugCandidateRecord]


class ContinuityRecallResultRecord(TypedDict):
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    lifecycle: ContinuityLifecycleStateRecord
    title: str
    body: JsonObject
    provenance: JsonObject
    confirmation_status: MemoryConfirmationStatus
    admission_posture: ContinuityCaptureAdmissionPosture
    confidence: float
    relevance: float
    last_confirmed_at: str | None
    supersedes_object_id: str | None
    superseded_by_object_id: str | None
    scope_matches: list[ContinuityRecallScopeMatch]
    provenance_references: list[ContinuityRecallProvenanceReference]
    ordering: ContinuityRecallOrderingMetadata
    explanation: ContinuityExplanationRecord
    created_at: str
    updated_at: str


class ContinuityRecallSummary(TypedDict):
    query: str | None
    filters: ContinuityRecallScopeFilters
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityRecallResponse(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ContinuityRecallSummary
    debug: NotRequired[ContinuityRetrievalDebugRecord]


class ContinuityLifecycleCounts(TypedDict):
    preserved_count: int
    searchable_count: int
    promotable_count: int
    not_searchable_count: int
    not_promotable_count: int


class ContinuityLifecycleListSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    counts: ContinuityLifecycleCounts
    order: list[str]


class ContinuityLifecycleListResponse(TypedDict):
    items: list[ContinuityReviewObjectRecord]
    summary: ContinuityLifecycleListSummary


class ContinuityLifecycleDetailResponse(TypedDict):
    continuity_object: ContinuityReviewObjectRecord


class ContinuityResumptionEmptyState(TypedDict):
    is_empty: bool
    message: str


class ContinuityResumptionSingleSection(TypedDict):
    item: ContinuityRecallResultRecord | None
    empty_state: ContinuityResumptionEmptyState


class ContinuityResumptionListSection(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ResumptionBriefSectionSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityResumptionBriefRecord(TypedDict):
    assembly_version: str
    scope: ContinuityRecallScopeFilters
    last_decision: ContinuityResumptionSingleSection
    open_loops: ContinuityResumptionListSection
    recent_changes: ContinuityResumptionListSection
    next_action: ContinuityResumptionSingleSection
    sources: list[str]


class ContinuityResumptionDebugRecord(TypedDict):
    retrieval: ContinuityRetrievalDebugRecord


class ContinuityResumptionBriefResponse(TypedDict):
    brief: ContinuityResumptionBriefRecord
    debug: NotRequired[ContinuityResumptionDebugRecord]


class ContinuityBriefRelevantFactsSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]
    task_brief_mode: TaskBriefMode


class ContinuityBriefRelevantFactsSection(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ContinuityBriefRelevantFactsSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityBriefConflictSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityBriefConflictSection(TypedDict):
    items: list[ContradictionCaseRecord]
    summary: ContinuityBriefConflictSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityBriefTimelineHighlightRecord(TypedDict):
    continuity_object_id: str
    title: str
    object_type: ContinuityObjectType
    status: str
    created_at: str
    source_section: str


class ContinuityBriefTimelineSection(TypedDict):
    items: list[ContinuityBriefTimelineHighlightRecord]
    summary: ResumptionBriefSectionSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityBriefSuggestedActionRecord(TypedDict):
    continuity_object_id: str | None
    title: str
    object_type: ContinuityObjectType | None
    reason: str
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    provenance_references: list[ContinuityRecallProvenanceReference]


class ContinuityBriefSelectionStrategyRecord(TypedDict):
    task_brief_mode: TaskBriefMode
    provider_strategy: str
    model_pack_strategy: str
    token_budget: int
    budget_source: str


class ContinuityBriefProvenanceSummary(TypedDict):
    source_object_count: int
    reference_count: int
    reference_kind_count: int


class ContinuityBriefProvenanceBundle(TypedDict):
    source_object_ids: list[str]
    references: list[ContinuityRecallProvenanceReference]
    summary: ContinuityBriefProvenanceSummary


class ContinuityBriefTrustPostureRecord(TypedDict):
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    average_confidence: float
    strongest_trust_class: MemoryTrustClass | None
    weakest_provenance_posture: ContinuityRecallProvenancePosture | None
    active_signal_count: int
    positive_signal_count: int
    negative_signal_count: int
    neutral_signal_count: int
    open_conflict_count: int
    rationale: str


class ContinuityBriefRecord(TypedDict):
    assembly_version: str
    brief_type: ContinuityBriefType
    scope: ContinuityRecallScopeFilters
    summary: str
    selection_strategy: ContinuityBriefSelectionStrategyRecord
    relevant_facts: ContinuityBriefRelevantFactsSection
    recent_changes: ContinuityResumptionListSection
    open_loops: ContinuityResumptionListSection
    conflicts: ContinuityBriefConflictSection
    timeline_highlights: ContinuityBriefTimelineSection
    next_suggested_action: ContinuityBriefSuggestedActionRecord
    provenance_bundle: ContinuityBriefProvenanceBundle
    trust_posture: ContinuityBriefTrustPostureRecord
    sources: list[str]


class ContinuityBriefResponse(TypedDict):
    brief: ContinuityBriefRecord


class TaskBriefEmptyState(TypedDict):
    is_empty: bool
    message: str


class TaskBriefSectionSummary(TypedDict):
    candidate_count: int
    selected_count: int
    truncated_count: int
    token_budget: int
    estimated_tokens: int
    order: list[str]


class TaskBriefSectionRecord(TypedDict):
    section_key: str
    title: str
    intent: str
    selection_rule: str
    items: list[ContinuityRecallResultRecord]
    summary: TaskBriefSectionSummary
    empty_state: TaskBriefEmptyState


class TaskBriefStrategyRecord(TypedDict):
    provider_strategy: str
    model_pack_strategy: str
    token_budget: int
    budget_source: str


class TaskBriefSummary(TypedDict):
    candidate_count: int
    selected_item_count: int
    estimated_tokens: int
    token_budget: int
    truncated: bool
    deterministic_key: str
    section_order: list[str]
    mode_order: list[str]


class TaskBriefRecord(TypedDict):
    assembly_version: str
    mode: TaskBriefMode
    scope: ContinuityRecallScopeFilters
    strategy: TaskBriefStrategyRecord
    summary: TaskBriefSummary
    sections: list[TaskBriefSectionRecord]
    sources: list[str]


class TaskBriefPersistenceRecord(TypedDict):
    task_brief_id: str
    created_at: str


class TaskBriefResponse(TypedDict):
    task_brief: TaskBriefRecord
    persistence: TaskBriefPersistenceRecord


class TaskBriefComparisonStats(TypedDict):
    primary_mode: TaskBriefMode
    secondary_mode: TaskBriefMode
    smaller_mode: TaskBriefMode | None
    estimated_token_delta: int
    selected_item_delta: int
    shared_item_ids: list[str]
    primary_is_smaller: bool


class TaskBriefComparisonResponse(TypedDict):
    comparison_version: str
    primary: TaskBriefRecord
    secondary: TaskBriefRecord
    comparison: TaskBriefComparisonStats


class RetrievalRunRecord(TypedDict):
    id: str
    source_surface: str
    ranking_strategy: str
    query_text: str | None
    request_scope: JsonObject
    result_ids: list[str]
    exclusion_summary: JsonObject
    candidate_count: int
    selected_count: int
    debug_enabled: bool
    retention_until: str
    created_at: str


class RetrievalRunListSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class RetrievalRunListResponse(TypedDict):
    items: list[RetrievalRunRecord]
    summary: RetrievalRunListSummary


class RetrievalTraceSummary(TypedDict):
    candidate_count: int
    selected_count: int
    order: list[str]


class RetrievalTraceResponse(TypedDict):
    retrieval_run: RetrievalRunRecord
    candidates: list[ContinuityRetrievalDebugCandidateRecord]
    summary: RetrievalTraceSummary


class ContinuityOpenLoopSectionSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ContinuityOpenLoopSection(TypedDict):
    items: list[ContinuityRecallResultRecord]
    summary: ContinuityOpenLoopSectionSummary
    empty_state: ContinuityResumptionEmptyState


class ContinuityOpenLoopDashboardSummary(TypedDict):
    limit: int
    total_count: int
    posture_order: list[ContinuityOpenLoopPosture]
    item_order: list[str]


class ContinuityOpenLoopDashboardRecord(TypedDict):
    scope: ContinuityRecallScopeFilters
    waiting_for: ContinuityOpenLoopSection
    blocker: ContinuityOpenLoopSection
    stale: ContinuityOpenLoopSection
    next_action: ContinuityOpenLoopSection
    summary: ContinuityOpenLoopDashboardSummary
    sources: list[str]


class ContinuityOpenLoopDashboardResponse(TypedDict):
    dashboard: ContinuityOpenLoopDashboardRecord


class ContinuityDailyBriefRecord(TypedDict):
    assembly_version: str
    scope: ContinuityRecallScopeFilters
    waiting_for_highlights: ContinuityOpenLoopSection
    blocker_highlights: ContinuityOpenLoopSection
    stale_items: ContinuityOpenLoopSection
    next_suggested_action: ContinuityResumptionSingleSection
    sources: list[str]


class ContinuityDailyBriefResponse(TypedDict):
    brief: ContinuityDailyBriefRecord


class ContinuityWeeklyReviewRollup(TypedDict):
    total_count: int
    waiting_for_count: int
    blocker_count: int
    stale_count: int
    correction_recurrence_count: int
    freshness_drift_count: int
    next_action_count: int
    posture_order: list[ContinuityOpenLoopPosture]


class ContinuityWeeklyReviewRecord(TypedDict):
    assembly_version: str
    scope: ContinuityRecallScopeFilters
    rollup: ContinuityWeeklyReviewRollup
    waiting_for: ContinuityOpenLoopSection
    blocker: ContinuityOpenLoopSection
    stale: ContinuityOpenLoopSection
    next_action: ContinuityOpenLoopSection
    sources: list[str]


class ContinuityWeeklyReviewResponse(TypedDict):
    review: ContinuityWeeklyReviewRecord


class ChiefOfStaffPriorityRankingInputs(TypedDict):
    posture: ChiefOfStaffPriorityPosture
    open_loop_posture: ContinuityOpenLoopPosture | None
    recency_rank: int | None
    age_hours_relative_to_latest: float
    recall_relevance: float
    scope_match_count: int
    query_term_match_count: int
    freshness_posture: ContinuityRecallFreshnessPosture
    provenance_posture: ContinuityRecallProvenancePosture
    supersession_posture: ContinuityRecallSupersessionPosture


class ChiefOfStaffPriorityTrustSignals(TypedDict):
    quality_gate_status: MemoryQualityGateStatus
    retrieval_status: RetrievalEvaluationStatus
    trust_confidence_cap: ChiefOfStaffRecommendationConfidencePosture
    downgraded_by_trust: bool
    reason: str


class ChiefOfStaffPriorityRationale(TypedDict):
    reasons: list[str]
    ranking_inputs: ChiefOfStaffPriorityRankingInputs
    provenance_references: list[ContinuityRecallProvenanceReference]
    trust_signals: ChiefOfStaffPriorityTrustSignals


class ChiefOfStaffPriorityItem(TypedDict):
    rank: int
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    title: str
    priority_posture: ChiefOfStaffPriorityPosture
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    confidence: float
    score: float
    provenance: JsonObject
    created_at: str
    updated_at: str
    rationale: ChiefOfStaffPriorityRationale


class ChiefOfStaffFollowThroughItem(TypedDict):
    rank: int
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    title: str
    current_priority_posture: ChiefOfStaffPriorityPosture
    follow_through_posture: ChiefOfStaffFollowThroughPosture
    recommendation_action: ChiefOfStaffFollowThroughRecommendationAction
    reason: str
    age_hours: float
    provenance_references: list[ContinuityRecallProvenanceReference]
    created_at: str
    updated_at: str


class ChiefOfStaffEscalationPostureRecord(TypedDict):
    posture: ChiefOfStaffEscalationPosture
    reason: str
    total_follow_through_count: int
    nudge_count: int
    defer_count: int
    escalate_count: int
    close_loop_candidate_count: int


class ChiefOfStaffDraftFollowUpTargetMetadata(TypedDict):
    continuity_object_id: str | None
    capture_event_id: str | None
    object_type: ContinuityObjectType | None
    priority_posture: ChiefOfStaffPriorityPosture | None
    follow_through_posture: ChiefOfStaffFollowThroughPosture | None
    recommendation_action: ChiefOfStaffFollowThroughRecommendationAction | None
    thread_id: str | None


class ChiefOfStaffDraftFollowUpContent(TypedDict):
    subject: str
    body: str


class ChiefOfStaffDraftFollowUpRecord(TypedDict):
    status: Literal["drafted", "none"]
    mode: Literal["draft_only"]
    approval_required: bool
    auto_send: bool
    reason: str
    target_metadata: ChiefOfStaffDraftFollowUpTargetMetadata
    content: ChiefOfStaffDraftFollowUpContent


class ChiefOfStaffRecommendedNextAction(TypedDict):
    action_type: ChiefOfStaffRecommendedActionType
    title: str
    target_priority_id: str | None
    priority_posture: ChiefOfStaffPriorityPosture | None
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    reason: str
    provenance_references: list[ContinuityRecallProvenanceReference]
    deterministic_rank_key: str


class ChiefOfStaffActionHandoffRequestTarget(TypedDict):
    thread_id: str | None
    task_id: str | None
    project: str | None
    person: str | None


class ChiefOfStaffActionHandoffRequestDraft(TypedDict):
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    attributes: JsonObject


class ChiefOfStaffActionHandoffTaskDraftRecord(TypedDict):
    status: Literal["draft"]
    mode: Literal["governed_request_draft"]
    approval_required: bool
    auto_execute: bool
    source_handoff_item_id: str
    title: str
    summary: str
    target: ChiefOfStaffActionHandoffRequestTarget
    request: ChiefOfStaffActionHandoffRequestDraft
    rationale: str
    provenance_references: list[ContinuityRecallProvenanceReference]


class ChiefOfStaffActionHandoffApprovalDraftRecord(TypedDict):
    status: Literal["draft_only"]
    mode: Literal["approval_request_draft"]
    decision: ToolRoutingDecision
    approval_required: bool
    auto_submit: bool
    source_handoff_item_id: str
    request: ChiefOfStaffActionHandoffRequestDraft
    reason: str
    required_checks: list[str]
    provenance_references: list[ContinuityRecallProvenanceReference]


class ChiefOfStaffActionHandoffItem(TypedDict):
    rank: int
    handoff_item_id: str
    source_kind: ChiefOfStaffActionHandoffSourceKind
    source_reference_id: str | None
    title: str
    recommendation_action: ChiefOfStaffActionHandoffAction
    priority_posture: ChiefOfStaffPriorityPosture | None
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    rationale: str
    provenance_references: list[ContinuityRecallProvenanceReference]
    score: float
    task_draft: ChiefOfStaffActionHandoffTaskDraftRecord
    approval_draft: ChiefOfStaffActionHandoffApprovalDraftRecord


class ChiefOfStaffActionHandoffBriefRecord(TypedDict):
    summary: str
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    non_autonomous_guarantee: str
    order: list[str]
    source_order: list[ChiefOfStaffActionHandoffSourceKind]
    provenance_references: list[ContinuityRecallProvenanceReference]


class ChiefOfStaffExecutionPostureRecord(TypedDict):
    posture: ChiefOfStaffExecutionPosture
    approval_required: bool
    autonomous_execution: bool
    external_side_effects_allowed: bool
    default_routing_decision: ToolRoutingDecision
    required_operator_actions: list[str]
    non_autonomous_guarantee: str
    reason: str


class ChiefOfStaffExecutionReadinessPostureRecord(TypedDict):
    posture: ChiefOfStaffExecutionReadinessPosture
    approval_required: bool
    autonomous_execution: bool
    external_side_effects_allowed: bool
    approval_path_visible: bool
    route_target_order: list[ChiefOfStaffExecutionRouteTarget]
    required_route_targets: list[ChiefOfStaffExecutionRouteTarget]
    transition_order: list[ChiefOfStaffExecutionRoutingTransition]
    non_autonomous_guarantee: str
    reason: str


class ChiefOfStaffExecutionRoutingAuditRecord(TypedDict):
    id: str
    capture_event_id: str
    handoff_item_id: str
    route_target: ChiefOfStaffExecutionRouteTarget
    transition: ChiefOfStaffExecutionRoutingTransition
    previously_routed: bool
    route_state: bool
    reason: str
    note: str | None
    provenance_references: list[ContinuityRecallProvenanceReference]
    created_at: str
    updated_at: str


class ChiefOfStaffRoutedHandoffItemRecord(TypedDict):
    handoff_rank: int
    handoff_item_id: str
    title: str
    source_kind: ChiefOfStaffActionHandoffSourceKind
    recommendation_action: ChiefOfStaffActionHandoffAction
    route_target_order: list[ChiefOfStaffExecutionRouteTarget]
    available_route_targets: list[ChiefOfStaffExecutionRouteTarget]
    routed_targets: list[ChiefOfStaffExecutionRouteTarget]
    is_routed: bool
    task_workflow_draft_routed: bool
    approval_workflow_draft_routed: bool
    follow_up_draft_only_routed: bool
    follow_up_draft_only_applicable: bool
    task_draft: ChiefOfStaffActionHandoffTaskDraftRecord
    approval_draft: ChiefOfStaffActionHandoffApprovalDraftRecord
    follow_up_draft: NotRequired[ChiefOfStaffDraftFollowUpRecord]
    last_routing_transition: ChiefOfStaffExecutionRoutingAuditRecord | None


class ChiefOfStaffExecutionRoutingSummary(TypedDict):
    total_handoff_count: int
    routed_handoff_count: int
    unrouted_handoff_count: int
    task_workflow_draft_count: int
    approval_workflow_draft_count: int
    follow_up_draft_only_count: int
    route_target_order: list[ChiefOfStaffExecutionRouteTarget]
    routed_item_order: list[str]
    audit_order: list[str]
    transition_order: list[ChiefOfStaffExecutionRoutingTransition]
    approval_required: bool
    non_autonomous_guarantee: str
    reason: str


class ChiefOfStaffHandoffReviewActionRecord(TypedDict):
    id: str
    capture_event_id: str
    handoff_item_id: str
    review_action: ChiefOfStaffHandoffReviewAction
    previous_lifecycle_state: ChiefOfStaffHandoffQueueLifecycleState | None
    next_lifecycle_state: ChiefOfStaffHandoffQueueLifecycleState
    reason: str
    note: str | None
    provenance_references: list[ContinuityRecallProvenanceReference]
    created_at: str
    updated_at: str


class ChiefOfStaffHandoffOutcomeRecord(TypedDict):
    id: str
    capture_event_id: str
    handoff_item_id: str
    outcome_status: ChiefOfStaffHandoffOutcomeStatus
    previous_outcome_status: ChiefOfStaffHandoffOutcomeStatus | None
    is_latest_outcome: bool
    reason: str
    note: str | None
    provenance_references: list[ContinuityRecallProvenanceReference]
    created_at: str
    updated_at: str


class ChiefOfStaffHandoffOutcomeSummary(TypedDict):
    returned_count: int
    total_count: int
    latest_total_count: int
    status_counts: dict[ChiefOfStaffHandoffOutcomeStatus, int]
    latest_status_counts: dict[ChiefOfStaffHandoffOutcomeStatus, int]
    status_order: list[ChiefOfStaffHandoffOutcomeStatus]
    order: list[str]


class ChiefOfStaffClosureQualitySummaryRecord(TypedDict):
    posture: ChiefOfStaffClosureQualityPosture
    reason: str
    closed_loop_count: int
    unresolved_count: int
    rejected_count: int
    ignored_count: int
    expired_count: int
    closure_rate: float
    explanation: str


class ChiefOfStaffConversionSignalSummaryRecord(TypedDict):
    total_handoff_count: int
    latest_outcome_count: int
    executed_count: int
    approved_count: int
    reviewed_count: int
    rewritten_count: int
    rejected_count: int
    ignored_count: int
    expired_count: int
    recommendation_to_execution_conversion_rate: float
    recommendation_to_closure_conversion_rate: float
    capture_coverage_rate: float
    explanation: str


class ChiefOfStaffStaleIgnoredEscalationPostureRecord(TypedDict):
    posture: ChiefOfStaffEscalationPosture
    reason: str
    stale_queue_count: int
    ignored_count: int
    expired_count: int
    trigger_count: int
    guidance_posture_explanation: str
    supporting_signals: list[str]


class ChiefOfStaffHandoffQueueItem(TypedDict):
    queue_rank: int
    handoff_rank: int
    handoff_item_id: str
    lifecycle_state: ChiefOfStaffHandoffQueueLifecycleState
    state_reason: str
    source_kind: ChiefOfStaffActionHandoffSourceKind
    source_reference_id: str | None
    title: str
    recommendation_action: ChiefOfStaffActionHandoffAction
    priority_posture: ChiefOfStaffPriorityPosture | None
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    score: float
    age_hours_relative_to_latest: float | None
    review_action_order: list[ChiefOfStaffHandoffReviewAction]
    available_review_actions: list[ChiefOfStaffHandoffReviewAction]
    last_review_action: ChiefOfStaffHandoffReviewActionRecord | None
    provenance_references: list[ContinuityRecallProvenanceReference]


class ChiefOfStaffHandoffQueueGroupSummary(TypedDict):
    lifecycle_state: ChiefOfStaffHandoffQueueLifecycleState
    returned_count: int
    total_count: int
    order: list[str]


class ChiefOfStaffHandoffQueueGroupEmptyState(TypedDict):
    is_empty: bool
    message: str


class ChiefOfStaffHandoffQueueGroup(TypedDict):
    items: list[ChiefOfStaffHandoffQueueItem]
    summary: ChiefOfStaffHandoffQueueGroupSummary
    empty_state: ChiefOfStaffHandoffQueueGroupEmptyState


class ChiefOfStaffHandoffQueueGroups(TypedDict):
    ready: ChiefOfStaffHandoffQueueGroup
    pending_approval: ChiefOfStaffHandoffQueueGroup
    executed: ChiefOfStaffHandoffQueueGroup
    stale: ChiefOfStaffHandoffQueueGroup
    expired: ChiefOfStaffHandoffQueueGroup


class ChiefOfStaffHandoffQueueSummary(TypedDict):
    total_count: int
    ready_count: int
    pending_approval_count: int
    executed_count: int
    stale_count: int
    expired_count: int
    state_order: list[ChiefOfStaffHandoffQueueLifecycleState]
    group_order: list[ChiefOfStaffHandoffQueueLifecycleState]
    item_order: list[str]
    review_action_order: list[ChiefOfStaffHandoffReviewAction]


class ChiefOfStaffPrioritySummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    posture_order: list[ChiefOfStaffPriorityPosture]
    order: list[str]
    follow_through_posture_order: list[ChiefOfStaffFollowThroughPosture]
    follow_through_item_order: list[str]
    follow_through_total_count: int
    overdue_count: int
    stale_waiting_for_count: int
    slipped_commitment_count: int
    trust_confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    trust_confidence_reason: str
    quality_gate_status: MemoryQualityGateStatus
    retrieval_status: RetrievalEvaluationStatus
    handoff_item_count: int
    handoff_item_order: list[str]
    execution_posture_order: list[ChiefOfStaffExecutionPosture]
    handoff_queue_total_count: int
    handoff_queue_ready_count: int
    handoff_queue_pending_approval_count: int
    handoff_queue_executed_count: int
    handoff_queue_stale_count: int
    handoff_queue_expired_count: int
    handoff_queue_state_order: list[ChiefOfStaffHandoffQueueLifecycleState]
    handoff_queue_group_order: list[ChiefOfStaffHandoffQueueLifecycleState]
    handoff_queue_item_order: list[str]
    handoff_outcome_total_count: int
    handoff_outcome_latest_count: int
    handoff_outcome_executed_count: int
    handoff_outcome_ignored_count: int
    closure_quality_posture: ChiefOfStaffClosureQualityPosture
    stale_ignored_escalation_posture: ChiefOfStaffEscalationPosture


class ChiefOfStaffPreparationArtifactItem(TypedDict):
    rank: int
    id: str
    capture_event_id: str
    object_type: ContinuityObjectType
    status: str
    title: str
    reason: str
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    provenance_references: list[ContinuityRecallProvenanceReference]
    created_at: str


class ChiefOfStaffPreparationSectionSummary(TypedDict):
    limit: int
    returned_count: int
    total_count: int
    order: list[str]


class ChiefOfStaffPreparationBriefRecord(TypedDict):
    scope: ContinuityRecallScopeFilters
    context_items: list[ChiefOfStaffPreparationArtifactItem]
    last_decision: ChiefOfStaffPreparationArtifactItem | None
    open_loops: list[ChiefOfStaffPreparationArtifactItem]
    next_action: ChiefOfStaffPreparationArtifactItem | None
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    confidence_reason: str
    summary: ChiefOfStaffPreparationSectionSummary


class ChiefOfStaffWhatChangedSummaryRecord(TypedDict):
    items: list[ChiefOfStaffPreparationArtifactItem]
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    confidence_reason: str
    summary: ChiefOfStaffPreparationSectionSummary


class ChiefOfStaffPrepChecklistRecord(TypedDict):
    items: list[ChiefOfStaffPreparationArtifactItem]
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    confidence_reason: str
    summary: ChiefOfStaffPreparationSectionSummary


class ChiefOfStaffSuggestedTalkingPointsRecord(TypedDict):
    items: list[ChiefOfStaffPreparationArtifactItem]
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    confidence_reason: str
    summary: ChiefOfStaffPreparationSectionSummary


class ChiefOfStaffResumptionSupervisionRecommendation(TypedDict):
    rank: int
    action: ChiefOfStaffResumptionRecommendationAction
    title: str
    reason: str
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    target_priority_id: str | None
    provenance_references: list[ContinuityRecallProvenanceReference]


class ChiefOfStaffResumptionSupervisionRecord(TypedDict):
    recommendations: list[ChiefOfStaffResumptionSupervisionRecommendation]
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    confidence_reason: str
    summary: ChiefOfStaffPreparationSectionSummary


class ChiefOfStaffWeeklyReviewGuidanceItem(TypedDict):
    rank: int
    action: ChiefOfStaffWeeklyReviewGuidanceAction
    signal_count: int
    rationale: str


class ChiefOfStaffWeeklyReviewBriefSummary(TypedDict):
    guidance_order: list[ChiefOfStaffWeeklyReviewGuidanceAction]
    guidance_item_order: list[str]


class ChiefOfStaffWeeklyReviewBriefRecord(TypedDict):
    scope: ContinuityRecallScopeFilters
    rollup: ContinuityWeeklyReviewRollup
    guidance: list[ChiefOfStaffWeeklyReviewGuidanceItem]
    summary: ChiefOfStaffWeeklyReviewBriefSummary


class ChiefOfStaffRecommendationOutcomeRecord(TypedDict):
    id: str
    capture_event_id: str
    outcome: ChiefOfStaffRecommendationOutcome
    recommendation_action_type: ChiefOfStaffRecommendedActionType
    recommendation_title: str
    rewritten_title: str | None
    target_priority_id: str | None
    rationale: str | None
    provenance_references: list[ContinuityRecallProvenanceReference]
    created_at: str
    updated_at: str


class ChiefOfStaffRecommendationOutcomeSummary(TypedDict):
    returned_count: int
    total_count: int
    outcome_counts: dict[ChiefOfStaffRecommendationOutcome, int]
    order: list[str]


class ChiefOfStaffRecommendationOutcomeSection(TypedDict):
    items: list[ChiefOfStaffRecommendationOutcomeRecord]
    summary: ChiefOfStaffRecommendationOutcomeSummary


class ChiefOfStaffOutcomeHotspotRecord(TypedDict):
    key: str
    count: int


class ChiefOfStaffPriorityLearningSummaryRecord(TypedDict):
    total_count: int
    accept_count: int
    defer_count: int
    ignore_count: int
    rewrite_count: int
    acceptance_rate: float
    override_rate: float
    defer_hotspots: list[ChiefOfStaffOutcomeHotspotRecord]
    ignore_hotspots: list[ChiefOfStaffOutcomeHotspotRecord]
    priority_shift_explanation: str
    hotspot_order: list[str]


class ChiefOfStaffPatternDriftSummaryRecord(TypedDict):
    posture: ChiefOfStaffPatternDriftPosture
    reason: str
    supporting_signals: list[str]


class ChiefOfStaffPriorityBriefRecord(TypedDict):
    assembly_version: str
    scope: ContinuityRecallScopeFilters
    ranked_items: list[ChiefOfStaffPriorityItem]
    overdue_items: list[ChiefOfStaffFollowThroughItem]
    stale_waiting_for_items: list[ChiefOfStaffFollowThroughItem]
    slipped_commitments: list[ChiefOfStaffFollowThroughItem]
    escalation_posture: ChiefOfStaffEscalationPostureRecord
    draft_follow_up: ChiefOfStaffDraftFollowUpRecord
    recommended_next_action: ChiefOfStaffRecommendedNextAction
    preparation_brief: ChiefOfStaffPreparationBriefRecord
    what_changed_summary: ChiefOfStaffWhatChangedSummaryRecord
    prep_checklist: ChiefOfStaffPrepChecklistRecord
    suggested_talking_points: ChiefOfStaffSuggestedTalkingPointsRecord
    resumption_supervision: ChiefOfStaffResumptionSupervisionRecord
    weekly_review_brief: ChiefOfStaffWeeklyReviewBriefRecord
    recommendation_outcomes: ChiefOfStaffRecommendationOutcomeSection
    priority_learning_summary: ChiefOfStaffPriorityLearningSummaryRecord
    pattern_drift_summary: ChiefOfStaffPatternDriftSummaryRecord
    action_handoff_brief: ChiefOfStaffActionHandoffBriefRecord
    handoff_items: list[ChiefOfStaffActionHandoffItem]
    handoff_queue_summary: ChiefOfStaffHandoffQueueSummary
    handoff_queue_groups: ChiefOfStaffHandoffQueueGroups
    handoff_review_actions: list[ChiefOfStaffHandoffReviewActionRecord]
    handoff_outcome_summary: ChiefOfStaffHandoffOutcomeSummary
    handoff_outcomes: list[ChiefOfStaffHandoffOutcomeRecord]
    closure_quality_summary: ChiefOfStaffClosureQualitySummaryRecord
    conversion_signal_summary: ChiefOfStaffConversionSignalSummaryRecord
    stale_ignored_escalation_posture: ChiefOfStaffStaleIgnoredEscalationPostureRecord
    execution_routing_summary: ChiefOfStaffExecutionRoutingSummary
    routed_handoff_items: list[ChiefOfStaffRoutedHandoffItemRecord]
    routing_audit_trail: list[ChiefOfStaffExecutionRoutingAuditRecord]
    execution_readiness_posture: ChiefOfStaffExecutionReadinessPostureRecord
    task_draft: ChiefOfStaffActionHandoffTaskDraftRecord
    approval_draft: ChiefOfStaffActionHandoffApprovalDraftRecord
    execution_posture: ChiefOfStaffExecutionPostureRecord
    summary: ChiefOfStaffPrioritySummary
    sources: list[str]


class ChiefOfStaffPriorityBriefResponse(TypedDict):
    brief: ChiefOfStaffPriorityBriefRecord


class ChiefOfStaffRecommendationOutcomeCaptureResponse(TypedDict):
    outcome: ChiefOfStaffRecommendationOutcomeRecord
    recommendation_outcomes: ChiefOfStaffRecommendationOutcomeSection
    priority_learning_summary: ChiefOfStaffPriorityLearningSummaryRecord
    pattern_drift_summary: ChiefOfStaffPatternDriftSummaryRecord


class ChiefOfStaffHandoffReviewActionCaptureResponse(TypedDict):
    review_action: ChiefOfStaffHandoffReviewActionRecord
    handoff_queue_summary: ChiefOfStaffHandoffQueueSummary
    handoff_queue_groups: ChiefOfStaffHandoffQueueGroups
    handoff_review_actions: list[ChiefOfStaffHandoffReviewActionRecord]


class ChiefOfStaffExecutionRoutingActionCaptureResponse(TypedDict):
    routing_action: ChiefOfStaffExecutionRoutingAuditRecord
    execution_routing_summary: ChiefOfStaffExecutionRoutingSummary
    routed_handoff_items: list[ChiefOfStaffRoutedHandoffItemRecord]
    routing_audit_trail: list[ChiefOfStaffExecutionRoutingAuditRecord]
    execution_readiness_posture: ChiefOfStaffExecutionReadinessPostureRecord


class ChiefOfStaffHandoffOutcomeCaptureResponse(TypedDict):
    handoff_outcome: ChiefOfStaffHandoffOutcomeRecord
    handoff_outcome_summary: ChiefOfStaffHandoffOutcomeSummary
    handoff_outcomes: list[ChiefOfStaffHandoffOutcomeRecord]
    closure_quality_summary: ChiefOfStaffClosureQualitySummaryRecord
    conversion_signal_summary: ChiefOfStaffConversionSignalSummaryRecord
    stale_ignored_escalation_posture: ChiefOfStaffStaleIgnoredEscalationPostureRecord


class ContinuityOpenLoopReviewActionResponse(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    correction_event: ContinuityCorrectionEventRecord
    review_action: ContinuityOpenLoopReviewAction
    lifecycle_outcome: str


class ContinuityCorrectionApplyResponse(TypedDict):
    continuity_object: ContinuityReviewObjectRecord
    correction_event: ContinuityCorrectionEventRecord
    replacement_object: ContinuityReviewObjectRecord | None


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
    trust_class: NotRequired[MemoryTrustClass]
    promotion_eligibility: NotRequired[MemoryPromotionEligibility]
    evidence_count: NotRequired[int | None]
    independent_source_count: NotRequired[int | None]
    extracted_by_model: NotRequired[str | None]
    trust_reason: NotRequired[str | None]
    valid_from: NotRequired[str | None]
    valid_to: NotRequired[str | None]
    last_confirmed_at: NotRequired[str | None]
    is_high_risk: bool
    is_stale_truth: bool
    is_promotable: bool
    queue_priority_mode: MemoryReviewQueuePriorityMode
    priority_reason: str
    created_at: str
    updated_at: str


class MemoryReviewQueueSummary(TypedDict):
    memory_status: Literal["active"]
    review_state: Literal["unlabeled"]
    priority_mode: MemoryReviewQueuePriorityMode
    available_priority_modes: list[MemoryReviewQueuePriorityMode]
    limit: int
    returned_count: int
    total_count: int
    has_more: bool
    order: list[str]


class MemoryReviewQueueResponse(TypedDict):
    items: list[MemoryReviewQueueItem]
    summary: MemoryReviewQueueSummary


class MemoryQualityGateComputationCounts(TypedDict):
    active_memory_count: int
    labeled_active_memory_count: int
    adjudicated_correct_count: int
    adjudicated_incorrect_count: int
    outdated_label_count: int
    insufficient_evidence_label_count: int


class MemoryQualityGateSummary(TypedDict):
    status: MemoryQualityGateStatus
    precision: float | None
    precision_target: float
    adjudicated_sample_count: int
    minimum_adjudicated_sample: int
    remaining_to_minimum_sample: int
    unlabeled_memory_count: int
    high_risk_memory_count: int
    stale_truth_count: int
    superseded_active_conflict_count: int
    counts: MemoryQualityGateComputationCounts


class MemoryQualityGateResponse(TypedDict):
    summary: MemoryQualityGateSummary


class MemoryTrustQueueAgingSummary(TypedDict):
    anchor_updated_at: str | None
    newest_updated_at: str | None
    oldest_updated_at: str | None
    backlog_span_hours: float
    fresh_within_24h_count: int
    aging_24h_to_72h_count: int
    stale_over_72h_count: int


class MemoryTrustQueuePostureSummary(TypedDict):
    priority_mode: MemoryReviewQueuePriorityMode
    total_count: int
    high_risk_count: int
    stale_truth_count: int
    priority_reason_counts: dict[str, int]
    order: list[str]
    aging: MemoryTrustQueueAgingSummary


class MemoryTrustCorrectionFreshnessSummary(TypedDict):
    total_open_loop_count: int
    stale_open_loop_count: int
    correction_recurrence_count: int
    freshness_drift_count: int


class MemoryTrustRecommendedReview(TypedDict):
    priority_mode: MemoryReviewQueuePriorityMode
    action: MemoryQualityReviewAction
    reason: str


MemoryHygienePosture = Literal["healthy", "watch", "critical"]
MemoryHygieneFocusKind = Literal[
    "duplicates",
    "stale_facts",
    "unresolved_contradictions",
    "weak_trust",
    "review_queue_pressure",
]


class MemoryDuplicateGroupRecord(TypedDict):
    group_key: str
    memory_type: str
    normalized_value: str
    count: int
    memory_ids: list[str]
    memory_keys: list[str]
    latest_updated_at: str


class MemoryReviewQueuePressureSummary(TypedDict):
    posture: MemoryHygienePosture
    total_count: int
    stale_over_72h_count: int
    aging_24h_to_72h_count: int
    reason: str


class MemoryHygieneFocusRecord(TypedDict):
    kind: MemoryHygieneFocusKind
    posture: MemoryHygienePosture
    count: int
    reason: str
    action: str
    sample_ids: list[str]


class MemoryHygieneDashboardSummary(TypedDict):
    posture: MemoryHygienePosture
    reason: str
    duplicate_group_count: int
    duplicate_memory_count: int
    stale_fact_count: int
    unresolved_contradiction_count: int
    weak_trust_count: int
    review_queue_pressure: MemoryReviewQueuePressureSummary
    duplicate_groups: list[MemoryDuplicateGroupRecord]
    focus: list[MemoryHygieneFocusRecord]
    sources: list[str]


class MemoryHygieneDashboardResponse(TypedDict):
    dashboard: MemoryHygieneDashboardSummary


class MemoryTrustDashboardSummary(TypedDict):
    quality_gate: MemoryQualityGateSummary
    queue_posture: MemoryTrustQueuePostureSummary
    retrieval_quality: RetrievalEvaluationSummary
    correction_freshness: MemoryTrustCorrectionFreshnessSummary
    recommended_review: MemoryTrustRecommendedReview
    sources: list[str]


class MemoryTrustDashboardResponse(TypedDict):
    dashboard: MemoryTrustDashboardSummary


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


class TemporalValidityRecord(TypedDict):
    valid_from: str | None
    valid_to: str | None
    effective_at: bool


class TemporalStateFactRecord(TypedDict):
    memory_id: str
    memory_key: str
    value: JsonValue | None
    status: str
    validity: TemporalValidityRecord
    created_at: str


class TemporalStateEdgeRecord(TypedDict):
    id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    validity: TemporalValidityRecord
    source_memory_ids: list[str]
    created_at: str


class TemporalStateSummary(TypedDict):
    entity_id: str
    entity_name: str
    entity_type: EntityType
    as_of: str
    fact_count: int
    edge_count: int


class TemporalStateAtRecord(TypedDict):
    entity: EntityRecord
    facts: list[TemporalStateFactRecord]
    edges: list[TemporalStateEdgeRecord]
    summary: TemporalStateSummary


class TemporalStateAtResponse(TypedDict):
    state_at: TemporalStateAtRecord


class TemporalTimelineEventRecord(TypedDict):
    id: str
    event_type: str
    object_kind: str
    object_id: str
    occurred_at: str
    summary: str
    payload: JsonObject


class TemporalTimelineSummary(TypedDict):
    entity_id: str
    entity_name: str
    entity_type: EntityType
    since: str | None
    until: str | None
    returned_count: int
    total_count: int
    limit: int
    order: list[str]


class TemporalTimelineRecord(TypedDict):
    entity: EntityRecord
    events: list[TemporalTimelineEventRecord]
    summary: TemporalTimelineSummary


class TemporalTimelineResponse(TypedDict):
    timeline: TemporalTimelineRecord


class TemporalTrustRecord(TypedDict):
    trust_class: str | None
    trust_reason: str | None
    confirmation_status: str | None
    confidence: float | None


class TemporalProvenanceRecord(TypedDict):
    source_memory_ids: list[str]
    source_event_ids: list[str]
    revision_sequence_no: int | None
    revision_action: str | None
    revision_created_at: str | None


class TemporalFactSupersessionRecord(TypedDict):
    revision_id: str
    sequence_no: int
    action: str
    created_at: str
    value: JsonValue | None
    status: str
    validity: TemporalValidityRecord
    source_event_ids: list[str]
    effective_at_as_of: bool


class TemporalFactExplainRecord(TemporalStateFactRecord):
    trust: TemporalTrustRecord
    provenance: TemporalProvenanceRecord
    supersession_chain: list[TemporalFactSupersessionRecord]


class TemporalEdgeSupersessionRecord(TypedDict):
    id: str
    created_at: str
    validity: TemporalValidityRecord
    source_memory_ids: list[str]
    effective_at_as_of: bool


class TemporalEdgeExplainRecord(TemporalStateEdgeRecord):
    trust: TemporalTrustRecord
    provenance: TemporalProvenanceRecord
    supersession_chain: list[TemporalEdgeSupersessionRecord]


class TemporalExplainSummary(TypedDict):
    entity_id: str
    entity_name: str
    entity_type: EntityType
    as_of: str
    fact_count: int
    edge_count: int


class TemporalExplainRecord(TypedDict):
    entity: EntityRecord
    facts: list[TemporalFactExplainRecord]
    edges: list[TemporalEdgeExplainRecord]
    summary: TemporalExplainSummary


class TemporalExplainResponse(TypedDict):
    explain: TemporalExplainRecord


class TrustedFactEvidenceLinkRecord(TypedDict):
    fact_id: str
    memory_key: str
    memory_type: str
    value: JsonValue
    trust: TemporalTrustRecord
    promotion_eligibility: MemoryPromotionEligibility
    evidence_count: int | None
    independent_source_count: int | None
    extracted_by_model: str | None
    source_event_ids: list[str]
    revision_sequence_no: int | None
    revision_action: str | None
    revision_created_at: str | None


class TrustedFactPatternRecord(TypedDict):
    id: str
    pattern_key: str
    title: str
    memory_type: str
    namespace_key: str
    fact_count: int
    source_fact_ids: list[str]
    evidence_chain: list[TrustedFactEvidenceLinkRecord]
    explanation: str
    created_at: str
    updated_at: str


class TrustedFactPatternListSummary(TypedDict):
    returned_count: int
    total_count: int
    limit: int
    order: list[str]


class TrustedFactPatternListResponse(TypedDict):
    items: list[TrustedFactPatternRecord]
    summary: TrustedFactPatternListSummary


class TrustedFactPatternExplainResponse(TypedDict):
    pattern: TrustedFactPatternRecord


class TrustedFactPlaybookStepRecord(TypedDict):
    step_no: int
    fact_id: str
    memory_key: str
    action_type: str
    instruction: str
    value: JsonValue
    trust: TemporalTrustRecord


class TrustedFactPlaybookRecord(TypedDict):
    id: str
    playbook_key: str
    pattern_id: str
    pattern_key: str
    title: str
    memory_type: str
    source_fact_ids: list[str]
    source_pattern_ids: list[str]
    steps: list[TrustedFactPlaybookStepRecord]
    explanation: str
    created_at: str
    updated_at: str


class TrustedFactPlaybookListSummary(TypedDict):
    returned_count: int
    total_count: int
    limit: int
    order: list[str]


class TrustedFactPlaybookListResponse(TypedDict):
    items: list[TrustedFactPlaybookRecord]
    summary: TrustedFactPlaybookListSummary


class TrustedFactPlaybookExplainResponse(TypedDict):
    playbook: TrustedFactPlaybookRecord


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


class RetrievalEvaluationFixtureResult(TypedDict):
    fixture_id: str
    title: str
    query: str
    top_k: int
    expected_relevant_ids: list[str]
    baseline_returned_ids: list[str]
    returned_ids: list[str]
    hit_count: int
    baseline_hit_count: int
    baseline_precision_at_k: float
    precision_at_k: float
    precision_lift_at_k: float
    baseline_top_result_id: str | None
    top_result_id: str | None
    baseline_top_result_ordering: ContinuityRecallOrderingMetadata | None
    top_result_ordering: ContinuityRecallOrderingMetadata | None


class RetrievalEvaluationSummary(TypedDict):
    fixture_count: int
    evaluated_fixture_count: int
    passing_fixture_count: int
    baseline_passing_fixture_count: int
    baseline_precision_at_k_mean: float
    precision_at_k_mean: float
    precision_at_k_lift: float
    baseline_precision_at_1_mean: float
    precision_at_1_mean: float
    precision_target: float
    status: RetrievalEvaluationStatus
    fixture_order: list[str]
    result_order: list[str]


class RetrievalEvaluationResponse(TypedDict):
    fixtures: list[RetrievalEvaluationFixtureResult]
    summary: RetrievalEvaluationSummary


class PublicEvalSuiteDefinitionRecord(TypedDict):
    suite_key: str
    title: str
    description: str
    evaluator_kind: str
    case_count: int
    fixture_schema_version: str
    fixture_source_path: str
    case_keys: list[str]


class PublicEvalSuiteDefinitionListResponse(TypedDict):
    items: list[PublicEvalSuiteDefinitionRecord]
    summary: JsonObject


class PublicEvalRunRecord(TypedDict):
    id: str
    status: str
    report_digest: str
    summary: JsonObject
    created_at: str


class PublicEvalResultRecord(TypedDict):
    id: str
    suite_key: str
    case_key: str
    status: str
    score: float
    summary: JsonObject
    details: JsonObject
    created_at: str


class PublicEvalRunListResponse(TypedDict):
    items: list[PublicEvalRunRecord]
    summary: JsonObject


class PublicEvalRunDetailResponse(TypedDict):
    run: PublicEvalRunRecord
    report: JsonObject
    results: list[PublicEvalResultRecord]


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
    retry_cap: int | None = None


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
    retry_count: int
    retry_cap: int
    retry_posture: TaskRunRetryPosture
    failure_class: TaskRunFailureClass | None
    stop_reason: TaskRunStopReason | None
    last_transitioned_at: str
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


class HostedUserAccountRecord(TypedDict):
    id: str
    email: str
    display_name: str | None
    beta_cohort_key: str | None
    created_at: str


class HostedAuthSessionRecord(TypedDict):
    id: str
    user_account_id: str
    workspace_id: str | None
    device_id: str | None
    status: HostedAuthSessionStatus
    expires_at: str
    revoked_at: str | None
    last_seen_at: str | None
    created_at: str


class HostedMagicLinkChallengeRecord(TypedDict):
    id: str
    email: str
    challenge_token_hash: str
    status: HostedMagicLinkChallengeStatus
    expires_at: str
    consumed_at: str | None
    created_at: str


class HostedWorkspaceRecord(TypedDict):
    id: str
    owner_user_account_id: str
    slug: str
    name: str
    bootstrap_status: HostedWorkspaceBootstrapStatus
    bootstrapped_at: str | None
    support_status: Literal["healthy", "needs_attention", "blocked"]
    support_notes: JsonObject
    onboarding_last_error_code: str | None
    onboarding_last_error_detail: str | None
    onboarding_last_error_at: str | None
    onboarding_error_count: int
    rollout_evidence: JsonObject
    rate_limit_evidence: JsonObject
    incident_evidence: JsonObject
    created_at: str
    updated_at: str


class HostedBootstrapStatusRecord(TypedDict):
    workspace_id: str
    status: HostedWorkspaceBootstrapStatus
    bootstrapped_at: str | None
    ready_for_next_phase_telegram_linkage: bool
    telegram_state: Literal["available_in_p10_s2_transport"]


class HostedDeviceRecord(TypedDict):
    id: str
    user_account_id: str
    workspace_id: str | None
    device_key: str
    device_label: str
    status: HostedDeviceStatus
    last_seen_at: str | None
    revoked_at: str | None
    created_at: str
    updated_at: str


class HostedDeviceLinkChallengeRecord(TypedDict):
    id: str
    user_account_id: str
    workspace_id: str | None
    device_key: str
    device_label: str
    challenge_token_hash: str
    status: HostedDeviceLinkChallengeStatus
    expires_at: str
    confirmed_at: str | None
    device_id: str | None
    created_at: str


class HostedUserPreferencesRecord(TypedDict):
    id: str
    user_account_id: str
    timezone: str
    brief_preferences: JsonObject
    quiet_hours: JsonObject
    created_at: str
    updated_at: str


class NotificationSubscriptionRecord(TypedDict):
    id: str
    workspace_id: str
    channel_type: ChannelTransportType
    channel_identity_id: str
    notifications_enabled: bool
    daily_brief_enabled: bool
    daily_brief_window_start: str
    open_loop_prompts_enabled: bool
    waiting_for_prompts_enabled: bool
    stale_prompts_enabled: bool
    timezone: str
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    created_at: str
    updated_at: str


class ChannelIdentityRecord(TypedDict):
    id: str
    user_account_id: str
    workspace_id: str
    channel_type: ChannelTransportType
    external_user_id: str
    external_chat_id: str
    external_username: str | None
    status: ChannelIdentityStatus
    linked_at: str
    unlinked_at: str | None
    created_at: str
    updated_at: str


class ChannelLinkChallengeRecord(TypedDict):
    id: str
    user_account_id: str
    workspace_id: str
    channel_type: ChannelTransportType
    link_code: str
    status: ChannelLinkChallengeStatus
    expires_at: str
    confirmed_at: str | None
    channel_identity_id: str | None
    created_at: str
    challenge_token: NotRequired[str]


class ChannelThreadRecord(TypedDict):
    id: str
    workspace_id: str
    channel_type: ChannelTransportType
    external_thread_key: str
    channel_identity_id: str | None
    last_message_at: str | None
    created_at: str
    updated_at: str


class ChannelMessageRecord(TypedDict):
    id: str
    workspace_id: str | None
    channel_thread_id: str | None
    channel_identity_id: str | None
    channel_type: ChannelTransportType
    direction: ChannelMessageDirection
    provider_update_id: str | None
    provider_message_id: str | None
    external_chat_id: str | None
    external_user_id: str | None
    message_text: str | None
    normalized_payload: JsonObject
    route_status: ChannelMessageRouteStatus
    idempotency_key: str
    created_at: str
    received_at: str


class ChatIntentRecord(TypedDict):
    id: str
    workspace_id: str
    channel_message_id: str
    channel_thread_id: str | None
    intent_kind: ChatIntentKind
    status: ChatIntentStatus
    intent_payload: JsonObject
    result_payload: JsonObject
    handled_at: str | None
    created_at: str


class ChannelDeliveryReceiptRecord(TypedDict):
    id: str
    workspace_id: str
    channel_message_id: str
    channel_type: ChannelTransportType
    status: ChannelDeliveryReceiptStatus
    provider_receipt_id: str | None
    failure_code: str | None
    failure_detail: str | None
    scheduled_job_id: str | None
    scheduler_job_kind: TelegramSchedulerJobKind | None
    scheduled_for: str | None
    schedule_slot: str | None
    notification_policy: JsonObject
    rollout_flag_state: Literal["enabled", "blocked"]
    support_evidence: JsonObject
    rate_limit_evidence: JsonObject
    incident_evidence: JsonObject
    recorded_at: str
    created_at: str


class TelegramContinuityBriefRecord(TypedDict):
    id: str
    workspace_id: str
    channel_type: ChannelTransportType
    channel_identity_id: str
    brief_kind: Literal["daily_brief"]
    assembly_version: str
    summary: JsonObject
    brief_payload: JsonObject
    message_text: str
    compiled_at: str
    created_at: str


class TelegramDailyBriefJobRecord(TypedDict):
    id: str
    workspace_id: str
    channel_type: ChannelTransportType
    channel_identity_id: str
    job_kind: TelegramSchedulerJobKind
    prompt_kind: TelegramSchedulerPromptKind | None
    prompt_id: str | None
    continuity_object_id: str | None
    continuity_brief_id: str | None
    schedule_slot: str
    idempotency_key: str
    due_at: str
    status: TelegramSchedulerJobStatus
    suppression_reason: str | None
    attempt_count: int
    delivery_receipt_id: str | None
    payload: JsonObject
    result_payload: JsonObject
    rollout_flag_state: Literal["enabled", "blocked"]
    support_evidence: JsonObject
    rate_limit_evidence: JsonObject
    incident_evidence: JsonObject
    attempted_at: str | None
    completed_at: str | None
    created_at: str
    updated_at: str


class ChatTelemetryRecord(TypedDict):
    id: str
    user_account_id: str
    workspace_id: str | None
    channel_message_id: str | None
    daily_brief_job_id: str | None
    delivery_receipt_id: str | None
    flow_kind: Literal["chat_handle", "scheduler_daily_brief", "scheduler_open_loop_prompt"]
    event_kind: Literal["attempt", "result", "rollout_block", "rate_limited", "abuse_block", "incident"]
    status: Literal[
        "ok",
        "failed",
        "blocked_rollout",
        "rate_limited",
        "abuse_blocked",
        "suppressed",
        "simulated",
        "delivered",
    ]
    route_path: str
    rollout_flag_key: str | None
    rollout_flag_state: str | None
    rate_limit_key: str | None
    rate_limit_window_seconds: int | None
    rate_limit_max_requests: int | None
    retry_after_seconds: int | None
    abuse_signal: str | None
    evidence: JsonObject
    created_at: str


class ApprovalChallengeRecord(TypedDict):
    id: str
    workspace_id: str
    approval_id: str
    channel_message_id: str | None
    status: Literal["pending", "approved", "rejected", "dismissed"]
    challenge_prompt: str
    challenge_payload: JsonObject
    resolved_at: str | None
    created_at: str
    updated_at: str


class OpenLoopReviewRecord(TypedDict):
    id: str
    workspace_id: str
    continuity_object_id: str
    channel_message_id: str | None
    correction_event_id: str | None
    review_action: ContinuityOpenLoopReviewAction
    note: str | None
    created_at: str
