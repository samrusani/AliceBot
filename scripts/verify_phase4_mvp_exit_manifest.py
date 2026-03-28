#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = ROOT_DIR / "artifacts" / "release" / "phase4_mvp_exit_manifest.json"
ARCHIVE_INDEX_VERSION = "phase4_rc_archive_index.v1"
MANIFEST_ARTIFACT_VERSION = "phase4_mvp_exit_manifest.v1"
RC_SUMMARY_ARTIFACT_VERSION = "phase4_rc_summary.v1"
REQUIRED_COMPATIBILITY_COMMANDS: tuple[str, ...] = (
    "python3 scripts/run_phase4_validation_matrix.py",
    "python3 scripts/run_phase3_validation_matrix.py",
    "python3 scripts/run_phase2_validation_matrix.py",
    "python3 scripts/run_mvp_validation_matrix.py",
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


def _sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_summary_step_status_by_id(summary_payload: dict[str, object]) -> dict[str, str]:
    steps = summary_payload.get("steps")
    if not isinstance(steps, list):
        raise ValueError("archive summary steps must be a list.")

    step_status_by_id: dict[str, str] = {}
    for step_payload in steps:
        if not isinstance(step_payload, dict):
            raise ValueError("archive summary steps[] entries must be JSON objects.")
        step_id = step_payload.get("step")
        status = step_payload.get("status")
        if not isinstance(step_id, str) or not isinstance(status, str):
            raise ValueError("archive summary steps[] must include string step and status fields.")
        step_status_by_id[step_id] = status
    return step_status_by_id


def verify_manifest(*, manifest_path: Path = DEFAULT_MANIFEST_PATH) -> list[str]:
    errors: list[str] = []
    if not manifest_path.exists():
        return [f"MVP exit manifest not found: {manifest_path}"]

    try:
        manifest_payload = _load_json_object(manifest_path)
    except Exception as exc:  # pragma: no cover - defensive parse surface
        return [f"Failed to parse manifest {manifest_path}: {exc}"]

    if manifest_payload.get("artifact_version") != MANIFEST_ARTIFACT_VERSION:
        errors.append(
            f"manifest artifact_version must be {MANIFEST_ARTIFACT_VERSION!r}, "
            f"got {manifest_payload.get('artifact_version')!r}."
        )

    expected_manifest_path_value = _render_path(manifest_path)
    if manifest_payload.get("artifact_path") != expected_manifest_path_value:
        errors.append(
            "manifest artifact_path mismatch: "
            f"expected {expected_manifest_path_value!r}, got {manifest_payload.get('artifact_path')!r}."
        )

    if manifest_payload.get("phase") != "phase4":
        errors.append("manifest phase must be 'phase4'.")
    if manifest_payload.get("release_gate") != "mvp":
        errors.append("manifest release_gate must be 'mvp'.")

    decision = manifest_payload.get("decision")
    if not isinstance(decision, dict):
        errors.append("manifest decision must be a JSON object.")
    else:
        if decision.get("final_decision") != "GO":
            errors.append("manifest decision.final_decision must be GO.")
        if decision.get("summary_exit_code") != 0:
            errors.append("manifest decision.summary_exit_code must be 0.")
        if decision.get("failing_steps") != []:
            errors.append("manifest decision.failing_steps must be [].")

    source_references = manifest_payload.get("source_references")
    if not isinstance(source_references, dict):
        errors.append("manifest source_references must be a JSON object.")
        return errors

    index_path_value = source_references.get("archive_index_path")
    archive_entry_index = source_references.get("archive_entry_index")
    archive_artifact_path_value = source_references.get("archive_artifact_path")
    archive_entry_created_at = source_references.get("archive_entry_created_at")
    archive_entry_command_mode = source_references.get("archive_entry_command_mode")

    if not isinstance(index_path_value, str):
        errors.append("manifest source_references.archive_index_path must be a string.")
        return errors
    if not isinstance(archive_entry_index, int) or isinstance(archive_entry_index, bool):
        errors.append("manifest source_references.archive_entry_index must be an integer.")
        return errors
    if not isinstance(archive_artifact_path_value, str):
        errors.append("manifest source_references.archive_artifact_path must be a string.")
        return errors
    if not isinstance(archive_entry_created_at, str):
        errors.append("manifest source_references.archive_entry_created_at must be a string.")
    if not isinstance(archive_entry_command_mode, str):
        errors.append("manifest source_references.archive_entry_command_mode must be a string.")

    index_path = _resolve_path(index_path_value)
    if not index_path.exists():
        errors.append(f"manifest source_references.archive_index_path missing file: {index_path_value}")
        return errors

    archive_artifact_path = _resolve_path(archive_artifact_path_value)
    if not archive_artifact_path.exists():
        errors.append(
            "manifest source_references.archive_artifact_path missing file: "
            f"{archive_artifact_path_value}"
        )
        return errors

    try:
        index_payload = _load_json_object(index_path)
    except Exception as exc:  # pragma: no cover - defensive parse surface
        errors.append(f"failed to parse archive index {index_path}: {exc}")
        return errors

    if index_payload.get("artifact_version") != ARCHIVE_INDEX_VERSION:
        errors.append(
            f"archive index artifact_version must be {ARCHIVE_INDEX_VERSION!r}, "
            f"got {index_payload.get('artifact_version')!r}."
        )

    entries = index_payload.get("entries")
    if not isinstance(entries, list):
        errors.append("archive index entries must be a list.")
        return errors

    if archive_entry_index < 0 or archive_entry_index >= len(entries):
        errors.append(
            "manifest source_references.archive_entry_index is out of range for archive index entries."
        )
        return errors

    matched_entry = entries[archive_entry_index]
    if not isinstance(matched_entry, dict):
        errors.append(
            "manifest source_references.archive_entry_index must reference a JSON object entry."
        )
        return errors

    if matched_entry.get("archive_artifact_path") != archive_artifact_path_value:
        errors.append(
            "manifest source_references.archive_entry_index does not reference "
            "archive_artifact_path in archive index."
        )
        return errors
    if matched_entry.get("final_decision") != "GO":
        errors.append(
            "manifest source archive artifact is not present as a GO entry in archive index: "
            f"{archive_artifact_path_value}"
        )
        return errors

    if archive_entry_created_at is not None and matched_entry.get("created_at") != archive_entry_created_at:
        errors.append(
            "manifest source_references.archive_entry_created_at mismatch with archive index entry."
        )
    if (
        archive_entry_command_mode is not None
        and matched_entry.get("command_mode") != archive_entry_command_mode
    ):
        errors.append(
            "manifest source_references.archive_entry_command_mode mismatch with archive index entry."
        )
    if matched_entry.get("summary_exit_code") != 0:
        errors.append("manifest source archive index entry summary_exit_code must be 0 for GO evidence.")
    if matched_entry.get("failing_steps") != []:
        errors.append("manifest source archive index entry failing_steps must be [].")

    try:
        summary_payload = _load_json_object(archive_artifact_path)
    except Exception as exc:  # pragma: no cover - defensive parse surface
        errors.append(f"failed to parse source archive summary {archive_artifact_path}: {exc}")
        return errors

    if summary_payload.get("artifact_version") != RC_SUMMARY_ARTIFACT_VERSION:
        errors.append(
            f"source archive summary artifact_version must be {RC_SUMMARY_ARTIFACT_VERSION!r}, "
            f"got {summary_payload.get('artifact_version')!r}."
        )
    if summary_payload.get("final_decision") != "GO":
        errors.append("source archive summary final_decision must be GO.")
    if summary_payload.get("summary_exit_code") != 0:
        errors.append("source archive summary summary_exit_code must be 0.")
    if summary_payload.get("failing_steps") != []:
        errors.append("source archive summary failing_steps must be [].")

    ordered_steps = summary_payload.get("ordered_steps")
    if not isinstance(ordered_steps, list) or not all(isinstance(step, str) for step in ordered_steps):
        errors.append("source archive summary ordered_steps must be list[str].")
        ordered_steps = None

    try:
        summary_step_status_by_id = _extract_summary_step_status_by_id(summary_payload)
    except ValueError as exc:
        errors.append(str(exc))
        summary_step_status_by_id = {}

    if ordered_steps is not None:
        expected_ordered_step_statuses = {
            step_id: summary_step_status_by_id.get(step_id, "") for step_id in ordered_steps
        }
        if any(status != "PASS" for status in expected_ordered_step_statuses.values()):
            errors.append("source archive summary GO evidence must have PASS for all ordered steps.")
    else:
        expected_ordered_step_statuses = {}

    manifest_ordered_steps = manifest_payload.get("ordered_steps")
    if manifest_ordered_steps != ordered_steps:
        errors.append("manifest ordered_steps must match source archive summary ordered_steps.")

    manifest_step_status_by_id = manifest_payload.get("step_status_by_id")
    if manifest_step_status_by_id != expected_ordered_step_statuses:
        errors.append("manifest step_status_by_id must match ordered source archive step statuses.")

    compatibility_commands = manifest_payload.get("compatibility_validation_commands")
    if compatibility_commands != list(REQUIRED_COMPATIBILITY_COMMANDS):
        errors.append(
            "manifest compatibility_validation_commands must match required compatibility chain."
        )

    integrity_payload = manifest_payload.get("integrity")
    if not isinstance(integrity_payload, dict):
        errors.append("manifest integrity must be a JSON object.")
        return errors

    expected_archive_hash = _sha256_for_file(archive_artifact_path)
    if integrity_payload.get("archive_artifact_sha256") != expected_archive_hash:
        errors.append(
            "manifest integrity.archive_artifact_sha256 mismatch with source archive artifact."
        )

    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify Phase 4 MVP exit manifest schema, required fields, and referenced "
            "release-candidate GO evidence integrity."
        ),
    )
    parser.add_argument(
        "--manifest-path",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to MVP exit manifest JSON artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest_path = Path(args.manifest_path)

    errors = verify_manifest(manifest_path=manifest_path)
    if errors:
        print("Phase 4 MVP exit manifest verification: FAIL")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Phase 4 MVP exit manifest verification: PASS")
    print(f"Validated manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
