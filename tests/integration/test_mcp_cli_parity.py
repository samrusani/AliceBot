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

from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import ContinuityRecallQueryInput, ContinuityResumptionBriefRequestInput
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


def run_cli(args: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alicebot_api", *args],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


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
        payload: dict[str, object] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        _write_mcp_message(self.process.stdin, payload)
        response = _read_mcp_message(self.process.stdout)
        assert response.get("id") == request_id
        return response

    def notify(self, method: str, params: dict[str, object] | None = None) -> None:
        payload: dict[str, object] = {"jsonrpc": "2.0", "method": method}
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


def _call_tool(client: MCPClient, *, name: str, arguments: dict[str, object]) -> dict[str, Any]:
    response = client.request("tools/call", params={"name": name, "arguments": arguments})
    assert "error" not in response
    result = response["result"]
    assert result["isError"] is False
    return result["structuredContent"]


def test_mcp_recall_and_resume_match_core_and_cli_behavior(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="mcp-parity@example.com")
    thread_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)

        decision_capture = store.create_continuity_capture_event(
            raw_content="Decision: Keep release freeze",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        decision_object = store.create_continuity_object(
            capture_event_id=decision_capture["id"],
            object_type="Decision",
            status="active",
            title="Decision: Keep release freeze",
            body={"decision_text": "Keep release freeze"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["mcp-parity-1"]},
            confidence=0.96,
        )

        next_action_capture = store.create_continuity_capture_event(
            raw_content="Next Action: Draft release memo",
            explicit_signal="next_action",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_next_action",
        )
        next_action_object = store.create_continuity_object(
            capture_event_id=next_action_capture["id"],
            object_type="NextAction",
            status="active",
            title="Next Action: Draft release memo",
            body={"action_text": "Draft release memo"},
            provenance={"thread_id": str(thread_id), "source_event_ids": ["mcp-parity-2"]},
            confidence=0.92,
        )

    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=decision_object["id"],
        created_at=datetime(2026, 4, 2, 9, 0, tzinfo=UTC),
    )
    set_continuity_timestamps(
        migrated_database_urls["admin"],
        continuity_object_id=next_action_object["id"],
        created_at=datetime(2026, 4, 2, 9, 5, tzinfo=UTC),
    )

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        core_recall = query_continuity_recall(
            store,
            user_id=user_id,
            request=ContinuityRecallQueryInput(
                thread_id=thread_id,
                query="release",
                limit=20,
            ),
        )
        core_resume = compile_continuity_resumption_brief(
            store,
            user_id=user_id,
            request=ContinuityResumptionBriefRequestInput(
                thread_id=thread_id,
                max_recent_changes=5,
                max_open_loops=5,
            ),
        )

    client = start_mcp_client(database_url=migrated_database_urls["app"], user_id=user_id)
    try:
        mcp_recall = _call_tool(
            client,
            name="alice_recall",
            arguments={
                "thread_id": str(thread_id),
                "query": "release",
                "limit": 20,
            },
        )
        mcp_resume = _call_tool(
            client,
            name="alice_resume",
            arguments={
                "thread_id": str(thread_id),
                "max_recent_changes": 5,
                "max_open_loops": 5,
            },
        )
        mcp_recall_debug = _call_tool(
            client,
            name="alice_recall_debug",
            arguments={
                "thread_id": str(thread_id),
                "query": "release",
                "limit": 20,
            },
        )
        retrieval_run_id = mcp_recall_debug["debug"]["retrieval_run_id"]
        mcp_retrieval_trace = _call_tool(
            client,
            name="alice_retrieval_trace",
            arguments={"retrieval_run_id": retrieval_run_id},
        )
    finally:
        client.close()

    assert mcp_recall == core_recall
    assert mcp_resume == core_resume
    assert mcp_recall_debug["items"] == core_recall["items"]
    assert mcp_recall_debug["debug"]["candidate_count"] >= 1
    assert mcp_retrieval_trace["retrieval_run"]["id"] == retrieval_run_id

    env = build_runtime_env(database_url=migrated_database_urls["app"], user_id=user_id)
    cli_recall = run_cli(
        ["recall", "--thread-id", str(thread_id), "--query", "release", "--limit", "20"],
        env=env,
    )
    assert cli_recall.returncode == 0
    assert core_recall["items"][0]["title"] in cli_recall.stdout
    assert core_recall["items"][0]["id"] in cli_recall.stdout

    cli_resume = run_cli(
        ["resume", "--thread-id", str(thread_id), "--max-recent-changes", "5", "--max-open-loops", "5"],
        env=env,
    )
    assert cli_resume.returncode == 0
    assert core_resume["brief"]["last_decision"]["item"]["title"] in cli_resume.stdout
    assert core_resume["brief"]["next_action"]["item"]["title"] in cli_resume.stdout
