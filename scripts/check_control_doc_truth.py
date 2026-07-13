#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import json
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
    candidate_pattern_templates: tuple[str, ...] = ()
    published_pattern_templates: tuple[str, ...] = ()


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
        relative_path="ARCHITECTURE.md",
        required_markers=(
            "# Architecture",
            "## Scope Boundary",
            "## Current Architectural Posture",
        ),
    ),
    ControlDocTruthRule(
        relative_path="RELEASING.md",
        required_markers=(
            "# Releasing Alice",
            "ALICE_RELEASE_CONTROLS_ATTESTATION",
            "alice_release_controls_attestation_v1",
            "independent mandatory gates",
            "exact-SHA semantic report/attestation",
            "normal cross-module mypy",
            "core plus vNext per-file coverage",
            "structured `embedding_signature`",
            "nonempty case lists",
        ),
    ),
    ControlDocTruthRule(
        relative_path="docs/vnext/consolidation.md",
        required_markers=(
            "non-null vector presence",
            "ANN/vector-search capability remains optional",
        ),
    ),
    ControlDocTruthRule(
        relative_path="docs/vnext/README.md",
        required_markers=("# Alice vNext", "## Alpha Boundary"),
    ),
    ControlDocTruthRule(
        relative_path="docs/integrations/reference-paths.md",
        required_markers=("# Reference Integration Paths", "## Scope Guard"),
    ),
    ControlDocTruthRule(
        relative_path="docs/alpha/headless-ubuntu-install.md",
        required_markers=("# Headless Ubuntu Install", "## Headless Alpha Check"),
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
        candidate_pattern_templates=(
            r"`v{version}`[^\n]*\bcandidate\b",
            r"^## What `v{version}` (?:Targets|Changes|Adds)$",
        ),
        published_pattern_templates=(
            r"`v{version}`[^\n]*\blatest published release\b",
            r"^## What `v{version}` Shipped$",
        ),
    ),
    VersionAlignedDocRule(
        relative_path=".ai/handoff/CURRENT_STATE.md",
        candidate_pattern_templates=(
            r"`v{version}`[^\n]*\bcandidate\b",
            r"^## What `v{version}` (?:Targets|Changes|Adds)$",
        ),
        published_pattern_templates=(
            r"`v{version}`[^\n]*\blatest published release\b",
            r"^## What `v{version}` Shipped$",
        ),
    ),
    VersionAlignedDocRule(
        relative_path="PRODUCT_BRIEF.md",
        candidate_pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
        published_pattern_templates=(r"`v{version}`[^\n]*\blatest published release\b",),
    ),
    VersionAlignedDocRule(
        relative_path="ROADMAP.md",
        candidate_pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
        published_pattern_templates=(r"`v{version}`[^\n]*\blatest published release\b",),
    ),
    VersionAlignedDocRule(
        relative_path="ARCHITECTURE.md",
        candidate_pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
        published_pattern_templates=(r"`v{version}`[^\n]*\blatest published[^\n]*release\b",),
    ),
    VersionAlignedDocRule(
        relative_path="README.md",
        candidate_pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
        published_pattern_templates=(r"`v{version}`[^\n]*\blatest published release\b",),
    ),
    VersionAlignedDocRule(
        relative_path="RELEASING.md",
        candidate_pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
        published_pattern_templates=(r"`v{version}`[^\n]*\blatest published release\b",),
    ),
    VersionAlignedDocRule(
        relative_path="docs/vnext/README.md",
        candidate_pattern_templates=(r"`v{version}`[^\n]*\bcandidate\b",),
        published_pattern_templates=(r"`v{version}`[^\n]*\blatest published release\b",),
    ),
    VersionAlignedDocRule(
        relative_path="docs/integrations/reference-paths.md",
        published_pattern_templates=(r"latest published `v{version}` baseline",),
    ),
    VersionAlignedDocRule(
        relative_path="docs/alpha/headless-ubuntu-install.md",
        published_pattern_templates=(r"latest published release tag\s+\(`v{version}`\)",),
    ),
)

RELEASE_DOCUMENT_STATE_SCHEMA_VERSION = "alice_release_document_state_v1"
_RELEASE_DOCUMENT_STATE_KEYS = frozenset(
    {"schema_version", "version", "publication_status", "checksums_status"}
)
_RELEASE_DOCUMENT_STATE_PATTERN = re.compile(
    r"<!-- alice-release-state: (?P<payload>\{.*\}) -->"
)
_LATEST_PUBLISHED_VERSION_PATTERN = re.compile(
    r"(?:\blatest\s+published\b(?:(?!\n[ \t]*\n)[\s\S]){0,160}?"
    r"`v(?P<after>\d+\.\d+\.\d+)`|"
    r"`v(?P<before>\d+\.\d+\.\d+)`(?:(?!\n[ \t]*\n)[\s\S]){0,160}?"
    r"\blatest\s+published\b)",
    flags=re.IGNORECASE,
)
_CHECKSUM_RECEIPT_PATTERN = re.compile(
    r"^[0-9a-f]{64}  [A-Za-z0-9][A-Za-z0-9_.+-]*$", flags=re.MULTILINE
)
_STALE_RELEASE_CLOSURE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "CHANGELOG.md",
        re.compile(r"v0\.10\.0[^\n]{0,80}current closure record", re.IGNORECASE),
    ),
    (
        "docs/release/v0.9.4-release-notes.md",
        re.compile(r"^The v0\.10\.0 remediation cycle tracks", re.IGNORECASE | re.MULTILINE),
    ),
)


def _semantic_version_key(version: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def _has_exact_release_state_keys(state: object) -> bool:
    return isinstance(state, dict) and set(state) == _RELEASE_DOCUMENT_STATE_KEYS


def _latest_structured_published_version(
    *, root_dir: Path, candidate_version: str
) -> str | None:
    """Resolve candidate-mode publication truth from structured historical notes."""

    release_dir = root_dir / "docs" / "release"
    published: list[tuple[tuple[int, int, int], str]] = []
    for path in release_dir.glob("v*-release-notes.md"):
        version = path.name.removeprefix("v").removesuffix("-release-notes.md")
        if version == candidate_version:
            continue
        key = _semantic_version_key(version)
        if key is None:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        if len(lines) < 2:
            continue
        state_match = _RELEASE_DOCUMENT_STATE_PATTERN.fullmatch(lines[1])
        if state_match is None:
            continue
        try:
            state = json.loads(state_match.group("payload"))
        except json.JSONDecodeError:
            continue
        if (
            _has_exact_release_state_keys(state)
            and state.get("schema_version") == RELEASE_DOCUMENT_STATE_SCHEMA_VERSION
            and state.get("version") == version
            and state.get("publication_status") == "published"
            and state.get("checksums_status") == "recorded"
            and _has_exact_checksum_receipt(
                root_dir / "docs" / "release" / f"v{version}-checksums.txt",
                version=version,
            )
        ):
            published.append((key, version))
    return max(published)[1] if published else None


def _has_exact_checksum_receipt(path: Path, *, version: str) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    artifact_names = [
        match.group(0).split("  ", maxsplit=1)[1]
        for match in _CHECKSUM_RECEIPT_PATTERN.finditer(text)
    ]
    return len(artifact_names) == 2 and set(artifact_names) == {
        f"alice_memory-{version}-py3-none-any.whl",
        f"alice_memory-{version}.tar.gz",
    }


def _read_release_document_mode(
    *, root_dir: Path, version: str
) -> tuple[str | None, list[str]]:
    relative_path = f"docs/release/v{version}-release-notes.md"
    path = root_dir / relative_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, [f"{relative_path}: missing file"]

    expected_title = f"# Alice v{version} Release Notes"
    issues: list[str] = []
    if not lines or lines[0] != expected_title:
        issues.append(f"{relative_path}: missing exact title '{expected_title}'")
    state_lines = [
        (index, line) for index, line in enumerate(lines) if "alice-release-state" in line
    ]
    if len(state_lines) != 1 or state_lines[0][0] != 1:
        issues.append(
            f"{relative_path}: alice-release-state must appear exactly once on line 2"
        )
        return None, issues
    match = _RELEASE_DOCUMENT_STATE_PATTERN.fullmatch(state_lines[0][1])
    if match is None:
        issues.append(f"{relative_path}: malformed alice-release-state")
        return None, issues
    try:
        state = json.loads(match.group("payload"))
    except json.JSONDecodeError as exc:
        issues.append(f"{relative_path}: invalid alice-release-state JSON: {exc}")
        return None, issues
    if not isinstance(state, dict):
        issues.append(f"{relative_path}: alice-release-state must be an object")
        return None, issues
    if not _has_exact_release_state_keys(state):
        issues.append(
            f"{relative_path}: alice-release-state must contain exactly the supported keys"
        )
    if state.get("schema_version") != RELEASE_DOCUMENT_STATE_SCHEMA_VERSION:
        issues.append(f"{relative_path}: unsupported alice-release-state schema")
    if state.get("version") != version:
        issues.append(f"{relative_path}: alice-release-state version does not match")

    publication_status = state.get("publication_status")
    checksums_status = state.get("checksums_status")
    pair = (publication_status, checksums_status)
    if pair == ("pending", "pending"):
        mode = "candidate"
    elif pair == ("published", "recorded"):
        mode = "published"
    else:
        issues.append(
            f"{relative_path}: unsupported publication/checksum state {pair!r}"
        )
        mode = None

    checksums = root_dir / "docs" / "release" / f"v{version}-checksums.txt"
    if mode == "candidate" and checksums.exists():
        issues.append(
            f"docs/release/v{version}-checksums.txt: must not exist while publication is pending"
        )
    if mode == "published":
        if not checksums.is_file():
            issues.append(
                f"docs/release/v{version}-checksums.txt: missing for recorded publication"
            )
        elif not _has_exact_checksum_receipt(checksums, version=version):
            issues.append(
                f"docs/release/v{version}-checksums.txt: must contain exactly the canonical wheel and sdist SHA-256 records"
            )
    return mode, issues

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
    "resumes feature work and clears the second audit's P2 backlog",
    "semantic attestation replaces the repository-control attestation",
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
    release_mode, release_state_issues = _read_release_document_mode(
        root_dir=root_dir, version=version
    )
    issues.extend(release_state_issues)
    latest_published_version = (
        _latest_structured_published_version(
            root_dir=root_dir, candidate_version=version
        )
        if release_mode == "candidate"
        else version
    )

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
        pattern_templates = (
            version_rule.published_pattern_templates
            if release_mode == "published"
            else version_rule.candidate_pattern_templates
        )
        for pattern_template in pattern_templates:
            pattern = pattern_template.format(version=re.escape(version))
            if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is None:
                issues.append(
                    f"{version_rule.relative_path}: missing current-version {release_mode or 'unknown'} marker matching '{pattern_template.format(version=version)}'"
                )
        if release_mode == "published":
            bounded_same_sentence = r"(?:(?!\n[ \t]*\n)[^.!?]){0,200}?"
            contradiction_term = r"(?:candidate|unshipped|unpublished|not[ \t]+published)"
            contradiction = re.compile(
                rf"(?:`v{re.escape(version)}`{bounded_same_sentence}\b{contradiction_term}\b|"
                rf"\b{contradiction_term}\b{bounded_same_sentence}`v{re.escape(version)}`)",
                flags=re.IGNORECASE,
            )
            if contradiction.search(text) is not None:
                issues.append(
                    f"{version_rule.relative_path}: describes published v{version} as unpublished or a candidate"
                )
        for match in _LATEST_PUBLISHED_VERSION_PATTERN.finditer(text):
            stated_version = match.group("after") or match.group("before")
            if latest_published_version is None:
                issues.append(
                    f"{version_rule.relative_path}: names v{stated_version} as latest published "
                    "without a structured published release record"
                )
            elif stated_version != latest_published_version:
                issues.append(
                    f"{version_rule.relative_path}: names v{stated_version} as latest published "
                    f"instead of v{latest_published_version}"
                )

    for relative_path, stale_pattern in _STALE_RELEASE_CLOSURE_PATTERNS:
        path = root_dir / relative_path
        if path.is_file() and stale_pattern.search(path.read_text(encoding="utf-8")):
            issues.append(
                f"{relative_path}: contains stale present-tense v0.10.0 closure wording"
            )

    mirror = root_dir / ".ai" / "handoff" / "CURRENT_STATE.md"
    current = root_dir / "CURRENT_STATE.md"
    if mirror.exists() and current.exists() and mirror.read_bytes() != current.read_bytes():
        issues.append(".ai/handoff/CURRENT_STATE.md: must exactly mirror CURRENT_STATE.md")

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
