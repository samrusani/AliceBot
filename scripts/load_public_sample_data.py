#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any
from uuid import UUID


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


DEFAULT_DATABASE_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
DEFAULT_AUTH_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_FIXTURE_PATH = REPO_ROOT / "fixtures" / "public_sample_data" / "continuity_v1.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load deterministic public-core sample continuity data."
    )
    parser.add_argument(
        "--fixture",
        default=os.getenv("PUBLIC_SAMPLE_DATA_PATH", str(DEFAULT_FIXTURE_PATH)),
        help="Path to a sample-data fixture JSON file.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Database URL used for writes.",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("ALICEBOT_AUTH_USER_ID", DEFAULT_AUTH_USER_ID),
        help="User ID to own the sample data.",
    )
    return parser.parse_args()


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"fixture file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fixture root must be a JSON object")
    if not isinstance(payload.get("fixture_id"), str) or payload["fixture_id"].strip() == "":
        raise ValueError("fixture_id must be a non-empty string")
    if not isinstance(payload.get("objects"), list) or len(payload["objects"]) == 0:
        raise ValueError("objects must be a non-empty list")
    return payload


def _ensure_user(store: ContinuityStore, *, user_id: UUID, email: str, display_name: str) -> None:
    with store.conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
        exists = cur.fetchone() is not None
    if exists:
        return
    store.create_user(user_id, email, display_name)


def _already_seeded(store: ContinuityStore, *, fixture_id: str) -> bool:
    for row in store.list_continuity_recall_candidates():
        provenance = row["provenance"]
        if isinstance(provenance, dict) and provenance.get("sample_fixture") == fixture_id:
            return True
    return False


def _seed_fixture(
    store: ContinuityStore,
    *,
    fixture: dict[str, Any],
) -> int:
    fixture_id = str(fixture["fixture_id"])
    created = 0

    for item in fixture["objects"]:
        if not isinstance(item, dict):
            raise ValueError("each fixture object entry must be a JSON object")

        raw_content = str(item["raw_content"])
        explicit_signal = item.get("explicit_signal")
        object_type = str(item["object_type"])
        status = str(item["status"])
        title = str(item["title"])
        body = item["body"]
        confidence = float(item.get("confidence", 0.9))
        provenance = dict(item.get("provenance", {}))

        provenance["sample_fixture"] = fixture_id
        provenance["source_kind"] = "public_sample_fixture"

        capture = store.create_continuity_capture_event(
            raw_content=raw_content,
            explicit_signal=explicit_signal,
            admission_posture="DERIVED",
            admission_reason=f"sample_fixture_{fixture_id}",
        )

        store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type=object_type,
            status=status,
            title=title,
            body=body,
            provenance=provenance,
            confidence=confidence,
        )
        created += 1

    return created


def main() -> int:
    args = _parse_args()
    fixture_path = Path(args.fixture)
    fixture = _load_fixture(fixture_path)
    fixture_id = str(fixture["fixture_id"])
    user_id = UUID(str(args.user_id))

    fixture_user = fixture.get("user") if isinstance(fixture.get("user"), dict) else {}
    email = str(fixture_user.get("email", "public-sample@example.com"))
    display_name = str(fixture_user.get("display_name", "Public Sample User"))

    with user_connection(args.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        _ensure_user(store, user_id=user_id, email=email, display_name=display_name)

        if _already_seeded(store, fixture_id=fixture_id):
            print(
                json.dumps(
                    {
                        "status": "noop",
                        "reason": "fixture_already_loaded",
                        "fixture_id": fixture_id,
                        "user_id": str(user_id),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        created_count = _seed_fixture(store, fixture=fixture)

    print(
        json.dumps(
            {
                "status": "ok",
                "fixture_id": fixture_id,
                "user_id": str(user_id),
                "created_object_count": created_count,
                "fixture_path": str(fixture_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
