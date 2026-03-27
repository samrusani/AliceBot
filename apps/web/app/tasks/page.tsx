import { PageHeader } from "../../components/page-header";
import { TaskList } from "../../components/task-list";
import { TaskRunList } from "../../components/task-run-list";
import { TaskStepList } from "../../components/task-step-list";
import { TaskSummary } from "../../components/task-summary";
import {
  combinePageModes,
  getApiConfig,
  getTaskDetail,
  listTaskRuns,
  getTaskSteps,
  getToolExecution,
  hasLiveApiConfig,
  listTasks,
  pageModeLabel,
  type ApiSource,
  type TaskItem,
  type TaskRunItem,
} from "../../lib/api";
import {
  getFixtureExecution,
  getFixtureTask,
  getFixtureTaskStepSummary,
  getFixtureTaskSteps,
  taskFixtures,
} from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function buildFixtureTaskRuns(task: TaskItem): TaskRunItem[] {
  if (task.status === "executed") {
    return [
      {
        id: `fixture-run-${task.id}`,
        task_id: task.id,
        status: "done",
        checkpoint: {
          cursor: 2,
          target_steps: 2,
          wait_for_signal: false,
        },
        tick_count: 2,
        step_count: 2,
        max_ticks: 3,
        retry_count: 0,
        retry_cap: 3,
        retry_posture: "terminal",
        failure_class: null,
        stop_reason: "done",
        last_transitioned_at: task.updated_at,
        created_at: task.created_at,
        updated_at: task.updated_at,
      },
    ];
  }

  if (task.status === "denied") {
    return [
      {
        id: `fixture-run-${task.id}`,
        task_id: task.id,
        status: "cancelled",
        checkpoint: {
          cursor: 0,
          target_steps: 1,
          wait_for_signal: false,
        },
        tick_count: 0,
        step_count: 0,
        max_ticks: 1,
        retry_count: 0,
        retry_cap: 1,
        retry_posture: "terminal",
        failure_class: null,
        stop_reason: "cancelled",
        last_transitioned_at: task.updated_at,
        created_at: task.created_at,
        updated_at: task.updated_at,
      },
    ];
  }

  if (task.status === "blocked") {
    return [
      {
        id: `fixture-run-${task.id}`,
        task_id: task.id,
        status: "failed",
        checkpoint: {
          cursor: 1,
          target_steps: 2,
          wait_for_signal: false,
        },
        tick_count: 1,
        step_count: 1,
        max_ticks: 1,
        retry_count: 0,
        retry_cap: 1,
        retry_posture: "terminal",
        failure_class: "budget",
        stop_reason: "budget_exhausted",
        last_transitioned_at: task.updated_at,
        created_at: task.created_at,
        updated_at: task.updated_at,
      },
    ];
  }

  if (task.status === "pending_approval") {
    return [
      {
        id: `fixture-run-${task.id}`,
        task_id: task.id,
        status: "waiting_approval",
        checkpoint: {
          cursor: 1,
          target_steps: 2,
          wait_for_signal: true,
          waiting_approval_id: task.latest_approval_id,
        },
        tick_count: 1,
        step_count: 1,
        max_ticks: 3,
        retry_count: 0,
        retry_cap: 3,
        retry_posture: "awaiting_approval",
        failure_class: null,
        stop_reason: "waiting_approval",
        last_transitioned_at: task.updated_at,
        created_at: task.created_at,
        updated_at: task.updated_at,
      },
    ];
  }

  return [
    {
      id: `fixture-run-${task.id}`,
      task_id: task.id,
      status: "queued",
      checkpoint: {
        cursor: 0,
        target_steps: 2,
        wait_for_signal: false,
      },
      tick_count: 0,
      step_count: 0,
      max_ticks: 2,
      retry_count: 0,
      retry_cap: 2,
      retry_posture: "none",
      failure_class: null,
      stop_reason: null,
      last_transitioned_at: task.updated_at,
      created_at: task.created_at,
      updated_at: task.updated_at,
    },
  ];
}

export default async function TasksPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const requestedTaskId = typeof params.task === "string" ? params.task : undefined;
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let items = taskFixtures;
  let listSource: ApiSource = "fixture";
  if (liveModeReady) {
    try {
      const payload = await listTasks(apiConfig.apiBaseUrl, apiConfig.userId);
      items = payload.items;
      listSource = "live";
    } catch {
      items = taskFixtures;
      listSource = "fixture";
    }
  }

  const selectedFromList = items.find((item) => item.id === requestedTaskId) ?? items[0] ?? null;
  let selectedTask = selectedFromList;
  let taskSource: ApiSource = selectedTask ? listSource : "fixture";

  if (selectedFromList && liveModeReady && listSource === "live") {
    try {
      const payload = await getTaskDetail(apiConfig.apiBaseUrl, selectedFromList.id, apiConfig.userId);
      selectedTask = payload.task;
      taskSource = "live";
    } catch {
      selectedTask = getFixtureTask(selectedFromList.id) ?? selectedFromList;
      taskSource = selectedTask === selectedFromList ? "live" : "fixture";
    }
  }

  let steps = selectedTask ? getFixtureTaskSteps(selectedTask.id) : [];
  let stepSummary = selectedTask ? getFixtureTaskStepSummary(selectedTask.id) : null;
  let stepSource: ApiSource = selectedTask ? "fixture" : listSource;

  if (selectedTask && liveModeReady && taskSource === "live") {
    try {
      const payload = await getTaskSteps(apiConfig.apiBaseUrl, selectedTask.id, apiConfig.userId);
      steps = payload.items;
      stepSummary = payload.summary;
      stepSource = "live";
    } catch {
      steps = getFixtureTaskSteps(selectedTask.id);
      stepSummary = getFixtureTaskStepSummary(selectedTask.id);
      stepSource = "fixture";
    }
  }

  let execution = selectedTask?.latest_execution_id ? getFixtureExecution(selectedTask.latest_execution_id) : null;
  let executionSource: ApiSource | null = execution ? "fixture" : null;
  let executionUnavailableMessage: string | null = null;

  if (selectedTask?.latest_execution_id && liveModeReady && taskSource === "live") {
    try {
      const payload = await getToolExecution(
        apiConfig.apiBaseUrl,
        selectedTask.latest_execution_id,
        apiConfig.userId,
      );
      execution = payload.execution;
      executionSource = "live";
    } catch {
      execution = getFixtureExecution(selectedTask.latest_execution_id);
      executionSource = execution ? "fixture" : null;
      executionUnavailableMessage = execution
        ? null
        : "The latest execution record could not be read from the configured backend.";
    }
  }

  let taskRuns = selectedTask ? buildFixtureTaskRuns(selectedTask) : [];
  let taskRunSource: ApiSource | "unavailable" = selectedTask ? "fixture" : "unavailable";
  let taskRunUnavailableMessage: string | null = null;

  if (selectedTask && liveModeReady && taskSource === "live") {
    try {
      const payload = await listTaskRuns(apiConfig.apiBaseUrl, selectedTask.id, apiConfig.userId);
      taskRuns = payload.items;
      taskRunSource = "live";
    } catch {
      taskRuns = [];
      taskRunSource = "unavailable";
      taskRunUnavailableMessage = "The task-run records could not be read from the configured backend.";
    }
  }

  const pageMode = combinePageModes(
    listSource,
    selectedTask ? taskSource : null,
    selectedTask ? stepSource : null,
    execution ? executionSource : null,
    taskRunSource === "unavailable" ? null : taskRunSource,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Tasks"
        title="Task lifecycle inspection"
        description="Tasks and task steps stay legible in a split review layout so approval linkage, execution state, and downstream outcome remain visible without overflow or guesswork."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(pageMode)}</span>
            <span className="subtle-chip">{items.length} tasks</span>
          </div>
        }
      />

      <div className="dashboard-grid dashboard-grid--detail">
        <TaskList tasks={items} selectedId={selectedTask?.id} />

        <div className="stack">
          <TaskSummary
            task={selectedTask}
            taskSource={taskSource}
            stepSource={stepSource}
            execution={execution}
            executionSource={executionSource}
            executionUnavailableMessage={executionUnavailableMessage}
          />
          <TaskRunList
            task={selectedTask}
            runs={taskRuns}
            source={taskRunSource}
            unavailableMessage={taskRunUnavailableMessage}
          />
          <TaskStepList steps={steps} summary={stepSummary} source={stepSource} />
        </div>
      </div>
    </div>
  );
}
