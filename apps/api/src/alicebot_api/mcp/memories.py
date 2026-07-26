"""Mechanical MCP memories carrier."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import uuid4
from alicebot_api.store import JsonObject
from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    AgentPolicyBlockedError,
    PolicyDecision,
    agent_metadata,
    evaluate_agent_policy,
    resource_project_scope,
)
from alicebot_api.vnext_embeddings import DeferredMemoryEmbedding
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_memory_commit import (
    VNextMemoryCommitService,
    VNextMemoryCommitValidationError,
    memory_commit_request_from_payload,
)
from alicebot_api.vnext_project_update_guard import (
    PENDING_PROJECT_UPDATE_MEMORY_MUTATION_MESSAGE,
    is_pending_project_update_memory,
)
from alicebot_api.vnext_repositories import JsonObject as VNextJsonObject
from alicebot_api.vnext_store import (
    REDACTION_MARKER,
    is_redacted_memory,
    is_redacted_project_update_artifact,
)

from .shared import (
    MCPRuntimeContext,
    MCPToolError,
    _agent_identity_from_arguments,
    _json_object,
    _parse_int,
    _parse_optional_float,
    _parse_optional_text,
    _parse_required_text,
    _parse_string_list,
    _persist_vnext_deferred_embedding_inputs,
    _policy_checked,
    _raise_mcp_policy_blocked,
    _vnext_store_context,
)


def _handle_alice_vnext_propose_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    if identity is None:
        raise MCPToolError("agent_id is required for alice_vnext_propose_memory")
    proposal_type = _parse_optional_text(arguments, "proposal_type") or "candidate_memory"
    canonical_text = _parse_required_text(arguments, "canonical_text")
    domain = _parse_optional_text(arguments, "domain") or "unknown"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "unknown"
    blocked_decision: PolicyDecision | None = None
    memory: VNextJsonObject | None = None
    decision: PolicyDecision | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="memory.propose",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            proposal_id = _parse_optional_text(arguments, "proposal_id") or str(uuid4())
            memory = store.create_memory(
                {
                    "memory_type": {
                        "decision": "decision",
                        "project_update": "project_state",
                        "belief_update": "belief",
                        "contradiction": "contradiction",
                        "artifact_summary": "artifact_summary",
                        "open_loop": "open_loop",
                    }.get(proposal_type, "semantic"),
                    "memory_key": f"agent_proposal.{proposal_type}.{proposal_id}",
                    "value": {"proposal_type": proposal_type, "text": canonical_text},
                    "status": "candidate",
                    "confidence": _parse_optional_float(arguments, "confidence") or 0.5,
                    "title": _parse_optional_text(arguments, "title") or canonical_text[:120],
                    "canonical_text": canonical_text,
                    "summary": canonical_text[:280],
                    "domain": domain,
                    "sensitivity": sensitivity,
                    "metadata_json": {
                        "proposal_type": proposal_type,
                        "review_required": True,
                        **agent_metadata(identity, decision),
                    },
                },
                actor_type="agent",
            )
            append_event(
                store,
                event_type="agent.memory_proposed",
                actor_type="agent",
                actor_id=identity.agent_id,
                target_type="memory",
                target_id=str(memory["id"]),
                trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                run_id=identity.agent_run_id,
                payload={"proposal_type": proposal_type, "agent_identity": identity.to_record()},
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if memory is None or decision is None:
        raise MCPToolError("vNext memory proposal did not complete")
    return _json_object({"proposal": memory, "policy_decision": decision.to_record(), "review_required": True})


def _handle_alice_vnext_commit_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    payload: VNextJsonObject | None = None
    confidence = _parse_optional_float(arguments, "confidence")
    request = memory_commit_request_from_payload(
        {
            "title": _parse_required_text(arguments, "title"),
            "canonical_text": _parse_required_text(arguments, "canonical_text"),
            "memory_type": _parse_optional_text(arguments, "memory_type") or "semantic",
            "domain": _parse_optional_text(arguments, "domain") or "unknown",
            "sensitivity": _parse_optional_text(arguments, "sensitivity") or "unknown",
            "confidence": 0.9 if confidence is None else confidence,
            "intent": _parse_optional_text(arguments, "intent") or "explicit_remember",
            "source_type": _parse_optional_text(arguments, "source_type") or "direct_user_instruction",
            "source_refs": list(_parse_string_list(arguments, "source_refs")),
            "conversation_excerpt": _parse_optional_text(arguments, "conversation_excerpt"),
            "rationale": _parse_optional_text(arguments, "rationale"),
            "idempotency_key": _parse_optional_text(arguments, "idempotency_key"),
            "project_scope": list(_parse_string_list(arguments, "project_scope")),
            "contradiction_refs": list(_parse_string_list(arguments, "contradiction_refs")),
            "trace_id": _parse_optional_text(arguments, "trace_id"),
        },
        user_id=context.user_id,
    )
    with _vnext_store_context(context) as store:
        service = VNextMemoryCommitService(store, defer_embeddings=True)
        payload = service.commit(identity=identity, request=request)
        deferred_embedding_inputs = service.deferred_embedding_inputs
    _persist_vnext_deferred_embedding_inputs(
        context,
        deferred_embedding_inputs,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
        trace_id=request.trace_id,
    )
    return _json_object(payload)


def _handle_alice_vnext_confirm_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    deferred_embedding_inputs: tuple[DeferredMemoryEmbedding, ...] = ()
    with _vnext_store_context(context) as store:
        try:
            service = VNextMemoryCommitService(store, defer_embeddings=True)
            payload = service.confirm(
                identity=identity,
                confirmation_id=_parse_required_text(arguments, "confirmation_id"),
                action=_parse_optional_text(arguments, "action") or "confirm",
                canonical_text=_parse_optional_text(arguments, "canonical_text"),
                rationale=_parse_optional_text(arguments, "rationale"),
            )
            deferred_embedding_inputs = service.deferred_embedding_inputs
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory confirmation did not complete")
    _persist_vnext_deferred_embedding_inputs(
        context,
        deferred_embedding_inputs,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
        trace_id=_parse_optional_text(arguments, "trace_id"),
    )
    return _json_object(payload)


def _handle_alice_vnext_undo_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    with _vnext_store_context(context) as store:
        try:
            payload = VNextMemoryCommitService(store).undo(
                identity=identity,
                memory_id=_parse_optional_text(arguments, "memory_id"),
                reason=_parse_optional_text(arguments, "reason"),
                superseded_by_memory_id=_parse_optional_text(arguments, "superseded_by"),
            )
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory undo did not complete")
    return _json_object(payload)


def _handle_alice_vnext_correct_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    deferred_embedding_inputs: tuple[DeferredMemoryEmbedding, ...] = ()
    with _vnext_store_context(context) as store:
        try:
            service = VNextMemoryCommitService(store, defer_embeddings=True)
            payload = service.correct(
                identity=identity,
                memory_id=_parse_required_text(arguments, "memory_id"),
                canonical_text=_parse_required_text(arguments, "canonical_text"),
                reason=_parse_optional_text(arguments, "reason"),
            )
            deferred_embedding_inputs = service.deferred_embedding_inputs
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory correction did not complete")
    _persist_vnext_deferred_embedding_inputs(
        context,
        deferred_embedding_inputs,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
        trace_id=_parse_optional_text(arguments, "trace_id"),
    )
    return _json_object(payload)


def _handle_alice_vnext_forget_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    with _vnext_store_context(context) as store:
        try:
            payload = VNextMemoryCommitService(store).forget(
                identity=identity,
                memory_id=_parse_required_text(arguments, "memory_id"),
                reason=_parse_optional_text(arguments, "reason"),
            )
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory forget did not complete")
    return _json_object(payload)


_REDACT_RETIRED_STATUSES = {"superseded", "archived", "rejected"}


def _memory_redaction_is_exact(memory: Mapping[str, object]) -> bool:
    return is_redacted_memory(memory)


def redact_memory_flow(
    store,
    *,
    memory_id: str,
    reason: str,
    identity: AgentIdentity | None = None,
) -> VNextJsonObject:
    """Scrub one memory's governed lifecycle copies, keeping the audit skeleton.

    Order: forget/archive first (when the row is still live, so the
    lifecycle trail records why it left recall), then redact the memory row
    content, its revisions, matching event payloads and quoted provenance,
    plus any coupled terminal project-update artifact copies. The skeleton —
    ids, types, timestamps, actors, and the ``memory.redacted`` event trail —
    survives, which is what proves redaction happened. Source and source-chunk
    evidence is intentionally retained because it may support other memories;
    removing that evidence requires separate source hygiene.

    Policy is the caller's job: ``memory.redact`` is restricted to a human
    or an admin agent (HUMAN_OR_ADMIN_ACTIONS); every surface (MCP, HTTP,
    CLI) must evaluate it before calling this flow.
    """
    reason_text = " ".join(reason.split()).strip() if isinstance(reason, str) else ""
    if not reason_text:
        raise VNextMemoryCommitValidationError("reason is required to redact a memory")
    memory_service = VNextMemoryCommitService(store)
    memory_service.lock_supersession_graph()
    memory = store.get_memory_for_redaction(memory_id)
    if memory is None:
        raise VNextMemoryCommitValidationError("memory was not found")
    if is_pending_project_update_memory(memory):
        raise VNextMemoryCommitValidationError(PENDING_PROJECT_UPDATE_MEMORY_MUTATION_MESSAGE)
    project_update_artifacts = store.lock_project_update_artifacts_for_redaction(memory_id)
    if any(str(artifact.get("status") or "") not in {"accepted", "rejected"} for artifact in project_update_artifacts):
        raise VNextMemoryCommitValidationError(PENDING_PROJECT_UPDATE_MEMORY_MUTATION_MESSAGE)

    artifact_ids = [str(artifact.get("id") or "") for artifact in project_update_artifacts]
    exact_replay = _memory_redaction_is_exact(memory) and all(
        is_redacted_project_update_artifact(artifact) for artifact in project_update_artifacts
    )
    exact_bundle_check = getattr(store, "memory_redaction_bundle_is_exact", None)
    exact_replay = bool(exact_replay and callable(exact_bundle_check) and exact_bundle_check(memory_id, artifact_ids))
    if exact_replay:
        # Preserve strict no-write idempotence for authenticated agents: the
        # ordinary policy adapter upserts the identity and appends a policy
        # event.  A replay still evaluates the same authorization, but does not
        # create new durable rows.
        decision = evaluate_agent_policy(
            identity=identity,
            action="memory.redact",
            domains=(str(memory.get("domain") or "unknown"),),
            sensitivity_allowed=(str(memory.get("sensitivity") or "unknown"),),
            project_scope=resource_project_scope(memory),
            require_explicit_project_scope=True,
        )
        if decision.decision == "blocked":
            raise AgentPolicyBlockedError(decision)
    else:
        memory_service.authorize_memory_action(
            identity=identity,
            action="memory.redact",
            memory=memory,
        )
    actor_type = "agent" if identity is not None else "user"
    forgotten_first = False
    if str(memory.get("status") or "") not in _REDACT_RETIRED_STATUSES:
        memory_service.forget(identity=identity, memory_id=memory_id, reason=reason_text)
        forgotten_first = True
    elif not exact_replay:
        # Rows retired through an older path may still predate occurrence
        # lifecycle integration. Close any surviving reviewed units before
        # redaction removes the evidence needed to do so truthfully.
        memory_service.retire_memory_occurrence_state(
            memory,
            identity=identity,
            stage="memory_redaction",
            reason=reason_text,
        )
    result = store.redact_memory_bundle(
        memory_id=memory_id,
        project_update_artifacts=project_update_artifacts,
        actor_type=actor_type,
    )
    return {
        "status": "redacted",
        "memory": result.get("memory"),
        "forgotten_first": forgotten_first,
        "redacted_revisions": result.get("redacted_revisions"),
        "redacted_events": result.get("redacted_events"),
        "redacted_artifacts": result.get("redacted_artifacts"),
        "redacted_artifact_ids": result.get("redacted_artifact_ids"),
        "redacted_quality_ratings": result.get("redacted_quality_ratings"),
        "redacted_provenance_links": result.get("redacted_provenance_links"),
        "redacted_occurrence_evidence": result.get("redacted_occurrence_evidence"),
        "redacted_occurrence_claims": result.get("redacted_occurrence_claims"),
        "redacted_occurrence_units": result.get("redacted_occurrence_units"),
        "idempotent_replay": result.get("idempotent_replay"),
        "redaction_marker": REDACTION_MARKER,
        "reason": reason_text,
    }


def _handle_alice_vnext_expire_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    with _vnext_store_context(context) as store:
        # The commit service policy-checks memory.expire itself (and appends
        # the policy events); a tool-level pre-check would double-log.
        try:
            payload = VNextMemoryCommitService(store).expire(
                _parse_required_text(arguments, "memory_id"),
                valid_to=_parse_optional_text(arguments, "valid_to"),
                reason=_parse_required_text(arguments, "reason"),
                identity=identity,
            )
        except AgentPolicyBlockedError as exc:
            # Exit the store context normally so the blocked-policy audit
            # events commit before the tool error is raised.
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory expire did not complete")
    return _json_object(payload)


def _handle_alice_vnext_unexpire_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    with _vnext_store_context(context) as store:
        try:
            payload = VNextMemoryCommitService(store).unexpire(
                _parse_required_text(arguments, "memory_id"),
                reason=_parse_required_text(arguments, "reason"),
                identity=identity,
            )
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory unexpire did not complete")
    return _json_object(payload)


def _handle_alice_vnext_accept_consolidation(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    deferred_embedding_inputs: tuple[DeferredMemoryEmbedding, ...] = ()
    with _vnext_store_context(context) as store:
        # Acceptance is a review decision: the commit service policy-checks
        # it internally (human or admin agent only).
        try:
            service = VNextMemoryCommitService(store, defer_embeddings=True)
            payload = service.accept_consolidation_candidate(
                _parse_required_text(arguments, "memory_id"),
                reason=_parse_required_text(arguments, "reason"),
                identity=identity,
            )
            deferred_embedding_inputs = service.deferred_embedding_inputs
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext consolidation acceptance did not complete")
    _persist_vnext_deferred_embedding_inputs(
        context,
        deferred_embedding_inputs,
        actor_type="agent" if identity is not None else "user",
        actor_id=identity.agent_id if identity is not None else None,
    )
    return _json_object(payload)


def _handle_alice_vnext_redact_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    with _vnext_store_context(context) as store:
        try:
            payload = redact_memory_flow(
                store,
                memory_id=_parse_required_text(arguments, "memory_id"),
                reason=_parse_required_text(arguments, "reason"),
                identity=identity,
            )
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory redaction did not complete")
    return _json_object(payload)


_MEMORY_MANAGE_ACTIONS = (
    "confirm",
    "undo",
    "forget",
    "expire",
    "unexpire",
    "accept_consolidation",
    "redact",
)


def _handle_alice_memory_manage(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    """Core-surface lifecycle verbs for memories written via alice_memory_commit.

    Dispatches to the same policy-checked commit-service handlers as the
    legacy alice_vnext_confirm_memory / alice_vnext_undo_memory /
    alice_vnext_forget_memory tools; no logic is duplicated here. The
    expire/unexpire/accept_consolidation/redact actions route to the v0.9
    commit-service seams (and the store redaction methods) the same way.
    """
    action = (_parse_optional_text(arguments, "action") or "").casefold()
    if action not in _MEMORY_MANAGE_ACTIONS:
        allowed = ", ".join(_MEMORY_MANAGE_ACTIONS)
        raise MCPToolError(f"action must be one of: {allowed}")

    delegate_arguments = {key: value for key, value in arguments.items() if key != "action"}
    if action == "confirm":
        # The underlying confirm verb distinguishes plain confirmation from
        # confirm-with-correction; surface both through one action by keying
        # off canonical_text so the revision history records 'corrected'.
        delegate_arguments["action"] = (
            "edit" if _parse_optional_text(arguments, "canonical_text") is not None else "confirm"
        )
        reason = _parse_optional_text(arguments, "reason")
        if reason is not None and "rationale" not in delegate_arguments:
            delegate_arguments["rationale"] = reason
        return _handle_alice_vnext_confirm_memory(context, delegate_arguments)
    if action == "undo":
        return _handle_alice_vnext_undo_memory(context, delegate_arguments)
    if action == "expire":
        return _handle_alice_vnext_expire_memory(context, delegate_arguments)
    if action == "unexpire":
        return _handle_alice_vnext_unexpire_memory(context, delegate_arguments)
    if action == "accept_consolidation":
        return _handle_alice_vnext_accept_consolidation(context, delegate_arguments)
    if action == "redact":
        return _handle_alice_vnext_redact_memory(context, delegate_arguments)
    return _handle_alice_vnext_forget_memory(context, delegate_arguments)


def _handle_alice_vnext_recent_memory_commits(
    context: MCPRuntimeContext, arguments: Mapping[str, object]
) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: VNextJsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="memory.recent_commits")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextMemoryCommitService(store).recent_commits(
                limit=_parse_int(arguments, key="limit", default=20, minimum=1, maximum=100)
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext recent memory commits did not complete")
    return _json_object(payload)
