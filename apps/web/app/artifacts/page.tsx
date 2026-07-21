import { ArtifactChunkList } from "../../components/artifact-chunk-list";
import { ArtifactDetail } from "../../components/artifact-detail";
import { ArtifactList } from "../../components/artifact-list";
import { ArtifactWorkspaceSummary } from "../../components/artifact-workspace-summary";
import { PageHeader } from "../../components/page-header";
import type { ApiSource, TaskArtifactRecord } from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getTaskArtifactDetail,
  hasLiveApiConfig,
  listTaskArtifactChunks,
  listTaskArtifacts,
  pageModeLabel,
} from "../../lib/api";
import {
  getFixtureTaskArtifact,
  getFixtureTaskArtifactChunkSummary,
  getFixtureTaskArtifactChunks,
  taskArtifactFixtures,
  taskArtifactListSummaryFixture,
} from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }

  return value?.trim() ?? "";
}

function resolveSelectedArtifactId(requestedArtifactId: string, items: TaskArtifactRecord[]) {
  if (!items.length) {
    return "";
  }

  const availableIds = new Set(items.map((item) => item.id));
  if (requestedArtifactId && availableIds.has(requestedArtifactId)) {
    return requestedArtifactId;
  }

  return items[0]?.id ?? "";
}

export default async function ArtifactsPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const requestedArtifactId = normalizeParam(params.artifact);
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let artifacts = taskArtifactFixtures;
  let artifactListSummary = taskArtifactListSummaryFixture;
  let artifactListSource: ApiSource = "fixture";
  let artifactListUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await listTaskArtifacts(apiConfig.apiBaseUrl, apiConfig.userId);
      artifacts = payload.items;
      artifactListSummary = payload.summary;
      artifactListSource = "live";
    } catch (error) {
      artifactListUnavailableReason =
        error instanceof Error ? error.message : "Task artifact list could not be loaded.";
    }
  }

  const selectedArtifactId = resolveSelectedArtifactId(requestedArtifactId, artifacts);
  const selectedFromList = artifacts.find((item) => item.id === selectedArtifactId) ?? null;

  let selectedArtifact = selectedFromList;
  let selectedArtifactSource: ApiSource | "unavailable" | null = selectedArtifact
    ? artifactListSource
    : null;
  let selectedArtifactUnavailableReason: string | undefined;

  if (selectedFromList && liveModeReady && artifactListSource === "live") {
    try {
      const payload = await getTaskArtifactDetail(apiConfig.apiBaseUrl, selectedFromList.id, apiConfig.userId);
      selectedArtifact = payload.artifact;
      selectedArtifactSource = "live";
    } catch (error) {
      const fixtureArtifact = getFixtureTaskArtifact(selectedFromList.id);
      if (fixtureArtifact) {
        selectedArtifact = fixtureArtifact;
        selectedArtifactSource = "fixture";
      } else {
        selectedArtifactSource = "unavailable";
      }
      selectedArtifactUnavailableReason =
        error instanceof Error ? error.message : "Selected artifact detail could not be loaded.";
    }
  }

  let chunks = selectedArtifact ? getFixtureTaskArtifactChunks(selectedArtifact.id) : [];
  let chunkSummary = selectedArtifact ? getFixtureTaskArtifactChunkSummary(selectedArtifact.id) : null;
  let chunkSource: ApiSource | "unavailable" | null = selectedArtifact
    ? selectedArtifactSource === "unavailable"
      ? "unavailable"
      : "fixture"
    : null;
  if (chunkSource === "unavailable") {
    chunks = [];
    chunkSummary = null;
  }
  let chunkUnavailableReason: string | undefined;

  if (selectedArtifact && liveModeReady && selectedArtifactSource === "live") {
    try {
      const chunkResult = await listTaskArtifactChunks(
        apiConfig.apiBaseUrl,
        selectedArtifact.id,
        apiConfig.userId,
      );
      chunks = chunkResult.items;
      chunkSummary = chunkResult.summary;
      chunkSource = "live";
    } catch (error) {
      const fixtureArtifact = getFixtureTaskArtifact(selectedArtifact.id);
      if (fixtureArtifact) {
        chunks = getFixtureTaskArtifactChunks(selectedArtifact.id);
        chunkSummary = getFixtureTaskArtifactChunkSummary(selectedArtifact.id);
        chunkSource = "fixture";
      } else {
        chunks = [];
        chunkSummary = null;
        chunkSource = "unavailable";
      }
      chunkUnavailableReason =
        error instanceof Error
          ? error.message
          : "Artifact chunk rows could not be loaded.";
    }
  }

  const pageMode = combinePageModes(
    artifactListSource,
    selectedArtifactSource === "unavailable" ? null : selectedArtifactSource,
    chunkSource === "unavailable" ? null : chunkSource,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Artifacts"
        title="Artifact review workspace"
        description="Inspect persisted artifacts in a bounded sequence: list first, selected detail second, then storage identity and ordered chunk evidence."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(pageMode)}</span>
            <span className="subtle-chip">{artifacts.length} visible artifacts</span>
            {selectedArtifact ? <span className="subtle-chip">Selected: {selectedArtifact.relative_path}</span> : null}
          </div>
        }
      />

      <div className="artifact-layout">
        <ArtifactList
          artifacts={artifacts}
          selectedArtifactId={selectedArtifact?.id}
          summary={artifactListSummary}
          source={artifactListSource}
          unavailableReason={artifactListUnavailableReason}
        />
        <ArtifactDetail
          artifact={selectedArtifact}
          source={selectedArtifactSource}
          unavailableReason={selectedArtifactUnavailableReason}
        />
      </div>

      <div className="artifact-review-grid">
        <ArtifactWorkspaceSummary
          artifact={selectedArtifact}
        />
        <ArtifactChunkList
          artifactId={selectedArtifact?.id ?? null}
          chunks={chunks}
          summary={chunkSummary}
          source={chunkSource}
          unavailableReason={chunkUnavailableReason}
        />
      </div>
    </div>
  );
}
