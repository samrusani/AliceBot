from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import psycopg
import pytest

from alicebot_api.contracts import EmbeddingConfigCreateInput, MemoryEmbeddingUpsertInput
from alicebot_api.embedding import (
    EmbeddingConfigValidationError,
    MemoryEmbeddingNotFoundError,
    MemoryEmbeddingValidationError,
    create_embedding_config_record,
    get_memory_embedding_record,
    list_embedding_config_records,
    list_memory_embedding_records,
    upsert_memory_embedding_record,
)


class EmbeddingStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.memories: dict[UUID, dict[str, object]] = {}
        self.configs: list[dict[str, object]] = []
        self.config_by_id: dict[UUID, dict[str, object]] = {}
        self.embeddings: list[dict[str, object]] = []
        self.embedding_by_id: dict[UUID, dict[str, object]] = {}

    def create_embedding_config(
        self,
        *,
        provider: str,
        model: str,
        version: str,
        dimensions: int,
        status: str,
        metadata: dict[str, object],
    ) -> dict[str, object]:
        config_id = uuid4()
        record = {
            "id": config_id,
            "user_id": uuid4(),
            "provider": provider,
            "model": model,
            "version": version,
            "dimensions": dimensions,
            "status": status,
            "metadata": metadata,
            "created_at": self.base_time + timedelta(minutes=len(self.configs)),
        }
        self.configs.append(record)
        self.config_by_id[config_id] = record
        return record

    def list_embedding_configs(self) -> list[dict[str, object]]:
        return list(self.configs)

    def get_embedding_config_optional(self, embedding_config_id: UUID) -> dict[str, object] | None:
        return self.config_by_id.get(embedding_config_id)

    def get_embedding_config_by_identity_optional(
        self,
        *,
        provider: str,
        model: str,
        version: str,
    ) -> dict[str, object] | None:
        for config in self.configs:
            if (
                config["provider"] == provider
                and config["model"] == model
                and config["version"] == version
            ):
                return config
        return None

    def get_memory_optional(self, memory_id: UUID) -> dict[str, object] | None:
        return self.memories.get(memory_id)

    def get_memory_embedding_by_memory_and_config_optional(
        self,
        *,
        memory_id: UUID,
        embedding_config_id: UUID,
    ) -> dict[str, object] | None:
        for embedding in self.embeddings:
            if (
                embedding["memory_id"] == memory_id
                and embedding["embedding_config_id"] == embedding_config_id
            ):
                return embedding
        return None

    def create_memory_embedding(
        self,
        *,
        memory_id: UUID,
        embedding_config_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> dict[str, object]:
        embedding_id = uuid4()
        record = {
            "id": embedding_id,
            "user_id": uuid4(),
            "memory_id": memory_id,
            "embedding_config_id": embedding_config_id,
            "dimensions": dimensions,
            "vector": vector,
            "created_at": self.base_time + timedelta(minutes=len(self.embeddings)),
            "updated_at": self.base_time + timedelta(minutes=len(self.embeddings)),
        }
        self.embeddings.append(record)
        self.embedding_by_id[embedding_id] = record
        return record

    def update_memory_embedding(
        self,
        *,
        memory_embedding_id: UUID,
        dimensions: int,
        vector: list[float],
    ) -> dict[str, object]:
        record = self.embedding_by_id[memory_embedding_id]
        updated = {
            **record,
            "dimensions": dimensions,
            "vector": vector,
            "updated_at": self.base_time + timedelta(minutes=10),
        }
        self.embedding_by_id[memory_embedding_id] = updated
        for index, existing in enumerate(self.embeddings):
            if existing["id"] == memory_embedding_id:
                self.embeddings[index] = updated
        return updated

    def get_memory_embedding_optional(self, memory_embedding_id: UUID) -> dict[str, object] | None:
        return self.embedding_by_id.get(memory_embedding_id)

    def list_memory_embeddings_for_memory(self, memory_id: UUID) -> list[dict[str, object]]:
        return [embedding for embedding in self.embeddings if embedding["memory_id"] == memory_id]


def seed_memory(store: EmbeddingStoreStub) -> UUID:
    memory_id = uuid4()
    store.memories[memory_id] = {
        "id": memory_id,
        "memory_key": "user.preference.coffee",
    }
    return memory_id


def seed_config(store: EmbeddingStoreStub, *, dimensions: int = 3) -> UUID:
    created = store.create_embedding_config(
        provider="openai",
        model="text-embedding-3-large",
        version="2026-03-12",
        dimensions=dimensions,
        status="active",
        metadata={"task": "memory_retrieval"},
    )
    return created["id"]  # type: ignore[return-value]


def test_create_and_list_embedding_configs_return_deterministic_shape() -> None:
    store = EmbeddingStoreStub()
    first = create_embedding_config_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        config=EmbeddingConfigCreateInput(
            provider="openai",
            model="text-embedding-3-small",
            version="2026-03-11",
            dimensions=1536,
            status="active",
            metadata={"task": "memory_retrieval"},
        ),
    )
    second = create_embedding_config_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        config=EmbeddingConfigCreateInput(
            provider="openai",
            model="text-embedding-3-large",
            version="2026-03-12",
            dimensions=3072,
            status="deprecated",
            metadata={"task": "memory_retrieval"},
        ),
    )

    payload = list_embedding_config_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
    )

    assert first["embedding_config"]["provider"] == "openai"
    assert second["embedding_config"]["status"] == "deprecated"
    assert payload == {
        "items": [
            first["embedding_config"],
            second["embedding_config"],
        ],
        "summary": {
            "total_count": 2,
            "order": ["created_at_asc", "id_asc"],
        },
    }


def test_create_embedding_config_rejects_duplicate_provider_model_version() -> None:
    store = EmbeddingStoreStub()
    create_embedding_config_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        config=EmbeddingConfigCreateInput(
            provider="openai",
            model="text-embedding-3-large",
            version="2026-03-12",
            dimensions=3072,
            status="active",
            metadata={"task": "memory_retrieval"},
        ),
    )

    with pytest.raises(
        EmbeddingConfigValidationError,
        match="embedding config already exists for provider/model/version under the user scope",
    ):
        create_embedding_config_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            config=EmbeddingConfigCreateInput(
                provider="openai",
                model="text-embedding-3-large",
                version="2026-03-12",
                dimensions=3072,
                status="active",
                metadata={"task": "memory_retrieval"},
            ),
        )


def test_create_embedding_config_translates_database_unique_violation_into_validation_error() -> None:
    class DuplicateConfigStoreStub(EmbeddingStoreStub):
        def get_embedding_config_by_identity_optional(
            self,
            *,
            provider: str,
            model: str,
            version: str,
        ) -> dict[str, object] | None:
            return None

        def create_embedding_config(
            self,
            *,
            provider: str,
            model: str,
            version: str,
            dimensions: int,
            status: str,
            metadata: dict[str, object],
        ) -> dict[str, object]:
            raise psycopg.errors.UniqueViolation("duplicate key value violates unique constraint")

    with pytest.raises(
        EmbeddingConfigValidationError,
        match="embedding config already exists for provider/model/version under the user scope",
    ):
        create_embedding_config_record(
            DuplicateConfigStoreStub(),  # type: ignore[arg-type]
            user_id=uuid4(),
            config=EmbeddingConfigCreateInput(
                provider="openai",
                model="text-embedding-3-large",
                version="2026-03-12",
                dimensions=3072,
                status="active",
                metadata={"task": "memory_retrieval"},
            ),
        )


def test_upsert_memory_embedding_creates_then_updates_existing_record() -> None:
    store = EmbeddingStoreStub()
    memory_id = seed_memory(store)
    config_id = seed_config(store, dimensions=3)

    created = upsert_memory_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=MemoryEmbeddingUpsertInput(
            memory_id=memory_id,
            embedding_config_id=config_id,
            vector=(0.1, 0.2, 0.3),
        ),
    )
    updated = upsert_memory_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=MemoryEmbeddingUpsertInput(
            memory_id=memory_id,
            embedding_config_id=config_id,
            vector=(0.3, 0.2, 0.1),
        ),
    )

    assert created["write_mode"] == "created"
    assert created["embedding"]["vector"] == [0.1, 0.2, 0.3]
    assert updated["write_mode"] == "updated"
    assert updated["embedding"]["id"] == created["embedding"]["id"]
    assert updated["embedding"]["vector"] == [0.3, 0.2, 0.1]


def test_upsert_memory_embedding_rejects_missing_memory() -> None:
    store = EmbeddingStoreStub()
    config_id = seed_config(store)

    with pytest.raises(
        MemoryEmbeddingValidationError,
        match="memory_id must reference an existing memory owned by the user",
    ):
        upsert_memory_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=MemoryEmbeddingUpsertInput(
                memory_id=uuid4(),
                embedding_config_id=config_id,
                vector=(0.1, 0.2, 0.3),
            ),
        )


def test_upsert_memory_embedding_rejects_missing_embedding_config() -> None:
    store = EmbeddingStoreStub()
    memory_id = seed_memory(store)

    with pytest.raises(
        MemoryEmbeddingValidationError,
        match="embedding_config_id must reference an existing embedding config owned by the user",
    ):
        upsert_memory_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=MemoryEmbeddingUpsertInput(
                memory_id=memory_id,
                embedding_config_id=uuid4(),
                vector=(0.1, 0.2, 0.3),
            ),
        )


def test_upsert_memory_embedding_rejects_dimension_mismatch_and_non_finite_values() -> None:
    store = EmbeddingStoreStub()
    memory_id = seed_memory(store)
    config_id = seed_config(store, dimensions=2)

    with pytest.raises(
        MemoryEmbeddingValidationError,
        match="vector length must match embedding config dimensions",
    ):
        upsert_memory_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=MemoryEmbeddingUpsertInput(
                memory_id=memory_id,
                embedding_config_id=config_id,
                vector=(0.1, 0.2, 0.3),
            ),
        )

    with pytest.raises(
        MemoryEmbeddingValidationError,
        match="vector must contain only finite numeric values",
    ):
        upsert_memory_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=MemoryEmbeddingUpsertInput(
                memory_id=memory_id,
                embedding_config_id=config_id,
                vector=(0.1, float("inf")),
            ),
        )


def test_memory_embedding_reads_return_deterministic_shape_and_not_found() -> None:
    store = EmbeddingStoreStub()
    memory_id = seed_memory(store)
    config_id = seed_config(store, dimensions=3)
    created = upsert_memory_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=MemoryEmbeddingUpsertInput(
            memory_id=memory_id,
            embedding_config_id=config_id,
            vector=(0.1, 0.2, 0.3),
        ),
    )

    listed = list_memory_embedding_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        memory_id=memory_id,
    )
    detail = get_memory_embedding_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        memory_embedding_id=UUID(created["embedding"]["id"]),
    )

    assert listed == {
        "items": [created["embedding"]],
        "summary": {
            "memory_id": str(memory_id),
            "total_count": 1,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert detail == {"embedding": created["embedding"]}

    with pytest.raises(MemoryEmbeddingNotFoundError, match="memory .* was not found"):
        list_memory_embedding_records(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            memory_id=uuid4(),
        )

    with pytest.raises(MemoryEmbeddingNotFoundError, match="memory embedding .* was not found"):
        get_memory_embedding_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            memory_embedding_id=uuid4(),
        )
