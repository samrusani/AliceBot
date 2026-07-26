from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import (
    SQLiteVNextStore,
    ensure_sqlite_user,
)
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_retrieval import (
    VNextRetrievalRequest,
    VNextRetrievalService,
)
from alicebot_api.vnext_stores.postgres import (
    occurrence_accounting as postgres_occurrence_accounting,
)
from alicebot_api.vnext_stores.postgres import occurrences as postgres_occurrences
from alicebot_api.vnext_stores.sqlite import (
    occurrence_accounting as sqlite_occurrence_accounting,
)
from alicebot_api.vnext_stores.sqlite import (
    memory_lifecycle as sqlite_memory_lifecycle,
)
from alicebot_api.vnext_stores.sqlite import occurrences as sqlite_occurrences


def _predicate() -> dict[str, object]:
    return {
        "schema": "occurrence_predicate_v1",
        "taxonomy": "alice-occurrence-exact-v1",
        "op": "atom",
        "subject": "self",
        "polarity": "completed",
        "action": {"leaf": "publish", "ancestors": []},
        "object": {
            "leaf": "release",
            "qualifiers": [],
            "ancestors": [],
        },
        "selector_keys": [
            "v1|a=exact:publish|o=exact:release",
            "v1|a=exact:publish|o=*",
        ],
        "closure_complete": True,
    }


def _claim_aggregation() -> dict[str, object]:
    return {
        "schema": "occurrence_aggregation_v1",
        "bases": [
            {
                "basis": "event_instance",
                "identity_basis": "occurrence_key",
            }
        ],
    }


def _unit_aggregation(occurrence_key: str) -> dict[str, object]:
    return {
        "schema": "occurrence_aggregation_v1",
        "members": [
            {
                "basis": "event_instance",
                "identity_basis": "occurrence_key",
                "member_identity": occurrence_key,
            }
        ],
    }


def _claim_object_aggregation() -> dict[str, object]:
    aggregation = _claim_aggregation()
    aggregation["bases"] = [
        *aggregation["bases"],
        {
            "basis": "object_member",
            "identity_basis": "reviewed_stable_object_v1",
        },
    ]
    return aggregation


def _unit_object_aggregation(
    occurrence_key: str,
    *,
    object_identity: str = "object:v1:" + ("a" * 64),
) -> dict[str, object]:
    aggregation = _unit_aggregation(occurrence_key)
    aggregation["members"] = [
        *aggregation["members"],
        {
            "basis": "object_member",
            "identity_basis": "reviewed_stable_object_v1",
            "member_identity": object_identity,
        },
    ]
    return aggregation


def _accounting_metadata() -> dict[str, object]:
    return {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": "phase6-test-v1",
        "source_ids": ["11111111-1111-4111-8111-111111111111"],
        "source_chunk_ids": ["22222222-2222-4222-8222-222222222222"],
        "snapshot_digest": "a" * 64,
        "disposition_digest": "b" * 64,
    }


def _store() -> SQLiteVNextStore:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(conn, user_id, f"{user_id}@example.com", "Occurrence Test")
    return SQLiteVNextStore(conn, user_id)


def _claim(
    *,
    claim_key: str,
    quantity: int = 1,
    domain: str = "project",
    sensitivity: str = "private",
    project_scope: list[str] | None = None,
    occurred_at: str = "2026-07-24T12:00:00Z",
    identity_basis: str = "exact_time",
    resolution_decision: str = "new",
) -> dict[str, object]:
    return {
        "claim_key": claim_key,
        "count_key": "published release",
        "predicate_json": _predicate(),
        "canonical_text": f"Published {quantity} releases",
        "quantity_min": quantity,
        "quantity_max": quantity,
        "range_kind": "exact",
        "resolution_decision": resolution_decision,
        "identity_basis": identity_basis,
        "aggregation_json": _claim_aggregation(),
        "occurred_at_start": occurred_at,
        "occurred_at_end": occurred_at,
        "domain": domain,
        "sensitivity": sensitivity,
        "project_scope": project_scope or ["alice"],
    }


def _unit(
    claim_id: str,
    ordinal: int,
    *,
    occurrence_key: str | None = None,
) -> dict[str, object]:
    resolved_occurrence_key = occurrence_key or f"occurrence-{ordinal}"
    return {
        "claim_id": claim_id,
        "claim_ordinal": ordinal,
        "occurrence_key": resolved_occurrence_key,
        "count_key": "published release",
        "predicate_json": _predicate(),
        "canonical_text": f"Published release {ordinal}",
        "identity_status": "resolved",
        "aggregation_json": _unit_aggregation(resolved_occurrence_key),
        "occurred_at_start": "2026-07-24T12:00:00Z",
        "occurred_at_end": "2026-07-24T12:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "project_scope": ["alice"],
    }


def _quote_evidence(
    claim_id: str,
    occurrence_id: str | None,
    *,
    evidence_key: str,
    store: SQLiteVNextStore | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "claim_id": claim_id,
        "occurrence_id": occurrence_id,
        "evidence_key": evidence_key,
        "evidence_role": "supports",
        "quote": "Release published.",
        "metadata_json": {"source": "test"},
    }
    if store is not None:
        claim_scope = store.conn.execute(
            """
            SELECT domain, sensitivity, project_scope
            FROM occurrence_claims
            WHERE id = ? AND user_id = ?
            """,
            (claim_id, store.user_id),
        ).fetchone()
        assert claim_scope is not None
        content_hash = f"occurrence-evidence-carrier:{claim_id}"
        source = store.get_source_by_content_hash(content_hash)
        if source is None:
            source = store.create_source(
                {
                    "source_type": "note",
                    "content_hash": content_hash,
                    "domain": str(claim_scope[0]),
                    "sensitivity": str(claim_scope[1]),
                    "metadata_json": {
                        "project_scope": json.loads(str(claim_scope[2])),
                    },
                }
            )
        payload["source_id"] = str(source["id"])
    return payload


@pytest.mark.parametrize(
    "create_evidence",
    (
        postgres_occurrences.create_occurrence_evidence,
        sqlite_occurrences.create_occurrence_evidence,
    ),
)
def test_evidence_writer_rejects_digest_that_disagrees_with_quote(
    create_evidence,
) -> None:
    with pytest.raises(ValueError, match="quote_sha256 does not match quote"):
        create_evidence(
            object(),
            {
                "claim_id": str(uuid4()),
                "evidence_key": "fabricated-quote-digest",
                "quote": "The actual quoted evidence.",
                "quote_sha256": hashlib.sha256(b"A different quoted value.").hexdigest(),
            },
        )


@pytest.mark.parametrize(
    "create_evidence",
    (
        postgres_occurrences.create_occurrence_evidence,
        sqlite_occurrences.create_occurrence_evidence,
    ),
)
def test_evidence_writer_rejects_quote_only_rows_without_authorization_carrier(
    create_evidence,
) -> None:
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="requires a memory_id or source_id authorization carrier",
    ):
        create_evidence(
            object(),
            {
                "claim_id": str(uuid4()),
                "evidence_key": "quote-only",
                "quote": "A quote cannot authorize itself.",
            },
        )


@pytest.mark.parametrize(
    "create_evidence",
    (
        postgres_occurrences.create_occurrence_evidence,
        sqlite_occurrences.create_occurrence_evidence,
    ),
)
def test_evidence_writer_normalizes_blank_carrier_ids_before_rejecting(
    create_evidence,
) -> None:
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="requires a memory_id or source_id authorization carrier",
    ):
        create_evidence(
            object(),
            {
                "claim_id": str(uuid4()),
                "source_id": "   ",
                "memory_id": "",
                "evidence_key": "blank-carriers",
                "quote": "Blank identifiers cannot authorize evidence.",
            },
        )


@pytest.mark.parametrize(
    "create_evidence",
    (
        postgres_occurrences.create_occurrence_evidence,
        sqlite_occurrences.create_occurrence_evidence,
    ),
)
def test_evidence_writer_requires_source_parent_for_chunk_carrier(
    create_evidence,
) -> None:
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="source_chunk_id requires source_id",
    ):
        create_evidence(
            object(),
            {
                "claim_id": str(uuid4()),
                "source_chunk_id": str(uuid4()),
                "evidence_key": "orphan-chunk",
                "quote": "A chunk cannot authorize without its source.",
            },
        )


@pytest.mark.parametrize(
    "create_evidence",
    (
        postgres_occurrences.create_occurrence_evidence,
        sqlite_occurrences.create_occurrence_evidence,
    ),
)
@pytest.mark.parametrize("quote", (None, "", "   ", "\u00a0", "\u001c"))
def test_evidence_writer_requires_nonempty_quote(
    create_evidence,
    quote: object,
) -> None:
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="requires a nonempty quote",
    ):
        create_evidence(
            object(),
            {
                "claim_id": str(uuid4()),
                "memory_id": str(uuid4()),
                "evidence_key": "missing-quote",
                "quote": quote,
            },
        )


def test_sqlite_evidence_schema_and_writer_preserve_only_authorized_carrier_shapes() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="carrier-shapes"))
    memory = store.create_memory(
        {
            "memory_key": "occurrence.carrier-shapes",
            "status": "active",
            "canonical_text": "Release published.",
            "value": {"text": "Release published."},
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    source = store.create_source(
        {
            "source_type": "note",
            "content_hash": "occurrence-carrier-shapes",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Release published.",
        }
    )

    created = [
        store.create_occurrence_evidence(
            {
                "claim_id": claim["id"],
                "evidence_key": "memory-only",
                "quote": "Release published.",
                "memory_id": memory["id"],
            }
        ),
        store.create_occurrence_evidence(
            {
                "claim_id": claim["id"],
                "evidence_key": "source-only",
                "quote": "Release published.",
                "source_id": source["id"],
            }
        ),
        store.create_occurrence_evidence(
            {
                "claim_id": claim["id"],
                "evidence_key": "source-plus-chunk",
                "quote": "Release published.",
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
            }
        ),
    ]
    assert [(row["memory_id"], row["source_id"], row["source_chunk_id"]) for row in created] == [
        (memory["id"], None, None),
        (None, source["id"], None),
        (None, source["id"], chunk["id"]),
    ]

    quote_sha256 = hashlib.sha256(b"Release published.").hexdigest()
    with pytest.raises(sqlite3.IntegrityError, match="authorization_carrier"):
        store.conn.execute(
            """
            INSERT INTO occurrence_evidence (
              id, user_id, claim_id, evidence_key, evidence_role,
              quote, quote_sha256, review_status, metadata_json
            ) VALUES (?, ?, ?, ?, 'supports', ?, ?, 'candidate', '{}')
            """,
            (
                str(uuid4()),
                store.user_id,
                claim["id"],
                "sql-quote-only",
                "Release published.",
                quote_sha256,
            ),
        )
    with pytest.raises(sqlite3.IntegrityError, match="source_chunk_parent"):
        store.conn.execute(
            """
            INSERT INTO occurrence_evidence (
              id, user_id, claim_id, source_chunk_id, memory_id,
              evidence_key, evidence_role, quote, quote_sha256,
              review_status, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, 'supports', ?, ?, 'candidate', '{}')
            """,
            (
                str(uuid4()),
                store.user_id,
                claim["id"],
                str(uuid4()),
                memory["id"],
                "sql-orphan-chunk",
                "Release published.",
                quote_sha256,
            ),
        )


def test_sqlite_unit_count_key_must_match_owner_on_create_schema_and_replay() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="count-key-owner"))
    mismatch = _unit(
        str(claim["id"]),
        1,
        occurrence_key="count-key-owned-unit",
    )
    mismatch["count_key"] = "attended conference"

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="count_key must match its owning claim",
    ):
        store.get_or_create_occurrence_unit(mismatch)

    valid = _unit(
        str(claim["id"]),
        1,
        occurrence_key="count-key-owned-unit",
    )
    unit, created = store.get_or_create_occurrence_unit(valid)
    assert created is True
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        store.conn.execute(
            """
            UPDATE occurrence_units
            SET count_key = ?
            WHERE id = ? AND user_id = ?
            """,
            ("attended conference", unit["id"], store.user_id),
        )
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="count_key must match its owning claim",
    ):
        store.get_or_create_occurrence_unit(mismatch)
    persisted = store.get_occurrence_unit_by_key("count-key-owned-unit")
    assert persisted is not None
    assert persisted["count_key"] == claim["count_key"] == "published release"


def test_sqlite_link_existing_rejects_cross_count_family_target() -> None:
    store = _store()
    _owner_claim, target = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="count-key-link-target",
        evidence_rows=[{"evidence_key": "count-key-link-target-evidence"}],
    )
    link_payload = _claim(
        claim_key="count-key-link-mismatch",
        resolution_decision="link_existing",
    )
    link_payload["count_key"] = "attended conference"
    linked_claim, _ = store.get_or_create_occurrence_claim(link_payload)

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="resolved-unit guard",
    ):
        store.review_occurrence_claim(
            claim_id=str(linked_claim["id"]),
            resolution_status="resolved",
            resolution_decision="link_existing",
            identity_basis="exact_time",
            reviewer_id="reviewer",
            reason="A claim cannot link across count families.",
            resolved_occurrence_id=str(target["id"]),
        )
    preserved = store.get_occurrence_claim(str(linked_claim["id"]))
    assert preserved is not None
    assert preserved["review_status"] == "candidate"
    assert preserved["resolution_status"] == "pending"
    assert preserved["resolved_occurrence_id"] is None


def test_sqlite_evidence_writer_rejects_cross_count_family_target() -> None:
    store = _store()
    _owner_claim, target = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="count-key-evidence-target",
        evidence_rows=[{"evidence_key": "count-key-evidence-target-owner"}],
    )
    cross_count_payload = _claim(claim_key="count-key-evidence-mismatch")
    cross_count_payload["count_key"] = "attended conference"
    cross_count_claim, _ = store.get_or_create_occurrence_claim(
        cross_count_payload
    )
    evidence_key = "count-key-evidence-mismatch-candidate"

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="mismatched reference",
    ):
        store.create_occurrence_evidence(
            _quote_evidence(
                str(cross_count_claim["id"]),
                str(target["id"]),
                evidence_key=evidence_key,
                store=store,
            )
        )

    persisted = store.conn.execute(
        """
        SELECT COUNT(*)
        FROM occurrence_evidence
        WHERE user_id = ? AND evidence_key = ?
        """,
        (store.user_id, evidence_key),
    ).fetchone()
    assert persisted == (0,)


def test_sqlite_plural_claim_acceptance_and_evidence_receipts_are_replay_safe() -> None:
    store = _store()
    store.ensure_occurrence_coverage()
    claim, created = store.get_or_create_occurrence_claim(_claim(claim_key="plural-claim", quantity=2))
    assert created is True

    units = [store.get_or_create_occurrence_unit(_unit(str(claim["id"]), ordinal))[0] for ordinal in (1, 2)]
    evidence = [
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key=f"plural-evidence-{ordinal}",
                store=store,
            )
        )
        for ordinal, unit in enumerate(units, start=1)
    ]
    replay = store.create_occurrence_evidence(
        _quote_evidence(
            str(claim["id"]),
            str(units[0]["id"]),
            evidence_key="plural-evidence-1",
            store=store,
        )
    )
    assert replay["id"] == evidence[0]["id"]
    assert (
        store.conn.execute(
            "SELECT COUNT(*) FROM occurrence_evidence WHERE user_id = ?",
            (store.user_id,),
        ).fetchone()[0]
        == 2
    )

    resolved = store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified plural event identities.",
        resolved_occurrence_id=None,
    )
    assert resolved["resolved_occurrence_id"] is None

    accepted = [
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reason="Evidence and identity verified.",
            reviewer_id="reviewer",
        )
        for unit in units
    ]
    assert [row["review_receipt_action"] for row in accepted] == [
        "accepted",
        "accepted",
    ]
    assert store.get_occurrence_unit_by_key("occurrence-2")["id"] == units[1]["id"]

    found = store.search_accepted_occurrence_units(
        query="published release",
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
    )
    assert {row["id"] for row in found} == {row["id"] for row in units}
    signed = store.list_occurrence_evidence_for_units([str(row["id"]) for row in found])
    assert len(signed) == 2
    assert {row["review_receipt_action"] for row in signed} == {"accepted"}
    assert {row["occurrence_review_receipt_action"] for row in signed} == {"accepted"}
    assert {tuple(row["occurrence_project_scope"]) for row in signed} == {("alice",)}
    assert all(
        row["unit_review_receipt_digest"]
        == next(unit["review_receipt_digest"] for unit in accepted if unit["id"] == row["occurrence_id"])
        for row in signed
    )


def test_sqlite_all_accepted_occurrence_units_are_exhaustively_paged() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="all-accepted-page", quantity=3))
    unit_ids = [f"00000000-0000-4000-8000-{ordinal:012d}" for ordinal in (1, 2, 3)]
    units: list[dict[str, object]] = []
    for ordinal, unit_id in enumerate(unit_ids, start=1):
        payload = _unit(
            str(claim["id"]),
            ordinal,
            occurrence_key=f"all-accepted-{ordinal}",
        )
        payload["id"] = unit_id
        unit, _ = store.get_or_create_occurrence_unit(payload)
        units.append(unit)
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key=f"all-accepted-evidence-{ordinal}",
                store=store,
            )
        )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="All three occurrence identities are distinct.",
    )
    for unit in units:
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reviewer_id="reviewer",
            reason="Evidence and identity verified.",
        )

    first = store.list_accepted_occurrence_units(
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        occurred_at_start=datetime(2026, 7, 24, 11, tzinfo=UTC),
        occurred_at_end=datetime(2026, 7, 25, tzinfo=UTC),
        as_of=datetime(2036, 7, 24, tzinfo=UTC),
        limit=2,
    )
    second = store.list_accepted_occurrence_units(
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        occurred_at_start=datetime(2026, 7, 24, 11, tzinfo=UTC),
        occurred_at_end=datetime(2026, 7, 25, tzinfo=UTC),
        as_of=datetime(2036, 7, 24, tzinfo=UTC),
        after_id=str(first[-1]["id"]),
        limit=2,
    )
    assert [row["id"] for row in first + second] == unit_ids
    assert (
        store.list_accepted_occurrence_units(
            projects=["other"],
            domains=["project"],
            sensitivity_allowed=["private"],
        )
        == []
    )
    with pytest.raises(ValueError, match="limit must be between 1 and 200"):
        store.list_accepted_occurrence_units(
            sensitivity_allowed=["private"],
            limit=201,
        )


@pytest.mark.parametrize("action", ("rejected", "ambiguous"))
def test_sqlite_terminal_candidate_review_receipt_is_reconstructible(
    action: str,
) -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key=f"terminal-{action}"))
    unit, _ = store.get_or_create_occurrence_unit(
        _unit(
            str(claim["id"]),
            1,
            occurrence_key=f"terminal-{action}",
        )
    )
    evidence = store.create_occurrence_evidence(
        _quote_evidence(
            str(claim["id"]),
            str(unit["id"]),
            evidence_key=f"terminal-{action}-evidence",
            store=store,
        )
    )
    reviewer_id = "terminal-reviewer"
    reason = f"Unit was terminally marked {action}."
    reviewed = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action=action,
        reviewer_id=reviewer_id,
        reason=reason,
    )

    evidence_digest = hashlib.sha256(
        sqlite_occurrences.occurrence_evidence_facts_digest(evidence).encode("utf-8")
    ).hexdigest()
    expected_receipt = sqlite_occurrences.occurrence_unit_review_receipt_digest(
        unit,
        action=action,
        reviewer_id=reviewer_id,
        reason=reason,
        review_version=1,
        evidence_digest=evidence_digest,
    )
    assert reviewed["review_receipt_action"] == action
    assert reviewed["reviewer_id"] == reviewer_id
    assert reviewed["review_reason"] == reason
    assert reviewed["reviewed_evidence_count"] == 1
    assert reviewed["reviewed_evidence_digest"] == evidence_digest
    assert reviewed["review_receipt_digest"] == expected_receipt
    assert reviewed["review_version"] == 1


def test_sqlite_retirement_issues_a_reconstructible_terminal_receipt() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="terminal-retired"))
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(claim["id"]), 1, occurrence_key="terminal-retired"))
    evidence = store.create_occurrence_evidence(
        _quote_evidence(
            str(claim["id"]),
            str(unit["id"]),
            evidence_key="terminal-retired-evidence",
            store=store,
        )
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="accept-reviewer",
        reason="Identity verified.",
    )
    accepted = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reviewer_id="accept-reviewer",
        reason="Evidence verified.",
    )
    reviewer_id = "retirement-reviewer"
    reason = "The occurrence was retired with a terminal receipt."
    retired = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="retired",
        reviewer_id=reviewer_id,
        reason=reason,
        expected_status="accepted",
        expected_review_version=int(accepted["review_version"]),
    )

    evidence_digest = hashlib.sha256(
        sqlite_occurrences.occurrence_evidence_facts_digest(evidence).encode("utf-8")
    ).hexdigest()
    expected_receipt = sqlite_occurrences.occurrence_unit_review_receipt_digest(
        accepted,
        action="retired",
        reviewer_id=reviewer_id,
        reason=reason,
        review_version=2,
        evidence_digest=evidence_digest,
    )
    assert retired["review_status"] == "retired"
    assert retired["review_receipt_action"] == "retired"
    assert retired["reviewer_id"] == reviewer_id
    assert retired["review_reason"] == reason
    assert retired["reviewed_evidence_count"] == 1
    assert retired["reviewed_evidence_digest"] == evidence_digest
    assert retired["review_receipt_digest"] == expected_receipt
    assert retired["review_version"] == 2


def test_sqlite_link_existing_requires_compatible_target_and_refreshes_receipt() -> None:
    store = _store()
    original_claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="original"))
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(original_claim["id"]), 1))
    store.create_occurrence_evidence(
        _quote_evidence(
            str(original_claim["id"]),
            str(unit["id"]),
            evidence_key="original-evidence",
            store=store,
        )
    )
    store.review_occurrence_claim(
        claim_id=str(original_claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified.",
    )
    accepted = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reason="Verified.",
        reviewer_id="reviewer",
    )

    linked_claim, _ = store.get_or_create_occurrence_claim(
        _claim(claim_key="linked", resolution_decision="link_existing")
    )
    linked_evidence = store.create_occurrence_evidence(
        _quote_evidence(
            str(linked_claim["id"]),
            str(unit["id"]),
            evidence_key="linked-evidence",
            store=store,
        )
    )
    store.review_occurrence_claim(
        claim_id=str(linked_claim["id"]),
        resolution_status="resolved",
        resolution_decision="link_existing",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Same event identity.",
        resolved_occurrence_id=str(unit["id"]),
    )
    before = store.list_occurrence_evidence_for_units([str(unit["id"])])
    assert {row["id"] for row in before} != {linked_evidence["id"]}

    refreshed = store.refresh_occurrence_unit_evidence(
        occurrence_id=str(unit["id"]),
        reason="Signed the linked evidence.",
        reviewer_id="reviewer",
        expected_review_version=int(accepted["review_version"]),
    )
    after = store.list_occurrence_evidence_for_units([str(unit["id"])])
    assert refreshed["review_receipt_action"] == "refresh_evidence"
    assert refreshed["review_version"] == 2
    assert {row["evidence_key"] for row in after} == {
        "original-evidence",
        "linked-evidence",
    }
    assert {row["review_receipt_action"] for row in after} == {"refresh_evidence"}


def test_sqlite_review_rejects_tampered_quote_digest_before_signing() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="tampered-quote"))
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(claim["id"]), 1, occurrence_key="tampered-quote"))
    evidence = store.create_occurrence_evidence(
        _quote_evidence(
            str(claim["id"]),
            str(unit["id"]),
            evidence_key="tampered-quote-evidence",
            store=store,
        )
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Owner claim identity verified.",
    )
    store.conn.execute(
        "UPDATE occurrence_evidence SET quote_sha256 = ? WHERE id = ?",
        ("0" * 64, evidence["id"]),
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="requires eligible supporting evidence",
    ):
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reviewer_id="reviewer",
            reason="Tampered evidence must not be signed.",
        )
    current = store.get_occurrence_unit_by_key("tampered-quote")
    assert current is not None
    assert current["review_status"] == "candidate"
    assert current["review_version"] == 0
    persisted = store.conn.execute(
        "SELECT review_status, review_receipt_digest FROM occurrence_evidence WHERE id = ?",
        (evidence["id"],),
    ).fetchone()
    assert persisted == ("candidate", None)


def test_sqlite_review_rejects_unreviewed_cross_claim_evidence_before_signing() -> None:
    store = _store()
    owner_claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="owner-claim"))
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(owner_claim["id"]), 1, occurrence_key="owner-unit"))
    store.review_occurrence_claim(
        claim_id=str(owner_claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Owner claim identity verified.",
    )
    linked_claim, _ = store.get_or_create_occurrence_claim(
        _claim(
            claim_key="pending-link",
            resolution_decision="link_existing",
        )
    )
    linked_evidence = store.create_occurrence_evidence(
        _quote_evidence(
            str(linked_claim["id"]),
            str(unit["id"]),
            evidence_key="pending-link-evidence",
            store=store,
        )
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="requires eligible supporting evidence",
    ):
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reviewer_id="reviewer",
            reason="An unreviewed cross-claim must not authorize signing.",
        )
    current = store.get_occurrence_unit_by_key("owner-unit")
    assert current is not None
    assert current["review_status"] == "candidate"
    assert current["review_version"] == 0
    signed = store.conn.execute(
        "SELECT review_status, unit_review_receipt_digest FROM occurrence_evidence WHERE id = ?",
        (linked_evidence["id"],),
    ).fetchone()
    assert signed == ("candidate", None)


@pytest.mark.parametrize("quote", ("\u00a0", "\u001c"))
def test_sqlite_schema_and_review_reject_python_strip_only_quote(
    quote: str,
) -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key=f"unicode-blank-{ord(quote)}"))
    unit, _ = store.get_or_create_occurrence_unit(
        _unit(
            str(claim["id"]),
            1,
            occurrence_key=f"unicode-blank-unit-{ord(quote)}",
        )
    )
    source = store.create_source(
        {
            "source_type": "note",
            "content_hash": f"unicode-blank-source-{ord(quote)}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    quote_sha256 = hashlib.sha256(quote.encode("utf-8")).hexdigest()
    insert_sql = """
        INSERT INTO occurrence_evidence (
          id, user_id, claim_id, occurrence_id, source_id,
          evidence_key, evidence_role, quote, quote_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, 'supports', ?, ?)
    """
    with pytest.raises(sqlite3.IntegrityError, match="occurrence_evidence_quote_check"):
        store.conn.execute(
            insert_sql,
            (
                str(uuid4()),
                store.user_id,
                claim["id"],
                unit["id"],
                source["id"],
                f"unicode-blank-schema-{ord(quote)}",
                quote,
                quote_sha256,
            ),
        )

    store.conn.commit()
    store.conn.execute("PRAGMA ignore_check_constraints = ON")
    try:
        evidence_id = str(uuid4())
        store.conn.execute(
            insert_sql,
            (
                evidence_id,
                store.user_id,
                claim["id"],
                unit["id"],
                source["id"],
                f"unicode-blank-review-{ord(quote)}",
                quote,
                quote_sha256,
            ),
        )
        store.conn.commit()
    finally:
        store.conn.execute("PRAGMA ignore_check_constraints = OFF")
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Owner claim identity verified.",
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="requires eligible supporting evidence",
    ):
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reviewer_id="reviewer",
            reason="Python-strip-only whitespace must not authorize signing.",
        )
    persisted = store.conn.execute(
        """
        SELECT review_status, unit_review_receipt_digest
        FROM occurrence_evidence
        WHERE id = ?
        """,
        (evidence_id,),
    ).fetchone()
    assert persisted == ("candidate", None)


def test_sqlite_unresolved_claim_filters_apply_before_keyset_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    identifiers = (
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000003",
        "00000000-0000-0000-0000-000000000004",
        "00000000-0000-0000-0000-000000000005",
    )
    for index, claim_id in enumerate(identifiers, start=1):
        payload = _claim(
            claim_key=f"ambiguous-{index}",
            identity_basis="ambiguous",
            resolution_decision="ambiguous",
            domain="personal" if index == 2 else "project",
            sensitivity="public" if index == 3 else "private",
        )
        payload["id"] = claim_id
        claim, _ = store.get_or_create_occurrence_claim(payload)
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                None,
                evidence_key=f"ambiguous-evidence-{index}",
                store=store,
            )
        )
    store.conn.execute(
        """
        UPDATE occurrence_claims
        SET project_scope = '["other"]'
        WHERE id = ?
        """,
        (identifiers[0],),
    )
    captured_queries: list[str] = []
    fetch_all = store._fetch_all

    def recording_fetch_all(
        query: str,
        params: tuple[object, ...] = (),
    ) -> list[dict[str, object]]:
        if "FROM occurrence_claims AS claim" in query:
            captured_queries.append(query)
        return fetch_all(query, params)

    monkeypatch.setattr(store, "_fetch_all", recording_fetch_all)

    first = store.list_unresolved_occurrence_claims(
        count_key="published release",
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        occurred_at_start=datetime(2026, 7, 24, 0, tzinfo=UTC),
        occurred_at_end=datetime(2026, 7, 25, 0, tzinfo=UTC),
        limit=1,
    )
    assert [row["id"] for row in first] == [identifiers[3]]
    second = store.list_unresolved_occurrence_claims(
        count_key="published release",
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        occurred_at_start=datetime(2026, 7, 24, 0, tzinfo=UTC),
        occurred_at_end=datetime(2026, 7, 25, 0, tzinfo=UTC),
        after_id=str(first[-1]["id"]),
        limit=1,
    )
    assert [row["id"] for row in second] == [identifiers[4]]
    assert len(captured_queries) == 2
    for query in captured_queries:
        limit_offset = query.index("LIMIT ?")
        assert query.index("AND claim.domain IN") < limit_offset
        assert query.index("AND claim.sensitivity IN") < limit_offset
        assert query.index("ORDER BY claim.id ASC") < limit_offset
        assert "ORDER BY unit.id" not in query
    rejected = store.review_occurrence_claim(
        claim_id=identifiers[4],
        resolution_status="rejected",
        resolution_decision="ambiguous",
        identity_basis="ambiguous",
        reviewer_id="reviewer",
        reason="A stronger reviewed identity replaced this ambiguity.",
    )
    assert rejected["review_status"] == "rejected"


def test_sqlite_ambiguous_collision_preserves_strong_identity_basis() -> None:
    store = _store()
    payload = _claim(
        claim_key="date-ordinal-collision",
        identity_basis="date_and_ordinal",
        resolution_decision="ambiguous",
    )
    claim, created = store.get_or_create_occurrence_claim(payload)
    assert created is True
    assert claim["identity_basis"] == "date_and_ordinal"
    assert claim["resolution_decision"] == "ambiguous"
    assert claim["resolution_status"] == "pending"
    assert claim["review_status"] == "candidate"


def test_sqlite_evidence_scope_and_memory_expiry_fail_closed() -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "document",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "personal",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="scoped"))
    with pytest.raises(ContinuityStoreInvariantError):
        store.create_occurrence_evidence(
            {
                **_quote_evidence(
                    str(claim["id"]),
                    None,
                    evidence_key="wrong-domain-source",
                ),
                "source_id": source["id"],
            }
        )

    memory = store.create_memory(
        {
            "memory_key": "occurrence-memory",
            "value": {"text": "Published a release."},
            "status": "active",
            "canonical_text": "Published a release.",
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(claim["id"]), 1))
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key="memory-evidence",
            ),
            "memory_id": memory["id"],
        }
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified.",
    )
    store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reason="Verified.",
        reviewer_id="reviewer",
    )
    query = {
        "query": "published release",
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
    }
    assert len(store.search_accepted_occurrence_units(**query)) == 1
    store.conn.execute(
        "UPDATE memories SET valid_to = ? WHERE id = ?",
        (
            (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            memory["id"],
        ),
    )
    expired_candidates = store.search_accepted_occurrence_units(**query)
    assert [row["id"] for row in expired_candidates] == [unit["id"]]
    assert (
        store.list_occurrence_evidence_for_units(
            [str(unit["id"])],
            as_of=datetime.now(UTC),
        )
        == []
    )
    store.conn.execute(
        "UPDATE memories SET valid_to = NULL WHERE id = ?",
        (memory["id"],),
    )
    assert len(store.search_accepted_occurrence_units(**query)) == 1
    assert (
        len(
            store.list_occurrence_evidence_for_units(
                [str(unit["id"])],
                as_of=datetime.now(UTC),
            )
        )
        == 1
    )


def test_sqlite_occurrence_reads_bind_one_stable_as_of_clock() -> None:
    store = _store()
    expiry = datetime(2036, 7, 24, 12, tzinfo=UTC)
    memory = store.create_memory(
        {
            "memory_key": "stable-clock-occurrence",
            "value": {"text": "Published a release."},
            "status": "active",
            "canonical_text": "Published a release.",
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "valid_to": expiry.isoformat(),
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="stable-clock"))
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(claim["id"]), 1))
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key="stable-clock-evidence",
            ),
            "memory_id": memory["id"],
        }
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified.",
    )
    store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reason="Verified.",
        reviewer_id="reviewer",
    )
    query = {
        "query": "published release",
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
    }
    at_boundary = store.search_accepted_occurrence_units(
        **query,
        as_of=expiry,
    )
    assert [row["id"] for row in at_boundary] == [unit["id"]]
    assert (
        len(
            store.list_occurrence_evidence_for_units(
                [str(unit["id"])],
                as_of=expiry,
            )
        )
        == 1
    )

    after_expiry = expiry + timedelta(seconds=1)
    assert [
        row["id"]
        for row in store.search_accepted_occurrence_units(
            **query,
            as_of=after_expiry,
        )
    ] == [unit["id"]]
    assert (
        store.list_occurrence_evidence_for_units(
            [str(unit["id"])],
            as_of=after_expiry,
        )
        == []
    )

    unresolved_payload = _claim(
        claim_key="stable-clock-unresolved",
        identity_basis="ambiguous",
        resolution_decision="ambiguous",
    )
    unresolved, _ = store.get_or_create_occurrence_claim(unresolved_payload)
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(unresolved["id"]),
                None,
                evidence_key="stable-clock-unresolved-evidence",
            ),
            "memory_id": memory["id"],
        }
    )
    unresolved_query = {
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
    }
    assert [
        row["id"]
        for row in store.list_unresolved_occurrence_claims(
            **unresolved_query,
            as_of=expiry,
        )
    ] == [unresolved["id"]]
    assert [
        row["id"]
        for row in store.list_unresolved_occurrence_claims(
            **unresolved_query,
            as_of=after_expiry,
        )
    ] == [unresolved["id"]]


def test_sqlite_expired_carrier_cannot_hide_accepted_unit_and_undercount() -> None:
    store = _store()
    memories = [
        store.create_memory(
            {
                "memory_key": f"passive-expiry-{index}",
                "value": {"text": "Published a release."},
                "status": "active",
                "canonical_text": "Published a release.",
                "domain": "project",
                "sensitivity": "private",
                "project_id": "alice",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        for index in (1, 2)
    ]
    units = [
        _accepted_unit_with_carrier_evidence(
            store,
            claim_key=f"passive-expiry-{index}",
            evidence_rows=[
                {
                    "evidence_key": f"passive-expiry-evidence-{index}",
                    "memory_id": memory["id"],
                }
            ],
        )[1]
        for index, memory in enumerate(memories, start=1)
    ]
    accounting_metadata = _prepare_complete_accounting(store)
    coverage = store.ensure_occurrence_coverage(started_at="2020-01-01T00:00:00Z")
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="current complete corpus",
    ):
        store.review_occurrence_coverage(
            coverage_mode="complete_history",
            historical_review_status="reviewed",
            complete_through="2040-12-31T23:59:59Z",
            reviewer_id="reviewer",
            reason="Memory-only carriers must block complete history.",
            accounting_metadata=accounting_metadata,
            expected_review_version=int(coverage["review_version"]),
        )
    store.conn.execute(
        "UPDATE memories SET valid_to = ? WHERE id = ?",
        ("2030-01-01T00:00:00Z", memories[1]["id"]),
    )
    as_of = datetime(2031, 1, 1, tzinfo=UTC)
    query = {
        "query": "published release",
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
        "as_of": as_of,
    }
    found = store.search_accepted_occurrence_units(**query)
    assert {row["id"] for row in found} == {row["id"] for row in units}
    live_evidence = store.list_occurrence_evidence_for_units(
        [str(row["id"]) for row in found],
        as_of=as_of,
    )
    assert {row["occurrence_id"] for row in live_evidence} == {units[0]["id"]}

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I publish a release?",
            projects=("alice",),
            domains=("project",),
            reference_time=as_of,
        )
    )
    assert pack["aggregation"]["answer_kind"] == "at_least"
    assert pack["aggregation"]["exact"] is False
    assert pack["aggregation"]["lower_bound"] == 2
    assert pack["aggregation"]["upper_bound"] is None
    assert pack["aggregation"]["unresolved_claims"]["count"] == 0
    assert pack["aggregation"]["coverage"]["fully_covered"] is False


def test_sqlite_stale_evidence_does_not_hide_pending_claim_from_exactness() -> None:
    store = _store()
    live_memory = store.create_memory(
        {
            "memory_key": "pending-claim-live-unit",
            "value": {"text": "Published a release."},
            "status": "active",
            "canonical_text": "Published a release.",
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    _accepted_unit_with_carrier_evidence(
        store,
        claim_key="pending-claim-live-unit",
        evidence_rows=[
            {
                "evidence_key": "pending-claim-live-unit-evidence",
                "memory_id": live_memory["id"],
            }
        ],
    )
    stale_memory = store.create_memory(
        {
            "memory_key": "pending-claim-stale-evidence",
            "value": {"text": "Published another release."},
            "status": "active",
            "canonical_text": "Published another release.",
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    pending_payload = _claim(
        claim_key="pending-stale-evidence",
        identity_basis="ambiguous",
        resolution_decision="ambiguous",
    )
    pending, _ = store.get_or_create_occurrence_claim(pending_payload)
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(pending["id"]),
                None,
                evidence_key="pending-stale-evidence",
            ),
            "memory_id": stale_memory["id"],
        }
    )
    store.conn.execute(
        "UPDATE memories SET valid_to = ? WHERE id = ?",
        ("2030-01-01T00:00:00Z", stale_memory["id"]),
    )
    as_of = datetime(2031, 1, 1, tzinfo=UTC)
    unresolved = store.list_unresolved_occurrence_claims(
        count_key="published release",
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        as_of=as_of,
    )
    assert [row["id"] for row in unresolved] == [pending["id"]]
    store.ensure_occurrence_coverage(started_at="2020-01-01T00:00:00Z")

    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I publish a release?",
            projects=("alice",),
            domains=("project",),
            reference_time=as_of,
        )
    )
    assert pack["aggregation"]["answer_kind"] == "at_least"
    assert pack["aggregation"]["exact"] is False
    assert pack["aggregation"]["lower_bound"] == 1
    assert pack["aggregation"]["upper_bound"] is None
    assert pack["aggregation"]["unresolved_claims"]["count"] == 1
    assert pack["aggregation"]["unresolved_claims"]["matching_or_unknown"] == 1
    assert pack["aggregation"]["coverage"]["fully_covered"] is False


def test_sqlite_reference_time_filters_event_time_not_current_carrier_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    imported_at = "2023-03-14T12:00:00Z"
    reviewed_at = "2026-01-15T12:00:00Z"
    monkeypatch.setattr(
        sqlite_memory_lifecycle,
        "_utc_now_iso",
        lambda: imported_at,
    )
    monkeypatch.setattr(
        sqlite_occurrences,
        "_utc_now_iso",
        lambda: imported_at,
    )
    memory = store.create_memory(
        {
            "memory_key": "historical-import-current-review",
            "value": {"text": "Published a release."},
            "status": "active",
            "canonical_text": "Published a release.",
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "valid_from": imported_at,
            "first_seen_at": imported_at,
            "last_seen_at": imported_at,
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    claim, _ = store.get_or_create_occurrence_claim(
        _claim(
            claim_key="historical-import-current-review",
            occurred_at=imported_at,
        )
    )
    unit_payload = _unit(
        str(claim["id"]),
        1,
        occurrence_key="historical-import-current-review-occurrence",
    )
    unit_payload["occurred_at_start"] = imported_at
    unit_payload["occurred_at_end"] = imported_at
    unit, _ = store.get_or_create_occurrence_unit(unit_payload)
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key="historical-import-current-review-evidence",
            ),
            "memory_id": memory["id"],
        }
    )

    monkeypatch.setattr(
        sqlite_occurrences,
        "_utc_now_iso",
        lambda: reviewed_at,
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Reviewed in the current lifecycle snapshot.",
    )
    accepted = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reason="Reviewed in the current lifecycle snapshot.",
        reviewer_id="reviewer",
    )
    assert accepted["reviewed_at"] == reviewed_at
    store.ensure_occurrence_coverage(started_at=imported_at)

    after_event_before_review = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I publish a release?",
            projects=("alice",),
            domains=("project",),
            reference_time=datetime(2024, 1, 1, tzinfo=UTC),
        )
    )
    assert after_event_before_review["aggregation"]["answer_kind"] == "at_least"
    assert after_event_before_review["aggregation"]["lower_bound"] == 1
    assert after_event_before_review["aggregation"]["occurrence_unit_ids"] == [unit["id"]]

    before_event = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I publish a release?",
            projects=("alice",),
            domains=("project",),
            reference_time=datetime(2023, 1, 1, tzinfo=UTC),
        )
    )
    assert "aggregation" not in before_event


def test_sqlite_coverage_review_is_signed_monotonic_and_cas_guarded() -> None:
    store = _store()
    accounting_metadata = _prepare_complete_accounting(store)
    coverage = store.ensure_occurrence_coverage(started_at="2026-01-01T00:00:00Z")
    assert coverage["review_version"] == 0
    qualified = store.review_occurrence_coverage(
        coverage_mode="complete_history",
        historical_review_status="reviewed",
        coverage_started_at="2026-01-01T00:00:00Z",
        complete_through="2026-12-31T23:59:59Z",
        reviewer_id="longmemeval-import",
        reason="Fresh isolated corpus fully imported and qualified.",
        accounting_metadata=accounting_metadata,
        expected_review_version=0,
    )
    assert qualified["coverage_mode"] == "complete_history"
    assert qualified["review_version"] == 1
    assert len(str(qualified["review_receipt_digest"])) == 64
    with pytest.raises(ContinuityStoreInvariantError):
        store.review_occurrence_coverage(
            coverage_mode="partial_history",
            historical_review_status="reviewed",
            complete_through="2026-12-31T23:59:59Z",
            reviewer_id="reviewer",
            reason="Would regress.",
            expected_review_version=1,
        )
    with pytest.raises(ContinuityStoreInvariantError):
        store.review_occurrence_coverage(
            coverage_mode="complete_history",
            historical_review_status="reviewed",
            complete_through="2027-01-01T00:00:00Z",
            reviewer_id="reviewer",
            reason="Stale version.",
            expected_review_version=0,
        )


def test_sqlite_historical_coverage_rejects_reversed_interval() -> None:
    store = _store()
    store.ensure_occurrence_coverage(started_at="2026-07-24T00:00:00Z")

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="complete_through cannot precede",
    ):
        store.review_occurrence_coverage(
            coverage_mode="complete_history",
            historical_review_status="reviewed",
            coverage_started_at="2026-07-24T00:00:00Z",
            complete_through="2026-07-23T23:59:59Z",
            reviewer_id="reviewer",
            reason="This reversed interval must never be signed.",
            expected_review_version=0,
        )


def test_postgres_historical_coverage_rejects_reversed_interval() -> None:
    class CoverageGuardStore:
        def _fetch_optional_one(
            self,
            _query: str,
            _params: tuple[object, ...] = (),
        ) -> dict[str, object]:
            return {
                "id": "00000000-0000-0000-0000-000000000001",
                "user_id": "11111111-1111-4111-8111-111111111111",
                "coverage_mode": "forward_only",
                "coverage_started_at": "2026-07-24T00:00:00.000000Z",
                "historical_review_status": "not_reviewed",
                "complete_through": None,
                "review_version": 0,
            }

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="complete_through cannot precede",
    ):
        postgres_occurrences.review_occurrence_coverage(
            CoverageGuardStore(),
            coverage_mode="partial_history",
            historical_review_status="reviewed",
            coverage_started_at="2026-07-24T00:00:00Z",
            complete_through="2026-07-23T23:59:59Z",
            reviewer_id="reviewer",
            reason="This reversed interval must never be signed.",
            expected_review_version=0,
        )


def test_coverage_receipt_is_backend_parity_bound_to_user_principal() -> None:
    payload = {
        "coverage_id": "00000000-0000-0000-0000-000000000001",
        "user_id": "11111111-1111-4111-8111-111111111111",
        "review_version": 2,
        "coverage_mode": "complete_history",
        "coverage_started_at": "2026-01-01T00:00:00Z",
        "historical_review_status": "reviewed",
        "complete_through": "2026-12-31T23:59:59Z",
        "reviewer_id": "reviewer",
        "reason": "Complete reviewed history.",
        "accounting_metadata": _accounting_metadata(),
    }
    postgres_digest = postgres_occurrences._coverage_receipt_digest(**payload)
    sqlite_digest = sqlite_occurrences._coverage_receipt_digest(**payload)
    assert postgres_digest == sqlite_digest
    assert len(postgres_digest) == 64
    assert postgres_digest != postgres_occurrences._coverage_receipt_digest(
        **{
            **payload,
            "user_id": "22222222-2222-4222-8222-222222222222",
        }
    )


def test_sqlite_candidate_memory_can_propose_but_not_sign_occurrence_evidence() -> None:
    store = _store()
    memory = store.create_memory(
        {
            "memory_key": "candidate-occurrence",
            "value": {"text": "Published a release."},
            "status": "candidate",
            "canonical_text": "Published a release.",
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="candidate"))
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(claim["id"]), 1))
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key="candidate-memory-evidence",
            ),
            "memory_id": memory["id"],
        }
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Identity verified.",
    )
    with pytest.raises(ContinuityStoreInvariantError):
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reason="Candidate evidence is not countable.",
            reviewer_id="reviewer",
        )


def _accepted_unit_with_carrier_evidence(
    store: SQLiteVNextStore,
    *,
    claim_key: str,
    evidence_rows: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object]]:
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key=claim_key))
    unit, _ = store.get_or_create_occurrence_unit(
        _unit(
            str(claim["id"]),
            1,
            occurrence_key=f"{claim_key}-occurrence",
        )
    )
    for evidence in evidence_rows:
        carrier_store = (
            None if evidence.get("memory_id") is not None or evidence.get("source_id") is not None else store
        )
        store.create_occurrence_evidence(
            {
                **_quote_evidence(
                    str(claim["id"]),
                    str(unit["id"]),
                    evidence_key=str(evidence["evidence_key"]),
                    store=carrier_store,
                ),
                **evidence,
            }
        )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified.",
    )
    accepted = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reason="Verified.",
        reviewer_id="reviewer",
    )
    return claim, accepted


def _prepare_complete_accounting(
    store: SQLiteVNextStore,
) -> dict[str, object]:
    extractor_version = "phase6-test-v1"
    source_rows = store.conn.execute(
        """
        SELECT id
        FROM sources
        WHERE user_id = ? AND deleted_at IS NULL
        ORDER BY id ASC
        """,
        (store.user_id,),
    ).fetchall()
    if not source_rows:
        source = store.create_source(
            {
                "source_type": "document",
                "content_hash": f"sha256:{uuid4()}",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        source_rows = [(source["id"],)]
    for (source_id,) in source_rows:
        chunk_rows = store.conn.execute(
            """
            SELECT id
            FROM source_chunks
            WHERE user_id = ? AND source_id = ?
            ORDER BY id ASC
            """,
            (store.user_id, str(source_id)),
        ).fetchall()
        if not chunk_rows:
            chunk = store.create_source_chunk(
                {
                    "source_id": str(source_id),
                    "chunk_index": 0,
                    "text": "No occurrence assertion in this accounting fixture.",
                }
            )
            chunk_rows = [(chunk["id"],)]
        for (source_chunk_id,) in chunk_rows:
            evidence_rows = store.conn.execute(
                """
                SELECT
                  claim.id,
                  claim.resolution_status,
                  claim.review_status,
                  evidence.occurrence_id
                FROM occurrence_evidence AS evidence
                JOIN occurrence_claims AS claim
                  ON claim.id = evidence.claim_id
                 AND claim.user_id = evidence.user_id
                WHERE evidence.user_id = ?
                  AND evidence.source_chunk_id = ?
                  AND evidence.evidence_role = 'supports'
                  AND evidence.review_status IN ('candidate', 'accepted')
                ORDER BY claim.id ASC, evidence.occurrence_id ASC
                """,
                (store.user_id, str(source_chunk_id)),
            ).fetchall()
            claim_ids = sorted({str(row[0]) for row in evidence_rows})
            occurrence_ids = sorted(
                {
                    str(row[3])
                    for row in evidence_rows
                    if row[3] is not None and row[1] == "resolved" and row[2] == "accepted"
                }
            )
            has_unresolved = any(row[1] == "pending" and row[2] == "candidate" for row in evidence_rows)
            disposition = (
                "no_occurrence"
                if not evidence_rows
                else "unresolved_claims"
                if has_unresolved
                else "accepted_occurrences"
            )
            recorded, _created = store.record_occurrence_extraction_disposition(
                source_chunk_id=str(source_chunk_id),
                extractor_version=extractor_version,
                disposition=disposition,
                claim_ids=claim_ids,
                occurrence_ids=occurrence_ids,
            )
            if recorded["review_status"] == "candidate":
                store.review_occurrence_extraction_disposition(
                    disposition_id=str(recorded["id"]),
                    action="accepted",
                    reviewer_id="reviewer",
                    reason="Complete reviewed occurrence accounting fixture.",
                    expected_review_version=int(recorded["review_version"]),
                )
    accounting = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
    )
    accounting_metadata = {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": extractor_version,
        "source_ids": accounting["source_ids"],
        "source_chunk_ids": accounting["source_chunk_ids"],
        "snapshot_digest": accounting["snapshot_digest"],
        "disposition_digest": accounting["disposition_digest"],
    }
    return accounting_metadata


def _qualify_complete_coverage(store: SQLiteVNextStore) -> None:
    accounting_metadata = _prepare_complete_accounting(store)
    coverage = store.ensure_occurrence_coverage(started_at="2020-01-01T00:00:00Z")
    store.review_occurrence_coverage(
        coverage_mode="complete_history",
        historical_review_status="reviewed",
        coverage_started_at="2020-01-01T00:00:00Z",
        complete_through="2040-12-31T23:59:59Z",
        reviewer_id="reviewer",
        reason="Complete reviewed occurrence history.",
        accounting_metadata=accounting_metadata,
        expected_review_version=int(coverage["review_version"]),
    )


def test_sqlite_memory_carrier_reconciliation_refreshes_then_retires() -> None:
    store = _store()
    memories = [
        store.create_memory(
            {
                "memory_key": f"carrier-memory-{index}",
                "value": {"text": "Published a release."},
                "status": "active",
                "canonical_text": "Published a release.",
                "domain": "project",
                "sensitivity": "private",
                "project_id": "alice",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        for index in (1, 2)
    ]
    _claim_row, unit = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="memory-carriers",
        evidence_rows=[
            {
                "evidence_key": f"memory-carrier-{index}",
                "memory_id": memory["id"],
            }
            for index, memory in enumerate(memories, start=1)
        ],
    )
    first = store.reconcile_occurrence_evidence_carrier(
        memory_id=str(memories[0]["id"]),
        reviewer_id="reviewer",
        reason="First memory retired.",
    )
    assert first == [
        {
            "occurrence_id": unit["id"],
            "outcome": "refreshed",
            "review_status": "accepted",
            "review_version": 2,
        }
    ]
    assert (
        store.reconcile_occurrence_evidence_carrier(
            memory_id=str(memories[0]["id"]),
            reviewer_id="reviewer",
            reason="Replay.",
        )
        == []
    )
    second = store.reconcile_occurrence_evidence_carrier(
        memory_id=str(memories[1]["id"]),
        reviewer_id="reviewer",
        reason="Last memory retired.",
    )
    assert second[0]["outcome"] == "retired"
    assert second[0]["review_status"] == "retired"


def test_sqlite_source_carrier_reconciliation_refreshes_then_retires() -> None:
    store = _store()
    sources = [
        store.create_source(
            {
                "source_type": "document",
                "content_hash": f"sha256:{uuid4()}",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        for _index in (1, 2)
    ]
    _claim_row, unit = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="source-carriers",
        evidence_rows=[
            {
                "evidence_key": f"source-carrier-{index}",
                "source_id": source["id"],
            }
            for index, source in enumerate(sources, start=1)
        ],
    )
    first = store.reconcile_occurrence_evidence_carrier(
        source_id=str(sources[0]["id"]),
        reviewer_id="reviewer",
        reason="First source retired.",
    )
    assert first[0]["occurrence_id"] == unit["id"]
    assert first[0]["outcome"] == "refreshed"
    second = store.reconcile_occurrence_evidence_carrier(
        source_id=str(sources[1]["id"]),
        reviewer_id="reviewer",
        reason="Last source retired.",
    )
    assert second[0]["outcome"] == "retired"


def test_sqlite_carrier_reconciliation_ignores_cross_count_survivor() -> None:
    store = _store()
    _owner_claim, unit = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="cross-count-survivor-owner",
        evidence_rows=[{"evidence_key": "cross-count-survivor-owner-evidence"}],
    )
    owner_evidence = store.conn.execute(
        """
        SELECT source_id
        FROM occurrence_evidence
        WHERE user_id = ? AND occurrence_id = ?
        """,
        (store.user_id, unit["id"]),
    ).fetchone()
    assert owner_evidence is not None and owner_evidence[0] is not None

    cross_count_payload = _claim(claim_key="cross-count-survivor-candidate")
    cross_count_payload["count_key"] = "attended conference"
    cross_count_claim, _ = store.get_or_create_occurrence_claim(
        cross_count_payload
    )
    cross_source = store.create_source(
        {
            "source_type": "note",
            "content_hash": f"cross-count-survivor:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    quote = "This carrier belongs to a different count family."
    cross_evidence_id = str(uuid4())
    store.conn.execute(
        """
        INSERT INTO occurrence_evidence (
          id, user_id, claim_id, occurrence_id, source_id,
          evidence_key, evidence_role, quote, quote_sha256,
          confidence, review_status, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, 'supports', ?, ?, 0.5, 'candidate', '{}')
        """,
        (
            cross_evidence_id,
            store.user_id,
            cross_count_claim["id"],
            unit["id"],
            cross_source["id"],
            "cross-count-survivor-candidate-evidence",
            quote,
            hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        ),
    )

    outcome = store.reconcile_occurrence_evidence_carrier(
        source_id=str(owner_evidence[0]),
        reviewer_id="reviewer",
        reason="The only compatible carrier was retired.",
    )

    assert outcome == [
        {
            "occurrence_id": unit["id"],
            "outcome": "retired",
            "review_status": "retired",
            "review_version": 2,
        }
    ]
    cross_status = store.conn.execute(
        """
        SELECT review_status
        FROM occurrence_evidence
        WHERE user_id = ? AND id = ?
        """,
        (store.user_id, cross_evidence_id),
    ).fetchone()
    assert cross_status == ("candidate",)


def test_sqlite_evidence_creation_rejects_terminal_claim_and_unit_lifecycles() -> None:
    store = _store()
    owner_claim, accepted_unit = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="terminal-evidence-unit",
        evidence_rows=[{"evidence_key": "terminal-evidence-unit-original"}],
    )
    retired = store.review_occurrence_unit(
        occurrence_id=str(accepted_unit["id"]),
        action="retired",
        expected_status="accepted",
        expected_review_version=int(accepted_unit["review_version"]),
        reviewer_id="reviewer",
        reason="This unit is terminal.",
    )
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="candidate or accepted unit",
    ):
        store.create_occurrence_evidence(
            _quote_evidence(
                str(owner_claim["id"]),
                str(retired["id"]),
                evidence_key="terminal-evidence-unit-late",
                store=store,
            )
        )

    rejected_claim, _ = store.get_or_create_occurrence_claim(
        _claim(
            claim_key="terminal-evidence-claim",
            identity_basis="ambiguous",
            resolution_decision="ambiguous",
        )
    )
    store.review_occurrence_claim(
        claim_id=str(rejected_claim["id"]),
        resolution_status="rejected",
        resolution_decision="ambiguous",
        identity_basis="ambiguous",
        reviewer_id="reviewer",
        reason="This claim is terminal.",
    )
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="live candidate or accepted claim",
    ):
        store.create_occurrence_evidence(
            _quote_evidence(
                str(rejected_claim["id"]),
                None,
                evidence_key="terminal-evidence-claim-late",
                store=store,
            )
        )

    rows = store.conn.execute(
        """
        SELECT evidence_key
        FROM occurrence_evidence
        WHERE user_id = ?
          AND evidence_key IN (?, ?)
        """,
        (
            store.user_id,
            "terminal-evidence-unit-late",
            "terminal-evidence-claim-late",
        ),
    ).fetchall()
    assert rows == []


def test_sqlite_timeless_detection_keeps_future_dated_rows_out() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="timeless-and-future", quantity=2))
    timeless_payload = _unit(str(claim["id"]), 1, occurrence_key="timeless")
    timeless_payload["occurred_at_start"] = None
    timeless_payload["occurred_at_end"] = None
    future_payload = _unit(str(claim["id"]), 2, occurrence_key="future")
    future_payload["occurred_at_start"] = "2030-01-01T00:00:00Z"
    future_payload["occurred_at_end"] = "2030-01-01T00:00:00Z"
    units = [store.get_or_create_occurrence_unit(payload)[0] for payload in (timeless_payload, future_payload)]
    for index, unit in enumerate(units, start=1):
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key=f"timeless-evidence-{index}",
                store=store,
            )
        )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified.",
    )
    for unit in units:
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reason="Verified.",
            reviewer_id="reviewer",
        )
    query = {
        "query": "published release",
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
        "occurred_at_end": datetime(2026, 12, 31, tzinfo=UTC),
    }
    assert store.search_accepted_occurrence_units(**query) == []
    detected = store.search_accepted_occurrence_units(
        **query,
        include_timeless=True,
    )
    assert [row["occurrence_key"] for row in detected] == ["timeless"]

    ambiguous_payload = _claim(
        claim_key="timeless-ambiguous",
        identity_basis="ambiguous",
        resolution_decision="ambiguous",
    )
    ambiguous_payload["occurred_at_start"] = None
    ambiguous_payload["occurred_at_end"] = None
    ambiguous, _ = store.get_or_create_occurrence_claim(ambiguous_payload)
    store.create_occurrence_evidence(
        _quote_evidence(
            str(ambiguous["id"]),
            None,
            evidence_key="timeless-ambiguous-evidence",
            store=store,
        )
    )
    unresolved_query = {
        "count_key": "published release",
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
        "occurred_at_end": datetime(2026, 12, 31, tzinfo=UTC),
    }
    assert store.list_unresolved_occurrence_claims(**unresolved_query) == []
    assert [
        row["id"]
        for row in store.list_unresolved_occurrence_claims(
            **unresolved_query,
            include_timeless=True,
        )
    ] == [ambiguous["id"]]


def test_sqlite_occurrence_filters_use_half_open_upper_boundary() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="upper-boundary"))
    unit, _ = store.get_or_create_occurrence_unit(_unit(str(claim["id"]), 1, occurrence_key="upper-boundary"))
    store.create_occurrence_evidence(
        _quote_evidence(
            str(claim["id"]),
            str(unit["id"]),
            evidence_key="upper-boundary-evidence",
            store=store,
        )
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified.",
    )
    store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reason="Verified.",
        reviewer_id="reviewer",
    )
    window_end = datetime(2026, 7, 24, 12, tzinfo=UTC)
    assert (
        store.search_accepted_occurrence_units(
            query="published release",
            projects=["alice"],
            domains=["project"],
            sensitivity_allowed=["private"],
            occurred_at_end=window_end,
        )
        == []
    )

    unresolved_payload = _claim(
        claim_key="unresolved-upper-boundary",
        identity_basis="ambiguous",
        resolution_decision="ambiguous",
    )
    unresolved, _ = store.get_or_create_occurrence_claim(unresolved_payload)
    store.create_occurrence_evidence(
        _quote_evidence(
            str(unresolved["id"]),
            None,
            evidence_key="unresolved-upper-boundary-evidence",
            store=store,
        )
    )
    assert (
        store.list_unresolved_occurrence_claims(
            projects=["alice"],
            domains=["project"],
            sensitivity_allowed=["private"],
            occurred_at_end=window_end,
        )
        == []
    )


def test_sqlite_source_chunk_bulk_lookup_is_bounded_deduplicated_and_scoped() -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "document",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Signed occurrence evidence.",
        }
    )
    assert store.get_source_chunks_by_ids([str(chunk["id"]), str(chunk["id"])]) == [
        {"id": chunk["id"], "source_id": source["id"]}
    ]
    assert store.get_source_chunk_for_occurrence_accounting(str(chunk["id"])) == {
        "id": chunk["id"],
        "source_id": source["id"],
        "text": "Signed occurrence evidence.",
        "source_title": None,
        "snapshot_sha256": sqlite_occurrences._extraction_snapshot_sha256(
            {
                "source_id": source["id"],
                "source_content_hash": source["content_hash"],
                "source_domain": source["domain"],
                "source_sensitivity": source["sensitivity"],
                "source_title": None,
                "source_created_at": source["source_created_at"],
                "source_session_date": None,
                "source_provenance_role": None,
                "source_project_scope": [],
                "source_chunk_id": chunk["id"],
                "chunk_index": chunk["chunk_index"],
                "chunk_text": chunk["text"],
            }
        ),
    }
    assert store.get_source_chunks_by_ids([]) == []
    with pytest.raises(ValueError, match="cannot exceed 200"):
        store.get_source_chunks_by_ids([str(uuid4()) for _index in range(201)])

    other_user_id = str(uuid4())
    ensure_sqlite_user(
        store.conn,
        other_user_id,
        f"{other_user_id}@example.com",
        "Other User",
    )
    other_store = SQLiteVNextStore(store.conn, other_user_id)
    assert other_store.get_source_chunks_by_ids([str(chunk["id"])]) == []
    assert other_store.get_source_chunk_for_occurrence_accounting(str(chunk["id"])) is None


def test_sqlite_occurrence_memory_lookup_is_bounded_and_checks_both_chunk_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "document",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Occurrence lookup source.",
        }
    )
    chunk_id = str(chunk["id"])

    def create_bound_memory(
        label: str,
        *,
        top_level_chunk_id: str,
        proposal_chunk_id: str,
        status: str,
    ) -> dict[str, object]:
        return store.create_memory(
            {
                "memory_key": f"occurrence-lookup.{label}",
                "value": {"text": label},
                "status": status,
                "memory_type": "semantic",
                "title": label,
                "canonical_text": label,
                "summary": label,
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {
                    "source_chunk_id": top_level_chunk_id,
                    "occurrence_proposal": {
                        "source_chunk_id": proposal_chunk_id,
                    },
                },
            }
        )

    active = create_bound_memory(
        "active-match",
        top_level_chunk_id=chunk_id,
        proposal_chunk_id=chunk_id,
        status="active",
    )
    candidate = create_bound_memory(
        "candidate-match",
        top_level_chunk_id=chunk_id,
        proposal_chunk_id=chunk_id,
        status="candidate",
    )
    create_bound_memory(
        "top-level-mismatch",
        top_level_chunk_id=str(uuid4()),
        proposal_chunk_id=chunk_id,
        status="active",
    )
    create_bound_memory(
        "proposal-mismatch",
        top_level_chunk_id=chunk_id,
        proposal_chunk_id=str(uuid4()),
        status="candidate",
    )
    other_user_id = str(uuid4())
    ensure_sqlite_user(
        store.conn,
        other_user_id,
        f"{other_user_id}@example.com",
        "Other Occurrence User",
    )
    other_store = SQLiteVNextStore(store.conn, other_user_id)
    other_memory = other_store.create_memory(
        {
            "memory_key": "occurrence-lookup.other-user",
            "value": {"text": "other-user-match"},
            "status": "active",
            "memory_type": "semantic",
            "title": "other-user-match",
            "canonical_text": "other-user-match",
            "summary": "other-user-match",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "source_chunk_id": chunk_id,
                "occurrence_proposal": {
                    "source_chunk_id": chunk_id,
                },
            },
        }
    )
    captured_queries: list[tuple[str, tuple[object, ...]]] = []
    fetch_all = store._fetch_all

    def recording_fetch_all(
        query: str,
        params: tuple[object, ...] = (),
    ) -> list[dict[str, object]]:
        if "$.occurrence_proposal.source_chunk_id" in query:
            captured_queries.append((query, params))
        return fetch_all(query, params)

    monkeypatch.setattr(store, "_fetch_all", recording_fetch_all)

    rows = store.list_memories_for_source_chunk(chunk_id)

    assert [str(row["id"]) for row in rows] == sorted(
        (str(active["id"]), str(candidate["id"])),
    )
    assert str(other_memory["id"]) not in {str(row["id"]) for row in rows}
    assert {str(row["status"]) for row in rows} == {"active", "candidate"}
    assert len(captured_queries) == 1
    lookup_sql, lookup_params = captured_queries[0]
    assert "json_extract(metadata_json, '$.source_chunk_id') = ?" in lookup_sql
    assert "$.occurrence_proposal.source_chunk_id" in lookup_sql
    assert "ORDER BY id ASC" in lookup_sql
    assert lookup_params[-1] == 201
    plan = store.conn.execute(
        f"EXPLAIN QUERY PLAN {lookup_sql}",
        lookup_params,
    ).fetchall()
    assert any("USING INDEX memories_occurrence_source_chunk_idx" in str(row[3]) for row in plan)


def test_sqlite_occurrence_read_snapshot_is_stable_across_wal_commit(
    tmp_path,
) -> None:
    db_path = tmp_path / "occurrence-snapshot.db"
    setup = sqlite3.connect(db_path)
    bootstrap_sqlite_schema(setup)
    user_id = str(uuid4())
    ensure_sqlite_user(setup, user_id, f"{user_id}@example.com", "Snapshot User")
    setup.commit()
    setup.close()

    reader_conn = sqlite3.connect(db_path)
    writer_conn = sqlite3.connect(db_path, timeout=0)
    reader = SQLiteVNextStore(reader_conn, user_id)
    writer = SQLiteVNextStore(writer_conn, user_id)
    try:
        before_snapshot = datetime.now(UTC)
        proof = reader.begin_occurrence_read_snapshot()
        after_snapshot = datetime.now(UTC)
        lifecycle_as_of = proof.pop("lifecycle_as_of")
        assert proof == {
            "proof": "occurrence_read_snapshot_v1",
            "acquired": True,
            "backend": "sqlite",
            "mode": "transaction_snapshot",
        }
        assert isinstance(lifecycle_as_of, datetime)
        assert lifecycle_as_of.tzinfo is not None
        assert lifecycle_as_of.utcoffset() == timedelta(0)
        assert before_snapshot <= lifecycle_as_of <= after_snapshot
        assert reader.get_occurrence_coverage() is None
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            writer.ensure_occurrence_coverage(
                started_at="2026-01-01T00:00:00Z"
            )
        writer_conn.rollback()
        assert reader.get_occurrence_coverage() is None

        reader.end_occurrence_read_snapshot()
        assert reader_conn.in_transaction is False
        writer.ensure_occurrence_coverage(started_at="2026-01-01T00:00:00Z")
        writer_conn.commit()
        reader.begin_occurrence_read_snapshot()
        assert reader.get_occurrence_coverage() is not None
        reader.end_occurrence_read_snapshot()
        assert reader_conn.in_transaction is False

        writer.review_occurrence_coverage(
            coverage_mode="forward_only",
            historical_review_status="needs_review",
            reviewer_id="reviewer",
            reason="Exercise a write after the reader releases its WAL snapshot.",
        )
        writer_conn.commit()
        reader.begin_occurrence_read_snapshot()
        assert reader.get_occurrence_coverage()["historical_review_status"] == "needs_review"
        reader.end_occurrence_read_snapshot()
    finally:
        reader_conn.close()
        writer_conn.close()


def test_sqlite_occurrence_snapshot_captures_clock_before_snapshot_pin(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "occurrence-snapshot-clock-order.db"
    setup = sqlite3.connect(db_path)
    setup.execute("PRAGMA journal_mode=WAL")
    bootstrap_sqlite_schema(setup)
    user_id = str(uuid4())
    ensure_sqlite_user(
        setup,
        user_id,
        f"{user_id}@example.com",
        "Snapshot Clock User",
    )
    setup.commit()
    setup.close()

    reader_conn = sqlite3.connect(db_path)
    writer_conn = sqlite3.connect(db_path)
    reader = SQLiteVNextStore(reader_conn, user_id)
    writer = SQLiteVNextStore(writer_conn, user_id)
    real_datetime = datetime

    class CommitAtClockCapture:
        @classmethod
        def now(cls, timezone):
            writer.ensure_occurrence_coverage(
                started_at="2026-01-01T00:00:00Z"
            )
            writer_conn.commit()
            return real_datetime.now(timezone)

    monkeypatch.setattr(
        sqlite_occurrences,
        "datetime",
        CommitAtClockCapture,
    )
    try:
        reader.begin_occurrence_read_snapshot()
        assert reader.get_occurrence_coverage() is not None
        reader.end_occurrence_read_snapshot()
    finally:
        reader_conn.close()
        writer_conn.close()


def test_sqlite_occurrence_snapshot_preserves_caller_owned_transaction() -> None:
    store = _store()
    store.conn.commit()
    store.conn.execute("BEGIN")
    assert store.conn.in_transaction is True

    store.begin_occurrence_read_snapshot()
    store.end_occurrence_read_snapshot()

    assert store.conn.in_transaction is True
    store.ensure_occurrence_coverage(started_at="2026-01-01T00:00:00Z")
    store.conn.rollback()
    assert store.get_occurrence_coverage() is None


def test_sqlite_stale_caller_snapshot_fails_closed_without_rollback(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "occurrence-stale-caller-snapshot.db"
    setup = sqlite3.connect(db_path)
    setup.execute("PRAGMA journal_mode=WAL")
    bootstrap_sqlite_schema(setup)
    user_id = str(uuid4())
    ensure_sqlite_user(
        setup,
        user_id,
        f"{user_id}@example.com",
        "Stale Snapshot User",
    )
    setup.commit()
    setup.close()

    reader_conn = sqlite3.connect(db_path, timeout=0)
    writer_conn = sqlite3.connect(db_path, timeout=0)
    reader = SQLiteVNextStore(reader_conn, user_id)
    writer = SQLiteVNextStore(writer_conn, user_id)
    monkeypatch.setattr(
        "alicebot_api.vnext_retrieval.append_event",
        lambda *_args, **_kwargs: {},
    )
    try:
        _accepted_unit_with_carrier_evidence(
            writer,
            claim_key="stale-snapshot-first",
            evidence_rows=[
                {"evidence_key": "stale-snapshot-first-evidence"}
            ],
        )
        _qualify_complete_coverage(writer)
        writer_conn.commit()

        reader_conn.execute("BEGIN")
        pinned = reader.get_occurrence_coverage()
        assert pinned is not None
        assert pinned["coverage_mode"] == "complete_history"

        _accepted_unit_with_carrier_evidence(
            writer,
            claim_key="stale-snapshot-second",
            evidence_rows=[
                {"evidence_key": "stale-snapshot-second-evidence"}
            ],
        )
        invalidated = writer.get_occurrence_coverage()
        assert invalidated is not None
        assert invalidated["coverage_mode"] == "forward_only"
        writer.review_occurrence_coverage(
            coverage_mode="forward_only",
            historical_review_status="not_reviewed",
            complete_through="2040-12-31T23:59:59Z",
            reviewer_id="reviewer",
            reason=(
                "Re-sign the forward-only boundary after the second "
                "accepted occurrence."
            ),
            expected_review_version=int(invalidated["review_version"]),
        )
        writer_conn.commit()

        request = VNextRetrievalRequest(
            query="How many times did I publish a release?",
            projects=("alice",),
            domains=("project",),
            reference_time=datetime(2030, 1, 1, tzinfo=UTC),
        )
        stale_pack = VNextRetrievalService(reader).compile_context_pack(
            request
        )
        assert "aggregation" not in stale_pack
        assert reader_conn.in_transaction is True
        assert reader.get_occurrence_coverage()["coverage_mode"] == (
            "complete_history"
        )

        reader_conn.rollback()
        fresh_pack = VNextRetrievalService(writer).compile_context_pack(
            request
        )
        assert fresh_pack["aggregation"]["answer_kind"] == "at_least"
        assert fresh_pack["aggregation"]["lower_bound"] == 2
    finally:
        if reader_conn.in_transaction:
            reader_conn.rollback()
        if writer_conn.in_transaction:
            writer_conn.rollback()
        reader_conn.close()
        writer_conn.close()


def test_sqlite_occurrence_snapshot_rejects_nested_or_unbalanced_lifecycle() -> None:
    store = _store()
    store.conn.commit()
    store.begin_occurrence_read_snapshot()
    with pytest.raises(ContinuityStoreInvariantError, match="already active"):
        store.begin_occurrence_read_snapshot()
    store.end_occurrence_read_snapshot()
    with pytest.raises(ContinuityStoreInvariantError, match="no occurrence"):
        store.end_occurrence_read_snapshot()


class _PostgresSnapshotCursor:
    def __init__(self, rows: list[object]) -> None:
        self.queries: list[tuple[str, object | None]] = []
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: object | None = None) -> None:
        self.queries.append((query, params))

    def fetchone(self) -> object | None:
        return self.rows.pop(0) if self.rows else None


class _PostgresSnapshotConnection:
    def __init__(
        self,
        rows: list[object],
        *,
        dsn: str = "postgresql://alice",
        password: str = "secret-password",
        close_error: bool = False,
    ) -> None:
        self.cursor_instance = _PostgresSnapshotCursor(rows)
        self.info = type("Info", (), {"dsn": dsn, "password": password})()
        self.rolled_back = False
        self.closed = False
        self.close_error = close_error

    def cursor(self) -> _PostgresSnapshotCursor:
        return self.cursor_instance

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True
        if self.close_error:
            raise RuntimeError("snapshot close failed")


class _TrackingSemaphore:
    def __init__(self) -> None:
        self.acquired = 0
        self.released = 0

    def acquire(self, *, blocking: bool) -> bool:
        assert blocking is False
        self.acquired += 1
        return True

    def release(self) -> None:
        self.released += 1


def test_postgres_occurrence_read_snapshot_is_dedicated_read_only_and_cleaned(
    monkeypatch,
) -> None:
    lifecycle_as_of = datetime(2026, 7, 24, 12, 34, 56, tzinfo=UTC)
    parent = _PostgresSnapshotConnection([{"current_setting": "11111111-1111-4111-8111-111111111111"}])
    snapshot = _PostgresSnapshotConnection(
        [
            {
                "isolation": "repeatable read",
                "read_only": "on",
                "snapshot_id": "10:20:",
                "lifecycle_as_of": lifecycle_as_of,
            }
        ]
    )
    connections: list[tuple[object, ...]] = []
    slots = _TrackingSemaphore()

    def fake_connect(
        dsn: str,
        *,
        password: str,
        row_factory: object,
        connect_timeout: int,
    ):
        connections.append((dsn, password, row_factory, connect_timeout))
        return snapshot

    monkeypatch.setattr(postgres_occurrences.psycopg, "connect", fake_connect)
    monkeypatch.setattr(postgres_occurrences, "_OCCURRENCE_SNAPSHOT_SLOTS", slots)
    store = type("SnapshotStore", (), {"conn": parent})()
    proof = postgres_occurrences.begin_occurrence_read_snapshot(store)
    assert proof == {
        "proof": "occurrence_read_snapshot_v1",
        "acquired": True,
        "backend": "postgres",
        "mode": "repeatable_read_read_only",
        "snapshot_id": "10:20:",
        "lifecycle_as_of": lifecycle_as_of,
    }
    assert connections[0][:2] == (parent.info.dsn, parent.info.password)
    assert connections[0][3] == 5
    assert slots.acquired == 1
    assert store.conn is snapshot
    snapshot_queries = [query for query, _params in snapshot.cursor_instance.queries]
    assert snapshot_queries[0].strip() == ("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    assert "set_config('app.current_user_id'" in snapshot_queries[1]
    assert "transaction_isolation" in snapshot_queries[2]
    assert "transaction_timestamp() AS lifecycle_as_of" in snapshot_queries[2]
    assert "clock_timestamp()" not in snapshot_queries[2]
    assert all("LOCK TABLE" not in query for query in snapshot_queries)

    postgres_occurrences.end_occurrence_read_snapshot(store)
    assert store.conn is parent
    assert snapshot.rolled_back is True
    assert snapshot.closed is True
    assert slots.released == 1


def test_postgres_occurrence_snapshot_connect_failure_releases_capacity(
    monkeypatch,
) -> None:
    parent = _PostgresSnapshotConnection([{"current_setting": "11111111-1111-4111-8111-111111111111"}])
    slots = _TrackingSemaphore()

    def fail_connect(*_args: object, **_kwargs: object):
        raise RuntimeError("password auth failed")

    monkeypatch.setattr(postgres_occurrences.psycopg, "connect", fail_connect)
    monkeypatch.setattr(postgres_occurrences, "_OCCURRENCE_SNAPSHOT_SLOTS", slots)
    store = type("SnapshotStore", (), {"conn": parent})()
    with pytest.raises(RuntimeError, match="password auth failed"):
        postgres_occurrences.begin_occurrence_read_snapshot(store)
    assert store.conn is parent
    assert slots.acquired == 1
    assert slots.released == 1


def test_postgres_occurrence_snapshot_dsn_failure_releases_capacity(
    monkeypatch,
) -> None:
    parent = _PostgresSnapshotConnection([{"current_setting": "11111111-1111-4111-8111-111111111111"}])
    slots = _TrackingSemaphore()

    def fail_conninfo(_dsn: str) -> dict[str, str]:
        raise RuntimeError("malformed snapshot dsn")

    monkeypatch.setattr(postgres_occurrences, "conninfo_to_dict", fail_conninfo)
    monkeypatch.setattr(
        postgres_occurrences.psycopg,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("DSN parsing must precede connect"),
    )
    monkeypatch.setattr(postgres_occurrences, "_OCCURRENCE_SNAPSHOT_SLOTS", slots)
    store = type("SnapshotStore", (), {"conn": parent})()

    with pytest.raises(RuntimeError, match="malformed snapshot dsn"):
        postgres_occurrences.begin_occurrence_read_snapshot(store)

    assert store.conn is parent
    assert slots.acquired == 1
    assert slots.released == 1


def test_postgres_occurrence_snapshot_proof_cleanup_releases_after_close_error(
    monkeypatch,
) -> None:
    parent = _PostgresSnapshotConnection([{"current_setting": "11111111-1111-4111-8111-111111111111"}])
    snapshot = _PostgresSnapshotConnection(
        [
            {
                "isolation": "read committed",
                "read_only": "off",
                "snapshot_id": "10:20:",
                "lifecycle_as_of": datetime(2026, 7, 24, 12, tzinfo=UTC),
            }
        ],
        close_error=True,
    )
    slots = _TrackingSemaphore()
    monkeypatch.setattr(
        postgres_occurrences.psycopg,
        "connect",
        lambda *_args, **_kwargs: snapshot,
    )
    monkeypatch.setattr(postgres_occurrences, "_OCCURRENCE_SNAPSHOT_SLOTS", slots)
    store = type("SnapshotStore", (), {"conn": parent})()
    with pytest.raises(RuntimeError, match="snapshot close failed"):
        postgres_occurrences.begin_occurrence_read_snapshot(store)
    assert store.conn is parent
    assert snapshot.rolled_back is True
    assert snapshot.closed is True
    assert slots.released == 1


def test_postgres_occurrence_snapshot_rejects_naive_database_lifecycle_clock(
    monkeypatch,
) -> None:
    parent = _PostgresSnapshotConnection([{"current_setting": "11111111-1111-4111-8111-111111111111"}])
    snapshot = _PostgresSnapshotConnection(
        [
            {
                "isolation": "repeatable read",
                "read_only": "on",
                "snapshot_id": "10:20:",
                "lifecycle_as_of": datetime(2026, 7, 24, 12),
            }
        ]
    )
    slots = _TrackingSemaphore()
    monkeypatch.setattr(
        postgres_occurrences.psycopg,
        "connect",
        lambda *_args, **_kwargs: snapshot,
    )
    monkeypatch.setattr(postgres_occurrences, "_OCCURRENCE_SNAPSHOT_SLOTS", slots)
    store = type("SnapshotStore", (), {"conn": parent})()

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="aware database lifecycle clock",
    ):
        postgres_occurrences.begin_occurrence_read_snapshot(store)

    assert store.conn is parent
    assert snapshot.rolled_back is True
    assert snapshot.closed is True
    assert slots.released == 1


class _PostgresShapeStore:
    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    def _fetch_all(
        self,
        query: str,
        params: tuple[object, ...],
    ) -> list[dict[str, object]]:
        self._record(query, params)
        if "SELECT id, claim_id" in query and "FROM occurrence_units" in query:
            return [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "claim_id": "22222222-2222-4222-8222-222222222222",
                }
            ]
        return []

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[object, ...] = (),
    ) -> dict[str, object] | None:
        self._record(query, params)
        if "FROM occurrence_coverage" in query:
            return None
        if "FROM occurrence_claims" in query and "FOR UPDATE" in query:
            return {
                "id": str(params[0]),
                "review_status": "accepted",
                "resolution_status": "resolved",
            }
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "user_id": "11111111-1111-4111-8111-111111111111",
            "claim_id": "22222222-2222-4222-8222-222222222222",
            "claim_ordinal": 1,
            "occurrence_key": "shape-occurrence",
            "count_key": "published release",
            "predicate_json": _predicate(),
            "canonical_text": "Published one release.",
            "aggregation_json": _unit_aggregation("shape-occurrence"),
            "unit_value": 1,
            "review_status": "candidate",
            "identity_status": "resolved",
            "ambiguity_group_key": None,
            "occurred_at_start": "2026-07-24T12:00:00Z",
            "occurred_at_end": "2026-07-24T12:00:00Z",
            "domain": "project",
            "sensitivity": "private",
            "project_scope": ["alice"],
            "source_id": "33333333-3333-4333-8333-333333333333",
            "source_content_hash": "sha256:shape-source",
            "source_domain": "project",
            "source_sensitivity": "private",
            "source_title": "Shape source",
            "source_created_at": "2026-07-24T12:00:00Z",
            "source_session_date": "2026-07-24",
            "source_provenance_role": "user",
            "source_project_scope": ["alice"],
            "source_chunk_id": "44444444-4444-4444-8444-444444444444",
            "chunk_index": 0,
            "chunk_text": "Shape source text.",
            "review_version": 1,
            "review_receipt_digest": "a" * 64,
            "review_receipt_action": "accepted",
            "reviewed_evidence_count": 1,
            "reviewed_evidence_digest": "b" * 64,
            "superseded_by": None,
            "retired_at": None,
        }

    def _append_mutation_event(self, **_kwargs: Any) -> None:
        return None

    def _record(self, query: str, params: tuple[object, ...]) -> None:
        assert query.count("%s") == len(params)
        self.queries.append((query, params))


def test_postgres_disposition_record_rejects_stale_expected_snapshot_before_write() -> None:
    store = _PostgresShapeStore()

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="snapshot CAS is stale",
    ):
        postgres_occurrences.record_occurrence_extraction_disposition(
            store,
            source_chunk_id="44444444-4444-4444-8444-444444444444",
            extractor_version="phase6-title-cas-v1",
            expected_snapshot_sha256="0" * 64,
            disposition="no_occurrence",
        )

    assert len(store.queries) == 1
    query, params = store.queries[0]
    assert "source.title AS source_title" in query
    assert "source.deleted_at IS NULL" in query
    assert "INSERT INTO occurrence_extraction_dispositions" not in query
    assert params == ("44444444-4444-4444-8444-444444444444",)


def test_postgres_occurrence_queries_keep_placeholder_parity() -> None:
    store = _PostgresShapeStore()
    stable_as_of = datetime(2036, 7, 24, 12, tzinfo=UTC)
    postgres_occurrences.list_unresolved_occurrence_claims(
        store,
        count_key="published release",
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        as_of=stable_as_of,
        limit=10,
    )
    postgres_occurrences.list_occurrence_evidence_for_units(
        store,
        ["00000000-0000-0000-0000-000000000001"],
        as_of=stable_as_of,
    )
    postgres_occurrences.search_accepted_occurrence_units(
        store,
        query="published release",
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        occurred_at_end=datetime(2026, 7, 24, 12, tzinfo=UTC),
        include_timeless=True,
        as_of=stable_as_of,
    )
    postgres_occurrences.get_source_chunks_by_ids(
        store,
        ["00000000-0000-0000-0000-000000000001"],
    )
    postgres_occurrences.get_source_chunk_for_occurrence_accounting(
        store,
        "00000000-0000-0000-0000-000000000001",
    )
    postgres_occurrences.list_memories_for_source_chunk(
        store,
        "00000000-0000-0000-0000-000000000001",
    )
    postgres_occurrences.review_occurrence_unit(
        store,
        occurrence_id="00000000-0000-0000-0000-000000000001",
        action="accepted",
        reason="Verified.",
        reviewer_id="reviewer",
        expected_review_version=1,
    )
    postgres_occurrences.list_accepted_occurrence_units(
        store,
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        occurred_at_start=datetime(2026, 7, 24, 11, tzinfo=UTC),
        occurred_at_end=datetime(2026, 7, 25, tzinfo=UTC),
        as_of=stable_as_of,
        after_id="00000000-0000-0000-0000-000000000001",
        limit=37,
    )
    assert len(store.queries) == 12
    assert (
        "COALESCE(claim.occurred_at_start, claim.occurred_at_end)\n                  < %s::timestamptz"
    ) in store.queries[0][0]
    assert (
        "COALESCE(unit.occurred_at_start, unit.occurred_at_end)\n                  < %s::timestamptz"
    ) in store.queries[2][0]
    unresolved_sql, unresolved_params = store.queries[0]
    evidence_sql, evidence_params = store.queries[1]
    accepted_sql, accepted_params = store.queries[2]
    assert "FROM occurrence_evidence" not in unresolved_sql
    assert "FROM occurrence_evidence" not in accepted_sql
    assert "claim.id::text" not in unresolved_sql
    assert "(%s::uuid IS NULL OR claim.id > %s::uuid)" in unresolved_sql
    assert "ORDER BY claim.id ASC" in unresolved_sql
    assert "unit.id::text" not in accepted_sql
    assert "(%s::uuid IS NULL OR unit.id > %s::uuid)" in accepted_sql
    assert "ORDER BY unit.id ASC" in accepted_sql
    assert stable_as_of not in unresolved_params
    assert stable_as_of in evidence_params
    assert stable_as_of not in accepted_params
    for query in (unresolved_sql, evidence_sql, accepted_sql):
        assert "clock_timestamp()" not in query
    targeted_sql, targeted_params = store.queries[4]
    assert "source.title AS source_title" in targeted_sql
    assert "chunk.id AS source_chunk_id" in targeted_sql
    assert "chunk.text AS chunk_text" in targeted_sql
    assert "source.deleted_at IS NULL" in targeted_sql
    assert targeted_params == ("00000000-0000-0000-0000-000000000001",)
    lookup_sql, lookup_params = store.queries[5]
    assert "metadata_json ->> 'source_chunk_id' = %s" in lookup_sql
    assert "metadata_json #>> '{occurrence_proposal,source_chunk_id}' = %s" in lookup_sql
    assert "ORDER BY id ASC" in lookup_sql
    assert lookup_params[-1] == 201
    review_sql = store.queries[9][0]
    assert postgres_occurrences._OCCURRENCE_QUOTE_STRIPPED_SQL in review_sql
    assert "chr(28)" in postgres_occurrences._OCCURRENCE_QUOTE_STRIPPED_SQL
    assert "chr(160)" in postgres_occurrences._OCCURRENCE_QUOTE_STRIPPED_SQL
    assert "char_length(btrim(evidence.quote))" not in review_sql
    assert "reviewed_evidence_count = receipt.evidence_count" in review_sql
    assert "reviewed_evidence_digest = receipt.evidence_digest" in review_sql
    assert "review_receipt_digest = receipt.review_receipt_digest" in review_sql
    assert "review_receipt_action = %s" in review_sql
    assert "THEN unit.review_receipt_digest" not in review_sql
    assert "claim.count_key = unit.count_key" in review_sql
    assert "successor.count_key = unit.count_key" in review_sql
    assert "successor.domain = unit.domain" in review_sql
    assert "successor.sensitivity = unit.sensitivity" in review_sql
    assert "successor.project_scope = unit.project_scope" in review_sql
    assert postgres_occurrences._OCCURRENCE_SUCCESSOR_AGGREGATION_COMPATIBLE_SQL in review_sql
    assert "successor.aggregation_json = unit.aggregation_json" not in review_sql
    all_accepted_sql, all_accepted_params = store.queries[11]
    assert "selector_keys" not in all_accepted_sql
    assert "ORDER BY unit.id ASC" in all_accepted_sql
    assert "(%s::uuid IS NULL OR unit.id > %s::uuid)" in all_accepted_sql
    assert all_accepted_params[-1] == 37


def test_postgres_disposition_review_cas_binds_exact_candidate_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunk = {
        "source_id": "22222222-2222-4222-8222-222222222222",
        "source_content_hash": "sha256:source",
        "source_domain": "project",
        "source_sensitivity": "private",
        "source_project_scope": ["alice"],
        "source_chunk_id": "33333333-3333-4333-8333-333333333333",
        "chunk_index": 0,
        "chunk_text": "Neutral chunk.",
    }
    current = {
        "id": "00000000-0000-0000-0000-000000000001",
        "user_id": "11111111-1111-4111-8111-111111111111",
        "source_id": chunk["source_id"],
        "source_chunk_id": chunk["source_chunk_id"],
        "snapshot_sha256": postgres_occurrences._extraction_snapshot_sha256(chunk),
        "extractor_version": "phase6-cas-shape-v1",
        "disposition": "no_occurrence",
        "predicate_keys": [],
        "claim_ids": [],
        "occurrence_ids": [],
        "review_status": "candidate",
        "review_version": 0,
        "review_receipt_digest": None,
        "metadata_json": {"raw_no_occurrence_guard": False},
    }

    class DispositionReviewShapeStore:
        def __init__(self) -> None:
            self.queries: list[tuple[str, tuple[object, ...]]] = []

        def _fetch_optional_one(
            self,
            query: str,
            params: tuple[object, ...] = (),
        ) -> dict[str, object]:
            assert query.count("%s") == len(params)
            self.queries.append((query, params))
            if query.lstrip().startswith("UPDATE"):
                return {
                    **current,
                    "review_status": "rejected",
                    "review_version": 1,
                    "review_receipt_digest": params[3],
                }
            return dict(current)

        def _append_mutation_event(self, **_kwargs: Any) -> None:
            return None

    store = DispositionReviewShapeStore()
    monkeypatch.setattr(
        postgres_occurrence_accounting,
        "_current_extraction_chunk",
        lambda _store, _source_chunk_id: chunk,
    )
    monkeypatch.setattr(
        postgres_occurrence_accounting,
        "invalidate_occurrence_coverage",
        lambda *_args, **_kwargs: None,
    )
    reviewed = postgres_occurrences.review_occurrence_extraction_disposition(
        store,
        disposition_id=str(current["id"]),
        action="rejected",
        reviewer_id="reviewer",
        reason="Shape proof.",
        expected_review_version=0,
    )
    assert reviewed["review_status"] == "rejected"
    update_sql, update_params = store.queries[1]
    for predicate in (
        "AND source_id = %s::uuid",
        "AND source_chunk_id = %s::uuid",
        "AND snapshot_sha256 = %s",
        "AND extractor_version = %s",
        "AND disposition = %s",
        "AND predicate_keys = %s",
        "AND claim_ids = %s",
        "AND occurrence_ids = %s",
        "AND metadata_json = %s",
    ):
        assert predicate in update_sql
    assert len(update_params) == 15


def test_extraction_snapshot_title_normalization_has_backend_parity() -> None:
    chunk = {
        "source_id": "22222222-2222-4222-8222-222222222222",
        "source_content_hash": "sha256:source",
        "source_domain": "project",
        "source_sensitivity": "private",
        "source_title": "  Connector\u00a0framing.\u001c",
        "source_created_at": "2026-07-24T12:00:00Z",
        "source_session_date": "2026-07-24",
        "source_provenance_role": "user",
        "source_project_scope": ["alice"],
        "source_chunk_id": "33333333-3333-4333-8333-333333333333",
        "chunk_index": 0,
        "chunk_text": "Neutral chunk.",
    }
    postgres_digest = postgres_occurrences._extraction_snapshot_sha256(chunk)
    sqlite_digest = sqlite_occurrences._extraction_snapshot_sha256(chunk)
    assert postgres_digest == sqlite_digest

    formatting_only = {
        **chunk,
        "source_title": "Connector framing",
    }
    assert postgres_occurrences._extraction_snapshot_sha256(formatting_only) == postgres_digest
    assert sqlite_occurrences._extraction_snapshot_sha256(formatting_only) == sqlite_digest

    changed = {
        **chunk,
        "source_title": "Different connector framing",
    }
    assert postgres_occurrences._extraction_snapshot_sha256(changed) != postgres_digest
    assert sqlite_occurrences._extraction_snapshot_sha256(changed) != sqlite_digest


def test_sqlite_disposition_record_rejects_stale_expected_source_snapshot(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "occurrence-snapshot-cas.sqlite3"
    owner_conn = sqlite3.connect(database_path)
    bootstrap_sqlite_schema(owner_conn)
    user_id = str(uuid4())
    ensure_sqlite_user(owner_conn, user_id, f"{user_id}@example.com", "Snapshot CAS")
    store = SQLiteVNextStore(owner_conn, user_id)
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "source_created_at": "2026-07-24T12:00:00Z",
            "title": "I published a release",
            "domain": "project",
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
    owner_conn.commit()
    observed = store.get_source_chunk_for_occurrence_accounting(str(chunk["id"]))
    assert observed is not None
    stale_snapshot = str(observed["snapshot_sha256"])

    concurrent_conn = sqlite3.connect(database_path)
    try:
        updated = concurrent_conn.execute(
            "UPDATE sources SET title = ? WHERE user_id = ? AND id = ?",
            ("Different title", user_id, str(source["id"])),
        )
        assert updated.rowcount == 1
        concurrent_conn.commit()
    finally:
        concurrent_conn.close()

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="snapshot CAS is stale",
    ):
        store.record_occurrence_extraction_disposition(
            source_chunk_id=str(chunk["id"]),
            extractor_version="phase6-title-cas-v1",
            expected_snapshot_sha256=stale_snapshot,
            disposition="no_occurrence",
            metadata_json={"raw_no_occurrence_guard": False},
        )
    persisted_count = owner_conn.execute(
        """
        SELECT COUNT(*)
        FROM occurrence_extraction_dispositions
        WHERE user_id = ? AND source_chunk_id = ?
        """,
        (user_id, str(chunk["id"])),
    ).fetchone()
    assert persisted_count == (0,)

    current = store.get_source_chunk_for_occurrence_accounting(str(chunk["id"]))
    assert current is not None
    assert current["snapshot_sha256"] != stale_snapshot
    recorded, created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-title-cas-v1",
        expected_snapshot_sha256=str(current["snapshot_sha256"]),
        disposition="no_occurrence",
        metadata_json={"raw_no_occurrence_guard": True},
    )
    assert created is True
    assert recorded["snapshot_sha256"] == current["snapshot_sha256"]
    owner_conn.close()


def test_sqlite_source_mutations_revoke_signed_complete_coverage() -> None:
    store = _store()
    _qualify_complete_coverage(store)
    signed = store.get_occurrence_coverage()
    assert signed is not None
    assert signed["review_version"] == 1

    source_payload = {
        "source_type": "conversation",
        "content_hash": f"sha256:{uuid4()}",
        "source_created_at": "2050-02-01T00:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "metadata_json": {
            "project_scope": ["alice"],
            "raw_payload": {"text": "I visited the Louvre last December."},
        },
    }
    source, created = store.get_or_create_source(source_payload)
    assert created is True
    invalidated = store.get_occurrence_coverage()
    assert invalidated is not None
    assert invalidated["coverage_mode"] == "forward_only"
    assert invalidated["historical_review_status"] == "not_reviewed"
    assert invalidated["complete_through"] is None
    assert invalidated["reviewed_at"] is None
    assert invalidated["reviewer_id"] is None
    assert invalidated["review_reason"] is None
    assert invalidated["review_receipt_digest"] is None
    assert invalidated["review_version"] == 2

    signed_again_accounting = _prepare_complete_accounting(store)
    signed_again = store.review_occurrence_coverage(
        coverage_mode="complete_history",
        historical_review_status="reviewed",
        complete_through="2051-01-01T00:00:00Z",
        reviewer_id="reviewer",
        reason="Requalified after source import.",
        accounting_metadata=signed_again_accounting,
        expected_review_version=2,
    )
    replay, replay_created = store.get_or_create_source(source_payload)
    assert replay_created is False
    assert replay["id"] == source["id"]
    assert store.get_occurrence_coverage()["review_version"] == signed_again["review_version"]

    store.update_source(source_id=str(source["id"]), patch={"title": None})
    assert store.get_occurrence_coverage()["review_version"] == signed_again["review_version"]
    store.update_source(
        source_id=str(source["id"]),
        patch={"title": "Late historical report"},
    )
    changed = store.get_occurrence_coverage()
    assert changed["coverage_mode"] == "forward_only"
    assert changed["review_version"] == signed_again["review_version"] + 1

    requalified_accounting = _prepare_complete_accounting(store)
    requalified = store.review_occurrence_coverage(
        coverage_mode="complete_history",
        historical_review_status="reviewed",
        complete_through="2051-01-01T00:00:00Z",
        reviewer_id="reviewer",
        reason="Requalified after source edit.",
        accounting_metadata=requalified_accounting,
        expected_review_version=int(changed["review_version"]),
    )
    store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 1,
            "text": "I visited the Louvre last December.",
        }
    )
    chunk_invalidated = store.get_occurrence_coverage()
    assert chunk_invalidated["coverage_mode"] == "forward_only"
    assert chunk_invalidated["review_version"] == requalified["review_version"] + 1


def test_sqlite_session_date_change_stales_extraction_until_rereview() -> None:
    store = _store()
    extractor_version = "phase6-reference-date-v1"
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "source_created_at": "2026-01-01T00:00:00Z",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "project_scope": ["alice"],
                "provenance_role": "user",
                "session_date": "2026-07-24",
            },
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Neutral source text without an occurrence assertion.",
        }
    )
    disposition, _ = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version=extractor_version,
        disposition="no_occurrence",
    )
    disposition = store.review_occurrence_extraction_disposition(
        disposition_id=str(disposition["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The neutral chunk was exhaustively reviewed.",
        expected_review_version=int(disposition["review_version"]),
    )
    original_summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
        source_ids=[str(source["id"])],
    )
    assert original_summary["complete"] is True
    accounting_metadata = {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": extractor_version,
        "source_ids": original_summary["source_ids"],
        "source_chunk_ids": original_summary["source_chunk_ids"],
        "snapshot_digest": original_summary["snapshot_digest"],
        "disposition_digest": original_summary["disposition_digest"],
    }
    coverage = store.ensure_occurrence_coverage(started_at="2020-01-01T00:00:00Z")
    coverage = store.review_occurrence_coverage(
        coverage_mode="complete_history",
        historical_review_status="reviewed",
        complete_through="2030-01-01T00:00:00Z",
        reviewer_id="reviewer",
        reason="The initial source date and extraction were reviewed.",
        accounting_metadata=accounting_metadata,
        expected_review_version=int(coverage["review_version"]),
    )
    assert coverage["coverage_mode"] == "complete_history"

    store.update_source(
        source_id=str(source["id"]),
        patch={
            "metadata_json": {
                "project_scope": ["alice"],
                "provenance_role": "user",
                "session_date": "2026-07-25",
            }
        },
    )
    stale = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
        source_ids=[str(source["id"])],
    )
    assert stale["complete"] is False
    assert stale["stale_count"] == 1
    invalidated = store.get_occurrence_coverage()
    assert invalidated is not None
    assert invalidated["coverage_mode"] == "forward_only"
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="current complete corpus",
    ):
        store.review_occurrence_coverage(
            coverage_mode="complete_history",
            historical_review_status="reviewed",
            complete_through="2030-01-01T00:00:00Z",
            reviewer_id="reviewer",
            reason="A metadata-only date change cannot reuse stale extraction.",
            accounting_metadata=accounting_metadata,
            expected_review_version=int(invalidated["review_version"]),
        )

    replacement, created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version=extractor_version,
        disposition="no_occurrence",
    )
    assert created is True
    assert replacement["id"] != disposition["id"]
    assert replacement["review_status"] == "candidate"
    replacement = store.review_occurrence_extraction_disposition(
        disposition_id=str(replacement["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The changed source reference date was re-extracted and reviewed.",
        expected_review_version=int(replacement["review_version"]),
    )
    assert replacement["review_status"] == "accepted"
    refreshed = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
        source_ids=[str(source["id"])],
    )
    assert refreshed["complete"] is True
    assert refreshed["snapshot_digest"] != original_summary["snapshot_digest"]


def test_sqlite_title_change_stales_extraction_until_rereview() -> None:
    store = _store()
    extractor_version = "phase6-source-title-v1"
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "source_created_at": "2026-07-24T12:00:00Z",
            "title": "Connector framing",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {
                "project_scope": ["alice"],
                "provenance_role": "user",
            },
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Neutral source text without an occurrence assertion.",
        }
    )
    disposition, _ = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version=extractor_version,
        disposition="no_occurrence",
    )
    disposition = store.review_occurrence_extraction_disposition(
        disposition_id=str(disposition["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The titled neutral chunk was exhaustively reviewed.",
        expected_review_version=int(disposition["review_version"]),
    )
    original_summary = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
        source_ids=[str(source["id"])],
    )
    assert original_summary["complete"] is True

    updated = store.conn.execute(
        """
        UPDATE sources
        SET title = ?
        WHERE user_id = ?
          AND id = ?
        """,
        ("Different connector framing", store.user_id, str(source["id"])),
    )
    assert updated.rowcount == 1
    stale = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
        source_ids=[str(source["id"])],
    )
    assert stale["complete"] is False
    assert stale["stale_count"] == 1
    assert stale["snapshot_digest"] != original_summary["snapshot_digest"]

    replacement, created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version=extractor_version,
        disposition="no_occurrence",
    )
    assert created is True
    assert replacement["id"] != disposition["id"]
    assert replacement["review_status"] == "candidate"
    replacement = store.review_occurrence_extraction_disposition(
        disposition_id=str(replacement["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The changed source title was re-extracted and reviewed.",
        expected_review_version=int(replacement["review_version"]),
    )
    assert replacement["review_status"] == "accepted"
    refreshed = store.summarize_occurrence_extraction_accounting(
        extractor_version=extractor_version,
        source_ids=[str(source["id"])],
    )
    assert refreshed["complete"] is True
    assert refreshed["snapshot_digest"] != original_summary["snapshot_digest"]


def test_sqlite_direct_unit_lifecycle_revokes_signed_exactness() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="direct-retire", quantity=2))
    units = [
        store.get_or_create_occurrence_unit(
            _unit(
                str(claim["id"]),
                ordinal,
                occurrence_key=f"direct-retire-{ordinal}",
            )
        )[0]
        for ordinal in (1, 2)
    ]
    for ordinal, unit in enumerate(units, start=1):
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key=f"direct-retire-evidence-{ordinal}",
                store=store,
            )
        )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified exact pair.",
    )
    accepted = [
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reason="Verified.",
            reviewer_id="reviewer",
        )
        for unit in units
    ]
    _qualify_complete_coverage(store)
    store.review_occurrence_unit(
        occurrence_id=str(accepted[0]["id"]),
        action="retired",
        reason="The first event was retracted.",
        reviewer_id="reviewer",
        expected_status="accepted",
        expected_review_version=int(accepted[0]["review_version"]),
    )
    coverage = store.get_occurrence_coverage()
    assert coverage["coverage_mode"] == "forward_only"
    assert coverage["historical_review_status"] == "not_reviewed"
    assert coverage["review_receipt_digest"] is None
    assert coverage["review_version"] == 2


def test_sqlite_exact_claim_materialization_guard_and_terminal_release() -> None:
    store = _store()
    short, _ = store.get_or_create_occurrence_claim(_claim(claim_key="short-materialization", quantity=2))
    store.get_or_create_occurrence_unit(_unit(str(short["id"]), 1, occurrence_key="short-unit"))
    with pytest.raises(ContinuityStoreInvariantError, match="resolved-unit"):
        store.review_occurrence_claim(
            claim_id=str(short["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="reviewer",
            reason="Must fail with one of two units missing.",
        )

    gap, _ = store.get_or_create_occurrence_claim(_claim(claim_key="gap-materialization", quantity=2))
    for ordinal in (1, 3):
        store.get_or_create_occurrence_unit(
            _unit(
                str(gap["id"]),
                ordinal,
                occurrence_key=f"gap-unit-{ordinal}",
            )
        )
    with pytest.raises(ContinuityStoreInvariantError, match="resolved-unit"):
        store.review_occurrence_claim(
            claim_id=str(gap["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="reviewer",
            reason="Must fail with a non-dense ordinal set.",
        )

    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="complete-materialization", quantity=2))
    units = [
        store.get_or_create_occurrence_unit(
            _unit(
                str(claim["id"]),
                ordinal,
                occurrence_key=f"complete-unit-{ordinal}",
            )
        )[0]
        for ordinal in (1, 2)
    ]
    for ordinal, unit in enumerate(units, start=1):
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key=f"complete-evidence-{ordinal}",
                store=store,
            )
        )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Dense exact materialization verified.",
    )
    unresolved_args = {
        "count_key": "published release",
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
    }
    assert str(claim["id"]) in {str(row["id"]) for row in store.list_unresolved_occurrence_claims(**unresolved_args)}
    first = store.review_occurrence_unit(
        occurrence_id=str(units[0]["id"]),
        action="accepted",
        reason="Verified first unit.",
        reviewer_id="reviewer",
    )
    assert str(claim["id"]) in {str(row["id"]) for row in store.list_unresolved_occurrence_claims(**unresolved_args)}
    store.review_occurrence_unit(
        occurrence_id=str(units[1]["id"]),
        action="accepted",
        reason="Verified second unit.",
        reviewer_id="reviewer",
    )
    assert str(claim["id"]) not in {
        str(row["id"]) for row in store.list_unresolved_occurrence_claims(**unresolved_args)
    }
    store.review_occurrence_unit(
        occurrence_id=str(first["id"]),
        action="retired",
        reason="One event was later retracted.",
        reviewer_id="reviewer",
        expected_status="accepted",
        expected_review_version=int(first["review_version"]),
    )
    assert str(claim["id"]) not in {
        str(row["id"]) for row in store.list_unresolved_occurrence_claims(**unresolved_args)
    }


def test_sqlite_claim_and_unit_inputs_enforce_count_key_and_utc_intervals() -> None:
    store = _store()
    for index, bad_key in enumerate((" published release", "published release ", "ｐｕｂｌｉｓｈｅｄ release")):
        payload = _claim(claim_key=f"bad-key-{index}")
        payload["count_key"] = bad_key
        with pytest.raises(ValueError, match="already be canonical"):
            store.get_or_create_occurrence_claim(payload)

    malformed = _claim(claim_key="malformed-claim")
    malformed["occurred_at_start"] = "not-a-timestamp"
    with pytest.raises(ValueError, match="ISO-8601"):
        store.get_or_create_occurrence_claim(malformed)

    reversed_claim = _claim(claim_key="reversed-fraction-claim")
    reversed_claim["occurred_at_start"] = "2026-01-01T00:00:00.500000Z"
    reversed_claim["occurred_at_end"] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="must not precede"):
        store.get_or_create_occurrence_claim(reversed_claim)

    date_claim = _claim(claim_key="date-only-claim")
    date_claim["occurred_at_start"] = "2026-01-01"
    date_claim["occurred_at_end"] = "2026-01-01T00:00:00.500000Z"
    claim, _ = store.get_or_create_occurrence_claim(date_claim)
    assert claim["occurred_at_start"] == "2026-01-01T00:00:00.000000Z"
    assert claim["occurred_at_end"] == "2026-01-01T00:00:00.500000Z"

    for index, bad_key in enumerate((" published release", "published release ", "ｐｕｂｌｉｓｈｅｄ release")):
        payload = _unit(
            str(claim["id"]),
            index + 1,
            occurrence_key=f"bad-unit-key-{index}",
        )
        payload["count_key"] = bad_key
        with pytest.raises(ValueError, match="already be canonical"):
            store.get_or_create_occurrence_unit(payload)

    malformed_unit = _unit(
        str(claim["id"]),
        1,
        occurrence_key="malformed-unit-time",
    )
    malformed_unit["occurred_at_start"] = "not-a-timestamp"
    with pytest.raises(ValueError, match="ISO-8601"):
        store.get_or_create_occurrence_unit(malformed_unit)

    reversed_unit = _unit(
        str(claim["id"]),
        1,
        occurrence_key="reversed-unit-time",
    )
    reversed_unit["occurred_at_start"] = "2026-01-01T00:00:00.500000Z"
    reversed_unit["occurred_at_end"] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValueError, match="must not precede"):
        store.get_or_create_occurrence_unit(reversed_unit)

    valid_unit = _unit(
        str(claim["id"]),
        1,
        occurrence_key="fixed-width-unit-time",
    )
    valid_unit["occurred_at_start"] = "2026-01-01"
    valid_unit["occurred_at_end"] = "2026-01-01T00:00:00.500000+00:00"
    unit, _ = store.get_or_create_occurrence_unit(valid_unit)
    assert unit["occurred_at_start"] == "2026-01-01T00:00:00.000000Z"
    assert unit["occurred_at_end"] == "2026-01-01T00:00:00.500000Z"

    assert (
        sqlite_occurrences._normalized_occurrence_timestamp(
            "2026-01-01",
            field="occurred_at_start",
        )
        == postgres_occurrences._normalized_occurrence_timestamp(
            "2026-01-01",
            field="occurred_at_start",
        )
        == "2026-01-01T00:00:00.000000Z"
    )


def test_sqlite_disposition_revision_supports_mixed_then_complete_chunk() -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "I published two independently identified releases.",
        }
    )
    accepted_claim, accepted_unit = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="mixed-accepted",
        evidence_rows=[
            {
                "evidence_key": "mixed-accepted-evidence",
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
            }
        ],
    )
    pending_claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="mixed-pending"))
    pending_unit, _ = store.get_or_create_occurrence_unit(
        _unit(
            str(pending_claim["id"]),
            1,
            occurrence_key="mixed-pending-unit",
        )
    )
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(pending_claim["id"]),
                str(pending_unit["id"]),
                evidence_key="mixed-pending-evidence",
            ),
            "source_id": source["id"],
            "source_chunk_id": chunk["id"],
        }
    )
    mixed, created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-test-v1",
        disposition="unresolved_claims",
        predicate_keys=["published release"],
        claim_ids=[
            str(accepted_claim["id"]),
            str(pending_claim["id"]),
        ],
        occurrence_ids=[str(accepted_unit["id"])],
    )
    assert created is True
    assert mixed["review_status"] == "candidate"
    mixed_summary = store.summarize_occurrence_extraction_accounting(
        extractor_version="phase6-test-v1",
        source_ids=[str(source["id"])],
    )
    assert mixed_summary["complete"] is False
    assert mixed_summary["unresolved_count"] == 1

    store.review_occurrence_claim(
        claim_id=str(pending_claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Second event verified.",
    )
    pending_accepted = store.review_occurrence_unit(
        occurrence_id=str(pending_unit["id"]),
        action="accepted",
        reason="Second event verified.",
        reviewer_id="reviewer",
    )
    complete, complete_created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-test-v1",
        disposition="accepted_occurrences",
        predicate_keys=["published release"],
        claim_ids=[
            str(accepted_claim["id"]),
            str(pending_claim["id"]),
        ],
        occurrence_ids=[
            str(accepted_unit["id"]),
            str(pending_accepted["id"]),
        ],
    )
    assert complete_created is False
    assert complete["id"] == mixed["id"]
    assert complete["review_status"] == "candidate"
    assert int(complete["review_version"]) == int(mixed["review_version"]) + 1
    reviewed = store.review_occurrence_extraction_disposition(
        disposition_id=str(complete["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The complete chunk accounting was verified.",
        expected_review_version=int(complete["review_version"]),
    )
    assert reviewed["review_status"] == "accepted"
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version="phase6-test-v1",
        source_ids=[str(source["id"])],
    )
    assert summary["complete"] is True
    assert summary["reviewed_current_count"] == 1

    store.invalidate_occurrence_extraction_dispositions(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-test-v1",
        reason="A later lifecycle correction changed the chunk facts.",
    )
    invalidated = store.summarize_occurrence_extraction_accounting(
        extractor_version="phase6-test-v1",
        source_ids=[str(source["id"])],
    )
    assert invalidated["complete"] is False
    assert invalidated["unreviewed_count"] == 1


def test_sqlite_disposition_invalidation_can_defer_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Neutral source text.",
        }
    )
    disposition, _created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-deferred-coverage-v1",
        disposition="no_occurrence",
    )
    reviewed = store.review_occurrence_extraction_disposition(
        disposition_id=str(disposition["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The neutral chunk was exhaustively reviewed.",
        expected_review_version=int(disposition["review_version"]),
    )
    coverage_writes: list[str] = []
    monkeypatch.setattr(
        sqlite_occurrence_accounting,
        "invalidate_occurrence_coverage",
        lambda *_args, **_kwargs: coverage_writes.append("coverage"),
    )

    invalidated = store.invalidate_occurrence_extraction_dispositions(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-deferred-coverage-v1",
        reason="A bundled reset will invalidate coverage once at the end.",
        _defer_occurrence_coverage=True,
    )

    assert [str(row["id"]) for row in invalidated] == [str(reviewed["id"])]
    assert invalidated[0]["review_status"] == "candidate"
    assert coverage_writes == []


def test_sqlite_reviewed_unresolved_disposition_completes_extraction_not_exact_count() -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "I published another release, but its identity is unresolved.",
        }
    )
    accepted_claim, accepted_unit = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="reviewed-unresolved-accepted",
        evidence_rows=[
            {
                "evidence_key": "reviewed-unresolved-accepted-evidence",
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
            }
        ],
    )
    pending_payload = _claim(
        claim_key="reviewed-unresolved-extraction",
        identity_basis="ambiguous",
        resolution_decision="ambiguous",
    )
    pending, _ = store.get_or_create_occurrence_claim(pending_payload)
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(pending["id"]),
                None,
                evidence_key="reviewed-unresolved-extraction-evidence",
            ),
            "source_id": source["id"],
            "source_chunk_id": chunk["id"],
        }
    )
    disposition, created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-reviewed-unresolved-v1",
        disposition="unresolved_claims",
        predicate_keys=["published release"],
        claim_ids=[str(accepted_claim["id"]), str(pending["id"])],
        occurrence_ids=[str(accepted_unit["id"])],
    )
    assert created is True

    reviewed = store.review_occurrence_extraction_disposition(
        disposition_id=str(disposition["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The chunk was exhaustively extracted; occurrence identity remains unresolved.",
        expected_review_version=int(disposition["review_version"]),
    )
    summary = store.summarize_occurrence_extraction_accounting(
        extractor_version="phase6-reviewed-unresolved-v1",
        source_ids=[str(source["id"])],
    )
    preserved_claim = store.get_occurrence_claim(str(pending["id"]))

    assert reviewed["review_status"] == "accepted"
    assert reviewed["review_receipt_digest"] is not None
    assert summary["complete"] is True
    assert summary["reviewed_current_count"] == 1
    assert summary["unresolved_count"] == 1
    assert summary["items"][0]["status"] == "complete_with_unresolved_claims"
    assert preserved_claim is not None
    assert preserved_claim["resolution_status"] == "pending"
    assert preserved_claim["review_status"] == "candidate"

    _qualify_complete_coverage(store)
    pack = VNextRetrievalService(store).compile_context_pack(
        VNextRetrievalRequest(
            query="How many times did I publish a release?",
            projects=("alice",),
            domains=("project",),
            reference_time=datetime(2026, 8, 1, tzinfo=UTC),
        )
    )
    assert pack["aggregation"]["answer_kind"] == "range"
    assert pack["aggregation"]["exact"] is False
    assert pack["aggregation"]["lower_bound"] == 1
    assert pack["aggregation"]["upper_bound"] == 2
    assert "count" not in pack["aggregation"]


def test_sqlite_disposition_review_requires_current_unit_bound_evidence() -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "I published one release.",
        }
    )
    claim, accepted = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="disposition-evidence-receipt",
        evidence_rows=[
            {
                "evidence_key": "reviewed-chunk-evidence",
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
            }
        ],
    )
    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(claim["id"]),
                str(accepted["id"]),
                evidence_key="late-candidate-chunk-evidence",
            ),
            "source_id": source["id"],
            "source_chunk_id": chunk["id"],
        }
    )
    disposition, _ = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-test-v1",
        disposition="accepted_occurrences",
        predicate_keys=["published release"],
        claim_ids=[str(claim["id"])],
        occurrence_ids=[str(accepted["id"])],
    )
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="not bound to the current reviewed occurrence",
    ):
        store.review_occurrence_extraction_disposition(
            disposition_id=str(disposition["id"]),
            action="accepted",
            reviewer_id="reviewer",
            reason="Candidate evidence must not be silently signed.",
            expected_review_version=int(disposition["review_version"]),
        )

    refreshed = store.refresh_occurrence_unit_evidence(
        occurrence_id=str(accepted["id"]),
        reviewer_id="reviewer",
        reason="Review and bind the newly attached evidence.",
        expected_review_version=int(accepted["review_version"]),
    )
    assert refreshed["review_version"] == int(accepted["review_version"]) + 1
    reviewed = store.review_occurrence_extraction_disposition(
        disposition_id=str(disposition["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="All current chunk evidence now shares the unit receipt.",
        expected_review_version=int(disposition["review_version"]),
    )
    assert reviewed["review_status"] == "accepted"

    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(claim["id"]),
                str(accepted["id"]),
                evidence_key="late-candidate-chunk-evidence",
            ),
            "source_id": source["id"],
            "source_chunk_id": chunk["id"],
        }
    )
    replay_preserved = store.summarize_occurrence_extraction_accounting(
        extractor_version="phase6-test-v1",
        source_ids=[str(source["id"])],
    )
    assert replay_preserved["complete"] is True
    assert replay_preserved["reviewed_current_count"] == 1
    assert replay_preserved["unreviewed_count"] == 0

    store.create_occurrence_evidence(
        {
            **_quote_evidence(
                str(claim["id"]),
                str(accepted["id"]),
                evidence_key="post-review-candidate-chunk-evidence",
            ),
            "source_id": source["id"],
            "source_chunk_id": chunk["id"],
        }
    )
    invalidated = store.summarize_occurrence_extraction_accounting(
        extractor_version="phase6-test-v1",
        source_ids=[str(source["id"])],
    )
    assert invalidated["complete"] is False
    assert invalidated["reviewed_current_count"] == 0
    assert invalidated["unreviewed_count"] == 1


@pytest.mark.parametrize("tampered_row", ["unit", "evidence"])
def test_sqlite_disposition_reconstructs_full_review_receipt_chain(
    tampered_row: str,
) -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "I published one release.",
        }
    )
    claim, unit = _accepted_unit_with_carrier_evidence(
        store,
        claim_key=f"receipt-chain-{tampered_row}",
        evidence_rows=[
            {
                "evidence_key": f"receipt-chain-{tampered_row}-evidence",
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
            }
        ],
    )
    if tampered_row == "unit":
        store.conn.execute(
            """
            UPDATE occurrence_units
            SET canonical_text = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                "Tampered accepted unit text.",
                store.user_id,
                str(unit["id"]),
            ),
        )
    else:
        store.conn.execute(
            """
            UPDATE occurrence_evidence
            SET evidence_key = ?
            WHERE user_id = ?
              AND occurrence_id = ?
              AND source_chunk_id = ?
            """,
            (
                f"tampered-receipt-chain-{uuid4()}",
                store.user_id,
                str(unit["id"]),
                str(chunk["id"]),
            ),
        )
    disposition, _created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version=f"phase6-receipt-chain-{tampered_row}-v1",
        disposition="accepted_occurrences",
        predicate_keys=["published release"],
        claim_ids=[str(claim["id"])],
        occurrence_ids=[str(unit["id"])],
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="review receipt|reviewed occurrence",
    ):
        store.review_occurrence_extraction_disposition(
            disposition_id=str(disposition["id"]),
            action="accepted",
            reviewer_id="reviewer",
            reason="Persisted receipt pointers cannot replace reconstruction.",
            expected_review_version=int(disposition["review_version"]),
        )
    preserved = store.conn.execute(
        """
        SELECT review_status, review_receipt_digest
        FROM occurrence_extraction_dispositions
        WHERE user_id = ? AND id = ?
        """,
        (store.user_id, str(disposition["id"])),
    ).fetchone()
    assert preserved == ("candidate", None)


def test_sqlite_disposition_review_rejects_metadata_changed_after_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Neutral heading without an occurrence assertion.",
        }
    )
    disposition, _ = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-cas-test-v1",
        disposition="no_occurrence",
        metadata_json={"raw_no_occurrence_guard": False},
    )
    original_validate = sqlite_occurrence_accounting._validate_extraction_references

    def mutate_metadata_after_validation(
        candidate_store: SQLiteVNextStore,
        **kwargs: Any,
    ) -> None:
        original_validate(candidate_store, **kwargs)
        candidate_store.conn.execute(
            """
            UPDATE occurrence_extraction_dispositions
            SET metadata_json = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                json.dumps(
                    {"raw_no_occurrence_guard": True},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                candidate_store.user_id,
                str(disposition["id"]),
            ),
        )

    monkeypatch.setattr(
        sqlite_occurrence_accounting,
        "_validate_extraction_references",
        mutate_metadata_after_validation,
    )
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="lost its lifecycle CAS",
    ):
        store.review_occurrence_extraction_disposition(
            disposition_id=str(disposition["id"]),
            action="accepted",
            reviewer_id="reviewer",
            reason="This stale review must not sign changed accounting facts.",
            expected_review_version=int(disposition["review_version"]),
        )

    preserved, created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-cas-test-v1",
        disposition="no_occurrence",
        metadata_json={"raw_no_occurrence_guard": True},
    )
    assert created is False
    assert preserved["review_status"] == "candidate"
    assert preserved["review_receipt_digest"] is None
    assert preserved["metadata_json"] == {
        "claim_facts_digests": {},
        "memory_facts_digests": {},
        "raw_no_occurrence_guard": True,
    }


def test_sqlite_disposition_rebinds_changed_source_memory_before_requalification() -> None:
    """A fresh coverage receipt cannot bless a stale no-occurrence decision."""

    store = _store()
    source = store.create_source(
        {
            "source_type": "conversation",
            "content_hash": f"sha256:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Neutral planning context.",
        }
    )
    memory = store.create_memory(
        {
            "memory_key": "neutral-source-memory",
            "value": {"text": "The release notes are ready."},
            "status": "active",
            "canonical_text": "The release notes are ready.",
            "domain": "project",
            "sensitivity": "private",
            "project_id": "alice",
            "metadata_json": {
                "project_scope": ["alice"],
                "source_chunk_id": str(chunk["id"]),
            },
        }
    )
    disposition, _ = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-memory-facts-v1",
        disposition="no_occurrence",
    )
    memory_facts = disposition["metadata_json"]["memory_facts_digests"]
    assert set(memory_facts) == {str(memory["id"])}
    reviewed = store.review_occurrence_extraction_disposition(
        disposition_id=str(disposition["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The neutral source memory was reviewed.",
        expected_review_version=int(disposition["review_version"]),
    )
    assert (
        store.summarize_occurrence_extraction_accounting(
            extractor_version="phase6-memory-facts-v1",
            source_ids=[str(source["id"])],
        )["complete"]
        is True
    )

    # Bypass application invalidation to prove read-time receipt
    # reconstruction still detects an old disposition.
    store.conn.execute(
        """
        UPDATE memories
        SET canonical_text = ?,
            value = ?
        WHERE user_id = ? AND id = ?
        """,
        (
            "I published another release.",
            json.dumps(
                {"text": "I published another release."},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            store.user_id,
            str(memory["id"]),
        ),
    )
    stale = store.summarize_occurrence_extraction_accounting(
        extractor_version="phase6-memory-facts-v1",
        source_ids=[str(source["id"])],
    )
    assert stale["complete"] is False
    assert stale["invalid_receipt_count"] == 1

    replacement, created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="phase6-memory-facts-v1",
        disposition="no_occurrence",
    )
    assert created is False
    assert replacement["id"] == reviewed["id"]
    assert replacement["review_status"] == "candidate"
    assert replacement["metadata_json"]["memory_facts_digests"][str(memory["id"])] != memory_facts[str(memory["id"])]
    store.review_occurrence_extraction_disposition(
        disposition_id=str(replacement["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The changed source memory was re-extracted and reviewed.",
        expected_review_version=int(replacement["review_version"]),
    )
    assert (
        store.summarize_occurrence_extraction_accounting(
            extractor_version="phase6-memory-facts-v1",
            source_ids=[str(source["id"])],
        )["complete"]
        is True
    )


def test_sqlite_supersession_rejects_unrelated_successor() -> None:
    store = _store()
    _first_claim, first = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="superseded-release",
        evidence_rows=[{"evidence_key": "superseded-release-evidence"}],
    )

    successor_claim_payload = _claim(claim_key="unrelated-successor")
    successor_claim_payload["count_key"] = "visited museum"
    successor_claim_payload["canonical_text"] = "Visited one museum."
    successor_claim, _ = store.get_or_create_occurrence_claim(successor_claim_payload)
    successor_unit_payload = _unit(
        str(successor_claim["id"]),
        1,
        occurrence_key="unrelated-successor-unit",
    )
    successor_unit_payload["count_key"] = "visited museum"
    successor_unit_payload["canonical_text"] = "Visited one museum."
    successor, _ = store.get_or_create_occurrence_unit(successor_unit_payload)
    store.create_occurrence_evidence(
        _quote_evidence(
            str(successor_claim["id"]),
            str(successor["id"]),
            evidence_key="unrelated-successor-evidence",
            store=store,
        )
    )
    store.review_occurrence_claim(
        claim_id=str(successor_claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="The museum visit was independently verified.",
    )
    successor = store.review_occurrence_unit(
        occurrence_id=str(successor["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The museum visit evidence was verified.",
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="lifecycle guard",
    ):
        store.review_occurrence_unit(
            occurrence_id=str(first["id"]),
            action="superseded",
            expected_status="accepted",
            expected_review_version=int(first["review_version"]),
            superseded_by=str(successor["id"]),
            reviewer_id="reviewer",
            reason="An unrelated predicate cannot supersede this occurrence.",
        )


def test_sqlite_supersession_accepts_distinct_same_semantics_and_rejects_basis_change() -> None:
    store = _store()
    _first_claim, first = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="supersession-predecessor",
        evidence_rows=[{"evidence_key": "supersession-predecessor-evidence"}],
    )
    _compatible_claim, compatible = _accepted_unit_with_carrier_evidence(
        store,
        claim_key="supersession-compatible",
        evidence_rows=[{"evidence_key": "supersession-compatible-evidence"}],
    )
    assert compatible["occurrence_key"] != first["occurrence_key"]
    assert compatible["aggregation_json"] != first["aggregation_json"]

    incompatible_claim_payload = _claim(claim_key="supersession-object-basis")
    incompatible_claim_payload["aggregation_json"] = _claim_object_aggregation()
    incompatible_claim, _ = store.get_or_create_occurrence_claim(incompatible_claim_payload)
    incompatible_key = "supersession-object-basis-occurrence"
    incompatible_unit_payload = _unit(
        str(incompatible_claim["id"]),
        1,
        occurrence_key=incompatible_key,
    )
    incompatible_unit_payload["aggregation_json"] = _unit_object_aggregation(incompatible_key)
    incompatible, _ = store.get_or_create_occurrence_unit(incompatible_unit_payload)
    store.create_occurrence_evidence(
        _quote_evidence(
            str(incompatible_claim["id"]),
            str(incompatible["id"]),
            evidence_key="supersession-object-basis-evidence",
            store=store,
        )
    )
    store.review_occurrence_claim(
        claim_id=str(incompatible_claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="The object-projected occurrence was verified.",
    )
    incompatible = store.review_occurrence_unit(
        occurrence_id=str(incompatible["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The object-projected occurrence evidence was verified.",
    )

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="lifecycle guard",
    ):
        store.review_occurrence_unit(
            occurrence_id=str(first["id"]),
            action="superseded",
            expected_status="accepted",
            expected_review_version=int(first["review_version"]),
            superseded_by=str(incompatible["id"]),
            reviewer_id="reviewer",
            reason="A changed aggregation basis cannot supersede the occurrence.",
        )
    preserved = store.get_occurrence_unit_by_key(str(first["occurrence_key"]))
    assert preserved is not None
    assert preserved["review_status"] == "accepted"

    superseded = store.review_occurrence_unit(
        occurrence_id=str(first["id"]),
        action="superseded",
        expected_status="accepted",
        expected_review_version=int(first["review_version"]),
        superseded_by=str(compatible["id"]),
        reviewer_id="reviewer",
        reason="A newer unit with the same signed semantics replaces this one.",
    )
    assert superseded["review_status"] == "superseded"
    assert superseded["superseded_by"] == compatible["id"]
    receipt_reason = "A newer unit with the same signed semantics replaces this one."
    expected_receipt = sqlite_occurrences.occurrence_unit_review_receipt_digest(
        {**first, "superseded_by": compatible["id"]},
        action="superseded",
        reviewer_id="reviewer",
        reason=receipt_reason,
        review_version=int(superseded["review_version"]),
        evidence_digest=str(superseded["reviewed_evidence_digest"]),
    )
    swapped_receipt = sqlite_occurrences.occurrence_unit_review_receipt_digest(
        {**first, "superseded_by": incompatible["id"]},
        action="superseded",
        reviewer_id="reviewer",
        reason=receipt_reason,
        review_version=int(superseded["review_version"]),
        evidence_digest=str(superseded["reviewed_evidence_digest"]),
    )
    assert superseded["review_receipt_digest"] == expected_receipt
    assert superseded["review_receipt_digest"] != swapped_receipt


def test_sqlite_evidence_keyset_pages_more_than_sqlite_variable_limit() -> None:
    store = _store()
    claim, _ = store.get_or_create_occurrence_claim(_claim(claim_key="large-evidence-page"))
    unit, _ = store.get_or_create_occurrence_unit(
        _unit(
            str(claim["id"]),
            1,
            occurrence_key="large-evidence-page-unit",
        )
    )
    for index in range(1001):
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key=f"large-evidence-{index:04d}",
                store=store,
            )
        )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Large evidence set verified.",
    )
    accepted = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reason="Large evidence set verified.",
        reviewer_id="reviewer",
    )
    seen: list[str] = []
    after_id: str | None = None
    while True:
        page = store.list_occurrence_evidence_for_units(
            [str(accepted["id"])],
            after_id=after_id,
            limit=1000,
        )
        assert len(page) <= 200
        seen.extend(str(row["id"]) for row in page)
        if len(page) < 200:
            break
        after_id = str(page[-1]["id"])
    assert len(seen) == 1001
    assert len(set(seen)) == 1001
    assert seen == sorted(seen)


def test_postgres_snapshot_capacity_exhaustion_does_not_connect(
    monkeypatch,
) -> None:
    parent = _PostgresSnapshotConnection([{"current_setting": "11111111-1111-4111-8111-111111111111"}])

    class _ExhaustedSemaphore:
        def acquire(self, *, blocking: bool) -> bool:
            assert blocking is False
            return False

        def release(self) -> None:
            raise AssertionError("an unacquired slot must not be released")

    monkeypatch.setattr(
        postgres_occurrences,
        "_OCCURRENCE_SNAPSHOT_SLOTS",
        _ExhaustedSemaphore(),
    )
    monkeypatch.setattr(
        postgres_occurrences.psycopg,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("capacity rejection must happen before connect"),
    )
    store = type("SnapshotStore", (), {"conn": parent})()
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="capacity is exhausted",
    ):
        postgres_occurrences.begin_occurrence_read_snapshot(store)
    assert store.conn is parent


def test_postgres_extraction_scope_sql_is_interpolated() -> None:
    store = _PostgresShapeStore()
    postgres_occurrences._current_extraction_chunk(
        store,
        "00000000-0000-0000-0000-000000000001",
    )
    sql, _params = store.queries[-1]
    assert "{_OCCURRENCE_SOURCE_SCOPE_SQL}" not in sql
    assert "metadata_json -> 'project_scope'" in sql


def test_exact_count_key_search_is_canonical_and_pre_limit() -> None:
    store = _store()
    for index, count_key in enumerate(("published release", "published article")):
        claim_payload = _claim(claim_key=f"exact-search-{index}")
        claim_payload["count_key"] = count_key
        claim_payload["canonical_text"] = f"{count_key} once"
        claim, _ = store.get_or_create_occurrence_claim(claim_payload)
        unit_payload = _unit(
            str(claim["id"]),
            1,
            occurrence_key=f"exact-search-unit-{index}",
        )
        unit_payload["count_key"] = count_key
        unit_payload["canonical_text"] = f"{count_key} once"
        unit, _ = store.get_or_create_occurrence_unit(unit_payload)
        store.create_occurrence_evidence(
            _quote_evidence(
                str(claim["id"]),
                str(unit["id"]),
                evidence_key=f"exact-search-evidence-{index}",
                store=store,
            )
        )
        store.review_occurrence_claim(
            claim_id=str(claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="reviewer",
            reason="Verified.",
        )
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reason="Verified.",
            reviewer_id="reviewer",
        )
    found = store.search_accepted_occurrence_units(
        query="published",
        exact_count_key="published release",
        projects=["alice"],
        domains=["project"],
        sensitivity_allowed=["private"],
        limit=1,
    )
    assert [row["count_key"] for row in found] == ["published release"]
    with pytest.raises(ValueError, match="already be canonical"):
        store.search_accepted_occurrence_units(
            query="published",
            exact_count_key=" Published Release ",
            projects=["alice"],
            domains=["project"],
            sensitivity_allowed=["private"],
        )


def test_coverage_receipt_uses_fixed_microsecond_canonical_payload() -> None:
    payload = {
        "coverage_id": "00000000-0000-0000-0000-000000000001",
        "user_id": "11111111-1111-4111-8111-111111111111",
        "review_version": 1,
        "coverage_mode": "complete_history",
        "coverage_started_at": "2026-01-01T00:00:00Z",
        "historical_review_status": "reviewed",
        "complete_through": "2026-12-31T23:59:59Z",
        "reviewer_id": "reviewer",
        "reason": "Complete reviewed history.",
        "accounting_metadata": _accounting_metadata(),
    }
    canonical = {
        "accounting_metadata": _accounting_metadata(),
        "complete_through": "2026-12-31T23:59:59.000000Z",
        "coverage_id": payload["coverage_id"],
        "coverage_mode": payload["coverage_mode"],
        "coverage_started_at": "2026-01-01T00:00:00.000000Z",
        "historical_review_status": payload["historical_review_status"],
        "reason": payload["reason"],
        "review_version": payload["review_version"],
        "reviewer_id": payload["reviewer_id"],
        "user_id": payload["user_id"],
    }
    expected = hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert postgres_occurrences._coverage_receipt_digest(**payload) == expected
    assert sqlite_occurrences._coverage_receipt_digest(**payload) == expected


def test_extraction_review_receipt_canonically_signs_metadata_on_both_backends() -> None:
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "user_id": "11111111-1111-4111-8111-111111111111",
        "source_id": "22222222-2222-4222-8222-222222222222",
        "source_chunk_id": "33333333-3333-4333-8333-333333333333",
        "snapshot_sha256": "a" * 64,
        "extractor_version": "phase6-receipt-v1",
        "disposition": "no_occurrence",
        "predicate_keys": [],
        "claim_ids": [],
        "occurrence_ids": [],
        "metadata_json": {
            "raw_no_occurrence_guard": False,
            "nested": {"b": 2, "a": 1},
        },
    }
    kwargs = {
        "action": "accepted",
        "reviewer_id": "reviewer",
        "reason": "The accounting facts were reviewed.",
        "review_version": 1,
    }
    postgres_digest = postgres_occurrences._extraction_review_receipt_digest(
        row,
        **kwargs,
    )
    sqlite_digest = sqlite_occurrences._extraction_review_receipt_digest(
        row,
        **kwargs,
    )
    assert postgres_digest == sqlite_digest

    reordered = {
        **row,
        "metadata_json": {
            "nested": {"a": 1, "b": 2},
            "raw_no_occurrence_guard": False,
        },
    }
    assert (
        postgres_occurrences._extraction_review_receipt_digest(
            reordered,
            **kwargs,
        )
        == postgres_digest
    )
    tampered = {
        **row,
        "metadata_json": {
            "raw_no_occurrence_guard": True,
            "nested": {"a": 1, "b": 2},
        },
    }
    assert (
        postgres_occurrences._extraction_review_receipt_digest(
            tampered,
            **kwargs,
        )
        != postgres_digest
    )
    assert (
        sqlite_occurrences._extraction_review_receipt_digest(
            tampered,
            **kwargs,
        )
        != sqlite_digest
    )
