from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260324_0033_agent_profile_registry"


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


def test_seeded_registry_rows_and_thread_binding_contract() -> None:
    module = load_migration_module()

    assert module.AGENT_PROFILE_SEED_ROWS == (
        (
            "assistant_default",
            "Assistant Default",
            "General-purpose assistant profile for baseline conversations.",
        ),
        (
            "coach_default",
            "Coach Default",
            "Coaching-oriented profile focused on guidance and accountability.",
        ),
    )
    assert module.AGENT_PROFILE_IDS == ("assistant_default", "coach_default")
    assert "threads_agent_profile_id_check" in module._UPGRADE_STATEMENTS[3]
    assert "threads_agent_profile_id_fkey" in module._UPGRADE_STATEMENTS[4]
