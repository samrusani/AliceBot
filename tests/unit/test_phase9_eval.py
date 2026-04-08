from __future__ import annotations

import json
from pathlib import Path

from alicebot_api.retrieval_evaluation import calculate_phase9_metric_ratio, write_phase9_evaluation_report


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
