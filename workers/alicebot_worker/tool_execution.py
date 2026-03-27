from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from alicebot_api.approvals import ApprovalNotFoundError
from alicebot_api.contracts import ProxyExecutionRequestInput
from alicebot_api.proxy_execution import (
    ProxyExecutionApprovalStateError,
    ProxyExecutionHandlerNotFoundError,
    ProxyExecutionIdempotencyError,
    execute_approved_proxy_request,
)
from alicebot_api.store import ContinuityStore, TaskRunRow


@dataclass(frozen=True, slots=True)
class WorkerExecutionOutcome:
    task_run_id: str
    status: str
    stop_reason: str | None


def execute_task_run_if_ready(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_run: TaskRunRow,
) -> WorkerExecutionOutcome | None:
    task = store.get_task_optional(task_run["task_id"])
    if task is None:
        return None

    latest_approval_id = task.get("latest_approval_id")
    if task["status"] != "approved" or latest_approval_id is None or task.get("latest_execution_id") is not None:
        return None

    approval = store.get_approval_optional(latest_approval_id)
    if approval is None or approval["status"] != "approved":
        return None

    try:
        execute_approved_proxy_request(
            store,
            user_id=user_id,
            request=ProxyExecutionRequestInput(
                approval_id=latest_approval_id,
                task_run_id=task_run["id"],
            ),
        )
    except (
        ApprovalNotFoundError,
        ProxyExecutionApprovalStateError,
        ProxyExecutionHandlerNotFoundError,
        ProxyExecutionIdempotencyError,
    ):
        return None

    refreshed = store.get_task_run_optional(task_run["id"])
    if refreshed is None:
        return None

    return WorkerExecutionOutcome(
        task_run_id=str(refreshed["id"]),
        status=str(refreshed["status"]),
        stop_reason=None if refreshed["stop_reason"] is None else str(refreshed["stop_reason"]),
    )
