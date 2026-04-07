from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import UUID, uuid4

import psycopg

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


REPO_ROOT = Path(__file__).resolve().parents[2]


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def set_continuity_timestamps(
    admin_database_url: str,
    *,
    continuity_object_id: UUID,
    created_at: datetime,
) -> None:
    with psycopg.connect(admin_database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE continuity_objects SET created_at = %s, updated_at = %s WHERE id = %s",
                (created_at, created_at, continuity_object_id),
            )


def build_runtime_env(*, database_url: str, user_id: UUID) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["ALICEBOT_AUTH_USER_ID"] = str(user_id)

    pythonpath_entries = [str(REPO_ROOT / "apps" / "api" / "src"), str(REPO_ROOT / "workers")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return env


def _write_mcp_message(stream, payload: dict[str, object]) -> None:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    stream.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("ascii"))
    stream.write(encoded)
    stream.flush()


def _read_mcp_message(stream) -> dict[str, object]:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if line == b"":
            raise RuntimeError("MCP server closed stdout unexpectedly")
        if line in {b"\r\n", b"\n"}:
            break
        decoded = line.decode("utf-8").strip()
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    content_length = int(headers["content-length"])
    body = stream.read(content_length)
    return json.loads(body.decode("utf-8"))


@dataclass
class MCPClient:
    process: subprocess.Popen[bytes]
    _next_id: int = 1

    def request(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        request_id = self._next_id
        self._next_id += 1
        payload: dict[str, object] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        _write_mcp_message(self.process.stdin, payload)
        response = _read_mcp_message(self.process.stdout)
        assert response.get("id") == request_id
        return response

    def notify(self, method: str, params: dict[str, object] | None = None) -> None:
        payload: dict[str, object] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        _write_mcp_message(self.process.stdin, payload)

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


def start_mcp_client(*, database_url: str, user_id: UUID) -> MCPClient:
    env = build_runtime_env(database_url=database_url, user_id=user_id)
    process = subprocess.Popen(
        [sys.executable, "-m", "alicebot_api.mcp_server"],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    assert process.stdin is not None
    assert process.stdout is not None

    client = MCPClient(process=process)
    initialize = client.request(
        "initialize",
        params={
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "pytest-mcp-client", "version": "1.0"},
            "capabilities": {},
        },
    )
    assert initialize["result"]["protocolVersion"] == "2024-11-05"
    client.notify("notifications/initialized", {})
    return client


def _call_tool(client: MCPClient, *, name: str, arguments: dict[str, object]) -> dict[str, object]:
    response = client.request("tools/call", params={"name": name, "arguments": arguments})
    assert "error" not in response
    return response["result"]


def test_mcp_server_tool_calls_and_correction_flow(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="mcp-user@example.com")
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        legacy_capture = store.create_continuity_capture_event(
            raw_content="Decision: Legacy rollout plan",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        legacy_decision = store.create_continuity_object(
            capture_event_id=legacy_capture["id"],
            object_type="Decision",
            status="active",
            title="Decision: Legacy rollout plan",
            body={"decision_text": "Legacy rollout plan"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["mcp-seed-1"]},
            confidence=0.93,
        )

        waiting_capture = store.create_continuity_capture_event(
            raw_content="Waiting For: Reviewer PASS",
            explicit_signal="waiting_for",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_waiting_for",
        )
        waiting_for = store.create_continuity_object(
            capture_event_id=waiting_capture["id"],
            object_type="WaitingFor",
            status="active",
            title="Waiting For: Reviewer PASS",
            body={"waiting_for_text": "Reviewer PASS"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["mcp-seed-2"]},
            confidence=0.9,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=legacy_decision["id"],
        created_at=datetime(2026, 4, 1, 10, 0, tzinfo=UTC),
    )
    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=waiting_for["id"],
        created_at=datetime(2026, 4, 1, 10, 5, tzinfo=UTC),
    )

    client = start_mcp_client(database_url=migrated_database_urls["app"], user_id=user_id)
    try:
        tools_list = client.request("tools/list")
        tool_names = [tool["name"] for tool in tools_list["result"]["tools"]]
        assert "alice_recall" in tool_names
        assert "alice_resume" in tool_names
        assert "alice_memory_correct" in tool_names

        recall_before = _call_tool(
            client,
            name="alice_recall",
            arguments={
                "thread_id": str(thread_id),
                "query": "rollout",
                "limit": 20,
            },
        )
        assert recall_before["isError"] is False
        before_payload = recall_before["structuredContent"]
        assert before_payload["items"][0]["id"] == str(legacy_decision["id"])

        resume_before = _call_tool(
            client,
            name="alice_resume",
            arguments={
                "thread_id": str(thread_id),
                "max_recent_changes": 5,
                "max_open_loops": 5,
            },
        )
        assert resume_before["isError"] is False
        assert resume_before["structuredContent"]["brief"]["last_decision"]["item"]["id"] == str(legacy_decision["id"])

        correction = _call_tool(
            client,
            name="alice_memory_correct",
            arguments={
                "continuity_object_id": str(legacy_decision["id"]),
                "action": "supersede",
                "reason": "Latest rollout decision supersedes legacy plan",
                "replacement_title": "Decision: Updated rollout plan",
                "replacement_body": {"decision_text": "Updated rollout plan"},
                "replacement_provenance": {
                    "thread_id": str(thread_id),
                    "source_event_ids": ["mcp-correction-1"],
                },
                "replacement_confidence": 0.98,
            },
        )
        assert correction["isError"] is False
        replacement_id = correction["structuredContent"]["replacement_object"]["id"]

        recall_after = _call_tool(
            client,
            name="alice_recall",
            arguments={
                "thread_id": str(thread_id),
                "query": "rollout",
                "limit": 20,
            },
        )
        assert recall_after["isError"] is False
        after_payload = recall_after["structuredContent"]
        assert after_payload["items"][0]["id"] == replacement_id
        assert any(item["id"] == str(legacy_decision["id"]) for item in after_payload["items"])

        resume_after = _call_tool(
            client,
            name="alice_resume",
            arguments={
                "thread_id": str(thread_id),
                "max_recent_changes": 5,
                "max_open_loops": 5,
            },
        )
        assert resume_after["isError"] is False
        assert resume_after["structuredContent"]["brief"]["last_decision"]["item"]["id"] == replacement_id
    finally:
        client.close()
