from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import SemanticMemoryRetrievalRequestInput
from alicebot_api.semantic_retrieval import (
    SemanticMemoryRetrievalValidationError,
    retrieve_semantic_memory_records,
)


class SemanticRetrievalStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.config_by_id: dict[UUID, dict[str, object]] = {}
        self.retrieval_rows: list[dict[str, object]] = []
        self.last_query: dict[str, object] | None = None

    def get_embedding_config_optional(self, embedding_config_id: UUID) -> dict[str, object] | None:
        return self.config_by_id.get(embedding_config_id)

    def retrieve_semantic_memory_matches(
        self,
        *,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[dict[str, object]]:
        self.last_query = {
            "embedding_config_id": embedding_config_id,
            "query_vector": query_vector,
            "limit": limit,
        }
        return list(self.retrieval_rows[:limit])


def seed_config(store: SemanticRetrievalStoreStub, *, dimensions: int = 3) -> UUID:
    config_id = uuid4()
    store.config_by_id[config_id] = {
        "id": config_id,
        "dimensions": dimensions,
    }
    return config_id


def active_row(
    store: SemanticRetrievalStoreStub,
    *,
    memory_key: str,
    score: float,
    minute_offset: int,
) -> dict[str, object]:
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "memory_key": memory_key,
        "value": {"memory_key": memory_key},
        "status": "active",
        "source_event_ids": [str(uuid4())],
        "created_at": store.base_time + timedelta(minutes=minute_offset),
        "updated_at": store.base_time + timedelta(minutes=minute_offset + 1),
        "deleted_at": None,
        "score": score,
    }


def test_retrieve_semantic_memory_records_returns_stable_shape_and_summary() -> None:
    store = SemanticRetrievalStoreStub()
    config_id = seed_config(store, dimensions=3)
    first_row = active_row(store, memory_key="user.preference.coffee", score=1.0, minute_offset=0)
    second_row = active_row(store, memory_key="user.preference.tea", score=0.75, minute_offset=1)
    store.retrieval_rows = [first_row, second_row]

    payload = retrieve_semantic_memory_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=SemanticMemoryRetrievalRequestInput(
            embedding_config_id=config_id,
            query_vector=(0.1, 0.2, 0.3),
            limit=2,
        ),
    )

    assert payload == {
        "items": [
            {
                "memory_id": str(first_row["id"]),
                "memory_key": "user.preference.coffee",
                "value": {"memory_key": "user.preference.coffee"},
                "source_event_ids": first_row["source_event_ids"],
                "created_at": first_row["created_at"].isoformat(),
                "updated_at": first_row["updated_at"].isoformat(),
                "score": 1.0,
            },
            {
                "memory_id": str(second_row["id"]),
                "memory_key": "user.preference.tea",
                "value": {"memory_key": "user.preference.tea"},
                "source_event_ids": second_row["source_event_ids"],
                "created_at": second_row["created_at"].isoformat(),
                "updated_at": second_row["updated_at"].isoformat(),
                "score": 0.75,
            },
        ],
        "summary": {
            "embedding_config_id": str(config_id),
            "limit": 2,
            "returned_count": 2,
            "similarity_metric": "cosine_similarity",
            "order": ["score_desc", "created_at_asc", "id_asc"],
        },
    }
    assert store.last_query == {
        "embedding_config_id": config_id,
        "query_vector": [0.1, 0.2, 0.3],
        "limit": 2,
    }


def test_retrieve_semantic_memory_records_rejects_missing_config() -> None:
    store = SemanticRetrievalStoreStub()

    with pytest.raises(
        SemanticMemoryRetrievalValidationError,
        match="embedding_config_id must reference an existing embedding config owned by the user",
    ):
        retrieve_semantic_memory_records(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=SemanticMemoryRetrievalRequestInput(
                embedding_config_id=uuid4(),
                query_vector=(0.1, 0.2, 0.3),
            ),
        )


def test_retrieve_semantic_memory_records_rejects_dimension_mismatch() -> None:
    store = SemanticRetrievalStoreStub()
    config_id = seed_config(store, dimensions=3)

    with pytest.raises(
        SemanticMemoryRetrievalValidationError,
        match="query_vector length must match embedding config dimensions \\(3\\): 2",
    ):
        retrieve_semantic_memory_records(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=SemanticMemoryRetrievalRequestInput(
                embedding_config_id=config_id,
                query_vector=(0.1, 0.2),
            ),
        )


def test_retrieve_semantic_memory_records_rejects_non_active_memory_rows() -> None:
    store = SemanticRetrievalStoreStub()
    config_id = seed_config(store, dimensions=3)
    invalid_row = active_row(store, memory_key="user.preference.music", score=0.5, minute_offset=0)
    invalid_row["status"] = "deleted"
    store.retrieval_rows = [invalid_row]

    with pytest.raises(
        SemanticMemoryRetrievalValidationError,
        match="semantic retrieval only supports active memories",
    ):
        retrieve_semantic_memory_records(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=SemanticMemoryRetrievalRequestInput(
                embedding_config_id=config_id,
                query_vector=(0.1, 0.2, 0.3),
            ),
        )
