import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

export type TaskStepItem = {
  id: string;
  task_id: string;
  sequence_no: number;
  kind: string;
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
  outcome: {
    routing_decision: string;
    approval_id: string | null;
    approval_status: string | null;
    execution_id: string | null;
    execution_status: string | null;
    blocked_reason: string | null;
  };
  lineage: {
    parent_step_id: string | null;
    source_approval_id: string | null;
    source_execution_id: string | null;
  };
  trace: {
    trace_id: string;
    trace_kind: string;
  };
  created_at: string;
  updated_at: string;
};

function formatAttributeValue(value: unknown) {
  if (value == null) {
    return "None";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

export function TaskStepList({ steps }: { steps: TaskStepItem[] }) {
  return (
    <SectionCard
      eyebrow="Task steps"
      title="Ordered lifecycle steps"
      description="The timeline preserves request intent, downstream approval or execution state, and trace linkage in one readable sequence."
    >
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
                    <dd>{step.outcome.approval_status ?? "No approval"}</dd>
                  </div>
                  <div>
                    <dt>Execution status</dt>
                    <dd>{step.outcome.execution_status ?? "Not executed"}</dd>
                  </div>
                  <div>
                    <dt>Trace</dt>
                    <dd className="mono">
                      {step.trace.trace_id} · {step.trace.trace_kind}
                    </dd>
                  </div>
                </div>
                {step.outcome.blocked_reason ? (
                  <p>Blocked reason: {step.outcome.blocked_reason}</p>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
