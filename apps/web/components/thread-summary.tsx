import type { ThreadEventItem, ThreadItem, ThreadSessionItem } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ThreadSummaryProps = {
  thread: ThreadItem | null;
  sessions: ThreadSessionItem[];
  events: ThreadEventItem[];
  source: "live" | "fixture" | "unavailable";
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

function formatStatus(status: string | undefined) {
  if (!status) {
    return "No sessions yet";
  }

  return status.replace(/_/g, " ");
}

export function ThreadSummary({
  thread,
  sessions,
  events,
  source,
  unavailableReason,
}: ThreadSummaryProps) {
  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Selected thread"
        title="Continuity summary unavailable"
        description="The thread summary could not be loaded from the continuity API."
      >
        <EmptyState
          title="Summary unavailable"
          description={unavailableReason ?? "Thread metadata and continuity counts are temporarily unavailable."}
        />
      </SectionCard>
    );
  }

  if (!thread) {
    return (
      <SectionCard
        eyebrow="Selected thread"
        title="No thread selected"
        description="Choose a visible thread first so the chat surface stays anchored to a single continuity record."
      >
        <EmptyState
          title="Select a thread"
          description="The assistant and governed request forms stay disabled until one visible thread is selected."
        />
      </SectionCard>
    );
  }

  const latestSession = sessions[sessions.length - 1];

  return (
    <SectionCard
      eyebrow="Selected thread"
      title={thread.title}
      description={
        source === "live"
          ? "Thread identity, lifecycle timing, and bounded continuity counts stay visible before any new message or governed action."
          : "Fixture preview keeps the current thread identity and continuity footprint explicit."
      }
    >
      <div className="thread-summary__topline">
        <StatusBadge
          status={latestSession?.status ?? "info"}
          label={formatStatus(latestSession?.status)}
        />
        <div className="attribute-list">
          <span className="meta-pill">Created {formatDate(thread.created_at)}</span>
          <span className="meta-pill">Updated {formatDate(thread.updated_at)}</span>
        </div>
      </div>

      <dl className="key-value-grid key-value-grid--compact">
        <div>
          <dt>Sessions</dt>
          <dd>{sessions.length}</dd>
        </div>
        <div>
          <dt>Events</dt>
          <dd>{events.length}</dd>
        </div>
        <div>
          <dt>Latest session</dt>
          <dd>{latestSession?.started_at ? formatDate(latestSession.started_at) : "Not started yet"}</dd>
        </div>
        <div>
          <dt>Review mode</dt>
          <dd>{source === "live" ? "Live continuity API" : "Fixture preview"}</dd>
        </div>
      </dl>

      <div className="detail-group">
        <span className="history-entry__label">Thread ID</span>
        <p className="thread-summary__id mono">{thread.id}</p>
      </div>
    </SectionCard>
  );
}
