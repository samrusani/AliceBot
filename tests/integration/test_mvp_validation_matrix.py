from __future__ import annotations

from pathlib import Path

import scripts.run_mvp_validation_matrix as validation_matrix


def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
    del cwd
    if "-c" in command and "Induced validation-matrix failure" in command[-1]:
        return validation_matrix.INDUCED_FAILURE_EXIT_CODE
    return 0


def test_matrix_sequence_contains_readiness_backend_and_web_surfaces() -> None:
    steps = validation_matrix.build_validation_matrix_steps(python_executable="/usr/bin/python3")

    assert [step.step for step in steps] == [
        validation_matrix.STEP_READINESS_GATES,
        validation_matrix.STEP_BACKEND_MATRIX,
        validation_matrix.STEP_WEB_MATRIX,
    ]

    readiness = steps[0]
    assert readiness.command == ("/usr/bin/python3", "scripts/run_mvp_readiness_gates.py")

    backend = steps[1]
    assert backend.command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *validation_matrix.BACKEND_INTEGRATION_TEST_FILES,
    )

    web = steps[2]
    assert web.command == (
        "npm",
        "--prefix",
        str(validation_matrix.WEB_DIR),
        "run",
        "test:mvp:validation-matrix",
    )
    assert web.coverage == ", ".join(validation_matrix.WEB_OPERATOR_SURFACES)


def test_exit_code_contract_is_zero_only_when_all_steps_pass() -> None:
    all_pass = [
        validation_matrix.MatrixStepResult(
            step=validation_matrix.STEP_READINESS_GATES,
            status="PASS",
            exit_code=0,
            duration_seconds=0.120,
            command=("python3", "scripts/run_mvp_readiness_gates.py"),
            coverage="acceptance_suite, latency_p95, cache_reuse, memory_quality",
            induced_failure=False,
        ),
        validation_matrix.MatrixStepResult(
            step=validation_matrix.STEP_BACKEND_MATRIX,
            status="PASS",
            exit_code=0,
            duration_seconds=9.321,
            command=("python3", "-m", "pytest", "-q"),
            coverage="backend seams",
            induced_failure=False,
        ),
    ]
    with_failure = [
        *all_pass,
        validation_matrix.MatrixStepResult(
            step=validation_matrix.STEP_WEB_MATRIX,
            status="FAIL",
            exit_code=1,
            duration_seconds=4.210,
            command=("npm", "--prefix", "apps/web", "run", "test:mvp:validation-matrix"),
            coverage="/chat, /approvals",
            induced_failure=False,
        ),
    ]

    assert validation_matrix.exit_code_for_step_results(all_pass) == 0
    assert validation_matrix.exit_code_for_step_results(with_failure) == 1


def test_induced_step_failure_reports_explicit_failing_step(capsys) -> None:
    results = validation_matrix.run_validation_matrix(
        induce_step=validation_matrix.STEP_BACKEND_MATRIX,
        execute_command=_always_pass_executor,
    )
    validation_matrix._print_step_results(results)
    output = capsys.readouterr().out

    assert len(results) == 3
    assert [result.step for result in results] == [
        validation_matrix.STEP_READINESS_GATES,
        validation_matrix.STEP_BACKEND_MATRIX,
        validation_matrix.STEP_WEB_MATRIX,
    ]
    assert results[0].status == "PASS"
    assert results[1].status == "FAIL"
    assert results[1].exit_code == validation_matrix.INDUCED_FAILURE_EXIT_CODE
    assert results[1].induced_failure is True
    assert results[2].status == "PASS"

    assert "MVP validation matrix results:" in output
    assert " - backend_integration_matrix: FAIL" in output
    assert "induced_failure: true" in output
    assert "Failing steps: backend_integration_matrix" in output
    assert validation_matrix.exit_code_for_step_results(results) == 1
