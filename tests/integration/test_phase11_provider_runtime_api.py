from __future__ import annotations

from io import BytesIO
import json
import socket
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio
import psycopg
import pytest

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings, WorkspaceProviderConfig


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


@pytest.fixture(autouse=True)
def allow_documentation_provider_hosts(monkeypatch) -> None:
    original_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(hostname: str, port, type=0, proto=0):
        if hostname.endswith(".example"):
            sockaddr = ("93.184.216.34", 0)
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)]
        return original_getaddrinfo(hostname, port, type=type, proto=proto)

    monkeypatch.setattr("alicebot_api.provider_security.socket.getaddrinfo", fake_getaddrinfo)


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


def install_openai_compatible_success(
    monkeypatch,
    *,
    models: list[str] | None = None,
    response_text: str = "OpenAI runtime response",
    response_id: str = "resp_openai_1",
    usage: dict[str, int] | None = None,
) -> list[dict[str, object]]:
    captured_requests: list[dict[str, object]] = []
    resolved_models = ["gpt-5-mini"] if models is None else models
    resolved_usage = (
        {"input_tokens": 12, "output_tokens": 5, "total_tokens": 17}
        if usage is None
        else usage
    )

    def fake_discovery_urlopen(request, timeout):
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": None if request.data is None else json.loads(request.data.decode("utf-8")),
            }
        )
        if request.full_url.endswith("/models"):
            return FakeHTTPResponse(
                json.dumps({"data": [{"id": model_name} for model_name in resolved_models]}).encode("utf-8")
            )
        raise AssertionError(f"unexpected openai-compatible discovery URL: {request.full_url}")

    def fake_invoke_urlopen(request, timeout):
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": None if request.data is None else json.loads(request.data.decode("utf-8")),
            }
        )
        return FakeHTTPResponse(
            json.dumps(
                {
                    "id": response_id,
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": response_text}],
                        }
                    ],
                    "usage": resolved_usage,
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("alicebot_api.local_provider_helpers.urlopen", fake_discovery_urlopen)
    monkeypatch.setattr("alicebot_api.response_generation.urlopen", fake_invoke_urlopen)
    return captured_requests


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
            if "vllm.example" in url:
                return FakeHTTPResponse(b"")
            return FakeHTTPResponse(json.dumps({"status": "ok"}).encode("utf-8"))
        if url.endswith("/v1/models") and "vllm.example" in url:
            return FakeHTTPResponse(json.dumps({"data": [{"id": "mistral-small-instruct"}]}).encode("utf-8"))
        if url.endswith("/v1/models"):
            return FakeHTTPResponse(json.dumps({"data": [{"id": "Meta-Llama-3.1-8B-Instruct"}]}).encode("utf-8"))
        raise AssertionError(f"unexpected local provider URL: {url}")

    monkeypatch.setattr("alicebot_api.local_provider_helpers.urlopen", fake_urlopen)

    ollama_status, ollama_payload = invoke_request(
        "POST",
        "/v1/providers/ollama/register",
        payload={
            "display_name": "Ollama Local",
            "base_url": "http://ollama.example:11434",
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
            "base_url": "http://llamacpp.example:8080",
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

    vllm_status, vllm_payload = invoke_request(
        "POST",
        "/v1/providers/vllm/register",
        payload={
            "display_name": "vLLM Self-Hosted",
            "base_url": "http://vllm.example:8001",
            "default_model": "mistral-small-instruct",
            "metadata": {"kind": "self_hosted"},
        },
        headers=auth_header(session_token),
    )
    assert vllm_status == 201
    vllm_provider_id = vllm_payload["provider"]["id"]
    assert vllm_payload["provider"]["provider_key"] == "vllm"
    assert vllm_payload["provider"]["model_provider"] == "openai_responses"
    assert vllm_payload["provider"]["auth_mode"] == "none"
    assert vllm_payload["provider"]["model_list_path"] == "/v1/models"
    assert vllm_payload["provider"]["healthcheck_path"] == "/health"
    assert vllm_payload["provider"]["invoke_path"] == "/v1/chat/completions"
    assert vllm_payload["capabilities"]["discovery_status"] == "ready"
    assert vllm_payload["capabilities"]["snapshot"]["health_status"] == "ok"
    assert vllm_payload["capabilities"]["snapshot"]["models"] == ["mistral-small-instruct"]

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/providers",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    assert list_payload["summary"]["total_count"] == 3
    listed_provider_ids = [item["id"] for item in list_payload["items"]]
    assert listed_provider_ids == [ollama_provider_id, llamacpp_provider_id, vllm_provider_id]

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

    vllm_detail_status, vllm_detail_payload = invoke_request(
        "GET",
        f"/v1/providers/{vllm_provider_id}",
        headers=auth_header(session_token),
    )
    assert vllm_detail_status == 200
    assert vllm_detail_payload["provider"]["id"] == vllm_provider_id
    assert vllm_detail_payload["capabilities"]["provider_id"] == vllm_provider_id

    captured_urls = [record["url"] for record in captured_requests]
    assert "http://ollama.example:11434/api/version" in captured_urls
    assert "http://ollama.example:11434/api/tags" in captured_urls
    assert "http://llamacpp.example:8080/health" in captured_urls
    assert "http://llamacpp.example:8080/v1/models" in captured_urls
    assert "http://vllm.example:8001/health" in captured_urls
    assert "http://vllm.example:8001/v1/models" in captured_urls


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
            if "vllm.example" in url:
                return FakeHTTPResponse(b"")
            return FakeHTTPResponse(json.dumps({"status": "ok"}).encode("utf-8"))
        if url.endswith("/v1/models") and "vllm.example" in url:
            return FakeHTTPResponse(json.dumps({"data": [{"id": "mistral-small-instruct"}]}).encode("utf-8"))
        if url.endswith("/v1/models"):
            return FakeHTTPResponse(json.dumps({"data": [{"id": "Meta-Llama-3.1-8B-Instruct"}]}).encode("utf-8"))
        if url.endswith("/v1/chat/completions"):
            if "vllm.example" in url:
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
                                "prompt_tokens": 13,
                                "completion_tokens": 4,
                                "total_tokens": 17,
                            },
                        }
                    ).encode("utf-8")
                )
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
            "base_url": "http://ollama.example:11434",
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
            "base_url": "http://llamacpp.example:8080",
            "default_model": "Meta-Llama-3.1-8B-Instruct",
        },
        headers=auth_header(session_token_a),
    )
    assert create_llamacpp_status == 201
    llamacpp_provider_id = create_llamacpp_payload["provider"]["id"]

    create_vllm_status, create_vllm_payload = invoke_request(
        "POST",
        "/v1/providers/vllm/register",
        payload={
            "display_name": "vLLM Runtime",
            "base_url": "http://vllm.example:8001",
            "default_model": "mistral-small-instruct",
        },
        headers=auth_header(session_token_a),
    )
    assert create_vllm_status == 201
    vllm_provider_id = create_vllm_payload["provider"]["id"]

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

    vllm_test_status, vllm_test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={
            "provider_id": vllm_provider_id,
            "prompt": "Validate self-hosted vllm path.",
        },
        headers=auth_header(session_token_a),
    )
    assert vllm_test_status == 200
    assert vllm_test_payload["result"]["text"] == "vLLM runtime response"
    assert vllm_test_payload["result"]["usage"]["total_tokens"] == 17

    vllm_runtime_status, vllm_runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": vllm_provider_id,
            "thread_id": thread_id,
            "message": "How is vllm runtime?",
        },
        headers=auth_header(session_token_a),
    )
    assert vllm_runtime_status == 200
    assert vllm_runtime_payload["assistant"]["provider_id"] == vllm_provider_id
    assert vllm_runtime_payload["assistant"]["provider_key"] == "vllm"
    assert vllm_runtime_payload["assistant"]["model_provider"] == "openai_responses"
    assert vllm_runtime_payload["assistant"]["text"] == "vLLM runtime response"
    assert vllm_runtime_payload["assistant"]["usage"]["total_tokens"] == 17
    assert UUID(vllm_runtime_payload["assistant"]["event_id"])

    captured_urls = [record["url"] for record in captured_requests]
    assert "http://ollama.example:11434/api/chat" in captured_urls
    assert "http://llamacpp.example:8080/v1/chat/completions" in captured_urls
    assert "http://vllm.example:8001/v1/chat/completions" in captured_urls


def test_phase13_hosted_provider_rows_respect_workspace_rls(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    install_openai_compatible_success(monkeypatch)
    owner_session_token, owner_workspace_id, owner_user_account_id = _bootstrap_workspace_session(
        "provider-rls-owner@example.com"
    )
    _, _, other_user_account_id = _bootstrap_workspace_session("provider-rls-other@example.com")

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "RLS Scoped Provider",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(owner_session_token),
    )
    assert create_status == 201
    provider_id = create_payload["provider"]["id"]

    with psycopg.connect(migrated_database_urls["app"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.current_user_account_id', %s, true)",
                (other_user_account_id,),
            )
            cur.execute("SELECT count(*) FROM model_providers WHERE id = %s", (provider_id,))
            other_visible_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM workspaces WHERE id = %s", (owner_workspace_id,))
            other_workspace_count = cur.fetchone()[0]

            cur.execute(
                "SELECT set_config('app.current_user_account_id', %s, true)",
                (owner_user_account_id,),
            )
            cur.execute("SELECT count(*) FROM model_providers WHERE id = %s", (provider_id,))
            owner_visible_count = cur.fetchone()[0]

    assert other_visible_count == 0
    assert other_workspace_count == 0
    assert owner_visible_count == 1


def test_phase13_hosted_rls_blocks_cross_workspace_membership_forgery(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    _, owner_workspace_id, _ = _bootstrap_workspace_session("provider-rls-owner-forgery@example.com")
    _, _, other_user_account_id = _bootstrap_workspace_session("provider-rls-other-forgery@example.com")

    with psycopg.connect(migrated_database_urls["app"]) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT set_config('app.current_user_account_id', %s, true)",
                        (other_user_account_id,),
                    )
                    cur.execute(
                        """
                        INSERT INTO workspace_members (workspace_id, user_account_id, role)
                        VALUES (%s, %s, 'member')
                        """,
                        (owner_workspace_id, other_user_account_id),
                    )

    with psycopg.connect(migrated_database_urls["app"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.current_user_account_id', %s, true)",
                (other_user_account_id,),
            )
            cur.execute(
                """
                SELECT count(*)
                FROM workspace_members
                WHERE workspace_id = %s
                  AND user_account_id = %s
                """,
                (owner_workspace_id, other_user_account_id),
            )
            member_count = cur.fetchone()[0]

    assert member_count == 0


def test_phase13_hosted_rls_blocks_cross_workspace_channel_identity_forgery(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    _, owner_workspace_id, _ = _bootstrap_workspace_session("provider-rls-owner-channel@example.com")
    _, _, other_user_account_id = _bootstrap_workspace_session("provider-rls-other-channel@example.com")

    with psycopg.connect(migrated_database_urls["app"]) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT set_config('app.current_user_account_id', %s, true)",
                        (other_user_account_id,),
                    )
                    cur.execute(
                        """
                        INSERT INTO channel_identities (
                          user_account_id,
                          workspace_id,
                          channel_type,
                          external_user_id,
                          external_chat_id,
                          external_username
                        )
                        VALUES (%s, %s, 'telegram', %s, %s, %s)
                        """,
                        (
                            other_user_account_id,
                            owner_workspace_id,
                            "telegram-user-1",
                            "telegram-chat-1",
                            "other-user",
                        ),
                    )

    with psycopg.connect(migrated_database_urls["app"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.current_user_account_id', %s, true)",
                (other_user_account_id,),
            )
            cur.execute(
                """
                SELECT count(*)
                FROM channel_identities
                WHERE workspace_id = %s
                  AND user_account_id = %s
                """,
                (owner_workspace_id, other_user_account_id),
            )
            identity_count = cur.fetchone()[0]

    assert identity_count == 0


def test_phase11_openai_compatible_registration_still_works(migrated_database_urls, monkeypatch) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    captured_requests = install_openai_compatible_success(
        monkeypatch,
        models=["gpt-4.1-mini", "gpt-5-mini"],
    )
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
    assert create_payload["capabilities"]["snapshot"]["models"] == ["gpt-4.1-mini", "gpt-5-mini"]
    assert any(record["url"] == "https://provider.example/v1/models" for record in captured_requests)

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


def test_phase14_workspace_bootstrap_config_seed_and_provider_update_refresh_capabilities(
    migrated_database_urls,
    monkeypatch,
) -> None:
    captured_requests: list[dict[str, object]] = []

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
            model_timeout_seconds=30,
            workspace_provider_configs=(
                WorkspaceProviderConfig(
                    provider_key="openai_compatible",
                    display_name="Configured OpenAI",
                    base_url="https://provider.example/v1",
                    api_key="provider-secret-key",
                    default_model="gpt-5-mini",
                ),
            ),
        ),
    )

    def fake_discovery_urlopen(request, timeout):
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": None if request.data is None else json.loads(request.data.decode("utf-8")),
            }
        )
        if request.full_url == "https://provider.example/v1/models":
            return FakeHTTPResponse(json.dumps({"data": [{"id": "gpt-5-mini"}]}).encode("utf-8"))
        if request.full_url == "https://updated-provider.example/v1/custom-models":
            return FakeHTTPResponse(
                json.dumps({"data": [{"id": "gpt-4.1-mini"}, {"id": "gpt-5-mini"}]}).encode("utf-8")
            )
        raise AssertionError(f"unexpected openai-compatible discovery URL: {request.full_url}")

    monkeypatch.setattr("alicebot_api.local_provider_helpers.urlopen", fake_discovery_urlopen)

    session_token, _, _ = _bootstrap_workspace_session("provider-bootstrap-config@example.com")

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/providers",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    assert list_payload["summary"]["total_count"] == 1
    provider_id = list_payload["items"][0]["id"]
    assert list_payload["items"][0]["display_name"] == "Configured OpenAI"

    update_status, update_payload = invoke_request(
        "PATCH",
        f"/v1/providers/{provider_id}",
        payload={
            "display_name": "Updated OpenAI",
            "base_url": "https://updated-provider.example/v1",
            "default_model": "gpt-4.1-mini",
            "model_list_path": "/custom-models",
            "healthcheck_path": "/custom-models",
            "invoke_path": "/custom-responses",
            "metadata": {"managed_by": "config"},
        },
        headers=auth_header(session_token),
    )
    assert update_status == 200
    assert update_payload["provider"]["display_name"] == "Updated OpenAI"
    assert update_payload["provider"]["invoke_path"] == "/custom-responses"
    assert update_payload["capabilities"]["snapshot"]["models"] == ["gpt-4.1-mini", "gpt-5-mini"]
    assert update_payload["capabilities"]["snapshot"]["models_endpoint"] == "/custom-models"
    assert any(record["url"] == "https://provider.example/v1/models" for record in captured_requests)
    assert any(
        record["url"] == "https://updated-provider.example/v1/custom-models"
        for record in captured_requests
    )


def test_phase14_workspace_bootstrap_config_seeds_vllm_provider(
    migrated_database_urls,
    monkeypatch,
) -> None:
    captured_requests: list[dict[str, object]] = []

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            magic_link_ttl_seconds=600,
            auth_session_ttl_seconds=3600,
            device_link_ttl_seconds=600,
            model_timeout_seconds=30,
            workspace_provider_configs=(
                WorkspaceProviderConfig(
                    provider_key="vllm",
                    display_name="Configured vLLM",
                    base_url="http://vllm.example:8001",
                    api_key="",
                    auth_mode="none",
                    default_model="mistral-small-instruct",
                    model_list_path="/v1/models",
                    healthcheck_path="/health",
                    invoke_path="/v1/chat/completions",
                ),
            ),
        ),
    )

    def fake_discovery_urlopen(request, timeout):
        captured_requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "headers": dict(request.header_items()),
                "body": None if request.data is None else json.loads(request.data.decode("utf-8")),
            }
        )
        if request.full_url == "http://vllm.example:8001/health":
            return FakeHTTPResponse(b"")
        if request.full_url == "http://vllm.example:8001/v1/models":
            return FakeHTTPResponse(json.dumps({"data": [{"id": "mistral-small-instruct"}]}).encode("utf-8"))
        raise AssertionError(f"unexpected vllm discovery URL: {request.full_url}")

    monkeypatch.setattr("alicebot_api.local_provider_helpers.urlopen", fake_discovery_urlopen)

    session_token, _, _ = _bootstrap_workspace_session("provider-bootstrap-vllm@example.com")

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/providers",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    assert list_payload["summary"]["total_count"] == 1
    provider = list_payload["items"][0]
    assert provider["display_name"] == "Configured vLLM"
    assert provider["provider_key"] == "vllm"
    assert provider["healthcheck_path"] == "/health"
    assert provider["model_list_path"] == "/v1/models"
    assert provider["invoke_path"] == "/v1/chat/completions"
    assert any(record["url"] == "http://vllm.example:8001/health" for record in captured_requests)
    assert any(record["url"] == "http://vllm.example:8001/v1/models" for record in captured_requests)

    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v1/providers/{provider['id']}",
        headers=auth_header(session_token),
    )
    assert detail_status == 200
    assert detail_payload["capabilities"]["discovery_status"] == "ready"
    assert detail_payload["capabilities"]["snapshot"]["health_status"] == "ok"
    assert detail_payload["capabilities"]["snapshot"]["models"] == ["mistral-small-instruct"]


def test_phase14_provider_invocation_telemetry_persists_for_test_and_runtime(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    install_openai_compatible_success(
        monkeypatch,
        models=["gpt-5-mini"],
        response_text="Telemetry runtime response",
        response_id="resp_telemetry_1",
        usage={"input_tokens": 14, "output_tokens": 3, "total_tokens": 17},
    )
    session_token, workspace_id, user_account_id = _bootstrap_workspace_session(
        "provider-telemetry@example.com"
    )

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "Telemetry OpenAI",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(session_token),
    )
    assert create_status == 201
    provider_id = create_payload["provider"]["id"]

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        email="provider-telemetry@example.com",
    )

    provider_test_status, provider_test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={"provider_id": provider_id},
        headers=auth_header(session_token),
    )
    assert provider_test_status == 200
    assert provider_test_payload["result"]["response_id"] == "resp_telemetry_1"

    runtime_status, runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "Persist provider invocation telemetry.",
        },
        headers=auth_header(session_token),
    )
    assert runtime_status == 200
    assert runtime_payload["assistant"]["response_id"] == "resp_telemetry_1"

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT invocation_kind,
                       status,
                       thread_id,
                       response_id,
                       usage->>'total_tokens' AS total_tokens,
                       runtime_provider
                FROM provider_invocation_telemetry
                WHERE workspace_id = %s
                  AND provider_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (workspace_id, provider_id),
            )
            telemetry_rows = cur.fetchall()

    assert len(telemetry_rows) == 2
    assert telemetry_rows[0][0] == "provider_test"
    assert telemetry_rows[0][1] == "succeeded"
    assert telemetry_rows[0][2] is None
    assert telemetry_rows[0][3] == "resp_telemetry_1"
    assert telemetry_rows[0][4] == "17"
    assert telemetry_rows[0][5] == "openai_responses"
    assert telemetry_rows[1][0] == "runtime_invoke"
    assert telemetry_rows[1][1] == "succeeded"
    assert str(telemetry_rows[1][2]) == thread_id
    assert telemetry_rows[1][3] == "resp_telemetry_1"
    assert telemetry_rows[1][4] == "17"
    assert telemetry_rows[1][5] == "openai_responses"


def test_phase14_provider_invocation_telemetry_respects_workspace_rls(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    install_openai_compatible_success(monkeypatch)
    owner_session_token, _, owner_user_account_id = _bootstrap_workspace_session(
        "provider-telemetry-rls-owner@example.com"
    )
    _, _, other_user_account_id = _bootstrap_workspace_session(
        "provider-telemetry-rls-other@example.com"
    )

    create_status, create_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "Telemetry RLS Provider",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(owner_session_token),
    )
    assert create_status == 201
    provider_id = create_payload["provider"]["id"]

    provider_test_status, _ = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={"provider_id": provider_id},
        headers=auth_header(owner_session_token),
    )
    assert provider_test_status == 200

    with psycopg.connect(migrated_database_urls["app"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('app.current_user_account_id', %s, true)",
                (other_user_account_id,),
            )
            cur.execute(
                "SELECT count(*) FROM provider_invocation_telemetry WHERE provider_id = %s",
                (provider_id,),
            )
            other_visible_count = cur.fetchone()[0]

            cur.execute(
                "SELECT set_config('app.current_user_account_id', %s, true)",
                (owner_user_account_id,),
            )
            cur.execute(
                "SELECT count(*) FROM provider_invocation_telemetry WHERE provider_id = %s",
                (provider_id,),
            )
            owner_visible_count = cur.fetchone()[0]

    assert other_visible_count == 0
    assert owner_visible_count == 1


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
            "base_url": "http://ollama.example:11434",
            "auth_mode": "none",
            "api_key": "should-not-be-stored",
            "default_model": "llama3.2:latest",
        },
        headers=auth_header(session_token),
    )
    assert status == 400
    assert payload["detail"] == "api_key must be empty when auth_mode is none"


def test_phase11_azure_provider_registration_test_and_no_plaintext_storage(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id, _ = _bootstrap_workspace_session("provider-azure-reg@example.com")
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
        if url.startswith("https://azure.example/openai/models"):
            return FakeHTTPResponse(json.dumps({"data": [{"id": "gpt-4.1-mini"}]}).encode("utf-8"))
        if url.startswith("https://azure.example/openai/responses"):
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "id": "resp_azure_test_1",
                        "status": "completed",
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": "Azure runtime response"}],
                            }
                        ],
                        "usage": {
                            "input_tokens": 10,
                            "output_tokens": 4,
                            "total_tokens": 14,
                        },
                    }
                ).encode("utf-8")
            )
        raise AssertionError(f"unexpected azure URL: {url}")

    monkeypatch.setattr("alicebot_api.azure_provider_helpers.urlopen", fake_urlopen)

    register_status, register_payload = invoke_request(
        "POST",
        "/v1/providers/azure/register",
        payload={
            "display_name": "Azure Primary",
            "base_url": "https://azure.example",
            "auth_mode": "azure_api_key",
            "api_key": "azure-secret-key",
            "api_version": "2024-10-21",
            "default_model": "gpt-4.1-mini",
            "metadata": {"kind": "enterprise"},
        },
        headers=auth_header(session_token),
    )
    assert register_status == 201
    provider_id = register_payload["provider"]["id"]
    assert register_payload["provider"]["provider_key"] == "azure"
    assert register_payload["provider"]["auth_mode"] == "azure_api_key"
    assert register_payload["provider"]["azure_api_version"] == "2024-10-21"
    assert register_payload["capabilities"]["discovery_status"] == "ready"
    assert register_payload["capabilities"]["snapshot"]["azure_api_version"] == "2024-10-21"
    assert register_payload["capabilities"]["snapshot"]["azure_auth_mode"] == "azure_api_key"
    assert register_payload["capabilities"]["snapshot"]["models"] == ["gpt-4.1-mini"]

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
    assert detail_payload["provider"]["provider_key"] == "azure"
    assert detail_payload["capabilities"]["provider_id"] == provider_id

    test_status, test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={
            "provider_id": provider_id,
            "prompt": "Reply with a concise Azure connectivity check.",
        },
        headers=auth_header(session_token),
    )
    assert test_status == 200
    assert test_payload["result"]["text"] == "Azure runtime response"
    assert test_payload["result"]["usage"]["total_tokens"] == 14

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT api_key, azure_auth_secret_ref, auth_mode, azure_api_version
                FROM model_providers
                WHERE id = %s
                  AND workspace_id = %s
                """,
                (provider_id, workspace_id),
            )
            row = cur.fetchone()
    assert row is not None
    stored_api_key, stored_secret_ref, stored_auth_mode, stored_api_version = row
    assert stored_auth_mode == "azure_api_key"
    assert stored_api_version == "2024-10-21"
    assert stored_api_key != "azure-secret-key"
    assert stored_secret_ref != "azure-secret-key"
    assert stored_secret_ref.startswith("provider_secret_ref:")

    captured_urls = [record["url"] for record in captured_requests]
    assert "https://azure.example/openai/models?api-version=2024-10-21" in captured_urls
    assert "https://azure.example/openai/responses?api-version=2024-10-21" in captured_urls
    invoke_record = next(record for record in captured_requests if "/openai/responses?" in record["url"])
    invoke_headers = {key.lower(): value for key, value in invoke_record["headers"].items()}
    assert invoke_headers["api-key"] == "azure-secret-key"
    assert "authorization" not in invoke_headers


def test_phase11_azure_runtime_invoke_workspace_isolation_and_ad_token_auth(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token_a, _, user_account_id_a = _bootstrap_workspace_session("provider-azure-a@example.com")
    session_token_b, _, _ = _bootstrap_workspace_session("provider-azure-b@example.com")
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
        if url.startswith("https://foundry.example/openai/models"):
            return FakeHTTPResponse(json.dumps({"data": [{"id": "gpt-4.1"}]}).encode("utf-8"))
        if url.startswith("https://foundry.example/openai/responses"):
            return FakeHTTPResponse(
                json.dumps(
                    {
                        "id": "resp_azure_runtime_1",
                        "status": "completed",
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": "Azure runtime invoke works"}],
                            }
                        ],
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 5,
                            "total_tokens": 17,
                        },
                    }
                ).encode("utf-8")
            )
        raise AssertionError(f"unexpected azure URL: {url}")

    monkeypatch.setattr("alicebot_api.azure_provider_helpers.urlopen", fake_urlopen)

    register_status, register_payload = invoke_request(
        "POST",
        "/v1/providers/azure/register",
        payload={
            "display_name": "Azure Entra",
            "base_url": "https://foundry.example",
            "auth_mode": "azure_ad_token",
            "ad_token": "entra-token-secret",
            "api_version": "2024-10-21",
            "default_model": "gpt-4.1",
        },
        headers=auth_header(session_token_a),
    )
    assert register_status == 201
    provider_id = register_payload["provider"]["id"]
    assert register_payload["provider"]["auth_mode"] == "azure_ad_token"

    other_workspace_status, other_workspace_payload = invoke_request(
        "GET",
        f"/v1/providers/{provider_id}",
        headers=auth_header(session_token_b),
    )
    assert other_workspace_status == 404
    assert "was not found" in other_workspace_payload["detail"]

    invalid_register_status, invalid_register_payload = invoke_request(
        "POST",
        "/v1/providers/azure/register",
        payload={
            "display_name": "Azure Invalid",
            "base_url": "https://foundry.example",
            "auth_mode": "azure_ad_token",
            "ad_token": "valid-token-that-should-have-been-alone",
            "api_key": "must-not-be-sent",
            "default_model": "gpt-4.1",
        },
        headers=auth_header(session_token_a),
    )
    assert invalid_register_status == 422
    assert "api_key must be empty when auth_mode is azure_ad_token" in json.dumps(
        invalid_register_payload["detail"]
    )

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id_a,
        email="provider-azure-a@example.com",
    )
    runtime_status, runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "Give a concise enterprise runtime check.",
        },
        headers=auth_header(session_token_a),
    )
    assert runtime_status == 200
    assert runtime_payload["assistant"]["provider_id"] == provider_id
    assert runtime_payload["assistant"]["provider_key"] == "azure"
    assert runtime_payload["assistant"]["text"] == "Azure runtime invoke works"
    assert runtime_payload["assistant"]["usage"]["total_tokens"] == 17

    invoke_record = next(record for record in captured_requests if "/openai/responses?" in record["url"])
    headers = {key.lower(): value for key, value in invoke_record["headers"].items()}
    assert headers["authorization"] == "Bearer entra-token-secret"
    assert "api-key" not in headers


def test_phase11_provider_registration_rejects_disallowed_targets(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, _, _ = _bootstrap_workspace_session("provider-security-blocked-register@example.com")

    blocked_base_urls = [
        "http://169.254.169.254/v1",
        "http://127.0.0.1:11434/v1",
        "http://10.0.10.7/v1",
        "http://192.168.1.44/v1",
        "http://172.16.3.8/v1",
        "http://0x7f000001/v1",
        "http://017700000001/v1",
        "http://127.1/v1",
    ]
    for blocked_base_url in blocked_base_urls:
        status, payload = invoke_request(
            "POST",
            "/v1/providers",
            payload={
                "provider_key": "openai_compatible",
                "display_name": f"Blocked {blocked_base_url}",
                "base_url": blocked_base_url,
                "api_key": "provider-secret-key",
                "default_model": "gpt-5-mini",
            },
            headers=auth_header(session_token),
        )
        assert status == 400
        assert "not allowed by outbound policy" in payload["detail"]


def test_phase11_provider_test_and_runtime_reject_disallowed_target_without_outbound(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    install_openai_compatible_success(monkeypatch)
    session_token, workspace_id, user_account_id = _bootstrap_workspace_session(
        "provider-security-blocked-runtime@example.com"
    )
    urlopen_call_count = 0

    def fake_urlopen(_request, _timeout):
        nonlocal urlopen_call_count
        urlopen_call_count += 1
        raise AssertionError("outbound request should not be attempted for blocked targets")

    monkeypatch.setattr("alicebot_api.response_generation.urlopen", fake_urlopen)

    register_status, register_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "OpenAI Blocked Runtime",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(session_token),
    )
    assert register_status == 201
    provider_id = register_payload["provider"]["id"]

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE model_providers
                SET base_url = %s
                WHERE id = %s
                  AND workspace_id = %s
                """,
                ("http://0x7f000001/latest/meta-data", provider_id, workspace_id),
            )
        conn.commit()

    test_status, test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={"provider_id": provider_id},
        headers=auth_header(session_token),
    )
    assert test_status == 400
    assert "not allowed by outbound policy" in test_payload["detail"]

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        email="provider-security-blocked-runtime@example.com",
    )
    runtime_status, runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "hello",
        },
        headers=auth_header(session_token),
    )
    assert runtime_status == 400
    assert "not allowed by outbound policy" in runtime_payload["detail"]
    assert urlopen_call_count == 0


def test_phase11_provider_rejects_userinfo_and_redacts_legacy_rows(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id, user_account_id = _bootstrap_workspace_session("provider-security-userinfo@example.com")

    rejected_status, rejected_payload = invoke_request(
        "POST",
        "/v1/providers/azure/register",
        payload={
            "display_name": "Azure UserInfo",
            "base_url": "https://alice:secret@azure.example/openai",
            "auth_mode": "azure_api_key",
            "api_key": "azure-secret-key",
            "api_version": "2024-10-21",
            "default_model": "gpt-4.1-mini",
        },
        headers=auth_header(session_token),
    )
    assert rejected_status == 400
    assert "embedded credentials" in rejected_payload["detail"]

    legacy_provider_id: str
    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_providers (
                  workspace_id,
                  created_by_user_account_id,
                  provider_key,
                  model_provider,
                  display_name,
                  base_url,
                  api_key,
                  auth_mode,
                  default_model,
                  status,
                  model_list_path,
                  healthcheck_path,
                  invoke_path,
                  azure_api_version,
                  azure_auth_secret_ref,
                  metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                RETURNING id
                """,
                (
                    workspace_id,
                    user_account_id,
                    "openai_compatible",
                    "openai_responses",
                    "Legacy UserInfo Provider",
                    "https://legacy-user:legacy-pass@provider.example/v1",
                    "provider_secret_ref:legacy",
                    "bearer",
                    "gpt-5-mini",
                    "active",
                    "/models",
                    "/models",
                    "/responses",
                    "",
                    "",
                    "{}",
                ),
            )
            legacy_provider_id = str(cur.fetchone()[0])
        conn.commit()

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/providers",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    listed_legacy = next(item for item in list_payload["items"] if item["id"] == legacy_provider_id)
    assert listed_legacy["base_url"] == "https://provider.example/v1"

    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v1/providers/{legacy_provider_id}",
        headers=auth_header(session_token),
    )
    assert detail_status == 200
    assert detail_payload["provider"]["base_url"] == "https://provider.example/v1"


def test_phase11_provider_error_reflection_and_persistence_are_sanitized(
    migrated_database_urls,
    monkeypatch,
) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    install_openai_compatible_success(monkeypatch)
    session_token, _, user_account_id = _bootstrap_workspace_session(
        "provider-security-sanitized-errors@example.com"
    )
    sensitive_detail = "UPSTREAM_SECRET_TOKEN_ABC123"

    def fake_urlopen(request, timeout):
        del timeout
        raise HTTPError(
            url=request.full_url,
            code=502,
            msg="Bad Gateway",
            hdrs=None,
            fp=BytesIO(
                json.dumps({"error": {"message": f"provider failed with {sensitive_detail}"}}).encode("utf-8")
            ),
        )

    monkeypatch.setattr("alicebot_api.response_generation.urlopen", fake_urlopen)

    register_status, register_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "OpenAI Sanitized Errors",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(session_token),
    )
    assert register_status == 201
    provider_id = register_payload["provider"]["id"]

    test_status, test_payload = invoke_request(
        "POST",
        "/v1/providers/test",
        payload={
            "provider_id": provider_id,
            "prompt": "Ping test provider.",
        },
        headers=auth_header(session_token),
    )
    assert test_status == 502
    assert test_payload["detail"] == "provider upstream request failed"
    assert sensitive_detail not in json.dumps(test_payload)

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT discovery_error
                FROM provider_capabilities
                WHERE provider_id = %s
                """,
                (provider_id,),
            )
            provider_capability_row = cur.fetchone()
    assert provider_capability_row is not None
    assert provider_capability_row[0] == "provider upstream request failed"
    assert sensitive_detail not in provider_capability_row[0]

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        email="provider-security-sanitized-errors@example.com",
    )
    runtime_status, runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "Runtime request should fail safely.",
        },
        headers=auth_header(session_token),
    )
    assert runtime_status == 502
    assert runtime_payload["detail"] == "provider upstream request failed"
    assert sensitive_detail not in json.dumps(runtime_payload)

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT te.payload->>'error_message'
                FROM trace_events te
                JOIN traces t
                  ON t.id = te.trace_id
                WHERE t.user_id = %s
                  AND t.thread_id = %s
                  AND te.kind = 'response.model.failed'
                ORDER BY te.created_at DESC
                LIMIT 1
                """,
                (user_account_id, thread_id),
            )
            trace_row = cur.fetchone()
    assert trace_row is not None
    assert trace_row[0] == "provider upstream request failed"
    assert sensitive_detail not in trace_row[0]
