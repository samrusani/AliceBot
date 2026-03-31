from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from alicebot_api.continuity_open_loops import compile_continuity_open_loop_dashboard
from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import (
    CHIEF_OF_STAFF_ESCALATION_POSTURE_ORDER,
    CHIEF_OF_STAFF_FOLLOW_THROUGH_ITEM_ORDER,
    CHIEF_OF_STAFF_FOLLOW_THROUGH_POSTURE_ORDER,
    CHIEF_OF_STAFF_FOLLOW_THROUGH_RECOMMENDATION_ACTIONS,
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
    ChiefOfStaffDraftFollowUpRecord,
    ChiefOfStaffEscalationPosture,
    ChiefOfStaffEscalationPostureRecord,
    ChiefOfStaffFollowThroughItem,
    ChiefOfStaffFollowThroughPosture,
    ChiefOfStaffFollowThroughRecommendationAction,
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
_FOLLOW_THROUGH_OVERDUE_HOURS = 24.0
_FOLLOW_THROUGH_STALE_WAITING_FOR_HOURS = 72.0
_FOLLOW_THROUGH_SLIPPED_COMMITMENT_HOURS = 48.0
_FOLLOW_THROUGH_CLOSE_LOOP_HOURS = 168.0
_FOLLOW_THROUGH_NUDGE_HOURS = 48.0
_FOLLOW_THROUGH_ESCALATE_HOURS = 120.0
_FOLLOW_THROUGH_ACTION_WEIGHT: dict[ChiefOfStaffFollowThroughRecommendationAction, int] = {
    "defer": 1,
    "close_loop_candidate": 2,
    "nudge": 3,
    "escalate": 4,
}
_FOLLOW_THROUGH_POSTURE_WEIGHT: dict[ChiefOfStaffFollowThroughPosture, int] = {
    "slipped_commitment": 1,
    "stale_waiting_for": 2,
    "overdue": 3,
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


def _follow_through_action_for_age(
    *,
    age_hours: float,
    close_loop_floor: float = _FOLLOW_THROUGH_CLOSE_LOOP_HOURS,
    escalate_floor: float = _FOLLOW_THROUGH_ESCALATE_HOURS,
    nudge_floor: float = _FOLLOW_THROUGH_NUDGE_HOURS,
    prioritize_escalation: bool = False,
) -> ChiefOfStaffFollowThroughRecommendationAction:
    if prioritize_escalation and age_hours >= escalate_floor:
        return "escalate"
    if age_hours >= close_loop_floor:
        return "close_loop_candidate"
    if age_hours >= escalate_floor:
        return "escalate"
    if age_hours >= nudge_floor:
        return "nudge"
    return "defer"


def _classify_follow_through_item(
    *,
    item: ContinuityRecallResultRecord,
    open_loop_posture: ContinuityOpenLoopPosture | None,
    age_hours: float,
    priority_posture: ChiefOfStaffPriorityPosture,
) -> tuple[
    ChiefOfStaffFollowThroughPosture | None,
    ChiefOfStaffFollowThroughRecommendationAction | None,
    str | None,
]:
    status = item["status"]
    object_type = item["object_type"]

    if status in {"completed", "cancelled", "superseded"}:
        return None, None, None

    if object_type == "Commitment":
        if status == "stale" or age_hours >= _FOLLOW_THROUGH_SLIPPED_COMMITMENT_HOURS:
            action = _follow_through_action_for_age(age_hours=age_hours)
            if status == "stale" and action == "defer":
                action = "nudge"
            reason = (
                f"Commitment is slipping (status={status}, age={age_hours:.1f}h from latest scoped item), "
                f"so action '{action}' is recommended."
            )
            return "slipped_commitment", action, reason
        return None, None, None

    if object_type == "WaitingFor":
        if status == "stale" or open_loop_posture == "stale" or age_hours >= _FOLLOW_THROUGH_STALE_WAITING_FOR_HOURS:
            action = _follow_through_action_for_age(age_hours=age_hours)
            if status == "stale" and action == "defer":
                action = "nudge"
            reason = (
                f"Waiting-for item is stale (status={status}, age={age_hours:.1f}h from latest scoped item), "
                f"so action '{action}' is recommended."
            )
            return "stale_waiting_for", action, reason

        if age_hours >= _FOLLOW_THROUGH_OVERDUE_HOURS:
            action = _follow_through_action_for_age(
                age_hours=age_hours,
                prioritize_escalation=True,
            )
            reason = (
                f"Waiting-for follow-up is overdue ({age_hours:.1f}h from latest scoped item), "
                f"so action '{action}' is recommended."
            )
            return "overdue", action, reason
        return None, None, None

    if object_type in {"NextAction", "Blocker"}:
        overdue_from_age = age_hours >= _FOLLOW_THROUGH_OVERDUE_HOURS
        overdue_from_priority = priority_posture in {"waiting", "blocked"} and age_hours >= _FOLLOW_THROUGH_NUDGE_HOURS
        if overdue_from_age or overdue_from_priority:
            action = _follow_through_action_for_age(
                age_hours=age_hours,
                prioritize_escalation=True,
            )
            if priority_posture == "blocked" and action in {"defer", "nudge", "close_loop_candidate"}:
                action = "escalate"
            reason = (
                f"Execution follow-through is overdue (posture={priority_posture}, age={age_hours:.1f}h), "
                f"so action '{action}' is recommended."
            )
            return "overdue", action, reason
        return None, None, None

    return None, None, None


def _follow_through_sort_key(
    item: ChiefOfStaffFollowThroughItem,
) -> tuple[int, float, str, str]:
    return (
        _FOLLOW_THROUGH_ACTION_WEIGHT[item["recommendation_action"]],
        item["age_hours"],
        item["created_at"],
        item["id"],
    )


def _rank_follow_through_items(
    items: list[ChiefOfStaffFollowThroughItem],
    *,
    limit: int,
) -> list[ChiefOfStaffFollowThroughItem]:
    if limit <= 0:
        return []

    sorted_items = sorted(
        items,
        key=_follow_through_sort_key,
        reverse=True,
    )
    ranked: list[ChiefOfStaffFollowThroughItem] = []
    for rank, item in enumerate(sorted_items[:limit], start=1):
        ranked_item = dict(item)
        ranked_item["rank"] = rank
        ranked.append(ranked_item)  # type: ignore[arg-type]
    return ranked


def _build_escalation_posture(
    *,
    all_follow_through_items: list[ChiefOfStaffFollowThroughItem],
) -> ChiefOfStaffEscalationPostureRecord:
    action_counts: dict[ChiefOfStaffFollowThroughRecommendationAction, int] = {
        "nudge": 0,
        "defer": 0,
        "escalate": 0,
        "close_loop_candidate": 0,
    }
    for item in all_follow_through_items:
        action_counts[item["recommendation_action"]] += 1

    posture: ChiefOfStaffEscalationPosture
    reason: str
    if action_counts["escalate"] > 0:
        posture = "critical"
        reason = "At least one follow-through item requires escalation."
    elif action_counts["nudge"] > 0:
        posture = "elevated"
        reason = "Follow-through items require nudges but no immediate escalations."
    elif action_counts["close_loop_candidate"] > 0:
        posture = "watch"
        reason = "Only close-loop candidates are present; keep watch posture and confirm closure."
    else:
        posture = "watch"
        reason = "No active follow-through escalations are present."

    if posture not in CHIEF_OF_STAFF_ESCALATION_POSTURE_ORDER:
        posture = "watch"

    return {
        "posture": posture,
        "reason": reason,
        "total_follow_through_count": len(all_follow_through_items),
        "nudge_count": action_counts["nudge"],
        "defer_count": action_counts["defer"],
        "escalate_count": action_counts["escalate"],
        "close_loop_candidate_count": action_counts["close_loop_candidate"],
    }


def _draft_follow_up_sort_key(
    item: ChiefOfStaffFollowThroughItem,
) -> tuple[int, int, float, str, str]:
    return (
        _FOLLOW_THROUGH_ACTION_WEIGHT[item["recommendation_action"]],
        _FOLLOW_THROUGH_POSTURE_WEIGHT[item["follow_through_posture"]],
        item["age_hours"],
        item["created_at"],
        item["id"],
    )


def _build_draft_follow_up(
    *,
    all_follow_through_items: list[ChiefOfStaffFollowThroughItem],
    thread_hint: str | None,
) -> ChiefOfStaffDraftFollowUpRecord:
    if not all_follow_through_items:
        return {
            "status": "none",
            "mode": "draft_only",
            "approval_required": True,
            "auto_send": False,
            "reason": "No follow-through targets are currently queued for drafting.",
            "target_metadata": {
                "continuity_object_id": None,
                "capture_event_id": None,
                "object_type": None,
                "priority_posture": None,
                "follow_through_posture": None,
                "recommendation_action": None,
                "thread_id": thread_hint,
            },
            "content": {
                "subject": "",
                "body": "",
            },
        }

    target = sorted(all_follow_through_items, key=_draft_follow_up_sort_key, reverse=True)[0]
    subject = f"Follow-up: {target['title']}"
    body = "\n".join(
        [
            f"Following up on: {target['title']}",
            f"Current follow-through posture: {target['follow_through_posture']}",
            f"Current priority posture: {target['current_priority_posture']}",
            f"Recommended action: {target['recommendation_action']}",
            f"Reason: {target['reason']}",
            "",
            "This draft is artifact-only and requires explicit approval before any external send.",
        ]
    )

    return {
        "status": "drafted",
        "mode": "draft_only",
        "approval_required": True,
        "auto_send": False,
        "reason": "Highest-severity follow-through item selected deterministically for operator review.",
        "target_metadata": {
            "continuity_object_id": target["id"],
            "capture_event_id": target["capture_event_id"],
            "object_type": target["object_type"],
            "priority_posture": target["current_priority_posture"],
            "follow_through_posture": target["follow_through_posture"],
            "recommendation_action": target["recommendation_action"],
            "thread_id": thread_hint,
        },
        "content": {
            "subject": subject,
            "body": body,
        },
    }


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
    follow_through_candidates: list[ChiefOfStaffFollowThroughItem] = []

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

        follow_through_posture, recommendation_action, follow_through_reason = _classify_follow_through_item(
            item=item,
            open_loop_posture=open_loop_posture,
            age_hours=age_hours,
            priority_posture=posture,
        )
        if (
            follow_through_posture is not None
            and recommendation_action is not None
            and follow_through_reason is not None
        ):
            if recommendation_action not in CHIEF_OF_STAFF_FOLLOW_THROUGH_RECOMMENDATION_ACTIONS:
                recommendation_action = "defer"
            if follow_through_posture not in CHIEF_OF_STAFF_FOLLOW_THROUGH_POSTURE_ORDER:
                follow_through_posture = "overdue"
            follow_through_candidates.append(
                {
                    "rank": 0,
                    "id": item_id,
                    "capture_event_id": item["capture_event_id"],
                    "object_type": item["object_type"],
                    "status": item["status"],
                    "title": item["title"],
                    "current_priority_posture": posture,
                    "follow_through_posture": follow_through_posture,
                    "recommendation_action": recommendation_action,
                    "reason": follow_through_reason,
                    "age_hours": age_hours,
                    "provenance_references": item["provenance_references"],
                    "created_at": item["created_at"],
                    "updated_at": item["updated_at"],
                }
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

    overdue_items_all = [
        item for item in follow_through_candidates if item["follow_through_posture"] == "overdue"
    ]
    stale_waiting_for_items_all = [
        item for item in follow_through_candidates if item["follow_through_posture"] == "stale_waiting_for"
    ]
    slipped_commitments_all = [
        item for item in follow_through_candidates if item["follow_through_posture"] == "slipped_commitment"
    ]

    overdue_items = _rank_follow_through_items(overdue_items_all, limit=limit)
    stale_waiting_for_items = _rank_follow_through_items(stale_waiting_for_items_all, limit=limit)
    slipped_commitments = _rank_follow_through_items(slipped_commitments_all, limit=limit)

    all_follow_through_items = sorted(
        follow_through_candidates,
        key=_draft_follow_up_sort_key,
        reverse=True,
    )
    escalation_posture = _build_escalation_posture(
        all_follow_through_items=all_follow_through_items,
    )
    scope_thread_id = recall_payload["summary"]["filters"].get("thread_id")
    thread_hint = None if scope_thread_id is None else str(scope_thread_id)
    draft_follow_up = _build_draft_follow_up(
        all_follow_through_items=all_follow_through_items,
        thread_hint=thread_hint,
    )

    summary: ChiefOfStaffPrioritySummary = {
        "limit": limit,
        "returned_count": len(ranked_items),
        "total_count": total_count,
        "posture_order": list(CHIEF_OF_STAFF_PRIORITY_POSTURE_ORDER),
        "order": list(CHIEF_OF_STAFF_PRIORITY_ITEM_ORDER),
        "follow_through_posture_order": list(CHIEF_OF_STAFF_FOLLOW_THROUGH_POSTURE_ORDER),
        "follow_through_item_order": list(CHIEF_OF_STAFF_FOLLOW_THROUGH_ITEM_ORDER),
        "follow_through_total_count": len(follow_through_candidates),
        "overdue_count": len(overdue_items_all),
        "stale_waiting_for_count": len(stale_waiting_for_items_all),
        "slipped_commitment_count": len(slipped_commitments_all),
        "trust_confidence_posture": trust_cap.posture,
        "trust_confidence_reason": trust_cap.reason,
        "quality_gate_status": quality_gate_status,
        "retrieval_status": retrieval_status,
    }

    brief: ChiefOfStaffPriorityBriefRecord = {
        "assembly_version": CHIEF_OF_STAFF_PRIORITY_BRIEF_ASSEMBLY_VERSION_V0,
        "scope": recall_payload["summary"]["filters"],
        "ranked_items": ranked_items,
        "overdue_items": overdue_items,
        "stale_waiting_for_items": stale_waiting_for_items,
        "slipped_commitments": slipped_commitments,
        "escalation_posture": escalation_posture,
        "draft_follow_up": draft_follow_up,
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
