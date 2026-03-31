import type {
  ApiSource,
  ChiefOfStaffPreparationArtifactItem,
  ChiefOfStaffPriorityBrief,
  ChiefOfStaffResumptionSupervisionRecommendation,
} from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffPreparationPanelProps = {
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live preparation brief";
  }
  if (source === "fixture") {
    return "Fixture preparation brief";
  }
  return "Preparation brief unavailable";
}

function renderProvenance(item: {
  provenance_references: Array<{ source_kind: string; source_id: string }>;
}) {
  if (item.provenance_references.length === 0) {
    return <p className="muted-copy">Provenance: none attached</p>;
  }

  return (
    <p className="muted-copy">
      Provenance: {item.provenance_references.map((ref) => `${ref.source_kind}:${ref.source_id}`).join(" | ")}
    </p>
  );
}

function renderPreparationItem(item: ChiefOfStaffPreparationArtifactItem) {
  return (
    <li key={item.id} className="list-row">
      <div className="list-row__topline">
        <div className="detail-stack">
          <span className="list-row__eyebrow mono">Rank #{item.rank}</span>
          <span className="list-row__title">{item.title}</span>
        </div>
        <div className="cluster">
          <StatusBadge status={item.object_type} label={item.object_type} />
          <StatusBadge status={item.confidence_posture} label={`${item.confidence_posture} confidence`} />
        </div>
      </div>
      <p>{item.reason}</p>
      {renderProvenance(item)}
    </li>
  );
}

function renderResumptionRecommendation(item: ChiefOfStaffResumptionSupervisionRecommendation) {
  return (
    <li key={`${item.rank}-${item.title}`} className="list-row">
      <div className="list-row__topline">
        <div className="detail-stack">
          <span className="list-row__eyebrow mono">Rank #{item.rank}</span>
          <span className="list-row__title">{item.title}</span>
        </div>
        <div className="cluster">
          <StatusBadge status={item.action} label={item.action} />
          <StatusBadge status={item.confidence_posture} label={`${item.confidence_posture} confidence`} />
        </div>
      </div>
      <p>{item.reason}</p>
      {renderProvenance(item)}
    </li>
  );
}

function renderSection(
  title: string,
  items: ChiefOfStaffPreparationArtifactItem[],
  emptyMessage: string,
) {
  return (
    <div className="detail-group" key={title}>
      <h3>{title}</h3>
      {items.length === 0 ? <p className="muted-copy">{emptyMessage}</p> : <ul className="detail-stack">{items.map(renderPreparationItem)}</ul>}
    </div>
  );
}

export function ChiefOfStaffPreparationPanel({
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffPreparationPanelProps) {
  if (brief === null) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Preparation and resumption"
        description="Preparation brief artifacts are unavailable in this mode."
      >
        <EmptyState
          title="Preparation unavailable"
          description="Preparation and resumption artifacts are unavailable in this mode."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Preparation and resumption"
      description="Deterministic preparation brief, what-changed summary, prep checklist, suggested talking points, and trust-aware resumption supervision."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <StatusBadge
            status={brief.preparation_brief.confidence_posture}
            label={`${brief.preparation_brief.confidence_posture} preparation confidence`}
          />
          <span className="meta-pill">{brief.preparation_brief.summary.returned_count} context items</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live preparation read failed: {unavailableReason}</p>
        ) : null}

        <div className="detail-group detail-group--muted">
          <div className="list-row__topline">
            <span className="list-row__eyebrow mono">Confidence rationale</span>
            <StatusBadge
              status={brief.resumption_supervision.confidence_posture}
              label={`${brief.resumption_supervision.confidence_posture} resumption confidence`}
            />
          </div>
          <p>{brief.preparation_brief.confidence_reason}</p>
        </div>

        {renderSection(
          "Preparation context",
          brief.preparation_brief.context_items,
          "No preparation context items for this scope.",
        )}
        {renderSection(
          "What changed",
          brief.what_changed_summary.items,
          "No recent changes were detected for this scope.",
        )}
        {renderSection(
          "Prep checklist",
          brief.prep_checklist.items,
          "No checklist items were generated for this scope.",
        )}
        {renderSection(
          "Suggested talking points",
          brief.suggested_talking_points.items,
          "No talking points were generated for this scope.",
        )}

        <div className="detail-group">
          <h3>Resumption supervision</h3>
          {brief.resumption_supervision.recommendations.length === 0 ? (
            <p className="muted-copy">No resumption supervision recommendations were generated.</p>
          ) : (
            <ul className="detail-stack">{brief.resumption_supervision.recommendations.map(renderResumptionRecommendation)}</ul>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
