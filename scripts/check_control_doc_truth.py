#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib


ROOT_DIR = Path(__file__).resolve().parents[1]
PACKAGE_DESCRIPTION_RELATIVE_PATH = "docs/pypi-description.md"
_PACKAGE_DESCRIPTION_VERSION_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)
_PACKAGE_DESCRIPTION_STATE_PATTERN = re.compile(
    r"\b(?:latest\s+(?:published\s+)?release|candidate|release[ -]?gating|"
    r"unpublished|publication\s+pending)\b",
    flags=re.IGNORECASE,
)
_LATEST_RELEASE_NOTES_DOCS = ("README.md", "docs/vnext/README.md")
_LATEST_CHECKSUM_DOCS = ("ARCHITECTURE.md", "PRODUCT_BRIEF.md", "ROADMAP.md")
_LITERAL_INSTALL_TAG_PATTERN = re.compile(r"--tag\s+v(?P<version>\d+\.\d+\.\d+)\b")
_PUBLISHED_FUTURE_STATE_PATTERN = re.compile(
    r"\b(?:will\s+be\s+(?:published|recorded|uploaded|created)|"
    r"after\s+publication|once\s+published)\b",
    flags=re.IGNORECASE,
)
# v0.10.3 is an immutable published baseline whose historical prose cannot be
# rewritten. Enforce publication-neutral notes for every later release.
_FUTURE_STATE_ENFORCEMENT_AFTER = (0, 10, 3)
_ACTIVE_REMEDIATION_HANDOFF = Path("docs/handoff/2026-07-14-v0.10.4-remediation")
_ACTIVE_REMEDIATION_VERSION = "0.10.4"
_ACTIVE_REMEDIATION_CODE_COMMIT = "41641fbfa5dc8198bf47bad8849c828dbb519617"
_ACTIVE_REMEDIATION_CODE_TREE = "dade94f367fc42a2fa9c6906c1f3bd91bf392fea"
_ACTIVE_REMEDIATION_CODE_PARENT = "d52e32114eb0b4ef63499e53be14b70dc0864487"
_ACTIVE_REMEDIATION_AUDIT_COMMIT = "42b8c2d470a7535ec39d4028c2ef3868dcd4598a"
_ACTIVE_REMEDIATION_AUDIT_TREE = "96a7f4d940bcf1154d31d730450e00935ba06341"
# Recipe: read `git ls-tree -r -z --full-tree <revision>` in Git's byte order,
# remove records whose path is in the correction/publication-truth allowlists,
# retain every remaining `<mode> <type> <object>\t<path>\0` byte, then SHA-256
# the concatenation. This exact v0.10.4 code-boundary manifest can be verified
# from HEAD in a real depth-1 clone without weakening content coverage.
_ACTIVE_REMEDIATION_FILTERED_TREE_SHA256 = "90cc8c16c9c94adee1585740e16be5f6c73d481a2e7b870191d5a638a20a0b53"
_ACTIVE_REMEDIATION_FILTERED_TREE_RECORDS = 1172
_ACTIVE_REMEDIATION_FILTERED_TREE_BYTES = 115611
_ACTIVE_REMEDIATION_CONTENT_HASHES: dict[str, str] = {
    "pyproject.toml": "f9eeb11ba086223523374c5e5fad6044d81bd40a23925fa44a7c09fb9ec6e099",
    "apps/web/package.json": "17c1a093afa6f8ff606414ff6ea741b28da019076fe67eb577ab2dd58169e164",
    "apps/web/scripts/npm-advisory-audit.mjs": ("8ede1ef336b1bf57f83b5d05cef07fc18c33a40e9e7668280e9bf6badc613616"),
    ".github/workflows/tests.yml": ("dedcec40527969db2dcc9023840496eb0df3277a89c70044fb7aeda22f6d60a2"),
}
_ACTIVE_REMEDIATION_CORRECTION_PATHS: tuple[str, ...] = (
    "docs/handoff/2026-07-14-v0.10.4-remediation/README.md",
    "docs/handoff/2026-07-14-v0.10.4-remediation/ENGINEER_HANDOFF.md",
    "docs/handoff/2026-07-14-v0.10.4-remediation/BUILD_REPORT.md",
    "docs/handoff/2026-07-14-v0.10.4-remediation/FIX_MATRIX.md",
    "docs/handoff/2026-07-14-v0.10.4-remediation/SURFACE_INVENTORY.md",
    "scripts/check_control_doc_truth.py",
    "tests/unit/test_control_doc_truth.py",
)
_ACTIVE_REMEDIATION_FUTURE_TRUTH_PATHS: tuple[str, ...] = (
    "README.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CURRENT_STATE.md",
    "PRODUCT_BRIEF.md",
    "RELEASING.md",
    "ROADMAP.md",
    ".ai/handoff/CURRENT_STATE.md",
    "docs/alpha/headless-ubuntu-install.md",
    "docs/integrations/reference-paths.md",
    "docs/vnext/README.md",
    "docs/release/v0.10.4-release-notes.md",
    "docs/release/v0.10.4-checksums.txt",
)
_ACTIVE_REMEDIATION_MARKERS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "Repair Batch 16 is the current bounded correction",
        "29-codepoint `chr()`-enumerated",
        "Batch 15 is historical, independently approved, and superseded",
    ),
    "BUILD_REPORT.md": (
        "## Historical Builder Repair Batch 16 dirty-tree scope and status",
        "### Historical Repair Batch 16 dirty-tree verification",
        "whitespace finding discovered",
        "Refreeze 17 changes only documentation-truth enforcement",
        "Independent review of the exact frozen Batch 16 carrier: **CHANGES",
    ),
    "ENGINEER_HANDOFF.md": (
        "## Builder Repair Batch 16 review delta",
        "U+001C–U+001F",
        "```md\n## Upgrade Overview",
        "- [x] memory schema",
        "- [x] continuity APIs",
    ),
    "FIX_MATRIX.md": (
        "## Builder Repair Batch 16 closure",
        "Embedding CAS Python-strip parity",
        "Repair Batch 16 is the current bounded correction",
        "Repair Batch 15 was independently approved",
        "Batch 16 review approved production semantics",
        "## Refreeze 17 documentation-truth closure",
        "Batch 15 is historical and superseded",
    ),
    "SURFACE_INVENTORY.md": (
        "## Repair Batch 16 correction appendix",
        "three embedding-CAS SQL consumers",
        "NBSP and U+001C",
    ),
}
_ACTIVE_FINALIZATION_MARKERS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "Code remediation commit `41641fbfa5dc8198bf47bad8849c828dbb519617`",
        "npm advisory endpoint commit `42b8c2d470a7535ec39d4028c2ef3868dcd4598a`",
        "At control-tower delivery, this documentation correction is intentionally uncommitted",
    ),
    "BUILD_REPORT.md": (
        "## Refreeze 17 exact-code handoff truth",
        "96a7f4d940bcf1154d31d730450e00935ba06341",
        "The final release SHA is deliberately not predicted",
    ),
    "ENGINEER_HANDOFF.md": (
        "Code boundary `42b8c2d470a7535ec39d4028c2ef3868dcd4598a`",
        "At control-tower delivery, the documentation correction itself is intentionally uncommitted",
        "Do not treat either code commit as the future release SHA",
    ),
    "FIX_MATRIX.md": (
        "## Refreeze 17 exact-code receipt",
        "code tree `96a7f4d940bcf1154d31d730450e00935ba06341`",
    ),
    "SURFACE_INVENTORY.md": (
        "Version sources were committed at `0.10.4`",
        "historical pre-edit inventory",
    ),
}
_ACTIVE_REMEDIATION_FORBIDDEN_MARKERS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "Repair Batch 14 is the current bounded correction",
        "Independent review and release approval remain pending",
        "all six groups",
    ),
    "BUILD_REPORT.md": (
        "## Builder Repair Batch 14 scope and current status",
        "### Current Repair Batch 14 verification",
        "Independent review of the exact fingerprinted Batch 14 carrier: **PENDING**",
        "Repair Batch 15 is the current bounded correction",
        "its six groups",
    ),
    "ENGINEER_HANDOFF.md": (
        "## Builder Repair Batch 14 review deltas",
        "scopes all six groups",
    ),
    "FIX_MATRIX.md": (
        "across the six groups",
        "## Builder Repair Batch 14 closure",
        "Repair Batch 15 is the current bounded correction",
    ),
    "SURFACE_INVENTORY.md": (
        "six memory/source/open-loop/artifact/entity/project groups",
        "## Repair Batch 14 correction appendix",
    ),
}
_ACTIVE_FINALIZATION_FORBIDDEN_MARKERS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "control-tower handoff for the uncommitted v0.10.4 remediation",
        "The tree is intentionally uncommitted. No version source was bumped",
    ),
    "BUILD_REPORT.md": (
        "Package version intentionally remains `0.10.3` until release-engineer finalization",
        "the package version remains `0.10.3`",
    ),
    "ENGINEER_HANDOFF.md": (
        "Review the uncommitted tree in this order",
        "Before the finalization commit, bump every governed version source to `0.10.4`",
    ),
    "FIX_MATRIX.md": ("v0.10.4 as uncommitted remediation",),
    "SURFACE_INVENTORY.md": (
        "Version sources remain `0.10.3` during this uncommitted remediation",
        "describing the current tree as uncommitted",
    ),
}


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
        required_markers=(
            "This folder preserves superseded planning and control material removed from the live docs during Context Compaction 01.",
        ),
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
_RELEASE_DOCUMENT_STATE_KEYS = frozenset({"schema_version", "version", "publication_status", "checksums_status"})
_RELEASE_DOCUMENT_STATE_PATTERN = re.compile(r"<!-- alice-release-state: (?P<payload>\{.*\}) -->")
_LATEST_PUBLISHED_VERSION_PATTERN = re.compile(
    r"(?:\blatest\s+published\b(?:(?!\n[ \t]*\n)[\s\S]){0,160}?"
    r"`v(?P<after>\d+\.\d+\.\d+)`|"
    r"`v(?P<before>\d+\.\d+\.\d+)`(?:(?!\n[ \t]*\n)[\s\S]){0,160}?"
    r"\blatest\s+published\b)",
    flags=re.IGNORECASE,
)
_CHECKSUM_RECEIPT_PATTERN = re.compile(r"^[0-9a-f]{64}  [A-Za-z0-9][A-Za-z0-9_.+-]*$", flags=re.MULTILINE)
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


def _markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match is not None else ""


def _validate_package_description(root_dir: Path, project: object) -> list[str]:
    issues: list[str] = []
    configured_readme = project.get("readme") if isinstance(project, dict) else None
    if configured_readme != PACKAGE_DESCRIPTION_RELATIVE_PATH:
        issues.append(
            f"pyproject.toml: project.readme must point to the evergreen {PACKAGE_DESCRIPTION_RELATIVE_PATH!r}"
        )
    path = root_dir / PACKAGE_DESCRIPTION_RELATIVE_PATH
    try:
        description = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        issues.append(f"{PACKAGE_DESCRIPTION_RELATIVE_PATH}: missing or unreadable")
        return issues
    if _PACKAGE_DESCRIPTION_VERSION_PATTERN.search(description):
        issues.append(f"{PACKAGE_DESCRIPTION_RELATIVE_PATH}: contains a version literal")
    if _PACKAGE_DESCRIPTION_STATE_PATTERN.search(description):
        issues.append(f"{PACKAGE_DESCRIPTION_RELATIVE_PATH}: contains release-state language")
    return issues


def _governed_versions(root_dir: Path) -> tuple[str | None, str | None]:
    python_version: str | None = None
    web_version: str | None = None
    try:
        with (root_dir / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle).get("project")
        if isinstance(project, dict) and isinstance(project.get("version"), str):
            python_version = project["version"]
    except (OSError, tomllib.TOMLDecodeError):
        pass
    try:
        package = json.loads((root_dir / "apps/web/package.json").read_text(encoding="utf-8"))
        if isinstance(package, dict) and isinstance(package.get("version"), str):
            web_version = package["version"]
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    return python_version, web_version


def _validate_active_remediation_handoff(root_dir: Path) -> list[str]:
    handoff_dir = root_dir / _ACTIVE_REMEDIATION_HANDOFF
    if not handoff_dir.is_dir():
        return []

    issues: list[str] = []
    for relative_path, markers in _ACTIVE_REMEDIATION_MARKERS.items():
        path = handoff_dir / relative_path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            issues.append(f"{path.relative_to(root_dir)}: missing or unreadable")
            continue
        for marker in markers:
            if marker not in text:
                issues.append(f"{path.relative_to(root_dir)}: missing Repair Batch 16 truth marker {marker!r}")
        normalized_text = " ".join(text.split()).casefold()
        for marker in _ACTIVE_REMEDIATION_FORBIDDEN_MARKERS.get(relative_path, ()):
            normalized_marker = " ".join(marker.split()).casefold()
            if normalized_marker in normalized_text:
                issues.append(f"{path.relative_to(root_dir)}: contains stale remediation marker {marker!r}")
        for marker in _ACTIVE_FINALIZATION_MARKERS.get(relative_path, ()):
            normalized_marker = " ".join(marker.split()).casefold()
            if normalized_marker not in normalized_text:
                issues.append(f"{path.relative_to(root_dir)}: missing finalization truth marker {marker!r}")
        for marker in _ACTIVE_FINALIZATION_FORBIDDEN_MARKERS.get(relative_path, ()):
            normalized_marker = " ".join(marker.split()).casefold()
            if normalized_marker in normalized_text:
                issues.append(f"{path.relative_to(root_dir)}: contains stale finalization marker {marker!r}")
    return issues


def _run_git(root_dir: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", "-C", str(root_dir), *args),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git_stdout(root_dir: Path, *args: str) -> tuple[str | None, str | None]:
    result = _run_git(root_dir, *args)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip() or f"exit {result.returncode}"
        return None, detail
    return result.stdout.decode("utf-8", errors="strict").strip(), None


def _filtered_tree_manifest(
    root_dir: Path,
    revision: str,
) -> tuple[tuple[str, int, int] | None, str | None]:
    result = _run_git(root_dir, "ls-tree", "-r", "-z", "--full-tree", revision)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip() or f"exit {result.returncode}"
        return None, detail

    excluded_paths = {
        path.encode("utf-8")
        for path in (*_ACTIVE_REMEDIATION_CORRECTION_PATHS, *_ACTIVE_REMEDIATION_FUTURE_TRUTH_PATHS)
    }
    digest = hashlib.sha256()
    record_count = 0
    byte_count = 0
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        _, separator, path = record.partition(b"\t")
        if not separator:
            return None, "git ls-tree returned a malformed NUL-delimited record"
        if path in excluded_paths:
            continue
        digest.update(record)
        digest.update(b"\0")
        record_count += 1
        byte_count += len(record) + 1
    return (digest.hexdigest(), record_count, byte_count), None


def _validate_active_remediation_code_receipt(root_dir: Path) -> list[str]:
    if not (root_dir / _ACTIVE_REMEDIATION_HANDOFF).is_dir():
        return []

    issues: list[str] = []
    python_version, web_version = _governed_versions(root_dir)
    if (python_version, web_version) != (_ACTIVE_REMEDIATION_VERSION, _ACTIVE_REMEDIATION_VERSION):
        issues.append(
            "governed version sources must both equal "
            f"{_ACTIVE_REMEDIATION_VERSION}; got pyproject={python_version!r}, web={web_version!r}"
        )

    # Source archives intentionally omit Git metadata. In that mode this rule
    # still requires aligned governed versions, while archive/package parity,
    # provenance, and content are enforced by their dedicated release gates.
    if not (root_dir / ".git").exists():
        return issues

    current_manifest, manifest_error = _filtered_tree_manifest(root_dir, "HEAD")
    expected_manifest = (
        _ACTIVE_REMEDIATION_FILTERED_TREE_SHA256,
        _ACTIVE_REMEDIATION_FILTERED_TREE_RECORDS,
        _ACTIVE_REMEDIATION_FILTERED_TREE_BYTES,
    )
    if manifest_error is not None:
        issues.append(f"unable to compute current HEAD filtered content manifest ({manifest_error})")
    elif current_manifest != expected_manifest:
        issues.append(
            "current HEAD filtered content manifest must equal exact code boundary "
            f"{expected_manifest!r}, got {current_manifest!r}"
        )

    shallow_value, shallow_error = _git_stdout(root_dir, "rev-parse", "--is-shallow-repository")
    if shallow_error is not None or shallow_value not in {"true", "false"}:
        shallow_detail = shallow_error or f"unexpected output {shallow_value!r}"
        issues.append(f"unable to determine whether repository history is shallow ({shallow_detail})")
        is_shallow = True
    else:
        is_shallow = shallow_value == "true"

    if not is_shallow:
        receipt_rows = (
            (
                "remediation",
                _ACTIVE_REMEDIATION_CODE_COMMIT,
                _ACTIVE_REMEDIATION_CODE_TREE,
                _ACTIVE_REMEDIATION_CODE_PARENT,
            ),
            (
                "npm advisory endpoint",
                _ACTIVE_REMEDIATION_AUDIT_COMMIT,
                _ACTIVE_REMEDIATION_AUDIT_TREE,
                _ACTIVE_REMEDIATION_CODE_COMMIT,
            ),
        )
        for label, commit, expected_tree, expected_parent in receipt_rows:
            resolved_commit, error = _git_stdout(root_dir, "rev-parse", "--verify", f"{commit}^{{commit}}")
            if error is not None or resolved_commit != commit:
                issues.append(f"{label} code receipt: commit {commit} is unavailable or resolves incorrectly ({error})")
                continue
            resolved_tree, error = _git_stdout(root_dir, "rev-parse", "--verify", f"{commit}^{{tree}}")
            if error is not None or resolved_tree != expected_tree:
                issues.append(f"{label} code receipt: tree must be {expected_tree}, got {resolved_tree!r} ({error})")
            resolved_parent, error = _git_stdout(root_dir, "rev-parse", "--verify", f"{commit}^")
            if error is not None or resolved_parent != expected_parent:
                issues.append(
                    f"{label} code receipt: parent must be {expected_parent}, got {resolved_parent!r} ({error})"
                )

        ancestry = _run_git(root_dir, "merge-base", "--is-ancestor", _ACTIVE_REMEDIATION_AUDIT_COMMIT, "HEAD")
        if ancestry.returncode != 0:
            issues.append(f"current HEAD must descend from exact code boundary {_ACTIVE_REMEDIATION_AUDIT_COMMIT}")

        committed_exclusions = (*_ACTIVE_REMEDIATION_CORRECTION_PATHS, *_ACTIVE_REMEDIATION_FUTURE_TRUTH_PATHS)
        committed_pathspecs = (".", *(f":(exclude){path}" for path in committed_exclusions))
        committed_content = _run_git(
            root_dir,
            "diff",
            "--quiet",
            _ACTIVE_REMEDIATION_AUDIT_COMMIT,
            "HEAD",
            "--",
            *committed_pathspecs,
        )
        if committed_content.returncode == 1:
            issues.append("current HEAD changes tracked content outside the handoff-truth correction allowlist")
        elif committed_content.returncode != 0:
            issues.append(f"unable to compare current HEAD with code boundary (exit {committed_content.returncode})")

    working_pathspecs = (".", *(f":(exclude){path}" for path in _ACTIVE_REMEDIATION_CORRECTION_PATHS))
    working_content = _run_git(root_dir, "diff", "--quiet", "HEAD", "--", *working_pathspecs)
    if working_content.returncode == 1:
        issues.append("working tree changes tracked content outside the handoff-truth correction allowlist")
    elif working_content.returncode != 0:
        issues.append(f"unable to validate working-tree correction scope (exit {working_content.returncode})")

    for relative_path, expected_hash in _ACTIVE_REMEDIATION_CONTENT_HASHES.items():
        if not is_shallow:
            committed = _run_git(root_dir, "show", f"{_ACTIVE_REMEDIATION_AUDIT_COMMIT}:{relative_path}")
            if committed.returncode != 0:
                issues.append(f"code receipt: unable to read {relative_path} from {_ACTIVE_REMEDIATION_AUDIT_COMMIT}")
            else:
                committed_hash = hashlib.sha256(committed.stdout).hexdigest()
                if committed_hash != expected_hash:
                    issues.append(
                        f"code receipt: committed {relative_path} SHA-256 must be {expected_hash}, got {committed_hash}"
                    )
        try:
            working_hash = hashlib.sha256((root_dir / relative_path).read_bytes()).hexdigest()
        except OSError:
            issues.append(f"code receipt: current {relative_path} is missing or unreadable")
            continue
        if working_hash != expected_hash:
            issues.append(f"code receipt: current {relative_path} SHA-256 must be {expected_hash}, got {working_hash}")
    return issues


def _has_exact_release_state_keys(state: object) -> bool:
    return isinstance(state, dict) and set(state) == _RELEASE_DOCUMENT_STATE_KEYS


def _latest_structured_published_version(*, root_dir: Path, candidate_version: str) -> str | None:
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
    artifact_names = [match.group(0).split("  ", maxsplit=1)[1] for match in _CHECKSUM_RECEIPT_PATTERN.finditer(text)]
    return len(artifact_names) == 2 and set(artifact_names) == {
        f"alice_memory-{version}-py3-none-any.whl",
        f"alice_memory-{version}.tar.gz",
    }


def _read_release_document_mode(*, root_dir: Path, version: str) -> tuple[str | None, list[str]]:
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
    state_lines = [(index, line) for index, line in enumerate(lines) if "alice-release-state" in line]
    if len(state_lines) != 1 or state_lines[0][0] != 1:
        issues.append(f"{relative_path}: alice-release-state must appear exactly once on line 2")
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
        issues.append(f"{relative_path}: alice-release-state must contain exactly the supported keys")
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
        issues.append(f"{relative_path}: unsupported publication/checksum state {pair!r}")
        mode = None

    checksums = root_dir / "docs" / "release" / f"v{version}-checksums.txt"
    if mode == "candidate" and checksums.exists():
        issues.append(f"docs/release/v{version}-checksums.txt: must not exist while publication is pending")
    if mode == "published":
        if not checksums.is_file():
            issues.append(f"docs/release/v{version}-checksums.txt: missing for recorded publication")
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
    issues.extend(_validate_package_description(root_dir, project))
    issues.extend(_validate_active_remediation_handoff(root_dir))
    issues.extend(_validate_active_remediation_code_receipt(root_dir))
    release_mode, release_state_issues = _read_release_document_mode(root_dir=root_dir, version=version)
    issues.extend(release_state_issues)
    latest_published_version = (
        _latest_structured_published_version(root_dir=root_dir, candidate_version=version)
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

    if latest_published_version is not None:
        expected_notes = f"v{latest_published_version}-release-notes.md"
        for relative_path in _LATEST_RELEASE_NOTES_DOCS:
            path = root_dir / relative_path
            if path.is_file() and expected_notes not in path.read_text(encoding="utf-8"):
                issues.append(f"{relative_path}: latest release-notes link must target {expected_notes}")

        expected_checksums = f"docs/release/v{latest_published_version}-checksums.txt"
        for relative_path in _LATEST_CHECKSUM_DOCS:
            path = root_dir / relative_path
            if path.is_file() and expected_checksums not in path.read_text(encoding="utf-8"):
                issues.append(f"{relative_path}: published checksum pointer must target {expected_checksums}")

        current_state = root_dir / "CURRENT_STATE.md"
        if current_state.is_file():
            release_boundary = _markdown_section(current_state.read_text(encoding="utf-8"), "## Release Boundary")
            if expected_checksums not in release_boundary:
                issues.append(f"CURRENT_STATE.md: Release Boundary checksum pointer must target {expected_checksums}")

        install_guide = root_dir / "docs" / "alpha" / "headless-ubuntu-install.md"
        if install_guide.is_file():
            install_text = install_guide.read_text(encoding="utf-8")
            for match in _LITERAL_INSTALL_TAG_PATTERN.finditer(install_text):
                if match.group("version") != latest_published_version:
                    issues.append(
                        "docs/alpha/headless-ubuntu-install.md: literal install tag "
                        f"v{match.group('version')} must match latest published "
                        f"v{latest_published_version}"
                    )

    version_key = _semantic_version_key(version)
    if release_mode == "published" and version_key is not None and version_key > _FUTURE_STATE_ENFORCEMENT_AFTER:
        notes_path = root_dir / "docs" / "release" / f"v{version}-release-notes.md"
        if notes_path.is_file() and _PUBLISHED_FUTURE_STATE_PATTERN.search(notes_path.read_text(encoding="utf-8")):
            issues.append(f"docs/release/v{version}-release-notes.md: published notes contain future-state language")

    for relative_path, stale_pattern in _STALE_RELEASE_CLOSURE_PATTERNS:
        path = root_dir / relative_path
        if path.is_file() and stale_pattern.search(path.read_text(encoding="utf-8")):
            issues.append(f"{relative_path}: contains stale present-tense v0.10.0 closure wording")

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
