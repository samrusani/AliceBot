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


def test_task_run_store_methods_use_expected_queries_and_jsonb_parameters() -> None:
    task_id = uuid4()
    task_run_id = uuid4()
    row = {
        "id": task_run_id,
        "user_id": uuid4(),
        "task_id": task_id,
        "status": "queued",
        "checkpoint": {"cursor": 0, "target_steps": 2, "wait_for_signal": False},
        "tick_count": 0,
        "step_count": 0,
        "max_ticks": 2,
        "stop_reason": None,
        "created_at": "2026-03-27T10:00:00+00:00",
        "updated_at": "2026-03-27T10:00:00+00:00",
    }
    cursor = RecordingCursor(
        fetchone_results=[
            row,
            row,
            {**row, "status": "running", "tick_count": 1, "step_count": 1},
            {**row, "status": "running"},
        ],
        fetchall_result=[row],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_task_run(
        task_id=task_id,
        status="queued",
        checkpoint={"cursor": 0, "target_steps": 2, "wait_for_signal": False},
        tick_count=0,
        step_count=0,
        max_ticks=2,
        stop_reason=None,
    )
    fetched = store.get_task_run_optional(task_run_id)
    listed = store.list_task_runs_for_task(task_id)
    updated = store.update_task_run_optional(
        task_run_id=task_run_id,
        status="running",
        checkpoint={"cursor": 1, "target_steps": 2, "wait_for_signal": False},
        tick_count=1,
        step_count=1,
        stop_reason=None,
    )
    acquired = store.acquire_next_task_run_optional()

    assert created["id"] == task_run_id
    assert fetched is not None
    assert fetched["id"] == task_run_id
    assert listed[0]["id"] == task_run_id
    assert updated is not None
    assert updated["status"] == "running"
    assert acquired is not None
    assert acquired["status"] == "running"

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO task_runs" in create_query
    assert create_params is not None
    assert create_params[0] == task_id
    assert create_params[1] == "queued"
    assert isinstance(create_params[2], Jsonb)
    assert create_params[2].obj == {"cursor": 0, "target_steps": 2, "wait_for_signal": False}
    assert create_params[3:] == (0, 0, 2, None)

    assert "FROM task_runs" in cursor.executed[1][0]
    assert "ORDER BY created_at ASC, id ASC" in cursor.executed[2][0]

    update_query, update_params = cursor.executed[3]
    assert "UPDATE task_runs" in update_query
    assert update_params is not None
    assert update_params[0] == "running"
    assert isinstance(update_params[1], Jsonb)
    assert update_params[1].obj == {"cursor": 1, "target_steps": 2, "wait_for_signal": False}
    assert update_params[2:] == (1, 1, None, task_run_id)

    acquire_query, acquire_params = cursor.executed[4]
    assert "WITH candidate AS" in acquire_query
    assert "FOR UPDATE SKIP LOCKED" in acquire_query
    assert "UPDATE task_runs" in acquire_query
    assert acquire_params is None
