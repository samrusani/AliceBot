"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { useRouter } from "next/navigation";

import type {
  ApiSource,
  CalendarAccountRecord,
  CalendarEventIngestionResponse,
  TaskWorkspaceRecord,
} from "../lib/api";
import { ingestCalendarEvent } from "../lib/api";
import { EmptyState } from "./empty-state";
import { CalendarIngestionSummary } from "./calendar-ingestion-summary";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";

type CalendarEventIngestFormProps = {
  account: CalendarAccountRecord | null;
  accountSource: ApiSource | "unavailable" | null;
  taskWorkspaces: TaskWorkspaceRecord[];
  taskWorkspaceSource: ApiSource | "unavailable";
  apiBaseUrl?: string;
  userId?: string;
};

export function CalendarEventIngestForm({
  account,
  accountSource,
  taskWorkspaces,
  taskWorkspaceSource,
  apiBaseUrl,
  userId,
}: CalendarEventIngestFormProps) {
  const router = useRouter();

  const [providerEventId, setProviderEventId] = useState("");
  const [taskWorkspaceId, setTaskWorkspaceId] = useState(taskWorkspaces[0]?.id ?? "");
  const [result, setResult] = useState<CalendarEventIngestionResponse | null>(null);
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
      ? "Select a Calendar account to enable single-event ingestion."
      : taskWorkspaces.length === 0
        ? "No task workspace is available for ingestion target selection."
        : liveModeReady
          ? "Enter one provider event ID and select one task workspace."
          : "Event ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
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
      setStatusText("Select a Calendar account to enable single-event ingestion.");
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
        "Event ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
      );
      return;
    }

    setStatusTone("info");
    setStatusText("Enter one provider event ID and select one task workspace.");
  }, [account, liveModeReady, taskWorkspaces.length]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!account) {
      setStatusTone("danger");
      setStatusText("Select a Calendar account before submitting ingestion.");
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
        "Event ingestion is unavailable until live API configuration, live account detail, and live task workspace list are present.",
      );
      return;
    }

    setIsSubmitting(true);
    setStatusTone("info");
    setStatusText("Submitting event ingestion...");
    setResultUnavailableReason(undefined);

    try {
      const payload = await ingestCalendarEvent(apiBaseUrl, account.id, providerEventId.trim(), {
        user_id: userId,
        task_workspace_id: taskWorkspaceId,
      });

      setResult(payload);
      setResultSource("live");
      setStatusTone("success");
      setStatusText(`Ingestion completed. Artifact path: ${payload.event.artifact_relative_path}`);
      router.refresh();
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Ingestion failed";
      setResult(null);
      setResultSource("unavailable");
      setResultUnavailableReason(detail);
      setStatusTone("danger");
      setStatusText(`Unable to ingest event: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = Boolean(
    liveModeReady && taskWorkspaceId && providerEventId.trim() && !isSubmitting,
  );

  if (!account) {
    return (
      <div className="stack">
        <SectionCard
          eyebrow="Ingest event"
          title="No account selected"
          description="Select one Calendar account before ingesting one provider event into a task workspace."
        >
          <EmptyState
            title="Ingestion form is disabled"
            description="Choose one account from the list to activate this bounded ingestion action."
          />
        </SectionCard>
        <CalendarIngestionSummary result={null} source={null} />
      </div>
    );
  }

  return (
    <div className="stack">
      <SectionCard
        eyebrow="Ingest event"
        title="Single-event ingestion"
        description="Ingest one provider event ID into one selected task workspace through the shipped text artifact seam."
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
            <label htmlFor="calendar-provider-event-id">Provider event ID</label>
            <input
              id="calendar-provider-event-id"
              name="calendar-provider-event-id"
              value={providerEventId}
              onChange={(event) => setProviderEventId(event.target.value)}
              placeholder="evt-001"
              required
              disabled={!liveModeReady || isSubmitting}
            />
          </div>

          <div className="form-field">
            <label htmlFor="calendar-task-workspace-id">Task workspace</label>
            <select
              id="calendar-task-workspace-id"
              name="calendar-task-workspace-id"
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
                      ? "Completed"
                      : statusTone === "danger"
                        ? "Error"
                        : liveModeReady
                          ? "Ready"
                          : "Unavailable"
                }
              />
              <span>{statusText}</span>
            </div>

            <button type="submit" className="button" disabled={!canSubmit}>
              Ingest selected event
            </button>
          </div>
        </form>
      </SectionCard>

      <CalendarIngestionSummary
        result={result}
        source={resultSource}
        unavailableReason={resultUnavailableReason}
      />
    </div>
  );
}
