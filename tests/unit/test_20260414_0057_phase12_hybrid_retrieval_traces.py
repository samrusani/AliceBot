from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260414_0057_phase12_hybrid_retrieval_traces"


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
        "ALTER TABLE retrieval_runs ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE retrieval_runs FORCE ROW LEVEL SECURITY",
        "ALTER TABLE retrieval_candidates ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE retrieval_candidates FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_retrieval_trace_tables_are_insert_select_only() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT SELECT, INSERT ON retrieval_runs TO alicebot_app",
        "GRANT SELECT, INSERT ON retrieval_candidates TO alicebot_app",
    )


def test_retrieval_trace_schema_mentions_required_tables_and_scores() -> None:
    module = load_migration_module()
    joined_upgrade_sql = module._UPGRADE_SCHEMA_STATEMENT

    for table_name in ("retrieval_runs", "retrieval_candidates"):
        assert table_name in joined_upgrade_sql
    for column_name in (
        "lexical_score",
        "semantic_score",
        "entity_edge_score",
        "temporal_score",
        "trust_score",
        "stage_details",
        "ordering",
        "retention_until",
    ):
        assert column_name in joined_upgrade_sql
