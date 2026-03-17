import type { ThreadEventItem, ThreadSessionItem } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ThreadEventListProps = {
  threadTitle?: string;
  sessions: ThreadSessionItem[];
  events: ThreadEventItem[];
  source: "live" | "fixture" | "unavailable";
  unavailableReason?: string;
};

const SESSION_LIMIT = 3;
const EVENT_LIMIT = 6;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function summarizePayload(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return "Structured continuity payload available.";
  }

  const record = payload as Record<string, unknown>;

  if (typeof record.text === "string" && record.text.trim()) {
    return record.text;
  }

  if (typeof record.summary === "string" && record.summary.trim()) {
    return record.summary;
  }

  const action = typeof record.action === "string" ? record.action : null;
  const scope = typeof record.scope === "string" ? record.scope : null;
  const status = typeof record.status === "string" ? record.status : null;

  if (action && scope && status) {
    return `${action} in ${scope} is ${status.replace(/_/g, " ")}.`;
  }

  if (action && scope) {
    return `${action} in ${scope}.`;
  }

  if (status) {
    return `Continuity status is ${status.replace(/_/g, " ")}.`;
  }

  return "Structured continuity payload available.";
}

function formatKind(kind: string) {
  return kind.replace(/[._]/g, " ");
}

export function ThreadEventList({
  threadTitle,
  sessions,
  events,
  source,
  unavailableReason,
}: ThreadEventListProps) {
  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Continuity review"
        title="Recent continuity state unavailable"
        description="The continuity review panel could not load the selected thread sessions and events."
      >
        <EmptyState
          title="Review unavailable"
          description={unavailableReason ?? "Try again once the continuity API is reachable."}
        />
      </SectionCard>
    );
  }

  if (!threadTitle) {
    return (
      <SectionCard
        eyebrow="Continuity review"
        title="No continuity state selected"
        description="Pick a visible thread before reviewing its recent sessions and continuity events."
      >
        <EmptyState
          title="Select a thread"
          description="Recent sessions and continuity events appear here after one thread is selected."
        />
      </SectionCard>
    );
  }

  if (sessions.length === 0 && events.length === 0) {
    return (
      <SectionCard
        eyebrow="Continuity review"
        title="Recent continuity state"
        description="This thread exists, but no sessions or continuity events have been recorded yet."
      >
        <EmptyState
          title="No continuity captured yet"
          description="Start the thread in assistant or governed mode and the latest sessions and continuity events will appear here."
        />
      </SectionCard>
    );
  }

  const visibleSessions = sessions.slice(-SESSION_LIMIT).reverse();
  const visibleEvents = events.slice(-EVENT_LIMIT).reverse();

  return (
    <SectionCard
      eyebrow="Continuity review"
      title="Recent continuity state"
      description="The latest sessions and events stay bounded so the operator can review continuity without turning this page into a raw transcript."
    >
      <div className="thread-review-grid">
        <div className="detail-group">
          <div className="detail-summary">
            <span className="detail-summary__label">Recent sessions</span>
            <span className="subtle-chip">{sessions.length} total</span>
          </div>

          <div className="timeline-list">
            {visibleSessions.map((session) => (
              <article key={session.id} className="timeline-item">
                <div className="timeline-item__topline">
                  <div className="detail-stack">
                    <h3 className="list-row__title">{formatDate(session.started_at ?? session.created_at)}</h3>
                    <p>{session.ended_at ? "Session closed cleanly." : "Current live session remains open."}</p>
                  </div>
                  <StatusBadge status={session.status} />
                </div>

                <div className="attribute-list">
                  <span className="meta-pill mono">{session.id}</span>
                  <span className="meta-pill">Started {formatDate(session.started_at ?? session.created_at)}</span>
                  {session.ended_at ? <span className="meta-pill">Ended {formatDate(session.ended_at)}</span> : null}
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="detail-group">
          <div className="detail-summary">
            <span className="detail-summary__label">Latest events</span>
            <span className="subtle-chip">{events.length} total</span>
          </div>

          <div className="timeline-list">
            {visibleEvents.map((event) => (
              <article key={event.id} className="timeline-item">
                <div className="timeline-item__topline">
                  <div className="detail-stack">
                    <span className="history-entry__label">{formatKind(event.kind)}</span>
                    <h3 className="list-row__title">{summarizePayload(event.payload)}</h3>
                  </div>
                  <span className="subtle-chip">{formatDate(event.created_at)}</span>
                </div>

                <div className="attribute-list">
                  <span className="meta-pill">Sequence {event.sequence_no}</span>
                  {event.session_id ? <span className="meta-pill mono">{event.session_id}</span> : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
