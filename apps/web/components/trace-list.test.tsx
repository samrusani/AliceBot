import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TracesPage from "../app/traces/page";
import { TraceList, type TraceItem } from "./trace-list";

const {
  getApiConfigMock,
  hasLiveApiConfigMock,
  listTracesMock,
  getTraceDetailMock,
  getTraceEventsMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listTracesMock: vi.fn(),
  getTraceDetailMock: vi.fn(),
  getTraceEventsMock: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listTraces: listTracesMock,
    getTraceDetail: getTraceDetailMock,
    getTraceEvents: getTraceEventsMock,
  };
});

const liveTrace: TraceItem = {
  id: "trace-1",
  kind: "context.compile",
  status: "completed",
  title: "Context Compile review",
  summary: "Context Compile recorded 2 ordered events for thread thread-1 and ended in completed status.",
  eventCount: 2,
  createdAt: "2026-03-17T00:00:00Z",
  source: "continuity_v0",
  scope: "Thread thread-1",
  related: {
    threadId: "thread-1",
    compilerVersion: "continuity_v0",
  },
  metadata: ["Trace: trace-1", "Thread: thread-1", "Compiler: continuity_v0"],
  evidence: ["2 ordered events loaded from the shipped trace review API."],
  events: [
    {
      id: "event-1",
      kind: "context.summary",
      title: "Context Summary event",
      detail: "This event captured 1 payload field for operator review.",
      facts: ["Sequence 1", "thread_id: thread-1"],
    },
  ],
  detailSource: "live",
  eventSource: "live",
};

describe("TraceList", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listTracesMock.mockReset();
    getTraceDetailMock.mockReset();
    getTraceEventsMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders an explicit unavailable state when the configured trace API cannot be reached", () => {
    render(<TraceList traces={[]} apiUnavailable />);

    expect(screen.getByText("Trace API unavailable")).toBeInTheDocument();
    expect(screen.getByText("No live trace detail")).toBeInTheDocument();
  });

  it("renders an empty split state when no traces are available", () => {
    render(<TraceList traces={[]} />);

    expect(screen.getByText("Trace review is empty")).toBeInTheDocument();
    expect(screen.getByText("Explain-why detail is idle")).toBeInTheDocument();
  });

  it("keeps the selected trace bounded when ordered events are unavailable", () => {
    render(
      <TraceList
        traces={[
          {
            ...liveTrace,
            events: [],
            eventsUnavailable: true,
          },
        ]}
        selectedId="trace-1"
      />,
    );

    expect(screen.getByText("Key metadata")).toBeInTheDocument();
    expect(screen.getByText("Ordered events unavailable")).toBeInTheDocument();
    expect(screen.getByText("Detail: Live trace detail")).toBeInTheDocument();
  });

  it("renders ordered event review for a selected trace", () => {
    render(<TraceList traces={[liveTrace]} selectedId="trace-1" />);

    expect(screen.getAllByText("Context Compile review")).toHaveLength(2);
    expect(screen.getByText("Context Summary event")).toBeInTheDocument();
    expect(screen.getByText("Sequence 1")).toBeInTheDocument();
  });
});

describe("TracesPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listTracesMock.mockReset();
    getTraceDetailMock.mockReset();
    getTraceEventsMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("stays fixture-backed when live API configuration is absent", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "",
      userId: "",
      defaultThreadId: "",
      defaultToolId: "",
    });
    hasLiveApiConfigMock.mockReturnValue(false);

    render(
      await TracesPage({
        searchParams: Promise.resolve({
          trace: "trace-approval-101",
        }),
      }),
    );

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getAllByText("Approval request review").length).toBeGreaterThan(0);
    expect(listTracesMock).not.toHaveBeenCalled();
  });

  it("shows an explicit unavailable state when the live trace list cannot be loaded", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "",
      defaultToolId: "",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listTracesMock.mockRejectedValue(new Error("trace list failed"));

    render(await TracesPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getAllByText("Trace API unavailable")).toHaveLength(2);
    expect(screen.getByText("Explainability review is unavailable")).toBeInTheDocument();
  });

  it("keeps the live route bounded when detail loads but ordered events fail", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "",
      defaultToolId: "",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listTracesMock.mockResolvedValue({
      items: [
        {
          id: "trace-1",
          thread_id: "thread-1",
          kind: "context.compile",
          compiler_version: "continuity_v0",
          status: "completed",
          created_at: "2026-03-17T00:00:00Z",
          trace_event_count: 2,
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_desc", "id_desc"],
      },
    });
    getTraceDetailMock.mockResolvedValue({
      trace: {
        id: "trace-1",
        thread_id: "thread-1",
        kind: "context.compile",
        compiler_version: "continuity_v0",
        status: "completed",
        created_at: "2026-03-17T00:00:00Z",
        trace_event_count: 2,
        limits: {
          max_sessions: 3,
          max_events: 8,
        },
      },
    });
    getTraceEventsMock.mockRejectedValue(new Error("event read failed"));

    render(
      await TracesPage({
        searchParams: Promise.resolve({
          trace: "trace-1",
        }),
      }),
    );

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText("Ordered events unavailable")).toBeInTheDocument();
    expect(screen.getByText("Limit max_events: 8")).toBeInTheDocument();
  });
});
