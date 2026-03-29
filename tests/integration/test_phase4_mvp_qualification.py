from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.run_phase4_mvp_qualification as qualification
import scripts.verify_phase4_mvp_signoff_record as verify_signoff


def _touch_artifact(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        path.write_text("{}\n", encoding="utf-8")
    else:
        path.write_text("ok\n", encoding="utf-8")


def _build_test_contract(tmp_path: Path) -> tuple[list[qualification.QualificationStep], dict[str, str], Path]:
    rc_summary_path = tmp_path / "phase4_rc_summary.json"
    rc_archive_index_path = tmp_path / "archive" / "index.json"
    mvp_exit_manifest_path = tmp_path / "phase4_mvp_exit_manifest.json"
    signoff_path = tmp_path / "phase4_mvp_signoff_record.json"

    steps = qualification.build_qualification_steps(
        python_executable="/usr/bin/python3",
        rc_summary_path=rc_summary_path,
        rc_archive_index_path=rc_archive_index_path,
        mvp_exit_manifest_path=mvp_exit_manifest_path,
    )
    references = qualification.default_required_references(
        rc_summary_path=rc_summary_path,
        rc_archive_index_path=rc_archive_index_path,
        mvp_exit_manifest_path=mvp_exit_manifest_path,
    )
    return steps, references, signoff_path


def test_qualification_go_contract_and_signoff_verifier_pass(tmp_path: Path) -> None:
    steps, references, signoff_path = _build_test_contract(tmp_path)
    for step in steps:
        for artifact_path_value in step.required_artifacts:
            _touch_artifact(Path(artifact_path_value))

    def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
        del command, cwd
        return 0

    step_results = qualification.run_qualification(
        qualification_steps=steps,
        execute_command=_always_pass_executor,
    )
    record = qualification.write_signoff_record(
        step_results=step_results,
        artifact_path=signoff_path,
        required_references=references,
        created_at=datetime(2026, 3, 28, 12, 0, 0, tzinfo=UTC),
    )

    assert [result.status for result in step_results] == ["PASS", "PASS", "PASS", "PASS"]
    assert record["final_decision"] == "GO"
    assert record["summary_exit_code"] == 0
    assert record["blockers"] == []
    assert record["required_references"] == references

    assert verify_signoff.verify_signoff_record(
        signoff_path=signoff_path,
        expected_required_references=references,
    ) == []


def test_qualification_no_go_marks_downstream_not_run_and_sets_blockers(tmp_path: Path) -> None:
    steps, references, signoff_path = _build_test_contract(tmp_path)
    _touch_artifact(tmp_path / "phase4_rc_summary.json")
    _touch_artifact(tmp_path / "archive" / "index.json")

    def _fail_archive_verify_executor(command: tuple[str, ...], cwd: Path) -> int:
        del cwd
        if command[-1] == "scripts/verify_phase4_rc_archive.py":
            return 1
        return 0

    step_results = qualification.run_qualification(
        qualification_steps=steps,
        execute_command=_fail_archive_verify_executor,
    )
    record = qualification.write_signoff_record(
        step_results=step_results,
        artifact_path=signoff_path,
        required_references=references,
        created_at=datetime(2026, 3, 28, 12, 15, 0, tzinfo=UTC),
    )

    assert [result.status for result in step_results] == ["PASS", "FAIL", "NOT_RUN", "NOT_RUN"]
    assert record["final_decision"] == "NO_GO"
    assert record["summary_exit_code"] == 1
    assert record["failing_steps"] == [qualification.STEP_RELEASE_CANDIDATE_ARCHIVE_VERIFY]
    assert record["not_run_steps"] == [
        qualification.STEP_MVP_EXIT_MANIFEST_GENERATE,
        qualification.STEP_MVP_EXIT_MANIFEST_VERIFY,
    ]

    blocker_steps = {blocker["step"] for blocker in record["blockers"]}
    assert blocker_steps == {
        qualification.STEP_RELEASE_CANDIDATE_ARCHIVE_VERIFY,
        qualification.STEP_MVP_EXIT_MANIFEST_GENERATE,
        qualification.STEP_MVP_EXIT_MANIFEST_VERIFY,
    }

    assert verify_signoff.verify_signoff_record(
        signoff_path=signoff_path,
        expected_required_references=references,
    ) == []


def test_signoff_verifier_rejects_go_with_blockers(tmp_path: Path) -> None:
    steps, references, signoff_path = _build_test_contract(tmp_path)
    for step in steps:
        for artifact_path_value in step.required_artifacts:
            _touch_artifact(Path(artifact_path_value))

    def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
        del command, cwd
        return 0

    step_results = qualification.run_qualification(
        qualification_steps=steps,
        execute_command=_always_pass_executor,
    )
    qualification.write_signoff_record(
        step_results=step_results,
        artifact_path=signoff_path,
        required_references=references,
        created_at=datetime(2026, 3, 28, 12, 30, 0, tzinfo=UTC),
    )

    payload = json.loads(signoff_path.read_text(encoding="utf-8"))
    payload["blockers"] = [
        {
            "step": qualification.STEP_RELEASE_CANDIDATE_REHEARSAL,
            "reason": "command_failed",
            "detail": "tampered",
        }
    ]
    signoff_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    errors = verify_signoff.verify_signoff_record(
        signoff_path=signoff_path,
        expected_required_references=references,
    )
    assert any("blockers must be empty when final_decision is GO" in error for error in errors)
