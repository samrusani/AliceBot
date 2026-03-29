import type { ApiSource, ContinuityDailyBrief } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityDailyBriefProps = {
  brief: ContinuityDailyBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function renderListSection(
  heading: string,
  section:
    | ContinuityDailyBrief["waiting_for_highlights"]
    | ContinuityDailyBrief["blocker_highlights"]
    | ContinuityDailyBrief["stale_items"],
) {
  return (
    <div className="detail-group">
      <h3>{heading}</h3>
      {section.items.length === 0 ? (
        <p className="muted-copy">{section.empty_state.message}</p>
      ) : (
        <ul className="detail-stack">
          {section.items.map((item) => (
            <li key={item.id} className="cluster">
              <span className="meta-pill">{item.object_type}</span>
              <span>{item.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ContinuityDailyBriefPanel({ brief, source, unavailableReason }: ContinuityDailyBriefProps) {
  if (brief === null) {
    return (
      <SectionCard
        eyebrow="Daily"
        title="Daily brief"
        description="Compose deterministic waiting-for, blocker, stale, and next-action sections for daily continuity review."
      >
        <EmptyState
          title="Daily brief unavailable"
          description="Daily brief is not available in this mode yet."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Daily"
      title="Daily brief"
      description="Daily review composes deterministic open-loop highlights and one next suggested action with explicit empty states."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge
            status={source}
            label={
              source === "live"
                ? "Live daily brief"
                : source === "fixture"
                  ? "Fixture daily brief"
                  : "Daily brief unavailable"
            }
          />
          <span className="meta-pill mono">{brief.assembly_version}</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live daily brief read failed: {unavailableReason}</p>
        ) : null}

        {renderListSection("Waiting for", brief.waiting_for_highlights)}
        {renderListSection("Blockers", brief.blocker_highlights)}
        {renderListSection("Stale", brief.stale_items)}

        <div className="detail-group">
          <h3>Next suggested action</h3>
          {brief.next_suggested_action.item ? (
            <div className="cluster">
              <span className="meta-pill">{brief.next_suggested_action.item.object_type}</span>
              <span>{brief.next_suggested_action.item.title}</span>
            </div>
          ) : (
            <p className="muted-copy">{brief.next_suggested_action.empty_state.message}</p>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
