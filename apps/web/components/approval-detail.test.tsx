import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApprovalDetail } from "./approval-detail";

const { admitMemoryMock, refreshMock } = vi.hoisted(() => ({
  admitMemoryMock: vi.fn(),
  refreshMock: vi.fn(),
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
    admitMemory: admitMemoryMock,
  };
});

const approval = {
  id: "approval-1",
  thread_id: "thread-1",
  task_step_id: "step-1",
  status: "approved",
  request: {
    thread_id: "thread-1",
    tool_id: "tool-1",
    action: "place_order",
    scope: "supplements",
    domain_hint: "ecommerce",
    risk_hint: "purchase",
    attributes: {
      item: "Magnesium Bisglycinate",
      merchant: "Thorne",
    },
  },
  tool: {
    id: "tool-1",
    tool_key: "proxy.echo",
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
    created_at: "2026-03-19T00:00:00Z",
  },
  routing: {
    decision: "require_approval",
    reasons: [
      {
        code: "policy_effect_require_approval",
        source: "policy",
        message: "Purchases require explicit approval.",
        tool_id: "tool-1",
        policy_id: "policy-1",
        consent_key: null,
      },
    ],
    trace: {
      trace_id: "trace-approval-1",
      trace_event_count: 3,
    },
  },
  created_at: "2026-03-19T00:00:00Z",
  resolution: {
    resolved_at: "2026-03-19T00:01:00Z",
    resolved_by_user_id: "user-1",
  },
};

const execution = {
  id: "execution-1",
  approval_id: "approval-1",
  task_step_id: "step-1",
  thread_id: "thread-1",
  tool_id: "tool-1",
  trace_id: "trace-execution-1",
  request_event_id: "event-request-1",
  result_event_id: "event-result-1",
  status: "completed",
  handler_key: "proxy.echo",
  request: approval.request,
  tool: approval.tool,
  result: {
    handler_key: "proxy.echo",
    status: "completed",
    output: {
      mode: "no_side_effect",
      item: "Magnesium Bisglycinate",
    },
    reason: null,
  },
  executed_at: "2026-03-19T00:03:00Z",
};

describe("ApprovalDetail", () => {
  beforeEach(() => {
    admitMemoryMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("submits explicit memory write-back from execution-linked evidence", async () => {
    admitMemoryMock.mockResolvedValue({
      decision: "ADD",
      reason: "memory_created",
      memory: {
        id: "memory-1",
        user_id: "user-1",
        memory_key: "user.preference.supplement.magnesium",
        value: {
          merchant: "Thorne",
        },
        status: "active",
        source_event_ids: ["event-result-1", "event-request-1"],
        created_at: "2026-03-19T00:04:00Z",
        updated_at: "2026-03-19T00:04:00Z",
        deleted_at: null,
      },
      revision: {
        id: "revision-1",
        user_id: "user-1",
        memory_id: "memory-1",
        sequence_no: 1,
        action: "ADD",
        memory_key: "user.preference.supplement.magnesium",
        previous_value: null,
        new_value: {
          merchant: "Thorne",
        },
        source_event_ids: ["event-result-1", "event-request-1"],
        candidate: {
          memory_key: "user.preference.supplement.magnesium",
          value: {
            merchant: "Thorne",
          },
          source_event_ids: ["event-result-1", "event-request-1"],
          delete_requested: false,
        },
        created_at: "2026-03-19T00:04:00Z",
      },
    });

    render(
      <ApprovalDetail
        initialApproval={approval}
        detailSource="live"
        initialExecution={execution}
        executionSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

    fireEvent.change(screen.getByLabelText("Memory key"), {
      target: { value: "user.preference.supplement.magnesium" },
    });
    fireEvent.change(screen.getByLabelText("Memory value (JSON)"), {
      target: { value: '{"merchant":"Thorne"}' },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit memory write-back" }));

    await waitFor(() => {
      expect(admitMemoryMock).toHaveBeenCalledWith("https://api.example.com", {
        user_id: "user-1",
        memory_key: "user.preference.supplement.magnesium",
        value: {
          merchant: "Thorne",
        },
        source_event_ids: ["event-result-1", "event-request-1"],
        delete_requested: false,
      });
    });

    expect(refreshMock).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("ADD persisted at revision 1.")).toBeInTheDocument();
  });

  it("shows validation feedback for invalid JSON before submitting", () => {
    render(
      <ApprovalDetail
        initialApproval={approval}
        detailSource="live"
        initialExecution={execution}
        executionSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

    fireEvent.change(screen.getByLabelText("Memory key"), {
      target: { value: "user.preference.supplement.magnesium" },
    });
    fireEvent.change(screen.getByLabelText("Memory value (JSON)"), {
      target: { value: "not-json" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit memory write-back" }));

    expect(admitMemoryMock).not.toHaveBeenCalled();
    expect(screen.getByText("Memory value must be valid JSON.")).toBeInTheDocument();
  });

  it("keeps write-back read-only in fixture workflow mode", () => {
    render(
      <ApprovalDetail
        initialApproval={approval}
        detailSource="fixture"
        initialExecution={execution}
        executionSource="fixture"
      />,
    );

    expect(screen.getByRole("button", { name: "Submit memory write-back" })).toBeDisabled();
    expect(
      screen.getByText("Memory write-back is disabled until live API configuration is present."),
    ).toBeInTheDocument();
  });
});
