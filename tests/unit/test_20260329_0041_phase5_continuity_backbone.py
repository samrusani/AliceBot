from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260329_0041_phase5_continuity_backbone"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_BOOTSTRAP_STATEMENTS,
        module._UPGRADE_SCHEMA_STATEMENT,
        module._UPGRADE_TRIGGER_STATEMENT,
        *module._UPGRADE_GRANT_STATEMENTS,
        "ALTER TABLE continuity_capture_events ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE continuity_capture_events FORCE ROW LEVEL SECURITY",
        "ALTER TABLE continuity_objects ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE continuity_objects FORCE ROW LEVEL SECURITY",
        module._UPGRADE_POLICY_STATEMENT,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_domains_match_sprint_contract() -> None:
    module = load_migration_module()

    assert module.CONTINUITY_OBJECT_TYPES == (
        "Note",
        "MemoryFact",
        "Decision",
        "Commitment",
        "WaitingFor",
        "Blocker",
        "NextAction",
    )
    assert module.CAPTURE_EXPLICIT_SIGNALS == (
        "remember_this",
        "task",
        "decision",
        "commitment",
        "waiting_for",
        "blocker",
        "next_action",
        "note",
    )
    assert module.CAPTURE_ADMISSION_POSTURES == ("DERIVED", "TRIAGE")
