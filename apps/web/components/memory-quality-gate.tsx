import type { ApiSource, MemoryEvaluationSummary } from "../lib/api";
import { deriveMemoryQualityGate, formatPrecisionPercent } from "../lib/memory-quality";
import { StatusBadge } from "./status-badge";

type MemoryQualityGateProps = {
  summary: MemoryEvaluationSummary | null;
  summarySource: ApiSource | "unavailable";
};

function statusBadge(status: ReturnType<typeof deriveMemoryQualityGate>["status"]) {
  if (status === "healthy") {
    return { badgeStatus: "ready", badgeLabel: "Healthy" };
  }

  if (status === "needs_review") {
    return { badgeStatus: "requires_review", badgeLabel: "Needs review" };
  }

  if (status === "insufficient_sample") {
    return { badgeStatus: "insufficient_evidence", badgeLabel: "Insufficient sample" };
  }

  if (status === "degraded") {
    return { badgeStatus: "error", badgeLabel: "Degraded" };
  }

  return { badgeStatus: "unavailable", badgeLabel: "Unavailable data" };
}

function interpretationCopy(gate: ReturnType<typeof deriveMemoryQualityGate>) {
  if (gate.status === "healthy") {
    return "Quality gate is healthy: precision target is met, sample minimum is met, and no blocking risk posture remains.";
  }

  if (gate.status === "needs_review") {
    return "Quality gate needs review: precision threshold is met, but unresolved queue risk still blocks healthy posture.";
  }

  if (gate.status === "insufficient_sample") {
    return "Quality gate is blocked by insufficient adjudicated sample for reliable precision posture.";
  }

  if (gate.status === "degraded") {
    return "Quality gate is degraded: precision is below target or active supersession conflicts remain unresolved.";
  }

  return "Quality-gate data is unavailable, so readiness cannot be determined.";
}

function sampleProgressCopy(gate: ReturnType<typeof deriveMemoryQualityGate>) {
  if (gate.adjudicatedSampleCount === null || gate.minimumAdjudicatedSample === null) {
    return "Adjudicated sample posture unavailable.";
  }

  if (gate.remainingToMinimumSample === 0) {
    return `Sample posture: ${gate.adjudicatedSampleCount}/${gate.minimumAdjudicatedSample} adjudicated labels. Minimum sample is met.`;
  }

  return `Sample posture: ${gate.adjudicatedSampleCount}/${gate.minimumAdjudicatedSample} adjudicated labels with ${gate.remainingToMinimumSample} remaining to minimum.`;
}

function queueRiskCopy(gate: ReturnType<typeof deriveMemoryQualityGate>) {
  if (
    gate.unlabeledQueueCount === null ||
    gate.highRiskMemoryCount === null ||
    gate.staleTruthCount === null ||
    gate.supersededActiveConflictCount === null
  ) {
    return "Queue and risk posture unavailable.";
  }

  return `Queue/risk posture: ${gate.unlabeledQueueCount} unlabeled, ${gate.highRiskMemoryCount} high risk, ${gate.staleTruthCount} stale truth, ${gate.supersededActiveConflictCount} superseded active conflicts.`;
}

function formatPercentTarget(value: number | null) {
  if (value === null) {
    return "—";
  }
  return `${Math.round(value * 100)}%`;
}

export function MemoryQualityGate({ summary, summarySource }: MemoryQualityGateProps) {
  const gate = deriveMemoryQualityGate(summarySource === "unavailable" ? null : summary);
  const badge = statusBadge(gate.status);

  return (
    <section className="detail-group detail-group--muted memory-quality-gate">
      <div className="memory-quality-gate__topline">
        <div className="detail-stack">
          <p className="execution-summary__label">Memory-quality gate</p>
          <h3>Ship-gate readiness</h3>
        </div>
        <StatusBadge status={badge.badgeStatus} label={badge.badgeLabel} />
      </div>

      <dl className="key-value-grid key-value-grid--compact">
        <div>
          <dt>Precision</dt>
          <dd>{formatPrecisionPercent(gate.precision)}</dd>
        </div>
        <div>
          <dt>Adjudicated sample</dt>
          <dd>{gate.adjudicatedSampleCount ?? "—"}</dd>
        </div>
        <div>
          <dt>Unlabeled queue</dt>
          <dd>{gate.unlabeledQueueCount ?? "—"}</dd>
        </div>
        <div>
          <dt>Remaining to minimum sample</dt>
          <dd>{gate.remainingToMinimumSample ?? "—"}</dd>
        </div>
      </dl>

      <div className="memory-quality-gate__copy">
        <p>{interpretationCopy(gate)}</p>
        <p>{sampleProgressCopy(gate)}</p>
        <p>{queueRiskCopy(gate)}</p>
      </div>

      <div className="cluster">
        <span className="meta-pill">Precision target: {formatPercentTarget(gate.precisionTarget)}</span>
        <span className="meta-pill">
          Minimum adjudicated sample: {gate.minimumAdjudicatedSample ?? "—"}
        </span>
      </div>
    </section>
  );
}
