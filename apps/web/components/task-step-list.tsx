import Link from "next/link";

import type { TaskStepItem, TaskStepListSummary } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

function formatAttributeValue(value: unknown) {
  if (value == null) {
    return "None";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TaskStepList({
  steps,
  summary,
  source,
  chrome = "card",
  traceHrefPrefix,
}: {
  steps: TaskStepItem[];
  summary: TaskStepListSummary | null;
  source: "live" | "fixture";
  chrome?: "card" | "embedded";
  traceHrefPrefix?: string;
}) {
  return (
    <SectionCard
      eyebrow="Task steps"
      title="Ordered lifecycle steps"
      description="The timeline preserves request intent, downstream approval or execution state, and trace linkage in one readable sequence."
      className={[
        chrome === "embedded" ? "section-card--embedded" : null,
        "task-step-list",
        chrome === "embedded" ? "task-step-list--embedded" : null,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {summary ? (
        <div className="cluster">
          <span className="meta-pill">{summary.total_count} steps</span>
          <span className="meta-pill">
            Latest {summary.latest_sequence_no ?? "none"} / {summary.latest_status ?? "empty"}
          </span>
          <span className="meta-pill">{source === "live" ? "Live sequencing" : "Fixture sequencing"}</span>
        </div>
      ) : null}
      {steps.length === 0 ? (
        <EmptyState
          title="No task steps available"
          description="Select a task with step records to inspect ordered lifecycle detail."
        />
      ) : (
        <div className="timeline-list">
          {steps.map((step) => (
            <article key={step.id} className="timeline-item">
              <div className="timeline-item__topline">
                <div className="detail-stack">
                  <span className="list-row__eyebrow">Step {step.sequence_no}</span>
                  <h3 className="list-row__title">
                    {step.request.action} / {step.request.scope}
                  </h3>
                </div>
                <StatusBadge status={step.status} />
              </div>

              <div className="timeline-item__meta">
                <span className="meta-pill">{step.kind.replace(/_/g, " ")}</span>
                <span className="meta-pill">{formatDate(step.updated_at)}</span>
              </div>

              <div className="timeline-item__summary">
                <div className="attribute-list">
                  {Object.entries(step.request.attributes).map(([key, value]) => (
                    <span key={key} className="attribute-item">
                      {key}: {formatAttributeValue(value)}
                    </span>
                  ))}
                </div>
                <div className="key-value-grid">
                  <div>
                    <dt>Routing</dt>
                    <dd>{step.outcome.routing_decision}</dd>
                  </div>
                  <div>
                    <dt>Approval status</dt>
                    <dd>
                      {step.outcome.approval_id ? (
                        <Link href={`/approvals?approval=${step.outcome.approval_id}`} className="inline-link">
                          {step.outcome.approval_status ?? "Linked approval"}
                        </Link>
                      ) : (
                        "No approval"
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Execution status</dt>
                    <dd>{step.outcome.execution_status ?? "Not executed"}</dd>
                  </div>
                  <div>
                    <dt>Trace</dt>
                    <dd className="mono">
                      {traceHrefPrefix ? (
                        <Link
                          href={`${traceHrefPrefix}${encodeURIComponent(step.trace.trace_id)}`}
                          className="inline-link"
                        >
                          {step.trace.trace_id}
                        </Link>
                      ) : (
                        step.trace.trace_id
                      )}{" "}
                      · {step.trace.trace_kind}
                    </dd>
                  </div>
                </div>
                {step.lineage.parent_step_id || step.lineage.source_approval_id || step.lineage.source_execution_id ? (
                  <div className="attribute-list">
                    {step.lineage.parent_step_id ? (
                      <span key="parent-step" className="attribute-item">
                        Parent step: {step.lineage.parent_step_id}
                      </span>
                    ) : null}
                    {step.lineage.source_approval_id ? (
                      <span key="source-approval" className="attribute-item">
                        Source approval: {step.lineage.source_approval_id}
                      </span>
                    ) : null}
                    {step.lineage.source_execution_id ? (
                      <span key="source-execution" className="attribute-item">
                        Source execution: {step.lineage.source_execution_id}
                      </span>
                    ) : null}
                  </div>
                ) : null}
                {step.outcome.execution_id ? (
                  <div className="attribute-list">
                    <span className="attribute-item">Execution record: {step.outcome.execution_id}</span>
                  </div>
                ) : null}
                {step.outcome.blocked_reason ? (
                  <div className="execution-summary__note execution-summary__note--danger">
                    <p className="execution-summary__label">Blocked reason</p>
                    <p>{step.outcome.blocked_reason}</p>
                  </div>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
