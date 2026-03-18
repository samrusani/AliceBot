import type { ApiSource, ApprovalItem, TaskItem, ThreadItem, ToolExecutionItem } from "../lib/api";
import { ApprovalDetail } from "./approval-detail";
import { EmptyState } from "./empty-state";
import { ExecutionSummary } from "./execution-summary";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";
import { TaskSummary } from "./task-summary";

type WorkflowSource = ApiSource | "unavailable";

type ThreadWorkflowPanelProps = {
  thread: ThreadItem | null;
  approval: ApprovalItem | null;
  approvalSource: WorkflowSource;
  approvalUnavailableReason?: string;
  task: TaskItem | null;
  taskSource: WorkflowSource;
  taskUnavailableReason?: string;
  execution: ToolExecutionItem | null;
  executionSource: WorkflowSource | null;
  executionUnavailableReason?: string;
  apiBaseUrl?: string;
  userId?: string;
};

function workflowModeLabel(
  approvalSource: WorkflowSource,
  taskSource: WorkflowSource,
  executionSource: WorkflowSource | null,
) {
  const sources = [approvalSource, taskSource, executionSource].filter(Boolean);

  if (sources.some((source) => source === "unavailable")) {
    return "Partial workflow review";
  }

  return sources.every((source) => source === "fixture") ? "Fixture workflow" : "Live workflow";
}

export function ThreadWorkflowPanel({
  thread,
  approval,
  approvalSource,
  approvalUnavailableReason,
  task,
  taskSource,
  taskUnavailableReason,
  execution,
  executionSource,
  executionUnavailableReason,
  apiBaseUrl,
  userId,
}: ThreadWorkflowPanelProps) {
  if (!thread) {
    return (
      <SectionCard
        eyebrow="Thread-linked workflow"
        title="Governed workflow stays with the thread"
        description="Approval, task, and execution review appears here once one visible thread is selected."
      >
        <EmptyState
          title="Select a thread"
          description="Choose or create a thread first so workflow review stays attached to one durable conversation."
        />
      </SectionCard>
    );
  }

  const hasWorkflow = Boolean(approval || task || execution);
  const hasUnavailableState =
    approvalSource === "unavailable" || taskSource === "unavailable" || executionSource === "unavailable";

  return (
    <SectionCard
      eyebrow="Thread-linked workflow"
      title="Governed workflow review"
      description="The latest approval, task, and execution state stays visible beside the selected thread without turning chat into a separate operations dashboard."
      className="thread-workflow-panel"
    >
      <div className="thread-workflow-panel__summary">
        <StatusBadge status={approval?.status ?? task?.status ?? execution?.status ?? "info"} />
        <div className="thread-workflow-panel__chips">
          <span className="subtle-chip">{workflowModeLabel(approvalSource, taskSource, executionSource)}</span>
          <span className="subtle-chip">Thread: {thread.title}</span>
          {approval ? <span className="subtle-chip">Approval: {approval.status.replace(/_/g, " ")}</span> : null}
          {task ? <span className="subtle-chip">Task: {task.status.replace(/_/g, " ")}</span> : null}
          {execution ? (
            <span className="subtle-chip">Execution: {execution.status.replace(/_/g, " ")}</span>
          ) : null}
        </div>
      </div>

      {!hasWorkflow && !hasUnavailableState ? (
        <EmptyState
          title="No governed workflow linked yet"
          description="When this thread produces an approval-gated request, the latest approval, task, and execution review will appear here."
        />
      ) : (
        <div className="thread-workflow-panel__stack">
          {approval ? (
            <ApprovalDetail
              initialApproval={approval}
              detailSource={approvalSource === "fixture" ? "fixture" : "live"}
              initialExecution={execution}
              executionSource={executionSource === "fixture" || executionSource === "live" ? executionSource : null}
              executionUnavailableMessage={executionUnavailableReason}
              apiBaseUrl={apiBaseUrl}
              userId={userId}
              chrome="embedded"
            />
          ) : approvalSource === "unavailable" ? (
            <EmptyState
              title="Approval review unavailable"
              description={
                approvalUnavailableReason ??
                "Approval state could not be loaded for the selected thread from the configured backend."
              }
              className="empty-state--compact"
            />
          ) : null}

          {task ? (
            <TaskSummary
              task={task}
              taskSource={taskSource === "fixture" ? "fixture" : "live"}
              stepSource={taskSource === "fixture" ? "fixture" : "live"}
              execution={execution}
              executionSource={executionSource === "fixture" || executionSource === "live" ? executionSource : null}
              executionUnavailableMessage={executionUnavailableReason}
              chrome="embedded"
              showExecutionReview={!approval}
            />
          ) : taskSource === "unavailable" ? (
            <EmptyState
              title="Task review unavailable"
              description={
                taskUnavailableReason ??
                "Task state could not be loaded for the selected thread from the configured backend."
              }
              className="empty-state--compact"
            />
          ) : null}

          {!approval && !task && (execution || executionSource === "unavailable") ? (
            <SectionCard
              eyebrow="Execution review"
              title={execution ? "Latest execution record" : "Execution review unavailable"}
              description="Execution outcome stays visible even when approval or task detail is missing from the selected-thread workflow review."
              className="section-card--embedded"
            >
              <ExecutionSummary
                execution={execution}
                source={executionSource === "fixture" || executionSource === "live" ? executionSource : null}
                unavailableMessage={
                  execution
                    ? null
                    : executionUnavailableReason ??
                      "Execution state could not be loaded for the selected thread from the configured backend."
                }
                emptyTitle="Execution record is unavailable"
                emptyDescription="Execution review appears here when a selected-thread execution record can be loaded."
              />
            </SectionCard>
          ) : null}
        </div>
      )}
    </SectionCard>
  );
}
