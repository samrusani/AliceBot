from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "check_protected_paths.py"
)
_SPEC = importlib.util.spec_from_file_location("check_protected_paths", _MODULE_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
guardrails = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = guardrails
_SPEC.loader.exec_module(guardrails)


def test_categorize_files_tracks_overlapping_protected_areas() -> None:
    touched = guardrails.categorize_files(
        [
            "apps/api/src/alicebot_api/contracts.py",
            "apps/api/src/alicebot_api/trusted_fact_promotions.py",
            "README.md",
        ]
    )

    assert sorted(touched) == [
        "continuity APIs",
        "memory schema",
        "promotion logic",
        "trust rules",
    ]
    assert touched["promotion logic"] == [
        "apps/api/src/alicebot_api/trusted_fact_promotions.py"
    ]


def test_validate_upgrade_overview_skips_non_protected_changes() -> None:
    assert guardrails.validate_upgrade_overview("", {}) == []


def test_validate_upgrade_overview_requires_checked_areas_and_notes() -> None:
    touched = {
        "memory schema": ["apps/api/alembic/versions/20260410_9999_example.py"],
        "continuity APIs": ["apps/api/src/alicebot_api/main.py"],
    }

    errors = guardrails.validate_upgrade_overview(
        """
## Upgrade Overview

### Protected Areas

- [x] memory schema

### Compatibility Impact

TBD

### Migration / Rollout

Pending

### Operator Action

None

### Validation

N/A
""",
        touched,
    )

    assert any("continuity APIs" in error for error in errors)
    assert any("Compatibility Impact" in error for error in errors)
    assert any("Rollback" in error for error in errors)


def test_validate_upgrade_overview_accepts_complete_metadata() -> None:
    touched = {
        "evidence pipeline": ["apps/api/src/alicebot_api/continuity_evidence.py"],
        "trust rules": ["apps/api/src/alicebot_api/memory.py"],
    }

    errors = guardrails.validate_upgrade_overview(
        """
## Summary

Short summary.

## Upgrade Overview

### Protected Areas

- [x] evidence pipeline
- [x] trust rules

### Compatibility Impact

Additive internal change only. Existing archived evidence rows stay readable and no API enum changes occur.

### Migration / Rollout

No deploy sequencing beyond the normal application rollout. Existing data remains valid without backfill.

### Operator Action

No manual operator action is required for this change.

### Validation

Ran targeted unit coverage for the guardrail parser and reviewed the protected-path mapping against the touched files.

### Rollback

Revert the change set and redeploy. No irreversible data rewrite occurs in this path.
""",
        touched,
    )

    assert errors == []
