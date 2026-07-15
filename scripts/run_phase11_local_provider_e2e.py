#!/usr/bin/env python3
"""Run a local-provider e2e flow for P11-S2.

Flow:
1) Bootstrap the deterministic local workspace
2) Register local or self-hosted provider (Ollama, llama.cpp, or vLLM)
3) Run provider test
4) Run runtime invoke
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def _request_json(
    *,
    method: str,
    url: str,
    user_id: str,
    payload: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "X-AliceBot-User-Id": user_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(
        url=url,
        method=method,
        data=body,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw_payload = response.read()
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc

    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{method} {url} returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{method} {url} returned invalid payload shape")
    return parsed


def _provider_defaults(provider: str) -> tuple[str, str]:
    if provider == "ollama":
        return ("http://127.0.0.1:11434", "/v1/providers/ollama/register")
    if provider == "llamacpp":
        return ("http://127.0.0.1:8080", "/v1/providers/llamacpp/register")
    return ("http://127.0.0.1:8001", "/v1/providers/vllm/register")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="run_phase11_local_provider_e2e.py",
        description="Register and invoke a local or self-hosted provider through the runtime paths.",
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Alice API base URL (default: http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("ALICEBOT_AUTH_USER_ID", ""),
        help="Local Alice operator UUID (defaults to ALICEBOT_AUTH_USER_ID).",
    )
    parser.add_argument(
        "--thread-id",
        required=True,
        help="Thread ID to use for /v1/runtime/invoke.",
    )
    parser.add_argument(
        "--provider",
        choices=("ollama", "llamacpp", "vllm"),
        required=True,
        help="Provider adapter to exercise.",
    )
    parser.add_argument(
        "--display-name",
        default="Local Provider E2E",
        help="Provider display name.",
    )
    parser.add_argument(
        "--provider-base-url",
        default=None,
        help="Local provider base URL. Defaults to adapter standard local URL.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model name to register/test/invoke.",
    )
    parser.add_argument(
        "--test-prompt",
        default="Reply with one sentence confirming connectivity.",
        help="Prompt used for /v1/providers/test.",
    )
    parser.add_argument(
        "--message",
        default="Give a concise runtime confirmation.",
        help="Message used for /v1/runtime/invoke.",
    )
    args = parser.parse_args()
    user_id = args.user_id.strip()
    if user_id == "":
        parser.error("--user-id or ALICEBOT_AUTH_USER_ID is required")

    default_provider_base_url, register_path = _provider_defaults(args.provider)
    provider_base_url = (args.provider_base_url or default_provider_base_url).strip()
    api_base_url = args.api_base_url.rstrip("/")

    _request_json(
        method="POST",
        url=f"{api_base_url}/v1/workspaces/bootstrap",
        user_id=user_id,
        payload={},
    )

    register_payload = {
        "display_name": args.display_name,
        "base_url": provider_base_url,
        "default_model": args.model,
        "metadata": {"source": "local_self_hosted_e2e"},
    }
    register_response = _request_json(
        method="POST",
        url=f"{api_base_url}{register_path}",
        user_id=user_id,
        payload=register_payload,
    )
    provider_id = register_response["provider"]["id"]

    test_response = _request_json(
        method="POST",
        url=f"{api_base_url}/v1/providers/test",
        user_id=user_id,
        payload={
            "provider_id": provider_id,
            "model": args.model,
            "prompt": args.test_prompt,
        },
    )

    invoke_response = _request_json(
        method="POST",
        url=f"{api_base_url}/v1/runtime/invoke",
        user_id=user_id,
        idempotency_key=f"local-provider-e2e-{uuid4()}",
        payload={
            "provider_id": provider_id,
            "thread_id": args.thread_id,
            "message": args.message,
            "model": args.model,
        },
    )

    result = {
        "provider": register_response["provider"],
        "capabilities": register_response["capabilities"],
        "test_result": test_response["result"],
        "runtime_assistant": invoke_response["assistant"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
