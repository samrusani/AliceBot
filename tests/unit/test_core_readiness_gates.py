from pathlib import Path

import scripts.run_phase2_readiness_gates as readiness_gates


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_readiness_checks_cover_only_retained_core_contracts() -> None:
    checks = readiness_gates.build_readiness_checks(python_executable="/usr/bin/python3")

    assert [check.gate for check in checks] == [
        readiness_gates.RETRIEVAL_GATE_NAME,
        readiness_gates.RUNTIME_GATE_NAME,
        readiness_gates.LOCAL_BOOTSTRAP_GATE_NAME,
    ]
    assert checks[0].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *readiness_gates.RETRIEVAL_TEST_FILES,
    )
    assert checks[1].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *readiness_gates.RUNTIME_TEST_FILES,
    )
    assert checks[2].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        *readiness_gates.LOCAL_BOOTSTRAP_TEST_FILES,
    )


def test_readiness_results_fail_closed_for_failure_and_blocked_execution() -> None:
    pass_results = readiness_gates.run_readiness_gates(
        execute_command=lambda _command, _cwd: 0,
    )
    assert [result.status for result in pass_results] == ["PASS", "PASS", "PASS"]
    assert readiness_gates.exit_code_for_gate_results(pass_results) == 0

    def induced_executor(command: tuple[str, ...], _cwd: Path) -> int:
        return readiness_gates.INDUCED_FAILURE_EXIT_CODE if "-c" in command else 0

    failed_results = readiness_gates.run_readiness_gates(
        induce_gate="runtime_fail",
        execute_command=induced_executor,
    )
    assert [result.status for result in failed_results] == ["PASS", "FAIL", "PASS"]
    assert readiness_gates.exit_code_for_gate_results(failed_results) == 1

    def blocked_executor(_command: tuple[str, ...], _cwd: Path) -> int:
        raise OSError("runner unavailable")

    blocked_results = readiness_gates.run_readiness_gates(execute_command=blocked_executor)
    assert [result.status for result in blocked_results] == ["BLOCKED", "BLOCKED", "BLOCKED"]
    assert all("runner unavailable" in result.detail for result in blocked_results)
    assert readiness_gates.exit_code_for_gate_results(blocked_results) == 1


def test_readiness_carrier_has_no_retired_response_or_workflow_dependencies() -> None:
    source = (REPO_ROOT / "scripts" / "run_phase2_readiness_gates.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "/v0/responses",
        "run_phase2_acceptance.py",
        "response_generation",
        "test_responses_api.py",
        "test_approval_api.py",
        "test_proxy_execution_api.py",
        "test_tasks_api.py",
    ):
        assert forbidden not in source


def test_readiness_output_uses_neutral_core_language(capsys) -> None:
    results = readiness_gates.run_readiness_gates(
        execute_command=lambda _command, _cwd: 0,
    )

    readiness_gates._print_gate_results(results)

    output = capsys.readouterr().out
    assert "Core readiness gate results:" in output
    assert "Phase 2" not in output
    assert "MVP" not in output
