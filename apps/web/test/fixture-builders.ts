import type {
  ChiefOfStaffHandoffQueueGroup,
  ChiefOfStaffPriorityBrief,
  ChiefOfStaffPrioritySummary,
} from "../lib/api";

type ExtendedPriorityFields =
  | "handoff_queue_summary"
  | "handoff_queue_groups"
  | "handoff_review_actions"
  | "handoff_outcome_summary"
  | "handoff_outcomes"
  | "closure_quality_summary"
  | "conversion_signal_summary"
  | "stale_ignored_escalation_posture"
  | "execution_routing_summary"
  | "routed_handoff_items"
  | "routing_audit_trail"
  | "execution_readiness_posture";

type ExtendedSummaryFields =
  | "handoff_queue_total_count"
  | "handoff_queue_ready_count"
  | "handoff_queue_pending_approval_count"
  | "handoff_queue_executed_count"
  | "handoff_queue_stale_count"
  | "handoff_queue_expired_count"
  | "handoff_queue_state_order"
  | "handoff_queue_group_order"
  | "handoff_queue_item_order"
  | "handoff_outcome_total_count"
  | "handoff_outcome_latest_count"
  | "handoff_outcome_executed_count"
  | "handoff_outcome_ignored_count"
  | "closure_quality_posture"
  | "stale_ignored_escalation_posture";

const EXTENDED_SUMMARY_DEFAULTS: Pick<ChiefOfStaffPrioritySummary, ExtendedSummaryFields> = {
  handoff_queue_total_count: 0,
  handoff_queue_ready_count: 0,
  handoff_queue_pending_approval_count: 0,
  handoff_queue_executed_count: 0,
  handoff_queue_stale_count: 0,
  handoff_queue_expired_count: 0,
  handoff_queue_state_order: ["ready", "pending_approval", "executed", "stale", "expired"],
  handoff_queue_group_order: ["ready", "pending_approval", "executed", "stale", "expired"],
  handoff_queue_item_order: [],
  handoff_outcome_total_count: 0,
  handoff_outcome_latest_count: 0,
  handoff_outcome_executed_count: 0,
  handoff_outcome_ignored_count: 0,
  closure_quality_posture: "insufficient_signal",
  stale_ignored_escalation_posture: "watch",
};

const EMPTY_QUEUE_GROUP: ChiefOfStaffHandoffQueueGroup = {
  items: [],
  summary: {
    lifecycle_state: "ready",
    returned_count: 0,
    total_count: 0,
    order: [],
  },
  empty_state: { is_empty: true, message: "No handoff items." },
};

const EXTENDED_PRIORITY_DEFAULTS: Pick<ChiefOfStaffPriorityBrief, ExtendedPriorityFields> = {
  handoff_queue_summary: {
    total_count: 0,
    ready_count: 0,
    pending_approval_count: 0,
    executed_count: 0,
    stale_count: 0,
    expired_count: 0,
    state_order: ["ready", "pending_approval", "executed", "stale", "expired"],
    group_order: ["ready", "pending_approval", "executed", "stale", "expired"],
    item_order: [],
    review_action_order: [
      "mark_ready",
      "mark_pending_approval",
      "mark_executed",
      "mark_stale",
      "mark_expired",
    ],
  },
  handoff_queue_groups: {
    ready: EMPTY_QUEUE_GROUP,
    pending_approval: {
      ...EMPTY_QUEUE_GROUP,
      summary: { ...EMPTY_QUEUE_GROUP.summary, lifecycle_state: "pending_approval" },
    },
    executed: {
      ...EMPTY_QUEUE_GROUP,
      summary: { ...EMPTY_QUEUE_GROUP.summary, lifecycle_state: "executed" },
    },
    stale: {
      ...EMPTY_QUEUE_GROUP,
      summary: { ...EMPTY_QUEUE_GROUP.summary, lifecycle_state: "stale" },
    },
    expired: {
      ...EMPTY_QUEUE_GROUP,
      summary: { ...EMPTY_QUEUE_GROUP.summary, lifecycle_state: "expired" },
    },
  },
  handoff_review_actions: [],
  handoff_outcome_summary: {
    returned_count: 0,
    total_count: 0,
    latest_total_count: 0,
    status_counts: { reviewed: 0, approved: 0, rejected: 0, rewritten: 0, executed: 0, ignored: 0, expired: 0 },
    latest_status_counts: { reviewed: 0, approved: 0, rejected: 0, rewritten: 0, executed: 0, ignored: 0, expired: 0 },
    status_order: ["reviewed", "approved", "rejected", "rewritten", "executed", "ignored", "expired"],
    order: [],
  },
  handoff_outcomes: [],
  closure_quality_summary: {
    posture: "insufficient_signal",
    reason: "No captured outcomes.",
    closed_loop_count: 0,
    unresolved_count: 0,
    rejected_count: 0,
    ignored_count: 0,
    expired_count: 0,
    closure_rate: 0,
    explanation: "No captured outcomes.",
  },
  conversion_signal_summary: {
    total_handoff_count: 0,
    latest_outcome_count: 0,
    executed_count: 0,
    approved_count: 0,
    reviewed_count: 0,
    rewritten_count: 0,
    rejected_count: 0,
    ignored_count: 0,
    expired_count: 0,
    recommendation_to_execution_conversion_rate: 0,
    recommendation_to_closure_conversion_rate: 0,
    capture_coverage_rate: 0,
    explanation: "No captured outcomes.",
  },
  stale_ignored_escalation_posture: {
    posture: "watch",
    reason: "No stale or ignored outcomes.",
    stale_queue_count: 0,
    ignored_count: 0,
    expired_count: 0,
    trigger_count: 0,
    guidance_posture_explanation: "No escalation trigger.",
    supporting_signals: [],
  },
  execution_routing_summary: {
    total_handoff_count: 0,
    routed_handoff_count: 0,
    unrouted_handoff_count: 0,
    task_workflow_draft_count: 0,
    approval_workflow_draft_count: 0,
    follow_up_draft_only_count: 0,
    route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
    routed_item_order: [],
    audit_order: [],
    transition_order: ["routed", "reaffirmed"],
    approval_required: true,
    non_autonomous_guarantee: "No external side effects.",
    reason: "No routed handoffs.",
  },
  routed_handoff_items: [],
  routing_audit_trail: [],
  execution_readiness_posture: {
    posture: "approval_required_draft_only",
    approval_required: true,
    autonomous_execution: false,
    external_side_effects_allowed: false,
    approval_path_visible: true,
    route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
    required_route_targets: [],
    transition_order: ["routed", "reaffirmed"],
    non_autonomous_guarantee: "No external side effects.",
    reason: "No routed handoffs.",
  },
};

export function completeChiefOfStaffPriorityBrief(
  brief: Omit<ChiefOfStaffPriorityBrief, ExtendedPriorityFields | "summary"> &
    Partial<Pick<ChiefOfStaffPriorityBrief, ExtendedPriorityFields>> & {
      summary: Omit<ChiefOfStaffPrioritySummary, ExtendedSummaryFields> &
        Partial<Pick<ChiefOfStaffPrioritySummary, ExtendedSummaryFields>>;
    },
): ChiefOfStaffPriorityBrief {
  return {
    ...EXTENDED_PRIORITY_DEFAULTS,
    ...brief,
    summary: { ...EXTENDED_SUMMARY_DEFAULTS, ...brief.summary },
  };
}
