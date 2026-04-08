from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio
import psycopg

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings


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


def _configure_settings(migrated_database_urls, monkeypatch) -> None:
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
            telegram_link_ttl_seconds=600,
            telegram_bot_username="alicebot",
            telegram_webhook_secret="",
            telegram_bot_token="",
        ),
    )


def _bootstrap_workspace_session(email: str) -> tuple[str, str]:
    start_status, start_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/start",
        payload={"email": email},
    )
    assert start_status == 200

    verify_status, verify_payload = invoke_request(
        "POST",
        "/v1/auth/magic-link/verify",
        payload={
            "challenge_token": start_payload["challenge"]["challenge_token"],
            "device_label": "P10-S4 Device",
            "device_key": f"device-{email}",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "P10-S4 Workspace"},
        headers=auth_header(session_token),
    )
    assert create_workspace_status == 201
    workspace_id = create_workspace_payload["workspace"]["id"]

    bootstrap_status, bootstrap_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert bootstrap_status == 200
    assert bootstrap_payload["workspace"]["bootstrap_status"] == "ready"
    return session_token, workspace_id


def _link_telegram_chat(
    *,
    session_token: str,
    workspace_id: str,
    chat_id: int,
    user_id: int,
    username: str,
) -> None:
    start_status, start_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/start",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert start_status == 200
    challenge_token = start_payload["challenge"]["challenge_token"]
    link_code = start_payload["challenge"]["link_code"]

    webhook_status, webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": 944001,
            "message": {
                "message_id": 744001,
                "date": 1710000000,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "username": username},
                "text": f"/link {link_code}",
            },
        },
    )
    assert webhook_status == 200
    assert webhook_payload["ingest"]["link_status"] == "confirmed"

    confirm_status, confirm_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/link/confirm",
        payload={"challenge_token": challenge_token},
        headers=auth_header(session_token),
    )
    assert confirm_status == 201
    assert confirm_payload["identity"]["status"] == "linked"


def _resolve_user_account_id(*, admin_db_url: str, session_token: str) -> UUID:
    token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
    with psycopg.connect(admin_db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_account_id
                FROM auth_sessions
                WHERE session_token_hash = %s
                LIMIT 1
                """,
                (token_hash,),
            )
            row = cur.fetchone()
    if row is None:
        raise AssertionError("failed to resolve user account id for session token")
    return row[0]


def _seed_open_loop_objects(*, admin_db_url: str, user_id: UUID) -> None:
    now = datetime(2026, 4, 8, 8, 0, tzinfo=UTC)
    seeded = [
        ("WaitingFor", "active", "Waiting For: Vendor SLA"),
        ("Blocker", "active", "Blocker: Missing release key"),
        ("NextAction", "active", "Next Action: Publish release note"),
        ("WaitingFor", "stale", "Waiting For: Stale security signoff"),
    ]

    with psycopg.connect(admin_db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET email = EXCLUDED.email,
                    display_name = EXCLUDED.display_name
                """,
                (str(user_id), f"p10s4-{user_id}@example.com", "P10-S4 User"),
            )

            for index, (object_type, status, title) in enumerate(seeded):
                capture_event_id = uuid4()
                continuity_object_id = uuid4()
                created_at = now - timedelta(minutes=index + 1)
                cur.execute(
                    """
                    INSERT INTO continuity_capture_events (
                      id,
                      user_id,
                      raw_content,
                      explicit_signal,
                      admission_posture,
                      admission_reason,
                      created_at
                    )
                    VALUES (%s, %s, %s, 'note', 'TRIAGE', 'integration_seed', %s)
                    """,
                    (
                        str(capture_event_id),
                        str(user_id),
                        title,
                        created_at,
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO continuity_objects (
                      id,
                      user_id,
                      capture_event_id,
                      object_type,
                      status,
                      title,
                      body,
                      provenance,
                      confidence,
                      last_confirmed_at,
                      supersedes_object_id,
                      superseded_by_object_id,
                      created_at,
                      updated_at
                    )
                    VALUES (
                      %s,
                      %s,
                      %s,
                      %s,
                      %s,
                      %s,
                      %s,
                      %s,
                      %s,
                      NULL,
                      NULL,
                      NULL,
                      %s,
                      %s
                    )
                    """,
                    (
                        str(continuity_object_id),
                        str(user_id),
                        str(capture_event_id),
                        object_type,
                        status,
                        title,
                        json.dumps({"text": title}),
                        json.dumps({"thread_id": "p10s4-thread"}),
                        0.9,
                        created_at,
                        created_at,
                    ),
                )


def test_phase10_daily_brief_delivery_records_scheduler_and_idempotency(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session("p10s4-builder@example.com")
    _link_telegram_chat(
        session_token=session_token,
        workspace_id=workspace_id,
        chat_id=988001,
        user_id=688001,
        username="p10s4builder",
    )

    user_account_id = _resolve_user_account_id(
        admin_db_url=migrated_database_urls["admin"],
        session_token=session_token,
    )
    _seed_open_loop_objects(admin_db_url=migrated_database_urls["admin"], user_id=user_account_id)

    patch_status, patch_payload = invoke_request(
        "PATCH",
        "/v1/channels/telegram/notification-preferences",
        payload={
            "notifications_enabled": True,
            "daily_brief_enabled": True,
            "open_loop_prompts_enabled": True,
            "waiting_for_prompts_enabled": True,
            "stale_prompts_enabled": True,
            "timezone": "UTC",
            "daily_brief_window_start": "00:00",
            "quiet_hours_enabled": False,
        },
        headers=auth_header(session_token),
    )
    assert patch_status == 200
    assert patch_payload["notification_preferences"]["daily_brief_enabled"] is True

    preview_status, preview_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/daily-brief",
        headers=auth_header(session_token),
    )
    assert preview_status == 200
    assert preview_payload["brief"]["assembly_version"] == "continuity_daily_brief_v0"
    assert preview_payload["delivery_policy"]["allowed"] is True

    first_deliver_status, first_deliver_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={},
        headers=auth_header(session_token),
    )
    assert first_deliver_status == 201
    assert first_deliver_payload["idempotent_replay"] is False
    assert first_deliver_payload["job"]["job_kind"] == "daily_brief"
    assert first_deliver_payload["job"]["status"] == "simulated"
    assert first_deliver_payload["delivery_receipt"]["status"] == "simulated"
    assert first_deliver_payload["delivery_receipt"]["scheduler_job_kind"] == "daily_brief"

    second_deliver_status, second_deliver_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={},
        headers=auth_header(session_token),
    )
    assert second_deliver_status == 200
    assert second_deliver_payload["idempotent_replay"] is True
    assert second_deliver_payload["job"]["id"] == first_deliver_payload["job"]["id"]

    receipts_status, receipts_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/delivery-receipts",
        headers=auth_header(session_token),
    )
    assert receipts_status == 200
    assert receipts_payload["summary"]["total_count"] >= 1
    assert receipts_payload["items"][0]["scheduler_job_kind"] in {"daily_brief", "open_loop_prompt"}


def test_phase10_quiet_hours_disabled_notifications_and_stale_prompt_delivery(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session("p10s4-suppress@example.com")
    _link_telegram_chat(
        session_token=session_token,
        workspace_id=workspace_id,
        chat_id=988002,
        user_id=688002,
        username="p10s4suppress",
    )

    user_account_id = _resolve_user_account_id(
        admin_db_url=migrated_database_urls["admin"],
        session_token=session_token,
    )
    _seed_open_loop_objects(admin_db_url=migrated_database_urls["admin"], user_id=user_account_id)

    disabled_status, disabled_payload = invoke_request(
        "PATCH",
        "/v1/channels/telegram/notification-preferences",
        payload={
            "notifications_enabled": False,
            "daily_brief_enabled": True,
            "timezone": "UTC",
            "daily_brief_window_start": "00:00",
            "quiet_hours_enabled": False,
        },
        headers=auth_header(session_token),
    )
    assert disabled_status == 200
    assert disabled_payload["notification_preferences"]["notifications_enabled"] is False

    disabled_deliver_status, disabled_deliver_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={},
        headers=auth_header(session_token),
    )
    assert disabled_deliver_status == 201
    assert disabled_deliver_payload["job"]["status"] == "suppressed_disabled"
    assert disabled_deliver_payload["delivery_receipt"]["status"] == "suppressed"

    quiet_status, quiet_payload = invoke_request(
        "PATCH",
        "/v1/channels/telegram/notification-preferences",
        payload={
            "notifications_enabled": True,
            "daily_brief_enabled": True,
            "open_loop_prompts_enabled": True,
            "waiting_for_prompts_enabled": True,
            "stale_prompts_enabled": True,
            "timezone": "UTC",
            "daily_brief_window_start": "00:00",
            "quiet_hours_enabled": True,
            "quiet_hours_start": "00:00",
            "quiet_hours_end": "23:59",
        },
        headers=auth_header(session_token),
    )
    assert quiet_status == 200
    assert quiet_payload["notification_preferences"]["quiet_hours"]["enabled"] is True

    quiet_deliver_status, quiet_deliver_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={"idempotency_key": "quiet-hours-p10s4-delivery"},
        headers=auth_header(session_token),
    )
    assert quiet_deliver_status == 201
    assert quiet_deliver_payload["job"]["status"] == "suppressed_quiet_hours"
    assert quiet_deliver_payload["delivery_receipt"]["status"] == "suppressed"

    enable_prompts_status, _enable_prompts_payload = invoke_request(
        "PATCH",
        "/v1/channels/telegram/notification-preferences",
        payload={
            "notifications_enabled": True,
            "daily_brief_enabled": True,
            "open_loop_prompts_enabled": True,
            "waiting_for_prompts_enabled": True,
            "stale_prompts_enabled": True,
            "timezone": "UTC",
            "daily_brief_window_start": "00:00",
            "quiet_hours_enabled": False,
        },
        headers=auth_header(session_token),
    )
    assert enable_prompts_status == 200

    prompts_status, prompts_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/open-loop-prompts",
        headers=auth_header(session_token),
    )
    assert prompts_status == 200
    assert prompts_payload["summary"]["returned_count"] >= 1

    stale_prompt = next(item for item in prompts_payload["items"] if item["prompt_kind"] == "stale")

    first_prompt_status, first_prompt_payload = invoke_request(
        "POST",
        f"/v1/channels/telegram/open-loop-prompts/{stale_prompt['prompt_id']}/deliver",
        payload={},
        headers=auth_header(session_token),
    )
    assert first_prompt_status == 201
    assert first_prompt_payload["job"]["job_kind"] == "open_loop_prompt"
    assert first_prompt_payload["job"]["status"] == "simulated"

    second_prompt_status, second_prompt_payload = invoke_request(
        "POST",
        f"/v1/channels/telegram/open-loop-prompts/{stale_prompt['prompt_id']}/deliver",
        payload={},
        headers=auth_header(session_token),
    )
    assert second_prompt_status == 200
    assert second_prompt_payload["idempotent_replay"] is True

    scheduler_status, scheduler_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/scheduler/jobs",
        headers=auth_header(session_token),
    )
    assert scheduler_status == 200
    assert scheduler_payload["summary"]["total_count"] >= 1


def test_phase10_custom_idempotency_key_is_scoped_per_workspace(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)

    session_token_a, workspace_id_a = _bootstrap_workspace_session("p10s4-scope-a@example.com")
    _link_telegram_chat(
        session_token=session_token_a,
        workspace_id=workspace_id_a,
        chat_id=988010,
        user_id=688010,
        username="p10s4scopea",
    )
    user_account_id_a = _resolve_user_account_id(
        admin_db_url=migrated_database_urls["admin"],
        session_token=session_token_a,
    )
    _seed_open_loop_objects(admin_db_url=migrated_database_urls["admin"], user_id=user_account_id_a)

    session_token_b, workspace_id_b = _bootstrap_workspace_session("p10s4-scope-b@example.com")
    _link_telegram_chat(
        session_token=session_token_b,
        workspace_id=workspace_id_b,
        chat_id=988011,
        user_id=688011,
        username="p10s4scopeb",
    )
    user_account_id_b = _resolve_user_account_id(
        admin_db_url=migrated_database_urls["admin"],
        session_token=session_token_b,
    )
    _seed_open_loop_objects(admin_db_url=migrated_database_urls["admin"], user_id=user_account_id_b)

    patch_payload = {
        "notifications_enabled": True,
        "daily_brief_enabled": True,
        "open_loop_prompts_enabled": True,
        "waiting_for_prompts_enabled": True,
        "stale_prompts_enabled": True,
        "timezone": "UTC",
        "daily_brief_window_start": "00:00",
        "quiet_hours_enabled": False,
    }
    patch_a_status, _ = invoke_request(
        "PATCH",
        "/v1/channels/telegram/notification-preferences",
        payload=patch_payload,
        headers=auth_header(session_token_a),
    )
    patch_b_status, _ = invoke_request(
        "PATCH",
        "/v1/channels/telegram/notification-preferences",
        payload=patch_payload,
        headers=auth_header(session_token_b),
    )
    assert patch_a_status == 200
    assert patch_b_status == 200

    shared_key = "shared-p10s4-idempotency-key"

    first_a_status, first_a_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={"idempotency_key": shared_key},
        headers=auth_header(session_token_a),
    )
    first_b_status, first_b_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={"idempotency_key": shared_key},
        headers=auth_header(session_token_b),
    )
    assert first_a_status == 201
    assert first_b_status == 201
    assert first_a_payload["idempotent_replay"] is False
    assert first_b_payload["idempotent_replay"] is False
    assert first_a_payload["workspace_id"] == workspace_id_a
    assert first_b_payload["workspace_id"] == workspace_id_b
    assert first_a_payload["job"]["id"] != first_b_payload["job"]["id"]
    assert first_a_payload["delivery_receipt"]["id"] != first_b_payload["delivery_receipt"]["id"]

    replay_a_status, replay_a_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={"idempotency_key": shared_key},
        headers=auth_header(session_token_a),
    )
    replay_b_status, replay_b_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/daily-brief/deliver",
        payload={"idempotency_key": shared_key},
        headers=auth_header(session_token_b),
    )
    assert replay_a_status == 200
    assert replay_b_status == 200
    assert replay_a_payload["idempotent_replay"] is True
    assert replay_b_payload["idempotent_replay"] is True
    assert replay_a_payload["job"]["id"] == first_a_payload["job"]["id"]
    assert replay_b_payload["job"]["id"] == first_b_payload["job"]["id"]
