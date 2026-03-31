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
  },
  sources: ["continuity_recall", "memory_trust_dashboard"],
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
