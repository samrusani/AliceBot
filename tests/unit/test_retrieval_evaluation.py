from __future__ import annotations

from uuid import UUID

from alicebot_api.retrieval_evaluation import (
    RETRIEVAL_EVALUATION_PRECISION_TARGET,
    get_retrieval_evaluation_summary,
)


class RetrievalEvaluationStoreStub:
    pass


def test_retrieval_evaluation_summary_is_deterministic_and_fixture_backed() -> None:
    payload_first = get_retrieval_evaluation_summary(
        RetrievalEvaluationStoreStub(),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    payload_second = get_retrieval_evaluation_summary(
        RetrievalEvaluationStoreStub(),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    assert payload_first == payload_second
    assert payload_first["summary"]["fixture_count"] == 6
    assert payload_first["summary"]["evaluated_fixture_count"] == 6
    assert payload_first["summary"]["precision_target"] == RETRIEVAL_EVALUATION_PRECISION_TARGET
    assert payload_first["summary"]["precision_at_k_mean"] >= RETRIEVAL_EVALUATION_PRECISION_TARGET
    assert payload_first["summary"]["precision_at_k_mean"] > payload_first["summary"]["baseline_precision_at_k_mean"]
    assert payload_first["summary"]["precision_at_k_lift"] > 0.0
    assert payload_first["summary"]["status"] == "pass"
    assert [fixture["fixture_id"] for fixture in payload_first["fixtures"]] == [
        "confirmed_fresh_truth_preferred",
        "provenance_breaks_tie",
        "supersession_chain_prefers_current_truth",
        "semantic_similarity_recovers_non_exact_query",
        "entity_signal_reduces_cross_entity_noise",
        "temporal_trust_supersession_prefers_current_valid_truth",
    ]
    assert all(fixture["precision_at_k"] >= fixture["baseline_precision_at_k"] for fixture in payload_first["fixtures"])
    assert payload_first["fixtures"][0]["top_result_ordering"] is not None
    assert payload_first["fixtures"][0]["top_result_ordering"]["freshness_posture"] == "fresh"
