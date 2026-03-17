"use client";

import Link from "next/link";

import type { ResponseHistoryEntry } from "../lib/api";
import { EmptyState } from "./empty-state";
import { StatusBadge } from "./status-badge";

type ResponseHistoryProps = {
  entries: ResponseHistoryEntry[];
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ResponseHistory({ entries }: ResponseHistoryProps) {
  return (
    <section className="section-card section-card--history">
      <div className="list-panel__header">
        <div>
          <p className="eyebrow">Assistant replies</p>
          <h2>Bounded response history</h2>
          <p>Each entry keeps the operator prompt, assistant reply, and both linked traces visible.</p>
        </div>
      </div>

      {entries.length === 0 ? (
        <EmptyState
          title="No assistant replies yet"
          description="Submitted questions will appear here with the returned assistant text and linked trace summaries."
        />
      ) : (
        <div className="history-list history-list--scrollable">
          {entries.map((entry) => (
            <article key={entry.id} className="history-entry history-entry--response">
              <div className="history-entry__topline">
                <div className="history-entry__state-row">
                  <StatusBadge
                    status={entry.source === "live" ? "live" : "fixture"}
                    label={entry.source === "live" ? "Live API" : "Fixture preview"}
                  />
                  <span className="meta-pill">Model {entry.model}</span>
                </div>
                <span className="subtle-chip">{formatDate(entry.submittedAt)}</span>
              </div>

              <div className="conversation-stack">
                <div className="conversation-block">
                  <span className="history-entry__label">Operator prompt</span>
                  <p className="response-copy">{entry.message}</p>
                </div>
                <div className="conversation-block conversation-block--accent">
                  <span className="history-entry__label">Assistant reply</span>
                  <p className="response-copy">{entry.assistantText}</p>
                </div>
              </div>

              <p>{entry.summary}</p>

              <div className="attribute-list">
                <span className="attribute-item">Thread: {entry.threadId}</span>
                <span className="attribute-item">Provider: {entry.modelProvider}</span>
                <span className="attribute-item">Sequence: {entry.assistantSequenceNo}</span>
              </div>

              <div className="history-entry__trace">
                <span className="meta-pill">
                  Compile {entry.trace.compileTraceId} · {entry.trace.compileTraceEventCount} events
                </span>
                <span className="meta-pill">
                  Response {entry.trace.responseTraceId} · {entry.trace.responseTraceEventCount} events
                </span>
              </div>

              <div className="cluster">
                <Link href={`/traces?trace=${entry.trace.compileTraceId}`} className="button-secondary">
                  Open compile trace
                </Link>
                <Link href={`/traces?trace=${entry.trace.responseTraceId}`} className="button-secondary">
                  Open response trace
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
