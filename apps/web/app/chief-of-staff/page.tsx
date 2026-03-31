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
  summary: {
    limit: 12,
    returned_count: 2,
    total_count: 2,
    posture_order: ["urgent", "important", "waiting", "blocked", "stale", "defer"],
    order: ["score_desc", "created_at_desc", "id_desc"],
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
        description="Deterministic priority ranking with explicit rationale, trust-aware confidence posture, and one recommended next action."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(mode)}</span>
            <span className="subtle-chip">{brief.summary.returned_count} ranked priorities</span>
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
    </div>
  );
}
