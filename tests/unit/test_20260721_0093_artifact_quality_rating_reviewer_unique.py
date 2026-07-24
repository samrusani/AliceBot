from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260721_0093_artifact_quality_rating_reviewer_unique"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_phase5_ops_evidence_baseline() -> None:
    module = load_migration_module()

    assert module.revision == "20260721_0093"
    assert module.down_revision == "20260716_0092"


def test_upgrade_temporarily_unforces_rls_only_around_global_dedupe(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == list(module._UPGRADE_STATEMENTS)
    assert executed[0] == ("ALTER TABLE artifact_quality_ratings NO FORCE ROW LEVEL SECURITY")
    assert "WITH ranked_ratings AS" in executed[1]
    assert "DELETE FROM artifact_quality_ratings AS rating" in executed[1]
    assert "ADD CONSTRAINT artifact_quality_ratings_artifact_reviewer_key" in executed[2]
    assert executed[3] == ("ALTER TABLE artifact_quality_ratings FORCE ROW LEVEL SECURITY")


def test_downgrade_only_removes_reviewer_uniqueness_constraint(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert len(executed) == 1
    assert "DROP CONSTRAINT IF EXISTS" in executed[0]
