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


def test_continuity_recall_api_returns_provenance_backed_scoped_results(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="owner@example.com")
    intruder_id = seed_user(migrated_database_urls["app"], email="intruder@example.com")

    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    task_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)

        capture_primary = store.create_continuity_capture_event(
            raw_content="Decision: Keep rollout phased",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        primary_object = store.create_continuity_object(
            capture_event_id=capture_primary["id"],
            object_type="Decision",
            status="active",
            title="Decision: Keep rollout phased",
            body={"decision_text": "Keep rollout phased"},
            provenance={
                "thread_id": str(thread_id),
                "task_id": str(task_id),
                "project": "Project Phoenix",
                "person": "Alex",
                "confirmation_status": "confirmed",
                "source_event_ids": ["event-1"],
            },
            confidence=0.95,
        )

        capture_other = store.create_continuity_capture_event(
            raw_content="Decision: unrelated",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        other_object = store.create_continuity_object(
            capture_event_id=capture_other["id"],
            object_type="Decision",
            status="active",
            title="Decision: unrelated",
            body={"decision_text": "unrelated"},
            provenance={
                "thread_id": str(uuid4()),
                "task_id": str(uuid4()),
                "project": "Project Atlas",
                "person": "Taylor",
                "confirmation_status": "unconfirmed",
                "source_event_ids": ["event-2"],
            },
            confidence=0.9,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=primary_object["id"],
        created_at=datetime(2026, 3, 29, 10, 0, tzinfo=UTC),
    )
    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=other_object["id"],
        created_at=datetime(2026, 3, 29, 9, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    status, payload = invoke_request(
        "GET",
        "/v0/continuity/recall",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "task_id": str(task_id),
            "project": "Project Phoenix",
            "person": "Alex",
            "query": "rollout",
            "since": "2026-03-29T09:30:00+00:00",
            "until": "2026-03-29T11:00:00+00:00",
            "limit": "20",
        },
    )

    assert status == 200
    assert payload["summary"] == {
        "query": "rollout",
        "filters": {
            "thread_id": str(thread_id),
            "task_id": str(task_id),
            "project": "Project Phoenix",
            "person": "Alex",
            "since": "2026-03-29T09:30:00+00:00",
            "until": "2026-03-29T11:00:00+00:00",
        },
        "limit": 20,
        "returned_count": 1,
        "total_count": 1,
        "order": ["relevance_desc", "created_at_desc", "id_desc"],
    }
    assert payload["items"][0]["title"] == "Decision: Keep rollout phased"
    assert payload["items"][0]["confirmation_status"] == "confirmed"
    assert payload["items"][0]["admission_posture"] == "DERIVED"
    assert payload["items"][0]["provenance_references"] == [
        {"source_kind": "continuity_capture_event", "source_id": payload["items"][0]["capture_event_id"]},
        {"source_kind": "source_event", "source_id": "event-1"},
        {"source_kind": "task", "source_id": str(task_id)},
        {"source_kind": "thread", "source_id": str(thread_id)},
    ]

    intruder_status, intruder_payload = invoke_request(
        "GET",
        "/v0/continuity/recall",
        query_params={"user_id": str(intruder_id), "limit": "20"},
    )
    assert intruder_status == 200
    assert intruder_payload == {
        "items": [],
        "summary": {
            "query": None,
            "filters": {"since": None, "until": None},
            "limit": 20,
            "returned_count": 0,
            "total_count": 0,
            "order": ["relevance_desc", "created_at_desc", "id_desc"],
        },
    }


def test_continuity_recall_api_rejects_invalid_time_window(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="owner2@example.com")

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    status, payload = invoke_request(
        "GET",
        "/v0/continuity/recall",
        query_params={
            "user_id": str(user_id),
            "since": "2026-03-29T11:00:00+00:00",
            "until": "2026-03-29T10:00:00+00:00",
            "limit": "20",
        },
    )

    assert status == 400
    assert payload == {"detail": "until must be greater than or equal to since"}
