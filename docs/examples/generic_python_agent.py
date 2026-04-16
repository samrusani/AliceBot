#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Minimal generic Python agent example for Alice one-call continuity.",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("ALICE_API_BASE_URL", "http://127.0.0.1:8000"),
        help="Alice API base URL.",
    )
    parser.add_argument(
        "--session-token",
        default=os.getenv("ALICE_SESSION_TOKEN"),
        help="Alice session token used as a Bearer token.",
    )
    parser.add_argument(
        "--brief-type",
        default=os.getenv("ALICE_BRIEF_TYPE", "agent_handoff"),
        help="Alice brief type.",
    )
    parser.add_argument(
        "--thread-id",
        default=os.getenv("ALICE_THREAD_ID"),
        help="Optional thread UUID.",
    )
    parser.add_argument(
        "--query",
        default=os.getenv("ALICE_QUERY", "release handoff"),
        help="Optional query string.",
    )
    return parser


def _compact_agent_view(payload: dict[str, Any]) -> dict[str, Any]:
    brief = payload["brief"]
    next_action = brief.get("next_suggested_action") or {}
    open_loops = brief.get("open_loops") or {}
    open_loop_summary = open_loops.get("summary") or {}
    trust_posture = brief.get("trust_posture") or {}
    return {
        "brief_type": brief.get("brief_type"),
        "summary": brief.get("summary"),
        "next_suggested_action": next_action.get("title"),
        "open_loop_count": open_loop_summary.get("total_count"),
        "source_kinds": brief.get("sources", []),
        "open_conflict_count": trust_posture.get("open_conflict_count"),
    }


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.session_token:
        print("Missing Alice session token. Set ALICE_SESSION_TOKEN or pass --session-token.", file=sys.stderr)
        return 1

    request_body: dict[str, Any] = {
        "brief_type": args.brief_type,
        "query": args.query,
        "max_relevant_facts": 6,
        "max_recent_changes": 5,
        "max_open_loops": 5,
        "max_conflicts": 3,
        "max_timeline_highlights": 5,
    }
    if args.thread_id:
        request_body["thread_id"] = args.thread_id

    encoded_body = json.dumps(request_body).encode("utf-8")
    request = Request(
        url=f"{args.api_base_url.rstrip('/')}/v1/continuity/brief",
        data=encoded_body,
        method="POST",
        headers={
            "Authorization": f"Bearer {args.session_token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Alice returned HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Failed to reach Alice: {exc.reason}", file=sys.stderr)
        return 1

    print(json.dumps(_compact_agent_view(payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
