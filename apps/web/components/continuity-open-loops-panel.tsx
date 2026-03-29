"use client";

import { useState } from "react";

import { useRouter } from "next/navigation";

import type {
  ApiSource,
  ContinuityOpenLoopDashboard,
  ContinuityOpenLoopPosture,
  ContinuityOpenLoopReviewAction,
} from "../lib/api";
import { applyContinuityOpenLoopReviewAction } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityOpenLoopsPanelProps = {
  apiBaseUrl?: string;
  userId?: string;
  dashboard: ContinuityOpenLoopDashboard | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

const GROUPS: Array<{ key: ContinuityOpenLoopPosture; label: string }> = [
  { key: "waiting_for", label: "Waiting for" },
  { key: "blocker", label: "Blockers" },
  { key: "stale", label: "Stale" },
  { key: "next_action", label: "Next action" },
];

const ACTION_LABELS: Array<{ action: ContinuityOpenLoopReviewAction; label: string }> = [
  { action: "done", label: "Done" },
  { action: "deferred", label: "Deferred" },
  { action: "still_blocked", label: "Still blocked" },
];

export function ContinuityOpenLoopsPanel({
  apiBaseUrl,
  userId,
  dashboard,
  source,
  unavailableReason,
}: ContinuityOpenLoopsPanelProps) {
  const router = useRouter();
  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    "Review one open-loop item and apply done/deferred/still_blocked actions.",
  );

  async function handleAction(
    continuityObjectId: string,
    action: ContinuityOpenLoopReviewAction,
    title: string,
  ) {
    if (!liveModeReady || !apiBaseUrl || !userId) {
      setStatusTone("info");
      setStatusText("Review actions are available only when live continuity API access is configured.");
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText(`Applying ${action}...`);

    try {
      const payload = await applyContinuityOpenLoopReviewAction(apiBaseUrl, continuityObjectId, {
        user_id: userId,
        action,
      });
      setStatusTone("success");
      setStatusText(
        `${action} applied to "${title}". Lifecycle is now ${payload.lifecycle_outcome}. Resumption has been refreshed.`,
      );
      router.refresh();
    } catch (error) {
      setStatusTone("danger");
      setStatusText(
        `Unable to apply review action: ${error instanceof Error ? error.message : "Request failed"}`,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (dashboard === null) {
    return (
      <SectionCard
        eyebrow="Open loops"
        title="Open-loop dashboard"
        description="Review waiting-for, blocker, stale, and next-action posture with deterministic grouping and ordering."
      >
        <EmptyState
          title="Open-loop dashboard unavailable"
          description="Open-loop dashboard is not available in this mode yet."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Open loops"
      title="Open-loop dashboard"
      description="Deterministic posture groups support daily continuity review and explicit action handling."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge
            status={source}
            label={
              source === "live"
                ? "Live open loops"
                : source === "fixture"
                  ? "Fixture open loops"
                  : "Open-loop dashboard unavailable"
            }
          />
          <span className="meta-pill">{dashboard.summary.total_count} total</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live open-loop dashboard read failed: {unavailableReason}</p>
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
                  ? "Applied"
                  : statusTone === "danger"
                    ? "Attention"
                    : liveModeReady
                      ? "Ready"
                      : "Unavailable"
            }
          />
          <span>{statusText}</span>
        </div>

        {GROUPS.map((group) => {
          const section = dashboard[group.key];
          return (
            <div key={group.key} className="detail-group">
              <h3>{group.label}</h3>
              {section.items.length === 0 ? (
                <p className="muted-copy">{section.empty_state.message}</p>
              ) : (
                <ul className="detail-stack">
                  {section.items.map((item) => (
                    <li key={item.id} className="list-row">
                      <div className="list-row__topline">
                        <div className="detail-stack">
                          <span className="list-row__eyebrow mono">{item.id}</span>
                          <span className="list-row__title">{item.title}</span>
                        </div>
                        <div className="cluster">
                          <span className="meta-pill">{item.object_type}</span>
                          <StatusBadge status={item.status} label={item.status} />
                        </div>
                      </div>

                      <div className="composer-actions">
                        {ACTION_LABELS.map((option) => (
                          <button
                            key={option.action}
                            type="button"
                            className="button button--ghost"
                            onClick={() => handleAction(item.id, option.action, item.title)}
                            disabled={!liveModeReady || isSubmitting}
                          >
                            {option.label}
                          </button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}
