from __future__ import annotations

import logging
import os
from pathlib import Path
import subprocess
import sys

from workers.alicebot_worker.main import run


def test_run_logs_scaffold_message(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="alicebot.worker"):
        run()

    assert caplog.messages == [
        "Worker scaffold initialized; no background jobs are in scope for this sprint."
    ]


def test_module_entrypoint_logs_scaffold_message() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    pythonpath_entries = [str(repo_root / "apps" / "api" / "src"), str(repo_root / "workers")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)

    result = subprocess.run(
        [sys.executable, "-m", "alicebot_worker.main"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Worker scaffold initialized; no background jobs are in scope for this sprint." in result.stderr
