from __future__ import annotations

from typing import Any
from uuid import uuid4

from alicebot_api.store import ContinuityStore


class RecordingCursor:
    def __init__(self, fetchone_results: list[dict[str, Any]], fetchall_result: list[dict[str, Any]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_result = fetchall_result or []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        return self.fetchall_result


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def test_execution_budget_store_methods_use_expected_queries_and_parameters() -> None:
    execution_budget_id = uuid4()
    replacement_budget_id = uuid4()
    row = {
        "id": execution_budget_id,
        "agent_profile_id": None,
        "tool_key": "proxy.echo",
        "domain_hint": "docs",
        "max_completed_executions": 2,
        "rolling_window_seconds": 3600,
        "status": "active",
        "deactivated_at": None,
        "superseded_by_budget_id": None,
        "supersedes_budget_id": None,
        "created_at": "2026-03-13T11:00:00+00:00",
    }
    cursor = RecordingCursor(
        fetchone_results=[
            row,
            row,
            {**row, "status": "inactive"},
            {**row, "status": "superseded", "superseded_by_budget_id": replacement_budget_id},
        ],
        fetchall_result=[row],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_execution_budget(
        agent_profile_id=None,
        tool_key="proxy.echo",
        domain_hint="docs",
        max_completed_executions=2,
        rolling_window_seconds=3600,
    )
    fetched = store.get_execution_budget_optional(execution_budget_id)
    listed = store.list_execution_budgets()
    deactivated = store.deactivate_execution_budget_optional(execution_budget_id)
    superseded = store.supersede_execution_budget_optional(
        execution_budget_id=execution_budget_id,
        superseded_by_budget_id=replacement_budget_id,
    )

    assert created["id"] == execution_budget_id
    assert fetched is not None
    assert fetched["id"] == execution_budget_id
    assert listed[0]["id"] == execution_budget_id
    assert deactivated is not None
    assert deactivated["status"] == "inactive"
    assert superseded is not None
    assert superseded["superseded_by_budget_id"] == replacement_budget_id

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO execution_budgets" in create_query
    assert create_params == (None, None, "proxy.echo", "docs", 2, 3600, None)
    assert "FROM execution_budgets" in cursor.executed[1][0]
    assert "ORDER BY created_at ASC, id ASC" in cursor.executed[2][0]
    assert "UPDATE execution_budgets" in cursor.executed[3][0]
    assert cursor.executed[4][1] == (replacement_budget_id, execution_budget_id)
