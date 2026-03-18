"use client";

import Link from "next/link";

import type { ResponseHistoryEntry, ThreadEventItem } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";

type ContinuitySource = "live" | "fixture" | "unavailable";

type ResponseHistoryProps = {
  entries: ResponseHistoryEntry[];
  events?: ThreadEventItem[];
  threadTitle?: string;
  source?: ContinuitySource;
  unavailableReason?: string;
  traceHrefPrefix?: string;
};

type TranscriptItem = {
  id: string;
  createdAt: string;
  text: string;
  role: "user" | "assistant";
  sequenceNo?: number;
  sessionId?: string | null;
  model?: string | null;
  modelProvider?: string | null;
  sourceLabel: string;
  trace?: ResponseHistoryEntry["trace"];
};

const TRANSCRIPT_LIMIT = 16;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function getConversationRole(kind: string) {
  if (kind === "message.user" || kind.endsWith(".user")) {
    return "user";
  }

  if (kind === "message.assistant" || kind.endsWith(".assistant")) {
    return "assistant";
  }

  return null;
}

function extractTranscriptText(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }

  const record = payload as Record<string, unknown>;

  if (typeof record.text === "string" && record.text.trim()) {
    return record.text.trim();
  }

  if (typeof record.summary === "string" && record.summary.trim()) {
    return record.summary.trim();
  }

  return null;
}

function extractAssistantModel(payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { model: null, modelProvider: null };
  }

  const record = payload as Record<string, unknown>;
  const modelRecord =
    record.model && typeof record.model === "object" && !Array.isArray(record.model)
      ? (record.model as Record<string, unknown>)
      : null;

  return {
    model: typeof modelRecord?.model === "string" ? modelRecord.model : null,
    modelProvider: typeof modelRecord?.provider === "string" ? modelRecord.provider : null,
  };
}

function buildContinuityTranscriptItem(event: ThreadEventItem): TranscriptItem | null {
  const role = getConversationRole(event.kind);
  const text = extractTranscriptText(event.payload);

  if (!role || !text) {
    return null;
  }

  const assistantModel = role === "assistant" ? extractAssistantModel(event.payload) : null;

  return {
    id: event.id,
    createdAt: event.created_at,
    text,
    role,
    sequenceNo: event.sequence_no,
    sessionId: event.session_id,
    model: assistantModel?.model ?? null,
    modelProvider: assistantModel?.modelProvider ?? null,
    sourceLabel: "Continuity event",
  };
}

function isTranscriptItem(item: TranscriptItem | null): item is TranscriptItem {
  return item !== null;
}

function buildLocalTranscriptItems(entries: ResponseHistoryEntry[], events: ThreadEventItem[]) {
  const persistedAssistantEventIds = new Set(
    events
      .map((event) => event.id)
      .filter((eventId) => typeof eventId === "string" && eventId.length > 0),
  );

  return entries.flatMap<TranscriptItem>((entry) => {
    if (entry.assistantEventId && persistedAssistantEventIds.has(entry.assistantEventId)) {
      return [];
    }

    return [
      {
        id: `${entry.id}:user`,
        createdAt: entry.submittedAt,
        text: entry.message,
        role: "user" as const,
        sequenceNo: undefined,
        sessionId: null,
        model: null,
        modelProvider: null,
        sourceLabel: entry.source === "live" ? "Live response" : "Fixture preview",
        trace: undefined,
      },
      {
        id: `${entry.id}:assistant`,
        createdAt: entry.submittedAt,
        text: entry.assistantText,
        role: "assistant" as const,
        sequenceNo: entry.assistantSequenceNo,
        sessionId: null,
        model: entry.model,
        modelProvider: entry.modelProvider,
        sourceLabel: entry.source === "live" ? "Live response" : "Fixture preview",
        trace: entry.trace,
      },
    ];
  });
}

function compareTranscriptItems(left: TranscriptItem, right: TranscriptItem) {
  const timeDelta = new Date(left.createdAt).getTime() - new Date(right.createdAt).getTime();

  if (timeDelta !== 0) {
    return timeDelta;
  }

  if (left.sequenceNo !== undefined && right.sequenceNo !== undefined && left.sequenceNo !== right.sequenceNo) {
    return left.sequenceNo - right.sequenceNo;
  }

  if (left.role !== right.role) {
    return left.role === "user" ? -1 : 1;
  }

  return left.id.localeCompare(right.id);
}

export function ResponseHistory({
  entries,
  events = [],
  threadTitle,
  source = "fixture",
  unavailableReason,
  traceHrefPrefix,
}: ResponseHistoryProps) {
  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Transcript"
        title="Transcript unavailable"
        description="The selected thread could not load a readable continuity transcript."
        className="section-card--history"
      >
        <EmptyState
          title="Transcript unavailable"
          description={unavailableReason ?? "Try again once the continuity API is reachable."}
        />
      </SectionCard>
    );
  }

  if (!threadTitle) {
    return (
      <SectionCard
        eyebrow="Transcript"
        title="No thread selected"
        description="Choose a visible thread before reading or extending the durable conversation record."
        className="section-card--history"
      >
        <EmptyState
          title="Select a thread"
          description="The selected thread transcript appears here once one continuity record is active."
        />
      </SectionCard>
    );
  }

  const conversationItems = events.map(buildContinuityTranscriptItem).filter(isTranscriptItem);
  const localItems = buildLocalTranscriptItems(entries, events);
  const transcriptItems = [...conversationItems, ...localItems].sort(compareTranscriptItems);
  const visibleItems = transcriptItems.slice(-TRANSCRIPT_LIMIT);
  const hiddenItemCount = transcriptItems.length - visibleItems.length;

  return (
    <SectionCard
      eyebrow="Transcript"
      title="Selected-thread transcript"
      description={
        source === "live"
          ? "The conversation surface is derived from immutable continuity events so the selected thread stays the durable source of truth."
          : "Fixture mode previews the transcript structure with bounded continuity records and explicit fallbacks."
      }
      className="section-card--history"
    >
      <div className="transcript-summary">
        <span className="subtle-chip">Thread: {threadTitle}</span>
        <span className="subtle-chip">{transcriptItems.length} conversation entries</span>
        <span className="subtle-chip">{source === "live" ? "Live continuity" : "Fixture continuity"}</span>
      </div>

      {visibleItems.length === 0 ? (
        <>
          <EmptyState
            title="No transcript yet"
            description="Conversation messages will appear here once the selected thread captures user or assistant continuity events."
          />
          <p className="responsive-note">No assistant replies yet</p>
        </>
      ) : (
        <>
          {hiddenItemCount > 0 ? (
            <p className="responsive-note">
              Showing the latest {TRANSCRIPT_LIMIT} conversation entries to keep the transcript
              bounded and readable.
            </p>
          ) : null}

          <div className="transcript-stream">
            {visibleItems.map((item) => (
              <article
                key={item.id}
                className={["transcript-entry", `transcript-entry--${item.role}`].join(" ")}
              >
                <div className="transcript-entry__topline">
                  <div className="transcript-entry__heading">
                    <span className={["transcript-entry__role", `transcript-entry__role--${item.role}`].join(" ")}>
                      {item.role === "user" ? "Operator" : "Assistant"}
                    </span>
                    <span className="history-entry__label">{item.sourceLabel}</span>
                  </div>
                  <span className="subtle-chip">{formatDate(item.createdAt)}</span>
                </div>

                <p className="transcript-entry__content">{item.text}</p>

                <div className="transcript-entry__footer">
                  {item.sequenceNo !== undefined ? (
                    <span className="meta-pill">Sequence {item.sequenceNo}</span>
                  ) : null}
                  {item.sessionId ? <span className="meta-pill mono">{item.sessionId}</span> : null}
                  {item.model ? <span className="meta-pill">Model {item.model}</span> : null}
                  {item.modelProvider ? <span className="meta-pill">Provider {item.modelProvider}</span> : null}
                </div>

                {item.trace ? (
                  <div className="cluster">
                    <Link
                      href={`${traceHrefPrefix ?? "/traces?trace="}${encodeURIComponent(item.trace.compileTraceId)}`}
                      className="button-secondary"
                    >
                      Open compile trace
                    </Link>
                    <Link
                      href={`${traceHrefPrefix ?? "/traces?trace="}${encodeURIComponent(item.trace.responseTraceId)}`}
                      className="button-secondary"
                    >
                      Open response trace
                    </Link>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        </>
      )}
    </SectionCard>
  );
}
