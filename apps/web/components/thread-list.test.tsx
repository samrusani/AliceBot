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
            created_at: "2026-03-17T10:00:00Z",
            updated_at: "2026-03-17T10:00:00Z",
          },
          {
            id: "thread-2",
            title: "Delta thread",
            created_at: "2026-03-17T11:00:00Z",
            updated_at: "2026-03-17T11:00:00Z",
          },
        ]}
        selectedThreadId="thread-2"
        currentMode="request"
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
  });
});
