from __future__ import annotations

import json
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
            "device_label": "P10-S3 Device",
            "device_key": f"device-{email}",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "P10-S3 Workspace"},
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
            "update_id": 910001,
            "message": {
                "message_id": 710001,
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


def _handle_message(
    *,
    session_token: str,
    message_id: str,
    intent_hint: str | None = None,
) -> tuple[int, dict[str, Any]]:
    payload: dict[str, Any] = {}
    if intent_hint is not None:
        payload["intent_hint"] = intent_hint
    return invoke_request(
        "POST",
        f"/v1/channels/telegram/messages/{message_id}/handle",
        payload=payload,
        headers=auth_header(session_token),
    )


def _seed_pending_approval(*, admin_db_url: str, user_id: UUID, seed_key: str) -> UUID:
    thread_id = uuid4()
    trace_id = uuid4()
    tool_id = uuid4()
    approval_id = uuid4()
    task_id = uuid4()
    task_step_id = uuid4()

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
                (str(user_id), f"{seed_key}@example.com", f"{seed_key} User"),
            )
            cur.execute(
                """
                INSERT INTO threads (id, user_id, title)
                VALUES (%s, %s, %s)
                """,
                (str(thread_id), str(user_id), f"{seed_key} Thread"),
            )
            cur.execute(
                """
                INSERT INTO traces (id, user_id, thread_id, kind, compiler_version, status, limits)
                VALUES (%s, %s, %s, 'telegram.seed', 'v0', 'completed', '{}'::jsonb)
                """,
                (str(trace_id), str(user_id), str(thread_id)),
            )
            cur.execute(
                """
                INSERT INTO tools (
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  '1.0.0',
                  'tool_metadata_v0',
                  TRUE,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '{}'::jsonb
                )
                """,
                (
                    str(tool_id),
                    str(user_id),
                    f"telegram.seed.{seed_key}",
                    f"{seed_key} Tool",
                    "Seed tool for telegram approvals",
                ),
            )
            cur.execute(
                """
                INSERT INTO approvals (
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_run_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  NULL,
                  NULL,
                  'pending',
                  '{"action":"deploy"}'::jsonb,
                  '{"id":"seed-tool"}'::jsonb,
                  '{"decision":"approval_required"}'::jsonb,
                  %s
                )
                """,
                (str(approval_id), str(user_id), str(thread_id), str(tool_id), str(trace_id)),
            )
            cur.execute(
                """
                INSERT INTO tasks (
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  'pending_approval',
                  '{"action":"deploy"}'::jsonb,
                  '{"id":"seed-tool"}'::jsonb,
                  %s,
                  NULL
                )
                """,
                (str(task_id), str(user_id), str(thread_id), str(tool_id), str(approval_id)),
            )
            cur.execute(
                """
                INSERT INTO task_steps (
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  1,
                  'governed_request',
                  'created',
                  '{"action":"deploy"}'::jsonb,
                  %s,
                  %s,
                  'telegram.seed'
                )
                """,
                (
                    str(task_step_id),
                    str(user_id),
                    str(task_id),
                    json.dumps(
                        {
                            "routing_decision": "approval_required",
                            "approval_id": str(approval_id),
                            "approval_status": "pending",
                            "execution_id": None,
                            "execution_status": None,
                            "blocked_reason": None,
                        }
                    ),
                    str(trace_id),
                ),
            )
            cur.execute(
                """
                UPDATE approvals
                SET task_step_id = %s
                WHERE id = %s
                """,
                (str(task_step_id), str(approval_id)),
            )
        conn.commit()

    return approval_id


def test_phase10_telegram_continuity_handle_result_and_open_loop_review(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session("p10s3-continuity@example.com")
    _link_telegram_chat(
        session_token=session_token,
        workspace_id=workspace_id,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
    )

    capture_message_id = _ingest_message(
        update_id=920001,
        message_id=720001,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text="Decision: Ship P10-S3 this week",
    )
    capture_handle_status, capture_handle_payload = _handle_message(
        session_token=session_token,
        message_id=capture_message_id,
    )
    assert capture_handle_status == 200
    assert capture_handle_payload["intent"]["intent_kind"] == "capture"
    assert capture_handle_payload["intent"]["status"] == "handled"

    result_status, result_payload = invoke_request(
        "GET",
        f"/v1/channels/telegram/messages/{capture_message_id}/result",
        headers=auth_header(session_token),
    )
    assert result_status == 200
    assert result_payload["intent"]["intent_kind"] == "capture"

    recall_message_id = _ingest_message(
        update_id=920002,
        message_id=720002,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text="/recall ship p10-s3",
    )
    recall_handle_status, recall_handle_payload = _handle_message(
        session_token=session_token,
        message_id=recall_message_id,
    )
    assert recall_handle_status == 200
    assert recall_handle_payload["intent"]["intent_kind"] == "recall"
    assert recall_handle_payload["intent"]["status"] == "handled"
    recall_items = recall_handle_payload["intent"]["result_payload"]["intent_result"]["recall"]["items"]
    assert len(recall_items) >= 1
    continuity_object_id = recall_items[0]["id"]

    correction_message_id = _ingest_message(
        update_id=920003,
        message_id=720003,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text=f"/correct {continuity_object_id} Decision: Ship P10-S3 after sign-off",
    )
    correction_handle_status, correction_handle_payload = _handle_message(
        session_token=session_token,
        message_id=correction_message_id,
    )
    assert correction_handle_status == 200
    assert correction_handle_payload["intent"]["intent_kind"] == "correction"
    assert correction_handle_payload["intent"]["status"] == "handled"

    corrected_recall_message_id = _ingest_message(
        update_id=920004,
        message_id=720004,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text="/recall sign-off",
    )
    corrected_recall_status, corrected_recall_payload = _handle_message(
        session_token=session_token,
        message_id=corrected_recall_message_id,
    )
    assert corrected_recall_status == 200
    corrected_title = corrected_recall_payload["intent"]["result_payload"]["intent_result"]["recall"]["items"][0][
        "title"
    ]
    assert "after sign-off" in corrected_title

    resume_message_id = _ingest_message(
        update_id=920005,
        message_id=720005,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text="/resume",
    )
    resume_handle_status, resume_handle_payload = _handle_message(
        session_token=session_token,
        message_id=resume_message_id,
    )
    assert resume_handle_status == 200
    assert resume_handle_payload["intent"]["intent_kind"] == "resume"
    assert resume_handle_payload["intent"]["status"] == "handled"
    assert (
        resume_handle_payload["intent"]["result_payload"]["intent_result"]["brief"]["last_decision"]["item"] is not None
    )

    empty_recall_message_id = _ingest_message(
        update_id=920008,
        message_id=720008,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text="/recall",
    )
    empty_recall_status, empty_recall_payload = _handle_message(
        session_token=session_token,
        message_id=empty_recall_message_id,
    )
    assert empty_recall_status == 200
    assert empty_recall_payload["intent"]["intent_kind"] == "recall"
    assert empty_recall_payload["intent"]["status"] == "failed"
    assert (
        empty_recall_payload["intent"]["result_payload"]["error"]["detail"]
        == "recall intent requires a query"
    )

    open_loop_capture_id = _ingest_message(
        update_id=920006,
        message_id=720006,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text="Next: Follow up with design review",
    )
    open_loop_capture_status, _open_loop_capture_payload = _handle_message(
        session_token=session_token,
        message_id=open_loop_capture_id,
    )
    assert open_loop_capture_status == 200

    open_loops_status, open_loops_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/open-loops",
        headers=auth_header(session_token),
    )
    assert open_loops_status == 200
    next_action_items = open_loops_payload["open_loops"]["dashboard"]["next_action"]["items"]
    assert len(next_action_items) >= 1
    open_loop_id = next_action_items[0]["id"]

    review_status, review_payload = invoke_request(
        "POST",
        f"/v1/channels/telegram/open-loops/{open_loop_id}/review-action",
        payload={"action": "deferred", "note": "waiting on external input"},
        headers=auth_header(session_token),
    )
    assert review_status == 200
    assert review_payload["review_action"] == "deferred"
    assert review_payload["review_log"]["review_action"] == "deferred"

    recall_endpoint_status, recall_endpoint_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/recall",
        query_params={"query": "sign-off"},
        headers=auth_header(session_token),
    )
    assert recall_endpoint_status == 200
    assert len(recall_endpoint_payload["recall"]["items"]) >= 1

    resume_endpoint_status, resume_endpoint_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/resume",
        headers=auth_header(session_token),
    )
    assert resume_endpoint_status == 200
    assert "brief" in resume_endpoint_payload["resume"]

    wrong_intent_message_id = _ingest_message(
        update_id=920007,
        message_id=720007,
        chat_id=75001,
        user_id=76001,
        username="continuity_builder",
        text="Remember to sync final notes",
    )
    wrong_intent_status, wrong_intent_payload = _handle_message(
        session_token=session_token,
        message_id=wrong_intent_message_id,
        intent_hint="recall",
    )
    assert wrong_intent_status == 200
    assert wrong_intent_payload["intent"]["status"] == "failed"
    assert wrong_intent_payload["intent"]["result_payload"]["error"]["code"] == "intent_hint_mismatch"


def test_phase10_telegram_approval_endpoints_and_chat_resolution(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id = _bootstrap_workspace_session("p10s3-approvals@example.com")
    _link_telegram_chat(
        session_token=session_token,
        workspace_id=workspace_id,
        chat_id=85001,
        user_id=86001,
        username="approval_builder",
    )

    seed_message_id = _ingest_message(
        update_id=930001,
        message_id=730001,
        chat_id=85001,
        user_id=86001,
        username="approval_builder",
        text="Decision: establish continuity user shadow",
    )
    seed_handle_status, _seed_handle_payload = _handle_message(
        session_token=session_token,
        message_id=seed_message_id,
    )
    assert seed_handle_status == 200

    session_status, session_payload = invoke_request(
        "GET",
        "/v1/auth/session",
        headers=auth_header(session_token),
    )
    assert session_status == 200
    user_account_id = UUID(session_payload["user_account"]["id"])

    approval_a = _seed_pending_approval(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        seed_key="approval-a",
    )
    approval_b = _seed_pending_approval(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        seed_key="approval-b",
    )
    approval_c = _seed_pending_approval(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        seed_key="approval-c",
    )
    approval_d = _seed_pending_approval(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        seed_key="approval-d",
    )

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/approvals",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    listed_ids = {item["id"] for item in list_payload["items"]}
    assert str(approval_a) in listed_ids
    assert str(approval_b) in listed_ids
    assert list_payload["summary"]["pending_count"] >= 4

    approve_status, approve_payload = invoke_request(
        "POST",
        f"/v1/channels/telegram/approvals/{approval_a}/approve",
        payload={},
        headers=auth_header(session_token),
    )
    assert approve_status == 200
    assert approve_payload["approval"]["status"] == "approved"
    assert isinstance(approve_payload["challenge_updates"], list)

    reject_status, reject_payload = invoke_request(
        "POST",
        f"/v1/channels/telegram/approvals/{approval_b}/reject",
        payload={},
        headers=auth_header(session_token),
    )
    assert reject_status == 200
    assert reject_payload["approval"]["status"] == "rejected"
    assert isinstance(reject_payload["challenge_updates"], list)

    approvals_message_id = _ingest_message(
        update_id=930002,
        message_id=730002,
        chat_id=85001,
        user_id=86001,
        username="approval_builder",
        text="/approvals",
    )
    approvals_handle_status, approvals_handle_payload = _handle_message(
        session_token=session_token,
        message_id=approvals_message_id,
    )
    assert approvals_handle_status == 200
    assert approvals_handle_payload["intent"]["intent_kind"] == "approvals"

    missing_approve_id_message_id = _ingest_message(
        update_id=930005,
        message_id=730005,
        chat_id=85001,
        user_id=86001,
        username="approval_builder",
        text="/approve",
    )
    missing_approve_id_status, missing_approve_id_payload = _handle_message(
        session_token=session_token,
        message_id=missing_approve_id_message_id,
    )
    assert missing_approve_id_status == 200
    assert missing_approve_id_payload["intent"]["intent_kind"] == "approval_approve"
    assert missing_approve_id_payload["intent"]["status"] == "failed"
    assert (
        missing_approve_id_payload["intent"]["result_payload"]["error"]["detail"]
        == "approve intent requires approval id"
    )

    missing_reject_id_message_id = _ingest_message(
        update_id=930006,
        message_id=730006,
        chat_id=85001,
        user_id=86001,
        username="approval_builder",
        text="/reject",
    )
    missing_reject_id_status, missing_reject_id_payload = _handle_message(
        session_token=session_token,
        message_id=missing_reject_id_message_id,
    )
    assert missing_reject_id_status == 200
    assert missing_reject_id_payload["intent"]["intent_kind"] == "approval_reject"
    assert missing_reject_id_payload["intent"]["status"] == "failed"
    assert (
        missing_reject_id_payload["intent"]["result_payload"]["error"]["detail"]
        == "reject intent requires approval id"
    )

    approve_chat_message_id = _ingest_message(
        update_id=930003,
        message_id=730003,
        chat_id=85001,
        user_id=86001,
        username="approval_builder",
        text=f"/approve {approval_c}",
    )
    approve_chat_status, approve_chat_payload = _handle_message(
        session_token=session_token,
        message_id=approve_chat_message_id,
    )
    assert approve_chat_status == 200
    assert approve_chat_payload["intent"]["intent_kind"] == "approval_approve"
    assert approve_chat_payload["intent"]["status"] == "handled"

    reject_chat_message_id = _ingest_message(
        update_id=930004,
        message_id=730004,
        chat_id=85001,
        user_id=86001,
        username="approval_builder",
        text=f"/reject {approval_d} no longer needed",
    )
    reject_chat_status, reject_chat_payload = _handle_message(
        session_token=session_token,
        message_id=reject_chat_message_id,
    )
    assert reject_chat_status == 200
    assert reject_chat_payload["intent"]["intent_kind"] == "approval_reject"
    assert reject_chat_payload["intent"]["status"] == "handled"

    pending_after_status, pending_after_payload = invoke_request(
        "GET",
        "/v1/channels/telegram/approvals",
        headers=auth_header(session_token),
    )
    assert pending_after_status == 200
    assert pending_after_payload["summary"]["pending_count"] == 0
