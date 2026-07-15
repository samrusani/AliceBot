#!/usr/bin/env python3
"""Bootstrap the deterministic Alice Lite workspace and request a first brief."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any
from urllib import error, request
from uuid import UUID


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_THREAD_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
LOCAL_USER_HEADER = "X-AliceBot-User-Id"


def _request_json(
    *,
    method: str,
    base_url: str,
    path: str,
    user_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if user_id is not None:
        headers[LOCAL_USER_HEADER] = user_id
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with request.urlopen(http_request, timeout=10) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{path} request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{path} returned a non-object payload")
    return parsed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ensure the deterministic local Alice workspace and request a "
            "one-call continuity brief against the seeded sample thread."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Alice API base URL.",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("ALICEBOT_AUTH_USER_ID", DEFAULT_USER_ID),
        help="Local Alice identity used for deterministic workspace bootstrap.",
    )
    parser.add_argument(
        "--query",
        default="local-first startup path",
        help="Continuity query sent to the one-call brief surface.",
    )
    parser.add_argument(
        "--brief-type",
        default="general",
        help="Continuity brief type.",
    )
    parser.add_argument(
        "--thread-id",
        default=DEFAULT_THREAD_ID,
        help="Seeded sample thread UUID used for the first-result brief.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    user_id = str(UUID(args.user_id))
    thread_id = str(UUID(args.thread_id))

    health = _request_json(method="GET", base_url=args.base_url, path="/healthz")
    if health.get("status") != "ok":
        raise RuntimeError(f"Alice Lite healthcheck failed: {health}")

    bootstrap_payload = _request_json(
        method="POST",
        base_url=args.base_url,
        path="/v1/workspaces/bootstrap",
        user_id=user_id,
        payload={},
    )
    workspace = bootstrap_payload.get("workspace")
    if not isinstance(workspace, dict):
        raise RuntimeError("local bootstrap response did not include a workspace")
    workspace_id = str(workspace.get("id", "")).strip()
    bootstrap_status = str(workspace.get("bootstrap_status", "")).strip()
    if workspace_id == "" or bootstrap_status != "ready":
        raise RuntimeError("local bootstrap response did not include a ready workspace")

    brief_payload = _request_json(
        method="POST",
        base_url=args.base_url,
        path="/v1/continuity/brief",
        user_id=user_id,
        payload={
            "brief_type": args.brief_type,
            "thread_id": thread_id,
            "query": args.query,
            "max_relevant_facts": 5,
            "max_recent_changes": 5,
            "max_open_loops": 5,
            "max_conflicts": 5,
            "max_timeline_highlights": 5,
        },
    )
    brief = brief_payload.get("brief")
    if not isinstance(brief, dict):
        raise RuntimeError("continuity response did not include a brief")

    print(
        json.dumps(
            {
                "status": "ok",
                "health": health["status"],
                "user_id": user_id,
                "workspace_id": workspace_id,
                "workspace_bootstrap_status": bootstrap_status,
                "brief_summary": brief.get("summary"),
                "brief_next_suggested_action": (
                    brief.get("next_suggested_action", {}).get("title")
                    if isinstance(brief.get("next_suggested_action"), dict)
                    else None
                ),
                "brief_sources": brief.get("sources", []),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
