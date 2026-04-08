from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import anyio
import psycopg
from psycopg.rows import dict_row

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from apps.api.src.alicebot_api.hosted_auth import hash_token


def invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
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
    request_headers = [(b"content-type", b"application/json")]
    for key, value in (headers or {}).items():
        request_headers.append((key.lower().encode(), value.encode()))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": request_headers,
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


def auth_header(session_token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {session_token}"}


def test_phase10_identity_workspace_bootstrap_and_preferences_flow(
    migrated_database_urls,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
        ),
    )

    start_status, start_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/start",
        payload={"email": "builder@example.com"},
    )
    assert start_status == 200
    challenge_token = start_payload["challenge"]["challenge_token"]

    verify_status, verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": challenge_token,
            "device_label": "Builder Laptop",
            "device_key": "builder-laptop",
        },
    )
    assert verify_status == 200
    assert verify_payload["workspace"] is None
    assert verify_payload["telegram_state"] == "available_in_p10_s2_transport"

    session_token = verify_payload["session_token"]
    primary_device_id = verify_payload["session"]["device_id"]

    session_status, session_payload = invoke_request(
        "GET",
        "/v1/auth/session",
        headers=auth_header(session_token),
    )
    assert session_status == 200
    assert session_payload["user_account"]["email"] == "builder@example.com"
    assert session_payload["preferences"]["timezone"] == "UTC"

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "Builder Control Plane"},
        headers=auth_header(session_token),
    )
    assert create_workspace_status == 201
    workspace_id = create_workspace_payload["workspace"]["id"]

    current_workspace_status, current_workspace_payload = invoke_request(
        "GET",
        "/v1/workspaces/current",
        headers=auth_header(session_token),
    )
    assert current_workspace_status == 200
    assert current_workspace_payload["workspace"]["id"] == workspace_id

    bootstrap_status_before, bootstrap_payload_before = invoke_request(
        "GET",
        "/v1/workspaces/bootstrap/status",
        headers=auth_header(session_token),
    )
    assert bootstrap_status_before == 200
    assert bootstrap_payload_before["bootstrap"]["status"] == "pending"
    assert bootstrap_payload_before["bootstrap"]["telegram_state"] == "available_in_p10_s2_transport"

    bootstrap_status, bootstrap_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert bootstrap_status == 200
    assert bootstrap_payload["workspace"]["bootstrap_status"] == "ready"
    assert bootstrap_payload["bootstrap"]["ready_for_next_phase_telegram_linkage"] is True
    assert bootstrap_payload["telegram_state"] == "available_in_p10_s2_transport"

    duplicate_bootstrap_status, duplicate_bootstrap_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert duplicate_bootstrap_status == 409
    assert "already complete" in duplicate_bootstrap_payload["detail"]

    get_preferences_status, get_preferences_payload = invoke_request(
        "GET",
        "/v1/preferences",
        headers=auth_header(session_token),
    )
    assert get_preferences_status == 200
    assert get_preferences_payload["preferences"]["timezone"] == "UTC"

    patch_preferences_status, patch_preferences_payload = invoke_request(
        "PATCH",
        "/v1/preferences",
        payload={
            "timezone": "Europe/Stockholm",
            "brief_preferences": {
                "daily_brief": {"enabled": True, "window_start": "08:30"},
                "mode": "hosted_foundation",
            },
            "quiet_hours": {"enabled": True, "start": "21:00", "end": "06:30"},
        },
        headers=auth_header(session_token),
    )
    assert patch_preferences_status == 200
    assert patch_preferences_payload["preferences"]["timezone"] == "Europe/Stockholm"
    assert patch_preferences_payload["preferences"]["brief_preferences"]["mode"] == "hosted_foundation"

    start_link_status, start_link_payload = invoke_request(
        "POST",
        "/v1/devices/link/start",
        payload={"device_key": "builder-phone", "device_label": "Builder Phone"},
        headers=auth_header(session_token),
    )
    assert start_link_status == 200

    confirm_link_status, confirm_link_payload = invoke_request(
        "POST",
        "/v1/devices/link/confirm",
        payload={"challenge_token": start_link_payload["challenge"]["challenge_token"]},
        headers=auth_header(session_token),
    )
    assert confirm_link_status == 201
    linked_device_id = confirm_link_payload["device"]["id"]

    list_devices_status, list_devices_payload = invoke_request(
        "GET",
        "/v1/devices",
        headers=auth_header(session_token),
    )
    assert list_devices_status == 200
    assert list_devices_payload["summary"]["total_count"] >= 2

    delete_linked_status, delete_linked_payload = invoke_request(
        "DELETE",
        f"/v1/devices/{linked_device_id}",
        headers=auth_header(session_token),
    )
    assert delete_linked_status == 200
    assert delete_linked_payload["device"]["status"] == "revoked"

    delete_primary_status, delete_primary_payload = invoke_request(
        "DELETE",
        f"/v1/devices/{primary_device_id}",
        headers=auth_header(session_token),
    )
    assert delete_primary_status == 200
    assert delete_primary_payload["device"]["status"] == "revoked"

    revoked_session_status, revoked_session_payload = invoke_request(
        "GET",
        "/v1/auth/session",
        headers=auth_header(session_token),
    )
    assert revoked_session_status == 401
    assert revoked_session_payload == {"detail": "session device has been revoked"}


def test_phase10_logout_revokes_session(migrated_database_urls, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
        ),
    )

    start_status, start_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/start",
        payload={"email": "logout@example.com"},
    )
    assert start_status == 200

    verify_status, verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": start_payload["challenge"]["challenge_token"],
            "device_label": "Logout Device",
            "device_key": "logout-device",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]

    logout_status, logout_payload = invoke_request(
        "POST",
        "/v1/auth/logout",
        headers=auth_header(session_token),
    )
    assert logout_status == 200
    assert logout_payload == {"status": "logged_out"}

    session_status, session_payload = invoke_request(
        "GET",
        "/v1/auth/session",
        headers=auth_header(session_token),
    )
    assert session_status == 401
    assert session_payload == {"detail": "session is not active"}


def test_phase10_magic_link_invalid_and_expired_paths(migrated_database_urls, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
        ),
    )

    invalid_verify_status, invalid_verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": "invalid-token-value-for-phase10",
            "device_label": "Invalid Device",
            "device_key": "invalid-device",
        },
    )
    assert invalid_verify_status == 400
    assert "invalid" in invalid_verify_payload["detail"]

    start_status, start_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/start",
        payload={"email": "expired@example.com"},
    )
    assert start_status == 200
    challenge_token = start_payload["challenge"]["challenge_token"]

    with psycopg.connect(migrated_database_urls["app"], row_factory=dict_row) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE magic_link_challenges
                    SET expires_at = clock_timestamp() - interval '1 second'
                    WHERE challenge_token_hash = %s
                    """,
                    (hash_token(challenge_token),),
                )

    expired_verify_status, expired_verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": challenge_token,
            "device_label": "Expired Device",
            "device_key": "expired-device",
        },
    )
    assert expired_verify_status == 401
    assert expired_verify_payload == {"detail": "magic-link token has expired"}

    invalid_session_status, invalid_session_payload = invoke_request(
        "GET",
        "/v1/auth/session",
        headers=auth_header("totally-invalid-session-token"),
    )
    assert invalid_session_status == 401
    assert "invalid" in invalid_session_payload["detail"]


def test_phase10_device_link_invalid_and_expired_paths(migrated_database_urls, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
        ),
    )

    start_status, start_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/start",
        payload={"email": "device-link@example.com"},
    )
    assert start_status == 200

    verify_status, verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": start_payload["challenge"]["challenge_token"],
            "device_label": "Primary Device",
            "device_key": "primary-device",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]

    invalid_confirm_status, invalid_confirm_payload = invoke_request(
        "POST",
        "/v1/devices/link/confirm",
        payload={"challenge_token": "invalid-device-link-token-value"},
        headers=auth_header(session_token),
    )
    assert invalid_confirm_status == 400
    assert "invalid" in invalid_confirm_payload["detail"]

    start_link_status, start_link_payload = invoke_request(
        "POST",
        "/v1/devices/link/start",
        payload={"device_key": "expiring-device", "device_label": "Expiring Device"},
        headers=auth_header(session_token),
    )
    assert start_link_status == 200
    link_challenge_token = start_link_payload["challenge"]["challenge_token"]

    with psycopg.connect(migrated_database_urls["app"], row_factory=dict_row) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE device_link_challenges
                    SET expires_at = clock_timestamp() - interval '1 second'
                    WHERE challenge_token_hash = %s
                    """,
                    (hash_token(link_challenge_token),),
                )

    expired_confirm_status, expired_confirm_payload = invoke_request(
        "POST",
        "/v1/devices/link/confirm",
        payload={"challenge_token": link_challenge_token},
        headers=auth_header(session_token),
    )
    assert expired_confirm_status == 401
    assert expired_confirm_payload == {"detail": "device-link token has expired"}
