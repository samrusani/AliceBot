import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ThreadEventList } from "./thread-event-list";

describe("ThreadEventList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders bounded recent sessions and event summaries for the selected thread", () => {
    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="fixture"
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
            created_at: "2026-03-17T10:00:00Z",
          },
          {
            id: "event-2",
            thread_id: "thread-1",
            session_id: "session-1",
            sequence_no: 2,
            kind: "approval.request",
            payload: { action: "place_order", scope: "supplements", status: "pending" },
            created_at: "2026-03-17T10:05:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("Recent continuity state")).toBeInTheDocument();
    expect(screen.getByText(/place_order in supplements is pending/i)).toBeInTheDocument();
    expect(screen.getByText("Sequence 2")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("shows an empty state when the selected thread has no continuity yet", () => {
    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="fixture"
        sessions={[]}
        events={[]}
      />,
    );

    expect(screen.getByText("No continuity captured yet")).toBeInTheDocument();
  });
});
