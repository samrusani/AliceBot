from __future__ import annotations

import scripts.check_github_release_checks as release_checks


def test_exact_sha_check_gate_requires_every_success() -> None:
    runs = [
        {"name": name, "conclusion": "success"}
        for name in release_checks.REQUIRED_CHECKS
    ]

    assert release_checks.validate_check_runs(runs) == []


def test_exact_sha_check_gate_reports_missing_and_failed() -> None:
    runs = [
        {"name": name, "conclusion": "success"}
        for name in release_checks.REQUIRED_CHECKS[2:]
    ]
    runs.append(
        {"name": release_checks.REQUIRED_CHECKS[0], "conclusion": "failure"}
    )

    issues = release_checks.validate_check_runs(runs)

    assert any("did not succeed" in issue for issue in issues)
    assert any(release_checks.REQUIRED_CHECKS[1] in issue for issue in issues)


def test_exact_sha_check_gate_uses_latest_rerun_only() -> None:
    required = release_checks.REQUIRED_CHECKS[0]
    successful_latest = [
        {"name": name, "id": 10, "conclusion": "success"}
        for name in release_checks.REQUIRED_CHECKS
    ]
    successful_latest.append({"name": required, "id": 9, "conclusion": "failure"})
    assert release_checks.validate_check_runs(successful_latest) == []

    failed_latest = [
        {"name": name, "id": 10, "conclusion": "success"}
        for name in release_checks.REQUIRED_CHECKS
    ]
    failed_latest.append({"name": required, "id": 11, "conclusion": "failure"})

    issues = release_checks.validate_check_runs(failed_latest)
    assert any(required in issue and "latest" in issue for issue in issues)
