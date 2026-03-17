import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RequestComposer } from "./request-composer";

const { submitApprovalRequestMock } = vi.hoisted(() => ({
  submitApprovalRequestMock: vi.fn(),
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
    submitApprovalRequest: submitApprovalRequestMock,
  };
});

describe("RequestComposer", () => {
  beforeEach(() => {
    submitApprovalRequestMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("submits governed requests against the selected thread", async () => {
    submitApprovalRequestMock.mockResolvedValue({
      request: {
        thread_id: "thread-1",
        tool_id: "tool-1",
        action: "place_order",
        scope: "supplements",
        domain_hint: "ecommerce",
        risk_hint: "purchase",
        attributes: {
          merchant: "Thorne",
          item: "Magnesium Bisglycinate",
          quantity: "1",
        },
      },
      decision: "approval_required",
      tool: {
        id: "tool-1",
        tool_key: "merchant_proxy",
        name: "Merchant Proxy",
        description: "Proxy",
        version: "0.1.0",
        metadata_version: "tool_metadata_v0",
        active: true,
        tags: [],
        action_hints: [],
        scope_hints: [],
        domain_hints: [],
        risk_hints: [],
        metadata: {},
        created_at: "2026-03-17T00:00:00Z",
      },
      reasons: [],
      task: {
        id: "task-1",
        thread_id: "thread-1",
        tool_id: "tool-1",
        status: "pending_approval",
        request: {
          thread_id: "thread-1",
          tool_id: "tool-1",
          action: "place_order",
          scope: "supplements",
          domain_hint: "ecommerce",
          risk_hint: "purchase",
          attributes: {
            merchant: "Thorne",
            item: "Magnesium Bisglycinate",
            quantity: "1",
          },
        },
        tool: {
          id: "tool-1",
          tool_key: "merchant_proxy",
          name: "Merchant Proxy",
          description: "Proxy",
          version: "0.1.0",
          metadata_version: "tool_metadata_v0",
          active: true,
          tags: [],
          action_hints: [],
          scope_hints: [],
          domain_hints: [],
          risk_hints: [],
          metadata: {},
          created_at: "2026-03-17T00:00:00Z",
        },
        latest_approval_id: "approval-1",
        latest_execution_id: null,
        created_at: "2026-03-17T00:00:00Z",
        updated_at: "2026-03-17T00:00:00Z",
      },
      approval: null,
      routing_trace: {
        trace_id: "route-trace-1",
        trace_event_count: 3,
      },
      trace: {
        trace_id: "request-trace-1",
        trace_event_count: 6,
      },
    });

    render(
      <RequestComposer
        initialEntries={[]}
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        selectedThreadId="thread-1"
        selectedThreadTitle="Gamma thread"
        defaultToolId="tool-1"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Submit governed request" }));

    await waitFor(() => {
      expect(submitApprovalRequestMock).toHaveBeenCalledWith("https://api.example.com", {
        user_id: "user-1",
        thread_id: "thread-1",
        tool_id: "tool-1",
        action: "place_order",
        scope: "supplements",
        domain_hint: "ecommerce",
        risk_hint: "purchase",
        attributes: {
          merchant: "Thorne",
          item: "Magnesium Bisglycinate",
          quantity: "1",
        },
      });
    });

    expect(screen.getByText(/Governed request submitted successfully/i)).toBeInTheDocument();
  });

  it("disables governed submission when no thread is selected", () => {
    render(
      <RequestComposer
        initialEntries={[]}
        defaultToolId="tool-1"
      />,
    );

    expect(screen.getByRole("button", { name: "Submit governed request" })).toBeDisabled();
    expect(screen.getByText(/Select or create a thread from the right rail/i)).toBeInTheDocument();
  });
});
