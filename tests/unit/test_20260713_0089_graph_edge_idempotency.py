from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260713_0089_graph_edge_idempotency"


class _AutocommitBlock:
    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


class _MigrationContext:
    def autocommit_block(self) -> _AutocommitBlock:
        return _AutocommitBlock()


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_and_online_unique_edge_fence(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module.op, "get_context", lambda: _MigrationContext())
    monkeypatch.setattr(module, "_index_is_invalid", lambda: False)

    module.upgrade()

    assert module.revision == "20260713_0089"
    assert module.down_revision == "20260713_0088"
    joined = "\n".join(executed)
    assert "CREATE UNIQUE INDEX CONCURRENTLY" in joined
    assert "graph_edges_user_idempotency_digest_uidx" in joined
    assert "metadata_json ->> 'idempotency_digest'" in joined


def test_upgrade_repairs_an_invalid_concurrent_index(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module.op, "get_context", lambda: _MigrationContext())
    monkeypatch.setattr(module, "_index_is_invalid", lambda: True)

    module.upgrade()

    assert executed[0] == ("DROP INDEX CONCURRENTLY IF EXISTS graph_edges_user_idempotency_digest_uidx")
    assert "CREATE UNIQUE INDEX CONCURRENTLY" in executed[1]
