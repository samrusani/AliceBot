import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  approvalFixtures,
  executionFixtures,
  getFixtureTaskStepSummary,
  getFixtureTaskSteps,
  taskFixtures,
  threadFixtures,
} from "../lib/fixtures";
import { ThreadWorkflowPanel } from "./thread-workflow-panel";

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

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: vi.fn(),
  }),
}));

describe("ThreadWorkflowPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders embedded approval and task review for a thread with linked workflow", () => {
    render(
      <ThreadWorkflowPanel
        thread={threadFixtures[1]}
        approval={approvalFixtures[1]}
        approvalSource="fixture"
        task={taskFixtures[1]}
        taskSource="fixture"
        execution={executionFixtures[0]}
        executionSource="fixture"
        taskSteps={getFixtureTaskSteps(taskFixtures[1].id)}
        taskStepSummary={getFixtureTaskStepSummary(taskFixtures[1].id)}
        taskStepSource="fixture"
      />,
    );

    expect(screen.getByText("Governed workflow review")).toBeInTheDocument();
    expect(screen.getByText("Fixture workflow")).toBeInTheDocument();
    expect(screen.getByText("Approval: approved")).toBeInTheDocument();
    expect(screen.getByText("Task: executed")).toBeInTheDocument();
    expect(screen.getByText("Execution: completed")).toBeInTheDocument();
    expect(screen.getByText("Approval detail")).toBeInTheDocument();
    expect(screen.getByText("Selected task")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Executed" })).toBeDisabled();
    expect(screen.getByText("Open linked approval")).toBeInTheDocument();
    expect(screen.getByText("Ordered lifecycle steps")).toBeInTheDocument();
    expect(screen.getByText("1 steps")).toBeInTheDocument();
  });

  it("shows an explicit empty state when the selected thread has no linked workflow", () => {
    render(
      <ThreadWorkflowPanel
        thread={threadFixtures[2]}
        approval={null}
        approvalSource="fixture"
        task={null}
        taskSource="fixture"
        execution={null}
        executionSource={null}
      />,
    );

    expect(screen.getByText("No governed workflow linked yet")).toBeInTheDocument();
    expect(
      screen.getByText(/When this thread produces an approval-gated request/i),
    ).toBeInTheDocument();
  });

  it("renders partial unavailable states without hiding the rest of the live workflow review", () => {
    render(
      <ThreadWorkflowPanel
        thread={threadFixtures[0]}
        approval={null}
        approvalSource="unavailable"
        approvalUnavailableReason="Approval API timed out."
        task={taskFixtures[0]}
        taskSource="live"
        execution={null}
        executionSource="unavailable"
        executionUnavailableReason="Execution API timed out."
        taskSteps={[]}
        taskStepSummary={null}
        taskStepSource="unavailable"
        taskStepUnavailableReason="Task step API timed out."
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

    expect(screen.getByText("Partial workflow review")).toBeInTheDocument();
    expect(screen.getByText("Approval review unavailable")).toBeInTheDocument();
    expect(screen.getByText("Approval API timed out.")).toBeInTheDocument();
    expect(screen.getByText("Selected task")).toBeInTheDocument();
    expect(screen.getByText("Task-step timeline unavailable")).toBeInTheDocument();
    expect(screen.getByText("Task step API timed out.")).toBeInTheDocument();
    expect(screen.getByText("Execution review could not be loaded")).toBeInTheDocument();
    expect(screen.getByText("Execution API timed out.")).toBeInTheDocument();
  });

  it("shows execution review inside task summary when approval detail is absent but execution data exists", () => {
    render(
      <ThreadWorkflowPanel
        thread={threadFixtures[1]}
        approval={null}
        approvalSource="fixture"
        task={taskFixtures[1]}
        taskSource="fixture"
        execution={executionFixtures[0]}
        executionSource="fixture"
        taskSteps={getFixtureTaskSteps(taskFixtures[1].id)}
        taskStepSummary={getFixtureTaskStepSummary(taskFixtures[1].id)}
        taskStepSource="fixture"
      />,
    );

    expect(screen.getByText("Selected task")).toBeInTheDocument();
    expect(screen.getByText("Execution review")).toBeInTheDocument();
    expect(screen.getByText("Execution record in review")).toBeInTheDocument();
    expect(screen.getByText("Fixture execution detail")).toBeInTheDocument();
  });
});
