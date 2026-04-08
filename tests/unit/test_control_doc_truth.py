from __future__ import annotations

from pathlib import Path

import scripts.check_control_doc_truth as control_doc_truth


def _seed_truth_docs(tmp_path: Path) -> None:
    for rule in control_doc_truth.CONTROL_DOC_TRUTH_RULES:
        doc_path = tmp_path / rule.relative_path
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("\n".join(rule.required_markers) + "\n", encoding="utf-8")


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
