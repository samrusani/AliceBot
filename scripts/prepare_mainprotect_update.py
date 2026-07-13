#!/usr/bin/env python3
"""Prepare a minimal, reviewable MainProtect ruleset update payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.check_github_release_checks import (
    BRANCH_PROTECTION_REQUIRED_CHECKS,
    validate_branch_rulesets,
)


_UPDATE_FIELDS = (
    "name",
    "target",
    "enforcement",
    "bypass_actors",
    "conditions",
    "rules",
)


def prepare_mainprotect_update(ruleset: dict[str, Any]) -> dict[str, Any]:
    """Preserve current controls while replacing only the required check set."""

    if ruleset.get("name") != "MainProtect":
        raise ValueError("ruleset name must be MainProtect")
    if ruleset.get("target") != "branch" or ruleset.get("enforcement") != "active":
        raise ValueError("MainProtect must be an active branch ruleset")
    payload = {field: ruleset[field] for field in _UPDATE_FIELDS if field in ruleset}
    if set(payload) != set(_UPDATE_FIELDS):
        missing = sorted(set(_UPDATE_FIELDS) - set(payload))
        raise ValueError(f"ruleset response is missing update fields: {missing}")

    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise ValueError("MainProtect rules must be a list")
    status_rules = [
        rule
        for rule in rules
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks"
    ]
    if len(status_rules) != 1:
        raise ValueError("MainProtect must contain exactly one required_status_checks rule")
    status_rules[0]["parameters"] = {
        "required_status_checks": [
            {"context": context} for context in BRANCH_PROTECTION_REQUIRED_CHECKS
        ],
        "strict_required_status_checks_policy": True,
    }
    issues = validate_branch_rulesets([payload])
    if issues:
        raise ValueError(f"prepared MainProtect payload is invalid: {issues}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    current = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(current, dict):
        raise ValueError("ruleset response must be a JSON object")
    payload = prepare_mainprotect_update(current)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"MainProtect update payload: PASS ({args.output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
