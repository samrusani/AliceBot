import { ModeToggle, type ChatMode } from "../../components/mode-toggle";
import { PageHeader } from "../../components/page-header";
import { RequestComposer } from "../../components/request-composer";
import { ResponseComposer } from "../../components/response-composer";
import { ResponseHistory } from "../../components/response-history";
import { ThreadWorkflowPanel } from "../../components/thread-workflow-panel";
import { ThreadCreate } from "../../components/thread-create";
import { ThreadEventList } from "../../components/thread-event-list";
import { ThreadList } from "../../components/thread-list";
import { ThreadSummary } from "../../components/thread-summary";
import type {
  ApiSource,
  ApprovalItem,
  TaskItem,
  TaskStepItem,
  TaskStepListSummary,
  ThreadEventItem,
  ThreadItem,
  ThreadSessionItem,
  ToolExecutionItem,
} from "../../lib/api";
import {
  deriveThreadWorkflowState,
  getApiConfig,
  getTaskSteps,
  getThreadDetail,
  getThreadEvents,
  getThreadSessions,
  hasLiveApiConfig,
  listApprovals,
  listThreads,
  listTasks,
  listToolExecutions,
  shouldExpectThreadExecutionReview,
} from "../../lib/api";
import {
  approvalFixtures,
  executionFixtures,
  getFixtureThread,
  getFixtureThreadEvents,
  getFixtureThreadSessions,
  getFixtureTaskStepSummary,
  getFixtureTaskSteps,
  requestHistoryFixtures,
  taskFixtures,
  threadFixtures,
} from "../../lib/fixtures";

type ChatPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

type ContinuitySource = "live" | "fixture" | "unavailable";

type ContinuityViewModel = {
  threadListSource: ContinuitySource;
  continuitySource: ContinuitySource;
  unavailableReason?: string;
  threads: ThreadItem[];
  selectedThreadId: string;
  selectedThread: ThreadItem | null;
  sessions: ThreadSessionItem[];
  events: ThreadEventItem[];
};

type WorkflowSource = ApiSource | "unavailable";

type WorkflowViewModel = {
  approval: ApprovalItem | null;
  approvalSource: WorkflowSource;
  approvalUnavailableReason?: string;
  task: TaskItem | null;
  taskSource: WorkflowSource;
  taskUnavailableReason?: string;
  execution: ToolExecutionItem | null;
  executionSource: WorkflowSource | null;
  executionUnavailableReason?: string;
  taskSteps: TaskStepItem[];
  taskStepSummary: TaskStepListSummary | null;
  taskStepSource: WorkflowSource | null;
  taskStepUnavailableReason?: string;
};

function normalizeMode(value: string | string[] | undefined): ChatMode {
  if (Array.isArray(value)) {
    return normalizeMode(value[0]);
  }

  return value === "request" ? "request" : "assistant";
}

function normalizeThreadId(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeThreadId(value[0]);
  }

  return value?.trim() ?? "";
}

function resolveSelectedThreadId(
  requestedThreadId: string,
  defaultThreadId: string,
  threads: ThreadItem[],
) {
  const availableIds = new Set(threads.map((thread) => thread.id));

  if (requestedThreadId && availableIds.has(requestedThreadId)) {
    return requestedThreadId;
  }

  if (defaultThreadId && availableIds.has(defaultThreadId)) {
    return defaultThreadId;
  }

  return threads[0]?.id ?? "";
}

async function loadFixtureWorkflow(selectedThreadId: string): Promise<WorkflowViewModel> {
  if (!selectedThreadId) {
    return {
      approval: null,
      approvalSource: "fixture",
      task: null,
      taskSource: "fixture",
      execution: null,
      executionSource: null,
      taskSteps: [],
      taskStepSummary: null,
      taskStepSource: null,
    };
  }

  const { approval, task, execution } = deriveThreadWorkflowState(
    selectedThreadId,
    approvalFixtures,
    taskFixtures,
    executionFixtures,
  );

  return {
    approval,
    approvalSource: "fixture",
    task,
    taskSource: "fixture",
    execution,
    executionSource: execution ? "fixture" : null,
    taskSteps: task ? getFixtureTaskSteps(task.id) : [],
    taskStepSummary: task ? getFixtureTaskStepSummary(task.id) : null,
    taskStepSource: task ? "fixture" : null,
  };
}

async function loadLiveWorkflow(
  apiBaseUrl: string,
  userId: string,
  selectedThreadId: string,
): Promise<WorkflowViewModel> {
  if (!selectedThreadId) {
    return {
      approval: null,
      approvalSource: "live",
      task: null,
      taskSource: "live",
      execution: null,
      executionSource: null,
      taskSteps: [],
      taskStepSummary: null,
      taskStepSource: null,
    };
  }

  const [approvalsResult, tasksResult, executionsResult] = await Promise.allSettled([
    listApprovals(apiBaseUrl, userId),
    listTasks(apiBaseUrl, userId),
    listToolExecutions(apiBaseUrl, userId),
  ]);

  const approvalItems = approvalsResult.status === "fulfilled" ? approvalsResult.value.items : [];
  const taskItems = tasksResult.status === "fulfilled" ? tasksResult.value.items : [];
  const executionItems = executionsResult.status === "fulfilled" ? executionsResult.value.items : [];
  const derivedWorkflow = deriveThreadWorkflowState(
    selectedThreadId,
    approvalItems,
    taskItems,
    executionItems,
  );
  let taskSteps: TaskStepItem[] = [];
  let taskStepSummary: TaskStepListSummary | null = null;
  let taskStepSource: WorkflowSource | null = derivedWorkflow.task ? "live" : null;
  let taskStepUnavailableReason: string | undefined;

  if (derivedWorkflow.task) {
    try {
      const taskStepPayload = await getTaskSteps(apiBaseUrl, derivedWorkflow.task.id, userId);
      taskSteps = taskStepPayload.items;
      taskStepSummary = taskStepPayload.summary;
      taskStepSource = "live";
    } catch (error) {
      taskStepSource = "unavailable";
      taskStepUnavailableReason =
        error instanceof Error ? error.message : "Task-step timeline could not be loaded.";
    }
  }

  const expectsExecutionReview = shouldExpectThreadExecutionReview(
    derivedWorkflow.approval,
    derivedWorkflow.task,
  );

  return {
    approval: derivedWorkflow.approval,
    approvalSource:
      approvalsResult.status === "fulfilled"
        ? "live"
        : "unavailable",
    approvalUnavailableReason:
      approvalsResult.status === "rejected"
        ? approvalsResult.reason instanceof Error
          ? approvalsResult.reason.message
          : "Approvals could not be loaded."
        : undefined,
    task: derivedWorkflow.task,
    taskSource: tasksResult.status === "fulfilled" ? "live" : "unavailable",
    taskUnavailableReason:
      tasksResult.status === "rejected"
        ? tasksResult.reason instanceof Error
          ? tasksResult.reason.message
          : "Tasks could not be loaded."
        : undefined,
    execution: derivedWorkflow.execution,
    executionSource:
      executionsResult.status === "fulfilled"
        ? derivedWorkflow.execution
          ? "live"
          : null
        : expectsExecutionReview
          ? "unavailable"
          : null,
    executionUnavailableReason:
      executionsResult.status === "rejected" && expectsExecutionReview
        ? executionsResult.reason instanceof Error
          ? executionsResult.reason.message
          : "Execution state could not be loaded."
        : undefined,
    taskSteps,
    taskStepSummary,
    taskStepSource,
    taskStepUnavailableReason,
  };
}

async function loadFixtureContinuity(
  requestedThreadId: string,
  defaultThreadId: string,
): Promise<ContinuityViewModel> {
  const selectedThreadId = resolveSelectedThreadId(requestedThreadId, defaultThreadId, threadFixtures);

  return {
    threadListSource: "fixture",
    continuitySource: "fixture",
    threads: threadFixtures,
    selectedThreadId,
    selectedThread: selectedThreadId ? getFixtureThread(selectedThreadId) : null,
    sessions: selectedThreadId ? getFixtureThreadSessions(selectedThreadId) : [],
    events: selectedThreadId ? getFixtureThreadEvents(selectedThreadId) : [],
  };
}

async function loadLiveContinuity(
  apiBaseUrl: string,
  userId: string,
  requestedThreadId: string,
  defaultThreadId: string,
): Promise<ContinuityViewModel> {
  try {
    const threadResponse = await listThreads(apiBaseUrl, userId);
    const threads = threadResponse.items;
    const selectedThreadId = resolveSelectedThreadId(requestedThreadId, defaultThreadId, threads);

    if (!selectedThreadId) {
      return {
        threadListSource: "live",
        continuitySource: "live",
        threads,
        selectedThreadId: "",
        selectedThread: null,
        sessions: [],
        events: [],
      };
    }

    const [threadResult, sessionsResult, eventsResult] = await Promise.allSettled([
      getThreadDetail(apiBaseUrl, selectedThreadId, userId),
      getThreadSessions(apiBaseUrl, selectedThreadId, userId),
      getThreadEvents(apiBaseUrl, selectedThreadId, userId),
    ]);

    const unavailableReason =
      threadResult.status === "rejected"
        ? threadResult.reason instanceof Error
          ? threadResult.reason.message
          : "Thread detail failed to load."
        : sessionsResult.status === "rejected"
          ? sessionsResult.reason instanceof Error
            ? sessionsResult.reason.message
            : "Thread sessions failed to load."
          : eventsResult.status === "rejected"
            ? eventsResult.reason instanceof Error
              ? eventsResult.reason.message
              : "Thread events failed to load."
            : undefined;

    return {
      threadListSource: "live",
      continuitySource: unavailableReason ? "unavailable" : "live",
      unavailableReason,
      threads,
      selectedThreadId,
      selectedThread:
        threadResult.status === "fulfilled"
          ? threadResult.value.thread
          : threads.find((thread) => thread.id === selectedThreadId) ?? null,
      sessions: sessionsResult.status === "fulfilled" ? sessionsResult.value.items : [],
      events: eventsResult.status === "fulfilled" ? eventsResult.value.items : [],
    };
  } catch (error) {
    return {
      threadListSource: "unavailable",
      continuitySource: "unavailable",
      unavailableReason: error instanceof Error ? error.message : "Thread continuity failed to load.",
      threads: [],
      selectedThreadId: "",
      selectedThread: null,
      sessions: [],
      events: [],
    };
  }
}

export default async function ChatPage({ searchParams }: ChatPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const mode = normalizeMode(resolvedSearchParams?.mode);
  const requestedThreadId = normalizeThreadId(resolvedSearchParams?.thread);
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);
  const continuity = liveModeReady
    ? await loadLiveContinuity(
        apiConfig.apiBaseUrl,
        apiConfig.userId,
        requestedThreadId,
        apiConfig.defaultThreadId,
      )
    : await loadFixtureContinuity(requestedThreadId, apiConfig.defaultThreadId);
  const workflow = liveModeReady
    ? await loadLiveWorkflow(apiConfig.apiBaseUrl, apiConfig.userId, continuity.selectedThreadId)
    : await loadFixtureWorkflow(continuity.selectedThreadId);

  const initialRequestEntries = liveModeReady ? [] : requestHistoryFixtures;

  return (
    <div className="page-stack page-stack--chat">
      <PageHeader
        eyebrow="Operator conversation surface"
        title="Chat with the assistant or route a governed request"
        description="Normal conversation and approval-gated actions now share one calm shell. Thread identity stays explicit, bounded, and visible so continuity never depends on a raw UUID field."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">
              {continuity.continuitySource === "unavailable"
                ? "Continuity unavailable"
                : liveModeReady
                  ? "Live continuity enabled"
                  : "Fixture continuity preview"}
            </span>
            <span className="subtle-chip">
              {continuity.selectedThread
                ? `Selected: ${continuity.selectedThread.title}`
                : "Select or create a thread"}
            </span>
          </div>
        }
      />

      <ModeToggle currentMode={mode} selectedThreadId={continuity.selectedThreadId} />

      <div className="chat-layout">
        <div className="chat-layout__main">
          {mode === "assistant" ? (
            <ResponseComposer
              initialEntries={[]}
              apiBaseUrl={apiConfig.apiBaseUrl}
              userId={apiConfig.userId}
              selectedThreadId={continuity.selectedThreadId}
              selectedThreadTitle={continuity.selectedThread?.title}
              events={continuity.events}
              source={continuity.continuitySource}
              unavailableReason={continuity.unavailableReason}
            />
          ) : (
            <>
              <ResponseHistory
                entries={[]}
                threadTitle={continuity.selectedThread?.title}
                events={continuity.events}
                source={continuity.continuitySource}
                unavailableReason={continuity.unavailableReason}
              />
              <RequestComposer
                initialEntries={initialRequestEntries}
                apiBaseUrl={apiConfig.apiBaseUrl}
                userId={apiConfig.userId}
                selectedThreadId={continuity.selectedThreadId}
                selectedThreadTitle={continuity.selectedThread?.title}
                defaultToolId={apiConfig.defaultToolId}
              />
            </>
          )}
        </div>

        <div className="chat-layout__rail">
          <ThreadWorkflowPanel
            thread={continuity.selectedThread}
            approval={workflow.approval}
            approvalSource={workflow.approvalSource}
            approvalUnavailableReason={workflow.approvalUnavailableReason}
            task={workflow.task}
            taskSource={workflow.taskSource}
            taskUnavailableReason={workflow.taskUnavailableReason}
            execution={workflow.execution}
            executionSource={workflow.executionSource}
            executionUnavailableReason={workflow.executionUnavailableReason}
            taskSteps={workflow.taskSteps}
            taskStepSummary={workflow.taskStepSummary}
            taskStepSource={workflow.taskStepSource}
            taskStepUnavailableReason={workflow.taskStepUnavailableReason}
            apiBaseUrl={liveModeReady ? apiConfig.apiBaseUrl : undefined}
            userId={liveModeReady ? apiConfig.userId : undefined}
          />

          <ThreadSummary
            thread={continuity.selectedThread}
            sessions={continuity.sessions}
            events={continuity.events}
            source={continuity.continuitySource}
            unavailableReason={continuity.unavailableReason}
          />

          <ThreadList
            threads={continuity.threads}
            selectedThreadId={continuity.selectedThreadId}
            currentMode={mode}
            source={continuity.threadListSource}
            unavailableReason={continuity.unavailableReason}
          />

          <ThreadEventList
            threadTitle={continuity.selectedThread?.title}
            sessions={continuity.sessions}
            events={continuity.events}
            source={continuity.continuitySource}
            unavailableReason={continuity.unavailableReason}
          />

          <ThreadCreate
            apiBaseUrl={liveModeReady ? apiConfig.apiBaseUrl : undefined}
            userId={liveModeReady ? apiConfig.userId : undefined}
            currentMode={mode}
          />
        </div>
      </div>
    </div>
  );
}
