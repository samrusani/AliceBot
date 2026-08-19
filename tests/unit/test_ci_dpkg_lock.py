"""CI must not let apt-get sit until the job timeout.

On #397 the dpkg-lock wait finished in one second. ``playwright
install --with-deps`` and bare ``apt-get`` then sat 16 and 30 minutes.
Web CI installs Chromium without ``--with-deps``. Ops apt-get is
timed and retried.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WAIT_SCRIPT = ROOT / "scripts" / "ci_wait_for_dpkg_lock.sh"
APT_SCRIPT = ROOT / "scripts" / "ci_apt_get.sh"
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"
OPS_WORKFLOW = ROOT / ".github" / "workflows" / "ops-evidence.yml"


def test_wait_script_masks_unattended_upgrades_and_fail_closes() -> None:
    text = WAIT_SCRIPT.read_text(encoding="utf-8")
    assert WAIT_SCRIPT.stat().st_mode & 0o111
    assert "unattended-upgrades.service" in text
    assert "systemctl mask" in text
    assert "/var/lib/dpkg/lock-frontend" in text
    assert "fuser" in text
    assert "still held after 90s" in text
    assert "exit 1" in text
    assert "not Linux, nothing to do" in text


def test_apt_script_times_out_and_retries() -> None:
    text = APT_SCRIPT.read_text(encoding="utf-8")
    assert APT_SCRIPT.stat().st_mode & 0o111
    assert "ci_wait_for_dpkg_lock.sh" in text
    assert "setsid --wait timeout" in text
    assert "--kill-after=15s" in text
    assert "Acquire::http::Timeout=15" in text
    assert "all attempts failed" in text
    assert "exit 1" in text


def test_web_job_installs_chromium_without_apt() -> None:
    text = TESTS_WORKFLOW.read_text(encoding="utf-8")
    assert "run: pnpm exec playwright install chromium" in text
    assert "run: pnpm run setup:browser:linux" not in text
    install = text.split("- name: Install browser runtime", 1)[1].split("- name:", 1)[0]
    assert "timeout-minutes: 8" in install
    assert "--with-deps" not in install


def test_ops_job_uses_timed_apt_before_postgresql_client() -> None:
    text = OPS_WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/ci_apt_get.sh postgresql-client-16" in text
    assert text.index("ci_apt_get.sh") < text.index("postgresql-client-16")
    select = text.split("- name: Select PostgreSQL 16 client tools", 1)[1]
    assert "timeout-minutes: 10" in select.split("- name:", 1)[0]
    assert "sudo apt-get update" not in text
