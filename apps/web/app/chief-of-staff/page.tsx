import { ChiefOfStaffFollowThroughPanel } from "../../components/chief-of-staff-follow-through-panel";
import { ChiefOfStaffPreparationPanel } from "../../components/chief-of-staff-preparation-panel";
import { ChiefOfStaffPriorityPanel } from "../../components/chief-of-staff-priority-panel";
import { PageHeader } from "../../components/page-header";
import { StatusBadge } from "../../components/status-badge";
import type { ApiSource, ChiefOfStaffPriorityBrief } from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getChiefOfStaffPriorityBrief,
  hasLiveApiConfig,
  pageModeLabel,
} from "../../lib/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }
  return value?.trim() ?? "";
}

function parseNonNegativeInt(value: string, fallback: number) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
}

const chiefOfStaffFixture: ChiefOfStaffPriorityBrief = {
  assembly_version: "chief_of_staff_priority_brief_v0",
  scope: {
    thread_id: "thread-fixture-1",
    since: null,
    until: null,
  },
  ranked_items: [
    {
      rank: 1,
      id: "priority-fixture-1",
      capture_event_id: "capture-priority-fixture-1",
      object_type: "NextAction",
      status: "active",
      title: "Next Action: Confirm launch checklist owner",
      priority_posture: "urgent",
      confidence_posture: "low",
      confidence: 0.97,
      score: 642.5,
      provenance: {
        thread_id: "thread-fixture-1",
        source_event_ids: ["event-fixture-1"],
      },
      created_at: "2026-03-31T10:05:00Z",
      updated_at: "2026-03-31T10:05:00Z",
      rationale: {
        reasons: [
          "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
          "Confidence is explicitly downgraded by current memory trust posture.",
          "Provenance references are attached from continuity recall evidence.",
        ],
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
            source_id: "capture-priority-fixture-1",
          },
        ],
        trust_signals: {
          quality_gate_status: "insufficient_sample",
          retrieval_status: "pass",
          trust_confidence_cap: "low",
          downgraded_by_trust: true,
          reason:
            "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
        },
      },
    },
    {
      rank: 2,
      id: "priority-fixture-2",
      capture_event_id: "capture-priority-fixture-2",
      object_type: "WaitingFor",
      status: "active",
      title: "Waiting For: Vendor legal review",
      priority_posture: "waiting",
      confidence_posture: "low",
      confidence: 0.88,
      score: 434,
      provenance: {
        thread_id: "thread-fixture-1",
        source_event_ids: ["event-fixture-2"],
      },
      created_at: "2026-03-31T09:15:00Z",
      updated_at: "2026-03-31T09:15:00Z",
      rationale: {
        reasons: [
          "Marked waiting because this item is in waiting-for posture and requires follow-through tracking.",
          "Aging evidence: 0.8h older than the newest scoped priority candidate.",
          "Provenance references are attached from continuity recall evidence.",
        ],
        ranking_inputs: {
          posture: "waiting",
          open_loop_posture: "waiting_for",
          recency_rank: 2,
          age_hours_relative_to_latest: 0.833333,
          recall_relevance: 108,
          scope_match_count: 1,
          query_term_match_count: 0,
          freshness_posture: "aging",
          provenance_posture: "strong",
          supersession_posture: "current",
        },
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-2",
          },
        ],
        trust_signals: {
          quality_gate_status: "insufficient_sample",
          retrieval_status: "pass",
          trust_confidence_cap: "low",
          downgraded_by_trust: true,
          reason:
            "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
        },
      },
    },
  ],
  overdue_items: [
    {
      rank: 1,
      id: "follow-fixture-overdue-1",
      capture_event_id: "capture-follow-fixture-overdue-1",
      object_type: "NextAction",
      status: "active",
      title: "Next Action: Send partner status follow-up",
      current_priority_posture: "urgent",
      follow_through_posture: "overdue",
      recommendation_action: "escalate",
      reason:
        "Execution follow-through is overdue (posture=urgent, age=140.0h), so action 'escalate' is recommended.",
      age_hours: 140,
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-follow-fixture-overdue-1",
        },
      ],
      created_at: "2026-03-26T08:00:00Z",
      updated_at: "2026-03-26T08:00:00Z",
    },
  ],
  stale_waiting_for_items: [
    {
      rank: 1,
      id: "follow-fixture-stale-waiting-1",
      capture_event_id: "capture-follow-fixture-stale-waiting-1",
      object_type: "WaitingFor",
      status: "stale",
      title: "Waiting For: Procurement approval",
      current_priority_posture: "stale",
      follow_through_posture: "stale_waiting_for",
      recommendation_action: "nudge",
      reason:
        "Waiting-for item is stale (status=stale, age=96.0h from latest scoped item), so action 'nudge' is recommended.",
      age_hours: 96,
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-follow-fixture-stale-waiting-1",
        },
      ],
      created_at: "2026-03-27T00:00:00Z",
      updated_at: "2026-03-27T00:00:00Z",
    },
  ],
  slipped_commitments: [
    {
      rank: 1,
      id: "follow-fixture-slipped-commitment-1",
      capture_event_id: "capture-follow-fixture-slipped-commitment-1",
      object_type: "Commitment",
      status: "active",
      title: "Commitment: Publish weekly status digest",
      current_priority_posture: "important",
      follow_through_posture: "slipped_commitment",
      recommendation_action: "defer",
      reason:
        "Commitment is slipping (status=active, age=60.0h from latest scoped item), so action 'defer' is recommended.",
      age_hours: 60,
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-follow-fixture-slipped-commitment-1",
        },
      ],
      created_at: "2026-03-28T12:00:00Z",
      updated_at: "2026-03-28T12:00:00Z",
    },
  ],
  escalation_posture: {
    posture: "critical",
    reason: "At least one follow-through item requires escalation.",
    total_follow_through_count: 3,
    nudge_count: 1,
    defer_count: 1,
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
      continuity_object_id: "follow-fixture-overdue-1",
      capture_event_id: "capture-follow-fixture-overdue-1",
      object_type: "NextAction",
      priority_posture: "urgent",
      follow_through_posture: "overdue",
      recommendation_action: "escalate",
      thread_id: "thread-fixture-1",
    },
    content: {
      subject: "Follow-up: Next Action: Send partner status follow-up",
      body: [
        "Following up on: Next Action: Send partner status follow-up",
        "Current follow-through posture: overdue",
        "Current priority posture: urgent",
        "Recommended action: escalate",
        "Reason: Execution follow-through is overdue (posture=urgent, age=140.0h), so action 'escalate' is recommended.",
        "",
        "This draft is artifact-only and requires explicit approval before any external send.",
      ].join("\\n"),
    },
  },
  recommended_next_action: {
    action_type: "execute_next_action",
    title: "Next Action: Confirm launch checklist owner",
    target_priority_id: "priority-fixture-1",
    priority_posture: "urgent",
    confidence_posture: "low",
    reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
    provenance_references: [
      {
        source_kind: "continuity_capture_event",
        source_id: "capture-priority-fixture-1",
      },
    ],
    deterministic_rank_key: "1:priority-fixture-1:642.500000",
  },
  preparation_brief: {
    scope: {
      thread_id: "thread-fixture-1",
      since: null,
      until: null,
    },
    context_items: [
      {
        rank: 1,
        id: "prep-context-fixture-1",
        capture_event_id: "capture-prep-context-fixture-1",
        object_type: "Decision",
        status: "active",
        title: "Decision: Keep rollout to one launch cohort",
        reason: "Decision context carried forward for deterministic meeting prep.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-prep-context-fixture-1",
          },
        ],
        created_at: "2026-03-31T07:45:00Z",
      },
    ],
    last_decision: {
      rank: 1,
      id: "prep-decision-fixture-1",
      capture_event_id: "capture-prep-decision-fixture-1",
      object_type: "Decision",
      status: "active",
      title: "Decision: Keep rollout to one launch cohort",
      reason: "Latest scoped decision included to ground upcoming preparation context.",
      confidence_posture: "low",
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-prep-decision-fixture-1",
        },
      ],
      created_at: "2026-03-31T07:45:00Z",
    },
    open_loops: [],
    next_action: {
      rank: 1,
      id: "prep-next-action-fixture-1",
      capture_event_id: "capture-prep-next-action-fixture-1",
      object_type: "NextAction",
      status: "active",
      title: "Next Action: Confirm launch checklist owner",
      reason: "Next action is included to keep immediate execution focus explicit after interruption.",
      confidence_posture: "low",
      provenance_references: [
        {
          source_kind: "continuity_capture_event",
          source_id: "capture-prep-next-action-fixture-1",
        },
      ],
      created_at: "2026-03-31T10:05:00Z",
    },
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
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
        id: "what-changed-fixture-1",
        capture_event_id: "capture-what-changed-fixture-1",
        object_type: "NextAction",
        status: "active",
        title: "Next Action: Confirm launch checklist owner",
        reason: "Included from deterministic continuity recent-changes ordering.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-what-changed-fixture-1",
          },
        ],
        created_at: "2026-03-31T10:05:00Z",
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
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
        id: "prep-checklist-fixture-1",
        capture_event_id: "capture-prep-checklist-fixture-1",
        object_type: "WaitingFor",
        status: "active",
        title: "Waiting For: Vendor legal review",
        reason: "Prepare a status check and explicit owner for this unresolved open loop.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-prep-checklist-fixture-1",
          },
        ],
        created_at: "2026-03-31T09:15:00Z",
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
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
        id: "suggested-point-fixture-1",
        capture_event_id: "capture-suggested-point-fixture-1",
        object_type: "Blocker",
        status: "active",
        title: "Blocker: Release token rotation lag",
        reason: "Raise this unresolved dependency explicitly and confirm a concrete follow-up path.",
        confidence_posture: "low",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-suggested-point-fixture-1",
          },
        ],
        created_at: "2026-03-30T10:00:00Z",
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
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
        title: "Next Action: Confirm launch checklist owner",
        reason: "Marked urgent because this item is a deterministic immediate focus from resumption signals.",
        confidence_posture: "low",
        target_priority_id: "priority-fixture-1",
        provenance_references: [
          {
            source_kind: "continuity_capture_event",
            source_id: "capture-priority-fixture-1",
          },
        ],
      },
      {
        rank: 2,
        action: "review_scope",
        title: "Calibrate recommendation confidence before execution",
        reason:
          "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
        confidence_posture: "low",
        target_priority_id: null,
        provenance_references: [],
      },
    ],
    confidence_posture: "low",
    confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    summary: {
      limit: 3,
      returned_count: 2,
      total_count: 2,
      order: ["rank_asc"],
    },
  },
  summary: {
    limit: 12,
    returned_count: 2,
    total_count: 2,
    posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"],
    order: ["score_desc", "created_at_desc", "id_desc"],
    follow_through_posture_order: ["overdue", "stale_waiting_for", "slipped_commitment"],
    follow_through_item_order: [
      "recommendation_action_desc",
      "age_hours_desc",
      "created_at_desc",
      "id_desc",
    ],
    follow_through_total_count: 3,
    overdue_count: 1,
    stale_waiting_for_count: 1,
    slipped_commitment_count: 1,
    trust_confidence_posture: "low",
    trust_confidence_reason:
      "Memory quality gate is weak (insufficient sample or degraded), so recommendation confidence is capped at low.",
    quality_gate_status: "insufficient_sample",
    retrieval_status: "pass",
  },
  sources: [
    "continuity_recall",
    "continuity_open_loops",
    "continuity_resumption_brief",
    "memory_trust_dashboard",
  ],
};

export default async function ChiefOfStaffPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const query = normalizeParam(params.query);
  const threadId = normalizeParam(params.thread_id);
  const taskId = normalizeParam(params.task_id);
  const project = normalizeParam(params.project);
  const person = normalizeParam(params.person);
  const since = normalizeParam(params.since);
  const until = normalizeParam(params.until);
  const limit = parseNonNegativeInt(normalizeParam(params.limit), 12);

  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let brief = chiefOfStaffFixture;
  let briefSource: ApiSource = "fixture";
  let briefUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await getChiefOfStaffPriorityBrief(apiConfig.apiBaseUrl, apiConfig.userId, {
        query: query || undefined,
        threadId: threadId || undefined,
        taskId: taskId || undefined,
        project: project || undefined,
        person: person || undefined,
        since: since || undefined,
        until: until || undefined,
        limit,
      });
      brief = payload.brief;
      briefSource = "live";
    } catch (error) {
      briefUnavailableReason =
        error instanceof Error ? error.message : "Chief-of-staff brief could not be loaded.";
    }
  }

  const mode = combinePageModes(briefSource);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Phase 7"
        title="Chief-of-staff"
        description="Deterministic priority ranking, preparation artifacts, and resumption supervision with explicit rationale, provenance visibility, trust-aware confidence posture, and draft-only follow-up artifacts."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(mode)}</span>
            <span className="subtle-chip">{brief.summary.returned_count} ranked priorities</span>
            <span className="subtle-chip">{brief.summary.follow_through_total_count} follow-through items</span>
            <span className="subtle-chip">{brief.prep_checklist.summary.returned_count} prep checklist items</span>
            <StatusBadge
              status={brief.summary.trust_confidence_posture}
              label={`${brief.summary.trust_confidence_posture} confidence`}
            />
          </div>
        }
      />

      <ChiefOfStaffPriorityPanel
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffFollowThroughPanel
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
      <ChiefOfStaffPreparationPanel
        brief={brief}
        source={briefSource}
        unavailableReason={briefUnavailableReason}
      />
    </div>
  );
}
