import { ChiefOfStaffActionHandoffPanel } from "../../components/chief-of-staff-action-handoff-panel";
import { ChiefOfStaffExecutionRoutingPanel } from "../../components/chief-of-staff-execution-routing-panel";
import { ChiefOfStaffHandoffQueuePanel } from "../../components/chief-of-staff-handoff-queue-panel";
import { ChiefOfStaffFollowThroughPanel } from "../../components/chief-of-staff-follow-through-panel";
import { ChiefOfStaffPreparationPanel } from "../../components/chief-of-staff-preparation-panel";
import { ChiefOfStaffPriorityPanel } from "../../components/chief-of-staff-priority-panel";
import { ChiefOfStaffWeeklyReviewPanel } from "../../components/chief-of-staff-weekly-review-panel";
import { PageHeader } from "../../components/page-header";
import { StatusBadge } from "../../components/status-badge";
import type { ApiSource, ChiefOfStaffPriorityBrief } from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getChiefOfStaffPriorityBrief,
  hasLiveApiConfig,
  pageModeLabel,
} from "../../lib/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }
  return value?.trim() ?? "";
}

function parseNonNegativeInt(value: string, fallback: number) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
}

const chiefOfStaffFixture: ChiefOfStaffPriorityBrief = {
  assembly_version: "chief_of_staff_priority_brief_v0",
  scope: {
    thread_id: "thread-fixture-1",
    since: null,
    until: null,
  },
  ranked_items: [
    {
      rank: 1,
      id: "priority-fixture-1",
      capture_event_id: "capture-priority-fixture-1",
      object_type: "NextAction",
      status: "active",
      title: "Next Action: Confirm launch checklist owner",
      priority_posture: "urgent",
      confidence_posture: "low",
      confidence: 0.97,
      score: 642.5,
      provenance: {
        thread_id: "thread-fixture-1",
        source_event_ids: ["event-fixture-1"],
      },
      created_at: "2026-03-31T10:05:00Z",
      updated_at: "2026-03-31T10:05:00Z",
      rationale: {
        reasons: [
          "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
          "Confidence is explicitly downgraded by current memory trust posture.",
          "Provenance references are attached from continuity recall evidence.",
        ],
        ranking_inputs: {
          posture: "urgent",
          open_loop_posture: "next_action",
          recency_rank: 1,
          age_hours_relative_to_latest: 0,
          recall_relevance: 120,
          scope_match_count: 1,
          query_term_match_count: 1,
          freshness_posture: "fresh",
          provenance_posture: "strong",
          supersession_posture: "current",
        },
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-1",
          },
        ],
        trust_signals: {
          quality_gate_status: "insufficient_sample",
          retrieval_status: "pass",
          trust_confidence_cap: "low",
          downgraded_by_trust: true,
          reason:
            "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
        },
      },
    },
    {
      rank: 2,
      id: "priority-fixture-2",
      capture_event_id: "capture-priority-fixture-2",
      object_type: "WaitingFor",
      status: "active",
      title: "Waiting For: Vendor legal review",
      priority_posture: "waiting",
      confidence_posture: "low",
      confidence: 0.88,
      score: 434,
      provenance: {
        thread_id: "thread-fixture-1",
        source_event_ids: ["event-fixture-2"],
      },
      created_at: "2026-03-31T09:15:00Z",
      updated_at: "2026-03-31T09:15:00Z",
      rationale: {
        reasons: [
          "Marked waiting because this item is in waiting-for posture and requires follow-through tracking.",
          "Aging evidence: 0.8h older than the newest scoped priority candidate.",
          "Provenance references are attached from continuity recall evidence.",
        ],
        ranking_inputs: {
          posture: "waiting",
          open_loop_posture: "waiting_for",
          recency_rank: 2,
          age_hours_relative_to_latest: 0.833333,
          recall_relevance: 108,
          scope_match_count: 1,
          query_term_match_count: 0,
          freshness_posture: "aging",
          provenance_posture: "strong",
          supersession_posture: "current",
        },
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-2",
          },
        ],
        trust_signals: {
          quality_gate_status: "insufficient_sample",
          retrieval_status: "pass",
          trust_confidence_cap: "low",
          downgraded_by_trust: true,
          reason:
            "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
        },
      },
    },
  ],
  overdue_items: [
    {
      rank: 1,
      id: "follow-fixture-overdue-1",
      capture_event_id: "capture-follow-fixture-overdue-1",
      object_type: "NextAction",
      status: "active",
      title: "Next Action: Send partner status follow-up",
      current_priority_posture: "urgent",
      follow_through_posture: "overdue",
      recommendation_action: "escalate",
      reason:
        "Execution follow-through is overdue (posture=urgent, age=140.0h), so action 'escalate' is recommended.",
      age_hours: 140,
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-follow-fixture-overdue-1",
        },
      ],
      created_at: "2026-03-26T08:00:00Z",
      updated_at: "2026-03-26T08:00:00Z",
    },
  ],
  stale_waiting_for_items: [
    {
      rank: 1,
      id: "follow-fixture-stale-waiting-1",
      capture_event_id: "capture-follow-fixture-stale-waiting-1",
      object_type: "WaitingFor",
      status: "stale",
      title: "Waiting For: Procurement approval",
      current_priority_posture: "stale",
      follow_through_posture: "stale_waiting_for",
      recommendation_action: "nudge",
      reason:
        "Waiting-for item is stale (status=stale, age=96.0h from latest scoped item), so action 'nudge' is recommended.",
      age_hours: 96,
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-follow-fixture-stale-waiting-1",
        },
      ],
      created_at: "2026-03-27T00:00:00Z",
      updated_at: "2026-03-27T00:00:00Z",
    },
  ],
  slipped_commitments: [
    {
      rank: 1,
      id: "follow-fixture-slipped-commitment-1",
      capture_event_id: "capture-follow-fixture-slipped-commitment-1",
      object_type: "Commitment",
      status: "active",
      title: "Commitment: Publish weekly status digest",
      current_priority_posture: "important",
      follow_through_posture: "slipped_commitment",
      recommendation_action: "defer",
      reason:
        "Commitment is slipping (status=active, age=60.0h from latest scoped item), so action 'defer' is recommended.",
      age_hours: 60,
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-follow-fixture-slipped-commitment-1",
        },
      ],
      created_at: "2026-03-28T12:00:00Z",
      updated_at: "2026-03-28T12:00:00Z",
    },
  ],
  escalation_posture: {
    posture: "critical",
    reason: "At least one follow-through item requires escalation.",
    total_follow_through_count: 3,
    nudge_count: 1,
    defer_count: 1,
    escalate_count: 1,
    close_loop_candidate_count: 0,
  },
  draft_follow_up: {
    status: "drafted",
    mode: "draft_only",
    approval_required: true,
    auto_send: false,
    reason: "Highest-severity follow-through item selected deterministically for operator review.",
    target_metadata: {
      continuity_object_id: "follow-fixture-overdue-1",
      capture_event_id: "capture-follow-fixture-overdue-1",
      object_type: "NextAction",
      priority_posture: "urgent",
      follow_through_posture: "overdue",
      recommendation_action: "escalate",
      thread_id: "thread-fixture-1",
    },
    content: {
      subject: "Follow-up: Next Action: Send partner status follow-up",
      body: [
        "Following up on: Next Action: Send partner status follow-up",
        "Current follow-through posture: overdue",
        "Current priority posture: urgent",
        "Recommended action: escalate",
        "Reason: Execution follow-through is overdue (posture=urgent, age=140.0h), so action 'escalate' is recommended.",
        "",
        "This draft is artifact-only and requires explicit approval before any external send.",
      ].join("\\n"),
    },
  },
  recommended_next_action: {
    action_type: "execute_next_action",
    title: "Next Action: Confirm launch checklist owner",
    target_priority_id: "priority-fixture-1",
    priority_posture: "urgent",
    confidence_posture: "low",
    reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
    provenance_references: [
      {
        source_kind: "continuity_capture_event",
        source_id: "capture-priority-fixture-1",
      },
    ],
    deterministic_rank_key: "1:priority-fixture-1:642.500000",
  },
  preparation_brief: {
    scope: {
      thread_id: "thread-fixture-1",
      since: null,
      until: null,
    },
    context_items: [
      {
        rank: 1,
        id: "prep-context-fixture-1",
        capture_event_id: "capture-prep-context-fixture-1",
        object_type: "Decision",
        status: "active",
        title: "Decision: Keep rollout to one launch cohort",
        reason: "Decision context carried forward for deterministic meeting prep.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-prep-context-fixture-1",
          },
        ],
        created_at: "2026-03-31T07:45:00Z",
      },
    ],
    last_decision: {
      rank: 1,
      id: "prep-decision-fixture-1",
      capture_event_id: "capture-prep-decision-fixture-1",
      object_type: "Decision",
      status: "active",
      title: "Decision: Keep rollout to one launch cohort",
      reason: "Latest scoped decision included to ground upcoming preparation context.",
      confidence_posture: "low",
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-prep-decision-fixture-1",
        },
      ],
      created_at: "2026-03-31T07:45:00Z",
    },
    open_loops: [],
    next_action: {
      rank: 1,
      id: "prep-next-action-fixture-1",
      capture_event_id: "capture-prep-next-action-fixture-1",
      object_type: "NextAction",
      status: "active",
      title: "Next Action: Confirm launch checklist owner",
      reason: "Next action is included to keep immediate execution focus explicit after interruption.",
      confidence_posture: "low",
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-prep-next-action-fixture-1",
        },
      ],
      created_at: "2026-03-31T10:05:00Z",
    },
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    summary: {
      limit: 6,
      returned_count: 1,
      total_count: 1,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  what_changed_summary: {
    items: [
      {
        rank: 1,
        id: "what-changed-fixture-1",
        capture_event_id: "capture-what-changed-fixture-1",
        object_type: "NextAction",
        status: "active",
        title: "Next Action: Confirm launch checklist owner",
        reason: "Included from deterministic continuity recent-changes ordering.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-what-changed-fixture-1",
          },
        ],
        created_at: "2026-03-31T10:05:00Z",
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    summary: {
      limit: 6,
      returned_count: 1,
      total_count: 1,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  prep_checklist: {
    items: [
      {
        rank: 1,
        id: "prep-checklist-fixture-1",
        capture_event_id: "capture-prep-checklist-fixture-1",
        object_type: "WaitingFor",
        status: "active",
        title: "Waiting For: Vendor legal review",
        reason: "Prepare a status check and explicit owner for this unresolved open loop.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-prep-checklist-fixture-1",
          },
        ],
        created_at: "2026-03-31T09:15:00Z",
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    summary: {
      limit: 6,
      returned_count: 1,
      total_count: 1,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  suggested_talking_points: {
    items: [
      {
        rank: 1,
        id: "suggested-point-fixture-1",
        capture_event_id: "capture-suggested-point-fixture-1",
        object_type: "Blocker",
        status: "active",
        title: "Blocker: Release token rotation lag",
        reason: "Raise this unresolved dependency explicitly and confirm a concrete follow-up path.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-suggested-point-fixture-1",
          },
        ],
        created_at: "2026-03-30T10:00:00Z",
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    summary: {
      limit: 6,
      returned_count: 1,
      total_count: 1,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  resumption_supervision: {
    recommendations: [
      {
        rank: 1,
        action: "execute_next_action",
        title: "Next Action: Confirm launch checklist owner",
        reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
        confidence_posture: "low",
        target_priority_id: "priority-fixture-1",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-1",
          },
        ],
      },
      {
        rank: 2,
        action: "review_scope",
        title: "Calibrate recommendation confidence before execution",
        reason:
          "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
        confidence_posture: "low",
        target_priority_id: null,
        provenance_references: [],
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    summary: {
      limit: 3,
      returned_count: 2,
      total_count: 2,
      order: ["rank_asc"],
    },
  },
  weekly_review_brief: {
    scope: {
      thread_id: "thread-fixture-1",
      since: null,
      until: null,
    },
    rollup: {
      total_count: 4,
      waiting_for_count: 1,
      blocker_count: 1,
      stale_count: 1,
      correction_recurrence_count: 1,
      freshness_drift_count: 1,
      next_action_count: 1,
      posture_order: ["waiting_for", "blocker", "stale", "next_action"],
    },
    guidance: [
      {
        rank: 1,
        action: "escalate",
        signal_count: 2,
        rationale:
          "Escalate where blockers (1) and escalate actions (1) indicate execution risk.",
      },
      {
        rank: 2,
        action: "close",
        signal_count: 1,
        rationale:
          "Close loops where close candidates (0) and actionable next steps (1) support deterministic closure.",
      },
      {
        rank: 3,
        action: "defer",
        signal_count: 2,
        rationale:
          "Defer or park work where defer actions (1), stale items (1), and waiting-for load (1) are concentrated.",
      },
    ],
    summary: {
      guidance_order: ["close", "defer", "escalate"],
      guidance_item_order: ["signal_count_desc", "action_desc"],
    },
  },
  recommendation_outcomes: {
    items: [
      {
        id: "outcome-fixture-1",
        capture_event_id: "capture-outcome-fixture-1",
        outcome: "accept",
        recommendation_action_type: "execute_next_action",
        recommendation_title: "Next Action: Confirm launch checklist owner",
        rewritten_title: null,
        target_priority_id: "priority-fixture-1",
        rationale: "Accepted in weekly review because blockers were already explicit.",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-outcome-fixture-1",
          },
        ],
        created_at: "2026-03-31T12:00:00Z",
        updated_at: "2026-03-31T12:00:00Z",
      },
    ],
    summary: {
      returned_count: 1,
      total_count: 1,
      outcome_counts: {
        accept: 1,
        defer: 0,
        ignore: 0,
        rewrite: 0,
      },
      order: ["created_at_desc", "id_desc"],
    },
  },
  priority_learning_summary: {
    total_count: 1,
    accept_count: 1,
    defer_count: 0,
    ignore_count: 0,
    rewrite_count: 0,
    acceptance_rate: 1,
    override_rate: 0,
    defer_hotspots: [],
    ignore_hotspots: [],
    priority_shift_explanation:
      "Prioritization is reinforcing currently accepted recommendation patterns while tracking defer/override hotspots.",
    hotspot_order: ["count_desc", "key_asc"],
  },
  pattern_drift_summary: {
    posture: "improving",
    reason:
      "Accepted outcomes are leading with bounded defers/overrides, indicating improving recommendation fit.",
    supporting_signals: [
      "Outcomes captured: 1",
      "Accept=1, Defer=0, Ignore=0, Rewrite=0",
      "Acceptance rate=1.000000, Override rate=0.000000",
    ],
  },
  action_handoff_brief: {
    summary:
      "Prepared 1 deterministic handoff item from recommended_next_action signals. All task and approval drafts remain artifact-only and approval-bounded.",
    confidence_posture: "low",
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
    source_order: ["recommended_next_action", "follow_through", "prep_checklist", "weekly_review"],
    provenance_references: [
      {
        source_kind: "continuity_capture_event",
        source_id: "capture-priority-fixture-1",
      },
      {
        source_kind: "continuity_capture_event",
        source_id: "capture-follow-fixture-overdue-1",
      },
    ],
  },
  handoff_items: [
    {
      rank: 1,
      handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
      source_kind: "recommended_next_action",
      source_reference_id: "priority-fixture-1",
      title: "Next Action: Confirm launch checklist owner",
      recommendation_action: "execute_next_action",
      priority_posture: "urgent",
      confidence_posture: "low",
      rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-priority-fixture-1",
        },
      ],
      score: 1650,
      task_draft: {
        status: "draft",
        mode: "governed_request_draft",
        approval_required: true,
        auto_execute: false,
        source_handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
        title: "Next Action: Confirm launch checklist owner",
        summary:
          "Draft-only governed request assembled from chief-of-staff handoff artifacts; requires explicit approval before any execution.",
        target: {
          thread_id: "thread-fixture-1",
          task_id: null,
          project: null,
          person: null,
        },
        request: {
          action: "execute_next_action",
          scope: "chief_of_staff_priority",
          domain_hint: "planning",
          risk_hint: "governed_handoff",
          attributes: {},
        },
        rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-1",
          },
        ],
      },
      approval_draft: {
        status: "draft_only",
        mode: "approval_request_draft",
        decision: "approval_required",
        approval_required: true,
        auto_submit: false,
        source_handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
        request: {
          action: "execute_next_action",
          scope: "chief_of_staff_priority",
          domain_hint: "planning",
          risk_hint: "governed_handoff",
          attributes: {},
        },
        reason:
          "Execution remains approval-bounded. This approval draft is artifact-only and must be explicitly submitted and resolved before any side effect.",
        required_checks: [
          "operator_review_handoff_artifact",
          "submit_governed_approval_request",
          "explicit_approval_resolution",
        ],
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-1",
          },
        ],
      },
    },
  ],
  handoff_queue_summary: {
    total_count: 1,
    ready_count: 1,
    pending_approval_count: 0,
    executed_count: 0,
    stale_count: 0,
    expired_count: 0,
    state_order: ["ready", "pending_approval", "executed", "stale", "expired"],
    group_order: ["ready", "pending_approval", "executed", "stale", "expired"],
    item_order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
    review_action_order: ["mark_ready", "mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"],
  },
  handoff_queue_groups: {
    ready: {
      items: [
        {
          queue_rank: 1,
          handoff_rank: 1,
          handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
          lifecycle_state: "ready",
          state_reason: "Handoff item is ready for explicit operator review.",
          source_kind: "recommended_next_action",
          source_reference_id: "priority-fixture-1",
          title: "Next Action: Confirm launch checklist owner",
          recommendation_action: "execute_next_action",
          priority_posture: "urgent",
          confidence_posture: "low",
          score: 1650,
          age_hours_relative_to_latest: 0,
          review_action_order: ["mark_ready", "mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"],
          available_review_actions: ["mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"],
          last_review_action: null,
          provenance_references: [
            {
              source_kind: "continuity_capture_event",
              source_id: "capture-priority-fixture-1",
            },
          ],
        },
      ],
      summary: {
        lifecycle_state: "ready",
        returned_count: 1,
        total_count: 1,
        order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
      },
      empty_state: {
        is_empty: false,
        message: "No ready handoff items for this scope.",
      },
    },
    pending_approval: {
      items: [],
      summary: {
        lifecycle_state: "pending_approval",
        returned_count: 0,
        total_count: 0,
        order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
      },
      empty_state: {
        is_empty: true,
        message: "No handoff items are currently pending approval.",
      },
    },
    executed: {
      items: [],
      summary: {
        lifecycle_state: "executed",
        returned_count: 0,
        total_count: 0,
        order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
      },
      empty_state: {
        is_empty: true,
        message: "No handoff items are currently marked executed.",
      },
    },
    stale: {
      items: [],
      summary: {
        lifecycle_state: "stale",
        returned_count: 0,
        total_count: 0,
        order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
      },
      empty_state: {
        is_empty: true,
        message: "No stale handoff items are currently surfaced.",
      },
    },
    expired: {
      items: [],
      summary: {
        lifecycle_state: "expired",
        returned_count: 0,
        total_count: 0,
        order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
      },
      empty_state: {
        is_empty: true,
        message: "No expired handoff items are currently surfaced.",
      },
    },
  },
  handoff_review_actions: [],
  execution_routing_summary: {
    total_handoff_count: 1,
    routed_handoff_count: 0,
    unrouted_handoff_count: 1,
    task_workflow_draft_count: 0,
    approval_workflow_draft_count: 0,
    follow_up_draft_only_count: 0,
    route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
    routed_item_order: ["handoff_rank_asc", "handoff_item_id_asc"],
    audit_order: ["created_at_desc", "id_desc"],
    transition_order: ["routed", "reaffirmed"],
    approval_required: true,
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    reason:
      "Routing transitions are explicit and auditable; task/approval/follow-up routes remain draft-only until separately submitted through governed workflows.",
  },
  routed_handoff_items: [
    {
      handoff_rank: 1,
      handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
      title: "Next Action: Confirm launch checklist owner",
      source_kind: "recommended_next_action",
      recommendation_action: "execute_next_action",
      route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
      available_route_targets: ["task_workflow_draft", "approval_workflow_draft"],
      routed_targets: [],
      is_routed: false,
      task_workflow_draft_routed: false,
      approval_workflow_draft_routed: false,
      follow_up_draft_only_routed: false,
      follow_up_draft_only_applicable: false,
      task_draft: {
        status: "draft",
        mode: "governed_request_draft",
        approval_required: true,
        auto_execute: false,
        source_handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
        title: "Next Action: Confirm launch checklist owner",
        summary:
          "Draft-only governed request assembled from chief-of-staff handoff artifacts; requires explicit approval before any execution.",
        target: {
          thread_id: "thread-fixture-1",
          task_id: null,
          project: null,
          person: null,
        },
        request: {
          action: "execute_next_action",
          scope: "chief_of_staff_priority",
          domain_hint: "planning",
          risk_hint: "governed_handoff",
          attributes: {},
        },
        rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-1",
          },
        ],
      },
      approval_draft: {
        status: "draft_only",
        mode: "approval_request_draft",
        decision: "approval_required",
        approval_required: true,
        auto_submit: false,
        source_handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
        request: {
          action: "execute_next_action",
          scope: "chief_of_staff_priority",
          domain_hint: "planning",
          risk_hint: "governed_handoff",
          attributes: {},
        },
        reason:
          "Execution remains approval-bounded. This approval draft is artifact-only and must be explicitly submitted and resolved before any side effect.",
        required_checks: [
          "operator_review_handoff_artifact",
          "submit_governed_approval_request",
          "explicit_approval_resolution",
        ],
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-1",
          },
        ],
      },
      last_routing_transition: null,
    },
  ],
  routing_audit_trail: [],
  execution_readiness_posture: {
    posture: "approval_required_draft_only",
    approval_required: true,
    autonomous_execution: false,
    external_side_effects_allowed: false,
    approval_path_visible: true,
    route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"],
    required_route_targets: ["task_workflow_draft", "approval_workflow_draft"],
    transition_order: ["routed", "reaffirmed"],
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    reason:
      "Execution routing remains draft-only and approval-bounded; operators can explicitly route handoff items into governed task/approval drafts with auditable transitions.",
  },
  task_draft: {
    status: "draft",
    mode: "governed_request_draft",
    approval_required: true,
    auto_execute: false,
    source_handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
    title: "Next Action: Confirm launch checklist owner",
    summary:
      "Draft-only governed request assembled from chief-of-staff handoff artifacts; requires explicit approval before any execution.",
    target: {
      thread_id: "thread-fixture-1",
      task_id: null,
      project: null,
      person: null,
    },
    request: {
      action: "execute_next_action",
      scope: "chief_of_staff_priority",
      domain_hint: "planning",
      risk_hint: "governed_handoff",
      attributes: {},
    },
    rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
    provenance_references: [
      {
        source_kind: "continuity_capture_event",
        source_id: "capture-priority-fixture-1",
      },
    ],
  },
  approval_draft: {
    status: "draft_only",
    mode: "approval_request_draft",
    decision: "approval_required",
    approval_required: true,
    auto_submit: false,
    source_handoff_item_id: "handoff-1-recommended_next_action-priority-fixture-1",
    request: {
      action: "execute_next_action",
      scope: "chief_of_staff_priority",
      domain_hint: "planning",
      risk_hint: "governed_handoff",
      attributes: {},
    },
    reason:
      "Execution remains approval-bounded. This approval draft is artifact-only and must be explicitly submitted and resolved before any side effect.",
    required_checks: [
      "operator_review_handoff_artifact",
      "submit_governed_approval_request",
      "explicit_approval_resolution",
    ],
    provenance_references: [
      {
        source_kind: "continuity_capture_event",
        source_id: "capture-priority-fixture-1",
      },
    ],
  },
  execution_posture: {
    posture: "approval_bounded_artifact_only",
    approval_required: true,
    autonomous_execution: false,
    external_side_effects_allowed: false,
    default_routing_decision: "approval_required",
    required_operator_actions: [
      "review_handoff_items",
      "submit_task_or_approval_request",
      "resolve_approval_before_execution",
    ],
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    reason: "Chief-of-staff handoff artifacts are deterministic execution-prep only in P8-S29.",
  },
  summary: {
    limit: 12,
    returned_count: 2,
    total_count: 2,
    posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"],
    order: ["score_desc", "created_at_desc", "id_desc"],
    follow_through_posture_order: ["overdue", "stale_waiting_for", "slipped_commitment"],
    follow_through_item_order: [
      "recommendation_action_desc",
      "age_hours_desc",
      "created_at_desc",
      "id_desc",
    ],
    follow_through_total_count: 3,
    overdue_count: 1,
    stale_waiting_for_count: 1,
    slipped_commitment_count: 1,
    trust_confidence_posture: "low",
    trust_confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    quality_gate_status: "insufficient_sample",
    retrieval_status: "pass",
    handoff_item_count: 1,
    handoff_item_order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
    execution_posture_order: ["approval_bounded_artifact_only"],
    handoff_queue_total_count: 1,
    handoff_queue_ready_count: 1,
    handoff_queue_pending_approval_count: 0,
    handoff_queue_executed_count: 0,
    handoff_queue_stale_count: 0,
    handoff_queue_expired_count: 0,
    handoff_queue_state_order: ["ready", "pending_approval", "executed", "stale", "expired"],
    handoff_queue_group_order: ["ready", "pending_approval", "executed", "stale", "expired"],
    handoff_queue_item_order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
  },
  sources: [
    "continuity_recall",
    "continuity_open_loops",
    "continuity_resumption_brief",
    "chief_of_staff_action_handoff",
    "chief_of_staff_handoff_queue",
    "chief_of_staff_handoff_review_actions",
    "chief_of_staff_execution_routing",
    "memory_trust_dashboard",
  ],
};

export default async function ChiefOfStaffPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const query = normalizeParam(params.query);
  const threadId = normalizeParam(params.thread_id);
  const taskId = normalizeParam(params.task_id);
  const project = normalizeParam(params.project);
  const person = normalizeParam(params.person);
  const since = normalizeParam(params.since);
  const until = normalizeParam(params.until);
  const limit = parseNonNegativeInt(normalizeParam(params.limit), 12);

  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let brief = chiefOfStaffFixture;
  let briefSource: ApiSource = "fixture";
  let briefUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await getChiefOfStaffPriorityBrief(apiConfig.apiBaseUrl, apiConfig.userId, {
        query: query || undefined,
        threadId: threadId || undefined,
        taskId: taskId || undefined,
        project: project || undefined,
        person: person || undefined,
        since: since || undefined,
        until: until || undefined,
        limit,
      });
      brief = payload.brief;
      briefSource = "live";
    } catch (error) {
      briefUnavailableReason =
        error instanceof Error ? error.message : "Chief-of-staff brief could not be loaded.";
    }
  }

  const mode = combinePageModes(briefSource);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Phase 8"
        title="Chief-of-staff"
        description="Deterministic priority ranking, follow-through/preparation supervision, weekly review learning, and approval-bounded action handoff artifacts with explicit rationale."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(mode)}</span>
            <span className="subtle-chip">{brief.summary.returned_count} ranked priorities</span>
            <span className="subtle-chip">{brief.summary.follow_through_total_count} follow-through items</span>
            <span className="subtle-chip">{brief.prep_checklist.summary.returned_count} prep checklist items</span>
            <span className="subtle-chip">{brief.summary.handoff_item_count} handoff items</span>
            <span className="subtle-chip">{brief.summary.handoff_queue_ready_count} ready queue items</span>
            <StatusBadge
              status={brief.summary.trust_confidence_posture}
              label={`${brief.summary.trust_confidence_posture} confidence`}
            />
          </div>
        }
      />

      <ChiefOfStaffPriorityPanel
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffFollowThroughPanel
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffPreparationPanel
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffWeeklyReviewPanel
        apiBaseUrl={briefSource === "live" ? apiConfig.apiBaseUrl : undefined}
        userId={briefSource === "live" ? apiConfig.userId : undefined}
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffActionHandoffPanel
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffHandoffQueuePanel
        apiBaseUrl={briefSource === "live" ? apiConfig.apiBaseUrl : undefined}
        userId={briefSource === "live" ? apiConfig.userId : undefined}
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffExecutionRoutingPanel
        apiBaseUrl={briefSource === "live" ? apiConfig.apiBaseUrl : undefined}
        userId={briefSource === "live" ? apiConfig.userId : undefined}
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
    </div>
  );
}
