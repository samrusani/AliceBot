#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class ControlDocTruthRule:
    relative_path: str
    required_markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VersionAlignedDocRule:
    relative_path: str
    pattern_templates: tuple[str, ...]


CONTROL_DOC_TRUTH_RULES: tuple[ControlDocTruthRule, ...] = (
    ControlDocTruthRule(
        relative_path="README.md",
        required_markers=(
            "**The continuity layer for AI agents.**",
            "make doctor",
            "ALICE_MCP_LEGACY_TOOLS=1",
            "## Status",
        ),
    ),
    ControlDocTruthRule(
        relative_path="ROADMAP.md",
        required_markers=(
            "## Baseline (Not Roadmap Work)",
            "## Release Candidate",
            "## Next",
            "## Explicit Non-Goals For Now",
        ),
    ),
    ControlDocTruthRule(
        relative_path="RULES.md",
        required_markers=(
            "## No Fake Intelligence",
            "The vNext store is the canonical memory system.",
            "Continuity semantics must not fork by provider.",
        ),
    ),
    ControlDocTruthRule(
        relative_path="CURRENT_STATE.md",
        required_markers=(
            "## Snapshot",
            "## Release Boundary",
            "## Product Boundaries",
        ),
    ),
    ControlDocTruthRule(
        relative_path=".ai/handoff/CURRENT_STATE.md",
        required_markers=(
            "## Snapshot",
            "## Release Boundary",
            "## Product Boundaries",
        ),
    ),
    ControlDocTruthRule(
        relative_path="PRODUCT_BRIEF.md",
        required_markers=(
            "Alice is the continuity layer for AI agents",
            "## Non-Goals (Now)",
        ),
    ),
    ControlDocTruthRule(
        relative_path="docs/archive/planning/2026-04-08-context-compaction/README.md",
        required_markers=("This folder preserves superseded planning and control material removed from the live docs during Context Compaction 01.",),
    ),
    ControlDocTruthRule(
        relative_path="docs/archive/process/README.md",
        required_markers=("historical build-process artifacts",),
    ),
)

VERSION_ALIGNED_DOC_RULES: tuple[VersionAlignedDocRule, ...] = (
    VersionAlignedDocRule(
        relative_path="CURRENT_STATE.md",
        pattern_templates=(
            r"`v{version}`[^\n]*\bcandidate\b",
            r"^## What `v{version}` (?:Targets|Changes|Adds)$",
        ),
    ),
    VersionAlignedDocRule(
        relative_path=".ai/handoff/CURRENT_STATE.md",
        pattern_templates=(
            r"`v{version}`[^\n]*\bcandidate\b",
            r"^## What `v{version}` (?:Targets|Changes|Adds)$",
        ),
    ),
    VersionAlignedDocRule(
        relative_path="PRODUCT_BRIEF.md",
        pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
    ),
    VersionAlignedDocRule(
        relative_path="ROADMAP.md",
        pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
    ),
    VersionAlignedDocRule(
        relative_path="ARCHITECTURE.md",
        pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
    ),
)

DISALLOWED_MARKERS: tuple[str, ...] = (
    "through Phase 3 Sprint 9",
    "Active Sprint focus is Phase 4 Sprint 14",
    "Gate ownership is canonicalized to Phase 4 runner scripts",
    "Gate ownership is canonicalized to Phase 4 runner script names",
    "Legacy Compatibility Marker",
    "Legacy Compatibility Markers",
    "Phase 9 Sprint Sequence",
    "No active build sprint is open.",
    "Phase 10 planning docs are not defined yet.",
    "Keep this file as an idle-state pointer, not as a fake active sprint.",
    "CTO summary",
    "control tower",
    "design partner",
    "second brain",
    "HF-001",
)


def run_control_doc_truth_check(
    *,
    root_dir: Path = ROOT_DIR,
    rules: tuple[ControlDocTruthRule, ...] = CONTROL_DOC_TRUTH_RULES,
    disallowed_markers: tuple[str, ...] = DISALLOWED_MARKERS,
) -> list[str]:
    issues: list[str] = []
    with (root_dir / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    project = pyproject.get("project")
    version = str(project.get("version", "")) if isinstance(project, dict) else ""
    if not version:
        issues.append("pyproject.toml: missing project.version")

    for rule in rules:
        doc_path = root_dir / rule.relative_path
        if not doc_path.exists():
            issues.append(f"{rule.relative_path}: missing file")
            continue

        text = doc_path.read_text(encoding="utf-8")
        for marker in rule.required_markers:
            if marker not in text:
                issues.append(f"{rule.relative_path}: missing required marker '{marker}'")

        lowered_text = text.casefold()
        for marker in disallowed_markers:
            if marker.casefold() in lowered_text:
                issues.append(f"{rule.relative_path}: contains disallowed marker '{marker}'")

    for version_rule in VERSION_ALIGNED_DOC_RULES:
        doc_path = root_dir / version_rule.relative_path
        if not doc_path.exists():
            continue  # The static rule already reports required-file absence.
        text = doc_path.read_text(encoding="utf-8")
        for pattern_template in version_rule.pattern_templates:
            pattern = pattern_template.format(version=re.escape(version))
            if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is None:
                issues.append(
                    f"{version_rule.relative_path}: missing current-version candidate marker matching '{pattern_template.format(version=version)}'"
                )

    return issues


def main() -> int:
    issues = run_control_doc_truth_check()
    if issues:
        print("Control-doc truth check: FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1

    print("Control-doc truth check: PASS")
    for rule in CONTROL_DOC_TRUTH_RULES:
        print(f" - verified: {rule.relative_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
