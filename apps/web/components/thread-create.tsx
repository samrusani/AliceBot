"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { createThread } from "../lib/api";
import type { ChatMode } from "./mode-toggle";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ThreadCreateProps = {
  apiBaseUrl?: string;
  userId?: string;
  currentMode: ChatMode;
};

function buildThreadHref(mode: ChatMode, threadId: string) {
  const params = new URLSearchParams();

  if (mode === "request") {
    params.set("mode", mode);
  }
  params.set("thread", threadId);

  return `/chat?${params.toString()}`;
}

export function ThreadCreate({ apiBaseUrl, userId, currentMode }: ThreadCreateProps) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [statusText, setStatusText] = useState(
    apiBaseUrl && userId
      ? "Create a new visible thread when the current conversation needs a fresh continuity boundary."
      : "Thread creation becomes available when the live web API base URL and user ID are configured.",
  );
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const liveModeReady = Boolean(apiBaseUrl && userId);

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
