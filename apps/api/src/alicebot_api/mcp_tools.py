from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from alicebot_api.continuity_capture import (
    ContinuityCaptureValidationError,
    capture_continuity_candidates,
    capture_continuity_input,
    commit_continuity_captures,
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
from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopValidationError,
    compile_continuity_open_loop_dashboard,
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
    CONTINUITY_CAPTURE_EXPLICIT_SIGNALS,
    CONTINUITY_CORRECTION_ACTIONS,
    CONTRADICTION_RESOLUTION_ACTIONS,
    CONTINUITY_REVIEW_QUEUE_ORDER,
    CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER,
    DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_CONTINUITY_REVIEW_LIMIT,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    ContinuityCaptureCandidatesInput,
    ContinuityCaptureCommitInput,
    ContinuityCaptureCreateInput,
    ContradictionCaseListQueryInput,
    ContradictionResolveInput,
    ContradictionSyncInput,
    ContinuityCorrectionInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    ContinuityReviewQueueQueryInput,
    MemoryOperationCommitInput,
    MemoryOperationGenerateInput,
    MemoryOperationListInput,
    TemporalExplainQueryInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
    TrustSignalListQueryInput,
)
from alicebot_api.config import get_settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore, JsonObject
from alicebot_api.temporal_state import (
    TemporalStateValidationError,
    get_temporal_explain,
    get_temporal_state_at,
    get_temporal_timeline,
)


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
_CONTEXT_PACK_ASSEMBLY_VERSION_V0 = "alice_context_pack_v0"
_PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0 = "alice_prefetch_context_v0"


class MCPToolError(ValueError):
    """Raised when MCP tool input or execution fails."""


class MCPToolNotFoundError(LookupError):
    """Raised when an MCP tool name is not supported."""


@dataclass(frozen=True, slots=True)
class MCPRuntimeContext:
    database_url: str
    user_id: UUID


@contextmanager
def _store_context(context: MCPRuntimeContext):
    with user_connection(context.database_url, context.user_id) as conn:
        yield ContinuityStore(conn)


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
    allowed = list(_REVIEW_APPLY_ACTION_CHOICES)
    if allow_legacy:
        allowed.extend(CONTINUITY_CORRECTION_ACTIONS)
    raise MCPToolError(f"action must be one of: {', '.join(allowed)}")


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


def _handle_alice_capture(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    explicit_signal = arguments.get("explicit_signal")
    if explicit_signal is not None and not isinstance(explicit_signal, str):
        raise MCPToolError("explicit_signal must be a string when provided")

    with _store_context(context) as store:
        return capture_continuity_input(
            store,
            user_id=context.user_id,
            request=ContinuityCaptureCreateInput(
                raw_content=_parse_required_text(arguments, "raw_content"),
                explicit_signal=explicit_signal,
            ),
        )


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


def _handle_alice_recall(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
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
            request=_build_recall_query(arguments, limit=limit),
        )


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
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    )

    with _store_context(context) as store:
        return compile_continuity_open_loop_dashboard(
            store,
            user_id=context.user_id,
            request=ContinuityOpenLoopDashboardQueryInput(
                query=_parse_optional_text(arguments, "query"),
                thread_id=_parse_optional_uuid(arguments, "thread_id"),
                task_id=_parse_optional_uuid(arguments, "task_id"),
                project=_parse_optional_text(arguments, "project"),
                person=_parse_optional_text(arguments, "person"),
                since=_parse_optional_datetime(arguments, "since"),
                until=_parse_optional_datetime(arguments, "until"),
                limit=limit,
            ),
        )


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
    return _recent_decisions_payload(context, arguments=arguments, limit=limit)


def _handle_alice_recent_changes(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    max_recent_changes = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
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
    continuity_object_id = _parse_optional_uuid(arguments, "continuity_object_id")
    entity_id = _parse_optional_uuid(arguments, "entity_id")
    if continuity_object_id is not None and entity_id is not None:
        raise MCPToolError("alice_explain accepts either continuity_object_id or entity_id, not both")
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
        raise MCPToolError("alice_explain requires continuity_object_id or entity_id")

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


def _handle_alice_context_pack(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    open_loops_limit = _parse_int(
        arguments,
        key="open_loops_limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )
    recent_changes_limit = _parse_int(
        arguments,
        key="recent_changes_limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=0,
        maximum=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    )
    recent_decisions_limit = _parse_int(
        arguments,
        key="recent_decisions_limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
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
                max_recent_changes=recent_changes_limit,
                max_open_loops=open_loops_limit,
            ),
        )

    brief = resumption_payload["brief"]
    recent_decisions = _recent_decisions_payload(
        context,
        arguments=arguments,
        limit=recent_decisions_limit,
    )
    return {
        "context_pack": {
            "assembly_version": _CONTEXT_PACK_ASSEMBLY_VERSION_V0,
            "scope": brief["scope"],
            "last_decision": brief["last_decision"],
            "next_action": brief["next_action"],
            "open_loops": brief["open_loops"],
            "recent_changes": brief["recent_changes"],
            "recent_decisions": recent_decisions,
            "sources": [
                "continuity_capture_events",
                "continuity_objects",
                "continuity_correction_events",
            ],
        }
    }


_TOOL_DEFINITIONS: list[dict[str, object]] = [
    {
        "name": "alice_capture",
        "description": "Capture continuity input into deterministic continuity objects.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["raw_content"],
            "properties": {
                "raw_content": {"type": "string"},
                "explicit_signal": {"type": "string", "enum": list(CONTINUITY_CAPTURE_EXPLICIT_SIGNALS)},
            },
        },
    },
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
        "name": "alice_recall",
        "description": "Recall continuity objects with deterministic ranking and provenance fields.",
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
        "name": "alice_resume",
        "description": "Compile continuity resumption brief for decisions, open loops, and next action.",
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
        "name": "alice_open_loops",
        "description": "List continuity open loops grouped by deterministic posture sections.",
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
                "limit": {"type": "integer", "minimum": 0, "maximum": MAX_CONTINUITY_OPEN_LOOP_LIMIT},
            },
        },
    },
    {
        "name": "alice_recent_decisions",
        "description": "List most recent continuity decisions in deterministic recency order.",
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
        "name": "alice_memory_review",
        "description": "Legacy alias for review queue/detail (use alice_review_queue).",
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
        "name": "alice_memory_correct",
        "description": "Legacy alias for review apply (use alice_review_apply).",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["continuity_object_id", "action"],
            "properties": {
                "review_item_id": {"type": "string", "format": "uuid"},
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "action": {"type": "string", "enum": list(CONTINUITY_CORRECTION_ACTIONS)},
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
        "name": "alice_explain",
        "description": "Show continuity evidence for one continuity object or temporal explain output for one entity.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "continuity_object_id": {"type": "string", "format": "uuid"},
                "entity_id": {"type": "string", "format": "uuid"},
                "at": {"type": "string", "format": "date-time"},
                "include_raw_content": {"type": "boolean"},
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
        "name": "alice_context_pack",
        "description": "Assemble a deterministic continuity context pack for scoped external-agent use.",
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
                "recent_decisions_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_CONTINUITY_RECALL_LIMIT,
                },
                "recent_changes_limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                },
                "open_loops_limit": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                },
            },
        },
    },
]

_TOOL_HANDLERS = {
    "alice_capture": _handle_alice_capture,
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
}


def list_mcp_tools() -> list[dict[str, object]]:
    return _canonicalize_json(_TOOL_DEFINITIONS)  # type: ignore[return-value]


def call_mcp_tool(
    context: MCPRuntimeContext,
    *,
    name: str,
    arguments: object,
) -> JsonObject:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise MCPToolNotFoundError(f"unknown tool '{name}'")

    parsed_arguments = _normalize_arguments(arguments)
    try:
        payload = handler(context, parsed_arguments)
    except (
        ContinuityCaptureValidationError,
        ContinuityRecallValidationError,
        ContinuityResumptionValidationError,
        ContinuityOpenLoopValidationError,
        ContinuityReviewValidationError,
        ContinuityReviewNotFoundError,
        ContinuityContradictionValidationError,
        ContinuityContradictionNotFoundError,
        RetrievalTraceNotFoundError,
        ContinuityEvidenceNotFoundError,
        MemoryMutationValidationError,
        TemporalStateValidationError,
    ) as exc:
        raise MCPToolError(str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise MCPToolError(str(exc)) from exc

    return _canonicalize_json(payload)  # type: ignore[return-value]


__all__ = [
    "MCPRuntimeContext",
    "MCPToolError",
    "MCPToolNotFoundError",
    "call_mcp_tool",
    "list_mcp_tools",
]
