import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChiefOfStaffPreparationPanel } from "./chief-of-staff-preparation-panel";

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
    content: {
      subject: "",
      body: "",
    },
  },
  recommended_next_action: {
    action_type: "execute_next_action" as const,
    title: "Next Action: Ship dashboard",
    target_priority_id: "priority-1",
    priority_posture: "urgent" as const,
    confidence_posture: "low" as const,
    reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
    provenance_references: [
      {
        source_kind: "continuity_capture_event",
        source_id: "capture-1",
      },
    ],
    deterministic_rank_key: "1:priority-1:640.000000",
  },
  preparation_brief: {
    scope: { thread_id: "thread-1", since: null, until: null },
    context_items: [
      {
        rank: 1,
        id: "context-1",
        capture_event_id: "capture-context-1",
        object_type: "Decision" as const,
        status: "active",
        title: "Decision: Keep launch staged",
        reason: "Decision context carried forward for deterministic meeting prep.",
        confidence_posture: "low" as const,
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-context-1",
          },
        ],
        created_at: "2026-03-31T08:00:00Z",
      },
    ],
    last_decision: {
      rank: 1,
      id: "decision-1",
      capture_event_id: "capture-decision-1",
      object_type: "Decision" as const,
      status: "active",
      title: "Decision: Keep launch staged",
      reason: "Latest scoped decision included to ground upcoming preparation context.",
      confidence_posture: "low" as const,
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-decision-1",
        },
      ],
      created_at: "2026-03-31T08:00:00Z",
    },
    open_loops: [],
    next_action: null,
    confidence_posture: "low" as const,
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
        id: "change-1",
        capture_event_id: "capture-change-1",
        object_type: "NextAction" as const,
        status: "active",
        title: "Next Action: Publish launch notes",
        reason: "Included from deterministic continuity recent-changes ordering.",
        confidence_posture: "low" as const,
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-change-1",
          },
        ],
        created_at: "2026-03-31T09:00:00Z",
      },
    ],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
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
        id: "checklist-1",
        capture_event_id: "capture-checklist-1",
        object_type: "WaitingFor" as const,
        status: "active",
        title: "Waiting For: Security review",
        reason: "Prepare a status check and explicit owner for this unresolved open loop.",
        confidence_posture: "low" as const,
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-checklist-1",
          },
        ],
        created_at: "2026-03-31T07:30:00Z",
      },
    ],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
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
        id: "talking-1",
        capture_event_id: "capture-talking-1",
        object_type: "Blocker" as const,
        status: "active",
        title: "Blocker: Missing launch credential",
        reason: "Raise this unresolved dependency explicitly and confirm a concrete follow-up path.",
        confidence_posture: "low" as const,
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-talking-1",
          },
        ],
        created_at: "2026-03-31T06:30:00Z",
      },
    ],
    confidence_posture: "low" as const,
    confidence_reason: "Memory quality posture is weak.",
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
        action: "execute_next_action" as const,
        title: "Next Action: Publish launch notes",
        reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
        confidence_posture: "low" as const,
        target_priority_id: "priority-1",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-1",
          },
        ],
      },
      {
        rank: 2,
        action: "review_scope" as const,
        title: "Calibrate recommendation confidence before execution",
        reason:
          "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
        confidence_posture: "low" as const,
        target_priority_id: null,
        provenance_references: [],
      },
    ],
    confidence_posture: "low" as const,
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
    scope: { thread_id: "thread-1", since: null, until: null },
    rollup: {
      total_count: 1,
      waiting_for_count: 0,
      blocker_count: 1,
      stale_count: 0,
      correction_recurrence_count: 0,
      freshness_drift_count: 0,
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
  summary: {
    limit: 10,
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
  },
  sources: ["continuity_recall", "memory_trust_dashboard"],
};

describe("ChiefOfStaffPreparationPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders deterministic preparation artifacts with rationale and provenance", () => {
    render(<ChiefOfStaffPreparationPanel brief={briefFixture} source="live" />);

    expect(screen.getByText("Live preparation brief")).toBeInTheDocument();
    expect(screen.getByText("Preparation context")).toBeInTheDocument();
    expect(screen.getByText("What changed")).toBeInTheDocument();
    expect(screen.getByText("Prep checklist")).toBeInTheDocument();
    expect(screen.getByText("Suggested talking points")).toBeInTheDocument();
    expect(screen.getByText("Resumption supervision")).toBeInTheDocument();
    expect(screen.getByText("Decision: Keep launch staged")).toBeInTheDocument();
    expect(screen.getByText("Provenance: continuity_capture_event:capture-context-1")).toBeInTheDocument();
    expect(screen.getByText("Calibrate recommendation confidence before execution")).toBeInTheDocument();
  });

  it("renders explicit fallback when brief payload is absent", () => {
    render(<ChiefOfStaffPreparationPanel brief={null} source="fixture" />);

    expect(screen.getByText("Preparation unavailable")).toBeInTheDocument();
  });
});
