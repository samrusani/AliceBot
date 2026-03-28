from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import scripts.run_phase4_release_candidate as release_candidate
import scripts.verify_phase4_rc_archive as verify_archive


def _always_pass_executor(command: tuple[str, ...], cwd: Path) -> int:
    del command, cwd
    return 0


def _write_go_archive(tmp_path: Path) -> Path:
    results = release_candidate.run_release_candidate(execute_command=_always_pass_executor)
    summary_path = tmp_path / "phase4_rc_summary.json"
    release_candidate.write_release_candidate_summary(
        step_results=results,
        artifact_path=summary_path,
        created_at=datetime(2026, 3, 28, 10, 0, 0, tzinfo=UTC),
    )
    return tmp_path / "archive" / "index.json"


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
