from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from alicebot_api.continuity_open_loops import (
    compile_continuity_open_loop_dashboard,
    compile_continuity_weekly_review,
)
from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import (
    CHIEF_OF_STAFF_ACTION_HANDOFF_ACTIONS,
    CHIEF_OF_STAFF_ACTION_HANDOFF_ITEM_ORDER,
    CHIEF_OF_STAFF_ACTION_HANDOFF_SOURCE_ORDER,
    CHIEF_OF_STAFF_EXECUTION_READINESS_POSTURE_ORDER,
    CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER,
    CHIEF_OF_STAFF_EXECUTION_ROUTED_ITEM_ORDER,
    CHIEF_OF_STAFF_EXECUTION_ROUTING_AUDIT_ORDER,
    CHIEF_OF_STAFF_EXECUTION_ROUTING_TRANSITIONS,
    CHIEF_OF_STAFF_ESCALATION_POSTURE_ORDER,
    CHIEF_OF_STAFF_EXECUTION_POSTURE_ORDER,
    CHIEF_OF_STAFF_FOLLOW_THROUGH_ITEM_ORDER,
    CHIEF_OF_STAFF_FOLLOW_THROUGH_POSTURE_ORDER,
    CHIEF_OF_STAFF_FOLLOW_THROUGH_RECOMMENDATION_ACTIONS,
    CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER,
    CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER,
    CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS,
    CHIEF_OF_STAFF_OUTCOME_HOTSPOT_ORDER,
    CHIEF_OF_STAFF_PREPARATION_ITEM_ORDER,
    CHIEF_OF_STAFF_PRIORITY_BRIEF_ASSEMBLY_VERSION_V0,
    CHIEF_OF_STAFF_PRIORITY_ITEM_ORDER,
    CHIEF_OF_STAFF_PRIORITY_POSTURE_ORDER,
    CHIEF_OF_STAFF_RECOMMENDED_ACTION_TYPES,
    CHIEF_OF_STAFF_RECOMMENDATION_OUTCOME_ORDER,
    CHIEF_OF_STAFF_RECOMMENDATION_OUTCOMES,
    CHIEF_OF_STAFF_RESUMPTION_RECOMMENDATION_ACTIONS,
    CHIEF_OF_STAFF_RESUMPTION_SUPERVISION_ITEM_ORDER,
    CHIEF_OF_STAFF_WEEKLY_REVIEW_GUIDANCE_ACTIONS,
    CONTINUITY_OPEN_LOOP_POSTURE_ORDER,
    DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT,
    ChiefOfStaffActionHandoffAction,
    ChiefOfStaffActionHandoffApprovalDraftRecord,
    ChiefOfStaffActionHandoffBriefRecord,
    ChiefOfStaffActionHandoffItem,
    ChiefOfStaffActionHandoffRequestDraft,
    ChiefOfStaffActionHandoffRequestTarget,
    ChiefOfStaffActionHandoffSourceKind,
    ChiefOfStaffActionHandoffTaskDraftRecord,
    ChiefOfStaffDraftFollowUpRecord,
    ChiefOfStaffEscalationPosture,
    ChiefOfStaffEscalationPostureRecord,
    ChiefOfStaffExecutionPostureRecord,
    ChiefOfStaffExecutionReadinessPostureRecord,
    ChiefOfStaffExecutionRouteTarget,
    ChiefOfStaffExecutionRoutingActionCaptureResponse,
    ChiefOfStaffExecutionRoutingActionInput,
    ChiefOfStaffExecutionRoutingAuditRecord,
    ChiefOfStaffExecutionRoutingSummary,
    ChiefOfStaffExecutionRoutingTransition,
    ChiefOfStaffFollowThroughItem,
    ChiefOfStaffFollowThroughPosture,
    ChiefOfStaffFollowThroughRecommendationAction,
    ChiefOfStaffHandoffQueueGroups,
    ChiefOfStaffHandoffQueueItem,
    ChiefOfStaffHandoffQueueLifecycleState,
    ChiefOfStaffHandoffQueueSummary,
    ChiefOfStaffHandoffReviewAction,
    ChiefOfStaffHandoffReviewActionCaptureResponse,
    ChiefOfStaffHandoffReviewActionInput,
    ChiefOfStaffHandoffReviewActionRecord,
    ChiefOfStaffOutcomeHotspotRecord,
    ChiefOfStaffPatternDriftPosture,
    ChiefOfStaffPatternDriftSummaryRecord,
    ChiefOfStaffPrepChecklistRecord,
    ChiefOfStaffPreparationArtifactItem,
    ChiefOfStaffPreparationBriefRecord,
    ChiefOfStaffPreparationSectionSummary,
    ChiefOfStaffPriorityLearningSummaryRecord,
    ChiefOfStaffPriorityBriefRecord,
    ChiefOfStaffPriorityBriefRequestInput,
    ChiefOfStaffPriorityBriefResponse,
    ChiefOfStaffPriorityItem,
    ChiefOfStaffPriorityPosture,
    ChiefOfStaffRecommendationOutcome,
    ChiefOfStaffRecommendationOutcomeCaptureInput,
    ChiefOfStaffRecommendationOutcomeCaptureResponse,
    ChiefOfStaffRecommendationOutcomeRecord,
    ChiefOfStaffRecommendationOutcomeSection,
    ChiefOfStaffRecommendationOutcomeSummary,
    ChiefOfStaffRecommendationConfidencePosture,
    ChiefOfStaffRecommendedActionType,
    ChiefOfStaffRecommendedNextAction,
    ChiefOfStaffRoutedHandoffItemRecord,
    ChiefOfStaffResumptionRecommendationAction,
    ChiefOfStaffResumptionSupervisionRecommendation,
    ChiefOfStaffResumptionSupervisionRecord,
    ChiefOfStaffSuggestedTalkingPointsRecord,
    ChiefOfStaffPrioritySummary,
    ChiefOfStaffWeeklyReviewBriefRecord,
    ChiefOfStaffWeeklyReviewBriefSummary,
    ChiefOfStaffWeeklyReviewGuidanceAction,
    ChiefOfStaffWeeklyReviewGuidanceItem,
    ChiefOfStaffWhatChangedSummaryRecord,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityOpenLoopPosture,
    ContinuityRecallProvenanceReference,
    ContinuityRecallQueryInput,
    ContinuityRecallResultRecord,
    ContinuityResumptionBriefRequestInput,
    ContinuityWeeklyReviewRequestInput,
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


@dataclass(frozen=True, slots=True)
class _ActionHandoffCandidate:
    source_kind: ChiefOfStaffActionHandoffSourceKind
    source_reference_id: str | None
    title: str
    recommendation_action: ChiefOfStaffActionHandoffAction
    priority_posture: ChiefOfStaffPriorityPosture | None
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture
    rationale: str
    provenance_references: list[ContinuityRecallProvenanceReference]
    score: float


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
_PREPARATION_CONTEXT_LIMIT = 6
_WHAT_CHANGED_LIMIT = 6
_PREP_CHECKLIST_LIMIT = 6
_SUGGESTED_TALKING_POINT_LIMIT = 6
_RESUMPTION_SUPERVISION_LIMIT = 3
_OUTCOME_HISTORY_LIMIT = MAX_CONTINUITY_RECALL_LIMIT
_OUTCOME_HOTSPOT_LIMIT = 3
_OUTCOME_BODY_KIND = "chief_of_staff_recommendation_outcome"
_ACTION_HANDOFF_LIMIT = 4
_ACTION_HANDOFF_SOURCE_WEIGHT: dict[ChiefOfStaffActionHandoffSourceKind, float] = {
    "recommended_next_action": 1000.0,
    "follow_through": 900.0,
    "prep_checklist": 700.0,
    "weekly_review": 500.0,
}
_ACTION_HANDOFF_SOURCE_RANK: dict[ChiefOfStaffActionHandoffSourceKind, int] = {
    source_kind: index for index, source_kind in enumerate(CHIEF_OF_STAFF_ACTION_HANDOFF_SOURCE_ORDER)
}
_ACTION_HANDOFF_ACTION_SCOPE_MAP: dict[ChiefOfStaffActionHandoffSourceKind, str] = {
    "recommended_next_action": "chief_of_staff_priority",
    "follow_through": "chief_of_staff_follow_through",
    "prep_checklist": "chief_of_staff_preparation",
    "weekly_review": "chief_of_staff_weekly_review",
}
_HANDOFF_QUEUE_STALE_HOURS = 120.0
_HANDOFF_QUEUE_EXPIRED_HOURS = 336.0
_HANDOFF_REVIEW_ACTION_BODY_KIND = "chief_of_staff_handoff_review_action"
_EXECUTION_ROUTING_ACTION_BODY_KIND = "chief_of_staff_execution_routing_action"
_FOLLOW_UP_ELIGIBLE_SOURCE_KINDS: set[ChiefOfStaffActionHandoffSourceKind] = {
    "follow_through",
    "weekly_review",
}
_ROUTE_TARGET_TO_FIELD: dict[ChiefOfStaffExecutionRouteTarget, str] = {
    "task_workflow_draft": "task_workflow_draft_routed",
    "approval_workflow_draft": "approval_workflow_draft_routed",
    "follow_up_draft_only": "follow_up_draft_only_routed",
}
_HANDOFF_REVIEW_ACTION_TO_STATE: dict[
    ChiefOfStaffHandoffReviewAction,
    ChiefOfStaffHandoffQueueLifecycleState,
] = {
    "mark_ready": "ready",
    "mark_pending_approval": "pending_approval",
    "mark_executed": "executed",
    "mark_stale": "stale",
    "mark_expired": "expired",
}
_HANDOFF_QUEUE_STATE_EMPTY_MESSAGE: dict[ChiefOfStaffHandoffQueueLifecycleState, str] = {
    "ready": "No ready handoff items for this scope.",
    "pending_approval": "No handoff items are currently pending approval.",
    "executed": "No handoff items are currently marked executed.",
    "stale": "No stale handoff items are currently surfaced.",
    "expired": "No expired handoff items are currently surfaced.",
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
            "provenance_references": _synthetic_provenance_references(
                source_kind="chief_of_staff_synthesis",
                source_id="recommended_next_action_fallback",
            ),
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


def _build_preparation_section_summary(
    *,
    limit: int,
    returned_count: int,
    total_count: int,
    order: list[str],
) -> ChiefOfStaffPreparationSectionSummary:
    return {
        "limit": limit,
        "returned_count": returned_count,
        "total_count": total_count,
        "order": list(order),
    }


def _serialize_preparation_item(
    *,
    source: ContinuityRecallResultRecord,
    rank: int,
    reason: str,
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture,
) -> ChiefOfStaffPreparationArtifactItem:
    return {
        "rank": rank,
        "id": source["id"],
        "capture_event_id": source["capture_event_id"],
        "object_type": source["object_type"],
        "status": source["status"],
        "title": source["title"],
        "reason": reason,
        "confidence_posture": confidence_posture,
        "provenance_references": source["provenance_references"],
        "created_at": source["created_at"],
    }


def _synthetic_provenance_references(
    *,
    source_kind: str,
    source_id: str,
) -> list[ContinuityRecallProvenanceReference]:
    return [
        {
            "source_kind": source_kind,
            "source_id": source_id,
        }
    ]


def _serialize_synthetic_preparation_item(
    *,
    synthetic_id: str,
    rank: int,
    title: str,
    reason: str,
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture,
) -> ChiefOfStaffPreparationArtifactItem:
    return {
        "rank": rank,
        "id": synthetic_id,
        "capture_event_id": synthetic_id,
        "object_type": "Note",
        "status": "active",
        "title": title,
        "reason": reason,
        "confidence_posture": confidence_posture,
        "provenance_references": _synthetic_provenance_references(
            source_kind="chief_of_staff_synthesis",
            source_id=synthetic_id,
        ),
        "created_at": "1970-01-01T00:00:00+00:00",
    }


def _preparation_reason_for_context(item: ContinuityRecallResultRecord) -> str:
    object_type = item["object_type"]
    if object_type == "Decision":
        return "Decision context carried forward for deterministic meeting prep."
    if object_type == "NextAction":
        return "Immediate execution context included to reduce ambiguity at resume time."
    if object_type == "WaitingFor":
        return "Waiting-for dependency included so follow-up context is explicit before conversation."
    if object_type == "Blocker":
        return "Blocker context included so unblock discussion can happen immediately."
    if object_type == "Commitment":
        return "Active commitment included to anchor accountability in prep."
    return "Relevant continuity context included for deterministic preparation."


def _build_preparation_brief(
    *,
    recall_items: list[ContinuityRecallResultRecord],
    scope: dict[str, object],
    last_decision: ContinuityRecallResultRecord | None,
    open_loops: list[ContinuityRecallResultRecord],
    next_action: ContinuityRecallResultRecord | None,
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture,
    confidence_reason: str,
) -> ChiefOfStaffPreparationBriefRecord:
    context_candidates = sorted(
        [item for item in recall_items if item["status"] != "deleted"],
        key=lambda item: (_parse_timestamp(item["created_at"]), item["id"]),
        reverse=True,
    )
    selected_context = context_candidates[:_PREPARATION_CONTEXT_LIMIT]
    context_items = [
        _serialize_preparation_item(
            source=item,
            rank=index,
            reason=_preparation_reason_for_context(item),
            confidence_posture=confidence_posture,
        )
        for index, item in enumerate(selected_context, start=1)
    ]

    serialized_last_decision = (
        None
        if last_decision is None
        else _serialize_preparation_item(
            source=last_decision,
            rank=1,
            reason="Latest scoped decision included to ground upcoming preparation context.",
            confidence_posture=confidence_posture,
        )
    )
    serialized_open_loops = [
        _serialize_preparation_item(
            source=item,
            rank=index,
            reason="Open loop included so unresolved items are visible before resuming execution.",
            confidence_posture=confidence_posture,
        )
        for index, item in enumerate(open_loops[:_PREPARATION_CONTEXT_LIMIT], start=1)
    ]
    serialized_next_action = (
        None
        if next_action is None
        else _serialize_preparation_item(
            source=next_action,
            rank=1,
            reason="Next action is included to keep immediate execution focus explicit after interruption.",
            confidence_posture=confidence_posture,
        )
    )

    return {
        "scope": scope,  # type: ignore[typeddict-item]
        "context_items": context_items,
        "last_decision": serialized_last_decision,
        "open_loops": serialized_open_loops,
        "next_action": serialized_next_action,
        "confidence_posture": confidence_posture,
        "confidence_reason": confidence_reason,
        "summary": _build_preparation_section_summary(
            limit=_PREPARATION_CONTEXT_LIMIT,
            returned_count=len(context_items),
            total_count=len(context_candidates),
            order=list(CHIEF_OF_STAFF_PREPARATION_ITEM_ORDER),
        ),
    }


def _build_what_changed_summary(
    *,
    recent_changes: list[ContinuityRecallResultRecord],
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture,
    confidence_reason: str,
) -> ChiefOfStaffWhatChangedSummaryRecord:
    selected_items = recent_changes[:_WHAT_CHANGED_LIMIT]
    items = [
        _serialize_preparation_item(
            source=item,
            rank=index,
            reason="Included from deterministic continuity recent-changes ordering.",
            confidence_posture=confidence_posture,
        )
        for index, item in enumerate(selected_items, start=1)
    ]
    return {
        "items": items,
        "confidence_posture": confidence_posture,
        "confidence_reason": confidence_reason,
        "summary": _build_preparation_section_summary(
            limit=_WHAT_CHANGED_LIMIT,
            returned_count=len(items),
            total_count=len(recent_changes),
            order=list(CHIEF_OF_STAFF_PREPARATION_ITEM_ORDER),
        ),
    }


def _build_prep_checklist(
    *,
    last_decision: ContinuityRecallResultRecord | None,
    open_loops: list[ContinuityRecallResultRecord],
    next_action: ContinuityRecallResultRecord | None,
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture,
    confidence_reason: str,
) -> ChiefOfStaffPrepChecklistRecord:
    checklist_items: list[ChiefOfStaffPreparationArtifactItem] = []
    checklist_candidates_count = 0
    seen_ids: set[str] = set()

    if last_decision is not None:
        checklist_candidates_count += 1
        seen_ids.add(last_decision["id"])
        checklist_items.append(
            _serialize_preparation_item(
                source=last_decision,
                rank=0,
                reason="Review the latest decision assumptions before the upcoming conversation.",
                confidence_posture=confidence_posture,
            )
        )

    for open_loop in open_loops:
        checklist_candidates_count += 1
        if open_loop["id"] in seen_ids:
            continue
        seen_ids.add(open_loop["id"])
        checklist_items.append(
            _serialize_preparation_item(
                source=open_loop,
                rank=0,
                reason="Prepare a status check and explicit owner for this unresolved open loop.",
                confidence_posture=confidence_posture,
            )
        )

    if next_action is not None:
        checklist_candidates_count += 1
        if next_action["id"] not in seen_ids:
            checklist_items.append(
                _serialize_preparation_item(
                    source=next_action,
                    rank=0,
                    reason="Confirm the first executable step and owner before resuming.",
                    confidence_posture=confidence_posture,
                )
            )
            seen_ids.add(next_action["id"])

    if not checklist_items:
        checklist_items.append(
            _serialize_synthetic_preparation_item(
                synthetic_id="prep-checklist-capture-next-action",
                rank=0,
                title="Capture one concrete next action",
                reason="No scoped prep candidates are available; capture one explicit next action before resume.",
                confidence_posture=confidence_posture,
            )
        )

    selected_items = checklist_items[:_PREP_CHECKLIST_LIMIT]
    for rank, item in enumerate(selected_items, start=1):
        item["rank"] = rank

    return {
        "items": selected_items,
        "confidence_posture": confidence_posture,
        "confidence_reason": confidence_reason,
        "summary": _build_preparation_section_summary(
            limit=_PREP_CHECKLIST_LIMIT,
            returned_count=len(selected_items),
            total_count=max(checklist_candidates_count, len(selected_items)),
            order=list(CHIEF_OF_STAFF_PREPARATION_ITEM_ORDER),
        ),
    }


def _build_suggested_talking_points(
    *,
    last_decision: ContinuityRecallResultRecord | None,
    top_ranked_priority: ChiefOfStaffPriorityItem | None,
    open_loops: list[ContinuityRecallResultRecord],
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture,
    confidence_reason: str,
) -> ChiefOfStaffSuggestedTalkingPointsRecord:
    talking_points: list[ChiefOfStaffPreparationArtifactItem] = []
    talking_point_candidates_count = 0
    seen_ids: set[str] = set()

    if last_decision is not None:
        talking_point_candidates_count += 1
        seen_ids.add(last_decision["id"])
        talking_points.append(
            _serialize_preparation_item(
                source=last_decision,
                rank=0,
                reason="Use this decision as opening context to align assumptions quickly.",
                confidence_posture=confidence_posture,
            )
        )

    if top_ranked_priority is not None:
        talking_point_candidates_count += 1
        priority_id = top_ranked_priority["id"]
        if priority_id not in seen_ids:
            seen_ids.add(priority_id)
            talking_points.append(
                {
                    "rank": 0,
                    "id": priority_id,
                    "capture_event_id": top_ranked_priority["capture_event_id"],
                    "object_type": top_ranked_priority["object_type"],
                    "status": top_ranked_priority["status"],
                    "title": top_ranked_priority["title"],
                    "reason": "Lead with the top-ranked current priority to reduce ambiguity on what to do next.",
                    "confidence_posture": top_ranked_priority["confidence_posture"],
                    "provenance_references": top_ranked_priority["rationale"]["provenance_references"],
                    "created_at": top_ranked_priority["created_at"],
                }
            )

    for open_loop in open_loops:
        talking_point_candidates_count += 1
        if open_loop["id"] in seen_ids:
            continue
        seen_ids.add(open_loop["id"])
        talking_points.append(
            _serialize_preparation_item(
                source=open_loop,
                rank=0,
                reason="Raise this unresolved dependency explicitly and confirm a concrete follow-up path.",
                confidence_posture=confidence_posture,
            )
        )

    if not talking_points:
        talking_points.append(
            _serialize_synthetic_preparation_item(
                synthetic_id="talking-point-capture-next-action",
                rank=0,
                title="What is the single next action after this conversation?",
                reason="No scoped continuity signals are available, so establish one explicit next action.",
                confidence_posture=confidence_posture,
            )
        )

    selected_items = talking_points[:_SUGGESTED_TALKING_POINT_LIMIT]
    for rank, item in enumerate(selected_items, start=1):
        item["rank"] = rank

    return {
        "items": selected_items,
        "confidence_posture": confidence_posture,
        "confidence_reason": confidence_reason,
        "summary": _build_preparation_section_summary(
            limit=_SUGGESTED_TALKING_POINT_LIMIT,
            returned_count=len(selected_items),
            total_count=max(talking_point_candidates_count, len(selected_items)),
            order=list(CHIEF_OF_STAFF_PREPARATION_ITEM_ORDER),
        ),
    }


def _normalize_resumption_action(
    action: str,
) -> ChiefOfStaffResumptionRecommendationAction:
    if action in CHIEF_OF_STAFF_RESUMPTION_RECOMMENDATION_ACTIONS:
        return action  # type: ignore[return-value]
    return "review_scope"


def _build_resumption_supervision(
    *,
    recommended_next_action: ChiefOfStaffRecommendedNextAction,
    follow_through_items: list[ChiefOfStaffFollowThroughItem],
    trust_cap: _TrustConfidenceCap,
) -> ChiefOfStaffResumptionSupervisionRecord:
    recommendations: list[ChiefOfStaffResumptionSupervisionRecommendation] = []

    recommendations.append(
        {
            "rank": 0,
            "action": _normalize_resumption_action(recommended_next_action["action_type"]),
            "title": recommended_next_action["title"],
            "reason": recommended_next_action["reason"],
            "confidence_posture": recommended_next_action["confidence_posture"],
            "target_priority_id": recommended_next_action["target_priority_id"],
            "provenance_references": recommended_next_action["provenance_references"],
        }
    )

    if follow_through_items:
        top_follow_through_item = follow_through_items[0]
        recommendations.append(
            {
                "rank": 0,
                "action": _normalize_resumption_action(top_follow_through_item["recommendation_action"]),
                "title": f"Follow-through: {top_follow_through_item['title']}",
                "reason": top_follow_through_item["reason"],
                "confidence_posture": trust_cap.posture,
                "target_priority_id": top_follow_through_item["id"],
                "provenance_references": top_follow_through_item["provenance_references"],
            }
        )

    if trust_cap.posture != "high":
        recommendations.append(
            {
                "rank": 0,
                "action": "review_scope",
                "title": "Calibrate recommendation confidence before execution",
                "reason": trust_cap.reason,
                "confidence_posture": trust_cap.posture,
                "target_priority_id": None,
                "provenance_references": _synthetic_provenance_references(
                    source_kind="memory_trust_dashboard",
                    source_id="trust_confidence_cap",
                ),
            }
        )

    selected = recommendations[:_RESUMPTION_SUPERVISION_LIMIT]
    for rank, recommendation in enumerate(selected, start=1):
        recommendation["rank"] = rank

    return {
        "recommendations": selected,
        "confidence_posture": trust_cap.posture,
        "confidence_reason": trust_cap.reason,
        "summary": _build_preparation_section_summary(
            limit=_RESUMPTION_SUPERVISION_LIMIT,
            returned_count=len(selected),
            total_count=len(recommendations),
            order=list(CHIEF_OF_STAFF_RESUMPTION_SUPERVISION_ITEM_ORDER),
        ),
    }


def _parse_recommendation_outcome_record(
    item: ContinuityRecallResultRecord,
) -> ChiefOfStaffRecommendationOutcomeRecord | None:
    if item["object_type"] != "Note":
        return None

    body = item["body"]
    if not isinstance(body, dict):
        return None

    kind = body.get("kind")
    if kind != _OUTCOME_BODY_KIND:
        return None

    raw_outcome = body.get("outcome")
    if not isinstance(raw_outcome, str) or raw_outcome not in CHIEF_OF_STAFF_RECOMMENDATION_OUTCOMES:
        return None
    outcome: ChiefOfStaffRecommendationOutcome = raw_outcome  # type: ignore[assignment]

    raw_action_type = body.get("recommendation_action_type")
    if not isinstance(raw_action_type, str) or raw_action_type not in CHIEF_OF_STAFF_RECOMMENDED_ACTION_TYPES:
        return None
    recommendation_action_type: ChiefOfStaffRecommendedActionType = raw_action_type  # type: ignore[assignment]

    recommendation_title = body.get("recommendation_title")
    if not isinstance(recommendation_title, str):
        return None

    rewritten_title = body.get("rewritten_title")
    rewritten_title_value = rewritten_title if isinstance(rewritten_title, str) else None

    target_priority_id = body.get("target_priority_id")
    target_priority_id_value = target_priority_id if isinstance(target_priority_id, str) else None

    rationale = body.get("rationale")
    rationale_value = rationale if isinstance(rationale, str) else None

    return {
        "id": item["id"],
        "capture_event_id": item["capture_event_id"],
        "outcome": outcome,
        "recommendation_action_type": recommendation_action_type,
        "recommendation_title": recommendation_title,
        "rewritten_title": rewritten_title_value,
        "target_priority_id": target_priority_id_value,
        "rationale": rationale_value,
        "provenance_references": item["provenance_references"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def _outcome_sort_key(item: ChiefOfStaffRecommendationOutcomeRecord) -> tuple[str, str]:
    return (item["created_at"], item["id"])


def _outcome_counts(
    items: list[ChiefOfStaffRecommendationOutcomeRecord],
) -> dict[ChiefOfStaffRecommendationOutcome, int]:
    counts: dict[ChiefOfStaffRecommendationOutcome, int] = {
        "accept": 0,
        "defer": 0,
        "ignore": 0,
        "rewrite": 0,
    }
    for item in items:
        counts[item["outcome"]] += 1
    return counts


def _build_outcome_hotspots(
    *,
    items: list[ChiefOfStaffRecommendationOutcomeRecord],
    outcome: ChiefOfStaffRecommendationOutcome,
) -> list[ChiefOfStaffOutcomeHotspotRecord]:
    counts_by_key: dict[str, int] = {}
    for item in items:
        if item["outcome"] != outcome:
            continue
        hotspot_key = item["target_priority_id"] or item["recommendation_action_type"]
        counts_by_key[hotspot_key] = counts_by_key.get(hotspot_key, 0) + 1

    hotspots = [
        {"key": key, "count": count}
        for key, count in sorted(
            counts_by_key.items(),
            key=lambda entry: (-entry[1], entry[0]),
        )[:_OUTCOME_HOTSPOT_LIMIT]
    ]
    return hotspots


def _list_recommendation_outcome_records(
    recall_items: list[ContinuityRecallResultRecord],
) -> list[ChiefOfStaffRecommendationOutcomeRecord]:
    all_outcome_items = [
        parsed
        for parsed in (
            _parse_recommendation_outcome_record(item)
            for item in recall_items
        )
        if parsed is not None
    ]
    all_outcome_items.sort(key=_outcome_sort_key, reverse=True)
    return all_outcome_items


def _build_recommendation_outcome_section(
    *,
    all_outcome_items: list[ChiefOfStaffRecommendationOutcomeRecord],
    limit: int,
) -> ChiefOfStaffRecommendationOutcomeSection:
    selected_items = all_outcome_items[:limit] if limit > 0 else []
    summary: ChiefOfStaffRecommendationOutcomeSummary = {
        "returned_count": len(selected_items),
        "total_count": len(all_outcome_items),
        "outcome_counts": _outcome_counts(all_outcome_items),
        "order": list(CHIEF_OF_STAFF_RECOMMENDATION_OUTCOME_ORDER),
    }
    return {
        "items": selected_items,
        "summary": summary,
    }


def _build_priority_shift_explanation(
    *,
    counts: dict[ChiefOfStaffRecommendationOutcome, int],
) -> str:
    accept_count = counts["accept"]
    defer_count = counts["defer"]
    ignore_count = counts["ignore"]
    rewrite_count = counts["rewrite"]
    override_count = ignore_count + rewrite_count

    if accept_count + defer_count + override_count == 0:
        return (
            "No recommendation outcomes are captured yet; prioritization remains anchored to "
            "current continuity and trust signals."
        )
    if override_count > accept_count:
        return (
            "Prioritization is shifting toward stricter confidence because ignore/rewrite outcomes "
            "currently exceed accepted recommendations."
        )
    if defer_count > 0 and defer_count >= accept_count:
        return (
            "Prioritization is shifting toward pacing controls because deferred outcomes are "
            "comparable to or above accepted recommendations."
        )
    return (
        "Prioritization is reinforcing currently accepted recommendation patterns while tracking "
        "defer/override hotspots."
    )


def _build_priority_learning_summary(
    *,
    all_outcome_items: list[ChiefOfStaffRecommendationOutcomeRecord],
) -> ChiefOfStaffPriorityLearningSummaryRecord:
    counts = _outcome_counts(all_outcome_items)
    total_count = len(all_outcome_items)
    override_count = counts["ignore"] + counts["rewrite"]

    acceptance_rate = 0.0 if total_count == 0 else counts["accept"] / total_count
    override_rate = 0.0 if total_count == 0 else override_count / total_count

    return {
        "total_count": total_count,
        "accept_count": counts["accept"],
        "defer_count": counts["defer"],
        "ignore_count": counts["ignore"],
        "rewrite_count": counts["rewrite"],
        "acceptance_rate": round(acceptance_rate, 6),
        "override_rate": round(override_rate, 6),
        "defer_hotspots": _build_outcome_hotspots(items=all_outcome_items, outcome="defer"),
        "ignore_hotspots": _build_outcome_hotspots(items=all_outcome_items, outcome="ignore"),
        "priority_shift_explanation": _build_priority_shift_explanation(counts=counts),
        "hotspot_order": list(CHIEF_OF_STAFF_OUTCOME_HOTSPOT_ORDER),
    }


def _build_pattern_drift_summary(
    *,
    learning_summary: ChiefOfStaffPriorityLearningSummaryRecord,
) -> ChiefOfStaffPatternDriftSummaryRecord:
    total_count = learning_summary["total_count"]
    override_count = learning_summary["ignore_count"] + learning_summary["rewrite_count"]
    accept_count = learning_summary["accept_count"]
    defer_count = learning_summary["defer_count"]

    posture: ChiefOfStaffPatternDriftPosture
    reason: str
    if total_count == 0:
        posture = "insufficient_signal"
        reason = "No recommendation outcomes are available yet, so drift posture is informational only."
    elif override_count > accept_count:
        posture = "drifting"
        reason = "Overrides are outpacing accepts, so recommendation behavior is drifting and needs inspection."
    elif accept_count > override_count and defer_count <= accept_count:
        posture = "improving"
        reason = "Accepted outcomes are leading with bounded defers/overrides, indicating improving recommendation fit."
    else:
        posture = "stable"
        reason = "Outcome mix is balanced; recommendation behavior is stable with routine monitoring."

    return {
        "posture": posture,
        "reason": reason,
        "supporting_signals": [
            f"Outcomes captured: {total_count}",
            f"Accept={accept_count}, Defer={defer_count}, Ignore={learning_summary['ignore_count']}, Rewrite={learning_summary['rewrite_count']}",
            f"Acceptance rate={learning_summary['acceptance_rate']:.6f}, Override rate={learning_summary['override_rate']:.6f}",
        ],
    }


def _build_weekly_review_brief(
    *,
    scope: dict[str, object],
    weekly_rollup: dict[str, object],
    follow_through_items: list[ChiefOfStaffFollowThroughItem],
) -> ChiefOfStaffWeeklyReviewBriefRecord:
    action_counts: dict[ChiefOfStaffFollowThroughRecommendationAction, int] = {
        "nudge": 0,
        "defer": 0,
        "escalate": 0,
        "close_loop_candidate": 0,
    }
    for item in follow_through_items:
        action_counts[item["recommendation_action"]] += 1

    blocker_count = int(weekly_rollup.get("blocker_count", 0))
    stale_count = int(weekly_rollup.get("stale_count", 0))
    waiting_for_count = int(weekly_rollup.get("waiting_for_count", 0))
    next_action_count = int(weekly_rollup.get("next_action_count", 0))

    guidance_candidates: list[ChiefOfStaffWeeklyReviewGuidanceItem] = [
        {
            "rank": 0,
            "action": "escalate",
            "signal_count": action_counts["escalate"] + blocker_count,
            "rationale": (
                f"Escalate where blockers ({blocker_count}) and escalate actions "
                f"({action_counts['escalate']}) indicate execution risk."
            ),
        },
        {
            "rank": 0,
            "action": "close",
            "signal_count": action_counts["close_loop_candidate"] + next_action_count,
            "rationale": (
                f"Close loops where close candidates ({action_counts['close_loop_candidate']}) "
                f"and actionable next steps ({next_action_count}) support deterministic closure."
            ),
        },
        {
            "rank": 0,
            "action": "defer",
            "signal_count": action_counts["defer"] + stale_count + waiting_for_count,
            "rationale": (
                f"Defer or park work where defer actions ({action_counts['defer']}), "
                f"stale items ({stale_count}), and waiting-for load ({waiting_for_count}) are concentrated."
            ),
        },
    ]
    guidance_candidates.sort(
        key=lambda item: (item["signal_count"], item["action"]),
        reverse=True,
    )
    for rank, item in enumerate(guidance_candidates, start=1):
        item["rank"] = rank

    summary: ChiefOfStaffWeeklyReviewBriefSummary = {
        "guidance_order": list(CHIEF_OF_STAFF_WEEKLY_REVIEW_GUIDANCE_ACTIONS),
        "guidance_item_order": ["signal_count_desc", "action_desc"],
    }
    return {
        "scope": scope,  # type: ignore[typeddict-item]
        "rollup": weekly_rollup,  # type: ignore[typeddict-item]
        "guidance": guidance_candidates,
        "summary": summary,
    }


def _normalize_handoff_action(
    *,
    source_kind: ChiefOfStaffActionHandoffSourceKind,
    action: str,
) -> ChiefOfStaffActionHandoffAction:
    if source_kind == "weekly_review":
        if action == "close":
            return "weekly_review_close"
        if action == "defer":
            return "weekly_review_defer"
        if action == "escalate":
            return "weekly_review_escalate"
        return "review_scope"

    if action in CHIEF_OF_STAFF_ACTION_HANDOFF_ACTIONS:
        return action  # type: ignore[return-value]
    return "review_scope"


def _normalize_identifier_part(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    normalized = normalized.strip("-")
    return normalized or "none"


def _action_handoff_sort_key(candidate: _ActionHandoffCandidate) -> tuple[float, int, str, str]:
    return (
        -candidate.score,
        _ACTION_HANDOFF_SOURCE_RANK[candidate.source_kind],
        candidate.source_reference_id or "",
        candidate.title,
    )


def _build_action_handoff_request_target(
    *,
    scope: dict[str, object],
) -> ChiefOfStaffActionHandoffRequestTarget:
    thread_id = scope.get("thread_id")
    task_id = scope.get("task_id")
    project = scope.get("project")
    person = scope.get("person")
    return {
        "thread_id": thread_id if isinstance(thread_id, str) else None,
        "task_id": task_id if isinstance(task_id, str) else None,
        "project": project if isinstance(project, str) else None,
        "person": person if isinstance(person, str) else None,
    }


def _build_action_handoff_request_draft(
    *,
    candidate: _ActionHandoffCandidate,
    handoff_item_id: str,
) -> ChiefOfStaffActionHandoffRequestDraft:
    domain_hint = "follow_through" if candidate.source_kind == "follow_through" else "planning"
    if candidate.source_kind == "weekly_review":
        domain_hint = "weekly_review"

    return {
        "action": candidate.recommendation_action,
        "scope": _ACTION_HANDOFF_ACTION_SCOPE_MAP[candidate.source_kind],
        "domain_hint": domain_hint,
        "risk_hint": "governed_handoff",
        "attributes": {
            "handoff_item_id": handoff_item_id,
            "source_kind": candidate.source_kind,
            "source_reference_id": candidate.source_reference_id,
            "confidence_posture": candidate.confidence_posture,
            "priority_posture": candidate.priority_posture,
            "score": round(candidate.score, 6),
            "rationale": candidate.rationale,
        },
    }


def _build_action_handoff_task_draft(
    *,
    candidate: _ActionHandoffCandidate,
    handoff_item_id: str,
    target: ChiefOfStaffActionHandoffRequestTarget,
    request_draft: ChiefOfStaffActionHandoffRequestDraft,
) -> ChiefOfStaffActionHandoffTaskDraftRecord:
    return {
        "status": "draft",
        "mode": "governed_request_draft",
        "approval_required": True,
        "auto_execute": False,
        "source_handoff_item_id": handoff_item_id,
        "title": candidate.title,
        "summary": (
            "Draft-only governed request assembled from chief-of-staff handoff artifacts; "
            "requires explicit approval before any execution."
        ),
        "target": target,
        "request": request_draft,
        "rationale": candidate.rationale,
        "provenance_references": candidate.provenance_references,
    }


def _build_action_handoff_approval_draft(
    *,
    candidate: _ActionHandoffCandidate,
    handoff_item_id: str,
    request_draft: ChiefOfStaffActionHandoffRequestDraft,
) -> ChiefOfStaffActionHandoffApprovalDraftRecord:
    return {
        "status": "draft_only",
        "mode": "approval_request_draft",
        "decision": "approval_required",
        "approval_required": True,
        "auto_submit": False,
        "source_handoff_item_id": handoff_item_id,
        "request": request_draft,
        "reason": (
            "Execution remains approval-bounded. This approval draft is artifact-only and must be "
            "explicitly submitted and resolved before any side effect."
        ),
        "required_checks": [
            "operator_review_handoff_artifact",
            "submit_governed_approval_request",
            "explicit_approval_resolution",
        ],
        "provenance_references": candidate.provenance_references,
    }


def _aggregate_provenance_references(
    handoff_items: list[ChiefOfStaffActionHandoffItem],
) -> list[ContinuityRecallProvenanceReference]:
    unique_keys: set[tuple[str, str]] = set()
    for item in handoff_items:
        for reference in item["provenance_references"]:
            unique_keys.add((reference["source_kind"], reference["source_id"]))
    return [
        {
            "source_kind": source_kind,
            "source_id": source_id,
        }
        for source_kind, source_id in sorted(unique_keys)
    ]


def _build_execution_posture() -> ChiefOfStaffExecutionPostureRecord:
    posture = "approval_bounded_artifact_only"
    if posture not in CHIEF_OF_STAFF_EXECUTION_POSTURE_ORDER:
        posture = CHIEF_OF_STAFF_EXECUTION_POSTURE_ORDER[0]  # type: ignore[index]

    non_autonomous_guarantee = (
        "No task, approval, connector send, or external side effect is executed by this endpoint."
    )
    return {
        "posture": posture,  # type: ignore[typeddict-item]
        "approval_required": True,
        "autonomous_execution": False,
        "external_side_effects_allowed": False,
        "default_routing_decision": "approval_required",
        "required_operator_actions": [
            "review_handoff_items",
            "submit_task_or_approval_request",
            "resolve_approval_before_execution",
        ],
        "non_autonomous_guarantee": non_autonomous_guarantee,
        "reason": "Chief-of-staff execution routing remains deterministic draft-only prep in P8-S31.",
    }


def _build_action_handoff_artifacts(
    *,
    recommended_next_action: ChiefOfStaffRecommendedNextAction,
    all_follow_through_items: list[ChiefOfStaffFollowThroughItem],
    prep_checklist: ChiefOfStaffPrepChecklistRecord,
    weekly_review_brief: ChiefOfStaffWeeklyReviewBriefRecord,
    trust_cap: _TrustConfidenceCap,
    scope: dict[str, object],
) -> tuple[
    ChiefOfStaffActionHandoffBriefRecord,
    list[ChiefOfStaffActionHandoffItem],
    ChiefOfStaffActionHandoffTaskDraftRecord,
    ChiefOfStaffActionHandoffApprovalDraftRecord,
    ChiefOfStaffExecutionPostureRecord,
]:
    candidates: list[_ActionHandoffCandidate] = []

    rec_priority = recommended_next_action["priority_posture"]
    rec_priority_weight = 0.0 if rec_priority is None else _POSTURE_WEIGHT[rec_priority]
    candidates.append(
        _ActionHandoffCandidate(
            source_kind="recommended_next_action",
            source_reference_id=recommended_next_action["target_priority_id"],
            title=recommended_next_action["title"],
            recommendation_action=_normalize_handoff_action(
                source_kind="recommended_next_action",
                action=recommended_next_action["action_type"],
            ),
            priority_posture=rec_priority,
            confidence_posture=recommended_next_action["confidence_posture"],
            rationale=recommended_next_action["reason"],
            provenance_references=recommended_next_action["provenance_references"],
            score=round(
                _ACTION_HANDOFF_SOURCE_WEIGHT["recommended_next_action"]
                + rec_priority_weight
                + (_CONFIDENCE_ORDER[recommended_next_action["confidence_posture"]] * 25.0),
                6,
            ),
        )
    )

    if all_follow_through_items:
        top_follow_through = all_follow_through_items[0]
        follow_through_action = _normalize_handoff_action(
            source_kind="follow_through",
            action=top_follow_through["recommendation_action"],
        )
        candidates.append(
            _ActionHandoffCandidate(
                source_kind="follow_through",
                source_reference_id=top_follow_through["id"],
                title=f"Follow-through: {top_follow_through['title']}",
                recommendation_action=follow_through_action,
                priority_posture=top_follow_through["current_priority_posture"],
                confidence_posture=trust_cap.posture,
                rationale=top_follow_through["reason"],
                provenance_references=top_follow_through["provenance_references"],
                score=round(
                    _ACTION_HANDOFF_SOURCE_WEIGHT["follow_through"]
                    + (_FOLLOW_THROUGH_ACTION_WEIGHT[top_follow_through["recommendation_action"]] * 30.0)
                    + top_follow_through["age_hours"],
                    6,
                ),
            )
        )

    if prep_checklist["items"]:
        top_prep = prep_checklist["items"][0]
        candidates.append(
            _ActionHandoffCandidate(
                source_kind="prep_checklist",
                source_reference_id=top_prep["id"],
                title=f"Preparation: {top_prep['title']}",
                recommendation_action="review_scope",
                priority_posture=None,
                confidence_posture=top_prep["confidence_posture"],
                rationale=top_prep["reason"],
                provenance_references=top_prep["provenance_references"],
                score=round(
                    _ACTION_HANDOFF_SOURCE_WEIGHT["prep_checklist"]
                    + max(0, _PREP_CHECKLIST_LIMIT - top_prep["rank"]),
                    6,
                ),
            )
        )

    if weekly_review_brief["guidance"]:
        top_guidance = weekly_review_brief["guidance"][0]
        candidates.append(
            _ActionHandoffCandidate(
                source_kind="weekly_review",
                source_reference_id=f"weekly-{top_guidance['action']}",
                title=f"Weekly review: {top_guidance['action']}",
                recommendation_action=_normalize_handoff_action(
                    source_kind="weekly_review",
                    action=top_guidance["action"],
                ),
                priority_posture=None,
                confidence_posture=trust_cap.posture,
                rationale=top_guidance["rationale"],
                provenance_references=_synthetic_provenance_references(
                    source_kind="continuity_weekly_review",
                    source_id=f"guidance-{top_guidance['action']}",
                ),
                score=round(
                    _ACTION_HANDOFF_SOURCE_WEIGHT["weekly_review"]
                    + (float(top_guidance["signal_count"]) * 20.0),
                    6,
                ),
            )
        )

    sorted_candidates = sorted(candidates, key=_action_handoff_sort_key)
    selected_candidates = sorted_candidates[:_ACTION_HANDOFF_LIMIT]

    target = _build_action_handoff_request_target(scope=scope)
    handoff_items: list[ChiefOfStaffActionHandoffItem] = []
    for rank, candidate in enumerate(selected_candidates, start=1):
        source_ref = _normalize_identifier_part(candidate.source_reference_id or "none")
        handoff_item_id = f"handoff-{rank}-{candidate.source_kind}-{source_ref}"
        request_draft = _build_action_handoff_request_draft(
            candidate=candidate,
            handoff_item_id=handoff_item_id,
        )
        task_draft = _build_action_handoff_task_draft(
            candidate=candidate,
            handoff_item_id=handoff_item_id,
            target=target,
            request_draft=request_draft,
        )
        approval_draft = _build_action_handoff_approval_draft(
            candidate=candidate,
            handoff_item_id=handoff_item_id,
            request_draft=request_draft,
        )
        handoff_items.append(
            {
                "rank": rank,
                "handoff_item_id": handoff_item_id,
                "source_kind": candidate.source_kind,
                "source_reference_id": candidate.source_reference_id,
                "title": candidate.title,
                "recommendation_action": candidate.recommendation_action,
                "priority_posture": candidate.priority_posture,
                "confidence_posture": candidate.confidence_posture,
                "rationale": candidate.rationale,
                "provenance_references": candidate.provenance_references,
                "score": round(candidate.score, 6),
                "task_draft": task_draft,
                "approval_draft": approval_draft,
            }
        )

    execution_posture = _build_execution_posture()
    non_autonomous_guarantee = execution_posture["non_autonomous_guarantee"]
    handoff_provenance = _aggregate_provenance_references(handoff_items=handoff_items)
    active_sources = ", ".join(item["source_kind"] for item in handoff_items)
    summary = (
        f"Prepared {len(handoff_items)} deterministic handoff items from {active_sources} signals. "
        "All task and approval drafts remain artifact-only and approval-bounded."
    )
    action_handoff_brief: ChiefOfStaffActionHandoffBriefRecord = {
        "summary": summary,
        "confidence_posture": trust_cap.posture,
        "non_autonomous_guarantee": non_autonomous_guarantee,
        "order": list(CHIEF_OF_STAFF_ACTION_HANDOFF_ITEM_ORDER),
        "source_order": list(CHIEF_OF_STAFF_ACTION_HANDOFF_SOURCE_ORDER),
        "provenance_references": handoff_provenance,
    }

    if handoff_items:
        task_draft = handoff_items[0]["task_draft"]
        approval_draft = handoff_items[0]["approval_draft"]
    else:
        fallback_candidate = _ActionHandoffCandidate(
            source_kind="recommended_next_action",
            source_reference_id=None,
            title="Capture one concrete next action",
            recommendation_action="capture_new_priority",
            priority_posture=None,
            confidence_posture=trust_cap.posture,
            rationale="No actionable handoff candidates were available in the scoped data.",
            provenance_references=_synthetic_provenance_references(
                source_kind="chief_of_staff_synthesis",
                source_id="action_handoff_empty_fallback",
            ),
            score=0.0,
        )
        fallback_request = _build_action_handoff_request_draft(
            candidate=fallback_candidate,
            handoff_item_id="handoff-fallback",
        )
        task_draft = _build_action_handoff_task_draft(
            candidate=fallback_candidate,
            handoff_item_id="handoff-fallback",
            target=target,
            request_draft=fallback_request,
        )
        approval_draft = _build_action_handoff_approval_draft(
            candidate=fallback_candidate,
            handoff_item_id="handoff-fallback",
            request_draft=fallback_request,
        )

    return action_handoff_brief, handoff_items, task_draft, approval_draft, execution_posture


def _handoff_item_id_from_request_payload(request_payload: object) -> str | None:
    if not isinstance(request_payload, dict):
        return None
    attributes = request_payload.get("attributes")
    if not isinstance(attributes, dict):
        return None
    handoff_item_id = attributes.get("handoff_item_id")
    if not isinstance(handoff_item_id, str):
        return None
    normalized = handoff_item_id.strip()
    return normalized or None


def _build_governed_handoff_state_maps(
    *,
    store: ContinuityStore,
) -> tuple[set[str], set[str]]:
    if not hasattr(store, "list_approvals") or not hasattr(store, "list_tasks"):
        return set(), set()

    pending_approval_ids: set[str] = set()
    executed_ids: set[str] = set()

    for approval in store.list_approvals():
        handoff_item_id = _handoff_item_id_from_request_payload(approval.get("request"))
        if handoff_item_id is None:
            continue
        if approval["status"] == "pending":
            pending_approval_ids.add(handoff_item_id)

    for task in store.list_tasks():
        handoff_item_id = _handoff_item_id_from_request_payload(task.get("request"))
        if handoff_item_id is None:
            continue
        if task["status"] == "executed":
            executed_ids.add(handoff_item_id)
        elif task["status"] == "pending_approval":
            pending_approval_ids.add(handoff_item_id)

    pending_approval_ids.difference_update(executed_ids)
    return pending_approval_ids, executed_ids


def _parse_timestamp_optional(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return _parse_timestamp(value)
    except ValueError:
        return None


def _queue_age_hours(
    *,
    source_created_at: datetime | None,
    latest_source_created_at: datetime | None,
) -> float | None:
    if source_created_at is None or latest_source_created_at is None:
        return None
    return _age_hours_relative_to_latest(
        latest_created_at=latest_source_created_at,
        item_created_at=source_created_at,
    )


def _queue_state_for_age(
    age_hours: float | None,
) -> ChiefOfStaffHandoffQueueLifecycleState | None:
    if age_hours is None:
        return None
    if age_hours >= _HANDOFF_QUEUE_EXPIRED_HOURS:
        return "expired"
    if age_hours >= _HANDOFF_QUEUE_STALE_HOURS:
        return "stale"
    return None


def _available_handoff_review_actions(
    state: ChiefOfStaffHandoffQueueLifecycleState,
) -> list[ChiefOfStaffHandoffReviewAction]:
    return [
        action
        for action in CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS
        if _HANDOFF_REVIEW_ACTION_TO_STATE[action] != state
    ]


def _infer_handoff_queue_state(
    *,
    handoff_item: ChiefOfStaffActionHandoffItem,
    pending_approval_ids: set[str],
    executed_ids: set[str],
    source_status_by_id: dict[str, str],
    source_created_at_by_id: dict[str, datetime],
    latest_source_created_at: datetime | None,
    follow_through_by_id: dict[str, ChiefOfStaffFollowThroughItem],
) -> tuple[ChiefOfStaffHandoffQueueLifecycleState, str, float | None]:
    handoff_item_id = handoff_item["handoff_item_id"]
    if handoff_item_id in executed_ids:
        return "executed", "Linked governed task status is executed.", None
    if handoff_item_id in pending_approval_ids:
        return "pending_approval", "Linked governed approval/task is currently pending approval.", None

    source_reference_id = handoff_item["source_reference_id"]
    source_created_at = (
        None
        if source_reference_id is None
        else source_created_at_by_id.get(source_reference_id)
    )
    age_hours = _queue_age_hours(
        source_created_at=source_created_at,
        latest_source_created_at=latest_source_created_at,
    )

    if handoff_item["priority_posture"] == "stale":
        return "stale", "Mapped source priority posture is stale.", age_hours

    if source_reference_id is not None and source_status_by_id.get(source_reference_id) == "stale":
        return "stale", "Mapped source continuity object status is stale.", age_hours

    follow_through_item = (
        None
        if source_reference_id is None
        else follow_through_by_id.get(source_reference_id)
    )
    if follow_through_item is not None:
        follow_through_age = follow_through_item["age_hours"]
        age_state = _queue_state_for_age(follow_through_age)
        if follow_through_item["follow_through_posture"] == "stale_waiting_for":
            return "stale", "Follow-through source is stale waiting-for and requires review.", follow_through_age
        if age_state == "expired":
            return "expired", "Follow-through source age exceeded deterministic expiration threshold.", follow_through_age
        if age_state == "stale":
            return "stale", "Follow-through source age exceeded deterministic stale threshold.", follow_through_age

    age_state = _queue_state_for_age(age_hours)
    if age_state == "expired":
        return "expired", "Source age exceeded deterministic expiration threshold.", age_hours
    if age_state == "stale":
        return "stale", "Source age exceeded deterministic stale threshold.", age_hours

    return "ready", "Handoff item is ready for explicit operator review.", age_hours


def _parse_handoff_review_action_record(
    item: ContinuityRecallResultRecord,
) -> ChiefOfStaffHandoffReviewActionRecord | None:
    if item["object_type"] != "Note":
        return None

    body = item["body"]
    if not isinstance(body, dict):
        return None

    if body.get("kind") != _HANDOFF_REVIEW_ACTION_BODY_KIND:
        return None

    handoff_item_id = body.get("handoff_item_id")
    if not isinstance(handoff_item_id, str) or not handoff_item_id.strip():
        return None

    raw_review_action = body.get("review_action")
    if (
        not isinstance(raw_review_action, str)
        or raw_review_action not in CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS
    ):
        return None
    review_action: ChiefOfStaffHandoffReviewAction = raw_review_action  # type: ignore[assignment]

    raw_next_state = body.get("next_lifecycle_state")
    if (
        not isinstance(raw_next_state, str)
        or raw_next_state not in CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER
    ):
        return None
    next_lifecycle_state: ChiefOfStaffHandoffQueueLifecycleState = raw_next_state  # type: ignore[assignment]

    raw_previous_state = body.get("previous_lifecycle_state")
    previous_lifecycle_state: ChiefOfStaffHandoffQueueLifecycleState | None
    if raw_previous_state is None:
        previous_lifecycle_state = None
    elif (
        isinstance(raw_previous_state, str)
        and raw_previous_state in CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER
    ):
        previous_lifecycle_state = raw_previous_state  # type: ignore[assignment]
    else:
        return None

    raw_reason = body.get("reason")
    reason = (
        raw_reason
        if isinstance(raw_reason, str) and raw_reason.strip()
        else "Lifecycle transition captured from explicit operator review action."
    )

    raw_note = body.get("note")
    note = raw_note if isinstance(raw_note, str) and raw_note.strip() else None

    return {
        "id": item["id"],
        "capture_event_id": item["capture_event_id"],
        "handoff_item_id": handoff_item_id.strip(),
        "review_action": review_action,
        "previous_lifecycle_state": previous_lifecycle_state,
        "next_lifecycle_state": next_lifecycle_state,
        "reason": reason,
        "note": note,
        "provenance_references": item["provenance_references"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def _handoff_review_action_sort_key(
    item: ChiefOfStaffHandoffReviewActionRecord,
) -> tuple[str, str]:
    return (item["created_at"], item["id"])


def _list_handoff_review_action_records(
    recall_items: list[ContinuityRecallResultRecord],
) -> list[ChiefOfStaffHandoffReviewActionRecord]:
    records = [
        parsed
        for parsed in (
            _parse_handoff_review_action_record(item)
            for item in recall_items
        )
        if parsed is not None
    ]
    records.sort(key=_handoff_review_action_sort_key, reverse=True)
    return records


def _parse_execution_routing_audit_record(
    item: ContinuityRecallResultRecord,
) -> ChiefOfStaffExecutionRoutingAuditRecord | None:
    if item["object_type"] != "Note":
        return None

    body = item["body"]
    if not isinstance(body, dict):
        return None

    if body.get("kind") != _EXECUTION_ROUTING_ACTION_BODY_KIND:
        return None

    handoff_item_id = body.get("handoff_item_id")
    if not isinstance(handoff_item_id, str) or not handoff_item_id.strip():
        return None

    raw_route_target = body.get("route_target")
    if (
        not isinstance(raw_route_target, str)
        or raw_route_target not in CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER
    ):
        return None
    route_target: ChiefOfStaffExecutionRouteTarget = raw_route_target  # type: ignore[assignment]

    raw_transition = body.get("transition")
    if (
        not isinstance(raw_transition, str)
        or raw_transition not in CHIEF_OF_STAFF_EXECUTION_ROUTING_TRANSITIONS
    ):
        return None
    transition: ChiefOfStaffExecutionRoutingTransition = raw_transition  # type: ignore[assignment]

    previously_routed = bool(body.get("previously_routed", False))
    route_state = bool(body.get("route_state", True))

    raw_reason = body.get("reason")
    reason = (
        raw_reason
        if isinstance(raw_reason, str) and raw_reason.strip()
        else "Governed execution routing transition captured with draft-only posture."
    )
    raw_note = body.get("note")
    note = raw_note if isinstance(raw_note, str) and raw_note.strip() else None

    return {
        "id": item["id"],
        "capture_event_id": item["capture_event_id"],
        "handoff_item_id": handoff_item_id.strip(),
        "route_target": route_target,
        "transition": transition,
        "previously_routed": previously_routed,
        "route_state": route_state,
        "reason": reason,
        "note": note,
        "provenance_references": item["provenance_references"],
        "created_at": item["created_at"],
        "updated_at": item["updated_at"],
    }


def _execution_routing_audit_sort_key(
    item: ChiefOfStaffExecutionRoutingAuditRecord,
) -> tuple[str, str]:
    return (item["created_at"], item["id"])


def _list_execution_routing_audit_records(
    recall_items: list[ContinuityRecallResultRecord],
) -> list[ChiefOfStaffExecutionRoutingAuditRecord]:
    records = [
        parsed
        for parsed in (
            _parse_execution_routing_audit_record(item)
            for item in recall_items
        )
        if parsed is not None
    ]
    records.sort(key=_execution_routing_audit_sort_key, reverse=True)
    return records


def _build_execution_readiness_posture(
    *,
    execution_posture: ChiefOfStaffExecutionPostureRecord,
) -> ChiefOfStaffExecutionReadinessPostureRecord:
    return {
        "posture": CHIEF_OF_STAFF_EXECUTION_READINESS_POSTURE_ORDER[0],  # type: ignore[index]
        "approval_required": execution_posture["approval_required"],
        "autonomous_execution": execution_posture["autonomous_execution"],
        "external_side_effects_allowed": execution_posture["external_side_effects_allowed"],
        "approval_path_visible": True,
        "route_target_order": list(CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER),
        "required_route_targets": [
            "task_workflow_draft",
            "approval_workflow_draft",
        ],
        "transition_order": list(CHIEF_OF_STAFF_EXECUTION_ROUTING_TRANSITIONS),
        "non_autonomous_guarantee": execution_posture["non_autonomous_guarantee"],
        "reason": (
            "Execution routing remains draft-only and approval-bounded; operators can explicitly route "
            "handoff items into governed task/approval drafts with auditable transitions."
        ),
    }


def _build_execution_routing_artifacts(
    *,
    handoff_items: list[ChiefOfStaffActionHandoffItem],
    routing_audit_trail: list[ChiefOfStaffExecutionRoutingAuditRecord],
    draft_follow_up: ChiefOfStaffDraftFollowUpRecord,
    execution_posture: ChiefOfStaffExecutionPostureRecord,
) -> tuple[
    ChiefOfStaffExecutionRoutingSummary,
    list[ChiefOfStaffRoutedHandoffItemRecord],
    ChiefOfStaffExecutionReadinessPostureRecord,
]:
    latest_by_item_target: dict[tuple[str, ChiefOfStaffExecutionRouteTarget], ChiefOfStaffExecutionRoutingAuditRecord] = {}
    latest_by_item: dict[str, ChiefOfStaffExecutionRoutingAuditRecord] = {}
    for transition in routing_audit_trail:
        item_id = transition["handoff_item_id"]
        route_target = transition["route_target"]
        key = (item_id, route_target)
        if key not in latest_by_item_target:
            latest_by_item_target[key] = transition
        if item_id not in latest_by_item:
            latest_by_item[item_id] = transition

    routed_handoff_items: list[ChiefOfStaffRoutedHandoffItemRecord] = []
    task_routed_count = 0
    approval_routed_count = 0
    follow_up_routed_count = 0

    sorted_handoffs = sorted(
        handoff_items,
        key=lambda item: (item["rank"], item["handoff_item_id"]),
    )
    for handoff_item in sorted_handoffs:
        handoff_item_id = handoff_item["handoff_item_id"]
        follow_up_applicable = handoff_item["source_kind"] in _FOLLOW_UP_ELIGIBLE_SOURCE_KINDS
        available_targets: list[ChiefOfStaffExecutionRouteTarget] = [
            "task_workflow_draft",
            "approval_workflow_draft",
        ]
        if follow_up_applicable:
            available_targets.append("follow_up_draft_only")

        routed_targets: list[ChiefOfStaffExecutionRouteTarget] = []
        for route_target in CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER:
            if route_target not in available_targets:
                continue
            transition = latest_by_item_target.get((handoff_item_id, route_target))
            if transition is not None and transition["route_state"]:
                routed_targets.append(route_target)

        task_routed = "task_workflow_draft" in routed_targets
        approval_routed = "approval_workflow_draft" in routed_targets
        follow_up_routed = "follow_up_draft_only" in routed_targets
        task_routed_count += int(task_routed)
        approval_routed_count += int(approval_routed)
        follow_up_routed_count += int(follow_up_routed)

        routed_item: ChiefOfStaffRoutedHandoffItemRecord = {
            "handoff_rank": handoff_item["rank"],
            "handoff_item_id": handoff_item_id,
            "title": handoff_item["title"],
            "source_kind": handoff_item["source_kind"],
            "recommendation_action": handoff_item["recommendation_action"],
            "route_target_order": list(CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER),
            "available_route_targets": available_targets,
            "routed_targets": routed_targets,
            "is_routed": len(routed_targets) > 0,
            "task_workflow_draft_routed": task_routed,
            "approval_workflow_draft_routed": approval_routed,
            "follow_up_draft_only_routed": follow_up_routed,
            "follow_up_draft_only_applicable": follow_up_applicable,
            "task_draft": handoff_item["task_draft"],
            "approval_draft": handoff_item["approval_draft"],
            "last_routing_transition": latest_by_item.get(handoff_item_id),
        }
        if follow_up_applicable:
            routed_item["follow_up_draft"] = draft_follow_up
        routed_handoff_items.append(routed_item)

    routed_handoff_count = sum(1 for item in routed_handoff_items if item["is_routed"])
    execution_routing_summary: ChiefOfStaffExecutionRoutingSummary = {
        "total_handoff_count": len(routed_handoff_items),
        "routed_handoff_count": routed_handoff_count,
        "unrouted_handoff_count": len(routed_handoff_items) - routed_handoff_count,
        "task_workflow_draft_count": task_routed_count,
        "approval_workflow_draft_count": approval_routed_count,
        "follow_up_draft_only_count": follow_up_routed_count,
        "route_target_order": list(CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER),
        "routed_item_order": list(CHIEF_OF_STAFF_EXECUTION_ROUTED_ITEM_ORDER),
        "audit_order": list(CHIEF_OF_STAFF_EXECUTION_ROUTING_AUDIT_ORDER),
        "transition_order": list(CHIEF_OF_STAFF_EXECUTION_ROUTING_TRANSITIONS),
        "approval_required": execution_posture["approval_required"],
        "non_autonomous_guarantee": execution_posture["non_autonomous_guarantee"],
        "reason": (
            "Routing transitions are explicit and auditable; task/approval/follow-up routes remain "
            "draft-only until separately submitted through governed workflows."
        ),
    }
    execution_readiness_posture = _build_execution_readiness_posture(
        execution_posture=execution_posture,
    )
    return execution_routing_summary, routed_handoff_items, execution_readiness_posture


def _handoff_queue_item_sort_key(
    item: ChiefOfStaffHandoffQueueItem,
) -> tuple[int, float, str]:
    return (
        item["handoff_rank"],
        -item["score"],
        item["handoff_item_id"],
    )


def _build_handoff_queue(
    *,
    store: ContinuityStore,
    handoff_items: list[ChiefOfStaffActionHandoffItem],
    recall_items: list[ContinuityRecallResultRecord],
    all_follow_through_items: list[ChiefOfStaffFollowThroughItem],
    handoff_review_actions: list[ChiefOfStaffHandoffReviewActionRecord],
) -> tuple[ChiefOfStaffHandoffQueueSummary, ChiefOfStaffHandoffQueueGroups]:
    source_status_by_id: dict[str, str] = {}
    source_created_at_by_id: dict[str, datetime] = {}
    for item in recall_items:
        source_status_by_id[item["id"]] = item["status"]
        parsed_created_at = _parse_timestamp_optional(item["created_at"])
        if parsed_created_at is not None:
            source_created_at_by_id[item["id"]] = parsed_created_at

    latest_source_created_at = (
        max(source_created_at_by_id.values())
        if source_created_at_by_id
        else None
    )

    follow_through_by_id = {
        item["id"]: item
        for item in all_follow_through_items
    }
    pending_approval_ids, executed_ids = _build_governed_handoff_state_maps(store=store)

    latest_review_action_by_handoff_item_id: dict[str, ChiefOfStaffHandoffReviewActionRecord] = {}
    for action in handoff_review_actions:
        handoff_item_id = action["handoff_item_id"]
        if handoff_item_id not in latest_review_action_by_handoff_item_id:
            latest_review_action_by_handoff_item_id[handoff_item_id] = action

    grouped_items: dict[ChiefOfStaffHandoffQueueLifecycleState, list[ChiefOfStaffHandoffQueueItem]] = {
        "ready": [],
        "pending_approval": [],
        "executed": [],
        "stale": [],
        "expired": [],
    }
    for handoff_item in handoff_items:
        (
            inferred_state,
            inferred_reason,
            age_hours,
        ) = _infer_handoff_queue_state(
            handoff_item=handoff_item,
            pending_approval_ids=pending_approval_ids,
            executed_ids=executed_ids,
            source_status_by_id=source_status_by_id,
            source_created_at_by_id=source_created_at_by_id,
            latest_source_created_at=latest_source_created_at,
            follow_through_by_id=follow_through_by_id,
        )

        state = inferred_state
        state_reason = inferred_reason
        last_review_action = latest_review_action_by_handoff_item_id.get(handoff_item["handoff_item_id"])
        if last_review_action is not None:
            state = last_review_action["next_lifecycle_state"]
            state_reason = (
                f"Latest operator review action '{last_review_action['review_action']}' "
                f"set lifecycle state to '{state}'."
            )

        queue_item: ChiefOfStaffHandoffQueueItem = {
            "queue_rank": 0,
            "handoff_rank": handoff_item["rank"],
            "handoff_item_id": handoff_item["handoff_item_id"],
            "lifecycle_state": state,
            "state_reason": state_reason,
            "source_kind": handoff_item["source_kind"],
            "source_reference_id": handoff_item["source_reference_id"],
            "title": handoff_item["title"],
            "recommendation_action": handoff_item["recommendation_action"],
            "priority_posture": handoff_item["priority_posture"],
            "confidence_posture": handoff_item["confidence_posture"],
            "score": handoff_item["score"],
            "age_hours_relative_to_latest": age_hours,
            "review_action_order": list(CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS),
            "available_review_actions": _available_handoff_review_actions(state),
            "last_review_action": last_review_action,
            "provenance_references": handoff_item["provenance_references"],
        }
        grouped_items[state].append(queue_item)

    queue_rank = 1
    for lifecycle_state in CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER:
        items = sorted(grouped_items[lifecycle_state], key=_handoff_queue_item_sort_key)
        for item in items:
            item["queue_rank"] = queue_rank
            queue_rank += 1
        grouped_items[lifecycle_state] = items

    handoff_queue_summary: ChiefOfStaffHandoffQueueSummary = {
        "total_count": len(handoff_items),
        "ready_count": len(grouped_items["ready"]),
        "pending_approval_count": len(grouped_items["pending_approval"]),
        "executed_count": len(grouped_items["executed"]),
        "stale_count": len(grouped_items["stale"]),
        "expired_count": len(grouped_items["expired"]),
        "state_order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER),
        "group_order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER),
        "item_order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER),
        "review_action_order": list(CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS),
    }
    handoff_queue_groups: ChiefOfStaffHandoffQueueGroups = {
        "ready": {
            "items": grouped_items["ready"],
            "summary": {
                "lifecycle_state": "ready",
                "returned_count": len(grouped_items["ready"]),
                "total_count": len(grouped_items["ready"]),
                "order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER),
            },
            "empty_state": {
                "is_empty": len(grouped_items["ready"]) == 0,
                "message": _HANDOFF_QUEUE_STATE_EMPTY_MESSAGE["ready"],
            },
        },
        "pending_approval": {
            "items": grouped_items["pending_approval"],
            "summary": {
                "lifecycle_state": "pending_approval",
                "returned_count": len(grouped_items["pending_approval"]),
                "total_count": len(grouped_items["pending_approval"]),
                "order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER),
            },
            "empty_state": {
                "is_empty": len(grouped_items["pending_approval"]) == 0,
                "message": _HANDOFF_QUEUE_STATE_EMPTY_MESSAGE["pending_approval"],
            },
        },
        "executed": {
            "items": grouped_items["executed"],
            "summary": {
                "lifecycle_state": "executed",
                "returned_count": len(grouped_items["executed"]),
                "total_count": len(grouped_items["executed"]),
                "order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER),
            },
            "empty_state": {
                "is_empty": len(grouped_items["executed"]) == 0,
                "message": _HANDOFF_QUEUE_STATE_EMPTY_MESSAGE["executed"],
            },
        },
        "stale": {
            "items": grouped_items["stale"],
            "summary": {
                "lifecycle_state": "stale",
                "returned_count": len(grouped_items["stale"]),
                "total_count": len(grouped_items["stale"]),
                "order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER),
            },
            "empty_state": {
                "is_empty": len(grouped_items["stale"]) == 0,
                "message": _HANDOFF_QUEUE_STATE_EMPTY_MESSAGE["stale"],
            },
        },
        "expired": {
            "items": grouped_items["expired"],
            "summary": {
                "lifecycle_state": "expired",
                "returned_count": len(grouped_items["expired"]),
                "total_count": len(grouped_items["expired"]),
                "order": list(CHIEF_OF_STAFF_HANDOFF_QUEUE_ITEM_ORDER),
            },
            "empty_state": {
                "is_empty": len(grouped_items["expired"]) == 0,
                "message": _HANDOFF_QUEUE_STATE_EMPTY_MESSAGE["expired"],
            },
        },
    }
    return handoff_queue_summary, handoff_queue_groups


def _flatten_handoff_queue_items(
    *,
    handoff_queue_groups: ChiefOfStaffHandoffQueueGroups,
) -> list[ChiefOfStaffHandoffQueueItem]:
    items: list[ChiefOfStaffHandoffQueueItem] = []
    for lifecycle_state in CHIEF_OF_STAFF_HANDOFF_QUEUE_STATE_ORDER:
        items.extend(handoff_queue_groups[lifecycle_state]["items"])
    return items


def _normalize_handoff_review_action(
    review_action: str,
) -> ChiefOfStaffHandoffReviewAction | None:
    if review_action not in CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS:
        return None
    return review_action  # type: ignore[return-value]


def _normalize_execution_route_target(
    route_target: str,
) -> ChiefOfStaffExecutionRouteTarget | None:
    if route_target not in CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER:
        return None
    return route_target  # type: ignore[return-value]


def capture_chief_of_staff_recommendation_outcome(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ChiefOfStaffRecommendationOutcomeCaptureInput,
) -> ChiefOfStaffRecommendationOutcomeCaptureResponse:
    outcome = request.outcome
    if outcome not in CHIEF_OF_STAFF_RECOMMENDATION_OUTCOMES:
        allowed = ", ".join(CHIEF_OF_STAFF_RECOMMENDATION_OUTCOMES)
        raise ChiefOfStaffValidationError(f"outcome must be one of: {allowed}")

    recommendation_action_type = request.recommendation_action_type
    if recommendation_action_type not in CHIEF_OF_STAFF_RECOMMENDED_ACTION_TYPES:
        allowed = ", ".join(CHIEF_OF_STAFF_RECOMMENDED_ACTION_TYPES)
        raise ChiefOfStaffValidationError(f"recommendation_action_type must be one of: {allowed}")

    recommendation_title = _normalize_optional_text(request.recommendation_title)
    if recommendation_title is None:
        raise ChiefOfStaffValidationError("recommendation_title must not be empty")

    rationale = _normalize_optional_text(request.rationale)
    rewritten_title = _normalize_optional_text(request.rewritten_title)
    if outcome == "rewrite" and rewritten_title is None:
        raise ChiefOfStaffValidationError("rewritten_title is required when outcome is rewrite")
    if outcome != "rewrite" and rewritten_title is not None:
        raise ChiefOfStaffValidationError("rewritten_title can only be provided when outcome is rewrite")

    capture_event = store.create_continuity_capture_event(
        raw_content=f"Chief-of-staff recommendation outcome ({outcome}): {recommendation_title}",
        explicit_signal="note",
        admission_posture="TRIAGE",
        admission_reason="chief_of_staff_recommendation_outcome",
    )

    target_priority_id = None if request.target_priority_id is None else str(request.target_priority_id)
    thread_id = None if request.thread_id is None else str(request.thread_id)
    task_id = None if request.task_id is None else str(request.task_id)
    project = _normalize_optional_text(request.project)
    person = _normalize_optional_text(request.person)

    body: dict[str, object] = {
        "kind": _OUTCOME_BODY_KIND,
        "outcome": outcome,
        "recommendation_action_type": recommendation_action_type,
        "recommendation_title": recommendation_title,
        "target_priority_id": target_priority_id,
        "rationale": rationale,
        "rewritten_title": rewritten_title,
    }
    provenance: dict[str, object] = {
        "thread_id": thread_id,
        "task_id": task_id,
        "project": project,
        "person": person,
        "source_event_ids": [str(capture_event["id"])],
        "chief_of_staff_recommendation_outcome": {
            "outcome": outcome,
            "recommendation_action_type": recommendation_action_type,
            "target_priority_id": target_priority_id,
        },
    }

    stored = store.create_continuity_object(
        capture_event_id=capture_event["id"],
        object_type="Note",
        status="active",
        title=f"Recommendation outcome: {outcome} -> {recommendation_title}",
        body=body,
        provenance=provenance,
        confidence=1.0,
    )

    scope_request = ChiefOfStaffPriorityBriefRequestInput(
        thread_id=request.thread_id,
        task_id=request.task_id,
        project=project,
        person=person,
        limit=DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    )
    brief_payload = compile_chief_of_staff_priority_brief(
        store,
        user_id=user_id,
        request=scope_request,
    )["brief"]

    serialized_outcome: ChiefOfStaffRecommendationOutcomeRecord = {
        "id": str(stored["id"]),
        "capture_event_id": str(stored["capture_event_id"]),
        "outcome": outcome,
        "recommendation_action_type": recommendation_action_type,
        "recommendation_title": recommendation_title,
        "rewritten_title": rewritten_title,
        "target_priority_id": target_priority_id,
        "rationale": rationale,
        "provenance_references": [
            {
                "source_kind": "continuity_capture_event",
                "source_id": str(capture_event["id"]),
            }
        ],
        "created_at": stored["created_at"].isoformat(),
        "updated_at": stored["updated_at"].isoformat(),
    }

    return {
        "outcome": serialized_outcome,
        "recommendation_outcomes": brief_payload["recommendation_outcomes"],
        "priority_learning_summary": brief_payload["priority_learning_summary"],
        "pattern_drift_summary": brief_payload["pattern_drift_summary"],
    }


def capture_chief_of_staff_handoff_review_action(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ChiefOfStaffHandoffReviewActionInput,
) -> ChiefOfStaffHandoffReviewActionCaptureResponse:
    handoff_item_id = _normalize_optional_text(request.handoff_item_id)
    if handoff_item_id is None:
        raise ChiefOfStaffValidationError("handoff_item_id must not be empty")

    review_action = _normalize_handoff_review_action(request.review_action)
    if review_action is None:
        allowed = ", ".join(CHIEF_OF_STAFF_HANDOFF_REVIEW_ACTIONS)
        raise ChiefOfStaffValidationError(f"review_action must be one of: {allowed}")

    note = _normalize_optional_text(request.note)
    project = _normalize_optional_text(request.project)
    person = _normalize_optional_text(request.person)
    scope_request = ChiefOfStaffPriorityBriefRequestInput(
        thread_id=request.thread_id,
        task_id=request.task_id,
        project=project,
        person=person,
        limit=MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    )
    scoped_brief = compile_chief_of_staff_priority_brief(
        store,
        user_id=user_id,
        request=scope_request,
    )["brief"]
    queue_items = _flatten_handoff_queue_items(
        handoff_queue_groups=scoped_brief["handoff_queue_groups"],
    )
    queue_item = next(
        (item for item in queue_items if item["handoff_item_id"] == handoff_item_id),
        None,
    )
    if queue_item is None:
        raise ChiefOfStaffValidationError(
            f"handoff_item_id '{handoff_item_id}' was not found in the scoped deterministic handoff queue"
        )

    previous_lifecycle_state = queue_item["lifecycle_state"]
    next_lifecycle_state = _HANDOFF_REVIEW_ACTION_TO_STATE[review_action]
    transition_reason = (
        f"Operator review action '{review_action}' moved lifecycle posture from "
        f"'{previous_lifecycle_state}' to '{next_lifecycle_state}'."
    )

    capture_event = store.create_continuity_capture_event(
        raw_content=f"Handoff review action ({review_action}): {handoff_item_id}",
        explicit_signal="note",
        admission_posture="TRIAGE",
        admission_reason="chief_of_staff_handoff_review_action",
    )

    thread_id = None if request.thread_id is None else str(request.thread_id)
    task_id = None if request.task_id is None else str(request.task_id)
    body: dict[str, object] = {
        "kind": _HANDOFF_REVIEW_ACTION_BODY_KIND,
        "handoff_item_id": handoff_item_id,
        "review_action": review_action,
        "previous_lifecycle_state": previous_lifecycle_state,
        "next_lifecycle_state": next_lifecycle_state,
        "reason": transition_reason,
        "note": note,
    }
    provenance: dict[str, object] = {
        "thread_id": thread_id,
        "task_id": task_id,
        "project": project,
        "person": person,
        "source_event_ids": [str(capture_event["id"])],
        "chief_of_staff_handoff_review_action": {
            "handoff_item_id": handoff_item_id,
            "review_action": review_action,
            "previous_lifecycle_state": previous_lifecycle_state,
            "next_lifecycle_state": next_lifecycle_state,
        },
    }

    stored = store.create_continuity_object(
        capture_event_id=capture_event["id"],
        object_type="Note",
        status="active",
        title=f"Handoff review action: {review_action} ({handoff_item_id})",
        body=body,
        provenance=provenance,
        confidence=1.0,
    )

    updated_brief = compile_chief_of_staff_priority_brief(
        store,
        user_id=user_id,
        request=scope_request,
    )["brief"]

    serialized_action: ChiefOfStaffHandoffReviewActionRecord = {
        "id": str(stored["id"]),
        "capture_event_id": str(stored["capture_event_id"]),
        "handoff_item_id": handoff_item_id,
        "review_action": review_action,
        "previous_lifecycle_state": previous_lifecycle_state,
        "next_lifecycle_state": next_lifecycle_state,
        "reason": transition_reason,
        "note": note,
        "provenance_references": [
            {
                "source_kind": "continuity_capture_event",
                "source_id": str(capture_event["id"]),
            }
        ],
        "created_at": stored["created_at"].isoformat(),
        "updated_at": stored["updated_at"].isoformat(),
    }

    review_actions = list(updated_brief["handoff_review_actions"])
    if not any(action["id"] == serialized_action["id"] for action in review_actions):
        review_actions.insert(0, serialized_action)

    return {
        "review_action": serialized_action,
        "handoff_queue_summary": updated_brief["handoff_queue_summary"],
        "handoff_queue_groups": updated_brief["handoff_queue_groups"],
        "handoff_review_actions": review_actions,
    }


def capture_chief_of_staff_execution_routing_action(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ChiefOfStaffExecutionRoutingActionInput,
) -> ChiefOfStaffExecutionRoutingActionCaptureResponse:
    handoff_item_id = _normalize_optional_text(request.handoff_item_id)
    if handoff_item_id is None:
        raise ChiefOfStaffValidationError("handoff_item_id must not be empty")

    route_target = _normalize_execution_route_target(request.route_target)
    if route_target is None:
        allowed = ", ".join(CHIEF_OF_STAFF_EXECUTION_ROUTE_TARGET_ORDER)
        raise ChiefOfStaffValidationError(f"route_target must be one of: {allowed}")

    note = _normalize_optional_text(request.note)
    project = _normalize_optional_text(request.project)
    person = _normalize_optional_text(request.person)
    scope_request = ChiefOfStaffPriorityBriefRequestInput(
        thread_id=request.thread_id,
        task_id=request.task_id,
        project=project,
        person=person,
        limit=MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    )
    scoped_brief = compile_chief_of_staff_priority_brief(
        store,
        user_id=user_id,
        request=scope_request,
    )["brief"]
    routed_item = next(
        (
            item
            for item in scoped_brief["routed_handoff_items"]
            if item["handoff_item_id"] == handoff_item_id
        ),
        None,
    )
    if routed_item is None:
        raise ChiefOfStaffValidationError(
            f"handoff_item_id '{handoff_item_id}' was not found in the scoped deterministic routing list"
        )
    if route_target not in routed_item["available_route_targets"]:
        allowed = ", ".join(routed_item["available_route_targets"])
        raise ChiefOfStaffValidationError(
            f"route_target '{route_target}' is not applicable for handoff_item_id '{handoff_item_id}'. "
            f"Allowed targets: {allowed}"
        )

    previously_routed = route_target in routed_item["routed_targets"]
    transition: ChiefOfStaffExecutionRoutingTransition = "reaffirmed" if previously_routed else "routed"
    transition_reason = (
        f"Operator routed handoff '{handoff_item_id}' to '{route_target}' as governed draft-only execution prep; "
        "explicit approval is still required before any execution."
    )

    capture_event = store.create_continuity_capture_event(
        raw_content=f"Execution routing action ({route_target}): {handoff_item_id}",
        explicit_signal="note",
        admission_posture="TRIAGE",
        admission_reason="chief_of_staff_execution_routing_action",
    )

    thread_id = None if request.thread_id is None else str(request.thread_id)
    task_id = None if request.task_id is None else str(request.task_id)
    body: dict[str, object] = {
        "kind": _EXECUTION_ROUTING_ACTION_BODY_KIND,
        "handoff_item_id": handoff_item_id,
        "route_target": route_target,
        "transition": transition,
        "previously_routed": previously_routed,
        "route_state": True,
        "reason": transition_reason,
        "note": note,
    }
    provenance: dict[str, object] = {
        "thread_id": thread_id,
        "task_id": task_id,
        "project": project,
        "person": person,
        "source_event_ids": [str(capture_event["id"])],
        "chief_of_staff_execution_routing_action": {
            "handoff_item_id": handoff_item_id,
            "route_target": route_target,
            "transition": transition,
            "previously_routed": previously_routed,
        },
    }

    stored = store.create_continuity_object(
        capture_event_id=capture_event["id"],
        object_type="Note",
        status="active",
        title=f"Execution routing action: {route_target} ({handoff_item_id})",
        body=body,
        provenance=provenance,
        confidence=1.0,
    )

    updated_brief = compile_chief_of_staff_priority_brief(
        store,
        user_id=user_id,
        request=scope_request,
    )["brief"]

    serialized_action: ChiefOfStaffExecutionRoutingAuditRecord = {
        "id": str(stored["id"]),
        "capture_event_id": str(stored["capture_event_id"]),
        "handoff_item_id": handoff_item_id,
        "route_target": route_target,
        "transition": transition,
        "previously_routed": previously_routed,
        "route_state": True,
        "reason": transition_reason,
        "note": note,
        "provenance_references": [
            {
                "source_kind": "continuity_capture_event",
                "source_id": str(capture_event["id"]),
            }
        ],
        "created_at": stored["created_at"].isoformat(),
        "updated_at": stored["updated_at"].isoformat(),
    }

    routing_audit_trail = list(updated_brief["routing_audit_trail"])
    if not any(action["id"] == serialized_action["id"] for action in routing_audit_trail):
        routing_audit_trail.insert(0, serialized_action)

    return {
        "routing_action": serialized_action,
        "execution_routing_summary": updated_brief["execution_routing_summary"],
        "routed_handoff_items": updated_brief["routed_handoff_items"],
        "routing_audit_trail": routing_audit_trail,
        "execution_readiness_posture": updated_brief["execution_readiness_posture"],
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
    weekly_review = compile_continuity_weekly_review(
        store,
        user_id=user_id,
        request=ContinuityWeeklyReviewRequestInput(
            query=normalized_request.query,
            thread_id=normalized_request.thread_id,
            task_id=normalized_request.task_id,
            project=normalized_request.project,
            person=normalized_request.person,
            since=normalized_request.since,
            until=normalized_request.until,
            limit=min(normalized_request.limit, MAX_CONTINUITY_WEEKLY_REVIEW_LIMIT),
        ),
    )["review"]

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
    recent_changes_items = resumption_brief.get("recent_changes", {}).get("items", [])  # type: ignore[call-overload]
    open_loop_items = resumption_brief.get("open_loops", {}).get("items", [])  # type: ignore[call-overload]
    resumption_last_decision_item = resumption_brief.get("last_decision", {}).get("item")  # type: ignore[call-overload]
    resumption_next_action_item = resumption_brief.get("next_action", {}).get("item")  # type: ignore[call-overload]

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
        for index, item in enumerate(recent_changes_items)
    }
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
    top_ranked_priority = ranked_items[0] if ranked_items else None
    preparation_brief = _build_preparation_brief(
        recall_items=recall_payload["items"],
        scope=recall_payload["summary"]["filters"],
        last_decision=resumption_last_decision_item,
        open_loops=open_loop_items,
        next_action=resumption_next_action_item,
        confidence_posture=trust_cap.posture,
        confidence_reason=trust_cap.reason,
    )
    what_changed_summary = _build_what_changed_summary(
        recent_changes=recent_changes_items,
        confidence_posture=trust_cap.posture,
        confidence_reason=trust_cap.reason,
    )
    prep_checklist = _build_prep_checklist(
        last_decision=resumption_last_decision_item,
        open_loops=open_loop_items,
        next_action=resumption_next_action_item,
        confidence_posture=trust_cap.posture,
        confidence_reason=trust_cap.reason,
    )
    suggested_talking_points = _build_suggested_talking_points(
        last_decision=resumption_last_decision_item,
        top_ranked_priority=top_ranked_priority,
        open_loops=open_loop_items,
        confidence_posture=trust_cap.posture,
        confidence_reason=trust_cap.reason,
    )
    resumption_supervision = _build_resumption_supervision(
        recommended_next_action=recommended_next_action,
        follow_through_items=all_follow_through_items,
        trust_cap=trust_cap,
    )
    weekly_review_brief = _build_weekly_review_brief(
        scope=weekly_review["scope"],
        weekly_rollup=weekly_review["rollup"],
        follow_through_items=all_follow_through_items,
    )
    all_outcome_items = _list_recommendation_outcome_records(recall_payload["items"])
    recommendation_outcomes = _build_recommendation_outcome_section(
        all_outcome_items=all_outcome_items,
        limit=min(limit, _OUTCOME_HISTORY_LIMIT),
    )
    priority_learning_summary = _build_priority_learning_summary(
        all_outcome_items=all_outcome_items,
    )
    pattern_drift_summary = _build_pattern_drift_summary(
        learning_summary=priority_learning_summary,
    )
    (
        action_handoff_brief,
        handoff_items,
        task_draft,
        approval_draft,
        execution_posture,
    ) = _build_action_handoff_artifacts(
        recommended_next_action=recommended_next_action,
        all_follow_through_items=all_follow_through_items,
        prep_checklist=prep_checklist,
        weekly_review_brief=weekly_review_brief,
        trust_cap=trust_cap,
        scope=recall_payload["summary"]["filters"],
    )
    handoff_review_actions = _list_handoff_review_action_records(recall_payload["items"])
    handoff_queue_summary, handoff_queue_groups = _build_handoff_queue(
        store=store,
        handoff_items=handoff_items,
        recall_items=recall_payload["items"],
        all_follow_through_items=all_follow_through_items,
        handoff_review_actions=handoff_review_actions,
    )
    routing_audit_trail = _list_execution_routing_audit_records(recall_payload["items"])
    (
        execution_routing_summary,
        routed_handoff_items,
        execution_readiness_posture,
    ) = _build_execution_routing_artifacts(
        handoff_items=handoff_items,
        routing_audit_trail=routing_audit_trail,
        draft_follow_up=draft_follow_up,
        execution_posture=execution_posture,
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
        "handoff_item_count": len(handoff_items),
        "handoff_item_order": list(CHIEF_OF_STAFF_ACTION_HANDOFF_ITEM_ORDER),
        "execution_posture_order": list(CHIEF_OF_STAFF_EXECUTION_POSTURE_ORDER),
        "handoff_queue_total_count": handoff_queue_summary["total_count"],
        "handoff_queue_ready_count": handoff_queue_summary["ready_count"],
        "handoff_queue_pending_approval_count": handoff_queue_summary["pending_approval_count"],
        "handoff_queue_executed_count": handoff_queue_summary["executed_count"],
        "handoff_queue_stale_count": handoff_queue_summary["stale_count"],
        "handoff_queue_expired_count": handoff_queue_summary["expired_count"],
        "handoff_queue_state_order": list(handoff_queue_summary["state_order"]),
        "handoff_queue_group_order": list(handoff_queue_summary["group_order"]),
        "handoff_queue_item_order": list(handoff_queue_summary["item_order"]),
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
        "preparation_brief": preparation_brief,
        "what_changed_summary": what_changed_summary,
        "prep_checklist": prep_checklist,
        "suggested_talking_points": suggested_talking_points,
        "resumption_supervision": resumption_supervision,
        "weekly_review_brief": weekly_review_brief,
        "recommendation_outcomes": recommendation_outcomes,
        "priority_learning_summary": priority_learning_summary,
        "pattern_drift_summary": pattern_drift_summary,
        "action_handoff_brief": action_handoff_brief,
        "handoff_items": handoff_items,
        "handoff_queue_summary": handoff_queue_summary,
        "handoff_queue_groups": handoff_queue_groups,
        "handoff_review_actions": handoff_review_actions,
        "execution_routing_summary": execution_routing_summary,
        "routed_handoff_items": routed_handoff_items,
        "routing_audit_trail": routing_audit_trail,
        "execution_readiness_posture": execution_readiness_posture,
        "task_draft": task_draft,
        "approval_draft": approval_draft,
        "execution_posture": execution_posture,
        "summary": summary,
        "sources": [
            "continuity_recall",
            "continuity_open_loops",
            "continuity_weekly_review",
            "continuity_resumption_brief",
            "chief_of_staff_recommendation_outcomes",
            "chief_of_staff_action_handoff",
            "chief_of_staff_handoff_queue",
            "chief_of_staff_handoff_review_actions",
            "chief_of_staff_execution_routing",
            "memory_trust_dashboard",
            "memories",
            "memory_review_labels",
        ],
    }

    return {"brief": brief}


def build_default_chief_of_staff_priority_request() -> ChiefOfStaffPriorityBriefRequestInput:
    return ChiefOfStaffPriorityBriefRequestInput(limit=DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT)
