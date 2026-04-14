from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260414_0060_phase12_public_eval_harness"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        module._UPGRADE_SCHEMA_STATEMENT,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE eval_suites ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE eval_suites FORCE ROW LEVEL SECURITY",
        "ALTER TABLE eval_cases ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE eval_cases FORCE ROW LEVEL SECURITY",
        "ALTER TABLE eval_runs ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE eval_runs FORCE ROW LEVEL SECURITY",
        "ALTER TABLE eval_results ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE eval_results FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_public_eval_schema_mentions_expected_tables_and_columns() -> None:
    module = load_migration_module()
    joined_upgrade_sql = module._UPGRADE_SCHEMA_STATEMENT

    for table_name in ("eval_suites", "eval_cases", "eval_runs", "eval_results"):
        assert table_name in joined_upgrade_sql
    for column_name in (
        "suite_key",
        "evaluator_kind",
        "fixture_schema_version",
        "fixture_source_path",
        "requested_suite_keys",
        "report_digest",
        "summary",
        "report",
        "score",
        "details",
    ):
        assert column_name in joined_upgrade_sql
