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
            model_timeout_seconds=30,
        ),
    )


def _bootstrap_workspace_session(email: str) -> tuple[str, str, str]:
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
            "device_label": "P11-S1 Device",
            "device_key": f"device-{email}",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]
    user_account_id = verify_payload["user_account"]["id"]

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "P11 Provider Workspace"},
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
    return session_token, workspace_id, user_account_id


def _seed_thread_for_user(*, admin_db_url: str, user_id: str, email: str) -> str:
    thread_id = str(uuid4())
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
                (user_id, email, "Provider Runtime User"),
            )
            cur.execute(
                """
                INSERT INTO threads (id, user_id, title)
                VALUES (%s, %s, %s)
                """,
                (thread_id, user_id, "Provider Runtime Thread"),
            )
        conn.commit()
    return thread_id


def test_phase11_provider_registration_list_and_detail(migrated_database_urls, monkeypatch) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id, _ = _bootstrap_workspace_session("provider-reg@example.com")

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "Primary OpenAI",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
            "metadata": {"tier": "test"},
        },
        headers=auth_header(session_token),
    )
    assert create_status == 201
    provider_id = create_payload["provider"]["id"]
    assert create_payload["provider"]["provider_key"] == "openai_compatible"
    assert create_payload["provider"]["model_provider"] == "openai_responses"
    assert create_payload["capabilities"]["discovery_status"] == "ready"
    assert create_payload["capabilities"]["snapshot"]["runtime_provider"] == "openai_responses"

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT api_key
                FROM model_providers
                WHERE id = %s
                  AND workspace_id = %s
                """,
                (provider_id, workspace_id),
            )
            stored_api_key_row = cur.fetchone()
    assert stored_api_key_row is not None
    assert stored_api_key_row[0] != "provider-secret-key"
    assert stored_api_key_row[0].startswith("provider_secret_ref:")

    duplicate_status, duplicate_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "Primary OpenAI",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(session_token),
    )
    assert duplicate_status == 409
    assert "display_name" in duplicate_payload["detail"]

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/providers",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    assert list_payload["summary"]["total_count"] == 1
    assert list_payload["items"][0]["id"] == provider_id

    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v1/providers/{provider_id}",
        headers=auth_header(session_token),
    )
    assert detail_status == 200
    assert detail_payload["provider"]["id"] == provider_id
    assert detail_payload["capabilities"]["provider_id"] == provider_id


def test_phase11_provider_test_runtime_invoke_and_workspace_isolation(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token_a, _, user_account_id_a = _bootstrap_workspace_session("provider-a@example.com")
    session_token_b, _, _ = _bootstrap_workspace_session("provider-b@example.com")

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "Shared Runtime",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(session_token_a),
    )
    assert create_status == 201
    provider_id = create_payload["provider"]["id"]

    detail_other_status, detail_other_payload = invoke_request(
        "GET",
        f"/v1/providers/{provider_id}",
        headers=auth_header(session_token_b),
    )
    assert detail_other_status == 404
    assert "was not found" in detail_other_payload["detail"]

    captured_requests: list[dict[str, object]] = []

    class FakeHTTPResponse:
        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    def fake_urlopen(request, timeout):
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": json.loads(request.data.decode("utf-8")),
            }
        )
        return FakeHTTPResponse(
            json.dumps(
                {
                    "id": f"resp_{len(captured_requests)}",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Provider response"}],
                        }
                    ],
                    "usage": {
                        "input_tokens": 11,
                        "output_tokens": 5,
                        "total_tokens": 16,
                    },
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("alicebot_api.response_generation.urlopen", fake_urlopen)

    test_status, test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={
            "provider_id": provider_id,
            "prompt": "Validate provider test path.",
        },
        headers=auth_header(session_token_a),
    )
    assert test_status == 200
    assert test_payload["result"]["text"] == "Provider response"
    assert test_payload["result"]["usage"]["total_tokens"] == 16
    assert captured_requests[0]["url"] == "https://provider.example/v1/responses"
    assert captured_requests[0]["headers"]["Authorization"] == "Bearer provider-secret-key"

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id_a,
        email="provider-a@example.com",
    )

    runtime_status, runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "What is the runtime status?",
        },
        headers=auth_header(session_token_a),
    )
    assert runtime_status == 200
    assert runtime_payload["assistant"]["provider_id"] == provider_id
    assert runtime_payload["assistant"]["provider_key"] == "openai_compatible"
    assert runtime_payload["assistant"]["model_provider"] == "openai_responses"
    assert runtime_payload["assistant"]["text"] == "Provider response"
    assert runtime_payload["assistant"]["usage"]["total_tokens"] == 16
    assert captured_requests[1]["url"] == "https://provider.example/v1/responses"
    assert captured_requests[1]["headers"]["Authorization"] == "Bearer provider-secret-key"
    assert UUID(runtime_payload["assistant"]["event_id"])
