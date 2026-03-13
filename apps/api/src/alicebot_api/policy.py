from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from alicebot_api.contracts import (
    CONSENT_LIST_ORDER,
    POLICY_EVALUATION_VERSION_V0,
    POLICY_LIST_ORDER,
    TRACE_KIND_POLICY_EVALUATE,
    ConsentListResponse,
    ConsentListSummary,
    ConsentRecord,
    ConsentUpsertInput,
    ConsentUpsertResponse,
    PolicyCreateInput,
    PolicyCreateResponse,
    PolicyDetailResponse,
    PolicyEvaluationReason,
    PolicyEvaluationRequestInput,
    PolicyEvaluationResponse,
    PolicyEvaluationSummary,
    PolicyEvaluationTraceSummary,
    PolicyListResponse,
    PolicyListSummary,
    PolicyRecord,
    isoformat_or_none,
)
from alicebot_api.store import ConsentRow, ContinuityStore, PolicyRow


class PolicyValidationError(ValueError):
    """Raised when a policy or consent request fails explicit validation."""


class PolicyNotFoundError(LookupError):
    """Raised when a requested policy is not visible inside the current user scope."""


class PolicyEvaluationValidationError(ValueError):
    """Raised when a policy-evaluation request fails explicit validation."""


@dataclass(frozen=True, slots=True)
class PolicyEvaluationContext:
    active_policies: tuple[PolicyRow, ...]
    consents_by_key: dict[str, ConsentRow]


@dataclass(frozen=True, slots=True)
class PolicyEvaluationCoreDecision:
    decision: str
    matched_policy: PolicyRow | None
    reasons: list[PolicyEvaluationReason]


def _serialize_consent(consent: ConsentRow) -> ConsentRecord:
    return {
        "id": str(consent["id"]),
        "consent_key": consent["consent_key"],
        "status": consent["status"],
        "metadata": consent["metadata"],
        "created_at": consent["created_at"].isoformat(),
        "updated_at": consent["updated_at"].isoformat(),
    }


def _serialize_policy(policy: PolicyRow) -> PolicyRecord:
    return {
        "id": str(policy["id"]),
        "name": policy["name"],
        "action": policy["action"],
        "scope": policy["scope"],
        "effect": policy["effect"],
        "priority": policy["priority"],
        "active": policy["active"],
        "conditions": policy["conditions"],
        "required_consents": policy["required_consents"],
        "created_at": policy["created_at"].isoformat(),
        "updated_at": policy["updated_at"].isoformat(),
    }


def _dedupe_required_consents(required_consents: tuple[str, ...]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for consent_key in required_consents:
        if consent_key in seen:
            continue
        seen.add(consent_key)
        deduped.append(consent_key)
    return deduped


def _policy_matches(policy: PolicyRow, request: PolicyEvaluationRequestInput) -> bool:
    if policy["action"] != request.action or policy["scope"] != request.scope:
        return False

    conditions = policy["conditions"]
    for key, expected_value in conditions.items():
        if key not in request.attributes:
            return False
        if request.attributes[key] != expected_value:
            return False

    return True


def _build_reason(
    *,
    code: str,
    source: str,
    message: str,
    policy_id: UUID | None = None,
    consent_key: str | None = None,
) -> PolicyEvaluationReason:
    return {
        "code": code,
        "source": source,
        "message": message,
        "policy_id": None if policy_id is None else str(policy_id),
        "consent_key": consent_key,
    }


def upsert_consent_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    consent: ConsentUpsertInput,
) -> ConsentUpsertResponse:
    del user_id

    existing = store.get_consent_by_key_optional(consent.consent_key)
    if existing is None:
        created = store.create_consent(
            consent_key=consent.consent_key,
            status=consent.status,
            metadata=consent.metadata,
        )
        return {
            "consent": _serialize_consent(created),
            "write_mode": "created",
        }

    updated = store.update_consent(
        consent_id=existing["id"],
        status=consent.status,
        metadata=consent.metadata,
    )
    return {
        "consent": _serialize_consent(updated),
        "write_mode": "updated",
    }


def list_consent_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> ConsentListResponse:
    del user_id

    items = [_serialize_consent(consent) for consent in store.list_consents()]
    summary: ConsentListSummary = {
        "total_count": len(items),
        "order": list(CONSENT_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def create_policy_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    policy: PolicyCreateInput,
) -> PolicyCreateResponse:
    del user_id

    required_consents = _dedupe_required_consents(policy.required_consents)
    created = store.create_policy(
        name=policy.name,
        action=policy.action,
        scope=policy.scope,
        effect=policy.effect,
        priority=policy.priority,
        active=policy.active,
        conditions=policy.conditions,
        required_consents=required_consents,
    )
    return {"policy": _serialize_policy(created)}


def list_policy_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> PolicyListResponse:
    del user_id

    items = [_serialize_policy(policy) for policy in store.list_policies()]
    summary: PolicyListSummary = {
        "total_count": len(items),
        "order": list(POLICY_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_policy_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    policy_id: UUID,
) -> PolicyDetailResponse:
    del user_id

    policy = store.get_policy_optional(policy_id)
    if policy is None:
        raise PolicyNotFoundError(f"policy {policy_id} was not found")

    return {"policy": _serialize_policy(policy)}


def load_policy_evaluation_context(store: ContinuityStore) -> PolicyEvaluationContext:
    return PolicyEvaluationContext(
        active_policies=tuple(store.list_active_policies()),
        consents_by_key={consent["consent_key"]: consent for consent in store.list_consents()},
    )


def evaluate_policy_against_context(
    context: PolicyEvaluationContext,
    *,
    request: PolicyEvaluationRequestInput,
) -> PolicyEvaluationCoreDecision:
    matched_policy = next(
        (policy for policy in context.active_policies if _policy_matches(policy, request)),
        None,
    )

    reasons: list[PolicyEvaluationReason] = []
    decision = "deny"

    if matched_policy is None:
        reasons.append(
            _build_reason(
                code="no_matching_policy",
                source="system",
                message="No active policy matched the requested action, scope, and attributes.",
            )
        )
        return PolicyEvaluationCoreDecision(
            decision=decision,
            matched_policy=None,
            reasons=reasons,
        )

    reasons.append(
        _build_reason(
            code="matched_policy",
            source="policy",
            message=f"Matched policy '{matched_policy['name']}' at priority {matched_policy['priority']}.",
            policy_id=matched_policy["id"],
        )
    )

    missing_or_revoked = False
    for consent_key in matched_policy["required_consents"]:
        consent = context.consents_by_key.get(consent_key)
        if consent is None:
            missing_or_revoked = True
            reasons.append(
                _build_reason(
                    code="consent_missing",
                    source="consent",
                    message=f"Required consent '{consent_key}' is missing.",
                    policy_id=matched_policy["id"],
                    consent_key=consent_key,
                )
            )
            continue
        if consent["status"] != "granted":
            missing_or_revoked = True
            reasons.append(
                _build_reason(
                    code="consent_revoked",
                    source="consent",
                    message=f"Required consent '{consent_key}' is not granted (status={consent['status']}).",
                    policy_id=matched_policy["id"],
                    consent_key=consent_key,
                )
            )

    if not missing_or_revoked:
        decision = matched_policy["effect"]
        effect_code = {
            "allow": "policy_effect_allow",
            "deny": "policy_effect_deny",
            "require_approval": "policy_effect_require_approval",
        }[decision]
        reasons.append(
            _build_reason(
                code=effect_code,
                source="policy",
                message=f"Policy effect resolved the decision to '{decision}'.",
                policy_id=matched_policy["id"],
            )
        )

    return PolicyEvaluationCoreDecision(
        decision=decision,
        matched_policy=matched_policy,
        reasons=reasons,
    )


def evaluate_policy_request(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: PolicyEvaluationRequestInput,
) -> PolicyEvaluationResponse:
    del user_id

    thread = store.get_thread_optional(request.thread_id)
    if thread is None:
        raise PolicyEvaluationValidationError(
            "thread_id must reference an existing thread owned by the user"
        )

    context = load_policy_evaluation_context(store)
    core_decision = evaluate_policy_against_context(
        context,
        request=request,
    )

    trace = store.create_trace(
        user_id=thread["user_id"],
        thread_id=thread["id"],
        kind=TRACE_KIND_POLICY_EVALUATE,
        compiler_version=POLICY_EVALUATION_VERSION_V0,
        status="completed",
        limits={
            "order": list(POLICY_LIST_ORDER),
            "active_policy_count": len(context.active_policies),
            "consent_count": len(context.consents_by_key),
        },
    )

    trace_events = [
        (
            "policy.evaluate.request",
            {
                "thread_id": str(request.thread_id),
                "action": request.action,
                "scope": request.scope,
                "attributes": request.attributes,
            },
        ),
        (
            "policy.evaluate.order",
            {
                "order": list(POLICY_LIST_ORDER),
                "policy_ids": [str(policy["id"]) for policy in context.active_policies],
            },
        ),
        (
            "policy.evaluate.decision",
            {
                "decision": core_decision.decision,
                "matched_policy_id": (
                    None if core_decision.matched_policy is None else str(core_decision.matched_policy["id"])
                ),
                "reasons": core_decision.reasons,
                "evaluated_policy_count": len(context.active_policies),
                "consent_states": {
                    consent_key: {
                        "status": consent["status"],
                        "updated_at": isoformat_or_none(consent["updated_at"]),
                    }
                    for consent_key, consent in context.consents_by_key.items()
                },
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

    evaluation: PolicyEvaluationSummary = {
        "action": request.action,
        "scope": request.scope,
        "evaluated_policy_count": len(context.active_policies),
        "matched_policy_id": (
            None if core_decision.matched_policy is None else str(core_decision.matched_policy["id"])
        ),
        "order": list(POLICY_LIST_ORDER),
    }
    trace_summary: PolicyEvaluationTraceSummary = {
        "trace_id": str(trace["id"]),
        "trace_event_count": len(trace_events),
    }
    return {
        "decision": core_decision.decision,
        "matched_policy": (
            None if core_decision.matched_policy is None else _serialize_policy(core_decision.matched_policy)
        ),
        "reasons": core_decision.reasons,
        "evaluation": evaluation,
        "trace": trace_summary,
    }
