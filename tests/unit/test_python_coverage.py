from __future__ import annotations

import math

import pytest

import scripts.check_python_coverage as python_coverage


SOURCE_PATH = "apps/api/src/alicebot_api/main.py"


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
