import type { ApiSource, TaskArtifactRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ArtifactDetailProps = {
  artifact: TaskArtifactRecord | null;
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

export function ArtifactDetail({ artifact, source, unavailableReason }: ArtifactDetailProps) {
  if (!artifact) {
    return (
      <SectionCard
        eyebrow="Selected artifact"
        title="No artifact selected"
        description="Select one artifact from the list to inspect metadata, ingestion status, and rooted path context."
      >
        <EmptyState
          title="Artifact inspector is idle"
          description="Choose one artifact from the bounded list to review detail."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Selected artifact"
      title={artifact.relative_path}
      description="Artifact detail keeps registration metadata and ingestion status explicit before workspace and chunk review."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={artifact.status} />
          <StatusBadge status={artifact.ingestion_status} />
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
            <dt>Artifact ID</dt>
            <dd className="mono">{artifact.id}</dd>
          </div>
          <div>
            <dt>Task ID</dt>
            <dd className="mono">{artifact.task_id}</dd>
          </div>
          <div>
            <dt>Workspace ID</dt>
            <dd className="mono">{artifact.task_workspace_id}</dd>
          </div>
          <div>
            <dt>Media type hint</dt>
            <dd>{artifact.media_type_hint ?? "None"}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDate(artifact.created_at)}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDate(artifact.updated_at)}</dd>
          </div>
        </dl>

        <div className="detail-group detail-group--muted">
          <h3>Rooted path summary</h3>
          <p className="mono">{artifact.relative_path}</p>
          <p className="muted-copy">
            This path is stored as a workspace-rooted relative path and remains read-only inside this review route.
          </p>
        </div>
      </div>
    </SectionCard>
  );
}
