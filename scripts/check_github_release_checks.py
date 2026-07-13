#!/usr/bin/env python3
"""Require successful GitHub check runs on the exact release commit."""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any
from urllib.request import Request, urlopen


# Protected-path metadata is enforced on the PR head and is not copied onto a
# merge commit. These are the exact-SHA push checks plus the new release gates.
REQUIRED_CHECKS = (
    "Secrets Scan (Gitleaks)",
    "CodeQL (python)",
    "CodeQL (javascript)",
    "Unit tests + live eval battery (SQLite)",
    "Python correctness lint, types, and release truth",
    "Installed wheel + sdist contract",
    "Python 3.13 install smoke",
    "Python 3.14 install smoke",
    "Integration tests (Postgres + pgvector, role separation)",
    "Web tests, types, accessibility, and budgets",
    "Semantic eval attestation (exact SHA)",
)


def validate_check_runs(check_runs: list[dict[str, Any]]) -> list[str]:
    runs_by_name: dict[str, list[tuple[int, str]]] = {}
    for check_run in check_runs:
        name = str(check_run.get("name", ""))
        conclusion = str(check_run.get("conclusion", ""))
        run_id = check_run.get("id")
        # GitHub check-run ids are monotonically increasing. Using the newest
        # run prevents an older successful attempt from masking a later failed
        # rerun on the same release commit.
        sortable_id = run_id if isinstance(run_id, int) else -1
        runs_by_name.setdefault(name, []).append((sortable_id, conclusion))

    issues: list[str] = []
    for required in REQUIRED_CHECKS:
        runs = runs_by_name.get(required, [])
        if not runs:
            issues.append(f"missing required exact-SHA check: {required}")
            continue
        _latest_id, latest_conclusion = max(runs, key=lambda item: item[0])
        if latest_conclusion != "success":
            issues.append(
                "latest required exact-SHA check did not succeed: "
                f"{required} ({latest_conclusion or 'pending'})"
            )
    return issues


def fetch_check_runs(*, repository: str, sha: str, token: str) -> list[dict[str, Any]]:
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is None:
        raise ValueError(f"invalid GitHub repository: {repository!r}")
    if re.fullmatch(r"[0-9a-fA-F]{40}", sha) is None:
        raise ValueError(f"invalid commit SHA: {sha!r}")
    url = f"https://api.github.com/repos/{repository}/commits/{sha}/check-runs?per_page=100"
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "alice-release-check/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - validated GitHub origin
        payload = json.load(response)
    check_runs = payload.get("check_runs") if isinstance(payload, dict) else None
    if not isinstance(check_runs, list):
        raise ValueError("GitHub check-runs response is malformed")
    return [item for item in check_runs if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        parser.error("GITHUB_TOKEN is required")

    issues = validate_check_runs(
        fetch_check_runs(repository=args.repo, sha=args.sha, token=token)
    )
    if issues:
        print("Exact-SHA GitHub checks: FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1
    print("Exact-SHA GitHub checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
