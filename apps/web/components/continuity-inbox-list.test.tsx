import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ContinuityInboxList } from "./continuity-inbox-list";

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

const inboxItems = [
  {
    capture_event: {
      id: "capture-1",
      raw_content: "Finalize launch checklist",
      explicit_signal: "task" as const,
      admission_posture: "DERIVED" as const,
      admission_reason: "explicit_signal_task",
      created_at: "2026-03-29T09:00:00Z",
    },
    derived_object: {
      id: "object-1",
      capture_event_id: "capture-1",
      object_type: "NextAction" as const,
      status: "active" as const,
      title: "Next Action: Finalize launch checklist",
      body: {
        action_text: "Finalize launch checklist",
      },
      provenance: {
        capture_event_id: "capture-1",
      },
      confidence: 1,
      created_at: "2026-03-29T09:00:00Z",
      updated_at: "2026-03-29T09:00:00Z",
    },
  },
  {
    capture_event: {
      id: "capture-2",
      raw_content: "Maybe revisit this next month",
      explicit_signal: null,
      admission_posture: "TRIAGE" as const,
      admission_reason: "ambiguous_capture_requires_triage",
      created_at: "2026-03-29T09:10:00Z",
    },
    derived_object: null,
  },
];

describe("ContinuityInboxList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders links, triage posture, and selected state", () => {
    render(
      <ContinuityInboxList
        items={inboxItems}
        selectedCaptureId="capture-2"
        summary={{
          limit: 20,
          returned_count: 2,
          total_count: 2,
          derived_count: 1,
          triage_count: 1,
          order: ["created_at_desc", "id_desc"],
        }}
        source="live"
      />,
    );

    expect(screen.getByRole("link", { name: /Finalize launch checklist/i })).toHaveAttribute(
      "href",
      "/continuity?capture=capture-1",
    );
    expect(screen.getByRole("link", { name: /Maybe revisit this next month/i })).toHaveAttribute(
      "href",
      "/continuity?capture=capture-2",
    );
    expect(screen.getByRole("link", { name: /Maybe revisit this next month/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("NextAction")).toBeInTheDocument();
    expect(screen.getByText("No durable object")).toBeInTheDocument();
    expect(screen.getByText("1 triage")).toBeInTheDocument();
  });

  it("renders empty state when the inbox has no captures", () => {
    render(
      <ContinuityInboxList
        items={[]}
        summary={null}
        source="fixture"
      />,
    );

    expect(screen.getByText("No captures yet")).toBeInTheDocument();
    expect(screen.getByText("Inbox is empty")).toBeInTheDocument();
  });
});
