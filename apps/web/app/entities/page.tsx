import { EntityDetail } from "../../components/entity-detail";
import { EntityEdgeList } from "../../components/entity-edge-list";
import { EntityList } from "../../components/entity-list";
import { PageHeader } from "../../components/page-header";
import type { ApiSource, EntityRecord } from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getEntityDetail,
  hasLiveApiConfig,
  listEntities,
  listEntityEdges,
  pageModeLabel,
} from "../../lib/api";
import {
  entityFixtures,
  entityListSummaryFixture,
  getFixtureEntity,
  getFixtureEntityEdgeSummary,
  getFixtureEntityEdges,
} from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }

  return value?.trim() ?? "";
}

function resolveSelectedEntityId(requestedEntityId: string, items: EntityRecord[]) {
  if (!items.length) {
    return "";
  }

  const availableIds = new Set(items.map((item) => item.id));
  if (requestedEntityId && availableIds.has(requestedEntityId)) {
    return requestedEntityId;
  }

  return items[0]?.id ?? "";
}

export default async function EntitiesPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const requestedEntityId = normalizeParam(params.entity);
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let entities = entityFixtures;
  let entityListSummary = entityListSummaryFixture;
  let entityListSource: ApiSource = "fixture";
  let entityListUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await listEntities(apiConfig.apiBaseUrl, apiConfig.userId);
      entities = payload.items;
      entityListSummary = payload.summary;
      entityListSource = "live";
    } catch (error) {
      entityListUnavailableReason =
        error instanceof Error ? error.message : "Entity list could not be loaded.";
    }
  }

  const selectedEntityId = resolveSelectedEntityId(requestedEntityId, entities);
  const selectedFromList = entities.find((item) => item.id === selectedEntityId) ?? null;

  let selectedEntity = selectedFromList;
  let selectedEntitySource: ApiSource | null = selectedEntity ? entityListSource : null;
  let selectedEntityUnavailableReason: string | undefined;

  if (selectedFromList && liveModeReady && entityListSource === "live") {
    try {
      const payload = await getEntityDetail(apiConfig.apiBaseUrl, selectedFromList.id, apiConfig.userId);
      selectedEntity = payload.entity;
      selectedEntitySource = "live";
    } catch (error) {
      const fixtureEntity = getFixtureEntity(selectedFromList.id);
      if (fixtureEntity) {
        selectedEntity = fixtureEntity;
        selectedEntitySource = "fixture";
      }
      selectedEntityUnavailableReason =
        error instanceof Error ? error.message : "Selected entity detail could not be loaded.";
    }
  }

  let edges = selectedEntity ? getFixtureEntityEdges(selectedEntity.id) : [];
  let edgeSummary = selectedEntity ? getFixtureEntityEdgeSummary(selectedEntity.id) : null;
  let edgeSource: ApiSource | "unavailable" | null = selectedEntity ? "fixture" : null;
  let edgeUnavailableReason: string | undefined;

  if (selectedEntity && liveModeReady && selectedEntitySource === "live") {
    try {
      const payload = await listEntityEdges(apiConfig.apiBaseUrl, selectedEntity.id, apiConfig.userId);
      edges = payload.items;
      edgeSummary = payload.summary;
      edgeSource = "live";
    } catch (error) {
      const fixtureEdges = getFixtureEntityEdges(selectedEntity.id);
      if (fixtureEdges.length > 0) {
        edges = fixtureEdges;
        edgeSummary = getFixtureEntityEdgeSummary(selectedEntity.id);
        edgeSource = "fixture";
      } else {
        edges = [];
        edgeSummary = null;
        edgeSource = "unavailable";
      }
      edgeUnavailableReason =
        error instanceof Error ? error.message : "Entity edges could not be loaded.";
    }
  }

  const pageMode = combinePageModes(
    entityListSource,
    selectedEntitySource,
    edgeSource === "unavailable" ? null : edgeSource,
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Entities"
        title="Entity review workspace"
        description="Review entities in a bounded sequence: list first, selected detail second, and related edge context third."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(pageMode)}</span>
            <span className="subtle-chip">{entities.length} visible entities</span>
            {selectedEntity ? <span className="subtle-chip">Selected: {selectedEntity.name}</span> : null}
          </div>
        }
      />

      <div className="entity-layout">
        <EntityList
          entities={entities}
          selectedEntityId={selectedEntity?.id}
          summary={entityListSummary}
          source={entityListSource}
          unavailableReason={entityListUnavailableReason}
        />
        <EntityDetail
          entity={selectedEntity}
          source={selectedEntitySource}
          unavailableReason={selectedEntityUnavailableReason}
        />
      </div>

      <EntityEdgeList
        entityId={selectedEntity?.id ?? null}
        edges={edges}
        summary={edgeSummary}
        source={edgeSource}
        unavailableReason={edgeUnavailableReason}
      />
    </div>
  );
}
