"use client";

import { useEffect, useState } from "react";

import type {
  ApiSource,
  ChiefOfStaffHandoffQueueGroups,
  ChiefOfStaffHandoffQueueItem,
  ChiefOfStaffHandoffQueueLifecycleState,
  ChiefOfStaffHandoffQueueSummary,
  ChiefOfStaffHandoffReviewAction,
  ChiefOfStaffHandoffReviewActionRecord,
  ChiefOfStaffPriorityBrief,
} from "../lib/api";
import { captureChiefOfStaffHandoffReviewAction } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ChiefOfStaffHandoffQueuePanelProps = {
  apiBaseUrl?: string;
  userId?: string;
  brief: ChiefOfStaffPriorityBrief | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

const DEFAULT_STATE_ORDER: ChiefOfStaffHandoffQueueLifecycleState[] = [
  "ready",
  "pending_approval",
  "executed",
  "stale",
  "expired",
];

const ACTION_LABELS: Record<ChiefOfStaffHandoffReviewAction, string> = {
  mark_ready: "Mark ready",
  mark_pending_approval: "Mark pending approval",
  mark_executed: "Mark executed",
  mark_stale: "Mark stale",
  mark_expired: "Mark expired",
};

function sourceLabel(source: ApiSource | "unavailable") {
  if (source === "live") {
    return "Live handoff queue";
  }
  if (source === "fixture") {
    return "Fixture handoff queue";
  }
  return "Handoff queue unavailable";
}

function formatLifecycleState(state: ChiefOfStaffHandoffQueueLifecycleState) {
  return state.replaceAll("_", " ");
}

function renderQueueItem(
  item: ChiefOfStaffHandoffQueueItem,
  options: {
    isSubmitting: boolean;
    liveModeReady: boolean;
    onApply: (item: ChiefOfStaffHandoffQueueItem, action: ChiefOfStaffHandoffReviewAction) => Promise<void>;
  },
) {
  const { isSubmitting, liveModeReady, onApply } = options;
  return (
    <li key={item.handoff_item_id} className="list-row">
      <div className="list-row__topline">
        <div className="detail-stack">
          <span className="list-row__eyebrow mono">Queue #{item.queue_rank}</span>
          <span className="list-row__title">{item.title}</span>
        </div>
        <div className="cluster">
          <StatusBadge status={item.lifecycle_state} label={formatLifecycleState(item.lifecycle_state)} />
          <StatusBadge status={item.recommendation_action} label={item.recommendation_action} />
          <StatusBadge status={item.confidence_posture} label={`${item.confidence_posture} confidence`} />
        </div>
      </div>

      <p className="muted-copy">
        Handoff #{item.handoff_rank} ({item.handoff_item_id}) | Score: {item.score.toFixed(6)}
      </p>
      {item.age_hours_relative_to_latest !== null ? (
        <p className="muted-copy">Age relative to latest source: {item.age_hours_relative_to_latest.toFixed(1)}h</p>
      ) : null}
      <p>{item.state_reason}</p>

      <div className="composer-actions">
        {item.available_review_actions.map((action) => (
          <button
            key={`${item.handoff_item_id}-${action}`}
            type="button"
            className="button button--ghost"
            disabled={!liveModeReady || isSubmitting}
            onClick={() => void onApply(item, action)}
          >
            {ACTION_LABELS[action]}
          </button>
        ))}
      </div>
    </li>
  );
}

export function ChiefOfStaffHandoffQueuePanel({
  apiBaseUrl,
  userId,
  brief,
  source,
  unavailableReason,
}: ChiefOfStaffHandoffQueuePanelProps) {
  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live");
  const [queueSummary, setQueueSummary] = useState<ChiefOfStaffHandoffQueueSummary | null>(
    brief?.handoff_queue_summary ?? null,
  );
  const [queueGroups, setQueueGroups] = useState<ChiefOfStaffHandoffQueueGroups | null>(
    brief?.handoff_queue_groups ?? null,
  );
  const [reviewActions, setReviewActions] = useState<ChiefOfStaffHandoffReviewActionRecord[]>(
    brief?.handoff_review_actions ?? [],
  );
  const [submittingItemId, setSubmittingItemId] = useState<string | null>(null);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    "Use explicit review actions to transition queue posture without autonomous side effects.",
  );

  useEffect(() => {
    setQueueSummary(brief?.handoff_queue_summary ?? null);
    setQueueGroups(brief?.handoff_queue_groups ?? null);
    setReviewActions(brief?.handoff_review_actions ?? []);
    setSubmittingItemId(null);
    setStatusTone("info");
    setStatusText("Use explicit review actions to transition queue posture without autonomous side effects.");
  }, [brief]);

  async function applyReviewAction(
    item: ChiefOfStaffHandoffQueueItem,
    action: ChiefOfStaffHandoffReviewAction,
  ) {
    if (!brief || !apiBaseUrl || !userId || !liveModeReady) {
      setStatusTone("info");
      setStatusText("Review actions are available only when live API mode is configured.");
      return;
    }

    setSubmittingItemId(item.handoff_item_id);
    setStatusTone("info");
    setStatusText(`Applying ${action} to ${item.handoff_item_id}...`);

    try {
      const payload = await captureChiefOfStaffHandoffReviewAction(apiBaseUrl, {
        user_id: userId,
        handoff_item_id: item.handoff_item_id,
        review_action: action,
        note: `Captured from handoff queue controls as ${action}.`,
        thread_id: brief.scope.thread_id ?? null,
        task_id: brief.scope.task_id ?? null,
        project: brief.scope.project ?? null,
        person: brief.scope.person ?? null,
      });
      setQueueSummary(payload.handoff_queue_summary);
      setQueueGroups(payload.handoff_queue_groups);
      setReviewActions(payload.handoff_review_actions);
      setStatusTone("success");
      setStatusText(`Applied ${action} to ${item.handoff_item_id}.`);
    } catch (error) {
      setStatusTone("danger");
      setStatusText(
        `Unable to apply review action: ${error instanceof Error ? error.message : "Request failed"}`,
      );
    } finally {
      setSubmittingItemId(null);
    }
  }

  if (brief === null || queueSummary === null || queueGroups === null) {
    return (
      <SectionCard
        eyebrow="Chief of staff"
        title="Handoff queue"
        description="Handoff queue artifacts are unavailable in this mode."
      >
        <EmptyState
          title="Handoff queue unavailable"
          description="Handoff queue artifacts are unavailable in this mode."
        />
      </SectionCard>
    );
  }

  const stateOrder = queueSummary.state_order.length > 0 ? queueSummary.state_order : DEFAULT_STATE_ORDER;

  return (
    <SectionCard
      eyebrow="Chief of staff"
      title="Handoff queue"
      description="Deterministic grouped queue posture with explicit operator lifecycle review controls."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge status={source} label={sourceLabel(source)} />
          <span className="meta-pill">{queueSummary.total_count} queued</span>
          <span className="meta-pill">{queueSummary.stale_count} stale</span>
          <span className="meta-pill">{queueSummary.expired_count} expired</span>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live handoff queue read failed: {unavailableReason}</p>
        ) : null}

        <div className="composer-status" aria-live="polite">
          <StatusBadge
            status={
              submittingItemId
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
              submittingItemId
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

        {stateOrder.map((lifecycleState) => {
          const group = queueGroups[lifecycleState];
          return (
            <div key={lifecycleState} className="detail-group">
              <h3>
                {formatLifecycleState(lifecycleState)} ({group.summary.total_count})
              </h3>
              {group.items.length === 0 ? (
                <p className="muted-copy">{group.empty_state.message}</p>
              ) : (
                <ul className="detail-stack">
                  {group.items.map((item) =>
                    renderQueueItem(item, {
                      isSubmitting: submittingItemId !== null,
                      liveModeReady,
                      onApply: applyReviewAction,
                    }),
                  )}
                </ul>
              )}
            </div>
          );
        })}

        <div className="detail-group detail-group--muted">
          <h3>Review action history</h3>
          {reviewActions.length === 0 ? (
            <p className="muted-copy">No explicit handoff review actions captured for this scope.</p>
          ) : (
            <ul className="detail-stack">
              {reviewActions.map((action) => (
                <li key={action.id} className="list-row">
                  <div className="list-row__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow mono">{action.created_at}</span>
                      <span className="list-row__title">{action.handoff_item_id}</span>
                    </div>
                    <StatusBadge status={action.review_action} label={ACTION_LABELS[action.review_action]} />
                  </div>
                  <p className="muted-copy">
                    {action.previous_lifecycle_state ?? "none"} → {action.next_lifecycle_state}
                  </p>
                  <p>{action.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
