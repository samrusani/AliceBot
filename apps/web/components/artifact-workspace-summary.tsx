import type { ApiSource, TaskArtifactRecord, TaskWorkspaceRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ArtifactWorkspaceSummaryProps = {
  artifact: TaskArtifactRecord | null;
  workspace: TaskWorkspaceRecord | null;
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

function formatRootedPath(workspacePath: string, relativePath: string) {
  return `${workspacePath.replace(/\/$/, "")}/${relativePath.replace(/^\//, "")}`;
}

export function ArtifactWorkspaceSummary({
  artifact,
  workspace,
  source,
  unavailableReason,
}: ArtifactWorkspaceSummaryProps) {
  if (!artifact) {
    return (
      <SectionCard
        eyebrow="Linked workspace"
        title="No artifact selected"
        description="Select one artifact to inspect the linked task workspace and rooted path context."
      >
        <EmptyState
          title="Workspace summary is idle"
          description="Choose one artifact from the list to review its linked task workspace."
        />
      </SectionCard>
    );
  }

  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Linked workspace"
        title="Workspace summary unavailable"
        description="The selected artifact loaded, but linked task workspace detail is currently unavailable."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="Workspace unavailable" />
          {unavailableReason ? (
            <div className="execution-summary__note execution-summary__note--danger">
              <p className="execution-summary__label">Workspace read</p>
              <p>{unavailableReason}</p>
            </div>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  if (!workspace) {
    return (
      <SectionCard
        eyebrow="Linked workspace"
        title="No linked workspace"
        description="No task workspace metadata is currently available for the selected artifact."
      >
        <EmptyState
          title="Workspace metadata missing"
          description="Workspace metadata will appear here once the selected artifact has a visible linked workspace."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Linked workspace"
      title="Task workspace summary"
      description="Review the linked task workspace identity and rooted local path before reading chunk evidence."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={workspace.status} />
          <StatusBadge
            status={source ?? "unavailable"}
            label={
              source === "live"
                ? "Live workspace"
                : source === "fixture"
                  ? "Fixture workspace"
                  : "Workspace unavailable"
            }
          />
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live workspace read failed: {unavailableReason}</p>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Workspace ID</dt>
            <dd className="mono">{workspace.id}</dd>
          </div>
          <div>
            <dt>Task ID</dt>
            <dd className="mono">{workspace.task_id}</dd>
          </div>
          <div>
            <dt>Workspace root</dt>
            <dd className="mono">{workspace.local_path}</dd>
          </div>
          <div>
            <dt>Rooted artifact path</dt>
            <dd className="mono">{formatRootedPath(workspace.local_path, artifact.relative_path)}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDate(workspace.created_at)}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDate(workspace.updated_at)}</dd>
          </div>
        </dl>
      </div>
    </SectionCard>
  );
}
