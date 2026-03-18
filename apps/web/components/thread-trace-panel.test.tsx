import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { threadFixtures } from "../lib/fixtures";
import { ThreadTracePanel } from "./thread-trace-panel";

const { listTracesMock, getTraceDetailMock, getTraceEventsMock } = vi.hoisted(() => ({
  listTracesMock: vi.fn(),
  getTraceDetailMock: vi.fn(),
  getTraceEventsMock: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    "aria-current": ariaCurrent,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
    "aria-current"?: string;
  }) => (
    <a href={href} className={className} aria-current={ariaCurrent}>
      {children}
    </a>
  ),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    listTraces: listTracesMock,
    getTraceDetail: getTraceDetailMock,
    getTraceEvents: getTraceEventsMock,
  };
});

describe("ThreadTracePanel", () => {
  beforeEach(() => {
    listTracesMock.mockReset();
    getTraceDetailMock.mockReset();
    getTraceEventsMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders a bounded empty state when no thread is selected", async () => {
    render(
      await ThreadTracePanel({
        thread: null,
        source: "fixture",
        traceTargets: [],
      }),
    );

    expect(screen.getByText("Thread-linked explainability")).toBeInTheDocument();
    expect(screen.getByText("Select a thread")).toBeInTheDocument();
  });

  it("renders fixture explainability detail for a selected linked trace", async () => {
    render(
      await ThreadTracePanel({
        thread: threadFixtures[0],
        source: "fixture",
        traceTargets: [
          {
            id: "trace-response-101",
            label: "Assistant response trace",
          },
          {
            id: "trace-ctx-401",
            label: "Assistant compile trace",
          },
        ],
        selectedTraceId: "trace-response-101",
        traceHrefPrefix: "/chat?thread=11111111-1111-4111-8111-111111111111&trace=",
      }),
    );

    expect(screen.getByText("Thread-linked explainability")).toBeInTheDocument();
    expect(screen.getByText("Assistant response review")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Assistant compile trace/i })).toHaveAttribute(
      "href",
      "/chat?thread=11111111-1111-4111-8111-111111111111&trace=trace-ctx-401",
    );
    expect(screen.getByText("Ordered events")).toBeInTheDocument();
    expect(screen.getByText("Open full trace workspace")).toBeInTheDocument();
  });

  it("keeps the panel explicit when linked trace IDs are unavailable in the current mode", async () => {
    render(
      await ThreadTracePanel({
        thread: threadFixtures[2],
        source: "fixture",
        traceTargets: [
          {
            id: "trace-does-not-exist",
            label: "Workflow trace",
          },
        ],
      }),
    );

    expect(screen.getByText("Linked trace unavailable")).toBeInTheDocument();
    expect(screen.getByText(/Missing trace IDs/i)).toBeInTheDocument();
  });

  it("ignores unrelated trace query ids in live mode and keeps selected-thread scope", async () => {
    listTracesMock.mockResolvedValue({
      items: [
        {
          id: "trace-related",
          thread_id: threadFixtures[0].id,
          kind: "response.generate",
          compiler_version: "response_generation_v0",
          status: "completed",
          created_at: "2026-03-17T08:45:04Z",
          trace_event_count: 1,
        },
        {
          id: "trace-foreign",
          thread_id: "thread-not-selected",
          kind: "response.generate",
          compiler_version: "response_generation_v0",
          status: "completed",
          created_at: "2026-03-17T08:45:10Z",
          trace_event_count: 1,
        },
      ],
      summary: {
        total_count: 2,
        order: ["created_at_desc", "id_desc"],
      },
    });
    getTraceDetailMock.mockResolvedValue({
      trace: {
        id: "trace-related",
        thread_id: threadFixtures[0].id,
        kind: "response.generate",
        compiler_version: "response_generation_v0",
        status: "completed",
        created_at: "2026-03-17T08:45:04Z",
        trace_event_count: 1,
        limits: {
          max_events: 8,
        },
      },
    });
    getTraceEventsMock.mockResolvedValue({
      items: [
        {
          id: "event-1",
          trace_id: "trace-related",
          sequence_no: 1,
          kind: "response.model.completed",
          payload: {
            provider: "openai_responses",
          },
          created_at: "2026-03-17T08:45:05Z",
        },
      ],
      summary: {
        trace_id: "trace-related",
        total_count: 1,
        order: ["sequence_asc", "id_asc"],
      },
    });

    render(
      await ThreadTracePanel({
        thread: threadFixtures[0],
        source: "live",
        traceTargets: [
          {
            id: "trace-related",
            label: "Workflow trace",
          },
        ],
        selectedTraceId: "trace-foreign",
        apiBaseUrl: "https://api.example.com",
        userId: "user-1",
      }),
    );

    expect(getTraceDetailMock).toHaveBeenCalledWith("https://api.example.com", "trace-related", "user-1");
    expect(screen.getByRole("link", { name: "Open full trace workspace" })).toHaveAttribute(
      "href",
      "/traces?trace=trace-related",
    );
  });
});
