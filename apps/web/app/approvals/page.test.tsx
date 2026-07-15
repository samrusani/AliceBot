import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ApprovalsPage from "./page";

const {
  getApiConfigMock,
  getApprovalDetailMock,
  getToolExecutionMock,
  hasLiveApiConfigMock,
  legacySurfacesEnabledMock,
  listApprovalsMock,
  listToolExecutionsMock,
  notFoundMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getApprovalDetailMock: vi.fn(),
  getToolExecutionMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  legacySurfacesEnabledMock: vi.fn(),
  listApprovalsMock: vi.fn(),
  listToolExecutionsMock: vi.fn(),
  notFoundMock: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  notFound: notFoundMock,
  useRouter: () => ({ refresh: vi.fn() }),
}));

vi.mock("../../lib/legacy-surfaces.server", () => ({
  legacySurfacesEnabled: legacySurfacesEnabledMock,
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getApprovalDetail: getApprovalDetailMock,
    getToolExecution: getToolExecutionMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listApprovals: listApprovalsMock,
    listToolExecutions: listToolExecutionsMock,
  };
});

const liveApproval = {
  id: "approval-live-1",
  thread_id: "thread-live-1",
  task_run_id: null,
  task_step_id: null,
  status: "approved",
  request: {
    thread_id: "thread-live-1",
    tool_id: "tool-live-1",
    action: "publish_release",
    scope: "repository",
    domain_hint: "engineering",
    risk_hint: "external_write",
    attributes: {},
  },
  tool: {
    id: "tool-live-1",
    tool_key: "release.publisher",
    name: "Release Publisher",
    description: "Publishes a release",
    version: "1.0.0",
    metadata_version: "tool_metadata_v0",
    active: true,
    tags: [],
    action_hints: [],
    scope_hints: [],
    domain_hints: [],
    risk_hints: [],
    metadata: {},
    created_at: "2026-07-13T10:00:00Z",
  },
  routing: { decision: "require_approval", reasons: [], trace: { trace_id: "trace-1", trace_event_count: 1 } },
  created_at: "2026-07-13T10:00:00Z",
  resolution: { resolved_at: "2026-07-13T10:01:00Z", resolved_by_user_id: "user-1" },
};

describe("ApprovalsPage", () => {
  beforeEach(() => {
    for (const mock of [
      getApiConfigMock,
      getApprovalDetailMock,
      getToolExecutionMock,
      hasLiveApiConfigMock,
      legacySurfacesEnabledMock,
      listApprovalsMock,
      listToolExecutionsMock,
      notFoundMock,
    ]) {
      mock.mockReset();
    }
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "", userId: "" });
    hasLiveApiConfigMock.mockReturnValue(false);
    legacySurfacesEnabledMock.mockReturnValue(true);
    notFoundMock.mockImplementation(() => {
      throw new Error("NEXT_NOT_FOUND");
    });
  });

  afterEach(cleanup);

  it("returns not found before any reads when legacy surfaces are disabled", async () => {
    legacySurfacesEnabledMock.mockReturnValue(false);

    await expect(ApprovalsPage({ searchParams: Promise.resolve({}) })).rejects.toThrow(
      "NEXT_NOT_FOUND",
    );
    expect(notFoundMock).toHaveBeenCalledOnce();
    expect(listApprovalsMock).not.toHaveBeenCalled();
  });

  it("renders an explicit fixture-backed inbox without issuing live reads", async () => {
    render(await ApprovalsPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Approval inbox and review" })).toBeInTheDocument();
    expect(listApprovalsMock).not.toHaveBeenCalled();
  });

  it("uses live list, detail, and execution reads when configured", async () => {
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "https://api.example.com", userId: "user-1" });
    hasLiveApiConfigMock.mockReturnValue(true);
    listApprovalsMock.mockResolvedValue({ items: [liveApproval] });
    getApprovalDetailMock.mockResolvedValue({ approval: liveApproval });
    listToolExecutionsMock.mockResolvedValue({
      items: [{ id: "execution-1", approval_id: liveApproval.id, status: "completed" }],
    });
    getToolExecutionMock.mockResolvedValue({
      execution: { id: "execution-1", approval_id: liveApproval.id, status: "completed" },
    });

    render(
      await ApprovalsPage({
        searchParams: Promise.resolve({ approval: liveApproval.id }),
      }),
    );

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getAllByText("Release Publisher").length).toBeGreaterThan(0);
    expect(getApprovalDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      liveApproval.id,
      "user-1",
    );
    expect(getToolExecutionMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "execution-1",
      "user-1",
    );
  });

  it("falls back visibly when the live approval list fails", async () => {
    getApiConfigMock.mockReturnValue({ apiBaseUrl: "https://api.example.com", userId: "user-1" });
    hasLiveApiConfigMock.mockReturnValue(true);
    listApprovalsMock.mockRejectedValue(new Error("backend unavailable"));

    render(await ApprovalsPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText(/total approvals/i)).toBeInTheDocument();
  });
});
