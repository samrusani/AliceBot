from __future__ import annotations

from uuid import UUID

from alicebot_api.contracts import (
    ENTITY_LIST_ORDER,
    EntityCreateInput,
    EntityCreateResponse,
    EntityDetailResponse,
    EntityListResponse,
    EntityListSummary,
    EntityRecord,
)
from alicebot_api.identity_resolution import normalize_identity_alias
from alicebot_api.store import ContinuityStore, EntityRow


class EntityValidationError(ValueError):
    """Raised when an entity create request fails explicit validation."""


class EntityNotFoundError(LookupError):
    """Raised when a requested entity is not visible inside the current user scope."""


def _serialize_entity(entity: EntityRow) -> EntityRecord:
    return {
        "id": str(entity["id"]),
        "entity_type": entity["entity_type"],
        "name": entity["name"],
        "source_memory_ids": entity["source_memory_ids"],
        "created_at": entity["created_at"].isoformat(),
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
        raise EntityValidationError(
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
        raise EntityValidationError(
            "source_memory_ids must all reference existing memories owned by the user: "
            + ", ".join(missing_memory_ids)
        )

    return [str(source_memory_id) for source_memory_id in normalized_memory_ids]


def create_entity_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    entity: EntityCreateInput,
) -> EntityCreateResponse:
    del user_id

    source_memory_ids = _validate_source_memories(store, entity.source_memory_ids)
    created = store.create_entity(
        entity_type=entity.entity_type,
        name=entity.name,
        source_memory_ids=source_memory_ids,
    )
    normalized_alias = normalize_identity_alias(entity.name)
    if normalized_alias is not None:
        store.create_entity_alias(
            entity_id=created["id"],
            alias=created["name"],
            normalized_alias=normalized_alias,
        )
    return {"entity": _serialize_entity(created)}


def list_entity_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> EntityListResponse:
    del user_id

    entities = store.list_entities()
    items = [_serialize_entity(entity) for entity in entities]
    summary: EntityListSummary = {
        "total_count": len(items),
        "order": list(ENTITY_LIST_ORDER),
    }
    return {
        "items": items,
        "summary": summary,
    }


def get_entity_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    entity_id: UUID,
) -> EntityDetailResponse:
    del user_id

    entity = store.get_entity_optional(entity_id)
    if entity is None:
        raise EntityNotFoundError(f"entity {entity_id} was not found")

    return {"entity": _serialize_entity(entity)}
