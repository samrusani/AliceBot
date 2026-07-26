"""Deterministic LongMemEval count-intent context-pack probe.

This keyless Phase 6 companion to ``coverage_probe.py`` reuses the same
per-question SQLite stores and compiles the same model-free context pack. It
keeps three surfaces separate:

* the Phase 4 bounded FTS candidate statistic, which remains trace-only;
* accepted memory roll-up cards, whose members remain non-countable; and
* the Phase 6 evidence-bearing ``occurrence_count`` reader contract.

Only an exact occurrence aggregate backed by distinct reviewed members and
per-unit supporting evidence can be answer-sufficient. Honest ``range`` and
``at_least`` aggregates are validated and reported but do not earn the exact
development-gold gate. Gold answers and ``answer_session_ids`` are comparison
inputs after pack compilation only; they never create, merge, or review units.
Numeric-value questions (hours/days/pages) and cadence questions ("how
often") form explicit safe-non-emission strata: coverage mode may run, but a
memory-row total must stay absent. The cadence abstention fixtures likewise
require recognition plus safe non-emission, not a fabricated answer.

Embeddings and the optional reranker are scrubbed by default, so no model or
paid API call can occur. Run from the repository root:

    .venv/bin/python eval/longmemeval/count_probe.py \
      --dataset-file eval/longmemeval/data/longmemeval_s_cleaned.json \
      --work-dir /private/tmp/alice-sprint4-stage1-work \
      --max-items 16 --workers 8
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Mapping, Sequence

_EVAL_DIR = Path(__file__).resolve().parent.parent
if str(_EVAL_DIR) not in sys.path:  # direct execution
    sys.path.insert(0, str(_EVAL_DIR))

from alicebot_api.vnext_coverage_query import (
    AGGREGATION_KIND_COUNT,
    COUNT_SUB_INTENT_CADENCE,
    COUNT_SUB_INTENT_NUMERIC_VALUE,
    count_bearing_rollup_member_count,
    detect_aggregation_intent,
    supports_candidate_instance_count,
)
from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService
from alicebot_api.vnext_temporal_query import parse_event_datetime

from longmemeval.adapter import max_items_from_env, question_run
from longmemeval.coverage_probe import (
    GOVERNED_DATASET_PATH,
    GOVERNED_DATASET_SHA256,
    GOVERNED_MAX_ITEMS,
    all_probe_stores_fresh,
    disable_embeddings_env,
    disable_reranker_env,
    file_sha256,
    provider_summary_metadata,
)
from longmemeval.dataset import (
    RESULTS_DIR,
    LongMemEvalDatasetError,
    LongMemEvalQuestion,
    load_dataset,
    resolve_dataset_path,
)
from longmemeval.runner import (
    _FILENAME_SAFE,
    _build_ingest_marker_payload,
    _cleanup_store,
    _sha256_prefix,
)


COUNT_PROBE_SCHEMA = "longmemeval_count_probe_v3"
DEFAULT_SLICE = Path(__file__).resolve().parent / "slices" / "stage1-150.txt"
DEFAULT_WORK_DIR = Path(__file__).resolve().parent / "work" / "coverage"
GOVERNED_AUDIT_QUESTION_COUNT = 172
GOVERNED_AUDIT_MANIFEST_SHA256 = "cc93a902019a82401f1f9bffc5c9437b08d1e269da599e248d64a7980e67ef73"

EXIT_OK = 0
EXIT_RUN_FAILURES = 1
EXIT_CONFIG_ERROR = 2
EXIT_STRATUM_FAILURES = 3

STRATUM_CANDIDATE_COUNT = "candidate_count_eligible"
STRATUM_NUMERIC_SAFE_NON_EMISSION = "numeric_value_safe_non_emission"
STRATUM_CADENCE_ANSWERABLE = "cadence_answerable_safe_non_emission"
STRATUM_CADENCE_ABSTENTION = "cadence_abstention_safe_non_emission"
STRATUM_REJECTED_GATE_WIDENING = "rejected_gate_widening_safe_non_emission"
STRATUM_DETECTOR_ONLY = "detector_only_unreviewed"
DEFAULT_AUDIT_MANIFEST = {
    "audited": 23,
    "safety_checks": 9,
    "answer_sufficiency_checks": 14,
}
DEFAULT_ANSWER_SUFFICIENCY_TARGET = 8

OCCURRENCE_AGGREGATION_KIND = "occurrence_count"
OCCURRENCE_ANSWER_KINDS = frozenset({"exact", "range", "at_least"})
OCCURRENCE_AGGREGATION_BASES = frozenset({"event_instance", "object_member"})
OCCURRENCE_AGGREGATION_UNITS = {
    "event_instance": "reviewed_occurrence_units",
    "object_member": "reviewed_object_members",
}
_OCCURRENCE_COVERAGE_MODES = frozenset({"forward_only", "partial_history", "complete_history"})
_OCCURRENCE_HISTORICAL_REVIEW_STATUSES = frozenset({"not_reviewed", "needs_review", "reviewed"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OBJECT_MEMBER_KEY_RE = re.compile(r"^object:v1:[0-9a-f]{64}$")
_OCCURRENCE_AGGREGATION_KEYS = frozenset(
    {
        "kind",
        "answer_kind",
        "exact",
        "lower_bound",
        "upper_bound",
        "unit",
        "aggregation_basis",
        "counted_member_keys",
        "occurrence_unit_ids",
        "provenance",
        "accepted_units",
        "coverage",
        "unresolved_claims",
        "saturated",
        "answer_sufficient",
    }
)
_OCCURRENCE_PROVENANCE_KEYS = frozenset(
    {
        "occurrence_unit_id",
        "counted_member_keys",
        "review_receipt_digest",
        "reviewed_evidence_digest",
        "reviewed_evidence_count",
        "evidence",
    }
)
_OCCURRENCE_EVIDENCE_KEYS = frozenset(
    {
        "evidence_id",
        "evidence_key",
        "evidence_role",
        "quote_sha256",
        "review_status",
        "review_receipt_digest",
        "unit_review_receipt_digest",
    }
)
_OCCURRENCE_EVIDENCE_CARRIER_KEYS = frozenset(
    {
        "memory_id",
        "source_id",
        "source_chunk_id",
    }
)
_OCCURRENCE_UNRESOLVED_CLAIM_KEYS = frozenset(
    {
        "count",
        "disjoint_proven",
        "matching_or_unknown",
        "saturated",
    }
)

# Hand-audited development strata from the fixed stage-1 slice. These are
# product-mechanism checks, not benchmark-label access during retrieval.
_CARDINALITY_FREQUENCY_IDS = frozenset(
    {
        "00ca467f",
        "0a995998",
        "1a8a66a6",
        "2788b940",
        "2e6d26dc",
        "4f54b7c9",
        "60159905",
        "681a1674",
        "88432d0a",
        "9d25d4e0",
        "a9f6b44c",
        "bf659f65",
        "c2ac3c61",
        "d682f1a2",
    }
)
_NUMERIC_SAFE_IDS = frozenset({"10d9b85a", "5a7937c8", "a08a253f"})
_GATE_RECALL_ANSWERABLE_IDS = frozenset({"945e3d21"})
_GATE_RECALL_ABSTENTION_IDS = frozenset({"2698e78f_abs", "f685340e_abs"})
_REJECTED_GATE_WIDENING_IDS = frozenset({"4adc0475", "8979f9ec", "8e91e7d9"})


def hand_audited_stratum(question_id: str) -> str:
    if question_id in _CARDINALITY_FREQUENCY_IDS:
        return STRATUM_CANDIDATE_COUNT
    if question_id in _NUMERIC_SAFE_IDS:
        return STRATUM_NUMERIC_SAFE_NON_EMISSION
    if question_id in _GATE_RECALL_ANSWERABLE_IDS:
        return STRATUM_CADENCE_ANSWERABLE
    if question_id in _GATE_RECALL_ABSTENTION_IDS:
        return STRATUM_CADENCE_ABSTENTION
    if question_id in _REJECTED_GATE_WIDENING_IDS:
        return STRATUM_REJECTED_GATE_WIDENING
    return STRATUM_DETECTOR_ONLY


def _db_path_for(work_dir: Path, question_id: str) -> Path:
    return work_dir / f"{_FILENAME_SAFE.sub('_', question_id)}.sqlite3"


def _marker_path_for(db_path: Path) -> Path:
    return Path(str(db_path) + ".ingested.json")


def _marker_matches(
    marker_path: Path,
    question: LongMemEvalQuestion,
    dataset_path: Path,
    *,
    accept_rollups: bool,
) -> bool:
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(marker, dict) and marker == _build_ingest_marker_payload(
        question,
        dataset_path=dataset_path,
        accept_rollups=accept_rollups,
    )


def _trace_candidate_record(pack: Mapping[str, object]) -> dict[str, object] | None:
    trace = pack.get("trace")
    if not isinstance(trace, Mapping):
        return None
    stages = trace.get("stages")
    if not isinstance(stages, Mapping):
        return None
    coverage = stages.get("coverage_mode")
    if not isinstance(coverage, Mapping):
        return None
    candidate = coverage.get("candidate_instance_count")
    if not isinstance(candidate, Mapping):
        return None
    return {str(key): value for key, value in candidate.items()}


def _reader_aggregation_record(pack: Mapping[str, object]) -> dict[str, object] | None:
    aggregation = pack.get("aggregation")
    if not isinstance(aggregation, Mapping):
        return None
    return {str(key): value for key, value in aggregation.items()}


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _coverage_receipt_is_valid(
    coverage: Mapping[str, object],
    *,
    expected_user_id: str,
) -> bool:
    """Validate the redacted public receipt contract.

    The complete-history accounting manifest is deliberately not exposed in a
    context pack because it can contain source and chunk IDs outside the query
    scope. The occurrence reader reconstructs and validates the full signed
    receipt before producing this record; the probe therefore validates the
    boolean result and the public receipt shape instead of attempting to
    recreate a different, incomplete signature payload.
    """

    coverage_id = coverage.get("id")
    coverage_started = parse_event_datetime(coverage.get("coverage_started_at"))
    complete_through = parse_event_datetime(coverage.get("complete_through"))
    review_version = coverage.get("review_version")
    reviewer_id = coverage.get("reviewer_id")
    review_reason = coverage.get("review_reason")
    receipt = coverage.get("review_receipt_digest")
    receipt_valid = coverage.get("receipt_valid")
    if (
        not _is_nonempty_string(coverage_id)
        or not _is_nonempty_string(expected_user_id)
        or coverage_started is None
        or (coverage.get("complete_through") is not None and complete_through is None)
        or not isinstance(receipt_valid, bool)
    ):
        return False
    if not receipt_valid:
        return False
    return bool(
        not isinstance(review_version, bool)
        and isinstance(review_version, int)
        and review_version >= 1
        and _is_nonempty_string(reviewer_id)
        and _is_nonempty_string(review_reason)
        and isinstance(receipt, str)
        and _SHA256_RE.fullmatch(receipt) is not None
    )


def _coverage_has_valid_closed_interval(
    coverage: Mapping[str, object],
) -> bool:
    coverage_started = parse_event_datetime(coverage.get("coverage_started_at"))
    complete_through = parse_event_datetime(coverage.get("complete_through"))
    return bool(coverage_started is not None and complete_through is not None and complete_through >= coverage_started)


def _validate_occurrence_reader_aggregation(
    aggregation: Mapping[str, object] | None,
    *,
    expected_user_id: str,
) -> tuple[dict[str, object] | None, str | None]:
    """Validate the evidence-bearing reader contract without consulting gold."""

    if aggregation is None:
        return None, "missing"
    record = {str(key): value for key, value in aggregation.items()}
    if record.get("kind") != OCCURRENCE_AGGREGATION_KIND:
        return None, "kind"
    answer_kind = record.get("answer_kind")
    if not isinstance(answer_kind, str) or answer_kind not in OCCURRENCE_ANSWER_KINDS:
        return None, "answer_kind"
    exact = record.get("exact")
    if not isinstance(exact, bool) or exact is not (answer_kind == "exact"):
        return None, "exact_flag"
    aggregation_basis = record.get("aggregation_basis")
    if not isinstance(aggregation_basis, str) or aggregation_basis not in OCCURRENCE_AGGREGATION_BASES:
        return None, "aggregation_basis"
    if record.get("unit") != OCCURRENCE_AGGREGATION_UNITS[aggregation_basis]:
        return None, "unit"

    lower_bound = record.get("lower_bound")
    if not _is_plain_int(lower_bound) or lower_bound < 0 or (lower_bound == 0 and answer_kind != "exact"):
        return None, "lower_bound"
    upper_bound = record.get("upper_bound")
    if answer_kind == "exact":
        count = record.get("count")
        if (
            not _is_plain_int(count)
            or count != lower_bound
            or not _is_plain_int(upper_bound)
            or upper_bound != lower_bound
        ):
            return None, "exact_bounds"
    elif "count" in record:
        return None, "non_exact_count"
    elif answer_kind == "range":
        if not _is_plain_int(upper_bound) or upper_bound <= lower_bound:
            return None, "range_bounds"
    elif upper_bound is not None:
        return None, "at_least_upper_bound"

    counted_member_keys = record.get("counted_member_keys")
    if (
        not isinstance(counted_member_keys, list)
        or any(not _is_nonempty_string(member_key) for member_key in counted_member_keys)
        or len(set(counted_member_keys)) != len(counted_member_keys)
        or counted_member_keys != sorted(counted_member_keys)
        or lower_bound != len(counted_member_keys)
    ):
        return None, "counted_member_keys"

    unit_ids = record.get("occurrence_unit_ids")
    if (
        not isinstance(unit_ids, list)
        or any(not _is_nonempty_string(unit_id) for unit_id in unit_ids)
        or len(set(unit_ids)) != len(unit_ids)
        or unit_ids != sorted(unit_ids)
    ):
        return None, "occurrence_unit_ids"

    provenance = record.get("provenance")
    if not isinstance(provenance, list) or len(provenance) != len(unit_ids):
        return None, "provenance"
    if lower_bound > 0 and (not counted_member_keys or not unit_ids):
        return None, "nonzero_projection"
    if lower_bound == 0 and (counted_member_keys or unit_ids or provenance):
        return None, "exact_zero_projection"
    if aggregation_basis == "event_instance" and lower_bound != len(unit_ids):
        return None, "event_instance_projection"

    provenance_ids: list[str] = []
    provenance_member_keys: set[str] = set()
    evidence_ids: set[str] = set()
    evidence_keys: set[str] = set()
    for item in provenance:
        if not isinstance(item, Mapping):
            return None, "provenance_item"
        if set(item) - _OCCURRENCE_PROVENANCE_KEYS:
            return None, "provenance_keys"
        occurrence_unit_id = item.get("occurrence_unit_id")
        if not _is_nonempty_string(occurrence_unit_id):
            return None, "provenance_unit_id"
        provenance_ids.append(occurrence_unit_id)
        item_member_keys = item.get("counted_member_keys")
        if (
            not isinstance(item_member_keys, list)
            or not item_member_keys
            or any(not _is_nonempty_string(member_key) for member_key in item_member_keys)
            or len(set(item_member_keys)) != len(item_member_keys)
            or item_member_keys != sorted(item_member_keys)
        ):
            return None, "provenance_counted_member_keys"
        if aggregation_basis == "event_instance":
            if len(item_member_keys) != 1 or _SHA256_RE.fullmatch(item_member_keys[0]) is None:
                return None, "event_instance_member_key"
        elif any(_OBJECT_MEMBER_KEY_RE.fullmatch(member_key) is None for member_key in item_member_keys):
            return None, "object_member_key"
        provenance_member_keys.update(item_member_keys)
        unit_review_receipt = item.get("review_receipt_digest")
        reviewed_evidence_digest = item.get("reviewed_evidence_digest")
        reviewed_evidence_count = item.get("reviewed_evidence_count")
        if (
            not isinstance(unit_review_receipt, str)
            or _SHA256_RE.fullmatch(unit_review_receipt) is None
            or not isinstance(reviewed_evidence_digest, str)
            or _SHA256_RE.fullmatch(reviewed_evidence_digest) is None
            or not _is_plain_int(reviewed_evidence_count)
            or reviewed_evidence_count < 1
        ):
            return None, "unit_review_receipt"
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            return None, "evidence"
        supporting_evidence_count = 0
        for evidence_item in evidence:
            if not isinstance(evidence_item, Mapping):
                return None, "evidence_item"
            evidence_item_keys = set(evidence_item)
            if evidence_item_keys - (_OCCURRENCE_EVIDENCE_KEYS | _OCCURRENCE_EVIDENCE_CARRIER_KEYS):
                return None, "evidence_keys"
            carrier_keys = evidence_item_keys & _OCCURRENCE_EVIDENCE_CARRIER_KEYS
            if not carrier_keys or any(not _is_nonempty_string(evidence_item.get(key)) for key in carrier_keys):
                return None, "evidence_carrier"
            if "source_chunk_id" in carrier_keys and "source_id" not in carrier_keys:
                return None, "evidence_source_chunk_without_source"
            evidence_id = evidence_item.get("evidence_id")
            evidence_key = evidence_item.get("evidence_key")
            evidence_role = evidence_item.get("evidence_role")
            quote_sha256 = evidence_item.get("quote_sha256")
            evidence_review_receipt = evidence_item.get("review_receipt_digest")
            if (
                not _is_nonempty_string(evidence_id)
                or evidence_id in evidence_ids
                or not _is_nonempty_string(evidence_key)
                or evidence_key in evidence_keys
                or evidence_role != "supports"
                or not isinstance(quote_sha256, str)
                or _SHA256_RE.fullmatch(quote_sha256) is None
                or evidence_item.get("review_status") != "accepted"
                or not isinstance(evidence_review_receipt, str)
                or _SHA256_RE.fullmatch(evidence_review_receipt) is None
                or evidence_item.get("unit_review_receipt_digest") != unit_review_receipt
            ):
                return None, "evidence_receipt"
            evidence_ids.add(evidence_id)
            evidence_keys.add(evidence_key)
            supporting_evidence_count += 1
        if supporting_evidence_count < 1:
            return None, "supporting_evidence"
        if reviewed_evidence_count != supporting_evidence_count:
            return None, "reviewed_evidence_count"
    if provenance_ids != unit_ids:
        return None, "provenance_unit_ids"
    if sorted(provenance_member_keys) != counted_member_keys:
        return None, "counted_member_key_union"

    accepted_units = record.get("accepted_units")
    if not isinstance(accepted_units, Mapping) or set(accepted_units) != {
        "matching",
        "disjoint_proven",
        "relation_unknown",
    }:
        return None, "accepted_unit_partition"
    accepted_matching = accepted_units.get("matching")
    accepted_disjoint = accepted_units.get("disjoint_proven")
    accepted_unknown = accepted_units.get("relation_unknown")
    if (
        not _is_plain_int(accepted_matching)
        or accepted_matching < 0
        or not _is_plain_int(accepted_disjoint)
        or accepted_disjoint < 0
        or not _is_plain_int(accepted_unknown)
        or accepted_unknown < 0
        or accepted_matching != len(unit_ids)
    ):
        return None, "accepted_unit_partition"

    coverage = record.get("coverage")
    if not isinstance(coverage, Mapping):
        return None, "coverage"
    public_coverage_keys = {
        "id",
        "coverage_mode",
        "coverage_started_at",
        "historical_review_status",
        "complete_through",
        "review_version",
        "reviewer_id",
        "review_reason",
        "review_receipt_digest",
        "receipt_valid",
        "requested_start",
        "requested_end",
        "fully_covered",
        "legacy_gap",
    }
    if set(coverage) != public_coverage_keys:
        return None, "coverage_accounting_metadata"
    if coverage.get("coverage_mode") not in _OCCURRENCE_COVERAGE_MODES:
        return None, "coverage_mode"
    if not _is_nonempty_string(coverage.get("coverage_started_at")):
        return None, "coverage_started_at"
    if coverage.get("historical_review_status") not in _OCCURRENCE_HISTORICAL_REVIEW_STATUSES:
        return None, "historical_review_status"
    for key in ("complete_through", "requested_start", "requested_end"):
        value = coverage.get(key)
        if value is not None and not _is_nonempty_string(value):
            return None, f"coverage_{key}"
    if not isinstance(coverage.get("fully_covered"), bool):
        return None, "fully_covered"
    if not isinstance(coverage.get("legacy_gap"), bool):
        return None, "legacy_gap"
    receipt_valid = _coverage_receipt_is_valid(
        coverage,
        expected_user_id=expected_user_id,
    )
    if coverage.get("receipt_valid") is not receipt_valid:
        return None, "coverage_receipt_flag"

    unresolved_claims = record.get("unresolved_claims")
    if not isinstance(unresolved_claims, Mapping):
        return None, "unresolved_claims"
    if set(unresolved_claims) - _OCCURRENCE_UNRESOLVED_CLAIM_KEYS:
        return None, "unresolved_claim_keys"
    unresolved_count = unresolved_claims.get("count")
    if not _is_plain_int(unresolved_count) or unresolved_count < 0:
        return None, "unresolved_claim_count"
    disjoint_proven = unresolved_claims.get("disjoint_proven")
    matching_or_unknown = unresolved_claims.get("matching_or_unknown")
    if (
        not _is_plain_int(disjoint_proven)
        or disjoint_proven < 0
        or not _is_plain_int(matching_or_unknown)
        or matching_or_unknown < 0
        or disjoint_proven + matching_or_unknown != unresolved_count
    ):
        return None, "unresolved_claim_partition"
    if not isinstance(unresolved_claims.get("saturated"), bool):
        return None, "unresolved_claim_saturation"
    if not isinstance(record.get("saturated"), bool):
        return None, "saturation"
    if not isinstance(record.get("answer_sufficient"), bool):
        return None, "answer_sufficient"

    incomplete = bool(
        not coverage["fully_covered"]
        or coverage["legacy_gap"]
        or accepted_unknown
        or matching_or_unknown
        or unresolved_claims["saturated"]
        or record["saturated"]
    )
    complete_signed_coverage = bool(
        coverage["coverage_mode"] == "complete_history"
        and coverage["historical_review_status"] == "reviewed"
        and coverage["fully_covered"]
        and not coverage["legacy_gap"]
        and receipt_valid
        and _coverage_has_valid_closed_interval(coverage)
    )
    if answer_kind == "exact":
        if incomplete or not complete_signed_coverage or record["answer_sufficient"] is not True:
            return None, "unsafe_exact"
    elif answer_kind == "range":
        if (
            aggregation_basis != "event_instance"
            or not complete_signed_coverage
            or unresolved_claims["saturated"]
            or record["saturated"]
            or accepted_unknown
            or matching_or_unknown == 0
        ):
            return None, "unsafe_range"
        if record["answer_sufficient"] is not False:
            return None, "non_exact_answer_sufficient"
    else:
        if not incomplete:
            return None, "unexplained_non_exact"
        if record["answer_sufficient"] is not False:
            return None, "non_exact_answer_sufficient"
    expected_record_keys = _OCCURRENCE_AGGREGATION_KEYS | ({"count"} if answer_kind == "exact" else set())
    if set(record) != expected_record_keys:
        return None, "aggregation_keys"
    return record, None


def _selected_count_rollups(pack: Mapping[str, object]) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    memories = pack.get("relevant_memories")
    if not isinstance(memories, list):
        return selected
    for memory in memories:
        if not isinstance(memory, dict):
            continue
        count = count_bearing_rollup_member_count(memory)
        if count is None:
            continue
        selected.append({"memory_id": str(memory.get("id") or ""), "member_count": count})
    return selected


def _candidate_disclosure_is_non_oracle(candidate: Mapping[str, object] | None) -> bool:
    return bool(
        candidate is not None
        and candidate.get("is_answer") is False
        and candidate.get("supports_numeric_sum") is False
        and isinstance(candidate.get("matching_criteria"), str)
        and str(candidate.get("matching_criteria")).strip()
    )


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}


def _simple_gold_count(answer: str) -> int | None:
    """Parse only an unambiguous leading scalar for audit comparison."""
    numeric = re.match(r"\s*([0-9]+)\b", answer)
    if numeric is not None:
        return int(numeric.group(1))
    word = re.match(r"\s*([a-z]+)\b", answer.casefold())
    return _NUMBER_WORDS.get(word.group(1)) if word is not None else None


def probe_row(
    question: LongMemEvalQuestion,
    pack: Mapping[str, object],
    *,
    expected_user_id: str,
    reused_store: bool,
    accept_rollups: bool,
    ingest_seconds: float | None,
    retrieval_seconds: float,
) -> dict[str, object]:
    """Build one auditable row without treating benchmark gold as retrieval input."""
    intent = detect_aggregation_intent(question.question)
    trace_candidate = _trace_candidate_record(pack)
    reader_aggregation = _reader_aggregation_record(pack)
    count_rollups = _selected_count_rollups(pack)
    stratum = hand_audited_stratum(question.question_id)
    trace_candidate_present = trace_candidate is not None
    reader_aggregation_present = reader_aggregation is not None
    non_oracle = _candidate_disclosure_is_non_oracle(trace_candidate)
    audited_answerable = stratum == STRATUM_CANDIDATE_COUNT
    gold_count = _simple_gold_count(question.answer) if audited_answerable else None
    trace_candidate_value = trace_candidate.get("count") if trace_candidate is not None else None
    trace_candidate_matches_gold = (
        trace_candidate_value == gold_count
        if isinstance(trace_candidate_value, int)
        and not isinstance(trace_candidate_value, bool)
        and gold_count is not None
        else None
    )
    (
        reader_verified_occurrence_aggregation,
        reader_aggregation_contract_error,
    ) = _validate_occurrence_reader_aggregation(
        reader_aggregation,
        expected_user_id=expected_user_id,
    )
    reader_answer_kind = (
        str(reader_verified_occurrence_aggregation["answer_kind"])
        if reader_verified_occurrence_aggregation is not None
        else None
    )
    reader_exact_count_matches_gold = (
        reader_verified_occurrence_aggregation.get("count") == gold_count
        if reader_verified_occurrence_aggregation is not None
        and reader_answer_kind == "exact"
        and gold_count is not None
        else None
    )
    safe_non_emission = not trace_candidate_present and not reader_aggregation_present
    safe_abstention_non_answer = bool(stratum == STRATUM_CADENCE_ABSTENTION and safe_non_emission)

    if stratum == STRATUM_NUMERIC_SAFE_NON_EMISSION:
        mechanism_expectation_met = bool(intent is not None and intent.sub_intent == COUNT_SUB_INTENT_NUMERIC_VALUE)
        safety_expectation_met = safe_non_emission
    elif stratum == STRATUM_REJECTED_GATE_WIDENING:
        mechanism_expectation_met = intent is None
        safety_expectation_met = safe_non_emission
    elif stratum in {STRATUM_CADENCE_ANSWERABLE, STRATUM_CADENCE_ABSTENTION}:
        mechanism_expectation_met = bool(intent is not None and intent.sub_intent == COUNT_SUB_INTENT_CADENCE)
        safety_expectation_met = safe_non_emission
    elif audited_answerable:
        mechanism_expectation_met = bool(
            supports_candidate_instance_count(intent) and trace_candidate_present and non_oracle
        )
        safety_expectation_met = None
    else:
        # Detector-only rows are measurement, not silently promoted into the
        # hand-audited release gate.
        mechanism_expectation_met = None
        safety_expectation_met = None

    if not audited_answerable:
        answer_sufficiency = "not_applicable"
    elif reader_verified_occurrence_aggregation is not None:
        if reader_answer_kind == "range":
            answer_sufficiency = "verified_occurrence_range_not_exact_answer"
        elif reader_answer_kind == "at_least":
            answer_sufficiency = "verified_occurrence_at_least_not_exact_answer"
        elif reader_verified_occurrence_aggregation["answer_sufficient"] is not True:
            answer_sufficiency = "verified_occurrence_aggregation_not_answer_sufficient"
        elif reader_exact_count_matches_gold:
            answer_sufficiency = "verified_occurrence_aggregation_matches_dev_gold"
        else:
            answer_sufficiency = "verified_occurrence_aggregation_mismatches_dev_gold"
    elif reader_aggregation_present:
        answer_sufficiency = "invalid_reader_aggregation_not_an_answer"
    elif count_rollups:
        answer_sufficiency = "selected_unverified_count_rollup_not_an_answer"
    elif trace_candidate_present:
        answer_sufficiency = "trace_candidate_statistic_only_not_an_answer"
    else:
        answer_sufficiency = "no_answer_sufficient_aggregate"

    trace = pack.get("trace")
    trace_mapping = trace if isinstance(trace, Mapping) else {}
    memories = pack.get("relevant_memories")
    return {
        "schema": COUNT_PROBE_SCHEMA,
        "question_id": question.question_id,
        "question_type": question.question_type,
        "is_abstention": question.is_abstention,
        "question": question.question,
        "gold_answer_for_measurement_only": question.answer,
        "parsed_gold_count_for_measurement_only": gold_count,
        "answer_session_count_for_measurement_only": len(question.answer_session_ids),
        "hand_audited_stratum": stratum,
        "detector_kind": intent.kind if intent is not None else None,
        "detector_trigger": intent.trigger if intent is not None else None,
        "detector_sub_intent": intent.sub_intent if intent is not None else None,
        "trace_candidate_count_present": trace_candidate_present,
        "trace_candidate_count": trace_candidate,
        "trace_candidate_disclosure_is_non_oracle": non_oracle,
        "trace_candidate_count_matches_dev_gold": trace_candidate_matches_gold,
        "reader_aggregation_present": reader_aggregation_present,
        # Invalid producer payloads are never copied into the durable report.
        "reader_aggregation": reader_verified_occurrence_aggregation,
        "reader_aggregation_contract_valid": (reader_verified_occurrence_aggregation is not None),
        "reader_aggregation_contract_error": reader_aggregation_contract_error,
        "reader_aggregation_answer_kind": reader_answer_kind,
        "selected_count_bearing_rollups": count_rollups,
        "reader_verified_occurrence_aggregation": (reader_verified_occurrence_aggregation),
        "reader_exact_count_matches_dev_gold": reader_exact_count_matches_gold,
        "safe_non_emission": safe_non_emission,
        "safe_abstention_non_answer": safe_abstention_non_answer,
        "mechanism_expectation_met": mechanism_expectation_met,
        "safety_expectation_met": safety_expectation_met,
        "answer_sufficiency": answer_sufficiency,
        "selected_memory_count": len(memories) if isinstance(memories, list) else 0,
        "vector_stage": str(trace_mapping.get("vector_stage", "unknown")),
        "reused_store": reused_store,
        "accept_rollups": accept_rollups,
        "ingest_seconds": round(ingest_seconds, 3) if ingest_seconds is not None else None,
        "retrieval_seconds": round(retrieval_seconds, 3),
    }


def probe_question(
    question: LongMemEvalQuestion,
    *,
    work_dir: Path,
    dataset_path: Path,
    max_items: int,
    accept_rollups: bool,
) -> dict[str, object]:
    db_path = _db_path_for(work_dir, question.question_id)
    marker_path = _marker_path_for(db_path)
    reuse = db_path.is_file() and _marker_matches(
        marker_path,
        question,
        dataset_path,
        accept_rollups=accept_rollups,
    )
    if not reuse:
        marker_path.unlink(missing_ok=True)
        _cleanup_store(db_path)
    started = time.monotonic()
    ingest_seconds: float | None = None
    with question_run(question, db_path) as run:
        expected_user_id = str(run.store.user_id)
        if not reuse:
            run.ingest(accept_rollups=accept_rollups)
            ingest_seconds = time.monotonic() - started
        request = VNextRetrievalRequest(
            query=question.question,
            max_items=max_items,
            include_sources=True,
            actor_type="system",
            reference_time=parse_event_datetime(question.question_date),
        )
        retrieval_started = time.monotonic()
        pack = VNextRetrievalService(run.store).compile_context_pack(request)
        retrieval_seconds = time.monotonic() - retrieval_started
    if not reuse:
        marker_path.write_text(
            json.dumps(
                _build_ingest_marker_payload(
                    question,
                    dataset_path=dataset_path,
                    accept_rollups=accept_rollups,
                ),
                ensure_ascii=True,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return probe_row(
        question,
        pack,
        expected_user_id=expected_user_id,
        reused_store=reuse,
        accept_rollups=accept_rollups,
        ingest_seconds=ingest_seconds,
        retrieval_seconds=retrieval_seconds,
    )


def summarize_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    def summarize_bucket(bucket_rows: list[dict[str, object]]) -> dict[str, object]:
        audited = [row for row in bucket_rows if row.get("mechanism_expectation_met") is not None]
        safety_checked = [row for row in bucket_rows if row.get("safety_expectation_met") is not None]
        candidate_gold_comparisons = [
            row for row in bucket_rows if row.get("trace_candidate_count_matches_dev_gold") is not None
        ]
        answer_sufficiency_checks = [row for row in bucket_rows if row.get("answer_sufficiency") != "not_applicable"]
        return {
            "questions": len(bucket_rows),
            "audited": len(audited),
            "detected": sum(1 for row in bucket_rows if row.get("detector_kind") == AGGREGATION_KIND_COUNT),
            "with_trace_candidate_count": sum(
                1 for row in bucket_rows if row.get("trace_candidate_count_present") is True
            ),
            "with_reader_aggregation": sum(1 for row in bucket_rows if row.get("reader_aggregation_present") is True),
            "with_valid_reader_aggregation": sum(
                1 for row in bucket_rows if row.get("reader_aggregation_contract_valid") is True
            ),
            "with_count_bearing_accepted_rollup": sum(
                1 for row in bucket_rows if row.get("selected_count_bearing_rollups")
            ),
            "numeric_safe_non_emissions": sum(
                1
                for row in bucket_rows
                if row.get("hand_audited_stratum") == STRATUM_NUMERIC_SAFE_NON_EMISSION
                and row.get("safety_expectation_met") is True
            ),
            "rejected_gate_widening_safe_non_emissions": sum(
                1
                for row in bucket_rows
                if row.get("hand_audited_stratum") == STRATUM_REJECTED_GATE_WIDENING
                and row.get("safety_expectation_met") is True
            ),
            "safe_abstention_non_answers": sum(
                1 for row in bucket_rows if row.get("safe_abstention_non_answer") is True
            ),
            "cadence_safe_non_emissions": sum(
                1
                for row in bucket_rows
                if row.get("hand_audited_stratum") in {STRATUM_CADENCE_ANSWERABLE, STRATUM_CADENCE_ABSTENTION}
                and row.get("safety_expectation_met") is True
            ),
            "mechanism_expectations_met": sum(1 for row in audited if row.get("mechanism_expectation_met") is True),
            "mechanism_expectations_failed": sum(1 for row in audited if row.get("mechanism_expectation_met") is False),
            "safety_checks": len(safety_checked),
            "safety_expectations_met": sum(1 for row in safety_checked if row.get("safety_expectation_met") is True),
            "safety_expectations_failed": sum(
                1 for row in safety_checked if row.get("safety_expectation_met") is False
            ),
            "trace_candidate_counts_compared_to_dev_gold": len(candidate_gold_comparisons),
            "trace_candidate_counts_matching_dev_gold": sum(
                1 for row in candidate_gold_comparisons if row.get("trace_candidate_count_matches_dev_gold") is True
            ),
            "trace_candidate_counts_mismatching_dev_gold": sum(
                1 for row in candidate_gold_comparisons if row.get("trace_candidate_count_matches_dev_gold") is False
            ),
            "answer_sufficiency_checks": len(answer_sufficiency_checks),
            "answer_sufficient_via_verified_occurrence_aggregation": sum(
                1
                for row in bucket_rows
                if row.get("answer_sufficiency") == "verified_occurrence_aggregation_matches_dev_gold"
            ),
            "valid_exact_occurrence_aggregations": sum(
                1
                for row in bucket_rows
                if row.get("reader_aggregation_contract_valid") is True
                and row.get("reader_aggregation_answer_kind") == "exact"
            ),
            "valid_occurrence_ranges": sum(
                1
                for row in bucket_rows
                if row.get("reader_aggregation_contract_valid") is True
                and row.get("reader_aggregation_answer_kind") == "range"
            ),
            "valid_occurrence_at_least_answers": sum(
                1
                for row in bucket_rows
                if row.get("reader_aggregation_contract_valid") is True
                and row.get("reader_aggregation_answer_kind") == "at_least"
            ),
        }

    by_stratum: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_stratum.setdefault(str(row["hand_audited_stratum"]), []).append(row)
    overall = summarize_bucket(rows)
    overall["answer_sufficiency_target"] = DEFAULT_ANSWER_SUFFICIENCY_TARGET
    overall["answer_sufficiency_target_met"] = bool(
        int(
            overall.get(
                "answer_sufficient_via_verified_occurrence_aggregation",
                0,
            )
        )
        >= DEFAULT_ANSWER_SUFFICIENCY_TARGET
    )
    return {
        "overall": overall,
        "by_stratum": {stratum: summarize_bucket(bucket_rows) for stratum, bucket_rows in sorted(by_stratum.items())},
    }


def exit_code_for_summary(
    summary: Mapping[str, object],
    *,
    has_errors: bool,
    expected_manifest: Mapping[str, int] | None = None,
    release_gate_eligible: bool | None = None,
) -> int:
    """Deterministic release-probe exit semantics, isolated for unit tests."""
    if has_errors:
        return EXIT_RUN_FAILURES
    if release_gate_eligible is None:
        release_gate_eligible = expected_manifest is not None
    if not release_gate_eligible or expected_manifest is None:
        return EXIT_STRATUM_FAILURES
    overall = summary.get("overall")
    if not isinstance(overall, Mapping):
        return EXIT_STRATUM_FAILURES
    required_nonzero = ("audited", "safety_checks", "answer_sufficiency_checks")
    if any(int(overall.get(key, 0)) < 1 for key in required_nonzero):
        return EXIT_STRATUM_FAILURES
    if expected_manifest is not None and any(
        int(overall.get(key, -1)) != expected for key, expected in expected_manifest.items()
    ):
        return EXIT_STRATUM_FAILURES
    if int(overall.get("mechanism_expectations_failed", 0)) or int(overall.get("safety_expectations_failed", 0)):
        return EXIT_STRATUM_FAILURES
    checks = int(overall.get("answer_sufficiency_checks", 0))
    sufficient = int(
        overall.get(
            "answer_sufficient_via_verified_occurrence_aggregation",
            0,
        )
    )
    if checks > 0 and sufficient < DEFAULT_ANSWER_SUFFICIENCY_TARGET:
        return EXIT_STRATUM_FAILURES
    return EXIT_OK


def _load_question_ids(path: Path) -> list[str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[count] cannot read question-id file: {exc}", file=sys.stderr)
        return None
    return [line for raw_line in text.splitlines() if (line := raw_line.strip()) and not line.startswith("#")]


def question_id_manifest_sha256(question_ids: Sequence[str]) -> str:
    """Digest an exact, ordered question-id manifest including its final LF."""
    return hashlib.sha256(("\n".join(question_ids) + "\n").encode("utf-8")).hexdigest()


def is_governed_audit_manifest(path: Path, question_ids: Sequence[str]) -> bool:
    """Require both the checked-in path and its frozen ordered content."""
    return bool(
        path.resolve() == DEFAULT_SLICE.resolve()
        and len(question_ids) == GOVERNED_AUDIT_QUESTION_COUNT
        and question_id_manifest_sha256(question_ids) == GOVERNED_AUDIT_MANIFEST_SHA256
    )


def count_release_input_checks(
    *,
    dataset_path: Path,
    dataset_sha256: str,
    question_id_file: Path,
    question_ids: Sequence[str],
    limit: int | None,
    max_items: int,
    with_vectors: bool,
    with_reranker: bool,
    accept_rollups: bool,
) -> dict[str, bool]:
    return {
        "dataset_path_matches": dataset_path.resolve() == GOVERNED_DATASET_PATH.resolve(),
        "dataset_sha256_matches": dataset_sha256 == GOVERNED_DATASET_SHA256,
        "question_manifest_matches": is_governed_audit_manifest(
            question_id_file,
            question_ids,
        ),
        "limit_disabled": limit is None,
        "max_items_matches": max_items == GOVERNED_MAX_ITEMS,
        "vectors_disabled": not with_vectors,
        "reranker_disabled": not with_reranker,
        "rollups_disabled": not accept_rollups,
    }


def default_output_path(dataset_path: Path, *, accept_rollups: bool) -> Path:
    mode = "rollups_on" if accept_rollups else "rollups_off"
    return RESULTS_DIR / f"count_probe_{dataset_path.stem}_{mode}.jsonl"


def expected_audit_manifest(question_ids: Path) -> Mapping[str, int] | None:
    """Return the governed audit only when path and frozen content both match."""
    loaded = _load_question_ids(question_ids)
    if loaded is None:
        return None
    return DEFAULT_AUDIT_MANIFEST if is_governed_audit_manifest(question_ids, loaded) else None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="count_probe.py",
        description=("Keyless evidence-bearing occurrence-count context-pack probe for count-intent questions."),
    )
    parser.add_argument("--dataset-file", type=Path, default=None)
    parser.add_argument(
        "--question-ids",
        type=Path,
        default=DEFAULT_SLICE,
        help="one question_id per line (default: fixed stage1-150 slice, comments ignored)",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--accept-rollups",
        action="store_true",
        help="deterministically build/accept roll-up cards during ingest (default: off)",
    )
    parser.add_argument("--with-vectors", action="store_true")
    parser.add_argument("--with-reranker", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.with_vectors:
        disable_embeddings_env()
    if not args.with_reranker:
        disable_reranker_env()

    dataset_path = args.dataset_file if args.dataset_file is not None else resolve_dataset_path("s")
    if dataset_path is None or not dataset_path.is_file():
        print("[count] dataset not found; pass --dataset-file", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    dataset_sha256 = file_sha256(dataset_path)
    try:
        questions = load_dataset(dataset_path)
    except LongMemEvalDatasetError as exc:
        print(f"[count] {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    question_ids = _load_question_ids(args.question_ids)
    if question_ids is None:
        return EXIT_CONFIG_ERROR
    expected_manifest = DEFAULT_AUDIT_MANIFEST if is_governed_audit_manifest(args.question_ids, question_ids) else None
    wanted = set(question_ids)
    selected = [question for question in questions if question.question_id in wanted]
    missing = wanted - {question.question_id for question in selected}
    if missing:
        print(
            f"[count] requested ids missing from dataset: {sorted(missing)[:5]}",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    # Keep all hand-audited rows, plus detector-positive rows for measurement.
    selected = [
        question
        for question in selected
        if hand_audited_stratum(question.question_id) != STRATUM_DETECTOR_ONLY
        or (
            (intent := detect_aggregation_intent(question.question)) is not None
            and intent.kind == AGGREGATION_KIND_COUNT
        )
    ]
    if args.limit is not None:
        selected = selected[: args.limit]
    if not selected:
        print("[count] no count-intent questions selected", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    selected_question_ids = [question.question_id for question in selected]

    max_items = args.max_items if args.max_items is not None else max_items_from_env()
    release_input_checks = count_release_input_checks(
        dataset_path=dataset_path,
        dataset_sha256=dataset_sha256,
        question_id_file=args.question_ids,
        question_ids=question_ids,
        limit=args.limit,
        max_items=max_items,
        with_vectors=args.with_vectors,
        with_reranker=args.with_reranker,
        accept_rollups=args.accept_rollups,
    )
    release_candidate = all(release_input_checks.values())
    args.work_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out or default_output_path(
        dataset_path,
        accept_rollups=args.accept_rollups,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vectors = "ambient" if args.with_vectors else "disabled"
    reranker = "ambient" if args.with_reranker else "disabled"
    print(
        f"[count] dataset={dataset_path.name} questions={len(selected)} max_items={max_items} "
        f"vectors={vectors} reranker={reranker} gate={'release-candidate' if release_candidate else 'diagnostic'} "
        f"work_dir={args.work_dir} workers={max(1, args.workers)} accept_rollups={args.accept_rollups}"
    )

    rows_by_id: dict[str, dict[str, object]] = {}
    errors: list[tuple[str, str]] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                probe_question,
                question,
                work_dir=args.work_dir,
                dataset_path=dataset_path,
                max_items=max_items,
                accept_rollups=args.accept_rollups,
            ): question
            for question in selected
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            question = futures[future]
            try:
                rows_by_id[question.question_id] = future.result()
            except Exception as exc:  # noqa: BLE001 - report every question independently
                errors.append((question.question_id, f"{type(exc).__name__}: {exc}"))
                print(
                    f"[count] {question.question_id} ERROR: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
            if completed % 25 == 0 or completed == len(selected):
                print(f"[count] {completed}/{len(selected)} probed", flush=True)

    rows = [rows_by_id[question.question_id] for question in selected if question.question_id in rows_by_id]
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")

    summary = summarize_rows(rows)
    all_stores_fresh = all_probe_stores_fresh(
        rows,
        expected_count=len(selected_question_ids),
    )
    release_eligible = bool(release_candidate and all_stores_fresh)
    exit_code = exit_code_for_summary(
        summary,
        has_errors=bool(errors),
        expected_manifest=expected_manifest,
        release_gate_eligible=release_eligible,
    )
    release_gate = {
        "mode": "release" if release_eligible else "diagnostic",
        "eligible": release_eligible,
        "governed_question_id_file": str(DEFAULT_SLICE),
        "governed_question_id_count": GOVERNED_AUDIT_QUESTION_COUNT,
        "governed_question_id_manifest_sha256": GOVERNED_AUDIT_MANIFEST_SHA256,
        "requested_manifest_matches": expected_manifest is not None,
        "limit_applied": args.limit is not None,
        "input_checks": release_input_checks,
        "all_stores_fresh": all_stores_fresh,
        "reused_store_count": sum(1 for row in rows if row.get("reused_store") is True),
        "required_vectors": "disabled",
        "required_reranker": "disabled",
        "governed_dataset_path": str(GOVERNED_DATASET_PATH),
        "governed_dataset_sha256": GOVERNED_DATASET_SHA256,
        "required_max_items": GOVERNED_MAX_ITEMS,
        "required_accept_rollups": False,
        "vectors": vectors,
        "reranker": reranker,
        "answer_sufficiency_target": DEFAULT_ANSWER_SUFFICIENCY_TARGET,
        "answer_sufficiency_checks": DEFAULT_AUDIT_MANIFEST["answer_sufficiency_checks"],
        "passed": exit_code == EXIT_OK,
    }
    summary_path = out_path.with_suffix(".summary.json")
    summary_payload = {
        "schema": COUNT_PROBE_SCHEMA + "_summary",
        "dataset_file": dataset_path.name,
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha256,
        "dataset_sha256_prefix": _sha256_prefix(dataset_path),
        "question_id_file": str(args.question_ids),
        "question_id_manifest_count": len(question_ids),
        "question_id_manifest_sha256": question_id_manifest_sha256(question_ids),
        "selected_question_id_count": len(selected_question_ids),
        "selected_question_id_manifest_sha256": question_id_manifest_sha256(selected_question_ids),
        "limit": args.limit,
        "max_items": max_items,
        "vectors": vectors,
        "reranker": reranker,
        **provider_summary_metadata(),
        "accept_rollups": args.accept_rollups,
        "questions": len(rows),
        "errors": [{"question_id": question_id, "error": error} for question_id, error in errors],
        "release_gate": release_gate,
        **summary,
    }
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"[count] done in {time.monotonic() - started:.1f}s rows={out_path} summary={summary_path}")
    if not release_eligible and not errors:
        print(
            "[count] diagnostic run only; release-green requires the canonical dataset, exact governed "
            "stage1-150 manifest, max_items=16, fresh stores, no rollups/limit, and disabled providers",
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COUNT_PROBE_SCHEMA",
    "DEFAULT_ANSWER_SUFFICIENCY_TARGET",
    "DEFAULT_SLICE",
    "DEFAULT_AUDIT_MANIFEST",
    "DEFAULT_WORK_DIR",
    "GOVERNED_AUDIT_MANIFEST_SHA256",
    "GOVERNED_AUDIT_QUESTION_COUNT",
    "EXIT_CONFIG_ERROR",
    "EXIT_OK",
    "EXIT_RUN_FAILURES",
    "EXIT_STRATUM_FAILURES",
    "STRATUM_CADENCE_ABSTENTION",
    "STRATUM_CADENCE_ANSWERABLE",
    "STRATUM_CANDIDATE_COUNT",
    "STRATUM_DETECTOR_ONLY",
    "STRATUM_NUMERIC_SAFE_NON_EMISSION",
    "STRATUM_REJECTED_GATE_WIDENING",
    "build_arg_parser",
    "count_release_input_checks",
    "default_output_path",
    "expected_audit_manifest",
    "exit_code_for_summary",
    "hand_audited_stratum",
    "is_governed_audit_manifest",
    "main",
    "probe_question",
    "probe_row",
    "question_id_manifest_sha256",
    "summarize_rows",
]
