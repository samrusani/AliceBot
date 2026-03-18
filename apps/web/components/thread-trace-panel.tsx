import Link from "next/link";

import type {
  ApiSource,
  ThreadItem,
  TraceReviewEventItem,
  TraceReviewItem,
  TraceReviewSummaryItem,
} from "../lib/api";
import { getTraceDetail, getTraceEvents, listTraces } from "../lib/api";
import { getFixtureTrace } from "../lib/fixtures";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";
import type { TraceEventItem, TraceItem } from "./trace-list";

export type ThreadTraceTarget = {
  id: string;
  label: string;
};

type ThreadTracePanelProps = {
  thread: ThreadItem | null;
  source: ApiSource;
  traceTargets: ThreadTraceTarget[];
  selectedTraceId?: string;
  traceHrefPrefix?: string;
  apiBaseUrl?: string;
  userId?: string;
};

type TraceOption = {
  id: string;
  label: string;
  available: boolean;
  status?: string;
  eventCount?: number;
};

type LoadedTraceState = {
  modeLabel: string;
  options: TraceOption[];
  trace: TraceItem | null;
  unavailableReason?: string;
  unresolvedTargetIds: string[];
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

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

function buildLiveTraceItem(
  trace: TraceReviewItem,
  events: TraceReviewEventItem[],
  options?: {
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
    eventsUnavailable: options?.eventsUnavailable,
  };
}

function normalizeTargets(traceTargets: ThreadTraceTarget[]) {
  const targetMap = new Map<string, ThreadTraceTarget>();

  for (const target of traceTargets) {
    const id = target.id.trim();
    if (!id || targetMap.has(id)) {
      continue;
    }

    targetMap.set(id, {
      id,
      label: target.label,
    });
  }

  return [...targetMap.values()];
}

function buildTraceHref(traceId: string, traceHrefPrefix?: string) {
  const prefix = traceHrefPrefix ?? "/traces?trace=";
  return `${prefix}${encodeURIComponent(traceId)}`;
}

function toMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

function prioritizeId(ids: string[], prioritizedId: string) {
  if (!prioritizedId || !ids.includes(prioritizedId)) {
    return ids;
  }

  return [prioritizedId, ...ids.filter((id) => id !== prioritizedId)];
}

async function loadFixtureTraceState(
  normalizedTargets: ThreadTraceTarget[],
  selectedTraceId: string,
): Promise<LoadedTraceState> {
  const targetLabelById = new Map(normalizedTargets.map((target) => [target.id, target.label]));
  const scopedTargetIds = prioritizeId(
    [...new Set(normalizedTargets.map((target) => target.id))],
    selectedTraceId,
  );
  const fixtureById = new Map<string, TraceItem>(
    scopedTargetIds
      .map((traceId) => [traceId, getFixtureTrace(traceId)] as const)
      .filter((entry): entry is readonly [string, TraceItem] => Boolean(entry[1])),
  );

  const availableOptions = scopedTargetIds
    .map<TraceOption>((traceId) => {
      const fixtureTrace = fixtureById.get(traceId);
      return {
        id: traceId,
        label: targetLabelById.get(traceId) ?? `Trace ${shortId(traceId)}`,
        available: Boolean(fixtureTrace),
        status: fixtureTrace?.status,
        eventCount: fixtureTrace?.eventCount,
      };
    })
    .filter((option) => option.available);

  const trace = fixtureById.get(availableOptions[0]?.id ?? "") ?? null;

  return {
    modeLabel: "Fixture explainability",
    options: availableOptions,
    trace,
    unresolvedTargetIds: normalizedTargets
      .filter((target) => !fixtureById.has(target.id))
      .map((target) => target.id),
  };
}

async function loadLiveTraceState(
  threadId: string,
  normalizedTargets: ThreadTraceTarget[],
  selectedTraceId: string,
  apiBaseUrl: string,
  userId: string,
): Promise<LoadedTraceState> {
  let summaries: TraceReviewSummaryItem[] = [];
  let listUnavailableReason: string | undefined;

  try {
    const payload = await listTraces(apiBaseUrl, userId);
    summaries = payload.items;
  } catch (error) {
    listUnavailableReason = toMessage(error, "Trace summaries could not be loaded.");
  }

  const summariesById = new Map<string, TraceReviewSummaryItem>(summaries.map((trace) => [trace.id, trace]));
  const threadSummaries = summaries.filter((trace) => trace.thread_id === threadId);
  const targetLabelById = new Map(normalizedTargets.map((target) => [target.id, target.label]));
  const scopedIds = [...new Set([...normalizedTargets.map((target) => target.id), ...threadSummaries.map((trace) => trace.id)])];
  const orderedIds = prioritizeId(scopedIds, selectedTraceId);

  if (orderedIds.length === 0) {
    return {
      modeLabel: "Live explainability",
      options: [],
      trace: null,
      unavailableReason: listUnavailableReason,
      unresolvedTargetIds: [],
    };
  }

  const options = orderedIds.map<TraceOption>((id) => {
    const summary = summariesById.get(id);
    return {
      id,
      label: targetLabelById.get(id) ?? (summary ? `${formatKind(summary.kind)} trace` : `Trace ${shortId(id)}`),
      available: Boolean(summary),
      status: summary?.status,
      eventCount: summary?.trace_event_count,
    };
  });

  const activeId = orderedIds[0];
  const selectedSummary = summariesById.get(activeId);
  let trace: TraceItem | null = null;

  try {
    const detailPayload = await getTraceDetail(apiBaseUrl, activeId, userId);

    try {
      const eventPayload = await getTraceEvents(apiBaseUrl, activeId, userId);
      trace = buildLiveTraceItem(detailPayload.trace, eventPayload.items);
    } catch {
      trace = buildLiveTraceItem(detailPayload.trace, [], {
        eventsUnavailable: true,
      });
    }
  } catch (error) {
    if (selectedSummary) {
      trace = {
        ...buildBaseTraceItem(selectedSummary),
        evidence: [
          "The selected summary came from the live trace list, but full trace detail could not be read.",
        ],
        detailUnavailable: true,
        eventsUnavailable: true,
      };
    } else if (!listUnavailableReason) {
      return {
        modeLabel: "Live explainability",
        options,
        trace: null,
        unavailableReason: toMessage(error, "Trace detail could not be loaded."),
        unresolvedTargetIds: normalizedTargets
          .filter((target) => !summariesById.has(target.id))
          .map((target) => target.id),
      };
    }
  }

  return {
    modeLabel: "Live explainability",
    options,
    trace,
    unavailableReason: listUnavailableReason,
    unresolvedTargetIds: normalizedTargets
      .filter((target) => !summariesById.has(target.id))
      .map((target) => target.id),
  };
}

export async function ThreadTracePanel({
  thread,
  source,
  traceTargets,
  selectedTraceId = "",
  traceHrefPrefix,
  apiBaseUrl,
  userId,
}: ThreadTracePanelProps) {
  if (!thread) {
    return (
      <SectionCard
        eyebrow="Explain why"
        title="Thread-linked explainability"
        description="A bounded explain-why inspector appears here once one thread is selected."
      >
        <EmptyState
          title="Select a thread"
          description="Choose a thread first to inspect its linked trace explanation inside chat."
        />
      </SectionCard>
    );
  }

  const normalizedTargets = normalizeTargets(traceTargets);
  const state =
    source === "live" && apiBaseUrl && userId
      ? await loadLiveTraceState(thread.id, normalizedTargets, selectedTraceId, apiBaseUrl, userId)
      : await loadFixtureTraceState(normalizedTargets, selectedTraceId);

  if (state.unavailableReason && !state.trace) {
    return (
      <SectionCard
        eyebrow="Explain why"
        title="Thread-linked explainability unavailable"
        description="The selected thread's explain-why data could not be loaded from the configured trace review seam."
        className="thread-trace-panel"
      >
        <div className="thread-trace-panel__summary-row">
          <span className="subtle-chip">Thread: {thread.title}</span>
          <span className="subtle-chip">{state.modeLabel}</span>
        </div>
        <EmptyState
          title="Explainability unavailable"
          description={state.unavailableReason}
        />
      </SectionCard>
    );
  }

  if (!state.trace) {
    const hasUnresolvedTargets = state.unresolvedTargetIds.length > 0;

    return (
      <SectionCard
        eyebrow="Explain why"
        title="No linked explain-why trace"
        description="This panel stays bounded and only renders when a selected-thread trace can be read or matched."
        className="thread-trace-panel"
      >
        <div className="thread-trace-panel__summary-row">
          <span className="subtle-chip">Thread: {thread.title}</span>
          <span className="subtle-chip">{state.modeLabel}</span>
        </div>
        <EmptyState
          title={hasUnresolvedTargets ? "Linked trace unavailable" : "No linked trace yet"}
          description={
            hasUnresolvedTargets
              ? "The selected thread references trace IDs that are not currently available in this mode."
              : "When the selected thread exposes approval, task-step, execution, or response traces, a bounded explain-why inspector appears here."
          }
        />
        {hasUnresolvedTargets ? (
          <p className="responsive-note">
            Missing trace IDs: {state.unresolvedTargetIds.map((traceId) => shortId(traceId)).join(", ")}
          </p>
        ) : null}
      </SectionCard>
    );
  }

  const selectedLabel =
    state.options.find((option) => option.id === state.trace?.id)?.label ??
    `${formatKind(state.trace.kind)} trace`;
  const activeTrace = state.trace;

  return (
    <SectionCard
      eyebrow="Explain why"
      title="Thread-linked explainability"
      description="One bounded inspector keeps the selected trace summary, metadata, and ordered events visible beside transcript and workflow review."
      className="thread-trace-panel"
    >
      <div className="thread-trace-panel__summary-row">
        <StatusBadge status={activeTrace.status} />
        <span className="subtle-chip">Thread: {thread.title}</span>
        <span className="subtle-chip">{state.modeLabel}</span>
        <span className="subtle-chip">{selectedLabel}</span>
      </div>

      {state.options.length > 1 ? (
        <div className="thread-trace-panel__options">
          {state.options.map((option) => (
            <Link
              key={option.id}
              href={buildTraceHref(option.id, traceHrefPrefix)}
              className={[
                "button-secondary",
                "button-secondary--compact",
                option.id === activeTrace.id ? "is-current" : null,
              ]
                .filter(Boolean)
                .join(" ")}
              aria-current={option.id === activeTrace.id ? "page" : undefined}
            >
              {option.label}
              {option.eventCount !== undefined ? ` · ${option.eventCount} events` : ""}
            </Link>
          ))}
        </div>
      ) : null}

      <div className="trace-panel trace-panel--embedded">
        <div className="detail-summary">
          <StatusBadge status={activeTrace.status} />
          <span className="detail-summary__label">
            {activeTrace.kind.replaceAll(".", " ")} · {activeTrace.eventCount} events
          </span>
        </div>

        <div className="trace-summary">
          <h3 className="thread-trace-panel__trace-title">{activeTrace.title}</h3>
          <p>{activeTrace.summary}</p>
          <div className="attribute-list">
            <span className="attribute-item">Source: {activeTrace.source}</span>
            <span className="attribute-item">Scope: {activeTrace.scope}</span>
            <span className="attribute-item">Captured: {formatDate(activeTrace.createdAt)}</span>
            <span className="attribute-item">
              Detail: {activeTrace.detailSource === "live" ? "Live trace detail" : "Fixture trace detail"}
            </span>
            <span className="attribute-item">
              Events: {activeTrace.eventSource === "live" ? "Live event review" : "Fixture event review"}
            </span>
          </div>
        </div>

        <div className="detail-group detail-group--muted">
          <h3>Key metadata</h3>
          <div className="evidence-list">
            {activeTrace.metadata.map((item) => (
              <span key={item} className="evidence-chip">
                {item}
              </span>
            ))}
          </div>
        </div>

        {activeTrace.evidence.length > 0 ? (
          <div className="detail-group">
            <h3>Review notes</h3>
            <div className="evidence-list">
              {activeTrace.evidence.map((item) => (
                <span key={item} className="evidence-chip">
                  {item}
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <div className="detail-group">
          <h3>Ordered events</h3>
          {activeTrace.eventsUnavailable ? (
            <EmptyState
              title="Ordered events unavailable"
              description="The trace summary loaded, but ordered event reads are unavailable right now."
              className="empty-state--compact"
            />
          ) : activeTrace.events.length === 0 ? (
            <EmptyState
              title="No ordered events"
              description="This trace currently has no event records to review."
              className="empty-state--compact"
            />
          ) : (
            <ol className="trace-events">
              {activeTrace.events.map((event) => (
                <li key={event.id} className="trace-event">
                  <div className="trace-event__topline">
                    <div className="detail-stack">
                      <span className="list-row__eyebrow">{event.kind}</span>
                      <h4>{event.title}</h4>
                    </div>
                  </div>
                  <p>{event.detail}</p>
                  {event.facts?.length ? (
                    <div className="attribute-list">
                      {event.facts.map((fact) => (
                        <span key={fact} className="attribute-item">
                          {fact}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>

      <div className="thread-trace-panel__footer">
        <Link href={`/traces?trace=${activeTrace.id}`} className="button-secondary button-secondary--compact">
          Open full trace workspace
        </Link>
      </div>
    </SectionCard>
  );
}
