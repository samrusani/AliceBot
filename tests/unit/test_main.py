from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.compiler import CompiledTraceRun
from alicebot_api.contracts import AdmissionDecisionOutput
from alicebot_api.embedding import (
    EmbeddingConfigValidationError,
    MemoryEmbeddingNotFoundError,
    MemoryEmbeddingValidationError,
)
from alicebot_api.entity import EntityNotFoundError, EntityValidationError
from alicebot_api.entity_edge import EntityEdgeValidationError
from alicebot_api.memory import MemoryAdmissionValidationError, MemoryReviewNotFoundError
from alicebot_api.response_generation import ResponseFailure
from alicebot_api.semantic_retrieval import SemanticMemoryRetrievalValidationError
from alicebot_api.store import ContinuityStoreInvariantError


def test_healthcheck_reports_ok_when_database_is_reachable(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://db",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
        healthcheck_timeout_seconds=7,
    )
    ping_calls: list[tuple[str, int]] = []

    def fake_get_settings() -> Settings:
        return settings

    def fake_ping_database(database_url: str, timeout_seconds: int) -> bool:
        ping_calls.append((database_url, timeout_seconds))
        return True

    monkeypatch.setattr(main_module, "get_settings", fake_get_settings)
    monkeypatch.setattr(main_module, "ping_database", fake_ping_database)

    response = main_module.healthcheck()

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "status": "ok",
        "environment": "test",
        "services": {
            "database": {"status": "ok"},
            "redis": {"status": "not_checked", "url": "redis://cache:6379/0"},
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": "http://object-store",
            },
        },
    }
    assert ping_calls == [("postgresql://db", 7)]


def test_healthcheck_reports_degraded_when_database_is_unreachable(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://db",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
        healthcheck_timeout_seconds=4,
    )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: False)

    response = main_module.healthcheck()

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "degraded",
        "environment": "test",
        "services": {
            "database": {"status": "unreachable"},
            "redis": {"status": "not_checked", "url": "redis://cache:6379/0"},
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": "http://object-store",
            },
        },
    }


def test_healthcheck_route_is_registered() -> None:
    route_paths = {route.path for route in main_module.app.routes}

    assert "/healthz" in route_paths
    assert "/v0/context/compile" in route_paths
    assert "/v0/responses" in route_paths
    assert "/v0/memories/admit" in route_paths
    assert "/v0/consents" in route_paths
    assert "/v0/policies" in route_paths
    assert "/v0/policies/{policy_id}" in route_paths
    assert "/v0/policies/evaluate" in route_paths
    assert "/v0/memories/extract-explicit-preferences" in route_paths
    assert "/v0/memories" in route_paths
    assert "/v0/memories/review-queue" in route_paths
    assert "/v0/memories/evaluation-summary" in route_paths
    assert "/v0/memories/semantic-retrieval" in route_paths
    assert "/v0/memories/{memory_id}" in route_paths
    assert "/v0/memories/{memory_id}/revisions" in route_paths
    assert "/v0/memories/{memory_id}/labels" in route_paths
    assert "/v0/embedding-configs" in route_paths
    assert "/v0/memory-embeddings" in route_paths
    assert "/v0/memories/{memory_id}/embeddings" in route_paths
    assert "/v0/memory-embeddings/{memory_embedding_id}" in route_paths
    assert "/v0/entities" in route_paths
    assert "/v0/entity-edges" in route_paths
    assert "/v0/tools/route" in route_paths
    assert "/v0/execution-budgets" in route_paths
    assert "/v0/execution-budgets/{execution_budget_id}" in route_paths
    assert "/v0/execution-budgets/{execution_budget_id}/deactivate" in route_paths
    assert "/v0/execution-budgets/{execution_budget_id}/supersede" in route_paths
    assert "/v0/tool-executions" in route_paths
    assert "/v0/tool-executions/{execution_id}" in route_paths
    assert "/v0/tasks" in route_paths
    assert "/v0/tasks/{task_id}" in route_paths
    assert "/v0/tasks/{task_id}/workspace" in route_paths
    assert "/v0/tasks/{task_id}/steps" in route_paths
    assert "/v0/task-workspaces" in route_paths
    assert "/v0/task-workspaces/{task_workspace_id}" in route_paths
    assert "/v0/task-workspaces/{task_workspace_id}/artifacts" in route_paths
    assert "/v0/task-artifacts" in route_paths
    assert "/v0/task-artifacts/{task_artifact_id}" in route_paths
    assert "/v0/task-steps/{task_step_id}" in route_paths
    assert "/v0/task-steps/{task_step_id}/transition" in route_paths
    assert "/v0/entities/{entity_id}" in route_paths
    assert "/v0/entities/{entity_id}/edges" in route_paths


def test_redact_url_credentials_strips_embedded_secrets() -> None:
    assert main_module.redact_url_credentials("redis://alicebot:supersecret@cache:6379/0") == (
        "redis://cache:6379/0"
    )
    assert main_module.redact_url_credentials("redis://cache:6379/0") == "redis://cache:6379/0"


def test_build_healthcheck_payload_keeps_boundary_statuses_consistent() -> None:
    settings = Settings(
        app_env="test",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
    )

    assert main_module.build_healthcheck_payload(settings, database_ok=True) == {
        "status": "ok",
        "environment": "test",
        "services": {
            "database": {"status": "ok"},
            "redis": {"status": "not_checked", "url": "redis://cache:6379/0"},
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": "http://object-store",
            },
        },
    }
    assert main_module.build_healthcheck_payload(settings, database_ok=False)["services"][
        "database"
    ] == {"status": "unreachable"}


def test_compile_context_returns_trace_and_context_pack(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_compile_and_persist_trace(store, *, user_id, thread_id, limits, semantic_retrieval):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["thread_id"] = thread_id
        captured["limits"] = limits
        captured["semantic_retrieval"] = semantic_retrieval
        return CompiledTraceRun(
            trace_id="trace-123",
            trace_event_count=5,
            context_pack={
                "compiler_version": "continuity_v0",
                "scope": {"user_id": str(user_id), "thread_id": str(thread_id)},
                "limits": {
                    "max_sessions": 2,
                    "max_events": 4,
                    "max_memories": 3,
                    "max_entities": 2,
                    "max_entity_edges": 6,
                },
                "user": {
                    "id": str(user_id),
                    "email": "owner@example.com",
                    "display_name": "Owner",
                    "created_at": "2026-03-11T09:00:00+00:00",
                },
                "thread": {
                    "id": str(thread_id),
                    "title": "Thread",
                    "created_at": "2026-03-11T09:00:00+00:00",
                    "updated_at": "2026-03-11T09:01:00+00:00",
                },
                "sessions": [],
                "events": [],
                "memories": [
                    {
                        "id": "memory-123",
                        "memory_key": "user.preference.coffee",
                        "value": {"likes": "oat milk"},
                        "status": "active",
                        "source_event_ids": ["event-1"],
                        "created_at": "2026-03-11T09:00:00+00:00",
                        "updated_at": "2026-03-11T09:02:00+00:00",
                        "source_provenance": {"sources": ["symbolic"], "semantic_score": None},
                    }
                ],
                "memory_summary": {
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
                },
                "entities": [
                    {
                        "id": "entity-123",
                        "entity_type": "project",
                        "name": "AliceBot",
                        "source_memory_ids": ["memory-123"],
                        "created_at": "2026-03-11T09:03:00+00:00",
                    }
                ],
                "entity_summary": {
                    "candidate_count": 2,
                    "included_count": 1,
                    "excluded_limit_count": 1,
                },
                "entity_edges": [
                    {
                        "id": "edge-123",
                        "from_entity_id": "entity-123",
                        "to_entity_id": "entity-999",
                        "relationship_type": "depends_on",
                        "valid_from": "2026-03-11T09:04:00+00:00",
                        "valid_to": None,
                        "source_memory_ids": ["memory-123"],
                        "created_at": "2026-03-11T09:04:00+00:00",
                    }
                ],
                "entity_edge_summary": {
                    "anchor_entity_count": 1,
                    "candidate_count": 2,
                    "included_count": 1,
                    "excluded_limit_count": 1,
                },
            },
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "compile_and_persist_trace", fake_compile_and_persist_trace)

    response = main_module.compile_context(
        main_module.CompileContextRequest(
            user_id=user_id,
            thread_id=thread_id,
            max_sessions=2,
            max_events=4,
            max_memories=3,
            max_entities=2,
            max_entity_edges=6,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "trace_id": "trace-123",
        "trace_event_count": 5,
        "context_pack": {
            "compiler_version": "continuity_v0",
            "scope": {"user_id": str(user_id), "thread_id": str(thread_id)},
            "limits": {
                "max_sessions": 2,
                "max_events": 4,
                "max_memories": 3,
                "max_entities": 2,
                "max_entity_edges": 6,
            },
            "user": {
                "id": str(user_id),
                "email": "owner@example.com",
                "display_name": "Owner",
                "created_at": "2026-03-11T09:00:00+00:00",
            },
            "thread": {
                "id": str(thread_id),
                "title": "Thread",
                "created_at": "2026-03-11T09:00:00+00:00",
                "updated_at": "2026-03-11T09:01:00+00:00",
            },
            "sessions": [],
            "events": [],
            "memories": [
                {
                    "id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "status": "active",
                    "source_event_ids": ["event-1"],
                    "created_at": "2026-03-11T09:00:00+00:00",
                    "updated_at": "2026-03-11T09:02:00+00:00",
                    "source_provenance": {"sources": ["symbolic"], "semantic_score": None},
                }
            ],
            "memory_summary": {
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
            },
            "entities": [
                {
                    "id": "entity-123",
                    "entity_type": "project",
                    "name": "AliceBot",
                    "source_memory_ids": ["memory-123"],
                    "created_at": "2026-03-11T09:03:00+00:00",
                }
            ],
            "entity_summary": {
                "candidate_count": 2,
                "included_count": 1,
                "excluded_limit_count": 1,
            },
            "entity_edges": [
                {
                    "id": "edge-123",
                    "from_entity_id": "entity-123",
                    "to_entity_id": "entity-999",
                    "relationship_type": "depends_on",
                    "valid_from": "2026-03-11T09:04:00+00:00",
                    "valid_to": None,
                    "source_memory_ids": ["memory-123"],
                    "created_at": "2026-03-11T09:04:00+00:00",
                }
            ],
            "entity_edge_summary": {
                "anchor_entity_count": 1,
                "candidate_count": 2,
                "included_count": 1,
                "excluded_limit_count": 1,
            },
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["thread_id"] == thread_id
    assert captured["limits"].max_sessions == 2
    assert captured["limits"].max_events == 4
    assert captured["limits"].max_memories == 3
    assert captured["limits"].max_entities == 2
    assert captured["limits"].max_entity_edges == 6
    assert captured["semantic_retrieval"] is None


def test_compile_context_returns_not_found_when_scope_row_is_missing(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "compile_and_persist_trace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ContinuityStoreInvariantError("get_thread did not return a row from the database")
        ),
    )

    response = main_module.compile_context(
        main_module.CompileContextRequest(user_id=uuid4(), thread_id=uuid4())
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": "get_thread did not return a row from the database",
    }


def test_compile_context_routes_semantic_inputs_and_validation_errors(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_compile_and_persist_trace(store, *, user_id, thread_id, limits, semantic_retrieval):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["thread_id"] = thread_id
        captured["limits"] = limits
        captured["semantic_retrieval"] = semantic_retrieval
        return CompiledTraceRun(
            trace_id="trace-semantic",
            trace_event_count=7,
            context_pack={
                "compiler_version": "continuity_v0",
                "scope": {"user_id": str(user_id), "thread_id": str(thread_id)},
                "limits": {
                    "max_sessions": 3,
                    "max_events": 8,
                    "max_memories": 5,
                    "max_entities": 5,
                    "max_entity_edges": 10,
                },
                "user": {
                    "id": str(user_id),
                    "email": "owner@example.com",
                    "display_name": "Owner",
                    "created_at": "2026-03-12T09:00:00+00:00",
                },
                "thread": {
                    "id": str(thread_id),
                    "title": "Thread",
                    "created_at": "2026-03-12T09:00:00+00:00",
                    "updated_at": "2026-03-12T09:01:00+00:00",
                },
                "sessions": [],
                "events": [],
                "memories": [
                    {
                        "id": "memory-123",
                        "memory_key": "user.preference.coffee",
                        "value": {"likes": "oat milk"},
                        "status": "active",
                        "source_event_ids": ["event-123"],
                        "created_at": "2026-03-12T09:00:00+00:00",
                        "updated_at": "2026-03-12T09:00:00+00:00",
                        "source_provenance": {
                            "sources": ["symbolic", "semantic"],
                            "semantic_score": 0.99,
                        },
                    }
                ],
                "memory_summary": {
                    "candidate_count": 1,
                    "included_count": 1,
                    "excluded_deleted_count": 0,
                    "excluded_limit_count": 0,
                    "hybrid_retrieval": {
                        "requested": True,
                        "embedding_config_id": str(config_id),
                        "query_vector_dimensions": 3,
                        "semantic_limit": 2,
                        "symbolic_selected_count": 1,
                        "semantic_selected_count": 1,
                        "merged_candidate_count": 1,
                        "deduplicated_count": 1,
                        "included_symbolic_only_count": 0,
                        "included_semantic_only_count": 0,
                        "included_dual_source_count": 1,
                        "similarity_metric": "cosine_similarity",
                        "source_precedence": ["symbolic", "semantic"],
                        "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
                        "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
                    },
                },
                "entities": [],
                "entity_summary": {
                    "candidate_count": 0,
                    "included_count": 0,
                    "excluded_limit_count": 0,
                },
                "entity_edges": [],
                "entity_edge_summary": {
                    "anchor_entity_count": 0,
                    "candidate_count": 0,
                    "included_count": 0,
                    "excluded_limit_count": 0,
                },
            },
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "compile_and_persist_trace", fake_compile_and_persist_trace)

    response = main_module.compile_context(
        main_module.CompileContextRequest(
            user_id=user_id,
            thread_id=thread_id,
            semantic=main_module.CompileContextSemanticRequest(
                embedding_config_id=config_id,
                query_vector=[0.1, 0.2, 0.3],
                limit=2,
            ),
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["context_pack"]["memory_summary"]["hybrid_retrieval"] == {
        "requested": True,
        "embedding_config_id": str(config_id),
        "query_vector_dimensions": 3,
        "semantic_limit": 2,
        "symbolic_selected_count": 1,
        "semantic_selected_count": 1,
        "merged_candidate_count": 1,
        "deduplicated_count": 1,
        "included_symbolic_only_count": 0,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 1,
        "similarity_metric": "cosine_similarity",
        "source_precedence": ["symbolic", "semantic"],
        "symbolic_order": ["updated_at_asc", "created_at_asc", "id_asc"],
        "semantic_order": ["score_desc", "created_at_asc", "id_asc"],
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["semantic_retrieval"].embedding_config_id == config_id
    assert captured["semantic_retrieval"].query_vector == (0.1, 0.2, 0.3)
    assert captured["semantic_retrieval"].limit == 2

    monkeypatch.setattr(
        main_module,
        "compile_and_persist_trace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SemanticMemoryRetrievalValidationError(
                "embedding_config_id must reference an existing embedding config owned by the user"
            )
        ),
    )

    error_response = main_module.compile_context(
        main_module.CompileContextRequest(
            user_id=user_id,
            thread_id=thread_id,
            semantic=main_module.CompileContextSemanticRequest(
                embedding_config_id=config_id,
                query_vector=[0.1, 0.2, 0.3],
                limit=2,
            ),
        )
    )

    assert error_response.status_code == 400
    assert json.loads(error_response.body) == {
        "detail": "embedding_config_id must reference an existing embedding config owned by the user"
    }


def test_generate_assistant_response_returns_assistant_and_trace_payload(monkeypatch) -> None:
    user_id = uuid4()
    thread_id = uuid4()
    settings = Settings(
        database_url="postgresql://app",
        model_provider="openai_responses",
        model_name="gpt-5-mini",
    )
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_generate_response(store, *, settings, user_id, thread_id, message_text, limits):
        captured["store_type"] = type(store).__name__
        captured["settings"] = settings
        captured["user_id"] = user_id
        captured["thread_id"] = thread_id
        captured["message_text"] = message_text
        captured["limits"] = limits
        return {
            "assistant": {
                "event_id": "assistant-event-123",
                "sequence_no": 5,
                "text": "Hello back.",
                "model_provider": "openai_responses",
                "model": "gpt-5-mini",
            },
            "trace": {
                "compile_trace_id": "compile-trace-123",
                "compile_trace_event_count": 11,
                "response_trace_id": "response-trace-123",
                "response_trace_event_count": 2,
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "generate_response", fake_generate_response)

    response = main_module.generate_assistant_response(
        main_module.GenerateResponseRequest(
            user_id=user_id,
            thread_id=thread_id,
            message="Hello?",
            max_sessions=2,
            max_events=4,
            max_memories=3,
            max_entities=2,
            max_entity_edges=6,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "assistant": {
            "event_id": "assistant-event-123",
            "sequence_no": 5,
            "text": "Hello back.",
            "model_provider": "openai_responses",
            "model": "gpt-5-mini",
        },
        "trace": {
            "compile_trace_id": "compile-trace-123",
            "compile_trace_event_count": 11,
            "response_trace_id": "response-trace-123",
            "response_trace_event_count": 2,
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["thread_id"] == thread_id
    assert captured["message_text"] == "Hello?"
    assert captured["limits"].max_sessions == 2
    assert captured["limits"].max_events == 4
    assert captured["limits"].max_memories == 3
    assert captured["limits"].max_entities == 2
    assert captured["limits"].max_entity_edges == 6


def test_generate_assistant_response_returns_502_with_trace_when_model_invocation_fails(
    monkeypatch,
) -> None:
    user_id = uuid4()
    thread_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "generate_response",
        lambda *_args, **_kwargs: ResponseFailure(
            detail="upstream timeout",
            trace={
                "compile_trace_id": "compile-trace-123",
                "compile_trace_event_count": 9,
                "response_trace_id": "response-trace-123",
                "response_trace_event_count": 2,
            },
        ),
    )

    response = main_module.generate_assistant_response(
        main_module.GenerateResponseRequest(
            user_id=user_id,
            thread_id=thread_id,
            message="Hello?",
        )
    )

    assert response.status_code == 502
    assert json.loads(response.body) == {
        "detail": "upstream timeout",
        "trace": {
            "compile_trace_id": "compile-trace-123",
            "compile_trace_event_count": 9,
            "response_trace_id": "response-trace-123",
            "response_trace_event_count": 2,
        },
    }


def test_admit_memory_returns_decision_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_admit_memory_candidate(store, *, user_id, candidate):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["candidate"] = candidate
        return AdmissionDecisionOutput(
            action="ADD",
            reason="source_backed_add",
            memory={
                "id": "memory-123",
                "user_id": str(user_id),
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-11T09:00:00+00:00",
                "updated_at": "2026-03-11T09:00:00+00:00",
                "deleted_at": None,
            },
            revision={
                "id": "revision-123",
                "user_id": str(user_id),
                "memory_id": "memory-123",
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": "user.preference.coffee",
                "previous_value": None,
                "new_value": {"likes": "oat milk"},
                "source_event_ids": ["event-1"],
                "candidate": {
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "source_event_ids": ["event-1"],
                    "delete_requested": False,
                },
                "created_at": "2026-03-11T09:00:00+00:00",
            },
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "admit_memory_candidate", fake_admit_memory_candidate)

    response = main_module.admit_memory(
        main_module.AdmitMemoryRequest(
            user_id=user_id,
            memory_key="user.preference.coffee",
            value={"likes": "oat milk"},
            source_event_ids=[uuid4()],
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "decision": "ADD",
        "reason": "source_backed_add",
        "memory": {
            "id": "memory-123",
            "user_id": str(user_id),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-1"],
            "created_at": "2026-03-11T09:00:00+00:00",
            "updated_at": "2026-03-11T09:00:00+00:00",
            "deleted_at": None,
        },
        "revision": {
            "id": "revision-123",
            "user_id": str(user_id),
            "memory_id": "memory-123",
            "sequence_no": 1,
            "action": "ADD",
            "memory_key": "user.preference.coffee",
            "previous_value": None,
            "new_value": {"likes": "oat milk"},
            "source_event_ids": ["event-1"],
            "candidate": {
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "source_event_ids": ["event-1"],
                "delete_requested": False,
            },
            "created_at": "2026-03-11T09:00:00+00:00",
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["candidate"].memory_key == "user.preference.coffee"


def test_admit_memory_returns_bad_request_when_source_validation_fails(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "admit_memory_candidate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MemoryAdmissionValidationError("source_event_ids must all reference existing events owned by the user")
        ),
    )

    response = main_module.admit_memory(
        main_module.AdmitMemoryRequest(
            user_id=uuid4(),
            memory_key="user.preference.coffee",
            value={"likes": "black"},
            source_event_ids=[uuid4()],
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_event_ids must all reference existing events owned by the user",
    }


def test_extract_explicit_preferences_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    source_event_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_extract_and_admit_explicit_preferences(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "candidates": [
                {
                    "memory_key": "user.preference.black_coffee",
                    "value": {
                        "kind": "explicit_preference",
                        "preference": "like",
                        "text": "black coffee",
                    },
                    "source_event_ids": [str(source_event_id)],
                    "delete_requested": False,
                    "pattern": "i_like",
                    "subject_text": "black coffee",
                }
            ],
            "admissions": [
                {
                    "decision": "ADD",
                    "reason": "source_backed_add",
                    "memory": {
                        "id": "memory-123",
                        "user_id": str(user_id),
                        "memory_key": "user.preference.black_coffee",
                        "value": {
                            "kind": "explicit_preference",
                            "preference": "like",
                            "text": "black coffee",
                        },
                        "status": "active",
                        "source_event_ids": [str(source_event_id)],
                        "created_at": "2026-03-12T09:00:00+00:00",
                        "updated_at": "2026-03-12T09:00:00+00:00",
                        "deleted_at": None,
                    },
                    "revision": {
                        "id": "revision-123",
                        "user_id": str(user_id),
                        "memory_id": "memory-123",
                        "sequence_no": 1,
                        "action": "ADD",
                        "memory_key": "user.preference.black_coffee",
                        "previous_value": None,
                        "new_value": {
                            "kind": "explicit_preference",
                            "preference": "like",
                            "text": "black coffee",
                        },
                        "source_event_ids": [str(source_event_id)],
                        "candidate": {
                            "memory_key": "user.preference.black_coffee",
                            "value": {
                                "kind": "explicit_preference",
                                "preference": "like",
                                "text": "black coffee",
                            },
                            "source_event_ids": [str(source_event_id)],
                            "delete_requested": False,
                        },
                        "created_at": "2026-03-12T09:00:00+00:00",
                    },
                }
            ],
            "summary": {
                "source_event_id": str(source_event_id),
                "source_event_kind": "message.user",
                "candidate_count": 1,
                "admission_count": 1,
                "persisted_change_count": 1,
                "noop_count": 0,
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_preferences",
        fake_extract_and_admit_explicit_preferences,
    )

    response = main_module.extract_explicit_preferences(
        main_module.ExtractExplicitPreferencesRequest(
            user_id=user_id,
            source_event_id=source_event_id,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "candidates": [
            {
                "memory_key": "user.preference.black_coffee",
                "value": {
                    "kind": "explicit_preference",
                    "preference": "like",
                    "text": "black coffee",
                },
                "source_event_ids": [str(source_event_id)],
                "delete_requested": False,
                "pattern": "i_like",
                "subject_text": "black coffee",
            }
        ],
        "admissions": [
            {
                "decision": "ADD",
                "reason": "source_backed_add",
                "memory": {
                    "id": "memory-123",
                    "user_id": str(user_id),
                    "memory_key": "user.preference.black_coffee",
                    "value": {
                        "kind": "explicit_preference",
                        "preference": "like",
                        "text": "black coffee",
                    },
                    "status": "active",
                    "source_event_ids": [str(source_event_id)],
                    "created_at": "2026-03-12T09:00:00+00:00",
                    "updated_at": "2026-03-12T09:00:00+00:00",
                    "deleted_at": None,
                },
                "revision": {
                    "id": "revision-123",
                    "user_id": str(user_id),
                    "memory_id": "memory-123",
                    "sequence_no": 1,
                    "action": "ADD",
                    "memory_key": "user.preference.black_coffee",
                    "previous_value": None,
                    "new_value": {
                        "kind": "explicit_preference",
                        "preference": "like",
                        "text": "black coffee",
                    },
                    "source_event_ids": [str(source_event_id)],
                    "candidate": {
                        "memory_key": "user.preference.black_coffee",
                        "value": {
                            "kind": "explicit_preference",
                            "preference": "like",
                            "text": "black coffee",
                        },
                        "source_event_ids": [str(source_event_id)],
                        "delete_requested": False,
                    },
                    "created_at": "2026-03-12T09:00:00+00:00",
                },
            }
        ],
        "summary": {
            "source_event_id": str(source_event_id),
            "source_event_kind": "message.user",
            "candidate_count": 1,
            "admission_count": 1,
            "persisted_change_count": 1,
            "noop_count": 0,
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].source_event_id == source_event_id


def test_extract_explicit_preferences_returns_bad_request_when_source_event_is_invalid(
    monkeypatch,
) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "extract_and_admit_explicit_preferences",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            main_module.ExplicitPreferenceExtractionValidationError(
                "source_event_id must reference an existing message.user event owned by the user"
            )
        ),
    )

    response = main_module.extract_explicit_preferences(
        main_module.ExtractExplicitPreferencesRequest(
            user_id=uuid4(),
            source_event_id=uuid4(),
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_event_id must reference an existing message.user event owned by the user",
    }


def test_list_memories_returns_review_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_review_records(store, *, user_id, status, limit):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["status"] = status
        captured["limit"] = limit
        return {
            "items": [
                {
                    "id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "status": "active",
                    "source_event_ids": ["event-1"],
                    "created_at": "2026-03-11T09:00:00+00:00",
                    "updated_at": "2026-03-11T09:02:00+00:00",
                    "deleted_at": None,
                }
            ],
            "summary": {
                "status": "active",
                "limit": 10,
                "returned_count": 1,
                "total_count": 1,
                "has_more": False,
                "order": ["updated_at_desc", "created_at_desc", "id_desc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_memory_review_records", fake_list_memory_review_records)

    response = main_module.list_memories(user_id=user_id, status="active", limit=10)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "memory-123",
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-11T09:00:00+00:00",
                "updated_at": "2026-03-11T09:02:00+00:00",
                "deleted_at": None,
            }
        ],
        "summary": {
            "status": "active",
            "limit": 10,
            "returned_count": 1,
            "total_count": 1,
            "has_more": False,
            "order": ["updated_at_desc", "created_at_desc", "id_desc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["status"] == "active"
    assert captured["limit"] == 10


def test_get_memory_returns_not_found_when_memory_is_inaccessible(monkeypatch) -> None:
    memory_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_memory_review_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            main_module.MemoryReviewNotFoundError(f"memory {memory_id} was not found")
        ),
    )

    response = main_module.get_memory(memory_id=memory_id, user_id=uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"memory {memory_id} was not found",
    }


def test_list_memory_review_queue_returns_unlabeled_active_queue_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_review_queue_records(store, *, user_id, limit):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["limit"] = limit
        return {
            "items": [
                {
                    "id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "status": "active",
                    "source_event_ids": ["event-1"],
                    "created_at": "2026-03-12T09:00:00+00:00",
                    "updated_at": "2026-03-12T09:02:00+00:00",
                }
            ],
            "summary": {
                "memory_status": "active",
                "review_state": "unlabeled",
                "limit": 7,
                "returned_count": 1,
                "total_count": 1,
                "has_more": False,
                "order": ["updated_at_desc", "created_at_desc", "id_desc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_memory_review_queue_records", fake_list_memory_review_queue_records)

    response = main_module.list_memory_review_queue(user_id=user_id, limit=7)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "memory-123",
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-12T09:00:00+00:00",
                "updated_at": "2026-03-12T09:02:00+00:00",
            }
        ],
        "summary": {
            "memory_status": "active",
            "review_state": "unlabeled",
            "limit": 7,
            "returned_count": 1,
            "total_count": 1,
            "has_more": False,
            "order": ["updated_at_desc", "created_at_desc", "id_desc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["limit"] == 7


def test_get_memories_evaluation_summary_returns_aggregate_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_memory_evaluation_summary(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "summary": {
                "total_memory_count": 4,
                "active_memory_count": 3,
                "deleted_memory_count": 1,
                "labeled_memory_count": 2,
                "unlabeled_memory_count": 2,
                "total_label_row_count": 3,
                "label_row_counts_by_value": {
                    "correct": 1,
                    "incorrect": 0,
                    "outdated": 1,
                    "insufficient_evidence": 1,
                },
                "label_value_order": [
                    "correct",
                    "incorrect",
                    "outdated",
                    "insufficient_evidence",
                ],
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_memory_evaluation_summary", fake_get_memory_evaluation_summary)

    response = main_module.get_memories_evaluation_summary(user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "summary": {
            "total_memory_count": 4,
            "active_memory_count": 3,
            "deleted_memory_count": 1,
            "labeled_memory_count": 2,
            "unlabeled_memory_count": 2,
            "total_label_row_count": 3,
            "label_row_counts_by_value": {
                "correct": 1,
                "incorrect": 0,
                "outdated": 1,
                "insufficient_evidence": 1,
            },
            "label_value_order": [
                "correct",
                "incorrect",
                "outdated",
                "insufficient_evidence",
            ],
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id


def test_list_memory_revisions_returns_review_payload(monkeypatch) -> None:
    user_id = uuid4()
    memory_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_revision_review_records(store, *, user_id, memory_id, limit):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["memory_id"] = memory_id
        captured["limit"] = limit
        return {
            "items": [
                {
                    "id": "revision-123",
                    "memory_id": str(memory_id),
                    "sequence_no": 1,
                    "action": "ADD",
                    "memory_key": "user.preference.coffee",
                    "previous_value": None,
                    "new_value": {"likes": "black"},
                    "source_event_ids": ["event-1"],
                    "created_at": "2026-03-11T09:00:00+00:00",
                }
            ],
            "summary": {
                "memory_id": str(memory_id),
                "limit": 5,
                "returned_count": 1,
                "total_count": 1,
                "has_more": False,
                "order": ["sequence_no_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_revision_review_records",
        fake_list_memory_revision_review_records,
    )

    response = main_module.list_memory_revisions(memory_id=memory_id, user_id=user_id, limit=5)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "revision-123",
                "memory_id": str(memory_id),
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": "user.preference.coffee",
                "previous_value": None,
                "new_value": {"likes": "black"},
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-11T09:00:00+00:00",
            }
        ],
        "summary": {
            "memory_id": str(memory_id),
            "limit": 5,
            "returned_count": 1,
            "total_count": 1,
            "has_more": False,
            "order": ["sequence_no_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["memory_id"] == memory_id
    assert captured["limit"] == 5


def test_create_memory_review_label_returns_created_payload(monkeypatch) -> None:
    memory_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_memory_review_label_record(store, *, user_id, memory_id, label, note):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["memory_id"] = memory_id
        captured["label"] = label
        captured["note"] = note
        return {
            "label": {
                "id": "label-123",
                "memory_id": str(memory_id),
                "reviewer_user_id": str(user_id),
                "label": "correct",
                "note": "Backed by the latest source.",
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            "summary": {
                "memory_id": str(memory_id),
                "total_count": 1,
                "counts_by_label": {
                    "correct": 1,
                    "incorrect": 0,
                    "outdated": 0,
                    "insufficient_evidence": 0,
                },
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_memory_review_label_record",
        fake_create_memory_review_label_record,
    )

    response = main_module.create_memory_review_label(
        memory_id,
        main_module.CreateMemoryReviewLabelRequest(
            user_id=user_id,
            label="correct",
            note="Backed by the latest source.",
        ),
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "label": {
            "id": "label-123",
            "memory_id": str(memory_id),
            "reviewer_user_id": str(user_id),
            "label": "correct",
            "note": "Backed by the latest source.",
            "created_at": "2026-03-12T09:00:00+00:00",
        },
        "summary": {
            "memory_id": str(memory_id),
            "total_count": 1,
            "counts_by_label": {
                "correct": 1,
                "incorrect": 0,
                "outdated": 0,
                "insufficient_evidence": 0,
            },
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["memory_id"] == memory_id
    assert captured["label"] == "correct"
    assert captured["note"] == "Backed by the latest source."


def test_create_memory_review_label_returns_not_found_for_inaccessible_memory(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_memory_review_label_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MemoryReviewNotFoundError("memory missing")),
    )

    response = main_module.create_memory_review_label(
        uuid4(),
        main_module.CreateMemoryReviewLabelRequest(user_id=uuid4(), label="incorrect"),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "memory missing"}


def test_list_memory_review_labels_returns_deterministic_items_and_summary(monkeypatch) -> None:
    memory_id = uuid4()
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_memory_review_label_records(store, *, user_id, memory_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["memory_id"] = memory_id
        return {
            "items": [
                {
                    "id": "label-123",
                    "memory_id": str(memory_id),
                    "reviewer_user_id": str(user_id),
                    "label": "incorrect",
                    "note": "Conflicts with the latest event.",
                    "created_at": "2026-03-12T09:00:00+00:00",
                },
                {
                    "id": "label-124",
                    "memory_id": str(memory_id),
                    "reviewer_user_id": str(user_id),
                    "label": "outdated",
                    "note": None,
                    "created_at": "2026-03-12T09:01:00+00:00",
                },
            ],
            "summary": {
                "memory_id": str(memory_id),
                "total_count": 2,
                "counts_by_label": {
                    "correct": 0,
                    "incorrect": 1,
                    "outdated": 1,
                    "insufficient_evidence": 0,
                },
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_review_label_records",
        fake_list_memory_review_label_records,
    )

    response = main_module.list_memory_review_labels(memory_id=memory_id, user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "label-123",
                "memory_id": str(memory_id),
                "reviewer_user_id": str(user_id),
                "label": "incorrect",
                "note": "Conflicts with the latest event.",
                "created_at": "2026-03-12T09:00:00+00:00",
            },
            {
                "id": "label-124",
                "memory_id": str(memory_id),
                "reviewer_user_id": str(user_id),
                "label": "outdated",
                "note": None,
                "created_at": "2026-03-12T09:01:00+00:00",
            },
        ],
        "summary": {
            "memory_id": str(memory_id),
            "total_count": 2,
            "counts_by_label": {
                "correct": 0,
                "incorrect": 1,
                "outdated": 1,
                "insufficient_evidence": 0,
            },
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["memory_id"] == memory_id


def test_list_memory_review_labels_returns_not_found_for_inaccessible_memory(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_review_label_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MemoryReviewNotFoundError("memory hidden")),
    )

    response = main_module.list_memory_review_labels(uuid4(), uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "memory hidden"}


def test_create_embedding_config_returns_created_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_embedding_config_record(store, *, user_id, config):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["config"] = config
        return {
            "embedding_config": {
                "id": "config-123",
                "provider": "openai",
                "model": "text-embedding-3-large",
                "version": "2026-03-12",
                "dimensions": 3,
                "status": "active",
                "metadata": {"task": "memory_retrieval"},
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_embedding_config_record", fake_create_embedding_config_record)

    response = main_module.create_embedding_config(
        main_module.CreateEmbeddingConfigRequest(
            user_id=user_id,
            provider="openai",
            model="text-embedding-3-large",
            version="2026-03-12",
            dimensions=3,
            status="active",
            metadata={"task": "memory_retrieval"},
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "embedding_config": {
            "id": "config-123",
            "provider": "openai",
            "model": "text-embedding-3-large",
            "version": "2026-03-12",
            "dimensions": 3,
            "status": "active",
            "metadata": {"task": "memory_retrieval"},
            "created_at": "2026-03-12T10:00:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["config"].provider == "openai"


def test_create_embedding_config_returns_bad_request_for_validation_failure(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_embedding_config_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EmbeddingConfigValidationError(
                "embedding config already exists for provider/model/version under the user scope: "
                "openai/text-embedding-3-large/2026-03-12"
            )
        ),
    )

    response = main_module.create_embedding_config(
        main_module.CreateEmbeddingConfigRequest(
            user_id=uuid4(),
            provider="openai",
            model="text-embedding-3-large",
            version="2026-03-12",
            dimensions=3,
            status="active",
            metadata={"task": "memory_retrieval"},
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": (
            "embedding config already exists for provider/model/version under the user scope: "
            "openai/text-embedding-3-large/2026-03-12"
        )
    }


def test_upsert_memory_embedding_routes_success_and_validation_errors(monkeypatch) -> None:
    user_id = uuid4()
    memory_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_upsert_memory_embedding_record(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "embedding": {
                "id": "embedding-123",
                "memory_id": str(memory_id),
                "embedding_config_id": str(config_id),
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": "2026-03-12T10:00:00+00:00",
                "updated_at": "2026-03-12T10:00:00+00:00",
            },
            "write_mode": "created",
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "upsert_memory_embedding_record", fake_upsert_memory_embedding_record)

    response = main_module.upsert_memory_embedding(
        main_module.UpsertMemoryEmbeddingRequest(
            user_id=user_id,
            memory_id=memory_id,
            embedding_config_id=config_id,
            vector=[0.1, 0.2, 0.3],
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body)["write_mode"] == "created"
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].memory_id == memory_id

    monkeypatch.setattr(
        main_module,
        "upsert_memory_embedding_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MemoryEmbeddingValidationError(
                "embedding_config_id must reference an existing embedding config owned by the user"
            )
        ),
    )

    error_response = main_module.upsert_memory_embedding(
        main_module.UpsertMemoryEmbeddingRequest(
            user_id=user_id,
            memory_id=memory_id,
            embedding_config_id=config_id,
            vector=[0.1, 0.2, 0.3],
        )
    )

    assert error_response.status_code == 400
    assert json.loads(error_response.body) == {
        "detail": "embedding_config_id must reference an existing embedding config owned by the user"
    }


def test_retrieve_semantic_memories_routes_success_and_validation_errors(monkeypatch) -> None:
    user_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_retrieve_semantic_memory_records(store, *, user_id, request):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["request"] = request
        return {
            "items": [
                {
                    "memory_id": "memory-123",
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "source_event_ids": ["event-123"],
                    "created_at": "2026-03-12T10:00:00+00:00",
                    "updated_at": "2026-03-12T10:00:00+00:00",
                    "score": 0.99,
                }
            ],
            "summary": {
                "embedding_config_id": str(config_id),
                "limit": 5,
                "returned_count": 1,
                "similarity_metric": "cosine_similarity",
                "order": ["score_desc", "created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_semantic_memory_records",
        fake_retrieve_semantic_memory_records,
    )

    response = main_module.retrieve_semantic_memories(
        main_module.RetrieveSemanticMemoriesRequest(
            user_id=user_id,
            embedding_config_id=config_id,
            query_vector=[0.1, 0.2, 0.3],
            limit=5,
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body)["summary"] == {
        "embedding_config_id": str(config_id),
        "limit": 5,
        "returned_count": 1,
        "similarity_metric": "cosine_similarity",
        "order": ["score_desc", "created_at_asc", "id_asc"],
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["request"].embedding_config_id == config_id
    assert captured["request"].query_vector == (0.1, 0.2, 0.3)

    monkeypatch.setattr(
        main_module,
        "retrieve_semantic_memory_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            SemanticMemoryRetrievalValidationError(
                "embedding_config_id must reference an existing embedding config owned by the user"
            )
        ),
    )

    error_response = main_module.retrieve_semantic_memories(
        main_module.RetrieveSemanticMemoriesRequest(
            user_id=user_id,
            embedding_config_id=config_id,
            query_vector=[0.1, 0.2, 0.3],
            limit=5,
        )
    )

    assert error_response.status_code == 400
    assert json.loads(error_response.body) == {
        "detail": "embedding_config_id must reference an existing embedding config owned by the user"
    }


def test_memory_embedding_read_routes_return_payload_and_not_found(monkeypatch) -> None:
    user_id = uuid4()
    memory_id = uuid4()
    embedding_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_memory_embedding_records",
        lambda *_args, **_kwargs: {
            "items": [
                {
                    "id": str(embedding_id),
                    "memory_id": str(memory_id),
                    "embedding_config_id": "config-123",
                    "dimensions": 3,
                    "vector": [0.1, 0.2, 0.3],
                    "created_at": "2026-03-12T10:00:00+00:00",
                    "updated_at": "2026-03-12T10:00:00+00:00",
                }
            ],
            "summary": {
                "memory_id": str(memory_id),
                "total_count": 1,
                "order": ["created_at_asc", "id_asc"],
            },
        },
    )
    monkeypatch.setattr(
        main_module,
        "get_memory_embedding_record",
        lambda *_args, **_kwargs: {
            "embedding": {
                "id": str(embedding_id),
                "memory_id": str(memory_id),
                "embedding_config_id": "config-123",
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": "2026-03-12T10:00:00+00:00",
                "updated_at": "2026-03-12T10:00:00+00:00",
            }
        },
    )

    list_response = main_module.list_memory_embeddings(memory_id=memory_id, user_id=user_id)
    detail_response = main_module.get_memory_embedding(memory_embedding_id=embedding_id, user_id=user_id)

    assert list_response.status_code == 200
    assert json.loads(list_response.body)["summary"]["memory_id"] == str(memory_id)
    assert detail_response.status_code == 200
    assert json.loads(detail_response.body)["embedding"]["id"] == str(embedding_id)

    monkeypatch.setattr(
        main_module,
        "get_memory_embedding_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            MemoryEmbeddingNotFoundError(f"memory embedding {embedding_id} was not found")
        ),
    )

    not_found_response = main_module.get_memory_embedding(
        memory_embedding_id=embedding_id,
        user_id=user_id,
    )

    assert not_found_response.status_code == 404
    assert json.loads(not_found_response.body) == {
        "detail": f"memory embedding {embedding_id} was not found"
    }


def test_create_entity_returns_created_payload(monkeypatch) -> None:
    user_id = uuid4()
    first_memory_id = uuid4()
    second_memory_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_entity_record(store, *, user_id, entity):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["entity"] = entity
        return {
            "entity": {
                "id": "entity-123",
                "entity_type": "project",
                "name": "AliceBot",
                "source_memory_ids": [str(first_memory_id), str(second_memory_id)],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_entity_record", fake_create_entity_record)

    response = main_module.create_entity(
        main_module.CreateEntityRequest(
            user_id=user_id,
            entity_type="project",
            name="AliceBot",
            source_memory_ids=[first_memory_id, second_memory_id],
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "entity": {
            "id": "entity-123",
            "entity_type": "project",
            "name": "AliceBot",
            "source_memory_ids": [str(first_memory_id), str(second_memory_id)],
            "created_at": "2026-03-12T10:00:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["entity"].entity_type == "project"
    assert captured["entity"].name == "AliceBot"


def test_create_entity_returns_bad_request_when_source_memory_validation_fails(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_entity_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityValidationError("source_memory_ids must all reference existing memories owned by the user")
        ),
    )

    response = main_module.create_entity(
        main_module.CreateEntityRequest(
            user_id=uuid4(),
            entity_type="person",
            name="Samir",
            source_memory_ids=[uuid4()],
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "source_memory_ids must all reference existing memories owned by the user",
    }


def test_create_entity_edge_returns_created_payload(monkeypatch) -> None:
    user_id = uuid4()
    from_entity_id = uuid4()
    to_entity_id = uuid4()
    source_memory_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_create_entity_edge_record(store, *, user_id, edge):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["edge"] = edge
        return {
            "edge": {
                "id": "edge-123",
                "from_entity_id": str(from_entity_id),
                "to_entity_id": str(to_entity_id),
                "relationship_type": "works_on",
                "valid_from": "2026-03-12T10:00:00+00:00",
                "valid_to": None,
                "source_memory_ids": [str(source_memory_id)],
                "created_at": "2026-03-12T10:01:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_entity_edge_record", fake_create_entity_edge_record)

    response = main_module.create_entity_edge(
        main_module.CreateEntityEdgeRequest(
            user_id=user_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relationship_type="works_on",
            valid_from="2026-03-12T10:00:00+00:00",
            source_memory_ids=[source_memory_id],
        )
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "edge": {
            "id": "edge-123",
            "from_entity_id": str(from_entity_id),
            "to_entity_id": str(to_entity_id),
            "relationship_type": "works_on",
            "valid_from": "2026-03-12T10:00:00+00:00",
            "valid_to": None,
            "source_memory_ids": [str(source_memory_id)],
            "created_at": "2026-03-12T10:01:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["edge"].from_entity_id == from_entity_id
    assert captured["edge"].to_entity_id == to_entity_id


def test_create_entity_edge_returns_bad_request_for_validation_failure(monkeypatch) -> None:
    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_entity_edge_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityEdgeValidationError("valid_to must be greater than or equal to valid_from")
        ),
    )

    response = main_module.create_entity_edge(
        main_module.CreateEntityEdgeRequest(
            user_id=uuid4(),
            from_entity_id=uuid4(),
            to_entity_id=uuid4(),
            relationship_type="works_on",
            valid_from="2026-03-12T11:00:00+00:00",
            valid_to="2026-03-12T10:00:00+00:00",
            source_memory_ids=[uuid4()],
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "valid_to must be greater than or equal to valid_from",
    }


def test_list_entities_returns_deterministic_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_entity_records(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "items": [
                {
                    "id": "entity-123",
                    "entity_type": "project",
                    "name": "AliceBot",
                    "source_memory_ids": ["memory-1"],
                    "created_at": "2026-03-12T10:00:00+00:00",
                }
            ],
            "summary": {
                "total_count": 1,
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_entity_records", fake_list_entity_records)

    response = main_module.list_entities(user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "entity-123",
                "entity_type": "project",
                "name": "AliceBot",
                "source_memory_ids": ["memory-1"],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        ],
        "summary": {
            "total_count": 1,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id


def test_list_entity_edges_returns_deterministic_payload(monkeypatch) -> None:
    user_id = uuid4()
    entity_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_entity_edge_records(store, *, user_id, entity_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["entity_id"] = entity_id
        return {
            "items": [
                {
                    "id": "edge-123",
                    "from_entity_id": str(entity_id),
                    "to_entity_id": "entity-456",
                    "relationship_type": "works_on",
                    "valid_from": None,
                    "valid_to": None,
                    "source_memory_ids": ["memory-1"],
                    "created_at": "2026-03-12T10:00:00+00:00",
                }
            ],
            "summary": {
                "entity_id": str(entity_id),
                "total_count": 1,
                "order": ["created_at_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_entity_edge_records", fake_list_entity_edge_records)

    response = main_module.list_entity_edges(entity_id=entity_id, user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [
            {
                "id": "edge-123",
                "from_entity_id": str(entity_id),
                "to_entity_id": "entity-456",
                "relationship_type": "works_on",
                "valid_from": None,
                "valid_to": None,
                "source_memory_ids": ["memory-1"],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        ],
        "summary": {
            "entity_id": str(entity_id),
            "total_count": 1,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["entity_id"] == entity_id


def test_list_entity_edges_returns_not_found_for_inaccessible_entity(monkeypatch) -> None:
    entity_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_entity_edge_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityNotFoundError(f"entity {entity_id} was not found")
        ),
    )

    response = main_module.list_entity_edges(entity_id=entity_id, user_id=uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"entity {entity_id} was not found",
    }


def test_get_entity_returns_detail_payload(monkeypatch) -> None:
    user_id = uuid4()
    entity_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_get_entity_record(store, *, user_id, entity_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["entity_id"] = entity_id
        return {
            "entity": {
                "id": str(entity_id),
                "entity_type": "person",
                "name": "Samir",
                "source_memory_ids": ["memory-1"],
                "created_at": "2026-03-12T10:00:00+00:00",
            }
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_entity_record", fake_get_entity_record)

    response = main_module.get_entity(entity_id=entity_id, user_id=user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "entity": {
            "id": str(entity_id),
            "entity_type": "person",
            "name": "Samir",
            "source_memory_ids": ["memory-1"],
            "created_at": "2026-03-12T10:00:00+00:00",
        }
    }
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["user_id"] == user_id
    assert captured["entity_id"] == entity_id


def test_get_entity_returns_not_found_for_inaccessible_entity(monkeypatch) -> None:
    entity_id = uuid4()

    @contextmanager
    def fake_user_connection(_database_url: str, _current_user_id):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url="postgresql://app"))
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_entity_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            EntityNotFoundError(f"entity {entity_id} was not found")
        ),
    )

    response = main_module.get_entity(entity_id=entity_id, user_id=uuid4())

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"entity {entity_id} was not found",
    }
