import type { ApiSource, EntityRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type EntityDetailProps = {
  entity: EntityRecord | null;
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

export function EntityDetail({ entity, source, unavailableReason }: EntityDetailProps) {
  if (!entity) {
    return (
      <SectionCard
        eyebrow="Selected entity"
        title="No entity selected"
        description="Choose one entity from the list to review type, provenance memories, and timestamps."
      >
        <EmptyState
          title="Entity inspector is idle"
          description="Select one tracked entity to open the bounded review detail panel."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Selected entity"
      title={entity.name}
      description="Entity detail keeps identity, source-memory context, and timestamps explicit before edge review."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={entity.entity_type} />
          <StatusBadge
            status={source ?? "unavailable"}
            label={
              source === "live"
                ? "Live detail"
                : source === "fixture"
                  ? "Fixture detail"
                  : "Detail unavailable"
            }
          />
        </div>

        {unavailableReason ? (
          <div className="execution-summary__note execution-summary__note--danger">
            <p className="execution-summary__label">Detail read</p>
            <p>{unavailableReason}</p>
          </div>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Entity ID</dt>
            <dd className="mono">{entity.id}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDate(entity.created_at)}</dd>
          </div>
          <div>
            <dt>Entity type</dt>
            <dd>{entity.entity_type}</dd>
          </div>
          <div>
            <dt>Source memories</dt>
            <dd>{entity.source_memory_ids.length}</dd>
          </div>
        </dl>

        <div className="detail-group detail-group--muted">
          <h3>Source memory references</h3>
          {entity.source_memory_ids.length === 0 ? (
            <p className="muted-copy">No source-memory references were returned for this entity.</p>
          ) : (
            <div className="attribute-list">
              {entity.source_memory_ids.map((memoryId) => (
                <span key={memoryId} className="attribute-item mono">
                  {memoryId}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
