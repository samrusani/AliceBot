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

INDUCED_FAILURE_EXIT_CODE = 97

StepStatus = Literal["PASS", "FAIL"]

STEP_CONTROL_DOC_TRUTH = "control_doc_truth"
STEP_PHASE4_ACCEPTANCE = "phase4_acceptance"
STEP_PHASE4_READINESS = "phase4_readiness_gates"
STEP_PHASE4_MAGNESIUM = "phase4_magnesium_ship_gate"
STEP_PHASE4_SCENARIOS = "phase4_scenarios"
STEP_PHASE4_WEB = "phase4_web_diagnostics"
STEP_PHASE3_COMPAT = "phase3_compat_validation"
STEP_PHASE2_COMPAT = "phase2_compat_validation"
STEP_MVP_COMPAT = "mvp_compat_validation"
STEP_IDS: tuple[str, ...] = (
    STEP_CONTROL_DOC_TRUTH,
    STEP_PHASE4_ACCEPTANCE,
    STEP_PHASE4_READINESS,
    STEP_PHASE4_MAGNESIUM,
    STEP_PHASE4_SCENARIOS,
    STEP_PHASE4_WEB,
    STEP_PHASE3_COMPAT,
    STEP_PHASE2_COMPAT,
    STEP_MVP_COMPAT,
)

PHASE4_MAGNESIUM_NODE_ID = (
    "tests/integration/test_mvp_acceptance_suite.py::"
    "test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence"
)

PHASE4_SCENARIO_NODE_IDS: tuple[str, ...] = (
    "tests/integration/test_task_runs_api.py::test_task_run_endpoints_cover_budget_wait_resume_pause_cancel_and_conflicts",
    "tests/unit/test_approvals.py::test_approval_resolution_resumes_waiting_approval_run_only",
    "tests/unit/test_task_runs.py::test_tick_sets_budget_exhaustion_as_failed_with_explicit_failure_class",
    "tests/unit/test_proxy_execution.py::test_registered_proxy_handler_keys_are_sorted_and_explicit",
    "tests/integration/test_proxy_execution_api.py::test_execute_approved_proxy_endpoint_marks_linked_run_failed_when_blocked",
)

PHASE4_WEB_COMMAND: tuple[str, ...] = (
    "pnpm",
    "--dir",
    "apps/web",
    "exec",
    "vitest",
    "run",
    "app/tasks/page.test.tsx",
    "app/traces/page.test.tsx",
    "components/task-run-list.test.tsx",
    "components/execution-summary.test.tsx",
    "lib/api.test.ts",
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


def _build_phase4_scenario_command(python_executable: str) -> tuple[str, ...]:
    return (python_executable, "-m", "pytest", "-q", *PHASE4_SCENARIO_NODE_IDS)


def _build_phase4_magnesium_command(python_executable: str) -> tuple[str, ...]:
    return (python_executable, "-m", "pytest", "-q", PHASE4_MAGNESIUM_NODE_ID)


def build_validation_matrix_steps(*, python_executable: str | None = None) -> list[MatrixStep]:
    resolved_python = python_executable or _resolve_python_executable()
    return [
        MatrixStep(
            step=STEP_CONTROL_DOC_TRUTH,
            description="Validate canonical control-doc truth markers.",
            command=(resolved_python, "scripts/check_control_doc_truth.py"),
            coverage="README.md, ROADMAP.md, .ai/handoff/CURRENT_STATE.md and linked control docs",
        ),
        MatrixStep(
            step=STEP_PHASE4_ACCEPTANCE,
            description="Run Phase 4 acceptance gate entrypoint.",
            command=(resolved_python, "scripts/run_phase4_acceptance.py"),
            coverage="Phase 4 canonical acceptance chain with magnesium evidence mapping",
        ),
        MatrixStep(
            step=STEP_PHASE4_READINESS,
            description="Run Phase 4 readiness gate entrypoint.",
            command=(resolved_python, "scripts/run_phase4_readiness_gates.py"),
            coverage="Phase 4 deterministic readiness gates and explicit failing-gate signaling",
        ),
        MatrixStep(
            step=STEP_PHASE4_MAGNESIUM,
            description=(
                "Run canonical MVP ship-gate magnesium reorder scenario evidence directly: "
                "request -> approval -> execution -> memory write-back."
            ),
            command=_build_phase4_magnesium_command(resolved_python),
            coverage=PHASE4_MAGNESIUM_NODE_ID,
        ),
        MatrixStep(
            step=STEP_PHASE4_SCENARIOS,
            description=(
                "Run deterministic Phase 4 scenario evidence checks: "
                "run_progression_with_pause, restart_safe_resume, budget_exhaustion_fail_closed, "
                "draft_first_tool_execution, approval_resume_execution."
            ),
            command=_build_phase4_scenario_command(resolved_python),
            coverage=", ".join(PHASE4_SCENARIO_NODE_IDS),
        ),
        MatrixStep(
            step=STEP_PHASE4_WEB,
            description="Run Phase 4 diagnostics shell tests for tasks/traces/run diagnostics surfaces.",
            command=PHASE4_WEB_COMMAND,
            coverage="apps/web tasks/traces diagnostics and API client shape",
        ),
        MatrixStep(
            step=STEP_PHASE3_COMPAT,
            description="Run Phase 3 compatibility validation matrix.",
            command=(resolved_python, "scripts/run_phase3_validation_matrix.py"),
            coverage="Phase 3 compatibility chain remains PASS",
        ),
        MatrixStep(
            step=STEP_PHASE2_COMPAT,
            description="Run Phase 2 compatibility validation matrix.",
            command=(resolved_python, "scripts/run_phase2_validation_matrix.py"),
            coverage="Phase 2 compatibility chain remains PASS",
        ),
        MatrixStep(
            step=STEP_MVP_COMPAT,
            description="Run MVP compatibility validation matrix alias.",
            command=(resolved_python, "scripts/run_mvp_validation_matrix.py"),
            coverage="MVP alias compatibility chain remains PASS",
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
            f"print('Induced phase4 validation failure for step: {step}'); "
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
    print("Phase 4 validation matrix results:")
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
            "Run deterministic Phase 4 validation matrix over control docs, "
            "canonical Phase 4 acceptance/readiness ownership, magnesium ship-gate evidence, "
            "diagnostics shell tests, and Phase 3/2/MVP compatibility."
        ),
    )
    parser.add_argument(
        "--induce-step",
        choices=STEP_IDS,
        default=None,
        help="Force one matrix step to fail deterministically for no-go signaling validation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    step_results = run_validation_matrix(induce_step=args.induce_step)
    _print_step_results(step_results)

    exit_code = exit_code_for_step_results(step_results)
    if exit_code == 0:
        print("Phase 4 validation matrix result: PASS")
    else:
        print("Phase 4 validation matrix result: NO_GO")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
