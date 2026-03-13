from __future__ import annotations

from typing import cast
from uuid import UUID

from alicebot_api.contracts import (
    TOOL_EXECUTION_LIST_ORDER,
    ToolExecutionDetailResponse,
    ToolExecutionListResponse,
    ToolExecutionListSummary,
    ToolExecutionRecord,
)
from alicebot_api.store import ContinuityStore, ToolExecutionRow


class ToolExecutionNotFoundError(LookupError):
    """Raised when an execution record is not visible inside the current user scope."""


def serialize_tool_execution_row(row: ToolExecutionRow) -> ToolExecutionRecord:
    return {
        "id": str(row["id"]),
        "approval_id": str(row["approval_id"]),
        "task_step_id": str(row["task_step_id"]),
        "thread_id": str(row["thread_id"]),
        "tool_id": str(row["tool_id"]),
        "trace_id": str(row["trace_id"]),
        "request_event_id": None if row["request_event_id"] is None else str(row["request_event_id"]),
        "result_event_id": None if row["result_event_id"] is None else str(row["result_event_id"]),
        "status": cast(str, row["status"]),
        "handler_key": row["handler_key"],
        "request": cast(dict[str, object], row["request"]),
        "tool": cast(dict[str, object], row["tool"]),
        "result": cast(dict[str, object], row["result"]),
        "executed_at": row["executed_at"].isoformat(),
    }


def list_tool_execution_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> ToolExecutionListResponse:
    del user_id

    items = [serialize_tool_execution_row(row) for row in store.list_tool_executions()]
    summary: ToolExecutionListSummary = {
        "total_count": len(items),
        "order": list(TOOL_EXECUTION_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_tool_execution_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    execution_id: UUID,
) -> ToolExecutionDetailResponse:
    del user_id

    execution = store.get_tool_execution_optional(execution_id)
    if execution is None:
        raise ToolExecutionNotFoundError(f"tool execution {execution_id} was not found")
    return {"execution": serialize_tool_execution_row(execution)}
