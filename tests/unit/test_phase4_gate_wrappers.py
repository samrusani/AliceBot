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
