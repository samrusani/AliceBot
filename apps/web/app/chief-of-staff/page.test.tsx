import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChiefOfStaffPage from "./page";

const { getApiConfigMock, getChiefOfStaffPriorityBriefMock, hasLiveApiConfigMock } = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getChiefOfStaffPriorityBriefMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
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
    getChiefOfStaffPriorityBrief: getChiefOfStaffPriorityBriefMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
  };
});

describe("ChiefOfStaffPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getChiefOfStaffPriorityBriefMock.mockReset();
    hasLiveApiConfigMock.mockReset();

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

  it("uses fixture chief-of-staff brief when live API config is absent", async () => {
    render(await ChiefOfStaffPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Chief-of-staff")).toBeInTheDocument();
    expect(screen.getByText("Fixture chief-of-staff brief")).toBeInTheDocument();
    expect(screen.getAllByText("Next Action: Confirm launch checklist owner").length).toBeGreaterThan(0);
    expect(screen.getByText("Action type: execute_next_action")).toBeInTheDocument();
    expect(getChiefOfStaffPriorityBriefMock).not.toHaveBeenCalled();
  });

  it("renders live chief-of-staff brief when API read succeeds", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);
    getChiefOfStaffPriorityBriefMock.mockResolvedValue({
      brief: {
        assembly_version: "chief_of_staff_priority_brief_v0",
        scope: { thread_id: "thread-1", since: null, until: null },
        ranked_items: [
          {
            rank: 1,
            id: "priority-live-1",
            capture_event_id: "capture-live-1",
            object_type: "NextAction",
            status: "active",
            title: "Next Action: Send partner follow-up",
            priority_posture: "urgent",
            confidence_posture: "medium",
            confidence: 0.92,
            score: 650,
            provenance: { thread_id: "thread-1" },
            created_at: "2026-03-31T10:10:00Z",
            updated_at: "2026-03-31T10:10:00Z",
            rationale: {
              reasons: ["Marked urgent because this item is a deterministic immediate focus from resumption signals."],
              ranking_inputs: {
                posture: "urgent",
                open_loop_posture: "next_action",
                recency_rank: 1,
                age_hours_relative_to_latest: 0,
                recall_relevance: 120,
                scope_match_count: 1,
                query_term_match_count: 1,
                freshness_posture: "fresh",
                provenance_posture: "strong",
                supersession_posture: "current",
              },
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-live-1",
                },
              ],
              trust_signals: {
                quality_gate_status: "needs_review",
                retrieval_status: "pass",
                trust_confidence_cap: "medium",
                downgraded_by_trust: false,
                reason: "Memory quality gate needs review, so recommendation confidence is capped at medium.",
              },
            },
          },
        ],
        recommended_next_action: {
          action_type: "execute_next_action",
          title: "Next Action: Send partner follow-up",
          target_priority_id: "priority-live-1",
          priority_posture: "urgent",
          confidence_posture: "medium",
          reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
          provenance_references: [
            {
              source_kind: "continuity_capture_event",
              source_id: "capture-live-1",
            },
          ],
          deterministic_rank_key: "1:priority-live-1:650.000000",
        },
        summary: {
          limit: 12,
          returned_count: 1,
          total_count: 1,
          posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"],
          order: ["score_desc", "created_at_desc", "id_desc"],
          trust_confidence_posture: "medium",
          trust_confidence_reason:
            "Memory quality gate needs review, so recommendation confidence is capped at medium.",
          quality_gate_status: "needs_review",
          retrieval_status: "pass",
        },
        sources: ["continuity_recall", "memory_trust_dashboard"],
      },
    });

    render(await ChiefOfStaffPage({ searchParams: Promise.resolve({ thread_id: "thread-1" }) }));

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText("Live chief-of-staff brief")).toBeInTheDocument();
    expect(screen.getAllByText("Next Action: Send partner follow-up").length).toBeGreaterThan(0);
    expect(getChiefOfStaffPriorityBriefMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "user-1",
      expect.objectContaining({ threadId: "thread-1" }),
    );
  });
});
