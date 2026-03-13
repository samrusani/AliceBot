from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import EntityEdgeCreateInput
from alicebot_api.entity import EntityNotFoundError
from alicebot_api.entity_edge import (
    EntityEdgeValidationError,
    create_entity_edge_record,
    list_entity_edge_records,
)


class EntityEdgeStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.memories: dict[UUID, dict[str, object]] = {}
        self.entities: dict[UUID, dict[str, object]] = {}
        self.created_edges: list[dict[str, object]] = []

    def list_memories_by_ids(self, memory_ids: list[UUID]) -> list[dict[str, object]]:
        return [self.memories[memory_id] for memory_id in memory_ids if memory_id in self.memories]

    def get_entity_optional(self, entity_id: UUID) -> dict[str, object] | None:
        return self.entities.get(entity_id)

    def create_entity_edge(
        self,
        *,
        from_entity_id: UUID,
        to_entity_id: UUID,
        relationship_type: str,
        valid_from: datetime | None,
        valid_to: datetime | None,
        source_memory_ids: list[str],
    ) -> dict[str, object]:
        edge_id = uuid4()
        edge = {
            "id": edge_id,
            "user_id": uuid4(),
            "from_entity_id": from_entity_id,
            "to_entity_id": to_entity_id,
            "relationship_type": relationship_type,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "source_memory_ids": source_memory_ids,
            "created_at": self.base_time + timedelta(minutes=len(self.created_edges)),
        }
        self.created_edges.append(edge)
        return edge

    def list_entity_edges_for_entity(self, entity_id: UUID) -> list[dict[str, object]]:
        return [
            edge
            for edge in self.created_edges
            if edge["from_entity_id"] == entity_id or edge["to_entity_id"] == entity_id
        ]


def seed_memory(store: EntityEdgeStoreStub) -> UUID:
    memory_id = uuid4()
    store.memories[memory_id] = {
        "id": memory_id,
        "memory_key": "user.project.current",
    }
    return memory_id


def seed_entity(store: EntityEdgeStoreStub) -> UUID:
    entity_id = uuid4()
    store.entities[entity_id] = {
        "id": entity_id,
        "name": "entity",
    }
    return entity_id


def test_create_entity_edge_record_rejects_missing_entities() -> None:
    store = EntityEdgeStoreStub()
    memory_id = seed_memory(store)

    with pytest.raises(
        EntityEdgeValidationError,
        match="from_entity_id must reference an existing entity owned by the user",
    ):
        create_entity_edge_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            edge=EntityEdgeCreateInput(
                from_entity_id=uuid4(),
                to_entity_id=uuid4(),
                relationship_type="works_on",
                valid_from=None,
                valid_to=None,
                source_memory_ids=(memory_id,),
            ),
        )


def test_create_entity_edge_record_rejects_invalid_temporal_range() -> None:
    store = EntityEdgeStoreStub()
    from_entity_id = seed_entity(store)
    to_entity_id = seed_entity(store)
    memory_id = seed_memory(store)

    with pytest.raises(
        EntityEdgeValidationError,
        match="valid_to must be greater than or equal to valid_from",
    ):
        create_entity_edge_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            edge=EntityEdgeCreateInput(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                relationship_type="works_on",
                valid_from=datetime(2026, 3, 12, 11, 0, tzinfo=UTC),
                valid_to=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
                source_memory_ids=(memory_id,),
            ),
        )


def test_create_entity_edge_record_creates_edge_with_deduped_source_memories() -> None:
    store = EntityEdgeStoreStub()
    from_entity_id = seed_entity(store)
    to_entity_id = seed_entity(store)
    first_memory_id = seed_memory(store)
    second_memory_id = seed_memory(store)
    valid_from = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
    valid_to = datetime(2026, 3, 12, 10, 0, tzinfo=UTC)

    payload = create_entity_edge_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        edge=EntityEdgeCreateInput(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relationship_type="works_on",
            valid_from=valid_from,
            valid_to=valid_to,
            source_memory_ids=(first_memory_id, first_memory_id, second_memory_id),
        ),
    )

    assert payload == {
        "edge": {
            "id": payload["edge"]["id"],
            "from_entity_id": str(from_entity_id),
            "to_entity_id": str(to_entity_id),
            "relationship_type": "works_on",
            "valid_from": valid_from.isoformat(),
            "valid_to": valid_to.isoformat(),
            "source_memory_ids": [str(first_memory_id), str(second_memory_id)],
            "created_at": store.created_edges[0]["created_at"].isoformat(),
        }
    }


def test_list_entity_edge_records_returns_deterministic_shape() -> None:
    store = EntityEdgeStoreStub()
    primary_entity_id = seed_entity(store)
    secondary_entity_id = seed_entity(store)
    tertiary_entity_id = seed_entity(store)
    first_memory_id = seed_memory(store)
    second_memory_id = seed_memory(store)

    first_edge = store.create_entity_edge(
        from_entity_id=primary_entity_id,
        to_entity_id=secondary_entity_id,
        relationship_type="works_on",
        valid_from=None,
        valid_to=None,
        source_memory_ids=[str(first_memory_id)],
    )
    second_edge = store.create_entity_edge(
        from_entity_id=tertiary_entity_id,
        to_entity_id=primary_entity_id,
        relationship_type="references",
        valid_from=None,
        valid_to=None,
        source_memory_ids=[str(second_memory_id)],
    )

    payload = list_entity_edge_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        entity_id=primary_entity_id,
    )

    assert payload == {
        "items": [
            {
                "id": str(first_edge["id"]),
                "from_entity_id": str(primary_entity_id),
                "to_entity_id": str(secondary_entity_id),
                "relationship_type": "works_on",
                "valid_from": None,
                "valid_to": None,
                "source_memory_ids": [str(first_memory_id)],
                "created_at": first_edge["created_at"].isoformat(),
            },
            {
                "id": str(second_edge["id"]),
                "from_entity_id": str(tertiary_entity_id),
                "to_entity_id": str(primary_entity_id),
                "relationship_type": "references",
                "valid_from": None,
                "valid_to": None,
                "source_memory_ids": [str(second_memory_id)],
                "created_at": second_edge["created_at"].isoformat(),
            },
        ],
        "summary": {
            "entity_id": str(primary_entity_id),
            "total_count": 2,
            "order": ["created_at_asc", "id_asc"],
        },
    }


def test_list_entity_edge_records_raises_not_found_for_inaccessible_entity() -> None:
    with pytest.raises(EntityNotFoundError, match="entity .* was not found"):
        list_entity_edge_records(
            EntityEdgeStoreStub(),  # type: ignore[arg-type]
            user_id=uuid4(),
            entity_id=uuid4(),
        )
