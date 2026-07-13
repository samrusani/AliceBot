import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApprovalItem } from "../lib/api";
import { ApprovalList } from "./approval-list";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

const item: ApprovalItem = {
  id: "approval-1",
  thread_id: "thread-1",
  task_run_id: null,
  task_step_id: "step-1",
  status: "pending",
  request: {
    thread_id: "thread-1",
    tool_id: "tool-1",
    action: "publish",
    scope: "repository",
    domain_hint: "engineering",
    risk_hint: "external_write",
    attributes: {},
  },
  tool: {
    id: "tool-1", tool_key: "publisher", name: "Publisher", description: "", version: "1",
    metadata_version: "tool_metadata_v0", active: true, tags: [], action_hints: [], scope_hints: [],
    domain_hints: [], risk_hints: [], metadata: {}, created_at: "2026-07-13T10:00:00Z",
  },
  routing: { decision: "require_approval", reasons: [], trace: { trace_id: "trace-1", trace_event_count: 1 } },
  created_at: "2026-07-13T10:00:00Z",
  resolution: null,
};

describe("ApprovalList", () => {
  afterEach(cleanup);

  it("renders an actionable empty state", () => {
    render(<ApprovalList items={[]} />);
    expect(screen.getByText("Approval inbox is empty")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open requests" })).toHaveAttribute("href", "/chat");
  });

  it("renders selection, task linkage, and risk metadata", () => {
    render(<ApprovalList items={[item]} selectedId={item.id} />);
    const link = screen.getByRole("link", { name: /Publisher/i });
    expect(link).toHaveAttribute("href", "/approvals?approval=approval-1");
    expect(link).toHaveClass("is-selected");
    expect(screen.getByText("Step linked")).toBeInTheDocument();
    expect(screen.getByText("Risk external_write")).toBeInTheDocument();
  });
});
