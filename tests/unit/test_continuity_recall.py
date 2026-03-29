from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from alicebot_api.continuity_recall import ContinuityRecallValidationError, query_continuity_recall
from alicebot_api.contracts import ContinuityRecallQueryInput


class ContinuityRecallStoreStub:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def list_continuity_recall_candidates(self):
        return list(self._rows)


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
) -> dict[str, object]:
    object_id = uuid4()
    capture_event_id = uuid4()
    created_at = capture_created_at
    updated_at = capture_created_at
    return {
        "id": object_id,
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "capture_event_id": capture_event_id,
        "object_type": object_type,
        "status": status,
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
