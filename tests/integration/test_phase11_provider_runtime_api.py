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
            "device_label": "P11-S2 Device",
            "device_key": f"device-{email}",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]
    user_account_id = verify_payload["user_account"]["id"]

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "P11 Local Provider Workspace"},
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
                (user_id, email, "Local Provider Runtime User"),
            )
            cur.execute(
                """
                INSERT INTO threads (id, user_id, title)
                VALUES (%s, %s, %s)
                """,
                (thread_id, user_id, "Local Provider Runtime Thread"),
            )
        conn.commit()
    return thread_id


class FakeHTTPResponse:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_phase11_local_provider_registration_list_and_detail(migrated_database_urls, monkeypatch) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _, _ = _bootstrap_workspace_session("provider-local-reg@example.com")
    captured_requests: list[dict[str, object]] = []

    def fake_urlopen(request, timeout):
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": None if request.data is None else json.loads(request.data.decode("utf-8")),
            }
        )
        url = request.full_url
        if url.endswith("/api/version"):
            return FakeHTTPResponse(json.dumps({"version": "0.4.0"}).encode("utf-8"))
        if url.endswith("/api/tags"):
            return FakeHTTPResponse(
                json.dumps({"models": [{"name": "llama3.2:latest"}, {"name": "qwen2.5:latest"}]}).encode("utf-8")
            )
        if url.endswith("/health"):
            return FakeHTTPResponse(json.dumps({"status": "ok"}).encode("utf-8"))
        if url.endswith("/v1/models"):
            return FakeHTTPResponse(json.dumps({"data": [{"id": "Meta-Llama-3.1-8B-Instruct"}]}).encode("utf-8"))
        raise AssertionError(f"unexpected local provider URL: {url}")

    monkeypatch.setattr("alicebot_api.local_provider_helpers.urlopen", fake_urlopen)

    ollama_status, ollama_payload = invoke_request(
        "POST",
        "/v1/providers/ollama/register",
        payload={
            "display_name": "Ollama Local",
            "base_url": "http://127.0.0.1:11434",
            "default_model": "llama3.2:latest",
            "metadata": {"kind": "local"},
        },
        headers=auth_header(session_token),
    )
    assert ollama_status == 201
    ollama_provider_id = ollama_payload["provider"]["id"]
    assert ollama_payload["provider"]["provider_key"] == "ollama"
    assert ollama_payload["provider"]["model_provider"] == "openai_responses"
    assert ollama_payload["provider"]["auth_mode"] == "none"
    assert ollama_payload["provider"]["model_list_path"] == "/api/tags"
    assert ollama_payload["provider"]["healthcheck_path"] == "/api/version"
    assert ollama_payload["provider"]["invoke_path"] == "/api/chat"
    assert ollama_payload["capabilities"]["discovery_status"] == "ready"
    assert ollama_payload["capabilities"]["snapshot"]["health_status"] == "ok"
    assert ollama_payload["capabilities"]["snapshot"]["models"] == [
        "llama3.2:latest",
        "qwen2.5:latest",
    ]

    llamacpp_status, llamacpp_payload = invoke_request(
        "POST",
        "/v1/providers/llamacpp/register",
        payload={
            "display_name": "llama.cpp Local",
            "base_url": "http://127.0.0.1:8080",
            "default_model": "Meta-Llama-3.1-8B-Instruct",
            "metadata": {"kind": "local"},
        },
        headers=auth_header(session_token),
    )
    assert llamacpp_status == 201
    llamacpp_provider_id = llamacpp_payload["provider"]["id"]
    assert llamacpp_payload["provider"]["provider_key"] == "llamacpp"
    assert llamacpp_payload["provider"]["model_provider"] == "openai_responses"
    assert llamacpp_payload["provider"]["auth_mode"] == "none"
    assert llamacpp_payload["provider"]["model_list_path"] == "/v1/models"
    assert llamacpp_payload["provider"]["healthcheck_path"] == "/health"
    assert llamacpp_payload["provider"]["invoke_path"] == "/v1/chat/completions"
    assert llamacpp_payload["capabilities"]["discovery_status"] == "ready"
    assert llamacpp_payload["capabilities"]["snapshot"]["health_status"] == "ok"
    assert llamacpp_payload["capabilities"]["snapshot"]["models"] == ["Meta-Llama-3.1-8B-Instruct"]

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/providers",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    assert list_payload["summary"]["total_count"] == 2
    listed_provider_ids = [item["id"] for item in list_payload["items"]]
    assert listed_provider_ids == [ollama_provider_id, llamacpp_provider_id]

    ollama_detail_status, ollama_detail_payload = invoke_request(
        "GET",
        f"/v1/providers/{ollama_provider_id}",
        headers=auth_header(session_token),
    )
    assert ollama_detail_status == 200
    assert ollama_detail_payload["provider"]["id"] == ollama_provider_id
    assert ollama_detail_payload["capabilities"]["provider_id"] == ollama_provider_id

    llamacpp_detail_status, llamacpp_detail_payload = invoke_request(
        "GET",
        f"/v1/providers/{llamacpp_provider_id}",
        headers=auth_header(session_token),
    )
    assert llamacpp_detail_status == 200
    assert llamacpp_detail_payload["provider"]["id"] == llamacpp_provider_id
    assert llamacpp_detail_payload["capabilities"]["provider_id"] == llamacpp_provider_id

    captured_urls = [record["url"] for record in captured_requests]
    assert "http://127.0.0.1:11434/api/version" in captured_urls
    assert "http://127.0.0.1:11434/api/tags" in captured_urls
    assert "http://127.0.0.1:8080/health" in captured_urls
    assert "http://127.0.0.1:8080/v1/models" in captured_urls


def test_phase11_local_provider_test_runtime_invoke_and_workspace_isolation(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token_a, _, user_account_id_a = _bootstrap_workspace_session("provider-local-a@example.com")
    session_token_b, _, _ = _bootstrap_workspace_session("provider-local-b@example.com")

    captured_requests: list[dict[str, object]] = []

    def fake_urlopen(request, timeout):
        body = None if request.data is None else json.loads(request.data.decode("utf-8"))
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": body,
            }
        )
        url = request.full_url
        if url.endswith("/api/version"):
            return FakeHTTPResponse(json.dumps({"version": "0.4.0"}).encode("utf-8"))
        if url.endswith("/api/tags"):
            return FakeHTTPResponse(json.dumps({"models": [{"name": "llama3.2:latest"}]}).encode("utf-8"))
        if url.endswith("/api/chat"):
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "model": "llama3.2:latest",
                        "done": True,
                        "message": {"role": "assistant", "content": "Ollama runtime response"},
                        "prompt_eval_count": 12,
                        "eval_count": 5,
                    }
                ).encode("utf-8")
            )
        if url.endswith("/health"):
            return FakeHTTPResponse(json.dumps({"status": "ok"}).encode("utf-8"))
        if url.endswith("/v1/models"):
            return FakeHTTPResponse(json.dumps({"data": [{"id": "Meta-Llama-3.1-8B-Instruct"}]}).encode("utf-8"))
        if url.endswith("/v1/chat/completions"):
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "id": "chatcmpl-local-2",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": "llama.cpp runtime response"},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 13,
                            "completion_tokens": 4,
                            "total_tokens": 17,
                        },
                    }
                ).encode("utf-8")
            )
        raise AssertionError(f"unexpected local provider URL: {url}")

    monkeypatch.setattr("alicebot_api.local_provider_helpers.urlopen", fake_urlopen)

    create_ollama_status, create_ollama_payload = invoke_request(
        "POST",
        "/v1/providers/ollama/register",
        payload={
            "display_name": "Ollama Runtime",
            "base_url": "http://127.0.0.1:11434",
            "default_model": "llama3.2:latest",
        },
        headers=auth_header(session_token_a),
    )
    assert create_ollama_status == 201
    ollama_provider_id = create_ollama_payload["provider"]["id"]

    create_llamacpp_status, create_llamacpp_payload = invoke_request(
        "POST",
        "/v1/providers/llamacpp/register",
        payload={
            "display_name": "llama.cpp Runtime",
            "base_url": "http://127.0.0.1:8080",
            "default_model": "Meta-Llama-3.1-8B-Instruct",
        },
        headers=auth_header(session_token_a),
    )
    assert create_llamacpp_status == 201
    llamacpp_provider_id = create_llamacpp_payload["provider"]["id"]

    detail_other_status, detail_other_payload = invoke_request(
        "GET",
        f"/v1/providers/{ollama_provider_id}",
        headers=auth_header(session_token_b),
    )
    assert detail_other_status == 404
    assert "was not found" in detail_other_payload["detail"]

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id_a,
        email="provider-local-a@example.com",
    )

    ollama_test_status, ollama_test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={
            "provider_id": ollama_provider_id,
            "prompt": "Validate local ollama path.",
        },
        headers=auth_header(session_token_a),
    )
    assert ollama_test_status == 200
    assert ollama_test_payload["result"]["text"] == "Ollama runtime response"
    assert ollama_test_payload["result"]["usage"]["total_tokens"] == 17

    ollama_runtime_status, ollama_runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": ollama_provider_id,
            "thread_id": thread_id,
            "message": "How is ollama runtime?",
        },
        headers=auth_header(session_token_a),
    )
    assert ollama_runtime_status == 200
    assert ollama_runtime_payload["assistant"]["provider_id"] == ollama_provider_id
    assert ollama_runtime_payload["assistant"]["provider_key"] == "ollama"
    assert ollama_runtime_payload["assistant"]["model_provider"] == "openai_responses"
    assert ollama_runtime_payload["assistant"]["text"] == "Ollama runtime response"
    assert ollama_runtime_payload["assistant"]["usage"]["total_tokens"] == 17
    assert UUID(ollama_runtime_payload["assistant"]["event_id"])

    llamacpp_test_status, llamacpp_test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={
            "provider_id": llamacpp_provider_id,
            "prompt": "Validate local llamacpp path.",
        },
        headers=auth_header(session_token_a),
    )
    assert llamacpp_test_status == 200
    assert llamacpp_test_payload["result"]["text"] == "llama.cpp runtime response"
    assert llamacpp_test_payload["result"]["usage"]["total_tokens"] == 17

    llamacpp_runtime_status, llamacpp_runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": llamacpp_provider_id,
            "thread_id": thread_id,
            "message": "How is llamacpp runtime?",
        },
        headers=auth_header(session_token_a),
    )
    assert llamacpp_runtime_status == 200
    assert llamacpp_runtime_payload["assistant"]["provider_id"] == llamacpp_provider_id
    assert llamacpp_runtime_payload["assistant"]["provider_key"] == "llamacpp"
    assert llamacpp_runtime_payload["assistant"]["model_provider"] == "openai_responses"
    assert llamacpp_runtime_payload["assistant"]["text"] == "llama.cpp runtime response"
    assert llamacpp_runtime_payload["assistant"]["usage"]["total_tokens"] == 17
    assert UUID(llamacpp_runtime_payload["assistant"]["event_id"])

    captured_urls = [record["url"] for record in captured_requests]
    assert "http://127.0.0.1:11434/api/chat" in captured_urls
    assert "http://127.0.0.1:8080/v1/chat/completions" in captured_urls


def test_phase11_vllm_registration_runtime_and_telemetry(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _, user_account_id = _bootstrap_workspace_session("provider-vllm-a@example.com")
    session_token_other, _, _ = _bootstrap_workspace_session("provider-vllm-b@example.com")

    captured_requests: list[dict[str, object]] = []

    def fake_urlopen(request, timeout):
        body = None if request.data is None else json.loads(request.data.decode("utf-8"))
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": body,
            }
        )
        url = request.full_url
        if url.endswith("/health"):
            return FakeHTTPResponse(json.dumps({"status": "ok"}).encode("utf-8"))
        if url.endswith("/v1/models"):
            return FakeHTTPResponse(json.dumps({"data": [{"id": "meta-llama/Meta-Llama-3.1-8B-Instruct"}]}).encode("utf-8"))
        if url.endswith("/v1/chat/completions"):
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "id": "chatcmpl-vllm-2",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": "vLLM runtime response"},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 19,
                            "completion_tokens": 6,
                            "total_tokens": 25,
                        },
                    }
                ).encode("utf-8")
            )
        raise AssertionError(f"unexpected local provider URL: {url}")

    monkeypatch.setattr("alicebot_api.local_provider_helpers.urlopen", fake_urlopen)

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/providers/vllm/register",
        payload={
            "display_name": "vLLM Self-Hosted",
            "base_url": "http://127.0.0.1:8001",
            "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "adapter_options": {
                "invoke_passthrough": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_tokens": 256,
                    "stop": ["###"],
                }
            },
            "metadata": {"kind": "self_hosted"},
        },
        headers=auth_header(session_token),
    )
    assert create_status == 201
    provider_id = create_payload["provider"]["id"]
    assert create_payload["provider"]["provider_key"] == "vllm"
    assert create_payload["provider"]["adapter_options"]["invoke_passthrough"]["temperature"] == 0.2
    assert create_payload["capabilities"]["snapshot"]["supports_normalized_latency_telemetry"] is True
    assert create_payload["capabilities"]["snapshot"]["supports_normalized_usage_telemetry"] is True
    assert create_payload["capabilities"]["snapshot"]["telemetry_flow_scope"] == [
        "provider_test",
        "runtime_invoke",
    ]

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        email="provider-vllm-a@example.com",
    )

    test_status, test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={
            "provider_id": provider_id,
            "prompt": "Validate vllm path.",
        },
        headers=auth_header(session_token),
    )
    assert test_status == 200
    assert test_payload["result"]["text"] == "vLLM runtime response"
    assert test_payload["result"]["usage"]["total_tokens"] == 25

    invoke_status, invoke_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "How is vllm runtime?",
        },
        headers=auth_header(session_token),
    )
    assert invoke_status == 200
    assert invoke_payload["assistant"]["provider_key"] == "vllm"
    assert invoke_payload["assistant"]["usage"]["total_tokens"] == 25

    telemetry_status, telemetry_payload = invoke_request(
        "GET",
        f"/v1/providers/{provider_id}/telemetry",
        query_params={"limit": "10"},
        headers=auth_header(session_token),
    )
    assert telemetry_status == 200
    assert telemetry_payload["provider_id"] == provider_id
    assert telemetry_payload["summary"]["total_count"] == 2
    assert telemetry_payload["summary"]["completed_count"] == 2
    assert telemetry_payload["summary"]["failed_count"] == 0
    assert telemetry_payload["summary"]["usage_totals"]["total_tokens"] == 50
    telemetry_flow_kinds = [item["flow_kind"] for item in telemetry_payload["items"]]
    assert "provider_test" in telemetry_flow_kinds
    assert "runtime_invoke" in telemetry_flow_kinds

    other_workspace_status, other_workspace_payload = invoke_request(
        "GET",
        f"/v1/providers/{provider_id}/telemetry",
        headers=auth_header(session_token_other),
    )
    assert other_workspace_status == 404
    assert "was not found" in other_workspace_payload["detail"]

    invoke_bodies = [
        record["body"]
        for record in captured_requests
        if record["url"] == "http://127.0.0.1:8001/v1/chat/completions"
    ]
    assert len(invoke_bodies) == 2
    for invoke_body in invoke_bodies:
        assert isinstance(invoke_body, dict)
        assert invoke_body["temperature"] == 0.2
        assert invoke_body["top_p"] == 0.9
        assert invoke_body["max_tokens"] == 256
        assert invoke_body["stop"] == ["###"]
        assert "unexpected_option" not in invoke_body


def test_phase11_openai_compatible_registration_still_works(migrated_database_urls, monkeypatch) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id, _ = _bootstrap_workspace_session("provider-openai-reg@example.com")

    create_status, create_payload = invoke_request(
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
    assert create_status == 201
    provider_id = create_payload["provider"]["id"]
    assert create_payload["provider"]["provider_key"] == "openai_compatible"
    assert create_payload["provider"]["auth_mode"] == "bearer"
    assert create_payload["capabilities"]["discovery_status"] == "ready"
    assert create_payload["capabilities"]["snapshot"]["runtime_provider"] == "openai_responses"

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT api_key, auth_mode
                FROM model_providers
                WHERE id = %s
                  AND workspace_id = %s
                """,
                (provider_id, workspace_id),
            )
            stored_row = cur.fetchone()
    assert stored_row is not None
    stored_api_key, stored_auth_mode = stored_row
    assert stored_auth_mode == "bearer"
    assert stored_api_key != "provider-secret-key"
    assert stored_api_key.startswith("provider_secret_ref:")


def test_phase11_local_provider_rejects_api_key_when_auth_mode_none(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _, _ = _bootstrap_workspace_session("provider-local-authmode-none@example.com")

    status, payload = invoke_request(
        "POST",
        "/v1/providers/ollama/register",
        payload={
            "display_name": "Ollama Invalid Auth",
            "base_url": "http://127.0.0.1:11434",
            "auth_mode": "none",
            "api_key": "should-not-be-stored",
            "default_model": "llama3.2:latest",
        },
        headers=auth_header(session_token),
    )
    assert status == 400
    assert payload["detail"] == "api_key must be empty when auth_mode is none"
