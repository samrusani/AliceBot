#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDER_SMOKE_SCRIPT = REPO_ROOT / "scripts" / "run_hermes_memory_provider_smoke.py"
DEFAULT_MCP_SMOKE_SCRIPT = REPO_ROOT / "scripts" / "run_hermes_mcp_smoke.py"
DEFAULT_DEMO_COMMAND = "./.venv/bin/python scripts/run_hermes_bridge_demo.py"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_hermes_bridge_demo.py",
        description=(
            "Run the bridge-phase Hermes demo in one command by executing "
            "provider and MCP smoke validations and printing a compact summary."
        ),
    )
    parser.add_argument(
        "--python-command",
        default=sys.executable,
        help="Python executable used to run smoke scripts.",
    )
    parser.add_argument(
        "--provider-smoke-script",
        type=Path,
        default=DEFAULT_PROVIDER_SMOKE_SCRIPT,
        help="Path to run_hermes_memory_provider_smoke.py.",
    )
    parser.add_argument(
        "--mcp-smoke-script",
        type=Path,
        default=DEFAULT_MCP_SMOKE_SCRIPT,
        help="Path to run_hermes_mcp_smoke.py.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Optional DATABASE_URL override passed to the MCP smoke script.",
    )
    return parser


def _parse_json_output(stdout: str) -> dict[str, Any] | None:
    payload = stdout.strip()
    if payload == "":
        return None
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _short_text(value: str, *, limit: int = 240) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _run_step(*, name: str, command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    parsed = _parse_json_output(completed.stdout)
    return {
        "name": name,
        "command": command,
        "returncode": completed.returncode,
        "json": parsed,
        "stdout_excerpt": _short_text(completed.stdout),
        "stderr_excerpt": _short_text(completed.stderr),
    }


def _provider_checks(step: dict[str, Any]) -> dict[str, Any]:
    payload = step.get("json")
    if not isinstance(payload, dict):
        return {"json_available": False, "bridge_ready": False}

    structural = payload.get("structural")
    if not isinstance(structural, dict):
        return {"json_available": True, "bridge_ready": False}

    bridge_status = structural.get("bridge_status")
    if not isinstance(bridge_status, dict):
        return {"json_available": True, "bridge_ready": False}

    return {
        "json_available": True,
        "bridge_ready": bool(bridge_status.get("ready", False)),
        "provider_registered": bool(structural.get("alice_registered", False)),
        "single_external_enforced": bool(structural.get("single_external_enforced", False)),
    }


def _mcp_checks(step: dict[str, Any]) -> dict[str, Any]:
    payload = step.get("json")
    if not isinstance(payload, dict):
        return {"json_available": False, "bridge_flow_validated": False}

    required_fields = (
        "recall_items",
        "open_loop_count",
        "capture_candidate_count",
        "capture_auto_saved_count",
        "capture_review_queued_count",
        "review_apply_resolved_action",
    )
    if not all(field in payload for field in required_fields):
        return {"json_available": True, "bridge_flow_validated": False}

    return {
        "json_available": True,
        "bridge_flow_validated": (
            payload.get("recall_items", 0) > 0
            and payload.get("open_loop_count", 0) > 0
            and payload.get("capture_candidate_count", 0) > 0
            and payload.get("capture_auto_saved_count", 0) > 0
            and payload.get("capture_review_queued_count", 0) > 0
            and payload.get("review_apply_resolved_action") == "confirm"
        ),
        "recall_items": payload.get("recall_items"),
        "open_loop_count": payload.get("open_loop_count"),
        "capture_candidate_count": payload.get("capture_candidate_count"),
        "capture_auto_saved_count": payload.get("capture_auto_saved_count"),
        "capture_review_queued_count": payload.get("capture_review_queued_count"),
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    provider_script = args.provider_smoke_script.resolve()
    mcp_script = args.mcp_smoke_script.resolve()
    if not provider_script.exists():
        raise RuntimeError(f"provider smoke script not found: {provider_script}")
    if not mcp_script.exists():
        raise RuntimeError(f"mcp smoke script not found: {mcp_script}")

    provider_step = _run_step(
        name="provider_smoke",
        command=[args.python_command, str(provider_script)],
    )

    mcp_command = [
        args.python_command,
        str(mcp_script),
        "--python-command",
        args.python_command,
        "--repo-root",
        str(REPO_ROOT),
    ]
    if args.database_url:
        mcp_command.extend(["--database-url", args.database_url])

    mcp_step = _run_step(
        name="mcp_smoke",
        command=mcp_command,
    )

    provider_summary = _provider_checks(provider_step)
    mcp_summary = _mcp_checks(mcp_step)

    ok = (
        provider_step["returncode"] == 0
        and mcp_step["returncode"] == 0
        and provider_summary.get("bridge_ready") is True
        and mcp_summary.get("bridge_flow_validated") is True
    )

    payload = {
        "status": "pass" if ok else "fail",
        "recommended_path": "provider_plus_mcp",
        "fallback_path": "mcp_only",
        "demo_command": DEFAULT_DEMO_COMMAND,
        "steps": [
            {
                "name": provider_step["name"],
                "returncode": provider_step["returncode"],
                "summary": provider_summary,
                "stderr_excerpt": provider_step["stderr_excerpt"],
            },
            {
                "name": mcp_step["name"],
                "returncode": mcp_step["returncode"],
                "summary": mcp_summary,
                "stderr_excerpt": mcp_step["stderr_excerpt"],
            },
        ],
    }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
