#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib import request


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke-check a running Alice Lite profile by verifying the local "
            "health endpoint and the one-call continuity CLI brief."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Alice API base URL.",
    )
    parser.add_argument(
        "--python-command",
        default=sys.executable,
        help="Python executable used to invoke the Alice CLI.",
    )
    parser.add_argument(
        "--query",
        default="local-first startup path",
        help="Continuity query sent to the CLI brief surface.",
    )
    return parser.parse_args()


def _get_health(base_url: str) -> dict[str, object]:
    with request.urlopen(f"{base_url}/healthz", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    args = _parse_args()
    health = _get_health(args.base_url)
    if health.get("status") != "ok":
        raise RuntimeError(f"Alice Lite healthcheck failed: {health}")

    env = dict(os.environ)
    pythonpath_entries = [str(REPO_ROOT / "apps" / "api" / "src")]
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    if existing_pythonpath != "":
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)

    command = [
        args.python_command,
        "-m",
        "alicebot_api",
        "brief",
        "--brief-type",
        "general",
        "--query",
        args.query,
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout
    required_markers = (
        "continuity brief",
        "brief_type: general",
        "summary:",
        "relevant_facts",
        "next_suggested_action:",
    )
    missing_markers = [marker for marker in required_markers if marker not in output]
    if missing_markers:
        raise RuntimeError(
            "Alice Lite CLI brief output is missing required markers: "
            + ", ".join(missing_markers)
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "health": health["status"],
                "services": health["services"],
                "brief_markers_verified": list(required_markers),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
