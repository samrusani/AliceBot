from __future__ import annotations

from uuid import UUID

from alicebot_api.continuity_contradictions import list_contradiction_cases
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.contracts import (
    CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0,
    CONTINUITY_BRIEF_TYPE_ORDER,
    CONTRADICTION_CASE_LIST_ORDER,
    DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    DEFAULT_CONTINUITY_REVIEW_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
    MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
    MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    TASK_BRIEF_SECTION_ITEM_ORDER,
    ChiefOfStaffRecommendationConfidencePosture,
    ContinuityBriefConflictSection,
    ContinuityBriefConflictSummary,
    ContinuityBriefProvenanceBundle,
    ContinuityBriefProvenanceSummary,
    ContinuityBriefRecord,
    ContinuityBriefRelevantFactsSection,
    ContinuityBriefRelevantFactsSummary,
    ContinuityBriefRequestInput,
    ContinuityBriefResponse,
    ContinuityBriefSelectionStrategyRecord,
    ContinuityBriefSuggestedActionRecord,
    ContinuityBriefTimelineHighlightRecord,
    ContinuityBriefTimelineSection,
    ContinuityBriefTrustPostureRecord,
    ContinuityRecallProvenancePosture,
    ContinuityRecallProvenanceReference,
    ContinuityRecallResultRecord,
    ContinuityResumptionBriefRequestInput,
    ContinuityResumptionEmptyState,
    ContinuityResumptionListSection,
    ContradictionCaseListQueryInput,
    ContradictionCaseRecord,
    MemoryTrustClass,
    TaskBriefCompileRequestInput,
    TaskBriefMode,
    TrustSignalListQueryInput,
    TrustSignalRecord,
)
from alicebot_api.store import ContinuityStore
from alicebot_api.task_briefing import compile_task_brief_record


class ContinuityBriefValidationError(ValueError):
    """Raised when a continuity brief request is invalid."""


_BRIEF_TYPE_TO_MODE: dict[str, tuple[TaskBriefMode, str | None]] = {
    "general": ("user_recall", None),
    "resume": ("resume", None),
    "agent_handoff": ("agent_handoff", None),
    "coding_context": ("worker_subtask", "compact"),
    "operator_context": ("agent_handoff", "detailed"),
}
_TRUST_CLASS_RANK: dict[MemoryTrustClass, int] = {
    "human_curated": 4,
    "deterministic": 3,
    "llm_corroborated": 2,
    "llm_single_source": 1,
}
_PROVENANCE_RANK: dict[ContinuityRecallProvenancePosture, int] = {
    "strong": 3,
    "partial": 2,
    "weak": 1,
    "missing": 0,
}
_SOURCE_PRECEDENCE = {
    "recent_changes": 0,
    "open_loops": 1,
    "relevant_facts": 2,
    "next_suggested_action": 3,
}


def _build_empty_state(*, is_empty: bool, message: str) -> ContinuityResumptionEmptyState:
    return {
        "is_empty": is_empty,
        "message": message,
    }


def _dedupe_items(items: list[ContinuityRecallResultRecord]) -> list[ContinuityRecallResultRecord]:
    deduped: list[ContinuityRecallResultRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        deduped.append(item)
    return deduped


def _recency_sort_key(item: ContinuityRecallResultRecord) -> tuple[str, str]:
    return (item["created_at"], item["id"])


def _validate_request(request: ContinuityBriefRequestInput) -> None:
    if request.brief_type not in CONTINUITY_BRIEF_TYPE_ORDER:
        raise ContinuityBriefValidationError(
            "brief_type must be one of: " + ", ".join(CONTINUITY_BRIEF_TYPE_ORDER)
        )
    if request.max_relevant_facts < 0 or request.max_relevant_facts > MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT:
        raise ContinuityBriefValidationError(
            "max_relevant_facts must be between "
            f"0 and {MAX_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT}"
        )
    if request.max_recent_changes < 0 or request.max_recent_changes > MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT:
        raise ContinuityBriefValidationError(
            "max_recent_changes must be between "
            f"0 and {MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT}"
        )
    if request.max_open_loops < 0 or request.max_open_loops > MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT:
        raise ContinuityBriefValidationError(
            "max_open_loops must be between "
            f"0 and {MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT}"
        )
    if request.max_conflicts < 0 or request.max_conflicts > MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT:
        raise ContinuityBriefValidationError(
            f"max_conflicts must be between 0 and {MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT}"
        )
    if request.max_timeline_highlights < 0 or request.max_timeline_highlights > MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT:
        raise ContinuityBriefValidationError(
            "max_timeline_highlights must be between "
            f"0 and {MAX_CONTINUITY_BRIEF_TIMELINE_LIMIT}"
        )
    if request.since is not None and request.until is not None and request.until < request.since:
        raise ContinuityBriefValidationError("until must be greater than or equal to since")


def _task_brief_request_for(request: ContinuityBriefRequestInput) -> TaskBriefCompileRequestInput:
    task_brief_mode, model_pack_strategy = _BRIEF_TYPE_TO_MODE[request.brief_type]
    return TaskBriefCompileRequestInput(
        mode=task_brief_mode,
        query=request.query,
        thread_id=request.thread_id,
        task_id=request.task_id,
        project=request.project,
        person=request.person,
        since=request.since,
        until=request.until,
        include_non_promotable_facts=request.include_non_promotable_facts,
        provider_strategy=f"continuity_brief.{request.brief_type}",
        model_pack_strategy=model_pack_strategy,
    )


def _build_relevant_facts_section(
    *,
    task_brief_mode: TaskBriefMode,
    candidates: list[ContinuityRecallResultRecord],
    limit: int,
) -> ContinuityBriefRelevantFactsSection:
    items = candidates[:limit] if limit > 0 else []
    summary: ContinuityBriefRelevantFactsSummary = {
        "limit": limit,
        "returned_count": len(items),
        "total_count": len(candidates),
        "order": list(TASK_BRIEF_SECTION_ITEM_ORDER),
        "task_brief_mode": task_brief_mode,
    }
    return {
        "items": items,
        "summary": summary,
        "empty_state": _build_empty_state(
            is_empty=len(items) == 0,
            message="No relevant facts found in the requested scope.",
        ),
    }


def _collect_open_conflict_ids(items: list[ContinuityRecallResultRecord]) -> list[str]:
    seen: set[str] = set()
    collected: list[str] = []
    for item in items:
        contradictions = item["explanation"]["contradictions"]
        for case_id in contradictions["open_case_ids"]:
            if case_id in seen:
                continue
            seen.add(case_id)
            collected.append(case_id)
    return collected


def _build_conflict_section(
    store: ContinuityStore,
    *,
    user_id: UUID,
    items: list[ContinuityRecallResultRecord],
    limit: int,
) -> ContinuityBriefConflictSection:
    open_case_ids = _collect_open_conflict_ids(items)
    if limit <= 0 or len(open_case_ids) == 0:
        empty_summary: ContinuityBriefConflictSummary = {
            "limit": limit,
            "returned_count": 0,
            "total_count": len(open_case_ids),
            "order": list(CONTRADICTION_CASE_LIST_ORDER),
        }
        return {
            "items": [],
            "summary": empty_summary,
            "empty_state": _build_empty_state(
                is_empty=True,
                message="No open conflicts found in the requested scope.",
            ),
        }

    seen_case_ids: set[str] = set()
    gathered: list[ContradictionCaseRecord] = []
    for item in items:
        contradiction_payload = list_contradiction_cases(
            store,
            user_id=user_id,
            request=ContradictionCaseListQueryInput(
                status="open",
                limit=MAX_CONTINUITY_BRIEF_CONFLICT_LIMIT,
                continuity_object_id=UUID(item["id"]),
            ),
        )
        for case in contradiction_payload["items"]:
            if case["id"] in seen_case_ids:
                continue
            seen_case_ids.add(case["id"])
            gathered.append(case)

    gathered.sort(key=lambda case: (case["updated_at"], case["id"]), reverse=True)
    limited_items = gathered[:limit]
    summary: ContinuityBriefConflictSummary = {
        "limit": limit,
        "returned_count": len(limited_items),
        "total_count": len(open_case_ids),
        "order": list(CONTRADICTION_CASE_LIST_ORDER),
    }
    return {
        "items": limited_items,
        "summary": summary,
        "empty_state": _build_empty_state(
            is_empty=len(limited_items) == 0,
            message="No open conflicts found in the requested scope.",
        ),
    }


def _build_timeline_section(
    *,
    relevant_facts: list[ContinuityRecallResultRecord],
    recent_changes: ContinuityResumptionListSection,
    open_loops: ContinuityResumptionListSection,
    next_action: ContinuityRecallResultRecord | None,
    limit: int,
) -> ContinuityBriefTimelineSection:
    timeline_candidates: list[tuple[str, ContinuityRecallResultRecord]] = []
    timeline_candidates.extend(("recent_changes", item) for item in recent_changes["items"])
    timeline_candidates.extend(("open_loops", item) for item in open_loops["items"])
    timeline_candidates.extend(("relevant_facts", item) for item in relevant_facts)
    if next_action is not None:
        timeline_candidates.append(("next_suggested_action", next_action))

    by_id: dict[str, tuple[str, ContinuityRecallResultRecord]] = {}
    for source_section, item in timeline_candidates:
        existing = by_id.get(item["id"])
        if existing is None:
            by_id[item["id"]] = (source_section, item)
            continue
        if _SOURCE_PRECEDENCE[source_section] < _SOURCE_PRECEDENCE[existing[0]]:
            by_id[item["id"]] = (source_section, item)

    ordered = sorted(
        by_id.values(),
        key=lambda candidate: (candidate[1]["created_at"], candidate[1]["id"]),
        reverse=True,
    )
    limited = ordered[:limit] if limit > 0 else []
    items: list[ContinuityBriefTimelineHighlightRecord] = [
        {
            "continuity_object_id": item["id"],
            "title": item["title"],
            "object_type": item["object_type"],
            "status": item["status"],
            "created_at": item["created_at"],
            "source_section": source_section,
        }
        for source_section, item in limited
    ]
    return {
        "items": items,
        "summary": {
            "limit": limit,
            "returned_count": len(items),
            "total_count": len(ordered),
            "order": ["created_at_desc", "id_desc"],
        },
        "empty_state": _build_empty_state(
            is_empty=len(items) == 0,
            message="No timeline highlights found in the requested scope.",
        ),
    }


def _collect_provenance_bundle(items: list[ContinuityRecallResultRecord]) -> ContinuityBriefProvenanceBundle:
    source_object_ids = sorted({item["id"] for item in items})
    reference_pairs = sorted(
        {
            (reference["source_kind"], reference["source_id"])
            for item in items
            for reference in item["provenance_references"]
        }
    )
    references: list[ContinuityRecallProvenanceReference] = [
        {
            "source_kind": source_kind,
            "source_id": source_id,
        }
        for source_kind, source_id in reference_pairs
    ]
    summary: ContinuityBriefProvenanceSummary = {
        "source_object_count": len(source_object_ids),
        "reference_count": len(references),
        "reference_kind_count": len({reference["source_kind"] for reference in references}),
    }
    return {
        "source_object_ids": source_object_ids,
        "references": references,
        "summary": summary,
    }


def _strongest_trust_class(items: list[ContinuityRecallResultRecord]) -> MemoryTrustClass | None:
    strongest: MemoryTrustClass | None = None
    strongest_rank = -1
    for item in items:
        trust_class = item["ordering"]["trust_class"]
        rank = _TRUST_CLASS_RANK[trust_class]
        if rank > strongest_rank:
            strongest = trust_class
            strongest_rank = rank
    return strongest


def _weakest_provenance_posture(
    items: list[ContinuityRecallResultRecord],
) -> ContinuityRecallProvenancePosture | None:
    weakest: ContinuityRecallProvenancePosture | None = None
    weakest_rank = 99
    for item in items:
        posture = item["ordering"]["provenance_posture"]
        rank = _PROVENANCE_RANK[posture]
        if rank < weakest_rank:
            weakest = posture
            weakest_rank = rank
    return weakest


def _confidence_posture(average_confidence: float) -> ChiefOfStaffRecommendationConfidencePosture:
    if average_confidence >= 0.8:
        return "high"
    if average_confidence >= 0.55:
        return "medium"
    return "low"


def _collect_active_signals(
    store: ContinuityStore,
    *,
    user_id: UUID,
    items: list[ContinuityRecallResultRecord],
) -> list[TrustSignalRecord]:
    seen_signal_ids: set[str] = set()
    gathered: list[TrustSignalRecord] = []
    for item in items:
        payload = list_trust_signals(
            store,
            user_id=user_id,
            request=TrustSignalListQueryInput(
                limit=DEFAULT_CONTINUITY_REVIEW_LIMIT,
                continuity_object_id=UUID(item["id"]),
                signal_state="active",
            ),
            sync_first=True,
        )
        for signal in payload["items"]:
            if signal["id"] in seen_signal_ids:
                continue
            seen_signal_ids.add(signal["id"])
            gathered.append(signal)
    gathered.sort(key=lambda signal: (signal["updated_at"], signal["id"]), reverse=True)
    return gathered


def _build_trust_posture(
    store: ContinuityStore,
    *,
    user_id: UUID,
    items: list[ContinuityRecallResultRecord],
    open_conflict_count: int,
) -> ContinuityBriefTrustPostureRecord:
    if len(items) == 0:
        return {
            "confidence_posture": "low",
            "average_confidence": 0.0,
            "strongest_trust_class": None,
            "weakest_provenance_posture": None,
            "active_signal_count": 0,
            "positive_signal_count": 0,
            "negative_signal_count": 0,
            "neutral_signal_count": 0,
            "open_conflict_count": open_conflict_count,
            "rationale": "No continuity items matched the requested scope.",
        }

    active_signals = _collect_active_signals(
        store,
        user_id=user_id,
        items=items,
    )
    average_confidence = sum(item["confidence"] for item in items) / len(items)
    strongest_trust_class = _strongest_trust_class(items)
    weakest_provenance = _weakest_provenance_posture(items)
    positive_signal_count = sum(1 for signal in active_signals if signal["direction"] == "positive")
    negative_signal_count = sum(1 for signal in active_signals if signal["direction"] == "negative")
    neutral_signal_count = sum(1 for signal in active_signals if signal["direction"] == "neutral")

    posture = _confidence_posture(average_confidence)
    reasons: list[str] = []
    if open_conflict_count > 0:
        reasons.append(f"{open_conflict_count} open conflict(s) remain")
    if negative_signal_count > 0:
        reasons.append(f"{negative_signal_count} negative trust signal(s) are active")
    if weakest_provenance in {"weak", "missing"}:
        reasons.append(f"provenance posture is {weakest_provenance}")

    if posture == "high" and reasons:
        posture = "medium"
    if (
        average_confidence < 0.55
        or open_conflict_count > 1
        or negative_signal_count > 1
        or weakest_provenance == "missing"
    ):
        posture = "low"

    rationale = (
        "; ".join(reasons)
        if reasons
        else "Selected continuity items have consistent trust and provenance signals."
    )
    return {
        "confidence_posture": posture,
        "average_confidence": average_confidence,
        "strongest_trust_class": strongest_trust_class,
        "weakest_provenance_posture": weakest_provenance,
        "active_signal_count": len(active_signals),
        "positive_signal_count": positive_signal_count,
        "negative_signal_count": negative_signal_count,
        "neutral_signal_count": neutral_signal_count,
        "open_conflict_count": open_conflict_count,
        "rationale": rationale,
    }


def _build_next_suggested_action(
    *,
    next_action_item: ContinuityRecallResultRecord | None,
    open_loop_items: list[ContinuityRecallResultRecord],
    relevant_facts: list[ContinuityRecallResultRecord],
    confidence_posture: ChiefOfStaffRecommendationConfidencePosture,
) -> ContinuityBriefSuggestedActionRecord:
    target: ContinuityRecallResultRecord | None = next_action_item
    reason = "Selected explicit next action from continuity resumption."
    if target is None and open_loop_items:
        target = open_loop_items[0]
        reason = "No explicit next action found; selected the highest-priority open loop."
    if target is None and relevant_facts:
        target = relevant_facts[0]
        reason = "No explicit next action or open loop found; selected the top relevant fact."
    if target is None:
        return {
            "continuity_object_id": None,
            "title": "No suggested action available.",
            "object_type": None,
            "reason": "No relevant continuity items matched the requested scope.",
            "confidence_posture": confidence_posture,
            "provenance_references": [],
        }
    return {
        "continuity_object_id": target["id"],
        "title": target["title"],
        "object_type": target["object_type"],
        "reason": reason,
        "confidence_posture": confidence_posture,
        "provenance_references": list(target["provenance_references"]),
    }


def _brief_summary(
    *,
    brief_type: str,
    relevant_facts: ContinuityBriefRelevantFactsSection,
    open_loops: ContinuityResumptionListSection,
    conflicts: ContinuityBriefConflictSection,
    next_action: ContinuityBriefSuggestedActionRecord,
) -> str:
    if relevant_facts["items"]:
        focus = "; ".join(item["title"] for item in relevant_facts["items"][:2])
    else:
        focus = "No relevant facts."
    return (
        f"{brief_type.replace('_', ' ')} brief. "
        f"Focus: {focus} "
        f"Open loops={open_loops['summary']['total_count']}, "
        f"conflicts={conflicts['summary']['total_count']}. "
        f"Next: {next_action['title']}"
    )


def compile_continuity_brief(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ContinuityBriefRequestInput,
) -> ContinuityBriefResponse:
    _validate_request(request)

    task_brief_request = _task_brief_request_for(request)
    task_brief = compile_task_brief_record(
        store,
        user_id=user_id,
        request=task_brief_request,
    )
    relevant_fact_candidates = _dedupe_items(
        [
            item
            for section in task_brief["sections"]
            for item in section["items"]
        ]
    )
    relevant_facts = _build_relevant_facts_section(
        task_brief_mode=task_brief["mode"],
        candidates=relevant_fact_candidates,
        limit=request.max_relevant_facts,
    )

    resumption_payload = compile_continuity_resumption_brief(
        store,
        user_id=user_id,
        request=ContinuityResumptionBriefRequestInput(
            query=request.query,
            thread_id=request.thread_id,
            task_id=request.task_id,
            project=request.project,
            person=request.person,
            since=request.since,
            until=request.until,
            max_recent_changes=request.max_recent_changes,
            max_open_loops=request.max_open_loops,
            include_non_promotable_facts=request.include_non_promotable_facts,
            debug=False,
        ),
    )
    resumption_brief = resumption_payload["brief"]
    included_items = _dedupe_items(
        relevant_facts["items"]
        + list(resumption_brief["recent_changes"]["items"])
        + list(resumption_brief["open_loops"]["items"])
        + (
            []
            if resumption_brief["last_decision"]["item"] is None
            else [resumption_brief["last_decision"]["item"]]
        )
        + (
            []
            if resumption_brief["next_action"]["item"] is None
            else [resumption_brief["next_action"]["item"]]
        )
    )
    conflict_section = _build_conflict_section(
        store,
        user_id=user_id,
        items=included_items,
        limit=request.max_conflicts,
    )
    trust_posture = _build_trust_posture(
        store,
        user_id=user_id,
        items=included_items,
        open_conflict_count=conflict_section["summary"]["total_count"],
    )
    next_suggested_action = _build_next_suggested_action(
        next_action_item=resumption_brief["next_action"]["item"],
        open_loop_items=list(resumption_brief["open_loops"]["items"]),
        relevant_facts=list(relevant_facts["items"]),
        confidence_posture=trust_posture["confidence_posture"],
    )
    timeline_highlights = _build_timeline_section(
        relevant_facts=list(relevant_facts["items"]),
        recent_changes=resumption_brief["recent_changes"],
        open_loops=resumption_brief["open_loops"],
        next_action=resumption_brief["next_action"]["item"],
        limit=request.max_timeline_highlights,
    )
    provenance_bundle = _collect_provenance_bundle(included_items)
    selection_strategy: ContinuityBriefSelectionStrategyRecord = {
        "task_brief_mode": task_brief["mode"],
        "provider_strategy": task_brief["strategy"]["provider_strategy"],
        "model_pack_strategy": task_brief["strategy"]["model_pack_strategy"],
        "token_budget": task_brief["strategy"]["token_budget"],
        "budget_source": task_brief["strategy"]["budget_source"],
    }
    brief: ContinuityBriefRecord = {
        "assembly_version": CONTINUITY_BRIEF_ASSEMBLY_VERSION_V0,
        "brief_type": request.brief_type,
        "scope": resumption_brief["scope"],
        "summary": _brief_summary(
            brief_type=request.brief_type,
            relevant_facts=relevant_facts,
            open_loops=resumption_brief["open_loops"],
            conflicts=conflict_section,
            next_action=next_suggested_action,
        ),
        "selection_strategy": selection_strategy,
        "relevant_facts": relevant_facts,
        "recent_changes": resumption_brief["recent_changes"],
        "open_loops": resumption_brief["open_loops"],
        "conflicts": conflict_section,
        "timeline_highlights": timeline_highlights,
        "next_suggested_action": next_suggested_action,
        "provenance_bundle": provenance_bundle,
        "trust_posture": trust_posture,
        "sources": [
            "continuity_capture_events",
            "continuity_objects",
            "retrieval_runs",
            "contradiction_cases",
            "trust_signals",
            "task_briefs",
        ],
    }
    return {"brief": brief}


def build_default_continuity_brief_request() -> ContinuityBriefRequestInput:
    return ContinuityBriefRequestInput(
        brief_type="general",
        max_relevant_facts=DEFAULT_CONTINUITY_BRIEF_RELEVANT_FACT_LIMIT,
        max_recent_changes=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        max_open_loops=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
        max_conflicts=DEFAULT_CONTINUITY_BRIEF_CONFLICT_LIMIT,
        max_timeline_highlights=DEFAULT_CONTINUITY_BRIEF_TIMELINE_LIMIT,
    )


__all__ = [
    "ContinuityBriefValidationError",
    "build_default_continuity_brief_request",
    "compile_continuity_brief",
]
