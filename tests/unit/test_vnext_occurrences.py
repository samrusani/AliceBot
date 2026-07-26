from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import UUID

import pytest

from alicebot_api.vnext_occurrences import (
    build_occurrence_aggregation,
    build_occurrence_proposal,
    normalize_count_key,
)
from alicebot_api.vnext_occurrence_predicates import (
    OCCURRENCE_AGGREGATION_SCHEMA,
    occurrence_coverage_review_receipt_digest,
    occurrence_evidence_facts_digest,
    occurrence_evidence_review_receipt_digest,
    occurrence_unit_review_receipt_digest,
)
from alicebot_api.vnext_occurrence_taxonomy import build_occurrence_predicate_atom


_ACCOUNTING_SOURCE_ID = "11111111-1111-4111-8111-111111111111"
_ACCOUNTING_CHUNK_ID = "22222222-2222-4222-8222-222222222222"
_ACCOUNTING_DISPOSITION_ID = "33333333-3333-4333-8333-333333333333"
_ACCOUNTING_EXTRACTOR_VERSION = "phase6-aggregation-test-v1"


def _predicate() -> dict[str, object]:
    return build_occurrence_predicate_atom(
        action="serviced",
        object_leaf="bike",
    )


def _claim_aggregation() -> dict[str, object]:
    return {
        "schema": OCCURRENCE_AGGREGATION_SCHEMA,
        "bases": [
            {
                "basis": "event_instance",
                "identity_basis": "occurrence_key",
            }
        ],
    }


def _object_member_identity(label: str) -> str:
    return f"object:v1:{sha256(label.encode()).hexdigest()}"


def _unit_aggregation(
    occurrence_key: str,
    *,
    object_member_identity: str | None = None,
    object_member_identities: tuple[str, ...] = (),
) -> dict[str, object]:
    reviewed_object_members = sorted(
        {
            *object_member_identities,
            *((object_member_identity,) if object_member_identity is not None else ()),
        }
    )
    members = [
        {
            "basis": "event_instance",
            "identity_basis": "occurrence_key",
            "member_identity": occurrence_key,
        }
    ]
    members.extend(
        [
            {
                "basis": "object_member",
                "identity_basis": "reviewed_stable_object_v1",
                "member_identity": reviewed_object_member,
            }
            for reviewed_object_member in reviewed_object_members
        ]
    )
    return {
        "schema": OCCURRENCE_AGGREGATION_SCHEMA,
        "members": members,
    }


def _accounting_metadata() -> dict[str, object]:
    return {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": _ACCOUNTING_EXTRACTOR_VERSION,
        "source_ids": [_ACCOUNTING_SOURCE_ID],
        "source_chunk_ids": [_ACCOUNTING_CHUNK_ID],
        "snapshot_digest": "a" * 64,
        "disposition_digest": "b" * 64,
    }


def _accounting_summary(
    coverage: dict[str, object],
    units: list[dict[str, object]],
) -> dict[str, object]:
    metadata = coverage.get("metadata_json")
    assert isinstance(metadata, dict)
    return {
        "extractor_version": metadata["extractor_version"],
        "source_ids": metadata["source_ids"],
        "source_chunk_ids": metadata["source_chunk_ids"],
        "current_chunk_count": 1,
        "reviewed_current_count": 1,
        "missing_count": 0,
        "stale_count": 0,
        "unresolved_count": 0,
        "unreviewed_count": 0,
        "invalid_accepted_count": 0,
        "invalid_receipt_count": 0,
        "unanchored_memory_count": 0,
        "unanchored_memory_ids": [],
        "accounted_memory_count": 0,
        "accounted_memory_ids": [],
        "snapshot_digest": metadata["snapshot_digest"],
        "disposition_digest": metadata["disposition_digest"],
        "complete": True,
        "items": [
            {
                "source_id": _ACCOUNTING_SOURCE_ID,
                "source_chunk_id": _ACCOUNTING_CHUNK_ID,
                "snapshot_sha256": "c" * 64,
                "disposition_id": _ACCOUNTING_DISPOSITION_ID,
                "disposition": "accepted_occurrences",
                "review_status": "accepted",
                "review_version": 1,
                "predicate_keys": _predicate()["selector_keys"],
                "claim_ids": sorted({str(unit["claim_id"]) for unit in units}),
                "occurrence_ids": sorted(str(unit["id"]) for unit in units),
                "status": "complete",
            }
        ],
    }


def _proposal(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "canonical_text": "I serviced the blue bike on March 3.",
        "count_key": "Bike Service",
        "predicate_json": build_occurrence_predicate_atom(
            action="serviced",
            object_leaf="bike",
        ),
        "aggregation_json": {
            "schema": OCCURRENCE_AGGREGATION_SCHEMA,
            "bases": [
                {
                    "basis": "event_instance",
                    "identity_basis": "occurrence_key",
                }
            ],
        },
        "domain": "work",
        "sensitivity": "private",
        "project_scope": ("garage", "maintenance"),
        "occurred_at_start": "2026-03-03T10:00:00Z",
        "occurred_at_end": "2026-03-03T11:00:00Z",
        "stable_object": "blue bike",
        "memory_id": "memory-1",
        "source_id": "source-1",
        "source_chunk_id": "chunk-1",
    }
    kwargs.update(overrides)
    return build_occurrence_proposal(**kwargs)  # type: ignore[arg-type]


def _evidence_digest(rows: list[dict[str, object]]) -> str:
    canonical = "|".join(
        occurrence_evidence_facts_digest(row)
        for row in sorted(
            rows,
            key=lambda row: (str(row["evidence_key"]), str(row["id"])),
        )
    )
    return sha256(canonical.encode()).hexdigest()


def _resign_reviewed_unit(
    unit: dict[str, object],
    evidence_rows: list[dict[str, object]],
) -> None:
    evidence_digest = _evidence_digest(evidence_rows)
    unit["reviewed_evidence_count"] = len(evidence_rows)
    unit["reviewed_evidence_digest"] = evidence_digest
    unit_receipt = occurrence_unit_review_receipt_digest(
        unit,
        action=str(unit["review_receipt_action"]),
        reviewer_id=str(unit["reviewer_id"]),
        reason=str(unit["review_reason"]),
        review_version=int(unit["review_version"]),
        evidence_digest=evidence_digest,
    )
    unit["review_receipt_digest"] = unit_receipt
    for evidence_row in evidence_rows:
        evidence_row["unit_review_receipt_digest"] = unit_receipt
        evidence_row["review_receipt_digest"] = occurrence_evidence_review_receipt_digest(
            evidence_row,
            action=str(evidence_row["review_receipt_action"]),
            reviewer_id=str(evidence_row["reviewer_id"]),
            reason=str(evidence_row["review_reason"]),
            unit_review_receipt_digest=unit_receipt,
        )


def _signed_rows(
    count: int = 2,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    units: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for index in range(1, count + 1):
        occurrence_id = f"occurrence-{index}"
        occurrence_key = f"occurrence-key-{index}"
        quote = f"event {index}"
        evidence_row: dict[str, object] = {
            "id": f"evidence-{index}",
            "user_id": "user-1",
            "claim_id": f"claim-{index}",
            "occurrence_id": occurrence_id,
            "evidence_key": f"evidence-key-{index}",
            "evidence_role": "supports",
            "quote": quote,
            "quote_sha256": sha256(quote.encode()).hexdigest(),
            "review_status": "accepted",
            "review_receipt_action": "accepted",
            "reviewer_id": "reviewer-1",
            "review_reason": "reviewed occurrence evidence",
            "memory_id": f"memory-{index}",
            "source_id": _ACCOUNTING_SOURCE_ID,
            "source_chunk_id": _ACCOUNTING_CHUNK_ID,
        }
        review_reason = "reviewed occurrence"
        unit: dict[str, object] = {
            "id": occurrence_id,
            "user_id": "user-1",
            "claim_id": f"claim-{index}",
            "claim_ordinal": 1,
            "occurrence_key": occurrence_key,
            "count_key": "bike service",
            "canonical_text": f"I serviced bike event {index}.",
            "unit_value": 1,
            "review_status": "accepted",
            "identity_status": "resolved",
            "ambiguity_group_key": None,
            "predicate_json": _predicate(),
            "aggregation_json": _unit_aggregation(occurrence_key),
            "review_version": 1,
            "review_receipt_action": "accepted",
            "reviewer_id": "reviewer-1",
            "review_reason": review_reason,
            "occurred_at_start": f"2026-03-{index:02d}T10:00:00Z",
            "occurred_at_end": f"2026-03-{index:02d}T11:00:00Z",
            "domain": "work",
            "sensitivity": "private",
            "project_scope": ["garage"],
        }
        _resign_reviewed_unit(unit, [evidence_row])
        units.append(unit)
        evidence.append(evidence_row)
    return units, evidence


def _coverage(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "coverage-1",
        "user_id": "user-1",
        "coverage_mode": "complete_history",
        "coverage_started_at": "2026-01-01T00:00:00Z",
        "historical_review_status": "reviewed",
        "complete_through": "2026-12-31T23:59:59Z",
        "review_version": 1,
        "reviewer_id": "reviewer-1",
        "review_reason": "Reviewed occurrence history coverage.",
    }
    row.update(overrides)
    accounting = _accounting_metadata() if row["coverage_mode"] == "complete_history" else None
    row.setdefault("metadata_json", accounting or {})

    def canonical_timestamp(value: object) -> str | None:
        if value is None:
            return None
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

    row.setdefault(
        "review_receipt_digest",
        occurrence_coverage_review_receipt_digest(
            coverage_id=row["id"],
            user_id=row["user_id"],
            review_version=int(row["review_version"]),
            coverage_mode=str(row["coverage_mode"]),
            coverage_started_at=canonical_timestamp(row["coverage_started_at"]),
            historical_review_status=str(row["historical_review_status"]),
            complete_through=canonical_timestamp(row.get("complete_through")),
            reviewer_id=str(row["reviewer_id"]),
            reason=str(row["review_reason"]),
            accounting_metadata=accounting,
        ),
    )
    return row


def _unresolved(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "unresolved-1",
        "user_id": "user-1",
        "claim_key": "unresolved-claim-1",
        "count_key": "bike service",
        "canonical_text": "I may have serviced the bike.",
        "predicate_json": _predicate(),
        "aggregation_json": _claim_aggregation(),
        "quantity_min": 1,
        "quantity_max": 1,
        "range_kind": "exact",
        "resolution_decision": "ambiguous",
        "resolution_status": "pending",
        "identity_basis": "ambiguous",
        "resolved_occurrence_id": None,
        "review_status": "candidate",
        "domain": "work",
        "sensitivity": "private",
        "project_scope": ["garage"],
        "occurred_at_start": "2026-03-10T10:00:00Z",
        "occurred_at_end": "2026-03-10T11:00:00Z",
    }
    row.update(overrides)
    return row


def _aggregate(
    *,
    units: list[dict[str, object]],
    evidence: list[dict[str, object]],
    coverage: dict[str, object] | None,
    **kwargs: object,
) -> dict[str, object] | None:
    predicate = _predicate()
    contract: dict[str, object] = {
        "query_selector_keys": tuple(predicate["selector_keys"]),
        "query_predicates": (predicate,),
    }
    if coverage is not None and coverage.get("coverage_mode") == "complete_history":
        contract["accounting_summary"] = _accounting_summary(coverage, units)
    contract.update(kwargs)
    return build_occurrence_aggregation(
        units=units,
        evidence=evidence,
        coverage=coverage,
        **contract,  # type: ignore[arg-type]
    )


def test_normalize_count_key_is_unicode_and_whitespace_stable() -> None:
    assert normalize_count_key("  BIKE—Services \u00a0 ") == "bike services"
    assert normalize_count_key("Ｂｉｋｅ services") == "bike services"
    with pytest.raises(ValueError, match="letter or number"):
        normalize_count_key("---")


def test_proposal_uses_strong_time_identity_and_is_order_stable() -> None:
    first = _proposal(project_scope=("maintenance", "garage"))
    second = _proposal(project_scope=("garage", "maintenance"))

    assert first == second
    assert first["identity_basis"] == "exact_time"
    assert first["resolution_decision"] == "new"
    assert first["range_kind"] == "exact"
    unit = first["unit_proposals"]
    assert isinstance(unit, list) and len(unit) == 1
    assert unit[0]["unit_value"] == 1


def test_proposal_requires_namespaced_external_identity() -> None:
    ambiguous = _proposal(
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="event-42",
    )
    strong = _proposal(
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="event-42",
        external_event_namespace="calendar:work",
    )

    assert ambiguous["identity_basis"] == "ambiguous"
    assert ambiguous["resolution_decision"] == "ambiguous"
    assert ambiguous["unit_proposals"] == []
    assert strong["identity_basis"] == "external_event_id"
    assert strong["resolution_decision"] == "new"


def test_proposal_expands_explicit_plural_into_one_value_units() -> None:
    proposal = _proposal(quantity_min=3, quantity_max=3)
    units = proposal["unit_proposals"]
    evidence = proposal["evidence_proposals"]

    assert isinstance(units, list)
    assert isinstance(evidence, list)
    assert [unit["claim_ordinal"] for unit in units] == [1, 2, 3]
    assert {unit["unit_value"] for unit in units} == {1}
    assert len({unit["occurrence_key"] for unit in units}) == 3
    assert len(evidence) == 3
    assert len({item["evidence_key"] for item in evidence}) == 3


def test_proposal_projects_reviewed_objects_only_for_one_exact_event() -> None:
    first = f"object:v1:{'a' * 64}"
    second = f"object:v1:{'b' * 64}"
    proposal = _proposal(
        aggregation_json={
            "schema": OCCURRENCE_AGGREGATION_SCHEMA,
            "bases": [
                {
                    "basis": "event_instance",
                    "identity_basis": "occurrence_key",
                },
                {
                    "basis": "object_member",
                    "identity_basis": "reviewed_stable_object_v1",
                },
            ],
        },
        object_member_identities=(second, first),
    )

    units = proposal["unit_proposals"]
    assert isinstance(units, list) and len(units) == 1
    members = units[0]["aggregation_json"]["members"]
    assert [member["member_identity"] for member in members] == [
        units[0]["occurrence_key"],
        first,
        second,
    ]


@pytest.mark.parametrize(
    ("quantity_min", "quantity_max"),
    [
        (2, 2),
        (1, 2),
        (1, None),
    ],
)
def test_proposal_rejects_object_projection_for_multi_or_unbounded_events(
    quantity_min: int,
    quantity_max: int | None,
) -> None:
    with pytest.raises(ValueError, match="one exact event"):
        _proposal(
            object_member_identities=(f"object:v1:{'a' * 64}",),
            quantity_min=quantity_min,
            quantity_max=quantity_max,
        )


@pytest.mark.parametrize(
    "object_members",
    [
        (f"object:v1:{'a' * 64}", f"object:v1:{'a' * 64}"),
        (f"object:v1:{'A' * 64}",),
        ("object:v1:not-a-digest",),
        (42,),
        tuple(f"object:v1:{index:064x}" for index in range(32)),
    ],
)
def test_proposal_rejects_noncanonical_object_members_before_ambiguous_resolution(
    object_members: tuple[object, ...],
) -> None:
    with pytest.raises(ValueError):
        _proposal(
            occurred_at_start=None,
            occurred_at_end=None,
            stable_object=None,
            object_member_identities=object_members,
        )


def test_proposal_links_only_an_exact_scope_compatible_identity() -> None:
    created = _proposal()
    unit = created["unit_proposals"]
    assert isinstance(unit, list) and len(unit) == 1
    existing = {
        **unit[0],
        "id": "existing-1",
        "review_status": "accepted",
        "identity_status": "resolved",
        "superseded_by": None,
        "retired_at": None,
    }

    linked = _proposal(existing_occurrence=existing)
    wrong_scope = _proposal(
        existing_occurrence={**existing, "project_scope": ["other"]},
    )
    wrong_count_key = _proposal(
        existing_occurrence={**existing, "count_key": "visited museum"},
    )

    assert linked["resolution_decision"] == "link_existing"
    assert linked["resolved_occurrence_id"] == "existing-1"
    assert linked["unit_proposals"] == []
    assert wrong_scope["resolution_decision"] == "ambiguous"
    assert wrong_scope["unit_proposals"] == []
    assert wrong_count_key["resolution_decision"] == "ambiguous"
    assert wrong_count_key["resolved_occurrence_id"] is None
    assert wrong_count_key["unit_proposals"] == []


def test_supersession_receipt_binds_the_normalized_successor() -> None:
    units, evidence = _signed_rows(1)
    unit = units[0]
    evidence_digest = _evidence_digest(evidence)
    successor_b = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    successor_c = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

    receipt_b = occurrence_unit_review_receipt_digest(
        {**unit, "superseded_by": successor_b},
        action="superseded",
        reviewer_id="reviewer-1",
        reason="A verified successor replaces this occurrence.",
        review_version=2,
        evidence_digest=evidence_digest,
    )
    receipt_b_canonical = occurrence_unit_review_receipt_digest(
        {**unit, "superseded_by": successor_b.casefold()},
        action="superseded",
        reviewer_id="reviewer-1",
        reason="A verified successor replaces this occurrence.",
        review_version=2,
        evidence_digest=evidence_digest,
    )
    receipt_c = occurrence_unit_review_receipt_digest(
        {**unit, "superseded_by": successor_c},
        action="superseded",
        reviewer_id="reviewer-1",
        reason="A verified successor replaces this occurrence.",
        review_version=2,
        evidence_digest=evidence_digest,
    )

    assert receipt_b == receipt_b_canonical
    assert receipt_b != receipt_c
    with pytest.raises(
        ValueError,
        match="requires superseded_by",
    ):
        occurrence_unit_review_receipt_digest(
            unit,
            action="superseded",
            reviewer_id="reviewer-1",
            reason="A verified successor replaces this occurrence.",
            review_version=2,
            evidence_digest=evidence_digest,
        )


def test_strong_event_identity_excludes_predicate_wording_but_incompatible_atom_fails_closed() -> None:
    buy = _proposal(
        canonical_text="I bought the ring.",
        count_key="buy ring",
        predicate_json=build_occurrence_predicate_atom(
            action="buy",
            object_leaf="ring",
        ),
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="checkout-42",
        external_event_namespace="orders:test",
    )
    buy_units = buy["unit_proposals"]
    assert isinstance(buy_units, list) and len(buy_units) == 1
    existing = {
        **buy_units[0],
        "id": "existing-buy",
        "review_status": "accepted",
        "identity_status": "resolved",
        "superseded_by": None,
        "retired_at": None,
    }

    purchase = _proposal(
        canonical_text="I purchased the ring.",
        count_key="purchase ring",
        predicate_json=build_occurrence_predicate_atom(
            action="purchase",
            object_leaf="ring",
        ),
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="checkout-42",
        external_event_namespace="orders:test",
    )
    purchase_units = purchase["unit_proposals"]
    assert isinstance(purchase_units, list) and len(purchase_units) == 1
    assert purchase_units[0]["occurrence_key"] == buy_units[0]["occurrence_key"]

    collision = _proposal(
        canonical_text="I purchased the ring.",
        count_key="purchase ring",
        predicate_json=build_occurrence_predicate_atom(
            action="purchase",
            object_leaf="ring",
        ),
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="checkout-42",
        external_event_namespace="orders:test",
        existing_occurrence=existing,
    )
    distinct = _proposal(
        canonical_text="I bought the ring again.",
        count_key="buy ring",
        predicate_json=build_occurrence_predicate_atom(
            action="buy",
            object_leaf="ring",
        ),
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="checkout-43",
        external_event_namespace="orders:test",
    )

    assert collision["resolution_decision"] == "ambiguous"
    assert collision["unit_proposals"] == []
    assert distinct["unit_proposals"][0]["occurrence_key"] != buy_units[0]["occurrence_key"]


def test_proposal_never_links_a_candidate_retired_or_date_only_collision() -> None:
    created = _proposal()
    units = created["unit_proposals"]
    assert isinstance(units, list) and len(units) == 1
    live = {
        **units[0],
        "id": "existing-1",
        "review_status": "accepted",
        "identity_status": "resolved",
        "superseded_by": None,
        "retired_at": None,
    }

    for stale in (
        {**live, "review_status": "candidate"},
        {**live, "review_status": "retired", "retired_at": "2026-03-04T00:00:00Z"},
    ):
        proposal = _proposal(existing_occurrence=stale)
        assert proposal["resolution_decision"] == "ambiguous"
        assert proposal["unit_proposals"] == []

    date_created = _proposal(
        occurred_at_start="2026-03-03",
        occurred_at_end="2026-03-03",
        reviewed_date_ordinal=1,
    )
    date_units = date_created["unit_proposals"]
    assert isinstance(date_units, list) and len(date_units) == 1
    date_collision = _proposal(
        occurred_at_start="2026-03-03",
        occurred_at_end="2026-03-03",
        reviewed_date_ordinal=1,
        existing_occurrence={
            **date_units[0],
            "id": "date-existing",
            "review_status": "accepted",
            "identity_status": "resolved",
            "superseded_by": None,
            "retired_at": None,
        },
    )
    assert date_collision["resolution_decision"] == "ambiguous"
    assert date_collision["unit_proposals"] == []


def test_proposal_rejects_invalid_time_and_quantity() -> None:
    with pytest.raises(ValueError, match="occurred_at_start"):
        _proposal(occurred_at_start="last Tuesday")
    with pytest.raises(ValueError, match="positive integer"):
        _proposal(quantity_min=0)
    with pytest.raises(ValueError, match="must not exceed"):
        _proposal(quantity_min=1, quantity_max=1001)
    for invalid in (True, 1.5, "2"):
        with pytest.raises(ValueError, match="positive integer"):
            _proposal(quantity_min=invalid)
    for invalid in (True, 1.5, "2"):
        with pytest.raises(ValueError, match="at least quantity_min"):
            _proposal(quantity_max=invalid)


def test_proposal_identity_anchor_is_part_of_claim_key() -> None:
    first = _proposal(
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="event-1",
        external_event_namespace="calendar:work",
    )
    second = _proposal(
        occurred_at_start=None,
        occurred_at_end=None,
        stable_object=None,
        external_event_id="event-2",
        external_event_namespace="calendar:work",
    )

    assert first["claim_key"] != second["claim_key"]
    assert first["identity_anchor"] == {
        "external_event_id": "event-1",
        "external_event_namespace": "calendar:work",
    }


def test_bare_date_requires_reviewed_date_and_ordinal_identity() -> None:
    ambiguous = _proposal(
        occurred_at_start="2026-03-03",
        occurred_at_end="2026-03-03",
    )
    reviewed = _proposal(
        occurred_at_start="2026-03-03",
        occurred_at_end="2026-03-03",
        reviewed_date_ordinal=2,
    )
    different_ordinal = _proposal(
        occurred_at_start="2026-03-03",
        occurred_at_end="2026-03-03",
        reviewed_date_ordinal=3,
    )

    assert ambiguous["identity_basis"] == "ambiguous"
    assert ambiguous["unit_proposals"] == []
    assert reviewed["identity_basis"] == "date_and_ordinal"
    assert reviewed["identity_anchor"]["reviewed_date_ordinal"] == 2
    assert reviewed["resolution_decision"] == "new"
    assert reviewed["unit_proposals"][0]["occurrence_key"] != different_ordinal["unit_proposals"][0]["occurrence_key"]
    with pytest.raises(ValueError, match="positive integer"):
        _proposal(
            occurred_at_start="2026-03-03",
            occurred_at_end="2026-03-03",
            reviewed_date_ordinal=True,
        )


def test_aggregation_reconstructs_exact_count_and_signed_provenance() -> None:
    units, evidence = _signed_rows()

    aggregation = _aggregate(
        units=list(reversed(units)),
        evidence=list(reversed(evidence)),
        coverage=_coverage(),
        requested_start="2026-02-01T00:00:00Z",
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["exact"] is True
    assert aggregation["count"] == 2
    assert aggregation["lower_bound"] == 2
    assert aggregation["upper_bound"] == 2
    assert aggregation["occurrence_unit_ids"] == ["occurrence-1", "occurrence-2"]
    assert aggregation["answer_sufficient"] is True
    assert len(aggregation["provenance"]) == 2  # type: ignore[arg-type]
    assert "user_id" not in aggregation["coverage"]


def test_object_member_aggregation_counts_distinct_signed_projections() -> None:
    units, evidence = _signed_rows(3)
    blue_bike = _object_member_identity("blue bike")
    red_bike = _object_member_identity("red bike")
    projected_members = (blue_bike, blue_bike, red_bike)
    for unit, evidence_row, object_member in zip(
        units,
        evidence,
        projected_members,
        strict=True,
    ):
        unit["aggregation_json"] = _unit_aggregation(
            str(unit["occurrence_key"]),
            object_member_identity=object_member,
        )
        _resign_reviewed_unit(unit, [evidence_row])

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
        aggregation_basis="object_member",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["count"] == 2
    assert aggregation["unit"] == "reviewed_object_members"
    assert aggregation["counted_member_keys"] == sorted({blue_bike, red_bike})
    provenance = aggregation["provenance"]
    assert isinstance(provenance, list)
    assert [item["counted_member_keys"] for item in provenance] == [[blue_bike], [blue_bike], [red_bike]]


def test_one_event_can_project_three_distinct_reviewed_objects() -> None:
    units, evidence = _signed_rows(1)
    object_members = tuple(_object_member_identity(label) for label in ("red bike", "blue bike", "green bike"))
    units[0]["aggregation_json"] = _unit_aggregation(
        str(units[0]["occurrence_key"]),
        object_member_identities=object_members,
    )
    _resign_reviewed_unit(units[0], evidence)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
        aggregation_basis="object_member",
    )

    assert aggregation is not None
    assert aggregation["count"] == 3
    assert aggregation["lower_bound"] == aggregation["upper_bound"] == 3
    assert aggregation["occurrence_unit_ids"] == ["occurrence-1"]
    assert aggregation["counted_member_keys"] == sorted(object_members)
    assert aggregation["provenance"][0]["counted_member_keys"] == sorted(object_members)


@pytest.mark.parametrize(
    ("canonical_texts", "object_members", "expected_count"),
    [
        (
            ("the red commuter", "my scarlet bicycle"),
            ("shared-stable-bike", "shared-stable-bike"),
            1,
        ),
        (
            ("the same display label", "the same display label"),
            ("stable-bike-one", "stable-bike-two"),
            2,
        ),
    ],
    ids=["aliases-share-stable-id", "same-label-distinct-stable-ids"],
)
def test_object_cardinality_depends_only_on_reviewed_stable_ids(
    canonical_texts: tuple[str, str],
    object_members: tuple[str, str],
    expected_count: int,
) -> None:
    units, evidence = _signed_rows(2)
    for unit, evidence_row, label, stable_key in zip(
        units,
        evidence,
        canonical_texts,
        object_members,
        strict=True,
    ):
        unit["canonical_text"] = label
        unit["aggregation_json"] = _unit_aggregation(
            str(unit["occurrence_key"]),
            object_member_identity=_object_member_identity(stable_key),
        )
        _resign_reviewed_unit(unit, [evidence_row])

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
        aggregation_basis="object_member",
    )

    assert aggregation is not None
    assert aggregation["count"] == expected_count
    assert len(aggregation["occurrence_unit_ids"]) == 2


def test_object_member_aggregation_fails_closed_when_any_unit_lacks_projection() -> None:
    units, evidence = _signed_rows(2)
    units[0]["aggregation_json"] = _unit_aggregation(
        str(units[0]["occurrence_key"]),
        object_member_identity=_object_member_identity("blue bike"),
    )
    _resign_reviewed_unit(units[0], [evidence[0]])

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            requested_end="2026-04-01T00:00:00Z",
            aggregation_basis="object_member",
        )
        is None
    )


def test_object_member_mutation_after_review_invalidates_the_unit_receipt() -> None:
    units, evidence = _signed_rows(1)
    units[0]["aggregation_json"] = _unit_aggregation(
        str(units[0]["occurrence_key"]),
        object_member_identity=_object_member_identity("reviewed bike"),
    )
    _resign_reviewed_unit(units[0], evidence)
    members = units[0]["aggregation_json"]["members"]
    assert isinstance(members, list)
    members[1]["member_identity"] = _object_member_identity("tampered bike")

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            requested_end="2026-04-01T00:00:00Z",
            aggregation_basis="object_member",
        )
        is None
    )


def test_aggregation_rejects_a_disjoint_signed_unit_for_an_exact_query_atom() -> None:
    units, evidence = _signed_rows(1)
    mismatched_predicate = build_occurrence_predicate_atom(
        action="visited",
        object_leaf="museum",
    )

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            query_selector_keys=tuple(mismatched_predicate["selector_keys"]),
            query_predicates=(mismatched_predicate,),
        )
        is None
    )


def test_unknown_accepted_relation_preserves_a_positive_signed_lower_bound() -> None:
    units, evidence = _signed_rows(2)
    units[1]["predicate_json"] = build_occurrence_predicate_atom(
        action="visited",
        object_leaf="museum",
    )
    _resign_reviewed_unit(units[1], [evidence[1]])

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "at_least"
    assert aggregation["lower_bound"] == 1
    assert aggregation["upper_bound"] is None
    assert aggregation["occurrence_unit_ids"] == ["occurrence-1"]
    assert aggregation["accepted_units"] == {
        "matching": 1,
        "disjoint_proven": 0,
        "relation_unknown": 1,
    }
    assert "count" not in aggregation


def test_signed_complete_closure_disjoint_unit_does_not_block_exactness() -> None:
    units, evidence = _signed_rows(2)
    disjoint = build_occurrence_predicate_atom(
        action="visited",
        object_leaf="museum",
    )
    disjoint["closure_complete"] = True
    units[1]["predicate_json"] = disjoint
    _resign_reviewed_unit(units[1], [evidence[1]])

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["count"] == 1
    assert aggregation["accepted_units"] == {
        "matching": 1,
        "disjoint_proven": 1,
        "relation_unknown": 0,
    }


@pytest.mark.parametrize(
    ("stored_action", "queried_action"),
    [
        ("made", "baked"),
        ("cooked", "baked"),
        ("got", "bought"),
        ("watched", "saw"),
    ],
)
def test_a_near_synonym_leaf_never_earns_an_exact_answer(
    stored_action: str,
    queried_action: str,
) -> None:
    """A store holding only "I made a cake" must not answer "how many cakes did
    I bake?" with an exact zero.

    The reviewed vocabulary folds inflections and a few synonyms; it does not
    partition the action space. ``make`` and ``bake`` are separate leaves that
    routinely describe one event, so a non-matching unit under a sibling leaf
    is an unknown relation, never proven disjointness. If any code path ever
    reads "different canonical leaf" as "different event", this test fails with
    a confidently wrong count.
    """

    units, evidence = _signed_rows(1)
    stored = build_occurrence_predicate_atom(action=stored_action, object_leaf="cake")
    units[0]["predicate_json"] = stored
    units[0]["count_key"] = f"{stored_action} cake"
    _resign_reviewed_unit(units[0], [evidence[0]])
    queried = build_occurrence_predicate_atom(action=queried_action, object_leaf="cake")

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
        query_selector_keys=tuple(queried["selector_keys"]),
        query_predicates=(queried,),
    )

    # No matching unit and no proven disjointness leaves nothing countable, so
    # the reader stays silent rather than emitting exact zero.
    assert aggregation is None


def test_a_sibling_leaf_unit_blocks_exactness_for_a_real_match() -> None:
    """The same hazard with one genuine match present.

    Truth is two cake events, one stored as ``bake`` and one as ``make``. The
    honest answer is "at least 1", never "exactly 1".
    """

    units, evidence = _signed_rows(2)
    baked = build_occurrence_predicate_atom(action="baked", object_leaf="cake")
    made = build_occurrence_predicate_atom(action="made", object_leaf="cake")
    units[0]["predicate_json"] = baked
    units[0]["count_key"] = "bake cake"
    _resign_reviewed_unit(units[0], [evidence[0]])
    units[1]["predicate_json"] = made
    units[1]["count_key"] = "make cake"
    _resign_reviewed_unit(units[1], [evidence[1]])

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
        query_selector_keys=tuple(baked["selector_keys"]),
        query_predicates=(baked,),
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "at_least"
    assert aggregation["lower_bound"] == 1
    assert aggregation["accepted_units"] == {
        "matching": 1,
        "disjoint_proven": 0,
        "relation_unknown": 1,
    }
    assert "count" not in aggregation


@pytest.mark.parametrize("closure_complete", [False, True])
def test_nonmatching_unit_must_still_have_a_current_receipt(
    closure_complete: bool,
) -> None:
    units, evidence = _signed_rows(2)
    nonmatching = build_occurrence_predicate_atom(
        action="visited",
        object_leaf="museum",
    )
    nonmatching["closure_complete"] = closure_complete
    units[1]["predicate_json"] = nonmatching
    _resign_reviewed_unit(units[1], [evidence[1]])
    units[1]["review_receipt_digest"] = "f" * 64

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


def test_aggregation_rejects_empty_query_selectors() -> None:
    units, evidence = _signed_rows(1)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            query_selector_keys=(),
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


def test_aggregation_rejects_duplicate_matching_query_selectors() -> None:
    units, evidence = _signed_rows(1)
    predicate = _predicate()
    exact_selector = next(str(value) for value in predicate["selector_keys"] if not str(value).endswith("|o=*"))
    valid = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        query_selector_keys=(exact_selector,),
        query_predicates=(predicate,),
        requested_end="2026-04-01T00:00:00Z",
    )
    assert valid is not None and valid["answer_kind"] == "exact"

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            query_selector_keys=(exact_selector, exact_selector),
            query_predicates=(predicate,),
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


def test_aggregation_rejects_a_mismatched_atom_with_matching_selector_keys() -> None:
    units, evidence = _signed_rows(1)
    signed_predicate = _predicate()
    exact_selector = next(str(value) for value in signed_predicate["selector_keys"] if not str(value).endswith("|o=*"))
    mismatched_atom = build_occurrence_predicate_atom(
        action="serviced",
        object_leaf="bike",
        object_qualifiers=("red",),
    )

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            query_selector_keys=(exact_selector,),
            query_predicates=(mismatched_atom,),
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


def test_aggregation_accepts_a_matching_wildcard_selector() -> None:
    units, evidence = _signed_rows(1)
    predicate = _predicate()
    wildcard_selector = next(str(value) for value in predicate["selector_keys"] if str(value).endswith("|o=*"))

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        query_selector_keys=(wildcard_selector,),
        query_predicates=(predicate,),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["count"] == 1


def test_aggregation_accepts_signed_evidence_from_a_resolved_linked_claim() -> None:
    units, evidence = _signed_rows(1)
    evidence[0].update(
        {
            "claim_id": "claim-linked",
            "evidence_claim_review_status": "accepted",
            "evidence_claim_resolution_status": "resolved",
            "evidence_claim_resolution_decision": "link_existing",
            "evidence_claim_resolved_occurrence_id": units[0]["id"],
        }
    )
    _resign_reviewed_unit(units[0], evidence)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["count"] == 1


@pytest.mark.parametrize(
    ("memory_id", "source_id", "source_chunk_id"),
    [
        (None, None, _ACCOUNTING_CHUNK_ID),
        ("memory-1", None, _ACCOUNTING_CHUNK_ID),
        ("", None, None),
        ("  ", None, None),
        (None, "", None),
        (None, "\u00a0", None),
        ("memory-1", " ", None),
        ("memory-1", "\u001c", _ACCOUNTING_CHUNK_ID),
    ],
    ids=(
        "source-chunk-only",
        "memory-plus-orphaned-source-chunk",
        "empty-memory",
        "whitespace-memory",
        "empty-source",
        "nbsp-source",
        "memory-plus-blank-source",
        "memory-plus-control-source-chunk",
    ),
)
def test_aggregation_rejects_re_signed_evidence_with_an_invalid_carrier_shape(
    memory_id: str | None,
    source_id: str | None,
    source_chunk_id: str | None,
) -> None:
    units, evidence = _signed_rows(1)
    evidence[0]["memory_id"] = memory_id
    evidence[0]["source_id"] = source_id
    evidence[0]["source_chunk_id"] = source_chunk_id
    _resign_reviewed_unit(units[0], evidence)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


@pytest.mark.parametrize(
    "quote",
    ["", " ", "\u00a0", "\u001c", "\u001f"],
    ids=("empty", "ascii-space", "nbsp", "file-separator", "unit-separator"),
)
def test_aggregation_rejects_re_signed_python_strip_empty_quote(
    quote: str,
) -> None:
    units, evidence = _signed_rows(1)
    evidence[0]["quote"] = quote
    evidence[0]["quote_sha256"] = sha256(quote.encode()).hexdigest()
    _resign_reviewed_unit(units[0], evidence)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


def test_aggregation_preserves_valid_unicode_quote_content() -> None:
    units, evidence = _signed_rows(1)
    quote = "\u00a0J'ai réparé le vélo.\u001c"
    evidence[0]["quote"] = quote
    evidence[0]["quote_sha256"] = sha256(quote.encode()).hexdigest()
    _resign_reviewed_unit(units[0], evidence)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["count"] == 1


@pytest.mark.parametrize(
    ("target", "field", "blank_value"),
    [
        ("coverage", "reviewer_id", "\u00a0"),
        ("coverage", "review_reason", "\u001c"),
        ("unit", "reviewer_id", "\u001f"),
        ("unit", "review_reason", "\u00a0"),
        ("evidence", "reviewer_id", "\u001c"),
        ("evidence", "review_reason", "\u001f"),
    ],
    ids=(
        "coverage-nbsp-reviewer",
        "coverage-file-separator-reason",
        "unit-unit-separator-reviewer",
        "unit-nbsp-reason",
        "evidence-file-separator-reviewer",
        "evidence-unit-separator-reason",
    ),
)
def test_aggregation_rejects_fully_re_signed_python_strip_empty_review_text(
    target: str,
    field: str,
    blank_value: str,
) -> None:
    units, evidence = _signed_rows(1)
    coverage = _coverage()
    if target == "coverage":
        coverage[field] = blank_value
        coverage["review_receipt_digest"] = occurrence_coverage_review_receipt_digest(
            coverage_id=coverage["id"],
            user_id=coverage["user_id"],
            review_version=int(coverage["review_version"]),
            coverage_mode=str(coverage["coverage_mode"]),
            coverage_started_at=coverage["coverage_started_at"],
            historical_review_status=str(coverage["historical_review_status"]),
            complete_through=coverage.get("complete_through"),
            reviewer_id=str(coverage["reviewer_id"]),
            reason=str(coverage["review_reason"]),
            accounting_metadata=coverage["metadata_json"],  # type: ignore[arg-type]
        )
    elif target == "unit":
        units[0][field] = blank_value
        _resign_reviewed_unit(units[0], evidence)
    else:
        evidence[0][field] = blank_value
        _resign_reviewed_unit(units[0], evidence)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=coverage,
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


@pytest.mark.parametrize(
    ("target", "field"),
    [
        ("coverage", "id"),
        ("coverage", "user_id"),
        ("unit", "id"),
        ("unit", "claim_id"),
        ("unit", "user_id"),
        ("evidence", "claim_id"),
        ("evidence", "evidence_key"),
        ("evidence", "id"),
        ("evidence", "user_id"),
    ],
)
def test_aggregation_rejects_fully_re_signed_python_strip_empty_row_ids(
    target: str,
    field: str,
) -> None:
    units, evidence = _signed_rows(1)
    coverage = _coverage()
    row = coverage if target == "coverage" else units[0] if target == "unit" else evidence[0]
    row[field] = "\u001c"
    if target == "coverage":
        coverage["review_receipt_digest"] = occurrence_coverage_review_receipt_digest(
            coverage_id=coverage["id"],
            user_id=coverage["user_id"],
            review_version=int(coverage["review_version"]),
            coverage_mode=str(coverage["coverage_mode"]),
            coverage_started_at=coverage["coverage_started_at"],
            historical_review_status=str(coverage["historical_review_status"]),
            complete_through=coverage.get("complete_through"),
            reviewer_id=str(coverage["reviewer_id"]),
            reason=str(coverage["review_reason"]),
            accounting_metadata=coverage["metadata_json"],  # type: ignore[arg-type]
        )
    else:
        _resign_reviewed_unit(units[0], evidence)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=coverage,
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


@pytest.mark.parametrize(
    "claim_metadata",
    [
        {},
        {
            "evidence_claim_review_status": "candidate",
            "evidence_claim_resolution_status": "resolved",
            "evidence_claim_resolution_decision": "link_existing",
            "evidence_claim_resolved_occurrence_id": "occurrence-1",
        },
        {
            "evidence_claim_review_status": "accepted",
            "evidence_claim_resolution_status": "resolved",
            "evidence_claim_resolution_decision": "link_existing",
            "evidence_claim_resolved_occurrence_id": "occurrence-other",
        },
    ],
)
def test_aggregation_rejects_signed_evidence_from_an_unrelated_claim(
    claim_metadata: dict[str, object],
) -> None:
    units, evidence = _signed_rows(1)
    evidence[0]["claim_id"] = "claim-unrelated"
    evidence[0].update(claim_metadata)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
        )
        is None
    )


def test_aggregation_emits_range_for_finite_unresolved_claims() -> None:
    units, evidence = _signed_rows(1)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        unresolved_claims=(
            _unresolved(range_kind="bounded", quantity_max=2),
            _unresolved(id="unresolved-2", quantity_max=1),
        ),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "range"
    assert aggregation["lower_bound"] == 1
    assert aggregation["upper_bound"] == 4
    assert "count" not in aggregation
    assert aggregation["answer_sufficient"] is False


def test_aggregation_requires_coverage_and_emits_at_least_for_unbounded_claim() -> None:
    units, evidence = _signed_rows(1)

    legacy = _aggregate(
        units=units,
        evidence=evidence,
        coverage=None,
    )
    unbounded = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        unresolved_claims=(_unresolved(range_kind="at_least", quantity_max=None),),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert legacy is None
    assert unbounded is not None
    assert unbounded["answer_kind"] == "at_least"
    assert unbounded["lower_bound"] == 1
    assert unbounded["upper_bound"] is None
    assert "count" not in unbounded


def test_unresolved_at_least_claim_never_becomes_a_finite_range() -> None:
    units, evidence = _signed_rows(1)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        unresolved_claims=(
            _unresolved(
                range_kind="at_least",
                quantity_min=2,
                quantity_max=2,
            ),
        ),
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "at_least"
    assert aggregation["upper_bound"] is None


@pytest.mark.parametrize(
    ("range_kind", "quantity_min", "quantity_max"),
    [
        ("exact", 1, 1),
        ("bounded", 1, 3),
    ],
)
def test_display_key_does_not_override_a_matching_unresolved_predicate(
    range_kind: str,
    quantity_min: int,
    quantity_max: int,
) -> None:
    units, evidence = _signed_rows(1)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        unresolved_claims=(
            _unresolved(
                count_key="museum visit",
                range_kind=range_kind,
                quantity_min=quantity_min,
                quantity_max=quantity_max,
            ),
        ),
        requested_end="2026-04-01T00:00:00Z",
        expected_user_id="user-1",
        projects=("garage",),
        domains=("work",),
        sensitivity_allowed=("private",),
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "range"
    assert aggregation["lower_bound"] == 1
    assert aggregation["upper_bound"] == 1 + quantity_max
    assert "count" not in aggregation
    assert aggregation["unresolved_claims"]["count"] == 1


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"user_id": "user-other"},
        {"domain": "personal"},
        {"sensitivity": "secret"},
        {"project_scope": ["other"]},
        {"quantity_min": 0},
        {
            "range_kind": "bounded",
            "quantity_min": 2,
            "quantity_max": 1,
        },
    ],
)
def test_different_key_unresolved_claim_still_fails_closed_on_invalid_rows(
    claim_overrides: dict[str, object],
) -> None:
    units, evidence = _signed_rows(1)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        unresolved_claims=(
            _unresolved(
                count_key="museum visit",
                **claim_overrides,
            ),
        ),
        requested_end="2026-04-01T00:00:00Z",
        expected_user_id="user-1",
        projects=("garage",),
        domains=("work",),
        sensitivity_allowed=("private",),
    )

    assert aggregation is None


@pytest.mark.parametrize(
    ("row_kind", "field"),
    [
        ("unit", "occurred_at_start"),
        ("unit", "occurred_at_end"),
        ("claim", "occurred_at_start"),
        ("claim", "occurred_at_end"),
    ],
)
def test_aggregation_rejects_non_null_unparseable_occurrence_timestamps(
    row_kind: str,
    field: str,
) -> None:
    units, evidence = _signed_rows(1)
    unresolved: tuple[dict[str, object], ...] = ()
    if row_kind == "unit":
        units[0][field] = "not-a-timestamp"
    else:
        claim = _unresolved()
        claim[field] = "not-a-timestamp"
        unresolved = (claim,)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        unresolved_claims=unresolved,
        allow_timeless_units=True,
    )

    assert aggregation is None


@pytest.mark.parametrize("row_kind", ["unit", "claim"])
def test_aggregation_rejects_reversed_occurrence_intervals(
    row_kind: str,
) -> None:
    units, evidence = _signed_rows(1)
    unresolved: tuple[dict[str, object], ...] = ()
    if row_kind == "unit":
        units[0]["occurred_at_start"] = "2026-03-03T12:00:00Z"
        units[0]["occurred_at_end"] = "2026-03-03T11:00:00Z"
    else:
        unresolved = (
            _unresolved(
                occurred_at_start="2026-03-10T12:00:00Z",
                occurred_at_end="2026-03-10T11:00:00Z",
            ),
        )

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            unresolved_claims=unresolved,
            allow_timeless_units=True,
        )
        is None
    )


@pytest.mark.parametrize(
    ("requested_start", "requested_end"),
    [
        ("2026-04-01T00:00:00Z", "2026-03-01T00:00:00Z"),
        ("2026-04-01T00:00:00Z", "2026-04-01T00:00:00Z"),
    ],
)
def test_aggregation_rejects_inverted_or_empty_requested_windows(
    requested_start: str,
    requested_end: str,
) -> None:
    units, evidence = _signed_rows(1)
    units[0]["occurred_at_start"] = None
    units[0]["occurred_at_end"] = None

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            requested_start=requested_start,
            requested_end=requested_end,
            allow_timeless_units=True,
        )
        is None
    )


@pytest.mark.parametrize(
    ("coverage_mode", "historical_review_status"),
    [
        ("forward_only", "not_reviewed"),
        ("partial_history", "reviewed"),
        ("complete_history", "reviewed"),
    ],
)
def test_aggregation_never_trusts_inverted_signed_coverage_interval(
    coverage_mode: str,
    historical_review_status: str,
) -> None:
    units, evidence = _signed_rows(1)
    units[0]["occurred_at_start"] = "2026-01-03T10:00:00Z"
    units[0]["occurred_at_end"] = "2026-01-03T11:00:00Z"
    _resign_reviewed_unit(units[0], evidence)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(
            coverage_mode=coverage_mode,
            historical_review_status=historical_review_status,
            coverage_started_at="2026-04-01T00:00:00Z",
            complete_through="2026-03-01T00:00:00Z",
        ),
        requested_end="2026-02-01T00:00:00Z",
        allow_timeless_units=True,
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "at_least"
    assert aggregation["coverage"]["receipt_valid"] is True
    assert aggregation["coverage"]["fully_covered"] is False


@pytest.mark.parametrize(
    ("coverage_mode", "historical_review_status"),
    [
        ("forward_only", "not_reviewed"),
        ("partial_history", "reviewed"),
    ],
)
def test_noncomplete_coverage_never_promotes_a_closed_interval_to_exact(
    coverage_mode: str,
    historical_review_status: str,
) -> None:
    units, evidence = _signed_rows(1)
    noncomplete = _coverage(
        coverage_mode=coverage_mode,
        historical_review_status=historical_review_status,
        coverage_started_at="2026-03-01T00:00:00Z",
        complete_through="2026-04-01T00:00:00Z",
    )

    covered = _aggregate(
        units=units,
        evidence=evidence,
        coverage=noncomplete,
        requested_start="2026-03-01T00:00:00Z",
        requested_end="2026-03-31T00:00:00Z",
    )
    open_ended = _aggregate(
        units=units,
        evidence=evidence,
        coverage=noncomplete,
        requested_start="2026-03-01T00:00:00Z",
    )

    assert covered is not None and covered["answer_kind"] == "at_least"
    assert covered["exact"] is False
    assert covered["coverage"]["fully_covered"] is True
    assert open_ended is not None and open_ended["answer_kind"] == "at_least"


@pytest.mark.parametrize(
    ("requested_start", "answer_kind", "fully_covered"),
    [
        ("2025-01-01T00:00:00Z", "at_least", False),
        ("2026-01-01T00:00:00Z", "exact", True),
        (None, "exact", True),
    ],
)
def test_complete_history_enforces_explicit_start_and_preserves_all_time(
    requested_start: str | None,
    answer_kind: str,
    fully_covered: bool,
) -> None:
    units, evidence = _signed_rows(1)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(
            coverage_started_at="2026-01-01T00:00:00Z",
            complete_through="2026-12-31T23:59:59Z",
        ),
        requested_start=requested_start,
        requested_end="2026-04-01T00:00:00Z",
        allow_timeless_units=True,
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == answer_kind
    assert aggregation["exact"] is fully_covered
    assert aggregation["coverage"]["fully_covered"] is fully_covered
    assert aggregation["coverage"]["legacy_gap"] is not fully_covered
    if fully_covered:
        assert aggregation["count"] == 1
    else:
        assert "count" not in aggregation


def test_exact_coverage_requires_a_reconstructible_review_receipt() -> None:
    units, evidence = _signed_rows(1)
    unsigned = _coverage(review_receipt_digest=None)
    tampered = _coverage()
    tampered["complete_through"] = "2027-12-31T23:59:59Z"

    for coverage in (unsigned, tampered):
        aggregation = _aggregate(
            units=units,
            evidence=evidence,
            coverage=coverage,
            requested_end="2026-04-01T00:00:00Z",
        )
        assert aggregation is not None
        assert aggregation["answer_kind"] == "at_least"
        assert aggregation["coverage"]["receipt_valid"] is False


@pytest.mark.parametrize(
    ("mismatch_field", "tampered_value"),
    [
        ("extractor_version", "phase6-other-extractor-v1"),
        (
            "source_ids",
            ["44444444-4444-4444-8444-444444444444"],
        ),
        (
            "source_chunk_ids",
            ["55555555-5555-4555-8555-555555555555"],
        ),
        ("snapshot_digest", "c" * 64),
        ("disposition_digest", "d" * 64),
        (
            "item_chunk_set",
            "66666666-6666-4666-8666-666666666666",
        ),
    ],
)
def test_complete_history_rejects_accounting_summary_mismatch(
    mismatch_field: str,
    tampered_value: object,
) -> None:
    units, evidence = _signed_rows(1)
    coverage = _coverage()
    accounting_summary = _accounting_summary(coverage, units)
    if mismatch_field == "item_chunk_set":
        items = accounting_summary["items"]
        assert isinstance(items, list)
        items[0]["source_chunk_id"] = tampered_value
    else:
        accounting_summary[mismatch_field] = tampered_value

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=coverage,
            requested_end="2026-04-01T00:00:00Z",
            accounting_summary=accounting_summary,
        )
        is None
    )


def test_coverage_rejects_precanonical_default_width_timestamp_receipt() -> None:
    units, evidence = _signed_rows(1)
    coverage = _coverage()
    coverage["review_receipt_digest"] = sha256(
        json.dumps(
            {
                "complete_through": "2026-12-31T23:59:59Z",
                "coverage_id": coverage["id"],
                "coverage_mode": coverage["coverage_mode"],
                "coverage_started_at": "2026-01-01T00:00:00Z",
                "historical_review_status": coverage["historical_review_status"],
                "reason": coverage["review_reason"],
                "review_version": coverage["review_version"],
                "reviewer_id": coverage["reviewer_id"],
                "user_id": coverage["user_id"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=coverage,
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "at_least"
    assert aggregation["coverage"]["receipt_valid"] is False


def test_aggregation_rejects_signed_coverage_from_a_different_user() -> None:
    units, evidence = _signed_rows(1)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(user_id="user-2"),
            expected_user_id="user-1",
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


def test_coverage_uuid_and_datetime_rows_emit_json_safe_receipt_fields() -> None:
    units, evidence = _signed_rows(1)
    coverage_id = UUID("00000000-0000-4000-8000-000000000001")
    started = datetime(2026, 1, 1, tzinfo=UTC)
    complete = datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC)
    coverage = _coverage()
    coverage.update(
        {
            "id": coverage_id,
            "coverage_started_at": started,
            "complete_through": complete,
        }
    )
    accounting_metadata = coverage["metadata_json"]
    assert isinstance(accounting_metadata, dict)
    coverage["review_receipt_digest"] = occurrence_coverage_review_receipt_digest(
        coverage_id=coverage_id,
        user_id=coverage["user_id"],
        review_version=int(coverage["review_version"]),
        coverage_mode=str(coverage["coverage_mode"]),
        coverage_started_at=started,
        historical_review_status=str(coverage["historical_review_status"]),
        complete_through=complete,
        reviewer_id=str(coverage["reviewer_id"]),
        reason=str(coverage["review_reason"]),
        accounting_metadata=accounting_metadata,
    )

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=coverage,
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["coverage"]["id"] == str(coverage_id)
    json.dumps(aggregation)


def test_timeless_accepted_units_count_only_for_an_explicit_all_time_request() -> None:
    units, evidence = _signed_rows(2)
    units[1]["occurred_at_start"] = None
    units[1]["occurred_at_end"] = None
    _resign_reviewed_unit(units[1], [evidence[1]])

    temporal = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_start="2026-01-01T00:00:00Z",
        requested_end="2026-04-01T00:00:00Z",
        allow_timeless_units=False,
    )
    all_time = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
        allow_timeless_units=True,
    )

    assert temporal is None
    assert all_time is not None
    assert all_time["answer_kind"] == "exact"
    assert all_time["count"] == 2


def test_unresolved_saturation_is_disclosed_at_both_contract_levels() -> None:
    units, evidence = _signed_rows(1)

    aggregation = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        unresolved_claims=(_unresolved(),),
        requested_end="2026-04-01T00:00:00Z",
        unresolved_saturated=True,
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "at_least"
    assert aggregation["unresolved_claims"]["saturated"] is True
    assert aggregation["saturated"] is True


@pytest.mark.parametrize(
    ("target", "field", "tampered_value"),
    [
        ("unit", "canonical_text", "I serviced a different bike."),
        (
            "evidence",
            "source_chunk_id",
            "77777777-7777-4777-8777-777777777777",
        ),
        (
            "evidence",
            "review_reason",
            "different evidence review reason",
        ),
    ],
    ids=["unit-fact", "evidence-carrier-fact", "evidence-receipt-fact"],
)
def test_aggregation_rejects_valid_rows_tampered_after_signing(
    target: str,
    field: str,
    tampered_value: object,
) -> None:
    units, evidence = _signed_rows(1)
    valid = _aggregate(
        units=units,
        evidence=evidence,
        coverage=_coverage(),
        requested_end="2026-04-01T00:00:00Z",
    )
    assert valid is not None and valid["answer_kind"] == "exact"

    row = units[0] if target == "unit" else evidence[0]
    row[field] = tampered_value

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
            requested_end="2026-04-01T00:00:00Z",
        )
        is None
    )


@pytest.mark.parametrize(
    ("mutation",),
    [
        (lambda units, evidence: units[0].update(unit_value=2),),
        (lambda units, evidence: units[0].update(review_status="retired"),),
        (lambda units, evidence: units[0].update(identity_status="ambiguous"),),
        (lambda units, evidence: evidence[0].update(review_status="candidate"),),
        (lambda units, evidence: evidence[0].update(unit_review_receipt_digest="f" * 64),),
        (lambda units, evidence: units[0].update(reviewed_evidence_count=2),),
        (lambda units, evidence: units[0].update(reviewed_evidence_digest="e" * 64),),
    ],
)
def test_aggregation_fails_closed_on_unsigned_or_stale_rows(mutation) -> None:
    units, evidence = _signed_rows(1)
    mutation(units, evidence)

    assert (
        _aggregate(
            units=units,
            evidence=evidence,
            coverage=_coverage(),
        )
        is None
    )


def test_aggregation_fails_closed_on_duplicate_units() -> None:
    units, evidence = _signed_rows(1)
    duplicate = deepcopy(units[0])

    assert (
        _aggregate(
            units=[units[0], duplicate],
            evidence=evidence,
            coverage=_coverage(),
        )
        is None
    )


@pytest.mark.parametrize(
    ("aggregation_basis", "expected_unit"),
    [
        ("event_instance", "reviewed_occurrence_units"),
        ("object_member", "reviewed_object_members"),
    ],
)
def test_complete_signed_accounting_can_emit_exact_zero_for_either_basis(
    aggregation_basis: str,
    expected_unit: str,
) -> None:
    aggregation = _aggregate(
        units=[],
        evidence=[],
        coverage=_coverage(),
        aggregation_basis=aggregation_basis,
        requested_end="2026-04-01T00:00:00Z",
    )

    assert aggregation is not None
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["count"] == 0
    assert aggregation["lower_bound"] == aggregation["upper_bound"] == 0
    assert aggregation["unit"] == expected_unit
    assert aggregation["occurrence_unit_ids"] == []
    assert aggregation["counted_member_keys"] == []
    assert aggregation["provenance"] == []
    assert aggregation["accepted_units"] == {
        "matching": 0,
        "disjoint_proven": 0,
        "relation_unknown": 0,
    }


@pytest.mark.parametrize("aggregation_basis", ["event_instance", "object_member"])
def test_forward_only_zero_remains_dormant(
    aggregation_basis: str,
) -> None:
    assert (
        _aggregate(
            units=[],
            evidence=[],
            coverage=_coverage(
                coverage_mode="forward_only",
                historical_review_status="not_reviewed",
                metadata_json={},
            ),
            aggregation_basis=aggregation_basis,
        )
        is None
    )
