"use client";

import type { FormEvent } from "react";
import { useState, useTransition } from "react";

export type RequestHistoryEntry = {
  id: string;
  request: string;
  response: string;
  submittedAt: string;
  source: "live" | "fixture";
  trace?: {
    compileTraceId: string;
    compileTraceEventCount: number;
    responseTraceId: string;
    responseTraceEventCount: number;
  };
};

type RequestComposerProps = {
  initialEntries: RequestHistoryEntry[];
  apiBaseUrl?: string;
  userId?: string;
  threadId?: string;
};

type LiveResponsePayload = {
  assistant: {
    event_id: string;
    text: string;
  };
  trace: {
    compile_trace_id: string;
    compile_trace_event_count: number;
    response_trace_id: string;
    response_trace_event_count: number;
  };
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function buildFixtureEntry(message: string): RequestHistoryEntry {
  const excerpt = message.trim().slice(0, 120);
  const requestLabel = excerpt.length > 0 ? excerpt : "Operator request";
  const nonce = Date.now().toString(36);

  return {
    id: `fixture-${nonce}`,
    request: requestLabel,
    response:
      `Prepared a governed response preview for "${requestLabel}". In live mode this surface returns assistant output together with compile and response trace references from the backend.`,
    submittedAt: new Date().toISOString(),
    source: "fixture",
    trace: {
      compileTraceId: `trace-ctx-${nonce}`,
      compileTraceEventCount: 5,
      responseTraceId: `trace-resp-${nonce}`,
      responseTraceEventCount: 3,
    },
  };
}

export function RequestComposer({
  initialEntries,
  apiBaseUrl,
  userId,
  threadId,
}: RequestComposerProps) {
  const [message, setMessage] = useState("");
  const [entries, setEntries] = useState(initialEntries);
  const [statusText, setStatusText] = useState("Ready for a governed operator request.");
  const [isPending, startTransition] = useTransition();

  const liveModeReady = Boolean(apiBaseUrl && userId && threadId);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextMessage = message.trim();
    if (!nextMessage) {
      return;
    }

    setStatusText(liveModeReady ? "Submitting request to the response endpoint..." : "Saving fixture-backed preview...");

    if (!liveModeReady) {
      const entry = buildFixtureEntry(nextMessage);
      startTransition(() => {
        setEntries((current) => [entry, ...current]);
        setMessage("");
        setStatusText("Fixture response added. Configure the web API env vars to switch this view into live mode.");
      });
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl?.replace(/\/$/, "")}/v0/responses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          thread_id: threadId,
          message: nextMessage,
          max_sessions: 8,
          max_events: 80,
          max_memories: 20,
          max_entities: 12,
          max_entity_edges: 20,
        }),
      });

      const payload = (await response.json()) as LiveResponsePayload | { detail?: string };
      if (!response.ok || !("assistant" in payload)) {
        throw new Error("detail" in payload && payload.detail ? payload.detail : "Request failed");
      }

      const entry: RequestHistoryEntry = {
        id: payload.assistant.event_id,
        request: nextMessage,
        response: payload.assistant.text,
        submittedAt: new Date().toISOString(),
        source: "live",
        trace: {
          compileTraceId: payload.trace.compile_trace_id,
          compileTraceEventCount: payload.trace.compile_trace_event_count,
          responseTraceId: payload.trace.response_trace_id,
          responseTraceEventCount: payload.trace.response_trace_event_count,
        },
      };

      startTransition(() => {
        setEntries((current) => [entry, ...current]);
        setMessage("");
        setStatusText("Live response received and trace references recorded.");
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed";
      setStatusText(`Unable to submit live request: ${detail}`);
    }
  }

  return (
    <section className="composer-card">
      <div className="composer-card__header">
        <div className="governance-banner">
          <strong>{liveModeReady ? "Live operator mode" : "Fixture operator mode"}</strong>
          <span>
            Requests stay explicitly governed and recent trace references remain attached to each response.
          </span>
        </div>

        <div className="form-field">
          <label htmlFor="operator-request">Operator request</label>
          <p className="field-hint">
            Keep requests bounded to existing backend concepts. This surface is optimized for clarity
            and review rather than casual back-and-forth.
          </p>
        </div>
      </div>

      <form className="detail-stack" onSubmit={handleSubmit}>
        <div className="form-field">
          <textarea
            id="operator-request"
            name="operator-request"
            placeholder="Example: Summarize the open approval-linked tasks and tell me what still requires explicit approval."
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
        </div>

        <div className="composer-actions">
          <div className="composer-status" aria-live="polite">
            {statusText}
          </div>
          <button type="submit" className="button" disabled={isPending || message.trim().length === 0}>
            {isPending ? "Working..." : "Submit governed request"}
          </button>
        </div>
      </form>

      <div className="detail-stack">
        <div className="list-panel__header">
          <div>
            <h2>Recent requests and responses</h2>
            <p>Latest entries stay grouped with timing and trace references.</p>
          </div>
        </div>

        <div className="history-list">
          {entries.map((entry) => (
            <article key={entry.id} className="history-entry">
              <div className="history-entry__topline">
                <span className="history-entry__label">{entry.source === "live" ? "Live response" : "Fixture preview"}</span>
                <span className="subtle-chip">{formatDate(entry.submittedAt)}</span>
              </div>
              <div className="detail-stack">
                <p>
                  <strong>Request:</strong> {entry.request}
                </p>
                <p>
                  <strong>Response:</strong> {entry.response}
                </p>
              </div>
              {entry.trace ? (
                <div className="history-entry__trace">
                  <span className="meta-pill">
                    Compile {entry.trace.compileTraceId} · {entry.trace.compileTraceEventCount} events
                  </span>
                  <span className="meta-pill">
                    Response {entry.trace.responseTraceId} · {entry.trace.responseTraceEventCount} events
                  </span>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
