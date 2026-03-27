from __future__ import annotations

from pathlib import Path

import scripts.run_phase4_validation_matrix as validation_matrix


def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
    del cwd
    if "-c" in command and "Induced phase4 validation failure" in command[-1]:
        return validation_matrix.INDUCED_FAILURE_EXIT_CODE
    return 0


def test_matrix_sequence_contains_canonical_magnesium_and_compatibility_steps() -> None:
    steps = validation_matrix.build_validation_matrix_steps(python_executable="/usr/bin/python3")

    assert [step.step for step in steps] == [
        validation_matrix.STEP_CONTROL_DOC_TRUTH,
        validation_matrix.STEP_PHASE4_ACCEPTANCE,
        validation_matrix.STEP_PHASE4_READINESS,
        validation_matrix.STEP_PHASE4_MAGNESIUM,
        validation_matrix.STEP_PHASE4_SCENARIOS,
        validation_matrix.STEP_PHASE4_WEB,
        validation_matrix.STEP_PHASE3_COMPAT,
        validation_matrix.STEP_PHASE2_COMPAT,
        validation_matrix.STEP_MVP_COMPAT,
    ]

    assert steps[0].command == ("/usr/bin/python3", "scripts/check_control_doc_truth.py")
    assert steps[1].command == ("/usr/bin/python3", "scripts/run_phase4_acceptance.py")
    assert steps[2].command == ("/usr/bin/python3", "scripts/run_phase4_readiness_gates.py")
    assert steps[3].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        validation_matrix.PHASE4_MAGNESIUM_NODE_ID,
    )
    assert steps[4].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *validation_matrix.PHASE4_SCENARIO_NODE_IDS,
    )
    assert steps[5].command == validation_matrix.PHASE4_WEB_COMMAND
    assert steps[6].command == ("/usr/bin/python3", "scripts/run_phase3_validation_matrix.py")
    assert steps[7].command == ("/usr/bin/python3", "scripts/run_phase2_validation_matrix.py")
    assert steps[8].command == ("/usr/bin/python3", "scripts/run_mvp_validation_matrix.py")


def test_induced_step_failure_reports_explicit_failing_step(capsys) -> None:
    results = validation_matrix.run_validation_matrix(
        induce_step=validation_matrix.STEP_PHASE4_MAGNESIUM,
        execute_command=_always_pass_executor,
    )
    validation_matrix._print_step_results(results)
    output = capsys.readouterr().out

    assert results[3].step == validation_matrix.STEP_PHASE4_MAGNESIUM
    assert results[3].status == "FAIL"
    assert results[3].exit_code == validation_matrix.INDUCED_FAILURE_EXIT_CODE
    assert results[3].induced_failure is True
    assert all(result.status == "PASS" for result in results[:3])
    assert all(result.status == "PASS" for result in results[4:])

    assert "Phase 4 validation matrix results:" in output
    assert " - phase4_magnesium_ship_gate: FAIL" in output
    assert "induced_failure: true" in output
    assert "Failing steps: phase4_magnesium_ship_gate" in output
    assert validation_matrix.exit_code_for_step_results(results) == 1
