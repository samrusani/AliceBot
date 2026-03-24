import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ThreadSummary } from "./thread-summary";

describe("ThreadSummary", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders selected thread metadata and continuity counts", () => {
    render(
      <ThreadSummary
        thread={{
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "coach_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:05:00Z",
        }}
        sessions={[
          {
            id: "session-1",
            thread_id: "thread-1",
            status: "active",
            started_at: "2026-03-17T10:00:00Z",
            ended_at: null,
            created_at: "2026-03-17T10:00:00Z",
          },
        ]}
        events={[
          {
            id: "event-1",
            thread_id: "thread-1",
            session_id: "session-1",
            sequence_no: 1,
            kind: "message.user",
            payload: { text: "Hello" },
            created_at: "2026-03-17T10:01:00Z",
          },
        ]}
        agentProfiles={[
          {
            id: "assistant_default",
            name: "Assistant Default",
            description: "General-purpose assistant profile for baseline conversations.",
          },
          {
            id: "coach_default",
            name: "Coach Default",
            description: "Coaching-oriented profile focused on guidance and accountability.",
          },
        ]}
        source="live"
      />,
    );

    expect(screen.getByText("Gamma thread")).toBeInTheDocument();
    expect(screen.getByText("Live continuity API")).toBeInTheDocument();
    expect(screen.getByText("thread-1")).toBeInTheDocument();
    expect(screen.getByText("Sessions")).toBeInTheDocument();
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("Profile Coach Default")).toBeInTheDocument();
    expect(screen.getByText("Agent profile")).toBeInTheDocument();
  });

  it("shows the explicit no-thread state when nothing is selected", () => {
    render(
      <ThreadSummary
        thread={null}
        sessions={[]}
        events={[]}
        source="fixture"
      />,
    );

    expect(screen.getByText("No thread selected")).toBeInTheDocument();
    expect(screen.getByText("Select a thread")).toBeInTheDocument();
  });

  it("renders deterministic resumption brief sections when available", () => {
    render(
      <ThreadSummary
        thread={{
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "assistant_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:05:00Z",
        }}
        sessions={[]}
        events={[]}
        source="live"
        resumptionSource="live"
        resumptionBrief={{
          assembly_version: "resumption_brief_v0",
          thread: {
            id: "thread-1",
            title: "Gamma thread",
            agent_profile_id: "assistant_default",
            created_at: "2026-03-17T10:00:00Z",
            updated_at: "2026-03-17T10:05:00Z",
          },
          conversation: {
            items: [
              {
                id: "event-1",
                thread_id: "thread-1",
                session_id: "session-1",
                sequence_no: 1,
                kind: "message.user",
                payload: { text: "Hello" },
                created_at: "2026-03-17T10:01:00Z",
              },
            ],
            summary: {
              limit: 8,
              returned_count: 1,
              total_count: 1,
              order: ["sequence_no_asc"],
              kinds: ["message.user", "message.assistant"],
            },
          },
          open_loops: {
            items: [
              {
                id: "loop-1",
                memory_id: null,
                title: "Follow up on dosage",
                status: "open",
                opened_at: "2026-03-17T10:02:00Z",
                due_at: null,
                resolved_at: null,
                resolution_note: null,
                created_at: "2026-03-17T10:02:00Z",
                updated_at: "2026-03-17T10:02:00Z",
              },
            ],
            summary: {
              limit: 5,
              returned_count: 1,
              total_count: 1,
              order: ["opened_at_desc", "created_at_desc", "id_desc"],
            },
          },
          memory_highlights: {
            items: [
              {
                id: "memory-1",
                memory_key: "user.preference.dose_time",
                value: { value: "morning" },
                status: "active",
                source_event_ids: ["event-1"],
                memory_type: "preference",
                confirmation_status: "confirmed",
                created_at: "2026-03-17T10:00:00Z",
                updated_at: "2026-03-17T10:03:00Z",
              },
            ],
            summary: {
              limit: 5,
              returned_count: 1,
              total_count: 1,
              order: ["updated_at_asc", "created_at_asc", "id_asc"],
            },
          },
          workflow: null,
          sources: ["threads", "events", "open_loops", "memories"],
        }}
      />,
    );

    expect(screen.getByText(/Live deterministic brief/i)).toBeInTheDocument();
    expect(screen.getByText("Latest conversation evidence")).toBeInTheDocument();
    expect(screen.getByText("Follow up on dosage")).toBeInTheDocument();
    expect(screen.getByText("user.preference.dose_time")).toBeInTheDocument();
  });

  it("shows explicit resumption brief unavailable state", () => {
    render(
      <ThreadSummary
        thread={{
          id: "thread-1",
          title: "Gamma thread",
          agent_profile_id: "assistant_default",
          created_at: "2026-03-17T10:00:00Z",
          updated_at: "2026-03-17T10:05:00Z",
        }}
        sessions={[]}
        events={[]}
        source="live"
        resumptionSource="unavailable"
        resumptionUnavailableReason="resumption brief down"
      />,
    );

    expect(screen.getByText("Resumption brief unavailable")).toBeInTheDocument();
    expect(screen.getByText("resumption brief down")).toBeInTheDocument();
  });
});
