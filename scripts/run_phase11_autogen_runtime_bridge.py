#!/usr/bin/env python3
"""AutoGen-style bridge to Alice's provider runtime invoke endpoint.

This script demonstrates a minimal model-client shape that external frameworks
can call while Alice remains the continuity and provider runtime surface.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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
    timeout_seconds: int = 30,
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
        with urlopen(request, timeout=timeout_seconds) as response:
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


def _latest_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        role = message.get("role", "").strip().lower()
        content = message.get("content", "").strip()
        if role == "user" and content != "":
            return content
    raise ValueError("messages must include at least one non-empty user message")


@dataclass(frozen=True, slots=True)
class AutoGenAliceRuntimeClient:
    api_base_url: str
    user_id: str
    provider_id: str
    thread_id: str
    model: str | None = None
    timeout_seconds: int = 30

    def create(self, *, messages: list[dict[str, str]]) -> dict[str, Any]:
        user_message = _latest_user_message(messages)
        payload: dict[str, Any] = {
            "provider_id": self.provider_id,
            "thread_id": self.thread_id,
            "message": user_message,
        }
        if self.model is not None and self.model.strip() != "":
            payload["model"] = self.model.strip()

        runtime_response = _request_json(
            method="POST",
            url=f"{self.api_base_url.rstrip('/')}/v1/runtime/invoke",
            user_id=self.user_id,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            idempotency_key=f"autogen-runtime-{uuid4()}",
        )
        assistant = runtime_response.get("assistant")
        if not isinstance(assistant, dict):
            raise RuntimeError("runtime invoke response missing assistant payload")
        text = assistant.get("text")
        if not isinstance(text, str) or text.strip() == "":
            raise RuntimeError("runtime invoke response missing assistant text")
        return {
            "content": text,
            "assistant": assistant,
            "trace": runtime_response.get("trace"),
            "metadata": runtime_response.get("metadata"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="run_phase11_autogen_runtime_bridge.py",
        description=(
            "Send an AutoGen-style message list through Alice /v1/runtime/invoke "
            "using a configured provider."
        ),
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
    parser.add_argument("--provider-id", required=True, help="Registered provider ID.")
    parser.add_argument("--thread-id", required=True, help="Thread ID used for runtime invoke continuity.")
    parser.add_argument("--user-message", required=True, help="Latest user message content.")
    parser.add_argument("--model", default=None, help="Optional runtime model override.")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="Request timeout in seconds.")
    parser.add_argument(
        "--show-raw",
        action="store_true",
        help="Print full runtime payload instead of content-only shape.",
    )
    args = parser.parse_args()
    if args.user_id.strip() == "":
        parser.error("--user-id or ALICEBOT_AUTH_USER_ID is required")

    client = AutoGenAliceRuntimeClient(
        api_base_url=args.api_base_url,
        user_id=args.user_id.strip(),
        provider_id=args.provider_id,
        thread_id=args.thread_id,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
    )
    result = client.create(messages=[{"role": "user", "content": args.user_message}])
    if args.show_raw:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps({"content": result["content"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
