import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CalendarEventList } from "./calendar-event-list";

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

const baseAccount = {
  id: "calendar-account-1",
  provider: "google_calendar",
  auth_kind: "oauth_access_token",
  provider_account_id: "acct-owner-001",
  email_address: "owner@gmail.example",
  display_name: "Owner",
  scope: "https://www.googleapis.com/auth/calendar.readonly" as const,
  created_at: "2026-03-18T10:00:00Z",
  updated_at: "2026-03-18T10:00:00Z",
};

const baseEvents = [
  {
    provider_event_id: "evt-001",
    status: "confirmed",
    summary: "Planning",
    start_time: "2026-03-20T09:00:00+00:00",
    end_time: "2026-03-20T09:30:00+00:00",
    html_link: "https://calendar.google.com/event?eid=evt-001",
    updated_at: "2026-03-19T09:00:00+00:00",
  },
  {
    provider_event_id: "evt-002",
    status: "tentative",
    summary: "Retro",
    start_time: "2026-03-20T11:00:00+00:00",
    end_time: "2026-03-20T11:30:00+00:00",
    html_link: null,
    updated_at: "2026-03-19T10:00:00+00:00",
  },
];

describe("CalendarEventList", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders discovered event links that preserve selection and bounded filter state", () => {
    render(
      <CalendarEventList
        account={baseAccount}
        source="live"
        events={baseEvents}
        summary={{
          total_count: 2,
          limit: 20,
          order: ["start_time_asc", "provider_event_id_asc"],
          time_min: "2026-03-20T00:00:00Z",
          time_max: "2026-03-21T00:00:00Z",
        }}
        selectedEventId="evt-002"
        limit={20}
        timeMin="2026-03-20T00:00:00Z"
        timeMax="2026-03-21T00:00:00Z"
      />,
    );

    expect(screen.getByRole("link", { name: /Planning/i })).toHaveAttribute(
      "href",
      "/calendar?account=calendar-account-1&event=evt-001&limit=20&time_min=2026-03-20T00%3A00%3A00Z&time_max=2026-03-21T00%3A00%3A00Z",
    );
    expect(screen.getByRole("link", { name: /Retro/i })).toHaveAttribute(
      "href",
      "/calendar?account=calendar-account-1&event=evt-002&limit=20&time_min=2026-03-20T00%3A00%3A00Z&time_max=2026-03-21T00%3A00%3A00Z",
    );
    expect(screen.getByRole("link", { name: /Retro/i })).toHaveAttribute("aria-current", "page");
  });

  it("renders explicit unavailable state when event discovery is unavailable", () => {
    render(
      <CalendarEventList
        account={baseAccount}
        source="unavailable"
        events={[]}
        summary={null}
        selectedEventId=""
        unavailableReason="calendar events could not be fetched"
        limit={20}
        timeMin=""
        timeMax=""
      />,
    );

    expect(screen.getByText("Discovered events unavailable")).toBeInTheDocument();
    expect(screen.getByText("Events unavailable")).toBeInTheDocument();
    expect(screen.getByText("calendar events could not be fetched")).toBeInTheDocument();
  });
});
