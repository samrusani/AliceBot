#!/usr/bin/env python3
"""Run a vLLM self-hosted e2e flow for P11-S3.

Flow:
1) Register vLLM provider
2) Run provider test
3) Run runtime invoke
4) Fetch provider telemetry
"""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _request_json(
    *,
    method: str,
    url: str,
    bearer_token: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url=url,
        method=method,
        data=body,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
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


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="run_phase11_vllm_e2e.py",
        description="Register and invoke a self-hosted vLLM provider through the P11-S3 runtime paths.",
    )
    parser.add_argument(
        "--api-base-url",
        default="http://127.0.0.1:8000",
        help="Alice API base URL (default: http://127.0.0.1:8000).",
    )
    parser.add_argument(
        "--session-token",
        required=True,
        help="Hosted session bearer token.",
    )
    parser.add_argument(
        "--thread-id",
        required=True,
        help="Thread ID to use for /v1/runtime/invoke.",
    )
    parser.add_argument(
        "--display-name",
        default="vLLM Self-Hosted E2E",
        help="Provider display name.",
    )
    parser.add_argument(
        "--provider-base-url",
        default="http://127.0.0.1:8001",
        help="vLLM base URL for OpenAI-compatible endpoints (default: http://127.0.0.1:8001).",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model name to register/test/invoke.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional vLLM passthrough: temperature.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=None,
        help="Optional vLLM passthrough: top_p.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Optional vLLM passthrough: max_tokens.",
    )
    parser.add_argument(
        "--stop",
        action="append",
        default=None,
        help="Optional vLLM passthrough: stop sequence (repeat flag for multiple values).",
    )
    parser.add_argument(
        "--test-prompt",
        default="Reply with one sentence confirming vLLM connectivity.",
        help="Prompt used for /v1/providers/test.",
    )
    parser.add_argument(
        "--message",
        default="Give a concise vLLM runtime confirmation.",
        help="Message used for /v1/runtime/invoke.",
    )
    args = parser.parse_args()

    invoke_passthrough: dict[str, object] = {}
    if args.temperature is not None:
        invoke_passthrough["temperature"] = args.temperature
    if args.top_p is not None:
        invoke_passthrough["top_p"] = args.top_p
    if args.max_tokens is not None:
        invoke_passthrough["max_tokens"] = args.max_tokens
    if args.stop:
        invoke_passthrough["stop"] = args.stop

    register_payload: dict[str, object] = {
        "display_name": args.display_name,
        "base_url": args.provider_base_url.strip(),
        "default_model": args.model,
        "metadata": {"source": "phase11_vllm_e2e"},
    }
    if len(invoke_passthrough) > 0:
        register_payload["adapter_options"] = {"invoke_passthrough": invoke_passthrough}

    register_response = _request_json(
        method="POST",
        url=f"{args.api_base_url.rstrip('/')}/v1/providers/vllm/register",
        bearer_token=args.session_token,
        payload=register_payload,
    )
    provider_id = register_response["provider"]["id"]

    test_response = _request_json(
        method="POST",
        url=f"{args.api_base_url.rstrip('/')}/v1/providers/test",
        bearer_token=args.session_token,
        payload={
            "provider_id": provider_id,
            "model": args.model,
            "prompt": args.test_prompt,
        },
    )

    invoke_response = _request_json(
        method="POST",
        url=f"{args.api_base_url.rstrip('/')}/v1/runtime/invoke",
        bearer_token=args.session_token,
        payload={
            "provider_id": provider_id,
            "thread_id": args.thread_id,
            "message": args.message,
            "model": args.model,
        },
    )

    telemetry_url = (
        f"{args.api_base_url.rstrip('/')}/v1/providers/{provider_id}/telemetry?"
        + urlencode({"limit": 10})
    )
    telemetry_response = _request_json(
        method="GET",
        url=telemetry_url,
        bearer_token=args.session_token,
    )

    result = {
        "provider": register_response["provider"],
        "capabilities": register_response["capabilities"],
        "test_result": test_response["result"],
        "runtime_assistant": invoke_response["assistant"],
        "telemetry": telemetry_response,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
