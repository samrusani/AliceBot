from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260706_0080_memory_consolidation_artifact_type"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_true_redaction() -> None:
    module = load_migration_module()

    assert module.revision == "20260706_0080"
    assert module.down_revision == "20260706_0079"


def test_artifact_types_extend_the_0067_vocabulary() -> None:
    module = load_migration_module()
    migration_0067 = importlib.import_module(
        "apps.api.alembic.versions.20260510_0067_vnext_memory_kernel_schema"
    )

    frozen = tuple(migration_0067.ARTIFACT_TYPES)
    assert module.ARTIFACT_TYPES[: len(frozen)] == frozen
    assert module.ARTIFACT_TYPES[-1] == "memory_consolidation"
    assert module.LEGACY_ARTIFACT_TYPES == frozen


def test_upgrade_extends_the_artifact_type_check(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    assert "DROP CONSTRAINT generated_artifacts_type_check" in joined
    assert "ADD CONSTRAINT generated_artifacts_type_check" in joined
    assert "'memory_consolidation'" in joined


def test_downgrade_removes_consolidation_artifacts_before_restoring(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    joined = "\n".join(executed)
    delete_index = joined.index("DELETE FROM generated_artifacts")
    add_index = joined.index("ADD CONSTRAINT")
    assert delete_index < add_index
    add_statements = [s for s in executed if "ADD CONSTRAINT" in s]
    assert len(add_statements) == 1
    assert "'memory_consolidation'" not in add_statements[0]
