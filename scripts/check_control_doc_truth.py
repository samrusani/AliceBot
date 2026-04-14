#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class ControlDocTruthRule:
    relative_path: str
    required_markers: tuple[str, ...]


CONTROL_DOC_TRUTH_RULES: tuple[ControlDocTruthRule, ...] = (
    ControlDocTruthRule(
        relative_path="README.md",
        required_markers=(
            "`v0.3.2` is the current **pre-1.0 release target** for the completed Phase 12 boundary.",
            "## Release Boundary (`v0.3.2` Target)",
            "Bridge `B1` through `B4` provider contract, auto-capture flow, review/explainability flow, and bridge docs/smoke validation",
            "Phase 12 retrieval quality stack:",
            "Historical planning/control artifacts remain available in:",
        ),
    ),
    ControlDocTruthRule(
        relative_path="ROADMAP.md",
        required_markers=(
            "Bridge Phase (`B1`-`B4`): shipped",
            "Phase 12 closeout and `v0.3.2` release update are the active control packet.",
        ),
    ),
    ControlDocTruthRule(
        relative_path=".ai/active/SPRINT_PACKET.md",
        required_markers=(
            "Phase 12 Closeout and `v0.3.2` Release Update",
            "`v0.2.0` is the latest published tag.",
            "The documented release target is `v0.3.2`",
        ),
    ),
    ControlDocTruthRule(
        relative_path="RULES.md",
        required_markers=(
            "For Hermes, use provider hooks for automation and MCP for explicit deep actions.",
            "Never fork continuity semantics by surface or runtime.",
        ),
    ),
    ControlDocTruthRule(
        relative_path=".ai/handoff/CURRENT_STATE.md",
        required_markers=(
            "Phase 9 is shipped.",
            "Phase 10 is shipped.",
            "Phase 11 is shipped.",
            "`v0.2.0` is the latest published tag.",
            "`v0.3.2` is the current release target.",
            "Phase 12 closeout and `v0.3.2` release update are the active control packet.",
        ),
    ),
    ControlDocTruthRule(
        relative_path="docs/runbooks/phase12-closeout-packet.md",
        required_markers=(
            "# Phase 12 Closeout Packet",
            "This runbook is the source-of-truth closeout packet for the accepted Phase 12 baseline through `P12-S5`.",
        ),
    ),
    ControlDocTruthRule(
        relative_path="docs/archive/planning/2026-04-08-context-compaction/README.md",
        required_markers=("This folder preserves superseded planning and control material removed from the live docs during Context Compaction 01.",),
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
)


def run_control_doc_truth_check(
    *,
    root_dir: Path = ROOT_DIR,
    rules: tuple[ControlDocTruthRule, ...] = CONTROL_DOC_TRUTH_RULES,
    disallowed_markers: tuple[str, ...] = DISALLOWED_MARKERS,
) -> list[str]:
    issues: list[str] = []
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
