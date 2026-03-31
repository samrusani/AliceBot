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
    expect(screen.getByText("Fixture follow-through")).toBeInTheDocument();
    expect(screen.getByText("Fixture preparation brief")).toBeInTheDocument();
    expect(screen.getByText("Fixture weekly review")).toBeInTheDocument();
    expect(screen.getAllByText("Next Action: Confirm launch checklist owner").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Action type: execute_next_action").length).toBeGreaterThan(0);
    expect(screen.getByText("Follow-through supervision")).toBeInTheDocument();
    expect(screen.getByText("Preparation and resumption")).toBeInTheDocument();
    expect(screen.getByText("Weekly review and learning")).toBeInTheDocument();
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
        overdue_items: [
          {
            rank: 1,
            id: "follow-live-overdue-1",
            capture_event_id: "capture-follow-live-overdue-1",
            object_type: "NextAction",
            status: "active",
            title: "Next Action: Send partner follow-up",
            current_priority_posture: "urgent",
            follow_through_posture: "overdue",
            recommendation_action: "escalate",
            reason:
              "Execution follow-through is overdue (posture=urgent, age=140.0h), so action 'escalate' is recommended.",
            age_hours: 140,
            provenance_references: [
              {
                source_kind: "continuity_capture_event",
                source_id: "capture-follow-live-overdue-1",
              },
            ],
            created_at: "2026-03-26T08:00:00Z",
            updated_at: "2026-03-26T08:00:00Z",
          },
        ],
        stale_waiting_for_items: [],
        slipped_commitments: [],
        escalation_posture: {
          posture: "critical",
          reason: "At least one follow-through item requires escalation.",
          total_follow_through_count: 1,
          nudge_count: 0,
          defer_count: 0,
          escalate_count: 1,
          close_loop_candidate_count: 0,
        },
        draft_follow_up: {
          status: "drafted",
          mode: "draft_only",
          approval_required: true,
          auto_send: false,
          reason: "Highest-severity follow-through item selected deterministically for operator review.",
          target_metadata: {
            continuity_object_id: "follow-live-overdue-1",
            capture_event_id: "capture-follow-live-overdue-1",
            object_type: "NextAction",
            priority_posture: "urgent",
            follow_through_posture: "overdue",
            recommendation_action: "escalate",
            thread_id: "thread-1",
          },
          content: {
            subject: "Follow-up: Next Action: Send partner follow-up",
            body: "This draft is artifact-only and requires explicit approval before any external send.",
          },
        },
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
        preparation_brief: {
          scope: { thread_id: "thread-1", since: null, until: null },
          context_items: [
            {
              rank: 1,
              id: "prep-context-live-1",
              capture_event_id: "capture-prep-context-live-1",
              object_type: "Decision",
              status: "active",
              title: "Decision: Keep launch phased",
              reason: "Decision context carried forward for deterministic meeting prep.",
              confidence_posture: "medium",
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-prep-context-live-1",
                },
              ],
              created_at: "2026-03-31T08:30:00Z",
            },
          ],
          last_decision: {
            rank: 1,
            id: "prep-decision-live-1",
            capture_event_id: "capture-prep-decision-live-1",
            object_type: "Decision",
            status: "active",
            title: "Decision: Keep launch phased",
            reason: "Latest scoped decision included to ground upcoming preparation context.",
            confidence_posture: "medium",
            provenance_references: [
              {
                source_kind: "continuity_capture_event",
                source_id: "capture-prep-decision-live-1",
              },
            ],
            created_at: "2026-03-31T08:30:00Z",
          },
          open_loops: [],
          next_action: null,
          confidence_posture: "medium",
          confidence_reason: "Memory quality gate needs review, so recommendation confidence is capped at medium.",
          summary: {
            limit: 6,
            returned_count: 1,
            total_count: 1,
            order: ["rank_asc", "created_at_desc", "id_desc"],
          },
        },
        what_changed_summary: {
          items: [
            {
              rank: 1,
              id: "what-changed-live-1",
              capture_event_id: "capture-what-changed-live-1",
              object_type: "NextAction",
              status: "active",
              title: "Next Action: Send partner follow-up",
              reason: "Included from deterministic continuity recent-changes ordering.",
              confidence_posture: "medium",
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-what-changed-live-1",
                },
              ],
              created_at: "2026-03-31T10:10:00Z",
            },
          ],
          confidence_posture: "medium",
          confidence_reason: "Memory quality gate needs review, so recommendation confidence is capped at medium.",
          summary: {
            limit: 6,
            returned_count: 1,
            total_count: 1,
            order: ["rank_asc", "created_at_desc", "id_desc"],
          },
        },
        prep_checklist: {
          items: [
            {
              rank: 1,
              id: "prep-check-live-1",
              capture_event_id: "capture-prep-check-live-1",
              object_type: "WaitingFor",
              status: "active",
              title: "Waiting For: Vendor legal review",
              reason: "Prepare a status check and explicit owner for this unresolved open loop.",
              confidence_posture: "medium",
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-prep-check-live-1",
                },
              ],
              created_at: "2026-03-31T09:00:00Z",
            },
          ],
          confidence_posture: "medium",
          confidence_reason: "Memory quality gate needs review, so recommendation confidence is capped at medium.",
          summary: {
            limit: 6,
            returned_count: 1,
            total_count: 1,
            order: ["rank_asc", "created_at_desc", "id_desc"],
          },
        },
        suggested_talking_points: {
          items: [
            {
              rank: 1,
              id: "talking-live-1",
              capture_event_id: "capture-talking-live-1",
              object_type: "Blocker",
              status: "active",
              title: "Blocker: Launch token pending",
              reason: "Raise this unresolved dependency explicitly and confirm a concrete follow-up path.",
              confidence_posture: "medium",
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-talking-live-1",
                },
              ],
              created_at: "2026-03-30T10:10:00Z",
            },
          ],
          confidence_posture: "medium",
          confidence_reason: "Memory quality gate needs review, so recommendation confidence is capped at medium.",
          summary: {
            limit: 6,
            returned_count: 1,
            total_count: 1,
            order: ["rank_asc", "created_at_desc", "id_desc"],
          },
        },
        resumption_supervision: {
          recommendations: [
            {
              rank: 1,
              action: "execute_next_action",
              title: "Next Action: Send partner follow-up",
              reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
              confidence_posture: "medium",
              target_priority_id: "priority-live-1",
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-live-1",
                },
              ],
            },
          ],
          confidence_posture: "medium",
          confidence_reason: "Memory quality gate needs review, so recommendation confidence is capped at medium.",
          summary: {
            limit: 3,
            returned_count: 1,
            total_count: 1,
            order: ["rank_asc"],
          },
        },
        weekly_review_brief: {
          scope: { thread_id: "thread-1", since: null, until: null },
          rollup: {
            total_count: 1,
            waiting_for_count: 0,
            blocker_count: 1,
            stale_count: 0,
            correction_recurrence_count: 0,
            freshness_drift_count: 0,
            next_action_count: 1,
            posture_order: ["waiting_for", "blocker", "stale", "next_action"],
          },
          guidance: [
            {
              rank: 1,
              action: "escalate",
              signal_count: 2,
              rationale: "Escalate where blockers are concentrated.",
            },
            {
              rank: 2,
              action: "close",
              signal_count: 1,
              rationale: "Close loops where deterministic close candidates exist.",
            },
            {
              rank: 3,
              action: "defer",
              signal_count: 0,
              rationale: "Defer where stale load remains.",
            },
          ],
          summary: {
            guidance_order: ["close", "defer", "escalate"],
            guidance_item_order: ["signal_count_desc", "action_desc"],
          },
        },
        recommendation_outcomes: {
          items: [
            {
              id: "outcome-live-1",
              capture_event_id: "capture-outcome-live-1",
              outcome: "accept",
              recommendation_action_type: "execute_next_action",
              recommendation_title: "Next Action: Send partner follow-up",
              rewritten_title: null,
              target_priority_id: "priority-live-1",
              rationale: "Accepted in weekly review.",
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-outcome-live-1",
                },
              ],
              created_at: "2026-03-31T12:00:00Z",
              updated_at: "2026-03-31T12:00:00Z",
            },
          ],
          summary: {
            returned_count: 1,
            total_count: 1,
            outcome_counts: { accept: 1, defer: 0, ignore: 0, rewrite: 0 },
            order: ["created_at_desc", "id_desc"],
          },
        },
        priority_learning_summary: {
          total_count: 1,
          accept_count: 1,
          defer_count: 0,
          ignore_count: 0,
          rewrite_count: 0,
          acceptance_rate: 1,
          override_rate: 0,
          defer_hotspots: [],
          ignore_hotspots: [],
          priority_shift_explanation:
            "Prioritization is reinforcing currently accepted recommendation patterns while tracking defer/override hotspots.",
          hotspot_order: ["count_desc", "key_asc"],
        },
        pattern_drift_summary: {
          posture: "improving",
          reason:
            "Accepted outcomes are leading with bounded defers/overrides, indicating improving recommendation fit.",
          supporting_signals: ["Outcomes captured: 1"],
        },
        summary: {
          limit: 12,
          returned_count: 1,
          total_count: 1,
          posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"],
          order: ["score_desc", "created_at_desc", "id_desc"],
          follow_through_posture_order: ["overdue", "stale_waiting_for", "slipped_commitment"],
          follow_through_item_order: [
            "recommendation_action_desc",
            "age_hours_desc",
            "created_at_desc",
            "id_desc",
          ],
          follow_through_total_count: 1,
          overdue_count: 1,
          stale_waiting_for_count: 0,
          slipped_commitment_count: 0,
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
    expect(screen.getByText("Live follow-through")).toBeInTheDocument();
    expect(screen.getByText("Live preparation brief")).toBeInTheDocument();
    expect(screen.getByText("Live weekly review")).toBeInTheDocument();
    expect(screen.getAllByText("Next Action: Send partner follow-up").length).toBeGreaterThan(0);
    expect(getChiefOfStaffPriorityBriefMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "user-1",
      expect.objectContaining({ threadId: "thread-1" }),
    );
  });
});
