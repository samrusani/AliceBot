import { describe, expect, it } from "vitest";

import {
  deriveMemoryQualityGate,
  formatPrecisionPercent,
  MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE,
  MEMORY_QUALITY_PRECISION_TARGET,
} from "./memory-quality";

describe("memory quality gate utility", () => {
  it("returns unavailable posture when summary data is missing", () => {
    const gate = deriveMemoryQualityGate(null);

    expect(gate.status).toBe("unavailable");
    expect(gate.precision).toBeNull();
    expect(gate.adjudicatedSampleCount).toBeNull();
    expect(gate.unlabeledQueueCount).toBeNull();
    expect(gate.samplePosture).toBe("unavailable");
    expect(gate.queuePosture).toBe("unavailable");
  });

  it("returns insufficient evidence when adjudicated sample is below threshold", () => {
    const gate = deriveMemoryQualityGate({
      total_memory_count: 6,
      active_memory_count: 6,
      deleted_memory_count: 0,
      labeled_memory_count: 6,
      unlabeled_memory_count: 4,
      total_label_row_count: 6,
      label_row_counts_by_value: {
        correct: MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE - 1,
        incorrect: 0,
        outdated: 0,
        insufficient_evidence: 0,
      },
      label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
    });

    expect(gate.status).toBe("insufficient_evidence");
    expect(gate.precision).toBe(1);
    expect(gate.samplePosture).toBe("insufficient_sample");
    expect(gate.queuePosture).toBe("queue_backlog");
  });

  it("returns needs review when sample is sufficient and precision is below threshold", () => {
    const gate = deriveMemoryQualityGate({
      total_memory_count: 10,
      active_memory_count: 10,
      deleted_memory_count: 0,
      labeled_memory_count: 10,
      unlabeled_memory_count: 0,
      total_label_row_count: 10,
      label_row_counts_by_value: {
        correct: 7,
        incorrect: 3,
        outdated: 0,
        insufficient_evidence: 0,
      },
      label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
    });

    expect(gate.status).toBe("needs_review");
    expect(gate.precision).toBe(0.7);
    expect(gate.samplePosture).toBe("enough_sample");
    expect(gate.queuePosture).toBe("queue_clear");
    expect(gate.precisionTarget).toBe(MEMORY_QUALITY_PRECISION_TARGET);
    expect(gate.minimumAdjudicatedSample).toBe(MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE);
  });

  it("returns on track when sample is sufficient and precision meets threshold", () => {
    const gate = deriveMemoryQualityGate({
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
    });

    expect(gate.status).toBe("on_track");
    expect(gate.precision).toBe(0.8);
    expect(formatPrecisionPercent(gate.precision)).toBe("80%");
  });

  it("formats unavailable precision explicitly", () => {
    expect(formatPrecisionPercent(null)).toBe("—");
  });
});
