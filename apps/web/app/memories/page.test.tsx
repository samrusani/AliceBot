import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import MemoriesPage from "./page";

const {
  getApiConfigMock,
  getMemoryDetailMock,
  getMemoryEvaluationSummaryMock,
  getMemoryTrustDashboardMock,
  getMemoryRevisionsMock,
  getOpenLoopDetailMock,
  hasLiveApiConfigMock,
  listMemoriesMock,
  listMemoryLabelsMock,
  listOpenLoopsMock,
  listMemoryReviewQueueMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getMemoryDetailMock: vi.fn(),
  getMemoryEvaluationSummaryMock: vi.fn(),
  getMemoryTrustDashboardMock: vi.fn(),
  getMemoryRevisionsMock: vi.fn(),
  getOpenLoopDetailMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listMemoriesMock: vi.fn(),
  listMemoryLabelsMock: vi.fn(),
  listOpenLoopsMock: vi.fn(),
  listMemoryReviewQueueMock: vi.fn(),
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

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: vi.fn(),
  }),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getMemoryDetail: getMemoryDetailMock,
    getMemoryEvaluationSummary: getMemoryEvaluationSummaryMock,
    getMemoryTrustDashboard: getMemoryTrustDashboardMock,
    getMemoryRevisions: getMemoryRevisionsMock,
    getOpenLoopDetail: getOpenLoopDetailMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listMemories: listMemoriesMock,
    listMemoryLabels: listMemoryLabelsMock,
    listOpenLoops: listOpenLoopsMock,
    listMemoryReviewQueue: listMemoryReviewQueueMock,
  };
});

describe("MemoriesPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getMemoryDetailMock.mockReset();
    getMemoryEvaluationSummaryMock.mockReset();
    getMemoryTrustDashboardMock.mockReset();
    getMemoryRevisionsMock.mockReset();
    getOpenLoopDetailMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listMemoriesMock.mockReset();
    listMemoryLabelsMock.mockReset();
    listOpenLoopsMock.mockReset();
    listMemoryReviewQueueMock.mockReset();

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

  it("uses fixture-backed memory workspace state when live API config is absent", async () => {
    render(await MemoriesPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Summary Fixture")).toBeInTheDocument();
    expect(screen.getByText("Canonical quality posture")).toBeInTheDocument();
    expect(screen.getByText(/Fixture dashboard/)).toBeInTheDocument();
    expect(screen.getByText("Queue Fixture")).toBeInTheDocument();
    expect(screen.getAllByText("Insufficient sample").length).toBeGreaterThan(0);
    expect(screen.getByText("Fixture list")).toBeInTheDocument();
    expect(screen.getByText("Fixture detail")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Label submission is unavailable until live API configuration and live memory detail are present.",
      ),
    ).toBeInTheDocument();
    expect(listMemoriesMock).not.toHaveBeenCalled();
  });

  it("renders live-backed memory summary, detail, revisions, and labels when live reads succeed", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listMemoriesMock.mockResolvedValue({
      items: [
        {
          id: "memory-live-1",
          memory_key: "user.preference.live",
          value: { merchant: "Live Merchant" },
          status: "active",
          source_event_ids: ["event-live-1"],
          created_at: "2026-03-18T10:00:00Z",
          updated_at: "2026-03-18T10:05:00Z",
          deleted_at: null,
        },
      ],
      summary: {
        status: "active",
        limit: 20,
        returned_count: 1,
        total_count: 1,
        has_more: false,
        order: ["updated_at_desc", "created_at_desc", "id_desc"],
      },
    });
    listMemoryReviewQueueMock.mockResolvedValue({
      items: [],
      summary: {
        memory_status: "active",
        review_state: "unlabeled",
        priority_mode: "recent_first",
        available_priority_modes: [
          "oldest_first",
          "recent_first",
          "high_risk_first",
          "stale_truth_first",
        ],
        limit: 20,
        returned_count: 0,
        total_count: 0,
        has_more: false,
        order: ["updated_at_desc", "created_at_desc", "id_desc"],
      },
    });
    getMemoryEvaluationSummaryMock.mockResolvedValue({
      summary: {
        total_memory_count: 10,
        active_memory_count: 10,
        deleted_memory_count: 0,
        labeled_memory_count: 10,
        unlabeled_memory_count: 0,
        total_label_row_count: 10,
        label_row_counts_by_value: {
          correct: 8,
          incorrect: 2,
          outdated: 0,
          insufficient_evidence: 0,
        },
        label_value_order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
        quality_gate: {
          status: "healthy",
          precision: 0.8,
          precision_target: 0.8,
          adjudicated_sample_count: 10,
          minimum_adjudicated_sample: 10,
          remaining_to_minimum_sample: 0,
          unlabeled_memory_count: 0,
          high_risk_memory_count: 0,
          stale_truth_count: 0,
          superseded_active_conflict_count: 0,
          counts: {
            active_memory_count: 10,
            labeled_active_memory_count: 10,
            adjudicated_correct_count: 8,
            adjudicated_incorrect_count: 2,
            outdated_label_count: 0,
            insufficient_evidence_label_count: 0,
          },
        },
      },
    });
    getMemoryTrustDashboardMock.mockResolvedValue({
      dashboard: {
        quality_gate: {
          status: "needs_review",
          precision: 0.8,
          precision_target: 0.8,
          adjudicated_sample_count: 10,
          minimum_adjudicated_sample: 10,
          remaining_to_minimum_sample: 0,
          unlabeled_memory_count: 2,
          high_risk_memory_count: 1,
          stale_truth_count: 1,
          superseded_active_conflict_count: 0,
          counts: {
            active_memory_count: 12,
            labeled_active_memory_count: 10,
            adjudicated_correct_count: 8,
            adjudicated_incorrect_count: 2,
            outdated_label_count: 0,
            insufficient_evidence_label_count: 0,
          },
        },
        queue_posture: {
          priority_mode: "recent_first",
          total_count: 2,
          high_risk_count: 1,
          stale_truth_count: 1,
          priority_reason_counts: { recent_first: 2 },
          order: ["updated_at_desc", "created_at_desc", "id_desc"],
          aging: {
            anchor_updated_at: "2026-03-23T09:00:00Z",
            newest_updated_at: "2026-03-23T09:00:00Z",
            oldest_updated_at: "2026-03-22T09:00:00Z",
            backlog_span_hours: 24,
            fresh_within_24h_count: 2,
            aging_24h_to_72h_count: 0,
            stale_over_72h_count: 0,
          },
        },
        retrieval_quality: {
          fixture_count: 3,
          evaluated_fixture_count: 3,
          passing_fixture_count: 3,
          precision_at_k_mean: 1,
          precision_at_1_mean: 1,
          precision_target: 0.8,
          status: "pass",
          fixture_order: ["fixture_id_asc"],
          result_order: ["precision_at_k_desc", "fixture_id_asc"],
        },
        correction_freshness: {
          total_open_loop_count: 1,
          stale_open_loop_count: 0,
          correction_recurrence_count: 0,
          freshness_drift_count: 0,
        },
        recommended_review: {
          priority_mode: "high_risk_first",
          action: "review_high_risk_queue",
          reason: "High-risk unlabeled memories are present; triage those before lower-risk backlog.",
        },
        sources: [
          "memories",
          "memory_review_labels",
          "continuity_recall",
          "continuity_correction_events",
          "retrieval_evaluation_fixtures",
        ],
      },
    });
    listOpenLoopsMock.mockResolvedValue({
      items: [
        {
          id: "loop-live-1",
          memory_id: "memory-live-1",
          title: "Confirm merchant details",
          status: "open",
          opened_at: "2026-03-23T09:00:00Z",
          due_at: "2026-03-25T09:00:00Z",
          resolved_at: null,
          resolution_note: null,
          created_at: "2026-03-23T09:00:00Z",
          updated_at: "2026-03-23T09:00:00Z",
        },
      ],
      summary: {
        status: "open",
        limit: 20,
        returned_count: 1,
        total_count: 1,
        has_more: false,
        order: ["opened_at_desc", "created_at_desc", "id_desc"],
      },
    });
    getOpenLoopDetailMock.mockResolvedValue({
      open_loop: {
        id: "loop-live-1",
        memory_id: "memory-live-1",
        title: "Confirm merchant details",
        status: "open",
        opened_at: "2026-03-23T09:00:00Z",
        due_at: "2026-03-25T09:00:00Z",
        resolved_at: null,
        resolution_note: null,
        created_at: "2026-03-23T09:00:00Z",
        updated_at: "2026-03-23T09:00:00Z",
      },
    });
    getMemoryDetailMock.mockResolvedValue({
      memory: {
        id: "memory-live-1",
        memory_key: "user.preference.live",
        value: { merchant: "Live Merchant", note: "Verified" },
        status: "active",
        source_event_ids: ["event-live-1"],
        memory_type: "decision",
        confidence: 0.93,
        salience: 0.81,
        confirmation_status: "confirmed",
        valid_from: "2026-03-01T00:00:00Z",
        valid_to: "2026-12-31T00:00:00Z",
        last_confirmed_at: "2026-03-20T00:00:00Z",
        created_at: "2026-03-18T10:00:00Z",
        updated_at: "2026-03-18T10:05:00Z",
        deleted_at: null,
      },
    });
    getMemoryRevisionsMock.mockResolvedValue({
      items: [
        {
          id: "revision-live-1",
          memory_id: "memory-live-1",
          sequence_no: 1,
          action: "ADD",
          memory_key: "user.preference.live",
          previous_value: null,
          new_value: { merchant: "Live Merchant" },
          source_event_ids: ["event-live-1"],
          created_at: "2026-03-18T10:00:00Z",
        },
      ],
      summary: {
        memory_id: "memory-live-1",
        limit: 20,
        returned_count: 1,
        total_count: 1,
        has_more: false,
        order: ["sequence_no_asc"],
      },
    });
    listMemoryLabelsMock.mockResolvedValue({
      items: [
        {
          id: "label-live-1",
          memory_id: "memory-live-1",
          reviewer_user_id: "user-1",
          label: "correct",
          note: "Confirmed",
          created_at: "2026-03-18T10:06:00Z",
        },
      ],
      summary: {
        memory_id: "memory-live-1",
        total_count: 1,
        counts_by_label: {
          correct: 1,
          incorrect: 0,
          outdated: 0,
          insufficient_evidence: 0,
        },
        order: ["correct", "incorrect", "outdated", "insufficient_evidence"],
      },
    });

    render(
      await MemoriesPage({
        searchParams: Promise.resolve({
          memory: "memory-live-1",
        }),
      }),
    );

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText("Summary Live")).toBeInTheDocument();
    expect(screen.getByText(/Live dashboard/)).toBeInTheDocument();
    expect(screen.getByText("review_high_risk_queue")).toBeInTheDocument();
    expect(screen.getByText("Queue Live")).toBeInTheDocument();
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.getByText("Live list")).toBeInTheDocument();
    expect(screen.getByText("Live detail")).toBeInTheDocument();
    expect(screen.getByText("Live revisions")).toBeInTheDocument();
    expect(screen.getByText("Live labels")).toBeInTheDocument();
    expect(screen.getByText("Typed metadata")).toBeInTheDocument();
    expect(screen.getByText("Open-loop backbone")).toBeInTheDocument();
    expect(screen.getByText("Confirm merchant details")).toBeInTheDocument();
    expect(screen.getByText("decision")).toBeInTheDocument();
    expect(screen.getByText("confirmed")).toBeInTheDocument();
    expect(screen.getByText("0.93")).toBeInTheDocument();
    expect(screen.getByText("0.81")).toBeInTheDocument();
    expect(screen.getByText("2026-03-01T00:00:00Z")).toBeInTheDocument();
    expect(screen.getByText("2026-12-31T00:00:00Z")).toBeInTheDocument();
    expect(screen.getByText("2026-03-20T00:00:00Z")).toBeInTheDocument();

    expect(listMemoriesMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      status: "active",
    });
    expect(getMemoryDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "memory-live-1",
      "user-1",
    );
    expect(listOpenLoopsMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      status: "open",
      limit: 20,
    });
    expect(listMemoryReviewQueueMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      priorityMode: "recent_first",
    });
    expect(getMemoryTrustDashboardMock).toHaveBeenCalledWith("https://api.example.com", "user-1");
  });

  it("keeps fallback state explicit when live reads partially fail and shows unavailable revision/label panels", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listMemoriesMock.mockResolvedValue({
      items: [
        {
          id: "memory-live-missing",
          memory_key: "user.preference.live.missing",
          value: { merchant: "Unknown" },
          status: "active",
          source_event_ids: ["event-live-missing"],
          created_at: "2026-03-18T10:00:00Z",
          updated_at: "2026-03-18T10:05:00Z",
          deleted_at: null,
        },
      ],
      summary: {
        status: "active",
        limit: 20,
        returned_count: 1,
        total_count: 1,
        has_more: false,
        order: ["updated_at_desc", "created_at_desc", "id_desc"],
      },
    });
    listMemoryReviewQueueMock.mockRejectedValue(new Error("queue down"));
    getMemoryEvaluationSummaryMock.mockRejectedValue(new Error("summary down"));
    getMemoryTrustDashboardMock.mockRejectedValue(new Error("trust dashboard down"));
    listOpenLoopsMock.mockRejectedValue(new Error("open loops down"));
    getMemoryDetailMock.mockRejectedValue(new Error("detail down"));
    getMemoryRevisionsMock.mockRejectedValue(new Error("revisions down"));
    listMemoryLabelsMock.mockRejectedValue(new Error("labels down"));

    render(
      await MemoriesPage({
        searchParams: Promise.resolve({
          memory: "memory-live-missing",
        }),
      }),
    );

    expect(screen.getByText("Summary: summary down")).toBeInTheDocument();
    expect(screen.getByText(/trust dashboard down/)).toBeInTheDocument();
    expect(screen.getByText("Queue: queue down")).toBeInTheDocument();
    expect(screen.getByText(/open loops down/)).toBeInTheDocument();
    expect(screen.getAllByText("Insufficient sample").length).toBeGreaterThan(0);
    expect(screen.getByText("Detail read")).toBeInTheDocument();
    expect(screen.getByText("detail down")).toBeInTheDocument();
    expect(screen.getByText("Revisions unavailable")).toBeInTheDocument();
    expect(screen.getByText("revisions down")).toBeInTheDocument();
    expect(screen.getByText("Labels unavailable")).toBeInTheDocument();
    expect(screen.getByText("labels down")).toBeInTheDocument();
  });

  it("shows queue submit-and-next action only when queue mode has a deterministic next item", async () => {
    render(
      await MemoriesPage({
        searchParams: Promise.resolve({
          filter: "queue",
        }),
      }),
    );

    expect(screen.getByRole("button", { name: "Submit review label" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit and next in queue" })).toBeInTheDocument();
  });

  it("hides queue submit-and-next action when selected queue item is last in current order", async () => {
    render(
      await MemoriesPage({
        searchParams: Promise.resolve({
          filter: "queue",
          memory: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3",
        }),
      }),
    );

    expect(screen.getByRole("button", { name: "Submit review label" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit and next in queue" }),
    ).not.toBeInTheDocument();
  });
});
