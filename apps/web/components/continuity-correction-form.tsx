"use client";

import type { FormEvent } from "react";
import { useMemo, useState } from "react";

import { useRouter } from "next/navigation";

import type {
  ApiSource,
  ContinuityCorrectionAction,
  ContinuityReviewDetail,
} from "../lib/api";
import { applyContinuityCorrection } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityCorrectionFormProps = {
  apiBaseUrl?: string;
  userId?: string;
  source: ApiSource | "unavailable";
  review: ContinuityReviewDetail | null;
};

const ACTION_OPTIONS: Array<{ value: ContinuityCorrectionAction; label: string }> = [
  { value: "confirm", label: "Confirm" },
  { value: "edit", label: "Edit" },
  { value: "delete", label: "Delete" },
  { value: "supersede", label: "Supersede" },
  { value: "mark_stale", label: "Mark stale" },
];

function parseOptionalNumber(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const parsed = Number.parseFloat(trimmed);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }
  return parsed;
}

export function ContinuityCorrectionForm({ apiBaseUrl, userId, source, review }: ContinuityCorrectionFormProps) {
  const router = useRouter();
  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live" && review);

  const [action, setAction] = useState<ContinuityCorrectionAction>("confirm");
  const [reason, setReason] = useState("");
  const [title, setTitle] = useState("");
  const [confidence, setConfidence] = useState("");
  const [replacementTitle, setReplacementTitle] = useState("");
  const [replacementConfidence, setReplacementConfidence] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    "Select one review object, then apply deterministic continuity corrections.",
  );

  const selectedObject = review?.continuity_object ?? null;

  const chainSummary = useMemo(() => {
    if (!review) {
      return "No object selected.";
    }
    const supersedes = review.supersession_chain.supersedes;
    const supersededBy = review.supersession_chain.superseded_by;
    if (!supersedes && !supersededBy) {
      return "No supersession chain links recorded.";
    }

    const parts: string[] = [];
    if (supersedes) {
      parts.push(`Supersedes: ${supersedes.title}`);
    }
    if (supersededBy) {
      parts.push(`Superseded by: ${supersededBy.title}`);
    }
    return parts.join(" | ");
  }, [review]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!liveModeReady || !apiBaseUrl || !userId || !selectedObject) {
      setStatusTone("info");
      setStatusText("Correction submit is unavailable until one live review object is selected.");
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Submitting correction...");

    try {
      await applyContinuityCorrection(apiBaseUrl, selectedObject.id, {
        user_id: userId,
        action,
        reason: reason.trim() || undefined,
        title: action === "edit" ? title.trim() || undefined : undefined,
        confidence: action === "edit" ? parseOptionalNumber(confidence) : undefined,
        replacement_title: action === "supersede" ? replacementTitle.trim() || undefined : undefined,
        replacement_confidence:
          action === "supersede" ? parseOptionalNumber(replacementConfidence) : undefined,
      });

      setStatusTone("success");
      setStatusText("Correction applied. Recall and resumption now reflect updated lifecycle state.");
      setReason("");
      setTitle("");
      setConfidence("");
      setReplacementTitle("");
      setReplacementConfidence("");
      router.refresh();
    } catch (error) {
      setStatusTone("danger");
      setStatusText(
        `Unable to apply correction: ${error instanceof Error ? error.message : "Request failed"}`,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!review) {
    return (
      <SectionCard
        eyebrow="Correction"
        title="Correction actions"
        description="Apply confirm/edit/delete/supersede/mark_stale actions to one selected continuity object."
      >
        <EmptyState
          title="No continuity object selected"
          description="Pick one item from the review queue to inspect supersession chain and submit corrections."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Correction"
      title="Correction actions"
      description="Corrections append immutable correction events before lifecycle mutation, then take effect in recall and resumption immediately."
    >
      <div className="detail-stack">
        <div className="cluster">
          <StatusBadge
            status={source}
            label={
              source === "live"
                ? "Live correction"
                : source === "fixture"
                  ? "Fixture correction"
                  : "Correction unavailable"
            }
          />
          <StatusBadge status={selectedObject?.status ?? "unknown"} label={selectedObject?.status ?? "Unknown"} />
          <span className="meta-pill">{selectedObject?.object_type}</span>
        </div>

        <div className="detail-group">
          <h3>{selectedObject?.title}</h3>
          <p className="muted-copy">{chainSummary}</p>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Recent correction events</h3>
          {review.correction_events.length === 0 ? (
            <p className="muted-copy">No corrections recorded yet.</p>
          ) : (
            <ul className="detail-stack">
              {review.correction_events.slice(0, 5).map((eventItem) => (
                <li key={eventItem.id} className="cluster">
                  <span className="meta-pill">{eventItem.action}</span>
                  <span>{eventItem.reason ?? "No reason provided"}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <form className="detail-stack" onSubmit={handleSubmit}>
          <div className="grid grid--two">
            <div className="form-field">
              <label htmlFor="continuity-correction-action">Action</label>
              <select
                id="continuity-correction-action"
                value={action}
                onChange={(event) => setAction(event.target.value as ContinuityCorrectionAction)}
                disabled={!liveModeReady || isSubmitting}
              >
                {ACTION_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="continuity-correction-reason">Reason (optional)</label>
              <input
                id="continuity-correction-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                maxLength={500}
                disabled={!liveModeReady || isSubmitting}
              />
            </div>

            {action === "edit" ? (
              <>
                <div className="form-field">
                  <label htmlFor="continuity-correction-title">Updated title (optional)</label>
                  <input
                    id="continuity-correction-title"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    maxLength={280}
                    disabled={!liveModeReady || isSubmitting}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="continuity-correction-confidence">Updated confidence (optional)</label>
                  <input
                    id="continuity-correction-confidence"
                    value={confidence}
                    onChange={(event) => setConfidence(event.target.value)}
                    placeholder="0.0 to 1.0"
                    disabled={!liveModeReady || isSubmitting}
                  />
                </div>
              </>
            ) : null}

            {action === "supersede" ? (
              <>
                <div className="form-field">
                  <label htmlFor="continuity-correction-replacement-title">Replacement title (optional)</label>
                  <input
                    id="continuity-correction-replacement-title"
                    value={replacementTitle}
                    onChange={(event) => setReplacementTitle(event.target.value)}
                    maxLength={280}
                    disabled={!liveModeReady || isSubmitting}
                  />
                </div>
                <div className="form-field">
                  <label htmlFor="continuity-correction-replacement-confidence">Replacement confidence (optional)</label>
                  <input
                    id="continuity-correction-replacement-confidence"
                    value={replacementConfidence}
                    onChange={(event) => setReplacementConfidence(event.target.value)}
                    placeholder="0.0 to 1.0"
                    disabled={!liveModeReady || isSubmitting}
                  />
                </div>
              </>
            ) : null}
          </div>

          <div className="composer-actions">
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

            <button type="submit" className="button" disabled={!liveModeReady || isSubmitting}>
              {isSubmitting ? "Submitting..." : "Apply correction"}
            </button>
          </div>
        </form>
      </div>
    </SectionCard>
  );
}
