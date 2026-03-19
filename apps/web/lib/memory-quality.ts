import type { MemoryEvaluationSummary } from "./api";

export const MEMORY_QUALITY_PRECISION_TARGET = 0.8;
export const MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE = 10;

export type MemoryQualityGateStatus =
  | "on_track"
  | "needs_review"
  | "insufficient_evidence"
  | "unavailable";

export type MemoryQualitySamplePosture = "enough_sample" | "insufficient_sample" | "unavailable";
export type MemoryQualityQueuePosture = "queue_clear" | "queue_backlog" | "unavailable";

export type MemoryQualityGate = {
  status: MemoryQualityGateStatus;
  precision: number | null;
  adjudicatedSampleCount: number | null;
  remainingToMinimumSample: number | null;
  unlabeledQueueCount: number | null;
  samplePosture: MemoryQualitySamplePosture;
  queuePosture: MemoryQualityQueuePosture;
  precisionTarget: number;
  minimumAdjudicatedSample: number;
};

function calculatePrecision(correctCount: number, incorrectCount: number) {
  const denominator = correctCount + incorrectCount;
  if (denominator === 0) {
    return null;
  }

  return correctCount / denominator;
}

export function deriveMemoryQualityGate(
  summary: MemoryEvaluationSummary | null | undefined,
): MemoryQualityGate {
  if (!summary) {
    return {
      status: "unavailable",
      precision: null,
      adjudicatedSampleCount: null,
      remainingToMinimumSample: null,
      unlabeledQueueCount: null,
      samplePosture: "unavailable",
      queuePosture: "unavailable",
      precisionTarget: MEMORY_QUALITY_PRECISION_TARGET,
      minimumAdjudicatedSample: MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE,
    };
  }

  const correctCount = summary.label_row_counts_by_value.correct;
  const incorrectCount = summary.label_row_counts_by_value.incorrect;
  const adjudicatedSampleCount = correctCount + incorrectCount;
  const remainingToMinimumSample = Math.max(
    0,
    MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE - adjudicatedSampleCount,
  );
  const precision = calculatePrecision(correctCount, incorrectCount);
  const hasMinimumSample = adjudicatedSampleCount >= MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE;

  let status: MemoryQualityGateStatus = "insufficient_evidence";
  if (hasMinimumSample) {
    status =
      precision !== null && precision >= MEMORY_QUALITY_PRECISION_TARGET ? "on_track" : "needs_review";
  }

  return {
    status,
    precision,
    adjudicatedSampleCount,
    remainingToMinimumSample,
    unlabeledQueueCount: summary.unlabeled_memory_count,
    samplePosture: hasMinimumSample ? "enough_sample" : "insufficient_sample",
    queuePosture: summary.unlabeled_memory_count === 0 ? "queue_clear" : "queue_backlog",
    precisionTarget: MEMORY_QUALITY_PRECISION_TARGET,
    minimumAdjudicatedSample: MEMORY_QUALITY_MIN_ADJUDICATED_SAMPLE,
  };
}

export function formatPrecisionPercent(precision: number | null) {
  if (precision === null) {
    return "—";
  }

  return `${Math.round(precision * 100)}%`;
}
