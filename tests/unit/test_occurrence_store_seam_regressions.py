from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
from types import ModuleType, SimpleNamespace
from uuid import uuid4

import pytest

from alicebot_api.sqlite_schema import bootstrap_sqlite_schema
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user
from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api import onramp, vnext_occurrence_write
from alicebot_api.vnext_occurrence_predicates import (
    occurrence_evidence_facts_digest,
    occurrence_evidence_review_receipt_digest,
    occurrence_unit_review_receipt_digest,
)
from alicebot_api.vnext_store import PostgresVNextStore
from alicebot_api.vnext_stores.postgres import (
    memory_lifecycle as postgres_memory_lifecycle,
)
from alicebot_api.vnext_stores.postgres import (
    occurrence_accounting as postgres_occurrence_accounting,
)
from alicebot_api.vnext_stores.postgres import occurrences as postgres_occurrences
from alicebot_api.vnext_stores.sqlite import (
    memory_lifecycle as sqlite_memory_lifecycle,
)
from alicebot_api.vnext_stores.sqlite import (
    occurrence_accounting as sqlite_occurrence_accounting,
)
from alicebot_api.vnext_stores.sqlite import occurrences as sqlite_occurrences


_CANONICAL_COUNT_KEY = "published release"
_START = "2026-07-24T12:00:00Z"
_END = "2026-07-24T13:00:00Z"
_OCCURRENCE_HELPERS: tuple[ModuleType, ...] = (
    sqlite_occurrences,
    postgres_occurrences,
)


def test_extraction_snapshot_binds_normalized_reference_and_provenance() -> None:
    base: dict[str, object] = {
        "source_id": "11111111-1111-4111-8111-111111111111",
        "source_content_hash": "sha256:source",
        "source_domain": "project",
        "source_sensitivity": "private",
        "source_project_scope": ["alice"],
        "source_created_at": "2026-01-01T00:00:00Z",
        "source_session_date": "2026-07-24",
        "source_provenance_role": "User",
        "source_chunk_id": "22222222-2222-4222-8222-222222222222",
        "chunk_index": 0,
        "chunk_text": "I visited the museum yesterday.",
    }
    sqlite_digest = sqlite_occurrences._extraction_snapshot_sha256(base)
    postgres_digest = postgres_occurrences._extraction_snapshot_sha256(base)
    assert sqlite_digest == postgres_digest

    equivalent = {
        **base,
        "source_session_date": "2026-07-24T00:00:00+00:00",
        "source_provenance_role": "USER",
    }
    assert sqlite_occurrences._extraction_snapshot_sha256(equivalent) == sqlite_digest
    assert postgres_occurrences._extraction_snapshot_sha256(equivalent) == postgres_digest

    offset_same_local_day = {
        **base,
        "source_session_date": "2026-07-24T23:30:00-07:00",
    }
    assert sqlite_occurrences._extraction_snapshot_sha256(offset_same_local_day) == sqlite_digest
    assert postgres_occurrences._extraction_snapshot_sha256(offset_same_local_day) == postgres_digest

    for changed in (
        {**base, "source_session_date": "2026-07-25"},
        {
            **base,
            "source_session_date": "2026-07-25T00:30:00+14:00",
        },
        {**base, "source_provenance_role": "assistant"},
        {**base, "source_session_date": None},
        {**base, "source_created_at": "2026-01-02T00:00:00Z"},
    ):
        assert sqlite_occurrences._extraction_snapshot_sha256(changed) != sqlite_digest
        assert postgres_occurrences._extraction_snapshot_sha256(changed) != postgres_digest


@pytest.mark.parametrize(
    ("facade", "carrier", "compatibility_module", "module_name"),
    [
        (
            SQLiteVNextStore,
            sqlite_occurrence_accounting,
            sqlite_occurrences,
            "alicebot_api.vnext_stores.sqlite.occurrence_accounting",
        ),
        (
            PostgresVNextStore,
            postgres_occurrence_accounting,
            postgres_occurrences,
            "alicebot_api.vnext_stores.postgres.occurrence_accounting",
        ),
    ],
)
def test_occurrence_accounting_facades_resolve_to_extracted_modules(
    facade: type[object],
    carrier: ModuleType,
    compatibility_module: ModuleType,
    module_name: str,
) -> None:
    for name in (
        "record_occurrence_extraction_disposition",
        "review_occurrence_extraction_disposition",
        "summarize_occurrence_extraction_accounting",
        "list_occurrence_evidence_for_units",
    ):
        implementation = getattr(carrier, name)
        assert implementation.__module__ == module_name
        assert getattr(compatibility_module, name) is implementation
        assert getattr(facade, name) is implementation


@pytest.mark.parametrize(
    "carrier",
    [sqlite_occurrence_accounting, postgres_occurrence_accounting],
    ids=["sqlite", "postgres"],
)
def test_occurrence_metadata_chunk_refs_cover_anchor_and_proposal(
    carrier: ModuleType,
) -> None:
    anchor_id = "11111111-1111-4111-8111-111111111111"
    proposal_id = "22222222-2222-4222-8222-222222222222"
    assert carrier._occurrence_metadata_source_chunk_ids(
        {
            "source_chunk_id": anchor_id,
            "occurrence_proposal": {"source_chunk_id": proposal_id},
        }
    ) == (anchor_id, proposal_id)
    writer_source = inspect.getsource(carrier.write_occurrence_memory_metadata)
    assert "_defer_occurrence_coverage=True" in writer_source
    assert writer_source.count("invalidate_occurrence_coverage(") == 1


def test_sqlite_occurrence_metadata_write_invalidates_top_level_chunk_accounting_once() -> None:
    store = _store()
    source = store.create_source(
        {
            "source_type": "note",
            "content_hash": f"top-level-accounting:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
        }
    )
    chunk = store.create_source_chunk(
        {
            "source_id": source["id"],
            "chunk_index": 0,
            "text": "Administrative status only.",
        }
    )
    memory = store.create_memory(
        {
            "memory_key": f"top-level-accounting:{uuid4()}",
            "value": {"status": "administrative"},
            "status": "active",
            "canonical_text": "Administrative status only.",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"source_chunk_id": str(chunk["id"])},
        }
    )
    disposition, _created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(chunk["id"]),
        extractor_version="top-level-accounting-v1",
        disposition="no_occurrence",
    )
    store.review_occurrence_extraction_disposition(
        disposition_id=str(disposition["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="The administrative chunk has no countable assertion.",
        expected_review_version=int(disposition["review_version"]),
    )
    coverage = store.ensure_occurrence_coverage(
        started_at="2026-01-01T00:00:00Z",
    )
    coverage = store.review_occurrence_coverage(
        coverage_mode="partial_history",
        historical_review_status="reviewed",
        coverage_started_at="2026-01-01T00:00:00Z",
        complete_through="2026-07-24T23:59:59Z",
        reviewer_id="reviewer",
        reason="The top-level accounting fixture was reviewed.",
        expected_review_version=int(coverage["review_version"]),
    )
    signed_version = int(coverage["review_version"])
    metadata = dict(memory["metadata_json"])
    metadata["occurrence_invalidation"] = {"reason": "test"}

    store.write_occurrence_memory_metadata(
        memory_id=str(memory["id"]),
        metadata_json=metadata,
        expected_metadata_json=dict(memory["metadata_json"]),
        actor_type="user",
        actor_id="reviewer",
    )

    persisted_disposition = store.conn.execute(
        """
        SELECT review_status
        FROM occurrence_extraction_dispositions
        WHERE user_id = ? AND id = ?
        """,
        (store.user_id, str(disposition["id"])),
    ).fetchone()
    assert persisted_disposition == ("candidate",)
    invalidated_coverage = store.get_occurrence_coverage()
    assert invalidated_coverage is not None
    assert int(invalidated_coverage["review_version"]) == signed_version + 1
    assert invalidated_coverage["review_receipt_digest"] is None


def test_source_envelope_lock_takes_graph_boundary_before_backend_row_lock() -> None:
    source_id = "11111111-1111-4111-8111-111111111111"

    for lock_source, row_lock in (
        (
            postgres_occurrence_accounting.lock_source_occurrence_envelope,
            lambda events: SimpleNamespace(
                lock_graph_mutation=lambda: events.append("graph"),
                _fetch_optional_one=lambda _sql, _params: events.append("source-row")
                or {"id": source_id},
                get_source=lambda _source_id: events.append("read") or {"id": source_id},
            ),
        ),
        (
            sqlite_occurrence_accounting.lock_source_occurrence_envelope,
            lambda events: SimpleNamespace(
                conn=SimpleNamespace(in_transaction=True),
                user_id="22222222-2222-4222-8222-222222222222",
                lock_graph_mutation=lambda: events.append("graph"),
                _execute=lambda _sql, _params: events.append("source-row")
                or SimpleNamespace(rowcount=1),
                get_source=lambda _source_id: events.append("read") or {"id": source_id},
            ),
        ),
    ):
        events: list[str] = []
        assert lock_source(row_lock(events), source_id) == {"id": source_id}
        assert events == ["graph", "source-row", "read"]


_OCCURRENCE_MUTATION_SEAMS = (
    "ensure_occurrence_coverage",
    "invalidate_occurrence_coverage",
    "review_occurrence_coverage",
    "get_or_create_occurrence_claim",
    "review_occurrence_claim",
    "get_or_create_occurrence_unit",
    "create_occurrence_evidence",
    "review_occurrence_unit",
    "reconcile_occurrence_evidence_carrier",
    "reconcile_occurrence_claim_evidence",
    "redact_occurrence_memory_content",
)
_ACCOUNTING_MUTATION_SEAMS = (
    "lock_source_occurrence_envelope",
    "write_occurrence_memory_metadata",
    "reestablish_source_occurrence_unit",
    "invalidate_occurrence_extraction_dispositions",
    "record_occurrence_extraction_disposition",
    "review_occurrence_extraction_disposition",
)
_OCCURRENCE_WRITE_ENTRYPOINTS = (
    "reconcile_chunk_extraction_disposition",
    "establish_memory_occurrences",
    "establish_source_chunk_occurrences",
    "review_source_chunk_occurrences",
    "retire_memory_occurrences",
    "retire_source_occurrences",
    "transfer_consolidated_occurrence_evidence",
)


def _assert_lock_precedes_storage_access(
    implementation: object,
    *,
    lock_expression: str,
) -> None:
    source = inspect.getsource(implementation)
    lock_offset = source.find(lock_expression)
    assert lock_offset >= 0, f"{implementation!r} lost {lock_expression}"
    access_offsets = [
        offset
        for marker in (
            "self._fetch",
            "self._execute",
            "self._get_row",
            "self.get_",
            "self.conn",
            "_lock_occurrence_claim_rows(",
            "_lock_occurrence_unit_rows(",
            "_lock_occurrence_memory_carrier(",
        )
        if (offset := source.find(marker)) >= 0
    ]
    assert access_offsets, f"{implementation!r} has no pinned storage access"
    assert lock_offset < min(access_offsets), f"{implementation!r} accesses storage before the graph boundary"


@pytest.mark.parametrize(
    "carrier",
    [sqlite_occurrences, postgres_occurrences],
    ids=["sqlite", "postgres"],
)
def test_every_occurrence_mutation_seam_enters_graph_boundary_first(
    carrier: ModuleType,
) -> None:
    for name in _OCCURRENCE_MUTATION_SEAMS:
        _assert_lock_precedes_storage_access(
            getattr(carrier, name),
            lock_expression="_lock_occurrence_graph_mutation(self)",
        )


@pytest.mark.parametrize(
    "carrier",
    [sqlite_occurrence_accounting, postgres_occurrence_accounting],
    ids=["sqlite", "postgres"],
)
def test_every_occurrence_accounting_mutation_seam_enters_graph_boundary_first(
    carrier: ModuleType,
) -> None:
    for name in _ACCOUNTING_MUTATION_SEAMS:
        _assert_lock_precedes_storage_access(
            getattr(carrier, name),
            lock_expression="_lock_occurrence_graph_mutation(self)",
        )


@pytest.mark.parametrize(
    "carrier",
    [sqlite_memory_lifecycle, postgres_memory_lifecycle],
    ids=["sqlite", "postgres"],
)
@pytest.mark.parametrize(
    "name",
    [
        "create_memory",
        "get_memory_for_update",
        "get_memory_for_redaction",
        "update_memory",
        "redact_memory_bundle",
        "redact_memory_content",
    ],
)
def test_every_memory_carrier_mutation_or_lock_seam_enters_graph_boundary_first(
    carrier: ModuleType,
    name: str,
) -> None:
    _assert_lock_precedes_storage_access(
        getattr(carrier, name),
        lock_expression="self.lock_graph_mutation()",
    )


@pytest.mark.parametrize(
    ("facade", "names"),
    [
        (
            SQLiteVNextStore,
            ("create_source", "get_or_create_source", "update_source", "create_source_chunk"),
        ),
        (
            PostgresVNextStore,
            (
                "create_source",
                "get_or_create_source",
                "update_source",
                "delete_source",
                "create_source_chunk",
            ),
        ),
    ],
    ids=["sqlite", "postgres"],
)
def test_every_source_carrier_mutation_enters_graph_boundary_first(
    facade: type[object],
    names: tuple[str, ...],
) -> None:
    for name in names:
        _assert_lock_precedes_storage_access(
            getattr(facade, name),
            lock_expression="self.lock_graph_mutation()",
        )


def test_artifact_authorization_lock_enters_graph_boundary_before_row_lock() -> None:
    _assert_lock_precedes_storage_access(
        PostgresVNextStore.get_artifact_for_update,
        lock_expression="self.lock_graph_mutation()",
    )
    assert "FOR UPDATE" in inspect.getsource(PostgresVNextStore.get_artifact_for_update)


def test_occurrence_write_entrypoint_manifest_enters_graph_boundary_before_reads() -> None:
    for name in _OCCURRENCE_WRITE_ENTRYPOINTS:
        source = inspect.getsource(getattr(vnext_occurrence_write, name))
        boundary = source.find("_lock_occurrence_write_graph(store)")
        assert boundary >= 0, f"{name} lost the bundled graph boundary"
        first_graph_read = min(
            offset
            for marker in ("typed_store =", "_metadata(", "store.list_", "store.get_")
            if (offset := source.find(marker)) >= 0
        )
        assert boundary < first_graph_read, f"{name} reads the occurrence graph before locking"


def test_backend_graph_lock_implementations_are_transaction_scoped() -> None:
    postgres_source = inspect.getsource(postgres_memory_lifecycle.lock_graph_mutation)
    assert "pg_advisory_xact_lock" in postgres_source

    sqlite_source = inspect.getsource(sqlite_memory_lifecycle.lock_graph_mutation)
    assert "BEGIN IMMEDIATE" in sqlite_source
    assert "UPDATE users" in sqlite_source
    assert sqlite_source.index("BEGIN IMMEDIATE") < sqlite_source.index("UPDATE users")


def test_sqlite_merge_import_locks_graph_before_reviewed_snapshot_reads() -> None:
    source = inspect.getsource(onramp._run_import_snapshot)
    boundary = source.index("store.lock_graph_mutation()")
    assert boundary < source.index("_reviewed_extraction_chunk_ids(")
    assert boundary < source.index("_import_records(")


@pytest.mark.parametrize(
    ("facade", "carrier", "module_name"),
    [
        (
            SQLiteVNextStore,
            sqlite_occurrences,
            "alicebot_api.sqlite_store",
        ),
        (
            PostgresVNextStore,
            postgres_occurrences,
            "alicebot_api.vnext_store",
        ),
    ],
)
def test_all_accepted_occurrence_unit_seam_is_exposed_by_both_facades(
    facade: type[object],
    carrier: ModuleType,
    module_name: str,
) -> None:
    implementation = carrier.list_accepted_occurrence_units
    assert implementation.__module__ == module_name
    assert getattr(facade, "list_accepted_occurrence_units") is implementation


@pytest.mark.parametrize(
    "carrier",
    [sqlite_occurrence_accounting, postgres_occurrence_accounting],
)
def test_extraction_receipt_chain_reconstruction_is_backend_identical(
    carrier: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = "11111111-1111-4111-8111-111111111111"
    claim_id = "22222222-2222-4222-8222-222222222222"
    unit_id = "33333333-3333-4333-8333-333333333333"
    evidence_id = "44444444-4444-4444-8444-444444444444"
    occurrence_key = "receipt-chain-unit"
    reviewer = "reviewer"
    reason = "Current unit and evidence facts were verified."
    unit: dict[str, object] = {
        "id": unit_id,
        "user_id": user_id,
        "claim_id": claim_id,
        "claim_ordinal": 1,
        "occurrence_key": occurrence_key,
        "count_key": _CANONICAL_COUNT_KEY,
        "canonical_text": "Published one release.",
        "unit_value": 1,
        "identity_status": "resolved",
        "ambiguity_group_key": None,
        "predicate_json": _predicate(),
        "aggregation_json": _unit_aggregation(occurrence_key),
        "occurred_at_start": _START,
        "occurred_at_end": _END,
        "domain": "project",
        "sensitivity": "private",
        "project_scope": ["alice"],
        "review_status": "accepted",
        "review_version": 1,
        "review_receipt_action": "accepted",
        "reviewer_id": reviewer,
        "review_reason": reason,
    }
    quote = "I published one release."
    evidence: dict[str, object] = {
        "id": evidence_id,
        "user_id": user_id,
        "claim_id": claim_id,
        "occurrence_id": unit_id,
        "evidence_key": "receipt-chain-evidence",
        "evidence_role": "supports",
        "memory_id": None,
        "source_id": "55555555-5555-4555-8555-555555555555",
        "source_chunk_id": "66666666-6666-4666-8666-666666666666",
        "quote": quote,
        "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "review_status": "accepted",
        "review_receipt_action": "accepted",
        "reviewer_id": reviewer,
        "review_reason": reason,
    }
    evidence_digest = hashlib.sha256(occurrence_evidence_facts_digest(evidence).encode("utf-8")).hexdigest()
    unit.update(
        {
            "reviewed_evidence_count": 1,
            "reviewed_evidence_digest": evidence_digest,
        }
    )
    unit_receipt = occurrence_unit_review_receipt_digest(
        unit,
        action="accepted",
        reviewer_id=reviewer,
        reason=reason,
        review_version=1,
        evidence_digest=evidence_digest,
    )
    unit["review_receipt_digest"] = unit_receipt
    evidence["unit_review_receipt_digest"] = unit_receipt
    evidence["review_receipt_digest"] = occurrence_evidence_review_receipt_digest(
        evidence,
        action="accepted",
        reviewer_id=reviewer,
        reason=reason,
        unit_review_receipt_digest=unit_receipt,
    )

    class ReceiptStore:
        def __init__(self) -> None:
            self.user_id = user_id

        def _fetch_optional_one(
            self,
            _query: str,
            _params: tuple[object, ...] = (),
        ) -> dict[str, object]:
            return dict(unit)

    monkeypatch.setattr(
        carrier,
        "_current_reviewed_supporting_evidence",
        lambda _store, _occurrence_id: [dict(evidence)],
    )
    carrier._require_current_reviewed_extraction_evidence(
        ReceiptStore(),
        [{"evidence_id": evidence_id, "occurrence_id": unit_id}],
        occurrence_ids=[unit_id],
    )
    unit["canonical_text"] = "Tampered accepted unit."
    with pytest.raises(
        ContinuityStoreInvariantError,
        match="unit review receipt is stale",
    ):
        carrier._require_current_reviewed_extraction_evidence(
            ReceiptStore(),
            [{"evidence_id": evidence_id, "occurrence_id": unit_id}],
            occurrence_ids=[unit_id],
        )


@pytest.mark.parametrize(
    "review",
    [
        sqlite_occurrences.review_occurrence_claim,
        postgres_occurrences.review_occurrence_claim,
    ],
)
@pytest.mark.parametrize(
    ("reviewer_id", "reason"),
    [("", "verified"), ("reviewer", "   "), ("   ", "")],
)
def test_claim_review_rejects_empty_reviewer_or_reason_before_store_access(
    review,
    reviewer_id: str,
    reason: str,
) -> None:
    with pytest.raises(ValueError, match="requires reviewer_id and reason"):
        review(
            object(),
            claim_id="11111111-1111-4111-8111-111111111111",
            resolution_status="rejected",
            resolution_decision="ambiguous",
            identity_basis="ambiguous",
            reviewer_id=reviewer_id,
            reason=reason,
        )


@pytest.mark.parametrize(
    "review",
    [
        sqlite_occurrences.review_occurrence_unit,
        postgres_occurrences.review_occurrence_unit,
    ],
)
@pytest.mark.parametrize(
    ("reviewer_id", "reason"),
    [("", "verified"), ("reviewer", "   "), ("   ", "")],
)
def test_unit_review_rejects_empty_reviewer_or_reason_before_store_access(
    review,
    reviewer_id: str,
    reason: str,
) -> None:
    with pytest.raises(ValueError, match="requires reviewer_id and reason"):
        review(
            object(),
            occurrence_id="11111111-1111-4111-8111-111111111111",
            action="rejected",
            reviewer_id=reviewer_id,
            reason=reason,
        )


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


def _object_claim_aggregation() -> dict[str, object]:
    return {
        "schema": "occurrence_aggregation_v1",
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
    }


def _object_unit_aggregation(
    occurrence_key: str,
    object_ids: tuple[str, ...],
) -> dict[str, object]:
    return {
        "schema": "occurrence_aggregation_v1",
        "members": [
            {
                "basis": "event_instance",
                "identity_basis": "occurrence_key",
                "member_identity": occurrence_key,
            },
            *[
                {
                    "basis": "object_member",
                    "identity_basis": "reviewed_stable_object_v1",
                    "member_identity": object_id,
                }
                for object_id in object_ids
            ],
        ],
    }


def _store() -> SQLiteVNextStore:
    conn = sqlite3.connect(":memory:")
    bootstrap_sqlite_schema(conn)
    user_id = str(uuid4())
    ensure_sqlite_user(
        conn,
        user_id,
        f"{user_id}@example.com",
        "Occurrence Seam Regression",
    )
    return SQLiteVNextStore(conn, user_id)


def _claim(
    *,
    claim_key: str,
    quantity: int = 1,
    count_key: str = _CANONICAL_COUNT_KEY,
    occurred_at_start: object | None = _START,
    occurred_at_end: object | None = _END,
) -> dict[str, object]:
    return {
        "claim_key": claim_key,
        "count_key": count_key,
        "predicate_json": _predicate(),
        "canonical_text": f"Published {quantity} releases",
        "quantity_min": quantity,
        "quantity_max": quantity,
        "range_kind": "exact",
        "resolution_decision": "new",
        "identity_basis": "exact_time",
        "aggregation_json": _claim_aggregation(),
        "occurred_at_start": occurred_at_start,
        "occurred_at_end": occurred_at_end,
        "domain": "project",
        "sensitivity": "private",
        "project_scope": ["alice"],
    }


def _unit(
    claim_id: str,
    *,
    ordinal: int = 1,
    count_key: str = _CANONICAL_COUNT_KEY,
    occurred_at_start: object | None = _START,
    occurred_at_end: object | None = _END,
) -> dict[str, object]:
    occurrence_key = f"occurrence-{uuid4()}"
    return {
        "claim_id": claim_id,
        "claim_ordinal": ordinal,
        "occurrence_key": occurrence_key,
        "count_key": count_key,
        "predicate_json": _predicate(),
        "canonical_text": f"Published release {ordinal}",
        "identity_status": "resolved",
        "aggregation_json": _unit_aggregation(occurrence_key),
        "occurred_at_start": occurred_at_start,
        "occurred_at_end": occurred_at_end,
        "domain": "project",
        "sensitivity": "private",
        "project_scope": ["alice"],
    }


def _create_parent_claim(store: SQLiteVNextStore) -> dict[str, object]:
    return store.get_or_create_occurrence_claim(
        _claim(claim_key=f"parent-{uuid4()}"),
    )[0]


def _persist_temporal_subject(
    subject: str,
    *,
    occurred_at_start: object | None,
    occurred_at_end: object | None,
) -> dict[str, object]:
    store = _store()
    if subject == "claim":
        return store.get_or_create_occurrence_claim(
            _claim(
                claim_key=f"temporal-{uuid4()}",
                occurred_at_start=occurred_at_start,
                occurred_at_end=occurred_at_end,
            )
        )[0]
    claim = _create_parent_claim(store)
    return store.get_or_create_occurrence_unit(
        _unit(
            str(claim["id"]),
            occurred_at_start=occurred_at_start,
            occurred_at_end=occurred_at_end,
        )
    )[0]


@pytest.mark.parametrize(
    ("quantity_min", "quantity_max", "range_kind"),
    [
        (2, 2, "exact"),
        (1, 2, "bounded"),
        (1, None, "at_least"),
    ],
)
def test_object_projection_claim_requires_one_exact_event(
    quantity_min: int,
    quantity_max: int | None,
    range_kind: str,
) -> None:
    store = _store()
    payload = _claim(
        claim_key=f"invalid-object-projection-{range_kind}",
        quantity=quantity_min,
    )
    payload.update(
        {
            "quantity_max": quantity_max,
            "range_kind": range_kind,
            "aggregation_json": _object_claim_aggregation(),
        }
    )
    with pytest.raises(ValueError, match="one exact event"):
        store.get_or_create_occurrence_claim(payload)


def test_sqlite_object_projection_schema_enforces_canonical_members() -> None:
    store = _store()
    claim_payload = _claim(claim_key="object-projection-exact-one")
    claim_payload["aggregation_json"] = _object_claim_aggregation()
    claim, _created = store.get_or_create_occurrence_claim(claim_payload)
    object_ids = tuple(f"object:v1:{digest * 64}" for digest in ("c", "a", "b"))
    unit_payload = _unit(str(claim["id"]))
    occurrence_key = str(unit_payload["occurrence_key"])
    unit_payload["aggregation_json"] = _object_unit_aggregation(
        occurrence_key,
        object_ids,
    )
    unit, _unit_created = store.get_or_create_occurrence_unit(unit_payload)
    members = unit["aggregation_json"]["members"]
    assert [member["basis"] for member in members] == [
        "event_instance",
        "object_member",
        "object_member",
        "object_member",
    ]
    assert [member["member_identity"] for member in members[1:]] == sorted(object_ids)
    store.conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        store.conn.execute(
            """
            UPDATE occurrence_claims
            SET quantity_min = 2,
                quantity_max = 2
            WHERE id = ?
            """,
            (str(claim["id"]),),
        )

    event_member = members[0]
    first_object = members[1]
    invalid_aggregations = (
        {
            "schema": "occurrence_aggregation_v1",
            "members": [first_object, event_member],
        },
        {
            "schema": "occurrence_aggregation_v1",
            "members": [event_member, first_object, first_object],
        },
        {
            "schema": "occurrence_aggregation_v1",
            "members": [
                event_member,
                {
                    **first_object,
                    "identity_basis": "occurrence_key",
                },
            ],
        },
        {
            "schema": "occurrence_aggregation_v1",
            "members": [
                event_member,
                {
                    **first_object,
                    "member_identity": f"object:v1:{'A' * 64}",
                },
            ],
        },
    )
    for invalid in invalid_aggregations:
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                UPDATE occurrence_units
                SET aggregation_json = ?
                WHERE id = ?
                """,
                (
                    json.dumps(
                        invalid,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    str(unit["id"]),
                ),
            )


@pytest.mark.parametrize(
    ("ordinals", "case"),
    [
        ((1,), "missing-cardinality"),
        ((1, 3), "noncontiguous-ordinals"),
    ],
    ids=lambda value: str(value),
)
def test_sqlite_exact_n_claim_resolution_requires_complete_contiguous_ordinals(
    ordinals: tuple[int, ...],
    case: str,
) -> None:
    store = _store()
    claim, _created = store.get_or_create_occurrence_claim(_claim(claim_key=f"exact-two-{case}", quantity=2))
    for ordinal in ordinals:
        store.get_or_create_occurrence_unit(_unit(str(claim["id"]), ordinal=ordinal))

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="resolved-unit guard",
    ):
        store.review_occurrence_claim(
            claim_id=str(claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="reviewer",
            reason="Verify exact-N materialization.",
        )

    unchanged = store.get_occurrence_claim(str(claim["id"]))
    assert unchanged is not None
    assert unchanged["resolution_status"] == "pending"
    assert unchanged["review_status"] == "candidate"
    assert unchanged["review_version"] == 0


def test_sqlite_partial_accepted_new_claim_blocks_until_remaining_unit_is_terminal() -> None:
    store = _store()
    claim, _created = store.get_or_create_occurrence_claim(_claim(claim_key="partial-accepted-new", quantity=2))
    units = [store.get_or_create_occurrence_unit(_unit(str(claim["id"]), ordinal=ordinal))[0] for ordinal in (1, 2)]
    source = store.create_source(
        {
            "source_type": "note",
            "content_hash": f"partial-accepted-new:{uuid4()}",
            "domain": "project",
            "sensitivity": "private",
            "metadata_json": {"project_scope": ["alice"]},
        }
    )
    store.create_occurrence_evidence(
        {
            "claim_id": claim["id"],
            "occurrence_id": units[0]["id"],
            "source_id": source["id"],
            "evidence_key": "partial-accepted-new-evidence",
            "evidence_role": "supports",
            "quote": "The release was published.",
        }
    )
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="reviewer",
        reason="Verified both proposed identities.",
    )
    store.review_occurrence_unit(
        occurrence_id=str(units[0]["id"]),
        action="accepted",
        reviewer_id="reviewer",
        reason="Verified first occurrence.",
    )

    query = {
        "count_key": _CANONICAL_COUNT_KEY,
        "projects": ["alice"],
        "domains": ["project"],
        "sensitivity_allowed": ["private"],
    }
    blocked = store.list_unresolved_occurrence_claims(**query)
    assert [row["id"] for row in blocked] == [claim["id"]]

    store.review_occurrence_unit(
        occurrence_id=str(units[1]["id"]),
        action="rejected",
        reviewer_id="reviewer",
        reason="Second proposal was not a distinct occurrence.",
    )

    assert store.list_unresolved_occurrence_claims(**query) == []


@pytest.mark.parametrize("subject", ["claim", "unit"])
@pytest.mark.parametrize("field", ["occurred_at_start", "occurred_at_end"])
def test_sqlite_claim_and_unit_reject_malformed_interval_endpoints(
    subject: str,
    field: str,
) -> None:
    values: dict[str, object] = {
        "occurred_at_start": _START,
        "occurred_at_end": _END,
    }
    values[field] = "not-an-iso-date"

    with pytest.raises(
        ValueError,
        match=rf"{field} must be an ISO-8601 date or timestamp",
    ):
        _persist_temporal_subject(
            subject,
            occurred_at_start=values["occurred_at_start"],
            occurred_at_end=values["occurred_at_end"],
        )


@pytest.mark.parametrize("subject", ["claim", "unit"])
@pytest.mark.parametrize(
    ("start", "end", "expected_start", "expected_end"),
    [
        (
            "2026-07-24",
            "2026-07-25",
            "2026-07-24T00:00:00.000000Z",
            "2026-07-25T00:00:00.000000Z",
        ),
        (
            "2026-07-24T14:00:00.123456+02:00",
            "2026-07-24T14:00:00.654321+02:00",
            "2026-07-24T12:00:00.123456Z",
            "2026-07-24T12:00:00.654321Z",
        ),
    ],
    ids=["date-only", "fractional-offset"],
)
def test_sqlite_claim_and_unit_canonicalize_date_and_fractional_intervals(
    subject: str,
    start: str,
    end: str,
    expected_start: str,
    expected_end: str,
) -> None:
    row = _persist_temporal_subject(
        subject,
        occurred_at_start=start,
        occurred_at_end=end,
    )

    assert row["occurred_at_start"] == expected_start
    assert row["occurred_at_end"] == expected_end


@pytest.mark.parametrize("subject", ["claim", "unit"])
def test_sqlite_claim_and_unit_reject_fractional_interval_reversal(
    subject: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="occurred_at_end must not precede occurred_at_start",
    ):
        _persist_temporal_subject(
            subject,
            occurred_at_start="2026-07-24T12:00:00.900000Z",
            occurred_at_end="2026-07-24T12:00:00.100000Z",
        )


@pytest.mark.parametrize(
    "raw_count_key",
    [
        "Ｐｕｂｌｉｓｈｅｄ release",
        " published release ",
        "published  release",
        "published\u00a0release",
        "published\u001crelease",
    ],
    ids=["fullwidth", "outer-space", "internal-space", "nbsp", "u001c"],
)
@pytest.mark.parametrize("subject", ["claim", "unit"])
def test_sqlite_claim_and_unit_reject_raw_noncanonical_count_keys(
    subject: str,
    raw_count_key: str,
) -> None:
    store = _store()

    with pytest.raises(ValueError, match="count_key must already be canonical"):
        if subject == "claim":
            store.get_or_create_occurrence_claim(
                _claim(
                    claim_key=f"noncanonical-{uuid4()}",
                    count_key=raw_count_key,
                )
            )
        else:
            claim = _create_parent_claim(store)
            store.get_or_create_occurrence_unit(
                _unit(
                    str(claim["id"]),
                    count_key=raw_count_key,
                )
            )


@pytest.mark.parametrize("helper_module", _OCCURRENCE_HELPERS)
@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("2026-07-24", "2026-07-24T00:00:00.000000Z"),
        (
            "2026-07-24T14:00:00.123456+02:00",
            "2026-07-24T12:00:00.123456Z",
        ),
    ],
    ids=["date-only", "fractional-offset"],
)
def test_postgres_and_sqlite_timestamp_helpers_are_canonicalization_equivalent(
    helper_module: ModuleType,
    raw_value: str,
    expected: str,
) -> None:
    assert (
        helper_module._normalized_occurrence_timestamp(
            raw_value,
            field="occurred_at_start",
        )
        == expected
    )


@pytest.mark.parametrize("helper_module", _OCCURRENCE_HELPERS)
@pytest.mark.parametrize("field", ["occurred_at_start", "occurred_at_end"])
def test_postgres_and_sqlite_timestamp_helpers_reject_malformed_values_equally(
    helper_module: ModuleType,
    field: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=rf"{field} must be an ISO-8601 date or timestamp",
    ):
        helper_module._normalized_occurrence_timestamp(
            "not-an-iso-date",
            field=field,
        )


@pytest.mark.parametrize("helper_module", _OCCURRENCE_HELPERS)
@pytest.mark.parametrize(
    "raw_count_key",
    [
        "Ｐｕｂｌｉｓｈｅｄ release",
        " published release ",
        "published  release",
        "published\u00a0release",
        "published\u001crelease",
    ],
    ids=["fullwidth", "outer-space", "internal-space", "nbsp", "u001c"],
)
def test_postgres_and_sqlite_count_key_helpers_reject_the_same_noncanonical_inputs(
    helper_module: ModuleType,
    raw_count_key: str,
) -> None:
    with pytest.raises(ValueError, match="count_key must already be canonical"):
        helper_module._canonical_count_key_input(raw_count_key)
