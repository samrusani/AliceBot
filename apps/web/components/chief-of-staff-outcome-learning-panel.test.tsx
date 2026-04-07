import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChiefOfStaffPriorityBrief } from "../lib/api";
import { ChiefOfStaffOutcomeLearningPanel } from "./chief-of-staff-outcome-learning-panel";

const { captureChiefOfStaffHandoffOutcomeMock } = vi.hoisted(() => ({
  captureChiefOfStaffHandoffOutcomeMock: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    captureChiefOfStaffHandoffOutcome: captureChiefOfStaffHandoffOutcomeMock,
  };
});

const briefFixture = {
  scope: {
    thread_id: "thread-1",
    task_id: null,
    project: null,
    person: null,
  },
  routed_handoff_items: [
    {
      handoff_rank: 1,
      handoff_item_id: "handoff-1",
      title: "Next Action: Ship dashboard",
      source_kind: "recommended_next_action",
      recommendation_action: "execute_next_action",
      route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"] as const,
      available_route_targets: ["task_workflow_draft", "approval_workflow_draft"] as const,
      routed_targets: ["task_workflow_draft"] as const,
      is_routed: true,
      task_workflow_draft_routed: true,
      approval_workflow_draft_routed: false,
      follow_up_draft_only_routed: false,
      follow_up_draft_only_applicable: false,
      task_draft: {
        status: "draft",
        mode: "governed_request_draft",
        approval_required: true,
        auto_execute: false,
        source_handoff_item_id: "handoff-1",
        title: "Next Action: Ship dashboard",
        summary: "Draft-only governed request.",
        target: { thread_id: "thread-1", task_id: null, project: null, person: null },
        request: {
          action: "execute_next_action",
          scope: "chief_of_staff_priority",
          domain_hint: "planning",
          risk_hint: "governed_handoff",
          attributes: {},
        },
        rationale: "fixture rationale",
        provenance_references: [],
      },
      approval_draft: {
        status: "draft_only",
        mode: "approval_request_draft",
        decision: "approval_required",
        approval_required: true,
        auto_submit: false,
        source_handoff_item_id: "handoff-1",
        request: {
          action: "execute_next_action",
          scope: "chief_of_staff_priority",
          domain_hint: "planning",
          risk_hint: "governed_handoff",
          attributes: {},
        },
        reason: "approval required",
        required_checks: ["operator_review_handoff_artifact"],
        provenance_references: [],
      },
      last_routing_transition: null,
    },
  ],
  handoff_outcome_summary: {
    returned_count: 0,
    total_count: 0,
    latest_total_count: 0,
    status_counts: {
      reviewed: 0,
      approved: 0,
      rejected: 0,
      rewritten: 0,
      executed: 0,
      ignored: 0,
      expired: 0,
    },
    latest_status_counts: {
      reviewed: 0,
      approved: 0,
      rejected: 0,
      rewritten: 0,
      executed: 0,
      ignored: 0,
      expired: 0,
    },
    status_order: ["reviewed", "approved", "rejected", "rewritten", "executed", "ignored", "expired"] as const,
    order: ["created_at_desc", "id_desc"],
  },
  handoff_outcomes: [],
  closure_quality_summary: {
    posture: "insufficient_signal",
    reason: "No handoff outcomes are captured yet, so closure quality remains informational.",
    closed_loop_count: 0,
    unresolved_count: 0,
    rejected_count: 0,
    ignored_count: 0,
    expired_count: 0,
    closure_rate: 0,
    explanation: "Closure quality uses the latest immutable outcome per handoff item.",
  },
  conversion_signal_summary: {
    total_handoff_count: 1,
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
    explanation: "Conversion signals are derived from latest immutable outcomes.",
  },
  stale_ignored_escalation_posture: {
    posture: "watch",
    reason: "No stale queue pressure or ignored/expired latest outcomes are currently detected.",
    stale_queue_count: 0,
    ignored_count: 0,
    expired_count: 0,
    trigger_count: 0,
    guidance_posture_explanation: "Guidance posture is derived from stale queue load plus ignored/expired outcomes.",
    supporting_signals: ["stale_queue_count=0", "ignored_count=0", "expired_count=0", "trigger_count=0"],
  },
} as const;

describe("ChiefOfStaffOutcomeLearningPanel", () => {
  beforeEach(() => {
    captureChiefOfStaffHandoffOutcomeMock.mockReset();
    captureChiefOfStaffHandoffOutcomeMock.mockResolvedValue({
      handoff_outcome: {
        id: "handoff-outcome-1",
        capture_event_id: "capture-handoff-outcome-1",
        handoff_item_id: "handoff-1",
        outcome_status: "executed",
        previous_outcome_status: null,
        is_latest_outcome: true,
        reason: "Operator captured routed handoff outcome 'executed' for 'handoff-1'.",
        note: null,
        provenance_references: [],
        created_at: "2026-04-07T09:30:00Z",
        updated_at: "2026-04-07T09:30:00Z",
      },
      handoff_outcome_summary: {
        ...briefFixture.handoff_outcome_summary,
        returned_count: 1,
        total_count: 1,
        latest_total_count: 1,
        status_counts: {
          ...briefFixture.handoff_outcome_summary.status_counts,
          executed: 1,
        },
        latest_status_counts: {
          ...briefFixture.handoff_outcome_summary.latest_status_counts,
          executed: 1,
        },
      },
      handoff_outcomes: [
        {
          id: "handoff-outcome-1",
          capture_event_id: "capture-handoff-outcome-1",
          handoff_item_id: "handoff-1",
          outcome_status: "executed",
          previous_outcome_status: null,
          is_latest_outcome: true,
          reason: "Operator captured routed handoff outcome 'executed' for 'handoff-1'.",
          note: null,
          provenance_references: [],
          created_at: "2026-04-07T09:30:00Z",
          updated_at: "2026-04-07T09:30:00Z",
        },
      ],
      closure_quality_summary: {
        posture: "healthy",
        reason: "Closed-loop outcomes are leading with bounded unresolved and ignored outcomes.",
        closed_loop_count: 1,
        unresolved_count: 0,
        rejected_count: 0,
        ignored_count: 0,
        expired_count: 0,
        closure_rate: 1,
        explanation: "Closure quality uses latest immutable outcomes.",
      },
      conversion_signal_summary: {
        ...briefFixture.conversion_signal_summary,
        latest_outcome_count: 1,
        executed_count: 1,
        recommendation_to_execution_conversion_rate: 1,
        recommendation_to_closure_conversion_rate: 1,
        capture_coverage_rate: 1,
      },
      stale_ignored_escalation_posture: briefFixture.stale_ignored_escalation_posture,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders deterministic outcome-learning artifacts and controls", () => {
    render(
      <ChiefOfStaffOutcomeLearningPanel
        brief={briefFixture as unknown as ChiefOfStaffPriorityBrief}
        source="fixture"
      />,
    );

    expect(screen.getByText("Fixture outcome learning")).toBeInTheDocument();
    expect(screen.getByText("Routed handoff outcome capture controls")).toBeInTheDocument();
    expect(screen.getByText("Closure quality summary")).toBeInTheDocument();
    expect(screen.getByText("No handoff outcomes captured for this scope.")).toBeInTheDocument();
  });

  it("captures routed handoff outcomes in live mode and updates summaries", async () => {
    render(
      <ChiefOfStaffOutcomeLearningPanel
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        brief={briefFixture as unknown as ChiefOfStaffPriorityBrief}
        source="live"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Executed" }));

    await waitFor(() => {
      expect(captureChiefOfStaffHandoffOutcomeMock).toHaveBeenCalledWith(
        "https://api.example.com",
        expect.objectContaining({
          user_id: "user-1",
          handoff_item_id: "handoff-1",
          outcome_status: "executed",
          thread_id: "thread-1",
        }),
      );
    });

    expect(screen.getByText("Captured executed for handoff-1.")).toBeInTheDocument();
    expect(screen.getByText("Operator captured routed handoff outcome 'executed' for 'handoff-1'.")).toBeInTheDocument();
  });
});
