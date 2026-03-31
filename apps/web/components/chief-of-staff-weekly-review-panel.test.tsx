import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChiefOfStaffWeeklyReviewPanel } from "./chief-of-staff-weekly-review-panel";

const { captureChiefOfStaffRecommendationOutcomeMock } = vi.hoisted(() => ({
  captureChiefOfStaffRecommendationOutcomeMock: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    captureChiefOfStaffRecommendationOutcome: captureChiefOfStaffRecommendationOutcomeMock,
  };
});

const briefFixture = {
  assembly_version: "chief_of_staff_priority_brief_v0",
  scope: { thread_id: "thread-1", since: null, until: null },
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
      total_count: 2,
      waiting_for_count: 1,
      blocker_count: 1,
      stale_count: 0,
      correction_recurrence_count: 0,
      freshness_drift_count: 0,
      next_action_count: 1,
      posture_order: ["waiting_for", "blocker", "stale", "next_action"] as const,
    },
    guidance: [
      {
        rank: 1,
        action: "escalate" as const,
        signal_count: 2,
        rationale: "Escalate where blockers are concentrated.",
      },
      {
        rank: 2,
        action: "close" as const,
        signal_count: 1,
        rationale: "Close loops where deterministic close candidates exist.",
      },
      {
        rank: 3,
        action: "defer" as const,
        signal_count: 1,
        rationale: "Defer where stale load remains.",
      },
    ],
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
    supporting_signals: ["Outcomes captured: 0"],
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

describe("ChiefOfStaffWeeklyReviewPanel", () => {
  beforeEach(() => {
    captureChiefOfStaffRecommendationOutcomeMock.mockReset();
    captureChiefOfStaffRecommendationOutcomeMock.mockResolvedValue({
      outcome: {
        id: "outcome-1",
        capture_event_id: "capture-outcome-1",
        outcome: "accept",
        recommendation_action_type: "execute_next_action",
        recommendation_title: "Next Action: Ship dashboard",
        rewritten_title: null,
        target_priority_id: "priority-1",
        rationale: "Captured from weekly review controls as accept.",
        provenance_references: [],
        created_at: "2026-03-31T12:00:00Z",
        updated_at: "2026-03-31T12:00:00Z",
      },
      recommendation_outcomes: briefFixture.recommendation_outcomes,
      priority_learning_summary: briefFixture.priority_learning_summary,
      pattern_drift_summary: briefFixture.pattern_drift_summary,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders weekly guidance and outcome-learning sections", () => {
    render(
      <ChiefOfStaffWeeklyReviewPanel
        brief={briefFixture}
        source="fixture"
      />,
    );

    expect(screen.getByText("Fixture weekly review")).toBeInTheDocument();
    expect(screen.getByText("Close / Defer / Escalate guidance")).toBeInTheDocument();
    expect(screen.getByText("Outcome capture controls")).toBeInTheDocument();
    expect(screen.getByText("Pattern drift summary")).toBeInTheDocument();
  });

  it("captures accept outcomes when live mode is ready", async () => {
    render(
      <ChiefOfStaffWeeklyReviewPanel
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        brief={briefFixture}
        source="live"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() => {
      expect(captureChiefOfStaffRecommendationOutcomeMock).toHaveBeenCalledWith(
        "https://api.example.com",
        expect.objectContaining({
          user_id: "user-1",
          outcome: "accept",
          recommendation_action_type: "execute_next_action",
        }),
      );
    });

    expect(
      screen.getByText(
        "accept captured. Refresh the page to see updated recommendation outcomes and learning summaries.",
      ),
    ).toBeInTheDocument();
  });

  it("renders explicit fallback when brief payload is absent", () => {
    render(<ChiefOfStaffWeeklyReviewPanel brief={null} source="fixture" />);

    expect(screen.getByText("Weekly review unavailable")).toBeInTheDocument();
  });
});
