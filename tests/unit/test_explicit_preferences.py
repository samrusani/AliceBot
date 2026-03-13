from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from alicebot_api.contracts import AdmissionDecisionOutput, ExplicitPreferenceExtractionRequestInput
from alicebot_api.explicit_preferences import (
    ExplicitPreferenceExtractionValidationError,
    _build_memory_key,
    extract_and_admit_explicit_preferences,
    extract_explicit_preference_candidates,
)


class ExplicitPreferenceStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
        self.events: dict[UUID, dict[str, object]] = {}

    def list_events_by_ids(self, event_ids: list[UUID]) -> list[dict[str, object]]:
        return [self.events[event_id] for event_id in event_ids if event_id in self.events]


def seed_event(
    store: ExplicitPreferenceStoreStub,
    *,
    kind: str = "message.user",
    text: str = "I like black coffee.",
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


def test_extract_explicit_preference_candidates_returns_supported_candidate_shape() -> None:
    event_id = UUID("11111111-1111-1111-1111-111111111111")
    memory_key = _build_memory_key("black coffee")

    payload = extract_explicit_preference_candidates(
        source_event_id=event_id,
        text="I like black coffee.",
    )

    assert payload == [
        {
            "memory_key": memory_key,
            "value": {
                "kind": "explicit_preference",
                "preference": "like",
                "text": "black coffee",
            },
            "source_event_ids": [str(event_id)],
            "delete_requested": False,
            "pattern": "i_like",
            "subject_text": "black coffee",
        }
    ]


def test_extract_explicit_preference_candidates_keeps_remember_pattern_deterministic() -> None:
    event_id = UUID("22222222-2222-2222-2222-222222222222")
    memory_key = _build_memory_key("oat milk")

    payload = extract_explicit_preference_candidates(
        source_event_id=event_id,
        text="  remember that   I prefer  oat milk!!  ",
    )

    assert payload == [
        {
            "memory_key": memory_key,
            "value": {
                "kind": "explicit_preference",
                "preference": "prefer",
                "text": "oat milk",
            },
            "source_event_ids": [str(event_id)],
            "delete_requested": False,
            "pattern": "remember_that_i_prefer",
            "subject_text": "oat milk",
        }
    ]


def test_extract_explicit_preference_candidates_returns_empty_for_unsupported_text() -> None:
    assert extract_explicit_preference_candidates(
        source_event_id=uuid4(),
        text="I had coffee yesterday.",
    ) == []


def test_extract_explicit_preference_candidates_rejects_clause_style_text() -> None:
    assert extract_explicit_preference_candidates(
        source_event_id=uuid4(),
        text="I prefer that we meet tomorrow.",
    ) == []


def test_build_memory_key_keeps_symbol_bearing_subjects_distinct() -> None:
    c_plus_plus_key = _build_memory_key("C++")
    c_hash_key = _build_memory_key("C#")

    assert c_plus_plus_key != c_hash_key
    assert c_plus_plus_key.startswith("user.preference.c__")
    assert c_hash_key.startswith("user.preference.c__")


def test_build_memory_key_is_case_insensitive_for_the_same_subject() -> None:
    assert _build_memory_key("Black Coffee") == _build_memory_key("black coffee")


def test_extract_and_admit_explicit_preferences_rejects_invalid_source_event() -> None:
    store = ExplicitPreferenceStoreStub()
    event_id = seed_event(store, kind="message.assistant", text="I like black coffee.")

    with pytest.raises(
        ExplicitPreferenceExtractionValidationError,
        match="source_event_id must reference an existing message.user event owned by the user",
    ):
        extract_and_admit_explicit_preferences(
            store,  # type: ignore[arg-type]
            user_id=uuid4(),
            request=ExplicitPreferenceExtractionRequestInput(source_event_id=event_id),
        )


def test_extract_and_admit_explicit_preferences_routes_candidate_through_memory_admission(
    monkeypatch,
) -> None:
    store = ExplicitPreferenceStoreStub()
    user_id = uuid4()
    event_id = seed_event(store, text="I don't like black coffee.")
    memory_key = _build_memory_key("black coffee")
    captured: dict[str, object] = {}

    def fake_admit_memory_candidate(store_arg, *, user_id, candidate):
        captured["store"] = store_arg
        captured["user_id"] = user_id
        captured["candidate"] = candidate
        return AdmissionDecisionOutput(
            action="ADD",
            reason="source_backed_add",
            memory={
                "id": "memory-123",
                "user_id": str(user_id),
                "memory_key": candidate.memory_key,
                "value": candidate.value,
                "status": "active",
                "source_event_ids": [str(event_id)],
                "created_at": "2026-03-12T09:00:00+00:00",
                "updated_at": "2026-03-12T09:00:00+00:00",
                "deleted_at": None,
            },
            revision={
                "id": "revision-123",
                "user_id": str(user_id),
                "memory_id": "memory-123",
                "sequence_no": 1,
                "action": "ADD",
                "memory_key": candidate.memory_key,
                "previous_value": None,
                "new_value": candidate.value,
                "source_event_ids": [str(event_id)],
                "candidate": candidate.as_payload(),
                "created_at": "2026-03-12T09:00:00+00:00",
            },
        )

    monkeypatch.setattr(
        "alicebot_api.explicit_preferences.admit_memory_candidate",
        fake_admit_memory_candidate,
    )

    payload = extract_and_admit_explicit_preferences(
        store,  # type: ignore[arg-type]
        user_id=user_id,
        request=ExplicitPreferenceExtractionRequestInput(source_event_id=event_id),
    )

    assert captured["store"] is store
    assert captured["user_id"] == user_id
    assert captured["candidate"].memory_key == memory_key
    assert captured["candidate"].value == {
        "kind": "explicit_preference",
        "preference": "dislike",
        "text": "black coffee",
    }
    assert payload == {
        "candidates": [
            {
                "memory_key": memory_key,
                "value": {
                    "kind": "explicit_preference",
                    "preference": "dislike",
                    "text": "black coffee",
                },
                "source_event_ids": [str(event_id)],
                "delete_requested": False,
                "pattern": "i_dont_like",
                "subject_text": "black coffee",
            }
        ],
        "admissions": [
            {
                "decision": "ADD",
                "reason": "source_backed_add",
                "memory": {
                    "id": "memory-123",
                    "user_id": str(user_id),
                    "memory_key": memory_key,
                    "value": {
                        "kind": "explicit_preference",
                        "preference": "dislike",
                        "text": "black coffee",
                    },
                    "status": "active",
                    "source_event_ids": [str(event_id)],
                    "created_at": "2026-03-12T09:00:00+00:00",
                    "updated_at": "2026-03-12T09:00:00+00:00",
                    "deleted_at": None,
                },
                "revision": {
                    "id": "revision-123",
                    "user_id": str(user_id),
                    "memory_id": "memory-123",
                    "sequence_no": 1,
                    "action": "ADD",
                    "memory_key": memory_key,
                    "previous_value": None,
                    "new_value": {
                        "kind": "explicit_preference",
                        "preference": "dislike",
                        "text": "black coffee",
                    },
                    "source_event_ids": [str(event_id)],
                    "candidate": {
                        "memory_key": memory_key,
                        "value": {
                            "kind": "explicit_preference",
                            "preference": "dislike",
                            "text": "black coffee",
                        },
                        "source_event_ids": [str(event_id)],
                        "delete_requested": False,
                    },
                    "created_at": "2026-03-12T09:00:00+00:00",
                },
            }
        ],
        "summary": {
            "source_event_id": str(event_id),
            "source_event_kind": "message.user",
            "candidate_count": 1,
            "admission_count": 1,
            "persisted_change_count": 1,
            "noop_count": 0,
        },
    }
