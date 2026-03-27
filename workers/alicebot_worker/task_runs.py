from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from alicebot_api.contracts import TaskRunTickInput
from alicebot_api.store import ContinuityStore
from alicebot_api.task_runs import (
    TaskRunNotFoundError,
    TaskRunTransitionError,
    tick_task_run_record,
)
from alicebot_worker.tool_execution import execute_task_run_if_ready


@dataclass(frozen=True, slots=True)
class WorkerTickOutcome:
    task_run_id: str
    previous_status: str
    status: str
    stop_reason: str | None


def acquire_and_tick_one_task_run(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> WorkerTickOutcome | None:
    row = store.acquire_next_task_run_optional()
    if row is None:
        return None

    task_run_id = row["id"]
    execution_outcome = execute_task_run_if_ready(
        store,
        user_id=user_id,
        task_run=row,
    )
    if execution_outcome is not None:
        return WorkerTickOutcome(
            task_run_id=execution_outcome.task_run_id,
            previous_status=str(row["status"]),
            status=execution_outcome.status,
            stop_reason=execution_outcome.stop_reason,
        )

    try:
        payload = tick_task_run_record(
            store,
            user_id=user_id,
            request=TaskRunTickInput(task_run_id=task_run_id),
        )
    except (TaskRunNotFoundError, TaskRunTransitionError):
        return None

    task_run = payload["task_run"]
    return WorkerTickOutcome(
        task_run_id=task_run["id"],
        previous_status=payload["previous_status"],
        status=task_run["status"],
        stop_reason=task_run["stop_reason"],
    )
