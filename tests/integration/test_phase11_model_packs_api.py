from __future__ import annotations

import json
import socket
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio
import psycopg
import pytest

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
            "device_label": "P11-S4 Device",
            "device_key": f"device-{email}",
        },
    )
    assert verify_status == 200
    session_token = verify_payload["session_token"]
    user_account_id = verify_payload["user_account"]["id"]

    create_workspace_status, create_workspace_payload = invoke_request(
        "POST",
        "/v1/workspaces",
        payload={"name": "P11 Model Pack Workspace"},
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
                (user_id, email, "Model Pack Runtime User"),
            )
            cur.execute(
                """
                INSERT INTO threads (id, user_id, title)
                VALUES (%s, %s, %s)
                """,
                (thread_id, user_id, "Model Pack Runtime Thread"),
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


def _extract_context_payload(http_payload: dict[str, Any]) -> dict[str, Any]:
    input_items = http_payload["input"]
    context_item = next(
        item
        for item in input_items
        if item["role"] == "user" and item["content"][0]["text"].startswith("[CONTEXT]\n")
    )
    context_text = context_item["content"][0]["text"].split("\n", maxsplit=1)[1]
    return json.loads(context_text)


def test_phase11_model_pack_catalog_bind_and_runtime_shaping(migrated_database_urls, monkeypatch) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token, workspace_id, user_account_id = _bootstrap_workspace_session(
        "model-pack-a@example.com"
    )

    create_provider_status, create_provider_payload = invoke_request(
        "POST",
        "/v1/providers",
        payload={
            "provider_key": "openai_compatible",
            "display_name": "Pack Runtime Provider",
            "base_url": "https://provider.example/v1",
            "api_key": "provider-secret-key",
            "default_model": "gpt-5-mini",
        },
        headers=auth_header(session_token),
    )
    assert create_provider_status == 201
    provider_id = create_provider_payload["provider"]["id"]

    list_status, list_payload = invoke_request(
        "GET",
        "/v1/model-packs",
        headers=auth_header(session_token),
    )
    assert list_status == 200
    listed_ids = {item["pack_id"] for item in list_payload["items"]}
    assert {
        "llama",
        "qwen",
        "gemma",
        "gpt-oss",
        "deepseek",
        "kimi",
        "mistral",
    }.issubset(listed_ids)

    detail_status, detail_payload = invoke_request(
        "GET",
        "/v1/model-packs/deepseek",
        query_params={"version": "1.0.0"},
        headers=auth_header(session_token),
    )
    assert detail_status == 200
    assert detail_payload["model_pack"]["pack_id"] == "deepseek"
    assert detail_payload["model_pack"]["pack_version"] == "1.0.0"
    assert detail_payload["model_pack"]["metadata"]["seed"] == "tier2"
    assert detail_payload["model_pack"]["briefing_strategy"] == "balanced"
    assert detail_payload["model_pack"]["briefing_max_tokens"] == 192

    reserved_create_status, reserved_create_payload = invoke_request(
        "POST",
        "/v1/model-packs",
        payload={
            "pack_id": "llama",
            "pack_version": "1.0.0",
            "display_name": "Conflicting Reserved Pack",
            "family": "custom",
            "description": "Should be rejected.",
            "contract": {
                "contract_version": "model_pack_contract_v1",
                "context": {},
                "tools": {"mode": "none"},
                "response": {},
                "compatibility": {
                    "provider_keys": ["openai_compatible"],
                    "runtime_providers": ["openai_responses"],
                },
            },
            "metadata": {},
        },
        headers=auth_header(session_token),
    )
    assert reserved_create_status == 409
    assert "reserved for built-in catalog entries" in reserved_create_payload["detail"]

    create_pack_status, create_pack_payload = invoke_request(
        "POST",
        "/v1/model-packs",
        payload={
            "pack_id": "custom-brief",
            "pack_version": "1.0.0",
            "display_name": "Custom Brief",
            "family": "custom",
            "description": "Custom operational brief style.",
            "briefing_strategy": "compact",
            "briefing_max_tokens": 160,
            "contract": {
                "contract_version": "model_pack_contract_v1",
                "context": {
                    "max_sessions_cap": 3,
                    "max_events_cap": 8,
                    "max_memories_cap": 5,
                    "max_entities_cap": 5,
                    "max_entity_edges_cap": 10,
                },
                "tools": {"mode": "none"},
                "response": {
                    "system_instruction_append": "Keep responses concise and grounded.",
                    "developer_instruction_append": "Prioritize explicit next actions.",
                },
                "compatibility": {
                    "provider_keys": ["openai_compatible", "ollama", "llamacpp", "vllm"],
                    "runtime_providers": ["openai_responses"],
                    "notes": "Custom workspace brief style.",
                },
            },
            "metadata": {"owner": "ops"},
        },
        headers=auth_header(session_token),
    )
    assert create_pack_status == 201
    assert create_pack_payload["model_pack"]["pack_id"] == "custom-brief"
    assert create_pack_payload["model_pack"]["briefing_strategy"] == "compact"
    assert create_pack_payload["model_pack"]["briefing_max_tokens"] == 160

    bind_status, bind_payload = invoke_request(
        "POST",
        "/v1/model-packs/gpt-oss/bind",
        payload={"pack_version": "1.0.0", "metadata": {"reason": "workspace-default"}},
        headers=auth_header(session_token),
    )
    assert bind_status == 200
    assert bind_payload["binding"]["model_pack"]["pack_id"] == "gpt-oss"
    assert bind_payload["binding"]["binding_source"] == "manual"

    binding_status, binding_payload = invoke_request(
        "GET",
        f"/v1/workspaces/{workspace_id}/model-pack-binding",
        headers=auth_header(session_token),
    )
    assert binding_status == 200
    assert binding_payload["binding"]["model_pack"]["pack_id"] == "gpt-oss"

    thread_id = _seed_thread_for_user(
        admin_db_url=migrated_database_urls["admin"],
        user_id=user_account_id,
        email="model-pack-a@example.com",
    )

    captured_model_requests: list[dict[str, Any]] = []

    def fake_urlopen(request, timeout):
        del timeout
        payload = json.loads(request.data.decode("utf-8"))
        captured_model_requests.append(payload)
        return FakeHTTPResponse(
            json.dumps(
                {
                    "id": f"resp_{len(captured_model_requests)}",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "Pack runtime response"}],
                        }
                    ],
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 4,
                        "total_tokens": 16,
                    },
                }
            ).encode("utf-8")
        )

    monkeypatch.setattr("alicebot_api.response_generation.urlopen", fake_urlopen)

    runtime_status, runtime_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "Summarize current status.",
            "max_sessions": 10,
            "max_events": 40,
            "max_memories": 50,
            "max_entities": 50,
            "max_entity_edges": 100,
        },
        headers=auth_header(session_token),
    )
    assert runtime_status == 200
    assert runtime_payload["metadata"]["model_pack"] == {
        "pack_id": "gpt-oss",
        "pack_version": "1.0.0",
        "source": "workspace_binding",
    }

    first_request = captured_model_requests[0]
    first_context = _extract_context_payload(first_request)
    assert first_context["limits"]["max_memories"] == 6
    assert first_context["limits"]["max_entities"] == 6
    assert first_context["limits"]["max_entity_edges"] == 12
    assert (
        "Use precise language, preserve continuity facts"
        in first_request["input"][0]["content"][0]["text"]
    )
    assert (
        "When uncertain, state the uncertainty"
        in first_request["input"][1]["content"][0]["text"]
    )

    runtime_override_status, runtime_override_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "Summarize current status with request override.",
            "pack_id": "qwen",
            "pack_version": "1.0.0",
            "max_sessions": 10,
            "max_events": 40,
            "max_memories": 50,
            "max_entities": 50,
            "max_entity_edges": 100,
        },
        headers=auth_header(session_token),
    )
    assert runtime_override_status == 200
    assert runtime_override_payload["metadata"]["model_pack"] == {
        "pack_id": "qwen",
        "pack_version": "1.0.0",
        "source": "request",
    }

    second_request = captured_model_requests[1]
    second_context = _extract_context_payload(second_request)
    assert second_context["limits"]["max_memories"] == 4
    assert second_context["limits"]["max_entity_edges"] == 8
    assert "Keep outputs directly actionable and compact." in second_request["input"][1]["content"][0]["text"]

    tier2_override_status, tier2_override_payload = invoke_request(
        "POST",
        "/v1/runtime/invoke",
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": "Summarize current status with tier-2 override.",
            "pack_id": "deepseek",
            "pack_version": "1.0.0",
            "max_sessions": 10,
            "max_events": 40,
            "max_memories": 50,
            "max_entities": 50,
            "max_entity_edges": 100,
        },
        headers=auth_header(session_token),
    )
    assert tier2_override_status == 200
    assert tier2_override_payload["metadata"]["model_pack"] == {
        "pack_id": "deepseek",
        "pack_version": "1.0.0",
        "source": "request",
    }

    third_request = captured_model_requests[2]
    third_context = _extract_context_payload(third_request)
    assert third_context["limits"]["max_memories"] == 6
    assert third_context["limits"]["max_entities"] == 6
    assert third_context["limits"]["max_entity_edges"] == 12
    assert (
        "Keep recommendations concrete and avoid speculative branching."
        in third_request["input"][1]["content"][0]["text"]
    )


def test_phase11_workspace_model_pack_binding_is_workspace_isolated(migrated_database_urls, monkeypatch) -> None:
    _configure_settings(migrated_database_urls, monkeypatch)
    session_token_a, workspace_id_a, _ = _bootstrap_workspace_session("model-pack-iso-a@example.com")
    session_token_b, _, _ = _bootstrap_workspace_session("model-pack-iso-b@example.com")

    bind_status, _ = invoke_request(
        "POST",
        "/v1/model-packs/llama/bind",
        payload={"pack_version": "1.0.0"},
        headers=auth_header(session_token_a),
    )
    assert bind_status == 200

    cross_workspace_status, cross_workspace_payload = invoke_request(
        "GET",
        f"/v1/workspaces/{workspace_id_a}/model-pack-binding",
        headers=auth_header(session_token_b),
    )
    assert cross_workspace_status == 404
    assert "was not found" in cross_workspace_payload["detail"]

    valid_workspace_status, valid_workspace_payload = invoke_request(
        "GET",
        f"/v1/workspaces/{workspace_id_a}/model-pack-binding",
        headers=auth_header(session_token_a),
    )
    assert valid_workspace_status == 200
    assert valid_workspace_payload["binding"]["model_pack"]["pack_id"] == "llama"
    assert UUID(valid_workspace_payload["binding"]["id"])
