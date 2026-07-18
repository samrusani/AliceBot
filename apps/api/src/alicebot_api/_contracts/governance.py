from __future__ import annotations

from dataclasses import dataclass, field
import sys as _sys
from typing import TYPE_CHECKING as _TYPE_CHECKING, Literal, NotRequired, TypedDict
from uuid import UUID

from alicebot_api._contracts.common import (
    ApprovalResolutionAction,
    ApprovalResolutionOutcome,
    ApprovalStatus,
    ConsentStatus,
    PolicyEffect,
    PolicyEvaluationReasonCode,
    TOOL_METADATA_VERSION_V0,
    ToolAllowlistDecision,
    ToolAllowlistReasonCode,
    ToolMetadataVersion,
    ToolRoutingDecision,
)
from alicebot_api.store import JsonObject

if _TYPE_CHECKING:
    from alicebot_api.contracts import TaskRecord


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


@dataclass(frozen=True, slots=True)
class ConsentUpsertInput:
    consent_key: str
    status: ConsentStatus
    metadata: JsonObject

    def as_payload(self) -> JsonObject:
        return {
            "consent_key": self.consent_key,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class PolicyCreateInput:
    name: str
    action: str
    scope: str
    effect: PolicyEffect
    priority: int
    active: bool
    conditions: JsonObject
    required_consents: tuple[str, ...]
    agent_profile_id: str | None = None

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "name": self.name,
            "action": self.action,
            "scope": self.scope,
            "effect": self.effect,
            "priority": self.priority,
            "active": self.active,
            "conditions": self.conditions,
            "required_consents": list(self.required_consents),
        }
        if self.agent_profile_id is not None:
            payload["agent_profile_id"] = self.agent_profile_id
        return payload


@dataclass(frozen=True, slots=True)
class PolicyEvaluationRequestInput:
    thread_id: UUID
    action: str
    scope: str
    attributes: JsonObject

    def as_payload(self) -> JsonObject:
        return {
            "thread_id": str(self.thread_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }


@dataclass(frozen=True, slots=True)
class ToolCreateInput:
    tool_key: str
    name: str
    description: str
    version: str
    metadata_version: ToolMetadataVersion = TOOL_METADATA_VERSION_V0
    active: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)
    action_hints: tuple[str, ...] = field(default_factory=tuple)
    scope_hints: tuple[str, ...] = field(default_factory=tuple)
    domain_hints: tuple[str, ...] = field(default_factory=tuple)
    risk_hints: tuple[str, ...] = field(default_factory=tuple)
    metadata: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        return {
            "tool_key": self.tool_key,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "metadata_version": self.metadata_version,
            "active": self.active,
            "tags": list(self.tags),
            "action_hints": list(self.action_hints),
            "scope_hints": list(self.scope_hints),
            "domain_hints": list(self.domain_hints),
            "risk_hints": list(self.risk_hints),
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class ToolAllowlistEvaluationRequestInput:
    thread_id: UUID
    action: str
    scope: str
    domain_hint: str | None = None
    risk_hint: str | None = None
    attributes: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "thread_id": str(self.thread_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }
        payload["domain_hint"] = self.domain_hint
        payload["risk_hint"] = self.risk_hint
        return payload


@dataclass(frozen=True, slots=True)
class ToolRoutingRequestInput:
    thread_id: UUID
    tool_id: UUID
    action: str
    scope: str
    domain_hint: str | None = None
    risk_hint: str | None = None
    attributes: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "thread_id": str(self.thread_id),
            "tool_id": str(self.tool_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }
        payload["domain_hint"] = self.domain_hint
        payload["risk_hint"] = self.risk_hint
        return payload


@dataclass(frozen=True, slots=True)
class ApprovalRequestCreateInput:
    thread_id: UUID
    tool_id: UUID
    action: str
    scope: str
    task_run_id: UUID | None = None
    domain_hint: str | None = None
    risk_hint: str | None = None
    attributes: JsonObject = field(default_factory=dict)

    def as_payload(self) -> JsonObject:
        payload: JsonObject = {
            "thread_id": str(self.thread_id),
            "tool_id": str(self.tool_id),
            "action": self.action,
            "scope": self.scope,
            "attributes": self.attributes,
        }
        payload["task_run_id"] = None if self.task_run_id is None else str(self.task_run_id)
        payload["domain_hint"] = self.domain_hint
        payload["risk_hint"] = self.risk_hint
        return payload


@dataclass(frozen=True, slots=True)
class ApprovalApproveInput:
    approval_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "approval_id": str(self.approval_id),
            "requested_action": "approve",
        }


@dataclass(frozen=True, slots=True)
class ApprovalRejectInput:
    approval_id: UUID

    def as_payload(self) -> JsonObject:
        return {
            "approval_id": str(self.approval_id),
            "requested_action": "reject",
        }


class ConsentRecord(TypedDict):
    id: str
    consent_key: str
    status: ConsentStatus
    metadata: JsonObject
    created_at: str
    updated_at: str


class ConsentUpsertResponse(TypedDict):
    consent: ConsentRecord
    write_mode: Literal["created", "updated"]


class ConsentListSummary(TypedDict):
    total_count: int
    order: list[str]


class ConsentListResponse(TypedDict):
    items: list[ConsentRecord]
    summary: ConsentListSummary


class PolicyRecord(TypedDict):
    id: str
    agent_profile_id: str | None
    name: str
    action: str
    scope: str
    effect: PolicyEffect
    priority: int
    active: bool
    conditions: JsonObject
    required_consents: list[str]
    created_at: str
    updated_at: str


class PolicyCreateResponse(TypedDict):
    policy: PolicyRecord


class PolicyListSummary(TypedDict):
    total_count: int
    order: list[str]


class PolicyListResponse(TypedDict):
    items: list[PolicyRecord]
    summary: PolicyListSummary


class PolicyDetailResponse(TypedDict):
    policy: PolicyRecord


class PolicyEvaluationReason(TypedDict):
    code: PolicyEvaluationReasonCode
    source: Literal["policy", "consent", "system"]
    message: str
    policy_id: str | None
    consent_key: str | None


class PolicyEvaluationSummary(TypedDict):
    action: str
    scope: str
    evaluated_policy_count: int
    matched_policy_id: str | None
    order: list[str]


class PolicyEvaluationTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class PolicyEvaluationResponse(TypedDict):
    decision: PolicyEffect
    matched_policy: PolicyRecord | None
    reasons: list[PolicyEvaluationReason]
    evaluation: PolicyEvaluationSummary
    trace: PolicyEvaluationTraceSummary


class ToolRecord(TypedDict):
    id: str
    tool_key: str
    name: str
    description: str
    version: str
    metadata_version: ToolMetadataVersion
    active: bool
    tags: list[str]
    action_hints: list[str]
    scope_hints: list[str]
    domain_hints: list[str]
    risk_hints: list[str]
    metadata: JsonObject
    created_at: str


class ToolCreateResponse(TypedDict):
    tool: ToolRecord


class ToolListSummary(TypedDict):
    total_count: int
    order: list[str]


class ToolListResponse(TypedDict):
    items: list[ToolRecord]
    summary: ToolListSummary


class ToolDetailResponse(TypedDict):
    tool: ToolRecord


class ToolAllowlistReason(TypedDict):
    code: ToolAllowlistReasonCode
    source: Literal["tool", "policy", "consent", "system"]
    message: str
    tool_id: str | None
    policy_id: str | None
    consent_key: str | None


class ToolAllowlistDecisionRecord(TypedDict):
    decision: ToolAllowlistDecision
    tool: ToolRecord
    reasons: list[ToolAllowlistReason]


class ToolAllowlistEvaluationSummary(TypedDict):
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    evaluated_tool_count: int
    allowed_count: int
    denied_count: int
    approval_required_count: int
    order: list[str]


class ToolAllowlistTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ToolAllowlistEvaluationResponse(TypedDict):
    allowed: list[ToolAllowlistDecisionRecord]
    denied: list[ToolAllowlistDecisionRecord]
    approval_required: list[ToolAllowlistDecisionRecord]
    summary: ToolAllowlistEvaluationSummary
    trace: ToolAllowlistTraceSummary


class ToolRoutingRequestRecord(TypedDict):
    thread_id: str
    tool_id: str
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    attributes: JsonObject


class ToolRoutingRequestTracePayload(TypedDict):
    thread_id: str
    tool_id: str
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    attributes: JsonObject


class ToolRoutingDecisionTracePayload(TypedDict):
    tool_id: str
    tool_key: str
    tool_version: str
    allowlist_decision: ToolAllowlistDecision
    routing_decision: ToolRoutingDecision
    matched_policy_id: str | None
    reasons: list[ToolAllowlistReason]


class ToolRoutingSummaryTracePayload(TypedDict):
    decision: ToolRoutingDecision
    evaluated_tool_count: int
    active_policy_count: int
    consent_count: int


class ToolRoutingSummary(TypedDict):
    thread_id: str
    tool_id: str
    action: str
    scope: str
    domain_hint: str | None
    risk_hint: str | None
    decision: ToolRoutingDecision
    evaluated_tool_count: int
    active_policy_count: int
    consent_count: int
    order: list[str]


class ToolRoutingTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ToolRoutingResponse(TypedDict):
    request: ToolRoutingRequestRecord
    decision: ToolRoutingDecision
    tool: ToolRecord
    reasons: list[ToolAllowlistReason]
    summary: ToolRoutingSummary
    trace: ToolRoutingTraceSummary


class ApprovalRoutingRecord(TypedDict):
    decision: ToolRoutingDecision
    reasons: list[ToolAllowlistReason]
    trace: ToolRoutingTraceSummary


class ApprovalResolutionRecord(TypedDict):
    resolved_at: str
    resolved_by_user_id: str


class ApprovalRecord(TypedDict):
    id: str
    thread_id: str
    task_run_id: NotRequired[str | None]
    task_step_id: str | None
    status: ApprovalStatus
    request: ToolRoutingRequestRecord
    tool: ToolRecord
    routing: ApprovalRoutingRecord
    created_at: str
    resolution: ApprovalResolutionRecord | None


class ApprovalRequestTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ApprovalResolutionTraceSummary(TypedDict):
    trace_id: str
    trace_event_count: int


class ApprovalResolutionRequestTracePayload(TypedDict):
    approval_id: str
    task_step_id: str | None
    requested_action: ApprovalResolutionAction


class ApprovalResolutionStateTracePayload(TypedDict):
    approval_id: str
    task_step_id: str | None
    requested_action: ApprovalResolutionAction
    previous_status: ApprovalStatus
    outcome: ApprovalResolutionOutcome
    current_status: ApprovalStatus
    resolved_at: str | None
    resolved_by_user_id: str | None


class ApprovalResolutionSummaryTracePayload(TypedDict):
    approval_id: str
    task_step_id: str | None
    requested_action: ApprovalResolutionAction
    outcome: ApprovalResolutionOutcome
    final_status: ApprovalStatus


class ApprovalRequestCreateResponse(TypedDict):
    request: ToolRoutingRequestRecord
    decision: ToolRoutingDecision
    tool: ToolRecord
    reasons: list[ToolAllowlistReason]
    task: TaskRecord
    approval: ApprovalRecord | None
    routing_trace: ToolRoutingTraceSummary
    trace: ApprovalRequestTraceSummary


class ApprovalListSummary(TypedDict):
    total_count: int
    order: list[str]


class ApprovalListResponse(TypedDict):
    items: list[ApprovalRecord]
    summary: ApprovalListSummary


class ApprovalDetailResponse(TypedDict):
    approval: ApprovalRecord


class ApprovalResolutionResponse(TypedDict):
    approval: ApprovalRecord
    trace: ApprovalResolutionTraceSummary

__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
