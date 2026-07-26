from __future__ import annotations

import json
import sqlite3
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest

from alicebot_api import vnext_memory_commit as memory_commit_module
from alicebot_api import vnext_occurrence_write as occurrence_write_module
from alicebot_api.mcp.memories import redact_memory_flow
from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_capture import SourceCaptureInput, VNextCaptureService
from alicebot_api.vnext_memory_commit import VNextMemoryCommitService
from alicebot_api.vnext_occurrence_write import (
    OCCURRENCE_EXTRACTOR_VERSION,
    OCCURRENCE_INVALIDATION_METADATA_KEY,
    OCCURRENCE_PROPOSAL_METADATA_KEY,
    establish_memory_occurrences,
    establish_source_chunk_occurrences,
    invalidate_occurrence_accounting,
    reconcile_chunk_extraction_disposition,
    review_source_chunk_occurrences,
)
from alicebot_api.vnext_occurrence_predicates import OCCURRENCE_AGGREGATION_SCHEMA
from alicebot_api.vnext_occurrence_taxonomy import build_occurrence_predicate_atom
from alicebot_api.vnext_retrieval import (
    VNextRetrievalRequest,
    VNextRetrievalService,
)
from alicebot_api.vnext_stores.sqlite import (
    occurrence_accounting as sqlite_occurrence_accounting,
)
from alicebot_api.vnext_stores.sqlite import occurrences as sqlite_occurrences

OCCURRENCE_PROPOSALS_METADATA_KEY = "occurrence_proposals"


def _store() -> SQLiteVNextStore:
    connection = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(connection)
    user_id = str(uuid4())
    ensure_sqlite_user(connection, user_id, f"{user_id}@example.com")
    return SQLiteVNextStore(connection, user_id)


def _source(
    store: SQLiteVNextStore,
    *,
    metadata_json: dict[str, object] | None = None,
) -> dict[str, object]:
    return store.create_source(
        {
            "source_type": "conversation",
            "title": "Occurrence write test",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "personal",
            "sensitivity": "private",
            "metadata_json": metadata_json or {},
        }
    )


def _memory(
    store: SQLiteVNextStore,
    text: str,
    *,
    status: str = "active",
    metadata_json: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = metadata_json or {}
    return store.create_memory(
        {
            "memory_key": f"occurrence-test.{uuid4()}",
            "value": {"text": text},
            "status": status,
            "memory_type": "semantic",
            "title": text[:120],
            "canonical_text": text,
            "summary": text[:280],
            "domain": "personal",
            "sensitivity": "private",
            "metadata_json": metadata,
        }
    )


def _search_probe(text: str) -> str:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
    return max(terms, key=len) if terms else "occurrence"


def _assert_memory_searches_empty(
    store: SQLiteVNextStore,
    *,
    text: str,
) -> None:
    query = _search_probe(text)
    assert store.search_memories(query=query, limit=50) == []
    assert store.search_memories_fts(query=query, limit=50) == []


def _raw_claim_evidence(
    store: SQLiteVNextStore,
    claim_id: str,
) -> list[dict[str, object]]:
    cursor = store.conn.execute(
        """
        SELECT
          id,
          claim_id,
          occurrence_id,
          memory_id,
          source_id,
          source_chunk_id,
          review_status
        FROM occurrence_evidence
        WHERE user_id = ?
          AND claim_id = ?
        ORDER BY id
        """,
        (store.user_id, claim_id),
    )
    columns = [str(item[0]) for item in cursor.description or ()]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _raw_claim_evidence_details(
    store: SQLiteVNextStore,
    claim_id: str,
) -> list[dict[str, object]]:
    cursor = store.conn.execute(
        """
        SELECT
          id,
          evidence_key,
          review_status,
          review_receipt_action,
          unit_review_receipt_digest,
          metadata_json
        FROM occurrence_evidence
        WHERE user_id = ?
          AND claim_id = ?
        ORDER BY evidence_key, id
        """,
        (store.user_id, claim_id),
    )
    columns = [str(item[0]) for item in cursor.description or ()]
    rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    for row in rows:
        row["metadata_json"] = json.loads(str(row["metadata_json"]))
    return rows


@dataclass(frozen=True)
class _DirectOccurrenceGraph:
    source: dict[str, object]
    chunk: dict[str, object]
    claims: list[dict[str, object]]
    units_by_claim: dict[str, list[dict[str, object]]]
    evidence_by_claim: dict[str, list[dict[str, object]]]

    def only_claim(self) -> dict[str, object]:
        assert len(self.claims) == 1
        return self.claims[0]

    def units_for(self, claim: dict[str, object]) -> list[dict[str, object]]:
        return self.units_by_claim[str(claim["id"])]

    def evidence_for(self, claim: dict[str, object]) -> list[dict[str, object]]:
        return self.evidence_by_claim[str(claim["id"])]


def _claim_identity_anchor(claim: dict[str, object]) -> dict[str, object] | None:
    metadata = claim.get("metadata_json")
    if not isinstance(metadata, dict):
        return None
    anchor = metadata.get("identity_anchor")
    return anchor if isinstance(anchor, dict) else None


def _read_direct_graph(
    store: SQLiteVNextStore,
    *,
    source: dict[str, object],
    chunk: dict[str, object],
    text: str,
    accepted: bool,
) -> _DirectOccurrenceGraph:
    chunk_id = str(chunk["id"])
    _assert_memory_searches_empty(store, text=text)
    if accepted:
        review_source_chunk_occurrences(
            store,
            source_chunk_id=chunk_id,
            reviewer_id="reviewer-1",
            reason="Reviewed in the occurrence write test.",
            actor_type="user",
            stage="test_source_review",
        )
    claims = store.list_occurrence_claims_for_source_chunk(chunk_id, limit=201)
    _assert_memory_searches_empty(store, text=text)
    units_by_claim: dict[str, list[dict[str, object]]] = {}
    evidence_by_claim: dict[str, list[dict[str, object]]] = {}
    for claim in claims:
        claim_id = str(claim["id"])
        units = store.list_occurrence_units_for_claim(claim_id)
        evidence = _raw_claim_evidence(store, claim_id)
        assert evidence
        assert all(row["memory_id"] is None for row in evidence)
        assert {str(row["source_id"]) for row in evidence} == {str(source["id"])}
        assert {str(row["source_chunk_id"]) for row in evidence} == {chunk_id}
        if accepted and claim["resolution_status"] == "resolved":
            accepted_evidence = store.list_occurrence_evidence_for_units([str(unit["id"]) for unit in units])
            assert len(accepted_evidence) == len(units)
            assert all(row["memory_id"] is None for row in accepted_evidence)
        units_by_claim[claim_id] = units
        evidence_by_claim[claim_id] = evidence
    return _DirectOccurrenceGraph(
        source=source,
        chunk=chunk,
        claims=claims,
        units_by_claim=units_by_claim,
        evidence_by_claim=evidence_by_claim,
    )


def _capture_natural_graph(
    store: SQLiteVNextStore,
    text: str,
    *,
    accepted: bool = True,
    session_date: str | None = None,
    captured_at: str | None = None,
    source_created_at: str | None = None,
    metadata_json: dict[str, object] | None = None,
) -> _DirectOccurrenceGraph:
    metadata = dict(metadata_json or {})
    metadata.setdefault("provenance_role", "user")
    if session_date is not None:
        metadata["session_date"] = session_date
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text=text,
            captured_at=captured_at,
            source_created_at=source_created_at,
            domain="personal",
            sensitivity="private",
            metadata_json=metadata,
        )
    )
    source = store.get_source(str(result.source_id))
    assert source is not None
    chunks = store.list_source_chunks(str(result.source_id))
    assert len(chunks) == 1
    return _read_direct_graph(
        store,
        source=source,
        chunk=chunks[0],
        text=text,
        accepted=accepted,
    )


def _establish_natural_chunk_graph(
    store: SQLiteVNextStore,
    *,
    source: dict[str, object],
    chunk: dict[str, object],
    accepted: bool,
) -> _DirectOccurrenceGraph:
    establish_source_chunk_occurrences(
        store,
        source=source,
        source_chunk=chunk,
        actor_type="user",
        stage="test_source_capture",
    )
    return _read_direct_graph(
        store,
        source=source,
        chunk=chunk,
        text=str(chunk["text"]),
        accepted=accepted,
    )


def _establish(
    store: SQLiteVNextStore,
    memory: dict[str, object],
    *,
    source: dict[str, object] | None = None,
    source_chunk_id: str | None = None,
    accepted: bool = True,
    stage: str = "test_review",
) -> dict[str, object]:
    return establish_memory_occurrences(
        store,
        memory,
        source=source,
        source_chunk_id=source_chunk_id,
        accepted=accepted,
        reviewer_id="reviewer-1",
        reason="Reviewed in the occurrence write test.",
        actor_type="user",
        stage=stage,
    )


def _proposal_record(memory: dict[str, object]) -> dict[str, object]:
    metadata = memory["metadata_json"]
    assert isinstance(metadata, dict)
    proposal = metadata[OCCURRENCE_PROPOSAL_METADATA_KEY]
    assert isinstance(proposal, dict)
    return proposal


def _structured_occurrence_contract(
    *,
    count_key: str = "museum visit",
    action: str = "visit",
    object_leaf: str = "museum",
) -> dict[str, object]:
    return {
        "count_key": count_key,
        "predicate_json": build_occurrence_predicate_atom(
            action=action,
            object_leaf=object_leaf,
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
    }


def _explicit_event(
    event_id: str,
    *,
    quantity: int = 1,
    count_key: str = "museum visit",
    action: str = "visit",
    object_leaf: str = "museum",
) -> dict[str, object]:
    return {
        **_structured_occurrence_contract(
            count_key=count_key,
            action=action,
            object_leaf=object_leaf,
        ),
        "external_event_id": event_id,
        "external_event_namespace": "calendar:test",
        "quantity_min": quantity,
        "quantity_max": quantity,
    }


def _qualify_complete_coverage(store: SQLiteVNextStore) -> dict[str, object]:
    chunk_rows = store.conn.execute(
        """
        SELECT chunk.id
        FROM source_chunks AS chunk
        JOIN sources AS source
          ON source.id = chunk.source_id
         AND source.user_id = chunk.user_id
        WHERE chunk.user_id = ?
          AND source.deleted_at IS NULL
        ORDER BY chunk.id
        """,
        (store.user_id,),
    ).fetchall()
    if not chunk_rows:
        result = VNextCaptureService(store).capture_source(
            SourceCaptureInput(
                source_type="note",
                raw_text="Neutral coverage anchor without an extraction rule.",
            )
        )
        chunk_rows = [(str(row["id"]),) for row in store.list_source_chunks(str(result.source_id))]
    for (chunk_id,) in chunk_rows:
        review_source_chunk_occurrences(
            store,
            source_chunk_id=str(chunk_id),
            reviewer_id="coverage-reviewer",
            reason="The test corpus chunk was reviewed completely.",
            actor_type="user",
            stage="complete_history_test",
        )
    accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=None,
    )
    assert accounting["complete"] is True
    coverage = store.ensure_occurrence_coverage(started_at="2020-01-01T00:00:00Z")
    return store.review_occurrence_coverage(
        coverage_mode="complete_history",
        historical_review_status="reviewed",
        coverage_started_at=coverage["coverage_started_at"],
        complete_through="2030-12-31T23:59:59Z",
        accounting_metadata={
            "accounting_schema": "occurrence_accounting_v1",
            "extractor_version": accounting["extractor_version"],
            "source_ids": accounting["source_ids"],
            "source_chunk_ids": accounting["source_chunk_ids"],
            "snapshot_digest": accounting["snapshot_digest"],
            "disposition_digest": accounting["disposition_digest"],
        },
        reviewer_id="coverage-reviewer",
        reason="The test corpus was reviewed completely.",
        expected_review_version=int(coverage["review_version"]),
    )


def _captured_multi_event_graph(
    store: SQLiteVNextStore,
) -> _DirectOccurrenceGraph:
    graph = _capture_natural_graph(
        store,
        ("I baked cookies on March 3, 2026. I created a clay sculpture on March 4, 2026."),
        session_date="2026-03-05T12:00:00Z",
    )
    assert len(graph.claims) == 2
    return graph


def test_natural_capture_alone_keeps_direct_graph_dormant_and_unsearchable() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I painted the garden fence on March 3, 2026.",
        accepted=False,
    )
    claim = graph.only_claim()

    assert claim["review_status"] == "candidate"
    assert claim["resolution_status"] == "pending"
    assert {unit["review_status"] for unit in graph.units_for(claim)} == {"candidate"}
    assert {evidence["review_status"] for evidence in graph.evidence_for(claim)} == {"candidate"}


def test_generic_completed_event_builds_a_review_gated_predicate_unit() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I painted the blue garden fence on March 3, 2026.",
    )
    claim = graph.only_claim()
    units = graph.units_for(claim)

    assert claim["count_key"] == "painted fence"
    assert claim["identity_basis"] == "date_and_ordinal"
    assert _claim_identity_anchor(claim)["reviewed_date_ordinal"] == 1
    assert claim["resolution_status"] == "resolved"
    assert claim["review_status"] == "accepted"
    assert claim["predicate_json"]["object"] == {
        "leaf": "fence",
        "qualifiers": ["blue", "garden"],
        "ancestors": [],
    }
    assert claim["aggregation_json"]["bases"] == [
        {
            "basis": "event_instance",
            "identity_basis": "occurrence_key",
        }
    ]
    assert len(units) == 1
    assert units[0]["unit_value"] == 1
    assert units[0]["review_status"] == "accepted"
    assert len(graph.evidence_for(claim)) == 1


def test_natural_predicate_beyond_bounded_qualifiers_stays_ambiguous() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        (
            "I painted the ancient blue cracked detailed enormous heavy "
            "ornate polished weathered fence on March 3, 2026."
        ),
        accepted=False,
    )
    claim = graph.only_claim()

    assert claim["review_status"] == "candidate"
    assert claim["resolution_status"] == "pending"
    assert claim["predicate_json"]["op"] == "unknown"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "text",
    [
        '[USER]: Alice wrote "Nothing happened. I baked cookies yesterday."',
        "[USER]: Alice wrote 'Nothing happened. I baked cookies yesterday.'",
        '[USER]: I said "Nothing happened. I baked cookies yesterday."',
        "[USER]: I said 'Nothing happened. I baked cookies yesterday.'",
        '[USER]: Alice wrote "Nothing happened.\nI baked cookies yesterday."',
        "[USER]: Alice wrote 'Nothing happened.\nI baked cookies yesterday.'",
    ],
)
def test_reported_quoted_events_never_become_user_event_carriers(text: str) -> None:
    assert occurrence_write_module.natural_occurrence_candidate_sentences(text) == ()


def test_quote_aware_split_retains_a_direct_event_after_reported_speech() -> None:
    text = '[USER]: I said "Nothing happened." I baked cookies yesterday.'

    assert occurrence_write_module.natural_occurrence_candidate_sentences(text) == (
        "[USER]: I baked cookies yesterday.",
    )


def test_calendar_month_may_does_not_look_like_a_modal() -> None:
    text = "[USER]: I visited the museum on May 5, 2026."

    assert occurrence_write_module.natural_occurrence_candidate_sentences(text) == (text,)


@pytest.mark.parametrize(
    "text",
    [
        "[USER]: I feed birds on June 5, 2026.",
        "[USER]: I seed rows on June 5, 2026.",
    ],
)
def test_present_base_verbs_ending_in_ed_never_become_completed_events(
    text: str,
) -> None:
    assert occurrence_write_module.natural_occurrence_candidate_sentences(text) == ()


def test_generic_predicate_key_ignores_descriptive_object_modifiers() -> None:
    store = _store()
    blue = _capture_natural_graph(
        store,
        "I painted the blue garden fence on March 3, 2026.",
        accepted=False,
    )
    old = _capture_natural_graph(
        store,
        "I painted the old wooden fence on March 4, 2026.",
        accepted=False,
    )

    assert blue.only_claim()["count_key"] == "painted fence"
    assert old.only_claim()["count_key"] == "painted fence"


@pytest.mark.parametrize("existing_accepted", [False, True])
def test_same_date_object_ordinal_collision_stays_ambiguous(
    existing_accepted: bool,
) -> None:
    store = _store()
    first = _capture_natural_graph(
        store,
        "I visited the museum on March 3, 2026.",
        accepted=existing_accepted,
    )
    second = _capture_natural_graph(
        store,
        "We visited the museum on March 3, 2026.",
        accepted=False,
    )
    first_claim = first.only_claim()
    first_units = first.units_for(first_claim)
    assert len(first_units) == 1
    assert first_units[0]["review_status"] == ("accepted" if existing_accepted else "candidate")

    collision_claim = second.only_claim()
    assert collision_claim["identity_basis"] == "date_and_ordinal"
    assert _claim_identity_anchor(collision_claim)["stable_object"] == "museum"
    assert collision_claim["resolution_decision"] == "ambiguous"
    assert collision_claim["review_status"] == "candidate"
    assert second.units_for(collision_claim) == []


def test_capture_timestamp_does_not_become_relative_event_identity() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I painted the fence yesterday.",
        captured_at="2026-03-05T12:00:00Z",
    )
    claim = graph.only_claim()

    assert claim["identity_basis"] == "ambiguous"
    assert claim["review_status"] == "candidate"
    assert claim["occurred_at_start"] is None
    assert graph.units_for(claim) == []
    assert claim["resolution_status"] == "pending"


def test_positive_structured_date_ordinal_is_proposed_then_reviewed() -> None:
    store = _store()
    memory = _memory(
        store,
        "I visited the museum on March 3, 2026.",
        status="candidate",
        metadata_json={
            "occurrence_input": {
                **_structured_occurrence_contract(),
                "occurred_at_start": "2026-03-03",
                "occurred_at_end": "2026-03-03",
                "stable_object": "museum",
                "reviewed_date_ordinal": 2,
            }
        },
    )

    proposed = _establish(store, memory, accepted=False, stage="capture")
    proposed_record = _proposal_record(proposed)
    proposed_units = store.list_occurrence_units_for_claim(str(proposed_record["claim_id"]))
    assert proposed_record["identity_basis"] == "date_and_ordinal"
    assert proposed_record["identity_anchor"]["reviewed_date_ordinal"] == 2
    assert proposed_record["materialization_status"] == "pending_review"
    assert len(proposed_units) == 1
    assert proposed_units[0]["review_status"] == "candidate"

    active = store.update_memory(
        memory_id=str(memory["id"]),
        patch={"status": "active"},
        actor_type="user",
    )
    reviewed = _establish(store, active, accepted=True, stage="review_accept")
    reviewed_record = _proposal_record(reviewed)
    units = store.list_occurrence_units_for_claim(str(reviewed_record["claim_id"]))

    assert reviewed_record["identity_basis"] == "date_and_ordinal"
    assert reviewed_record["identity_anchor"]["reviewed_date_ordinal"] == 2
    assert reviewed_record["materialization_status"] == "accepted"
    assert reviewed_record["claim_id"] == proposed_record["claim_id"]
    assert len(units) == 1


def test_structured_candidate_replays_immutable_rows_at_acceptance() -> None:
    store = _store()
    memory = _memory(
        store,
        "I visited the museum.",
        status="candidate",
        metadata_json={"occurrence_input": _explicit_event("candidate-replay")},
    )

    proposed = _establish(store, memory, accepted=False, stage="capture")
    proposed_record = _proposal_record(proposed)
    candidate_units = store.list_occurrence_units_for_claim(str(proposed_record["claim_id"]))
    assert len(candidate_units) == 1
    assert candidate_units[0]["review_status"] == "candidate"

    active = store.update_memory(
        memory_id=str(memory["id"]),
        patch={"status": "active"},
        actor_type="user",
    )
    reviewed = _establish(store, active, accepted=True, stage="review_accept")
    reviewed_record = _proposal_record(reviewed)
    accepted_units = store.list_occurrence_units_for_claim(str(reviewed_record["claim_id"]))

    assert reviewed_record["claim_id"] == proposed_record["claim_id"]
    assert len(accepted_units) == 1
    assert accepted_units[0]["id"] == candidate_units[0]["id"]
    assert accepted_units[0]["review_status"] == "accepted"


def test_structured_manual_identity_is_candidate_then_reviewed() -> None:
    store = _store()
    memory = _memory(
        store,
        "I joined the manually identified workshop.",
        status="candidate",
        metadata_json={
            "occurrence_input": {
                **_structured_occurrence_contract(
                    count_key="workshop attendance",
                    action="attend",
                    object_leaf="workshop",
                ),
                "reviewed_manual_identity": "workshop:team-offsite:2026",
            }
        },
    )

    proposed = _establish(store, memory, accepted=False, stage="capture")
    proposed_record = _proposal_record(proposed)
    candidate = store.list_occurrence_units_for_claim(str(proposed_record["claim_id"]))
    assert proposed_record["identity_basis"] == "reviewed_manual"
    assert proposed_record["materialization_status"] == "pending_review"
    assert len(candidate) == 1 and candidate[0]["review_status"] == "candidate"

    active = store.update_memory(
        memory_id=str(memory["id"]),
        patch={"status": "active"},
        actor_type="user",
    )
    reviewed = _establish(store, active, accepted=True, stage="review_accept")
    reviewed_record = _proposal_record(reviewed)
    unit = store.list_occurrence_units_for_claim(str(reviewed_record["claim_id"]))

    assert reviewed_record["claim_id"] == proposed_record["claim_id"]
    assert reviewed_record["materialization_status"] == "accepted"
    assert len(unit) == 1 and unit[0]["review_status"] == "accepted"


def test_booked_remains_an_exact_surface_without_inferring_a_dentist_visit() -> None:
    store = _store()
    text = "I booked the dentist on March 3, 2026."
    natural = _capture_natural_graph(store, text)
    natural_claim = natural.only_claim()

    assert natural_claim["count_key"] == "booked dentist"
    assert natural_claim["predicate_json"]["action"]["leaf"] == "booked"
    assert natural_claim["predicate_json"]["object"]["leaf"] == "dentist"

    explicit = _memory(
        store,
        text,
        metadata_json={
            "occurrence_input": _explicit_event(
                "booking-1",
                count_key="book dentist",
                action="book",
                object_leaf="dentist",
            )
        },
    )
    reviewed = _establish(store, explicit)
    record = _proposal_record(reviewed)

    assert record["materialization_status"] == "accepted"
    assert len(store.list_occurrence_units_for_claim(str(record["claim_id"]))) == 1


@pytest.mark.parametrize(
    ("field", "invalid_quantity", "message"),
    [
        ("quantity_min", True, "quantity_min must be a positive integer"),
        ("quantity_min", 2.5, "quantity_min must be a positive integer"),
        ("quantity_min", "2", "quantity_min must be a positive integer"),
        ("quantity_max", True, "quantity_max must be at least quantity_min"),
        ("quantity_max", 2.5, "quantity_max must be at least quantity_min"),
        ("quantity_max", "2", "quantity_max must be at least quantity_min"),
    ],
)
def test_structured_quantity_never_coerces_bool_float_or_string(
    field: str,
    invalid_quantity: object,
    message: str,
) -> None:
    store = _store()
    hint = _explicit_event("invalid-quantity")
    hint[field] = invalid_quantity
    memory = _memory(
        store,
        "I visited the museum.",
        metadata_json={"occurrence_input": hint},
    )

    with pytest.raises(ValueError, match=message):
        _establish(store, memory)


def test_compound_completed_predicates_fail_closed_as_one_ambiguous_claim() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I painted the fence and repaired the garden gate on March 3, 2026.",
    )
    claim = graph.only_claim()

    assert str(claim["count_key"]).startswith("compound completed event")
    assert claim["identity_basis"] == "ambiguous"
    assert claim["resolution_decision"] == "ambiguous"
    assert claim["review_status"] == "candidate"
    assert graph.units_for(claim) == []
    assert claim["quantity_max"] is None


def test_multiple_structured_predicates_never_silently_pick_the_first() -> None:
    store = _store()
    text = "I visited the museum and ate dinner."
    source = _source(
        store,
        metadata_json={
            "occurrence_inputs": [
                {
                    "canonical_text": text,
                    **_explicit_event("museum-1"),
                },
                {
                    "canonical_text": text,
                    **_explicit_event(
                        "dinner-1",
                        count_key="dinner",
                        action="eat",
                        object_leaf="dinner",
                    ),
                },
            ]
        },
    )
    memory = _memory(store, text)

    updated = _establish(store, memory, source=source)
    record = _proposal_record(updated)

    assert record["count_key"] == "compound structured occurrence"
    assert record["materialization_status"] == "ambiguous"
    assert store.list_occurrence_units_for_claim(str(record["claim_id"])) == []


def test_plural_review_accepts_all_one_value_units_without_singular_pointer() -> None:
    store = _store()
    memory = _memory(
        store,
        "I visited the museum three times.",
        metadata_json={"occurrence_input": _explicit_event("museum-series", quantity=3)},
    )

    updated = _establish(store, memory)
    record = _proposal_record(updated)
    claim = store.get_occurrence_claim(str(record["claim_id"]))
    units = store.list_occurrence_units_for_claim(str(record["claim_id"]))

    assert claim is not None
    assert claim["resolution_decision"] == "new"
    assert claim["resolved_occurrence_id"] is None
    assert len(units) == 3
    assert {unit["unit_value"] for unit in units} == {1}
    assert {unit["review_status"] for unit in units} == {"accepted"}
    assert len({unit["occurrence_key"] for unit in units}) == 3


def test_plural_identity_collision_fails_closed_before_any_unit_is_reused() -> None:
    store = _store()
    first = _memory(
        store,
        "I visited the museum once.",
        metadata_json={"occurrence_input": _explicit_event("plural-collision")},
    )
    plural = _memory(
        store,
        "I later claimed three visits to the same event.",
        metadata_json={
            "occurrence_input": _explicit_event(
                "plural-collision",
                quantity=3,
            )
        },
    )
    first_reviewed = _establish(store, first)
    first_unit_id = str(_proposal_record(first_reviewed)["occurrence_unit_ids"][0])

    reviewed = _establish(store, plural)
    record = _proposal_record(reviewed)
    claim = store.get_occurrence_claim(str(record["claim_id"]))

    assert record["resolution_decision"] == "ambiguous"
    assert record["materialization_status"] == "ambiguous"
    assert record["occurrence_unit_ids"] == []
    assert claim is not None and claim["resolution_status"] == "pending"
    assert store.list_occurrence_units_for_claim(str(record["claim_id"])) == []
    first_units = store.list_occurrence_units_for_memory(str(first["id"]))
    assert [str(unit["id"]) for unit in first_units] == [first_unit_id]


def test_same_external_event_across_memories_links_one_unit_and_refreshes_evidence() -> None:
    store = _store()
    first = _memory(
        store,
        "I visited the city museum.",
        metadata_json={"occurrence_input": _explicit_event("museum-duplicate")},
    )
    second = _memory(
        store,
        "I visited that museum.",
        metadata_json={"occurrence_input": _explicit_event("museum-duplicate")},
    )

    first_reviewed = _establish(store, first, stage="first_review")
    second_reviewed = _establish(store, second, stage="second_review")
    first_record = _proposal_record(first_reviewed)
    second_record = _proposal_record(second_reviewed)
    first_units = store.list_occurrence_units_for_claim(str(first_record["claim_id"]))
    second_units = store.list_occurrence_units_for_memory(str(second["id"]))

    assert len(first_units) == 1
    assert len(second_units) == 1
    assert second_units[0]["id"] == first_units[0]["id"]
    assert second_record["materialization_status"] == "linked_existing"
    evidence = store.list_occurrence_evidence_for_units([str(first_units[0]["id"])])
    assert {str(row["memory_id"]) for row in evidence if row.get("memory_id") is not None} == {
        str(first["id"]),
        str(second["id"]),
    }


def test_retiring_one_deduped_memory_preserves_unit_with_other_live_evidence() -> None:
    store = _store()
    first = _memory(
        store,
        "I visited the city museum.",
        metadata_json={"occurrence_input": _explicit_event("shared-event")},
    )
    second = _memory(
        store,
        "I visited that museum.",
        metadata_json={"occurrence_input": _explicit_event("shared-event")},
    )
    first_reviewed = _establish(store, first, stage="first_review")
    second_reviewed = _establish(store, second, stage="second_review")
    unit_id = str(_proposal_record(first_reviewed)["occurrence_unit_ids"][0])

    affected = VNextMemoryCommitService(store).retire_memory_occurrence_state(
        first_reviewed,
        stage="test_first_memory_retired",
        reason="The first duplicate carrier was removed.",
    )
    unit = store.get_occurrence_unit_by_key(
        str(store.list_occurrence_units_for_memory(str(second["id"]))[0]["occurrence_key"])
    )
    evidence = store.list_occurrence_evidence_for_units([unit_id])

    assert affected == [unit_id]
    assert unit is not None and unit["review_status"] == "accepted"
    assert {str(row["memory_id"]) for row in evidence if row.get("memory_id") is not None} == {
        str(second_reviewed["id"])
    }


def test_deferred_memory_retirement_touches_no_accounting_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = _source(store)
    chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": "I visited the museum.",
            "token_count": 5,
            "metadata_json": {},
        }
    )
    memory = _memory(
        store,
        "I visited the museum.",
        metadata_json={
            "source_id": str(source["id"]),
            "source_chunk_id": str(chunk["id"]),
            "occurrence_input": _explicit_event("deferred-memory-retirement"),
        },
    )
    reviewed = _establish(
        store,
        memory,
        source=source,
        source_chunk_id=str(chunk["id"]),
    )
    accounting_writes: list[str] = []
    monkeypatch.setattr(
        sqlite_occurrences,
        "invalidate_occurrence_coverage",
        lambda *_args, **_kwargs: accounting_writes.append("coverage"),
    )
    monkeypatch.setattr(
        occurrence_write_module,
        "invalidate_occurrence_accounting",
        lambda *_args, **_kwargs: accounting_writes.append("accounting"),
    )
    monkeypatch.setattr(
        occurrence_write_module,
        "reconcile_chunk_extraction_disposition",
        lambda *_args, **_kwargs: accounting_writes.append("disposition"),
    )

    VNextMemoryCommitService(store).retire_memory_occurrence_state(
        reviewed,
        stage="deferred_bundle",
        reason="The bundled carrier reset is still reconciling.",
        preserve_claim=True,
        _defer_occurrence_accounting=True,
    )

    assert accounting_writes == []


def test_deferred_source_retirement_touches_no_accounting_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited museums on March 3, 2026.",
        session_date="2026-03-05T12:00:00Z",
    )
    accounting_writes: list[str] = []
    monkeypatch.setattr(
        sqlite_occurrences,
        "invalidate_occurrence_coverage",
        lambda *_args, **_kwargs: accounting_writes.append("coverage"),
    )
    monkeypatch.setattr(
        occurrence_write_module,
        "invalidate_occurrence_accounting",
        lambda *_args, **_kwargs: accounting_writes.append("accounting"),
    )

    VNextMemoryCommitService(store).retire_source_occurrence_state(
        str(graph.source["id"]),
        stage="deferred_bundle",
        reason="The bundled source reset is still reconciling.",
        _defer_occurrence_accounting=True,
    )

    assert accounting_writes == []


def test_chunk_accounting_invalidation_forwards_coverage_defer() -> None:
    calls: list[dict[str, object]] = []

    class _DispositionStore:
        def invalidate_occurrence_extraction_dispositions(
            self,
            **kwargs: object,
        ) -> None:
            calls.append(dict(kwargs))

    invalidate_occurrence_accounting(
        _DispositionStore(),
        reason="The bundled reset will invalidate coverage once at the end.",
        actor_type="user",
        source_chunk_id="11111111-1111-4111-8111-111111111111",
        _defer_occurrence_coverage=True,
    )

    assert len(calls) == 1
    assert calls[0]["_defer_occurrence_coverage"] is True


def test_source_retirement_preserves_unit_when_reviewed_memory_survives() -> None:
    store = _store()
    source = _source(store)
    memory = _memory(
        store,
        "I visited the museum.",
        metadata_json={"occurrence_input": _explicit_event("source-retirement")},
    )
    reviewed = _establish(store, memory, source=source)
    unit_id = str(_proposal_record(reviewed)["occurrence_unit_ids"][0])
    service = VNextMemoryCommitService(store)

    affected = service.retire_source_occurrence_state(
        str(source["id"]),
        stage="test_source_delete",
        reason="The source was deleted.",
    )
    unit = store.list_occurrence_units_for_memory(str(memory["id"]))[0]
    evidence = store.list_occurrence_evidence_for_units([unit_id])

    assert affected == [unit_id]
    assert unit["review_status"] == "accepted"
    assert len(evidence) == 1
    assert evidence[0]["memory_id"] == memory["id"]
    assert evidence[0]["source_id"] is None


def test_memory_forget_retires_its_reviewed_occurrence_unit() -> None:
    store = _store()
    memory = _memory(
        store,
        "I visited the museum.",
        metadata_json={"occurrence_input": _explicit_event("museum-forget")},
    )
    reviewed = _establish(store, memory)
    record = _proposal_record(reviewed)
    units = store.list_occurrence_units_for_claim(str(record["claim_id"]))
    assert len(units) == 1 and units[0]["review_status"] == "accepted"

    VNextMemoryCommitService(store).forget(
        identity=None,
        memory_id=str(memory["id"]),
        reason="The user removed this memory.",
    )

    retired = store.list_occurrence_units_for_claim(str(record["claim_id"]))
    assert len(retired) == 1
    assert retired[0]["review_status"] == "retired"


def test_memory_correction_retires_old_unit_without_natural_reparse() -> None:
    store = _store()
    original = _memory(
        store,
        "I visited the museum on March 3, 2026.",
        metadata_json={"occurrence_input": _explicit_event("corrected-memory")},
    )
    reviewed = _establish(store, original)
    original_record = _proposal_record(reviewed)
    original_unit_id = str(original_record["occurrence_unit_ids"][0])
    metadata = dict(reviewed["metadata_json"])
    metadata.pop("occurrence_input")
    reviewed = store.update_memory(
        memory_id=str(reviewed["id"]),
        patch={"metadata_json": metadata},
        actor_type="user",
    )

    result = VNextMemoryCommitService(store).correct(
        identity=None,
        memory_id=str(reviewed["id"]),
        canonical_text="I visited the gallery on March 4, 2026.",
        reason="The reviewer corrected the event.",
    )
    corrected = result["memory"]
    original_unit = store.list_occurrence_units_for_claim(str(original_record["claim_id"]))[0]
    corrected_metadata = corrected["metadata_json"]
    assert isinstance(corrected_metadata, dict)

    assert str(original_unit["id"]) == original_unit_id
    assert original_unit["review_status"] == "retired"
    assert OCCURRENCE_PROPOSAL_METADATA_KEY not in corrected_metadata
    assert OCCURRENCE_INVALIDATION_METADATA_KEY in corrected_metadata
    corrected_units = store.list_occurrence_units_for_memory(str(corrected["id"]))
    assert [str(unit["id"]) for unit in corrected_units] == [original_unit_id]
    assert {unit["review_status"] for unit in corrected_units} == {"retired"}
    assert (
        store.conn.execute(
            "SELECT COUNT(*) FROM occurrence_claims WHERE user_id = ?",
            (store.user_id,),
        ).fetchone()[0]
        == 1
    )


def test_true_redaction_retires_occurrence_before_scrubbing_and_replays_without_write() -> None:
    store = _store()
    memory = _memory(
        store,
        "I visited the museum.",
        metadata_json={"occurrence_input": _explicit_event("museum-redact")},
    )
    reviewed = _establish(store, memory)
    record = _proposal_record(reviewed)
    units = store.list_occurrence_units_for_claim(str(record["claim_id"]))
    assert len(units) == 1 and units[0]["review_status"] == "accepted"

    first = redact_memory_flow(
        store,
        memory_id=str(memory["id"]),
        reason="The user requested erasure.",
    )
    retired = store.list_occurrence_units_for_claim(str(record["claim_id"]))[0]
    first_version = retired["review_version"]

    second = redact_memory_flow(
        store,
        memory_id=str(memory["id"]),
        reason="The user requested erasure.",
    )
    replayed = store.list_occurrence_units_for_claim(str(record["claim_id"]))[0]

    assert first["idempotent_replay"] is False
    assert retired["review_status"] == "retired"
    assert second["idempotent_replay"] is True
    assert replayed["review_version"] == first_version


def test_reconcile_uses_one_bounded_lookup_and_no_source_wide_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="note",
            raw_text="Neutral heading without a memory extraction rule",
        )
    )
    chunk = store.list_source_chunks(str(result.source_id))[0]
    for index in range(40):
        _memory(store, f"Unrelated memory {index}.", status="candidate")

    bounded_lookup = store.list_memories_for_source_chunk
    chunk_lookup = store.get_source_chunk_for_occurrence_accounting
    memory_calls: list[str] = []
    chunk_calls: list[str] = []

    def recording_lookup(source_chunk_id: str) -> list[dict[str, object]]:
        memory_calls.append(source_chunk_id)
        return bounded_lookup(source_chunk_id)

    def recording_chunk_lookup(source_chunk_id: str) -> dict[str, object] | None:
        chunk_calls.append(source_chunk_id)
        return chunk_lookup(source_chunk_id)

    def fail_unbounded(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        raise AssertionError("production reconciliation must not scan the memory corpus")

    def fail_source_scan(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        raise AssertionError("raw assertion guard must use the targeted chunk row")

    monkeypatch.setattr(store, "list_memories_for_source_chunk", recording_lookup)
    monkeypatch.setattr(
        store,
        "get_source_chunk_for_occurrence_accounting",
        recording_chunk_lookup,
    )
    monkeypatch.setattr(store, "list_memories", fail_unbounded)
    monkeypatch.setattr(store, "get_source_chunks_by_ids", fail_source_scan)
    monkeypatch.setattr(store, "list_source_chunks", fail_source_scan)

    disposition = reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
    )

    assert disposition is not None
    assert disposition["disposition"] == "no_occurrence"
    assert memory_calls == [str(chunk["id"])]
    assert chunk_calls == [str(chunk["id"])]


def test_reconcile_binds_title_guard_and_record_to_same_chunk_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "title": "I published a release",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "personal",
            "sensitivity": "private",
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "I published a release.\n[USER]: Hello.",
        }
    )
    targeted_lookup = store.get_source_chunk_for_occurrence_accounting
    record = store.record_occurrence_extraction_disposition
    looked_up: list[dict[str, object]] = []
    forwarded: list[str | None] = []

    def recording_lookup(source_chunk_id: str) -> dict[str, object] | None:
        row = targeted_lookup(source_chunk_id)
        if row is not None:
            looked_up.append(dict(row))
        return row

    def recording_record(*args: object, **kwargs: object) -> object:
        forwarded.append(
            str(kwargs["expected_snapshot_sha256"]) if kwargs.get("expected_snapshot_sha256") is not None else None
        )
        return record(*args, **kwargs)

    def fail_secondary_source_read(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("title guard must use the signed targeted chunk envelope")

    monkeypatch.setattr(
        store,
        "get_source_chunk_for_occurrence_accounting",
        recording_lookup,
    )
    monkeypatch.setattr(store, "record_occurrence_extraction_disposition", recording_record)
    monkeypatch.setattr(store, "get_source", fail_secondary_source_read)

    disposition = reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
    )

    assert disposition is not None
    assert disposition["disposition"] == "no_occurrence"
    assert disposition["metadata_json"]["raw_no_occurrence_guard"] is False
    assert len(looked_up) == 1
    assert looked_up[0]["source_title"] == "I published a release"
    assert forwarded == [looked_up[0]["snapshot_sha256"]]


def test_reconcile_title_snapshot_race_fails_before_autoaccept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "title": "I published a release",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "personal",
            "sensitivity": "private",
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "I published a release.\n[USER]: Hello.",
        }
    )
    record = store.record_occurrence_extraction_disposition

    def mutate_title_then_record(*args: object, **kwargs: object) -> object:
        updated = store.conn.execute(
            "UPDATE sources SET title = ? WHERE user_id = ? AND id = ?",
            ("Different title", store.user_id, str(source["id"])),
        )
        assert updated.rowcount == 1
        return record(*args, **kwargs)

    monkeypatch.setattr(
        store,
        "record_occurrence_extraction_disposition",
        mutate_title_then_record,
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="snapshot CAS is stale",
    ):
        reconcile_chunk_extraction_disposition(
            store,
            source_chunk_id=str(chunk["id"]),
            actor_type="user",
            reviewer_id="reviewer",
            reason="This must not sign a stale title-derived decision.",
        )
    persisted = store.conn.execute(
        """
        SELECT review_status
        FROM occurrence_extraction_dispositions
        WHERE user_id = ? AND source_chunk_id = ?
        """,
        (store.user_id, str(chunk["id"])),
    ).fetchall()
    assert persisted == []


def test_reconcile_accepts_uuid_source_id_from_targeted_chunk_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="note",
            raw_text="Neutral heading without a memory extraction rule",
        )
    )
    chunk = store.list_source_chunks(str(result.source_id))[0]
    targeted_lookup = store.get_source_chunk_for_occurrence_accounting

    def uuid_source_lookup(source_chunk_id: str) -> dict[str, object] | None:
        row = targeted_lookup(source_chunk_id)
        if row is None:
            return None
        return {
            **row,
            "source_id": UUID(str(row["source_id"])),
        }

    monkeypatch.setattr(
        store,
        "get_source_chunk_for_occurrence_accounting",
        uuid_source_lookup,
    )

    disposition = reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
    )

    assert disposition is not None
    assert disposition["disposition"] == "no_occurrence"


@pytest.mark.parametrize(
    "malformed_fields",
    (
        {},
        {"source_id": "", "text": "Neutral text."},
        {"source_id": "source-id"},
        {"source_id": "source-id", "text": None},
    ),
)
def test_reconcile_fails_closed_on_malformed_targeted_chunk_row(
    monkeypatch: pytest.MonkeyPatch,
    malformed_fields: dict[str, object],
) -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="note",
            raw_text="Neutral heading without a memory extraction rule",
        )
    )
    chunk = store.list_source_chunks(str(result.source_id))[0]
    malformed = {"id": str(chunk["id"]), **malformed_fields}
    monkeypatch.setattr(
        store,
        "get_source_chunk_for_occurrence_accounting",
        lambda _source_chunk_id: malformed,
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="could not resolve its source chunk",
    ):
        reconcile_chunk_extraction_disposition(
            store,
            source_chunk_id=str(chunk["id"]),
            actor_type="system",
        )


def test_reconcile_legacy_store_without_snapshot_envelope_fails_closed() -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="note",
            raw_text="Neutral heading without a memory extraction rule",
        )
    )
    chunk = store.list_source_chunks(str(result.source_id))[0]
    fast = reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
    )
    assert fast is not None

    class LegacyDispositionStore:
        def __init__(self, delegate: SQLiteVNextStore) -> None:
            self.delegate = delegate
            self.list_calls = 0
            self.chunk_batch_calls = 0
            self.source_list_calls = 0

        def __getattr__(self, name: str) -> object:
            if name in {
                "get_source_chunk_for_occurrence_accounting",
                "list_memories_for_source_chunk",
            }:
                raise AttributeError(name)
            return getattr(self.delegate, name)

        def list_memories(self, *, status: str | None = None) -> list[dict[str, object]]:
            self.list_calls += 1
            return self.delegate.list_memories(status=status)

        def get_source_chunks_by_ids(
            self,
            chunk_ids: list[str],
        ) -> list[dict[str, object]]:
            self.chunk_batch_calls += 1
            return self.delegate.get_source_chunks_by_ids(chunk_ids)

        def list_source_chunks(self, source_id: str) -> list[dict[str, object]]:
            self.source_list_calls += 1
            return self.delegate.list_source_chunks(source_id)

    legacy = LegacyDispositionStore(store)
    fallback = reconcile_chunk_extraction_disposition(
        legacy,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
    )

    assert fallback is None
    assert legacy.list_calls == 0
    assert legacy.chunk_batch_calls == 0
    assert legacy.source_list_calls == 0


def test_reconcile_fails_closed_before_writes_when_chunk_exceeds_memory_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = _source(store)
    chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": "Oversized occurrence reconciliation chunk.",
            "token_count": 4,
            "metadata_json": {},
        }
    )
    chunk_id = str(chunk["id"])
    for index in range(201):
        _memory(
            store,
            f"Oversized occurrence memory {index}.",
            status="candidate",
            metadata_json={
                "source_chunk_id": chunk_id,
                OCCURRENCE_PROPOSAL_METADATA_KEY: {
                    "source_chunk_id": chunk_id,
                },
            },
        )

    def fail_write(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("over-cap reconciliation must fail before disposition writes")

    monkeypatch.setattr(store, "record_occurrence_extraction_disposition", fail_write)
    monkeypatch.setattr(store, "review_occurrence_extraction_disposition", fail_write)

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="exceeds the bounded memory limit",
    ):
        reconcile_chunk_extraction_disposition(
            store,
            source_chunk_id=chunk_id,
            actor_type="system",
            reviewer_id="reviewer",
            reason="Must fail before review.",
        )


def test_backdated_capture_revokes_signed_complete_history_before_write() -> None:
    store = _store()
    qualified = _qualify_complete_coverage(store)

    VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text="[USER]: I visited the museum on March 3, 2026.",
            source_created_at="2026-03-04T12:00:00Z",
            domain="personal",
            sensitivity="private",
        )
    )
    coverage = store.get_occurrence_coverage()

    assert coverage is not None
    assert coverage["coverage_mode"] == "forward_only"
    assert coverage["historical_review_status"] == "not_reviewed"
    assert coverage["complete_through"] is None
    assert coverage["review_receipt_digest"] is None
    assert coverage["review_version"] == int(qualified["review_version"]) + 1


def test_rejecting_reviewed_event_invalidates_disposition_and_exact_coverage() -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text="[USER]: I visited the museum on March 3, 2026.",
            source_created_at="2026-03-04T12:00:00Z",
            domain="personal",
            sensitivity="private",
        )
    )
    assert result.candidate_memory_count == 0
    assert store.list_memories(status=None) == []
    source = store.get_source(str(result.source_id))
    assert source is not None
    chunk = store.list_source_chunks(str(result.source_id))[0]
    graph = _read_direct_graph(
        store,
        source=source,
        chunk=chunk,
        text=str(chunk["text"]),
        accepted=True,
    )
    claim = graph.only_claim()
    unit = graph.units_for(claim)[0]
    accepted_accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )
    qualified = _qualify_complete_coverage(store)

    affected = VNextMemoryCommitService(store).retire_source_occurrence_state(
        str(result.source_id),
        stage="test_event_reject",
        reason="The reviewer rejected the event assertion.",
    )
    reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="user",
    )
    after = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )
    coverage = store.get_occurrence_coverage()

    assert affected == [str(unit["id"])]
    assert accepted_accounting["complete"] is True
    assert accepted_accounting["items"][0]["disposition"] == ("accepted_occurrences")
    assert accepted_accounting["items"][0]["review_status"] == "accepted"
    assert after["complete"] is False
    assert after["items"][0]["disposition"] == "no_occurrence"
    assert after["items"][0]["review_status"] == "candidate"
    assert after["items"][0].get("review_receipt_digest") is None
    assert coverage is not None
    assert coverage["coverage_mode"] == "forward_only"
    assert coverage["historical_review_status"] == "not_reviewed"
    assert coverage["review_version"] == int(qualified["review_version"]) + 1


def test_acceptance_skips_only_the_provably_duplicate_outer_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = _source(store)
    chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": "I visited the museum.",
            "token_count": 4,
            "metadata_json": {},
        }
    )
    candidate = _memory(
        store,
        "I visited the museum.",
        status="candidate",
        metadata_json={
            "source_id": str(source["id"]),
            "source_chunk_id": str(chunk["id"]),
            "occurrence_input": _explicit_event("single-reconciliation"),
        },
    )
    candidate = _establish(
        store,
        candidate,
        source=source,
        source_chunk_id=str(chunk["id"]),
        accepted=False,
        stage="candidate_capture",
    )
    active = store.update_memory(
        memory_id=str(candidate["id"]),
        patch={"status": "active"},
        actor_type="user",
    )
    inner_original = occurrence_write_module.reconcile_chunk_extraction_disposition
    outer_original = memory_commit_module.reconcile_chunk_extraction_disposition
    calls = {"inner": 0, "outer": 0}

    def recording_inner(*args: Any, **kwargs: Any) -> dict[str, object] | None:
        calls["inner"] += 1
        return inner_original(*args, **kwargs)

    def recording_outer(*args: Any, **kwargs: Any) -> dict[str, object] | None:
        calls["outer"] += 1
        return outer_original(*args, **kwargs)

    monkeypatch.setattr(
        occurrence_write_module,
        "reconcile_chunk_extraction_disposition",
        recording_inner,
    )
    monkeypatch.setattr(
        memory_commit_module,
        "reconcile_chunk_extraction_disposition",
        recording_outer,
    )

    VNextMemoryCommitService(store).reconcile_memory_occurrence_state(
        active,
        stage="single_reconciliation_review",
    )

    assert calls == {"inner": 1, "outer": 0}


def test_non_occurrence_acceptance_retains_outer_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text="Fact: The museum calendar was useful for future planning.",
        )
    )
    candidate = store.list_memories(status="candidate")[0]
    active = store.update_memory(
        memory_id=str(candidate["id"]),
        patch={"status": "active"},
        actor_type="user",
    )
    inner_original = occurrence_write_module.reconcile_chunk_extraction_disposition
    outer_original = memory_commit_module.reconcile_chunk_extraction_disposition
    calls = {"inner": 0, "outer": 0}

    def recording_inner(*args: Any, **kwargs: Any) -> dict[str, object] | None:
        calls["inner"] += 1
        return inner_original(*args, **kwargs)

    def recording_outer(*args: Any, **kwargs: Any) -> dict[str, object] | None:
        calls["outer"] += 1
        return outer_original(*args, **kwargs)

    monkeypatch.setattr(
        occurrence_write_module,
        "reconcile_chunk_extraction_disposition",
        recording_inner,
    )
    monkeypatch.setattr(
        memory_commit_module,
        "reconcile_chunk_extraction_disposition",
        recording_outer,
    )

    VNextMemoryCommitService(store).reconcile_memory_occurrence_state(
        active,
        stage="non_occurrence_single_reconciliation_review",
    )

    assert calls == {"inner": 0, "outer": 1}


@pytest.mark.parametrize(
    "text",
    [
        "Did I visit the museum?",
        "Have I visited the museum?",
        "Had I visited the museum?",
        "If I visited the museum, tell me.",
        "Unless I visited the museum, the count is zero.",
        "Someone claimed I visited the museum.",
        'I said "I visited the museum."',
        "Do you remember if I visited the museum?",
    ],
)
def test_natural_question_conditional_and_attribution_guards_create_no_claim(
    text: str,
) -> None:
    store = _store()
    assert _capture_natural_graph(store, text).claims == []


@pytest.mark.parametrize(
    "text",
    [
        "I visited no museums on March 3, 2026.",
        "I bought zero albums on March 3, 2026.",
        "I had no appointments on March 3, 2026.",
        "I visited neither museum on March 3, 2026.",
        "I visited not one museum on March 3, 2026.",
        "I visited nil museums on March 3, 2026.",
        "I visited nought museums on March 3, 2026.",
        "I attended none of the conferences on March 3, 2026.",
        "I completed not a single workshop on March 3, 2026.",
    ],
)
def test_explicit_zero_object_cardinality_creates_no_occurrence_claim(
    text: str,
) -> None:
    store = _store()
    assert _capture_natural_graph(store, text).claims == []


@pytest.mark.parametrize(
    "text",
    [
        "I visited hardly any museums on March 3, 2026.",
        "I visited scarcely any museums on March 3, 2026.",
        "I visited barely any museums on March 3, 2026.",
        "I visited some museums on March 3, 2026.",
    ],
)
def test_vague_object_cardinality_stays_unresolved(
    text: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(store, text)
    claim = graph.only_claim()

    assert claim["review_status"] == "candidate"
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "text",
    [
        "I had not visited the museum on March 3, 2026.",
        "I hadn't visited the museum on March 3, 2026.",
        "I hadn’t visited the museum on March 3, 2026.",
    ],
)
def test_had_not_forms_create_no_occurrence_claim(text: str) -> None:
    store = _store()
    assert _capture_natural_graph(store, text).claims == []


def test_bare_had_never_uses_a_semantic_noun_allowlist() -> None:
    store = _store()
    appointment = _capture_natural_graph(
        store,
        "I had a dental appointment on March 2, 2026.",
    )
    state = _capture_natural_graph(
        store,
        "I had a car on March 3, 2026.",
    )

    assert appointment.claims == []
    assert state.claims == []


def test_zero_object_statement_cannot_inflate_an_exact_count() -> None:
    store = _store()
    real = _capture_natural_graph(
        store,
        "I visited museums on March 2, 2026.",
    )
    zero = _capture_natural_graph(
        store,
        "I visited no museums on March 3, 2026.",
    )

    assert real.only_claim()["resolution_status"] == "resolved"
    assert zero.claims == []
    _qualify_complete_coverage(store)
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times have I visited museums?",
            domains=("personal",),
        )
    )

    aggregation = pack["aggregation"]
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["exact"] is True
    assert aggregation["count"] == 1
    assert aggregation["lower_bound"] == aggregation["upper_bound"] == 1


def test_trusted_assistant_provenance_suppresses_untagged_natural_event() -> None:
    store = _store()
    assistant = _capture_natural_graph(
        store,
        "[ASSISTANT]: I visited the museum on March 3, 2026.",
    )
    user = _capture_natural_graph(
        store,
        "[USER]: I visited the gallery on March 4, 2026.",
    )

    assert assistant.claims == []
    assert user.only_claim()["count_key"] == "visited gallery"


def test_tagged_assistant_event_is_ignored_but_user_event_is_reviewable() -> None:
    store = _store()
    assistant = _capture_natural_graph(
        store,
        "[ASSISTANT]: I visited the museum on March 3, 2026.",
    )
    user = _capture_natural_graph(
        store,
        "[USER]: I visited the museum on March 3, 2026.",
    )

    assert assistant.claims == []
    assert user.only_claim()["resolution_status"] == "resolved"


def test_declarative_sentence_before_trailing_question_remains_eligible() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I baked cookies last Thursday. Should I make more?",
        session_date="2026-07-24T12:00:00Z",
    )
    claim = graph.only_claim()

    assert claim["count_key"] == "baked cookies"
    assert claim["occurred_at_start"] == "2026-07-23T00:00:00.000000Z"
    assert claim["resolution_status"] == "resolved"


def test_relative_date_preserves_the_session_dates_stated_local_day() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited the museum yesterday.",
        session_date="2026-07-24T00:30:00+02:00",
    )
    claim = graph.only_claim()

    assert claim["occurred_at_start"] == "2026-07-23T00:00:00.000000Z"
    assert claim["occurred_at_end"] == "2026-07-23T00:00:00.000000Z"
    assert claim["resolution_status"] == "resolved"


def test_benchmark_shaped_nested_context_does_not_create_a_claim() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        (
            "I've had good results with the convection setting on my oven, "
            "like when I used it to bake a batch of cookies last Thursday."
        ),
        session_date="2026-07-24T12:00:00Z",
    )

    assert graph.claims == []


def test_unrelated_nested_completed_event_uses_exact_lexical_predicate() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I used a ceramic wheel to shape a smooth clay bowl last Thursday.",
        session_date="2026-07-24T12:00:00Z",
    )
    claim = graph.only_claim()

    assert claim["count_key"] == "shape bowl"
    assert claim["occurred_at_start"] == "2026-07-23T00:00:00.000000Z"
    assert claim["resolution_status"] == "resolved"
    assert claim["predicate_json"]["object"] == {
        "leaf": "bowl",
        "qualifiers": ["clay", "smooth"],
        "ancestors": [],
    }


def test_complex_measure_relation_stays_unresolved_without_a_measure_allowlist() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I baked a tray of saffron buns on March 3, 2026.",
    )
    claim = graph.only_claim()

    assert claim["count_key"] == "baked buns"
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


def test_regular_past_surfaces_and_n_weeks_ago_resolve_without_topic_alias() -> None:
    store = _store()
    baked = _capture_natural_graph(
        store,
        "I baked cookies two weeks ago.",
        session_date="2026-07-24T12:00:00Z",
    )
    created = _capture_natural_graph(
        store,
        "I created a clay sculpture two weeks ago.",
        session_date="2026-07-24T12:00:00Z",
    )

    baked_claim = baked.only_claim()
    created_claim = created.only_claim()

    assert baked_claim["count_key"] == "baked cookies"
    assert created_claim["count_key"] == "created sculpture"
    assert baked_claim["occurred_at_start"] == "2026-07-10T00:00:00.000000Z"
    assert created_claim["occurred_at_start"] == "2026-07-10T00:00:00.000000Z"


@pytest.mark.parametrize(
    "text",
    [
        "I drove a blue coupe on March 2, 2026.",
        "I flew a red kite on March 3, 2026.",
        "I went hiking on March 4, 2026.",
        "I left the library on March 5, 2026.",
        "I taught a pottery class on March 6, 2026.",
    ],
)
def test_unsourced_irregular_inflections_require_structured_review(
    text: str,
) -> None:
    store = _store()

    assert _capture_natural_graph(store, text).claims == []


@pytest.mark.parametrize(
    "text",
    [
        "I visited the Louvre on March 2, 2026.",
        'I visited the "North Gallery" on March 3, 2026.',
    ],
)
def test_natural_named_or_quoted_mentions_never_propose_object_members(
    text: str,
) -> None:
    store = _store()
    claim = _capture_natural_graph(store, text).only_claim()

    assert claim["aggregation_json"]["bases"] == [
        {
            "basis": "event_instance",
            "identity_basis": "occurrence_key",
        }
    ]


@pytest.mark.parametrize(
    "text",
    [
        "I have been to Oslo on March 2, 2026.",
        "I read the handbook on March 3, 2026.",
    ],
)
def test_unregistered_or_ambiguous_irregular_forms_fail_closed(
    text: str,
) -> None:
    store = _store()

    assert _capture_natural_graph(store, text).claims == []


@pytest.mark.parametrize(
    "date_text",
    ["December 30", "12/30"],
)
def test_future_yearless_date_stays_ambiguous_at_year_boundary(
    date_text: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        f"I visited the museum on {date_text}.",
        session_date="2026-01-05T12:00:00Z",
    )
    claim = graph.only_claim()

    assert claim["occurred_at_start"] is None
    assert claim["occurred_at_end"] is None
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "date_text",
    ["December 30", "12/30"],
)
def test_past_yearless_date_in_reference_year_remains_resolvable(
    date_text: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        f"I visited the museum on {date_text}.",
        session_date="2026-12-31T12:00:00Z",
    )
    claim = graph.only_claim()

    assert claim["occurred_at_start"] == "2026-12-30T00:00:00.000000Z"
    assert claim["occurred_at_end"] == "2026-12-30T00:00:00.000000Z"
    assert claim["resolution_status"] == "resolved"


def test_locale_ambiguous_slash_date_never_becomes_strong_identity() -> None:
    store = _store()
    graph = _capture_natural_graph(store, "I visited the museum on 03/04/2026.")
    claim = graph.only_claim()

    assert claim["occurred_at_start"] is None
    assert claim["occurred_at_end"] is None
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "text",
    [
        "I visited the museum yesterday and today.",
        "I visited the museum today and yesterday.",
        "I visited the museum today on March 3, 2026.",
    ],
)
def test_multiple_natural_date_cues_stay_ambiguous(text: str) -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        text,
        session_date="2026-03-04T12:00:00Z",
    )
    claim = graph.only_claim()

    assert claim["occurred_at_start"] is None
    assert claim["occurred_at_end"] is None
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "date_text",
    ["2027-03-03", "March 3, 2027", "03/30/2027"],
)
def test_explicit_future_completed_event_date_stays_ambiguous(
    date_text: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        f"I visited the museum on {date_text}.",
        session_date="2026-03-04T12:00:00Z",
    )
    claim = graph.only_claim()

    assert claim["occurred_at_start"] is None
    assert claim["occurred_at_end"] is None
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    ("text", "expected_key"),
    [
        (
            "I visited the museum, and it was great on March 3, 2026.",
            "visited museum",
        ),
        (
            "I visited the museum and loved it on March 3, 2026.",
            "compound completed event visited loved",
        ),
        (
            "I visited the museum, which was two times larger on March 3, 2026.",
            "visited museum",
        ),
    ],
)
def test_unparsed_coordination_and_comparison_stay_ambiguous_without_false_object(
    text: str,
    expected_key: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(store, text)
    claim = graph.only_claim()

    assert claim["count_key"] == expected_key
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "text",
    [
        "I visited the museum before lunch.",
        "I visited the museum because it was free.",
    ],
)
def test_subordinate_or_unrelated_text_never_becomes_event_object_or_date(
    text: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(store, text)
    claim = graph.only_claim()

    assert claim["count_key"] == "visited museum"
    assert claim["occurred_at_start"] is None
    assert claim["resolution_status"] == "pending"


def test_independent_completed_sentences_keep_separate_objects_and_dates() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited the museum. I booked an appointment on March 3, 2026.",
    )
    claims = {str(claim["count_key"]): claim for claim in graph.claims}

    assert set(claims) == {"visited museum", "booked appointment"}
    assert claims["visited museum"]["occurred_at_start"] is None
    assert claims["visited museum"]["resolution_status"] == "pending"
    assert claims["booked appointment"]["occurred_at_start"] == "2026-03-03T00:00:00.000000Z"
    assert claims["booked appointment"]["resolution_status"] == "resolved"


def test_quantity_is_bound_to_event_clause_and_valid_range_keeps_predicate() -> None:
    store = _store()
    control = _capture_natural_graph(
        store,
        "I visited the museum two times on March 3, 2026.",
    )
    bounded = _capture_natural_graph(
        store,
        "I visited the museum between 2 and 3 times on March 4, 2026.",
    )

    control_claim = control.only_claim()
    bounded_claim = bounded.only_claim()

    assert control_claim["count_key"] == "visited museum"
    assert control_claim["quantity_min"] == 2
    assert control_claim["quantity_max"] == 2
    assert len(control.units_for(control_claim)) == 2
    assert bounded_claim["count_key"] == "visited museum"
    assert bounded_claim["quantity_min"] == 2
    assert bounded_claim["quantity_max"] == 3
    assert bounded_claim["resolution_status"] == "pending"


def test_reversed_natural_range_never_falls_back_to_an_exact_count() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited the museum between 3 and 2 times on March 3, 2026.",
    )
    claim = graph.only_claim()

    assert claim["count_key"] == "visited museum"
    assert claim["quantity_max"] is None
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    ("text", "expect_proposal"),
    [
        ("I visited the museum 0 times.", False),
        ("I visited the museum at least 0 times.", False),
        ("I visited the museum 1001 times.", True),
    ],
)
def test_untrusted_natural_quantity_never_aborts_capture(
    text: str,
    expect_proposal: bool,
) -> None:
    store = _store()
    graph = _capture_natural_graph(store, text)

    if not expect_proposal:
        assert graph.claims == []
    else:
        claim = graph.only_claim()
        assert claim["resolution_status"] == "pending"
        assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "text",
    [
        "I visited the museum about twice on March 3, 2026.",
        "I visited the museum roughly three times on March 3, 2026.",
        "I visited the museum three or four times on March 3, 2026.",
        "I visited the museum three-ish times on March 3, 2026.",
        "I visited the museum several times on March 3, 2026.",
        "I visited the museum many times on March 3, 2026.",
        "I visited the museum a few times on March 3, 2026.",
        "I visited the museum a couple of times on March 3, 2026.",
        "I visited the museum dozens of times on March 3, 2026.",
        "I visited the museum no more than 3 times on March 3, 2026.",
    ],
)
def test_estimated_alternative_and_vague_quantities_never_materialize_exact(
    text: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(store, text)
    claim = graph.only_claim()

    assert claim["count_key"] == "visited museum"
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    ("quantity_text", "expected_quantity"),
    [
        ("once", 1),
        ("twice", 2),
        ("exactly twice", 2),
        ("three times", 3),
    ],
)
def test_unambiguous_exact_quantity_forms_materialize_every_unit(
    quantity_text: str,
    expected_quantity: int,
) -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        f"I visited the museum {quantity_text} on March 3, 2026.",
    )
    claim = graph.only_claim()

    assert claim["count_key"] == "visited museum"
    assert claim["quantity_min"] == expected_quantity
    assert claim["quantity_max"] == expected_quantity
    assert len(graph.units_for(claim)) == expected_quantity


def test_word_bounded_range_is_preserved_but_not_falsely_exact() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited the museum between three and five times on March 3, 2026.",
    )
    claim = graph.only_claim()

    assert claim["count_key"] == "visited museum"
    assert claim["quantity_min"] == 3
    assert claim["quantity_max"] == 5
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    "text",
    [
        "According to Bob, I visited the museum on March 3, 2026.",
        "I visited the museum on March 3, 2026, according to Bob.",
        "Maybe I visited the museum on March 3, 2026.",
        "I visited the museum, right?",
    ],
)
def test_attribution_uncertainty_and_tag_questions_create_no_natural_claim(
    text: str,
) -> None:
    store = _store()
    assert _capture_natural_graph(store, text).claims == []


def test_alternative_dates_stay_ambiguous_instead_of_choosing_first() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited the museum on March 3, 2026 or March 4, 2026.",
    )
    claim = graph.only_claim()

    assert claim["count_key"] == "visited museum"
    assert claim["occurred_at_start"] is None
    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []


@pytest.mark.parametrize(
    ("past", "expected_key"),
    [
        ("baked cookies", "baked cookies"),
        ("created a clay sculpture", "created sculpture"),
        ("stopped the timer", "stopped timer"),
        ("walked the trail", "walked trail"),
    ],
)
def test_generic_past_tense_surfaces_remain_exact_predicate_identity(
    past: str,
    expected_key: str,
) -> None:
    store = _store()
    graph = _capture_natural_graph(store, f"I {past} on March 3, 2026.")
    assert graph.only_claim()["count_key"] == expected_key


@pytest.mark.parametrize(
    "text",
    [
        "I polished the meteorite on March 3, 2026.",
        "I treated the timber on March 4, 2026.",
    ],
)
def test_regular_ed_surfaces_are_review_candidates_without_lemmatization(
    text: str,
) -> None:
    store = _store()

    claim = _capture_natural_graph(store, text).only_claim()
    assert claim["predicate_json"]["action"]["leaf"] in {"polished", "treated"}


def test_accepted_non_occurrence_memory_reviews_its_chunk_no_occurrence() -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text="Fact: The museum calendar was useful for future planning.",
        )
    )
    memory = store.list_memories(status="candidate")[0]
    active = store.update_memory(
        memory_id=str(memory["id"]),
        patch={"status": "active"},
        actor_type="user",
    )

    VNextMemoryCommitService(store).reconcile_memory_occurrence_state(
        active,
        stage="non_occurrence_review",
    )
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )

    assert summary["complete"] is True
    assert summary["reviewed_current_count"] == 1
    assert summary["items"][0]["disposition"] == "no_occurrence"
    assert summary["items"][0]["review_status"] == "accepted"


def test_accepted_event_chunk_with_unaccounted_user_clause_stays_unreviewed() -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text=("[USER]: I visited the museum on March 3, 2026. Taught a class on March 4, 2026."),
            source_created_at="2026-03-05T12:00:00Z",
            domain="personal",
            sensitivity="private",
        )
    )
    assert result.candidate_memory_count == 0
    source = store.get_source(str(result.source_id))
    assert source is not None
    chunk = store.list_source_chunks(str(result.source_id))[0]
    graph = _read_direct_graph(
        store,
        source=source,
        chunk=chunk,
        text=str(chunk["text"]),
        accepted=True,
    )
    claim = graph.only_claim()
    assert claim["resolution_status"] == "resolved"
    assert len(graph.units_for(claim)) == 1
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )

    assert summary["complete"] is False
    assert summary["unreviewed_count"] == 1
    assert summary["items"][0]["disposition"] == "accepted_occurrences"
    assert summary["items"][0]["review_status"] == "candidate"


@pytest.mark.parametrize(
    "second_event",
    [
        "I baked cookies on March 4, 2026.",
        "I visited the museum on March 4, 2026.",
    ],
)
def test_one_structured_hint_cannot_account_for_two_raw_events(
    second_event: str,
) -> None:
    store = _store()
    source = _source(
        store,
        metadata_json={"session_date": "2026-03-05T12:00:00Z"},
    )
    raw_text = f"[USER]: I visited the museum on March 3, 2026. {second_event}"
    chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": raw_text,
            "token_count": len(raw_text.split()),
            "metadata_json": {},
        }
    )
    memory = _memory(
        store,
        raw_text,
        metadata_json={
            "source_id": str(source["id"]),
            "source_chunk_id": str(chunk["id"]),
            "occurrence_input": {
                **_explicit_event(
                    "structured-one-event",
                    count_key="visit museum",
                ),
            },
        },
    )

    reviewed = _establish(
        store,
        memory,
        source=source,
        source_chunk_id=str(chunk["id"]),
    )
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(source["id"])],
    )

    assert _proposal_record(reviewed)["materialization_status"] == "accepted"
    assert summary["complete"] is False
    assert summary["unreviewed_count"] == 1
    assert summary["items"][0]["disposition"] == "accepted_occurrences"
    assert summary["items"][0]["review_status"] == "candidate"


def test_unresolved_claim_cannot_hide_a_second_unaccounted_raw_event() -> None:
    store = _store()
    source = _source(
        store,
        metadata_json={"session_date": "2026-03-05T12:00:00Z"},
    )
    raw_text = "[USER]: I painted the fence several times on March 3, 2026. Taught a class on March 4, 2026."
    chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": raw_text,
            "token_count": len(raw_text.split()),
            "metadata_json": {},
        }
    )
    graph = _establish_natural_chunk_graph(
        store,
        source=source,
        chunk=chunk,
        accepted=False,
    )
    claim = graph.only_claim()
    disposition = reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
    )
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(source["id"])],
    )

    assert claim["resolution_status"] == "pending"
    assert graph.units_for(claim) == []
    assert summary["complete"] is False
    assert summary["unreviewed_count"] == 1
    assert summary["items"][0]["disposition"] == "unresolved_claims"
    assert summary["items"][0]["review_status"] == "candidate"
    assert disposition is not None
    assert disposition["metadata_json"]["raw_no_occurrence_guard"] is True


def test_multi_proposal_memory_forget_retires_every_reviewed_unit() -> None:
    store = _store()
    graph = _captured_multi_event_graph(store)
    unit_ids = {str(unit["id"]) for claim in graph.claims for unit in graph.units_for(claim)}
    assert len(unit_ids) == 2

    retired_ids = VNextMemoryCommitService(store).retire_source_occurrence_state(
        str(graph.source["id"]),
        stage="multi_event_source_forget",
        reason="The user removed the multi-event source carrier.",
    )

    retired = {
        str(unit["id"]): str(unit["review_status"])
        for claim in graph.claims
        for unit in store.list_occurrence_units_for_claim(str(claim["id"]))
    }
    assert set(retired_ids) == unit_ids
    assert retired == {unit_id: "retired" for unit_id in unit_ids}
    accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(graph.source["id"])],
    )
    assert accounting["complete"] is False


def test_multi_proposal_carrier_mutation_retires_and_invalidates_every_record() -> None:
    store = _store()
    graph = _captured_multi_event_graph(store)
    claim_ids = [str(claim["id"]) for claim in graph.claims]

    VNextMemoryCommitService(store).retire_source_occurrence_state(
        str(graph.source["id"]),
        stage="multi_event_source_mutation",
        reason="The source carrier changed and no longer supports these events.",
    )

    assert {
        str(unit["review_status"]) for claim_id in claim_ids for unit in store.list_occurrence_units_for_claim(claim_id)
    } == {"retired"}
    assert {
        str(evidence["review_status"]) for claim_id in claim_ids for evidence in _raw_claim_evidence(store, claim_id)
    } == {"rejected"}
    accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(graph.source["id"])],
    )
    assert accounting["complete"] is False


@pytest.mark.parametrize(
    ("mutation", "legacy_value"),
    [
        (
            "reordered_texts",
            [
                "I attended dinner on March 4, 2026.",
                "I baked cookies on March 3, 2026.",
            ],
        ),
        (
            "duplicate_texts",
            [
                "I baked cookies on March 3, 2026.",
                "I baked cookies on March 3, 2026.",
            ],
        ),
        (
            "over_limit_texts",
            [f"I baked batch {index} on March 3, 2026." for index in range(33)],
        ),
        (
            "duplicate_records",
            [{"claim_id": "legacy-claim"}, {"claim_id": "legacy-claim"}],
        ),
    ],
)
def test_multi_proposal_collection_tampering_fails_closed(
    mutation: str,
    legacy_value: object,
) -> None:
    store = _store()
    legacy_key = OCCURRENCE_PROPOSALS_METADATA_KEY if mutation == "duplicate_records" else "occurrence_candidate_texts"
    candidate = _memory(
        store,
        "This ordinary memory has no structured occurrence input.",
        status="candidate",
        metadata_json={legacy_key: legacy_value},
    )

    sanitized = establish_memory_occurrences(
        store,
        candidate,
        accepted=False,
        reviewer_id="reviewer-1",
        reason="Obsolete natural-memory carrier keys must stay inert.",
        actor_type="user",
        stage="legacy_collection_inert",
    )

    metadata = sanitized["metadata_json"]
    assert isinstance(metadata, dict)
    assert "occurrence_candidate_texts" not in metadata
    assert OCCURRENCE_PROPOSALS_METADATA_KEY not in metadata
    assert OCCURRENCE_PROPOSAL_METADATA_KEY not in metadata
    assert store.conn.execute("SELECT COUNT(*) FROM occurrence_claims").fetchone() == (0,)
    assert store.conn.execute("SELECT COUNT(*) FROM occurrence_units").fetchone() == (0,)
    assert store.conn.execute("SELECT COUNT(*) FROM occurrence_evidence").fetchone() == (0,)


def test_zero_candidate_chunk_requires_then_accepts_explicit_source_review() -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="note",
            raw_text="Neutral heading without a memory extraction rule",
        )
    )
    assert result.candidate_memory_count == 0
    chunks = store.list_source_chunks(str(result.source_id))
    assert len(chunks) == 1
    _assert_memory_searches_empty(store, text=str(chunks[0]["text"]))
    before = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )

    reviewed_ids = review_source_chunk_occurrences(
        store,
        source_chunk_id=str(chunks[0]["id"]),
        reviewer_id="source-reviewer",
        reason="The zero-candidate source chunk was explicitly reviewed.",
        actor_type="user",
    )
    assert reviewed_ids == []
    _assert_memory_searches_empty(store, text=str(chunks[0]["text"]))
    after = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )

    assert before["complete"] is False
    assert before["unreviewed_count"] == 1
    assert after["complete"] is True
    assert after["items"][0]["disposition"] == "no_occurrence"


@pytest.mark.parametrize(
    "raw_text",
    [
        "[USER]: I've taught a class on 2023-05-30.",
        "[USER]: Visited the museum on 2023-05-30.",
        "[USER]: My visit to the museum happened on 2023-05-30.",
        "[USER]: The museum was visited by me on 2023-05-30.",
        "[USER]: Had a meeting yesterday.",
        "[USER]: Did the laundry yesterday.",
        "[USER]: Taught a class on 2023-05-30.",
        "[USER]: Chose a venue on 2023-05-30.",
        "[USER]: Was interviewed by Acme yesterday.",
        "[USER]: My visit was helpful.",
        "[USER]: Yesterday, I taught a class.",
        "[USER]: On 2023-05-30, I taught a class.",
        "[USER]: Yes, I taught a class on 2023-05-30.",
        "[USER]: After lunch, I taught a class.",
    ],
)
def test_unrecognized_plausible_user_assertion_cannot_auto_review_no_occurrence(
    raw_text: str,
) -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text=raw_text,
            metadata_json={"session_date": "2023-05-31T12:00:00Z"},
        )
    )
    chunk = store.list_source_chunks(str(result.source_id))[0]

    reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
        reviewer_id="automated-corpus-review",
        reason="Automated fresh-corpus extraction review.",
    )
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )

    assert summary["complete"] is False
    assert summary["unreviewed_count"] == 1
    assert summary["items"][0]["disposition"] == "no_occurrence"
    assert summary["items"][0]["review_status"] == "candidate"


@pytest.mark.parametrize(
    "raw_text",
    [
        "[USER]: The trip was useful.",
        "[USER]: The meeting was important.",
        "[USER]: The event was interesting.",
        "[USER]: The appointment was relevant.",
    ],
)
def test_unowned_nominal_state_does_not_use_an_event_noun_allowlist(
    raw_text: str,
) -> None:
    store = _store()
    result = VNextCaptureService(store).capture_source(
        SourceCaptureInput(
            source_type="conversation",
            raw_text=raw_text,
        )
    )
    chunk = store.list_source_chunks(str(result.source_id))[0]

    reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(chunk["id"]),
        actor_type="system",
        reviewer_id="automated-corpus-review",
        reason="Automated fresh-corpus extraction review.",
    )
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(result.source_id)],
    )

    assert summary["complete"] is True
    assert summary["items"][0]["disposition"] == "no_occurrence"
    assert summary["items"][0]["review_status"] == "accepted"


@pytest.mark.parametrize("quantity", [200, 201])
def test_large_exact_occurrence_disposition_batches_evidence_without_truncation(
    quantity: int,
) -> None:
    store = _store()
    occurrence_input = _explicit_event(
        f"large-exact-{quantity}",
        quantity=quantity,
    )
    source = _source(
        store,
        metadata_json={"occurrence_input": occurrence_input},
    )
    carrier_text = f"Batch fixture large-exact-{quantity}."
    chunk = store.create_source_chunk(
        {
            "source_id": str(source["id"]),
            "chunk_index": 0,
            "text": carrier_text,
            "token_count": 6,
            "metadata_json": {},
        }
    )
    memory = _memory(
        store,
        carrier_text,
        metadata_json={
            "source_id": str(source["id"]),
            "source_chunk_id": str(chunk["id"]),
            "occurrence_input": occurrence_input,
        },
    )

    reviewed = _establish(
        store,
        memory,
        source=source,
        source_chunk_id=str(chunk["id"]),
    )
    record = _proposal_record(reviewed)
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(source["id"])],
    )

    assert len(record["occurrence_unit_ids"]) == quantity
    assert len(store.list_occurrence_units_for_claim(str(record["claim_id"]))) == quantity
    assert summary["complete"] is True
    assert len(summary["items"][0]["occurrence_ids"]) == quantity


def test_reviewed_source_retitle_reestablishes_same_count_identity_and_is_idempotent() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited museums on March 3, 2026.",
        session_date="2026-03-05T12:00:00Z",
    )
    claim = graph.only_claim()
    original_unit = graph.units_for(claim)[0]
    original_evidence = _raw_claim_evidence_details(
        store,
        str(claim["id"]),
    )

    store.lock_source_occurrence_envelope(str(graph.source["id"]))
    retired = VNextMemoryCommitService(store).retire_source_occurrence_state(
        str(graph.source["id"]),
        stage="http_source_review_envelope_change",
        reason="The source title occurrence input changed.",
        _defer_occurrence_accounting=True,
    )
    updated = store.update_source(
        source_id=str(graph.source["id"]),
        patch={"title": "A harmless new heading"},
        actor_type="user",
    )
    records = establish_source_chunk_occurrences(
        store,
        source=updated,
        source_chunk=graph.chunk,
        actor_type="user",
        stage="http_source_review_envelope_change",
    )
    reviewed_ids = review_source_chunk_occurrences(
        store,
        source_chunk_id=str(graph.chunk["id"]),
        reviewer_id="reviewer-2",
        reason="The retitled source snapshot was reviewed.",
        actor_type="user",
        stage="http_source_review",
        _defer_occurrence_accounting=True,
    )
    reconcile_chunk_extraction_disposition(
        store,
        source_chunk_id=str(graph.chunk["id"]),
        actor_type="user",
        reviewer_id="reviewer-2",
        reason=(
            "The retitled source snapshot was reviewed. "
            "Extraction disposition reviewed during http_source_review."
        ),
    )

    current_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
    current_evidence = _raw_claim_evidence_details(
        store,
        str(claim["id"]),
    )
    accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(graph.source["id"])],
    )

    assert retired == [str(original_unit["id"])]
    assert len(records) == 1
    assert reviewed_ids == [str(claim["id"])]
    assert current_unit["id"] == original_unit["id"]
    assert current_unit["occurrence_key"] == original_unit["occurrence_key"]
    assert current_unit["review_status"] == "accepted"
    assert current_unit["review_receipt_action"] == "reestablished"
    assert current_unit["review_version"] == int(original_unit["review_version"]) + 2
    assert current_unit["retired_at"] is None
    assert current_unit["retired_by"] is None
    assert current_unit["retirement_reason"] is None
    assert current_unit["superseded_by"] is None
    assert len(original_evidence) == 1
    assert len(current_evidence) == 2
    assert {row["review_status"] for row in current_evidence} == {
        "accepted",
        "rejected",
    }
    accepted_evidence = next(row for row in current_evidence if row["review_status"] == "accepted")
    assert accepted_evidence["review_receipt_action"] == "reestablished"
    assert accepted_evidence["unit_review_receipt_digest"] == current_unit["review_receipt_digest"]
    assert accounting["complete"] is True
    assert accounting["reviewed_current_count"] == 1

    evidence_keys = [str(row["evidence_key"]) for row in current_evidence]
    review_version = int(current_unit["review_version"])
    replayed = establish_source_chunk_occurrences(
        store,
        source=updated,
        source_chunk=graph.chunk,
        actor_type="user",
        stage="http_source_review_envelope_change",
    )
    replay_reviewed = review_source_chunk_occurrences(
        store,
        source_chunk_id=str(graph.chunk["id"]),
        reviewer_id="reviewer-2",
        reason="The same source snapshot was replayed.",
        actor_type="user",
        stage="http_source_review",
    )
    replay_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
    replay_evidence = _raw_claim_evidence_details(store, str(claim["id"]))

    assert len(replayed) == 1
    assert replay_reviewed == [str(claim["id"])]
    assert replay_unit["review_version"] == review_version
    assert [str(row["evidence_key"]) for row in replay_evidence] == evidence_keys

    _qualify_complete_coverage(store)
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times have I visited museums?",
            domains=("personal",),
        )
    )
    assert pack["aggregation"]["answer_kind"] == "exact"
    assert pack["aggregation"]["count"] == 1


def test_sqlite_second_retitle_under_source_lock_preserves_signed_identity_and_replay() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited museums on March 3, 2026.",
        session_date="2026-03-05T12:00:00Z",
    )
    claim = graph.only_claim()
    original_unit = graph.units_for(claim)[0]
    expected_title = graph.source.get("title")

    for title in ("Snapshot B", "Snapshot C"):
        locked = store.lock_source_occurrence_envelope(str(graph.source["id"]))
        assert locked.get("title") == expected_title
        retired = VNextMemoryCommitService(store).retire_source_occurrence_state(
            str(graph.source["id"]),
            stage="http_source_review_envelope_change",
            reason="The source title occurrence input changed.",
            _defer_occurrence_accounting=True,
        )
        assert retired == [str(original_unit["id"])]
        updated = store.update_source(
            source_id=str(graph.source["id"]),
            patch={"title": title},
            actor_type="user",
        )
        establish_source_chunk_occurrences(
            store,
            source=updated,
            source_chunk=graph.chunk,
            actor_type="user",
            stage="http_source_review_envelope_change",
        )
        assert review_source_chunk_occurrences(
            store,
            source_chunk_id=str(graph.chunk["id"]),
            reviewer_id="reviewer-2",
            reason=f"The {title} source snapshot was reviewed.",
            actor_type="user",
            stage="http_source_review",
            _defer_occurrence_accounting=True,
        ) == [str(claim["id"])]
        reconcile_chunk_extraction_disposition(
            store,
            source_chunk_id=str(graph.chunk["id"]),
            actor_type="user",
            reviewer_id="reviewer-2",
            reason=(
                f"The {title} source snapshot was reviewed. "
                "Extraction disposition reviewed during http_source_review."
            ),
        )
        expected_title = title

    current_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
    current_snapshot = store.get_source_chunk_for_occurrence_accounting(str(graph.chunk["id"]))
    evidence = _raw_claim_evidence_details(store, str(claim["id"]))
    accepted = [row for row in evidence if row["review_status"] == "accepted"]
    accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        source_ids=[str(graph.source["id"])],
    )

    assert current_snapshot is not None
    assert current_unit["id"] == original_unit["id"]
    assert current_unit["occurrence_key"] == original_unit["occurrence_key"]
    assert current_unit["review_status"] == "accepted"
    assert current_unit["review_receipt_action"] == "reestablished"
    assert current_unit["retired_at"] is None
    assert len(accepted) == 1
    assert accepted[0]["review_receipt_action"] == "reestablished"
    assert accepted[0]["unit_review_receipt_digest"] == current_unit["review_receipt_digest"]
    assert accepted[0]["metadata_json"]["source_snapshot_sha256"] == current_snapshot["snapshot_sha256"]
    assert accounting["complete"] is True
    assert accounting["reviewed_current_count"] == 1

    review_version = int(current_unit["review_version"])
    evidence_keys = [str(row["evidence_key"]) for row in evidence]
    replay_source = store.lock_source_occurrence_envelope(str(graph.source["id"]))
    establish_source_chunk_occurrences(
        store,
        source=replay_source,
        source_chunk=graph.chunk,
        actor_type="user",
        stage="http_source_review_envelope_change",
    )
    assert review_source_chunk_occurrences(
        store,
        source_chunk_id=str(graph.chunk["id"]),
        reviewer_id="reviewer-2",
        reason="The same final source snapshot was replayed.",
        actor_type="user",
        stage="http_source_review",
    ) == [str(claim["id"])]
    replay_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
    replay_evidence = _raw_claim_evidence_details(store, str(claim["id"]))
    assert replay_unit["review_version"] == review_version
    assert [str(row["evidence_key"]) for row in replay_evidence] == evidence_keys


def test_explicitly_rejected_source_unit_cannot_be_reestablished() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited museums on March 3, 2026.",
        accepted=False,
        session_date="2026-03-05T12:00:00Z",
    )
    claim = graph.only_claim()
    unit = graph.units_for(claim)[0]
    rejected = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="rejected",
        reviewer_id="reviewer-2",
        reason="The reviewer explicitly rejected this occurrence.",
    )
    updated = store.update_source(
        source_id=str(graph.source["id"]),
        patch={"title": "A later source heading"},
        actor_type="user",
    )
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="candidate or accepted unit",
    ):
        establish_source_chunk_occurrences(
            store,
            source=updated,
            source_chunk=graph.chunk,
            actor_type="user",
            stage="http_source_review_envelope_change",
        )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="lifecycle-retired unit",
    ):
        store.reestablish_source_occurrence_unit(
            occurrence_id=str(unit["id"]),
            source_chunk_id=str(graph.chunk["id"]),
            stage="http_source_review",
            reason="A later snapshot must not override explicit rejection.",
            reviewer_id="reviewer-3",
            expected_review_version=int(rejected["review_version"]),
        )

    current = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
    assert current["review_status"] == "rejected"
    assert current["review_receipt_action"] == "rejected"


def test_archived_source_retirement_cannot_be_reestablished() -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited museums on March 3, 2026.",
        session_date="2026-03-05T12:00:00Z",
    )
    claim = graph.only_claim()
    unit = graph.units_for(claim)[0]
    VNextMemoryCommitService(store).retire_source_occurrence_state(
        str(graph.source["id"]),
        stage="http_source_review_archive",
        reason="The source was archived.",
    )
    updated = store.update_source(
        source_id=str(graph.source["id"]),
        patch={"title": "A heading cannot undo archive retirement"},
        actor_type="user",
    )
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="candidate or accepted unit",
    ):
        establish_source_chunk_occurrences(
            store,
            source=updated,
            source_chunk=graph.chunk,
            actor_type="user",
            stage="http_source_review_envelope_change",
        )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="signed lifecycle detachment",
    ):
        store.reestablish_source_occurrence_unit(
            occurrence_id=str(unit["id"]),
            source_chunk_id=str(graph.chunk["id"]),
            stage="http_source_review",
            reason="Archive retirement must remain terminal.",
            reviewer_id="reviewer-2",
            expected_review_version=int(store.list_occurrence_units_for_claim(str(claim["id"]))[0]["review_version"]),
        )

    current = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
    assert current["id"] == unit["id"]
    assert current["review_status"] == "retired"


def test_source_snapshot_mutation_between_guard_and_review_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    graph = _capture_natural_graph(
        store,
        "I visited museums on March 3, 2026.",
        session_date="2026-03-05T12:00:00Z",
    )
    claim = graph.only_claim()
    unit = graph.units_for(claim)[0]
    store.lock_source_occurrence_envelope(str(graph.source["id"]))
    VNextMemoryCommitService(store).retire_source_occurrence_state(
        str(graph.source["id"]),
        stage="http_source_review_envelope_change",
        reason="The source title occurrence input changed.",
        _defer_occurrence_accounting=True,
    )
    updated = store.update_source(
        source_id=str(graph.source["id"]),
        patch={"title": "Snapshot B"},
        actor_type="user",
    )
    establish_source_chunk_occurrences(
        store,
        source=updated,
        source_chunk=graph.chunk,
        actor_type="user",
        stage="http_source_review_envelope_change",
    )
    invalidate_occurrence_accounting(
        store,
        reason="The replacement source snapshot requires review.",
        actor_type="user",
        actor_id="reviewer-2",
        source_chunk_id=str(graph.chunk["id"]),
    )

    original_review = sqlite_occurrence_accounting.review_occurrence_unit

    def mutate_snapshot_then_review(*args: object, **kwargs: object) -> object:
        store.update_source(
            source_id=str(graph.source["id"]),
            patch={"title": "Snapshot C"},
            actor_type="user",
        )
        return original_review(*args, **kwargs)

    monkeypatch.setattr(
        sqlite_occurrence_accounting,
        "review_occurrence_unit",
        mutate_snapshot_then_review,
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="fresh current-snapshot evidence",
    ):
        review_source_chunk_occurrences(
            store,
            source_chunk_id=str(graph.chunk["id"]),
            reviewer_id="reviewer-2",
            reason="A stale snapshot must not be re-signed.",
            actor_type="user",
            stage="http_source_review",
        )

    current = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
    assert current["id"] == unit["id"]
    assert current["review_status"] == "retired"
    assert current["review_receipt_action"] == "retired"
