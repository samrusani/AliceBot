from __future__ import annotations

import json
from pathlib import Path

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


def test_induced_failure_reports_no_go_and_preserves_partial_evidence(tmp_path: Path) -> None:
    results = release_candidate.run_release_candidate(
        induce_step=release_candidate.STEP_PHASE4_VALIDATION_MATRIX,
        execute_command=_pass_except_induced_executor,
    )

    summary_path = tmp_path / "phase4_rc_summary.json"
    summary = release_candidate.write_release_candidate_summary(
        step_results=results,
        artifact_path=summary_path,
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
