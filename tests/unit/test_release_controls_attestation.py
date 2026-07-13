from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

import pytest

import scripts.check_release_controls_attestation as release_controls


NOW = datetime(2026, 7, 13, 12, 0, 0, tzinfo=UTC)
REPOSITORY = "900Labs/AliceBot"
RELEASE_SHA = "a" * 40
RELEASE_TAG = "v0.10.0"
ROOT = Path(__file__).resolve().parents[2]


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_payload() -> dict[str, Any]:
    return {
        "schema_version": release_controls.ATTESTATION_SCHEMA_VERSION,
        "repository": REPOSITORY,
        "release_sha": RELEASE_SHA,
        "release_tag": RELEASE_TAG,
        "verified_at": _timestamp(NOW - timedelta(hours=1)),
        "expires_at": _timestamp(NOW + timedelta(hours=1)),
        "controls": {control: True for control in release_controls.REQUIRED_CONTROLS},
    }


def _validate(payload: dict[str, Any]) -> list[str]:
    return release_controls.validate_release_controls_attestation(
        json.dumps(payload),
        expected_repository=REPOSITORY,
        expected_release_sha=RELEASE_SHA,
        expected_release_tag=RELEASE_TAG,
        now=NOW,
    )


def test_release_controls_attestation_accepts_exact_fresh_closed_claim() -> None:
    assert _validate(_valid_payload()) == []


def test_releasing_example_matches_the_executable_attestation_contract() -> None:
    releasing = (ROOT / "RELEASING.md").read_text(encoding="utf-8")
    example = json.loads(releasing.split("```json", 1)[1].split("```", 1)[0])

    assert set(example) == {
        "schema_version",
        "repository",
        "release_sha",
        "release_tag",
        "verified_at",
        "expires_at",
        "controls",
    }
    assert example["schema_version"] == release_controls.ATTESTATION_SCHEMA_VERSION
    assert tuple(example["controls"]) == release_controls.REQUIRED_CONTROLS
    assert all(value is True for value in example["controls"].values())


def test_release_controls_cli_reads_only_named_environment_variable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_attestation = json.dumps(_valid_payload())

    result = release_controls.main(
        [
            "--repository",
            REPOSITORY,
            "--release-sha",
            RELEASE_SHA,
            "--release-tag",
            RELEASE_TAG,
        ],
        environ={release_controls.ATTESTATION_ENVIRONMENT_VARIABLE: raw_attestation},
        now=NOW,
    )

    assert result == 0
    assert capsys.readouterr().out == "Repository release controls: PASS\n"


@pytest.mark.parametrize(
    "case",
    (
        "missing",
        "malformed",
        "stale",
        "wrong_repository",
        "wrong_sha",
        "wrong_tag",
        "false_control",
    ),
)
def test_release_controls_cli_fail_closed_runtime_matrix(
    case: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = _valid_payload()
    raw_attestation: str | None = json.dumps(payload)
    if case == "missing":
        raw_attestation = None
    elif case == "malformed":
        raw_attestation = "v1"
    elif case == "stale":
        payload["verified_at"] = _timestamp(NOW - timedelta(hours=25))
        payload["expires_at"] = _timestamp(NOW - timedelta(hours=2))
        raw_attestation = json.dumps(payload)
    elif case == "wrong_repository":
        payload["repository"] = "other/repository"
        raw_attestation = json.dumps(payload)
    elif case == "wrong_sha":
        payload["release_sha"] = "b" * 40
        raw_attestation = json.dumps(payload)
    elif case == "wrong_tag":
        payload["release_tag"] = "v0.10.1"
        raw_attestation = json.dumps(payload)
    elif case == "false_control":
        payload["controls"][release_controls.REQUIRED_CONTROLS[0]] = False
        raw_attestation = json.dumps(payload)

    environment = (
        {} if raw_attestation is None else {release_controls.ATTESTATION_ENVIRONMENT_VARIABLE: raw_attestation}
    )
    result = release_controls.main(
        [
            "--repository",
            REPOSITORY,
            "--release-sha",
            RELEASE_SHA,
            "--release-tag",
            RELEASE_TAG,
        ],
        environ=environment,
        now=NOW,
    )

    assert result == 1
    assert capsys.readouterr().out.startswith("Repository release controls: FAIL\n")


@pytest.mark.parametrize(
    "raw_attestation",
    (
        None,
        "",
        "v1",
        "{",
        "[]",
        '{"schema_version": NaN}',
        '{"schema_version": Infinity}',
        '{"repository":"900Labs/AliceBot","repository":"other/repo"}',
        "[" * 1_001 + "0" + "]" * 1_001,
    ),
)
def test_release_controls_attestation_rejects_missing_or_malformed_json(
    raw_attestation: str | None,
) -> None:
    issues = release_controls.validate_release_controls_attestation(
        raw_attestation,
        expected_repository=REPOSITORY,
        expected_release_sha=RELEASE_SHA,
        expected_release_tag=RELEASE_TAG,
        now=NOW,
    )

    assert issues


@pytest.mark.parametrize(
    ("field", "value", "expected_issue"),
    (
        ("schema_version", "alice_release_controls_attestation_v0", "schema_version"),
        ("repository", "other/repository", "exact repository"),
        ("release_sha", "b" * 40, "exact release SHA"),
        ("release_tag", "v0.10.1", "exact release tag"),
    ),
)
def test_release_controls_attestation_rejects_wrong_identity(
    field: str,
    value: str,
    expected_issue: str,
) -> None:
    payload = _valid_payload()
    payload[field] = value

    issues = _validate(payload)

    assert any(expected_issue in issue for issue in issues)


@pytest.mark.parametrize(
    ("verified_at", "expires_at", "expected_issue"),
    (
        (
            NOW - timedelta(hours=25),
            NOW - timedelta(hours=2),
            "stale",
        ),
        (
            NOW + timedelta(seconds=1),
            NOW + timedelta(hours=1),
            "future",
        ),
        (
            NOW - timedelta(hours=1),
            NOW,
            "expired",
        ),
        (
            NOW - timedelta(hours=1),
            NOW + timedelta(hours=24),
            "validity exceeds 24 hours",
        ),
        (
            NOW - timedelta(hours=1),
            NOW - timedelta(hours=2),
            "must follow verified_at",
        ),
    ),
)
def test_release_controls_attestation_rejects_invalid_freshness_window(
    verified_at: datetime,
    expires_at: datetime,
    expected_issue: str,
) -> None:
    payload = _valid_payload()
    payload["verified_at"] = _timestamp(verified_at)
    payload["expires_at"] = _timestamp(expires_at)

    issues = _validate(payload)

    assert any(expected_issue in issue for issue in issues)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("verified_at", "2026-07-13T12:00:00+00:00"),
        ("verified_at", "2026-02-30T12:00:00Z"),
        ("verified_at", True),
        ("expires_at", "2026-07-13"),
        ("expires_at", None),
    ),
)
def test_release_controls_attestation_rejects_noncanonical_timestamps(
    field: str,
    value: object,
) -> None:
    payload = _valid_payload()
    payload[field] = value

    issues = _validate(payload)

    assert any(field in issue for issue in issues)


@pytest.mark.parametrize("control", release_controls.REQUIRED_CONTROLS)
def test_release_controls_attestation_rejects_each_missing_control(control: str) -> None:
    payload = _valid_payload()
    del payload["controls"][control]

    issues = _validate(payload)

    assert any(control in issue for issue in issues)


@pytest.mark.parametrize("control", release_controls.REQUIRED_CONTROLS)
def test_release_controls_attestation_rejects_each_false_control(control: str) -> None:
    payload = _valid_payload()
    payload["controls"][control] = False

    issues = _validate(payload)

    assert any(control in issue for issue in issues)


@pytest.mark.parametrize("invalid_value", (0, 1, 1.0, "true", None, [], {}))
def test_release_controls_attestation_rejects_non_boolean_true_control(
    invalid_value: object,
) -> None:
    payload = _valid_payload()
    payload["controls"][release_controls.REQUIRED_CONTROLS[0]] = invalid_value

    issues = _validate(payload)

    assert any("must be exactly true" in issue for issue in issues)


def test_release_controls_attestation_rejects_unknown_top_level_and_control_claims() -> None:
    payload = _valid_payload()
    unknown_top_level = "unexpected-secret-like-key-must-not-be-printed"
    unknown_control = "semantic_attestation_is_a_substitute"
    payload[unknown_top_level] = True
    payload["controls"][unknown_control] = True

    issues = _validate(payload)

    assert sum("contains 1 unknown field(s)" in issue for issue in issues) == 2
    assert unknown_top_level not in "\n".join(issues)
    assert unknown_control not in "\n".join(issues)


def test_release_controls_cli_fails_closed_without_echoing_attestation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = _valid_payload()
    unknown_key = "credential-key-must-not-be-printed"
    payload[unknown_key] = "credential-value-must-not-be-printed"
    raw_attestation = json.dumps(payload)

    result = release_controls.main(
        [
            "--repository",
            REPOSITORY,
            "--release-sha",
            RELEASE_SHA,
            "--release-tag",
            RELEASE_TAG,
        ],
        environ={release_controls.ATTESTATION_ENVIRONMENT_VARIABLE: raw_attestation},
        now=NOW,
    )
    output = capsys.readouterr().out

    assert result == 1
    assert "Repository release controls: FAIL" in output
    assert unknown_key not in output
    assert "credential-value-must-not-be-printed" not in output
