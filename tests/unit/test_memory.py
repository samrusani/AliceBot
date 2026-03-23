from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import MemoryCandidateInput
from alicebot_api.memory import (
    MemoryAdmissionValidationError,
    MemoryReviewNotFoundError,
    admit_memory_candidate,
    create_memory_review_label_record,
    get_memory_evaluation_summary,
    get_memory_review_record,
    list_memory_review_queue_records,
    list_memory_review_label_records,
    list_memory_review_records,
    list_memory_revision_review_records,
)


class MemoryStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
        self.events: dict[UUID, dict[str, object]] = {}
        self.memory: dict[str, object] | None = None
        self.revisions: list[dict[str, object]] = []

    def list_events_by_ids(self, event_ids: list[UUID]) -> list[dict[str, object]]:
        return [self.events[event_id] for event_id in event_ids if event_id in self.events]

    def get_memory_by_key(self, memory_key: str) -> dict[str, object] | None:
        if self.memory is None or self.memory["memory_key"] != memory_key:
            return None
        return self.memory

    def create_memory(
        self,
        *,
        memory_key: str,
        value,
        status: str,
        source_event_ids: list[str],
        memory_type: str = "preference",
        confidence: float | None = None,
        salience: float | None = None,
        confirmation_status: str = "unconfirmed",
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        last_confirmed_at: datetime | None = None,
    ) -> dict[str, object]:
        self.memory = {
            "id": uuid4(),
            "user_id": uuid4(),
            "memory_key": memory_key,
            "value": value,
            "status": status,
            "source_event_ids": source_event_ids,
            "memory_type": memory_type,
            "confidence": confidence,
            "salience": salience,
            "confirmation_status": confirmation_status,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "last_confirmed_at": last_confirmed_at,
            "created_at": self.base_time,
            "updated_at": self.base_time,
            "deleted_at": None,
        }
        return self.memory

    def update_memory(
        self,
        *,
        memory_id: UUID,
        value,
        status: str,
        source_event_ids: list[str],
        memory_type: str = "preference",
        confidence: float | None = None,
        salience: float | None = None,
        confirmation_status: str = "unconfirmed",
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        last_confirmed_at: datetime | None = None,
    ) -> dict[str, object]:
        assert self.memory is not None
        assert self.memory["id"] == memory_id
        updated_at = self.base_time + timedelta(minutes=len(self.revisions) + 1)
        self.memory = {
            **self.memory,
            "value": value,
            "status": status,
            "source_event_ids": source_event_ids,
            "memory_type": memory_type,
            "confidence": confidence,
            "salience": salience,
            "confirmation_status": confirmation_status,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "last_confirmed_at": last_confirmed_at,
            "updated_at": updated_at,
            "deleted_at": updated_at if status == "deleted" else None,
        }
        return self.memory

    def append_memory_revision(
        self,
        *,
        memory_id: UUID,
        action: str,
        memory_key: str,
        previous_value,
        new_value,
        source_event_ids: list[str],
        candidate: dict[str, object],
    ) -> dict[str, object]:
        revision = {
            "id": uuid4(),
            "user_id": self.memory["user_id"] if self.memory is not None else uuid4(),
            "memory_id": memory_id,
            "sequence_no": len(self.revisions) + 1,
            "action": action,
            "memory_key": memory_key,
            "previous_value": previous_value,
            "new_value": new_value,
            "source_event_ids": source_event_ids,
            "candidate": candidate,
            "created_at": self.base_time + timedelta(minutes=len(self.revisions) + 1),
        }
        self.revisions.append(revision)
        return revision


def seed_event(store: MemoryStoreStub) -> UUID:
    event_id = uuid4()
    store.events[event_id] = {
        "id": event_id,
        "sequence_no": 1,
        "kind": "message.user",
        "payload": {"text": "evidence"},
        "created_at": store.base_time,
    }
    return event_id


def test_admit_memory_candidate_defaults_to_noop_when_value_is_missing() -> None:
    store = MemoryStoreStub()
    event_id = seed_event(store)

    decision = admit_memory_candidate(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        candidate=MemoryCandidateInput(
            memory_key="user.preference.coffee",
            value=None,
            source_event_ids=(event_id,),
        ),
    )

    assert decision.action == "NOOP"
    assert decision.reason == "candidate_value_missing"
    assert decision.memory is None
    assert decision.revision is None


def test_admit_memory_candidate_rejects_missing_source_events() -> None:
    store = MemoryStoreStub()

    with pytest.raises(
        MemoryAdmissionValidationError,
        match="source_event_ids must all reference existing events owned by the user",
    ):
        admit_memory_candidate(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            candidate=MemoryCandidateInput(
                memory_key="user.preference.tea",
                value={"likes": True},
                source_event_ids=(uuid4(),),
            ),
        )


def test_admit_memory_candidate_rejects_empty_source_event_ids() -> None:
    store = MemoryStoreStub()

    with pytest.raises(
        MemoryAdmissionValidationError,
        match="source_event_ids must include at least one existing event owned by the user",
    ):
        admit_memory_candidate(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            candidate=MemoryCandidateInput(
                memory_key="user.preference.tea",
                value={"likes": True},
                source_event_ids=(),
            ),
        )


def test_admit_memory_candidate_rejects_invalid_memory_type() -> None:
    store = MemoryStoreStub()
    event_id = seed_event(store)

    with pytest.raises(
        MemoryAdmissionValidationError,
        match="memory_type must be one of:",
    ):
        admit_memory_candidate(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            candidate=MemoryCandidateInput(
                memory_key="user.preference.tea",
                value={"likes": True},
                source_event_ids=(event_id,),
                memory_type="not_a_valid_type",
            ),
        )


def test_admit_memory_candidate_adds_new_memory_with_first_revision() -> None:
    store = MemoryStoreStub()
    event_id = seed_event(store)

    decision = admit_memory_candidate(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        candidate=MemoryCandidateInput(
            memory_key="user.preference.coffee",
            value={"likes": "oat milk"},
            source_event_ids=(event_id,),
        ),
    )

    assert decision.action == "ADD"
    assert decision.reason == "source_backed_add"
    assert decision.memory is not None
    assert decision.memory["memory_key"] == "user.preference.coffee"
    assert decision.memory["status"] == "active"
    assert decision.revision is not None
    assert decision.revision["sequence_no"] == 1
    assert decision.revision["action"] == "ADD"
    assert decision.revision["new_value"] == {"likes": "oat milk"}


def test_admit_memory_candidate_updates_existing_memory_and_appends_revision() -> None:
    store = MemoryStoreStub()
    event_id = seed_event(store)
    created = store.create_memory(
        memory_key="user.preference.coffee",
        value={"likes": "black"},
        status="active",
        source_event_ids=[str(event_id)],
    )
    store.append_memory_revision(
        memory_id=created["id"],
        action="ADD",
        memory_key="user.preference.coffee",
        previous_value=None,
        new_value={"likes": "black"},
        source_event_ids=[str(event_id)],
        candidate={
            "memory_key": "user.preference.coffee",
            "value": {"likes": "black"},
            "source_event_ids": [str(event_id)],
            "delete_requested": False,
        },
    )

    decision = admit_memory_candidate(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        candidate=MemoryCandidateInput(
            memory_key="user.preference.coffee",
            value={"likes": "oat milk"},
            source_event_ids=(event_id,),
        ),
    )

    assert decision.action == "UPDATE"
    assert decision.reason == "source_backed_update"
    assert decision.memory is not None
    assert decision.memory["value"] == {"likes": "oat milk"}
    assert decision.revision is not None
    assert decision.revision["sequence_no"] == 2
    assert decision.revision["previous_value"] == {"likes": "black"}
    assert decision.revision["new_value"] == {"likes": "oat milk"}


def test_admit_memory_candidate_marks_memory_deleted_and_appends_revision() -> None:
    store = MemoryStoreStub()
    event_id = seed_event(store)
    created = store.create_memory(
        memory_key="user.preference.coffee",
        value={"likes": "black"},
        status="active",
        source_event_ids=[str(event_id)],
    )

    decision = admit_memory_candidate(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        candidate=MemoryCandidateInput(
            memory_key="user.preference.coffee",
            value=None,
            source_event_ids=(event_id,),
            delete_requested=True,
        ),
    )

    assert decision.action == "DELETE"
    assert decision.reason == "source_backed_delete"
    assert decision.memory is not None
    assert UUID(decision.memory["id"]) == created["id"]
    assert decision.memory["status"] == "deleted"
    assert decision.revision is not None
    assert decision.revision["sequence_no"] == 1
    assert decision.revision["action"] == "DELETE"
    assert decision.revision["new_value"] is None


class MemoryReviewStoreStub:
    def __init__(self) -> None:
        self.memories: list[dict[str, object]] = []
        self.revisions: dict[UUID, list[dict[str, object]]] = {}
        self.labels: dict[UUID, list[dict[str, object]]] = {}

    def count_memories(self, *, status: str | None = None) -> int:
        return len(self._filtered_memories(status))

    def list_review_memories(self, *, status: str | None = None, limit: int) -> list[dict[str, object]]:
        return self._review_sorted_memories(self._filtered_memories(status))[:limit]

    def count_unlabeled_review_memories(self) -> int:
        return len(
            [memory for memory in self.memories if memory["status"] == "active" and not self.labels.get(memory["id"])]
        )

    def list_unlabeled_review_memories(self, *, limit: int) -> list[dict[str, object]]:
        return self._review_sorted_memories(
            [
                memory
                for memory in self.memories
                if memory["status"] == "active" and not self.labels.get(memory["id"])
            ]
        )[:limit]

    def get_memory_optional(self, memory_id: UUID) -> dict[str, object] | None:
        for memory in self.memories:
            if memory["id"] == memory_id:
                return memory
        return None

    def count_memory_revisions(self, memory_id: UUID) -> int:
        return len(self.revisions.get(memory_id, []))

    def list_memory_revisions(self, memory_id: UUID, *, limit: int | None = None) -> list[dict[str, object]]:
        revisions = self.revisions.get(memory_id, [])
        if limit is None:
            return revisions
        return revisions[:limit]

    def create_memory_review_label(
        self,
        *,
        memory_id: UUID,
        label: str,
        note: str | None,
    ) -> dict[str, object]:
        memory = self.get_memory_optional(memory_id)
        created = {
            "id": uuid4(),
            "user_id": uuid4() if memory is None else memory["user_id"],
            "memory_id": memory_id,
            "label": label,
            "note": note,
            "created_at": datetime(2026, 3, 11, 13, len(self.labels.get(memory_id, [])), tzinfo=UTC),
        }
        self.labels.setdefault(memory_id, []).append(created)
        return created

    def list_memory_review_labels(self, memory_id: UUID) -> list[dict[str, object]]:
        return list(self.labels.get(memory_id, []))

    def list_memory_review_label_counts(self, memory_id: UUID) -> list[dict[str, object]]:
        counts: dict[str, int] = {}
        for label in self.labels.get(memory_id, []):
            label_name = label["label"]
            counts[label_name] = counts.get(label_name, 0) + 1
        return [{"label": label, "count": count} for label, count in sorted(counts.items())]

    def count_labeled_memories(self) -> int:
        return len([memory for memory in self.memories if self.labels.get(memory["id"])])

    def count_unlabeled_memories(self) -> int:
        return len([memory for memory in self.memories if not self.labels.get(memory["id"])])

    def list_all_memory_review_label_counts(self) -> list[dict[str, object]]:
        counts: dict[str, int] = {}
        for labels in self.labels.values():
            for label in labels:
                label_name = label["label"]
                counts[label_name] = counts.get(label_name, 0) + 1
        return [{"label": label, "count": count} for label, count in sorted(counts.items())]

    def _filtered_memories(self, status: str | None) -> list[dict[str, object]]:
        if status is None:
            return list(self.memories)
        return [memory for memory in self.memories if memory["status"] == status]

    def _review_sorted_memories(self, memories: list[dict[str, object]]) -> list[dict[str, object]]:
        return sorted(
            memories,
            key=lambda memory: (memory["updated_at"], memory["created_at"], memory["id"]),
            reverse=True,
        )


def test_list_memory_review_records_returns_summary_and_stable_shape() -> None:
    store = MemoryReviewStoreStub()
    base_time = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    deleted_time = base_time + timedelta(minutes=1)
    active_time = base_time + timedelta(minutes=2)
    deleted_id = uuid4()
    active_id = uuid4()
    store.memories = [
        {
            "id": active_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-2"],
            "created_at": base_time,
            "updated_at": active_time,
            "deleted_at": None,
        },
        {
            "id": deleted_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.tea",
            "value": {"likes": "green"},
            "status": "deleted",
            "source_event_ids": ["event-1"],
            "created_at": base_time,
            "updated_at": deleted_time,
            "deleted_at": deleted_time,
        },
    ]

    payload = list_memory_review_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        status="all",
        limit=1,
    )

    assert payload == {
        "items": [
            {
                "id": str(active_id),
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-2"],
                "created_at": "2026-03-11T12:00:00+00:00",
                "updated_at": "2026-03-11T12:02:00+00:00",
                "deleted_at": None,
            }
        ],
        "summary": {
            "status": "all",
            "limit": 1,
            "returned_count": 1,
            "total_count": 2,
            "has_more": True,
            "order": ["updated_at_desc", "created_at_desc", "id_desc"],
        },
    }


def test_get_memory_review_record_raises_not_found_for_inaccessible_memory() -> None:
    store = MemoryReviewStoreStub()

    with pytest.raises(MemoryReviewNotFoundError, match="was not found"):
        get_memory_review_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            memory_id=uuid4(),
        )


def test_list_memory_review_queue_records_returns_only_active_unlabeled_memories_in_stable_order() -> None:
    store = MemoryReviewStoreStub()
    base_time = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    deleted_id = uuid4()
    labeled_id = uuid4()
    newest_unlabeled_id = uuid4()
    older_unlabeled_id = uuid4()
    store.memories = [
        {
            "id": newest_unlabeled_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-4"],
            "created_at": base_time + timedelta(minutes=3),
            "updated_at": base_time + timedelta(minutes=6),
            "deleted_at": None,
        },
        {
            "id": labeled_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.snack",
            "value": {"likes": "chips"},
            "status": "active",
            "source_event_ids": ["event-3"],
            "created_at": base_time + timedelta(minutes=2),
            "updated_at": base_time + timedelta(minutes=5),
            "deleted_at": None,
        },
        {
            "id": older_unlabeled_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.book",
            "value": {"genre": "science fiction"},
            "status": "active",
            "source_event_ids": ["event-2"],
            "created_at": base_time + timedelta(minutes=1),
            "updated_at": base_time + timedelta(minutes=4),
            "deleted_at": None,
        },
        {
            "id": deleted_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.tea",
            "value": {"likes": "green"},
            "status": "deleted",
            "source_event_ids": ["event-1"],
            "created_at": base_time,
            "updated_at": base_time + timedelta(minutes=7),
            "deleted_at": base_time + timedelta(minutes=7),
        },
    ]
    store.labels[labeled_id] = [
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "memory_id": labeled_id,
            "label": "correct",
            "note": "Already reviewed.",
            "created_at": base_time + timedelta(minutes=8),
        }
    ]

    payload = list_memory_review_queue_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        limit=2,
    )

    assert payload == {
        "items": [
            {
                "id": str(newest_unlabeled_id),
                "memory_key": "user.preference.coffee",
                "value": {"likes": "oat milk"},
                "status": "active",
                "source_event_ids": ["event-4"],
                "created_at": "2026-03-11T12:03:00+00:00",
                "updated_at": "2026-03-11T12:06:00+00:00",
            },
            {
                "id": str(older_unlabeled_id),
                "memory_key": "user.preference.book",
                "value": {"genre": "science fiction"},
                "status": "active",
                "source_event_ids": ["event-2"],
                "created_at": "2026-03-11T12:01:00+00:00",
                "updated_at": "2026-03-11T12:04:00+00:00",
            },
        ],
        "summary": {
            "memory_status": "active",
            "review_state": "unlabeled",
            "limit": 2,
            "returned_count": 2,
            "total_count": 2,
            "has_more": False,
            "order": ["updated_at_desc", "created_at_desc", "id_desc"],
        },
    }


def test_list_memory_revision_review_records_returns_deterministic_revision_order() -> None:
    store = MemoryReviewStoreStub()
    memory_id = uuid4()
    base_time = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    store.memories = [
        {
            "id": memory_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-2"],
            "created_at": base_time,
            "updated_at": base_time + timedelta(minutes=2),
            "deleted_at": None,
        }
    ]
    store.revisions[memory_id] = [
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "memory_id": memory_id,
            "sequence_no": 1,
            "action": "ADD",
            "memory_key": "user.preference.coffee",
            "previous_value": None,
            "new_value": {"likes": "black"},
            "source_event_ids": ["event-1"],
            "candidate": {"memory_key": "user.preference.coffee"},
            "created_at": base_time,
        },
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "memory_id": memory_id,
            "sequence_no": 2,
            "action": "UPDATE",
            "memory_key": "user.preference.coffee",
            "previous_value": {"likes": "black"},
            "new_value": {"likes": "oat milk"},
            "source_event_ids": ["event-2"],
            "candidate": {"memory_key": "user.preference.coffee"},
            "created_at": base_time + timedelta(minutes=1),
        },
    ]

    payload = list_memory_revision_review_records(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        memory_id=memory_id,
        limit=10,
    )

    assert payload == {
        "items": [
            {
                "id": str(store.revisions[memory_id][0]["id"]),
                "memory_id": str(memory_id),
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": "user.preference.coffee",
                "previous_value": None,
                "new_value": {"likes": "black"},
                "source_event_ids": ["event-1"],
                "created_at": "2026-03-11T12:00:00+00:00",
            },
            {
                "id": str(store.revisions[memory_id][1]["id"]),
                "memory_id": str(memory_id),
                "sequence_no": 2,
                "action": "UPDATE",
                "memory_key": "user.preference.coffee",
                "previous_value": {"likes": "black"},
                "new_value": {"likes": "oat milk"},
                "source_event_ids": ["event-2"],
                "created_at": "2026-03-11T12:01:00+00:00",
            },
        ],
        "summary": {
            "memory_id": str(memory_id),
            "limit": 10,
            "returned_count": 2,
            "total_count": 2,
            "has_more": False,
            "order": ["sequence_no_asc"],
        },
    }


def test_create_memory_review_label_record_returns_created_label_and_summary_counts() -> None:
    store = MemoryReviewStoreStub()
    memory_id = uuid4()
    reviewer_user_id = uuid4()
    base_time = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    store.memories = [
        {
            "id": memory_id,
            "user_id": reviewer_user_id,
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-2"],
            "created_at": base_time,
            "updated_at": base_time,
            "deleted_at": None,
        }
    ]
    store.labels[memory_id] = [
        {
            "id": uuid4(),
            "user_id": reviewer_user_id,
            "memory_id": memory_id,
            "label": "correct",
            "note": "Matches the latest cited event.",
            "created_at": datetime(2026, 3, 11, 12, 30, tzinfo=UTC),
        }
    ]

    payload = create_memory_review_label_record(
        store,  # type: ignore[arg-type]
        user_id=reviewer_user_id,
        memory_id=memory_id,
        label="outdated",
        note="Superseded by the newer milk preference.",
    )

    assert payload == {
        "label": {
            "id": payload["label"]["id"],
            "memory_id": str(memory_id),
            "reviewer_user_id": payload["label"]["reviewer_user_id"],
            "label": "outdated",
            "note": "Superseded by the newer milk preference.",
            "created_at": "2026-03-11T13:01:00+00:00",
        },
        "summary": {
            "memory_id": str(memory_id),
            "total_count": 2,
            "counts_by_label": {
                "correct": 1,
                "incorrect": 0,
                "outdated": 1,
                "insufficient_evidence": 0,
            },
            "order": ["created_at_asc", "id_asc"],
        },
    }


def test_create_memory_review_label_record_raises_not_found_for_inaccessible_memory() -> None:
    store = MemoryReviewStoreStub()

    with pytest.raises(MemoryReviewNotFoundError, match="was not found"):
        create_memory_review_label_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            memory_id=uuid4(),
            label="correct",
            note=None,
        )


def test_list_memory_review_label_records_returns_deterministic_order_and_zero_filled_counts() -> None:
    store = MemoryReviewStoreStub()
    memory_id = uuid4()
    reviewer_user_id = uuid4()
    base_time = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    store.memories = [
        {
            "id": memory_id,
            "user_id": reviewer_user_id,
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-2"],
            "created_at": base_time,
            "updated_at": base_time,
            "deleted_at": None,
        }
    ]
    store.labels[memory_id] = [
        {
            "id": uuid4(),
            "user_id": reviewer_user_id,
            "memory_id": memory_id,
            "label": "incorrect",
            "note": "The source event only mentions tea.",
            "created_at": datetime(2026, 3, 11, 12, 15, tzinfo=UTC),
        },
        {
            "id": uuid4(),
            "user_id": reviewer_user_id,
            "memory_id": memory_id,
            "label": "insufficient_evidence",
            "note": None,
            "created_at": datetime(2026, 3, 11, 12, 16, tzinfo=UTC),
        },
    ]

    payload = list_memory_review_label_records(
        store,  # type: ignore[arg-type]
        user_id=reviewer_user_id,
        memory_id=memory_id,
    )

    assert payload == {
        "items": [
            {
                "id": str(store.labels[memory_id][0]["id"]),
                "memory_id": str(memory_id),
                "reviewer_user_id": str(reviewer_user_id),
                "label": "incorrect",
                "note": "The source event only mentions tea.",
                "created_at": "2026-03-11T12:15:00+00:00",
            },
            {
                "id": str(store.labels[memory_id][1]["id"]),
                "memory_id": str(memory_id),
                "reviewer_user_id": str(reviewer_user_id),
                "label": "insufficient_evidence",
                "note": None,
                "created_at": "2026-03-11T12:16:00+00:00",
            },
        ],
        "summary": {
            "memory_id": str(memory_id),
            "total_count": 2,
            "counts_by_label": {
                "correct": 0,
                "incorrect": 1,
                "outdated": 0,
                "insufficient_evidence": 1,
            },
            "order": ["created_at_asc", "id_asc"],
        },
    }


def test_get_memory_evaluation_summary_returns_explicit_consistent_counts() -> None:
    store = MemoryReviewStoreStub()
    base_time = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
    active_labeled_id = uuid4()
    active_unlabeled_id = uuid4()
    deleted_labeled_id = uuid4()
    deleted_unlabeled_id = uuid4()
    store.memories = [
        {
            "id": active_labeled_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.coffee",
            "value": {"likes": "oat milk"},
            "status": "active",
            "source_event_ids": ["event-1"],
            "created_at": base_time,
            "updated_at": base_time,
            "deleted_at": None,
        },
        {
            "id": active_unlabeled_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.book",
            "value": {"genre": "science fiction"},
            "status": "active",
            "source_event_ids": ["event-2"],
            "created_at": base_time + timedelta(minutes=1),
            "updated_at": base_time + timedelta(minutes=1),
            "deleted_at": None,
        },
        {
            "id": deleted_labeled_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.snack",
            "value": {"likes": "chips"},
            "status": "deleted",
            "source_event_ids": ["event-3"],
            "created_at": base_time + timedelta(minutes=2),
            "updated_at": base_time + timedelta(minutes=2),
            "deleted_at": base_time + timedelta(minutes=2),
        },
        {
            "id": deleted_unlabeled_id,
            "user_id": uuid4(),
            "memory_key": "user.preference.tea",
            "value": {"likes": "green"},
            "status": "deleted",
            "source_event_ids": ["event-4"],
            "created_at": base_time + timedelta(minutes=3),
            "updated_at": base_time + timedelta(minutes=3),
            "deleted_at": base_time + timedelta(minutes=3),
        },
    ]
    store.labels[active_labeled_id] = [
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "memory_id": active_labeled_id,
            "label": "correct",
            "note": "Looks right.",
            "created_at": base_time + timedelta(minutes=4),
        },
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "memory_id": active_labeled_id,
            "label": "insufficient_evidence",
            "note": "Needs another source.",
            "created_at": base_time + timedelta(minutes=5),
        },
    ]
    store.labels[deleted_labeled_id] = [
        {
            "id": uuid4(),
            "user_id": uuid4(),
            "memory_id": deleted_labeled_id,
            "label": "outdated",
            "note": None,
            "created_at": base_time + timedelta(minutes=6),
        }
    ]

    payload = get_memory_evaluation_summary(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
    )

    assert payload == {
        "summary": {
            "total_memory_count": 4,
            "active_memory_count": 2,
            "deleted_memory_count": 2,
            "labeled_memory_count": 2,
            "unlabeled_memory_count": 2,
            "total_label_row_count": 3,
            "label_row_counts_by_value": {
                "correct": 1,
                "incorrect": 0,
                "outdated": 1,
                "insufficient_evidence": 1,
            },
            "label_value_order": [
                "correct",
                "incorrect",
                "outdated",
                "insufficient_evidence",
            ],
        }
    }
