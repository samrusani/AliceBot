#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Callable, Literal

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "apps" / "web"

INDUCED_FAILURE_EXIT_CODE = 97

StepStatus = Literal["PASS", "FAIL"]

BACKEND_INTEGRATION_TEST_FILES: tuple[str, ...] = (
    "tests/integration/test_continuity_api.py",
    "tests/integration/test_responses_api.py",
    "tests/integration/test_approval_api.py",
    "tests/integration/test_proxy_execution_api.py",
    "tests/integration/test_tasks_api.py",
    "tests/integration/test_traces_api.py",
    "tests/integration/test_memory_review_api.py",
    "tests/integration/test_entities_api.py",
    "tests/integration/test_task_artifacts_api.py",
    "tests/integration/test_gmail_accounts_api.py",
    "tests/integration/test_calendar_accounts_api.py",
)

WEB_OPERATOR_SURFACES: tuple[str, ...] = (
    "/chat",
    "/approvals",
    "/tasks",
    "/artifacts",
    "/gmail",
    "/calendar",
    "/memories",
    "/entities",
    "/traces",
)

STEP_READINESS_GATES = "readiness_gates"
STEP_BACKEND_MATRIX = "backend_integration_matrix"
STEP_WEB_MATRIX = "web_validation_matrix"
STEP_CONTROL_DOC_TRUTH = "control_doc_truth"
STEP_IDS: tuple[str, ...] = (
    STEP_CONTROL_DOC_TRUTH,
    STEP_READINESS_GATES,
    STEP_BACKEND_MATRIX,
    STEP_WEB_MATRIX,
)


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


def _build_backend_matrix_command(python_executable: str) -> tuple[str, ...]:
    return (python_executable, "-m", "pytest", "-q", *BACKEND_INTEGRATION_TEST_FILES)


def _build_control_doc_truth_command(python_executable: str) -> tuple[str, ...]:
    return (python_executable, "scripts/check_control_doc_truth.py")


def _build_web_matrix_command() -> tuple[str, ...]:
    return ("npm", "--prefix", str(WEB_DIR), "run", "test:mvp:validation-matrix")


def build_validation_matrix_steps(*, python_executable: str | None = None) -> list[MatrixStep]:
    resolved_python = python_executable or _resolve_python_executable()
    return [
        MatrixStep(
            step=STEP_CONTROL_DOC_TRUTH,
            description="Validate canonical control-doc truth markers and stale-marker exclusions.",
            command=_build_control_doc_truth_command(resolved_python),
            coverage=(
                "ARCHITECTURE.md, ROADMAP.md, README.md, PRODUCT_BRIEF.md, RULES.md, "
                ".ai/handoff/CURRENT_STATE.md baseline/ownership truth markers"
            ),
        ),
        MatrixStep(
            step=STEP_READINESS_GATES,
            description="Run deterministic readiness gates prerequisite chain.",
            command=(resolved_python, "scripts/run_phase2_readiness_gates.py"),
            coverage="acceptance_suite, latency_p95, cache_reuse, memory_quality",
        ),
        MatrixStep(
            step=STEP_BACKEND_MATRIX,
            description="Run bounded backend integration seams matrix.",
            command=_build_backend_matrix_command(resolved_python),
            coverage=(
                "continuity, responses, approvals/execution, tasks/steps, traces, "
                "memory/entities/artifacts, gmail/calendar account seams"
            ),
        ),
        MatrixStep(
            step=STEP_WEB_MATRIX,
            description="Run bounded web operator shell matrix via explicit Vitest suites.",
            command=_build_web_matrix_command(),
            coverage=", ".join(WEB_OPERATOR_SURFACES),
        ),
    ]


def _execute_command(command: tuple[str, ...], cwd: Path) -> int:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
    )
    return completed.returncode


def _build_induced_failure_command(*, step: str, python_executable: str) -> tuple[str, ...]:
    return (
        python_executable,
        "-c",
        (
            "import sys; "
            f"print('Induced validation-matrix failure for step: {step}'); "
            f"sys.exit({INDUCED_FAILURE_EXIT_CODE})"
        ),
    )


def run_validation_matrix(
    *,
    induce_step: str | None = None,
    execute_command: CommandExecutor = _execute_command,
) -> list[MatrixStepResult]:
    results: list[MatrixStepResult] = []
    matrix_steps = build_validation_matrix_steps()
    python_executable = _resolve_python_executable()

    for matrix_step in matrix_steps:
        induced_failure = induce_step == matrix_step.step
        step_command = (
            _build_induced_failure_command(step=matrix_step.step, python_executable=python_executable)
            if induced_failure
            else matrix_step.command
        )

        started = time.perf_counter()
        exit_code = execute_command(step_command, ROOT_DIR)
        duration_seconds = time.perf_counter() - started
        status: StepStatus = "PASS" if exit_code == 0 else "FAIL"
        results.append(
            MatrixStepResult(
                step=matrix_step.step,
                status=status,
                exit_code=exit_code,
                duration_seconds=duration_seconds,
                command=step_command,
                coverage=matrix_step.coverage,
                induced_failure=induced_failure,
            )
        )

    return results


def exit_code_for_step_results(step_results: list[MatrixStepResult]) -> int:
    return 0 if all(result.status == "PASS" for result in step_results) else 1


def _print_step_results(step_results: list[MatrixStepResult]) -> None:
    print("Phase 2 validation matrix results:")
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
        description=(
            "Run deterministic Phase 2 validation matrix over control-doc truth, readiness "
            "prerequisite, backend seams, and web operator shell suites."
        ),
    )
    parser.add_argument(
        "--induce-step",
        choices=STEP_IDS,
        default=None,
        help=(
            "Force one matrix step to fail deterministically to validate "
            "no-go signaling and failing-step reporting."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    step_results = run_validation_matrix(induce_step=args.induce_step)
    _print_step_results(step_results)

    exit_code = exit_code_for_step_results(step_results)
    if exit_code == 0:
        print("Phase 2 validation matrix result: PASS")
    else:
        print("Phase 2 validation matrix result: NO_GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
