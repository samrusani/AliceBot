import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ContinuityWeeklyReviewPanel } from "./continuity-weekly-review";

const reviewFixture = {
  assembly_version: "continuity_weekly_review_v0",
  scope: {
    since: null,
    until: null,
  },
  rollup: {
    total_count: 2,
    waiting_for_count: 1,
    blocker_count: 0,
    stale_count: 1,
    next_action_count: 0,
    posture_order: ["waiting_for", "blocker", "stale", "next_action"] as const,
  },
  waiting_for: {
    items: [
      {
        id: "waiting-1",
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
        created_at: "2026-03-30T09:00:00Z",
        updated_at: "2026-03-30T09:00:00Z",
      },
    ],
    summary: {
      limit: 5,
      returned_count: 1,
      total_count: 1,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: false,
      message: "No waiting-for items in the requested scope.",
    },
  },
  blocker: {
    items: [],
    summary: {
      limit: 5,
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
    items: [
      {
        id: "stale-1",
        capture_event_id: "capture-2",
        object_type: "WaitingFor" as const,
        status: "stale",
        title: "Waiting For: Stale invoice response",
        body: { waiting_for_text: "Stale invoice response" },
        provenance: {},
        confirmation_status: "unconfirmed" as const,
        admission_posture: "DERIVED" as const,
        confidence: 1,
        relevance: 90,
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
          lifecycle_rank: 3,
          confidence: 1,
        },
        created_at: "2026-03-30T09:05:00Z",
        updated_at: "2026-03-30T09:05:00Z",
      },
    ],
    summary: {
      limit: 5,
      returned_count: 1,
      total_count: 1,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: false,
      message: "No stale items in the requested scope.",
    },
  },
  next_action: {
    items: [],
    summary: {
      limit: 5,
      returned_count: 0,
      total_count: 0,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No next-action items in the requested scope.",
    },
  },
  sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
};

describe("ContinuityWeeklyReviewPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders weekly rollup and grouped posture sections", () => {
    render(<ContinuityWeeklyReviewPanel review={reviewFixture} source="live" />);

    expect(screen.getByText("Live weekly review")).toBeInTheDocument();
    expect(screen.getByText("continuity_weekly_review_v0")).toBeInTheDocument();
    expect(screen.getByText("2 total")).toBeInTheDocument();
    expect(screen.getByText("Waiting For: Vendor quote")).toBeInTheDocument();
    expect(screen.getByText("Waiting For: Stale invoice response")).toBeInTheDocument();
    expect(screen.getByText("No blocker items in the requested scope.")).toBeInTheDocument();
    expect(screen.getByText("No next-action items in the requested scope.")).toBeInTheDocument();
  });

  it("renders fallback empty state when payload is absent", () => {
    render(<ContinuityWeeklyReviewPanel review={null} source="fixture" />);

    expect(screen.getByText("Weekly review unavailable")).toBeInTheDocument();
  });
});
