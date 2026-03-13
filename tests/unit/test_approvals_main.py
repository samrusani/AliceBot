from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.approvals import ApprovalNotFoundError, ApprovalResolutionConflictError
from alicebot_api.tasks import TaskStepApprovalLinkageError
from alicebot_api.tools import ToolRoutingValidationError


def test_create_approval_request_endpoint_translates_request_and_returns_trace_payload(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    tool_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_submit_approval_request(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "request": {
                "thread_id": str(thread_id),
                "tool_id": str(tool_id),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": None,
                "risk_hint": None,
                "attributes": {"command": "ls"},
            },
            "decision": "approval_required",
            "tool": {"id": str(tool_id), "tool_key": "shell.exec"},
            "reasons": [],
            "approval": {
                "id": "approval-123",
                "thread_id": str(thread_id),
                "task_step_id": "task-step-123",
                "status": "pending",
                "resolution": None,
                "request": {
                    "thread_id": str(thread_id),
                    "tool_id": str(tool_id),
                    "action": "tool.run",
                    "scope": "workspace",
                    "domain_hint": None,
                    "risk_hint": None,
                    "attributes": {"command": "ls"},
                },
                "tool": {"id": str(tool_id), "tool_key": "shell.exec"},
                "routing": {
                    "decision": "approval_required",
                    "reasons": [],
                    "trace": {"trace_id": "routing-trace-123", "trace_event_count": 3},
                },
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            "routing_trace": {"trace_id": "routing-trace-123", "trace_event_count": 3},
            "trace": {"trace_id": "approval-trace-123", "trace_event_count": 4},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "submit_approval_request", fake_submit_approval_request)

    response = main_module.create_approval_request(
        main_module.CreateApprovalRequest(
            user_id=user_id,
            thread_id=thread_id,
            tool_id=tool_id,
            action="tool.run",
            scope="workspace",
            attributes={"command": "ls"},
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["trace"] == {
        "trace_id": "approval-trace-123",
        "trace_event_count": 4,
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].thread_id == thread_id
    assert captured["request"].tool_id == tool_id
    assert captured["request"].attributes == {"command": "ls"}


def test_create_approval_request_endpoint_maps_validation_errors_to_400(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_submit_approval_request(*_args, **_kwargs):
        raise ToolRoutingValidationError("tool_id must reference an existing active tool owned by the user")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "submit_approval_request", fake_submit_approval_request)

    response = main_module.create_approval_request(
        main_module.CreateApprovalRequest(
            user_id=user_id,
            thread_id=uuid4(),
            tool_id=uuid4(),
            action="tool.run",
            scope="workspace",
            attributes={},
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "tool_id must reference an existing active tool owned by the user"
    }


def test_list_approvals_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_approval_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = main_module.list_approvals(user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
    }


def test_get_approval_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_approval_record(*_args, **_kwargs):
        raise ApprovalNotFoundError(f"approval {approval_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_approval_record", fake_get_approval_record)

    response = main_module.get_approval(approval_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"approval {approval_id} was not found"}


def test_approve_approval_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_approve_approval_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "approval": {
                "id": str(approval_id),
                "thread_id": "thread-123",
                "task_step_id": "task-step-123",
                "status": "approved",
                "resolution": {
                    "resolved_at": "2026-03-12T10:00:00+00:00",
                    "resolved_by_user_id": str(user_id),
                },
                "request": {"thread_id": "thread-123", "tool_id": "tool-123"},
                "tool": {"id": "tool-123", "tool_key": "shell.exec"},
                "routing": {
                    "decision": "approval_required",
                    "reasons": [],
                    "trace": {"trace_id": "routing-trace-123", "trace_event_count": 3},
                },
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            "trace": {"trace_id": "approval-resolution-trace-123", "trace_event_count": 3},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "approve_approval_record", fake_approve_approval_record)

    response = main_module.approve_approval(
        approval_id,
        main_module.ResolveApprovalRequest(user_id=user_id),
    )

    assert response.status_code == 200
    assert json.loads(response.body)["trace"] == {
        "trace_id": "approval-resolution-trace-123",
        "trace_event_count": 3,
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].approval_id == approval_id


def test_approve_approval_endpoint_maps_conflicts_to_409(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_approve_approval_record(*_args, **_kwargs):
        raise ApprovalResolutionConflictError(f"approval {approval_id} was already approved")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "approve_approval_record", fake_approve_approval_record)

    response = main_module.approve_approval(
        approval_id,
        main_module.ResolveApprovalRequest(user_id=user_id),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {"detail": f"approval {approval_id} was already approved"}


def test_approve_approval_endpoint_maps_linkage_errors_to_409(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_approve_approval_record(*_args, **_kwargs):
        raise TaskStepApprovalLinkageError(
            f"approval {approval_id} is inconsistent with linked task step task-step-123"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "approve_approval_record", fake_approve_approval_record)

    response = main_module.approve_approval(
        approval_id,
        main_module.ResolveApprovalRequest(user_id=user_id),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"approval {approval_id} is inconsistent with linked task step task-step-123"
    }


def test_reject_approval_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_reject_approval_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "approval": {
                "id": str(approval_id),
                "thread_id": "thread-123",
                "task_step_id": "task-step-456",
                "status": "rejected",
                "resolution": {
                    "resolved_at": "2026-03-12T10:01:00+00:00",
                    "resolved_by_user_id": str(user_id),
                },
                "request": {"thread_id": "thread-123", "tool_id": "tool-123"},
                "tool": {"id": "tool-123", "tool_key": "shell.exec"},
                "routing": {
                    "decision": "approval_required",
                    "reasons": [],
                    "trace": {"trace_id": "routing-trace-123", "trace_event_count": 3},
                },
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            "trace": {"trace_id": "approval-resolution-trace-456", "trace_event_count": 3},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "reject_approval_record", fake_reject_approval_record)

    response = main_module.reject_approval(
        approval_id,
        main_module.ResolveApprovalRequest(user_id=user_id),
    )

    assert response.status_code == 200
    assert json.loads(response.body)["trace"] == {
        "trace_id": "approval-resolution-trace-456",
        "trace_event_count": 3,
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].approval_id == approval_id


def test_reject_approval_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    approval_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_reject_approval_record(*_args, **_kwargs):
        raise ApprovalNotFoundError(f"approval {approval_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "reject_approval_record", fake_reject_approval_record)

    response = main_module.reject_approval(
        approval_id,
        main_module.ResolveApprovalRequest(user_id=user_id),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"approval {approval_id} was not found"}
