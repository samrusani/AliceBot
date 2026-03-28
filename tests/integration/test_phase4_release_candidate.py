from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import threading

import pytest

import scripts.run_phase4_release_candidate as release_candidate


def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
    del command, cwd
    return 0


def _pass_except_induced_executor(command: tuple[str, ...], cwd: Path) -> int:
    del cwd
    if "-c" in command and "Induced phase4 release-candidate failure" in command[-1]:
        return release_candidate.INDUCED_FAILURE_EXIT_CODE
    return 0


def test_release_candidate_step_sequence_and_go_summary_contract(tmp_path: Path) -> None:
    steps = release_candidate.build_release_candidate_steps(python_executable="/usr/bin/python3")

    assert [step.step for step in steps] == [
        release_candidate.STEP_CONTROL_DOC_TRUTH,
        release_candidate.STEP_PHASE4_ACCEPTANCE,
        release_candidate.STEP_PHASE4_READINESS,
        release_candidate.STEP_PHASE4_VALIDATION_MATRIX,
        release_candidate.STEP_PHASE3_COMPAT_VALIDATION,
        release_candidate.STEP_PHASE2_COMPAT_VALIDATION,
        release_candidate.STEP_MVP_COMPAT_VALIDATION,
    ]

    assert steps[0].command == ("/usr/bin/python3", "scripts/check_control_doc_truth.py")
    assert steps[1].command == ("/usr/bin/python3", "scripts/run_phase4_acceptance.py")
    assert steps[2].command == ("/usr/bin/python3", "scripts/run_phase4_readiness_gates.py")
    assert steps[3].command == ("/usr/bin/python3", "scripts/run_phase4_validation_matrix.py")
    assert steps[4].command == ("/usr/bin/python3", "scripts/run_phase3_validation_matrix.py")
    assert steps[5].command == ("/usr/bin/python3", "scripts/run_phase2_validation_matrix.py")
    assert steps[6].command == ("/usr/bin/python3", "scripts/run_mvp_validation_matrix.py")

    results = release_candidate.run_release_candidate(execute_command=_always_pass_executor)
    summary_path = tmp_path / "phase4_rc_summary.json"
    summary = release_candidate.write_release_candidate_summary(
        step_results=results,
        artifact_path=summary_path,
        created_at=datetime(2026, 3, 28, 8, 0, 0, tzinfo=UTC),
    )

    assert all(result.status == "PASS" for result in results)
    assert summary["artifact_version"] == "phase4_rc_summary.v1"
    assert summary["final_decision"] == "GO"
    assert summary["summary_exit_code"] == 0
    assert summary["ordered_steps"] == list(release_candidate.STEP_IDS)
    assert summary["executed_steps"] == len(release_candidate.STEP_IDS)
    assert summary["total_steps"] == len(release_candidate.STEP_IDS)
    assert summary["failing_steps"] == []

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["artifact_version"] == "phase4_rc_summary.v1"
    assert payload["steps"][0]["status"] == "PASS"
    assert payload["steps"][3]["step"] == release_candidate.STEP_PHASE4_VALIDATION_MATRIX

    archive_artifact_path = tmp_path / "archive" / "20260328T080000Z_phase4_rc_summary.json"
    archive_index_path = tmp_path / "archive" / "index.json"
    assert summary["archive_artifact_path"] == str(archive_artifact_path)
    assert summary["archive_index_path"] == str(archive_index_path)
    assert archive_artifact_path.exists()
    assert archive_index_path.exists()

    archive_payload = json.loads(archive_artifact_path.read_text(encoding="utf-8"))
    assert archive_payload["artifact_path"] == str(archive_artifact_path)
    assert archive_payload["final_decision"] == "GO"

    index_payload = json.loads(archive_index_path.read_text(encoding="utf-8"))
    assert index_payload["artifact_version"] == release_candidate.ARCHIVE_INDEX_VERSION
    assert index_payload["latest_summary_path"] == str(summary_path)
    assert index_payload["archive_dir"] == str(tmp_path / "archive")
    assert index_payload["entries"] == [
        {
            "created_at": "2026-03-28T08:00:00Z",
            "archive_artifact_path": str(archive_artifact_path),
            "final_decision": "GO",
            "summary_exit_code": 0,
            "failing_steps": [],
            "command_mode": "default",
        }
    ]


def test_induced_failure_reports_no_go_and_preserves_partial_evidence(tmp_path: Path) -> None:
    results = release_candidate.run_release_candidate(
        induce_step=release_candidate.STEP_PHASE4_VALIDATION_MATRIX,
        execute_command=_pass_except_induced_executor,
    )

    summary_path = tmp_path / "phase4_rc_summary.json"
    summary = release_candidate.write_release_candidate_summary(
        step_results=results,
        artifact_path=summary_path,
        command_mode=f"induced_failure:{release_candidate.STEP_PHASE4_VALIDATION_MATRIX}",
        created_at=datetime(2026, 3, 28, 8, 15, 0, tzinfo=UTC),
    )

    assert [result.step for result in results] == list(release_candidate.STEP_IDS)
    assert [result.status for result in results[:3]] == ["PASS", "PASS", "PASS"]

    induced_failure = results[3]
    assert induced_failure.step == release_candidate.STEP_PHASE4_VALIDATION_MATRIX
    assert induced_failure.status == "FAIL"
    assert induced_failure.exit_code == release_candidate.INDUCED_FAILURE_EXIT_CODE
    assert induced_failure.induced_failure is True

    assert [result.status for result in results[4:]] == ["NOT_RUN", "NOT_RUN", "NOT_RUN"]
    assert all(result.exit_code is None for result in results[4:])

    assert summary["final_decision"] == "NO_GO"
    assert summary["summary_exit_code"] == 1
    assert summary["executed_steps"] == 4
    assert summary["failing_steps"] == [release_candidate.STEP_PHASE4_VALIDATION_MATRIX]

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["final_decision"] == "NO_GO"
    assert payload["steps"][3]["status"] == "FAIL"
    assert payload["steps"][4]["status"] == "NOT_RUN"

    archive_index_path = tmp_path / "archive" / "index.json"
    index_payload = json.loads(archive_index_path.read_text(encoding="utf-8"))
    assert index_payload["entries"] == [
        {
            "created_at": "2026-03-28T08:15:00Z",
            "archive_artifact_path": str(
                tmp_path / "archive" / "20260328T081500Z_phase4_rc_summary.json"
            ),
            "final_decision": "NO_GO",
            "summary_exit_code": 1,
            "failing_steps": [release_candidate.STEP_PHASE4_VALIDATION_MATRIX],
            "command_mode": f"induced_failure:{release_candidate.STEP_PHASE4_VALIDATION_MATRIX}",
        }
    ]


def test_archive_index_is_append_only_and_avoids_same_second_overwrite(tmp_path: Path) -> None:
    first_results = release_candidate.run_release_candidate(execute_command=_always_pass_executor)
    second_results = release_candidate.run_release_candidate(execute_command=_always_pass_executor)
    summary_path = tmp_path / "phase4_rc_summary.json"

    release_candidate.write_release_candidate_summary(
        step_results=first_results,
        artifact_path=summary_path,
        created_at=datetime(2026, 3, 28, 9, 0, 0, tzinfo=UTC),
    )
    release_candidate.write_release_candidate_summary(
        step_results=second_results,
        artifact_path=summary_path,
        created_at=datetime(2026, 3, 28, 9, 0, 0, tzinfo=UTC),
    )

    archive_dir = tmp_path / "archive"
    first_archive = archive_dir / "20260328T090000Z_phase4_rc_summary.json"
    second_archive = archive_dir / "20260328T090000Z_001_phase4_rc_summary.json"
    assert first_archive.exists()
    assert second_archive.exists()

    index_payload = json.loads((archive_dir / "index.json").read_text(encoding="utf-8"))
    assert len(index_payload["entries"]) == 2
    assert index_payload["entries"][0]["archive_artifact_path"] == str(first_archive)
    assert index_payload["entries"][1]["archive_artifact_path"] == str(second_archive)


def test_archive_index_concurrent_writes_retain_all_entries(tmp_path: Path) -> None:
    summary_path = tmp_path / "phase4_rc_summary.json"
    created_at = datetime(2026, 3, 28, 9, 30, 0, tzinfo=UTC)
    run_count = 4
    barrier = threading.Barrier(run_count)
    failures: list[str] = []

    def _writer() -> None:
        try:
            step_results = release_candidate.run_release_candidate(execute_command=_always_pass_executor)
            barrier.wait()
            release_candidate.write_release_candidate_summary(
                step_results=step_results,
                artifact_path=summary_path,
                created_at=created_at,
            )
        except Exception as exc:  # pragma: no cover - defensive guard for threaded assertions
            failures.append(str(exc))

    threads = [threading.Thread(target=_writer) for _ in range(run_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    archive_dir = tmp_path / "archive"
    index_payload = json.loads((archive_dir / "index.json").read_text(encoding="utf-8"))
    archive_paths = [entry["archive_artifact_path"] for entry in index_payload["entries"]]
    assert len(archive_paths) == run_count
    assert len(set(archive_paths)) == run_count
    assert all(Path(path).exists() for path in archive_paths)
    assert (archive_dir / "20260328T093000Z_phase4_rc_summary.json").exists()
    assert (archive_dir / "20260328T093000Z_001_phase4_rc_summary.json").exists()
    assert (archive_dir / "20260328T093000Z_002_phase4_rc_summary.json").exists()
    assert (archive_dir / "20260328T093000Z_003_phase4_rc_summary.json").exists()


def test_archive_index_lock_timeout_is_explicit_and_bounded(tmp_path: Path) -> None:
    step_results = release_candidate.run_release_candidate(execute_command=_always_pass_executor)
    summary_path = tmp_path / "phase4_rc_summary.json"
    lock_path = tmp_path / "archive" / release_candidate.ARCHIVE_INDEX_LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("held-by-test\n", encoding="utf-8")

    with pytest.raises(
        release_candidate.ArchiveIndexLockTimeoutError,
        match=r"Timed out acquiring archive index lock at .*index\.lock",
    ):
        release_candidate.write_release_candidate_summary(
            step_results=step_results,
            artifact_path=summary_path,
            created_at=datetime(2026, 3, 28, 9, 45, 0, tzinfo=UTC),
            lock_timeout_seconds=0.02,
            lock_retry_interval_seconds=0.005,
        )

    assert summary_path.exists()
    assert not (tmp_path / "archive" / "index.json").exists()
