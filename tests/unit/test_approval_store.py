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


def test_approval_store_methods_use_expected_queries_and_jsonb_parameters() -> None:
    approval_id = uuid4()
    thread_id = uuid4()
    tool_id = uuid4()
    task_step_id = uuid4()
    routing_trace_id = uuid4()
    resolved_by_user_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": approval_id,
                "thread_id": thread_id,
                "tool_id": tool_id,
                "task_step_id": task_step_id,
                "status": "pending",
                "request": {"thread_id": str(thread_id), "tool_id": str(tool_id)},
                "tool": {"id": str(tool_id), "tool_key": "shell.exec"},
                "routing": {"decision": "approval_required", "trace": {"trace_id": str(routing_trace_id)}},
                "routing_trace_id": routing_trace_id,
                "resolved_at": None,
                "resolved_by_user_id": None,
            },
            {
                "id": approval_id,
                "thread_id": thread_id,
                "tool_id": tool_id,
                "task_step_id": task_step_id,
                "status": "pending",
                "request": {"thread_id": str(thread_id), "tool_id": str(tool_id)},
                "tool": {"id": str(tool_id), "tool_key": "shell.exec"},
                "routing": {"decision": "approval_required", "trace": {"trace_id": str(routing_trace_id)}},
                "routing_trace_id": routing_trace_id,
                "resolved_at": None,
                "resolved_by_user_id": None,
            },
            {
                "id": approval_id,
                "thread_id": thread_id,
                "tool_id": tool_id,
                "task_step_id": task_step_id,
                "status": "approved",
                "request": {"thread_id": str(thread_id), "tool_id": str(tool_id)},
                "tool": {"id": str(tool_id), "tool_key": "shell.exec"},
                "routing": {"decision": "approval_required", "trace": {"trace_id": str(routing_trace_id)}},
                "routing_trace_id": routing_trace_id,
                "resolved_at": "2026-03-12T10:00:00+00:00",
                "resolved_by_user_id": resolved_by_user_id,
            },
        ],
        fetchall_result=[
            {
                "id": approval_id,
                "thread_id": thread_id,
                "tool_id": tool_id,
                "task_step_id": task_step_id,
                "status": "pending",
                "request": {"thread_id": str(thread_id), "tool_id": str(tool_id)},
                "tool": {"id": str(tool_id), "tool_key": "shell.exec"},
                "routing": {"decision": "approval_required", "trace": {"trace_id": str(routing_trace_id)}},
                "routing_trace_id": routing_trace_id,
                "resolved_at": None,
                "resolved_by_user_id": None,
            }
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_approval(
        thread_id=thread_id,
        tool_id=tool_id,
        task_step_id=task_step_id,
        status="pending",
        request={"thread_id": str(thread_id), "tool_id": str(tool_id)},
        tool={"id": str(tool_id), "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "trace": {"trace_id": str(routing_trace_id)}},
        routing_trace_id=routing_trace_id,
    )
    fetched = store.get_approval_optional(approval_id)
    listed = store.list_approvals()
    resolved = store.resolve_approval_optional(approval_id=approval_id, status="approved")

    assert created["id"] == approval_id
    assert created["resolved_at"] is None
    assert fetched is not None
    assert listed[0]["id"] == approval_id
    assert resolved is not None
    assert resolved["status"] == "approved"

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO approvals" in create_query
    assert create_params is not None
    assert create_params[:4] == (thread_id, tool_id, task_step_id, "pending")
    assert isinstance(create_params[4], Jsonb)
    assert create_params[4].obj == {"thread_id": str(thread_id), "tool_id": str(tool_id)}
    assert isinstance(create_params[5], Jsonb)
    assert create_params[5].obj == {"id": str(tool_id), "tool_key": "shell.exec"}
    assert isinstance(create_params[6], Jsonb)
    assert create_params[6].obj == {
        "decision": "approval_required",
        "trace": {"trace_id": str(routing_trace_id)},
    }
    assert create_params[7] == routing_trace_id
    assert "resolved_at" in cursor.executed[1][0]
    assert "ORDER BY created_at ASC, id ASC" in cursor.executed[2][0]

    resolve_query, resolve_params = cursor.executed[3]
    assert "UPDATE approvals" in resolve_query
    assert "WHERE id = %s" in resolve_query
    assert "AND status = 'pending'" in resolve_query
    assert resolve_params == ("approved", approval_id)
