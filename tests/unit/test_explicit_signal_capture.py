from __future__ import annotations

from uuid import uuid4

import pytest

from alicebot_api.contracts import ExplicitSignalCaptureRequestInput
from alicebot_api.explicit_preferences import ExplicitPreferenceExtractionValidationError
from alicebot_api.explicit_signal_capture import (
    ExplicitSignalCaptureValidationError,
    extract_and_admit_explicit_signals,
)


def test_extract_and_admit_explicit_signals_runs_preferences_before_commitments(monkeypatch) -> None:
    source_event_id = uuid4()
    user_id = uuid4()
    call_order: list[str] = []

    def fake_extract_preferences(_store, *, user_id, request):
        call_order.append("preferences")
        assert request.source_event_id == source_event_id
        assert user_id
        return {
            "candidates": [],
            "admissions": [],
            "summary": {
                "source_event_id": str(source_event_id),
                "source_event_kind": "message.user",
                "candidate_count": 0,
                "admission_count": 0,
                "persisted_change_count": 0,
                "noop_count": 0,
            },
        }

    def fake_extract_commitments(_store, *, user_id, request):
        call_order.append("commitments")
        assert request.source_event_id == source_event_id
        assert user_id
        return {
            "candidates": [
                {
                    "memory_key": "user.commitment.submit_tax_forms",
                    "value": {
                        "kind": "explicit_commitment",
                        "text": "submit tax forms",
                    },
                    "source_event_ids": [str(source_event_id)],
                    "delete_requested": False,
                    "pattern": "remind_me_to",
                    "commitment_text": "submit tax forms",
                    "open_loop_title": "Remember to submit tax forms",
                }
            ],
            "admissions": [],
            "summary": {
                "source_event_id": str(source_event_id),
                "source_event_kind": "message.user",
                "candidate_count": 1,
                "admission_count": 0,
                "persisted_change_count": 0,
                "noop_count": 0,
                "open_loop_created_count": 0,
                "open_loop_noop_count": 0,
            },
        }

    monkeypatch.setattr(
        "alicebot_api.explicit_signal_capture.extract_and_admit_explicit_preferences",
        fake_extract_preferences,
    )
    monkeypatch.setattr(
        "alicebot_api.explicit_signal_capture.extract_and_admit_explicit_commitments",
        fake_extract_commitments,
    )

    payload = extract_and_admit_explicit_signals(
        object(),  # type: ignore[arg-type]
        user_id=user_id,
        request=ExplicitSignalCaptureRequestInput(source_event_id=source_event_id),
    )

    assert call_order == ["preferences", "commitments"]
    assert payload["summary"] == {
        "source_event_id": str(source_event_id),
        "source_event_kind": "message.user",
        "candidate_count": 1,
        "admission_count": 0,
        "persisted_change_count": 0,
        "noop_count": 0,
        "open_loop_created_count": 0,
        "open_loop_noop_count": 0,
        "preference_candidate_count": 0,
        "preference_admission_count": 0,
        "commitment_candidate_count": 1,
        "commitment_admission_count": 0,
    }


def test_extract_and_admit_explicit_signals_wraps_validation_error_from_pipeline(monkeypatch) -> None:
    source_event_id = uuid4()

    def fake_extract_preferences(_store, *, user_id, request):
        del user_id, request
        raise ExplicitPreferenceExtractionValidationError(
            "source_event_id must reference an existing message.user event owned by the user"
        )

    def fake_extract_commitments(_store, *, user_id, request):
        del user_id, request
        raise AssertionError("commitments pipeline should not run after preference validation failure")

    monkeypatch.setattr(
        "alicebot_api.explicit_signal_capture.extract_and_admit_explicit_preferences",
        fake_extract_preferences,
    )
    monkeypatch.setattr(
        "alicebot_api.explicit_signal_capture.extract_and_admit_explicit_commitments",
        fake_extract_commitments,
    )

    with pytest.raises(
        ExplicitSignalCaptureValidationError,
        match="source_event_id must reference an existing message.user event owned by the user",
    ):
        extract_and_admit_explicit_signals(
            object(),  # type: ignore[arg-type]
            user_id=uuid4(),
            request=ExplicitSignalCaptureRequestInput(source_event_id=source_event_id),
        )
