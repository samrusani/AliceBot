import type { ApiSource, ChiefOfStaffFollowThroughItem, ChiefOfStaffPriorityBrief } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffFollowThroughPanelProps = {
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live follow-through";
  }
  if (source === "fixture") {
    return "Fixture follow-through";
  }
  return "Follow-through unavailable";
}

function renderItem(item: ChiefOfStaffFollowThroughItem) {
  return (
    <li key={item.id} className="list-row">
      <div className="list-row__topline">
        <div className="detail-stack">
          <span className="list-row__eyebrow mono">Rank #{item.rank}</span>
          <span className="list-row__title">{item.title}</span>
        </div>
        <div className="cluster">
          <StatusBadge status={item.follow_through_posture} label={item.follow_through_posture} />
          <StatusBadge status={item.recommendation_action} label={item.recommendation_action} />
        </div>
      </div>
      <p className="muted-copy">
        Priority posture: {item.current_priority_posture} | Age: {item.age_hours.toFixed(1)}h | Type: {item.object_type}
      </p>
      <p>{item.reason}</p>
    </li>
  );
}

function renderGroup(
  title: string,
  items: ChiefOfStaffFollowThroughItem[],
  emptyMessage: string,
) {
  return (
    <div className="detail-group" key={title}>
      <h3>{title}</h3>
      {items.length === 0 ? <p className="muted-copy">{emptyMessage}</p> : <ul className="detail-stack">{items.map(renderItem)}</ul>}
    </div>
  );
}

export function ChiefOfStaffFollowThroughPanel({
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffFollowThroughPanelProps) {
  if (brief === null) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Follow-through supervision"
        description="Overdue, stale waiting-for, and slipped commitment supervision is unavailable in this mode."
      >
        <EmptyState
          title="Follow-through unavailable"
          description="Follow-through supervision data is unavailable in this mode."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Follow-through supervision"
      description="Deterministic supervision queue for overdue, stale waiting-for, and slipped commitments with draft-only follow-up artifacts."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <StatusBadge
            status={brief.escalation_posture.posture}
            label={`Escalation: ${brief.escalation_posture.posture}`}
          />
          <span className="meta-pill">{brief.summary.follow_through_total_count} follow-through items</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live follow-through read failed: {unavailableReason}</p>
        ) : null}

        <div className="detail-group detail-group--muted">
          <div className="list-row__topline">
            <span className="list-row__eyebrow mono">Escalation rationale</span>
            <div className="cluster">
              <span className="meta-pill">Escalate: {brief.escalation_posture.escalate_count}</span>
              <span className="meta-pill">Nudge: {brief.escalation_posture.nudge_count}</span>
              <span className="meta-pill">Defer: {brief.escalation_posture.defer_count}</span>
            </div>
          </div>
          <p>{brief.escalation_posture.reason}</p>
        </div>

        <div className="detail-group detail-group--muted">
          <div className="list-row__topline">
            <div className="detail-stack">
              <span className="list-row__eyebrow mono">Draft follow-up artifact</span>
              <span className="list-row__title">
                {brief.draft_follow_up.status === "drafted"
                  ? brief.draft_follow_up.content.subject
                  : "No draft follow-up generated"}
              </span>
            </div>
            <StatusBadge status={brief.draft_follow_up.mode} label={brief.draft_follow_up.mode} />
          </div>
          <p className="muted-copy">Auto send: {brief.draft_follow_up.auto_send ? "enabled" : "disabled"}</p>
          <p>{brief.draft_follow_up.reason}</p>
          {brief.draft_follow_up.status === "drafted" ? (
            <pre className="panel-code">{brief.draft_follow_up.content.body}</pre>
          ) : null}
        </div>

        {renderGroup(
          "Overdue items",
          brief.overdue_items,
          "No overdue follow-through items for the current scope.",
        )}
        {renderGroup(
          "Stale waiting-for items",
          brief.stale_waiting_for_items,
          "No stale waiting-for items for the current scope.",
        )}
        {renderGroup(
          "Slipped commitments",
          brief.slipped_commitments,
          "No slipped commitments for the current scope.",
        )}
      </div>
    </SectionCard>
  );
}
