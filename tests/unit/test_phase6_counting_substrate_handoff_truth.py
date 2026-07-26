from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[2]
BASE = "a09c60c2fdb3b559cc3bf4099d457e79ede415cc"
BASE_TREE = "f73cc2bc04b7d5cf5bf4c7afcd0225b356bf7ed3"
FORMAT = "alice-v0.14.0-phase6-counting-substrate-explicit-carrier-v1"
BRANCH = "codex/phase6-counting-substrate"
HANDOFF_REL = "docs/handoff/2026-07-24-v0.14.0-phase6-counting-substrate"
HANDOFF = ROOT / HANDOFF_REL
CARRIER_PATHS = (
    "apps/api/alembic/versions/20260724_0095_occurrence_substrate.py",
    "apps/api/src/alicebot_api/cli/capture.py",
    "apps/api/src/alicebot_api/mcp/context.py",
    "apps/api/src/alicebot_api/mcp/memories.py",
    "apps/api/src/alicebot_api/mcp/review.py",
    "apps/api/src/alicebot_api/memory.py",
    "apps/api/src/alicebot_api/onramp.py",
    "apps/api/src/alicebot_api/openapi_operation_contracts.py",
    "apps/api/src/alicebot_api/routers/vnext_memories.py",
    "apps/api/src/alicebot_api/sqlite_schema.py",
    "apps/api/src/alicebot_api/sqlite_store.py",
    "apps/api/src/alicebot_api/vnext_capture.py",
    "apps/api/src/alicebot_api/vnext_memory_commit.py",
    "apps/api/src/alicebot_api/vnext_occurrence_predicates.py",
    "apps/api/src/alicebot_api/vnext_occurrence_retrieval.py",
    "apps/api/src/alicebot_api/vnext_occurrence_taxonomy.py",
    "apps/api/src/alicebot_api/vnext_occurrence_write.py",
    "apps/api/src/alicebot_api/vnext_occurrences.py",
    "apps/api/src/alicebot_api/vnext_projects.py",
    "apps/api/src/alicebot_api/vnext_retrieval.py",
    "apps/api/src/alicebot_api/vnext_scheduler.py",
    "apps/api/src/alicebot_api/vnext_store.py",
    "apps/api/src/alicebot_api/vnext_stores/postgres/memory_lifecycle.py",
    "apps/api/src/alicebot_api/vnext_stores/postgres/occurrence_accounting.py",
    "apps/api/src/alicebot_api/vnext_stores/postgres/occurrences.py",
    "apps/api/src/alicebot_api/vnext_stores/sqlite/memory_lifecycle.py",
    "apps/api/src/alicebot_api/vnext_stores/sqlite/occurrence_accounting.py",
    "apps/api/src/alicebot_api/vnext_stores/sqlite/occurrences.py",
    f"{HANDOFF_REL}/DESIGN.md",
    f"{HANDOFF_REL}/ENGINEER_HANDOFF.md",
    f"{HANDOFF_REL}/FIX_MATRIX.md",
    f"{HANDOFF_REL}/README.md",
    "eval/longmemeval/adapter.py",
    "eval/longmemeval/count_probe.py",
    "eval/longmemeval/coverage_probe.py",
    "eval/longmemeval/runner.py",
    "eval/longmemeval/slices/phase6-non-count-101.txt",
    "eval/longmemeval/test_adapter_occurrences.py",
    "eval/longmemeval/test_count_probe.py",
    "eval/longmemeval/test_harness.py",
    "eval/longmemeval/test_phase6_eval_controls.py",
    "tests/integration/test_lifecycle_transitions_postgres.py",
    "tests/integration/test_memory_fact_keys_postgres.py",
    "tests/integration/test_migrations.py",
    "tests/integration/test_occurrence_substrate_postgres.py",
    "tests/integration/test_source_review_identity_api.py",
    "tests/unit/test_20260724_0095_occurrence_substrate.py",
    "tests/unit/test_cli_demo_reset_occurrences.py",
    "tests/unit/test_main.py",
    "tests/unit/test_mcp.py",
    "tests/unit/test_memory.py",
    "tests/unit/test_occurrence_store.py",
    "tests/unit/test_occurrence_store_seam_regressions.py",
    "tests/unit/test_phase6_counting_substrate_handoff_truth.py",
    "tests/unit/test_providers_router_split.py",
    "tests/unit/test_public_errors.py",
    "tests/unit/test_sqlite_onramp.py",
    "tests/unit/test_store_events_revisions_split.py",
    "tests/unit/test_store_graph_open_loops_split.py",
    "tests/unit/test_store_memory_access_split.py",
    "tests/unit/test_store_memory_lifecycle_split.py",
    "tests/unit/test_vnext_capture.py",
    "tests/unit/test_vnext_main.py",
    "tests/unit/test_vnext_occurrence_taxonomy.py",
    "tests/unit/test_vnext_occurrence_write.py",
    "tests/unit/test_vnext_occurrences.py",
    "tests/unit/test_vnext_projects.py",
    "tests/unit/test_vnext_retrieval.py",
    "tests/unit/test_vnext_scheduler.py",
    "tests/unit/test_vnext_store.py",
    "tests/unit/test_workspaces_router_split.py",
)
RECEIPT_EXCLUSIONS = (
    f"{HANDOFF_REL}/BUILD_REPORT.md",
    f"{HANDOFF_REL}/REVIEW_REPORT.md",
)
_REPORT_NAMES = ("BUILD_REPORT.md", "REVIEW_REPORT.md")
PROTECTED_PATHS = (
    "apps/api/src/alicebot_api/vnext_stores/postgres/memory_access.py",
    "apps/api/src/alicebot_api/vnext_stores/sqlite/memory_access.py",
    "apps/web/package.json",
    "eval/longmemeval/data/longmemeval_s_cleaned.json",
    "eval/longmemeval/slices/dataset-manifest.json",
    "eval/longmemeval/slices/stage1-150.txt",
    "pyproject.toml",
)
Record = tuple[bytes, bytes, bytes]
RecordReader = Callable[[str], Record]


def _require_reports_on_disk() -> None:
    """Skip where the gitignored evidence reports were never checked out."""

    if not all((HANDOFF / name).is_file() for name in _REPORT_NAMES):
        pytest.skip("carrier evidence reports are gitignored and absent from this checkout")


def _git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ("git", "-C", str(ROOT), *arguments),
        check=check,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _base_history_available() -> bool:
    probe = _git("cat-file", "-e", f"{BASE}^{{commit}}", check=False)
    if probe.returncode == 0:
        return True
    shallow = _git("rev-parse", "--is-shallow-repository", check=False)
    assert shallow.returncode == 0 and shallow.stdout.strip() == b"true", (
        "Phase 6 base commit is missing from a checkout that is not verified shallow"
    )
    return False


def _require_full_git_history() -> None:
    if not _base_history_available():
        pytest.skip(
            "Phase 6 base commit unavailable in this verified shallow checkout; "
            "the full-history release workflow owns ancestry assertions"
        )


def _field(name: bytes, value: bytes) -> bytes:
    return name + b"\0" + len(value).to_bytes(8, "big") + value


def _base_mode(relative_path: str) -> bytes:
    entry = _git("ls-tree", "-z", BASE, "--", relative_path).stdout
    assert entry, relative_path
    return entry.split(b" ", 1)[0]


def _read_live_record(
    relative_path: str,
    *,
    root: Path = ROOT,
    base_mode_reader: Callable[[str], bytes] = _base_mode,
) -> Record:
    parts = relative_path.encode("utf-8").split(b"/")
    assert parts and all(part not in {b"", b".", b".."} for part in parts)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    assert nofollow is not None and directory is not None
    try:
        parent_fd = os.open(root, os.O_RDONLY | directory | nofollow)
    except OSError as exc:
        raise AssertionError(f"unsafe carrier root: {root}") from exc
    try:
        for component in parts[:-1]:
            try:
                component_info = os.stat(
                    component,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                return base_mode_reader(relative_path), b"deleted", b""
            assert stat.S_ISDIR(component_info.st_mode), f"unsafe carrier parent component: {relative_path}"
            try:
                child_fd = os.open(
                    component,
                    os.O_RDONLY | directory | nofollow,
                    dir_fd=parent_fd,
                )
            except OSError as exc:
                raise AssertionError(f"carrier parent changed during receipt: {relative_path}") from exc
            child_info = os.fstat(child_fd)
            try:
                assert stat.S_ISDIR(child_info.st_mode)
                assert (component_info.st_dev, component_info.st_ino) == (
                    child_info.st_dev,
                    child_info.st_ino,
                ), f"carrier parent changed during receipt: {relative_path}"
            except BaseException:
                os.close(child_fd)
                raise
            os.close(parent_fd)
            parent_fd = child_fd

        file_name = parts[-1]
        try:
            info = os.stat(file_name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return base_mode_reader(relative_path), b"deleted", b""
        if stat.S_ISLNK(info.st_mode):
            target = os.readlink(file_name, dir_fd=parent_fd)
            return b"120000", b"symlink", (target if isinstance(target, bytes) else os.fsencode(target))
        assert stat.S_ISREG(info.st_mode), f"unsupported carrier entry type: {relative_path}"
        try:
            descriptor = os.open(
                file_name,
                os.O_RDONLY | nofollow,
                dir_fd=parent_fd,
            )
        except OSError as exc:
            raise AssertionError(f"carrier entry changed during receipt: {relative_path}") from exc
        try:
            before = os.fstat(descriptor)
            assert stat.S_ISREG(before.st_mode)
            assert (info.st_dev, info.st_ino) == (before.st_dev, before.st_ino), (
                f"carrier entry changed during receipt: {relative_path}"
            )
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        stable = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        assert all(getattr(before, key) == getattr(after, key) for key in stable), relative_path
        mode = b"100755" if before.st_mode & stat.S_IXUSR else b"100644"
        return mode, b"regular", b"".join(chunks)
    finally:
        os.close(parent_fd)


def _read_commit_record(commit: str, relative_path: str) -> Record:
    entry = _git("ls-tree", "-z", commit, "--", relative_path).stdout
    if not entry:
        return _base_mode(relative_path), b"deleted", b""
    metadata, actual_path = entry.rstrip(b"\0").split(b"\t", 1)
    mode, object_type, _object_id = metadata.split(b" ", 2)
    assert object_type == b"blob" and actual_path.decode() == relative_path
    payload = _git("show", f"{commit}:{relative_path}").stdout
    return mode, b"symlink" if mode == b"120000" else b"regular", payload


def _build_receipt(reader: RecordReader) -> bytes:
    output = bytearray(
        b"".join(
            (
                _field(b"format", FORMAT.encode()),
                _field(b"base", BASE.encode()),
                _field(b"base_tree", BASE_TREE.encode()),
            )
        )
    )
    for relative_path in CARRIER_PATHS:
        mode, kind, payload = reader(relative_path)
        output.extend(_field(b"path", relative_path.encode()))
        output.extend(_field(b"mode", mode))
        output.extend(_field(b"kind", kind))
        output.extend(_field(b"sha256", hashlib.sha256(payload).hexdigest().encode()))
    return bytes(output)


def build_live_receipt() -> bytes:
    return _build_receipt(_read_live_record)


def _receipt_from_report(text: str) -> str:
    match = re.search(r"carrier receipt sha256:\s*`([0-9a-f]{64})`", text)
    assert match is not None, "BUILD_REPORT.md lacks the frozen carrier receipt"
    return match.group(1)


def _receipt_bytes_from_report(text: str) -> int:
    match = re.search(r"serialized receipt bytes:\s*`([1-9][0-9]*)`", text)
    assert match is not None, "BUILD_REPORT.md lacks the receipt byte length"
    return int(match.group(1))


def _carrier_paths_from_report(text: str) -> tuple[str, ...]:
    match = re.search(
        rf"Receipt-listed paths \({len(CARRIER_PATHS)}, bytewise sorted\):"
        r"\n\n```text\n(.*?)\n```",
        text,
        flags=re.DOTALL,
    )
    assert match is not None, "BUILD_REPORT.md lacks the explicit carrier path list"
    return tuple(match.group(1).splitlines())


def _live_dirty_paths() -> set[str]:
    changed = _git("diff", "--name-only", "-z", BASE, "--").stdout.split(b"\0")
    untracked = _git(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    ).stdout.split(b"\0")
    result = {path.decode("utf-8", errors="surrogateescape") for path in (*changed, *untracked) if path}
    # The two report filenames are intentionally ignored repository-wide so
    # builders cannot accidentally add stale reports. They are explicit,
    # existence-checked exclusions and release engineering must force-add the
    # final reviewed versions when integrating the carrier.
    result.update(path for path in RECEIPT_EXCLUSIONS if (ROOT / path).is_file())
    return result


def _worktree_delta_paths() -> set[str]:
    changed = _git("diff", "--name-only", "-z", "HEAD", "--").stdout.split(b"\0")
    untracked = _git(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    ).stdout.split(b"\0")
    return {path.decode("utf-8", errors="surrogateescape") for path in (*changed, *untracked) if path}


def _historical_handoff_delta_paths(paths: set[str]) -> set[str]:
    prefix = f"{HANDOFF_REL}/"
    return {path for path in paths if path == HANDOFF_REL or path.startswith(prefix)}


def _carrier_commit(receipt: str) -> str | None:
    commits = _git(
        "log",
        "--format=%H",
        "--fixed-strings",
        f"--grep=Alice-Carrier-Receipt-SHA256: {receipt}",
        "HEAD",
        check=False,
    )
    if commits.returncode != 0:
        return None
    matches = commits.stdout.decode().split()
    assert len(matches) <= 1, f"duplicate carrier receipt commits: {matches}"
    return matches[0] if matches else None


def _assert_carrier_directly_descends_from_base(carrier: str) -> None:
    carrier_line = _git("rev-list", "--parents", "-n", "1", carrier).stdout.decode().split()
    assert carrier_line == [carrier, BASE], "the Phase 6 carrier must be one fresh commit directly on its recorded base"


def _assert_commit_report_receipts(commit: str, receipt: str) -> None:
    message = _git("show", "-s", "--format=%B", commit).stdout.decode()
    assert f"Alice-Carrier-Receipt-SHA256: {receipt}" in message
    for filename, trailer in (
        ("BUILD_REPORT.md", "Alice-Build-Report-SHA256"),
        ("REVIEW_REPORT.md", "Alice-Review-Report-SHA256"),
    ):
        # These two reports are deliberately gitignored local evidence and are
        # never tracked: tracking them would make them tracked-and-ignored,
        # which the released single-tenant deployment contract forbids. Their
        # bytes are pinned by the commit trailer instead, so hash what is on
        # disk. A checkout without them, such as a fresh CI clone, has nothing
        # to compare and is not evidence of tampering.
        report_path = HANDOFF / filename
        if not report_path.is_file():
            continue
        expected = hashlib.sha256(report_path.read_bytes()).hexdigest()
        assert f"{trailer}: {expected}" in message


def _assert_integrated_handoff_immutable(
    carrier: str,
    *,
    head: str = "HEAD",
) -> None:
    handoff_diff = _git(
        "diff",
        "--quiet",
        carrier,
        head,
        "--",
        HANDOFF_REL,
        check=False,
    )
    assert handoff_diff.returncode == 0, "the integrated Phase 6 handoff changed after its receipt-trailed commit"


def _assert_protected_scope_immutable(commit: str) -> None:
    protected = _git(
        "diff",
        "--quiet",
        BASE,
        commit,
        "--",
        *PROTECTED_PATHS,
        "docs/release",
        check=False,
    )
    assert protected.returncode == 0, "a protected Phase 6 input or release record changed"
    handoff_changes = _git("diff", "--name-only", BASE, commit, "--", "docs/handoff").stdout.decode().splitlines()
    assert all(path.startswith(f"{HANDOFF_REL}/") for path in handoff_changes), (
        "a prior handoff package changed during Phase 6"
    )


def _is_ignored(relative_path: str) -> bool:
    result = _git("check-ignore", "--no-index", "--quiet", relative_path, check=False)
    assert result.returncode in {0, 1}, result.stderr
    return result.returncode == 0


def test_phase6_handoff_package_and_verdict_boundaries() -> None:
    tracked_names = {
        "README.md",
        "DESIGN.md",
        "FIX_MATRIX.md",
        "ENGINEER_HANDOFF.md",
    }
    # BUILD_REPORT.md and REVIEW_REPORT.md are gitignored local evidence pinned
    # by the carrier commit trailers, so a checkout that never carried them,
    # such as CI, legitimately has only the tracked four.
    present_reports = {name for name in _REPORT_NAMES if (HANDOFF / name).is_file()}
    assert {path.name for path in HANDOFF.iterdir()} == tracked_names | present_reports
    documents = {
        name: (HANDOFF / name).read_text(encoding="utf-8") for name in sorted(tracked_names | present_reports)
    }
    if "REVIEW_REPORT.md" in documents:
        review = " ".join(documents["REVIEW_REPORT.md"].split())
        assert "Code carrier" in review
        assert "Phase 6" in review and "NO-GO" in review
        assert "Release" in review and "NO-GO" in review
    for name, text in documents.items():
        normalized = " ".join(text.split())
        assert "Phase 6" in normalized, name
        assert "NO-GO" in normalized, name
        assert "0/14" in normalized, name
        assert "8/14" in normalized, name
        assert "172" in normalized, name
        assert "328" in normalized, name
        assert "0.14.0" in normalized, name
        assert "bf659f65" in normalized, name


def test_phase6_truth_docs_pin_the_subtle_contract_boundaries() -> None:
    _require_reports_on_disk()
    design = (HANDOFF / "DESIGN.md").read_text(encoding="utf-8")
    build = (HANDOFF / "BUILD_REPORT.md").read_text(encoding="utf-8")
    engineer = (HANDOFF / "ENGINEER_HANDOFF.md").read_text(encoding="utf-8")
    combined = "\n".join((design, build, engineer))
    assert "complete_with_unresolved_claims" in combined
    assert "matching-or-unknown" in combined
    assert "entire current live source corpus" in combined
    assert "signed exact zero" in combined
    assert "predicate is separately signed" in combined
    assert "event/reference clock" in combined
    assert "lifecycle clock" in combined
    assert "no operator-visible" in combined
    assert "observability" in combined
    assert "Do **not** deploy or apply migration 0095" in engineer


def test_phase6_versions_protected_inputs_and_prior_records_are_unchanged() -> None:
    python_version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    web_version = json.loads((ROOT / "apps/web/package.json").read_text(encoding="utf-8"))["version"]
    assert python_version == web_version == "0.14.0"
    assert all(path not in CARRIER_PATHS for path in PROTECTED_PATHS)
    assert all(not path.startswith("docs/release/") for path in CARRIER_PATHS)
    assert _git("diff", "--quiet", "HEAD", "--", *PROTECTED_PATHS).returncode == 0
    assert _git("diff", "--quiet", "HEAD", "--", "docs/release").returncode == 0
    prior_handoff_changes = {
        path
        for path in _worktree_delta_paths()
        if path.startswith("docs/handoff/") and not path.startswith(f"{HANDOFF_REL}/")
    }
    assert prior_handoff_changes == set()


def test_phase6_base_tree_is_bound_to_the_carrier() -> None:
    _require_full_git_history()
    assert _git("rev-parse", f"{BASE}^{{tree}}").stdout.decode().strip() == BASE_TREE
    python_at_base = tomllib.loads(_git("show", f"{BASE}:pyproject.toml").stdout.decode())["project"]["version"]
    web_at_base = json.loads(_git("show", f"{BASE}:apps/web/package.json").stdout.decode())["version"]
    assert python_at_base == web_at_base == "0.14.0"


def test_phase6_receipt_exclusions_and_path_manifest_are_exact() -> None:
    assert RECEIPT_EXCLUSIONS == (
        f"{HANDOFF_REL}/BUILD_REPORT.md",
        f"{HANDOFF_REL}/REVIEW_REPORT.md",
    )
    assert all(_is_ignored(path) for path in RECEIPT_EXCLUSIONS)
    assert tuple(sorted(CARRIER_PATHS, key=lambda value: value.encode())) == CARRIER_PATHS
    assert len(CARRIER_PATHS) == 71
    # The manifest cross-check needs the gitignored report, which a fresh
    # checkout never carried. The path-list assertions above still run.
    _require_reports_on_disk()
    report = (HANDOFF / "BUILD_REPORT.md").read_text(encoding="utf-8")
    assert _carrier_paths_from_report(report) == CARRIER_PATHS


def test_phase6_live_carrier_scope_and_receipt() -> None:
    _require_reports_on_disk()
    head = _git("rev-parse", "HEAD").stdout.decode().strip()
    report = (HANDOFF / "BUILD_REPORT.md").read_text(encoding="utf-8")
    receipt = _receipt_from_report(report)
    if head == BASE:
        assert _git("branch", "--show-current").stdout.decode().strip() == BRANCH
        assert _git("diff", "--cached", "--quiet").returncode == 0
        expected_paths = set(CARRIER_PATHS) | set(RECEIPT_EXCLUSIONS)
        assert _live_dirty_paths() == expected_paths
        serialized = build_live_receipt()
        assert len(serialized) == _receipt_bytes_from_report(report)
        assert hashlib.sha256(serialized).hexdigest() == receipt
        return

    handoff_delta = _historical_handoff_delta_paths(_worktree_delta_paths())
    assert not handoff_delta, f"integrated checkout has live Phase 6 handoff drift: {sorted(handoff_delta)}"
    message = _git("show", "-s", "--format=%B", "HEAD").stdout.decode()
    if f"Alice-Carrier-Receipt-SHA256: {receipt}" not in message:
        pytest.skip("carrier is integrated; full-history receipt test owns ancestry")
    serialized = _build_receipt(lambda path: _read_commit_record("HEAD", path))
    assert len(serialized) == _receipt_bytes_from_report(report)
    assert hashlib.sha256(serialized).hexdigest() == receipt
    _assert_commit_report_receipts("HEAD", receipt)


def test_phase6_integrated_carrier_is_ancestry_and_content_bound() -> None:
    _require_reports_on_disk()
    head = _git("rev-parse", "HEAD").stdout.decode().strip()
    if head == BASE:
        pytest.skip("uncommitted carrier: live receipt test is authoritative")
    _require_full_git_history()

    report = (HANDOFF / "BUILD_REPORT.md").read_text(encoding="utf-8")
    receipt = _receipt_from_report(report)
    carrier = _carrier_commit(receipt)
    assert carrier is not None
    _assert_carrier_directly_descends_from_base(carrier)
    assert (
        _git(
            "merge-base",
            "--is-ancestor",
            BASE,
            carrier,
            check=False,
        ).returncode
        == 0
    )
    assert (
        _git(
            "merge-base",
            "--is-ancestor",
            carrier,
            "HEAD",
            check=False,
        ).returncode
        == 0
    )
    changed = set(_git("diff", "--name-only", BASE, carrier, "--").stdout.decode().splitlines())
    # The receipt exclusions are gitignored local evidence and are never
    # tracked, so the carrier commit changes exactly the receipt-listed paths.
    assert changed == set(CARRIER_PATHS)
    serialized = _build_receipt(lambda path: _read_commit_record(carrier, path))
    assert len(serialized) == _receipt_bytes_from_report(report)
    assert hashlib.sha256(serialized).hexdigest() == receipt
    _assert_commit_report_receipts(carrier, receipt)
    _assert_protected_scope_immutable(carrier)
    _assert_integrated_handoff_immutable(carrier)


def test_phase6_receipt_records_fail_on_old_bytes_modes_deletions_and_symlinks(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "carrier.txt"
    candidate.write_bytes(b"first\n")
    base_mode_reader = lambda _path: b"100644"
    first = _read_live_record(
        "carrier.txt",
        root=tmp_path,
        base_mode_reader=base_mode_reader,
    )
    candidate.write_bytes(b"second\n")
    second = _read_live_record(
        "carrier.txt",
        root=tmp_path,
        base_mode_reader=base_mode_reader,
    )
    assert first != second

    candidate.chmod(0o755)
    executable = _read_live_record(
        "carrier.txt",
        root=tmp_path,
        base_mode_reader=base_mode_reader,
    )
    assert executable[0] == b"100755" and executable != second

    candidate.unlink()
    os.symlink("target-that-is-never-followed", candidate)
    linked = _read_live_record(
        "carrier.txt",
        root=tmp_path,
        base_mode_reader=base_mode_reader,
    )
    assert linked == (b"120000", b"symlink", b"target-that-is-never-followed")

    candidate.unlink()
    deleted = _read_live_record(
        "carrier.txt",
        root=tmp_path,
        base_mode_reader=base_mode_reader,
    )
    assert deleted == (b"100644", b"deleted", b"")

    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    (real_parent / "nested.txt").write_text("payload\n", encoding="utf-8")
    os.symlink("real-parent", tmp_path / "linked-parent", target_is_directory=True)
    with pytest.raises(AssertionError, match="unsafe carrier parent component"):
        _read_live_record(
            "linked-parent/nested.txt",
            root=tmp_path,
            base_mode_reader=base_mode_reader,
        )


def test_phase6_integrated_handoff_rejects_post_carrier_drift(monkeypatch) -> None:
    observed: list[tuple[str, ...]] = []

    def fake_git(
        *arguments: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        observed.append(arguments)
        return subprocess.CompletedProcess(arguments, 1, b"", b"")

    monkeypatch.setattr(f"{__name__}._git", fake_git)
    with pytest.raises(AssertionError, match="handoff changed"):
        _assert_integrated_handoff_immutable("carrier-commit")
    assert observed == [("diff", "--quiet", "carrier-commit", "HEAD", "--", HANDOFF_REL)]


def test_phase6_integrated_carrier_rejects_a_child_of_an_old_carrier(
    monkeypatch,
) -> None:
    def fake_git(
        *arguments: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        del check
        assert arguments == ("rev-list", "--parents", "-n", "1", "replacement")
        return subprocess.CompletedProcess(
            arguments,
            0,
            b"replacement old-carrier\n",
            b"",
        )

    monkeypatch.setattr(f"{__name__}._git", fake_git)
    with pytest.raises(AssertionError, match="fresh commit directly"):
        _assert_carrier_directly_descends_from_base("replacement")
