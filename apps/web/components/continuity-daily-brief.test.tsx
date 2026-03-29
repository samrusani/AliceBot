import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ContinuityDailyBriefPanel } from "./continuity-daily-brief";

const briefFixture = {
  assembly_version: "continuity_daily_brief_v0",
  scope: {
    since: null,
    until: null,
  },
  waiting_for_highlights: {
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
      limit: 3,
      returned_count: 1,
      total_count: 1,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: false,
      message: "No waiting-for highlights for today in the requested scope.",
    },
  },
  blocker_highlights: {
    items: [],
    summary: {
      limit: 3,
      returned_count: 0,
      total_count: 0,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No blocker highlights for today in the requested scope.",
    },
  },
  stale_items: {
    items: [],
    summary: {
      limit: 3,
      returned_count: 0,
      total_count: 0,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No stale items for today in the requested scope.",
    },
  },
  next_suggested_action: {
    item: {
      id: "next-1",
      capture_event_id: "capture-2",
      object_type: "NextAction" as const,
      status: "active",
      title: "Next Action: Send follow-up",
      body: { action_text: "Send follow-up" },
      provenance: {},
      confirmation_status: "unconfirmed" as const,
      admission_posture: "DERIVED" as const,
      confidence: 1,
      relevance: 99,
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
      created_at: "2026-03-30T09:05:00Z",
      updated_at: "2026-03-30T09:05:00Z",
    },
    empty_state: {
      is_empty: false,
      message: "No next suggested action in the requested scope.",
    },
  },
  sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
};

describe("ContinuityDailyBriefPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders daily brief sections with explicit empty states", () => {
    render(<ContinuityDailyBriefPanel brief={briefFixture} source="live" />);

    expect(screen.getByText("Live daily brief")).toBeInTheDocument();
    expect(screen.getByText("continuity_daily_brief_v0")).toBeInTheDocument();
    expect(screen.getByText("Waiting For: Vendor quote")).toBeInTheDocument();
    expect(screen.getByText("No blocker highlights for today in the requested scope.")).toBeInTheDocument();
    expect(screen.getByText("No stale items for today in the requested scope.")).toBeInTheDocument();
    expect(screen.getByText("Next Action: Send follow-up")).toBeInTheDocument();
  });

  it("renders fallback empty state when payload is absent", () => {
    render(<ContinuityDailyBriefPanel brief={null} source="fixture" />);

    expect(screen.getByText("Daily brief unavailable")).toBeInTheDocument();
  });
});
