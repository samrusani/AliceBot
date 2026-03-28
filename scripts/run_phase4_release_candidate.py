#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Callable, Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_PATH = ROOT_DIR / "artifacts" / "release" / "phase4_rc_summary.json"

INDUCED_FAILURE_EXIT_CODE = 97

StepStatus = Literal["PASS", "FAIL", "NOT_RUN"]
FinalDecision = Literal["GO", "NO_GO"]

STEP_CONTROL_DOC_TRUTH = "control_doc_truth"
STEP_PHASE4_ACCEPTANCE = "phase4_acceptance"
STEP_PHASE4_READINESS = "phase4_readiness"
STEP_PHASE4_VALIDATION_MATRIX = "phase4_validation_matrix"
STEP_PHASE3_COMPAT_VALIDATION = "phase3_compat_validation"
STEP_PHASE2_COMPAT_VALIDATION = "phase2_compat_validation"
STEP_MVP_COMPAT_VALIDATION = "mvp_compat_validation"
STEP_IDS: tuple[str, ...] = (
    STEP_CONTROL_DOC_TRUTH,
    STEP_PHASE4_ACCEPTANCE,
    STEP_PHASE4_READINESS,
    STEP_PHASE4_VALIDATION_MATRIX,
    STEP_PHASE3_COMPAT_VALIDATION,
    STEP_PHASE2_COMPAT_VALIDATION,
    STEP_MVP_COMPAT_VALIDATION,
)


@dataclass(frozen=True, slots=True)
class ReleaseCandidateStep:
    step: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReleaseCandidateStepResult:
    step: str
    description: str
    status: StepStatus
    exit_code: int | None
    duration_seconds: float
    command: tuple[str, ...]
    induced_failure: bool


CommandExecutor = Callable[[tuple[str, ...], Path], int]


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def build_release_candidate_steps(*, python_executable: str | None = None) -> list[ReleaseCandidateStep]:
    resolved_python = python_executable or _resolve_python_executable()
    return [
        ReleaseCandidateStep(
            step=STEP_CONTROL_DOC_TRUTH,
            description="Validate control-doc truth markers.",
            command=(resolved_python, "scripts/check_control_doc_truth.py"),
        ),
        ReleaseCandidateStep(
            step=STEP_PHASE4_ACCEPTANCE,
            description="Run Phase 4 acceptance gate.",
            command=(resolved_python, "scripts/run_phase4_acceptance.py"),
        ),
        ReleaseCandidateStep(
            step=STEP_PHASE4_READINESS,
            description="Run Phase 4 readiness gates.",
            command=(resolved_python, "scripts/run_phase4_readiness_gates.py"),
        ),
        ReleaseCandidateStep(
            step=STEP_PHASE4_VALIDATION_MATRIX,
            description="Run Phase 4 validation matrix.",
            command=(resolved_python, "scripts/run_phase4_validation_matrix.py"),
        ),
        ReleaseCandidateStep(
            step=STEP_PHASE3_COMPAT_VALIDATION,
            description="Run Phase 3 compatibility validation matrix.",
            command=(resolved_python, "scripts/run_phase3_validation_matrix.py"),
        ),
        ReleaseCandidateStep(
            step=STEP_PHASE2_COMPAT_VALIDATION,
            description="Run Phase 2 compatibility validation matrix.",
            command=(resolved_python, "scripts/run_phase2_validation_matrix.py"),
        ),
        ReleaseCandidateStep(
            step=STEP_MVP_COMPAT_VALIDATION,
            description="Run MVP compatibility validation matrix.",
            command=(resolved_python, "scripts/run_mvp_validation_matrix.py"),
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
            f"print('Induced phase4 release-candidate failure for step: {step}'); "
            f"sys.exit({INDUCED_FAILURE_EXIT_CODE})"
        ),
    )


def run_release_candidate(
    *,
    induce_step: str | None = None,
    execute_command: CommandExecutor = _execute_command,
) -> list[ReleaseCandidateStepResult]:
    results: list[ReleaseCandidateStepResult] = []
    steps = build_release_candidate_steps()
    python_executable = _resolve_python_executable()
    failed = False

    for step in steps:
        if failed:
            results.append(
                ReleaseCandidateStepResult(
                    step=step.step,
                    description=step.description,
                    status="NOT_RUN",
                    exit_code=None,
                    duration_seconds=0.0,
                    command=step.command,
                    induced_failure=False,
                )
            )
            continue

        induced_failure = induce_step == step.step
        step_command = (
            _build_induced_failure_command(step=step.step, python_executable=python_executable)
            if induced_failure
            else step.command
        )

        started = time.perf_counter()
        exit_code = execute_command(step_command, ROOT_DIR)
        duration_seconds = time.perf_counter() - started
        status: StepStatus = "PASS" if exit_code == 0 else "FAIL"

        results.append(
            ReleaseCandidateStepResult(
                step=step.step,
                description=step.description,
                status=status,
                exit_code=exit_code,
                duration_seconds=duration_seconds,
                command=step_command,
                induced_failure=induced_failure,
            )
        )

        if status == "FAIL":
            failed = True

    return results


def final_decision_for_step_results(step_results: list[ReleaseCandidateStepResult]) -> FinalDecision:
    return "GO" if all(result.status == "PASS" for result in step_results) else "NO_GO"


def exit_code_for_final_decision(final_decision: FinalDecision) -> int:
    return 0 if final_decision == "GO" else 1


def _render_artifact_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def build_release_candidate_summary(
    *,
    step_results: list[ReleaseCandidateStepResult],
    artifact_path: Path,
) -> dict[str, object]:
    final_decision = final_decision_for_step_results(step_results)
    return {
        "artifact_version": "phase4_rc_summary.v1",
        "artifact_path": _render_artifact_path(artifact_path),
        "final_decision": final_decision,
        "summary_exit_code": exit_code_for_final_decision(final_decision),
        "ordered_steps": list(STEP_IDS),
        "executed_steps": sum(1 for result in step_results if result.status != "NOT_RUN"),
        "total_steps": len(step_results),
        "failing_steps": [result.step for result in step_results if result.status == "FAIL"],
        "steps": [
            {
                "step": result.step,
                "description": result.description,
                "status": result.status,
                "command": list(result.command),
                "exit_code": result.exit_code,
                "duration_seconds": round(result.duration_seconds, 6),
                "induced_failure": result.induced_failure,
            }
            for result in step_results
        ],
    }


def write_release_candidate_summary(
    *,
    step_results: list[ReleaseCandidateStepResult],
    artifact_path: Path = ARTIFACT_PATH,
) -> dict[str, object]:
    summary = build_release_candidate_summary(step_results=step_results, artifact_path=artifact_path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _print_step_results(step_results: list[ReleaseCandidateStepResult]) -> None:
    print("Phase 4 release-candidate rehearsal results:")
    for result in step_results:
        print(f" - {result.step}: {result.status}")
        print(f"   command: {shlex.join(result.command)}")
        print(f"   duration_seconds: {result.duration_seconds:.3f}")
        print(f"   exit_code: {result.exit_code}")
        if result.induced_failure:
            print("   induced_failure: true")

    failing_steps = [result.step for result in step_results if result.status == "FAIL"]
    if failing_steps:
        print(f"Failing steps: {', '.join(failing_steps)}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic Phase 4 release-candidate rehearsal chain and write "
            "structured GO/NO_GO evidence bundle."
        ),
    )
    parser.add_argument(
        "--induce-step",
        choices=STEP_IDS,
        default=None,
        help="Force one rehearsal step to fail deterministically for NO_GO contract validation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    step_results = run_release_candidate(induce_step=args.induce_step)
    summary = write_release_candidate_summary(step_results=step_results)
    _print_step_results(step_results)

    print(f"Release-candidate summary artifact: {summary['artifact_path']}")
    final_decision = summary["final_decision"]
    if final_decision == "GO":
        print("Phase 4 release-candidate rehearsal result: GO")
    else:
        print("Phase 4 release-candidate rehearsal result: NO_GO")

    return int(summary["summary_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
