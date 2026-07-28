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
        selectedProviderEventId="evt-001"
        selectedEventSource="live"
        taskWorkspaces={baseWorkspaces}
        taskWorkspaceSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

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
        selectedProviderEventId="evt-001"
        selectedEventSource="fixture"
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

  it("keeps ingestion disabled when no discovered event is selected", () => {
    render(
      <CalendarEventIngestForm
        account={baseAccount}
        accountSource="live"
        selectedProviderEventId=""
        selectedEventSource="live"
        taskWorkspaces={baseWorkspaces}
        taskWorkspaceSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

    expect(screen.getByRole("button", { name: "Ingest selected event" })).toBeDisabled();
    expect(screen.getByText("Select one discovered event before submitting ingestion.")).toBeInTheDocument();
    expect(ingestCalendarEventMock).not.toHaveBeenCalled();
  });

  it("preserves valid workspace state and resets only prop-derived status when inputs change", async () => {
    const secondWorkspace = {
      ...baseWorkspaces[0],
      id: "workspace-2",
      task_id: "task-2",
      local_path: "/tmp/task-workspaces/task-2",
    };
    const replacementWorkspace = {
      ...baseWorkspaces[0],
      id: "workspace-3",
      task_id: "task-3",
      local_path: "/tmp/task-workspaces/task-3",
    };
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
        task_workspace_id: "workspace-2",
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

    const renderForm = (account = baseAccount, taskWorkspaces = [baseWorkspaces[0], secondWorkspace]) => (
      <CalendarEventIngestForm
        account={account}
        accountSource="live"
        selectedProviderEventId="evt-001"
        selectedEventSource="live"
        taskWorkspaces={taskWorkspaces}
        taskWorkspaceSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />
    );
    const { rerender } = render(renderForm());

    fireEvent.change(screen.getByLabelText("Task workspace"), {
      target: { value: "workspace-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ingest selected event" }));
    await screen.findByText(/Ingestion completed\./i);

    rerender(renderForm({ ...baseAccount }, [{ ...baseWorkspaces[0] }, { ...secondWorkspace }]));
    expect(screen.getByLabelText("Task workspace")).toHaveValue("workspace-2");
    expect(screen.getByText("Select one task workspace to ingest the discovered event.")).toBeInTheDocument();
    expect(screen.getAllByText("calendar/acct-owner-001/evt-001.txt").length).toBeGreaterThan(0);

    rerender(renderForm({ ...baseAccount }, [replacementWorkspace]));
    expect(screen.getByLabelText("Task workspace")).toHaveValue("workspace-3");
    fireEvent.click(screen.getByRole("button", { name: "Ingest selected event" }));
    await waitFor(() => {
      expect(ingestCalendarEventMock).toHaveBeenLastCalledWith(
        "https://api.example.com",
        "calendar-account-1",
        "evt-001",
        { user_id: "user-1", task_workspace_id: "workspace-3" },
      );
    });
  });
});
