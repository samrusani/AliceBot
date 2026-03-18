import Link from "next/link";

import type { ApiSource, TaskArtifactListSummary, TaskArtifactRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ArtifactListProps = {
  artifacts: TaskArtifactRecord[];
  selectedArtifactId?: string;
  summary: TaskArtifactListSummary | null;
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

function artifactHref(taskArtifactId: string) {
  return `/artifacts?artifact=${encodeURIComponent(taskArtifactId)}`;
}

export function ArtifactList({
  artifacts,
  selectedArtifactId,
  summary,
  source,
  unavailableReason,
}: ArtifactListProps) {
  if (artifacts.length === 0) {
    return (
      <SectionCard
        eyebrow="Artifact list"
        title="No artifacts available"
        description="No task artifacts are currently available in this bounded review workspace."
      >
        <EmptyState
          title="No persisted artifacts"
          description="Artifacts will appear here once task workspaces register and persist reviewable files."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Artifact list"
      title="Persisted task artifacts"
      description="Select one artifact to inspect detail, linked workspace context, and ordered chunk evidence."
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
          {artifacts.map((artifact) => (
            <Link
              key={artifact.id}
              href={artifactHref(artifact.id)}
              className={`list-row${artifact.id === selectedArtifactId ? " is-selected" : ""}`}
              aria-current={artifact.id === selectedArtifactId ? "page" : undefined}
            >
              <div className="list-row__topline">
                <div className="detail-stack">
                  <span className="list-row__eyebrow">{formatDate(artifact.updated_at)}</span>
                  <h3 className="list-row__title">{artifact.relative_path}</h3>
                </div>
                <StatusBadge status={artifact.ingestion_status} />
              </div>

              <div className="list-row__meta">
                <span className="meta-pill mono">{artifact.id}</span>
                <span className="meta-pill">Task {artifact.task_id}</span>
                <span className="meta-pill">Workspace {artifact.task_workspace_id}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
