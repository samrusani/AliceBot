from pathlib import Path

import scripts.run_phase2_validation_matrix as validation_matrix


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_validation_matrix_covers_current_core_only() -> None:
    steps = validation_matrix.build_validation_matrix_steps(
        python_executable="/usr/bin/python3"
    )

    assert [step.step for step in steps] == list(validation_matrix.STEP_IDS)
    assert steps[0].command == (
        "/usr/bin/python3",
        "scripts/check_control_doc_truth.py",
    )
    assert steps[1].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *validation_matrix.GATE_CONTRACT_TEST_FILES,
    )
    assert steps[2].command == (
        "/usr/bin/python3",
        "scripts/run_phase2_readiness_gates.py",
    )
    assert steps[3].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *validation_matrix.BACKEND_INTEGRATION_TEST_FILES,
    )
    assert steps[4].command == (
        "npm",
        "--prefix",
        str(validation_matrix.WEB_DIR),
        "run",
        "test:mvp:validation-matrix",
    )


def test_validation_matrix_induced_failure_is_explicit_and_fail_closed(capsys) -> None:
    def executor(command: tuple[str, ...], _cwd: Path) -> int:
        return validation_matrix.INDUCED_FAILURE_EXIT_CODE if "-c" in command else 0

    results = validation_matrix.run_validation_matrix(
        induce_step=validation_matrix.STEP_BACKEND_MATRIX,
        execute_command=executor,
    )
    validation_matrix._print_step_results(results)

    assert len(results) == len(validation_matrix.STEP_IDS)
    assert [result.status for result in results] == ["PASS", "PASS", "PASS", "FAIL", "PASS"]
    assert results[3].induced_failure is True
    assert results[3].exit_code == validation_matrix.INDUCED_FAILURE_EXIT_CODE
    assert validation_matrix.exit_code_for_step_results(results) == 1

    output = capsys.readouterr().out
    assert "Core validation matrix results:" in output
    assert f"Failing steps: {validation_matrix.STEP_BACKEND_MATRIX}" in output


def test_validation_matrix_has_no_deleted_or_default_hidden_api_assumptions() -> None:
    source = (REPO_ROOT / "scripts" / "run_phase2_validation_matrix.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "/v0/responses",
        "test_responses_api.py",
        "test_approval_api.py",
        "test_proxy_execution_api.py",
        "test_tasks_api.py",
        "test_task_artifacts_api.py",
        "test_gmail_accounts_api.py",
        "test_calendar_accounts_api.py",
        '"/chat"',
        '"/approvals"',
        '"/tasks"',
    ):
        assert forbidden not in source

    assert "test_local_workspace_bootstrap_api.py" in source
    assert "test_vnext_retrieval_postgres_filters.py" in source


def test_validation_matrix_pass_exit_requires_every_step_to_pass() -> None:
    results = validation_matrix.run_validation_matrix(
        execute_command=lambda _command, _cwd: 0,
    )

    assert all(result.status == "PASS" for result in results)
    assert validation_matrix.exit_code_for_step_results(results) == 0
