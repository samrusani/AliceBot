from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from alicebot_api.continuity_capture import (
    ContinuityCaptureNotFoundError,
    ContinuityCaptureValidationError,
    capture_continuity_input,
    get_continuity_capture_detail,
    list_continuity_capture_inbox,
)
from alicebot_api.contracts import ContinuityCaptureCreateInput


class ContinuityCaptureStoreStub:
    def __init__(self) -> None:
        self.user_id = UUID("11111111-1111-4111-8111-111111111111")
        self.base_time = datetime(2026, 3, 29, 9, 30, tzinfo=UTC)
        self.capture_events: dict[UUID, dict[str, object]] = {}
        self.capture_event_order: list[UUID] = []
        self.objects_by_capture_event: dict[UUID, dict[str, object]] = {}

    def create_continuity_capture_event(
        self,
        *,
        raw_content: str,
        explicit_signal: str | None,
        admission_posture: str,
        admission_reason: str,
    ):
        capture_event_id = uuid4()
        row = {
            "id": capture_event_id,
            "user_id": self.user_id,
            "raw_content": raw_content,
            "explicit_signal": explicit_signal,
            "admission_posture": admission_posture,
            "admission_reason": admission_reason,
            "created_at": self.base_time,
        }
        self.capture_events[capture_event_id] = row
        self.capture_event_order.insert(0, capture_event_id)
        return row

    def get_continuity_capture_event_optional(self, capture_event_id: UUID):
        return self.capture_events.get(capture_event_id)

    def list_continuity_capture_events(self, *, limit: int):
        return [
            self.capture_events[capture_event_id]
            for capture_event_id in self.capture_event_order[:limit]
        ]

    def count_continuity_capture_events(self) -> int:
        return len(self.capture_events)

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
        is_preserved: bool = True,
        is_searchable: bool = True,
        is_promotable: bool = True,
    ):
        row = {
            "id": uuid4(),
            "user_id": self.user_id,
            "capture_event_id": capture_event_id,
            "object_type": object_type,
            "status": status,
            "is_preserved": is_preserved,
            "is_searchable": is_searchable,
            "is_promotable": is_promotable,
            "title": title,
            "body": body,
            "provenance": provenance,
            "confidence": confidence,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.objects_by_capture_event[capture_event_id] = row
        return row

    def get_continuity_object_by_capture_event_optional(self, capture_event_id: UUID):
        return self.objects_by_capture_event.get(capture_event_id)

    def list_continuity_objects_for_capture_events(self, capture_event_ids: list[UUID]):
        return [
            self.objects_by_capture_event[capture_event_id]
            for capture_event_id in capture_event_ids
            if capture_event_id in self.objects_by_capture_event
        ]


def test_capture_continuity_input_maps_explicit_signal_deterministically() -> None:
    store = ContinuityCaptureStoreStub()

    payload = capture_continuity_input(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ContinuityCaptureCreateInput(
            raw_content="Call supplier before noon",
            explicit_signal="task",
        ),
    )

    capture = payload["capture"]
    assert capture["capture_event"]["admission_posture"] == "DERIVED"
    assert capture["capture_event"]["admission_reason"] == "explicit_signal_task"
    assert capture["derived_object"] is not None
    assert capture["derived_object"]["object_type"] == "NextAction"
    assert capture["derived_object"]["body"]["action_text"] == "Call supplier before noon"
    assert capture["derived_object"]["provenance"]["capture_event_id"] == capture["capture_event"]["id"]


def test_capture_continuity_input_uses_high_confidence_prefix_when_signal_is_missing() -> None:
    store = ContinuityCaptureStoreStub()

    payload = capture_continuity_input(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ContinuityCaptureCreateInput(raw_content="Decision: ship conservative admission"),
    )

    assert payload["capture"]["capture_event"]["admission_posture"] == "DERIVED"
    assert payload["capture"]["capture_event"]["admission_reason"] == "high_confidence_prefix_decision"
    assert payload["capture"]["derived_object"]["object_type"] == "Decision"
    assert payload["capture"]["derived_object"]["body"]["decision_text"] == "ship conservative admission"
    assert payload["capture"]["derived_object"]["confidence"] == 0.95


def test_capture_continuity_input_defaults_to_triage_for_ambiguous_input() -> None:
    store = ContinuityCaptureStoreStub()

    payload = capture_continuity_input(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ContinuityCaptureCreateInput(raw_content="Need to think about this sometime"),
    )

    assert payload["capture"]["capture_event"] == {
        "id": payload["capture"]["capture_event"]["id"],
        "raw_content": "Need to think about this sometime",
        "explicit_signal": None,
        "admission_posture": "TRIAGE",
        "admission_reason": "ambiguous_capture_requires_triage",
        "created_at": "2026-03-29T09:30:00+00:00",
    }
    assert payload["capture"]["derived_object"] is None


def test_continuity_capture_list_and_detail_preserve_triage_visibility() -> None:
    store = ContinuityCaptureStoreStub()

    triage_payload = capture_continuity_input(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ContinuityCaptureCreateInput(raw_content="Uncertain note without prefix"),
    )
    derived_payload = capture_continuity_input(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=ContinuityCaptureCreateInput(raw_content="task: send invoice"),
    )

    inbox = list_continuity_capture_inbox(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        limit=20,
    )

    assert inbox["summary"] == {
        "limit": 20,
        "returned_count": 2,
        "total_count": 2,
        "derived_count": 1,
        "triage_count": 1,
        "order": ["created_at_desc", "id_desc"],
    }
    assert inbox["items"][0]["capture_event"]["id"] == derived_payload["capture"]["capture_event"]["id"]
    assert inbox["items"][1]["capture_event"]["id"] == triage_payload["capture"]["capture_event"]["id"]

    detail = get_continuity_capture_detail(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        capture_event_id=UUID(derived_payload["capture"]["capture_event"]["id"]),
    )
    assert detail["capture"]["derived_object"]["object_type"] == "NextAction"


def test_continuity_capture_validation_and_not_found_contracts() -> None:
    store = ContinuityCaptureStoreStub()

    with pytest.raises(ContinuityCaptureValidationError, match="raw_content must not be empty"):
        capture_continuity_input(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ContinuityCaptureCreateInput(raw_content="   "),
        )

    with pytest.raises(ContinuityCaptureValidationError, match="explicit_signal must be one of"):
        capture_continuity_input(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=ContinuityCaptureCreateInput(
                raw_content="Call supplier",
                explicit_signal="unknown_signal",  # type: ignore[arg-type]
            ),
        )

    with pytest.raises(
        ContinuityCaptureNotFoundError,
        match="continuity capture event .* was not found",
    ):
        get_continuity_capture_detail(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            capture_event_id=uuid4(),
        )
