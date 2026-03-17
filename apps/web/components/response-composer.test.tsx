import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
      />,
    );

    fireEvent.change(screen.getByLabelText("Ask the assistant"), {
      target: { value: "What do I usually take in coffee?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask assistant" }));

    await waitFor(() => {
      expect(submitAssistantResponseMock).toHaveBeenCalledWith("https://api.example.com", {
        user_id: "user-1",
        thread_id: "thread-1",
        message: "What do I usually take in coffee?",
      });
    });

    expect(await screen.findByText("You prefer oat milk.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open compile trace" })).toHaveAttribute(
      "href",
      "/traces?trace=compile-trace-1",
    );
    expect(screen.getByText(/Assistant reply added successfully/i)).toBeInTheDocument();
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

  it("requires a selected thread before enabling assistant submission", () => {
    render(<ResponseComposer initialEntries={[]} />);

    expect(screen.getByRole("button", { name: "Ask assistant" })).toBeDisabled();
    expect(screen.getByText(/Select or create a thread from the right rail/i)).toBeInTheDocument();
  });
});
