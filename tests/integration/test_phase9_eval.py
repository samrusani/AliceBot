from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID, uuid4

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_SCRIPT = REPO_ROOT / "scripts" / "run_phase9_eval.py"


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def test_phase9_eval_script_generates_report_with_expected_metrics(migrated_database_urls, tmp_path: Path) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="phase9-eval@example.com")
    report_path = tmp_path / "phase9_eval_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(EVAL_SCRIPT),
            "--database-url",
            migrated_database_urls["app"],
            "--user-id",
            str(user_id),
            "--report-path",
            str(report_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    stdout_payload = json.loads(completed.stdout)
    assert stdout_payload["status"] == "pass"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report["schema_version"] == "phase9_eval_v1"
    assert summary["status"] == "pass"
    assert summary["importer_count"] == 3
    assert summary["importer_success_rate"] == 1.0
    assert summary["duplicate_posture_rate"] == 1.0
    assert summary["recall_precision_at_1"] == 1.0
    assert summary["resumption_usefulness_rate"] == 1.0
    assert summary["correction_effectiveness_rate"] == 1.0
    assert len(report["importer_runs"]) == 3
