#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import time


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE_INDEX_PATH = ROOT_DIR / "artifacts" / "release" / "archive" / "index.json"
DEFAULT_MANIFEST_PATH = ROOT_DIR / "artifacts" / "release" / "phase4_mvp_exit_manifest.json"

MANIFEST_ARTIFACT_VERSION = "phase4_mvp_exit_manifest.v1"
ARCHIVE_INDEX_VERSION = "phase4_rc_archive_index.v1"
RC_SUMMARY_ARTIFACT_VERSION = "phase4_rc_summary.v1"
REQUIRED_COMPATIBILITY_COMMANDS: tuple[str, ...] = (
    "python3 scripts/run_phase4_validation_matrix.py",
    "python3 scripts/run_phase3_validation_matrix.py",
    "python3 scripts/run_phase2_validation_matrix.py",
    "python3 scripts/run_mvp_validation_matrix.py",
)
UTC_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


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


def _render_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _atomic_write_json(*, path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp.{os.getpid()}.{time.monotonic_ns()}"
    temp_path.write_text(_render_json(payload), encoding="utf-8")
    try:
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _load_json_object(path: Path, *, label: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _validate_utc_timestamp(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string in {UTC_TIMESTAMP_FORMAT}.")
    try:
        datetime.strptime(value, UTC_TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use {UTC_TIMESTAMP_FORMAT}.") from exc
    return value


def _sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_archive_index(index_path: Path) -> dict[str, object]:
    if not index_path.exists():
        raise ValueError(f"Phase 4 RC archive index not found: {index_path}")
    payload = _load_json_object(index_path, label="archive index")
    if payload.get("artifact_version") != ARCHIVE_INDEX_VERSION:
        raise ValueError(
            "archive index artifact_version must be "
            f"{ARCHIVE_INDEX_VERSION!r}, got {payload.get('artifact_version')!r}."
        )
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("archive index entries must be a list.")
    return payload


def _find_latest_go_entry(index_payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    entries = index_payload["entries"]
    assert isinstance(entries, list)

    for entry_index in range(len(entries) - 1, -1, -1):
        entry = entries[entry_index]
        if isinstance(entry, dict) and entry.get("final_decision") == "GO":
            return entry_index, entry

    raise ValueError("archive index does not contain a GO rehearsal entry.")


def _extract_go_summary_contract(summary_payload: dict[str, object]) -> tuple[list[str], dict[str, str]]:
    if summary_payload.get("artifact_version") != RC_SUMMARY_ARTIFACT_VERSION:
        raise ValueError(
            "archive summary artifact_version must be "
            f"{RC_SUMMARY_ARTIFACT_VERSION!r}, got {summary_payload.get('artifact_version')!r}."
        )
    if summary_payload.get("final_decision") != "GO":
        raise ValueError("archive summary final_decision must be GO.")
    if summary_payload.get("summary_exit_code") != 0:
        raise ValueError("archive summary summary_exit_code must be 0 for GO evidence.")
    if summary_payload.get("failing_steps") != []:
        raise ValueError("archive summary failing_steps must be [] for GO evidence.")

    ordered_steps = summary_payload.get("ordered_steps")
    if not isinstance(ordered_steps, list) or not all(isinstance(step, str) for step in ordered_steps):
        raise ValueError("archive summary ordered_steps must be list[str].")

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

    missing_steps = [step_id for step_id in ordered_steps if step_id not in step_status_by_id]
    if missing_steps:
        raise ValueError(
            "archive summary ordered_steps references missing step payloads: "
            + ", ".join(missing_steps)
        )

    non_pass_steps = [step_id for step_id in ordered_steps if step_status_by_id.get(step_id) != "PASS"]
    if non_pass_steps:
        raise ValueError(
            "archive summary GO evidence must have PASS for all ordered steps. "
            f"Non-PASS steps: {', '.join(non_pass_steps)}"
        )

    ordered_step_statuses = {step_id: step_status_by_id[step_id] for step_id in ordered_steps}
    return ordered_steps, ordered_step_statuses


def generate_manifest(
    *,
    index_path: Path = DEFAULT_ARCHIVE_INDEX_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, object]:
    index_payload = _load_archive_index(index_path)
    go_entry_index, go_entry = _find_latest_go_entry(index_payload)

    archive_artifact_path_value = go_entry.get("archive_artifact_path")
    if not isinstance(archive_artifact_path_value, str):
        raise ValueError("latest GO archive entry archive_artifact_path must be a string.")

    archive_artifact_path = _resolve_path(archive_artifact_path_value)
    if not archive_artifact_path.exists():
        raise ValueError(f"latest GO archive artifact is missing: {archive_artifact_path_value}")

    go_entry_created_at = _validate_utc_timestamp(
        go_entry.get("created_at"),
        field_name="latest GO archive entry created_at",
    )

    go_entry_command_mode = go_entry.get("command_mode")
    if not isinstance(go_entry_command_mode, str):
        raise ValueError("latest GO archive entry command_mode must be a string.")

    archive_summary_payload = _load_json_object(archive_artifact_path, label="archive summary")
    ordered_steps, step_status_by_id = _extract_go_summary_contract(archive_summary_payload)

    if go_entry.get("summary_exit_code") != 0:
        raise ValueError("latest GO archive entry summary_exit_code must be 0.")
    if go_entry.get("failing_steps") != []:
        raise ValueError("latest GO archive entry failing_steps must be [].")

    manifest = {
        "artifact_version": MANIFEST_ARTIFACT_VERSION,
        "artifact_path": _render_path(manifest_path),
        "phase": "phase4",
        "release_gate": "mvp",
        "decision": {
            "final_decision": "GO",
            "summary_exit_code": 0,
            "failing_steps": [],
        },
        "source_references": {
            "archive_index_path": _render_path(index_path),
            "archive_entry_index": go_entry_index,
            "archive_entry_created_at": go_entry_created_at,
            "archive_artifact_path": archive_artifact_path_value,
            "archive_entry_command_mode": go_entry_command_mode,
        },
        "ordered_steps": ordered_steps,
        "step_status_by_id": step_status_by_id,
        "compatibility_validation_commands": list(REQUIRED_COMPATIBILITY_COMMANDS),
        "integrity": {
            "archive_artifact_sha256": _sha256_for_file(archive_artifact_path),
        },
    }

    _atomic_write_json(path=manifest_path, payload=manifest)
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic Phase 4 MVP exit manifest from the latest GO release-candidate "
            "archive evidence entry."
        ),
    )
    parser.add_argument(
        "--index-path",
        default=str(DEFAULT_ARCHIVE_INDEX_PATH),
        help="Path to Phase 4 RC archive index JSON artifact.",
    )
    parser.add_argument(
        "--manifest-path",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Output path for generated MVP exit manifest.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    index_path = Path(args.index_path)
    manifest_path = Path(args.manifest_path)

    try:
        manifest = generate_manifest(index_path=index_path, manifest_path=manifest_path)
    except Exception as exc:
        print("Phase 4 MVP exit manifest generation: FAIL")
        print(f" - {exc}")
        return 1

    print("Phase 4 MVP exit manifest generation: PASS")
    print(f"Manifest artifact: {manifest['artifact_path']}")
    source_refs = manifest["source_references"]
    assert isinstance(source_refs, dict)
    print(f"Source archive artifact: {source_refs['archive_artifact_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
