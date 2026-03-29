from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.contracts import (
    RETRIEVAL_EVALUATION_FIXTURE_ORDER,
    RETRIEVAL_EVALUATION_RESULT_ORDER,
    ContinuityRecallQueryInput,
    RetrievalEvaluationStatus,
    RetrievalEvaluationFixtureResult,
    RetrievalEvaluationResponse,
    RetrievalEvaluationSummary,
)
from alicebot_api.semantic_retrieval import calculate_mean_precision, calculate_precision_at_k
from alicebot_api.store import ContinuityRecallCandidateRow, ContinuityStore

RETRIEVAL_EVALUATION_PRECISION_TARGET = 0.8


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationFixture:
    fixture_id: str
    title: str
    request: ContinuityRecallQueryInput
    candidates: tuple[ContinuityRecallCandidateRow, ...]
    expected_relevant_ids: tuple[str, ...]
    top_k: int = 1


class _FixtureStore:
    def __init__(self, rows: tuple[ContinuityRecallCandidateRow, ...]) -> None:
        self._rows = rows

    def list_continuity_recall_candidates(self) -> list[ContinuityRecallCandidateRow]:
        return list(self._rows)


def _candidate(
    *,
    object_id: str,
    capture_event_id: str,
    title: str,
    body: dict[str, object],
    provenance: dict[str, object],
    confidence: float,
    status: str = "active",
    admission_posture: str = "DERIVED",
    created_at: datetime,
    last_confirmed_at: datetime | None = None,
    supersedes_object_id: str | None = None,
    superseded_by_object_id: str | None = None,
) -> ContinuityRecallCandidateRow:
    parsed_supersedes = None if supersedes_object_id is None else UUID(supersedes_object_id)
    parsed_superseded_by = None if superseded_by_object_id is None else UUID(superseded_by_object_id)
    row: ContinuityRecallCandidateRow = {
        "id": UUID(object_id),
        "user_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "capture_event_id": UUID(capture_event_id),
        "object_type": "Decision",
        "status": status,
        "title": title,
        "body": body,
        "provenance": provenance,
        "confidence": confidence,
        "last_confirmed_at": last_confirmed_at,
        "supersedes_object_id": parsed_supersedes,
        "superseded_by_object_id": parsed_superseded_by,
        "object_created_at": created_at,
        "object_updated_at": created_at,
        "admission_posture": admission_posture,
        "admission_reason": "retrieval_evaluation_fixture",
        "explicit_signal": None,
        "capture_created_at": created_at,
    }
    return row


def _fixture_suite() -> tuple[RetrievalEvaluationFixture, ...]:
    return (
        RetrievalEvaluationFixture(
            fixture_id="confirmed_fresh_truth_preferred",
            title="Confirmed fresher active truth outranks stale/superseded alternatives",
            request=ContinuityRecallQueryInput(query="rollout", limit=5),
            candidates=(
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000001",
                    capture_event_id="10000000-0000-4000-8000-000000000001",
                    title="Decision: Keep phased rollout",
                    body={"decision_text": "Keep phased rollout"},
                    provenance={
                        "project": "Project Phoenix",
                        "source_event_ids": ["e-1"],
                        "confirmation_status": "confirmed",
                    },
                    confidence=0.91,
                    created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 29, 10, 30, tzinfo=UTC),
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000002",
                    capture_event_id="10000000-0000-4000-8000-000000000002",
                    title="Decision: Prior rollout note",
                    body={"decision_text": "rollout from last month"},
                    provenance={"project": "Project Phoenix", "confirmation_status": "confirmed"},
                    confidence=0.99,
                    status="stale",
                    created_at=datetime(2026, 2, 20, 10, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 2, 21, 10, 0, tzinfo=UTC),
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000003",
                    capture_event_id="10000000-0000-4000-8000-000000000003",
                    title="Decision: Superseded rollout approach",
                    body={"decision_text": "rollout through legacy pipeline"},
                    provenance={"project": "Project Phoenix", "confirmation_status": "confirmed"},
                    confidence=1.0,
                    status="superseded",
                    created_at=datetime(2026, 1, 30, 9, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 1, 30, 9, 30, tzinfo=UTC),
                    superseded_by_object_id="00000000-0000-4000-8000-000000000001",
                ),
            ),
            expected_relevant_ids=("00000000-0000-4000-8000-000000000001",),
        ),
        RetrievalEvaluationFixture(
            fixture_id="provenance_breaks_tie",
            title="Provenance quality breaks ranking ties deterministically",
            request=ContinuityRecallQueryInput(query="pricing", limit=5),
            candidates=(
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000011",
                    capture_event_id="10000000-0000-4000-8000-000000000011",
                    title="Decision: Keep pricing guardrail",
                    body={"decision_text": "pricing guardrail for enterprise"},
                    provenance={
                        "thread_id": "thread-1",
                        "source_event_ids": ["e-11"],
                        "confirmation_status": "confirmed",
                    },
                    confidence=0.85,
                    created_at=datetime(2026, 3, 28, 10, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 28, 11, 0, tzinfo=UTC),
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000012",
                    capture_event_id="10000000-0000-4000-8000-000000000012",
                    title="Decision: Pricing note",
                    body={"decision_text": "pricing guardrail for enterprise"},
                    provenance={"confirmation_status": "confirmed"},
                    confidence=0.95,
                    created_at=datetime(2026, 3, 28, 10, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 28, 11, 0, tzinfo=UTC),
                ),
            ),
            expected_relevant_ids=("00000000-0000-4000-8000-000000000011",),
        ),
        RetrievalEvaluationFixture(
            fixture_id="supersession_chain_prefers_current_truth",
            title="Current active truth outranks superseded chain links",
            request=ContinuityRecallQueryInput(query="api timeout", limit=5),
            candidates=(
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000021",
                    capture_event_id="10000000-0000-4000-8000-000000000021",
                    title="Decision: API timeout is 30s",
                    body={"decision_text": "api timeout is 30 seconds"},
                    provenance={"source_event_ids": ["e-21"], "confirmation_status": "confirmed"},
                    confidence=0.88,
                    created_at=datetime(2026, 3, 29, 8, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 29, 8, 30, tzinfo=UTC),
                    supersedes_object_id="00000000-0000-4000-8000-000000000022",
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000022",
                    capture_event_id="10000000-0000-4000-8000-000000000022",
                    title="Decision: API timeout is 45s",
                    body={"decision_text": "api timeout is 45 seconds"},
                    provenance={"source_event_ids": ["e-22"], "confirmation_status": "confirmed"},
                    confidence=0.99,
                    status="superseded",
                    created_at=datetime(2026, 3, 20, 8, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 20, 8, 30, tzinfo=UTC),
                    superseded_by_object_id="00000000-0000-4000-8000-000000000021",
                ),
            ),
            expected_relevant_ids=("00000000-0000-4000-8000-000000000021",),
        ),
    )


def _evaluate_fixture(fixture: RetrievalEvaluationFixture) -> tuple[RetrievalEvaluationFixtureResult, float]:
    payload = query_continuity_recall(
        _FixtureStore(fixture.candidates),  # type: ignore[arg-type]
        user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        request=fixture.request,
        apply_limit=False,
    )
    returned_ids = [item["id"] for item in payload["items"]]
    relevant_ids = set(fixture.expected_relevant_ids)
    precision_at_k = calculate_precision_at_k(
        returned_ids=returned_ids,
        relevant_ids=relevant_ids,
        top_k=fixture.top_k,
    )
    evaluated_window = returned_ids[: fixture.top_k]
    hit_count = sum(1 for candidate_id in evaluated_window if candidate_id in relevant_ids)
    top_result = payload["items"][0] if payload["items"] else None
    result: RetrievalEvaluationFixtureResult = {
        "fixture_id": fixture.fixture_id,
        "title": fixture.title,
        "query": fixture.request.query or "",
        "top_k": fixture.top_k,
        "expected_relevant_ids": list(fixture.expected_relevant_ids),
        "returned_ids": returned_ids,
        "hit_count": hit_count,
        "precision_at_k": precision_at_k,
        "top_result_id": None if top_result is None else top_result["id"],
        "top_result_ordering": None if top_result is None else top_result["ordering"],
    }
    precision_at_1 = calculate_precision_at_k(
        returned_ids=returned_ids,
        relevant_ids=relevant_ids,
        top_k=1,
    )
    return result, precision_at_1


def get_retrieval_evaluation_summary(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> RetrievalEvaluationResponse:
    del store
    del user_id

    fixture_suite = _fixture_suite()
    evaluated_results: list[RetrievalEvaluationFixtureResult] = []
    precision_values: list[float] = []
    precision_at_1_values: list[float] = []

    for fixture in fixture_suite:
        result, precision_at_1 = _evaluate_fixture(fixture)
        evaluated_results.append(result)
        precision_values.append(result["precision_at_k"])
        precision_at_1_values.append(precision_at_1)

    fixture_count = len(fixture_suite)
    precision_at_k_mean = calculate_mean_precision(precision_values)
    precision_at_1_mean = calculate_mean_precision(precision_at_1_values)
    passing_fixture_count = sum(
        1
        for result in evaluated_results
        if result["precision_at_k"] >= RETRIEVAL_EVALUATION_PRECISION_TARGET
    )
    status: RetrievalEvaluationStatus = (
        "pass"
        if precision_at_k_mean >= RETRIEVAL_EVALUATION_PRECISION_TARGET
        else "fail"
    )
    summary: RetrievalEvaluationSummary = {
        "fixture_count": fixture_count,
        "evaluated_fixture_count": len(evaluated_results),
        "passing_fixture_count": passing_fixture_count,
        "precision_at_k_mean": precision_at_k_mean,
        "precision_at_1_mean": precision_at_1_mean,
        "precision_target": RETRIEVAL_EVALUATION_PRECISION_TARGET,
        "status": status,
        "fixture_order": list(RETRIEVAL_EVALUATION_FIXTURE_ORDER),
        "result_order": list(RETRIEVAL_EVALUATION_RESULT_ORDER),
    }
    return {
        "fixtures": evaluated_results,
        "summary": summary,
    }
