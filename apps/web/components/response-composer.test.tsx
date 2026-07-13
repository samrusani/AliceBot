import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../lib/api";
import { ResponseComposer } from "./response-composer";

const { submitAssistantResponseMock } = vi.hoisted(() => ({
  submitAssistantResponseMock: vi.fn(),
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
    submitAssistantResponse: submitAssistantResponseMock,
  };
});

describe("ResponseComposer", () => {
  beforeEach(() => {
    submitAssistantResponseMock.mockReset();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("submits assistant messages through the shipped response endpoint", async () => {
    submitAssistantResponseMock.mockResolvedValue({
      assistant: {
        event_id: "assistant-event-1",
        sequence_no: 3,
        text: "You prefer oat milk.",
        model_provider: "openai_responses",
        model: "gpt-5-mini",
      },
      trace: {
        compile_trace_id: "compile-trace-1",
        compile_trace_event_count: 3,
        response_trace_id: "response-trace-1",
        response_trace_event_count: 2,
      },
    });

    render(
      <ResponseComposer
        initialEntries={[]}
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        selectedThreadId="thread-1"
        selectedThreadTitle="Gamma thread"
        source="live"
      />,
    );

    fireEvent.change(screen.getByLabelText("Ask the assistant"), {
      target: { value: "What do I usually take in coffee?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));

    await waitFor(() => {
      expect(submitAssistantResponseMock).toHaveBeenCalledWith(
        "https://api.example.com",
        {
          user_id: "user-1",
          thread_id: "thread-1",
          message: "What do I usually take in coffee?",
        },
        expect.any(String),
      );
    });

    expect(await screen.findByText("You prefer oat milk.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open compile trace" })).toHaveAttribute(
      "href",
      "/traces?trace=compile-trace-1",
    );
    expect(screen.getByText(/Assistant reply added successfully/i)).toBeInTheDocument();
  });

  it("reuses one idempotency key while polling a 202 response job", async () => {
    vi.useFakeTimers();
    submitAssistantResponseMock
      .mockResolvedValueOnce({
        detail: {
          code: "response_generation_in_progress",
          message: "response generation is already in progress",
        },
        response_job: {
          id: "job-1",
          state: "running",
          endpoint: "/v0/responses",
          created_at: "2026-07-13T10:00:00Z",
          updated_at: "2026-07-13T10:00:01Z",
          completed_at: null,
        },
      })
      .mockResolvedValueOnce({
        assistant: {
          event_id: "assistant-event-1",
          sequence_no: 3,
          text: "Finished once.",
          model_provider: "openai_responses",
          model: "gpt-5-mini",
        },
        trace: {
          compile_trace_id: "compile-trace-1",
          compile_trace_event_count: 3,
          response_trace_id: "response-trace-1",
          response_trace_event_count: 2,
        },
      });
    render(
      <ResponseComposer
        initialEntries={[]}
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        selectedThreadId="thread-1"
        selectedThreadTitle="Polling thread"
        source="live"
      />,
    );

    fireEvent.change(screen.getByLabelText("Ask the assistant"), {
      target: { value: "Finish this once." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));
    await act(async () => undefined);
    expect(submitAssistantResponseMock).toHaveBeenCalledTimes(1);
    const firstKey = submitAssistantResponseMock.mock.calls[0]?.[2];

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });

    expect(submitAssistantResponseMock).toHaveBeenCalledTimes(2);
    expect(submitAssistantResponseMock.mock.calls[1]?.[2]).toBe(firstKey);
    expect(screen.getByText("Finished once.")).toBeInTheDocument();
  });

  it("retains an uncertain request key but rotates it after a terminal error", async () => {
    submitAssistantResponseMock
      .mockRejectedValueOnce(new ApiError("Request timed out", 0, "request_timeout"))
      .mockRejectedValueOnce(new ApiError("Rate limited", 429, "response_rate_limit_exceeded"))
      .mockResolvedValueOnce({
        assistant: {
          event_id: "assistant-event-2",
          sequence_no: 4,
          text: "Fresh logical attempt.",
          model_provider: "openai_responses",
          model: "gpt-5-mini",
        },
        trace: {
          compile_trace_id: "compile-trace-2",
          compile_trace_event_count: 3,
          response_trace_id: "response-trace-2",
          response_trace_event_count: 2,
        },
      });
    render(
      <ResponseComposer
        initialEntries={[]}
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        selectedThreadId="thread-1"
        selectedThreadTitle="Retry thread"
        source="live"
      />,
    );

    fireEvent.change(screen.getByLabelText("Ask the assistant"), {
      target: { value: "Retry safely." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));
    expect(await screen.findByText(/Request timed out/i)).toBeInTheDocument();
    const uncertainKey = submitAssistantResponseMock.mock.calls[0]?.[2];

    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));
    expect(await screen.findByText(/Rate limited/i)).toBeInTheDocument();
    expect(submitAssistantResponseMock.mock.calls[1]?.[2]).toBe(uncertainKey);

    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));
    expect(await screen.findByText("Fresh logical attempt.")).toBeInTheDocument();
    expect(submitAssistantResponseMock.mock.calls[2]?.[2]).not.toBe(uncertainKey);
  });

  it("adds an explicit fixture preview when live API configuration is absent", async () => {
    render(
      <ResponseComposer
        initialEntries={[]}
        selectedThreadId="thread-1"
        selectedThreadTitle="Gamma thread"
      />,
    );

    fireEvent.change(screen.getByLabelText("Ask the assistant"), {
      target: { value: "Summarize the latest thread state." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));

    expect(submitAssistantResponseMock).not.toHaveBeenCalled();
    expect(await screen.findByText(/Fixture mode generated a preview response only/i)).toBeInTheDocument();
    expect(screen.getByText(/Fixture response preview added/i)).toBeInTheDocument();
  });

  it("never submits fixture thread IDs even when API credentials are present", async () => {
    render(
      <ResponseComposer
        initialEntries={[]}
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        selectedThreadId="fixture-thread-1"
        selectedThreadTitle="Fixture thread"
        source="fixture"
      />,
    );

    fireEvent.change(screen.getByLabelText("Ask the assistant"), {
      target: { value: "Preview this fixture thread." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));

    expect(submitAssistantResponseMock).not.toHaveBeenCalled();
    expect(await screen.findByText(/Fixture response preview added/i)).toBeInTheDocument();
  });

  it("disables assistant submission while continuity is unavailable", () => {
    render(
      <ResponseComposer
        initialEntries={[]}
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        selectedThreadId="thread-1"
        selectedThreadTitle="Unavailable thread"
        source="unavailable"
      />,
    );

    fireEvent.change(screen.getByLabelText("Ask the assistant"), {
      target: { value: "Do not submit this." },
    });
    expect(screen.getByRole("button", { name: "Ask assistant" })).toBeDisabled();
    expect(screen.getByText(/submission is unavailable until live continuity can be loaded/i)).toBeInTheDocument();
  });

  it("requires a selected thread before enabling assistant submission", () => {
    render(<ResponseComposer initialEntries={[]} />);

    expect(screen.getByRole("button", { name: "Ask assistant" })).toBeDisabled();
    expect(screen.getByText(/Select or create a thread from the right rail/i)).toBeInTheDocument();
  });
});
