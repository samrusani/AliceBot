from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from alicebot_api.contracts import (
    TemporalExplainQueryInput,
    TemporalStateAtQueryInput,
    TemporalTimelineQueryInput,
)
from alicebot_api.temporal_state import (
    get_temporal_explain,
    get_temporal_state_at,
    get_temporal_timeline,
)


class TemporalStateStoreStub:
    def __init__(self) -> None:
        self.entity_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
        self.project_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.memory_id = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
        self.entity = {
            "id": self.project_id,
            "user_id": uuid4(),
            "entity_type": "project",
            "name": "AliceBot",
            "source_memory_ids": [str(self.memory_id)],
            "created_at": datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        }
        self.memory = {
            "id": self.memory_id,
            "user_id": uuid4(),
            "agent_profile_id": "assistant_default",
            "memory_key": "user.project.current",
            "value": {"name": "AliceBot v2"},
            "status": "active",
            "source_event_ids": ["event-2"],
            "memory_type": "project_fact",
            "confidence": 0.98,
            "salience": None,
            "confirmation_status": "confirmed",
            "trust_class": "human_curated",
            "promotion_eligibility": "promotable",
            "evidence_count": None,
            "independent_source_count": None,
            "extracted_by_model": None,
            "trust_reason": "confirmed by owner",
            "valid_from": None,
            "valid_to": None,
            "last_confirmed_at": None,
            "created_at": datetime(2026, 3, 12, 9, 10, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 12, 10, 10, tzinfo=UTC),
            "deleted_at": None,
        }
        self.revisions = [
            {
                "id": UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
                "user_id": uuid4(),
                "memory_id": self.memory_id,
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": "user.project.current",
                "previous_value": None,
                "new_value": {"name": "AliceBot v1"},
                "source_event_ids": ["event-1"],
                "candidate": {
                    "memory_key": "user.project.current",
                    "value": {"name": "AliceBot v1"},
                    "confidence": 0.91,
                    "confirmation_status": "confirmed",
                    "trust_class": "human_curated",
                    "trust_reason": "initial capture",
                },
                "created_at": datetime(2026, 3, 12, 9, 10, tzinfo=UTC),
            },
            {
                "id": UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
                "user_id": uuid4(),
                "memory_id": self.memory_id,
                "sequence_no": 2,
                "action": "UPDATE",
                "memory_key": "user.project.current",
                "previous_value": {"name": "AliceBot v1"},
                "new_value": {"name": "AliceBot v2"},
                "source_event_ids": ["event-2"],
                "candidate": {
                    "memory_key": "user.project.current",
                    "value": {"name": "AliceBot v2"},
                    "confidence": 0.98,
                    "trust_reason": "confirmed by owner",
                },
                "created_at": datetime(2026, 3, 12, 10, 10, tzinfo=UTC),
            },
        ]
        self.edges = [
            {
                "id": self.entity_id,
                "user_id": uuid4(),
                "from_entity_id": self.entity_id,
                "to_entity_id": self.project_id,
                "relationship_type": "works_on",
                "valid_from": datetime(2026, 3, 12, 9, 30, tzinfo=UTC),
                "valid_to": None,
                "source_memory_ids": [str(self.memory_id)],
                "created_at": datetime(2026, 3, 12, 9, 20, tzinfo=UTC),
            }
        ]

    def get_entity_optional(self, entity_id: UUID):
        if entity_id == self.project_id:
            return self.entity
        return None

    def list_memories_by_ids(self, memory_ids: list[UUID]):
        return [self.memory] if self.memory_id in memory_ids else []

    def list_memory_revisions(self, memory_id: UUID):
        return list(self.revisions) if memory_id == self.memory_id else []

    def list_entity_edges_for_entity(self, entity_id: UUID):
        if entity_id != self.project_id:
            return []
        return list(self.edges)


def test_temporal_state_at_reconstructs_historical_fact_state() -> None:
    store = TemporalStateStoreStub()

    historical = get_temporal_state_at(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TemporalStateAtQueryInput(
            entity_id=store.project_id,
            at=datetime(2026, 3, 12, 9, 45, tzinfo=UTC),
        ),
    )
    current = get_temporal_state_at(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TemporalStateAtQueryInput(
            entity_id=store.project_id,
            at=datetime(2026, 3, 12, 10, 30, tzinfo=UTC),
        ),
    )

    assert historical["state_at"]["facts"][0]["value"] == {"name": "AliceBot v1"}
    assert current["state_at"]["facts"][0]["value"] == {"name": "AliceBot v2"}
    assert historical["state_at"]["edges"][0]["relationship_type"] == "works_on"
    assert current["state_at"]["summary"]["fact_count"] == 1


def test_temporal_timeline_is_chronological_and_explain_includes_provenance_and_supersession() -> None:
    store = TemporalStateStoreStub()

    timeline = get_temporal_timeline(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TemporalTimelineQueryInput(
            entity_id=store.project_id,
            limit=10,
        ),
    )
    explain = get_temporal_explain(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        request=TemporalExplainQueryInput(
            entity_id=store.project_id,
            at=datetime(2026, 3, 12, 9, 45, tzinfo=UTC),
        ),
    )

    assert [event["event_type"] for event in timeline["timeline"]["events"]] == [
        "entity_created",
        "fact_add",
        "edge_recorded",
        "fact_update",
    ]
    fact_explain = explain["explain"]["facts"][0]
    assert fact_explain["trust"]["trust_class"] == "human_curated"
    assert fact_explain["provenance"]["source_event_ids"] == ["event-1"]
    assert [item["sequence_no"] for item in fact_explain["supersession_chain"]] == [1, 2]
    assert fact_explain["supersession_chain"][0]["effective_at_as_of"] is True
    assert fact_explain["supersession_chain"][1]["effective_at_as_of"] is False
