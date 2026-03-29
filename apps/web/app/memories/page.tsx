import { MemoryDetail } from "../../components/memory-detail";
import { MemoryLabelForm } from "../../components/memory-label-form";
import { MemoryLabelList } from "../../components/memory-label-list";
import { MemoryList } from "../../components/memory-list";
import { MemoryRevisionList } from "../../components/memory-revision-list";
import { MemorySummary } from "../../components/memory-summary";
import { PageHeader } from "../../components/page-header";
import type {
  ApiSource,
  MemoryReviewLabelSummary,
  MemoryReviewQueuePriorityMode,
  MemoryReviewRecord,
  MemoryRevisionReviewListSummary,
  OpenLoopListSummary,
  OpenLoopRecord,
} from "../../lib/api";
import {
  combinePageModes,
  getOpenLoopDetail,
  getApiConfig,
  getMemoryDetail,
  getMemoryEvaluationSummary,
  getMemoryRevisions,
  hasLiveApiConfig,
  listOpenLoops,
  listMemories,
  listMemoryLabels,
  listMemoryReviewQueue,
  pageModeLabel,
} from "../../lib/api";
import {
  getFixtureMemory,
  getFixtureMemoryLabelSummary,
  getFixtureMemoryLabels,
  getFixtureMemoryRevisionSummary,
  getFixtureMemoryRevisions,
  memoryEvaluationSummaryFixture,
  memoryFixtures,
  memoryLabelFixtures,
  memoryReviewListSummaryFixture,
  memoryReviewQueueFixtures,
  memoryReviewQueueSummaryFixture,
} from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }

  return value?.trim() ?? "";
}

function normalizeFilter(value: string | string[] | undefined): "active" | "queue" {
  const normalized = normalizeParam(value).toLowerCase();
  return normalized === "queue" ? "queue" : "active";
}

function normalizeQueuePriorityMode(
  value: string | string[] | undefined,
): MemoryReviewQueuePriorityMode {
  const normalized = normalizeParam(value).toLowerCase();
  if (
    normalized === "oldest_first" ||
    normalized === "recent_first" ||
    normalized === "high_risk_first" ||
    normalized === "stale_truth_first"
  ) {
    return normalized;
  }
  return "recent_first";
}

function resolveSelectedMemoryId(requestedMemoryId: string, items: MemoryReviewRecord[]) {
  if (!items.length) {
    return "";
  }

  const availableIds = new Set(items.map((item) => item.id));
  if (requestedMemoryId && availableIds.has(requestedMemoryId)) {
    return requestedMemoryId;
  }

  return items[0]?.id ?? "";
}

function queueItemAsMemory(item: {
  id: string;
  memory_key: string;
  value: unknown;
  status: "active";
  source_event_ids: string[];
  memory_type: MemoryReviewRecord["memory_type"];
  confidence: MemoryReviewRecord["confidence"];
  salience: MemoryReviewRecord["salience"];
  confirmation_status: MemoryReviewRecord["confirmation_status"];
  valid_from: MemoryReviewRecord["valid_from"];
  valid_to: MemoryReviewRecord["valid_to"];
  last_confirmed_at: MemoryReviewRecord["last_confirmed_at"];
  created_at: string;
  updated_at: string;
}): MemoryReviewRecord {
  return {
    ...item,
    deleted_at: null,
  };
}

function formatTypedValue(value: string | null | undefined) {
  if (value == null) {
    return "Not set";
  }
  return value;
}

function formatTypedScore(value: number | null | undefined) {
  if (value == null) {
    return "Not set";
  }
  return value.toFixed(2);
}

function formatTypedTimestamp(value: string | null | undefined) {
  return value ?? "Not set";
}

const openLoopFixtures: OpenLoopRecord[] = [
  {
    id: "loop-fixture-1",
    memory_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
    title: "Confirm magnesium package size before reorder",
    status: "open",
    opened_at: "2026-03-20T09:00:00Z",
    due_at: "2026-03-24T09:00:00Z",
    resolved_at: null,
    resolution_note: null,
    created_at: "2026-03-20T09:00:00Z",
    updated_at: "2026-03-20T09:00:00Z",
  },
  {
    id: "loop-fixture-2",
    memory_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
    title: "Verify merchant preference after next approval",
    status: "open",
    opened_at: "2026-03-19T09:00:00Z",
    due_at: null,
    resolved_at: null,
    resolution_note: null,
    created_at: "2026-03-19T09:00:00Z",
    updated_at: "2026-03-19T09:00:00Z",
  },
];

const openLoopSummaryFixture: OpenLoopListSummary = {
  status: "open",
  limit: 20,
  returned_count: openLoopFixtures.length,
  total_count: openLoopFixtures.length,
  has_more: false,
  order: ["opened_at_desc", "created_at_desc", "id_desc"],
};

function resolveSelectedOpenLoopId(requestedOpenLoopId: string, items: OpenLoopRecord[]) {
  if (!items.length) {
    return "";
  }

  const availableIds = new Set(items.map((item) => item.id));
  if (requestedOpenLoopId && availableIds.has(requestedOpenLoopId)) {
    return requestedOpenLoopId;
  }

  return items[0]?.id ?? "";
}

export default async function MemoriesPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const requestedMemoryId = normalizeParam(params.memory);
  const requestedOpenLoopId = normalizeParam(params.open_loop);
  const activeFilter = normalizeFilter(params.filter);
  const queuePriorityMode = normalizeQueuePriorityMode(params.priority_mode);
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let memories = memoryFixtures;
  let memoryListSummary = memoryReviewListSummaryFixture;
  let memoryListSource: ApiSource = "fixture";
  let memoryListUnavailableReason: string | undefined;

  let reviewQueue = memoryReviewQueueFixtures;
  let reviewQueueSummary = memoryReviewQueueSummaryFixture;
  let reviewQueueSource: ApiSource = "fixture";
  let reviewQueueUnavailableReason: string | undefined;

  let evaluationSummary = memoryEvaluationSummaryFixture;
  let evaluationSummarySource: ApiSource = "fixture";
  let evaluationSummaryUnavailableReason: string | undefined;

  let openLoops = openLoopFixtures;
  let openLoopSummary = openLoopSummaryFixture;
  let openLoopSource: ApiSource = "fixture";
  let openLoopUnavailableReason: string | undefined;

  if (liveModeReady) {
    const [memoryResult, queueResult, summaryResult, openLoopResult] = await Promise.allSettled([
      listMemories(apiConfig.apiBaseUrl, apiConfig.userId, { status: "active" }),
      listMemoryReviewQueue(apiConfig.apiBaseUrl, apiConfig.userId, {
        priorityMode: queuePriorityMode,
      }),
      getMemoryEvaluationSummary(apiConfig.apiBaseUrl, apiConfig.userId),
      listOpenLoops(apiConfig.apiBaseUrl, apiConfig.userId, { status: "open", limit: 20 }),
    ]);

    if (memoryResult.status === "fulfilled") {
      memories = memoryResult.value.items;
      memoryListSummary = memoryResult.value.summary;
      memoryListSource = "live";
    } else {
      memoryListUnavailableReason =
        memoryResult.reason instanceof Error
          ? memoryResult.reason.message
          : "Memory list could not be loaded.";
    }

    if (queueResult.status === "fulfilled") {
      reviewQueue = queueResult.value.items;
      reviewQueueSummary = queueResult.value.summary;
      reviewQueueSource = "live";
    } else {
      reviewQueueUnavailableReason =
        queueResult.reason instanceof Error
          ? queueResult.reason.message
          : "Memory review queue could not be loaded.";
    }

    if (summaryResult.status === "fulfilled") {
      evaluationSummary = summaryResult.value.summary;
      evaluationSummarySource = "live";
    } else {
      evaluationSummaryUnavailableReason =
        summaryResult.reason instanceof Error
          ? summaryResult.reason.message
          : "Memory evaluation summary could not be loaded.";
    }

    if (openLoopResult.status === "fulfilled") {
      openLoops = openLoopResult.value.items;
      openLoopSummary = openLoopResult.value.summary;
      openLoopSource = "live";
    } else {
      openLoopUnavailableReason =
        openLoopResult.reason instanceof Error
          ? openLoopResult.reason.message
          : "Open-loop list could not be loaded.";
    }
  }

  const visibleMemories =
    activeFilter === "queue" ? reviewQueue.map((item) => queueItemAsMemory(item)) : memories;
  const selectedMemoryId = resolveSelectedMemoryId(requestedMemoryId, visibleMemories);
  const selectedFromVisibleList = visibleMemories.find((item) => item.id === selectedMemoryId) ?? null;
  const selectedListSource = activeFilter === "queue" ? reviewQueueSource : memoryListSource;
  const selectedQueueIndex =
    activeFilter === "queue" && selectedMemoryId
      ? visibleMemories.findIndex((item) => item.id === selectedMemoryId)
      : -1;
  const nextQueueMemoryId =
    selectedQueueIndex >= 0 ? visibleMemories[selectedQueueIndex + 1]?.id ?? null : null;

  let selectedMemory = selectedFromVisibleList;
  let selectedMemorySource: ApiSource | null = selectedMemory ? selectedListSource : null;
  let selectedMemoryUnavailableReason: string | undefined;

  if (selectedFromVisibleList && liveModeReady && selectedListSource === "live") {
    try {
      const payload = await getMemoryDetail(
        apiConfig.apiBaseUrl,
        selectedFromVisibleList.id,
        apiConfig.userId,
      );
      selectedMemory = payload.memory;
      selectedMemorySource = "live";
    } catch (error) {
      const fixtureMemory = getFixtureMemory(selectedFromVisibleList.id);
      if (fixtureMemory) {
        selectedMemory = fixtureMemory;
        selectedMemorySource = "fixture";
      }
      selectedMemoryUnavailableReason =
        error instanceof Error ? error.message : "Selected memory detail could not be loaded.";
    }
  }

  const selectedOpenLoopId = resolveSelectedOpenLoopId(requestedOpenLoopId, openLoops);
  const selectedOpenLoopFromList = openLoops.find((item) => item.id === selectedOpenLoopId) ?? null;
  let selectedOpenLoop = selectedOpenLoopFromList;
  let selectedOpenLoopSource: ApiSource | null = selectedOpenLoop ? openLoopSource : null;
  let selectedOpenLoopUnavailableReason: string | undefined;

  if (selectedOpenLoopFromList && liveModeReady && openLoopSource === "live") {
    try {
      const payload = await getOpenLoopDetail(
        apiConfig.apiBaseUrl,
        selectedOpenLoopFromList.id,
        apiConfig.userId,
      );
      selectedOpenLoop = payload.open_loop;
      selectedOpenLoopSource = "live";
    } catch (error) {
      const fixtureOpenLoop = openLoopFixtures.find((item) => item.id === selectedOpenLoopFromList.id);
      if (fixtureOpenLoop) {
        selectedOpenLoop = fixtureOpenLoop;
        selectedOpenLoopSource = "fixture";
      } else {
        selectedOpenLoop = null;
        selectedOpenLoopSource = null;
      }
      selectedOpenLoopUnavailableReason =
        error instanceof Error ? error.message : "Selected open loop could not be loaded.";
    }
  }

  let revisions = selectedMemory ? getFixtureMemoryRevisions(selectedMemory.id) : [];
  let revisionSummary: MemoryRevisionReviewListSummary | null = selectedMemory
    ? getFixtureMemoryRevisionSummary(selectedMemory.id)
    : null;
  let revisionSource: ApiSource | "unavailable" | null = selectedMemory ? "fixture" : null;
  let revisionUnavailableReason: string | undefined;

  if (selectedMemory && liveModeReady && selectedMemorySource === "live") {
    try {
      const payload = await getMemoryRevisions(apiConfig.apiBaseUrl, selectedMemory.id, apiConfig.userId);
      revisions = payload.items;
      revisionSummary = payload.summary;
      revisionSource = "live";
    } catch (error) {
      const fixtureRevisions = getFixtureMemoryRevisions(selectedMemory.id);
      if (fixtureRevisions.length > 0) {
        revisions = fixtureRevisions;
        revisionSummary = getFixtureMemoryRevisionSummary(selectedMemory.id);
        revisionSource = "fixture";
      } else {
        revisions = [];
        revisionSummary = null;
        revisionSource = "unavailable";
      }
      revisionUnavailableReason =
        error instanceof Error ? error.message : "Revision history could not be loaded.";
    }
  }

  let labels = selectedMemory ? getFixtureMemoryLabels(selectedMemory.id) : [];
  let labelSummary: MemoryReviewLabelSummary | null = selectedMemory
    ? getFixtureMemoryLabelSummary(selectedMemory.id)
    : null;
  let labelSource: ApiSource | "unavailable" | null = selectedMemory ? "fixture" : null;
  let labelUnavailableReason: string | undefined;

  if (selectedMemory && liveModeReady && selectedMemorySource === "live") {
    try {
      const payload = await listMemoryLabels(apiConfig.apiBaseUrl, selectedMemory.id, apiConfig.userId);
      labels = payload.items;
      labelSummary = payload.summary;
      labelSource = "live";
    } catch (error) {
      const fixtureLabels = memoryLabelFixtures[selectedMemory.id];
      if (fixtureLabels) {
        labels = fixtureLabels;
        labelSummary = getFixtureMemoryLabelSummary(selectedMemory.id);
        labelSource = "fixture";
      } else {
        labels = [];
        labelSummary = getFixtureMemoryLabelSummary(selectedMemory.id);
        labelSource = "unavailable";
      }
      labelUnavailableReason =
        error instanceof Error ? error.message : "Memory labels could not be loaded.";
    }
  }

  const pageMode = combinePageModes(
    memoryListSource,
    reviewQueueSource,
    evaluationSummarySource,
    openLoopSource,
    selectedMemorySource,
    selectedOpenLoopSource,
    revisionSource === "unavailable" ? null : revisionSource,
    labelSource === "unavailable" ? null : labelSource,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Memories"
        title="Memory review workspace"
        description="Review memory evaluation posture first, inspect one selected memory second, and apply labels only after value and revisions are clear."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(pageMode)}</span>
            <span className="subtle-chip">
              {activeFilter === "queue" ? "Queue filter active" : "Active list filter"}
            </span>
            {activeFilter === "queue" ? (
              <span className="subtle-chip">Priority: {queuePriorityMode}</span>
            ) : null}
            <span className="subtle-chip">{visibleMemories.length} visible memories</span>
            <span className="subtle-chip">{openLoops.length} open loops</span>
          </div>
        }
      />

      <MemorySummary
        summary={evaluationSummary}
        summarySource={evaluationSummarySource}
        summaryUnavailableReason={evaluationSummaryUnavailableReason}
        queueSummary={reviewQueueSummary}
        queueSource={reviewQueueSource}
        queueUnavailableReason={reviewQueueUnavailableReason}
        activeFilter={activeFilter}
      />

      <div className="section-card">
        <header className="section-card__header">
          <div>
            <p className="section-card__eyebrow">Open-loop backbone</p>
            <h2 className="section-card__title">Unresolved commitment review</h2>
          </div>
          <p className="section-card__description">
            Review unresolved loops with deterministic ordering and inspect one selected loop in detail.
          </p>
        </header>

        <div className="stack">
          <p className="muted-copy">
            Source: {openLoopSource === "live" ? "Live list" : "Fixture list"}
            {openLoopUnavailableReason ? ` · ${openLoopUnavailableReason}` : ""}
          </p>
          <p className="muted-copy">
            {openLoopSummary.returned_count} open loops shown of {openLoopSummary.total_count} total
          </p>
          {openLoops.length ? (
            <ul className="stack">
              {openLoops.map((openLoop) => {
                const selected = selectedOpenLoop?.id === openLoop.id;
                const hrefParts = [
                  `/memories?open_loop=${encodeURIComponent(openLoop.id)}`,
                  selectedMemory?.id
                    ? `memory=${encodeURIComponent(selectedMemory.id)}`
                    : null,
                  activeFilter === "queue" ? "filter=queue" : null,
                  activeFilter === "queue"
                    ? `priority_mode=${encodeURIComponent(queuePriorityMode)}`
                    : null,
                ].filter(Boolean);
                const href = hrefParts.length > 1 ? `${hrefParts[0]}&${hrefParts.slice(1).join("&")}` : hrefParts[0];
                return (
                  <li key={openLoop.id}>
                    <a href={href} aria-current={selected ? "page" : undefined}>
                      {openLoop.title}
                    </a>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="muted-copy">No open loops are currently available.</p>
          )}

          {selectedOpenLoop ? (
            <dl className="key-value-grid key-value-grid--compact">
              <div>
                <dt>Status</dt>
                <dd>{selectedOpenLoop.status}</dd>
              </div>
              <div>
                <dt>Memory link</dt>
                <dd className="mono">{selectedOpenLoop.memory_id ?? "Not linked"}</dd>
              </div>
              <div>
                <dt>Opened at</dt>
                <dd className="mono">{formatTypedTimestamp(selectedOpenLoop.opened_at)}</dd>
              </div>
              <div>
                <dt>Due at</dt>
                <dd className="mono">{formatTypedTimestamp(selectedOpenLoop.due_at)}</dd>
              </div>
              <div>
                <dt>Resolved at</dt>
                <dd className="mono">{formatTypedTimestamp(selectedOpenLoop.resolved_at)}</dd>
              </div>
              <div>
                <dt>Resolution note</dt>
                <dd>{selectedOpenLoop.resolution_note ?? "Not set"}</dd>
              </div>
            </dl>
          ) : (
            <p className="muted-copy">
              {selectedOpenLoopUnavailableReason ?? "Select an open loop to inspect its detail fields."}
            </p>
          )}
        </div>
      </div>

      <div className="memory-layout">
        <MemoryList
          memories={visibleMemories}
          selectedMemoryId={selectedMemory?.id}
          summary={activeFilter === "queue" ? null : memoryListSummary}
          source={selectedListSource}
          filter={activeFilter}
          priorityMode={activeFilter === "queue" ? queuePriorityMode : undefined}
          availablePriorityModes={
            activeFilter === "queue" ? reviewQueueSummary.available_priority_modes : undefined
          }
          unavailableReason={activeFilter === "queue" ? reviewQueueUnavailableReason : memoryListUnavailableReason}
        />
        <MemoryDetail
          memory={selectedMemory}
          source={selectedMemorySource}
          unavailableReason={selectedMemoryUnavailableReason}
        />
      </div>

      <div className="section-card">
        <header className="section-card__header">
          <div>
            <p className="section-card__eyebrow">Typed metadata</p>
            <h2 className="section-card__title">Memory classification and confidence</h2>
          </div>
          <p className="section-card__description">
            Typed metadata remains visible in the review workspace with explicit safe fallbacks.
          </p>
        </header>
        {selectedMemory ? (
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Type</dt>
              <dd>{formatTypedValue(selectedMemory.memory_type)}</dd>
            </div>
            <div>
              <dt>Confirmation</dt>
              <dd>{formatTypedValue(selectedMemory.confirmation_status)}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{formatTypedScore(selectedMemory.confidence)}</dd>
            </div>
            <div>
              <dt>Salience</dt>
              <dd>{formatTypedScore(selectedMemory.salience)}</dd>
            </div>
            <div>
              <dt>Valid from</dt>
              <dd className="mono">{formatTypedTimestamp(selectedMemory.valid_from)}</dd>
            </div>
            <div>
              <dt>Valid to</dt>
              <dd className="mono">{formatTypedTimestamp(selectedMemory.valid_to)}</dd>
            </div>
            <div>
              <dt>Last confirmed</dt>
              <dd className="mono">{formatTypedTimestamp(selectedMemory.last_confirmed_at)}</dd>
            </div>
          </dl>
        ) : (
          <p className="muted-copy">Select a memory to inspect typed metadata fields.</p>
        )}
      </div>

      <div className="memory-followup-grid">
        <MemoryRevisionList
          memoryId={selectedMemory?.id ?? null}
          revisions={revisions}
          summary={revisionSummary}
          source={revisionSource}
          unavailableReason={revisionUnavailableReason}
        />

        <div className="stack">
          <MemoryLabelList
            memoryId={selectedMemory?.id ?? null}
            labels={labels}
            summary={labelSummary}
            source={labelSource}
            unavailableReason={labelUnavailableReason}
          />
          <MemoryLabelForm
            memoryId={selectedMemory?.id ?? null}
            source={selectedMemorySource}
            apiBaseUrl={apiConfig.apiBaseUrl}
            userId={apiConfig.userId}
            activeFilter={activeFilter}
            nextQueueMemoryId={nextQueueMemoryId}
            queuePriorityMode={activeFilter === "queue" ? queuePriorityMode : undefined}
          />
        </div>
      </div>
    </div>
  );
}
