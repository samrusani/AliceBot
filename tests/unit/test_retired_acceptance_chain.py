from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

RETIRED_CLOSEOUT_RUNBOOKS: tuple[str, ...] = (
    "docs/runbooks/phase2-closeout-packet.md",
    "docs/runbooks/phase3-closeout-packet.md",
)
CLOSEOUT_HISTORY_PATH = "docs/archive/process/phase2-phase3-closeout-history.md"

RETIRED_ACCEPTANCE_CHAIN: tuple[str, ...] = (
    "scripts/run_phase2_acceptance.py",
    "scripts/run_mvp_acceptance.py",
    "scripts/run_phase3_acceptance.py",
    "scripts/run_phase4_acceptance.py",
    "scripts/run_phase4_readiness_gates.py",
    "scripts/run_phase4_validation_matrix.py",
    "scripts/run_phase4_release_candidate.py",
    "scripts/generate_phase4_mvp_exit_manifest.py",
    "scripts/verify_phase4_mvp_exit_manifest.py",
    "scripts/run_phase4_mvp_qualification.py",
    "scripts/verify_phase4_mvp_signoff_record.py",
    "tests/integration/test_mvp_acceptance_suite.py",
    "tests/integration/test_phase4_acceptance_suite.py",
    "tests/integration/test_phase4_readiness_gates.py",
    "tests/integration/test_phase4_validation_matrix.py",
    "tests/integration/test_phase4_release_candidate.py",
    "tests/integration/test_phase4_mvp_exit_manifest.py",
    "tests/integration/test_phase4_mvp_qualification.py",
    "tests/integration/test_mvp_readiness_gates.py",
    "tests/integration/test_mvp_validation_matrix.py",
    "tests/unit/test_phase2_gate_wrappers.py",
    "tests/unit/test_phase4_gate_wrappers.py",
    "docs/runbooks/mvp-acceptance-suite.md",
    "docs/runbooks/mvp-ship-gate-magnesium-reorder.md",
    "docs/runbooks/mvp-validation-matrix.md",
    "docs/runbooks/phase4-acceptance-suite.md",
    "docs/runbooks/phase4-readiness-gates.md",
    "docs/runbooks/phase4-validation-matrix.md",
    "docs/runbooks/phase4-mvp-qualification.md",
    "docs/runbooks/phase4-closeout-packet.md",
    *RETIRED_CLOSEOUT_RUNBOOKS,
)

CURRENT_GATE_CARRIERS: tuple[str, ...] = (
    "scripts/run_phase2_readiness_gates.py",
    "scripts/run_phase2_validation_matrix.py",
    "scripts/run_mvp_readiness_gates.py",
    "scripts/run_mvp_validation_matrix.py",
    "scripts/run_phase3_readiness_gates.py",
    "scripts/run_phase3_validation_matrix.py",
    "docs/runbooks/mvp-readiness-gates.md",
)

RETIRED_REFERENCES: tuple[str, ...] = (
    "/v0/responses",
    "run_phase2_acceptance.py",
    "run_phase4_acceptance.py",
    "run_phase4_readiness_gates.py",
    "run_phase4_validation_matrix.py",
    "run_phase4_release_candidate.py",
    "test_mvp_acceptance_suite.py",
    "phase4_mvp_exit_manifest",
    "phase4_mvp_signoff_record",
)


def test_obsolete_acceptance_and_phase4_receipt_chain_stays_retired() -> None:
    restored_paths = [
        relative_path
        for relative_path in RETIRED_ACCEPTANCE_CHAIN
        if (REPO_ROOT / relative_path).exists()
    ]

    assert restored_paths == []


def test_current_gate_carriers_do_not_reintroduce_retired_chain() -> None:
    carrier_text = "\n".join(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        for relative_path in CURRENT_GATE_CARRIERS
    )

    for retired_reference in RETIRED_REFERENCES:
        assert retired_reference not in carrier_text


def test_retired_phase2_and_phase3_closeout_history_is_explicitly_nonoperational() -> None:
    history = (REPO_ROOT / CLOSEOUT_HISTORY_PATH).read_text(encoding="utf-8")
    archive_index = (REPO_ROOT / "docs/archive/process/README.md").read_text(encoding="utf-8")

    for marker in (
        "Historical record only.",
        "The former active runbooks were retired during the v0.11.0 Phase 1 periphery cut.",
        "This record does not authorize Phase 2 or Phase 3 work.",
        "../../../.ai/active/SPRINT_PACKET.md",
    ):
        assert marker in history
    assert "[Phase 2 and Phase 3 closeout history](phase2-phase3-closeout-history.md)" in archive_index


def test_live_docs_do_not_link_to_retired_phase2_or_phase3_closeout_runbooks() -> None:
    live_paths = [*REPO_ROOT.glob("*.md"), *(REPO_ROOT / ".ai/active").rglob("*.md")]
    live_paths.extend(
        path
        for path in (REPO_ROOT / "docs").rglob("*.md")
        if "archive" not in path.relative_to(REPO_ROOT / "docs").parts
        and "handoff" not in path.relative_to(REPO_ROOT / "docs").parts
    )
    retired_references = (
        *RETIRED_CLOSEOUT_RUNBOOKS,
        *(Path(relative_path).name for relative_path in RETIRED_CLOSEOUT_RUNBOOKS),
    )

    offenders = {
        str(path.relative_to(REPO_ROOT)): retired_name
        for path in live_paths
        for retired_name in retired_references
        if retired_name in path.read_text(encoding="utf-8")
    }

    assert offenders == {}
