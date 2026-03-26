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
        relative_path="ARCHITECTURE.md",
        required_markers=("through Phase 3 Sprint 9",),
    ),
    ControlDocTruthRule(
        relative_path="ROADMAP.md",
        required_markers=(
            "through Phase 3 Sprint 9",
            "canonical Phase 3 gate entrypoints",
        ),
    ),
    ControlDocTruthRule(
        relative_path="README.md",
        required_markers=(
            "through Phase 3 Sprint 9",
            "Canonical gate entrypoints: `scripts/run_phase3_*.py` are the control-plane entrypoint wrappers",
        ),
    ),
    ControlDocTruthRule(
        relative_path="PRODUCT_BRIEF.md",
        required_markers=("canonical v1 release-readiness validation scenario",),
    ),
    ControlDocTruthRule(
        relative_path="RULES.md",
        required_markers=("v1 release-readiness validation scenario",),
    ),
    ControlDocTruthRule(
        relative_path=".ai/handoff/CURRENT_STATE.md",
        required_markers=(
            "through Phase 3 Sprint 9",
            "Gate entrypoints are canonicalized to Phase 3 runner script names",
        ),
    ),
    ControlDocTruthRule(
        relative_path="docs/runbooks/phase3-closeout-packet.md",
        required_markers=(
            "accepted Phase 3 Sprint 9 baseline",
            "Required Phase 3 Go/No-Go Commands",
            "Required PASS Evidence Bundle",
            "Explicit Deferred Scope Entering Next Phase",
        ),
    ),
)

DISALLOWED_MARKERS: tuple[str, ...] = (
    "through Phase 2 Sprint 14",
    "current through Phase 2 Sprint 14",
    "accepted Phase 2 Sprint 14 baseline",
    "canonical Phase 2 gate ownership",
    "Gate ownership is canonicalized to Phase 2 runner scripts",
    "through Phase 2 Sprint 11",
    "current through Phase 2 Sprint 11",
    "Phase 2 Sprint 7",
    "v1 ship gate",
    "v1 ship-gate",
    "ship gates",
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
