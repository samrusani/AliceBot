"use client";

import type { FormEvent } from "react";
import { useRef, useState } from "react";

import { ApiError, isAssistantResponseAccepted } from "../lib/api";
import type {
  AssistantResponsePayload,
  ResponseHistoryEntry,
  ThreadEventItem,
} from "../lib/api";
import { submitAssistantResponse } from "../lib/api";
import { buildFixtureResponseEntry } from "../lib/fixtures";
import { ResponseHistory } from "./response-history";
import { StatusBadge } from "./status-badge";

type ContinuitySource = "live" | "fixture" | "unavailable";

const RESPONSE_JOB_POLL_DELAY_MS = 2_000;
const MAX_RESPONSE_JOB_POLLS = 60;

type PendingAssistantSubmission = {
  fingerprint: string;
  idempotencyKey: string;
};

type ResponseComposerProps = {
  initialEntries: ResponseHistoryEntry[];
  apiBaseUrl?: string;
  userId?: string;
  selectedThreadId?: string;
  selectedThreadTitle?: string;
  events?: ThreadEventItem[];
  source?: ContinuitySource;
  unavailableReason?: string;
};

export function ResponseComposer({
  initialEntries,
  apiBaseUrl,
  userId,
  selectedThreadId,
  selectedThreadTitle,
  events = [],
  source = "fixture",
  unavailableReason,
}: ResponseComposerProps) {
  const [message, setMessage] = useState("");
  const [entries, setEntries] = useState(initialEntries);
  const [statusText, setStatusText] = useState(
    source === "unavailable"
      ? "Assistant submission is unavailable until live continuity can be loaded."
      : selectedThreadId
      ? "Ready to ask the assistant inside the selected thread."
      : "Select a thread before sending an assistant message.",
  );
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const pendingSubmission = useRef<PendingAssistantSubmission | null>(null);

  const liveModeReady = Boolean(apiBaseUrl && userId && source === "live");
  const interactionAvailable = source !== "unavailable";
  const activeThreadId = selectedThreadId?.trim() ?? "";
  const visibleEntries = activeThreadId
    ? entries.filter((entry) => entry.threadId === activeThreadId)
    : [];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextMessage = message.trim();

    if (!interactionAvailable) {
      setStatusTone("danger");
      setStatusText("Assistant submission is unavailable until live continuity can be loaded.");
      return;
    }

    if (!activeThreadId || !nextMessage) {
      setStatusTone("danger");
      setStatusText("Select a thread and enter a message before submitting.");
      return;
    }

    const payload: AssistantResponsePayload = {
      user_id: userId ?? "fixture-user",
      thread_id: activeThreadId,
      message: nextMessage,
    };
    const fingerprint = JSON.stringify(payload);
    const submission =
      pendingSubmission.current?.fingerprint === fingerprint
        ? pendingSubmission.current
        : { fingerprint, idempotencyKey: crypto.randomUUID() };
    pendingSubmission.current = submission;

    setStatusTone("info");
    setStatusText(
      liveModeReady
        ? "Submitting the operator message through the assistant response endpoint..."
        : "Preparing a fixture-backed assistant response preview...",
    );
    setIsSubmitting(true);

    if (!liveModeReady) {
      const entry = buildFixtureResponseEntry({
        threadId: activeThreadId,
        message: nextMessage,
      });
      setEntries((current) => [entry, ...current]);
      setMessage("");
      setStatusTone("success");
      setStatusText(
        "Fixture response preview added. Configure the web API base URL and user ID to persist assistant replies and traces.",
      );
      setIsSubmitting(false);
      return;
    }

    try {
      let response = await submitAssistantResponse(
        apiBaseUrl!,
        payload,
        submission.idempotencyKey,
      );
      let pollCount = 0;
      while (isAssistantResponseAccepted(response)) {
        setStatusText("Assistant response is still running. Checking the same response job...");
        pollCount += 1;
        if (pollCount >= MAX_RESPONSE_JOB_POLLS) {
          throw new ApiError(
            "Assistant response is still running; retry to check the same response job.",
            0,
            "response_generation_in_progress",
          );
        }
        await new Promise((resolve) => setTimeout(resolve, RESPONSE_JOB_POLL_DELAY_MS));
        response = await submitAssistantResponse(
          apiBaseUrl!,
          payload,
          submission.idempotencyKey,
        );
      }
      const entry: ResponseHistoryEntry = {
        id: response.trace.response_trace_id,
        submittedAt: new Date().toISOString(),
        source: "live",
        threadId: activeThreadId,
        message: nextMessage,
        assistantText: response.assistant.text,
        assistantEventId: response.assistant.event_id,
        assistantSequenceNo: response.assistant.sequence_no,
        modelProvider: response.assistant.model_provider,
        model: response.assistant.model,
        summary:
          "The reply was returned through the shipped response seam and linked to both compile and response traces.",
        trace: {
          compileTraceId: response.trace.compile_trace_id,
          compileTraceEventCount: response.trace.compile_trace_event_count,
          responseTraceId: response.trace.response_trace_id,
          responseTraceEventCount: response.trace.response_trace_event_count,
        },
      };

      setEntries((current) => [entry, ...current]);
      setMessage((current) => (current.trim() === nextMessage ? "" : current));
      if (pendingSubmission.current?.idempotencyKey === submission.idempotencyKey) {
        pendingSubmission.current = null;
      }
      setStatusTone("success");
      setStatusText("Assistant reply added successfully. Linked trace summaries are visible alongside the response.");
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status > 0 &&
        pendingSubmission.current?.idempotencyKey === submission.idempotencyKey
      ) {
        pendingSubmission.current = null;
      }
      const detail = error instanceof Error ? error.message : "Request failed";
      setStatusTone("danger");
      setStatusText(`Unable to submit assistant message: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="chat-workspace">
      <ResponseHistory
        entries={visibleEntries}
        threadTitle={selectedThreadTitle}
        events={events}
        source={source}
        unavailableReason={unavailableReason}
      />

      <section className="composer-card composer-card--chat-primary composer-card--assistant">
        <div className="composer-card__header composer-card__header--tight">
          <div className="selected-thread-panel">
            <div className="selected-thread-panel__copy">
              <span className="history-entry__label">Selected thread</span>
              <h2 className="composer-title">{selectedThreadTitle ?? "Choose a visible thread"}</h2>
              <p className="field-hint">
                {activeThreadId
                  ? "New assistant replies will stay attached to the selected continuity record."
                  : "Select or create a thread from the right rail before starting assistant conversation."}
              </p>
            </div>
            {activeThreadId ? <span className="meta-pill mono">{activeThreadId}</span> : null}
          </div>

          <div className="governance-banner governance-banner--assistant">
            <strong>{liveModeReady ? "Live assistant mode" : "Fixture assistant mode"}</strong>
            <span>
              Conversation stays anchored to immutable thread continuity while new assistant responses
              still go through `POST /v0/responses`.
            </span>
          </div>

          <div className="composer-intro">
            <p className="eyebrow">Continue thread</p>
            <h2 className="composer-title">Add the next operator message</h2>
            <p className="field-hint">
              Keep the composer compact and use the transcript above as the durable reading surface
              for the selected thread.
            </p>
          </div>
        </div>

        <form className="detail-stack" onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="assistant-message">Ask the assistant</label>
            <textarea
              id="assistant-message"
              name="assistant-message"
              placeholder="Summarize the current thread state, explain the last approval, or answer a normal operator question."
              value={message}
              onChange={(event) => {
                setMessage(event.target.value);
                pendingSubmission.current = null;
              }}
            />
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
                        : "info"
                }
                label={
                  isSubmitting
                    ? "Submitting"
                    : statusTone === "success"
                      ? "Ready"
                      : statusTone === "danger"
                        ? "Attention"
                        : "Prepared"
                }
              />
              <span>{statusText}</span>
            </div>
            <button
              type="submit"
              className="button"
              disabled={!interactionAvailable || isSubmitting || !activeThreadId || !message.trim()}
            >
              {isSubmitting ? "Asking..." : "Ask assistant"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
