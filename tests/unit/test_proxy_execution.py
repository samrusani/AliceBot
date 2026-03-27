from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.approvals import ApprovalNotFoundError
from alicebot_api.contracts import DEFAULT_AGENT_PROFILE_ID, ProxyExecutionRequestInput
from alicebot_api.proxy_execution import (
    PROXY_EXECUTION_REQUEST_EVENT_KIND,
    PROXY_EXECUTION_RESULT_EVENT_KIND,
    ProxyExecutionApprovalStateError,
    ProxyExecutionHandlerNotFoundError,
    execute_approved_proxy_request,
    registered_proxy_handler_keys,
)


class ProxyExecutionStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 9, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.thread_id = uuid4()
        self.agent_profiles = {DEFAULT_AGENT_PROFILE_ID}
        self.thread_profiles: dict[UUID, str] = {
            self.thread_id: DEFAULT_AGENT_PROFILE_ID,
        }
        self.locked_task_ids: list[UUID] = []
        self.approvals: dict[UUID, dict[str, object]] = {}
        self.tasks: list[dict[str, object]] = []
        self.task_runs: list[dict[str, object]] = []
        self.task_steps: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.tool_executions: list[dict[str, object]] = []
        self.execution_budgets: list[dict[str, object]] = []
        self.traces: list[dict[str, object]] = []
        self.trace_events: list[dict[str, object]] = []

    def current_time(self) -> datetime:
        return self.base_time + timedelta(minutes=len(self.tool_executions))

    def seed_approval(self, *, status: str, tool_key: str) -> dict[str, object]:
        approval_id = uuid4()
        tool_id = uuid4()
        created_at = self.base_time + timedelta(minutes=len(self.approvals))
        approval = {
            "id": approval_id,
            "user_id": self.user_id,
            "thread_id": self.thread_id,
            "tool_id": tool_id,
            "task_step_id": None,
            "status": status,
            "request": {
                "thread_id": str(self.thread_id),
                "tool_id": str(tool_id),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": None,
                "risk_hint": None,
                "attributes": {"message": "hello", "count": 2},
            },
            "tool": {
                "id": str(tool_id),
                "tool_key": tool_key,
                "name": "Proxy Echo" if tool_key == "proxy.echo" else "Unregistered Proxy",
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
                "created_at": created_at.isoformat(),
            },
            "routing": {
                "decision": "approval_required",
                "reasons": [],
                "trace": {"trace_id": str(uuid4()), "trace_event_count": 3},
            },
            "routing_trace_id": uuid4(),
            "created_at": created_at,
            "resolved_at": None if status == "pending" else created_at + timedelta(minutes=30),
            "resolved_by_user_id": None if status == "pending" else self.user_id,
        }
        self.approvals[approval_id] = approval
        task = self.create_task(
            thread_id=self.thread_id,
            tool_id=tool_id,
            status={
                "pending": "pending_approval",
                "approved": "approved",
                "rejected": "denied",
            }[status],
            request=approval["request"],
            tool=approval["tool"],
            latest_approval_id=approval_id,
            latest_execution_id=None,
        )
        task_step = self.create_task_step(
            task_id=task["id"],
            sequence_no=1,
            kind="governed_request",
            status={
                "pending": "created",
                "approved": "approved",
                "rejected": "denied",
            }[status],
            request=approval["request"],
            outcome={
                "routing_decision": "approval_required",
                "approval_id": str(approval_id),
                "approval_status": status,
                "execution_id": None,
                "execution_status": None,
                "blocked_reason": None,
            },
            trace_id=uuid4(),
            trace_kind="approval.request" if status == "pending" else "approval.resolve",
        )
        approval["task_step_id"] = task_step["id"]
        return approval

    def seed_execution_budget(
        self,
        *,
        agent_profile_id: str | None = None,
        tool_key: str | None,
        domain_hint: str | None,
        max_completed_executions: int,
        rolling_window_seconds: int | None = None,
        supersedes_budget_id: UUID | None = None,
    ) -> dict[str, object]:
        row = {
            "id": uuid4(),
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
            "created_at": self.base_time + timedelta(minutes=len(self.execution_budgets)),
        }
        self.execution_budgets.append(row)
        self.execution_budgets.sort(key=lambda item: (item["created_at"], item["id"]))
        return row

    def get_approval_optional(self, approval_id: UUID) -> dict[str, object] | None:
        return self.approvals.get(approval_id)

    def get_thread_optional(self, thread_id: UUID) -> dict[str, object] | None:
        profile_id = self.thread_profiles.get(thread_id)
        if profile_id is None:
            return None
        return {
            "id": thread_id,
            "user_id": self.user_id,
            "title": "Proxy execution thread",
            "agent_profile_id": profile_id,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }

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

    def create_task(
        self,
        *,
        thread_id: UUID,
        tool_id: UUID,
        status: str,
        request: dict[str, object],
        tool: dict[str, object],
        latest_approval_id: UUID | None,
        latest_execution_id: UUID | None,
    ) -> dict[str, object]:
        task = {
            "id": uuid4(),
            "user_id": self.user_id,
            "thread_id": thread_id,
            "tool_id": tool_id,
            "status": status,
            "request": request,
            "tool": tool,
            "latest_approval_id": latest_approval_id,
            "latest_execution_id": latest_execution_id,
            "created_at": self.base_time + timedelta(minutes=len(self.tasks)),
            "updated_at": self.base_time + timedelta(minutes=len(self.tasks)),
        }
        self.tasks.append(task)
        return task

    def get_task_by_approval_optional(self, approval_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["latest_approval_id"] == approval_id), None)

    def get_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["id"] == task_id), None)

    def create_task_run(
        self,
        *,
        task_id: UUID,
        status: str,
        checkpoint: dict[str, object],
        tick_count: int,
        step_count: int,
        max_ticks: int,
        retry_count: int = 0,
        retry_cap: int = 1,
        retry_posture: str = "none",
        failure_class: str | None = None,
        stop_reason: str | None = None,
    ) -> dict[str, object]:
        row = {
            "id": uuid4(),
            "user_id": self.user_id,
            "task_id": task_id,
            "status": status,
            "checkpoint": checkpoint,
            "tick_count": tick_count,
            "step_count": step_count,
            "max_ticks": max_ticks,
            "retry_count": retry_count,
            "retry_cap": retry_cap,
            "retry_posture": retry_posture,
            "failure_class": failure_class,
            "stop_reason": stop_reason,
            "last_transitioned_at": self.base_time + timedelta(minutes=len(self.task_runs)),
            "created_at": self.base_time + timedelta(minutes=len(self.task_runs)),
            "updated_at": self.base_time + timedelta(minutes=len(self.task_runs)),
        }
        self.task_runs.append(row)
        return row

    def get_task_run_optional(self, task_run_id: UUID) -> dict[str, object] | None:
        return next((run for run in self.task_runs if run["id"] == task_run_id), None)

    def update_task_run_optional(
        self,
        *,
        task_run_id: UUID,
        status: str,
        checkpoint: dict[str, object],
        tick_count: int,
        step_count: int,
        retry_count: int,
        retry_cap: int,
        retry_posture: str,
        failure_class: str | None,
        stop_reason: str | None,
    ) -> dict[str, object] | None:
        run = self.get_task_run_optional(task_run_id)
        if run is None:
            return None
        run["status"] = status
        run["checkpoint"] = checkpoint
        run["tick_count"] = tick_count
        run["step_count"] = step_count
        run["retry_count"] = retry_count
        run["retry_cap"] = retry_cap
        run["retry_posture"] = retry_posture
        run["failure_class"] = failure_class
        run["stop_reason"] = stop_reason
        run["last_transitioned_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        run["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return run

    def get_task_step_optional(self, task_step_id: UUID) -> dict[str, object] | None:
        return next((task_step for task_step in self.task_steps if task_step["id"] == task_step_id), None)

    def lock_task_steps(self, task_id: UUID) -> None:
        self.locked_task_ids.append(task_id)

    def update_task_execution_by_approval_optional(
        self,
        *,
        approval_id: UUID,
        latest_execution_id: UUID,
        status: str,
    ) -> dict[str, object] | None:
        task = self.get_task_by_approval_optional(approval_id)
        if task is None:
            return None
        task["status"] = status
        task["latest_execution_id"] = latest_execution_id
        task["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return task

    def append_event(
        self,
        thread_id: UUID,
        session_id: UUID | None,
        kind: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        event = {
            "id": uuid4(),
            "user_id": self.user_id,
            "thread_id": thread_id,
            "session_id": session_id,
            "sequence_no": len(self.events) + 1,
            "kind": kind,
            "payload": payload,
            "created_at": self.base_time + timedelta(minutes=len(self.events)),
        }
        self.events.append(event)
        return event

    def create_task_step(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
        parent_step_id: UUID | None = None,
        source_approval_id: UUID | None = None,
        source_execution_id: UUID | None = None,
        kind: str,
        status: str,
        request: dict[str, object],
        outcome: dict[str, object],
        trace_id: UUID,
        trace_kind: str,
    ) -> dict[str, object]:
        task_step = {
            "id": uuid4(),
            "user_id": self.user_id,
            "task_id": task_id,
            "sequence_no": sequence_no,
            "parent_step_id": parent_step_id,
            "source_approval_id": source_approval_id,
            "source_execution_id": source_execution_id,
            "kind": kind,
            "status": status,
            "request": request,
            "outcome": outcome,
            "trace_id": trace_id,
            "trace_kind": trace_kind,
            "created_at": self.base_time + timedelta(minutes=len(self.task_steps)),
            "updated_at": self.base_time + timedelta(minutes=len(self.task_steps)),
        }
        self.task_steps.append(task_step)
        return task_step

    def get_task_step_for_task_sequence_optional(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
    ) -> dict[str, object] | None:
        return next(
            (
                task_step
                for task_step in self.task_steps
                if task_step["task_id"] == task_id and task_step["sequence_no"] == sequence_no
            ),
            None,
        )

    def list_task_steps_for_task(self, task_id: UUID) -> list[dict[str, object]]:
        return sorted(
            [task_step for task_step in self.task_steps if task_step["task_id"] == task_id],
            key=lambda task_step: (task_step["sequence_no"], task_step["created_at"], task_step["id"]),
        )

    def update_task_step_for_task_sequence_optional(
        self,
        *,
        task_id: UUID,
        sequence_no: int,
        status: str,
        outcome: dict[str, object],
        trace_id: UUID,
        trace_kind: str,
    ) -> dict[str, object] | None:
        task_step = self.get_task_step_for_task_sequence_optional(task_id=task_id, sequence_no=sequence_no)
        if task_step is None:
            return None
        task_step["status"] = status
        task_step["outcome"] = outcome
        task_step["trace_id"] = trace_id
        task_step["trace_kind"] = trace_kind
        task_step["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return task_step

    def update_task_step_optional(
        self,
        *,
        task_step_id: UUID,
        status: str,
        outcome: dict[str, object],
        trace_id: UUID,
        trace_kind: str,
    ) -> dict[str, object] | None:
        task_step = self.get_task_step_optional(task_step_id)
        if task_step is None:
            return None
        task_step["status"] = status
        task_step["outcome"] = outcome
        task_step["trace_id"] = trace_id
        task_step["trace_kind"] = trace_kind
        task_step["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return task_step

    def create_tool_execution(
        self,
        *,
        approval_id: UUID,
        task_step_id: UUID,
        thread_id: UUID,
        tool_id: UUID,
        trace_id: UUID,
        request_event_id: UUID | None,
        result_event_id: UUID | None,
        status: str,
        handler_key: str | None,
        request: dict[str, object],
        tool: dict[str, object],
        result: dict[str, object],
    ) -> dict[str, object]:
        execution = {
            "id": uuid4(),
            "user_id": self.user_id,
            "approval_id": approval_id,
            "task_step_id": task_step_id,
            "thread_id": thread_id,
            "tool_id": tool_id,
            "trace_id": trace_id,
            "request_event_id": request_event_id,
            "result_event_id": result_event_id,
            "status": status,
            "handler_key": handler_key,
            "request": request,
            "tool": tool,
            "result": result,
            "executed_at": self.base_time + timedelta(minutes=len(self.tool_executions)),
        }
        self.tool_executions.append(execution)
        return execution

    def list_execution_budgets(self) -> list[dict[str, object]]:
        return list(self.execution_budgets)

    def list_tool_executions(self) -> list[dict[str, object]]:
        return list(self.tool_executions)


def test_execute_approved_proxy_request_returns_result_and_persists_events() -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.echo")

    payload = execute_approved_proxy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ProxyExecutionRequestInput(approval_id=approval["id"]),
    )

    assert list(payload) == ["request", "approval", "tool", "result", "events", "trace"]
    assert payload["request"] == {
        "approval_id": str(approval["id"]),
        "task_step_id": str(approval["task_step_id"]),
    }
    assert payload["approval"]["status"] == "approved"
    assert payload["tool"]["tool_key"] == "proxy.echo"
    assert payload["result"] == {
        "handler_key": "proxy.echo",
        "status": "completed",
        "output": {
            "mode": "no_side_effect",
            "tool_key": "proxy.echo",
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {"message": "hello", "count": 2},
        },
    }
    assert payload["events"]["request_sequence_no"] == 1
    assert payload["events"]["result_sequence_no"] == 2
    assert payload["trace"]["trace_event_count"] == 9
    assert len(store.tool_executions) == 1
    assert store.tool_executions[0]["approval_id"] == approval["id"]
    assert store.tool_executions[0]["task_step_id"] == approval["task_step_id"]
    assert store.tool_executions[0]["trace_id"] == UUID(payload["trace"]["trace_id"])
    assert store.tool_executions[0]["handler_key"] == "proxy.echo"
    assert store.tasks[0]["status"] == "executed"
    assert store.task_steps[0]["status"] == "executed"
    assert store.tasks[0]["latest_execution_id"] == store.tool_executions[0]["id"]
    assert store.tool_executions[0]["result"] == {
        "handler_key": "proxy.echo",
        "status": "completed",
        "output": payload["result"]["output"],
        "reason": None,
    }
    assert [event["kind"] for event in store.events] == [
        PROXY_EXECUTION_REQUEST_EVENT_KIND,
        PROXY_EXECUTION_RESULT_EVENT_KIND,
    ]
    assert [event["kind"] for event in store.trace_events] == [
        "tool.proxy.execute.request",
        "tool.proxy.execute.approval",
        "tool.proxy.execute.budget",
        "tool.proxy.execute.dispatch",
        "tool.proxy.execute.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]


def test_execute_approved_proxy_request_locks_task_steps_before_persisting_execution_state() -> None:
    class LockingProxyExecutionStoreStub(ProxyExecutionStoreStub):
        def list_task_steps_for_task(self, task_id: UUID) -> list[dict[str, object]]:
            if task_id not in self.locked_task_ids:
                raise AssertionError("task-step boundary was checked before the task-step lock was taken")
            return super().list_task_steps_for_task(task_id)

        def create_tool_execution(
            self,
            *,
            approval_id: UUID,
            task_step_id: UUID,
            thread_id: UUID,
            tool_id: UUID,
            trace_id: UUID,
            request_event_id: UUID | None,
            result_event_id: UUID | None,
            status: str,
            handler_key: str | None,
            request: dict[str, object],
            tool: dict[str, object],
            result: dict[str, object],
        ) -> dict[str, object]:
            task = self.get_task_by_approval_optional(approval_id)
            if task is None:
                raise AssertionError("expected task for approval before execution persistence")
            if task["id"] not in self.locked_task_ids:
                raise AssertionError("tool execution persisted before the task-step lock was taken")
            return super().create_tool_execution(
                approval_id=approval_id,
                task_step_id=task_step_id,
                thread_id=thread_id,
                tool_id=tool_id,
                trace_id=trace_id,
                request_event_id=request_event_id,
                result_event_id=result_event_id,
                status=status,
                handler_key=handler_key,
                request=request,
                tool=tool,
                result=result,
            )

    store = LockingProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.echo")

    payload = execute_approved_proxy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ProxyExecutionRequestInput(approval_id=approval["id"]),
    )

    assert payload["result"]["status"] == "completed"
    assert store.tasks[0]["id"] in store.locked_task_ids


def test_execute_approved_proxy_request_updates_the_linked_later_step_without_mutating_the_original_step() -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.echo")
    task = store.tasks[0]
    first_step = store.task_steps[0]
    initial_execution_id = uuid4()
    task["status"] = "pending_approval"
    task["latest_execution_id"] = None
    first_step["status"] = "executed"
    first_step["outcome"] = {
        "routing_decision": "approval_required",
        "approval_id": str(approval["id"]),
        "approval_status": "approved",
        "execution_id": str(initial_execution_id),
        "execution_status": "completed",
        "blocked_reason": None,
    }
    later_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=2,
        parent_step_id=first_step["id"],
        source_approval_id=approval["id"],
        source_execution_id=initial_execution_id,
        kind="governed_request",
        status="created",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(approval["id"]),
            "approval_status": "approved",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="task.step.continuation",
    )

    original_first_trace_id = first_step["trace_id"]
    original_first_outcome = dict(first_step["outcome"])
    original_later_trace_id = later_step["trace_id"]
    approval["task_step_id"] = later_step["id"]

    payload = execute_approved_proxy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ProxyExecutionRequestInput(approval_id=approval["id"]),
    )

    assert payload["result"]["status"] == "completed"
    assert task["status"] == "executed"
    assert task["latest_execution_id"] == store.tool_executions[0]["id"]
    assert first_step["status"] == "executed"
    assert first_step["trace_id"] == original_first_trace_id
    assert first_step["outcome"] == original_first_outcome
    assert later_step["status"] == "executed"
    assert later_step["trace_id"] == UUID(payload["trace"]["trace_id"])
    assert later_step["trace_id"] != original_later_trace_id
    assert later_step["outcome"]["execution_id"] == str(store.tool_executions[0]["id"])
    assert later_step["outcome"]["execution_status"] == "completed"
    assert store.tool_executions[0]["task_step_id"] == later_step["id"]
    assert store.events[0]["payload"]["task_step_id"] == str(later_step["id"])
    assert store.events[1]["payload"]["task_step_id"] == str(later_step["id"])
    assert store.trace_events[0]["payload"] == {
        "approval_id": str(approval["id"]),
        "task_step_id": str(later_step["id"]),
    }
    assert store.trace_events[3]["payload"]["task_step_id"] == str(later_step["id"])
    assert store.trace_events[4]["payload"]["task_step_id"] == str(later_step["id"])


@pytest.mark.parametrize("status", ["pending", "rejected"])
def test_execute_approved_proxy_request_rejects_non_approved_statuses(status: str) -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status=status, tool_key="proxy.echo")

    with pytest.raises(
        ProxyExecutionApprovalStateError,
        match=rf"approval {approval['id']} is {status} and cannot be executed",
    ):
        execute_approved_proxy_request(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ProxyExecutionRequestInput(approval_id=approval["id"]),
        )

    assert store.events == []
    assert store.tool_executions == []
    assert [event["kind"] for event in store.trace_events] == [
        "tool.proxy.execute.request",
        "tool.proxy.execute.approval",
        "tool.proxy.execute.dispatch",
        "tool.proxy.execute.summary",
    ]
    assert store.trace_events[2]["payload"]["dispatch_status"] == "blocked"
    assert store.trace_events[3]["payload"]["execution_status"] == "blocked"


def test_execute_approved_proxy_request_rejects_missing_handlers() -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.missing")

    with pytest.raises(
        ProxyExecutionHandlerNotFoundError,
        match="tool 'proxy.missing' has no registered proxy handler",
    ):
        execute_approved_proxy_request(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ProxyExecutionRequestInput(approval_id=approval["id"]),
        )

    assert store.events == []
    assert len(store.tool_executions) == 1
    assert store.tool_executions[0]["status"] == "blocked"
    assert store.tool_executions[0]["task_step_id"] == approval["task_step_id"]
    assert store.tool_executions[0]["handler_key"] is None
    assert store.tool_executions[0]["request_event_id"] is None
    assert store.tool_executions[0]["result_event_id"] is None
    assert store.tasks[0]["status"] == "blocked"
    assert store.task_steps[0]["status"] == "blocked"
    assert store.tasks[0]["latest_execution_id"] == store.tool_executions[0]["id"]
    assert store.tool_executions[0]["result"] == {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": "tool 'proxy.missing' has no registered proxy handler",
    }
    assert store.trace_events[2]["payload"]["decision"] == "allow"
    assert store.trace_events[3]["payload"] == {
        "approval_id": str(approval["id"]),
        "task_step_id": str(approval["task_step_id"]),
        "tool_id": approval["tool"]["id"],
        "tool_key": "proxy.missing",
        "handler_key": None,
        "dispatch_status": "blocked",
        "reason": "tool 'proxy.missing' has no registered proxy handler",
        "result_status": "blocked",
        "output": None,
    }
    assert [event["kind"] for event in store.trace_events] == [
        "tool.proxy.execute.request",
        "tool.proxy.execute.approval",
        "tool.proxy.execute.budget",
        "tool.proxy.execute.dispatch",
        "tool.proxy.execute.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]


def test_execute_approved_proxy_request_returns_blocked_budget_response_and_persists_review_record() -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.echo")
    budget = store.seed_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=1,
    )
    store.create_tool_execution(
        approval_id=uuid4(),
        task_step_id=uuid4(),
        thread_id=store.thread_id,
        tool_id=UUID(approval["tool"]["id"]),
        trace_id=uuid4(),
        request_event_id=uuid4(),
        result_event_id=uuid4(),
        status="completed",
        handler_key="proxy.echo",
        request={
            "thread_id": str(store.thread_id),
            "tool_id": approval["tool"]["id"],
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {"message": "seed"},
        },
        tool=approval["tool"],
        result={
            "handler_key": "proxy.echo",
            "status": "completed",
            "output": {"mode": "no_side_effect"},
            "reason": None,
        },
    )

    payload = execute_approved_proxy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ProxyExecutionRequestInput(approval_id=approval["id"]),
    )

    assert payload["events"] is None
    assert payload["trace"]["trace_event_count"] == 9
    assert payload["result"] == {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": (
            f"execution budget {budget['id']} blocks execution: projected completed executions "
            "2 would exceed limit 1"
        ),
        "budget_decision": {
            "matched_budget_id": str(budget["id"]),
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
    assert len(store.events) == 0
    assert len(store.tool_executions) == 2
    assert store.tool_executions[-1]["status"] == "blocked"
    assert store.tool_executions[-1]["request_event_id"] is None
    assert store.tool_executions[-1]["result_event_id"] is None
    assert store.tasks[0]["status"] == "blocked"
    assert store.task_steps[0]["status"] == "blocked"
    assert store.tasks[0]["latest_execution_id"] == store.tool_executions[-1]["id"]
    assert store.tool_executions[-1]["result"] == payload["result"]
    assert [event["kind"] for event in store.trace_events] == [
        "tool.proxy.execute.request",
        "tool.proxy.execute.approval",
        "tool.proxy.execute.budget",
        "tool.proxy.execute.dispatch",
        "tool.proxy.execute.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]
    assert store.trace_events[2]["payload"] == payload["result"]["budget_decision"]


def test_execute_approved_proxy_request_fail_closes_when_budget_context_is_invalid() -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.echo")
    approval["request"]["thread_id"] = "not-a-uuid"  # type: ignore[index]

    payload = execute_approved_proxy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ProxyExecutionRequestInput(approval_id=approval["id"]),
    )

    assert payload["events"] is None
    assert payload["result"] == {
        "handler_key": None,
        "status": "blocked",
        "output": None,
        "reason": (
            "execution budget invariance blocks execution: invalid request thread/profile "
            "context: request.thread_id 'not-a-uuid' is not a valid UUID"
        ),
        "budget_decision": {
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
        },
    }
    assert store.events == []
    assert len(store.tool_executions) == 1
    assert store.tool_executions[0]["status"] == "blocked"
    assert store.tool_executions[0]["result"] == payload["result"]
    assert [event["kind"] for event in store.trace_events] == [
        "tool.proxy.execute.request",
        "tool.proxy.execute.approval",
        "tool.proxy.execute.budget",
        "tool.proxy.execute.dispatch",
        "tool.proxy.execute.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]
    assert store.trace_events[2]["payload"] == payload["result"]["budget_decision"]
    assert store.trace_events[3]["payload"]["budget_context"] == {
        "request_thread_id": "not-a-uuid",
        "context_resolution": "invalid",
        "context_reason": "request.thread_id 'not-a-uuid' is not a valid UUID",
    }


def test_execute_approved_proxy_request_rejects_missing_visible_approval() -> None:
    store = ProxyExecutionStoreStub()

    with pytest.raises(ApprovalNotFoundError, match="was not found"):
        execute_approved_proxy_request(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ProxyExecutionRequestInput(approval_id=uuid4()),
        )


def test_execute_approved_proxy_request_marks_linked_run_budget_blocked_as_failed() -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.echo")
    run = store.create_task_run(
        task_id=store.tasks[0]["id"],
        status="queued",
        checkpoint={
            "cursor": 0,
            "target_steps": 1,
            "wait_for_signal": False,
        },
        tick_count=1,
        step_count=0,
        max_ticks=3,
        stop_reason=None,
    )
    approval["task_run_id"] = run["id"]
    store.seed_execution_budget(
        tool_key="proxy.echo",
        domain_hint=None,
        max_completed_executions=1,
    )
    store.create_tool_execution(
        approval_id=uuid4(),
        task_step_id=uuid4(),
        thread_id=store.thread_id,
        tool_id=UUID(approval["tool"]["id"]),
        trace_id=uuid4(),
        request_event_id=uuid4(),
        result_event_id=uuid4(),
        status="completed",
        handler_key="proxy.echo",
        request={
            "thread_id": str(store.thread_id),
            "tool_id": approval["tool"]["id"],
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {"message": "seed"},
        },
        tool=approval["tool"],
        result={
            "handler_key": "proxy.echo",
            "status": "completed",
            "output": {"mode": "no_side_effect"},
            "reason": None,
        },
    )

    payload = execute_approved_proxy_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ProxyExecutionRequestInput(approval_id=approval["id"]),
    )

    assert payload["result"]["status"] == "blocked"
    assert store.task_runs[0]["status"] == "failed"
    assert store.task_runs[0]["stop_reason"] == "budget_exhausted"
    assert store.task_runs[0]["failure_class"] == "budget"
    assert store.task_runs[0]["retry_posture"] == "terminal"
    assert store.task_runs[0]["checkpoint"]["last_execution_status"] == "blocked"
    assert store.task_runs[0]["checkpoint"]["resolved_approval_id"] == str(approval["id"])


def test_execute_approved_proxy_request_marks_linked_run_missing_handler_as_failed() -> None:
    store = ProxyExecutionStoreStub()
    approval = store.seed_approval(status="approved", tool_key="proxy.missing")
    run = store.create_task_run(
        task_id=store.tasks[0]["id"],
        status="queued",
        checkpoint={
            "cursor": 0,
            "target_steps": 1,
            "wait_for_signal": False,
        },
        tick_count=1,
        step_count=0,
        max_ticks=3,
        stop_reason=None,
    )
    approval["task_run_id"] = run["id"]

    with pytest.raises(
        ProxyExecutionHandlerNotFoundError,
        match="tool 'proxy.missing' has no registered proxy handler",
    ):
        execute_approved_proxy_request(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ProxyExecutionRequestInput(approval_id=approval["id"]),
        )

    assert store.task_runs[0]["status"] == "failed"
    assert store.task_runs[0]["stop_reason"] == "policy_blocked"
    assert store.task_runs[0]["failure_class"] == "policy"
    assert store.task_runs[0]["retry_posture"] == "terminal"
    assert store.task_runs[0]["checkpoint"]["last_execution_status"] == "blocked"
    assert store.task_runs[0]["checkpoint"]["resolved_approval_id"] == str(approval["id"])


def test_registered_proxy_handler_keys_are_sorted_and_explicit() -> None:
    assert registered_proxy_handler_keys() == (
        "proxy.calendar.draft_event",
        "proxy.echo",
        "proxy.thread_audit",
    )
