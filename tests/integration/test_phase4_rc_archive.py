from __future__ import annotations

import json
from pathlib import Path

import scripts.verify_phase4_rc_archive as verify_archive


def _write_go_archive(tmp_path: Path) -> Path:
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True)
    archive_summary_path = archive_dir / "20260328T100000Z_phase4_rc_summary.json"
    latest_summary_path = tmp_path / "phase4_rc_summary.json"
    index_path = archive_dir / verify_archive.ARCHIVE_INDEX_NAME

    summary_payload = {
        "artifact_version": verify_archive.SUMMARY_ARTIFACT_VERSION,
        "artifact_path": str(archive_summary_path),
        "final_decision": "GO",
        "summary_exit_code": 0,
        "failing_steps": [],
        "ordered_steps": ["phase4_acceptance", "phase4_validation_matrix"],
    }
    archive_summary_path.write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    latest_summary_path.write_text(
        json.dumps(
            {**summary_payload, "artifact_path": str(latest_summary_path)},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    index_path.write_text(
        json.dumps(
            {
                "archive_dir": str(archive_dir),
                "artifact_version": verify_archive.ARCHIVE_INDEX_VERSION,
                "entries": [
                    {
                        "archive_artifact_path": str(archive_summary_path),
                        "command_mode": "default",
                        "created_at": "2026-03-28T10:00:00Z",
                        "failing_steps": [],
                        "final_decision": "GO",
                        "summary_exit_code": 0,
                    }
                ],
                "latest_summary_path": str(latest_summary_path),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return index_path


def test_verify_phase4_rc_archive_passes_for_valid_archive(tmp_path: Path) -> None:
    index_path = _write_go_archive(tmp_path)

    assert verify_archive.verify_archive_index(index_path=index_path) == []


def test_verify_phase4_rc_archive_detects_summary_mismatch(tmp_path: Path) -> None:
    index_path = _write_go_archive(tmp_path)
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    index_payload["entries"][0]["summary_exit_code"] = 1
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    errors = verify_archive.verify_archive_index(index_path=index_path)
    assert any("summary_exit_code mismatch with archive summary" in error for error in errors)


def test_verify_phase4_rc_archive_detects_missing_archive_artifact(tmp_path: Path) -> None:
    index_path = _write_go_archive(tmp_path)
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    archive_path = Path(index_payload["entries"][0]["archive_artifact_path"])
    archive_path.unlink()

    errors = verify_archive.verify_archive_index(index_path=index_path)
    assert any("archive_artifact_path missing file" in error for error in errors)


def test_verify_phase4_rc_archive_detects_stale_lock_file(tmp_path: Path) -> None:
    index_path = _write_go_archive(tmp_path)
    lock_path = tmp_path / "archive" / verify_archive.ARCHIVE_INDEX_LOCK_NAME
    lock_path.write_text("stale-lock\n", encoding="utf-8")

    errors = verify_archive.verify_archive_index(index_path=index_path)
    assert any("lock file should not persist" in error for error in errors)
