from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

import scripts.check_control_doc_truth as control_doc_truth


def _checksum_manifest(version: str, digit: str = "0") -> str:
    return (
        digit * 64 + f"  alice_memory-{version}-py3-none-any.whl\n" + digit * 64 + f"  alice_memory-{version}.tar.gz\n"
    )


def _seed_truth_docs(tmp_path: Path, *, published: bool = False) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "alice-memory"\nversion = "9.8.7"\nreadme = "docs/pypi-description.md"\n',
        encoding="utf-8",
    )
    description = tmp_path / control_doc_truth.PACKAGE_DESCRIPTION_RELATIVE_PATH
    description.parent.mkdir(parents=True, exist_ok=True)
    description.write_text(
        "# Alice Memory\n\nEvergreen package description.\n",
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

    if published:
        for relative_path in ("README.md", "docs/vnext/README.md"):
            target = tmp_path / relative_path
            target.write_text(
                target.read_text(encoding="utf-8") + "\n[Release notes](docs/release/v9.8.7-release-notes.md)\n",
                encoding="utf-8",
            )
        for relative_path in ("ARCHITECTURE.md", "PRODUCT_BRIEF.md", "ROADMAP.md"):
            target = tmp_path / relative_path
            target.write_text(
                target.read_text(encoding="utf-8") + "\ndocs/release/v9.8.7-checksums.txt\n",
                encoding="utf-8",
            )
        for relative_path in ("CURRENT_STATE.md", ".ai/handoff/CURRENT_STATE.md"):
            target = tmp_path / relative_path
            target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "## Release Boundary\n",
                    "## Release Boundary\ndocs/release/v9.8.7-checksums.txt\n",
                ),
                encoding="utf-8",
            )
        install = tmp_path / "docs" / "alpha" / "headless-ubuntu-install.md"
        install.write_text(
            install.read_text(encoding="utf-8") + "\nUse --tag v9.8.7.\n",
            encoding="utf-8",
        )


def test_control_doc_truth_passes_with_required_markers() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=repo_root)

    assert issues == []


def test_release_gate_requires_fresh_isolated_artifact_directories() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    releasing = (repo_root / "RELEASING.md").read_text(encoding="utf-8")
    engineer_handoff = (repo_root / "docs/handoff/2026-07-14-v0.10.4-remediation/ENGINEER_HANDOFF.md").read_text(
        encoding="utf-8"
    )
    build_report = (repo_root / "docs/handoff/2026-07-14-v0.10.4-remediation/BUILD_REPORT.md").read_text(
        encoding="utf-8"
    )

    assert "make release-check DIST_DIR=dist" not in releasing
    assert "`dist/SHA256SUMS`" not in releasing
    for document in (releasing, engineer_handoff):
        for marker in (
            'release_run_root="$(mktemp -d /tmp/alice-release-check.XXXXXX)"',
            'DIST_DIR="$dist_dir"',
            'REPRO_DIST_DIR="$repro_dist_dir"',
            'test -z "$(find "$directory" -mindepth 1 -maxdepth 1 -print -quit)"',
        ):
            assert marker in document
    for marker in (
        "$DIST_DIR/SHA256SUMS",
        "never point either variable at user-owned artifact",
        "Run the gate without `-j`",
        "do not run `release-artifacts` separately first",
    ):
        assert marker in releasing
    for marker in (
        "Run without `-j`",
        "do not invoke that target separately",
        "never delete, overwrite, or rely on ignored historical",
    ):
        assert marker in engineer_handoff
    for marker in (
        "may have been refreshed by verification commands",
        "excluded from the tracked/untracked manifest and remediation",
        "not used as evidence",
    ):
        assert marker in build_report


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
    target_rule = next(rule for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES if rule.relative_path == "ROADMAP.md")
    target_path = tmp_path / target_rule.relative_path
    target_path.write_text(
        target_path.read_text(encoding="utf-8") + "\nGate ownership is canonicalized to Phase 4 runner scripts.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(
        issue
        == f"{target_rule.relative_path}: contains disallowed marker 'Gate ownership is canonicalized to Phase 4 runner scripts'"
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
    target_rule = next(rule for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES if rule.relative_path == "README.md")
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

    assert any(issue.startswith("CURRENT_STATE.md: missing current-version candidate marker") for issue in issues)


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
        target.read_text(encoding="utf-8") + "\n`v9.8.5` is the latest published release.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any(issue == "PRODUCT_BRIEF.md: names v9.8.5 as latest published instead of v9.8.6" for issue in issues)


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
        target.read_text(encoding="utf-8") + "\n`v9.8.6` is the latest published release.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert (
        "PRODUCT_BRIEF.md: names v9.8.6 as latest published without a structured published release record"
    ) in issues


@pytest.mark.parametrize(
    "stale_claim",
    (
        "The latest published\nrelease is `v9.8.5`.",
        "`v9.8.5` remains the latest\npublished release.",
    ),
)
def test_candidate_mode_rejects_multiline_stale_latest_published_claim(tmp_path: Path, stale_claim: str) -> None:
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

    assert ("PRODUCT_BRIEF.md: names v9.8.5 as latest published instead of v9.8.6") in issues


def test_control_doc_truth_rejects_empty_checksum_receipt_after_publication(
    tmp_path: Path,
) -> None:
    _seed_truth_docs(tmp_path, published=True)
    (tmp_path / "docs" / "release" / "v9.8.7-checksums.txt").write_text("# no artifact records\n", encoding="utf-8")

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
        _checksum_manifest("9.8.7") + "7" * 64 + "  alice_memory-9.8.7.tar.gz\n",
    ),
)
def test_control_doc_truth_rejects_noncanonical_checksum_receipts(tmp_path: Path, manifest: str) -> None:
    _seed_truth_docs(tmp_path, published=True)
    (tmp_path / "docs" / "release" / "v9.8.7-checksums.txt").write_text(manifest, encoding="utf-8")

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
    (release_dir / "v9.8.6-checksums.txt").write_text(_checksum_manifest("9.8.6", "8"), encoding="utf-8")
    target = tmp_path / "PRODUCT_BRIEF.md"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n`v9.8.6` is the latest published release.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert (
        "PRODUCT_BRIEF.md: names v9.8.6 as latest published without a structured published release record"
    ) in issues


@pytest.mark.parametrize("published", (False, True))
def test_control_doc_truth_rejects_extra_release_state_keys(tmp_path: Path, published: bool) -> None:
    _seed_truth_docs(tmp_path, published=published)
    notes = tmp_path / "docs" / "release" / "v9.8.7-release-notes.md"
    notes.write_text(
        notes.read_text(encoding="utf-8").replace('"version":"9.8.7",', '"version":"9.8.7","unexpected":true,'),
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

    assert any(issue == f"{relative_path}: contains stale present-tense v0.10.0 closure wording" for issue in issues)


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
        target.read_text(encoding="utf-8") + "\n`v9.8.7` is still an unpublished candidate.\n",
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


@pytest.mark.parametrize(
    "description",
    (
        "Alice v9.8.7 package description.\n",
        "Alice is the latest release.\n",
        "Alice is a release-gating candidate.\n",
    ),
)
def test_control_doc_truth_rejects_mutable_package_description_language(
    tmp_path: Path,
    description: str,
) -> None:
    _seed_truth_docs(tmp_path)
    (tmp_path / control_doc_truth.PACKAGE_DESCRIPTION_RELATIVE_PATH).write_text(
        description,
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("pypi-description.md" in issue for issue in issues)


def test_control_doc_truth_requires_evergreen_project_readme(tmp_path: Path) -> None:
    _seed_truth_docs(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('readme = "docs/pypi-description.md"', 'readme = "README.md"'),
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("project.readme must point" in issue for issue in issues)


def test_control_doc_truth_aligns_latest_notes_and_checksum_pointers(
    tmp_path: Path,
) -> None:
    _seed_truth_docs(tmp_path, published=True)
    readme = tmp_path / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("v9.8.7-release-notes.md", "v9.8.6-release-notes.md"),
        encoding="utf-8",
    )
    architecture = tmp_path / "ARCHITECTURE.md"
    architecture.write_text(
        architecture.read_text(encoding="utf-8").replace("v9.8.7-checksums.txt", "v9.8.6-checksums.txt"),
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("latest release-notes link" in issue for issue in issues)
    assert any("ARCHITECTURE.md: published checksum pointer" in issue for issue in issues)


def test_control_doc_truth_aligns_release_boundary_and_install_tag(
    tmp_path: Path,
) -> None:
    _seed_truth_docs(tmp_path, published=True)
    for relative_path in ("CURRENT_STATE.md", ".ai/handoff/CURRENT_STATE.md"):
        target = tmp_path / relative_path
        target.write_text(
            target.read_text(encoding="utf-8").replace("v9.8.7-checksums.txt", "v9.8.6-checksums.txt"),
            encoding="utf-8",
        )
    install = tmp_path / "docs" / "alpha" / "headless-ubuntu-install.md"
    install.write_text(
        install.read_text(encoding="utf-8").replace("--tag v9.8.7", "--tag v9.8.6"),
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("Release Boundary checksum pointer" in issue for issue in issues)
    assert any("literal install tag v9.8.6" in issue for issue in issues)


def test_control_doc_truth_rejects_future_state_in_new_published_notes(
    tmp_path: Path,
) -> None:
    _seed_truth_docs(tmp_path, published=True)
    notes = tmp_path / "docs" / "release" / "v9.8.7-release-notes.md"
    notes.write_text(
        notes.read_text(encoding="utf-8") + "\nArtifact digests will be recorded after publication.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert any("published notes contain future-state language" in issue for issue in issues)


def _seed_active_handoff_docs(tmp_path: Path, *, finalization: bool = True) -> Path:
    handoff_dir = tmp_path / control_doc_truth._ACTIVE_REMEDIATION_HANDOFF
    handoff_dir.mkdir(parents=True, exist_ok=True)
    for relative_path, markers in control_doc_truth._ACTIVE_REMEDIATION_MARKERS.items():
        finalization_markers = (
            control_doc_truth._ACTIVE_FINALIZATION_MARKERS.get(relative_path, ()) if finalization else ()
        )
        (handoff_dir / relative_path).write_text(
            "\n".join((*markers, *finalization_markers)),
            encoding="utf-8",
        )
    return handoff_dir


def _write_governed_versions(
    tmp_path: Path,
    *,
    python_version: str | None,
    web_version: str | None,
    include_readme: bool = False,
) -> None:
    python_lines = ["[project]", 'name = "alice-memory"']
    if python_version is not None:
        python_lines.append(f'version = "{python_version}"')
    if include_readme:
        python_lines.append('readme = "docs/pypi-description.md"')
    (tmp_path / "pyproject.toml").write_text("\n".join(python_lines) + "\n", encoding="utf-8")

    web_package = tmp_path / "apps/web/package.json"
    web_package.parent.mkdir(parents=True, exist_ok=True)
    version_field = f',"version":"{web_version}"' if web_version is not None else ""
    web_package.write_text(f'{{"name":"@alicebot/web"{version_field}}}\n', encoding="utf-8")


def test_control_doc_truth_requires_repair_batch_16_handoff_boundary(
    tmp_path: Path,
) -> None:
    handoff_dir = _seed_active_handoff_docs(tmp_path)

    engineer_handoff = handoff_dir / "ENGINEER_HANDOFF.md"
    engineer_handoff.write_text(
        engineer_handoff.read_text(encoding="utf-8").replace("- [x] continuity APIs", "- [ ] continuity APIs"),
        encoding="utf-8",
    )

    issues = control_doc_truth._validate_active_remediation_handoff(tmp_path)

    assert any("ENGINEER_HANDOFF.md" in issue and "continuity APIs" in issue for issue in issues)


def test_control_doc_truth_rejects_stale_batch_14_pending_freeze_claim(
    tmp_path: Path,
) -> None:
    handoff_dir = _seed_active_handoff_docs(tmp_path)

    readme = handoff_dir / "README.md"
    stale_marker = control_doc_truth._ACTIVE_REMEDIATION_FORBIDDEN_MARKERS["README.md"][0]
    readme.write_text(
        readme.read_text(encoding="utf-8") + f"\n{stale_marker}\n",
        encoding="utf-8",
    )

    issues = control_doc_truth._validate_active_remediation_handoff(tmp_path)

    assert any(
        issue
        == (
            f"{control_doc_truth._ACTIVE_REMEDIATION_HANDOFF}/README.md: "
            f"contains stale remediation marker {stale_marker!r}"
        )
        for issue in issues
    )


def test_control_doc_truth_rejects_stale_batch_15_current_pending_claim(
    tmp_path: Path,
) -> None:
    handoff_dir = _seed_active_handoff_docs(tmp_path)

    fix_matrix = handoff_dir / "FIX_MATRIX.md"
    stale_marker = control_doc_truth._ACTIVE_REMEDIATION_FORBIDDEN_MARKERS["FIX_MATRIX.md"][-1]
    fix_matrix.write_text(
        fix_matrix.read_text(encoding="utf-8")
        + "\nRepair Batch 15 is the current\n"
        + "bounded correction. The tree is builder-frozen; independent review remains **PENDING**.\n",
        encoding="utf-8",
    )

    issues = control_doc_truth._validate_active_remediation_handoff(tmp_path)

    assert any(
        issue
        == (
            f"{control_doc_truth._ACTIVE_REMEDIATION_HANDOFF}/FIX_MATRIX.md: "
            f"contains stale remediation marker {stale_marker!r}"
        )
        for issue in issues
    )


def _seed_finalized_active_handoff(tmp_path: Path) -> Path:
    _write_governed_versions(tmp_path, python_version="0.10.4", web_version="0.10.4")
    return _seed_active_handoff_docs(tmp_path)


def test_active_handoff_presence_requires_finalization_markers_before_version_alignment(tmp_path: Path) -> None:
    _write_governed_versions(tmp_path, python_version="0.10.3", web_version="0.10.3")
    _seed_active_handoff_docs(tmp_path, finalization=False)

    issues = control_doc_truth._validate_active_remediation_handoff(tmp_path)

    assert any("missing finalization truth marker" in issue for issue in issues)


@pytest.mark.parametrize(
    ("relative_path", "marker"),
    [
        ("README.md", "The tree is intentionally uncommitted. No version source was bumped"),
        ("BUILD_REPORT.md", "Package version intentionally remains `0.10.3` until release-engineer finalization"),
        (
            "ENGINEER_HANDOFF.md",
            "Before the finalization commit, bump every governed version source to `0.10.4`",
        ),
        ("FIX_MATRIX.md", "v0.10.4 as uncommitted remediation"),
        (
            "SURFACE_INVENTORY.md",
            "Version sources remain `0.10.3` during this uncommitted remediation",
        ),
    ],
)
def test_control_doc_truth_rejects_stale_finalization_claims_after_version_bump(
    tmp_path: Path,
    relative_path: str,
    marker: str,
) -> None:
    handoff_dir = _seed_finalized_active_handoff(tmp_path)
    target = handoff_dir / relative_path
    line_wrapped_marker = marker.replace(" ", "\n", 1)
    target.write_text(target.read_text(encoding="utf-8") + f"\n{line_wrapped_marker}\n", encoding="utf-8")

    issues = control_doc_truth._validate_active_remediation_handoff(tmp_path)

    assert any(
        issue
        == (
            f"{control_doc_truth._ACTIVE_REMEDIATION_HANDOFF}/{relative_path}: "
            f"contains stale finalization marker {marker!r}"
        )
        for issue in issues
    )


@pytest.mark.parametrize(
    ("python_version", "web_version"),
    (
        ("0.10.4", "0.10.3"),
        ("0.10.3", "0.10.4"),
        ("0.10.3", "0.10.3"),
        ("0.10.5", "0.10.5"),
        (None, "0.10.4"),
        ("0.10.4", None),
        (None, None),
    ),
)
def test_active_code_receipt_rejects_every_nonexact_governed_version_pair(
    tmp_path: Path,
    python_version: str | None,
    web_version: str | None,
) -> None:
    _seed_finalized_active_handoff(tmp_path)
    _write_governed_versions(
        tmp_path,
        python_version=python_version,
        web_version=web_version,
    )

    issues = control_doc_truth._validate_active_remediation_code_receipt(tmp_path)

    assert issues == [
        f"governed version sources must both equal 0.10.4; got pyproject={python_version!r}, web={web_version!r}"
    ]


@pytest.mark.parametrize(
    ("python_version", "web_version"),
    (("0.10.3", "0.10.3"), ("0.10.5", "0.10.5"), (None, None)),
)
def test_full_checker_active_handoff_cannot_be_disabled_by_version_sources(
    tmp_path: Path,
    python_version: str | None,
    web_version: str | None,
) -> None:
    _seed_truth_docs(tmp_path)
    _seed_active_handoff_docs(tmp_path)
    _write_governed_versions(
        tmp_path,
        python_version=python_version,
        web_version=web_version,
        include_readme=True,
    )

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=tmp_path)

    assert (
        f"governed version sources must both equal 0.10.4; got pyproject={python_version!r}, web={web_version!r}"
    ) in issues


def test_active_code_receipt_source_archive_without_git_validates_versions_only(tmp_path: Path) -> None:
    _seed_finalized_active_handoff(tmp_path)
    assert not (tmp_path / ".git").exists()

    # Source archives cannot prove Git ancestry or a Git-tree manifest. Their
    # dedicated package/parity gates own content provenance; this rule still
    # enforces aligned governed versions before returning.
    assert control_doc_truth._validate_active_remediation_code_receipt(tmp_path) == []


def _git(tmp_path: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(tmp_path), *args),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _commit_all(tmp_path: Path, message: str) -> str:
    _git(tmp_path, "add", ".")
    _git(
        tmp_path,
        "-c",
        "user.name=Control Truth Test",
        "-c",
        "user.email=control-truth@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        message,
    )
    return _git(tmp_path, "rev-parse", "HEAD")


def _pin_fixture_code_receipt(
    repo_path: Path,
    *,
    initial: str,
    remediation: str,
    audit_commit: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content_hashes = {
        relative_path: hashlib.sha256((repo_path / relative_path).read_bytes()).hexdigest()
        for relative_path in (
            "pyproject.toml",
            "apps/web/package.json",
            "apps/web/scripts/npm-advisory-audit.mjs",
            ".github/workflows/tests.yml",
        )
    }
    manifest, manifest_error = control_doc_truth._filtered_tree_manifest(repo_path, audit_commit)
    assert manifest_error is None
    assert manifest is not None

    monkeypatch.setattr(control_doc_truth, "_ACTIVE_REMEDIATION_CODE_COMMIT", remediation)
    monkeypatch.setattr(
        control_doc_truth,
        "_ACTIVE_REMEDIATION_CODE_TREE",
        _git(repo_path, "rev-parse", f"{remediation}^{{tree}}"),
    )
    monkeypatch.setattr(control_doc_truth, "_ACTIVE_REMEDIATION_CODE_PARENT", initial)
    monkeypatch.setattr(control_doc_truth, "_ACTIVE_REMEDIATION_AUDIT_COMMIT", audit_commit)
    monkeypatch.setattr(
        control_doc_truth,
        "_ACTIVE_REMEDIATION_AUDIT_TREE",
        _git(repo_path, "rev-parse", f"{audit_commit}^{{tree}}"),
    )
    monkeypatch.setattr(control_doc_truth, "_ACTIVE_REMEDIATION_CONTENT_HASHES", content_hashes)
    monkeypatch.setattr(control_doc_truth, "_ACTIVE_REMEDIATION_FILTERED_TREE_SHA256", manifest[0])
    monkeypatch.setattr(control_doc_truth, "_ACTIVE_REMEDIATION_FILTERED_TREE_RECORDS", manifest[1])
    monkeypatch.setattr(control_doc_truth, "_ACTIVE_REMEDIATION_FILTERED_TREE_BYTES", manifest[2])


@pytest.mark.parametrize("mutation", ("content", "mode", "path", "addition", "deletion"))
def test_filtered_tree_manifest_detects_every_committed_tree_drift_class(
    tmp_path: Path,
    mutation: str,
) -> None:
    _git(tmp_path, "init", "-q")
    production = tmp_path / "production.txt"
    production.write_text("baseline\n", encoding="utf-8")
    baseline_commit = _commit_all(tmp_path, "baseline")
    baseline, baseline_error = control_doc_truth._filtered_tree_manifest(tmp_path, baseline_commit)
    assert baseline_error is None
    assert baseline is not None

    if mutation == "content":
        production.write_text("changed\n", encoding="utf-8")
    elif mutation == "mode":
        production.chmod(production.stat().st_mode | 0o111)
    elif mutation == "path":
        _git(tmp_path, "mv", "production.txt", "renamed.txt")
    elif mutation == "addition":
        (tmp_path / "added.txt").write_text("added\n", encoding="utf-8")
    else:
        production.unlink()
    changed_commit = _commit_all(tmp_path, f"{mutation} drift")

    changed, changed_error = control_doc_truth._filtered_tree_manifest(tmp_path, changed_commit)

    assert changed_error is None
    assert changed is not None
    assert changed != baseline


def test_active_code_receipt_is_future_sha_safe_and_rejects_non_doc_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _git(tmp_path, "init", "-q")
    handoff_dir = _seed_finalized_active_handoff(tmp_path)
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    initial = _commit_all(tmp_path, "initial")

    (tmp_path / "production.txt").write_text("remediated\n", encoding="utf-8")
    remediation = _commit_all(tmp_path, "remediation")

    audit_script = tmp_path / "apps/web/scripts/npm-advisory-audit.mjs"
    audit_script.parent.mkdir(parents=True)
    audit_script.write_text("export const endpoint = 'bulk';\n", encoding="utf-8")
    release_notes = tmp_path / "docs/release/v0.10.4-release-notes.md"
    release_notes.parent.mkdir(parents=True)
    release_notes.write_text("pending\n", encoding="utf-8")
    workflow = tmp_path / ".github/workflows/tests.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: tests\n", encoding="utf-8")
    audit_commit = _commit_all(tmp_path, "npm audit endpoint")
    _pin_fixture_code_receipt(
        tmp_path,
        initial=initial,
        remediation=remediation,
        audit_commit=audit_commit,
        monkeypatch=monkeypatch,
    )

    readme = handoff_dir / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nreviewed truth\n", encoding="utf-8")
    _commit_all(tmp_path, "future documentation correction sha")

    assert control_doc_truth._validate_active_remediation_code_receipt(tmp_path) == []

    release_notes.write_text("published\n", encoding="utf-8")
    _commit_all(tmp_path, "post-publication truth update")

    assert control_doc_truth._validate_active_remediation_code_receipt(tmp_path) == []

    (tmp_path / "production.txt").write_text("unreviewed drift\n", encoding="utf-8")
    _commit_all(tmp_path, "unexpected production drift")

    issues = control_doc_truth._validate_active_remediation_code_receipt(tmp_path)

    assert any(issue.startswith("current HEAD filtered content manifest must equal") for issue in issues)
    assert "current HEAD changes tracked content outside the handoff-truth correction allowlist" in issues


def test_active_code_receipt_depth_one_clone_uses_complete_manifest_without_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    handoff_dir = _seed_finalized_active_handoff(origin)
    (origin / "base.txt").write_text("base\n", encoding="utf-8")
    initial = _commit_all(origin, "initial")

    (origin / "production.txt").write_text("remediated\n", encoding="utf-8")
    remediation = _commit_all(origin, "remediation")

    audit_script = origin / "apps/web/scripts/npm-advisory-audit.mjs"
    audit_script.parent.mkdir(parents=True)
    audit_script.write_text("export const endpoint = 'bulk';\n", encoding="utf-8")
    release_notes = origin / "docs/release/v0.10.4-release-notes.md"
    release_notes.parent.mkdir(parents=True)
    release_notes.write_text("pending\n", encoding="utf-8")
    workflow = origin / ".github/workflows/tests.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: tests\n", encoding="utf-8")
    audit_commit = _commit_all(origin, "npm audit endpoint")
    _pin_fixture_code_receipt(
        origin,
        initial=initial,
        remediation=remediation,
        audit_commit=audit_commit,
        monkeypatch=monkeypatch,
    )

    readme = handoff_dir / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nreviewed truth\n", encoding="utf-8")
    _commit_all(origin, "future documentation correction sha")
    _git(origin, "branch", "-M", "main")

    shallow = tmp_path / "shallow"
    subprocess.run(
        (
            "git",
            "clone",
            "-q",
            "--depth",
            "1",
            "--branch",
            "main",
            origin.resolve().as_uri(),
            str(shallow),
        ),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert _git(shallow, "rev-parse", "--is-shallow-repository") == "true"
    assert control_doc_truth._run_git(shallow, "cat-file", "-e", f"{audit_commit}^{{commit}}").returncode != 0

    assert control_doc_truth._validate_active_remediation_code_receipt(shallow) == []

    shallow_notes = shallow / "docs/release/v0.10.4-release-notes.md"
    shallow_notes.write_text("published\n", encoding="utf-8")
    _commit_all(shallow, "post-publication truth update")

    assert control_doc_truth._validate_active_remediation_code_receipt(shallow) == []

    (shallow / "production.txt").write_text("unreviewed drift\n", encoding="utf-8")

    uncommitted_issues = control_doc_truth._validate_active_remediation_code_receipt(shallow)

    assert "working tree changes tracked content outside the handoff-truth correction allowlist" in uncommitted_issues
    assert not any(
        issue.startswith("current HEAD filtered content manifest must equal") for issue in uncommitted_issues
    )

    _commit_all(shallow, "unexpected production drift")

    issues = control_doc_truth._validate_active_remediation_code_receipt(shallow)

    assert any(issue.startswith("current HEAD filtered content manifest must equal") for issue in issues)
    assert "current HEAD changes tracked content outside the handoff-truth correction allowlist" not in issues


def test_context_tree_docs_match_five_resource_groups_plus_events_and_legacy_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    changelog = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
    integration = (repo_root / "docs/alpha/agent-integration.md").read_text(encoding="utf-8")
    handoff_docs = [
        (repo_root / "docs/handoff/2026-07-14-v0.10.4-remediation" / filename).read_text(encoding="utf-8")
        for filename in (
            "BUILD_REPORT.md",
            "ENGINEER_HANDOFF.md",
            "FIX_MATRIX.md",
            "SURFACE_INVENTORY.md",
        )
    ]

    assert "five resource groups" in changelog
    assert "outside the core MCP surface" in changelog
    assert "five resource groups" in integration
    assert "not part of that core surface" in integration
    assert "disabled on key-bound servers" in integration
    assert all("five resource groups" in text for text in handoff_docs)
    false_markers = (
        "all six groups",
        "its six groups",
        "across the six groups",
        "six memory/source/open-loop/artifact/entity/project groups",
    )
    assert all(marker not in text for text in (changelog, integration, *handoff_docs) for marker in false_markers)


def test_mcp_resume_docs_limit_ascii_matching_to_open_loop_surfaces() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    mcp_docs = (repo_root / "docs/alpha/mcp-tools.md").read_text(encoding="utf-8")

    assert "root or nested `next_action` metadata participates only when its" in mcp_docs
    assert "JSON value is a string" in mcp_docs
    assert "For those open-loop row fields and loop-event string leaves only" in mcp_docs
    assert "memory search retains its memory-store matching contract" in mcp_docs
