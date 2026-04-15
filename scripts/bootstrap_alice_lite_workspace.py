#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib import error, request
from uuid import UUID


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
import load_public_sample_data as public_sample_data


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_EMAIL = "builder@example.com"
DEFAULT_WORKSPACE_NAME = "Alice Lite Sample"
DEFAULT_DEVICE_LABEL = "Alice Lite Builder"
DEFAULT_DEVICE_KEY = "alice-lite-builder"
DEFAULT_THREAD_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
DEFAULT_DATABASE_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"


def _post_json(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    *,
    session_token: str | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if session_token is not None:
        headers["Authorization"] = f"Bearer {session_token}"
    http_request = request.Request(
        f"{base_url}{path}",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {detail}") from exc


def _get_json(
    base_url: str,
    path: str,
    *,
    session_token: str | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    if session_token is not None:
        headers["Authorization"] = f"Bearer {session_token}"
    http_request = request.Request(
        f"{base_url}{path}",
        headers=headers,
        method="GET",
    )
    try:
        with request.urlopen(http_request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{path} returned HTTP {exc.code}: {detail}") from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap a sample Alice Lite hosted workspace and request a "
            "one-call continuity brief against the seeded sample thread."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Alice API base URL.",
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help="Email address used for the simulated local magic-link flow.",
    )
    parser.add_argument(
        "--workspace-name",
        default=DEFAULT_WORKSPACE_NAME,
        help="Workspace name created for the sample bootstrap flow.",
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
        help="Sample thread UUID used for the first-result brief.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    health = _get_json(args.base_url, "/healthz")
    if health.get("status") != "ok":
        raise RuntimeError(f"Alice Lite healthcheck failed: {health}")

    start_payload = _post_json(
        args.base_url,
        "/v1/auth/magic-link/start",
        {"email": args.email},
    )
    challenge = start_payload.get("challenge", {})
    challenge_token = str(challenge.get("challenge_token", "")).strip()
    if challenge_token == "":
        raise RuntimeError("magic-link start response did not include a challenge token")

    verify_payload = _post_json(
        args.base_url,
        "/v1/auth/magic-link/verify",
        {
            "challenge_token": challenge_token,
            "device_label": DEFAULT_DEVICE_LABEL,
            "device_key": DEFAULT_DEVICE_KEY,
        },
    )
    session_token = str(verify_payload.get("session_token", "")).strip()
    if session_token == "":
        raise RuntimeError("magic-link verify response did not include a session token")
    user_account_id = str(verify_payload["user_account"]["id"])

    fixture = public_sample_data._load_fixture(public_sample_data.DEFAULT_FIXTURE_PATH)
    seeded_user_id = UUID(user_account_id)
    with user_connection(
        os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        seeded_user_id,
    ) as conn:
        store = ContinuityStore(conn)
        public_sample_data._ensure_user(
            store,
            user_id=seeded_user_id,
            email=args.email,
            display_name=str(verify_payload["user_account"]["display_name"]),
        )
        if not public_sample_data._already_seeded(store, fixture_id=str(fixture["fixture_id"])):
            public_sample_data._seed_fixture(store, fixture=fixture)

    workspace_payload = _post_json(
        args.base_url,
        "/v1/workspaces",
        {"name": args.workspace_name},
        session_token=session_token,
    )
    workspace = workspace_payload.get("workspace", {})
    workspace_id = str(workspace.get("id", "")).strip()
    if workspace_id == "":
        raise RuntimeError("workspace create response did not include a workspace id")

    bootstrap_payload = _post_json(
        args.base_url,
        "/v1/workspaces/bootstrap",
        {"workspace_id": workspace_id},
        session_token=session_token,
    )
    brief_payload = _post_json(
        args.base_url,
        "/v1/continuity/brief",
        {
            "brief_type": args.brief_type,
            "thread_id": args.thread_id,
            "query": args.query,
            "max_relevant_facts": 5,
            "max_recent_changes": 5,
            "max_open_loops": 5,
            "max_conflicts": 5,
            "max_timeline_highlights": 5,
        },
        session_token=session_token,
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "health": health["status"],
                "user_account_id": user_account_id,
                "workspace_id": workspace_id,
                "workspace_bootstrap_status": bootstrap_payload["workspace"]["bootstrap_status"],
                "brief_summary": brief_payload["brief"]["summary"],
                "brief_next_suggested_action": brief_payload["brief"]["next_suggested_action"]["title"],
                "brief_sources": brief_payload["brief"]["sources"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
