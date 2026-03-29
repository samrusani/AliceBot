from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio

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


def test_continuity_capture_create_list_and_detail_support_deterministic_signal_mapping(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="owner@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    create_status, create_payload = invoke_request(
        "POST",
        "/v0/continuity/captures",
        payload={
            "user_id": str(user_id),
            "raw_content": "Finalize launch checklist",
            "explicit_signal": "task",
        },
    )

    assert create_status == 201
    capture_id = create_payload["capture"]["capture_event"]["id"]
    assert create_payload["capture"]["capture_event"] == {
        "id": capture_id,
        "raw_content": "Finalize launch checklist",
        "explicit_signal": "task",
        "admission_posture": "DERIVED",
        "admission_reason": "explicit_signal_task",
        "created_at": create_payload["capture"]["capture_event"]["created_at"],
    }
    assert create_payload["capture"]["derived_object"]["object_type"] == "NextAction"
    assert create_payload["capture"]["derived_object"]["body"] == {
        "action_text": "Finalize launch checklist",
        "raw_content": "Finalize launch checklist",
        "explicit_signal": "task",
    }
    assert create_payload["capture"]["derived_object"]["provenance"]["capture_event_id"] == capture_id

    list_status, list_payload = invoke_request(
        "GET",
        "/v0/continuity/captures",
        query_params={
            "user_id": str(user_id),
            "limit": "20",
        },
    )
    assert list_status == 200
    assert list_payload["summary"] == {
        "limit": 20,
        "returned_count": 1,
        "total_count": 1,
        "derived_count": 1,
        "triage_count": 0,
        "order": ["created_at_desc", "id_desc"],
    }
    assert list_payload["items"][0]["capture_event"]["id"] == capture_id

    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v0/continuity/captures/{capture_id}",
        query_params={"user_id": str(user_id)},
    )
    assert detail_status == 200
    assert detail_payload["capture"]["capture_event"]["id"] == capture_id
    assert detail_payload["capture"]["derived_object"]["object_type"] == "NextAction"


def test_continuity_capture_ambiguous_input_is_preserved_with_triage_posture(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="owner2@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    create_status, create_payload = invoke_request(
        "POST",
        "/v0/continuity/captures",
        payload={
            "user_id": str(user_id),
            "raw_content": "Maybe revisit this next month",
        },
    )

    assert create_status == 201
    assert create_payload["capture"]["capture_event"]["admission_posture"] == "TRIAGE"
    assert create_payload["capture"]["capture_event"]["admission_reason"] == "ambiguous_capture_requires_triage"
    assert create_payload["capture"]["derived_object"] is None

    capture_id = create_payload["capture"]["capture_event"]["id"]
    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v0/continuity/captures/{capture_id}",
        query_params={"user_id": str(user_id)},
    )
    assert detail_status == 200
    assert detail_payload["capture"]["derived_object"] is None


def test_continuity_capture_rejects_invalid_signal_and_enforces_user_scope(
    migrated_database_urls,
    monkeypatch,
) -> None:
    owner_id = seed_user(migrated_database_urls["app"], email="owner3@example.com")
    intruder_id = seed_user(migrated_database_urls["app"], email="intruder@example.com")
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    invalid_status, invalid_payload = invoke_request(
        "POST",
        "/v0/continuity/captures",
        payload={
            "user_id": str(owner_id),
            "raw_content": "Call the supplier",
            "explicit_signal": "invalid_signal",
        },
    )
    assert invalid_status == 400
    assert invalid_payload["detail"].startswith("explicit_signal must be one of")

    create_status, create_payload = invoke_request(
        "POST",
        "/v0/continuity/captures",
        payload={
            "user_id": str(owner_id),
            "raw_content": "Decision: keep intake conservative",
        },
    )
    assert create_status == 201

    intruder_detail_status, intruder_detail_payload = invoke_request(
        "GET",
        f"/v0/continuity/captures/{create_payload['capture']['capture_event']['id']}",
        query_params={"user_id": str(intruder_id)},
    )
    assert intruder_detail_status == 404
    assert intruder_detail_payload == {
        "detail": (
            f"continuity capture event {create_payload['capture']['capture_event']['id']} "
            "was not found"
        )
    }

    intruder_list_status, intruder_list_payload = invoke_request(
        "GET",
        "/v0/continuity/captures",
        query_params={"user_id": str(intruder_id), "limit": "20"},
    )
    assert intruder_list_status == 200
    assert intruder_list_payload == {
        "items": [],
        "summary": {
            "limit": 20,
            "returned_count": 0,
            "total_count": 0,
            "derived_count": 0,
            "triage_count": 0,
            "order": ["created_at_desc", "id_desc"],
        },
    }
