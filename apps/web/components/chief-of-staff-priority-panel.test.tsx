import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChiefOfStaffPriorityPanel } from "./chief-of-staff-priority-panel";

const briefFixture = {
  assembly_version: "chief_of_staff_priority_brief_v0",
  scope: {
    thread_id: "thread-1",
    since: null,
    until: null,
  },
  ranked_items: [
    {
      rank: 1,
      id: "priority-1",
      capture_event_id: "capture-1",
      object_type: "NextAction" as const,
      status: "active",
      title: "Next Action: Ship dashboard",
      priority_posture: "urgent" as const,
      confidence_posture: "low" as const,
      confidence: 1,
      score: 640,
      provenance: {
        thread_id: "thread-1",
      },
      created_at: "2026-03-31T10:00:00Z",
      updated_at: "2026-03-31T10:00:00Z",
      rationale: {
        reasons: [
          "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
          "Confidence is explicitly downgraded by current memory trust posture.",
        ],
        ranking_inputs: {
          posture: "urgent" as const,
          open_loop_posture: "next_action" as const,
          recency_rank: 1,
          age_hours_relative_to_latest: 0,
          recall_relevance: 120,
          scope_match_count: 1,
          query_term_match_count: 1,
          freshness_posture: "fresh" as const,
          provenance_posture: "strong" as const,
          supersession_posture: "current" as const,
        },
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-1",
          },
        ],
        trust_signals: {
          quality_gate_status: "insufficient_sample" as const,
          retrieval_status: "pass" as const,
          trust_confidence_cap: "low" as const,
          downgraded_by_trust: true,
          reason: "Memory quality posture is weak.",
        },
      },
    },
  ],
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
    returned_count: 1,
    total_count: 1,
    posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"] as const,
    order: ["score_desc", "created_at_desc", "id_desc"],
    follow_through_posture_order: ["overdue", "stale_waiting_for", "slipped_commitment"] as const,
    follow_through_item_order: [
      "recommendation_action_desc",
      "age_hours_desc",
      "created_at_desc",
      "id_desc",
    ],
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

describe("ChiefOfStaffPriorityPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders ranked priorities, rationale, and explicit low-trust confidence downgrade", () => {
    render(<ChiefOfStaffPriorityPanel brief={briefFixture} source="live" />);

    expect(screen.getByText("Live chief-of-staff brief")).toBeInTheDocument();
    expect(screen.getByText("Recommended next action")).toBeInTheDocument();
    expect(screen.getAllByText("Next Action: Ship dashboard").length).toBeGreaterThan(0);
    expect(screen.getByText("Action type: execute_next_action")).toBeInTheDocument();
    expect(
      screen.getByText("Confidence is explicitly downgraded because memory trust posture is weak."),
    ).toBeInTheDocument();
    expect(screen.getByText("Rank #1")).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
      ).length,
    ).toBeGreaterThan(0);
  });

  it("renders explicit fallback when brief payload is absent", () => {
    render(<ChiefOfStaffPriorityPanel brief={null} source="fixture" />);

    expect(screen.getByText("Chief-of-staff brief unavailable")).toBeInTheDocument();
  });
});
