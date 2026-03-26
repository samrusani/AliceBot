from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import (
    DEFAULT_AGENT_PROFILE_ID,
    ExecutionBudgetCreateInput,
    ExecutionBudgetDeactivateInput,
    ExecutionBudgetSupersedeInput,
)
from alicebot_api.execution_budgets import (
    ExecutionBudgetLifecycleError,
    ExecutionBudgetNotFoundError,
    ExecutionBudgetValidationError,
    create_execution_budget_record,
    deactivate_execution_budget_record,
    evaluate_execution_budget,
    get_execution_budget_record,
    list_execution_budget_records,
    supersede_execution_budget_record,
)


class _SavepointConnection:
    def __init__(self, store: "ExecutionBudgetStoreStub") -> None:
        self.store = store

    def transaction(self) -> "_Savepoint":
        return _Savepoint(self.store)


class _Savepoint:
    def __init__(self, store: "ExecutionBudgetStoreStub") -> None:
        self.store = store
        self.snapshot: list[dict[str, object]] | None = None

    def __enter__(self) -> "_Savepoint":
        self.snapshot = [dict(row) for row in self.store.budgets]
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None and self.snapshot is not None:
            self.store.budgets = [dict(row) for row in self.snapshot]
        return False


class ExecutionBudgetStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 11, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.thread_id = uuid4()
        self.agent_profiles = {DEFAULT_AGENT_PROFILE_ID, "coach_default"}
        self.thread_profiles: dict[UUID, str] = {
            self.thread_id: DEFAULT_AGENT_PROFILE_ID,
        }
        self.budgets: list[dict[str, object]] = []
        self.executions: list[dict[str, object]] = []
        self.traces: list[dict[str, object]] = []
        self.trace_events: list[dict[str, object]] = []
        self.fail_next_supersede_update = False
        self.conn = _SavepointConnection(self)

    def current_time(self) -> datetime:
        return self.base_time + timedelta(minutes=len(self.executions))

    def get_thread_optional(self, thread_id: UUID) -> dict[str, object] | None:
        if thread_id not in self.thread_profiles:
            return None
        return {
            "id": thread_id,
            "user_id": self.user_id,
            "title": "Budget lifecycle thread",
            "agent_profile_id": self.thread_profiles[thread_id],
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }

    def create_thread(self, *, agent_profile_id: str) -> UUID:
        thread_id = uuid4()
        self.thread_profiles[thread_id] = agent_profile_id
        return thread_id

    def get_agent_profile_optional(self, profile_id: str) -> dict[str, object] | None:
        if profile_id not in self.agent_profiles:
            return None
        return {
            "id": profile_id,
            "name": profile_id,
            "description": "",
            "model_provider": None,
            "model_name": None,
        }

    def create_trace(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        kind: str,
        compiler_version: str,
        status: str,
        limits: dict[str, object],
    ) -> dict[str, object]:
        trace = {
            "id": uuid4(),
            "user_id": user_id,
            "thread_id": thread_id,
            "kind": kind,
            "compiler_version": compiler_version,
            "status": status,
            "limits": limits,
            "created_at": self.base_time + timedelta(minutes=len(self.traces)),
        }
        self.traces.append(trace)
        return trace

    def append_trace_event(
        self,
        *,
        trace_id: UUID,
        sequence_no: int,
        kind: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        event = {
            "id": uuid4(),
            "trace_id": trace_id,
            "sequence_no": sequence_no,
            "kind": kind,
            "payload": payload,
            "created_at": self.base_time + timedelta(minutes=len(self.trace_events)),
        }
        self.trace_events.append(event)
        return event

    def create_execution_budget(
        self,
        *,
        budget_id: UUID | None = None,
        agent_profile_id: str | None = None,
        tool_key: str | None,
        domain_hint: str | None,
        max_completed_executions: int,
        rolling_window_seconds: int | None = None,
        supersedes_budget_id: UUID | None = None,
    ) -> dict[str, object]:
        row = {
            "id": uuid4() if budget_id is None else budget_id,
            "user_id": self.user_id,
            "agent_profile_id": agent_profile_id,
            "tool_key": tool_key,
            "domain_hint": domain_hint,
            "max_completed_executions": max_completed_executions,
            "rolling_window_seconds": rolling_window_seconds,
            "status": "active",
            "deactivated_at": None,
            "superseded_by_budget_id": None,
            "supersedes_budget_id": supersedes_budget_id,
            "created_at": self.base_time + timedelta(minutes=len(self.budgets)),
        }
        self.budgets.append(row)
        self.budgets.sort(key=lambda item: (item["created_at"], item["id"]))
        return row

    def deactivate_execution_budget_optional(
        self,
        execution_budget_id: UUID,
    ) -> dict[str, object] | None:
        row = self.get_execution_budget_optional(execution_budget_id)
        if row is None or row["status"] != "active":
            return None
        row["status"] = "inactive"
        row["deactivated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return row

    def supersede_execution_budget_optional(
        self,
        *,
        execution_budget_id: UUID,
        superseded_by_budget_id: UUID,
    ) -> dict[str, object] | None:
        if self.fail_next_supersede_update:
            self.fail_next_supersede_update = False
            return None
        row = self.get_execution_budget_optional(execution_budget_id)
        if row is None or row["status"] != "active":
            return None
        row["status"] = "superseded"
        row["deactivated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        row["superseded_by_budget_id"] = superseded_by_budget_id
        return row

    def get_execution_budget_optional(self, execution_budget_id: UUID) -> dict[str, object] | None:
        return next((row for row in self.budgets if row["id"] == execution_budget_id), None)

    def list_execution_budgets(self) -> list[dict[str, object]]:
        return list(self.budgets)

    def seed_execution(
        self,
        *,
        tool_key: str,
        domain_hint: str | None,
        status: str,
        offset_minutes: int,
        thread_id: UUID | None = None,
    ) -> None:
        execution_thread_id = self.thread_id if thread_id is None else thread_id
        tool_id = uuid4()
        self.executions.append(
            {
                "id": uuid4(),
                "user_id": self.user_id,
                "approval_id": uuid4(),
                "thread_id": execution_thread_id,
                "tool_id": tool_id,
                "trace_id": uuid4(),
                "request_event_id": None,
                "result_event_id": None,
                "status": status,
                "handler_key": None if status == "blocked" else tool_key,
                "request": {
                    "thread_id": str(execution_thread_id),
                    "tool_id": str(tool_id),
                    "action": "tool.run",
                    "scope": "workspace",
                    "domain_hint": domain_hint,
                    "risk_hint": None,
                    "attributes": {},
                },
                "tool": {
                    "id": str(tool_id),
                    "tool_key": tool_key,
                },
                "result": {
                    "handler_key": None if status == "blocked" else tool_key,
                    "status": status,
                    "output": None,
                    "reason": None,
                },
                "executed_at": self.base_time + timedelta(minutes=offset_minutes),
            }
        )

    def list_tool_executions(self) -> list[dict[str, object]]:
        return list(self.executions)


def test_create_execution_budget_requires_at_least_one_selector() -> None:
    store = ExecutionBudgetStoreStub()

    with pytest.raises(
        ExecutionBudgetValidationError,
        match="execution budget requires at least one selector: tool_key or domain_hint",
    ):
        create_execution_budget_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ExecutionBudgetCreateInput(
                tool_key=None,
                domain_hint=None,
                max_completed_executions=1,
            ),
        )


def test_create_execution_budget_rejects_duplicate_active_scope() -> None:
    store = ExecutionBudgetStoreStub()
    create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key="proxy.echo",
            domain_hint="docs",
            max_completed_executions=1,
        ),
    )

    with pytest.raises(
        ExecutionBudgetValidationError,
        match="active execution budget already exists for selector scope",
    ):
        create_execution_budget_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ExecutionBudgetCreateInput(
                tool_key="proxy.echo",
                domain_hint="docs",
                max_completed_executions=2,
            ),
        )


def test_create_execution_budget_allows_same_selector_across_profile_scopes() -> None:
    store = ExecutionBudgetStoreStub()
    default_budget = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            agent_profile_id=DEFAULT_AGENT_PROFILE_ID,
            tool_key="proxy.echo",
            domain_hint="docs",
            max_completed_executions=1,
        ),
    )
    global_budget = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            agent_profile_id=None,
            tool_key="proxy.echo",
            domain_hint="docs",
            max_completed_executions=2,
        ),
    )

    assert default_budget["execution_budget"]["agent_profile_id"] == DEFAULT_AGENT_PROFILE_ID
    assert global_budget["execution_budget"]["agent_profile_id"] is None
    assert len(store.budgets) == 2


def test_create_execution_budget_rejects_unknown_agent_profile_id() -> None:
    store = ExecutionBudgetStoreStub()

    with pytest.raises(
        ExecutionBudgetValidationError,
        match="agent_profile_id must reference an existing profile in the registry",
    ):
        create_execution_budget_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ExecutionBudgetCreateInput(
                agent_profile_id="profile_missing",
                tool_key="proxy.echo",
                domain_hint=None,
                max_completed_executions=1,
            ),
        )


def test_create_execution_budget_includes_optional_rolling_window_seconds() -> None:
    store = ExecutionBudgetStoreStub()

    payload = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key="proxy.echo",
            domain_hint=None,
            max_completed_executions=2,
            rolling_window_seconds=3600,
        ),
    )

    assert payload["execution_budget"]["rolling_window_seconds"] == 3600
    assert payload["execution_budget"]["agent_profile_id"] is None
    assert store.budgets[0]["rolling_window_seconds"] == 3600


def test_create_list_and_get_execution_budget_records_are_deterministic() -> None:
    store = ExecutionBudgetStoreStub()
    second = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key="proxy.echo",
            domain_hint=None,
            max_completed_executions=2,
        ),
    )
    first = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key=None,
            domain_hint="docs",
            max_completed_executions=1,
        ),
    )

    listed = list_execution_budget_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
    )
    detail = get_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        execution_budget_id=UUID(second["execution_budget"]["id"]),
    )

    assert [item["id"] for item in listed["items"]] == [
        second["execution_budget"]["id"],
        first["execution_budget"]["id"],
    ]
    assert listed["summary"] == {
        "total_count": 2,
        "order": ["created_at_asc", "id_asc"],
    }
    assert detail == {"execution_budget": second["execution_budget"]}
    assert detail["execution_budget"]["status"] == "active"
    assert detail["execution_budget"]["deactivated_at"] is None
    assert detail["execution_budget"]["rolling_window_seconds"] is None


def test_deactivate_execution_budget_marks_row_inactive_and_records_trace() -> None:
    store = ExecutionBudgetStoreStub()
    created = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key="proxy.echo",
            domain_hint=None,
            max_completed_executions=1,
        ),
    )

    payload = deactivate_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetDeactivateInput(
            thread_id=store.thread_id,
            execution_budget_id=UUID(created["execution_budget"]["id"]),
        ),
    )

    assert payload["execution_budget"]["status"] == "inactive"
    assert payload["execution_budget"]["deactivated_at"] == "2026-03-13T12:00:00+00:00"
    assert payload["trace"]["trace_event_count"] == 3
    assert store.traces[0]["kind"] == "execution_budget.lifecycle"
    assert store.traces[0]["compiler_version"] == "execution_budget_lifecycle_v0"
    assert [event["kind"] for event in store.trace_events] == [
        "execution_budget.lifecycle.request",
        "execution_budget.lifecycle.state",
        "execution_budget.lifecycle.summary",
    ]
    assert store.trace_events[1]["payload"] == {
        "execution_budget_id": created["execution_budget"]["id"],
        "requested_action": "deactivate",
        "previous_status": "active",
        "current_status": "inactive",
        "tool_key": "proxy.echo",
        "domain_hint": None,
        "max_completed_executions": 1,
        "rolling_window_seconds": None,
        "deactivated_at": "2026-03-13T12:00:00+00:00",
        "superseded_by_budget_id": None,
        "supersedes_budget_id": None,
        "replacement_budget_id": None,
        "replacement_status": None,
        "replacement_max_completed_executions": None,
        "replacement_rolling_window_seconds": None,
        "rejection_reason": None,
    }


def test_supersede_execution_budget_replaces_active_budget_and_records_trace() -> None:
    store = ExecutionBudgetStoreStub()
    created = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key="proxy.echo",
            domain_hint="docs",
            max_completed_executions=1,
        ),
    )

    payload = supersede_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetSupersedeInput(
            thread_id=store.thread_id,
            execution_budget_id=UUID(created["execution_budget"]["id"]),
            max_completed_executions=3,
        ),
    )

    assert payload["superseded_budget"]["status"] == "superseded"
    assert payload["replacement_budget"]["status"] == "active"
    assert payload["replacement_budget"]["max_completed_executions"] == 3
    assert payload["replacement_budget"]["tool_key"] == "proxy.echo"
    assert payload["replacement_budget"]["domain_hint"] == "docs"
    assert payload["replacement_budget"]["rolling_window_seconds"] is None
    assert payload["replacement_budget"]["supersedes_budget_id"] == created["execution_budget"]["id"]
    assert payload["superseded_budget"]["superseded_by_budget_id"] == payload["replacement_budget"]["id"]
    assert payload["trace"]["trace_event_count"] == 3
    assert store.trace_events[1]["payload"]["replacement_budget_id"] == payload["replacement_budget"]["id"]
    assert store.trace_events[2]["payload"] == {
        "execution_budget_id": created["execution_budget"]["id"],
        "requested_action": "supersede",
        "outcome": "superseded",
        "replacement_budget_id": payload["replacement_budget"]["id"],
        "active_budget_id": payload["replacement_budget"]["id"],
    }


def test_lifecycle_rejects_invalid_transition_and_records_trace() -> None:
    store = ExecutionBudgetStoreStub()
    created = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key="proxy.echo",
            domain_hint=None,
            max_completed_executions=1,
        ),
    )
    deactivate_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetDeactivateInput(
            thread_id=store.thread_id,
            execution_budget_id=UUID(created["execution_budget"]["id"]),
        ),
    )

    with pytest.raises(
        ExecutionBudgetLifecycleError,
        match=f"execution budget {created['execution_budget']['id']} is inactive and cannot be deactivated",
    ):
        deactivate_execution_budget_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ExecutionBudgetDeactivateInput(
                thread_id=store.thread_id,
                execution_budget_id=UUID(created["execution_budget"]["id"]),
            ),
        )

    assert store.trace_events[-2]["payload"]["current_status"] == "inactive"
    assert store.trace_events[-2]["payload"]["rejection_reason"] == (
        f"execution budget {created['execution_budget']['id']} is inactive and cannot be deactivated"
    )
    assert store.trace_events[-1]["payload"]["outcome"] == "rejected"


def test_supersede_execution_budget_rolls_back_replacement_when_source_update_fails() -> None:
    store = ExecutionBudgetStoreStub()
    created = create_execution_budget_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ExecutionBudgetCreateInput(
            tool_key="proxy.echo",
            domain_hint=None,
            max_completed_executions=1,
        ),
    )
    store.fail_next_supersede_update = True

    with pytest.raises(
        ExecutionBudgetLifecycleError,
        match=f"execution budget {created['execution_budget']['id']} could not be superseded",
    ):
        supersede_execution_budget_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ExecutionBudgetSupersedeInput(
                thread_id=store.thread_id,
                execution_budget_id=UUID(created["execution_budget"]["id"]),
                max_completed_executions=3,
            ),
        )

    assert len(store.budgets) == 1
    assert store.budgets[0]["id"] == UUID(created["execution_budget"]["id"])
    assert store.budgets[0]["status"] == "active"
    assert store.budgets[0]["superseded_by_budget_id"] is None
    assert store.trace_events[-1]["payload"]["outcome"] == "rejected"


def test_get_execution_budget_record_raises_clear_error_when_missing() -> None:
    store = ExecutionBudgetStoreStub()

    with pytest.raises(ExecutionBudgetNotFoundError, match="execution budget .* was not found"):
        get_execution_budget_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            execution_budget_id=uuid4(),
        )


def test_evaluate_execution_budget_fail_closed_when_request_thread_context_is_malformed() -> None:
    store = ExecutionBudgetStoreStub()
    store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=10,
    )

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": "not-a-uuid",
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record == {
        "matched_budget_id": None,
        "tool_key": "proxy.echo",
        "domain_hint": None,
        "budget_tool_key": None,
        "budget_domain_hint": None,
        "max_completed_executions": None,
        "rolling_window_seconds": None,
        "count_scope": "lifetime",
        "window_started_at": None,
        "completed_execution_count": 0,
        "projected_completed_execution_count": 1,
        "decision": "block",
        "reason": "invalid_request_context",
        "order": ["specificity_desc", "created_at_asc", "id_asc"],
        "history_order": ["executed_at_asc", "id_asc"],
        "request_thread_id": "not-a-uuid",
        "context_resolution": "invalid",
        "context_reason": "request.thread_id 'not-a-uuid' is not a valid UUID",
    }
    assert decision.blocked_result == {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": (
            "execution budget invariance blocks execution: invalid request "
            "thread/profile context: request.thread_id 'not-a-uuid' is not a valid UUID"
        ),
        "budget_decision": decision.record,
    }


def test_evaluate_execution_budget_fail_closed_when_request_thread_profile_is_unresolvable() -> None:
    store = ExecutionBudgetStoreStub()
    broken_thread_id = store.create_thread(agent_profile_id="profile_missing")
    store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=10,
    )

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(broken_thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record["decision"] == "block"
    assert decision.record["reason"] == "invalid_request_context"
    assert decision.record["request_thread_id"] == str(broken_thread_id)
    assert decision.record["context_resolution"] == "invalid"
    assert decision.record["context_reason"] == (
        f"request.thread_id '{broken_thread_id}' did not resolve to a visible "
        "thread/profile context"
    )
    assert decision.blocked_result is not None
    assert decision.blocked_result["status"] == "blocked"
    assert decision.blocked_result["reason"] == (
        "execution budget invariance blocks execution: invalid request thread/profile context: "
        f"request.thread_id '{broken_thread_id}' did not resolve to a visible thread/profile context"
    )


def test_evaluate_execution_budget_excludes_malformed_history_rows_from_profile_scoped_counts() -> None:
    store = ExecutionBudgetStoreStub()
    matched = store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=2,
    )
    store.seed_execution(tool_key="proxy.echo", domain_hint=None, status="completed", offset_minutes=0)
    store.seed_execution(tool_key="proxy.echo", domain_hint=None, status="completed", offset_minutes=1)
    store.seed_execution(tool_key="proxy.echo", domain_hint=None, status="completed", offset_minutes=2)
    malformed_thread_id_row = store.executions[1]
    malformed_thread_id_row["request"]["thread_id"] = "not-a-uuid"  # type: ignore[index]
    missing_thread_id_row = store.executions[2]
    missing_thread_id_row["request"].pop("thread_id")  # type: ignore[index]

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(store.thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record == {
        "matched_budget_id": str(matched["id"]),
        "tool_key": "proxy.echo",
        "domain_hint": None,
        "budget_tool_key": "proxy.echo",
        "budget_domain_hint": None,
        "max_completed_executions": 2,
        "rolling_window_seconds": None,
        "count_scope": "lifetime",
        "window_started_at": None,
        "completed_execution_count": 1,
        "projected_completed_execution_count": 2,
        "decision": "allow",
        "reason": "within_budget",
        "order": ["specificity_desc", "created_at_asc", "id_asc"],
        "history_order": ["executed_at_asc", "id_asc"],
    }
    assert decision.blocked_result is None


def test_evaluate_execution_budget_prefers_more_specific_active_match_and_ignores_inactive_rows() -> None:
    store = ExecutionBudgetStoreStub()
    inactive = store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint="docs",
        max_completed_executions=1,
    )
    store.deactivate_execution_budget_optional(inactive["id"])
    store.create_execution_budget(tool_key=None, domain_hint="docs", max_completed_executions=1)
    matched = store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint="docs",
        max_completed_executions=2,
    )
    store.seed_execution(tool_key="proxy.echo", domain_hint="docs", status="completed", offset_minutes=0)
    store.seed_execution(tool_key="proxy.echo", domain_hint="docs", status="blocked", offset_minutes=1)

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(store.thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": "docs",
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record == {
        "matched_budget_id": str(matched["id"]),
        "tool_key": "proxy.echo",
        "domain_hint": "docs",
        "budget_tool_key": "proxy.echo",
        "budget_domain_hint": "docs",
        "max_completed_executions": 2,
        "rolling_window_seconds": None,
        "count_scope": "lifetime",
        "window_started_at": None,
        "completed_execution_count": 1,
        "projected_completed_execution_count": 2,
        "decision": "allow",
        "reason": "within_budget",
        "order": ["specificity_desc", "created_at_asc", "id_asc"],
        "history_order": ["executed_at_asc", "id_asc"],
    }
    assert decision.blocked_result is None


def test_evaluate_execution_budget_prefers_profile_scoped_budget_before_global_fallback() -> None:
    store = ExecutionBudgetStoreStub()
    global_budget = store.create_execution_budget(
        agent_profile_id=None,
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=1,
    )
    profile_budget = store.create_execution_budget(
        agent_profile_id=DEFAULT_AGENT_PROFILE_ID,
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=2,
    )
    store.seed_execution(
        tool_key="proxy.echo",
        domain_hint=None,
        status="completed",
        offset_minutes=0,
        thread_id=store.thread_id,
    )

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(store.thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record["matched_budget_id"] == str(profile_budget["id"])
    assert decision.record["completed_execution_count"] == 1
    assert decision.record["projected_completed_execution_count"] == 2
    assert decision.record["reason"] == "within_budget"
    assert decision.blocked_result is None
    assert str(global_budget["id"]) != decision.record["matched_budget_id"]


def test_evaluate_execution_budget_global_fallback_counts_only_active_thread_profile_history() -> None:
    store = ExecutionBudgetStoreStub()
    coach_thread_id = store.create_thread(agent_profile_id="coach_default")
    global_budget = store.create_execution_budget(
        agent_profile_id=None,
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=1,
    )
    store.seed_execution(
        tool_key="proxy.echo",
        domain_hint=None,
        status="completed",
        offset_minutes=0,
        thread_id=store.thread_id,
    )

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(coach_thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record["matched_budget_id"] == str(global_budget["id"])
    assert decision.record["completed_execution_count"] == 0
    assert decision.record["projected_completed_execution_count"] == 1
    assert decision.record["reason"] == "within_budget"
    assert decision.blocked_result is None


def test_evaluate_execution_budget_blocks_when_projected_completed_count_would_exceed_limit() -> None:
    store = ExecutionBudgetStoreStub()
    matched = store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=1,
    )
    store.seed_execution(tool_key="proxy.echo", domain_hint=None, status="completed", offset_minutes=0)

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(store.thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record == {
        "matched_budget_id": str(matched["id"]),
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
    assert decision.blocked_result == {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": (
            f"execution budget {matched['id']} blocks execution: projected completed executions "
            "2 would exceed limit 1"
        ),
        "budget_decision": decision.record,
    }


def test_evaluate_execution_budget_uses_only_recent_completed_history_inside_window() -> None:
    store = ExecutionBudgetStoreStub()
    matched = store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=2,
        rolling_window_seconds=3600,
    )
    store.seed_execution(tool_key="proxy.echo", domain_hint=None, status="completed", offset_minutes=-120)
    store.seed_execution(tool_key="proxy.echo", domain_hint=None, status="completed", offset_minutes=-10)

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(store.thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record == {
        "matched_budget_id": str(matched["id"]),
        "tool_key": "proxy.echo",
        "domain_hint": None,
        "budget_tool_key": "proxy.echo",
        "budget_domain_hint": None,
        "max_completed_executions": 2,
        "rolling_window_seconds": 3600,
        "count_scope": "rolling_window",
        "window_started_at": "2026-03-13T10:02:00+00:00",
        "completed_execution_count": 1,
        "projected_completed_execution_count": 2,
        "decision": "allow",
        "reason": "within_budget",
        "order": ["specificity_desc", "created_at_asc", "id_asc"],
        "history_order": ["executed_at_asc", "id_asc"],
    }
    assert decision.blocked_result is None


def test_evaluate_execution_budget_blocks_when_recent_window_history_exceeds_limit() -> None:
    store = ExecutionBudgetStoreStub()
    matched = store.create_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=1,
        rolling_window_seconds=900,
    )
    store.seed_execution(tool_key="proxy.echo", domain_hint=None, status="completed", offset_minutes=-5)

    decision = evaluate_execution_budget(
        store,  # type: ignore[arg-type]
        tool={"id": str(uuid4()), "tool_key": "proxy.echo"},
        request={
            "thread_id": str(store.thread_id),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
    )

    assert decision.record == {
        "matched_budget_id": str(matched["id"]),
        "tool_key": "proxy.echo",
        "domain_hint": None,
        "budget_tool_key": "proxy.echo",
        "budget_domain_hint": None,
        "max_completed_executions": 1,
        "rolling_window_seconds": 900,
        "count_scope": "rolling_window",
        "window_started_at": "2026-03-13T10:46:00+00:00",
        "completed_execution_count": 1,
        "projected_completed_execution_count": 2,
        "decision": "block",
        "reason": "budget_exceeded",
        "order": ["specificity_desc", "created_at_asc", "id_asc"],
        "history_order": ["executed_at_asc", "id_asc"],
    }
    assert decision.blocked_result == {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": (
            f"execution budget {matched['id']} blocks execution: projected completed executions "
            "2 within rolling window 900 seconds would exceed limit 1"
        ),
        "budget_decision": decision.record,
    }
