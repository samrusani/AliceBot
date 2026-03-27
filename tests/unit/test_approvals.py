from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from alicebot_api.approvals import (
    ApprovalNotFoundError,
    ApprovalResolutionConflictError,
    approve_approval_record,
    get_approval_record,
    list_approval_records,
    reject_approval_record,
    submit_approval_request,
)
from alicebot_api.contracts import ApprovalApproveInput, ApprovalRejectInput, ApprovalRequestCreateInput
from alicebot_api.tasks import TaskStepApprovalLinkageError


class ApprovalStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.user_id = uuid4()
        self.thread_id = uuid4()
        self.locked_task_ids: list[UUID] = []
        self.consents: dict[str, dict[str, object]] = {}
        self.policies: list[dict[str, object]] = []
        self.tools: list[dict[str, object]] = []
        self.approvals: list[dict[str, object]] = []
        self.tasks: list[dict[str, object]] = []
        self.task_runs: list[dict[str, object]] = []
        self.task_steps: list[dict[str, object]] = []
        self.traces: list[dict[str, object]] = []
        self.trace_events: list[dict[str, object]] = []

    def create_consent(self, *, consent_key: str, status: str, metadata: dict[str, object]) -> dict[str, object]:
        consent = {
            "id": uuid4(),
            "user_id": self.user_id,
            "consent_key": consent_key,
            "status": status,
            "metadata": metadata,
            "created_at": self.base_time + timedelta(minutes=len(self.consents)),
            "updated_at": self.base_time + timedelta(minutes=len(self.consents)),
        }
        self.consents[consent_key] = consent
        return consent

    def list_consents(self) -> list[dict[str, object]]:
        return sorted(
            self.consents.values(),
            key=lambda consent: (consent["consent_key"], consent["created_at"], consent["id"]),
        )

    def create_policy(
        self,
        *,
        name: str,
        action: str,
        scope: str,
        effect: str,
        priority: int,
        active: bool,
        conditions: dict[str, object],
        required_consents: list[str],
    ) -> dict[str, object]:
        policy = {
            "id": uuid4(),
            "user_id": self.user_id,
            "name": name,
            "action": action,
            "scope": scope,
            "effect": effect,
            "priority": priority,
            "active": active,
            "conditions": conditions,
            "required_consents": required_consents,
            "created_at": self.base_time + timedelta(minutes=len(self.policies)),
            "updated_at": self.base_time + timedelta(minutes=len(self.policies)),
        }
        self.policies.append(policy)
        return policy

    def list_active_policies(self) -> list[dict[str, object]]:
        return sorted(
            [policy for policy in self.policies if policy["active"] is True],
            key=lambda policy: (policy["priority"], policy["created_at"], policy["id"]),
        )

    def create_tool(
        self,
        *,
        tool_key: str,
        name: str,
        description: str,
        version: str,
        metadata_version: str,
        active: bool,
        tags: list[str],
        action_hints: list[str],
        scope_hints: list[str],
        domain_hints: list[str],
        risk_hints: list[str],
        metadata: dict[str, object],
    ) -> dict[str, object]:
        tool = {
            "id": uuid4(),
            "user_id": self.user_id,
            "tool_key": tool_key,
            "name": name,
            "description": description,
            "version": version,
            "metadata_version": metadata_version,
            "active": active,
            "tags": tags,
            "action_hints": action_hints,
            "scope_hints": scope_hints,
            "domain_hints": domain_hints,
            "risk_hints": risk_hints,
            "metadata": metadata,
            "created_at": self.base_time + timedelta(minutes=len(self.tools)),
        }
        self.tools.append(tool)
        return tool

    def get_tool_optional(self, tool_id: UUID) -> dict[str, object] | None:
        return next((tool for tool in self.tools if tool["id"] == tool_id), None)

    def list_active_tools(self) -> list[dict[str, object]]:
        return [tool for tool in self.tools if tool["active"] is True]

    def get_thread_optional(self, thread_id: UUID) -> dict[str, object] | None:
        if thread_id != self.thread_id:
            return None
        return {
            "id": self.thread_id,
            "user_id": self.user_id,
            "title": "Approval thread",
            "created_at": self.base_time,
            "updated_at": self.base_time,
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

    def create_approval(
        self,
        *,
        thread_id: UUID,
        tool_id: UUID,
        task_step_id: UUID | None,
        status: str,
        request: dict[str, object],
        tool: dict[str, object],
        routing: dict[str, object],
        routing_trace_id: UUID,
    ) -> dict[str, object]:
        approval = {
            "id": uuid4(),
            "user_id": self.user_id,
            "thread_id": thread_id,
            "tool_id": tool_id,
            "task_step_id": task_step_id,
            "status": status,
            "request": request,
            "tool": tool,
            "routing": routing,
            "routing_trace_id": routing_trace_id,
            "created_at": self.base_time + timedelta(minutes=len(self.approvals)),
            "resolved_at": None,
            "resolved_by_user_id": None,
        }
        self.approvals.append(approval)
        return approval

    def get_approval_optional(self, approval_id: UUID) -> dict[str, object] | None:
        return next((approval for approval in self.approvals if approval["id"] == approval_id), None)

    def list_approvals(self) -> list[dict[str, object]]:
        return sorted(
            self.approvals,
            key=lambda approval: (approval["created_at"], approval["id"]),
        )

    def get_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["id"] == task_id), None)

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
        return next((row for row in self.task_runs if row["id"] == task_run_id), None)

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
        row = self.get_task_run_optional(task_run_id)
        if row is None:
            return None
        row["status"] = status
        row["checkpoint"] = checkpoint
        row["tick_count"] = tick_count
        row["step_count"] = step_count
        row["retry_count"] = retry_count
        row["retry_cap"] = retry_cap
        row["retry_posture"] = retry_posture
        row["failure_class"] = failure_class
        row["stop_reason"] = stop_reason
        row["last_transitioned_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        row["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return row

    def get_task_by_approval_optional(self, approval_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["latest_approval_id"] == approval_id), None)

    def lock_task_steps(self, task_id: UUID) -> None:
        self.locked_task_ids.append(task_id)

    def list_tasks(self) -> list[dict[str, object]]:
        return sorted(
            self.tasks,
            key=lambda task: (task["created_at"], task["id"]),
        )

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

    def get_task_step_optional(self, task_step_id: UUID) -> dict[str, object] | None:
        return next((task_step for task_step in self.task_steps if task_step["id"] == task_step_id), None)

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

    def update_task_status_by_approval_optional(
        self,
        *,
        approval_id: UUID,
        status: str,
    ) -> dict[str, object] | None:
        task = self.get_task_by_approval_optional(approval_id)
        if task is None:
            return None
        task["status"] = status
        task["updated_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        return task

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

    def resolve_approval_optional(self, *, approval_id: UUID, status: str) -> dict[str, object] | None:
        approval = self.get_approval_optional(approval_id)
        if approval is None or approval["status"] != "pending":
            return None

        approval["status"] = status
        approval["resolved_at"] = self.base_time + timedelta(hours=1, minutes=len(self.trace_events))
        approval["resolved_by_user_id"] = self.user_id
        return approval

    def update_approval_task_step_optional(
        self,
        *,
        approval_id: UUID,
        task_step_id: UUID,
    ) -> dict[str, object] | None:
        approval = self.get_approval_optional(approval_id)
        if approval is None:
            return None
        approval["task_step_id"] = task_step_id
        return approval


def test_submit_approval_request_persists_record_for_approval_required_route() -> None:
    store = ApprovalStoreStub()
    tool = store.create_tool(
        tool_key="shell.exec",
        name="Shell Exec",
        description="Run shell commands.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["shell"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=[],
        risk_hints=[],
        metadata={"transport": "local"},
    )
    policy = store.create_policy(
        name="Require shell approval",
        action="tool.run",
        scope="workspace",
        effect="require_approval",
        priority=10,
        active=True,
        conditions={"tool_key": "shell.exec"},
        required_consents=[],
    )

    payload = submit_approval_request(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalRequestCreateInput(
            thread_id=store.thread_id,
            tool_id=tool["id"],
            action="tool.run",
            scope="workspace",
            attributes={"command": "ls"},
        ),
    )

    assert payload["decision"] == "approval_required"
    assert payload["task"]["status"] == "pending_approval"
    assert payload["task"]["latest_approval_id"] == payload["approval"]["id"]
    assert payload["task"]["latest_execution_id"] is None
    assert payload["approval"] is not None
    assert payload["approval"]["status"] == "pending"
    assert payload["approval"]["resolution"] is None
    assert payload["approval"]["thread_id"] == str(store.thread_id)
    assert payload["approval"]["task_step_id"] == str(store.task_steps[0]["id"])
    assert payload["approval"]["request"] == payload["request"]
    assert payload["approval"]["tool"] == payload["tool"]
    assert payload["approval"]["routing"] == {
        "decision": "approval_required",
        "reasons": payload["reasons"],
        "trace": payload["routing_trace"],
    }
    assert payload["routing_trace"]["trace_event_count"] == 3
    assert payload["trace"]["trace_event_count"] == 8
    assert len(store.approvals) == 1
    assert len(store.tasks) == 1
    assert len(store.task_steps) == 1
    assert store.traces[0]["kind"] == "tool.route"
    assert store.traces[1]["kind"] == "approval.request"
    assert store.traces[1]["compiler_version"] == "approval_request_v0"
    assert store.traces[1]["limits"] == {
        "order": ["created_at_asc", "id_asc"],
        "persisted": True,
    }
    assert [event["kind"] for event in store.trace_events[-8:]] == [
        "approval.request.request",
        "approval.request.routing",
        "approval.request.persisted",
        "approval.request.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]
    assert store.trace_events[-7]["payload"]["routing_trace_id"] == payload["routing_trace"]["trace_id"]
    assert store.trace_events[-6]["payload"] == {
        "approval_id": payload["approval"]["id"],
        "task_step_id": payload["approval"]["task_step_id"],
        "decision": "approval_required",
        "persisted": True,
    }
    assert store.trace_events[-4]["payload"] == {
        "task_id": payload["task"]["id"],
        "source": "approval_request",
        "previous_status": None,
        "current_status": "pending_approval",
        "latest_approval_id": payload["approval"]["id"],
        "latest_execution_id": None,
    }
    assert store.trace_events[-2]["payload"] == {
        "task_id": payload["task"]["id"],
        "task_step_id": str(store.task_steps[0]["id"]),
        "source": "approval_request",
        "sequence_no": 1,
        "kind": "governed_request",
        "previous_status": None,
        "current_status": "created",
        "trace": {
            "trace_id": payload["trace"]["trace_id"],
            "trace_kind": "approval.request",
        },
    }
    assert payload["reasons"][-1] == {
        "code": "policy_effect_require_approval",
        "source": "policy",
        "message": "Policy effect resolved the decision to 'require_approval'.",
        "tool_id": str(tool["id"]),
        "policy_id": str(policy["id"]),
        "consent_key": None,
    }


def test_submit_approval_request_does_not_persist_for_ready_or_denied_routes() -> None:
    ready_store = ApprovalStoreStub()
    ready_store.create_consent(
        consent_key="web_access",
        status="granted",
        metadata={"source": "settings"},
    )
    ready_tool = ready_store.create_tool(
        tool_key="browser.open",
        name="Browser Open",
        description="Open documentation pages.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["browser"],
        action_hints=["tool.run"],
        scope_hints=["workspace"],
        domain_hints=["docs"],
        risk_hints=[],
        metadata={"transport": "proxy"},
    )
    ready_store.create_policy(
        name="Allow docs browser",
        action="tool.run",
        scope="workspace",
        effect="allow",
        priority=10,
        active=True,
        conditions={"tool_key": "browser.open", "domain_hint": "docs"},
        required_consents=["web_access"],
    )

    ready_payload = submit_approval_request(
        ready_store,  # type: ignore[arg-type]
        user_id=ready_store.user_id,
        request=ApprovalRequestCreateInput(
            thread_id=ready_store.thread_id,
            tool_id=ready_tool["id"],
            action="tool.run",
            scope="workspace",
            domain_hint="docs",
            attributes={},
        ),
    )

    denied_store = ApprovalStoreStub()
    denied_tool = denied_store.create_tool(
        tool_key="calendar.read",
        name="Calendar Read",
        description="Read calendars.",
        version="1.0.0",
        metadata_version="tool_metadata_v0",
        active=True,
        tags=["calendar"],
        action_hints=["calendar.read"],
        scope_hints=["calendar"],
        domain_hints=[],
        risk_hints=[],
        metadata={},
    )
    denied_payload = submit_approval_request(
        denied_store,  # type: ignore[arg-type]
        user_id=denied_store.user_id,
        request=ApprovalRequestCreateInput(
            thread_id=denied_store.thread_id,
            tool_id=denied_tool["id"],
            action="tool.run",
            scope="workspace",
            attributes={},
        ),
    )

    assert ready_payload["decision"] == "ready"
    assert ready_payload["task"]["status"] == "approved"
    assert ready_payload["task"]["latest_approval_id"] is None
    assert ready_payload["approval"] is None
    assert ready_store.approvals == []
    assert len(ready_store.task_steps) == 1
    assert [event["kind"] for event in ready_store.trace_events[-8:]] == [
        "approval.request.request",
        "approval.request.routing",
        "approval.request.skipped",
        "approval.request.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]

    assert denied_payload["decision"] == "denied"
    assert denied_payload["task"]["status"] == "denied"
    assert denied_payload["task"]["latest_approval_id"] is None
    assert denied_payload["approval"] is None
    assert denied_store.approvals == []
    assert [reason["code"] for reason in denied_payload["reasons"]] == [
        "tool_action_unsupported",
        "tool_scope_unsupported",
    ]


def test_approve_approval_record_resolves_pending_and_records_trace() -> None:
    store = ApprovalStoreStub()
    approval = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-1"},
        tool={"id": "tool-1", "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-1", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    created_task = store.create_task(
        thread_id=store.thread_id,
        tool_id=approval["tool_id"],
        status="pending_approval",
        request=approval["request"],
        tool=approval["tool"],
        latest_approval_id=approval["id"],
        latest_execution_id=None,
    )
    created_step = store.create_task_step(
        task_id=created_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(approval["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    approval["task_step_id"] = created_step["id"]

    payload = approve_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalApproveInput(approval_id=approval["id"]),
    )

    assert payload["approval"]["id"] == str(approval["id"])
    assert payload["approval"]["task_step_id"] == str(created_step["id"])
    assert payload["approval"]["status"] == "approved"
    assert payload["approval"]["resolution"] == {
        "resolved_at": "2026-03-12T10:00:00+00:00",
        "resolved_by_user_id": str(store.user_id),
    }
    assert payload["trace"]["trace_event_count"] == 7
    assert store.traces[0]["kind"] == "approval.resolve"
    assert store.traces[0]["compiler_version"] == "approval_resolution_v0"
    assert store.traces[0]["limits"] == {
        "order": ["created_at_asc", "id_asc"],
        "requested_action": "approve",
        "outcome": "resolved",
    }
    assert [event["kind"] for event in store.trace_events] == [
        "approval.resolution.request",
        "approval.resolution.state",
        "approval.resolution.summary",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]
    assert store.trace_events[1]["payload"] == {
        "approval_id": str(approval["id"]),
        "task_step_id": str(approval["task_step_id"]),
        "requested_action": "approve",
        "previous_status": "pending",
        "outcome": "resolved",
        "current_status": "approved",
        "resolved_at": "2026-03-12T10:00:00+00:00",
        "resolved_by_user_id": str(store.user_id),
    }
    assert store.trace_events[3]["payload"] == {
        "task_id": str(store.tasks[0]["id"]),
        "source": "approval_resolution",
        "previous_status": "pending_approval",
        "current_status": "approved",
        "latest_approval_id": str(approval["id"]),
        "latest_execution_id": None,
    }
    assert store.trace_events[5]["payload"] == {
        "task_id": str(store.tasks[0]["id"]),
        "task_step_id": str(store.task_steps[0]["id"]),
        "source": "approval_resolution",
        "sequence_no": 1,
        "kind": "governed_request",
        "previous_status": "created",
        "current_status": "approved",
        "trace": {
            "trace_id": str(store.traces[0]["id"]),
            "trace_kind": "approval.resolve",
        },
    }


def test_reject_approval_record_resolves_pending_and_records_trace() -> None:
    store = ApprovalStoreStub()
    approval = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-2"},
        tool={"id": "tool-2", "tool_key": "browser.open"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-2", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    created_task = store.create_task(
        thread_id=store.thread_id,
        tool_id=approval["tool_id"],
        status="pending_approval",
        request=approval["request"],
        tool=approval["tool"],
        latest_approval_id=approval["id"],
        latest_execution_id=None,
    )
    created_step = store.create_task_step(
        task_id=created_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(approval["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    approval["task_step_id"] = created_step["id"]

    payload = reject_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalRejectInput(approval_id=approval["id"]),
    )

    assert payload["approval"]["status"] == "rejected"
    assert payload["approval"]["task_step_id"] == str(created_step["id"])
    assert payload["approval"]["resolution"] == {
        "resolved_at": "2026-03-12T10:00:00+00:00",
        "resolved_by_user_id": str(store.user_id),
    }
    assert store.trace_events[1]["payload"]["requested_action"] == "reject"
    assert store.trace_events[1]["payload"]["current_status"] == "rejected"


def test_approval_resolution_resumes_waiting_approval_run_only() -> None:
    store = ApprovalStoreStub()
    approval = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-run"},
        tool={"id": "tool-run", "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-run", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    created_task = store.create_task(
        thread_id=store.thread_id,
        tool_id=approval["tool_id"],
        status="pending_approval",
        request=approval["request"],
        tool=approval["tool"],
        latest_approval_id=approval["id"],
        latest_execution_id=None,
    )
    created_step = store.create_task_step(
        task_id=created_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(approval["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    approval["task_step_id"] = created_step["id"]
    run = store.create_task_run(
        task_id=created_task["id"],
        status="waiting_approval",
        checkpoint={
            "cursor": 0,
            "target_steps": 1,
            "wait_for_signal": True,
            "waiting_approval_id": str(approval["id"]),
        },
        tick_count=1,
        step_count=0,
        max_ticks=3,
        stop_reason="waiting_approval",
    )
    approval["task_run_id"] = run["id"]

    payload = approve_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalApproveInput(approval_id=approval["id"]),
    )

    assert payload["approval"]["status"] == "approved"
    assert payload["trace"]["trace_event_count"] == 8
    assert store.task_runs[0]["status"] == "queued"
    assert store.task_runs[0]["stop_reason"] is None
    assert store.task_runs[0]["checkpoint"]["wait_for_signal"] is False
    assert store.task_runs[0]["checkpoint"]["waiting_approval_id"] is None
    assert store.task_runs[0]["checkpoint"]["resolved_approval_id"] == str(approval["id"])
    assert store.task_runs[0]["checkpoint"]["approval_resolution_status"] == "approved"
    assert [event["kind"] for event in store.trace_events] == [
        "approval.resolution.request",
        "approval.resolution.state",
        "approval.resolution.summary",
        "approval.resolution.run",
        "task.lifecycle.state",
        "task.lifecycle.summary",
        "task.step.lifecycle.state",
        "task.step.lifecycle.summary",
    ]


def test_approval_resolution_does_not_reopen_cancelled_linked_run() -> None:
    store = ApprovalStoreStub()
    approval = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-cancelled-run"},
        tool={"id": "tool-cancelled-run", "tool_key": "shell.exec"},
        routing={
            "decision": "approval_required",
            "reasons": [],
            "trace": {"trace_id": "trace-cancelled-run", "trace_event_count": 3},
        },
        routing_trace_id=uuid4(),
    )
    created_task = store.create_task(
        thread_id=store.thread_id,
        tool_id=approval["tool_id"],
        status="pending_approval",
        request=approval["request"],
        tool=approval["tool"],
        latest_approval_id=approval["id"],
        latest_execution_id=None,
    )
    created_step = store.create_task_step(
        task_id=created_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(approval["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    approval["task_step_id"] = created_step["id"]
    run = store.create_task_run(
        task_id=created_task["id"],
        status="cancelled",
        checkpoint={
            "cursor": 0,
            "target_steps": 1,
            "wait_for_signal": False,
        },
        tick_count=1,
        step_count=0,
        max_ticks=3,
        stop_reason="cancelled",
    )
    approval["task_run_id"] = run["id"]

    payload = approve_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalApproveInput(approval_id=approval["id"]),
    )

    assert payload["approval"]["status"] == "approved"
    assert payload["trace"]["trace_event_count"] == 7
    assert store.task_runs[0]["status"] == "cancelled"
    assert store.task_runs[0]["stop_reason"] == "cancelled"
    assert store.task_runs[0]["checkpoint"] == {
        "cursor": 0,
        "target_steps": 1,
        "wait_for_signal": False,
    }
    assert "approval.resolution.run" not in [event["kind"] for event in store.trace_events]


def test_approval_resolution_locks_task_steps_before_task_and_step_mutation() -> None:
    class LockingApprovalStoreStub(ApprovalStoreStub):
        def list_task_steps_for_task(self, task_id: UUID) -> list[dict[str, object]]:
            if task_id not in self.locked_task_ids:
                raise AssertionError("task-step boundary was checked before the task-step lock was taken")
            return super().list_task_steps_for_task(task_id)

        def update_task_status_by_approval_optional(
            self,
            *,
            approval_id: UUID,
            status: str,
        ) -> dict[str, object] | None:
            task = self.get_task_by_approval_optional(approval_id)
            if task is None:
                return None
            if task["id"] not in self.locked_task_ids:
                raise AssertionError("task status changed before the task-step lock was taken")
            return super().update_task_status_by_approval_optional(
                approval_id=approval_id,
                status=status,
            )

    store = LockingApprovalStoreStub()
    approval = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-lock"},
        tool={"id": "tool-lock", "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-lock", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    task = store.create_task(
        thread_id=store.thread_id,
        tool_id=approval["tool_id"],
        status="pending_approval",
        request=approval["request"],
        tool=approval["tool"],
        latest_approval_id=approval["id"],
        latest_execution_id=None,
    )
    created_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(approval["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    approval["task_step_id"] = created_step["id"]

    payload = approve_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalApproveInput(approval_id=approval["id"]),
    )

    assert payload["approval"]["status"] == "approved"
    assert task["id"] in store.locked_task_ids


def test_resolution_rejects_duplicate_and_conflicting_updates_deterministically() -> None:
    duplicate_store = ApprovalStoreStub()
    duplicate_approval = duplicate_store.create_approval(
        thread_id=duplicate_store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(duplicate_store.thread_id), "tool_id": "tool-3"},
        tool={"id": "tool-3", "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-3", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    duplicate_task = duplicate_store.create_task(
        thread_id=duplicate_store.thread_id,
        tool_id=duplicate_approval["tool_id"],
        status="pending_approval",
        request=duplicate_approval["request"],
        tool=duplicate_approval["tool"],
        latest_approval_id=duplicate_approval["id"],
        latest_execution_id=None,
    )
    duplicate_step = duplicate_store.create_task_step(
        task_id=duplicate_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=duplicate_approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(duplicate_approval["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    duplicate_approval["task_step_id"] = duplicate_step["id"]
    approve_approval_record(
        duplicate_store,  # type: ignore[arg-type]
        user_id=duplicate_store.user_id,
        request=ApprovalApproveInput(approval_id=duplicate_approval["id"]),
    )

    try:
        approve_approval_record(
            duplicate_store,  # type: ignore[arg-type]
            user_id=duplicate_store.user_id,
            request=ApprovalApproveInput(approval_id=duplicate_approval["id"]),
        )
    except ApprovalResolutionConflictError as exc:
        assert str(exc) == f"approval {duplicate_approval['id']} was already approved"
    else:
        raise AssertionError("expected ApprovalResolutionConflictError for duplicate approval")

    assert duplicate_store.trace_events[-6]["payload"]["outcome"] == "duplicate_rejected"

    conflict_store = ApprovalStoreStub()
    conflict_approval = conflict_store.create_approval(
        thread_id=conflict_store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(conflict_store.thread_id), "tool_id": "tool-4"},
        tool={"id": "tool-4", "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-4", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    conflict_task = conflict_store.create_task(
        thread_id=conflict_store.thread_id,
        tool_id=conflict_approval["tool_id"],
        status="pending_approval",
        request=conflict_approval["request"],
        tool=conflict_approval["tool"],
        latest_approval_id=conflict_approval["id"],
        latest_execution_id=None,
    )
    conflict_step = conflict_store.create_task_step(
        task_id=conflict_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=conflict_approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(conflict_approval["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    conflict_approval["task_step_id"] = conflict_step["id"]
    approve_approval_record(
        conflict_store,  # type: ignore[arg-type]
        user_id=conflict_store.user_id,
        request=ApprovalApproveInput(approval_id=conflict_approval["id"]),
    )

    try:
        reject_approval_record(
            conflict_store,  # type: ignore[arg-type]
            user_id=conflict_store.user_id,
            request=ApprovalRejectInput(approval_id=conflict_approval["id"]),
        )
    except ApprovalResolutionConflictError as exc:
        assert str(exc) == (
            f"approval {conflict_approval['id']} was already approved and cannot be rejected"
        )
    else:
        raise AssertionError("expected ApprovalResolutionConflictError for conflicting rejection")

    assert conflict_store.trace_events[-6]["payload"]["outcome"] == "conflict_rejected"


def test_approval_resolution_rejects_inconsistent_linkage_without_mutating_task_state() -> None:
    store = ApprovalStoreStub()
    approval = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="approved",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-boundary"},
        tool={"id": "tool-boundary", "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-boundary", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    task = store.create_task(
        thread_id=store.thread_id,
        tool_id=approval["tool_id"],
        status="pending_approval",
        request=approval["request"],
        tool=approval["tool"],
        latest_approval_id=approval["id"],
        latest_execution_id=None,
    )
    first_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=1,
        kind="governed_request",
        status="executed",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(approval["id"]),
            "approval_status": "approved",
            "execution_id": str(uuid4()),
            "execution_status": "completed",
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="tool.proxy.execute",
    )
    later_step = store.create_task_step(
        task_id=task["id"],
        sequence_no=2,
        parent_step_id=first_step["id"],
        source_approval_id=approval["id"],
        source_execution_id=uuid4(),
        kind="governed_request",
        status="created",
        request=approval["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": None,
            "approval_status": None,
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="task.step.continuation",
    )
    approval["task_step_id"] = later_step["id"]

    original_first_trace_id = first_step["trace_id"]
    original_first_outcome = dict(first_step["outcome"])
    original_later_trace_id = later_step["trace_id"]

    try:
        approve_approval_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ApprovalApproveInput(approval_id=approval["id"]),
        )
    except TaskStepApprovalLinkageError as exc:
        assert str(exc) == (
            f"approval {approval['id']} is inconsistent with linked task step {later_step['id']}"
        )
    else:
        raise AssertionError("expected TaskStepApprovalLinkageError")

    assert task["status"] == "pending_approval"
    assert task["latest_execution_id"] is None
    assert first_step["status"] == "executed"
    assert first_step["trace_id"] == original_first_trace_id
    assert first_step["outcome"] == original_first_outcome
    assert later_step["status"] == "created"
    assert later_step["trace_id"] == original_later_trace_id
    assert store.traces == []
    assert store.trace_events == []


def test_list_and_get_approval_records_use_deterministic_order_after_resolution() -> None:
    store = ApprovalStoreStub()
    first = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-1"},
        tool={"id": "tool-1", "tool_key": "shell.exec"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-1", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    first_task = store.create_task(
        thread_id=store.thread_id,
        tool_id=first["tool_id"],
        status="pending_approval",
        request=first["request"],
        tool=first["tool"],
        latest_approval_id=first["id"],
        latest_execution_id=None,
    )
    first_step = store.create_task_step(
        task_id=first_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=first["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(first["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    first["task_step_id"] = first_step["id"]
    second = store.create_approval(
        thread_id=store.thread_id,
        tool_id=uuid4(),
        task_step_id=None,
        status="pending",
        request={"thread_id": str(store.thread_id), "tool_id": "tool-2"},
        tool={"id": "tool-2", "tool_key": "browser.open"},
        routing={"decision": "approval_required", "reasons": [], "trace": {"trace_id": "trace-2", "trace_event_count": 3}},
        routing_trace_id=uuid4(),
    )
    second_task = store.create_task(
        thread_id=store.thread_id,
        tool_id=second["tool_id"],
        status="pending_approval",
        request=second["request"],
        tool=second["tool"],
        latest_approval_id=second["id"],
        latest_execution_id=None,
    )
    second_step = store.create_task_step(
        task_id=second_task["id"],
        sequence_no=1,
        kind="governed_request",
        status="created",
        request=second["request"],
        outcome={
            "routing_decision": "approval_required",
            "approval_id": str(second["id"]),
            "approval_status": "pending",
            "execution_id": None,
            "execution_status": None,
            "blocked_reason": None,
        },
        trace_id=uuid4(),
        trace_kind="approval.request",
    )
    second["task_step_id"] = second_step["id"]

    approve_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalApproveInput(approval_id=first["id"]),
    )
    reject_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ApprovalRejectInput(approval_id=second["id"]),
    )

    listed = list_approval_records(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
    )
    detail = get_approval_record(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        approval_id=UUID(str(second["id"])),
    )

    assert [item["id"] for item in listed["items"]] == [str(first["id"]), str(second["id"])]
    assert [item["task_step_id"] for item in listed["items"]] == [str(first_step["id"]), str(second_step["id"])]
    assert [item["status"] for item in listed["items"]] == ["approved", "rejected"]
    assert listed["items"][0]["resolution"] is not None
    assert listed["items"][1]["resolution"] is not None
    assert listed["summary"] == {
        "total_count": 2,
        "order": ["created_at_asc", "id_asc"],
    }
    assert detail["approval"]["id"] == str(second["id"])
    assert detail["approval"]["task_step_id"] == str(second_step["id"])
    assert detail["approval"]["status"] == "rejected"
    assert detail["approval"]["resolution"] == {
        "resolved_at": "2026-03-12T10:07:00+00:00",
        "resolved_by_user_id": str(store.user_id),
    }


def test_get_approval_record_raises_not_found_when_missing() -> None:
    store = ApprovalStoreStub()

    try:
        get_approval_record(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            approval_id=uuid4(),
        )
    except ApprovalNotFoundError as exc:
        assert "approval" in str(exc)
    else:
        raise AssertionError("expected ApprovalNotFoundError")
