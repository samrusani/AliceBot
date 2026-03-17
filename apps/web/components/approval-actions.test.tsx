import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApprovalActions } from "./approval-actions";

const { refreshMock, resolveApprovalMock } = vi.hoisted(() => ({
  refreshMock: vi.fn(),
  resolveApprovalMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    resolveApproval: resolveApprovalMock,
  };
});

const pendingApproval = {
  id: "approval-1",
  thread_id: "thread-1",
  task_step_id: "step-1",
  status: "pending",
  request: {
    thread_id: "thread-1",
    tool_id: "tool-1",
    action: "place_order",
    scope: "supplements",
    domain_hint: "ecommerce",
    risk_hint: "purchase",
    attributes: {
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
  routing: {
    decision: "require_approval",
    reasons: [],
    trace: {
      trace_id: "trace-1",
      trace_event_count: 3,
    },
  },
  created_at: "2026-03-17T00:00:00Z",
  resolution: null,
};

describe("ApprovalActions", () => {
  beforeEach(() => {
    refreshMock.mockReset();
    resolveApprovalMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("disables live actions in fixture mode", () => {
    render(<ApprovalActions approval={pendingApproval} onResolved={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeDisabled();
    expect(screen.getByText(/disabled in fixture mode/i)).toBeInTheDocument();
  });

  it("submits approval resolution and refreshes the route on success", async () => {
    const onResolved = vi.fn();
    resolveApprovalMock.mockResolvedValue({
      approval: {
        ...pendingApproval,
        status: "approved",
        resolution: {
          resolved_at: "2026-03-17T01:00:00Z",
          resolved_by_user_id: "user-1",
        },
      },
      trace: {
        trace_id: "trace-2",
        trace_event_count: 4,
      },
    });

    render(
      <ApprovalActions
        approval={pendingApproval}
        apiBaseUrl="https://api.example.com"
        userId="user-1"
        onResolved={onResolved}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(resolveApprovalMock).toHaveBeenCalledWith(
        "https://api.example.com",
        "approval-1",
        "approve",
        "user-1",
      );
    });

    await waitFor(() => {
      expect(onResolved).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "approved",
        }),
      );
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Approval resolved as approved/i)).toBeInTheDocument();
  });
});
