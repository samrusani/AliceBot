"use client";

import type { FormEvent } from "react";
import { useRef, useState } from "react";

import { useRouter } from "next/navigation";

import type {
  ApiSource,
  MemoryReviewLabelValue,
  MemoryReviewQueuePriorityMode,
} from "../lib/api";
import { submitMemoryLabel } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type MemoryLabelFormProps = {
  memoryId: string | null;
  source: ApiSource | "unavailable" | null;
  apiBaseUrl?: string;
  userId?: string;
  activeFilter?: "active" | "queue";
  nextQueueMemoryId?: string | null;
  queuePriorityMode?: MemoryReviewQueuePriorityMode;
};

const LABEL_OPTIONS: Array<{
  value: MemoryReviewLabelValue;
  label: string;
}> = [
  { value: "correct", label: "Correct" },
  { value: "incorrect", label: "Incorrect" },
  { value: "outdated", label: "Outdated" },
  { value: "insufficient_evidence", label: "Insufficient evidence" },
];

export function MemoryLabelForm({
  memoryId,
  source,
  apiBaseUrl,
  userId,
  activeFilter = "active",
  nextQueueMemoryId = null,
  queuePriorityMode,
}: MemoryLabelFormProps) {
  const router = useRouter();
  const submitActionRef = useRef<"submit" | "submit_and_next">("submit");
  const liveModeReady = Boolean(memoryId && apiBaseUrl && userId && source === "live");
  const queueModeWithNext = activeFilter === "queue" && Boolean(nextQueueMemoryId);
  const [label, setLabel] = useState<MemoryReviewLabelValue>("correct");
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    !memoryId
      ? "Select a memory to enable label submission."
      : liveModeReady
        ? queueModeWithNext
          ? "Choose a label, then submit once or submit and move to the next queue item."
          : "Choose a label and submit when review is complete."
        : "Label submission is unavailable until live API configuration and live memory detail are present.",
  );
  const canSubmit = liveModeReady && !isSubmitting;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!memoryId) {
      setStatusTone("danger");
      setStatusText("Select a memory before submitting a label.");
      return;
    }

    if (!apiBaseUrl || !userId || source !== "live") {
      setStatusTone("info");
      setStatusText("Label submission is unavailable until live API configuration and live memory detail are present.");
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Submitting memory review label...");

    const submitAndNextRequested = submitActionRef.current === "submit_and_next";
    submitActionRef.current = "submit";

    try {
      const payload = await submitMemoryLabel(apiBaseUrl, memoryId, {
        user_id: userId,
        label,
        note: note.trim() ? note.trim() : null,
      });

      setStatusTone("success");
      if (submitAndNextRequested && activeFilter === "queue" && nextQueueMemoryId) {
        setStatusText("Label saved. Advancing to next queue memory.");
      } else {
        setStatusText(
          `Label saved. ${payload.summary.total_count} total label${payload.summary.total_count === 1 ? "" : "s"} now recorded for this memory.`,
        );
      }
      setNote("");
      if (submitAndNextRequested && activeFilter === "queue" && nextQueueMemoryId) {
        const priorityQuery = queuePriorityMode
          ? `&priority_mode=${encodeURIComponent(queuePriorityMode)}`
          : "";
        router.push(
          `/memories?filter=queue&memory=${encodeURIComponent(nextQueueMemoryId)}${priorityQuery}`,
        );
      } else {
        router.refresh();
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Submission failed";
      setStatusTone("danger");
      setStatusText(`Unable to submit label: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!memoryId) {
    return (
      <SectionCard
        eyebrow="Submit label"
        title="No memory selected"
        description="Select a memory from the list to submit a review label."
      >
        <EmptyState
          title="Label form is disabled"
          description="The submission surface activates after one memory is selected."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Submit label"
      title="Apply review label"
      description="Label submission is intentional: pick one label, add an optional note, then submit once."
    >
      <form className="detail-stack" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="memory-label-value">Review label</label>
          <select
            id="memory-label-value"
            name="memory-label-value"
            value={label}
            onChange={(event) => setLabel(event.target.value as MemoryReviewLabelValue)}
          >
            {LABEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label htmlFor="memory-label-note">Reviewer note (optional)</label>
          <textarea
            id="memory-label-note"
            name="memory-label-note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Capture why this label was chosen for later review."
            maxLength={280}
          />
          <p className="field-hint">{note.length}/280</p>
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
                        ? "info"
                        : "unavailable"
              }
              label={
                isSubmitting
                  ? "Submitting"
                  : statusTone === "success"
                    ? "Saved"
                    : statusTone === "danger"
                      ? "Attention"
                      : liveModeReady
                        ? "Ready"
                        : "Unavailable"
              }
            />
            <span>{statusText}</span>
          </div>
          <button
            type="submit"
            className="button"
            disabled={!canSubmit}
            onClick={() => {
              submitActionRef.current = "submit";
            }}
          >
            {isSubmitting ? "Submitting..." : "Submit review label"}
          </button>
          {queueModeWithNext ? (
            <button
              type="submit"
              value="submit_and_next"
              className="button-secondary"
              disabled={!canSubmit}
              onClick={() => {
                submitActionRef.current = "submit_and_next";
              }}
            >
              {isSubmitting ? "Submitting..." : "Submit and next in queue"}
            </button>
          ) : null}
        </div>
      </form>
    </SectionCard>
  );
}
