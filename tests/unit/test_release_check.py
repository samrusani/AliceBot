from __future__ import annotations

from pathlib import Path
import subprocess

import scripts.release_check as release_check


def _seed_metadata_tree(tmp_path: Path, *, python_version: str, web_version: str) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "\n".join(
            (
                "[project]",
                'name = "alice-memory"',
                f'version = "{python_version}"',
                "",
            )
        ),
        encoding="utf-8",
    )
    web_dir = tmp_path / "apps" / "web"
    web_dir.mkdir(parents=True)
    (web_dir / "package.json").write_text(
        f'{{"name":"@alicebot/web","private":true,"version":"{web_version}"}}\n',
        encoding="utf-8",
    )
    package_dir = tmp_path / "apps" / "api" / "src" / "alicebot_api"
    package_dir.mkdir(parents=True)
    (package_dir / "main.py").write_text(
        'app = FastAPI(title="AliceBot API", version=__version__)\n',
        encoding="utf-8",
    )
    (package_dir / "__init__.py").write_text(
        '__version__ = _distribution_version("alice-memory")\n',
        encoding="utf-8",
    )


def test_release_metadata_uses_pyproject_as_canonical_version(tmp_path: Path) -> None:
    _seed_metadata_tree(tmp_path, python_version="1.2.3", web_version="1.2.3")

    metadata, issues = release_check.validate_metadata(tmp_path)

    assert issues == []
    assert metadata.version == "1.2.3"
    assert metadata.tag == "v1.2.3"


def test_release_metadata_rejects_web_version_drift(tmp_path: Path) -> None:
    _seed_metadata_tree(tmp_path, python_version="1.2.3", web_version="1.2.2")

    _metadata, issues = release_check.validate_metadata(tmp_path)

    assert any("package.json version does not match pyproject.toml" in issue for issue in issues)


def test_release_metadata_rejects_prerelease_version(tmp_path: Path) -> None:
    _seed_metadata_tree(tmp_path, python_version="1.2.3rc1", web_version="1.2.3rc1")

    _metadata, issues = release_check.validate_metadata(tmp_path)

    assert any("stable SemVer" in issue for issue in issues)


def test_checksum_manifest_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "alice_memory-1.2.3.tar.gz"
    second = tmp_path / "alice_memory-1.2.3-py3-none-any.whl"
    first.write_bytes(b"sdist")
    second.write_bytes(b"wheel")

    manifest = release_check.write_checksums(tmp_path, [second, first])

    assert manifest.read_text(encoding="utf-8").splitlines() == [
        "ba59926159d2aa256eb8739b8da7e2b574b960e1202c6d624cbe981cef996c91  alice_memory-1.2.3-py3-none-any.whl",
        "714772a9f82b2aeb4fa5f7092d00fe4ac4c9cdeb6800840b6ed39ea64c4d785a  alice_memory-1.2.3.tar.gz",
    ]


def test_release_git_identity_resolves_annotated_tag_to_exact_main_commit(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Release Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "release@example.invalid"], check=True)
    (repo / "candidate.txt").write_text("candidate\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "candidate.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "candidate"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "-u", "origin", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "tag", "-a", "v1.2.3", "-m", "v1.2.3"], check=True)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    issues = release_check.validate_git_state(
        root_dir=repo,
        tag="v1.2.3",
        expected_sha=head,
        require_main_head=True,
        require_clean=True,
    )

    assert issues == []


def test_release_git_identity_rejects_lightweight_tag(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Release Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "release@example.invalid"],
        check=True,
    )
    (repo / "candidate.txt").write_text("candidate\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "candidate.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "candidate"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "-C", str(repo), "tag", "v1.2.3"], check=True)

    issues = release_check.validate_git_state(
        root_dir=repo,
        tag="v1.2.3",
        expected_sha=None,
        require_main_head=False,
        require_clean=True,
    )

    assert any("must be an annotated tag" in issue for issue in issues)


def test_finalized_release_docs_require_dated_changelog_and_final_title(tmp_path: Path) -> None:
    release_dir = tmp_path / "docs" / "release"
    release_dir.mkdir(parents=True)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n## v1.2.3 — 2026-07-11\n\n- Ready.\n",
        encoding="utf-8",
    )
    (release_dir / "v1.2.3-release-notes.md").write_text(
        "# Alice v1.2.3 Release Notes\n\nReady for publication.\n",
        encoding="utf-8",
    )

    assert release_check.validate_release_document_state(
        tmp_path, version="1.2.3", require_finalized=True
    ) == []

    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n", encoding="utf-8")
    (release_dir / "v1.2.3-release-notes.md").write_text(
        "# Alice v1.2.3 Release Candidate Notes\n\nNot published yet.\n",
        encoding="utf-8",
    )
    issues = release_check.validate_release_document_state(
        tmp_path, version="1.2.3", require_finalized=True
    )
    assert any("finalized dated heading" in issue for issue in issues)
    assert any("finalized title" in issue for issue in issues)
    assert any("release-candidate status language" in issue for issue in issues)


def _seed_finalized_docs(tmp_path: Path, notes_verify_section: str) -> Path:
    release_dir = tmp_path / "docs" / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n## v1.2.3 — 2026-07-11\n\n- Ready.\n",
        encoding="utf-8",
    )
    notes = release_dir / "v1.2.3-release-notes.md"
    notes.write_text(
        "# Alice v1.2.3 Release Notes\n\nReady.\n\n"
        "## Verifying this release\n\n" + notes_verify_section + "\n",
        encoding="utf-8",
    )
    return notes


def test_finalized_release_docs_reject_premature_publication_claim(tmp_path: Path) -> None:
    # The finalized notes are committed BEFORE the tag and publication, so a
    # present-tense assertion that artifacts are already on PyPI is false at
    # tag time and must be rejected by the gate.
    _seed_finalized_docs(
        tmp_path,
        "The wheel and source distribution are published to PyPI through GitHub "
        "Trusted Publishing and carry PyPI's integrity attestations.",
    )

    issues = release_check.validate_release_document_state(
        tmp_path, version="1.2.3", require_finalized=True
    )

    assert any("publication" in issue.lower() for issue in issues), issues


def test_finalized_release_docs_reject_claiming_absent_checksums_recorded(tmp_path: Path) -> None:
    # The per-release checksums file is written only in the post-publication
    # commit. Claiming digests "are recorded" in it while it does not exist is
    # a premature/false reference and must be rejected.
    _seed_finalized_docs(
        tmp_path,
        "The exact SHA-256 digests of the published artifacts are recorded in "
        "`docs/release/v1.2.3-checksums.txt` in this repository.",
    )

    issues = release_check.validate_release_document_state(
        tmp_path, version="1.2.3", require_finalized=True
    )

    assert any("checksums" in issue.lower() for issue in issues), issues


def test_finalized_release_docs_accept_forward_looking_verification(tmp_path: Path) -> None:
    # Honest forward-looking wording (publication described as forthcoming, and
    # the checksums file as something that WILL be recorded) must pass.
    _seed_finalized_docs(
        tmp_path,
        "Alice publishes to PyPI through GitHub Trusted Publishing. "
        "Once published, the artifacts carry PyPI's integrity attestations. "
        "Their exact SHA-256 digests will be recorded in "
        "`docs/release/v1.2.3-checksums.txt` as part of the post-publication commit.",
    )

    assert release_check.validate_release_document_state(
        tmp_path, version="1.2.3", require_finalized=True
    ) == []


def test_finalized_release_docs_require_empty_unreleased_section(tmp_path: Path) -> None:
    release_dir = tmp_path / "docs" / "release"
    release_dir.mkdir(parents=True)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n- Still pending.\n\n"
        "## v1.2.3 — 2026-07-11\n\n- Ready.\n",
        encoding="utf-8",
    )
    (release_dir / "v1.2.3-release-notes.md").write_text(
        "# Alice v1.2.3 Release Notes\n\nReady for publication.\n",
        encoding="utf-8",
    )

    issues = release_check.validate_release_document_state(
        tmp_path, version="1.2.3", require_finalized=True
    )

    assert any("Unreleased section must be empty" in issue for issue in issues)
