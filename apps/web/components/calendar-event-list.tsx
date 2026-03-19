import Link from "next/link";

import type {
  ApiSource,
  CalendarAccountRecord,
  CalendarEventListSummary,
  CalendarEventSummaryRecord,
} from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type CalendarEventListProps = {
  account: CalendarAccountRecord | null;
  source: ApiSource | "unavailable" | null;
  events: CalendarEventSummaryRecord[];
  summary: CalendarEventListSummary | null;
  selectedEventId: string;
  unavailableReason?: string;
  limit: number;
  timeMin: string;
  timeMax: string;
};

function formatDateTime(value: string | null) {
  if (!value) {
    return "Start time unavailable";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function buildCalendarHref(
  accountId: string,
  eventId: string,
  limit: number,
  timeMin: string,
  timeMax: string,
) {
  const searchParams = new URLSearchParams();
  searchParams.set("account", accountId);
  searchParams.set("event", eventId);
  searchParams.set("limit", String(limit));

  if (timeMin.trim()) {
    searchParams.set("time_min", timeMin.trim());
  }
  if (timeMax.trim()) {
    searchParams.set("time_max", timeMax.trim());
  }

  return `/calendar?${searchParams.toString()}`;
}

export function CalendarEventList({
  account,
  source,
  events,
  summary,
  selectedEventId,
  unavailableReason,
  limit,
  timeMin,
  timeMax,
}: CalendarEventListProps) {
  if (!account) {
    return (
      <SectionCard
        eyebrow="Event discovery"
        title="No account selected"
        description="Select one Calendar account before loading bounded discovered events."
      >
        <EmptyState
          title="Event discovery is idle"
          description="Choose one account from the list to review and select one discovered event."
        />
      </SectionCard>
    );
  }

  if (source === "unavailable") {
    return (
      <SectionCard
        eyebrow="Event discovery"
        title="Discovered events unavailable"
        description="The selected account loaded, but discovered events are currently unavailable."
      >
        <div className="detail-stack">
          <StatusBadge status="unavailable" label="Events unavailable" />
          {unavailableReason ? (
            <div className="execution-summary__note execution-summary__note--danger">
              <p className="execution-summary__label">Event discovery read</p>
              <p>{unavailableReason}</p>
            </div>
          ) : null}
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Event discovery"
      title="Bounded discovered events"
      description="Refresh bounded discovery results, then select one discovered event for explicit ingestion."
    >
      <div className="list-panel">
        <div className="list-panel__header">
          <div className="cluster">
            <StatusBadge
              status={source ?? "unavailable"}
              label={
                source === "live"
                  ? "Live events"
                  : source === "fixture"
                    ? "Fixture events"
                    : "Events unavailable"
              }
            />
            {summary ? <span className="meta-pill">{summary.total_count} listed</span> : null}
            {summary ? <span className="meta-pill">Limit {summary.limit}</span> : null}
          </div>
        </div>

        <form method="get" action="/calendar" className="detail-stack">
          <input type="hidden" name="account" value={account.id} />
          {selectedEventId ? <input type="hidden" name="event" value={selectedEventId} /> : null}

          <div className="form-field-group form-field-group--two-up">
            <div className="form-field">
              <label htmlFor="calendar-event-limit">Limit</label>
              <input
                id="calendar-event-limit"
                name="limit"
                type="number"
                min={1}
                max={50}
                defaultValue={limit}
              />
            </div>

            <div className="form-field">
              <label htmlFor="calendar-event-time-min">Time min (optional)</label>
              <input
                id="calendar-event-time-min"
                name="time_min"
                type="text"
                placeholder="2026-03-20T00:00:00Z"
                defaultValue={timeMin}
              />
            </div>
          </div>

          <div className="form-field">
            <label htmlFor="calendar-event-time-max">Time max (optional)</label>
            <input
              id="calendar-event-time-max"
              name="time_max"
              type="text"
              placeholder="2026-03-21T00:00:00Z"
              defaultValue={timeMax}
            />
          </div>

          <button type="submit" className="button-secondary">
            Refresh event list
          </button>
        </form>

        {unavailableReason ? (
          <p className="responsive-note">Live event discovery read failed: {unavailableReason}</p>
        ) : null}

        {events.length === 0 ? (
          <EmptyState
            title="No discovered events"
            description="Adjust the limit or optional time window, then refresh discovery for this selected account."
            className="empty-state--compact"
          />
        ) : (
          <div className="list-rows">
            {events.map((event) => (
              <Link
                key={event.provider_event_id}
                href={buildCalendarHref(account.id, event.provider_event_id, limit, timeMin, timeMax)}
                className={`list-row${event.provider_event_id === selectedEventId ? " is-selected" : ""}`}
                aria-current={event.provider_event_id === selectedEventId ? "page" : undefined}
              >
                <div className="list-row__topline">
                  <div className="detail-stack">
                    <span className="list-row__eyebrow">{formatDateTime(event.start_time)}</span>
                    <h3 className="list-row__title">{event.summary ?? "Untitled event"}</h3>
                  </div>
                  <StatusBadge status={event.status ?? "unavailable"} />
                </div>

                <div className="list-row__meta">
                  <span className="meta-pill mono">{event.provider_event_id}</span>
                  <span className="meta-pill">End: {formatDateTime(event.end_time)}</span>
                  {event.updated_at ? (
                    <span className="meta-pill">Updated: {formatDateTime(event.updated_at)}</span>
                  ) : null}
                  {event.html_link ? <span className="meta-pill">Source link available</span> : null}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </SectionCard>
  );
}
