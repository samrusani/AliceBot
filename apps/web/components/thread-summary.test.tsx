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
        source="live"
      />,
    );

    expect(screen.getByText("Gamma thread")).toBeInTheDocument();
    expect(screen.getByText("Live continuity API")).toBeInTheDocument();
    expect(screen.getByText("thread-1")).toBeInTheDocument();
    expect(screen.getByText("Sessions")).toBeInTheDocument();
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
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
});
