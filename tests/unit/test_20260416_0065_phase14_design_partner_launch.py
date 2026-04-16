from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260416_0065_phase14_design_partner_launch"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    expected_rls_statements = []
    for table_name in module._RLS_TABLES:
        expected_rls_statements.append(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        expected_rls_statements.append(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

    assert executed == [
        *module._UPGRADE_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
        *expected_rls_statements,
        *module._UPGRADE_POLICY_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_upgrade_defines_admin_bypass_policies() -> None:
    module = load_migration_module()
    policy_sql = "\n".join(module._UPGRADE_POLICY_STATEMENTS)

    assert "CREATE POLICY design_partners_admin_access" in policy_sql
    assert "app.hosted_access_bypass()" in policy_sql
