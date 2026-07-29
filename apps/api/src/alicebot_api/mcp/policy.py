"""MCP agent-identity resolution and policy enforcement helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import replace

from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    AgentIdentityValidationError,
    PolicyDecision,
    append_policy_events,
    evaluate_agent_policy,
)
from alicebot_api.vnext_agent_keys import AgentKeyAuthenticationError, resolve_agent_identity
from alicebot_api.vnext_promotion_policy import PromotionCandidate, PromotionSettings
from alicebot_api.vnext_store import PostgresVNextStore

from .runtime import _vnext_store_context
from .types import MCPRuntimeContext, MCPToolError


AGENT_API_KEY_ENV = "ALICE_AGENT_API_KEY"


def _agent_identity_from_arguments(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> AgentIdentity | None:
    """Resolve the calling agent's identity for one MCP tool call.

    Without ``ALICE_AGENT_API_KEY`` the MCP server is local operator tooling
    (it already holds direct database credentials), so payload identity is
    honored and carries the default ``unauthenticated_local`` auth marker.
    With the key set, identity is resolved and enforced against the issued
    key record exactly like the HTTP surface.
    """

    if context.agent_identity_resolved:
        return context.agent_identity

    raw_key = (os.environ.get(AGENT_API_KEY_ENV) or "").strip() or None
    if raw_key is None:
        try:
            return AgentIdentity.from_payload(arguments)
        except AgentIdentityValidationError as exc:
            raise MCPToolError(str(exc)) from exc
    try:
        with _vnext_store_context(context) as store:
            return resolve_agent_identity(
                store,
                user_id=context.user_id,
                raw_key=raw_key,
                payload=arguments,
            )
    except (AgentKeyAuthenticationError, AgentIdentityValidationError) as exc:
        raise MCPToolError(str(exc)) from exc


def _policy_checked(
    store: PostgresVNextStore,
    *,
    identity: AgentIdentity | None,
    action: str,
    domains: tuple[str, ...] = (),
    sensitivity_allowed: tuple[str, ...] = ("public", "internal", "private", "unknown"),
    project_scope: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
    require_explicit_project_scope: bool = False,
    require_unfiltered_target: bool = False,
    target_type: str | None = None,
    target_id: str | None = None,
    promotion_settings: PromotionSettings | None = None,
    promotion_candidate: PromotionCandidate | None = None,
    owner_verified: bool = False,
) -> tuple[str, str | None, PolicyDecision]:
    if identity is not None:
        store.upsert_agent_identity(
            {
                "agent_id": identity.agent_id,
                "agent_type": identity.agent_type,
                "permission_profile": identity.permission_profile,
                "project_scope_json": list(identity.project_scope),
                "metadata_json": {"last_agent_run_id": identity.agent_run_id, "last_task_id": identity.task_id},
            },
            actor_type="agent",
        )
    decision = evaluate_agent_policy(
        identity=identity,
        action=action,
        domains=domains,
        sensitivity_allowed=sensitivity_allowed,
        project_scope=project_scope,
        workflow_type=workflow_type,
        write_policy=write_policy,
        require_explicit_project_scope=require_explicit_project_scope,
        promotion_settings=promotion_settings,
        promotion_candidate=promotion_candidate,
        owner_verified=owner_verified,
    )
    if require_unfiltered_target and decision.decision == "allowed_with_filtering":
        decision = replace(
            decision,
            decision="blocked",
            reasons=tuple(dict.fromkeys((*decision.reasons, "artifact_target_filtering_not_permitted"))),
        )
    append_policy_events(
        store,
        identity=identity,
        decision=decision,
        target_type=target_type,
        target_id=target_id,
    )
    return ("agent", identity.agent_id, decision) if identity is not None else ("system", None, decision)


def _raise_mcp_policy_blocked(decision: PolicyDecision) -> None:
    raise MCPToolError(f"agent policy blocked: {', '.join(decision.reasons) or decision.action}")


def _mcp_agent_policy_preflight(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
    *,
    action: str,
    domains: tuple[str, ...] = (),
    sensitivity_allowed: tuple[str, ...] = ("public", "internal", "private", "unknown"),
    project_scope: tuple[str, ...] = (),
    workflow_type: str | None = None,
    write_policy: str | None = None,
) -> PolicyDecision:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    decision: PolicyDecision | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action=action,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            project_scope=project_scope,
            workflow_type=workflow_type,
            write_policy=write_policy,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if decision is None:
        raise MCPToolError("agent policy preflight did not complete")
    return decision
