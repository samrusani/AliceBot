import Link from "next/link";

import type { ApiSource, EntityListSummary, EntityRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type EntityListProps = {
  entities: EntityRecord[];
  selectedEntityId?: string;
  summary: EntityListSummary | null;
  source: ApiSource | "unavailable";
  unavailableReason?: string;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function entityHref(entityId: string) {
  return `/entities?entity=${encodeURIComponent(entityId)}`;
}

export function EntityList({
  entities,
  selectedEntityId,
  summary,
  source,
  unavailableReason,
}: EntityListProps) {
  if (entities.length === 0) {
    return (
      <SectionCard
        eyebrow="Entity list"
        title="No entities available"
        description="The bounded entity list is currently empty for this operator workspace."
      >
        <EmptyState
          title="No tracked entities"
          description="Entities will appear here once entity records are available for review."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Entity list"
      title="Tracked entities"
      description="Select one entity to inspect full provenance and related edges without leaving this route."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <div className="cluster">
            <StatusBadge
              status={source}
              label={
                source === "live"
                  ? "Live list"
                  : source === "fixture"
                    ? "Fixture list"
                    : "List unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} total</span> : null}
          </div>
        </div>

        {unavailableReason ? <p className="responsive-note">Live list read failed: {unavailableReason}</p> : null}

        <div className="list-rows">
          {entities.map((entity) => (
            <Link
              key={entity.id}
              href={entityHref(entity.id)}
              className={`list-row${entity.id === selectedEntityId ? " is-selected" : ""}`}
              aria-current={entity.id === selectedEntityId ? "page" : undefined}
            >
              <div className="list-row__topline">
                <div className="detail-stack">
                  <span className="list-row__eyebrow">{formatDate(entity.created_at)}</span>
                  <h3 className="list-row__title">{entity.name}</h3>
                </div>
                <StatusBadge status={entity.entity_type} />
              </div>

              <div className="list-row__meta">
                <span className="meta-pill mono">{entity.id}</span>
                <span className="meta-pill">{entity.source_memory_ids.length} source memories</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
