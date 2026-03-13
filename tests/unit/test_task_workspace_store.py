from __future__ import annotations

from typing import Any
from uuid import uuid4

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


def test_task_workspace_store_methods_use_expected_queries() -> None:
    task_workspace_id = uuid4()
    task_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": task_workspace_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "status": "active",
                "local_path": "/tmp/alicebot/task-workspaces/user/task",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            },
            {
                "id": task_workspace_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "status": "active",
                "local_path": "/tmp/alicebot/task-workspaces/user/task",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            },
            {
                "id": task_workspace_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "status": "active",
                "local_path": "/tmp/alicebot/task-workspaces/user/task",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            },
        ],
        fetchall_result=[
            {
                "id": task_workspace_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "status": "active",
                "local_path": "/tmp/alicebot/task-workspaces/user/task",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            }
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_task_workspace(
        task_id=task_id,
        status="active",
        local_path="/tmp/alicebot/task-workspaces/user/task",
    )
    fetched = store.get_task_workspace_optional(task_workspace_id)
    active = store.get_active_task_workspace_for_task_optional(task_id)
    listed = store.list_task_workspaces()
    store.lock_task_workspaces(task_id)

    assert created["id"] == task_workspace_id
    assert fetched is not None
    assert active is not None
    assert listed[0]["id"] == task_workspace_id
    assert cursor.executed == [
        (
            """
                INSERT INTO task_workspaces (
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
                  clock_timestamp(),
                  clock_timestamp()
                )
                RETURNING
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                """,
            (task_id, "active", "/tmp/alicebot/task-workspaces/user/task"),
        ),
        (
            """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                WHERE id = %s
                """,
            (task_workspace_id,),
        ),
        (
            """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                WHERE task_id = %s
                  AND status = 'active'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """,
            (task_id,),
        ),
        (
            """
                SELECT
                  id,
                  user_id,
                  task_id,
                  status,
                  local_path,
                  created_at,
                  updated_at
                FROM task_workspaces
                ORDER BY created_at ASC, id ASC
                """,
            None,
        ),
        (
            "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 3))",
            (str(task_id),),
        ),
    ]
