from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from alicebot_api.continuity_open_loops import compile_continuity_open_loop_dashboard
from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import (
    CHIEF_OF_STAFF_PRIORITY_BRIEF_ASSEMBLY_VERSION_V0,
    CHIEF_OF_STAFF_PRIORITY_ITEM_ORDER,
    CHIEF_OF_STAFF_PRIORITY_POSTURE_ORDER,
    CHIEF_OF_STAFF_RECOMMENDED_ACTION_TYPES,
    CONTINUITY_OPEN_LOOP_POSTURE_ORDER,
    DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    ChiefOfStaffPriorityBriefRecord,
    ChiefOfStaffPriorityBriefRequestInput,
    ChiefOfStaffPriorityBriefResponse,
    ChiefOfStaffPriorityItem,
    ChiefOfStaffPriorityPosture,
    ChiefOfStaffRecommendationConfidencePosture,
    ChiefOfStaffRecommendedActionType,
    ChiefOfStaffRecommendedNextAction,
    ChiefOfStaffPrioritySummary,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityOpenLoopPosture,
    ContinuityRecallQueryInput,
    ContinuityRecallResultRecord,
    ContinuityResumptionBriefRequestInput,
    MemoryQualityGateStatus,
)
from alicebot_api.memory import get_memory_trust_dashboard_summary
from alicebot_api.store import ContinuityStore


class ChiefOfStaffValidationError(ValueError):
    """Raised when a chief-of-staff request is invalid."""


@dataclass(frozen=True, slots=True)
class _TrustConfidenceCap:
    posture: ChiefOfStaffRecommendationConfidencePosture
    reason: str


_ACTIONABLE_OBJECT_TYPES = {"Commitment", "WaitingFor", "Blocker", "NextAction"}
_CONFIDENCE_ORDER: dict[ChiefOfStaffRecommendationConfidencePosture, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
}
_POSTURE_WEIGHT: dict[ChiefOfStaffPriorityPosture, float] = {
    "urgent": 600.0,
    "important": 500.0,
    "waiting": 400.0,
    "blocked": 300.0,
    "stale": 200.0,
    "defer": 100.0,
}


def _is_offset_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    if not normalized:
        return None
    return normalized


def _validate_request(request: ChiefOfStaffPriorityBriefRequestInput) -> None:
    if request.limit < 0 or request.limit > MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT:
        raise ChiefOfStaffValidationError(
            f"limit must be between 0 and {MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT}"
        )

    if request.since is None or request.until is None:
        return

    if _is_offset_aware(request.since) != _is_offset_aware(request.until):
        raise ChiefOfStaffValidationError(
            "since and until must both include timezone offsets or both omit timezone offsets"
        )

    try:
        if request.until < request.since:
            raise ChiefOfStaffValidationError("until must be greater than or equal to since")
    except TypeError as exc:
        raise ChiefOfStaffValidationError(
            "since and until must both include timezone offsets or both omit timezone offsets"
        ) from exc


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _age_hours_relative_to_latest(*, latest_created_at: datetime, item_created_at: datetime) -> float:
    age_seconds = (latest_created_at - item_created_at).total_seconds()
    return round(max(0.0, age_seconds) / 3600.0, 6)


def _build_open_loop_posture_map(
    dashboard: dict[str, object],
) -> dict[str, ContinuityOpenLoopPosture]:
    posture_by_id: dict[str, ContinuityOpenLoopPosture] = {}
    for posture in CONTINUITY_OPEN_LOOP_POSTURE_ORDER:
        section = dashboard[posture]
        if not isinstance(section, dict):
            continue
        raw_items = section.get("items")
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if isinstance(item, dict):
                item_id = item.get("id")
                if isinstance(item_id, str):
                    posture_by_id[item_id] = posture
    return posture_by_id


def _trust_confidence_cap(
    *,
    quality_gate_status: MemoryQualityGateStatus,
    retrieval_status: str,
) -> _TrustConfidenceCap:
    if quality_gate_status == "healthy":
        posture: ChiefOfStaffRecommendationConfidencePosture = "high"
        reason = "Memory quality gate is healthy, so recommendation confidence can remain high."
    elif quality_gate_status == "needs_review":
        posture = "medium"
        reason = "Memory quality gate needs review, so recommendation confidence is capped at medium."
    else:
        posture = "low"
        reason = (
            "Memory quality gate is weak (insufficient sample or degraded), "
            "so recommendation confidence is capped at low."
        )

    if retrieval_status == "fail" and posture == "high":
        posture = "medium"
        reason = (
            "Memory quality gate is healthy but retrieval quality is failing; "
            "recommendation confidence is capped at medium."
        )

    return _TrustConfidenceCap(posture=posture, reason=reason)


def _confidence_posture_from_score(score: float) -> ChiefOfStaffRecommendationConfidencePosture:
    if score >= 0.8:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _clamp_confidence_posture(
    base: ChiefOfStaffRecommendationConfidencePosture,
    cap: ChiefOfStaffRecommendationConfidencePosture,
) -> ChiefOfStaffRecommendationConfidencePosture:
    if _CONFIDENCE_ORDER[base] <= _CONFIDENCE_ORDER[cap]:
        return base
    return cap


def _derive_priority_posture(
    *,
    item: ContinuityRecallResultRecord,
    open_loop_posture: ContinuityOpenLoopPosture | None,
    is_resumption_next_action: bool,
    recent_change_index: int | None,
) -> ChiefOfStaffPriorityPosture:
    lifecycle_status = item["status"]

    if lifecycle_status in {"completed", "cancelled", "superseded"}:
        return "defer"

    if lifecycle_status == "stale" or open_loop_posture == "stale":
        return "stale"

    if open_loop_posture == "waiting_for" or item["object_type"] == "WaitingFor":
        return "waiting"

    if open_loop_posture == "blocker" or item["object_type"] == "Blocker":
        return "blocked"

    if is_resumption_next_action:
        return "urgent"

    if item["object_type"] == "NextAction" and recent_change_index is not None and recent_change_index == 0:
        return "urgent"

    if item["object_type"] == "Commitment" and recent_change_index is not None and recent_change_index <= 1:
        return "urgent"

    return "important"


def _confidence_score(item: ContinuityRecallResultRecord) -> float:
    score = float(item["confidence"])
    if item["confirmation_status"] == "confirmed":
        score += 0.1

    provenance_posture = item["ordering"]["provenance_posture"]
    if provenance_posture == "strong":
        score += 0.1
    elif provenance_posture == "partial":
        score += 0.05

    freshness_posture = item["ordering"]["freshness_posture"]
    if freshness_posture == "stale":
        score -= 0.1
    elif freshness_posture == "superseded":
        score -= 0.2

    return min(1.0, max(0.0, score))


def _ranking_score(
    *,
    item: ContinuityRecallResultRecord,
    posture: ChiefOfStaffPriorityPosture,
    age_hours: float,
    is_resumption_next_action: bool,
    recent_change_index: int | None,
) -> float:
    score = _POSTURE_WEIGHT[posture]
    score += float(item["relevance"]) * 0.2
    score += float(item["ordering"]["scope_match_count"]) * 3.0
    score += float(item["ordering"]["query_term_match_count"]) * 2.0
    score += float(item["ordering"]["confidence"])

    if recent_change_index is not None:
        score += max(0.0, 20.0 - float(recent_change_index))

    if is_resumption_next_action:
        score += 25.0

    if posture in {"waiting", "blocked", "stale"}:
        score += min(age_hours, 336.0) * 0.25

    return round(score, 6)


def _posture_reason(posture: ChiefOfStaffPriorityPosture) -> str:
    if posture == "urgent":
        return "Marked urgent because this item is a deterministic immediate focus from resumption signals."
    if posture == "important":
        return "Marked important because this is active work with strong continuity relevance."
    if posture == "waiting":
        return "Marked waiting because this item is in waiting-for posture and requires follow-through tracking."
    if posture == "blocked":
        return "Marked blocked because this item has blocker posture and requires unblock action."
    if posture == "stale":
        return "Marked stale because freshness posture indicates this item is slipping."
    return "Marked defer because lifecycle posture indicates it is not current active focus."


def _build_recommended_action(
    *,
    ranked_items: list[ChiefOfStaffPriorityItem],
    trust_cap: ChiefOfStaffRecommendationConfidencePosture,
) -> ChiefOfStaffRecommendedNextAction:
    target = next((item for item in ranked_items if item["priority_posture"] != "defer"), None)

    if target is None:
        return {
            "action_type": "capture_new_priority",
            "title": "Capture one concrete next action",
            "target_priority_id": None,
            "priority_posture": None,
            "confidence_posture": trust_cap,
            "reason": "No active priority items are present, so capture one concrete next action to restore focus.",
            "provenance_references": [],
            "deterministic_rank_key": "none",
        }

    posture = target["priority_posture"]
    action_type: ChiefOfStaffRecommendedActionType
    if posture == "blocked":
        action_type = "unblock_blocker"
    elif posture == "waiting":
        action_type = "follow_up_waiting_for"
    elif posture == "stale":
        action_type = "refresh_stale_item"
    elif posture == "defer":
        action_type = "review_and_defer"
    elif target["object_type"] == "Commitment":
        action_type = "progress_commitment"
    else:
        action_type = "execute_next_action"

    if action_type not in CHIEF_OF_STAFF_RECOMMENDED_ACTION_TYPES:
        action_type = "review_and_defer"

    rationale_reasons = target["rationale"]["reasons"]
    reason = rationale_reasons[0] if rationale_reasons else "Ranked highest by deterministic priority score."

    return {
        "action_type": action_type,
        "title": target["title"],
        "target_priority_id": target["id"],
        "priority_posture": posture,
        "confidence_posture": target["confidence_posture"],
        "reason": reason,
        "provenance_references": target["rationale"]["provenance_references"],
        "deterministic_rank_key": f"{target['rank']}:{target['id']}:{target['score']:.6f}",
    }


def compile_chief_of_staff_priority_brief(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ChiefOfStaffPriorityBriefRequestInput,
) -> ChiefOfStaffPriorityBriefResponse:
    normalized_request = ChiefOfStaffPriorityBriefRequestInput(
        query=_normalize_optional_text(request.query),
        thread_id=request.thread_id,
        task_id=request.task_id,
        project=_normalize_optional_text(request.project),
        person=_normalize_optional_text(request.person),
        since=request.since,
        until=request.until,
        limit=request.limit,
    )
    _validate_request(normalized_request)

    recall_payload = query_continuity_recall(
        store,
        user_id=user_id,
        request=ContinuityRecallQueryInput(
            query=normalized_request.query,
            thread_id=normalized_request.thread_id,
            task_id=normalized_request.task_id,
            project=normalized_request.project,
            person=normalized_request.person,
            since=normalized_request.since,
            until=normalized_request.until,
            limit=MAX_CONTINUITY_RECALL_LIMIT,
        ),
        apply_limit=False,
    )

    open_loop_dashboard = compile_continuity_open_loop_dashboard(
        store,
        user_id=user_id,
        request=ContinuityOpenLoopDashboardQueryInput(
            query=normalized_request.query,
            thread_id=normalized_request.thread_id,
            task_id=normalized_request.task_id,
            project=normalized_request.project,
            person=normalized_request.person,
            since=normalized_request.since,
            until=normalized_request.until,
            limit=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
        ),
    )["dashboard"]

    resumption_brief = compile_continuity_resumption_brief(
        store,
        user_id=user_id,
        request=ContinuityResumptionBriefRequestInput(
            query=normalized_request.query,
            thread_id=normalized_request.thread_id,
            task_id=normalized_request.task_id,
            project=normalized_request.project,
            person=normalized_request.person,
            since=normalized_request.since,
            until=normalized_request.until,
            max_recent_changes=MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
            max_open_loops=MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        ),
    )["brief"]

    trust_dashboard = get_memory_trust_dashboard_summary(
        store,
        user_id=user_id,
    )["dashboard"]

    quality_gate_status = trust_dashboard["quality_gate"]["status"]
    retrieval_status = trust_dashboard["retrieval_quality"]["status"]
    trust_cap = _trust_confidence_cap(
        quality_gate_status=quality_gate_status,
        retrieval_status=retrieval_status,
    )

    open_loop_posture_by_id = _build_open_loop_posture_map(open_loop_dashboard)
    recent_change_index_by_id: dict[str, int] = {
        item["id"]: index
        for index, item in enumerate(resumption_brief["recent_changes"]["items"])
    }
    resumption_next_action_item = resumption_brief["next_action"]["item"]
    resumption_next_action_id = (
        None
        if resumption_next_action_item is None
        else resumption_next_action_item["id"]
    )

    candidate_items = [
        item
        for item in recall_payload["items"]
        if item["object_type"] in _ACTIONABLE_OBJECT_TYPES
    ]

    created_at_values = [_parse_timestamp(item["created_at"]) for item in candidate_items]
    latest_created_at = max(created_at_values) if created_at_values else None

    scored_items: list[tuple[float, datetime, ChiefOfStaffPriorityItem]] = []

    for item in candidate_items:
        item_id = item["id"]
        item_created_at = _parse_timestamp(item["created_at"])
        age_hours = (
            0.0
            if latest_created_at is None
            else _age_hours_relative_to_latest(
                latest_created_at=latest_created_at,
                item_created_at=item_created_at,
            )
        )
        open_loop_posture = open_loop_posture_by_id.get(item_id)
        recent_change_index = recent_change_index_by_id.get(item_id)
        is_resumption_next_action = item_id == resumption_next_action_id

        posture = _derive_priority_posture(
            item=item,
            open_loop_posture=open_loop_posture,
            is_resumption_next_action=is_resumption_next_action,
            recent_change_index=recent_change_index,
        )

        score = _ranking_score(
            item=item,
            posture=posture,
            age_hours=age_hours,
            is_resumption_next_action=is_resumption_next_action,
            recent_change_index=recent_change_index,
        )

        base_confidence_score = _confidence_score(item)
        base_confidence_posture = _confidence_posture_from_score(base_confidence_score)
        confidence_posture = _clamp_confidence_posture(
            base_confidence_posture,
            trust_cap.posture,
        )
        downgraded_by_trust = confidence_posture != base_confidence_posture

        reasons = [_posture_reason(posture)]
        if recent_change_index is not None:
            reasons.append(
                f"Appears in recent continuity changes at rank {recent_change_index + 1}."
            )
        if posture in {"waiting", "blocked", "stale"} and age_hours > 0:
            reasons.append(
                f"Aging evidence: {age_hours:.1f}h older than the newest scoped priority candidate."
            )
        if downgraded_by_trust:
            reasons.append("Confidence is explicitly downgraded by current memory trust posture.")
        reasons.append("Provenance references are attached from continuity recall evidence.")

        scored_items.append(
            (
                score,
                item_created_at,
                {
                    "rank": 0,
                    "id": item_id,
                    "capture_event_id": item["capture_event_id"],
                    "object_type": item["object_type"],
                    "status": item["status"],
                    "title": item["title"],
                    "priority_posture": posture,
                    "confidence_posture": confidence_posture,
                    "confidence": round(float(item["confidence"]), 6),
                    "score": score,
                    "provenance": item["provenance"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                    "rationale": {
                        "reasons": reasons,
                        "ranking_inputs": {
                            "posture": posture,
                            "open_loop_posture": open_loop_posture,
                            "recency_rank": None if recent_change_index is None else recent_change_index + 1,
                            "age_hours_relative_to_latest": age_hours,
                            "recall_relevance": round(float(item["relevance"]), 6),
                            "scope_match_count": item["ordering"]["scope_match_count"],
                            "query_term_match_count": item["ordering"]["query_term_match_count"],
                            "freshness_posture": item["ordering"]["freshness_posture"],
                            "provenance_posture": item["ordering"]["provenance_posture"],
                            "supersession_posture": item["ordering"]["supersession_posture"],
                        },
                        "provenance_references": item["provenance_references"],
                        "trust_signals": {
                            "quality_gate_status": quality_gate_status,
                            "retrieval_status": retrieval_status,
                            "trust_confidence_cap": trust_cap.posture,
                            "downgraded_by_trust": downgraded_by_trust,
                            "reason": trust_cap.reason,
                        },
                    },
                },
            )
        )

    scored_items.sort(
        key=lambda entry: (entry[0], entry[1], entry[2]["id"]),
        reverse=True,
    )

    total_count = len(scored_items)
    limit = normalized_request.limit
    selected_items = scored_items[:limit] if limit > 0 else []

    ranked_items: list[ChiefOfStaffPriorityItem] = []
    for rank, (_, _, item) in enumerate(selected_items, start=1):
        ranked_item = dict(item)
        ranked_item["rank"] = rank
        ranked_items.append(ranked_item)  # type: ignore[arg-type]

    recommended_next_action = _build_recommended_action(
        ranked_items=ranked_items,
        trust_cap=trust_cap.posture,
    )

    summary: ChiefOfStaffPrioritySummary = {
        "limit": limit,
        "returned_count": len(ranked_items),
        "total_count": total_count,
        "posture_order": list(CHIEF_OF_STAFF_PRIORITY_POSTURE_ORDER),
        "order": list(CHIEF_OF_STAFF_PRIORITY_ITEM_ORDER),
        "trust_confidence_posture": trust_cap.posture,
        "trust_confidence_reason": trust_cap.reason,
        "quality_gate_status": quality_gate_status,
        "retrieval_status": retrieval_status,
    }

    brief: ChiefOfStaffPriorityBriefRecord = {
        "assembly_version": CHIEF_OF_STAFF_PRIORITY_BRIEF_ASSEMBLY_VERSION_V0,
        "scope": recall_payload["summary"]["filters"],
        "ranked_items": ranked_items,
        "recommended_next_action": recommended_next_action,
        "summary": summary,
        "sources": [
            "continuity_recall",
            "continuity_open_loops",
            "continuity_resumption_brief",
            "memory_trust_dashboard",
            "memories",
            "memory_review_labels",
        ],
    }

    return {"brief": brief}


def build_default_chief_of_staff_priority_request() -> ChiefOfStaffPriorityBriefRequestInput:
    return ChiefOfStaffPriorityBriefRequestInput(limit=DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT)
