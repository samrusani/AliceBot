from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from alicebot_api.tasks import (
    TaskNotFoundError,
    TaskStepApprovalLinkageError,
    TaskStepExecutionLinkageError,
    TaskStepNotFoundError,
    TaskStepSequenceError,
    TaskStepTransitionError,
    allowed_task_step_transitions,
    create_next_task_step_record,
    create_task_step_for_governed_request,
    get_task_step_record,
    get_task_record,
    list_task_records,
    list_task_step_records,
    sync_task_with_task_step_status,
    sync_task_step_with_approval,
    sync_task_step_with_execution,
    task_status_for_step_status,
    next_task_status_for_approval,
    task_lifecycle_trace_events,
    task_step_lifecycle_trace_events,
    task_step_outcome_snapshot,
    task_step_status_for_approval_status,
    task_step_status_for_execution_status,
    task_step_status_for_routing_decision,
    task_status_for_approval_status,
    task_status_for_execution_status,
    task_status_for_routing_decision,
    transition_task_step_record,
)
from alicebot_api.contracts import (
    TaskStepCreateInput,
    TaskStepLineageInput,
    TaskStepNextCreateInput,
    TaskStepTransitionInput,
)


class TaskStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 10, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.tasks: list[dict[str, object]] = []
        self.task_steps: list[dict[str, object]] = []
        self.approvals: list[dict[str, object]] = []
        self.tool_executions: list[dict[str, object]] = []
        self.traces: list[dict[str, object]] = []
        self.trace_events: list[dict[str, object]] = []
        self.locked_task_ids: list[UUID] = []

    def create_task(
        self,
        *,
        status: str,
        latest_approval_id: UUID | None,
        latest_execution_id: UUID | None,
    ) -> dict[str, object]:
        task = {
            "id": uuid4(),
            "user_id": self.user_id,
            "thread_id": uuid4(),
            "tool_id": uuid4(),
            "status": status,
            "request": {
                "thread_id": str(uuid4()),
                "tool_id": str(uuid4()),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": None,
                "risk_hint": None,
                "attributes": {},
            },
            "tool": {
                "id": str(uuid4()),
                "tool_key": "proxy.echo",
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
                "created_at": self.base_time.isoformat(),
            },
            "latest_approval_id": latest_approval_id,
            "latest_execution_id": latest_execution_id,
            "created_at": self.base_time + timedelta(minutes=len(self.tasks)),
            "updated_at": self.base_time + timedelta(minutes=len(self.tasks)),
        }
        self.tasks.append(task)
        return task

    def list_tasks(self) -> list[dict[str, object]]:
        return sorted(self.tasks, key=lambda task: (task["created_at"], task["id"]))

    def get_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["id"] == task_id), None)

    def get_task_by_approval_optional(self, approval_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["latest_approval_id"] == approval_id), None)

    def update_task_status_optional(
        self,
        *,
        task_id: UUID,
        status: str,
        latest_approval_id: UUID | None,
        latest_execution_id: UUID | None,
    ) -> dict[str, object] | None:
        task = self.get_task_optional(task_id)
        if task is None:
            return None
        task["status"] = status
        task["latest_approval_id"] = latest_approval_id
        task["latest_execution_id"] = latest_execution_id
        task["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return task

    def lock_task_steps(self, task_id: UUID) -> None:
        self.locked_task_ids.append(task_id)

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

    def get_task_step_optional(self, task_step_id: UUID) -> dict[str, object] | None:
        return next((task_step for task_step in self.task_steps if task_step["id"] == task_step_id), None)

    def get_approval_optional(self, approval_id: UUID) -> dict[str, object] | None:
        return next((approval for approval in self.approvals if approval["id"] == approval_id), None)

    def get_tool_execution_optional(self, execution_id: UUID) -> dict[str, object] | None:
        return next((execution for execution in self.tool_executions if execution["id"] == execution_id), None)

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
        task_step["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.task_steps))
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
        task_step["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.task_steps))
        return task_step

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


def test_list_and_get_task_records_are_deterministic() -> None:
    store = TaskStoreStub()
    first = store.create_task(
        status="approved",
        latest_approval_id=None,
        latest_execution_id=None,
    )
    second = store.create_task(
        status="blocked",
        latest_approval_id=uuid4(),
        latest_execution_id=uuid4(),
    )

    listed = list_task_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
    )
    detail = get_task_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        task_id=second["id"],
    )

    assert [item["id"] for item in listed["items"]] == [str(first["id"]), str(second["id"])]
    assert [item["status"] for item in listed["items"]] == ["approved", "blocked"]
    assert listed["summary"] == {
        "total_count": 2,
        "order": ["created_at_asc", "id_asc"],
    }
    assert detail["task"]["id"] == str(second["id"])
    assert detail["task"]["status"] == "blocked"
    assert detail["task"]["latest_approval_id"] == str(second["latest_approval_id"])
    assert detail["task"]["latest_execution_id"] == str(second["latest_execution_id"])


def test_task_lifecycle_helpers_return_deterministic_statuses_and_trace_payloads() -> None:
    assert task_status_for_routing_decision("approval_required") == "pending_approval"
    assert task_status_for_routing_decision("ready") == "approved"
    assert task_status_for_routing_decision("denied") == "denied"
    assert task_status_for_approval_status("approved") == "approved"
    assert task_status_for_approval_status("rejected") == "denied"
    assert next_task_status_for_approval(current_status="pending_approval", approval_status="approved") == "approved"
    assert next_task_status_for_approval(current_status="executed", approval_status="approved") == "executed"
    assert task_status_for_execution_status("completed") == "executed"
    assert task_status_for_execution_status("blocked") == "blocked"
    assert task_step_status_for_routing_decision("approval_required") == "created"
    assert task_step_status_for_routing_decision("ready") == "approved"
    assert task_step_status_for_routing_decision("denied") == "denied"
    assert task_step_status_for_approval_status("approved") == "approved"
    assert task_step_status_for_approval_status("rejected") == "denied"
    assert task_step_status_for_execution_status("completed") == "executed"
    assert task_step_status_for_execution_status("blocked") == "blocked"
    assert task_status_for_step_status("created") == "pending_approval"
    assert task_status_for_step_status("approved") == "approved"
    assert task_status_for_step_status("executed") == "executed"
    assert allowed_task_step_transitions("created") == ["approved", "denied"]
    assert allowed_task_step_transitions("approved") == ["executed", "blocked"]
    assert allowed_task_step_transitions("executed") == []

    task = {
        "id": str(uuid4()),
        "thread_id": str(uuid4()),
        "tool_id": str(uuid4()),
        "status": "executed",
        "request": {
            "thread_id": str(uuid4()),
            "tool_id": str(uuid4()),
            "action": "tool.run",
            "scope": "workspace",
            "domain_hint": None,
            "risk_hint": None,
            "attributes": {},
        },
        "tool": {
            "id": str(uuid4()),
            "tool_key": "proxy.echo",
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
            "created_at": "2026-03-13T10:00:00+00:00",
        },
        "latest_approval_id": str(uuid4()),
        "latest_execution_id": str(uuid4()),
        "created_at": "2026-03-13T10:00:00+00:00",
        "updated_at": "2026-03-13T10:05:00+00:00",
    }

    events = task_lifecycle_trace_events(
        task=task,
        previous_status="approved",
        source="proxy_execution",
    )

    assert events == [
        (
            "task.lifecycle.state",
            {
                "task_id": task["id"],
                "source": "proxy_execution",
                "previous_status": "approved",
                "current_status": "executed",
                "latest_approval_id": task["latest_approval_id"],
                "latest_execution_id": task["latest_execution_id"],
            },
        ),
        (
            "task.lifecycle.summary",
            {
                "task_id": task["id"],
                "source": "proxy_execution",
                "final_status": "executed",
                "latest_approval_id": task["latest_approval_id"],
                "latest_execution_id": task["latest_execution_id"],
            },
        ),
    ]

    task_step = {
        "id": str(uuid4()),
        "task_id": task["id"],
        "sequence_no": 1,
        "lineage": {
            "parent_step_id": None,
            "source_approval_id": None,
            "source_execution_id": None,
        },
        "kind": "governed_request",
        "status": "executed",
        "request": task["request"],
        "outcome": task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=task["latest_approval_id"],
            approval_status="approved",
            execution_id=task["latest_execution_id"],
            execution_status="completed",
            blocked_reason=None,
        ),
        "trace": {
            "trace_id": str(uuid4()),
            "trace_kind": "tool.proxy.execute",
        },
        "created_at": "2026-03-13T10:00:00+00:00",
        "updated_at": "2026-03-13T10:05:00+00:00",
    }

    task_step_events = task_step_lifecycle_trace_events(
        task_step=task_step,
        previous_status="approved",
        source="proxy_execution",
    )

    assert task_step_events == [
        (
            "task.step.lifecycle.state",
            {
                "task_id": task["id"],
                "task_step_id": task_step["id"],
                "source": "proxy_execution",
                "sequence_no": 1,
                "kind": "governed_request",
                "previous_status": "approved",
                "current_status": "executed",
                "trace": task_step["trace"],
            },
        ),
        (
            "task.step.lifecycle.summary",
            {
                "task_id": task["id"],
                "task_step_id": task_step["id"],
                "source": "proxy_execution",
                "sequence_no": 1,
                "kind": "governed_request",
                "final_status": "executed",
                "trace": task_step["trace"],
            },
        ),
    ]


def test_get_task_record_raises_not_found_when_missing() -> None:
    store = TaskStoreStub()

    try:
        get_task_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            task_id=uuid4(),
        )
    except TaskNotFoundError as exc:
        assert "task" in str(exc)
    else:
        raise AssertionError("expected TaskNotFoundError")


def test_task_step_list_get_and_lifecycle_updates_are_deterministic() -> None:
    store = TaskStoreStub()
    task = store.create_task(
        status="pending_approval",
        latest_approval_id=uuid4(),
        latest_execution_id=None,
    )
    first_trace_id = uuid4()
    create_payload = create_task_step_for_governed_request(
        store,  # type: ignore[arg-type]
        request=TaskStepCreateInput(
            task_id=task["id"],
            sequence_no=1,
            kind="governed_request",
            status="created",
            request=task["request"],
            outcome=task_step_outcome_snapshot(
                routing_decision="approval_required",
                approval_id=str(task["latest_approval_id"]),
                approval_status="pending",
                execution_id=None,
                execution_status=None,
                blocked_reason=None,
            ),
            trace_id=first_trace_id,
            trace_kind="approval.request",
        ),
    )
    second_trace_id = uuid4()
    approval_transition = sync_task_step_with_approval(
        store,  # type: ignore[arg-type]
        approval_id=UUID(str(task["latest_approval_id"])),
        task_step_id=UUID(create_payload["task_step"]["id"]),
        approval_status="approved",
        trace_id=second_trace_id,
        trace_kind="approval.resolve",
    )
    execution = {
        "id": uuid4(),
        "approval_id": task["latest_approval_id"],
        "task_step_id": UUID(create_payload["task_step"]["id"]),
        "status": "completed",
        "result": {
            "handler_key": "proxy.echo",
            "status": "completed",
            "output": {"mode": "no_side_effect"},
            "reason": None,
        },
    }
    third_trace_id = uuid4()
    execution_transition = sync_task_step_with_execution(
        store,  # type: ignore[arg-type]
        task_id=task["id"],
        execution=execution,  # type: ignore[arg-type]
        trace_id=third_trace_id,
        trace_kind="tool.proxy.execute",
    )
    store.create_task_step(
        task_id=task["id"],
        sequence_no=2,
        kind="governed_request",
        status="denied",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="denied",
            approval_id=None,
            approval_status=None,
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="approval.request",
    )

    listed = list_task_step_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        task_id=task["id"],
    )
    detail = get_task_step_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        task_step_id=UUID(create_payload["task_step"]["id"]),
    )

    assert [item["sequence_no"] for item in listed["items"]] == [1, 2]
    assert listed["summary"] == {
        "task_id": str(task["id"]),
        "total_count": 2,
        "latest_sequence_no": 2,
        "latest_status": "denied",
        "next_sequence_no": 3,
        "append_allowed": True,
        "order": ["sequence_no_asc", "created_at_asc", "id_asc"],
    }
    assert detail["task_step"]["id"] == create_payload["task_step"]["id"]
    assert detail["task_step"]["status"] == "executed"
    assert detail["task_step"]["trace"] == {
        "trace_id": str(third_trace_id),
        "trace_kind": "tool.proxy.execute",
    }
    assert detail["task_step"]["outcome"] == {
        "routing_decision": "approval_required",
        "approval_id": str(task["latest_approval_id"]),
        "approval_status": "approved",
        "execution_id": str(execution["id"]),
        "execution_status": "completed",
        "blocked_reason": None,
    }


def test_sync_task_step_with_approval_updates_explicitly_linked_later_step_only() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    initial_execution_id = uuid4()
    task = store.create_task(
        status="pending_approval",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    first_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=str(initial_execution_id),
            execution_status="completed",
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )
    later_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=2,
        parent_step_id=first_step["id"],
        source_approval_id=approval_id,
        source_execution_id=initial_execution_id,
        kind="governed_request",
        status="created",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="pending",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="task.step.continuation",
    )

    original_first_trace_id = first_step["trace_id"]
    original_first_trace_kind = first_step["trace_kind"]
    original_first_outcome = dict(first_step["outcome"])
    later_trace_id = uuid4()

    transition = sync_task_step_with_approval(
        store,  # type: ignore[arg-type]
        approval_id=approval_id,
        task_step_id=later_step["id"],
        approval_status="approved",
        trace_id=later_trace_id,
        trace_kind="approval.resolve",
    )

    assert transition.previous_status == "created"
    assert transition.task_step["id"] == str(later_step["id"])
    assert transition.task_step["status"] == "approved"
    assert first_step["status"] == "executed"
    assert first_step["trace_id"] == original_first_trace_id
    assert first_step["trace_kind"] == original_first_trace_kind
    assert first_step["outcome"] == original_first_outcome
    assert later_step["status"] == "approved"
    assert later_step["trace_id"] == later_trace_id
    assert later_step["trace_kind"] == "approval.resolve"
    assert later_step["outcome"] == {
        "routing_decision": "approval_required",
        "approval_id": str(approval_id),
        "approval_status": "approved",
        "execution_id": None,
        "execution_status": None,
        "blocked_reason": None,
    }
    assert task["status"] == "pending_approval"
    assert task["latest_execution_id"] is None


def test_sync_task_step_with_approval_rejects_inconsistent_linkage_without_mutating_steps() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    initial_execution_id = uuid4()
    task = store.create_task(
        status="pending_approval",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    first_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=str(initial_execution_id),
            execution_status="completed",
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )
    later_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=2,
        parent_step_id=first_step["id"],
        source_approval_id=approval_id,
        source_execution_id=initial_execution_id,
        kind="governed_request",
        status="created",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=None,
            approval_status=None,
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="task.step.continuation",
    )

    original_first_outcome = dict(first_step["outcome"])
    original_later_trace_id = later_step["trace_id"]

    try:
        sync_task_step_with_approval(
            store,  # type: ignore[arg-type]
            approval_id=approval_id,
            task_step_id=later_step["id"],
            approval_status="approved",
            trace_id=uuid4(),
            trace_kind="approval.resolve",
        )
    except TaskStepApprovalLinkageError as exc:
        assert str(exc) == (
            f"approval {approval_id} is inconsistent with linked task step {later_step['id']}"
        )
    else:
        raise AssertionError("expected TaskStepApprovalLinkageError")

    assert first_step["outcome"] == original_first_outcome
    assert later_step["status"] == "created"
    assert later_step["trace_id"] == original_later_trace_id
    assert later_step["trace_kind"] == "task.step.continuation"


def test_sync_task_step_with_execution_updates_the_linked_later_step_without_mutating_initial_step() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    initial_execution_id = uuid4()
    task = store.create_task(
        status="approved",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    first_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=str(initial_execution_id),
            execution_status="completed",
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )
    later_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=2,
        parent_step_id=first_step["id"],
        source_approval_id=approval_id,
        source_execution_id=initial_execution_id,
        kind="governed_request",
        status="approved",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="task.step.transition",
    )

    original_first_trace_id = first_step["trace_id"]
    original_first_trace_kind = first_step["trace_kind"]
    original_first_outcome = dict(first_step["outcome"])
    execution = {
        "id": uuid4(),
        "approval_id": approval_id,
        "task_step_id": later_step["id"],
        "status": "completed",
        "result": {
            "handler_key": "proxy.echo",
            "status": "completed",
            "output": {"mode": "no_side_effect"},
            "reason": None,
        },
    }

    transition = sync_task_step_with_execution(
        store,  # type: ignore[arg-type]
        task_id=task["id"],
        execution=execution,  # type: ignore[arg-type]
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )

    assert transition.previous_status == "approved"
    assert transition.task_step["id"] == str(later_step["id"])
    assert transition.task_step["status"] == "executed"
    assert first_step["status"] == "executed"
    assert first_step["trace_id"] == original_first_trace_id
    assert first_step["trace_kind"] == original_first_trace_kind
    assert first_step["outcome"] == original_first_outcome
    assert later_step["status"] == "executed"
    assert later_step["trace_kind"] == "tool.proxy.execute"
    assert later_step["outcome"] == {
        "routing_decision": "approval_required",
        "approval_id": str(approval_id),
        "approval_status": "approved",
        "execution_id": str(execution["id"]),
        "execution_status": "completed",
        "blocked_reason": None,
    }
    assert task["status"] == "approved"
    assert task["latest_execution_id"] is None


def test_sync_task_step_with_execution_rejects_missing_linkage_without_mutating_steps() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    task = store.create_task(
        status="approved",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    first_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="approved",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="approval.resolve",
    )
    execution_id = uuid4()

    try:
        sync_task_step_with_execution(
            store,  # type: ignore[arg-type]
            task_id=task["id"],
            execution={
                "id": execution_id,
                "approval_id": approval_id,
                "task_step_id": None,
                "status": "completed",
                "result": {
                    "handler_key": "proxy.echo",
                    "status": "completed",
                    "output": {"mode": "no_side_effect"},
                    "reason": None,
                },
            },  # type: ignore[arg-type]
            trace_id=uuid4(),
            trace_kind="tool.proxy.execute",
        )
    except TaskStepExecutionLinkageError as exc:
        assert str(exc) == f"tool execution {execution_id} is missing linked task_step_id"
    else:
        raise AssertionError("expected TaskStepExecutionLinkageError")

    assert first_step["status"] == "approved"
    assert first_step["outcome"]["execution_id"] is None


def test_sync_task_step_with_execution_rejects_unknown_or_out_of_task_linkage() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    task = store.create_task(
        status="approved",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="approved",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="approval.resolve",
    )
    other_task = store.create_task(
        status="approved",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    other_step = store.create_task_step(
        task_id=other_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="approved",
        request=other_task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="approval.resolve",
    )

    missing_execution_id = uuid4()
    missing_task_step_id = uuid4()
    try:
        sync_task_step_with_execution(
            store,  # type: ignore[arg-type]
            task_id=task["id"],
            execution={
                "id": missing_execution_id,
                "approval_id": approval_id,
                "task_step_id": missing_task_step_id,
                "status": "completed",
                "result": {
                    "handler_key": "proxy.echo",
                    "status": "completed",
                    "output": {"mode": "no_side_effect"},
                    "reason": None,
                },
            },  # type: ignore[arg-type]
            trace_id=uuid4(),
            trace_kind="tool.proxy.execute",
        )
    except TaskStepExecutionLinkageError as exc:
        assert str(exc) == (
            f"tool execution {missing_execution_id} references linked task step "
            f"{missing_task_step_id} that was not found"
        )
    else:
        raise AssertionError("expected TaskStepExecutionLinkageError")

    outside_execution_id = uuid4()
    try:
        sync_task_step_with_execution(
            store,  # type: ignore[arg-type]
            task_id=task["id"],
            execution={
                "id": outside_execution_id,
                "approval_id": approval_id,
                "task_step_id": other_step["id"],
                "status": "completed",
                "result": {
                    "handler_key": "proxy.echo",
                    "status": "completed",
                    "output": {"mode": "no_side_effect"},
                    "reason": None,
                },
            },  # type: ignore[arg-type]
            trace_id=uuid4(),
            trace_kind="tool.proxy.execute",
        )
    except TaskStepExecutionLinkageError as exc:
        assert str(exc) == (
            f"tool execution {outside_execution_id} links task step {other_step['id']} "
            f"outside task {task['id']}"
        )
    else:
        raise AssertionError("expected TaskStepExecutionLinkageError")


def test_sync_task_step_with_execution_rejects_inconsistent_linkage_without_mutating_steps() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    task = store.create_task(
        status="approved",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="approved",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="approval.resolve",
    )
    inconsistent_execution_id = uuid4()

    try:
        sync_task_step_with_execution(
            store,  # type: ignore[arg-type]
            task_id=task["id"],
            execution={
                "id": inconsistent_execution_id,
                "approval_id": uuid4(),
                "task_step_id": step["id"],
                "status": "completed",
                "result": {
                    "handler_key": "proxy.echo",
                    "status": "completed",
                    "output": {"mode": "no_side_effect"},
                    "reason": None,
                },
            },  # type: ignore[arg-type]
            trace_id=uuid4(),
            trace_kind="tool.proxy.execute",
        )
    except TaskStepExecutionLinkageError as exc:
        assert str(exc) == (
            f"tool execution {inconsistent_execution_id} is inconsistent with linked task step {step['id']}"
        )
    else:
        raise AssertionError("expected TaskStepExecutionLinkageError")

    assert step["status"] == "approved"
    assert step["outcome"]["execution_id"] is None


def test_sync_task_with_task_step_status_updates_parent_through_task_seam() -> None:
    store = TaskStoreStub()
    task = store.create_task(
        status="executed",
        latest_approval_id=uuid4(),
        latest_execution_id=uuid4(),
    )

    transition = sync_task_with_task_step_status(
        store,  # type: ignore[arg-type]
        task_id=task["id"],
        task_step_status="created",
        linked_approval_id=task["latest_approval_id"],
        linked_execution_id=None,
    )

    assert transition.previous_status == "executed"
    assert transition.task["status"] == "pending_approval"
    assert transition.task["latest_execution_id"] is None
    assert store.tasks[0]["status"] == "pending_approval"
    assert store.tasks[0]["latest_execution_id"] is None


def test_create_next_task_step_assigns_deterministic_sequence_updates_parent_and_records_trace() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    initial_execution_id = uuid4()
    task = store.create_task(
        status="executed",
        latest_approval_id=approval_id,
        latest_execution_id=initial_execution_id,
    )
    store.approvals.append({"id": approval_id, "thread_id": task["thread_id"], "tool_id": task["tool_id"]})
    store.tool_executions.append(
        {
            "id": task["latest_execution_id"],
            "thread_id": task["thread_id"],
            "tool_id": task["tool_id"],
            "approval_id": approval_id,
        }
    )
    store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=str(task["latest_execution_id"]),
            execution_status="completed",
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )

    payload = create_next_task_step_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskStepNextCreateInput(
            task_id=task["id"],
            kind="governed_request",
            status="created",
            request=task["request"],
            outcome=task_step_outcome_snapshot(
                routing_decision="approval_required",
                approval_id=None,
                approval_status=None,
                execution_id=None,
                execution_status=None,
                blocked_reason=None,
            ),
                lineage=TaskStepLineageInput(
                    parent_step_id=store.task_steps[0]["id"],
                    source_approval_id=approval_id,
                    source_execution_id=initial_execution_id,
                ),
            ),
    )

    assert payload["task"]["status"] == "pending_approval"
    assert payload["task"]["latest_approval_id"] == str(approval_id)
    assert payload["task"]["latest_execution_id"] is None
    assert payload["task_step"]["sequence_no"] == 2
    assert payload["task_step"]["status"] == "created"
    assert payload["task_step"]["lineage"] == {
        "parent_step_id": str(store.task_steps[0]["id"]),
        "source_approval_id": str(approval_id),
        "source_execution_id": str(initial_execution_id),
    }
    assert payload["task_step"]["trace"]["trace_kind"] == "task.step.continuation"
    assert payload["sequencing"] == {
        "task_id": str(task["id"]),
        "total_count": 2,
        "latest_sequence_no": 2,
        "latest_status": "created",
        "next_sequence_no": 3,
        "append_allowed": False,
        "order": ["sequence_no_asc", "created_at_asc", "id_asc"],
    }
    assert payload["trace"]["trace_event_count"] == 7
    assert [event["kind"] for event in store.trace_events] == [
        "task.step.continuation.request",
        "task.step.continuation.lineage",
        "task.step.continuation.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]
    assert store.trace_events[1]["payload"] == {
        "task_id": str(task["id"]),
        "parent_task_step_id": str(store.task_steps[0]["id"]),
        "parent_sequence_no": 1,
        "parent_status": "executed",
        "source_approval_id": str(approval_id),
        "source_execution_id": str(initial_execution_id),
    }


def test_create_next_task_step_rejects_when_latest_step_is_not_terminal() -> None:
    store = TaskStoreStub()
    task = store.create_task(
        status="pending_approval",
        latest_approval_id=uuid4(),
        latest_execution_id=None,
    )
    store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(task["latest_approval_id"]),
            approval_status="pending",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="approval.request",
    )

    try:
        create_next_task_step_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskStepNextCreateInput(
                task_id=task["id"],
                kind="governed_request",
                status="created",
                request=task["request"],
                outcome=task_step_outcome_snapshot(
                    routing_decision="approval_required",
                    approval_id=None,
                    approval_status="pending",
                    execution_id=None,
                    execution_status=None,
                    blocked_reason=None,
                ),
                lineage=TaskStepLineageInput(parent_step_id=store.task_steps[0]["id"]),
            ),
        )
    except TaskStepSequenceError as exc:
        assert str(exc) == (
            f"task {task['id']} latest step {store.task_steps[0]['id']} is created and cannot append a next step"
        )
    else:
        raise AssertionError("expected TaskStepSequenceError")


def test_transition_task_step_updates_latest_step_parent_and_trace() -> None:
    store = TaskStoreStub()
    first_approval_id = uuid4()
    first_execution_id = uuid4()
    task = store.create_task(
        status="approved",
        latest_approval_id=first_approval_id,
        latest_execution_id=first_execution_id,
    )
    store.approvals.extend(
        [
            {"id": first_approval_id, "thread_id": task["thread_id"], "tool_id": task["tool_id"]},
        ]
    )
    store.tool_executions.extend(
        [
            {
                "id": first_execution_id,
                "thread_id": task["thread_id"],
                "tool_id": task["tool_id"],
                "approval_id": first_approval_id,
            },
        ]
    )
    first_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(first_approval_id),
            approval_status="approved",
            execution_id=str(first_execution_id),
            execution_status="completed",
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )
    second_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=2,
        kind="governed_request",
        status="approved",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="ready",
            approval_id=None,
            approval_status=None,
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="task.step.sequence",
    )

    payload = transition_task_step_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskStepTransitionInput(
            task_step_id=second_step["id"],
            status="executed",
            outcome=task_step_outcome_snapshot(
                routing_decision="ready",
                approval_id=str(first_approval_id),
                approval_status="approved",
                execution_id=str(first_execution_id),
                execution_status="completed",
                blocked_reason=None,
            ),
        ),
    )

    assert first_step["status"] == "executed"
    assert payload["task"]["status"] == "executed"
    assert payload["task"]["latest_approval_id"] == str(first_approval_id)
    assert payload["task"]["latest_execution_id"] == str(first_execution_id)
    assert payload["task_step"]["id"] == str(second_step["id"])
    assert payload["task_step"]["status"] == "executed"
    assert payload["task_step"]["trace"]["trace_kind"] == "task.step.transition"
    assert payload["sequencing"] == {
        "task_id": str(task["id"]),
        "total_count": 2,
        "latest_sequence_no": 2,
        "latest_status": "executed",
        "next_sequence_no": 3,
        "append_allowed": True,
        "order": ["sequence_no_asc", "created_at_asc", "id_asc"],
    }
    assert [event["kind"] for event in store.trace_events] == [
        "task.step.transition.request",
        "task.step.transition.state",
        "task.step.transition.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]
    assert store.trace_events[1]["payload"]["allowed_next_statuses"] == ["executed", "blocked"]


def test_create_next_task_step_locks_before_listing_existing_steps() -> None:
    class LockingTaskStoreStub(TaskStoreStub):
        def list_task_steps_for_task(self, task_id: UUID) -> list[dict[str, object]]:
            if task_id not in self.locked_task_ids:
                raise AssertionError("task steps were listed before the advisory lock was taken")
            return super().list_task_steps_for_task(task_id)

    store = LockingTaskStoreStub()
    approval_id = uuid4()
    initial_execution_id = uuid4()
    task = store.create_task(
        status="executed",
        latest_approval_id=approval_id,
        latest_execution_id=initial_execution_id,
    )
    store.approvals.append({"id": approval_id, "thread_id": task["thread_id"], "tool_id": task["tool_id"]})
    store.tool_executions.append(
        {
            "id": task["latest_execution_id"],
            "thread_id": task["thread_id"],
            "tool_id": task["tool_id"],
            "approval_id": approval_id,
        }
    )
    store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=str(task["latest_execution_id"]),
            execution_status="completed",
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )

    payload = create_next_task_step_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=TaskStepNextCreateInput(
            task_id=task["id"],
            kind="governed_request",
            status="created",
            request=task["request"],
            outcome=task_step_outcome_snapshot(
                routing_decision="approval_required",
                approval_id=None,
                approval_status=None,
                execution_id=None,
                execution_status=None,
                blocked_reason=None,
            ),
                lineage=TaskStepLineageInput(
                    parent_step_id=store.task_steps[0]["id"],
                    source_approval_id=approval_id,
                    source_execution_id=initial_execution_id,
                ),
            ),
        )

    assert payload["task_step"]["sequence_no"] == 2


def test_create_next_task_step_rejects_visible_approval_from_unrelated_task_lineage() -> None:
    store = TaskStoreStub()
    task = store.create_task(
        status="executed",
        latest_approval_id=uuid4(),
        latest_execution_id=uuid4(),
    )
    unrelated_approval_id = uuid4()
    store.approvals.append(
        {
            "id": unrelated_approval_id,
            "thread_id": uuid4(),
            "tool_id": uuid4(),
        }
    )
    store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(task["latest_approval_id"]),
            approval_status="approved",
            execution_id=str(task["latest_execution_id"]),
            execution_status="completed",
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )

    try:
        create_next_task_step_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskStepNextCreateInput(
                task_id=task["id"],
                kind="governed_request",
                status="created",
                request=task["request"],
                outcome=task_step_outcome_snapshot(
                    routing_decision="approval_required",
                    approval_id=None,
                    approval_status=None,
                    execution_id=None,
                    execution_status=None,
                    blocked_reason=None,
                ),
                lineage=TaskStepLineageInput(
                    parent_step_id=store.task_steps[0]["id"],
                    source_approval_id=unrelated_approval_id,
                ),
            ),
        )
    except TaskStepSequenceError as exc:
        assert str(exc) == f"approval {unrelated_approval_id} does not belong to task {task['id']}"
    else:
        raise AssertionError("expected TaskStepSequenceError")


def test_create_next_task_step_rejects_parent_step_from_unrelated_task() -> None:
    store = TaskStoreStub()
    task = store.create_task(
        status="executed",
        latest_approval_id=None,
        latest_execution_id=None,
    )
    unrelated_task = store.create_task(
        status="executed",
        latest_approval_id=None,
        latest_execution_id=None,
    )
    store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="ready",
            approval_id=None,
            approval_status=None,
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )
    unrelated_step = store.create_task_step(
        task_id=unrelated_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=unrelated_task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="ready",
            approval_id=None,
            approval_status=None,
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )

    try:
        create_next_task_step_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskStepNextCreateInput(
                task_id=task["id"],
                kind="governed_request",
                status="approved",
                request=task["request"],
                outcome=task_step_outcome_snapshot(
                    routing_decision="ready",
                    approval_id=None,
                    approval_status=None,
                    execution_id=None,
                    execution_status=None,
                    blocked_reason=None,
                ),
                lineage=TaskStepLineageInput(parent_step_id=unrelated_step["id"]),
            ),
        )
    except TaskStepSequenceError as exc:
        assert str(exc) == f"task step {unrelated_step['id']} does not belong to task {task['id']}"
    else:
        raise AssertionError("expected TaskStepSequenceError")


def test_transition_task_step_rejects_invalid_status_graph_edge() -> None:
    store = TaskStoreStub()
    task = store.create_task(
        status="pending_approval",
        latest_approval_id=uuid4(),
        latest_execution_id=None,
    )
    step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(task["latest_approval_id"]),
            approval_status="pending",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="approval.request",
    )

    try:
        transition_task_step_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskStepTransitionInput(
                task_step_id=step["id"],
                status="executed",
                outcome=task_step_outcome_snapshot(
                    routing_decision="approval_required",
                    approval_id=str(task["latest_approval_id"]),
                    approval_status="approved",
                    execution_id=str(uuid4()),
                    execution_status="completed",
                    blocked_reason=None,
                ),
            ),
        )
    except TaskStepTransitionError as exc:
        assert str(exc) == (
            f"task step {step['id']} is created and cannot transition to executed; allowed: approved, denied"
        )
    else:
        raise AssertionError("expected TaskStepTransitionError")


def test_transition_task_step_rejects_visible_execution_from_unrelated_task_lineage() -> None:
    store = TaskStoreStub()
    approval_id = uuid4()
    task = store.create_task(
        status="approved",
        latest_approval_id=approval_id,
        latest_execution_id=None,
    )
    step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="approved",
        request=task["request"],
        outcome=task_step_outcome_snapshot(
            routing_decision="approval_required",
            approval_id=str(approval_id),
            approval_status="approved",
            execution_id=None,
            execution_status=None,
            blocked_reason=None,
        ),
        trace_id=uuid4(),
        trace_kind="task.step.sequence",
    )
    store.approvals.append({"id": approval_id, "thread_id": task["thread_id"], "tool_id": task["tool_id"]})
    unrelated_execution_id = uuid4()
    store.tool_executions.append(
        {
            "id": unrelated_execution_id,
            "thread_id": uuid4(),
            "tool_id": uuid4(),
            "approval_id": approval_id,
        }
    )

    try:
        transition_task_step_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=TaskStepTransitionInput(
                task_step_id=step["id"],
                status="executed",
                outcome=task_step_outcome_snapshot(
                    routing_decision="approval_required",
                    approval_id=str(approval_id),
                    approval_status="approved",
                    execution_id=str(unrelated_execution_id),
                    execution_status="completed",
                    blocked_reason=None,
                ),
            ),
        )
    except TaskStepTransitionError as exc:
        assert str(exc) == f"tool execution {unrelated_execution_id} does not belong to task {task['id']}"
    else:
        raise AssertionError("expected TaskStepTransitionError")


def test_get_task_step_record_raises_not_found_when_missing() -> None:
    store = TaskStoreStub()

    try:
        get_task_step_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            task_step_id=uuid4(),
        )
    except TaskStepNotFoundError as exc:
        assert "task step" in str(exc)
    else:
        raise AssertionError("expected TaskStepNotFoundError")
