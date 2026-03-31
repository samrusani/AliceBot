import type { ApiSource, ChiefOfStaffPriorityBrief } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffPriorityPanelProps = {
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live chief-of-staff brief";
  }
  if (source === "fixture") {
    return "Fixture chief-of-staff brief";
  }
  return "Chief-of-staff brief unavailable";
}

export function ChiefOfStaffPriorityPanel({
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffPriorityPanelProps) {
  if (brief === null) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Priority dashboard"
        description="Deterministic ranking, explicit rationale, and one recommended next action."
      >
        <EmptyState
          title="Chief-of-staff brief unavailable"
          description="Priority dashboard data is unavailable in this mode."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Priority dashboard"
      description="What matters now, why it matters, and what to do next with trust-aware confidence posture."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <span className="meta-pill">{brief.summary.returned_count} ranked</span>
          <span className="meta-pill">Quality: {brief.summary.quality_gate_status}</span>
          <span className="meta-pill">Retrieval: {brief.summary.retrieval_status}</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live chief-of-staff read failed: {unavailableReason}</p>
        ) : null}

        <div className="detail-group detail-group--muted">
          <div className="list-row__topline">
            <div className="detail-stack">
              <span className="list-row__eyebrow mono">Recommended next action</span>
              <span className="list-row__title">{brief.recommended_next_action.title}</span>
            </div>
            <div className="cluster">
              <StatusBadge
                status={brief.recommended_next_action.priority_posture ?? "unavailable"}
                label={brief.recommended_next_action.priority_posture ?? "No target"}
              />
              <StatusBadge
                status={brief.recommended_next_action.confidence_posture}
                label={`${brief.recommended_next_action.confidence_posture} confidence`}
              />
            </div>
          </div>
          <p>{brief.recommended_next_action.reason}</p>
          <p className="muted-copy">Action type: {brief.recommended_next_action.action_type}</p>
        </div>

        {brief.summary.trust_confidence_posture === "low" ? (
          <p className="responsive-note">
            Confidence is explicitly downgraded because memory trust posture is weak.
          </p>
        ) : null}

        {brief.ranked_items.length === 0 ? (
          <p className="muted-copy">No ranked priorities are available for the selected scope.</p>
        ) : (
          <ul className="detail-stack">
            {brief.ranked_items.map((item) => (
              <li key={item.id} className="list-row">
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow mono">Rank #{item.rank}</span>
                    <span className="list-row__title">{item.title}</span>
                  </div>
                  <div className="cluster">
                    <StatusBadge status={item.priority_posture} label={item.priority_posture} />
                    <StatusBadge
                      status={item.confidence_posture}
                      label={`${item.confidence_posture} confidence`}
                    />
                  </div>
                </div>

                <p className="muted-copy">{item.object_type}</p>
                <ul className="detail-stack">
                  {item.rationale.reasons.map((reason, index) => (
                    <li key={`${item.id}-reason-${index}`} className="muted-copy">
                      {reason}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
