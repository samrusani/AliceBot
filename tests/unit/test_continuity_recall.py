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
        "status": "active",
        "title": title,
        "body": body or {},
        "provenance": provenance or {},
        "confidence": confidence,
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
    assert payload["items"][0]["provenance_references"] == [
        {"source_kind": "continuity_capture_event", "source_id": payload["items"][0]["capture_event_id"]},
        {"source_kind": "source_event", "source_id": "event-1"},
        {"source_kind": "task", "source_id": str(task_id)},
        {"source_kind": "thread", "source_id": str(thread_id)},
    ]


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

    with pytest.raises(ContinuityRecallValidationError, match="until must be greater than or equal to since"):
        query_continuity_recall(
            store,  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            request=ContinuityRecallQueryInput(
                since=datetime(2026, 3, 29, 12, 0, tzinfo=UTC),
                until=datetime(2026, 3, 29, 11, 0, tzinfo=UTC),
            ),
        )
