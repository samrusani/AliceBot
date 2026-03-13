from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260311_0002_tighten_runtime_privileges"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == list(module._UPGRADE_STATEMENTS)


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_downgrade_reasserts_revision_0001_privilege_floor() -> None:
    module = load_migration_module()

    assert module._DOWNGRADE_STATEMENTS == (
        "REVOKE UPDATE ON users FROM alicebot_app",
        "REVOKE UPDATE ON threads FROM alicebot_app",
        "REVOKE UPDATE ON sessions FROM alicebot_app",
    )
