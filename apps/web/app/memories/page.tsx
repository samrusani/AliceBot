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
  MemoryReviewRecord,
  MemoryRevisionReviewListSummary,
} from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getMemoryDetail,
  getMemoryEvaluationSummary,
  getMemoryRevisions,
  hasLiveApiConfig,
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
  created_at: string;
  updated_at: string;
}): MemoryReviewRecord {
  return {
    ...item,
    deleted_at: null,
  };
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
  const activeFilter = normalizeFilter(params.filter);
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

  if (liveModeReady) {
    const [memoryResult, queueResult, summaryResult] = await Promise.allSettled([
      listMemories(apiConfig.apiBaseUrl, apiConfig.userId, { status: "active" }),
      listMemoryReviewQueue(apiConfig.apiBaseUrl, apiConfig.userId),
      getMemoryEvaluationSummary(apiConfig.apiBaseUrl, apiConfig.userId),
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
    selectedMemorySource,
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
            <span className="subtle-chip">{visibleMemories.length} visible memories</span>
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

      <div className="memory-layout">
        <MemoryList
          memories={visibleMemories}
          selectedMemoryId={selectedMemory?.id}
          summary={activeFilter === "queue" ? null : memoryListSummary}
          source={selectedListSource}
          filter={activeFilter}
          unavailableReason={activeFilter === "queue" ? reviewQueueUnavailableReason : memoryListUnavailableReason}
        />
        <MemoryDetail
          memory={selectedMemory}
          source={selectedMemorySource}
          unavailableReason={selectedMemoryUnavailableReason}
        />
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
          />
        </div>
      </div>
    </div>
  );
}
