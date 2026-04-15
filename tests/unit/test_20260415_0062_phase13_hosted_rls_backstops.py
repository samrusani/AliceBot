from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260415_0062_phase13_hosted_rls_backstops"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    expected = [
        *module._UPGRADE_FUNCTION_STATEMENTS,
    ]
    for table_name in module._RLS_TABLES:
        expected.append(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        expected.append(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    expected.extend(module._UPGRADE_POLICY_STATEMENTS)

    assert executed == expected


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    expected = list(module._DOWNGRADE_POLICY_STATEMENTS)
    for table_name in reversed(module._RLS_TABLES):
        expected.append(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
        expected.append(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")
    expected.extend(module._DOWNGRADE_FUNCTION_STATEMENTS)

    assert executed == expected


def test_upgrade_defines_workspace_backstop_functions_and_policies() -> None:
    module = load_migration_module()
    function_sql = "\n".join(module._UPGRADE_FUNCTION_STATEMENTS)
    policy_sql = "\n".join(module._UPGRADE_POLICY_STATEMENTS)

    assert "app.current_user_account_id()" in function_sql
    assert "app.hosted_workspace_access_allowed(target_workspace_id uuid)" in function_sql
    assert "app.hosted_workspace_owner_allowed(target_workspace_id uuid)" in function_sql
    assert "FROM workspace_members AS wm" in function_sql
    assert "CREATE POLICY model_providers_workspace_access" in policy_sql
    assert "CREATE POLICY workspaces_update_access" in policy_sql
    assert "CREATE POLICY workspace_members_insert_access" in policy_sql
    assert "app.hosted_workspace_owner_allowed(workspace_id)" in policy_sql
    assert "CREATE POLICY channel_identities_access" in policy_sql
    assert "app.hosted_workspace_access_allowed(workspace_id)" in policy_sql
