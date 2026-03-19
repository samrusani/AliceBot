"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { useRouter } from "next/navigation";

import type {
  ApiSource,
  GmailAccountRecord,
  GmailMessageIngestionResponse,
  TaskWorkspaceRecord,
} from "../lib/api";
import { ingestGmailMessage } from "../lib/api";
import { EmptyState } from "./empty-state";
import { GmailIngestionSummary } from "./gmail-ingestion-summary";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type GmailMessageIngestFormProps = {
  account: GmailAccountRecord | null;
  accountSource: ApiSource | "unavailable" | null;
  taskWorkspaces: TaskWorkspaceRecord[];
  taskWorkspaceSource: ApiSource | "unavailable";
  apiBaseUrl?: string;
  userId?: string;
};

export function GmailMessageIngestForm({
  account,
  accountSource,
  taskWorkspaces,
  taskWorkspaceSource,
  apiBaseUrl,
  userId,
}: GmailMessageIngestFormProps) {
  const router = useRouter();

  const [providerMessageId, setProviderMessageId] = useState("");
  const [taskWorkspaceId, setTaskWorkspaceId] = useState(taskWorkspaces[0]?.id ?? "");
  const [result, setResult] = useState<GmailMessageIngestionResponse | null>(null);
  const [resultSource, setResultSource] = useState<ApiSource | "unavailable" | null>(null);
  const [resultUnavailableReason, setResultUnavailableReason] = useState<string | undefined>(undefined);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");

  const liveModeReady = useMemo(
    () =>
      Boolean(
        account &&
          accountSource === "live" &&
          apiBaseUrl &&
          userId &&
          taskWorkspaceSource === "live" &&
          taskWorkspaces.length > 0,
      ),
    [account, accountSource, apiBaseUrl, userId, taskWorkspaceSource, taskWorkspaces.length],
  );

  const [statusText, setStatusText] = useState(
    !account
      ? "Select a Gmail account to enable single-message ingestion."
      : taskWorkspaces.length === 0
        ? "No task workspace is available for ingestion target selection."
        : liveModeReady
          ? "Enter one provider message ID and select one task workspace."
          : "Message ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
  );

  useEffect(() => {
    const hasWorkspace = taskWorkspaces.some((workspace) => workspace.id === taskWorkspaceId);
    if (!hasWorkspace) {
      setTaskWorkspaceId(taskWorkspaces[0]?.id ?? "");
    }
  }, [taskWorkspaceId, taskWorkspaces]);

  useEffect(() => {
    if (!account) {
      setStatusTone("info");
      setStatusText("Select a Gmail account to enable single-message ingestion.");
      return;
    }

    if (taskWorkspaces.length === 0) {
      setStatusTone("info");
      setStatusText("No task workspace is available for ingestion target selection.");
      return;
    }

    if (!liveModeReady) {
      setStatusTone("info");
      setStatusText(
        "Message ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
      );
      return;
    }

    setStatusTone("info");
    setStatusText("Enter one provider message ID and select one task workspace.");
  }, [account, liveModeReady, taskWorkspaces.length]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!account) {
      setStatusTone("danger");
      setStatusText("Select a Gmail account before submitting ingestion.");
      return;
    }

    if (!taskWorkspaceId) {
      setStatusTone("danger");
      setStatusText("Select a task workspace before submitting ingestion.");
      return;
    }

    if (!apiBaseUrl || !userId || !liveModeReady) {
      setStatusTone("info");
      setStatusText(
        "Message ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
      );
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Submitting message ingestion...");
    setResultUnavailableReason(undefined);

    try {
      const payload = await ingestGmailMessage(
        apiBaseUrl,
        account.id,
        providerMessageId.trim(),
        {
          user_id: userId,
          task_workspace_id: taskWorkspaceId,
        },
      );

      setResult(payload);
      setResultSource("live");
      setStatusTone("success");
      setStatusText(`Ingestion completed. Artifact path: ${payload.message.artifact_relative_path}`);
      router.refresh();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Ingestion failed";
      setResult(null);
      setResultSource("unavailable");
      setResultUnavailableReason(detail);
      setStatusTone("danger");
      setStatusText(`Unable to ingest message: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = Boolean(
    liveModeReady && taskWorkspaceId && providerMessageId.trim() && !isSubmitting,
  );

  if (!account) {
    return (
      <div className="stack">
        <SectionCard
          eyebrow="Ingest message"
          title="No account selected"
          description="Select one Gmail account before ingesting one provider message into a task workspace."
        >
          <EmptyState
            title="Ingestion form is disabled"
            description="Choose one account from the list to activate this bounded ingestion action."
          />
        </SectionCard>
        <GmailIngestionSummary result={null} source={null} />
      </div>
    );
  }

  return (
    <div className="stack">
      <SectionCard
        eyebrow="Ingest message"
        title="Single-message ingestion"
        description="Ingest one provider message id into one selected task workspace through the shipped RFC822 artifact seam."
      >
        <form className="detail-stack" onSubmit={handleSubmit}>
          <div className="cluster">
            <StatusBadge
              status={accountSource ?? "unavailable"}
              label={
                accountSource === "live"
                  ? "Live account"
                  : accountSource === "fixture"
                    ? "Fixture account"
                    : "Account unavailable"
              }
            />
            <StatusBadge
              status={taskWorkspaceSource}
              label={
                taskWorkspaceSource === "live"
                  ? "Live workspaces"
                  : taskWorkspaceSource === "fixture"
                    ? "Fixture workspaces"
                    : "Workspaces unavailable"
              }
            />
          </div>

          <div className="form-field">
            <label htmlFor="gmail-provider-message-id">Provider message ID</label>
            <input
              id="gmail-provider-message-id"
              name="gmail-provider-message-id"
              value={providerMessageId}
              onChange={(event) => setProviderMessageId(event.target.value)}
              placeholder="msg-001"
              required
              disabled={!liveModeReady || isSubmitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="gmail-task-workspace-id">Task workspace</label>
            <select
              id="gmail-task-workspace-id"
              name="gmail-task-workspace-id"
              value={taskWorkspaceId}
              onChange={(event) => setTaskWorkspaceId(event.target.value)}
              disabled={!liveModeReady || isSubmitting || taskWorkspaces.length === 0}
            >
              {taskWorkspaces.length === 0 ? (
                <option value="">No task workspace available</option>
              ) : (
                taskWorkspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.id} · {workspace.local_path}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="composer-actions">
            <div className="composer-status" aria-live="polite">
              <StatusBadge
                status={
                  isSubmitting
                    ? "submitting"
                    : statusTone === "success"
                      ? "success"
                      : statusTone === "danger"
                        ? "error"
                        : liveModeReady
                          ? "info"
                          : "unavailable"
                }
                label={
                  isSubmitting
                    ? "Submitting"
                    : statusTone === "success"
                      ? "Ingested"
                      : statusTone === "danger"
                        ? "Attention"
                        : liveModeReady
                          ? "Ready"
                          : "Unavailable"
                }
              />
              <span>{statusText}</span>
            </div>
            <button type="submit" className="button" disabled={!canSubmit}>
              {isSubmitting ? "Submitting..." : "Ingest selected message"}
            </button>
          </div>
        </form>
      </SectionCard>

      <GmailIngestionSummary
        result={result}
        source={resultSource}
        unavailableReason={resultUnavailableReason}
      />
    </div>
  );
}
