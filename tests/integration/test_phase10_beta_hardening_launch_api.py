from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlencode

import anyio
import psycopg
from psycopg.rows import dict_row

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


def _configure_settings(migrated_database_urls, monkeypatch, **overrides: object) -> None:
    settings_kwargs: dict[str, object] = {
        "app_env": "test",
        "database_url": migrated_database_urls["app"],
        "magic_link_ttl_seconds": 600,
        "auth_session_ttl_seconds": 3600,
        "device_link_ttl_seconds": 600,
        "telegram_link_ttl_seconds": 600,
        "telegram_bot_username": "alicebot",
        "telegram_webhook_secret": "",
        "telegram_bot_token": "",
        "hosted_chat_rate_limit_window_seconds": 60,
        "hosted_chat_rate_limit_max_requests": 20,
        "hosted_scheduler_rate_limit_window_seconds": 300,
        "hosted_scheduler_rate_limit_max_requests": 20,
        "hosted_abuse_window_seconds": 600,
        "hosted_abuse_block_threshold": 5,
        "hosted_rate_limits_enabled_by_default": True,
        "hosted_abuse_controls_enabled_by_default": True,
    }
    settings_kwargs.update(overrides)

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(**settings_kwargs),
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
            "device_label": "P10-S5 Device",
            "device_key": f"device-{email}",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "P10-S5 Workspace"},
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
            "update_id": 990001,
            "message": {
                "message_id": 890001,
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


def _ingest_message(
    *,
    update_id: int,
    message_id: int,
    chat_id: int,
    user_id: int,
    username: str,
    text: str,
) -> str:
    webhook_status, webhook_payload = invoke_request(
        "POST",
        "/v1/channels/telegram/webhook",
        payload={
            "update_id": update_id,
            "message": {
                "message_id": message_id,
                "date": 1710001000 + update_id,
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": user_id, "username": username},
                "text": text,
            },
        },
    )
    assert webhook_status == 200
    assert webhook_payload["ingest"]["route_status"] == "resolved"
    return webhook_payload["ingest"]["message"]["id"]


def _handle_message(*, session_token: str, message_id: str) -> tuple[int, dict[str, Any]]:
    return invoke_request(
        "POST",
        f"/v1/channels/telegram/messages/{message_id}/handle",
        payload={},
        headers=auth_header(session_token),
    )


def _promote_session_to_operator(migrated_database_urls, *, session_token: str) -> str:
    token_hash = hashlib.sha256(session_token.encode("utf-8")).hexdigest()
    with psycopg.connect(migrated_database_urls["app"], row_factory=dict_row) as conn:
        with conn.transaction():
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
                session = cur.fetchone()
                assert session is not None
                user_account_id = session["user_account_id"]

                cur.execute(
                    """
                    INSERT INTO beta_cohorts (cohort_key, description)
                    VALUES ('p10-ops', 'Phase 10 hosted beta operator cohort')
                    ON CONFLICT (cohort_key) DO NOTHING
                    """,
                )
                cur.execute(
                    """
                    UPDATE user_accounts
                    SET beta_cohort_key = 'p10-ops'
                    WHERE id = %s
                    """,
                    (user_account_id,),
                )
    return str(user_account_id)


def _workspace_support_snapshot(migrated_database_urls, *, workspace_id: str) -> dict[str, Any]:
    with psycopg.connect(migrated_database_urls["admin"], row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT support_status,
                       onboarding_error_count,
                       onboarding_last_error_code,
                       onboarding_last_error_detail,
                       onboarding_last_error_at,
                       incident_evidence
                FROM workspaces
                WHERE id = %s
                """,
                (workspace_id,),
            )
            row = cur.fetchone()
    assert row is not None
    return {
        "support_status": row["support_status"],
        "onboarding_error_count": int(row["onboarding_error_count"]),
        "onboarding_last_error_code": row["onboarding_last_error_code"],
        "onboarding_last_error_detail": row["onboarding_last_error_detail"],
        "onboarding_last_error_at": row["onboarding_last_error_at"],
        "incident_evidence": row["incident_evidence"],
    }


def test_phase10_s5_admin_endpoints_require_operator_authorization(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _workspace_id = _bootstrap_workspace_session("p10s5-non-operator@example.com")

    status, payload = invoke_request(
        "GET",
        "/v1/admin/hosted/overview",
        headers=auth_header(session_token),
    )
    assert status == 403
    assert "hosted_admin_operator" in payload["detail"]


def test_phase10_s5_admin_endpoints_expose_hosted_visibility(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session("p10s5-admin@example.com")
    _promote_session_to_operator(migrated_database_urls, session_token=session_token)
    _link_telegram_chat(
        session_token=session_token,
        workspace_id=workspace_id,
        chat_id=995001,
        user_id=895001,
        username="p10s5admin",
    )

    message_id = _ingest_message(
        update_id=995101,
        message_id=895101,
        chat_id=995001,
        user_id=895001,
        username="p10s5admin",
        text="Decision: confirm hosted admin visibility",
    )
    handle_status, handle_payload = _handle_message(session_token=session_token, message_id=message_id)
    assert handle_status == 200
    assert handle_payload["intent"]["status"] == "handled"

    overview_status, overview_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/overview",
        headers=auth_header(session_token),
    )
    assert overview_status == 200
    assert overview_payload["workspaces"]["total_count"] >= 1

    workspaces_status, workspaces_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/workspaces",
        headers=auth_header(session_token),
    )
    assert workspaces_status == 200
    assert workspaces_payload["summary"]["returned_count"] >= 1

    delivery_status, delivery_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/delivery-receipts",
        headers=auth_header(session_token),
    )
    assert delivery_status == 200
    assert delivery_payload["summary"]["returned_count"] >= 1

    incidents_status, incidents_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/incidents",
        query_params={"status": "all"},
        headers=auth_header(session_token),
    )
    assert incidents_status == 200
    assert "items" in incidents_payload

    rollout_status, rollout_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/rollout-flags",
        headers=auth_header(session_token),
    )
    assert rollout_status == 200
    assert any(item["flag_key"] == "hosted_chat_handle_enabled" for item in rollout_payload["items"])

    analytics_status, analytics_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/analytics",
        headers=auth_header(session_token),
    )
    assert analytics_status == 200
    assert analytics_payload["analytics"]["total_events"] >= 1

    rate_limits_status, rate_limits_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/rate-limits",
        headers=auth_header(session_token),
    )
    assert rate_limits_status == 200
    assert "summary" in rate_limits_payload
    assert "items" in rate_limits_payload


def test_phase10_s5_rollout_flag_blocks_chat_handle_deterministically(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session("p10s5-rollout@example.com")
    _promote_session_to_operator(migrated_database_urls, session_token=session_token)
    _link_telegram_chat(
        session_token=session_token,
        workspace_id=workspace_id,
        chat_id=995002,
        user_id=895002,
        username="p10s5rollout",
    )

    patch_status, patch_payload = invoke_request(
        "PATCH",
        "/v1/admin/hosted/rollout-flags",
        payload={
            "updates": [
                {
                    "flag_key": "hosted_chat_handle_enabled",
                    "enabled": False,
                    "cohort_key": "p10-ops",
                }
            ]
        },
        headers=auth_header(session_token),
    )
    assert patch_status == 200
    assert any(
        item["flag_key"] == "hosted_chat_handle_enabled" and item["enabled"] is False
        for item in patch_payload["items"]
    )

    message_id = _ingest_message(
        update_id=995201,
        message_id=895201,
        chat_id=995002,
        user_id=895002,
        username="p10s5rollout",
        text="Decision: this should be rollout blocked",
    )
    handle_status, handle_payload = _handle_message(session_token=session_token, message_id=message_id)

    assert handle_status == 403
    assert handle_payload["detail"]["code"] == "hosted_rollout_blocked"

    analytics_status, analytics_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/analytics",
        headers=auth_header(session_token),
    )
    assert analytics_status == 200
    assert analytics_payload["analytics"]["status_counts"].get("blocked_rollout", 0) >= 1


def test_phase10_s5_rate_limit_and_abuse_controls_block_deterministically(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(
        migrated_database_urls,
        monkeypatch,
        hosted_chat_rate_limit_window_seconds=600,
        hosted_chat_rate_limit_max_requests=1,
        hosted_abuse_window_seconds=600,
        hosted_abuse_block_threshold=1,
    )
    session_token, workspace_id = _bootstrap_workspace_session("p10s5-ratelimit@example.com")
    _link_telegram_chat(
        session_token=session_token,
        workspace_id=workspace_id,
        chat_id=995003,
        user_id=895003,
        username="p10s5ratelimit",
    )

    first_message_id = _ingest_message(
        update_id=995301,
        message_id=895301,
        chat_id=995003,
        user_id=895003,
        username="p10s5ratelimit",
        text="Decision: first handle should pass",
    )
    first_status, _first_payload = _handle_message(session_token=session_token, message_id=first_message_id)
    assert first_status == 200

    second_message_id = _ingest_message(
        update_id=995302,
        message_id=895302,
        chat_id=995003,
        user_id=895003,
        username="p10s5ratelimit",
        text="Decision: second handle should rate limit",
    )
    second_status, second_payload = _handle_message(session_token=session_token, message_id=second_message_id)
    assert second_status == 429
    assert second_payload["detail"]["code"] == "hosted_rate_limit_exceeded"

    third_message_id = _ingest_message(
        update_id=995303,
        message_id=895303,
        chat_id=995003,
        user_id=895003,
        username="p10s5ratelimit",
        text="Decision: third handle should abuse block",
    )
    third_status, third_payload = _handle_message(session_token=session_token, message_id=third_message_id)
    assert third_status == 429
    assert third_payload["detail"]["code"] == "hosted_abuse_limit_exceeded"

    _promote_session_to_operator(migrated_database_urls, session_token=session_token)
    rate_limits_status, rate_limits_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/rate-limits",
        headers=auth_header(session_token),
    )
    assert rate_limits_status == 200
    observed_statuses = {item["status"] for item in rate_limits_payload["items"]}
    assert "rate_limited" in observed_statuses
    assert "abuse_blocked" in observed_statuses


def test_phase10_s5_bootstrap_conflict_surfaces_onboarding_support_visibility(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session("p10s5-onboarding@example.com")

    duplicate_bootstrap_status, duplicate_bootstrap_payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert duplicate_bootstrap_status == 409
    assert "already complete" in duplicate_bootstrap_payload["detail"]

    _promote_session_to_operator(migrated_database_urls, session_token=session_token)
    workspaces_status, workspaces_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/workspaces",
        headers=auth_header(session_token),
    )
    assert workspaces_status == 200
    workspace_item = next(item for item in workspaces_payload["items"] if item["id"] == workspace_id)
    assert workspace_item["support_status"] == "needs_attention"
    assert workspace_item["onboarding_error_count"] >= 1
    assert workspace_item["onboarding_last_error_code"] == "bootstrap_conflict"

    incidents_status, incidents_payload = invoke_request(
        "GET",
        "/v1/admin/hosted/incidents",
        query_params={"status": "open", "workspace_id": workspace_id},
        headers=auth_header(session_token),
    )
    assert incidents_status == 200
    assert any(
        item["source"] == "workspace_onboarding" and item["code"] == "bootstrap_conflict"
        for item in incidents_payload["items"]
    )


def test_phase10_s5_rollout_patch_rejects_non_hosted_flag_keys(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _workspace_id = _bootstrap_workspace_session("p10s5-rollout-scope@example.com")
    _promote_session_to_operator(migrated_database_urls, session_token=session_token)

    patch_status, patch_payload = invoke_request(
        "PATCH",
        "/v1/admin/hosted/rollout-flags",
        payload={
            "updates": [
                {
                    "flag_key": "calendar_ingest_enabled",
                    "enabled": False,
                    "cohort_key": "p10-ops",
                }
            ]
        },
        headers=auth_header(session_token),
    )
    assert patch_status == 400
    assert "must start with 'hosted_'" in patch_payload["detail"]


def test_phase10_s5_bootstrap_not_found_does_not_mutate_foreign_workspace_support_evidence(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    owner_session_token, owner_workspace_id = _bootstrap_workspace_session("p10s5-owner@example.com")
    intruder_session_token, _intruder_workspace_id = _bootstrap_workspace_session("p10s5-intruder@example.com")

    before = _workspace_support_snapshot(migrated_database_urls, workspace_id=owner_workspace_id)
    status, payload = invoke_request(
        "POST",
        "/v1/workspaces/bootstrap",
        payload={"workspace_id": owner_workspace_id},
        headers=auth_header(intruder_session_token),
    )
    assert status == 404
    assert owner_workspace_id in payload["detail"]

    after = _workspace_support_snapshot(migrated_database_urls, workspace_id=owner_workspace_id)
    assert after == before

    # Keep the owner token referenced so both sessions are exercised intentionally.
    assert owner_session_token != intruder_session_token
