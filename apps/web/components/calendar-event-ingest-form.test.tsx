import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CalendarEventIngestForm } from "./calendar-event-ingest-form";

const { ingestCalendarEventMock, refreshMock } = vi.hoisted(() => ({
  ingestCalendarEventMock: vi.fn(),
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshMock,
  }),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual("../lib/api");
  return {
    ...actual,
    ingestCalendarEvent: ingestCalendarEventMock,
  };
});

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

const baseWorkspaces = [
  {
    id: "workspace-1",
    task_id: "task-1",
    status: "active" as const,
    local_path: "/tmp/task-workspaces/task-1",
    created_at: "2026-03-18T10:00:00Z",
    updated_at: "2026-03-18T10:00:00Z",
  },
];

describe("CalendarEventIngestForm", () => {
  beforeEach(() => {
    ingestCalendarEventMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("submits selected-event ingestion through the shipped endpoint when live mode is available", async () => {
    ingestCalendarEventMock.mockResolvedValue({
      account: baseAccount,
      event: {
        provider_event_id: "evt-001",
        artifact_relative_path: "calendar/acct-owner-001/evt-001.txt",
        media_type: "text/plain",
      },
      artifact: {
        id: "artifact-1",
        task_id: "task-1",
        task_workspace_id: "workspace-1",
        status: "registered",
        ingestion_status: "ingested",
        relative_path: "calendar/acct-owner-001/evt-001.txt",
        media_type_hint: "text/plain",
        created_at: "2026-03-18T10:10:00Z",
        updated_at: "2026-03-18T10:11:00Z",
      },
      summary: {
        total_count: 1,
        total_characters: 256,
        media_type: "text/plain",
        chunking_rule: "normalized_utf8_text_fixed_window_1000_chars_v1",
        order: ["sequence_no_asc", "id_asc"],
      },
    });

    render(
      <CalendarEventIngestForm
        account={baseAccount}
        accountSource="live"
        taskWorkspaces={baseWorkspaces}
        taskWorkspaceSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

    fireEvent.change(screen.getByLabelText("Provider event ID"), {
      target: { value: "evt-001" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ingest selected event" }));

    await waitFor(() => {
      expect(ingestCalendarEventMock).toHaveBeenCalledWith(
        "https://api.example.com",
        "calendar-account-1",
        "evt-001",
        {
          user_id: "user-1",
          task_workspace_id: "workspace-1",
        },
      );
    });

    expect(refreshMock).toHaveBeenCalled();
    expect(screen.getByText(/Ingestion completed\./i)).toBeInTheDocument();
  });

  it("keeps ingestion disabled when live prerequisites are unavailable", () => {
    render(
      <CalendarEventIngestForm
        account={baseAccount}
        accountSource="fixture"
        taskWorkspaces={baseWorkspaces}
        taskWorkspaceSource="fixture"
      />,
    );

    expect(screen.getByRole("button", { name: "Ingest selected event" })).toBeDisabled();
    expect(
      screen.getByText(
        "Event ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
      ),
    ).toBeInTheDocument();
    expect(ingestCalendarEventMock).not.toHaveBeenCalled();
  });
});
