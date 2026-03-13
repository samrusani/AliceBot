from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.config import Settings
from alicebot_api.contracts import TaskWorkspaceCreateInput
from alicebot_api.tasks import TaskNotFoundError
from alicebot_api.workspaces import (
    TaskWorkspaceAlreadyExistsError,
    TaskWorkspaceNotFoundError,
    TaskWorkspaceProvisioningError,
    build_task_workspace_path,
    create_task_workspace_record,
    ensure_workspace_path_is_rooted,
    get_task_workspace_record,
    list_task_workspace_records,
    serialize_task_workspace_row,
)


class WorkspaceStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 10, 0, tzinfo=UTC)
        self.tasks: list[dict[str, object]] = []
        self.workspaces: list[dict[str, object]] = []
        self.locked_task_ids: list[UUID] = []

    def create_task(self, *, task_id: UUID, user_id: UUID) -> None:
        self.tasks.append(
            {
                "id": task_id,
                "user_id": user_id,
                "thread_id": uuid4(),
                "tool_id": uuid4(),
                "status": "approved",
                "request": {},
                "tool": {},
                "latest_approval_id": None,
                "latest_execution_id": None,
                "created_at": self.base_time,
                "updated_at": self.base_time,
            }
        )

    def get_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["id"] == task_id), None)

    def lock_task_workspaces(self, task_id: UUID) -> None:
        self.locked_task_ids.append(task_id)

    def get_active_task_workspace_for_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return next(
            (
                workspace
                for workspace in self.workspaces
                if workspace["task_id"] == task_id and workspace["status"] == "active"
            ),
            None,
        )

    def create_task_workspace(
        self,
        *,
        task_id: UUID,
        status: str,
        local_path: str,
    ) -> dict[str, object]:
        workspace = {
            "id": uuid4(),
            "user_id": self.tasks[0]["user_id"],
            "task_id": task_id,
            "status": status,
            "local_path": local_path,
            "created_at": self.base_time + timedelta(minutes=len(self.workspaces)),
            "updated_at": self.base_time + timedelta(minutes=len(self.workspaces)),
        }
        self.workspaces.append(workspace)
        return workspace

    def list_task_workspaces(self) -> list[dict[str, object]]:
        return sorted(self.workspaces, key=lambda workspace: (workspace["created_at"], workspace["id"]))

    def get_task_workspace_optional(self, task_workspace_id: UUID) -> dict[str, object] | None:
        return next((workspace for workspace in self.workspaces if workspace["id"] == task_workspace_id), None)


def test_build_task_workspace_path_is_deterministic() -> None:
    user_id = UUID("00000000-0000-0000-0000-000000000111")
    task_id = UUID("00000000-0000-0000-0000-000000000222")
    root = Path("/tmp/alicebot/task-workspaces")

    path = build_task_workspace_path(
        workspace_root=root,
        user_id=user_id,
        task_id=task_id,
    )

    assert path == Path("/tmp/alicebot/task-workspaces") / str(user_id) / str(task_id)


def test_ensure_workspace_path_is_rooted_rejects_escape() -> None:
    with pytest.raises(TaskWorkspaceProvisioningError, match="escapes configured root"):
        ensure_workspace_path_is_rooted(
            workspace_root=Path("/tmp/alicebot/task-workspaces"),
            workspace_path=Path("/tmp/alicebot/task-workspaces/../escape"),
        )


def test_create_task_workspace_record_provisions_directory_and_returns_record(tmp_path) -> None:
    store = WorkspaceStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    store.create_task(task_id=task_id, user_id=user_id)
    settings = Settings(task_workspace_root=str(tmp_path / "workspaces"))

    response = create_task_workspace_record(
        store,
        settings=settings,
        user_id=user_id,
        request=TaskWorkspaceCreateInput(task_id=task_id, status="active"),
    )

    expected_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    assert response == {
        "workspace": {
            "id": response["workspace"]["id"],
            "task_id": str(task_id),
            "status": "active",
            "local_path": str(expected_path.resolve()),
            "created_at": "2026-03-13T10:00:00+00:00",
            "updated_at": "2026-03-13T10:00:00+00:00",
        }
    }
    assert expected_path.is_dir()
    assert store.locked_task_ids == [task_id]


def test_create_task_workspace_record_rejects_duplicate_active_workspace(tmp_path) -> None:
    store = WorkspaceStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    store.create_task(task_id=task_id, user_id=user_id)
    settings = Settings(task_workspace_root=str(tmp_path / "workspaces"))
    create_task_workspace_record(
        store,
        settings=settings,
        user_id=user_id,
        request=TaskWorkspaceCreateInput(task_id=task_id, status="active"),
    )

    with pytest.raises(TaskWorkspaceAlreadyExistsError, match=f"task {task_id} already has active workspace"):
        create_task_workspace_record(
            store,
            settings=settings,
            user_id=user_id,
            request=TaskWorkspaceCreateInput(task_id=task_id, status="active"),
        )


def test_create_task_workspace_record_requires_visible_task(tmp_path) -> None:
    store = WorkspaceStoreStub()

    with pytest.raises(TaskNotFoundError, match="was not found"):
        create_task_workspace_record(
            store,
            settings=Settings(task_workspace_root=str(tmp_path / "workspaces")),
            user_id=uuid4(),
            request=TaskWorkspaceCreateInput(task_id=uuid4(), status="active"),
        )


def test_list_and_get_task_workspace_records_are_deterministic() -> None:
    store = WorkspaceStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    store.create_task(task_id=task_id, user_id=user_id)
    workspace = store.create_task_workspace(
        task_id=task_id,
        status="active",
        local_path="/tmp/alicebot/task-workspaces/user/task",
    )

    assert list_task_workspace_records(store, user_id=user_id) == {
        "items": [serialize_task_workspace_row(workspace)],
        "summary": {
            "total_count": 1,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert get_task_workspace_record(
        store,
        user_id=user_id,
        task_workspace_id=workspace["id"],
    ) == {"workspace": serialize_task_workspace_row(workspace)}


def test_get_task_workspace_record_raises_when_workspace_is_missing() -> None:
    with pytest.raises(TaskWorkspaceNotFoundError, match="was not found"):
        get_task_workspace_record(
            WorkspaceStoreStub(),
            user_id=uuid4(),
            task_workspace_id=uuid4(),
        )
