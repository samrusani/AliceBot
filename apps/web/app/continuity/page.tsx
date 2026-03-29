import { ContinuityCaptureForm } from "../../components/continuity-capture-form";
import { ContinuityInboxList } from "../../components/continuity-inbox-list";
import { ContinuityRecallPanel } from "../../components/continuity-recall-panel";
import { EmptyState } from "../../components/empty-state";
import { PageHeader } from "../../components/page-header";
import { ResumptionBrief } from "../../components/resumption-brief";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";
import type {
  ApiSource,
  ContinuityCaptureInboxItem,
  ContinuityCaptureInboxSummary,
  ContinuityRecallResult,
  ContinuityRecallSummary,
  ContinuityResumptionBrief,
} from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getContinuityCaptureDetail,
  getContinuityResumptionBrief,
  hasLiveApiConfig,
  listContinuityCaptures,
  pageModeLabel,
  queryContinuityRecall,
} from "../../lib/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }
  return value?.trim() ?? "";
}

function parsePositiveInt(value: string, fallback: number) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return parsed;
}

function parseNonNegativeInt(value: string, fallback: number) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
}

function resolveSelectedCaptureId(requestedCaptureId: string, items: ContinuityCaptureInboxItem[]) {
  if (!items.length) {
    return "";
  }

  const available = new Set(items.map((item) => item.capture_event.id));
  if (requestedCaptureId && available.has(requestedCaptureId)) {
    return requestedCaptureId;
  }

  return items[0]?.capture_event.id ?? "";
}

const continuityCaptureFixtures: ContinuityCaptureInboxItem[] = [
  {
    capture_event: {
      id: "capture-fixture-1",
      raw_content: "Finalize launch checklist",
      explicit_signal: "task",
      admission_posture: "DERIVED",
      admission_reason: "explicit_signal_task",
      created_at: "2026-03-29T09:00:00Z",
    },
    derived_object: {
      id: "object-fixture-1",
      capture_event_id: "capture-fixture-1",
      object_type: "NextAction",
      status: "active",
      title: "Next Action: Finalize launch checklist",
      body: {
        action_text: "Finalize launch checklist",
        raw_content: "Finalize launch checklist",
        explicit_signal: "task",
      },
      provenance: {
        capture_event_id: "capture-fixture-1",
        source_kind: "continuity_capture_event",
        admission_reason: "explicit_signal_task",
      },
      confidence: 1,
      created_at: "2026-03-29T09:00:00Z",
      updated_at: "2026-03-29T09:00:00Z",
    },
  },
  {
    capture_event: {
      id: "capture-fixture-2",
      raw_content: "Maybe revisit this next month",
      explicit_signal: null,
      admission_posture: "TRIAGE",
      admission_reason: "ambiguous_capture_requires_triage",
      created_at: "2026-03-29T09:10:00Z",
    },
    derived_object: null,
  },
];

const continuityCaptureSummaryFixture: ContinuityCaptureInboxSummary = {
  limit: 20,
  returned_count: continuityCaptureFixtures.length,
  total_count: continuityCaptureFixtures.length,
  derived_count: 1,
  triage_count: 1,
  order: ["created_at_desc", "id_desc"],
};

const continuityRecallFixtures: ContinuityRecallResult[] = [
  {
    id: "recall-fixture-1",
    capture_event_id: "capture-fixture-1",
    object_type: "NextAction",
    status: "active",
    title: "Next Action: Finalize launch checklist",
    body: {
      action_text: "Finalize launch checklist",
    },
    provenance: {
      thread_id: "thread-fixture-1",
      project: "Launch Project",
      person: "Alex",
      source_event_ids: ["event-fixture-1"],
    },
    confirmation_status: "unconfirmed",
    admission_posture: "DERIVED",
    confidence: 1,
    relevance: 121,
    scope_matches: [
      { kind: "project", value: "launch project" },
      { kind: "person", value: "alex" },
    ],
    provenance_references: [
      { source_kind: "continuity_capture_event", source_id: "capture-fixture-1" },
      { source_kind: "event", source_id: "event-fixture-1" },
      { source_kind: "thread", source_id: "thread-fixture-1" },
    ],
    ordering: {
      scope_match_count: 2,
      query_term_match_count: 1,
      confirmation_rank: 2,
      posture_rank: 2,
      confidence: 1,
    },
    created_at: "2026-03-29T09:00:00Z",
    updated_at: "2026-03-29T09:00:00Z",
  },
];

const continuityRecallSummaryFixture: ContinuityRecallSummary = {
  query: null,
  filters: {
    since: null,
    until: null,
  },
  limit: 20,
  returned_count: continuityRecallFixtures.length,
  total_count: continuityRecallFixtures.length,
  order: ["relevance_desc", "created_at_desc", "id_desc"],
};

const continuityResumptionFixture: ContinuityResumptionBrief = {
  assembly_version: "continuity_resumption_brief_v0",
  scope: {
    since: null,
    until: null,
  },
  last_decision: {
    item: null,
    empty_state: {
      is_empty: true,
      message: "No decision found in the requested scope.",
    },
  },
  open_loops: {
    items: [],
    summary: {
      limit: 5,
      returned_count: 0,
      total_count: 0,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: true,
      message: "No open loops found in the requested scope.",
    },
  },
  recent_changes: {
    items: continuityRecallFixtures,
    summary: {
      limit: 5,
      returned_count: continuityRecallFixtures.length,
      total_count: continuityRecallFixtures.length,
      order: ["created_at_desc", "id_desc"],
    },
    empty_state: {
      is_empty: false,
      message: "No recent changes found in the requested scope.",
    },
  },
  next_action: {
    item: continuityRecallFixtures[0],
    empty_state: {
      is_empty: false,
      message: "No next action found in the requested scope.",
    },
  },
  sources: ["continuity_capture_events", "continuity_objects"],
};

function renderDetail(item: ContinuityCaptureInboxItem | null, source: ApiSource | "unavailable" | null, unavailableReason?: string) {
  if (!item) {
    return (
      <SectionCard
        eyebrow="Capture detail"
        title="No capture selected"
        description="Select one capture row to inspect its immutable event payload and derived-object provenance."
      >
        <EmptyState
          title="Detail panel is idle"
          description="Choose one capture from the inbox to inspect posture and provenance."
        />
      </SectionCard>
    );
  }

  const capture = item.capture_event;
  const derived = item.derived_object;

  return (
    <SectionCard
      eyebrow="Capture detail"
      title={capture.raw_content}
      description="Derived objects remain explicitly linked to immutable capture evidence through provenance fields."
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge
            status={source ?? "unavailable"}
            label={
              source === "live"
                ? "Live detail"
                : source === "fixture"
                  ? "Fixture detail"
                  : "Detail unavailable"
            }
          />
          <StatusBadge
            status={capture.admission_posture}
            label={capture.admission_posture === "TRIAGE" ? "Triage" : "Derived"}
          />
        </div>

        {unavailableReason ? (
          <div className="execution-summary__note execution-summary__note--danger">
            <p className="execution-summary__label">Detail read</p>
            <p>{unavailableReason}</p>
          </div>
        ) : null}

        <dl className="key-value-grid key-value-grid--compact">
          <div>
            <dt>Capture ID</dt>
            <dd className="mono">{capture.id}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{capture.created_at}</dd>
          </div>
          <div>
            <dt>Explicit signal</dt>
            <dd>{capture.explicit_signal ?? "None"}</dd>
          </div>
          <div>
            <dt>Admission reason</dt>
            <dd>{capture.admission_reason}</dd>
          </div>
        </dl>

        {derived ? (
          <>
            <div className="detail-group">
              <h3>Derived object</h3>
              <pre className="execution-summary__code">{JSON.stringify(derived, null, 2)}</pre>
            </div>
            <div className="detail-group detail-group--muted">
              <h3>Provenance</h3>
              <pre className="execution-summary__code">{JSON.stringify(derived.provenance, null, 2)}</pre>
            </div>
          </>
        ) : (
          <div className="detail-group detail-group--muted">
            <h3>Triage posture</h3>
            <p className="muted-copy">
              This capture is stored immutably and visible in inbox triage. No durable object was promoted.
            </p>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

export default async function ContinuityPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;

  const requestedCaptureId = normalizeParam(params.capture);
  const recallQuery = normalizeParam(params.recall_query);
  const recallThreadId = normalizeParam(params.recall_thread);
  const recallTaskId = normalizeParam(params.recall_task);
  const recallProject = normalizeParam(params.recall_project);
  const recallPerson = normalizeParam(params.recall_person);
  const recallSince = normalizeParam(params.recall_since);
  const recallUntil = normalizeParam(params.recall_until);
  const recallLimit = parsePositiveInt(normalizeParam(params.recall_limit), 20);
  const resumptionRecentChanges = parseNonNegativeInt(normalizeParam(params.resumption_recent), 5);
  const resumptionOpenLoops = parseNonNegativeInt(normalizeParam(params.resumption_open), 5);

  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let items = continuityCaptureFixtures;
  let summary = continuityCaptureSummaryFixture;
  let listSource: ApiSource = "fixture";
  let listUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await listContinuityCaptures(apiConfig.apiBaseUrl, apiConfig.userId, {
        limit: 20,
      });
      items = payload.items;
      summary = payload.summary;
      listSource = "live";
    } catch (error) {
      listUnavailableReason =
        error instanceof Error
          ? error.message
          : "Continuity capture inbox could not be loaded.";
    }
  }

  const selectedCaptureId = resolveSelectedCaptureId(requestedCaptureId, items);
  const selectedFromList = items.find((item) => item.capture_event.id === selectedCaptureId) ?? null;
  let selectedItem = selectedFromList;
  let selectedSource: ApiSource | "unavailable" | null = selectedFromList ? listSource : null;
  let selectedUnavailableReason: string | undefined;

  if (selectedFromList && liveModeReady && listSource === "live") {
    try {
      const payload = await getContinuityCaptureDetail(
        apiConfig.apiBaseUrl,
        selectedFromList.capture_event.id,
        apiConfig.userId,
      );
      selectedItem = payload.capture;
      selectedSource = "live";
    } catch (error) {
      selectedUnavailableReason =
        error instanceof Error
          ? error.message
          : "Selected continuity capture detail could not be loaded.";
      selectedSource = "unavailable";
    }
  }

  let recallResults = continuityRecallFixtures;
  let recallSummary = continuityRecallSummaryFixture;
  let recallSource: ApiSource = "fixture";
  let recallUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await queryContinuityRecall(apiConfig.apiBaseUrl, apiConfig.userId, {
        query: recallQuery,
        threadId: recallThreadId,
        taskId: recallTaskId,
        project: recallProject,
        person: recallPerson,
        since: recallSince,
        until: recallUntil,
        limit: recallLimit,
      });
      recallResults = payload.items;
      recallSummary = payload.summary;
      recallSource = "live";
    } catch (error) {
      recallUnavailableReason =
        error instanceof Error
          ? error.message
          : "Continuity recall query could not be loaded.";
    }
  }

  let brief = continuityResumptionFixture;
  let resumptionSource: ApiSource = "fixture";
  let resumptionUnavailableReason: string | undefined;

  if (liveModeReady) {
    try {
      const payload = await getContinuityResumptionBrief(apiConfig.apiBaseUrl, apiConfig.userId, {
        query: recallQuery,
        threadId: recallThreadId,
        taskId: recallTaskId,
        project: recallProject,
        person: recallPerson,
        since: recallSince,
        until: recallUntil,
        maxRecentChanges: resumptionRecentChanges,
        maxOpenLoops: resumptionOpenLoops,
      });
      brief = payload.brief;
      resumptionSource = "live";
    } catch (error) {
      resumptionUnavailableReason =
        error instanceof Error
          ? error.message
          : "Continuity resumption brief could not be loaded.";
    }
  }

  const pageMode = combinePageModes(listSource, selectedSource, recallSource, resumptionSource);

  return (
    <main className="stack">
      <PageHeader
        eyebrow="Continuity"
        title="Continuity workspace"
        description="Capture quickly, query continuity with provenance-backed recall, and compile deterministic resumption sections."
        meta={<StatusBadge status={pageMode} label={pageModeLabel(pageMode)} />}
      />

      <ContinuityCaptureForm
        apiBaseUrl={apiConfig.apiBaseUrl}
        userId={apiConfig.userId}
        source={listSource}
      />

      <div className="grid grid--two">
        <ContinuityInboxList
          items={items}
          selectedCaptureId={selectedCaptureId}
          summary={summary}
          source={listSource}
          unavailableReason={listUnavailableReason}
        />
        {renderDetail(selectedItem, selectedSource, selectedUnavailableReason)}
      </div>

      <div className="grid grid--two">
        <ContinuityRecallPanel
          results={recallResults}
          summary={recallSummary}
          source={recallSource}
          unavailableReason={recallUnavailableReason}
          filters={{
            query: recallQuery,
            threadId: recallThreadId,
            taskId: recallTaskId,
            project: recallProject,
            person: recallPerson,
            since: recallSince,
            until: recallUntil,
            limit: recallLimit,
          }}
        />
        <ResumptionBrief
          brief={brief}
          source={resumptionSource}
          unavailableReason={resumptionUnavailableReason}
        />
      </div>
    </main>
  );
}
