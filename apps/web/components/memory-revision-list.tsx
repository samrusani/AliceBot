import type {
  ApiSource,
  MemoryRevisionReviewListSummary,
  MemoryRevisionReviewRecord,
} from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type MemoryRevisionListProps = {
  memoryId: string | null;
  revisions: MemoryRevisionReviewRecord[];
  summary: MemoryRevisionReviewListSummary | null;
  source: ApiSource | "unavailable" | null;
  unavailableReason?: string;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatValue(value: unknown | null) {
  if (value == null) {
    return "null";
  }

  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value, null, 2) ?? "null";
}

export function MemoryRevisionList({
  memoryId,
  revisions,
  summary,
  source,
  unavailableReason,
}: MemoryRevisionListProps) {
  if (!memoryId) {
    return (
      <SectionCard
        eyebrow="Revision history"
        title="No memory selected"
        description="Select a memory to inspect ordered revision history."
      >
        <EmptyState
          title="Revision review is idle"
          description="Revision records appear here after one memory is selected."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Revision history"
      title="Ordered revisions"
      description="Revisions remain chronologically bounded so operators can verify how each memory changed over time."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge
            status={source ?? "unavailable"}
            label={
              source === "live"
                ? "Live revisions"
                : source === "fixture"
                  ? "Fixture revisions"
                  : "Revisions unavailable"
            }
          />
          {summary ? <span className="meta-pill">{summary.total_count} revisions</span> : null}
          {summary?.has_more ? <span className="meta-pill">More revisions available</span> : null}
        </div>

        {unavailableReason ? (
          <div className="execution-summary__note execution-summary__note--danger">
            <p className="execution-summary__label">Revision read</p>
            <p>{unavailableReason}</p>
          </div>
        ) : null}

        {revisions.length === 0 ? (
          <EmptyState
            title="No revisions returned"
            description="No revision records were returned for the selected memory."
          />
        ) : (
          <div className="timeline-list">
            {revisions.map((revision) => (
              <article key={revision.id} className="timeline-item">
                <div className="timeline-item__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">Sequence {revision.sequence_no}</span>
                    <h3 className="list-row__title mono">{revision.memory_key}</h3>
                  </div>
                  <StatusBadge status={revision.action.toLowerCase()} label={revision.action} />
                </div>

                <div className="timeline-item__meta">
                  <span className="meta-pill">{formatDate(revision.created_at)}</span>
                  <span className="meta-pill">{revision.source_event_ids.length} source events</span>
                </div>

                <div className="key-value-grid key-value-grid--compact">
                  <div>
                    <dt>Previous value</dt>
                    <dd className="mono">{formatValue(revision.previous_value)}</dd>
                  </div>
                  <div>
                    <dt>New value</dt>
                    <dd className="mono">{formatValue(revision.new_value)}</dd>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </SectionCard>
  );
}
