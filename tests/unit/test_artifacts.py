from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.artifacts import (
    TaskArtifactAlreadyExistsError,
    TaskArtifactNotFoundError,
    TaskArtifactValidationError,
    build_workspace_relative_artifact_path,
    ensure_artifact_path_is_rooted,
    get_task_artifact_record,
    list_task_artifact_records,
    register_task_artifact_record,
    serialize_task_artifact_row,
)
from alicebot_api.contracts import TaskArtifactRegisterInput
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


class ArtifactStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 10, 0, tzinfo=UTC)
        self.workspaces: list[dict[str, object]] = []
        self.artifacts: list[dict[str, object]] = []
        self.locked_workspace_ids: list[UUID] = []

    def create_task_workspace(self, *, task_workspace_id: UUID, task_id: UUID, user_id: UUID, local_path: str) -> dict[str, object]:
        workspace = {
            "id": task_workspace_id,
            "user_id": user_id,
            "task_id": task_id,
            "status": "active",
            "local_path": local_path,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.workspaces.append(workspace)
        return workspace

    def get_task_workspace_optional(self, task_workspace_id: UUID) -> dict[str, object] | None:
        return next((workspace for workspace in self.workspaces if workspace["id"] == task_workspace_id), None)

    def lock_task_artifacts(self, task_workspace_id: UUID) -> None:
        self.locked_workspace_ids.append(task_workspace_id)

    def get_task_artifact_by_workspace_relative_path_optional(
        self,
        *,
        task_workspace_id: UUID,
        relative_path: str,
    ) -> dict[str, object] | None:
        return next(
            (
                artifact
                for artifact in self.artifacts
                if artifact["task_workspace_id"] == task_workspace_id
                and artifact["relative_path"] == relative_path
            ),
            None,
        )

    def create_task_artifact(
        self,
        *,
        task_id: UUID,
        task_workspace_id: UUID,
        status: str,
        ingestion_status: str,
        relative_path: str,
        media_type_hint: str | None,
    ) -> dict[str, object]:
        artifact = {
            "id": uuid4(),
            "user_id": self.workspaces[0]["user_id"],
            "task_id": task_id,
            "task_workspace_id": task_workspace_id,
            "status": status,
            "ingestion_status": ingestion_status,
            "relative_path": relative_path,
            "media_type_hint": media_type_hint,
            "created_at": self.base_time + timedelta(minutes=len(self.artifacts)),
            "updated_at": self.base_time + timedelta(minutes=len(self.artifacts)),
        }
        self.artifacts.append(artifact)
        return artifact

    def list_task_artifacts(self) -> list[dict[str, object]]:
        return sorted(self.artifacts, key=lambda artifact: (artifact["created_at"], artifact["id"]))

    def get_task_artifact_optional(self, task_artifact_id: UUID) -> dict[str, object] | None:
        return next((artifact for artifact in self.artifacts if artifact["id"] == task_artifact_id), None)


def test_ensure_artifact_path_is_rooted_rejects_escape() -> None:
    with pytest.raises(TaskArtifactValidationError, match="escapes workspace root"):
        ensure_artifact_path_is_rooted(
            workspace_path=Path("/tmp/alicebot/task-workspaces/user/task"),
            artifact_path=Path("/tmp/alicebot/task-workspaces/user/task/../escape.txt"),
        )


def test_build_workspace_relative_artifact_path_returns_posix_path() -> None:
    relative_path = build_workspace_relative_artifact_path(
        workspace_path=Path("/tmp/alicebot/task-workspaces/user/task"),
        artifact_path=Path("/tmp/alicebot/task-workspaces/user/task/docs/spec.txt"),
    )

    assert relative_path == "docs/spec.txt"


def test_register_task_artifact_record_persists_relative_path_and_returns_record(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("spec")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )

    response = register_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactRegisterInput(
            task_workspace_id=task_workspace_id,
            local_path=str(artifact_path),
            media_type_hint="text/plain",
        ),
    )

    assert response == {
        "artifact": {
            "id": response["artifact"]["id"],
            "task_id": str(task_id),
            "task_workspace_id": str(task_workspace_id),
            "status": "registered",
            "ingestion_status": "pending",
            "relative_path": "docs/spec.txt",
            "media_type_hint": "text/plain",
            "created_at": "2026-03-13T10:00:00+00:00",
            "updated_at": "2026-03-13T10:00:00+00:00",
        }
    }
    assert store.locked_workspace_ids == [task_workspace_id]


def test_register_task_artifact_record_rejects_duplicate_relative_path(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("spec")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )

    register_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactRegisterInput(
            task_workspace_id=task_workspace_id,
            local_path=str(artifact_path),
            media_type_hint="text/plain",
        ),
    )

    with pytest.raises(
        TaskArtifactAlreadyExistsError,
        match=f"artifact docs/spec.txt is already registered for task workspace {task_workspace_id}",
    ):
        register_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactRegisterInput(
                task_workspace_id=task_workspace_id,
                local_path=str(artifact_path),
                media_type_hint="text/plain",
            ),
        )


def test_register_task_artifact_record_requires_visible_workspace(tmp_path) -> None:
    artifact_path = tmp_path / "spec.txt"
    artifact_path.write_text("spec")

    with pytest.raises(TaskWorkspaceNotFoundError, match="was not found"):
        register_task_artifact_record(
            ArtifactStoreStub(),
            user_id=uuid4(),
            request=TaskArtifactRegisterInput(
                task_workspace_id=uuid4(),
                local_path=str(artifact_path),
                media_type_hint=None,
            ),
        )


def test_register_task_artifact_record_rejects_paths_outside_workspace(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    outside_path = tmp_path / "escape.txt"
    outside_path.write_text("escape")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )

    with pytest.raises(TaskArtifactValidationError, match="escapes workspace root"):
        register_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactRegisterInput(
                task_workspace_id=task_workspace_id,
                local_path=str(outside_path),
                media_type_hint=None,
            ),
        )


def test_list_and_get_task_artifact_records_are_deterministic() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path="/tmp/alicebot/task-workspaces/user/task",
    )
    first = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/a.txt",
        media_type_hint="text/plain",
    )
    second = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/b.txt",
        media_type_hint=None,
    )

    assert list_task_artifact_records(store, user_id=user_id) == {
        "items": [
            serialize_task_artifact_row(first),
            serialize_task_artifact_row(second),
        ],
        "summary": {
            "total_count": 2,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert get_task_artifact_record(
        store,
        user_id=user_id,
        task_artifact_id=first["id"],
    ) == {"artifact": serialize_task_artifact_row(first)}


def test_get_task_artifact_record_raises_when_artifact_is_missing() -> None:
    with pytest.raises(TaskArtifactNotFoundError, match="was not found"):
        get_task_artifact_record(
            ArtifactStoreStub(),
            user_id=uuid4(),
            task_artifact_id=uuid4(),
        )
