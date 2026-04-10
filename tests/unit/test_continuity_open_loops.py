from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from alicebot_api.continuity_open_loops import (
    ContinuityOpenLoopValidationError,
    apply_continuity_open_loop_review_action,
    compile_continuity_daily_brief,
    compile_continuity_open_loop_dashboard,
    compile_continuity_weekly_review,
)
from alicebot_api.contracts import (
    ContinuityDailyBriefRequestInput,
    ContinuityOpenLoopDashboardQueryInput,
    ContinuityOpenLoopReviewActionInput,
    ContinuityWeeklyReviewRequestInput,
)


class ContinuityOpenLoopsStoreStub:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.base_time = datetime(2026, 3, 30, 9, 0, tzinfo=UTC)
        self._recall_rows = list(rows or [])
        self.objects: dict[UUID, dict[str, object]] = {}
        self.events: list[dict[str, object]] = []

    def list_continuity_recall_candidates(self):
        return list(self._recall_rows)

    def add_object(
        self,
        *,
        object_type: str,
        status: str = "active",
        title: str,
        created_at: datetime | None = None,
        last_confirmed_at: datetime | None = None,
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
            "provenance": {"thread_id": "thread-1"},
            "confidence": 0.91,
            "last_confirmed_at": last_confirmed_at,
            "supersedes_object_id": None,
            "superseded_by_object_id": None,
            "created_at": created_at or self.base_time,
            "updated_at": created_at or self.base_time,
        }
        self.objects[object_id] = row
        return dict(row)

    def get_continuity_object_optional(self, continuity_object_id: UUID):
        row = self.objects.get(continuity_object_id)
        if row is None:
            return None
        return dict(row)

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
        event = {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "continuity_object_id": continuity_object_id,
            "action": action,
            "reason": reason,
            "before_snapshot": before_snapshot,
            "after_snapshot": after_snapshot,
            "payload": payload,
            "created_at": self.base_time + timedelta(minutes=len(self.events) + 1),
        }
        self.events.append(event)
        return dict(event)

    def list_continuity_correction_events(self, *, continuity_object_id: UUID, limit: int):
        matching = [
            dict(event)
            for event in self.events
            if event["continuity_object_id"] == continuity_object_id
        ]
        matching.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
        return matching[:limit]

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
        row = self.objects.get(continuity_object_id)
        if row is None:
            return None

        updated = {
            **row,
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
            "updated_at": self.base_time + timedelta(minutes=len(self.events) + 1),
        }
        self.objects[continuity_object_id] = updated
        return dict(updated)


def make_candidate_row(
    *,
    title: str,
    object_type: str,
    status: str,
    created_at: datetime,
) -> dict[str, object]:
    return {
        "id": uuid4(),
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "capture_event_id": uuid4(),
        "object_type": object_type,
        "status": status,
        "is_preserved": True,
        "is_searchable": True,
        "is_promotable": object_type in {"Decision", "Commitment", "WaitingFor", "Blocker", "NextAction"},
        "title": title,
        "body": {"text": title},
        "provenance": {"thread_id": "thread-1"},
        "confidence": 1.0,
        "last_confirmed_at": None,
        "supersedes_object_id": None,
        "superseded_by_object_id": None,
        "object_created_at": created_at,
        "object_updated_at": created_at,
        "admission_posture": "DERIVED",
        "admission_reason": "seeded",
        "explicit_signal": None,
        "capture_created_at": created_at,
    }


def test_open_loop_dashboard_groups_and_orders_posture_deterministically() -> None:
    rows = [
        make_candidate_row(
            title="Waiting For: Vendor quote",
            object_type="WaitingFor",
            status="active",
            created_at=datetime(2026, 3, 30, 10, 1, tzinfo=UTC),
        ),
        make_candidate_row(
            title="Waiting For: Legal signoff",
            object_type="WaitingFor",
            status="active",
            created_at=datetime(2026, 3, 30, 10, 3, tzinfo=UTC),
        ),
        make_candidate_row(
            title="Blocker: Missing API key",
            object_type="Blocker",
            status="active",
            created_at=datetime(2026, 3, 30, 10, 4, tzinfo=UTC),
        ),
        make_candidate_row(
            title="Next Action: Send follow-up",
            object_type="NextAction",
            status="active",
            created_at=datetime(2026, 3, 30, 10, 5, tzinfo=UTC),
        ),
        make_candidate_row(
            title="Waiting For: Stale invoice response",
            object_type="WaitingFor",
            status="stale",
            created_at=datetime(2026, 3, 30, 10, 6, tzinfo=UTC),
        ),
        make_candidate_row(
            title="Note: not part of open-loop posture",
            object_type="Note",
            status="active",
            created_at=datetime(2026, 3, 30, 10, 7, tzinfo=UTC),
        ),
    ]

    payload = compile_continuity_open_loop_dashboard(
        ContinuityOpenLoopsStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityOpenLoopDashboardQueryInput(limit=10),
    )

    dashboard = payload["dashboard"]
    assert dashboard["summary"] == {
        "limit": 10,
        "total_count": 5,
        "posture_order": ["waiting_for", "blocker", "stale", "next_action"],
        "item_order": ["created_at_desc", "id_desc"],
    }
    assert [item["title"] for item in dashboard["waiting_for"]["items"]] == [
        "Waiting For: Legal signoff",
        "Waiting For: Vendor quote",
    ]
    assert [item["title"] for item in dashboard["blocker"]["items"]] == [
        "Blocker: Missing API key",
    ]
    assert [item["title"] for item in dashboard["stale"]["items"]] == [
        "Waiting For: Stale invoice response",
    ]
    assert [item["title"] for item in dashboard["next_action"]["items"]] == [
        "Next Action: Send follow-up",
    ]


def test_daily_and_weekly_briefs_emit_explicit_empty_states() -> None:
    rows = [
        make_candidate_row(
            title="Decision: Keep rollout phased",
            object_type="Decision",
            status="active",
            created_at=datetime(2026, 3, 30, 11, 0, tzinfo=UTC),
        ),
    ]

    daily = compile_continuity_daily_brief(
        ContinuityOpenLoopsStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityDailyBriefRequestInput(limit=3),
    )["brief"]
    weekly = compile_continuity_weekly_review(
        ContinuityOpenLoopsStoreStub(rows),  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityWeeklyReviewRequestInput(limit=3),
    )["review"]

    assert daily["waiting_for_highlights"]["empty_state"] == {
        "is_empty": True,
        "message": "No waiting-for highlights for today in the requested scope.",
    }
    assert daily["blocker_highlights"]["empty_state"] == {
        "is_empty": True,
        "message": "No blocker highlights for today in the requested scope.",
    }
    assert daily["stale_items"]["empty_state"] == {
        "is_empty": True,
        "message": "No stale items for today in the requested scope.",
    }
    assert daily["next_suggested_action"] == {
        "item": None,
        "empty_state": {
            "is_empty": True,
            "message": "No next suggested action in the requested scope.",
        },
    }

    assert weekly["rollup"] == {
        "total_count": 0,
        "waiting_for_count": 0,
        "blocker_count": 0,
        "stale_count": 0,
        "correction_recurrence_count": 0,
        "freshness_drift_count": 0,
        "next_action_count": 0,
        "posture_order": ["waiting_for", "blocker", "stale", "next_action"],
    }


def test_weekly_rollup_surfaces_correction_recurrence_and_freshness_drift() -> None:
    stale_id = uuid4()
    recurring_id = uuid4()
    rows = [
        {
            **make_candidate_row(
                title="Waiting For: stale handoff",
                object_type="WaitingFor",
                status="stale",
                created_at=datetime(2026, 3, 30, 10, 0, tzinfo=UTC),
            ),
            "id": stale_id,
        },
        {
            **make_candidate_row(
                title="Blocker: recurring correction",
                object_type="Blocker",
                status="active",
                created_at=datetime(2026, 3, 30, 10, 1, tzinfo=UTC),
            ),
            "id": recurring_id,
        },
    ]
    store = ContinuityOpenLoopsStoreStub(rows)
    store.events.extend(
        [
            {
                "id": uuid4(),
                "continuity_object_id": recurring_id,
                "created_at": datetime(2026, 3, 30, 9, 1, tzinfo=UTC),
            },
            {
                "id": uuid4(),
                "continuity_object_id": recurring_id,
                "created_at": datetime(2026, 3, 30, 9, 2, tzinfo=UTC),
            },
        ]
    )

    weekly = compile_continuity_weekly_review(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=ContinuityWeeklyReviewRequestInput(limit=5),
    )["review"]

    assert weekly["rollup"]["correction_recurrence_count"] == 1
    assert weekly["rollup"]["freshness_drift_count"] == 1


def test_open_loop_dashboard_rejects_mixed_naive_and_offset_aware_time_window() -> None:
    with pytest.raises(
        ContinuityOpenLoopValidationError,
        match="since and until must both include timezone offsets or both omit timezone offsets",
    ):
        compile_continuity_open_loop_dashboard(
            ContinuityOpenLoopsStoreStub(),  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            request=ContinuityOpenLoopDashboardQueryInput(
                since=datetime(2026, 3, 30, 10, 0, tzinfo=UTC),
                until=datetime(2026, 3, 30, 10, 1),
            ),
        )


def test_review_actions_transition_deterministically_and_emit_audit_rows() -> None:
    store = ContinuityOpenLoopsStoreStub()
    row = store.add_object(
        object_type="WaitingFor",
        status="active",
        title="Waiting For: Vendor quote",
    )

    done = apply_continuity_open_loop_review_action(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=row["id"],
        request=ContinuityOpenLoopReviewActionInput(action="done", note="Closed in standup"),
    )
    assert done["review_action"] == "done"
    assert done["lifecycle_outcome"] == "completed"
    assert done["continuity_object"]["status"] == "completed"
    assert done["correction_event"]["action"] == "edit"
    assert done["correction_event"]["payload"]["review_action"] == "done"

    deferred = apply_continuity_open_loop_review_action(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=row["id"],
        request=ContinuityOpenLoopReviewActionInput(action="deferred"),
    )
    assert deferred["lifecycle_outcome"] == "stale"
    assert deferred["continuity_object"]["status"] == "stale"
    assert deferred["correction_event"]["action"] == "mark_stale"

    still_blocked = apply_continuity_open_loop_review_action(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        continuity_object_id=row["id"],
        request=ContinuityOpenLoopReviewActionInput(action="still_blocked"),
    )
    assert still_blocked["lifecycle_outcome"] == "active"
    assert still_blocked["continuity_object"]["status"] == "active"
    assert still_blocked["continuity_object"]["last_confirmed_at"] is not None
    assert still_blocked["correction_event"]["action"] == "confirm"


def test_review_action_rejects_unsupported_status() -> None:
    store = ContinuityOpenLoopsStoreStub()
    row = store.add_object(
        object_type="Blocker",
        status="deleted",
        title="Blocker: Deprecated",
    )

    with pytest.raises(
        ContinuityOpenLoopValidationError,
        match="review action cannot be applied when status is deleted",
    ):
        apply_continuity_open_loop_review_action(
            store,  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            continuity_object_id=row["id"],
            request=ContinuityOpenLoopReviewActionInput(action="still_blocked"),
        )
