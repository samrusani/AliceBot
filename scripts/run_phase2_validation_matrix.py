#!/usr/bin/env python3
"""Run the bounded validation matrix for Alice's retained core surfaces."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "apps" / "web"
INDUCED_FAILURE_EXIT_CODE = 97

BACKEND_INTEGRATION_TEST_FILES: tuple[str, ...] = (
    "tests/integration/test_local_workspace_bootstrap_api.py",
    "tests/integration/test_continuity_brief_api.py",
    "tests/integration/test_memory_quality_gate_api.py",
    "tests/integration/test_retrieval_evaluation_api.py",
    "tests/integration/test_vnext_fts_fallback_postgres.py",
    "tests/integration/test_vnext_retrieval_postgres_filters.py",
)

GATE_CONTRACT_TEST_FILES: tuple[str, ...] = (
    "tests/unit/test_core_readiness_gates.py",
    "tests/unit/test_core_validation_matrix.py",
)

WEB_CORE_CONTRACTS: tuple[str, ...] = (
    "core shell",
    "legacy mount gates",
    "artifacts",
    "memories",
    "entities",
    "traces",
)

STEP_CONTROL_DOC_TRUTH = "control_doc_truth"
STEP_GATE_CONTRACT_TESTS = "gate_contract_tests"
STEP_READINESS_GATES = "core_readiness_gates"
STEP_BACKEND_MATRIX = "core_backend_matrix"
STEP_WEB_MATRIX = "core_web_matrix"
STEP_IDS: tuple[str, ...] = (
    STEP_CONTROL_DOC_TRUTH,
    STEP_GATE_CONTRACT_TESTS,
    STEP_READINESS_GATES,
    STEP_BACKEND_MATRIX,
    STEP_WEB_MATRIX,
)

StepStatus = Literal["PASS", "FAIL"]


@dataclass(frozen=True, slots=True)
class MatrixStep:
    step: str
    description: str
    command: tuple[str, ...]
    coverage: str


@dataclass(frozen=True, slots=True)
class MatrixStepResult:
    step: str
    status: StepStatus
    exit_code: int
    duration_seconds: float
    command: tuple[str, ...]
    coverage: str
    induced_failure: bool


CommandExecutor = Callable[[tuple[str, ...], Path], int]


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _pytest_command(python_executable: str, test_files: tuple[str, ...]) -> tuple[str, ...]:
    return (python_executable, "-m", "pytest", "-q", *test_files)


def _build_web_matrix_command() -> tuple[str, ...]:
    # This package script now covers the core shell plus explicit legacy mount
    # gates. Its historical name remains a package-level compatibility alias.
    return ("npm", "--prefix", str(WEB_DIR), "run", "test:mvp:validation-matrix")


def build_validation_matrix_steps(*, python_executable: str | None = None) -> list[MatrixStep]:
    resolved_python = python_executable or _resolve_python_executable()
    return [
        MatrixStep(
            step=STEP_CONTROL_DOC_TRUTH,
            description="Validate canonical control-document truth markers.",
            command=(resolved_python, "scripts/check_control_doc_truth.py"),
            coverage="architecture, roadmap, product brief, rules, and handoff truth",
        ),
        MatrixStep(
            step=STEP_GATE_CONTRACT_TESTS,
            description="Run the core readiness and validation carrier contracts.",
            command=_pytest_command(resolved_python, GATE_CONTRACT_TEST_FILES),
            coverage=", ".join(GATE_CONTRACT_TEST_FILES),
        ),
        MatrixStep(
            step=STEP_READINESS_GATES,
            description="Run retrieval, provider-runtime, and local-bootstrap readiness contracts.",
            command=(resolved_python, "scripts/run_phase2_readiness_gates.py"),
            coverage="retrieval, provider runtime, deterministic local bootstrap",
        ),
        MatrixStep(
            step=STEP_BACKEND_MATRIX,
            description="Run bounded integration seams for the retained core.",
            command=_pytest_command(resolved_python, BACKEND_INTEGRATION_TEST_FILES),
            coverage=(
                "local workspace bootstrap, continuity brief, memory quality, "
                "retrieval evaluation, FTS fallback, vector filtering"
            ),
        ),
        MatrixStep(
            step=STEP_WEB_MATRIX,
            description="Run the core web shell and legacy mount-gate contracts.",
            command=_build_web_matrix_command(),
            coverage=", ".join(WEB_CORE_CONTRACTS),
        ),
    ]


def _execute_command(command: tuple[str, ...], cwd: Path) -> int:
    completed = subprocess.run(list(command), cwd=cwd, check=False)
    return completed.returncode


def _build_induced_failure_command(*, step: str, python_executable: str) -> tuple[str, ...]:
    return (
        python_executable,
        "-c",
        (
            "import sys; "
            f"print('Induced core validation failure for step: {step}'); "
            f"sys.exit({INDUCED_FAILURE_EXIT_CODE})"
        ),
    )


def run_validation_matrix(
    *,
    induce_step: str | None = None,
    execute_command: CommandExecutor = _execute_command,
) -> list[MatrixStepResult]:
    results: list[MatrixStepResult] = []
    python_executable = _resolve_python_executable()

    for matrix_step in build_validation_matrix_steps(python_executable=python_executable):
        induced_failure = induce_step == matrix_step.step
        command = (
            _build_induced_failure_command(step=matrix_step.step, python_executable=python_executable)
            if induced_failure
            else matrix_step.command
        )
        started = time.perf_counter()
        exit_code = execute_command(command, ROOT_DIR)
        results.append(
            MatrixStepResult(
                step=matrix_step.step,
                status="PASS" if exit_code == 0 else "FAIL",
                exit_code=exit_code,
                duration_seconds=time.perf_counter() - started,
                command=command,
                coverage=matrix_step.coverage,
                induced_failure=induced_failure,
            )
        )
    return results


def exit_code_for_step_results(step_results: list[MatrixStepResult]) -> int:
    return 0 if all(result.status == "PASS" for result in step_results) else 1


def _print_step_results(step_results: list[MatrixStepResult]) -> None:
    print("Core validation matrix results:")
    for result in step_results:
        print(f" - {result.step}: {result.status}")
        print(f"   command: {shlex.join(result.command)}")
        print(f"   duration_seconds: {result.duration_seconds:.3f}")
        print(f"   exit_code: {result.exit_code}")
        print(f"   coverage: {result.coverage}")
        if result.induced_failure:
            print("   induced_failure: true")

    failing_steps = [result.step for result in step_results if result.status != "PASS"]
    if failing_steps:
        print(f"Failing steps: {', '.join(failing_steps)}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the bounded validation matrix for Alice's retained core.",
    )
    parser.add_argument(
        "--induce-step",
        choices=STEP_IDS,
        default=None,
        help="Force one matrix step to fail to verify no-go signaling.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    step_results = run_validation_matrix(induce_step=args.induce_step)
    _print_step_results(step_results)
    exit_code = exit_code_for_step_results(step_results)
    print(f"Core validation matrix result: {'PASS' if exit_code == 0 else 'NO_GO'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
