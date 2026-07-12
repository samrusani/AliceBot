from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260712_0084_memory_lifecycle_identifier_repair"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_follows_lifecycle_invariants_head() -> None:
    module = load_migration_module()
    assert module.revision == "20260712_0084"
    assert module.down_revision == "20260711_0083"


def test_upgrade_moves_identifiers_from_tombstone_to_oldest_live_row(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    joined = "\n".join(executed)
    # Each repaired column selects the oldest LIVE cleared sibling of a
    # tombstone that still holds the identifier.
    for column in ("commit_digest", "confirmation_id"):
        assert f"{column} IS NOT NULL" in joined
        assert f"AND candidate.{column} IS NULL" in joined
    assert "deleted_at IS NOT NULL" in joined
    assert "candidate.deleted_at IS NULL" in joined
    assert "ORDER BY candidate.created_at ASC, candidate.id ASC" in joined
    assert "LIMIT 1" in joined
    # The move is release (clear) then restore, so ordering matters: the
    # tombstone is cleared before the identifier is set on the live row.
    assert joined.index("commit_digest = NULL") < joined.index(
        "commit_digest = r.holder_value"
    )
    assert joined.index("confirmation_id = NULL") < joined.index(
        "confirmation_id = r.holder_value"
    )
    assert "duplicate_commit_digest_canonical_memory_id" in joined
    assert "duplicate_confirmation_id_canonical_memory_id" in joined
    # Mirrored metadata values are restored onto the live canonical row.
    assert "{agentic_memory,idempotency_key}" in joined
    assert "{agentic_memory,confirmation,confirmation_id}" in joined
    # Scratch state is created, guarded against a stale prior run, cleaned up,
    # and never enforces uniqueness itself.
    assert "CREATE UNIQUE INDEX" not in joined
    for temp_table in (
        "_lifecycle_0084_commit_digest_repair",
        "_lifecycle_0084_confirmation_id_repair",
    ):
        assert f"CREATE TEMP TABLE {temp_table}" in joined
        assert f"DROP TABLE IF EXISTS {temp_table}" in joined
        # The final cleanup drop (distinct from the leading IF EXISTS guard).
        assert joined.count(f"DROP TABLE {temp_table}") == 1


def test_downgrade_is_a_no_op(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == []
