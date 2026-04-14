from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260414_0061_phase12_task_adaptive_briefing"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_MODEL_PACK_STATEMENTS,
        module._UPGRADE_SCHEMA_STATEMENT,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE task_briefs ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE task_briefs FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_task_brief_schema_mentions_expected_columns() -> None:
    module = load_migration_module()
    joined_upgrade_sql = module._UPGRADE_SCHEMA_STATEMENT
    model_pack_sql = "\n".join(module._UPGRADE_MODEL_PACK_STATEMENTS)

    for table_name in ("task_briefs",):
        assert table_name in joined_upgrade_sql
    for column_name in (
        "mode",
        "query_text",
        "scope",
        "provider_strategy",
        "model_pack_strategy",
        "token_budget",
        "estimated_tokens",
        "item_count",
        "deterministic_key",
        "payload",
    ):
        assert column_name in joined_upgrade_sql

    assert "briefing_strategy" in model_pack_sql
    assert "briefing_max_tokens" in model_pack_sql
