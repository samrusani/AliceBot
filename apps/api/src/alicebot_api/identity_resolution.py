from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from alicebot_api.store import ContinuityStore


class EntityScopeResolutionError(ValueError):
    """Raised when scope filters cannot be resolved coherently."""


def normalize_identity_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    if normalized == "":
        return None
    return normalized


def normalize_identity_alias(value: str | None) -> str | None:
    normalized = normalize_identity_text(value)
    if normalized is None:
        return None
    return normalized.casefold()


def canonicalize_entity_id(
    store: ContinuityStore,
    *,
    entity_id: UUID | None,
) -> UUID | None:
    if entity_id is None:
        return None

    current = entity_id
    seen: set[UUID] = set()
    while current not in seen:
        seen.add(current)
        merge = store.get_latest_entity_merge_for_source_optional(current)
        if merge is None:
            return current
        current = merge["target_entity_id"]
    return current


def resolve_entity_alias_optional(
    store: ContinuityStore,
    *,
    entity_type: str,
    alias_text: str | None,
) -> UUID | None:
    normalized_alias = normalize_identity_alias(alias_text)
    if normalized_alias is None:
        return None

    matches = store.find_entity_alias_matches(
        entity_type=entity_type,
        normalized_alias=normalized_alias,
    )
    canonical_ids: list[UUID] = []
    seen: set[UUID] = set()
    for match in matches:
        canonical_id = canonicalize_entity_id(store, entity_id=match["entity_id"])
        if canonical_id is None or canonical_id in seen:
            continue
        seen.add(canonical_id)
        canonical_ids.append(canonical_id)

    if len(canonical_ids) == 1:
        return canonical_ids[0]
    return None


@dataclass(frozen=True, slots=True)
class ResolvedScopeEntityFilters:
    project: str | None
    person: str | None
    topic: str | None
    project_entity_id: UUID | None
    person_entity_id: UUID | None
    topic_entity_id: UUID | None


def resolve_scope_entity_filters(
    store: ContinuityStore,
    *,
    project: str | None = None,
    person: str | None = None,
    topic: str | None = None,
    project_entity_id: UUID | None = None,
    person_entity_id: UUID | None = None,
    topic_entity_id: UUID | None = None,
) -> ResolvedScopeEntityFilters:
    normalized_project = normalize_identity_text(project)
    normalized_person = normalize_identity_text(person)
    normalized_topic = normalize_identity_text(topic)

    canonical_project_entity_id = canonicalize_entity_id(store, entity_id=project_entity_id)
    canonical_person_entity_id = canonicalize_entity_id(store, entity_id=person_entity_id)
    canonical_topic_entity_id = canonicalize_entity_id(store, entity_id=topic_entity_id)

    resolved_project_entity_id = resolve_entity_alias_optional(
        store,
        entity_type="project",
        alias_text=normalized_project,
    )
    resolved_person_entity_id = resolve_entity_alias_optional(
        store,
        entity_type="person",
        alias_text=normalized_person,
    )
    resolved_topic_entity_id = resolve_entity_alias_optional(
        store,
        entity_type="topic",
        alias_text=normalized_topic,
    )

    if (
        canonical_project_entity_id is not None
        and resolved_project_entity_id is not None
        and canonical_project_entity_id != resolved_project_entity_id
    ):
        raise EntityScopeResolutionError("project and project_entity_id resolve to different canonical entities")
    if (
        canonical_person_entity_id is not None
        and resolved_person_entity_id is not None
        and canonical_person_entity_id != resolved_person_entity_id
    ):
        raise EntityScopeResolutionError("person and person_entity_id resolve to different canonical entities")
    if (
        canonical_topic_entity_id is not None
        and resolved_topic_entity_id is not None
        and canonical_topic_entity_id != resolved_topic_entity_id
    ):
        raise EntityScopeResolutionError("topic and topic_entity_id resolve to different canonical entities")

    return ResolvedScopeEntityFilters(
        project=normalized_project,
        person=normalized_person,
        topic=normalized_topic,
        project_entity_id=canonical_project_entity_id or resolved_project_entity_id,
        person_entity_id=canonical_person_entity_id or resolved_person_entity_id,
        topic_entity_id=canonical_topic_entity_id or resolved_topic_entity_id,
    )


def merge_entities(
    store: ContinuityStore,
    *,
    source_entity_id: UUID,
    target_entity_id: UUID,
    reason: str | None = None,
) -> dict[str, object]:
    source_entity = store.get_entity_optional(source_entity_id)
    if source_entity is None:
        raise EntityScopeResolutionError(f"source entity {source_entity_id} was not found")
    target_entity = store.get_entity_optional(target_entity_id)
    if target_entity is None:
        raise EntityScopeResolutionError(f"target entity {target_entity_id} was not found")
    if source_entity_id == target_entity_id:
        raise EntityScopeResolutionError("source and target entities must differ")
    if source_entity["entity_type"] != target_entity["entity_type"]:
        raise EntityScopeResolutionError("entity merges require matching entity_type values")

    merge_record = store.create_entity_merge_log(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        reason=normalize_identity_text(reason),
    )
    rebound_object_count = store.rebind_continuity_object_entity_references(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
    )
    return {
        "merge": merge_record,
        "rebound_object_count": rebound_object_count,
    }
