from __future__ import annotations

from typing import cast
from uuid import UUID

from alicebot_api.contracts import (
    APPROVAL_LIST_ORDER,
    APPROVAL_REQUEST_VERSION_V0,
    APPROVAL_RESOLUTION_VERSION_V0,
    TRACE_KIND_APPROVAL_REQUEST,
    TRACE_KIND_APPROVAL_RESOLUTION,
    ApprovalApproveInput,
    ApprovalDetailResponse,
    ApprovalListResponse,
    ApprovalListSummary,
    ApprovalRecord,
    ApprovalRejectInput,
    ApprovalResolutionAction,
    ApprovalResolutionOutcome,
    ApprovalResolutionRecord,
    ApprovalResolutionRequestTracePayload,
    ApprovalResolutionResponse,
    ApprovalResolutionStateTracePayload,
    ApprovalResolutionSummaryTracePayload,
    ApprovalRequestCreateInput,
    ApprovalRequestCreateResponse,
    ApprovalRequestTraceSummary,
    ApprovalRoutingRecord,
    TaskCreateInput,
    TaskStepCreateInput,
    ToolRoutingRequestInput,
)
from alicebot_api.store import ApprovalRow, ContinuityStore, JsonObject
from alicebot_api.tasks import (
    DEFAULT_TASK_STEP_KIND,
    DEFAULT_TASK_STEP_SEQUENCE_NO,
    create_task_step_for_governed_request,
    create_task_for_governed_request,
    sync_task_step_with_approval,
    task_step_lifecycle_trace_events,
    task_step_outcome_snapshot,
    task_step_status_for_routing_decision,
    sync_task_with_approval,
    task_lifecycle_trace_events,
    task_status_for_routing_decision,
    validate_linked_task_step_for_approval,
)
from alicebot_api.tools import route_tool_invocation


class ApprovalNotFoundError(LookupError):
    """Raised when an approval record is not visible inside the current user scope."""


class ApprovalResolutionConflictError(RuntimeError):
    """Raised when a visible approval record is no longer pending."""


def _serialize_resolution(row: ApprovalRow) -> ApprovalResolutionRecord | None:
    if row["resolved_at"] is None or row["resolved_by_user_id"] is None:
        return None
    return {
        "resolved_at": row["resolved_at"].isoformat(),
        "resolved_by_user_id": str(row["resolved_by_user_id"]),
    }


def serialize_approval_row(row: ApprovalRow) -> ApprovalRecord:
    payload: ApprovalRecord = {
        "id": str(row["id"]),
        "thread_id": str(row["thread_id"]),
        "task_step_id": None if row["task_step_id"] is None else str(row["task_step_id"]),
        "status": cast(str, row["status"]),
        "request": cast(dict[str, object], row["request"]),
        "tool": cast(dict[str, object], row["tool"]),
        "routing": cast(ApprovalRoutingRecord, row["routing"]),
        "created_at": row["created_at"].isoformat(),
        "resolution": _serialize_resolution(row),
    }
    task_run_id = cast(UUID | None, row.get("task_run_id"))
    if task_run_id is not None:
        payload["task_run_id"] = str(task_run_id)
    return payload


_serialize_approval = serialize_approval_row


def _resume_task_run_after_resolution(
    store: ContinuityStore,
    *,
    approval: ApprovalRow,
) -> tuple[str, str] | None:
    task_run_id = cast(UUID | None, approval.get("task_run_id"))
    if task_run_id is None:
        return None

    task_run = store.get_task_run_optional(task_run_id)
    if task_run is None:
        return None
    if cast(str, task_run["status"]) != "waiting_approval":
        return None

    checkpoint = cast(JsonObject, task_run["checkpoint"])
    if not isinstance(checkpoint, dict):
        checkpoint = {}
    updated_checkpoint = dict(checkpoint)
    updated_checkpoint["wait_for_signal"] = False
    updated_checkpoint["waiting_approval_id"] = None
    updated_checkpoint["resolved_approval_id"] = str(approval["id"])
    updated_checkpoint["approval_resolution_status"] = cast(str, approval["status"])

    next_status = "queued" if approval["status"] == "approved" else "completed"
    next_stop_reason = None if next_status == "queued" else "completed"
    updated = store.update_task_run_optional(
        task_run_id=task_run_id,
        status=next_status,
        checkpoint=updated_checkpoint,
        tick_count=int(task_run["tick_count"]),
        step_count=int(task_run["step_count"]),
        stop_reason=next_stop_reason,
    )
    if updated is None:
        return None
    return cast(str, task_run["status"]), cast(str, updated["status"])


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


def _resolution_outcome(
    *,
    requested_action: ApprovalResolutionAction,
    current_status: str,
) -> ApprovalResolutionOutcome:
    if (
        requested_action == "approve"
        and current_status == "approved"
    ) or (
        requested_action == "reject"
        and current_status == "rejected"
    ):
        return "duplicate_rejected"
    return "conflict_rejected"


def _resolution_error(
    approval_id: UUID,
    *,
    requested_action: ApprovalResolutionAction,
    current_status: str,
) -> ApprovalResolutionConflictError:
    if (
        requested_action == "approve"
        and current_status == "approved"
    ) or (
        requested_action == "reject"
        and current_status == "rejected"
    ):
        return ApprovalResolutionConflictError(f"approval {approval_id} was already {current_status}")

    requested_status = "approved" if requested_action == "approve" else "rejected"
    return ApprovalResolutionConflictError(
        f"approval {approval_id} was already {current_status} and cannot be {requested_status}"
    )


def _resolve_approval(
    store: ContinuityStore,
    *,
    user_id: UUID,
    approval_id: UUID,
    requested_action: ApprovalResolutionAction,
    resolved_status: str,
) -> ApprovalResolutionResponse:
    del user_id

    approval = store.get_approval_optional(approval_id)
    if approval is None:
        raise ApprovalNotFoundError(f"approval {approval_id} was not found")
    validate_linked_task_step_for_approval(
        store,
        approval_id=approval_id,
        task_step_id=cast(UUID | None, approval["task_step_id"]),
    )

    previous_status = cast(str, approval["status"])
    current = approval
    outcome: ApprovalResolutionOutcome

    if approval["status"] == "pending":
        resolved = store.resolve_approval_optional(
            approval_id=approval_id,
            status=resolved_status,
        )
        if resolved is None:
            current = store.get_approval_optional(approval_id)
            if current is None:
                raise ApprovalNotFoundError(f"approval {approval_id} was not found")
            outcome = _resolution_outcome(
                requested_action=requested_action,
                current_status=cast(str, current["status"]),
            )
        else:
            current = resolved
            outcome = "resolved"
    else:
        outcome = _resolution_outcome(
            requested_action=requested_action,
            current_status=previous_status,
        )

    trace = store.create_trace(
        user_id=current["user_id"],
        thread_id=current["thread_id"],
        kind=TRACE_KIND_APPROVAL_RESOLUTION,
        compiler_version=APPROVAL_RESOLUTION_VERSION_V0,
        status="completed",
        limits={
            "order": list(APPROVAL_LIST_ORDER),
            "requested_action": requested_action,
            "outcome": outcome,
        },
    )

    resolution = _serialize_resolution(current)
    linked_task_step_id = None if current["task_step_id"] is None else str(current["task_step_id"])
    request_payload: ApprovalResolutionRequestTracePayload = {
        "approval_id": str(approval_id),
        "task_step_id": linked_task_step_id,
        "requested_action": requested_action,
    }
    state_payload: ApprovalResolutionStateTracePayload = {
        "approval_id": str(current["id"]),
        "task_step_id": linked_task_step_id,
        "requested_action": requested_action,
        "previous_status": previous_status,
        "outcome": outcome,
        "current_status": cast(str, current["status"]),
        "resolved_at": None if resolution is None else resolution["resolved_at"],
        "resolved_by_user_id": None if resolution is None else resolution["resolved_by_user_id"],
    }
    summary_payload: ApprovalResolutionSummaryTracePayload = {
        "approval_id": str(current["id"]),
        "task_step_id": linked_task_step_id,
        "requested_action": requested_action,
        "outcome": outcome,
        "final_status": cast(str, current["status"]),
    }
    task_transition = sync_task_with_approval(
        store,
        approval_id=current["id"],
        approval_status=cast(str, current["status"]),
    )
    task_step_transition = sync_task_step_with_approval(
        store,
        approval_id=current["id"],
        task_step_id=cast(UUID | None, current["task_step_id"]),
        approval_status=cast(str, current["status"]),
        trace_id=trace["id"],
        trace_kind=TRACE_KIND_APPROVAL_RESOLUTION,
    )
    run_transition = _resume_task_run_after_resolution(store, approval=current)
    trace_events: list[tuple[str, dict[str, object]]] = [
        ("approval.resolution.request", cast(dict[str, object], request_payload)),
        ("approval.resolution.state", cast(dict[str, object], state_payload)),
        ("approval.resolution.summary", cast(dict[str, object], summary_payload)),
    ]
    if run_transition is not None:
        previous_run_status, current_run_status = run_transition
        trace_events.append(
            (
                "approval.resolution.run",
                {
                    "approval_id": str(current["id"]),
                    "task_run_id": str(cast(UUID, current.get("task_run_id"))),
                    "previous_status": previous_run_status,
                    "current_status": current_run_status,
                },
            )
        )
    trace_events.extend(
        task_lifecycle_trace_events(
            task=task_transition.task,
            previous_status=task_transition.previous_status,
            source="approval_resolution",
        )
    )
    trace_events.extend(
        task_step_lifecycle_trace_events(
            task_step=task_step_transition.task_step,
            previous_status=task_step_transition.previous_status,
            source="approval_resolution",
        )
    )
    _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)

    if outcome != "resolved":
        raise _resolution_error(
            approval_id,
            requested_action=requested_action,
            current_status=cast(str, current["status"]),
        )

    return {
        "approval": _serialize_approval(current),
        "trace": {
            "trace_id": str(trace["id"]),
            "trace_event_count": len(trace_events),
        },
    }


def submit_approval_request(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ApprovalRequestCreateInput,
) -> ApprovalRequestCreateResponse:
    routing = route_tool_invocation(
        store,
        user_id=user_id,
        request=ToolRoutingRequestInput(
            thread_id=request.thread_id,
            tool_id=request.tool_id,
            action=request.action,
            scope=request.scope,
            domain_hint=request.domain_hint,
            risk_hint=request.risk_hint,
            attributes=request.attributes,
        ),
    )

    thread = store.get_thread_optional(request.thread_id)
    if thread is None:
        raise RuntimeError("validated thread disappeared before approval request trace creation")

    approval_persist_requested = routing["decision"] == "approval_required"
    approval = None
    approval_created = False
    if routing["decision"] == "approval_required":
        try:
            approval_row = store.create_approval(
                thread_id=request.thread_id,
                tool_id=request.tool_id,
                task_run_id=request.task_run_id,
                task_step_id=None,
                status="pending",
                request=routing["request"],
                tool=routing["tool"],
                routing={
                    "decision": routing["decision"],
                    "reasons": routing["reasons"],
                    "trace": routing["trace"],
                },
                routing_trace_id=UUID(routing["trace"]["trace_id"]),
            )
        except TypeError:
            approval_row = store.create_approval(
                thread_id=request.thread_id,
                tool_id=request.tool_id,
                task_step_id=None,
                status="pending",
                request=routing["request"],
                tool=routing["tool"],
                routing={
                    "decision": routing["decision"],
                    "reasons": routing["reasons"],
                    "trace": routing["trace"],
                },
                routing_trace_id=UUID(routing["trace"]["trace_id"]),
            )
        approval = _serialize_approval(approval_row)
        approval_created = True

    task = create_task_for_governed_request(
        store,
        request=TaskCreateInput(
            thread_id=request.thread_id,
            tool_id=request.tool_id,
            status=task_status_for_routing_decision(routing["decision"]),
            request=routing["request"],
            tool=routing["tool"],
            latest_approval_id=None if approval is None else UUID(approval["id"]),
        ),
    )["task"]

    trace = store.create_trace(
        user_id=thread["user_id"],
        thread_id=thread["id"],
        kind=TRACE_KIND_APPROVAL_REQUEST,
        compiler_version=APPROVAL_REQUEST_VERSION_V0,
        status="completed",
        limits={
            "order": list(APPROVAL_LIST_ORDER),
            "persisted": approval_persist_requested,
        },
    )
    task_step = create_task_step_for_governed_request(
        store,
        request=TaskStepCreateInput(
            task_id=UUID(task["id"]),
            sequence_no=DEFAULT_TASK_STEP_SEQUENCE_NO,
            kind=DEFAULT_TASK_STEP_KIND,
            status=task_step_status_for_routing_decision(routing["decision"]),
            request=routing["request"],
            outcome=task_step_outcome_snapshot(
                routing_decision=routing["decision"],
                approval_id=None if approval is None else approval["id"],
                approval_status=None if approval is None else approval["status"],
                execution_id=None,
                execution_status=None,
                blocked_reason=None,
            ),
            trace_id=trace["id"],
            trace_kind=TRACE_KIND_APPROVAL_REQUEST,
        ),
    )["task_step"]
    if approval is not None:
        updated_approval = store.update_approval_task_step_optional(
            approval_id=UUID(approval["id"]),
            task_step_id=UUID(task_step["id"]),
        )
        if updated_approval is None:
            raise RuntimeError("approval disappeared while linking it to its originating task step")
        approval = _serialize_approval(updated_approval)

    trace_events: list[tuple[str, dict[str, object]]] = [
        ("approval.request.request", request.as_payload()),
        (
            "approval.request.routing",
            {
                "decision": routing["decision"],
                "tool_id": routing["tool"]["id"],
                "tool_key": routing["tool"]["tool_key"],
                "tool_version": routing["tool"]["version"],
                "routing_trace_id": routing["trace"]["trace_id"],
                "routing_trace_event_count": routing["trace"]["trace_event_count"],
                "reasons": routing["reasons"],
            },
        ),
        (
            "approval.request.persisted" if approval_created else "approval.request.skipped",
            {
                "approval_id": None if approval is None else approval["id"],
                "task_step_id": None if approval is None else approval["task_step_id"],
                "decision": routing["decision"],
                "persisted": approval_created,
            },
        ),
        (
            "approval.request.summary",
            {
                "decision": routing["decision"],
                "persisted": approval_created,
                "approval_id": None if approval is None else approval["id"],
                "task_step_id": None if approval is None else approval["task_step_id"],
            },
        ),
    ]
    trace_events.extend(
        task_lifecycle_trace_events(
            task=task,
            previous_status=None,
            source="approval_request",
        )
    )
    trace_events.extend(
        task_step_lifecycle_trace_events(
            task_step=task_step,
            previous_status=None,
            source="approval_request",
        )
    )
    _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)

    trace_summary: ApprovalRequestTraceSummary = {
        "trace_id": str(trace["id"]),
        "trace_event_count": len(trace_events),
    }
    return {
        "request": routing["request"],
        "decision": routing["decision"],
        "tool": routing["tool"],
        "reasons": routing["reasons"],
        "task": task,
        "approval": approval,
        "routing_trace": routing["trace"],
        "trace": trace_summary,
    }


def approve_approval_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ApprovalApproveInput,
) -> ApprovalResolutionResponse:
    return _resolve_approval(
        store,
        user_id=user_id,
        approval_id=request.approval_id,
        requested_action="approve",
        resolved_status="approved",
    )


def reject_approval_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ApprovalRejectInput,
) -> ApprovalResolutionResponse:
    return _resolve_approval(
        store,
        user_id=user_id,
        approval_id=request.approval_id,
        requested_action="reject",
        resolved_status="rejected",
    )


def list_approval_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> ApprovalListResponse:
    del user_id

    items = [_serialize_approval(row) for row in store.list_approvals()]
    summary: ApprovalListSummary = {
        "total_count": len(items),
        "order": list(APPROVAL_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_approval_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    approval_id: UUID,
) -> ApprovalDetailResponse:
    del user_id

    approval = store.get_approval_optional(approval_id)
    if approval is None:
        raise ApprovalNotFoundError(f"approval {approval_id} was not found")
    return {"approval": _serialize_approval(approval)}
