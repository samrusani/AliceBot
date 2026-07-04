from __future__ import annotations

import importlib

from alicebot_api.vnext_scheduler import WORKFLOW_TYPES


MODULE_NAME = "apps.api.alembic.versions.20260704_0075_staleness_write_path"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_memory_consolidation_workflow_type() -> None:
    module = load_migration_module()

    assert module.revision == "20260704_0075"
    assert module.down_revision == "20260704_0074"


def test_migration_types_match_scheduler_workflow_types() -> None:
    module = load_migration_module()

    assert module.WORKFLOW_TYPES == WORKFLOW_TYPES
    assert "staleness_sweep" in module.WORKFLOW_TYPES
    assert module.LEGACY_WORKFLOW_TYPES == WORKFLOW_TYPES[:-1]
    assert "staleness_sweep" not in module.LEGACY_WORKFLOW_TYPES


def test_migration_documents_missing_postgres_status_check() -> None:
    module = load_migration_module()

    docstring = module.__doc__ or ""
    assert "NO status CHECK" in docstring
    assert "20260510_0067" in docstring


def test_upgrade_creates_partial_valid_to_index_and_extends_both_type_checks(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "memories_user_valid_to_expiry_idx" in joined
    assert "ON memories (user_id, valid_to)" in joined
    assert "WHERE valid_to IS NOT NULL" in joined
    for constraint in ("scheduler_workflows_type_check", "scheduler_runs_type_check"):
        assert f"DROP CONSTRAINT {constraint}" in joined
        assert f"ADD CONSTRAINT {constraint}" in joined
    assert joined.count("'staleness_sweep'") == 2


def test_upgrade_skips_user_status_index_because_one_already_exists(monkeypatch) -> None:
    """20260311_0004 already ships memories_user_status_updated_idx on
    (user_id, status, updated_at), which covers (user_id, status) lookups, so
    0075 must not add a redundant status index."""
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "memories_user_status_updated_idx" not in joined
    assert "(user_id, status)" not in joined
    assert "memories_user_status_updated_idx" in (module.__doc__ or "")


def test_downgrade_removes_sweep_rows_before_restoring_checks_and_drops_index(monkeypatch) -> None:
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
        assert "'staleness_sweep'" not in statement
    assert "DROP INDEX IF EXISTS memories_user_valid_to_expiry_idx" in joined
