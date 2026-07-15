from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import anyio
from psycopg.rows import dict_row

import alicebot_api.main as main_module
from alicebot_api.config import Settings
from alicebot_api.db import set_current_user_account, user_connection
from alicebot_api.local_workspace import LOCAL_WORKSPACE_NAME, local_workspace_id
from alicebot_api.store import ContinuityStore


def invoke_request(
    method: str,
    path: str,
    *,
    user_id: UUID | str | None = None,
) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, object]] = []
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}

        request_received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    request_headers = [(b"content-type", b"application/json")]
    if user_id is not None:
        request_headers.append((b"x-alicebot-user-id", str(user_id).encode()))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
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
    return int(start_message["status"]), json.loads(body)


def configure_local_api(monkeypatch: Any, database_urls: dict[str, str]) -> None:
    settings = Settings(
        app_env="test",
        database_url=database_urls["app"],
        database_admin_url=database_urls["admin"],
    )
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def test_local_workspace_bootstrap_requires_a_valid_identity_header(monkeypatch: Any) -> None:
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(app_env="test"))

    missing_status, missing_payload = invoke_request("POST", "/v1/workspaces/bootstrap")
    assert missing_status == 400
    assert missing_payload == {
        "detail": "local identity is required; set ALICEBOT_AUTH_USER_ID or provide X-AliceBot-User-Id"
    }

    invalid_status, invalid_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        user_id="not-a-uuid",
    )
    assert invalid_status == 400
    assert invalid_payload == {"detail": "X-AliceBot-User-Id must be a valid UUID"}

def test_local_workspace_bootstrap_is_deterministic_idempotent_and_identity_isolated(
    migrated_database_urls: dict[str, str],
    monkeypatch: Any,
) -> None:
    configure_local_api(monkeypatch, migrated_database_urls)

    unknown_user_id = uuid4()
    unknown_status, unknown_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        user_id=unknown_user_id,
    )
    assert unknown_status == 404
    assert unknown_payload == {"detail": f"local Alice user {unknown_user_id} was not found"}

    owner_id = seed_user(migrated_database_urls["app"], email="local-owner@example.com")
    other_id = seed_user(migrated_database_urls["app"], email="local-other@example.com")

    before_status, before_payload = invoke_request(
        "GET",
        "/v1/workspaces/bootstrap/status",
        user_id=owner_id,
    )
    assert before_status == 404
    assert before_payload == {
        "detail": "local workspace is not bootstrapped; POST /v1/workspaces/bootstrap first"
    }

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        user_id=owner_id,
    )
    assert create_status == 200
    expected_workspace_id = local_workspace_id(owner_id)
    assert create_payload["workspace"]["id"] == str(expected_workspace_id)
    assert create_payload["workspace"]["owner_user_account_id"] == str(owner_id)
    assert create_payload["workspace"]["slug"] == f"local-{owner_id.hex}"
    assert create_payload["workspace"]["name"] == LOCAL_WORKSPACE_NAME
    assert create_payload["workspace"]["bootstrap_status"] == "ready"
    assert create_payload["bootstrap"]["workspace_id"] == str(expected_workspace_id)
    assert create_payload["bootstrap"]["status"] == "ready"
    assert create_payload["seeded_provider_count"] == 0

    repeat_status, repeat_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        user_id=owner_id,
    )
    assert repeat_status == 200
    assert repeat_payload["workspace"]["id"] == str(expected_workspace_id)
    assert repeat_payload["bootstrap"]["bootstrapped_at"] == create_payload["bootstrap"]["bootstrapped_at"]

    status_code, status_payload = invoke_request(
        "GET",
        "/v1/workspaces/bootstrap/status",
        user_id=owner_id,
    )
    assert status_code == 200
    assert status_payload["workspace"]["id"] == str(expected_workspace_id)
    assert status_payload["bootstrap"]["status"] == "ready"

    other_before_status, _ = invoke_request(
        "GET",
        "/v1/workspaces/bootstrap/status",
        user_id=other_id,
    )
    assert other_before_status == 404

    other_create_status, other_create_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        user_id=other_id,
    )
    assert other_create_status == 200
    assert other_create_payload["workspace"]["id"] == str(local_workspace_id(other_id))
    assert other_create_payload["workspace"]["id"] != str(expected_workspace_id)

    with user_connection(migrated_database_urls["app"], owner_id) as conn:
        set_current_user_account(conn, owner_id)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT w.id, w.owner_user_account_id, wm.role,
                       ua.email, ua.display_name
                FROM workspaces AS w
                JOIN workspace_members AS wm
                  ON wm.workspace_id = w.id
                 AND wm.user_account_id = w.owner_user_account_id
                JOIN user_accounts AS ua
                  ON ua.id = w.owner_user_account_id
                WHERE w.id = %s
                """,
                (expected_workspace_id,),
            )
            persisted = cur.fetchone()

    assert persisted is not None
    assert persisted["owner_user_account_id"] == owner_id
    assert persisted["role"] == "owner"
    assert persisted["email"] == f"local+{owner_id.hex}@alicebot.invalid"
    assert persisted["display_name"] == "Alice local operator"
