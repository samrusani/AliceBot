import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ExecutionSummary } from "./execution-summary";

const execution = {
  id: "execution-1",
  approval_id: "approval-1",
  task_step_id: "step-1",
  thread_id: "thread-1",
  tool_id: "tool-1",
  trace_id: "trace-1",
  request_event_id: "event-1",
  result_event_id: "event-2",
  status: "completed",
  handler_key: "proxy.echo",
  request: {
    thread_id: "thread-1",
    tool_id: "tool-1",
    action: "place_order",
    scope: "supplements",
    domain_hint: "ecommerce",
    risk_hint: "purchase",
    attributes: {
      item: "Magnesium",
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
    created_at: "2026-03-17T00:00:00Z",
  },
  result: {
    handler_key: "proxy.echo",
    status: "completed",
    output: {
      ok: true,
      mode: "no_side_effect",
    },
    reason: null,
  },
  executed_at: "2026-03-17T00:10:00Z",
};

const executionPreview = {
  request: {
    approval_id: "approval-1",
    task_step_id: "step-1",
  },
  approval: {
    id: "approval-1",
    thread_id: "thread-1",
    task_step_id: "step-1",
    status: "approved",
    request: execution.request,
    tool: execution.tool,
    routing: {
      decision: "require_approval",
      reasons: [],
      trace: {
        trace_id: "trace-route-1",
        trace_event_count: 3,
      },
    },
    created_at: "2026-03-17T00:00:00Z",
    resolution: {
      resolved_at: "2026-03-17T00:05:00Z",
      resolved_by_user_id: "user-1",
    },
  },
  tool: execution.tool,
  result: execution.result,
  events: {
    request_event_id: "event-1",
    request_sequence_no: 1,
    result_event_id: "event-2",
    result_sequence_no: 2,
  },
  trace: {
    trace_id: "trace-1",
    trace_event_count: 9,
  },
};

describe("ExecutionSummary", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders the empty execution state", () => {
    render(
      <ExecutionSummary
        execution={null}
        emptyTitle="Task has not executed yet"
        emptyDescription="Execution detail will appear here once the request runs."
      />,
    );

    expect(screen.getByText("Task has not executed yet")).toBeInTheDocument();
    expect(screen.getByText(/Execution detail will appear here/i)).toBeInTheDocument();
    expect(screen.getByText("Not executed")).toBeInTheDocument();
  });

  it("renders a persisted execution record", () => {
    render(
      <ExecutionSummary
        execution={execution}
        source="live"
        emptyTitle="unused"
        emptyDescription="unused"
      />,
    );

    expect(screen.getByText("Execution record in review")).toBeInTheDocument();
    expect(screen.getByText("Live execution detail")).toBeInTheDocument();
    expect(screen.getByText("Merchant Proxy")).toBeInTheDocument();
    expect(screen.getByText(/"mode": "no_side_effect"/i)).toBeInTheDocument();
  });

  it("renders an unavailable message instead of implying no execution", () => {
    render(
      <ExecutionSummary
        execution={null}
        unavailableMessage="The execution API did not return a usable record."
        emptyTitle="unused"
        emptyDescription="unused"
      />,
    );

    expect(screen.getByText("Execution review could not be loaded")).toBeInTheDocument();
    expect(screen.getByText(/did not return a usable record/i)).toBeInTheDocument();
  });

  it("prefers a fresh execute preview over a stale unavailable message", () => {
    render(
      <ExecutionSummary
        execution={null}
        preview={executionPreview}
        unavailableMessage="The execution API did not return a usable record."
        emptyTitle="unused"
        emptyDescription="unused"
      />,
    );

    expect(screen.getByText("Latest execution result")).toBeInTheDocument();
    expect(screen.getByText("Latest execute response")).toBeInTheDocument();
    expect(screen.queryByText("Execution review could not be loaded")).not.toBeInTheDocument();
  });
});
