"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import type { AssistantResponsePayload, ResponseHistoryEntry } from "../lib/api";
import { submitAssistantResponse } from "../lib/api";
import { buildFixtureResponseEntry } from "../lib/fixtures";
import { ResponseHistory } from "./response-history";
import { StatusBadge } from "./status-badge";

type ResponseComposerProps = {
  initialEntries: ResponseHistoryEntry[];
  apiBaseUrl?: string;
  userId?: string;
  defaultThreadId?: string;
};

export function ResponseComposer({
  initialEntries,
  apiBaseUrl,
  userId,
  defaultThreadId,
}: ResponseComposerProps) {
  const [threadId, setThreadId] = useState(defaultThreadId ?? "");
  const [message, setMessage] = useState("");
  const [entries, setEntries] = useState(initialEntries);
  const [statusText, setStatusText] = useState("Ready to ask the assistant inside the current thread.");
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const liveModeReady = Boolean(apiBaseUrl && userId);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextThreadId = threadId.trim();
    const nextMessage = message.trim();

    if (!nextThreadId || !nextMessage) {
      setStatusTone("danger");
      setStatusText("Thread ID and a message are both required.");
      return;
    }

    const payload: AssistantResponsePayload = {
      user_id: userId ?? "fixture-user",
      thread_id: nextThreadId,
      message: nextMessage,
    };

    setStatusTone("info");
    setStatusText(
      liveModeReady
        ? "Submitting the operator message through the assistant response endpoint..."
        : "Preparing a fixture-backed assistant response preview...",
    );
    setIsSubmitting(true);

    if (!liveModeReady) {
      const entry = buildFixtureResponseEntry({
        threadId: nextThreadId,
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
      const response = await submitAssistantResponse(apiBaseUrl!, payload);
      const entry: ResponseHistoryEntry = {
        id: response.trace.response_trace_id,
        submittedAt: new Date().toISOString(),
        source: "live",
        threadId: nextThreadId,
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
      setMessage("");
      setStatusTone("success");
      setStatusText("Assistant reply added successfully. Linked trace summaries are visible alongside the response.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed";
      setStatusTone("danger");
      setStatusText(`Unable to submit assistant message: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="chat-workspace">
      <section className="composer-card composer-card--chat-primary">
        <div className="composer-card__header composer-card__header--tight">
          <div className="governance-banner governance-banner--assistant">
            <strong>{liveModeReady ? "Live assistant mode" : "Fixture assistant mode"}</strong>
            <span>
              Normal questions go through `POST /v0/responses` while thread identity and trace linkage stay explicit.
            </span>
          </div>

          <div className="form-field">
            <label htmlFor="assistant-thread-id">Thread ID</label>
            <p className="field-hint">
              Keep the thread explicit so assistant replies stay attached to the intended conversation context.
            </p>
            <input
              id="assistant-thread-id"
              name="assistant-thread-id"
              value={threadId}
              onChange={(event) => setThreadId(event.target.value)}
              placeholder="Thread UUID"
            />
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
              onChange={(event) => setMessage(event.target.value)}
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
              disabled={isSubmitting || !threadId.trim() || !message.trim()}
            >
              {isSubmitting ? "Asking..." : "Ask assistant"}
            </button>
          </div>
        </form>
      </section>

      <ResponseHistory entries={entries} />
    </div>
  );
}
