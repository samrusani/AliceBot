from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260327_0039_task_run_execution_linkage"


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


def test_upgrade_enforces_idempotent_side_effect_guardrails() -> None:
    module = load_migration_module()

    assert any(
        "tool_executions_task_run_idempotency_idx" in statement
        for statement in module._UPGRADE_STATEMENTS
    )
    assert any(
        "waiting_approval" in statement
        for statement in module._UPGRADE_STATEMENTS
    )
