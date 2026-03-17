import Link from "next/link";

import type { ApiSource } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

export type TraceEventItem = {
  id: string;
  kind: string;
  title: string;
  detail: string;
  facts?: string[];
};

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
    compilerVersion?: string;
  };
  metadata: string[];
  evidence: string[];
  events: TraceEventItem[];
  detailSource: ApiSource;
  eventSource: ApiSource;
  detailUnavailable?: boolean;
  eventsUnavailable?: boolean;
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
  apiUnavailable = false,
}: {
  traces: TraceItem[];
  selectedId?: string;
  apiUnavailable?: boolean;
}) {
  if (apiUnavailable) {
    return (
      <div className="split-layout">
        <SectionCard
          eyebrow="Trace list"
          title="Trace API unavailable"
          description="The live explain-why list could not be loaded from the configured backend."
        >
          <EmptyState
            title="Explainability review is unavailable"
            description="The configured trace review endpoints did not return a usable response. Verify the API and retry."
          />
        </SectionCard>

        <SectionCard
          eyebrow="Trace detail"
          title="Detail unavailable"
          description="Detail and ordered events stay hidden until the trace review API becomes reachable again."
        >
          <EmptyState
            title="No live trace detail"
            description="The detail panel remains bounded instead of falling back to stale or invented event data."
          />
        </SectionCard>
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="split-layout">
        <SectionCard
          eyebrow="Trace list"
          title="No trace records"
          description="Explainability entries will appear here when trace sources are available."
        >
          <EmptyState
            title="Trace review is empty"
            description="No trace summaries are available in the current mode."
          />
        </SectionCard>

        <SectionCard
          eyebrow="Trace detail"
          title="No trace selected"
          description="Select a trace once explainability records are available."
        >
          <EmptyState
            title="Explain-why detail is idle"
            description="The detail panel stays empty until a trace summary can be selected."
          />
        </SectionCard>
      </div>
    );
  }

  const selected = traces.find((trace) => trace.id === selectedId) ?? traces[0];

  return (
    <div className="split-layout">
      <SectionCard
        eyebrow="Trace list"
        title="Explainability summaries"
        description="Trace rows surface kind, status, and event count before you open the bounded review panel."
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
                  <span className="meta-pill">{trace.kind.replaceAll(".", " ")}</span>
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
        description={
          selected.detailUnavailable
            ? "The selected live trace detail could not be read, so this panel stays on the bounded summary already returned by the list."
            : "Summary, key metadata, and ordered events stay grouped here without expanding into a raw debugging dump."
        }
      >
        <div className="trace-panel">
          <div className="detail-summary">
            <StatusBadge status={selected.status} />
            <span className="detail-summary__label">
              {selected.kind.replaceAll(".", " ")} · {selected.eventCount} events
            </span>
          </div>

          <div className="trace-summary">
            <p>{selected.summary}</p>
            <div className="attribute-list">
              <span className="attribute-item">Source: {selected.source}</span>
              <span className="attribute-item">Scope: {selected.scope}</span>
              <span className="attribute-item">
                Detail: {selected.detailSource === "live" ? "Live trace detail" : "Fixture trace detail"}
              </span>
              <span className="attribute-item">
                Events: {selected.eventSource === "live" ? "Live event review" : "Fixture event review"}
              </span>
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
              {selected.related.compilerVersion ? (
                <span className="attribute-item">Compiler: {selected.related.compilerVersion}</span>
              ) : null}
            </div>
          </div>

          <div className="detail-group">
            <h3>Key metadata</h3>
            <div className="evidence-list">
              {selected.metadata.map((item) => (
                <span key={item} className="evidence-chip">
                  {item}
                </span>
              ))}
            </div>
          </div>

          {selected.evidence.length > 0 ? (
            <div className="detail-group">
              <h3>Review notes</h3>
              <div className="evidence-list">
                {selected.evidence.map((item) => (
                  <span key={item} className="evidence-chip">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="detail-group">
            <h3>Ordered events</h3>
            {selected.eventsUnavailable ? (
              <EmptyState
                title="Ordered events unavailable"
                description="The trace summary loaded, but the ordered event review could not be read from the current backing source."
              />
            ) : selected.events.length === 0 ? (
              <EmptyState
                title="No ordered events"
                description="This trace currently has no event records to review."
              />
            ) : (
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
                    {event.facts?.length ? (
                      <div className="attribute-list">
                        {event.facts.map((fact) => (
                          <span key={fact} className="attribute-item">
                            {fact}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
