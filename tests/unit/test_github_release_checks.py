from __future__ import annotations

import json
from pathlib import Path
import re

import scripts.check_github_release_checks as release_checks


REPO_ROOT = Path(__file__).resolve().parents[2]


def _workflow_job_display_names(path: Path) -> set[str]:
    """Parse job-level YAML names and expand the inline matrix used by CI."""
    workflow = path.read_text(encoding="utf-8")
    raw_names = re.findall(r"^    name:\s*(.+?)\s*$", workflow, flags=re.MULTILINE)
    names: set[str] = set()
    for raw_name in raw_names:
        matrix_keys = re.findall(r"\$\{\{\s*matrix\.([\w-]+)\s*\}\}", raw_name)
        if not matrix_keys:
            names.add(raw_name)
            continue
        expanded = {raw_name}
        for matrix_key in matrix_keys:
            values_match = re.search(
                rf"^        {re.escape(matrix_key)}:\s*(\[.*\])\s*$",
                workflow,
                flags=re.MULTILINE,
            )
            assert values_match is not None, matrix_key
            values = json.loads(values_match.group(1))
            expanded = {
                name.replace(f"${{{{ matrix.{matrix_key} }}}}", str(value))
                for name in expanded
                for value in values
            }
        names.update(expanded)
    return names


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


def test_required_checks_match_actual_workflow_job_display_names() -> None:
    tests_jobs = _workflow_job_display_names(REPO_ROOT / ".github/workflows/tests.yml")
    semantic_jobs = _workflow_job_display_names(
        REPO_ROOT / ".github/workflows/semantic-release-gate.yml"
    )
    externally_managed_jobs = {
        "Secrets Scan (Gitleaks)",
        "CodeQL (python)",
        "CodeQL (javascript)",
    }

    assert set(release_checks.REQUIRED_CHECKS) == (
        tests_jobs | semantic_jobs | externally_managed_jobs
    )


def _active_main_ruleset(
    *contexts: str,
    strict: bool = True,
    includes: tuple[str, ...] = ("~DEFAULT_BRANCH",),
    excludes: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "target": "branch",
        "enforcement": "active",
        "conditions": {
            "ref_name": {"include": list(includes), "exclude": list(excludes)}
        },
        "rules": [
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": strict,
                    "required_status_checks": [
                        {"context": context} for context in contexts
                    ],
                },
            }
        ],
    }


def test_branch_ruleset_check_accepts_current_strict_contexts() -> None:
    ruleset = _active_main_ruleset(
        *release_checks.BRANCH_PROTECTION_REQUIRED_CHECKS
    )

    assert release_checks.validate_branch_rulesets([ruleset]) == []


def test_branch_ruleset_check_rejects_renamed_missing_and_nonstrict_contexts() -> None:
    contexts = list(release_checks.BRANCH_PROTECTION_REQUIRED_CHECKS)
    contexts.remove("Web tests, types, accessibility, and budgets")
    contexts.append("Web tests, lint, build")

    issues = release_checks.validate_branch_rulesets(
        [_active_main_ruleset(*contexts, strict=False)]
    )

    assert any("not strict" in issue for issue in issues)
    assert any("missing current required check" in issue for issue in issues)


def test_branch_ruleset_check_allows_additional_organization_contexts() -> None:
    ruleset = _active_main_ruleset(
        *release_checks.BRANCH_PROTECTION_REQUIRED_CHECKS,
        "Organization release policy",
    )

    assert release_checks.validate_branch_rulesets([ruleset]) == []


def test_branch_ruleset_check_matches_and_excludes_ref_patterns() -> None:
    wildcard = _active_main_ruleset(
        *release_checks.BRANCH_PROTECTION_REQUIRED_CHECKS,
        includes=("refs/heads/m*",),
    )
    excluded = _active_main_ruleset(
        *release_checks.BRANCH_PROTECTION_REQUIRED_CHECKS,
        includes=("refs/heads/*",),
        excludes=("refs/heads/m*",),
    )

    assert release_checks.validate_branch_rulesets([wildcard]) == []
    assert release_checks.validate_branch_rulesets([excluded]) == [
        "no active strict status-check ruleset applies to main"
    ]


def test_branch_ruleset_check_ignores_inactive_or_other_branch_rulesets() -> None:
    inactive = _active_main_ruleset(*release_checks.BRANCH_PROTECTION_REQUIRED_CHECKS)
    inactive["enforcement"] = "disabled"
    other = _active_main_ruleset(*release_checks.BRANCH_PROTECTION_REQUIRED_CHECKS)
    other["conditions"] = {
        "ref_name": {"include": ["refs/heads/develop"], "exclude": []}
    }

    issues = release_checks.validate_branch_rulesets([inactive, other])

    assert issues == ["no active strict status-check ruleset applies to main"]
