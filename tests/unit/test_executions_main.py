from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.executions import ToolExecutionNotFoundError


def test_list_tool_executions_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_tool_execution_records(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "items": [
                {
                    "id": "execution-123",
                    "approval_id": "approval-123",
                    "task_step_id": "task-step-123",
                    "thread_id": "thread-123",
                    "tool_id": "tool-123",
                    "trace_id": "trace-123",
                    "request_event_id": "event-1",
                    "result_event_id": "event-2",
                    "status": "completed",
                    "handler_key": "proxy.echo",
                    "request": {
                        "thread_id": "thread-123",
                        "tool_id": "tool-123",
                        "action": "tool.run",
                        "scope": "workspace",
                        "domain_hint": None,
                        "risk_hint": None,
                        "attributes": {"message": "hello"},
                    },
                    "tool": {"id": "tool-123", "tool_key": "proxy.echo"},
                    "result": {
                        "handler_key": "proxy.echo",
                        "status": "completed",
                        "output": {"mode": "no_side_effect"},
                        "reason": None,
                    },
                    "executed_at": "2026-03-13T10:00:00+00:00",
                }
            ],
            "summary": {"total_count": 1, "order": ["executed_at_asc", "id_asc"]},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_tool_execution_records", fake_list_tool_execution_records)

    response = main_module.list_tool_executions(user_id)

    assert response.status_code == 200
    assert json.loads(response.body)["summary"] == {
        "total_count": 1,
        "order": ["executed_at_asc", "id_asc"],
    }
    assert captured == {
        "database_url": "postgresql://app",
        "current_user_id": user_id,
        "store_type": "ContinuityStore",
        "user_id": user_id,
    }


def test_get_tool_execution_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    execution_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_tool_execution_record(store, *, user_id, execution_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["execution_id"] = execution_id
        return {
            "execution": {
                "id": str(execution_id),
                "approval_id": "approval-123",
                "task_step_id": "task-step-123",
                "thread_id": "thread-123",
                "tool_id": "tool-123",
                "trace_id": "trace-123",
                "request_event_id": "event-1",
                "result_event_id": "event-2",
                "status": "completed",
                "handler_key": "proxy.echo",
                "request": {
                    "thread_id": "thread-123",
                    "tool_id": "tool-123",
                    "action": "tool.run",
                    "scope": "workspace",
                    "domain_hint": None,
                    "risk_hint": None,
                    "attributes": {"message": "hello"},
                },
                "tool": {"id": "tool-123", "tool_key": "proxy.echo"},
                "result": {
                    "handler_key": "proxy.echo",
                    "status": "completed",
                    "output": {"mode": "no_side_effect"},
                    "reason": None,
                },
                "executed_at": "2026-03-13T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_tool_execution_record", fake_get_tool_execution_record)

    response = main_module.get_tool_execution(execution_id, user_id)

    assert response.status_code == 200
    assert json.loads(response.body)["execution"]["id"] == str(execution_id)
    assert captured == {
        "database_url": "postgresql://app",
        "current_user_id": user_id,
        "store_type": "ContinuityStore",
        "user_id": user_id,
        "execution_id": execution_id,
    }


def test_get_tool_execution_endpoint_maps_missing_record_to_404(monkeypatch) -> None:
    user_id = uuid4()
    execution_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_tool_execution_record(*_args, **_kwargs):
        raise ToolExecutionNotFoundError(f"tool execution {execution_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_tool_execution_record", fake_get_tool_execution_record)

    response = main_module.get_tool_execution(execution_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"tool execution {execution_id} was not found"
    }
