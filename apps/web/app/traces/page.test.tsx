import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TracesPage from "./page";

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

  it("shows fixture mode when live api config is absent", async () => {
    render(await TracesPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Trace and explain-why review")).toBeInTheDocument();
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
});
