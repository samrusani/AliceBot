from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import psycopg

from alicebot_api.contracts import (
    DEFAULT_AGENT_PROFILE_ID,
    EXECUTION_BUDGET_LIFECYCLE_VERSION_V0,
    EXECUTION_BUDGET_LIST_ORDER,
    EXECUTION_BUDGET_MATCH_ORDER,
    EXECUTION_BUDGET_STATUSES,
    TOOL_EXECUTION_LIST_ORDER,
    TRACE_KIND_EXECUTION_BUDGET_LIFECYCLE,
    ExecutionBudgetCreateInput,
    ExecutionBudgetCreateResponse,
    ExecutionBudgetDeactivateInput,
    ExecutionBudgetDeactivateResponse,
    ExecutionBudgetDecisionRecord,
    ExecutionBudgetDetailResponse,
    ExecutionBudgetLifecycleAction,
    ExecutionBudgetLifecycleOutcome,
    ExecutionBudgetLifecycleRequestTracePayload,
    ExecutionBudgetLifecycleStateTracePayload,
    ExecutionBudgetLifecycleSummaryTracePayload,
    ExecutionBudgetListResponse,
    ExecutionBudgetListSummary,
    ExecutionBudgetRecord,
    ExecutionBudgetSupersedeInput,
    ExecutionBudgetSupersedeResponse,
    ToolExecutionResultRecord,
    ToolRecord,
    ToolRoutingRequestRecord,
)
from alicebot_api.store import ContinuityStore, ExecutionBudgetRow, ToolExecutionRow


class ExecutionBudgetValidationError(ValueError):
    """Raised when an execution-budget request fails explicit validation."""


class ExecutionBudgetNotFoundError(LookupError):
    """Raised when an execution budget is not visible inside the current user scope."""


class ExecutionBudgetLifecycleError(RuntimeError):
    """Raised when an execution budget lifecycle transition is invalid."""


@dataclass(frozen=True, slots=True)
class ExecutionBudgetDecision:
    record: ExecutionBudgetDecisionRecord
    blocked_result: ToolExecutionResultRecord | None


@dataclass(frozen=True, slots=True)
class _RequestContextResolution:
    request_thread_id: str | None
    active_thread_profile_id: str | None
    context_resolution: str
    context_reason: str | None


def serialize_execution_budget_row(row: ExecutionBudgetRow) -> ExecutionBudgetRecord:
    return {
        "id": str(row["id"]),
        "agent_profile_id": cast(str | None, row["agent_profile_id"]),
        "tool_key": row["tool_key"],
        "domain_hint": row["domain_hint"],
        "max_completed_executions": row["max_completed_executions"],
        "rolling_window_seconds": row["rolling_window_seconds"],
        "status": cast(str, row["status"]),
        "deactivated_at": None if row["deactivated_at"] is None else row["deactivated_at"].isoformat(),
        "superseded_by_budget_id": (
            None if row["superseded_by_budget_id"] is None else str(row["superseded_by_budget_id"])
        ),
        "supersedes_budget_id": (
            None if row["supersedes_budget_id"] is None else str(row["supersedes_budget_id"])
        ),
        "created_at": row["created_at"].isoformat(),
    }


def _validate_budget_scope(*, tool_key: str | None, domain_hint: str | None) -> None:
    if tool_key is None and domain_hint is None:
        raise ExecutionBudgetValidationError(
            "execution budget requires at least one selector: tool_key or domain_hint"
        )


def _validate_rolling_window_seconds(rolling_window_seconds: int | None) -> None:
    if rolling_window_seconds is not None and rolling_window_seconds <= 0:
        raise ExecutionBudgetValidationError(
            "rolling_window_seconds must be greater than 0 when provided"
        )


def _validate_agent_profile_id(
    store: ContinuityStore,
    *,
    agent_profile_id: str | None,
) -> None:
    if agent_profile_id is None:
        return
    if store.get_agent_profile_optional(agent_profile_id) is None:
        raise ExecutionBudgetValidationError(
            "agent_profile_id must reference an existing profile in the registry"
        )


def _validate_lifecycle_thread(store: ContinuityStore, *, thread_id: UUID) -> dict[str, object]:
    thread = store.get_thread_optional(thread_id)
    if thread is None:
        raise ExecutionBudgetValidationError(
            "thread_id must reference an existing thread owned by the user"
        )
    return cast(dict[str, object], thread)


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


def _trace_summary(trace_id: UUID, trace_events: list[tuple[str, dict[str, object]]]) -> dict[str, object]:
    return {
        "trace_id": str(trace_id),
        "trace_event_count": len(trace_events),
    }


def _active_budget_rows_for_scope(
    store: ContinuityStore,
    *,
    agent_profile_id: str | None,
    tool_key: str | None,
    domain_hint: str | None,
) -> list[ExecutionBudgetRow]:
    rows = [
        row
        for row in store.list_execution_budgets()
        if cast(str | None, row["agent_profile_id"]) == agent_profile_id
        and row["tool_key"] == tool_key
        and row["domain_hint"] == domain_hint
        and cast(str, row["status"]) == "active"
    ]
    return sorted(rows, key=lambda row: (row["created_at"], row["id"]))


def _scope_label(
    *,
    agent_profile_id: str | None,
    tool_key: str | None,
    domain_hint: str | None,
) -> str:
    return (
        f"agent_profile_id={agent_profile_id!r}, "
        f"tool_key={tool_key!r}, "
        f"domain_hint={domain_hint!r}"
    )


def _duplicate_active_scope_message(
    *,
    agent_profile_id: str | None,
    tool_key: str | None,
    domain_hint: str | None,
) -> str:
    return (
        "active execution budget already exists for selector scope "
        f"{_scope_label(agent_profile_id=agent_profile_id, tool_key=tool_key, domain_hint=domain_hint)}"
    )


def _is_active_scope_uniqueness_error(exc: psycopg.Error) -> bool:
    diag = getattr(exc, "diag", None)
    return getattr(diag, "constraint_name", None) == "execution_budgets_one_active_scope_idx"


def _invalid_transition_error(
    *,
    row: ExecutionBudgetRow,
    requested_action: ExecutionBudgetLifecycleAction,
) -> ExecutionBudgetLifecycleError:
    return ExecutionBudgetLifecycleError(
        f"execution budget {row['id']} is {row['status']} and cannot be {requested_action}d"
    )


def _record_lifecycle_trace(
    store: ContinuityStore,
    *,
    thread: dict[str, object],
    request_payload: ExecutionBudgetLifecycleRequestTracePayload,
    state_payload: ExecutionBudgetLifecycleStateTracePayload,
    summary_payload: ExecutionBudgetLifecycleSummaryTracePayload,
    requested_action: ExecutionBudgetLifecycleAction,
    outcome: ExecutionBudgetLifecycleOutcome,
) -> dict[str, object]:
    trace = store.create_trace(
        user_id=cast(UUID, thread["user_id"]),
        thread_id=cast(UUID, thread["id"]),
        kind=TRACE_KIND_EXECUTION_BUDGET_LIFECYCLE,
        compiler_version=EXECUTION_BUDGET_LIFECYCLE_VERSION_V0,
        status="completed",
        limits={
            "order": list(EXECUTION_BUDGET_LIST_ORDER),
            "match_order": list(EXECUTION_BUDGET_MATCH_ORDER),
            "statuses": list(EXECUTION_BUDGET_STATUSES),
            "requested_action": requested_action,
            "outcome": outcome,
        },
    )
    trace_events: list[tuple[str, dict[str, object]]] = [
        ("execution_budget.lifecycle.request", cast(dict[str, object], request_payload)),
        ("execution_budget.lifecycle.state", cast(dict[str, object], state_payload)),
        ("execution_budget.lifecycle.summary", cast(dict[str, object], summary_payload)),
    ]
    _append_trace_events(store, trace_id=trace["id"], trace_events=trace_events)
    return _trace_summary(trace["id"], trace_events)


def create_execution_budget_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ExecutionBudgetCreateInput,
) -> ExecutionBudgetCreateResponse:
    del user_id

    _validate_budget_scope(tool_key=request.tool_key, domain_hint=request.domain_hint)
    _validate_rolling_window_seconds(request.rolling_window_seconds)
    _validate_agent_profile_id(store, agent_profile_id=request.agent_profile_id)
    if _active_budget_rows_for_scope(
        store,
        agent_profile_id=request.agent_profile_id,
        tool_key=request.tool_key,
        domain_hint=request.domain_hint,
    ):
        raise ExecutionBudgetValidationError(
            _duplicate_active_scope_message(
                agent_profile_id=request.agent_profile_id,
                tool_key=request.tool_key,
                domain_hint=request.domain_hint,
            )
        )
    try:
        row = store.create_execution_budget(
            agent_profile_id=request.agent_profile_id,
            tool_key=request.tool_key,
            domain_hint=request.domain_hint,
            max_completed_executions=request.max_completed_executions,
            rolling_window_seconds=request.rolling_window_seconds,
        )
    except psycopg.IntegrityError as exc:
        if _is_active_scope_uniqueness_error(exc):
            raise ExecutionBudgetValidationError(
                _duplicate_active_scope_message(
                    agent_profile_id=request.agent_profile_id,
                    tool_key=request.tool_key,
                    domain_hint=request.domain_hint,
                )
            ) from exc
        raise
    return {"execution_budget": serialize_execution_budget_row(row)}


def list_execution_budget_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> ExecutionBudgetListResponse:
    del user_id

    items = [serialize_execution_budget_row(row) for row in store.list_execution_budgets()]
    summary: ExecutionBudgetListSummary = {
        "total_count": len(items),
        "order": list(EXECUTION_BUDGET_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_execution_budget_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    execution_budget_id: UUID,
) -> ExecutionBudgetDetailResponse:
    del user_id

    row = store.get_execution_budget_optional(execution_budget_id)
    if row is None:
        raise ExecutionBudgetNotFoundError(f"execution budget {execution_budget_id} was not found")
    return {"execution_budget": serialize_execution_budget_row(row)}


def deactivate_execution_budget_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ExecutionBudgetDeactivateInput,
) -> ExecutionBudgetDeactivateResponse:
    del user_id

    thread = _validate_lifecycle_thread(store, thread_id=request.thread_id)
    row = store.get_execution_budget_optional(request.execution_budget_id)
    if row is None:
        raise ExecutionBudgetNotFoundError(
            f"execution budget {request.execution_budget_id} was not found"
        )

    request_payload: ExecutionBudgetLifecycleRequestTracePayload = {
        "thread_id": str(request.thread_id),
        "execution_budget_id": str(request.execution_budget_id),
        "requested_action": "deactivate",
        "replacement_max_completed_executions": None,
    }

    if cast(str, row["status"]) != "active":
        error = _invalid_transition_error(row=row, requested_action="deactivate")
        trace = _record_lifecycle_trace(
            store,
            thread=thread,
            request_payload=request_payload,
            state_payload={
                "execution_budget_id": str(row["id"]),
                "requested_action": "deactivate",
                "previous_status": cast(str, row["status"]),
                "current_status": cast(str, row["status"]),
                "tool_key": row["tool_key"],
                "domain_hint": row["domain_hint"],
                "max_completed_executions": row["max_completed_executions"],
                "rolling_window_seconds": row["rolling_window_seconds"],
                "deactivated_at": (
                    None if row["deactivated_at"] is None else row["deactivated_at"].isoformat()
                ),
                "superseded_by_budget_id": (
                    None if row["superseded_by_budget_id"] is None else str(row["superseded_by_budget_id"])
                ),
                "supersedes_budget_id": (
                    None if row["supersedes_budget_id"] is None else str(row["supersedes_budget_id"])
                ),
                "replacement_budget_id": None,
                "replacement_status": None,
                "replacement_max_completed_executions": None,
                "replacement_rolling_window_seconds": None,
                "rejection_reason": str(error),
            },
            summary_payload={
                "execution_budget_id": str(row["id"]),
                "requested_action": "deactivate",
                "outcome": "rejected",
                "replacement_budget_id": None,
                "active_budget_id": None,
            },
            requested_action="deactivate",
            outcome="rejected",
        )
        del trace
        raise error

    updated = store.deactivate_execution_budget_optional(request.execution_budget_id)
    if updated is None:
        raise ExecutionBudgetLifecycleError(
            f"execution budget {request.execution_budget_id} could not be deactivated"
        )

    trace = _record_lifecycle_trace(
        store,
        thread=thread,
        request_payload=request_payload,
        state_payload={
            "execution_budget_id": str(updated["id"]),
            "requested_action": "deactivate",
            "previous_status": "active",
            "current_status": cast(str, updated["status"]),
            "tool_key": updated["tool_key"],
            "domain_hint": updated["domain_hint"],
            "max_completed_executions": updated["max_completed_executions"],
            "rolling_window_seconds": updated["rolling_window_seconds"],
            "deactivated_at": (
                None if updated["deactivated_at"] is None else updated["deactivated_at"].isoformat()
            ),
            "superseded_by_budget_id": (
                None if updated["superseded_by_budget_id"] is None else str(updated["superseded_by_budget_id"])
            ),
            "supersedes_budget_id": (
                None if updated["supersedes_budget_id"] is None else str(updated["supersedes_budget_id"])
            ),
            "replacement_budget_id": None,
            "replacement_status": None,
            "replacement_max_completed_executions": None,
            "replacement_rolling_window_seconds": None,
            "rejection_reason": None,
        },
        summary_payload={
            "execution_budget_id": str(updated["id"]),
            "requested_action": "deactivate",
            "outcome": "deactivated",
            "replacement_budget_id": None,
            "active_budget_id": None,
        },
        requested_action="deactivate",
        outcome="deactivated",
    )
    return {
        "execution_budget": serialize_execution_budget_row(updated),
        "trace": cast(dict[str, object], trace),
    }


def supersede_execution_budget_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ExecutionBudgetSupersedeInput,
) -> ExecutionBudgetSupersedeResponse:
    del user_id

    thread = _validate_lifecycle_thread(store, thread_id=request.thread_id)
    current = store.get_execution_budget_optional(request.execution_budget_id)
    if current is None:
        raise ExecutionBudgetNotFoundError(
            f"execution budget {request.execution_budget_id} was not found"
        )

    request_payload: ExecutionBudgetLifecycleRequestTracePayload = {
        "thread_id": str(request.thread_id),
        "execution_budget_id": str(request.execution_budget_id),
        "requested_action": "supersede",
        "replacement_max_completed_executions": request.max_completed_executions,
    }

    if cast(str, current["status"]) != "active":
        error = _invalid_transition_error(row=current, requested_action="supersede")
        trace = _record_lifecycle_trace(
            store,
            thread=thread,
            request_payload=request_payload,
            state_payload={
                "execution_budget_id": str(current["id"]),
                "requested_action": "supersede",
                "previous_status": cast(str, current["status"]),
                "current_status": cast(str, current["status"]),
                "tool_key": current["tool_key"],
                "domain_hint": current["domain_hint"],
                "max_completed_executions": current["max_completed_executions"],
                "rolling_window_seconds": current["rolling_window_seconds"],
                "deactivated_at": (
                    None if current["deactivated_at"] is None else current["deactivated_at"].isoformat()
                ),
                "superseded_by_budget_id": (
                    None if current["superseded_by_budget_id"] is None else str(current["superseded_by_budget_id"])
                ),
                "supersedes_budget_id": (
                    None if current["supersedes_budget_id"] is None else str(current["supersedes_budget_id"])
                ),
                "replacement_budget_id": None,
                "replacement_status": None,
                "replacement_max_completed_executions": request.max_completed_executions,
                "replacement_rolling_window_seconds": current["rolling_window_seconds"],
                "rejection_reason": str(error),
            },
            summary_payload={
                "execution_budget_id": str(current["id"]),
                "requested_action": "supersede",
                "outcome": "rejected",
                "replacement_budget_id": None,
                "active_budget_id": str(current["id"]) if cast(str, current["status"]) == "active" else None,
            },
            requested_action="supersede",
            outcome="rejected",
        )
        del trace
        raise error

    active_scope_rows = _active_budget_rows_for_scope(
        store,
        agent_profile_id=cast(str | None, current["agent_profile_id"]),
        tool_key=current["tool_key"],
        domain_hint=current["domain_hint"],
    )
    if [row["id"] for row in active_scope_rows] != [current["id"]]:
        error = ExecutionBudgetLifecycleError(
            "execution budget selector scope must have exactly one active budget to supersede: "
            f"{_scope_label(agent_profile_id=cast(str | None, current['agent_profile_id']), tool_key=current['tool_key'], domain_hint=current['domain_hint'])}"
        )
        trace = _record_lifecycle_trace(
            store,
            thread=thread,
            request_payload=request_payload,
            state_payload={
                "execution_budget_id": str(current["id"]),
                "requested_action": "supersede",
                "previous_status": "active",
                "current_status": "active",
                "tool_key": current["tool_key"],
                "domain_hint": current["domain_hint"],
                "max_completed_executions": current["max_completed_executions"],
                "rolling_window_seconds": current["rolling_window_seconds"],
                "deactivated_at": None,
                "superseded_by_budget_id": None,
                "supersedes_budget_id": (
                    None if current["supersedes_budget_id"] is None else str(current["supersedes_budget_id"])
                ),
                "replacement_budget_id": None,
                "replacement_status": None,
                "replacement_max_completed_executions": request.max_completed_executions,
                "replacement_rolling_window_seconds": current["rolling_window_seconds"],
                "rejection_reason": str(error),
            },
            summary_payload={
                "execution_budget_id": str(current["id"]),
                "requested_action": "supersede",
                "outcome": "rejected",
                "replacement_budget_id": None,
                "active_budget_id": str(current["id"]),
            },
            requested_action="supersede",
            outcome="rejected",
        )
        del trace
        raise error

    replacement_budget_id = uuid4()
    try:
        with store.conn.transaction():
            superseded = store.supersede_execution_budget_optional(
                execution_budget_id=request.execution_budget_id,
                superseded_by_budget_id=replacement_budget_id,
            )
            if superseded is None:
                raise ExecutionBudgetLifecycleError(
                    f"execution budget {request.execution_budget_id} could not be superseded"
                )
            replacement = store.create_execution_budget(
                budget_id=replacement_budget_id,
                agent_profile_id=cast(str | None, current["agent_profile_id"]),
                tool_key=current["tool_key"],
                domain_hint=current["domain_hint"],
                max_completed_executions=request.max_completed_executions,
                rolling_window_seconds=current["rolling_window_seconds"],
                supersedes_budget_id=current["id"],
            )
    except psycopg.IntegrityError as exc:
        if _is_active_scope_uniqueness_error(exc):
            error = ExecutionBudgetLifecycleError(
                _duplicate_active_scope_message(
                    agent_profile_id=cast(str | None, current["agent_profile_id"]),
                    tool_key=current["tool_key"],
                    domain_hint=current["domain_hint"],
                )
            )
        else:
            raise
    except ExecutionBudgetLifecycleError as exc:
        error = exc
    else:
        error = None

    if error is not None:
        current_state = store.get_execution_budget_optional(request.execution_budget_id)
        if current_state is None:
            raise ExecutionBudgetNotFoundError(
                f"execution budget {request.execution_budget_id} was not found"
            )
        trace = _record_lifecycle_trace(
            store,
            thread=thread,
            request_payload=request_payload,
            state_payload={
                "execution_budget_id": str(current_state["id"]),
                "requested_action": "supersede",
                "previous_status": cast(str, current["status"]),
                "current_status": cast(str, current_state["status"]),
                "tool_key": current_state["tool_key"],
                "domain_hint": current_state["domain_hint"],
                "max_completed_executions": current_state["max_completed_executions"],
                "rolling_window_seconds": current_state["rolling_window_seconds"],
                "deactivated_at": (
                    None
                    if current_state["deactivated_at"] is None
                    else current_state["deactivated_at"].isoformat()
                ),
                "superseded_by_budget_id": (
                    None
                    if current_state["superseded_by_budget_id"] is None
                    else str(current_state["superseded_by_budget_id"])
                ),
                "supersedes_budget_id": (
                    None
                    if current_state["supersedes_budget_id"] is None
                    else str(current_state["supersedes_budget_id"])
                ),
                "replacement_budget_id": None,
                "replacement_status": None,
                "replacement_max_completed_executions": request.max_completed_executions,
                "replacement_rolling_window_seconds": current["rolling_window_seconds"],
                "rejection_reason": str(error),
            },
            summary_payload={
                "execution_budget_id": str(current_state["id"]),
                "requested_action": "supersede",
                "outcome": "rejected",
                "replacement_budget_id": None,
                "active_budget_id": (
                    str(current_state["id"])
                    if cast(str, current_state["status"]) == "active"
                    else None
                ),
            },
            requested_action="supersede",
            outcome="rejected",
        )
        del trace
        raise error

    trace = _record_lifecycle_trace(
        store,
        thread=thread,
        request_payload=request_payload,
        state_payload={
            "execution_budget_id": str(superseded["id"]),
            "requested_action": "supersede",
            "previous_status": "active",
            "current_status": cast(str, superseded["status"]),
            "tool_key": superseded["tool_key"],
            "domain_hint": superseded["domain_hint"],
            "max_completed_executions": superseded["max_completed_executions"],
            "rolling_window_seconds": superseded["rolling_window_seconds"],
            "deactivated_at": (
                None if superseded["deactivated_at"] is None else superseded["deactivated_at"].isoformat()
            ),
            "superseded_by_budget_id": (
                None if superseded["superseded_by_budget_id"] is None else str(superseded["superseded_by_budget_id"])
            ),
            "supersedes_budget_id": (
                None if superseded["supersedes_budget_id"] is None else str(superseded["supersedes_budget_id"])
            ),
            "replacement_budget_id": str(replacement["id"]),
            "replacement_status": cast(str, replacement["status"]),
            "replacement_max_completed_executions": replacement["max_completed_executions"],
            "replacement_rolling_window_seconds": replacement["rolling_window_seconds"],
            "rejection_reason": None,
        },
        summary_payload={
            "execution_budget_id": str(superseded["id"]),
            "requested_action": "supersede",
            "outcome": "superseded",
            "replacement_budget_id": str(replacement["id"]),
            "active_budget_id": str(replacement["id"]),
        },
        requested_action="supersede",
        outcome="superseded",
    )
    return {
        "superseded_budget": serialize_execution_budget_row(superseded),
        "replacement_budget": serialize_execution_budget_row(replacement),
        "trace": cast(dict[str, object], trace),
    }


def _budget_specificity(row: ExecutionBudgetRow) -> int:
    return int(row["tool_key"] is not None) + int(row["domain_hint"] is not None)


def _matches_budget(
    row: ExecutionBudgetRow,
    *,
    tool_key: str,
    domain_hint: str | None,
) -> bool:
    if row["tool_key"] is not None and row["tool_key"] != tool_key:
        return False
    if row["domain_hint"] is not None and row["domain_hint"] != domain_hint:
        return False
    return True


def _matching_budget_rows(
    store: ContinuityStore,
    *,
    active_thread_profile_id: str | None,
    tool_key: str,
    domain_hint: str | None,
) -> list[ExecutionBudgetRow]:
    scoped_rows: list[ExecutionBudgetRow] = []
    global_rows: list[ExecutionBudgetRow] = []
    for row in store.list_execution_budgets():
        budget_row = cast(ExecutionBudgetRow, row)
        if cast(str, budget_row["status"]) != "active":
            continue
        if not _matches_budget(budget_row, tool_key=tool_key, domain_hint=domain_hint):
            continue
        budget_profile_id = cast(str | None, budget_row["agent_profile_id"])
        if active_thread_profile_id is not None and budget_profile_id == active_thread_profile_id:
            scoped_rows.append(budget_row)
        elif budget_profile_id is None:
            global_rows.append(budget_row)
    scoped_rows.sort(key=lambda row: (-_budget_specificity(row), row["created_at"], row["id"]))
    global_rows.sort(key=lambda row: (-_budget_specificity(row), row["created_at"], row["id"]))
    return [*scoped_rows, *global_rows]


def _thread_profile_id_optional(
    store: ContinuityStore,
    *,
    thread_id: UUID,
) -> str | None:
    thread = store.get_thread_optional(thread_id)
    if thread is None:
        return None
    profile_id = cast(str | None, thread.get("agent_profile_id"))
    if profile_id is None:
        profile_id = DEFAULT_AGENT_PROFILE_ID
    if store.get_agent_profile_optional(profile_id) is None:
        return None
    return profile_id


def _resolve_request_context(
    store: ContinuityStore,
    *,
    request: ToolRoutingRequestRecord,
) -> _RequestContextResolution:
    request_thread_id = request.get("thread_id")
    if not isinstance(request_thread_id, str):
        return _RequestContextResolution(
            request_thread_id=None,
            active_thread_profile_id=None,
            context_resolution="invalid",
            context_reason="request.thread_id is missing",
        )
    try:
        thread_id = UUID(request_thread_id)
    except (TypeError, ValueError):
        return _RequestContextResolution(
            request_thread_id=request_thread_id,
            active_thread_profile_id=None,
            context_resolution="invalid",
            context_reason=f"request.thread_id '{request_thread_id}' is not a valid UUID",
        )
    active_thread_profile_id = _thread_profile_id_optional(store, thread_id=thread_id)
    if active_thread_profile_id is None:
        return _RequestContextResolution(
            request_thread_id=request_thread_id,
            active_thread_profile_id=None,
            context_resolution="invalid",
            context_reason=(
                f"request.thread_id '{request_thread_id}' did not resolve to a visible "
                "thread/profile context"
            ),
        )
    return _RequestContextResolution(
        request_thread_id=request_thread_id,
        active_thread_profile_id=active_thread_profile_id,
        context_resolution="resolved",
        context_reason=None,
    )


def _count_profile_scope_id(
    *,
    matched_budget: ExecutionBudgetRow,
    active_thread_profile_id: str | None,
) -> str | None:
    matched_budget_profile_id = cast(str | None, matched_budget["agent_profile_id"])
    if matched_budget_profile_id is not None:
        return matched_budget_profile_id
    return active_thread_profile_id


def _execution_matches_budget(row: ToolExecutionRow, budget: ExecutionBudgetRow) -> bool:
    if cast(str, row["status"]) != "completed":
        return False

    tool = cast(dict[str, object], row["tool"])
    request = cast(dict[str, object], row["request"])

    if budget["tool_key"] is not None and tool.get("tool_key") != budget["tool_key"]:
        return False
    if budget["domain_hint"] is not None and request.get("domain_hint") != budget["domain_hint"]:
        return False
    return True


def _current_time(store: ContinuityStore) -> datetime:
    current_time = getattr(store, "current_time", None)
    if callable(current_time):
        value = current_time()
        if isinstance(value, datetime):
            return value
    return datetime.now(UTC)


def _window_started_at(
    *,
    evaluation_time: datetime,
    rolling_window_seconds: int | None,
) -> datetime | None:
    if rolling_window_seconds is None:
        return None
    return evaluation_time - timedelta(seconds=rolling_window_seconds)


def _counted_completed_execution_rows(
    store: ContinuityStore,
    *,
    matched_budget: ExecutionBudgetRow,
    evaluation_time: datetime,
    count_profile_scope_id: str | None,
) -> list[ToolExecutionRow]:
    window_started_at = _window_started_at(
        evaluation_time=evaluation_time,
        rolling_window_seconds=matched_budget["rolling_window_seconds"],
    )
    counted_rows: list[ToolExecutionRow] = []
    thread_profile_cache: dict[UUID, str | None] = {}
    for row in store.list_tool_executions():
        execution_row = cast(ToolExecutionRow, row)
        if not _execution_matches_budget(execution_row, matched_budget):
            continue
        request_payload = cast(dict[str, object], execution_row["request"])
        request_thread_id_raw = request_payload.get("thread_id")
        if not isinstance(request_thread_id_raw, str):
            continue
        try:
            request_thread_id = UUID(request_thread_id_raw)
        except (TypeError, ValueError):
            continue
        if request_thread_id != execution_row["thread_id"]:
            continue
        if request_thread_id not in thread_profile_cache:
            thread_profile_cache[request_thread_id] = _thread_profile_id_optional(
                store,
                thread_id=request_thread_id,
            )
        row_profile_id = thread_profile_cache[request_thread_id]
        if row_profile_id is None:
            continue
        if count_profile_scope_id is not None and row_profile_id != count_profile_scope_id:
            continue
        if window_started_at is not None and execution_row["executed_at"] < window_started_at:
            continue
        counted_rows.append(execution_row)
    return counted_rows


def _blocked_result(
    decision: ExecutionBudgetDecisionRecord,
) -> ToolExecutionResultRecord:
    matched_budget_id = decision["matched_budget_id"]
    max_completed_executions = decision["max_completed_executions"]
    projected_completed_execution_count = decision["projected_completed_execution_count"]
    rolling_window_seconds = decision["rolling_window_seconds"]
    if rolling_window_seconds is None:
        reason = (
            f"execution budget {matched_budget_id} blocks execution: projected completed executions "
            f"{projected_completed_execution_count} would exceed limit {max_completed_executions}"
        )
    else:
        reason = (
            f"execution budget {matched_budget_id} blocks execution: projected completed executions "
            f"{projected_completed_execution_count} within rolling window {rolling_window_seconds} "
            f"seconds would exceed limit {max_completed_executions}"
        )
    return {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": reason,
        "budget_decision": decision,
    }


def _invalid_context_blocked_result(
    decision: ExecutionBudgetDecisionRecord,
) -> ToolExecutionResultRecord:
    context_reason = cast(str | None, decision.get("context_reason"))
    reason = "execution budget invariance blocks execution: invalid request thread/profile context"
    if context_reason is not None:
        reason = f"{reason}: {context_reason}"
    return {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": reason,
        "budget_decision": decision,
    }


def evaluate_execution_budget(
    store: ContinuityStore,
    *,
    tool: ToolRecord,
    request: ToolRoutingRequestRecord,
) -> ExecutionBudgetDecision:
    request_context = _resolve_request_context(store, request=request)
    active_thread_profile_id = request_context.active_thread_profile_id
    matching_budgets = (
        []
        if request_context.context_resolution == "invalid"
        else _matching_budget_rows(
            store,
            active_thread_profile_id=active_thread_profile_id,
            tool_key=tool["tool_key"],
            domain_hint=request["domain_hint"],
        )
    )
    matched_budget = matching_budgets[0] if matching_budgets else None
    evaluation_time = _current_time(store)
    window_started_at = (
        None
        if matched_budget is None
        else _window_started_at(
            evaluation_time=evaluation_time,
            rolling_window_seconds=matched_budget["rolling_window_seconds"],
        )
    )
    completed_execution_count = 0
    projected_completed_execution_count = 1

    if matched_budget is not None:
        completed_execution_count = len(
            _counted_completed_execution_rows(
                store,
                matched_budget=matched_budget,
                evaluation_time=evaluation_time,
                count_profile_scope_id=_count_profile_scope_id(
                    matched_budget=matched_budget,
                    active_thread_profile_id=active_thread_profile_id,
                ),
            )
        )
        projected_completed_execution_count = completed_execution_count + 1

    record: ExecutionBudgetDecisionRecord = {
        "matched_budget_id": None if matched_budget is None else str(matched_budget["id"]),
        "tool_key": tool["tool_key"],
        "domain_hint": request["domain_hint"],
        "budget_tool_key": None if matched_budget is None else matched_budget["tool_key"],
        "budget_domain_hint": None if matched_budget is None else matched_budget["domain_hint"],
        "max_completed_executions": (
            None if matched_budget is None else matched_budget["max_completed_executions"]
        ),
        "rolling_window_seconds": (
            None if matched_budget is None else matched_budget["rolling_window_seconds"]
        ),
        "count_scope": (
            "lifetime"
            if matched_budget is None or matched_budget["rolling_window_seconds"] is None
            else "rolling_window"
        ),
        "window_started_at": None if window_started_at is None else window_started_at.isoformat(),
        "completed_execution_count": completed_execution_count,
        "projected_completed_execution_count": projected_completed_execution_count,
        "decision": "allow",
        "reason": "no_matching_budget",
        "order": list(EXECUTION_BUDGET_MATCH_ORDER),
        "history_order": list(TOOL_EXECUTION_LIST_ORDER),
    }

    if request_context.context_resolution == "invalid":
        record["decision"] = "block"
        record["reason"] = "invalid_request_context"
        record["request_thread_id"] = request_context.request_thread_id
        record["context_resolution"] = request_context.context_resolution
        record["context_reason"] = request_context.context_reason
        blocked_result = _invalid_context_blocked_result(record)
        return ExecutionBudgetDecision(record=record, blocked_result=blocked_result)

    if matched_budget is None:
        return ExecutionBudgetDecision(record=record, blocked_result=None)

    if projected_completed_execution_count <= matched_budget["max_completed_executions"]:
        record["reason"] = "within_budget"
        return ExecutionBudgetDecision(record=record, blocked_result=None)

    record["decision"] = "block"
    record["reason"] = "budget_exceeded"
    blocked_result = _blocked_result(record)
    return ExecutionBudgetDecision(record=record, blocked_result=blocked_result)
