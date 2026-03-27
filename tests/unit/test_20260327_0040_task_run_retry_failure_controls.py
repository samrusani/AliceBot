from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260327_0040_task_run_retry_failure_controls"


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


def test_upgrade_enforces_retry_and_failure_controls() -> None:
    module = load_migration_module()

    combined = "\n".join(module._UPGRADE_STATEMENTS)
    assert "retry_count" in combined
    assert "retry_cap" in combined
    assert "retry_posture" in combined
    assert "failure_class" in combined
    assert "last_transitioned_at" in combined
    assert "waiting_user" in combined
    assert "done" in combined
    assert "failed" in combined
    assert "status = 'paused' AND stop_reason = 'budget_exhausted' THEN 'terminal'" in combined
