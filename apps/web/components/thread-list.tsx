import Link from "next/link";

import { DEFAULT_AGENT_PROFILE_ID, type AgentProfileItem, type ThreadItem } from "../lib/api";
import type { ChatMode } from "./mode-toggle";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";

type ThreadListProps = {
  threads: ThreadItem[];
  selectedThreadId?: string;
  currentMode: ChatMode;
  agentProfiles?: AgentProfileItem[];
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

function buildThreadHref(mode: ChatMode, threadId: string) {
  const params = new URLSearchParams();

  if (mode === "request") {
    params.set("mode", mode);
  }
  params.set("thread", threadId);

  return `/chat?${params.toString()}`;
}

function resolveAgentProfileName(
  agentProfileId: string,
  profiles: AgentProfileItem[],
) {
  return profiles.find((profile) => profile.id === agentProfileId)?.name ?? agentProfileId;
}

export function ThreadList({
  threads,
  selectedThreadId,
  currentMode,
  agentProfiles = [],
  source,
  unavailableReason,
}: ThreadListProps) {
  const description =
    source === "live"
      ? "Visible threads stay explicit and bounded so the operator can anchor work to one continuity record at a time."
      : source === "fixture"
        ? "Fixture preview keeps the selection surface readable when live continuity configuration is absent."
        : "Thread review is temporarily unavailable even though the chat shell is still reachable.";

  return (
    <SectionCard
      eyebrow="Visible threads"
      title="Select a thread"
      description={description}
    >
      {source === "unavailable" ? (
        <EmptyState
          title="Thread continuity unavailable"
          description={unavailableReason ?? "The thread list could not be loaded from the continuity API."}
        />
      ) : threads.length === 0 ? (
        <EmptyState
          title="No threads yet"
          description="Create a thread first so assistant replies and governed requests stay attached to a visible continuity record."
        />
      ) : (
        <div className="history-list history-list--scrollable">
          {threads.map((thread) => {
            const isSelected = thread.id === selectedThreadId;
            const agentProfileId = thread.agent_profile_id || DEFAULT_AGENT_PROFILE_ID;
            const agentProfileName = resolveAgentProfileName(agentProfileId, agentProfiles);

            return (
              <Link
                key={thread.id}
                href={buildThreadHref(currentMode, thread.id)}
                className={["list-row", isSelected ? "is-selected" : ""].filter(Boolean).join(" ")}
                aria-current={isSelected ? "page" : undefined}
              >
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{isSelected ? "Selected thread" : "Thread"}</span>
                    <h3 className="list-row__title">{thread.title}</h3>
                  </div>
                  <span className="subtle-chip">{formatDate(thread.updated_at)}</span>
                </div>

                <div className="list-row__meta">
                  <span className="meta-pill">Updated {formatDate(thread.updated_at)}</span>
                  <span className="meta-pill">Profile {agentProfileName}</span>
                  <span className="meta-pill mono">{thread.id}</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}
