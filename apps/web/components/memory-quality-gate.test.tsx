import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MemoryQualityGate } from "./memory-quality-gate";

describe("MemoryQualityGate", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders on-track readiness when precision target and sample threshold are met", () => {
    render(
      <MemoryQualityGate
        summarySource="live"
        summary={{
          total_memory_count: 10,
          active_memory_count: 10,
          deleted_memory_count: 0,
          labeled_memory_count: 10,
          unlabeled_memory_count: 0,
          total_label_row_count: 10,
          label_row_counts_by_value: {
            correct: 8,
            incorrect: 2,
            outdated: 0,
            insufficient_evidence: 0,
          },
          label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
        }}
      />,
    );

    expect(screen.getByText("On track")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("Progress: minimum adjudicated sample is met.")).toBeInTheDocument();
    expect(screen.getByText("Queue posture: unlabeled queue is clear.")).toBeInTheDocument();
  });

  it("renders needs-review posture when precision is below threshold with enough sample", () => {
    render(
      <MemoryQualityGate
        summarySource="fixture"
        summary={{
          total_memory_count: 10,
          active_memory_count: 10,
          deleted_memory_count: 0,
          labeled_memory_count: 10,
          unlabeled_memory_count: 2,
          total_label_row_count: 10,
          label_row_counts_by_value: {
            correct: 7,
            incorrect: 3,
            outdated: 0,
            insufficient_evidence: 0,
          },
          label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
        }}
      />,
    );

    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(
      screen.getByText("Precision is below the 80% target despite sufficient adjudicated labels."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Queue posture: 2 unlabeled memories still need review."),
    ).toBeInTheDocument();
    expect(screen.getByText("Progress: minimum adjudicated sample is met.")).toBeInTheDocument();
  });

  it("renders insufficient-evidence posture when adjudicated sample is below minimum", () => {
    render(
      <MemoryQualityGate
        summarySource="fixture"
        summary={{
          total_memory_count: 2,
          active_memory_count: 2,
          deleted_memory_count: 0,
          labeled_memory_count: 1,
          unlabeled_memory_count: 1,
          total_label_row_count: 1,
          label_row_counts_by_value: {
            correct: 1,
            incorrect: 0,
            outdated: 0,
            insufficient_evidence: 0,
          },
          label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
        }}
      />,
    );

    expect(screen.getByText("Insufficient evidence")).toBeInTheDocument();
    expect(screen.getByText("Sample posture: 1/10 adjudicated labels.")).toBeInTheDocument();
    expect(
      screen.getByText("Progress: 9 labels remaining to reach the minimum sample."),
    ).toBeInTheDocument();
  });

  it("renders unavailable-data posture when summary data cannot be computed", () => {
    render(<MemoryQualityGate summarySource="unavailable" summary={null} />);

    expect(screen.getByText("Unavailable data")).toBeInTheDocument();
    expect(
      screen.getByText("Evaluation summary data is unavailable, so gate readiness cannot be computed."),
    ).toBeInTheDocument();
    expect(screen.getByText("Sample posture unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Progress to minimum sample is unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Queue posture unavailable.")).toBeInTheDocument();
  });
});
