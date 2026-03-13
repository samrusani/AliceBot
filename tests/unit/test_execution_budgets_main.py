from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.execution_budgets import (
    ExecutionBudgetLifecycleError,
    ExecutionBudgetNotFoundError,
    ExecutionBudgetValidationError,
)


def test_create_execution_budget_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_execution_budget_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "execution_budget": {
                "id": "budget-123",
                "tool_key": "proxy.echo",
                "domain_hint": None,
                "max_completed_executions": 1,
                "rolling_window_seconds": 3600,
                "status": "active",
                "deactivated_at": None,
                "superseded_by_budget_id": None,
                "supersedes_budget_id": None,
                "created_at": "2026-03-13T11:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_execution_budget_record", fake_create_execution_budget_record)

    response = main_module.create_execution_budget(
        main_module.CreateExecutionBudgetRequest(
            user_id=user_id,
            tool_key="proxy.echo",
            domain_hint=None,
            max_completed_executions=1,
            rolling_window_seconds=3600,
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body)["execution_budget"]["id"] == "budget-123"
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].tool_key == "proxy.echo"
    assert captured["request"].rolling_window_seconds == 3600


def test_create_execution_budget_endpoint_maps_validation_error_to_400(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_execution_budget_record(*_args, **_kwargs):
        raise ExecutionBudgetValidationError(
            "execution budget requires at least one selector: tool_key or domain_hint"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_execution_budget_record", fake_create_execution_budget_record)

    response = main_module.create_execution_budget(
        main_module.CreateExecutionBudgetRequest(
            user_id=user_id,
            tool_key=None,
            domain_hint="docs",
            max_completed_executions=1,
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "execution budget requires at least one selector: tool_key or domain_hint"
    }


def test_list_execution_budgets_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_execution_budget_records(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "items": [
                {
                    "id": "budget-123",
                    "tool_key": "proxy.echo",
                    "domain_hint": None,
                    "max_completed_executions": 1,
                    "rolling_window_seconds": None,
                    "status": "active",
                    "deactivated_at": None,
                    "superseded_by_budget_id": None,
                    "supersedes_budget_id": None,
                    "created_at": "2026-03-13T11:00:00+00:00",
                }
            ],
            "summary": {"total_count": 1, "order": ["created_at_asc", "id_asc"]},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_execution_budget_records", fake_list_execution_budget_records)

    response = main_module.list_execution_budgets(user_id)

    assert response.status_code == 200
    assert json.loads(response.body)["summary"] == {
        "total_count": 1,
        "order": ["created_at_asc", "id_asc"],
    }
    assert captured == {
        "database_url": "postgresql://app",
        "current_user_id": user_id,
        "store_type": "ContinuityStore",
        "user_id": user_id,
    }


def test_get_execution_budget_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    execution_budget_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_execution_budget_record(store, *, user_id, execution_budget_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["execution_budget_id"] = execution_budget_id
        return {
            "execution_budget": {
                "id": str(execution_budget_id),
                "tool_key": "proxy.echo",
                "domain_hint": None,
                "max_completed_executions": 1,
                "rolling_window_seconds": None,
                "status": "active",
                "deactivated_at": None,
                "superseded_by_budget_id": None,
                "supersedes_budget_id": None,
                "created_at": "2026-03-13T11:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_execution_budget_record", fake_get_execution_budget_record)

    response = main_module.get_execution_budget(execution_budget_id, user_id)

    assert response.status_code == 200
    assert json.loads(response.body)["execution_budget"]["id"] == str(execution_budget_id)
    assert captured == {
        "database_url": "postgresql://app",
        "current_user_id": user_id,
        "store_type": "ContinuityStore",
        "user_id": user_id,
        "execution_budget_id": execution_budget_id,
    }


def test_get_execution_budget_endpoint_maps_missing_record_to_404(monkeypatch) -> None:
    user_id = uuid4()
    execution_budget_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_execution_budget_record(*_args, **_kwargs):
        raise ExecutionBudgetNotFoundError(f"execution budget {execution_budget_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_execution_budget_record", fake_get_execution_budget_record)

    response = main_module.get_execution_budget(execution_budget_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"execution budget {execution_budget_id} was not found"
    }


def test_deactivate_execution_budget_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    execution_budget_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_deactivate_execution_budget_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "execution_budget": {
                "id": str(execution_budget_id),
                "tool_key": "proxy.echo",
                "domain_hint": None,
                "max_completed_executions": 1,
                "rolling_window_seconds": None,
                "status": "inactive",
                "deactivated_at": "2026-03-13T12:00:00+00:00",
                "superseded_by_budget_id": None,
                "supersedes_budget_id": None,
                "created_at": "2026-03-13T11:00:00+00:00",
            },
            "trace": {"trace_id": "trace-123", "trace_event_count": 3},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "deactivate_execution_budget_record", fake_deactivate_execution_budget_record)

    response = main_module.deactivate_execution_budget(
        execution_budget_id,
        main_module.DeactivateExecutionBudgetRequest(
            user_id=user_id,
            thread_id=thread_id,
        ),
    )

    assert response.status_code == 200
    assert json.loads(response.body)["execution_budget"]["status"] == "inactive"
    assert captured["request"].thread_id == thread_id
    assert captured["request"].execution_budget_id == execution_budget_id


def test_deactivate_execution_budget_endpoint_maps_lifecycle_error_to_409(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    execution_budget_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_deactivate_execution_budget_record(*_args, **_kwargs):
        raise ExecutionBudgetLifecycleError(
            f"execution budget {execution_budget_id} is inactive and cannot be deactivated"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "deactivate_execution_budget_record", fake_deactivate_execution_budget_record)

    response = main_module.deactivate_execution_budget(
        execution_budget_id,
        main_module.DeactivateExecutionBudgetRequest(
            user_id=user_id,
            thread_id=thread_id,
        ),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"execution budget {execution_budget_id} is inactive and cannot be deactivated"
    }


def test_supersede_execution_budget_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    execution_budget_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_supersede_execution_budget_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "superseded_budget": {
                "id": str(execution_budget_id),
                "tool_key": "proxy.echo",
                "domain_hint": None,
                "max_completed_executions": 1,
                "rolling_window_seconds": 1800,
                "status": "superseded",
                "deactivated_at": "2026-03-13T12:00:00+00:00",
                "superseded_by_budget_id": "budget-456",
                "supersedes_budget_id": None,
                "created_at": "2026-03-13T11:00:00+00:00",
            },
            "replacement_budget": {
                "id": "budget-456",
                "tool_key": "proxy.echo",
                "domain_hint": None,
                "max_completed_executions": 3,
                "rolling_window_seconds": 1800,
                "status": "active",
                "deactivated_at": None,
                "superseded_by_budget_id": None,
                "supersedes_budget_id": str(execution_budget_id),
                "created_at": "2026-03-13T11:01:00+00:00",
            },
            "trace": {"trace_id": "trace-456", "trace_event_count": 3},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "supersede_execution_budget_record", fake_supersede_execution_budget_record)

    response = main_module.supersede_execution_budget(
        execution_budget_id,
        main_module.SupersedeExecutionBudgetRequest(
            user_id=user_id,
            thread_id=thread_id,
            max_completed_executions=3,
        ),
    )

    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["superseded_budget"]["status"] == "superseded"
    assert body["replacement_budget"]["status"] == "active"
    assert captured["request"].thread_id == thread_id
    assert captured["request"].execution_budget_id == execution_budget_id
    assert captured["request"].max_completed_executions == 3
