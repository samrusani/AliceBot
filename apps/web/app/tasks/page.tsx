import { PageHeader } from "../../components/page-header";
import { TaskList } from "../../components/task-list";
import { TaskStepList } from "../../components/task-step-list";
import { TaskSummary } from "../../components/task-summary";
import {
  combinePageModes,
  getApiConfig,
  getTaskDetail,
  getTaskSteps,
  hasLiveApiConfig,
  listTasks,
  pageModeLabel,
  type ApiSource,
} from "../../lib/api";
import {
  getFixtureTask,
  getFixtureTaskStepSummary,
  getFixtureTaskSteps,
  taskFixtures,
} from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

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

  const pageMode = combinePageModes(listSource, selectedTask ? taskSource : null, selectedTask ? stepSource : null);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Tasks"
        title="Task lifecycle inspection"
        description="Tasks and task steps stay legible in a split review layout so state, provenance, approval linkage, and next action remain visible without overflow or guesswork."
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
          <TaskSummary task={selectedTask} taskSource={taskSource} stepSource={stepSource} />
          <TaskStepList steps={steps} summary={stepSummary} source={stepSource} />
        </div>
      </div>
    </div>
  );
}
