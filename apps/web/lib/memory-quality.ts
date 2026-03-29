import type { MemoryEvaluationSummary, MemoryQualityGateSummary } from "./api";

export type MemoryQualityGate = {
  status: MemoryQualityGateSummary["status"] | "unavailable";
  precision: number | null;
  adjudicatedSampleCount: number | null;
  remainingToMinimumSample: number | null;
  unlabeledQueueCount: number | null;
  highRiskMemoryCount: number | null;
  staleTruthCount: number | null;
  supersededActiveConflictCount: number | null;
  precisionTarget: number | null;
  minimumAdjudicatedSample: number | null;
};

export function deriveMemoryQualityGate(
  summary: MemoryEvaluationSummary | null | undefined,
): MemoryQualityGate {
  const qualityGate = summary?.quality_gate;
  if (!qualityGate) {
    return {
      status: "unavailable",
      precision: null,
      adjudicatedSampleCount: null,
      remainingToMinimumSample: null,
      unlabeledQueueCount: null,
      highRiskMemoryCount: null,
      staleTruthCount: null,
      supersededActiveConflictCount: null,
      precisionTarget: null,
      minimumAdjudicatedSample: null,
    };
  }

  return {
    status: qualityGate.status,
    precision: qualityGate.precision,
    adjudicatedSampleCount: qualityGate.adjudicated_sample_count,
    remainingToMinimumSample: qualityGate.remaining_to_minimum_sample,
    unlabeledQueueCount: qualityGate.unlabeled_memory_count,
    highRiskMemoryCount: qualityGate.high_risk_memory_count,
    staleTruthCount: qualityGate.stale_truth_count,
    supersededActiveConflictCount: qualityGate.superseded_active_conflict_count,
    precisionTarget: qualityGate.precision_target,
    minimumAdjudicatedSample: qualityGate.minimum_adjudicated_sample,
  };
}

export function formatPrecisionPercent(precision: number | null) {
  if (precision === null) {
    return "—";
  }

  return `${Math.round(precision * 100)}%`;
}
