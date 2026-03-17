import Link from "next/link";

import type { ApprovalItem } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
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

  return (
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
              className={`list-row${item.id === selectedId ? " is-selected" : ""}`}
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
                {item.task_step_id ? <span className="meta-pill">Step linked</span> : null}
                {item.request.risk_hint ? <span className="meta-pill">Risk {item.request.risk_hint}</span> : null}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
