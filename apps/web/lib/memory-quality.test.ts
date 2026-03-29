import { describe, expect, it } from "vitest";

import { deriveMemoryQualityGate, formatPrecisionPercent } from "./memory-quality";

describe("memory quality gate utility", () => {
  it("returns unavailable posture when quality-gate payload is missing", () => {
    const gate = deriveMemoryQualityGate(null);

    expect(gate.status).toBe("unavailable");
    expect(gate.precision).toBeNull();
    expect(gate.adjudicatedSampleCount).toBeNull();
    expect(gate.remainingToMinimumSample).toBeNull();
    expect(gate.unlabeledQueueCount).toBeNull();
    expect(gate.precisionTarget).toBeNull();
    expect(gate.minimumAdjudicatedSample).toBeNull();
  });

  it("maps canonical quality-gate payload values without local threshold recomputation", () => {
    const gate = deriveMemoryQualityGate({
      total_memory_count: 12,
      active_memory_count: 11,
      deleted_memory_count: 1,
      labeled_memory_count: 10,
      unlabeled_memory_count: 1,
      total_label_row_count: 10,
      label_row_counts_by_value: {
        correct: 9,
        incorrect: 1,
        outdated: 0,
        insufficient_evidence: 0,
      },
      label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
      quality_gate: {
        status: "needs_review",
        precision: 0.9,
        precision_target: 0.8,
        adjudicated_sample_count: 10,
        minimum_adjudicated_sample: 10,
        remaining_to_minimum_sample: 0,
        unlabeled_memory_count: 1,
        high_risk_memory_count: 1,
        stale_truth_count: 0,
        superseded_active_conflict_count: 0,
        counts: {
          active_memory_count: 11,
          labeled_active_memory_count: 10,
          adjudicated_correct_count: 9,
          adjudicated_incorrect_count: 1,
          outdated_label_count: 0,
          insufficient_evidence_label_count: 0,
        },
      },
    });

    expect(gate.status).toBe("needs_review");
    expect(gate.precision).toBe(0.9);
    expect(gate.adjudicatedSampleCount).toBe(10);
    expect(gate.remainingToMinimumSample).toBe(0);
    expect(gate.unlabeledQueueCount).toBe(1);
    expect(gate.highRiskMemoryCount).toBe(1);
    expect(gate.staleTruthCount).toBe(0);
    expect(gate.supersededActiveConflictCount).toBe(0);
    expect(gate.precisionTarget).toBe(0.8);
    expect(gate.minimumAdjudicatedSample).toBe(10);
  });

  it("formats unavailable precision explicitly", () => {
    expect(formatPrecisionPercent(null)).toBe("—");
  });
});
