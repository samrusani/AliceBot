from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260314_0024_task_artifact_chunks"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_TASK_ARTIFACTS_STATEMENTS,
        module._UPGRADE_SCHEMA_STATEMENT,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE task_artifact_chunks ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE task_artifact_chunks FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_task_artifact_chunk_privileges_allow_only_expected_runtime_writes() -> None:
    module = load_migration_module()

    assert module._UPGRADE_GRANT_STATEMENTS == (
        "GRANT UPDATE ON task_artifacts TO alicebot_app",
        "GRANT SELECT, INSERT ON task_artifact_chunks TO alicebot_app",
    )
