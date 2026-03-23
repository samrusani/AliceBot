from __future__ import annotations

from uuid import UUID

from alicebot_api.contracts import (
    ExplicitCommitmentExtractionRequestInput,
    ExplicitCommitmentExtractionResponse,
    ExplicitPreferenceExtractionRequestInput,
    ExplicitPreferenceExtractionResponse,
    ExplicitSignalCaptureRequestInput,
    ExplicitSignalCaptureResponse,
    ExplicitSignalCaptureSummary,
)
from alicebot_api.explicit_commitments import (
    ExplicitCommitmentExtractionValidationError,
    extract_and_admit_explicit_commitments,
)
from alicebot_api.explicit_preferences import (
    ExplicitPreferenceExtractionValidationError,
    extract_and_admit_explicit_preferences,
)
from alicebot_api.store import ContinuityStore


class ExplicitSignalCaptureValidationError(ValueError):
    """Raised when an explicit-signal capture request is invalid."""


def _build_summary(
    *,
    source_event_id: UUID,
    source_event_kind: str,
    preferences: ExplicitPreferenceExtractionResponse,
    commitments: ExplicitCommitmentExtractionResponse,
) -> ExplicitSignalCaptureSummary:
    preference_candidate_count = preferences["summary"]["candidate_count"]
    preference_admission_count = preferences["summary"]["admission_count"]
    preference_persisted_change_count = preferences["summary"]["persisted_change_count"]
    preference_noop_count = preferences["summary"]["noop_count"]

    commitment_candidate_count = commitments["summary"]["candidate_count"]
    commitment_admission_count = commitments["summary"]["admission_count"]
    commitment_persisted_change_count = commitments["summary"]["persisted_change_count"]
    commitment_noop_count = commitments["summary"]["noop_count"]
    open_loop_created_count = commitments["summary"]["open_loop_created_count"]
    open_loop_noop_count = commitments["summary"]["open_loop_noop_count"]

    return {
        "source_event_id": str(source_event_id),
        "source_event_kind": source_event_kind,
        "candidate_count": preference_candidate_count + commitment_candidate_count,
        "admission_count": preference_admission_count + commitment_admission_count,
        "persisted_change_count": preference_persisted_change_count + commitment_persisted_change_count,
        "noop_count": preference_noop_count + commitment_noop_count,
        "open_loop_created_count": open_loop_created_count,
        "open_loop_noop_count": open_loop_noop_count,
        "preference_candidate_count": preference_candidate_count,
        "preference_admission_count": preference_admission_count,
        "commitment_candidate_count": commitment_candidate_count,
        "commitment_admission_count": commitment_admission_count,
    }


def extract_and_admit_explicit_signals(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ExplicitSignalCaptureRequestInput,
) -> ExplicitSignalCaptureResponse:
    try:
        # Preserve explicit deterministic sequencing: preferences first, commitments second.
        preferences = extract_and_admit_explicit_preferences(
            store,
            user_id=user_id,
            request=ExplicitPreferenceExtractionRequestInput(
                source_event_id=request.source_event_id,
            ),
        )
        commitments = extract_and_admit_explicit_commitments(
            store,
            user_id=user_id,
            request=ExplicitCommitmentExtractionRequestInput(
                source_event_id=request.source_event_id,
            ),
        )
    except (
        ExplicitPreferenceExtractionValidationError,
        ExplicitCommitmentExtractionValidationError,
    ) as exc:
        raise ExplicitSignalCaptureValidationError(str(exc)) from exc

    return {
        "preferences": preferences,
        "commitments": commitments,
        "summary": _build_summary(
            source_event_id=request.source_event_id,
            source_event_kind=preferences["summary"]["source_event_kind"],
            preferences=preferences,
            commitments=commitments,
        ),
    }
