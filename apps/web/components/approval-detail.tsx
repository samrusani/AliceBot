"use client";

import { useEffect, useState } from "react";

import type { ApprovalExecutionResponse, ApprovalItem, ApiSource, ToolExecutionItem } from "../lib/api";
import { EmptyState } from "./empty-state";
import { SectionCard } from "./section-card";
import { StatusBadge } from "./status-badge";
import { ApprovalActions } from "./approval-actions";
import { ExecutionSummary } from "./execution-summary";
import { WorkflowMemoryWritebackForm } from "./workflow-memory-writeback-form";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatAttributeValue(value: unknown) {
  if (value == null) {
    return "None";
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

type ApprovalDetailProps = {
  initialApproval: ApprovalItem | null;
  detailSource: ApiSource;
  initialExecution: ToolExecutionItem | null;
  executionSource?: ApiSource | null;
  executionUnavailableMessage?: string | null;
  apiBaseUrl?: string;
  userId?: string;
  chrome?: "card" | "embedded";
};

export function ApprovalDetail({
  initialApproval,
  detailSource,
  initialExecution,
  executionSource,
  executionUnavailableMessage,
  apiBaseUrl,
  userId,
  chrome = "card",
}: ApprovalDetailProps) {
  const [approval, setApproval] = useState(initialApproval);
  const [execution, setExecution] = useState(initialExecution);
  const [executionPreview, setExecutionPreview] = useState<ApprovalExecutionResponse | null>(null);

  useEffect(() => {
    setApproval(initialApproval);
    setExecution(initialExecution);
    setExecutionPreview(null);
  }, [initialApproval, initialExecution]);

  if (!approval) {
    return (
      <SectionCard
        eyebrow="Approval detail"
        title="No approval selected"
        description="Choose an approval from the inbox to inspect its governing request and resolution state."
        className={chrome === "embedded" ? "section-card--embedded" : undefined}
      >
        <EmptyState
          title="Approval inspector is idle"
          description="No approval detail is available in the current route state."
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      eyebrow="Approval detail"
      title={approval.tool.name}
      description="Request detail, routing rationale, resolution, and execution review stay composed inside one bounded inspector."
      className={chrome === "embedded" ? "section-card--embedded" : undefined}
    >
      <div className="detail-grid">
        <div className="detail-summary">
          <StatusBadge status={approval.status} />
          <span className="detail-summary__label">
            {approval.request.action} / {approval.request.scope}
          </span>
        </div>

        <dl className="key-value-grid">
          <div>
            <dt>Thread</dt>
            <dd className="mono">{approval.thread_id}</dd>
          </div>
          <div>
            <dt>Task run</dt>
            <dd className="mono">{approval.task_run_id ?? "Unlinked"}</dd>
          </div>
          <div>
            <dt>Task step</dt>
            <dd className="mono">{approval.task_step_id ?? "Unlinked"}</dd>
          </div>
          <div>
            <dt>Routing decision</dt>
            <dd>{approval.routing.decision}</dd>
          </div>
          <div>
            <dt>Detail source</dt>
            <dd>{detailSource === "live" ? "Live approval detail" : "Fixture detail fallback"}</dd>
          </div>
          <div>
            <dt>Routing trace</dt>
            <dd className="mono">
              {approval.routing.trace.trace_id} · {approval.routing.trace.trace_event_count} events
            </dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDate(approval.created_at)}</dd>
          </div>
        </dl>

        <div className="detail-group">
          <h3>Request attributes</h3>
          <div className="attribute-list">
            {Object.entries(approval.request.attributes).map(([key, value]) => (
              <span key={key} className="attribute-item">
                {key}: {formatAttributeValue(value)}
              </span>
            ))}
          </div>
        </div>

        <div className="detail-group">
          <h3>Routing rationale</h3>
          <ul className="reason-list">
            {approval.routing.reasons.map((reason) => (
              <li key={`${reason.code}-${reason.message}`}>{reason.message}</li>
            ))}
          </ul>
        </div>

        <div className="detail-group">
          <h3>Resolution</h3>
          <p className="muted-copy">
            {approval.resolution
              ? `Resolved ${formatDate(approval.resolution.resolved_at)} by ${approval.resolution.resolved_by_user_id}.`
              : "Still awaiting explicit operator resolution."}
          </p>
        </div>

        <div className="detail-group">
          <h3>Approval action bar</h3>
          <ApprovalActions
            approval={approval}
            hasExecution={Boolean(execution || executionPreview)}
            apiBaseUrl={apiBaseUrl}
            userId={userId}
            onResolved={setApproval}
            onExecuted={(payload) => {
              setApproval(payload.approval);
              setExecutionPreview(payload);
            }}
          />
        </div>

        <div className="detail-group">
          <h3>Execution review</h3>
          <ExecutionSummary
            execution={execution}
            preview={executionPreview}
            source={executionSource}
            unavailableMessage={executionPreview ? null : executionUnavailableMessage}
            emptyTitle="Approval is ready but not executed"
            emptyDescription="Once an approved request is executed, the resulting record and output snapshot will appear here."
          />
        </div>

        <div className="detail-group">
          <h3>Post-execution memory write-back</h3>
          <WorkflowMemoryWritebackForm
            execution={execution}
            preview={executionPreview}
            source={executionSource ?? null}
            apiBaseUrl={apiBaseUrl}
            userId={userId}
          />
        </div>
      </div>
    </SectionCard>
  );
}
