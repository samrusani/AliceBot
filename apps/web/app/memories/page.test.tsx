import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import MemoriesPage from "./page";

const {
  getApiConfigMock,
  getMemoryDetailMock,
  getMemoryEvaluationSummaryMock,
  getMemoryRevisionsMock,
  hasLiveApiConfigMock,
  listMemoriesMock,
  listMemoryLabelsMock,
  listMemoryReviewQueueMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getMemoryDetailMock: vi.fn(),
  getMemoryEvaluationSummaryMock: vi.fn(),
  getMemoryRevisionsMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listMemoriesMock: vi.fn(),
  listMemoryLabelsMock: vi.fn(),
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
    getMemoryRevisions: getMemoryRevisionsMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listMemories: listMemoriesMock,
    listMemoryLabels: listMemoryLabelsMock,
    listMemoryReviewQueue: listMemoryReviewQueueMock,
  };
});

describe("MemoriesPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getMemoryDetailMock.mockReset();
    getMemoryEvaluationSummaryMock.mockReset();
    getMemoryRevisionsMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listMemoriesMock.mockReset();
    listMemoryLabelsMock.mockReset();
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
    expect(screen.getByText("Queue Fixture")).toBeInTheDocument();
    expect(screen.getAllByText("Insufficient evidence").length).toBeGreaterThan(0);
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
      },
    });
    getMemoryDetailMock.mockResolvedValue({
      memory: {
        id: "memory-live-1",
        memory_key: "user.preference.live",
        value: { merchant: "Live Merchant", note: "Verified" },
        status: "active",
        source_event_ids: ["event-live-1"],
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
    expect(screen.getByText("Queue Live")).toBeInTheDocument();
    expect(screen.getByText("On track")).toBeInTheDocument();
    expect(screen.getByText("Live list")).toBeInTheDocument();
    expect(screen.getByText("Live detail")).toBeInTheDocument();
    expect(screen.getByText("Live revisions")).toBeInTheDocument();
    expect(screen.getByText("Live labels")).toBeInTheDocument();

    expect(listMemoriesMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      status: "active",
    });
    expect(getMemoryDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "memory-live-1",
      "user-1",
    );
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
    expect(screen.getByText("Queue: queue down")).toBeInTheDocument();
    expect(screen.getAllByText("Insufficient evidence").length).toBeGreaterThan(0);
    expect(screen.getByText("Detail read")).toBeInTheDocument();
    expect(screen.getByText("detail down")).toBeInTheDocument();
    expect(screen.getByText("Revisions unavailable")).toBeInTheDocument();
    expect(screen.getByText("revisions down")).toBeInTheDocument();
    expect(screen.getByText("Labels unavailable")).toBeInTheDocument();
    expect(screen.getByText("labels down")).toBeInTheDocument();
  });
});
