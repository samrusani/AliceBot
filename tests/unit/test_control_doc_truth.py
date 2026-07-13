from __future__ import annotations

from pathlib import Path

import pytest

import scripts.check_control_doc_truth as control_doc_truth


def _seed_truth_docs(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "alice-memory"\nversion = "9.8.7"\n',
        encoding="utf-8",
    )
    for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES:
        doc_path = tmp_path / rule.relative_path
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("\n".join(rule.required_markers) + "\n", encoding="utf-8")
    for rule in control_doc_truth.VERSION_ALIGNED_DOC_RULES:
        doc_path = tmp_path / rule.relative_path
        with doc_path.open("a", encoding="utf-8") as handle:
            # Seed text satisfying the semantic patterns without coupling the
            # test fixture to one exact pre-release sentence.
            handle.write("`v9.8.7` is the current release-hardening candidate\n")
            if rule.relative_path.endswith("CURRENT_STATE.md"):
                handle.write("## What `v9.8.7` Targets\n")


def test_control_doc_truth_passes_with_required_markers() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    issues = control_doc_truth.run_control_doc_truth_check(root_dir=repo_root)

    assert issues == []


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
            "docs/release/v0.9.4-release-notes.md",
            'The checker rejects present-tense "published to PyPI" claims.',
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
