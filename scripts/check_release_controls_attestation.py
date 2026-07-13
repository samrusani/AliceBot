#!/usr/bin/env python3
"""Validate the release-specific repository-control attestation.

The attestation is a credentialless GitHub repository variable.  It records a
recent operator readback of release controls; it is not a secret and it does
not replace the exact-SHA semantic-evaluation attestation.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
import os
import re
from collections.abc import Mapping, Sequence
from typing import Any


ATTESTATION_SCHEMA_VERSION = "alice_release_controls_attestation_v1"
ATTESTATION_ENVIRONMENT_VARIABLE = "ALICE_RELEASE_CONTROLS_ATTESTATION"
MAX_ATTESTATION_BYTES = 8_192
MAX_ATTESTATION_AGE = timedelta(hours=24)
MAX_ATTESTATION_VALIDITY = timedelta(hours=24)

REQUIRED_CONTROLS: tuple[str, ...] = (
    "pypi_environment_protected",
    "pypi_required_reviewers",
    "pypi_deployment_policy_restricted",
    "main_branch_protected",
    "main_required_checks_strict",
    "stable_tags_protected",
    "immutable_releases_enabled",
    "trusted_publishing_enabled",
    "no_long_lived_pypi_credentials",
    "exposed_provider_credentials_revoked",
    "exact_sha_release_checks_required",
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "repository",
        "release_sha",
        "release_tag",
        "verified_at",
        "expires_at",
        "controls",
    }
)
_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
_STABLE_TAG_PATTERN = re.compile(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
_UTC_TIMESTAMP_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class _DuplicateKeyError(ValueError):
    pass


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError
        result[key] = value
    return result


def _reject_nonstandard_number(_value: str) -> None:
    raise ValueError


def _parse_strict_json(raw_attestation: str) -> Any:
    return json.loads(
        raw_attestation,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_nonstandard_number,
    )


def _closed_key_issues(
    value: Mapping[str, Any],
    *,
    expected: frozenset[str],
    context: str,
) -> list[str]:
    actual = frozenset(value)
    issues: list[str] = []
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        issues.append(f"{context} is missing required fields: {', '.join(missing)}")
    if unknown:
        issues.append(f"{context} contains {len(unknown)} unknown field(s)")
    return issues


def _parse_utc_timestamp(value: Any, *, field: str, issues: list[str]) -> datetime | None:
    if not isinstance(value, str) or _UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
        issues.append(f"release-controls attestation {field} must be UTC YYYY-MM-DDTHH:MM:SSZ")
        return None
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        issues.append(f"release-controls attestation {field} is not a valid calendar timestamp")
        return None


def validate_release_controls_attestation(
    raw_attestation: str | None,
    *,
    expected_repository: str,
    expected_release_sha: str,
    expected_release_tag: str,
    now: datetime | None = None,
) -> list[str]:
    """Return fail-closed validation issues for a repository-control claim."""

    issues: list[str] = []
    if _REPOSITORY_PATTERN.fullmatch(expected_repository) is None:
        issues.append("expected repository must be an owner/name GitHub repository")
    if _SHA_PATTERN.fullmatch(expected_release_sha) is None:
        issues.append("expected release SHA must be 40 lowercase hexadecimal characters")
    if _STABLE_TAG_PATTERN.fullmatch(expected_release_tag) is None:
        issues.append("expected release tag must be a stable vMAJOR.MINOR.PATCH tag")

    if raw_attestation is None or not raw_attestation.strip():
        issues.append("release-controls attestation is missing")
        return issues
    if len(raw_attestation.encode("utf-8")) > MAX_ATTESTATION_BYTES:
        issues.append("release-controls attestation exceeds the size limit")
        return issues

    try:
        payload = _parse_strict_json(raw_attestation)
    except (_DuplicateKeyError, json.JSONDecodeError, RecursionError, ValueError):
        issues.append("release-controls attestation is not valid strict JSON")
        return issues
    if not isinstance(payload, dict):
        issues.append("release-controls attestation must be a JSON object")
        return issues

    issues.extend(
        _closed_key_issues(
            payload,
            expected=_TOP_LEVEL_KEYS,
            context="release-controls attestation",
        )
    )

    if payload.get("schema_version") != ATTESTATION_SCHEMA_VERSION:
        issues.append("release-controls attestation has an unsupported schema_version")
    if type(payload.get("repository")) is not str or payload.get("repository") != expected_repository:
        issues.append("release-controls attestation does not match the exact repository")
    if type(payload.get("release_sha")) is not str or payload.get("release_sha") != expected_release_sha:
        issues.append("release-controls attestation does not match the exact release SHA")
    if type(payload.get("release_tag")) is not str or payload.get("release_tag") != expected_release_tag:
        issues.append("release-controls attestation does not match the exact release tag")

    verified_at = _parse_utc_timestamp(payload.get("verified_at"), field="verified_at", issues=issues)
    expires_at = _parse_utc_timestamp(payload.get("expires_at"), field="expires_at", issues=issues)
    effective_now = datetime.now(UTC) if now is None else now
    if effective_now.tzinfo is None or effective_now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    effective_now = effective_now.astimezone(UTC)

    if verified_at is not None:
        if verified_at > effective_now:
            issues.append("release-controls attestation verified_at is in the future")
        elif effective_now - verified_at > MAX_ATTESTATION_AGE:
            issues.append("release-controls attestation is stale")
    if verified_at is not None and expires_at is not None:
        if expires_at <= verified_at:
            issues.append("release-controls attestation expires_at must follow verified_at")
        elif expires_at - verified_at > MAX_ATTESTATION_VALIDITY:
            issues.append("release-controls attestation validity exceeds 24 hours")
    if expires_at is not None and expires_at <= effective_now:
        issues.append("release-controls attestation has expired")

    controls = payload.get("controls")
    if not isinstance(controls, dict):
        issues.append("release-controls attestation controls must be a JSON object")
    else:
        required_controls = frozenset(REQUIRED_CONTROLS)
        issues.extend(
            _closed_key_issues(
                controls,
                expected=required_controls,
                context="release-controls attestation controls",
            )
        )
        for control in REQUIRED_CONTROLS:
            if type(controls.get(control)) is not bool or controls.get(control) is not True:
                issues.append(f"release-controls attestation control must be exactly true: {control}")

    return issues


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument(
        "--attestation-env",
        default=ATTESTATION_ENVIRONMENT_VARIABLE,
        help="Environment variable containing the credentialless JSON attestation.",
    )
    args = parser.parse_args(argv)

    environment = os.environ if environ is None else environ
    issues = validate_release_controls_attestation(
        environment.get(args.attestation_env),
        expected_repository=args.repository,
        expected_release_sha=args.release_sha,
        expected_release_tag=args.release_tag,
        now=now,
    )
    if issues:
        print("Repository release controls: FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1
    print("Repository release controls: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
