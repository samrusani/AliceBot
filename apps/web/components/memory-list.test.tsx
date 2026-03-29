import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MemoryList } from "./memory-list";

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

const baseMemories = [
  {
    id: "memory-1",
    memory_key: "user.preference.merchant",
    value: { merchant: "Thorne" },
    status: "active" as const,
    source_event_ids: ["event-1"],
    created_at: "2026-03-17T10:00:00Z",
    updated_at: "2026-03-17T10:00:00Z",
    deleted_at: null,
  },
  {
    id: "memory-2",
    memory_key: "user.preference.delivery",
    value: { window: "weekday_morning" },
    status: "active" as const,
    source_event_ids: ["event-2"],
    created_at: "2026-03-17T11:00:00Z",
    updated_at: "2026-03-17T11:00:00Z",
    deleted_at: null,
  },
];

describe("MemoryList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders queue-filter links that preserve selected memory state", () => {
    render(
      <MemoryList
        memories={baseMemories}
        selectedMemoryId="memory-2"
        summary={null}
        source="live"
        filter="queue"
        priorityMode="high_risk_first"
        availablePriorityModes={[
          "oldest_first",
          "recent_first",
          "high_risk_first",
          "stale_truth_first",
        ]}
      />,
    );

    expect(screen.getByRole("link", { name: /user.preference.merchant/i })).toHaveAttribute(
      "href",
      "/memories?filter=queue&memory=memory-1&priority_mode=high_risk_first",
    );
    expect(screen.getByRole("link", { name: /user.preference.delivery/i })).toHaveAttribute(
      "href",
      "/memories?filter=queue&memory=memory-2&priority_mode=high_risk_first",
    );
    expect(screen.getByRole("link", { name: /user.preference.delivery/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "High risk first" })).toHaveAttribute(
      "href",
      "/memories?filter=queue&priority_mode=high_risk_first",
    );
  });

  it("renders active-filter links without queue params", () => {
    render(
      <MemoryList
        memories={baseMemories}
        selectedMemoryId="memory-1"
        summary={null}
        source="fixture"
        filter="active"
      />,
    );

    expect(screen.getByRole("link", { name: /user.preference.merchant/i })).toHaveAttribute(
      "href",
      "/memories?memory=memory-1",
    );
  });
});
