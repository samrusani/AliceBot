from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import AdmissionDecisionOutput, ExplicitCommitmentExtractionRequestInput
from alicebot_api.explicit_commitments import (
    ExplicitCommitmentExtractionValidationError,
    _build_memory_key,
    extract_and_admit_explicit_commitments,
    extract_explicit_commitment_candidates,
)


class ExplicitCommitmentStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 23, 9, 0, tzinfo=UTC)
        self.events: dict[UUID, dict[str, object]] = {}
        self.open_loops: dict[UUID, dict[str, object]] = {}
        self.create_open_loop_calls = 0

    def list_events_by_ids(self, event_ids: list[UUID]) -> list[dict[str, object]]:
        return [self.events[event_id] for event_id in event_ids if event_id in self.events]

    def list_open_loops(self, *, status: str | None = None, limit: int | None = None) -> list[dict[str, object]]:
        items = list(self.open_loops.values())
        if status is not None:
            items = [item for item in items if item["status"] == status]
        if limit is not None:
            items = items[:limit]
        return items

    def create_open_loop(
        self,
        *,
        memory_id: UUID | None,
        title: str,
        status: str,
        opened_at: datetime | None,
        due_at: datetime | None,
        resolved_at: datetime | None,
        resolution_note: str | None,
    ) -> dict[str, object]:
        del opened_at, due_at, resolved_at

        self.create_open_loop_calls += 1
        open_loop_id = uuid4()
        created = {
            "id": open_loop_id,
            "memory_id": memory_id,
            "title": title,
            "status": status,
            "opened_at": self.base_time,
            "due_at": None,
            "resolved_at": None,
            "resolution_note": resolution_note,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.open_loops[open_loop_id] = created
        return created


def seed_event(
    store: ExplicitCommitmentStoreStub,
    *,
    kind: str = "message.user",
    text: str = "Remind me to submit tax forms.",
) -> UUID:
    event_id = uuid4()
    store.events[event_id] = {
        "id": event_id,
        "sequence_no": 1,
        "kind": kind,
        "payload": {"text": text},
        "created_at": store.base_time,
    }
    return event_id


def test_extract_explicit_commitment_candidates_returns_supported_candidate_shape() -> None:
    event_id = UUID("11111111-1111-1111-1111-111111111111")
    memory_key = _build_memory_key("submit tax forms")

    payload = extract_explicit_commitment_candidates(
        source_event_id=event_id,
        text="Remind me to submit tax forms.",
    )

    assert payload == [
        {
            "memory_key": memory_key,
            "value": {
                "kind": "explicit_commitment",
                "text": "submit tax forms",
            },
            "source_event_ids": [str(event_id)],
            "delete_requested": False,
            "pattern": "remind_me_to",
            "commitment_text": "submit tax forms",
            "open_loop_title": "Remember to submit tax forms",
        }
    ]


def test_extract_explicit_commitment_candidates_supports_dont_let_me_forget_pattern() -> None:
    event_id = UUID("22222222-2222-2222-2222-222222222222")

    payload = extract_explicit_commitment_candidates(
        source_event_id=event_id,
        text="Don't let me forget to call the clinic!",
    )

    assert payload[0]["pattern"] == "dont_let_me_forget_to"
    assert payload[0]["commitment_text"] == "call the clinic"


def test_extract_explicit_commitment_candidates_returns_empty_for_unsupported_text() -> None:
    assert extract_explicit_commitment_candidates(
        source_event_id=uuid4(),
        text="I had coffee yesterday.",
    ) == []


def test_extract_explicit_commitment_candidates_rejects_clause_style_text() -> None:
    assert extract_explicit_commitment_candidates(
        source_event_id=uuid4(),
        text="Remember to if we can reschedule.",
    ) == []


def test_build_memory_key_is_case_insensitive_for_the_same_commitment() -> None:
    assert _build_memory_key("Submit Tax Forms") == _build_memory_key("submit tax forms")


def test_extract_and_admit_explicit_commitments_rejects_invalid_source_event() -> None:
    store = ExplicitCommitmentStoreStub()
    event_id = seed_event(store, kind="message.assistant", text="Remind me to submit tax forms.")

    with pytest.raises(
        ExplicitCommitmentExtractionValidationError,
        match="source_event_id must reference an existing message.user event owned by the user",
    ):
        extract_and_admit_explicit_commitments(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=ExplicitCommitmentExtractionRequestInput(source_event_id=event_id),
        )


def test_extract_and_admit_explicit_commitments_routes_candidate_through_memory_admission_and_creates_open_loop(
    monkeypatch,
) -> None:
    store = ExplicitCommitmentStoreStub()
    user_id = uuid4()
    event_id = seed_event(store, text="I need to submit tax forms.")
    memory_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    memory_key = _build_memory_key("submit tax forms")
    captured: dict[str, object] = {}

    def fake_admit_memory_candidate(store_arg, *, user_id, candidate):
        captured["store"] = store_arg
        captured["user_id"] = user_id
        captured["candidate"] = candidate
        return AdmissionDecisionOutput(
            action="ADD",
            reason="source_backed_add",
            memory={
                "id": str(memory_id),
                "user_id": str(user_id),
                "memory_key": candidate.memory_key,
                "value": candidate.value,
                "status": "active",
                "source_event_ids": [str(event_id)],
                "memory_type": "commitment",
                "created_at": "2026-03-23T09:00:00+00:00",
                "updated_at": "2026-03-23T09:00:00+00:00",
                "deleted_at": None,
            },
            revision={
                "id": "revision-123",
                "user_id": str(user_id),
                "memory_id": str(memory_id),
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": candidate.memory_key,
                "previous_value": None,
                "new_value": candidate.value,
                "source_event_ids": [str(event_id)],
                "candidate": candidate.as_payload(),
                "created_at": "2026-03-23T09:00:00+00:00",
            },
        )

    monkeypatch.setattr(
        "alicebot_api.explicit_commitments.admit_memory_candidate",
        fake_admit_memory_candidate,
    )

    payload = extract_and_admit_explicit_commitments(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=ExplicitCommitmentExtractionRequestInput(source_event_id=event_id),
    )

    assert captured["store"] is store
    assert captured["user_id"] == user_id
    assert captured["candidate"].memory_key == memory_key
    assert captured["candidate"].memory_type == "commitment"
    assert payload["admissions"][0]["open_loop"]["decision"] == "CREATED"
    assert payload["admissions"][0]["open_loop"]["open_loop"]["memory_id"] == str(memory_id)
    assert payload["summary"] == {
        "source_event_id": str(event_id),
        "source_event_kind": "message.user",
        "candidate_count": 1,
        "admission_count": 1,
        "persisted_change_count": 1,
        "noop_count": 0,
        "open_loop_created_count": 1,
        "open_loop_noop_count": 0,
    }
    assert store.create_open_loop_calls == 1


def test_extract_and_admit_explicit_commitments_keeps_existing_active_open_loop_without_duplicate(
    monkeypatch,
) -> None:
    store = ExplicitCommitmentStoreStub()
    user_id = uuid4()
    event_id = seed_event(store, text="Remember to submit tax forms.")
    memory_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    existing_open_loop_id = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")

    store.open_loops[existing_open_loop_id] = {
        "id": existing_open_loop_id,
        "memory_id": memory_id,
        "title": "Remember to submit tax forms",
        "status": "open",
        "opened_at": store.base_time,
        "due_at": None,
        "resolved_at": None,
        "resolution_note": None,
        "created_at": store.base_time,
        "updated_at": store.base_time,
    }

    def fake_admit_memory_candidate(_store_arg, *, user_id, candidate):
        return AdmissionDecisionOutput(
            action="NOOP",
            reason="memory_unchanged",
            memory={
                "id": str(memory_id),
                "user_id": str(user_id),
                "memory_key": candidate.memory_key,
                "value": candidate.value,
                "status": "active",
                "source_event_ids": [str(event_id)],
                "memory_type": "commitment",
                "created_at": "2026-03-23T09:00:00+00:00",
                "updated_at": "2026-03-23T09:00:00+00:00",
                "deleted_at": None,
            },
            revision=None,
        )

    monkeypatch.setattr(
        "alicebot_api.explicit_commitments.admit_memory_candidate",
        fake_admit_memory_candidate,
    )

    payload = extract_and_admit_explicit_commitments(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=ExplicitCommitmentExtractionRequestInput(source_event_id=event_id),
    )

    assert payload["admissions"][0]["open_loop"]["decision"] == "NOOP_ACTIVE_EXISTS"
    assert payload["admissions"][0]["open_loop"]["open_loop"]["id"] == str(existing_open_loop_id)
    assert store.create_open_loop_calls == 0
