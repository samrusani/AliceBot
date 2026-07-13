#!/usr/bin/env python3
"""Fail closed when a release-critical Python file loses meaningful coverage."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path, PurePosixPath
from typing import Any


def _normalized_path(value: str) -> str:
    return str(PurePosixPath(value.replace("\\", "/")))


def validate_file_coverage(
    payload: dict[str, Any],
    *,
    source_path: str,
    minimum_percent: float,
) -> list[str]:
    files = payload.get("files")
    if not isinstance(files, dict):
        return ["coverage JSON is missing its files object"]

    expected = _normalized_path(source_path)
    matches = [
        (str(path), value)
        for path, value in files.items()
        if _normalized_path(str(path)) == expected
        or _normalized_path(str(path)).endswith(f"/{expected}")
    ]
    if len(matches) != 1:
        return [
            f"coverage JSON must contain exactly one record for {source_path}; "
            f"found {len(matches)}"
        ]

    reported_path, record = matches[0]
    summary = record.get("summary") if isinstance(record, dict) else None
    percent = (
        summary.get("percent_statements_covered")
        if isinstance(summary, dict)
        else None
    )
    if isinstance(percent, bool) or not isinstance(percent, (int, float)):
        return [
            f"coverage record for {reported_path} has no numeric "
            "percent_statements_covered"
        ]
    if not math.isfinite(float(percent)):
        return [
            f"coverage record for {reported_path} has non-finite "
            "percent_statements_covered"
        ]
    if not 0.0 <= float(percent) <= 100.0:
        return [
            f"coverage record for {reported_path} has out-of-range "
            "percent_statements_covered"
        ]
    if percent < minimum_percent:
        return [
            f"{source_path} line coverage {percent:.2f}% is below the "
            f"ratcheted {minimum_percent:.2f}% floor"
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-json", type=Path, required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--min-percent", type=float, required=True)
    args = parser.parse_args()

    if not 0.0 < args.min_percent <= 100.0:
        parser.error("--min-percent must be greater than 0 and at most 100")
    try:
        payload = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Python per-file coverage: FAIL\n - could not read coverage JSON: {exc}")
        return 1
    if not isinstance(payload, dict):
        print("Python per-file coverage: FAIL\n - coverage JSON root must be an object")
        return 1

    issues = validate_file_coverage(
        payload,
        source_path=args.path,
        minimum_percent=args.min_percent,
    )
    if issues:
        print("Python per-file coverage: FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1
    print(
        f"Python per-file coverage: PASS ({args.path} >= {args.min_percent:.2f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
