from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import alicebot_api.conversation_health as conversation_health_module
from alicebot_api.conversation_health import get_thread_health_dashboard


class ThreadHealthStoreStub:
    def __init__(self) -> None:
        self.threads: list[dict[str, object]] = []
        self.sessions: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []
        self.recall_candidates: list[dict[str, object]] = []
        self.contradiction_cases: list[dict[str, object]] = []
        self.trust_signals: list[dict[str, object]] = []

    def list_threads(self) -> list[dict[str, object]]:
        return list(self.threads)

    def list_thread_sessions(self, thread_id: UUID) -> list[dict[str, object]]:
        return [session for session in self.sessions if session["thread_id"] == thread_id]

    def list_thread_events(self, thread_id: UUID) -> list[dict[str, object]]:
        return [event for event in self.events if event["thread_id"] == thread_id]

    def list_continuity_recall_candidates(self) -> list[dict[str, object]]:
        return list(self.recall_candidates)

    def list_contradiction_cases_for_objects(
        self,
        *,
        continuity_object_ids: list[UUID],
        statuses: list[str],
    ) -> list[dict[str, object]]:
        assert statuses == ["open"]
        return [
            case
            for case in self.contradiction_cases
            if case["status"] in statuses
            and (
                case["continuity_object_id"] in continuity_object_ids
                or case["counterpart_object_id"] in continuity_object_ids
            )
        ]

    def list_trust_signals(
        self,
        *,
        limit: int,
        continuity_object_id: UUID | None = None,
        signal_state: str | None = None,
        signal_type: str | None = None,
    ) -> list[dict[str, object]]:
        signals = list(self.trust_signals)
        if continuity_object_id is not None:
            signals = [signal for signal in signals if signal["continuity_object_id"] == continuity_object_id]
        if signal_state is not None:
            signals = [signal for signal in signals if signal["signal_state"] == signal_state]
        if signal_type is not None:
            signals = [signal for signal in signals if signal["signal_type"] == signal_type]
        return signals[:limit]

    def count_trust_signals(
        self,
        *,
        continuity_object_id: UUID | None = None,
        signal_state: str | None = None,
        signal_type: str | None = None,
    ) -> int:
        return len(
            self.list_trust_signals(
                limit=10_000,
                continuity_object_id=continuity_object_id,
                signal_state=signal_state,
                signal_type=signal_type,
            )
        )


def test_get_thread_health_dashboard_surfaces_recent_stale_and_risky_threads(
    monkeypatch,
) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(conversation_health_module, "_utcnow", lambda: now)

    store = ThreadHealthStoreStub()
    recent_thread_id = UUID("00000000-0000-4000-8000-000000000001")
    stale_thread_id = UUID("00000000-0000-4000-8000-000000000002")
    risky_thread_id = UUID("00000000-0000-4000-8000-000000000003")
    risky_object_id = UUID("10000000-0000-4000-8000-000000000001")
    stale_object_id = UUID("10000000-0000-4000-8000-000000000002")

    store.threads = [
        {
            "id": recent_thread_id,
            "user_id": uuid4(),
            "title": "Recent thread",
            "agent_profile_id": "assistant_default",
            "created_at": now - timedelta(hours=6),
            "updated_at": now - timedelta(hours=2),
        },
        {
            "id": stale_thread_id,
            "user_id": uuid4(),
            "title": "Stale thread",
            "agent_profile_id": "assistant_default",
            "created_at": now - timedelta(days=7),
            "updated_at": now - timedelta(days=5),
        },
        {
            "id": risky_thread_id,
            "user_id": uuid4(),
            "title": "Risky thread",
            "agent_profile_id": "assistant_default",
            "created_at": now - timedelta(days=2),
            "updated_at": now - timedelta(hours=30),
        },
    ]
    store.sessions = [
        {
            "id": uuid4(),
            "thread_id": recent_thread_id,
            "status": "active",
            "started_at": now - timedelta(hours=3),
            "ended_at": None,
            "created_at": now - timedelta(hours=3),
        }
    ]
    store.events = [
        {
            "id": uuid4(),
            "thread_id": recent_thread_id,
            "session_id": None,
            "sequence_no": 1,
            "kind": "message.user",
            "payload": {"text": "hello"},
            "created_at": now - timedelta(hours=2),
        },
        {
            "id": uuid4(),
            "thread_id": stale_thread_id,
            "session_id": None,
            "sequence_no": 1,
            "kind": "message.assistant",
            "payload": {"text": "later"},
            "created_at": now - timedelta(days=5),
        },
        {
            "id": uuid4(),
            "thread_id": risky_thread_id,
            "session_id": None,
            "sequence_no": 1,
            "kind": "message.user",
            "payload": {"text": "conflict"},
            "created_at": now - timedelta(hours=30),
        },
    ]
    store.recall_candidates = [
        {
            "id": stale_object_id,
            "capture_event_id": uuid4(),
            "object_type": "WaitingFor",
            "status": "stale",
            "is_preserved": True,
            "is_searchable": True,
            "is_promotable": True,
            "title": "Need vendor follow-up",
            "body": {"waiting_for_text": "Vendor reply"},
            "provenance": {"thread_id": str(stale_thread_id)},
            "confidence": 0.9,
            "last_confirmed_at": None,
            "supersedes_object_id": None,
            "superseded_by_object_id": None,
            "object_created_at": now - timedelta(days=6),
            "object_updated_at": now - timedelta(days=5),
            "admission_posture": "DERIVED",
        },
        {
            "id": risky_object_id,
            "capture_event_id": uuid4(),
            "object_type": "Decision",
            "status": "active",
            "is_preserved": True,
            "is_searchable": True,
            "is_promotable": True,
            "title": "Conflicting preference",
            "body": {"decision_text": "Use provider A"},
            "provenance": {"thread_id": str(risky_thread_id)},
            "confidence": 0.7,
            "last_confirmed_at": None,
            "supersedes_object_id": None,
            "superseded_by_object_id": None,
            "object_created_at": now - timedelta(days=2),
            "object_updated_at": now - timedelta(hours=30),
            "admission_posture": "DERIVED",
        },
    ]
    store.contradiction_cases = [
        {
            "id": uuid4(),
            "continuity_object_id": risky_object_id,
            "counterpart_object_id": uuid4(),
            "status": "open",
        }
    ]
    store.trust_signals = [
        {
            "id": uuid4(),
            "continuity_object_id": risky_object_id,
            "signal_key": "weak_inference:risky",
            "signal_type": "weak_inference",
            "signal_state": "active",
            "direction": "negative",
            "magnitude": 0.35,
            "reason": "Structured continuity state exists without corroborating evidence.",
            "contradiction_case_id": None,
            "related_continuity_object_id": None,
            "payload": {},
            "created_at": now - timedelta(hours=29),
            "updated_at": now - timedelta(hours=29),
        }
    ]

    payload = get_thread_health_dashboard(store, user_id=uuid4())  # type: ignore[arg-type]

    assert payload["dashboard"]["posture"] == "critical"
    assert payload["dashboard"]["recent_thread_count"] == 1
    assert payload["dashboard"]["stale_thread_count"] == 1
    assert payload["dashboard"]["risky_thread_count"] == 1
    assert payload["dashboard"]["risky_threads"][0]["thread"]["title"] == "Risky thread"
    assert payload["dashboard"]["risky_threads"][0]["unresolved_contradiction_count"] == 1
    assert payload["dashboard"]["risky_threads"][0]["weak_trust_signal_count"] == 1
    assert payload["dashboard"]["stale_threads"][0]["thread"]["title"] == "Stale thread"
    assert payload["dashboard"]["stale_threads"][0]["stale_open_loop_count"] == 1
    assert payload["dashboard"]["recent_threads"][0]["thread"]["title"] == "Recent thread"


def test_get_thread_health_dashboard_counts_weak_trust_without_global_signal_truncation(
    monkeypatch,
) -> None:
    now = datetime(2026, 4, 15, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(conversation_health_module, "_utcnow", lambda: now)

    store = ThreadHealthStoreStub()
    target_thread_id = UUID("00000000-0000-4000-8000-000000000111")
    filler_thread_id = UUID("00000000-0000-4000-8000-000000000112")

    store.threads = [
        {
            "id": target_thread_id,
            "user_id": uuid4(),
            "title": "Target thread",
            "agent_profile_id": "assistant_default",
            "created_at": now - timedelta(hours=8),
            "updated_at": now - timedelta(hours=2),
        },
        {
            "id": filler_thread_id,
            "user_id": uuid4(),
            "title": "Filler thread",
            "agent_profile_id": "assistant_default",
            "created_at": now - timedelta(hours=8),
            "updated_at": now - timedelta(hours=2),
        },
    ]

    filler_object_ids = [
        UUID(f"20000000-0000-4000-8000-{index:012d}")
        for index in range(1, 61)
    ]
    target_object_id = UUID("30000000-0000-4000-8000-000000000001")
    store.recall_candidates = [
        {
            "id": object_id,
            "capture_event_id": uuid4(),
            "object_type": "Decision",
            "status": "active",
            "is_preserved": True,
            "is_searchable": True,
            "is_promotable": True,
            "title": f"Filler object {index}",
            "body": {"decision_text": f"Filler {index}"},
            "provenance": {"thread_id": str(filler_thread_id)},
            "confidence": 0.8,
            "last_confirmed_at": None,
            "supersedes_object_id": None,
            "superseded_by_object_id": None,
            "object_created_at": now - timedelta(hours=7),
            "object_updated_at": now - timedelta(hours=6),
            "admission_posture": "DERIVED",
        }
        for index, object_id in enumerate(filler_object_ids, start=1)
    ]
    store.recall_candidates.append(
        {
            "id": target_object_id,
            "capture_event_id": uuid4(),
            "object_type": "Decision",
            "status": "active",
            "is_preserved": True,
            "is_searchable": True,
            "is_promotable": True,
            "title": "Target object",
            "body": {"decision_text": "Target"},
            "provenance": {"thread_id": str(target_thread_id)},
            "confidence": 0.8,
            "last_confirmed_at": None,
            "supersedes_object_id": None,
            "superseded_by_object_id": None,
            "object_created_at": now - timedelta(hours=7),
            "object_updated_at": now - timedelta(hours=6),
            "admission_posture": "DERIVED",
        }
    )

    for object_id in filler_object_ids:
        for signal_index in range(5):
            store.trust_signals.append(
                {
                    "id": uuid4(),
                    "continuity_object_id": object_id,
                    "signal_key": f"weak_inference:filler:{signal_index}",
                    "signal_type": "weak_inference",
                    "signal_state": "active",
                    "direction": "negative",
                    "magnitude": 0.1,
                    "reason": "Filler weak inference signal.",
                    "contradiction_case_id": None,
                    "related_continuity_object_id": None,
                    "payload": {},
                    "created_at": now - timedelta(hours=5),
                    "updated_at": now - timedelta(hours=5),
                }
            )
    for signal_index in range(5):
        store.trust_signals.append(
            {
                "id": uuid4(),
                "continuity_object_id": target_object_id,
                "signal_key": f"weak_inference:target:{signal_index}",
                "signal_type": "weak_inference",
                "signal_state": "active",
                "direction": "negative",
                "magnitude": 0.2,
                "reason": "Target weak inference signal.",
                "contradiction_case_id": None,
                "related_continuity_object_id": None,
                "payload": {},
                "created_at": now - timedelta(hours=4),
                "updated_at": now - timedelta(hours=4),
            }
        )

    payload = get_thread_health_dashboard(store, user_id=uuid4())  # type: ignore[arg-type]

    target_item = next(
        item for item in payload["dashboard"]["items"] if item["thread"]["id"] == str(target_thread_id)
    )
    assert target_item["weak_trust_signal_count"] == 5
    assert target_item["risk_posture"] == "watch"
