import type { ApiSource, ContinuityRecallResult, ContinuityRecallSummary } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityRecallPanelProps = {
  results: ContinuityRecallResult[];
  summary: ContinuityRecallSummary | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
  filters: {
    query: string;
    threadId: string;
    taskId: string;
    project: string;
    person: string;
    since: string;
    until: string;
    limit: number;
  };
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function toFixedRelevance(value: number) {
  if (!Number.isFinite(value)) {
    return "0.00";
  }
  return value.toFixed(2);
}

export function ContinuityRecallPanel({
  results,
  summary,
  source,
  unavailableReason,
  filters,
}: ContinuityRecallPanelProps) {
  return (
    <SectionCard
      eyebrow="Recall"
      title="Continuity recall"
      description="Query typed continuity objects with scoped filters and provenance-backed ranking."
    >
      <div className="detail-stack">
        <form method="get" className="detail-stack">
          <div className="cluster">
            <StatusBadge
              status={source}
              label={
                source === "live"
                  ? "Live recall"
                  : source === "fixture"
                    ? "Fixture recall"
                    : "Recall unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} matched</span> : null}
          </div>

          {unavailableReason ? (
            <p className="responsive-note">Live recall read failed: {unavailableReason}</p>
          ) : null}

          <div className="grid grid--two">
            <div className="form-field">
              <label htmlFor="continuity-recall-query">Query</label>
              <input id="continuity-recall-query" name="recall_query" defaultValue={filters.query} maxLength={4000} />
            </div>
            <div className="form-field">
              <label htmlFor="continuity-recall-limit">Limit</label>
              <input
                id="continuity-recall-limit"
                name="recall_limit"
                type="number"
                min={1}
                max={100}
                defaultValue={String(filters.limit)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="continuity-recall-thread">Thread ID</label>
              <input id="continuity-recall-thread" name="recall_thread" defaultValue={filters.threadId} />
            </div>
            <div className="form-field">
              <label htmlFor="continuity-recall-task">Task ID</label>
              <input id="continuity-recall-task" name="recall_task" defaultValue={filters.taskId} />
            </div>
            <div className="form-field">
              <label htmlFor="continuity-recall-project">Project</label>
              <input id="continuity-recall-project" name="recall_project" defaultValue={filters.project} />
            </div>
            <div className="form-field">
              <label htmlFor="continuity-recall-person">Person</label>
              <input id="continuity-recall-person" name="recall_person" defaultValue={filters.person} />
            </div>
            <div className="form-field">
              <label htmlFor="continuity-recall-since">Since (ISO datetime)</label>
              <input id="continuity-recall-since" name="recall_since" defaultValue={filters.since} />
            </div>
            <div className="form-field">
              <label htmlFor="continuity-recall-until">Until (ISO datetime)</label>
              <input id="continuity-recall-until" name="recall_until" defaultValue={filters.until} />
            </div>
          </div>

          <div className="composer-actions">
            <button type="submit" className="button">Run recall</button>
          </div>
        </form>

        {results.length === 0 ? (
          <EmptyState
            title="No recall hits"
            description="Try broader filters or a less specific query to retrieve continuity evidence."
          />
        ) : (
          <div className="list-rows">
            {results.map((item) => (
              <article key={item.id} className="list-row">
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{formatDate(item.created_at)}</span>
                    <h3 className="list-row__title">{item.title}</h3>
                  </div>
                  <div className="cluster">
                    <StatusBadge status={item.admission_posture} label={item.admission_posture} />
                    <span className="meta-pill">{item.object_type}</span>
                    <span className="meta-pill">{item.confirmation_status}</span>
                  </div>
                </div>
                <div className="list-row__meta">
                  <span className="meta-pill mono">score {toFixedRelevance(item.relevance)}</span>
                  <span className="meta-pill">freshness {item.ordering.freshness_posture}</span>
                  <span className="meta-pill">provenance {item.ordering.provenance_posture}</span>
                  <span className="meta-pill">supersession {item.ordering.supersession_posture}</span>
                  <span className="meta-pill">{item.provenance_references.length} provenance refs</span>
                  <span className="meta-pill">{item.scope_matches.length} scope matches</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </SectionCard>
  );
}
