from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER_CASES = (
    ("run_mvp_readiness_gates.py", "run_phase2_readiness_gates.py"),
    ("run_phase3_readiness_gates.py", "run_phase2_readiness_gates.py"),
    ("run_mvp_validation_matrix.py", "run_phase2_validation_matrix.py"),
    ("run_phase3_validation_matrix.py", "run_phase2_validation_matrix.py"),
)
RETIRED_TEST_FILES = (
    "tests/integration/test_mvp_readiness_gates.py",
    "tests/integration/test_mvp_validation_matrix.py",
    "tests/unit/test_phase2_gate_wrappers.py",
)


def _load_script_module(script_name: str) -> ModuleType:
    script_path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(
        f"test_{script_name.replace('.', '_')}",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("wrapper_script", "target_script"), WRAPPER_CASES)
def test_compatibility_wrapper_targets_current_carrier(
    wrapper_script: str,
    target_script: str,
) -> None:
    module = _load_script_module(wrapper_script)

    assert module.TARGET_SCRIPT == module.ROOT_DIR / "scripts" / target_script


@pytest.mark.parametrize(("wrapper_script", "target_script"), WRAPPER_CASES)
def test_compatibility_wrapper_forwards_arguments_and_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    wrapper_script: str,
    target_script: str,
) -> None:
    module = _load_script_module(wrapper_script)
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    fake_target = fake_root / "scripts" / target_script
    forwarded_args = ["--limit=3", "value with spaces"]
    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, check):  # noqa: ANN001
        captured.update(command=command, cwd=cwd, check=check)
        return SimpleNamespace(returncode=23)

    monkeypatch.setattr(module, "ROOT_DIR", fake_root)
    monkeypatch.setattr(module, "TARGET_SCRIPT", fake_target)
    monkeypatch.setattr(module, "_resolve_python_executable", lambda: "/usr/bin/python3")
    monkeypatch.setattr(module.sys, "argv", [wrapper_script, *forwarded_args])
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.main() == 23
    assert captured == {
        "command": ["/usr/bin/python3", str(fake_target), *forwarded_args],
        "cwd": fake_root,
        "check": False,
    }


def test_phase_named_contract_suites_are_retired() -> None:
    assert all(not (REPO_ROOT / relative_path).exists() for relative_path in RETIRED_TEST_FILES)
