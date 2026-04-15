import type { ApiSource, MemoryHygieneDashboardSummary } from "../lib/api";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type MemoryHygieneDashboardProps = {
  dashboard: MemoryHygieneDashboardSummary;
  source: ApiSource;
  unavailableReason?: string;
};

function postureBadge(posture: MemoryHygieneDashboardSummary["posture"]) {
  if (posture === "healthy") {
    return { status: "ready", label: "Healthy posture" };
  }
  if (posture === "critical") {
    return { status: "error", label: "Critical posture" };
  }
  return { status: "requires_review", label: "Watch posture" };
}

export function MemoryHygieneDashboard({
  dashboard,
  source,
  unavailableReason,
}: MemoryHygieneDashboardProps) {
  const badge = postureBadge(dashboard.posture);

  return (
    <SectionCard
      eyebrow="Memory hygiene"
      title="Operational hygiene posture"
      description="Surface duplicate facts, stale truth, contradictions, weak trust, and queue pressure before item-by-item review."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={badge.status} label={badge.label} />
          <StatusBadge
            status={source}
            label={source === "live" ? "Live hygiene dashboard" : "Fixture hygiene dashboard"}
          />
        </div>

        <p>{dashboard.reason}</p>
        {unavailableReason ? (
          <div className="execution-summary__note execution-summary__note--danger">
            <p className="execution-summary__label">Live source note</p>
            <p>{unavailableReason}</p>
          </div>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Duplicate groups</dt>
            <dd>{dashboard.duplicate_group_count}</dd>
          </div>
          <div>
            <dt>Duplicate memories</dt>
            <dd>{dashboard.duplicate_memory_count}</dd>
          </div>
          <div>
            <dt>Stale facts</dt>
            <dd>{dashboard.stale_fact_count}</dd>
          </div>
          <div>
            <dt>Unresolved contradictions</dt>
            <dd>{dashboard.unresolved_contradiction_count}</dd>
          </div>
          <div>
            <dt>Weak trust</dt>
            <dd>{dashboard.weak_trust_count}</dd>
          </div>
          <div>
            <dt>Queue pressure</dt>
            <dd>{dashboard.review_queue_pressure.total_count}</dd>
          </div>
        </dl>

        <div className="detail-group detail-group--muted">
          <span className="history-entry__label">Focus queue</span>
          {dashboard.focus.length > 0 ? (
            <ul className="timeline-list">
              {dashboard.focus.map((item) => (
                <li key={item.kind} className="timeline-item">
                  <p className="mono">{item.kind}</p>
                  <p>{item.reason}</p>
                  <p>{item.action}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-copy">No active hygiene issues are currently surfaced.</p>
          )}
        </div>

        <div className="detail-group detail-group--muted">
          <span className="history-entry__label">Duplicate groups</span>
          {dashboard.duplicate_groups.length > 0 ? (
            <ul className="timeline-list">
              {dashboard.duplicate_groups.slice(0, 3).map((group) => (
                <li key={group.group_key} className="timeline-item">
                  <p className="mono">{group.memory_keys.join(", ")}</p>
                  <p>{group.count} memories share one normalized value.</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-copy">No duplicate fact groups are currently visible.</p>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
