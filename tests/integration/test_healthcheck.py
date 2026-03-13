from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib import error, request

import anyio

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings


REPO_ROOT = Path(__file__).resolve().parents[2]


def invoke_healthcheck() -> tuple[int, dict[str, object]]:
    messages: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/healthz",
        "raw_path": b"/healthz",
        "query_string": b"",
        "headers": [],
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


def test_healthcheck_endpoint_returns_ok_response(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://db",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
        healthcheck_timeout_seconds=2,
    )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: True)

    status_code, payload = invoke_healthcheck()

    assert status_code == 200
    assert payload["status"] == "ok"
    assert payload["services"]["database"]["status"] == "ok"
    assert payload["services"]["redis"]["status"] == "not_checked"
    assert payload["services"]["redis"]["url"] == "redis://cache:6379/0"
    assert payload["services"]["object_storage"]["status"] == "not_checked"


def test_healthcheck_endpoint_returns_degraded_response(monkeypatch) -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://db",
        redis_url="redis://alicebot:supersecret@cache:6379/0",
        s3_endpoint_url="http://object-store",
        healthcheck_timeout_seconds=2,
    )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "ping_database", lambda *_args, **_kwargs: False)

    status_code, payload = invoke_healthcheck()

    assert status_code == 503
    assert payload["status"] == "degraded"
    assert payload["services"]["database"]["status"] == "unreachable"
    assert payload["services"]["redis"]["status"] == "not_checked"
    assert payload["services"]["redis"]["url"] == "redis://cache:6379/0"
    assert payload["services"]["object_storage"]["status"] == "not_checked"


def test_api_dev_script_serves_live_healthcheck() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    env = os.environ.copy()
    env.update(
        {
        "APP_HOST": "127.0.0.1",
        "APP_PORT": str(port),
        "APP_RELOAD": "false",
        "APP_ENV": "test",
        "DATABASE_URL": "postgresql://invalid:invalid@127.0.0.1:1/invalid",
        "REDIS_URL": "redis://alicebot:supersecret@localhost:6379/0",
        "HEALTHCHECK_TIMEOUT_SECONDS": "1",
        }
    )

    process = subprocess.Popen(
        ["/bin/bash", str(REPO_ROOT / "scripts" / "api_dev.sh")],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    payload: dict[str, object] | None = None
    status_code: int | None = None

    try:
        deadline = time.time() + 15
        url = f"http://127.0.0.1:{port}/healthz"

        while time.time() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                raise AssertionError(
                    "api_dev.sh exited before serving /healthz\n"
                    f"stdout:\n{stdout}\n"
                    f"stderr:\n{stderr}"
                )

            try:
                with request.urlopen(url, timeout=0.5) as response:
                    status_code = response.status
                    payload = json.loads(response.read())
                    break
            except error.HTTPError as exc:
                status_code = exc.code
                payload = json.loads(exc.read())
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError("Timed out waiting for api_dev.sh to serve /healthz")
    finally:
        process.terminate()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)

    assert status_code == 503
    assert payload == {
        "status": "degraded",
        "environment": "test",
        "services": {
            "database": {"status": "unreachable"},
            "redis": {"status": "not_checked", "url": "redis://localhost:6379/0"},
            "object_storage": {
                "status": "not_checked",
                "endpoint_url": "http://localhost:9000",
            },
        },
    }
