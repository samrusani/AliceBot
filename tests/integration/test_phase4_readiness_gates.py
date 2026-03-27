from __future__ import annotations

from pathlib import Path

import scripts.run_phase4_readiness_gates as readiness_gates


def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
    del cwd
    if "-c" in command and "Induced phase4 readiness failure" in command[-1]:
        return readiness_gates.INDUCED_FAILURE_EXIT_CODE
    return 0


def test_readiness_gate_sequence_contains_magnesium_and_phase3_compat() -> None:
    gate_steps = readiness_gates.build_readiness_gate_steps(python_executable="/usr/bin/python3")

    assert [gate.gate for gate in gate_steps] == [
        readiness_gates.GATE_PHASE4_ACCEPTANCE,
        readiness_gates.GATE_MAGNESIUM_SHIP_GATE,
        readiness_gates.GATE_PHASE3_COMPAT,
    ]

    assert gate_steps[0].command == ("/usr/bin/python3", "scripts/run_phase4_acceptance.py")
    assert gate_steps[1].command == (
        "/usr/bin/python3",
        "-m",
        "pytest",
        "-q",
        readiness_gates.MAGNESIUM_NODE_ID,
    )
    assert gate_steps[2].command == ("/usr/bin/python3", "scripts/run_phase3_readiness_gates.py")


def test_induced_gate_failure_reports_explicit_failing_gate(capsys) -> None:
    results = readiness_gates.run_readiness_gates(
        induce_gate=readiness_gates.GATE_MAGNESIUM_SHIP_GATE,
        execute_command=_always_pass_executor,
    )
    readiness_gates._print_gate_results(results)
    output = capsys.readouterr().out

    assert [result.gate for result in results] == [
        readiness_gates.GATE_PHASE4_ACCEPTANCE,
        readiness_gates.GATE_MAGNESIUM_SHIP_GATE,
        readiness_gates.GATE_PHASE3_COMPAT,
    ]
    assert results[0].status == "PASS"
    assert results[1].status == "FAIL"
    assert results[1].exit_code == readiness_gates.INDUCED_FAILURE_EXIT_CODE
    assert results[1].induced_failure is True
    assert results[2].status == "PASS"

    assert "Phase 4 readiness gate results:" in output
    assert " - canonical_magnesium_ship_gate: FAIL" in output
    assert "induced_failure: true" in output
    assert "Failing gates: canonical_magnesium_ship_gate" in output
    assert readiness_gates.exit_code_for_gate_results(results) == 1
