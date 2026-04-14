from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from alicebot_api.continuity_contradictions import (
    build_explanation_contradiction_summary,
    contradiction_metrics_by_object,
    resolve_contradiction_case,
    sync_contradiction_state_for_objects,
)
from alicebot_api.continuity_trust import list_trust_signals
from alicebot_api.contracts import ContradictionResolveInput, TrustSignalListQueryInput


class InMemoryContradictionStore:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = [dict(row) for row in rows]
        self._objects = {
            row["id"]: {
                "id": row["id"],
                "capture_event_id": row["capture_event_id"],
                "object_type": row["object_type"],
                "status": row["status"],
                "is_preserved": row["is_preserved"],
                "is_searchable": row["is_searchable"],
                "is_promotable": row["is_promotable"],
                "title": row["title"],
                "body": row["body"],
                "provenance": row["provenance"],
                "confidence": row["confidence"],
                "last_confirmed_at": row["last_confirmed_at"],
                "supersedes_object_id": row["supersedes_object_id"],
                "superseded_by_object_id": row["superseded_by_object_id"],
                "created_at": row["object_created_at"],
                "updated_at": row["object_updated_at"],
            }
            for row in self._rows
        }
        self._cases: dict[UUID, dict[str, object]] = {}
        self._signals: dict[tuple[UUID, str], dict[str, object]] = {}
        self._clock = datetime(2026, 4, 14, 12, 0, tzinfo=UTC)

    def _tick(self) -> datetime:
        self._clock = self._clock + timedelta(seconds=1)
        return self._clock

    def list_continuity_recall_candidates(self) -> list[dict[str, object]]:
        return [dict(row) for row in self._rows]

    def list_continuity_correction_events(
        self,
        *,
        continuity_object_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        del continuity_object_id, limit
        return []

    def list_continuity_object_evidence(self, continuity_object_id: UUID) -> list[dict[str, object]]:
        del continuity_object_id
        return []

    def get_continuity_object_optional(self, continuity_object_id: UUID) -> dict[str, object] | None:
        record = self._objects.get(continuity_object_id)
        return None if record is None else dict(record)

    def create_contradiction_case(self, **kwargs: object) -> dict[str, object]:
        now = self._tick()
        row = {
            "id": uuid4(),
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }
        self._cases[row["id"]] = row
        return dict(row)

    def update_contradiction_case_optional(
        self,
        *,
        contradiction_case_id: UUID,
        **kwargs: object,
    ) -> dict[str, object] | None:
        existing = self._cases.get(contradiction_case_id)
        if existing is None:
            return None
        updated = {
            **existing,
            **kwargs,
            "updated_at": self._tick(),
        }
        self._cases[contradiction_case_id] = updated
        return dict(updated)

    def get_contradiction_case_optional(self, contradiction_case_id: UUID) -> dict[str, object] | None:
        record = self._cases.get(contradiction_case_id)
        return None if record is None else dict(record)

    def list_contradiction_cases(
        self,
        *,
        statuses: list[str],
        limit: int,
        continuity_object_id: UUID | None,
    ) -> list[dict[str, object]]:
        rows = [
            dict(row)
            for row in self._cases.values()
            if row["status"] in statuses
            and (
                continuity_object_id is None
                or row["continuity_object_id"] == continuity_object_id
                or row["counterpart_object_id"] == continuity_object_id
            )
        ]
        rows.sort(key=lambda row: (row["updated_at"], str(row["id"])), reverse=True)
        return rows[:limit]

    def count_contradiction_cases(
        self,
        *,
        statuses: list[str],
        continuity_object_id: UUID | None,
    ) -> int:
        return len(
            self.list_contradiction_cases(
                statuses=statuses,
                limit=10_000,
                continuity_object_id=continuity_object_id,
            )
        )

    def list_contradiction_cases_for_objects(
        self,
        *,
        continuity_object_ids: list[UUID],
        statuses: list[str],
    ) -> list[dict[str, object]]:
        requested = set(continuity_object_ids)
        rows = [
            dict(row)
            for row in self._cases.values()
            if row["status"] in statuses
            and (
                row["continuity_object_id"] in requested
                or row["counterpart_object_id"] in requested
            )
        ]
        rows.sort(key=lambda row: (row["updated_at"], str(row["id"])), reverse=True)
        return rows

    def upsert_trust_signal(
        self,
        *,
        continuity_object_id: UUID,
        signal_key: str,
        signal_type: str,
        signal_state: str,
        direction: str,
        magnitude: float,
        reason: str,
        contradiction_case_id: UUID | None,
        related_continuity_object_id: UUID | None,
        payload: dict[str, object],
    ) -> dict[str, object]:
        now = self._tick()
        key = (continuity_object_id, signal_key)
        existing = self._signals.get(key)
        row = {
            "id": existing["id"] if existing is not None else uuid4(),
            "continuity_object_id": continuity_object_id,
            "signal_key": signal_key,
            "signal_type": signal_type,
            "signal_state": signal_state,
            "direction": direction,
            "magnitude": magnitude,
            "reason": reason,
            "contradiction_case_id": contradiction_case_id,
            "related_continuity_object_id": related_continuity_object_id,
            "payload": dict(payload),
            "created_at": existing["created_at"] if existing is not None else now,
            "updated_at": now,
        }
        self._signals[key] = row
        return dict(row)

    def list_trust_signals(
        self,
        *,
        limit: int,
        continuity_object_id: UUID | None,
        signal_state: str | None,
        signal_type: str | None,
    ) -> list[dict[str, object]]:
        rows = [
            dict(row)
            for row in self._signals.values()
            if (continuity_object_id is None or row["continuity_object_id"] == continuity_object_id)
            and (signal_state is None or row["signal_state"] == signal_state)
            and (signal_type is None or row["signal_type"] == signal_type)
        ]
        rows.sort(key=lambda row: (row["updated_at"], str(row["id"])), reverse=True)
        return rows[:limit]

    def count_trust_signals(
        self,
        *,
        continuity_object_id: UUID | None,
        signal_state: str | None,
        signal_type: str | None,
    ) -> int:
        return len(
            self.list_trust_signals(
                limit=10_000,
                continuity_object_id=continuity_object_id,
                signal_state=signal_state,
                signal_type=signal_type,
            )
        )


def make_candidate_row(
    *,
    subject: str,
    value: str,
    created_at: datetime,
) -> dict[str, object]:
    object_id = uuid4()
    return {
        "id": object_id,
        "user_id": UUID("11111111-1111-4111-8111-111111111111"),
        "capture_event_id": uuid4(),
        "object_type": "Decision",
        "status": "active",
        "is_preserved": True,
        "is_searchable": True,
        "is_promotable": True,
        "title": f"Decision: Release mode {value}",
        "body": {
            "fact_key": subject,
            "fact_value": value,
            "decision_text": f"Release mode {value}",
        },
        "provenance": {"thread_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},
        "confidence": 0.95,
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


def test_sync_detects_contradictions_persists_trust_and_preserves_resolution_state() -> None:
    left = make_candidate_row(
        subject="release_mode",
        value="canary",
        created_at=datetime(2026, 4, 14, 10, 0, tzinfo=UTC),
    )
    right = make_candidate_row(
        subject="release_mode",
        value="beta",
        created_at=datetime(2026, 4, 14, 10, 5, tzinfo=UTC),
    )
    store = InMemoryContradictionStore([left, right])

    first_sync = sync_contradiction_state_for_objects(
        store,  # type: ignore[arg-type]
        continuity_object_ids=[left["id"], right["id"]],
    )

    assert first_sync.scanned_object_count == 2
    assert first_sync.open_case_count == 1
    assert first_sync.resolved_case_count == 0
    assert first_sync.updated_case_count == 1

    summary = build_explanation_contradiction_summary(
        store,  # type: ignore[arg-type]
        continuity_object_id=left["id"],
    )
    assert summary["open_case_count"] == 1
    assert summary["resolved_case_count"] == 0
    assert summary["kinds"] == ["direct_fact_conflict"]
    assert summary["penalty_score"] == 2.0

    metrics = contradiction_metrics_by_object(
        store,  # type: ignore[arg-type]
        continuity_object_ids=[left["id"], right["id"]],
    )
    assert metrics[left["id"]] == (1, 2.0)
    assert metrics[right["id"]] == (1, 2.0)

    active_signals = list_trust_signals(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=TrustSignalListQueryInput(
            continuity_object_id=left["id"],
            signal_state="active",
            signal_type=None,
            limit=20,
        ),
        sync_first=False,
    )
    assert active_signals["summary"]["returned_count"] == 1
    assert active_signals["items"][0]["signal_type"] == "contradiction"
    assert active_signals["items"][0]["direction"] == "negative"

    contradiction_case_id = first_sync.cases[0]["id"]
    resolved = resolve_contradiction_case(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        contradiction_case_id=contradiction_case_id,
        request=ContradictionResolveInput(
            action="confirm_primary",
            note="Primary record remains canonical.",
        ),
    )
    assert resolved["contradiction_case"]["status"] == "resolved"
    assert resolved["contradiction_case"]["resolution_action"] == "confirm_primary"
    assert resolved["contradiction_case"]["resolution_note"] == "Primary record remains canonical."

    resolved_summary = build_explanation_contradiction_summary(
        store,  # type: ignore[arg-type]
        continuity_object_id=left["id"],
    )
    assert resolved_summary["open_case_count"] == 0
    assert resolved_summary["resolved_case_count"] == 1
    assert resolved_summary["penalty_score"] == 0.0

    active_signals_after = list_trust_signals(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=TrustSignalListQueryInput(
            continuity_object_id=left["id"],
            signal_state="active",
            signal_type=None,
            limit=20,
        ),
        sync_first=False,
    )
    assert active_signals_after["items"] == []


def test_sync_resolves_existing_case_when_one_side_becomes_superseded() -> None:
    left = make_candidate_row(
        subject="release_mode",
        value="canary",
        created_at=datetime(2026, 4, 14, 10, 0, tzinfo=UTC),
    )
    right = make_candidate_row(
        subject="release_mode",
        value="beta",
        created_at=datetime(2026, 4, 14, 10, 5, tzinfo=UTC),
    )
    store = InMemoryContradictionStore([left, right])

    first_sync = sync_contradiction_state_for_objects(
        store,  # type: ignore[arg-type]
        continuity_object_ids=[left["id"], right["id"]],
    )
    assert first_sync.open_case_count == 1

    store._rows[0]["status"] = "superseded"
    store._rows[0]["superseded_by_object_id"] = right["id"]
    store._objects[left["id"]]["status"] = "superseded"
    store._objects[left["id"]]["superseded_by_object_id"] = right["id"]

    second_sync = sync_contradiction_state_for_objects(
        store,  # type: ignore[arg-type]
        continuity_object_ids=[left["id"], right["id"]],
    )

    assert second_sync.open_case_count == 0
    assert second_sync.resolved_case_count == 1
    assert second_sync.updated_case_count == 1

    right_summary = build_explanation_contradiction_summary(
        store,  # type: ignore[arg-type]
        continuity_object_id=right["id"],
    )
    assert right_summary["open_case_count"] == 0
    assert right_summary["resolved_case_count"] == 1
    assert right_summary["penalty_score"] == 0.0

    active_right_signals = list_trust_signals(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
        request=TrustSignalListQueryInput(
            continuity_object_id=right["id"],
            signal_state="active",
            signal_type=None,
            limit=20,
        ),
        sync_first=False,
    )
    assert active_right_signals["items"] == []


def test_sync_normalizes_naive_temporal_strings_before_overlap_detection() -> None:
    left = make_candidate_row(
        subject="release_window",
        value="canary",
        created_at=datetime(2026, 4, 14, 10, 0, tzinfo=UTC),
    )
    left["body"] = {
        "fact_key": "release_window",
        "fact_value": "canary",
        "decision_text": "Release window canary",
        "valid_from": "2026-04-14",
        "valid_to": "2026-04-20",
    }

    right = make_candidate_row(
        subject="release_window",
        value="beta",
        created_at=datetime(2026, 4, 14, 10, 5, tzinfo=UTC),
    )
    right["body"] = {
        "fact_key": "release_window",
        "fact_value": "beta",
        "decision_text": "Release window beta",
        "valid_from": "2026-04-15T09:00:00",
        "valid_to": "2026-04-21T18:00:00",
    }

    store = InMemoryContradictionStore([left, right])

    sync = sync_contradiction_state_for_objects(
        store,  # type: ignore[arg-type]
        continuity_object_ids=[left["id"], right["id"]],
    )

    assert sync.open_case_count == 1
    assert sync.cases[0]["kind"] == "temporal_conflict"
