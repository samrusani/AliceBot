import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ChiefOfStaffPriorityBrief } from "../lib/api";
import { ChiefOfStaffHandoffQueuePanel } from "./chief-of-staff-handoff-queue-panel";

const { captureChiefOfStaffHandoffReviewActionMock } = vi.hoisted(() => ({
  captureChiefOfStaffHandoffReviewActionMock: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    captureChiefOfStaffHandoffReviewAction: captureChiefOfStaffHandoffReviewActionMock,
  };
});

const briefFixture = {
  scope: {
    thread_id: "thread-1",
    task_id: null,
    project: null,
    person: null,
  },
  handoff_queue_summary: {
    total_count: 1,
    ready_count: 1,
    pending_approval_count: 0,
    executed_count: 0,
    stale_count: 0,
    expired_count: 0,
    state_order: ["ready", "pending_approval", "executed", "stale", "expired"] as const,
    group_order: ["ready", "pending_approval", "executed", "stale", "expired"] as const,
    item_order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
    review_action_order: ["mark_ready", "mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"] as const,
  },
  handoff_queue_groups: {
    ready: {
      items: [
        {
          queue_rank: 1,
          handoff_rank: 1,
          handoff_item_id: "handoff-1",
          lifecycle_state: "ready",
          state_reason: "Handoff item is ready for explicit operator review.",
          source_kind: "recommended_next_action",
          source_reference_id: "priority-1",
          title: "Next Action: Ship dashboard",
          recommendation_action: "execute_next_action",
          priority_posture: "urgent",
          confidence_posture: "low",
          score: 1650,
          age_hours_relative_to_latest: 0,
          review_action_order: ["mark_ready", "mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"] as const,
          available_review_actions: ["mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"] as const,
          last_review_action: null,
          provenance_references: [],
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
} as const;

describe("ChiefOfStaffHandoffQueuePanel", () => {
  beforeEach(() => {
    captureChiefOfStaffHandoffReviewActionMock.mockReset();
    captureChiefOfStaffHandoffReviewActionMock.mockResolvedValue({
      review_action: {
        id: "review-1",
        capture_event_id: "capture-review-1",
        handoff_item_id: "handoff-1",
        review_action: "mark_stale",
        previous_lifecycle_state: "ready",
        next_lifecycle_state: "stale",
        reason: "Operator review action moved queue posture to stale.",
        note: null,
        provenance_references: [],
        created_at: "2026-04-01T09:00:00Z",
        updated_at: "2026-04-01T09:00:00Z",
      },
      handoff_queue_summary: {
        ...briefFixture.handoff_queue_summary,
        ready_count: 0,
        stale_count: 1,
      },
      handoff_queue_groups: {
        ...briefFixture.handoff_queue_groups,
        ready: {
          ...briefFixture.handoff_queue_groups.ready,
          items: [],
          summary: {
            ...briefFixture.handoff_queue_groups.ready.summary,
            returned_count: 0,
            total_count: 0,
          },
          empty_state: {
            is_empty: true,
            message: "No ready handoff items for this scope.",
          },
        },
        stale: {
          ...briefFixture.handoff_queue_groups.stale,
          items: [
            {
              ...briefFixture.handoff_queue_groups.ready.items[0],
              lifecycle_state: "stale",
              state_reason: "Latest operator review action 'mark_stale' set lifecycle state to 'stale'.",
              available_review_actions: ["mark_ready", "mark_pending_approval", "mark_executed", "mark_expired"],
            },
          ],
          summary: {
            ...briefFixture.handoff_queue_groups.stale.summary,
            returned_count: 1,
            total_count: 1,
          },
          empty_state: {
            is_empty: false,
            message: "No stale handoff items are currently surfaced.",
          },
        },
      },
      handoff_review_actions: [
        {
          id: "review-1",
          capture_event_id: "capture-review-1",
          handoff_item_id: "handoff-1",
          review_action: "mark_stale",
          previous_lifecycle_state: "ready",
          next_lifecycle_state: "stale",
          reason: "Operator review action moved queue posture to stale.",
          note: null,
          provenance_references: [],
          created_at: "2026-04-01T09:00:00Z",
          updated_at: "2026-04-01T09:00:00Z",
        },
      ],
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders deterministic grouped handoff queue posture", () => {
    render(
      <ChiefOfStaffHandoffQueuePanel
        brief={briefFixture as unknown as ChiefOfStaffPriorityBrief}
        source="fixture"
      />,
    );

    expect(screen.getByText("Fixture handoff queue")).toBeInTheDocument();
    expect(screen.getByText("ready (1)")).toBeInTheDocument();
    expect(screen.getByText("Next Action: Ship dashboard")).toBeInTheDocument();
    expect(screen.getByText("Review action history")).toBeInTheDocument();
    expect(
      screen.getByText("No explicit handoff review actions captured for this scope."),
    ).toBeInTheDocument();
  });

  it("submits explicit review actions in live mode and updates queue posture", async () => {
    render(
      <ChiefOfStaffHandoffQueuePanel
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        brief={briefFixture as unknown as ChiefOfStaffPriorityBrief}
        source="live"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Mark stale" }));

    await waitFor(() => {
      expect(captureChiefOfStaffHandoffReviewActionMock).toHaveBeenCalledWith(
        "https://api.example.com",
        expect.objectContaining({
          user_id: "user-1",
          handoff_item_id: "handoff-1",
          review_action: "mark_stale",
          thread_id: "thread-1",
        }),
      );
    });

    expect(screen.getByText("Applied mark_stale to handoff-1.")).toBeInTheDocument();
    expect(screen.getByText("Operator review action moved queue posture to stale.")).toBeInTheDocument();
  });
});
