from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import psycopg

from alicebot_api.continuity_contradictions import sync_contradiction_state_for_objects
from alicebot_api.contracts import (
    ThreadActivityPosture,
    ThreadHealthDashboardResponse,
    ThreadHealthDashboardSummary,
    ThreadHealthPosture,
    ThreadHealthRecord,
    ThreadHealthThresholdsRecord,
    ThreadRecord,
    ThreadRiskPosture,
)
from alicebot_api.store import (
    ContinuityRecallCandidateRow,
    ContinuityStore,
    EventRow,
    SessionRow,
    ThreadRow,
)

_RECENT_THREAD_WINDOW_HOURS = 24.0
_STALE_THREAD_WINDOW_HOURS = 72.0
_RISKY_THREAD_SCORE_THRESHOLD = 2
_OPEN_LOOP_OBJECT_TYPES = {"WaitingFor", "Blocker", "NextAction"}
_CONVERSATION_EVENT_KINDS = {"message.user", "message.assistant"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _serialize_thread(thread: ThreadRow) -> ThreadRecord:
    return {
        "id": str(thread["id"]),
        "title": thread["title"],
        "agent_profile_id": thread["agent_profile_id"],
        "created_at": thread["created_at"].isoformat(),
        "updated_at": thread["updated_at"].isoformat(),
    }


def _hours_since(now: datetime, value: datetime | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, (now - value).total_seconds() / 3600.0), 6)


def _thread_id_from_provenance(row: ContinuityRecallCandidateRow) -> UUID | None:
    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        return None
    raw_thread_id = provenance.get("thread_id")
    if isinstance(raw_thread_id, UUID):
        return raw_thread_id
    if isinstance(raw_thread_id, str):
        try:
            return UUID(raw_thread_id)
        except ValueError:
            return None
    return None


def _activity_posture(hours_since_last_activity: float | None) -> ThreadActivityPosture:
    if hours_since_last_activity is None or hours_since_last_activity <= _RECENT_THREAD_WINDOW_HOURS:
        return "recent"
    if hours_since_last_activity <= _STALE_THREAD_WINDOW_HOURS:
        return "current"
    return "stale"


def _risk_posture(score: int) -> ThreadRiskPosture:
    if score >= _RISKY_THREAD_SCORE_THRESHOLD:
        return "risky"
    if score > 0:
        return "watch"
    return "normal"


def _health_posture(
    *,
    activity_posture: ThreadActivityPosture,
    risk_posture: ThreadRiskPosture,
) -> ThreadHealthPosture:
    if risk_posture == "risky":
        return "critical"
    if activity_posture == "stale" or risk_posture == "watch":
        return "watch"
    return "healthy"


def _recommended_action(
    *,
    risk_posture: ThreadRiskPosture,
    activity_posture: ThreadActivityPosture,
    unresolved_contradiction_count: int,
    stale_open_loop_count: int,
    weak_trust_signal_count: int,
) -> str:
    if unresolved_contradiction_count > 0:
        return "Resolve contradiction cases before trusting this thread for recall or briefing."
    if stale_open_loop_count > 0:
        return "Review stale waiting-for or blocker items linked to this thread."
    if weak_trust_signal_count > 0:
        return "Corroborate weakly supported continuity objects before reuse."
    if risk_posture == "watch":
        return "Inspect recent continuity changes before continuing the thread."
    if activity_posture == "stale":
        return "Refresh thread context before resuming work."
    return "No immediate intervention required."


def _thread_reasons(
    *,
    hours_since_last_activity: float | None,
    active_session_count: int,
    stale_open_loop_count: int,
    unresolved_contradiction_count: int,
    weak_trust_signal_count: int,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if unresolved_contradiction_count > 0:
        score += 2
        reasons.append(f"{unresolved_contradiction_count} unresolved contradiction case(s).")

    if stale_open_loop_count > 0:
        score += 1
        reasons.append(f"{stale_open_loop_count} stale open-loop item(s).")

    if weak_trust_signal_count > 0:
        score += 1
        reasons.append(f"{weak_trust_signal_count} active weak-trust signal(s).")

    if active_session_count > 0 and hours_since_last_activity is not None and hours_since_last_activity > _RECENT_THREAD_WINDOW_HOURS:
        score += 1
        reasons.append(
            f"Active session has been quiet for {hours_since_last_activity:.1f}h."
        )

    if not reasons:
        reasons.append("No active contradiction, stale open-loop, or weak-trust pressure is currently visible.")

    return score, reasons


def _sort_thread_item(item: ThreadHealthRecord) -> tuple[int, int, float, str]:
    health_priority = {"critical": 2, "watch": 1, "healthy": 0}[item["health_posture"]]
    activity_hours = item["hours_since_last_activity"]
    return (
        health_priority,
        item["risk_score"],
        0.0 if activity_hours is None else activity_hours,
        item["thread"]["updated_at"],
    )


def _safe_sync_contradictions(store: ContinuityStore) -> None:
    try:
        sync_contradiction_state_for_objects(store, continuity_object_ids=None)
    except psycopg.errors.UndefinedTable:
        return


def _weak_trust_counts_by_thread(
    store: ContinuityStore,
    *,
    thread_by_object_id: dict[UUID, UUID],
) -> dict[UUID, int]:
    counts: dict[UUID, int] = {thread_id: 0 for thread_id in thread_by_object_id.values()}

    if hasattr(store, "count_trust_signals"):
        for object_id, thread_id in thread_by_object_id.items():
            try:
                counts[thread_id] += store.count_trust_signals(
                    continuity_object_id=object_id,
                    signal_state="active",
                    signal_type="weak_inference",
                )
            except psycopg.errors.UndefinedTable:
                return counts
        return counts

    if hasattr(store, "list_trust_signals"):
        for object_id, thread_id in thread_by_object_id.items():
            try:
                signals = store.list_trust_signals(
                    limit=10_000,
                    continuity_object_id=object_id,
                    signal_state="active",
                    signal_type="weak_inference",
                )
            except psycopg.errors.UndefinedTable:
                return counts
            counts[thread_id] += len(signals)

    return counts


def get_thread_health_dashboard(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> ThreadHealthDashboardResponse:
    del user_id

    now = _utcnow()
    threads = store.list_threads()
    thread_ids = {thread["id"] for thread in threads}
    sessions_by_thread: dict[UUID, list[SessionRow]] = {
        thread_id: store.list_thread_sessions(thread_id) for thread_id in thread_ids
    }
    events_by_thread: dict[UUID, list[EventRow]] = {
        thread_id: store.list_thread_events(thread_id) for thread_id in thread_ids
    }

    recall_by_thread: dict[UUID, list[ContinuityRecallCandidateRow]] = {thread_id: [] for thread_id in thread_ids}
    contradiction_counts_by_thread: dict[UUID, int] = {thread_id: 0 for thread_id in thread_ids}
    weak_trust_counts_by_thread: dict[UUID, int] = {thread_id: 0 for thread_id in thread_ids}

    recall_candidates: list[ContinuityRecallCandidateRow] = []
    if hasattr(store, "list_continuity_recall_candidates"):
        try:
            recall_candidates = store.list_continuity_recall_candidates()
        except psycopg.errors.UndefinedTable:
            recall_candidates = []

    recall_object_ids: list[UUID] = []
    for row in recall_candidates:
        thread_id = _thread_id_from_provenance(row)
        if thread_id is None or thread_id not in recall_by_thread:
            continue
        recall_by_thread[thread_id].append(row)
        recall_object_ids.append(row["id"])

    if recall_object_ids and hasattr(store, "list_contradiction_cases_for_objects"):
        _safe_sync_contradictions(store)
        try:
            cases = store.list_contradiction_cases_for_objects(
                continuity_object_ids=recall_object_ids,
                statuses=["open"],
            )
        except psycopg.errors.UndefinedTable:
            cases = []
        thread_by_object_id = {
            row["id"]: thread_id
            for thread_id, rows in recall_by_thread.items()
            for row in rows
        }
        counted_case_ids: dict[UUID, set[UUID]] = {thread_id: set() for thread_id in thread_ids}
        for case in cases:
            for object_id in (case["continuity_object_id"], case["counterpart_object_id"]):
                thread_id = thread_by_object_id.get(object_id)
                if thread_id is None or case["id"] in counted_case_ids[thread_id]:
                    continue
                counted_case_ids[thread_id].add(case["id"])
                contradiction_counts_by_thread[thread_id] += 1

    if recall_object_ids:
        thread_by_object_id = {
            row["id"]: thread_id
            for thread_id, rows in recall_by_thread.items()
            for row in rows
        }
        weak_trust_counts_by_thread.update(
            _weak_trust_counts_by_thread(
                store,
                thread_by_object_id=thread_by_object_id,
            )
        )

    items: list[ThreadHealthRecord] = []
    for thread in threads:
        thread_id = thread["id"]
        sessions = sessions_by_thread.get(thread_id, [])
        events = events_by_thread.get(thread_id, [])
        recall_rows = recall_by_thread.get(thread_id, [])

        conversation_events = [event for event in events if event["kind"] in _CONVERSATION_EVENT_KINDS]
        last_conversation_at = (
            max((event["created_at"] for event in conversation_events), default=None)
            if conversation_events
            else None
        )
        candidate_activity_times = [thread["updated_at"]]
        candidate_activity_times.extend(session["created_at"] for session in sessions)
        candidate_activity_times.extend(event["created_at"] for event in events)
        last_activity_at = max(candidate_activity_times) if candidate_activity_times else None
        hours_since_last_activity = _hours_since(now, last_activity_at)

        open_loop_rows = [
            row
            for row in recall_rows
            if row["object_type"] in _OPEN_LOOP_OBJECT_TYPES and row["status"] in {"active", "stale"}
        ]
        stale_open_loop_count = sum(1 for row in open_loop_rows if row["status"] == "stale")
        active_session_count = sum(1 for session in sessions if session["status"] == "active")
        unresolved_contradiction_count = contradiction_counts_by_thread.get(thread_id, 0)
        weak_trust_signal_count = weak_trust_counts_by_thread.get(thread_id, 0)
        score, reasons = _thread_reasons(
            hours_since_last_activity=hours_since_last_activity,
            active_session_count=active_session_count,
            stale_open_loop_count=stale_open_loop_count,
            unresolved_contradiction_count=unresolved_contradiction_count,
            weak_trust_signal_count=weak_trust_signal_count,
        )
        activity_posture = _activity_posture(hours_since_last_activity)
        risk_posture = _risk_posture(score)
        health_posture = _health_posture(
            activity_posture=activity_posture,
            risk_posture=risk_posture,
        )

        items.append(
            {
                "thread": _serialize_thread(thread),
                "health_posture": health_posture,
                "activity_posture": activity_posture,
                "risk_posture": risk_posture,
                "risk_score": score,
                "last_activity_at": None if last_activity_at is None else last_activity_at.isoformat(),
                "last_conversation_at": (
                    None if last_conversation_at is None else last_conversation_at.isoformat()
                ),
                "hours_since_last_activity": hours_since_last_activity,
                "conversation_event_count": len(conversation_events),
                "operational_event_count": max(0, len(events) - len(conversation_events)),
                "active_session_count": active_session_count,
                "open_loop_count": len(open_loop_rows),
                "stale_open_loop_count": stale_open_loop_count,
                "unresolved_contradiction_count": unresolved_contradiction_count,
                "weak_trust_signal_count": weak_trust_signal_count,
                "reasons": reasons,
                "recommended_action": _recommended_action(
                    risk_posture=risk_posture,
                    activity_posture=activity_posture,
                    unresolved_contradiction_count=unresolved_contradiction_count,
                    stale_open_loop_count=stale_open_loop_count,
                    weak_trust_signal_count=weak_trust_signal_count,
                ),
            }
        )

    ordered_items = sorted(items, key=_sort_thread_item, reverse=True)
    recent_threads = sorted(
        [item for item in ordered_items if item["activity_posture"] == "recent"],
        key=lambda item: (item["last_activity_at"] or "", item["thread"]["id"]),
        reverse=True,
    )
    stale_threads = sorted(
        [item for item in ordered_items if item["activity_posture"] == "stale"],
        key=lambda item: (item["hours_since_last_activity"] or 0.0, item["thread"]["id"]),
        reverse=True,
    )
    risky_threads = sorted(
        [item for item in ordered_items if item["risk_posture"] == "risky"],
        key=lambda item: (item["risk_score"], item["hours_since_last_activity"] or 0.0, item["thread"]["id"]),
        reverse=True,
    )
    watch_thread_count = sum(1 for item in ordered_items if item["health_posture"] == "watch")
    risky_thread_count = len(risky_threads)
    stale_thread_count = len(stale_threads)

    if risky_thread_count > 0:
        posture: ThreadHealthPosture = "critical"
    elif stale_thread_count > 0 or watch_thread_count > 0:
        posture = "watch"
    else:
        posture = "healthy"

    thresholds: ThreadHealthThresholdsRecord = {
        "recent_window_hours": _RECENT_THREAD_WINDOW_HOURS,
        "stale_window_hours": _STALE_THREAD_WINDOW_HOURS,
        "risky_score_threshold": _RISKY_THREAD_SCORE_THRESHOLD,
    }
    dashboard: ThreadHealthDashboardSummary = {
        "posture": posture,
        "total_thread_count": len(ordered_items),
        "recent_thread_count": len(recent_threads),
        "stale_thread_count": stale_thread_count,
        "risky_thread_count": risky_thread_count,
        "watch_thread_count": watch_thread_count,
        "thresholds": thresholds,
        "recent_threads": recent_threads,
        "stale_threads": stale_threads,
        "risky_threads": risky_threads,
        "items": ordered_items,
        "sources": [
            "threads",
            "thread_sessions",
            "thread_events",
            "continuity_recall",
            "contradiction_cases",
            "trust_signals",
        ],
    }
    return {"dashboard": dashboard}


__all__ = ["get_thread_health_dashboard"]
