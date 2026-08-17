"""Mechanical MCP retrieval carrier."""

from __future__ import annotations

from collections.abc import Mapping
from alicebot_api.continuity_brief import compile_continuity_brief
from alicebot_api.continuity_recall import (
    get_retrieval_trace,
    query_continuity_recall,
)
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import (
    CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER,
    DEFAULT_CONTINUITY_RECALL_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    DEFAULT_TEMPORAL_TIMELINE_LIMIT,
    MAX_CONTINUITY_RECALL_LIMIT,
    MAX_CONTINUITY_RESUMPTION_OPEN_LOOP_LIMIT,
    MAX_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
    MAX_TEMPORAL_TIMELINE_LIMIT,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
)
from alicebot_api.store import JsonObject
from alicebot_api.temporal_state import (
    get_temporal_state_at,
    get_temporal_timeline,
)
from alicebot_api.task_briefing import (
    compare_task_briefs,
    compile_and_persist_task_brief,
    get_persisted_task_brief,
)
from alicebot_api.vnext_agent_control import (
    PolicyDecision,
    resource_project_scope,
)
from alicebot_api.vnext_projects import VNextProjectService
from alicebot_api.vnext_repositories import JsonObject as VNextJsonObject
from alicebot_api.vnext_retrieval import (
    CONTEXT_DEPTH_MINIMAL,
    CONTEXT_DEPTH_MINIMAL_MAX_ITEMS,
    GRAPH_STAGE_ENABLED,
    RRF_K,
    STAGE_DISABLED_MINIMAL,
    VECTOR_STAGE_ENABLED,
    VNextRetrievalService,
    _order_memories_for_strategy,
    reciprocal_rank_fusion,
)

from .context import _COMPACT_SOURCE_FIELDS, _compact_items
from .projects import _handle_alice_vnext_open_loops
from .retrieval_shared import (
    _SQLITE_NEXT_ACTION_MEMORY_TYPES,
    _SQLITE_OPEN_LOOP_ACTIVE_STATUSES,
    _SQLITE_REVIEWABLE_STATUSES,
    _compact_vnext_event,
    _compact_vnext_memory,
    _compact_vnext_open_loop,
    _created_at_sort_key,
    _memory_matches_project,
    _memory_matches_query,
    _provenance_count,
    _resource_matches_project_scope,
    _row_in_window,
    _utc_now_iso_text,
)
from .shared import (
    MCPRuntimeContext,
    MCPToolError,
    _DEFAULT_SENSITIVITY_ALLOWED,
    _OPEN_LOOP_TOOL_ACTIONS,
    _PREFETCH_CONTEXT_ASSEMBLY_VERSION_V0,
    _RECALL_DEFAULT_LIMIT,
    _RECALL_MAX_LIMIT,
    _agent_identity_from_arguments,
    _json_object,
    _mcp_agent_policy_preflight,
    _parse_bool,
    _parse_context_pack_tuning,
    _parse_continuity_brief_request,
    _parse_int,
    _parse_optional_datetime,
    _parse_optional_text,
    _parse_optional_uuid,
    _parse_required_text,
    _parse_required_uuid,
    _parse_string_list,
    _parse_task_brief_request,
    _policy_checked,
    _raise_mcp_policy_blocked,
    _render_prefetch_context_text,
    _retrieval_filter_kwargs,
    _store_context,
    _vnext_store_context,
)


def _compact_recall_result(item: Mapping[str, object], *, score: float, provenance_count: int) -> JsonObject:
    return _json_object(
        {
            "id": str(item.get("id")),
            "type": item.get("memory_type"),
            "text": item.get("canonical_text") or item.get("summary") or item.get("title"),
            "score": round(score, 6),
            "domain": item.get("domain"),
            "status": item.get("status"),
            "confidence": item.get("confidence"),
            "provenance_count": provenance_count,
        }
    )


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
    # Defaults on. An agent that imported a vault and then recalls from it
    # should not have to know a flag exists to see its own documents.
    include_sources = _parse_bool(arguments, key="include_sources", default=True)
    context_depth, budget_strategy = _parse_context_pack_tuning(arguments)
    if context_depth == CONTEXT_DEPTH_MINIMAL:
        # Same tier semantics as the context-pack compiler: the cheapest
        # useful call caps the result count and runs full-text search only.
        limit = min(limit, CONTEXT_DEPTH_MINIMAL_MAX_ITEMS)
    domains = list(_parse_string_list(arguments, "domains"))
    sensitivity_allowed = list(_parse_string_list(arguments, "sensitivity_allowed") or _DEFAULT_SENSITIVITY_ALLOWED)
    # Validate typed retrieval inputs before opening an auth/policy store
    # transaction, preserving the public fail-fast contract.
    retrieval_filters = _retrieval_filter_kwargs(arguments)
    requested_projects = retrieval_filters.get("projects", ()) or _parse_string_list(arguments, "project_scope")
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="memory.recall",
        domains=tuple(domains),
        sensitivity_allowed=tuple(sensitivity_allowed),
        project_scope=requested_projects,
    )
    domains = list(decision.effective_domains)
    sensitivity_allowed = list(decision.effective_sensitivity_allowed)
    if decision.effective_project_scope:
        retrieval_filters["projects"] = decision.effective_project_scope
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
            vector_rows: list[VNextJsonObject] = []
            vector_stage = STAGE_DISABLED_MINIMAL
            graph_rows: list[VNextJsonObject] = []
            graph_stage = STAGE_DISABLED_MINIMAL
            matched_entities: list[VNextJsonObject] = []
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
        ranked_lists: dict[str, list[VNextJsonObject]] = {"fts": fts_rows}
        if vector_stage == VECTOR_STAGE_ENABLED:
            ranked_lists["vector"] = vector_rows
        if graph_stage == GRAPH_STAGE_ENABLED:
            ranked_lists["graph"] = graph_rows
        fused: list[tuple[VNextJsonObject, float]] = []
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
            provenance_count = len(store.list_provenance_links(target_type="memory", target_id=str(item.get("id"))))
            results.append(
                _compact_recall_result(item, score=scores[str(item.get("id"))], provenance_count=provenance_count)
            )

        # Imported source material, alongside the memories rather than mixed
        # into them. Without this, the natural agent sequence — import a vault,
        # then recall from it — answers count=0 for content the store holds and
        # retrieval can already rank, because captured documents land as
        # unsearchable candidates and recall only ever searched memories.
        source_excerpts: list[JsonObject] = []
        if include_sources:
            raw_sources, _sources_stage = service.search_source_excerpts(
                query=query,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit,
                winning_memories=ordered_rows,
            )
            source_excerpts = _compact_items(raw_sources, _COMPACT_SOURCE_FIELDS)

    payload: dict[str, object] = {
        "query": query,
        "results": results,
        "count": len(results),
    }
    if source_excerpts:
        # Deliberately a separate key with its own count. These are documents
        # the user imported, quotable but not asserted; results[] stays the
        # channel for facts the system stands behind.
        payload["sources"] = source_excerpts
        payload["source_count"] = len(source_excerpts)
    if matched_entities:
        # WHO the results are about: entities the query resolved to via the
        # graph stage. Only present when the query matched entities.
        payload["entities"] = matched_entities
    if debug:
        from alicebot_api.vnext_retrieval import TIE_BREAK_CONTENT_STABLE

        retrieval_payload: dict[str, object] = {
            "fusion": {
                "algorithm": "reciprocal_rank_fusion",
                "k": RRF_K,
                "tie_break": TIE_BREAK_CONTENT_STABLE,
            },
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
            filter_payload: dict[str, object] = {}
            if "memory_types" in retrieval_filters:
                filter_payload["memory_types"] = list(retrieval_filters["memory_types"])
            if "projects" in retrieval_filters:
                filter_payload["projects"] = list(retrieval_filters["projects"])
            if "created_by_agent_ids" in retrieval_filters:
                filter_payload["created_by_agent_ids"] = list(retrieval_filters["created_by_agent_ids"])
            retrieval_payload["filters"] = filter_payload
        payload["retrieval"] = retrieval_payload
    return _json_object(payload)


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
        return _json_object(
            query_continuity_recall(
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
            ),
        )


def _handle_alice_state_at(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return _json_object(
            get_temporal_state_at(
                store,
                user_id=context.user_id,
                request=TemporalStateAtQueryInput(
                    entity_id=_parse_required_uuid(arguments, "entity_id"),
                    at=_parse_optional_datetime(arguments, "at"),
                ),
            ),
        )


def _handle_alice_resume(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    requested_project = _parse_optional_text(arguments, "project")
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="context_pack.request",
        project_scope=(requested_project,) if requested_project else (),
    )
    return _vnext_resume(
        context,
        arguments,
        effective_project_scope=decision.effective_project_scope,
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
        return _json_object(
            compile_continuity_resumption_brief(
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
            ),
        )


def _handle_alice_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return _json_object(
            compile_continuity_brief(
                store,
                user_id=context.user_id,
                request=_parse_continuity_brief_request(arguments),
            )
        )


def _handle_alice_task_brief(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    with _store_context(context) as store:
        return _json_object(
            compile_and_persist_task_brief(
                store,
                user_id=context.user_id,
                request=_parse_task_brief_request(arguments),
            )
        )


def _handle_alice_task_brief_show(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return _json_object(
            get_persisted_task_brief(
                store,
                task_brief_id=_parse_required_uuid(arguments, "task_brief_id"),
            )
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
    if "compare_briefing_strategy" in arguments:
        secondary_arguments["briefing_strategy"] = arguments["compare_briefing_strategy"]
    if "compare_token_budget" in arguments:
        secondary_arguments["token_budget"] = arguments["compare_token_budget"]

    with _store_context(context) as store:
        return _json_object(
            compare_task_briefs(
                store,
                user_id=context.user_id,
                primary_request=primary_request,
                secondary_request=_parse_task_brief_request(secondary_arguments),
            )
        )


def _handle_alice_retrieval_trace(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
) -> JsonObject:
    with _store_context(context) as store:
        return _json_object(
            get_retrieval_trace(
                store,
                user_id=context.user_id,
                retrieval_run_id=_parse_required_uuid(arguments, "retrieval_run_id"),
            )
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
    return _json_object(
        {
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
    )


def _handle_alice_open_loops(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    action = (_parse_optional_text(arguments, "action") or "list").lower()
    if action not in _OPEN_LOOP_TOOL_ACTIONS:
        allowed = ", ".join(_OPEN_LOOP_TOOL_ACTIONS)
        raise MCPToolError(f"action must be one of: {allowed}")
    if action == "list":
        return _handle_alice_vnext_open_loops(context, arguments)

    identity = _agent_identity_from_arguments(context, arguments)
    loop_id = _parse_required_text(arguments, "loop_id")
    blocked_decision: PolicyDecision | None = None
    loop: VNextJsonObject | None = None
    with _vnext_store_context(context) as store:
        target = store.get_open_loop(loop_id)
        if target is None:
            raise MCPToolError(f"open loop {loop_id} was not found")
        _actor_type, _actor_id, decision = _policy_checked(
            store,
            identity=identity,
            action="open_loop.update",
            domains=(str(target.get("domain") or "unknown"),),
            sensitivity_allowed=(str(target.get("sensitivity") or "unknown"),),
            project_scope=resource_project_scope(target),
            require_explicit_project_scope=True,
        )
        if decision.decision == "blocked":
            blocked_decision = decision
        else:
            loop = VNextProjectService(store).review_open_loop(
                loop_id=loop_id,
                action=action,
                title=_parse_optional_text(arguments, "title"),
                description=_parse_optional_text(arguments, "description"),
                due_at=_parse_optional_text(arguments, "due_at"),
                priority=_parse_optional_text(arguments, "priority"),
                resolution_note=_parse_optional_text(arguments, "resolution_note"),
            )
    if blocked_decision is not None:
        _raise_mcp_policy_blocked(blocked_decision)
    if loop is None:
        raise MCPToolError("open-loop update did not complete")
    return _json_object({"action": action, "open_loop": loop})


def _vnext_recent_decisions(
    context: MCPRuntimeContext,
    *,
    arguments: Mapping[str, object],
    limit: int,
    effective_project_scope: tuple[str, ...] = (),
) -> JsonObject:
    query = _parse_optional_text(arguments, "query")
    project = _parse_optional_text(arguments, "project")
    since = _parse_optional_datetime(arguments, "since")
    until = _parse_optional_datetime(arguments, "until")
    filters_ignored = [key for key in ("thread_id", "task_id", "person") if arguments.get(key) not in (None, "")]

    with _vnext_store_context(context) as store:
        matched = [
            row
            for row in store.list_memories()
            if row.get("memory_type") == "decision"
            and str(row.get("status")) in _SQLITE_REVIEWABLE_STATUSES
            and _resource_matches_project_scope(row, effective_project_scope)
            and _memory_matches_query(row, query)
            and _memory_matches_project(row, project)
            and _row_in_window(row, key="created_at", since=since, until=until)
        ]
        matched.sort(key=_created_at_sort_key, reverse=True)
        decisions = [
            _compact_vnext_memory(row, provenance_count=_provenance_count(store, row.get("id")))
            for row in matched[:limit]
        ]

    payload: dict[str, object] = {
        "decisions": decisions,
        "count": len(decisions),
        "mode": "vnext",
    }
    if filters_ignored:
        payload["filters_ignored"] = filters_ignored
    return _json_object(payload)


def _vnext_resume(
    context: MCPRuntimeContext,
    arguments: Mapping[str, object],
    *,
    effective_project_scope: tuple[str, ...] = (),
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
    query = _parse_optional_text(arguments, "query")
    since = _parse_optional_datetime(arguments, "since")
    until = _parse_optional_datetime(arguments, "until")
    filters_ignored = [
        key
        for key in ("thread_id", "task_id", "person", "include_non_promotable_facts", "debug")
        if arguments.get(key) not in (None, "", False)
    ]

    with _vnext_store_context(context) as store:
        decisions = store.list_memories(
            status=None,
            statuses=tuple(_SQLITE_REVIEWABLE_STATUSES),
            memory_types=("decision",),
            projects=effective_project_scope or None,
            created_at_start=since,
            created_at_end=until,
            query=query,
            order_by_created_at=True,
            limit=1,
        )
        last_decision: JsonObject | None = None
        if decisions:
            last_decision = {
                "kind": "memory",
                **_compact_vnext_memory(
                    decisions[0], provenance_count=_provenance_count(store, decisions[0].get("id"))
                ),
            }

        loop_rows = []
        if max_open_loops > 0:
            loop_rows = store.list_open_loops(
                status=None,
                statuses=tuple(_SQLITE_OPEN_LOOP_ACTIVE_STATUSES),
                query=query,
                limit=max_open_loops,
                scope_projects=effective_project_scope,
                scope_window_start=since,
                scope_window_end=until,
            )
        open_loops = [_compact_vnext_open_loop(row) for row in loop_rows[:max_open_loops]]

        next_action: JsonObject | None = open_loops[0] if open_loops else None
        if next_action is None:
            todo_memories = store.list_memories(
                status=None,
                statuses=tuple(_SQLITE_REVIEWABLE_STATUSES),
                memory_types=tuple(_SQLITE_NEXT_ACTION_MEMORY_TYPES),
                projects=effective_project_scope or None,
                created_at_start=since,
                created_at_end=until,
                query=query,
                order_by_created_at=True,
                limit=1,
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
            if not effective_project_scope and query is None:
                event_rows = store.list_events(
                    occurred_at_start=since,
                    occurred_at_end=until,
                    limit=max_recent_changes,
                )
            else:
                # Event rows do not carry authoritative project scope. Query
                # admitted memory targets and join loop events to authoritative
                # loop scope before LIMIT. The loop join deliberately has no
                # opened-at bound: an older active loop can have a newer event
                # inside the requested event window.
                event_rows = []
                seen_event_ids: set[str] = set()
                for event in store.list_resume_memory_events(
                    statuses=tuple(_SQLITE_REVIEWABLE_STATUSES),
                    projects=effective_project_scope,
                    query=query,
                    occurred_at_start=since,
                    occurred_at_end=until,
                    limit=max_recent_changes,
                ):
                    event_id = str(event.get("id") or "")
                    if event_id:
                        seen_event_ids.add(event_id)
                    event_rows.append(event)
                for event in store.list_open_loop_events(
                    statuses=tuple(_SQLITE_OPEN_LOOP_ACTIVE_STATUSES),
                    scope_projects=effective_project_scope,
                    query=query,
                    occurred_at_start=since,
                    occurred_at_end=until,
                    limit=max_recent_changes,
                ):
                    event_id = str(event.get("id") or "")
                    if event_id and event_id in seen_event_ids:
                        continue
                    if event_id:
                        seen_event_ids.add(event_id)
                    event_rows.append(event)
                event_rows.sort(
                    key=lambda row: (str(row.get("occurred_at") or ""), str(row.get("id") or "")),
                    reverse=True,
                )
            recent_changes = [_compact_vnext_event(row) for row in event_rows[:max_recent_changes]]

    return _json_object(
        {
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
    )


def _handle_alice_recent_decisions(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_CONTINUITY_RESUMPTION_RECENT_CHANGES_LIMIT,
        minimum=1,
        maximum=MAX_CONTINUITY_RECALL_LIMIT,
    )
    identity = _agent_identity_from_arguments(context, arguments)
    requested_project = _parse_optional_text(arguments, "project")
    decision = _mcp_agent_policy_preflight(
        context,
        arguments,
        action="recent_decisions.lookup",
        domains=_parse_string_list(arguments, "domains"),
        sensitivity_allowed=_parse_string_list(arguments, "sensitivity_allowed")
        or ("public", "internal", "private", "unknown"),
        project_scope=_parse_string_list(arguments, "project_scope")
        or ((requested_project,) if requested_project else ()),
    )
    return _vnext_recent_decisions(
        context,
        arguments=arguments,
        limit=limit,
        effective_project_scope=(
            decision.effective_project_scope if identity is not None and identity.project_scope else ()
        ),
    )


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
    return _json_object(
        {
            "recent_changes": brief["recent_changes"],
            "scope": brief["scope"],
            "sources": brief["sources"],
            "order": list(CONTINUITY_RESUMPTION_RECENT_CHANGE_ORDER),
        }
    )


def _handle_alice_timeline(context: MCPRuntimeContext, arguments: Mapping[str, object]) -> JsonObject:
    limit = _parse_int(
        arguments,
        key="limit",
        default=DEFAULT_TEMPORAL_TIMELINE_LIMIT,
        minimum=1,
        maximum=MAX_TEMPORAL_TIMELINE_LIMIT,
    )
    with _store_context(context) as store:
        return _json_object(
            get_temporal_timeline(
                store,
                user_id=context.user_id,
                request=TemporalTimelineQueryInput(
                    entity_id=_parse_required_uuid(arguments, "entity_id"),
                    since=_parse_optional_datetime(arguments, "since"),
                    until=_parse_optional_datetime(arguments, "until"),
                    limit=limit,
                ),
            ),
        )
