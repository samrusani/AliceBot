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
    # These suites exercise the legacy long-tail tools as well as the core
    # nine, so enable the legacy MCP surface for the spawned server.
    env["ALICE_MCP_LEGACY_TOOLS"] = "1"

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
        try:
            response = _read_mcp_message(self.process.stdout)
        except RuntimeError as exc:
            stderr_text = ""
            if self.process.stderr is not None:
                stderr_text = self.process.stderr.read().decode("utf-8", errors="replace")
            if stderr_text.strip():
                raise RuntimeError(f"{exc}\nMCP stderr:\n{stderr_text}") from exc
            raise
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
    result = response["result"]
    return json.loads(result["content"][0]["text"])


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
        assert "alice_task_brief" in tool_names
        assert "alice_task_brief_compare" in tool_names
        assert "alice_prefetch_context" in tool_names
        assert "alice_open_loops" in tool_names
        assert "alice_review_queue" in tool_names
        assert "alice_review_apply" in tool_names

        # Core recall now searches vNext memories with hybrid FTS+RRF ranking;
        # commit one through agent policy and confirm recall returns it.
        committed = _call_tool(
            client,
            name="alice_vnext_commit_memory",
            arguments={
                "agent_id": "hermes",
                "agent_type": "personal_assistant",
                "permission_profile": "trusted_local_agent",
                "title": "Rollout checklist owner",
                "canonical_text": "Priya owns the phased rollout checklist for the beta launch.",
                "memory_type": "decision",
                "domain": "professional",
                "sensitivity": "internal",
                "confidence": 0.96,
            },
        )
        assert committed["status"] == "committed"
        committed_memory_id = committed["memory"]["id"]

        core_recall = _call_tool(
            client,
            name="alice_recall",
            arguments={"query": "rollout checklist", "limit": 5, "debug": True},
        )
        assert core_recall["count"] >= 1
        assert core_recall["results"][0]["id"] == committed_memory_id
        assert core_recall["retrieval"]["fusion"]["algorithm"] == "reciprocal_rank_fusion"
        assert core_recall["retrieval"]["stages"]["fts"]["candidate_count"] >= 1

        # The legacy continuity recall view stays available behind the flag.
        recall_before = _call_tool(
            client,
            name="alice_recall_debug",
            arguments={
                "thread_id": str(thread_id),
                "query": "rollout",
                "limit": 20,
            },
        )
        before_payload = recall_before
        assert before_payload["items"][0]["id"] == str(legacy_decision["id"])
        assert before_payload["items"][0]["explanation"]["evidence_segments"][0]["source_kind"] == (
            "continuity_capture_event"
        )

        resume_before = _call_tool(
            client,
            name="alice_resume",
            arguments={
                "thread_id": str(thread_id),
                "max_recent_changes": 5,
                "max_open_loops": 5,
            },
        )
        assert resume_before["brief"]["last_decision"]["id"] == committed_memory_id
        assert resume_before["brief"]["filters_ignored"] == ["thread_id"]

        prefetch_before = _call_tool(
            client,
            name="alice_prefetch_context",
            arguments={
                "thread_id": str(thread_id),
                "max_recent_changes": 5,
                "max_open_loops": 5,
            },
        )
        prefetch_payload = prefetch_before["prefetch_context"]
        assert prefetch_payload["last_decision"]["item"]["id"] == str(legacy_decision["id"])
        assert "## Alice Continuity Prefetch" in prefetch_payload["text"]

        # Core open_loops lists vNext open loops (none seeded here); the legacy
        # WaitingFor continuity object stays visible through the debug recall view.
        open_loops = _call_tool(
            client,
            name="alice_open_loops",
            arguments={"limit": 20},
        )
        assert open_loops["count"] == 0
        assert open_loops["items"] == []
        assert any(
            item["id"] == str(waiting_for["id"]) for item in before_payload["items"]
        ) or any(
            item["id"] == str(waiting_for["id"])
            for item in _call_tool(
                client,
                name="alice_recall_debug",
                arguments={"thread_id": str(thread_id), "limit": 20},
            )["items"]
        )

        review_queue = _call_tool(
            client,
            name="alice_review_queue",
            arguments={
                "status": "correction_ready",
                "limit": 20,
            },
        )
        queue_payload = review_queue
        queue_item = next(
            item for item in queue_payload["items"] if item["id"] == str(legacy_decision["id"])
        )
        assert queue_item["explanation"]["trust"]["trust_class"] in {
            "deterministic",
            "llm_single_source",
            "llm_corroborated",
            "human_curated",
        }
        assert queue_item["explanation"]["proposal_rationale"]

        correction = _call_tool(
            client,
            name="alice_review_apply",
            arguments={
                "review_item_id": str(legacy_decision["id"]),
                "action": "supersede-existing",
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
        assert correction["review_action"]["resolved_action"] == "supersede"
        replacement_id = correction["replacement_object"]["id"]

        recall_after = _call_tool(
            client,
            name="alice_recall_debug",
            arguments={
                "thread_id": str(thread_id),
                "query": "rollout",
                "limit": 20,
            },
        )
        after_payload = recall_after
        assert after_payload["items"][0]["id"] == replacement_id
        assert any(item["id"] == str(legacy_decision["id"]) for item in after_payload["items"])
        replacement_item = next(item for item in after_payload["items"] if item["id"] == replacement_id)
        legacy_item = next(item for item in after_payload["items"] if item["id"] == str(legacy_decision["id"]))
        assert any(note["kind"] == "supersedes" for note in replacement_item["explanation"]["supersession_notes"])
        assert any(note["kind"] == "superseded_by" for note in legacy_item["explanation"]["supersession_notes"])
        assert any(note["action"] == "supersede" for note in legacy_item["explanation"]["supersession_notes"])

        resume_after = _call_tool(
            client,
            name="alice_resume",
            arguments={
                "thread_id": str(thread_id),
                "max_recent_changes": 5,
                "max_open_loops": 5,
            },
        )
        # The correction above exercises the explicitly enabled legacy
        # surface. Core resume remains canonical vNext and therefore keeps
        # returning the vNext decision committed at the start of the test.
        assert resume_after["brief"]["last_decision"]["id"] == committed_memory_id

        rejected = _call_tool(
            client,
            name="alice_review_apply",
            arguments={
                "review_item_id": str(waiting_for["id"]),
                "action": "reject",
                "reason": "No longer needed",
            },
        )
        assert rejected["review_action"]["resolved_action"] == "delete"

        recall_post_reject = _call_tool(
            client,
            name="alice_recall_debug",
            arguments={
                "thread_id": str(thread_id),
                "limit": 20,
            },
        )
        recall_rejected_payload = recall_post_reject
        assert all(item["id"] != str(waiting_for["id"]) for item in recall_rejected_payload["items"])
    finally:
        client.close()


def test_mcp_memory_mutation_tools_smoke(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="mcp-mutations@example.com")
    thread_id = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)
        capture = store.create_continuity_capture_event(
            raw_content="Decision: Legacy MCP mutation plan",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type="Decision",
            status="active",
            title="Decision: Legacy MCP mutation plan",
            body={"decision_text": "Legacy MCP mutation plan"},
            provenance={"thread_id": str(thread_id)},
            confidence=0.95,
        )

    client = start_mcp_client(database_url=migrated_database_urls["app"], user_id=user_id)
    try:
        generated = _call_tool(
            client,
            name="alice_memory_mutations_generate",
            arguments={
                "user_content": "Correction: Updated MCP mutation plan",
                "assistant_content": "",
                "mode": "assist",
                "sync_fingerprint": "mcp-mutation-sync-001",
                "thread_id": str(thread_id),
            },
        )
        generated_payload = generated
        assert generated_payload["summary"]["operation_types"] == ["SUPERSEDE"]
        candidate_id = generated_payload["items"][0]["id"]

        listed_candidates = _call_tool(
            client,
            name="alice_memory_mutations_list_candidates",
            arguments={
                "sync_fingerprint": "mcp-mutation-sync-001",
                "limit": 20,
            },
        )
        assert listed_candidates["summary"]["returned_count"] == 1

        committed = _call_tool(
            client,
            name="alice_memory_mutations_commit",
            arguments={
                "candidate_ids": [candidate_id],
            },
        )
        committed_payload = committed
        assert committed_payload["summary"]["applied_count"] == 1
        assert committed_payload["operations"][0]["operation_type"] == "SUPERSEDE"

        listed_operations = _call_tool(
            client,
            name="alice_memory_mutations_list_operations",
            arguments={
                "sync_fingerprint": "mcp-mutation-sync-001",
                "limit": 20,
            },
        )
        assert listed_operations["summary"]["returned_count"] == 1
        assert listed_operations["items"][0]["operation_type"] == "SUPERSEDE"
    finally:
        client.close()
