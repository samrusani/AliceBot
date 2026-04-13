from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_hermes_bridge_demo.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_hermes_bridge_demo_test_module", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bridge_demo_runs_provider_and_mcp_smokes_in_order(monkeypatch, capsys) -> None:
    module = _load_module()
    commands: list[list[str]] = []

    def _fake_run(command, cwd, capture_output, text, check):  # type: ignore[no-untyped-def]
        del cwd, capture_output, text, check
        commands.append(list(command))
        command_text = " ".join(command)
        if "run_hermes_memory_provider_smoke.py" in command_text:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "structural": {
                            "alice_registered": True,
                            "single_external_enforced": True,
                            "bridge_status": {"ready": True},
                        }
                    }
                ),
                stderr="",
            )
        if "run_hermes_mcp_smoke.py" in command_text:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "recall_items": 1,
                        "open_loop_count": 1,
                        "capture_candidate_count": 2,
                        "capture_auto_saved_count": 1,
                        "capture_review_queued_count": 1,
                        "review_apply_resolved_action": "confirm",
                    }
                ),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main(["--python-command", "python3", "--database-url", "postgresql://demo"])
    assert exit_code == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "pass"
    assert payload["recommended_path"] == "provider_plus_mcp"
    assert payload["fallback_path"] == "mcp_only"

    assert len(commands) == 2
    assert any("run_hermes_memory_provider_smoke.py" in part for part in commands[0])
    assert any("run_hermes_mcp_smoke.py" in part for part in commands[1])
    assert "--database-url" in commands[1]


def test_bridge_demo_fails_when_mcp_smoke_output_is_incomplete(monkeypatch, capsys) -> None:
    module = _load_module()

    def _fake_run(command, cwd, capture_output, text, check):  # type: ignore[no-untyped-def]
        del cwd, capture_output, text, check
        command_text = " ".join(command)
        if "run_hermes_memory_provider_smoke.py" in command_text:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"structural": {"bridge_status": {"ready": True}}}),
                stderr="",
            )
        if "run_hermes_mcp_smoke.py" in command_text:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"recall_items": 1}),
                stderr="",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main(["--python-command", "python3"])
    assert exit_code == 1

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "fail"
