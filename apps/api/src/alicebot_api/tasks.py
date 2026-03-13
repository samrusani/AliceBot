from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from uuid import UUID

import psycopg

from alicebot_api.contracts import (
    TASK_LIST_ORDER,
    TASK_STEP_CONTINUATION_VERSION_V0,
    TASK_STEP_LIST_ORDER,
    TASK_STEP_TRANSITION_VERSION_V0,
    TRACE_KIND_TASK_STEP_CONTINUATION,
    TRACE_KIND_TASK_STEP_TRANSITION,
    TaskCreateInput,
    TaskCreateResponse,
    TaskDetailResponse,
    TaskLifecycleSource,
    TaskLifecycleStateTracePayload,
    TaskLifecycleSummaryTracePayload,
    TaskListResponse,
    TaskListSummary,
    TaskRecord,
    TaskStatus,
    TaskStepCreateInput,
    TaskStepCreateResponse,
    TaskStepDetailResponse,
    TaskStepContinuationLineageTracePayload,
    TaskStepContinuationRequestTracePayload,
    TaskStepContinuationSummaryTracePayload,
    TaskStepLifecycleStateTracePayload,
    TaskStepLifecycleSummaryTracePayload,
    TaskStepLineageRecord,
    TaskStepListSummary,
    TaskStepListResponse,
    TaskStepMutationTraceSummary,
    TaskStepNextCreateInput,
    TaskStepNextCreateResponse,
    TaskStepOutcomeSnapshot,
    TaskStepRecord,
    TaskStepStatus,
    TaskStepTransitionInput,
    TaskStepTransitionRequestTracePayload,
    TaskStepTransitionResponse,
    TaskStepTransitionStateTracePayload,
    TaskStepTransitionSummaryTracePayload,
)
from alicebot_api.store import (
    ContinuityStore,
    ContinuityStoreInvariantError,
    TaskRow,
    TaskStepRow,
    ToolExecutionRow,
)

TASK_LIFECYCLE_STATE_EVENT_KIND = "task.lifecycle.state"
TASK_LIFECYCLE_SUMMARY_EVENT_KIND = "task.lifecycle.summary"
TASK_STEP_LIFECYCLE_STATE_EVENT_KIND = "task.step.lifecycle.state"
TASK_STEP_LIFECYCLE_SUMMARY_EVENT_KIND = "task.step.lifecycle.summary"
TASK_STEP_CONTINUATION_REQUEST_EVENT_KIND = "task.step.continuation.request"
TASK_STEP_CONTINUATION_LINEAGE_EVENT_KIND = "task.step.continuation.lineage"
TASK_STEP_CONTINUATION_SUMMARY_EVENT_KIND = "task.step.continuation.summary"
TASK_STEP_TRANSITION_REQUEST_EVENT_KIND = "task.step.transition.request"
TASK_STEP_TRANSITION_STATE_EVENT_KIND = "task.step.transition.state"
TASK_STEP_TRANSITION_SUMMARY_EVENT_KIND = "task.step.transition.summary"
DEFAULT_TASK_STEP_SEQUENCE_NO = 1
DEFAULT_TASK_STEP_KIND = "governed_request"
TASK_STEP_APPENDABLE_STATUSES = frozenset({"executed", "blocked", "denied"})
TASK_STEP_INITIAL_STATUSES = frozenset({"created", "approved", "denied"})
TASK_STEP_STATUS_GRAPH: dict[TaskStepStatus, tuple[TaskStepStatus, ...]] = {
    "created": ("approved", "denied"),
    "approved": ("executed", "blocked"),
    "executed": (),
    "blocked": (),
    "denied": (),
}


class TaskNotFoundError(LookupError):
    """Raised when a task record is not visible inside the current user scope."""


class TaskStepNotFoundError(LookupError):
    """Raised when a task-step record is not visible inside the current user scope."""


class TaskStepSequenceError(RuntimeError):
    """Raised when a task-step append request violates deterministic sequencing rules."""


class TaskStepTransitionError(RuntimeError):
    """Raised when a task-step transition request violates the explicit status graph."""


class TaskStepLifecycleBoundaryError(RuntimeError):
    """Raised when first-step-only lifecycle helpers are routed a later-step context."""


class TaskStepApprovalLinkageError(RuntimeError):
    """Raised when approval resolution cannot validate its linked task step."""


class TaskStepExecutionLinkageError(RuntimeError):
    """Raised when execution synchronization cannot validate its linked task step."""


@dataclass(frozen=True, slots=True)
class TaskTransitionResult:
    task: TaskRecord
    previous_status: TaskStatus | None


@dataclass(frozen=True, slots=True)
class TaskStepTransitionResult:
    task_step: TaskStepRecord
    previous_status: TaskStepStatus | None


def _append_trace_events(
    store: ContinuityStore,
    *,
    trace_id: UUID,
    trace_events: list[tuple[str, dict[str, object]]],
) -> None:
    for sequence_no, (kind, payload) in enumerate(trace_events, start=1):
        store.append_trace_event(
            trace_id=trace_id,
            sequence_no=sequence_no,
            kind=kind,
            payload=payload,
        )


def _trace_summary(
    trace_id: UUID,
    trace_events: list[tuple[str, dict[str, object]]],
) -> TaskStepMutationTraceSummary:
    return {
        "trace_id": str(trace_id),
        "trace_event_count": len(trace_events),
    }


def validate_linked_task_step_for_approval(
    store: ContinuityStore,
    *,
    approval_id: UUID,
    task_step_id: UUID | None,
) -> tuple[TaskRow, TaskStepRow]:
    if task_step_id is None:
        raise TaskStepApprovalLinkageError(f"approval {approval_id} is missing linked task_step_id")

    unlocked_task = store.get_task_by_approval_optional(approval_id)
    if unlocked_task is None:
        raise TaskStepApprovalLinkageError(f"approval {approval_id} is not linked to a visible task")
    store.lock_task_steps(cast(UUID, unlocked_task["id"]))

    task = store.get_task_optional(cast(UUID, unlocked_task["id"]))
    if task is None:
        raise ContinuityStoreInvariantError(
            f"task for approval {approval_id} disappeared during approval linkage validation"
        )

    task_step = store.get_task_step_optional(task_step_id)
    if task_step is None:
        raise TaskStepApprovalLinkageError(
            f"approval {approval_id} references linked task step {task_step_id} that was not found"
        )
    if task_step["task_id"] != task["id"]:
        raise TaskStepApprovalLinkageError(
            f"approval {approval_id} links task step {task_step_id} outside task {task['id']}"
        )

    outcome = cast(TaskStepOutcomeSnapshot, task_step["outcome"])
    if outcome["approval_id"] != str(approval_id):
        raise TaskStepApprovalLinkageError(
            f"approval {approval_id} is inconsistent with linked task step {task_step_id}"
        )

    return task, task_step


def validate_linked_task_step_for_execution(
    store: ContinuityStore,
    *,
    task_id: UUID,
    execution: ToolExecutionRow,
) -> TaskStepRow:
    store.lock_task_steps(task_id)

    execution_id = cast(UUID, execution["id"])
    task_step_id = cast(UUID | None, execution["task_step_id"])
    if task_step_id is None:
        raise TaskStepExecutionLinkageError(
            f"tool execution {execution_id} is missing linked task_step_id"
        )

    task_step = store.get_task_step_optional(task_step_id)
    if task_step is None:
        raise TaskStepExecutionLinkageError(
            f"tool execution {execution_id} references linked task step {task_step_id} that was not found"
        )
    if task_step["task_id"] != task_id:
        raise TaskStepExecutionLinkageError(
            f"tool execution {execution_id} links task step {task_step_id} outside task {task_id}"
        )

    outcome = cast(TaskStepOutcomeSnapshot, task_step["outcome"])
    if outcome["approval_id"] != str(execution["approval_id"]):
        raise TaskStepExecutionLinkageError(
            f"tool execution {execution_id} is inconsistent with linked task step {task_step_id}"
        )

    return task_step


def serialize_task_row(row: TaskRow) -> TaskRecord:
    return {
        "id": str(row["id"]),
        "thread_id": str(row["thread_id"]),
        "tool_id": str(row["tool_id"]),
        "status": cast(TaskStatus, row["status"]),
        "request": cast(dict[str, object], row["request"]),
        "tool": cast(dict[str, object], row["tool"]),
        "latest_approval_id": None if row["latest_approval_id"] is None else str(row["latest_approval_id"]),
        "latest_execution_id": None if row["latest_execution_id"] is None else str(row["latest_execution_id"]),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def serialize_task_step_row(row: TaskStepRow) -> TaskStepRecord:
    return {
        "id": str(row["id"]),
        "task_id": str(row["task_id"]),
        "sequence_no": row["sequence_no"],
        "lineage": {
            "parent_step_id": None if row["parent_step_id"] is None else str(row["parent_step_id"]),
            "source_approval_id": (
                None if row["source_approval_id"] is None else str(row["source_approval_id"])
            ),
            "source_execution_id": (
                None if row["source_execution_id"] is None else str(row["source_execution_id"])
            ),
        },
        "kind": cast(str, row["kind"]),
        "status": cast(TaskStepStatus, row["status"]),
        "request": cast(dict[str, object], row["request"]),
        "outcome": cast(TaskStepOutcomeSnapshot, row["outcome"]),
        "trace": {
            "trace_id": str(row["trace_id"]),
            "trace_kind": row["trace_kind"],
        },
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def task_status_for_routing_decision(decision: str) -> TaskStatus:
    return {
        "approval_required": "pending_approval",
        "ready": "approved",
        "denied": "denied",
    }[decision]


def task_status_for_approval_status(approval_status: str) -> TaskStatus:
    return {
        "pending": "pending_approval",
        "approved": "approved",
        "rejected": "denied",
    }[approval_status]


def next_task_status_for_approval(
    *,
    current_status: TaskStatus,
    approval_status: str,
) -> TaskStatus:
    if current_status in {"executed", "blocked"}:
        return current_status
    return task_status_for_approval_status(approval_status)


def task_status_for_execution_status(execution_status: str) -> TaskStatus:
    return {
        "completed": "executed",
        "blocked": "blocked",
    }[execution_status]


def task_status_for_step_status(step_status: TaskStepStatus) -> TaskStatus:
    return {
        "created": "pending_approval",
        "approved": "approved",
        "executed": "executed",
        "blocked": "blocked",
        "denied": "denied",
    }[step_status]


def task_step_status_for_routing_decision(decision: str) -> TaskStepStatus:
    return {
        "approval_required": "created",
        "ready": "approved",
        "denied": "denied",
    }[decision]


def task_step_status_for_approval_status(approval_status: str) -> TaskStepStatus:
    return {
        "pending": "created",
        "approved": "approved",
        "rejected": "denied",
    }[approval_status]


def next_task_step_status_for_approval(
    *,
    current_status: TaskStepStatus,
    approval_status: str,
) -> TaskStepStatus:
    if current_status in {"executed", "blocked"}:
        return current_status
    return task_step_status_for_approval_status(approval_status)


def task_step_status_for_execution_status(execution_status: str) -> TaskStepStatus:
    return {
        "completed": "executed",
        "blocked": "blocked",
    }[execution_status]


def allowed_task_step_transitions(current_status: TaskStepStatus) -> list[TaskStepStatus]:
    return list(TASK_STEP_STATUS_GRAPH[current_status])


def task_step_outcome_snapshot(
    *,
    routing_decision: str,
    approval_id: str | None,
    approval_status: str | None,
    execution_id: str | None,
    execution_status: str | None,
    blocked_reason: str | None,
) -> TaskStepOutcomeSnapshot:
    return {
        "routing_decision": cast(str, routing_decision),
        "approval_id": approval_id,
        "approval_status": cast(str | None, approval_status),
        "execution_id": execution_id,
        "execution_status": cast(str | None, execution_status),
        "blocked_reason": blocked_reason,
    }


def create_task_for_governed_request(
    store: ContinuityStore,
    *,
    request: TaskCreateInput,
) -> TaskCreateResponse:
    task = store.create_task(
        thread_id=request.thread_id,
        tool_id=request.tool_id,
        status=request.status,
        request=cast(dict[str, object], request.request),
        tool=cast(dict[str, object], request.tool),
        latest_approval_id=request.latest_approval_id,
        latest_execution_id=request.latest_execution_id,
    )
    return {"task": serialize_task_row(task)}


def create_task_step_for_governed_request(
    store: ContinuityStore,
    *,
    request: TaskStepCreateInput,
) -> TaskStepCreateResponse:
    task_step = store.create_task_step(
        task_id=request.task_id,
        sequence_no=request.sequence_no,
        kind=request.kind,
        status=request.status,
        request=cast(dict[str, object], request.request),
        outcome=cast(dict[str, object], request.outcome),
        trace_id=request.trace_id,
        trace_kind=request.trace_kind,
    )
    return {"task_step": serialize_task_step_row(task_step)}


def _task_step_sequencing_summary(
    *,
    task_id: str,
    items: list[TaskStepRecord],
) -> TaskStepListSummary:
    latest = items[-1] if items else None
    latest_status = None if latest is None else latest["status"]
    latest_sequence_no = None if latest is None else latest["sequence_no"]
    return {
        "task_id": task_id,
        "total_count": len(items),
        "latest_sequence_no": latest_sequence_no,
        "latest_status": latest_status,
        "next_sequence_no": 1 if latest_sequence_no is None else latest_sequence_no + 1,
        "append_allowed": latest_status in TASK_STEP_APPENDABLE_STATUSES if latest_status is not None else False,
        "order": list(TASK_STEP_LIST_ORDER),
    }


def _validated_optional_approval_id(
    store: ContinuityStore,
    *,
    approval_id: str | None,
    current_approval_id: UUID | None,
    task: TaskRow,
    require_existing: bool,
    missing_error: str,
    error_cls: type[TaskStepSequenceError] | type[TaskStepTransitionError],
) -> UUID | None:
    def _approval_belongs_to_task(approval_uuid: UUID) -> bool:
        if current_approval_id == approval_uuid:
            return True
        for task_step in store.list_task_steps_for_task(task["id"]):
            outcome = cast(dict[str, object], task_step["outcome"])
            linked_approval_id = outcome.get("approval_id")
            if linked_approval_id is not None and str(linked_approval_id) == str(approval_uuid):
                return True
        return False

    if approval_id is None:
        if require_existing and current_approval_id is None:
            raise error_cls(missing_error)
        approval_uuid = current_approval_id
    else:
        approval_uuid = UUID(approval_id)
        if not _approval_belongs_to_task(approval_uuid):
            raise error_cls(f"approval {approval_uuid} does not belong to task {task['id']}")

    if approval_uuid is None:
        return None

    approval_row = store.get_approval_optional(approval_uuid)
    if approval_row is None:
        raise error_cls(f"approval {approval_uuid} was not found")
    return approval_uuid


def _validated_optional_execution_id(
    store: ContinuityStore,
    *,
    execution_id: str | None,
    current_execution_id: UUID | None,
    task: TaskRow,
    require_existing: bool,
    missing_error: str,
    error_cls: type[TaskStepSequenceError] | type[TaskStepTransitionError],
) -> UUID | None:
    def _execution_belongs_to_task(execution_uuid: UUID) -> bool:
        if current_execution_id == execution_uuid:
            return True
        for task_step in store.list_task_steps_for_task(task["id"]):
            outcome = cast(dict[str, object], task_step["outcome"])
            linked_execution_id = outcome.get("execution_id")
            if linked_execution_id is not None and str(linked_execution_id) == str(execution_uuid):
                return True
        return False

    if execution_id is None:
        if require_existing and current_execution_id is None:
            raise error_cls(missing_error)
        execution_uuid = current_execution_id
    else:
        execution_uuid = UUID(execution_id)
        if not _execution_belongs_to_task(execution_uuid):
            raise error_cls(f"tool execution {execution_uuid} does not belong to task {task['id']}")

    if execution_uuid is None:
        return None

    execution_row = store.get_tool_execution_optional(execution_uuid)
    if execution_row is None:
        raise error_cls(f"tool execution {execution_uuid} was not found")
    return execution_uuid


def _validated_continuation_parent_step(
    *,
    task_id: UUID,
    latest: TaskStepRecord,
    existing_items: list[TaskStepRecord],
    parent_step_id: UUID,
) -> TaskStepRecord:
    parent_step = next(
        (
            item
            for item in existing_items
            if item["id"] == str(parent_step_id)
        ),
        None,
    )
    if parent_step is None:
        raise TaskStepSequenceError(f"task step {parent_step_id} does not belong to task {task_id}")
    if parent_step["id"] != latest["id"]:
        raise TaskStepSequenceError(
            f"task {task_id} continuation must reference latest step {latest['id']}; received {parent_step_id}"
        )
    return parent_step


def _validated_continuation_lineage(
    *,
    parent_step: TaskStepRecord,
    source_approval_id: UUID | None,
    source_execution_id: UUID | None,
) -> TaskStepLineageRecord:
    parent_outcome = parent_step["outcome"]
    if source_approval_id is not None and parent_outcome["approval_id"] != str(source_approval_id):
        raise TaskStepSequenceError(
            f"approval {source_approval_id} is not linked from parent step {parent_step['id']}"
        )
    if source_execution_id is not None and parent_outcome["execution_id"] != str(source_execution_id):
        raise TaskStepSequenceError(
            f"tool execution {source_execution_id} is not linked from parent step {parent_step['id']}"
        )

    return {
        "parent_step_id": parent_step["id"],
        "source_approval_id": None if source_approval_id is None else str(source_approval_id),
        "source_execution_id": None if source_execution_id is None else str(source_execution_id),
    }


def sync_task_with_task_step_status(
    store: ContinuityStore,
    *,
    task_id: UUID,
    task_step_status: TaskStepStatus,
    linked_approval_id: UUID | None,
    linked_execution_id: UUID | None,
) -> TaskTransitionResult:
    current = store.get_task_optional(task_id)
    if current is None:
        raise ContinuityStoreInvariantError(
            f"task {task_id} disappeared before task-step lifecycle synchronization"
        )
    previous_status = cast(TaskStatus, current["status"])
    target_status = task_status_for_step_status(task_step_status)
    latest_execution_id = (
        current["latest_execution_id"] if linked_execution_id is None else linked_execution_id
    ) if target_status in {"executed", "blocked"} else None
    updated = store.update_task_status_optional(
        task_id=task_id,
        status=target_status,
        latest_approval_id=linked_approval_id,
        latest_execution_id=latest_execution_id,
    )
    if updated is None:
        raise ContinuityStoreInvariantError(
            f"task {task_id} disappeared during task-step lifecycle synchronization"
        )
    return TaskTransitionResult(
        task=serialize_task_row(updated),
        previous_status=previous_status,
    )


def sync_task_with_approval(
    store: ContinuityStore,
    *,
    approval_id: UUID,
    approval_status: str,
) -> TaskTransitionResult:
    current = store.get_task_by_approval_optional(approval_id)
    if current is None:
        raise ContinuityStoreInvariantError(
            f"task for approval {approval_id} disappeared before lifecycle synchronization"
        )
    previous_status = cast(TaskStatus, current["status"])

    updated = store.update_task_status_by_approval_optional(
        approval_id=approval_id,
        status=next_task_status_for_approval(
            current_status=previous_status,
            approval_status=approval_status,
        ),
    )
    if updated is None:
        raise ContinuityStoreInvariantError(
            f"task for approval {approval_id} disappeared during lifecycle synchronization"
        )

    return TaskTransitionResult(
        task=serialize_task_row(updated),
        previous_status=previous_status,
    )


def sync_task_step_with_approval(
    store: ContinuityStore,
    *,
    approval_id: UUID,
    task_step_id: UUID | None,
    approval_status: str,
    trace_id: UUID,
    trace_kind: str,
) -> TaskStepTransitionResult:
    _, current = validate_linked_task_step_for_approval(
        store,
        approval_id=approval_id,
        task_step_id=task_step_id,
    )
    previous_status = cast(TaskStepStatus, current["status"])
    current_outcome = cast(TaskStepOutcomeSnapshot, current["outcome"])
    updated_outcome = task_step_outcome_snapshot(
        routing_decision=current_outcome["routing_decision"],
        approval_id=str(approval_id),
        approval_status=approval_status,
        execution_id=current_outcome["execution_id"],
        execution_status=current_outcome["execution_status"],
        blocked_reason=current_outcome["blocked_reason"],
    )

    updated = store.update_task_step_optional(
        task_step_id=cast(UUID, current["id"]),
        status=next_task_step_status_for_approval(
            current_status=previous_status,
            approval_status=approval_status,
        ),
        outcome=cast(dict[str, object], updated_outcome),
        trace_id=trace_id,
        trace_kind=trace_kind,
    )
    if updated is None:
        raise ContinuityStoreInvariantError(
            f"linked task step {current['id']} disappeared during approval lifecycle synchronization"
        )

    return TaskStepTransitionResult(
        task_step=serialize_task_step_row(updated),
        previous_status=previous_status,
    )


def sync_task_with_execution(
    store: ContinuityStore,
    *,
    approval_id: UUID,
    execution_id: UUID,
    execution_status: str,
) -> TaskTransitionResult:
    current = store.get_task_by_approval_optional(approval_id)
    if current is None:
        raise ContinuityStoreInvariantError(
            f"task for approval {approval_id} disappeared before execution synchronization"
        )
    previous_status = cast(TaskStatus, current["status"])

    updated = store.update_task_execution_by_approval_optional(
        approval_id=approval_id,
        latest_execution_id=execution_id,
        status=task_status_for_execution_status(execution_status),
    )
    if updated is None:
        raise ContinuityStoreInvariantError(
            f"task for approval {approval_id} disappeared during execution synchronization"
        )

    return TaskTransitionResult(
        task=serialize_task_row(updated),
        previous_status=previous_status,
    )


def sync_task_step_with_execution(
    store: ContinuityStore,
    *,
    task_id: UUID,
    execution: ToolExecutionRow,
    trace_id: UUID,
    trace_kind: str,
) -> TaskStepTransitionResult:
    current = validate_linked_task_step_for_execution(
        store,
        task_id=task_id,
        execution=execution,
    )
    previous_status = cast(TaskStepStatus, current["status"])
    current_outcome = cast(TaskStepOutcomeSnapshot, current["outcome"])
    execution_result = cast(dict[str, object], execution["result"])
    updated_outcome = task_step_outcome_snapshot(
        routing_decision=current_outcome["routing_decision"],
        approval_id=current_outcome["approval_id"],
        approval_status=current_outcome["approval_status"],
        execution_id=str(execution["id"]),
        execution_status=cast(str, execution["status"]),
        blocked_reason=cast(str | None, execution_result.get("reason")),
    )

    updated = store.update_task_step_optional(
        task_step_id=cast(UUID, current["id"]),
        status=task_step_status_for_execution_status(cast(str, execution["status"])),
        outcome=cast(dict[str, object], updated_outcome),
        trace_id=trace_id,
        trace_kind=trace_kind,
    )
    if updated is None:
        raise ContinuityStoreInvariantError(
            f"linked task step {current['id']} disappeared during execution lifecycle synchronization"
        )

    return TaskStepTransitionResult(
        task_step=serialize_task_step_row(updated),
        previous_status=previous_status,
    )


def create_next_task_step_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskStepNextCreateInput,
) -> TaskStepNextCreateResponse:
    del user_id

    task_row = store.get_task_optional(request.task_id)
    if task_row is None:
        raise TaskNotFoundError(f"task {request.task_id} was not found")

    store.lock_task_steps(request.task_id)
    existing_items = [serialize_task_step_row(row) for row in store.list_task_steps_for_task(request.task_id)]
    if not existing_items:
        raise TaskStepSequenceError(f"task {request.task_id} has no existing steps and cannot append a next step")

    latest = existing_items[-1]
    if latest["status"] not in TASK_STEP_APPENDABLE_STATUSES:
        raise TaskStepSequenceError(
            f"task {request.task_id} latest step {latest['id']} is {latest['status']} and cannot append a next step"
        )
    if request.status not in TASK_STEP_INITIAL_STATUSES:
        allowed = ", ".join(sorted(TASK_STEP_INITIAL_STATUSES))
        raise TaskStepSequenceError(
            f"new task step for task {request.task_id} must start in one of {allowed}; received {request.status}"
        )
    parent_step = _validated_continuation_parent_step(
        task_id=request.task_id,
        latest=latest,
        existing_items=existing_items,
        parent_step_id=request.lineage.parent_step_id,
    )
    source_approval_id = _validated_optional_approval_id(
        store,
        approval_id=(
            None if request.lineage.source_approval_id is None else str(request.lineage.source_approval_id)
        ),
        current_approval_id=None,
        task=task_row,
        require_existing=False,
        missing_error="",
        error_cls=TaskStepSequenceError,
    )
    source_execution_id = _validated_optional_execution_id(
        store,
        execution_id=(
            None if request.lineage.source_execution_id is None else str(request.lineage.source_execution_id)
        ),
        current_execution_id=None,
        task=task_row,
        require_existing=False,
        missing_error="",
        error_cls=TaskStepSequenceError,
    )
    lineage = _validated_continuation_lineage(
        parent_step=parent_step,
        source_approval_id=source_approval_id,
        source_execution_id=source_execution_id,
    )
    linked_approval_id = _validated_optional_approval_id(
        store,
        approval_id=request.outcome["approval_id"],
        current_approval_id=None,
        task=task_row,
        require_existing=False,
        missing_error="",
        error_cls=TaskStepSequenceError,
    )
    linked_execution_id = _validated_optional_execution_id(
        store,
        execution_id=request.outcome["execution_id"],
        current_execution_id=None,
        task=task_row,
        require_existing=False,
        missing_error="",
        error_cls=TaskStepSequenceError,
    )

    trace = store.create_trace(
        user_id=task_row["user_id"],
        thread_id=task_row["thread_id"],
        kind=TRACE_KIND_TASK_STEP_CONTINUATION,
        compiler_version=TASK_STEP_CONTINUATION_VERSION_V0,
        status="completed",
        limits={
            "order": list(TASK_STEP_LIST_ORDER),
            "appendable_statuses": sorted(TASK_STEP_APPENDABLE_STATUSES),
            "initial_statuses": sorted(TASK_STEP_INITIAL_STATUSES),
            "parent_step_id": parent_step["id"],
            "parent_sequence_no": parent_step["sequence_no"],
        },
    )
    try:
        created = store.create_task_step(
            task_id=request.task_id,
            sequence_no=latest["sequence_no"] + 1,
            parent_step_id=request.lineage.parent_step_id,
            source_approval_id=source_approval_id,
            source_execution_id=source_execution_id,
            kind=request.kind,
            status=request.status,
            request=cast(dict[str, object], request.request),
            outcome=cast(dict[str, object], request.outcome),
            trace_id=trace["id"],
            trace_kind=TRACE_KIND_TASK_STEP_CONTINUATION,
        )
    except psycopg.IntegrityError as exc:
        raise TaskStepSequenceError(
            f"task {request.task_id} next-step creation conflicted with a concurrent append"
        ) from exc
    task_step = serialize_task_step_row(created)
    task_transition = sync_task_with_task_step_status(
        store,
        task_id=request.task_id,
        task_step_status=request.status,
        linked_approval_id=(
            source_approval_id if request.status == "created" and linked_approval_id is None else linked_approval_id
        ),
        linked_execution_id=linked_execution_id,
    )
    updated_items = [*existing_items, task_step]
    sequencing = _task_step_sequencing_summary(
        task_id=str(task_row["id"]),
        items=updated_items,
    )

    request_payload: TaskStepContinuationRequestTracePayload = {
        "task_id": str(task_row["id"]),
        "parent_task_step_id": parent_step["id"],
        "parent_sequence_no": parent_step["sequence_no"],
        "parent_status": parent_step["status"],
        "requested_kind": request.kind,
        "requested_status": request.status,
        "requested_source_approval_id": lineage["source_approval_id"],
        "requested_source_execution_id": lineage["source_execution_id"],
    }
    lineage_payload: TaskStepContinuationLineageTracePayload = {
        "task_id": str(task_row["id"]),
        "parent_task_step_id": parent_step["id"],
        "parent_sequence_no": parent_step["sequence_no"],
        "parent_status": parent_step["status"],
        "source_approval_id": lineage["source_approval_id"],
        "source_execution_id": lineage["source_execution_id"],
    }
    summary_payload: TaskStepContinuationSummaryTracePayload = {
        "task_id": str(task_row["id"]),
        "task_step_id": task_step["id"],
        "latest_sequence_no": task_step["sequence_no"],
        "next_sequence_no": sequencing["next_sequence_no"],
        "append_allowed": sequencing["append_allowed"],
        "lineage": task_step["lineage"],
    }
    trace_events: list[tuple[str, dict[str, object]]] = [
        (TASK_STEP_CONTINUATION_REQUEST_EVENT_KIND, cast(dict[str, object], request_payload)),
        (TASK_STEP_CONTINUATION_LINEAGE_EVENT_KIND, cast(dict[str, object], lineage_payload)),
        (TASK_STEP_CONTINUATION_SUMMARY_EVENT_KIND, cast(dict[str, object], summary_payload)),
    ]
    trace_events.extend(
        task_lifecycle_trace_events(
            task=task_transition.task,
            previous_status=task_transition.previous_status,
            source="task_step_continuation",
        )
    )
    trace_events.extend(
        task_step_lifecycle_trace_events(
            task_step=task_step,
            previous_status=None,
            source="task_step_continuation",
        )
    )
    _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)

    return {
        "task": task_transition.task,
        "task_step": task_step,
        "sequencing": sequencing,
        "trace": _trace_summary(trace["id"], trace_events),
    }


def transition_task_step_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskStepTransitionInput,
) -> TaskStepTransitionResponse:
    del user_id

    step_row = store.get_task_step_optional(request.task_step_id)
    if step_row is None:
        raise TaskStepNotFoundError(f"task step {request.task_step_id} was not found")

    task_row = store.get_task_optional(step_row["task_id"])
    if task_row is None:
        raise ContinuityStoreInvariantError(
            f"task {step_row['task_id']} disappeared before task-step transition"
        )

    existing_items = [serialize_task_step_row(row) for row in store.list_task_steps_for_task(step_row["task_id"])]
    latest = existing_items[-1] if existing_items else None
    if latest is None:
        raise ContinuityStoreInvariantError(
            f"task {step_row['task_id']} has no visible steps during transition"
        )
    if latest["id"] != str(step_row["id"]):
        raise TaskStepTransitionError(
            f"task step {request.task_step_id} is not the latest step on task {step_row['task_id']}"
        )

    previous_status = cast(TaskStepStatus, step_row["status"])
    allowed_next_statuses = allowed_task_step_transitions(previous_status)
    if request.status not in allowed_next_statuses:
        allowed = ", ".join(allowed_next_statuses) or "no further statuses"
        raise TaskStepTransitionError(
            f"task step {request.task_step_id} is {previous_status} and cannot transition to {request.status}; allowed: {allowed}"
        )
    linked_approval_id = _validated_optional_approval_id(
        store,
        approval_id=request.outcome["approval_id"],
        current_approval_id=task_row["latest_approval_id"],
        task=task_row,
        require_existing=request.status == "created",
        missing_error=f"task {task_row['id']} cannot reflect created without an approval link",
        error_cls=TaskStepTransitionError,
    )
    linked_execution_id = _validated_optional_execution_id(
        store,
        execution_id=request.outcome["execution_id"],
        current_execution_id=task_row["latest_execution_id"],
        task=task_row,
        require_existing=request.status in {"executed", "blocked"},
        missing_error=f"task {task_row['id']} cannot reflect {request.status} without an existing execution link",
        error_cls=TaskStepTransitionError,
    )

    trace = store.create_trace(
        user_id=task_row["user_id"],
        thread_id=task_row["thread_id"],
        kind=TRACE_KIND_TASK_STEP_TRANSITION,
        compiler_version=TASK_STEP_TRANSITION_VERSION_V0,
        status="completed",
        limits={
            "order": list(TASK_STEP_LIST_ORDER),
            "status_graph": {status: list(next_statuses) for status, next_statuses in TASK_STEP_STATUS_GRAPH.items()},
            "requested_status": request.status,
        },
    )
    updated_row = store.update_task_step_for_task_sequence_optional(
        task_id=step_row["task_id"],
        sequence_no=step_row["sequence_no"],
        status=request.status,
        outcome=cast(dict[str, object], request.outcome),
        trace_id=trace["id"],
        trace_kind=TRACE_KIND_TASK_STEP_TRANSITION,
    )
    if updated_row is None:
        raise ContinuityStoreInvariantError(
            f"task step {request.task_step_id} disappeared during transition"
        )

    updated_step = serialize_task_step_row(updated_row)
    task_transition = sync_task_with_task_step_status(
        store,
        task_id=step_row["task_id"],
        task_step_status=request.status,
        linked_approval_id=linked_approval_id,
        linked_execution_id=linked_execution_id,
    )
    updated_items = [*existing_items[:-1], updated_step]
    sequencing = _task_step_sequencing_summary(
        task_id=str(task_row["id"]),
        items=updated_items,
    )

    request_payload: TaskStepTransitionRequestTracePayload = {
        "task_id": str(task_row["id"]),
        "task_step_id": updated_step["id"],
        "sequence_no": updated_step["sequence_no"],
        "previous_status": previous_status,
        "requested_status": request.status,
    }
    state_payload: TaskStepTransitionStateTracePayload = {
        "task_id": str(task_row["id"]),
        "task_step_id": updated_step["id"],
        "sequence_no": updated_step["sequence_no"],
        "previous_status": previous_status,
        "current_status": updated_step["status"],
        "allowed_next_statuses": allowed_next_statuses,
        "trace": updated_step["trace"],
    }
    summary_payload: TaskStepTransitionSummaryTracePayload = {
        "task_id": str(task_row["id"]),
        "task_step_id": updated_step["id"],
        "sequence_no": updated_step["sequence_no"],
        "final_status": updated_step["status"],
        "parent_task_status": task_transition.task["status"],
        "trace": updated_step["trace"],
    }
    trace_events: list[tuple[str, dict[str, object]]] = [
        (TASK_STEP_TRANSITION_REQUEST_EVENT_KIND, cast(dict[str, object], request_payload)),
        (TASK_STEP_TRANSITION_STATE_EVENT_KIND, cast(dict[str, object], state_payload)),
        (TASK_STEP_TRANSITION_SUMMARY_EVENT_KIND, cast(dict[str, object], summary_payload)),
    ]
    trace_events.extend(
        task_lifecycle_trace_events(
            task=task_transition.task,
            previous_status=task_transition.previous_status,
            source="task_step_transition",
        )
    )
    trace_events.extend(
        task_step_lifecycle_trace_events(
            task_step=updated_step,
            previous_status=previous_status,
            source="task_step_transition",
        )
    )
    _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)

    return {
        "task": task_transition.task,
        "task_step": updated_step,
        "sequencing": sequencing,
        "trace": _trace_summary(trace["id"], trace_events),
    }


def task_lifecycle_trace_events(
    *,
    task: TaskRecord,
    previous_status: TaskStatus | None,
    source: TaskLifecycleSource,
) -> list[tuple[str, dict[str, object]]]:
    state_payload: TaskLifecycleStateTracePayload = {
        "task_id": task["id"],
        "source": source,
        "previous_status": previous_status,
        "current_status": task["status"],
        "latest_approval_id": task["latest_approval_id"],
        "latest_execution_id": task["latest_execution_id"],
    }
    summary_payload: TaskLifecycleSummaryTracePayload = {
        "task_id": task["id"],
        "source": source,
        "final_status": task["status"],
        "latest_approval_id": task["latest_approval_id"],
        "latest_execution_id": task["latest_execution_id"],
    }
    return [
        (TASK_LIFECYCLE_STATE_EVENT_KIND, cast(dict[str, object], state_payload)),
        (TASK_LIFECYCLE_SUMMARY_EVENT_KIND, cast(dict[str, object], summary_payload)),
    ]


def task_step_lifecycle_trace_events(
    *,
    task_step: TaskStepRecord,
    previous_status: TaskStepStatus | None,
    source: TaskLifecycleSource,
) -> list[tuple[str, dict[str, object]]]:
    state_payload: TaskStepLifecycleStateTracePayload = {
        "task_id": task_step["task_id"],
        "task_step_id": task_step["id"],
        "source": source,
        "sequence_no": task_step["sequence_no"],
        "kind": task_step["kind"],
        "previous_status": previous_status,
        "current_status": task_step["status"],
        "trace": task_step["trace"],
    }
    summary_payload: TaskStepLifecycleSummaryTracePayload = {
        "task_id": task_step["task_id"],
        "task_step_id": task_step["id"],
        "source": source,
        "sequence_no": task_step["sequence_no"],
        "kind": task_step["kind"],
        "final_status": task_step["status"],
        "trace": task_step["trace"],
    }
    return [
        (TASK_STEP_LIFECYCLE_STATE_EVENT_KIND, cast(dict[str, object], state_payload)),
        (TASK_STEP_LIFECYCLE_SUMMARY_EVENT_KIND, cast(dict[str, object], summary_payload)),
    ]


def list_task_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> TaskListResponse:
    del user_id

    items = [serialize_task_row(row) for row in store.list_tasks()]
    summary: TaskListSummary = {
        "total_count": len(items),
        "order": list(TASK_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_task_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_id: UUID,
) -> TaskDetailResponse:
    del user_id

    task = store.get_task_optional(task_id)
    if task is None:
        raise TaskNotFoundError(f"task {task_id} was not found")
    return {"task": serialize_task_row(task)}


def list_task_step_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_id: UUID,
) -> TaskStepListResponse:
    del user_id

    task = store.get_task_optional(task_id)
    if task is None:
        raise TaskNotFoundError(f"task {task_id} was not found")

    items = [serialize_task_step_row(row) for row in store.list_task_steps_for_task(task_id)]
    summary = _task_step_sequencing_summary(task_id=str(task["id"]), items=items)
    return {
        "items": items,
        "summary": summary,
    }


def get_task_step_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_step_id: UUID,
) -> TaskStepDetailResponse:
    del user_id

    task_step = store.get_task_step_optional(task_step_id)
    if task_step is None:
        raise TaskStepNotFoundError(f"task step {task_step_id} was not found")
    return {"task_step": serialize_task_step_row(task_step)}
