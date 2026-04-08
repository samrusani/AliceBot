from __future__ import annotations

import json
from pathlib import Path

from alicebot_api.retrieval_evaluation import (
    _public_source_path,
    calculate_phase9_metric_ratio,
    write_phase9_evaluation_report,
)


def test_phase9_ratio_handles_zero_total() -> None:
    assert calculate_phase9_metric_ratio(passed_count=0, total_count=0) == 0.0


def test_phase9_ratio_calculates_fraction() -> None:
    assert calculate_phase9_metric_ratio(passed_count=2, total_count=4) == 0.5


def test_phase9_report_writer_persists_json(tmp_path: Path) -> None:
    report = {
        "schema_version": "phase9_eval_v1",
        "summary": {
            "status": "pass",
            "importer_count": 3,
        },
    }

    output_path = write_phase9_evaluation_report(
        report=report,
        report_path=tmp_path / "phase9_eval.json",
    )

    assert output_path.exists()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved == report


def test_public_source_path_uses_repo_relative_path_for_repo_files() -> None:
    repo_fixture = Path("fixtures/openclaw/workspace_v1.json").resolve()
    assert _public_source_path(repo_fixture) == "fixtures/openclaw/workspace_v1.json"


def test_public_source_path_redacts_external_paths(tmp_path: Path) -> None:
    external = tmp_path / "sensitive-source.json"
    external.write_text("{}", encoding="utf-8")
    assert _public_source_path(external) == "external/sensitive-source.json"
