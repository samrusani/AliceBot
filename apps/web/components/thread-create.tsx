"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { createThread, DEFAULT_AGENT_PROFILE_ID, type AgentProfileItem } from "../lib/api";
import type { ChatMode } from "./mode-toggle";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ThreadCreateProps = {
  apiBaseUrl?: string;
  userId?: string;
  currentMode: ChatMode;
  agentProfiles?: AgentProfileItem[];
};

function buildThreadHref(mode: ChatMode, threadId: string) {
  const params = new URLSearchParams();

  if (mode === "request") {
    params.set("mode", mode);
  }
  params.set("thread", threadId);

  return `/chat?${params.toString()}`;
}

export function ThreadCreate({
  apiBaseUrl,
  userId,
  currentMode,
  agentProfiles,
}: ThreadCreateProps) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [selectedProfileId, setSelectedProfileId] = useState(DEFAULT_AGENT_PROFILE_ID);
  const [statusText, setStatusText] = useState(
    apiBaseUrl && userId
      ? "Create a new visible thread when the current conversation needs a fresh continuity boundary."
      : "Thread creation becomes available when the live web API base URL and user ID are configured.",
  );
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const liveModeReady = Boolean(apiBaseUrl && userId);
  const profileOptions = agentProfiles && agentProfiles.length > 0
    ? agentProfiles
    : [
        {
          id: DEFAULT_AGENT_PROFILE_ID,
          name: "Assistant Default",
          description: "General-purpose assistant profile for baseline conversations.",
        },
      ];

  useEffect(() => {
    if (profileOptions.some((profile) => profile.id === selectedProfileId)) {
      return;
    }

    const fallbackProfile =
      profileOptions.find((profile) => profile.id === DEFAULT_AGENT_PROFILE_ID) ?? profileOptions[0];
    setSelectedProfileId(fallbackProfile.id);
  }, [profileOptions, selectedProfileId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextTitle = title.trim();

    if (!liveModeReady) {
      setStatusTone("danger");
      setStatusText(
        "Thread creation is unavailable in fixture preview because the continuity create endpoint only persists through the live API.",
      );
      return;
    }

    if (!nextTitle) {
      setStatusTone("danger");
      setStatusText("A short thread title is required.");
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Creating a new continuity thread through the shipped thread-create endpoint...");

    try {
      const response = await createThread(apiBaseUrl!, {
        user_id: userId!,
        title: nextTitle,
        agent_profile_id: selectedProfileId || DEFAULT_AGENT_PROFILE_ID,
      });

      setStatusTone("success");
      setStatusText("Thread created. Loading the new continuity record now.");
      setTitle("");
      router.push(buildThreadHref(currentMode, response.thread.id));
      router.refresh();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed";
      setStatusTone("danger");
      setStatusText(`Unable to create thread: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <SectionCard
      eyebrow="Create thread"
      title="Start a new continuity record"
      description="Keep thread identity explicit instead of recycling one conversation container for unrelated work."
    >
      <form className="detail-stack" onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="thread-agent-profile">Agent profile</label>
          <select
            id="thread-agent-profile"
            name="thread-agent-profile"
            value={selectedProfileId}
            onChange={(event) => setSelectedProfileId(event.target.value)}
            disabled={!liveModeReady || isSubmitting}
          >
            {profileOptions.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label htmlFor="thread-title">Thread title</label>
          <input
            id="thread-title"
            name="thread-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Magnesium reorder review"
            disabled={!liveModeReady || isSubmitting}
          />
        </div>

        <div className="composer-actions">
          <div className="composer-status" aria-live="polite">
            <StatusBadge
              status={
                isSubmitting
                  ? "submitting"
                  : statusTone === "success"
                    ? "success"
                    : statusTone === "danger"
                      ? "error"
                      : "info"
              }
              label={
                isSubmitting
                  ? "Creating"
                  : statusTone === "success"
                    ? "Ready"
                    : statusTone === "danger"
                      ? "Attention"
                      : "Prepared"
              }
            />
            <span>{statusText}</span>
          </div>
          <button
            type="submit"
            className="button"
            disabled={isSubmitting || !liveModeReady || !title.trim()}
          >
            {isSubmitting ? "Creating..." : "Create thread"}
          </button>
        </div>
      </form>
    </SectionCard>
  );
}
