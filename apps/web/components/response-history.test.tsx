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
  it("renders an empty state when no assistant replies are available", () => {
    render(<ResponseHistory entries={[]} />);

    expect(screen.getByText("No assistant replies yet")).toBeInTheDocument();
    expect(screen.getByText(/Submitted questions will appear here/i)).toBeInTheDocument();
  });

  it("renders bounded prompt, reply, and trace links for each entry", () => {
    render(
      <ResponseHistory
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
      />,
    );

    expect(screen.getByText("Operator prompt")).toBeInTheDocument();
    expect(screen.getByText("Assistant reply")).toBeInTheDocument();
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
