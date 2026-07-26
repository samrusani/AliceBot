from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from longmemeval import count_probe as count_probe_module
from longmemeval.count_probe import (
    DEFAULT_ANSWER_SUFFICIENCY_TARGET,
    EXIT_RUN_FAILURES,
    EXIT_OK,
    EXIT_STRATUM_FAILURES,
    DEFAULT_AUDIT_MANIFEST,
    DEFAULT_SLICE,
    STRATUM_CADENCE_ABSTENTION,
    STRATUM_CADENCE_ANSWERABLE,
    STRATUM_CANDIDATE_COUNT,
    STRATUM_NUMERIC_SAFE_NON_EMISSION,
    STRATUM_REJECTED_GATE_WIDENING,
    default_output_path,
    expected_audit_manifest,
    exit_code_for_summary,
    probe_row,
    probe_question,
    summarize_rows,
)
from longmemeval.dataset import LongMemEvalQuestion


_TEST_USER_ID = "count-probe-user"


def _question(
    question_id: str,
    question: str,
    answer: str = "3",
    *,
    answer_session_ids: tuple[str, ...] = ("session-1",),
) -> LongMemEvalQuestion:
    return LongMemEvalQuestion(
        question_id=question_id,
        question_type="multi-session",
        question=question,
        answer=answer,
        question_date="2025/01/01 (Wed) 00:00",
        haystack_session_ids=(),
        haystack_dates=(),
        haystack_sessions=(),
        answer_session_ids=answer_session_ids,
    )


def _candidate(count: int = 3) -> dict[str, object]:
    return {
        "count": count,
        "unit": "deduplicated_memory_candidate_groups",
        "basis": "bounded_scoped_fts_candidates",
        "query_basis": "context_pack_query",
        "matching_criteria": "searchable scoped memories matched by the reported FTS mode",
        "deduplication": "source_chunk_then_source_then_memory_id",
        "fts_source": "sqlite_fts",
        "rows_examined": count,
        "rollup_cards_excluded": 1,
        "candidate_cap": 96,
        "scope_filtered": False,
        "candidate_prefix_exhausted": True,
        "more_candidate_groups_may_exist": False,
        "is_answer": False,
        "supports_numeric_sum": False,
    }


def _count_card(count: int = 3) -> dict[str, object]:
    member_ids = [f"memory-{index}" for index in range(1, count + 1)]
    return {
        "id": "rollup-1",
        "title": f"Roll-up: bike service ({count} instances in total)",
        "canonical_text": f"bike service - {count} instances: receipts",
        "metadata_json": {
            "candidate_kind": "memory_rollup",
            "consolidation": {
                "proposal_kind": "rollup",
                "cluster_member_ids": member_ids,
                "accepted": {"reviewed": True},
                "rollup": {"topic_label": "bike service"},
            },
        },
        "value": {
            "rollup": {
                "topic_label": "bike service",
                "member_ids": member_ids,
                "member_count": count,
                "grouping_input_truncated": False,
                "grouping_input_total_exact": True,
                "grouping_input_count": count,
                "grouping_input_total": count,
                "instances_truncated": False,
            }
        },
    }


def _pack(
    *,
    candidate: dict[str, object] | None = None,
    selected_rollup: bool = False,
    aggregation: dict[str, object] | None = None,
) -> dict[str, object]:
    pack: dict[str, object] = {
        "relevant_memories": [],
        "trace": {"vector_stage": "disabled", "stages": {"coverage_mode": {}}},
    }
    if candidate is not None:
        pack["trace"]["stages"]["coverage_mode"]["candidate_instance_count"] = deepcopy(  # type: ignore[index]
            candidate
        )
    if selected_rollup:
        assert candidate is not None
        pack["relevant_memories"] = [_count_card(int(candidate["count"]))]
    if aggregation is not None:
        pack["aggregation"] = deepcopy(aggregation)
    return pack


def _occurrence_aggregation(
    count: int = 3,
    *,
    answer_kind: str = "exact",
    aggregation_basis: str = "event_instance",
    counted_members_by_unit: tuple[tuple[str, ...], ...] | None = None,
) -> dict[str, object]:
    if counted_members_by_unit is None:
        unit_ids = [f"occurrence-{index:02d}" for index in range(1, count + 1)]
        if aggregation_basis == "event_instance":
            counted_members_by_unit = tuple((f"{index:064x}",) for index in range(1, count + 1))
        else:
            counted_members_by_unit = tuple((f"object:v1:{index:064x}",) for index in range(1, count + 1))
    else:
        unit_ids = [f"occurrence-{index:02d}" for index in range(1, len(counted_members_by_unit) + 1)]
    normalized_members_by_unit = tuple(tuple(sorted(set(member_keys))) for member_keys in counted_members_by_unit)
    counted_member_keys = sorted(
        {member_key for member_keys in normalized_members_by_unit for member_key in member_keys}
    )
    assert len(counted_member_keys) == count
    if answer_kind == "exact":
        upper_bound: int | None = count
        coverage_fully_covered = True
        legacy_gap = False
        unresolved_count = 0
    elif answer_kind == "range":
        upper_bound = count + 2
        coverage_fully_covered = True
        legacy_gap = False
        unresolved_count = 2
    else:
        assert answer_kind == "at_least"
        upper_bound = None
        coverage_fully_covered = False
        legacy_gap = True
        unresolved_count = 0
    coverage: dict[str, object] = {
        "id": "coverage-1",
        "coverage_mode": ("forward_only" if answer_kind == "at_least" else "complete_history"),
        "coverage_started_at": "2024-01-01T00:00:00Z",
        "historical_review_status": ("not_reviewed" if answer_kind == "at_least" else "reviewed"),
        "complete_through": "2025-01-01T00:00:00Z",
        "review_version": 1,
        "reviewer_id": "reviewer-1",
        "review_reason": "Reviewed occurrence coverage.",
        "requested_start": None,
        "requested_end": "2025-01-01T00:00:00Z",
        "fully_covered": coverage_fully_covered,
        "legacy_gap": legacy_gap,
        "receipt_valid": True,
    }
    coverage["review_receipt_digest"] = hashlib.sha256(
        json.dumps(
            {
                "complete_through": coverage["complete_through"],
                "coverage_id": coverage["id"],
                "coverage_mode": coverage["coverage_mode"],
                "coverage_started_at": coverage["coverage_started_at"],
                "historical_review_status": coverage["historical_review_status"],
                "reason": coverage["review_reason"],
                "review_version": coverage["review_version"],
                "reviewer_id": coverage["reviewer_id"],
                "user_id": _TEST_USER_ID,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    provenance: list[dict[str, object]] = []
    for index, (unit_id, member_keys) in enumerate(
        zip(unit_ids, normalized_members_by_unit, strict=True),
        start=1,
    ):
        evidence_id = f"evidence-{index:02d}"
        evidence_key = f"evidence-key-{index:02d}"
        quote_sha256 = f"{index:064x}"
        unit_review_receipt_digest = f"{1000 + index:064x}"
        # Opaque producer-validated digest; the public projection intentionally
        # omits the immutable evidence facts needed to reconstruct it.
        reviewed_evidence_digest = f"{3000 + index:064x}"
        provenance.append(
            {
                "occurrence_unit_id": unit_id,
                "counted_member_keys": list(member_keys),
                "review_receipt_digest": unit_review_receipt_digest,
                "reviewed_evidence_digest": reviewed_evidence_digest,
                "reviewed_evidence_count": 1,
                "evidence": [
                    {
                        "evidence_id": evidence_id,
                        "evidence_key": evidence_key,
                        "evidence_role": "supports",
                        "memory_id": f"memory-{index:02d}",
                        "source_id": f"source-{index:02d}",
                        "source_chunk_id": f"chunk-{index:02d}",
                        "quote_sha256": quote_sha256,
                        "review_status": "accepted",
                        "review_receipt_digest": f"{2000 + index:064x}",
                        "unit_review_receipt_digest": unit_review_receipt_digest,
                    }
                ],
            }
        )
    aggregation: dict[str, object] = {
        "kind": "occurrence_count",
        "answer_kind": answer_kind,
        "exact": answer_kind == "exact",
        "lower_bound": count,
        "upper_bound": upper_bound,
        "unit": ("reviewed_occurrence_units" if aggregation_basis == "event_instance" else "reviewed_object_members"),
        "aggregation_basis": aggregation_basis,
        "counted_member_keys": counted_member_keys,
        "occurrence_unit_ids": unit_ids,
        "provenance": provenance,
        "accepted_units": {
            "matching": len(unit_ids),
            "disjoint_proven": 0,
            "relation_unknown": 0,
        },
        "coverage": coverage,
        "unresolved_claims": {
            "count": unresolved_count,
            "disjoint_proven": 0,
            "matching_or_unknown": unresolved_count,
            "saturated": False,
        },
        "saturated": False,
        "answer_sufficient": answer_kind == "exact",
    }
    if answer_kind == "exact":
        aggregation["count"] = count
    return aggregation


def _row(
    question: LongMemEvalQuestion,
    pack: dict[str, object],
    *,
    expected_user_id: str = _TEST_USER_ID,
) -> dict[str, object]:
    return probe_row(
        question,
        pack,
        expected_user_id=expected_user_id,
        reused_store=True,
        accept_rollups=False,
        ingest_seconds=None,
        retrieval_seconds=0.01,
    )


def _release_manifest_rows(*, sufficient: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cardinality_ids = sorted(count_probe_module._CARDINALITY_FREQUENCY_IDS)
    for index, question_id in enumerate(cardinality_ids):
        aggregation = _occurrence_aggregation() if index < sufficient else None
        rows.append(
            _row(
                _question(
                    question_id,
                    "How many times did I service my bike?",
                    "3",
                ),
                _pack(candidate=_candidate(), aggregation=aggregation),
            )
        )
    for question_id in sorted(count_probe_module._NUMERIC_SAFE_IDS):
        rows.append(
            _row(
                _question(question_id, "How many days did the trip last?"),
                _pack(),
            )
        )
    for question_id in sorted(count_probe_module._REJECTED_GATE_WIDENING_IDS):
        rows.append(
            _row(
                _question(
                    question_id,
                    "What is the total number of goals and assists I have?",
                ),
                _pack(),
            )
        )
    for question_id in sorted(count_probe_module._GATE_RECALL_ANSWERABLE_IDS):
        rows.append(
            _row(
                _question(
                    question_id,
                    "How often did I service my bike?",
                    "Three times a week",
                ),
                _pack(),
            )
        )
    for question_id in sorted(count_probe_module._GATE_RECALL_ABSTENTION_IDS):
        rows.append(
            _row(
                _question(
                    question_id,
                    "How often did I service my bike?",
                    "No evidence",
                ),
                _pack(),
            )
        )
    return rows


def test_probe_separates_trace_mechanism_from_reader_sufficiency() -> None:
    question = _question("00ca467f", "How many bike services did I record?")
    row = _row(question, _pack(candidate=_candidate()))

    assert row["hand_audited_stratum"] == STRATUM_CANDIDATE_COUNT
    assert row["trace_candidate_count_present"] is True
    assert row["trace_candidate_disclosure_is_non_oracle"] is True
    assert row["reader_aggregation_present"] is False
    assert row["mechanism_expectation_met"] is True
    assert row["answer_sufficiency"] == "trace_candidate_statistic_only_not_an_answer"


def test_probe_never_treats_selected_frequency_rollup_as_answer_sufficient() -> None:
    question = _question(
        "00ca467f",
        "How many times did I score goals?",
        # Each of the three member memories can say "twice"; member_count=3
        # therefore does not establish the six queried occurrences.
        "6",
    )
    row = _row(
        question,
        _pack(candidate=_candidate(), selected_rollup=True),
    )

    assert row["selected_count_bearing_rollups"] == [{"memory_id": "rollup-1", "member_count": 3}]
    assert row["reader_aggregation_present"] is False
    assert row["reader_aggregation_contract_valid"] is False
    assert row["reader_verified_occurrence_aggregation"] is None
    assert row["reader_exact_count_matches_dev_gold"] is None
    assert row["answer_sufficiency"] == "selected_unverified_count_rollup_not_an_answer"


def test_probe_rejects_fabricated_legacy_reader_aggregation_surface() -> None:
    question = _question("00ca467f", "How many times did I service my bike?")
    row = _row(
        question,
        _pack(
            candidate=_candidate(),
            aggregation={"verified_instance_count": 3},
        ),
    )

    assert row["reader_aggregation_present"] is True
    assert row["reader_aggregation_contract_valid"] is False
    assert row["reader_aggregation_contract_error"] == "kind"
    assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_accepts_only_exact_evidence_bearing_occurrence_answer() -> None:
    question = _question(
        "00ca467f",
        "How many times did I service my bike?",
        "3",
    )
    aggregation = _occurrence_aggregation()
    row = _row(
        question,
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is True
    assert row["reader_aggregation_contract_error"] is None
    assert row["reader_aggregation_answer_kind"] == "exact"
    assert row["reader_verified_occurrence_aggregation"] == aggregation
    assert row["reader_exact_count_matches_dev_gold"] is True
    assert row["answer_sufficiency"] == "verified_occurrence_aggregation_matches_dev_gold"


def test_probe_accepts_exact_with_signed_proven_disjoint_unresolved_claim() -> None:
    aggregation = _occurrence_aggregation()
    unresolved = aggregation["unresolved_claims"]
    assert isinstance(unresolved, dict)
    unresolved.update(
        {
            "count": 1,
            "disjoint_proven": 1,
            "matching_or_unknown": 0,
        }
    )

    row = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "3",
        ),
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is True
    assert row["reader_exact_count_matches_dev_gold"] is True
    assert row["answer_sufficiency"] == "verified_occurrence_aggregation_matches_dev_gold"


def test_probe_rejects_tampered_unresolved_claim_partition() -> None:
    missing_partition = _occurrence_aggregation()
    missing_partition_unresolved = missing_partition["unresolved_claims"]
    assert isinstance(missing_partition_unresolved, dict)
    del missing_partition_unresolved["disjoint_proven"]

    mismatched_sum = _occurrence_aggregation()
    mismatched_sum_unresolved = mismatched_sum["unresolved_claims"]
    assert isinstance(mismatched_sum_unresolved, dict)
    mismatched_sum_unresolved.update(
        {
            "count": 1,
            "disjoint_proven": 0,
            "matching_or_unknown": 0,
        }
    )

    negative_partition = _occurrence_aggregation()
    negative_partition_unresolved = negative_partition["unresolved_claims"]
    assert isinstance(negative_partition_unresolved, dict)
    negative_partition_unresolved.update(
        {
            "count": 0,
            "disjoint_proven": -1,
            "matching_or_unknown": 1,
        }
    )

    boolean_partition = _occurrence_aggregation()
    boolean_partition_unresolved = boolean_partition["unresolved_claims"]
    assert isinstance(boolean_partition_unresolved, dict)
    boolean_partition_unresolved["matching_or_unknown"] = False

    for aggregation in (
        missing_partition,
        mismatched_sum,
        negative_partition,
        boolean_partition,
    ):
        row = _row(
            _question(
                "00ca467f",
                "How many times did I service my bike?",
                "3",
            ),
            _pack(candidate=_candidate(), aggregation=aggregation),
        )

        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == "unresolved_claim_partition"
        assert row["reader_aggregation"] is None
        assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_tampered_accepted_unit_partition() -> None:
    missing_partition = _occurrence_aggregation()
    del missing_partition["accepted_units"]

    mismatched_matching = _occurrence_aggregation()
    mismatched_record = mismatched_matching["accepted_units"]
    assert isinstance(mismatched_record, dict)
    mismatched_record["matching"] = 2

    negative_partition = _occurrence_aggregation()
    negative_record = negative_partition["accepted_units"]
    assert isinstance(negative_record, dict)
    negative_record["relation_unknown"] = -1

    boolean_partition = _occurrence_aggregation()
    boolean_record = boolean_partition["accepted_units"]
    assert isinstance(boolean_record, dict)
    boolean_record["disjoint_proven"] = False

    for aggregation in (
        missing_partition,
        mismatched_matching,
        negative_partition,
        boolean_partition,
    ):
        row = _row(
            _question(
                "00ca467f",
                "How many times did I service my bike?",
                "3",
            ),
            _pack(candidate=_candidate(), aggregation=aggregation),
        )

        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == "accepted_unit_partition"
        assert row["reader_aggregation"] is None


def test_probe_accepts_object_member_count_larger_than_unit_count() -> None:
    aggregation = _occurrence_aggregation(
        3,
        aggregation_basis="object_member",
        counted_members_by_unit=(
            (f"object:v1:{'a' * 64}", f"object:v1:{'b' * 64}"),
            (f"object:v1:{'c' * 64}",),
        ),
    )
    row = _row(
        _question(
            "00ca467f",
            "How many albums did I buy?",
            "3",
        ),
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert len(aggregation["occurrence_unit_ids"]) == 2
    assert aggregation["unit"] == "reviewed_object_members"
    assert aggregation["counted_member_keys"] == [
        f"object:v1:{'a' * 64}",
        f"object:v1:{'b' * 64}",
        f"object:v1:{'c' * 64}",
    ]
    assert row["reader_aggregation_contract_valid"] is True
    assert row["reader_exact_count_matches_dev_gold"] is True
    assert row["answer_sufficiency"] == "verified_occurrence_aggregation_matches_dev_gold"


def test_probe_deduplicates_counted_members_across_unit_provenance() -> None:
    aggregation = _occurrence_aggregation(
        3,
        aggregation_basis="object_member",
        counted_members_by_unit=(
            (f"object:v1:{'a' * 64}", f"object:v1:{'b' * 64}"),
            (f"object:v1:{'b' * 64}", f"object:v1:{'c' * 64}"),
        ),
    )
    row = _row(
        _question(
            "00ca467f",
            "How many albums did I buy?",
            "3",
        ),
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    provenance = aggregation["provenance"]
    assert isinstance(provenance, list)
    assert sum(len(item["counted_member_keys"]) for item in provenance if isinstance(item, dict)) == 4
    assert len(aggregation["counted_member_keys"]) == 3
    assert aggregation["count"] == aggregation["lower_bound"] == 3
    assert row["reader_aggregation_contract_valid"] is True
    assert row["reader_exact_count_matches_dev_gold"] is True


def test_probe_rejects_global_member_projection_mismatch() -> None:
    aggregation = _occurrence_aggregation()
    counted_member_keys = aggregation["counted_member_keys"]
    assert isinstance(counted_member_keys, list)
    aggregation["counted_member_keys"] = sorted([*counted_member_keys[:-1], f"{999:064x}"])

    row = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "3",
        ),
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is False
    assert row["reader_aggregation_contract_error"] == "counted_member_key_union"
    assert row["reader_aggregation"] is None
    assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_two_event_members_projected_from_one_unit() -> None:
    aggregation = _occurrence_aggregation(1)
    provenance = aggregation["provenance"]
    assert isinstance(provenance, list)
    assert isinstance(provenance[0], dict)
    event_members = [f"{1:064x}", f"{2:064x}"]
    provenance[0]["counted_member_keys"] = event_members
    aggregation["counted_member_keys"] = event_members
    aggregation["lower_bound"] = 2
    aggregation["upper_bound"] = 2
    aggregation["count"] = 2

    row = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "2",
        ),
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is False
    assert row["reader_aggregation_contract_error"] == "event_instance_projection"
    assert row["reader_aggregation"] is None
    assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_accepts_signed_complete_history_exact_zero_for_both_projections() -> None:
    for aggregation_basis in ("event_instance", "object_member"):
        aggregation = _occurrence_aggregation(
            0,
            aggregation_basis=aggregation_basis,
        )
        row = _row(
            _question(
                "00ca467f",
                "How many times did I service my bike?",
                "0",
            ),
            _pack(candidate=_candidate(0), aggregation=aggregation),
        )

        assert aggregation["occurrence_unit_ids"] == []
        assert aggregation["counted_member_keys"] == []
        assert aggregation["provenance"] == []
        assert row["reader_aggregation_contract_valid"] is True
        assert row["reader_exact_count_matches_dev_gold"] is True
        assert row["answer_sufficiency"] == "verified_occurrence_aggregation_matches_dev_gold"


def test_probe_accepts_exact_zero_with_proven_disjoint_unresolved_claim() -> None:
    aggregation = _occurrence_aggregation(0)
    unresolved = aggregation["unresolved_claims"]
    assert isinstance(unresolved, dict)
    unresolved.update(
        {
            "count": 1,
            "disjoint_proven": 1,
            "matching_or_unknown": 0,
        }
    )

    row = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "0",
        ),
        _pack(candidate=_candidate(0), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is True
    assert row["reader_exact_count_matches_dev_gold"] is True
    assert row["answer_sufficiency"] == "verified_occurrence_aggregation_matches_dev_gold"


def test_probe_rejects_nonzero_exact_without_complete_reviewed_closed_history() -> None:
    forward_only = _occurrence_aggregation()
    forward_coverage = forward_only["coverage"]
    assert isinstance(forward_coverage, dict)
    forward_coverage["coverage_mode"] = "forward_only"

    historical_not_reviewed = _occurrence_aggregation()
    historical_coverage = historical_not_reviewed["coverage"]
    assert isinstance(historical_coverage, dict)
    historical_coverage["historical_review_status"] = "needs_review"

    reversed_interval = _occurrence_aggregation()
    reversed_coverage = reversed_interval["coverage"]
    assert isinstance(reversed_coverage, dict)
    reversed_coverage["complete_through"] = "2023-12-31T23:59:59Z"

    for aggregation in (
        forward_only,
        historical_not_reviewed,
        reversed_interval,
    ):
        row = _row(
            _question(
                "00ca467f",
                "How many times did I service my bike?",
                "3",
            ),
            _pack(candidate=_candidate(), aggregation=aggregation),
        )

        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == "unsafe_exact"
        assert row["reader_aggregation"] is None
        assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_unsafe_exact_zero_projection() -> None:
    incomplete_coverage = _occurrence_aggregation(0)
    incomplete_coverage_record = incomplete_coverage["coverage"]
    assert isinstance(incomplete_coverage_record, dict)
    incomplete_coverage_record["fully_covered"] = False

    non_complete_history = _occurrence_aggregation(0)
    non_complete_history_coverage = non_complete_history["coverage"]
    assert isinstance(non_complete_history_coverage, dict)
    non_complete_history_coverage["coverage_mode"] = "partial_history"

    incomplete_signed_interval = _occurrence_aggregation(0)
    incomplete_signed_interval_coverage = incomplete_signed_interval["coverage"]
    assert isinstance(incomplete_signed_interval_coverage, dict)
    incomplete_signed_interval_coverage["complete_through"] = None

    unresolved = _occurrence_aggregation(0)
    unresolved_record = unresolved["unresolved_claims"]
    assert isinstance(unresolved_record, dict)
    unresolved_record["count"] = 1
    unresolved_record["matching_or_unknown"] = 1

    unresolved_saturated = _occurrence_aggregation(0)
    unresolved_saturated_record = unresolved_saturated["unresolved_claims"]
    assert isinstance(unresolved_saturated_record, dict)
    unresolved_saturated_record["saturated"] = True

    aggregate_saturated = _occurrence_aggregation(0)
    aggregate_saturated["saturated"] = True

    for aggregation in (
        incomplete_coverage,
        non_complete_history,
        incomplete_signed_interval,
        unresolved,
        unresolved_saturated,
        aggregate_saturated,
    ):
        row = _row(
            _question(
                "00ca467f",
                "How many times did I service my bike?",
                "0",
            ),
            _pack(candidate=_candidate(0), aggregation=aggregation),
        )

        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == "unsafe_exact"
        assert row["reader_aggregation"] is None
        assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_declared_valid_coverage_without_receipt_shape() -> None:
    question = _question(
        "00ca467f",
        "How many times did I service my bike?",
        "3",
    )
    aggregation = _occurrence_aggregation()
    coverage = aggregation["coverage"]
    assert isinstance(coverage, dict)
    assert "user_id" not in coverage
    assert _TEST_USER_ID not in repr(aggregation)
    coverage["review_receipt_digest"] = None

    row = _row(
        question,
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is False
    assert row["reader_aggregation_contract_error"] == "coverage_receipt_flag"
    assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_non_boolean_public_coverage_receipt_flag() -> None:
    aggregation = _occurrence_aggregation()
    coverage = aggregation["coverage"]
    assert isinstance(coverage, dict)
    coverage["receipt_valid"] = "true"
    row = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "3",
        ),
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is False
    assert row["reader_aggregation_contract_error"] == "coverage_receipt_flag"
    assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_leaked_or_tampered_coverage_accounting_metadata() -> None:
    private_values: dict[str, object] = {
        "metadata_json": {
            "source_ids": ["cross-scope-source"],
            "source_chunk_ids": ["cross-scope-chunk"],
        },
        "accounting_metadata": {
            "source_ids": ["cross-scope-source"],
            "source_chunk_ids": ["cross-scope-chunk"],
        },
        "source_ids": ["cross-scope-source"],
        "source_chunk_ids": ["cross-scope-chunk"],
        "user_id": "cross-scope-user",
        "snapshot_digest": "a" * 64,
        "disposition_digest": "b" * 64,
    }
    for key, value in private_values.items():
        aggregation = _occurrence_aggregation()
        coverage = aggregation["coverage"]
        assert isinstance(coverage, dict)
        coverage[key] = value

        row = _row(
            _question(
                "00ca467f",
                "How many times did I service my bike?",
                "3",
            ),
            _pack(candidate=_candidate(), aggregation=aggregation),
        )

        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == "coverage_accounting_metadata"
        assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"
        assert row["reader_aggregation"] is None
        assert repr(value) not in repr(row)


def test_gold_and_answer_sessions_only_change_post_pack_measurement() -> None:
    aggregation = _occurrence_aggregation()
    pack = _pack(candidate=_candidate(), aggregation=aggregation)
    matching = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "3",
            answer_session_ids=("gold-session-a",),
        ),
        pack,
    )
    mismatching = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "4",
            answer_session_ids=("different-a", "different-b"),
        ),
        pack,
    )

    assert (
        matching["reader_verified_occurrence_aggregation"]
        == mismatching["reader_verified_occurrence_aggregation"]
        == aggregation
    )
    assert matching["reader_aggregation_contract_valid"] is True
    assert mismatching["reader_aggregation_contract_valid"] is True
    assert matching["reader_exact_count_matches_dev_gold"] is True
    assert mismatching["reader_exact_count_matches_dev_gold"] is False
    assert matching["answer_session_count_for_measurement_only"] == 1
    assert mismatching["answer_session_count_for_measurement_only"] == 2


def test_probe_distinguishes_honest_range_and_at_least_from_exact_sufficiency() -> None:
    question = _question(
        "00ca467f",
        "How many times did I service my bike?",
        "3",
    )

    count_range = _row(
        question,
        _pack(
            candidate=_candidate(),
            aggregation=_occurrence_aggregation(answer_kind="range"),
        ),
    )
    at_least = _row(
        question,
        _pack(
            candidate=_candidate(),
            aggregation=_occurrence_aggregation(answer_kind="at_least"),
        ),
    )

    assert count_range["reader_aggregation_contract_valid"] is True
    assert count_range["reader_aggregation_answer_kind"] == "range"
    assert count_range["answer_sufficiency"] == "verified_occurrence_range_not_exact_answer"
    assert at_least["reader_aggregation_contract_valid"] is True
    assert at_least["reader_aggregation_answer_kind"] == "at_least"
    assert at_least["answer_sufficiency"] == "verified_occurrence_at_least_not_exact_answer"


def test_probe_accepts_complete_coverage_at_least_explained_by_unknown_relation() -> None:
    aggregation = _occurrence_aggregation()
    aggregation.update(
        {
            "answer_kind": "at_least",
            "exact": False,
            "upper_bound": None,
            "answer_sufficient": False,
        }
    )
    del aggregation["count"]
    accepted_units = aggregation["accepted_units"]
    assert isinstance(accepted_units, dict)
    accepted_units["relation_unknown"] = 1

    row = _row(
        _question(
            "00ca467f",
            "How many times did I service my bike?",
            "3",
        ),
        _pack(candidate=_candidate(), aggregation=aggregation),
    )

    assert row["reader_aggregation_contract_valid"] is True
    assert row["reader_aggregation_answer_kind"] == "at_least"
    assert row["answer_sufficiency"] == "verified_occurrence_at_least_not_exact_answer"


def test_probe_rejects_range_without_bounded_complete_event_projection() -> None:
    object_projection = _occurrence_aggregation(
        answer_kind="range",
        aggregation_basis="object_member",
    )

    aggregate_saturated = _occurrence_aggregation(answer_kind="range")
    aggregate_saturated["saturated"] = True

    unresolved_saturated = _occurrence_aggregation(answer_kind="range")
    unresolved_saturated_record = unresolved_saturated["unresolved_claims"]
    assert isinstance(unresolved_saturated_record, dict)
    unresolved_saturated_record["saturated"] = True

    forward_only = _occurrence_aggregation(answer_kind="range")
    forward_coverage = forward_only["coverage"]
    assert isinstance(forward_coverage, dict)
    forward_coverage["coverage_mode"] = "forward_only"

    partial_history = _occurrence_aggregation(answer_kind="range")
    partial_coverage = partial_history["coverage"]
    assert isinstance(partial_coverage, dict)
    partial_coverage["coverage_mode"] = "partial_history"

    legacy_gap = _occurrence_aggregation(answer_kind="range")
    legacy_gap_coverage = legacy_gap["coverage"]
    assert isinstance(legacy_gap_coverage, dict)
    legacy_gap_coverage["legacy_gap"] = True

    unsigned = _occurrence_aggregation(answer_kind="range")
    unsigned_coverage = unsigned["coverage"]
    assert isinstance(unsigned_coverage, dict)
    unsigned_coverage["receipt_valid"] = False

    reversed_interval = _occurrence_aggregation(answer_kind="range")
    reversed_coverage = reversed_interval["coverage"]
    assert isinstance(reversed_coverage, dict)
    reversed_coverage["complete_through"] = "2023-12-31T23:59:59Z"

    no_matching_claims = _occurrence_aggregation(answer_kind="range")
    no_matching_record = no_matching_claims["unresolved_claims"]
    assert isinstance(no_matching_record, dict)
    no_matching_record.update(
        {
            "count": 2,
            "disjoint_proven": 2,
            "matching_or_unknown": 0,
        }
    )

    unknown_relation = _occurrence_aggregation(answer_kind="range")
    unknown_accepted = unknown_relation["accepted_units"]
    assert isinstance(unknown_accepted, dict)
    unknown_accepted["relation_unknown"] = 1

    for aggregation in (
        object_projection,
        aggregate_saturated,
        unresolved_saturated,
        forward_only,
        partial_history,
        legacy_gap,
        unsigned,
        reversed_interval,
        no_matching_claims,
        unknown_relation,
    ):
        row = _row(
            _question(
                "00ca467f",
                "How many times did I service my bike?",
                "3",
            ),
            _pack(candidate=_candidate(), aggregation=aggregation),
        )

        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == "unsafe_range"
        assert row["reader_aggregation"] is None
        assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_unknown_reader_fields_and_carrierless_evidence() -> None:
    question = _question("00ca467f", "How many times did I service my bike?")
    invalid: list[tuple[dict[str, object], str]] = []

    unexpected_top_level = _occurrence_aggregation()
    unexpected_top_level["unexpected_private_field"] = "copied"
    invalid.append((unexpected_top_level, "aggregation_keys"))

    unexpected_provenance = _occurrence_aggregation()
    provenance = unexpected_provenance["provenance"]
    assert isinstance(provenance, list)
    assert isinstance(provenance[0], dict)
    provenance[0]["unexpected_private_field"] = "copied"
    invalid.append((unexpected_provenance, "provenance_keys"))

    unexpected_evidence = _occurrence_aggregation()
    provenance = unexpected_evidence["provenance"]
    assert isinstance(provenance, list)
    assert isinstance(provenance[0], dict)
    evidence = provenance[0]["evidence"]
    assert isinstance(evidence, list)
    assert isinstance(evidence[0], dict)
    evidence[0]["unexpected_private_field"] = "copied"
    invalid.append((unexpected_evidence, "evidence_keys"))

    unexpected_unresolved = _occurrence_aggregation()
    unresolved = unexpected_unresolved["unresolved_claims"]
    assert isinstance(unresolved, dict)
    unresolved["unexpected_private_field"] = "copied"
    invalid.append((unexpected_unresolved, "unresolved_claim_keys"))

    carrierless = _occurrence_aggregation()
    provenance = carrierless["provenance"]
    assert isinstance(provenance, list)
    for item in provenance:
        assert isinstance(item, dict)
        evidence = item["evidence"]
        assert isinstance(evidence, list)
        for evidence_item in evidence:
            assert isinstance(evidence_item, dict)
            for key in ("memory_id", "source_id", "source_chunk_id"):
                evidence_item.pop(key, None)
    invalid.append((carrierless, "evidence_carrier"))

    source_chunk_without_source = _occurrence_aggregation()
    provenance = source_chunk_without_source["provenance"]
    assert isinstance(provenance, list)
    assert isinstance(provenance[0], dict)
    evidence = provenance[0]["evidence"]
    assert isinstance(evidence, list)
    assert isinstance(evidence[0], dict)
    evidence[0].pop("source_id")
    invalid.append(
        (
            source_chunk_without_source,
            "evidence_source_chunk_without_source",
        )
    )

    invalid_carrier = _occurrence_aggregation()
    provenance = invalid_carrier["provenance"]
    assert isinstance(provenance, list)
    assert isinstance(provenance[0], dict)
    evidence = provenance[0]["evidence"]
    assert isinstance(evidence, list)
    assert isinstance(evidence[0], dict)
    evidence[0]["memory_id"] = ""
    invalid.append((invalid_carrier, "evidence_carrier"))

    for aggregation, expected_error in invalid:
        row = _row(
            question,
            _pack(candidate=_candidate(), aggregation=aggregation),
        )
        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == expected_error
        assert row["reader_aggregation"] is None
        assert row["reader_verified_occurrence_aggregation"] is None
        assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_rejects_non_unit_counts_and_incomplete_occurrence_receipts() -> None:
    question = _question("00ca467f", "How many times did I service my bike?")
    invalid: list[tuple[dict[str, object], str]] = []

    wrong_unit = _occurrence_aggregation()
    wrong_unit["unit"] = "deduplicated_memory_candidate_groups"
    invalid.append((wrong_unit, "unit"))

    object_member_wrong_unit = _occurrence_aggregation(aggregation_basis="object_member")
    object_member_wrong_unit["unit"] = "reviewed_occurrence_units"
    invalid.append((object_member_wrong_unit, "unit"))

    missing_basis = _occurrence_aggregation()
    del missing_basis["aggregation_basis"]
    invalid.append((missing_basis, "aggregation_basis"))

    unsupported_basis = _occurrence_aggregation()
    unsupported_basis["aggregation_basis"] = "memory_row"
    invalid.append((unsupported_basis, "aggregation_basis"))

    malformed_basis = _occurrence_aggregation()
    malformed_basis["aggregation_basis"] = []
    invalid.append((malformed_basis, "aggregation_basis"))

    duplicate_global_member = _occurrence_aggregation()
    duplicate_global_keys = duplicate_global_member["counted_member_keys"]
    assert isinstance(duplicate_global_keys, list)
    duplicate_global_member["counted_member_keys"] = sorted([*duplicate_global_keys, duplicate_global_keys[0]])
    invalid.append((duplicate_global_member, "counted_member_keys"))

    empty_unit_members = _occurrence_aggregation()
    empty_unit_provenance = empty_unit_members["provenance"]
    assert isinstance(empty_unit_provenance, list)
    assert isinstance(empty_unit_provenance[0], dict)
    empty_unit_provenance[0]["counted_member_keys"] = []
    invalid.append((empty_unit_members, "provenance_counted_member_keys"))

    duplicate_unit_members = _occurrence_aggregation()
    duplicate_member_provenance = duplicate_unit_members["provenance"]
    assert isinstance(duplicate_member_provenance, list)
    assert isinstance(duplicate_member_provenance[0], dict)
    duplicate_member_keys = duplicate_member_provenance[0]["counted_member_keys"]
    assert isinstance(duplicate_member_keys, list)
    duplicate_member_provenance[0]["counted_member_keys"] = [
        *duplicate_member_keys,
        duplicate_member_keys[0],
    ]
    invalid.append((duplicate_unit_members, "provenance_counted_member_keys"))

    unsorted_unit_members = _occurrence_aggregation()
    unsorted_member_provenance = unsorted_unit_members["provenance"]
    assert isinstance(unsorted_member_provenance, list)
    assert isinstance(unsorted_member_provenance[0], dict)
    unsorted_member_keys = unsorted_member_provenance[0]["counted_member_keys"]
    assert isinstance(unsorted_member_keys, list)
    unsorted_member_provenance[0]["counted_member_keys"] = [
        *unsorted_member_keys,
        "0" * 64,
    ]
    invalid.append((unsorted_unit_members, "provenance_counted_member_keys"))

    malformed_event_member = _occurrence_aggregation(1)
    malformed_event_provenance = malformed_event_member["provenance"]
    assert isinstance(malformed_event_provenance, list)
    assert isinstance(malformed_event_provenance[0], dict)
    malformed_event_provenance[0]["counted_member_keys"] = ["not-a-lowercase-sha256"]
    malformed_event_member["counted_member_keys"] = ["not-a-lowercase-sha256"]
    invalid.append((malformed_event_member, "event_instance_member_key"))

    malformed_object_member = _occurrence_aggregation(
        1,
        aggregation_basis="object_member",
    )
    malformed_object_provenance = malformed_object_member["provenance"]
    assert isinstance(malformed_object_provenance, list)
    assert isinstance(malformed_object_provenance[0], dict)
    malformed_object_provenance[0]["counted_member_keys"] = ["object:v1:not-a-lowercase-sha256"]
    malformed_object_member["counted_member_keys"] = ["object:v1:not-a-lowercase-sha256"]
    invalid.append((malformed_object_member, "object_member_key"))

    unsigned_unit = _occurrence_aggregation()
    unsigned_unit_provenance = unsigned_unit["provenance"]
    assert isinstance(unsigned_unit_provenance, list)
    assert isinstance(unsigned_unit_provenance[0], dict)
    del unsigned_unit_provenance[0]["review_receipt_digest"]
    invalid.append((unsigned_unit, "unit_review_receipt"))

    duplicate_units = _occurrence_aggregation()
    duplicate_units["occurrence_unit_ids"] = [
        "occurrence-01",
        "occurrence-01",
        "occurrence-03",
    ]
    invalid.append((duplicate_units, "occurrence_unit_ids"))

    no_evidence = _occurrence_aggregation()
    no_evidence_provenance = no_evidence["provenance"]
    assert isinstance(no_evidence_provenance, list)
    assert isinstance(no_evidence_provenance[0], dict)
    no_evidence_provenance[0]["evidence"] = []
    invalid.append((no_evidence, "evidence"))

    no_support = _occurrence_aggregation()
    no_support_provenance = no_support["provenance"]
    assert isinstance(no_support_provenance, list)
    assert isinstance(no_support_provenance[0], dict)
    no_support_evidence = no_support_provenance[0]["evidence"]
    assert isinstance(no_support_evidence, list)
    assert isinstance(no_support_evidence[0], dict)
    no_support_evidence[0]["evidence_role"] = "same_event_hint"
    invalid.append((no_support, "evidence_receipt"))

    mixed_evidence_roles = _occurrence_aggregation()
    mixed_role_provenance = mixed_evidence_roles["provenance"]
    assert isinstance(mixed_role_provenance, list)
    assert isinstance(mixed_role_provenance[0], dict)
    mixed_role_evidence = mixed_role_provenance[0]["evidence"]
    assert isinstance(mixed_role_evidence, list)
    assert isinstance(mixed_role_evidence[0], dict)
    extra_evidence = deepcopy(mixed_role_evidence[0])
    extra_evidence.update(
        {
            "evidence_id": "same-event-hint",
            "evidence_key": "same-event-hint",
            "evidence_role": "same_event_hint",
        }
    )
    mixed_role_evidence.append(extra_evidence)
    invalid.append((mixed_evidence_roles, "evidence_receipt"))

    unsigned_evidence = _occurrence_aggregation()
    unsigned_evidence_provenance = unsigned_evidence["provenance"]
    assert isinstance(unsigned_evidence_provenance, list)
    assert isinstance(unsigned_evidence_provenance[0], dict)
    unsigned_evidence_items = unsigned_evidence_provenance[0]["evidence"]
    assert isinstance(unsigned_evidence_items, list)
    assert isinstance(unsigned_evidence_items[0], dict)
    unsigned_evidence_items[0]["review_status"] = "candidate"
    invalid.append((unsigned_evidence, "evidence_receipt"))

    cross_receipt = _occurrence_aggregation()
    cross_receipt_provenance = cross_receipt["provenance"]
    assert isinstance(cross_receipt_provenance, list)
    assert isinstance(cross_receipt_provenance[0], dict)
    cross_receipt_evidence = cross_receipt_provenance[0]["evidence"]
    assert isinstance(cross_receipt_evidence, list)
    assert isinstance(cross_receipt_evidence[0], dict)
    cross_receipt_evidence[0]["unit_review_receipt_digest"] = "f" * 64
    invalid.append((cross_receipt, "evidence_receipt"))

    stale_evidence_count = _occurrence_aggregation()
    stale_count_provenance = stale_evidence_count["provenance"]
    assert isinstance(stale_count_provenance, list)
    assert isinstance(stale_count_provenance[0], dict)
    stale_count_provenance[0]["reviewed_evidence_count"] = 2
    invalid.append((stale_evidence_count, "reviewed_evidence_count"))

    malformed_evidence_digest = _occurrence_aggregation()
    stale_digest_provenance = malformed_evidence_digest["provenance"]
    assert isinstance(stale_digest_provenance, list)
    assert isinstance(stale_digest_provenance[0], dict)
    stale_digest_provenance[0]["reviewed_evidence_digest"] = "not-a-sha256"
    invalid.append((malformed_evidence_digest, "unit_review_receipt"))

    unsafe_coverage = _occurrence_aggregation()
    unsafe_coverage_record = unsafe_coverage["coverage"]
    assert isinstance(unsafe_coverage_record, dict)
    unsafe_coverage_record["fully_covered"] = False
    invalid.append((unsafe_coverage, "unsafe_exact"))

    unresolved = _occurrence_aggregation()
    unresolved_record = unresolved["unresolved_claims"]
    assert isinstance(unresolved_record, dict)
    unresolved_record["count"] = 1
    unresolved_record["matching_or_unknown"] = 1
    invalid.append((unresolved, "unsafe_exact"))

    unknown_relation = _occurrence_aggregation()
    unknown_accepted = unknown_relation["accepted_units"]
    assert isinstance(unknown_accepted, dict)
    unknown_accepted["relation_unknown"] = 1
    invalid.append((unknown_relation, "unsafe_exact"))

    saturated = _occurrence_aggregation()
    saturated["saturated"] = True
    invalid.append((saturated, "unsafe_exact"))

    legacy_gap = _occurrence_aggregation()
    legacy_coverage = legacy_gap["coverage"]
    assert isinstance(legacy_coverage, dict)
    legacy_coverage["legacy_gap"] = True
    invalid.append((legacy_gap, "unsafe_exact"))

    wrong_count = _occurrence_aggregation()
    wrong_count["count"] = 2
    invalid.append((wrong_count, "exact_bounds"))

    for aggregation, expected_error in invalid:
        row = _row(
            question,
            _pack(candidate=_candidate(), aggregation=aggregation),
        )
        assert row["reader_aggregation_contract_valid"] is False
        assert row["reader_aggregation_contract_error"] == expected_error
        assert row["answer_sufficiency"] == "invalid_reader_aggregation_not_an_answer"


def test_probe_safe_non_emission_strata_cover_numeric_rejected_and_cadence() -> None:
    cases = (
        (
            _question("10d9b85a", "How many days did the trip last?"),
            STRATUM_NUMERIC_SAFE_NON_EMISSION,
            "numeric_value",
        ),
        (
            _question("4adc0475", "What is the total number of goals and assists I have?"),
            STRATUM_REJECTED_GATE_WIDENING,
            None,
        ),
        (
            _question("945e3d21", "How often did I service my bike?", "Three times a week"),
            STRATUM_CADENCE_ANSWERABLE,
            "cadence",
        ),
        (
            _question("2698e78f_abs", "How often did I service my bike?", "No evidence"),
            STRATUM_CADENCE_ABSTENTION,
            "cadence",
        ),
    )

    for question, stratum, sub_intent in cases:
        row = _row(question, _pack())
        assert row["hand_audited_stratum"] == stratum
        assert row["detector_sub_intent"] == sub_intent
        assert row["trace_candidate_count_present"] is False
        assert row["reader_aggregation_present"] is False
        assert row["mechanism_expectation_met"] is True
        assert row["safety_expectation_met"] is True
    abstention = _row(cases[-1][0], _pack())
    assert abstention["safe_abstention_non_answer"] is True


def test_probe_summary_and_exit_require_eight_of_fourteen_exact_answers() -> None:
    question = _question("00ca467f", "How many bike services did I record?")
    trace_only = _row(question, _pack(candidate=_candidate()))
    no_go = summarize_rows([trace_only])

    assert no_go["overall"]["mechanism_expectations_failed"] == 0  # type: ignore[index]
    assert no_go["overall"]["answer_sufficiency_checks"] == 1  # type: ignore[index]
    assert (
        no_go["overall"][  # type: ignore[index]
            "answer_sufficient_via_verified_occurrence_aggregation"
        ]
        == 0
    )
    assert exit_code_for_summary(no_go, has_errors=False) == EXIT_STRATUM_FAILURES

    green = summarize_rows(_release_manifest_rows(sufficient=DEFAULT_ANSWER_SUFFICIENCY_TARGET))
    assert green["overall"]["audited"] == 23  # type: ignore[index]
    assert green["overall"]["safety_checks"] == 9  # type: ignore[index]
    assert green["overall"]["answer_sufficiency_checks"] == 14  # type: ignore[index]
    assert (
        green["overall"][  # type: ignore[index]
            "answer_sufficient_via_verified_occurrence_aggregation"
        ]
        == 8
    )
    assert green["overall"]["answer_sufficiency_target"] == 8  # type: ignore[index]
    assert green["overall"]["answer_sufficiency_target_met"] is True  # type: ignore[index]
    assert (
        exit_code_for_summary(
            green,
            has_errors=False,
            expected_manifest=DEFAULT_AUDIT_MANIFEST,
        )
        == EXIT_OK
    )
    assert (
        exit_code_for_summary(
            green,
            has_errors=False,
            expected_manifest=None,
        )
        == EXIT_STRATUM_FAILURES
    )
    assert (
        exit_code_for_summary(
            green,
            has_errors=False,
            expected_manifest=DEFAULT_AUDIT_MANIFEST,
            release_gate_eligible=False,
        )
        == EXIT_STRATUM_FAILURES
    )

    below_target = summarize_rows(_release_manifest_rows(sufficient=DEFAULT_ANSWER_SUFFICIENCY_TARGET - 1))
    assert below_target["overall"]["answer_sufficiency_target_met"] is False  # type: ignore[index]
    assert (
        exit_code_for_summary(
            below_target,
            has_errors=False,
            expected_manifest=DEFAULT_AUDIT_MANIFEST,
        )
        == EXIT_STRATUM_FAILURES
    )
    assert (
        exit_code_for_summary(
            green,
            has_errors=True,
            expected_manifest=DEFAULT_AUDIT_MANIFEST,
        )
        == EXIT_RUN_FAILURES
    )


def test_probe_keeps_mechanism_and_safety_gates_strict_at_majority_target() -> None:
    rows = _release_manifest_rows(sufficient=DEFAULT_ANSWER_SUFFICIENCY_TARGET)

    mechanism_failure = deepcopy(rows)
    mechanism_failure[0]["mechanism_expectation_met"] = False
    assert (
        exit_code_for_summary(
            summarize_rows(mechanism_failure),
            has_errors=False,
            expected_manifest=DEFAULT_AUDIT_MANIFEST,
        )
        == EXIT_STRATUM_FAILURES
    )

    safety_failure = deepcopy(rows)
    safety_row = next(row for row in safety_failure if row["safety_expectation_met"] is not None)
    safety_row["safety_expectation_met"] = False
    assert (
        exit_code_for_summary(
            summarize_rows(safety_failure),
            has_errors=False,
            expected_manifest=DEFAULT_AUDIT_MANIFEST,
        )
        == EXIT_STRATUM_FAILURES
    )


def test_probe_exit_rejects_empty_detector_only_and_incomplete_default_manifest() -> None:
    assert exit_code_for_summary(summarize_rows([]), has_errors=False) == EXIT_STRATUM_FAILURES
    detector_only = _row(
        _question("unreviewed", "How many bikes did I service?"),
        _pack(candidate=_candidate()),
    )
    assert exit_code_for_summary(summarize_rows([detector_only]), has_errors=False) == EXIT_STRATUM_FAILURES
    selected_card = _row(
        _question("00ca467f", "How many times did I service my bike?"),
        _pack(candidate=_candidate(), selected_rollup=True),
    )
    numeric = _row(
        _question("10d9b85a", "How many days did the trip last?"),
        _pack(),
    )
    incomplete = summarize_rows([selected_card, numeric])
    assert (
        exit_code_for_summary(
            incomplete,
            has_errors=False,
            expected_manifest=DEFAULT_AUDIT_MANIFEST,
        )
        == EXIT_STRATUM_FAILURES
    )
    # ``--limit`` changes row selection, not the default-slice truth target:
    # main() keeps this exact manifest and therefore rejects the partial run.
    assert expected_audit_manifest(Path(DEFAULT_SLICE)) == DEFAULT_AUDIT_MANIFEST


def test_default_outputs_separate_rollup_modes() -> None:
    dataset = Path("longmemeval_s_cleaned.json")
    defaults = count_probe_module.build_arg_parser().parse_args([])

    off = default_output_path(dataset, accept_rollups=False)
    on = default_output_path(dataset, accept_rollups=True)

    assert defaults.with_vectors is False
    assert defaults.with_reranker is False
    assert off.name == "count_probe_longmemeval_s_cleaned_rollups_off.jsonl"
    assert on.name == "count_probe_longmemeval_s_cleaned_rollups_on.jsonl"
    assert off != on


def test_probe_request_uses_the_question_date_as_reference_time(
    monkeypatch,
    tmp_path: Path,
) -> None:
    question = _question("00ca467f", "How many bike services did I record?")
    captured: dict[str, object] = {}

    class FakeStore:
        user_id = _TEST_USER_ID

    class FakeRun:
        store = FakeStore()

        def ingest(self, *, accept_rollups: bool) -> None:
            captured["accept_rollups"] = accept_rollups

    @contextmanager
    def fake_question_run(_question_value, _db_path):
        yield FakeRun()

    class FakeService:
        def __init__(self, _store: object) -> None:
            pass

        def compile_context_pack(self, request):
            captured["request"] = request
            return {"relevant_memories": [], "trace": {"stages": {}}}

    monkeypatch.setattr(count_probe_module, "question_run", fake_question_run)
    monkeypatch.setattr(count_probe_module, "VNextRetrievalService", FakeService)
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text("[]\n", encoding="utf-8")

    probe_question(
        question,
        work_dir=tmp_path,
        dataset_path=dataset_path,
        max_items=16,
        accept_rollups=False,
    )

    request = captured["request"]
    assert request.reference_time is not None
    assert request.reference_time.isoformat() == "2025-01-01T00:00:00+00:00"
