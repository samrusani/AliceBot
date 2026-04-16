from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260416_0066_hosted_control_plane_owner_writes"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_DROP_STATEMENTS,
        *module._UPGRADE_CREATE_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == [
        *module._DOWNGRADE_DROP_STATEMENTS,
        *module._DOWNGRADE_CREATE_STATEMENTS,
    ]


def test_upgrade_restricts_control_plane_writes_to_workspace_owners() -> None:
    module = load_migration_module()
    policy_sql = "\n".join(module._UPGRADE_CREATE_STATEMENTS)

    assert "CREATE POLICY model_providers_select_access" in policy_sql
    assert "CREATE POLICY model_providers_insert_owner_access" in policy_sql
    assert "CREATE POLICY workspace_model_pack_bindings_delete_owner_access" in policy_sql
    assert "app.hosted_workspace_access_allowed(workspace_id)" in policy_sql
    assert "app.hosted_workspace_owner_allowed(workspace_id)" in policy_sql
