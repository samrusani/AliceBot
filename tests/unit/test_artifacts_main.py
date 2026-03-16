from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.artifacts import (
    TaskArtifactAlreadyExistsError,
    TaskArtifactChunkRetrievalValidationError,
    TaskArtifactNotFoundError,
    TaskArtifactValidationError,
)
from alicebot_api.semantic_retrieval import SemanticArtifactChunkRetrievalValidationError
from alicebot_api.tasks import TaskNotFoundError
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


def test_list_task_artifacts_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_task_artifact_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = main_module.list_task_artifacts(user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
    }


def test_get_task_artifact_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_artifact_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_task_artifact_record", fake_get_task_artifact_record)

    response = main_module.get_task_artifact(task_artifact_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task artifact {task_artifact_id} was not found"}


def test_list_task_artifact_chunks_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    task_artifact_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_task_artifact_chunk_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {
                "total_count": 0,
                "total_characters": 0,
                "media_type": "text/plain",
                "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
                "order": ["sequence_no_asc", "id_asc"],
            },
        },
    )

    response = main_module.list_task_artifact_chunks(task_artifact_id, user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {
            "total_count": 0,
            "total_characters": 0,
            "media_type": "text/plain",
            "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
            "order": ["sequence_no_asc", "id_asc"],
        },
    }


def test_retrieve_task_artifact_chunks_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_task_scoped_artifact_chunk_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {
                "total_count": 0,
                "searched_artifact_count": 1,
                "query": "alpha",
                "query_terms": ["alpha"],
                "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
                "order": [
                    "matched_query_term_count_desc",
                    "first_match_char_start_asc",
                    "relative_path_asc",
                    "sequence_no_asc",
                    "id_asc",
                ],
                "scope": {"kind": "task", "task_id": str(task_id)},
            },
        },
    )

    response = main_module.retrieve_task_artifact_chunks(
        task_id,
        main_module.RetrieveArtifactChunksRequest(user_id=user_id, query="alpha"),
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {
            "total_count": 0,
            "searched_artifact_count": 1,
            "query": "alpha",
            "query_terms": ["alpha"],
            "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
            "order": [
                "matched_query_term_count_desc",
                "first_match_char_start_asc",
                "relative_path_asc",
                "sequence_no_asc",
                "id_asc",
            ],
            "scope": {"kind": "task", "task_id": str(task_id)},
        },
    }


def test_retrieve_task_artifact_chunks_endpoint_maps_task_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_retrieve_task_scoped_artifact_chunk_records(*_args, **_kwargs):
        raise TaskNotFoundError(f"task {task_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_task_scoped_artifact_chunk_records",
        fake_retrieve_task_scoped_artifact_chunk_records,
    )

    response = main_module.retrieve_task_artifact_chunks(
        task_id,
        main_module.RetrieveArtifactChunksRequest(user_id=user_id, query="alpha"),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task {task_id} was not found"}


def test_retrieve_task_artifact_chunks_endpoint_maps_validation_to_400(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_retrieve_task_scoped_artifact_chunk_records(*_args, **_kwargs):
        raise TaskArtifactChunkRetrievalValidationError(
            "artifact chunk retrieval query must include at least one word"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_task_scoped_artifact_chunk_records",
        fake_retrieve_task_scoped_artifact_chunk_records,
    )

    response = main_module.retrieve_task_artifact_chunks(
        task_id,
        main_module.RetrieveArtifactChunksRequest(user_id=user_id, query="alpha"),
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "artifact chunk retrieval query must include at least one word"
    }


def test_retrieve_semantic_task_artifact_chunks_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_task_scoped_semantic_artifact_chunk_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {
                "embedding_config_id": str(config_id),
                "query_vector_dimensions": 3,
                "limit": 5,
                "returned_count": 0,
                "searched_artifact_count": 1,
                "similarity_metric": "cosine_similarity",
                "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
                "scope": {"kind": "task", "task_id": str(task_id)},
            },
        },
    )

    response = main_module.retrieve_semantic_task_artifact_chunks(
        task_id,
        main_module.RetrieveSemanticArtifactChunksRequest(
            user_id=user_id,
            embedding_config_id=config_id,
            query_vector=[1.0, 0.0, 0.0],
            limit=5,
        ),
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {
            "embedding_config_id": str(config_id),
            "query_vector_dimensions": 3,
            "limit": 5,
            "returned_count": 0,
            "searched_artifact_count": 1,
            "similarity_metric": "cosine_similarity",
            "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
            "scope": {"kind": "task", "task_id": str(task_id)},
        },
    }


def test_retrieve_semantic_task_artifact_chunks_endpoint_maps_validation_to_400(monkeypatch) -> None:
    user_id = uuid4()
    task_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_retrieve_task_scoped_semantic_artifact_chunk_records(*_args, **_kwargs):
        raise SemanticArtifactChunkRetrievalValidationError(
            f"embedding_config_id must reference an existing embedding config owned by the user: {config_id}"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_task_scoped_semantic_artifact_chunk_records",
        fake_retrieve_task_scoped_semantic_artifact_chunk_records,
    )

    response = main_module.retrieve_semantic_task_artifact_chunks(
        task_id,
        main_module.RetrieveSemanticArtifactChunksRequest(
            user_id=user_id,
            embedding_config_id=config_id,
            query_vector=[1.0, 0.0, 0.0],
            limit=5,
        ),
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": (
            "embedding_config_id must reference an existing embedding config owned by the user: "
            f"{config_id}"
        )
    }


def test_retrieve_semantic_artifact_chunk_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_artifact_id = uuid4()
    config_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_retrieve_artifact_scoped_semantic_artifact_chunk_records(*_args, **_kwargs):
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_artifact_scoped_semantic_artifact_chunk_records",
        fake_retrieve_artifact_scoped_semantic_artifact_chunk_records,
    )

    response = main_module.retrieve_semantic_artifact_chunks_for_artifact(
        task_artifact_id,
        main_module.RetrieveSemanticArtifactChunksRequest(
            user_id=user_id,
            embedding_config_id=config_id,
            query_vector=[1.0, 0.0, 0.0],
            limit=5,
        ),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"task artifact {task_artifact_id} was not found"
    }


def test_retrieve_artifact_chunk_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_artifact_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_retrieve_artifact_scoped_artifact_chunk_records(*_args, **_kwargs):
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "retrieve_artifact_scoped_artifact_chunk_records",
        fake_retrieve_artifact_scoped_artifact_chunk_records,
    )

    response = main_module.retrieve_task_artifact_chunks_for_artifact(
        task_artifact_id,
        main_module.RetrieveArtifactChunksRequest(user_id=user_id, query="alpha"),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"task artifact {task_artifact_id} was not found"
    }


def test_register_task_artifact_endpoint_maps_workspace_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_register_task_artifact_record(*_args, **_kwargs):
        raise TaskWorkspaceNotFoundError(f"task workspace {task_workspace_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "register_task_artifact_record", fake_register_task_artifact_record)

    response = main_module.register_task_artifact(
        task_workspace_id,
        main_module.RegisterTaskArtifactRequest(
            user_id=user_id,
            local_path="/tmp/example.txt",
        ),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task workspace {task_workspace_id} was not found"}


def test_register_task_artifact_endpoint_maps_validation_to_400(monkeypatch) -> None:
    user_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_register_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactValidationError("artifact path /tmp/escape.txt escapes workspace root /tmp/workspace")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "register_task_artifact_record", fake_register_task_artifact_record)

    response = main_module.register_task_artifact(
        task_workspace_id,
        main_module.RegisterTaskArtifactRequest(
            user_id=user_id,
            local_path="/tmp/escape.txt",
        ),
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "artifact path /tmp/escape.txt escapes workspace root /tmp/workspace"
    }


def test_register_task_artifact_endpoint_maps_duplicate_to_409(monkeypatch) -> None:
    user_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_register_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactAlreadyExistsError(
            f"artifact docs/spec.txt is already registered for task workspace {task_workspace_id}"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "register_task_artifact_record", fake_register_task_artifact_record)

    response = main_module.register_task_artifact(
        task_workspace_id,
        main_module.RegisterTaskArtifactRequest(
            user_id=user_id,
            local_path="/tmp/docs/spec.txt",
        ),
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"artifact docs/spec.txt is already registered for task workspace {task_workspace_id}"
    }


def test_ingest_task_artifact_endpoint_maps_validation_to_400(monkeypatch) -> None:
    user_id = uuid4()
    task_artifact_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_ingest_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactValidationError(
            "artifact docs/spec.bin has unsupported media type application/octet-stream; "
            "supported types: text/plain, text/markdown, application/pdf, "
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "ingest_task_artifact_record", fake_ingest_task_artifact_record)

    response = main_module.ingest_task_artifact(
        task_artifact_id,
        main_module.IngestTaskArtifactRequest(user_id=user_id),
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": (
            "artifact docs/spec.bin has unsupported media type application/octet-stream; "
            "supported types: text/plain, text/markdown, application/pdf, "
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    }


def test_ingest_task_artifact_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    task_artifact_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_ingest_task_artifact_record(*_args, **_kwargs):
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "ingest_task_artifact_record", fake_ingest_task_artifact_record)

    response = main_module.ingest_task_artifact(
        task_artifact_id,
        main_module.IngestTaskArtifactRequest(user_id=user_id),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"task artifact {task_artifact_id} was not found"}
