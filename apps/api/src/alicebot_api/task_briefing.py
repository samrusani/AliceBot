from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import cast
from uuid import UUID

from alicebot_api.continuity_recall import (
    ContinuityRecallValidationError,
    query_continuity_recall,
)
from alicebot_api.continuity_resumption import (
    ContinuityResumptionValidationError,
    compile_continuity_resumption_brief,
)
from alicebot_api.contracts import (
    DEFAULT_TASK_BRIEF_TOKEN_BUDGET,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_TASK_BRIEF_TOKEN_BUDGET,
    MODEL_PACK_BRIEFING_STRATEGIES,
    TASK_BRIEF_ASSEMBLY_VERSION_V0,
    TASK_BRIEF_COMPARISON_VERSION_V0,
    TASK_BRIEF_MODE_ORDER,
    TASK_BRIEF_SECTION_ITEM_ORDER,
    ContinuityRecallQueryInput,
    ContinuityRecallResultRecord,
    ContinuityRecallScopeFilters,
    ContinuityResumptionBriefRequestInput,
    JsonObject,
    TaskBriefComparisonResponse,
    TaskBriefComparisonStats,
    TaskBriefCompileRequestInput,
    TaskBriefEmptyState,
    TaskBriefRecord,
    TaskBriefResponse,
    TaskBriefSectionRecord,
    TaskBriefSectionSummary,
    TaskBriefStrategyRecord,
    TaskBriefSummary,
)
from alicebot_api.model_packs import (
    ModelPackNotFoundError,
    ModelPackValidationError,
    resolve_workspace_model_pack_selection,
)
from alicebot_api.store import ContinuityStore, TaskBriefRow


class TaskBriefValidationError(ValueError):
    """Raised when a task-brief request is invalid."""


class TaskBriefNotFoundError(LookupError):
    """Raised when a persisted task brief cannot be found."""


@dataclass(frozen=True, slots=True)
class _ModeConfig:
    token_budget: int
    default_model_pack_strategy: str


@dataclass(frozen=True, slots=True)
class _SectionPlan:
    section_key: str
    title: str
    intent: str
    selection_rule: str
    candidates: list[ContinuityRecallResultRecord]
    token_budget: int
    max_items: int


_MODE_CONFIGS: dict[str, _ModeConfig] = {
    "user_recall": _ModeConfig(token_budget=320, default_model_pack_strategy="balanced"),
    "resume": _ModeConfig(token_budget=220, default_model_pack_strategy="balanced"),
    "worker_subtask": _ModeConfig(token_budget=128, default_model_pack_strategy="compact"),
    "agent_handoff": _ModeConfig(token_budget=180, default_model_pack_strategy="balanced"),
}
_MODE_TOKEN_ESTIMATE_MULTIPLIER = {
    "user_recall": 1.2,
    "resume": 1.0,
    "worker_subtask": 0.7,
    "agent_handoff": 0.9,
}
_SECTION_EMPTY_MESSAGES = {
    "top_recall": "No recall items matched the requested scope.",
    "current_objective": "No active decision or next action was found in the requested scope.",
    "active_constraints": "No active blockers, commitments, or waiting-for items were found.",
    "critical_context": "No critical facts were available for this worker brief.",
    "handoff_focus": "No active decision or next action was available for the handoff.",
    "handoff_open_loops": "No active open loops were available for the handoff.",
    "handoff_recent_changes": "No recent changes were available for the handoff.",
    "last_decision": "No decision found in the requested scope.",
    "open_loops": "No open loops found in the requested scope.",
    "recent_changes": "No recent changes found in the requested scope.",
    "next_action": "No next action found in the requested scope.",
}
_STRATEGY_MULTIPLIER = {
    "balanced": 1.0,
    "compact": 0.75,
    "detailed": 1.2,
}


def _validate_request(request: TaskBriefCompileRequestInput) -> None:
    if request.mode not in _MODE_CONFIGS:
        raise TaskBriefValidationError(f"unsupported task brief mode: {request.mode}")
    if request.until is not None and request.since is not None and request.until < request.since:
        raise TaskBriefValidationError("until must be greater than or equal to since")
    if request.token_budget is not None and (
        request.token_budget < 1 or request.token_budget > MAX_TASK_BRIEF_TOKEN_BUDGET
    ):
        raise TaskBriefValidationError(
            f"token_budget must be between 1 and {MAX_TASK_BRIEF_TOKEN_BUDGET}"
        )
    if request.model_pack_strategy is not None and request.model_pack_strategy not in MODEL_PACK_BRIEFING_STRATEGIES:
        raise TaskBriefValidationError(
            "model_pack_strategy must be one of: "
            + ", ".join(MODEL_PACK_BRIEFING_STRATEGIES)
        )
    if request.workspace_id is None and (request.pack_id is not None or request.pack_version is not None):
        raise TaskBriefValidationError("workspace_id is required when resolving model-pack defaults")
    if request.pack_version is not None and request.pack_id is None:
        raise TaskBriefValidationError("pack_id is required when pack_version is provided")


def _estimate_tokens(payload: object) -> int:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return max(1, math.ceil(len(serialized) / 4))


def _estimate_candidate_tokens(item: ContinuityRecallResultRecord) -> int:
    compact_payload = {
        "id": item["id"],
        "object_type": item["object_type"],
        "status": item["status"],
        "title": item["title"],
        "body": item["body"],
        "provenance": item["provenance"],
    }
    return _estimate_tokens(compact_payload)


def _empty_state(message: str, *, is_empty: bool) -> TaskBriefEmptyState:
    return {
        "is_empty": is_empty,
        "message": message,
    }


def _recent_sort_key(item: ContinuityRecallResultRecord) -> tuple[str, str]:
    return (item["created_at"], item["id"])


def _recent_items(items: list[ContinuityRecallResultRecord]) -> list[ContinuityRecallResultRecord]:
    return sorted(items, key=_recent_sort_key, reverse=True)


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


def _select_items_for_budget(
    *,
    candidates: list[ContinuityRecallResultRecord],
    token_budget: int,
    max_items: int,
) -> list[ContinuityRecallResultRecord]:
    selected: list[ContinuityRecallResultRecord] = []
    remaining_budget = max(1, token_budget)

    for candidate in candidates:
        if len(selected) >= max_items:
            break
        candidate_tokens = _estimate_candidate_tokens(candidate)
        if selected and candidate_tokens > remaining_budget:
            continue
        selected.append(candidate)
        remaining_budget -= candidate_tokens
        if remaining_budget <= 0:
            break

    return selected


def _build_section(
    *,
    section_key: str,
    title: str,
    intent: str,
    selection_rule: str,
    candidates: list[ContinuityRecallResultRecord],
    token_budget: int,
    max_items: int,
) -> TaskBriefSectionRecord:
    ordered_candidates = _dedupe_items(candidates)
    selected = _select_items_for_budget(
        candidates=ordered_candidates,
        token_budget=token_budget,
        max_items=max_items,
    )
    summary: TaskBriefSectionSummary = {
        "candidate_count": len(ordered_candidates),
        "selected_count": len(selected),
        "truncated_count": max(0, len(ordered_candidates) - len(selected)),
        "token_budget": token_budget,
        "estimated_tokens": sum(_estimate_candidate_tokens(item) for item in selected),
        "order": list(TASK_BRIEF_SECTION_ITEM_ORDER),
    }
    return {
        "section_key": section_key,
        "title": title,
        "intent": intent,
        "selection_rule": selection_rule,
        "items": selected,
        "summary": summary,
        "empty_state": _empty_state(
            _SECTION_EMPTY_MESSAGES[section_key],
            is_empty=len(selected) == 0,
        ),
    }


def _build_sections(plans: list[_SectionPlan]) -> list[TaskBriefSectionRecord]:
    return [
        _build_section(
            section_key=plan.section_key,
            title=plan.title,
            intent=plan.intent,
            selection_rule=plan.selection_rule,
            candidates=plan.candidates,
            token_budget=plan.token_budget,
            max_items=plan.max_items,
        )
        for plan in plans
    ]


def _single_item_candidates(
    item: ContinuityRecallResultRecord | None,
) -> list[ContinuityRecallResultRecord]:
    return [] if item is None else [item]


def _resolve_model_pack_defaults(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskBriefCompileRequestInput,
) -> tuple[str | None, int | None]:
    if request.workspace_id is None:
        return (None, None)
    if not store.workspace_visible_to_user_account(
        workspace_id=request.workspace_id,
        user_account_id=user_id,
    ):
        raise TaskBriefValidationError(f"workspace {request.workspace_id} was not found")
    try:
        selection = resolve_workspace_model_pack_selection(
            store=store,
            workspace_id=request.workspace_id,
            requested_pack_id=request.pack_id,
            requested_pack_version=request.pack_version,
        )
    except (ModelPackNotFoundError, ModelPackValidationError) as exc:
        raise TaskBriefValidationError(str(exc)) from exc
    pack = selection.pack
    if pack is None:
        return (None, None)
    return (pack["briefing_strategy"], pack["briefing_max_tokens"])


def _resolve_strategy(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskBriefCompileRequestInput,
) -> TaskBriefStrategyRecord:
    mode_defaults = _MODE_CONFIGS[request.mode]
    resolved_pack_strategy, resolved_pack_budget = _resolve_model_pack_defaults(
        store,
        user_id=user_id,
        request=request,
    )
    model_pack_strategy = (
        request.model_pack_strategy
        or resolved_pack_strategy
        or mode_defaults.default_model_pack_strategy
    )
    if request.token_budget is not None:
        resolved_budget = request.token_budget
        budget_source = "request"
    elif resolved_pack_budget is not None:
        resolved_budget = resolved_pack_budget
        budget_source = "model_pack_default"
    else:
        strategy_multiplier = _STRATEGY_MULTIPLIER.get(model_pack_strategy, 1.0)
        resolved_budget = min(
            MAX_TASK_BRIEF_TOKEN_BUDGET,
            max(1, int(round(mode_defaults.token_budget * strategy_multiplier))),
        )
        budget_source = "mode_default"
    return {
        "provider_strategy": request.provider_strategy or "deterministic_default",
        "model_pack_strategy": model_pack_strategy,
        "token_budget": resolved_budget,
        "budget_source": budget_source,
    }


def _compile_recall_payload(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskBriefCompileRequestInput,
    source_surface: str,
) -> tuple[list[ContinuityRecallResultRecord], ContinuityRecallScopeFilters]:
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
            debug=False,
        ),
        apply_limit=False,
        source_surface=source_surface,
    )
    return list(recall_payload["items"]), recall_payload["summary"]["filters"]


def _compile_user_recall_sections(
    items: list[ContinuityRecallResultRecord],
    *,
    token_budget: int,
) -> list[TaskBriefSectionRecord]:
    return _build_sections(
        [
            _SectionPlan(
                section_key="top_recall",
                title="Top Recall",
                intent="Provide the highest-ranked continuity recall items for direct user recall.",
                selection_rule="Hybrid recall rank order with token-budget truncation.",
                candidates=items,
                token_budget=token_budget,
                max_items=8,
            )
        ]
    )


def _compile_worker_sections(
    items: list[ContinuityRecallResultRecord],
    *,
    token_budget: int,
    include_non_promotable_facts: bool,
) -> list[TaskBriefSectionRecord]:
    recent_items = _recent_items(items)
    latest_decision = next(
        (item for item in recent_items if item["object_type"] == "Decision" and _is_active_truth(item)),
        None,
    )
    latest_next_action = next(
        (item for item in recent_items if item["object_type"] == "NextAction" and _is_active_truth(item)),
        None,
    )
    objective_candidates = [
        item for item in (latest_decision, latest_next_action) if item is not None
    ]
    constraint_candidates = [
        item
        for item in recent_items
        if _is_active_truth(item)
        and item["object_type"] in {"Commitment", "WaitingFor", "Blocker"}
    ]
    fact_candidates = [
        item
        for item in recent_items
        if _is_active_truth(item)
        and item["object_type"] in {"MemoryFact", "Decision", "Note"}
        and _is_promotable_fact(
            item,
            include_non_promotable_facts=include_non_promotable_facts,
        )
    ]
    objective_budget = max(1, int(token_budget * 0.4))
    constraints_budget = max(1, int(token_budget * 0.35))
    facts_budget = max(1, token_budget - objective_budget - constraints_budget)
    return _build_sections(
        [
            _SectionPlan(
                section_key="current_objective",
                title="Current Objective",
                intent="Give the worker the active decision and next action first.",
                selection_rule="Most recent active decision and next action only.",
                candidates=objective_candidates,
                token_budget=objective_budget,
                max_items=2,
            ),
            _SectionPlan(
                section_key="active_constraints",
                title="Active Constraints",
                intent="Expose blockers, commitments, and waiting-for items that can stall execution.",
                selection_rule="Newest active blocker, commitment, and waiting-for items under a compact budget.",
                candidates=constraint_candidates,
                token_budget=constraints_budget,
                max_items=3,
            ),
            _SectionPlan(
                section_key="critical_context",
                title="Critical Context",
                intent="Keep only the smallest set of facts that materially change task execution.",
                selection_rule="Newest active facts and notes that remain promotable unless explicitly overridden.",
                candidates=fact_candidates,
                token_budget=facts_budget,
                max_items=2,
            ),
        ]
    )


def _compile_handoff_sections(
    items: list[ContinuityRecallResultRecord],
    *,
    token_budget: int,
    include_non_promotable_facts: bool,
) -> list[TaskBriefSectionRecord]:
    recent_items = _recent_items(items)
    focus_candidates = [
        item
        for item in recent_items
        if _is_active_truth(item) and item["object_type"] in {"Decision", "NextAction"}
    ]
    open_loop_candidates = [
        item
        for item in recent_items
        if _is_active_truth(item) and item["object_type"] in {"Commitment", "WaitingFor", "Blocker"}
    ]
    recent_change_candidates = [
        item
        for item in recent_items
        if _is_recent_change_candidate(item)
        and _is_promotable_fact(
            item,
            include_non_promotable_facts=include_non_promotable_facts,
        )
    ]
    focus_budget = max(1, int(token_budget * 0.35))
    loop_budget = max(1, int(token_budget * 0.3))
    change_budget = max(1, token_budget - focus_budget - loop_budget)
    return _build_sections(
        [
            _SectionPlan(
                section_key="handoff_focus",
                title="Handoff Focus",
                intent="Summarize the active decision and next action for the receiving agent.",
                selection_rule="Newest active decision and next action first.",
                candidates=focus_candidates,
                token_budget=focus_budget,
                max_items=3,
            ),
            _SectionPlan(
                section_key="handoff_open_loops",
                title="Open Loops",
                intent="Carry unresolved dependencies and blockers into the handoff.",
                selection_rule="Newest active commitments, waiting-for items, and blockers.",
                candidates=open_loop_candidates,
                token_budget=loop_budget,
                max_items=3,
            ),
            _SectionPlan(
                section_key="handoff_recent_changes",
                title="Recent Changes",
                intent="Show the most recent materially relevant changes before handoff.",
                selection_rule="Newest change candidates, including superseded history, under token budget.",
                candidates=recent_change_candidates,
                token_budget=change_budget,
                max_items=4,
            ),
        ]
    )


def _compile_resume_sections(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskBriefCompileRequestInput,
    token_budget: int,
) -> tuple[list[TaskBriefSectionRecord], ContinuityRecallScopeFilters]:
    resume_payload = compile_continuity_resumption_brief(
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
            max_recent_changes=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
            max_open_loops=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
            include_non_promotable_facts=request.include_non_promotable_facts,
            debug=False,
        ),
    )
    brief = resume_payload["brief"]
    scope = brief["scope"]
    recent_changes_budget = max(1, int(token_budget * 0.35))
    open_loops_budget = max(1, int(token_budget * 0.3))
    single_budget = max(1, int((token_budget - recent_changes_budget - open_loops_budget) / 2))
    return (
        _build_sections(
            [
                _SectionPlan(
                    section_key="last_decision",
                    title="Last Decision",
                    intent="Keep the latest decision visible for resumption quality.",
                    selection_rule="Legacy continuity resumption latest active decision selection.",
                    candidates=_single_item_candidates(brief["last_decision"]["item"]),
                    token_budget=single_budget,
                    max_items=1,
                ),
                _SectionPlan(
                    section_key="open_loops",
                    title="Open Loops",
                    intent="Show unresolved commitments, waiting-for items, and blockers.",
                    selection_rule="Legacy continuity resumption open-loop ordering and limits.",
                    candidates=list(brief["open_loops"]["items"]),
                    token_budget=open_loops_budget,
                    max_items=DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
                ),
                _SectionPlan(
                    section_key="recent_changes",
                    title="Recent Changes",
                    intent="Surface recent relevant changes without reopening retrieval logic.",
                    selection_rule="Legacy continuity resumption recent-change ordering and limits.",
                    candidates=list(brief["recent_changes"]["items"]),
                    token_budget=recent_changes_budget,
                    max_items=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
                ),
                _SectionPlan(
                    section_key="next_action",
                    title="Next Action",
                    intent="Keep the next action prominent for restart quality.",
                    selection_rule="Legacy continuity resumption latest active next action selection.",
                    candidates=_single_item_candidates(brief["next_action"]["item"]),
                    token_budget=single_budget,
                    max_items=1,
                ),
            ]
        ),
        scope,
    )


def _compile_sections_for_request(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskBriefCompileRequestInput,
    token_budget: int,
) -> tuple[list[TaskBriefSectionRecord], ContinuityRecallScopeFilters, int]:
    if request.mode == "resume":
        sections, scope = _compile_resume_sections(
            store,
            user_id=user_id,
            request=request,
            token_budget=token_budget,
        )
        candidate_count = sum(section["summary"]["candidate_count"] for section in sections)
        return sections, scope, candidate_count

    items, scope = _compile_recall_payload(
        store,
        user_id=user_id,
        request=request,
        source_surface=f"task_brief.{request.mode}",
    )
    if request.mode == "user_recall":
        sections = _compile_user_recall_sections(
            items,
            token_budget=token_budget,
        )
    elif request.mode == "worker_subtask":
        sections = _compile_worker_sections(
            items,
            token_budget=token_budget,
            include_non_promotable_facts=request.include_non_promotable_facts,
        )
    else:
        sections = _compile_handoff_sections(
            items,
            token_budget=token_budget,
            include_non_promotable_facts=request.include_non_promotable_facts,
        )
    return sections, scope, len(items)


def _build_task_brief_summary(
    *,
    mode: str,
    sections: list[TaskBriefSectionRecord],
    candidate_count: int,
    token_budget: int,
) -> TaskBriefSummary:
    selected_item_count = sum(len(section["items"]) for section in sections)
    base_estimated_tokens = sum(section["summary"]["estimated_tokens"] for section in sections)
    return {
        "candidate_count": candidate_count,
        "selected_item_count": selected_item_count,
        "estimated_tokens": int(round(base_estimated_tokens * _MODE_TOKEN_ESTIMATE_MULTIPLIER[mode])),
        "token_budget": token_budget,
        "truncated": any(section["summary"]["truncated_count"] > 0 for section in sections),
        "deterministic_key": "",
        "section_order": [section["section_key"] for section in sections],
        "mode_order": list(TASK_BRIEF_MODE_ORDER),
    }


def _task_brief_deterministic_key(brief: TaskBriefRecord) -> str:
    deterministic_payload = {
        "assembly_version": brief["assembly_version"],
        "mode": brief["mode"],
        "scope": brief["scope"],
        "strategy": brief["strategy"],
        "sections": brief["sections"],
        "sources": brief["sources"],
        "summary": {
            "candidate_count": brief["summary"]["candidate_count"],
            "selected_item_count": brief["summary"]["selected_item_count"],
            "estimated_tokens": brief["summary"]["estimated_tokens"],
            "token_budget": brief["summary"]["token_budget"],
            "truncated": brief["summary"]["truncated"],
            "section_order": brief["summary"]["section_order"],
            "mode_order": brief["summary"]["mode_order"],
        },
    }
    return sha256(
        json.dumps(deterministic_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def compile_task_brief_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskBriefCompileRequestInput,
) -> TaskBriefRecord:
    _validate_request(request)
    strategy = _resolve_strategy(
        store,
        user_id=user_id,
        request=request,
    )
    sections, scope, candidate_count = _compile_sections_for_request(
        store,
        user_id=user_id,
        request=request,
        token_budget=strategy["token_budget"],
    )
    summary = _build_task_brief_summary(
        mode=request.mode,
        sections=sections,
        candidate_count=candidate_count,
        token_budget=strategy["token_budget"],
    )
    brief: TaskBriefRecord = {
        "assembly_version": TASK_BRIEF_ASSEMBLY_VERSION_V0,
        "mode": request.mode,
        "scope": scope,
        "strategy": strategy,
        "summary": summary,
        "sections": sections,
        "sources": ["continuity_capture_events", "continuity_objects", "retrieval_runs"],
    }
    brief["summary"]["deterministic_key"] = _task_brief_deterministic_key(brief)
    return brief


def compile_and_persist_task_brief(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskBriefCompileRequestInput,
) -> TaskBriefResponse:
    brief = compile_task_brief_record(
        store,
        user_id=user_id,
        request=request,
    )
    row = store.create_task_brief(
        mode=brief["mode"],
        query_text=request.query,
        scope=cast(JsonObject, brief["scope"]),
        provider_strategy=brief["strategy"]["provider_strategy"],
        model_pack_strategy=brief["strategy"]["model_pack_strategy"],
        token_budget=brief["summary"]["token_budget"],
        estimated_tokens=brief["summary"]["estimated_tokens"],
        item_count=brief["summary"]["selected_item_count"],
        deterministic_key=brief["summary"]["deterministic_key"],
        payload=cast(JsonObject, brief),
    )
    return _serialize_task_brief_row(row)


def _serialize_task_brief_row(row: TaskBriefRow) -> TaskBriefResponse:
    return {
        "task_brief": cast(TaskBriefRecord, row["payload"]),
        "persistence": {
            "task_brief_id": str(row["id"]),
            "created_at": row["created_at"].isoformat(),
        },
    }


def get_persisted_task_brief(
    store: ContinuityStore,
    *,
    task_brief_id: UUID,
) -> TaskBriefResponse:
    row = store.get_task_brief_optional(task_brief_id=task_brief_id)
    if row is None:
        raise TaskBriefNotFoundError(f"task brief {task_brief_id} was not found")
    return _serialize_task_brief_row(row)


def compare_task_briefs(
    store: ContinuityStore,
    *,
    user_id: UUID,
    primary_request: TaskBriefCompileRequestInput,
    secondary_request: TaskBriefCompileRequestInput,
) -> TaskBriefComparisonResponse:
    primary = compile_task_brief_record(
        store,
        user_id=user_id,
        request=primary_request,
    )
    secondary = compile_task_brief_record(
        store,
        user_id=user_id,
        request=secondary_request,
    )
    primary_ids = {item["id"] for section in primary["sections"] for item in section["items"]}
    secondary_ids = {item["id"] for section in secondary["sections"] for item in section["items"]}
    smaller_mode = None
    if primary["summary"]["estimated_tokens"] < secondary["summary"]["estimated_tokens"]:
        smaller_mode = primary["mode"]
    elif secondary["summary"]["estimated_tokens"] < primary["summary"]["estimated_tokens"]:
        smaller_mode = secondary["mode"]

    comparison: TaskBriefComparisonStats = {
        "primary_mode": primary["mode"],
        "secondary_mode": secondary["mode"],
        "smaller_mode": smaller_mode,
        "estimated_token_delta": primary["summary"]["estimated_tokens"] - secondary["summary"]["estimated_tokens"],
        "selected_item_delta": primary["summary"]["selected_item_count"] - secondary["summary"]["selected_item_count"],
        "shared_item_ids": sorted(primary_ids & secondary_ids),
        "primary_is_smaller": (
            primary["summary"]["estimated_tokens"] < secondary["summary"]["estimated_tokens"]
        ),
    }
    return {
        "comparison_version": TASK_BRIEF_COMPARISON_VERSION_V0,
        "primary": primary,
        "secondary": secondary,
        "comparison": comparison,
    }


__all__ = [
    "TaskBriefNotFoundError",
    "TaskBriefValidationError",
    "compile_and_persist_task_brief",
    "compile_task_brief_record",
    "compare_task_briefs",
    "get_persisted_task_brief",
]
