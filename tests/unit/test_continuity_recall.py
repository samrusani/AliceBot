from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

import alicebot_api.continuity_recall as continuity_recall_module
from alicebot_api.config import Settings
from alicebot_api.continuity_recall import ContinuityRecallValidationError, query_continuity_recall
from alicebot_api.contracts import ContinuityRecallQueryInput


class ContinuityRecallStoreStub:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._capture_events: dict[UUID, dict[str, object]] = {}
        self._evidence_by_object: dict[UUID, list[dict[str, object]]] = {}
        self._corrections_by_object: dict[UUID, list[dict[str, object]]] = {}
        self._entities: list[dict[str, object]] = []
        self._entity_edges: list[dict[str, object]] = []
        self._retrieval_runs: list[dict[str, object]] = []
        self._retrieval_candidates: list[dict[str, object]] = []

    def list_continuity_recall_candidates(self):
        return list(self._rows)

    def list_entities(self):
        return list(self._entities)

    def list_entity_edges_for_entities(self, entity_ids: list[UUID]):
        requested = set(entity_ids)
        return [
            dict(edge)
            for edge in self._entity_edges
            if edge["from_entity_id"] in requested or edge["to_entity_id"] in requested
        ]

    def add_entity(self, entity_row: dict[str, object]) -> None:
        self._entities.append(dict(entity_row))

    def add_entity_edge(self, edge_row: dict[str, object]) -> None:
        self._entity_edges.append(dict(edge_row))

    def add_capture_event(self, capture_event_id: UUID, *, raw_content: str, created_at: datetime) -> None:
        self._capture_events[capture_event_id] = {
            "id": capture_event_id,
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "raw_content": raw_content,
            "explicit_signal": None,
            "admission_posture": "DERIVED",
            "admission_reason": "seeded",
            "created_at": created_at,
        }

    def get_continuity_capture_event_optional(self, capture_event_id: UUID):
        record = self._capture_events.get(capture_event_id)
        return None if record is None else dict(record)

    def add_evidence_row(self, continuity_object_id: UUID, evidence_row: dict[str, object]) -> None:
        self._evidence_by_object.setdefault(continuity_object_id, []).append(evidence_row)

    def list_continuity_object_evidence(self, continuity_object_id: UUID):
        return [dict(row) for row in self._evidence_by_object.get(continuity_object_id, [])]

    def add_correction_event(self, continuity_object_id: UUID, correction_event: dict[str, object]) -> None:
        self._corrections_by_object.setdefault(continuity_object_id, []).append(correction_event)

    def list_continuity_correction_events(self, *, continuity_object_id: UUID, limit: int):
        rows = [dict(row) for row in self._corrections_by_object.get(continuity_object_id, [])]
        rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
        return rows[:limit]

    def create_retrieval_run(self, **kwargs):
        row = {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "created_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            **kwargs,
        }
        self._retrieval_runs.append(row)
        return row

    def create_retrieval_candidate(self, **kwargs):
        row = {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "created_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            **kwargs,
        }
        self._retrieval_candidates.append(row)
        return row


def make_candidate_row(
    *,
    title: str,
    object_type: str,
    capture_created_at: datetime,
    confidence: float,
    admission_posture: str = "DERIVED",
    provenance: dict[str, object] | None = None,
    body: dict[str, object] | None = None,
    status: str = "active",
    last_confirmed_at: datetime | None = None,
    supersedes_object_id: UUID | None = None,
    superseded_by_object_id: UUID | None = None,
    is_searchable: bool = True,
    is_promotable: bool | None = None,
) -> dict[str, object]:
    object_id = uuid4()
    capture_event_id = uuid4()
    created_at = capture_created_at
    updated_at = capture_created_at
    resolved_is_promotable = (
        object_type in {"Decision", "Commitment", "WaitingFor", "Blocker", "NextAction"}
        if is_promotable is None
        else is_promotable
    )
    return {
        "id": object_id,
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "capture_event_id": capture_event_id,
        "object_type": object_type,
        "status": status,
        "is_preserved": True,
        "is_searchable": is_searchable,
        "is_promotable": resolved_is_promotable,
        "title": title,
        "body": body or {},
        "provenance": provenance or {},
        "confidence": confidence,
        "last_confirmed_at": last_confirmed_at,
        "supersedes_object_id": supersedes_object_id,
        "superseded_by_object_id": superseded_by_object_id,
        "object_created_at": created_at,
        "object_updated_at": updated_at,
        "admission_posture": admission_posture,
        "admission_reason": "seeded",
        "explicit_signal": None,
        "capture_created_at": capture_created_at,
    }


def test_recall_returns_deterministic_order_and_provenance_fields() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    task_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    rows = [
        make_candidate_row(
            title="Decision: Keep conservative posture",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 5, tzinfo=UTC),
            confidence=0.8,
            provenance={
                "thread_id": str(thread_id),
                "task_id": str(task_id),
                "confirmation_status": "confirmed",
                "source_event_ids": ["event-1"],
            },
            body={"decision_text": "Keep conservative posture"},
        ),
        make_candidate_row(
            title="Decision: Revisit tomorrow",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 10, tzinfo=UTC),
            confidence=0.9,
            provenance={
                "thread_id": str(thread_id),
                "task_id": str(task_id),
                "confirmation_status": "unconfirmed",
                "source_event_ids": ["event-2"],
            },
            body={"decision_text": "Revisit tomorrow"},
        ),
    ]

    payload = query_continuity_recall(
        ContinuityRecallStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(
            thread_id=thread_id,
            task_id=task_id,
            limit=20,
        ),
    )

    assert payload["summary"] == {
        "query": None,
        "filters": {
            "thread_id": str(thread_id),
            "task_id": str(task_id),
            "since": None,
            "until": None,
        },
        "limit": 20,
        "returned_count": 2,
        "total_count": 2,
        "order": ["relevance_desc", "created_at_desc", "id_desc"],
    }
    assert payload["items"][0]["title"] == "Decision: Keep conservative posture"
    assert payload["items"][0]["confirmation_status"] == "confirmed"
    assert payload["items"][0]["admission_posture"] == "DERIVED"
    assert payload["items"][0]["scope_matches"] == [
        {"kind": "thread", "value": str(thread_id).lower()},
        {"kind": "task", "value": str(task_id).lower()},
    ]
    assert payload["items"][0]["last_confirmed_at"] is None
    assert payload["items"][0]["supersedes_object_id"] is None
    assert payload["items"][0]["superseded_by_object_id"] is None
    assert payload["items"][0]["provenance_references"] == [
        {"source_kind": "continuity_capture_event", "source_id": payload["items"][0]["capture_event_id"]},
        {"source_kind": "source_event", "source_id": "event-1"},
        {"source_kind": "task", "source_id": str(task_id)},
        {"source_kind": "thread", "source_id": str(thread_id)},
    ]
    assert payload["items"][0]["ordering"]["freshness_posture"] == "fresh"
    assert payload["items"][0]["ordering"]["freshness_rank"] == 4
    assert payload["items"][0]["ordering"]["provenance_posture"] == "strong"
    assert payload["items"][0]["ordering"]["provenance_rank"] == 3
    assert payload["items"][0]["ordering"]["supersession_posture"] == "current"
    assert payload["items"][0]["ordering"]["supersession_rank"] == 3
    assert payload["items"][0]["ordering"]["lifecycle_rank"] == 4
    assert payload["items"][0]["lifecycle"]["is_promotable"] is True
    assert payload["items"][0]["explanation"]["trust"]["provenance_posture"] == "strong"
    assert payload["items"][0]["explanation"]["evidence_segments"][0]["source_kind"] == "continuity_capture_event"
    assert payload["items"][0]["explanation"]["timestamps"]["created_at"] == "2026-03-29T10:05:00+00:00"


def test_recall_filters_project_person_query_and_time_window() -> None:
    rows = [
        make_candidate_row(
            title="Next Action: Follow up with Alex on Phoenix",
            object_type="NextAction",
            capture_created_at=datetime(2026, 3, 29, 10, 30, tzinfo=UTC),
            confidence=1.0,
            provenance={"project": "Project Phoenix", "person": "Alex"},
            body={"action_text": "Follow up with Alex"},
        ),
        make_candidate_row(
            title="Next Action: Draft runway notes",
            object_type="NextAction",
            capture_created_at=datetime(2026, 3, 29, 8, 0, tzinfo=UTC),
            confidence=1.0,
            provenance={"project": "Project Atlas", "person": "Sam"},
            body={"action_text": "Draft notes"},
        ),
    ]

    payload = query_continuity_recall(
        ContinuityRecallStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(
            query="follow up",
            project="Project Phoenix",
            person="Alex",
            since=datetime(2026, 3, 29, 9, 0, tzinfo=UTC),
            until=datetime(2026, 3, 29, 11, 0, tzinfo=UTC),
            limit=20,
        ),
    )

    assert [item["title"] for item in payload["items"]] == [
        "Next Action: Follow up with Alex on Phoenix",
    ]


def test_recall_explanation_surfaces_evidence_and_correction_supersession_notes() -> None:
    created_at = datetime(2026, 3, 29, 10, 5, tzinfo=UTC)
    superseded_by_object_id = uuid4()
    row = make_candidate_row(
        title="Decision: Keep rollout phased",
        object_type="Decision",
        capture_created_at=created_at,
        confidence=0.93,
        provenance={
            "thread_id": "thread-1",
            "source_event_ids": ["event-1", "event-2"],
        },
        body={"decision_text": "Keep rollout phased"},
        status="superseded",
        superseded_by_object_id=superseded_by_object_id,
    )
    store = ContinuityRecallStoreStub([row])
    store.add_capture_event(
        row["capture_event_id"],
        raw_content="Decision: Keep rollout phased",
        created_at=created_at,
    )
    store.add_evidence_row(
        row["id"],
        {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "continuity_object_id": row["id"],
            "artifact_id": uuid4(),
            "artifact_copy_id": uuid4(),
            "artifact_segment_id": uuid4(),
            "relationship": "supports",
            "created_at": created_at,
            "source_kind": "markdown_import",
            "import_source_path": "fixtures/demo.md",
            "relative_path": "demo.md",
            "display_name": "Demo import",
            "media_type": "text/markdown",
            "artifact_created_at": created_at,
            "artifact_copy_checksum_sha256": "checksum",
            "artifact_copy_content_text": "Decision: Keep rollout phased",
            "artifact_copy_content_length_bytes": 29,
            "artifact_copy_content_encoding": "utf-8",
            "artifact_copy_created_at": created_at,
            "segment_source_item_id": "decision-1",
            "segment_sequence_no": 1,
            "segment_kind": "paragraph",
            "segment_locator": {"line_start": 1},
            "segment_raw_content": "Decision: Keep rollout phased because of rollout safety.",
            "segment_checksum_sha256": "segment-checksum",
            "segment_created_at": created_at,
        },
    )
    store.add_correction_event(
        row["id"],
        {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "continuity_object_id": row["id"],
            "action": "supersede",
            "reason": "Updated rollout decision replaced this one",
            "before_snapshot": {},
            "after_snapshot": {},
            "payload": {},
            "created_at": datetime(2026, 3, 29, 11, 0, tzinfo=UTC),
        },
    )

    payload = query_continuity_recall(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(limit=20),
    )

    explanation = payload["items"][0]["explanation"]
    assert explanation["trust"]["trust_class"] == "human_curated"
    assert explanation["evidence_segments"][0]["source_kind"] == "markdown_import"
    assert explanation["evidence_segments"][0]["snippet"].startswith("Decision: Keep rollout phased")
    assert any(
        note["related_object_id"] == str(superseded_by_object_id)
        for note in explanation["supersession_notes"]
    )
    assert any(note["action"] == "supersede" for note in explanation["supersession_notes"])


def test_recall_rejects_invalid_limits_and_time_window() -> None:
    store = ContinuityRecallStoreStub([])

    with pytest.raises(ContinuityRecallValidationError, match="limit must be between 1 and"):
        query_continuity_recall(
            store,  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            request=ContinuityRecallQueryInput(limit=0),
        )


def test_recall_excludes_deleted_and_ranks_lifecycle_posture_deterministically() -> None:
    rows = [
        make_candidate_row(
            title="Decision: active item",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            confidence=0.8,
            status="active",
            body={"decision_text": "active item"},
        ),
        make_candidate_row(
            title="Decision: stale item",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 1, tzinfo=UTC),
            confidence=0.99,
            status="stale",
            body={"decision_text": "stale item"},
        ),
        make_candidate_row(
            title="Decision: superseded item",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 2, tzinfo=UTC),
            confidence=1.0,
            status="superseded",
            body={"decision_text": "superseded item"},
        ),
        make_candidate_row(
            title="Decision: deleted item",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 3, tzinfo=UTC),
            confidence=1.0,
            status="deleted",
            body={"decision_text": "deleted item"},
        ),
        make_candidate_row(
            title="Note: preserved but hidden",
            object_type="Note",
            capture_created_at=datetime(2026, 3, 29, 10, 4, tzinfo=UTC),
            confidence=1.0,
            status="active",
            body={"body": "preserved but hidden"},
            is_searchable=False,
            is_promotable=False,
        ),
    ]

    store = ContinuityRecallStoreStub(rows)  # type: ignore[arg-type]
    payload = query_continuity_recall(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(limit=20),
    )

    assert [item["title"] for item in payload["items"]] == [
        "Decision: active item",
        "Decision: stale item",
        "Decision: superseded item",
    ]
    assert all(item["status"] != "deleted" for item in payload["items"])
    assert all(item["object_type"] != "Note" for item in payload["items"])

    with pytest.raises(ContinuityRecallValidationError, match="until must be greater than or equal to since"):
        query_continuity_recall(
            store,  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            request=ContinuityRecallQueryInput(
                since=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
                until=datetime(2026, 3, 29, 11, 0, tzinfo=UTC),
            ),
        )


def test_recall_prefers_confirmed_fresh_active_truth_over_stale_and_superseded_candidates() -> None:
    confirmed_fresh = make_candidate_row(
        title="Decision: Current rollout policy",
        object_type="Decision",
        capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
        confidence=0.62,
        status="active",
        body={"decision_text": "rollout policy"},
        provenance={"confirmation_status": "confirmed", "source_event_ids": ["event-current"]},
        last_confirmed_at=datetime(2026, 3, 29, 10, 30, tzinfo=UTC),
    )
    stale = make_candidate_row(
        title="Decision: Old rollout policy",
        object_type="Decision",
        capture_created_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
        confidence=0.99,
        status="stale",
        body={"decision_text": "rollout policy"},
        provenance={"confirmation_status": "confirmed"},
    )
    superseded = make_candidate_row(
        title="Decision: Superseded rollout policy",
        object_type="Decision",
        capture_created_at=datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
        confidence=1.0,
        status="superseded",
        body={"decision_text": "rollout policy"},
        provenance={"confirmation_status": "confirmed"},
        superseded_by_object_id=UUID(str(confirmed_fresh["id"])),
    )

    payload = query_continuity_recall(
        ContinuityRecallStoreStub([stale, superseded, confirmed_fresh]),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(
            query="rollout policy",
            limit=20,
        ),
    )

    assert [item["title"] for item in payload["items"]] == [
        "Decision: Current rollout policy",
        "Decision: Old rollout policy",
        "Decision: Superseded rollout policy",
    ]
    assert payload["items"][0]["ordering"]["freshness_posture"] == "fresh"
    assert payload["items"][0]["ordering"]["supersession_posture"] == "current"
    assert payload["items"][1]["ordering"]["freshness_posture"] == "stale"
    assert payload["items"][2]["ordering"]["supersession_posture"] == "superseded"


def test_recall_uses_provenance_quality_as_tie_breaker() -> None:
    rows = [
        make_candidate_row(
            title="Decision: pricing guardrail with source event",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 5, tzinfo=UTC),
            confidence=0.9,
            provenance={
                "confirmation_status": "confirmed",
                "thread_id": "thread-1",
                "source_event_ids": ["event-strong"],
            },
            body={"decision_text": "pricing guardrail"},
        ),
        make_candidate_row(
            title="Decision: pricing guardrail without source event",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 5, tzinfo=UTC),
            confidence=0.99,
            provenance={
                "confirmation_status": "confirmed",
            },
            body={"decision_text": "pricing guardrail"},
        ),
    ]

    payload = query_continuity_recall(
        ContinuityRecallStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(query="pricing", limit=20),
    )

    assert [item["title"] for item in payload["items"]] == [
        "Decision: pricing guardrail with source event",
        "Decision: pricing guardrail without source event",
    ]
    assert payload["items"][0]["ordering"]["provenance_posture"] == "strong"
    assert payload["items"][1]["ordering"]["provenance_posture"] in {"weak", "partial"}


def test_recall_prefers_provenance_freshness_when_explicit_values_conflict() -> None:
    row = make_candidate_row(
        title="Decision: rollout policy conflict metadata",
        object_type="Decision",
        capture_created_at=datetime(2026, 3, 29, 11, 0, tzinfo=UTC),
        confidence=0.7,
        status="active",
        provenance={
            "confirmation_status": "confirmed",
            "freshness_posture": "stale",
        },
        body={
            "decision_text": "rollout policy",
            "freshness_status": "fresh",
        },
    )

    payload = query_continuity_recall(
        ContinuityRecallStoreStub([row]),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(query="rollout policy", limit=20),
    )

    assert payload["items"][0]["ordering"]["freshness_posture"] == "stale"
    assert payload["items"][0]["ordering"]["freshness_rank"] == 2


def test_recall_selects_ranked_explicit_values_deterministically_within_source() -> None:
    row = make_candidate_row(
        title="Decision: rollout policy list metadata",
        object_type="Decision",
        capture_created_at=datetime(2026, 3, 29, 11, 5, tzinfo=UTC),
        confidence=0.7,
        status="active",
        provenance={
            "confirmation_status": ["contested", "confirmed"],
            "freshness_posture": ["stale", "fresh"],
        },
        body={"decision_text": "rollout policy"},
    )

    payload = query_continuity_recall(
        ContinuityRecallStoreStub([row]),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(query="rollout policy", limit=20),
    )

    assert payload["items"][0]["confirmation_status"] == "confirmed"
    assert payload["items"][0]["ordering"]["freshness_posture"] == "fresh"


def test_recall_debug_surfaces_stage_scores_and_exclusion_reasons() -> None:
    rows = [
        make_candidate_row(
            title="Decision: Keep rollout phased",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            confidence=0.9,
            body={"decision_text": "keep rollout phased"},
            provenance={"confirmation_status": "confirmed", "source_event_ids": ["event-1"]},
            last_confirmed_at=datetime(2026, 3, 29, 10, 30, tzinfo=UTC),
        ),
        make_candidate_row(
            title="Decision: Budget note",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 1, tzinfo=UTC),
            confidence=0.95,
            body={"decision_text": "budget note only"},
            provenance={"confirmation_status": "confirmed", "source_event_ids": ["event-2"]},
        ),
    ]

    payload = query_continuity_recall(
        ContinuityRecallStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(query="rollout", limit=20, debug=True),
    )

    debug = payload["debug"]
    assert debug["ranking_strategy"] == "hybrid_v2"
    assert debug["candidate_count"] == 2
    assert debug["selected_count"] == 1
    assert debug["candidates"][0]["selected"] is True
    assert debug["candidates"][0]["stage_scores"]["lexical"]["matched"] is True
    assert debug["candidates"][0]["stage_scores"]["semantic"]["matched"] is True
    assert debug["candidates"][1]["selected"] is False
    assert debug["candidates"][1]["exclusion_reason"] == "no_stream_match"
    assert debug["candidates"][1]["stage_scores"]["trust"]["matched"] is True


def test_recall_uses_entity_edge_expansion_to_prefer_related_owner() -> None:
    rows = [
        make_candidate_row(
            title="Decision: Alex owns dependency follow-up",
            object_type="Decision",
            capture_created_at=datetime(2026, 4, 1, 9, 0, tzinfo=UTC),
            confidence=0.72,
            body={"decision_text": "dependency owner follow-up is Alex"},
            provenance={"person": "Alex", "confirmation_status": "confirmed", "source_event_ids": ["event-1"]},
            last_confirmed_at=datetime(2026, 4, 1, 9, 30, tzinfo=UTC),
        ),
        make_candidate_row(
            title="Decision: Phoenix dependency note",
            object_type="Decision",
            capture_created_at=datetime(2026, 4, 1, 9, 5, tzinfo=UTC),
            confidence=0.95,
            body={"decision_text": "dependency owner follow-up is Taylor"},
            provenance={
                "project": "Project Phoenix",
                "person": "Taylor",
                "confirmation_status": "confirmed",
                "source_event_ids": ["event-2"],
            },
            status="stale",
        ),
    ]
    store = ContinuityRecallStoreStub(rows)  # type: ignore[arg-type]
    store.add_entity(
        {
            "id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "entity_type": "project",
            "name": "Project Phoenix",
            "source_memory_ids": ["memory-1"],
            "created_at": datetime(2026, 4, 1, 8, 0, tzinfo=UTC),
        }
    )
    store.add_entity(
        {
            "id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "entity_type": "person",
            "name": "Alex",
            "source_memory_ids": ["memory-2"],
            "created_at": datetime(2026, 4, 1, 8, 5, tzinfo=UTC),
        }
    )
    store.add_entity_edge(
        {
            "id": UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "from_entity_id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            "to_entity_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            "relationship_type": "owner_of",
            "valid_from": None,
            "valid_to": None,
            "source_memory_ids": ["memory-3"],
            "created_at": datetime(2026, 4, 1, 8, 10, tzinfo=UTC),
        }
    )

    payload = query_continuity_recall(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(query="Project Phoenix dependency owner", limit=20, debug=True),
    )

    assert payload["items"][0]["title"] == "Decision: Alex owns dependency follow-up"
    assert payload["debug"]["candidates"][0]["stage_scores"]["entity_edge"]["matched"] is True


def test_recall_debug_normalizes_against_scope_matched_candidates_only() -> None:
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    rows = [
        make_candidate_row(
            title="Decision: Keep rollout phased",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
            confidence=0.9,
            body={"decision_text": "keep rollout phased"},
            provenance={"thread_id": str(thread_id), "confirmation_status": "confirmed"},
        ),
        make_candidate_row(
            title="Decision: Off-scope rollout archive",
            object_type="Decision",
            capture_created_at=datetime(2026, 3, 29, 11, 0, tzinfo=UTC),
            confidence=0.99,
            body={"decision_text": "rollout rollout rollout rollout rollout rollout rollout rollout"},
            provenance={
                "thread_id": str(UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")),
                "confirmation_status": "confirmed",
            },
        ),
    ]

    payload = query_continuity_recall(
        ContinuityRecallStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityRecallQueryInput(
            query="rollout",
            thread_id=thread_id,
            limit=20,
            debug=True,
        ),
    )

    assert [item["title"] for item in payload["items"]] == ["Decision: Keep rollout phased"]
    selected_candidate = payload["debug"]["candidates"][0]
    assert selected_candidate["object_id"] == str(rows[0]["id"])
    assert selected_candidate["stage_scores"]["lexical"]["normalized_score"] == pytest.approx(1.0)

    excluded_candidate = next(
        candidate
        for candidate in payload["debug"]["candidates"]
        if candidate["object_id"] == str(rows[1]["id"])
    )
    assert excluded_candidate["exclusion_reason"] == "scope_mismatch"


def test_retrieval_trace_retention_uses_configured_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        continuity_recall_module,
        "get_settings",
        lambda: Settings(retrieval_trace_retention_days=3),
    )

    assert continuity_recall_module._retrieval_trace_retention_until(now=now) == now + timedelta(days=3)
