#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import ContinuityRecallQueryInput, ContinuityResumptionBriefRequestInput
from alicebot_api.db import user_connection
from alicebot_api.openclaw_import import import_openclaw_source
from alicebot_api.store import ContinuityStore

DEFAULT_DATABASE_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
DEFAULT_SOURCE_PATH = REPO_ROOT / "fixtures" / "openclaw" / "workspace_v1.json"
DEFAULT_THREAD_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
DEFAULT_PROJECT = "Alice Public Core"
DEFAULT_QUERY = "MCP tool surface"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one-command OpenClaw integration demo: before recall/resume, import, idempotent replay, "
            "and after recall/resume verification."
        )
    )
    parser.add_argument(
        "--source",
        default=os.getenv("OPENCLAW_SAMPLE_DATA_PATH", str(DEFAULT_SOURCE_PATH)),
        help="Path to an OpenClaw workspace/export file or directory.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Database URL used for reads/writes.",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("ALICEBOT_AUTH_USER_ID"),
        help="Optional user ID. If omitted, a new UUID is generated for isolated demo output.",
    )
    parser.add_argument(
        "--user-email",
        default=None,
        help="Optional user email. Defaults to openclaw-demo-<user_id>@example.com.",
    )
    parser.add_argument(
        "--display-name",
        default="OpenClaw Demo User",
        help="Display name for auto-created user when needed.",
    )
    parser.add_argument(
        "--thread-id",
        default=DEFAULT_THREAD_ID,
        help="Thread UUID used for recall/resume verification.",
    )
    parser.add_argument(
        "--project",
        default=DEFAULT_PROJECT,
        help="Project filter used for recall verification.",
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help="Recall query text used before and after import.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Recall limit.",
    )
    parser.add_argument(
        "--max-recent-changes",
        type=int,
        default=10,
        help="Resume max_recent_changes parameter.",
    )
    parser.add_argument(
        "--max-open-loops",
        type=int,
        default=10,
        help="Resume max_open_loops parameter.",
    )
    return parser.parse_args()


def _ensure_user(store: ContinuityStore, *, user_id: UUID, email: str, display_name: str) -> None:
    with store.conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
        exists = cur.fetchone() is not None
    if exists:
        return
    store.create_user(user_id, email, display_name)


def _ensure_user_committed(*, database_url: str, user_id: UUID, email: str, display_name: str) -> None:
    with user_connection(database_url, user_id) as conn:
        store = ContinuityStore(conn)
        _ensure_user(store, user_id=user_id, email=email, display_name=display_name)


def _source_kinds(items: list[dict[str, object]]) -> list[str]:
    kinds: list[str] = []
    for item in items:
        provenance = item.get("provenance")
        if not isinstance(provenance, dict):
            continue
        source_kind = provenance.get("source_kind")
        if isinstance(source_kind, str):
            kinds.append(source_kind)
    return sorted(set(kinds))


def _source_labels(items: list[dict[str, object]]) -> list[str]:
    labels: list[str] = []
    for item in items:
        provenance = item.get("provenance")
        if not isinstance(provenance, dict):
            continue
        source_label = provenance.get("source_label")
        if isinstance(source_label, str):
            labels.append(source_label)
    return sorted(set(labels))


def _provenance_value(item: dict[str, object] | None, key: str) -> str | None:
    if not isinstance(item, dict):
        return None
    provenance = item.get("provenance")
    if not isinstance(provenance, dict):
        return None
    value = provenance.get(key)
    return value if isinstance(value, str) else None


def main() -> int:
    args = _parse_args()

    source_path = Path(args.source).expanduser().resolve()
    user_id = UUID(str(args.user_id)) if args.user_id else uuid4()
    user_email = args.user_email or f"openclaw-demo-{user_id}@example.com"
    thread_id = UUID(str(args.thread_id))

    _ensure_user_committed(
        database_url=args.database_url,
        user_id=user_id,
        email=user_email,
        display_name=str(args.display_name),
    )

    with user_connection(args.database_url, user_id) as conn:
        store = ContinuityStore(conn)

        recall_before = query_continuity_recall(
            store,
            user_id=user_id,
            request=ContinuityRecallQueryInput(
                thread_id=thread_id,
                project=args.project,
                query=args.query,
                limit=args.limit,
            ),
        )
        resume_before = compile_continuity_resumption_brief(
            store,
            user_id=user_id,
            request=ContinuityResumptionBriefRequestInput(
                thread_id=thread_id,
                max_recent_changes=args.max_recent_changes,
                max_open_loops=args.max_open_loops,
            ),
        )

        first_import = import_openclaw_source(
            store,
            user_id=user_id,
            source=source_path,
        )
        second_import = import_openclaw_source(
            store,
            user_id=user_id,
            source=source_path,
        )

        recall_after = query_continuity_recall(
            store,
            user_id=user_id,
            request=ContinuityRecallQueryInput(
                thread_id=thread_id,
                project=args.project,
                query=args.query,
                limit=args.limit,
            ),
        )
        resume_after = compile_continuity_resumption_brief(
            store,
            user_id=user_id,
            request=ContinuityResumptionBriefRequestInput(
                thread_id=thread_id,
                max_recent_changes=args.max_recent_changes,
                max_open_loops=args.max_open_loops,
            ),
        )

    recall_after_items = recall_after["items"]
    resume_after_brief = resume_after["brief"]
    last_decision_item = resume_after_brief["last_decision"]["item"]
    next_action_item = resume_after_brief["next_action"]["item"]

    checks = {
        "first_import_ok": first_import["status"] == "ok",
        "first_import_has_openclaw_source_kind": first_import["provenance_source_kind"] == "openclaw_import",
        "first_import_has_openclaw_source_label": first_import.get("provenance_source_label") == "OpenClaw",
        "second_import_noop": second_import["status"] == "noop",
        "second_import_skipped_all_candidates": second_import["skipped_duplicates"] == second_import["total_candidates"],
        "recall_after_includes_openclaw_source": any(
            isinstance(item.get("provenance"), dict)
            and item["provenance"].get("source_kind") == "openclaw_import"
            and item["provenance"].get("source_label") == "OpenClaw"
            for item in recall_after_items
        ),
        "resume_after_last_decision_openclaw": isinstance(last_decision_item, dict)
        and isinstance(last_decision_item.get("provenance"), dict)
        and last_decision_item["provenance"].get("source_kind") == "openclaw_import"
        and last_decision_item["provenance"].get("source_label") == "OpenClaw",
        "resume_after_next_action_openclaw": isinstance(next_action_item, dict)
        and isinstance(next_action_item.get("provenance"), dict)
        and next_action_item["provenance"].get("source_kind") == "openclaw_import"
        and next_action_item["provenance"].get("source_label") == "OpenClaw",
    }

    payload = {
        "status": "pass" if all(checks.values()) else "fail",
        "source_path": str(source_path),
        "user_id": str(user_id),
        "user_email": user_email,
        "before": {
            "recall_returned_count": recall_before["summary"]["returned_count"],
            "resume_last_decision_present": resume_before["brief"]["last_decision"]["item"] is not None,
            "resume_next_action_present": resume_before["brief"]["next_action"]["item"] is not None,
        },
        "import": {
            "first": first_import,
            "second": second_import,
        },
        "after": {
            "recall_returned_count": recall_after["summary"]["returned_count"],
            "recall_source_kinds": _source_kinds(recall_after_items),
            "recall_source_labels": _source_labels(recall_after_items),
            "resume_last_decision_source_kind": _provenance_value(last_decision_item, "source_kind"),
            "resume_last_decision_source_label": _provenance_value(last_decision_item, "source_label"),
            "resume_next_action_source_kind": _provenance_value(next_action_item, "source_kind"),
            "resume_next_action_source_label": _provenance_value(next_action_item, "source_label"),
        },
        "checks": checks,
    }

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
