#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE_INDEX_PATH = ROOT_DIR / "artifacts" / "release" / "archive" / "index.json"
ARCHIVE_INDEX_NAME = "index.json"
ARCHIVE_INDEX_LOCK_NAME = "index.lock"
ARCHIVE_INDEX_VERSION = "phase4_rc_archive_index.v1"
SUMMARY_ARTIFACT_VERSION = "phase4_rc_summary.v1"
FinalDecision = Literal["GO", "NO_GO"]


def _resolve_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return ROOT_DIR / candidate


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: payload must be a JSON object.")
    return payload


def _validate_created_at(value: object, *, field_name: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{field_name} must be a string.")
        return
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        errors.append(f"{field_name} must use UTC format YYYY-MM-DDTHH:MM:SSZ.")


def _validate_entry_command_mode(
    *,
    value: object,
    ordered_steps: set[str],
    field_prefix: str,
    errors: list[str],
) -> None:
    if not isinstance(value, str):
        errors.append(f"{field_prefix}.command_mode must be a string.")
        return

    if value == "default":
        return

    if not value.startswith("induced_failure:"):
        errors.append(
            f"{field_prefix}.command_mode must be 'default' or 'induced_failure:<step_id>'."
        )
        return

    induced_step = value.removeprefix("induced_failure:")
    if induced_step not in ordered_steps:
        errors.append(
            f"{field_prefix}.command_mode references unknown induced step {induced_step!r}."
        )


def verify_archive_index(index_path: Path = DEFAULT_ARCHIVE_INDEX_PATH) -> list[str]:
    errors: list[str] = []
    if not index_path.exists():
        return [f"Archive index not found: {index_path}"]

    try:
        index_payload = _load_json_object(index_path)
    except Exception as exc:  # pragma: no cover - defensive surface
        return [f"Failed to parse archive index {index_path}: {exc}"]

    if index_payload.get("artifact_version") != ARCHIVE_INDEX_VERSION:
        errors.append(
            f"archive index artifact_version must be {ARCHIVE_INDEX_VERSION!r}, "
            f"got {index_payload.get('artifact_version')!r}."
        )

    latest_summary_path_value = index_payload.get("latest_summary_path")
    if not isinstance(latest_summary_path_value, str):
        errors.append("archive index latest_summary_path must be a string.")
    else:
        latest_summary_path = _resolve_path(latest_summary_path_value)
        if not latest_summary_path.exists():
            errors.append(
                f"archive index latest_summary_path does not exist: {latest_summary_path_value}"
            )

    archive_dir_value = index_payload.get("archive_dir")
    archive_dir: Path | None = None
    if not isinstance(archive_dir_value, str):
        errors.append("archive index archive_dir must be a string.")
    else:
        archive_dir = _resolve_path(archive_dir_value)
        if not archive_dir.exists():
            errors.append(f"archive index archive_dir does not exist: {archive_dir_value}")
        else:
            expected_index_path = (archive_dir / ARCHIVE_INDEX_NAME).resolve(strict=False)
            if index_path.resolve(strict=False) != expected_index_path:
                errors.append(
                    "archive index path must be archive_dir/index.json for deterministic "
                    "lock and atomic-write contract."
                )
            lock_path = archive_dir / ARCHIVE_INDEX_LOCK_NAME
            if lock_path.exists():
                errors.append(
                    f"archive index lock file should not persist after RC write completion: {lock_path}"
                )

    entries = index_payload.get("entries")
    if not isinstance(entries, list):
        errors.append("archive index entries must be a list.")
        return errors

    seen_archive_paths: set[str] = set()
    previous_created_at: str | None = None
    for idx, entry in enumerate(entries):
        field_prefix = f"entries[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{field_prefix} must be a JSON object.")
            continue

        _validate_created_at(entry.get("created_at"), field_name=f"{field_prefix}.created_at", errors=errors)

        archive_artifact_path_value = entry.get("archive_artifact_path")
        if not isinstance(archive_artifact_path_value, str):
            errors.append(f"{field_prefix}.archive_artifact_path must be a string.")
            continue

        if archive_artifact_path_value in seen_archive_paths:
            errors.append(
                f"{field_prefix}.archive_artifact_path duplicates a prior index entry: "
                f"{archive_artifact_path_value}"
            )
            continue
        seen_archive_paths.add(archive_artifact_path_value)

        archive_artifact_path = _resolve_path(archive_artifact_path_value)
        if archive_dir is not None:
            try:
                archive_artifact_path.relative_to(archive_dir)
            except ValueError:
                errors.append(
                    f"{field_prefix}.archive_artifact_path is outside archive_dir: "
                    f"{archive_artifact_path_value}"
                )

        if not archive_artifact_path.exists():
            errors.append(
                f"{field_prefix}.archive_artifact_path missing file: {archive_artifact_path_value}"
            )
            continue

        try:
            summary_payload = _load_json_object(archive_artifact_path)
        except Exception as exc:  # pragma: no cover - defensive surface
            errors.append(f"{field_prefix} failed to parse archive summary: {exc}")
            continue

        if summary_payload.get("artifact_version") != SUMMARY_ARTIFACT_VERSION:
            errors.append(
                f"{field_prefix} archive summary artifact_version must be "
                f"{SUMMARY_ARTIFACT_VERSION!r}."
            )

        summary_artifact_path = summary_payload.get("artifact_path")
        if summary_artifact_path != archive_artifact_path_value:
            errors.append(
                f"{field_prefix} archive summary artifact_path mismatch: "
                f"expected {archive_artifact_path_value!r}, got {summary_artifact_path!r}."
            )

        final_decision = summary_payload.get("final_decision")
        if final_decision not in {"GO", "NO_GO"}:
            errors.append(f"{field_prefix} archive summary final_decision must be GO or NO_GO.")
            continue
        assert isinstance(final_decision, str)
        typed_final_decision: FinalDecision = final_decision

        entry_final_decision = entry.get("final_decision")
        if entry_final_decision != typed_final_decision:
            errors.append(
                f"{field_prefix}.final_decision mismatch with archive summary: "
                f"{entry_final_decision!r} != {typed_final_decision!r}."
            )

        summary_exit_code = summary_payload.get("summary_exit_code")
        entry_summary_exit_code = entry.get("summary_exit_code")
        if entry_summary_exit_code != summary_exit_code:
            errors.append(
                f"{field_prefix}.summary_exit_code mismatch with archive summary: "
                f"{entry_summary_exit_code!r} != {summary_exit_code!r}."
            )

        failing_steps = summary_payload.get("failing_steps")
        entry_failing_steps = entry.get("failing_steps")
        if entry_failing_steps != failing_steps:
            errors.append(
                f"{field_prefix}.failing_steps mismatch with archive summary: "
                f"{entry_failing_steps!r} != {failing_steps!r}."
            )

        ordered_steps = summary_payload.get("ordered_steps")
        if not isinstance(ordered_steps, list) or not all(isinstance(step, str) for step in ordered_steps):
            errors.append(f"{field_prefix} archive summary ordered_steps must be list[str].")
            ordered_steps_set: set[str] = set()
        else:
            ordered_steps_set = set(ordered_steps)

        _validate_entry_command_mode(
            value=entry.get("command_mode"),
            ordered_steps=ordered_steps_set,
            field_prefix=field_prefix,
            errors=errors,
        )

        if typed_final_decision == "GO":
            if summary_exit_code != 0:
                errors.append(f"{field_prefix} GO summary_exit_code must be 0.")
            if failing_steps != []:
                errors.append(f"{field_prefix} GO failing_steps must be [].")
        else:
            if summary_exit_code != 1:
                errors.append(f"{field_prefix} NO_GO summary_exit_code must be 1.")
            if not isinstance(failing_steps, list) or len(failing_steps) == 0:
                errors.append(f"{field_prefix} NO_GO failing_steps must be non-empty.")

        created_at_value = entry.get("created_at")
        if isinstance(created_at_value, str):
            if previous_created_at is not None and created_at_value < previous_created_at:
                errors.append(
                    f"{field_prefix}.created_at must be non-decreasing for append-only ordering."
                )
            previous_created_at = created_at_value

    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Phase 4 release-candidate archive index schema and ensure each index "
            "entry matches the retained archive summary artifact."
        ),
    )
    parser.add_argument(
        "--index-path",
        default=str(DEFAULT_ARCHIVE_INDEX_PATH),
        help="Path to archive index JSON file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    index_path = Path(args.index_path)

    errors = verify_archive_index(index_path=index_path)
    if errors:
        print("Phase 4 RC archive verification: FAIL")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Phase 4 RC archive verification: PASS")
    print(f"Validated archive index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
