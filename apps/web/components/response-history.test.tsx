import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ModeToggle } from "./mode-toggle";
import { ResponseHistory } from "./response-history";

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

afterEach(() => {
  cleanup();
});

describe("ResponseHistory", () => {
  it("renders an empty state when the selected thread has no transcript yet", () => {
    render(
      <ResponseHistory
        entries={[]}
        events={[]}
        threadTitle="Gamma thread"
        source="live"
      />,
    );

    expect(screen.getByText("No transcript yet")).toBeInTheDocument();
    expect(screen.getByText(/Conversation messages will appear here/i)).toBeInTheDocument();
  });

  it("renders continuity-derived transcript entries and trace links for local responses", () => {
    render(
      <ResponseHistory
        threadTitle="Gamma thread"
        source="live"
        entries={[
          {
            id: "response-trace-1",
            submittedAt: "2026-03-17T08:45:00Z",
            source: "live",
            threadId: "thread-1",
            message: "Summarize the latest thread state.",
            assistantText: "The latest governed request is still waiting on approval.",
            assistantEventId: "assistant-event-1",
            assistantSequenceNo: 3,
            modelProvider: "openai_responses",
            model: "gpt-5-mini",
            summary: "The reply is linked to both compile and response traces.",
            trace: {
              compileTraceId: "compile-trace-1",
              compileTraceEventCount: 3,
              responseTraceId: "response-trace-1",
              responseTraceEventCount: 2,
            },
          },
        ]}
        events={[
          {
            id: "event-1",
            thread_id: "thread-1",
            session_id: "session-1",
            sequence_no: 1,
            kind: "message.user",
            payload: { text: "Hello there." },
            created_at: "2026-03-17T08:40:00Z",
          },
          {
            id: "event-2",
            thread_id: "thread-1",
            session_id: "session-1",
            sequence_no: 2,
            kind: "message.assistant",
            payload: {
              text: "I have the earlier continuity context ready.",
              model: {
                provider: "openai_responses",
                model: "gpt-5-mini",
              },
            },
            created_at: "2026-03-17T08:41:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("Selected-thread transcript")).toBeInTheDocument();
    expect(screen.getByText("Hello there.")).toBeInTheDocument();
    expect(screen.getByText("The latest governed request is still waiting on approval.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open compile trace" })).toHaveAttribute(
      "href",
      "/traces?trace=compile-trace-1",
    );
    expect(screen.getByRole("link", { name: "Open response trace" })).toHaveAttribute(
      "href",
      "/traces?trace=response-trace-1",
    );
  });
});

describe("ModeToggle", () => {
  it("keeps the assistant and governed request modes explicit", () => {
    render(<ModeToggle currentMode="request" />);

    expect(screen.getByRole("link", { name: /Ask the assistant/i })).toHaveAttribute("href", "/chat");
    expect(screen.getByRole("link", { name: /Submit a governed request/i })).toHaveAttribute(
      "href",
      "/chat?mode=request",
    );
    expect(screen.getByRole("link", { name: /Submit a governed request/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
