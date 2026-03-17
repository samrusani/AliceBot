import { PageHeader } from "../../components/page-header";
import { SectionCard } from "../../components/section-card";
import { TraceList, type TraceEventItem, type TraceItem } from "../../components/trace-list";
import {
  getApiConfig,
  getTraceDetail,
  getTraceEvents,
  hasLiveApiConfig,
  listTraces,
  pageModeLabel,
  type TraceReviewEventItem,
  type TraceReviewItem,
  type TraceReviewSummaryItem,
} from "../../lib/api";
import { getFixtureTrace, traceFixtures } from "../../lib/fixtures";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function formatKind(kind: string) {
  return kind
    .split(/[._]/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

function formatStatus(status: string) {
  return status.replaceAll("_", " ");
}

function shortId(value: string) {
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}

function stringifyValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  if (value === null) {
    return "null";
  }

  if (Array.isArray(value)) {
    return value.map((item) => stringifyValue(item)).join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return "unknown";
}

function buildTraceSummary(trace: TraceReviewSummaryItem | TraceReviewItem) {
  const eventLabel = trace.trace_event_count === 1 ? "ordered event" : "ordered events";
  return `${formatKind(trace.kind)} recorded ${trace.trace_event_count} ${eventLabel} for thread ${shortId(trace.thread_id)} and ended in ${formatStatus(trace.status)} status.`;
}

function buildBaseTraceItem(trace: TraceReviewSummaryItem): TraceItem {
  return {
    id: trace.id,
    kind: trace.kind,
    status: trace.status,
    title: `${formatKind(trace.kind)} review`,
    summary: buildTraceSummary(trace),
    eventCount: trace.trace_event_count,
    createdAt: trace.created_at,
    source: trace.compiler_version,
    scope: `Thread ${shortId(trace.thread_id)}`,
    related: {
      threadId: trace.thread_id,
      compilerVersion: trace.compiler_version,
    },
    metadata: [
      `Trace: ${trace.id}`,
      `Thread: ${trace.thread_id}`,
      `Compiler: ${trace.compiler_version}`,
      `Status: ${formatStatus(trace.status)}`,
    ],
    evidence: [],
    events: [],
    detailSource: "live",
    eventSource: "live",
  };
}

function buildEventFacts(event: TraceReviewEventItem) {
  const payload = event.payload;
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return [`Sequence ${event.sequence_no}`, `Payload: ${stringifyValue(payload)}`];
  }

  const entries = Object.entries(payload as Record<string, unknown>).slice(0, 4);
  return [
    `Sequence ${event.sequence_no}`,
    ...entries.map(([key, value]) => `${key}: ${stringifyValue(value)}`),
  ];
}

function buildEventDetail(event: TraceReviewEventItem) {
  const payload = event.payload;
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return `This event captured payload value ${stringifyValue(payload)}.`;
  }

  const keys = Object.keys(payload as Record<string, unknown>);
  if (keys.length === 0) {
    return "This event completed without additional payload fields.";
  }

  return `This event captured ${keys.length} payload field${keys.length === 1 ? "" : "s"} for operator review.`;
}

function buildEventTitle(event: TraceReviewEventItem) {
  return `${formatKind(event.kind)} event`;
}

function buildLiveTraceItem(
  trace: TraceReviewItem,
  events: TraceReviewEventItem[],
  options?: {
    detailUnavailable?: boolean;
    eventsUnavailable?: boolean;
  },
): TraceItem {
  const metadata = [
    `Trace: ${trace.id}`,
    `Thread: ${trace.thread_id}`,
    `Compiler: ${trace.compiler_version}`,
    `Status: ${formatStatus(trace.status)}`,
    ...Object.entries(trace.limits).map(([key, value]) => `Limit ${key}: ${stringifyValue(value)}`),
  ];

  const evidence = events.length
    ? [
        `${events.length} ordered event${events.length === 1 ? "" : "s"} loaded from the shipped trace review API.`,
      ]
    : ["No ordered events were returned for this trace."];

  return {
    ...buildBaseTraceItem(trace),
    metadata,
    evidence,
    events: events.map<TraceEventItem>((event) => ({
      id: event.id,
      kind: event.kind,
      title: buildEventTitle(event),
      detail: buildEventDetail(event),
      facts: buildEventFacts(event),
    })),
    detailUnavailable: options?.detailUnavailable,
    eventsUnavailable: options?.eventsUnavailable,
  };
}

export default async function TracesPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}) {
  const params = (searchParams ? await searchParams : {}) as Record<
    string,
    string | string[] | undefined
  >;
  const requestedId = typeof params.trace === "string" ? params.trace : undefined;
  const apiConfig = getApiConfig();
  const liveModeReady = hasLiveApiConfig(apiConfig);

  let traces = traceFixtures;
  let apiUnavailable = false;

  if (liveModeReady) {
    try {
      const payload = await listTraces(apiConfig.apiBaseUrl, apiConfig.userId);
      const selectedSummary = payload.items.find((item) => item.id === requestedId) ?? payload.items[0] ?? null;
      const mapped = payload.items.map((item) => buildBaseTraceItem(item));

      if (selectedSummary) {
        const selectedIndex = mapped.findIndex((item) => item.id === selectedSummary.id);
        let selectedTrace = mapped[selectedIndex];

        try {
          const detailPayload = await getTraceDetail(
            apiConfig.apiBaseUrl,
            selectedSummary.id,
            apiConfig.userId,
          );

          try {
            const eventPayload = await getTraceEvents(
              apiConfig.apiBaseUrl,
              selectedSummary.id,
              apiConfig.userId,
            );

            selectedTrace = buildLiveTraceItem(detailPayload.trace, eventPayload.items);
          } catch {
            selectedTrace = buildLiveTraceItem(detailPayload.trace, [], {
              eventsUnavailable: true,
            });
          }
        } catch {
          selectedTrace = {
            ...selectedTrace,
            metadata: [
              `Trace: ${selectedSummary.id}`,
              `Thread: ${selectedSummary.thread_id}`,
              `Compiler: ${selectedSummary.compiler_version}`,
              `Status: ${formatStatus(selectedSummary.status)}`,
            ],
            evidence: [
              "The selected summary came from the live trace list, but full trace detail could not be read.",
            ],
            detailUnavailable: true,
            eventsUnavailable: true,
          };
        }

        if (selectedIndex >= 0) {
          mapped[selectedIndex] = selectedTrace;
        }
      }

      traces = mapped;
    } catch {
      traces = [];
      apiUnavailable = true;
    }
  } else {
    const selectedFixture = requestedId ? getFixtureTrace(requestedId) : null;
    if (selectedFixture) {
      traces = [selectedFixture, ...traceFixtures.filter((item) => item.id !== selectedFixture.id)];
    }
  }

  const selectedId = requestedId ?? traces[0]?.id;
  const pageMode = liveModeReady ? "live" : "fixture";

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Explainability"
        title="Trace and explain-why review"
        description="Trace review keeps explanation calm and bounded: live summaries first, key metadata second, and ordered events last."
        meta={
          <div className="header-meta">
            <span className="subtle-chip">{pageModeLabel(pageMode)}</span>
            <span className="subtle-chip">
              {apiUnavailable ? "Trace API unavailable" : `${traces.length} entries`}
            </span>
          </div>
        }
      />

      <TraceList traces={traces} selectedId={selectedId} apiUnavailable={apiUnavailable} />

      <SectionCard
        eyebrow="Review guidance"
        title="What operators should verify"
        description="The explain-why view is designed to stay readable before action."
      >
        <ul className="bullet-list">
          <li>Whether the summary matches the trace kind, status, and ordered event count returned by the backend.</li>
          <li>Whether key metadata keeps thread, compiler, and limit context visible without turning into a debugger dump.</li>
          <li>Whether the ordered events explain the outcome clearly enough without requiring broader trace filtering or mutation scope.</li>
        </ul>
      </SectionCard>
    </div>
  );
}
