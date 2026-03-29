import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ResumptionBrief } from "./resumption-brief";

const briefFixture = {
  assembly_version: "continuity_resumption_brief_v0",
  scope: {
    since: null,
    until: null,
  },
  last_decision: {
    item: {
      id: "decision-1",
      capture_event_id: "capture-1",
      object_type: "Decision" as const,
      status: "active",
      title: "Decision: Keep rollout phased",
      body: { decision_text: "Keep rollout phased" },
      provenance: {},
      confirmation_status: "confirmed" as const,
      admission_posture: "DERIVED" as const,
      confidence: 1,
      relevance: 100,
      scope_matches: [],
      provenance_references: [],
      ordering: {
        scope_match_count: 0,
        query_term_match_count: 0,
        confirmation_rank: 3,
        posture_rank: 2,
        confidence: 1,
      },
      created_at: "2026-03-29T10:00:00Z",
      updated_at: "2026-03-29T10:00:00Z",
    },
    empty_state: {
      is_empty: false,
      message: "No decision found in the requested scope.",
    },
  },
  open_loops: {
    items: [
      {
        id: "loop-1",
        capture_event_id: "capture-2",
        object_type: "WaitingFor" as const,
        status: "active",
        title: "Waiting For: Vendor quote",
        body: { waiting_for_text: "Vendor quote" },
        provenance: {},
        confirmation_status: "unconfirmed" as const,
        admission_posture: "DERIVED" as const,
        confidence: 1,
        relevance: 95,
        scope_matches: [],
        provenance_references: [],
        ordering: {
          scope_match_count: 0,
          query_term_match_count: 0,
          confirmation_rank: 2,
          posture_rank: 2,
          confidence: 1,
        },
        created_at: "2026-03-29T10:10:00Z",
        updated_at: "2026-03-29T10:10:00Z",
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
      message: "No open loops found in the requested scope.",
    },
  },
  recent_changes: {
    items: [],
    summary: {
      limit: 5,
      returned_count: 0,
      total_count: 1,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No recent changes found in the requested scope.",
    },
  },
  next_action: {
    item: null,
    empty_state: {
      is_empty: true,
      message: "No next action found in the requested scope.",
    },
  },
  sources: ["continuity_capture_events", "continuity_objects"],
};

describe("ResumptionBrief", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders deterministic resumption sections with explicit empty states", () => {
    render(<ResumptionBrief brief={briefFixture} source="live" />);

    expect(screen.getByText("Live brief")).toBeInTheDocument();
    expect(screen.getByText("continuity_resumption_brief_v0")).toBeInTheDocument();
    expect(screen.getByText("Decision: Keep rollout phased")).toBeInTheDocument();
    expect(screen.getByText("Waiting For: Vendor quote")).toBeInTheDocument();
    expect(screen.getByText("No recent changes found in the requested scope.")).toBeInTheDocument();
    expect(screen.getByText("No next action found in the requested scope.")).toBeInTheDocument();
  });

  it("renders fallback empty state when brief payload is absent", () => {
    render(<ResumptionBrief brief={null} source="fixture" />);

    expect(screen.getByText("Resumption unavailable")).toBeInTheDocument();
  });
});
