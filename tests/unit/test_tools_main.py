from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.tools import (
    ToolAllowlistValidationError,
    ToolNotFoundError,
    ToolRoutingValidationError,
)


def test_create_tool_endpoint_translates_request_and_returns_created_status(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_tool_record(store, *, user_id, tool):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["tool"] = tool
        return {
            "tool": {
                "id": "tool-123",
                "tool_key": "browser.open",
                "name": "Browser Open",
                "description": "Open documentation pages.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["browser"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": ["docs"],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
                "created_at": "2026-03-12T09:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_tool_record", fake_create_tool_record)

    response = main_module.create_tool(
        main_module.CreateToolRequest(
            user_id=user_id,
            tool_key="browser.open",
            name="Browser Open",
            description="Open documentation pages.",
            version="1.0.0",
            action_hints=["tool.run"],
            scope_hints=["workspace"],
            domain_hints=["docs"],
            risk_hints=[],
            metadata={"transport": "proxy"},
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body)["tool"]["tool_key"] == "browser.open"
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["tool"].tool_key == "browser.open"
    assert captured["tool"].action_hints == ("tool.run",)
    assert captured["tool"].scope_hints == ("workspace",)


def test_get_tool_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    tool_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_tool_record(*_args, **_kwargs):
        raise ToolNotFoundError(f"tool {tool_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_tool_record", fake_get_tool_record)

    response = main_module.get_tool(tool_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"tool {tool_id} was not found"}


def test_evaluate_tool_allowlist_endpoint_translates_request_and_returns_trace_payload(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_evaluate_tool_allowlist(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "allowed": [],
            "denied": [],
            "approval_required": [],
            "summary": {
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": "docs",
                "risk_hint": None,
                "evaluated_tool_count": 0,
                "allowed_count": 0,
                "denied_count": 0,
                "approval_required_count": 0,
                "order": ["tool_key_asc", "version_asc", "created_at_asc", "id_asc"],
            },
            "trace": {"trace_id": "trace-123", "trace_event_count": 3},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "evaluate_tool_allowlist", fake_evaluate_tool_allowlist)

    response = main_module.evaluate_tools_allowlist(
        main_module.EvaluateToolAllowlistRequest(
            user_id=user_id,
            thread_id=thread_id,
            action="tool.run",
            scope="workspace",
            domain_hint="docs",
            attributes={"channel": "chat"},
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["trace"] == {"trace_id": "trace-123", "trace_event_count": 3}
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].thread_id == thread_id
    assert captured["request"].action == "tool.run"
    assert captured["request"].scope == "workspace"
    assert captured["request"].domain_hint == "docs"
    assert captured["request"].attributes == {"channel": "chat"}


def test_evaluate_tool_allowlist_endpoint_maps_validation_errors_to_400(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_evaluate_tool_allowlist(*_args, **_kwargs):
        raise ToolAllowlistValidationError("thread_id must reference an existing thread owned by the user")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "evaluate_tool_allowlist", fake_evaluate_tool_allowlist)

    response = main_module.evaluate_tools_allowlist(
        main_module.EvaluateToolAllowlistRequest(
            user_id=user_id,
            thread_id=uuid4(),
            action="tool.run",
            scope="workspace",
            attributes={},
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "thread_id must reference an existing thread owned by the user"
    }


def test_route_tool_endpoint_translates_request_and_returns_trace_payload(monkeypatch) -> None:
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

    def fake_route_tool_invocation(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "request": {
                "thread_id": str(thread_id),
                "tool_id": str(tool_id),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": "docs",
                "risk_hint": None,
                "attributes": {"channel": "chat"},
            },
            "decision": "ready",
            "tool": {
                "id": str(tool_id),
                "tool_key": "browser.open",
                "name": "Browser Open",
                "description": "Open documentation pages.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["browser"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": ["docs"],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            "reasons": [],
            "summary": {
                "thread_id": str(thread_id),
                "tool_id": str(tool_id),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": "docs",
                "risk_hint": None,
                "decision": "ready",
                "evaluated_tool_count": 1,
                "active_policy_count": 1,
                "consent_count": 1,
                "order": ["tool_key_asc", "version_asc", "created_at_asc", "id_asc"],
            },
            "trace": {"trace_id": "trace-123", "trace_event_count": 3},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "route_tool_invocation", fake_route_tool_invocation)

    response = main_module.route_tool(
        main_module.RouteToolRequest(
            user_id=user_id,
            thread_id=thread_id,
            tool_id=tool_id,
            action="tool.run",
            scope="workspace",
            domain_hint="docs",
            attributes={"channel": "chat"},
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["trace"] == {"trace_id": "trace-123", "trace_event_count": 3}
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["request"].thread_id == thread_id
    assert captured["request"].tool_id == tool_id
    assert captured["request"].action == "tool.run"
    assert captured["request"].scope == "workspace"
    assert captured["request"].domain_hint == "docs"
    assert captured["request"].attributes == {"channel": "chat"}


def test_route_tool_endpoint_maps_validation_errors_to_400(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_route_tool_invocation(*_args, **_kwargs):
        raise ToolRoutingValidationError("tool_id must reference an existing active tool owned by the user")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "route_tool_invocation", fake_route_tool_invocation)

    response = main_module.route_tool(
        main_module.RouteToolRequest(
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
