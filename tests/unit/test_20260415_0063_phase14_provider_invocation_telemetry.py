from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260415_0063_phase14_provider_invocation_telemetry"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
        *module._UPGRADE_RLS_STATEMENTS,
        *module._UPGRADE_POLICY_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_upgrade_defines_workspace_access_policy() -> None:
    module = load_migration_module()
    policy_sql = "\n".join(module._UPGRADE_POLICY_STATEMENTS)

    assert "CREATE POLICY provider_invocation_telemetry_workspace_access" in policy_sql
    assert "app.hosted_workspace_access_allowed(workspace_id)" in policy_sql
