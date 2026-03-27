import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TasksPage from "./page";
import { taskFixtures } from "../../lib/fixtures";

const {
  getApiConfigMock,
  getTaskDetailMock,
  getTaskStepsMock,
  getToolExecutionMock,
  hasLiveApiConfigMock,
  listTaskRunsMock,
  listTasksMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getTaskDetailMock: vi.fn(),
  getTaskStepsMock: vi.fn(),
  getToolExecutionMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listTaskRunsMock: vi.fn(),
  listTasksMock: vi.fn(),
}));

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

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getTaskDetail: getTaskDetailMock,
    getTaskSteps: getTaskStepsMock,
    getToolExecution: getToolExecutionMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listTaskRuns: listTaskRunsMock,
    listTasks: listTasksMock,
  };
});

describe("TasksPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getTaskDetailMock.mockReset();
    getTaskStepsMock.mockReset();
    getToolExecutionMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listTaskRunsMock.mockReset();
    listTasksMock.mockReset();

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "",
      userId: "",
      defaultThreadId: "",
      defaultToolId: "",
    });
    hasLiveApiConfigMock.mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
  });

  it("shows fixture task-run review when live API config is absent", async () => {
    render(await TasksPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Durable run review")).toBeInTheDocument();
    expect(screen.getByText("Fixture run state")).toBeInTheDocument();
    expect(screen.getByText("Run fixture-run-33333333-3333-4333-8333-333333333333")).toBeInTheDocument();
    expect(listTaskRunsMock).not.toHaveBeenCalled();
  });

  it("shows live task-run rows when live task-run read succeeds", async () => {
    const selected = taskFixtures[0];
    if (!selected) {
      throw new Error("Expected task fixtures to contain at least one task.");
    }

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);

    listTasksMock.mockResolvedValue({
      items: [selected],
      summary: { total_count: 1, order: ["created_at_asc", "id_asc"] },
    });
    getTaskDetailMock.mockResolvedValue({ task: selected });
    getTaskStepsMock.mockResolvedValue({
      items: [],
      summary: {
        task_id: selected.id,
        total_count: 0,
        latest_sequence_no: null,
        latest_status: null,
        next_sequence_no: 1,
        append_allowed: false,
        order: ["sequence_no_asc", "created_at_asc", "id_asc"],
      },
    });
    listTaskRunsMock.mockResolvedValue({
      items: [
        {
          id: "run-live-1",
          task_id: selected.id,
          status: "running",
          checkpoint: { cursor: 1, target_steps: 3, wait_for_signal: false },
          tick_count: 1,
          step_count: 1,
          max_ticks: 3,
          stop_reason: null,
          created_at: selected.created_at,
          updated_at: selected.updated_at,
        },
      ],
      summary: {
        task_id: selected.id,
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    render(await TasksPage({ searchParams: Promise.resolve({ task: selected.id }) }));

    expect(screen.getByText("Live run state")).toBeInTheDocument();
    expect(screen.getByText("Run run-live-1")).toBeInTheDocument();
    expect(listTaskRunsMock).toHaveBeenCalledWith("https://api.example.com", selected.id, "user-1");
  });

  it("shows unavailable run state when live task-run read fails", async () => {
    const selected = taskFixtures[0];
    if (!selected) {
      throw new Error("Expected task fixtures to contain at least one task.");
    }

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);

    listTasksMock.mockResolvedValue({
      items: [selected],
      summary: { total_count: 1, order: ["created_at_asc", "id_asc"] },
    });
    getTaskDetailMock.mockResolvedValue({ task: selected });
    getTaskStepsMock.mockResolvedValue({
      items: [],
      summary: {
        task_id: selected.id,
        total_count: 0,
        latest_sequence_no: null,
        latest_status: null,
        next_sequence_no: 1,
        append_allowed: false,
        order: ["sequence_no_asc", "created_at_asc", "id_asc"],
      },
    });
    listTaskRunsMock.mockRejectedValue(new Error("run backend unavailable"));

    render(await TasksPage({ searchParams: Promise.resolve({ task: selected.id }) }));

    expect(screen.getByText("Run review unavailable")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(
      screen.getByText("The task-run records could not be read from the configured backend."),
    ).toBeInTheDocument();
  });
});
