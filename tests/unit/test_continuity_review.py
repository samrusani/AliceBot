from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from alicebot_api.continuity_review import (
    ContinuityReviewNotFoundError,
    ContinuityReviewValidationError,
    apply_continuity_correction,
    get_continuity_review_detail,
    list_continuity_review_queue,
)
from alicebot_api.contracts import ContinuityCorrectionInput, ContinuityReviewQueueQueryInput


class ContinuityReviewStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 30, 9, 0, tzinfo=UTC)
        self.objects: dict[UUID, dict[str, object]] = {}
        self.events_by_object: dict[UUID, list[dict[str, object]]] = {}
        self.call_log: list[str] = []

    def add_object(
        self,
        *,
        title: str,
        status: str = "active",
        object_type: str = "Decision",
        last_confirmed_at: datetime | None = None,
        supersedes_object_id: UUID | None = None,
        superseded_by_object_id: UUID | None = None,
    ) -> dict[str, object]:
        object_id = uuid4()
        capture_event_id = uuid4()
        row = {
            "id": object_id,
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "capture_event_id": capture_event_id,
            "object_type": object_type,
            "status": status,
            "is_preserved": True,
            "is_searchable": True,
            "is_promotable": True,
            "title": title,
            "body": {"text": title},
            "provenance": {"capture_event_id": str(capture_event_id)},
            "confidence": 0.9,
            "last_confirmed_at": last_confirmed_at,
            "supersedes_object_id": supersedes_object_id,
            "superseded_by_object_id": superseded_by_object_id,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.objects[object_id] = row
        self.events_by_object.setdefault(object_id, [])
        return row

    def get_continuity_object_optional(self, continuity_object_id: UUID):
        row = self.objects.get(continuity_object_id)
        if row is None:
            return None
        return dict(row)

    def list_continuity_review_queue(self, *, statuses: list[str], limit: int):
        filtered = [
            dict(row)
            for row in self.objects.values()
            if row["status"] in statuses
        ]
        filtered.sort(key=lambda item: (item["updated_at"], item["created_at"], item["id"]), reverse=True)
        return filtered[:limit]

    def count_continuity_review_queue(self, *, statuses: list[str]) -> int:
        return sum(1 for row in self.objects.values() if row["status"] in statuses)

    def list_continuity_correction_events(self, *, continuity_object_id: UUID, limit: int):
        events = [dict(item) for item in self.events_by_object.get(continuity_object_id, [])]
        events.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
        return events[:limit]

    def create_continuity_correction_event(
        self,
        *,
        continuity_object_id: UUID,
        action: str,
        reason: str | None,
        before_snapshot,
        after_snapshot,
        payload,
    ):
        self.call_log.append("create_event")
        event = {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "continuity_object_id": continuity_object_id,
            "action": action,
            "reason": reason,
            "before_snapshot": before_snapshot,
            "after_snapshot": after_snapshot,
            "payload": payload,
            "created_at": self.base_time,
        }
        self.events_by_object.setdefault(continuity_object_id, []).append(event)
        return dict(event)

    def update_continuity_object_optional(
        self,
        *,
        continuity_object_id: UUID,
        status: str,
        is_preserved: bool,
        is_searchable: bool,
        is_promotable: bool,
        title: str,
        body,
        provenance,
        confidence: float,
        last_confirmed_at: datetime | None,
        supersedes_object_id: UUID | None,
        superseded_by_object_id: UUID | None,
    ):
        self.call_log.append("update_object")
        row = self.objects.get(continuity_object_id)
        if row is None:
            return None
        row.update(
            {
                "status": status,
                "is_preserved": is_preserved,
                "is_searchable": is_searchable,
                "is_promotable": is_promotable,
                "title": title,
                "body": body,
                "provenance": provenance,
                "confidence": confidence,
                "last_confirmed_at": last_confirmed_at,
                "supersedes_object_id": supersedes_object_id,
                "superseded_by_object_id": superseded_by_object_id,
                "updated_at": self.base_time,
            }
        )
        return dict(row)

    def create_continuity_capture_event(
        self,
        *,
        raw_content: str,
        explicit_signal: str | None,
        admission_posture: str,
        admission_reason: str,
    ):
        self.call_log.append("create_capture")
        return {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "raw_content": raw_content,
            "explicit_signal": explicit_signal,
            "admission_posture": admission_posture,
            "admission_reason": admission_reason,
            "created_at": self.base_time,
        }

    def create_continuity_object(
        self,
        *,
        capture_event_id: UUID,
        object_type: str,
        status: str,
        title: str,
        body,
        provenance,
        confidence: float,
        is_preserved: bool = True,
        is_searchable: bool = True,
        is_promotable: bool = True,
        last_confirmed_at: datetime | None = None,
        supersedes_object_id: UUID | None = None,
        superseded_by_object_id: UUID | None = None,
    ):
        self.call_log.append("create_object")
        object_id = uuid4()
        row = {
            "id": object_id,
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "capture_event_id": capture_event_id,
            "object_type": object_type,
            "status": status,
            "is_preserved": is_preserved,
            "is_searchable": is_searchable,
            "is_promotable": is_promotable,
            "title": title,
            "body": body,
            "provenance": provenance,
            "confidence": confidence,
            "last_confirmed_at": last_confirmed_at,
            "supersedes_object_id": supersedes_object_id,
            "superseded_by_object_id": superseded_by_object_id,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.objects[object_id] = row
        self.events_by_object.setdefault(object_id, [])
        return dict(row)


def test_review_queue_filters_correction_ready_statuses() -> None:
    store = ContinuityReviewStoreStub()
    store.add_object(title="Active", status="active")
    store.add_object(title="Stale", status="stale")
    store.add_object(title="Deleted", status="deleted")

    payload = list_continuity_review_queue(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityReviewQueueQueryInput(status="correction_ready", limit=20),
    )

    assert sorted(item["status"] for item in payload["items"]) == ["active", "stale"]
    assert payload["summary"] == {
        "status": "correction_ready",
        "limit": 20,
        "returned_count": 2,
        "total_count": 2,
        "order": ["updated_at_desc", "created_at_desc", "id_desc"],
    }


def test_confirm_records_event_before_lifecycle_mutation() -> None:
    store = ContinuityReviewStoreStub()
    row = store.add_object(title="Decision: Keep rollout phased", status="active")

    payload = apply_continuity_correction(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=row["id"],
        request=ContinuityCorrectionInput(action="confirm", reason="Verified in review"),
    )

    assert store.call_log[:2] == ["create_event", "update_object"]
    assert payload["continuity_object"]["status"] == "active"
    assert payload["continuity_object"]["lifecycle"]["is_promotable"] is True
    assert payload["continuity_object"]["last_confirmed_at"] is not None
    assert payload["correction_event"]["action"] == "confirm"
    assert payload["replacement_object"] is None


def test_edit_delete_and_mark_stale_are_deterministic() -> None:
    store = ContinuityReviewStoreStub()
    edit_row = store.add_object(title="Decision: Old", status="active")
    stale_row = store.add_object(title="Decision: Fresh", status="active")
    delete_row = store.add_object(title="Decision: Remove", status="stale")

    edited = apply_continuity_correction(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=edit_row["id"],
        request=ContinuityCorrectionInput(
            action="edit",
            title="Decision: Updated",
            body={"text": "Updated"},
            confidence=0.95,
        ),
    )
    marked_stale = apply_continuity_correction(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=stale_row["id"],
        request=ContinuityCorrectionInput(action="mark_stale"),
    )
    deleted = apply_continuity_correction(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=delete_row["id"],
        request=ContinuityCorrectionInput(action="delete", reason="No longer valid"),
    )

    assert edited["continuity_object"]["title"] == "Decision: Updated"
    assert edited["continuity_object"]["status"] == "active"
    assert marked_stale["continuity_object"]["status"] == "stale"
    assert deleted["continuity_object"]["status"] == "deleted"


def test_supersede_creates_replacement_and_preserves_chain_links() -> None:
    store = ContinuityReviewStoreStub()
    row = store.add_object(title="Decision: Legacy truth", status="active")

    payload = apply_continuity_correction(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=row["id"],
        request=ContinuityCorrectionInput(
            action="supersede",
            reason="Contradicted by newer evidence",
            replacement_title="Decision: New truth",
            replacement_body={"decision_text": "New truth"},
            replacement_provenance={"thread_id": "thread-1"},
            replacement_confidence=0.97,
        ),
    )

    assert store.call_log[:4] == [
        "create_event",
        "create_capture",
        "create_object",
        "update_object",
    ]
    assert payload["continuity_object"]["status"] == "superseded"
    assert payload["replacement_object"] is not None
    assert payload["replacement_object"]["status"] == "active"
    assert payload["replacement_object"]["supersedes_object_id"] == str(row["id"])
    assert payload["continuity_object"]["superseded_by_object_id"] == payload["replacement_object"]["id"]


def test_review_detail_exposes_supersession_chain_and_event_history() -> None:
    store = ContinuityReviewStoreStub()
    old_row = store.add_object(title="Decision: Old", status="superseded")
    replacement_row = store.add_object(
        title="Decision: New",
        status="active",
        supersedes_object_id=old_row["id"],
    )
    old_row["superseded_by_object_id"] = replacement_row["id"]
    store.objects[old_row["id"]] = old_row

    store.create_continuity_correction_event(
        continuity_object_id=old_row["id"],
        action="supersede",
        reason="Updated truth",
        before_snapshot={"status": "active"},
        after_snapshot={"status": "superseded"},
        payload={"replacement_title": "Decision: New"},
    )

    detail = get_continuity_review_detail(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=old_row["id"],
    )

    assert detail["review"]["continuity_object"]["status"] == "superseded"
    assert detail["review"]["supersession_chain"]["superseded_by"] is not None
    assert detail["review"]["supersession_chain"]["superseded_by"]["id"] == str(replacement_row["id"])
    assert detail["review"]["correction_events"][0]["action"] == "supersede"


def test_review_rejects_invalid_transition_and_missing_rows() -> None:
    store = ContinuityReviewStoreStub()
    deleted_row = store.add_object(title="Decision: Removed", status="deleted")

    with pytest.raises(ContinuityReviewValidationError, match="confirm requires an active or stale"):
        apply_continuity_correction(
            store,  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            continuity_object_id=deleted_row["id"],
            request=ContinuityCorrectionInput(action="confirm"),
        )

    with pytest.raises(ContinuityReviewNotFoundError, match="was not found"):
        get_continuity_review_detail(
            store,  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            continuity_object_id=uuid4(),
        )
