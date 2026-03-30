#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import UUID

from alicebot_api.config import get_settings
from alicebot_api.db import user_connection
from alicebot_api.memory import get_memory_trust_dashboard_summary
from alicebot_api.store import ContinuityStore


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_PATH = ROOT_DIR / "artifacts" / "release" / "phase6_quality_evidence.json"
DEFAULT_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
ARTIFACT_VERSION = "phase6_quality_evidence.v1"


def _render_artifact_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _resolve_user_id(explicit_user_id: str | None) -> UUID:
    raw_value = explicit_user_id or os.getenv("PHASE6_QUALITY_USER_ID") or str(DEFAULT_USER_ID)
    try:
        return UUID(raw_value)
    except ValueError as exc:
        raise ValueError(f"user_id must be a valid UUID: {raw_value}") from exc


def build_quality_evidence_payload(*, artifact_path: Path, user_id: UUID) -> dict[str, object]:
    settings = get_settings()
    with user_connection(settings.database_url, user_id) as conn:
        dashboard = get_memory_trust_dashboard_summary(
            ContinuityStore(conn),
            user_id=user_id,
        )["dashboard"]

    return {
        "artifact_version": ARTIFACT_VERSION,
        "artifact_path": _render_artifact_path(artifact_path),
        "user_id": str(user_id),
        "dashboard": dashboard,
    }


def _atomic_write_json(*, path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.tmp.{os.getpid()}"
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic Phase 6 quality evidence from canonical memory trust dashboard "
            "semantics for release/readiness reporting."
        ),
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help=(
            "User UUID for quality evidence scope. Defaults to PHASE6_QUALITY_USER_ID env var, "
            "or deterministic fallback UUID when unset."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_ARTIFACT_PATH),
        help="Artifact output path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        user_id = _resolve_user_id(args.user_id)
    except ValueError as exc:
        print(f"Phase 6 quality evidence failed: {exc}")
        return 2

    artifact_path = Path(args.output).expanduser()
    if not artifact_path.is_absolute():
        artifact_path = (ROOT_DIR / artifact_path).resolve()

    payload = build_quality_evidence_payload(
        artifact_path=artifact_path,
        user_id=user_id,
    )
    _atomic_write_json(path=artifact_path, payload=payload)

    print(f"Phase 6 quality evidence artifact: {payload['artifact_path']}")
    dashboard = payload["dashboard"]
    assert isinstance(dashboard, dict)
    quality_gate = dashboard.get("quality_gate", {})
    recommended_review = dashboard.get("recommended_review", {})
    print(f"quality_gate_status: {quality_gate.get('status')}")
    print(
        "recommended_review: "
        f"mode={recommended_review.get('priority_mode')} "
        f"action={recommended_review.get('action')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
