from __future__ import annotations

from datetime import datetime
from uuid import UUID

from alicebot_api.contracts import (
    ENTITY_EDGE_LIST_ORDER,
    EntityEdgeCreateInput,
    EntityEdgeCreateResponse,
    EntityEdgeListResponse,
    EntityEdgeListSummary,
    EntityEdgeRecord,
    isoformat_or_none,
)
from alicebot_api.entity import EntityNotFoundError
from alicebot_api.store import ContinuityStore, EntityEdgeRow


class EntityEdgeValidationError(ValueError):
    """Raised when an entity-edge request fails explicit validation."""


def _serialize_entity_edge(edge: EntityEdgeRow) -> EntityEdgeRecord:
    return {
        "id": str(edge["id"]),
        "from_entity_id": str(edge["from_entity_id"]),
        "to_entity_id": str(edge["to_entity_id"]),
        "relationship_type": edge["relationship_type"],
        "valid_from": isoformat_or_none(edge["valid_from"]),
        "valid_to": isoformat_or_none(edge["valid_to"]),
        "source_memory_ids": edge["source_memory_ids"],
        "created_at": edge["created_at"].isoformat(),
    }


def _dedupe_source_memory_ids(source_memory_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    deduped: list[UUID] = []
    seen: set[UUID] = set()
    for source_memory_id in source_memory_ids:
        if source_memory_id in seen:
            continue
        seen.add(source_memory_id)
        deduped.append(source_memory_id)
    return tuple(deduped)


def _validate_source_memories(store: ContinuityStore, source_memory_ids: tuple[UUID, ...]) -> list[str]:
    normalized_memory_ids = _dedupe_source_memory_ids(source_memory_ids)
    if not normalized_memory_ids:
        raise EntityEdgeValidationError(
            "source_memory_ids must include at least one existing memory owned by the user"
        )

    source_memories = store.list_memories_by_ids(list(normalized_memory_ids))
    found_memory_ids = {memory["id"] for memory in source_memories}
    missing_memory_ids = [
        str(source_memory_id)
        for source_memory_id in normalized_memory_ids
        if source_memory_id not in found_memory_ids
    ]
    if missing_memory_ids:
        raise EntityEdgeValidationError(
            "source_memory_ids must all reference existing memories owned by the user: "
            + ", ".join(missing_memory_ids)
        )

    return [str(source_memory_id) for source_memory_id in normalized_memory_ids]


def _validate_entity_exists(
    store: ContinuityStore,
    *,
    field_name: str,
    entity_id: UUID,
) -> None:
    entity = store.get_entity_optional(entity_id)
    if entity is None:
        raise EntityEdgeValidationError(
            f"{field_name} must reference an existing entity owned by the user: {entity_id}"
        )


def _validate_temporal_range(valid_from: datetime | None, valid_to: datetime | None) -> None:
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise EntityEdgeValidationError("valid_to must be greater than or equal to valid_from")


def create_entity_edge_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    edge: EntityEdgeCreateInput,
) -> EntityEdgeCreateResponse:
    del user_id

    _validate_entity_exists(store, field_name="from_entity_id", entity_id=edge.from_entity_id)
    _validate_entity_exists(store, field_name="to_entity_id", entity_id=edge.to_entity_id)
    _validate_temporal_range(edge.valid_from, edge.valid_to)
    source_memory_ids = _validate_source_memories(store, edge.source_memory_ids)

    created = store.create_entity_edge(
        from_entity_id=edge.from_entity_id,
        to_entity_id=edge.to_entity_id,
        relationship_type=edge.relationship_type,
        valid_from=edge.valid_from,
        valid_to=edge.valid_to,
        source_memory_ids=source_memory_ids,
    )
    return {"edge": _serialize_entity_edge(created)}


def list_entity_edge_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    entity_id: UUID,
) -> EntityEdgeListResponse:
    del user_id

    entity = store.get_entity_optional(entity_id)
    if entity is None:
        raise EntityNotFoundError(f"entity {entity_id} was not found")

    edges = store.list_entity_edges_for_entity(entity_id)
    items = [_serialize_entity_edge(edge) for edge in edges]
    summary: EntityEdgeListSummary = {
        "entity_id": str(entity["id"]),
        "total_count": len(items),
        "order": list(ENTITY_EDGE_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }
