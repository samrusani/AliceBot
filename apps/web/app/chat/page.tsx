import { ModeToggle, type ChatMode } from "../../components/mode-toggle";
import { PageHeader } from "../../components/page-header";
import { RequestComposer } from "../../components/request-composer";
import { ResponseComposer } from "../../components/response-composer";
import { ResponseHistory } from "../../components/response-history";
import { ThreadTracePanel, type ThreadTraceTarget } from "../../components/thread-trace-panel";
import { ThreadWorkflowPanel } from "../../components/thread-workflow-panel";
import { ThreadCreate } from "../../components/thread-create";
import { ThreadEventList } from "../../components/thread-event-list";
import { ThreadList } from "../../components/thread-list";
import { ThreadSummary } from "../../components/thread-summary";
import type {
  AgentProfileItem,
  ApiSource,
  ApprovalItem,
  ResumptionBrief,
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
  DEFAULT_AGENT_PROFILE_ID,
  getApiConfig,
  getTaskSteps,
  getThreadDetail,
  getThreadEvents,
  getThreadResumptionBrief,
  getThreadSessions,
  hasLiveApiConfig,
  listAgentProfiles,
  listApprovals,
  listThreads,
  listTasks,
  listToolExecutions,
  shouldExpectThreadExecutionReview,
} from "../../lib/api";
import {
  approvalFixtures,
  agentProfileFixtures,
  executionFixtures,
  getFixtureThreadEvents,
  getFixtureThreadSessions,
  getFixtureTaskStepSummary,
  getFixtureTaskSteps,
  requestHistoryFixtures,
  responseHistoryFixtures,
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

type ProfileRegistrySource = ApiSource | "unavailable";

type ProfileRegistryViewModel = {
  profiles: AgentProfileItem[];
  source: ProfileRegistrySource;
  unavailableReason?: string;
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

type ResumptionBriefSource = ApiSource | "unavailable" | null;

type ResumptionBriefViewModel = {
  brief: ResumptionBrief | null;
  source: ResumptionBriefSource;
  unavailableReason?: string;
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

function normalizeTraceId(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeTraceId(value[0]);
  }

  return value?.trim() ?? "";
}

function normalizeAgentProfileId(value: string | null | undefined) {
  const profileId = value?.trim();
  return profileId && profileId.length > 0 ? profileId : DEFAULT_AGENT_PROFILE_ID;
}

function normalizeThreadItem(thread: ThreadItem): ThreadItem {
  return {
    ...thread,
    agent_profile_id: normalizeAgentProfileId(thread.agent_profile_id),
  };
}

function normalizeThreadItems(items: ThreadItem[]) {
  return items.map((item) => normalizeThreadItem(item));
}

function buildChatTraceHrefPrefix(mode: ChatMode, threadId: string) {
  const params = new URLSearchParams();

  if (mode === "request") {
    params.set("mode", "request");
  }

  if (threadId) {
    params.set("thread", threadId);
  }

  return `/chat?${params.toString()}${params.size > 0 ? "&" : ""}trace=`;
}

function buildThreadTraceTargets(
  selectedThreadId: string,
  workflow: WorkflowViewModel,
  liveModeReady: boolean,
): ThreadTraceTarget[] {
  const targetMap = new Map<string, ThreadTraceTarget>();

  function registerTarget(id: string | null | undefined, label: string) {
    const normalizedId = id?.trim();
    if (!normalizedId || targetMap.has(normalizedId)) {
      return;
    }

    targetMap.set(normalizedId, {
      id: normalizedId,
      label,
    });
  }

  registerTarget(workflow.execution?.trace_id, "Execution trace");
  registerTarget(workflow.approval?.routing.trace.trace_id, "Approval routing trace");

  for (const step of [...workflow.taskSteps].sort((left, right) => right.sequence_no - left.sequence_no)) {
    registerTarget(step.trace.trace_id, `Task step ${step.sequence_no} trace`);
  }

  if (!liveModeReady && selectedThreadId) {
    for (const entry of responseHistoryFixtures
      .filter((item) => item.threadId === selectedThreadId)
      .sort((left, right) => new Date(right.submittedAt).getTime() - new Date(left.submittedAt).getTime())) {
      registerTarget(entry.trace.responseTraceId, "Assistant response trace");
      registerTarget(entry.trace.compileTraceId, "Assistant compile trace");
    }

    for (const entry of requestHistoryFixtures
      .filter((item) => item.threadId === selectedThreadId)
      .sort((left, right) => new Date(right.submittedAt).getTime() - new Date(left.submittedAt).getTime())) {
      registerTarget(entry.trace.requestTraceId, "Governed request trace");
      registerTarget(entry.trace.routingTraceId, "Routing decision trace");
    }
  }

  return [...targetMap.values()];
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

function buildFixtureResumptionBrief(
  continuity: ContinuityViewModel,
  workflow: WorkflowViewModel,
): ResumptionBrief {
  const conversationItems = continuity.events
    .filter((event) => event.kind === "message.user" || event.kind === "message.assistant")
    .slice(-8);
  const latestTaskStep = workflow.taskSteps[workflow.taskSteps.length - 1] ?? null;

  return {
    assembly_version: "resumption_brief_v0",
    thread: continuity.selectedThread as NonNullable<ContinuityViewModel["selectedThread"]>,
    conversation: {
      items: conversationItems,
      summary: {
        limit: 8,
        returned_count: conversationItems.length,
        total_count: continuity.events.filter(
          (event) => event.kind === "message.user" || event.kind === "message.assistant",
        ).length,
        order: ["sequence_no_asc"],
        kinds: ["message.user", "message.assistant"],
      },
    },
    open_loops: {
      items: [],
      summary: {
        limit: 5,
        returned_count: 0,
        total_count: 0,
        order: ["opened_at_desc", "created_at_desc", "id_desc"],
      },
    },
    memory_highlights: {
      items: [],
      summary: {
        limit: 5,
        returned_count: 0,
        total_count: 0,
        order: ["updated_at_asc", "created_at_asc", "id_asc"],
      },
    },
    workflow: workflow.task
      ? {
          task: workflow.task,
          latest_task_step: latestTaskStep,
          summary: {
            present: true,
            task_order: ["created_at_asc", "id_asc"],
            task_step_order: ["sequence_no_asc", "created_at_asc", "id_asc"],
          },
        }
      : null,
    sources: workflow.task
      ? ["threads", "events", "open_loops", "memories", "tasks", "task_steps"]
      : ["threads", "events", "open_loops", "memories"],
  };
}

async function loadFixtureResumptionBrief(
  continuity: ContinuityViewModel,
  workflow: WorkflowViewModel,
): Promise<ResumptionBriefViewModel> {
  if (!continuity.selectedThread) {
    return {
      brief: null,
      source: "fixture",
    };
  }

  return {
    brief: buildFixtureResumptionBrief(continuity, workflow),
    source: "fixture",
  };
}

async function loadLiveResumptionBrief(
  apiBaseUrl: string,
  userId: string,
  selectedThreadId: string,
): Promise<ResumptionBriefViewModel> {
  if (!selectedThreadId) {
    return {
      brief: null,
      source: "live",
    };
  }

  try {
    const payload = await getThreadResumptionBrief(apiBaseUrl, selectedThreadId, userId);
    return {
      brief: payload.brief,
      source: "live",
    };
  } catch (error) {
    return {
      brief: null,
      source: "unavailable",
      unavailableReason: error instanceof Error ? error.message : "Resumption brief could not be loaded.",
    };
  }
}

async function loadFixtureContinuity(
  requestedThreadId: string,
  defaultThreadId: string,
): Promise<ContinuityViewModel> {
  const threads = normalizeThreadItems(threadFixtures);
  const selectedThreadId = resolveSelectedThreadId(requestedThreadId, defaultThreadId, threads);
  const selectedThread = selectedThreadId
    ? threads.find((item) => item.id === selectedThreadId) ?? null
    : null;

  return {
    threadListSource: "fixture",
    continuitySource: "fixture",
    threads,
    selectedThreadId,
    selectedThread,
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
    const threads = normalizeThreadItems(threadResponse.items);
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
          ? normalizeThreadItem(threadResult.value.thread)
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

async function loadFixtureProfileRegistry(): Promise<ProfileRegistryViewModel> {
  return {
    profiles: agentProfileFixtures,
    source: "fixture",
  };
}

async function loadLiveProfileRegistry(apiBaseUrl: string): Promise<ProfileRegistryViewModel> {
  try {
    const response = await listAgentProfiles(apiBaseUrl);
    return {
      profiles: response.items,
      source: "live",
    };
  } catch (error) {
    return {
      profiles: agentProfileFixtures,
      source: "fixture",
      unavailableReason:
        error instanceof Error ? error.message : "Agent profile registry could not be loaded.",
    };
  }
}

export default async function ChatPage({ searchParams }: ChatPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const mode = normalizeMode(resolvedSearchParams?.mode);
  const requestedThreadId = normalizeThreadId(resolvedSearchParams?.thread);
  const requestedTraceId = normalizeTraceId(resolvedSearchParams?.trace);
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);
  const [continuity, profileRegistry] = liveModeReady
    ? await Promise.all([
        loadLiveContinuity(
          apiConfig.apiBaseUrl,
          apiConfig.userId,
          requestedThreadId,
          apiConfig.defaultThreadId,
        ),
        loadLiveProfileRegistry(apiConfig.apiBaseUrl),
      ])
    : await Promise.all([
        loadFixtureContinuity(requestedThreadId, apiConfig.defaultThreadId),
        loadFixtureProfileRegistry(),
      ]);
  const workflow = liveModeReady
    ? await loadLiveWorkflow(apiConfig.apiBaseUrl, apiConfig.userId, continuity.selectedThreadId)
    : await loadFixtureWorkflow(continuity.selectedThreadId);
  const resumptionBrief = liveModeReady
    ? await loadLiveResumptionBrief(
        apiConfig.apiBaseUrl,
        apiConfig.userId,
        continuity.selectedThreadId,
      )
    : await loadFixtureResumptionBrief(continuity, workflow);
  const traceTargets = buildThreadTraceTargets(continuity.selectedThreadId, workflow, liveModeReady);
  const traceHrefPrefix = buildChatTraceHrefPrefix(mode, continuity.selectedThreadId);
  const threadTracePanel = await ThreadTracePanel({
    thread: continuity.selectedThread,
    source: liveModeReady ? "live" : "fixture",
    traceTargets,
    selectedTraceId: requestedTraceId,
    traceHrefPrefix,
    apiBaseUrl: liveModeReady ? apiConfig.apiBaseUrl : undefined,
    userId: liveModeReady ? apiConfig.userId : undefined,
  });

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
                traceHrefPrefix={traceHrefPrefix}
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
            traceHrefPrefix={traceHrefPrefix}
          />

          {threadTracePanel}

          <ThreadSummary
            thread={continuity.selectedThread}
            sessions={continuity.sessions}
            events={continuity.events}
            agentProfiles={profileRegistry.profiles}
            source={continuity.continuitySource}
            unavailableReason={continuity.unavailableReason}
            resumptionBrief={resumptionBrief.brief}
            resumptionSource={resumptionBrief.source}
            resumptionUnavailableReason={resumptionBrief.unavailableReason}
          />

          <ThreadList
            threads={continuity.threads}
            selectedThreadId={continuity.selectedThreadId}
            currentMode={mode}
            agentProfiles={profileRegistry.profiles}
            source={continuity.threadListSource}
            unavailableReason={continuity.unavailableReason}
          />

          <ThreadEventList
            threadTitle={continuity.selectedThread?.title}
            sessions={continuity.sessions}
            events={continuity.events}
            source={continuity.continuitySource}
            unavailableReason={continuity.unavailableReason}
            apiBaseUrl={liveModeReady ? apiConfig.apiBaseUrl : undefined}
            userId={liveModeReady ? apiConfig.userId : undefined}
          />

          <ThreadCreate
            apiBaseUrl={liveModeReady ? apiConfig.apiBaseUrl : undefined}
            userId={liveModeReady ? apiConfig.userId : undefined}
            currentMode={mode}
            agentProfiles={profileRegistry.profiles}
          />
        </div>
      </div>
    </div>
  );
}
