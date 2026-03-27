import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { TaskRunList } from "./task-run-list";

const task = {
  id: "33333333-3333-4333-8333-333333333333",
  thread_id: "11111111-1111-4111-8111-111111111111",
  tool_id: "22222222-2222-4222-8222-222222222222",
  status: "approved",
  request: {
    thread_id: "11111111-1111-4111-8111-111111111111",
    tool_id: "22222222-2222-4222-8222-222222222222",
    action: "tool.run",
    scope: "workspace",
    domain_hint: null,
    risk_hint: null,
    attributes: {},
  },
  tool: {
    id: "22222222-2222-4222-8222-222222222222",
    tool_key: "proxy.echo",
    name: "Proxy Echo",
    description: "Deterministic proxy handler.",
    version: "1.0.0",
    metadata_version: "tool_metadata_v0",
    active: true,
    tags: ["proxy"],
    action_hints: ["tool.run"],
    scope_hints: ["workspace"],
    domain_hints: [],
    risk_hints: [],
    metadata: {},
    created_at: "2026-03-17T00:00:00Z",
  },
  latest_approval_id: "44444444-4444-4444-8444-444444444444",
  latest_execution_id: null,
  created_at: "2026-03-17T00:00:00Z",
  updated_at: "2026-03-17T00:00:00Z",
};

describe("TaskRunList", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows idle state when no task is selected", () => {
    render(<TaskRunList task={null} runs={[]} source="fixture" />);

    expect(screen.getByText("No task selected")).toBeInTheDocument();
    expect(screen.getByText("Run review is idle")).toBeInTheDocument();
  });

  it("shows unavailable backend state without implying empty runs", () => {
    render(
      <TaskRunList
        task={task}
        runs={[]}
        source="unavailable"
        unavailableMessage="Task-run reads timed out."
      />,
    );

    expect(screen.getByText("Run review unavailable")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("Task-run reads timed out.")).toBeInTheDocument();
  });

  it("renders durable run counters, checkpoint state, and stop reason", () => {
    render(
      <TaskRunList
        task={task}
        source="live"
        runs={[
          {
            id: "run-1",
            task_id: task.id,
            status: "paused",
            checkpoint: {
              cursor: 1,
              target_steps: 3,
              wait_for_signal: false,
            },
            tick_count: 1,
            step_count: 1,
            max_ticks: 1,
            retry_count: 0,
            retry_cap: 1,
            retry_posture: "terminal",
            failure_class: "budget",
            stop_reason: "budget_exhausted",
            last_transitioned_at: "2026-03-27T10:05:00Z",
            created_at: "2026-03-27T10:00:00Z",
            updated_at: "2026-03-27T10:05:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("Durable run review")).toBeInTheDocument();
    expect(screen.getByText("1 runs")).toBeInTheDocument();
    expect(screen.getByText("Live run state")).toBeInTheDocument();
    expect(screen.getByText("Run run-1")).toBeInTheDocument();
    expect(screen.getByText("Tick 1 / 1")).toBeInTheDocument();
    expect(screen.getByText("Stop: budget_exhausted")).toBeInTheDocument();
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByText("false")).toBeInTheDocument();
  });
});
