"""Focused Phase 6 guards for the LongMemEval development adapter."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sys
from uuid import uuid4

import pytest


_EVAL_DIR = Path(__file__).resolve().parent.parent
_API_SRC = _EVAL_DIR.parent / "apps" / "api" / "src"
for _path in (_EVAL_DIR, _API_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from alicebot_api.sqlite_store import (  # noqa: E402
    SQLiteVNextStore,
    ensure_sqlite_user,
    sqlite_user_connection,
)
from alicebot_api.vnext_capture import (  # noqa: E402
    SourceCaptureInput,
    VNextCaptureService,
)
from alicebot_api.vnext_memory_commit import VNextMemoryCommitService  # noqa: E402
from alicebot_api.vnext_occurrence_write import (  # noqa: E402
    review_source_chunk_occurrences,
)
from longmemeval import adapter  # noqa: E402
from longmemeval.dataset import LongMemEvalQuestion, parse_question  # noqa: E402


@pytest.fixture(autouse=True)
def _no_ambient_model_config(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ALICE_EMBEDDINGS_BASE_URL",
        "ALICE_EMBEDDINGS_MODEL",
        "ALICE_EMBEDDINGS_API_KEY",
        "ALICE_RERANKER_BASE_URL",
        "ALICE_RERANKER_MODEL",
        "ALICE_RERANKER_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _question(
    *,
    dates: tuple[str, ...] = (
        "2023/06/01 (Thu) 10:00",
        "2023/05/01 (Mon) 09:30",
    ),
    contents: tuple[str, ...] = (
        (
            "I visited the Louvre in Paris on 2023-05-30 with my friend "
            "Alice, and the visit was an unforgettable afternoon."
        ),
        ("I visited the Prado in Madrid on 2023-04-30 with my brother, and the visit was an unforgettable morning."),
    ),
) -> LongMemEvalQuestion:
    session_ids = [f"session-{index}" for index in range(len(dates))]
    return parse_question(
        {
            "question_id": "phase6-adapter-question",
            "question_type": "multi-session",
            "question": "BENCHMARK QUESTION MUST NOT ENTER OCCURRENCE WRITES",
            "answer": "BENCHMARK GOLD MUST NOT ENTER OCCURRENCE WRITES",
            "question_date": "2023/07/01 (Sat) 12:00",
            "haystack_dates": list(dates),
            "haystack_session_ids": session_ids,
            "haystack_sessions": [[{"role": "user", "content": content}] for content in contents],
            "answer_session_ids": ["BENCHMARK ANSWER SESSION LABEL MUST NOT ENTER OCCURRENCE WRITES"],
        }
    )


def _bootstrap_existing_store(path: Path) -> None:
    with sqlite_user_connection(path, adapter.LME_USER_ID) as conn:
        ensure_sqlite_user(
            conn,
            adapter.LME_USER_ID,
            adapter.LME_USER_EMAIL,
            "LongMemEval Harness",
        )
        store = SQLiteVNextStore(conn, adapter.LME_USER_ID)
        store.ensure_occurrence_coverage(
            started_at="2023-01-01T00:00:00Z",
            actor_type="system",
        )


def _json_object(value: object) -> dict[str, object]:
    if isinstance(value, str):
        value = json.loads(value)
    assert isinstance(value, dict)
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_occurrence_snapshot(
    run: adapter.QuestionRun,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Semantic graph digest with generated row IDs and receipts normalized."""

    source_rows = list(run.store.conn.execute("SELECT * FROM sources"))
    source_nodes: dict[str, dict[str, object]] = {}
    for row in source_rows:
        source_id = str(row["id"])
        metadata = _json_object(row["metadata_json"])
        external_id = str(row["external_id"])
        match = re.fullmatch(r"session-(\d{6})-([0-9a-f]{64})", external_id)
        assert match is not None
        assert int(match.group(1)) == metadata["session_ordinal"]
        assert match.group(2) == metadata["source_content_sha256"]
        assert "question_id" not in metadata
        source_nodes[source_id] = {
            "external_id": external_id,
            "content_hash": str(row["content_hash"]),
            "session_ordinal": metadata["session_ordinal"],
            "source_content_sha256": metadata["source_content_sha256"],
            "session_id": metadata["session_id"],
            "session_date": metadata["session_date"],
        }

    chunk_rows = list(run.store.conn.execute("SELECT * FROM source_chunks"))
    chunk_nodes: dict[str, dict[str, object]] = {}
    for row in chunk_rows:
        chunk_nodes[str(row["id"])] = {
            "source": source_nodes[str(row["source_id"])]["external_id"],
            "chunk_index": row["chunk_index"],
            "text_sha256": hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest(),
        }

    memory_nodes = {
        str(row["id"]): {
            "canonical_text": str(row["canonical_text"]),
            "status": str(row["status"]),
        }
        for row in run.store.conn.execute("SELECT id, canonical_text, status FROM memories")
    }

    predicate_digests: list[str] = []
    aggregation_digests: list[str] = []
    claim_nodes: dict[str, dict[str, object]] = {}
    for row in run.store.conn.execute("SELECT * FROM occurrence_claims"):
        predicate = _json_object(row["predicate_json"])
        aggregation = _json_object(row["aggregation_json"])
        predicate_digest = _canonical_digest(predicate)
        aggregation_digest = _canonical_digest(aggregation)
        predicate_digests.append(predicate_digest)
        aggregation_digests.append(aggregation_digest)
        claim_nodes[str(row["id"])] = {
            "count_key": str(row["count_key"]),
            "canonical_text": str(row["canonical_text"]),
            "predicate_digest": predicate_digest,
            "aggregation_digest": aggregation_digest,
            "quantity_min": row["quantity_min"],
            "quantity_max": row["quantity_max"],
            "range_kind": str(row["range_kind"]),
            "resolution_decision": str(row["resolution_decision"]),
            "resolution_status": str(row["resolution_status"]),
            "identity_basis": str(row["identity_basis"]),
            "review_status": str(row["review_status"]),
            "occurred_at_start": row["occurred_at_start"],
            "occurred_at_end": row["occurred_at_end"],
        }

    unit_nodes: dict[str, dict[str, object]] = {}
    for row in run.store.conn.execute("SELECT * FROM occurrence_units"):
        predicate = _json_object(row["predicate_json"])
        aggregation = _json_object(row["aggregation_json"])
        predicate_digest = _canonical_digest(predicate)
        aggregation_digest = _canonical_digest(aggregation)
        predicate_digests.append(predicate_digest)
        aggregation_digests.append(aggregation_digest)
        unit_nodes[str(row["id"])] = {
            "claim": claim_nodes[str(row["claim_id"])],
            "claim_ordinal": row["claim_ordinal"],
            "occurrence_key": str(row["occurrence_key"]),
            "count_key": str(row["count_key"]),
            "canonical_text": str(row["canonical_text"]),
            "predicate_digest": predicate_digest,
            "aggregation_digest": aggregation_digest,
            "unit_value": row["unit_value"],
            "review_status": str(row["review_status"]),
            "identity_status": str(row["identity_status"]),
            "occurred_at_start": row["occurred_at_start"],
            "occurred_at_end": row["occurred_at_end"],
            "retired": row["retired_at"] is not None,
        }

    evidence_nodes: list[dict[str, object]] = []
    for row in run.store.conn.execute("SELECT * FROM occurrence_evidence"):
        occurrence_id = str(row["occurrence_id"] or "")
        source_id = str(row["source_id"] or "")
        chunk_id = str(row["source_chunk_id"] or "")
        memory_id = str(row["memory_id"] or "")
        evidence_nodes.append(
            {
                "claim": claim_nodes[str(row["claim_id"])],
                "occurrence": unit_nodes.get(occurrence_id),
                "source": source_nodes.get(source_id),
                "source_chunk": chunk_nodes.get(chunk_id),
                "memory": memory_nodes.get(memory_id),
                "evidence_role": str(row["evidence_role"]),
                "quote_sha256": str(row["quote_sha256"]),
                "confidence": row["confidence"],
                "review_status": str(row["review_status"]),
            }
        )

    graph = {
        "sources": sorted(source_nodes.values(), key=_canonical_json),
        "source_chunks": sorted(chunk_nodes.values(), key=_canonical_json),
        "claims": sorted(claim_nodes.values(), key=_canonical_json),
        "units": sorted(unit_nodes.values(), key=_canonical_json),
        "evidence": sorted(evidence_nodes, key=_canonical_json),
    }
    return (
        _canonical_digest(graph),
        tuple(sorted(predicate_digests)),
        tuple(sorted(aggregation_digests)),
    )


def _canonical_returned_occurrence_aggregation(
    run: adapter.QuestionRun,
    value: object,
) -> dict[str, object]:
    """Project answer semantics while replacing generated row identities."""

    aggregation = _json_object(value)
    sources: dict[str, dict[str, object]] = {}
    for row in run.store.conn.execute("SELECT id, external_id, content_hash, metadata_json FROM sources"):
        metadata = _json_object(row["metadata_json"])
        sources[str(row["id"])] = {
            "external_id": str(row["external_id"]),
            "content_hash": str(row["content_hash"]),
            "source_content_sha256": metadata.get("source_content_sha256"),
        }
    chunks = {
        str(row["id"]): {
            "source": sources[str(row["source_id"])],
            "chunk_index": row["chunk_index"],
            "text_sha256": hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest(),
        }
        for row in run.store.conn.execute("SELECT id, source_id, chunk_index, text FROM source_chunks")
    }
    memories = {
        str(row["id"]): {
            "canonical_text_sha256": hashlib.sha256(str(row["canonical_text"]).encode("utf-8")).hexdigest(),
            "status": str(row["status"]),
        }
        for row in run.store.conn.execute("SELECT id, canonical_text, status FROM memories")
    }
    units = {
        str(row["id"]): str(row["occurrence_key"])
        for row in run.store.conn.execute("SELECT id, occurrence_key FROM occurrence_units")
    }

    provenance: list[dict[str, object]] = []
    raw_provenance = aggregation.get("provenance", [])
    assert isinstance(raw_provenance, list)
    for raw_item in raw_provenance:
        item = _json_object(raw_item)
        raw_evidence = item.get("evidence", [])
        assert isinstance(raw_evidence, list)
        evidence: list[dict[str, object]] = []
        for raw_row in raw_evidence:
            row = _json_object(raw_row)
            source_id = str(row.get("source_id") or "")
            source_chunk_id = str(row.get("source_chunk_id") or "")
            memory_id = str(row.get("memory_id") or "")
            evidence.append(
                {
                    "evidence_role": row.get("evidence_role"),
                    "quote_sha256": row.get("quote_sha256"),
                    "review_status": row.get("review_status"),
                    "source": sources.get(source_id),
                    "source_chunk": chunks.get(source_chunk_id),
                    "memory": memories.get(memory_id),
                }
            )
        unit_id = str(item.get("occurrence_unit_id") or "")
        provenance.append(
            {
                "occurrence_key": units.get(unit_id),
                "counted_member_keys": sorted(str(key) for key in item.get("counted_member_keys", [])),
                "reviewed_evidence_count": item.get("reviewed_evidence_count"),
                "evidence": sorted(evidence, key=_canonical_json),
            }
        )

    raw_coverage = aggregation.get("coverage")
    assert isinstance(raw_coverage, dict)
    coverage = {
        key: raw_coverage.get(key)
        for key in (
            "coverage_mode",
            "historical_review_status",
            "complete_through",
            "fully_covered",
            "legacy_gap",
            "receipt_valid",
            "requested_start",
            "requested_end",
        )
    }
    canonical: dict[str, object] = {
        key: aggregation.get(key)
        for key in (
            "kind",
            "aggregation_basis",
            "answer_kind",
            "answer_sufficient",
            "exact",
            "count",
            "lower_bound",
            "upper_bound",
            "unit",
            "saturated",
            "unit_count",
            "counted_member_count",
        )
    }
    canonical.update(
        {
            "counted_member_keys": sorted(str(key) for key in aggregation.get("counted_member_keys", [])),
            "occurrence_keys": sorted(units[str(unit_id)] for unit_id in aggregation.get("occurrence_unit_ids", [])),
            "coverage": coverage,
            "unresolved_claims": aggregation.get("unresolved_claims"),
            "provenance": sorted(provenance, key=_canonical_json),
        }
    )
    for key in (
        "formula",
        "query_predicate",
        "query_predicates",
        "query_selector_keys",
        "selector_keys",
        "taxonomy",
    ):
        if key in aggregation:
            canonical[key] = aggregation[key]
    return canonical


def test_freshness_probe_rejects_sqlite_sidecars_and_non_filesystem_stores(
    tmp_path: Path,
) -> None:
    path = tmp_path / "question.sqlite3"
    assert adapter._sqlite_store_file_family_was_absent(path)
    sidecar = Path(f"{path}-mjDEADBEEF")
    sidecar.write_text("stale super-journal", encoding="utf-8")
    assert not adapter._sqlite_store_file_family_was_absent(path)
    assert not adapter._sqlite_store_file_family_was_absent(":memory:")
    assert not adapter._sqlite_store_file_family_was_absent("file:question.sqlite3?mode=memory")


def test_capture_alone_leaves_direct_source_occurrences_unreviewed(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capture-only.sqlite3"
    with sqlite_user_connection(path, adapter.LME_USER_ID) as conn:
        ensure_sqlite_user(
            conn,
            adapter.LME_USER_ID,
            adapter.LME_USER_EMAIL,
            "LongMemEval Harness",
        )
        store = SQLiteVNextStore(conn, adapter.LME_USER_ID)
        result = VNextCaptureService(store).capture_source(
            SourceCaptureInput(
                source_type=adapter.SOURCE_TYPE,
                raw_text="[USER]: I visited the museum on March 3, 2026.",
                domain=adapter.SOURCE_DOMAIN,
                sensitivity=adapter.SOURCE_SENSITIVITY,
                metadata_json={"session_date": "2026-03-05T12:00:00Z"},
            )
        )
        assert result.source_id is not None
        chunks = store.list_source_chunks(result.source_id)
        assert len(chunks) == 1
        claims = store.list_occurrence_claims_for_source_chunk(
            str(chunks[0]["id"]),
            limit=200,
        )
        assert len(claims) == 1
        predicate = _json_object(claims[0]["predicate_json"])
        units = store.list_occurrence_units_for_claim(str(claims[0]["id"]))
        assert len(units) == 1
        evidence = [
            dict(row)
            for row in store.conn.execute(
                """
                SELECT
                  occurrence_id,
                  memory_id,
                  source_id,
                  source_chunk_id,
                  review_status
                FROM occurrence_evidence
                WHERE user_id = ?
                  AND claim_id = ?
                ORDER BY id ASC
                """,
                (store.user_id, str(claims[0]["id"])),
            )
        ]
        accounting = store.summarize_occurrence_extraction_accounting(
            extractor_version=adapter.OCCURRENCE_EXTRACTOR_VERSION,
            source_ids=None,
        )
        coverage = store.get_occurrence_coverage()
        assert store.search_memories(query="museum", limit=20) == []
        assert store.search_memories_fts(query="museum", limit=20) == []

    assert claims[0]["count_key"] == "visited museum"
    assert predicate["action"] == {"leaf": "visited", "ancestors": []}
    assert predicate["selector_keys"] == [
        "v1|a=exact:visited|o=exact:museum",
        "v1|a=exact:visited|o=*",
    ]
    assert claims[0]["review_status"] == "candidate"
    assert claims[0]["resolution_status"] == "pending"
    assert units[0]["review_status"] == "candidate"
    assert len(evidence) == 1
    assert evidence[0]["review_status"] == "candidate"
    assert evidence[0]["source_id"] == result.source_id
    assert evidence[0]["source_chunk_id"] == chunks[0]["id"]
    assert evidence[0]["memory_id"] is None
    assert accounting["complete"] is False
    assert accounting["reviewed_current_count"] == 0
    assert accounting["unreviewed_count"] == 1
    assert accounting["items"][0]["disposition"] == "unresolved_claims"
    assert accounting["items"][0]["review_status"] == "candidate"
    assert coverage is not None
    assert coverage["coverage_mode"] == "forward_only"
    assert coverage["historical_review_status"] == "not_reviewed"


def test_structured_memory_links_reviewed_direct_source_event_without_duplication(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source-memory-collision.sqlite3"
    canonical_text = "I visited the museum."
    predicate = {
        "schema": "occurrence_predicate_v1",
        "taxonomy": "alice-occurrence-exact-v1",
        "op": "atom",
        "subject": "self",
        "polarity": "completed",
        "action": {"leaf": "visit", "ancestors": []},
        "object": {
            "leaf": "museum",
            "qualifiers": [],
            "ancestors": [],
        },
        "selector_keys": [
            "v1|a=exact:visit|o=exact:museum",
            "v1|a=exact:visit|o=*",
        ],
        "closure_complete": False,
    }
    aggregation = {
        "schema": "occurrence_aggregation_v1",
        "bases": [
            {
                "basis": "event_instance",
                "identity_basis": "occurrence_key",
            }
        ],
    }
    occurrence_input = {
        "count_key": "visit museum",
        "predicate_json": predicate,
        "aggregation_json": aggregation,
        "external_event_id": "phase6-source-memory-shared-event",
        "external_event_namespace": "longmemeval:test",
        "quantity_min": 1,
        "quantity_max": 1,
    }
    with sqlite_user_connection(path, adapter.LME_USER_ID) as conn:
        ensure_sqlite_user(
            conn,
            adapter.LME_USER_ID,
            adapter.LME_USER_EMAIL,
            "LongMemEval Harness",
        )
        store = SQLiteVNextStore(conn, adapter.LME_USER_ID)
        captured = VNextCaptureService(store).capture_source(
            SourceCaptureInput(
                source_type=adapter.SOURCE_TYPE,
                raw_text=canonical_text,
                domain=adapter.SOURCE_DOMAIN,
                sensitivity=adapter.SOURCE_SENSITIVITY,
                metadata_json={
                    "session_date": "2026-03-05T12:00:00Z",
                    "provenance_role": "user",
                    "occurrence_inputs": [
                        {
                            **occurrence_input,
                            "canonical_text": canonical_text,
                        }
                    ],
                },
            )
        )
        assert captured.source_id is not None
        chunk = store.list_source_chunks(captured.source_id)[0]
        direct_claim = store.list_occurrence_claims_for_source_chunk(
            str(chunk["id"]),
            limit=200,
        )[0]
        direct_units = store.list_occurrence_units_for_claim(
            str(direct_claim["id"]),
        )
        assert len(direct_units) == 1
        direct_unit_id = str(direct_units[0]["id"])
        assert direct_units[0]["review_status"] == "candidate"

        reviewed_claim_ids = review_source_chunk_occurrences(
            store,
            source_chunk_id=str(chunk["id"]),
            reviewer_id=adapter.OCCURRENCE_COVERAGE_REVIEWER,
            reason=adapter.OCCURRENCE_COVERAGE_REASON,
            actor_type="system",
            stage="test_direct_source_review",
        )
        assert reviewed_claim_ids == [str(direct_claim["id"])]
        direct_units = store.list_occurrence_units_for_claim(
            str(direct_claim["id"]),
        )
        assert len(direct_units) == 1
        assert direct_units[0]["id"] == direct_unit_id
        assert direct_units[0]["review_status"] == "accepted"

        memory = store.create_memory(
            {
                "memory_key": f"phase6.source-memory-collision.{uuid4()}",
                "value": {"text": canonical_text},
                "status": "active",
                "memory_type": "semantic",
                "title": "Structured museum visit",
                "canonical_text": canonical_text,
                "summary": canonical_text,
                "domain": adapter.SOURCE_DOMAIN,
                "sensitivity": adapter.SOURCE_SENSITIVITY,
                "metadata_json": {
                    "occurrence_input": occurrence_input,
                },
            },
            actor_type="system",
        )
        reconciled = VNextMemoryCommitService(
            store,
        ).reconcile_memory_occurrence_state(
            memory,
            stage="test_structured_memory_review",
        )
        proposal = reconciled["metadata_json"]["occurrence_proposal"]
        all_units = [dict(row) for row in store.conn.execute("SELECT * FROM occurrence_units ORDER BY id ASC")]
        evidence = store.list_occurrence_evidence_for_units([direct_unit_id])

    assert proposal["resolution_decision"] == "link_existing"
    assert proposal["materialization_status"] == "linked_existing"
    assert proposal["occurrence_unit_ids"] == [direct_unit_id]
    assert len(all_units) == 1
    assert all_units[0]["id"] == direct_unit_id
    assert all_units[0]["review_status"] == "accepted"
    assert len(evidence) == 2
    assert {row["occurrence_id"] for row in evidence} == {direct_unit_id}
    assert {row["review_status"] for row in evidence} == {"accepted"}
    assert sum(row["source_id"] is not None for row in evidence) == 1
    assert sum(row["memory_id"] is not None for row in evidence) == 1
    assert all((row["source_id"] is None) != (row["memory_id"] is None) for row in evidence)
    assert {str(row["source_id"]) for row in evidence if row["source_id"] is not None} == {str(captured.source_id)}
    assert {str(row["memory_id"]) for row in evidence if row["memory_id"] is not None} == {str(memory["id"])}


def test_occurrence_graph_is_independent_of_randomized_benchmark_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = replace(
        _question(
            dates=(
                "2023/05/01 (Mon) 09:30",
                "2023/06/01 (Thu) 10:00",
            ),
            contents=(
                "I visited the Louvre in Paris on 2023-04-30.",
                "I visited the Louvre in Paris on 2023-05-30.",
            ),
        ),
        question="How many times have I visited the Louvre?",
    )
    snapshots: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
    aggregations: list[dict[str, object]] = []
    forbidden_by_run: list[tuple[str, str, str]] = []
    serialized_outputs: list[str] = []
    packs: list[dict[str, object]] = []
    original = adapter.VNextRetrievalService.compile_context_pack

    def record_pack(
        service: object,
        request: object,
    ) -> dict[str, object]:
        pack = original(service, request)
        packs.append(pack)
        return pack

    monkeypatch.setattr(
        adapter.VNextRetrievalService,
        "compile_context_pack",
        record_pack,
    )
    for run_index in range(2):
        question_id = f"random-question-{uuid4()}"
        gold = f"random-gold-{uuid4()}"
        answer_session_id = f"random-answer-session-{uuid4()}"
        question = replace(
            base,
            question_id=question_id,
            answer=gold,
            answer_session_ids=(answer_session_id,),
        )
        with adapter.question_run(question, tmp_path / f"run-{run_index}.sqlite3") as run:
            stats = run.ingest()
            run.retrieve(max_items=8, context_char_budget=12_000)
            assert stats.source_count == 2
            assert len(packs) == run_index + 1
            snapshots.append(_canonical_occurrence_snapshot(run))
            aggregation = packs[-1].get("aggregation")
            assert isinstance(aggregation, dict)
            aggregations.append(
                _canonical_returned_occurrence_aggregation(
                    run,
                    aggregation,
                )
            )
            assert snapshots[-1][1]
            assert snapshots[-1][2]
            persisted_dump = "\n".join(run.store.conn.iterdump())
            serialized_outputs.extend((persisted_dump, _canonical_json(packs[-1])))
        forbidden_by_run.append((question_id, gold, answer_session_id))

    assert snapshots[0] == snapshots[1]
    assert aggregations[0] == aggregations[1]
    assert all(
        aggregation["answer_kind"] == "exact"
        and aggregation["exact"] is True
        and aggregation["count"] == 2
        and aggregation["lower_bound"] == 2
        and aggregation["upper_bound"] == 2
        for aggregation in aggregations
    )
    forbidden_labels = {label for labels in forbidden_by_run for label in labels}
    assert all(label not in serialized for label in forbidden_labels for serialized in serialized_outputs)


def test_accounting_summary_must_cover_every_requested_source_and_chunk() -> None:
    summary_source_filters: list[tuple[str, ...] | None] = []
    summary: dict[str, object] = {
        "extractor_version": adapter.OCCURRENCE_EXTRACTOR_VERSION,
        "source_ids": ["source-a", "source-b"],
        "current_chunk_count": 1,
        "reviewed_current_count": 1,
        "missing_count": 0,
        "stale_count": 0,
        "unresolved_count": 0,
        "unreviewed_count": 0,
        "invalid_accepted_count": 0,
        "invalid_receipt_count": 0,
        "unanchored_memory_count": 0,
        "snapshot_digest": "a" * 64,
        "disposition_digest": "b" * 64,
        "complete": True,
        "items": [
            {
                "source_id": "source-a",
                "source_chunk_id": "chunk-a",
                "status": "complete",
            }
        ],
    }

    class SummaryStore:
        def summarize_occurrence_extraction_accounting(
            self,
            *,
            extractor_version: str,
            source_ids: tuple[str, ...] | None = None,
        ) -> dict[str, object]:
            assert extractor_version == adapter.OCCURRENCE_EXTRACTOR_VERSION
            summary_source_filters.append(source_ids)
            return summary

    run = adapter.QuestionRun(_question(), SummaryStore())  # type: ignore[arg-type]
    run._source_sessions = {
        "source-a": ("session-0", "2023/05/01 (Mon) 09:30"),
        "source-b": ("session-1", "2023/06/01 (Thu) 10:00"),
    }

    assert not run._occurrence_extraction_accounting_is_complete()
    summary.update(
        {
            "current_chunk_count": 0,
            "reviewed_current_count": 0,
            "items": [],
        }
    )
    assert not run._occurrence_extraction_accounting_is_complete()
    summary.update(
        {
            "current_chunk_count": 2,
            "reviewed_current_count": 2,
            "items": [
                {
                    "source_id": "source-b",
                    "source_chunk_id": "chunk-b",
                    "status": "complete_with_unresolved_claims",
                },
                {
                    "source_id": "source-a",
                    "source_chunk_id": "chunk-a",
                    "status": "complete",
                },
            ],
        }
    )
    assert run._complete_occurrence_accounting_metadata() == {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": adapter.OCCURRENCE_EXTRACTOR_VERSION,
        "source_ids": ["source-a", "source-b"],
        "source_chunk_ids": ["chunk-a", "chunk-b"],
        "snapshot_digest": "a" * 64,
        "disposition_digest": "b" * 64,
    }
    summary["items"][1]["source_chunk_id"] = "chunk-b"
    assert run._complete_occurrence_accounting_metadata() is None
    summary["items"][1]["source_chunk_id"] = "chunk-a"
    summary["source_ids"].append("source-c")
    assert run._complete_occurrence_accounting_metadata() is None
    assert summary_source_filters
    assert set(summary_source_filters) == {None}


def test_promotions_keep_central_review_while_source_occurrences_carry_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[dict[str, object], dict[str, object], dict[str, object]]] = []
    original = VNextMemoryCommitService.reconcile_memory_occurrence_state

    def recording_reconcile(
        self: VNextMemoryCommitService,
        memory: dict[str, object],
        **kwargs: object,
    ) -> dict[str, object]:
        reconciled = original(self, memory, **kwargs)
        calls.append((dict(memory), dict(kwargs), dict(reconciled)))
        return reconciled

    monkeypatch.setattr(
        VNextMemoryCommitService,
        "reconcile_memory_occurrence_state",
        recording_reconcile,
    )

    with adapter.question_run(_question(), tmp_path / "fresh.sqlite3") as run:
        stats = run.ingest()
        assert calls
        assert len(calls) == stats.promoted_memory_count
        accounting = run.store.summarize_occurrence_extraction_accounting(
            extractor_version=adapter.OCCURRENCE_EXTRACTOR_VERSION,
            source_ids=None,
        )
        claim_ids = {str(claim_id) for item in accounting["items"] for claim_id in item["claim_ids"]}
        occurrence_ids = {
            str(occurrence_id) for item in accounting["items"] for occurrence_id in item["occurrence_ids"]
        }
        claims = [
            claim for claim_id in sorted(claim_ids) if (claim := run.store.get_occurrence_claim(claim_id)) is not None
        ]
        units = [unit for claim_id in sorted(claim_ids) for unit in run.store.list_occurrence_units_for_claim(claim_id)]
        evidence = run.store.list_occurrence_evidence_for_units(
            sorted(occurrence_ids),
        )

        assert accounting["complete"] is True
        assert len(claims) == len(units) == len(evidence) == 2
        expected_natural_surfaces = {
            "visited louvre": [
                "v1|a=exact:visited|o=exact:louvre",
                "v1|a=exact:visited|o=*",
            ],
            "visited prado": [
                "v1|a=exact:visited|o=exact:prado",
                "v1|a=exact:visited|o=*",
            ],
        }
        assert {str(claim["count_key"]) for claim in claims} == set(expected_natural_surfaces)
        for claim in claims:
            predicate = _json_object(claim["predicate_json"])
            assert predicate["action"] == {
                "leaf": "visited",
                "ancestors": [],
            }
            assert predicate["selector_keys"] == expected_natural_surfaces[str(claim["count_key"])]
        assert {claim["review_status"] for claim in claims} == {"accepted"}
        assert {claim["resolution_status"] for claim in claims} == {"resolved"}
        assert {unit["review_status"] for unit in units} == {"accepted"}
        assert {unit["identity_status"] for unit in units} == {"resolved"}
        assert {unit["unit_value"] for unit in units} == {1}
        assert all(
            row["review_status"] == "accepted"
            and row["source_id"] is not None
            and row["source_chunk_id"] is not None
            and row["memory_id"] is None
            for row in evidence
        )
        for memory, kwargs, reconciled in calls:
            assert memory["status"] == "active"
            assert kwargs == {"stage": "longmemeval_review_accept"}
            assert "occurrence_proposal" not in reconciled["metadata_json"]
            assert run.store.list_occurrence_units_for_memory(str(memory["id"])) == []
            serialized = repr(
                (
                    memory,
                    reconciled,
                    accounting,
                    claims,
                    units,
                    evidence,
                )
            )
            assert "BENCHMARK QUESTION MUST NOT ENTER OCCURRENCE WRITES" not in serialized
            assert "BENCHMARK GOLD MUST NOT ENTER OCCURRENCE WRITES" not in serialized
            assert "BENCHMARK ANSWER SESSION LABEL MUST NOT ENTER OCCURRENCE WRITES" not in serialized


def test_long_user_turn_preserves_late_source_occurrence_without_fragment_memory_fanout(
    tmp_path: Path,
) -> None:
    late_event = (
        "I visited the Louvre in Paris on 2023-05-30 with my friend "
        "Alice, and the visit was an unforgettable afternoon."
    )
    internal_lines = [
        "I paid $10 for entry.",
        *(f"This detail is context segment {index}. " + ("background " * 28).strip() + "." for index in range(12)),
        late_event,
    ]
    content = "\n".join(internal_lines)
    question = _question(
        dates=("2023/06/01 (Thu) 10:00",),
        contents=(content,),
    )
    rendered = adapter.render_session_text(
        "session-0",
        question.haystack_dates[0],
        question.haystack_sessions[0],
    )

    assert rendered.index(late_event) > 2_400
    assert rendered.count("[USER]: ") > 1
    assert all("\n" not in paragraph for paragraph in rendered.split("\n\n")[1:])

    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        stats = run.ingest()
        source_id = next(iter(run._source_sessions))
        chunks = run.store.list_source_chunks(source_id)
        late_chunk = next(chunk for chunk in chunks if late_event in str(chunk["text"]))
        claims = run.store.list_occurrence_claims_for_source_chunk(str(late_chunk["id"]))
        louvre_claim = next(claim for claim in claims if claim["count_key"] == "visited louvre")
        units = run.store.list_occurrence_units_for_claim(str(louvre_claim["id"]))
        evidence = run.store.list_occurrence_evidence_for_units([str(unit["id"]) for unit in units])

        assert stats.chunk_count == 3
        assert stats.candidate_memory_count == stats.promoted_memory_count == 3
        assert int(late_chunk["chunk_index"]) > 0
        assert louvre_claim["review_status"] == "accepted"
        assert louvre_claim["resolution_status"] == "resolved"
        assert len(units) == 1
        assert units[0]["review_status"] == "accepted"
        assert units[0]["identity_status"] == "resolved"
        assert evidence
        assert all(
            row["source_id"] == source_id
            and row["source_chunk_id"] == late_chunk["id"]
            and row["memory_id"] is None
            and row["review_status"] == "accepted"
            for row in evidence
        )


def test_occurrence_reconciliation_keeps_promotion_model_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_flags: list[bool] = []

    def record_fact_key_mode(
        store: object,
        memory: dict[str, object],
        *,
        use_env_provider: bool,
    ) -> None:
        del store, memory
        provider_flags.append(use_env_provider)

    monkeypatch.setattr(
        adapter,
        "attach_memory_fact_keys",
        record_fact_key_mode,
    )
    with adapter.question_run(_question(), tmp_path / "fresh.sqlite3") as run:
        stats = run.ingest()

    assert stats.promoted_memory_count > 0
    assert provider_flags == [False] * stats.promoted_memory_count


def test_adapter_retrieve_emits_signed_exact_occurrence_aggregation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = replace(
        _question(
            dates=(
                "2023/05/01 (Mon) 09:30",
                "2023/06/01 (Thu) 10:00",
            ),
            contents=(
                ("I visited the Louvre in Paris on 2023-04-30, and the visit was an unforgettable morning."),
                ("I visited the Louvre in Paris on 2023-05-30, and the visit was an unforgettable afternoon."),
            ),
        ),
        question="How many times have I visited the Louvre?",
        answer="BENCHMARK GOLD 999 MUST NOT ENTER OCCURRENCE RETRIEVAL",
        answer_session_ids=("BENCHMARK ANSWER IDS MUST NOT ENTER OCCURRENCE RETRIEVAL",),
    )
    packs: list[dict[str, object]] = []
    original = adapter.VNextRetrievalService.compile_context_pack

    def record_pack(
        service: object,
        request: object,
    ) -> dict[str, object]:
        pack = original(service, request)
        packs.append(pack)
        return pack

    monkeypatch.setattr(
        adapter.VNextRetrievalService,
        "compile_context_pack",
        record_pack,
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        stats = run.ingest()
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)

    assert stats.promoted_memory_count == 2
    assert outcome.memory_count >= 1
    assert len(packs) == 1
    assert "aggregation" in packs[0]
    aggregation = packs[0]["aggregation"]
    assert aggregation["kind"] == "occurrence_count"
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["exact"] is True
    assert aggregation["count"] == 2
    assert aggregation["lower_bound"] == aggregation["upper_bound"] == 2
    assert aggregation["answer_sufficient"] is True
    assert len(aggregation["occurrence_unit_ids"]) == 2
    assert len(aggregation["provenance"]) == 2
    assert aggregation["coverage"]["fully_covered"] is True
    assert aggregation["coverage"]["requested_end"] == "2023-07-01T12:00:00+00:00"
    serialized = repr(aggregation)
    assert "BENCHMARK GOLD 999 MUST NOT ENTER OCCURRENCE RETRIEVAL" not in serialized
    assert "BENCHMARK ANSWER IDS MUST NOT ENTER OCCURRENCE RETRIEVAL" not in serialized


def test_compound_unresolved_accounting_cannot_emit_false_exact_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = replace(
        _question(
            dates=(
                "2023/05/01 (Mon) 09:30",
                "2023/06/01 (Thu) 10:00",
            ),
            contents=(
                ("I visited the Louvre in Paris on 2023-04-30, and the visit was an unforgettable morning."),
                ("I visited the Louvre in Paris on 2023-05-30 and toured the Colosseum in Rome on 2023-05-31."),
            ),
        ),
        question="How many times have I visited the Louvre?",
        answer="BENCHMARK GOLD MUST NOT QUALIFY OCCURRENCE COVERAGE",
        answer_session_ids=("BENCHMARK ANSWER IDS MUST NOT QUALIFY OCCURRENCE COVERAGE",),
    )
    packs: list[dict[str, object]] = []
    original = adapter.VNextRetrievalService.compile_context_pack

    def record_pack(
        service: object,
        request: object,
    ) -> dict[str, object]:
        pack = original(service, request)
        packs.append(pack)
        return pack

    monkeypatch.setattr(
        adapter.VNextRetrievalService,
        "compile_context_pack",
        record_pack,
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        stats = run.ingest()
        coverage = run.store.get_occurrence_coverage()
        accounting = run.store.summarize_occurrence_extraction_accounting(
            extractor_version=adapter.OCCURRENCE_EXTRACTOR_VERSION,
            source_ids=None,
        )
        second_source_id = next(
            source_id for source_id, (session_id, _date) in run._source_sessions.items() if session_id == "session-1"
        )
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)

    assert stats.source_count == 2
    assert stats.chunk_count == 2
    assert stats.promoted_memory_count == stats.candidate_memory_count >= 1
    assert outcome.memory_count >= 1
    assert len(packs) == 1
    aggregation = packs[0].get("aggregation")
    assert isinstance(aggregation, dict)
    assert aggregation["kind"] == "occurrence_count"
    assert aggregation["answer_kind"] == "at_least"
    assert aggregation["exact"] is False
    assert aggregation["lower_bound"] == 1
    assert aggregation["upper_bound"] is None
    assert "count" not in aggregation
    assert aggregation["answer_sufficient"] is False
    assert coverage is not None
    assert coverage["coverage_mode"] == "complete_history"
    assert coverage["historical_review_status"] == "reviewed"
    second_item = next(item for item in accounting["items"] if item["source_id"] == second_source_id)
    assert second_item["status"] == "complete_with_unresolved_claims"
    assert second_item["disposition"] == "unresolved_claims"
    assert second_item["review_status"] == "accepted"
    serialized = repr((aggregation, accounting))
    assert "BENCHMARK GOLD MUST NOT QUALIFY OCCURRENCE COVERAGE" not in serialized
    assert "BENCHMARK ANSWER IDS MUST NOT QUALIFY OCCURRENCE COVERAGE" not in serialized


def test_affirmative_clause_is_accounted_before_exact_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = replace(
        _question(
            dates=(
                "2023/05/01 (Mon) 09:30",
                "2023/06/01 (Thu) 10:00",
            ),
            contents=(
                ("I visited the Louvre in Paris on 2023-04-30, and the visit was an unforgettable morning."),
                "I have visited the Louvre in Paris on 2023-05-30.",
            ),
        ),
        question="How many times have I visited the Louvre?",
        answer="BENCHMARK GOLD MUST NOT SIGN RAW-CLAUSE ACCOUNTING",
        answer_session_ids=("BENCHMARK ANSWER IDS MUST NOT SIGN RAW-CLAUSE ACCOUNTING",),
    )
    packs: list[dict[str, object]] = []
    original = adapter.VNextRetrievalService.compile_context_pack

    def record_pack(
        service: object,
        request: object,
    ) -> dict[str, object]:
        pack = original(service, request)
        packs.append(pack)
        return pack

    monkeypatch.setattr(
        adapter.VNextRetrievalService,
        "compile_context_pack",
        record_pack,
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        stats = run.ingest()
        coverage = run.store.get_occurrence_coverage()
        accounting = run.store.summarize_occurrence_extraction_accounting(
            extractor_version=adapter.OCCURRENCE_EXTRACTOR_VERSION,
            source_ids=None,
        )
        second_source_id = next(
            source_id for source_id, (session_id, _date) in run._source_sessions.items() if session_id == "session-1"
        )
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)

    assert stats.source_count == 2
    assert stats.chunk_count == 2
    assert stats.promoted_memory_count >= 1
    assert outcome.memory_count >= 1
    assert len(packs) == 1
    aggregation = packs[0].get("aggregation")
    assert isinstance(aggregation, dict)
    assert aggregation["kind"] == "occurrence_count"
    assert coverage is not None
    second_item = next(item for item in accounting["items"] if item["source_id"] == second_source_id)
    assert second_item["disposition"] != "no_occurrence"
    assert second_item["disposition"] == "accepted_occurrences"
    assert second_item["status"] == "complete"
    assert second_item["review_status"] == "accepted"
    assert second_item["occurrence_ids"]
    assert aggregation["answer_kind"] == "exact"
    assert aggregation["exact"] is True
    assert aggregation["count"] == 2
    assert aggregation["lower_bound"] == aggregation["upper_bound"] == 2
    assert aggregation["answer_sufficient"] is True
    assert coverage["coverage_mode"] == "complete_history"
    assert coverage["historical_review_status"] == "reviewed"
    serialized = repr((aggregation, accounting))
    assert "BENCHMARK GOLD MUST NOT SIGN RAW-CLAUSE ACCOUNTING" not in serialized
    assert "BENCHMARK ANSWER IDS MUST NOT SIGN RAW-CLAUSE ACCOUNTING" not in serialized


def test_novel_affirmative_clause_remains_unresolved_instead_of_no_occurrence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = replace(
        _question(
            dates=(
                "2023/05/01 (Mon) 09:30",
                "2023/06/01 (Thu) 10:00",
            ),
            contents=(
                ("I instructed a class on 2023-04-30, and the class was memorable."),
                "I taught a class on 2023-05-30.",
            ),
        ),
        question="How many times have I instructed a class?",
        answer="BENCHMARK GOLD MUST NOT SIGN NOVEL RAW CLAUSES",
        answer_session_ids=("BENCHMARK ANSWER IDS MUST NOT SIGN NOVEL RAW CLAUSES",),
    )
    packs: list[dict[str, object]] = []
    original = adapter.VNextRetrievalService.compile_context_pack

    def record_pack(
        service: object,
        request: object,
    ) -> dict[str, object]:
        pack = original(service, request)
        packs.append(pack)
        return pack

    monkeypatch.setattr(
        adapter.VNextRetrievalService,
        "compile_context_pack",
        record_pack,
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        stats = run.ingest()
        coverage = run.store.get_occurrence_coverage()
        accounting = run.store.summarize_occurrence_extraction_accounting(
            extractor_version=adapter.OCCURRENCE_EXTRACTOR_VERSION,
            source_ids=None,
        )
        first_source_id = next(
            source_id for source_id, (session_id, _date) in run._source_sessions.items() if session_id == "session-0"
        )
        second_source_id = next(
            source_id for source_id, (session_id, _date) in run._source_sessions.items() if session_id == "session-1"
        )
        first_item = next(item for item in accounting["items"] if item["source_id"] == first_source_id)
        assert len(first_item["claim_ids"]) == 1
        instructed_claim = run.store.get_occurrence_claim(str(first_item["claim_ids"][0]))
        assert instructed_claim is not None
        instructed_predicate = _json_object(instructed_claim["predicate_json"])
        outcome = run.retrieve(max_items=8, context_char_budget=12_000)

    assert stats.source_count == 2
    assert stats.chunk_count == 2
    assert stats.promoted_memory_count >= 1
    assert instructed_claim["count_key"] == "instructed class"
    assert instructed_predicate["action"] == {
        "leaf": "instructed",
        "ancestors": [],
    }
    assert instructed_predicate["selector_keys"] == [
        "v1|a=exact:instructed|o=exact:class",
        "v1|a=exact:instructed|o=*",
    ]
    assert outcome.memory_count >= 1
    assert len(packs) == 1
    aggregation = packs[0].get("aggregation")
    if aggregation is not None:
        assert isinstance(aggregation, dict)
        assert aggregation["kind"] == "occurrence_count"
        assert aggregation["answer_kind"] == "at_least"
        assert aggregation["exact"] is False
        assert aggregation["lower_bound"] == 1
        assert aggregation["upper_bound"] is None
        assert "count" not in aggregation
        assert aggregation["answer_sufficient"] is False
    assert coverage is not None
    assert coverage["coverage_mode"] == "forward_only"
    assert coverage["historical_review_status"] == "not_reviewed"
    second_item = next(item for item in accounting["items"] if item["source_id"] == second_source_id)
    assert second_item["status"] in {"unresolved", "unreviewed"}
    assert second_item["review_status"] == "candidate"
    assert not (second_item["disposition"] == "no_occurrence" and second_item["review_status"] == "accepted")
    serialized = repr((aggregation, accounting))
    assert "BENCHMARK GOLD MUST NOT SIGN NOVEL RAW CLAUSES" not in serialized
    assert "BENCHMARK ANSWER IDS MUST NOT SIGN NOVEL RAW CLAUSES" not in serialized


def test_fresh_isolated_store_gets_complete_history_from_session_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = _question(
        contents=(
            "Did I visit the museum this year?",
            "I did not visit the gallery this year.",
        )
    )
    requested_ends: list[object] = []

    def record_retrieval_end(
        service: object,
        request: object,
    ) -> dict[str, object]:
        del service
        requested_ends.append(request.reference_time)
        return {
            "relevant_memories": [],
            "sources": [],
            "trace": {},
            "warnings": [],
        }

    monkeypatch.setattr(
        adapter.VNextRetrievalService,
        "compile_context_pack",
        record_retrieval_end,
    )
    summary_source_filters: list[tuple[str, ...] | None] = []
    summaries_at_coverage_review: list[dict[str, object]] = []
    coverage_review_inputs: list[dict[str, object]] = []
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        summarize = run.store.summarize_occurrence_extraction_accounting
        review_coverage = run.store.review_occurrence_coverage
        observed_summaries: list[dict[str, object]] = []

        def record_summary(
            *,
            extractor_version: str,
            source_ids: tuple[str, ...] | None = None,
        ) -> dict[str, object]:
            summary_source_filters.append(source_ids)
            summary = summarize(
                extractor_version=extractor_version,
                source_ids=source_ids,
            )
            observed_summaries.append(summary)
            return summary

        def record_coverage_review(
            **kwargs: object,
        ) -> dict[str, object]:
            assert observed_summaries
            summaries_at_coverage_review.append(observed_summaries[-1])
            coverage_review_inputs.append(dict(kwargs))
            return review_coverage(**kwargs)

        monkeypatch.setattr(
            run.store,
            "summarize_occurrence_extraction_accounting",
            record_summary,
        )
        monkeypatch.setattr(
            run.store,
            "review_occurrence_coverage",
            record_coverage_review,
        )
        run.ingest()
        coverage = run.store.get_occurrence_coverage()
        expected_source_ids = sorted(run._source_sessions)
        assert summaries_at_coverage_review
        accounting = summaries_at_coverage_review[0]
        run.retrieve()

    assert coverage is not None
    assert coverage["coverage_mode"] == "complete_history"
    assert coverage["historical_review_status"] == "reviewed"
    assert coverage["coverage_started_at"] == "2023-05-01T09:30:00.000000Z"
    assert coverage["complete_through"] == "2023-07-01T12:00:00.000000Z"
    assert coverage["reviewer_id"] == adapter.OCCURRENCE_COVERAGE_REVIEWER
    assert coverage["review_reason"] == adapter.OCCURRENCE_COVERAGE_REASON
    expected_accounting_metadata = {
        "accounting_schema": "occurrence_accounting_v1",
        "extractor_version": adapter.OCCURRENCE_EXTRACTOR_VERSION,
        "source_ids": expected_source_ids,
        "source_chunk_ids": sorted(item["source_chunk_id"] for item in accounting["items"]),
        "snapshot_digest": accounting["snapshot_digest"],
        "disposition_digest": accounting["disposition_digest"],
    }
    assert summary_source_filters
    assert set(summary_source_filters) == {None}
    assert accounting["source_ids"] == expected_source_ids
    assert coverage_review_inputs
    assert coverage_review_inputs[0]["accounting_metadata"] == expected_accounting_metadata
    assert coverage["metadata_json"] == expected_accounting_metadata
    assert len(requested_ends) == 1
    assert requested_ends[0].isoformat() == "2023-07-01T12:00:00+00:00"


def test_existing_and_reused_stores_cannot_upgrade_occurrence_coverage(
    tmp_path: Path,
) -> None:
    path = tmp_path / "existing.sqlite3"
    _bootstrap_existing_store(path)
    question = _question(
        contents=(
            "Did I visit the museum this year?",
            "I did not visit the gallery this year.",
        )
    )

    with adapter.question_run(question, path) as run:
        run.ingest()
        existing = run.store.get_occurrence_coverage()
        assert existing is not None
        assert existing["coverage_mode"] == "forward_only"

    with adapter.question_run(question, path) as run:
        before = run.store.get_occurrence_coverage()
        run.ingest(reuse_store=True)
        after = run.store.get_occurrence_coverage()

    assert before == after == existing


def test_invalid_session_provenance_fails_closed_on_a_fresh_store(
    tmp_path: Path,
) -> None:
    question = _question(
        dates=("not-a-provenance-date",),
        contents=("I am considering a museum visit next year.",),
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        run.ingest()
        coverage = run.store.get_occurrence_coverage()

    assert coverage is None or coverage["coverage_mode"] == "forward_only"


@pytest.mark.parametrize(
    "question_date",
    (
        "not-a-question-date",
        "2023/04/30 (Sun) 08:00",
    ),
)
def test_invalid_or_backward_question_date_cannot_earn_complete_history(
    tmp_path: Path,
    question_date: str,
) -> None:
    question = replace(
        _question(
            contents=(
                "Did I visit the museum this year?",
                "I did not visit the gallery this year.",
            )
        ),
        question_date=question_date,
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        run.ingest()
        coverage = run.store.get_occurrence_coverage()

    assert coverage is None or coverage["coverage_mode"] == "forward_only"


def test_duplicate_session_identity_cannot_earn_complete_history(
    tmp_path: Path,
) -> None:
    question = replace(
        _question(
            contents=(
                "Did I visit the museum this year?",
                "I did not visit the gallery this year.",
            )
        ),
        haystack_session_ids=("duplicate-session", "duplicate-session"),
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        run.ingest()
        coverage = run.store.get_occurrence_coverage()

    assert coverage is None or coverage["coverage_mode"] == "forward_only"


def test_failed_import_consumes_freshness_and_cannot_upgrade_on_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = VNextCaptureService.capture_source
    calls = 0

    def fail_second_capture(
        self: VNextCaptureService,
        request: object,
    ) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected partial import")
        return original(self, request)

    monkeypatch.setattr(VNextCaptureService, "capture_source", fail_second_capture)
    question = _question(
        contents=(
            "Did I visit the museum this year?",
            "I did not visit the gallery this year.",
        )
    )
    with adapter.question_run(question, tmp_path / "fresh.sqlite3") as run:
        with pytest.raises(RuntimeError, match="injected partial import"):
            run.ingest()
        monkeypatch.setattr(VNextCaptureService, "capture_source", original)
        run.ingest()
        coverage = run.store.get_occurrence_coverage()

    assert coverage is None or coverage["coverage_mode"] == "forward_only"
