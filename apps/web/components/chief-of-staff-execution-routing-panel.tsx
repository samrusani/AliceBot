"use client";

import { useEffect, useState } from "react";

import type {
  ApiSource,
  ChiefOfStaffExecutionRouteTarget,
  ChiefOfStaffExecutionReadinessPosture,
  ChiefOfStaffExecutionRoutingAuditRecord,
  ChiefOfStaffExecutionRoutingSummary,
  ChiefOfStaffPriorityBrief,
  ChiefOfStaffRoutedHandoffItem,
} from "../lib/api";
import { captureChiefOfStaffExecutionRoutingAction } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffExecutionRoutingPanelProps = {
  apiBaseUrl?: string;
  userId?: string;
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

const ROUTE_TARGET_LABELS: Record<ChiefOfStaffExecutionRouteTarget, string> = {
  task_workflow_draft: "Route task draft",
  approval_workflow_draft: "Route approval draft",
  follow_up_draft_only: "Route follow-up draft",
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live execution routing";
  }
  if (source === "fixture") {
    return "Fixture execution routing";
  }
  return "Execution routing unavailable";
}

function formatRouteTarget(routeTarget: ChiefOfStaffExecutionRouteTarget) {
  return routeTarget.replaceAll("_", " ");
}

export function ChiefOfStaffExecutionRoutingPanel({
  apiBaseUrl,
  userId,
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffExecutionRoutingPanelProps) {
  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live");
  const [routingSummary, setRoutingSummary] = useState<ChiefOfStaffExecutionRoutingSummary | null>(
    brief?.execution_routing_summary ?? null,
  );
  const [routedItems, setRoutedItems] = useState<ChiefOfStaffRoutedHandoffItem[]>(
    brief?.routed_handoff_items ?? [],
  );
  const [routingAuditTrail, setRoutingAuditTrail] = useState<ChiefOfStaffExecutionRoutingAuditRecord[]>(
    brief?.routing_audit_trail ?? [],
  );
  const [readinessPosture, setReadinessPosture] = useState<ChiefOfStaffExecutionReadinessPosture | null>(
    brief?.execution_readiness_posture ?? null,
  );
  const [submittingRouteKey, setSubmittingRouteKey] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    "Route selected handoff items into governed draft paths with explicit audit transitions.",
  );

  useEffect(() => {
    setRoutingSummary(brief?.execution_routing_summary ?? null);
    setRoutedItems(brief?.routed_handoff_items ?? []);
    setRoutingAuditTrail(brief?.routing_audit_trail ?? []);
    setReadinessPosture(brief?.execution_readiness_posture ?? null);
    setSubmittingRouteKey(null);
    setStatusTone("info");
    setStatusText("Route selected handoff items into governed draft paths with explicit audit transitions.");
  }, [brief]);

  async function applyRoute(item: ChiefOfStaffRoutedHandoffItem, routeTarget: ChiefOfStaffExecutionRouteTarget) {
    if (!brief || !apiBaseUrl || !userId || !liveModeReady) {
      setStatusTone("info");
      setStatusText("Execution routing controls are available only when live API mode is configured.");
      return;
    }

    const routeKey = `${item.handoff_item_id}:${routeTarget}`;
    setSubmittingRouteKey(routeKey);
    setStatusTone("info");
    setStatusText(`Routing ${item.handoff_item_id} -> ${routeTarget}...`);

    try {
      const payload = await captureChiefOfStaffExecutionRoutingAction(apiBaseUrl, {
        user_id: userId,
        handoff_item_id: item.handoff_item_id,
        route_target: routeTarget,
        note: `Captured from execution routing controls as ${routeTarget}.`,
        thread_id: brief.scope.thread_id ?? null,
        task_id: brief.scope.task_id ?? null,
        project: brief.scope.project ?? null,
        person: brief.scope.person ?? null,
      });
      setRoutingSummary(payload.execution_routing_summary);
      setRoutedItems(payload.routed_handoff_items);
      setRoutingAuditTrail(payload.routing_audit_trail);
      setReadinessPosture(payload.execution_readiness_posture);
      setStatusTone("success");
      setStatusText(`Routed ${item.handoff_item_id} -> ${routeTarget}.`);
    } catch (error) {
      setStatusTone("danger");
      setStatusText(
        `Unable to capture routing action: ${error instanceof Error ? error.message : "Request failed"}`,
      );
    } finally {
      setSubmittingRouteKey(null);
    }
  }

  if (brief === null || routingSummary === null || readinessPosture === null) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Execution routing"
        description="Execution routing artifacts are unavailable in this mode."
      >
        <EmptyState
          title="Execution routing unavailable"
          description="Execution routing artifacts are unavailable in this mode."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Execution routing"
      description="Deterministic governed routing controls for draft-only task, approval, and follow-up execution preparation."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <StatusBadge status={readinessPosture.posture} label={`Readiness: ${readinessPosture.posture}`} />
          <span className="meta-pill">{routingSummary.routed_handoff_count} routed</span>
          <span className="meta-pill">{routingSummary.unrouted_handoff_count} unrouted</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live execution routing read failed: {unavailableReason}</p>
        ) : null}

        <div className="composer-status" aria-live="polite">
          <StatusBadge
            status={
              submittingRouteKey
                ? "submitting"
                : statusTone === "success"
                  ? "success"
                  : statusTone === "danger"
                    ? "error"
                    : liveModeReady
                      ? "ready"
                      : "unavailable"
            }
            label={
              submittingRouteKey
                ? "Submitting"
                : statusTone === "success"
                  ? "Captured"
                  : statusTone === "danger"
                    ? "Attention"
                    : liveModeReady
                      ? "Ready"
                      : "Unavailable"
            }
          />
          <span>{statusText}</span>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Execution readiness posture</h3>
          <p>{readinessPosture.reason}</p>
          <p className="muted-copy">{readinessPosture.non_autonomous_guarantee}</p>
          <p className="muted-copy">
            Approval required: {readinessPosture.approval_required ? "yes" : "no"} | Autonomous execution:{" "}
            {readinessPosture.autonomous_execution ? "enabled" : "disabled"} | External side effects:{" "}
            {readinessPosture.external_side_effects_allowed ? "allowed" : "blocked"}
          </p>
        </div>

        <div className="detail-group">
          <h3>Routed handoff items</h3>
          {routedItems.length === 0 ? (
            <p className="muted-copy">No handoff items are currently available for governed routing.</p>
          ) : (
            <ul className="detail-stack">
              {routedItems.map((item) => (
                <li key={item.handoff_item_id} className="list-row">
                  <div className="list-row__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow mono">Rank #{item.handoff_rank}</span>
                      <span className="list-row__title">{item.title}</span>
                    </div>
                    <div className="cluster">
                      <StatusBadge
                        status={item.is_routed ? "routed" : "not_routed"}
                        label={item.is_routed ? "Routed" : "Not routed"}
                      />
                      <StatusBadge status={item.source_kind} label={item.source_kind} />
                    </div>
                  </div>
                  <p className="muted-copy">
                    {item.handoff_item_id} | Routed targets: {item.routed_targets.length > 0 ? item.routed_targets.join(", ") : "none"}
                  </p>
                  <div className="composer-actions">
                    {item.available_route_targets.map((routeTarget) => {
                      const routeKey = `${item.handoff_item_id}:${routeTarget}`;
                      return (
                        <button
                          key={routeKey}
                          type="button"
                          className="button button--ghost"
                          disabled={!liveModeReady || submittingRouteKey !== null}
                          onClick={() => void applyRoute(item, routeTarget)}
                        >
                          {ROUTE_TARGET_LABELS[routeTarget]}
                        </button>
                      );
                    })}
                  </div>
                  {item.last_routing_transition ? (
                    <p className="muted-copy">
                      Last transition: {item.last_routing_transition.transition}{" -> "}
                      {formatRouteTarget(item.last_routing_transition.route_target)}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Routing audit trail</h3>
          {routingAuditTrail.length === 0 ? (
            <p className="muted-copy">No execution routing transitions captured for this scope.</p>
          ) : (
            <ul className="detail-stack">
              {routingAuditTrail.map((entry) => (
                <li key={entry.id} className="list-row">
                  <div className="list-row__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow mono">{entry.created_at}</span>
                      <span className="list-row__title">{entry.handoff_item_id}</span>
                    </div>
                    <StatusBadge status={entry.route_target} label={formatRouteTarget(entry.route_target)} />
                  </div>
                  <p className="muted-copy">
                    Transition: {entry.transition} | Previously routed: {entry.previously_routed ? "yes" : "no"}
                  </p>
                  <p>{entry.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
