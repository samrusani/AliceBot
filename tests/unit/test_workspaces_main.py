from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.tasks import TaskNotFoundError
from alicebot_api.workspaces import TaskWorkspaceAlreadyExistsError, TaskWorkspaceNotFoundError


def test_list_task_workspaces_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_task_workspace_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = main_module.list_task_workspaces(user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
    }


def test_get_task_workspace_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_task_workspace_record(*_args, **_kwargs):
        raise TaskWorkspaceNotFoundError(f"task workspace {task_workspace_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_task_workspace_record", fake_get_task_workspace_record)

    response = main_module.get_task_workspace(task_workspace_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task workspace {task_workspace_id} was not found"}


def test_create_task_workspace_endpoint_maps_task_not_found_to_404(monkeypatch) -> None:
    task_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_task_workspace_record(*_args, **_kwargs):
        raise TaskNotFoundError(f"task {task_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_task_workspace_record", fake_create_task_workspace_record)

    response = main_module.create_task_workspace(
        task_id,
        main_module.CreateTaskWorkspaceRequest(user_id=user_id),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task {task_id} was not found"}


def test_create_task_workspace_endpoint_maps_duplicate_to_409(monkeypatch) -> None:
    task_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_task_workspace_record(*_args, **_kwargs):
        raise TaskWorkspaceAlreadyExistsError(f"task {task_id} already has active workspace workspace-123")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_task_workspace_record", fake_create_task_workspace_record)

    response = main_module.create_task_workspace(
        task_id,
        main_module.CreateTaskWorkspaceRequest(user_id=user_id),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"task {task_id} already has active workspace workspace-123"
    }
