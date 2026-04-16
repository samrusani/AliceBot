from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_quickstart_documents_stdout_default_and_bounded_file_logging() -> None:
    quickstart = (
        REPO_ROOT / "docs" / "quickstart" / "local-setup-and-first-result.md"
    ).read_text(encoding="utf-8")

    assert "stdout only" in quickstart
    assert "APP_LOG_MODE=file" in quickstart
    assert "APP_LOG_PATH=/var/log/alicebot/api.log" in quickstart
    assert "APP_LOG_MAX_BYTES=10485760" in quickstart
    assert "APP_LOG_BACKUP_COUNT=5" in quickstart


def test_release_runbook_recommends_systemd_and_journald() -> None:
    runbook = (
        REPO_ROOT / "docs" / "runbooks" / "v0.4.0-public-release-runbook.md"
    ).read_text(encoding="utf-8")

    assert "systemd" in runbook
    assert "journald" in runbook
    assert "StandardOutput=journal" in runbook
    assert "APP_LOG_MODE=stdout" in runbook
