import {
  DEFAULT_AGENT_PROFILE_ID,
  type AgentProfileItem,
  type ResumptionBrief,
  type ThreadEventItem,
  type ThreadItem,
  type ThreadSessionItem,
} from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ThreadSummaryProps = {
  thread: ThreadItem | null;
  sessions: ThreadSessionItem[];
  events: ThreadEventItem[];
  agentProfiles?: AgentProfileItem[];
  source: "live" | "fixture" | "unavailable";
  unavailableReason?: string;
  resumptionBrief?: ResumptionBrief | null;
  resumptionSource?: "live" | "fixture" | "unavailable" | null;
  resumptionUnavailableReason?: string;
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

function isConversationEvent(event: ThreadEventItem) {
  return event.kind === "message.user" || event.kind === "message.assistant";
}

function summarizeEvent(event: ThreadEventItem) {
  const payload = event.payload;
  if (payload && typeof payload === "object" && "text" in payload && typeof payload.text === "string") {
    return payload.text;
  }
  return event.kind;
}

function resolveAgentProfileName(agentProfileId: string, profiles: AgentProfileItem[]) {
  return profiles.find((profile) => profile.id === agentProfileId)?.name ?? agentProfileId;
}

export function ThreadSummary({
  thread,
  sessions,
  events,
  agentProfiles = [],
  source,
  unavailableReason,
  resumptionBrief = null,
  resumptionSource = null,
  resumptionUnavailableReason,
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
  const conversationCount = events.filter(isConversationEvent).length;
  const operationalCount = events.length - conversationCount;
  const agentProfileId = thread.agent_profile_id || DEFAULT_AGENT_PROFILE_ID;
  const agentProfileName = resolveAgentProfileName(agentProfileId, agentProfiles);

  return (
    <SectionCard
      eyebrow="Selected thread"
      title={thread.title}
      description={
        source === "live"
          ? "Thread identity and continuity footprint stay explicit while the transcript remains the primary reading surface."
          : "Fixture preview keeps the selected thread identity and continuity footprint explicit."
      }
    >
      <div className="thread-summary__topline">
        <StatusBadge
          status={latestSession?.status ?? "info"}
          label={formatStatus(latestSession?.status)}
        />
        <div className="attribute-list">
          <span className="meta-pill">Profile {agentProfileName}</span>
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
        <div>
          <dt>Agent profile</dt>
          <dd>{agentProfileName}</dd>
        </div>
      </dl>

      <div className="detail-group detail-group--muted">
        <span className="history-entry__label">Continuity breakdown</span>
        <p>
          {conversationCount} conversation entries and {operationalCount} supporting operational
          events are attached to this thread.
        </p>
      </div>

      {resumptionSource === "unavailable" ? (
        <div className="detail-group">
          <span className="history-entry__label">Resumption brief</span>
          <EmptyState
            title="Resumption brief unavailable"
            description={
              resumptionUnavailableReason ??
              "The deterministic resumption brief could not be loaded for this thread."
            }
          />
        </div>
      ) : resumptionBrief ? (
        <div className="detail-group">
          <span className="history-entry__label">Resumption brief</span>
          <p>
            {resumptionSource === "live"
              ? "Live deterministic brief"
              : "Fixture deterministic brief"}{" "}
            from durable continuity seams.
          </p>
          <dl className="key-value-grid key-value-grid--compact">
            <div>
              <dt>Conversation evidence</dt>
              <dd>
                {resumptionBrief.conversation.summary.returned_count}/
                {resumptionBrief.conversation.summary.total_count}
              </dd>
            </div>
            <div>
              <dt>Active open loops</dt>
              <dd>
                {resumptionBrief.open_loops.summary.returned_count}/
                {resumptionBrief.open_loops.summary.total_count}
              </dd>
            </div>
            <div>
              <dt>Memory highlights</dt>
              <dd>
                {resumptionBrief.memory_highlights.summary.returned_count}/
                {resumptionBrief.memory_highlights.summary.total_count}
              </dd>
            </div>
            <div>
              <dt>Workflow posture</dt>
              <dd>{resumptionBrief.workflow ? "Present" : "Not linked"}</dd>
            </div>
          </dl>

          {resumptionBrief.conversation.items.length > 0 ? (
            <div className="detail-group detail-group--muted">
              <span className="history-entry__label">Latest conversation evidence</span>
              <ul className="timeline-list">
                {resumptionBrief.conversation.items.map((item) => (
                  <li key={item.id} className="timeline-item">
                    <p className="mono">#{item.sequence_no} {item.kind}</p>
                    <p>{summarizeEvent(item)}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="muted-copy">No conversation evidence is currently available.</p>
          )}

          {resumptionBrief.open_loops.items.length > 0 ? (
            <div className="detail-group detail-group--muted">
              <span className="history-entry__label">Active open loops</span>
              <ul className="timeline-list">
                {resumptionBrief.open_loops.items.map((item) => (
                  <li key={item.id} className="timeline-item">
                    <p className="mono">{item.title}</p>
                    <p>Status: {item.status}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {resumptionBrief.memory_highlights.items.length > 0 ? (
            <div className="detail-group detail-group--muted">
              <span className="history-entry__label">Memory highlights</span>
              <ul className="timeline-list">
                {resumptionBrief.memory_highlights.items.map((item) => (
                  <li key={item.id} className="timeline-item">
                    <p className="mono">{item.memory_key}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="detail-group">
        <span className="history-entry__label">Thread ID</span>
        <p className="thread-summary__id mono">{thread.id}</p>
      </div>
    </SectionCard>
  );
}
