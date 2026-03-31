import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChiefOfStaffFollowThroughPanel } from "./chief-of-staff-follow-through-panel";

const briefFixture = {
  assembly_version: "chief_of_staff_priority_brief_v0",
  scope: {
    thread_id: "thread-1",
    since: null,
    until: null,
  },
  ranked_items: [],
  overdue_items: [
    {
      rank: 1,
      id: "next-overdue-1",
      capture_event_id: "capture-next-overdue-1",
      object_type: "NextAction" as const,
      status: "active",
      title: "Next Action: Send client follow-up",
      current_priority_posture: "urgent" as const,
      follow_through_posture: "overdue" as const,
      recommendation_action: "escalate" as const,
      reason: "Execution follow-through is overdue (posture=urgent, age=140.0h), so action 'escalate' is recommended.",
      age_hours: 140,
      provenance_references: [
        {
          source_kind: "continuity_capture_event" as const,
          source_id: "capture-next-overdue-1",
        },
      ],
      created_at: "2026-03-26T08:00:00Z",
      updated_at: "2026-03-26T08:00:00Z",
    },
  ],
  stale_waiting_for_items: [
    {
      rank: 1,
      id: "waiting-stale-1",
      capture_event_id: "capture-waiting-stale-1",
      object_type: "WaitingFor" as const,
      status: "stale",
      title: "Waiting For: Security review",
      current_priority_posture: "stale" as const,
      follow_through_posture: "stale_waiting_for" as const,
      recommendation_action: "nudge" as const,
      reason: "Waiting-for item is stale (status=stale, age=96.0h from latest scoped item), so action 'nudge' is recommended.",
      age_hours: 96,
      provenance_references: [
        {
          source_kind: "continuity_capture_event" as const,
          source_id: "capture-waiting-stale-1",
        },
      ],
      created_at: "2026-03-27T00:00:00Z",
      updated_at: "2026-03-27T00:00:00Z",
    },
  ],
  slipped_commitments: [
    {
      rank: 1,
      id: "commitment-slip-1",
      capture_event_id: "capture-commitment-slip-1",
      object_type: "Commitment" as const,
      status: "active",
      title: "Commitment: Ship status report",
      current_priority_posture: "important" as const,
      follow_through_posture: "slipped_commitment" as const,
      recommendation_action: "defer" as const,
      reason: "Commitment is slipping (status=active, age=60.0h from latest scoped item), so action 'defer' is recommended.",
      age_hours: 60,
      provenance_references: [
        {
          source_kind: "continuity_capture_event" as const,
          source_id: "capture-commitment-slip-1",
        },
      ],
      created_at: "2026-03-28T12:00:00Z",
      updated_at: "2026-03-28T12:00:00Z",
    },
  ],
  escalation_posture: {
    posture: "critical" as const,
    reason: "At least one follow-through item requires escalation.",
    total_follow_through_count: 3,
    nudge_count: 1,
    defer_count: 1,
    escalate_count: 1,
    close_loop_candidate_count: 0,
  },
  draft_follow_up: {
    status: "drafted" as const,
    mode: "draft_only" as const,
    approval_required: true,
    auto_send: false,
    reason: "Highest-severity follow-through item selected deterministically for operator review.",
    target_metadata: {
      continuity_object_id: "next-overdue-1",
      capture_event_id: "capture-next-overdue-1",
      object_type: "NextAction" as const,
      priority_posture: "urgent" as const,
      follow_through_posture: "overdue" as const,
      recommendation_action: "escalate" as const,
      thread_id: "thread-1",
    },
    content: {
      subject: "Follow-up: Next Action: Send client follow-up",
      body: "This draft is artifact-only and requires explicit approval before any external send.",
    },
  },
  recommended_next_action: {
    action_type: "execute_next_action" as const,
    title: "Next Action: Send client follow-up",
    target_priority_id: "next-overdue-1",
    priority_posture: "urgent" as const,
    confidence_posture: "low" as const,
    reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
    provenance_references: [
      {
        source_kind: "continuity_capture_event" as const,
        source_id: "capture-next-overdue-1",
      },
    ],
    deterministic_rank_key: "1:next-overdue-1:640.000000",
  },
  preparation_brief: {
    scope: { thread_id: "thread-1", since: null, until: null },
    context_items: [],
    last_decision: null,
    open_loops: [],
    next_action: null,
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: {
      limit: 6,
      returned_count: 0,
      total_count: 0,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  what_changed_summary: {
    items: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: {
      limit: 6,
      returned_count: 0,
      total_count: 0,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  prep_checklist: {
    items: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: {
      limit: 6,
      returned_count: 0,
      total_count: 0,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  suggested_talking_points: {
    items: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: {
      limit: 6,
      returned_count: 0,
      total_count: 0,
      order: ["rank_asc", "created_at_desc", "id_desc"],
    },
  },
  resumption_supervision: {
    recommendations: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: {
      limit: 3,
      returned_count: 0,
      total_count: 0,
      order: ["rank_asc"],
    },
  },
  weekly_review_brief: {
    scope: { thread_id: "thread-1", since: null, until: null },
    rollup: {
      total_count: 3,
      waiting_for_count: 1,
      blocker_count: 1,
      stale_count: 1,
      correction_recurrence_count: 0,
      freshness_drift_count: 1,
      next_action_count: 1,
      posture_order: ["waiting_for", "blocker", "stale", "next_action"] as const,
    },
    guidance: [],
    summary: {
      guidance_order: ["close", "defer", "escalate"] as const,
      guidance_item_order: ["signal_count_desc", "action_desc"],
    },
  },
  recommendation_outcomes: {
    items: [],
    summary: {
      returned_count: 0,
      total_count: 0,
      outcome_counts: { accept: 0, defer: 0, ignore: 0, rewrite: 0 },
      order: ["created_at_desc", "id_desc"],
    },
  },
  priority_learning_summary: {
    total_count: 0,
    accept_count: 0,
    defer_count: 0,
    ignore_count: 0,
    rewrite_count: 0,
    acceptance_rate: 0,
    override_rate: 0,
    defer_hotspots: [],
    ignore_hotspots: [],
    priority_shift_explanation:
      "No recommendation outcomes are captured yet; prioritization remains anchored to current continuity and trust signals.",
    hotspot_order: ["count_desc", "key_asc"],
  },
  pattern_drift_summary: {
    posture: "insufficient_signal" as const,
    reason: "No recommendation outcomes are available yet, so drift posture is informational only.",
    supporting_signals: [],
  },
  action_handoff_brief: {
    summary:
      "Prepared 1 deterministic handoff item from recommended_next_action signals. All task and approval drafts remain artifact-only and approval-bounded.",
    confidence_posture: "low" as const,
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
    source_order: ["recommended_next_action", "follow_through", "prep_checklist", "weekly_review"] as const,
    provenance_references: [],
  },
  handoff_items: [],
  task_draft: {
    status: "draft" as const,
    mode: "governed_request_draft" as const,
    approval_required: true,
    auto_execute: false,
    source_handoff_item_id: "handoff-1-recommended_next_action-next-overdue-1",
    title: "Next Action: Send client follow-up",
    summary:
      "Draft-only governed request assembled from chief-of-staff handoff artifacts; requires explicit approval before any execution.",
    target: { thread_id: "thread-1", task_id: null, project: null, person: null },
    request: {
      action: "execute_next_action",
      scope: "chief_of_staff_priority",
      domain_hint: "planning",
      risk_hint: "governed_handoff",
      attributes: {},
    },
    rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
    provenance_references: [],
  },
  approval_draft: {
    status: "draft_only" as const,
    mode: "approval_request_draft" as const,
    decision: "approval_required" as const,
    approval_required: true,
    auto_submit: false,
    source_handoff_item_id: "handoff-1-recommended_next_action-next-overdue-1",
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
    provenance_references: [],
  },
  execution_posture: {
    posture: "approval_bounded_artifact_only" as const,
    approval_required: true,
    autonomous_execution: false,
    external_side_effects_allowed: false,
    default_routing_decision: "approval_required" as const,
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
    limit: 10,
    returned_count: 0,
    total_count: 3,
    posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"] as const,
    order: ["score_desc", "created_at_desc", "id_desc"],
    follow_through_posture_order: ["overdue", "stale_waiting_for", "slipped_commitment"] as const,
    follow_through_item_order: ["recommendation_action_desc", "age_hours_desc", "created_at_desc", "id_desc"],
    follow_through_total_count: 3,
    overdue_count: 1,
    stale_waiting_for_count: 1,
    slipped_commitment_count: 1,
    trust_confidence_posture: "low" as const,
    trust_confidence_reason: "Memory quality posture is weak.",
    quality_gate_status: "insufficient_sample" as const,
    retrieval_status: "pass" as const,
    handoff_item_count: 0,
    handoff_item_order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
    execution_posture_order: ["approval_bounded_artifact_only"] as const,
  },
  sources: ["continuity_recall", "memory_trust_dashboard", "chief_of_staff_action_handoff"],
};

describe("ChiefOfStaffFollowThroughPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders escalation, follow-through groups, and draft-only follow-up artifact", () => {
    render(<ChiefOfStaffFollowThroughPanel brief={briefFixture} source="live" />);

    expect(screen.getByText("Live follow-through")).toBeInTheDocument();
    expect(screen.getByText("Escalation: critical")).toBeInTheDocument();
    expect(screen.getByText("Overdue items")).toBeInTheDocument();
    expect(screen.getByText("Stale waiting-for items")).toBeInTheDocument();
    expect(screen.getByText("Slipped commitments")).toBeInTheDocument();
    expect(screen.getByText("Follow-up: Next Action: Send client follow-up")).toBeInTheDocument();
    expect(screen.getByText("Auto send: disabled")).toBeInTheDocument();
    expect(
      screen.getByText("This draft is artifact-only and requires explicit approval before any external send."),
    ).toBeInTheDocument();
  });

  it("renders explicit fallback when brief payload is absent", () => {
    render(<ChiefOfStaffFollowThroughPanel brief={null} source="fixture" />);

    expect(screen.getByText("Follow-through unavailable")).toBeInTheDocument();
  });
});
