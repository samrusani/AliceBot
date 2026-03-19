import type { ApiSource, MemoryEvaluationSummary } from "../lib/api";
import { deriveMemoryQualityGate, formatPrecisionPercent } from "../lib/memory-quality";
import { StatusBadge } from "./status-badge";

type MemoryQualityGateProps = {
  summary: MemoryEvaluationSummary | null;
  summarySource: ApiSource | "unavailable";
};

function statusBadge(status: ReturnType<typeof deriveMemoryQualityGate>["status"]) {
  if (status === "on_track") {
    return { badgeStatus: "ready", badgeLabel: "On track" };
  }

  if (status === "needs_review") {
    return { badgeStatus: "requires_review", badgeLabel: "Needs review" };
  }

  if (status === "insufficient_evidence") {
    return { badgeStatus: "insufficient_evidence", badgeLabel: "Insufficient evidence" };
  }

  return { badgeStatus: "unavailable", badgeLabel: "Unavailable data" };
}

function interpretationCopy(gate: ReturnType<typeof deriveMemoryQualityGate>) {
  if (gate.status === "on_track") {
    return `Precision meets the ${Math.round(gate.precisionTarget * 100)}% target with enough adjudicated labels.`;
  }

  if (gate.status === "needs_review") {
    return `Precision is below the ${Math.round(gate.precisionTarget * 100)}% target despite sufficient adjudicated labels.`;
  }

  if (gate.status === "insufficient_evidence") {
    return `Collect at least ${gate.minimumAdjudicatedSample} adjudicated labels before using this as a ship-gate signal.`;
  }

  return "Evaluation summary data is unavailable, so gate readiness cannot be computed.";
}

function samplePostureCopy(gate: ReturnType<typeof deriveMemoryQualityGate>) {
  if (gate.samplePosture === "unavailable") {
    return "Sample posture unavailable.";
  }

  if (gate.samplePosture === "enough_sample") {
    return `Sample posture: ${gate.adjudicatedSampleCount} adjudicated labels, meeting the minimum ${gate.minimumAdjudicatedSample}.`;
  }

  return `Sample posture: ${gate.adjudicatedSampleCount}/${gate.minimumAdjudicatedSample} adjudicated labels.`;
}

function queuePostureCopy(gate: ReturnType<typeof deriveMemoryQualityGate>) {
  if (gate.queuePosture === "unavailable") {
    return "Queue posture unavailable.";
  }

  if (gate.queuePosture === "queue_clear") {
    return "Queue posture: unlabeled queue is clear.";
  }

  return `Queue posture: ${gate.unlabeledQueueCount} unlabeled memories still need review.`;
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
      </dl>

      <div className="memory-quality-gate__copy">
        <p>{interpretationCopy(gate)}</p>
        <p>{samplePostureCopy(gate)}</p>
        <p>{queuePostureCopy(gate)}</p>
      </div>

      <div className="cluster">
        <span className="meta-pill">Precision target: {Math.round(gate.precisionTarget * 100)}%</span>
        <span className="meta-pill">Minimum adjudicated sample: {gate.minimumAdjudicatedSample}</span>
      </div>
    </section>
  );
}
