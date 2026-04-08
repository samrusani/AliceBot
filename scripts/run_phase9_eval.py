#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID


REPO_ROOT = Path(__file__).resolve().parents[1]
_VENV_REEXEC_ENV = "ALICEBOT_PHASE9_EVAL_REEXEC"


def _maybe_reexec_into_repo_venv() -> None:
    if os.getenv(_VENV_REEXEC_ENV) == "1":
        return

    venv_python = (REPO_ROOT / ".venv" / "bin" / "python").resolve()
    if not venv_python.exists():
        return

    current_python = Path(sys.executable).expanduser().resolve()
    if current_python == venv_python:
        return

    os.environ[_VENV_REEXEC_ENV] = "1"
    os.execv(
        str(venv_python),
        [
            str(venv_python),
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ],
    )


_maybe_reexec_into_repo_venv()

API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from alicebot_api.db import user_connection
from alicebot_api.retrieval_evaluation import run_phase9_evaluation, write_phase9_evaluation_report
from alicebot_api.store import ContinuityStore


DEFAULT_DATABASE_URL = "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot"
DEFAULT_AUTH_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_REPORT_PATH = REPO_ROOT / "eval" / "reports" / "phase9_eval_latest.json"
DEFAULT_OPENCLAW_SOURCE = REPO_ROOT / "fixtures" / "openclaw" / "workspace_v1.json"
DEFAULT_MARKDOWN_SOURCE = REPO_ROOT / "fixtures" / "importers" / "markdown" / "workspace_v1.md"
DEFAULT_CHATGPT_SOURCE = REPO_ROOT / "fixtures" / "importers" / "chatgpt" / "workspace_v1.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase 9 importer and continuity evaluation harness and write a baseline report."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="Database URL used for writes and reads.",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("ALICEBOT_AUTH_USER_ID", DEFAULT_AUTH_USER_ID),
        help="User ID to own the evaluation run data.",
    )
    parser.add_argument(
        "--user-email",
        default=os.getenv("ALICEBOT_IMPORT_USER_EMAIL", "phase9-eval@example.com"),
        help="Email for auto-created user when --user-id is not found.",
    )
    parser.add_argument(
        "--display-name",
        default=os.getenv("ALICEBOT_IMPORT_USER_DISPLAY_NAME", "Phase9 Eval User"),
        help="Display name for auto-created user when --user-id is not found.",
    )
    parser.add_argument(
        "--openclaw-source",
        default=str(DEFAULT_OPENCLAW_SOURCE),
        help="Path to OpenClaw fixture source.",
    )
    parser.add_argument(
        "--markdown-source",
        default=str(DEFAULT_MARKDOWN_SOURCE),
        help="Path to markdown fixture source.",
    )
    parser.add_argument(
        "--chatgpt-source",
        default=str(DEFAULT_CHATGPT_SOURCE),
        help="Path to ChatGPT fixture source.",
    )
    parser.add_argument(
        "--report-path",
        default=str(DEFAULT_REPORT_PATH),
        help="Output JSON report path.",
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
    user_id = UUID(str(args.user_id))

    with user_connection(args.database_url, user_id) as conn:
        store = ContinuityStore(conn)
        _ensure_user(
            store,
            user_id=user_id,
            email=str(args.user_email),
            display_name=str(args.display_name),
        )

        report = run_phase9_evaluation(
            store,
            user_id=user_id,
            openclaw_source=Path(str(args.openclaw_source)).expanduser().resolve(),
            markdown_source=Path(str(args.markdown_source)).expanduser().resolve(),
            chatgpt_source=Path(str(args.chatgpt_source)).expanduser().resolve(),
        )

    output_path = write_phase9_evaluation_report(
        report=report,
        report_path=Path(str(args.report_path)).expanduser().resolve(),
    )

    print(
        json.dumps(
            {
                "status": report["summary"]["status"],
                "report_path": str(output_path),
                "summary": report["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
