import type { ApiSource, ThreadHealthDashboardSummary } from "../lib/api";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ThreadHealthDashboardProps = {
  dashboard: ThreadHealthDashboardSummary;
  source: ApiSource;
  unavailableReason?: string;
};

function postureBadge(posture: ThreadHealthDashboardSummary["posture"]) {
  if (posture === "healthy") {
    return { status: "ready", label: "Healthy posture" };
  }
  if (posture === "critical") {
    return { status: "error", label: "Critical posture" };
  }
  return { status: "requires_review", label: "Watch posture" };
}

function formatHours(value: number | null) {
  if (value == null) {
    return "Not yet active";
  }
  return `${value.toFixed(1)}h`;
}

export function ThreadHealthDashboard({
  dashboard,
  source,
  unavailableReason,
}: ThreadHealthDashboardProps) {
  const badge = postureBadge(dashboard.posture);

  return (
    <SectionCard
      eyebrow="Thread health"
      title="Conversation health posture"
      description="Keep recent, stale, and risky threads visible before diving into recall, open loops, or review queues."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={badge.status} label={badge.label} />
          <StatusBadge
            status={source}
            label={source === "live" ? "Live thread dashboard" : "Fixture thread dashboard"}
          />
          <span className="meta-pill">
            Recent within {dashboard.thresholds.recent_window_hours}h
          </span>
          <span className="meta-pill">
            Stale after {dashboard.thresholds.stale_window_hours}h
          </span>
        </div>

        {unavailableReason ? (
          <div className="execution-summary__note execution-summary__note--danger">
            <p className="execution-summary__label">Live source note</p>
            <p>{unavailableReason}</p>
          </div>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Total threads</dt>
            <dd>{dashboard.total_thread_count}</dd>
          </div>
          <div>
            <dt>Recent</dt>
            <dd>{dashboard.recent_thread_count}</dd>
          </div>
          <div>
            <dt>Stale</dt>
            <dd>{dashboard.stale_thread_count}</dd>
          </div>
          <div>
            <dt>Risky</dt>
            <dd>{dashboard.risky_thread_count}</dd>
          </div>
          <div>
            <dt>Watch</dt>
            <dd>{dashboard.watch_thread_count}</dd>
          </div>
          <div>
            <dt>Risk threshold</dt>
            <dd>{dashboard.thresholds.risky_score_threshold}</dd>
          </div>
        </dl>

        <div className="detail-group detail-group--muted">
          <span className="history-entry__label">Risky threads</span>
          {dashboard.risky_threads.length > 0 ? (
            <ul className="timeline-list">
              {dashboard.risky_threads.slice(0, 3).map((item) => (
                <li key={item.thread.id} className="timeline-item">
                  <p className="mono">{item.thread.title}</p>
                  <p>
                    Score {item.risk_score} · {item.unresolved_contradiction_count} contradictions ·{" "}
                    {item.stale_open_loop_count} stale loops
                  </p>
                  <p>{item.recommended_action}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-copy">No risky threads are currently surfaced.</p>
          )}
        </div>

        <div className="detail-group detail-group--muted">
          <span className="history-entry__label">Stale threads</span>
          {dashboard.stale_threads.length > 0 ? (
            <ul className="timeline-list">
              {dashboard.stale_threads.slice(0, 3).map((item) => (
                <li key={item.thread.id} className="timeline-item">
                  <p className="mono">{item.thread.title}</p>
                  <p>Last activity {formatHours(item.hours_since_last_activity)} ago.</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-copy">No stale threads are currently surfaced.</p>
          )}
        </div>

        <div className="detail-group detail-group--muted">
          <span className="history-entry__label">Recent threads</span>
          {dashboard.recent_threads.length > 0 ? (
            <ul className="timeline-list">
              {dashboard.recent_threads.slice(0, 3).map((item) => (
                <li key={item.thread.id} className="timeline-item">
                  <p className="mono">{item.thread.title}</p>
                  <p>
                    {item.conversation_event_count} conversation events · {item.operational_event_count} operational events
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-copy">No recent threads are currently surfaced.</p>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
