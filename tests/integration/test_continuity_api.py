from __future__ import annotations

from datetime import UTC, datetime, timedelta
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


def create_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def seed_user_with_continuity(database_url: str, *, email: str) -> dict[str, object]:
    user_id = create_user(database_url, email=email)

    with user_connection(database_url, user_id) as conn:
        store = ContinuityStore(conn)
        first_thread = store.create_thread("Alpha thread")
        second_thread = store.create_thread("Beta thread")
        first_session = store.create_session(second_thread["id"], status="completed")
        second_session = store.create_session(second_thread["id"], status="active")
        first_event = store.append_event(
            second_thread["id"],
            second_session["id"],
            "message.user",
            {"text": "Hello"},
        )
        second_event = store.append_event(
            second_thread["id"],
            second_session["id"],
            "message.assistant",
            {"text": "Hello back"},
        )

    return {
        "user_id": user_id,
        "first_thread": first_thread,
        "second_thread": second_thread,
        "first_session": first_session,
        "second_session": second_session,
        "first_event": first_event,
        "second_event": second_event,
    }


def set_thread_timestamps(
    admin_database_url: str,
    *,
    thread_id: UUID,
    created_at: datetime,
    updated_at: datetime,
) -> None:
    with psycopg.connect(admin_database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE threads SET created_at = %s, updated_at = %s WHERE id = %s",
                (created_at, updated_at, thread_id),
            )


def set_session_timestamps(
    admin_database_url: str,
    *,
    session_id: UUID,
    started_at: datetime,
    ended_at: datetime | None,
    created_at: datetime,
) -> None:
    with psycopg.connect(admin_database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE sessions SET started_at = %s, ended_at = %s, created_at = %s WHERE id = %s",
                (started_at, ended_at, created_at, session_id),
            )


def serialize_thread(*, thread_id: UUID, title: str, created_at: datetime, updated_at: datetime) -> dict[str, Any]:
    return {
        "id": str(thread_id),
        "title": title,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


def serialize_session(
    *,
    session_id: UUID,
    thread_id: UUID,
    status: str,
    started_at: datetime | None,
    ended_at: datetime | None,
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "id": str(session_id),
        "thread_id": str(thread_id),
        "status": status,
        "started_at": None if started_at is None else started_at.isoformat(),
        "ended_at": None if ended_at is None else ended_at.isoformat(),
        "created_at": created_at.isoformat(),
    }


def serialize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(event["id"]),
        "thread_id": str(event["thread_id"]),
        "session_id": None if event["session_id"] is None else str(event["session_id"]),
        "sequence_no": event["sequence_no"],
        "kind": event["kind"],
        "payload": event["payload"],
        "created_at": event["created_at"].isoformat(),
    }


def test_thread_continuity_endpoints_create_list_detail_sessions_and_events(
    migrated_database_urls,
    monkeypatch,
) -> None:
    seeded = seed_user_with_continuity(migrated_database_urls["app"], email="owner@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    create_status, create_payload = invoke_request(
        "POST",
        "/v0/threads",
        payload={
            "user_id": str(seeded["user_id"]),
            "title": "Gamma thread",
        },
    )

    assert create_status == 201
    assert create_payload["thread"]["title"] == "Gamma thread"

    api_thread_id = UUID(create_payload["thread"]["id"])
    shared_created_at = datetime(2026, 3, 17, 9, 0, tzinfo=UTC)
    newer_created_at = datetime(2026, 3, 17, 10, 0, tzinfo=UTC)
    first_session_start = shared_created_at
    first_session_end = shared_created_at + timedelta(minutes=5)
    second_session_start = shared_created_at + timedelta(hours=1)

    set_thread_timestamps(
        migrated_database_urls["admin"],
        thread_id=seeded["first_thread"]["id"],
        created_at=shared_created_at,
        updated_at=shared_created_at,
    )
    set_thread_timestamps(
        migrated_database_urls["admin"],
        thread_id=seeded["second_thread"]["id"],
        created_at=shared_created_at,
        updated_at=shared_created_at,
    )
    set_thread_timestamps(
        migrated_database_urls["admin"],
        thread_id=api_thread_id,
        created_at=newer_created_at,
        updated_at=newer_created_at,
    )
    set_session_timestamps(
        migrated_database_urls["admin"],
        session_id=seeded["first_session"]["id"],
        started_at=first_session_start,
        ended_at=first_session_end,
        created_at=first_session_start,
    )
    set_session_timestamps(
        migrated_database_urls["admin"],
        session_id=seeded["second_session"]["id"],
        started_at=second_session_start,
        ended_at=None,
        created_at=second_session_start,
    )

    with user_connection(migrated_database_urls["app"], seeded["user_id"]) as conn:
        stored_thread_ids = [thread["id"] for thread in ContinuityStore(conn).list_threads()]

    assert api_thread_id in stored_thread_ids

    list_status, list_payload = invoke_request(
        "GET",
        "/v0/threads",
        query_params={"user_id": str(seeded["user_id"])},
    )
    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v0/threads/{seeded['second_thread']['id']}",
        query_params={"user_id": str(seeded["user_id"])},
    )
    sessions_status, sessions_payload = invoke_request(
        "GET",
        f"/v0/threads/{seeded['second_thread']['id']}/sessions",
        query_params={"user_id": str(seeded["user_id"])},
    )
    events_status, events_payload = invoke_request(
        "GET",
        f"/v0/threads/{seeded['second_thread']['id']}/events",
        query_params={"user_id": str(seeded["user_id"])},
    )
    tied_threads = sorted(
        [seeded["first_thread"], seeded["second_thread"]],
        key=lambda thread: (thread["created_at"], thread["id"]),
        reverse=True,
    )

    assert list_status == 200
    assert list_payload == {
        "items": [
            serialize_thread(
                thread_id=api_thread_id,
                title="Gamma thread",
                created_at=newer_created_at,
                updated_at=newer_created_at,
            ),
            serialize_thread(
                thread_id=tied_threads[0]["id"],
                title=tied_threads[0]["title"],
                created_at=shared_created_at,
                updated_at=shared_created_at,
            ),
            serialize_thread(
                thread_id=tied_threads[1]["id"],
                title=tied_threads[1]["title"],
                created_at=shared_created_at,
                updated_at=shared_created_at,
            ),
        ],
        "summary": {
            "total_count": 3,
            "order": ["created_at_desc", "id_desc"],
        },
    }

    assert detail_status == 200
    assert detail_payload == {
        "thread": serialize_thread(
            thread_id=seeded["second_thread"]["id"],
            title="Beta thread",
            created_at=shared_created_at,
            updated_at=shared_created_at,
        )
    }

    assert sessions_status == 200
    assert sessions_payload == {
        "items": [
            serialize_session(
                session_id=seeded["first_session"]["id"],
                thread_id=seeded["second_thread"]["id"],
                status="completed",
                started_at=first_session_start,
                ended_at=first_session_end,
                created_at=first_session_start,
            ),
            serialize_session(
                session_id=seeded["second_session"]["id"],
                thread_id=seeded["second_thread"]["id"],
                status="active",
                started_at=second_session_start,
                ended_at=None,
                created_at=second_session_start,
            ),
        ],
        "summary": {
            "thread_id": str(seeded["second_thread"]["id"]),
            "total_count": 2,
            "order": ["started_at_asc", "created_at_asc", "id_asc"],
        },
    }

    assert events_status == 200
    assert events_payload == {
        "items": [
            serialize_event(seeded["first_event"]),
            serialize_event(seeded["second_event"]),
        ],
        "summary": {
            "thread_id": str(seeded["second_thread"]["id"]),
            "total_count": 2,
            "order": ["sequence_no_asc"],
        },
    }


def test_thread_continuity_endpoints_enforce_user_isolation_and_not_found(
    migrated_database_urls,
    monkeypatch,
) -> None:
    owner = seed_user_with_continuity(migrated_database_urls["app"], email="owner@example.com")
    intruder_id = create_user(migrated_database_urls["app"], email="intruder@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    list_status, list_payload = invoke_request(
        "GET",
        "/v0/threads",
        query_params={"user_id": str(intruder_id)},
    )
    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v0/threads/{owner['second_thread']['id']}",
        query_params={"user_id": str(intruder_id)},
    )
    sessions_status, sessions_payload = invoke_request(
        "GET",
        f"/v0/threads/{owner['second_thread']['id']}/sessions",
        query_params={"user_id": str(intruder_id)},
    )
    events_status, events_payload = invoke_request(
        "GET",
        f"/v0/threads/{owner['second_thread']['id']}/events",
        query_params={"user_id": str(intruder_id)},
    )

    assert list_status == 200
    assert list_payload == {
        "items": [],
        "summary": {
            "total_count": 0,
            "order": ["created_at_desc", "id_desc"],
        },
    }
    assert detail_status == 404
    assert detail_payload == {"detail": f"thread {owner['second_thread']['id']} was not found"}
    assert sessions_status == 404
    assert sessions_payload == {"detail": f"thread {owner['second_thread']['id']} was not found"}
    assert events_status == 404
    assert events_payload == {"detail": f"thread {owner['second_thread']['id']} was not found"}
