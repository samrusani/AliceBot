#!/usr/bin/env python3
"""Run an OpenAI-compatible provider smoke flow for P14-S1.

Flow:
1) Register an OpenAI-compatible provider through `/v1/providers`
2) Run `/v1/providers/test`
3) Run `/v1/runtime/invoke`

If `--provider-base-url` is omitted, the script starts a temporary local
OpenAI-compatible stub endpoint for the smoke run.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading


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


class _StubHandler(BaseHTTPRequestHandler):
    model_name = "gpt-5-mini"

    def _write_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/v1/models":
            self._write_json(404, {"error": {"message": "not found"}})
            return
        self._write_json(200, {"data": [{"id": self.model_name}]})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/responses":
            self._write_json(404, {"error": {"message": "not found"}})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json(400, {"error": {"message": "invalid json"}})
            return

        model_name = payload.get("model")
        if not isinstance(model_name, str) or model_name.strip() == "":
            self._write_json(400, {"error": {"message": "model is required"}})
            return

        self._write_json(
            200,
            {
                "id": "resp_phase14_smoke",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "OpenAI-compatible smoke OK"}],
                    }
                ],
                "usage": {
                    "input_tokens": 12,
                    "output_tokens": 4,
                    "total_tokens": 16,
                },
            },
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        del format, args


@contextmanager
def _temporary_stub_server(*, model_name: str) -> Iterator[str]:
    handler = type(
        "OpenAICompatibleSmokeHandler",
        (_StubHandler,),
        {"model_name": model_name},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/v1"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _run_flow(
    *,
    api_base_url: str,
    session_token: str,
    thread_id: str,
    provider_base_url: str,
    display_name: str,
    model: str,
    test_prompt: str,
    message: str,
) -> dict[str, object]:
    register_response = _request_json(
        method="POST",
        url=f"{api_base_url.rstrip('/')}/v1/providers",
        bearer_token=session_token,
        payload={
            "provider_key": "openai_compatible",
            "display_name": display_name,
            "base_url": provider_base_url,
            "api_key": "phase14-smoke-key",
            "default_model": model,
            "metadata": {"source": "phase14_openai_compatible_smoke"},
        },
    )
    provider_id = register_response["provider"]["id"]

    test_response = _request_json(
        method="POST",
        url=f"{api_base_url.rstrip('/')}/v1/providers/test",
        bearer_token=session_token,
        payload={
            "provider_id": provider_id,
            "model": model,
            "prompt": test_prompt,
        },
    )

    invoke_response = _request_json(
        method="POST",
        url=f"{api_base_url.rstrip('/')}/v1/runtime/invoke",
        bearer_token=session_token,
        payload={
            "provider_id": provider_id,
            "thread_id": thread_id,
            "message": message,
            "model": model,
        },
    )

    return {
        "provider": register_response["provider"],
        "capabilities": register_response["capabilities"],
        "test_result": test_response["result"],
        "runtime_assistant": invoke_response["assistant"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="run_phase14_openai_compatible_smoke.py",
        description="Register and invoke an OpenAI-compatible provider through the P14-S1 runtime paths.",
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
        "--provider-base-url",
        default=None,
        help="OpenAI-compatible provider base URL. If omitted, a local compliant stub is started.",
    )
    parser.add_argument(
        "--display-name",
        default="OpenAI-Compatible Smoke",
        help="Provider display name.",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="Model name to register/test/invoke.",
    )
    parser.add_argument(
        "--test-prompt",
        default="Reply with one sentence confirming OpenAI-compatible connectivity.",
        help="Prompt used for /v1/providers/test.",
    )
    parser.add_argument(
        "--message",
        default="Give a concise runtime confirmation.",
        help="Message used for /v1/runtime/invoke.",
    )
    args = parser.parse_args()

    if args.provider_base_url is not None:
        result = _run_flow(
            api_base_url=args.api_base_url,
            session_token=args.session_token,
            thread_id=args.thread_id,
            provider_base_url=args.provider_base_url.strip(),
            display_name=args.display_name,
            model=args.model,
            test_prompt=args.test_prompt,
            message=args.message,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    with _temporary_stub_server(model_name=args.model) as stub_provider_base_url:
        result = _run_flow(
            api_base_url=args.api_base_url,
            session_token=args.session_token,
            thread_id=args.thread_id,
            provider_base_url=stub_provider_base_url,
            display_name=args.display_name,
            model=args.model,
            test_prompt=args.test_prompt,
            message=args.message,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
