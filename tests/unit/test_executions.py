from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.executions import (
    ToolExecutionNotFoundError,
    get_tool_execution_record,
    list_tool_execution_records,
)


class ToolExecutionStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 10, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.thread_id = uuid4()
        self.executions: list[dict[str, object]] = []

    def seed_execution(self, *, tool_key: str, offset_minutes: int) -> dict[str, object]:
        tool_id = uuid4()
        execution = {
            "id": uuid4(),
            "user_id": self.user_id,
            "approval_id": uuid4(),
            "task_step_id": uuid4(),
            "thread_id": self.thread_id,
            "tool_id": tool_id,
            "trace_id": uuid4(),
            "request_event_id": uuid4(),
            "result_event_id": uuid4(),
            "status": "completed",
            "handler_key": tool_key,
            "request": {
                "thread_id": str(self.thread_id),
                "tool_id": str(tool_id),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": None,
                "risk_hint": None,
                "attributes": {"message": tool_key},
            },
            "tool": {
                "id": str(tool_id),
                "tool_key": tool_key,
                "name": "Proxy Echo",
                "description": "Deterministic proxy handler.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["proxy"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": [],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
                "created_at": (self.base_time + timedelta(minutes=offset_minutes)).isoformat(),
            },
            "result": {
                "handler_key": tool_key,
                "status": "completed",
                "output": {"mode": "no_side_effect", "tool_key": tool_key},
                "reason": None,
            },
            "executed_at": self.base_time + timedelta(minutes=offset_minutes),
        }
        self.executions.append(execution)
        self.executions.sort(key=lambda row: (row["executed_at"], row["id"]))
        return execution

    def seed_blocked_execution(self, *, tool_key: str, offset_minutes: int) -> dict[str, object]:
        tool_id = uuid4()
        execution = {
            "id": uuid4(),
            "user_id": self.user_id,
            "approval_id": uuid4(),
            "task_step_id": uuid4(),
            "thread_id": self.thread_id,
            "tool_id": tool_id,
            "trace_id": uuid4(),
            "request_event_id": None,
            "result_event_id": None,
            "status": "blocked",
            "handler_key": None,
            "request": {
                "thread_id": str(self.thread_id),
                "tool_id": str(tool_id),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": None,
                "risk_hint": None,
                "attributes": {"message": tool_key},
            },
            "tool": {
                "id": str(tool_id),
                "tool_key": tool_key,
                "name": "Missing Proxy",
                "description": "Missing handler.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["proxy"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": [],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
                "created_at": (self.base_time + timedelta(minutes=offset_minutes)).isoformat(),
            },
            "result": {
                "handler_key": None,
                "status": "blocked",
                "output": None,
                "reason": f"tool '{tool_key}' has no registered proxy handler",
            },
            "executed_at": self.base_time + timedelta(minutes=offset_minutes),
        }
        self.executions.append(execution)
        self.executions.sort(key=lambda row: (row["executed_at"], row["id"]))
        return execution

    def list_tool_executions(self) -> list[dict[str, object]]:
        return list(self.executions)

    def get_tool_execution_optional(self, execution_id: UUID) -> dict[str, object] | None:
        return next((row for row in self.executions if row["id"] == execution_id), None)


def test_list_tool_execution_records_uses_explicit_order_and_summary() -> None:
    store = ToolExecutionStoreStub()
    first = store.seed_execution(tool_key="proxy.echo", offset_minutes=0)
    second = store.seed_execution(tool_key="proxy.echo", offset_minutes=5)

    payload = list_tool_execution_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
    )

    assert [item["id"] for item in payload["items"]] == [str(first["id"]), str(second["id"])]
    assert payload["summary"] == {
        "total_count": 2,
        "order": ["executed_at_asc", "id_asc"],
    }


def test_get_tool_execution_record_returns_detail_shape() -> None:
    store = ToolExecutionStoreStub()
    execution = store.seed_execution(tool_key="proxy.echo", offset_minutes=0)

    payload = get_tool_execution_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        execution_id=execution["id"],
    )

    assert payload["execution"]["id"] == str(execution["id"])
    assert payload["execution"]["approval_id"] == str(execution["approval_id"])
    assert payload["execution"]["task_step_id"] == str(execution["task_step_id"])
    assert payload["execution"]["status"] == "completed"
    assert payload["execution"]["tool"]["tool_key"] == "proxy.echo"
    assert payload["execution"]["result"]["output"] == {
        "mode": "no_side_effect",
        "tool_key": "proxy.echo",
    }


def test_get_tool_execution_record_preserves_blocked_attempt_shape() -> None:
    store = ToolExecutionStoreStub()
    execution = store.seed_blocked_execution(tool_key="proxy.missing", offset_minutes=0)

    payload = get_tool_execution_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        execution_id=execution["id"],
    )

    assert payload["execution"]["status"] == "blocked"
    assert payload["execution"]["handler_key"] is None
    assert payload["execution"]["request_event_id"] is None
    assert payload["execution"]["result_event_id"] is None
    assert payload["execution"]["result"] == {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": "tool 'proxy.missing' has no registered proxy handler",
    }


def test_get_tool_execution_record_preserves_budget_blocked_attempt_shape() -> None:
    store = ToolExecutionStoreStub()
    execution = store.seed_blocked_execution(tool_key="proxy.echo", offset_minutes=0)
    execution["result"] = {
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
    }

    payload = get_tool_execution_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        execution_id=execution["id"],
    )

    assert payload["execution"]["result"]["budget_decision"] == {
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
    }


def test_get_tool_execution_record_raises_clear_error_when_missing() -> None:
    store = ToolExecutionStoreStub()

    with pytest.raises(ToolExecutionNotFoundError, match="tool execution .* was not found"):
        get_tool_execution_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            execution_id=uuid4(),
        )
