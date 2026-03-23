from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]

MVP_ALIAS_CASES = (
    ("run_mvp_acceptance.py", "run_phase2_acceptance.py"),
    ("run_mvp_readiness_gates.py", "run_phase2_readiness_gates.py"),
    ("run_mvp_validation_matrix.py", "run_phase2_validation_matrix.py"),
)


PHASE2_CANONICAL_SCRIPTS = (
    "run_phase2_acceptance.py",
    "run_phase2_readiness_gates.py",
    "run_phase2_validation_matrix.py",
)


def _load_script_module(script_name: str) -> ModuleType:
    script_path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(f"test_{script_name.replace('.', '_')}", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("alias_script", "target_script"), MVP_ALIAS_CASES)
def test_mvp_alias_target_mapping_is_stable(alias_script: str, target_script: str) -> None:
    module = _load_script_module(alias_script)

    assert module.TARGET_SCRIPT == module.ROOT_DIR / "scripts" / target_script


@pytest.mark.parametrize(("alias_script", "target_script"), MVP_ALIAS_CASES)
def test_mvp_alias_main_forwards_args_and_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, alias_script: str, target_script: str
) -> None:
    module = _load_script_module(alias_script)
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    fake_target = fake_root / "scripts" / target_script
    fake_python = str(fake_root / ".venv" / "bin" / "python")
    forwarded_args = ["--dry-run", "--limit=3", "value with spaces", "--flag=true"]
    call: dict[str, object] = {}

    def fake_run(command, cwd, check):  # noqa: ANN001
        call["command"] = command
        call["cwd"] = cwd
        call["check"] = check
        return SimpleNamespace(returncode=23)

    monkeypatch.setattr(module, "ROOT_DIR", fake_root)
    monkeypatch.setattr(module, "TARGET_SCRIPT", fake_target)
    monkeypatch.setattr(module, "_resolve_python_executable", lambda: fake_python)
    monkeypatch.setattr(
        module.sys,
        "argv",
        [str(REPO_ROOT / "scripts" / alias_script), *forwarded_args],
    )
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.main() == 23
    assert call == {
        "command": [fake_python, str(fake_target), *forwarded_args],
        "cwd": fake_root,
        "check": False,
    }


@pytest.mark.parametrize(("alias_script", "_target_script"), MVP_ALIAS_CASES)
def test_mvp_alias_resolve_python_executable_prefers_repo_venv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, alias_script: str, _target_script: str
) -> None:
    module = _load_script_module(alias_script)
    fake_root = tmp_path / "repo"
    venv_python = fake_root / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("#!/usr/bin/env python3\n")

    monkeypatch.setattr(module, "ROOT_DIR", fake_root)
    monkeypatch.setattr(module.sys, "executable", "/usr/bin/system-python")

    assert module._resolve_python_executable() == str(venv_python)


@pytest.mark.parametrize(("alias_script", "_target_script"), MVP_ALIAS_CASES)
def test_mvp_alias_resolve_python_executable_falls_back_to_sys_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, alias_script: str, _target_script: str
) -> None:
    module = _load_script_module(alias_script)
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    fallback_python = "/usr/local/bin/fallback-python"

    monkeypatch.setattr(module, "ROOT_DIR", fake_root)
    monkeypatch.setattr(module.sys, "executable", fallback_python)

    assert module._resolve_python_executable() == fallback_python


@pytest.mark.parametrize("phase2_script", PHASE2_CANONICAL_SCRIPTS)
def test_phase2_scripts_do_not_delegate_to_mvp_scripts(phase2_script: str) -> None:
    script_path = REPO_ROOT / "scripts" / phase2_script
    script_text = script_path.read_text()

    assert "run_mvp_" not in script_text


def test_phase2_readiness_gate_calls_phase2_acceptance() -> None:
    script_path = REPO_ROOT / "scripts" / "run_phase2_readiness_gates.py"
    script_text = script_path.read_text()

    assert "scripts/run_phase2_acceptance.py" in script_text


def test_phase2_validation_matrix_calls_phase2_readiness() -> None:
    script_path = REPO_ROOT / "scripts" / "run_phase2_validation_matrix.py"
    script_text = script_path.read_text()

    assert "scripts/run_phase2_readiness_gates.py" in script_text
