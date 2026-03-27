from __future__ import annotations

from typing import cast
from uuid import UUID

from alicebot_api.contracts import (
    TASK_RUN_LIST_ORDER,
    TaskRunCancelInput,
    TaskRunCreateInput,
    TaskRunCreateResponse,
    TaskRunDetailResponse,
    TaskRunListResponse,
    TaskRunListSummary,
    TaskRunMutationResponse,
    TaskRunPauseInput,
    TaskRunRecord,
    TaskRunResumeInput,
    TaskRunStatus,
    TaskRunTickInput,
)
from alicebot_api.store import ContinuityStore, JsonObject, TaskRunRow
from alicebot_api.tasks import TaskNotFoundError


RUNNABLE_TASK_RUN_STATUSES = frozenset({"queued", "running"})
PAUSEABLE_TASK_RUN_STATUSES = frozenset({"queued", "running", "waiting", "waiting_approval"})
RESUMABLE_TASK_RUN_STATUSES = frozenset({"paused", "waiting", "waiting_approval"})
CANCELLABLE_TASK_RUN_STATUSES = frozenset({"queued", "running", "waiting", "waiting_approval", "paused"})


class TaskRunValidationError(ValueError):
    """Raised when a task-run request fails explicit validation."""


class TaskRunNotFoundError(LookupError):
    """Raised when a task-run record is not visible inside the current user scope."""


class TaskRunTransitionError(RuntimeError):
    """Raised when a task-run lifecycle transition is invalid."""


def serialize_task_run_row(row: TaskRunRow) -> TaskRunRecord:
    return {
        "id": str(row["id"]),
        "task_id": str(row["task_id"]),
        "status": cast(TaskRunStatus, row["status"]),
        "checkpoint": cast(JsonObject, row["checkpoint"]),
        "tick_count": row["tick_count"],
        "step_count": row["step_count"],
        "max_ticks": row["max_ticks"],
        "stop_reason": cast(str | None, row["stop_reason"]),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _coerce_non_negative_int(value: object, *, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TaskRunValidationError(f"checkpoint.{key} must be an integer")
    if value < 0:
        raise TaskRunValidationError(f"checkpoint.{key} must be greater than or equal to 0")
    return value


def _coerce_positive_int(value: object, *, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TaskRunValidationError(f"checkpoint.{key} must be an integer")
    if value <= 0:
        raise TaskRunValidationError(f"checkpoint.{key} must be greater than 0")
    return value


def normalize_checkpoint(checkpoint: JsonObject) -> JsonObject:
    if not isinstance(checkpoint, dict):
        raise TaskRunValidationError("checkpoint must be a JSON object")

    cursor = _coerce_non_negative_int(checkpoint.get("cursor", 0), key="cursor")
    target_steps = _coerce_positive_int(checkpoint.get("target_steps", 1), key="target_steps")
    wait_for_signal = checkpoint.get("wait_for_signal", False)
    if not isinstance(wait_for_signal, bool):
        raise TaskRunValidationError("checkpoint.wait_for_signal must be a boolean")
    if cursor > target_steps:
        raise TaskRunValidationError("checkpoint.cursor must be less than or equal to checkpoint.target_steps")

    normalized = dict(checkpoint)
    normalized["cursor"] = cursor
    normalized["target_steps"] = target_steps
    normalized["wait_for_signal"] = wait_for_signal
    return normalized


def _require_task_exists(store: ContinuityStore, *, task_id: UUID) -> None:
    if store.get_task_optional(task_id) is None:
        raise TaskNotFoundError(f"task {task_id} was not found")


def _require_task_run(store: ContinuityStore, *, task_run_id: UUID) -> TaskRunRow:
    row = store.get_task_run_optional(task_run_id)
    if row is None:
        raise TaskRunNotFoundError(f"task run {task_run_id} was not found")
    return row


def _transition_conflict(*, task_run_id: UUID, status: str, action: str) -> TaskRunTransitionError:
    return TaskRunTransitionError(f"task run {task_run_id} is {status} and cannot be {action}")


def create_task_run_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskRunCreateInput,
) -> TaskRunCreateResponse:
    del user_id

    _require_task_exists(store, task_id=request.task_id)
    if request.max_ticks <= 0:
        raise TaskRunValidationError("max_ticks must be greater than 0")

    checkpoint = normalize_checkpoint(request.checkpoint)
    row = store.create_task_run(
        task_id=request.task_id,
        status="queued",
        checkpoint=checkpoint,
        tick_count=0,
        step_count=0,
        max_ticks=request.max_ticks,
        stop_reason=None,
    )
    return {"task_run": serialize_task_run_row(row)}


def list_task_run_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_id: UUID,
) -> TaskRunListResponse:
    del user_id

    _require_task_exists(store, task_id=task_id)
    items = [serialize_task_run_row(row) for row in store.list_task_runs_for_task(task_id)]
    summary: TaskRunListSummary = {
        "task_id": str(task_id),
        "total_count": len(items),
        "order": list(TASK_RUN_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_task_run_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_run_id: UUID,
) -> TaskRunDetailResponse:
    del user_id

    row = _require_task_run(store, task_run_id=task_run_id)
    return {"task_run": serialize_task_run_row(row)}


def _update_task_run(
    store: ContinuityStore,
    *,
    row: TaskRunRow,
    status: TaskRunStatus,
    checkpoint: JsonObject,
    tick_count: int,
    step_count: int,
    stop_reason: str | None,
) -> TaskRunRow:
    updated = store.update_task_run_optional(
        task_run_id=cast(UUID, row["id"]),
        status=status,
        checkpoint=checkpoint,
        tick_count=tick_count,
        step_count=step_count,
        stop_reason=stop_reason,
    )
    if updated is None:
        raise TaskRunNotFoundError(f"task run {row['id']} was not found")
    return updated


def tick_task_run_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskRunTickInput,
) -> TaskRunMutationResponse:
    del user_id

    row = _require_task_run(store, task_run_id=request.task_run_id)
    previous_status = cast(TaskRunStatus, row["status"])
    if previous_status not in RUNNABLE_TASK_RUN_STATUSES:
        raise _transition_conflict(task_run_id=request.task_run_id, status=previous_status, action="ticked")

    checkpoint = normalize_checkpoint(cast(JsonObject, row["checkpoint"]))
    cursor = _coerce_non_negative_int(checkpoint.get("cursor", 0), key="cursor")
    target_steps = _coerce_positive_int(checkpoint.get("target_steps", 1), key="target_steps")
    wait_for_signal = bool(checkpoint.get("wait_for_signal", False))
    tick_count = int(row["tick_count"])
    step_count = int(row["step_count"])
    max_ticks = int(row["max_ticks"])
    task = _require_task_exists_and_load(store, task_id=cast(UUID, row["task_id"]))

    if task["status"] == "pending_approval" and task["latest_approval_id"] is not None:
        approval_id = cast(UUID, task["latest_approval_id"])
        approval = store.get_approval_optional(approval_id)
        if approval is not None and approval["status"] == "pending":
            checkpoint["wait_for_signal"] = True
            checkpoint["waiting_approval_id"] = str(approval_id)
            store.update_approval_task_run_optional(
                approval_id=approval_id,
                task_run_id=cast(UUID, row["id"]),
            )
            updated = _update_task_run(
                store,
                row=row,
                status="waiting_approval",
                checkpoint=checkpoint,
                tick_count=tick_count + 1,
                step_count=step_count,
                stop_reason="waiting_approval",
            )
            return {
                "task_run": serialize_task_run_row(updated),
                "previous_status": previous_status,
            }

    if cursor >= target_steps:
        updated = _update_task_run(
            store,
            row=row,
            status="completed",
            checkpoint=checkpoint,
            tick_count=tick_count,
            step_count=step_count,
            stop_reason="completed",
        )
    elif tick_count >= max_ticks:
        updated = _update_task_run(
            store,
            row=row,
            status="paused",
            checkpoint=checkpoint,
            tick_count=tick_count,
            step_count=step_count,
            stop_reason="budget_exhausted",
        )
    elif wait_for_signal:
        checkpoint["wait_for_signal"] = True
        updated = _update_task_run(
            store,
            row=row,
            status="waiting",
            checkpoint=checkpoint,
            tick_count=tick_count + 1,
            step_count=step_count,
            stop_reason="wait_state",
        )
    else:
        checkpoint["cursor"] = cursor + 1
        next_tick_count = tick_count + 1
        next_step_count = step_count + 1
        if checkpoint["cursor"] >= target_steps:
            status: TaskRunStatus = "completed"
            stop_reason = "completed"
        else:
            status = "running"
            stop_reason = None
        updated = _update_task_run(
            store,
            row=row,
            status=status,
            checkpoint=checkpoint,
            tick_count=next_tick_count,
            step_count=next_step_count,
            stop_reason=stop_reason,
        )

    return {
        "task_run": serialize_task_run_row(updated),
        "previous_status": previous_status,
    }


def pause_task_run_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskRunPauseInput,
) -> TaskRunMutationResponse:
    del user_id

    row = _require_task_run(store, task_run_id=request.task_run_id)
    previous_status = cast(TaskRunStatus, row["status"])
    if previous_status not in PAUSEABLE_TASK_RUN_STATUSES:
        raise _transition_conflict(task_run_id=request.task_run_id, status=previous_status, action="paused")

    checkpoint = normalize_checkpoint(cast(JsonObject, row["checkpoint"]))
    updated = _update_task_run(
        store,
        row=row,
        status="paused",
        checkpoint=checkpoint,
        tick_count=int(row["tick_count"]),
        step_count=int(row["step_count"]),
        stop_reason="paused",
    )
    return {
        "task_run": serialize_task_run_row(updated),
        "previous_status": previous_status,
    }


def resume_task_run_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskRunResumeInput,
) -> TaskRunMutationResponse:
    del user_id

    row = _require_task_run(store, task_run_id=request.task_run_id)
    previous_status = cast(TaskRunStatus, row["status"])
    if previous_status not in RESUMABLE_TASK_RUN_STATUSES:
        raise _transition_conflict(task_run_id=request.task_run_id, status=previous_status, action="resumed")

    checkpoint = normalize_checkpoint(cast(JsonObject, row["checkpoint"]))
    if previous_status == "waiting_approval":
        waiting_approval_id = checkpoint.get("waiting_approval_id")
        if isinstance(waiting_approval_id, str) and waiting_approval_id:
            try:
                waiting_approval_uuid = UUID(waiting_approval_id)
            except ValueError:
                waiting_approval_uuid = None
            approval = None if waiting_approval_uuid is None else store.get_approval_optional(waiting_approval_uuid)
            if approval is not None and approval["status"] == "pending":
                raise _transition_conflict(
                    task_run_id=request.task_run_id,
                    status=previous_status,
                    action="resumed while approval is still pending",
                )
    checkpoint["wait_for_signal"] = False
    checkpoint["waiting_approval_id"] = None
    updated = _update_task_run(
        store,
        row=row,
        status="running" if previous_status != "waiting_approval" else "queued",
        checkpoint=checkpoint,
        tick_count=int(row["tick_count"]),
        step_count=int(row["step_count"]),
        stop_reason=None,
    )
    return {
        "task_run": serialize_task_run_row(updated),
        "previous_status": previous_status,
    }


def cancel_task_run_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskRunCancelInput,
) -> TaskRunMutationResponse:
    del user_id

    row = _require_task_run(store, task_run_id=request.task_run_id)
    previous_status = cast(TaskRunStatus, row["status"])
    if previous_status not in CANCELLABLE_TASK_RUN_STATUSES:
        raise _transition_conflict(task_run_id=request.task_run_id, status=previous_status, action="cancelled")

    checkpoint = normalize_checkpoint(cast(JsonObject, row["checkpoint"]))
    updated = _update_task_run(
        store,
        row=row,
        status="cancelled",
        checkpoint=checkpoint,
        tick_count=int(row["tick_count"]),
        step_count=int(row["step_count"]),
        stop_reason="cancelled",
    )
    return {
        "task_run": serialize_task_run_row(updated),
        "previous_status": previous_status,
    }


def _require_task_exists_and_load(store: ContinuityStore, *, task_id: UUID) -> dict[str, object]:
    task = store.get_task_optional(task_id)
    if task is None:
        raise TaskNotFoundError(f"task {task_id} was not found")
    return cast(dict[str, object], task)
