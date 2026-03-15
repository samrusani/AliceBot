from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import (
    ArtifactScopedSemanticArtifactChunkRetrievalInput,
    SemanticMemoryRetrievalRequestInput,
    TaskScopedSemanticArtifactChunkRetrievalInput,
)
from alicebot_api.semantic_retrieval import (
    SemanticArtifactChunkRetrievalValidationError,
    SemanticMemoryRetrievalValidationError,
    retrieve_artifact_scoped_semantic_artifact_chunk_records,
    retrieve_semantic_memory_records,
    retrieve_task_scoped_semantic_artifact_chunk_records,
)
from alicebot_api.tasks import TaskNotFoundError


class SemanticRetrievalStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.config_by_id: dict[UUID, dict[str, object]] = {}
        self.retrieval_rows: list[dict[str, object]] = []
        self.task_artifact_retrieval_rows: list[dict[str, object]] = []
        self.tasks: dict[UUID, dict[str, object]] = {}
        self.artifacts_by_id: dict[UUID, dict[str, object]] = {}
        self.artifacts_by_task_id: dict[UUID, list[dict[str, object]]] = {}
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

    def get_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return self.tasks.get(task_id)

    def get_task_artifact_optional(self, task_artifact_id: UUID) -> dict[str, object] | None:
        return self.artifacts_by_id.get(task_artifact_id)

    def list_task_artifacts_for_task(self, task_id: UUID) -> list[dict[str, object]]:
        return list(self.artifacts_by_task_id.get(task_id, []))

    def retrieve_task_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_id: UUID,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[dict[str, object]]:
        self.last_query = {
            "scope": "task",
            "task_id": task_id,
            "embedding_config_id": embedding_config_id,
            "query_vector": query_vector,
            "limit": limit,
        }
        return list(self.task_artifact_retrieval_rows[:limit])

    def retrieve_artifact_scoped_semantic_artifact_chunk_matches(
        self,
        *,
        task_artifact_id: UUID,
        embedding_config_id: UUID,
        query_vector: list[float],
        limit: int,
    ) -> list[dict[str, object]]:
        self.last_query = {
            "scope": "artifact",
            "task_artifact_id": task_artifact_id,
            "embedding_config_id": embedding_config_id,
            "query_vector": query_vector,
            "limit": limit,
        }
        return list(self.task_artifact_retrieval_rows[:limit])


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


def seed_task(store: SemanticRetrievalStoreStub) -> UUID:
    task_id = uuid4()
    store.tasks[task_id] = {"id": task_id}
    return task_id


def seed_artifact(
    store: SemanticRetrievalStoreStub,
    *,
    task_id: UUID,
    ingestion_status: str = "ingested",
    relative_path: str = "docs/spec.txt",
    media_type_hint: str | None = "text/plain",
) -> UUID:
    task_artifact_id = uuid4()
    artifact = {
        "id": task_artifact_id,
        "task_id": task_id,
        "ingestion_status": ingestion_status,
        "relative_path": relative_path,
        "media_type_hint": media_type_hint,
    }
    store.artifacts_by_id[task_artifact_id] = artifact
    store.artifacts_by_task_id.setdefault(task_id, []).append(artifact)
    return task_artifact_id


def semantic_artifact_row(
    store: SemanticRetrievalStoreStub,
    *,
    task_id: UUID,
    task_artifact_id: UUID,
    relative_path: str,
    score: float,
    sequence_no: int,
) -> dict[str, object]:
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "task_id": task_id,
        "task_artifact_id": task_artifact_id,
        "relative_path": relative_path,
        "media_type_hint": "text/plain",
        "sequence_no": sequence_no,
        "char_start": 0,
        "char_end_exclusive": 11,
        "text": f"{relative_path}-chunk",
        "created_at": store.base_time + timedelta(minutes=sequence_no),
        "updated_at": store.base_time + timedelta(minutes=sequence_no + 1),
        "embedding_config_id": uuid4(),
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


def test_retrieve_task_scoped_semantic_artifact_chunk_records_returns_stable_shape_and_summary() -> None:
    store = SemanticRetrievalStoreStub()
    config_id = seed_config(store, dimensions=3)
    task_id = seed_task(store)
    first_artifact_id = seed_artifact(
        store,
        task_id=task_id,
        relative_path="docs/a.txt",
    )
    second_artifact_id = seed_artifact(
        store,
        task_id=task_id,
        relative_path="notes/b.txt",
    )
    pending_artifact_id = seed_artifact(
        store,
        task_id=task_id,
        ingestion_status="pending",
        relative_path="notes/pending.txt",
    )
    first_row = semantic_artifact_row(
        store,
        task_id=task_id,
        task_artifact_id=first_artifact_id,
        relative_path="docs/a.txt",
        score=1.0,
        sequence_no=1,
    )
    second_row = semantic_artifact_row(
        store,
        task_id=task_id,
        task_artifact_id=second_artifact_id,
        relative_path="notes/b.txt",
        score=0.25,
        sequence_no=1,
    )
    store.task_artifact_retrieval_rows = [first_row, second_row]

    payload = retrieve_task_scoped_semantic_artifact_chunk_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TaskScopedSemanticArtifactChunkRetrievalInput(
            task_id=task_id,
            embedding_config_id=config_id,
            query_vector=(1.0, 0.0, 0.0),
            limit=2,
        ),
    )

    assert payload == {
        "items": [
            {
                "id": str(first_row["id"]),
                "task_id": str(task_id),
                "task_artifact_id": str(first_artifact_id),
                "relative_path": "docs/a.txt",
                "media_type": "text/plain",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 11,
                "text": "docs/a.txt-chunk",
                "score": 1.0,
            },
            {
                "id": str(second_row["id"]),
                "task_id": str(task_id),
                "task_artifact_id": str(second_artifact_id),
                "relative_path": "notes/b.txt",
                "media_type": "text/plain",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 11,
                "text": "notes/b.txt-chunk",
                "score": 0.25,
            },
        ],
        "summary": {
            "embedding_config_id": str(config_id),
            "query_vector_dimensions": 3,
            "limit": 2,
            "returned_count": 2,
            "searched_artifact_count": 2,
            "similarity_metric": "cosine_similarity",
            "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
            "scope": {"kind": "task", "task_id": str(task_id)},
        },
    }
    assert pending_artifact_id in store.artifacts_by_id
    assert store.last_query == {
        "scope": "task",
        "task_id": task_id,
        "embedding_config_id": config_id,
        "query_vector": [1.0, 0.0, 0.0],
        "limit": 2,
    }


def test_retrieve_task_scoped_semantic_artifact_chunk_records_rejects_missing_task_and_dimension_mismatch() -> None:
    store = SemanticRetrievalStoreStub()
    config_id = seed_config(store, dimensions=3)

    with pytest.raises(TaskNotFoundError, match="task .* was not found"):
        retrieve_task_scoped_semantic_artifact_chunk_records(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=TaskScopedSemanticArtifactChunkRetrievalInput(
                task_id=uuid4(),
                embedding_config_id=config_id,
                query_vector=(1.0, 0.0, 0.0),
            ),
        )

    task_id = seed_task(store)
    seed_artifact(store, task_id=task_id)
    with pytest.raises(
        SemanticArtifactChunkRetrievalValidationError,
        match="query_vector length must match embedding config dimensions \\(3\\): 2",
    ):
        retrieve_task_scoped_semantic_artifact_chunk_records(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=TaskScopedSemanticArtifactChunkRetrievalInput(
                task_id=task_id,
                embedding_config_id=config_id,
                query_vector=(1.0, 0.0),
            ),
        )


def test_retrieve_artifact_scoped_semantic_artifact_chunk_records_returns_empty_for_pending_artifact() -> None:
    store = SemanticRetrievalStoreStub()
    config_id = seed_config(store, dimensions=3)
    task_id = seed_task(store)
    artifact_id = seed_artifact(
        store,
        task_id=task_id,
        ingestion_status="pending",
        relative_path="notes/pending.txt",
        media_type_hint="text/markdown",
    )

    payload = retrieve_artifact_scoped_semantic_artifact_chunk_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=ArtifactScopedSemanticArtifactChunkRetrievalInput(
            task_artifact_id=artifact_id,
            embedding_config_id=config_id,
            query_vector=(0.0, 1.0, 0.0),
            limit=5,
        ),
    )

    assert payload == {
        "items": [],
        "summary": {
            "embedding_config_id": str(config_id),
            "query_vector_dimensions": 3,
            "limit": 5,
            "returned_count": 0,
            "searched_artifact_count": 0,
            "similarity_metric": "cosine_similarity",
            "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
            "scope": {
                "kind": "artifact",
                "task_id": str(task_id),
                "task_artifact_id": str(artifact_id),
            },
        },
    }
    assert store.last_query == {
        "scope": "artifact",
        "task_artifact_id": artifact_id,
        "embedding_config_id": config_id,
        "query_vector": [0.0, 1.0, 0.0],
        "limit": 5,
    }
