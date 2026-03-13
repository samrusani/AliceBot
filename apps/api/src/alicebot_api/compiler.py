from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from alicebot_api.contracts import (
    COMPILER_VERSION_V0,
    CompilerDecision,
    CompileContextSemanticRetrievalInput,
    CompilerRunResult,
    CompiledContextPack,
    ContextCompilerLimits,
    ContextPackHybridMemorySummary,
    ContextPackMemory,
    ContextPackMemorySummary,
    HybridMemoryDecisionTracePayload,
    MemorySelectionSource,
    SEMANTIC_MEMORY_RETRIEVAL_ORDER,
    SemanticMemoryRetrievalRequestInput,
    TRACE_KIND_CONTEXT_COMPILE,
    TraceEventRecord,
    isoformat_or_none,
)
from alicebot_api.semantic_retrieval import validate_semantic_memory_retrieval_request
from alicebot_api.store import (
    ContinuityStore,
    EntityEdgeRow,
    EntityRow,
    EventRow,
    MemoryRow,
    SemanticMemoryRetrievalRow,
    SessionRow,
    ThreadRow,
    UserRow,
)

SUMMARY_TRACE_EVENT_KIND = "context.summary"
_UNBOUNDED_SEMANTIC_RETRIEVAL_LIMIT = 2_147_483_647
HYBRID_MEMORY_SOURCE_PRECEDENCE: list[MemorySelectionSource] = ["symbolic", "semantic"]
HYBRID_SYMBOLIC_ORDER = ["updated_at_asc", "created_at_asc", "id_asc"]


@dataclass(frozen=True, slots=True)
class CompiledTraceRun:
    trace_id: str
    context_pack: CompiledContextPack
    trace_event_count: int


@dataclass(frozen=True, slots=True)
class CompiledMemorySection:
    items: list[ContextPackMemory]
    summary: ContextPackMemorySummary
    decisions: list[CompilerDecision]


@dataclass(slots=True)
class HybridMemoryCandidate:
    memory: MemoryRow
    sources: list[MemorySelectionSource]
    semantic_score: float | None = None


def _session_sort_key(
    session: SessionRow,
    latest_session_sequence: dict[UUID, int],
) -> tuple[int, str, str, str]:
    latest_sequence = latest_session_sequence.get(session["id"], -1)
    started_at = isoformat_or_none(session["started_at"]) or ""
    created_at = session["created_at"].isoformat()
    return (latest_sequence, started_at, created_at, str(session["id"]))


def _serialize_user(user: UserRow) -> dict[str, str | None]:
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "display_name": user["display_name"],
        "created_at": user["created_at"].isoformat(),
    }


def _serialize_thread(thread: ThreadRow) -> dict[str, str]:
    return {
        "id": str(thread["id"]),
        "title": thread["title"],
        "created_at": thread["created_at"].isoformat(),
        "updated_at": thread["updated_at"].isoformat(),
    }


def _serialize_session(session: SessionRow) -> dict[str, str | None]:
    return {
        "id": str(session["id"]),
        "status": session["status"],
        "started_at": isoformat_or_none(session["started_at"]),
        "ended_at": isoformat_or_none(session["ended_at"]),
        "created_at": session["created_at"].isoformat(),
    }


def _serialize_event(event: EventRow) -> dict[str, object]:
    return {
        "id": str(event["id"]),
        "session_id": None if event["session_id"] is None else str(event["session_id"]),
        "sequence_no": event["sequence_no"],
        "kind": event["kind"],
        "payload": event["payload"],
        "created_at": event["created_at"].isoformat(),
    }


def _memory_sort_key(memory: MemoryRow) -> tuple[str, str, str]:
    return (
        memory["updated_at"].isoformat(),
        memory["created_at"].isoformat(),
        str(memory["id"]),
    )


def _serialize_memory(memory: MemoryRow) -> dict[str, object]:
    return {
        "id": str(memory["id"]),
        "memory_key": memory["memory_key"],
        "value": memory["value"],
        "status": memory["status"],
        "source_event_ids": memory["source_event_ids"],
        "created_at": memory["created_at"].isoformat(),
        "updated_at": memory["updated_at"].isoformat(),
        "source_provenance": {
            "sources": ["symbolic"],
            "semantic_score": None,
        },
    }


def _entity_sort_key(entity: EntityRow) -> tuple[str, str]:
    return (entity["created_at"].isoformat(), str(entity["id"]))


def _serialize_entity(entity: EntityRow) -> dict[str, object]:
    return {
        "id": str(entity["id"]),
        "entity_type": entity["entity_type"],
        "name": entity["name"],
        "source_memory_ids": entity["source_memory_ids"],
        "created_at": entity["created_at"].isoformat(),
    }


def _entity_edge_sort_key(edge: EntityEdgeRow) -> tuple[str, str]:
    return (edge["created_at"].isoformat(), str(edge["id"]))


def _serialize_entity_edge(edge: EntityEdgeRow) -> dict[str, object]:
    return {
        "id": str(edge["id"]),
        "from_entity_id": str(edge["from_entity_id"]),
        "to_entity_id": str(edge["to_entity_id"]),
        "relationship_type": edge["relationship_type"],
        "valid_from": isoformat_or_none(edge["valid_from"]),
        "valid_to": isoformat_or_none(edge["valid_to"]),
        "source_memory_ids": edge["source_memory_ids"],
        "created_at": edge["created_at"].isoformat(),
    }


def _semantic_memory_sort_key(memory: SemanticMemoryRetrievalRow) -> tuple[float, str, str]:
    return (-float(memory["score"]), memory["created_at"].isoformat(), str(memory["id"]))


def _semantic_deleted_memory_sort_key(memory: MemoryRow) -> tuple[str, str, str]:
    return (
        memory["updated_at"].isoformat(),
        memory["created_at"].isoformat(),
        str(memory["id"]),
    )


def _empty_hybrid_memory_summary() -> ContextPackHybridMemorySummary:
    return {
        "requested": False,
        "embedding_config_id": None,
        "query_vector_dimensions": 0,
        "semantic_limit": 0,
        "symbolic_selected_count": 0,
        "semantic_selected_count": 0,
        "merged_candidate_count": 0,
        "deduplicated_count": 0,
        "included_symbolic_only_count": 0,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 0,
        "similarity_metric": None,
        "source_precedence": list(HYBRID_MEMORY_SOURCE_PRECEDENCE),
        "symbolic_order": list(HYBRID_SYMBOLIC_ORDER),
        "semantic_order": list(SEMANTIC_MEMORY_RETRIEVAL_ORDER),
    }


def _hybrid_memory_decision_metadata(
    *,
    embedding_config_id: UUID | None,
    memory_key: str,
    status: str,
    source_event_ids: list[str],
    selected_sources: list[MemorySelectionSource],
    semantic_score: float | None,
) -> HybridMemoryDecisionTracePayload:
    return {
        "embedding_config_id": None if embedding_config_id is None else str(embedding_config_id),
        "memory_key": memory_key,
        "status": status,
        "source_event_ids": source_event_ids,
        "selected_sources": list(selected_sources),
        "semantic_score": semantic_score,
    }


def _serialize_hybrid_memory(candidate: HybridMemoryCandidate) -> ContextPackMemory:
    memory = candidate.memory
    return {
        "id": str(memory["id"]),
        "memory_key": memory["memory_key"],
        "value": memory["value"],
        "status": memory["status"],
        "source_event_ids": memory["source_event_ids"],
        "created_at": memory["created_at"].isoformat(),
        "updated_at": memory["updated_at"].isoformat(),
        "source_provenance": {
            "sources": list(candidate.sources),
            "semantic_score": candidate.semantic_score,
        },
    }


def _build_symbolic_memory_section(
    *,
    memories: list[MemoryRow],
    limits: ContextCompilerLimits,
) -> CompiledMemorySection:
    ordered_memories = sorted(memories, key=_memory_sort_key)
    active_memories = [memory for memory in ordered_memories if memory["status"] == "active"]
    deleted_memories = [memory for memory in ordered_memories if memory["status"] != "active"]
    symbolic_candidates = active_memories[-limits.max_memories :] if limits.max_memories > 0 else []
    memory_candidates = [
        HybridMemoryCandidate(memory=memory, sources=["symbolic"])
        for memory in symbolic_candidates
    ]
    decisions: list[CompilerDecision] = []

    for position, candidate in enumerate(memory_candidates, start=1):
        decisions.append(
            CompilerDecision(
                "included",
                "memory",
                candidate.memory["id"],
                "within_hybrid_memory_limit",
                position,
                metadata=_hybrid_memory_decision_metadata(
                    embedding_config_id=None,
                    memory_key=candidate.memory["memory_key"],
                    status=candidate.memory["status"],
                    source_event_ids=candidate.memory["source_event_ids"],
                    selected_sources=candidate.sources,
                    semantic_score=None,
                ),
            )
        )

    for position, memory in enumerate(deleted_memories, start=1):
        decisions.append(
            CompilerDecision(
                "excluded",
                "memory",
                memory["id"],
                "hybrid_memory_deleted",
                position,
                metadata=_hybrid_memory_decision_metadata(
                    embedding_config_id=None,
                    memory_key=memory["memory_key"],
                    status=memory["status"],
                    source_event_ids=memory["source_event_ids"],
                    selected_sources=["symbolic"],
                    semantic_score=None,
                ),
            )
        )

    included_items = [_serialize_hybrid_memory(candidate) for candidate in memory_candidates]
    return CompiledMemorySection(
        items=included_items,
        summary={
            "candidate_count": len(memory_candidates) + len(deleted_memories),
            "included_count": len(included_items),
            "excluded_deleted_count": len(deleted_memories),
            "excluded_limit_count": 0,
            "hybrid_retrieval": {
                **_empty_hybrid_memory_summary(),
                "symbolic_selected_count": len(memory_candidates),
                "merged_candidate_count": len(memory_candidates),
                "included_symbolic_only_count": len(included_items),
            },
        },
        decisions=decisions,
    )


def _compile_memory_section(
    store: ContinuityStore,
    *,
    memories: list[MemoryRow],
    limits: ContextCompilerLimits,
    semantic_retrieval: CompileContextSemanticRetrievalInput | None,
) -> CompiledMemorySection:
    if semantic_retrieval is None:
        return _build_symbolic_memory_section(memories=memories, limits=limits)

    ordered_memories = sorted(memories, key=_memory_sort_key)
    active_memories = [memory for memory in ordered_memories if memory["status"] == "active"]
    deleted_memories = [memory for memory in ordered_memories if memory["status"] != "active"]
    symbolic_candidates = active_memories[-limits.max_memories :] if limits.max_memories > 0 else []
    active_memories_by_id = {memory["id"]: memory for memory in active_memories}

    request = SemanticMemoryRetrievalRequestInput(
        embedding_config_id=semantic_retrieval.embedding_config_id,
        query_vector=semantic_retrieval.query_vector,
        limit=semantic_retrieval.limit,
    )
    _config, query_vector = validate_semantic_memory_retrieval_request(store, request=request)
    ordered_semantic_candidates = sorted(
        store.retrieve_semantic_memory_matches(
            embedding_config_id=semantic_retrieval.embedding_config_id,
            query_vector=query_vector,
            limit=_UNBOUNDED_SEMANTIC_RETRIEVAL_LIMIT,
        ),
        key=_semantic_memory_sort_key,
    )
    selected_semantic_candidates = ordered_semantic_candidates[: semantic_retrieval.limit]

    merged_candidates: list[HybridMemoryCandidate] = [
        HybridMemoryCandidate(memory=memory, sources=["symbolic"])
        for memory in symbolic_candidates
    ]
    merged_candidate_ids = {candidate.memory["id"] for candidate in merged_candidates}
    deduplication_decisions: list[CompilerDecision] = []
    deduplicated_count = 0

    for position, semantic_candidate in enumerate(selected_semantic_candidates, start=1):
        memory = active_memories_by_id.get(semantic_candidate["id"], semantic_candidate)
        if semantic_candidate["id"] in merged_candidate_ids:
            deduplicated_count += 1
            for candidate in merged_candidates:
                if candidate.memory["id"] != semantic_candidate["id"]:
                    continue
                if "semantic" not in candidate.sources:
                    candidate.sources.append("semantic")
                candidate.semantic_score = float(semantic_candidate["score"])
                deduplication_decisions.append(
                    CompilerDecision(
                        "included",
                        "memory",
                        semantic_candidate["id"],
                        "hybrid_memory_deduplicated",
                        position,
                        metadata=_hybrid_memory_decision_metadata(
                            embedding_config_id=semantic_retrieval.embedding_config_id,
                            memory_key=candidate.memory["memory_key"],
                            status=candidate.memory["status"],
                            source_event_ids=candidate.memory["source_event_ids"],
                            selected_sources=candidate.sources,
                            semantic_score=candidate.semantic_score,
                        ),
                    )
                )
                break
            continue

        merged_candidate_ids.add(semantic_candidate["id"])
        merged_candidates.append(
            HybridMemoryCandidate(
                memory=memory,
                sources=["semantic"],
                semantic_score=float(semantic_candidate["score"]),
            )
        )

    deleted_candidates = [
        HybridMemoryCandidate(
            memory=memory,
            sources=["symbolic"],
        )
        for memory in sorted(deleted_memories, key=_semantic_deleted_memory_sort_key)
    ]

    decisions = list(deduplication_decisions)
    included_candidates = merged_candidates[: limits.max_memories] if limits.max_memories > 0 else []
    excluded_candidates = merged_candidates[limits.max_memories :] if limits.max_memories > 0 else merged_candidates
    included_symbolic_only_count = 0
    included_semantic_only_count = 0
    included_dual_source_count = 0

    for position, candidate in enumerate(merged_candidates, start=1):
        if position <= limits.max_memories and limits.max_memories > 0:
            if candidate.sources == ["symbolic"]:
                included_symbolic_only_count += 1
            elif candidate.sources == ["semantic"]:
                included_semantic_only_count += 1
            else:
                included_dual_source_count += 1
            decisions.append(
                CompilerDecision(
                    "included",
                    "memory",
                    candidate.memory["id"],
                    "within_hybrid_memory_limit",
                    position,
                    metadata=_hybrid_memory_decision_metadata(
                        embedding_config_id=semantic_retrieval.embedding_config_id,
                        memory_key=candidate.memory["memory_key"],
                        status=candidate.memory["status"],
                        source_event_ids=candidate.memory["source_event_ids"],
                        selected_sources=candidate.sources,
                        semantic_score=candidate.semantic_score,
                    ),
                )
            )
            continue

        decisions.append(
            CompilerDecision(
                "excluded",
                "memory",
                candidate.memory["id"],
                "hybrid_memory_limit_exceeded",
                position,
                metadata=_hybrid_memory_decision_metadata(
                    embedding_config_id=semantic_retrieval.embedding_config_id,
                    memory_key=candidate.memory["memory_key"],
                    status=candidate.memory["status"],
                    source_event_ids=candidate.memory["source_event_ids"],
                    selected_sources=candidate.sources,
                    semantic_score=candidate.semantic_score,
                ),
            )
        )

    for position, candidate in enumerate(deleted_candidates, start=1):
        decisions.append(
            CompilerDecision(
                "excluded",
                "memory",
                candidate.memory["id"],
                "hybrid_memory_deleted",
                position,
                metadata=_hybrid_memory_decision_metadata(
                    embedding_config_id=semantic_retrieval.embedding_config_id,
                    memory_key=candidate.memory["memory_key"],
                    status=candidate.memory["status"],
                    source_event_ids=candidate.memory["source_event_ids"],
                    selected_sources=candidate.sources,
                    semantic_score=None,
                ),
            )
        )

    return CompiledMemorySection(
        items=[_serialize_hybrid_memory(candidate) for candidate in included_candidates],
        summary={
            "candidate_count": len(merged_candidates) + len(deleted_candidates),
            "included_count": len(included_candidates),
            "excluded_deleted_count": len(deleted_candidates),
            "excluded_limit_count": len(excluded_candidates),
            "hybrid_retrieval": {
                "requested": True,
                "embedding_config_id": str(semantic_retrieval.embedding_config_id),
                "query_vector_dimensions": len(query_vector),
                "semantic_limit": semantic_retrieval.limit,
                "symbolic_selected_count": len(symbolic_candidates),
                "semantic_selected_count": len(selected_semantic_candidates),
                "merged_candidate_count": len(merged_candidates),
                "deduplicated_count": deduplicated_count,
                "included_symbolic_only_count": included_symbolic_only_count,
                "included_semantic_only_count": included_semantic_only_count,
                "included_dual_source_count": included_dual_source_count,
                "similarity_metric": "cosine_similarity",
                "source_precedence": list(HYBRID_MEMORY_SOURCE_PRECEDENCE),
                "symbolic_order": list(HYBRID_SYMBOLIC_ORDER),
                "semantic_order": list(SEMANTIC_MEMORY_RETRIEVAL_ORDER),
            },
        },
        decisions=decisions,
    )


def compile_continuity_context(
    *,
    user: UserRow,
    thread: ThreadRow,
    sessions: list[SessionRow],
    events: list[EventRow],
    memories: list[MemoryRow],
    entities: list[EntityRow],
    entity_edges: list[EntityEdgeRow],
    limits: ContextCompilerLimits,
    memory_section: CompiledMemorySection | None = None,
) -> CompilerRunResult:
    latest_session_sequence: dict[UUID, int] = {}
    for event in events:
        session_id = event["session_id"]
        if session_id is None:
            continue
        latest_session_sequence[session_id] = max(
            latest_session_sequence.get(session_id, -1),
            event["sequence_no"],
        )

    ordered_sessions = sorted(
        sessions,
        key=lambda session: _session_sort_key(session, latest_session_sequence),
    )
    included_sessions = ordered_sessions[-limits.max_sessions :] if limits.max_sessions > 0 else []
    included_session_ids = {session["id"] for session in included_sessions}

    decisions: list[CompilerDecision] = [
        CompilerDecision("included", "user", user["id"], "scope_user", 1),
        CompilerDecision("included", "thread", thread["id"], "scope_thread", 1),
    ]

    for position, session in enumerate(included_sessions, start=1):
        decisions.append(
            CompilerDecision(
                "included",
                "session",
                session["id"],
                "within_session_limit",
                position,
            )
        )

    excluded_sessions = ordered_sessions[: max(len(ordered_sessions) - len(included_sessions), 0)]
    for position, session in enumerate(excluded_sessions, start=1):
        decisions.append(
            CompilerDecision(
                "excluded",
                "session",
                session["id"],
                "session_limit_exceeded",
                position,
            )
        )

    eligible_events: list[EventRow] = []
    for event in events:
        if event["session_id"] is not None and event["session_id"] not in included_session_ids:
            decisions.append(
                CompilerDecision(
                    "excluded",
                    "event",
                    event["id"],
                    "session_not_included",
                    event["sequence_no"],
                )
            )
            continue
        eligible_events.append(event)

    included_events = eligible_events[-limits.max_events :] if limits.max_events > 0 else []
    included_event_ids = {event["id"] for event in included_events}

    for event in eligible_events:
        if event["id"] in included_event_ids:
            decisions.append(
                CompilerDecision(
                    "included",
                    "event",
                    event["id"],
                    "within_event_limit",
                    event["sequence_no"],
                )
            )
            continue

        decisions.append(
            CompilerDecision(
                "excluded",
                "event",
                event["id"],
                "event_limit_exceeded",
                event["sequence_no"],
            )
        )

    resolved_memory_section = memory_section or _build_symbolic_memory_section(
        memories=memories,
        limits=limits,
    )
    decisions.extend(resolved_memory_section.decisions)
    ordered_entities = sorted(entities, key=_entity_sort_key)
    included_entities = ordered_entities[-limits.max_entities :] if limits.max_entities > 0 else []
    included_entity_ids = {entity["id"] for entity in included_entities}
    excluded_entity_limit_count = max(len(ordered_entities) - len(included_entities), 0)

    for position, entity in enumerate(ordered_entities, start=1):
        if entity["id"] in included_entity_ids:
            decisions.append(
                CompilerDecision(
                    "included",
                    "entity",
                    entity["id"],
                    "within_entity_limit",
                    position,
                    metadata={
                        "record_entity_type": entity["entity_type"],
                        "name": entity["name"],
                        "source_memory_ids": entity["source_memory_ids"],
                    },
                )
            )
            continue

        decisions.append(
            CompilerDecision(
                "excluded",
                "entity",
                entity["id"],
                "entity_limit_exceeded",
                position,
                metadata={
                    "record_entity_type": entity["entity_type"],
                    "name": entity["name"],
                    "source_memory_ids": entity["source_memory_ids"],
                },
            )
        )

    ordered_candidate_entity_edges = sorted(
        [
            edge
            for edge in entity_edges
            if edge["from_entity_id"] in included_entity_ids
            or edge["to_entity_id"] in included_entity_ids
        ],
        key=_entity_edge_sort_key,
    )
    included_entity_edges = (
        ordered_candidate_entity_edges[-limits.max_entity_edges :]
        if limits.max_entity_edges > 0
        else []
    )
    included_entity_edge_ids = {edge["id"] for edge in included_entity_edges}
    excluded_entity_edge_limit_count = max(
        len(ordered_candidate_entity_edges) - len(included_entity_edges),
        0,
    )

    for position, edge in enumerate(ordered_candidate_entity_edges, start=1):
        attached_included_entity_ids = [
            str(entity_id)
            for entity_id in (edge["from_entity_id"], edge["to_entity_id"])
            if entity_id in included_entity_ids
        ]
        metadata = {
            "from_entity_id": str(edge["from_entity_id"]),
            "to_entity_id": str(edge["to_entity_id"]),
            "relationship_type": edge["relationship_type"],
            "valid_from": isoformat_or_none(edge["valid_from"]),
            "valid_to": isoformat_or_none(edge["valid_to"]),
            "source_memory_ids": edge["source_memory_ids"],
            "attached_included_entity_ids": attached_included_entity_ids,
        }
        if edge["id"] in included_entity_edge_ids:
            decisions.append(
                CompilerDecision(
                    "included",
                    "entity_edge",
                    edge["id"],
                    "within_entity_edge_limit",
                    position,
                    metadata=metadata,
                )
            )
            continue

        decisions.append(
            CompilerDecision(
                "excluded",
                "entity_edge",
                edge["id"],
                "entity_edge_limit_exceeded",
                position,
                metadata=metadata,
            )
        )

    trace_events = [decision.to_trace_event() for decision in decisions]
    trace_events.append(
        TraceEventRecord(
            kind=SUMMARY_TRACE_EVENT_KIND,
            payload={
                "included_session_count": len(included_sessions),
                "excluded_session_count": len(excluded_sessions),
                "included_event_count": len(included_events),
                "excluded_event_count": len(events) - len(included_events),
                "included_memory_count": resolved_memory_section.summary["included_count"],
                "excluded_memory_count": (
                    resolved_memory_section.summary["excluded_deleted_count"]
                    + resolved_memory_section.summary["excluded_limit_count"]
                ),
                "excluded_deleted_memory_count": resolved_memory_section.summary[
                    "excluded_deleted_count"
                ],
                "excluded_memory_limit_count": resolved_memory_section.summary[
                    "excluded_limit_count"
                ],
                "hybrid_memory_requested": resolved_memory_section.summary["hybrid_retrieval"][
                    "requested"
                ],
                "hybrid_memory_candidate_count": resolved_memory_section.summary["candidate_count"],
                "hybrid_memory_merged_candidate_count": resolved_memory_section.summary[
                    "hybrid_retrieval"
                ]["merged_candidate_count"],
                "hybrid_memory_deduplicated_count": resolved_memory_section.summary[
                    "hybrid_retrieval"
                ]["deduplicated_count"],
                "included_dual_source_memory_count": resolved_memory_section.summary[
                    "hybrid_retrieval"
                ]["included_dual_source_count"],
                "included_entity_count": len(included_entities),
                "excluded_entity_count": excluded_entity_limit_count,
                "excluded_entity_limit_count": excluded_entity_limit_count,
                "included_entity_edge_count": len(included_entity_edges),
                "excluded_entity_edge_count": excluded_entity_edge_limit_count,
                "excluded_entity_edge_limit_count": excluded_entity_edge_limit_count,
                "compiler_version": COMPILER_VERSION_V0,
            },
        )
    )

    return CompilerRunResult(
        context_pack={
            "compiler_version": COMPILER_VERSION_V0,
            "scope": {
                "user_id": str(user["id"]),
                "thread_id": str(thread["id"]),
            },
            "limits": {
                "max_sessions": limits.max_sessions,
                "max_events": limits.max_events,
                "max_memories": limits.max_memories,
                "max_entities": limits.max_entities,
                "max_entity_edges": limits.max_entity_edges,
            },
            "user": _serialize_user(user),
            "thread": _serialize_thread(thread),
            "sessions": [_serialize_session(session) for session in included_sessions],
            "events": [_serialize_event(event) for event in included_events],
            "memories": list(resolved_memory_section.items),
            "memory_summary": resolved_memory_section.summary,
            "entities": [_serialize_entity(entity) for entity in included_entities],
            "entity_summary": {
                "candidate_count": len(ordered_entities),
                "included_count": len(included_entities),
                "excluded_limit_count": excluded_entity_limit_count,
            },
            "entity_edges": [_serialize_entity_edge(edge) for edge in included_entity_edges],
            "entity_edge_summary": {
                "anchor_entity_count": len(included_entities),
                "candidate_count": len(ordered_candidate_entity_edges),
                "included_count": len(included_entity_edges),
                "excluded_limit_count": excluded_entity_edge_limit_count,
            },
        },
        trace_events=trace_events,
    )


def compile_and_persist_trace(
    store: ContinuityStore,
    *,
    user_id: UUID,
    thread_id: UUID,
    limits: ContextCompilerLimits,
    semantic_retrieval: CompileContextSemanticRetrievalInput | None = None,
) -> CompiledTraceRun:
    user = store.get_user(user_id)
    thread = store.get_thread(thread_id)
    sessions = store.list_thread_sessions(thread_id)
    events = store.list_thread_events(thread_id)
    memories = store.list_context_memories()
    memory_section = _compile_memory_section(
        store,
        memories=memories,
        limits=limits,
        semantic_retrieval=semantic_retrieval,
    )
    entities = store.list_entities()
    ordered_entities = sorted(entities, key=_entity_sort_key)
    included_entities = ordered_entities[-limits.max_entities :] if limits.max_entities > 0 else []
    entity_edges = store.list_entity_edges_for_entities([entity["id"] for entity in included_entities])
    compiler_run = compile_continuity_context(
        user=user,
        thread=thread,
        sessions=sessions,
        events=events,
        memories=memories,
        entities=entities,
        entity_edges=entity_edges,
        limits=limits,
        memory_section=memory_section,
    )
    trace = store.create_trace(
        user_id=user_id,
        thread_id=thread_id,
        kind=TRACE_KIND_CONTEXT_COMPILE,
        compiler_version=COMPILER_VERSION_V0,
        status="completed",
        limits=limits.as_payload(),
    )

    for sequence_no, trace_event in enumerate(compiler_run.trace_events, start=1):
        store.append_trace_event(
            trace_id=trace["id"],
            sequence_no=sequence_no,
            kind=trace_event.kind,
            payload=trace_event.payload,
        )

    return CompiledTraceRun(
        trace_id=str(trace["id"]),
        context_pack=compiler_run.context_pack,
        trace_event_count=len(compiler_run.trace_events),
    )
