from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb
import pytest

from alicebot_api.store import ContinuityStore, ContinuityStoreInvariantError


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


def test_task_step_store_methods_use_expected_queries_and_jsonb_parameters() -> None:
    task_step_id = uuid4()
    task_id = uuid4()
    thread_id = uuid4()
    tool_id = uuid4()
    trace_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": task_step_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "sequence_no": 1,
                "parent_step_id": None,
                "source_approval_id": None,
                "source_execution_id": None,
                "kind": "governed_request",
                "status": "created",
                "request": {"thread_id": str(uuid4()), "tool_id": str(uuid4())},
                "outcome": {
                    "routing_decision": "approval_required",
                    "approval_id": None,
                    "approval_status": None,
                    "execution_id": None,
                    "execution_status": None,
                    "blocked_reason": None,
                },
                "trace_id": trace_id,
                "trace_kind": "approval.request",
            },
            {
                "id": task_step_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "sequence_no": 1,
                "parent_step_id": None,
                "source_approval_id": None,
                "source_execution_id": None,
                "kind": "governed_request",
                "status": "created",
                "request": {"thread_id": str(uuid4()), "tool_id": str(uuid4())},
                "outcome": {
                    "routing_decision": "approval_required",
                    "approval_id": None,
                    "approval_status": None,
                    "execution_id": None,
                    "execution_status": None,
                    "blocked_reason": None,
                },
                "trace_id": trace_id,
                "trace_kind": "approval.request",
            },
            {
                "id": task_step_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "sequence_no": 1,
                "parent_step_id": None,
                "source_approval_id": None,
                "source_execution_id": None,
                "kind": "governed_request",
                "status": "approved",
                "request": {"thread_id": str(uuid4()), "tool_id": str(uuid4())},
                "outcome": {
                    "routing_decision": "approval_required",
                    "approval_id": str(uuid4()),
                    "approval_status": "approved",
                    "execution_id": None,
                    "execution_status": None,
                    "blocked_reason": None,
                },
                "trace_id": trace_id,
                "trace_kind": "approval.resolve",
            },
            {
                "id": task_step_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "sequence_no": 1,
                "parent_step_id": None,
                "source_approval_id": None,
                "source_execution_id": None,
                "kind": "governed_request",
                "status": "approved",
                "request": {"thread_id": str(uuid4()), "tool_id": str(uuid4())},
                "outcome": {
                    "routing_decision": "approval_required",
                    "approval_id": str(uuid4()),
                    "approval_status": "approved",
                    "execution_id": None,
                    "execution_status": None,
                    "blocked_reason": None,
                },
                "trace_id": trace_id,
                "trace_kind": "approval.resolve",
            },
            {
                "id": task_id,
                "user_id": uuid4(),
                "thread_id": thread_id,
                "tool_id": tool_id,
                "status": "approved",
                "request": {"thread_id": str(uuid4()), "tool_id": str(uuid4())},
                "tool": {"id": str(tool_id), "tool_key": "proxy.echo"},
                "latest_approval_id": None,
                "latest_execution_id": None,
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:05:00+00:00",
            },
        ],
        fetchall_result=[
            {
                "id": task_step_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "sequence_no": 1,
                "parent_step_id": None,
                "source_approval_id": None,
                "source_execution_id": None,
                "kind": "governed_request",
                "status": "created",
                "request": {"thread_id": str(uuid4()), "tool_id": str(uuid4())},
                "outcome": {
                    "routing_decision": "approval_required",
                    "approval_id": None,
                    "approval_status": None,
                    "execution_id": None,
                    "execution_status": None,
                    "blocked_reason": None,
                },
                "trace_id": trace_id,
                "trace_kind": "approval.request",
            }
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_task_step(
        task_id=task_id,
        sequence_no=1,
        kind="governed_request",
        status="created",
        request={"thread_id": "thread-123", "tool_id": "tool-123"},
        outcome={
            "routing_decision": "approval_required",
            "approval_id": None,
            "approval_status": None,
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=trace_id,
        trace_kind="approval.request",
    )
    fetched = store.get_task_step_optional(task_step_id)
    listed = store.list_task_steps_for_task(task_id)
    updated = store.update_task_step_for_task_sequence_optional(
        task_id=task_id,
        sequence_no=1,
        status="approved",
        outcome={
            "routing_decision": "approval_required",
            "approval_id": "approval-123",
            "approval_status": "approved",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=trace_id,
        trace_kind="approval.resolve",
    )
    updated_by_id = store.update_task_step_optional(
        task_step_id=task_step_id,
        status="approved",
        outcome={
            "routing_decision": "approval_required",
            "approval_id": "approval-123",
            "approval_status": "approved",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=trace_id,
        trace_kind="approval.resolve",
    )
    updated_task = store.update_task_status_optional(
        task_id=task_id,
        status="approved",
        latest_approval_id=None,
        latest_execution_id=None,
    )

    assert created["id"] == task_step_id
    assert fetched is not None
    assert listed[0]["id"] == task_step_id
    assert updated is not None
    assert updated["status"] == "approved"
    assert updated_by_id is not None
    assert updated_by_id["status"] == "approved"
    assert updated_task is not None
    assert updated_task["status"] == "approved"

    lock_query, lock_params = cursor.executed[0]
    assert "pg_advisory_xact_lock" in lock_query
    assert lock_params == (str(task_id),)

    create_query, create_params = cursor.executed[1]
    assert "INSERT INTO task_steps" in create_query
    assert create_params is not None
    assert create_params[:7] == (task_id, 1, None, None, None, "governed_request", "created")
    assert isinstance(create_params[7], Jsonb)
    assert create_params[7].obj == {"thread_id": "thread-123", "tool_id": "tool-123"}
    assert isinstance(create_params[8], Jsonb)
    assert create_params[8].obj == {
        "routing_decision": "approval_required",
        "approval_id": None,
        "approval_status": None,
        "execution_id": None,
        "execution_status": None,
        "blocked_reason": None,
    }
    assert create_params[9] == trace_id
    assert create_params[10] == "approval.request"
    assert "FROM task_steps" in cursor.executed[2][0]
    assert "ORDER BY sequence_no ASC, created_at ASC, id ASC" in cursor.executed[3][0]

    update_query, update_params = cursor.executed[4]
    assert "UPDATE task_steps" in update_query
    assert "WHERE task_id = %s" in update_query
    assert update_params is not None
    assert update_params[0] == "approved"
    assert isinstance(update_params[1], Jsonb)
    assert update_params[1].obj["approval_status"] == "approved"
    assert update_params[2] == trace_id
    assert update_params[3] == "approval.resolve"
    assert update_params[4:] == (task_id, 1)

    update_by_id_query, update_by_id_params = cursor.executed[5]
    assert "UPDATE task_steps" in update_by_id_query
    assert "WHERE id = %s" in update_by_id_query
    assert update_by_id_params is not None
    assert update_by_id_params[0] == "approved"
    assert isinstance(update_by_id_params[1], Jsonb)
    assert update_by_id_params[1].obj["approval_status"] == "approved"
    assert update_by_id_params[2] == trace_id
    assert update_by_id_params[3] == "approval.resolve"
    assert update_by_id_params[4] == task_step_id

    task_update_query, task_update_params = cursor.executed[6]
    assert "UPDATE tasks" in task_update_query
    assert task_update_params == ("approved", None, None, task_id)


def test_create_task_step_raises_clear_error_when_returning_row_is_missing() -> None:
    task_id = uuid4()
    store = ContinuityStore(RecordingConnection(RecordingCursor(fetchone_results=[])))

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="create_task_step did not return a row",
    ):
        store.create_task_step(
            task_id=task_id,
            sequence_no=1,
            kind="governed_request",
            status="created",
            request={"thread_id": "thread-123", "tool_id": "tool-123"},
            outcome={
                "routing_decision": "approval_required",
                "approval_id": None,
                "approval_status": None,
                "execution_id": None,
                "execution_status": None,
                "blocked_reason": None,
            },
            trace_id=uuid4(),
            trace_kind="approval.request",
        )
