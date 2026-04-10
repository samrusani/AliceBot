from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from alicebot_api.identity_resolution import (
    EntityScopeResolutionError,
    canonicalize_entity_id,
    merge_entities,
    normalize_identity_alias,
    resolve_entity_alias_optional,
    resolve_scope_entity_filters,
)


class IdentityResolutionStoreStub:
    def __init__(self) -> None:
        self.alias_matches: dict[tuple[str, str], list[dict[str, object]]] = {}
        self.merge_targets: dict[UUID, UUID] = {}
        self.entities: dict[UUID, dict[str, object]] = {}
        self.created_merge_logs: list[tuple[UUID, UUID, str | None]] = []
        self.rebound_requests: list[tuple[UUID, UUID]] = []

    def find_entity_alias_matches(self, *, entity_type: str, normalized_alias: str):
        return list(self.alias_matches.get((entity_type, normalized_alias), []))

    def get_latest_entity_merge_for_source_optional(self, source_entity_id: UUID):
        target_entity_id = self.merge_targets.get(source_entity_id)
        if target_entity_id is None:
            return None
        return {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "reason": "merged duplicate identity",
            "created_at": datetime(2026, 3, 29, 7, 0, tzinfo=UTC),
        }

    def get_entity_optional(self, entity_id: UUID):
        return self.entities.get(entity_id)

    def create_entity_merge_log(self, *, source_entity_id: UUID, target_entity_id: UUID, reason: str | None):
        self.created_merge_logs.append((source_entity_id, target_entity_id, reason))
        return {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "source_entity_id": source_entity_id,
            "target_entity_id": target_entity_id,
            "reason": reason,
            "created_at": datetime(2026, 3, 29, 7, 5, tzinfo=UTC),
        }

    def rebind_continuity_object_entity_references(self, *, source_entity_id: UUID, target_entity_id: UUID) -> int:
        self.rebound_requests.append((source_entity_id, target_entity_id))
        return 3


def test_normalize_identity_alias_collapses_space_and_case() -> None:
    assert normalize_identity_alias("  Project   Orion  ") == "project orion"
    assert normalize_identity_alias("   ") is None


def test_resolve_entity_alias_optional_canonicalizes_merged_matches() -> None:
    store = IdentityResolutionStoreStub()
    source_entity_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    target_entity_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    store.alias_matches[("project", "legacy project label")] = [
        {
            "entity_id": source_entity_id,
            "entity_type": "project",
            "entity_name": "Project Orion",
            "created_at": datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        }
    ]
    store.merge_targets[source_entity_id] = target_entity_id

    resolved = resolve_entity_alias_optional(
        store,  # type: ignore[arg-type]
        entity_type="project",
        alias_text="Legacy Project Label",
    )

    assert resolved == target_entity_id
    assert canonicalize_entity_id(store, entity_id=source_entity_id) == target_entity_id  # type: ignore[arg-type]


def test_resolve_scope_entity_filters_rejects_conflicting_text_and_id() -> None:
    store = IdentityResolutionStoreStub()
    expected_project_id = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
    conflicting_project_id = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
    store.alias_matches[("project", "legacy project label")] = [
        {
            "entity_id": expected_project_id,
            "entity_type": "project",
            "entity_name": "Project Orion",
            "created_at": datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
        }
    ]

    with pytest.raises(
        EntityScopeResolutionError,
        match="project and project_entity_id resolve to different canonical entities",
    ):
        resolve_scope_entity_filters(
            store,  # type: ignore[arg-type]
            project="Legacy Project Label",
            project_entity_id=conflicting_project_id,
        )


def test_merge_entities_records_audit_entry_and_rebinds_bound_objects() -> None:
    store = IdentityResolutionStoreStub()
    source_entity_id = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
    target_entity_id = UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
    store.entities[source_entity_id] = {
        "id": source_entity_id,
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "entity_type": "project",
        "name": "Legacy Project Label",
        "source_memory_ids": ["m-1"],
        "created_at": datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
    }
    store.entities[target_entity_id] = {
        "id": target_entity_id,
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "entity_type": "project",
        "name": "Project Orion",
        "source_memory_ids": ["m-2"],
        "created_at": datetime(2026, 3, 2, 10, 0, tzinfo=UTC),
    }

    payload = merge_entities(
        store,  # type: ignore[arg-type]
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        reason="duplicate import identity",
    )

    assert payload["merge"]["source_entity_id"] == source_entity_id
    assert payload["merge"]["target_entity_id"] == target_entity_id
    assert payload["rebound_object_count"] == 3
    assert store.created_merge_logs == [
        (source_entity_id, target_entity_id, "duplicate import identity")
    ]
    assert store.rebound_requests == [(source_entity_id, target_entity_id)]
