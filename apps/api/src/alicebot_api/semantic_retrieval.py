from __future__ import annotations

import math
from uuid import UUID

from alicebot_api.contracts import (
    SEMANTIC_MEMORY_RETRIEVAL_ORDER,
    SemanticMemoryRetrievalRequestInput,
    SemanticMemoryRetrievalResponse,
    SemanticMemoryRetrievalResultItem,
    SemanticMemoryRetrievalSummary,
)
from alicebot_api.store import ContinuityStore, SemanticMemoryRetrievalRow


class SemanticMemoryRetrievalValidationError(ValueError):
    """Raised when semantic memory retrieval fails explicit validation."""


def _validate_query_vector(query_vector: tuple[float, ...]) -> list[float]:
    if not query_vector:
        raise SemanticMemoryRetrievalValidationError(
            "query_vector must include at least one numeric value"
        )

    normalized: list[float] = []
    for value in query_vector:
        normalized_value = float(value)
        if not math.isfinite(normalized_value):
            raise SemanticMemoryRetrievalValidationError(
                "query_vector must contain only finite numeric values"
            )
        normalized.append(normalized_value)

    return normalized


def validate_semantic_memory_retrieval_request(
    store: ContinuityStore,
    *,
    request: SemanticMemoryRetrievalRequestInput,
) -> tuple[dict[str, object], list[float]]:
    config = store.get_embedding_config_optional(request.embedding_config_id)
    if config is None:
        raise SemanticMemoryRetrievalValidationError(
            "embedding_config_id must reference an existing embedding config owned by the user: "
            f"{request.embedding_config_id}"
        )

    query_vector = _validate_query_vector(request.query_vector)
    if len(query_vector) != config["dimensions"]:
        raise SemanticMemoryRetrievalValidationError(
            "query_vector length must match embedding config dimensions "
            f"({config['dimensions']}): {len(query_vector)}"
        )

    return config, query_vector


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
