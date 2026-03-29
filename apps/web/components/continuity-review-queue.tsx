import Link from "next/link";

import type {
  ApiSource,
  ContinuityReviewObject,
  ContinuityReviewQueueSummary,
  ContinuityReviewStatusFilter,
} from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityReviewQueueProps = {
  items: ContinuityReviewObject[];
  summary: ContinuityReviewQueueSummary | null;
  selectedObjectId: string;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
  filters: {
    status: ContinuityReviewStatusFilter;
    limit: number;
  };
};

const FILTER_OPTIONS: Array<{ value: ContinuityReviewStatusFilter; label: string }> = [
  { value: "correction_ready", label: "Correction ready" },
  { value: "active", label: "Active" },
  { value: "stale", label: "Stale" },
  { value: "superseded", label: "Superseded" },
  { value: "deleted", label: "Deleted" },
  { value: "all", label: "All" },
];

function formatTimestamp(value: string | null) {
  if (!value) {
    return "Never";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ContinuityReviewQueue({
  items,
  summary,
  selectedObjectId,
  source,
  unavailableReason,
  filters,
}: ContinuityReviewQueueProps) {
  return (
    <SectionCard
      eyebrow="Review"
      title="Continuity review queue"
      description="Inspect correction-ready continuity objects, filter posture, and choose one object to apply deterministic correction actions."
    >
      <div className="detail-stack">
        <form method="get" className="detail-stack">
          <div className="cluster">
            <StatusBadge
              status={source}
              label={
                source === "live"
                  ? "Live review queue"
                  : source === "fixture"
                    ? "Fixture review queue"
                    : "Review queue unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} queued</span> : null}
          </div>

          {unavailableReason ? (
            <p className="responsive-note">Live review queue read failed: {unavailableReason}</p>
          ) : null}

          <div className="grid grid--two">
            <div className="form-field">
              <label htmlFor="continuity-review-status">Status filter</label>
              <select id="continuity-review-status" name="review_status" defaultValue={filters.status}>
                {FILTER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="continuity-review-limit">Limit</label>
              <input
                id="continuity-review-limit"
                name="review_limit"
                type="number"
                min={1}
                max={100}
                defaultValue={String(filters.limit)}
              />
            </div>
          </div>

          <div className="composer-actions">
            <button type="submit" className="button">Refresh queue</button>
          </div>
        </form>

        {items.length === 0 ? (
          <EmptyState
            title="No review items"
            description="No continuity objects match the current review filter."
          />
        ) : (
          <div className="list-rows">
            {items.map((item) => {
              const isSelected = item.id === selectedObjectId;
              const href = `?review_object=${encodeURIComponent(item.id)}&review_status=${encodeURIComponent(filters.status)}&review_limit=${filters.limit}`;

              return (
                <article key={item.id} className="list-row">
                  <div className="list-row__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow mono">{item.id}</span>
                      <h3 className="list-row__title">{item.title}</h3>
                    </div>
                    <div className="cluster">
                      <StatusBadge status={item.status} label={item.status} />
                      <span className="meta-pill">{item.object_type}</span>
                    </div>
                  </div>

                  <div className="list-row__meta">
                    <span className="meta-pill">Confirmed: {formatTimestamp(item.last_confirmed_at)}</span>
                    <span className="meta-pill mono">confidence {item.confidence.toFixed(2)}</span>
                  </div>

                  <div className="composer-actions">
                    <Link
                      href={href}
                      className="button button--ghost"
                      aria-current={isSelected ? "true" : undefined}
                    >
                      {isSelected ? "Selected" : "Review"}
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </SectionCard>
  );
}
