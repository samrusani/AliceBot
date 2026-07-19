#!/usr/bin/env python3
"""MCP-native quickstart: capture one memory and recall it over stdio.

This script is the smallest end-to-end proof that Alice's packaged MCP
server works: it spawns the zero-infrastructure SQLite on-ramp as a
subprocess, speaks MCP JSON-RPC over stdio (initialize handshake,
``tools/list``, ``alice_capture``, ``alice_memory_commit``,
``alice_recall``), and verifies the committed sentence comes back from
recall. Standard library only -- no MCP SDK, no HTTP server, no
Postgres.

Two write paths are shown, matching ``docs/alpha/first-memory.md``:

- ``alice_capture`` stores source evidence and produces candidate
  memories that wait for review -- it does not silently promote
  trusted memory, so a recall right after capture finds nothing.
- ``alice_memory_commit`` is the explicit "remember this" path; the
  committed memory is active immediately and recall returns it.

The subprocess launched here::

    python -m alicebot_api.onramp mcp --data-dir <temp dir>

is exactly what the published package runs as::

    uvx alice-memory mcp

A Claude Desktop config for the same server (see
``docs/integrations/mcp.md`` for the Postgres variant)::

    {
      "mcpServers": {
        "alice": {
          "command": "uvx",
          "args": ["alice-memory", "mcp"]
        }
      }
    }

Run it from the repo root::

    .venv/bin/python docs/examples/mcp_quickstart.py

On success it prints ``MCP QUICKSTART OK`` plus a short summary and
exits 0; any protocol or content mismatch raises and exits non-zero.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from typing import Any

CORE_TOOL_NAMES = frozenset(
    {
        "alice_capture",
        "alice_memory_commit",
        "alice_recall",
        "alice_resume",
        "alice_context_pack",
        "alice_open_loops",
        "alice_recent_decisions",
        "alice_memory_review",
        "alice_memory_correct",
        "alice_memory_manage",
        "alice_explain",
    }
)

CAPTURE_SENTENCE = (
    "The MCP quickstart canary phrase is indigo-lighthouse-42; "
    "it proves capture and recall work over stdio."
)
RECALL_QUERY = "indigo-lighthouse-42 canary phrase"


class MCPClient:
    """Minimal newline-delimited JSON-RPC client over a child's stdio."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self._process = process
        self._next_id = 0

    def _send(self, message: dict[str, Any]) -> None:
        stdin = self._process.stdin
        assert stdin is not None
        stdin.write(json.dumps(message).encode("utf-8") + b"\n")
        stdin.flush()

    def _read_response(self) -> dict[str, Any]:
        stdout = self._process.stdout
        assert stdout is not None
        line = stdout.readline()
        if line == b"":
            raise RuntimeError(
                "MCP server closed stdout before responding "
                f"(exit code: {self._process.poll()})"
            )
        payload = json.loads(line.decode("utf-8"))
        if "error" in payload:
            raise RuntimeError(f"JSON-RPC error response: {payload['error']}")
        return payload

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self._next_id += 1
        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params
        self._send(message)
        response = self._read_response()
        if response.get("id") != self._next_id:
            raise RuntimeError(f"response id mismatch: {response!r}")
        return response["result"]

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request(
            "tools/call", {"name": name, "arguments": arguments}
        )
        if result.get("isError"):
            raise RuntimeError(f"tool {name} failed: {result!r}")
        text = result["content"][0]["text"]
        structured = json.loads(text)
        if not isinstance(structured, dict):
            raise RuntimeError(f"tool {name} returned non-object: {text!r}")
        return structured


def run_quickstart(data_dir: str) -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "alicebot_api.onramp", "mcp", "--data-dir", data_dir],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        client = MCPClient(process)

        # 1. MCP initialize handshake.
        init_result = client.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-quickstart", "version": "1.0"},
            },
        )
        server_name = init_result["serverInfo"]["name"]
        client.notify("notifications/initialized")

        # 2. The default surface is exactly the eleven core tools.
        tools = client.request("tools/list")["tools"]
        tool_names = {tool["name"] for tool in tools}
        if tool_names != CORE_TOOL_NAMES:
            raise RuntimeError(
                "tool surface mismatch; "
                f"missing={sorted(CORE_TOOL_NAMES - tool_names)} "
                f"unexpected={sorted(tool_names - CORE_TOOL_NAMES)}"
            )

        # 3. Capture the sentence as source evidence. This creates
        #    candidate memories awaiting review -- deliberately NOT yet
        #    recallable, so nothing here can pass by accident.
        capture = client.call_tool(
            "alice_capture",
            {
                "raw_text": CAPTURE_SENTENCE,
                "title": "MCP quickstart canary",
            },
        )
        if capture.get("candidate_memory_count", 0) < 1:
            raise RuntimeError(f"capture produced no candidates: {capture!r}")

        # 4. Commit the sentence as explicit, user-directed memory.
        #    This is the deterministic write path: the memory is active
        #    immediately.
        commit = client.call_tool(
            "alice_memory_commit",
            {
                "title": "MCP quickstart canary",
                "canonical_text": CAPTURE_SENTENCE,
            },
        )
        memory = commit.get("memory") or {}
        if memory.get("canonical_text") != CAPTURE_SENTENCE:
            raise RuntimeError(f"commit did not store the sentence: {commit!r}")

        # 5. Recall it. With no embedding endpoint configured the server
        #    falls back to full-text search, so this stays offline. The
        #    committed sentence must appear in a returned result's text,
        #    not merely in the echoed query.
        recall = client.call_tool("alice_recall", {"query": RECALL_QUERY})
        results = recall.get("results") or []
        recalled = [
            item
            for item in results
            if "indigo-lighthouse-42" in str(item.get("text", ""))
        ]
        if not recalled:
            raise RuntimeError(
                f"committed sentence not found in recall results: {recall!r}"
            )

        print("MCP QUICKSTART OK")
        print(f"server: {server_name}")
        print(f"tools: {len(tool_names)} (core surface verified)")
        print(f"capture: source_id={capture.get('source_id')} candidates={capture.get('candidate_memory_count')}")
        print(f"commit: memory_id={memory.get('id')} status={memory.get('status')}")
        print(f"recall: {len(recalled)} of {len(results)} results contain the canary phrase")
    finally:
        if process.stdin is not None:
            process.stdin.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alice-mcp-quickstart-") as data_dir:
        run_quickstart(data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
