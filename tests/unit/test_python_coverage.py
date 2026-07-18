from __future__ import annotations

import json
import math
from pathlib import Path
import re
import sys

import pytest

import scripts.check_python_coverage as python_coverage


SOURCE_PATH = "apps/api/src/alicebot_api/main.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
COVERAGE_CONTROL_PATHS = (
    REPO_ROOT / "Makefile",
    REPO_ROOT / ".github/workflows/tests.yml",
    REPO_ROOT / ".github/workflows/publish-pypi.yml",
)


def _payload(*, statement_percent: object) -> dict[str, object]:
    return {
        "files": {
            SOURCE_PATH: {
                "summary": {
                    # Coverage.py's percent_covered includes branch outcomes
                    # when branch measurement is enabled. The release contract
                    # deliberately ratchets statement/line coverage instead.
                    "percent_covered": 1.0,
                    "percent_statements_covered": statement_percent,
                }
            }
        }
    }


def test_file_coverage_uses_statement_percent_not_combined_branch_percent() -> None:
    assert python_coverage.validate_file_coverage(
        _payload(statement_percent=47.5),
        source_path=SOURCE_PATH,
        minimum_percent=45.0,
    ) == []


def test_file_coverage_rejects_statement_percent_below_floor() -> None:
    issues = python_coverage.validate_file_coverage(
        _payload(statement_percent=44.99),
        source_path=SOURCE_PATH,
        minimum_percent=45.0,
    )

    assert any("line coverage 44.99%" in issue for issue in issues)


@pytest.mark.parametrize(
    "invalid",
    (True, None, "50", math.nan, math.inf, -math.inf, -0.01, 100.01),
)
def test_file_coverage_rejects_invalid_or_nonfinite_statement_percent(
    invalid: object,
) -> None:
    issues = python_coverage.validate_file_coverage(
        _payload(statement_percent=invalid),
        source_path=SOURCE_PATH,
        minimum_percent=45.0,
    )

    assert issues
    assert "percent_statements_covered" in issues[0]


def test_file_coverage_requires_one_canonical_path_record() -> None:
    payload = _payload(statement_percent=50.0)
    files = payload["files"]
    assert isinstance(files, dict)
    files[f"/workspace/{SOURCE_PATH}"] = files[SOURCE_PATH]

    issues = python_coverage.validate_file_coverage(
        payload,
        source_path=SOURCE_PATH,
        minimum_percent=45.0,
    )

    assert issues == [
        f"coverage JSON must contain exactly one record for {SOURCE_PATH}; found 2"
    ]


def test_aggregate_coverage_weights_exact_statement_totals() -> None:
    payload = {
        "files": {
            SOURCE_PATH: {
                "summary": {
                    "covered_lines": 45,
                    "num_statements": 100,
                    "percent_statements_covered": 45.0,
                }
            },
            "apps/api/src/alicebot_api/routers/vnext_retrieval.py": {
                "summary": {
                    "covered_lines": 9,
                    "num_statements": 10,
                    "percent_statements_covered": 90.0,
                }
            },
        }
    }

    issues = python_coverage.validate_aggregate_coverage(
        payload,
        source_paths=[
            SOURCE_PATH,
            "apps/api/src/alicebot_api/routers/vnext_retrieval.py",
        ],
        minimum_percent=50.0,
    )

    assert issues == [
        "aggregate line coverage 49.09% is below the ratcheted 50.00% floor"
    ]


def test_aggregate_coverage_fails_closed_when_a_required_path_is_missing() -> None:
    payload = {
        "files": {
            SOURCE_PATH: {
                "summary": {"covered_lines": 90, "num_statements": 100}
            }
        }
    }
    issues = python_coverage.validate_aggregate_coverage(
        payload,
        source_paths=[
            SOURCE_PATH,
            "apps/api/src/alicebot_api/routers/vnext_retrieval.py",
        ],
        minimum_percent=45.0,
    )

    assert issues == [
        "coverage JSON must contain exactly one record for "
        "apps/api/src/alicebot_api/routers/vnext_retrieval.py; found 0"
    ]


@pytest.mark.parametrize(
    ("covered_lines", "num_statements"),
    ((True, 10), (1.5, 10), (5, False), (5, 4), (-1, 10), (0, 0)),
)
def test_aggregate_coverage_rejects_invalid_or_empty_statement_totals(
    covered_lines: object,
    num_statements: object,
) -> None:
    payload = {
        "files": {
            SOURCE_PATH: {
                "summary": {
                    "covered_lines": covered_lines,
                    "num_statements": num_statements,
                }
            },
            "apps/api/src/alicebot_api/routers/vnext_retrieval.py": {
                "summary": {"covered_lines": 1, "num_statements": 1}
            },
        }
    }

    issues = python_coverage.validate_aggregate_coverage(
        payload,
        source_paths=[
            SOURCE_PATH,
            "apps/api/src/alicebot_api/routers/vnext_retrieval.py",
        ],
        minimum_percent=45.0,
    )

    assert issues


def test_aggregate_coverage_rejects_an_empty_required_router_record() -> None:
    router_path = "apps/api/src/alicebot_api/routers/vnext_retrieval.py"
    payload = {
        "files": {
            SOURCE_PATH: {
                "summary": {"covered_lines": 90, "num_statements": 100}
            },
            router_path: {"summary": {"covered_lines": 0, "num_statements": 0}},
        }
    }

    issues = python_coverage.validate_aggregate_coverage(
        payload,
        source_paths=[SOURCE_PATH, router_path],
        minimum_percent=45.0,
    )

    assert issues == [
        f"coverage record for {router_path} has invalid statement totals: "
        "covered_lines=0, num_statements=0"
    ]


def test_single_path_cli_preserves_the_original_per_file_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    coverage_json = tmp_path / "coverage.json"
    coverage_json.write_text(
        json.dumps(_payload(statement_percent=47.5)),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_python_coverage.py",
            "--coverage-json",
            str(coverage_json),
            "--path",
            SOURCE_PATH,
            "--min-percent",
            "45",
        ],
    )

    assert python_coverage.main() == 0
    assert f"PASS ({SOURCE_PATH} >= 45.00%)" in capsys.readouterr().out


def test_every_coverage_control_governs_main_and_all_router_modules() -> None:
    router_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "apps/api/src/alicebot_api/routers").rglob("*.py")
        if path.name != "__init__.py"
    }
    expected_paths = {SOURCE_PATH, *router_paths}

    for control_path in COVERAGE_CONTROL_PATHS:
        invocations = [
            line
            for line in control_path.read_text(encoding="utf-8").splitlines()
            if "scripts/check_python_coverage.py --coverage-json" in line
        ]
        assert invocations, f"no coverage invocation found in {control_path}"
        for invocation in invocations:
            governed_paths = set(
                re.findall(
                    r"--path\s+(apps/api/src/alicebot_api/[^\s]+\.py)",
                    invocation,
                )
            )
            assert governed_paths == expected_paths, control_path
