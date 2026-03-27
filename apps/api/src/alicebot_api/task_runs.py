from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from alicebot_api.contracts import (
    TASK_RUN_LIST_ORDER,
    TaskRunCancelInput,
    TaskRunCreateInput,
    TaskRunCreateResponse,
    TaskRunDetailResponse,
    TaskRunFailureClass,
    TaskRunListResponse,
    TaskRunListSummary,
    TaskRunMutationResponse,
    TaskRunPauseInput,
    TaskRunRecord,
    TaskRunResumeInput,
    TaskRunRetryPosture,
    TaskRunStatus,
    TaskRunStopReason,
    TaskRunTickInput,
)
from alicebot_api.store import ContinuityStore, JsonObject, TaskRunRow
from alicebot_api.tasks import TaskNotFoundError


RUNNABLE_TASK_RUN_STATUSES = frozenset({"queued", "running"})
PAUSEABLE_TASK_RUN_STATUSES = frozenset({"queued", "running", "waiting_approval", "waiting_user"})
RESUMABLE_TASK_RUN_STATUSES = frozenset({"paused", "waiting_approval", "waiting_user", "failed"})
CANCELLABLE_TASK_RUN_STATUSES = frozenset({"queued", "running", "waiting_approval", "waiting_user", "paused"})
TERMINAL_TASK_RUN_STATUSES = frozenset({"failed", "done", "cancelled"})


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
        "retry_count": row["retry_count"],
        "retry_cap": row["retry_cap"],
        "retry_posture": cast(TaskRunRetryPosture, row["retry_posture"]),
        "failure_class": cast(TaskRunFailureClass | None, row["failure_class"]),
        "stop_reason": cast(TaskRunStopReason | None, row["stop_reason"]),
        "last_transitioned_at": row["last_transitioned_at"].isoformat(),
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


def _append_transition_checkpoint_entry(
    checkpoint: JsonObject,
    *,
    source: str,
    previous_status: TaskRunStatus | None,
    status: TaskRunStatus,
    previous_stop_reason: TaskRunStopReason | None,
    stop_reason: TaskRunStopReason | None,
    failure_class: TaskRunFailureClass | None,
    retry_count: int,
    retry_cap: int,
    retry_posture: TaskRunRetryPosture,
) -> JsonObject:
    normalized = normalize_checkpoint(checkpoint)
    transitions = normalized.get("transitions")
    if isinstance(transitions, list):
        history = [entry for entry in transitions if isinstance(entry, dict)]
    else:
        history = []

    transition_entry = {
        "sequence_no": len(history) + 1,
        "source": source,
        "at": datetime.now(UTC).isoformat(),
        "previous_status": previous_status,
        "status": status,
        "previous_stop_reason": previous_stop_reason,
        "stop_reason": stop_reason,
        "failure_class": failure_class,
        "retry_count": retry_count,
        "retry_cap": retry_cap,
        "retry_posture": retry_posture,
    }
    history.append(transition_entry)
    normalized["transitions"] = history
    normalized["last_transition"] = transition_entry
    return normalized


def _update_task_run(
    store: ContinuityStore,
    *,
    row: TaskRunRow,
    status: TaskRunStatus,
    checkpoint: JsonObject,
    tick_count: int,
    step_count: int,
    retry_count: int,
    retry_cap: int,
    retry_posture: TaskRunRetryPosture,
    failure_class: TaskRunFailureClass | None,
    stop_reason: TaskRunStopReason | None,
    source: str,
) -> TaskRunRow:
    checkpoint_with_transition = _append_transition_checkpoint_entry(
        checkpoint,
        source=source,
        previous_status=cast(TaskRunStatus, row["status"]),
        status=status,
        previous_stop_reason=cast(TaskRunStopReason | None, row["stop_reason"]),
        stop_reason=stop_reason,
        failure_class=failure_class,
        retry_count=retry_count,
        retry_cap=retry_cap,
        retry_posture=retry_posture,
    )
    updated = store.update_task_run_optional(
        task_run_id=cast(UUID, row["id"]),
        status=status,
        checkpoint=checkpoint_with_transition,
        tick_count=tick_count,
        step_count=step_count,
        retry_count=retry_count,
        retry_cap=retry_cap,
        retry_posture=retry_posture,
        failure_class=failure_class,
        stop_reason=stop_reason,
    )
    if updated is None:
        raise TaskRunNotFoundError(f"task run {row['id']} was not found")
    return updated


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

    retry_cap = request.retry_cap if request.retry_cap is not None else max(1, request.max_ticks)
    if retry_cap <= 0:
        raise TaskRunValidationError("retry_cap must be greater than 0")

    checkpoint = _append_transition_checkpoint_entry(
        request.checkpoint,
        source="create",
        previous_status=None,
        status="queued",
        previous_stop_reason=None,
        stop_reason=None,
        failure_class=None,
        retry_count=0,
        retry_cap=retry_cap,
        retry_posture="none",
    )
    row = store.create_task_run(
        task_id=request.task_id,
        status="queued",
        checkpoint=checkpoint,
        tick_count=0,
        step_count=0,
        max_ticks=request.max_ticks,
        retry_count=0,
        retry_cap=retry_cap,
        retry_posture="none",
        failure_class=None,
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
    retry_count = int(row["retry_count"])
    retry_cap = int(row["retry_cap"])
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
                retry_count=retry_count,
                retry_cap=retry_cap,
                retry_posture="awaiting_approval",
                failure_class=None,
                stop_reason="waiting_approval",
                source="tick_waiting_approval",
            )
            return {
                "task_run": serialize_task_run_row(updated),
                "previous_status": previous_status,
            }

    if cursor >= target_steps:
        updated = _update_task_run(
            store,
            row=row,
            status="done",
            checkpoint=checkpoint,
            tick_count=tick_count,
            step_count=step_count,
            retry_count=retry_count,
            retry_cap=retry_cap,
            retry_posture="terminal",
            failure_class=None,
            stop_reason="done",
            source="tick_done_existing_cursor",
        )
    elif tick_count >= max_ticks:
        updated = _update_task_run(
            store,
            row=row,
            status="failed",
            checkpoint=checkpoint,
            tick_count=tick_count,
            step_count=step_count,
            retry_count=retry_count,
            retry_cap=retry_cap,
            retry_posture="terminal",
            failure_class="budget",
            stop_reason="budget_exhausted",
            source="tick_budget_exhausted",
        )
    elif wait_for_signal:
        checkpoint["wait_for_signal"] = True
        updated = _update_task_run(
            store,
            row=row,
            status="waiting_user",
            checkpoint=checkpoint,
            tick_count=tick_count + 1,
            step_count=step_count,
            retry_count=retry_count,
            retry_cap=retry_cap,
            retry_posture="awaiting_user",
            failure_class=None,
            stop_reason="waiting_user",
            source="tick_waiting_user",
        )
    else:
        checkpoint["cursor"] = cursor + 1
        next_tick_count = tick_count + 1
        next_step_count = step_count + 1
        if checkpoint["cursor"] >= target_steps:
            status: TaskRunStatus = "done"
            stop_reason: TaskRunStopReason | None = "done"
            retry_posture: TaskRunRetryPosture = "terminal"
        else:
            status = "running"
            stop_reason = None
            retry_posture = "none"
        updated = _update_task_run(
            store,
            row=row,
            status=status,
            checkpoint=checkpoint,
            tick_count=next_tick_count,
            step_count=next_step_count,
            retry_count=retry_count,
            retry_cap=retry_cap,
            retry_posture=retry_posture,
            failure_class=None,
            stop_reason=stop_reason,
            source="tick_progress",
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
        retry_count=int(row["retry_count"]),
        retry_cap=int(row["retry_cap"]),
        retry_posture="paused",
        failure_class=None,
        stop_reason="paused",
        source="pause",
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
    checkpoint["resumed_by_user"] = True

    retry_count = int(row["retry_count"])
    retry_cap = int(row["retry_cap"])
    if previous_status == "failed":
        failure_class = cast(TaskRunFailureClass | None, row["failure_class"])
        if failure_class != "transient":
            raise _transition_conflict(
                task_run_id=request.task_run_id,
                status=previous_status,
                action="resumed because failure class is terminal",
            )
        if retry_count >= retry_cap:
            raise _transition_conflict(
                task_run_id=request.task_run_id,
                status=previous_status,
                action="resumed because retry cap is exhausted",
            )
        next_retry_count = retry_count + 1
        next_status: TaskRunStatus = "queued"
    else:
        next_retry_count = retry_count
        next_status = "queued" if previous_status == "waiting_approval" else "running"

    updated = _update_task_run(
        store,
        row=row,
        status=next_status,
        checkpoint=checkpoint,
        tick_count=int(row["tick_count"]),
        step_count=int(row["step_count"]),
        retry_count=next_retry_count,
        retry_cap=retry_cap,
        retry_posture="none",
        failure_class=None,
        stop_reason=None,
        source="resume",
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
        retry_count=int(row["retry_count"]),
        retry_cap=int(row["retry_cap"]),
        retry_posture="terminal",
        failure_class=None,
        stop_reason="cancelled",
        source="cancel",
    )
    return {
        "task_run": serialize_task_run_row(updated),
        "previous_status": previous_status,
    }


def mark_task_run_failed(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_run_id: UUID,
    stop_reason: TaskRunStopReason,
    failure_class: TaskRunFailureClass,
    source: str,
) -> TaskRunMutationResponse | None:
    del user_id

    row = store.get_task_run_optional(task_run_id)
    if row is None:
        return None

    previous_status = cast(TaskRunStatus, row["status"])
    if previous_status in {"done", "cancelled"}:
        return None

    retry_count = int(row["retry_count"])
    retry_cap = int(row["retry_cap"])
    if failure_class == "transient":
        if retry_count < retry_cap:
            retry_posture: TaskRunRetryPosture = "retryable"
            next_stop_reason = stop_reason
        else:
            retry_posture = "exhausted"
            next_stop_reason = "retry_exhausted"
    else:
        retry_posture = "terminal"
        next_stop_reason = stop_reason

    updated = _update_task_run(
        store,
        row=row,
        status="failed",
        checkpoint=cast(JsonObject, row["checkpoint"]),
        tick_count=int(row["tick_count"]),
        step_count=int(row["step_count"]),
        retry_count=retry_count,
        retry_cap=retry_cap,
        retry_posture=retry_posture,
        failure_class=failure_class,
        stop_reason=next_stop_reason,
        source=source,
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
