import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { GmailMessageIngestForm } from "./gmail-message-ingest-form";

const { ingestGmailMessageMock, refreshMock } = vi.hoisted(() => ({
  ingestGmailMessageMock: vi.fn(),
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
    ingestGmailMessage: ingestGmailMessageMock,
  };
});

const baseAccount = {
  id: "gmail-account-1",
  provider: "gmail",
  auth_kind: "oauth_access_token",
  provider_account_id: "acct-owner-001",
  email_address: "owner@gmail.example",
  display_name: "Owner",
  scope: "https://www.googleapis.com/auth/gmail.readonly" as const,
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

describe("GmailMessageIngestForm", () => {
  beforeEach(() => {
    ingestGmailMessageMock.mockReset();
    refreshMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("submits selected-message ingestion through the shipped endpoint when live mode is available", async () => {
    ingestGmailMessageMock.mockResolvedValue({
      account: baseAccount,
      message: {
        provider_message_id: "msg-001",
        artifact_relative_path: "gmail/acct-owner-001/msg-001.eml",
        media_type: "message/rfc822",
      },
      artifact: {
        id: "artifact-1",
        task_id: "task-1",
        task_workspace_id: "workspace-1",
        status: "registered",
        ingestion_status: "ingested",
        relative_path: "gmail/acct-owner-001/msg-001.eml",
        media_type_hint: "message/rfc822",
        created_at: "2026-03-18T10:10:00Z",
        updated_at: "2026-03-18T10:11:00Z",
      },
      summary: {
        total_count: 1,
        total_characters: 128,
        media_type: "message/rfc822",
        chunking_rule: "normalized_utf8_text_fixed_window_1000_chars_v1",
        order: ["sequence_no_asc", "id_asc"],
      },
    });

    render(
      <GmailMessageIngestForm
        account={baseAccount}
        accountSource="live"
        taskWorkspaces={baseWorkspaces}
        taskWorkspaceSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />,
    );

    fireEvent.change(screen.getByLabelText("Provider message ID"), {
      target: { value: "msg-001" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ingest selected message" }));

    await waitFor(() => {
      expect(ingestGmailMessageMock).toHaveBeenCalledWith(
        "https://api.example.com",
        "gmail-account-1",
        "msg-001",
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
      <GmailMessageIngestForm
        account={baseAccount}
        accountSource="fixture"
        taskWorkspaces={baseWorkspaces}
        taskWorkspaceSource="fixture"
      />,
    );

    expect(screen.getByRole("button", { name: "Ingest selected message" })).toBeDisabled();
    expect(
      screen.getByText(
        "Message ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
      ),
    ).toBeInTheDocument();
    expect(ingestGmailMessageMock).not.toHaveBeenCalled();
  });

  it("preserves typed input and result while reconciling workspace and status props", async () => {
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
    ingestGmailMessageMock.mockResolvedValue({
      account: baseAccount,
      message: {
        provider_message_id: "msg-001",
        artifact_relative_path: "gmail/acct-owner-001/msg-001.eml",
        media_type: "message/rfc822",
      },
      artifact: {
        id: "artifact-1",
        task_id: "task-1",
        task_workspace_id: "workspace-2",
        status: "registered",
        ingestion_status: "ingested",
        relative_path: "gmail/acct-owner-001/msg-001.eml",
        media_type_hint: "message/rfc822",
        created_at: "2026-03-18T10:10:00Z",
        updated_at: "2026-03-18T10:11:00Z",
      },
      summary: {
        total_count: 1,
        total_characters: 128,
        media_type: "message/rfc822",
        chunking_rule: "normalized_utf8_text_fixed_window_1000_chars_v1",
        order: ["sequence_no_asc", "id_asc"],
      },
    });

    const renderForm = (account = baseAccount, taskWorkspaces = [baseWorkspaces[0], secondWorkspace]) => (
      <GmailMessageIngestForm
        account={account}
        accountSource="live"
        taskWorkspaces={taskWorkspaces}
        taskWorkspaceSource="live"
        apiBaseUrl="https://api.example.com"
        userId="user-1"
      />
    );
    const { rerender } = render(renderForm());

    fireEvent.change(screen.getByLabelText("Provider message ID"), {
      target: { value: "msg-001" },
    });
    fireEvent.change(screen.getByLabelText("Task workspace"), {
      target: { value: "workspace-2" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ingest selected message" }));
    await screen.findByText(/Ingestion completed\./i);

    rerender(renderForm({ ...baseAccount }, [{ ...baseWorkspaces[0] }, { ...secondWorkspace }]));
    expect(screen.getByLabelText("Provider message ID")).toHaveValue("msg-001");
    expect(screen.getByLabelText("Task workspace")).toHaveValue("workspace-2");
    expect(screen.getByText("Enter one provider message ID and select one task workspace.")).toBeInTheDocument();
    expect(screen.getAllByText("gmail/acct-owner-001/msg-001.eml").length).toBeGreaterThan(0);

    rerender(renderForm({ ...baseAccount }, [replacementWorkspace]));
    expect(screen.getByLabelText("Task workspace")).toHaveValue("workspace-3");
    fireEvent.click(screen.getByRole("button", { name: "Ingest selected message" }));
    await waitFor(() => {
      expect(ingestGmailMessageMock).toHaveBeenLastCalledWith(
        "https://api.example.com",
        "gmail-account-1",
        "msg-001",
        { user_id: "user-1", task_workspace_id: "workspace-3" },
      );
    });
  });
});
