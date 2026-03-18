import Link from "next/link";

import type { ApiSource, MemoryReviewListSummary, MemoryReviewRecord } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type MemoryListProps = {
  memories: MemoryReviewRecord[];
  selectedMemoryId?: string;
  summary: MemoryReviewListSummary | null;
  source: ApiSource | "unavailable";
  filter: "active" | "queue";
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

function previewValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  const stringified = JSON.stringify(value);
  if (!stringified) {
    return "No value";
  }

  return stringified.length > 120 ? `${stringified.slice(0, 117)}...` : stringified;
}

function memoryHref(memoryId: string, filter: "active" | "queue") {
  if (filter === "queue") {
    return `/memories?filter=queue&memory=${encodeURIComponent(memoryId)}`;
  }

  return `/memories?memory=${encodeURIComponent(memoryId)}`;
}

export function MemoryList({
  memories,
  selectedMemoryId,
  summary,
  source,
  filter,
  unavailableReason,
}: MemoryListProps) {
  if (memories.length === 0) {
    return (
      <SectionCard
        eyebrow="Memory list"
        title="No memories available"
        description="The active memory list is empty for the current filter state."
      >
        <EmptyState
          title={filter === "queue" ? "Review queue is clear" : "No active memories"}
          description={
            filter === "queue"
              ? "No unlabeled active memories need review right now."
              : "Memory records will appear here once admissions are persisted."
          }
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Memory list"
      title={filter === "queue" ? "Unlabeled review queue" : "Active memory records"}
      description="Select one memory to inspect detail, revision history, and review labels without leaving the workspace."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <div className="cluster">
            <StatusBadge status={source} label={source === "live" ? "Live list" : source === "fixture" ? "Fixture list" : "List unavailable"} />
            {summary ? <span className="meta-pill">{summary.total_count} total</span> : null}
            {summary?.has_more ? <span className="meta-pill">More available</span> : null}
          </div>
        </div>

        {unavailableReason ? (
          <p className="responsive-note">Live list read failed: {unavailableReason}</p>
        ) : null}

        <div className="list-rows">
          {memories.map((memory) => (
            <Link
              key={memory.id}
              href={memoryHref(memory.id, filter)}
              className={`list-row${memory.id === selectedMemoryId ? " is-selected" : ""}`}
              aria-current={memory.id === selectedMemoryId ? "page" : undefined}
            >
              <div className="list-row__topline">
                <div className="detail-stack">
                  <span className="list-row__eyebrow">{formatDate(memory.updated_at)}</span>
                  <h3 className="list-row__title mono">{memory.memory_key}</h3>
                </div>
                <StatusBadge status={memory.status} />
              </div>

              <p>{previewValue(memory.value)}</p>

              <div className="list-row__meta">
                <span className="meta-pill mono">{memory.id}</span>
                <span className="meta-pill">{memory.source_event_ids.length} source events</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
