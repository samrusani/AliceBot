from __future__ import annotations

import math
from uuid import UUID

import psycopg

from alicebot_api.contracts import (
    EMBEDDING_CONFIG_LIST_ORDER,
    MEMORY_EMBEDDING_LIST_ORDER,
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
)
from alicebot_api.store import ContinuityStore, EmbeddingConfigRow, MemoryEmbeddingRow


class EmbeddingConfigValidationError(ValueError):
    """Raised when an embedding-config request fails explicit validation."""


class MemoryEmbeddingValidationError(ValueError):
    """Raised when a memory-embedding request fails explicit validation."""


class MemoryEmbeddingNotFoundError(LookupError):
    """Raised when a requested memory embedding is not visible inside the current user scope."""


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


def _validate_vector(vector: tuple[float, ...]) -> list[float]:
    if not vector:
        raise MemoryEmbeddingValidationError("vector must include at least one numeric value")

    normalized: list[float] = []
    for value in vector:
        normalized_value = float(value)
        if not math.isfinite(normalized_value):
            raise MemoryEmbeddingValidationError("vector must contain only finite numeric values")
        normalized.append(normalized_value)

    return normalized


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

    vector = _validate_vector(request.vector)
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
