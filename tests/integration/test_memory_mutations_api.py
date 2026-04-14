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
    payload: dict[str, Any] | None = None,
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


def test_memory_mutation_api_generates_commits_and_replays_idempotently(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="mutations@example.com")
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        capture = store.create_continuity_capture_event(
            raw_content="Decision: Legacy rollout plan",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        legacy = store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type="Decision",
            status="active",
            title="Decision: Legacy rollout plan",
            body={"decision_text": "Legacy rollout plan"},
            provenance={"thread_id": str(thread_id)},
            confidence=0.95,
        )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    generate_status, generate_payload = invoke_request(
        "POST",
        "/v1/memory/operations/candidates/generate",
        payload={
            "user_id": str(user_id),
            "user_content": "Correction: Updated rollout plan",
            "assistant_content": "",
            "mode": "assist",
            "sync_fingerprint": "mutation-api-sync-001",
            "thread_id": str(thread_id),
        },
    )
    assert generate_status == 200
    assert generate_payload["summary"] == {
        "candidate_count": 1,
        "auto_apply_count": 1,
        "review_required_count": 0,
        "noop_count": 0,
        "operation_types": ["SUPERSEDE"],
    }
    candidate_id = generate_payload["items"][0]["id"]
    assert generate_payload["items"][0]["target_continuity_object_id"] == str(legacy["id"])

    commit_status, commit_payload = invoke_request(
        "POST",
        "/v1/memory/operations/commit",
        payload={
            "user_id": str(user_id),
            "candidate_ids": [candidate_id],
        },
    )
    assert commit_status == 200
    assert commit_payload["summary"]["applied_count"] == 1
    assert commit_payload["summary"]["operation_types"] == ["SUPERSEDE"]
    assert commit_payload["operations"][0]["operation_type"] == "SUPERSEDE"
    assert commit_payload["operations"][0]["correction_event_id"] is not None
    replacement_id = commit_payload["operations"][0]["resulting_continuity_object_id"]
    assert replacement_id is not None

    operations_status, operations_payload = invoke_request(
        "GET",
        "/v1/memory/operations",
        query_params={
            "user_id": str(user_id),
            "sync_fingerprint": "mutation-api-sync-001",
            "limit": "20",
        },
    )
    assert operations_status == 200
    assert operations_payload["summary"]["returned_count"] == 1
    assert operations_payload["items"][0]["resulting_continuity_object_id"] == replacement_id

    second_generate_status, second_generate_payload = invoke_request(
        "POST",
        "/v1/memory/operations/candidates/generate",
        payload={
            "user_id": str(user_id),
            "user_content": "Correction: Updated rollout plan",
            "assistant_content": "",
            "mode": "assist",
            "sync_fingerprint": "mutation-api-sync-001",
            "thread_id": str(thread_id),
        },
    )
    assert second_generate_status == 200
    assert second_generate_payload["items"][0]["id"] == candidate_id

    second_commit_status, second_commit_payload = invoke_request(
        "POST",
        "/v1/memory/operations/commit",
        payload={
            "user_id": str(user_id),
            "candidate_ids": [candidate_id],
        },
    )
    assert second_commit_status == 200
    assert second_commit_payload["summary"]["duplicate_count"] == 1
    assert second_commit_payload["summary"]["applied_count"] == 0

    recall_status, recall_payload = invoke_request(
        "GET",
        "/v0/continuity/recall",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "limit": "20",
        },
    )
    assert recall_status == 200
    assert recall_payload["items"][0]["id"] == replacement_id
    assert {item["status"] for item in recall_payload["items"]} == {"active", "superseded"}


def test_memory_mutation_add_commit_preserves_scope_for_recall(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="mutations-add@example.com")
    thread_id = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    generate_status, generate_payload = invoke_request(
        "POST",
        "/v1/memory/operations/candidates/generate",
        payload={
            "user_id": str(user_id),
            "user_content": "Decision: Finalize beta launch checklist",
            "assistant_content": "",
            "mode": "assist",
            "sync_fingerprint": "mutation-api-sync-add-001",
            "thread_id": str(thread_id),
            "project": "apollo",
            "person": "alex",
        },
    )
    assert generate_status == 200
    assert generate_payload["summary"]["operation_types"] == ["ADD"]
    candidate_id = generate_payload["items"][0]["id"]

    commit_status, commit_payload = invoke_request(
        "POST",
        "/v1/memory/operations/commit",
        payload={
            "user_id": str(user_id),
            "candidate_ids": [candidate_id],
        },
    )
    assert commit_status == 200
    assert commit_payload["summary"]["applied_count"] == 1
    resulting_id = commit_payload["operations"][0]["resulting_continuity_object_id"]
    assert resulting_id is not None

    recall_status, recall_payload = invoke_request(
        "GET",
        "/v0/continuity/recall",
        query_params={
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "project": "apollo",
            "person": "alex",
            "limit": "20",
        },
    )
    assert recall_status == 200
    assert [item["id"] for item in recall_payload["items"]] == [resulting_id]

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        stored = ContinuityStore(conn).get_continuity_object_optional(UUID(resulting_id))
    assert stored is not None
    assert stored["provenance"]["thread_id"] == str(thread_id)
    assert stored["provenance"]["project"] == "apollo"
    assert stored["provenance"]["person"] == "alex"


def test_memory_mutation_api_rejects_unknown_mode(
    migrated_database_urls,
    monkeypatch,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="mutations-invalid-mode@example.com")

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(database_url=migrated_database_urls["app"]),
    )

    status, payload = invoke_request(
        "POST",
        "/v1/memory/operations/candidates/generate",
        payload={
            "user_id": str(user_id),
            "user_content": "Decision: Reject invalid mode input",
            "assistant_content": "",
            "mode": "banana",
        },
    )

    assert status == 400
    assert payload == {"detail": "mode must be one of: manual, assist, auto"}
