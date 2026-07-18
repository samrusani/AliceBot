from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

from alicebot_api.routers import legacy_gated as legacy_gated_router
from alicebot_api.config import Settings
from alicebot_api.tasks import TaskNotFoundError
from alicebot_api.workspaces import TaskWorkspaceAlreadyExistsError, TaskWorkspaceNotFoundError


def test_list_task_workspaces_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        legacy_gated_router,
        "list_task_workspace_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = legacy_gated_router.list_task_workspaces(user_id)

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

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(legacy_gated_router, "get_task_workspace_record", fake_get_task_workspace_record)

    response = legacy_gated_router.get_task_workspace(task_workspace_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": {"code": "not_found", "message": "The requested resource was not found"}
    }


def test_create_task_workspace_endpoint_maps_task_not_found_to_404(monkeypatch) -> None:
    task_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_task_workspace_record(*_args, **_kwargs):
        raise TaskNotFoundError(f"task {task_id} was not found")

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(legacy_gated_router, "create_task_workspace_record", fake_create_task_workspace_record)

    response = legacy_gated_router.create_task_workspace(
        task_id,
        legacy_gated_router.CreateTaskWorkspaceRequest(user_id=user_id),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": {"code": "not_found", "message": "The requested resource was not found"}
    }


def test_create_task_workspace_endpoint_maps_duplicate_to_409(monkeypatch) -> None:
    task_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_task_workspace_record(*_args, **_kwargs):
        raise TaskWorkspaceAlreadyExistsError(f"task {task_id} already has active workspace workspace-123")

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(legacy_gated_router, "create_task_workspace_record", fake_create_task_workspace_record)

    response = legacy_gated_router.create_task_workspace(
        task_id,
        legacy_gated_router.CreateTaskWorkspaceRequest(user_id=user_id),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": {"code": "conflict", "message": "The request conflicts with the current resource state"}
    }
