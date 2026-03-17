"use client";

import Link from "next/link";
import type { FormEvent } from "react";
import { useState } from "react";

import type { ApprovalRequestPayload, RequestHistoryEntry } from "../lib/api";
import { submitApprovalRequest } from "../lib/api";
import { buildFixtureRequestEntry } from "../lib/fixtures";
import { EmptyState } from "./empty-state";
import { StatusBadge } from "./status-badge";

type RequestComposerProps = {
  initialEntries: RequestHistoryEntry[];
  apiBaseUrl?: string;
  userId?: string;
  selectedThreadId?: string;
  selectedThreadTitle?: string;
  defaultToolId?: string;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function RequestComposer({
  initialEntries,
  apiBaseUrl,
  userId,
  selectedThreadId,
  selectedThreadTitle,
  defaultToolId,
}: RequestComposerProps) {
  const [toolId, setToolId] = useState(defaultToolId ?? "");
  const [action, setAction] = useState("place_order");
  const [scope, setScope] = useState("supplements");
  const [domainHint, setDomainHint] = useState("ecommerce");
  const [riskHint, setRiskHint] = useState("purchase");
  const [attributesText, setAttributesText] = useState(
    JSON.stringify(
      {
        merchant: "Thorne",
        item: "Magnesium Bisglycinate",
        quantity: "1",
      },
      null,
      2,
    ),
  );
  const [entries, setEntries] = useState(initialEntries);
  const [statusText, setStatusText] = useState("Ready to submit a governed approval request.");
  const [statusTone, setStatusTone] = useState<"info" | "success" | "danger">("info");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const liveModeReady = Boolean(apiBaseUrl && userId);
  const activeThreadId = selectedThreadId?.trim() ?? "";
  const visibleEntries = activeThreadId
    ? entries.filter((entry) => entry.threadId === activeThreadId)
    : [];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextToolId = toolId.trim();
    const nextAction = action.trim();
    const nextScope = scope.trim();

    if (!activeThreadId || !nextToolId || !nextAction || !nextScope) {
      setStatusTone("danger");
      setStatusText("Select a thread, then provide tool ID, action, and scope.");
      return;
    }

    let attributes: Record<string, unknown>;
    try {
      const parsed = JSON.parse(attributesText);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Attributes must be a JSON object.");
      }
      attributes = parsed as Record<string, unknown>;
    } catch (error) {
      setStatusTone("danger");
      setStatusText(error instanceof Error ? error.message : "Attributes JSON is invalid.");
      return;
    }

    const payload: ApprovalRequestPayload = {
      user_id: userId ?? "fixture-user",
      thread_id: activeThreadId,
      tool_id: nextToolId,
      action: nextAction,
      scope: nextScope,
      domain_hint: domainHint.trim() || null,
      risk_hint: riskHint.trim() || null,
      attributes,
    };

    setStatusTone("info");
    setStatusText(
      liveModeReady
        ? "Submitting governed request through the approval-request endpoint..."
        : "Preparing a fixture-backed governed request preview...",
    );
    setIsSubmitting(true);

    if (!liveModeReady) {
      const entry = buildFixtureRequestEntry(payload);
      setEntries((current) => [entry, ...current]);
      setStatusTone("success");
      setStatusText(
        "Fixture request summary added. Configure the web API base URL and user ID to persist live approvals and tasks.",
      );
      setIsSubmitting(false);
      return;
    }

    try {
      const response = await submitApprovalRequest(apiBaseUrl!, payload);
      const entry: RequestHistoryEntry = {
        id: response.trace.trace_id,
        submittedAt: new Date().toISOString(),
        source: "live",
        threadId: response.request.thread_id,
        toolId: response.request.tool_id,
        toolName: response.tool.name,
        action: response.request.action,
        scope: response.request.scope,
        domainHint: response.request.domain_hint,
        riskHint: response.request.risk_hint,
        attributes: response.request.attributes,
        decision: response.decision,
        taskId: response.task.id,
        taskStatus: response.task.status,
        approvalId: response.approval?.id ?? null,
        approvalStatus: response.approval?.status ?? null,
        summary: response.approval
          ? "The request persisted an approval and downstream task state through the shipped governed workflow."
          : "The request was routed without a persisted approval record and still returned downstream task state.",
        reasons: response.reasons.map((reason) => reason.message),
        trace: {
          routingTraceId: response.routing_trace.trace_id,
          routingTraceEventCount: response.routing_trace.trace_event_count,
          requestTraceId: response.trace.trace_id,
          requestTraceEventCount: response.trace.trace_event_count,
        },
      };

      setEntries((current) => [entry, ...current]);
      setStatusTone("success");
      setStatusText("Governed request submitted successfully. Approval and task linkage are now visible below.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Request failed";
      setStatusTone("danger");
      setStatusText(`Unable to submit live request: ${detail}`);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="composer-card composer-card--request">
      <div className="composer-card__header composer-card__header--tight">
        <div className="governance-banner">
          <strong>{liveModeReady ? "Live operator mode" : "Fixture operator mode"}</strong>
          <span>Requests stay explicitly governed and the resulting approval, task, and trace links remain attached.</span>
        </div>

        <div className="selected-thread-panel">
          <div className="selected-thread-panel__copy">
            <span className="history-entry__label">Linked thread</span>
            <h2 className="composer-title">{selectedThreadTitle ?? "Choose a visible thread"}</h2>
            <p className="field-hint">
              {activeThreadId
                ? "Governed requests stay explicitly linked to the selected continuity record."
                : "Select or create a thread from the right rail before submitting a governed request."}
            </p>
          </div>
          {activeThreadId ? <span className="meta-pill mono">{activeThreadId}</span> : null}
        </div>

        <div className="form-field-group form-field-group--two-up">
          <div className="form-field">
            <label htmlFor="tool-id">Tool ID</label>
            <input
              id="tool-id"
              name="tool-id"
              value={toolId}
              onChange={(event) => setToolId(event.target.value)}
              placeholder="Tool UUID"
            />
          </div>
        </div>

        <div className="composer-intro">
          <p className="eyebrow">Governed request</p>
          <h2 className="composer-title">Approval-gated action submission</h2>
          <p className="field-hint">
            Submit the shipped approval-request payload directly. This mode is purpose-built for consequential actions, not freeform conversation.
          </p>
        </div>
      </div>

      <form className="detail-stack" onSubmit={handleSubmit}>
        <div className="form-field-group form-field-group--two-up">
          <div className="form-field">
            <label htmlFor="governed-action">Action</label>
            <input
              id="governed-action"
              name="governed-action"
              value={action}
              onChange={(event) => setAction(event.target.value)}
              placeholder="place_order"
            />
          </div>
          <div className="form-field">
            <label htmlFor="governed-scope">Scope</label>
            <input
              id="governed-scope"
              name="governed-scope"
              value={scope}
              onChange={(event) => setScope(event.target.value)}
              placeholder="supplements"
            />
          </div>
          <div className="form-field">
            <label htmlFor="domain-hint">Domain hint</label>
            <input
              id="domain-hint"
              name="domain-hint"
              value={domainHint}
              onChange={(event) => setDomainHint(event.target.value)}
              placeholder="ecommerce"
            />
          </div>
          <div className="form-field">
            <label htmlFor="risk-hint">Risk hint</label>
            <input
              id="risk-hint"
              name="risk-hint"
              value={riskHint}
              onChange={(event) => setRiskHint(event.target.value)}
              placeholder="purchase"
            />
          </div>
        </div>

        <div className="form-field">
          <label htmlFor="request-attributes">Attributes JSON</label>
          <textarea
            id="request-attributes"
            name="request-attributes"
            placeholder='{"merchant":"Thorne","item":"Magnesium Bisglycinate","quantity":"1"}'
            value={attributesText}
            onChange={(event) => setAttributesText(event.target.value)}
          />
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
                      : "info"
              }
              label={
                isSubmitting
                  ? "Submitting"
                  : statusTone === "success"
                    ? "Ready"
                    : statusTone === "danger"
                      ? "Attention"
                      : "Prepared"
              }
            />
            <span>{statusText}</span>
          </div>
          <button
            type="submit"
            className="button"
            disabled={
              isSubmitting || !activeThreadId || !toolId.trim() || !action.trim() || !scope.trim()
            }
          >
            {isSubmitting ? "Submitting..." : "Submit governed request"}
          </button>
        </div>
      </form>

      <div className="detail-stack">
        <div className="list-panel__header">
          <div>
            <p className="eyebrow">Recent activity</p>
            <h2>Recent governed request summaries</h2>
            <p>Latest submissions stay grouped with decision, approval linkage, task state, and traces.</p>
          </div>
        </div>

        {!activeThreadId ? (
          <EmptyState
            title="Select a thread first"
            description="Governed request summaries appear here after one visible thread is selected and used."
          />
        ) : visibleEntries.length === 0 ? (
          <EmptyState
            title="No governed requests yet"
            description="Submitted requests for the selected thread appear here with approval and task linkage."
          />
        ) : (
          <div className="history-list">
            {visibleEntries.map((entry) => (
              <article key={entry.id} className="history-entry">
                <div className="history-entry__topline">
                  <div className="detail-stack">
                    <span className="history-entry__label">
                      {entry.source === "live" ? "Live submission" : "Fixture preview"}
                    </span>
                    <h3 className="list-row__title">
                      {entry.action} / {entry.scope}
                    </h3>
                  </div>
                  <span className="subtle-chip">{formatDate(entry.submittedAt)}</span>
                </div>

                <div className="history-entry__state-row">
                  <StatusBadge status={entry.decision} label={`Decision ${entry.decision.replace(/_/g, " ")}`} />
                  <StatusBadge status={entry.taskStatus} label={`Task ${entry.taskStatus.replace(/_/g, " ")}`} />
                  {entry.approvalStatus ? (
                    <StatusBadge
                      status={entry.approvalStatus}
                      label={`Approval ${entry.approvalStatus.replace(/_/g, " ")}`}
                    />
                  ) : null}
                </div>

                <p>{entry.summary}</p>

                <div className="attribute-list">
                  <span className="attribute-item">Thread: {entry.threadId}</span>
                  <span className="attribute-item">Tool: {entry.toolId}</span>
                  {entry.domainHint ? <span className="attribute-item">Domain: {entry.domainHint}</span> : null}
                  {entry.riskHint ? <span className="attribute-item">Risk: {entry.riskHint}</span> : null}
                </div>

                <div className="history-entry__trace">
                  <span className="meta-pill">
                    Route {entry.trace.routingTraceId} · {entry.trace.routingTraceEventCount} events
                  </span>
                  <span className="meta-pill">
                    Request {entry.trace.requestTraceId} · {entry.trace.requestTraceEventCount} events
                  </span>
                </div>

                <div className="cluster">
                  <Link href={`/tasks?task=${entry.taskId}`} className="button-secondary">
                    Open task
                  </Link>
                  {entry.approvalId ? (
                    <Link href={`/approvals?approval=${entry.approvalId}`} className="button-secondary">
                      Open approval
                    </Link>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
