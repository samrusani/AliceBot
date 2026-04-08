import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ContinuityOpenLoopsPanel } from "./continuity-open-loops-panel";

const { applyContinuityOpenLoopReviewActionMock, refreshMock } = vi.hoisted(() => ({
  applyContinuityOpenLoopReviewActionMock: vi.fn(),
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    applyContinuityOpenLoopReviewAction: applyContinuityOpenLoopReviewActionMock,
  };
});

const dashboardFixture = {
  scope: {
    since: null,
    until: null,
  },
  waiting_for: {
    items: [
      {
        id: "object-1",
        capture_event_id: "capture-1",
        object_type: "WaitingFor" as const,
        status: "active",
        title: "Waiting For: Vendor quote",
        body: { waiting_for_text: "Vendor quote" },
        provenance: {},
        confirmation_status: "unconfirmed" as const,
        admission_posture: "DERIVED" as const,
        confidence: 1,
        relevance: 100,
        last_confirmed_at: null,
        supersedes_object_id: null,
        superseded_by_object_id: null,
        scope_matches: [],
        provenance_references: [],
        ordering: {
          scope_match_count: 0,
          query_term_match_count: 0,
          confirmation_rank: 2,
          posture_rank: 2,
          lifecycle_rank: 4,
          confidence: 1,
        },
        created_at: "2026-03-30T10:00:00Z",
        updated_at: "2026-03-30T10:00:00Z",
      },
    ],
    summary: {
      limit: 10,
      returned_count: 1,
      total_count: 1,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: false,
      message: "none",
    },
  },
  blocker: {
    items: [],
    summary: {
      limit: 10,
      returned_count: 0,
      total_count: 0,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No blocker items in the requested scope.",
    },
  },
  stale: {
    items: [],
    summary: {
      limit: 10,
      returned_count: 0,
      total_count: 0,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No stale items in the requested scope.",
    },
  },
  next_action: {
    items: [],
    summary: {
      limit: 10,
      returned_count: 0,
      total_count: 0,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No next-action items in the requested scope.",
    },
  },
  summary: {
    limit: 10,
    total_count: 1,
    posture_order: ["waiting_for", "blocker", "stale", "next_action"] as const,
    item_order: ["created_at_desc", "id_desc"],
  },
  sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
};

describe("ContinuityOpenLoopsPanel", () => {
  beforeEach(() => {
    applyContinuityOpenLoopReviewActionMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders posture groups and submits review actions", async () => {
    applyContinuityOpenLoopReviewActionMock.mockResolvedValue({
      continuity_object: {
        id: "object-1",
        capture_event_id: "capture-1",
        object_type: "WaitingFor",
        status: "completed",
        title: "Waiting For: Vendor quote",
        body: { waiting_for_text: "Vendor quote" },
        provenance: {},
        confidence: 1,
        last_confirmed_at: null,
        supersedes_object_id: null,
        superseded_by_object_id: null,
        created_at: "2026-03-30T10:00:00Z",
        updated_at: "2026-03-30T10:01:00Z",
      },
      correction_event: {
        id: "event-1",
        continuity_object_id: "object-1",
        action: "edit",
        reason: null,
        before_snapshot: {},
        after_snapshot: {},
        payload: { review_action: "done" },
        created_at: "2026-03-30T10:01:00Z",
      },
      review_action: "done",
      lifecycle_outcome: "completed",
    });

    render(
      <ContinuityOpenLoopsPanel
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        dashboard={dashboardFixture}
        source="live"
      />,
    );

    expect(screen.getByText("Live open loops")).toBeInTheDocument();
    expect(screen.getByText("Waiting For: Vendor quote")).toBeInTheDocument();
    expect(screen.getByText("No blocker items in the requested scope.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Done" }));

    await waitFor(() => {
      expect(applyContinuityOpenLoopReviewActionMock).toHaveBeenCalledWith(
        "https://api.example.com",
        "object-1",
        {
          user_id: "user-1",
          action: "done",
        },
      );
    });

    await waitFor(() => {
      expect(refreshMock).toHaveBeenCalled();
    });
    expect(await screen.findByText(/Lifecycle is now completed/i)).toBeInTheDocument();
  });

  it("renders explicit fallback when dashboard payload is absent", () => {
    render(<ContinuityOpenLoopsPanel dashboard={null} source="fixture" />);

    expect(screen.getByText("Open-loop dashboard unavailable")).toBeInTheDocument();
  });
});
