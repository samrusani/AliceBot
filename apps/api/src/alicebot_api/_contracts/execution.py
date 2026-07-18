from __future__ import annotations

from dataclasses import dataclass
import sys as _sys
from typing import Literal, NotRequired, TypedDict
from uuid import UUID

from alicebot_api._contracts.common import (
    ApprovalStatus,
    ExecutionBudgetContextResolution,
    ExecutionBudgetCountScope,
    ExecutionBudgetDecision,
    ExecutionBudgetDecisionReason,
    ExecutionBudgetLifecycleAction,
    ExecutionBudgetLifecycleOutcome,
    ExecutionBudgetStatus,
    ProxyExecutionStatus,
)
from alicebot_api._contracts.governance import (
    ApprovalRecord,
    ToolRecord,
    ToolRoutingRequestRecord,
)
from alicebot_api.store import JsonObject


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


@dataclass(frozen=True, slots=True)
class ProxyExecutionRequestInput:
    approval_id: UUID
    task_run_id: UUID | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "approval_id": str(self.approval_id),
        }
        payload["task_run_id"] = None if self.task_run_id is None else str(self.task_run_id)
        return payload


@dataclass(frozen=True, slots=True)
class ExecutionBudgetCreateInput:
    max_completed_executions: int
    tool_key: str | None = None
    domain_hint: str | None = None
    rolling_window_seconds: int | None = None
    agent_profile_id: str | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "max_completed_executions": self.max_completed_executions,
        }
        payload["tool_key"] = self.tool_key
        payload["domain_hint"] = self.domain_hint
        payload["rolling_window_seconds"] = self.rolling_window_seconds
        payload["agent_profile_id"] = self.agent_profile_id
        return payload


@dataclass(frozen=True, slots=True)
class ExecutionBudgetDeactivateInput:
    thread_id: UUID
    execution_budget_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "thread_id": str(self.thread_id),
            "execution_budget_id": str(self.execution_budget_id),
            "requested_action": "deactivate",
        }


@dataclass(frozen=True, slots=True)
class ExecutionBudgetSupersedeInput:
    thread_id: UUID
    execution_budget_id: UUID
    max_completed_executions: int

    def as_payload(self) -> JsonObject:
        return {
            "thread_id": str(self.thread_id),
            "execution_budget_id": str(self.execution_budget_id),
            "requested_action": "supersede",
            "max_completed_executions": self.max_completed_executions,
        }


class ExecutionBudgetRecord(TypedDict):
    id: str
    agent_profile_id: str | None
    tool_key: str | None
    domain_hint: str | None
    max_completed_executions: int
    rolling_window_seconds: int | None
    status: ExecutionBudgetStatus
    deactivated_at: str | None
    superseded_by_budget_id: str | None
    supersedes_budget_id: str | None
    created_at: str


class ExecutionBudgetCreateResponse(TypedDict):
    execution_budget: ExecutionBudgetRecord


class ExecutionBudgetListSummary(TypedDict):
    total_count: int
    order: list[str]


class ExecutionBudgetListResponse(TypedDict):
    items: list[ExecutionBudgetRecord]
    summary: ExecutionBudgetListSummary


class ExecutionBudgetDetailResponse(TypedDict):
    execution_budget: ExecutionBudgetRecord


class ExecutionBudgetLifecycleTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ExecutionBudgetDeactivateResponse(TypedDict):
    execution_budget: ExecutionBudgetRecord
    trace: ExecutionBudgetLifecycleTraceSummary


class ExecutionBudgetSupersedeResponse(TypedDict):
    superseded_budget: ExecutionBudgetRecord
    replacement_budget: ExecutionBudgetRecord
    trace: ExecutionBudgetLifecycleTraceSummary


class ExecutionBudgetDecisionRecord(TypedDict):
    matched_budget_id: str | None
    tool_key: str
    domain_hint: str | None
    budget_tool_key: str | None
    budget_domain_hint: str | None
    max_completed_executions: int | None
    rolling_window_seconds: int | None
    count_scope: ExecutionBudgetCountScope
    window_started_at: str | None
    completed_execution_count: int
    projected_completed_execution_count: int
    decision: ExecutionBudgetDecision
    reason: ExecutionBudgetDecisionReason
    order: list[str]
    history_order: list[str]
    request_thread_id: NotRequired[str | None]
    context_resolution: NotRequired[ExecutionBudgetContextResolution]
    context_reason: NotRequired[str | None]


class ExecutionBudgetLifecycleRequestTracePayload(TypedDict):
    thread_id: str
    execution_budget_id: str
    requested_action: ExecutionBudgetLifecycleAction
    replacement_max_completed_executions: int | None


class ExecutionBudgetLifecycleStateTracePayload(TypedDict):
    execution_budget_id: str
    requested_action: ExecutionBudgetLifecycleAction
    previous_status: ExecutionBudgetStatus
    current_status: ExecutionBudgetStatus
    tool_key: str | None
    domain_hint: str | None
    max_completed_executions: int
    rolling_window_seconds: int | None
    deactivated_at: str | None
    superseded_by_budget_id: str | None
    supersedes_budget_id: str | None
    replacement_budget_id: str | None
    replacement_status: ExecutionBudgetStatus | None
    replacement_max_completed_executions: int | None
    replacement_rolling_window_seconds: int | None
    rejection_reason: str | None


class ExecutionBudgetLifecycleSummaryTracePayload(TypedDict):
    execution_budget_id: str
    requested_action: ExecutionBudgetLifecycleAction
    outcome: ExecutionBudgetLifecycleOutcome
    replacement_budget_id: str | None
    active_budget_id: str | None


@dataclass(frozen=True, slots=True)
class ToolExecutionCreateInput:
    approval_id: UUID
    task_step_id: UUID
    thread_id: UUID
    tool_id: UUID
    trace_id: UUID
    request_event_id: UUID | None
    result_event_id: UUID | None
    status: ProxyExecutionStatus
    handler_key: str | None
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    result: "ToolExecutionResultRecord"
    task_run_id: UUID | None = None
    idempotency_key: str | None = None


class ToolExecutionRecord(TypedDict):
    id: str
    approval_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str
    thread_id: str
    tool_id: str
    trace_id: str
    request_event_id: str | None
    result_event_id: str | None
    status: ProxyExecutionStatus
    handler_key: str | None
    idempotency_key: NotRequired[str | None]
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    result: "ToolExecutionResultRecord"
    executed_at: str


class ToolExecutionListSummary(TypedDict):
    total_count: int
    order: list[str]


class ToolExecutionListResponse(TypedDict):
    items: list[ToolExecutionRecord]
    summary: ToolExecutionListSummary


class ToolExecutionDetailResponse(TypedDict):
    execution: ToolExecutionRecord


class ProxyExecutionRequestRecord(TypedDict):
    approval_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str


class ProxyExecutionRequestEventPayload(TypedDict):
    approval_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str
    tool_id: str
    tool_key: str
    request: ToolRoutingRequestRecord


class ProxyExecutionResultRecord(TypedDict):
    handler_key: str
    status: ProxyExecutionStatus
    output: JsonObject | None


class ProxyExecutionResultEventPayload(TypedDict):
    approval_id: str
    task_step_id: str
    tool_id: str
    tool_key: str
    handler_key: str
    status: Literal["completed"]
    output: JsonObject


class ToolExecutionResultRecord(TypedDict):
    handler_key: str | None
    status: ProxyExecutionStatus
    output: JsonObject | None
    reason: str | None
    budget_decision: NotRequired[ExecutionBudgetDecisionRecord]


class ProxyExecutionEventSummary(TypedDict):
    request_event_id: str
    request_sequence_no: int
    result_event_id: str
    result_sequence_no: int


class ProxyExecutionTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ProxyExecutionBudgetPrecheckTracePayload(ExecutionBudgetDecisionRecord):
    pass


class ProxyExecutionApprovalTracePayload(TypedDict):
    approval_id: str
    task_step_id: str
    approval_status: ApprovalStatus
    eligible_for_execution: bool


class ProxyExecutionBudgetContextTracePayload(TypedDict):
    request_thread_id: str | None
    context_resolution: ExecutionBudgetContextResolution
    context_reason: str | None


class ProxyExecutionDispatchTracePayload(TypedDict):
    approval_id: str
    task_step_id: str
    tool_id: str
    tool_key: str
    handler_key: str | None
    dispatch_status: Literal["executed", "blocked"]
    reason: str | None
    result_status: ProxyExecutionStatus | None
    output: JsonObject | None
    budget_context: NotRequired[ProxyExecutionBudgetContextTracePayload]


class ProxyExecutionSummaryTracePayload(TypedDict):
    approval_id: str
    task_step_id: str
    tool_id: str
    tool_key: str
    approval_status: ApprovalStatus
    execution_status: Literal["completed", "blocked"]
    handler_key: str | None
    request_event_id: str | None
    result_event_id: str | None


class ProxyExecutionResponse(TypedDict):
    request: ProxyExecutionRequestRecord
    approval: ApprovalRecord
    tool: ToolRecord
    result: ProxyExecutionResultRecord | ToolExecutionResultRecord
    events: ProxyExecutionEventSummary | None
    trace: ProxyExecutionTraceSummary


class ProxyExecutionBudgetBlockedResponse(TypedDict):
    request: ProxyExecutionRequestRecord
    approval: ApprovalRecord
    tool: ToolRecord
    result: ToolExecutionResultRecord
    events: None
    trace: ProxyExecutionTraceSummary

__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
