from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import EntityCreateInput
from alicebot_api.entity import (
    EntityNotFoundError,
    EntityValidationError,
    create_entity_record,
    get_entity_record,
    list_entity_records,
)


class EntityStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.memories: dict[UUID, dict[str, object]] = {}
        self.created_entities: list[dict[str, object]] = []
        self.entity_by_id: dict[UUID, dict[str, object]] = {}

    def list_memories_by_ids(self, memory_ids: list[UUID]) -> list[dict[str, object]]:
        return [self.memories[memory_id] for memory_id in memory_ids if memory_id in self.memories]

    def create_entity(
        self,
        *,
        entity_type: str,
        name: str,
        source_memory_ids: list[str],
    ) -> dict[str, object]:
        entity_id = uuid4()
        entity = {
            "id": entity_id,
            "user_id": uuid4(),
            "entity_type": entity_type,
            "name": name,
            "source_memory_ids": source_memory_ids,
            "created_at": self.base_time + timedelta(minutes=len(self.created_entities)),
        }
        self.created_entities.append(entity)
        self.entity_by_id[entity_id] = entity
        return entity

    def list_entities(self) -> list[dict[str, object]]:
        return list(self.created_entities)

    def get_entity_optional(self, entity_id: UUID) -> dict[str, object] | None:
        return self.entity_by_id.get(entity_id)


def seed_memory(store: EntityStoreStub) -> UUID:
    memory_id = uuid4()
    store.memories[memory_id] = {
        "id": memory_id,
        "memory_key": "user.preference.coffee",
    }
    return memory_id


def test_create_entity_record_rejects_empty_source_memory_ids() -> None:
    store = EntityStoreStub()

    with pytest.raises(
        EntityValidationError,
        match="source_memory_ids must include at least one existing memory owned by the user",
    ):
        create_entity_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            entity=EntityCreateInput(
                entity_type="person",
                name="Samir",
                source_memory_ids=(),
            ),
        )


def test_create_entity_record_rejects_missing_source_memories() -> None:
    store = EntityStoreStub()

    with pytest.raises(
        EntityValidationError,
        match="source_memory_ids must all reference existing memories owned by the user",
    ):
        create_entity_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            entity=EntityCreateInput(
                entity_type="project",
                name="AliceBot",
                source_memory_ids=(uuid4(),),
            ),
        )


def test_create_entity_record_creates_entity_with_deduped_source_memories() -> None:
    store = EntityStoreStub()
    first_memory_id = seed_memory(store)
    second_memory_id = seed_memory(store)

    payload = create_entity_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        entity=EntityCreateInput(
            entity_type="project",
            name="AliceBot",
            source_memory_ids=(first_memory_id, first_memory_id, second_memory_id),
        ),
    )

    assert payload["entity"]["entity_type"] == "project"
    assert payload["entity"]["name"] == "AliceBot"
    assert payload["entity"]["source_memory_ids"] == [str(first_memory_id), str(second_memory_id)]


def test_list_entity_records_returns_deterministic_shape() -> None:
    store = EntityStoreStub()
    first_memory_id = seed_memory(store)
    second_memory_id = seed_memory(store)
    first_entity = store.create_entity(
        entity_type="person",
        name="Samir",
        source_memory_ids=[str(first_memory_id)],
    )
    second_entity = store.create_entity(
        entity_type="project",
        name="AliceBot",
        source_memory_ids=[str(second_memory_id)],
    )

    payload = list_entity_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
    )

    assert payload == {
        "items": [
            {
                "id": str(first_entity["id"]),
                "entity_type": "person",
                "name": "Samir",
                "source_memory_ids": [str(first_memory_id)],
                "created_at": first_entity["created_at"].isoformat(),
            },
            {
                "id": str(second_entity["id"]),
                "entity_type": "project",
                "name": "AliceBot",
                "source_memory_ids": [str(second_memory_id)],
                "created_at": second_entity["created_at"].isoformat(),
            },
        ],
        "summary": {
            "total_count": 2,
            "order": ["created_at_asc", "id_asc"],
        },
    }


def test_get_entity_record_raises_not_found_for_inaccessible_entity() -> None:
    with pytest.raises(EntityNotFoundError, match="entity .* was not found"):
        get_entity_record(
            EntityStoreStub(),  # type: ignore[arg-type]
            user_id=uuid4(),
            entity_id=uuid4(),
        )
