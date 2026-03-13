from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.approvals import ApprovalNotFoundError
from alicebot_api.proxy_execution import (
    ProxyExecutionApprovalStateError,
    ProxyExecutionHandlerNotFoundError,
)
from alicebot_api.tasks import TaskStepApprovalLinkageError


def test_execute_approved_proxy_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_execute_approved_proxy_request(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "request": {"approval_id": str(approval_id), "task_step_id": "task-step-123"},
            "approval": {
                "id": str(approval_id),
                "thread_id": "thread-123",
                "task_step_id": "task-step-123",
                "status": "approved",
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
                "routing": {
                    "decision": "approval_required",
                    "reasons": [],
                    "trace": {"trace_id": "routing-trace-123", "trace_event_count": 3},
                },
                "created_at": "2026-03-13T09:00:00+00:00",
                "resolution": {
                    "resolved_at": "2026-03-13T09:30:00+00:00",
                    "resolved_by_user_id": str(user_id),
                },
            },
            "tool": {"id": "tool-123", "tool_key": "proxy.echo"},
            "result": {
                "handler_key": "proxy.echo",
                "status": "completed",
                "output": {"mode": "no_side_effect"},
            },
            "events": {
                "request_event_id": "event-request-123",
                "request_sequence_no": 1,
                "result_event_id": "event-result-123",
                "result_sequence_no": 2,
            },
            "trace": {"trace_id": "proxy-trace-123", "trace_event_count": 5},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "execute_approved_proxy_request", fake_execute_approved_proxy_request)

    response = main_module.execute_approved_proxy(
        approval_id,
        main_module.ExecuteApprovedProxyRequest(user_id=user_id),
    )

    assert response.status_code == 200
    assert json.loads(response.body)["request"] == {
        "approval_id": str(approval_id),
        "task_step_id": "task-step-123",
    }
    assert json.loads(response.body)["trace"] == {
        "trace_id": "proxy-trace-123",
        "trace_event_count": 5,
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].approval_id == approval_id


def test_execute_approved_proxy_endpoint_maps_missing_approval_to_404(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_execute_approved_proxy_request(*_args, **_kwargs):
        raise ApprovalNotFoundError(f"approval {approval_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "execute_approved_proxy_request", fake_execute_approved_proxy_request)

    response = main_module.execute_approved_proxy(
        approval_id,
        main_module.ExecuteApprovedProxyRequest(user_id=user_id),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"approval {approval_id} was not found"}


def test_execute_approved_proxy_endpoint_maps_blocked_approval_to_409(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_execute_approved_proxy_request(*_args, **_kwargs):
        raise ProxyExecutionApprovalStateError(
            f"approval {approval_id} is pending and cannot be executed"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "execute_approved_proxy_request", fake_execute_approved_proxy_request)

    response = main_module.execute_approved_proxy(
        approval_id,
        main_module.ExecuteApprovedProxyRequest(user_id=user_id),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"approval {approval_id} is pending and cannot be executed"
    }


def test_execute_approved_proxy_endpoint_maps_missing_handler_to_409(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_execute_approved_proxy_request(*_args, **_kwargs):
        raise ProxyExecutionHandlerNotFoundError(
            "tool 'proxy.missing' has no registered proxy handler"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "execute_approved_proxy_request", fake_execute_approved_proxy_request)

    response = main_module.execute_approved_proxy(
        approval_id,
        main_module.ExecuteApprovedProxyRequest(user_id=user_id),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": "tool 'proxy.missing' has no registered proxy handler"
    }


def test_execute_approved_proxy_endpoint_maps_linkage_error_to_409(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_execute_approved_proxy_request(*_args, **_kwargs):
        raise TaskStepApprovalLinkageError(
            f"approval {approval_id} is missing linked task_step_id"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "execute_approved_proxy_request", fake_execute_approved_proxy_request)

    response = main_module.execute_approved_proxy(
        approval_id,
        main_module.ExecuteApprovedProxyRequest(user_id=user_id),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"approval {approval_id} is missing linked task_step_id"
    }


def test_execute_approved_proxy_endpoint_returns_budget_blocked_payload(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_execute_approved_proxy_request(*_args, **_kwargs):
        return {
            "request": {"approval_id": str(approval_id), "task_step_id": "task-step-123"},
            "approval": {
                "id": str(approval_id),
                "thread_id": "thread-123",
                "task_step_id": "task-step-123",
                "status": "approved",
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
                "routing": {
                    "decision": "approval_required",
                    "reasons": [],
                    "trace": {"trace_id": "routing-trace-123", "trace_event_count": 3},
                },
                "created_at": "2026-03-13T09:00:00+00:00",
                "resolution": {
                    "resolved_at": "2026-03-13T09:30:00+00:00",
                    "resolved_by_user_id": str(user_id),
                },
            },
            "tool": {"id": "tool-123", "tool_key": "proxy.echo"},
            "result": {
                "handler_key": None,
                "status": "blocked",
                "output": None,
                "reason": "execution budget budget-123 blocks execution: projected completed executions 2 would exceed limit 1",
                "budget_decision": {
                    "matched_budget_id": "budget-123",
                    "tool_key": "proxy.echo",
                    "domain_hint": None,
                    "budget_tool_key": "proxy.echo",
                    "budget_domain_hint": None,
                    "max_completed_executions": 1,
                    "rolling_window_seconds": None,
                    "count_scope": "lifetime",
                    "window_started_at": None,
                    "completed_execution_count": 1,
                    "projected_completed_execution_count": 2,
                    "decision": "block",
                    "reason": "budget_exceeded",
                    "order": ["specificity_desc", "created_at_asc", "id_asc"],
                    "history_order": ["executed_at_asc", "id_asc"],
                },
            },
            "events": None,
            "trace": {"trace_id": "proxy-trace-456", "trace_event_count": 5},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "execute_approved_proxy_request", fake_execute_approved_proxy_request)

    response = main_module.execute_approved_proxy(
        approval_id,
        main_module.ExecuteApprovedProxyRequest(user_id=user_id),
    )

    assert response.status_code == 200
    assert json.loads(response.body)["events"] is None
