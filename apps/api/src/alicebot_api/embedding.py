from __future__ import annotations

import math
from uuid import UUID

import psycopg

from alicebot_api.artifacts import TaskArtifactNotFoundError
from alicebot_api.contracts import (
    EMBEDDING_CONFIG_LIST_ORDER,
    MEMORY_EMBEDDING_LIST_ORDER,
    TASK_ARTIFACT_CHUNK_EMBEDDING_LIST_ORDER,
    EmbeddingConfigCreateInput,
    EmbeddingConfigCreateResponse,
    EmbeddingConfigListResponse,
    EmbeddingConfigListSummary,
    EmbeddingConfigRecord,
    MemoryEmbeddingDetailResponse,
    MemoryEmbeddingListResponse,
    MemoryEmbeddingListSummary,
    MemoryEmbeddingRecord,
    MemoryEmbeddingUpsertInput,
    MemoryEmbeddingUpsertResponse,
    TaskArtifactChunkEmbeddingDetailResponse,
    TaskArtifactChunkEmbeddingListResponse,
    TaskArtifactChunkEmbeddingListScope,
    TaskArtifactChunkEmbeddingListScopeKind,
    TaskArtifactChunkEmbeddingListSummary,
    TaskArtifactChunkEmbeddingRecord,
    TaskArtifactChunkEmbeddingUpsertInput,
    TaskArtifactChunkEmbeddingWriteResponse,
)
from alicebot_api.store import (
    ContinuityStore,
    EmbeddingConfigRow,
    MemoryEmbeddingRow,
    TaskArtifactChunkEmbeddingRow,
)


class EmbeddingConfigValidationError(ValueError):
    """Raised when an embedding-config request fails explicit validation."""


class MemoryEmbeddingValidationError(ValueError):
    """Raised when a memory-embedding request fails explicit validation."""


class MemoryEmbeddingNotFoundError(LookupError):
    """Raised when a requested memory embedding is not visible inside the current user scope."""


class TaskArtifactChunkEmbeddingValidationError(ValueError):
    """Raised when an artifact-chunk embedding request fails explicit validation."""


class TaskArtifactChunkEmbeddingNotFoundError(LookupError):
    """Raised when an artifact-chunk embedding read target is not visible inside the current user scope."""


def _duplicate_embedding_config_message(
    *,
    provider: str,
    model: str,
    version: str,
) -> str:
    return (
        "embedding config already exists for provider/model/version under the user scope: "
        f"{provider}/{model}/{version}"
    )


def _serialize_embedding_config(config: EmbeddingConfigRow) -> EmbeddingConfigRecord:
    return {
        "id": str(config["id"]),
        "provider": config["provider"],
        "model": config["model"],
        "version": config["version"],
        "dimensions": config["dimensions"],
        "status": config["status"],
        "metadata": config["metadata"],
        "created_at": config["created_at"].isoformat(),
    }


def _serialize_memory_embedding(embedding: MemoryEmbeddingRow) -> MemoryEmbeddingRecord:
    return {
        "id": str(embedding["id"]),
        "memory_id": str(embedding["memory_id"]),
        "embedding_config_id": str(embedding["embedding_config_id"]),
        "dimensions": embedding["dimensions"],
        "vector": [float(value) for value in embedding["vector"]],
        "created_at": embedding["created_at"].isoformat(),
        "updated_at": embedding["updated_at"].isoformat(),
    }


def _serialize_task_artifact_chunk_embedding(
    embedding: TaskArtifactChunkEmbeddingRow,
) -> TaskArtifactChunkEmbeddingRecord:
    return {
        "id": str(embedding["id"]),
        "task_artifact_id": str(embedding["task_artifact_id"]),
        "task_artifact_chunk_id": str(embedding["task_artifact_chunk_id"]),
        "task_artifact_chunk_sequence_no": embedding["task_artifact_chunk_sequence_no"],
        "embedding_config_id": str(embedding["embedding_config_id"]),
        "dimensions": embedding["dimensions"],
        "vector": [float(value) for value in embedding["vector"]],
        "created_at": embedding["created_at"].isoformat(),
        "updated_at": embedding["updated_at"].isoformat(),
    }


def _validate_vector(
    vector: tuple[float, ...],
    *,
    error_type: type[ValueError],
) -> list[float]:
    if not vector:
        raise error_type("vector must include at least one numeric value")

    normalized: list[float] = []
    for value in vector:
        normalized_value = float(value)
        if not math.isfinite(normalized_value):
            raise error_type("vector must contain only finite numeric values")
        normalized.append(normalized_value)

    return normalized


def _build_task_artifact_chunk_embedding_scope(
    *,
    kind: TaskArtifactChunkEmbeddingListScopeKind,
    task_artifact_id: UUID,
    task_artifact_chunk_id: UUID | None = None,
) -> TaskArtifactChunkEmbeddingListScope:
    scope: TaskArtifactChunkEmbeddingListScope = {
        "kind": kind,
        "task_artifact_id": str(task_artifact_id),
    }
    if task_artifact_chunk_id is not None:
        scope["task_artifact_chunk_id"] = str(task_artifact_chunk_id)
    return scope


def _build_task_artifact_chunk_embedding_summary(
    *,
    items: list[TaskArtifactChunkEmbeddingRecord],
    scope: TaskArtifactChunkEmbeddingListScope,
) -> TaskArtifactChunkEmbeddingListSummary:
    return {
        "total_count": len(items),
        "order": list(TASK_ARTIFACT_CHUNK_EMBEDDING_LIST_ORDER),
        "scope": scope,
    }


def create_embedding_config_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    config: EmbeddingConfigCreateInput,
) -> EmbeddingConfigCreateResponse:
    del user_id

    existing = store.get_embedding_config_by_identity_optional(
        provider=config.provider,
        model=config.model,
        version=config.version,
    )
    if existing is not None:
        raise EmbeddingConfigValidationError(
            _duplicate_embedding_config_message(
                provider=config.provider,
                model=config.model,
                version=config.version,
            )
        )

    try:
        created = store.create_embedding_config(
            provider=config.provider,
            model=config.model,
            version=config.version,
            dimensions=config.dimensions,
            status=config.status,
            metadata=config.metadata,
        )
    except psycopg.errors.UniqueViolation as exc:
        raise EmbeddingConfigValidationError(
            _duplicate_embedding_config_message(
                provider=config.provider,
                model=config.model,
                version=config.version,
            )
        ) from exc
    return {"embedding_config": _serialize_embedding_config(created)}


def list_embedding_config_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> EmbeddingConfigListResponse:
    del user_id

    configs = store.list_embedding_configs()
    items = [_serialize_embedding_config(config) for config in configs]
    summary: EmbeddingConfigListSummary = {
        "total_count": len(items),
        "order": list(EMBEDDING_CONFIG_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def upsert_memory_embedding_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: MemoryEmbeddingUpsertInput,
) -> MemoryEmbeddingUpsertResponse:
    del user_id

    memory = store.get_memory_optional(request.memory_id)
    if memory is None:
        raise MemoryEmbeddingValidationError(
            f"memory_id must reference an existing memory owned by the user: {request.memory_id}"
        )

    config = store.get_embedding_config_optional(request.embedding_config_id)
    if config is None:
        raise MemoryEmbeddingValidationError(
            "embedding_config_id must reference an existing embedding config owned by the user: "
            f"{request.embedding_config_id}"
        )

    vector = _validate_vector(request.vector, error_type=MemoryEmbeddingValidationError)
    if len(vector) != config["dimensions"]:
        raise MemoryEmbeddingValidationError(
            "vector length must match embedding config dimensions "
            f"({config['dimensions']}): {len(vector)}"
        )

    existing = store.get_memory_embedding_by_memory_and_config_optional(
        memory_id=request.memory_id,
        embedding_config_id=request.embedding_config_id,
    )
    if existing is None:
        created = store.create_memory_embedding(
            memory_id=request.memory_id,
            embedding_config_id=request.embedding_config_id,
            dimensions=config["dimensions"],
            vector=vector,
        )
        return {
            "embedding": _serialize_memory_embedding(created),
            "write_mode": "created",
        }

    updated = store.update_memory_embedding(
        memory_embedding_id=existing["id"],
        dimensions=config["dimensions"],
        vector=vector,
    )
    return {
        "embedding": _serialize_memory_embedding(updated),
        "write_mode": "updated",
    }


def get_memory_embedding_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    memory_embedding_id: UUID,
) -> MemoryEmbeddingDetailResponse:
    del user_id

    embedding = store.get_memory_embedding_optional(memory_embedding_id)
    if embedding is None:
        raise MemoryEmbeddingNotFoundError(f"memory embedding {memory_embedding_id} was not found")

    return {"embedding": _serialize_memory_embedding(embedding)}


def list_memory_embedding_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    memory_id: UUID,
) -> MemoryEmbeddingListResponse:
    del user_id

    memory = store.get_memory_optional(memory_id)
    if memory is None:
        raise MemoryEmbeddingNotFoundError(f"memory {memory_id} was not found")

    embeddings = store.list_memory_embeddings_for_memory(memory_id)
    items = [_serialize_memory_embedding(embedding) for embedding in embeddings]
    summary: MemoryEmbeddingListSummary = {
        "memory_id": str(memory_id),
        "total_count": len(items),
        "order": list(MEMORY_EMBEDDING_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def upsert_task_artifact_chunk_embedding_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskArtifactChunkEmbeddingUpsertInput,
) -> TaskArtifactChunkEmbeddingWriteResponse:
    del user_id

    chunk = store.get_task_artifact_chunk_optional(request.task_artifact_chunk_id)
    if chunk is None:
        raise TaskArtifactChunkEmbeddingValidationError(
            "task_artifact_chunk_id must reference an existing task artifact chunk owned by the "
            f"user: {request.task_artifact_chunk_id}"
        )

    config = store.get_embedding_config_optional(request.embedding_config_id)
    if config is None:
        raise TaskArtifactChunkEmbeddingValidationError(
            "embedding_config_id must reference an existing embedding config owned by the user: "
            f"{request.embedding_config_id}"
        )

    vector = _validate_vector(request.vector, error_type=TaskArtifactChunkEmbeddingValidationError)
    if len(vector) != config["dimensions"]:
        raise TaskArtifactChunkEmbeddingValidationError(
            "vector length must match embedding config dimensions "
            f"({config['dimensions']}): {len(vector)}"
        )

    existing = store.get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        task_artifact_chunk_id=request.task_artifact_chunk_id,
        embedding_config_id=request.embedding_config_id,
    )
    if existing is None:
        created = store.create_task_artifact_chunk_embedding(
            task_artifact_chunk_id=request.task_artifact_chunk_id,
            embedding_config_id=request.embedding_config_id,
            dimensions=config["dimensions"],
            vector=vector,
        )
        return {
            "embedding": _serialize_task_artifact_chunk_embedding(created),
            "write_mode": "created",
        }

    updated = store.update_task_artifact_chunk_embedding(
        task_artifact_chunk_embedding_id=existing["id"],
        dimensions=config["dimensions"],
        vector=vector,
    )
    return {
        "embedding": _serialize_task_artifact_chunk_embedding(updated),
        "write_mode": "updated",
    }


def get_task_artifact_chunk_embedding_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_artifact_chunk_embedding_id: UUID,
) -> TaskArtifactChunkEmbeddingDetailResponse:
    del user_id

    embedding = store.get_task_artifact_chunk_embedding_optional(task_artifact_chunk_embedding_id)
    if embedding is None:
        raise TaskArtifactChunkEmbeddingNotFoundError(
            f"task artifact chunk embedding {task_artifact_chunk_embedding_id} was not found"
        )

    return {"embedding": _serialize_task_artifact_chunk_embedding(embedding)}


def list_task_artifact_chunk_embedding_records_for_artifact(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_artifact_id: UUID,
) -> TaskArtifactChunkEmbeddingListResponse:
    del user_id

    artifact = store.get_task_artifact_optional(task_artifact_id)
    if artifact is None:
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    items = [
        _serialize_task_artifact_chunk_embedding(embedding)
        for embedding in store.list_task_artifact_chunk_embeddings_for_artifact(task_artifact_id)
    ]
    scope = _build_task_artifact_chunk_embedding_scope(
        kind="artifact",
        task_artifact_id=task_artifact_id,
    )
    return {
        "items": items,
        "summary": _build_task_artifact_chunk_embedding_summary(items=items, scope=scope),
    }


def list_task_artifact_chunk_embedding_records_for_chunk(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_artifact_chunk_id: UUID,
) -> TaskArtifactChunkEmbeddingListResponse:
    del user_id

    chunk = store.get_task_artifact_chunk_optional(task_artifact_chunk_id)
    if chunk is None:
        raise TaskArtifactChunkEmbeddingNotFoundError(
            f"task artifact chunk {task_artifact_chunk_id} was not found"
        )

    items = [
        _serialize_task_artifact_chunk_embedding(embedding)
        for embedding in store.list_task_artifact_chunk_embeddings_for_chunk(task_artifact_chunk_id)
    ]
    scope = _build_task_artifact_chunk_embedding_scope(
        kind="chunk",
        task_artifact_id=chunk["task_artifact_id"],
        task_artifact_chunk_id=task_artifact_chunk_id,
    )
    return {
        "items": items,
        "summary": _build_task_artifact_chunk_embedding_summary(items=items, scope=scope),
    }
