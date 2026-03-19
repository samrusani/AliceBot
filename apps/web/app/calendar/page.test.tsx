import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CalendarPage from "./page";

const {
  getApiConfigMock,
  getCalendarAccountDetailMock,
  hasLiveApiConfigMock,
  listCalendarAccountsMock,
  listCalendarEventsMock,
  listTaskWorkspacesMock,
} = vi.hoisted(() => ({
  getApiConfigMock: vi.fn(),
  getCalendarAccountDetailMock: vi.fn(),
  hasLiveApiConfigMock: vi.fn(),
  listCalendarAccountsMock: vi.fn(),
  listCalendarEventsMock: vi.fn(),
  listTaskWorkspacesMock: vi.fn(),
}));

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

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    getApiConfig: getApiConfigMock,
    getCalendarAccountDetail: getCalendarAccountDetailMock,
    hasLiveApiConfig: hasLiveApiConfigMock,
    listCalendarAccounts: listCalendarAccountsMock,
    listCalendarEvents: listCalendarEventsMock,
    listTaskWorkspaces: listTaskWorkspacesMock,
  };
});

describe("CalendarPage", () => {
  beforeEach(() => {
    getApiConfigMock.mockReset();
    getCalendarAccountDetailMock.mockReset();
    hasLiveApiConfigMock.mockReset();
    listCalendarAccountsMock.mockReset();
    listCalendarEventsMock.mockReset();
    listTaskWorkspacesMock.mockReset();

    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "",
      userId: "",
      defaultThreadId: "",
      defaultToolId: "",
    });
    hasLiveApiConfigMock.mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
  });

  it("uses fixture discovery state when live API configuration is absent", async () => {
    render(await CalendarPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("Fixture-backed")).toBeInTheDocument();
    expect(screen.getByText("Fixture events")).toBeInTheDocument();
    expect(screen.getByText("Select one discovered event before submitting ingestion.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ingest selected event" })).toBeDisabled();
    expect(listCalendarEventsMock).not.toHaveBeenCalled();
  });

  it("renders live discovery state when live calendar event reads succeed", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);

    listCalendarAccountsMock.mockResolvedValue({
      items: [
        {
          id: "calendar-live-1",
          provider: "google_calendar",
          auth_kind: "oauth_access_token",
          provider_account_id: "acct-live-001",
          email_address: "owner@gmail.example",
          display_name: "Owner",
          scope: "https://www.googleapis.com/auth/calendar.readonly",
          created_at: "2026-03-18T10:00:00Z",
          updated_at: "2026-03-18T10:00:00Z",
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    getCalendarAccountDetailMock.mockResolvedValue({
      account: {
        id: "calendar-live-1",
        provider: "google_calendar",
        auth_kind: "oauth_access_token",
        provider_account_id: "acct-live-001",
        email_address: "owner@gmail.example",
        display_name: "Owner",
        scope: "https://www.googleapis.com/auth/calendar.readonly",
        created_at: "2026-03-18T10:00:00Z",
        updated_at: "2026-03-18T10:00:00Z",
      },
    });

    listCalendarEventsMock.mockResolvedValue({
      account: {
        id: "calendar-live-1",
        provider: "google_calendar",
        auth_kind: "oauth_access_token",
        provider_account_id: "acct-live-001",
        email_address: "owner@gmail.example",
        display_name: "Owner",
        scope: "https://www.googleapis.com/auth/calendar.readonly",
        created_at: "2026-03-18T10:00:00Z",
        updated_at: "2026-03-18T10:00:00Z",
      },
      items: [
        {
          provider_event_id: "evt-live-1",
          status: "confirmed",
          summary: "Live planning",
          start_time: "2026-03-20T09:00:00+00:00",
          end_time: "2026-03-20T09:30:00+00:00",
          html_link: "https://calendar.google.com/event?eid=evt-live-1",
          updated_at: "2026-03-19T10:00:00+00:00",
        },
      ],
      summary: {
        total_count: 1,
        limit: 10,
        order: ["start_time_asc", "provider_event_id_asc"],
        time_min: "2026-03-20T00:00:00Z",
        time_max: "2026-03-21T00:00:00Z",
      },
    });

    listTaskWorkspacesMock.mockResolvedValue({
      items: [
        {
          id: "workspace-1",
          task_id: "task-1",
          status: "active",
          local_path: "/tmp/task-workspaces/task-1",
          created_at: "2026-03-18T10:00:00Z",
          updated_at: "2026-03-18T10:00:00Z",
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    render(
      await CalendarPage({
        searchParams: Promise.resolve({
          account: "calendar-live-1",
          event: "evt-live-1",
          limit: "10",
          time_min: "2026-03-20T00:00:00Z",
          time_max: "2026-03-21T00:00:00Z",
        }),
      }),
    );

    expect(screen.getByText("Live events")).toBeInTheDocument();
    expect(screen.getAllByText("evt-live-1").length).toBeGreaterThan(0);
    expect(listCalendarEventsMock).toHaveBeenCalledWith(
      "https://api.example.com",
      "calendar-live-1",
      "user-1",
      {
        limit: 10,
        timeMin: "2026-03-20T00:00:00Z",
        timeMax: "2026-03-21T00:00:00Z",
      },
    );
  });

  it("falls back to fixture discovery state when live event discovery fails", async () => {
    getApiConfigMock.mockReturnValue({
      apiBaseUrl: "https://api.example.com",
      userId: "user-1",
      defaultThreadId: "thread-1",
      defaultToolId: "tool-1",
    });
    hasLiveApiConfigMock.mockReturnValue(true);

    listCalendarAccountsMock.mockResolvedValue({
      items: [
        {
          id: "c1c1c1c1-c1c1-4c1c-8c1c-c1c1c1c1c1c1",
          provider: "google_calendar",
          auth_kind: "oauth_access_token",
          provider_account_id: "acct-owner-001",
          email_address: "owner@gmail.example",
          display_name: "Owner",
          scope: "https://www.googleapis.com/auth/calendar.readonly",
          created_at: "2026-03-18T10:00:00Z",
          updated_at: "2026-03-18T10:00:00Z",
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    getCalendarAccountDetailMock.mockResolvedValue({
      account: {
        id: "c1c1c1c1-c1c1-4c1c-8c1c-c1c1c1c1c1c1",
        provider: "google_calendar",
        auth_kind: "oauth_access_token",
        provider_account_id: "acct-owner-001",
        email_address: "owner@gmail.example",
        display_name: "Owner",
        scope: "https://www.googleapis.com/auth/calendar.readonly",
        created_at: "2026-03-18T10:00:00Z",
        updated_at: "2026-03-18T10:00:00Z",
      },
    });

    listCalendarEventsMock.mockRejectedValue(new Error("calendar events could not be fetched"));
    listTaskWorkspacesMock.mockResolvedValue({
      items: [
        {
          id: "workspace-1",
          task_id: "task-1",
          status: "active",
          local_path: "/tmp/task-workspaces/task-1",
          created_at: "2026-03-18T10:00:00Z",
          updated_at: "2026-03-18T10:00:00Z",
        },
      ],
      summary: {
        total_count: 1,
        order: ["created_at_asc", "id_asc"],
      },
    });

    render(
      await CalendarPage({
        searchParams: Promise.resolve({
          account: "c1c1c1c1-c1c1-4c1c-8c1c-c1c1c1c1c1c1",
        }),
      }),
    );

    expect(screen.getByText("Mixed fallback")).toBeInTheDocument();
    expect(screen.getByText("Fixture events")).toBeInTheDocument();
    expect(screen.getAllByText(/Live event discovery read failed:/i)).toHaveLength(1);
  });
});
