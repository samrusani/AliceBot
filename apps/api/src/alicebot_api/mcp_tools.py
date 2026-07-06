from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid4

from psycopg.errors import CheckViolation

from alicebot_api.continuity_capture import (
    ContinuityCaptureValidationError,
    capture_continuity_candidates,
    commit_continuity_captures,
)
from alicebot_api.continuity_brief import (
    ContinuityBriefValidationError,
    compile_continuity_brief,
)
from alicebot_api.continuity_evidence import (
    ContinuityEvidenceNotFoundError,
    build_continuity_explain,
    get_continuity_artifact_detail,
)
from alicebot_api.continuity_contradictions import (
    ContinuityContradictionNotFoundError,
    ContinuityContradictionValidationError,
    get_contradiction_case,
    list_contradiction_cases,
    resolve_contradiction_case,
    sync_contradictions,
)
from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError,
    RetrievalTraceNotFoundError,
    get_retrieval_trace,
    query_continuity_recall,
)
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError,
    compile_continuity_resumption_brief,
)
from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError,
    ContinuityReviewValidationError,
    apply_continuity_correction,
    get_continuity_review_detail,
    list_continuity_review_queue,
)
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.memory_mutations import (
    MemoryMutationValidationError,
    commit_memory_operations,
    generate_memory_operation_candidates,
    list_memory_operation_candidates,
    list_memory_operations,
)
from alicebot_api.contracts import (
    CONTINUITY_CAPTURE_COMMIT_MODES,
    CONTINUITY_CORRECTION_ACTIONS,
    CONTINUITY_BRIEF_TYPE_ORDER,
    CONTRADICTION_RESOLUTION_ACTIONS,
    CONTINUITY_REVIEW_QUEUE_ORDER,
    CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    ContinuityCaptureCandidatesInput,
    ContinuityCaptureCommitInput,
    ContinuityBriefRequestInput,
    ContradictionCaseListQueryInput,
    ContradictionResolveInput,
    ContradictionSyncInput,
    ContinuityCorrectionInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    ContinuityReviewQueueQueryInput,
    MemoryOperationCommitInput,
    MemoryOperationGenerateInput,
    MemoryOperationListInput,
    TaskBriefCompileRequestInput,
    TemporalExplainQueryInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
    TrustSignalListQueryInput,
)
from alicebot_api.config import get_settings
from alicebot_api.db import user_connection
from alicebot_api.sqlite_store import SQLiteVNextStore, sqlite_user_connection
from alicebot_api.store import ContinuityStore, JsonObject
from alicebot_api.temporal_state import (
    TemporalStateValidationError,
    get_temporal_explain,
    get_temporal_state_at,
    get_temporal_timeline,
)
from alicebot_api.task_briefing import (
    TaskBriefNotFoundError,
    TaskBriefValidationError,
    compare_task_briefs,
    compile_and_persist_task_brief,
    get_persisted_task_brief,
)
from alicebot_api.vnext_agent_control import (
    AgentIdentity,
    AgentIdentityValidationError,
    AgentPolicyBlockedError,
    PolicyDecision,
    agent_metadata,
    append_policy_events,
    evaluate_agent_policy,
)
from alicebot_api.vnext_agent_keys import (
    AgentKeyAuthenticationError,
    resolve_agent_identity,
)
from alicebot_api.vnext_brain import BrainArtifactRequest, VNextBrainService
from alicebot_api.vnext_capture import VNextCaptureService
from alicebot_api.vnext_connections import ConnectionFinderRequest, VNextConnectionService
from alicebot_api.vnext_context_tree import ContextTreeRequest, VNextContextTreeService
from alicebot_api.vnext_connectors import VNextConnectorService
from alicebot_api.vnext_contradictions import ContradictionFinderRequest, VNextContradictionService
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_memory_commit import (
    VNextMemoryCommitService,
    VNextMemoryCommitValidationError,
    VNEXT_DOMAINS,
    VNEXT_MEMORY_TYPES,
    VNEXT_SENSITIVITY_LEVELS,
    memory_commit_request_from_payload,
)
from alicebot_api.vnext_projects import OPEN_LOOP_ACTIONS, ProjectAutomationRequest, VNextProjectService
from alicebot_api.vnext_queue import QueueTaskRequest, VNextQueueService
from alicebot_api.vnext_retrieval import (
    BUDGET_STRATEGIES,
    BUDGET_STRATEGY_BALANCED,
    CONTEXT_DEPTHS,
    CONTEXT_DEPTH_LOW,
    CONTEXT_DEPTH_MINIMAL,
    CONTEXT_DEPTH_MINIMAL_MAX_ITEMS,
    GRAPH_STAGE_ENABLED,
    MEMORY_ENTITY_EDGE_TYPES,
    RRF_K,
    STAGE_DISABLED_MINIMAL,
    VECTOR_STAGE_ENABLED,
    VNextRetrievalRequest,
    VNextRetrievalService,
    _order_memories_for_strategy,
    reciprocal_rank_fusion,
)
from alicebot_api.vnext_scheduler import SchedulerRunRequest, VNextSchedulerService
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_store import REDACTION_MARKER, PostgresVNextStore


_REVIEW_STATUS_CHOICES = (
    "pending_review",
    "correction_ready",
    "active",
    "stale",
    "superseded",
    "deleted",
    "all",
)
_REVIEW_STATUS_ALIASES = {
    "pending": "pending_review",
}
_REVIEW_APPLY_ACTION_CHOICES = (
    "approve",
    "edit-and-approve",
    "reject",
    "supersede-existing",
)
_REVIEW_APPLY_ACTION_ALIASES = {
    "edit_and_approve": "edit-and-approve",
    "supersede_existing": "supersede-existing",
}
_REVIEW_APPLY_TO_CORRECTION_ACTION = {
    "approve": "confirm",
    "edit-and-approve": "edit",
    "reject": "delete",
    "supersede-existing": "supersede",
}
MCP_LEGACY_TOOLS_ENV = "ALICE_MCP_LEGACY_TOOLS"
_LEGACY_ENABLED_VALUES = {"1", "true", "yes", "on"}
_DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
_RECALL_DEFAULT_LIMIT = 8
_RECALL_MAX_LIMIT = 50
_OPEN_LOOP_TOOL_ACTIONS = ("list", *sorted(OPEN_LOOP_ACTIONS))
_PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0 = "alice_prefetch_context_v0"
_MODEL_GENERATION_MODES = ("deterministic", "model_backed")
_MODEL_ROUTE_MODES = ("local_only", "cloud_allowed", "cloud_requires_approval", "model_disabled")
_MODEL_GENERATION_SCHEMA_PROPERTIES: dict[str, object] = {
    "generation_mode": {"type": "string", "enum": list(_MODEL_GENERATION_MODES)},
    "model_route_mode": {"type": "string", "enum": list(_MODEL_ROUTE_MODES)},
    "model_provider": {"type": "string"},
    "model": {"type": "string"},
    "model_temperature": {"type": "number", "minimum": 0.0, "maximum": 2.0},
    "allow_cloud_private": {"type": "boolean"},
}


class MCPToolError(ValueError):
    """Raised when MCP tool input or execution fails."""


class MCPToolNotFoundError(LookupError):
    """Raised when an MCP tool name is not supported."""


@dataclass(frozen=True, slots=True)
class MCPRuntimeContext:
    database_url: str
    user_id: UUID


_SQLITE_POSTGRES_ONLY_MESSAGE = (
    "this tool requires the Postgres backend; the SQLite on-ramp serves the core tools only"
)


def _is_sqlite_backend(context: MCPRuntimeContext) -> bool:
    return context.database_url.startswith("sqlite:")


def _sqlite_path_from_url(database_url: str) -> str:
    """Extract the database file path from a ``sqlite:///`` URL.

    Accepts both the three-slash (``sqlite:///Users/x/memory.db``) and the
    SQLAlchemy-style four-slash (``sqlite:////Users/x/memory.db``) absolute
    forms; both resolve to ``/Users/x/memory.db``.
    """
    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise MCPToolError(f"expected a sqlite:/// database URL, got '{database_url}'")
    if parsed.netloc not in {"", "localhost"}:
        raise MCPToolError("sqlite database URLs must reference a local file path")
    path = unquote(parsed.path)
    while path.startswith("//"):
        path = path[1:]
    if path in {"", "/"}:
        raise MCPToolError("sqlite database URL must include a database file path")
    return path


@contextmanager
def _store_context(context: MCPRuntimeContext):
    if _is_sqlite_backend(context):
        raise MCPToolError(_SQLITE_POSTGRES_ONLY_MESSAGE)
    with user_connection(context.database_url, context.user_id) as conn:
        yield ContinuityStore(conn)


@contextmanager
def _vnext_store_context(context: MCPRuntimeContext):
    if _is_sqlite_backend(context):
        sqlite_path = _sqlite_path_from_url(context.database_url)
        with sqlite_user_connection(sqlite_path, context.user_id) as conn:
            yield SQLiteVNextStore(conn, context.user_id)
        return
    with user_connection(context.database_url, context.user_id) as conn:
        yield PostgresVNextStore(conn)


def _normalize_arguments(arguments: object) -> Mapping[str, object]:
    if arguments is None:
        return {}
    if not isinstance(arguments, Mapping):
        raise MCPToolError("tool arguments must be a JSON object")
    return arguments


def _parse_optional_text(arguments: Mapping[str, object], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MCPToolError(f"{key} must be a string")
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        return None
    return normalized


def _parse_required_text(arguments: Mapping[str, object], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str):
        raise MCPToolError(f"{key} is required and must be a string")
    normalized = " ".join(value.split()).strip()
    if normalized == "":
        raise MCPToolError(f"{key} must not be empty")
    return normalized


def _parse_optional_uuid(arguments: Mapping[str, object], key: str) -> UUID | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MCPToolError(f"{key} must be a UUID string")
    try:
        return UUID(value)
    except ValueError as exc:
        raise MCPToolError(f"{key} must be a valid UUID") from exc


def _parse_required_uuid(arguments: Mapping[str, object], key: str) -> UUID:
    value = _parse_optional_uuid(arguments, key)
    if value is None:
        raise MCPToolError(f"{key} is required and must be a UUID string")
    return value


def _parse_optional_datetime(arguments: Mapping[str, object], key: str) -> datetime | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise MCPToolError(f"{key} must be an ISO-8601 datetime string")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MCPToolError(f"{key} must be an ISO-8601 datetime string") from exc


def _parse_int(
    arguments: Mapping[str, object],
    *,
    key: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = arguments.get(key, default)
    if isinstance(value, bool):
        raise MCPToolError(f"{key} must be an integer")

    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            raise MCPToolError(f"{key} must be an integer")
        try:
            parsed = int(stripped)
        except ValueError as exc:
            raise MCPToolError(f"{key} must be an integer") from exc
    else:
        raise MCPToolError(f"{key} must be an integer")

    if parsed < minimum or parsed > maximum:
        raise MCPToolError(f"{key} must be between {minimum} and {maximum}")
    return parsed


def _parse_optional_json_object(arguments: Mapping[str, object], key: str) -> JsonObject | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MCPToolError(f"{key} must be a JSON object")
    return value


def _parse_string_list(arguments: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = arguments.get(key)
    if value is None:
        return ()
    if isinstance(value, str):
        normalized = " ".join(value.split()).strip()
        return (normalized,) if normalized else ()
    if not isinstance(value, list):
        raise MCPToolError(f"{key} must be a string array")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise MCPToolError(f"{key} must be a string array")
        normalized = " ".join(item.split()).strip()
        if normalized:
            output.append(normalized)
    return tuple(output)


def _parse_memory_types(arguments: Mapping[str, object], *, key: str = "memory_types") -> tuple[str, ...]:
    """Parse an optional typed-memory filter, validating against the canonical enum."""
    values = _parse_string_list(arguments, key)
    invalid = sorted({value for value in values if value not in VNEXT_MEMORY_TYPES})
    if invalid:
        raise MCPToolError(
            f"{key} contains unsupported values: {', '.join(invalid)}; "
            f"allowed values are: {', '.join(VNEXT_MEMORY_TYPES)}"
        )
    return values


def _retrieval_filter_kwargs(arguments: Mapping[str, object]) -> dict[str, object]:
    """Optional typed/scoped retrieval filters, passed through only when set.

    ``memory_types``, ``projects``, and ``created_by_agents`` (forwarded as
    ``created_by_agent_ids``) are keyword arguments so the retrieval service
    signature stays the source of truth; when a filter is not requested the
    argument is omitted entirely and the service defaults (``()``) apply.
    """
    kwargs: dict[str, object] = {}
    memory_types = _parse_memory_types(arguments)
    if memory_types:
        kwargs["memory_types"] = memory_types
    projects = _parse_string_list(arguments, "projects")
    if projects:
        kwargs["projects"] = projects
    created_by_agents = _parse_string_list(arguments, "created_by_agents")
    if created_by_agents:
        kwargs["created_by_agent_ids"] = created_by_agents
    return kwargs


AGENT_API_KEY_ENV = "ALICE_AGENT_API_KEY"


def _agent_identity_from_arguments(
    context: MCPRuntimeContext, arguments: Mapping[str, object]
) -> AgentIdentity | None:
    """Resolve the calling agent's identity for one MCP tool call.

    Without ``ALICE_AGENT_API_KEY`` the MCP server is local operator tooling
    (it already holds direct database credentials), so payload identity is
    honored and carries the default ``unauthenticated_local`` auth marker.
    With the key set, identity is resolved and enforced against the issued
    key record exactly like the HTTP surface.
    """

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
) -> tuple[str, str | None, object]:
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
    )
    append_policy_events(store, identity=identity, decision=decision)
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


def _parse_task_brief_request(arguments: Mapping[str, object], *, mode_key: str = "mode") -> TaskBriefCompileRequestInput:
    mode_value = arguments.get(mode_key)
    if not isinstance(mode_value, str):
        raise MCPToolError(f"{mode_key} is required and must be a string")
    normalized_mode = mode_value.strip()
    if normalized_mode == "":
        raise MCPToolError(f"{mode_key} must not be empty")
    token_budget = arguments.get("token_budget")
    parsed_token_budget: int | None
    if token_budget is None:
        parsed_token_budget = None
    else:
        parsed_token_budget = _parse_int(
            arguments,
            key="token_budget",
            default=DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
            minimum=1,
            maximum=MAX_TASK_BRIEF_TOKEN_BUDGET,
        )
    return TaskBriefCompileRequestInput(
        mode=normalized_mode,  # type: ignore[arg-type]
        query=_parse_optional_text(arguments, "query"),
        workspace_id=_parse_optional_uuid(arguments, "workspace_id"),
        pack_id=_parse_optional_text(arguments, "pack_id"),
        pack_version=_parse_optional_text(arguments, "pack_version"),
        thread_id=_parse_optional_uuid(arguments, "thread_id"),
        task_id=_parse_optional_uuid(arguments, "task_id"),
        project=_parse_optional_text(arguments, "project"),
        person=_parse_optional_text(arguments, "person"),
        since=_parse_optional_datetime(arguments, "since"),
        until=_parse_optional_datetime(arguments, "until"),
        include_non_promotable_facts=_parse_bool(
            arguments,
            key="include_non_promotable_facts",
            default=False,
        ),
        provider_strategy=_parse_optional_text(arguments, "provider_strategy"),
        model_pack_strategy=_parse_optional_text(arguments, "model_pack_strategy"),
        token_budget=parsed_token_budget,
    )


def _parse_continuity_brief_request(arguments: Mapping[str, object]) -> ContinuityBriefRequestInput:
    brief_type_value = arguments.get("brief_type", "general")
    if not isinstance(brief_type_value, str) or brief_type_value.strip() == "":
        raise MCPToolError("brief_type must be a string")
    brief_type = brief_type_value.strip()
    if brief_type not in CONTINUITY_BRIEF_TYPE_ORDER:
        raise MCPToolError("brief_type must be one of: " + ", ".join(CONTINUITY_BRIEF_TYPE_ORDER))
    return ContinuityBriefRequestInput(
        brief_type=brief_type,  # type: ignore[arg-type]
        query=_parse_optional_text(arguments, "query"),
        thread_id=_parse_optional_uuid(arguments, "thread_id"),
        task_id=_parse_optional_uuid(arguments, "task_id"),
        project=_parse_optional_text(arguments, "project"),
        person=_parse_optional_text(arguments, "person"),
        since=_parse_optional_datetime(arguments, "since"),
        until=_parse_optional_datetime(arguments, "until"),
        max_relevant_facts=_parse_int(
            arguments,
            key="max_relevant_facts",
            default=DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        ),
        max_recent_changes=_parse_int(
            arguments,
            key="max_recent_changes",
            default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        ),
        max_open_loops=_parse_int(
            arguments,
            key="max_open_loops",
            default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ),
        max_conflicts=_parse_int(
            arguments,
            key="max_conflicts",
            default=DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        ),
        max_timeline_highlights=_parse_int(
            arguments,
            key="max_timeline_highlights",
            default=DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
            minimum=0,
            maximum=MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
        ),
        include_non_promotable_facts=_parse_bool(
            arguments,
            key="include_non_promotable_facts",
            default=False,
        ),
    )


def _parse_optional_float(arguments: Mapping[str, object], key: str) -> float | None:
    value = arguments.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise MCPToolError(f"{key} must be a number")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError as exc:
            raise MCPToolError(f"{key} must be a number") from exc
    raise MCPToolError(f"{key} must be a number")


def _parse_bool(arguments: Mapping[str, object], *, key: str, default: bool = False) -> bool:
    value = arguments.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise MCPToolError(f"{key} must be a boolean")


def _parse_optional_bool(arguments: Mapping[str, object], *, key: str) -> bool | None:
    """Tri-state boolean: absent (or null) means "caller did not specify".

    Retrieval flags such as ``include_sources`` treat None as "let the
    context_depth tier decide", so absence must stay distinguishable from an
    explicit false.
    """
    if arguments.get(key) is None:
        return None
    return _parse_bool(arguments, key=key)


def _parse_context_pack_tuning(arguments: Mapping[str, object]) -> tuple[str, str]:
    """Validated (context_depth, budget_strategy) pair with tier defaults."""
    depth = _parse_optional_text(arguments, "context_depth") or CONTEXT_DEPTH_LOW
    if depth not in CONTEXT_DEPTHS:
        raise MCPToolError(f"context_depth must be one of: {', '.join(CONTEXT_DEPTHS)}")
    strategy = _parse_optional_text(arguments, "budget_strategy") or BUDGET_STRATEGY_BALANCED
    if strategy not in BUDGET_STRATEGIES:
        raise MCPToolError(f"budget_strategy must be one of: {', '.join(BUDGET_STRATEGIES)}")
    return depth, strategy


def _parse_model_generation_kwargs(arguments: Mapping[str, object]) -> JsonObject:
    generation_mode = _parse_optional_text(arguments, "generation_mode") or "deterministic"
    if generation_mode not in _MODEL_GENERATION_MODES:
        raise MCPToolError("generation_mode must be deterministic or model_backed")
    route_mode = _parse_optional_text(arguments, "model_route_mode")
    if route_mode is not None and route_mode not in _MODEL_ROUTE_MODES:
        raise MCPToolError(
            "model_route_mode must be local_only, cloud_allowed, cloud_requires_approval, or model_disabled"
        )
    temperature = _parse_optional_float(arguments, "model_temperature")
    if temperature is None:
        temperature = 0.2
    if temperature < 0.0 or temperature > 2.0:
        raise MCPToolError("model_temperature must be between 0.0 and 2.0")
    return {
        "generation_mode": generation_mode,
        "model_route_mode": route_mode,
        "model_provider": _parse_optional_text(arguments, "model_provider"),
        "model": _parse_optional_text(arguments, "model"),
        "model_temperature": temperature,
        "allow_cloud_private": _parse_bool(arguments, key="allow_cloud_private", default=False),
    }


def _parse_review_status(
    arguments: Mapping[str, object],
    *,
    default: str,
) -> str:
    raw_status = arguments.get("status", default)
    if not isinstance(raw_status, str):
        raise MCPToolError("status must be a string")
    normalized = raw_status.strip()
    if normalized in _REVIEW_STATUS_ALIASES:
        normalized = _REVIEW_STATUS_ALIASES[normalized]
    if normalized not in _REVIEW_STATUS_CHOICES:
        allowed = ", ".join(_REVIEW_STATUS_CHOICES)
        raise MCPToolError(f"status must be one of: {allowed}")
    if normalized == "pending_review":
        return "stale"
    return normalized


def _parse_review_item_id(arguments: Mapping[str, object], *, required: bool) -> UUID | None:
    review_item_id = _parse_optional_uuid(arguments, "review_item_id")
    continuity_object_id = _parse_optional_uuid(arguments, "continuity_object_id")
    if review_item_id is not None and continuity_object_id is not None and review_item_id != continuity_object_id:
        raise MCPToolError("review_item_id and continuity_object_id must match when both are provided")
    resolved = review_item_id or continuity_object_id
    if required and resolved is None:
        raise MCPToolError("review_item_id or continuity_object_id is required and must be a UUID string")
    return resolved


def _resolve_review_apply_action(raw_action: str, *, allow_legacy: bool) -> str:
    normalized = raw_action.strip()
    if normalized in _REVIEW_APPLY_ACTION_ALIASES:
        normalized = _REVIEW_APPLY_ACTION_ALIASES[normalized]
    mapped = _REVIEW_APPLY_TO_CORRECTION_ACTION.get(normalized)
    if mapped is not None:
        return mapped
    if allow_legacy and normalized in CONTINUITY_CORRECTION_ACTIONS:
        return normalized
    # Advertise only the schema enum; legacy action names are still accepted
    # above when allow_legacy is set, but are not part of the public surface.
    raise MCPToolError(f"action must be one of: {', '.join(_REVIEW_APPLY_ACTION_CHOICES)}")


def _build_recall_query(arguments: Mapping[str, object], *, limit: int) -> ContinuityRecallQueryInput:
    return ContinuityRecallQueryInput(
        query=_parse_optional_text(arguments, "query"),
        thread_id=_parse_optional_uuid(arguments, "thread_id"),
        task_id=_parse_optional_uuid(arguments, "task_id"),
        project=_parse_optional_text(arguments, "project"),
        person=_parse_optional_text(arguments, "person"),
        since=_parse_optional_datetime(arguments, "since"),
        until=_parse_optional_datetime(arguments, "until"),
        limit=limit,
    )


def _canonicalize_json(value: object) -> object:
    value = json_safe(value)
    if isinstance(value, dict):
        return {
            key: _canonicalize_json(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [_canonicalize_json(item) for item in value]
    return value


def _recency_sort_key(item: Mapping[str, object]) -> tuple[str, str]:
    created_at = str(item.get("created_at", ""))
    item_id = str(item.get("id", ""))
    return created_at, item_id


def _extract_prefetch_single_title(section: object) -> str:
    if not isinstance(section, Mapping):
        return ""
    item = section.get("item")
    if not isinstance(item, Mapping):
        return ""
    title = item.get("title")
    if not isinstance(title, str):
        return ""
    return title.strip()


def _extract_prefetch_titles(section: object, *, limit: int) -> list[str]:
    if not isinstance(section, Mapping):
        return []
    items = section.get("items")
    if not isinstance(items, list):
        return []

    titles: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        title = item.get("title")
        if not isinstance(title, str):
            continue
        normalized = title.strip()
        if normalized == "":
            continue
        titles.append(normalized)
        if len(titles) >= limit:
            break
    return titles


def _render_prefetch_context_text(
    *,
    brief: Mapping[str, object],
    open_loops_limit: int,
    recent_changes_limit: int,
) -> str:
    lines: list[str] = ["## Alice Continuity Prefetch"]

    last_decision = _extract_prefetch_single_title(brief.get("last_decision"))
    if last_decision:
        lines.append(f"- Last decision: {last_decision}")

    next_action = _extract_prefetch_single_title(brief.get("next_action"))
    if next_action:
        lines.append(f"- Next action: {next_action}")

    open_loop_titles = _extract_prefetch_titles(brief.get("open_loops"), limit=open_loops_limit)
    if open_loop_titles:
        lines.append("- Open loops:")
        lines.extend([f"  - {title}" for title in open_loop_titles])

    recent_change_titles = _extract_prefetch_titles(brief.get("recent_changes"), limit=recent_changes_limit)
    if recent_change_titles:
        lines.append("- Recent changes:")
        lines.extend([f"  - {title}" for title in recent_change_titles])

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _handle_alice_capture_candidates(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return capture_continuity_candidates(
            store,
            user_id=context.user_id,
            request=ContinuityCaptureCandidatesInput(
                user_content=_parse_optional_text(arguments, "user_content") or "",
                assistant_content=_parse_optional_text(arguments, "assistant_content") or "",
                session_id=_parse_optional_text(arguments, "session_id"),
                source_kind=_parse_optional_text(arguments, "source_kind") or "sync_turn",
            ),
        )


def _handle_alice_commit_captures(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    raw_mode = _parse_optional_text(arguments, "mode") or "assist"
    mode = raw_mode.lower()
    if mode not in CONTINUITY_CAPTURE_COMMIT_MODES:
        allowed = ", ".join(CONTINUITY_CAPTURE_COMMIT_MODES)
        raise MCPToolError(f"mode must be one of: {allowed}")

    raw_candidates = arguments.get("candidates", [])
    if not isinstance(raw_candidates, list):
        raise MCPToolError("candidates must be a JSON array")
    for item in raw_candidates:
        if not isinstance(item, dict):
            raise MCPToolError("each candidate must be a JSON object")

    with _store_context(context) as store:
        return commit_continuity_captures(
            store,
            user_id=context.user_id,
            request=ContinuityCaptureCommitInput(
                mode=mode,  # type: ignore[arg-type]
                candidates=list(raw_candidates),
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
                source_kind=_parse_optional_text(arguments, "source_kind") or "sync_turn",
            ),
        )


def _handle_alice_memory_mutations_generate(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    raw_mode = _parse_optional_text(arguments, "mode") or "assist"
    mode = raw_mode.lower()
    if mode not in CONTINUITY_CAPTURE_COMMIT_MODES:
        allowed = ", ".join(CONTINUITY_CAPTURE_COMMIT_MODES)
        raise MCPToolError(f"mode must be one of: {allowed}")

    with _store_context(context) as store:
        return generate_memory_operation_candidates(
            store,
            user_id=context.user_id,
            request=MemoryOperationGenerateInput(
                user_content=_parse_optional_text(arguments, "user_content") or "",
                assistant_content=_parse_optional_text(arguments, "assistant_content") or "",
                mode=mode,  # type: ignore[arg-type]
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
                source_kind=_parse_optional_text(arguments, "source_kind") or "sync_turn",
                session_id=_parse_optional_text(arguments, "session_id"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                target_continuity_object_id=_parse_optional_uuid(arguments, "target_continuity_object_id"),
            ),
        )


def _handle_alice_memory_mutations_list_candidates(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(arguments, key="limit", default=20, minimum=1, maximum=100)
    with _store_context(context) as store:
        return list_memory_operation_candidates(
            store,
            user_id=context.user_id,
            request=MemoryOperationListInput(
                limit=limit,
                policy_action=_parse_optional_text(arguments, "policy_action"),  # type: ignore[arg-type]
                operation_type=_parse_optional_text(arguments, "operation_type"),  # type: ignore[arg-type]
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
            ),
        )


def _handle_alice_memory_mutations_commit(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    raw_candidate_ids = arguments.get("candidate_ids", [])
    if not isinstance(raw_candidate_ids, list):
        raise MCPToolError("candidate_ids must be a JSON array")
    candidate_ids: list[UUID] = []
    for item in raw_candidate_ids:
        if not isinstance(item, str):
            raise MCPToolError("candidate_ids must contain UUID strings")
        try:
            candidate_ids.append(UUID(item))
        except ValueError as exc:
            raise MCPToolError("candidate_ids must contain UUID strings") from exc

    with _store_context(context) as store:
        return commit_memory_operations(
            store,
            user_id=context.user_id,
            request=MemoryOperationCommitInput(
                candidate_ids=candidate_ids,
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
                include_review_required=_parse_bool(arguments, key="include_review_required", default=False),
            ),
        )


def _handle_alice_memory_mutations_list_operations(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(arguments, key="limit", default=20, minimum=1, maximum=100)
    with _store_context(context) as store:
        return list_memory_operations(
            store,
            user_id=context.user_id,
            request=MemoryOperationListInput(
                limit=limit,
                sync_fingerprint=_parse_optional_text(arguments, "sync_fingerprint"),
            ),
        )


def _compact_recall_result(item: Mapping[str, object], *, score: float, provenance_count: int) -> JsonObject:
    return {
        "id": str(item.get("id")),
        "type": item.get("memory_type"),
        "text": item.get("canonical_text") or item.get("summary") or item.get("title"),
        "score": round(score, 6),
        "domain": item.get("domain"),
        "status": item.get("status"),
        "confidence": item.get("confidence"),
        "provenance_count": provenance_count,
    }


def _handle_alice_recall(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    query = _parse_required_text(arguments, "query")
    limit = _parse_int(
        arguments,
        key="limit",
        default=_RECALL_DEFAULT_LIMIT,
        minimum=1,
        maximum=_RECALL_MAX_LIMIT,
    )
    debug = _parse_bool(arguments, key="debug", default=False)
    context_depth, budget_strategy = _parse_context_pack_tuning(arguments)
    if context_depth == CONTEXT_DEPTH_MINIMAL:
        # Same tier semantics as the context-pack compiler: the cheapest
        # useful call caps the result count and runs full-text search only.
        limit = min(limit, CONTEXT_DEPTH_MINIMAL_MAX_ITEMS)
    domains = list(_parse_string_list(arguments, "domains"))
    sensitivity_allowed = list(
        _parse_string_list(arguments, "sensitivity_allowed") or _DEFAULT_SENSITIVITY_ALLOWED
    )
    retrieval_filters = _retrieval_filter_kwargs(arguments)
    candidate_limit = max(limit * 2, limit)

    with _vnext_store_context(context) as store:
        # Reuse the hybrid retrieval stages (Postgres FTS + pgvector) that back
        # vNext context packs so recall and context packs rank identically.
        service = VNextRetrievalService(store)
        fts_rows, fts_source = service._memory_fts_rows(
            query=query,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=candidate_limit,
            **retrieval_filters,
        )
        if context_depth == CONTEXT_DEPTH_MINIMAL:
            # No query embedding, no entity resolution or graph hop; honest
            # tier status instead (mirrors compile_context_pack).
            vector_rows, vector_stage = [], STAGE_DISABLED_MINIMAL
            graph_rows, graph_stage, matched_entities = [], STAGE_DISABLED_MINIMAL, []
        else:
            vector_rows, vector_stage = service._memory_vector_rows(
                query=query,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=candidate_limit,
                **retrieval_filters,
            )
            graph_rows, graph_stage, matched_entities = service._memory_graph_rows(
                query=query,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=candidate_limit,
                **retrieval_filters,
            )
        ranked_lists: dict[str, list[JsonObject]] = {"fts": fts_rows}
        if vector_stage == VECTOR_STAGE_ENABLED:
            ranked_lists["vector"] = vector_rows
        if graph_stage == GRAPH_STAGE_ENABLED:
            ranked_lists["graph"] = graph_rows
        fused: list[tuple[JsonObject, float]] = []
        for item, score, _stage_ranks in reciprocal_rank_fusion(ranked_lists):
            if len(fused) >= limit:
                break
            fused.append((item, score))
        # The budget strategy reorders the fused selection exactly like the
        # context-pack packer would (facts_first/recent_first partitions);
        # it never changes what was retrieved or ranked.
        scores = {str(item.get("id")): score for item, score in fused}
        ordered_rows = _order_memories_for_strategy([item for item, _score in fused], budget_strategy)
        results: list[JsonObject] = []
        for item in ordered_rows:
            provenance_count = len(
                store.list_provenance_links(target_type="memory", target_id=str(item.get("id")))
            )
            results.append(
                _compact_recall_result(
                    item, score=scores[str(item.get("id"))], provenance_count=provenance_count
                )
            )

    payload: JsonObject = {
        "query": query,
        "results": results,
        "count": len(results),
    }
    if matched_entities:
        # WHO the results are about: entities the query resolved to via the
        # graph stage. Only present when the query matched entities.
        payload["entities"] = matched_entities
    if debug:
        payload["retrieval"] = {
            "fusion": {"algorithm": "reciprocal_rank_fusion", "k": RRF_K},
            "vector_stage": vector_stage,
            "context_depth": context_depth,
            "budget_strategy": budget_strategy,
            "stages": {
                "fts": {"source": fts_source, "candidate_count": len(fts_rows)},
                "vector": {"status": vector_stage, "candidate_count": len(vector_rows)},
                "graph": {
                    "status": graph_stage,
                    "matched_entities": matched_entities,
                    "candidate_count": len(graph_rows),
                },
            },
        }
        if retrieval_filters:
            payload["retrieval"]["filters"] = {
                key: list(value) for key, value in retrieval_filters.items()  # type: ignore[arg-type]
            }
    return payload


def _handle_alice_recall_debug(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RECALL_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
    )

    with _store_context(context) as store:
        return query_continuity_recall(
            store,
            user_id=context.user_id,
            request=ContinuityRecallQueryInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                limit=limit,
                debug=True,
            ),
        )


def _handle_alice_state_at(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return get_temporal_state_at(
            store,
            user_id=context.user_id,
            request=TemporalStateAtQueryInput(
                entity_id=_parse_required_uuid(arguments, "entity_id"),
                at=_parse_optional_datetime(arguments, "at"),
            ),
        )


def _handle_alice_resume(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    if _is_sqlite_backend(context):
        return _sqlite_resume(context, arguments)

    max_recent_changes = _parse_int(
        arguments,
        key="max_recent_changes",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops = _parse_int(
        arguments,
        key="max_open_loops",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        return compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=max_open_loops,
                include_non_promotable_facts=_parse_bool(
                    arguments,
                    key="include_non_promotable_facts",
                    default=False,
                ),
                debug=_parse_bool(arguments, key="debug", default=False),
            ),
        )


def _handle_alice_resume_debug(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="max_recent_changes",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops = _parse_int(
        arguments,
        key="max_open_loops",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        return compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=max_open_loops,
                include_non_promotable_facts=_parse_bool(
                    arguments,
                    key="include_non_promotable_facts",
                    default=False,
                ),
                debug=True,
            ),
        )


def _handle_alice_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return compile_continuity_brief(
            store,
            user_id=context.user_id,
            request=_parse_continuity_brief_request(arguments),
        )


def _handle_alice_task_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return compile_and_persist_task_brief(
            store,
            user_id=context.user_id,
            request=_parse_task_brief_request(arguments),
        )


def _handle_alice_task_brief_show(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return get_persisted_task_brief(
            store,
            task_brief_id=_parse_required_uuid(arguments, "task_brief_id"),
        )


def _handle_alice_task_brief_compare(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    compare_to_mode = arguments.get("compare_to_mode")
    if not isinstance(compare_to_mode, str) or compare_to_mode.strip() == "":
        raise MCPToolError("compare_to_mode is required and must be a string")

    primary_request = _parse_task_brief_request(arguments)
    secondary_arguments = dict(arguments)
    secondary_arguments["mode"] = compare_to_mode
    if "compare_model_pack_strategy" in arguments:
        secondary_arguments["model_pack_strategy"] = arguments["compare_model_pack_strategy"]
    if "compare_token_budget" in arguments:
        secondary_arguments["token_budget"] = arguments["compare_token_budget"]

    with _store_context(context) as store:
        return compare_task_briefs(
            store,
            user_id=context.user_id,
            primary_request=primary_request,
            secondary_request=_parse_task_brief_request(secondary_arguments),
        )


def _handle_alice_retrieval_trace(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return get_retrieval_trace(
            store,
            user_id=context.user_id,
            retrieval_run_id=_parse_required_uuid(arguments, "retrieval_run_id"),
        )


def _handle_alice_prefetch_context(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="max_recent_changes",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops = _parse_int(
        arguments,
        key="max_open_loops",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        resumption_payload = compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=max_open_loops,
                include_non_promotable_facts=_parse_bool(
                    arguments,
                    key="include_non_promotable_facts",
                    default=False,
                ),
            ),
        )

    brief = resumption_payload["brief"]
    return {
        "prefetch_context": {
            "assembly_version": _PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0,
            "text": _render_prefetch_context_text(
                brief=brief,
                open_loops_limit=max_open_loops,
                recent_changes_limit=max_recent_changes,
            ),
            "scope": brief["scope"],
            "last_decision": brief["last_decision"],
            "next_action": brief["next_action"],
            "open_loops": brief["open_loops"],
            "recent_changes": brief["recent_changes"],
            "sources": brief["sources"],
        }
    }


def _handle_alice_open_loops(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    action = (_parse_optional_text(arguments, "action") or "list").lower()
    if action not in _OPEN_LOOP_TOOL_ACTIONS:
        allowed = ", ".join(_OPEN_LOOP_TOOL_ACTIONS)
        raise MCPToolError(f"action must be one of: {allowed}")
    if action == "list":
        return _handle_alice_vnext_open_loops(context, arguments)

    loop_id = _parse_required_text(arguments, "loop_id")
    with _vnext_store_context(context) as store:
        loop = VNextProjectService(store).review_open_loop(
            loop_id=loop_id,
            action=action,
            title=_parse_optional_text(arguments, "title"),
            description=_parse_optional_text(arguments, "description"),
            due_at=_parse_optional_text(arguments, "due_at"),
            priority=_parse_optional_text(arguments, "priority"),
            resolution_note=_parse_optional_text(arguments, "resolution_note"),
        )
    return {"action": action, "open_loop": loop}


# --- SQLite on-ramp implementations -----------------------------------------
#
# The SQLite backend has no legacy continuity tables, so the four core tools
# that are legacy-backed on Postgres (alice_recent_decisions, alice_resume,
# alice_memory_review, alice_memory_correct) get vNext-native implementations
# built only on the SQLiteVNextStore surface. Postgres behavior is unchanged.

_SQLITE_REVIEWABLE_STATUSES = frozenset({"active", "candidate"})
_SQLITE_NEXT_ACTION_MEMORY_TYPES = frozenset({"open_loop", "commitment"})
_SQLITE_OPEN_LOOP_ACTIVE_STATUSES = frozenset({"open", "waiting"})


def _utc_now_iso_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _row_datetime(row: Mapping[str, object], key: str) -> datetime | None:
    value = row.get(key)
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _row_in_window(
    row: Mapping[str, object],
    *,
    key: str,
    since: datetime | None,
    until: datetime | None,
) -> bool:
    if since is None and until is None:
        return True
    moment = _row_datetime(row, key)
    if moment is None:
        return False
    if since is not None:
        bounded_since = since if since.tzinfo is not None else since.replace(tzinfo=UTC)
        if moment < bounded_since:
            return False
    if until is not None:
        bounded_until = until if until.tzinfo is not None else until.replace(tzinfo=UTC)
        if moment > bounded_until:
            return False
    return True


def _memory_matches_query(row: Mapping[str, object], query: str | None) -> bool:
    if query is None:
        return True
    needle = query.casefold()
    for key in ("title", "canonical_text", "summary"):
        value = row.get(key)
        if isinstance(value, str) and needle in value.casefold():
            return True
    return False


def _memory_matches_project(row: Mapping[str, object], project: str | None) -> bool:
    if project is None:
        return True
    needle = project.casefold()
    metadata = row.get("metadata_json")
    if isinstance(metadata, Mapping):
        project_id = metadata.get("project_id")
        if isinstance(project_id, str) and project_id.casefold() == needle:
            return True
    domain = row.get("domain")
    return isinstance(domain, str) and domain.casefold() == needle


def _created_at_sort_key(row: Mapping[str, object]) -> tuple[str, str]:
    return str(row.get("created_at") or ""), str(row.get("id") or "")


def _compact_vnext_memory(row: Mapping[str, object], *, provenance_count: int) -> JsonObject:
    return {
        "id": str(row.get("id")),
        "title": row.get("title"),
        "canonical_text": row.get("canonical_text"),
        "created_at": row.get("created_at"),
        "domain": row.get("domain"),
        "status": row.get("status"),
        "memory_type": row.get("memory_type"),
        "confidence": row.get("confidence"),
        "provenance_count": provenance_count,
    }


def _compact_vnext_open_loop(row: Mapping[str, object]) -> JsonObject:
    return {
        "kind": "open_loop",
        "id": str(row.get("id")),
        "title": row.get("title"),
        "status": row.get("status"),
        "priority": row.get("priority"),
        "due_at": row.get("due_at"),
        "opened_at": row.get("opened_at"),
        "domain": row.get("domain"),
        "project_id": row.get("project_id"),
    }


def _compact_vnext_event(row: Mapping[str, object]) -> JsonObject:
    return {
        "id": str(row.get("id")),
        "event_type": row.get("event_type"),
        "actor_type": row.get("actor_type"),
        "target_type": row.get("target_type"),
        "target_id": row.get("target_id"),
        "occurred_at": row.get("occurred_at"),
    }


def _provenance_count(store: SQLiteVNextStore, memory_id: object) -> int:
    return len(store.list_provenance_links(target_type="memory", target_id=str(memory_id)))


def _sqlite_recent_decisions(
    context: MCPRuntimeContext,
    *,
    arguments: Mapping[str, object],
    limit: int,
) -> JsonObject:
    query = _parse_optional_text(arguments, "query")
    project = _parse_optional_text(arguments, "project")
    since = _parse_optional_datetime(arguments, "since")
    until = _parse_optional_datetime(arguments, "until")
    filters_ignored = [
        key for key in ("thread_id", "task_id", "person") if arguments.get(key) not in (None, "")
    ]

    with _vnext_store_context(context) as store:
        matched = [
            row
            for row in store.list_memories()
            if row.get("memory_type") == "decision"
            and str(row.get("status")) in _SQLITE_REVIEWABLE_STATUSES
            and _memory_matches_query(row, query)
            and _memory_matches_project(row, project)
            and _row_in_window(row, key="created_at", since=since, until=until)
        ]
        matched.sort(key=_created_at_sort_key, reverse=True)
        decisions = [
            _compact_vnext_memory(row, provenance_count=_provenance_count(store, row.get("id")))
            for row in matched[:limit]
        ]

    payload: JsonObject = {
        "decisions": decisions,
        "count": len(decisions),
        "mode": "vnext",
    }
    if filters_ignored:
        payload["filters_ignored"] = filters_ignored
    return payload


def _sqlite_resume(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="max_recent_changes",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    max_open_loops = _parse_int(
        arguments,
        key="max_open_loops",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )
    query = _parse_optional_text(arguments, "query")
    project = _parse_optional_text(arguments, "project")
    since = _parse_optional_datetime(arguments, "since")
    until = _parse_optional_datetime(arguments, "until")
    filters_ignored = [
        key
        for key in ("thread_id", "task_id", "person", "include_non_promotable_facts", "debug")
        if arguments.get(key) not in (None, "", False)
    ]

    def _memory_matches(row: Mapping[str, object]) -> bool:
        return (
            str(row.get("status")) in _SQLITE_REVIEWABLE_STATUSES
            and _memory_matches_query(row, query)
            and _memory_matches_project(row, project)
            and _row_in_window(row, key="created_at", since=since, until=until)
        )

    with _vnext_store_context(context) as store:
        memories = [row for row in store.list_memories() if _memory_matches(row)]

        decisions = sorted(
            (row for row in memories if row.get("memory_type") == "decision"),
            key=_created_at_sort_key,
            reverse=True,
        )
        last_decision: JsonObject | None = None
        if decisions:
            last_decision = {
                "kind": "memory",
                **_compact_vnext_memory(
                    decisions[0], provenance_count=_provenance_count(store, decisions[0].get("id"))
                ),
            }

        loop_candidate_limit = max(max_open_loops, 1) * 5
        loop_rows = [
            row
            for row in store.list_open_loops(status=None, limit=loop_candidate_limit)
            if str(row.get("status")) in _SQLITE_OPEN_LOOP_ACTIVE_STATUSES
            and _row_in_window(row, key="opened_at", since=since, until=until)
        ]
        open_loops = [_compact_vnext_open_loop(row) for row in loop_rows[:max_open_loops]]

        next_action: JsonObject | None = open_loops[0] if open_loops else None
        if next_action is None:
            todo_memories = sorted(
                (
                    row
                    for row in memories
                    if row.get("memory_type") in _SQLITE_NEXT_ACTION_MEMORY_TYPES
                ),
                key=_created_at_sort_key,
                reverse=True,
            )
            if todo_memories:
                next_action = {
                    "kind": "memory",
                    **_compact_vnext_memory(
                        todo_memories[0],
                        provenance_count=_provenance_count(store, todo_memories[0].get("id")),
                    ),
                }

        recent_changes: list[JsonObject] = []
        if max_recent_changes > 0:
            recent_changes = [
                _compact_vnext_event(row) for row in store.list_events(limit=max_recent_changes)
            ]

    return {
        "brief": {
            "last_decision": last_decision,
            "next_action": next_action,
            "open_loops": open_loops,
            "recent_changes": recent_changes,
            "generated_at": _utc_now_iso_text(),
            "mode": "vnext",
            "filters_ignored": filters_ignored,
        }
    }


def _sqlite_memory_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    review_item_id = _parse_review_item_id(arguments, required=False)
    if review_item_id is not None:
        memory_id = str(review_item_id)
        with _vnext_store_context(context) as store:
            memory = store.get_memory(memory_id)
            if memory is None:
                raise MCPToolError(f"memory {memory_id} was not found")
            return {
                "mode": "vnext_detail",
                "review": {
                    "memory": memory,
                    "revisions": store.list_revisions(memory_id),
                    "provenance_links": store.list_provenance_links(
                        target_type="memory", target_id=memory_id
                    ),
                },
            }

    raw_status = arguments.get("status", "correction_ready")
    if not isinstance(raw_status, str):
        raise MCPToolError("status must be a string")
    normalized_status = raw_status.strip()
    normalized_status = _REVIEW_STATUS_ALIASES.get(normalized_status, normalized_status)
    if normalized_status not in _REVIEW_STATUS_CHOICES:
        allowed = ", ".join(_REVIEW_STATUS_CHOICES)
        raise MCPToolError(f"status must be one of: {allowed}")
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )

    if normalized_status in {"pending_review", "correction_ready"}:
        vnext_status: str | None = "candidate"
    elif normalized_status == "active":
        vnext_status = "active"
    elif normalized_status == "all":
        vnext_status = None
    else:
        return {
            "items": [],
            "count": 0,
            "mode": "vnext_candidates",
            "note": (
                f"status '{normalized_status}' has no SQLite on-ramp equivalent; "
                "use pending_review, correction_ready, active, or all"
            ),
        }

    with _vnext_store_context(context) as store:
        rows = store.list_memories(status=vnext_status)[:limit]
        items = [
            _compact_vnext_memory(row, provenance_count=_provenance_count(store, row.get("id")))
            for row in rows
        ]
    return {"items": items, "count": len(items), "mode": "vnext_candidates"}


def _canonical_text_from_body(body: Mapping[str, object]) -> str:
    text = body.get("text")
    if isinstance(text, str) and text.strip() != "":
        return text.strip()
    return _canonical_json_dumps(body)


def _canonical_json_dumps(value: object) -> str:
    return json.dumps(json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sqlite_review_revision(
    store: SQLiteVNextStore,
    *,
    previous: Mapping[str, object],
    updated: Mapping[str, object],
    revision_type: str,
    action_label: str,
    reason: str | None,
    metadata: JsonObject | None = None,
) -> None:
    store.append_revision(
        {
            "memory_id": str(updated["id"]),
            "memory_key": str(updated["memory_key"]),
            "previous_value": previous.get("value"),
            "new_value": updated.get("value"),
            "source_event_ids": updated.get("source_event_ids"),
            "revision_type": revision_type,
            "action": f"memory_correct_{action_label}",
            "text_before": previous.get("canonical_text"),
            "text_after": str(updated.get("canonical_text") or ""),
            "reason": reason or f"alice_memory_correct action: {action_label}",
            "actor_type": "user",
            "metadata_json": {"action": action_label, **(metadata or {})},
        },
        actor_type="user",
    )


def _link_accepted_memory_entities(store: object, memory: Mapping[str, object]) -> None:
    """Entity-link a memory at review-acceptance time (sqlite review path).

    Mirrors VNextMemoryCommitService._link_memory_entities: failures never
    fail the review action; stores without the entity substrate skip.
    """
    from alicebot_api.vnext_entities import (
        EntityLinkingService,
        derive_person_name_from_title,
        store_supports_entity_linking,
    )

    if not store_supports_entity_linking(store):
        return
    observed_at = (
        memory.get("last_reviewed_at") or memory.get("updated_at") or memory.get("created_at")
    )
    try:
        linker = EntityLinkingService(store, actor_type="user", actor_id=None, trace_id=None)
        text = str(memory.get("canonical_text") or "")
        if text.strip():
            linker.link_entities_for_memory(
                memory_id=str(memory["id"]), text=text, observed_at=observed_at
            )
        if str(memory.get("memory_type") or "") == "person":
            person_name = derive_person_name_from_title(str(memory.get("title") or ""))
            if person_name is not None:
                linker.link_memory_to_person(
                    memory_id=str(memory["id"]), person_name=person_name, observed_at=observed_at
                )
    except Exception:
        try:
            store.append_event(
                {
                    "event_type": "entity.extraction_failed",
                    "actor_type": "user",
                    "payload": {"memory_id": str(memory.get("id")), "stage": "mcp_review_approve"},
                }
            )
        except Exception:
            pass


def _sqlite_memory_correct(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    requested_action = _parse_required_text(arguments, "action")
    resolved_action = _resolve_review_apply_action(requested_action, allow_legacy=True)
    if resolved_action not in {"confirm", "edit", "delete", "supersede"}:
        raise MCPToolError(
            f"action '{requested_action}' is not supported on the SQLite on-ramp; "
            "use approve, edit-and-approve, reject, or supersede-existing"
        )
    memory_id = str(cast(UUID, _parse_review_item_id(arguments, required=True)))
    reason = _parse_optional_text(arguments, "reason")
    now_iso = _utc_now_iso_text()

    replacement_object: JsonObject | None = None
    with _vnext_store_context(context) as store:
        memory = store.get_memory(memory_id)
        if memory is None:
            raise MCPToolError(f"memory {memory_id} was not found")
        event_payload: JsonObject = {
            "requested_action": requested_action,
            "resolved_action": resolved_action,
            "reason": reason,
        }

        if resolved_action == "confirm":
            updated = store.update_memory(
                memory_id=memory_id,
                patch={"status": "active", "last_reviewed_at": now_iso},
                actor_type="user",
            )
            _sqlite_review_revision(
                store,
                previous=memory,
                updated=updated,
                revision_type="promoted",
                action_label="approve",
                reason=reason,
            )
            # Acceptance is the promotion into trusted memory, so it is also
            # the entity-linking moment; proposal-time candidates never link.
            _link_accepted_memory_entities(store, updated)
        elif resolved_action == "delete":
            updated = store.update_memory(
                memory_id=memory_id,
                patch={"status": "rejected", "last_reviewed_at": now_iso},
                actor_type="user",
            )
            _sqlite_review_revision(
                store,
                previous=memory,
                updated=updated,
                revision_type="rejected",
                action_label="reject",
                reason=reason,
            )
        elif resolved_action == "edit":
            title = _parse_optional_text(arguments, "title")
            body = _parse_optional_json_object(arguments, "body")
            confidence = _parse_optional_float(arguments, "confidence")
            if title is None and body is None and confidence is None:
                raise MCPToolError(
                    "edit-and-approve requires at least one of title, body, or confidence"
                )
            patch: JsonObject = {"status": "active", "last_reviewed_at": now_iso}
            if title is not None:
                patch["title"] = title
            if body is not None:
                patch["value"] = body
                patch["canonical_text"] = _canonical_text_from_body(body)
            if confidence is not None:
                patch["confidence"] = confidence
            updated = store.update_memory(memory_id=memory_id, patch=patch, actor_type="user")
            _sqlite_review_revision(
                store,
                previous=memory,
                updated=updated,
                revision_type="edited",
                action_label="edit-and-approve",
                reason=reason,
            )
        else:  # supersede
            replacement_title = _parse_optional_text(arguments, "replacement_title")
            replacement_body = _parse_optional_json_object(arguments, "replacement_body")
            replacement_provenance = _parse_optional_json_object(arguments, "replacement_provenance")
            replacement_confidence = _parse_optional_float(arguments, "replacement_confidence")
            if replacement_title is None and replacement_body is None:
                raise MCPToolError(
                    "supersede-existing requires replacement_title or replacement_body"
                )
            canonical_text = (
                _canonical_text_from_body(replacement_body)
                if replacement_body is not None
                else cast(str, replacement_title)
            )
            # The supersession pointer is a first-class column
            # (memories.supersedes / memories.superseded_by, migration
            # 20260704_0077); the metadata_json copies below stay for
            # backward compatibility.
            replacement_metadata: JsonObject = {
                "supersedes": memory_id,
                "correction_reason": reason,
            }
            if replacement_provenance is not None:
                replacement_metadata["replacement_provenance"] = replacement_provenance
            replacement_object = store.create_memory(
                {
                    "memory_key": f"vnext.correction.supersede.{uuid4().hex[:16]}",
                    "value": replacement_body
                    if replacement_body is not None
                    else {"text": canonical_text},
                    "status": "active",
                    "supersedes": memory_id,
                    "memory_type": memory.get("memory_type") or "semantic",
                    "confidence": replacement_confidence,
                    "title": replacement_title or canonical_text[:120],
                    "canonical_text": canonical_text,
                    "summary": canonical_text[:280],
                    "domain": memory.get("domain") or "unknown",
                    "sensitivity": memory.get("sensitivity") or "unknown",
                    "last_reviewed_at": now_iso,
                    "metadata_json": replacement_metadata,
                },
                actor_type="user",
            )
            replacement_id = str(replacement_object["id"])
            if replacement_provenance is not None:
                provenance_source_id = replacement_provenance.get("source_id")
                if (
                    isinstance(provenance_source_id, str)
                    and store.get_source(provenance_source_id) is not None
                ):
                    store.create_provenance_link(
                        {
                            "target_type": "memory",
                            "target_id": replacement_id,
                            "source_id": provenance_source_id,
                            "quote": canonical_text,
                            "evidence_role": "supports",
                            "confidence": replacement_confidence
                            if replacement_confidence is not None
                            else 0.5,
                        },
                        actor_type="user",
                    )
            existing_metadata = (
                dict(cast(Mapping[str, object], memory.get("metadata_json")))
                if isinstance(memory.get("metadata_json"), Mapping)
                else {}
            )
            updated = store.update_memory(
                memory_id=memory_id,
                patch={
                    "status": "superseded",
                    "superseded_by": replacement_id,
                    "last_reviewed_at": now_iso,
                    "metadata_json": {**existing_metadata, "superseded_by": replacement_id},
                },
                actor_type="user",
            )
            _sqlite_review_revision(
                store,
                previous=memory,
                updated=updated,
                revision_type="superseded",
                action_label="supersede-existing",
                reason=reason,
                metadata={"superseded_by": replacement_id},
            )
            store.append_revision(
                {
                    "memory_id": replacement_id,
                    "memory_key": str(replacement_object["memory_key"]),
                    "new_value": replacement_object.get("value"),
                    "source_event_ids": replacement_object.get("source_event_ids"),
                    "revision_type": "created",
                    "action": "memory_correct_supersede-existing",
                    "text_after": canonical_text,
                    "reason": reason or "alice_memory_correct action: supersede-existing",
                    "actor_type": "user",
                    "metadata_json": {"action": "supersede-existing", "supersedes": memory_id},
                },
                actor_type="user",
            )
            event_payload["replacement_memory_id"] = replacement_id

        append_event(
            store,
            event_type="memory.reviewed",
            actor_type="user",
            target_type="memory",
            target_id=memory_id,
            payload=event_payload,
        )

    return {
        "review_action": {
            "requested_action": requested_action,
            "resolved_action": resolved_action,
            "memory_id": memory_id,
        },
        "memory": updated,
        "replacement_object": replacement_object,
        "mode": "vnext",
    }


def _recent_decisions_payload(
    context: MCPRuntimeContext,
    *,
    arguments: Mapping[str, object],
    limit: int,
) -> JsonObject:
    with _store_context(context) as store:
        recall_payload = query_continuity_recall(
            store,
            user_id=context.user_id,
            request=_build_recall_query(arguments, limit=MAX_CONTINUITY_RECALL_LIMIT),
            apply_limit=False,
        )

    all_decisions = [
        item
        for item in recall_payload["items"]
        if item["object_type"] == "Decision"
    ]
    ordered = sorted(all_decisions, key=_recency_sort_key, reverse=True)
    items = ordered[:limit]
    return {
        "items": items,
        "summary": {
            "scope": recall_payload["summary"]["filters"],
            "limit": limit,
            "returned_count": len(items),
            "total_count": len(all_decisions),
            "order": ["created_at_desc", "id_desc"],
        },
    }


def _handle_alice_recent_decisions(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
    )
    _mcp_agent_policy_preflight(
        context,
        arguments,
        action="recent_decisions.lookup",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=_parse_string_list(arguments, "sensitivity_allowed")
        or ("public", "internal", "private", "unknown"),
        project_scope=_parse_string_list(arguments, "project_scope"),
    )
    if _is_sqlite_backend(context):
        return _sqlite_recent_decisions(context, arguments=arguments, limit=limit)
    return _recent_decisions_payload(context, arguments=arguments, limit=limit)


def _handle_alice_recent_changes(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    _mcp_agent_policy_preflight(
        context,
        arguments,
        action="recent_changes.lookup",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=_parse_string_list(arguments, "sensitivity_allowed")
        or ("public", "internal", "private", "unknown"),
        project_scope=_parse_string_list(arguments, "project_scope"),
    )

    with _store_context(context) as store:
        resumption_payload = compile_continuity_resumption_brief(
            store,
            user_id=context.user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                max_recent_changes=max_recent_changes,
                max_open_loops=0,
            ),
        )

    brief = resumption_payload["brief"]
    return {
        "recent_changes": brief["recent_changes"],
        "scope": brief["scope"],
        "sources": brief["sources"],
        "order": list(CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER),
    }


def _handle_alice_timeline(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_TEMPORAL_TIMELINE_LIMIT,
        minimum=1,
        maximum=MAX_TEMPORAL_TIMELINE_LIMIT,
    )
    with _store_context(context) as store:
        return get_temporal_timeline(
            store,
            user_id=context.user_id,
            request=TemporalTimelineQueryInput(
                entity_id=_parse_required_uuid(arguments, "entity_id"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                limit=limit,
            ),
        )


def _review_queue_payload(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
    *,
    default_status: str,
) -> JsonObject:
    continuity_object_id = _parse_review_item_id(arguments, required=False)
    if continuity_object_id is not None:
        with _store_context(context) as store:
            payload = get_continuity_review_detail(
                store,
                user_id=context.user_id,
                continuity_object_id=continuity_object_id,
            )
        return {
            "mode": "detail",
            "review": payload["review"],
        }

    status = _parse_review_status(arguments, default=default_status)
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )

    with _store_context(context) as store:
        payload = list_continuity_review_queue(
            store,
            user_id=context.user_id,
            request=ContinuityReviewQueueQueryInput(
                status=status,
                limit=limit,
            ),
        )
    return {
        "mode": "queue",
        "items": payload["items"],
        "summary": {
            **payload["summary"],
            "order": list(CONTINUITY_REVIEW_QUEUE_ORDER),
        },
    }


def _handle_alice_review_queue(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    return _review_queue_payload(
        context,
        arguments,
        default_status="pending_review",
    )


def _handle_alice_memory_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    if _is_sqlite_backend(context):
        return _sqlite_memory_review(context, arguments)
    return _review_queue_payload(
        context,
        arguments,
        default_status="correction_ready",
    )


def _review_apply_payload(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
    *,
    allow_legacy_actions: bool,
    include_action_resolution: bool,
) -> JsonObject:
    requested_action = _parse_required_text(arguments, "action")
    resolved_action = _resolve_review_apply_action(
        requested_action,
        allow_legacy=allow_legacy_actions,
    )
    continuity_object_id = cast(UUID, _parse_review_item_id(arguments, required=True))

    with _store_context(context) as store:
        payload = apply_continuity_correction(
            store,
            user_id=context.user_id,
            continuity_object_id=continuity_object_id,
            request=ContinuityCorrectionInput(
                action=resolved_action,
                reason=_parse_optional_text(arguments, "reason"),
                title=_parse_optional_text(arguments, "title"),
                body=_parse_optional_json_object(arguments, "body"),
                provenance=_parse_optional_json_object(arguments, "provenance"),
                confidence=_parse_optional_float(arguments, "confidence"),
                replacement_title=_parse_optional_text(arguments, "replacement_title"),
                replacement_body=_parse_optional_json_object(arguments, "replacement_body"),
                replacement_provenance=_parse_optional_json_object(arguments, "replacement_provenance"),
                replacement_confidence=_parse_optional_float(arguments, "replacement_confidence"),
            ),
        )

    if not include_action_resolution:
        return payload
    return {
        "review_action": {
            "requested_action": requested_action,
            "resolved_action": resolved_action,
        },
        **payload,
    }


def _handle_alice_review_apply(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    return _review_apply_payload(
        context,
        arguments,
        allow_legacy_actions=True,
        include_action_resolution=True,
    )


def _handle_alice_memory_correct(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    if _is_sqlite_backend(context):
        return _sqlite_memory_correct(context, arguments)
    return _review_apply_payload(
        context,
        arguments,
        allow_legacy_actions=True,
        include_action_resolution=False,
    )


def _handle_alice_contradictions_detect(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )
    with _store_context(context) as store:
        return sync_contradictions(
            store,
            user_id=context.user_id,
            request=ContradictionSyncInput(
                continuity_object_id=_parse_optional_uuid(arguments, "continuity_object_id"),
                limit=limit,
            ),
        )


def _handle_alice_contradictions_list(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    contradiction_case_id = _parse_optional_uuid(arguments, "contradiction_case_id")
    if contradiction_case_id is not None:
        with _store_context(context) as store:
            return get_contradiction_case(
                store,
                user_id=context.user_id,
                contradiction_case_id=contradiction_case_id,
            )
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )
    raw_status = _parse_optional_text(arguments, "status") or "open"
    with _store_context(context) as store:
        return list_contradiction_cases(
            store,
            user_id=context.user_id,
            request=ContradictionCaseListQueryInput(
                status=cast("ContradictionStatus", raw_status),
                limit=limit,
                continuity_object_id=_parse_optional_uuid(arguments, "continuity_object_id"),
            ),
        )


def _handle_alice_contradictions_resolve(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    contradiction_case_id = _parse_required_uuid(arguments, "contradiction_case_id")
    action = _parse_required_text(arguments, "action")
    with _store_context(context) as store:
        return resolve_contradiction_case(
            store,
            user_id=context.user_id,
            contradiction_case_id=contradiction_case_id,
            request=ContradictionResolveInput(
                action=cast("ContradictionResolutionAction", action),
                note=_parse_optional_text(arguments, "note"),
            ),
        )


def _handle_alice_trust_signals(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_REVIEW_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_REVIEW_LIMIT,
    )
    with _store_context(context) as store:
        return list_trust_signals(
            store,
            user_id=context.user_id,
            request=TrustSignalListQueryInput(
                limit=limit,
                continuity_object_id=_parse_optional_uuid(arguments, "continuity_object_id"),
                signal_state=cast("TrustSignalState", _parse_optional_text(arguments, "signal_state") or "active"),
                signal_type=cast("TrustSignalType | None", _parse_optional_text(arguments, "signal_type")),
            ),
        )


def _handle_alice_explain(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    memory_id = _parse_optional_text(arguments, "memory_id")
    continuity_object_id = _parse_optional_uuid(arguments, "continuity_object_id")
    entity_id = _parse_optional_uuid(arguments, "entity_id")
    provided = [value for value in (memory_id, continuity_object_id, entity_id) if value is not None]
    if len(provided) > 1:
        raise MCPToolError("alice_explain accepts exactly one of memory_id, continuity_object_id, or entity_id")
    if memory_id is not None:
        return _handle_alice_vnext_memory_audit(context, arguments)
    if _is_sqlite_backend(context):
        raise MCPToolError(
            "alice_explain with entity_id or continuity_object_id is available on the Postgres "
            "backend; pass memory_id on the SQLite on-ramp"
        )
    if entity_id is not None:
        with _store_context(context) as store:
            return get_temporal_explain(
                store,
                user_id=context.user_id,
                request=TemporalExplainQueryInput(
                    entity_id=entity_id,
                    at=_parse_optional_datetime(arguments, "at"),
                ),
            )
    if continuity_object_id is None:
        raise MCPToolError("alice_explain requires memory_id, continuity_object_id, or entity_id")

    include_raw_content = _parse_bool(arguments, key="include_raw_content", default=False)
    if include_raw_content and get_settings().app_env not in {"development", "test"}:
        raise MCPToolError("include_raw_content is restricted to development/test environments")

    with _store_context(context) as store:
        return build_continuity_explain(
            store,
            user_id=context.user_id,
            continuity_object_id=continuity_object_id,
            include_raw_content=include_raw_content,
        )


def _handle_alice_artifact_inspect(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    include_raw_content = _parse_bool(arguments, key="include_raw_content", default=False)
    if include_raw_content and get_settings().app_env not in {"development", "test"}:
        raise MCPToolError("include_raw_content is restricted to development/test environments")

    with _store_context(context) as store:
        return get_continuity_artifact_detail(
            store,
            user_id=context.user_id,
            artifact_id=_parse_required_uuid(arguments, "artifact_id"),
            include_raw_content=include_raw_content,
        )


_COMPACT_MEMORY_FIELDS = (
    "id",
    "memory_type",
    "title",
    "canonical_text",
    "summary",
    "status",
    "confidence",
    "domain",
    "sensitivity",
    "last_seen_at",
    # Attached by the compiler when last_confirmed_at is older than the
    # staleness threshold; agents should weigh flagged memories accordingly.
    "staleness",
)
_COMPACT_OPEN_LOOP_FIELDS = (
    "id",
    "title",
    "description",
    "status",
    "priority",
    "due_at",
    "domain",
    "project_id",
)
_COMPACT_SOURCE_FIELDS = ("id", "source_type", "title", "captured_at", "domain", "sensitivity")


def _compact_fields(item: object, fields: tuple[str, ...]) -> JsonObject:
    if not isinstance(item, Mapping):
        return {}
    return {key: item[key] for key in fields if item.get(key) is not None}


def _compact_items(items: object, fields: tuple[str, ...]) -> list[JsonObject]:
    if not isinstance(items, list):
        return []
    return [_compact_fields(item, fields) for item in items]


def _handle_alice_context_pack(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    debug = _parse_bool(arguments, key="debug", default=False)
    pack = _vnext_context_pack_payload(context, arguments)
    interpretation = pack.get("query_interpretation")
    if not isinstance(interpretation, Mapping):
        interpretation = {}
    payload: JsonObject = {
        "context_pack_id": pack.get("context_pack_id"),
        "query": interpretation.get("query"),
        "query_type": interpretation.get("query_type"),
        "memories": _compact_items(pack.get("relevant_memories"), _COMPACT_MEMORY_FIELDS),
        "open_loops": _compact_items(pack.get("open_loops"), _COMPACT_OPEN_LOOP_FIELDS),
        "sources": _compact_items(pack.get("sources"), _COMPACT_SOURCE_FIELDS),
        "supporting_evidence": pack.get("supporting_evidence", []),
        "missing_information": pack.get("missing_information", []),
        "warnings": pack.get("warnings", []),
        "trace_id": pack.get("trace_id"),
    }
    token_report = _context_pack_token_report(pack)
    if token_report:
        payload["token_report"] = token_report
    # Sections that cannot be reconstructed from the memory rows themselves;
    # typed groupings (procedures/decisions/beliefs) are omitted here because
    # every compact memory row already carries memory_type.
    entities = pack.get("entities")
    if isinstance(entities, list) and entities:
        # Already compact ({id, name, entity_type, mention_count}): the
        # entities the query resolved to, i.e. who the pack is about.
        payload["entities"] = entities
    contradictions = pack.get("contradicting_evidence")
    if isinstance(contradictions, list) and contradictions:
        payload["contradicting_evidence"] = contradictions
    recent_changes = pack.get("recent_changes")
    if isinstance(recent_changes, list) and recent_changes:
        payload["recent_changes"] = recent_changes
    if debug:
        payload["query_interpretation"] = dict(interpretation)
        payload["trace"] = pack.get("trace")
        for section in ("procedures", "decisions", "relevant_beliefs", "current_known_state"):
            payload[section] = pack.get(section, [])
    return payload


_TOKEN_REPORT_FIELDS = ("token_budget", "token_estimate", "truncated", "dropped_item_count")


def _context_pack_token_report(pack: Mapping[str, object]) -> JsonObject:
    """Extract the compiler's token-budget report from a context pack.

    Accepts either a nested ``token_report`` object or the report fields at
    the top level of the pack, and returns ``{}`` when the compiler did not
    report a budget.
    """
    nested = pack.get("token_report")
    if not isinstance(nested, Mapping):
        nested = pack.get("budget")
    if isinstance(nested, Mapping):
        return {key: nested[key] for key in _TOKEN_REPORT_FIELDS if key in nested}
    return {key: pack[key] for key in _TOKEN_REPORT_FIELDS if key in pack}


def _vnext_context_pack_payload(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_items = _parse_int(
        arguments,
        key="max_items",
        default=8,
        minimum=1,
        maximum=50,
    )
    max_tokens = _parse_int(
        arguments,
        key="max_tokens",
        default=8000,
        minimum=500,
        maximum=50_000,
    )
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    identity = _agent_identity_from_arguments(context, arguments)

    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="context_pack.request",
            domains=_parse_string_list(arguments, "domains"),
            sensitivity_allowed=sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            request_kwargs: dict[str, object] = {}
            memory_types = _parse_memory_types(arguments)
            if memory_types:
                # Forwarded only when requested so the retrieval request
                # dataclass stays the source of truth for the default ().
                request_kwargs["memory_types"] = memory_types
            created_by_agents = _parse_string_list(arguments, "created_by_agents")
            if created_by_agents:
                request_kwargs["created_by_agent_ids"] = created_by_agents
            context_depth, budget_strategy = _parse_context_pack_tuning(arguments)
            payload = VNextRetrievalService(store).compile_context_pack(
                VNextRetrievalRequest(
                    query=_parse_required_text(arguments, "query"),
                    domains=decision.effective_domains,
                    projects=_parse_string_list(arguments, "projects"),
                    people=_parse_string_list(arguments, "people"),
                    time_window=_parse_optional_text(arguments, "time_window") or "all",
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    # Tri-state: absent means "let the context_depth tier
                    # decide"; an explicit true/false always wins.
                    include_sources=_parse_optional_bool(arguments, key="include_sources"),
                    include_contradictions=_parse_optional_bool(arguments, key="include_contradictions"),
                    context_depth=context_depth,
                    budget_strategy=budget_strategy,
                    max_items=max_items,
                    max_tokens=max_tokens,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                    trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                    **request_kwargs,  # type: ignore[arg-type]
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext context-pack request did not complete")
    return payload


def _handle_alice_vnext_context_pack(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    return _vnext_context_pack_payload(context, arguments)


def _handle_alice_vnext_context_tree(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(arguments, key="limit", default=12, minimum=1, maximum=50)
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    identity = _agent_identity_from_arguments(context, arguments)

    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="context_pack.request",
            domains=_parse_string_list(arguments, "domains"),
            sensitivity_allowed=sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextContextTreeService(store).build_tree(
                ContextTreeRequest(
                    query=_parse_optional_text(arguments, "query") or "",
                    domains=decision.effective_domains,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    limit=limit,
                    include_events=_parse_bool(arguments, key="include_events", default=True),
                    generated_by=actor_type,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                    trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext context-tree request did not complete")
    return payload


def _brain_artifact_request_from_arguments(arguments: Mapping[str, object]) -> BrainArtifactRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    return BrainArtifactRequest(
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        generated_for=_parse_optional_text(arguments, "generated_for"),
        source_limit=_parse_int(arguments, key="source_limit", default=8, minimum=1, maximum=50),
        memory_limit=_parse_int(arguments, key="memory_limit", default=8, minimum=1, maximum=50),
        open_loop_limit=_parse_int(arguments, key="open_loop_limit", default=8, minimum=1, maximum=50),
        artifact_limit=_parse_int(arguments, key="artifact_limit", default=4, minimum=1, maximum=50),
        discover_open_loops=_parse_bool(arguments, key="discover_open_loops", default=True),
        create_candidate_memories=_parse_bool(arguments, key="create_candidate_memories", default=True),
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_generate_daily_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextBrainService(store).generate_daily_brief(_brain_artifact_request_from_arguments(arguments))


def _handle_alice_generate_weekly_synthesis(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextBrainService(store).generate_weekly_synthesis(_brain_artifact_request_from_arguments(arguments))


def _connection_request_from_arguments(arguments: Mapping[str, object]) -> ConnectionFinderRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    auto_accept_threshold = _parse_optional_float(arguments, "auto_accept_threshold")
    return ConnectionFinderRequest(
        query=_parse_optional_text(arguments, "query") or "",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        max_connections=_parse_int(arguments, key="max_connections", default=8, minimum=1, maximum=50),
        auto_accept_threshold=auto_accept_threshold,
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_generate_connections(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    request = _connection_request_from_arguments(arguments)
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="artifact.generate",
        domains=request.domains,
        sensitivity_allowed=request.sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
    )
    request = ConnectionFinderRequest(
        query=request.query,
        domains=decision.effective_domains,
        sensitivity_allowed=decision.effective_sensitivity_allowed,
        max_connections=request.max_connections,
        auto_accept_threshold=request.auto_accept_threshold,
        generation_mode=request.generation_mode,
        model_route_mode=request.model_route_mode,
        model_provider=request.model_provider,
        model=request.model,
        model_temperature=request.model_temperature,
        allow_cloud_private=request.allow_cloud_private,
    )
    with _vnext_store_context(context) as store:
        return VNextConnectionService(store).generate_connection_report(request)


def _handle_alice_graph_edge_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextConnectionService(store).review_edge(
            edge_id=_parse_required_text(arguments, "edge_id"),
            action=_parse_required_text(arguments, "action"),
        )


def _handle_alice_graph_neighborhood(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextConnectionService(store).graph_neighborhood(
            target_id=_parse_required_text(arguments, "target_id"),
        )


def _contradiction_request_from_arguments(arguments: Mapping[str, object]) -> ContradictionFinderRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    return ContradictionFinderRequest(
        query=_parse_optional_text(arguments, "query") or "",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        max_contradictions=_parse_int(arguments, key="max_contradictions", default=8, minimum=1, maximum=50),
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_generate_contradictions(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    request = _contradiction_request_from_arguments(arguments)
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="artifact.generate",
        domains=request.domains,
        sensitivity_allowed=request.sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
    )
    request = ContradictionFinderRequest(
        query=request.query,
        domains=decision.effective_domains,
        sensitivity_allowed=decision.effective_sensitivity_allowed,
        max_contradictions=request.max_contradictions,
        generation_mode=request.generation_mode,
        model_route_mode=request.model_route_mode,
        model_provider=request.model_provider,
        model=request.model,
        model_temperature=request.model_temperature,
        allow_cloud_private=request.allow_cloud_private,
    )
    with _vnext_store_context(context) as store:
        return VNextContradictionService(store).generate_contradiction_report(request)


def _handle_alice_belief_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextContradictionService(store).review_belief(
            belief_id=_parse_required_text(arguments, "belief_id"),
            action=_parse_required_text(arguments, "action"),
            confidence=_parse_optional_float(arguments, "confidence"),
            superseded_by=_parse_optional_text(arguments, "superseded_by"),
        )


def _handle_alice_belief_state(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextContradictionService(store).belief_state(
            belief_id=_parse_required_text(arguments, "belief_id"),
        )


def _project_request_from_arguments(arguments: Mapping[str, object]) -> ProjectAutomationRequest:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    return ProjectAutomationRequest(
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        project_id=_parse_optional_text(arguments, "project_id"),
        person_id=_parse_optional_text(arguments, "person_id"),
        max_items=_parse_int(arguments, key="max_items", default=8, minimum=1, maximum=50),
        **_parse_model_generation_kwargs(arguments),
    )


def _handle_alice_project_update_candidate(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    request = _project_request_from_arguments(arguments)
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="artifact.generate",
            domains=request.domains,
            sensitivity_allowed=request.sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
            workflow_type="project_update_scan",
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextProjectService(store).generate_project_update_candidate(
                ProjectAutomationRequest(
                    domains=decision.effective_domains,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    project_id=request.project_id,
                    person_id=request.person_id,
                    max_items=request.max_items,
                    generated_by=actor_type,
                    actor_id=actor_id,
                    trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                    metadata_json=agent_metadata(identity, decision),
                    generation_mode=request.generation_mode,
                    model_route_mode=request.model_route_mode,
                    model_provider=request.model_provider,
                    model=request.model,
                    model_temperature=request.model_temperature,
                    allow_cloud_private=request.allow_cloud_private,
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext project update candidate generation did not complete")
    return payload


def _handle_alice_project_update_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextProjectService(store).review_project_update(
            artifact_id=_parse_required_text(arguments, "artifact_id"),
            action=_parse_required_text(arguments, "action"),
            edited_current_state=_parse_optional_text(arguments, "edited_current_state"),
        )


def _handle_alice_project_dashboard(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="project.dashboard",
        sensitivity_allowed=sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope"),
    )
    with _vnext_store_context(context) as store:
        return VNextProjectService(store).project_dashboard(
            project_id=_parse_required_text(arguments, "project_id"),
            sensitivity_allowed=decision.effective_sensitivity_allowed,
        )


def _handle_alice_open_loop_extract(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        loops = VNextProjectService(store).extract_open_loops(_project_request_from_arguments(arguments))
    return {"open_loops": loops, "created_count": len(loops)}


def _handle_alice_open_loop_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextProjectService(store).review_open_loop(
            loop_id=_parse_required_text(arguments, "loop_id"),
            action=_parse_required_text(arguments, "action"),
            title=_parse_optional_text(arguments, "title"),
            description=_parse_optional_text(arguments, "description"),
            due_at=_parse_optional_text(arguments, "due_at"),
            priority=_parse_optional_text(arguments, "priority"),
            resolution_note=_parse_optional_text(arguments, "resolution_note"),
        )


def _handle_alice_vnext_capture(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    domain = _parse_optional_text(arguments, "domain") or "unknown"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "unknown"
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="source.capture",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextCaptureService(
                store,
                actor_type=actor_type,
                actor_id=actor_id,
                trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
                agent_identity=identity.to_record() if identity is not None else None,
                policy_decision=decision.to_record(),
            ).capture_text(
                _parse_required_text(arguments, "raw_text"),
                title=_parse_optional_text(arguments, "title"),
                domain=domain,
                sensitivity=sensitivity,
            ).to_record()
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext source capture did not complete")
    return payload


def _handle_alice_vnext_ingest_agent_output(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    if identity is None:
        raise MCPToolError("agent_id is required for alice_vnext_ingest_agent_output")
    domain = _parse_optional_text(arguments, "domain") or "project"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "private"
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="source.capture",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
            write_policy="proposal_only" if _parse_bool(arguments, key="propose_memory", default=False) else None,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextConnectorService(store).ingest_agent_output(
                {
                    "agent_id": identity.agent_id,
                    "agent_type": identity.agent_type,
                    "agent_run_id": identity.agent_run_id,
                    "task_id": identity.task_id,
                    "project_scope": list(identity.project_scope or _parse_string_list(arguments, "project_scope")),
                    "title": _parse_required_text(arguments, "title"),
                    "content": _parse_required_text(arguments, "content"),
                    "output_type": _parse_optional_text(arguments, "output_type") or "general",
                    "domain": domain,
                    "sensitivity": sensitivity,
                    "source_refs": list(_parse_string_list(arguments, "source_refs")),
                    "rationale": _parse_optional_text(arguments, "rationale"),
                    "propose_memory": _parse_bool(arguments, key="propose_memory", default=False),
                },
                policy_decision=decision.to_record(),
            ).to_record()
            append_policy_events(store, identity=identity, decision=decision, target_type="connector", target_id="agent_output")
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("agent output ingestion did not complete")
    return payload


def _handle_alice_vnext_queue_task(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    domain = _parse_optional_text(arguments, "domain") or "unknown"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "unknown"
    write_policy = _parse_optional_text(arguments, "write_policy") or "proposal_only"
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="queue_task.create",
            domains=(domain,),
            sensitivity_allowed=(sensitivity,),
            project_scope=_parse_string_list(arguments, "project_scope"),
            write_policy=write_policy,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextQueueService(store).enqueue_task(
                QueueTaskRequest(
                    title=_parse_required_text(arguments, "title"),
                    task_type=_parse_required_text(arguments, "task_type"),
                    instructions=_parse_required_text(arguments, "instructions"),
                    requested_by=identity.agent_id if identity is not None else "mcp",
                    domain=domain,
                    sensitivity=sensitivity,
                    write_policy=write_policy,
                    scope_json={"project_scope": list(_parse_string_list(arguments, "project_scope"))},
                    actor_type=actor_type,
                    actor_id=actor_id,
                    trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                    run_id=identity.agent_run_id if identity is not None else None,
                    agent_identity=identity.to_record() if identity is not None else None,
                    policy_decision=decision.to_record(),
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext queue task did not complete")
    return payload


def _handle_alice_vnext_generate_artifact(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    workflow_type = _parse_optional_text(arguments, "workflow_type") or "daily_brief"
    if workflow_type in {"connection_report", "connections"}:
        return _handle_alice_generate_connections(context, arguments)
    if workflow_type in {"contradiction_report", "contradictions"}:
        return _handle_alice_generate_contradictions(context, arguments)
    if workflow_type in {"open_loop_review", "project_update_scan", "memory_consolidation"}:
        scheduler_arguments = dict(arguments)
        scheduler_arguments["workflow_type"] = workflow_type
        return _handle_alice_vnext_scheduler_run_now(context, scheduler_arguments)
    if workflow_type not in {"daily_brief", "weekly_synthesis"}:
        raise MCPToolError(
            "workflow_type must be daily_brief, weekly_synthesis, connection_report, "
            "contradiction_report, open_loop_review, project_update_scan, or memory_consolidation"
        )
    identity = _agent_identity_from_arguments(context, arguments)
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    generation_kwargs = _parse_model_generation_kwargs(arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="artifact.generate",
            domains=_parse_string_list(arguments, "domains"),
            sensitivity_allowed=sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            request = BrainArtifactRequest(
                domains=decision.effective_domains,
                sensitivity_allowed=decision.effective_sensitivity_allowed,
                generated_for=_parse_optional_text(arguments, "generated_for"),
                source_limit=_parse_int(arguments, key="source_limit", default=8, minimum=1, maximum=50),
                memory_limit=_parse_int(arguments, key="memory_limit", default=8, minimum=1, maximum=50),
                open_loop_limit=_parse_int(arguments, key="open_loop_limit", default=8, minimum=1, maximum=50),
                artifact_limit=_parse_int(arguments, key="artifact_limit", default=4, minimum=1, maximum=50),
                discover_open_loops=_parse_bool(arguments, key="discover_open_loops", default=True),
                create_candidate_memories=_parse_bool(arguments, key="create_candidate_memories", default=True),
                generated_by=actor_type,
                actor_id=actor_id,
                trace_id=_parse_optional_text(arguments, "trace_id") or decision.trace_id,
                run_id=identity.agent_run_id if identity is not None else None,
                agent_identity=identity.to_record() if identity is not None else None,
                policy_decision=decision.to_record(),
                metadata_json=agent_metadata(identity, decision),
                **generation_kwargs,
            )
            service = VNextBrainService(store)
            payload = (
                service.generate_weekly_synthesis(request)
                if workflow_type == "weekly_synthesis"
                else service.generate_daily_brief(request)
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext artifact generation did not complete")
    return payload


def _handle_alice_vnext_open_loops(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    status = _parse_optional_text(arguments, "status") or "open"
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="open_loop.lookup",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=sensitivity_allowed,
        project_scope=_parse_string_list(arguments, "project_scope"),
    )
    with _vnext_store_context(context) as store:
        loops = store.list_open_loops(
            status=status if status != "all" else None,
            domains=list(decision.effective_domains) or None,
            sensitivity_allowed=list(decision.effective_sensitivity_allowed),
            limit=_parse_int(arguments, key="limit", default=20, minimum=1, maximum=100),
        )
    return {"items": loops, "count": len(loops)}


def _handle_alice_vnext_propose_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    if identity is None:
        raise MCPToolError("agent_id is required for alice_vnext_propose_memory")
    proposal_type = _parse_optional_text(arguments, "proposal_type") or "candidate_memory"
    canonical_text = _parse_required_text(arguments, "canonical_text")
    domain = _parse_optional_text(arguments, "domain") or "unknown"
    sensitivity = _parse_optional_text(arguments, "sensitivity") or "unknown"
    blocked_decision: PolicyDecision | None = None
    memory: JsonObject | None = None
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
    return {"proposal": memory, "policy_decision": decision.to_record(), "review_required": True}


def _handle_alice_vnext_commit_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    payload: JsonObject | None = None
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
        payload = VNextMemoryCommitService(store).commit(identity=identity, request=request)
    return payload


def _handle_alice_vnext_confirm_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="memory.confirm")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextMemoryCommitService(store).confirm(
                identity=identity,
                confirmation_id=_parse_required_text(arguments, "confirmation_id"),
                action=_parse_optional_text(arguments, "action") or "confirm",
                canonical_text=_parse_optional_text(arguments, "canonical_text"),
                rationale=_parse_optional_text(arguments, "rationale"),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory confirmation did not complete")
    return payload


def _handle_alice_vnext_undo_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="memory.undo")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextMemoryCommitService(store).undo(
                identity=identity,
                memory_id=_parse_optional_text(arguments, "memory_id"),
                reason=_parse_optional_text(arguments, "reason"),
                superseded_by_memory_id=_parse_optional_text(arguments, "superseded_by"),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory undo did not complete")
    return payload


def _handle_alice_vnext_correct_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="memory.correct")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextMemoryCommitService(store).correct(
                identity=identity,
                memory_id=_parse_required_text(arguments, "memory_id"),
                canonical_text=_parse_required_text(arguments, "canonical_text"),
                reason=_parse_optional_text(arguments, "reason"),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory correction did not complete")
    return payload


def _handle_alice_vnext_forget_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="memory.forget")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextMemoryCommitService(store).forget(
                identity=identity,
                memory_id=_parse_required_text(arguments, "memory_id"),
                reason=_parse_optional_text(arguments, "reason"),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory forget did not complete")
    return payload


# Statuses that no longer participate in recall; redaction skips the
# forget-first transition for rows already retired.
_REDACT_RETIRED_STATUSES = {"superseded", "archived", "rejected"}


def redact_memory_flow(
    store,
    *,
    memory_id: str,
    reason: str,
    identity: AgentIdentity | None = None,
) -> JsonObject:
    """Expunge one memory's content everywhere, keeping the audit skeleton.

    Order: forget/archive first (when the row is still live, so the
    lifecycle trail records why it left recall), then redact the memory row
    content, then its revisions, then event payloads that reference it. The
    skeleton — ids, types, timestamps, actors, and the ``memory.redacted``
    event trail — survives, which is what proves redaction happened.

    Policy is the caller's job: ``memory.redact`` is restricted to a human
    or an admin agent (HUMAN_OR_ADMIN_ACTIONS); every surface (MCP, HTTP,
    CLI) must evaluate it before calling this flow.
    """
    reason_text = " ".join(reason.split()).strip() if isinstance(reason, str) else ""
    if not reason_text:
        raise VNextMemoryCommitValidationError("reason is required to redact a memory")
    memory = store.get_memory(memory_id)
    if memory is None:
        raise VNextMemoryCommitValidationError("memory was not found")
    actor_type = "agent" if identity is not None else "user"
    forgotten_first = False
    if str(memory.get("status") or "") not in _REDACT_RETIRED_STATUSES:
        VNextMemoryCommitService(store).forget(identity=identity, memory_id=memory_id, reason=reason_text)
        forgotten_first = True
    redacted_memory = store.redact_memory_content(memory_id=memory_id, actor_type=actor_type)
    revisions_result = store.redact_memory_revisions(memory_id=memory_id, actor_type=actor_type)
    events_result = store.redact_memory_events(memory_id=memory_id, actor_type=actor_type)
    return {
        "status": "redacted",
        "memory": redacted_memory,
        "forgotten_first": forgotten_first,
        "redacted_revisions": revisions_result.get("redacted_revisions"),
        "redacted_events": events_result.get("redacted_events"),
        "redaction_marker": REDACTION_MARKER,
        "reason": reason_text,
    }


def _handle_alice_vnext_expire_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
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
    return payload


def _handle_alice_vnext_unexpire_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
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
    return payload


def _handle_alice_vnext_accept_consolidation(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        # Acceptance is a review decision: the commit service policy-checks
        # it internally (human or admin agent only).
        try:
            payload = VNextMemoryCommitService(store).accept_consolidation_candidate(
                _parse_required_text(arguments, "memory_id"),
                reason=_parse_required_text(arguments, "reason"),
                identity=identity,
            )
        except AgentPolicyBlockedError as exc:
            blocked_decision = exc.decision
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext consolidation acceptance did not complete")
    return payload


def _handle_alice_vnext_redact_memory(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        # Redaction has no commit-service seam, so the destructive-action
        # policy (memory.redact: human or admin agent only) is checked here.
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="memory.redact")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = redact_memory_flow(
                store,
                memory_id=_parse_required_text(arguments, "memory_id"),
                reason=_parse_required_text(arguments, "reason"),
                identity=identity,
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory redaction did not complete")
    return payload


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


def _handle_alice_vnext_recent_memory_commits(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
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
    return payload


# Timeline safety bound: supersession chains are already depth-capped by the
# commit service, but revision lists are not; keep the merged view small.
_MEMORY_TIMELINE_MAX_ENTRIES = 50


def _timeline_sort_key(value: object) -> str:
    """ISO-8601 strings (and datetimes rendered by json_safe) sort lexically;
    entries without a usable timestamp sort last, keeping insertion order."""
    rendered = json_safe(value)
    if isinstance(rendered, str) and rendered.strip():
        return rendered.replace("Z", "+00:00")
    return "9999"


def _memory_linked_entities(store: object, memory_id: str) -> list[JsonObject]:
    """Entities connected to one memory via mentions/about graph edges.

    Walks both edge directions (memory -> entity and entity -> memory) and
    resolves each linked entity to a compact record. Callers must check
    store support (list_edges + get_entity) first.
    """
    list_edges = getattr(store, "list_edges")
    get_entity = getattr(store, "get_entity")
    entity_ids: list[str] = []
    edge_sides = (
        (list_edges(from_id=memory_id), "memory", "entity", "to_id"),
        (list_edges(to_id=memory_id), "entity", "memory", "from_id"),
    )
    for edges, from_type, to_type, entity_key in edge_sides:
        for edge in edges:
            if edge.get("edge_type") not in MEMORY_ENTITY_EDGE_TYPES:
                continue
            if str(edge.get("from_type")) != from_type or str(edge.get("to_type")) != to_type:
                continue
            entity_ids.append(str(edge.get(entity_key)))
    entities: list[JsonObject] = []
    seen: set[str] = set()
    for entity_id in entity_ids:
        if entity_id in seen:
            continue
        seen.add(entity_id)
        row = get_entity(entity_id)
        if row is None:
            continue
        entities.append(
            {
                "id": str(row.get("id")),
                "name": row.get("name"),
                "entity_type": row.get("entity_type"),
                "mention_count": row.get("mention_count"),
            }
        )
    return entities


def _memory_evolution_timeline(
    chain: list[JsonObject], revisions: list[Mapping[str, object]]
) -> list[JsonObject]:
    """Merge the supersession chain and revision history into one story.

    One chronological list of ``{at, kind, memory_id, summary}`` entries
    answering "how did this belief evolve": the oldest chain node is the
    creation, each later chain node is a replacement (``superseded_by``),
    and the audited memory's revisions fill in corrections and edits.
    Cycle safety comes from the chain itself (the commit service walks
    pointers with a visited set and a depth bound); the merged list is
    additionally capped at ``_MEMORY_TIMELINE_MAX_ENTRIES``.
    """
    entries: list[JsonObject] = []
    for index, node in enumerate(chain):
        title = node.get("title")
        summary = str(title) if isinstance(title, str) and title.strip() else str(node.get("id"))
        entries.append(
            {
                "at": json_safe(node.get("created_at")),
                "kind": "created" if index == 0 else "superseded_by",
                "memory_id": str(node.get("id")),
                "summary": summary if index == 0 else f"Replaced by: {summary}",
            }
        )
    chain_has_successor = any(node.get("relation") == "successor" for node in chain)
    for revision in revisions:
        revision_type = str(revision.get("revision_type") or "")
        if revision_type == "created":
            continue  # the chain already carries the creation entry
        if revision_type == "corrected":
            kind = "corrected"
        elif revision_type == "superseded":
            if chain_has_successor:
                # The successor chain node already tells this part of the
                # story; a second superseded_by entry would just be noise.
                continue
            kind = "superseded_by"
        else:
            kind = "revised"
        reason = revision.get("reason")
        summary = str(reason) if isinstance(reason, str) and reason.strip() else revision_type
        entries.append(
            {
                "at": json_safe(revision.get("created_at")),
                "kind": kind,
                "memory_id": str(revision.get("memory_id")),
                "summary": summary,
            }
        )
    entries.sort(key=lambda entry: _timeline_sort_key(entry.get("at")))
    # Over the bound, keep the most recent entries: they answer "where did
    # this belief end up" better than ancient intermediate edits.
    return entries[-_MEMORY_TIMELINE_MAX_ENTRIES:]


def _extend_memory_audit(store: object, payload: JsonObject) -> JsonObject:
    """Add entity links and the evolution timeline to an audit payload.

    Chain nodes gain an ``entities`` list (via mentions/about edges) when
    the store has the entity substrate; stores without it keep the plain
    chain. The ``timeline`` field is always added on the memory_id branch.
    """
    chain_value = payload.get("supersession_chain")
    chain = [node for node in chain_value if isinstance(node, dict)] if isinstance(chain_value, list) else []
    revisions_value = payload.get("revisions")
    revisions = [row for row in revisions_value if isinstance(row, Mapping)] if isinstance(revisions_value, list) else []
    supports_entities = callable(getattr(store, "list_edges", None)) and callable(
        getattr(store, "get_entity", None)
    )
    if supports_entities:
        for node in chain:
            node["entities"] = _memory_linked_entities(store, str(node.get("id")))
    payload["timeline"] = _memory_evolution_timeline(chain, revisions)
    return payload


def _handle_alice_vnext_memory_audit(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="memory.audit")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = _extend_memory_audit(
                store,
                VNextMemoryCommitService(store).audit(memory_id=_parse_required_text(arguments, "memory_id")),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext memory audit did not complete")
    return payload


def _handle_alice_vnext_review_items(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        items = [
            row
            for row in store.list_memories(status=None)
            if str(row.get("status")) in {"candidate", "needs_review", "private_only"}
        ][:_parse_int(arguments, key="limit", default=20, minimum=1, maximum=100)]
    return {"items": items, "count": len(items)}


def _handle_alice_vnext_artifact_get(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    artifact_id = _parse_required_text(arguments, "artifact_id")
    with _vnext_store_context(context) as store:
        artifact = store.get_artifact(artifact_id)
    if artifact is None:
        raise MCPToolError(f"artifact {artifact_id} was not found")
    return artifact


def _handle_alice_vnext_artifact_review(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    artifact_id = _parse_required_text(arguments, "artifact_id")
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="artifact.review")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextQueueService(store).review_artifact(
                artifact_id=artifact_id,
                action=_parse_required_text(arguments, "action"),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext artifact review did not complete")
    return payload


def _handle_alice_vnext_scheduler_status(context: MCPRuntimeContext, _arguments: Mapping[str, object]) -> JsonObject:
    with _vnext_store_context(context) as store:
        return VNextSchedulerService(store).status()


def _handle_alice_vnext_scheduler_run_now(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    workflow_type = _parse_required_text(arguments, "workflow_type")
    sensitivity_allowed = _parse_string_list(arguments, "sensitivity_allowed") or (
        "public",
        "internal",
        "private",
        "unknown",
    )
    generation_kwargs = {
        **_parse_model_generation_kwargs(arguments),
        "source_limit": _parse_int(arguments, key="source_limit", default=12, minimum=1, maximum=100),
        "memory_limit": _parse_int(arguments, key="memory_limit", default=12, minimum=1, maximum=100),
        "artifact_limit": _parse_int(arguments, key="artifact_limit", default=8, minimum=1, maximum=100),
        "event_limit": _parse_int(arguments, key="event_limit", default=30, minimum=1, maximum=100),
        "rating_limit": _parse_int(arguments, key="rating_limit", default=20, minimum=1, maximum=100),
        "create_candidate_memories": _parse_bool(arguments, key="create_candidate_memories", default=True),
    }
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="scheduler.run_now",
            domains=_parse_string_list(arguments, "domains"),
            sensitivity_allowed=sensitivity_allowed,
            project_scope=_parse_string_list(arguments, "project_scope") or _parse_string_list(arguments, "projects"),
            workflow_type=workflow_type,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).run_now(
                SchedulerRunRequest(
                    workflow_type=workflow_type,
                    domains=decision.effective_domains,
                    sensitivity_allowed=decision.effective_sensitivity_allowed,
                    generated_for=_parse_optional_text(arguments, "generated_for"),
                    triggered_by="agent" if identity is not None else "user",
                    agent_identity=identity,
                    policy_decision=decision,
                    options=generation_kwargs,
                )
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler run-now did not complete")
    return payload


def _handle_alice_vnext_scheduler_run_due(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    limit_value = arguments.get("limit", 10)
    if not isinstance(limit_value, int):
        raise MCPToolError("limit must be an integer")
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="scheduler.run_due")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).run_due_workflows(
                limit=limit_value,
                triggered_by=actor_type if identity is not None else "scheduler",
                agent_identity=identity,
                policy_decision=decision,
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler run-due did not complete")
    return payload


def _handle_alice_vnext_scheduler_pause(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="scheduler.pause")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).pause_all(actor_type=actor_type)
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler pause did not complete")
    return payload


def _handle_alice_vnext_scheduler_resume(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    identity = _agent_identity_from_arguments(context, arguments)
    blocked_decision: PolicyDecision | None = None
    payload: JsonObject | None = None
    with _vnext_store_context(context) as store:
        actor_type, _actor_id, decision = _policy_checked(store, identity=identity, action="scheduler.resume")
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            payload = VNextSchedulerService(store).resume_all(actor_type=actor_type)
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if payload is None:
        raise MCPToolError("vNext scheduler resume did not complete")
    return payload


_VNEXT_AGENT_SCHEMA_PROPERTIES: dict[str, object] = {
    "agent_id": {"type": "string"},
    "agent_type": {"type": "string"},
    "agent_run_id": {"type": "string"},
    "task_id": {"type": "string"},
    "project_scope": {"type": "array", "items": {"type": "string"}},
    "permission_profile": {"type": "string"},
    "trace_id": {"type": "string"},
    "domains": {"type": "array", "items": {"type": "string"}},
    "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
}


def _vnext_agent_tool_schema(
    properties: dict[str, object] | None = None,
    *,
    required: list[str] | None = None,
) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required or [],
        "properties": {**_VNEXT_AGENT_SCHEMA_PROPERTIES, **(properties or {})},
    }


# Optional caller-identity block shared by the core tools that accept agent
# callers. Declaring an identity routes the call through the permission checks
# and audit logging; omitting it means a direct user call.
_AGENT_IDENTITY_SCHEMA_PROPERTIES: dict[str, object] = {
    "agent_id": {
        "type": "string",
        "description": "Stable identifier of the calling agent, for example 'hermes'. Omit when a human calls directly.",
    },
    "agent_type": {
        "type": "string",
        "description": "Category of the calling agent, such as 'coding_agent' or 'personal_assistant'.",
    },
    "agent_run_id": {
        "type": "string",
        "description": "Identifier of the agent's current run, recorded in the audit log.",
    },
    "task_id": {
        "type": "string",
        "description": "Identifier of the task the agent is working on, recorded in the audit log.",
    },
    "project_scope": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Project names the agent may access; requests outside this scope are filtered or blocked.",
    },
    "permission_profile": {
        "type": "string",
        "description": "Named permission level for the agent, such as 'trusted_local_agent' or 'project_scoped_agent'.",
    },
    "trace_id": {
        "type": "string",
        "description": "Correlation id used to link this call with other logged events.",
    },
}

_DOMAINS_FILTER_SCHEMA: dict[str, object] = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Restrict to these life or work areas, such as 'project', 'professional', or 'personal'.",
}
_MEMORY_TYPES_FILTER_SCHEMA: dict[str, object] = {
    "type": "array",
    "items": {"type": "string", "enum": list(VNEXT_MEMORY_TYPES)},
    "description": "Restrict to these memory types, such as 'decision', 'preference', or 'procedure'. Empty means all types.",
}
_SENSITIVITY_ALLOWED_SCHEMA: dict[str, object] = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Sensitivity levels the caller may see. Defaults to public, internal, private, and unknown.",
}

# The default MCP surface. Exactly these eleven tools are listed and callable
# unless ALICE_MCP_LEGACY_TOOLS=1 also enables the legacy long tail below.
_CORE_TOOL_DEFINITIONS: list[dict[str, object]] = [
    {
        "name": "alice_capture",
        "description": (
            "Submit new information to Alice as a source-backed, reviewable memory. The text is "
            "stored verbatim with provenance and split into searchable chunks; it only becomes "
            "trusted memory after review. Use this whenever you learn something worth keeping."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["raw_text"],
            "properties": {
                "raw_text": {
                    "type": "string",
                    "description": "The text to capture. Stored verbatim as source evidence.",
                },
                "title": {
                    "type": "string",
                    "description": "Short human-readable title for the captured text.",
                },
                "domain": {
                    "type": "string",
                    "description": "Life or work area this belongs to, such as 'project', 'professional', or 'personal'. Defaults to 'unknown'.",
                },
                "sensitivity": {
                    "type": "string",
                    "description": "How sensitive the content is: 'public', 'internal', 'private', or 'unknown' (default).",
                },
                **_AGENT_IDENTITY_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_memory_commit",
        "description": (
            "Write one explicit memory on the user's instruction ('remember this'). The write "
            "is policy-checked, never blind: the outcome is 'committed', 'confirmation_required' "
            "(finish with alice_memory_manage action 'confirm'), 'review_required' (waits for "
            "human review), or 'rejected'. Every outcome is recorded with provenance, a "
            "revision, and an audit event. For source documents and raw notes use "
            "alice_capture instead."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "canonical_text"],
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short human-readable title for the memory.",
                },
                "canonical_text": {
                    "type": "string",
                    "description": "The memory content, phrased as a standalone statement.",
                },
                "memory_type": {
                    "type": "string",
                    "enum": list(VNEXT_MEMORY_TYPES),
                    "description": "What kind of memory this is, such as 'preference', 'decision', or 'procedure'. Defaults to 'semantic'.",
                },
                "domain": {
                    "type": "string",
                    "enum": list(VNEXT_DOMAINS),
                    "description": "Life or work area this belongs to. Sensitive domains such as 'health' require inline confirmation. Defaults to 'unknown'.",
                },
                "sensitivity": {
                    "type": "string",
                    "enum": list(VNEXT_SENSITIVITY_LEVELS),
                    "description": "How sensitive the content is. Levels above 'private' require inline confirmation. Defaults to 'unknown'.",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "How certain the caller is, 0 to 1. Below 0.5 routes to review; below 0.85 requires confirmation. Defaults to 0.9.",
                },
                "source_type": {
                    "type": "string",
                    "description": "Where the content came from. Defaults to 'direct_user_instruction'; external sources such as 'email' or 'web_page' route to review.",
                },
                "source_refs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ids or URLs of supporting sources, stored as provenance links.",
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this memory is being committed. Stored in the audit trail.",
                },
                "idempotency_key": {
                    "type": "string",
                    "description": "Unique key that makes retries safe; a replay returns the original result.",
                },
                **_AGENT_IDENTITY_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_recall",
        "description": (
            "Search Alice's memory. Runs full-text and semantic vector search over stored "
            "memories and merges both rankings (reciprocal-rank fusion); falls back to "
            "full-text only when no embedding endpoint is configured. Returns compact matches "
            "with relevance scores and provenance counts."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, in natural language or keywords.",
                },
                "domains": _DOMAINS_FILTER_SCHEMA,
                "memory_types": _MEMORY_TYPES_FILTER_SCHEMA,
                "projects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restrict results to memories scoped to these project names.",
                },
                "created_by_agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Restrict results to memories committed by these agent ids "
                        "(for example ['openclaw']). Omit to search memories from every writer."
                    ),
                },
                "sensitivity_allowed": _SENSITIVITY_ALLOWED_SCHEMA,
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": _RECALL_MAX_LIMIT,
                    "description": "Maximum number of results to return. Defaults to 8.",
                },
                "context_depth": {
                    "type": "string",
                    "enum": list(CONTEXT_DEPTHS),
                    "description": "Cost/coverage tier: 'minimal' runs full-text search only and caps results at 4, 'low' (default) adds vector and entity-graph stages, 'medium' and 'high' match the context-pack tiers.",
                },
                "budget_strategy": {
                    "type": "string",
                    "enum": list(BUDGET_STRATEGIES),
                    "description": "How to order results: 'balanced' (default) keeps fused relevance order, 'facts_first' boosts semantic/decision/preference memories, 'recent_first' orders by recency; 'contradictions_first' and 'sources_first' match the context-pack strategies and keep fused order here.",
                },
                "debug": {
                    "type": "boolean",
                    "description": "When true, include a retrieval trace showing which search stages ran and why vector search was on or off.",
                },
            },
        },
    },
    {
        "name": "alice_resume",
        "description": (
            "Get a brief for picking work back up: the last recorded decision, the suggested "
            "next action, open loops, and recent changes, optionally scoped to a project, "
            "person, or conversation thread."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text topic to focus the brief on.",
                },
                "thread_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Limit the brief to one conversation thread (UUID).",
                },
                "task_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Limit the brief to one task (UUID).",
                },
                "project": {
                    "type": "string",
                    "description": "Limit the brief to one project name.",
                },
                "person": {
                    "type": "string",
                    "description": "Limit the brief to one person's name.",
                },
                "since": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Only include items from at or after this ISO-8601 timestamp.",
                },
                "until": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Only include items from at or before this ISO-8601 timestamp.",
                },
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                    "description": "Maximum number of recent changes to include.",
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                    "description": "Maximum number of open loops to include.",
                },
                "include_non_promotable_facts": {
                    "type": "boolean",
                    "description": "When true, also include captured facts that were not approved for reuse.",
                },
                "debug": {
                    "type": "boolean",
                    "description": "When true, attach the underlying retrieval trace to the brief.",
                },
            },
        },
    },
    {
        "name": "alice_context_pack",
        "description": (
            "Build a scoped context bundle for a task: the most relevant memories, open loops, "
            "and source documents for a query, with supporting evidence. Use this to brief an "
            "agent before it starts work."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The task or question the context should support.",
                },
                "domains": _DOMAINS_FILTER_SCHEMA,
                "memory_types": _MEMORY_TYPES_FILTER_SCHEMA,
                "projects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Project names to prioritize when selecting context.",
                },
                "created_by_agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Restrict the memory sections to memories committed by these agent ids. "
                        "Omit to build the pack from every writer's memories."
                    ),
                },
                "people": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "People to prioritize when selecting context.",
                },
                "time_window": {
                    "type": "string",
                    "description": "Time range to consider, such as 'all' (default), '7d', or '30d'.",
                },
                "sensitivity_allowed": _SENSITIVITY_ALLOWED_SCHEMA,
                "include_sources": {
                    "type": "boolean",
                    "description": "Include matching source documents. Omit to let context_depth decide (on for low/medium/high, off for minimal); an explicit true or false always wins over the tier default.",
                },
                "include_contradictions": {
                    "type": "boolean",
                    "description": "Include known contradicting evidence when relevant. Omit to let context_depth decide (on for low/medium/high, off for minimal); an explicit true or false always wins over the tier default.",
                },
                "context_depth": {
                    "type": "string",
                    "enum": list(CONTEXT_DEPTHS),
                    "description": "Cost/coverage tier: 'minimal' runs full-text only with at most 4 items, 'low' (default) is the standard hybrid retrieval, 'medium' adds fuller sections, 'high' also walks supersession chains. No tier performs LLM synthesis.",
                },
                "budget_strategy": {
                    "type": "string",
                    "enum": list(BUDGET_STRATEGIES),
                    "description": "How the token budget is spent when max_tokens is tight: 'balanced' (default), 'facts_first' boosts semantic/decision/preference memories, 'recent_first' orders memories by recency, 'contradictions_first' packs contradicting evidence before memories, 'sources_first' packs source documents before memories.",
                },
                "max_items": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of memories to include. Defaults to 8.",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 500,
                    "maximum": 50000,
                    "description": "Token budget for the pack. Lowest-ranked items are dropped to fit; the result is reported in token_report. Defaults to 8000.",
                },
                "debug": {
                    "type": "boolean",
                    "description": "When true, include the full retrieval trace and query interpretation.",
                },
                **_AGENT_IDENTITY_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_open_loops",
        "description": (
            "List or manage open loops: unresolved tasks, blockers, and follow-ups. The default "
            "action 'list' returns current loops; 'close', 'snooze', 'edit', and 'reopen' "
            "update one loop by id."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {
                    "type": "string",
                    "enum": list(_OPEN_LOOP_TOOL_ACTIONS),
                    "description": "What to do: 'list' (default) to read loops, or 'close', 'snooze', 'edit', 'reopen' to change one loop.",
                },
                "status": {
                    "type": "string",
                    "description": "For 'list': filter by loop status such as 'open' (default), 'resolved', or 'all'.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "For 'list': maximum number of loops to return. Defaults to 20.",
                },
                "domains": _DOMAINS_FILTER_SCHEMA,
                "sensitivity_allowed": _SENSITIVITY_ALLOWED_SCHEMA,
                "loop_id": {
                    "type": "string",
                    "description": "Id of the loop to change. Required for every action except 'list'.",
                },
                "title": {
                    "type": "string",
                    "description": "For 'edit': new title for the loop.",
                },
                "description": {
                    "type": "string",
                    "description": "For 'edit': new description for the loop.",
                },
                "due_at": {
                    "type": "string",
                    "description": "For 'snooze' (required) or 'edit': new due timestamp, ISO-8601.",
                },
                "priority": {
                    "type": "string",
                    "description": "For 'edit': new priority label, such as 'high'.",
                },
                "resolution_note": {
                    "type": "string",
                    "description": "For 'close': short note recording how the loop was resolved.",
                },
                **_AGENT_IDENTITY_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_recent_decisions",
        "description": (
            "List the most recent recorded decisions, newest first, optionally filtered by "
            "project, person, thread, or time window."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text filter for which decisions to return.",
                },
                "thread_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Limit results to one conversation thread (UUID).",
                },
                "task_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Limit results to one task (UUID).",
                },
                "project": {
                    "type": "string",
                    "description": "Limit results to one project name.",
                },
                "person": {
                    "type": "string",
                    "description": "Limit results to one person's name.",
                },
                "since": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Only include decisions recorded at or after this ISO-8601 timestamp.",
                },
                "until": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Only include decisions recorded at or before this ISO-8601 timestamp.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_CONTINUITY_RECALL_LIMIT,
                    "description": "Maximum number of decisions to return.",
                },
            },
        },
    },
    {
        "name": "alice_memory_review",
        "description": (
            "Inspect the memory review queue. Without an id it lists items awaiting human "
            "review; with review_item_id it returns full detail for one item, including why it "
            "was flagged. Use alice_memory_correct to act on an item."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "review_item_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "UUID of one review item to inspect in detail.",
                },
                "continuity_object_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Alias for review_item_id; both refer to the stored memory record's UUID.",
                },
                "status": {
                    "type": "string",
                    "enum": list(_REVIEW_STATUS_CHOICES),
                    "description": "Which queue slice to list, such as 'pending_review' or 'correction_ready' (default). Use 'all' for everything.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_CONTINUITY_REVIEW_LIMIT,
                    "description": "Maximum number of queue items to return.",
                },
            },
        },
    },
    {
        "name": "alice_memory_correct",
        "description": (
            "Propose a correction to an existing memory: approve it as-is, edit and approve, "
            "reject it, or supersede it with a replacement. Every change keeps an audit trail."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "review_item_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "UUID of the memory record to act on. Provide this or continuity_object_id.",
                },
                "continuity_object_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "Alias for review_item_id; both refer to the same memory record UUID.",
                },
                "action": {
                    "type": "string",
                    "enum": list(_REVIEW_APPLY_ACTION_CHOICES),
                    "description": "What to do with the memory: 'approve', 'edit-and-approve', 'reject', or 'supersede-existing'.",
                },
                "reason": {
                    "type": "string",
                    "description": "Why the change is being made. Stored in the audit trail.",
                },
                "title": {
                    "type": "string",
                    "description": "For edit-and-approve: corrected title.",
                },
                "body": {
                    "type": "object",
                    "description": "For edit-and-approve: corrected structured content.",
                },
                "provenance": {
                    "type": "object",
                    "description": "For edit-and-approve: corrected provenance details.",
                },
                "confidence": {
                    "type": "number",
                    "description": "For edit-and-approve: corrected confidence, between 0 and 1.",
                },
                "replacement_title": {
                    "type": "string",
                    "description": "For supersede-existing: title of the replacement memory.",
                },
                "replacement_body": {
                    "type": "object",
                    "description": "For supersede-existing: structured content of the replacement memory.",
                },
                "replacement_provenance": {
                    "type": "object",
                    "description": "For supersede-existing: provenance details of the replacement memory.",
                },
                "replacement_confidence": {
                    "type": "number",
                    "description": "For supersede-existing: confidence of the replacement memory, between 0 and 1.",
                },
            },
        },
    },
    {
        "name": "alice_memory_manage",
        "description": (
            "Manage a memory written through alice_memory_commit: confirm a pending "
            "confirmation, undo a commit, forget a memory, expire or unexpire its validity "
            "window, accept a consolidation candidate, or redact its content. Undo, forget, "
            "and expire hide the memory from recall but keep its revisions and audit events; "
            "redact permanently expunges the content everywhere while keeping the audit "
            "skeleton, and is restricted to a human operator or an admin agent (as is "
            "accept_consolidation)."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": list(_MEMORY_MANAGE_ACTIONS),
                    "description": (
                        "What to do: 'confirm' completes a pending confirmation by confirmation_id, "
                        "'undo' reverses a commit, 'forget' retires a memory from recall, 'expire' "
                        "closes the memory's validity window (valid_to) so recall stops returning it, "
                        "'unexpire' reopens that window, 'accept_consolidation' accepts a "
                        "consolidation candidate and supersedes the memories it merges, and 'redact' "
                        "permanently expunges the memory's content from the row, its revisions, and "
                        "event payloads while keeping the audit skeleton."
                    ),
                },
                "confirmation_id": {
                    "type": "string",
                    "description": "For confirm: the confirmation id returned by alice_memory_commit.",
                },
                "memory_id": {
                    "type": "string",
                    "description": "The memory to act on. Required for forget, expire, unexpire, accept_consolidation, and redact; for undo it defaults to the calling agent's most recent commit.",
                },
                "canonical_text": {
                    "type": "string",
                    "description": "For confirm: corrected text to store instead of the proposed text.",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this change is being made. Stored in the audit trail. Required for expire, unexpire, accept_consolidation, and redact.",
                },
                "valid_to": {
                    "type": "string",
                    "description": "For expire: ISO-8601 timestamp when the memory stops being valid. Defaults to now, which hides the memory from recall immediately.",
                },
                "superseded_by": {
                    "type": "string",
                    "description": "For undo: id of the memory that replaces the undone one. Links the two so alice_explain can show what changed and when.",
                },
                **_AGENT_IDENTITY_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_explain",
        "description": (
            "Explain where a memory came from, why it can be trusted, and how it changed "
            "over time: source evidence, revision history, corroborations, and contradiction "
            "signals, plus the memory's supersession chain (what it replaced and what "
            "replaced it, oldest to newest, each entry listing the people, projects, and "
            "other entities it is linked to) and a timeline that merges creations, edits, "
            "corrections, and replacements into one chronological story. "
            "Pass memory_id for a result from alice_recall, continuity_object_id for a "
            "reviewed record, or entity_id (optionally with 'at') for a point-in-time "
            "explanation."
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "Id of a memory returned by alice_recall; returns its provenance links, revisions, event history, supersession_chain (each entry has id, title, status, created_at, its relation to this memory: predecessor, self, or successor, and the entities it is linked to when available), and a timeline: one chronological list of {at, kind, memory_id, summary} entries (kind is created, revised, corrected, or superseded_by) telling how this memory evolved.",
                },
                "continuity_object_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "UUID of a reviewed memory record; returns its evidence chain and trust signals.",
                },
                "entity_id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "UUID of an entity; explains which facts were in effect for it and why.",
                },
                "at": {
                    "type": "string",
                    "format": "date-time",
                    "description": "With entity_id: the point in time to explain, ISO-8601. Defaults to now.",
                },
                "include_raw_content": {
                    "type": "boolean",
                    "description": "Include raw captured content in the explanation. Only allowed in development or test environments.",
                },
            },
        },
    },
]

# Legacy long-tail surface. Hidden unless ALICE_MCP_LEGACY_TOOLS=1; kept for
# existing integrations. Tool names that collide with the core nine are owned
# by the core definitions above.
_LEGACY_TOOL_DEFINITIONS: list[dict[str, object]] = [
    {
        "name": "alice_capture_candidates",
        "description": "Extract continuity candidates from one user/assistant turn without writing memory.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "user_content": {"type": "string"},
                "assistant_content": {"type": "string"},
                "session_id": {"type": "string"},
                "source_kind": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_commit_captures",
        "description": "Commit extracted continuity candidates using manual/assist/auto bridge policy.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "mode": {"type": "string", "enum": list(CONTINUITY_CAPTURE_COMMIT_MODES)},
                "sync_fingerprint": {"type": "string"},
                "source_kind": {"type": "string"},
                "candidates": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
        },
    },
    {
        "name": "alice_memory_mutations_generate",
        "description": "Generate explicit memory mutation candidates with ADD/UPDATE/SUPERSEDE/DELETE/NOOP classification.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "user_content": {"type": "string"},
                "assistant_content": {"type": "string"},
                "mode": {"type": "string", "enum": list(CONTINUITY_CAPTURE_COMMIT_MODES)},
                "sync_fingerprint": {"type": "string"},
                "source_kind": {"type": "string"},
                "session_id": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "target_continuity_object_id": {"type": "string", "format": "uuid"},
            },
        },
    },
    {
        "name": "alice_memory_mutations_list_candidates",
        "description": "Inspect generated explicit memory mutation candidates.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "policy_action": {"type": "string", "enum": ["auto_apply", "review_required", "skip"]},
                "operation_type": {"type": "string", "enum": ["ADD", "UPDATE", "SUPERSEDE", "DELETE", "NOOP"]},
                "sync_fingerprint": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_memory_mutations_commit",
        "description": "Apply explicit memory mutation candidates with idempotent audit records.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "candidate_ids": {
                    "type": "array",
                    "items": {"type": "string", "format": "uuid"},
                },
                "sync_fingerprint": {"type": "string"},
                "include_review_required": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_memory_mutations_list_operations",
        "description": "Inspect committed explicit memory operations and their result links.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "sync_fingerprint": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_recall_debug",
        "description": "Run hybrid continuity retrieval with per-candidate stage scores and exclusion reasons.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_RECALL_LIMIT},
            },
        },
    },
    {
        "name": "alice_state_at",
        "description": "Show entity facts and edges that were effective at a specific point in time.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["entity_id"],
            "properties": {
                "entity_id": {"type": "string", "format": "uuid"},
                "at": {"type": "string", "format": "date-time"},
            },
        },
    },
    {
        "name": "alice_resume_debug",
        "description": "Compile a resumption brief with the underlying hybrid retrieval trace attached.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
                "include_non_promotable_facts": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_brief",
        "description": "Compile the primary one-call continuity brief for general, resume, handoff, coding, or operator contexts.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "brief_type": {
                    "type": "string",
                    "enum": CONTINUITY_BRIEF_TYPE_ORDER,
                },
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "max_relevant_facts": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
                },
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
                "max_conflicts": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
                },
                "max_timeline_highlights": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
                },
                "include_non_promotable_facts": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_task_brief",
        "description": "Compile and persist one task-adaptive brief for recall, resume, worker, or handoff workloads.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["mode"],
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["user_recall", "resume", "worker_subtask", "agent_handoff"],
                },
                "query": {"type": "string"},
                "workspace_id": {"type": "string", "format": "uuid"},
                "pack_id": {"type": "string"},
                "pack_version": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "include_non_promotable_facts": {"type": "boolean"},
                "provider_strategy": {"type": "string"},
                "model_pack_strategy": {"type": "string"},
                "token_budget": {"type": "integer", "minimum": 1, "maximum": MAX_TASK_BRIEF_TOKEN_BUDGET},
            },
        },
    },
    {
        "name": "alice_task_brief_show",
        "description": "Load one persisted task-adaptive brief by id.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["task_brief_id"],
            "properties": {
                "task_brief_id": {"type": "string", "format": "uuid"},
            },
        },
    },
    {
        "name": "alice_task_brief_compare",
        "description": "Compare two task-brief modes for the same scope and show which one is smaller.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["mode", "compare_to_mode"],
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["user_recall", "resume", "worker_subtask", "agent_handoff"],
                },
                "compare_to_mode": {
                    "type": "string",
                    "enum": ["user_recall", "resume", "worker_subtask", "agent_handoff"],
                },
                "query": {"type": "string"},
                "workspace_id": {"type": "string", "format": "uuid"},
                "pack_id": {"type": "string"},
                "pack_version": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "include_non_promotable_facts": {"type": "boolean"},
                "provider_strategy": {"type": "string"},
                "model_pack_strategy": {"type": "string"},
                "compare_model_pack_strategy": {"type": "string"},
                "token_budget": {"type": "integer", "minimum": 1, "maximum": MAX_TASK_BRIEF_TOKEN_BUDGET},
                "compare_token_budget": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_TASK_BRIEF_TOKEN_BUDGET,
                },
            },
        },
    },
    {
        "name": "alice_retrieval_trace",
        "description": "Load one persisted retrieval trace by run id.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["retrieval_run_id"],
            "properties": {
                "retrieval_run_id": {"type": "string", "format": "uuid"},
            },
        },
    },
    {
        "name": "alice_prefetch_context",
        "description": "Assemble deterministic pre-turn prefetch context text from continuity resumption state.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "max_recent_changes": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "max_open_loops": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
                "include_non_promotable_facts": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_recent_changes",
        "description": "List recent continuity changes from the shipped resumption assembly logic.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "thread_id": {"type": "string", "format": "uuid"},
                "task_id": {"type": "string", "format": "uuid"},
                "project": {"type": "string"},
                "person": {"type": "string"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
            },
        },
    },
    {
        "name": "alice_timeline",
        "description": "List chronological temporal history for one entity.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["entity_id"],
            "properties": {
                "entity_id": {"type": "string", "format": "uuid"},
                "since": {"type": "string", "format": "date-time"},
                "until": {"type": "string", "format": "date-time"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_TEMPORAL_TIMELINE_LIMIT},
            },
        },
    },
    {
        "name": "alice_review_queue",
        "description": "List pending review queue items or fetch one review item detail with explanation metadata.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "review_item_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": list(_REVIEW_STATUS_CHOICES)},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_review_apply",
        "description": "Apply approve/reject/edit-and-approve/supersede-existing review actions deterministically.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "review_item_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": list(_REVIEW_APPLY_ACTION_CHOICES)},
                "reason": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "object"},
                "provenance": {"type": "object"},
                "confidence": {"type": "number"},
                "replacement_title": {"type": "string"},
                "replacement_body": {"type": "object"},
                "replacement_provenance": {"type": "object"},
                "replacement_confidence": {"type": "number"},
            },
        },
    },
    {
        "name": "alice_contradictions_detect",
        "description": "Run contradiction detection and persist current contradiction and trust state.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_contradictions_list",
        "description": "List contradiction cases or fetch one contradiction case detail.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "contradiction_case_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "status": {"type": "string", "enum": ["open", "resolved", "dismissed"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_contradictions_resolve",
        "description": "Resolve one contradiction case with an explicit audit action.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["contradiction_case_id", "action"],
            "properties": {
                "contradiction_case_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": list(CONTRADICTION_RESOLUTION_ACTIONS)},
                "note": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_trust_signals",
        "description": "Inspect current stored trust signals for continuity objects.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "signal_state": {"type": "string", "enum": ["active", "inactive"]},
                "signal_type": {
                    "type": "string",
                    "enum": ["correction", "corroboration", "contradiction", "weak_inference"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_CONTINUITY_REVIEW_LIMIT},
            },
        },
    },
    {
        "name": "alice_artifact_inspect",
        "description": "Inspect one archived artifact with copies and extracted segments.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["artifact_id"],
            "properties": {
                "artifact_id": {"type": "string", "format": "uuid"},
                "include_raw_content": {"type": "boolean"},
            },
        },
    },
    {
        "name": "alice_vnext_context_pack",
        "description": "Compile a vNext provenance-aware context pack with retrieval trace metadata.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "projects": {"type": "array", "items": {"type": "string"}},
                "people": {"type": "array", "items": {"type": "string"}},
                "time_window": {"type": "string"},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "include_sources": {"type": "boolean"},
                "include_contradictions": {"type": "boolean"},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
                "max_tokens": {"type": "integer", "minimum": 500, "maximum": 50000},
            },
        },
    },
    {
        "name": "alice_vnext_context_tree",
        "description": "Return a read-only agent-navigable tree over vNext projects, memories, sources, open loops, artifacts, and events.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "query": {"type": "string"},
                "projects": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "include_events": {"type": "boolean"},
                "trace_id": {"type": "string"},
            },
        ),
    },
    {
        "name": "alice_generate_daily_brief",
        "description": "Generate a vNext daily brief artifact with provenance and review status.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "generated_for": {"type": "string", "format": "date"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "source_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "memory_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "open_loop_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "artifact_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "discover_open_loops": {"type": "boolean"},
                "create_candidate_memories": {"type": "boolean"},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_generate_weekly_synthesis",
        "description": "Generate a vNext weekly synthesis artifact and candidate insight memories.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "generated_for": {"type": "string", "format": "date"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "source_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "memory_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "open_loop_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "artifact_limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "discover_open_loops": {"type": "boolean"},
                "create_candidate_memories": {"type": "boolean"},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_generate_connections",
        "description": "Generate a vNext connection report and candidate graph edges.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_connections": {"type": "integer", "minimum": 1, "maximum": 50},
                "auto_accept_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_graph_edge_review",
        "description": "Review, accept, or reject a vNext candidate graph edge.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["edge_id", "action"],
            "properties": {
                "edge_id": {"type": "string"},
                "action": {"type": "string", "enum": ["review", "accept", "reject"]},
            },
        },
    },
    {
        "name": "alice_graph_neighborhood",
        "description": "Return active vNext graph edges around a target id.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["target_id"],
            "properties": {
                "target_id": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_generate_contradictions",
        "description": "Generate a vNext contradiction report and candidate contradiction graph edges.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_contradictions": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_belief_review",
        "description": "Reinforce, challenge, supersede, or retire a vNext belief.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["belief_id", "action"],
            "properties": {
                "belief_id": {"type": "string"},
                "action": {"type": "string", "enum": ["reinforce", "challenge", "supersede", "retire"]},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "superseded_by": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_belief_state",
        "description": "Return current and historical state for a vNext belief.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["belief_id"],
            "properties": {
                "belief_id": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_project_update_candidate",
        "description": "Generate a vNext project update candidate artifact.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "project_id": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        },
    },
    {
        "name": "alice_project_update_review",
        "description": "Accept, edit, or reject a vNext project update candidate artifact.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["artifact_id", "action"],
            "properties": {
                "artifact_id": {"type": "string"},
                "action": {"type": "string", "enum": ["accept", "edit", "reject"]},
                "edited_current_state": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_project_dashboard",
        "description": "Return vNext project dashboard state, memories, open loops, and artifacts.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["project_id"],
            "properties": {
                "project_id": {"type": "string"},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "alice_open_loop_extract",
        "description": "Extract vNext candidate open loops from selected sources.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "project_id": {"type": "string"},
                "person_id": {"type": "string"},
                "domains": {"type": "array", "items": {"type": "string"}},
                "sensitivity_allowed": {"type": "array", "items": {"type": "string"}},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        },
    },
    {
        "name": "alice_open_loop_review",
        "description": "Close, snooze, edit, or reopen a vNext open loop.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["loop_id", "action"],
            "properties": {
                "loop_id": {"type": "string"},
                "action": {"type": "string", "enum": ["close", "snooze", "edit", "reopen"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "due_at": {"type": "string"},
                "priority": {"type": "string"},
                "resolution_note": {"type": "string"},
            },
        },
    },
    {
        "name": "alice_vnext_capture",
        "description": "Capture a vNext source with optional agent identity and policy checks.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "raw_text": {"type": "string"},
                "title": {"type": "string"},
                "source_type": {"type": "string"},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
            },
            required=["raw_text"],
        ),
    },
    {
        "name": "alice_vnext_ingest_agent_output",
        "description": "Capture Hermes/OpenClaw agent output as source/artifact evidence with optional review-only memory proposal.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "output_type": {
                    "type": "string",
                    "enum": ["sprint_summary", "research_summary", "code_review", "project_update", "decision", "general"],
                },
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "source_refs": {"type": "array", "items": {"type": "string"}},
                "rationale": {"type": "string"},
                "propose_memory": {"type": "boolean"},
            },
            required=["agent_id", "title", "content"],
        ),
    },
    {
        "name": "alice_vnext_queue_task",
        "description": "Create a vNext queue task with optional agent identity and policy checks.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "title": {"type": "string"},
                "task_type": {"type": "string"},
                "instructions": {"type": "string"},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "scheduled_for": {"type": "string"},
            },
            required=["title", "task_type", "instructions"],
        ),
    },
    {
        "name": "alice_vnext_generate_artifact",
        "description": "Generate a vNext artifact workflow such as daily_brief or weekly_synthesis.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "artifact_type": {"type": "string"},
                "workflow_type": {"type": "string"},
                "generated_for": {"type": "string"},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 50},
                "source_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "memory_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "artifact_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "event_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "rating_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "create_candidate_memories": {"type": "boolean"},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
        ),
    },
    {
        "name": "alice_vnext_project_dashboard",
        "description": "Return vNext project dashboard state.",
        "inputSchema": _vnext_agent_tool_schema({"project_id": {"type": "string"}}, required=["project_id"]),
    },
    {
        "name": "alice_vnext_open_loops",
        "description": "List vNext open loops with domain and sensitivity filters.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "project_id": {"type": "string"},
                "source_id": {"type": "string"},
                "status": {"type": "string"},
                "priority": {"type": "string"},
                "due_at": {"type": "string"},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        ),
    },
    {
        "name": "alice_vnext_recent_decisions",
        "description": "Return recent decision context through the existing continuity lookup.",
        "inputSchema": _vnext_agent_tool_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    },
    {
        "name": "alice_vnext_recent_changes",
        "description": "Return recent change context through the existing continuity lookup.",
        "inputSchema": _vnext_agent_tool_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    },
    {
        "name": "alice_vnext_find_connections",
        "description": "Generate a vNext connection report.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "max_connections": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            }
        ),
    },
    {
        "name": "alice_vnext_find_contradictions",
        "description": "Generate a vNext contradiction report.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "max_contradictions": {"type": "integer", "minimum": 1, "maximum": 50},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            }
        ),
    },
    {
        "name": "alice_vnext_propose_memory",
        "description": "Submit an agent memory proposal for human review.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "proposal_type": {"type": "string"},
                "title": {"type": "string"},
                "canonical_text": {"type": "string"},
                "source_refs": {"type": "array", "items": {"type": "string"}},
                "domain": {"type": "string"},
                "sensitivity": {"type": "string"},
                "confidence": {"type": "number"},
                "rationale": {"type": "string"},
            },
            required=["agent_id", "canonical_text"],
        ),
    },
    {
        "name": "alice_vnext_commit_memory",
        "description": "Commit an explicit trusted-agent memory write through Alice policy, or return confirmation/review/reject.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "intent": {"type": "string"},
                "title": {"type": "string"},
                "canonical_text": {"type": "string"},
                "memory_type": {"type": "string", "enum": list(VNEXT_MEMORY_TYPES)},
                "domain": {"type": "string", "enum": list(VNEXT_DOMAINS)},
                "sensitivity": {"type": "string", "enum": list(VNEXT_SENSITIVITY_LEVELS)},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "source_type": {"type": "string"},
                "source_refs": {"type": "array", "items": {"type": "string"}},
                "conversation_excerpt": {"type": "string"},
                "rationale": {"type": "string"},
                "idempotency_key": {"type": "string"},
                "contradiction_refs": {"type": "array", "items": {"type": "string"}},
            },
            required=["agent_id", "title", "canonical_text"],
        ),
    },
    {
        "name": "alice_vnext_confirm_memory",
        "description": "Confirm, reject, or edit a pending inline agentic memory confirmation.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "confirmation_id": {"type": "string"},
                "action": {"type": "string", "enum": ["confirm", "reject", "edit"]},
                "canonical_text": {"type": "string"},
                "rationale": {"type": "string"},
            },
            required=["confirmation_id"],
        ),
    },
    {
        "name": "alice_vnext_undo_memory",
        "description": "Undo an agentic memory commit without deleting the audit trail.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "memory_id": {"type": "string"},
                "reason": {"type": "string"},
                "superseded_by": {"type": "string"},
            },
        ),
    },
    {
        "name": "alice_vnext_correct_memory",
        "description": "Correct an agentic memory commit and append a revision.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "memory_id": {"type": "string"},
                "canonical_text": {"type": "string"},
                "reason": {"type": "string"},
            },
            required=["memory_id", "canonical_text"],
        ),
    },
    {
        "name": "alice_vnext_forget_memory",
        "description": "Forget an agentic memory commit while preserving audit history.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "memory_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            required=["memory_id"],
        ),
    },
    {
        "name": "alice_vnext_recent_memory_commits",
        "description": "List recent agentic memory commits, confirmations, corrections, undos, and forgets.",
        "inputSchema": _vnext_agent_tool_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 100}}),
    },
    {
        "name": "alice_vnext_memory_audit",
        "description": "Return memory, revision, provenance, and event audit details for one memory.",
        "inputSchema": _vnext_agent_tool_schema({"memory_id": {"type": "string"}}, required=["memory_id"]),
    },
    {
        "name": "alice_vnext_review_items",
        "description": "List pending vNext memory review items.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "status": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
        ),
    },
    {
        "name": "alice_vnext_artifact_get",
        "description": "Get one vNext generated artifact.",
        "inputSchema": _vnext_agent_tool_schema({"artifact_id": {"type": "string"}}, required=["artifact_id"]),
    },
    {
        "name": "alice_vnext_artifact_review",
        "description": "Review a vNext artifact; agent callers are policy checked.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "artifact_id": {"type": "string"},
                "action": {"type": "string"},
                "reason": {"type": "string"},
            },
            required=["artifact_id", "action"],
        ),
    },
    {
        "name": "alice_vnext_scheduler_status",
        "description": "Return governed local scheduler status.",
        "inputSchema": _vnext_agent_tool_schema(),
    },
    {
        "name": "alice_vnext_scheduler_run_now",
        "description": "Run a governed scheduler workflow now with policy checks.",
        "inputSchema": _vnext_agent_tool_schema(
            {
                "workflow_type": {"type": "string"},
                "generated_for": {"type": "string"},
                "source_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "memory_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "artifact_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "event_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "rating_limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "create_candidate_memories": {"type": "boolean"},
                **_MODEL_GENERATION_SCHEMA_PROPERTIES,
            },
            required=["workflow_type"],
        ),
    },
    {
        "name": "alice_vnext_scheduler_run_due",
        "description": "Run enabled governed scheduler workflows whose next_run_at is due.",
        "inputSchema": _vnext_agent_tool_schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
    },
    {
        "name": "alice_vnext_scheduler_pause",
        "description": "Pause all governed scheduler workflows.",
        "inputSchema": _vnext_agent_tool_schema(),
    },
    {
        "name": "alice_vnext_scheduler_resume",
        "description": "Resume all governed scheduler workflows.",
        "inputSchema": _vnext_agent_tool_schema(),
    },
]

_TOOL_HANDLERS = {
    "alice_capture": _handle_alice_vnext_capture,
    # Core front door for explicit agent writes; same handler as the legacy
    # alice_vnext_commit_memory alias below.
    "alice_memory_commit": _handle_alice_vnext_commit_memory,
    "alice_memory_manage": _handle_alice_memory_manage,
    "alice_capture_candidates": _handle_alice_capture_candidates,
    "alice_commit_captures": _handle_alice_commit_captures,
    "alice_memory_mutations_generate": _handle_alice_memory_mutations_generate,
    "alice_memory_mutations_list_candidates": _handle_alice_memory_mutations_list_candidates,
    "alice_memory_mutations_commit": _handle_alice_memory_mutations_commit,
    "alice_memory_mutations_list_operations": _handle_alice_memory_mutations_list_operations,
    "alice_recall": _handle_alice_recall,
    "alice_recall_debug": _handle_alice_recall_debug,
    "alice_state_at": _handle_alice_state_at,
    "alice_resume": _handle_alice_resume,
    "alice_resume_debug": _handle_alice_resume_debug,
    "alice_brief": _handle_alice_brief,
    "alice_task_brief": _handle_alice_task_brief,
    "alice_task_brief_show": _handle_alice_task_brief_show,
    "alice_task_brief_compare": _handle_alice_task_brief_compare,
    "alice_retrieval_trace": _handle_alice_retrieval_trace,
    "alice_prefetch_context": _handle_alice_prefetch_context,
    "alice_open_loops": _handle_alice_open_loops,
    "alice_recent_decisions": _handle_alice_recent_decisions,
    "alice_recent_changes": _handle_alice_recent_changes,
    "alice_timeline": _handle_alice_timeline,
    "alice_review_queue": _handle_alice_review_queue,
    "alice_review_apply": _handle_alice_review_apply,
    "alice_contradictions_detect": _handle_alice_contradictions_detect,
    "alice_contradictions_list": _handle_alice_contradictions_list,
    "alice_contradictions_resolve": _handle_alice_contradictions_resolve,
    "alice_trust_signals": _handle_alice_trust_signals,
    "alice_memory_review": _handle_alice_memory_review,
    "alice_memory_correct": _handle_alice_memory_correct,
    "alice_explain": _handle_alice_explain,
    "alice_artifact_inspect": _handle_alice_artifact_inspect,
    "alice_context_pack": _handle_alice_context_pack,
    "alice_vnext_context_pack": _handle_alice_vnext_context_pack,
    "alice_vnext_context_tree": _handle_alice_vnext_context_tree,
    "alice_generate_daily_brief": _handle_alice_generate_daily_brief,
    "alice_generate_weekly_synthesis": _handle_alice_generate_weekly_synthesis,
    "alice_generate_connections": _handle_alice_generate_connections,
    "alice_graph_edge_review": _handle_alice_graph_edge_review,
    "alice_graph_neighborhood": _handle_alice_graph_neighborhood,
    "alice_generate_contradictions": _handle_alice_generate_contradictions,
    "alice_belief_review": _handle_alice_belief_review,
    "alice_belief_state": _handle_alice_belief_state,
    "alice_project_update_candidate": _handle_alice_project_update_candidate,
    "alice_project_update_review": _handle_alice_project_update_review,
    "alice_project_dashboard": _handle_alice_project_dashboard,
    "alice_open_loop_extract": _handle_alice_open_loop_extract,
    "alice_open_loop_review": _handle_alice_open_loop_review,
    "alice_vnext_capture": _handle_alice_vnext_capture,
    "alice_vnext_ingest_agent_output": _handle_alice_vnext_ingest_agent_output,
    "alice_vnext_queue_task": _handle_alice_vnext_queue_task,
    "alice_vnext_generate_artifact": _handle_alice_vnext_generate_artifact,
    "alice_vnext_project_dashboard": _handle_alice_project_dashboard,
    "alice_vnext_open_loops": _handle_alice_vnext_open_loops,
    "alice_vnext_recent_decisions": _handle_alice_recent_decisions,
    "alice_vnext_recent_changes": _handle_alice_recent_changes,
    "alice_vnext_find_connections": _handle_alice_generate_connections,
    "alice_vnext_find_contradictions": _handle_alice_generate_contradictions,
    "alice_vnext_propose_memory": _handle_alice_vnext_propose_memory,
    "alice_vnext_commit_memory": _handle_alice_vnext_commit_memory,
    "alice_vnext_confirm_memory": _handle_alice_vnext_confirm_memory,
    "alice_vnext_undo_memory": _handle_alice_vnext_undo_memory,
    "alice_vnext_correct_memory": _handle_alice_vnext_correct_memory,
    "alice_vnext_forget_memory": _handle_alice_vnext_forget_memory,
    "alice_vnext_recent_memory_commits": _handle_alice_vnext_recent_memory_commits,
    "alice_vnext_memory_audit": _handle_alice_vnext_memory_audit,
    "alice_vnext_review_items": _handle_alice_vnext_review_items,
    "alice_vnext_artifact_get": _handle_alice_vnext_artifact_get,
    "alice_vnext_artifact_review": _handle_alice_vnext_artifact_review,
    "alice_vnext_scheduler_status": _handle_alice_vnext_scheduler_status,
    "alice_vnext_scheduler_run_now": _handle_alice_vnext_scheduler_run_now,
    "alice_vnext_scheduler_run_due": _handle_alice_vnext_scheduler_run_due,
    "alice_vnext_scheduler_pause": _handle_alice_vnext_scheduler_pause,
    "alice_vnext_scheduler_resume": _handle_alice_vnext_scheduler_resume,
}


_CORE_TOOL_NAMES = frozenset(str(tool["name"]) for tool in _CORE_TOOL_DEFINITIONS)
_LEGACY_TOOL_NAMES = frozenset(str(tool["name"]) for tool in _LEGACY_TOOL_DEFINITIONS)


def _legacy_tools_enabled() -> bool:
    return os.environ.get(MCP_LEGACY_TOOLS_ENV, "").strip().casefold() in _LEGACY_ENABLED_VALUES


def _enabled_tool_definitions() -> list[dict[str, object]]:
    if _legacy_tools_enabled():
        return [*_CORE_TOOL_DEFINITIONS, *_LEGACY_TOOL_DEFINITIONS]
    return list(_CORE_TOOL_DEFINITIONS)


def list_mcp_tools() -> list[dict[str, object]]:
    return _canonicalize_json(_enabled_tool_definitions())  # type: ignore[return-value]


def call_mcp_tool(
    context: MCPRuntimeContext,
    *,
    name: str,
    arguments: object,
) -> JsonObject:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise MCPToolNotFoundError(f"unknown tool '{name}'")
    if name not in _CORE_TOOL_NAMES and not _legacy_tools_enabled():
        raise MCPToolNotFoundError(
            f"tool '{name}' is part of the legacy MCP surface and is currently disabled; "
            f"set {MCP_LEGACY_TOOLS_ENV}=1 in the MCP server environment to enable legacy tools"
        )

    parsed_arguments = _normalize_arguments(arguments)
    try:
        payload = handler(context, parsed_arguments)
    except (
        ContinuityCaptureValidationError,
        ContinuityRecallValidationError,
        ContinuityBriefValidationError,
        ContinuityResumptionValidationError,
        ContinuityReviewValidationError,
        ContinuityReviewNotFoundError,
        ContinuityContradictionValidationError,
        ContinuityContradictionNotFoundError,
        RetrievalTraceNotFoundError,
        ContinuityEvidenceNotFoundError,
        MemoryMutationValidationError,
        TaskBriefNotFoundError,
        TaskBriefValidationError,
        TemporalStateValidationError,
    ) as exc:
        raise MCPToolError(str(exc)) from exc
    except (CheckViolation, sqlite3.IntegrityError) as exc:
        raise MCPToolError(
            "vNext request violates a persisted schema constraint; use schema-backed enum values "
            "for memory_type, domain, sensitivity, status, and action fields."
        ) from exc
    except (TypeError, ValueError) as exc:
        raise MCPToolError(str(exc)) from exc

    return _canonicalize_json(payload)  # type: ignore[return-value]


__all__ = [
    "MCP_LEGACY_TOOLS_ENV",
    "MCPRuntimeContext",
    "MCPToolError",
    "MCPToolNotFoundError",
    "call_mcp_tool",
    "list_mcp_tools",
    "redact_memory_flow",
]
