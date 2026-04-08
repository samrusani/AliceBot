"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";

import { useRouter } from "next/navigation";

import type { ApiSource, ApprovalExecutionResponse, ToolExecutionItem } from "../lib/api";
import { admitMemory } from "../lib/api";
import { StatusBadge } from "./status-badge";

type WorkflowMemoryWritebackFormProps = {
  execution: ToolExecutionItem | null;
  preview?: ApprovalExecutionResponse | null;
  source?: ApiSource | null;
  apiBaseUrl?: string;
  userId?: string;
};

function deriveExecutionEvidenceEventIds(
  execution: ToolExecutionItem | null,
  preview?: ApprovalExecutionResponse | null,
) {
  const ids: string[] = [];

  const previewResultEventId = preview?.events?.result_event_id?.trim();
  const previewRequestEventId = preview?.events?.request_event_id?.trim();
  const executionResultEventId = execution?.result_event_id?.trim();
  const executionRequestEventId = execution?.request_event_id?.trim();

  if (previewResultEventId) {
    ids.push(previewResultEventId);
  }
  if (previewRequestEventId) {
    ids.push(previewRequestEventId);
  }
  if (executionResultEventId) {
    ids.push(executionResultEventId);
  }
  if (executionRequestEventId) {
    ids.push(executionRequestEventId);
  }

  return Array.from(new Set(ids));
}

function defaultStatusText(options: {
  hasExecutionEvidence: boolean;
  liveModeReady: boolean;
  source: ApiSource | null;
  hasPreview: boolean;
}) {
  if (!options.hasExecutionEvidence) {
    return "Execution evidence is required before memory write-back can be submitted.";
  }

  if (!options.liveModeReady) {
    return "Memory write-back is disabled until live API configuration is present.";
  }

  if (options.hasPreview || options.source === "live") {
    return "Set memory key and JSON value, then submit explicit write-back.";
  }

  return "Fixture workflow review is read-only. Memory write-back submits only from live workflow data.";
}

export function WorkflowMemoryWritebackForm({
  execution,
  preview,
  source,
  apiBaseUrl,
  userId,
}: WorkflowMemoryWritebackFormProps) {
  const router = useRouter();

  const [memoryKey, setMemoryKey] = useState("");
  const [valueText, setValueText] = useState("");
  const [deleteRequested, setDeleteRequested] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const evidenceEventIds = useMemo(
    () => deriveExecutionEvidenceEventIds(execution, preview),
    [execution, preview],
  );
  const liveModeReady = Boolean(apiBaseUrl && userId);
  const liveWorkflowEvidence = source === "live" || Boolean(preview);
  const canSubmit = Boolean(liveModeReady && liveWorkflowEvidence && evidenceEventIds.length > 0 && !isSubmitting);
  const [statusText, setStatusText] = useState(
    defaultStatusText({
      hasExecutionEvidence: evidenceEventIds.length > 0,
      liveModeReady,
      source: source ?? null,
      hasPreview: Boolean(preview),
    }),
  );

  useEffect(() => {
    setStatusTone("info");
    setStatusText(
      defaultStatusText({
        hasExecutionEvidence: evidenceEventIds.length > 0,
        liveModeReady,
        source: source ?? null,
        hasPreview: Boolean(preview),
      }),
    );
  }, [evidenceEventIds.length, liveModeReady, preview, source]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedMemoryKey = memoryKey.trim();
    if (!normalizedMemoryKey) {
      setStatusTone("danger");
      setStatusText("Memory key is required.");
      return;
    }

    if (!canSubmit || !apiBaseUrl || !userId) {
      setStatusTone("info");
      setStatusText(
        defaultStatusText({
          hasExecutionEvidence: evidenceEventIds.length > 0,
          liveModeReady,
          source: source ?? null,
          hasPreview: Boolean(preview),
        }),
      );
      return;
    }

    let parsedValue: unknown = null;

    if (!deleteRequested) {
      const normalizedValueText = valueText.trim();
      if (!normalizedValueText) {
        setStatusTone("danger");
        setStatusText("Enter a JSON value or enable delete mode.");
        return;
      }

      try {
        parsedValue = JSON.parse(normalizedValueText);
      } catch {
        setStatusTone("danger");
        setStatusText("Memory value must be valid JSON.");
        return;
      }
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Submitting explicit memory write-back...");

    try {
      const payload = await admitMemory(apiBaseUrl, {
        user_id: userId,
        memory_key: normalizedMemoryKey,
        value: deleteRequested ? null : parsedValue,
        source_event_ids: evidenceEventIds,
        delete_requested: deleteRequested,
      });

      const decisionMessage =
        payload.decision === "NOOP"
          ? `No write was persisted (${payload.reason}).`
          : payload.revision
            ? `${payload.decision} persisted at revision ${payload.revision.sequence_no}.`
            : `${payload.decision} persisted.`;

      setStatusTone(payload.decision === "NOOP" ? "info" : "success");
      setStatusText(decisionMessage);

      if (payload.decision !== "NOOP") {
        setValueText("");
      }

      router.refresh();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Memory write-back failed";
      setStatusTone("danger");
      setStatusText(`Unable to submit memory write-back: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="detail-stack workflow-memory-writeback" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="workflow-memory-key">Memory key</label>
        <input
          id="workflow-memory-key"
          name="workflow-memory-key"
          type="text"
          placeholder="user.preference.supplement.magnesium"
          value={memoryKey}
          onChange={(event) => setMemoryKey(event.target.value)}
          maxLength={200}
        />
      </div>

      <div className="form-field workflow-memory-writeback__value-field">
        <label htmlFor="workflow-memory-value">Memory value (JSON)</label>
        <textarea
          id="workflow-memory-value"
          name="workflow-memory-value"
          placeholder='{"merchant":"Thorne","item":"Magnesium Bisglycinate"}'
          value={valueText}
          onChange={(event) => setValueText(event.target.value)}
          disabled={deleteRequested}
        />
        <p className="field-hint">
          Write-back evidence is fixed to execution-linked event IDs shown below.
        </p>
      </div>

      <label className="workflow-memory-writeback__toggle">
        <input
          type="checkbox"
          checked={deleteRequested}
          onChange={(event) => setDeleteRequested(event.target.checked)}
        />
        Delete requested (submit a DELETE memory revision)
      </label>

      <div className="workflow-memory-writeback__evidence">
        <p className="history-entry__label">Execution evidence</p>
        {evidenceEventIds.length > 0 ? (
          <div className="evidence-list">
            {evidenceEventIds.map((eventId) => (
              <span key={eventId} className="evidence-chip mono">
                {eventId}
              </span>
            ))}
          </div>
        ) : (
          <p className="muted-copy">No execution-linked source events are available yet.</p>
        )}
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
                    : canSubmit
                      ? "ready"
                      : "fixture"
            }
            label={
              isSubmitting
                ? "Submitting"
                : statusTone === "success"
                  ? "Saved"
                  : statusTone === "danger"
                    ? "Attention"
                    : canSubmit
                      ? "Ready"
                      : "Read-only"
            }
          />
          <span>{statusText}</span>
        </div>

        <button type="submit" className="button" disabled={!canSubmit}>
          {isSubmitting ? "Submitting..." : "Submit memory write-back"}
        </button>
      </div>
    </form>
  );
}
