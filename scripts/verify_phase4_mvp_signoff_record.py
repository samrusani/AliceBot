#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.run_phase4_mvp_qualification as qualification


ROOT_DIR = qualification.ROOT_DIR
DEFAULT_SIGNOFF_PATH = qualification.DEFAULT_SIGNOFF_PATH
SIGNOFF_ARTIFACT_VERSION = qualification.SIGNOFF_ARTIFACT_VERSION
STEP_IDS = qualification.STEP_IDS
STEP_STATUS_VALUES = {"PASS", "FAIL", "NOT_RUN"}

REQUIRED_REFERENCE_KEYS: tuple[str, ...] = (
    "release_candidate_summary_path",
    "release_candidate_archive_index_path",
    "mvp_exit_manifest_path",
)


def _resolve_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return ROOT_DIR / candidate


def _render_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: payload must be a JSON object.")
    return payload


def _validate_generated_at(value: object, *, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append("sign-off generated_at must be a UTC timestamp string.")
        return
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        errors.append("sign-off generated_at must use UTC format YYYY-MM-DDTHH:MM:SSZ.")


def verify_signoff_record(
    *,
    signoff_path: Path = DEFAULT_SIGNOFF_PATH,
    expected_step_ids: tuple[str, ...] = STEP_IDS,
    expected_required_references: dict[str, str] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not signoff_path.exists():
        return [f"MVP qualification sign-off record not found: {signoff_path}"]

    try:
        payload = _load_json_object(signoff_path)
    except Exception as exc:  # pragma: no cover - defensive parse surface
        return [f"Failed to parse sign-off record {signoff_path}: {exc}"]

    if payload.get("artifact_version") != SIGNOFF_ARTIFACT_VERSION:
        errors.append(
            f"sign-off artifact_version must be {SIGNOFF_ARTIFACT_VERSION!r}, "
            f"got {payload.get('artifact_version')!r}."
        )

    expected_artifact_path = _render_path(signoff_path)
    if payload.get("artifact_path") != expected_artifact_path:
        errors.append(
            "sign-off artifact_path mismatch: "
            f"expected {expected_artifact_path!r}, got {payload.get('artifact_path')!r}."
        )

    if payload.get("phase") != "phase4":
        errors.append("sign-off phase must be 'phase4'.")
    if payload.get("release_gate") != "mvp":
        errors.append("sign-off release_gate must be 'mvp'.")

    _validate_generated_at(payload.get("generated_at"), errors=errors)

    ordered_steps = payload.get("ordered_steps")
    if ordered_steps != list(expected_step_ids):
        errors.append("sign-off ordered_steps must match canonical qualification chain.")

    total_steps = payload.get("total_steps")
    if total_steps != len(expected_step_ids):
        errors.append(f"sign-off total_steps must be {len(expected_step_ids)}.")

    required_references = payload.get("required_references")
    if not isinstance(required_references, dict):
        errors.append("sign-off required_references must be a JSON object.")
        return errors

    expected_references = expected_required_references or qualification.default_required_references()
    for key in REQUIRED_REFERENCE_KEYS:
        value = required_references.get(key)
        if not isinstance(value, str):
            errors.append(f"sign-off required_references.{key} must be a string.")
            continue
        expected_value = expected_references.get(key)
        if expected_value is not None and value != expected_value:
            errors.append(
                f"sign-off required_references.{key} must be {expected_value!r}, got {value!r}."
            )

    steps_payload = payload.get("steps")
    if not isinstance(steps_payload, list):
        errors.append("sign-off steps must be a list.")
        return errors
    if len(steps_payload) != len(expected_step_ids):
        errors.append("sign-off steps length must match canonical qualification chain.")
        return errors

    failing_steps: list[str] = []
    not_run_steps: list[str] = []
    executed_steps = 0
    all_pass = True
    non_pass_step_ids: set[str] = set()
    step_status_by_id: dict[str, str] = {}

    for idx, step_payload in enumerate(steps_payload):
        field_prefix = f"steps[{idx}]"
        if not isinstance(step_payload, dict):
            errors.append(f"{field_prefix} must be a JSON object.")
            all_pass = False
            continue

        expected_step_id = expected_step_ids[idx]
        step_id = step_payload.get("step")
        if step_id != expected_step_id:
            errors.append(
                f"{field_prefix}.step must be {expected_step_id!r}, got {step_id!r}."
            )
            all_pass = False
            continue
        assert isinstance(step_id, str)

        status = step_payload.get("status")
        if status not in STEP_STATUS_VALUES:
            errors.append(f"{field_prefix}.status must be PASS, FAIL, or NOT_RUN.")
            all_pass = False
            continue
        assert isinstance(status, str)
        step_status_by_id[step_id] = status

        command = step_payload.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
            errors.append(f"{field_prefix}.command must be non-empty list[str].")

        required_artifacts = step_payload.get("required_artifacts")
        if not isinstance(required_artifacts, list) or not all(
            isinstance(path_value, str) for path_value in required_artifacts
        ):
            errors.append(f"{field_prefix}.required_artifacts must be list[str].")
            required_artifacts = []

        missing_artifacts = step_payload.get("missing_artifacts")
        if not isinstance(missing_artifacts, list) or not all(
            isinstance(path_value, str) for path_value in missing_artifacts
        ):
            errors.append(f"{field_prefix}.missing_artifacts must be list[str].")
            missing_artifacts = []

        exit_code = step_payload.get("exit_code")
        if status == "PASS":
            executed_steps += 1
            if exit_code != 0:
                errors.append(f"{field_prefix}.exit_code must be 0 for PASS status.")
            if missing_artifacts:
                errors.append(f"{field_prefix}.missing_artifacts must be empty for PASS status.")
            for artifact_path_value in required_artifacts:
                if not _resolve_path(artifact_path_value).exists():
                    errors.append(
                        f"{field_prefix}.required_artifacts missing file: {artifact_path_value}"
                    )
        elif status == "FAIL":
            executed_steps += 1
            all_pass = False
            failing_steps.append(step_id)
            non_pass_step_ids.add(step_id)
            if not isinstance(exit_code, int) or isinstance(exit_code, bool):
                errors.append(f"{field_prefix}.exit_code must be an integer for FAIL status.")
        else:
            all_pass = False
            not_run_steps.append(step_id)
            non_pass_step_ids.add(step_id)
            if exit_code is not None:
                errors.append(f"{field_prefix}.exit_code must be null for NOT_RUN status.")

        duration_seconds = step_payload.get("duration_seconds")
        if not isinstance(duration_seconds, (float, int)):
            errors.append(f"{field_prefix}.duration_seconds must be numeric.")

    if payload.get("executed_steps") != executed_steps:
        errors.append("sign-off executed_steps must match count of non-NOT_RUN steps.")

    if payload.get("failing_steps") != failing_steps:
        errors.append("sign-off failing_steps must match FAIL steps from sign-off steps[].")
    if payload.get("not_run_steps") != not_run_steps:
        errors.append("sign-off not_run_steps must match NOT_RUN steps from sign-off steps[].")

    final_decision = payload.get("final_decision")
    summary_exit_code = payload.get("summary_exit_code")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list):
        errors.append("sign-off blockers must be a list.")
        blockers = []

    blocker_step_ids: set[str] = set()
    for idx, blocker in enumerate(blockers):
        field_prefix = f"blockers[{idx}]"
        if not isinstance(blocker, dict):
            errors.append(f"{field_prefix} must be a JSON object.")
            continue
        step_id = blocker.get("step")
        reason = blocker.get("reason")
        detail = blocker.get("detail")
        if not isinstance(step_id, str):
            errors.append(f"{field_prefix}.step must be a string.")
            continue
        blocker_step_ids.add(step_id)
        if not isinstance(reason, str):
            errors.append(f"{field_prefix}.reason must be a string.")
        if not isinstance(detail, str):
            errors.append(f"{field_prefix}.detail must be a string.")

    if all_pass:
        if final_decision != "GO":
            errors.append("sign-off final_decision must be GO when all steps PASS.")
        if summary_exit_code != 0:
            errors.append("sign-off summary_exit_code must be 0 when all steps PASS.")
        if blockers:
            errors.append("sign-off blockers must be empty when final_decision is GO.")
    else:
        if final_decision != "NO_GO":
            errors.append("sign-off final_decision must be NO_GO when any step is non-PASS.")
        if summary_exit_code != 1:
            errors.append("sign-off summary_exit_code must be 1 when any step is non-PASS.")
        if not blockers:
            errors.append("sign-off blockers must be non-empty when final_decision is NO_GO.")
        if not non_pass_step_ids.issubset(blocker_step_ids):
            errors.append(
                "sign-off blockers must include every non-PASS step as a blocker entry."
            )

    reference_path_by_key = {
        "release_candidate_summary_path": required_references.get("release_candidate_summary_path"),
        "release_candidate_archive_index_path": required_references.get(
            "release_candidate_archive_index_path"
        ),
        "mvp_exit_manifest_path": required_references.get("mvp_exit_manifest_path"),
    }
    for key, path_value in reference_path_by_key.items():
        if not isinstance(path_value, str):
            continue
        should_exist = False
        if key == "release_candidate_summary_path":
            should_exist = step_status_by_id.get(qualification.STEP_RELEASE_CANDIDATE_REHEARSAL) == "PASS"
        elif key == "release_candidate_archive_index_path":
            should_exist = (
                step_status_by_id.get(qualification.STEP_RELEASE_CANDIDATE_REHEARSAL) == "PASS"
                or step_status_by_id.get(qualification.STEP_RELEASE_CANDIDATE_ARCHIVE_VERIFY) == "PASS"
            )
        elif key == "mvp_exit_manifest_path":
            should_exist = (
                step_status_by_id.get(qualification.STEP_MVP_EXIT_MANIFEST_GENERATE) == "PASS"
                or step_status_by_id.get(qualification.STEP_MVP_EXIT_MANIFEST_VERIFY) == "PASS"
            )

        if should_exist and not _resolve_path(path_value).exists():
            errors.append(f"sign-off required_references.{key} missing file: {path_value}")

    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Phase 4 MVP qualification sign-off record schema, references, and "
            "GO/NO_GO consistency."
        ),
    )
    parser.add_argument(
        "--signoff-path",
        default=str(DEFAULT_SIGNOFF_PATH),
        help="Path to MVP qualification sign-off JSON artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    signoff_path = Path(args.signoff_path)

    errors = verify_signoff_record(signoff_path=signoff_path)
    if errors:
        print("Phase 4 MVP sign-off record verification: FAIL")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Phase 4 MVP sign-off record verification: PASS")
    print(f"Validated sign-off record: {signoff_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
