from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_SCRIPT = REPO_ROOT / "scripts" / "run_reference_agent_examples_demo.py"


def test_reference_agent_examples_demo_runs_python_and_typescript_examples() -> None:
    completed = subprocess.run(
        [sys.executable, str(DEMO_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "pass"
    assert payload["contract_fixture"] == "fixtures/reference_integrations/continuity_brief_agent_handoff_v1.json"
    assert payload["outputs_match"] is True
    assert payload["python_example"]["returncode"] == 0
    assert payload["typescript_example"]["returncode"] == 0
    assert payload["python_example"]["stdout"]["brief_type"] == "agent_handoff"
    assert payload["python_example"]["stdout"]["next_suggested_action"] == "Next Action: Run release smoke"
    assert payload["typescript_example"]["stdout"] == payload["python_example"]["stdout"]
