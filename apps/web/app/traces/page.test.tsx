import React from "react";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TracesPage from "./page";
import TracesLoading from "./loading";

const {
  getApiConfigMock,
  getTraceDetailMock,
  getTraceEventsMock,
  hasLiveApiConfigMock,
  listTracesMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getTraceDetailMock: vi.fn(),
  getTraceEventsMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listTracesMock: vi.fn(),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getTraceDetail: getTraceDetailMock,
    getTraceEvents: getTraceEventsMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listTraces: listTracesMock,
  };
});

function deferred<T = never>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

const liveTraceSummary = {
  id: "trace-live-1",
  thread_id: "thread-1",
  kind: "response.generate",
  compiler_version: "response_generation_v0",
  status: "completed",
  created_at: "2026-03-17T08:45:04Z",
  trace_event_count: 1,
};

function configureLiveTraceList() {
  getApiConfigMock.mockReturnValue({
    apiBaseUrl: "https://api.example.com",
    userId: "user-1",
    defaultThreadId: "thread-1",
    defaultToolId: "tool-1",
  });
  hasLiveApiConfigMock.mockReturnValue(true);
  listTracesMock.mockResolvedValue({
    items: [liveTraceSummary],
    summary: { total_count: 1, order: ["created_at_desc", "id_desc"] },
  });
}

describe("TracesPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getTraceDetailMock.mockReset();
    getTraceEventsMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listTracesMock.mockReset();

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "",
      userId: "",
      defaultThreadId: "",
      defaultToolId: "",
    });
    hasLiveApiConfigMock.mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
  });

  it("announces the loading route without interrupting the operator", () => {
    const { container } = render(<TracesLoading />);

    expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
    expect(container.firstElementChild).toHaveAttribute("aria-live", "polite");
  });

  it("shows fixture mode when live api config is absent", async () => {
    render(await TracesPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Trace and explain-why review")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Context compile review/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("shows api unavailable chip when live trace list fails", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listTracesMock.mockRejectedValue(new Error("trace backend unavailable"));

    render(await TracesPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getAllByText("Trace API unavailable").length).toBeGreaterThanOrEqual(1);
  });

  it("starts trace detail and event reads in the same request wave", async () => {
    configureLiveTraceList();

    const detail = deferred();
    const events = deferred();
    getTraceDetailMock.mockReturnValue(detail.promise);
    getTraceEventsMock.mockReturnValue(events.promise);

    const pagePromise = TracesPage({
      searchParams: Promise.resolve({ trace: "trace-live-1" }),
    });

    await waitFor(() => {
      expect(getTraceDetailMock).toHaveBeenCalledTimes(1);
      expect(getTraceEventsMock).toHaveBeenCalledTimes(1);
    });

    detail.reject(new Error("detail unavailable"));
    events.reject(new Error("events unavailable"));
    await pagePromise;
  });

  it("renders live events from the same wave when trace detail is unavailable", async () => {
    configureLiveTraceList();
    getTraceDetailMock.mockRejectedValue(new Error("detail unavailable"));
    getTraceEventsMock.mockResolvedValue({
      items: [
        {
          id: "event-live-1",
          trace_id: "trace-live-1",
          sequence_no: 1,
          kind: "response.model.completed",
          payload: { provider: "openai_responses" },
          created_at: "2026-03-17T08:45:05Z",
        },
      ],
      summary: {
        trace_id: "trace-live-1",
        total_count: 1,
        order: ["sequence_asc", "id_asc"],
      },
    });

    render(
      await TracesPage({
        searchParams: Promise.resolve({ trace: "trace-live-1" }),
      }),
    );

    expect(screen.getByText("Response Model Completed event")).toBeInTheDocument();
    expect(screen.getByText("Detail: Unavailable")).toBeInTheDocument();
    expect(screen.getByText("Events: Live event review")).toBeInTheDocument();
    expect(screen.queryByText("Ordered events unavailable")).not.toBeInTheDocument();
  });

  it("retains live trace detail when ordered events are unavailable", async () => {
    configureLiveTraceList();
    getTraceDetailMock.mockResolvedValue({
      trace: {
        ...liveTraceSummary,
        limits: { max_events: 8 },
      },
    });
    getTraceEventsMock.mockRejectedValue(new Error("events unavailable"));

    render(
      await TracesPage({
        searchParams: Promise.resolve({ trace: "trace-live-1" }),
      }),
    );

    expect(screen.getByText("Limit max_events: 8")).toBeInTheDocument();
    expect(screen.getByText("Detail: Live trace detail")).toBeInTheDocument();
    expect(screen.getByText("Events: Unavailable")).toBeInTheDocument();
    expect(screen.getByText("Ordered events unavailable")).toBeInTheDocument();
  });
});
