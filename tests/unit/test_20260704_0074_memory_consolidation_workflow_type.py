from __future__ import annotations

import importlib

from alicebot_api.vnext_scheduler import WORKFLOW_TYPES


MODULE_NAME = "apps.api.alembic.versions.20260704_0074_memory_consolidation_workflow_type"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_agent_api_keys() -> None:
    module = load_migration_module()

    assert module.revision == "20260704_0074"
    assert module.down_revision == "20260704_0073"


def test_migration_types_match_scheduler_workflow_types() -> None:
    module = load_migration_module()

    assert module.WORKFLOW_TYPES == WORKFLOW_TYPES
    assert "memory_consolidation" in module.WORKFLOW_TYPES
    assert module.LEGACY_WORKFLOW_TYPES == WORKFLOW_TYPES[:-1]


def test_upgrade_extends_both_type_checks(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    for constraint in ("scheduler_workflows_type_check", "scheduler_runs_type_check"):
        assert f"DROP CONSTRAINT {constraint}" in joined
        assert f"ADD CONSTRAINT {constraint}" in joined
    assert joined.count("'memory_consolidation'") == 2


def test_downgrade_removes_consolidation_rows_before_restoring_checks(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    joined = "\n".join(executed)
    delete_runs_index = joined.index("DELETE FROM scheduler_runs")
    delete_workflows_index = joined.index("DELETE FROM scheduler_workflows")
    first_add_index = joined.index("ADD CONSTRAINT")
    assert delete_runs_index < first_add_index
    assert delete_workflows_index < first_add_index
    add_statements = [statement for statement in executed if "ADD CONSTRAINT" in statement]
    assert len(add_statements) == 2
    for statement in add_statements:
        assert "'memory_consolidation'" not in statement
