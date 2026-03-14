from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.artifacts import TaskArtifactNotFoundError
from alicebot_api.contracts import TaskArtifactChunkEmbeddingUpsertInput
from alicebot_api.embedding import (
    TaskArtifactChunkEmbeddingNotFoundError,
    TaskArtifactChunkEmbeddingValidationError,
    get_task_artifact_chunk_embedding_record,
    list_task_artifact_chunk_embedding_records_for_artifact,
    list_task_artifact_chunk_embedding_records_for_chunk,
    upsert_task_artifact_chunk_embedding_record,
)


class TaskArtifactChunkEmbeddingStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
        self.artifacts: dict[UUID, dict[str, object]] = {}
        self.chunks: dict[UUID, dict[str, object]] = {}
        self.configs: dict[UUID, dict[str, object]] = {}
        self.embeddings: list[dict[str, object]] = []
        self.embedding_by_id: dict[UUID, dict[str, object]] = {}

    def create_artifact(self) -> UUID:
        artifact_id = uuid4()
        self.artifacts[artifact_id] = {
            "id": artifact_id,
            "task_id": uuid4(),
            "task_workspace_id": uuid4(),
            "status": "registered",
            "ingestion_status": "ingested",
            "relative_path": "docs/spec.txt",
            "media_type_hint": "text/plain",
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        return artifact_id

    def create_chunk(self, *, task_artifact_id: UUID, sequence_no: int) -> UUID:
        chunk_id = uuid4()
        self.chunks[chunk_id] = {
            "id": chunk_id,
            "task_artifact_id": task_artifact_id,
            "sequence_no": sequence_no,
            "char_start": (sequence_no - 1) * 10,
            "char_end_exclusive": sequence_no * 10,
            "text": f"chunk-{sequence_no}",
            "created_at": self.base_time + timedelta(minutes=sequence_no),
            "updated_at": self.base_time + timedelta(minutes=sequence_no),
        }
        return chunk_id

    def create_config(self, *, dimensions: int = 3) -> UUID:
        config_id = uuid4()
        self.configs[config_id] = {
            "id": config_id,
            "provider": "openai",
            "model": "text-embedding-3-large",
            "version": "2026-03-14",
            "dimensions": dimensions,
            "status": "active",
            "metadata": {"task": "artifact_chunk_retrieval"},
            "created_at": self.base_time,
        }
        return config_id

    def get_task_artifact_optional(self, task_artifact_id: UUID) -> dict[str, object] | None:
        return self.artifacts.get(task_artifact_id)

    def get_task_artifact_chunk_optional(
        self,
        task_artifact_chunk_id: UUID,
    ) -> dict[str, object] | None:
        return self.chunks.get(task_artifact_chunk_id)

    def get_embedding_config_optional(self, embedding_config_id: UUID) -> dict[str, object] | None:
        return self.configs.get(embedding_config_id)

    def get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
    ) -> dict[str, object] | None:
        return next(
            (
                embedding
                for embedding in self.embeddings
                if embedding["task_artifact_chunk_id"] == task_artifact_chunk_id
                and embedding["embedding_config_id"] == embedding_config_id
            ),
            None,
        )

    def create_task_artifact_chunk_embedding(
        self,
        *,
        task_artifact_chunk_id: UUID,
        embedding_config_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> dict[str, object]:
        chunk = self.chunks[task_artifact_chunk_id]
        embedding_id = uuid4()
        record = {
            "id": embedding_id,
            "user_id": uuid4(),
            "task_artifact_id": chunk["task_artifact_id"],
            "task_artifact_chunk_id": task_artifact_chunk_id,
            "task_artifact_chunk_sequence_no": chunk["sequence_no"],
            "embedding_config_id": embedding_config_id,
            "dimensions": dimensions,
            "vector": vector,
            "created_at": self.base_time + timedelta(seconds=len(self.embeddings)),
            "updated_at": self.base_time + timedelta(seconds=len(self.embeddings)),
        }
        self.embeddings.append(record)
        self.embedding_by_id[embedding_id] = record
        return record

    def update_task_artifact_chunk_embedding(
        self,
        *,
        task_artifact_chunk_embedding_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> dict[str, object]:
        record = self.embedding_by_id[task_artifact_chunk_embedding_id]
        updated = {
            **record,
            "dimensions": dimensions,
            "vector": vector,
            "updated_at": self.base_time + timedelta(minutes=10),
        }
        self.embedding_by_id[task_artifact_chunk_embedding_id] = updated
        for index, existing in enumerate(self.embeddings):
            if existing["id"] == task_artifact_chunk_embedding_id:
                self.embeddings[index] = updated
        return updated

    def get_task_artifact_chunk_embedding_optional(
        self,
        task_artifact_chunk_embedding_id: UUID,
    ) -> dict[str, object] | None:
        return self.embedding_by_id.get(task_artifact_chunk_embedding_id)

    def list_task_artifact_chunk_embeddings_for_artifact(
        self,
        task_artifact_id: UUID,
    ) -> list[dict[str, object]]:
        return sorted(
            (
                embedding
                for embedding in self.embeddings
                if embedding["task_artifact_id"] == task_artifact_id
            ),
            key=lambda embedding: (
                embedding["task_artifact_chunk_sequence_no"],
                embedding["created_at"],
                embedding["id"],
            ),
        )

    def list_task_artifact_chunk_embeddings_for_chunk(
        self,
        task_artifact_chunk_id: UUID,
    ) -> list[dict[str, object]]:
        return sorted(
            (
                embedding
                for embedding in self.embeddings
                if embedding["task_artifact_chunk_id"] == task_artifact_chunk_id
            ),
            key=lambda embedding: (
                embedding["task_artifact_chunk_sequence_no"],
                embedding["created_at"],
                embedding["id"],
            ),
        )


def test_task_artifact_chunk_embedding_writes_and_reads_are_deterministic() -> None:
    store = TaskArtifactChunkEmbeddingStoreStub()
    artifact_id = store.create_artifact()
    first_chunk_id = store.create_chunk(task_artifact_id=artifact_id, sequence_no=1)
    second_chunk_id = store.create_chunk(task_artifact_id=artifact_id, sequence_no=2)
    config_id = store.create_config()

    second_write = upsert_task_artifact_chunk_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TaskArtifactChunkEmbeddingUpsertInput(
            task_artifact_chunk_id=second_chunk_id,
            embedding_config_id=config_id,
            vector=(0.4, 0.5, 0.6),
        ),
    )
    first_write = upsert_task_artifact_chunk_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TaskArtifactChunkEmbeddingUpsertInput(
            task_artifact_chunk_id=first_chunk_id,
            embedding_config_id=config_id,
            vector=(0.1, 0.2, 0.3),
        ),
    )
    updated = upsert_task_artifact_chunk_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TaskArtifactChunkEmbeddingUpsertInput(
            task_artifact_chunk_id=second_chunk_id,
            embedding_config_id=config_id,
            vector=(0.9, 0.8, 0.7),
        ),
    )

    artifact_payload = list_task_artifact_chunk_embedding_records_for_artifact(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        task_artifact_id=artifact_id,
    )
    chunk_payload = list_task_artifact_chunk_embedding_records_for_chunk(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        task_artifact_chunk_id=second_chunk_id,
    )
    detail_payload = get_task_artifact_chunk_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        task_artifact_chunk_embedding_id=UUID(updated["embedding"]["id"]),
    )

    assert second_write["write_mode"] == "created"
    assert first_write["write_mode"] == "created"
    assert updated["write_mode"] == "updated"
    assert updated["embedding"]["vector"] == [0.9, 0.8, 0.7]
    assert [item["task_artifact_chunk_id"] for item in artifact_payload["items"]] == [
        str(first_chunk_id),
        str(second_chunk_id),
    ]
    assert artifact_payload["summary"] == {
        "total_count": 2,
        "order": ["task_artifact_chunk_sequence_no_asc", "created_at_asc", "id_asc"],
        "scope": {
            "kind": "artifact",
            "task_artifact_id": str(artifact_id),
        },
    }
    assert chunk_payload["summary"] == {
        "total_count": 1,
        "order": ["task_artifact_chunk_sequence_no_asc", "created_at_asc", "id_asc"],
        "scope": {
            "kind": "chunk",
            "task_artifact_id": str(artifact_id),
            "task_artifact_chunk_id": str(second_chunk_id),
        },
    }
    assert detail_payload["embedding"]["id"] == updated["embedding"]["id"]
    assert detail_payload["embedding"]["task_artifact_chunk_sequence_no"] == 2


def test_task_artifact_chunk_embedding_writes_reject_missing_refs_and_dimension_mismatch() -> None:
    store = TaskArtifactChunkEmbeddingStoreStub()
    artifact_id = store.create_artifact()
    chunk_id = store.create_chunk(task_artifact_id=artifact_id, sequence_no=1)
    config_id = store.create_config(dimensions=3)

    with pytest.raises(
        TaskArtifactChunkEmbeddingValidationError,
        match="task_artifact_chunk_id must reference an existing task artifact chunk owned by the user",
    ):
        upsert_task_artifact_chunk_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=TaskArtifactChunkEmbeddingUpsertInput(
                task_artifact_chunk_id=uuid4(),
                embedding_config_id=config_id,
                vector=(0.1, 0.2, 0.3),
            ),
        )

    with pytest.raises(
        TaskArtifactChunkEmbeddingValidationError,
        match="embedding_config_id must reference an existing embedding config owned by the user",
    ):
        upsert_task_artifact_chunk_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=TaskArtifactChunkEmbeddingUpsertInput(
                task_artifact_chunk_id=chunk_id,
                embedding_config_id=uuid4(),
                vector=(0.1, 0.2, 0.3),
            ),
        )

    with pytest.raises(
        TaskArtifactChunkEmbeddingValidationError,
        match=r"vector length must match embedding config dimensions \(3\): 2",
    ):
        upsert_task_artifact_chunk_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=TaskArtifactChunkEmbeddingUpsertInput(
                task_artifact_chunk_id=chunk_id,
                embedding_config_id=config_id,
                vector=(0.1, 0.2),
            ),
        )


def test_task_artifact_chunk_embedding_reads_raise_not_found_when_scope_is_missing() -> None:
    store = TaskArtifactChunkEmbeddingStoreStub()

    with pytest.raises(TaskArtifactNotFoundError, match="task artifact .* was not found"):
        list_task_artifact_chunk_embedding_records_for_artifact(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            task_artifact_id=uuid4(),
        )

    with pytest.raises(
        TaskArtifactChunkEmbeddingNotFoundError,
        match="task artifact chunk .* was not found",
    ):
        list_task_artifact_chunk_embedding_records_for_chunk(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            task_artifact_chunk_id=uuid4(),
        )

    with pytest.raises(
        TaskArtifactChunkEmbeddingNotFoundError,
        match="task artifact chunk embedding .* was not found",
    ):
        get_task_artifact_chunk_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            task_artifact_chunk_embedding_id=uuid4(),
        )
