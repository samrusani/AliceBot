import type { ApiSource, MemoryReviewRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type MemoryDetailProps = {
  memory: MemoryReviewRecord | null;
  source: ApiSource | "unavailable" | null;
  unavailableReason?: string;
};

function formatDate(value: string | null) {
  if (!value) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  const stringified = JSON.stringify(value, null, 2);
  return stringified ?? "null";
}

export function MemoryDetail({ memory, source, unavailableReason }: MemoryDetailProps) {
  if (!memory) {
    return (
      <SectionCard
        eyebrow="Selected memory"
        title="No memory selected"
        description="Choose a memory from the list to inspect full value, source-event references, and timestamps."
      >
        <EmptyState
          title="Memory inspector is idle"
          description="Select one active memory record to open the bounded detail panel."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Selected memory"
      title={memory.memory_key}
      description="The detail panel keeps value shape, provenance, and update time legible before revisions or labels are applied."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={memory.status} />
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
            <dt>Memory ID</dt>
            <dd className="mono">{memory.id}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDate(memory.created_at)}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDate(memory.updated_at)}</dd>
          </div>
          <div>
            <dt>Deleted</dt>
            <dd>{formatDate(memory.deleted_at)}</dd>
          </div>
        </dl>

        <div className="detail-group">
          <h3>Memory value</h3>
          <pre className="execution-summary__code">{formatValue(memory.value)}</pre>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Source events</h3>
          {memory.source_event_ids.length === 0 ? (
            <p className="muted-copy">No source-event references were returned for this memory.</p>
          ) : (
            <div className="attribute-list">
              {memory.source_event_ids.map((eventId) => (
                <span key={eventId} className="attribute-item mono">
                  {eventId}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </SectionCard>
  );
}
