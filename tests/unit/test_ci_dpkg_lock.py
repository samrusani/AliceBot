"""CI must wait for the dpkg lock before any apt-using step.

Fresh ubuntu-24.04 runners still run unattended-upgrades. That holds
``/var/lib/dpkg/lock-frontend``. ``playwright install --with-deps`` and
``apt-get install postgresql-client-16`` then block until the job
timeout. Observed on main after #396 and twice on #397.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci_wait_for_dpkg_lock.sh"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
OPS_WORKFLOW = ROOT / ".github" / "workflows" / "ops-evidence.yml"


def test_wait_script_stops_unattended_upgrades_and_waits_for_the_lock() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert SCRIPT.stat().st_mode & 0o111
    assert "unattended-upgrades.service" in text
    assert "/var/lib/dpkg/lock-frontend" in text
    assert "fuser" in text
    assert "still held after 90s" in text
    assert "exit 1" in text
    assert 'uname -s' in text
    assert "not Linux, nothing to do" in text


def test_web_job_waits_from_repo_root_before_playwright_with_deps() -> None:
    """The web job defaults to apps/web. The wait script lives at repo root."""

    text = TESTS_WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/ci_wait_for_dpkg_lock.sh" in text
    assert text.index("ci_wait_for_dpkg_lock.sh") < text.index("setup:browser:linux")
    assert "working-directory: ${{ github.workspace }}" in text
    wait_at = text.index("Wait for dpkg lock")
    workspace_at = text.index("working-directory: ${{ github.workspace }}", wait_at)
    browser_at = text.index("Install browser runtime", wait_at)
    assert workspace_at < browser_at


def test_ops_job_waits_before_postgresql_client_apt() -> None:
    text = OPS_WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/ci_wait_for_dpkg_lock.sh" in text
    assert text.index("ci_wait_for_dpkg_lock.sh") < text.index("postgresql-client-16")
    assert "DEBIAN_FRONTEND: noninteractive" in text
