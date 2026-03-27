from __future__ import annotations

from dataclasses import dataclass
from typing import cast
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
from alicebot_api.task_runs import mark_task_run_failed


@dataclass(frozen=True, slots=True)
class WorkerExecutionOutcome:
    task_run_id: str
    status: str
    stop_reason: str | None
    retry_posture: str
    retry_count: int
    retry_cap: int
    failure_class: str | None


def _worker_outcome_from_task_run(task_run: TaskRunRow) -> WorkerExecutionOutcome:
    return WorkerExecutionOutcome(
        task_run_id=str(task_run["id"]),
        status=str(task_run["status"]),
        stop_reason=None if task_run["stop_reason"] is None else str(task_run["stop_reason"]),
        retry_posture=str(task_run["retry_posture"]),
        retry_count=int(task_run["retry_count"]),
        retry_cap=int(task_run["retry_cap"]),
        failure_class=None if task_run["failure_class"] is None else str(task_run["failure_class"]),
    )


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
    except ProxyExecutionHandlerNotFoundError:
        refreshed = store.get_task_run_optional(task_run["id"])
        if refreshed is not None:
            return _worker_outcome_from_task_run(refreshed)
        failure = mark_task_run_failed(
            store,
            user_id=user_id,
            task_run_id=task_run["id"],
            stop_reason="policy_blocked",
            failure_class="policy",
            source="worker_execute_missing_handler",
        )
        if failure is None:
            return None
        return _worker_outcome_from_task_run(cast(TaskRunRow, failure["task_run"]))
    except (
        ApprovalNotFoundError,
        ProxyExecutionApprovalStateError,
        ProxyExecutionIdempotencyError,
    ):
        failure = mark_task_run_failed(
            store,
            user_id=user_id,
            task_run_id=task_run["id"],
            stop_reason="fatal_error",
            failure_class="transient",
            source="worker_execute_exception",
        )
        if failure is None:
            return None
        return _worker_outcome_from_task_run(cast(TaskRunRow, failure["task_run"]))

    refreshed = store.get_task_run_optional(task_run["id"])
    if refreshed is None:
        return None

    return _worker_outcome_from_task_run(refreshed)
