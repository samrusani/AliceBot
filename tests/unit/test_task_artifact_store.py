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


def test_task_artifact_store_methods_use_expected_queries() -> None:
    task_artifact_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": task_artifact_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "task_workspace_id": task_workspace_id,
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": "docs/spec.txt",
                "media_type_hint": "text/plain",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            },
            {
                "id": task_artifact_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "task_workspace_id": task_workspace_id,
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": "docs/spec.txt",
                "media_type_hint": "text/plain",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            },
            {
                "id": task_artifact_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "task_workspace_id": task_workspace_id,
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": "docs/spec.txt",
                "media_type_hint": "text/plain",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            },
        ],
        fetchall_result=[
            {
                "id": task_artifact_id,
                "user_id": uuid4(),
                "task_id": task_id,
                "task_workspace_id": task_workspace_id,
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": "docs/spec.txt",
                "media_type_hint": "text/plain",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            }
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/spec.txt",
        media_type_hint="text/plain",
    )
    fetched = store.get_task_artifact_optional(task_artifact_id)
    duplicate = store.get_task_artifact_by_workspace_relative_path_optional(
        task_workspace_id=task_workspace_id,
        relative_path="docs/spec.txt",
    )
    listed = store.list_task_artifacts()
    store.lock_task_artifacts(task_workspace_id)

    assert created["id"] == task_artifact_id
    assert fetched is not None
    assert duplicate is not None
    assert listed[0]["id"] == task_artifact_id
    assert cursor.executed == [
        (
            """
                INSERT INTO task_artifacts (
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                )
                VALUES (
                  app.current_user_id(),
                  %s,
                  %s,
                  %s,
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
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                """,
            (
                task_id,
                task_workspace_id,
                "registered",
                "pending",
                "docs/spec.txt",
                "text/plain",
            ),
        ),
        (
            """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE id = %s
                """,
            (task_artifact_id,),
        ),
        (
            """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                WHERE task_workspace_id = %s
                  AND relative_path = %s
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """,
            (task_workspace_id, "docs/spec.txt"),
        ),
        (
            """
                SELECT
                  id,
                  user_id,
                  task_id,
                  task_workspace_id,
                  status,
                  ingestion_status,
                  relative_path,
                  media_type_hint,
                  created_at,
                  updated_at
                FROM task_artifacts
                ORDER BY created_at ASC, id ASC
                """,
            None,
        ),
        (
            "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 4))",
            (str(task_workspace_id),),
        ),
    ]
