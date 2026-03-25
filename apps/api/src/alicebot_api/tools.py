from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from alicebot_api.contracts import (
    DEFAULT_AGENT_PROFILE_ID,
    TOOL_ALLOWLIST_EVALUATION_VERSION_V0,
    TOOL_ROUTING_VERSION_V0,
    TOOL_LIST_ORDER,
    TRACE_KIND_TOOL_ALLOWLIST_EVALUATE,
    TRACE_KIND_TOOL_ROUTE,
    PolicyEvaluationRequestInput,
    ToolAllowlistDecisionRecord,
    ToolAllowlistEvaluationRequestInput,
    ToolAllowlistEvaluationResponse,
    ToolAllowlistEvaluationSummary,
    ToolAllowlistReason,
    ToolAllowlistTraceSummary,
    ToolRoutingDecision,
    ToolRoutingDecisionTracePayload,
    ToolRoutingRequestInput,
    ToolRoutingRequestTracePayload,
    ToolRoutingResponse,
    ToolRoutingSummary,
    ToolRoutingSummaryTracePayload,
    ToolRoutingTraceSummary,
    ToolCreateInput,
    ToolCreateResponse,
    ToolDetailResponse,
    ToolListResponse,
    ToolListSummary,
    ToolRecord,
    isoformat_or_none,
)
from alicebot_api.policy import (
    evaluate_policy_against_context,
    load_policy_evaluation_context,
)
from alicebot_api.store import ContinuityStore, ToolRow


class ToolValidationError(ValueError):
    """Raised when a tool-registry request fails explicit validation."""


class ToolNotFoundError(LookupError):
    """Raised when a requested tool is not visible inside the current user scope."""


class ToolAllowlistValidationError(ValueError):
    """Raised when a tool-allowlist evaluation request fails explicit validation."""


class ToolRoutingValidationError(ValueError):
    """Raised when a tool-routing request fails explicit validation."""


@dataclass(frozen=True, slots=True)
class ToolClassificationResult:
    decision: str
    tool: ToolRecord
    reasons: list[ToolAllowlistReason]
    matched_policy_id: str | None


def _serialize_tool(tool: ToolRow) -> ToolRecord:
    return {
        "id": str(tool["id"]),
        "tool_key": tool["tool_key"],
        "name": tool["name"],
        "description": tool["description"],
        "version": tool["version"],
        "metadata_version": tool["metadata_version"],
        "active": tool["active"],
        "tags": list(tool["tags"]),
        "action_hints": list(tool["action_hints"]),
        "scope_hints": list(tool["scope_hints"]),
        "domain_hints": list(tool["domain_hints"]),
        "risk_hints": list(tool["risk_hints"]),
        "metadata": tool["metadata"],
        "created_at": tool["created_at"].isoformat(),
    }


def _build_tool_reason(
    *,
    code: str,
    source: str,
    message: str,
    tool_id: UUID,
    policy_id: str | None = None,
    consent_key: str | None = None,
) -> ToolAllowlistReason:
    return {
        "code": code,
        "source": source,
        "message": message,
        "tool_id": str(tool_id),
        "policy_id": policy_id,
        "consent_key": consent_key,
    }


def _metadata_match_reasons(
    *,
    tool: ToolRow,
    request: ToolAllowlistEvaluationRequestInput,
) -> tuple[bool, list[ToolAllowlistReason]]:
    reasons: list[ToolAllowlistReason] = []
    matched = True

    if request.action not in tool["action_hints"]:
        matched = False
        reasons.append(
            _build_tool_reason(
                code="tool_action_unsupported",
                source="tool",
                message=f"Tool '{tool['tool_key']}' does not declare support for action '{request.action}'.",
                tool_id=tool["id"],
            )
        )

    if request.scope not in tool["scope_hints"]:
        matched = False
        reasons.append(
            _build_tool_reason(
                code="tool_scope_unsupported",
                source="tool",
                message=f"Tool '{tool['tool_key']}' does not declare support for scope '{request.scope}'.",
                tool_id=tool["id"],
            )
        )

    if request.domain_hint is not None and tool["domain_hints"] and request.domain_hint not in tool["domain_hints"]:
        matched = False
        reasons.append(
            _build_tool_reason(
                code="tool_domain_mismatch",
                source="tool",
                message=(
                    f"Tool '{tool['tool_key']}' does not declare domain hint '{request.domain_hint}'."
                ),
                tool_id=tool["id"],
            )
        )

    if request.risk_hint is not None and tool["risk_hints"] and request.risk_hint not in tool["risk_hints"]:
        matched = False
        reasons.append(
            _build_tool_reason(
                code="tool_risk_mismatch",
                source="tool",
                message=f"Tool '{tool['tool_key']}' does not declare risk hint '{request.risk_hint}'.",
                tool_id=tool["id"],
            )
        )

    if matched:
        reasons.append(
            _build_tool_reason(
                code="tool_metadata_matched",
                source="tool",
                message="Tool metadata matched the requested action, scope, and optional hints.",
                tool_id=tool["id"],
            )
        )

    return matched, reasons


def _policy_attributes(
    *,
    tool: ToolRow,
    request: ToolAllowlistEvaluationRequestInput,
) -> dict[str, object]:
    attributes: dict[str, object] = dict(request.attributes)
    attributes["tool_key"] = tool["tool_key"]
    attributes["tool_version"] = tool["version"]
    attributes["metadata_version"] = tool["metadata_version"]
    if request.domain_hint is not None:
        attributes["domain_hint"] = request.domain_hint
    if request.risk_hint is not None:
        attributes["risk_hint"] = request.risk_hint
    return attributes


def _classify_tool_request(
    *,
    tool: ToolRow,
    request: ToolAllowlistEvaluationRequestInput,
    policy_context,
) -> ToolClassificationResult:
    metadata_matched, metadata_reasons = _metadata_match_reasons(tool=tool, request=request)
    serialized_tool = _serialize_tool(tool)

    if not metadata_matched:
        return ToolClassificationResult(
            decision="denied",
            tool=serialized_tool,
            reasons=metadata_reasons,
            matched_policy_id=None,
        )

    policy_decision = evaluate_policy_against_context(
        policy_context,
        request=PolicyEvaluationRequestInput(
            thread_id=request.thread_id,
            action=request.action,
            scope=request.scope,
            attributes=_policy_attributes(tool=tool, request=request),
        ),
    )
    reasons = metadata_reasons + [
        {
            "code": reason["code"],
            "source": reason["source"],
            "message": reason["message"],
            "tool_id": str(tool["id"]),
            "policy_id": reason["policy_id"],
            "consent_key": reason["consent_key"],
        }
        for reason in policy_decision.reasons
    ]
    return ToolClassificationResult(
        decision={
            "allow": "allowed",
            "deny": "denied",
            "require_approval": "approval_required",
        }[policy_decision.decision],
        tool=serialized_tool,
        reasons=reasons,
        matched_policy_id=(
            None if policy_decision.matched_policy is None else str(policy_decision.matched_policy["id"])
        ),
    )


def _decision_record_from_classification(
    classification: ToolClassificationResult,
) -> ToolAllowlistDecisionRecord:
    return {
        "decision": classification.decision,
        "tool": classification.tool,
        "reasons": classification.reasons,
    }


def _allowlist_trace_payload(
    classification: ToolClassificationResult,
) -> dict[str, object]:
    return {
        "tool_id": classification.tool["id"],
        "tool_key": classification.tool["tool_key"],
        "tool_version": classification.tool["version"],
        "decision": classification.decision,
        "matched_policy_id": classification.matched_policy_id,
        "reasons": classification.reasons,
    }


def _allowlist_request_from_routing(
    request: ToolRoutingRequestInput,
) -> ToolAllowlistEvaluationRequestInput:
    return ToolAllowlistEvaluationRequestInput(
        thread_id=request.thread_id,
        action=request.action,
        scope=request.scope,
        domain_hint=request.domain_hint,
        risk_hint=request.risk_hint,
        attributes=request.attributes,
    )


def _routing_decision_from_allowlist(allowlist_decision: str) -> ToolRoutingDecision:
    return {
        "allowed": "ready",
        "denied": "denied",
        "approval_required": "approval_required",
    }[allowlist_decision]


def create_tool_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    tool: ToolCreateInput,
) -> ToolCreateResponse:
    del user_id

    created = store.create_tool(
        tool_key=tool.tool_key,
        name=tool.name,
        description=tool.description,
        version=tool.version,
        metadata_version=tool.metadata_version,
        active=tool.active,
        tags=list(tool.tags),
        action_hints=list(tool.action_hints),
        scope_hints=list(tool.scope_hints),
        domain_hints=list(tool.domain_hints),
        risk_hints=list(tool.risk_hints),
        metadata=tool.metadata,
    )
    return {"tool": _serialize_tool(created)}


def list_tool_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> ToolListResponse:
    del user_id

    items = [_serialize_tool(tool) for tool in store.list_tools()]
    summary: ToolListSummary = {
        "total_count": len(items),
        "order": list(TOOL_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_tool_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    tool_id: UUID,
) -> ToolDetailResponse:
    del user_id

    tool = store.get_tool_optional(tool_id)
    if tool is None:
        raise ToolNotFoundError(f"tool {tool_id} was not found")
    return {"tool": _serialize_tool(tool)}


def evaluate_tool_allowlist(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ToolAllowlistEvaluationRequestInput,
) -> ToolAllowlistEvaluationResponse:
    del user_id

    thread = store.get_thread_optional(request.thread_id)
    if thread is None:
        raise ToolAllowlistValidationError(
            "thread_id must reference an existing thread owned by the user"
        )

    active_tools = store.list_active_tools()
    policy_context = load_policy_evaluation_context(
        store,
        thread_agent_profile_id=thread.get("agent_profile_id", DEFAULT_AGENT_PROFILE_ID),
    )

    allowed: list[ToolAllowlistDecisionRecord] = []
    denied: list[ToolAllowlistDecisionRecord] = []
    approval_required: list[ToolAllowlistDecisionRecord] = []
    tool_trace_events: list[tuple[str, dict[str, object]]] = []

    for tool in active_tools:
        classification = _classify_tool_request(
            tool=tool,
            request=request,
            policy_context=policy_context,
        )
        decision_record = _decision_record_from_classification(classification)

        if classification.decision == "allowed":
            allowed.append(decision_record)
        elif classification.decision == "approval_required":
            approval_required.append(decision_record)
        else:
            denied.append(decision_record)

        tool_trace_events.append(
            (
                "tool.allowlist.decision",
                _allowlist_trace_payload(classification),
            )
        )

    trace = store.create_trace(
        user_id=thread["user_id"],
        thread_id=thread["id"],
        kind=TRACE_KIND_TOOL_ALLOWLIST_EVALUATE,
        compiler_version=TOOL_ALLOWLIST_EVALUATION_VERSION_V0,
        status="completed",
        limits={
            "order": list(TOOL_LIST_ORDER),
            "active_tool_count": len(active_tools),
            "active_policy_count": len(policy_context.active_policies),
            "consent_count": len(policy_context.consents_by_key),
        },
    )

    trace_events: list[tuple[str, dict[str, object]]] = [
        (
            "tool.allowlist.request",
            {
                "thread_id": str(request.thread_id),
                "action": request.action,
                "scope": request.scope,
                "domain_hint": request.domain_hint,
                "risk_hint": request.risk_hint,
                "attributes": request.attributes,
            },
        ),
        (
            "tool.allowlist.order",
            {
                "order": list(TOOL_LIST_ORDER),
                "tool_ids": [str(tool["id"]) for tool in active_tools],
            },
        ),
        *tool_trace_events,
        (
            "tool.allowlist.summary",
            {
                "allowed_count": len(allowed),
                "denied_count": len(denied),
                "approval_required_count": len(approval_required),
            },
        ),
    ]
    for sequence_no, (kind, payload) in enumerate(trace_events, start=1):
        store.append_trace_event(
            trace_id=trace["id"],
            sequence_no=sequence_no,
            kind=kind,
            payload=payload,
        )

    summary: ToolAllowlistEvaluationSummary = {
        "action": request.action,
        "scope": request.scope,
        "domain_hint": request.domain_hint,
        "risk_hint": request.risk_hint,
        "evaluated_tool_count": len(active_tools),
        "allowed_count": len(allowed),
        "denied_count": len(denied),
        "approval_required_count": len(approval_required),
        "order": list(TOOL_LIST_ORDER),
    }
    trace_summary: ToolAllowlistTraceSummary = {
        "trace_id": str(trace["id"]),
        "trace_event_count": len(trace_events),
    }
    return {
        "allowed": allowed,
        "denied": denied,
        "approval_required": approval_required,
        "summary": summary,
        "trace": trace_summary,
    }


def route_tool_invocation(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ToolRoutingRequestInput,
) -> ToolRoutingResponse:
    del user_id

    thread = store.get_thread_optional(request.thread_id)
    if thread is None:
        raise ToolRoutingValidationError(
            "thread_id must reference an existing thread owned by the user"
        )

    tool = store.get_tool_optional(request.tool_id)
    if tool is None or tool["active"] is not True:
        raise ToolRoutingValidationError(
            "tool_id must reference an existing active tool owned by the user"
        )

    policy_context = load_policy_evaluation_context(
        store,
        thread_agent_profile_id=thread.get("agent_profile_id", DEFAULT_AGENT_PROFILE_ID),
    )
    classification = _classify_tool_request(
        tool=tool,
        request=_allowlist_request_from_routing(request),
        policy_context=policy_context,
    )
    routing_decision = _routing_decision_from_allowlist(classification.decision)

    trace = store.create_trace(
        user_id=thread["user_id"],
        thread_id=thread["id"],
        kind=TRACE_KIND_TOOL_ROUTE,
        compiler_version=TOOL_ROUTING_VERSION_V0,
        status="completed",
        limits={
            "order": list(TOOL_LIST_ORDER),
            "evaluated_tool_count": 1,
            "active_policy_count": len(policy_context.active_policies),
            "consent_count": len(policy_context.consents_by_key),
        },
    )

    request_payload: ToolRoutingRequestTracePayload = request.as_payload()
    decision_payload: ToolRoutingDecisionTracePayload = {
        "tool_id": classification.tool["id"],
        "tool_key": classification.tool["tool_key"],
        "tool_version": classification.tool["version"],
        "allowlist_decision": classification.decision,
        "routing_decision": routing_decision,
        "matched_policy_id": classification.matched_policy_id,
        "reasons": classification.reasons,
    }
    summary_payload: ToolRoutingSummaryTracePayload = {
        "decision": routing_decision,
        "evaluated_tool_count": 1,
        "active_policy_count": len(policy_context.active_policies),
        "consent_count": len(policy_context.consents_by_key),
    }
    trace_events = [
        ("tool.route.request", request_payload),
        ("tool.route.decision", decision_payload),
        ("tool.route.summary", summary_payload),
    ]
    for sequence_no, (kind, payload) in enumerate(trace_events, start=1):
        store.append_trace_event(
            trace_id=trace["id"],
            sequence_no=sequence_no,
            kind=kind,
            payload=payload,
        )

    summary: ToolRoutingSummary = {
        "thread_id": str(request.thread_id),
        "tool_id": classification.tool["id"],
        "action": request.action,
        "scope": request.scope,
        "domain_hint": request.domain_hint,
        "risk_hint": request.risk_hint,
        "decision": routing_decision,
        "evaluated_tool_count": 1,
        "active_policy_count": len(policy_context.active_policies),
        "consent_count": len(policy_context.consents_by_key),
        "order": list(TOOL_LIST_ORDER),
    }
    trace_summary: ToolRoutingTraceSummary = {
        "trace_id": str(trace["id"]),
        "trace_event_count": len(trace_events),
    }
    return {
        "request": request_payload,
        "decision": routing_decision,
        "tool": classification.tool,
        "reasons": classification.reasons,
        "summary": summary,
        "trace": trace_summary,
    }
