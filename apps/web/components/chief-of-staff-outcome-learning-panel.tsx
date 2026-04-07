"use client";

import { useEffect, useState } from "react";

import type {
  ApiSource,
  ChiefOfStaffClosureQualitySummary,
  ChiefOfStaffConversionSignalSummary,
  ChiefOfStaffHandoffOutcomeRecord,
  ChiefOfStaffHandoffOutcomeStatus,
  ChiefOfStaffHandoffOutcomeSummary,
  ChiefOfStaffPriorityBrief,
  ChiefOfStaffRoutedHandoffItem,
  ChiefOfStaffStaleIgnoredEscalationPosture,
} from "../lib/api";
import { captureChiefOfStaffHandoffOutcome } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffOutcomeLearningPanelProps = {
  apiBaseUrl?: string;
  userId?: string;
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

const OUTCOME_STATUS_LABELS: Record<ChiefOfStaffHandoffOutcomeStatus, string> = {
  reviewed: "Reviewed",
  approved: "Approved",
  rejected: "Rejected",
  rewritten: "Rewritten",
  executed: "Executed",
  ignored: "Ignored",
  expired: "Expired",
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live outcome learning";
  }
  if (source === "fixture") {
    return "Fixture outcome learning";
  }
  return "Outcome learning unavailable";
}

function renderOutcomeCaptureControls(
  item: ChiefOfStaffRoutedHandoffItem,
  options: {
    isSubmitting: boolean;
    liveModeReady: boolean;
    onCapture: (item: ChiefOfStaffRoutedHandoffItem, status: ChiefOfStaffHandoffOutcomeStatus) => Promise<void>;
  },
) {
  const { isSubmitting, liveModeReady, onCapture } = options;
  return (
    <li key={item.handoff_item_id} className="list-row">
      <div className="list-row__topline">
        <div className="detail-stack">
          <span className="list-row__eyebrow mono">Handoff #{item.handoff_rank}</span>
          <span className="list-row__title">{item.title}</span>
        </div>
        <div className="cluster">
          <StatusBadge status={item.source_kind} label={item.source_kind} />
          <StatusBadge status="routed" label="Routed" />
        </div>
      </div>
      <p className="muted-copy">
        {item.handoff_item_id} | Routed targets: {item.routed_targets.join(", ")}
      </p>
      <div className="composer-actions">
        {(Object.keys(OUTCOME_STATUS_LABELS) as ChiefOfStaffHandoffOutcomeStatus[]).map((status) => (
          <button
            key={`${item.handoff_item_id}-${status}`}
            type="button"
            className="button button--ghost"
            disabled={!liveModeReady || isSubmitting}
            onClick={() => void onCapture(item, status)}
          >
            {OUTCOME_STATUS_LABELS[status]}
          </button>
        ))}
      </div>
    </li>
  );
}

export function ChiefOfStaffOutcomeLearningPanel({
  apiBaseUrl,
  userId,
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffOutcomeLearningPanelProps) {
  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live");
  const [handoffOutcomeSummary, setHandoffOutcomeSummary] = useState<ChiefOfStaffHandoffOutcomeSummary | null>(
    brief?.handoff_outcome_summary ?? null,
  );
  const [handoffOutcomes, setHandoffOutcomes] = useState<ChiefOfStaffHandoffOutcomeRecord[]>(
    brief?.handoff_outcomes ?? [],
  );
  const [closureQualitySummary, setClosureQualitySummary] = useState<ChiefOfStaffClosureQualitySummary | null>(
    brief?.closure_quality_summary ?? null,
  );
  const [conversionSignalSummary, setConversionSignalSummary] = useState<ChiefOfStaffConversionSignalSummary | null>(
    brief?.conversion_signal_summary ?? null,
  );
  const [staleIgnoredEscalationPosture, setStaleIgnoredEscalationPosture] =
    useState<ChiefOfStaffStaleIgnoredEscalationPosture | null>(brief?.stale_ignored_escalation_posture ?? null);
  const [submittingKey, setSubmittingKey] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    "Capture explicit routed handoff outcomes to keep closure quality and conversion signals deterministic.",
  );

  useEffect(() => {
    setHandoffOutcomeSummary(brief?.handoff_outcome_summary ?? null);
    setHandoffOutcomes(brief?.handoff_outcomes ?? []);
    setClosureQualitySummary(brief?.closure_quality_summary ?? null);
    setConversionSignalSummary(brief?.conversion_signal_summary ?? null);
    setStaleIgnoredEscalationPosture(brief?.stale_ignored_escalation_posture ?? null);
    setSubmittingKey(null);
    setStatusTone("info");
    setStatusText("Capture explicit routed handoff outcomes to keep closure quality and conversion signals deterministic.");
  }, [brief]);

  async function captureOutcome(
    item: ChiefOfStaffRoutedHandoffItem,
    outcomeStatus: ChiefOfStaffHandoffOutcomeStatus,
  ) {
    if (!brief || !apiBaseUrl || !userId || !liveModeReady) {
      setStatusTone("info");
      setStatusText("Outcome capture controls are available only when live API mode is configured.");
      return;
    }

    const actionKey = `${item.handoff_item_id}:${outcomeStatus}`;
    setSubmittingKey(actionKey);
    setStatusTone("info");
    setStatusText(`Capturing ${outcomeStatus} for ${item.handoff_item_id}...`);

    try {
      const payload = await captureChiefOfStaffHandoffOutcome(apiBaseUrl, {
        user_id: userId,
        handoff_item_id: item.handoff_item_id,
        outcome_status: outcomeStatus,
        note: `Captured from outcome learning controls as ${outcomeStatus}.`,
        thread_id: brief.scope.thread_id ?? null,
        task_id: brief.scope.task_id ?? null,
        project: brief.scope.project ?? null,
        person: brief.scope.person ?? null,
      });
      setHandoffOutcomeSummary(payload.handoff_outcome_summary);
      setHandoffOutcomes(payload.handoff_outcomes);
      setClosureQualitySummary(payload.closure_quality_summary);
      setConversionSignalSummary(payload.conversion_signal_summary);
      setStaleIgnoredEscalationPosture(payload.stale_ignored_escalation_posture);
      setStatusTone("success");
      setStatusText(`Captured ${outcomeStatus} for ${item.handoff_item_id}.`);
    } catch (error) {
      setStatusTone("danger");
      setStatusText(
        `Unable to capture handoff outcome: ${error instanceof Error ? error.message : "Request failed"}`,
      );
    } finally {
      setSubmittingKey(null);
    }
  }

  if (
    brief === null ||
    handoffOutcomeSummary === null ||
    closureQualitySummary === null ||
    conversionSignalSummary === null ||
    staleIgnoredEscalationPosture === null
  ) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Outcome learning"
        description="Outcome-learning artifacts are unavailable in this mode."
      >
        <EmptyState
          title="Outcome learning unavailable"
          description="Outcome-learning artifacts are unavailable in this mode."
        />
      </SectionCard>
    );
  }

  const captureCandidates = brief.routed_handoff_items.filter((item) => item.is_routed);

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Outcome learning"
      description="Deterministic routed-handoff outcome capture with explainable closure quality, conversion signals, and stale/ignored escalation posture."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <StatusBadge status={closureQualitySummary.posture} label={`Closure: ${closureQualitySummary.posture}`} />
          <StatusBadge
            status={staleIgnoredEscalationPosture.posture}
            label={`Escalation: ${staleIgnoredEscalationPosture.posture}`}
          />
          <span className="meta-pill">{handoffOutcomeSummary.latest_total_count} latest outcomes</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live outcome-learning read failed: {unavailableReason}</p>
        ) : null}

        <div className="composer-status" aria-live="polite">
          <StatusBadge
            status={
              submittingKey
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
              submittingKey
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

        <div className="detail-group">
          <h3>Routed handoff outcome capture controls</h3>
          {captureCandidates.length === 0 ? (
            <p className="muted-copy">
              Route at least one handoff item in Execution routing before capturing outcomes.
            </p>
          ) : (
            <ul className="detail-stack">
              {captureCandidates.map((item) =>
                renderOutcomeCaptureControls(item, {
                  isSubmitting: submittingKey !== null,
                  liveModeReady,
                  onCapture: captureOutcome,
                }),
              )}
            </ul>
          )}
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Closure quality summary</h3>
          <p>{closureQualitySummary.reason}</p>
          <p className="muted-copy">{closureQualitySummary.explanation}</p>
          <div className="cluster">
            <span className="meta-pill">Closed loop: {closureQualitySummary.closed_loop_count}</span>
            <span className="meta-pill">Unresolved: {closureQualitySummary.unresolved_count}</span>
            <span className="meta-pill">Ignored: {closureQualitySummary.ignored_count}</span>
            <span className="meta-pill">Expired: {closureQualitySummary.expired_count}</span>
          </div>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Conversion signals</h3>
          <div className="cluster">
            <span className="meta-pill">
              Execution conversion: {conversionSignalSummary.recommendation_to_execution_conversion_rate.toFixed(6)}
            </span>
            <span className="meta-pill">
              Closure conversion: {conversionSignalSummary.recommendation_to_closure_conversion_rate.toFixed(6)}
            </span>
            <span className="meta-pill">Coverage: {conversionSignalSummary.capture_coverage_rate.toFixed(6)}</span>
          </div>
          <p className="muted-copy">{conversionSignalSummary.explanation}</p>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Stale / ignored escalation posture</h3>
          <p>{staleIgnoredEscalationPosture.reason}</p>
          <p className="muted-copy">{staleIgnoredEscalationPosture.guidance_posture_explanation}</p>
          <ul className="detail-stack">
            {staleIgnoredEscalationPosture.supporting_signals.map((signal, index) => (
              <li key={`stale-ignored-signal-${index}`} className="muted-copy">
                {signal}
              </li>
            ))}
          </ul>
        </div>

        <div className="detail-group">
          <h3>Captured handoff outcomes</h3>
          {handoffOutcomes.length === 0 ? (
            <p className="muted-copy">No handoff outcomes captured for this scope.</p>
          ) : (
            <ul className="detail-stack">
              {handoffOutcomes.map((outcome) => (
                <li key={outcome.id} className="list-row">
                  <div className="list-row__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow mono">{outcome.created_at}</span>
                      <span className="list-row__title">{outcome.handoff_item_id}</span>
                    </div>
                    <div className="cluster">
                      <StatusBadge status={outcome.outcome_status} label={OUTCOME_STATUS_LABELS[outcome.outcome_status]} />
                      {outcome.is_latest_outcome ? <StatusBadge status="latest" label="Latest" /> : null}
                    </div>
                  </div>
                  <p className="muted-copy">
                    Previous: {outcome.previous_outcome_status ?? "none"} | Note: {outcome.note ?? "none"}
                  </p>
                  <p>{outcome.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
