"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { useRouter } from "next/navigation";

import type { ApiSource, ContinuityCaptureExplicitSignal, ContinuityCaptureInboxItem } from "../lib/api";
import { createContinuityCapture } from "../lib/api";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ContinuityCaptureFormProps = {
  apiBaseUrl?: string;
  userId?: string;
  source: ApiSource | "unavailable";
};

const SIGNAL_OPTIONS: Array<{
  value: ContinuityCaptureExplicitSignal;
  label: string;
}> = [
  { value: "remember_this", label: "Remember This" },
  { value: "task", label: "Task" },
  { value: "decision", label: "Decision" },
  { value: "commitment", label: "Commitment" },
  { value: "waiting_for", label: "Waiting For" },
  { value: "blocker", label: "Blocker" },
  { value: "next_action", label: "Next Action" },
  { value: "note", label: "Note" },
];

function admissionMessage(item: ContinuityCaptureInboxItem) {
  if (item.derived_object) {
    return `Derived ${item.derived_object.object_type} with provenance from capture ${item.capture_event.id}.`;
  }
  return "Capture persisted with TRIAGE posture. No durable object was created.";
}

export function ContinuityCaptureForm({ apiBaseUrl, userId, source }: ContinuityCaptureFormProps) {
  const router = useRouter();
  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live");

  const [rawContent, setRawContent] = useState("");
  const [explicitSignal, setExplicitSignal] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [statusText, setStatusText] = useState(
    liveModeReady
      ? "Capture one note quickly. Explicit signals deterministically map to typed continuity objects."
      : "Capture submission is unavailable until live API configuration is present.",
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!liveModeReady || !apiBaseUrl || !userId) {
      setStatusTone("info");
      setStatusText("Capture submission is unavailable until live API configuration is present.");
      return;
    }

    if (!rawContent.trim()) {
      setStatusTone("danger");
      setStatusText("Enter capture text before submitting.");
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Submitting capture...");

    try {
      const payload = await createContinuityCapture(apiBaseUrl, {
        user_id: userId,
        raw_content: rawContent.trim(),
        explicit_signal: explicitSignal
          ? (explicitSignal as ContinuityCaptureExplicitSignal)
          : null,
      });

      setRawContent("");
      setExplicitSignal("");
      setStatusTone("success");
      setStatusText(admissionMessage(payload.capture));
      router.refresh();
    } catch (error) {
      setStatusTone("danger");
      setStatusText(
        `Unable to submit capture: ${error instanceof Error ? error.message : "Request failed"}`,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <SectionCard
      eyebrow="Fast capture"
      title="Continuity intake"
      description="Every submit appends one immutable capture event. Durable objects are only promoted when explicit or high-confidence signals are present."
    >
      <form className="detail-stack" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="continuity-capture-text">Capture text</label>
          <textarea
            id="continuity-capture-text"
            name="continuity-capture-text"
            value={rawContent}
            onChange={(event) => setRawContent(event.target.value)}
            placeholder="Capture something worth keeping..."
            maxLength={4000}
            disabled={!liveModeReady || isSubmitting}
          />
          <p className="field-hint">{rawContent.length}/4000</p>
        </div>

        <div className="form-field">
          <label htmlFor="continuity-capture-signal">Explicit signal (optional)</label>
          <select
            id="continuity-capture-signal"
            name="continuity-capture-signal"
            value={explicitSignal}
            onChange={(event) => setExplicitSignal(event.target.value)}
            disabled={!liveModeReady || isSubmitting}
          >
            <option value="">Auto triage (no explicit signal)</option>
            {SIGNAL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
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
            disabled={!liveModeReady || !rawContent.trim() || isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Capture"}
          </button>
        </div>
      </form>
    </SectionCard>
  );
}
