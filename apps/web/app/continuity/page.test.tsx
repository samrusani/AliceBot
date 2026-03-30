import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ContinuityPage from "./page";

const {
  getApiConfigMock,
  getContinuityDailyBriefMock,
  getContinuityOpenLoopDashboardMock,
  getContinuityCaptureDetailMock,
  getContinuityReviewDetailMock,
  getContinuityResumptionBriefMock,
  getContinuityWeeklyReviewMock,
  hasLiveApiConfigMock,
  listContinuityReviewQueueMock,
  listContinuityCapturesMock,
  queryContinuityRecallMock,
  refreshMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getContinuityDailyBriefMock: vi.fn(),
  getContinuityOpenLoopDashboardMock: vi.fn(),
  getContinuityCaptureDetailMock: vi.fn(),
  getContinuityReviewDetailMock: vi.fn(),
  getContinuityResumptionBriefMock: vi.fn(),
  getContinuityWeeklyReviewMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listContinuityReviewQueueMock: vi.fn(),
  listContinuityCapturesMock: vi.fn(),
  queryContinuityRecallMock: vi.fn(),
  refreshMock: vi.fn(),
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
    refresh: refreshMock,
  }),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getContinuityDailyBrief: getContinuityDailyBriefMock,
    getContinuityOpenLoopDashboard: getContinuityOpenLoopDashboardMock,
    getContinuityCaptureDetail: getContinuityCaptureDetailMock,
    getContinuityReviewDetail: getContinuityReviewDetailMock,
    getContinuityResumptionBrief: getContinuityResumptionBriefMock,
    getContinuityWeeklyReview: getContinuityWeeklyReviewMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listContinuityReviewQueue: listContinuityReviewQueueMock,
    listContinuityCaptures: listContinuityCapturesMock,
    queryContinuityRecall: queryContinuityRecallMock,
  };
});

describe("ContinuityPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getContinuityDailyBriefMock.mockReset();
    getContinuityOpenLoopDashboardMock.mockReset();
    getContinuityCaptureDetailMock.mockReset();
    getContinuityReviewDetailMock.mockReset();
    getContinuityResumptionBriefMock.mockReset();
    getContinuityWeeklyReviewMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listContinuityReviewQueueMock.mockReset();
    listContinuityCapturesMock.mockReset();
    queryContinuityRecallMock.mockReset();
    refreshMock.mockReset();

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

  it("uses fixture continuity state when live API config is absent", async () => {
    render(await ContinuityPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Fixture inbox")).toBeInTheDocument();
    expect(screen.getByText("Fixture recall")).toBeInTheDocument();
    expect(screen.getByText("Fixture brief")).toBeInTheDocument();
    expect(screen.getByText("Fixture open loops")).toBeInTheDocument();
    expect(screen.getByText("Fixture daily brief")).toBeInTheDocument();
    expect(screen.getByText("Fixture weekly review")).toBeInTheDocument();
    expect(screen.getByText("Fixture review queue")).toBeInTheDocument();
    expect(screen.getByText("Continuity recall")).toBeInTheDocument();
    expect(screen.getAllByText("Correction actions").length).toBeGreaterThan(0);
    expect(listContinuityCapturesMock).not.toHaveBeenCalled();
    expect(queryContinuityRecallMock).not.toHaveBeenCalled();
    expect(getContinuityResumptionBriefMock).not.toHaveBeenCalled();
    expect(getContinuityOpenLoopDashboardMock).not.toHaveBeenCalled();
    expect(getContinuityDailyBriefMock).not.toHaveBeenCalled();
    expect(getContinuityWeeklyReviewMock).not.toHaveBeenCalled();
    expect(listContinuityReviewQueueMock).not.toHaveBeenCalled();
  });

  it("renders live continuity inbox, recall, and resumption when reads succeed", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    listContinuityCapturesMock.mockResolvedValue({
      items: [
        {
          capture_event: {
            id: "capture-live-1",
            raw_content: "Decision: Keep admission conservative",
            explicit_signal: null,
            admission_posture: "DERIVED",
            admission_reason: "high_confidence_prefix_decision",
            created_at: "2026-03-29T09:20:00Z",
          },
          derived_object: {
            id: "object-live-1",
            capture_event_id: "capture-live-1",
            object_type: "Decision",
            status: "active",
            title: "Decision: Keep admission conservative",
            body: {
              decision_text: "Keep admission conservative",
            },
            provenance: {
              capture_event_id: "capture-live-1",
              source_kind: "continuity_capture_event",
            },
            confidence: 0.95,
            created_at: "2026-03-29T09:20:00Z",
            updated_at: "2026-03-29T09:20:00Z",
          },
        },
      ],
      summary: {
        limit: 20,
        returned_count: 1,
        total_count: 1,
        derived_count: 1,
        triage_count: 0,
        order: ["created_at_desc", "id_desc"],
      },
    });
    getContinuityCaptureDetailMock.mockResolvedValue({
      capture: {
        capture_event: {
          id: "capture-live-1",
          raw_content: "Decision: Keep admission conservative",
          explicit_signal: null,
          admission_posture: "DERIVED",
          admission_reason: "high_confidence_prefix_decision",
          created_at: "2026-03-29T09:20:00Z",
        },
        derived_object: {
          id: "object-live-1",
          capture_event_id: "capture-live-1",
          object_type: "Decision",
          status: "active",
          title: "Decision: Keep admission conservative",
          body: {
            decision_text: "Keep admission conservative",
          },
          provenance: {
            capture_event_id: "capture-live-1",
            source_kind: "continuity_capture_event",
          },
          confidence: 0.95,
          created_at: "2026-03-29T09:20:00Z",
          updated_at: "2026-03-29T09:20:00Z",
        },
      },
    });
    queryContinuityRecallMock.mockResolvedValue({
      items: [
        {
          id: "recall-live-1",
          capture_event_id: "capture-live-1",
          object_type: "Decision",
          status: "active",
          title: "Decision: Keep admission conservative",
          body: { decision_text: "Keep admission conservative" },
          provenance: { thread_id: "thread-1" },
          confirmation_status: "confirmed",
          admission_posture: "DERIVED",
          confidence: 0.95,
          relevance: 130,
          last_confirmed_at: "2026-03-29T09:20:00Z",
          supersedes_object_id: null,
          superseded_by_object_id: null,
          scope_matches: [{ kind: "thread", value: "thread-1" }],
          provenance_references: [{ source_kind: "continuity_capture_event", source_id: "capture-live-1" }],
          ordering: {
            scope_match_count: 1,
            query_term_match_count: 1,
            confirmation_rank: 3,
            freshness_posture: "fresh",
            freshness_rank: 4,
            provenance_posture: "partial",
            provenance_rank: 2,
            supersession_posture: "current",
            supersession_rank: 3,
            posture_rank: 2,
            lifecycle_rank: 4,
            confidence: 0.95,
          },
          created_at: "2026-03-29T09:20:00Z",
          updated_at: "2026-03-29T09:20:00Z",
        },
      ],
      summary: {
        query: "decision",
        filters: {
          thread_id: "thread-1",
          since: null,
          until: null,
        },
        limit: 20,
        returned_count: 1,
        total_count: 1,
        order: ["relevance_desc", "created_at_desc", "id_desc"],
      },
    });
    getContinuityResumptionBriefMock.mockResolvedValue({
      brief: {
        assembly_version: "continuity_resumption_brief_v0",
        scope: { thread_id: "thread-1", since: null, until: null },
        last_decision: {
          item: {
            id: "recall-live-1",
            capture_event_id: "capture-live-1",
            object_type: "Decision",
            status: "active",
            title: "Decision: Keep admission conservative",
            body: { decision_text: "Keep admission conservative" },
            provenance: { thread_id: "thread-1" },
            confirmation_status: "confirmed",
            admission_posture: "DERIVED",
            confidence: 0.95,
            relevance: 130,
            last_confirmed_at: "2026-03-29T09:20:00Z",
            supersedes_object_id: null,
            superseded_by_object_id: null,
            scope_matches: [{ kind: "thread", value: "thread-1" }],
            provenance_references: [{ source_kind: "continuity_capture_event", source_id: "capture-live-1" }],
            ordering: {
              scope_match_count: 1,
              query_term_match_count: 1,
              confirmation_rank: 3,
              freshness_posture: "fresh",
              freshness_rank: 4,
              provenance_posture: "partial",
              provenance_rank: 2,
              supersession_posture: "current",
              supersession_rank: 3,
              posture_rank: 2,
              lifecycle_rank: 4,
              confidence: 0.95,
            },
            created_at: "2026-03-29T09:20:00Z",
            updated_at: "2026-03-29T09:20:00Z",
          },
          empty_state: { is_empty: false, message: "No decision found in the requested scope." },
        },
        open_loops: {
          items: [],
          summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No open loops found in the requested scope." },
        },
        recent_changes: {
          items: [],
          summary: { limit: 5, returned_count: 0, total_count: 1, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No recent changes found in the requested scope." },
        },
        next_action: {
          item: null,
          empty_state: { is_empty: true, message: "No next action found in the requested scope." },
        },
        sources: ["continuity_capture_events", "continuity_objects"],
      },
    });
    getContinuityOpenLoopDashboardMock.mockResolvedValue({
      dashboard: {
        scope: { thread_id: "thread-1", since: null, until: null },
        waiting_for: {
          items: [],
          summary: { limit: 20, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No waiting-for items in the requested scope." },
        },
        blocker: {
          items: [],
          summary: { limit: 20, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No blocker items in the requested scope." },
        },
        stale: {
          items: [],
          summary: { limit: 20, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No stale items in the requested scope." },
        },
        next_action: {
          items: [],
          summary: { limit: 20, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No next-action items in the requested scope." },
        },
        summary: {
          limit: 20,
          total_count: 0,
          posture_order: ["waiting_for", "blocker", "stale", "next_action"],
          item_order: ["created_at_desc", "id_desc"],
        },
        sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
      },
    });
    getContinuityDailyBriefMock.mockResolvedValue({
      brief: {
        assembly_version: "continuity_daily_brief_v0",
        scope: { thread_id: "thread-1", since: null, until: null },
        waiting_for_highlights: {
          items: [],
          summary: { limit: 3, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No waiting-for highlights for today in the requested scope." },
        },
        blocker_highlights: {
          items: [],
          summary: { limit: 3, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No blocker highlights for today in the requested scope." },
        },
        stale_items: {
          items: [],
          summary: { limit: 3, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No stale items for today in the requested scope." },
        },
        next_suggested_action: {
          item: null,
          empty_state: { is_empty: true, message: "No next suggested action in the requested scope." },
        },
        sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
      },
    });
    getContinuityWeeklyReviewMock.mockResolvedValue({
      review: {
        assembly_version: "continuity_weekly_review_v0",
        scope: { thread_id: "thread-1", since: null, until: null },
        rollup: {
          total_count: 0,
          waiting_for_count: 0,
          blocker_count: 0,
          stale_count: 0,
          correction_recurrence_count: 0,
          freshness_drift_count: 0,
          next_action_count: 0,
          posture_order: ["waiting_for", "blocker", "stale", "next_action"],
        },
        waiting_for: {
          items: [],
          summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No waiting-for items in the requested scope." },
        },
        blocker: {
          items: [],
          summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No blocker items in the requested scope." },
        },
        stale: {
          items: [],
          summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No stale items in the requested scope." },
        },
        next_action: {
          items: [],
          summary: { limit: 5, returned_count: 0, total_count: 0, order: ["created_at_desc", "id_desc"] },
          empty_state: { is_empty: true, message: "No next-action items in the requested scope." },
        },
        sources: ["continuity_capture_events", "continuity_objects", "continuity_correction_events"],
      },
    });
    listContinuityReviewQueueMock.mockResolvedValue({
      items: [
        {
          id: "object-live-1",
          capture_event_id: "capture-live-1",
          object_type: "Decision",
          status: "active",
          title: "Decision: Keep admission conservative",
          body: {
            decision_text: "Keep admission conservative",
          },
          provenance: {
            capture_event_id: "capture-live-1",
          },
          confidence: 0.95,
          last_confirmed_at: "2026-03-29T09:20:00Z",
          supersedes_object_id: null,
          superseded_by_object_id: null,
          created_at: "2026-03-29T09:20:00Z",
          updated_at: "2026-03-29T09:20:00Z",
        },
      ],
      summary: {
        status: "correction_ready",
        limit: 20,
        returned_count: 1,
        total_count: 1,
        order: ["updated_at_desc", "created_at_desc", "id_desc"],
      },
    });
    getContinuityReviewDetailMock.mockResolvedValue({
      review: {
        continuity_object: {
          id: "object-live-1",
          capture_event_id: "capture-live-1",
          object_type: "Decision",
          status: "active",
          title: "Decision: Keep admission conservative",
          body: { decision_text: "Keep admission conservative" },
          provenance: { capture_event_id: "capture-live-1" },
          confidence: 0.95,
          last_confirmed_at: "2026-03-29T09:20:00Z",
          supersedes_object_id: null,
          superseded_by_object_id: null,
          created_at: "2026-03-29T09:20:00Z",
          updated_at: "2026-03-29T09:20:00Z",
        },
        correction_events: [],
        supersession_chain: {
          supersedes: null,
          superseded_by: null,
        },
      },
    });

    render(await ContinuityPage({ searchParams: Promise.resolve({ capture: "capture-live-1", recall_query: "decision" }) }));

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText("Live inbox")).toBeInTheDocument();
    expect(screen.getByText("Live recall")).toBeInTheDocument();
    expect(screen.getByText("Live brief")).toBeInTheDocument();
    expect(screen.getByText("Live open loops")).toBeInTheDocument();
    expect(screen.getByText("Live daily brief")).toBeInTheDocument();
    expect(screen.getByText("Live weekly review")).toBeInTheDocument();
    expect(screen.getByText("Live review queue")).toBeInTheDocument();
    expect(screen.getAllByText("Decision: Keep admission conservative").length).toBeGreaterThan(0);

    expect(listContinuityCapturesMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      limit: 20,
    });
    expect(getContinuityCaptureDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "capture-live-1",
      "user-1",
    );
    expect(queryContinuityRecallMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      query: "decision",
      threadId: "",
      taskId: "",
      project: "",
      person: "",
      since: "",
      until: "",
      limit: 20,
    });
    expect(listContinuityReviewQueueMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      status: "correction_ready",
      limit: 20,
    });
    expect(getContinuityReviewDetailMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "object-live-1",
      "user-1",
    );
    expect(getContinuityResumptionBriefMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      query: "decision",
      threadId: "",
      taskId: "",
      project: "",
      person: "",
      since: "",
      until: "",
      maxRecentChanges: 5,
      maxOpenLoops: 5,
    });
    expect(getContinuityOpenLoopDashboardMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "user-1",
      {
        query: "decision",
        threadId: "",
        taskId: "",
        project: "",
        person: "",
        since: "",
        until: "",
        limit: 20,
      },
    );
    expect(getContinuityDailyBriefMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      query: "decision",
      threadId: "",
      taskId: "",
      project: "",
      person: "",
      since: "",
      until: "",
      limit: 3,
    });
    expect(getContinuityWeeklyReviewMock).toHaveBeenCalledWith("https://api.example.com", "user-1", {
      query: "decision",
      threadId: "",
      taskId: "",
      project: "",
      person: "",
      since: "",
      until: "",
      limit: 5,
    });
  });
});
