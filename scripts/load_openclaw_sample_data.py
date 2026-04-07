#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from alicebot_api.db import user_connection
from alicebot_api.openclaw_import import import_openclaw_source
from alicebot_api.store import ContinuityStore


DEFAULT_DATABASE_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
DEFAULT_AUTH_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_SOURCE_PATH = REPO_ROOT / "fixtures" / "openclaw" / "workspace_v1.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import OpenClaw sample workspace data into Alice continuity objects."
    )
    parser.add_argument(
        "--source",
        default=os.getenv("OPENCLAW_SAMPLE_DATA_PATH", str(DEFAULT_SOURCE_PATH)),
        help="Path to an OpenClaw workspace/export file or directory.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Database URL used for writes.",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("ALICEBOT_AUTH_USER_ID", DEFAULT_AUTH_USER_ID),
        help="User ID to own imported OpenClaw data.",
    )
    parser.add_argument(
        "--user-email",
        default=os.getenv("ALICEBOT_IMPORT_USER_EMAIL", "openclaw-sample@example.com"),
        help="Email for auto-created user when --user-id is not found.",
    )
    parser.add_argument(
        "--display-name",
        default=os.getenv("ALICEBOT_IMPORT_USER_DISPLAY_NAME", "OpenClaw Sample User"),
        help="Display name for auto-created user when --user-id is not found.",
    )
    return parser.parse_args()


def _ensure_user(store: ContinuityStore, *, user_id: UUID, email: str, display_name: str) -> None:
    with store.conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
        exists = cur.fetchone() is not None
    if exists:
        return
    store.create_user(user_id, email, display_name)


def main() -> int:
    args = _parse_args()
    source_path = Path(args.source).expanduser().resolve()
    user_id = UUID(str(args.user_id))

    with user_connection(args.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        _ensure_user(
            store,
            user_id=user_id,
            email=str(args.user_email),
            display_name=str(args.display_name),
        )
        summary = import_openclaw_source(
            store,
            user_id=user_id,
            source=source_path,
        )

    print(
        json.dumps(
            {
                **summary,
                "user_id": str(user_id),
                "source_path": str(source_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
