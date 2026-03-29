from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from alicebot_api.continuity_objects import (
    ContinuityObjectValidationError,
    create_continuity_object_record,
    get_continuity_object_for_capture_event,
    list_continuity_objects_for_capture_events,
)


class ContinuityObjectStoreStub:
    def __init__(self) -> None:
        self.created_payloads: list[dict[str, object]] = []
        self.rows_by_capture_event: dict[UUID, dict[str, object]] = {}
        self.base_time = datetime(2026, 3, 29, 9, 0, tzinfo=UTC)

    def create_continuity_object(
        self,
        *,
        capture_event_id: UUID,
        object_type: str,
        status: str,
        title: str,
        body,
        provenance,
        confidence: float,
    ):
        created = {
            "id": uuid4(),
            "user_id": uuid4(),
            "capture_event_id": capture_event_id,
            "object_type": object_type,
            "status": status,
            "title": title,
            "body": body,
            "provenance": provenance,
            "confidence": confidence,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.created_payloads.append(created)
        self.rows_by_capture_event[capture_event_id] = created
        return created

    def get_continuity_object_by_capture_event_optional(self, capture_event_id: UUID):
        return self.rows_by_capture_event.get(capture_event_id)

    def list_continuity_objects_for_capture_events(self, capture_event_ids: list[UUID]):
        return [
            self.rows_by_capture_event[capture_event_id]
            for capture_event_id in capture_event_ids
            if capture_event_id in self.rows_by_capture_event
        ]


def test_create_continuity_object_record_serializes_created_row() -> None:
    store = ContinuityObjectStoreStub()
    capture_event_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    user_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

    payload = create_continuity_object_record(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        capture_event_id=capture_event_id,
        object_type="Decision",
        title="Decision: Use bounded intake",
        body={"decision_text": "Use bounded intake"},
        provenance={"capture_event_id": str(capture_event_id)},
        confidence=1.0,
    )

    assert payload == {
        "id": payload["id"],
        "capture_event_id": str(capture_event_id),
        "object_type": "Decision",
        "status": "active",
        "title": "Decision: Use bounded intake",
        "body": {"decision_text": "Use bounded intake"},
        "provenance": {"capture_event_id": str(capture_event_id)},
        "confidence": 1.0,
        "created_at": "2026-03-29T09:00:00+00:00",
        "updated_at": "2026-03-29T09:00:00+00:00",
    }


def test_create_continuity_object_record_rejects_invalid_object_type() -> None:
    store = ContinuityObjectStoreStub()

    with pytest.raises(
        ContinuityObjectValidationError,
        match="object_type must be one of",
    ):
        create_continuity_object_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            capture_event_id=uuid4(),
            object_type="Task",
            title="Task: Call supplier",
            body={"action_text": "Call supplier"},
            provenance={"capture_event_id": "event-1"},
            confidence=1.0,
        )


def test_create_continuity_object_record_rejects_empty_title_and_invalid_confidence() -> None:
    store = ContinuityObjectStoreStub()

    with pytest.raises(ContinuityObjectValidationError, match="title must not be empty"):
        create_continuity_object_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            capture_event_id=uuid4(),
            object_type="Note",
            title="   ",
            body={"body": "note"},
            provenance={"capture_event_id": "event-1"},
            confidence=1.0,
        )

    with pytest.raises(
        ContinuityObjectValidationError,
        match="confidence must be between 0.0 and 1.0",
    ):
        create_continuity_object_record(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            capture_event_id=uuid4(),
            object_type="Note",
            title="Valid title",
            body={"body": "note"},
            provenance={"capture_event_id": "event-1"},
            confidence=1.01,
        )


def test_get_and_list_continuity_objects_for_capture_events_use_capture_event_scope() -> None:
    store = ContinuityObjectStoreStub()
    capture_event_id = uuid4()

    created = create_continuity_object_record(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        capture_event_id=capture_event_id,
        object_type="MemoryFact",
        title="Memory Fact: prefers tea",
        body={"fact_text": "prefers tea"},
        provenance={"capture_event_id": str(capture_event_id)},
        confidence=0.95,
    )

    fetched = get_continuity_object_for_capture_event(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        capture_event_id=capture_event_id,
    )
    missing = get_continuity_object_for_capture_event(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        capture_event_id=uuid4(),
    )
    listed = list_continuity_objects_for_capture_events(
        store,  # type: ignore[arg-type]
        user_id=uuid4(),
        capture_event_ids=[capture_event_id, uuid4()],
    )

    assert fetched == created
    assert missing is None
    assert listed == {
        str(capture_event_id): created,
    }
