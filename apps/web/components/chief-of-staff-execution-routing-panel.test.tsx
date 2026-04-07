import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChiefOfStaffPriorityBrief } from "../lib/api";
import { ChiefOfStaffExecutionRoutingPanel } from "./chief-of-staff-execution-routing-panel";

const { captureChiefOfStaffExecutionRoutingActionMock } = vi.hoisted(() => ({
  captureChiefOfStaffExecutionRoutingActionMock: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    captureChiefOfStaffExecutionRoutingAction: captureChiefOfStaffExecutionRoutingActionMock,
  };
});

const briefFixture = {
  scope: {
    thread_id: "thread-1",
    task_id: null,
    project: null,
    person: null,
  },
  execution_routing_summary: {
    total_handoff_count: 1,
    routed_handoff_count: 0,
    unrouted_handoff_count: 1,
    task_workflow_draft_count: 0,
    approval_workflow_draft_count: 0,
    follow_up_draft_only_count: 0,
    route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"] as const,
    routed_item_order: ["handoff_rank_asc", "handoff_item_id_asc"],
    audit_order: ["created_at_desc", "id_desc"],
    transition_order: ["routed", "reaffirmed"] as const,
    approval_required: true,
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    reason: "Routing transitions are explicit and auditable.",
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
  routing_audit_trail: [],
  execution_readiness_posture: {
    posture: "approval_required_draft_only",
    approval_required: true,
    autonomous_execution: false,
    external_side_effects_allowed: false,
    approval_path_visible: true,
    route_target_order: ["task_workflow_draft", "approval_workflow_draft", "follow_up_draft_only"] as const,
    required_route_targets: ["task_workflow_draft", "approval_workflow_draft"] as const,
    transition_order: ["routed", "reaffirmed"] as const,
    non_autonomous_guarantee:
      "No task, approval, connector send, or external side effect is executed by this endpoint.",
    reason: "Execution routing remains draft-only.",
  },
} as const;

describe("ChiefOfStaffExecutionRoutingPanel", () => {
  beforeEach(() => {
    captureChiefOfStaffExecutionRoutingActionMock.mockReset();
    captureChiefOfStaffExecutionRoutingActionMock.mockResolvedValue({
      routing_action: {
        id: "routing-1",
        capture_event_id: "capture-routing-1",
        handoff_item_id: "handoff-1",
        route_target: "task_workflow_draft",
        transition: "routed",
        previously_routed: false,
        route_state: true,
        reason: "Operator routed handoff.",
        note: null,
        provenance_references: [],
        created_at: "2026-04-01T09:30:00Z",
        updated_at: "2026-04-01T09:30:00Z",
      },
      execution_routing_summary: {
        ...briefFixture.execution_routing_summary,
        routed_handoff_count: 1,
        unrouted_handoff_count: 0,
        task_workflow_draft_count: 1,
      },
      routed_handoff_items: [
        {
          ...briefFixture.routed_handoff_items[0],
          routed_targets: ["task_workflow_draft"],
          is_routed: true,
          task_workflow_draft_routed: true,
          last_routing_transition: {
            id: "routing-1",
            capture_event_id: "capture-routing-1",
            handoff_item_id: "handoff-1",
            route_target: "task_workflow_draft",
            transition: "routed",
            previously_routed: false,
            route_state: true,
            reason: "Operator routed handoff.",
            note: null,
            provenance_references: [],
            created_at: "2026-04-01T09:30:00Z",
            updated_at: "2026-04-01T09:30:00Z",
          },
        },
      ],
      routing_audit_trail: [
        {
          id: "routing-1",
          capture_event_id: "capture-routing-1",
          handoff_item_id: "handoff-1",
          route_target: "task_workflow_draft",
          transition: "routed",
          previously_routed: false,
          route_state: true,
          reason: "Operator routed handoff.",
          note: null,
          provenance_references: [],
          created_at: "2026-04-01T09:30:00Z",
          updated_at: "2026-04-01T09:30:00Z",
        },
      ],
      execution_readiness_posture: briefFixture.execution_readiness_posture,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders deterministic execution routing posture and controls", () => {
    render(
      <ChiefOfStaffExecutionRoutingPanel
        brief={briefFixture as unknown as ChiefOfStaffPriorityBrief}
        source="fixture"
      />,
    );

    expect(screen.getByText("Fixture execution routing")).toBeInTheDocument();
    expect(screen.getByText("Execution readiness posture")).toBeInTheDocument();
    expect(screen.getByText("Routed handoff items")).toBeInTheDocument();
    expect(screen.getByText("No execution routing transitions captured for this scope.")).toBeInTheDocument();
  });

  it("submits execution routing actions in live mode and updates audit trail", async () => {
    render(
      <ChiefOfStaffExecutionRoutingPanel
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        brief={briefFixture as unknown as ChiefOfStaffPriorityBrief}
        source="live"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Route task draft" }));

    await waitFor(() => {
      expect(captureChiefOfStaffExecutionRoutingActionMock).toHaveBeenCalledWith(
        "https://api.example.com",
        expect.objectContaining({
          user_id: "user-1",
          handoff_item_id: "handoff-1",
          route_target: "task_workflow_draft",
          thread_id: "thread-1",
        }),
      );
    });

    expect(screen.getByText("Routed handoff-1 -> task_workflow_draft.")).toBeInTheDocument();
    expect(screen.getByText("Operator routed handoff.")).toBeInTheDocument();
  });
});
