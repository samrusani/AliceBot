from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import anyio
import psycopg

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


def seed_task(database_url: str, *, email: str) -> dict[str, UUID]:
    user_id = uuid4()

    with user_connection(database_url, user_id) as conn:
        store = ContinuityStore(conn)
        store.create_user(user_id, email, email.split("@", 1)[0].title())
        thread = store.create_thread("Artifact thread")
        tool = store.create_tool(
            tool_key="proxy.echo",
            name="Proxy Echo",
            description="Deterministic proxy handler.",
            version="1.0.0",
            metadata_version="tool_metadata_v0",
            active=True,
            tags=["proxy"],
            action_hints=["tool.run"],
            scope_hints=["workspace"],
            domain_hints=[],
            risk_hints=[],
            metadata={"transport": "proxy"},
        )
        task = store.create_task(
            thread_id=thread["id"],
            tool_id=tool["id"],
            status="approved",
            request={
                "thread_id": str(thread["id"]),
                "tool_id": str(tool["id"]),
                "action": "tool.run",
                "scope": "workspace",
                "domain_hint": None,
                "risk_hint": None,
                "attributes": {},
            },
            tool={
                "id": str(tool["id"]),
                "tool_key": "proxy.echo",
                "name": "Proxy Echo",
                "description": "Deterministic proxy handler.",
                "version": "1.0.0",
                "metadata_version": "tool_metadata_v0",
                "active": True,
                "tags": ["proxy"],
                "action_hints": ["tool.run"],
                "scope_hints": ["workspace"],
                "domain_hints": [],
                "risk_hints": [],
                "metadata": {"transport": "proxy"},
                "created_at": tool["created_at"].isoformat(),
            },
            latest_approval_id=None,
            latest_execution_id=None,
        )

    return {
        "user_id": user_id,
        "task_id": task["id"],
    }


def test_task_artifact_endpoints_register_list_detail_isolate_and_reject_duplicates(
    migrated_database_urls,
    monkeypatch,
    tmp_path,
) -> None:
    owner = seed_task(migrated_database_urls["app"], email="owner@example.com")
    intruder = seed_task(migrated_database_urls["app"], email="intruder@example.com")
    workspace_root = tmp_path / "task-workspaces"
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            task_workspace_root=str(workspace_root),
        ),
    )

    workspace_status, workspace_payload = invoke_request(
        "POST",
        f"/v0/tasks/{owner['task_id']}/workspace",
        payload={"user_id": str(owner["user_id"])},
    )
    assert workspace_status == 201

    workspace_path = Path(workspace_payload["workspace"]["local_path"])
    first_file = workspace_path / "docs" / "spec.txt"
    first_file.parent.mkdir(parents=True)
    first_file.write_text("spec")
    second_file = workspace_path / "notes" / "plan.md"
    second_file.parent.mkdir(parents=True)
    second_file.write_text("plan")
    outside_file = tmp_path / "escape.txt"
    outside_file.write_text("escape")

    first_create_status, first_create_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(first_file),
            "media_type_hint": "text/plain",
        },
    )
    second_create_status, second_create_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(second_file),
            "media_type_hint": "text/markdown",
        },
    )
    list_status, list_payload = invoke_request(
        "GET",
        "/v0/task-artifacts",
        query_params={"user_id": str(owner["user_id"])},
    )
    detail_status, detail_payload = invoke_request(
        "GET",
        f"/v0/task-artifacts/{first_create_payload['artifact']['id']}",
        query_params={"user_id": str(owner["user_id"])},
    )
    duplicate_status, duplicate_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(first_file),
            "media_type_hint": "text/plain",
        },
    )
    escaped_status, escaped_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(outside_file),
        },
    )
    isolated_list_status, isolated_list_payload = invoke_request(
        "GET",
        "/v0/task-artifacts",
        query_params={"user_id": str(intruder["user_id"])},
    )
    isolated_detail_status, isolated_detail_payload = invoke_request(
        "GET",
        f"/v0/task-artifacts/{first_create_payload['artifact']['id']}",
        query_params={"user_id": str(intruder["user_id"])},
    )
    isolated_create_status, isolated_create_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(intruder["user_id"]),
            "local_path": str(first_file),
        },
    )

    assert first_create_status == 201
    assert first_create_payload == {
        "artifact": {
            "id": first_create_payload["artifact"]["id"],
            "task_id": str(owner["task_id"]),
            "task_workspace_id": workspace_payload["workspace"]["id"],
            "status": "registered",
            "ingestion_status": "pending",
            "relative_path": "docs/spec.txt",
            "media_type_hint": "text/plain",
            "created_at": first_create_payload["artifact"]["created_at"],
            "updated_at": first_create_payload["artifact"]["updated_at"],
        }
    }

    assert second_create_status == 201
    assert second_create_payload == {
        "artifact": {
            "id": second_create_payload["artifact"]["id"],
            "task_id": str(owner["task_id"]),
            "task_workspace_id": workspace_payload["workspace"]["id"],
            "status": "registered",
            "ingestion_status": "pending",
            "relative_path": "notes/plan.md",
            "media_type_hint": "text/markdown",
            "created_at": second_create_payload["artifact"]["created_at"],
            "updated_at": second_create_payload["artifact"]["updated_at"],
        }
    }

    assert list_status == 200
    assert list_payload == {
        "items": [
            first_create_payload["artifact"],
            second_create_payload["artifact"],
        ],
        "summary": {"total_count": 2, "order": ["created_at_asc", "id_asc"]},
    }

    assert detail_status == 200
    assert detail_payload == {"artifact": first_create_payload["artifact"]}

    assert duplicate_status == 409
    assert duplicate_payload == {
        "detail": (
            "artifact docs/spec.txt is already registered for task workspace "
            f"{workspace_payload['workspace']['id']}"
        )
    }

    assert escaped_status == 400
    assert escaped_payload == {
        "detail": f"artifact path {outside_file.resolve()} escapes workspace root {workspace_path.resolve()}"
    }

    assert isolated_list_status == 200
    assert isolated_list_payload == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
    }

    assert isolated_detail_status == 404
    assert isolated_detail_payload == {
        "detail": f"task artifact {first_create_payload['artifact']['id']} was not found"
    }

    assert isolated_create_status == 404
    assert isolated_create_payload == {
        "detail": f"task workspace {workspace_payload['workspace']['id']} was not found"
    }


def test_task_artifact_ingestion_and_chunk_endpoints_are_deterministic_and_isolated(
    migrated_database_urls,
    monkeypatch,
    tmp_path,
) -> None:
    owner = seed_task(migrated_database_urls["app"], email="owner@example.com")
    intruder = seed_task(migrated_database_urls["app"], email="intruder@example.com")
    workspace_root = tmp_path / "task-workspaces"
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            task_workspace_root=str(workspace_root),
        ),
    )

    workspace_status, workspace_payload = invoke_request(
        "POST",
        f"/v0/tasks/{owner['task_id']}/workspace",
        payload={"user_id": str(owner["user_id"])},
    )
    assert workspace_status == 201

    workspace_path = Path(workspace_payload["workspace"]["local_path"])
    supported_file = workspace_path / "docs" / "spec.txt"
    supported_file.parent.mkdir(parents=True)
    supported_file.write_text(("A" * 998) + "\r\n" + ("B" * 5) + "\rC")
    unsupported_file = workspace_path / "docs" / "manual.pdf"
    unsupported_file.write_text("not really a pdf")

    register_status, register_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(supported_file),
            "media_type_hint": "text/plain",
        },
    )
    assert register_status == 201

    ingest_status, ingest_payload = invoke_request(
        "POST",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/ingest",
        payload={"user_id": str(owner["user_id"])},
    )
    chunk_list_status, chunk_list_payload = invoke_request(
        "GET",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/chunks",
        query_params={"user_id": str(owner["user_id"])},
    )
    isolated_chunk_list_status, isolated_chunk_list_payload = invoke_request(
        "GET",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/chunks",
        query_params={"user_id": str(intruder["user_id"])},
    )
    isolated_ingest_status, isolated_ingest_payload = invoke_request(
        "POST",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/ingest",
        payload={"user_id": str(intruder["user_id"])},
    )

    unsupported_register_status, unsupported_register_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(unsupported_file),
            "media_type_hint": "application/pdf",
        },
    )
    assert unsupported_register_status == 201
    unsupported_ingest_status, unsupported_ingest_payload = invoke_request(
        "POST",
        f"/v0/task-artifacts/{unsupported_register_payload['artifact']['id']}/ingest",
        payload={"user_id": str(owner["user_id"])},
    )

    assert ingest_status == 200
    assert ingest_payload == {
        "artifact": {
            "id": register_payload["artifact"]["id"],
            "task_id": str(owner["task_id"]),
            "task_workspace_id": workspace_payload["workspace"]["id"],
            "status": "registered",
            "ingestion_status": "ingested",
            "relative_path": "docs/spec.txt",
            "media_type_hint": "text/plain",
            "created_at": register_payload["artifact"]["created_at"],
            "updated_at": ingest_payload["artifact"]["updated_at"],
        },
        "summary": {
            "total_count": 2,
            "total_characters": 1006,
            "media_type": "text/plain",
            "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
            "order": ["sequence_no_asc", "id_asc"],
        },
    }

    assert chunk_list_status == 200
    assert chunk_list_payload == {
        "items": [
            {
                "id": chunk_list_payload["items"][0]["id"],
                "task_artifact_id": register_payload["artifact"]["id"],
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 1000,
                "text": ("A" * 998) + "\n" + "B",
                "created_at": chunk_list_payload["items"][0]["created_at"],
                "updated_at": chunk_list_payload["items"][0]["updated_at"],
            },
            {
                "id": chunk_list_payload["items"][1]["id"],
                "task_artifact_id": register_payload["artifact"]["id"],
                "sequence_no": 2,
                "char_start": 1000,
                "char_end_exclusive": 1006,
                "text": "BBBB\nC",
                "created_at": chunk_list_payload["items"][1]["created_at"],
                "updated_at": chunk_list_payload["items"][1]["updated_at"],
            },
        ],
        "summary": {
            "total_count": 2,
            "total_characters": 1006,
            "media_type": "text/plain",
            "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
            "order": ["sequence_no_asc", "id_asc"],
        },
    }

    assert isolated_chunk_list_status == 404
    assert isolated_chunk_list_payload == {
        "detail": f"task artifact {register_payload['artifact']['id']} was not found"
    }

    assert isolated_ingest_status == 404
    assert isolated_ingest_payload == {
        "detail": f"task artifact {register_payload['artifact']['id']} was not found"
    }

    assert unsupported_ingest_status == 400
    assert unsupported_ingest_payload == {
        "detail": (
            "artifact docs/manual.pdf has unsupported media type application/pdf; "
            "supported types: text/plain, text/markdown"
        )
    }


def test_task_artifact_ingestion_supports_markdown_and_reingest_is_idempotent(
    migrated_database_urls,
    monkeypatch,
    tmp_path,
) -> None:
    owner = seed_task(migrated_database_urls["app"], email="owner@example.com")
    workspace_root = tmp_path / "task-workspaces"
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            task_workspace_root=str(workspace_root),
        ),
    )

    workspace_status, workspace_payload = invoke_request(
        "POST",
        f"/v0/tasks/{owner['task_id']}/workspace",
        payload={"user_id": str(owner["user_id"])},
    )
    assert workspace_status == 201

    workspace_path = Path(workspace_payload["workspace"]["local_path"])
    markdown_file = workspace_path / "notes" / "plan.md"
    markdown_file.parent.mkdir(parents=True)
    markdown_file.write_text("# Plan\r\n\r\n- Ship ingestion\n- Keep scope narrow\r")

    register_status, register_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(markdown_file),
            "media_type_hint": "text/markdown",
        },
    )
    assert register_status == 201

    first_ingest_status, first_ingest_payload = invoke_request(
        "POST",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/ingest",
        payload={"user_id": str(owner["user_id"])},
    )
    second_ingest_status, second_ingest_payload = invoke_request(
        "POST",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/ingest",
        payload={"user_id": str(owner["user_id"])},
    )
    chunk_list_status, chunk_list_payload = invoke_request(
        "GET",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/chunks",
        query_params={"user_id": str(owner["user_id"])},
    )

    assert first_ingest_status == 200
    assert first_ingest_payload == {
        "artifact": {
            "id": register_payload["artifact"]["id"],
            "task_id": str(owner["task_id"]),
            "task_workspace_id": workspace_payload["workspace"]["id"],
            "status": "registered",
            "ingestion_status": "ingested",
            "relative_path": "notes/plan.md",
            "media_type_hint": "text/markdown",
            "created_at": register_payload["artifact"]["created_at"],
            "updated_at": first_ingest_payload["artifact"]["updated_at"],
        },
        "summary": {
            "total_count": 1,
            "total_characters": 45,
            "media_type": "text/markdown",
            "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
            "order": ["sequence_no_asc", "id_asc"],
        },
    }
    assert second_ingest_status == 200
    assert second_ingest_payload == first_ingest_payload
    assert chunk_list_status == 200
    assert chunk_list_payload == {
        "items": [
            {
                "id": chunk_list_payload["items"][0]["id"],
                "task_artifact_id": register_payload["artifact"]["id"],
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 45,
                "text": "# Plan\n\n- Ship ingestion\n- Keep scope narrow\n",
                "created_at": chunk_list_payload["items"][0]["created_at"],
                "updated_at": chunk_list_payload["items"][0]["updated_at"],
            }
        ],
        "summary": {
            "total_count": 1,
            "total_characters": 45,
            "media_type": "text/markdown",
            "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
            "order": ["sequence_no_asc", "id_asc"],
        },
    }


def test_task_artifact_ingestion_rejects_invalid_utf8_content(
    migrated_database_urls,
    monkeypatch,
    tmp_path,
) -> None:
    owner = seed_task(migrated_database_urls["app"], email="owner@example.com")
    workspace_root = tmp_path / "task-workspaces"
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            task_workspace_root=str(workspace_root),
        ),
    )

    workspace_status, workspace_payload = invoke_request(
        "POST",
        f"/v0/tasks/{owner['task_id']}/workspace",
        payload={"user_id": str(owner["user_id"])},
    )
    assert workspace_status == 201

    workspace_path = Path(workspace_payload["workspace"]["local_path"])
    broken_file = workspace_path / "docs" / "broken.txt"
    broken_file.parent.mkdir(parents=True)
    broken_file.write_bytes(b"\xff\xfe\xfd")

    register_status, register_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(broken_file),
            "media_type_hint": "text/plain",
        },
    )
    assert register_status == 201

    ingest_status, ingest_payload = invoke_request(
        "POST",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/ingest",
        payload={"user_id": str(owner["user_id"])},
    )

    assert ingest_status == 400
    assert ingest_payload == {
        "detail": "artifact docs/broken.txt is not valid UTF-8 text"
    }


def test_task_artifact_ingestion_enforces_rooted_workspace_paths(
    migrated_database_urls,
    monkeypatch,
    tmp_path,
) -> None:
    owner = seed_task(migrated_database_urls["app"], email="owner@example.com")
    workspace_root = tmp_path / "task-workspaces"
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url=migrated_database_urls["app"],
            task_workspace_root=str(workspace_root),
        ),
    )

    workspace_status, workspace_payload = invoke_request(
        "POST",
        f"/v0/tasks/{owner['task_id']}/workspace",
        payload={"user_id": str(owner["user_id"])},
    )
    assert workspace_status == 201

    workspace_path = Path(workspace_payload["workspace"]["local_path"])
    safe_file = workspace_path / "docs" / "spec.txt"
    safe_file.parent.mkdir(parents=True)
    safe_file.write_text("spec")
    outside_file = tmp_path / "escape.txt"
    outside_file.write_text("escape")

    register_status, register_payload = invoke_request(
        "POST",
        f"/v0/task-workspaces/{workspace_payload['workspace']['id']}/artifacts",
        payload={
            "user_id": str(owner["user_id"]),
            "local_path": str(safe_file),
            "media_type_hint": "text/plain",
        },
    )
    assert register_status == 201

    with psycopg.connect(migrated_database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE task_artifacts
                SET relative_path = '../../../escape.txt'
                WHERE id = %s
                """,
                (register_payload["artifact"]["id"],),
            )
            conn.commit()

    ingest_status, ingest_payload = invoke_request(
        "POST",
        f"/v0/task-artifacts/{register_payload['artifact']['id']}/ingest",
        payload={"user_id": str(owner["user_id"])},
    )

    assert ingest_status == 400
    assert ingest_payload == {
        "detail": f"artifact path {outside_file.resolve()} escapes workspace root {workspace_path.resolve()}"
    }
