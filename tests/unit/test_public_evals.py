from __future__ import annotations

from datetime import UTC, datetime
from copy import deepcopy
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

import alicebot_api.public_evals as public_evals_module
from alicebot_api.public_evals import (
    list_public_eval_suites,
    run_public_evals,
    write_public_eval_report,
)


class EvalStoreStub:
    def __init__(self) -> None:
        self.suites: dict[str, dict[str, object]] = {}
        self.cases: dict[UUID, list[dict[str, object]]] = {}
        self.runs: dict[UUID, dict[str, object]] = {}
        self.results: dict[UUID, list[dict[str, object]]] = {}

    def upsert_eval_suite(self, **kwargs):
        existing = self.suites.get(kwargs["suite_key"])
        suite_id = existing["id"] if existing is not None else uuid4()
        row = {
            "id": suite_id,
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "created_at": existing["created_at"] if existing is not None else datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            **kwargs,
        }
        self.suites[kwargs["suite_key"]] = row
        return dict(row)

    def list_eval_suites(self):
        rows = [dict(row) for row in self.suites.values()]
        rows.sort(key=lambda row: (row["suite_order"], row["suite_key"]))
        return rows

    def delete_eval_suites_not_in(self, suite_keys: list[str]):
        allowed = set(suite_keys)
        kept_suite_ids = {
            row["id"]
            for key, row in self.suites.items()
            if key in allowed
        }
        self.suites = {
            key: row
            for key, row in self.suites.items()
            if key in allowed
        }
        self.cases = {
            suite_id: rows
            for suite_id, rows in self.cases.items()
            if suite_id in kept_suite_ids
        }

    def upsert_eval_case(self, **kwargs):
        suite_cases = self.cases.setdefault(kwargs["suite_id"], [])
        existing = next((row for row in suite_cases if row["case_key"] == kwargs["case_key"]), None)
        row = {
            "id": existing["id"] if existing is not None else uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "created_at": existing["created_at"] if existing is not None else datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            **kwargs,
        }
        if existing is None:
            suite_cases.append(row)
        else:
            suite_cases[suite_cases.index(existing)] = row
        return dict(row)

    def list_eval_cases_for_suite(self, suite_id: UUID):
        rows = [dict(row) for row in self.cases.get(suite_id, [])]
        rows.sort(key=lambda row: (row["case_order"], row["case_key"]))
        return rows

    def delete_eval_cases_for_suite_not_in(self, *, suite_id: UUID, case_keys: list[str]):
        allowed = set(case_keys)
        self.cases[suite_id] = [
            row for row in self.cases.get(suite_id, [])
            if row["case_key"] in allowed
        ]

    def create_eval_run(self, **kwargs):
        run_id = uuid4()
        row = {
            "id": run_id,
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "created_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            **kwargs,
        }
        self.runs[run_id] = row
        self.results.setdefault(run_id, [])
        return dict(row)

    def list_eval_runs(self, *, limit: int):
        rows = [dict(row) for row in self.runs.values()]
        rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
        return rows[:limit]

    def get_eval_run_optional(self, eval_run_id: UUID):
        row = self.runs.get(eval_run_id)
        return None if row is None else dict(row)

    def create_eval_result(self, **kwargs):
        row = {
            "id": uuid4(),
            "user_id": UUID("11111111-1111-4111-8111-111111111111"),
            "created_at": datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            **kwargs,
        }
        self.results.setdefault(kwargs["eval_run_id"], []).append(row)
        return dict(row)

    def list_eval_results_for_run(self, eval_run_id: UUID):
        rows = [dict(row) for row in self.results.get(eval_run_id, [])]
        rows.sort(key=lambda row: (row["suite_key"], row["case_key"], row["created_at"], row["id"]))
        return rows


def test_public_eval_runner_is_deterministic_and_passes() -> None:
    store = EvalStoreStub()
    user_id = UUID("11111111-1111-4111-8111-111111111111")

    first = run_public_evals(store, user_id=user_id)
    second = run_public_evals(store, user_id=user_id)

    assert first["report"] == second["report"]
    assert first["run"]["report_digest"] == second["run"]["report_digest"]
    assert first["report"]["summary"] == {
        "status": "pass",
        "suite_count": 5,
        "case_count": 12,
        "passed_case_count": 12,
        "failed_case_count": 0,
        "pass_rate": 1.0,
    }
    assert [suite["suite_key"] for suite in first["report"]["suites"]] == [
        "recall",
        "resumption",
        "correction",
        "contradiction",
        "open_loop",
    ]


def test_public_eval_suite_listing_reflects_catalog() -> None:
    store = EvalStoreStub()
    payload = list_public_eval_suites(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )

    assert payload["summary"]["suite_count"] == 5
    assert payload["summary"]["case_count"] == 12
    assert payload["items"][0]["suite_key"] == "recall"
    assert "entity_edge_expansion_recovers_related_owner" in payload["items"][0]["case_keys"]
    assert store.suites == {}
    assert store.cases == {}


def test_public_eval_runner_prunes_removed_catalog_entries(monkeypatch) -> None:
    store = EvalStoreStub()
    user_id = UUID("11111111-1111-4111-8111-111111111111")
    first_catalog = {
        "schema_version": "public_eval_fixture_v1",
        "suites": [
            {
                "suite_key": "alpha",
                "title": "Alpha",
                "description": "Alpha suite",
                "evaluator_kind": "open_loop_dashboard",
                "cases": [
                    {
                        "case_key": "alpha_case_1",
                        "title": "Alpha case 1",
                        "evaluator_kind": "open_loop_dashboard",
                        "fixture": {"request": {"limit": 10}, "rows": []},
                        "expectations": {
                            "waiting_for_titles": [],
                            "blocker_titles": [],
                            "stale_titles": [],
                            "next_action_titles": [],
                        },
                    },
                    {
                        "case_key": "alpha_case_2",
                        "title": "Alpha case 2",
                        "evaluator_kind": "open_loop_dashboard",
                        "fixture": {"request": {"limit": 10}, "rows": []},
                        "expectations": {
                            "waiting_for_titles": [],
                            "blocker_titles": [],
                            "stale_titles": [],
                            "next_action_titles": [],
                        },
                    },
                ],
            },
            {
                "suite_key": "beta",
                "title": "Beta",
                "description": "Beta suite",
                "evaluator_kind": "open_loop_dashboard",
                "cases": [
                    {
                        "case_key": "beta_case_1",
                        "title": "Beta case 1",
                        "evaluator_kind": "open_loop_dashboard",
                        "fixture": {"request": {"limit": 10}, "rows": []},
                        "expectations": {
                            "waiting_for_titles": [],
                            "blocker_titles": [],
                            "stale_titles": [],
                            "next_action_titles": [],
                        },
                    }
                ],
            },
        ],
    }
    second_catalog = deepcopy(first_catalog)
    second_catalog["suites"] = [deepcopy(first_catalog["suites"][0])]
    second_catalog["suites"][0]["cases"] = [deepcopy(first_catalog["suites"][0]["cases"][0])]

    monkeypatch.setattr(public_evals_module, "_load_fixture_catalog", lambda: deepcopy(first_catalog))
    first_run = run_public_evals(store, user_id=user_id)
    assert [suite["suite_key"] for suite in first_run["report"]["suites"]] == ["alpha", "beta"]

    monkeypatch.setattr(public_evals_module, "_load_fixture_catalog", lambda: deepcopy(second_catalog))
    second_run = run_public_evals(store, user_id=user_id)
    assert [suite["suite_key"] for suite in second_run["report"]["suites"]] == ["alpha"]
    assert sorted(store.suites) == ["alpha"]
    alpha_suite_id = next(iter(store.cases))
    assert [row["case_key"] for row in store.cases[alpha_suite_id]] == ["alpha_case_1"]


def test_public_eval_runner_rejects_unknown_suite_keys() -> None:
    with pytest.raises(ValueError, match="unknown suite_key values: missing_suite"):
        run_public_evals(
            EvalStoreStub(),  # type: ignore[arg-type]
            user_id=UUID("11111111-1111-4111-8111-111111111111"),
            suite_keys=["missing_suite"],
        )


def test_write_public_eval_report_persists_stable_json(tmp_path: Path) -> None:
    store = EvalStoreStub()
    payload = run_public_evals(
        store,  # type: ignore[arg-type]
        user_id=UUID("11111111-1111-4111-8111-111111111111"),
    )
    output_path = tmp_path / "public_eval_report.json"

    written = write_public_eval_report(report=payload["report"], report_path=output_path)

    assert written == output_path.resolve()
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload["report"]
