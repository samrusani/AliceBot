from __future__ import annotations

from collections.abc import Callable
from typing import cast
from uuid import UUID

from alicebot_api.approvals import ApprovalNotFoundError, serialize_approval_row
from alicebot_api.contracts import (
    PROXY_EXECUTION_VERSION_V0,
    EXECUTION_BUDGET_MATCH_ORDER,
    TRACE_KIND_PROXY_EXECUTE,
    ApprovalRecord,
    ProxyExecutionApprovalTracePayload,
    ProxyExecutionBudgetContextTracePayload,
    ProxyExecutionBudgetPrecheckTracePayload,
    ProxyExecutionDispatchTracePayload,
    ProxyExecutionEventSummary,
    ProxyExecutionRequestEventPayload,
    ProxyExecutionRequestInput,
    ProxyExecutionResponse,
    ProxyExecutionResultEventPayload,
    ProxyExecutionResultRecord,
    ProxyExecutionStatus,
    ProxyExecutionSummaryTracePayload,
    ProxyExecutionTraceSummary,
    ToolRecord,
    ToolExecutionCreateInput,
    ToolExecutionResultRecord,
    ToolRoutingRequestRecord,
)
from alicebot_api.execution_budgets import evaluate_execution_budget
from alicebot_api.store import ContinuityStore, JsonObject, ToolExecutionRow
from alicebot_api.tasks import (
    validate_linked_task_step_for_approval,
    sync_task_step_with_execution,
    sync_task_with_execution,
    task_lifecycle_trace_events,
    task_step_lifecycle_trace_events,
)

PROXY_EXECUTION_REQUEST_EVENT_KIND = "tool.proxy.execution.request"
PROXY_EXECUTION_RESULT_EVENT_KIND = "tool.proxy.execution.result"


class ProxyExecutionApprovalStateError(RuntimeError):
    """Raised when an approval is visible but not executable in its current state."""


class ProxyExecutionHandlerNotFoundError(RuntimeError):
    """Raised when an approved tool has no registered proxy handler."""


ProxyHandler = Callable[[ToolRoutingRequestRecord, ToolRecord], ProxyExecutionResultRecord]


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


def _proxy_echo_handler(
    request: ToolRoutingRequestRecord,
    tool: ToolRecord,
) -> ProxyExecutionResultRecord:
    output: JsonObject = {
        "mode": "no_side_effect",
        "tool_key": tool["tool_key"],
        "action": request["action"],
        "scope": request["scope"],
        "domain_hint": request["domain_hint"],
        "risk_hint": request["risk_hint"],
        "attributes": request["attributes"],
    }
    return {
        "handler_key": "proxy.echo",
        "status": "completed",
        "output": output,
    }


REGISTERED_PROXY_HANDLERS: dict[str, ProxyHandler] = {
    "proxy.echo": _proxy_echo_handler,
}


def registered_proxy_handler_keys() -> tuple[str, ...]:
    return tuple(sorted(REGISTERED_PROXY_HANDLERS))


def _trace_summary(trace_id: UUID, trace_events: list[tuple[str, dict[str, object]]]) -> ProxyExecutionTraceSummary:
    return {
        "trace_id": str(trace_id),
        "trace_event_count": len(trace_events),
    }


def _blocked_state_error(*, approval: ApprovalRecord) -> ProxyExecutionApprovalStateError:
    return ProxyExecutionApprovalStateError(
        f"approval {approval['id']} is {approval['status']} and cannot be executed"
    )


def _missing_handler_error(*, tool: ToolRecord) -> ProxyExecutionHandlerNotFoundError:
    return ProxyExecutionHandlerNotFoundError(
        f"tool '{tool['tool_key']}' has no registered proxy handler"
    )


def _tool_execution_result(
    *,
    handler_key: str | None,
    status: ProxyExecutionStatus,
    output: JsonObject | None,
    reason: str | None,
    budget_decision: dict[str, object] | None = None,
) -> ToolExecutionResultRecord:
    payload: ToolExecutionResultRecord = {
        "handler_key": handler_key,
        "status": status,
        "output": output,
        "reason": reason,
    }
    if budget_decision is not None:
        payload["budget_decision"] = cast(dict[str, object], budget_decision)
    return payload


def _budget_context_trace_payload(
    budget_decision: ProxyExecutionBudgetPrecheckTracePayload,
) -> ProxyExecutionBudgetContextTracePayload | None:
    if budget_decision["reason"] != "invalid_request_context":
        return None
    return {
        "request_thread_id": cast(str | None, budget_decision.get("request_thread_id")),
        "context_resolution": "invalid",
        "context_reason": cast(str | None, budget_decision.get("context_reason")),
    }


def _persist_tool_execution(
    store: ContinuityStore,
    *,
    approval_row: dict[str, object],
    task_step_id: UUID,
    trace_id: UUID,
    handler_key: str | None,
    request: ToolRoutingRequestRecord,
    tool: ToolRecord,
    result: ToolExecutionResultRecord,
    request_event_id: UUID | None,
    result_event_id: UUID | None,
) -> ToolExecutionRow:
    execution = ToolExecutionCreateInput(
        approval_id=cast(UUID, approval_row["id"]),
        task_step_id=task_step_id,
        thread_id=cast(UUID, approval_row["thread_id"]),
        tool_id=cast(UUID, approval_row["tool_id"]),
        trace_id=trace_id,
        request_event_id=request_event_id,
        result_event_id=result_event_id,
        status=result["status"],
        handler_key=handler_key,
        request=request,
        tool=tool,
        result=result,
    )
    return store.create_tool_execution(
        approval_id=execution.approval_id,
        task_step_id=execution.task_step_id,
        thread_id=execution.thread_id,
        tool_id=execution.tool_id,
        trace_id=execution.trace_id,
        request_event_id=execution.request_event_id,
        result_event_id=execution.result_event_id,
        status=execution.status,
        handler_key=execution.handler_key,
        request=cast(JsonObject, execution.request),
        tool=cast(JsonObject, execution.tool),
        result=cast(JsonObject, execution.result),
    )


def execute_approved_proxy_request(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ProxyExecutionRequestInput,
) -> ProxyExecutionResponse:
    del user_id

    approval_row = store.get_approval_optional(request.approval_id)
    if approval_row is None:
        raise ApprovalNotFoundError(f"approval {request.approval_id} was not found")
    _, linked_task_step = validate_linked_task_step_for_approval(
        store,
        approval_id=request.approval_id,
        task_step_id=cast(UUID | None, approval_row["task_step_id"]),
    )

    approval = serialize_approval_row(approval_row)
    linked_task_step_id = cast(str, approval["task_step_id"])
    tool = cast(ToolRecord, approval["tool"])
    routed_request = cast(ToolRoutingRequestRecord, approval["request"])
    handler = REGISTERED_PROXY_HANDLERS.get(tool["tool_key"])

    trace = store.create_trace(
        user_id=approval_row["user_id"],
        thread_id=approval_row["thread_id"],
        kind=TRACE_KIND_PROXY_EXECUTE,
        compiler_version=PROXY_EXECUTION_VERSION_V0,
        status="completed",
        limits={
            "approval_status": approval["status"],
            "enabled_handler_keys": list(registered_proxy_handler_keys()),
            "budget_match_order": list(EXECUTION_BUDGET_MATCH_ORDER),
        },
    )

    approval_trace_payload: ProxyExecutionApprovalTracePayload = {
        "approval_id": approval["id"],
        "task_step_id": linked_task_step_id,
        "approval_status": approval["status"],
        "eligible_for_execution": approval["status"] == "approved",
    }

    trace_events: list[tuple[str, dict[str, object]]] = [
        (
            "tool.proxy.execute.request",
            {
                "approval_id": approval["id"],
                "task_step_id": linked_task_step_id,
            },
        ),
        ("tool.proxy.execute.approval", cast(dict[str, object], approval_trace_payload)),
    ]

    if approval["status"] != "approved":
        error = _blocked_state_error(approval=approval)
        dispatch_payload: ProxyExecutionDispatchTracePayload = {
            "approval_id": approval["id"],
            "task_step_id": linked_task_step_id,
            "tool_id": tool["id"],
            "tool_key": tool["tool_key"],
            "handler_key": None,
            "dispatch_status": "blocked",
            "reason": str(error),
            "result_status": None,
            "output": None,
        }
        summary_payload: ProxyExecutionSummaryTracePayload = {
            "approval_id": approval["id"],
            "task_step_id": linked_task_step_id,
            "tool_id": tool["id"],
            "tool_key": tool["tool_key"],
            "approval_status": approval["status"],
            "execution_status": "blocked",
            "handler_key": None,
            "request_event_id": None,
            "result_event_id": None,
        }
        trace_events.extend(
            [
                ("tool.proxy.execute.dispatch", cast(dict[str, object], dispatch_payload)),
                ("tool.proxy.execute.summary", cast(dict[str, object], summary_payload)),
            ]
        )
        _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)
        raise error

    budget_decision = evaluate_execution_budget(
        store,
        tool=tool,
        request=routed_request,
    )
    budget_trace_payload: ProxyExecutionBudgetPrecheckTracePayload = budget_decision.record
    trace_events.append(
        ("tool.proxy.execute.budget", cast(dict[str, object], budget_trace_payload))
    )

    if budget_decision.blocked_result is not None:
        dispatch_payload: ProxyExecutionDispatchTracePayload = {
            "approval_id": approval["id"],
            "task_step_id": linked_task_step_id,
            "tool_id": tool["id"],
            "tool_key": tool["tool_key"],
            "handler_key": None,
            "dispatch_status": "blocked",
            "reason": budget_decision.blocked_result["reason"],
            "result_status": budget_decision.blocked_result["status"],
            "output": budget_decision.blocked_result["output"],
        }
        budget_context = _budget_context_trace_payload(budget_trace_payload)
        if budget_context is not None:
            dispatch_payload["budget_context"] = budget_context
        summary_payload: ProxyExecutionSummaryTracePayload = {
            "approval_id": approval["id"],
            "task_step_id": linked_task_step_id,
            "tool_id": tool["id"],
            "tool_key": tool["tool_key"],
            "approval_status": approval["status"],
            "execution_status": "blocked",
            "handler_key": None,
            "request_event_id": None,
            "result_event_id": None,
        }
        trace_events.extend(
            [
                ("tool.proxy.execute.dispatch", cast(dict[str, object], dispatch_payload)),
                ("tool.proxy.execute.summary", cast(dict[str, object], summary_payload)),
            ]
        )
        execution = _persist_tool_execution(
            store,
            approval_row=cast(dict[str, object], approval_row),
            task_step_id=cast(UUID, linked_task_step["id"]),
            trace_id=trace["id"],
            handler_key=None,
            request=routed_request,
            tool=tool,
            result=budget_decision.blocked_result,
            request_event_id=None,
            result_event_id=None,
        )
        task_transition = sync_task_with_execution(
            store,
            approval_id=cast(UUID, approval_row["id"]),
            execution_id=execution["id"],
            execution_status=execution["status"],
        )
        task_step_transition = sync_task_step_with_execution(
            store,
            task_id=UUID(task_transition.task["id"]),
            execution=execution,
            trace_id=trace["id"],
            trace_kind=TRACE_KIND_PROXY_EXECUTE,
        )
        trace_events.extend(
            task_lifecycle_trace_events(
                task=task_transition.task,
                previous_status=task_transition.previous_status,
                source="proxy_execution",
            )
        )
        trace_events.extend(
            task_step_lifecycle_trace_events(
                task_step=task_step_transition.task_step,
                previous_status=task_step_transition.previous_status,
                source="proxy_execution",
            )
        )
        _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)
        return {
            "request": {
                "approval_id": approval["id"],
                "task_step_id": linked_task_step_id,
            },
            "approval": approval,
            "tool": tool,
            "result": budget_decision.blocked_result,
            "events": None,
            "trace": _trace_summary(trace["id"], trace_events),
        }

    if handler is None:
        error = _missing_handler_error(tool=tool)
        result = _tool_execution_result(
            handler_key=None,
            status="blocked",
            output=None,
            reason=str(error),
        )
        dispatch_payload: ProxyExecutionDispatchTracePayload = {
            "approval_id": approval["id"],
            "task_step_id": linked_task_step_id,
            "tool_id": tool["id"],
            "tool_key": tool["tool_key"],
            "handler_key": None,
            "dispatch_status": "blocked",
            "reason": str(error),
            "result_status": result["status"],
            "output": None,
        }
        summary_payload: ProxyExecutionSummaryTracePayload = {
            "approval_id": approval["id"],
            "task_step_id": linked_task_step_id,
            "tool_id": tool["id"],
            "tool_key": tool["tool_key"],
            "approval_status": approval["status"],
            "execution_status": "blocked",
            "handler_key": None,
            "request_event_id": None,
            "result_event_id": None,
        }
        trace_events.extend(
            [
                ("tool.proxy.execute.dispatch", cast(dict[str, object], dispatch_payload)),
                ("tool.proxy.execute.summary", cast(dict[str, object], summary_payload)),
            ]
        )
        execution = _persist_tool_execution(
            store,
            approval_row=cast(dict[str, object], approval_row),
            task_step_id=cast(UUID, linked_task_step["id"]),
            trace_id=trace["id"],
            handler_key=None,
            request=routed_request,
            tool=tool,
            result=result,
            request_event_id=None,
            result_event_id=None,
        )
        task_transition = sync_task_with_execution(
            store,
            approval_id=cast(UUID, approval_row["id"]),
            execution_id=execution["id"],
            execution_status=execution["status"],
        )
        task_step_transition = sync_task_step_with_execution(
            store,
            task_id=UUID(task_transition.task["id"]),
            execution=execution,
            trace_id=trace["id"],
            trace_kind=TRACE_KIND_PROXY_EXECUTE,
        )
        trace_events.extend(
            task_lifecycle_trace_events(
                task=task_transition.task,
                previous_status=task_transition.previous_status,
                source="proxy_execution",
            )
        )
        trace_events.extend(
            task_step_lifecycle_trace_events(
                task_step=task_step_transition.task_step,
                previous_status=task_step_transition.previous_status,
                source="proxy_execution",
            )
        )
        _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)
        raise error

    request_event_payload: ProxyExecutionRequestEventPayload = {
        "approval_id": approval["id"],
        "task_step_id": linked_task_step_id,
        "tool_id": tool["id"],
        "tool_key": tool["tool_key"],
        "request": routed_request,
    }
    request_event = store.append_event(
        approval_row["thread_id"],
        None,
        PROXY_EXECUTION_REQUEST_EVENT_KIND,
        cast(JsonObject, request_event_payload),
    )

    result = handler(routed_request, tool)
    result_event_payload: ProxyExecutionResultEventPayload = {
        "approval_id": approval["id"],
        "task_step_id": linked_task_step_id,
        "tool_id": tool["id"],
        "tool_key": tool["tool_key"],
        "handler_key": result["handler_key"],
        "status": result["status"],
        "output": result["output"],
    }
    result_event = store.append_event(
        approval_row["thread_id"],
        None,
        PROXY_EXECUTION_RESULT_EVENT_KIND,
        cast(JsonObject, result_event_payload),
    )
    execution = _persist_tool_execution(
        store,
        approval_row=cast(dict[str, object], approval_row),
        task_step_id=cast(UUID, linked_task_step["id"]),
        trace_id=trace["id"],
        handler_key=result["handler_key"],
        request=routed_request,
        tool=tool,
        result=_tool_execution_result(
            handler_key=result["handler_key"],
            status=result["status"],
            output=result["output"],
            reason=None,
        ),
        request_event_id=request_event["id"],
        result_event_id=result_event["id"],
    )

    events: ProxyExecutionEventSummary = {
        "request_event_id": str(request_event["id"]),
        "request_sequence_no": request_event["sequence_no"],
        "result_event_id": str(result_event["id"]),
        "result_sequence_no": result_event["sequence_no"],
    }
    dispatch_payload: ProxyExecutionDispatchTracePayload = {
        "approval_id": approval["id"],
        "task_step_id": linked_task_step_id,
        "tool_id": tool["id"],
        "tool_key": tool["tool_key"],
        "handler_key": result["handler_key"],
        "dispatch_status": "executed",
        "reason": None,
        "result_status": result["status"],
        "output": result["output"],
    }
    summary_payload: ProxyExecutionSummaryTracePayload = {
        "approval_id": approval["id"],
        "task_step_id": linked_task_step_id,
        "tool_id": tool["id"],
        "tool_key": tool["tool_key"],
        "approval_status": approval["status"],
        "execution_status": "completed",
        "handler_key": result["handler_key"],
        "request_event_id": events["request_event_id"],
        "result_event_id": events["result_event_id"],
    }
    trace_events.extend(
        [
            ("tool.proxy.execute.dispatch", cast(dict[str, object], dispatch_payload)),
            ("tool.proxy.execute.summary", cast(dict[str, object], summary_payload)),
        ]
    )
    task_transition = sync_task_with_execution(
        store,
        approval_id=cast(UUID, approval_row["id"]),
        execution_id=execution["id"],
        execution_status=execution["status"],
    )
    task_step_transition = sync_task_step_with_execution(
        store,
        task_id=UUID(task_transition.task["id"]),
        execution=execution,
        trace_id=trace["id"],
        trace_kind=TRACE_KIND_PROXY_EXECUTE,
    )
    trace_events.extend(
        task_lifecycle_trace_events(
            task=task_transition.task,
            previous_status=task_transition.previous_status,
            source="proxy_execution",
        )
    )
    trace_events.extend(
        task_step_lifecycle_trace_events(
            task_step=task_step_transition.task_step,
            previous_status=task_step_transition.previous_status,
            source="proxy_execution",
        )
    )
    _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)

    return {
        "request": {
            "approval_id": approval["id"],
            "task_step_id": linked_task_step_id,
        },
        "approval": approval,
        "tool": tool,
        "result": result,
        "events": events,
        "trace": _trace_summary(trace["id"], trace_events),
    }
