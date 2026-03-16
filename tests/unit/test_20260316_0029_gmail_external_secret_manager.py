from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260316_0029_gmail_external_secret_manager"


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


def test_upgrade_marks_external_secret_manager_and_legacy_transition_kinds_explicitly() -> None:
    module = load_migration_module()

    assert module.GMAIL_SECRET_MANAGER_KIND_FILE_V1 == "file_v1"
    assert module.GMAIL_SECRET_MANAGER_KIND_LEGACY_DB_V0 == "legacy_db_v0"
