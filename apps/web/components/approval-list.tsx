import Link from "next/link";

import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

export type ApprovalItem = {
  id: string;
  thread_id: string;
  task_step_id: string | null;
  status: string;
  request: {
    thread_id: string;
    tool_id: string;
    action: string;
    scope: string;
    domain_hint: string | null;
    risk_hint: string | null;
    attributes: Record<string, unknown>;
  };
  tool: {
    id: string;
    tool_key: string;
    name: string;
    description: string;
    version: string;
    metadata_version: string;
    active: boolean;
    tags: string[];
    action_hints: string[];
    scope_hints: string[];
    domain_hints: string[];
    risk_hints: string[];
    metadata: Record<string, unknown>;
    created_at: string;
  };
  routing: {
    decision: string;
    reasons: Array<{
      code: string;
      source: string;
      message: string;
      tool_id: string | null;
      policy_id: string | null;
      consent_key: string | null;
    }>;
    trace: {
      trace_id: string;
      trace_event_count: number;
    };
  };
  created_at: string;
  resolution: {
    resolved_at: string;
    resolved_by_user_id: string;
  } | null;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatAttributeValue(value: unknown) {
  if (value == null) {
    return "None";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

export function ApprovalList({
  items,
  selectedId,
}: {
  items: ApprovalItem[];
  selectedId?: string;
}) {
  if (items.length === 0) {
    return (
      <SectionCard
        eyebrow="Approval inbox"
        title="No approvals in view"
        description="When approvals are created, they will appear here with the governing rationale attached."
      >
        <EmptyState
          title="Approval inbox is empty"
          description="There are no approval records to review in the current mode."
          actionHref="/chat"
          actionLabel="Open requests"
        />
      </SectionCard>
    );
  }

  const selected = items.find((item) => item.id === selectedId) ?? items[0];

  return (
    <div className="split-layout">
      <SectionCard
        eyebrow="Approval inbox"
        title="Requests awaiting review"
        description="The inbox favors scanability first: tool, action, scope, and state are visible without opening every row."
      >
        <div className="list-panel">
          <div className="list-panel__header">
            <p>{items.length} total approvals</p>
          </div>
          <div className="list-rows">
            {items.map((item) => (
              <Link
                key={item.id}
                href={`/approvals?approval=${item.id}`}
                className={`list-row${selected.id === item.id ? " is-selected" : ""}`}
              >
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{formatDate(item.created_at)}</span>
                    <h3 className="list-row__title">{item.tool.name}</h3>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
                <p>
                  {item.request.action} / {item.request.scope}
                </p>
                <div className="list-row__meta">
                  <span className="meta-pill">Thread {item.thread_id}</span>
                  {item.request.risk_hint ? <span className="meta-pill">Risk {item.request.risk_hint}</span> : null}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </SectionCard>

      <SectionCard
        eyebrow="Approval detail"
        title={selected.tool.name}
        description="Request detail, routing rationale, and trace reference stay in one bounded inspector."
      >
        <div className="detail-grid">
          <div className="detail-summary">
            <StatusBadge status={selected.status} />
            <span className="detail-summary__label">
              {selected.request.action} / {selected.request.scope}
            </span>
          </div>

          <dl className="key-value-grid">
            <div>
              <dt>Thread</dt>
              <dd className="mono">{selected.thread_id}</dd>
            </div>
            <div>
              <dt>Task step</dt>
              <dd className="mono">{selected.task_step_id ?? "Unlinked"}</dd>
            </div>
            <div>
              <dt>Routing decision</dt>
              <dd>{selected.routing.decision}</dd>
            </div>
            <div>
              <dt>Trace</dt>
              <dd className="mono">
                {selected.routing.trace.trace_id} · {selected.routing.trace.trace_event_count} events
              </dd>
            </div>
          </dl>

          <div className="detail-group">
            <h3>Request attributes</h3>
            <div className="attribute-list">
              {Object.entries(selected.request.attributes).map(([key, value]) => (
                <span key={key} className="attribute-item">
                  {key}: {formatAttributeValue(value)}
                </span>
              ))}
            </div>
          </div>

          <div className="detail-group">
            <h3>Routing rationale</h3>
            <ul className="reason-list">
              {selected.routing.reasons.map((reason) => (
                <li key={`${reason.code}-${reason.message}`}>
                  {reason.message}
                </li>
              ))}
            </ul>
          </div>

          <div className="detail-group">
            <h3>Resolution</h3>
            <p className="muted-copy">
              {selected.resolution
                ? `Resolved ${formatDate(selected.resolution.resolved_at)} by ${selected.resolution.resolved_by_user_id}.`
                : "Still awaiting explicit operator resolution."}
            </p>
          </div>
        </div>
      </SectionCard>
    </div>
  );
}
