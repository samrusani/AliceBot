from __future__ import annotations

import math
from pathlib import Path
from typing import cast
from uuid import UUID

from alicebot_api.artifacts import TaskArtifactNotFoundError
from alicebot_api.contracts import (
    SEMANTIC_MEMORY_RETRIEVAL_ORDER,
    TASK_ARTIFACT_CHUNK_SEMANTIC_RETRIEVAL_ORDER,
    ArtifactScopedSemanticArtifactChunkRetrievalInput,
    SemanticMemoryRetrievalRequestInput,
    SemanticMemoryRetrievalResponse,
    SemanticMemoryRetrievalResultItem,
    SemanticMemoryRetrievalSummary,
    TaskArtifactChunkRetrievalScope,
    TaskArtifactChunkRetrievalScopeKind,
    TaskArtifactChunkSemanticRetrievalItem,
    TaskArtifactChunkSemanticRetrievalResponse,
    TaskArtifactChunkSemanticRetrievalSummary,
    TaskScopedSemanticArtifactChunkRetrievalInput,
)
from alicebot_api.store import (
    ContinuityStore,
    SemanticMemoryRetrievalRow,
    TaskArtifactChunkSemanticRetrievalRow,
)
from alicebot_api.tasks import TaskNotFoundError

SUPPORTED_TEXT_ARTIFACT_EXTENSIONS = {
    ".txt": "text/plain",
    ".text": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".eml": "message/rfc822",
}


class SemanticMemoryRetrievalValidationError(ValueError):
    """Raised when semantic memory retrieval fails explicit validation."""


class SemanticArtifactChunkRetrievalValidationError(ValueError):
    """Raised when semantic artifact chunk retrieval fails explicit validation."""


def calculate_precision_at_k(
    *,
    returned_ids: list[str],
    relevant_ids: set[str],
    top_k: int,
) -> float:
    if top_k < 1:
        raise SemanticMemoryRetrievalValidationError("top_k must be greater than or equal to 1")

    top_results = returned_ids[:top_k]
    if not top_results:
        return 0.0

    hit_count = sum(1 for result_id in top_results if result_id in relevant_ids)
    return hit_count / float(len(top_results))


def calculate_mean_precision(precision_values: list[float]) -> float:
    if not precision_values:
        return 0.0
    return sum(precision_values) / float(len(precision_values))


def _validate_query_vector(
    query_vector: tuple[float, ...],
    *,
    error_type: type[ValueError],
) -> list[float]:
    if not query_vector:
        raise error_type(
            "query_vector must include at least one numeric value"
        )

    normalized: list[float] = []
    for value in query_vector:
        normalized_value = float(value)
        if not math.isfinite(normalized_value):
            raise error_type(
                "query_vector must contain only finite numeric values"
            )
        normalized.append(normalized_value)

    return normalized


def _validate_embedding_config_and_query_vector(
    store: ContinuityStore,
    *,
    embedding_config_id: UUID,
    query_vector: tuple[float, ...],
    error_type: type[ValueError],
) -> tuple[dict[str, object], list[float]]:
    config = store.get_embedding_config_optional(embedding_config_id)
    if config is None:
        raise error_type(
            "embedding_config_id must reference an existing embedding config owned by the user: "
            f"{embedding_config_id}"
        )

    normalized_query_vector = _validate_query_vector(query_vector, error_type=error_type)
    if len(normalized_query_vector) != config["dimensions"]:
        raise error_type(
            "query_vector length must match embedding config dimensions "
            f"({config['dimensions']}): {len(normalized_query_vector)}"
        )

    return config, normalized_query_vector


def validate_semantic_memory_retrieval_request(
    store: ContinuityStore,
    *,
    request: SemanticMemoryRetrievalRequestInput,
) -> tuple[dict[str, object], list[float]]:
    return _validate_embedding_config_and_query_vector(
        store,
        embedding_config_id=request.embedding_config_id,
        query_vector=request.query_vector,
        error_type=SemanticMemoryRetrievalValidationError,
    )


def serialize_semantic_memory_result_item(
    row: SemanticMemoryRetrievalRow,
) -> SemanticMemoryRetrievalResultItem:
    if row["status"] != "active":
        raise SemanticMemoryRetrievalValidationError(
            f"semantic retrieval only supports active memories: {row['id']}"
        )

    return {
        "memory_id": str(row["id"]),
        "memory_key": row["memory_key"],
        "value": row["value"],
        "source_event_ids": row["source_event_ids"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "score": float(row["score"]),
    }


def _infer_media_type(*, relative_path: str, media_type_hint: str | None) -> str:
    if media_type_hint is not None:
        return media_type_hint
    return SUPPORTED_TEXT_ARTIFACT_EXTENSIONS.get(Path(relative_path).suffix.lower(), "unknown")


def _build_task_artifact_chunk_retrieval_scope(
    *,
    kind: str,
    task_id: UUID,
    task_artifact_id: UUID | None = None,
) -> TaskArtifactChunkRetrievalScope:
    scope: TaskArtifactChunkRetrievalScope = {
        "kind": cast(TaskArtifactChunkRetrievalScopeKind, kind),
        "task_id": str(task_id),
    }
    if task_artifact_id is not None:
        scope["task_artifact_id"] = str(task_artifact_id)
    return scope


def serialize_semantic_artifact_chunk_result_item(
    row: TaskArtifactChunkSemanticRetrievalRow,
) -> TaskArtifactChunkSemanticRetrievalItem:
    return {
        "id": str(row["id"]),
        "task_id": str(row["task_id"]),
        "task_artifact_id": str(row["task_artifact_id"]),
        "relative_path": row["relative_path"],
        "media_type": _infer_media_type(
            relative_path=row["relative_path"],
            media_type_hint=row["media_type_hint"],
        ),
        "sequence_no": row["sequence_no"],
        "char_start": row["char_start"],
        "char_end_exclusive": row["char_end_exclusive"],
        "text": row["text"],
        "score": float(row["score"]),
    }


def validate_semantic_artifact_chunk_retrieval_request(
    store: ContinuityStore,
    *,
    embedding_config_id: UUID,
    query_vector: tuple[float, ...],
) -> tuple[dict[str, object], list[float]]:
    return _validate_embedding_config_and_query_vector(
        store,
        embedding_config_id=embedding_config_id,
        query_vector=query_vector,
        error_type=SemanticArtifactChunkRetrievalValidationError,
    )


def _count_ingested_artifacts(artifact_rows: list[dict[str, object]]) -> int:
    return sum(1 for artifact_row in artifact_rows if artifact_row["ingestion_status"] == "ingested")


def _build_semantic_artifact_chunk_summary(
    *,
    embedding_config_id: UUID,
    query_vector_dimensions: int,
    limit: int,
    searched_artifact_count: int,
    scope: TaskArtifactChunkRetrievalScope,
    items: list[TaskArtifactChunkSemanticRetrievalItem],
) -> TaskArtifactChunkSemanticRetrievalSummary:
    return {
        "embedding_config_id": str(embedding_config_id),
        "query_vector_dimensions": query_vector_dimensions,
        "limit": limit,
        "returned_count": len(items),
        "searched_artifact_count": searched_artifact_count,
        "similarity_metric": "cosine_similarity",
        "order": list(TASK_ARTIFACT_CHUNK_SEMANTIC_RETRIEVAL_ORDER),
        "scope": scope,
    }


def retrieve_task_scoped_semantic_artifact_chunk_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskScopedSemanticArtifactChunkRetrievalInput,
) -> TaskArtifactChunkSemanticRetrievalResponse:
    del user_id

    task = store.get_task_optional(request.task_id)
    if task is None:
        raise TaskNotFoundError(f"task {request.task_id} was not found")

    _config, query_vector = validate_semantic_artifact_chunk_retrieval_request(
        store,
        embedding_config_id=request.embedding_config_id,
        query_vector=request.query_vector,
    )
    items = [
        serialize_semantic_artifact_chunk_result_item(row)
        for row in store.retrieve_task_scoped_semantic_artifact_chunk_matches(
            task_id=request.task_id,
            embedding_config_id=request.embedding_config_id,
            query_vector=query_vector,
            limit=request.limit,
        )
    ]
    artifact_rows = store.list_task_artifacts_for_task(request.task_id)
    scope = _build_task_artifact_chunk_retrieval_scope(
        kind="task",
        task_id=request.task_id,
    )
    return {
        "items": items,
        "summary": _build_semantic_artifact_chunk_summary(
            embedding_config_id=request.embedding_config_id,
            query_vector_dimensions=len(query_vector),
            limit=request.limit,
            searched_artifact_count=_count_ingested_artifacts(artifact_rows),
            scope=scope,
            items=items,
        ),
    }


def retrieve_artifact_scoped_semantic_artifact_chunk_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ArtifactScopedSemanticArtifactChunkRetrievalInput,
) -> TaskArtifactChunkSemanticRetrievalResponse:
    del user_id

    artifact_row = store.get_task_artifact_optional(request.task_artifact_id)
    if artifact_row is None:
        raise TaskArtifactNotFoundError(f"task artifact {request.task_artifact_id} was not found")

    _config, query_vector = validate_semantic_artifact_chunk_retrieval_request(
        store,
        embedding_config_id=request.embedding_config_id,
        query_vector=request.query_vector,
    )
    items = [
        serialize_semantic_artifact_chunk_result_item(row)
        for row in store.retrieve_artifact_scoped_semantic_artifact_chunk_matches(
            task_artifact_id=request.task_artifact_id,
            embedding_config_id=request.embedding_config_id,
            query_vector=query_vector,
            limit=request.limit,
        )
    ]
    scope = _build_task_artifact_chunk_retrieval_scope(
        kind="artifact",
        task_id=artifact_row["task_id"],
        task_artifact_id=artifact_row["id"],
    )
    searched_artifact_count = 1 if artifact_row["ingestion_status"] == "ingested" else 0
    return {
        "items": items,
        "summary": _build_semantic_artifact_chunk_summary(
            embedding_config_id=request.embedding_config_id,
            query_vector_dimensions=len(query_vector),
            limit=request.limit,
            searched_artifact_count=searched_artifact_count,
            scope=scope,
            items=items,
        ),
    }


def retrieve_semantic_memory_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: SemanticMemoryRetrievalRequestInput,
) -> SemanticMemoryRetrievalResponse:
    del user_id

    _config, query_vector = validate_semantic_memory_retrieval_request(store, request=request)

    items = [
        serialize_semantic_memory_result_item(row)
        for row in store.retrieve_semantic_memory_matches(
            embedding_config_id=request.embedding_config_id,
            query_vector=query_vector,
            limit=request.limit,
        )
    ]
    summary: SemanticMemoryRetrievalSummary = {
        "embedding_config_id": str(request.embedding_config_id),
        "limit": request.limit,
        "returned_count": len(items),
        "similarity_metric": "cosine_similarity",
        "order": list(SEMANTIC_MEMORY_RETRIEVAL_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }
