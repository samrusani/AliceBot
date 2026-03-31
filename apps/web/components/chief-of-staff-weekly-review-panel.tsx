"use client";

import { useState } from "react";

import type {
  ApiSource,
  ChiefOfStaffPriorityBrief,
  ChiefOfStaffRecommendationOutcome,
} from "../lib/api";
import { captureChiefOfStaffRecommendationOutcome } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffWeeklyReviewPanelProps = {
  apiBaseUrl?: string;
  userId?: string;
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

const OUTCOME_OPTIONS: Array<{ outcome: ChiefOfStaffRecommendationOutcome; label: string }> = [
  { outcome: "accept", label: "Accept" },
  { outcome: "defer", label: "Defer" },
  { outcome: "ignore", label: "Ignore" },
  { outcome: "rewrite", label: "Rewrite" },
];

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live weekly review";
  }
  if (source === "fixture") {
    return "Fixture weekly review";
  }
  return "Weekly review unavailable";
}

export function ChiefOfStaffWeeklyReviewPanel({
  apiBaseUrl,
  userId,
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffWeeklyReviewPanelProps) {
  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [rewriteTitle, setRewriteTitle] = useState("");
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    "Capture recommendation outcomes as accept/defer/ignore/rewrite to update learning rollups.",
  );

  async function captureOutcome(outcome: ChiefOfStaffRecommendationOutcome) {
    if (!brief || !apiBaseUrl || !userId || !liveModeReady) {
      setStatusTone("info");
      setStatusText("Outcome capture is available only when live API mode is configured.");
      return;
    }

    const normalizedRewriteTitle = rewriteTitle.trim();
    if (outcome === "rewrite" && normalizedRewriteTitle.length === 0) {
      setStatusTone("danger");
      setStatusText("Rewrite outcome requires a rewritten recommendation title.");
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText(`Capturing ${outcome} outcome...`);

    try {
      await captureChiefOfStaffRecommendationOutcome(apiBaseUrl, {
        user_id: userId,
        outcome,
        recommendation_action_type: brief.recommended_next_action.action_type,
        recommendation_title: brief.recommended_next_action.title,
        rewritten_title: outcome === "rewrite" ? normalizedRewriteTitle : undefined,
        target_priority_id: brief.recommended_next_action.target_priority_id,
        thread_id: brief.scope.thread_id ?? null,
        rationale: `Captured from weekly review controls as ${outcome}.`,
      });
      setStatusTone("success");
      setStatusText(
        `${outcome} captured. Refresh the page to see updated recommendation outcomes and learning summaries.`,
      );
      if (outcome === "rewrite") {
        setRewriteTitle("");
      }
    } catch (error) {
      setStatusTone("danger");
      setStatusText(
        `Unable to capture outcome: ${error instanceof Error ? error.message : "Request failed"}`,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (brief === null) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Weekly review and learning"
        description="Weekly review guidance and recommendation outcome learning are unavailable in this mode."
      >
        <EmptyState
          title="Weekly review unavailable"
          description="Weekly review and recommendation outcome-learning artifacts are unavailable in this mode."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Weekly review and learning"
      description="Deterministic close/defer/escalate review guidance, explicit recommendation-outcome capture, and explainable priority-learning drift signals."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <StatusBadge
            status={brief.pattern_drift_summary.posture}
            label={`Drift: ${brief.pattern_drift_summary.posture}`}
          />
          <span className="meta-pill">
            {brief.recommendation_outcomes.summary.total_count} outcomes
          </span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live weekly review read failed: {unavailableReason}</p>
        ) : null}

        <div className="composer-status" aria-live="polite">
          <StatusBadge
            status={
              isSubmitting
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
              isSubmitting
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
          <h3>Weekly rollup</h3>
          <div className="cluster">
            <span className="meta-pill">Total: {brief.weekly_review_brief.rollup.total_count}</span>
            <span className="meta-pill">Waiting: {brief.weekly_review_brief.rollup.waiting_for_count}</span>
            <span className="meta-pill">Blockers: {brief.weekly_review_brief.rollup.blocker_count}</span>
            <span className="meta-pill">Stale: {brief.weekly_review_brief.rollup.stale_count}</span>
          </div>
        </div>

        <div className="detail-group">
          <h3>Close / Defer / Escalate guidance</h3>
          <ul className="detail-stack">
            {brief.weekly_review_brief.guidance.map((item) => (
              <li key={`${item.action}-${item.rank}`} className="list-row">
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow mono">Rank #{item.rank}</span>
                    <span className="list-row__title">{item.action}</span>
                  </div>
                  <span className="meta-pill">Signals: {item.signal_count}</span>
                </div>
                <p>{item.rationale}</p>
              </li>
            ))}
          </ul>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Outcome capture controls</h3>
          <p className="muted-copy">
            Capture how you handled the current recommendation so future priority behavior changes remain visible and
            auditable.
          </p>
          <label className="detail-stack" htmlFor="chief-of-staff-rewrite-title">
            <span className="list-row__eyebrow mono">Rewrite title (only for rewrite)</span>
            <input
              id="chief-of-staff-rewrite-title"
              className="input"
              value={rewriteTitle}
              onChange={(event) => setRewriteTitle(event.target.value)}
              placeholder="Rewrite: ..."
              disabled={!liveModeReady || isSubmitting}
            />
          </label>
          <div className="composer-actions">
            {OUTCOME_OPTIONS.map((option) => (
              <button
                key={option.outcome}
                type="button"
                className="button button--ghost"
                onClick={() => captureOutcome(option.outcome)}
                disabled={!liveModeReady || isSubmitting}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="detail-group">
          <h3>Recommendation outcomes</h3>
          {brief.recommendation_outcomes.items.length === 0 ? (
            <p className="muted-copy">No recommendation outcomes captured for this scope.</p>
          ) : (
            <ul className="detail-stack">
              {brief.recommendation_outcomes.items.map((item) => (
                <li key={item.id} className="list-row">
                  <div className="list-row__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow mono">{item.created_at}</span>
                      <span className="list-row__title">{item.recommendation_title}</span>
                    </div>
                    <StatusBadge status={item.outcome} label={item.outcome} />
                  </div>
                  <p className="muted-copy">Action type: {item.recommendation_action_type}</p>
                  {item.rationale ? <p>{item.rationale}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Priority learning summary</h3>
          <div className="cluster">
            <span className="meta-pill">Accept: {brief.priority_learning_summary.accept_count}</span>
            <span className="meta-pill">Defer: {brief.priority_learning_summary.defer_count}</span>
            <span className="meta-pill">Ignore: {brief.priority_learning_summary.ignore_count}</span>
            <span className="meta-pill">Rewrite: {brief.priority_learning_summary.rewrite_count}</span>
          </div>
          <p>{brief.priority_learning_summary.priority_shift_explanation}</p>
          <p className="muted-copy">
            Acceptance rate: {brief.priority_learning_summary.acceptance_rate.toFixed(6)} | Override rate:{" "}
            {brief.priority_learning_summary.override_rate.toFixed(6)}
          </p>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Pattern drift summary</h3>
          <p>{brief.pattern_drift_summary.reason}</p>
          <ul className="detail-stack">
            {brief.pattern_drift_summary.supporting_signals.map((signal, index) => (
              <li key={`signal-${index}`} className="muted-copy">
                {signal}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </SectionCard>
  );
}
