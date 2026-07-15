#!/usr/bin/env python3
"""Run deterministic readiness contracts for Alice's retained core."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
INDUCED_FAILURE_EXIT_CODE = 97

RETRIEVAL_GATE_NAME = "retrieval_contracts"
RUNTIME_GATE_NAME = "provider_runtime_contracts"
LOCAL_BOOTSTRAP_GATE_NAME = "local_bootstrap_contracts"

RETRIEVAL_TEST_FILES: tuple[str, ...] = (
    "tests/unit/test_vnext_retrieval.py",
    "tests/unit/test_vnext_evals.py",
    "tests/unit/test_retrieval_stability.py",
)
RUNTIME_TEST_FILES: tuple[str, ...] = (
    "tests/unit/test_provider_runtime.py",
    "tests/unit/test_autogen_runtime_bridge.py",
)
LOCAL_BOOTSTRAP_TEST_FILES: tuple[str, ...] = (
    "tests/unit/test_alice_lite_assets.py",
)

GateStatus = Literal["PASS", "FAIL", "BLOCKED"]
InducedScenario = Literal["retrieval_fail", "runtime_fail", "local_bootstrap_fail"]
INDUCED_SCENARIOS: tuple[InducedScenario, ...] = (
    "retrieval_fail",
    "runtime_fail",
    "local_bootstrap_fail",
)


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    gate: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    status: GateStatus
    measured: str
    threshold: str
    detail: str


CommandExecutor = Callable[[tuple[str, ...], Path], int]


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _pytest_command(python_executable: str, test_files: tuple[str, ...]) -> tuple[str, ...]:
    return (python_executable, "-m", "pytest", "-q", *test_files)


def build_readiness_checks(*, python_executable: str | None = None) -> list[ReadinessCheck]:
    resolved_python = python_executable or _resolve_python_executable()
    return [
        ReadinessCheck(
            gate=RETRIEVAL_GATE_NAME,
            description="Run deterministic retrieval and evaluation contracts.",
            command=_pytest_command(resolved_python, RETRIEVAL_TEST_FILES),
        ),
        ReadinessCheck(
            gate=RUNTIME_GATE_NAME,
            description="Run retained provider-runtime and bridge contracts.",
            command=_pytest_command(resolved_python, RUNTIME_TEST_FILES),
        ),
        ReadinessCheck(
            gate=LOCAL_BOOTSTRAP_GATE_NAME,
            description="Run the deterministic local bootstrap asset contracts.",
            command=_pytest_command(resolved_python, LOCAL_BOOTSTRAP_TEST_FILES),
        ),
    ]


def _execute_command(command: tuple[str, ...], cwd: Path) -> int:
    completed = subprocess.run(list(command), cwd=cwd, check=False)
    return completed.returncode


def _induced_failure_command(*, gate: str, python_executable: str) -> tuple[str, ...]:
    return (
        python_executable,
        "-c",
        (
            "import sys; "
            f"print('Induced core-readiness failure for gate: {gate}'); "
            f"sys.exit({INDUCED_FAILURE_EXIT_CODE})"
        ),
    )


def _induced_gate_name(induce_gate: InducedScenario | None) -> str | None:
    if induce_gate == "retrieval_fail":
        return RETRIEVAL_GATE_NAME
    if induce_gate == "runtime_fail":
        return RUNTIME_GATE_NAME
    if induce_gate == "local_bootstrap_fail":
        return LOCAL_BOOTSTRAP_GATE_NAME
    return None


def run_readiness_gates(
    *,
    induce_gate: InducedScenario | None = None,
    execute_command: CommandExecutor = _execute_command,
) -> list[GateResult]:
    induced_gate = _induced_gate_name(induce_gate)
    python_executable = _resolve_python_executable()
    results: list[GateResult] = []

    for check in build_readiness_checks(python_executable=python_executable):
        command = (
            _induced_failure_command(gate=check.gate, python_executable=python_executable)
            if check.gate == induced_gate
            else check.command
        )
        try:
            exit_code = execute_command(command, ROOT_DIR)
        except OSError as exc:
            results.append(
                GateResult(
                    gate=check.gate,
                    status="BLOCKED",
                    measured="exit_code=unavailable",
                    threshold="exit_code == 0",
                    detail=f"{check.description} command_error={exc}",
                )
            )
            continue

        results.append(
            GateResult(
                gate=check.gate,
                status="PASS" if exit_code == 0 else "FAIL",
                measured=f"exit_code={exit_code}",
                threshold="exit_code == 0",
                detail=f"{check.description} command={shlex.join(command)}",
            )
        )
    return results


def exit_code_for_gate_results(gate_results: list[GateResult]) -> int:
    return 0 if all(result.status == "PASS" for result in gate_results) else 1


def _print_gate_results(gate_results: list[GateResult]) -> None:
    print("Core readiness gate results:")
    for result in gate_results:
        print(f" - {result.gate}: {result.status}")
        print(f"   measured: {result.measured}")
        print(f"   threshold: {result.threshold}")
        print(f"   detail: {result.detail}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic readiness contracts for retrieval and local provider runtime.",
    )
    parser.add_argument(
        "--induce-gate",
        choices=INDUCED_SCENARIOS,
        default=None,
        help="Intentionally fail one gate to verify no-go signaling.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    gate_results = run_readiness_gates(induce_gate=args.induce_gate)
    _print_gate_results(gate_results)
    exit_code = exit_code_for_gate_results(gate_results)
    print(f"Core readiness gate result: {'PASS' if exit_code == 0 else 'NO_GO'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
