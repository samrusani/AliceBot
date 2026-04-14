from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


def invoke_request(
    method: str,
    path: str,
    *,
    query_params: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, object]] = []
    request_received = False

    async def receive() -> dict[str, object]:
        nonlocal request_received
        if request_received:
            return {"type": "http.disconnect"}
        request_received = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    query_string = urlencode(query_params or {}).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": [(b"content-type", b"application/json")],
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


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def test_public_eval_api_runs_lists_and_reads_persisted_report(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="public-evals@example.com")

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    suites_status, suites_payload = invoke_request(
        "GET",
        "/v1/evals/suites",
        query_params={"user_id": str(user_id)},
    )
    assert suites_status == 200
    assert suites_payload["summary"]["suite_count"] == 5
    assert suites_payload["summary"]["case_count"] == 12

    run_status, run_payload = invoke_request(
        "POST",
        "/v1/evals/runs",
        query_params={"user_id": str(user_id)},
    )
    assert run_status == 200
    assert run_payload["run"]["status"] == "pass"
    assert run_payload["report"]["summary"]["suite_count"] == 5
    assert run_payload["report"]["summary"]["case_count"] == 12
    eval_run_id = run_payload["run"]["id"]

    runs_status, runs_payload = invoke_request(
        "GET",
        "/v1/evals/runs",
        query_params={"user_id": str(user_id), "limit": "10"},
    )
    assert runs_status == 200
    assert runs_payload["summary"]["returned_count"] == 1
    assert runs_payload["items"][0]["id"] == eval_run_id

    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v1/evals/runs/{eval_run_id}",
        query_params={"user_id": str(user_id)},
    )
    assert detail_status == 200
    assert detail_payload["run"]["report_digest"] == run_payload["run"]["report_digest"]
    assert detail_payload["report"] == run_payload["report"]
    assert len(detail_payload["results"]) == 12


def test_public_eval_api_rejects_unknown_suite_key(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="public-evals-invalid-suite@example.com")

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    status, payload = invoke_request(
        "POST",
        "/v1/evals/runs",
        query_params={"user_id": str(user_id), "suite_key": "missing_suite"},
    )

    assert status == 400
    assert payload["detail"] == "unknown suite_key values: missing_suite"
