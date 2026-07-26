"""Live PostgreSQL proofs for the Phase 6 occurrence persistence substrate."""

from __future__ import annotations

from contextlib import ExitStack
from datetime import UTC, datetime
import hashlib
import json
from queue import Queue
from threading import Thread
from time import monotonic, sleep
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
import pytest

from alicebot_api.contracts import MemoryCandidateInput
from alicebot_api.db import set_current_user, user_connection
from alicebot_api.memory import admit_memory_candidate
from alicebot_api.store import ContinuityStore, ContinuityStoreInvariantError
from alicebot_api.vnext_capture import SourceCaptureInput, VNextCaptureService
from alicebot_api.vnext_memory_commit import VNextMemoryCommitService
from alicebot_api.vnext_occurrence_write import (
    OCCURRENCE_EXTRACTOR_VERSION,
    establish_source_chunk_occurrences,
    invalidate_occurrence_accounting,
    reconcile_chunk_extraction_disposition,
    review_source_chunk_occurrences,
)
from alicebot_api.vnext_occurrence_predicates import (
    occurrence_unit_review_receipt_digest,
)
from alicebot_api.vnext_retrieval import (
    VNextRetrievalRequest,
    VNextRetrievalService,
)
from alicebot_api.vnext_store import PostgresVNextStore


_OCCURRENCE_TABLES = (
    "occurrence_coverage",
    "occurrence_claims",
    "occurrence_units",
    "occurrence_evidence",
    "occurrence_extraction_dispositions",
)


def _predicate(action: str, object_leaf: str) -> dict[str, object]:
    selector = f"v1|a=exact:{action}|o=exact:{object_leaf}"
    return {
        "schema": "occurrence_predicate_v1",
        "taxonomy": "alice-occurrence-exact-v1",
        "op": "atom",
        "subject": "self",
        "polarity": "completed",
        "action": {"leaf": action, "ancestors": []},
        "object": {
            "leaf": object_leaf,
            "qualifiers": [],
            "ancestors": [],
        },
        "selector_keys": [
            selector,
            f"v1|a=exact:{action}|o=*",
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


def _seed_user(database_url: str, *, label: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"phase6-{label}-{user_id}@example.invalid",
            f"Phase 6 {label}",
        )
    return user_id


def test_occurrence_migration_grants_rls_and_review_lifecycle(
    migrated_database_urls,
) -> None:
    admin_url = migrated_database_urls["admin"]
    app_url = migrated_database_urls["app"]
    app_role = unquote(urlsplit(app_url).username or "")

    with psycopg.connect(admin_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = ANY(%s)
                ORDER BY relname
                """,
                (list(_OCCURRENCE_TABLES),),
            )
            table_security = cur.fetchall()
            cur.execute(
                """
                SELECT tablename, policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = ANY(%s)
                ORDER BY tablename
                """,
                (list(_OCCURRENCE_TABLES),),
            )
            policies = cur.fetchall()
            cur.execute(
                """
                SELECT table_name, privilege_type
                FROM information_schema.role_table_grants
                WHERE grantee = %s
                  AND table_schema = 'public'
                  AND table_name = ANY(%s)
                ORDER BY table_name, privilege_type
                """,
                (app_role, list(_OCCURRENCE_TABLES)),
            )
            grants = cur.fetchall()

    assert {row["relname"] for row in table_security} == set(_OCCURRENCE_TABLES)
    assert all(row["relrowsecurity"] is True and row["relforcerowsecurity"] is True for row in table_security)
    assert {(row["tablename"], row["policyname"]) for row in policies} == {
        (table, f"{table}_is_owner") for table in _OCCURRENCE_TABLES
    }
    grants_by_table = {
        table: {row["privilege_type"] for row in grants if row["table_name"] == table} for table in _OCCURRENCE_TABLES
    }
    assert grants_by_table == {table: {"INSERT", "SELECT", "UPDATE"} for table in _OCCURRENCE_TABLES}

    owner_id = _seed_user(app_url, label="owner")
    intruder_id = _seed_user(app_url, label="intruder")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
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
        claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.claim.{uuid4()}",
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "new",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        occurrence_key = f"phase6.unit.{uuid4()}"
        unit, _ = store.get_or_create_occurrence_unit(
            {
                "claim_id": claim["id"],
                "claim_ordinal": 1,
                "occurrence_key": occurrence_key,
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "identity_status": "resolved",
                "aggregation_json": _unit_aggregation(occurrence_key),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        store.create_occurrence_evidence(
            {
                "claim_id": claim["id"],
                "occurrence_id": unit["id"],
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
                "evidence_key": f"phase6.evidence.{uuid4()}",
                "quote": "I published one release.",
            }
        )
        store.review_occurrence_claim(
            claim_id=str(claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="phase6-reviewer",
            reason="The exact occurrence identity was verified.",
        )
        unit = store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
            reason="The source-backed occurrence was verified.",
        )
        store.create_occurrence_evidence(
            {
                "claim_id": claim["id"],
                "occurrence_id": unit["id"],
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
                "evidence_key": f"phase6.late-evidence.{uuid4()}",
                "quote": "I published one release.",
            }
        )
        disposition, created = store.record_occurrence_extraction_disposition(
            source_chunk_id=str(chunk["id"]),
            extractor_version="phase6-live-pg-v1",
            disposition="accepted_occurrences",
            predicate_keys=["published release"],
            claim_ids=[str(claim["id"])],
            occurrence_ids=[str(unit["id"])],
        )
        assert created is True
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="not bound to the current reviewed occurrence",
        ):
            store.review_occurrence_extraction_disposition(
                disposition_id=str(disposition["id"]),
                action="accepted",
                reviewer_id="phase6-reviewer",
                reason="Candidate evidence must not be silently signed.",
                expected_review_version=int(disposition["review_version"]),
            )
        unit = store.refresh_occurrence_unit_evidence(
            occurrence_id=str(unit["id"]),
            reviewer_id="phase6-reviewer",
            reason="Review and bind the newly attached chunk evidence.",
            expected_review_version=int(unit["review_version"]),
        )
        disposition = store.review_occurrence_extraction_disposition(
            disposition_id=str(disposition["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
            reason="The chunk accounting was verified.",
            expected_review_version=int(disposition["review_version"]),
        )
        accounting = store.summarize_occurrence_extraction_accounting(
            extractor_version="phase6-live-pg-v1",
            source_ids=[str(source["id"])],
        )
        assert accounting["complete"] is True
        accounting_metadata = {
            "accounting_schema": "occurrence_accounting_v1",
            "extractor_version": accounting["extractor_version"],
            "source_ids": accounting["source_ids"],
            "source_chunk_ids": accounting["source_chunk_ids"],
            "snapshot_digest": accounting["snapshot_digest"],
            "disposition_digest": accounting["disposition_digest"],
        }
        coverage = store.ensure_occurrence_coverage(started_at="2026-01-01T00:00:00Z")
        coverage = store.review_occurrence_coverage(
            coverage_mode="complete_history",
            historical_review_status="reviewed",
            coverage_started_at="2026-01-01T00:00:00Z",
            complete_through="2026-07-24T23:59:59Z",
            reviewer_id="phase6-reviewer",
            reason="All owner history and current chunk accounting were reviewed.",
            accounting_metadata=accounting_metadata,
            expected_review_version=int(coverage["review_version"]),
        )
        assert disposition["review_status"] == "accepted"
        assert disposition["review_receipt_digest"] is not None
        assert coverage["coverage_mode"] == "complete_history"
        assert coverage["review_receipt_digest"] is not None

        unrelated_source = store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:unrelated:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        unrelated_chunk = store.create_source_chunk(
            {
                "source_id": unrelated_source["id"],
                "chunk_index": 0,
                "text": "I visited one museum.",
            }
        )
        unrelated_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.unrelated-claim.{uuid4()}",
                "count_key": "visited museum",
                "predicate_json": _predicate("visit", "museum"),
                "canonical_text": "Visited one museum.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "new",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        unrelated_occurrence_key = f"phase6.unrelated-unit.{uuid4()}"
        unrelated_unit, _ = store.get_or_create_occurrence_unit(
            {
                "claim_id": unrelated_claim["id"],
                "claim_ordinal": 1,
                "occurrence_key": unrelated_occurrence_key,
                "count_key": "visited museum",
                "predicate_json": _predicate("visit", "museum"),
                "canonical_text": "Visited one museum.",
                "identity_status": "resolved",
                "aggregation_json": _unit_aggregation(unrelated_occurrence_key),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        store.create_occurrence_evidence(
            {
                "claim_id": unrelated_claim["id"],
                "occurrence_id": unrelated_unit["id"],
                "source_id": unrelated_source["id"],
                "source_chunk_id": unrelated_chunk["id"],
                "evidence_key": f"phase6.unrelated-evidence.{uuid4()}",
                "quote": "I visited one museum.",
            }
        )
        store.review_occurrence_claim(
            claim_id=str(unrelated_claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="phase6-reviewer",
            reason="The unrelated occurrence identity was verified.",
        )
        unrelated_unit = store.review_occurrence_unit(
            occurrence_id=str(unrelated_unit["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
            reason="The unrelated occurrence evidence was verified.",
        )
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="identity/evidence guard",
        ):
            store.review_occurrence_unit(
                occurrence_id=str(unit["id"]),
                action="superseded",
                expected_status="accepted",
                expected_review_version=int(unit["review_version"]),
                superseded_by=str(unrelated_unit["id"]),
                reviewer_id="phase6-reviewer",
                reason="An unrelated predicate cannot supersede this unit.",
            )
        store.create_occurrence_evidence(
            {
                "claim_id": claim["id"],
                "occurrence_id": unit["id"],
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
                "evidence_key": f"phase6.post-review-evidence.{uuid4()}",
                "quote": "I published one release.",
            }
        )
        invalidated = store.summarize_occurrence_extraction_accounting(
            extractor_version="phase6-live-pg-v1",
            source_ids=[str(source["id"])],
        )
        assert invalidated["complete"] is False
        assert invalidated["reviewed_current_count"] == 0
        assert invalidated["unreviewed_count"] == 1

    with user_connection(app_url, intruder_id) as conn:
        intruder_store = PostgresVNextStore(conn)
        assert intruder_store.get_occurrence_coverage() is None
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS count FROM occurrence_extraction_dispositions")
            assert cur.fetchone()["count"] == 0


def test_occurrence_evidence_requires_authorized_claim_and_python_strip_quote(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="evidence-authorization")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:evidence-authorization:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        owner_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.evidence-owner.{uuid4()}",
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "new",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        occurrence_key = f"phase6.evidence-owner-unit.{uuid4()}"
        unit, _ = store.get_or_create_occurrence_unit(
            {
                "claim_id": owner_claim["id"],
                "claim_ordinal": 1,
                "occurrence_key": occurrence_key,
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "identity_status": "resolved",
                "aggregation_json": _unit_aggregation(occurrence_key),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        linked_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.evidence-pending-link.{uuid4()}",
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published the same release.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "link_existing",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )

        for quote in ("\u00a0", "\u001c"):
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO occurrence_evidence (
                              user_id, claim_id, occurrence_id, source_id,
                              evidence_key, evidence_role, quote, quote_sha256
                            ) VALUES (
                              app.current_user_id(), %s::uuid, %s::uuid, %s::uuid,
                              %s, 'supports', %s, %s
                            )
                            """,
                            (
                                linked_claim["id"],
                                unit["id"],
                                source["id"],
                                f"phase6.unicode-blank.{ord(quote)}.{uuid4()}",
                                quote,
                                hashlib.sha256(quote.encode("utf-8")).hexdigest(),
                            ),
                        )

        evidence = store.create_occurrence_evidence(
            {
                "claim_id": linked_claim["id"],
                "occurrence_id": unit["id"],
                "source_id": source["id"],
                "evidence_key": f"phase6.pending-link-evidence.{uuid4()}",
                "quote": "I published one release.",
            }
        )
        store.review_occurrence_claim(
            claim_id=str(owner_claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="phase6-reviewer",
            reason="The owner claim identity was verified.",
        )

        with pytest.raises(
            ContinuityStoreInvariantError,
            match="identity/evidence guard",
        ):
            store.review_occurrence_unit(
                occurrence_id=str(unit["id"]),
                action="accepted",
                reviewer_id="phase6-reviewer",
                reason="An unreviewed cross-claim must not authorize signing.",
            )
        current = store.get_occurrence_unit_by_key(occurrence_key)
        assert current is not None
        assert current["review_status"] == "candidate"
        assert int(current["review_version"]) == 0
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_status, review_receipt_digest,
                       unit_review_receipt_digest
                FROM occurrence_evidence
                WHERE id = %s::uuid
                  AND user_id = app.current_user_id()
                """,
                (evidence["id"],),
            )
            persisted = cur.fetchone()
        assert persisted == {
            "review_status": "candidate",
            "review_receipt_digest": None,
            "unit_review_receipt_digest": None,
        }


def test_occurrence_count_key_and_supersession_invariants(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="count-key-supersession")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:count-key-supersession:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )

        def create_candidate(
            label: str,
            *,
            count_key: str = "published release",
            object_projection: bool = False,
        ) -> tuple[dict[str, object], dict[str, object]]:
            claim, _ = store.get_or_create_occurrence_claim(
                {
                    "claim_key": f"phase6.{label}.claim.{uuid4()}",
                    "count_key": count_key,
                    "predicate_json": _predicate("publish", "release"),
                    "canonical_text": "Published one release.",
                    "quantity_min": 1,
                    "quantity_max": 1,
                    "range_kind": "exact",
                    "resolution_decision": "new",
                    "identity_basis": "exact_time",
                    "aggregation_json": (_claim_object_aggregation() if object_projection else _claim_aggregation()),
                    "occurred_at_start": "2026-07-24T12:00:00Z",
                    "occurred_at_end": "2026-07-24T12:00:00Z",
                    "domain": "project",
                    "sensitivity": "private",
                    "project_scope": ["alice"],
                }
            )
            occurrence_key = f"phase6.{label}.unit.{uuid4()}"
            unit, _ = store.get_or_create_occurrence_unit(
                {
                    "claim_id": claim["id"],
                    "claim_ordinal": 1,
                    "occurrence_key": occurrence_key,
                    "count_key": count_key,
                    "predicate_json": _predicate("publish", "release"),
                    "canonical_text": "Published one release.",
                    "identity_status": "resolved",
                    "aggregation_json": (
                        _unit_object_aggregation(occurrence_key)
                        if object_projection
                        else _unit_aggregation(occurrence_key)
                    ),
                    "occurred_at_start": "2026-07-24T12:00:00Z",
                    "occurred_at_end": "2026-07-24T12:00:00Z",
                    "domain": "project",
                    "sensitivity": "private",
                    "project_scope": ["alice"],
                }
            )
            return claim, unit

        def accept(
            label: str,
            claim: dict[str, object],
            unit: dict[str, object],
        ) -> dict[str, object]:
            store.create_occurrence_evidence(
                {
                    "claim_id": claim["id"],
                    "occurrence_id": unit["id"],
                    "source_id": source["id"],
                    "evidence_key": f"phase6.{label}.evidence.{uuid4()}",
                    "quote": "I published one release.",
                }
            )
            store.review_occurrence_claim(
                claim_id=str(claim["id"]),
                resolution_status="resolved",
                resolution_decision="new",
                identity_basis="exact_time",
                reviewer_id="phase6-reviewer",
                reason="The occurrence identity was verified.",
            )
            return store.review_occurrence_unit(
                occurrence_id=str(unit["id"]),
                action="accepted",
                reviewer_id="phase6-reviewer",
                reason="The occurrence evidence was verified.",
            )

        owner_claim, owner_unit = create_candidate("count-owner")
        mismatch_payload = {
            "claim_id": owner_claim["id"],
            "claim_ordinal": 1,
            "occurrence_key": "phase6.count-mismatch",
            "count_key": "attended conference",
            "predicate_json": _predicate("publish", "release"),
            "canonical_text": "Published one release.",
            "identity_status": "resolved",
            "aggregation_json": _unit_aggregation("phase6.count-mismatch"),
            "occurred_at_start": "2026-07-24T12:00:00Z",
            "occurred_at_end": "2026-07-24T12:00:00Z",
            "domain": "project",
            "sensitivity": "private",
            "project_scope": ["alice"],
        }
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="count_key must match its owning claim",
        ):
            store.get_or_create_occurrence_unit(mismatch_payload)
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE occurrence_units
                        SET count_key = 'attended conference'
                        WHERE id = %s::uuid
                          AND user_id = app.current_user_id()
                        """,
                        (owner_unit["id"],),
                    )
        replay_mismatch = {
            **mismatch_payload,
            "occurrence_key": owner_unit["occurrence_key"],
            "aggregation_json": _unit_aggregation(str(owner_unit["occurrence_key"])),
        }
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="count_key must match its owning claim",
        ):
            store.get_or_create_occurrence_unit(replay_mismatch)
        owner_unit = accept("count-owner", owner_claim, owner_unit)

        link_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.cross-count-link.{uuid4()}",
                "count_key": "attended conference",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published the same release.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "link_existing",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        cross_count_evidence_key = f"phase6.cross-count-evidence.{uuid4()}"
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="mismatched reference",
        ):
            store.create_occurrence_evidence(
                {
                    "claim_id": link_claim["id"],
                    "occurrence_id": owner_unit["id"],
                    "source_id": source["id"],
                    "evidence_key": cross_count_evidence_key,
                    "quote": "This claim belongs to a different count family.",
                }
            )
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM occurrence_evidence
                WHERE user_id = app.current_user_id()
                  AND evidence_key = %s
                """,
                (cross_count_evidence_key,),
            )
            assert cur.fetchone()["count"] == 0
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="resolved-unit guard",
        ):
            store.review_occurrence_claim(
                claim_id=str(link_claim["id"]),
                resolution_status="resolved",
                resolution_decision="link_existing",
                identity_basis="exact_time",
                reviewer_id="phase6-reviewer",
                reason="A claim cannot link across count families.",
                resolved_occurrence_id=str(owner_unit["id"]),
            )

        incompatible_claim, incompatible_unit = create_candidate(
            "basis-incompatible",
            object_projection=True,
        )
        incompatible_unit = accept(
            "basis-incompatible",
            incompatible_claim,
            incompatible_unit,
        )
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="identity/evidence guard",
        ):
            store.review_occurrence_unit(
                occurrence_id=str(owner_unit["id"]),
                action="superseded",
                expected_status="accepted",
                expected_review_version=int(owner_unit["review_version"]),
                superseded_by=str(incompatible_unit["id"]),
                reviewer_id="phase6-reviewer",
                reason="A changed aggregation basis cannot supersede this unit.",
            )

        compatible_claim, compatible_unit = create_candidate("compatible-successor")
        compatible_unit = accept(
            "compatible-successor",
            compatible_claim,
            compatible_unit,
        )
        superseded = store.review_occurrence_unit(
            occurrence_id=str(owner_unit["id"]),
            action="superseded",
            expected_status="accepted",
            expected_review_version=int(owner_unit["review_version"]),
            superseded_by=str(compatible_unit["id"]),
            reviewer_id="phase6-reviewer",
            reason="A newer unit with the same signed semantics replaces this one.",
        )
        assert superseded["review_status"] == "superseded"
        assert superseded["superseded_by"] == compatible_unit["id"]
        receipt_reason = "A newer unit with the same signed semantics replaces this one."
        expected_receipt = occurrence_unit_review_receipt_digest(
            {**owner_unit, "superseded_by": compatible_unit["id"]},
            action="superseded",
            reviewer_id="phase6-reviewer",
            reason=receipt_reason,
            review_version=int(superseded["review_version"]),
            evidence_digest=str(superseded["reviewed_evidence_digest"]),
        )
        swapped_receipt = occurrence_unit_review_receipt_digest(
            {**owner_unit, "superseded_by": incompatible_unit["id"]},
            action="superseded",
            reviewer_id="phase6-reviewer",
            reason=receipt_reason,
            review_version=int(superseded["review_version"]),
            evidence_digest=str(superseded["reviewed_evidence_digest"]),
        )
        assert superseded["review_receipt_digest"] == expected_receipt
        assert superseded["review_receipt_digest"] != swapped_receipt


def test_postgres_carrier_reconciliation_ignores_cross_count_survivor(
    migrated_database_urls,
) -> None:
    """A corrupt cross-count evidence row cannot keep a unit accepted."""

    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="cross-count-survivor")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        owner_source = store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:cross-count-owner:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        survivor_source = store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:cross-count-survivor:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        owner_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.cross-count-owner.{uuid4()}",
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "new",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        occurrence_key = f"phase6.cross-count-owner-unit.{uuid4()}"
        owner_unit, _ = store.get_or_create_occurrence_unit(
            {
                "claim_id": owner_claim["id"],
                "claim_ordinal": 1,
                "occurrence_key": occurrence_key,
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "identity_status": "resolved",
                "aggregation_json": _unit_aggregation(occurrence_key),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        store.create_occurrence_evidence(
            {
                "claim_id": owner_claim["id"],
                "occurrence_id": owner_unit["id"],
                "source_id": owner_source["id"],
                "evidence_key": f"phase6.cross-count-owner-evidence.{uuid4()}",
                "quote": "I published one release.",
            }
        )
        store.review_occurrence_claim(
            claim_id=str(owner_claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="phase6-reviewer",
            reason="The owner occurrence identity was verified.",
        )
        owner_unit = store.review_occurrence_unit(
            occurrence_id=str(owner_unit["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
            reason="The owner occurrence evidence was verified.",
        )

        cross_count_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.cross-count-survivor.{uuid4()}",
                "count_key": "attended conference",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "This belongs to another count family.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "ambiguous",
                "identity_basis": "ambiguous",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        cross_quote = "This carrier belongs to a different count family."
        cross_evidence_id = uuid4()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO occurrence_evidence (
                  id, user_id, claim_id, occurrence_id, source_id,
                  evidence_key, evidence_role, quote, quote_sha256,
                  confidence, review_status, metadata_json
                ) VALUES (
                  %s::uuid, app.current_user_id(), %s::uuid, %s::uuid,
                  %s::uuid, %s, 'supports', %s, %s, 0.5, 'candidate',
                  '{}'::jsonb
                )
                """,
                (
                    cross_evidence_id,
                    cross_count_claim["id"],
                    owner_unit["id"],
                    survivor_source["id"],
                    f"phase6.cross-count-survivor-evidence.{uuid4()}",
                    cross_quote,
                    hashlib.sha256(cross_quote.encode("utf-8")).hexdigest(),
                ),
            )

        outcome = store.reconcile_occurrence_evidence_carrier(
            source_id=str(owner_source["id"]),
            reviewer_id="phase6-reviewer",
            reason="The only compatible carrier was retired.",
        )

        assert len(outcome) == 1
        assert outcome[0]["occurrence_id"] == owner_unit["id"]
        assert outcome[0]["outcome"] == "retired"
        assert outcome[0]["review_status"] == "retired"
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_status
                FROM occurrence_evidence
                WHERE user_id = app.current_user_id()
                  AND id = %s::uuid
                """,
                (cross_evidence_id,),
            )
            assert cur.fetchone()["review_status"] == "candidate"


def test_occurrence_snapshot_is_live_read_only_bounded_and_released(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    user_ids = [uuid4(), uuid4(), uuid4()]

    with ExitStack() as stack:
        connections = [stack.enter_context(user_connection(app_url, user_id)) for user_id in user_ids]
        stores = [PostgresVNextStore(conn) for conn in connections]
        parent_connections = list(connections)
        active_stores: list[PostgresVNextStore] = []
        try:
            for store in stores[:2]:
                proof = store.begin_occurrence_read_snapshot()
                active_stores.append(store)
                assert proof["proof"] == "occurrence_read_snapshot_v1"
                assert proof["mode"] == "repeatable_read_read_only"
                lifecycle_as_of = proof["lifecycle_as_of"]
                assert isinstance(lifecycle_as_of, datetime)
                assert lifecycle_as_of.tzinfo is not None
                assert lifecycle_as_of.tzinfo is UTC
                with store.conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT current_setting('transaction_isolation') AS isolation,
                               current_setting('transaction_read_only') AS read_only,
                               transaction_timestamp() AS lifecycle_as_of
                        """
                    )
                    row = cur.fetchone()
                    assert row == {
                        "isolation": "repeatable read",
                        "read_only": "on",
                        "lifecycle_as_of": lifecycle_as_of,
                    }

            with pytest.raises(
                ContinuityStoreInvariantError,
                match="capacity is exhausted",
            ):
                stores[2].begin_occurrence_read_snapshot()

            snapshot_connection = stores[0].conn
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                with snapshot_connection.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO occurrence_coverage (
                          user_id, coverage_mode, coverage_started_at
                        )
                        VALUES (
                          app.current_user_id(), 'forward_only', clock_timestamp()
                        )
                        """
                    )
            stores[0].end_occurrence_read_snapshot()
            active_stores.remove(stores[0])
            assert stores[0].conn is parent_connections[0]
            assert snapshot_connection.closed is True

            proof = stores[2].begin_occurrence_read_snapshot()
            active_stores.append(stores[2])
            assert proof["acquired"] is True
        finally:
            for store in reversed(active_stores):
                store.end_occurrence_read_snapshot()
            assert all(store.conn is parent for store, parent in zip(stores, parent_connections, strict=True))


def test_disposition_review_rejects_concurrent_candidate_fact_replacement(
    migrated_database_urls,
) -> None:
    """A stale reviewer must never sign a concurrently replaced candidate."""

    admin_url = migrated_database_urls["admin"]
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="disposition-cas")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6-disposition-cas:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
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
        initial, created = store.record_occurrence_extraction_disposition(
            source_chunk_id=str(chunk["id"]),
            extractor_version="phase6-live-pg-cas-v1",
            disposition="no_occurrence",
            metadata_json={"raw_no_occurrence_guard": False},
        )
        assert created is True

    writer_conn = psycopg.connect(app_url, row_factory=dict_row)
    review_thread: Thread | None = None
    pid_queue: Queue[int] = Queue()
    outcome_queue: Queue[object] = Queue()
    try:
        set_current_user(writer_conn, owner_id)
        with writer_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE occurrence_extraction_dispositions
                SET metadata_json = %s::jsonb,
                    updated_at = clock_timestamp()
                WHERE user_id = app.current_user_id()
                  AND id = %s::uuid
                  AND review_status = 'candidate'
                  AND review_version = %s
                RETURNING id, review_status, review_version, metadata_json
                """,
                (
                    json.dumps(
                        {"raw_no_occurrence_guard": True},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    str(initial["id"]),
                    int(initial["review_version"]),
                ),
            )
            replacement = cur.fetchone()
        assert replacement is not None
        assert replacement["id"] == initial["id"]
        assert int(replacement["review_version"]) == int(initial["review_version"])

        def run_stale_review() -> None:
            try:
                with user_connection(app_url, owner_id) as review_conn:
                    with review_conn.cursor() as cur:
                        cur.execute("SELECT pg_backend_pid() AS pid")
                        pid_queue.put(int(cur.fetchone()["pid"]))
                    reviewed = PostgresVNextStore(review_conn).review_occurrence_extraction_disposition(
                        disposition_id=str(initial["id"]),
                        action="accepted",
                        reviewer_id="stale-reviewer",
                        reason="The pre-replacement facts appeared complete.",
                        expected_review_version=int(initial["review_version"]),
                    )
                outcome_queue.put(reviewed)
            except BaseException as exc:
                outcome_queue.put(exc)

        review_thread = Thread(
            target=run_stale_review,
            name="phase6-stale-disposition-review",
            daemon=True,
        )
        review_thread.start()
        reviewer_pid = pid_queue.get(timeout=5)

        blocked_on_writer = False
        deadline = monotonic() + 5
        with psycopg.connect(
            admin_url,
            autocommit=True,
            row_factory=dict_row,
        ) as admin_conn:
            while monotonic() < deadline:
                with admin_conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT wait_event_type
                        FROM pg_stat_activity
                        WHERE pid = %s
                        """,
                        (reviewer_pid,),
                    )
                    activity = cur.fetchone()
                if activity is not None and activity["wait_event_type"] == "Lock":
                    blocked_on_writer = True
                    break
                if not review_thread.is_alive():
                    break
                sleep(0.01)
        assert blocked_on_writer is True

        writer_conn.commit()
        review_thread.join(timeout=5)
        assert review_thread.is_alive() is False
        outcome = outcome_queue.get(timeout=1)
        assert isinstance(outcome, ContinuityStoreInvariantError)
        assert "lost its lifecycle CAS" in str(outcome)
    finally:
        writer_conn.rollback()
        writer_conn.close()
        if review_thread is not None:
            review_thread.join(timeout=5)

    with user_connection(app_url, owner_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_status, review_version, review_receipt_digest,
                       metadata_json
                FROM occurrence_extraction_dispositions
                WHERE user_id = app.current_user_id()
                  AND id = %s::uuid
                """,
                (str(initial["id"]),),
            )
            preserved = cur.fetchone()
    assert preserved is not None
    assert preserved["review_status"] == "candidate"
    assert int(preserved["review_version"]) == int(initial["review_version"])
    assert preserved["review_receipt_digest"] is None
    assert preserved["metadata_json"] == {"raw_no_occurrence_guard": True}


def test_disposition_rebinds_changed_source_memory_before_requalification(
    migrated_database_urls,
) -> None:
    """Postgres reconstructs the same source-memory facts as SQLite."""

    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="memory-facts")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "conversation",
                "content_hash": f"phase6-memory-facts:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
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
        original_facts = disposition["metadata_json"]["memory_facts_digests"]
        assert set(original_facts) == {str(memory["id"])}
        reviewed = store.review_occurrence_extraction_disposition(
            disposition_id=str(disposition["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
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

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE memories
                SET canonical_text = %s,
                    value = %s::jsonb
                WHERE user_id = app.current_user_id()
                  AND id = %s::uuid
                """,
                (
                    "I published another release.",
                    json.dumps(
                        {"text": "I published another release."},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    str(memory["id"]),
                ),
            )
            assert cur.rowcount == 1
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
        assert (
            replacement["metadata_json"]["memory_facts_digests"][str(memory["id"])] != original_facts[str(memory["id"])]
        )
        store.review_occurrence_extraction_disposition(
            disposition_id=str(replacement["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
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


def test_source_title_change_stales_extraction_until_rereview(
    migrated_database_urls,
) -> None:
    """Postgres binds connector-framing title semantics into extraction receipts."""

    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="source-title")
    extractor_version = "phase6-source-title-v1"
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "conversation",
                "content_hash": f"phase6-source-title:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
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
            reviewer_id="phase6-reviewer",
            reason="The titled neutral chunk was exhaustively reviewed.",
            expected_review_version=int(disposition["review_version"]),
        )
        original_summary = store.summarize_occurrence_extraction_accounting(
            extractor_version=extractor_version,
            source_ids=[str(source["id"])],
        )
        assert original_summary["complete"] is True

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sources
                SET title = %s
                WHERE user_id = app.current_user_id()
                  AND id = %s::uuid
                """,
                ("Different connector framing", str(source["id"])),
            )
            assert cur.rowcount == 1
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
            reviewer_id="phase6-reviewer",
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


def test_disposition_record_rejects_concurrent_source_title_snapshot_postgres(
    migrated_database_urls,
) -> None:
    """A decision made on title A cannot be recorded against title B."""

    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="source-title-cas")
    with user_connection(app_url, owner_id) as seed_conn:
        store = PostgresVNextStore(seed_conn)
        source = store.create_source(
            {
                "source_type": "conversation",
                "content_hash": f"phase6-source-title-cas:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
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

    with user_connection(app_url, owner_id) as observer_conn:
        observer = PostgresVNextStore(observer_conn)
        observed = observer.get_source_chunk_for_occurrence_accounting(str(chunk["id"]))
        assert observed is not None
        stale_snapshot = str(observed["snapshot_sha256"])

        with user_connection(app_url, owner_id) as concurrent_conn:
            with concurrent_conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sources
                    SET title = %s
                    WHERE user_id = app.current_user_id()
                      AND id = %s::uuid
                    """,
                    ("Different title", str(source["id"])),
                )
                assert cur.rowcount == 1

        with pytest.raises(
            ContinuityStoreInvariantError,
            match="snapshot CAS is stale",
        ):
            observer.record_occurrence_extraction_disposition(
                source_chunk_id=str(chunk["id"]),
                extractor_version="phase6-title-cas-v1",
                expected_snapshot_sha256=stale_snapshot,
                disposition="no_occurrence",
                metadata_json={"raw_no_occurrence_guard": False},
            )
        with observer_conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM occurrence_extraction_dispositions
                WHERE user_id = app.current_user_id()
                  AND source_chunk_id = %s::uuid
                """,
                (str(chunk["id"]),),
            )
            assert cur.fetchone()["count"] == 0

        current = observer.get_source_chunk_for_occurrence_accounting(str(chunk["id"]))
        assert current is not None
        assert current["snapshot_sha256"] != stale_snapshot
        recorded, created = observer.record_occurrence_extraction_disposition(
            source_chunk_id=str(chunk["id"]),
            extractor_version="phase6-title-cas-v1",
            expected_snapshot_sha256=str(current["snapshot_sha256"]),
            disposition="no_occurrence",
            metadata_json={"raw_no_occurrence_guard": True},
        )
        assert created is True
        assert recorded["snapshot_sha256"] == current["snapshot_sha256"]


def test_reviewed_unresolved_disposition_completes_extraction_not_exact_count(
    migrated_database_urls,
) -> None:
    """Reviewed extraction completeness must not imply resolved count identity."""

    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="reviewed-unresolved")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        source = store.create_source(
            {
                "source_type": "conversation",
                "content_hash": f"phase6-reviewed-unresolved:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
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
        accepted_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.reviewed-unresolved.accepted.{uuid4()}",
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "new",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        accepted_occurrence_key = f"phase6.reviewed-unresolved.unit.{uuid4()}"
        accepted_unit, _ = store.get_or_create_occurrence_unit(
            {
                "claim_id": accepted_claim["id"],
                "claim_ordinal": 1,
                "occurrence_key": accepted_occurrence_key,
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published one release.",
                "identity_status": "resolved",
                "aggregation_json": _unit_aggregation(accepted_occurrence_key),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        store.create_occurrence_evidence(
            {
                "claim_id": accepted_claim["id"],
                "occurrence_id": accepted_unit["id"],
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
                "evidence_key": f"phase6.reviewed-unresolved.accepted-evidence.{uuid4()}",
                "quote": "I published one release.",
            }
        )
        store.review_occurrence_claim(
            claim_id=str(accepted_claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="phase6-reviewer",
            reason="The first occurrence identity was verified.",
        )
        accepted_unit = store.review_occurrence_unit(
            occurrence_id=str(accepted_unit["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
            reason="The first occurrence evidence was verified.",
        )
        pending_claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.reviewed-unresolved.pending.{uuid4()}",
                "count_key": "published release",
                "predicate_json": _predicate("publish", "release"),
                "canonical_text": "Published another release.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "ambiguous",
                "identity_basis": "ambiguous",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "project_scope": ["alice"],
            }
        )
        store.create_occurrence_evidence(
            {
                "claim_id": pending_claim["id"],
                "source_id": source["id"],
                "source_chunk_id": chunk["id"],
                "evidence_key": f"phase6.reviewed-unresolved.pending-evidence.{uuid4()}",
                "quote": "I published another release.",
            }
        )
        disposition, created = store.record_occurrence_extraction_disposition(
            source_chunk_id=str(chunk["id"]),
            extractor_version="phase6-reviewed-unresolved-v1",
            disposition="unresolved_claims",
            predicate_keys=["published release"],
            claim_ids=[
                str(accepted_claim["id"]),
                str(pending_claim["id"]),
            ],
            occurrence_ids=[str(accepted_unit["id"])],
        )
        assert created is True
        reviewed = store.review_occurrence_extraction_disposition(
            disposition_id=str(disposition["id"]),
            action="accepted",
            reviewer_id="phase6-reviewer",
            reason="The chunk was exhaustively extracted; occurrence identity remains unresolved.",
            expected_review_version=int(disposition["review_version"]),
        )
        summary = store.summarize_occurrence_extraction_accounting(
            extractor_version="phase6-reviewed-unresolved-v1",
            source_ids=[str(source["id"])],
        )
        preserved_claim = store.get_occurrence_claim(str(pending_claim["id"]))

        assert reviewed["review_status"] == "accepted"
        assert reviewed["review_receipt_digest"] is not None
        assert summary["complete"] is True
        assert summary["reviewed_current_count"] == 1
        assert summary["unresolved_count"] == 1
        assert summary["items"][0]["status"] == "complete_with_unresolved_claims"
        assert preserved_claim is not None
        assert preserved_claim["resolution_status"] == "pending"
        assert preserved_claim["review_status"] == "candidate"

        accounting_metadata = {
            "accounting_schema": "occurrence_accounting_v1",
            "extractor_version": summary["extractor_version"],
            "source_ids": summary["source_ids"],
            "source_chunk_ids": summary["source_chunk_ids"],
            "snapshot_digest": summary["snapshot_digest"],
            "disposition_digest": summary["disposition_digest"],
        }
        coverage = store.ensure_occurrence_coverage(
            started_at="2020-01-01T00:00:00Z",
        )
        store.review_occurrence_coverage(
            coverage_mode="complete_history",
            historical_review_status="reviewed",
            coverage_started_at="2020-01-01T00:00:00Z",
            complete_through="2040-12-31T23:59:59Z",
            reviewer_id="phase6-reviewer",
            reason="The occurrence history was exhaustively reviewed.",
            accounting_metadata=accounting_metadata,
            expected_review_version=int(coverage["review_version"]),
        )

    with user_connection(app_url, owner_id) as reader_conn:
        reader_store = PostgresVNextStore(reader_conn)
        pack = VNextRetrievalService(reader_store).compile_context_pack(
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


def test_postgres_reviewed_source_retitle_reestablishes_signed_count_identity(
    migrated_database_urls,
) -> None:
    """A retitle creates fresh evidence and re-signs the same semantic unit."""

    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="source-reestablish")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        capture = VNextCaptureService(store).capture_source(
            SourceCaptureInput(
                source_type="conversation",
                raw_text="I visited museums on March 3, 2026.",
                title="Original heading",
                source_created_at="2026-03-05T12:00:00Z",
                domain="personal",
                sensitivity="private",
                metadata_json={
                    "provenance_role": "user",
                    "session_date": "2026-03-05T12:00:00Z",
                },
            )
        )
        source = store.get_source(str(capture.source_id))
        assert source is not None
        chunk = store.list_source_chunks(str(capture.source_id))[0]
        initial_reviewed = review_source_chunk_occurrences(
            store,
            source_chunk_id=str(chunk["id"]),
            reviewer_id="phase6-reviewer",
            reason="The original source snapshot was reviewed.",
            actor_type="user",
            stage="http_source_review",
        )
        assert len(initial_reviewed) == 1
        claim = store.list_occurrence_claims_for_source_chunk(
            str(chunk["id"]),
            limit=201,
        )[0]
        original_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]

        store.lock_source_occurrence_envelope(str(source["id"]))
        VNextMemoryCommitService(store).retire_source_occurrence_state(
            str(source["id"]),
            stage="http_source_review_envelope_change",
            reason="The source title occurrence input changed.",
            _defer_occurrence_accounting=True,
        )
        updated = store.update_source(
            source_id=str(source["id"]),
            patch={"title": "Retitled heading"},
            actor_type="user",
        )
        records = establish_source_chunk_occurrences(
            store,
            source=updated,
            source_chunk=chunk,
            actor_type="user",
            stage="http_source_review_envelope_change",
        )
        reviewed = review_source_chunk_occurrences(
            store,
            source_chunk_id=str(chunk["id"]),
            reviewer_id="phase6-reviewer",
            reason="The retitled source snapshot was reviewed.",
            actor_type="user",
            stage="http_source_review",
            _defer_occurrence_accounting=True,
        )
        reconcile_chunk_extraction_disposition(
            store,
            source_chunk_id=str(chunk["id"]),
            actor_type="user",
            reviewer_id="phase6-reviewer",
            reason=(
                "The retitled source snapshot was reviewed. Extraction disposition reviewed during http_source_review."
            ),
        )
        current_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
        accounting = store.summarize_occurrence_extraction_accounting(
            extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
            source_ids=[str(source["id"])],
        )

        assert len(records) == 1
        assert reviewed == [str(claim["id"])]
        assert current_unit["id"] == original_unit["id"]
        assert current_unit["occurrence_key"] == original_unit["occurrence_key"]
        assert current_unit["review_status"] == "accepted"
        assert current_unit["review_receipt_action"] == "reestablished"
        assert current_unit["retired_at"] is None
        assert current_unit["retired_by"] is None
        assert current_unit["retirement_reason"] is None
        assert current_unit["superseded_by"] is None
        assert accounting["complete"] is True
        assert accounting["reviewed_current_count"] == 1


def test_postgres_stale_source_snapshot_evidence_fails_closed(
    migrated_database_urls,
) -> None:
    """Re-establishment rejects evidence signed for an older source snapshot."""

    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="source-reestablish-race")
    with user_connection(app_url, owner_id) as conn:
        store = PostgresVNextStore(conn)
        capture = VNextCaptureService(store).capture_source(
            SourceCaptureInput(
                source_type="conversation",
                raw_text="I visited museums on March 3, 2026.",
                title="Original heading",
                source_created_at="2026-03-05T12:00:00Z",
                domain="personal",
                sensitivity="private",
                metadata_json={
                    "provenance_role": "user",
                    "session_date": "2026-03-05T12:00:00Z",
                },
            )
        )
        source = store.get_source(str(capture.source_id))
        assert source is not None
        chunk = store.list_source_chunks(str(capture.source_id))[0]
        review_source_chunk_occurrences(
            store,
            source_chunk_id=str(chunk["id"]),
            reviewer_id="phase6-reviewer",
            reason="The original source snapshot was reviewed.",
            actor_type="user",
            stage="http_source_review",
        )
        claim = store.list_occurrence_claims_for_source_chunk(
            str(chunk["id"]),
            limit=201,
        )[0]
        original_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
        store.lock_source_occurrence_envelope(str(source["id"]))
        VNextMemoryCommitService(store).retire_source_occurrence_state(
            str(source["id"]),
            stage="http_source_review_envelope_change",
            reason="The source title occurrence input changed.",
            _defer_occurrence_accounting=True,
        )
        updated = store.update_source(
            source_id=str(source["id"]),
            patch={"title": "Snapshot B"},
            actor_type="user",
        )
        establish_source_chunk_occurrences(
            store,
            source=updated,
            source_chunk=chunk,
            actor_type="user",
            stage="http_source_review_envelope_change",
        )
        invalidate_occurrence_accounting(
            store,
            reason="The replacement source snapshot requires review.",
            actor_type="user",
            actor_id="phase6-reviewer",
            source_chunk_id=str(chunk["id"]),
        )
        store.update_source(
            source_id=str(source["id"]),
            patch={"title": "Snapshot C"},
            actor_type="user",
        )

    with user_connection(app_url, owner_id) as review_conn:
        store = PostgresVNextStore(review_conn)
        with pytest.raises(
            ContinuityStoreInvariantError,
            match="fresh current-snapshot evidence",
        ):
            review_source_chunk_occurrences(
                store,
                source_chunk_id=str(chunk["id"]),
                reviewer_id="phase6-reviewer",
                reason="A stale source snapshot must not be re-signed.",
                actor_type="user",
                stage="http_source_review",
            )

        current_unit = store.list_occurrence_units_for_claim(str(claim["id"]))[0]
        assert current_unit["id"] == original_unit["id"]
        assert current_unit["review_status"] == "retired"
        assert current_unit["review_receipt_action"] == "retired"


def test_postgres_second_retitle_waits_for_uncommitted_reestablishment_and_resigns_final_snapshot(
    migrated_database_urls,
) -> None:
    """A second retitle cannot retire before the first review becomes visible."""

    admin_url = migrated_database_urls["admin"]
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="source-second-reestablish")
    with user_connection(app_url, owner_id) as setup_conn:
        setup_store = PostgresVNextStore(setup_conn)
        capture = VNextCaptureService(setup_store).capture_source(
            SourceCaptureInput(
                source_type="conversation",
                raw_text="I visited museums on March 3, 2026.",
                title="Original heading",
                source_created_at="2026-03-05T12:00:00Z",
                domain="personal",
                sensitivity="private",
                metadata_json={
                    "provenance_role": "user",
                    "session_date": "2026-03-05T12:00:00Z",
                },
            )
        )
        source = setup_store.get_source(str(capture.source_id))
        assert source is not None
        chunk = setup_store.list_source_chunks(str(capture.source_id))[0]
        review_source_chunk_occurrences(
            setup_store,
            source_chunk_id=str(chunk["id"]),
            reviewer_id="phase6-reviewer",
            reason="The original source snapshot was reviewed.",
            actor_type="user",
            stage="http_source_review",
        )
        claim = setup_store.list_occurrence_claims_for_source_chunk(
            str(chunk["id"]),
            limit=201,
        )[0]
        original_unit = setup_store.list_occurrence_units_for_claim(str(claim["id"]))[0]

        setup_store.lock_source_occurrence_envelope(str(source["id"]))
        VNextMemoryCommitService(setup_store).retire_source_occurrence_state(
            str(source["id"]),
            stage="http_source_review_envelope_change",
            reason="The source title occurrence input changed.",
            _defer_occurrence_accounting=True,
        )
        snapshot_b = setup_store.update_source(
            source_id=str(source["id"]),
            patch={"title": "Snapshot B"},
            actor_type="user",
        )
        establish_source_chunk_occurrences(
            setup_store,
            source=snapshot_b,
            source_chunk=chunk,
            actor_type="user",
            stage="http_source_review_envelope_change",
        )
        invalidate_occurrence_accounting(
            setup_store,
            reason=("The source title occurrence input changed. (http_source_review_envelope_change)"),
            actor_type="user",
            actor_id="phase6-reviewer",
            source_chunk_id=str(chunk["id"]),
        )

    pid_queue: Queue[int] = Queue()
    outcome_queue: Queue[object] = Queue()

    def run_second_retitle() -> None:
        try:
            with user_connection(app_url, owner_id) as second_conn:
                second_store = PostgresVNextStore(second_conn)
                with second_conn.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid() AS pid")
                    pid_queue.put(int(cur.fetchone()["pid"]))
                locked = second_store.lock_source_occurrence_envelope(str(source["id"]))
                VNextMemoryCommitService(second_store).retire_source_occurrence_state(
                    str(source["id"]),
                    stage="http_source_review_envelope_change",
                    reason="The source title occurrence input changed again.",
                    _defer_occurrence_accounting=True,
                )
                snapshot_c = second_store.update_source(
                    source_id=str(source["id"]),
                    patch={"title": "Snapshot C"},
                    actor_type="user",
                )
                establish_source_chunk_occurrences(
                    second_store,
                    source=snapshot_c,
                    source_chunk=chunk,
                    actor_type="user",
                    stage="http_source_review_envelope_change",
                )
                reviewed = review_source_chunk_occurrences(
                    second_store,
                    source_chunk_id=str(chunk["id"]),
                    reviewer_id="phase6-reviewer-2",
                    reason="The final source snapshot was reviewed.",
                    actor_type="user",
                    stage="http_source_review",
                    _defer_occurrence_accounting=True,
                )
                reconcile_chunk_extraction_disposition(
                    second_store,
                    source_chunk_id=str(chunk["id"]),
                    actor_type="user",
                    reviewer_id="phase6-reviewer-2",
                    reason=(
                        "The final source snapshot was reviewed. "
                        "Extraction disposition reviewed during http_source_review."
                    ),
                )
                outcome_queue.put(
                    {
                        "locked_title": locked.get("title"),
                        "reviewed": reviewed,
                    }
                )
        except BaseException as exc:
            outcome_queue.put(exc)

    second_thread: Thread | None = None
    with user_connection(app_url, owner_id) as first_conn:
        first_store = PostgresVNextStore(first_conn)
        locked = first_store.lock_source_occurrence_envelope(str(source["id"]))
        assert locked["title"] == "Snapshot B"

        second_thread = Thread(
            target=run_second_retitle,
            name="phase6-second-source-retitle",
            daemon=True,
        )
        second_thread.start()
        second_pid = pid_queue.get(timeout=5)

        blocked_before_retirement = False
        deadline = monotonic() + 5
        with psycopg.connect(
            admin_url,
            autocommit=True,
            row_factory=dict_row,
        ) as admin_conn:
            while monotonic() < deadline:
                with admin_conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT wait_event_type
                        FROM pg_stat_activity
                        WHERE pid = %s
                        """,
                        (second_pid,),
                    )
                    activity = cur.fetchone()
                if activity is not None and activity["wait_event_type"] == "Lock":
                    blocked_before_retirement = True
                    break
                if not second_thread.is_alive():
                    break
                sleep(0.01)
        assert blocked_before_retirement is True

        assert review_source_chunk_occurrences(
            first_store,
            source_chunk_id=str(chunk["id"]),
            reviewer_id="phase6-reviewer",
            reason="The first retitled source snapshot was reviewed.",
            actor_type="user",
            stage="http_source_review",
        ) == [str(claim["id"])]
        uncommitted_unit = first_store.list_occurrence_units_for_claim(str(claim["id"]))[0]
        assert uncommitted_unit["review_status"] == "accepted"
        assert uncommitted_unit["review_receipt_action"] == "reestablished"

    assert second_thread is not None
    second_thread.join(timeout=5)
    assert second_thread.is_alive() is False
    outcome = outcome_queue.get(timeout=1)
    assert isinstance(outcome, dict), repr(outcome)
    assert outcome == {
        "locked_title": "Snapshot B",
        "reviewed": [str(claim["id"])],
    }

    with user_connection(app_url, owner_id) as reader_conn:
        reader_store = PostgresVNextStore(reader_conn)
        final_source = reader_store.get_source(str(source["id"]))
        final_snapshot = reader_store.get_source_chunk_for_occurrence_accounting(str(chunk["id"]))
        final_unit = reader_store.list_occurrence_units_for_claim(str(claim["id"]))[0]
        final_evidence = reader_store.list_occurrence_evidence_for_units([str(final_unit["id"])])
        accounting = reader_store.summarize_occurrence_extraction_accounting(
            extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
            source_ids=[str(source["id"])],
        )

        assert final_source is not None
        assert final_source["title"] == "Snapshot C"
        assert final_snapshot is not None
        assert final_unit["id"] == original_unit["id"]
        assert final_unit["occurrence_key"] == original_unit["occurrence_key"]
        assert final_unit["review_status"] == "accepted"
        assert final_unit["review_receipt_action"] == "reestablished"
        assert final_unit["retired_at"] is None
        assert len(final_evidence) == 1
        assert final_evidence[0]["review_receipt_action"] == "reestablished"
        assert final_evidence[0]["unit_review_receipt_digest"] == final_unit["review_receipt_digest"]
        assert final_evidence[0]["metadata_json"]["source_snapshot_sha256"] == final_snapshot["snapshot_sha256"]
        assert accounting["complete"] is True
        assert accounting["reviewed_current_count"] == 1


def _assert_backend_waits_on_graph_lock(
    admin_url: str,
    *,
    backend_pid: int,
    worker_thread: Thread,
) -> None:
    """Prove the competing mutation reached PostgreSQL's lock wait."""

    blocked_on_graph_lock = False
    deadline = monotonic() + 5
    with psycopg.connect(
        admin_url,
        autocommit=True,
        row_factory=dict_row,
    ) as admin_conn:
        while monotonic() < deadline:
            with admin_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT wait_event_type
                    FROM pg_stat_activity
                    WHERE pid = %s
                    """,
                    (backend_pid,),
                )
                activity = cur.fetchone()
            if activity is not None and activity["wait_event_type"] == "Lock":
                blocked_on_graph_lock = True
                break
            if not worker_thread.is_alive():
                break
            sleep(0.01)
    assert blocked_on_graph_lock is True


def _race_claim_payload(
    label: str,
    *,
    resolution_decision: str = "new",
    identity_basis: str = "exact_time",
) -> dict[str, object]:
    return {
        "claim_key": f"phase6.race.{label}.claim.{uuid4()}",
        "count_key": "published release",
        "predicate_json": _predicate("publish", "release"),
        "canonical_text": "Published one release.",
        "quantity_min": 1,
        "quantity_max": 1,
        "range_kind": "exact",
        "resolution_decision": resolution_decision,
        "identity_basis": identity_basis,
        "aggregation_json": _claim_aggregation(),
        "occurred_at_start": "2026-07-24T12:00:00Z",
        "occurred_at_end": "2026-07-24T12:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "project_scope": ["alice"],
    }


def _race_unit_payload(
    claim_id: object,
    *,
    label: str,
) -> tuple[str, dict[str, object]]:
    occurrence_key = f"phase6.race.{label}.unit.{uuid4()}"
    return occurrence_key, {
        "claim_id": claim_id,
        "claim_ordinal": 1,
        "occurrence_key": occurrence_key,
        "count_key": "published release",
        "predicate_json": _predicate("publish", "release"),
        "canonical_text": "Published one release.",
        "identity_status": "resolved",
        "aggregation_json": _unit_aggregation(occurrence_key),
        "occurred_at_start": "2026-07-24T12:00:00Z",
        "occurred_at_end": "2026-07-24T12:00:00Z",
        "domain": "project",
        "sensitivity": "private",
        "project_scope": ["alice"],
    }


def _seed_accepted_race_unit(
    store: PostgresVNextStore,
    *,
    label: str,
    source_id: object,
) -> tuple[dict[str, object], dict[str, object]]:
    claim, _ = store.get_or_create_occurrence_claim(
        _race_claim_payload(label),
    )
    _, unit_payload = _race_unit_payload(claim["id"], label=label)
    unit, _ = store.get_or_create_occurrence_unit(unit_payload)
    store.create_occurrence_evidence(
        {
            "claim_id": claim["id"],
            "occurrence_id": unit["id"],
            "source_id": source_id,
            "evidence_key": f"phase6.race.{label}.evidence.{uuid4()}",
            "quote": "I published one release.",
        }
    )
    claim = store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis="exact_time",
        reviewer_id="phase6-race-reviewer",
        reason="The occurrence identity was verified before the race.",
    )
    unit = store.review_occurrence_unit(
        occurrence_id=str(unit["id"]),
        action="accepted",
        reviewer_id="phase6-race-reviewer",
        reason="The occurrence evidence was verified before the race.",
    )
    return claim, unit


def test_postgres_late_evidence_waits_for_unit_retirement_and_fails_closed(
    migrated_database_urls,
) -> None:
    admin_url = migrated_database_urls["admin"]
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="late-evidence-race")
    with user_connection(app_url, owner_id) as setup_conn:
        setup_store = PostgresVNextStore(setup_conn)
        source = setup_store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:late-evidence-race:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        claim, unit = _seed_accepted_race_unit(
            setup_store,
            label="late-evidence",
            source_id=source["id"],
        )

    late_evidence_key = f"phase6.race.late-evidence.{uuid4()}"
    pid_queue: Queue[int] = Queue()
    outcome_queue: Queue[object] = Queue()

    def attach_late_evidence() -> None:
        try:
            with user_connection(app_url, owner_id) as evidence_conn:
                with evidence_conn.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid() AS pid")
                    pid_queue.put(int(cur.fetchone()["pid"]))
                outcome_queue.put(
                    PostgresVNextStore(evidence_conn).create_occurrence_evidence(
                        {
                            "claim_id": claim["id"],
                            "occurrence_id": unit["id"],
                            "source_id": source["id"],
                            "evidence_key": late_evidence_key,
                            "quote": "I published one release.",
                        }
                    )
                )
        except BaseException as exc:
            outcome_queue.put(exc)

    writer_conn = psycopg.connect(app_url, row_factory=dict_row)
    worker_thread: Thread | None = None
    try:
        set_current_user(writer_conn, owner_id)
        writer_store = PostgresVNextStore(writer_conn)
        writer_store.lock_graph_mutation()

        worker_thread = Thread(
            target=attach_late_evidence,
            name="phase6-late-evidence-race",
            daemon=True,
        )
        worker_thread.start()
        worker_pid = pid_queue.get(timeout=5)
        _assert_backend_waits_on_graph_lock(
            admin_url,
            backend_pid=worker_pid,
            worker_thread=worker_thread,
        )

        retired = writer_store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="retired",
            expected_status="accepted",
            expected_review_version=int(unit["review_version"]),
            reviewer_id="phase6-race-reviewer",
            reason="The accepted unit was retired while a late evidence write waited.",
        )
        assert retired["review_status"] == "retired"
        writer_conn.commit()

        worker_thread.join(timeout=5)
        assert worker_thread.is_alive() is False
        outcome = outcome_queue.get(timeout=1)
        assert isinstance(outcome, ContinuityStoreInvariantError)
        assert "candidate or accepted unit" in str(outcome)
    finally:
        writer_conn.rollback()
        writer_conn.close()
        if worker_thread is not None:
            worker_thread.join(timeout=5)

    with user_connection(app_url, owner_id) as reader_conn:
        reader_store = PostgresVNextStore(reader_conn)
        current_unit = reader_store.get_occurrence_unit_by_key(str(unit["occurrence_key"]))
        assert current_unit is not None
        assert current_unit["review_status"] == "retired"
        assert current_unit["superseded_by"] is None
        with reader_conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM occurrence_evidence
                WHERE user_id = app.current_user_id()
                  AND evidence_key = %s
                """,
                (late_evidence_key,),
            )
            assert cur.fetchone()["count"] == 0


def test_postgres_new_unit_waits_for_claim_rejection_and_fails_closed(
    migrated_database_urls,
) -> None:
    admin_url = migrated_database_urls["admin"]
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="new-unit-rejection-race")
    with user_connection(app_url, owner_id) as setup_conn:
        setup_store = PostgresVNextStore(setup_conn)
        claim, _ = setup_store.get_or_create_occurrence_claim(
            _race_claim_payload(
                "new-unit-rejection",
                resolution_decision="ambiguous",
                identity_basis="ambiguous",
            )
        )
    occurrence_key, unit_payload = _race_unit_payload(
        claim["id"],
        label="new-unit-rejection",
    )

    pid_queue: Queue[int] = Queue()
    outcome_queue: Queue[object] = Queue()

    def insert_new_unit() -> None:
        try:
            with user_connection(app_url, owner_id) as unit_conn:
                with unit_conn.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid() AS pid")
                    pid_queue.put(int(cur.fetchone()["pid"]))
                outcome_queue.put(PostgresVNextStore(unit_conn).get_or_create_occurrence_unit(unit_payload))
        except BaseException as exc:
            outcome_queue.put(exc)

    writer_conn = psycopg.connect(app_url, row_factory=dict_row)
    worker_thread: Thread | None = None
    try:
        set_current_user(writer_conn, owner_id)
        writer_store = PostgresVNextStore(writer_conn)
        writer_store.lock_graph_mutation()

        worker_thread = Thread(
            target=insert_new_unit,
            name="phase6-new-unit-rejection-race",
            daemon=True,
        )
        worker_thread.start()
        worker_pid = pid_queue.get(timeout=5)
        _assert_backend_waits_on_graph_lock(
            admin_url,
            backend_pid=worker_pid,
            worker_thread=worker_thread,
        )

        rejected = writer_store.review_occurrence_claim(
            claim_id=str(claim["id"]),
            resolution_status="rejected",
            resolution_decision="ambiguous",
            identity_basis="ambiguous",
            reviewer_id="phase6-race-reviewer",
            reason="The claim was rejected while a unit insert waited.",
        )
        assert rejected["review_status"] == "rejected"
        writer_conn.commit()

        worker_thread.join(timeout=5)
        assert worker_thread.is_alive() is False
        outcome = outcome_queue.get(timeout=1)
        assert isinstance(outcome, ContinuityStoreInvariantError)
        assert "requires a candidate pending owning claim" in str(outcome)
    finally:
        writer_conn.rollback()
        writer_conn.close()
        if worker_thread is not None:
            worker_thread.join(timeout=5)

    with user_connection(app_url, owner_id) as reader_conn:
        reader_store = PostgresVNextStore(reader_conn)
        current_claim = reader_store.get_occurrence_claim(str(claim["id"]))
        assert current_claim is not None
        assert current_claim["resolution_status"] == "rejected"
        assert current_claim["review_status"] == "rejected"
        assert reader_store.get_occurrence_unit_by_key(occurrence_key) is None


def test_postgres_supersession_waits_for_successor_retirement_and_fails_closed(
    migrated_database_urls,
) -> None:
    admin_url = migrated_database_urls["admin"]
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="successor-retirement-race")
    with user_connection(app_url, owner_id) as setup_conn:
        setup_store = PostgresVNextStore(setup_conn)
        source = setup_store.create_source(
            {
                "source_type": "note",
                "content_hash": f"phase6:successor-retirement-race:{uuid4()}",
                "captured_at": "2026-07-24T12:00:00Z",
                "domain": "project",
                "sensitivity": "private",
                "metadata_json": {"project_scope": ["alice"]},
            }
        )
        predecessor_claim, predecessor = _seed_accepted_race_unit(
            setup_store,
            label="supersession-predecessor",
            source_id=source["id"],
        )
        successor_claim, successor = _seed_accepted_race_unit(
            setup_store,
            label="supersession-successor",
            source_id=source["id"],
        )

    pid_queue: Queue[int] = Queue()
    outcome_queue: Queue[object] = Queue()

    def supersede_predecessor() -> None:
        try:
            with user_connection(app_url, owner_id) as supersession_conn:
                with supersession_conn.cursor() as cur:
                    cur.execute("SELECT pg_backend_pid() AS pid")
                    pid_queue.put(int(cur.fetchone()["pid"]))
                outcome_queue.put(
                    PostgresVNextStore(supersession_conn).review_occurrence_unit(
                        occurrence_id=str(predecessor["id"]),
                        action="superseded",
                        expected_status="accepted",
                        expected_review_version=int(predecessor["review_version"]),
                        superseded_by=str(successor["id"]),
                        reviewer_id="phase6-race-reviewer",
                        reason=("The predecessor attempted to bind the successor while its retirement waited."),
                    )
                )
        except BaseException as exc:
            outcome_queue.put(exc)

    writer_conn = psycopg.connect(app_url, row_factory=dict_row)
    worker_thread: Thread | None = None
    try:
        set_current_user(writer_conn, owner_id)
        writer_store = PostgresVNextStore(writer_conn)
        writer_store.lock_graph_mutation()

        worker_thread = Thread(
            target=supersede_predecessor,
            name="phase6-successor-retirement-race",
            daemon=True,
        )
        worker_thread.start()
        worker_pid = pid_queue.get(timeout=5)
        _assert_backend_waits_on_graph_lock(
            admin_url,
            backend_pid=worker_pid,
            worker_thread=worker_thread,
        )

        retired = writer_store.review_occurrence_unit(
            occurrence_id=str(successor["id"]),
            action="retired",
            expected_status="accepted",
            expected_review_version=int(successor["review_version"]),
            reviewer_id="phase6-race-reviewer",
            reason="The successor was retired before the supersession could proceed.",
        )
        assert retired["review_status"] == "retired"
        writer_conn.commit()

        worker_thread.join(timeout=5)
        assert worker_thread.is_alive() is False
        outcome = outcome_queue.get(timeout=1)
        assert isinstance(outcome, ContinuityStoreInvariantError)
        assert "requires an accepted resolved successor" in str(outcome)
    finally:
        writer_conn.rollback()
        writer_conn.close()
        if worker_thread is not None:
            worker_thread.join(timeout=5)

    with user_connection(app_url, owner_id) as reader_conn:
        reader_store = PostgresVNextStore(reader_conn)
        current_predecessor = reader_store.list_occurrence_units_for_claim(str(predecessor_claim["id"]))[0]
        current_successor = reader_store.list_occurrence_units_for_claim(str(successor_claim["id"]))[0]
        assert current_predecessor["review_status"] == "accepted"
        assert current_predecessor["superseded_by"] is None
        assert current_successor["review_status"] == "retired"
        with reader_conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM occurrence_units
                WHERE user_id = app.current_user_id()
                  AND superseded_by = %s::uuid
                """,
                (str(successor["id"]),),
            )
            assert cur.fetchone()["count"] == 0


def test_legacy_admission_reconciles_occurrence_carrier_and_rolls_back_failures(
    migrated_database_urls,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="legacy-admission-bridge")

    with user_connection(app_url, owner_id) as conn:
        legacy = ContinuityStore(conn)
        thread = legacy.create_thread("Legacy occurrence bridge")
        session = legacy.create_session(thread["id"], status="active")
        first_event = legacy.append_event(
            thread["id"],
            session["id"],
            "message.user",
            {"text": "I visited one museum."},
        )
        second_event = legacy.append_event(
            thread["id"],
            session["id"],
            "message.user",
            {"text": "I visited a different museum."},
        )
        admitted = admit_memory_candidate(
            legacy,
            user_id=owner_id,
            candidate=MemoryCandidateInput(
                memory_key="phase6.legacy.museum",
                value={"museum": "first"},
                source_event_ids=(first_event["id"],),
            ),
        )
        assert admitted.action == "ADD"
        assert admitted.memory is not None
        memory_id = admitted.memory["id"]

        store = PostgresVNextStore(conn)
        memory = store.update_memory(
            memory_id=memory_id,
            patch={
                "canonical_text": "I visited one museum.",
                "domain": "personal",
                "sensitivity": "private",
            },
            actor_type="user",
        )
        count_key = "visited museum"
        claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.legacy-admission-claim.{uuid4()}",
                "count_key": count_key,
                "predicate_json": _predicate("visit", "museum"),
                "canonical_text": "I visited one museum.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "new",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": memory["domain"],
                "sensitivity": memory["sensitivity"],
                "project_scope": memory.get("project_scope") or [],
            }
        )
        occurrence_key = f"phase6.legacy-admission-unit.{uuid4()}"
        unit, _ = store.get_or_create_occurrence_unit(
            {
                "claim_id": claim["id"],
                "claim_ordinal": 1,
                "occurrence_key": occurrence_key,
                "count_key": count_key,
                "predicate_json": _predicate("visit", "museum"),
                "canonical_text": "I visited one museum.",
                "identity_status": "resolved",
                "aggregation_json": _unit_aggregation(occurrence_key),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": memory["domain"],
                "sensitivity": memory["sensitivity"],
                "project_scope": memory.get("project_scope") or [],
            }
        )
        evidence = store.create_occurrence_evidence(
            {
                "claim_id": claim["id"],
                "occurrence_id": unit["id"],
                "memory_id": memory_id,
                "evidence_key": f"phase6.legacy-admission-evidence.{uuid4()}",
                "quote": "I visited one museum.",
            }
        )
        store.review_occurrence_claim(
            claim_id=str(claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="phase6-reviewer",
            reason="The legacy memory occurrence identity was reviewed.",
        )
        unit = store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            expected_status="candidate",
            expected_review_version=int(unit["review_version"]),
            reviewer_id="phase6-reviewer",
            reason="The legacy memory occurrence evidence was reviewed.",
        )
        memory = store.get_memory_for_redaction(memory_id)
        assert memory is not None
        proposal_metadata = dict(memory["metadata_json"])
        proposal_metadata["occurrence_proposal"] = {
            "claim_id": str(claim["id"]),
            "claim_key": str(claim["claim_key"]),
            "materialization_status": "accepted",
            "occurrence_unit_ids": [str(unit["id"])],
        }
        store.write_occurrence_memory_metadata(
            memory_id=memory_id,
            metadata_json=proposal_metadata,
            expected_metadata_json=dict(memory["metadata_json"]),
            actor_type="user",
        )
        coverage = store.ensure_occurrence_coverage(
            started_at="2026-01-01T00:00:00Z",
        )
        signed_coverage = store.review_occurrence_coverage(
            coverage_mode="partial_history",
            historical_review_status="reviewed",
            coverage_started_at="2026-01-01T00:00:00Z",
            complete_through="2026-07-24T23:59:59Z",
            reviewer_id="phase6-reviewer",
            reason="The bounded legacy occurrence history was reviewed.",
            expected_review_version=int(coverage["review_version"]),
        )
        signed_unit_receipt = unit["review_receipt_digest"]
        signed_coverage_receipt = signed_coverage["review_receipt_digest"]

        metadata_only = admit_memory_candidate(
            legacy,
            user_id=owner_id,
            candidate=MemoryCandidateInput(
                memory_key="phase6.legacy.museum",
                value={"museum": "first"},
                source_event_ids=(first_event["id"],),
                confidence=0.91,
            ),
        )
        assert metadata_only.action == "UPDATE"
        preserved_unit = store.get_occurrence_unit_by_key(occurrence_key)
        preserved_coverage = store.get_occurrence_coverage()
        assert preserved_unit is not None
        assert preserved_unit["review_status"] == "accepted"
        assert preserved_unit["review_receipt_digest"] == signed_unit_receipt
        assert preserved_coverage is not None
        assert preserved_coverage["review_receipt_digest"] == signed_coverage_receipt
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_status, review_receipt_digest
                FROM occurrence_evidence
                WHERE id = %s::uuid
                """,
                (str(evidence["id"]),),
            )
            preserved_evidence = cur.fetchone()
        assert preserved_evidence["review_status"] == "accepted"
        assert preserved_evidence["review_receipt_digest"] is not None

        changed = admit_memory_candidate(
            legacy,
            user_id=owner_id,
            candidate=MemoryCandidateInput(
                memory_key="phase6.legacy.museum",
                value={"museum": "second"},
                source_event_ids=(second_event["id"],),
            ),
        )
        assert changed.action == "UPDATE"
        retired_unit = store.get_occurrence_unit_by_key(occurrence_key)
        assert retired_unit is not None
        assert retired_unit["review_status"] == "retired"
        claim_after = store.get_occurrence_claim(str(claim["id"]))
        assert claim_after is not None
        assert claim_after["review_status"] == "accepted"
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT review_status
                FROM occurrence_evidence
                WHERE id = %s::uuid
                """,
                (str(evidence["id"]),),
            )
            assert cur.fetchone()["review_status"] == "rejected"
        current_memory = store.get_memory_for_redaction(memory_id)
        assert current_memory is not None
        current_metadata = dict(current_memory["metadata_json"])
        assert "occurrence_proposal" not in current_metadata
        invalidation = dict(current_metadata["occurrence_invalidation"])
        invalidation_digest = invalidation.pop("invalidation_receipt_digest")
        assert invalidation_digest == hashlib.sha256(
            json.dumps(
                invalidation,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        invalidated_coverage = store.get_occurrence_coverage()
        assert invalidated_coverage is not None
        assert invalidated_coverage["coverage_mode"] == "forward_only"
        assert invalidated_coverage["review_receipt_digest"] is None

        original_reconcile = PostgresVNextStore.reconcile_occurrence_evidence_carrier

        def fail_reconcile(*_args, **_kwargs):
            raise RuntimeError("forced legacy occurrence reconciliation failure")

        monkeypatch.setattr(
            PostgresVNextStore,
            "reconcile_occurrence_evidence_carrier",
            fail_reconcile,
        )
        with pytest.raises(
            RuntimeError,
            match="forced legacy occurrence reconciliation failure",
        ):
            with conn.transaction():
                admit_memory_candidate(
                    legacy,
                    user_id=owner_id,
                    candidate=MemoryCandidateInput(
                        memory_key="phase6.legacy.museum",
                        value={"museum": "third"},
                        source_event_ids=(first_event["id"],),
                    ),
                )
        monkeypatch.setattr(
            PostgresVNextStore,
            "reconcile_occurrence_evidence_carrier",
            original_reconcile,
        )
        rolled_back = legacy.get_memory_by_key_and_profile(
            memory_key="phase6.legacy.museum",
            agent_profile_id="assistant_default",
        )
        assert rolled_back is not None
        assert rolled_back["value"] == {"museum": "second"}

        source_chunk_ids: list[str] = []
        disposition_ids: list[str] = []
        for index in (1, 2):
            source = store.create_source(
                {
                    "source_type": "note",
                    "content_hash": f"phase6:legacy-delete-accounting:{index}:{uuid4()}",
                    "captured_at": "2026-07-24T12:00:00Z",
                    "domain": "personal",
                    "sensitivity": "private",
                }
            )
            chunk = store.create_source_chunk(
                {
                    "source_id": source["id"],
                    "chunk_index": 0,
                    "text": f"Administrative chunk {index} with no event assertion.",
                }
            )
            source_chunk_ids.append(str(chunk["id"]))
        current_memory = store.get_memory_for_redaction(memory_id)
        assert current_memory is not None
        delete_metadata = dict(current_memory["metadata_json"])
        delete_metadata["source_chunk_id"] = source_chunk_ids[0]
        delete_metadata["occurrence_proposal"] = {
            "claim_id": str(claim["id"]),
            "claim_key": str(claim["claim_key"]),
            "materialization_status": "accepted",
            "occurrence_unit_ids": [str(unit["id"])],
            "source_chunk_id": source_chunk_ids[1],
        }
        store.update_memory(
            memory_id=memory_id,
            patch={"metadata_json": delete_metadata},
            actor_type="user",
        )
        for source_chunk_id in source_chunk_ids:
            disposition, _ = store.record_occurrence_extraction_disposition(
                source_chunk_id=source_chunk_id,
                extractor_version="phase6-legacy-delete-v1",
                disposition="no_occurrence",
            )
            disposition = store.review_occurrence_extraction_disposition(
                disposition_id=str(disposition["id"]),
                action="accepted",
                reviewer_id="phase6-reviewer",
                reason="The administrative chunk has no countable event.",
                expected_review_version=int(disposition["review_version"]),
            )
            disposition_ids.append(str(disposition["id"]))
        coverage = store.get_occurrence_coverage()
        assert coverage is not None
        store.review_occurrence_coverage(
            coverage_mode="partial_history",
            historical_review_status="reviewed",
            coverage_started_at=coverage["coverage_started_at"],
            complete_through="2026-07-25T23:59:59Z",
            reviewer_id="phase6-reviewer",
            reason="The delete accounting fixture was reviewed.",
            expected_review_version=int(coverage["review_version"]),
        )

        deleted = admit_memory_candidate(
            legacy,
            user_id=owner_id,
            candidate=MemoryCandidateInput(
                memory_key="phase6.legacy.museum",
                value=None,
                source_event_ids=(second_event["id"],),
                delete_requested=True,
            ),
        )
        assert deleted.action == "DELETE"
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, review_status
                FROM occurrence_extraction_dispositions
                WHERE id = ANY(%s::uuid[])
                ORDER BY id
                """,
                (disposition_ids,),
            )
            invalidated_dispositions = cur.fetchall()
            cur.execute(
                """
                SELECT metadata_json
                FROM memories
                WHERE id = %s::uuid
                """,
                (memory_id,),
            )
            deleted_metadata = cur.fetchone()["metadata_json"]
        assert {row["review_status"] for row in invalidated_dispositions} == {"candidate"}
        assert deleted_metadata["occurrence_proposal"]["materialization_status"] == "accepted"
        delete_coverage = store.get_occurrence_coverage()
        assert delete_coverage is not None
        assert delete_coverage["review_receipt_digest"] is None

        reactivated = admit_memory_candidate(
            legacy,
            user_id=owner_id,
            candidate=MemoryCandidateInput(
                memory_key="phase6.legacy.museum",
                value={"museum": "second"},
                source_event_ids=(second_event["id"],),
            ),
        )
        assert reactivated.action == "UPDATE"
        reactivated_memory = store.get_memory_for_redaction(memory_id)
        assert reactivated_memory is not None
        reactivated_metadata = dict(reactivated_memory["metadata_json"])
        assert "occurrence_proposal" not in reactivated_metadata
        assert "source_chunk_id" in reactivated_metadata
        assert reactivated_metadata["occurrence_invalidation"]["action"] == "UPDATE"


def test_legacy_admission_refreshes_shared_occurrence_survivor(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    owner_id = _seed_user(app_url, label="legacy-shared-survivor")

    with user_connection(app_url, owner_id) as conn:
        legacy = ContinuityStore(conn)
        thread = legacy.create_thread("Legacy shared occurrence")
        session = legacy.create_session(thread["id"], status="active")
        source_event = legacy.append_event(
            thread["id"],
            session["id"],
            "message.user",
            {"text": "I attended one workshop."},
        )
        memories: list[dict[str, object]] = []
        for index in (1, 2):
            decision = admit_memory_candidate(
                legacy,
                user_id=owner_id,
                candidate=MemoryCandidateInput(
                    memory_key=f"phase6.legacy.workshop.{index}",
                    value={"workshop": "same", "carrier": index},
                    source_event_ids=(source_event["id"],),
                ),
            )
            assert decision.memory is not None
            memories.append(dict(decision.memory))

        store = PostgresVNextStore(conn)
        full_memories = [
            store.update_memory(
                memory_id=str(memory["id"]),
                patch={
                    "canonical_text": "I attended one workshop.",
                    "domain": "personal",
                    "sensitivity": "private",
                },
                actor_type="user",
            )
            for memory in memories
        ]
        claim, _ = store.get_or_create_occurrence_claim(
            {
                "claim_key": f"phase6.legacy-shared-claim.{uuid4()}",
                "count_key": "attended workshop",
                "predicate_json": _predicate("attend", "workshop"),
                "canonical_text": "I attended one workshop.",
                "quantity_min": 1,
                "quantity_max": 1,
                "range_kind": "exact",
                "resolution_decision": "new",
                "identity_basis": "exact_time",
                "aggregation_json": _claim_aggregation(),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": full_memories[0]["domain"],
                "sensitivity": full_memories[0]["sensitivity"],
                "project_scope": full_memories[0].get("project_scope") or [],
            }
        )
        occurrence_key = f"phase6.legacy-shared-unit.{uuid4()}"
        unit, _ = store.get_or_create_occurrence_unit(
            {
                "claim_id": claim["id"],
                "claim_ordinal": 1,
                "occurrence_key": occurrence_key,
                "count_key": "attended workshop",
                "predicate_json": _predicate("attend", "workshop"),
                "canonical_text": "I attended one workshop.",
                "identity_status": "resolved",
                "aggregation_json": _unit_aggregation(occurrence_key),
                "occurred_at_start": "2026-07-24T12:00:00Z",
                "occurred_at_end": "2026-07-24T12:00:00Z",
                "domain": full_memories[0]["domain"],
                "sensitivity": full_memories[0]["sensitivity"],
                "project_scope": full_memories[0].get("project_scope") or [],
            }
        )
        evidence_rows = [
            store.create_occurrence_evidence(
                {
                    "claim_id": claim["id"],
                    "occurrence_id": unit["id"],
                    "memory_id": memory["id"],
                    "evidence_key": f"phase6.legacy-shared-evidence.{index}.{uuid4()}",
                    "quote": "I attended one workshop.",
                }
            )
            for index, memory in enumerate(full_memories, start=1)
        ]
        store.review_occurrence_claim(
            claim_id=str(claim["id"]),
            resolution_status="resolved",
            resolution_decision="new",
            identity_basis="exact_time",
            reviewer_id="phase6-reviewer",
            reason="The shared legacy occurrence identity was reviewed.",
        )
        unit = store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            expected_status="candidate",
            expected_review_version=int(unit["review_version"]),
            reviewer_id="phase6-reviewer",
            reason="Both legacy memory carriers support one reviewed occurrence.",
        )
        old_unit_receipt = unit["review_receipt_digest"]
        old_unit_version = int(unit["review_version"])
        coverage = store.ensure_occurrence_coverage(
            started_at="2026-01-01T00:00:00Z",
        )
        coverage = store.review_occurrence_coverage(
            coverage_mode="partial_history",
            historical_review_status="reviewed",
            coverage_started_at="2026-01-01T00:00:00Z",
            complete_through="2026-07-24T23:59:59Z",
            reviewer_id="phase6-reviewer",
            reason="The shared legacy occurrence fixture was reviewed.",
            expected_review_version=int(coverage["review_version"]),
        )
        signed_coverage_version = int(coverage["review_version"])

        changed = admit_memory_candidate(
            legacy,
            user_id=owner_id,
            candidate=MemoryCandidateInput(
                memory_key="phase6.legacy.workshop.1",
                value={"workshop": "different", "carrier": 1},
                source_event_ids=(source_event["id"],),
            ),
        )
        assert changed.action == "UPDATE"

        survivor = store.get_occurrence_unit_by_key(occurrence_key)
        assert survivor is not None
        assert survivor["review_status"] == "accepted"
        assert int(survivor["review_version"]) == old_unit_version + 1
        assert survivor["review_receipt_digest"] != old_unit_receipt
        assert store.get_occurrence_claim(str(claim["id"]))["review_status"] == "accepted"
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text AS id, review_status, review_receipt_digest,
                       unit_review_receipt_digest
                FROM occurrence_evidence
                WHERE id = ANY(%s::uuid[])
                ORDER BY id
                """,
                ([str(row["id"]) for row in evidence_rows],),
            )
            persisted_evidence = {
                row["id"]: row for row in cur.fetchall()
            }
        detached = persisted_evidence[str(evidence_rows[0]["id"])]
        surviving = persisted_evidence[str(evidence_rows[1]["id"])]
        assert detached["review_status"] == "rejected"
        assert detached["unit_review_receipt_digest"] is None
        assert surviving["review_status"] == "accepted"
        assert surviving["review_receipt_digest"] is not None
        assert surviving["unit_review_receipt_digest"] == survivor["review_receipt_digest"]
        invalidated_coverage = store.get_occurrence_coverage()
        assert invalidated_coverage is not None
        assert int(invalidated_coverage["review_version"]) == signed_coverage_version + 1
        assert invalidated_coverage["review_receipt_digest"] is None
