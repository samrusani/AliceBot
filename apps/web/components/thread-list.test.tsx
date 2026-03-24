import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ThreadList } from "./thread-list";

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

describe("ThreadList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders thread links that preserve the current mode and selected thread", () => {
    render(
      <ThreadList
        threads={[
          {
            id: "thread-1",
            title: "Gamma thread",
            agent_profile_id: "assistant_default",
            created_at: "2026-03-17T10:00:00Z",
            updated_at: "2026-03-17T10:00:00Z",
          },
          {
            id: "thread-2",
            title: "Delta thread",
            agent_profile_id: "coach_default",
            created_at: "2026-03-17T11:00:00Z",
            updated_at: "2026-03-17T11:00:00Z",
          },
        ]}
        selectedThreadId="thread-2"
        currentMode="request"
        agentProfiles={[
          {
            id: "assistant_default",
            name: "Assistant Default",
            description: "General-purpose assistant profile for baseline conversations.",
          },
          {
            id: "coach_default",
            name: "Coach Default",
            description: "Coaching-oriented profile focused on guidance and accountability.",
          },
        ]}
        source="live"
      />,
    );

    expect(screen.getByRole("link", { name: /Gamma thread/i })).toHaveAttribute(
      "href",
      "/chat?mode=request&thread=thread-1",
    );
    expect(screen.getByRole("link", { name: /Delta thread/i })).toHaveAttribute(
      "href",
      "/chat?mode=request&thread=thread-2",
    );
    expect(screen.getByRole("link", { name: /Delta thread/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Profile Assistant Default")).toBeInTheDocument();
    expect(screen.getByText("Profile Coach Default")).toBeInTheDocument();
  });
});
