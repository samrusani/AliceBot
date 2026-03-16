from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from alicebot_api.compiler import (
    SUMMARY_TRACE_EVENT_KIND,
    _compile_artifact_chunk_section,
    _compile_memory_section,
    compile_continuity_context,
)
from alicebot_api.contracts import (
    CompileContextArtifactScopedArtifactRetrievalInput,
    CompileContextArtifactScopedSemanticArtifactRetrievalInput,
    CompileContextSemanticRetrievalInput,
    CompileContextTaskScopedSemanticArtifactRetrievalInput,
    CompileContextTaskScopedArtifactRetrievalInput,
    ContextCompilerLimits,
)


def test_compile_continuity_context_is_deterministic_and_stably_ordered() -> None:
    user_id = uuid4()
    thread_id = uuid4()
    base_time = datetime(2026, 3, 11, 9, 0, tzinfo=UTC)
    session_ids = [uuid4(), uuid4(), uuid4()]
    event_ids = [uuid4(), uuid4(), uuid4(), uuid4()]
    memory_ids = [uuid4(), uuid4(), uuid4()]
    entity_ids = [uuid4(), uuid4(), uuid4()]
    edge_ids = [uuid4(), uuid4(), uuid4(), uuid4()]

    user = {
        "id": user_id,
        "email": "owner@example.com",
        "display_name": "Owner",
        "created_at": base_time,
    }
    thread = {
        "id": thread_id,
        "user_id": user_id,
        "title": "Traceable thread",
        "created_at": base_time,
        "updated_at": base_time + timedelta(minutes=4),
    }
    sessions = [
        {
            "id": session_ids[0],
            "user_id": user_id,
            "thread_id": thread_id,
            "status": "done",
            "started_at": base_time,
            "ended_at": base_time + timedelta(minutes=1),
            "created_at": base_time,
        },
        {
            "id": session_ids[1],
            "user_id": user_id,
            "thread_id": thread_id,
            "status": "done",
            "started_at": base_time + timedelta(minutes=2),
            "ended_at": base_time + timedelta(minutes=3),
            "created_at": base_time + timedelta(minutes=2),
        },
        {
            "id": session_ids[2],
            "user_id": user_id,
            "thread_id": thread_id,
            "status": "active",
            "started_at": base_time + timedelta(minutes=4),
            "ended_at": None,
            "created_at": base_time + timedelta(minutes=4),
        },
    ]
    events = [
        {
            "id": event_ids[0],
            "user_id": user_id,
            "thread_id": thread_id,
            "session_id": session_ids[0],
            "sequence_no": 1,
            "kind": "message.user",
            "payload": {"text": "one"},
            "created_at": base_time,
        },
        {
            "id": event_ids[1],
            "user_id": user_id,
            "thread_id": thread_id,
            "session_id": session_ids[1],
            "sequence_no": 2,
            "kind": "message.assistant",
            "payload": {"text": "two"},
            "created_at": base_time + timedelta(minutes=2),
        },
        {
            "id": event_ids[2],
            "user_id": user_id,
            "thread_id": thread_id,
            "session_id": session_ids[2],
            "sequence_no": 3,
            "kind": "message.user",
            "payload": {"text": "three"},
            "created_at": base_time + timedelta(minutes=4),
        },
        {
            "id": event_ids[3],
            "user_id": user_id,
            "thread_id": thread_id,
            "session_id": session_ids[2],
            "sequence_no": 4,
            "kind": "message.assistant",
            "payload": {"text": "four"},
            "created_at": base_time + timedelta(minutes=5),
        },
    ]
    memories = [
        {
            "id": memory_ids[0],
            "user_id": user_id,
            "memory_key": "user.preference.tea",
            "value": {"likes": "green"},
            "status": "active",
            "source_event_ids": [str(event_ids[0])],
            "created_at": base_time,
            "updated_at": base_time + timedelta(minutes=1),
            "deleted_at": None,
        },
        {
            "id": memory_ids[1],
            "user_id": user_id,
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": [str(event_ids[1])],
            "created_at": base_time + timedelta(minutes=1),
            "updated_at": base_time + timedelta(minutes=4),
            "deleted_at": None,
        },
        {
            "id": memory_ids[2],
            "user_id": user_id,
            "memory_key": "user.preference.snacks",
            "value": {"likes": "almonds"},
            "status": "active",
            "source_event_ids": [str(event_ids[2])],
            "created_at": base_time + timedelta(minutes=2),
            "updated_at": base_time + timedelta(minutes=5),
            "deleted_at": None,
        },
    ]
    entities = [
        {
            "id": entity_ids[0],
            "user_id": user_id,
            "entity_type": "person",
            "name": "Samir",
            "source_memory_ids": [str(memory_ids[0])],
            "created_at": base_time,
        },
        {
            "id": entity_ids[1],
            "user_id": user_id,
            "entity_type": "merchant",
            "name": "Neighborhood Cafe",
            "source_memory_ids": [str(memory_ids[1])],
            "created_at": base_time + timedelta(minutes=3),
        },
        {
            "id": entity_ids[2],
            "user_id": user_id,
            "entity_type": "project",
            "name": "AliceBot",
            "source_memory_ids": [str(memory_ids[1]), str(memory_ids[2])],
            "created_at": base_time + timedelta(minutes=6),
        },
    ]
    entity_edges = [
        {
            "id": edge_ids[0],
            "user_id": user_id,
            "from_entity_id": entity_ids[0],
            "to_entity_id": entity_ids[1],
            "relationship_type": "visits",
            "valid_from": None,
            "valid_to": None,
            "source_memory_ids": [str(memory_ids[0])],
            "created_at": base_time + timedelta(minutes=2),
        },
        {
            "id": edge_ids[1],
            "user_id": user_id,
            "from_entity_id": entity_ids[2],
            "to_entity_id": entity_ids[0],
            "relationship_type": "references",
            "valid_from": base_time + timedelta(minutes=5),
            "valid_to": None,
            "source_memory_ids": [str(memory_ids[2])],
            "created_at": base_time + timedelta(minutes=5),
        },
        {
            "id": edge_ids[2],
            "user_id": user_id,
            "from_entity_id": entity_ids[1],
            "to_entity_id": entity_ids[2],
            "relationship_type": "works_on",
            "valid_from": None,
            "valid_to": base_time + timedelta(minutes=8),
            "source_memory_ids": [str(memory_ids[1]), str(memory_ids[2])],
            "created_at": base_time + timedelta(minutes=8),
        },
        {
            "id": edge_ids[3],
            "user_id": user_id,
            "from_entity_id": entity_ids[0],
            "to_entity_id": entity_ids[0],
            "relationship_type": "self_loop",
            "valid_from": None,
            "valid_to": None,
            "source_memory_ids": [str(memory_ids[0])],
            "created_at": base_time + timedelta(minutes=9),
        },
    ]
    limits = ContextCompilerLimits(
        max_sessions=2,
        max_events=2,
        max_memories=2,
        max_entities=2,
        max_entity_edges=2,
    )

    first_run = compile_continuity_context(
        user=user,
        thread=thread,
        sessions=sessions,
        events=events,
        memories=memories,
        entities=entities,
        entity_edges=entity_edges,
        limits=limits,
    )
    second_run = compile_continuity_context(
        user=user,
        thread=thread,
        sessions=sessions,
        events=events,
        memories=memories,
        entities=entities,
        entity_edges=entity_edges,
        limits=limits,
    )

    assert first_run.context_pack == second_run.context_pack
    assert first_run.trace_events == second_run.trace_events
    assert [session["id"] for session in first_run.context_pack["sessions"]] == [
        str(session_ids[1]),
        str(session_ids[2]),
    ]
    assert [event["sequence_no"] for event in first_run.context_pack["events"]] == [3, 4]
    assert [memory["memory_key"] for memory in first_run.context_pack["memories"]] == [
        "user.preference.coffee",
        "user.preference.snacks",
    ]
    assert [memory["source_provenance"] for memory in first_run.context_pack["memories"]] == [
        {"sources": ["symbolic"], "semantic_score": None},
        {"sources": ["symbolic"], "semantic_score": None},
    ]
    assert [entity["id"] for entity in first_run.context_pack["entities"]] == [
        str(entity_ids[1]),
        str(entity_ids[2]),
    ]
    assert [edge["id"] for edge in first_run.context_pack["entity_edges"]] == [
        str(edge_ids[1]),
        str(edge_ids[2]),
    ]
    assert first_run.context_pack["memory_summary"] == {
        "candidate_count": 2,
        "included_count": 2,
        "excluded_deleted_count": 0,
        "excluded_limit_count": 0,
        "hybrid_retrieval": {
            "requested": False,
            "embedding_config_id": None,
            "query_vector_dimensions": 0,
            "semantic_limit": 0,
            "symbolic_selected_count": 2,
            "semantic_selected_count": 0,
            "merged_candidate_count": 2,
            "deduplicated_count": 0,
            "included_symbolic_only_count": 2,
            "included_semantic_only_count": 0,
            "included_dual_source_count": 0,
            "similarity_metric": None,
            "source_precedence": ["symbolic", "semantic"],
            "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
            "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
        },
    }
    assert first_run.context_pack["artifact_chunks"] == []
    assert first_run.context_pack["artifact_chunk_summary"] == {
        "requested": False,
        "lexical_requested": False,
        "semantic_requested": False,
        "scope": None,
        "query": None,
        "query_terms": [],
        "embedding_config_id": None,
        "query_vector_dimensions": 0,
        "limit": 0,
        "lexical_limit": 0,
        "semantic_limit": 0,
        "searched_artifact_count": 0,
        "lexical_candidate_count": 0,
        "semantic_candidate_count": 0,
        "merged_candidate_count": 0,
        "deduplicated_count": 0,
        "included_count": 0,
        "included_lexical_only_count": 0,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 0,
        "excluded_uningested_artifact_count": 0,
        "excluded_limit_count": 0,
        "matching_rule": None,
        "similarity_metric": None,
        "source_precedence": ["lexical", "semantic"],
        "lexical_order": [
            "matched_query_term_count_desc",
            "first_match_char_start_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
        "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
        "merged_order": [
            "source_precedence_asc",
            "lexical_rank_asc",
            "semantic_rank_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
    }
    assert first_run.context_pack["entity_summary"] == {
        "candidate_count": 3,
        "included_count": 2,
        "excluded_limit_count": 1,
    }
    assert first_run.context_pack["entity_edge_summary"] == {
        "anchor_entity_count": 2,
        "candidate_count": 3,
        "included_count": 2,
        "excluded_limit_count": 1,
    }


def test_compile_continuity_context_records_included_and_excluded_reasons() -> None:
    user_id = uuid4()
    thread_id = uuid4()
    base_time = datetime(2026, 3, 11, 9, 0, tzinfo=UTC)
    kept_session_id = uuid4()
    dropped_session_id = uuid4()
    dropped_by_session_event_id = uuid4()
    dropped_by_event_limit_id = uuid4()
    kept_event_id = uuid4()
    dropped_by_memory_limit_id = uuid4()
    kept_memory_id = uuid4()
    deleted_memory_id = uuid4()
    dropped_entity_id = uuid4()
    kept_entity_id = uuid4()
    dropped_entity_edge_id = uuid4()
    kept_entity_edge_id = uuid4()
    ignored_entity_edge_id = uuid4()
    external_entity_id = uuid4()
    kept_edge_valid_from = base_time + timedelta(minutes=5)

    compiler_run = compile_continuity_context(
        user={
            "id": user_id,
            "email": "owner@example.com",
            "display_name": "Owner",
            "created_at": base_time,
        },
        thread={
            "id": thread_id,
            "user_id": user_id,
            "title": "Traceable thread",
            "created_at": base_time,
            "updated_at": base_time,
        },
        sessions=[
            {
                "id": dropped_session_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "status": "done",
                "started_at": base_time,
                "ended_at": base_time,
                "created_at": base_time,
            },
            {
                "id": kept_session_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "status": "active",
                "started_at": base_time + timedelta(minutes=1),
                "ended_at": None,
                "created_at": base_time + timedelta(minutes=1),
            },
        ],
        events=[
            {
                "id": dropped_by_session_event_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "session_id": dropped_session_id,
                "sequence_no": 1,
                "kind": "message.user",
                "payload": {"text": "old session"},
                "created_at": base_time,
            },
            {
                "id": dropped_by_event_limit_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "session_id": kept_session_id,
                "sequence_no": 2,
                "kind": "message.assistant",
                "payload": {"text": "too old"},
                "created_at": base_time + timedelta(minutes=1),
            },
            {
                "id": kept_event_id,
                "user_id": user_id,
                "thread_id": thread_id,
                "session_id": kept_session_id,
                "sequence_no": 3,
                "kind": "message.user",
                "payload": {"text": "keep"},
                "created_at": base_time + timedelta(minutes=2),
            },
        ],
        memories=[
            {
                "id": dropped_by_memory_limit_id,
                "user_id": user_id,
                "memory_key": "user.preference.old",
                "value": {"likes": "black"},
                "status": "active",
                "source_event_ids": [str(dropped_by_session_event_id)],
                "created_at": base_time,
                "updated_at": base_time,
                "deleted_at": None,
            },
            {
                "id": kept_memory_id,
                "user_id": user_id,
                "memory_key": "user.preference.keep",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": [str(kept_event_id)],
                "created_at": base_time + timedelta(minutes=1),
                "updated_at": base_time + timedelta(minutes=2),
                "deleted_at": None,
            },
            {
                "id": deleted_memory_id,
                "user_id": user_id,
                "memory_key": "user.preference.deleted",
                "value": {"likes": "espresso"},
                "status": "deleted",
                "source_event_ids": [str(dropped_by_event_limit_id)],
                "created_at": base_time + timedelta(minutes=2),
                "updated_at": base_time + timedelta(minutes=3),
                "deleted_at": base_time + timedelta(minutes=3),
            },
        ],
        entities=[
            {
                "id": dropped_entity_id,
                "user_id": user_id,
                "entity_type": "person",
                "name": "Samir",
                "source_memory_ids": [str(dropped_by_memory_limit_id)],
                "created_at": base_time,
            },
            {
                "id": kept_entity_id,
                "user_id": user_id,
                "entity_type": "project",
                "name": "AliceBot",
                "source_memory_ids": [str(kept_memory_id)],
                "created_at": base_time + timedelta(minutes=4),
            },
        ],
        entity_edges=[
            {
                "id": dropped_entity_edge_id,
                "user_id": user_id,
                "from_entity_id": dropped_entity_id,
                "to_entity_id": kept_entity_id,
                "relationship_type": "related_to",
                "valid_from": None,
                "valid_to": None,
                "source_memory_ids": [str(kept_memory_id)],
                "created_at": base_time + timedelta(minutes=3),
            },
            {
                "id": kept_entity_edge_id,
                "user_id": user_id,
                "from_entity_id": kept_entity_id,
                "to_entity_id": external_entity_id,
                "relationship_type": "depends_on",
                "valid_from": kept_edge_valid_from,
                "valid_to": None,
                "source_memory_ids": [str(kept_memory_id)],
                "created_at": base_time + timedelta(minutes=5),
            },
            {
                "id": ignored_entity_edge_id,
                "user_id": user_id,
                "from_entity_id": dropped_entity_id,
                "to_entity_id": external_entity_id,
                "relationship_type": "ignored",
                "valid_from": None,
                "valid_to": None,
                "source_memory_ids": [str(dropped_by_memory_limit_id)],
                "created_at": base_time + timedelta(minutes=6),
            },
        ],
        limits=ContextCompilerLimits(
            max_sessions=1,
            max_events=1,
            max_memories=1,
            max_entities=1,
            max_entity_edges=1,
        ),
    )

    trace_payloads = [trace_event.payload for trace_event in compiler_run.trace_events]

    assert {"entity_type": "session", "entity_id": str(kept_session_id), "reason": "within_session_limit", "position": 1} in trace_payloads
    assert {"entity_type": "session", "entity_id": str(dropped_session_id), "reason": "session_limit_exceeded", "position": 1} in trace_payloads
    assert {"entity_type": "event", "entity_id": str(dropped_by_session_event_id), "reason": "session_not_included", "position": 1} in trace_payloads
    assert {"entity_type": "event", "entity_id": str(dropped_by_event_limit_id), "reason": "event_limit_exceeded", "position": 2} in trace_payloads
    assert {"entity_type": "event", "entity_id": str(kept_event_id), "reason": "within_event_limit", "position": 3} in trace_payloads
    assert {
        "entity_type": "memory",
        "entity_id": str(kept_memory_id),
        "reason": "within_hybrid_memory_limit",
        "position": 1,
        "memory_key": "user.preference.keep",
        "status": "active",
        "source_event_ids": [str(kept_event_id)],
        "embedding_config_id": None,
        "selected_sources": ["symbolic"],
        "semantic_score": None,
    } in trace_payloads
    assert {
        "entity_type": "memory",
        "entity_id": str(deleted_memory_id),
        "reason": "hybrid_memory_deleted",
        "position": 1,
        "memory_key": "user.preference.deleted",
        "status": "deleted",
        "source_event_ids": [str(dropped_by_event_limit_id)],
        "embedding_config_id": None,
        "selected_sources": ["symbolic"],
        "semantic_score": None,
    } in trace_payloads
    assert {
        "entity_type": "entity",
        "entity_id": str(dropped_entity_id),
        "reason": "entity_limit_exceeded",
        "position": 1,
        "record_entity_type": "person",
        "name": "Samir",
        "source_memory_ids": [str(dropped_by_memory_limit_id)],
    } in trace_payloads
    assert {
        "entity_type": "entity",
        "entity_id": str(kept_entity_id),
        "reason": "within_entity_limit",
        "position": 2,
        "record_entity_type": "project",
        "name": "AliceBot",
        "source_memory_ids": [str(kept_memory_id)],
    } in trace_payloads
    assert {
        "entity_type": "entity_edge",
        "entity_id": str(dropped_entity_edge_id),
        "reason": "entity_edge_limit_exceeded",
        "position": 1,
        "from_entity_id": str(dropped_entity_id),
        "to_entity_id": str(kept_entity_id),
        "relationship_type": "related_to",
        "valid_from": None,
        "valid_to": None,
        "source_memory_ids": [str(kept_memory_id)],
        "attached_included_entity_ids": [str(kept_entity_id)],
    } in trace_payloads
    assert {
        "entity_type": "entity_edge",
        "entity_id": str(kept_entity_edge_id),
        "reason": "within_entity_edge_limit",
        "position": 2,
        "from_entity_id": str(kept_entity_id),
        "to_entity_id": str(external_entity_id),
        "relationship_type": "depends_on",
        "valid_from": kept_edge_valid_from.isoformat(),
        "valid_to": None,
        "source_memory_ids": [str(kept_memory_id)],
        "attached_included_entity_ids": [str(kept_entity_id)],
    } in trace_payloads
    assert all(payload.get("entity_id") != str(ignored_entity_edge_id) for payload in trace_payloads)
    assert compiler_run.trace_events[-1].kind == SUMMARY_TRACE_EVENT_KIND
    assert compiler_run.context_pack["events"][0]["id"] == str(kept_event_id)
    assert compiler_run.context_pack["memories"] == [
        {
            "id": str(kept_memory_id),
            "memory_key": "user.preference.keep",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": [str(kept_event_id)],
            "created_at": (base_time + timedelta(minutes=1)).isoformat(),
            "updated_at": (base_time + timedelta(minutes=2)).isoformat(),
            "source_provenance": {"sources": ["symbolic"], "semantic_score": None},
        }
    ]
    assert compiler_run.context_pack["memory_summary"] == {
        "candidate_count": 2,
        "included_count": 1,
        "excluded_deleted_count": 1,
        "excluded_limit_count": 0,
        "hybrid_retrieval": {
            "requested": False,
            "embedding_config_id": None,
            "query_vector_dimensions": 0,
            "semantic_limit": 0,
            "symbolic_selected_count": 1,
            "semantic_selected_count": 0,
            "merged_candidate_count": 1,
            "deduplicated_count": 0,
            "included_symbolic_only_count": 1,
            "included_semantic_only_count": 0,
            "included_dual_source_count": 0,
            "similarity_metric": None,
            "source_precedence": ["symbolic", "semantic"],
            "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
            "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
        },
    }
    assert compiler_run.context_pack["artifact_chunks"] == []
    assert compiler_run.context_pack["artifact_chunk_summary"] == {
        "requested": False,
        "lexical_requested": False,
        "semantic_requested": False,
        "scope": None,
        "query": None,
        "query_terms": [],
        "embedding_config_id": None,
        "query_vector_dimensions": 0,
        "limit": 0,
        "lexical_limit": 0,
        "semantic_limit": 0,
        "searched_artifact_count": 0,
        "lexical_candidate_count": 0,
        "semantic_candidate_count": 0,
        "merged_candidate_count": 0,
        "deduplicated_count": 0,
        "included_count": 0,
        "included_lexical_only_count": 0,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 0,
        "excluded_uningested_artifact_count": 0,
        "excluded_limit_count": 0,
        "matching_rule": None,
        "similarity_metric": None,
        "source_precedence": ["lexical", "semantic"],
        "lexical_order": [
            "matched_query_term_count_desc",
            "first_match_char_start_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
        "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
        "merged_order": [
            "source_precedence_asc",
            "lexical_rank_asc",
            "semantic_rank_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
    }
    assert compiler_run.context_pack["entities"] == [
        {
            "id": str(kept_entity_id),
            "entity_type": "project",
            "name": "AliceBot",
            "source_memory_ids": [str(kept_memory_id)],
            "created_at": (base_time + timedelta(minutes=4)).isoformat(),
        }
    ]
    assert compiler_run.context_pack["entity_edges"] == [
        {
            "id": str(kept_entity_edge_id),
            "from_entity_id": str(kept_entity_id),
            "to_entity_id": str(external_entity_id),
            "relationship_type": "depends_on",
            "valid_from": kept_edge_valid_from.isoformat(),
            "valid_to": None,
            "source_memory_ids": [str(kept_memory_id)],
            "created_at": (base_time + timedelta(minutes=5)).isoformat(),
        }
    ]
    assert compiler_run.context_pack["entity_edge_summary"] == {
        "anchor_entity_count": 1,
        "candidate_count": 2,
        "included_count": 1,
        "excluded_limit_count": 1,
    }
    assert compiler_run.trace_events[-1].payload["included_entity_edge_count"] == 1
    assert compiler_run.trace_events[-1].payload["excluded_entity_edge_limit_count"] == 1
    assert compiler_run.trace_events[-1].payload["hybrid_memory_requested"] is False
    assert compiler_run.trace_events[-1].payload["hybrid_memory_candidate_count"] == 2
    assert compiler_run.trace_events[-1].payload["hybrid_memory_merged_candidate_count"] == 1
    assert compiler_run.trace_events[-1].payload["hybrid_memory_deduplicated_count"] == 0
    assert compiler_run.trace_events[-1].payload["artifact_retrieval_requested"] is False
    assert compiler_run.trace_events[-1].payload["artifact_lexical_retrieval_requested"] is False
    assert compiler_run.trace_events[-1].payload["artifact_semantic_retrieval_requested"] is False
    assert compiler_run.trace_events[-1].payload["artifact_lexical_candidate_count"] == 0
    assert compiler_run.trace_events[-1].payload["artifact_semantic_candidate_count"] == 0
    assert compiler_run.trace_events[-1].payload["artifact_merged_candidate_count"] == 0
    assert compiler_run.trace_events[-1].payload["artifact_deduplicated_count"] == 0
    assert compiler_run.trace_events[-1].payload["included_artifact_chunk_count"] == 0
    assert compiler_run.trace_events[-1].payload["included_dual_source_artifact_chunk_count"] == 0
    assert compiler_run.trace_events[-1].payload["excluded_artifact_chunk_limit_count"] == 0
    assert compiler_run.trace_events[-1].payload["excluded_uningested_artifact_count"] == 0


class SemanticCompileStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
        self.config_id = uuid4()
        self.memory_ids = [uuid4(), uuid4(), uuid4()]
        self.event_ids = [uuid4(), uuid4(), uuid4()]

    def get_embedding_config_optional(self, embedding_config_id):
        if embedding_config_id != self.config_id:
            return None
        return {"id": self.config_id, "dimensions": 3}

    def retrieve_semantic_memory_matches(self, *, embedding_config_id, query_vector, limit):
        assert embedding_config_id == self.config_id
        assert query_vector == [1.0, 0.0, 0.0]
        assert limit > 1000
        return [
            {
                "id": self.memory_ids[0],
                "user_id": uuid4(),
                "memory_key": "user.preference.breakfast",
                "value": {"likes": "porridge"},
                "status": "active",
                "source_event_ids": [str(self.event_ids[0])],
                "created_at": self.base_time,
                "updated_at": self.base_time,
                "deleted_at": None,
                "score": 1.0,
            },
            {
                "id": self.memory_ids[1],
                "user_id": uuid4(),
                "memory_key": "user.preference.lunch",
                "value": {"likes": "ramen"},
                "status": "active",
                "source_event_ids": [str(self.event_ids[1])],
                "created_at": self.base_time + timedelta(minutes=1),
                "updated_at": self.base_time + timedelta(minutes=1),
                "deleted_at": None,
                "score": 1.0,
            },
        ]

    def list_memory_embeddings_for_config(self, embedding_config_id):
        assert embedding_config_id == self.config_id
        return [
            {
                "id": uuid4(),
                "user_id": uuid4(),
                "memory_id": self.memory_ids[2],
                "embedding_config_id": self.config_id,
                "dimensions": 3,
                "vector": [1.0, 0.0, 0.0],
                "created_at": self.base_time + timedelta(minutes=2),
                "updated_at": self.base_time + timedelta(minutes=2),
            }
        ]


class ArtifactCompileStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
        self.config_id = uuid4()
        self.task_id = uuid4()
        self.artifact_ids = [uuid4(), uuid4(), uuid4(), uuid4()]
        self.chunk_ids = [uuid4(), uuid4(), uuid4(), uuid4()]

    def get_embedding_config_optional(self, embedding_config_id):
        if embedding_config_id != self.config_id:
            return None
        return {"id": self.config_id, "dimensions": 3}

    def get_task_optional(self, task_id):
        if task_id != self.task_id:
            return None
        return {"id": self.task_id}

    def list_task_artifacts_for_task(self, task_id):
        assert task_id == self.task_id
        return [
            {
                "id": self.artifact_ids[0],
                "task_id": self.task_id,
                "task_workspace_id": uuid4(),
                "status": "registered",
                "ingestion_status": "ingested",
                "relative_path": "docs/a.txt",
                "media_type_hint": "text/plain",
                "created_at": self.base_time,
                "updated_at": self.base_time,
            },
            {
                "id": self.artifact_ids[1],
                "task_id": self.task_id,
                "task_workspace_id": uuid4(),
                "status": "registered",
                "ingestion_status": "ingested",
                "relative_path": "notes/b.md",
                "media_type_hint": "text/markdown",
                "created_at": self.base_time + timedelta(minutes=1),
                "updated_at": self.base_time + timedelta(minutes=1),
            },
            {
                "id": self.artifact_ids[2],
                "task_id": self.task_id,
                "task_workspace_id": uuid4(),
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": "notes/hidden.txt",
                "media_type_hint": "text/plain",
                "created_at": self.base_time + timedelta(minutes=2),
                "updated_at": self.base_time + timedelta(minutes=2),
            },
            {
                "id": self.artifact_ids[3],
                "task_id": self.task_id,
                "task_workspace_id": uuid4(),
                "status": "registered",
                "ingestion_status": "ingested",
                "relative_path": "notes/c.txt",
                "media_type_hint": "text/plain",
                "created_at": self.base_time + timedelta(minutes=3),
                "updated_at": self.base_time + timedelta(minutes=3),
            },
        ]

    def list_task_artifact_chunks(self, task_artifact_id):
        if task_artifact_id == self.artifact_ids[0]:
            return [
                {
                    "id": self.chunk_ids[0],
                    "task_artifact_id": task_artifact_id,
                    "sequence_no": 1,
                    "char_start": 0,
                    "char_end_exclusive": 14,
                    "text": "beta alpha doc",
                    "created_at": self.base_time,
                    "updated_at": self.base_time,
                }
            ]
        if task_artifact_id == self.artifact_ids[1]:
            return [
                {
                    "id": self.chunk_ids[1],
                    "task_artifact_id": task_artifact_id,
                    "sequence_no": 1,
                    "char_start": 0,
                    "char_end_exclusive": 15,
                    "text": "alpha beta note",
                    "created_at": self.base_time,
                    "updated_at": self.base_time,
                }
            ]
        if task_artifact_id == self.artifact_ids[3]:
            return [
                {
                    "id": self.chunk_ids[2],
                    "task_artifact_id": task_artifact_id,
                    "sequence_no": 1,
                    "char_start": 0,
                    "char_end_exclusive": 9,
                    "text": "beta only",
                    "created_at": self.base_time,
                    "updated_at": self.base_time,
                }
            ]
        return []

    def get_task_artifact_optional(self, task_artifact_id):
        for artifact_row in self.list_task_artifacts_for_task(self.task_id):
            if artifact_row["id"] == task_artifact_id:
                return artifact_row
        return None

    def retrieve_task_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_id,
        embedding_config_id,
        query_vector,
        limit,
    ):
        assert task_id == self.task_id
        assert embedding_config_id == self.config_id
        assert query_vector == [1.0, 0.0, 0.0]
        rows = [
            {
                "id": self.chunk_ids[0],
                "user_id": uuid4(),
                "task_id": self.task_id,
                "task_artifact_id": self.artifact_ids[0],
                "relative_path": "docs/a.txt",
                "media_type_hint": "text/plain",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 14,
                "text": "beta alpha doc",
                "created_at": self.base_time,
                "updated_at": self.base_time,
                "embedding_config_id": self.config_id,
                "score": 1.0,
            },
            {
                "id": self.chunk_ids[1],
                "user_id": uuid4(),
                "task_id": self.task_id,
                "task_artifact_id": self.artifact_ids[1],
                "relative_path": "notes/b.md",
                "media_type_hint": "text/markdown",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 15,
                "text": "alpha beta note",
                "created_at": self.base_time + timedelta(minutes=1),
                "updated_at": self.base_time + timedelta(minutes=1),
                "embedding_config_id": self.config_id,
                "score": 1.0,
            },
            {
                "id": self.chunk_ids[3],
                "user_id": uuid4(),
                "task_id": self.task_id,
                "task_artifact_id": self.artifact_ids[3],
                "relative_path": "notes/c.txt",
                "media_type_hint": "text/plain",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 9,
                "text": "beta only",
                "created_at": self.base_time + timedelta(minutes=3),
                "updated_at": self.base_time + timedelta(minutes=3),
                "embedding_config_id": self.config_id,
                "score": 0.25,
            },
        ]
        return list(rows[:limit])

    def retrieve_artifact_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_artifact_id,
        embedding_config_id,
        query_vector,
        limit,
    ):
        assert embedding_config_id == self.config_id
        assert query_vector == [1.0, 0.0, 0.0]
        rows = [
            row
            for row in self.retrieve_task_scoped_semantic_artifact_chunk_matches(
                task_id=self.task_id,
                embedding_config_id=embedding_config_id,
                query_vector=query_vector,
                limit=10,
            )
            if row["task_artifact_id"] == task_artifact_id
        ]
        return list(rows[:limit])


def test_compile_artifact_chunk_section_orders_limits_and_excludes_non_ingested() -> None:
    store = ArtifactCompileStoreStub()

    artifact_section = _compile_artifact_chunk_section(
        store,  # type: ignore[arg-type]
        artifact_retrieval=CompileContextTaskScopedArtifactRetrievalInput(
            task_id=store.task_id,
            query="Alpha beta",
            limit=2,
        ),
        semantic_artifact_retrieval=None,
    )

    assert artifact_section.items == [
        {
            "id": str(store.chunk_ids[0]),
            "task_id": str(store.task_id),
            "task_artifact_id": str(store.artifact_ids[0]),
            "relative_path": "docs/a.txt",
            "media_type": "text/plain",
            "sequence_no": 1,
            "char_start": 0,
            "char_end_exclusive": 14,
            "text": "beta alpha doc",
            "source_provenance": {
                "sources": ["lexical"],
                "lexical_match": {
                    "matched_query_terms": ["alpha", "beta"],
                    "matched_query_term_count": 2,
                    "first_match_char_start": 0,
                },
                "semantic_score": None,
            },
        },
        {
            "id": str(store.chunk_ids[1]),
            "task_id": str(store.task_id),
            "task_artifact_id": str(store.artifact_ids[1]),
            "relative_path": "notes/b.md",
            "media_type": "text/markdown",
            "sequence_no": 1,
            "char_start": 0,
            "char_end_exclusive": 15,
            "text": "alpha beta note",
            "source_provenance": {
                "sources": ["lexical"],
                "lexical_match": {
                    "matched_query_terms": ["alpha", "beta"],
                    "matched_query_term_count": 2,
                    "first_match_char_start": 0,
                },
                "semantic_score": None,
            },
        },
    ]
    assert artifact_section.summary == {
        "requested": True,
        "lexical_requested": True,
        "semantic_requested": False,
        "scope": {"kind": "task", "task_id": str(store.task_id)},
        "query": "Alpha beta",
        "query_terms": ["alpha", "beta"],
        "embedding_config_id": None,
        "query_vector_dimensions": 0,
        "limit": 2,
        "lexical_limit": 2,
        "semantic_limit": 0,
        "searched_artifact_count": 3,
        "lexical_candidate_count": 3,
        "semantic_candidate_count": 0,
        "merged_candidate_count": 3,
        "deduplicated_count": 0,
        "included_count": 2,
        "included_lexical_only_count": 2,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 0,
        "excluded_uningested_artifact_count": 1,
        "excluded_limit_count": 1,
        "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
        "similarity_metric": None,
        "source_precedence": ["lexical", "semantic"],
        "lexical_order": [
            "matched_query_term_count_desc",
            "first_match_char_start_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
        "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
        "merged_order": [
            "source_precedence_asc",
            "lexical_rank_asc",
            "semantic_rank_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
    }
    assert [decision.reason for decision in artifact_section.decisions] == [
        "hybrid_artifact_not_ingested",
        "within_hybrid_artifact_chunk_limit",
        "within_hybrid_artifact_chunk_limit",
        "hybrid_artifact_chunk_limit_exceeded",
    ]
    assert artifact_section.decisions[0].metadata["relative_path"] == "notes/hidden.txt"
    assert artifact_section.decisions[-1].metadata["relative_path"] == "notes/c.txt"


def test_compile_artifact_chunk_section_supports_semantic_only_scope() -> None:
    store = ArtifactCompileStoreStub()

    artifact_section = _compile_artifact_chunk_section(
        store,  # type: ignore[arg-type]
        artifact_retrieval=None,
        semantic_artifact_retrieval=CompileContextTaskScopedSemanticArtifactRetrievalInput(
            task_id=store.task_id,
            embedding_config_id=store.config_id,
            query_vector=(1.0, 0.0, 0.0),
            limit=2,
        ),
    )

    assert artifact_section.items == [
        {
            "id": str(store.chunk_ids[0]),
            "task_id": str(store.task_id),
            "task_artifact_id": str(store.artifact_ids[0]),
            "relative_path": "docs/a.txt",
            "media_type": "text/plain",
            "sequence_no": 1,
            "char_start": 0,
            "char_end_exclusive": 14,
            "text": "beta alpha doc",
            "source_provenance": {
                "sources": ["semantic"],
                "lexical_match": None,
                "semantic_score": 1.0,
            },
        },
        {
            "id": str(store.chunk_ids[1]),
            "task_id": str(store.task_id),
            "task_artifact_id": str(store.artifact_ids[1]),
            "relative_path": "notes/b.md",
            "media_type": "text/markdown",
            "sequence_no": 1,
            "char_start": 0,
            "char_end_exclusive": 15,
            "text": "alpha beta note",
            "source_provenance": {
                "sources": ["semantic"],
                "lexical_match": None,
                "semantic_score": 1.0,
            },
        },
    ]
    assert artifact_section.summary == {
        "requested": True,
        "lexical_requested": False,
        "semantic_requested": True,
        "scope": {"kind": "task", "task_id": str(store.task_id)},
        "query": None,
        "query_terms": [],
        "embedding_config_id": str(store.config_id),
        "query_vector_dimensions": 3,
        "limit": 2,
        "lexical_limit": 0,
        "semantic_limit": 2,
        "searched_artifact_count": 3,
        "lexical_candidate_count": 0,
        "semantic_candidate_count": 3,
        "merged_candidate_count": 3,
        "deduplicated_count": 0,
        "included_count": 2,
        "included_lexical_only_count": 0,
        "included_semantic_only_count": 2,
        "included_dual_source_count": 0,
        "excluded_uningested_artifact_count": 1,
        "excluded_limit_count": 1,
        "matching_rule": None,
        "similarity_metric": "cosine_similarity",
        "source_precedence": ["lexical", "semantic"],
        "lexical_order": [
            "matched_query_term_count_desc",
            "first_match_char_start_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
        "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
        "merged_order": [
            "source_precedence_asc",
            "lexical_rank_asc",
            "semantic_rank_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
    }
    assert [decision.reason for decision in artifact_section.decisions] == [
        "hybrid_artifact_not_ingested",
        "within_hybrid_artifact_chunk_limit",
        "within_hybrid_artifact_chunk_limit",
        "hybrid_artifact_chunk_limit_exceeded",
    ]
    assert artifact_section.decisions[0].metadata["relative_path"] == "notes/hidden.txt"
    assert artifact_section.decisions[-1].metadata["relative_path"] == "notes/c.txt"


def test_compile_artifact_chunk_section_merges_dual_source_provenance_for_artifact_scope() -> None:
    store = ArtifactCompileStoreStub()

    artifact_section = _compile_artifact_chunk_section(
        store,  # type: ignore[arg-type]
        artifact_retrieval=CompileContextArtifactScopedArtifactRetrievalInput(
            task_artifact_id=store.artifact_ids[1],
            query="Alpha beta",
            limit=2,
        ),
        semantic_artifact_retrieval=CompileContextArtifactScopedSemanticArtifactRetrievalInput(
            task_artifact_id=store.artifact_ids[1],
            embedding_config_id=store.config_id,
            query_vector=(1.0, 0.0, 0.0),
            limit=2,
        ),
    )

    assert artifact_section.items == [
        {
            "id": str(store.chunk_ids[1]),
            "task_id": str(store.task_id),
            "task_artifact_id": str(store.artifact_ids[1]),
            "relative_path": "notes/b.md",
            "media_type": "text/markdown",
            "sequence_no": 1,
            "char_start": 0,
            "char_end_exclusive": 15,
            "text": "alpha beta note",
            "source_provenance": {
                "sources": ["lexical", "semantic"],
                "lexical_match": {
                    "matched_query_terms": ["alpha", "beta"],
                    "matched_query_term_count": 2,
                    "first_match_char_start": 0,
                },
                "semantic_score": 1.0,
            },
        }
    ]
    assert artifact_section.summary == {
        "requested": True,
        "lexical_requested": True,
        "semantic_requested": True,
        "scope": {
            "kind": "artifact",
            "task_id": str(store.task_id),
            "task_artifact_id": str(store.artifact_ids[1]),
        },
        "query": "Alpha beta",
        "query_terms": ["alpha", "beta"],
        "embedding_config_id": str(store.config_id),
        "query_vector_dimensions": 3,
        "limit": 2,
        "lexical_limit": 2,
        "semantic_limit": 2,
        "searched_artifact_count": 1,
        "lexical_candidate_count": 1,
        "semantic_candidate_count": 1,
        "merged_candidate_count": 1,
        "deduplicated_count": 1,
        "included_count": 1,
        "included_lexical_only_count": 0,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 1,
        "excluded_uningested_artifact_count": 0,
        "excluded_limit_count": 0,
        "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
        "similarity_metric": "cosine_similarity",
        "source_precedence": ["lexical", "semantic"],
        "lexical_order": [
            "matched_query_term_count_desc",
            "first_match_char_start_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
        "semantic_order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
        "merged_order": [
            "source_precedence_asc",
            "lexical_rank_asc",
            "semantic_rank_asc",
            "relative_path_asc",
            "sequence_no_asc",
            "id_asc",
        ],
    }
    assert [decision.reason for decision in artifact_section.decisions] == [
        "hybrid_artifact_chunk_deduplicated",
        "within_hybrid_artifact_chunk_limit",
    ]
    assert artifact_section.decisions[1].metadata["selected_sources"] == ["lexical", "semantic"]


def test_compile_memory_section_orders_limits_and_excludes_deleted() -> None:
    store = SemanticCompileStoreStub()
    deleted_memory = {
        "id": store.memory_ids[2],
        "user_id": uuid4(),
        "memory_key": "user.preference.deleted",
        "value": {"likes": "hidden"},
        "status": "deleted",
        "source_event_ids": [str(store.event_ids[2])],
        "created_at": store.base_time + timedelta(minutes=2),
        "updated_at": store.base_time + timedelta(minutes=3),
        "deleted_at": store.base_time + timedelta(minutes=3),
    }

    memory_section = _compile_memory_section(
        store,  # type: ignore[arg-type]
        memories=[deleted_memory],
        limits=ContextCompilerLimits(max_memories=1),
        semantic_retrieval=CompileContextSemanticRetrievalInput(
            embedding_config_id=store.config_id,
            query_vector=(1.0, 0.0, 0.0),
            limit=1,
        ),
    )

    assert memory_section.items == [
        {
            "id": str(store.memory_ids[0]),
            "memory_key": "user.preference.breakfast",
            "value": {"likes": "porridge"},
            "status": "active",
            "source_event_ids": [str(store.event_ids[0])],
            "created_at": store.base_time.isoformat(),
            "updated_at": store.base_time.isoformat(),
            "source_provenance": {
                "sources": ["semantic"],
                "semantic_score": 1.0,
            },
        }
    ]
    assert memory_section.summary == {
        "candidate_count": 2,
        "included_count": 1,
        "excluded_deleted_count": 1,
        "excluded_limit_count": 0,
        "hybrid_retrieval": {
            "requested": True,
            "embedding_config_id": str(store.config_id),
            "query_vector_dimensions": 3,
            "semantic_limit": 1,
            "symbolic_selected_count": 0,
            "semantic_selected_count": 1,
            "merged_candidate_count": 1,
            "deduplicated_count": 0,
            "included_symbolic_only_count": 0,
            "included_semantic_only_count": 1,
            "included_dual_source_count": 0,
            "similarity_metric": "cosine_similarity",
            "source_precedence": ["symbolic", "semantic"],
            "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
            "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
        },
    }
    assert [decision.reason for decision in memory_section.decisions] == [
        "within_hybrid_memory_limit",
        "hybrid_memory_deleted",
    ]
    assert memory_section.decisions[-1].metadata["selected_sources"] == ["symbolic"]
