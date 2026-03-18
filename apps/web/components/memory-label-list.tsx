import type { ApiSource, MemoryReviewLabelRecord, MemoryReviewLabelSummary } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type MemoryLabelListProps = {
  memoryId: string | null;
  labels: MemoryReviewLabelRecord[];
  summary: MemoryReviewLabelSummary | null;
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

export function MemoryLabelList({
  memoryId,
  labels,
  summary,
  source,
  unavailableReason,
}: MemoryLabelListProps) {
  if (!memoryId) {
    return (
      <SectionCard
        eyebrow="Review labels"
        title="No memory selected"
        description="Select one memory to inspect existing review labels and counts."
      >
        <EmptyState
          title="Label review is idle"
          description="The selected memory's label summary will appear here."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Review labels"
      title="Existing labels and counts"
      description="Labels remain visible and countable so review confidence can be checked before downstream decisions."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge
            status={source ?? "unavailable"}
            label={
              source === "live"
                ? "Live labels"
                : source === "fixture"
                  ? "Fixture labels"
                  : "Labels unavailable"
            }
          />
          <span className="meta-pill">{summary?.total_count ?? 0} total labels</span>
        </div>

        <div className="attribute-list" aria-label="Label counts">
          <span className="attribute-item">Correct: {summary?.counts_by_label.correct ?? 0}</span>
          <span className="attribute-item">Incorrect: {summary?.counts_by_label.incorrect ?? 0}</span>
          <span className="attribute-item">Outdated: {summary?.counts_by_label.outdated ?? 0}</span>
          <span className="attribute-item">
            Insufficient evidence: {summary?.counts_by_label.insufficient_evidence ?? 0}
          </span>
        </div>

        {unavailableReason ? (
          <div className="execution-summary__note execution-summary__note--danger">
            <p className="execution-summary__label">Label read</p>
            <p>{unavailableReason}</p>
          </div>
        ) : null}

        {labels.length === 0 ? (
          <EmptyState
            title="No labels yet"
            description="Use the submission form to add the first review label for this memory."
          />
        ) : (
          <div className="list-rows">
            {labels.map((label) => (
              <article key={label.id} className="list-row">
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{formatDate(label.created_at)}</span>
                    <h3 className="list-row__title">Reviewer {label.reviewer_user_id}</h3>
                  </div>
                  <StatusBadge status={label.label} />
                </div>

                <p>{label.note ?? "No reviewer note provided."}</p>

                <div className="list-row__meta">
                  <span className="meta-pill mono">{label.id}</span>
                  <span className="meta-pill mono">{label.memory_id}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </SectionCard>
  );
}
