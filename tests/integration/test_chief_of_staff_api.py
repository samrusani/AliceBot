from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio
import psycopg

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


def invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, object]] = []
    encoded_body = b"" if payload is None else json.dumps(payload).encode()
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}

        request_received = True
        return {"type": "http.request", "body": encoded_body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    query_string = urlencode(query_params or {}).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": [(b"content-type", b"application/json")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }

    anyio.run(main_module.app, scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start_message["status"], json.loads(body)


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def set_continuity_timestamps(
    admin_database_url: str,
    *,
    continuity_object_id: UUID,
    created_at: datetime,
) -> None:
    with psycopg.connect(admin_database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE continuity_objects SET created_at = %s, updated_at = %s WHERE id = %s",
                (created_at, created_at, continuity_object_id),
            )


def test_chief_of_staff_priority_brief_is_deterministic_and_trust_aware(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="chief-of-staff@example.com")
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)

        next_capture = store.create_continuity_capture_event(
            raw_content="Next Action: Ship the dashboard",
            explicit_signal="next_action",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_next_action",
        )
        next_object = store.create_continuity_object(
            capture_event_id=next_capture["id"],
            object_type="NextAction",
            status="active",
            title="Next Action: Ship the dashboard",
            body={"action_text": "Ship the dashboard", "confirmation_status": "confirmed"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-next"]},
            confidence=1.0,
        )

        commitment_capture = store.create_continuity_capture_event(
            raw_content="Commitment: Publish sprint report",
            explicit_signal="commitment",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_commitment",
        )
        commitment_object = store.create_continuity_object(
            capture_event_id=commitment_capture["id"],
            object_type="Commitment",
            status="active",
            title="Commitment: Publish sprint report",
            body={"commitment_text": "Publish sprint report", "confirmation_status": "confirmed"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-commitment"]},
            confidence=0.95,
        )

        waiting_capture = store.create_continuity_capture_event(
            raw_content="Waiting For: Vendor legal review",
            explicit_signal="waiting_for",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_waiting_for",
        )
        waiting_object = store.create_continuity_object(
            capture_event_id=waiting_capture["id"],
            object_type="WaitingFor",
            status="active",
            title="Waiting For: Vendor legal review",
            body={"waiting_for_text": "Vendor legal review"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-waiting"]},
            confidence=0.9,
        )

        blocker_capture = store.create_continuity_capture_event(
            raw_content="Blocker: Missing release token",
            explicit_signal="blocker",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_blocker",
        )
        blocker_object = store.create_continuity_object(
            capture_event_id=blocker_capture["id"],
            object_type="Blocker",
            status="active",
            title="Blocker: Missing release token",
            body={"blocking_reason": "Missing release token"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-blocker"]},
            confidence=0.9,
        )

        stale_capture = store.create_continuity_capture_event(
            raw_content="Waiting For: Old finance response",
            explicit_signal="waiting_for",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_waiting_for",
        )
        stale_object = store.create_continuity_object(
            capture_event_id=stale_capture["id"],
            object_type="WaitingFor",
            status="stale",
            title="Waiting For: Old finance response",
            body={"waiting_for_text": "Old finance response"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-stale"]},
            confidence=0.85,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=next_object["id"],
        created_at=datetime(2026, 3, 31, 10, 5, tzinfo=UTC),
    )
    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=commitment_object["id"],
        created_at=datetime(2026, 3, 28, 10, 0, tzinfo=UTC),
    )
    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=waiting_object["id"],
        created_at=datetime(2026, 3, 31, 9, 30, tzinfo=UTC),
    )
    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=blocker_object["id"],
        created_at=datetime(2026, 3, 23, 9, 0, tzinfo=UTC),
    )
    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=stale_object["id"],
        created_at=datetime(2026, 3, 27, 8, 30, tzinfo=UTC),
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    params = {
        "user_id": str(user_id),
        "thread_id": str(thread_id),
        "limit": "5",
    }

    status_one, payload_one = invoke_request("GET", "/v0/chief-of-staff", query_params=params)
    status_two, payload_two = invoke_request("GET", "/v0/chief-of-staff", query_params=params)

    assert status_one == 200
    assert status_two == 200
    assert payload_one == payload_two

    brief = payload_one["brief"]
    assert brief["assembly_version"] == "chief_of_staff_priority_brief_v0"
    assert brief["summary"]["posture_order"] == ["urgent", "important", "waiting", "blocked", "stale", "defer"]
    assert brief["summary"]["follow_through_posture_order"] == [
        "overdue",
        "stale_waiting_for",
        "slipped_commitment",
    ]
    assert brief["summary"]["follow_through_item_order"] == [
        "recommendation_action_desc",
        "age_hours_desc",
        "created_at_desc",
        "id_desc",
    ]
    assert brief["summary"]["quality_gate_status"] == "insufficient_sample"
    assert brief["summary"]["trust_confidence_posture"] == "low"

    ranked = brief["ranked_items"]
    assert ranked[0]["title"] == "Next Action: Ship the dashboard"
    assert ranked[0]["priority_posture"] == "urgent"
    assert ranked[0]["confidence_posture"] == "low"
    assert ranked[0]["rationale"]["trust_signals"]["downgraded_by_trust"] is True
    assert ranked[0]["rationale"]["provenance_references"]
    assert ranked[0]["rationale"]["reasons"]

    assert {item["priority_posture"] for item in ranked} >= {"urgent", "waiting", "blocked", "stale"}
    assert brief["summary"]["follow_through_total_count"] >= 3
    assert brief["summary"]["overdue_count"] >= 1
    assert brief["summary"]["stale_waiting_for_count"] >= 1
    assert brief["summary"]["slipped_commitment_count"] >= 1
    assert brief["overdue_items"]
    assert brief["overdue_items"][0]["recommendation_action"] == "escalate"
    assert brief["stale_waiting_for_items"]
    assert brief["slipped_commitments"]
    assert brief["escalation_posture"]["posture"] == "critical"
    assert brief["draft_follow_up"]["status"] == "drafted"
    assert brief["draft_follow_up"]["mode"] == "draft_only"
    assert brief["draft_follow_up"]["approval_required"] is True
    assert brief["draft_follow_up"]["auto_send"] is False
    assert brief["draft_follow_up"]["target_metadata"]["continuity_object_id"] == brief["overdue_items"][0]["id"]
    assert "artifact-only" in brief["draft_follow_up"]["content"]["body"]

    recommendation = brief["recommended_next_action"]
    assert recommendation["target_priority_id"] == ranked[0]["id"]
    assert recommendation["confidence_posture"] == "low"
    assert recommendation["action_type"] in {
        "execute_next_action",
        "progress_commitment",
        "follow_up_waiting_for",
        "unblock_blocker",
        "refresh_stale_item",
        "review_and_defer",
        "capture_new_priority",
    }
    assert brief["preparation_brief"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert brief["what_changed_summary"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert brief["prep_checklist"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert brief["suggested_talking_points"]["summary"]["order"] == [
        "rank_asc",
        "created_at_desc",
        "id_desc",
    ]
    assert brief["resumption_supervision"]["summary"]["order"] == [
        "rank_asc",
    ]
    assert brief["preparation_brief"]["confidence_posture"] == "low"
    assert brief["what_changed_summary"]["confidence_posture"] == "low"
    assert brief["prep_checklist"]["confidence_posture"] == "low"
    assert brief["suggested_talking_points"]["confidence_posture"] == "low"
    assert brief["resumption_supervision"]["confidence_posture"] == "low"
    assert brief["preparation_brief"]["context_items"]
    assert brief["what_changed_summary"]["items"]
    assert brief["prep_checklist"]["items"]
    assert brief["suggested_talking_points"]["items"]
    assert brief["resumption_supervision"]["recommendations"]
    assert any(
        recommendation["action"] == "review_scope" and recommendation["provenance_references"]
        for recommendation in brief["resumption_supervision"]["recommendations"]
    )
