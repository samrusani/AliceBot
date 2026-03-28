#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
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
ARTIFACT_PATH = ROOT_DIR / "artifacts" / "release" / "phase4_rc_summary.json"
ARCHIVE_DIR_NAME = "archive"
ARCHIVE_INDEX_NAME = "index.json"
ARCHIVE_INDEX_LOCK_NAME = "index.lock"
ARCHIVE_INDEX_VERSION = "phase4_rc_archive_index.v1"
ARCHIVE_FILENAME_SUFFIX = "_phase4_rc_summary.json"
ARCHIVE_INDEX_LOCK_TIMEOUT_SECONDS = 5.0
ARCHIVE_INDEX_LOCK_RETRY_INTERVAL_SECONDS = 0.05
ARCHIVE_INDEX_LOCK_TIMEOUT_EXIT_CODE = 2

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


class ArchiveIndexLockTimeoutError(RuntimeError):
    """Raised when archive index lock acquisition times out."""


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


def _normalize_utc_datetime(created_at: datetime | None) -> datetime:
    if created_at is None:
        return datetime.now(UTC).replace(microsecond=0)
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=UTC, microsecond=0)
    return created_at.astimezone(UTC).replace(microsecond=0)


def _format_created_at(created_at: datetime) -> str:
    return created_at.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_archive_timestamp(created_at: datetime) -> str:
    return created_at.strftime("%Y%m%dT%H%M%SZ")


def _archive_dir_for_artifact_path(artifact_path: Path) -> Path:
    return artifact_path.parent / ARCHIVE_DIR_NAME


def _archive_index_path_for_artifact_path(artifact_path: Path) -> Path:
    return _archive_dir_for_artifact_path(artifact_path) / ARCHIVE_INDEX_NAME


def _archive_index_lock_path_for_artifact_path(artifact_path: Path) -> Path:
    return _archive_dir_for_artifact_path(artifact_path) / ARCHIVE_INDEX_LOCK_NAME


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


@contextmanager
def _acquire_archive_index_lock(
    *,
    artifact_path: Path,
    timeout_seconds: float,
    retry_interval_seconds: float,
):
    lock_path = _archive_index_lock_path_for_artifact_path(artifact_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ArchiveIndexLockTimeoutError(
                    "Timed out acquiring archive index lock at "
                    f"{_render_artifact_path(lock_path)} after {timeout_seconds:.2f}s."
                )
            time.sleep(retry_interval_seconds)
            continue

        with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(f"pid={os.getpid()}\n")
        break

    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _next_archive_artifact_path(*, archive_dir: Path, timestamp: str) -> Path:
    candidate = archive_dir / f"{timestamp}{ARCHIVE_FILENAME_SUFFIX}"
    if not candidate.exists():
        return candidate

    suffix = 1
    while True:
        candidate = archive_dir / f"{timestamp}_{suffix:03d}{ARCHIVE_FILENAME_SUFFIX}"
        if not candidate.exists():
            return candidate
        suffix += 1


def _new_archive_index_payload(*, artifact_path: Path, archive_dir: Path) -> dict[str, object]:
    return {
        "artifact_version": ARCHIVE_INDEX_VERSION,
        "latest_summary_path": _render_artifact_path(artifact_path),
        "archive_dir": _render_artifact_path(archive_dir),
        "entries": [],
    }


def _load_archive_index_payload(*, artifact_path: Path, archive_dir: Path) -> dict[str, object]:
    index_path = _archive_index_path_for_artifact_path(artifact_path)
    if not index_path.exists():
        return _new_archive_index_payload(artifact_path=artifact_path, archive_dir=archive_dir)

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Archive index payload must be a JSON object.")

    if payload.get("artifact_version") != ARCHIVE_INDEX_VERSION:
        raise ValueError(
            f"Archive index artifact_version must be {ARCHIVE_INDEX_VERSION!r}."
        )

    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Archive index entries must be a list.")

    latest_summary_path = payload.get("latest_summary_path")
    if not isinstance(latest_summary_path, str):
        raise ValueError("Archive index latest_summary_path must be a string.")

    archive_dir_value = payload.get("archive_dir")
    if not isinstance(archive_dir_value, str):
        raise ValueError("Archive index archive_dir must be a string.")

    return payload


def _append_archive_index_entry(
    *,
    artifact_path: Path,
    archive_dir: Path,
    entry: dict[str, object],
) -> Path:
    payload = _load_archive_index_payload(artifact_path=artifact_path, archive_dir=archive_dir)
    entries = payload["entries"]
    assert isinstance(entries, list)
    entries.append(entry)

    index_path = _archive_index_path_for_artifact_path(artifact_path)
    _atomic_write_json(path=index_path, payload=payload)
    return index_path


def _write_archive_copy_and_index(
    *,
    step_results: list[ReleaseCandidateStepResult],
    artifact_path: Path,
    command_mode: str,
    created_at: datetime | None,
    lock_timeout_seconds: float = ARCHIVE_INDEX_LOCK_TIMEOUT_SECONDS,
    lock_retry_interval_seconds: float = ARCHIVE_INDEX_LOCK_RETRY_INTERVAL_SECONDS,
) -> tuple[Path, Path]:
    normalized_created_at = _normalize_utc_datetime(created_at)
    created_at_iso = _format_created_at(normalized_created_at)
    timestamp = _format_archive_timestamp(normalized_created_at)

    archive_dir = _archive_dir_for_artifact_path(artifact_path)
    with _acquire_archive_index_lock(
        artifact_path=artifact_path,
        timeout_seconds=lock_timeout_seconds,
        retry_interval_seconds=lock_retry_interval_seconds,
    ):
        archive_artifact_path = _next_archive_artifact_path(archive_dir=archive_dir, timestamp=timestamp)
        archive_summary = build_release_candidate_summary(
            step_results=step_results,
            artifact_path=archive_artifact_path,
        )
        try:
            _atomic_write_json(path=archive_artifact_path, payload=archive_summary)

            entry = {
                "created_at": created_at_iso,
                "archive_artifact_path": _render_artifact_path(archive_artifact_path),
                "final_decision": archive_summary["final_decision"],
                "summary_exit_code": archive_summary["summary_exit_code"],
                "failing_steps": archive_summary["failing_steps"],
                "command_mode": command_mode,
            }
            index_path = _append_archive_index_entry(
                artifact_path=artifact_path,
                archive_dir=archive_dir,
                entry=entry,
            )
        except Exception:
            if archive_artifact_path.exists():
                archive_artifact_path.unlink()
            raise
    return archive_artifact_path, index_path


def write_release_candidate_summary(
    *,
    step_results: list[ReleaseCandidateStepResult],
    artifact_path: Path = ARTIFACT_PATH,
    write_archive: bool = True,
    command_mode: str = "default",
    created_at: datetime | None = None,
    lock_timeout_seconds: float = ARCHIVE_INDEX_LOCK_TIMEOUT_SECONDS,
    lock_retry_interval_seconds: float = ARCHIVE_INDEX_LOCK_RETRY_INTERVAL_SECONDS,
) -> dict[str, object]:
    summary = build_release_candidate_summary(step_results=step_results, artifact_path=artifact_path)
    _atomic_write_json(path=artifact_path, payload=summary)

    if write_archive:
        archive_artifact_path, archive_index_path = _write_archive_copy_and_index(
            step_results=step_results,
            artifact_path=artifact_path,
            command_mode=command_mode,
            created_at=created_at,
            lock_timeout_seconds=lock_timeout_seconds,
            lock_retry_interval_seconds=lock_retry_interval_seconds,
        )
        summary["archive_artifact_path"] = _render_artifact_path(archive_artifact_path)
        summary["archive_index_path"] = _render_artifact_path(archive_index_path)

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
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Write only the latest summary artifact and skip archive/index updates.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    step_results = run_release_candidate(induce_step=args.induce_step)
    command_mode = "default" if args.induce_step is None else f"induced_failure:{args.induce_step}"
    try:
        summary = write_release_candidate_summary(
            step_results=step_results,
            write_archive=not args.no_archive,
            command_mode=command_mode,
        )
    except ArchiveIndexLockTimeoutError as exc:
        _print_step_results(step_results)
        print(f"Phase 4 release-candidate archive update failed: {exc}")
        return ARCHIVE_INDEX_LOCK_TIMEOUT_EXIT_CODE
    _print_step_results(step_results)

    print(f"Release-candidate summary artifact: {summary['artifact_path']}")
    archive_artifact_path = summary.get("archive_artifact_path")
    archive_index_path = summary.get("archive_index_path")
    if isinstance(archive_artifact_path, str):
        print(f"Release-candidate archive artifact: {archive_artifact_path}")
    if isinstance(archive_index_path, str):
        print(f"Release-candidate archive index: {archive_index_path}")
    final_decision = summary["final_decision"]
    if final_decision == "GO":
        print("Phase 4 release-candidate rehearsal result: GO")
    else:
        print("Phase 4 release-candidate rehearsal result: NO_GO")

    return int(summary["summary_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
