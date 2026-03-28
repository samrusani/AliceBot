from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.generate_phase4_mvp_exit_manifest as generate_manifest
import scripts.run_phase4_release_candidate as release_candidate
import scripts.verify_phase4_mvp_exit_manifest as verify_manifest


def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
    del command, cwd
    return 0


def _pass_except_induced_executor(command: tuple[str, ...], cwd: Path) -> int:
    del cwd
    if "-c" in command and "Induced phase4 release-candidate failure" in command[-1]:
        return release_candidate.INDUCED_FAILURE_EXIT_CODE
    return 0


def _write_go_archive(tmp_path: Path, created_at: datetime) -> Path:
    step_results = release_candidate.run_release_candidate(execute_command=_always_pass_executor)
    summary_path = tmp_path / "phase4_rc_summary.json"
    release_candidate.write_release_candidate_summary(
        step_results=step_results,
        artifact_path=summary_path,
        created_at=created_at,
    )
    return tmp_path / "archive" / "index.json"


def _write_no_go_archive(tmp_path: Path, created_at: datetime) -> Path:
    step_results = release_candidate.run_release_candidate(
        induce_step=release_candidate.STEP_PHASE4_VALIDATION_MATRIX,
        execute_command=_pass_except_induced_executor,
    )
    summary_path = tmp_path / "phase4_rc_summary.json"
    release_candidate.write_release_candidate_summary(
        step_results=step_results,
        artifact_path=summary_path,
        created_at=created_at,
        command_mode=f"induced_failure:{release_candidate.STEP_PHASE4_VALIDATION_MATRIX}",
    )
    return tmp_path / "archive" / "index.json"


def test_generate_manifest_selects_latest_go_entry_and_verify_passes(tmp_path: Path) -> None:
    index_path = _write_go_archive(tmp_path, datetime(2026, 3, 28, 10, 0, 0, tzinfo=UTC))
    _write_no_go_archive(tmp_path, datetime(2026, 3, 28, 10, 15, 0, tzinfo=UTC))
    manifest_path = tmp_path / "phase4_mvp_exit_manifest.json"

    manifest = generate_manifest.generate_manifest(index_path=index_path, manifest_path=manifest_path)

    assert manifest["artifact_version"] == generate_manifest.MANIFEST_ARTIFACT_VERSION
    assert manifest["artifact_path"] == str(manifest_path)
    assert manifest["phase"] == "phase4"
    assert manifest["release_gate"] == "mvp"
    assert manifest["compatibility_validation_commands"] == list(
        generate_manifest.REQUIRED_COMPATIBILITY_COMMANDS
    )
    assert manifest["decision"] == {
        "final_decision": "GO",
        "summary_exit_code": 0,
        "failing_steps": [],
    }

    source_references = manifest["source_references"]
    assert source_references["archive_index_path"] == str(index_path)
    assert source_references["archive_artifact_path"] == str(
        tmp_path / "archive" / "20260328T100000Z_phase4_rc_summary.json"
    )
    assert source_references["archive_entry_created_at"] == "2026-03-28T10:00:00Z"
    assert source_references["archive_entry_command_mode"] == "default"

    ordered_steps = manifest["ordered_steps"]
    assert ordered_steps == list(release_candidate.STEP_IDS)
    assert manifest["step_status_by_id"] == {step_id: "PASS" for step_id in ordered_steps}
    assert verify_manifest.verify_manifest(manifest_path=manifest_path) == []


def test_verify_manifest_fails_when_referenced_archive_artifact_missing(tmp_path: Path) -> None:
    index_path = _write_go_archive(tmp_path, datetime(2026, 3, 28, 10, 30, 0, tzinfo=UTC))
    manifest_path = tmp_path / "phase4_mvp_exit_manifest.json"
    manifest = generate_manifest.generate_manifest(index_path=index_path, manifest_path=manifest_path)

    source_references = manifest["source_references"]
    archive_artifact_path = Path(source_references["archive_artifact_path"])
    archive_artifact_path.unlink()

    errors = verify_manifest.verify_manifest(manifest_path=manifest_path)
    assert any("archive_artifact_path missing file" in error for error in errors)


def test_verify_manifest_fails_when_archive_entry_index_is_tampered(tmp_path: Path) -> None:
    _write_go_archive(tmp_path, datetime(2026, 3, 28, 10, 0, 0, tzinfo=UTC))
    index_path = _write_go_archive(tmp_path, datetime(2026, 3, 28, 10, 15, 0, tzinfo=UTC))
    manifest_path = tmp_path / "phase4_mvp_exit_manifest.json"
    generate_manifest.generate_manifest(index_path=index_path, manifest_path=manifest_path)

    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_references = manifest_payload["source_references"]
    source_references["archive_entry_index"] = 0
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    errors = verify_manifest.verify_manifest(manifest_path=manifest_path)
    assert any("archive_entry_index" in error for error in errors)
