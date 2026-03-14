from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.artifacts import (
    TaskArtifactAlreadyExistsError,
    TaskArtifactNotFoundError,
    TaskArtifactValidationError,
)
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


def test_list_task_artifacts_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_task_artifact_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = main_module.list_task_artifacts(user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
    }


def test_get_task_artifact_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_artifact_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_task_artifact_record", fake_get_task_artifact_record)

    response = main_module.get_task_artifact(task_artifact_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task artifact {task_artifact_id} was not found"}


def test_register_task_artifact_endpoint_maps_workspace_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_register_task_artifact_record(*_args, **_kwargs):
        raise TaskWorkspaceNotFoundError(f"task workspace {task_workspace_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "register_task_artifact_record", fake_register_task_artifact_record)

    response = main_module.register_task_artifact(
        task_workspace_id,
        main_module.RegisterTaskArtifactRequest(
            user_id=user_id,
            local_path="/tmp/example.txt",
        ),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task workspace {task_workspace_id} was not found"}


def test_register_task_artifact_endpoint_maps_validation_to_400(monkeypatch) -> None:
    user_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_register_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactValidationError("artifact path /tmp/escape.txt escapes workspace root /tmp/workspace")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "register_task_artifact_record", fake_register_task_artifact_record)

    response = main_module.register_task_artifact(
        task_workspace_id,
        main_module.RegisterTaskArtifactRequest(
            user_id=user_id,
            local_path="/tmp/escape.txt",
        ),
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "artifact path /tmp/escape.txt escapes workspace root /tmp/workspace"
    }


def test_register_task_artifact_endpoint_maps_duplicate_to_409(monkeypatch) -> None:
    user_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_register_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactAlreadyExistsError(
            f"artifact docs/spec.txt is already registered for task workspace {task_workspace_id}"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "register_task_artifact_record", fake_register_task_artifact_record)

    response = main_module.register_task_artifact(
        task_workspace_id,
        main_module.RegisterTaskArtifactRequest(
            user_id=user_id,
            local_path="/tmp/docs/spec.txt",
        ),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"artifact docs/spec.txt is already registered for task workspace {task_workspace_id}"
    }
