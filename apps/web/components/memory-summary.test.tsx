import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MemorySummary } from "./memory-summary";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("MemorySummary", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders quality gate metrics and preserves queue/active filter controls", () => {
    render(
      <MemorySummary
        summary={{
          total_memory_count: 10,
          active_memory_count: 9,
          deleted_memory_count: 1,
          labeled_memory_count: 10,
          unlabeled_memory_count: 2,
          total_label_row_count: 10,
          label_row_counts_by_value: {
            correct: 8,
            incorrect: 2,
            outdated: 0,
            insufficient_evidence: 0,
          },
          label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
          quality_gate: {
            status: "healthy",
            precision: 0.9,
            precision_target: 0.8,
            adjudicated_sample_count: 12,
            minimum_adjudicated_sample: 10,
            remaining_to_minimum_sample: 0,
            unlabeled_memory_count: 2,
            high_risk_memory_count: 0,
            stale_truth_count: 0,
            superseded_active_conflict_count: 0,
            counts: {
              active_memory_count: 9,
              labeled_active_memory_count: 7,
              adjudicated_correct_count: 6,
              adjudicated_incorrect_count: 1,
              outdated_label_count: 0,
              insufficient_evidence_label_count: 0,
            },
          },
        }}
        summarySource="live"
        queueSummary={{
          memory_status: "active",
          review_state: "unlabeled",
          limit: 20,
          returned_count: 2,
          total_count: 2,
          has_more: false,
          order: ["updated_at_desc", "created_at_desc", "id_desc"],
        }}
        queueSource="live"
        activeFilter="active"
      />,
    );

    expect(screen.getByText("Ship-gate readiness")).toBeInTheDocument();
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Quality gate is healthy: precision target is met, sample minimum is met, and no blocking risk posture remains.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Sample posture: 12/10 adjudicated labels. Minimum sample is met.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Queue/risk posture: 2 unlabeled, 0 high risk, 0 stale truth, 0 superseded active conflicts.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Active list" })).toHaveAttribute("href", "/memories");
    expect(screen.getByRole("link", { name: "Unlabeled queue" })).toHaveAttribute(
      "href",
      "/memories?filter=queue",
    );
  });

  it("keeps source fallback notes explicit", () => {
    render(
      <MemorySummary
        summary={{
          total_memory_count: 3,
          active_memory_count: 3,
          deleted_memory_count: 0,
          labeled_memory_count: 1,
          unlabeled_memory_count: 2,
          total_label_row_count: 1,
          label_row_counts_by_value: {
            correct: 1,
            incorrect: 0,
            outdated: 0,
            insufficient_evidence: 0,
          },
          label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
        }}
        summarySource="fixture"
        summaryUnavailableReason="summary down"
        queueSummary={{
          memory_status: "active",
          review_state: "unlabeled",
          limit: 20,
          returned_count: 2,
          total_count: 2,
          has_more: false,
          order: ["updated_at_desc", "created_at_desc", "id_desc"],
        }}
        queueSource="fixture"
        queueUnavailableReason="queue down"
        activeFilter="queue"
      />,
    );

    expect(screen.getByText("Summary: summary down")).toBeInTheDocument();
    expect(screen.getByText("Queue: queue down")).toBeInTheDocument();
  });
});
