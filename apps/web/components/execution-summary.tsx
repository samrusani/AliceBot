import type { ApiSource, ApprovalExecutionResponse, ToolExecutionItem } from "../lib/api";
import { StatusBadge } from "./status-badge";

type ExecutionSummaryProps = {
  execution: ToolExecutionItem | null;
  preview?: ApprovalExecutionResponse | null;
  source?: ApiSource | null;
  unavailableMessage?: string | null;
  emptyTitle: string;
  emptyDescription: string;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export function ExecutionSummary({
  execution,
  preview,
  source,
  unavailableMessage,
  emptyTitle,
  emptyDescription,
}: ExecutionSummaryProps) {
  if (!execution && !preview) {
    if (unavailableMessage) {
      return (
        <div className="execution-summary execution-summary--unavailable">
          <div className="execution-summary__topline">
            <div className="detail-stack">
              <StatusBadge status="warning" label="Execution unavailable" />
              <h4 className="execution-summary__title">Execution review could not be loaded</h4>
            </div>
          </div>
          <p className="muted-copy">{unavailableMessage}</p>
        </div>
      );
    }

    return (
      <div className="execution-summary execution-summary--empty">
        <div className="execution-summary__topline">
          <div className="detail-stack">
            <StatusBadge status="pending" label="Not executed" />
            <h4 className="execution-summary__title">{emptyTitle}</h4>
          </div>
        </div>
        <p className="muted-copy">{emptyDescription}</p>
      </div>
    );
  }

  const result = execution?.result ?? preview?.result ?? null;
  const tool = execution?.tool ?? preview?.tool ?? null;
  const traceId = execution?.trace_id ?? preview?.trace.trace_id ?? null;
  const requestEventId = execution?.request_event_id ?? preview?.events?.request_event_id ?? null;
  const resultEventId = execution?.result_event_id ?? preview?.events?.result_event_id ?? null;
  const taskRunId = execution?.task_run_id ?? preview?.request.task_run_id ?? null;
  const idempotencyKey = execution?.idempotency_key ?? null;
  const executedAt = execution?.executed_at ?? null;
  const reviewSource = execution ? (source === "live" ? "Live execution detail" : "Fixture execution detail") : "Latest execute response";

  return (
    <div className="execution-summary">
      <div className="execution-summary__topline">
        <div className="detail-stack">
          <StatusBadge status={execution?.status ?? result?.status ?? "info"} />
          <h4 className="execution-summary__title">
            {execution ? "Execution record in review" : "Latest execution result"}
          </h4>
        </div>
        <span className="meta-pill">{reviewSource}</span>
      </div>

      <div className="key-value-grid key-value-grid--compact">
        {execution ? (
          <div>
            <dt>Execution</dt>
            <dd className="mono">{execution.id}</dd>
          </div>
        ) : null}
        <div>
          <dt>Handler</dt>
          <dd>{result?.handler_key ?? "Unavailable"}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{result?.status ?? execution?.status ?? "Unknown"}</dd>
        </div>
        <div>
          <dt>Executed</dt>
          <dd>{executedAt ? formatDate(executedAt) : "Just returned from execute"}</dd>
        </div>
        {requestEventId ? (
          <div>
            <dt>Request event</dt>
            <dd className="mono">{requestEventId}</dd>
          </div>
        ) : null}
        {resultEventId ? (
          <div>
            <dt>Result event</dt>
            <dd className="mono">{resultEventId}</dd>
          </div>
        ) : null}
        {traceId ? (
          <div>
            <dt>Trace</dt>
            <dd className="mono">{traceId}</dd>
          </div>
        ) : null}
        {taskRunId ? (
          <div>
            <dt>Task run</dt>
            <dd className="mono">{taskRunId}</dd>
          </div>
        ) : null}
        {idempotencyKey ? (
          <div>
            <dt>Idempotency</dt>
            <dd className="mono">{idempotencyKey}</dd>
          </div>
        ) : null}
        {tool ? (
          <div>
            <dt>Tool</dt>
            <dd>{tool.name}</dd>
          </div>
        ) : null}
      </div>

      {result?.reason ? (
        <div className="execution-summary__note execution-summary__note--danger">
          <p className="execution-summary__label">Execution reason</p>
          <p>{result.reason}</p>
        </div>
      ) : null}

      {result?.budget_decision ? (
        <div className="execution-summary__note">
          <p className="execution-summary__label">Budget decision</p>
          <pre className="execution-summary__code">{formatJson(result.budget_decision)}</pre>
        </div>
      ) : null}

      {result?.output ? (
        <div className="execution-summary__note">
          <p className="execution-summary__label">Output snapshot</p>
          <pre className="execution-summary__code">{formatJson(result.output)}</pre>
        </div>
      ) : null}
    </div>
  );
}
