"""Truth pins for the Phase 6 development and owner-held eval partition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

_EVAL_DIR = Path(__file__).resolve().parent.parent
_API_SRC = _EVAL_DIR.parent / "apps" / "api" / "src"
for _path in (_EVAL_DIR, _API_SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from longmemeval import count_probe, coverage_probe, runner  # noqa: E402


_SLICES_DIR = Path(__file__).resolve().parent / "slices"
_SOURCE_DEV_SLICE = _SLICES_DIR / "stage1-150.txt"
_NON_COUNT_SLICE = _SLICES_DIR / "phase6-non-count-101.txt"
_DATASET_MANIFEST = _SLICES_DIR / "dataset-manifest.json"
_SOURCE_DEV_STAGE_ORDER_SHA256 = "cc93a902019a82401f1f9bffc5c9437b08d1e269da599e248d64a7980e67ef73"
_NON_COUNT_STAGE_ORDER_SHA256 = "c660317b20610f578087dc1042b5454eed871cd395c558333fd927637e1627f0"


def _canonical_stage_order_sha256(question_ids: tuple[str, ...]) -> str:
    return hashlib.sha256(("\n".join(question_ids) + "\n").encode("utf-8")).hexdigest()


def test_phase6_non_count_slice_is_the_frozen_current_base_partition() -> None:
    source_dev_ids = runner.load_question_ids(_SOURCE_DEV_SLICE)
    non_count_ids = runner.load_question_ids(_NON_COUNT_SLICE)

    assert len(source_dev_ids) == len(set(source_dev_ids)) == 172
    assert _canonical_stage_order_sha256(source_dev_ids) == _SOURCE_DEV_STAGE_ORDER_SHA256
    assert len(non_count_ids) == len(set(non_count_ids)) == 101
    assert _canonical_stage_order_sha256(non_count_ids) == _NON_COUNT_STAGE_ORDER_SHA256

    non_count_id_set = set(non_count_ids)
    detector_positive_ids = tuple(question_id for question_id in source_dev_ids if question_id not in non_count_id_set)
    assert len(detector_positive_ids) == len(set(detector_positive_ids)) == 71
    assert non_count_id_set.isdisjoint(detector_positive_ids)
    assert non_count_id_set | set(detector_positive_ids) == set(source_dev_ids)


def test_phase6_owner_held_complement_count_is_truthful_without_an_id_list() -> None:
    dataset_manifest = json.loads(_DATASET_MANIFEST.read_text(encoding="utf-8"))
    source_dev_ids = runner.load_question_ids(_SOURCE_DEV_SLICE)

    assert dataset_manifest["question_count"] == 500
    assert dataset_manifest["dataset_sha256"] == coverage_probe.GOVERNED_DATASET_SHA256
    assert len(source_dev_ids) == len(set(source_dev_ids)) == 172
    assert dataset_manifest["question_count"] - len(source_dev_ids) == 328


def test_coverage_probe_question_id_loader_ignores_comments(tmp_path: Path) -> None:
    question_ids = tmp_path / "question-ids.txt"
    question_ids.write_text(
        "# governed slice\nq1\n  # section marker\n\nq2\n",
        encoding="utf-8",
    )

    assert coverage_probe._load_question_ids(question_ids) == ["q1", "q2"]


def test_phase6_release_manifests_are_content_bound(
    tmp_path: Path,
    monkeypatch,
) -> None:
    non_count_ids = runner.load_question_ids(_NON_COUNT_SLICE)
    assert coverage_probe.is_governed_non_count_manifest(
        _NON_COUNT_SLICE,
        non_count_ids,
    )
    assert not coverage_probe.is_governed_non_count_manifest(
        _NON_COUNT_SLICE,
        non_count_ids[:-1],
    )
    assert not coverage_probe.is_governed_non_count_manifest(
        tmp_path / _NON_COUNT_SLICE.name,
        non_count_ids,
    )

    governed_count_ids = runner.load_question_ids(_SOURCE_DEV_SLICE)
    copied_governed_path = tmp_path / "stage1-150.txt"
    copied_governed_path.write_text(
        "\n".join(governed_count_ids) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(count_probe, "DEFAULT_SLICE", copied_governed_path)
    assert count_probe.expected_audit_manifest(copied_governed_path) == count_probe.DEFAULT_AUDIT_MANIFEST

    copied_governed_path.write_text(
        "\n".join(governed_count_ids[:-1]) + "\n",
        encoding="utf-8",
    )
    assert count_probe.expected_audit_manifest(copied_governed_path) is None


def test_phase6_non_count_frozen_floor_gate_is_strict() -> None:
    baseline = {
        "overall": {
            "any_coverage": 0.9505,
            "all_coverage": 0.8812,
        },
        "per_type": {
            "multi-session": {
                "any_coverage": 0.9643,
                "all_coverage": 0.8571,
            }
        },
    }
    release_gate = coverage_probe.coverage_release_gate(
        baseline,
        release_eligible=True,
    )
    assert release_gate["passed"] is True
    assert (
        coverage_probe.exit_code_for_release_gate(
            release_gate,
            has_errors=False,
        )
        == coverage_probe.EXIT_OK
    )

    diagnostic_gate = coverage_probe.coverage_release_gate(
        baseline,
        release_eligible=False,
    )
    assert diagnostic_gate["mode"] == "diagnostic"
    assert diagnostic_gate["passed"] is False
    assert (
        coverage_probe.exit_code_for_release_gate(
            diagnostic_gate,
            has_errors=False,
        )
        == coverage_probe.EXIT_STRATUM_FAILURES
    )

    for scope, metric in (
        ("overall", "any_coverage"),
        ("overall", "all_coverage"),
        ("multi-session", "any_coverage"),
        ("multi-session", "all_coverage"),
    ):
        regressed = json.loads(json.dumps(baseline))
        bucket = regressed["overall"] if scope == "overall" else regressed["per_type"][scope]
        bucket[metric] -= 0.0001
        gate = coverage_probe.coverage_release_gate(
            regressed,
            release_eligible=True,
        )
        assert gate["checks"][f"{scope}.{metric}"]["passed"] is False
        assert (
            coverage_probe.exit_code_for_release_gate(
                gate,
                has_errors=False,
            )
            == coverage_probe.EXIT_STRATUM_FAILURES
        )


def test_phase6_release_inputs_are_dataset_mode_and_fresh_store_bound(
    tmp_path: Path,
) -> None:
    non_count_ids = runner.load_question_ids(_NON_COUNT_SLICE)
    coverage_kwargs = {
        "dataset_path": coverage_probe.GOVERNED_DATASET_PATH,
        "dataset_sha256": coverage_probe.GOVERNED_DATASET_SHA256,
        "question_id_file": _NON_COUNT_SLICE,
        "question_ids": non_count_ids,
        "limit": None,
        "max_items": coverage_probe.GOVERNED_MAX_ITEMS,
        "with_vectors": False,
        "with_reranker": False,
    }
    assert all(coverage_probe.coverage_release_input_checks(**coverage_kwargs).values())

    for override, failed_check in (
        ({"dataset_path": tmp_path / "spoof.json"}, "dataset_path_matches"),
        ({"dataset_sha256": "0" * 64}, "dataset_sha256_matches"),
        ({"max_items": 1}, "max_items_matches"),
        ({"with_vectors": True}, "vectors_disabled"),
        ({"with_reranker": True}, "reranker_disabled"),
        ({"limit": 1}, "limit_disabled"),
    ):
        checks = coverage_probe.coverage_release_input_checks(**(coverage_kwargs | override))
        assert checks[failed_check] is False

    count_ids = runner.load_question_ids(_SOURCE_DEV_SLICE)
    count_kwargs = {
        "dataset_path": coverage_probe.GOVERNED_DATASET_PATH,
        "dataset_sha256": coverage_probe.GOVERNED_DATASET_SHA256,
        "question_id_file": _SOURCE_DEV_SLICE,
        "question_ids": count_ids,
        "limit": None,
        "max_items": coverage_probe.GOVERNED_MAX_ITEMS,
        "with_vectors": False,
        "with_reranker": False,
        "accept_rollups": False,
    }
    assert all(count_probe.count_release_input_checks(**count_kwargs).values())
    for override, failed_check in (
        ({"dataset_path": tmp_path / "spoof.json"}, "dataset_path_matches"),
        ({"dataset_sha256": "0" * 64}, "dataset_sha256_matches"),
        ({"max_items": 1}, "max_items_matches"),
        ({"with_vectors": True}, "vectors_disabled"),
        ({"with_reranker": True}, "reranker_disabled"),
        ({"accept_rollups": True}, "rollups_disabled"),
        ({"limit": 1}, "limit_disabled"),
    ):
        checks = count_probe.count_release_input_checks(**(count_kwargs | override))
        assert checks[failed_check] is False

    assert coverage_probe.all_probe_stores_fresh(
        [{"reused_store": False}, {"reused_store": False}],
        expected_count=2,
    )
    assert not coverage_probe.all_probe_stores_fresh(
        [{"reused_store": False}, {"reused_store": True}],
        expected_count=2,
    )
    assert not coverage_probe.all_probe_stores_fresh(
        [{"reused_store": False}],
        expected_count=2,
    )
    assert not coverage_probe.all_probe_stores_fresh(
        [{"reused_store": None}, {"reused_store": False}],
        expected_count=2,
    )


def test_phase6_provider_metadata_redacts_endpoints(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        coverage_probe.EMBEDDINGS_BASE_URL_ENV,
        "https://user:secret@embeddings.example.test:8443/v1?api_key=hidden",
    )
    monkeypatch.setenv(coverage_probe.EMBEDDINGS_MODEL_ENV, "embed-model")
    monkeypatch.setenv(
        coverage_probe.RERANKER_BASE_URL_ENV,
        "https://user:secret@reranker.example.test/rank#token",
    )
    monkeypatch.setenv(coverage_probe.RERANKER_MODEL_ENV, "rerank-model")

    assert coverage_probe.provider_summary_metadata() == {
        "embeddings_model": "embed-model",
        "embeddings_base_url": "https://embeddings.example.test:8443/v1",
        "reranker_model": "rerank-model",
        "reranker_base_url": "https://reranker.example.test/rank",
    }
