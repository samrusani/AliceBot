from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from alicebot_api.store import ContinuityStore


class RecordingCursor:
    def __init__(self, fetchone_results: list[dict[str, Any]], fetchall_result: list[dict[str, Any]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_result = fetchall_result or []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        return self.fetchall_result


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def test_tool_execution_store_methods_use_expected_queries_and_jsonb_parameters() -> None:
    execution_id = uuid4()
    approval_id = uuid4()
    task_step_id = uuid4()
    thread_id = uuid4()
    tool_id = uuid4()
    trace_id = uuid4()
    request_event_id = uuid4()
    result_event_id = uuid4()
    row = {
        "id": execution_id,
        "approval_id": approval_id,
        "task_step_id": task_step_id,
        "thread_id": thread_id,
        "tool_id": tool_id,
        "trace_id": trace_id,
        "request_event_id": request_event_id,
        "result_event_id": result_event_id,
        "status": "completed",
        "handler_key": "proxy.echo",
        "request": {"thread_id": str(thread_id), "tool_id": str(tool_id)},
        "tool": {"id": str(tool_id), "tool_key": "proxy.echo"},
        "result": {"handler_key": "proxy.echo", "status": "completed", "output": {"mode": "no_side_effect"}, "reason": None},
        "executed_at": "2026-03-13T10:00:00+00:00",
    }
    cursor = RecordingCursor(
        fetchone_results=[row, row],
        fetchall_result=[row],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_tool_execution(
        approval_id=approval_id,
        task_step_id=task_step_id,
        thread_id=thread_id,
        tool_id=tool_id,
        trace_id=trace_id,
        request_event_id=request_event_id,
        result_event_id=result_event_id,
        status="completed",
        handler_key="proxy.echo",
        request={"thread_id": str(thread_id), "tool_id": str(tool_id)},
        tool={"id": str(tool_id), "tool_key": "proxy.echo"},
        result={"handler_key": "proxy.echo", "status": "completed", "output": {"mode": "no_side_effect"}, "reason": None},
    )
    fetched = store.get_tool_execution_optional(execution_id)
    listed = store.list_tool_executions()

    assert created["id"] == execution_id
    assert fetched is not None
    assert fetched["id"] == execution_id
    assert listed[0]["id"] == execution_id

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO tool_executions" in create_query
    assert create_params is not None
    assert create_params[:9] == (
        approval_id,
        task_step_id,
        thread_id,
        tool_id,
        trace_id,
        request_event_id,
        result_event_id,
        "completed",
        "proxy.echo",
    )
    assert isinstance(create_params[9], Jsonb)
    assert create_params[9].obj == {"thread_id": str(thread_id), "tool_id": str(tool_id)}
    assert isinstance(create_params[10], Jsonb)
    assert create_params[10].obj == {"id": str(tool_id), "tool_key": "proxy.echo"}
    assert isinstance(create_params[11], Jsonb)
    assert create_params[11].obj == {
        "handler_key": "proxy.echo",
        "status": "completed",
        "output": {"mode": "no_side_effect"},
        "reason": None,
    }
    assert "FROM tool_executions" in cursor.executed[1][0]
    assert "ORDER BY executed_at ASC, id ASC" in cursor.executed[2][0]


def test_create_tool_execution_accepts_blocked_attempt_without_event_ids() -> None:
    execution_id = uuid4()
    approval_id = uuid4()
    task_step_id = uuid4()
    thread_id = uuid4()
    tool_id = uuid4()
    trace_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": execution_id,
                "approval_id": approval_id,
                "task_step_id": task_step_id,
                "thread_id": thread_id,
                "tool_id": tool_id,
                "trace_id": trace_id,
                "request_event_id": None,
                "result_event_id": None,
                "status": "blocked",
                "handler_key": None,
                "request": {"thread_id": str(thread_id), "tool_id": str(tool_id)},
                "tool": {"id": str(tool_id), "tool_key": "proxy.missing"},
                "result": {
                    "handler_key": None,
                    "status": "blocked",
                    "output": None,
                    "reason": "tool 'proxy.missing' has no registered proxy handler",
                },
                "executed_at": "2026-03-13T10:05:00+00:00",
            }
        ]
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_tool_execution(
        approval_id=approval_id,
        task_step_id=task_step_id,
        thread_id=thread_id,
        tool_id=tool_id,
        trace_id=trace_id,
        request_event_id=None,
        result_event_id=None,
        status="blocked",
        handler_key=None,
        request={"thread_id": str(thread_id), "tool_id": str(tool_id)},
        tool={"id": str(tool_id), "tool_key": "proxy.missing"},
        result={
            "handler_key": None,
            "status": "blocked",
            "output": None,
            "reason": "tool 'proxy.missing' has no registered proxy handler",
        },
    )

    assert created["status"] == "blocked"
    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO tool_executions" in create_query
    assert create_params is not None
    assert create_params[5] is None
    assert create_params[6] is None
    assert create_params[8] is None
