from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260707_0082_memory_fact_keys"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_source_chunk_fts() -> None:
    module = load_migration_module()

    assert module.revision == "20260707_0082"
    assert module.down_revision == "20260707_0081"


def test_upgrade_adds_fact_keys_and_reweaves_search_tsv(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == list(module._UPGRADE_STATEMENTS)
    joined = "\n".join(executed)
    assert "ADD COLUMN fact_keys text NULL" in joined
    # The stored generated column cannot be altered in place: it is
    # dropped and re-added with the fact_keys 'D' term, then re-indexed.
    assert "DROP INDEX IF EXISTS memories_search_tsv_gin_idx" in joined
    assert "DROP COLUMN IF EXISTS search_tsv" in joined
    assert "GENERATED ALWAYS AS" in joined
    assert "STORED" in joined
    for field, weight in (("title", "'A'"), ("canonical_text", "'B'"), ("summary", "'C'"), ("fact_keys", "'D'")):
        assert f"coalesce({field}, '')), {weight}" in joined
    assert "USING gin (search_tsv)" in joined

    # Ordering: fact_keys exists before the generated column references it,
    # and the GIN index is created after the column returns.
    add_fact_keys = next(index for index, sql in enumerate(executed) if "ADD COLUMN fact_keys" in sql)
    add_tsv = next(index for index, sql in enumerate(executed) if "ADD COLUMN search_tsv" in sql)
    create_index = next(index for index, sql in enumerate(executed) if "USING gin" in sql)
    assert add_fact_keys < add_tsv < create_index


def test_downgrade_restores_the_0072_expression_and_drops_fact_keys(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)
    joined = "\n".join(executed)
    assert "DROP COLUMN IF EXISTS fact_keys" in joined
    assert "coalesce(summary, '')), 'C'" in joined
    # The restored expression must NOT reference the dropped column.
    restored_tsv = next(sql for sql in executed if "ADD COLUMN search_tsv" in sql)
    assert "fact_keys" not in restored_tsv
    assert "USING gin (search_tsv)" in joined
    # fact_keys is dropped only after search_tsv stops referencing it.
    drop_fact_keys = next(index for index, sql in enumerate(executed) if "DROP COLUMN IF EXISTS fact_keys" in sql)
    add_tsv = next(index for index, sql in enumerate(executed) if "ADD COLUMN search_tsv" in sql)
    assert add_tsv < drop_fact_keys
