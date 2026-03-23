import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ThreadEventList } from "./thread-event-list";

const { captureExplicitSignalsMock } = vi.hoisted(() => ({
  captureExplicitSignalsMock: vi.fn(),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    captureExplicitSignals: captureExplicitSignalsMock,
  };
});

const BASE_EVENTS = [
  {
    id: "event-1",
    thread_id: "thread-1",
    session_id: "session-1",
    sequence_no: 1,
    kind: "message.user",
    payload: { text: "Please remind me to submit tax forms." },
    created_at: "2026-03-17T10:00:00Z",
  },
  {
    id: "event-2",
    thread_id: "thread-1",
    session_id: "session-1",
    sequence_no: 2,
    kind: "message.assistant",
    payload: { text: "Sure, I can help with that." },
    created_at: "2026-03-17T10:01:00Z",
  },
  {
    id: "event-3",
    thread_id: "thread-1",
    session_id: "session-1",
    sequence_no: 3,
    kind: "approval.request",
    payload: { action: "place_order", scope: "supplements", status: "pending" },
    created_at: "2026-03-17T10:02:00Z",
  },
  {
    id: "event-4",
    thread_id: "thread-1",
    session_id: "session-1",
    sequence_no: 4,
    kind: "message.user",
    payload: { text: "I also need to call the dentist." },
    created_at: "2026-03-17T10:03:00Z",
  },
] as const;

describe("ThreadEventList", () => {
  beforeEach(() => {
    captureExplicitSignalsMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("selects only eligible message.user events and does not auto-capture on render", () => {
    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
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
        events={[...BASE_EVENTS]}
      />,
    );

    const sourceEventSelect = screen.getByLabelText("Eligible user event");
    const options = within(sourceEventSelect).getAllByRole("option");

    expect(options).toHaveLength(2);
    expect(options.map((option) => (option as HTMLOptionElement).value)).toEqual(["event-4", "event-1"]);
    expect(screen.getByRole("button", { name: "Capture explicit signals" })).toBeEnabled();
    expect(captureExplicitSignalsMock).not.toHaveBeenCalled();
  });

  it("posts deterministic capture payload and renders deterministic summary on success", async () => {
    captureExplicitSignalsMock.mockResolvedValue({
      preferences: {
        candidates: [],
        admissions: [],
        summary: {
          source_event_id: "event-1",
          source_event_kind: "message.user",
          candidate_count: 0,
          admission_count: 0,
          persisted_change_count: 0,
          noop_count: 0,
        },
      },
      commitments: {
        candidates: [],
        admissions: [],
        summary: {
          source_event_id: "event-1",
          source_event_kind: "message.user",
          candidate_count: 0,
          admission_count: 0,
          persisted_change_count: 0,
          noop_count: 0,
          open_loop_created_count: 0,
          open_loop_noop_count: 0,
        },
      },
      summary: {
        source_event_id: "event-1",
        source_event_kind: "message.user",
        candidate_count: 3,
        admission_count: 2,
        persisted_change_count: 2,
        noop_count: 1,
        open_loop_created_count: 1,
        open_loop_noop_count: 1,
        preference_candidate_count: 1,
        preference_admission_count: 1,
        commitment_candidate_count: 2,
        commitment_admission_count: 1,
      },
    });

    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        sessions={[]}
        events={[...BASE_EVENTS]}
      />,
    );

    fireEvent.change(screen.getByLabelText("Eligible user event"), {
      target: { value: "event-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Capture explicit signals" }));

    await waitFor(() => {
      expect(captureExplicitSignalsMock).toHaveBeenCalledWith("https://api.example.com", {
        user_id: "user-1",
        source_event_id: "event-1",
      });
    });

    expect(await screen.findByText("Capture result summary")).toBeInTheDocument();
    expect(screen.getByText("event-1 (message user)")).toBeInTheDocument();
    expect(screen.getByText("Candidates 3")).toBeInTheDocument();
    expect(screen.getByText("Admissions 2")).toBeInTheDocument();
    expect(screen.getByText("Open loops created 1")).toBeInTheDocument();
    expect(screen.getByText("Open loops noop 1")).toBeInTheDocument();
  });

  it("renders deterministic non-destructive error text when capture fails", async () => {
    captureExplicitSignalsMock.mockRejectedValue(
      new Error("source_event_id must reference an existing message.user event"),
    );

    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        sessions={[]}
        events={[BASE_EVENTS[0]]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Capture explicit signals" }));

    expect(
      await screen.findByText(
        /Capture failed: source_event_id must reference an existing message\.user event/i,
      ),
    ).toBeInTheDocument();
  });

  it("shows explicit fixture and unavailable disabled states", () => {
    const { rerender } = render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="fixture"
        sessions={[]}
        events={[BASE_EVENTS[0]]}
      />,
    );

    expect(screen.getByRole("button", { name: "Capture explicit signals" })).toBeDisabled();
    expect(
      screen.getByText(/Fixture mode is non-destructive\. Configure live API settings to enable capture\./i),
    ).toBeInTheDocument();

    rerender(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="unavailable"
        unavailableReason="Thread events failed to load."
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        sessions={[]}
        events={[BASE_EVENTS[0]]}
      />,
    );

    expect(screen.getByRole("button", { name: "Capture explicit signals" })).toBeDisabled();
    expect(screen.getAllByText("Thread events failed to load.").length).toBeGreaterThan(0);
  });

  it("shows blocked live state when API config is incomplete", () => {
    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="live"
        sessions={[]}
        events={[BASE_EVENTS[0]]}
      />,
    );

    const captureButton = screen.getByRole("button", { name: "Capture explicit signals" });
    expect(captureButton).toBeDisabled();
    expect(
      screen.getByText("Live API configuration is incomplete for explicit-signal capture."),
    ).toBeInTheDocument();

    fireEvent.click(captureButton);
    expect(captureExplicitSignalsMock).not.toHaveBeenCalled();
  });

  it("shows blocked live state when no eligible message.user events exist", () => {
    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        sessions={[]}
        events={[BASE_EVENTS[1], BASE_EVENTS[2]]}
      />,
    );

    expect(screen.getByRole("button", { name: "Capture explicit signals" })).toBeDisabled();
    expect(
      screen.getByText("No eligible message.user events are available on this thread."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Eligible user event")).toBeDisabled();
    expect(captureExplicitSignalsMock).not.toHaveBeenCalled();
  });

  it("renders bounded recent sessions and event summaries for continuity review", () => {
    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
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
        events={[...BASE_EVENTS]}
      />,
    );

    expect(screen.getByText("Bounded supporting continuity")).toBeInTheDocument();
    expect(screen.getByText(/place_order in supplements is pending/i)).toBeInTheDocument();
    expect(screen.getByText("Sequence 3")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("shows continuity empty state when selected thread has no sessions and no operational events", () => {
    render(
      <ThreadEventList
        threadTitle="Gamma thread"
        source="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        sessions={[]}
        events={[]}
      />,
    );

    expect(screen.getByText("No supporting continuity yet")).toBeInTheDocument();
  });
});
