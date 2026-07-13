from __future__ import annotations

from pathlib import Path

import pytest

import scripts.check_control_doc_truth as control_doc_truth


def _checksum_manifest(version: str, digit: str = "0") -> str:
    return (
        digit * 64 + f"  alice_memory-{version}-py3-none-any.whl\n"
        + digit * 64
        + f"  alice_memory-{version}.tar.gz\n"
    )


def _seed_truth_docs(tmp_path: Path, *, published: bool = False) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "alice-memory"\nversion = "9.8.7"\n',
        encoding="utf-8",
    )
    for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES:
        doc_path = tmp_path / rule.relative_path
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("\n".join(rule.required_markers) + "\n", encoding="utf-8")
    release_dir = tmp_path / "docs" / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    publication_status = "published" if published else "pending"
    checksums_status = "recorded" if published else "pending"
    (release_dir / "v9.8.7-release-notes.md").write_text(
        "# Alice v9.8.7 Release Notes\n"
        '<!-- alice-release-state: {"schema_version":"alice_release_document_state_v1",'
        '"version":"9.8.7",'
        f'"publication_status":"{publication_status}",'
        f'"checksums_status":"{checksums_status}"}} -->\n\nReady.\n',
        encoding="utf-8",
    )
    if published:
        (release_dir / "v9.8.7-checksums.txt").write_text(
            _checksum_manifest("9.8.7"),
            encoding="utf-8",
        )

    for rule in control_doc_truth.VERSION_ALIGNED_DOC_RULES:
        doc_path = tmp_path / rule.relative_path
        with doc_path.open("a", encoding="utf-8") as handle:
            if published:
                if rule.relative_path == "docs/integrations/reference-paths.md":
                    handle.write("latest published `v9.8.7` baseline\n")
                elif rule.relative_path == "docs/alpha/headless-ubuntu-install.md":
                    handle.write("latest published release tag\n(`v9.8.7`)\n")
                else:
                    handle.write("`v9.8.7` is the latest published release\n")
                if rule.relative_path.endswith("CURRENT_STATE.md"):
                    handle.write("## What `v9.8.7` Shipped\n")
            else:
                handle.write("`v9.8.7` is the current release-hardening candidate\n")
                if rule.relative_path.endswith("CURRENT_STATE.md"):
                    handle.write("## What `v9.8.7` Targets\n")


def test_control_doc_truth_passes_with_required_markers() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=repo_root)

    assert issues == []


def test_control_doc_truth_accepts_published_state_and_markers(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path, published=True)

    assert control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path) == []


def test_control_doc_truth_fails_when_required_marker_is_missing(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    first_rule = control_doc_truth.CONTROL_DOC_TRUTH_RULES[0]
    first_doc_path = tmp_path / first_rule.relative_path
    first_doc_path.write_text("missing required baseline marker\n", encoding="utf-8")

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue == f"{first_rule.relative_path}: missing required marker '{first_rule.required_markers[0]}'"
        for issue in issues
    )


def test_control_doc_truth_fails_when_disallowed_marker_is_present(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    target_rule = next(
        rule
        for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES
        if rule.relative_path == "ROADMAP.md"
    )
    target_path = tmp_path / target_rule.relative_path
    target_path.write_text(
        target_path.read_text(encoding="utf-8")
        + "\nGate ownership is canonicalized to Phase 4 runner scripts.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue == f"{target_rule.relative_path}: contains disallowed marker 'Gate ownership is canonicalized to Phase 4 runner scripts'"
        for issue in issues
    )


def test_control_doc_truth_fails_when_archive_index_is_missing(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    archive_rule = next(
        rule
        for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES
        if rule.relative_path == "docs/archive/planning/2026-04-08-context-compaction/README.md"
    )
    (tmp_path / archive_rule.relative_path).unlink()

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(issue == f"{archive_rule.relative_path}: missing file" for issue in issues)


def test_control_doc_truth_fails_when_stale_legacy_marker_is_present(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    target_rule = next(
        rule
        for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES
        if rule.relative_path == "README.md"
    )
    target_path = tmp_path / target_rule.relative_path
    target_path.write_text(
        target_path.read_text(encoding="utf-8") + "\nLegacy Compatibility Markers still apply here.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue == f"{target_rule.relative_path}: contains disallowed marker 'Legacy Compatibility Markers'"
        for issue in issues
    )


def test_control_doc_truth_fails_when_release_version_is_stale(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    target = tmp_path / "CURRENT_STATE.md"
    target.write_text(
        target.read_text(encoding="utf-8").replace(
            "`v9.8.7` is the current release-hardening candidate",
            "`v9.8.6` is the current release-hardening candidate",
        ),
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue.startswith("CURRENT_STATE.md: missing current-version candidate marker")
        for issue in issues
    )


def test_candidate_mode_rejects_stale_latest_published_claim(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    release_dir = tmp_path / "docs" / "release"
    (release_dir / "v9.8.6-release-notes.md").write_text(
        "# Alice v9.8.6 Release Notes\n"
        '<!-- alice-release-state: {"schema_version":"alice_release_document_state_v1",'
        '"version":"9.8.6","publication_status":"published",'
        '"checksums_status":"recorded"} -->\n',
        encoding="utf-8",
    )
    (release_dir / "v9.8.6-checksums.txt").write_text(
        _checksum_manifest("9.8.6", "1"),
        encoding="utf-8",
    )
    target = tmp_path / "PRODUCT_BRIEF.md"
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n`v9.8.5` is the latest published release.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue
        == "PRODUCT_BRIEF.md: names v9.8.5 as latest published instead of v9.8.6"
        for issue in issues
    )


@pytest.mark.parametrize(
    ("schema_version", "with_checksums"),
    (
        ("alice_release_document_state_v0", True),
        ("alice_release_document_state_v1", False),
    ),
)
def test_candidate_mode_rejects_latest_published_history_without_valid_evidence(
    tmp_path: Path, schema_version: str, with_checksums: bool
) -> None:
    _seed_truth_docs(tmp_path)
    release_dir = tmp_path / "docs" / "release"
    (release_dir / "v9.8.6-release-notes.md").write_text(
        "# Alice v9.8.6 Release Notes\n"
        f'<!-- alice-release-state: {{"schema_version":"{schema_version}",'
        '"version":"9.8.6","publication_status":"published",'
        '"checksums_status":"recorded"} -->\n',
        encoding="utf-8",
    )
    if with_checksums:
        (release_dir / "v9.8.6-checksums.txt").write_text(
            "2" * 64 + "  alice_memory-9.8.6.tar.gz\n",
            encoding="utf-8",
        )
    target = tmp_path / "PRODUCT_BRIEF.md"
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n`v9.8.6` is the latest published release.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert (
        "PRODUCT_BRIEF.md: names v9.8.6 as latest published without a structured "
        "published release record"
    ) in issues


@pytest.mark.parametrize(
    "stale_claim",
    (
        "The latest published\nrelease is `v9.8.5`.",
        "`v9.8.5` remains the latest\npublished release.",
    ),
)
def test_candidate_mode_rejects_multiline_stale_latest_published_claim(
    tmp_path: Path, stale_claim: str
) -> None:
    _seed_truth_docs(tmp_path)
    release_dir = tmp_path / "docs" / "release"
    (release_dir / "v9.8.6-release-notes.md").write_text(
        "# Alice v9.8.6 Release Notes\n"
        '<!-- alice-release-state: {"schema_version":"alice_release_document_state_v1",'
        '"version":"9.8.6","publication_status":"published",'
        '"checksums_status":"recorded"} -->\n',
        encoding="utf-8",
    )
    (release_dir / "v9.8.6-checksums.txt").write_text(
        _checksum_manifest("9.8.6", "3"),
        encoding="utf-8",
    )
    target = tmp_path / "PRODUCT_BRIEF.md"
    target.write_text(
        target.read_text(encoding="utf-8") + f"\n{stale_claim}\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert (
        "PRODUCT_BRIEF.md: names v9.8.5 as latest published instead of v9.8.6"
    ) in issues


def test_control_doc_truth_rejects_empty_checksum_receipt_after_publication(
    tmp_path: Path,
) -> None:
    _seed_truth_docs(tmp_path, published=True)
    (tmp_path / "docs" / "release" / "v9.8.7-checksums.txt").write_text(
        "# no artifact records\n", encoding="utf-8"
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert (
        "docs/release/v9.8.7-checksums.txt: must contain exactly the canonical wheel and sdist SHA-256 records"
    ) in issues


@pytest.mark.parametrize(
    "manifest",
    (
        "4" * 64 + "  unrelated-package.zip\n",
        "5" * 64 + "  alice_memory-9.8.7.tar.gz\n",
        _checksum_manifest("9.8.7") + "6" * 64 + "  unrelated-package.zip\n",
        _checksum_manifest("9.8.7")
        + "7" * 64
        + "  alice_memory-9.8.7.tar.gz\n",
    ),
)
def test_control_doc_truth_rejects_noncanonical_checksum_receipts(
    tmp_path: Path, manifest: str
) -> None:
    _seed_truth_docs(tmp_path, published=True)
    (tmp_path / "docs" / "release" / "v9.8.7-checksums.txt").write_text(
        manifest, encoding="utf-8"
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("must contain exactly the canonical wheel and sdist" in issue for issue in issues)


def test_candidate_mode_ignores_historical_state_with_extra_keys(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    release_dir = tmp_path / "docs" / "release"
    (release_dir / "v9.8.6-release-notes.md").write_text(
        "# Alice v9.8.6 Release Notes\n"
        '<!-- alice-release-state: {"schema_version":"alice_release_document_state_v1",'
        '"version":"9.8.6","publication_status":"published",'
        '"checksums_status":"recorded","unexpected":true} -->\n',
        encoding="utf-8",
    )
    (release_dir / "v9.8.6-checksums.txt").write_text(
        _checksum_manifest("9.8.6", "8"), encoding="utf-8"
    )
    target = tmp_path / "PRODUCT_BRIEF.md"
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n`v9.8.6` is the latest published release.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert (
        "PRODUCT_BRIEF.md: names v9.8.6 as latest published without a structured "
        "published release record"
    ) in issues


@pytest.mark.parametrize("published", (False, True))
def test_control_doc_truth_rejects_extra_release_state_keys(
    tmp_path: Path, published: bool
) -> None:
    _seed_truth_docs(tmp_path, published=published)
    notes = tmp_path / "docs" / "release" / "v9.8.7-release-notes.md"
    notes.write_text(
        notes.read_text(encoding="utf-8").replace(
            '"version":"9.8.7",', '"version":"9.8.7","unexpected":true,'
        ),
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("must contain exactly the supported keys" in issue for issue in issues)


@pytest.mark.parametrize(
    ("relative_path", "stale_text"),
    (
        ("CHANGELOG.md", "the v0.10.0 matrix is the current closure record"),
        (
            "docs/release/v0.9.4-release-notes.md",
            "The v0.10.0 remediation cycle tracks unfinished work.",
        ),
    ),
)
def test_control_doc_truth_rejects_stale_historical_closure_wording(
    tmp_path: Path, relative_path: str, stale_text: str
) -> None:
    _seed_truth_docs(tmp_path)
    target = tmp_path / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(stale_text + "\n", encoding="utf-8")

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue
        == f"{relative_path}: contains stale present-tense v0.10.0 closure wording"
        for issue in issues
    )


@pytest.mark.parametrize(
    ("relative_path", "contradiction"),
    (
        (
            "CURRENT_STATE.md",
            "The cycle resumes feature work and clears the second audit's P2 backlog.",
        ),
        (
            "ARCHITECTURE.md",
            "The candidate resumes feature work and clears the second audit's P2 backlog.",
        ),
        (
            "RELEASING.md",
            "The semantic attestation replaces the repository-control attestation.",
        ),
    ),
)
def test_control_doc_truth_rejects_known_release_contradictions(
    tmp_path: Path,
    relative_path: str,
    contradiction: str,
) -> None:
    _seed_truth_docs(tmp_path)
    target = tmp_path / relative_path
    target.write_text(
        target.read_text(encoding="utf-8") + f"\n{contradiction}\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(issue.startswith(f"{relative_path}: contains disallowed marker") for issue in issues)


def test_control_doc_truth_requires_repository_control_attestation_contract(
    tmp_path: Path,
) -> None:
    _seed_truth_docs(tmp_path)
    target_rule = next(
        rule for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES if rule.relative_path == "RELEASING.md"
    )
    target = tmp_path / target_rule.relative_path
    target.write_text(
        target.read_text(encoding="utf-8").replace("ALICE_RELEASE_CONTROLS_ATTESTATION", "removed-control-variable"),
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue == ("RELEASING.md: missing required marker 'ALICE_RELEASE_CONTROLS_ATTESTATION'") for issue in issues
    )


def test_control_doc_truth_rejects_candidate_claim_after_publication(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path, published=True)
    target = tmp_path / "PRODUCT_BRIEF.md"
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n`v9.8.7` is still an unpublished candidate.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("describes published v9.8.7" in issue for issue in issues)


@pytest.mark.parametrize(
    "contradiction",
    (
        "`v9.8.7` remains\nan unpublished candidate.",
        "This unpublished candidate\nis `v9.8.7`.",
        "`v9.8.7` is not\tpublished.",
    ),
)
def test_control_doc_truth_rejects_multiline_candidate_claim_after_publication(
    tmp_path: Path, contradiction: str
) -> None:
    _seed_truth_docs(tmp_path, published=True)
    target = tmp_path / "PRODUCT_BRIEF.md"
    target.write_text(
        target.read_text(encoding="utf-8") + f"\n{contradiction}\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("describes published v9.8.7" in issue for issue in issues)


def test_control_doc_truth_requires_checksum_receipt_after_publication(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path, published=True)
    (tmp_path / "docs" / "release" / "v9.8.7-checksums.txt").unlink()

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("missing for recorded publication" in issue for issue in issues)


def test_control_doc_truth_requires_exact_current_state_mirror(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    mirror = tmp_path / ".ai" / "handoff" / "CURRENT_STATE.md"
    mirror.write_text(mirror.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("must exactly mirror CURRENT_STATE.md" in issue for issue in issues)
