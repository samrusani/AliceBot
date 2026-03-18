import type { ApiSource, EntityEdgeListSummary, EntityEdgeRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type EntityEdgeListProps = {
  entityId: string | null;
  edges: EntityEdgeRecord[];
  summary: EntityEdgeListSummary | null;
  source: ApiSource | "unavailable" | null;
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

function formatRange(validFrom: string | null, validTo: string | null) {
  if (!validFrom && !validTo) {
    return "Open range";
  }

  const from = validFrom ? formatDate(validFrom) : "Unbounded start";
  const to = validTo ? formatDate(validTo) : "Open-ended";
  return `${from} to ${to}`;
}

export function EntityEdgeList({
  entityId,
  edges,
  summary,
  source,
  unavailableReason,
}: EntityEdgeListProps) {
  if (!entityId) {
    return (
      <SectionCard
        eyebrow="Related edges"
        title="No entity selected"
        description="Select one entity to inspect ordered relationship edges and source-memory context."
      >
        <EmptyState
          title="Edge review is idle"
          description="Choose one tracked entity from the list to open relationship review."
        />
      </SectionCard>
    );
  }

  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Related edges"
        title="Edge review unavailable"
        description="The selected entity loaded, but related edges could not be read from live or fixture sources."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="Edges unavailable" />
          {unavailableReason ? (
            <div className="execution-summary__note execution-summary__note--danger">
              <p className="execution-summary__label">Edge read</p>
              <p>{unavailableReason}</p>
            </div>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  if (edges.length === 0) {
    return (
      <SectionCard
        eyebrow="Related edges"
        title="No related edges"
        description="No relationship edges are currently linked to the selected entity."
      >
        <EmptyState
          title="Edge list is empty"
          description="Relationship records will appear here once entity edges are persisted."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Related edges"
      title="Ordered relationship review"
      description="Review each edge in order with explicit direction, validity window, and source-memory references."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <div className="cluster">
            <StatusBadge
              status={source ?? "unavailable"}
              label={
                source === "live"
                  ? "Live edges"
                  : source === "fixture"
                    ? "Fixture edges"
                    : "Edges unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} total</span> : null}
          </div>
        </div>

        {unavailableReason ? <p className="responsive-note">Live edge read failed: {unavailableReason}</p> : null}

        <div className="list-rows">
          {edges.map((edge) => (
            <article key={edge.id} className="list-row" aria-label={`${edge.relationship_type} edge`}>
              <div className="list-row__topline">
                <h3 className="list-row__title mono">{edge.relationship_type}</h3>
                <StatusBadge status="info" label="Edge" />
              </div>

              <p className="mono">
                {edge.from_entity_id} to {edge.to_entity_id}
              </p>

              <div className="list-row__meta">
                <span className="meta-pill">Created {formatDate(edge.created_at)}</span>
                <span className="meta-pill">{formatRange(edge.valid_from, edge.valid_to)}</span>
                <span className="meta-pill mono">{edge.id}</span>
              </div>

              <div className="detail-group detail-group--muted">
                <h3>Source memories</h3>
                {edge.source_memory_ids.length === 0 ? (
                  <p className="muted-copy">No source-memory references were returned for this edge.</p>
                ) : (
                  <div className="attribute-list">
                    {edge.source_memory_ids.map((memoryId) => (
                      <span key={memoryId} className="attribute-item mono">
                        {memoryId}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
