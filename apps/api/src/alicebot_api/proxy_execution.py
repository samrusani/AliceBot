from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
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
    ProxyExecutionRequestRecord,
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
from alicebot_api.store import ContinuityStore, JsonObject, TaskRunRow, ToolExecutionRow
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


class ProxyExecutionIdempotencyError(RuntimeError):
    """Raised when a side-effect-capable execution request cannot satisfy idempotency guards."""


ProxyHandler = Callable[[ToolRoutingRequestRecord, ToolRecord], ProxyExecutionResultRecord]


@dataclass(frozen=True, slots=True)
class ProxyHandlerSpec:
    handler: ProxyHandler
    side_effect_capable: bool
    rollout_mode: str


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


def _proxy_thread_audit_handler(
    request: ToolRoutingRequestRecord,
    tool: ToolRecord,
) -> ProxyExecutionResultRecord:
    attributes = request["attributes"]
    output: JsonObject = {
        "mode": "internal_low_risk",
        "tool_key": tool["tool_key"],
        "summary": {
            "attribute_count": len(attributes),
            "attribute_keys": sorted(attributes.keys()),
            "action": request["action"],
            "scope": request["scope"],
        },
    }
    return {
        "handler_key": "proxy.thread_audit",
        "status": "completed",
        "output": output,
    }


def _proxy_calendar_draft_handler(
    request: ToolRoutingRequestRecord,
    tool: ToolRecord,
) -> ProxyExecutionResultRecord:
    title = cast(str, request["attributes"].get("title", "Untitled draft event"))
    output: JsonObject = {
        "mode": "external_draft",
        "tool_key": tool["tool_key"],
        "provider": "google_calendar",
        "draft": {
            "title": title,
            "scope": request["scope"],
            "domain_hint": request["domain_hint"],
            "risk_hint": request["risk_hint"],
            "attributes": request["attributes"],
        },
    }
    return {
        "handler_key": "proxy.calendar.draft_event",
        "status": "completed",
        "output": output,
    }


REGISTERED_PROXY_HANDLERS: dict[str, ProxyHandlerSpec] = {
    "proxy.echo": ProxyHandlerSpec(
        handler=_proxy_echo_handler,
        side_effect_capable=False,
        rollout_mode="internal",
    ),
    "proxy.thread_audit": ProxyHandlerSpec(
        handler=_proxy_thread_audit_handler,
        side_effect_capable=False,
        rollout_mode="internal",
    ),
    "proxy.calendar.draft_event": ProxyHandlerSpec(
        handler=_proxy_calendar_draft_handler,
        side_effect_capable=True,
        rollout_mode="external_draft",
    ),
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


def _build_idempotency_key(
    *,
    task_run_id: UUID,
    approval_id: UUID,
    request: ToolRoutingRequestRecord,
    tool: ToolRecord,
) -> str:
    canonical_payload = {
        "task_run_id": str(task_run_id),
        "approval_id": str(approval_id),
        "tool_key": tool["tool_key"],
        "action": request["action"],
        "scope": request["scope"],
        "domain_hint": request["domain_hint"],
        "risk_hint": request["risk_hint"],
        "attributes": request["attributes"],
    }
    canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_task_run_linkage(
    store: ContinuityStore,
    *,
    approval_row: dict[str, object],
    linked_task_step: dict[str, object],
    requested_task_run_id: UUID | None,
) -> UUID | None:
    approval_task_run_id = cast(UUID | None, approval_row.get("task_run_id"))
    linked_task_run_id = requested_task_run_id or approval_task_run_id
    if linked_task_run_id is None:
        return None

    if not hasattr(store, "get_task_run_optional"):
        return linked_task_run_id
    task_run = store.get_task_run_optional(linked_task_run_id)
    if task_run is None:
        raise ProxyExecutionApprovalStateError(
            f"approval {approval_row['id']} links task run {linked_task_run_id} that was not found"
        )
    if task_run["task_id"] != linked_task_step["task_id"]:
        raise ProxyExecutionApprovalStateError(
            f"approval {approval_row['id']} links task run {linked_task_run_id} outside task {linked_task_step['task_id']}"
        )
    if approval_task_run_id is not None and approval_task_run_id != linked_task_run_id:
        raise ProxyExecutionApprovalStateError(
            f"approval {approval_row['id']} is already linked to task run {approval_task_run_id}"
        )

    if approval_task_run_id is None and hasattr(store, "update_approval_task_run_optional"):
        store.update_approval_task_run_optional(
            approval_id=cast(UUID, approval_row["id"]),
            task_run_id=linked_task_run_id,
        )

    return linked_task_run_id


def _sync_task_run_after_execution(
    store: ContinuityStore,
    *,
    task_run_id: UUID,
    approval_id: UUID,
    execution: ToolExecutionRow,
) -> TaskRunRow | None:
    task_run = store.get_task_run_optional(task_run_id)
    if task_run is None:
        return None
    if cast(str, task_run["status"]) in {"done", "cancelled"}:
        return task_run

    checkpoint = cast(JsonObject, task_run["checkpoint"])
    if not isinstance(checkpoint, dict):
        checkpoint = {}
    next_checkpoint = dict(checkpoint)
    next_checkpoint["wait_for_signal"] = False
    next_checkpoint["waiting_approval_id"] = None
    next_checkpoint["resolved_approval_id"] = str(approval_id)
    next_checkpoint["resumed_from_approval_id"] = str(approval_id)
    next_checkpoint["last_execution_id"] = str(execution["id"])
    next_checkpoint["last_execution_status"] = cast(str, execution["status"])
    next_checkpoint["last_execution_at"] = execution["executed_at"].isoformat()

    execution_status = cast(str, execution["status"])
    next_status = "done"
    next_stop_reason = "done"
    next_failure_class = None
    next_retry_posture = "terminal"
    if execution_status == "blocked":
        next_status = "failed"
        next_stop_reason = "policy_blocked"
        next_failure_class = "policy"
        next_retry_posture = "terminal"
        execution_result = cast(dict[str, object], execution.get("result", {}))
        budget_decision = execution_result.get("budget_decision")
        if isinstance(budget_decision, dict) and budget_decision.get("reason") == "budget_exceeded":
            next_stop_reason = "budget_exhausted"
            next_failure_class = "budget"

    transitions = next_checkpoint.get("transitions")
    if isinstance(transitions, list):
        history = [entry for entry in transitions if isinstance(entry, dict)]
    else:
        history = []
    transition_entry = {
        "sequence_no": len(history) + 1,
        "source": "proxy_execution",
        "at": datetime.now(UTC).isoformat(),
        "previous_status": cast(str, task_run["status"]),
        "status": next_status,
        "previous_stop_reason": cast(str | None, task_run["stop_reason"]),
        "stop_reason": next_stop_reason,
        "failure_class": next_failure_class,
        "retry_count": int(task_run["retry_count"]),
        "retry_cap": int(task_run["retry_cap"]),
        "retry_posture": next_retry_posture,
    }
    history.append(transition_entry)
    next_checkpoint["transitions"] = history
    next_checkpoint["last_transition"] = transition_entry

    return store.update_task_run_optional(
        task_run_id=task_run_id,
        status=next_status,
        checkpoint=next_checkpoint,
        tick_count=max(1, int(task_run["tick_count"])),
        step_count=max(int(task_run["step_count"]), 1),
        retry_count=int(task_run["retry_count"]),
        retry_cap=int(task_run["retry_cap"]),
        retry_posture=next_retry_posture,
        failure_class=next_failure_class,
        stop_reason=next_stop_reason,
    )


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


def _task_run_trace_payload(task_run: TaskRunRow) -> dict[str, object]:
    return {
        "task_run_id": str(task_run["id"]),
        "status": cast(str, task_run["status"]),
        "stop_reason": cast(str | None, task_run["stop_reason"]),
        "failure_class": cast(str | None, task_run["failure_class"]),
        "retry_count": int(task_run["retry_count"]),
        "retry_cap": int(task_run["retry_cap"]),
        "retry_posture": cast(str, task_run["retry_posture"]),
    }


def _persist_tool_execution(
    store: ContinuityStore,
    *,
    approval_row: dict[str, object],
    task_run_id: UUID | None,
    task_step_id: UUID,
    trace_id: UUID,
    handler_key: str | None,
    idempotency_key: str | None,
    request: ToolRoutingRequestRecord,
    tool: ToolRecord,
    result: ToolExecutionResultRecord,
    request_event_id: UUID | None,
    result_event_id: UUID | None,
) -> ToolExecutionRow:
    execution = ToolExecutionCreateInput(
        approval_id=cast(UUID, approval_row["id"]),
        task_run_id=task_run_id,
        task_step_id=task_step_id,
        thread_id=cast(UUID, approval_row["thread_id"]),
        tool_id=cast(UUID, approval_row["tool_id"]),
        trace_id=trace_id,
        request_event_id=request_event_id,
        result_event_id=result_event_id,
        status=result["status"],
        handler_key=handler_key,
        idempotency_key=idempotency_key,
        request=request,
        tool=tool,
        result=result,
    )
    try:
        return store.create_tool_execution(
            approval_id=execution.approval_id,
            task_run_id=execution.task_run_id,
            task_step_id=execution.task_step_id,
            thread_id=execution.thread_id,
            tool_id=execution.tool_id,
            trace_id=execution.trace_id,
            request_event_id=execution.request_event_id,
            result_event_id=execution.result_event_id,
            status=execution.status,
            handler_key=execution.handler_key,
            idempotency_key=execution.idempotency_key,
            request=cast(JsonObject, execution.request),
            tool=cast(JsonObject, execution.tool),
            result=cast(JsonObject, execution.result),
        )
    except TypeError:
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
    handler_spec = REGISTERED_PROXY_HANDLERS.get(tool["tool_key"])
    linked_task_run_id = _resolve_task_run_linkage(
        store,
        approval_row=cast(dict[str, object], approval_row),
        linked_task_step=cast(dict[str, object], linked_task_step),
        requested_task_run_id=request.task_run_id,
    )
    approval["task_run_id"] = None if linked_task_run_id is None else str(linked_task_run_id)
    idempotency_key: str | None = None
    if handler_spec is not None and handler_spec.side_effect_capable:
        if linked_task_run_id is None:
            raise ProxyExecutionIdempotencyError(
                f"tool '{tool['tool_key']}' requires a linked task run for idempotent execution"
            )
        idempotency_key = _build_idempotency_key(
            task_run_id=linked_task_run_id,
            approval_id=cast(UUID, approval_row["id"]),
            request=routed_request,
            tool=tool,
        )

    trace = store.create_trace(
        user_id=approval_row["user_id"],
        thread_id=approval_row["thread_id"],
        kind=TRACE_KIND_PROXY_EXECUTE,
        compiler_version=PROXY_EXECUTION_VERSION_V0,
        status="completed",
        limits={
            "approval_status": approval["status"],
            "enabled_handler_keys": [tool["tool_key"]],
            "budget_match_order": list(EXECUTION_BUDGET_MATCH_ORDER),
        },
    )

    approval_trace_payload: ProxyExecutionApprovalTracePayload = {
        "approval_id": approval["id"],
        "task_step_id": linked_task_step_id,
        "approval_status": approval["status"],
        "eligible_for_execution": approval["status"] == "approved",
    }

    request_trace_payload: dict[str, object] = {
        "approval_id": approval["id"],
        "task_step_id": linked_task_step_id,
    }
    if linked_task_run_id is not None:
        request_trace_payload["task_run_id"] = str(linked_task_run_id)

    trace_events: list[tuple[str, dict[str, object]]] = [
        ("tool.proxy.execute.request", request_trace_payload),
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

    if idempotency_key is not None and linked_task_run_id is not None:
        existing_execution = (
            store.get_tool_execution_by_idempotency_optional(
                task_run_id=linked_task_run_id,
                approval_id=cast(UUID, approval_row["id"]),
                idempotency_key=idempotency_key,
            )
            if hasattr(store, "get_tool_execution_by_idempotency_optional")
            else None
        )
        if existing_execution is not None:
            trace_events.append(
                (
                    "tool.proxy.execute.idempotency",
                    {
                        "approval_id": approval["id"],
                        "task_run_id": str(linked_task_run_id),
                        "idempotency_key": idempotency_key,
                        "replayed_execution_id": str(existing_execution["id"]),
                        "decision": "replay_existing",
                    },
                )
            )
            run_after_sync = _sync_task_run_after_execution(
                store,
                task_run_id=linked_task_run_id,
                approval_id=cast(UUID, approval_row["id"]),
                execution=existing_execution,
            )
            if run_after_sync is not None:
                trace_events.append(
                    (
                        "tool.proxy.execute.run",
                        _task_run_trace_payload(run_after_sync),
                    )
                )
            _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)
            return {
                "request": cast(
                    ProxyExecutionRequestRecord,
                    {
                        "approval_id": approval["id"],
                        "task_step_id": linked_task_step_id,
                        "task_run_id": str(linked_task_run_id),
                    },
                ),
                "approval": approval,
                "tool": tool,
                "result": cast(ToolExecutionResultRecord, existing_execution["result"]),
                "events": None,
                "trace": _trace_summary(trace["id"], trace_events),
            }

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
            task_run_id=linked_task_run_id,
            task_step_id=cast(UUID, linked_task_step["id"]),
            trace_id=trace["id"],
            handler_key=None,
            idempotency_key=idempotency_key,
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
        if linked_task_run_id is not None:
            run_after_sync = _sync_task_run_after_execution(
                store,
                task_run_id=linked_task_run_id,
                approval_id=cast(UUID, approval_row["id"]),
                execution=execution,
            )
            if run_after_sync is not None:
                trace_events.append(
                    (
                        "tool.proxy.execute.run",
                        _task_run_trace_payload(run_after_sync),
                    )
                )
        _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)
        return {
            "request": cast(
                ProxyExecutionRequestRecord,
                {
                    "approval_id": approval["id"],
                    "task_step_id": linked_task_step_id,
                    **(
                        {"task_run_id": str(linked_task_run_id)}
                        if linked_task_run_id is not None
                        else {}
                    ),
                },
            ),
            "approval": approval,
            "tool": tool,
            "result": budget_decision.blocked_result,
            "events": None,
            "trace": _trace_summary(trace["id"], trace_events),
        }

    if handler_spec is None:
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
            task_run_id=linked_task_run_id,
            task_step_id=cast(UUID, linked_task_step["id"]),
            trace_id=trace["id"],
            handler_key=None,
            idempotency_key=idempotency_key,
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
        if linked_task_run_id is not None:
            run_after_sync = _sync_task_run_after_execution(
                store,
                task_run_id=linked_task_run_id,
                approval_id=cast(UUID, approval_row["id"]),
                execution=execution,
            )
            if run_after_sync is not None:
                trace_events.append(
                    (
                        "tool.proxy.execute.run",
                        _task_run_trace_payload(run_after_sync),
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
    if linked_task_run_id is not None:
        request_event_payload["task_run_id"] = str(linked_task_run_id)
    request_event = store.append_event(
        approval_row["thread_id"],
        None,
        PROXY_EXECUTION_REQUEST_EVENT_KIND,
        cast(JsonObject, request_event_payload),
    )

    result = handler_spec.handler(routed_request, tool)
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
        task_run_id=linked_task_run_id,
        task_step_id=cast(UUID, linked_task_step["id"]),
        trace_id=trace["id"],
        handler_key=result["handler_key"],
        idempotency_key=idempotency_key,
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
    if linked_task_run_id is not None:
        run_after_sync = _sync_task_run_after_execution(
            store,
            task_run_id=linked_task_run_id,
            approval_id=cast(UUID, approval_row["id"]),
            execution=execution,
        )
        if run_after_sync is not None:
            trace_events.append(
                (
                    "tool.proxy.execute.run",
                    _task_run_trace_payload(run_after_sync),
                )
            )
    _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)

    return {
        "request": cast(
            ProxyExecutionRequestRecord,
            {
                "approval_id": approval["id"],
                "task_step_id": linked_task_step_id,
                **({"task_run_id": str(linked_task_run_id)} if linked_task_run_id is not None else {}),
            },
        ),
        "approval": approval,
        "tool": tool,
        "result": result,
        "events": events,
        "trace": _trace_summary(trace["id"], trace_events),
    }
