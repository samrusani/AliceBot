from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module(script_name: str) -> ModuleType:
    script_path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(f"test_{script_name.replace('.', '_')}", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase4_acceptance_is_not_phase3_wrapper_delegate() -> None:
    script_text = (REPO_ROOT / "scripts" / "run_phase4_acceptance.py").read_text()

    assert "TARGET_SCRIPT" not in script_text
    assert "scripts/run_phase3_acceptance.py" not in script_text


def test_phase4_readiness_is_not_phase3_wrapper_delegate() -> None:
    script_text = (REPO_ROOT / "scripts" / "run_phase4_readiness_gates.py").read_text()

    assert "TARGET_SCRIPT" not in script_text


def test_phase4_acceptance_includes_canonical_magnesium_mapping() -> None:
    module = _load_script_module("run_phase4_acceptance.py")

    scenario_ids = [scenario.scenario for scenario in module.ACCEPTANCE_SCENARIOS]
    assert scenario_ids == [
        "response_memory",
        "capture_resumption",
        "approval_execution",
        "magnesium_reorder",
    ]

    magnesium = next(
        scenario for scenario in module.ACCEPTANCE_SCENARIOS if scenario.scenario == "magnesium_reorder"
    )
    assert "canonical MVP ship gate" in magnesium.evidence
    assert (
        magnesium.node_id
        == "tests/integration/test_mvp_acceptance_suite.py::"
        "test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence"
    )


def test_phase4_readiness_gate_contract_sequence_is_stable() -> None:
    module = _load_script_module("run_phase4_readiness_gates.py")

    gate_steps = module.build_readiness_gate_steps(python_executable="/usr/bin/python3")
    assert [gate.gate for gate in gate_steps] == [
        module.GATE_PHASE4_ACCEPTANCE,
        module.GATE_MAGNESIUM_SHIP_GATE,
        module.GATE_PHASE3_COMPAT,
    ]

    assert gate_steps[0].command == ("/usr/bin/python3", "scripts/run_phase4_acceptance.py")
    assert gate_steps[1].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        module.MAGNESIUM_NODE_ID,
    )
    assert gate_steps[2].command == ("/usr/bin/python3", "scripts/run_phase3_readiness_gates.py")


def test_phase4_release_candidate_rehearsal_contract_sequence_is_stable() -> None:
    module = _load_script_module("run_phase4_release_candidate.py")

    steps = module.build_release_candidate_steps(python_executable="/usr/bin/python3")
    assert [step.step for step in steps] == [
        module.STEP_CONTROL_DOC_TRUTH,
        module.STEP_PHASE4_ACCEPTANCE,
        module.STEP_PHASE4_READINESS,
        module.STEP_PHASE4_VALIDATION_MATRIX,
        module.STEP_PHASE3_COMPAT_VALIDATION,
        module.STEP_PHASE2_COMPAT_VALIDATION,
        module.STEP_MVP_COMPAT_VALIDATION,
    ]

    assert steps[0].command == ("/usr/bin/python3", "scripts/check_control_doc_truth.py")
    assert steps[1].command == ("/usr/bin/python3", "scripts/run_phase4_acceptance.py")
    assert steps[2].command == ("/usr/bin/python3", "scripts/run_phase4_readiness_gates.py")
    assert steps[3].command == ("/usr/bin/python3", "scripts/run_phase4_validation_matrix.py")
    assert steps[4].command == ("/usr/bin/python3", "scripts/run_phase3_validation_matrix.py")
    assert steps[5].command == ("/usr/bin/python3", "scripts/run_phase2_validation_matrix.py")
    assert steps[6].command == ("/usr/bin/python3", "scripts/run_mvp_validation_matrix.py")


def test_phase4_release_candidate_lock_timeout_exit_contract_is_explicit(
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module("run_phase4_release_candidate.py")
    step_result = module.ReleaseCandidateStepResult(
        step=module.STEP_CONTROL_DOC_TRUTH,
        description="Validate control-doc truth markers.",
        status="PASS",
        exit_code=0,
        duration_seconds=0.1,
        command=("/usr/bin/python3", "scripts/check_control_doc_truth.py"),
        induced_failure=False,
    )

    def _fake_run_release_candidate(*, induce_step=None, execute_command=module._execute_command):
        del induce_step, execute_command
        return [step_result]

    def _fake_write_release_candidate_summary(**kwargs):
        del kwargs
        raise module.ArchiveIndexLockTimeoutError(
            "Timed out acquiring archive index lock at artifacts/release/archive/index.lock after 0.02s."
        )

    monkeypatch.setattr(module, "run_release_candidate", _fake_run_release_candidate)
    monkeypatch.setattr(module, "write_release_candidate_summary", _fake_write_release_candidate_summary)

    exit_code = module.main([])
    assert exit_code == module.ARCHIVE_INDEX_LOCK_TIMEOUT_EXIT_CODE
    stdout = capsys.readouterr().out
    assert "Phase 4 release-candidate archive update failed:" in stdout
    assert "Timed out acquiring archive index lock" in stdout


def test_phase4_mvp_exit_manifest_generator_contract_is_stable() -> None:
    module = _load_script_module("generate_phase4_mvp_exit_manifest.py")

    assert module.MANIFEST_ARTIFACT_VERSION == "phase4_mvp_exit_manifest.v1"
    assert module.DEFAULT_MANIFEST_PATH == (
        REPO_ROOT / "artifacts" / "release" / "phase4_mvp_exit_manifest.json"
    )
    assert module.REQUIRED_COMPATIBILITY_COMMANDS == (
        "python3 scripts/run_phase4_validation_matrix.py",
        "python3 scripts/run_phase3_validation_matrix.py",
        "python3 scripts/run_phase2_validation_matrix.py",
        "python3 scripts/run_mvp_validation_matrix.py",
    )


def test_phase4_mvp_exit_manifest_verifier_default_path_contract_is_stable() -> None:
    module = _load_script_module("verify_phase4_mvp_exit_manifest.py")

    assert module.DEFAULT_MANIFEST_PATH == (
        REPO_ROOT / "artifacts" / "release" / "phase4_mvp_exit_manifest.json"
    )
