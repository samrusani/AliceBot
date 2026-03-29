import type { ApiSource, ContinuityResumptionBrief } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ResumptionBriefProps = {
  brief: ContinuityResumptionBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function renderSingleSection(
  heading: string,
  section: {
    item: ContinuityResumptionBrief["last_decision"]["item"];
    empty_state: ContinuityResumptionBrief["last_decision"]["empty_state"];
  },
) {
  if (section.item) {
    return (
      <div className="detail-group">
        <h3>{heading}</h3>
        <p className="list-row__title">{section.item.title}</p>
        <div className="cluster">
          <span className="meta-pill">{section.item.object_type}</span>
          <StatusBadge status={section.item.confirmation_status} label={section.item.confirmation_status} />
        </div>
      </div>
    );
  }

  return (
    <div className="detail-group detail-group--muted">
      <h3>{heading}</h3>
      <p className="muted-copy">{section.empty_state.message}</p>
    </div>
  );
}

export function ResumptionBrief({ brief, source, unavailableReason }: ResumptionBriefProps) {
  if (brief === null) {
    return (
      <SectionCard
        eyebrow="Resumption"
        title="Resumption brief"
        description="Compile deterministic resume artifacts from continuity objects."
      >
        <EmptyState
          title="Resumption unavailable"
          description="Resumption brief is not available in this mode yet."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Resumption"
      title="Resumption brief"
      description="Deterministic sections are compiled for last decision, open loops, recent changes, and next action."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge
            status={source}
            label={
              source === "live"
                ? "Live brief"
                : source === "fixture"
                  ? "Fixture brief"
                  : "Brief unavailable"
            }
          />
          <span className="meta-pill mono">{brief.assembly_version}</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live brief read failed: {unavailableReason}</p>
        ) : null}

        {renderSingleSection("Last decision", brief.last_decision)}

        <div className="detail-group">
          <h3>Open loops</h3>
          {brief.open_loops.items.length === 0 ? (
            <p className="muted-copy">{brief.open_loops.empty_state.message}</p>
          ) : (
            <ul className="detail-stack">
              {brief.open_loops.items.map((item) => (
                <li key={item.id} className="cluster">
                  <span className="meta-pill">{item.object_type}</span>
                  <span>{item.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="detail-group">
          <h3>Recent changes</h3>
          {brief.recent_changes.items.length === 0 ? (
            <p className="muted-copy">{brief.recent_changes.empty_state.message}</p>
          ) : (
            <ul className="detail-stack">
              {brief.recent_changes.items.map((item) => (
                <li key={item.id} className="cluster">
                  <span className="meta-pill">{item.object_type}</span>
                  <span>{item.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {renderSingleSection("Next action", brief.next_action)}
      </div>
    </SectionCard>
  );
}
