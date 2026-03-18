import type { ApiSource, TaskArtifactChunkListSummary, TaskArtifactChunkRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ArtifactChunkListProps = {
  artifactId: string | null;
  chunks: TaskArtifactChunkRecord[];
  summary: TaskArtifactChunkListSummary | null;
  source: ApiSource | "unavailable" | null;
  unavailableReason?: string;
};

function chunkLength(chunk: TaskArtifactChunkRecord) {
  return Math.max(0, chunk.char_end_exclusive - chunk.char_start);
}

export function ArtifactChunkList({
  artifactId,
  chunks,
  summary,
  source,
  unavailableReason,
}: ArtifactChunkListProps) {
  if (!artifactId) {
    return (
      <SectionCard
        eyebrow="Chunk review"
        title="No artifact selected"
        description="Select one artifact to inspect ordered persisted chunks and evidence text."
      >
        <EmptyState
          title="Chunk review is idle"
          description="Choose one artifact from the list to inspect ordered chunk rows."
        />
      </SectionCard>
    );
  }

  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Chunk review"
        title="Chunk review unavailable"
        description="The selected artifact loaded, but chunk rows are currently unavailable."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="Chunks unavailable" />
          {unavailableReason ? (
            <div className="execution-summary__note execution-summary__note--danger">
              <p className="execution-summary__label">Chunk read</p>
              <p>{unavailableReason}</p>
            </div>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  if (chunks.length === 0) {
    return (
      <SectionCard
        eyebrow="Chunk review"
        title="No persisted chunks"
        description="The selected artifact has no persisted chunk rows yet."
      >
        <EmptyState
          title="Chunk list is empty"
          description="Chunk rows will appear here after artifact ingestion persists chunked evidence."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Chunk review"
      title="Ordered persisted chunks"
      description="Read chunk rows in stored order with explicit character ranges and bounded evidence text."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <div className="cluster">
            <StatusBadge
              status={source ?? "unavailable"}
              label={
                source === "live"
                  ? "Live chunks"
                  : source === "fixture"
                    ? "Fixture chunks"
                    : "Chunks unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} total</span> : null}
            {summary ? <span className="meta-pill">{summary.total_characters} chars</span> : null}
            {summary ? <span className="meta-pill">{summary.media_type}</span> : null}
          </div>
        </div>

        {unavailableReason ? <p className="responsive-note">Live chunk read failed: {unavailableReason}</p> : null}

        <div className="list-rows">
          {chunks.map((chunk) => (
            <article key={chunk.id} className="list-row" aria-label={`Chunk ${chunk.sequence_no}`}>
              <div className="list-row__topline">
                <h3 className="list-row__title">Chunk {chunk.sequence_no}</h3>
                <StatusBadge status="info" label={`${chunkLength(chunk)} chars`} />
              </div>

              <div className="list-row__meta">
                <span className="meta-pill mono">{chunk.id}</span>
                <span className="meta-pill">
                  {chunk.char_start} to {chunk.char_end_exclusive}
                </span>
              </div>

              <pre className="artifact-chunk__text">{chunk.text}</pre>
            </article>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
