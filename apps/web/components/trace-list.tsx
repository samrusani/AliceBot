import Link from "next/link";

import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

export type TraceItem = {
  id: string;
  kind: string;
  status: string;
  title: string;
  summary: string;
  eventCount: number;
  createdAt: string;
  source: string;
  scope: string;
  related: {
    threadId?: string;
    taskId?: string;
    approvalId?: string;
    executionId?: string;
  };
  evidence: string[];
  events: Array<{
    id: string;
    kind: string;
    title: string;
    detail: string;
  }>;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TraceList({
  traces,
  selectedId,
}: {
  traces: TraceItem[];
  selectedId?: string;
}) {
  if (traces.length === 0) {
    return (
      <SectionCard
        eyebrow="Traces"
        title="No trace records"
        description="Explainability entries will appear here when trace sources are available."
      >
        <EmptyState
          title="Trace review is empty"
          description="No trace summaries are available in the current mode."
        />
      </SectionCard>
    );
  }

  const selected = traces.find((trace) => trace.id === selectedId) ?? traces[0];

  return (
    <div className="split-layout">
      <SectionCard
        eyebrow="Trace list"
        title="Explainability summaries"
        description="Trace rows surface kind, scope, event count, and state before you open a detail panel."
      >
        <div className="list-panel">
          <div className="list-panel__header">
            <p>{traces.length} explainability entries</p>
          </div>
          <div className="list-rows">
            {traces.map((trace) => (
              <Link
                key={trace.id}
                href={`/traces?trace=${trace.id}`}
                className={`list-row${trace.id === selected.id ? " is-selected" : ""}`}
              >
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{formatDate(trace.createdAt)}</span>
                    <h3 className="list-row__title">{trace.title}</h3>
                  </div>
                  <StatusBadge status={trace.status} />
                </div>
                <p>{trace.summary}</p>
                <div className="list-row__meta">
                  <span className="meta-pill">{trace.kind.replace(/_/g, " ")}</span>
                  <span className="meta-pill">{trace.eventCount} events</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </SectionCard>

      <SectionCard
        eyebrow="Trace detail"
        title={selected.title}
        description="Detail view keeps trace evidence, related records, and key events grouped without turning into a debugger dump."
      >
        <div className="trace-panel">
          <div className="detail-summary">
            <StatusBadge status={selected.status} />
            <span className="detail-summary__label">
              {selected.kind.replace(/_/g, " ")} · {selected.eventCount} events
            </span>
          </div>

          <div className="trace-summary">
            <p>{selected.summary}</p>
            <div className="attribute-list">
              <span className="attribute-item">Source: {selected.source}</span>
              <span className="attribute-item">Scope: {selected.scope}</span>
              {selected.related.threadId ? (
                <span className="attribute-item">Thread: {selected.related.threadId}</span>
              ) : null}
              {selected.related.taskId ? (
                <span className="attribute-item">Task: {selected.related.taskId}</span>
              ) : null}
              {selected.related.approvalId ? (
                <span className="attribute-item">Approval: {selected.related.approvalId}</span>
              ) : null}
              {selected.related.executionId ? (
                <span className="attribute-item">Execution: {selected.related.executionId}</span>
              ) : null}
            </div>
          </div>

          <div className="detail-group">
            <h3>Evidence in view</h3>
            <div className="evidence-list">
              {selected.evidence.map((item) => (
                <span key={item} className="evidence-chip">
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="detail-group">
            <h3>Key events</h3>
            <ol className="trace-events">
              {selected.events.map((event) => (
                <li key={event.id} className="trace-event">
                  <div className="trace-event__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow">{event.kind}</span>
                      <h4>{event.title}</h4>
                    </div>
                  </div>
                  <p>{event.detail}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
