import type { TaskArtifactRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ArtifactWorkspaceSummaryProps = {
  artifact: TaskArtifactRecord | null;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ArtifactWorkspaceSummary({ artifact }: ArtifactWorkspaceSummaryProps) {
  if (!artifact) {
    return (
      <SectionCard
        eyebrow="Artifact storage"
        title="No artifact selected"
        description="Select one artifact to inspect its persisted storage identity."
      >
        <EmptyState
          title="Storage summary is idle"
          description="Choose one artifact from the list to review its immutable identifiers and relative path."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Artifact storage"
      title="Persisted identity"
      description="Review the artifact's durable identifiers and workspace-relative path without calling the legacy task-workspace API."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={artifact.status} />
          <StatusBadge status={artifact.ingestion_status} />
        </div>

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Artifact ID</dt>
            <dd className="mono">{artifact.id}</dd>
          </div>
          <div>
            <dt>Storage scope ID</dt>
            <dd className="mono">{artifact.task_workspace_id}</dd>
          </div>
          <div>
            <dt>Relative path</dt>
            <dd className="mono">{artifact.relative_path}</dd>
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
      </div>
    </SectionCard>
  );
}
