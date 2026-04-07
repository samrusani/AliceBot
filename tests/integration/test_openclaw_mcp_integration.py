from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from uuid import UUID, uuid4

from alicebot_api.db import user_connection
from alicebot_api.openclaw_import import import_openclaw_source
from alicebot_api.store import ContinuityStore


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENCLAW_FIXTURE_PATH = REPO_ROOT / "fixtures" / "openclaw" / "workspace_v1.json"
THREAD_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


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


class MCPClient:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process
        self._next_id = 1

    def request(self, method: str, params: dict[str, object] | None = None) -> dict[str, object]:
        request_id = self._next_id
        self._next_id += 1
        payload: dict[str, object] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        assert self.process.stdin is not None
        _write_mcp_message(self.process.stdin, payload)
        assert self.process.stdout is not None
        response = _read_mcp_message(self.process.stdout)
        assert response.get("id") == request_id
        return response

    def notify(self, method: str, params: dict[str, object] | None = None) -> None:
        payload: dict[str, object] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        assert self.process.stdin is not None
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

    client = MCPClient(process=process)
    initialize = client.request(
        "initialize",
        params={
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "pytest-openclaw-mcp", "version": "1.0"},
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


def test_openclaw_imported_data_is_usable_from_shipped_mcp_recall_and_resume_tools(
    migrated_database_urls,
) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="openclaw-mcp@example.com")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        summary = import_openclaw_source(
            store,
            user_id=user_id,
            source=OPENCLAW_FIXTURE_PATH,
        )
        assert summary["imported_count"] == 4

    client = start_mcp_client(database_url=migrated_database_urls["app"], user_id=user_id)
    try:
        recall_payload = _call_tool(
            client,
            name="alice_recall",
            arguments={
                "thread_id": str(THREAD_ID),
                "project": "Alice Public Core",
                "query": "MCP tool surface",
                "limit": 20,
            },
        )
        resume_payload = _call_tool(
            client,
            name="alice_resume",
            arguments={
                "thread_id": str(THREAD_ID),
                "max_recent_changes": 10,
                "max_open_loops": 10,
            },
        )
    finally:
        client.close()

    assert recall_payload["summary"]["returned_count"] >= 1
    assert any(item["provenance"]["source_kind"] == "openclaw_import" for item in recall_payload["items"])

    brief = resume_payload["brief"]
    assert brief["last_decision"]["item"] is not None
    assert brief["last_decision"]["item"]["provenance"]["source_kind"] == "openclaw_import"
    assert brief["next_action"]["item"] is not None
    assert brief["next_action"]["item"]["provenance"]["source_kind"] == "openclaw_import"
