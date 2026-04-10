from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import TrustedFactPatternListQueryInput, TrustedFactPlaybookListQueryInput
from alicebot_api.trusted_fact_promotions import (
    TrustedFactPromotionNotFoundError,
    get_trusted_fact_pattern,
    list_trusted_fact_patterns,
    list_trusted_fact_playbooks,
    sync_trusted_fact_promotions,
)


class TrustedFactPromotionStoreStub:
    def __init__(self) -> None:
        self.memories: list[dict[str, object]] = []
        self.revisions: dict[UUID, list[dict[str, object]]] = {}
        self.patterns: dict[UUID, dict[str, object]] = {}
        self.playbooks: dict[UUID, dict[str, object]] = {}
        self._base_time = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)

    def list_memories(self) -> list[dict[str, object]]:
        return list(self.memories)

    def list_memory_revisions(self, memory_id: UUID) -> list[dict[str, object]]:
        return list(self.revisions.get(memory_id, []))

    def upsert_fact_pattern(self, **kwargs):  # type: ignore[no-untyped-def]
        pattern_id = kwargs["pattern_id"]
        existing = self.patterns.get(pattern_id)
        created_at = self._base_time if existing is None else existing["created_at"]
        row = {
            "id": pattern_id,
            "user_id": self._current_user_id(),
            "pattern_key": kwargs["pattern_key"],
            "title": kwargs["title"],
            "memory_type": kwargs["memory_type"],
            "namespace_key": kwargs["namespace_key"],
            "fact_count": kwargs["fact_count"],
            "source_fact_ids": kwargs["source_fact_ids"],
            "evidence_chain": kwargs["evidence_chain"],
            "explanation": kwargs["explanation"],
            "created_at": created_at,
            "updated_at": self._base_time + timedelta(minutes=1),
        }
        self.patterns[pattern_id] = row
        return row

    def list_fact_patterns(self, *, limit: int):
        rows = sorted(
            self.patterns.values(),
            key=lambda row: (row["memory_type"], row["namespace_key"], row["title"], str(row["id"])),
        )
        return rows[:limit]

    def count_fact_patterns(self) -> int:
        return len(self.patterns)

    def get_fact_pattern_optional(self, pattern_id: UUID):
        return self.patterns.get(pattern_id)

    def delete_fact_patterns_not_in(self, pattern_ids: list[UUID]) -> None:
        keep = set(pattern_ids)
        self.patterns = {pattern_id: row for pattern_id, row in self.patterns.items() if pattern_id in keep}

    def upsert_fact_playbook(self, **kwargs):  # type: ignore[no-untyped-def]
        playbook_id = kwargs["playbook_id"]
        existing = self.playbooks.get(playbook_id)
        created_at = self._base_time if existing is None else existing["created_at"]
        row = {
            "id": playbook_id,
            "user_id": self._current_user_id(),
            "playbook_key": kwargs["playbook_key"],
            "pattern_id": kwargs["pattern_id"],
            "pattern_key": kwargs["pattern_key"],
            "title": kwargs["title"],
            "memory_type": kwargs["memory_type"],
            "source_fact_ids": kwargs["source_fact_ids"],
            "source_pattern_ids": kwargs["source_pattern_ids"],
            "steps": kwargs["steps"],
            "explanation": kwargs["explanation"],
            "created_at": created_at,
            "updated_at": self._base_time + timedelta(minutes=1),
        }
        self.playbooks[playbook_id] = row
        return row

    def list_fact_playbooks(self, *, limit: int):
        rows = sorted(
            self.playbooks.values(),
            key=lambda row: (row["memory_type"], row["pattern_key"], row["title"], str(row["id"])),
        )
        return rows[:limit]

    def count_fact_playbooks(self) -> int:
        return len(self.playbooks)

    def get_fact_playbook_optional(self, playbook_id: UUID):
        return self.playbooks.get(playbook_id)

    def delete_fact_playbooks_not_in(self, playbook_ids: list[UUID]) -> None:
        keep = set(playbook_ids)
        self.playbooks = {
            playbook_id: row for playbook_id, row in self.playbooks.items() if playbook_id in keep
        }

    def _current_user_id(self) -> UUID:
        return UUID(str(self.memories[0]["user_id"]))


def _memory(
    *,
    memory_id: UUID,
    user_id: UUID,
    memory_key: str,
    value: object,
    trust_class: str,
    promotion_eligibility: str = "promotable",
    extracted_by_model: str | None = None,
    independent_source_count: int | None = None,
) -> dict[str, object]:
    return {
        "id": memory_id,
        "user_id": user_id,
        "agent_profile_id": "assistant_default",
        "memory_key": memory_key,
        "value": value,
        "status": "active",
        "source_event_ids": [f"event-{memory_key.split('.')[-1]}"],
        "memory_type": "preference",
        "confidence": 0.95,
        "salience": 0.5,
        "confirmation_status": "confirmed",
        "trust_class": trust_class,
        "promotion_eligibility": promotion_eligibility,
        "evidence_count": 1,
        "independent_source_count": independent_source_count,
        "extracted_by_model": extracted_by_model,
        "trust_reason": "trusted test fact",
        "valid_from": None,
        "valid_to": None,
        "last_confirmed_at": None,
        "created_at": datetime(2026, 4, 10, 9, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 10, 9, 1, tzinfo=UTC),
        "deleted_at": None,
    }


def _revision(*, memory_id: UUID, memory_key: str, sequence_no: int) -> dict[str, object]:
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "memory_id": memory_id,
        "sequence_no": sequence_no,
        "action": "ADD",
        "memory_key": memory_key,
        "previous_value": None,
        "new_value": {"captured": memory_key},
        "source_event_ids": [f"event-{memory_key.split('.')[-1]}"],
        "candidate": {"memory_key": memory_key},
        "created_at": datetime(2026, 4, 10, 9, sequence_no, tzinfo=UTC),
    }


def test_sync_trusted_fact_promotions_excludes_single_source_llm_facts() -> None:
    store = TrustedFactPromotionStoreStub()
    user_id = uuid4()
    coffee_id = uuid4()
    tea_id = uuid4()
    generated_id = uuid4()

    store.memories = [
        _memory(
            memory_id=coffee_id,
            user_id=user_id,
            memory_key="user.preference.coffee",
            value={"drink": "coffee"},
            trust_class="human_curated",
        ),
        _memory(
            memory_id=tea_id,
            user_id=user_id,
            memory_key="user.preference.tea",
            value={"drink": "tea"},
            trust_class="deterministic",
        ),
        _memory(
            memory_id=generated_id,
            user_id=user_id,
            memory_key="user.preference.generated",
            value={"drink": "mate"},
            trust_class="llm_corroborated",
            extracted_by_model="gpt-5.4-mini",
            independent_source_count=1,
        ),
    ]
    store.revisions = {
        coffee_id: [_revision(memory_id=coffee_id, memory_key="user.preference.coffee", sequence_no=1)],
        tea_id: [_revision(memory_id=tea_id, memory_key="user.preference.tea", sequence_no=2)],
        generated_id: [_revision(memory_id=generated_id, memory_key="user.preference.generated", sequence_no=3)],
    }

    sync_trusted_fact_promotions(store, user_id=user_id)  # type: ignore[arg-type]

    patterns = list_trusted_fact_patterns(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TrustedFactPatternListQueryInput(limit=10),
    )
    assert patterns["summary"]["total_count"] == 1
    pattern = patterns["items"][0]
    assert pattern["fact_count"] == 2
    assert pattern["source_fact_ids"] == [str(coffee_id), str(tea_id)]
    assert [link["fact_id"] for link in pattern["evidence_chain"]] == [str(coffee_id), str(tea_id)]

    playbooks = list_trusted_fact_playbooks(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=TrustedFactPlaybookListQueryInput(limit=10),
    )
    assert playbooks["summary"]["total_count"] == 1
    playbook = playbooks["items"][0]
    assert playbook["source_fact_ids"] == [str(coffee_id), str(tea_id)]
    assert len(playbook["steps"]) == 2
    assert "no opaque synthesis" in playbook["explanation"]


def test_get_trusted_fact_pattern_raises_not_found_for_unknown_id() -> None:
    store = TrustedFactPromotionStoreStub()

    with pytest.raises(TrustedFactPromotionNotFoundError):
        get_trusted_fact_pattern(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            pattern_id=uuid4(),
        )
