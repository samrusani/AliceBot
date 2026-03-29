import { ContinuityCaptureForm } from "../../components/continuity-capture-form";
import { ContinuityInboxList } from "../../components/continuity-inbox-list";
import { EmptyState } from "../../components/empty-state";
import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { StatusBadge } from "../../components/status-badge";
import type { ApiSource, ContinuityCaptureInboxItem, ContinuityCaptureInboxSummary } from "../../lib/api";
import {
  combinePageModes,
  getApiConfig,
  getContinuityCaptureDetail,
  hasLiveApiConfig,
  listContinuityCaptures,
  pageModeLabel,
} from "../../lib/api";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function normalizeParam(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return normalizeParam(value[0]);
  }
  return value?.trim() ?? "";
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

  const pageMode = combinePageModes(listSource, selectedSource);

  return (
    <main className="stack">
      <PageHeader
        eyebrow="Continuity"
        title="Fast Capture Inbox"
        description="Capture quickly, preserve immutable events, and promote durable continuity objects only with explicit or high-confidence signals."
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
    </main>
  );
}
