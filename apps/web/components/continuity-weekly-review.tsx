import type { ApiSource, ContinuityWeeklyReview } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityWeeklyReviewProps = {
  review: ContinuityWeeklyReview | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function renderSection(
  heading: string,
  section: ContinuityWeeklyReview["waiting_for"] | ContinuityWeeklyReview["blocker"] | ContinuityWeeklyReview["stale"] | ContinuityWeeklyReview["next_action"],
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
              <span className="meta-pill">{item.status}</span>
              <span>{item.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ContinuityWeeklyReviewPanel({ review, source, unavailableReason }: ContinuityWeeklyReviewProps) {
  if (review === null) {
    return (
      <SectionCard
        eyebrow="Weekly"
        title="Weekly review"
        description="Compile deterministic weekly posture rollups over waiting, blocker, stale, and next-action continuity seams."
      >
        <EmptyState
          title="Weekly review unavailable"
          description="Weekly review is not available in this mode yet."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Weekly"
      title="Weekly review"
      description="Weekly review keeps posture counts and grouped continuity sections deterministic and auditable."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge
            status={source}
            label={
              source === "live"
                ? "Live weekly review"
                : source === "fixture"
                  ? "Fixture weekly review"
                  : "Weekly review unavailable"
            }
          />
          <span className="meta-pill mono">{review.assembly_version}</span>
          <span className="meta-pill">{review.rollup.total_count} total</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live weekly review read failed: {unavailableReason}</p>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Waiting for</dt>
            <dd>{review.rollup.waiting_for_count}</dd>
          </div>
          <div>
            <dt>Blockers</dt>
            <dd>{review.rollup.blocker_count}</dd>
          </div>
          <div>
            <dt>Stale</dt>
            <dd>{review.rollup.stale_count}</dd>
          </div>
          <div>
            <dt>Next action</dt>
            <dd>{review.rollup.next_action_count}</dd>
          </div>
        </dl>

        {renderSection("Waiting for", review.waiting_for)}
        {renderSection("Blockers", review.blocker)}
        {renderSection("Stale", review.stale)}
        {renderSection("Next action", review.next_action)}
      </div>
    </SectionCard>
  );
}
