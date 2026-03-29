#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Callable, Literal


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_SIGNOFF_PATH = ROOT_DIR / "artifacts" / "release" / "phase4_mvp_signoff_record.json"
DEFAULT_RC_SUMMARY_PATH = ROOT_DIR / "artifacts" / "release" / "phase4_rc_summary.json"
DEFAULT_RC_ARCHIVE_INDEX_PATH = ROOT_DIR / "artifacts" / "release" / "archive" / "index.json"
DEFAULT_MVP_EXIT_MANIFEST_PATH = ROOT_DIR / "artifacts" / "release" / "phase4_mvp_exit_manifest.json"

SIGNOFF_ARTIFACT_VERSION = "phase4_mvp_signoff_record.v1"

StepStatus = Literal["PASS", "FAIL", "NOT_RUN"]
FinalDecision = Literal["GO", "NO_GO"]

STEP_RELEASE_CANDIDATE_REHEARSAL = "release_candidate_rehearsal"
STEP_RELEASE_CANDIDATE_ARCHIVE_VERIFY = "release_candidate_archive_verify"
STEP_MVP_EXIT_MANIFEST_GENERATE = "mvp_exit_manifest_generate"
STEP_MVP_EXIT_MANIFEST_VERIFY = "mvp_exit_manifest_verify"
STEP_IDS: tuple[str, ...] = (
    STEP_RELEASE_CANDIDATE_REHEARSAL,
    STEP_RELEASE_CANDIDATE_ARCHIVE_VERIFY,
    STEP_MVP_EXIT_MANIFEST_GENERATE,
    STEP_MVP_EXIT_MANIFEST_VERIFY,
)


@dataclass(frozen=True, slots=True)
class QualificationStep:
    step: str
    description: str
    command: tuple[str, ...]
    required_artifacts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QualificationStepResult:
    step: str
    description: str
    status: StepStatus
    exit_code: int | None
    duration_seconds: float
    command: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    missing_artifacts: tuple[str, ...]


CommandExecutor = Callable[[tuple[str, ...], Path], int]


def _resolve_python_executable() -> str:
    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _resolve_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return ROOT_DIR / candidate


def _render_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _atomic_write_json(*, path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp.{os.getpid()}.{time.monotonic_ns()}"
    temp_path.write_text(_render_json(payload), encoding="utf-8")
    try:
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def default_required_references(
    *,
    rc_summary_path: Path = DEFAULT_RC_SUMMARY_PATH,
    rc_archive_index_path: Path = DEFAULT_RC_ARCHIVE_INDEX_PATH,
    mvp_exit_manifest_path: Path = DEFAULT_MVP_EXIT_MANIFEST_PATH,
) -> dict[str, str]:
    return {
        "release_candidate_summary_path": _render_path(rc_summary_path),
        "release_candidate_archive_index_path": _render_path(rc_archive_index_path),
        "mvp_exit_manifest_path": _render_path(mvp_exit_manifest_path),
    }


def build_qualification_steps(
    *,
    python_executable: str | None = None,
    rc_summary_path: Path = DEFAULT_RC_SUMMARY_PATH,
    rc_archive_index_path: Path = DEFAULT_RC_ARCHIVE_INDEX_PATH,
    mvp_exit_manifest_path: Path = DEFAULT_MVP_EXIT_MANIFEST_PATH,
) -> list[QualificationStep]:
    resolved_python = python_executable or _resolve_python_executable()
    rc_summary_ref = _render_path(rc_summary_path)
    rc_archive_index_ref = _render_path(rc_archive_index_path)
    mvp_manifest_ref = _render_path(mvp_exit_manifest_path)
    return [
        QualificationStep(
            step=STEP_RELEASE_CANDIDATE_REHEARSAL,
            description="Run canonical Phase 4 release-candidate rehearsal chain.",
            command=(resolved_python, "scripts/run_phase4_release_candidate.py"),
            required_artifacts=(rc_summary_ref, rc_archive_index_ref),
        ),
        QualificationStep(
            step=STEP_RELEASE_CANDIDATE_ARCHIVE_VERIFY,
            description="Verify append-only Phase 4 RC archive/index evidence.",
            command=(resolved_python, "scripts/verify_phase4_rc_archive.py"),
            required_artifacts=(rc_archive_index_ref,),
        ),
        QualificationStep(
            step=STEP_MVP_EXIT_MANIFEST_GENERATE,
            description="Generate deterministic Phase 4 MVP exit manifest from latest GO archive evidence.",
            command=(resolved_python, "scripts/generate_phase4_mvp_exit_manifest.py"),
            required_artifacts=(mvp_manifest_ref,),
        ),
        QualificationStep(
            step=STEP_MVP_EXIT_MANIFEST_VERIFY,
            description="Verify deterministic Phase 4 MVP exit manifest schema and source coherence.",
            command=(resolved_python, "scripts/verify_phase4_mvp_exit_manifest.py"),
            required_artifacts=(mvp_manifest_ref,),
        ),
    ]


def _execute_command(command: tuple[str, ...], cwd: Path) -> int:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
    )
    return completed.returncode


def run_qualification(
    *,
    qualification_steps: list[QualificationStep] | None = None,
    execute_command: CommandExecutor = _execute_command,
    cwd: Path = ROOT_DIR,
) -> list[QualificationStepResult]:
    results: list[QualificationStepResult] = []
    steps = qualification_steps or build_qualification_steps()
    failed = False

    for step in steps:
        if failed:
            results.append(
                QualificationStepResult(
                    step=step.step,
                    description=step.description,
                    status="NOT_RUN",
                    exit_code=None,
                    duration_seconds=0.0,
                    command=step.command,
                    required_artifacts=step.required_artifacts,
                    missing_artifacts=(),
                )
            )
            continue

        started = time.perf_counter()
        exit_code = execute_command(step.command, cwd)
        duration_seconds = time.perf_counter() - started
        status: StepStatus = "PASS" if exit_code == 0 else "FAIL"

        missing_artifacts = tuple(
            path_value
            for path_value in step.required_artifacts
            if not _resolve_path(path_value).exists()
        )

        if status == "PASS" and missing_artifacts:
            status = "FAIL"

        results.append(
            QualificationStepResult(
                step=step.step,
                description=step.description,
                status=status,
                exit_code=exit_code,
                duration_seconds=duration_seconds,
                command=step.command,
                required_artifacts=step.required_artifacts,
                missing_artifacts=missing_artifacts,
            )
        )

        if status == "FAIL":
            failed = True

    return results


def final_decision_for_step_results(step_results: list[QualificationStepResult]) -> FinalDecision:
    return "GO" if all(result.status == "PASS" for result in step_results) else "NO_GO"


def exit_code_for_final_decision(final_decision: FinalDecision) -> int:
    return 0 if final_decision == "GO" else 1


def _build_blockers(step_results: list[QualificationStepResult]) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for result in step_results:
        if result.status == "PASS":
            continue
        if result.status == "NOT_RUN":
            blockers.append(
                {
                    "step": result.step,
                    "reason": "upstream_failure",
                    "detail": "Step was not run because an earlier qualification gate failed.",
                }
            )
            continue
        if result.missing_artifacts:
            blockers.append(
                {
                    "step": result.step,
                    "reason": "missing_required_artifacts",
                    "detail": (
                        "Step command returned success but required artifacts were not present: "
                        + ", ".join(result.missing_artifacts)
                    ),
                }
            )
            continue
        blockers.append(
            {
                "step": result.step,
                "reason": "command_failed",
                "detail": f"Step command exited non-zero ({result.exit_code}).",
            }
        )
    return blockers


def _normalize_utc_datetime(created_at: datetime | None) -> datetime:
    if created_at is None:
        return datetime.now(UTC).replace(microsecond=0)
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=UTC, microsecond=0)
    return created_at.astimezone(UTC).replace(microsecond=0)


def _format_created_at(created_at: datetime) -> str:
    return created_at.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_signoff_record(
    *,
    step_results: list[QualificationStepResult],
    artifact_path: Path,
    required_references: dict[str, str],
    created_at: datetime | None,
) -> dict[str, object]:
    final_decision = final_decision_for_step_results(step_results)
    blockers = _build_blockers(step_results)
    failing_steps = [result.step for result in step_results if result.status == "FAIL"]
    not_run_steps = [result.step for result in step_results if result.status == "NOT_RUN"]
    normalized_created_at = _normalize_utc_datetime(created_at)
    return {
        "artifact_version": SIGNOFF_ARTIFACT_VERSION,
        "artifact_path": _render_path(artifact_path),
        "generated_at": _format_created_at(normalized_created_at),
        "phase": "phase4",
        "release_gate": "mvp",
        "ordered_steps": list(STEP_IDS),
        "executed_steps": sum(1 for result in step_results if result.status != "NOT_RUN"),
        "total_steps": len(step_results),
        "failing_steps": failing_steps,
        "not_run_steps": not_run_steps,
        "required_references": required_references,
        "final_decision": final_decision,
        "summary_exit_code": exit_code_for_final_decision(final_decision),
        "blockers": blockers,
        "steps": [
            {
                "step": result.step,
                "description": result.description,
                "status": result.status,
                "command": list(result.command),
                "exit_code": result.exit_code,
                "duration_seconds": round(result.duration_seconds, 6),
                "required_artifacts": list(result.required_artifacts),
                "missing_artifacts": list(result.missing_artifacts),
            }
            for result in step_results
        ],
    }


def write_signoff_record(
    *,
    step_results: list[QualificationStepResult],
    artifact_path: Path = DEFAULT_SIGNOFF_PATH,
    required_references: dict[str, str] | None = None,
    created_at: datetime | None = None,
) -> dict[str, object]:
    references = required_references or default_required_references()
    record = build_signoff_record(
        step_results=step_results,
        artifact_path=artifact_path,
        required_references=references,
        created_at=created_at,
    )
    _atomic_write_json(path=artifact_path, payload=record)
    return record


def _print_step_results(step_results: list[QualificationStepResult]) -> None:
    print("Phase 4 MVP qualification results:")
    for result in step_results:
        print(f" - {result.step}: {result.status}")
        print(f"   command: {shlex.join(result.command)}")
        print(f"   duration_seconds: {result.duration_seconds:.3f}")
        print(f"   exit_code: {result.exit_code}")
        if result.required_artifacts:
            print("   required_artifacts: " + ", ".join(result.required_artifacts))
        if result.missing_artifacts:
            print("   missing_artifacts: " + ", ".join(result.missing_artifacts))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the deterministic Phase 4 MVP qualification chain and emit a machine-readable "
            "GO/NO_GO sign-off record."
        ),
    )
    parser.add_argument(
        "--signoff-path",
        default=str(DEFAULT_SIGNOFF_PATH),
        help="Output path for the qualification sign-off JSON artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    signoff_path = Path(args.signoff_path)

    step_results = run_qualification()
    signoff_record = write_signoff_record(
        step_results=step_results,
        artifact_path=signoff_path,
    )
    _print_step_results(step_results)

    print(f"MVP qualification sign-off artifact: {signoff_record['artifact_path']}")
    if signoff_record["final_decision"] == "GO":
        print("Phase 4 MVP qualification result: GO")
    else:
        print("Phase 4 MVP qualification result: NO_GO")
        blockers = signoff_record["blockers"]
        assert isinstance(blockers, list)
        if blockers:
            print("Blockers:")
            for blocker in blockers:
                assert isinstance(blocker, dict)
                print(f" - {blocker['step']}: {blocker['reason']} ({blocker['detail']})")

    return int(signoff_record["summary_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
