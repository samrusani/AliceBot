import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChiefOfStaffActionHandoffPanel } from "./chief-of-staff-action-handoff-panel";

const briefFixture = {
  assembly_version: "chief_of_staff_priority_brief_v0",
  scope: {
    thread_id: "thread-1",
    since: null,
    until: null,
  },
  ranked_items: [],
  overdue_items: [],
  stale_waiting_for_items: [],
  slipped_commitments: [],
  escalation_posture: {
    posture: "watch" as const,
    reason: "No active follow-through escalations are present.",
    total_follow_through_count: 0,
    nudge_count: 0,
    defer_count: 0,
    escalate_count: 0,
    close_loop_candidate_count: 0,
  },
  draft_follow_up: {
    status: "none" as const,
    mode: "draft_only" as const,
    approval_required: true,
    auto_send: false,
    reason: "No follow-through targets are currently queued for drafting.",
    target_metadata: {
      continuity_object_id: null,
      capture_event_id: null,
      object_type: null,
      priority_posture: null,
      follow_through_posture: null,
      recommendation_action: null,
      thread_id: "thread-1",
    },
    content: { subject: "", body: "" },
  },
  recommended_next_action: {
    action_type: "execute_next_action" as const,
    title: "Next Action: Ship dashboard",
    target_priority_id: "priority-1",
    priority_posture: "urgent" as const,
    confidence_posture: "low" as const,
    reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
    provenance_references: [],
    deterministic_rank_key: "1:priority-1:640.000000",
  },
  preparation_brief: {
    scope: { thread_id: "thread-1", since: null, until: null },
    context_items: [],
    last_decision: null,
    open_loops: [],
    next_action: null,
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: { limit: 6, returned_count: 0, total_count: 0, order: ["rank_asc", "created_at_desc", "id_desc"] },
  },
  what_changed_summary: {
    items: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: { limit: 6, returned_count: 0, total_count: 0, order: ["rank_asc", "created_at_desc", "id_desc"] },
  },
  prep_checklist: {
    items: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: { limit: 6, returned_count: 0, total_count: 0, order: ["rank_asc", "created_at_desc", "id_desc"] },
  },
  suggested_talking_points: {
    items: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: { limit: 6, returned_count: 0, total_count: 0, order: ["rank_asc", "created_at_desc", "id_desc"] },
  },
  resumption_supervision: {
    recommendations: [],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
    summary: { limit: 3, returned_count: 0, total_count: 0, order: ["rank_asc"] },
  },
  weekly_review_brief: {
    scope: { thread_id: "thread-1", since: null, until: null },
    rollup: {
      total_count: 0,
      waiting_for_count: 0,
      blocker_count: 0,
      stale_count: 0,
      correction_recurrence_count: 0,
      freshness_drift_count: 0,
      next_action_count: 0,
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
      "Prepared 2 deterministic handoff items from recommended_next_action, follow_through signals. All task and approval drafts remain artifact-only and approval-bounded.",
    confidence_posture: "low" as const,
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
    source_order: ["recommended_next_action", "follow_through", "prep_checklist", "weekly_review"] as const,
    provenance_references: [],
  },
  handoff_items: [
    {
      rank: 1,
      handoff_item_id: "handoff-1-recommended_next_action-priority-1",
      source_kind: "recommended_next_action" as const,
      source_reference_id: "priority-1",
      title: "Next Action: Ship dashboard",
      recommendation_action: "execute_next_action" as const,
      priority_posture: "urgent" as const,
      confidence_posture: "low" as const,
      rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
      provenance_references: [],
      score: 1650,
      task_draft: {
        status: "draft" as const,
        mode: "governed_request_draft" as const,
        approval_required: true,
        auto_execute: false,
        source_handoff_item_id: "handoff-1-recommended_next_action-priority-1",
        title: "Next Action: Ship dashboard",
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
        source_handoff_item_id: "handoff-1-recommended_next_action-priority-1",
        request: {
          action: "execute_next_action",
          scope: "chief_of_staff_priority",
          domain_hint: "planning",
          risk_hint: "governed_handoff",
          attributes: {},
        },
        reason: "Execution remains approval-bounded.",
        required_checks: ["operator_review_handoff_artifact"],
        provenance_references: [],
      },
    },
  ],
  task_draft: {
    status: "draft" as const,
    mode: "governed_request_draft" as const,
    approval_required: true,
    auto_execute: false,
    source_handoff_item_id: "handoff-1-recommended_next_action-priority-1",
    title: "Next Action: Ship dashboard",
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
    source_handoff_item_id: "handoff-1-recommended_next_action-priority-1",
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
    limit: 12,
    returned_count: 0,
    total_count: 0,
    posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"] as const,
    order: ["score_desc", "created_at_desc", "id_desc"],
    follow_through_posture_order: ["overdue", "stale_waiting_for", "slipped_commitment"] as const,
    follow_through_item_order: ["recommendation_action_desc", "age_hours_desc", "created_at_desc", "id_desc"],
    follow_through_total_count: 0,
    overdue_count: 0,
    stale_waiting_for_count: 0,
    slipped_commitment_count: 0,
    trust_confidence_posture: "low" as const,
    trust_confidence_reason: "Memory quality posture is weak.",
    quality_gate_status: "insufficient_sample" as const,
    retrieval_status: "pass" as const,
    handoff_item_count: 1,
    handoff_item_order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
    execution_posture_order: ["approval_bounded_artifact_only"] as const,
  },
  sources: ["continuity_recall", "memory_trust_dashboard", "chief_of_staff_action_handoff"],
};

describe("ChiefOfStaffActionHandoffPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders deterministic handoff artifacts and approval-bounded execution posture", () => {
    render(<ChiefOfStaffActionHandoffPanel brief={briefFixture} source="live" />);

    expect(screen.getByText("Live action handoff")).toBeInTheDocument();
    expect(screen.getByText("Execution posture: approval_bounded_artifact_only")).toBeInTheDocument();
    expect(screen.getByText("Action handoff brief")).toBeInTheDocument();
    expect(screen.getByText("Primary task draft")).toBeInTheDocument();
    expect(screen.getByText("Primary approval draft")).toBeInTheDocument();
    expect(screen.getByText("Handoff items")).toBeInTheDocument();
    expect(screen.getAllByText("Request: execute_next_action (chief_of_staff_priority)").length).toBeGreaterThan(0);
    expect(
      screen.getByText("No task, approval, connector send, or external side effect is executed by this endpoint."),
    ).toBeInTheDocument();
  });

  it("renders explicit fallback when brief payload is absent", () => {
    render(<ChiefOfStaffActionHandoffPanel brief={null} source="fixture" />);

    expect(screen.getByText("Action handoff unavailable")).toBeInTheDocument();
  });
});
