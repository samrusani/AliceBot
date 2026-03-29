import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ContinuityRecallPanel } from "./continuity-recall-panel";

const recallItems = [
  {
    id: "recall-1",
    capture_event_id: "capture-1",
    object_type: "Decision" as const,
    status: "active",
    title: "Decision: Keep rollout phased",
    body: { decision_text: "Keep rollout phased" },
    provenance: { thread_id: "thread-1" },
    confirmation_status: "confirmed" as const,
    admission_posture: "DERIVED" as const,
    confidence: 0.95,
    relevance: 130,
    scope_matches: [{ kind: "thread" as const, value: "thread-1" }],
    provenance_references: [{ source_kind: "continuity_capture_event", source_id: "capture-1" }],
    ordering: {
      scope_match_count: 1,
      query_term_match_count: 1,
      confirmation_rank: 3,
      posture_rank: 2,
      confidence: 0.95,
    },
    created_at: "2026-03-29T10:00:00Z",
    updated_at: "2026-03-29T10:00:00Z",
  },
];

describe("ContinuityRecallPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders recall filters and provenance-backed result cards", () => {
    render(
      <ContinuityRecallPanel
        results={recallItems}
        summary={{
          query: "rollout",
          filters: {
            thread_id: "thread-1",
            since: null,
            until: null,
          },
          limit: 20,
          returned_count: 1,
          total_count: 1,
          order: ["relevance_desc", "created_at_desc", "id_desc"],
        }}
        source="live"
        filters={{
          query: "rollout",
          threadId: "thread-1",
          taskId: "",
          project: "",
          person: "",
          since: "",
          until: "",
          limit: 20,
        }}
      />,
    );

    expect(screen.getByText("Live recall")).toBeInTheDocument();
    expect(screen.getByText("1 matched")).toBeInTheDocument();
    expect(screen.getByLabelText("Query")).toHaveValue("rollout");
    expect(screen.getByLabelText("Thread ID")).toHaveValue("thread-1");
    expect(screen.getByText("Decision: Keep rollout phased")).toBeInTheDocument();
    expect(screen.getByText("1 provenance refs")).toBeInTheDocument();
    expect(screen.getByText("1 scope matches")).toBeInTheDocument();
  });

  it("renders explicit empty state when no recall results exist", () => {
    render(
      <ContinuityRecallPanel
        results={[]}
        summary={{
          query: null,
          filters: {
            since: null,
            until: null,
          },
          limit: 20,
          returned_count: 0,
          total_count: 0,
          order: ["relevance_desc", "created_at_desc", "id_desc"],
        }}
        source="fixture"
        filters={{
          query: "",
          threadId: "",
          taskId: "",
          project: "",
          person: "",
          since: "",
          until: "",
          limit: 20,
        }}
      />,
    );

    expect(screen.getByText("No recall hits")).toBeInTheDocument();
  });
});
