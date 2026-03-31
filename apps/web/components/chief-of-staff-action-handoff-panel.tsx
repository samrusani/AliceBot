import type { ApiSource, ChiefOfStaffActionHandoffItem, ChiefOfStaffPriorityBrief } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffActionHandoffPanelProps = {
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live action handoff";
  }
  if (source === "fixture") {
    return "Fixture action handoff";
  }
  return "Action handoff unavailable";
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

function renderHandoffItem(item: ChiefOfStaffActionHandoffItem) {
  return (
    <li key={item.handoff_item_id} className="list-row">
      <div className="list-row__topline">
        <div className="detail-stack">
          <span className="list-row__eyebrow mono">Rank #{item.rank}</span>
          <span className="list-row__title">{item.title}</span>
        </div>
        <div className="cluster">
          <StatusBadge status={item.source_kind} label={item.source_kind} />
          <StatusBadge status={item.recommendation_action} label={item.recommendation_action} />
          <StatusBadge status={item.confidence_posture} label={`${item.confidence_posture} confidence`} />
        </div>
      </div>
      <p className="muted-copy">
        Handoff item: {item.handoff_item_id} | Score: {item.score.toFixed(6)}
      </p>
      <p>{item.rationale}</p>
      <p className="muted-copy">
        Task draft request: {item.task_draft.request.action} ({item.task_draft.request.scope})
      </p>
      <p className="muted-copy">
        Approval draft decision: {item.approval_draft.decision} | Auto submit:{" "}
        {item.approval_draft.auto_submit ? "enabled" : "disabled"}
      </p>
      {renderProvenance(item)}
    </li>
  );
}

export function ChiefOfStaffActionHandoffPanel({
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffActionHandoffPanelProps) {
  if (brief === null) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Action handoff"
        description="Action handoff artifacts are unavailable in this mode."
      >
        <EmptyState
          title="Action handoff unavailable"
          description="Action handoff artifacts are unavailable in this mode."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Action handoff"
      description="Deterministic recommendation-to-task/approval handoff artifacts with explicit approval-bounded execution posture."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <StatusBadge
            status={brief.execution_posture.posture}
            label={`Execution posture: ${brief.execution_posture.posture}`}
          />
          <span className="meta-pill">{brief.summary.handoff_item_count} handoff items</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live action handoff read failed: {unavailableReason}</p>
        ) : null}

        <div className="detail-group detail-group--muted">
          <h3>Action handoff brief</h3>
          <p>{brief.action_handoff_brief.summary}</p>
          <p className="muted-copy">{brief.action_handoff_brief.non_autonomous_guarantee}</p>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Primary task draft</h3>
          <p className="muted-copy">Mode: {brief.task_draft.mode}</p>
          <p className="muted-copy">
            Approval required: {brief.task_draft.approval_required ? "yes" : "no"} | Auto execute:{" "}
            {brief.task_draft.auto_execute ? "enabled" : "disabled"}
          </p>
          <p className="muted-copy">
            Request: {brief.task_draft.request.action} ({brief.task_draft.request.scope})
          </p>
          <p>{brief.task_draft.summary}</p>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Primary approval draft</h3>
          <p className="muted-copy">
            Decision: {brief.approval_draft.decision} | Auto submit:{" "}
            {brief.approval_draft.auto_submit ? "enabled" : "disabled"}
          </p>
          <p className="muted-copy">
            Request: {brief.approval_draft.request.action} ({brief.approval_draft.request.scope})
          </p>
          <p>{brief.approval_draft.reason}</p>
        </div>

        <div className="detail-group">
          <h3>Handoff items</h3>
          {brief.handoff_items.length === 0 ? (
            <p className="muted-copy">No handoff items were generated for this scope.</p>
          ) : (
            <ul className="detail-stack">{brief.handoff_items.map(renderHandoffItem)}</ul>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
