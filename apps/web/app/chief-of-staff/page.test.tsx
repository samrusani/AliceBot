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
    expect(screen.getByText("Fixture action handoff")).toBeInTheDocument();
    expect(screen.getByText("Fixture handoff queue")).toBeInTheDocument();
    expect(screen.getAllByText("Next Action: Confirm launch checklist owner").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Action type: execute_next_action").length).toBeGreaterThan(0);
    expect(screen.getByText("Follow-through supervision")).toBeInTheDocument();
    expect(screen.getByText("Preparation and resumption")).toBeInTheDocument();
    expect(screen.getByText("Weekly review and learning")).toBeInTheDocument();
    expect(screen.getByText("Action handoff")).toBeInTheDocument();
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
        action_handoff_brief: {
          summary:
            "Prepared 1 deterministic handoff item from recommended_next_action signals. All task and approval drafts remain artifact-only and approval-bounded.",
          confidence_posture: "medium",
          non_autonomous_guarantee:
            "No task, approval, connector send, or external side effect is executed by this endpoint.",
          order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
          source_order: ["recommended_next_action", "follow_through", "prep_checklist", "weekly_review"],
          provenance_references: [
            {
              source_kind: "continuity_capture_event",
              source_id: "capture-live-1",
            },
          ],
        },
        handoff_items: [
          {
            rank: 1,
            handoff_item_id: "handoff-1-recommended_next_action-priority-live-1",
            source_kind: "recommended_next_action",
            source_reference_id: "priority-live-1",
            title: "Next Action: Send partner follow-up",
            recommendation_action: "execute_next_action",
            priority_posture: "urgent",
            confidence_posture: "medium",
            rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
            provenance_references: [
              {
                source_kind: "continuity_capture_event",
                source_id: "capture-live-1",
              },
            ],
            score: 1650,
            task_draft: {
              status: "draft",
              mode: "governed_request_draft",
              approval_required: true,
              auto_execute: false,
              source_handoff_item_id: "handoff-1-recommended_next_action-priority-live-1",
              title: "Next Action: Send partner follow-up",
              summary:
                "Draft-only governed request assembled from chief-of-staff handoff artifacts; requires explicit approval before any execution.",
              target: { thread_id: "thread-1", task_id: null, project: null, person: null },
              request: {
                action: "execute_next_action",
                scope: "chief_of_staff_priority",
                domain_hint: "planning",
                risk_hint: "governed_handoff",
                attributes: {},
              },
              rationale:
                "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-live-1",
                },
              ],
            },
            approval_draft: {
              status: "draft_only",
              mode: "approval_request_draft",
              decision: "approval_required",
              approval_required: true,
              auto_submit: false,
              source_handoff_item_id: "handoff-1-recommended_next_action-priority-live-1",
              request: {
                action: "execute_next_action",
                scope: "chief_of_staff_priority",
                domain_hint: "planning",
                risk_hint: "governed_handoff",
                attributes: {},
              },
              reason:
                "Execution remains approval-bounded. This approval draft is artifact-only and must be explicitly submitted and resolved before any side effect.",
              required_checks: [
                "operator_review_handoff_artifact",
                "submit_governed_approval_request",
                "explicit_approval_resolution",
              ],
              provenance_references: [
                {
                  source_kind: "continuity_capture_event",
                  source_id: "capture-live-1",
                },
              ],
            },
          },
        ],
        handoff_queue_summary: {
          total_count: 1,
          ready_count: 1,
          pending_approval_count: 0,
          executed_count: 0,
          stale_count: 0,
          expired_count: 0,
          state_order: ["ready", "pending_approval", "executed", "stale", "expired"],
          group_order: ["ready", "pending_approval", "executed", "stale", "expired"],
          item_order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
          review_action_order: ["mark_ready", "mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"],
        },
        handoff_queue_groups: {
          ready: {
            items: [
              {
                queue_rank: 1,
                handoff_rank: 1,
                handoff_item_id: "handoff-1-recommended_next_action-priority-live-1",
                lifecycle_state: "ready",
                state_reason: "Handoff item is ready for explicit operator review.",
                source_kind: "recommended_next_action",
                source_reference_id: "priority-live-1",
                title: "Next Action: Send partner follow-up",
                recommendation_action: "execute_next_action",
                priority_posture: "urgent",
                confidence_posture: "medium",
                score: 1650,
                age_hours_relative_to_latest: 0,
                review_action_order: ["mark_ready", "mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"],
                available_review_actions: ["mark_pending_approval", "mark_executed", "mark_stale", "mark_expired"],
                last_review_action: null,
                provenance_references: [
                  {
                    source_kind: "continuity_capture_event",
                    source_id: "capture-live-1",
                  },
                ],
              },
            ],
            summary: {
              lifecycle_state: "ready",
              returned_count: 1,
              total_count: 1,
              order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
            },
            empty_state: {
              is_empty: false,
              message: "No ready handoff items for this scope.",
            },
          },
          pending_approval: {
            items: [],
            summary: {
              lifecycle_state: "pending_approval",
              returned_count: 0,
              total_count: 0,
              order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
            },
            empty_state: {
              is_empty: true,
              message: "No handoff items are currently pending approval.",
            },
          },
          executed: {
            items: [],
            summary: {
              lifecycle_state: "executed",
              returned_count: 0,
              total_count: 0,
              order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
            },
            empty_state: {
              is_empty: true,
              message: "No handoff items are currently marked executed.",
            },
          },
          stale: {
            items: [],
            summary: {
              lifecycle_state: "stale",
              returned_count: 0,
              total_count: 0,
              order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
            },
            empty_state: {
              is_empty: true,
              message: "No stale handoff items are currently surfaced.",
            },
          },
          expired: {
            items: [],
            summary: {
              lifecycle_state: "expired",
              returned_count: 0,
              total_count: 0,
              order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
            },
            empty_state: {
              is_empty: true,
              message: "No expired handoff items are currently surfaced.",
            },
          },
        },
        handoff_review_actions: [],
        task_draft: {
          status: "draft",
          mode: "governed_request_draft",
          approval_required: true,
          auto_execute: false,
          source_handoff_item_id: "handoff-1-recommended_next_action-priority-live-1",
          title: "Next Action: Send partner follow-up",
          summary:
            "Draft-only governed request assembled from chief-of-staff handoff artifacts; requires explicit approval before any execution.",
          target: { thread_id: "thread-1", task_id: null, project: null, person: null },
          request: {
            action: "execute_next_action",
            scope: "chief_of_staff_priority",
            domain_hint: "planning",
            risk_hint: "governed_handoff",
            attributes: {},
          },
          rationale: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
          provenance_references: [
            {
              source_kind: "continuity_capture_event",
              source_id: "capture-live-1",
            },
          ],
        },
        approval_draft: {
          status: "draft_only",
          mode: "approval_request_draft",
          decision: "approval_required",
          approval_required: true,
          auto_submit: false,
          source_handoff_item_id: "handoff-1-recommended_next_action-priority-live-1",
          request: {
            action: "execute_next_action",
            scope: "chief_of_staff_priority",
            domain_hint: "planning",
            risk_hint: "governed_handoff",
            attributes: {},
          },
          reason:
            "Execution remains approval-bounded. This approval draft is artifact-only and must be explicitly submitted and resolved before any side effect.",
          required_checks: [
            "operator_review_handoff_artifact",
            "submit_governed_approval_request",
            "explicit_approval_resolution",
          ],
          provenance_references: [
            {
              source_kind: "continuity_capture_event",
              source_id: "capture-live-1",
            },
          ],
        },
        execution_posture: {
          posture: "approval_bounded_artifact_only",
          approval_required: true,
          autonomous_execution: false,
          external_side_effects_allowed: false,
          default_routing_decision: "approval_required",
          required_operator_actions: [
            "review_handoff_items",
            "submit_task_or_approval_request",
            "resolve_approval_before_execution",
          ],
          non_autonomous_guarantee:
            "No task, approval, connector send, or external side effect is executed by this endpoint.",
          reason: "Chief-of-staff handoff artifacts are deterministic execution-prep only in P8-S29.",
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
          handoff_item_count: 1,
          handoff_item_order: ["score_desc", "source_order_asc", "source_reference_id_asc"],
          execution_posture_order: ["approval_bounded_artifact_only"],
          handoff_queue_total_count: 1,
          handoff_queue_ready_count: 1,
          handoff_queue_pending_approval_count: 0,
          handoff_queue_executed_count: 0,
          handoff_queue_stale_count: 0,
          handoff_queue_expired_count: 0,
          handoff_queue_state_order: ["ready", "pending_approval", "executed", "stale", "expired"],
          handoff_queue_group_order: ["ready", "pending_approval", "executed", "stale", "expired"],
          handoff_queue_item_order: ["queue_rank_asc", "handoff_rank_asc", "score_desc", "handoff_item_id_asc"],
        },
        sources: [
          "continuity_recall",
          "memory_trust_dashboard",
          "chief_of_staff_action_handoff",
          "chief_of_staff_handoff_queue",
          "chief_of_staff_handoff_review_actions",
        ],
      },
    });

    render(await ChiefOfStaffPage({ searchParams: Promise.resolve({ thread_id: "thread-1" }) }));

    expect(screen.getByText("Live API")).toBeInTheDocument();
    expect(screen.getByText("Live chief-of-staff brief")).toBeInTheDocument();
    expect(screen.getByText("Live follow-through")).toBeInTheDocument();
    expect(screen.getByText("Live preparation brief")).toBeInTheDocument();
    expect(screen.getByText("Live weekly review")).toBeInTheDocument();
    expect(screen.getByText("Live action handoff")).toBeInTheDocument();
    expect(screen.getByText("Live handoff queue")).toBeInTheDocument();
    expect(screen.getAllByText("Next Action: Send partner follow-up").length).toBeGreaterThan(0);
    expect(getChiefOfStaffPriorityBriefMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "user-1",
      expect.objectContaining({ threadId: "thread-1" }),
    );
  });
});
