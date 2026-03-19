import Link from "next/link";

import type { ApiSource, MemoryEvaluationSummary, MemoryReviewQueueSummary } from "../lib/api";
import { MemoryQualityGate } from "./memory-quality-gate";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type MemorySummaryProps = {
  summary: MemoryEvaluationSummary | null;
  summarySource: ApiSource | "unavailable";
  summaryUnavailableReason?: string;
  queueSummary: MemoryReviewQueueSummary | null;
  queueSource: ApiSource | "unavailable";
  queueUnavailableReason?: string;
  activeFilter: "active" | "queue";
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live";
  }

  if (source === "fixture") {
    return "Fixture";
  }

  return "Unavailable";
}

export function MemorySummary({
  summary,
  summarySource,
  summaryUnavailableReason,
  queueSummary,
  queueSource,
  queueUnavailableReason,
  activeFilter,
}: MemorySummaryProps) {
  return (
    <SectionCard
      eyebrow="Memory summary"
      title="Evaluation and review posture"
      description="Keep memory review grounded in one bounded summary before diving into item-level detail."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={summarySource} label={`Summary ${sourceLabel(summarySource)}`} />
          <StatusBadge status={queueSource} label={`Queue ${sourceLabel(queueSource)}`} />
          <span className="meta-pill">
            {queueSummary?.total_count ?? 0} unlabeled in review queue
          </span>
        </div>

        {summaryUnavailableReason || queueUnavailableReason ? (
          <div className="execution-summary__note execution-summary__note--danger">
            <p className="execution-summary__label">Live source notes</p>
            {summaryUnavailableReason ? <p>Summary: {summaryUnavailableReason}</p> : null}
            {queueUnavailableReason ? <p>Queue: {queueUnavailableReason}</p> : null}
          </div>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Total memories</dt>
            <dd>{summary?.total_memory_count ?? 0}</dd>
          </div>
          <div>
            <dt>Active</dt>
            <dd>{summary?.active_memory_count ?? 0}</dd>
          </div>
          <div>
            <dt>Labeled</dt>
            <dd>{summary?.labeled_memory_count ?? 0}</dd>
          </div>
          <div>
            <dt>Unlabeled</dt>
            <dd>{summary?.unlabeled_memory_count ?? 0}</dd>
          </div>
        </dl>

        <MemoryQualityGate
          summary={summary}
          summarySource={summarySource}
        />

        <div className="cluster">
          <Link
            href="/memories"
            className={`button-secondary button-secondary--compact${activeFilter === "active" ? " is-current" : ""}`}
          >
            Active list
          </Link>
          <Link
            href="/memories?filter=queue"
            className={`button-secondary button-secondary--compact${activeFilter === "queue" ? " is-current" : ""}`}
          >
            Unlabeled queue
          </Link>
        </div>
      </div>
    </SectionCard>
  );
}
