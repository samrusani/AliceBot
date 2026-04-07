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
    assert brief["weekly_review_brief"]["summary"]["guidance_order"] == ["close", "defer", "escalate"]
    assert len(brief["weekly_review_brief"]["guidance"]) == 3
    assert brief["recommendation_outcomes"]["summary"]["total_count"] == 0
    assert brief["priority_learning_summary"]["total_count"] == 0
    assert brief["pattern_drift_summary"]["posture"] == "insufficient_signal"
    assert brief["action_handoff_brief"]["order"] == [
        "score_desc",
        "source_order_asc",
        "source_reference_id_asc",
    ]
    assert brief["action_handoff_brief"]["source_order"] == [
        "recommended_next_action",
        "follow_through",
        "prep_checklist",
        "weekly_review",
    ]
    assert brief["handoff_items"]
    assert brief["summary"]["handoff_item_count"] == len(brief["handoff_items"])
    assert brief["summary"]["handoff_item_order"] == [
        "score_desc",
        "source_order_asc",
        "source_reference_id_asc",
    ]
    assert brief["handoff_queue_summary"]["state_order"] == [
        "ready",
        "pending_approval",
        "executed",
        "stale",
        "expired",
    ]
    assert brief["handoff_queue_summary"]["item_order"] == [
        "queue_rank_asc",
        "handoff_rank_asc",
        "score_desc",
        "handoff_item_id_asc",
    ]
    assert brief["summary"]["handoff_queue_total_count"] == len(brief["handoff_items"])
    assert brief["summary"]["handoff_queue_state_order"] == [
        "ready",
        "pending_approval",
        "executed",
        "stale",
        "expired",
    ]
    assert brief["summary"]["handoff_queue_item_order"] == [
        "queue_rank_asc",
        "handoff_rank_asc",
        "score_desc",
        "handoff_item_id_asc",
    ]
    assert brief["handoff_review_actions"] == []
    assert brief["handoff_outcome_summary"]["total_count"] == 0
    assert brief["handoff_outcome_summary"]["latest_total_count"] == 0
    assert brief["closure_quality_summary"]["posture"] == "insufficient_signal"
    assert brief["conversion_signal_summary"]["total_handoff_count"] == len(brief["handoff_items"])
    assert brief["conversion_signal_summary"]["latest_outcome_count"] == 0
    assert brief["stale_ignored_escalation_posture"]["supporting_signals"]
    assert brief["summary"]["handoff_outcome_total_count"] == 0
    assert brief["summary"]["handoff_outcome_latest_count"] == 0
    assert brief["execution_routing_summary"]["total_handoff_count"] == len(brief["handoff_items"])
    assert brief["execution_routing_summary"]["routed_handoff_count"] == 0
    assert brief["execution_routing_summary"]["route_target_order"] == [
        "task_workflow_draft",
        "approval_workflow_draft",
        "follow_up_draft_only",
    ]
    assert brief["routed_handoff_items"]
    assert brief["routed_handoff_items"][0]["routed_targets"] == []
    assert brief["routing_audit_trail"] == []
    assert brief["execution_readiness_posture"]["posture"] == "approval_required_draft_only"
    assert brief["execution_readiness_posture"]["approval_required"] is True
    assert brief["execution_readiness_posture"]["autonomous_execution"] is False
    assert brief["execution_readiness_posture"]["external_side_effects_allowed"] is False
    assert brief["execution_readiness_posture"]["approval_path_visible"] is True
    assert brief["execution_readiness_posture"]["transition_order"] == ["routed", "reaffirmed"]
    assert brief["summary"]["execution_posture_order"] == ["approval_bounded_artifact_only"]
    assert brief["task_draft"]["source_handoff_item_id"] == brief["handoff_items"][0]["handoff_item_id"]
    assert brief["approval_draft"]["source_handoff_item_id"] == brief["handoff_items"][0]["handoff_item_id"]
    assert brief["task_draft"]["approval_required"] is True
    assert brief["task_draft"]["auto_execute"] is False
    assert brief["approval_draft"]["decision"] == "approval_required"
    assert brief["approval_draft"]["approval_required"] is True
    assert brief["approval_draft"]["auto_submit"] is False
    assert brief["execution_posture"]["posture"] == "approval_bounded_artifact_only"
    assert brief["execution_posture"]["approval_required"] is True
    assert brief["execution_posture"]["autonomous_execution"] is False
    assert brief["execution_posture"]["external_side_effects_allowed"] is False
    assert brief["execution_posture"]["default_routing_decision"] == "approval_required"
    assert "No task, approval, connector send, or external side effect is executed" in brief[
        "execution_posture"
    ]["non_autonomous_guarantee"]


def test_chief_of_staff_handoff_review_action_updates_queue_lifecycle(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="chief-of-staff-queue@example.com")
    thread_id = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        capture = store.create_continuity_capture_event(
            raw_content="Next Action: Queue review validation",
            explicit_signal="next_action",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_next_action",
        )
        continuity_object = store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type="NextAction",
            status="active",
            title="Next Action: Queue review validation",
            body={"action_text": "Queue review validation"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-next"]},
            confidence=0.95,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=continuity_object["id"],
        created_at=datetime(2026, 3, 31, 10, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    status, brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )
    assert status == 200
    handoff_item_id = brief_payload["brief"]["handoff_items"][0]["handoff_item_id"]

    action_status, action_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/handoff-review-actions",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": handoff_item_id,
            "review_action": "mark_stale",
            "thread_id": str(thread_id),
            "note": "operator review test",
        },
    )

    assert action_status == 200
    assert action_payload["review_action"]["handoff_item_id"] == handoff_item_id
    assert action_payload["review_action"]["review_action"] == "mark_stale"
    assert action_payload["review_action"]["next_lifecycle_state"] == "stale"
    assert action_payload["handoff_queue_summary"]["stale_count"] >= 1

    refreshed_status, refreshed_brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )
    assert refreshed_status == 200
    refreshed_brief = refreshed_brief_payload["brief"]
    assert refreshed_brief["handoff_review_actions"]
    assert refreshed_brief["handoff_review_actions"][0]["review_action"] == "mark_stale"
    assert any(
        item["handoff_item_id"] == handoff_item_id
        for item in refreshed_brief["handoff_queue_groups"]["stale"]["items"]
    )


def test_chief_of_staff_execution_routing_action_updates_routing_audit(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="chief-of-staff-routing@example.com")
    thread_id = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        capture = store.create_continuity_capture_event(
            raw_content="Next Action: Governed routing validation",
            explicit_signal="next_action",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_next_action",
        )
        continuity_object = store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type="NextAction",
            status="active",
            title="Next Action: Governed routing validation",
            body={"action_text": "Governed routing validation"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-next"]},
            confidence=0.95,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=continuity_object["id"],
        created_at=datetime(2026, 3, 31, 10, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    status, brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )
    assert status == 200
    handoff_item_id = brief_payload["brief"]["handoff_items"][0]["handoff_item_id"]

    routing_status, routing_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/execution-routing-actions",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": handoff_item_id,
            "route_target": "task_workflow_draft",
            "thread_id": str(thread_id),
            "note": "operator routing test",
        },
    )

    assert routing_status == 200
    assert routing_payload["routing_action"]["handoff_item_id"] == handoff_item_id
    assert routing_payload["routing_action"]["route_target"] == "task_workflow_draft"
    assert routing_payload["routing_action"]["transition"] == "routed"
    assert routing_payload["execution_routing_summary"]["routed_handoff_count"] >= 1
    assert any(
        item["handoff_item_id"] == handoff_item_id and "task_workflow_draft" in item["routed_targets"]
        for item in routing_payload["routed_handoff_items"]
    )
    assert routing_payload["execution_readiness_posture"]["approval_required"] is True

    reaffirm_status, reaffirm_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/execution-routing-actions",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": handoff_item_id,
            "route_target": "task_workflow_draft",
            "thread_id": str(thread_id),
            "note": "operator reaffirm test",
        },
    )
    assert reaffirm_status == 200
    assert reaffirm_payload["routing_action"]["transition"] == "reaffirmed"
    assert reaffirm_payload["routing_action"]["previously_routed"] is True

    refreshed_status, refreshed_brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )
    assert refreshed_status == 200
    refreshed_brief = refreshed_brief_payload["brief"]
    assert refreshed_brief["routing_audit_trail"]
    assert refreshed_brief["routing_audit_trail"][0]["route_target"] == "task_workflow_draft"
    assert any(
        item["handoff_item_id"] == handoff_item_id and "task_workflow_draft" in item["routed_targets"]
        for item in refreshed_brief["routed_handoff_items"]
    )


def test_chief_of_staff_handoff_outcome_capture_updates_closure_and_conversion_rollups(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="chief-of-staff-handoff-outcomes@example.com")
    thread_id = UUID("f1f1f1f1-f1f1-4f1f-8f1f-f1f1f1f1f1f1")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        capture = store.create_continuity_capture_event(
            raw_content="Next Action: Outcome seam validation",
            explicit_signal="next_action",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_next_action",
        )
        continuity_object = store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type="NextAction",
            status="active",
            title="Next Action: Outcome seam validation",
            body={"action_text": "Outcome seam validation"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-next"]},
            confidence=0.95,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=continuity_object["id"],
        created_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    brief_status, brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )
    assert brief_status == 200
    handoff_item_id = brief_payload["brief"]["handoff_items"][0]["handoff_item_id"]

    routing_status, _routing_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/execution-routing-actions",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": handoff_item_id,
            "route_target": "task_workflow_draft",
            "thread_id": str(thread_id),
            "note": "route for outcome capture test",
        },
    )
    assert routing_status == 200

    outcome_status, outcome_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/handoff-outcomes",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": handoff_item_id,
            "outcome_status": "executed",
            "thread_id": str(thread_id),
            "note": "explicit execution outcome",
        },
    )
    assert outcome_status == 200
    assert outcome_payload["handoff_outcome"]["handoff_item_id"] == handoff_item_id
    assert outcome_payload["handoff_outcome"]["outcome_status"] == "executed"
    assert outcome_payload["handoff_outcome_summary"]["latest_status_counts"]["executed"] >= 1
    assert outcome_payload["closure_quality_summary"]["closed_loop_count"] >= 1
    assert outcome_payload["conversion_signal_summary"]["executed_count"] >= 1
    assert outcome_payload["conversion_signal_summary"]["recommendation_to_execution_conversion_rate"] >= 0.0
    assert outcome_payload["stale_ignored_escalation_posture"]["supporting_signals"]

    refreshed_status, refreshed_brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )
    assert refreshed_status == 200
    refreshed_brief = refreshed_brief_payload["brief"]
    assert refreshed_brief["handoff_outcomes"]
    assert refreshed_brief["handoff_outcomes"][0]["handoff_item_id"] == handoff_item_id
    assert refreshed_brief["handoff_outcome_summary"]["latest_status_counts"]["executed"] >= 1
    assert refreshed_brief["conversion_signal_summary"]["executed_count"] >= 1


def test_chief_of_staff_handoff_outcome_capture_rejects_invalid_and_unrouted_or_out_of_scope_items(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="chief-of-staff-handoff-outcomes-negative@example.com")
    thread_id = UUID("a1a1a1a1-a1a1-4a1a-8a1a-a1a1a1a1a1a1")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        capture = store.create_continuity_capture_event(
            raw_content="Next Action: Outcome validation negative-path coverage",
            explicit_signal="next_action",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_next_action",
        )
        continuity_object = store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type="NextAction",
            status="active",
            title="Next Action: Outcome validation negative-path coverage",
            body={"action_text": "Outcome validation negative-path coverage"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-next-negative"]},
            confidence=0.95,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=continuity_object["id"],
        created_at=datetime(2026, 4, 1, 11, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    brief_status, brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )
    assert brief_status == 200
    handoff_item_id = brief_payload["brief"]["handoff_items"][0]["handoff_item_id"]

    invalid_status_code, invalid_status_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/handoff-outcomes",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": handoff_item_id,
            "outcome_status": "invalid_status",
            "thread_id": str(thread_id),
            "note": "invalid status should fail",
        },
    )
    assert invalid_status_code == 400
    assert "outcome_status must be one of" in invalid_status_payload["detail"]

    unrouted_status_code, unrouted_status_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/handoff-outcomes",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": handoff_item_id,
            "outcome_status": "executed",
            "thread_id": str(thread_id),
            "note": "unrouted handoff should fail",
        },
    )
    assert unrouted_status_code == 400
    assert "has no routed targets yet" in unrouted_status_payload["detail"]

    out_of_scope_status_code, out_of_scope_status_payload = invoke_request(
        "POST",
        "/v0/chief-of-staff/handoff-outcomes",
        payload={
            "user_id": str(user_id),
            "handoff_item_id": "handoff-item-outside-scope",
            "outcome_status": "executed",
            "thread_id": str(thread_id),
            "note": "out-of-scope handoff should fail",
        },
    )
    assert out_of_scope_status_code == 400
    assert "was not found in the scoped deterministic routed handoff list" in out_of_scope_status_payload["detail"]


def test_chief_of_staff_recommendation_outcome_capture_is_auditable_and_updates_learning(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="chief-of-staff-outcomes@example.com")
    thread_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        next_capture = store.create_continuity_capture_event(
            raw_content="Next Action: Ship outcome learning panel",
            explicit_signal="next_action",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_next_action",
        )
        next_object = store.create_continuity_object(
            capture_event_id=next_capture["id"],
            object_type="NextAction",
            status="active",
            title="Next Action: Ship outcome learning panel",
            body={"action_text": "Ship outcome learning panel"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["event-next"]},
            confidence=0.95,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=next_object["id"],
        created_at=datetime(2026, 3, 31, 10, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    capture_payload = {
        "user_id": str(user_id),
        "outcome": "accept",
        "recommendation_action_type": "execute_next_action",
        "recommendation_title": "Next Action: Ship outcome learning panel",
        "rationale": "Accepted after weekly review.",
        "target_priority_id": str(next_object["id"]),
        "thread_id": str(thread_id),
    }
    capture_status, capture_response = invoke_request(
        "POST",
        "/v0/chief-of-staff/recommendation-outcomes",
        payload=capture_payload,
    )

    assert capture_status == 200
    assert capture_response["outcome"]["outcome"] == "accept"
    assert capture_response["outcome"]["recommendation_action_type"] == "execute_next_action"
    assert capture_response["priority_learning_summary"]["accept_count"] == 1
    assert capture_response["pattern_drift_summary"]["posture"] == "improving"

    status, brief_payload = invoke_request(
        "GET",
        "/v0/chief-of-staff",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "5",
        },
    )

    assert status == 200
    brief = brief_payload["brief"]
    assert brief["recommendation_outcomes"]["summary"]["total_count"] >= 1
    assert brief["recommendation_outcomes"]["summary"]["outcome_counts"]["accept"] >= 1
    assert brief["priority_learning_summary"]["accept_count"] >= 1
    assert "Prioritization is" in brief["priority_learning_summary"]["priority_shift_explanation"]
    assert brief["pattern_drift_summary"]["supporting_signals"]
