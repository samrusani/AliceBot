from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_SCRIPT = REPO_ROOT / "scripts" / "use_alice_with_openclaw.py"


def test_openclaw_one_command_demo_runs_import_recall_resume_with_idempotent_replay(migrated_database_urls) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(DEMO_SCRIPT),
            "--database-url",
            migrated_database_urls["app"],
            "--display-name",
            "OpenClaw Demo Test User",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "pass"
    assert payload["import"]["first"]["status"] == "ok"
    assert payload["import"]["second"]["status"] == "noop"
    assert payload["after"]["recall_returned_count"] >= 1
    assert payload["after"]["resume_last_decision_source_kind"] == "openclaw_import"
    assert payload["after"]["resume_next_action_source_kind"] == "openclaw_import"
    assert payload["after"]["resume_last_decision_source_label"] == "OpenClaw"
    assert payload["after"]["resume_next_action_source_label"] == "OpenClaw"
    assert payload["after"]["recall_source_labels"] == ["OpenClaw"]
    assert all(payload["checks"].values())
