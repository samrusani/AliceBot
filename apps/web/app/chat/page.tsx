import { ModeToggle, type ChatMode } from "../../components/mode-toggle";
import { PageHeader } from "../../components/page-header";
import { RequestComposer } from "../../components/request-composer";
import { ResponseComposer } from "../../components/response-composer";
import { ResponseHistory } from "../../components/response-history";
import { ThreadCreate } from "../../components/thread-create";
import { ThreadEventList } from "../../components/thread-event-list";
import { ThreadList } from "../../components/thread-list";
import { ThreadSummary } from "../../components/thread-summary";
import type { ThreadEventItem, ThreadItem, ThreadSessionItem } from "../../lib/api";
import {
  getApiConfig,
  getThreadDetail,
  getThreadEvents,
  getThreadSessions,
  hasLiveApiConfig,
  listThreads,
} from "../../lib/api";
import {
  getFixtureThread,
  getFixtureThreadEvents,
  getFixtureThreadSessions,
  requestHistoryFixtures,
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

  const initialRequestEntries = liveModeReady ? [] : requestHistoryFixtures;

  return (
    <div className="page-stack">
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
