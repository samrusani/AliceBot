from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Callable
from uuid import UUID

from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.continuity_review import apply_continuity_correction
from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.contracts import (
    RETRIEVAL_EVALUATION_FIXTURE_ORDER,
    RETRIEVAL_EVALUATION_RESULT_ORDER,
    ContinuityCorrectionInput,
    ContinuityRecallQueryInput,
    ContinuityResumptionBriefRequestInput,
    RetrievalEvaluationStatus,
    RetrievalEvaluationFixtureResult,
    RetrievalEvaluationResponse,
    RetrievalEvaluationSummary,
)
from alicebot_api.semantic_retrieval import calculate_mean_precision, calculate_precision_at_k
from alicebot_api.store import (
    ContinuityRecallCandidateRow,
    ContinuityStore,
    EntityEdgeRow,
    EntityRow,
    JsonObject,
)

RETRIEVAL_EVALUATION_PRECISION_TARGET = 0.8


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationFixture:
    fixture_id: str
    title: str
    request: ContinuityRecallQueryInput
    candidates: tuple[ContinuityRecallCandidateRow, ...]
    expected_relevant_ids: tuple[str, ...]
    entities: tuple[EntityRow, ...] = ()
    entity_edges: tuple[EntityEdgeRow, ...] = ()
    top_k: int = 1


class _FixtureStore:
    def __init__(
        self,
        rows: tuple[ContinuityRecallCandidateRow, ...],
        *,
        entities: tuple[EntityRow, ...] = (),
        entity_edges: tuple[EntityEdgeRow, ...] = (),
    ) -> None:
        self._rows = rows
        self._entities = entities
        self._entity_edges = entity_edges

    def list_continuity_recall_candidates(self) -> list[ContinuityRecallCandidateRow]:
        return list(self._rows)

    def list_entities(self) -> list[EntityRow]:
        return list(self._entities)

    def list_entity_edges_for_entities(self, entity_ids: list[UUID]) -> list[EntityEdgeRow]:
        requested = set(entity_ids)
        return [
            edge
            for edge in self._entity_edges
            if edge["from_entity_id"] in requested or edge["to_entity_id"] in requested
        ]


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


def _fixture_entity(
    *,
    entity_id: str,
    entity_type: str,
    name: str,
) -> EntityRow:
    return {
        "id": UUID(entity_id),
        "user_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "entity_type": entity_type,
        "name": name,
        "source_memory_ids": ["fixture-memory"],
        "created_at": datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
    }


def _fixture_entity_edge(
    *,
    edge_id: str,
    from_entity_id: str,
    to_entity_id: str,
    relationship_type: str,
) -> EntityEdgeRow:
    return {
        "id": UUID(edge_id),
        "user_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "from_entity_id": UUID(from_entity_id),
        "to_entity_id": UUID(to_entity_id),
        "relationship_type": relationship_type,
        "valid_from": None,
        "valid_to": None,
        "source_memory_ids": ["fixture-memory"],
        "created_at": datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
    }


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
        RetrievalEvaluationFixture(
            fixture_id="semantic_similarity_recovers_non_exact_query",
            title="Semantic similarity recovers non-exact query wording without lexical matches",
            request=ContinuityRecallQueryInput(query="synchronize calendars", limit=5),
            candidates=(
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000031",
                    capture_event_id="10000000-0000-4000-8000-000000000031",
                    title="Decision: Sync calendar availability",
                    body={"decision_text": "sync calendar availability before send"},
                    provenance={
                        "project": "Project Orbit",
                        "source_event_ids": ["e-31"],
                        "confirmation_status": "confirmed",
                    },
                    confidence=0.84,
                    created_at=datetime(2026, 3, 30, 9, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 30, 9, 30, tzinfo=UTC),
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000032",
                    capture_event_id="10000000-0000-4000-8000-000000000032",
                    title="Decision: Archive sprint retro",
                    body={"decision_text": "archive retro notes after review"},
                    provenance={"project": "Project Orbit"},
                    confidence=0.99,
                    created_at=datetime(2026, 3, 30, 9, 5, tzinfo=UTC),
                ),
            ),
            expected_relevant_ids=("00000000-0000-4000-8000-000000000031",),
        ),
        RetrievalEvaluationFixture(
            fixture_id="entity_signal_reduces_cross_entity_noise",
            title="Entity matching downranks same-topic but wrong-entity candidates",
            request=ContinuityRecallQueryInput(query="alex dependency owner", limit=5),
            candidates=(
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000041",
                    capture_event_id="10000000-0000-4000-8000-000000000041",
                    title="Decision: Alex owns dependency follow-up",
                    body={"decision_text": "dependency owner follow-up is Alex"},
                    provenance={
                        "person": "Alex",
                        "project": "Project Atlas",
                        "source_event_ids": ["e-41"],
                        "confirmation_status": "confirmed",
                    },
                    confidence=0.64,
                    created_at=datetime(2026, 3, 27, 9, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 27, 9, 30, tzinfo=UTC),
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000042",
                    capture_event_id="10000000-0000-4000-8000-000000000042",
                    title="Decision: Dependency owner note",
                    body={"decision_text": "dependency owner follow-up is Taylor"},
                    provenance={
                        "person": "Taylor",
                        "project": "Project Atlas",
                        "source_event_ids": ["e-42"],
                        "confirmation_status": "confirmed",
                    },
                    confidence=0.99,
                    created_at=datetime(2026, 3, 27, 10, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 3, 27, 10, 5, tzinfo=UTC),
                ),
            ),
            expected_relevant_ids=("00000000-0000-4000-8000-000000000041",),
        ),
        RetrievalEvaluationFixture(
            fixture_id="temporal_trust_supersession_prefers_current_valid_truth",
            title="Current valid trusted facts outrank stale superseded alternatives",
            request=ContinuityRecallQueryInput(
                query="contract window",
                since=datetime(2026, 2, 1, 0, 0, tzinfo=UTC),
                until=datetime(2026, 4, 30, 23, 59, tzinfo=UTC),
                limit=5,
            ),
            candidates=(
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000051",
                    capture_event_id="10000000-0000-4000-8000-000000000051",
                    title="Decision: Contract window is April",
                    body={
                        "decision_text": "contract window is April and currently valid",
                        "valid_from": "2026-04-01T00:00:00+00:00",
                        "valid_to": "2026-04-30T23:59:00+00:00",
                    },
                    provenance={
                        "project": "Project Atlas",
                        "source_event_ids": ["e-51"],
                        "trust_class": "human_curated",
                    },
                    confidence=0.58,
                    created_at=datetime(2026, 3, 31, 12, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000052",
                    capture_event_id="10000000-0000-4000-8000-000000000052",
                    title="Decision: Contract window legacy note",
                    body={
                        "decision_text": "contract window from prior quarter",
                        "valid_from": "2026-01-01T00:00:00+00:00",
                        "valid_to": "2026-03-01T00:00:00+00:00",
                    },
                    provenance={
                        "project": "Project Atlas",
                        "source_event_ids": ["e-52"],
                        "confirmation_status": "confirmed",
                        "trust_class": "llm_single_source",
                    },
                    confidence=0.99,
                    status="superseded",
                    created_at=datetime(2026, 2, 15, 12, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 2, 15, 12, 30, tzinfo=UTC),
                    superseded_by_object_id="00000000-0000-4000-8000-000000000051",
                ),
            ),
            expected_relevant_ids=("00000000-0000-4000-8000-000000000051",),
        ),
        RetrievalEvaluationFixture(
            fixture_id="entity_edge_expansion_recovers_related_owner",
            title="Entity-edge expansion recovers the related owner when the query names only the project",
            request=ContinuityRecallQueryInput(
                query="Project Phoenix dependency owner",
                limit=5,
            ),
            candidates=(
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000061",
                    capture_event_id="10000000-0000-4000-8000-000000000061",
                    title="Decision: Alex owns dependency follow-up",
                    body={"decision_text": "dependency owner follow-up is Alex"},
                    provenance={
                        "person": "Alex",
                        "source_event_ids": ["e-61"],
                        "confirmation_status": "confirmed",
                    },
                    confidence=0.72,
                    created_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 4, 1, 9, 30, tzinfo=UTC),
                ),
                _candidate(
                    object_id="00000000-0000-4000-8000-000000000062",
                    capture_event_id="10000000-0000-4000-8000-000000000062",
                    title="Decision: Phoenix dependency note",
                    body={"decision_text": "dependency owner follow-up is Taylor"},
                    provenance={
                        "project": "Project Phoenix",
                        "person": "Taylor",
                        "source_event_ids": ["e-62"],
                        "confirmation_status": "confirmed",
                    },
                    confidence=0.95,
                    created_at=datetime(2026, 4, 1, 9, 5, tzinfo=UTC),
                    last_confirmed_at=datetime(2026, 4, 1, 9, 35, tzinfo=UTC),
                ),
            ),
            expected_relevant_ids=("00000000-0000-4000-8000-000000000061",),
            entities=(
                _fixture_entity(
                    entity_id="00000000-0000-4000-8000-100000000061",
                    entity_type="project",
                    name="Project Phoenix",
                ),
                _fixture_entity(
                    entity_id="00000000-0000-4000-8000-100000000062",
                    entity_type="person",
                    name="Alex",
                ),
            ),
            entity_edges=(
                _fixture_entity_edge(
                    edge_id="00000000-0000-4000-8000-200000000061",
                    from_entity_id="00000000-0000-4000-8000-100000000062",
                    to_entity_id="00000000-0000-4000-8000-100000000061",
                    relationship_type="owner_of",
                ),
            ),
        ),
    )


def _evaluate_fixture(
    fixture: RetrievalEvaluationFixture,
) -> tuple[RetrievalEvaluationFixtureResult, float, float]:
    payload = query_continuity_recall(
        _FixtureStore(
            fixture.candidates,
            entities=fixture.entities,
            entity_edges=fixture.entity_edges,
        ),  # type: ignore[arg-type]
        user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        request=fixture.request,
        apply_limit=False,
        ranking_strategy="hybrid_v2",
    )
    baseline_payload = query_continuity_recall(
        _FixtureStore(
            fixture.candidates,
            entities=fixture.entities,
            entity_edges=fixture.entity_edges,
        ),  # type: ignore[arg-type]
        user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        request=fixture.request,
        apply_limit=False,
        ranking_strategy="legacy_v1",
    )
    returned_ids = [item["id"] for item in payload["items"]]
    baseline_returned_ids = [item["id"] for item in baseline_payload["items"]]
    relevant_ids = set(fixture.expected_relevant_ids)
    precision_at_k = calculate_precision_at_k(
        returned_ids=returned_ids,
        relevant_ids=relevant_ids,
        top_k=fixture.top_k,
    )
    baseline_precision_at_k = calculate_precision_at_k(
        returned_ids=baseline_returned_ids,
        relevant_ids=relevant_ids,
        top_k=fixture.top_k,
    )
    evaluated_window = returned_ids[: fixture.top_k]
    baseline_evaluated_window = baseline_returned_ids[: fixture.top_k]
    hit_count = sum(1 for candidate_id in evaluated_window if candidate_id in relevant_ids)
    baseline_hit_count = sum(
        1 for candidate_id in baseline_evaluated_window if candidate_id in relevant_ids
    )
    top_result = payload["items"][0] if payload["items"] else None
    baseline_top_result = baseline_payload["items"][0] if baseline_payload["items"] else None
    result: RetrievalEvaluationFixtureResult = {
        "fixture_id": fixture.fixture_id,
        "title": fixture.title,
        "query": fixture.request.query or "",
        "top_k": fixture.top_k,
        "expected_relevant_ids": list(fixture.expected_relevant_ids),
        "baseline_returned_ids": baseline_returned_ids,
        "returned_ids": returned_ids,
        "hit_count": hit_count,
        "baseline_hit_count": baseline_hit_count,
        "baseline_precision_at_k": baseline_precision_at_k,
        "precision_at_k": precision_at_k,
        "precision_lift_at_k": precision_at_k - baseline_precision_at_k,
        "baseline_top_result_id": (
            None if baseline_top_result is None else baseline_top_result["id"]
        ),
        "top_result_id": None if top_result is None else top_result["id"],
        "baseline_top_result_ordering": (
            None if baseline_top_result is None else baseline_top_result["ordering"]
        ),
        "top_result_ordering": None if top_result is None else top_result["ordering"],
    }
    precision_at_1 = calculate_precision_at_k(
        returned_ids=returned_ids,
        relevant_ids=relevant_ids,
        top_k=1,
    )
    baseline_precision_at_1 = calculate_precision_at_k(
        returned_ids=baseline_returned_ids,
        relevant_ids=relevant_ids,
        top_k=1,
    )
    return result, precision_at_1, baseline_precision_at_1


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
    baseline_precision_values: list[float] = []
    precision_at_1_values: list[float] = []
    baseline_precision_at_1_values: list[float] = []
    precision_lift_values: list[float] = []

    for fixture in fixture_suite:
        result, precision_at_1, baseline_precision_at_1 = _evaluate_fixture(fixture)
        evaluated_results.append(result)
        precision_values.append(result["precision_at_k"])
        baseline_precision_values.append(result["baseline_precision_at_k"])
        precision_lift_values.append(result["precision_lift_at_k"])
        precision_at_1_values.append(precision_at_1)
        baseline_precision_at_1_values.append(baseline_precision_at_1)

    fixture_count = len(fixture_suite)
    baseline_precision_at_k_mean = calculate_mean_precision(baseline_precision_values)
    precision_at_k_mean = calculate_mean_precision(precision_values)
    precision_at_k_lift = calculate_mean_precision(precision_lift_values)
    baseline_precision_at_1_mean = calculate_mean_precision(baseline_precision_at_1_values)
    precision_at_1_mean = calculate_mean_precision(precision_at_1_values)
    passing_fixture_count = sum(
        1
        for result in evaluated_results
        if result["precision_at_k"] >= RETRIEVAL_EVALUATION_PRECISION_TARGET
    )
    baseline_passing_fixture_count = sum(
        1
        for result in evaluated_results
        if result["baseline_precision_at_k"] >= RETRIEVAL_EVALUATION_PRECISION_TARGET
    )
    status: RetrievalEvaluationStatus = (
        "pass"
        if (
            precision_at_k_mean >= RETRIEVAL_EVALUATION_PRECISION_TARGET
            and precision_at_k_lift > 0.0
        )
        else "fail"
    )
    summary: RetrievalEvaluationSummary = {
        "fixture_count": fixture_count,
        "evaluated_fixture_count": len(evaluated_results),
        "passing_fixture_count": passing_fixture_count,
        "baseline_passing_fixture_count": baseline_passing_fixture_count,
        "baseline_precision_at_k_mean": baseline_precision_at_k_mean,
        "precision_at_k_mean": precision_at_k_mean,
        "precision_at_k_lift": precision_at_k_lift,
        "baseline_precision_at_1_mean": baseline_precision_at_1_mean,
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


PHASE9_EVALUATION_SCHEMA_VERSION = "phase9_eval_v1"
PHASE9_EVALUATION_PASS_THRESHOLD = 1.0


@dataclass(frozen=True, slots=True)
class Phase9ImporterDefinition:
    importer_name: str
    source_kind: str
    source_path: Path
    project: str
    thread_id: UUID | None
    recall_query: str
    import_fn: Callable[[ContinuityStore, UUID, Path], JsonObject]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _public_source_path(source_path: Path) -> str:
    resolved = source_path.expanduser().resolve()
    repo_root = _repo_root()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return f"external/{resolved.name}"


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def calculate_phase9_metric_ratio(*, passed_count: int, total_count: int) -> float:
    if total_count <= 0:
        return 0.0
    return passed_count / total_count


def _build_phase9_importer_definitions(
    *,
    openclaw_source: str | Path | None,
    markdown_source: str | Path | None,
    chatgpt_source: str | Path | None,
) -> tuple[Phase9ImporterDefinition, ...]:
    from alicebot_api.chatgpt_import import import_chatgpt_source
    from alicebot_api.markdown_import import import_markdown_source
    from alicebot_api.openclaw_import import import_openclaw_source

    repo_root = _repo_root()
    resolved_openclaw = Path(openclaw_source) if openclaw_source is not None else (
        repo_root / "fixtures" / "openclaw" / "workspace_v1.json"
    )
    resolved_markdown = Path(markdown_source) if markdown_source is not None else (
        repo_root / "fixtures" / "importers" / "markdown" / "workspace_v1.md"
    )
    resolved_chatgpt = Path(chatgpt_source) if chatgpt_source is not None else (
        repo_root / "fixtures" / "importers" / "chatgpt" / "workspace_v1.json"
    )

    return (
        Phase9ImporterDefinition(
            importer_name="openclaw",
            source_kind="openclaw_import",
            source_path=resolved_openclaw,
            project="Alice Public Core",
            thread_id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
            recall_query="MCP tool surface",
            import_fn=lambda store, user_id, path: import_openclaw_source(
                store,
                user_id=user_id,
                source=path,
            ),
        ),
        Phase9ImporterDefinition(
            importer_name="markdown",
            source_kind="markdown_import",
            source_path=resolved_markdown,
            project="Markdown Import Project",
            thread_id=UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
            recall_query="markdown importer deterministic",
            import_fn=lambda store, user_id, path: import_markdown_source(
                store,
                user_id=user_id,
                source=path,
            ),
        ),
        Phase9ImporterDefinition(
            importer_name="chatgpt",
            source_kind="chatgpt_import",
            source_path=resolved_chatgpt,
            project="ChatGPT Import Project",
            thread_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            recall_query="ChatGPT import provenance explicit",
            import_fn=lambda store, user_id, path: import_chatgpt_source(
                store,
                user_id=user_id,
                source=path,
            ),
        ),
    )


def _run_phase9_importer_evidence(
    store: ContinuityStore,
    *,
    user_id: UUID,
    definitions: tuple[Phase9ImporterDefinition, ...],
) -> list[JsonObject]:
    evidence: list[JsonObject] = []
    for definition in definitions:
        first_run = definition.import_fn(store, user_id, definition.source_path)
        second_run = definition.import_fn(store, user_id, definition.source_path)

        import_success = (
            first_run.get("status") == "ok"
            and _as_int(first_run.get("imported_count")) > 0
        )
        duplicate_posture_ok = (
            second_run.get("status") == "noop"
            and _as_int(second_run.get("skipped_duplicates")) == _as_int(first_run.get("total_candidates"))
        )
        evidence.append(
            {
                "importer": definition.importer_name,
                "source_kind": definition.source_kind,
                "source_path": _public_source_path(definition.source_path),
                "first_run": first_run,
                "second_run": second_run,
                "import_success": import_success,
                "duplicate_posture_ok": duplicate_posture_ok,
            }
        )
    return evidence


def _run_phase9_recall_precision(
    store: ContinuityStore,
    *,
    user_id: UUID,
    definitions: tuple[Phase9ImporterDefinition, ...],
) -> tuple[list[JsonObject], float]:
    checks: list[JsonObject] = []
    hit_count = 0

    for definition in definitions:
        payload = query_continuity_recall(
            store,
            user_id=user_id,
            request=ContinuityRecallQueryInput(
                query=definition.recall_query,
                thread_id=definition.thread_id,
                project=definition.project,
                limit=5,
            ),
        )
        top_item = payload["items"][0] if payload["items"] else None
        top_source_kind = None
        if top_item is not None and isinstance(top_item.get("provenance"), dict):
            top_source_kind = top_item["provenance"].get("source_kind")

        hit = top_source_kind == definition.source_kind
        if hit:
            hit_count += 1

        checks.append(
            {
                "importer": definition.importer_name,
                "query": definition.recall_query,
                "expected_source_kind": definition.source_kind,
                "top_source_kind": top_source_kind,
                "returned_count": payload["summary"]["returned_count"],
                "hit": hit,
            }
        )

    precision = calculate_phase9_metric_ratio(
        passed_count=hit_count,
        total_count=len(definitions),
    )
    return checks, precision


def _run_phase9_resumption_usefulness(
    store: ContinuityStore,
    *,
    user_id: UUID,
    definitions: tuple[Phase9ImporterDefinition, ...],
) -> tuple[list[JsonObject], float]:
    checks: list[JsonObject] = []
    useful_count = 0

    for definition in definitions:
        payload = compile_continuity_resumption_brief(
            store,
            user_id=user_id,
            request=ContinuityResumptionBriefRequestInput(
                query=None,
                thread_id=definition.thread_id,
                project=definition.project,
                max_recent_changes=5,
                max_open_loops=5,
            ),
        )
        brief = payload["brief"]
        last_decision = brief["last_decision"]["item"]
        next_action = brief["next_action"]["item"]
        last_source_kind = (
            None
            if last_decision is None
            else last_decision["provenance"].get("source_kind")
        )
        next_source_kind = (
            None
            if next_action is None
            else next_action["provenance"].get("source_kind")
        )
        useful = (
            last_decision is not None
            and next_action is not None
            and last_source_kind == definition.source_kind
            and next_source_kind == definition.source_kind
        )
        if useful:
            useful_count += 1
        checks.append(
            {
                "importer": definition.importer_name,
                "expected_source_kind": definition.source_kind,
                "last_decision_source_kind": last_source_kind,
                "next_action_source_kind": next_source_kind,
                "useful": useful,
            }
        )

    usefulness_rate = calculate_phase9_metric_ratio(
        passed_count=useful_count,
        total_count=len(definitions),
    )
    return checks, usefulness_rate


def _run_phase9_correction_effectiveness(
    store: ContinuityStore,
    *,
    user_id: UUID,
    target_definition: Phase9ImporterDefinition,
) -> JsonObject:
    before = query_continuity_recall(
        store,
        user_id=user_id,
        request=ContinuityRecallQueryInput(
            query=target_definition.recall_query,
            thread_id=target_definition.thread_id,
            project=target_definition.project,
            limit=5,
        ),
    )
    if not before["items"]:
        return {
            "target_importer": target_definition.importer_name,
            "effective": False,
            "reason": "no_recall_items_before_correction",
        }

    before_top = before["items"][0]
    before_top_id = str(before_top["id"])
    before_provenance = before_top.get("provenance")
    replacement_provenance = (
        dict(before_provenance)
        if isinstance(before_provenance, dict)
        else {}
    )
    replacement_provenance["phase9_eval_correction"] = "supersede_verification"

    correction = apply_continuity_correction(
        store,
        user_id=user_id,
        continuity_object_id=UUID(before_top_id),
        request=ContinuityCorrectionInput(
            action="supersede",
            reason="phase9_eval_correction_effectiveness",
            replacement_title="Decision: Keep MCP tool surface narrow after correction verification.",
            replacement_body={
                "decision_text": "Keep MCP tool surface narrow after correction verification.",
            },
            replacement_provenance=replacement_provenance,
            replacement_confidence=0.99,
        ),
    )

    replacement_object = correction["replacement_object"]
    replacement_id = None if replacement_object is None else replacement_object["id"]

    after = query_continuity_recall(
        store,
        user_id=user_id,
        request=ContinuityRecallQueryInput(
            query=target_definition.recall_query,
            thread_id=target_definition.thread_id,
            project=target_definition.project,
            limit=5,
        ),
    )
    after_top_id = None if not after["items"] else str(after["items"][0]["id"])
    effective = (
        replacement_id is not None
        and after_top_id == replacement_id
        and after_top_id != before_top_id
    )

    return {
        "target_importer": target_definition.importer_name,
        "before_top_id": before_top_id,
        "replacement_id": replacement_id,
        "after_top_id": after_top_id,
        "effective": effective,
    }


def run_phase9_evaluation(
    store: ContinuityStore,
    *,
    user_id: UUID,
    openclaw_source: str | Path | None = None,
    markdown_source: str | Path | None = None,
    chatgpt_source: str | Path | None = None,
) -> JsonObject:
    definitions = _build_phase9_importer_definitions(
        openclaw_source=openclaw_source,
        markdown_source=markdown_source,
        chatgpt_source=chatgpt_source,
    )

    importer_runs = _run_phase9_importer_evidence(
        store,
        user_id=user_id,
        definitions=definitions,
    )
    recall_checks, recall_precision = _run_phase9_recall_precision(
        store,
        user_id=user_id,
        definitions=definitions,
    )
    resumption_checks, resumption_usefulness = _run_phase9_resumption_usefulness(
        store,
        user_id=user_id,
        definitions=definitions,
    )
    correction_check = _run_phase9_correction_effectiveness(
        store,
        user_id=user_id,
        target_definition=definitions[0],
    )

    importer_success_count = sum(1 for run in importer_runs if run["import_success"] is True)
    duplicate_posture_count = sum(1 for run in importer_runs if run["duplicate_posture_ok"] is True)
    importer_total = len(importer_runs)

    importer_success_rate = calculate_phase9_metric_ratio(
        passed_count=importer_success_count,
        total_count=importer_total,
    )
    duplicate_posture_rate = calculate_phase9_metric_ratio(
        passed_count=duplicate_posture_count,
        total_count=importer_total,
    )
    correction_effectiveness_rate = 1.0 if correction_check["effective"] is True else 0.0

    threshold = PHASE9_EVALUATION_PASS_THRESHOLD
    status = (
        "pass"
        if (
            importer_success_rate >= threshold
            and duplicate_posture_rate >= threshold
            and recall_precision >= threshold
            and resumption_usefulness >= threshold
            and correction_effectiveness_rate >= threshold
        )
        else "fail"
    )

    return {
        "schema_version": PHASE9_EVALUATION_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "status": status,
            "importer_count": importer_total,
            "importer_success_rate": importer_success_rate,
            "duplicate_posture_rate": duplicate_posture_rate,
            "recall_precision_at_1": recall_precision,
            "resumption_usefulness_rate": resumption_usefulness,
            "correction_effectiveness_rate": correction_effectiveness_rate,
            "pass_threshold": threshold,
        },
        "importer_runs": importer_runs,
        "recall_precision_checks": recall_checks,
        "resumption_usefulness_checks": resumption_checks,
        "correction_effectiveness": correction_check,
    }


def write_phase9_evaluation_report(
    *,
    report: JsonObject,
    report_path: str | Path,
) -> Path:
    output_path = Path(report_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path
