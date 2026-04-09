#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

from alicebot_api.config import DEFAULT_DATABASE_URL
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


THREAD_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
REQUIRED_HERMES_TOOL_NAMES = (
    "mcp_alice_core_alice_recall",
    "mcp_alice_core_alice_resume",
    "mcp_alice_core_alice_open_loops",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_hermes_mcp_smoke.py",
        description=(
            "Verify Hermes MCP runtime can discover and call Alice MCP tools "
            "(alice_recall, alice_resume, alice_open_loops)."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Database URL for seeding and runtime calls.",
    )
    parser.add_argument(
        "--python-command",
        default=sys.executable,
        help="Python executable Hermes should use for the Alice MCP server.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Alice repository root used to compose PYTHONPATH for the MCP server.",
    )
    return parser


def _dispatch_mcp_tool(registry, *, tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    payload = json.loads(registry.dispatch(tool_name, arguments))
    if "error" in payload:
        raise RuntimeError(f"{tool_name} returned error: {payload['error']}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"{tool_name} returned unexpected payload: {payload}")
    return result


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Import Hermes MCP runtime lazily so the script can print a clear error
    # when Hermes dependencies are not installed in this Python environment.
    try:
        from tools.mcp_tool import register_mcp_servers, shutdown_mcp_servers
        from tools.registry import registry
    except ModuleNotFoundError as exc:
        print(
            "error: Hermes runtime modules are unavailable. "
            "Install hermes-agent and mcp in this Python environment.",
            file=sys.stderr,
        )
        print(f"detail: {exc}", file=sys.stderr)
        return 1

    user_id = uuid4()
    email = f"hermes-smoke-{user_id}@example.com"
    pythonpath = f"{args.repo_root}/apps/api/src:{args.repo_root}/workers"

    with user_connection(args.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        store.create_user(user_id, email, "Hermes Smoke")

        decision_capture = store.create_continuity_capture_event(
            raw_content="Decision: Keep Alice MCP local-first for Hermes verification.",
            explicit_signal="decision",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_decision",
        )
        decision = store.create_continuity_object(
            capture_event_id=decision_capture["id"],
            object_type="Decision",
            status="active",
            title="Decision: Keep Alice MCP local-first for Hermes verification.",
            body={"decision_text": "Keep Alice MCP local-first for Hermes verification."},
            provenance={"thread_id": str(THREAD_ID), "source_event_ids": ["hermes-smoke-1"]},
            confidence=0.95,
        )

        waiting_capture = store.create_continuity_capture_event(
            raw_content="Waiting For: Hermes docs sign-off",
            explicit_signal="waiting_for",
            admission_posture="DERIVED",
            admission_reason="explicit_signal_waiting_for",
        )
        waiting_for = store.create_continuity_object(
            capture_event_id=waiting_capture["id"],
            object_type="WaitingFor",
            status="active",
            title="Waiting For: Hermes docs sign-off",
            body={"waiting_for_text": "Hermes docs sign-off"},
            provenance={"thread_id": str(THREAD_ID), "source_event_ids": ["hermes-smoke-2"]},
            confidence=0.93,
        )

    server_config = {
        "alice_core": {
            "command": args.python_command,
            "args": ["-m", "alicebot_api.mcp_server"],
            "env": {
                "DATABASE_URL": args.database_url,
                "ALICEBOT_AUTH_USER_ID": str(user_id),
                "PYTHONPATH": pythonpath,
            },
            "tools": {
                "include": ["alice_recall", "alice_resume", "alice_open_loops"],
                "resources": False,
                "prompts": False,
            },
        }
    }

    try:
        registered_tools = set(register_mcp_servers(server_config))
        required_tools = set(REQUIRED_HERMES_TOOL_NAMES)
        if not required_tools.issubset(registered_tools):
            missing = sorted(required_tools - registered_tools)
            raise RuntimeError(f"Hermes did not register expected tools: {missing}")

        recall = _dispatch_mcp_tool(
            registry,
            tool_name="mcp_alice_core_alice_recall",
            arguments={"thread_id": str(THREAD_ID), "query": "Hermes", "limit": 5},
        )
        resume = _dispatch_mcp_tool(
            registry,
            tool_name="mcp_alice_core_alice_resume",
            arguments={"thread_id": str(THREAD_ID), "max_recent_changes": 5, "max_open_loops": 5},
        )
        open_loops = _dispatch_mcp_tool(
            registry,
            tool_name="mcp_alice_core_alice_open_loops",
            arguments={"thread_id": str(THREAD_ID), "limit": 5},
        )

        if recall["summary"]["returned_count"] < 1:
            raise RuntimeError("Recall returned no continuity items.")
        if resume["brief"]["last_decision"]["item"]["id"] != str(decision["id"]):
            raise RuntimeError("Resume did not surface the seeded decision.")
        if open_loops["dashboard"]["waiting_for"]["items"][0]["id"] != str(waiting_for["id"]):
            raise RuntimeError("Open loops did not surface the seeded waiting-for item.")

        summary = {
            "registered_tools": sorted(required_tools),
            "recall_items": recall["summary"]["returned_count"],
            "resume_last_decision_title": resume["brief"]["last_decision"]["item"]["title"],
            "open_loop_count": open_loops["dashboard"]["summary"]["total_count"],
        }
        print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    finally:
        shutdown_mcp_servers()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
