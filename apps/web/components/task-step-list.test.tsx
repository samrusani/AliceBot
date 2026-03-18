import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getFixtureTaskStepSummary, getFixtureTaskSteps } from "../lib/fixtures";
import { TaskStepList } from "./task-step-list";

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

describe("TaskStepList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders an ordered task-step timeline with summary pills and linked approval state", () => {
    const taskId = "33333333-3333-4333-8333-333333333334";
    render(
      <TaskStepList
        steps={getFixtureTaskSteps(taskId)}
        summary={getFixtureTaskStepSummary(taskId)}
        source="fixture"
      />,
    );

    expect(screen.getByText("Ordered lifecycle steps")).toBeInTheDocument();
    expect(screen.getByText("1 steps")).toBeInTheDocument();
    expect(screen.getByText("Step 1")).toBeInTheDocument();
    expect(screen.getByText("place_order / supplements")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "approved" })).toHaveAttribute(
      "href",
      "/approvals?approval=44444444-4444-4444-8444-444444444445",
    );
  });

  it("shows an explicit empty state when the selected task has no steps", () => {
    render(<TaskStepList steps={[]} summary={null} source="live" />);

    expect(screen.getByText("No task steps available")).toBeInTheDocument();
    expect(screen.getByText(/Select a task with step records/i)).toBeInTheDocument();
  });

  it("supports embedded chrome for bounded timeline rendering", () => {
    const taskId = "33333333-3333-4333-8333-333333333333";
    const { container } = render(
      <TaskStepList
        steps={getFixtureTaskSteps(taskId)}
        summary={getFixtureTaskStepSummary(taskId)}
        source="fixture"
        chrome="embedded"
      />,
    );

    const card = container.querySelector(".task-step-list");
    expect(card).toHaveClass("section-card--embedded");
    expect(card).toHaveClass("task-step-list--embedded");
  });
});
