"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import type { ExplicitSignalCaptureResponse, ThreadEventItem, ThreadSessionItem } from "../lib/api";
import { captureExplicitSignals } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type ThreadEventListProps = {
  threadTitle?: string;
  sessions: ThreadSessionItem[];
  events: ThreadEventItem[];
  source: "live" | "fixture" | "unavailable";
  unavailableReason?: string;
  apiBaseUrl?: string;
  userId?: string;
};

const SESSION_LIMIT = 3;
const EVENT_LIMIT = 4;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function isConversationEvent(event: ThreadEventItem) {
  return event.kind === "message.user" || event.kind === "message.assistant";
}

function isCaptureEligibleEvent(event: ThreadEventItem) {
  return event.kind === "message.user";
}

function sortEligibleCaptureEvents(left: ThreadEventItem, right: ThreadEventItem) {
  if (left.sequence_no !== right.sequence_no) {
    return right.sequence_no - left.sequence_no;
  }

  const leftTimestamp = new Date(left.created_at).getTime();
  const rightTimestamp = new Date(right.created_at).getTime();
  if (leftTimestamp !== rightTimestamp) {
    return rightTimestamp - leftTimestamp;
  }

  return right.id.localeCompare(left.id);
}

function summarizePayload(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return "Structured continuity payload available.";
  }

  const record = payload as Record<string, unknown>;

  if (typeof record.summary === "string" && record.summary.trim()) {
    return record.summary;
  }

  if (typeof record.text === "string" && record.text.trim()) {
    return record.text;
  }

  const action = typeof record.action === "string" ? record.action : null;
  const scope = typeof record.scope === "string" ? record.scope : null;
  const status = typeof record.status === "string" ? record.status : null;

  if (action && scope && status) {
    return `${action} in ${scope} is ${status.replace(/_/g, " ")}.`;
  }

  if (action && scope) {
    return `${action} in ${scope}.`;
  }

  if (status) {
    return `Continuity status is ${status.replace(/_/g, " ")}.`;
  }

  return "Structured continuity payload available.";
}

function formatKind(kind: string) {
  return kind.replace(/[._]/g, " ");
}

function summarizeCaptureEventPayload(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return "User message payload available.";
  }

  const record = payload as Record<string, unknown>;

  if (typeof record.text === "string" && record.text.trim()) {
    return record.text.trim();
  }

  if (typeof record.summary === "string" && record.summary.trim()) {
    return record.summary.trim();
  }

  return "User message payload available.";
}

function formatCaptureEventOption(event: ThreadEventItem) {
  const payloadSummary = summarizeCaptureEventPayload(event.payload);
  const compactSummary =
    payloadSummary.length > 72 ? `${payloadSummary.slice(0, 69)}...` : payloadSummary;

  return `Sequence ${event.sequence_no} - ${formatDate(event.created_at)} - ${compactSummary}`;
}

function buildCaptureDisabledReason({
  source,
  unavailableReason,
  threadTitle,
  apiBaseUrl,
  userId,
  eligibleCount,
}: {
  source: ThreadEventListProps["source"];
  unavailableReason?: string;
  threadTitle?: string;
  apiBaseUrl?: string;
  userId?: string;
  eligibleCount: number;
}) {
  if (source === "unavailable") {
    return unavailableReason ?? "Continuity is unavailable, so capture is disabled for now.";
  }

  if (source === "fixture") {
    return "Fixture mode is non-destructive. Configure live API settings to enable capture.";
  }

  if (!threadTitle) {
    return "Select a thread before capturing explicit signals.";
  }

  if (!apiBaseUrl || !userId) {
    return "Live API configuration is incomplete for explicit-signal capture.";
  }

  if (eligibleCount === 0) {
    return "No eligible message.user events are available on this thread.";
  }

  return null;
}

export function ThreadEventList({
  threadTitle,
  sessions,
  events,
  source,
  unavailableReason,
  apiBaseUrl,
  userId,
}: ThreadEventListProps) {
  const eligibleCaptureEvents = useMemo(
    () => [...events].filter(isCaptureEligibleEvent).sort(sortEligibleCaptureEvents),
    [events],
  );
  const [selectedCaptureEventId, setSelectedCaptureEventId] = useState(
    eligibleCaptureEvents[0]?.id ?? "",
  );
  const [captureSummary, setCaptureSummary] =
    useState<ExplicitSignalCaptureResponse["summary"] | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  useEffect(() => {
    setSelectedCaptureEventId((currentValue) => {
      if (currentValue && eligibleCaptureEvents.some((event) => event.id === currentValue)) {
        return currentValue;
      }

      return eligibleCaptureEvents[0]?.id ?? "";
    });
  }, [eligibleCaptureEvents]);

  useEffect(() => {
    setCaptureSummary(null);
    setCaptureError(null);
  }, [selectedCaptureEventId, threadTitle, source]);

  const captureDisabledReason = buildCaptureDisabledReason({
    source,
    unavailableReason,
    threadTitle,
    apiBaseUrl,
    userId,
    eligibleCount: eligibleCaptureEvents.length,
  });
  const canCapture = !captureDisabledReason && !isCapturing;
  const disableEventSelection = source !== "live" || isCapturing || eligibleCaptureEvents.length === 0;

  let captureStatus = "info";
  let captureStatusLabel = "Prepared";
  let captureStatusText = "Ready to run explicit-signal capture for a selected message.user event.";

  if (captureDisabledReason) {
    captureStatus = source === "unavailable" ? "unavailable" : source === "fixture" ? "fixture" : "blocked";
    captureStatusLabel = source === "unavailable" ? "Unavailable" : source === "fixture" ? "Fixture" : "Blocked";
    captureStatusText = captureDisabledReason;
  } else if (isCapturing) {
    captureStatus = "submitting";
    captureStatusLabel = "Capturing";
    captureStatusText = "Running POST /v0/memories/capture-explicit-signals for the selected source event.";
  } else if (captureError) {
    captureStatus = "error";
    captureStatusLabel = "Error";
    captureStatusText = `Capture failed: ${captureError}`;
  } else if (captureSummary) {
    captureStatus = "success";
    captureStatusLabel = "Captured";
    captureStatusText = `Capture completed for source event ${captureSummary.source_event_id}.`;
  }

  async function handleCaptureSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canCapture || !selectedCaptureEventId || !apiBaseUrl || !userId) {
      setCaptureSummary(null);
      setCaptureError(captureDisabledReason ?? "Select an eligible message.user event before capturing.");
      return;
    }

    setCaptureSummary(null);
    setCaptureError(null);
    setIsCapturing(true);

    try {
      const response = await captureExplicitSignals(apiBaseUrl, {
        user_id: userId,
        source_event_id: selectedCaptureEventId,
      });
      setCaptureSummary(response.summary);
    } catch (error) {
      setCaptureError(
        error instanceof Error ? error.message : "Explicit-signal capture request failed.",
      );
    } finally {
      setIsCapturing(false);
    }
  }

  const captureControlSection = (
    <SectionCard
      eyebrow="Explicit signal capture"
      title="Manual capture control"
      description="Manually trigger unified explicit-signal capture for one selected message.user event. No automatic capture runs in this rail."
    >
      <form className="detail-stack" onSubmit={handleCaptureSubmit}>
        <div className="form-field">
          <label htmlFor="explicit-signal-source-event">Eligible user event</label>
          <select
            id="explicit-signal-source-event"
            name="explicit-signal-source-event"
            value={selectedCaptureEventId}
            onChange={(inputEvent) => setSelectedCaptureEventId(inputEvent.target.value)}
            disabled={disableEventSelection}
          >
            {eligibleCaptureEvents.length === 0 ? (
              <option value="">No eligible message.user events</option>
            ) : (
              eligibleCaptureEvents.map((captureEvent) => (
                <option key={captureEvent.id} value={captureEvent.id}>
                  {formatCaptureEventOption(captureEvent)}
                </option>
              ))
            )}
          </select>
        </div>

        <div className="composer-actions">
          <div className="composer-status" aria-live="polite">
            <StatusBadge status={captureStatus} label={captureStatusLabel} />
            <span>{captureStatusText}</span>
          </div>
          <button type="submit" className="button" disabled={!canCapture}>
            {isCapturing ? "Capturing..." : "Capture explicit signals"}
          </button>
        </div>
      </form>

      {captureSummary ? (
        <div className="detail-stack" aria-live="polite">
          <div className="detail-summary">
            <span className="detail-summary__label">Capture result summary</span>
            <span className="subtle-chip">Source event confirmed</span>
          </div>
          <p>
            {captureSummary.source_event_id} ({formatKind(captureSummary.source_event_kind)})
          </p>
          <div className="attribute-list">
            <span className="meta-pill">Candidates {captureSummary.candidate_count}</span>
            <span className="meta-pill">Admissions {captureSummary.admission_count}</span>
            <span className="meta-pill">
              Open loops created {captureSummary.open_loop_created_count}
            </span>
            <span className="meta-pill">Open loops noop {captureSummary.open_loop_noop_count}</span>
          </div>
        </div>
      ) : null}
    </SectionCard>
  );

  if (source === "unavailable") {
    return (
      <>
        {captureControlSection}
        <SectionCard
          eyebrow="Operational review"
          title="Supporting continuity unavailable"
          description="The bounded operational review panel could not load for the selected thread."
        >
          <EmptyState
            title="Operational review unavailable"
            description={unavailableReason ?? "Try again once the continuity API is reachable."}
          />
        </SectionCard>
      </>
    );
  }

  if (!threadTitle) {
    return (
      <>
        {captureControlSection}
        <SectionCard
          eyebrow="Operational review"
          title="No thread selected"
          description="Pick a visible thread before reviewing recent session state and non-conversation continuity."
        >
          <EmptyState
            title="Select a thread"
            description="Supporting continuity stays visible here once one thread is selected."
          />
        </SectionCard>
      </>
    );
  }

  const operationalEvents = events.filter((event) => !isConversationEvent(event));

  if (sessions.length === 0 && operationalEvents.length === 0) {
    return (
      <>
        {captureControlSection}
        <SectionCard
          eyebrow="Operational review"
          title="Supporting continuity"
          description="This thread exists, but no supporting session or operational continuity has been recorded yet."
        >
          <EmptyState
            title="No supporting continuity yet"
            description="Assistant and governed activity will add bounded operational review details here without cluttering the transcript."
          />
        </SectionCard>
      </>
    );
  }

  const visibleSessions = sessions.slice(-SESSION_LIMIT).reverse();
  const visibleEvents = operationalEvents.slice(-EVENT_LIMIT).reverse();

  return (
    <>
      {captureControlSection}
      <SectionCard
        eyebrow="Operational review"
        title="Bounded supporting continuity"
        description="Sessions and non-conversation events stay available for review without repeating the main transcript."
      >
        <div className="thread-review-grid">
          <div className="detail-group">
            <div className="detail-summary">
              <span className="detail-summary__label">Recent sessions</span>
              <span className="subtle-chip">{sessions.length} total</span>
            </div>

            {visibleSessions.length === 0 ? (
              <EmptyState
                title="No sessions yet"
                description="Session lifecycle updates appear here once the selected thread has started recording them."
                className="empty-state--compact"
              />
            ) : (
              <div className="timeline-list">
                {visibleSessions.map((session) => (
                  <article key={session.id} className="timeline-item">
                    <div className="timeline-item__topline">
                      <div className="detail-stack">
                        <h3 className="list-row__title">{formatDate(session.started_at ?? session.created_at)}</h3>
                        <p>{session.ended_at ? "Session closed cleanly." : "Current live session remains open."}</p>
                      </div>
                      <StatusBadge status={session.status} />
                    </div>

                    <div className="attribute-list">
                      <span className="meta-pill mono">{session.id}</span>
                      <span className="meta-pill">Started {formatDate(session.started_at ?? session.created_at)}</span>
                      {session.ended_at ? <span className="meta-pill">Ended {formatDate(session.ended_at)}</span> : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="detail-group">
            <div className="detail-summary">
              <span className="detail-summary__label">Operational events</span>
              <span className="subtle-chip">{operationalEvents.length} total</span>
            </div>

            {visibleEvents.length === 0 ? (
              <EmptyState
                title="No operational events yet"
                description="Approval, execution, and other supporting continuity events will appear here once the thread records them."
                className="empty-state--compact"
              />
            ) : (
              <div className="timeline-list">
                {visibleEvents.map((event) => (
                  <article key={event.id} className="timeline-item">
                    <div className="timeline-item__topline">
                      <div className="detail-stack">
                        <span className="history-entry__label">{formatKind(event.kind)}</span>
                        <h3 className="list-row__title">{summarizePayload(event.payload)}</h3>
                      </div>
                      <span className="subtle-chip">{formatDate(event.created_at)}</span>
                    </div>

                    <div className="attribute-list">
                      <span className="meta-pill">Sequence {event.sequence_no}</span>
                      {event.session_id ? <span className="meta-pill mono">{event.session_id}</span> : null}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      </SectionCard>
    </>
  );
}
