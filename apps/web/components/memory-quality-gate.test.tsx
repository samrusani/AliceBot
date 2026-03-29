import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MemoryQualityGate } from "./memory-quality-gate";

function summaryWithGate(status: "healthy" | "needs_review" | "insufficient_sample" | "degraded") {
  return {
    total_memory_count: 12,
    active_memory_count: 10,
    deleted_memory_count: 2,
    labeled_memory_count: 10,
    unlabeled_memory_count: 0,
    total_label_row_count: 10,
    label_row_counts_by_value: {
      correct: 9,
      incorrect: 1,
      outdated: 0,
      insufficient_evidence: 0,
    },
    label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"] as const,
    quality_gate: {
      status,
      precision: status === "degraded" ? 0.7 : 0.9,
      precision_target: 0.8,
      adjudicated_sample_count: status === "insufficient_sample" ? 4 : 10,
      minimum_adjudicated_sample: 10,
      remaining_to_minimum_sample: status === "insufficient_sample" ? 6 : 0,
      unlabeled_memory_count: status === "needs_review" ? 2 : 0,
      high_risk_memory_count: status === "needs_review" ? 1 : 0,
      stale_truth_count: 0,
      superseded_active_conflict_count: status === "degraded" ? 1 : 0,
      counts: {
        active_memory_count: 10,
        labeled_active_memory_count: status === "needs_review" ? 8 : 10,
        adjudicated_correct_count: status === "degraded" ? 7 : 9,
        adjudicated_incorrect_count: status === "degraded" ? 3 : 1,
        outdated_label_count: status === "degraded" ? 1 : 0,
        insufficient_evidence_label_count: 0,
      },
    },
  };
}

describe("MemoryQualityGate", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders healthy readiness from canonical API status", () => {
    render(<MemoryQualityGate summarySource="live" summary={summaryWithGate("healthy")} />);

    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText(/Quality gate is healthy/i)).toBeInTheDocument();
  });

  it("renders needs-review posture from canonical API status", () => {
    render(<MemoryQualityGate summarySource="fixture" summary={summaryWithGate("needs_review")} />);

    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText(/Quality gate needs review/i)).toBeInTheDocument();
    expect(screen.getByText(/2 unlabeled, 1 high risk/i)).toBeInTheDocument();
  });

  it("renders insufficient-sample posture from canonical API status", () => {
    render(<MemoryQualityGate summarySource="fixture" summary={summaryWithGate("insufficient_sample")} />);

    expect(screen.getByText("Insufficient sample")).toBeInTheDocument();
    expect(screen.getByText(/insufficient adjudicated sample/i)).toBeInTheDocument();
    expect(screen.getByText(/4\/10 adjudicated labels with 6 remaining/i)).toBeInTheDocument();
  });

  it("renders degraded posture from canonical API status", () => {
    render(<MemoryQualityGate summarySource="fixture" summary={summaryWithGate("degraded")} />);

    expect(screen.getByText("Degraded")).toBeInTheDocument();
    expect(screen.getByText(/Quality gate is degraded/i)).toBeInTheDocument();
    expect(screen.getByText(/superseded active conflicts/i)).toBeInTheDocument();
  });

  it("renders unavailable-data posture when quality-gate payload is unavailable", () => {
    render(<MemoryQualityGate summarySource="unavailable" summary={null} />);

    expect(screen.getByText("Unavailable data")).toBeInTheDocument();
    expect(screen.getByText(/Quality-gate data is unavailable/i)).toBeInTheDocument();
    expect(screen.getByText("Adjudicated sample posture unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Queue and risk posture unavailable.")).toBeInTheDocument();
  });
});
