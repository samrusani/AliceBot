"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import type { ApprovalItem } from "../lib/api";
import { resolveApproval } from "../lib/api";
import { StatusBadge } from "./status-badge";

type ApprovalActionsProps = {
  approval: ApprovalItem;
  apiBaseUrl?: string;
  userId?: string;
  onResolved: (approval: ApprovalItem) => void;
};

type FeedbackState = {
  tone: "info" | "success" | "danger";
  message: string;
};

function actionAvailabilityMessage(liveModeReady: boolean, approvalStatus: ApprovalItem["status"]) {
  if (!liveModeReady) {
    return "Approve and reject controls are disabled in fixture mode.";
  }

  if (approvalStatus !== "pending") {
    return "This approval has already been resolved. The action bar is now read-only.";
  }

  return "Choose approve or reject to resolve the approval through the shipped backend seam.";
}

export function ApprovalActions({
  approval,
  apiBaseUrl,
  userId,
  onResolved,
}: ApprovalActionsProps) {
  const router = useRouter();
  const [feedback, setFeedback] = useState<FeedbackState>({
    tone: "info",
    message: actionAvailabilityMessage(Boolean(apiBaseUrl && userId), approval.status),
  });
  const [pendingAction, setPendingAction] = useState<"approve" | "reject" | null>(null);

  const liveModeReady = Boolean(apiBaseUrl && userId);
  const actionLocked = !liveModeReady || approval.status !== "pending" || pendingAction !== null;

  useEffect(() => {
    setFeedback({
      tone: "info",
      message: actionAvailabilityMessage(liveModeReady, approval.status),
    });
    setPendingAction(null);
  }, [approval.id, approval.status, liveModeReady]);

  async function handleResolve(action: "approve" | "reject") {
    if (!apiBaseUrl || !userId) {
      return;
    }

    setPendingAction(action);
    setFeedback({
      tone: "info",
      message: action === "approve" ? "Submitting approval resolution..." : "Submitting rejection resolution...",
    });

    try {
      const payload = await resolveApproval(apiBaseUrl, approval.id, action, userId);
      onResolved(payload.approval);
      setFeedback({
        tone: "success",
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
        message,
      });
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className="approval-action-bar">
      <div className="approval-action-bar__summary">
        <StatusBadge
          status={
            pendingAction ? "submitting" : feedback.tone === "danger" ? "rejected" : feedback.tone
          }
          label={
            pendingAction
              ? pendingAction === "approve"
                ? "Submitting approve"
                : "Submitting reject"
              : feedback.tone === "success"
                ? "Resolution saved"
                : feedback.tone === "danger"
                  ? "Resolution failed"
                  : liveModeReady
                    ? "Ready"
                    : "Fixture mode"
          }
        />
        <p className="muted-copy">{feedback.message}</p>
      </div>

      <div className="approval-action-bar__buttons">
        <button
          type="button"
          className="button"
          onClick={() => handleResolve("approve")}
          disabled={actionLocked}
        >
          {pendingAction === "approve" ? "Approving..." : "Approve"}
        </button>
        <button
          type="button"
          className="button-secondary button-secondary--danger"
          onClick={() => handleResolve("reject")}
          disabled={actionLocked}
        >
          {pendingAction === "reject" ? "Rejecting..." : "Reject"}
        </button>
      </div>
    </div>
  );
}
