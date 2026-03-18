import Link from "next/link";

import type { ApiSource, TaskItem, ToolExecutionItem } from "../lib/api";
import { EmptyState } from "./empty-state";
import { ExecutionSummary } from "./execution-summary";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type TaskSummaryProps = {
  task: TaskItem | null;
  taskSource: ApiSource;
  stepSource: ApiSource;
  execution: ToolExecutionItem | null;
  executionSource?: ApiSource | null;
  executionUnavailableMessage?: string | null;
  chrome?: "card" | "embedded";
  showExecutionReview?: boolean;
};

export function TaskSummary({
  task,
  taskSource,
  stepSource,
  execution,
  executionSource,
  executionUnavailableMessage,
  chrome = "card",
  showExecutionReview = true,
}: TaskSummaryProps) {
  if (!task) {
    return (
      <SectionCard
        eyebrow="Selected task"
        title="No task selected"
        description="Choose a task to inspect its current governed state and ordered task steps."
        className={chrome === "embedded" ? "section-card--embedded" : undefined}
      >
        <EmptyState
          title="Task inspector is idle"
          description="No task records are available in the current route state."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Selected task"
      title={task.tool.name}
      description="Latest task state, approval linkage, and execution review stay grouped in one bounded task summary."
      className={chrome === "embedded" ? "section-card--embedded" : undefined}
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={task.status} />
          <span className="detail-summary__label">
            {task.request.action} / {task.request.scope}
          </span>
        </div>

        <dl className="key-value-grid">
          <div>
            <dt>Task</dt>
            <dd className="mono">{task.id}</dd>
          </div>
          <div>
            <dt>Thread</dt>
            <dd className="mono">{task.thread_id}</dd>
          </div>
          <div>
            <dt>Latest approval</dt>
            <dd className="mono">{task.latest_approval_id ?? "Not linked"}</dd>
          </div>
          <div>
            <dt>Latest execution</dt>
            <dd className="mono">{task.latest_execution_id ?? "Not executed"}</dd>
          </div>
          <div>
            <dt>Task source</dt>
            <dd>{taskSource === "live" ? "Live task detail" : "Fixture task detail"}</dd>
          </div>
          <div>
            <dt>Step source</dt>
            <dd>{stepSource === "live" ? "Live task-step detail" : "Fixture task-step fallback"}</dd>
          </div>
        </dl>

        <div className="detail-group">
          <h3>Governed linkage</h3>
          <p className="muted-copy">
            {task.latest_approval_id
              ? "This task reflects the latest approval outcome and remains directly linked back to the approval inbox."
              : "No approval record is linked to this task in the current payload."}
          </p>
          {task.latest_approval_id ? (
            <div className="cluster">
              <Link href={`/approvals?approval=${task.latest_approval_id}`} className="button-secondary">
                Open linked approval
              </Link>
            </div>
          ) : null}
        </div>

        {showExecutionReview ? (
          <div className="detail-group">
            <h3>Execution review</h3>
            <ExecutionSummary
              execution={execution}
              source={executionSource}
              unavailableMessage={executionUnavailableMessage}
              emptyTitle="Task has not executed yet"
              emptyDescription="When execution runs for this task, the latest execution record and output snapshot will appear here."
            />
          </div>
        ) : null}
      </div>
    </SectionCard>
  );
}
