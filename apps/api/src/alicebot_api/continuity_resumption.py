from __future__ import annotations

from uuid import UUID

from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.contracts import (
    CONTINUITY_RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0,
    CONTINUITY_RESUMPTION_OPEN_LOOP_ORDER,
    CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    ContinuityRecallQueryInput,
    ContinuityRecallResultRecord,
    ContinuityResumptionBriefRecord,
    ContinuityResumptionBriefRequestInput,
    ContinuityResumptionBriefResponse,
    ContinuityResumptionEmptyState,
    ContinuityResumptionListSection,
    ContinuityResumptionSingleSection,
    ResumptionBriefSectionSummary,
)
from alicebot_api.store import ContinuityStore


class ContinuityResumptionValidationError(ValueError):
    """Raised when a continuity resumption request is invalid."""


def _is_active_truth(item: ContinuityRecallResultRecord) -> bool:
    return item["status"] == "active"


def _is_recent_change_candidate(item: ContinuityRecallResultRecord) -> bool:
    return item["status"] in {"active", "stale", "superseded", "completed", "cancelled"}


def _is_promotable_fact(
    item: ContinuityRecallResultRecord,
    *,
    include_non_promotable_facts: bool,
) -> bool:
    if item["object_type"] != "MemoryFact":
        return True
    if include_non_promotable_facts:
        return True
    return item["lifecycle"]["is_promotable"]


def _build_empty_state(*, is_empty: bool, message: str) -> ContinuityResumptionEmptyState:
    return {
        "is_empty": is_empty,
        "message": message,
    }


def _build_single_section(
    item: ContinuityRecallResultRecord | None,
    *,
    empty_message: str,
) -> ContinuityResumptionSingleSection:
    return {
        "item": item,
        "empty_state": _build_empty_state(
            is_empty=item is None,
            message=empty_message,
        ),
    }


def _build_list_section(
    *,
    items: list[ContinuityRecallResultRecord],
    limit: int,
    total_count: int,
    order: list[str],
    empty_message: str,
) -> ContinuityResumptionListSection:
    summary: ResumptionBriefSectionSummary = {
        "limit": limit,
        "returned_count": len(items),
        "total_count": total_count,
        "order": list(order),
    }
    return {
        "items": items,
        "summary": summary,
        "empty_state": _build_empty_state(
            is_empty=len(items) == 0,
            message=empty_message,
        ),
    }


def _validate_request(request: ContinuityResumptionBriefRequestInput) -> None:
    if request.max_recent_changes < 0 or request.max_recent_changes > MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT:
        raise ContinuityResumptionValidationError(
            "max_recent_changes must be between "
            f"0 and {MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT}"
        )

    if request.max_open_loops < 0 or request.max_open_loops > MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT:
        raise ContinuityResumptionValidationError(
            f"max_open_loops must be between 0 and {MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT}"
        )

    if request.since is not None and request.until is not None and request.until < request.since:
        raise ContinuityResumptionValidationError("until must be greater than or equal to since")


def _recency_sort_key(item: ContinuityRecallResultRecord) -> tuple[str, str]:
    return (item["created_at"], item["id"])


def compile_continuity_resumption_brief(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContinuityResumptionBriefRequestInput,
) -> ContinuityResumptionBriefResponse:
    _validate_request(request)

    recall_payload = query_continuity_recall(
        store,
        user_id=user_id,
        request=ContinuityRecallQueryInput(
            query=request.query,
            thread_id=request.thread_id,
            task_id=request.task_id,
            project=request.project,
            person=request.person,
            since=request.since,
            until=request.until,
            limit=MAX_CONTINUITY_RECALL_LIMIT,
        ),
        apply_limit=False,
    )

    ranked_items = list(recall_payload["items"])
    recent_ordered_items = sorted(
        ranked_items,
        key=_recency_sort_key,
        reverse=True,
    )

    latest_decision = next(
        (
            item
            for item in recent_ordered_items
            if item["object_type"] == "Decision" and _is_active_truth(item)
        ),
        None,
    )
    latest_next_action = next(
        (
            item
            for item in recent_ordered_items
            if item["object_type"] == "NextAction" and _is_active_truth(item)
        ),
        None,
    )

    open_loop_candidates = [
        item
        for item in recent_ordered_items
        if _is_active_truth(item)
        and item["object_type"] in {"Commitment", "WaitingFor", "Blocker"}
    ]
    open_loop_items = (
        open_loop_candidates[: request.max_open_loops]
        if request.max_open_loops > 0
        else []
    )

    recent_change_candidates = [
        item
        for item in recent_ordered_items
        if _is_recent_change_candidate(item)
        and _is_promotable_fact(
            item,
            include_non_promotable_facts=request.include_non_promotable_facts,
        )
    ]
    recent_change_items = (
        recent_change_candidates[: request.max_recent_changes]
        if request.max_recent_changes > 0
        else []
    )

    brief: ContinuityResumptionBriefRecord = {
        "assembly_version": CONTINUITY_RESUMPTION_BRIEF_ASSEMBLY_VERSION_V0,
        "scope": recall_payload["summary"]["filters"],
        "last_decision": _build_single_section(
            latest_decision,
            empty_message="No decision found in the requested scope.",
        ),
        "open_loops": _build_list_section(
            items=open_loop_items,
            limit=request.max_open_loops,
            total_count=len(open_loop_candidates),
            order=list(CONTINUITY_RESUMPTION_OPEN_LOOP_ORDER),
            empty_message="No open loops found in the requested scope.",
        ),
        "recent_changes": _build_list_section(
            items=recent_change_items,
            limit=request.max_recent_changes,
            total_count=len(recent_change_candidates),
            order=list(CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER),
            empty_message="No recent changes found in the requested scope.",
        ),
        "next_action": _build_single_section(
            latest_next_action,
            empty_message="No next action found in the requested scope.",
        ),
        "sources": ["continuity_capture_events", "continuity_objects"],
    }

    return {"brief": brief}


def build_default_resumption_request() -> ContinuityResumptionBriefRequestInput:
    return ContinuityResumptionBriefRequestInput(
        max_recent_changes=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        max_open_loops=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    )
