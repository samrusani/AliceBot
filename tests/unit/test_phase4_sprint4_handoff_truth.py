from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import tomllib

import pytest


_ROOT = Path(__file__).resolve().parents[2]
_BASE = "dc60924f6c5486b8ba2b82dcecf22378bf043319"
_BASE_TREE = "2f1a6ababbd70ebc0106f750dc1b34d4b85fd5ca"
_BRANCH = "codex/v0130-phase4-sprint4-synthesis"
_FORMAT = "alice-v0.13.0-phase4-sprint4-synthesis-explicit-carrier-v2"
_HANDOFF_REL = "docs/handoff/2026-07-19-v0.13.0-phase4-sprint4-synthesis"
_HANDOFF = _ROOT / _HANDOFF_REL
_CARRIER_PATHS = (
    ".gitignore",
    "apps/api/src/alicebot_api/vnext_coverage_query.py",
    "apps/api/src/alicebot_api/vnext_retrieval.py",
    f"{_HANDOFF_REL}/ENGINEER_HANDOFF.md",
    f"{_HANDOFF_REL}/FIX_MATRIX.md",
    f"{_HANDOFF_REL}/README.md",
    "eval/longmemeval/count_probe.py",
    "eval/longmemeval/test_count_probe.py",
    "tests/unit/test_phase4_sprint4_handoff_truth.py",
    "tests/unit/test_vnext_coverage_query.py",
    "tests/unit/test_vnext_main.py",
    "tests/unit/test_vnext_retrieval.py",
)
_RECEIPT_EXCLUSIONS = (
    f"{_HANDOFF_REL}/BUILD_REPORT.md",
    f"{_HANDOFF_REL}/REVIEW_REPORT.md",
)
# The immutable carrier receipt, recorded in BUILD_REPORT.md and in the
# integration commit message; used to locate the carrier commit in history.
_RECEIPT_SHA256 = "b0f85fdaafcc2038f92162292b68374aa912f2e4df5ea766efb4faf1fbcfe840"
_ALLOWED_AUXILIARY_PATHS = ("coverage.json", "uv.lock")
_EXTERNAL_RELEASE_ENGINEER_DIR = "docs/benchmarks/scale/results"
_COVERAGE_FRAGMENT_PATTERN = re.compile(
    r"^\.coverage\.[A-Za-z0-9_-]+\.pid[1-9][0-9]*\.X[A-Za-z0-9]{6}x"
    r"(?:\.H[A-Za-z0-9_]{10}h)?$"
)


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", "-C", str(_ROOT), *args),
        check=check,
        capture_output=True,
    )


def _is_ignored(relative_path: str) -> bool:
    result = _git("check-ignore", "--no-index", "--quiet", relative_path, check=False)
    assert result.returncode in {0, 1}, result.stderr
    return result.returncode == 0


def _live_dirty_paths() -> set[str]:
    changed = _git("diff", "--name-only", "-z", _BASE, "--").stdout.split(b"\0")
    untracked = _git("ls-files", "--others", "--exclude-standard", "-z").stdout.split(b"\0")
    return {
        path.decode("utf-8", errors="surrogateescape")
        for path in (*changed, *untracked)
        if path
    }


def _is_external_release_engineer_output(relative_path: str) -> bool:
    path = Path(relative_path)
    return (
        path.parent.as_posix() == _EXTERNAL_RELEASE_ENGINEER_DIR
        and path.suffix == ".json"
    )


def _external_dirty_paths() -> tuple[str, ...]:
    live = _live_dirty_paths()
    return tuple(sorted(path for path in live if _is_external_release_engineer_output(path)))


def _is_allowed_auxiliary_output(relative_path: str) -> bool:
    return bool(
        relative_path in _ALLOWED_AUXILIARY_PATHS
        or _COVERAGE_FRAGMENT_PATTERN.fullmatch(relative_path)
    )


def _selected_paths() -> list[bytes]:
    live = _live_dirty_paths()
    carrier = set(_CARRIER_PATHS)
    missing = carrier - live
    assert not missing, f"carrier allowlist paths are not dirty/present: {sorted(missing)}"

    allowed_exact = carrier | set(_RECEIPT_EXCLUSIONS)
    unexpected = sorted(
        path
        for path in live
        if path not in allowed_exact
        and not _is_allowed_auxiliary_output(path)
        and not _is_external_release_engineer_output(path)
    )
    assert not unexpected, f"unexpected non-carrier dirty paths: {unexpected}"
    return [path.encode("utf-8") for path in sorted(_CARRIER_PATHS)]


def _base_mode(relative_path: bytes) -> bytes:
    tree = _git("ls-tree", "-z", _BASE, "--", relative_path.decode("utf-8")).stdout
    assert tree, relative_path
    return tree.split(b" ", 1)[0]


def build_live_receipt() -> bytes:
    parts = [
        b"format\0" + _FORMAT.encode() + b"\0",
        b"base\0" + _BASE.encode() + b"\0",
        b"branch\0" + _BRANCH.encode() + b"\0",
    ]
    for relative_bytes in _selected_paths():
        relative = relative_bytes.decode("utf-8", errors="surrogateescape")
        path = _ROOT / relative
        if path.is_symlink():
            kind = b"symlink"
            mode = b"120000"
            payload = os.readlink(path).encode("utf-8", errors="surrogateescape")
        elif path.is_file():
            kind = b"file"
            executable = bool(path.stat().st_mode & stat.S_IXUSR)
            mode = b"100755" if executable else b"100644"
            payload = path.read_bytes()
        else:
            kind = b"deleted"
            mode = _base_mode(relative_bytes)
            payload = b""
        parts.extend(
            (
                b"path\0" + relative_bytes + b"\0",
                b"mode\0" + mode + b"\0",
                b"kind\0" + kind + b"\0",
                b"sha256\0" + hashlib.sha256(payload).hexdigest().encode() + b"\0",
            )
        )
    return b"".join(parts)


def test_sprint4_handoff_truth_and_no_go_boundary() -> None:
    documents = {
        filename: (_HANDOFF / filename).read_text(encoding="utf-8")
        for filename in ("README.md", "FIX_MATRIX.md", "BUILD_REPORT.md", "ENGINEER_HANDOFF.md")
    }
    assert all("NO-GO" in document for document in documents.values())
    assert all("0/14" in document for document in documents.values())
    assert all("trace-only" in document.casefold() for document in documents.values())
    assert "Code carrier" in documents["ENGINEER_HANDOFF.md"]
    assert "benchmark closure" in documents["ENGINEER_HANDOFF.md"]
    for external_path in _external_dirty_paths():
        assert external_path in documents["BUILD_REPORT.md"]

    review_path = _HANDOFF / "REVIEW_REPORT.md"
    if review_path.exists():
        review = review_path.read_text(encoding="utf-8")
        assert "independent" in review.casefold()
        assert "Code carrier" in review
        assert "benchmark closure" in review
        assert "NO-GO" in review
        assert "0/14" in review


def test_sprint4_versions_and_protected_scope_remain_at_base() -> None:
    with (_ROOT / "pyproject.toml").open("rb") as handle:
        assert tomllib.load(handle)["project"]["version"] == "0.12.0"
    package = (_ROOT / "apps/web/package.json").read_text(encoding="utf-8")
    assert re.search(r'"version"\s*:\s*"0\.12\.0"', package)
    assert _git("rev-parse", f"{_BASE}^{{tree}}").stdout.decode().strip() == _BASE_TREE

    carrier = set(_CARRIER_PATHS)
    forbidden_carrier_prefixes = (
        "docs/benchmarks/",
        "docs/release/",
        "docs/handoff/2026-07-13-v0.10-audit-remediation/",
        "docs/handoff/2026-07-13-v0.10.2-post-release-remediation/",
        "docs/handoff/2026-07-14-v0.10.4-remediation/",
        "docs/handoff/2026-07-15-v0.11.0-phase1-periphery-cut/",
        "docs/handoff/2026-07-16-v0.11.1-phase2-debt-sweep/",
        "docs/handoff/2026-07-18-v0.12.0-phase3-structural-refactor/",
    )
    assert all(
        not path.startswith(forbidden_carrier_prefixes)
        for path in carrier
    )
    protected_sqlite = "apps/api/src/alicebot_api/vnext_stores/sqlite/memory_access.py"
    assert protected_sqlite not in carrier

    # Post-integration form: the carrier COMMIT touched neither the protected
    # SQLite scale file, the immutable records, nor the governed versions.
    # Later reviewed commits by the release engineer (the vector-cache lane)
    # legitimately change the protected file; the invariant guarded here is
    # that Sprint 4 itself never did.
    carrier_commit_paths = _carrier_commit_paths()
    assert protected_sqlite not in carrier_commit_paths
    forbidden_committed_prefixes = (
        "docs/release/",
        "docs/handoff/2026-07-13-",
        "docs/handoff/2026-07-14-",
        "docs/handoff/2026-07-15-",
        "docs/handoff/2026-07-16-",
        "docs/handoff/2026-07-18-",
    )
    assert all(
        not path.startswith(forbidden_committed_prefixes)
        for path in carrier_commit_paths
    )
    assert "pyproject.toml" not in carrier_commit_paths
    assert "apps/web/package.json" not in carrier_commit_paths


def _carrier_commit_paths() -> frozenset[str]:
    """Paths changed by the integrated Sprint 4 carrier commit.

    The commit is located by the immutable receipt hash recorded in its
    message, so this guard survives later history without pinning a sha.
    """
    commits = (
        _git("log", "--format=%H", f"--grep={_RECEIPT_SHA256}", "HEAD")
        .stdout.decode()
        .split()
    )
    assert len(commits) == 1, commits
    listing = _git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", commits[0]
    ).stdout.decode()
    return frozenset(line for line in listing.splitlines() if line)


def test_sprint4_carrier_allowlist_isolated_from_external_scale_lane() -> None:
    # Post-integration form: the carrier commit changed exactly the 12
    # receipt-bound paths plus the two receipt-excluded report documents,
    # and nothing from the concurrent release-engineer scale lane.
    committed = _carrier_commit_paths()
    assert committed == set(_CARRIER_PATHS) | set(_RECEIPT_EXCLUSIONS), sorted(
        committed.symmetric_difference(set(_CARRIER_PATHS) | set(_RECEIPT_EXCLUSIONS))
    )


def test_sprint4_allows_only_precise_root_coverage_fragments() -> None:
    assert _is_allowed_auxiliary_output(
        ".coverage.ci_host.pid123.XaB09zZx.Hv4NT5NRZ1Uh"
    )
    assert _is_allowed_auxiliary_output(".coverage.ci_host.pid123.XaB09zZx")
    for near_miss in (
        ".coverage.ci_host.pid0.XaB09zZx",
        ".coverage.ci.host.pid123.XaB09zZx",
        ".coverage.ci_host.pid123.Xshortx",
        ".coverage.ci_host.pid123.XaB09zZx.Hshort",
        ".coverage.ci_host.pid123.XaB09zZx.extra.again",
        "tmp/.coverage.ci_host.pid123.XaB09zZx",
        ".coverage-arbitrary",
    ):
        assert not _is_allowed_auxiliary_output(near_miss)


def test_sprint4_reports_are_unignored_without_weakening_generic_policy() -> None:
    for filename in ("BUILD_REPORT.md", "REVIEW_REPORT.md"):
        assert not _is_ignored(f"{_HANDOFF_REL}/{filename}")
        assert _is_ignored(filename)


def test_sprint4_live_carrier_receipt_or_integrated_ancestry() -> None:
    head = _git("rev-parse", "HEAD").stdout.decode().strip()
    if head != _BASE:
        ancestry = _git("merge-base", "--is-ancestor", _BASE, "HEAD", check=False)
        assert ancestry.returncode == 0
        pytest.skip("carrier has been integrated; the immutable receipt records pre-commit bytes")

    build_report = (_HANDOFF / "BUILD_REPORT.md").read_text(encoding="utf-8")
    match = re.search(r"carrier receipt sha256:\s*`([0-9a-f]{64})`", build_report)
    assert match is not None
    assert hashlib.sha256(build_live_receipt()).hexdigest() == match.group(1)
