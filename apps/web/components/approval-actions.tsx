"use client";

import { useEffect, useRef, useState } from "react";

import { useRouter } from "next/navigation";

import type { ApprovalExecutionResponse, ApprovalItem } from "../lib/api";
import { executeApproval, resolveApproval } from "../lib/api";
import { StatusBadge } from "./status-badge";

type ApprovalActionsProps = {
  approval: ApprovalItem;
  hasExecution: boolean;
  apiBaseUrl?: string;
  userId?: string;
  onResolved: (approval: ApprovalItem) => void;
  onExecuted: (payload: ApprovalExecutionResponse) => void;
};

type FeedbackState = {
  tone: "info" | "success" | "danger";
  kind: "availability" | "resolution" | "execution";
  message: string;
  badgeStatus?: string;
  badgeLabel?: string;
};

function actionAvailabilityMessage(
  liveModeReady: boolean,
  approvalStatus: ApprovalItem["status"],
  hasExecution: boolean,
) {
  if (!liveModeReady) {
    if (hasExecution) {
      return "Fixture mode is read-only. Review the recorded execution detail below.";
    }

    return approvalStatus === "pending"
      ? "Approve and reject controls are disabled in fixture mode."
      : "Execution controls are unavailable until live API configuration is present.";
  }

  if (approvalStatus === "pending") {
    return "Choose approve or reject to resolve the approval through the shipped backend seam.";
  }

  if (approvalStatus === "approved" && !hasExecution) {
    return "This approval is resolved and eligible for execution. Run it only when the reviewed request is ready to proceed.";
  }

  if (approvalStatus === "approved" && hasExecution) {
    return "A linked execution record already exists. The action bar is now read-only.";
  }

  return "This approval is not in an executable state. The action bar is read-only.";
}

export function ApprovalActions({
  approval,
  hasExecution,
  apiBaseUrl,
  userId,
  onResolved,
  onExecuted,
}: ApprovalActionsProps) {
  const router = useRouter();
  const lastResetContextRef = useRef<{ approvalId: string; liveModeReady: boolean } | null>(null);
  const [feedback, setFeedback] = useState<FeedbackState>({
    tone: "info",
    kind: "availability",
    message: actionAvailabilityMessage(Boolean(apiBaseUrl && userId), approval.status, hasExecution),
  });
  const [pendingAction, setPendingAction] = useState<"approve" | "reject" | "execute" | null>(null);

  const liveModeReady = Boolean(apiBaseUrl && userId);
  const actionBusy = pendingAction !== null;
  const canResolve = liveModeReady && approval.status === "pending" && !actionBusy;
  const canExecute = liveModeReady && approval.status === "approved" && !hasExecution && !actionBusy;

  useEffect(() => {
    const lastResetContext = lastResetContextRef.current;
    const shouldReset =
      lastResetContext == null ||
      lastResetContext.approvalId !== approval.id ||
      lastResetContext.liveModeReady !== liveModeReady;

    if (shouldReset) {
      setFeedback({
        tone: "info",
        kind: "availability",
        message: actionAvailabilityMessage(liveModeReady, approval.status, hasExecution),
      });
      setPendingAction(null);
      lastResetContextRef.current = {
        approvalId: approval.id,
        liveModeReady,
      };
    }
  }, [approval.id, approval.status, hasExecution, liveModeReady]);

  async function handleResolve(action: "approve" | "reject") {
    if (!apiBaseUrl || !userId) {
      return;
    }

    setPendingAction(action);
    setFeedback({
      tone: "info",
      kind: "resolution",
      message: action === "approve" ? "Submitting approval resolution..." : "Submitting rejection resolution...",
    });

    try {
      const payload = await resolveApproval(apiBaseUrl, approval.id, action, userId);
      onResolved(payload.approval);
      setFeedback({
        tone: "success",
        kind: "resolution",
        message:
          action === "approve"
            ? "Approval resolved as approved. The inbox and downstream task view have been refreshed."
            : "Approval resolved as rejected. The inbox and downstream task view have been refreshed.",
      });
      router.refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Resolution failed";
      setFeedback({
        tone: "danger",
        kind: "resolution",
        message,
        badgeStatus: "rejected",
        badgeLabel: "Resolution failed",
      });
    } finally {
      setPendingAction(null);
    }
  }

  async function handleExecute() {
    if (!apiBaseUrl || !userId) {
      return;
    }

    setPendingAction("execute");
    setFeedback({
      tone: "info",
      kind: "execution",
      message: "Submitting approved execution...",
    });

    try {
      const payload = await executeApproval(apiBaseUrl, approval.id, userId);
      onExecuted(payload);
      setFeedback({
        tone: payload.result.status === "blocked" ? "danger" : "success",
        kind: "execution",
        message:
          payload.result.status === "blocked"
            ? "Execution was recorded as blocked. Review the execution summary for the blocking reason."
            : "Execution completed and the review panels have been refreshed.",
        badgeStatus: payload.result.status === "blocked" ? "blocked" : "completed",
        badgeLabel: payload.result.status === "blocked" ? "Execution blocked" : "Execution saved",
      });
      router.refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Execution failed";
      setFeedback({
        tone: "danger",
        kind: "execution",
        message,
        badgeStatus: "failed",
        badgeLabel: "Execution failed",
      });
    } finally {
      setPendingAction(null);
    }
  }

  const badgeStatus = pendingAction
    ? pendingAction === "execute"
      ? "executing"
      : "submitting"
    : feedback.badgeStatus ??
      (feedback.tone === "danger"
        ? feedback.kind === "execution"
          ? "failed"
          : "rejected"
        : feedback.tone);

  const badgeLabel = pendingAction
    ? pendingAction === "approve"
      ? "Submitting approve"
      : pendingAction === "reject"
        ? "Submitting reject"
        : "Executing"
    : feedback.badgeLabel ??
      (feedback.tone === "success"
        ? feedback.kind === "execution"
          ? "Execution saved"
          : "Resolution saved"
        : feedback.tone === "danger"
          ? feedback.kind === "execution"
            ? "Execution failed"
            : "Resolution failed"
          : liveModeReady
            ? "Ready"
            : "Fixture mode");

  return (
    <div className="approval-action-bar">
      <div className="approval-action-bar__summary">
        <StatusBadge status={badgeStatus} label={badgeLabel} />
        <p className="muted-copy">{feedback.message}</p>
      </div>

      <div className="approval-action-bar__buttons">
        {approval.status === "pending" ? (
          <>
            <button
              type="button"
              className="button"
              onClick={() => handleResolve("approve")}
              disabled={!canResolve}
            >
              {pendingAction === "approve" ? "Approving..." : "Approve"}
            </button>
            <button
              type="button"
              className="button-secondary button-secondary--danger"
              onClick={() => handleResolve("reject")}
              disabled={!canResolve}
            >
              {pendingAction === "reject" ? "Rejecting..." : "Reject"}
            </button>
          </>
        ) : null}

        {approval.status === "approved" ? (
          <button type="button" className="button" onClick={handleExecute} disabled={!canExecute}>
            {pendingAction === "execute" ? "Executing..." : hasExecution ? "Executed" : "Execute approved request"}
          </button>
        ) : null}
      </div>
    </div>
  );
}
