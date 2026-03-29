import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ContinuityReviewQueue } from "./continuity-review-queue";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    "aria-current": ariaCurrent,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
    "aria-current"?: string;
  }) => (
    <a href={href} className={className} aria-current={ariaCurrent}>
      {children}
    </a>
  ),
}));

const queueItems = [
  {
    id: "object-1",
    capture_event_id: "capture-1",
    object_type: "Decision" as const,
    status: "active",
    title: "Decision: Keep rollout phased",
    body: { decision_text: "Keep rollout phased" },
    provenance: {},
    confidence: 0.95,
    last_confirmed_at: "2026-03-30T10:00:00Z",
    supersedes_object_id: null,
    superseded_by_object_id: null,
    created_at: "2026-03-30T10:00:00Z",
    updated_at: "2026-03-30T10:00:00Z",
  },
  {
    id: "object-2",
    capture_event_id: "capture-2",
    object_type: "Decision" as const,
    status: "stale",
    title: "Decision: Recheck next week",
    body: { decision_text: "Recheck next week" },
    provenance: {},
    confidence: 0.75,
    last_confirmed_at: null,
    supersedes_object_id: null,
    superseded_by_object_id: null,
    created_at: "2026-03-30T11:00:00Z",
    updated_at: "2026-03-30T11:00:00Z",
  },
];

describe("ContinuityReviewQueue", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders review queue filters and selectable items", () => {
    render(
      <ContinuityReviewQueue
        items={queueItems}
        summary={{
          status: "correction_ready",
          limit: 20,
          returned_count: 2,
          total_count: 2,
          order: ["updated_at_desc", "created_at_desc", "id_desc"],
        }}
        selectedObjectId="object-1"
        source="live"
        filters={{
          status: "correction_ready",
          limit: 20,
        }}
      />,
    );

    expect(screen.getByText("Live review queue")).toBeInTheDocument();
    expect(screen.getByText("2 queued")).toBeInTheDocument();
    expect(screen.getByLabelText("Status filter")).toHaveValue("correction_ready");
    expect(screen.getByLabelText("Limit")).toHaveValue(20);
    expect(screen.getByText("Decision: Keep rollout phased")).toBeInTheDocument();
    expect(screen.getByText("Decision: Recheck next week")).toBeInTheDocument();

    const selectedLink = screen.getByRole("link", { name: "Selected" });
    expect(selectedLink).toHaveAttribute("aria-current", "true");
  });

  it("renders explicit empty state when queue is empty", () => {
    render(
      <ContinuityReviewQueue
        items={[]}
        summary={{
          status: "correction_ready",
          limit: 20,
          returned_count: 0,
          total_count: 0,
          order: ["updated_at_desc", "created_at_desc", "id_desc"],
        }}
        selectedObjectId=""
        source="fixture"
        filters={{
          status: "correction_ready",
          limit: 20,
        }}
      />,
    );

    expect(screen.getByText("No review items")).toBeInTheDocument();
  });
});
