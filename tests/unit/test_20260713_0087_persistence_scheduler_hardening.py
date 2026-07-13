from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260713_0087_persistence_scheduler_hardening"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_follows_last_published_migration() -> None:
    module = load_migration_module()
    assert module.revision == "20260713_0087"
    assert module.down_revision == "20260713_0086"


class _AutocommitBlock:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def __enter__(self):
        self.calls.append("autocommit.enter")
        return self

    def __exit__(self, *_args) -> None:
        self.calls.append("autocommit.exit")


class _MigrationContext:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def autocommit_block(self) -> _AutocommitBlock:
        return _AutocommitBlock(self.calls)


def test_upgrade_is_online_safe_and_defers_legacy_status_repair(monkeypatch) -> None:
    module = load_migration_module()
    assert "deleted" in module.MEMORY_STATUSES
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module.op, "get_context", lambda: _MigrationContext(executed))
    monkeypatch.setattr(module, "_index_is_invalid", lambda _index_name: False)

    module.upgrade()

    joined = "\n".join(executed)
    assert "UPDATE memories" not in joined
    assert "VALIDATE CONSTRAINT" not in joined
    assert "NOT VALID" in joined
    assert "autocommit.enter" in executed
    assert "CREATE INDEX CONCURRENTLY" in joined
    assert "task_queue_user_pending_claim_idx" in joined
    assert "event_log_user_occurred_idx" in joined
    assert "sources_user_content_hash_idx" in joined
    assert "generated_artifacts_user_workflow_digest_idx" in joined
    assert "generated_artifacts_user_idempotency_digest_uidx" in joined
    assert "memories_user_project_rollup_digest_idx" in joined
    assert "open_loops_user_automation_digest_idx" in joined
    assert "open_loops_user_idempotency_digest_uidx" in joined
    assert "scheduler_workflows_user_due_claim_idx" in joined
    assert "scheduler_runs_user_expired_claim_idx" in joined
    assert "ADD COLUMN IF NOT EXISTS claim_token" in joined
    assert "ADD COLUMN IF NOT EXISTS scheduled_for" in joined
    assert joined.count("FROM pg_catalog.pg_constraint") == 4


def test_concurrent_index_names_remain_in_lockstep_with_create_statements() -> None:
    module = load_migration_module()
    extracted_names = tuple(
        statement.split("IF NOT EXISTS", maxsplit=1)[1].split(maxsplit=1)[0]
        for statement in module._CONCURRENT_INDEX_STATEMENTS
    )

    assert extracted_names == module._CONCURRENT_INDEX_NAMES


def test_upgrade_drops_only_invalid_indexes_before_rebuilding(monkeypatch) -> None:
    module = load_migration_module()
    invalid_name = "generated_artifacts_user_idempotency_digest_uidx"
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module.op, "get_context", lambda: _MigrationContext(executed))
    monkeypatch.setattr(
        module,
        "_index_is_invalid",
        lambda index_name: index_name == invalid_name,
    )

    module.upgrade()

    drop = f"DROP INDEX CONCURRENTLY IF EXISTS {invalid_name}"
    create = next(statement for statement in module._CONCURRENT_INDEX_STATEMENTS if invalid_name in statement)
    assert executed.count(drop) == 1
    assert executed.index(drop) < executed.index(create)
    assert sum(item.startswith("DROP INDEX CONCURRENTLY") for item in executed) == 1


class _ScalarResult:
    def __init__(self, value: bool | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> bool | None:
        return self.value


class _Bind:
    def __init__(self, value: bool | None) -> None:
        self.value = value
        self.calls: list[tuple[object, dict[str, str]]] = []

    def execute(self, statement, parameters):
        self.calls.append((statement, parameters))
        return _ScalarResult(self.value)


def test_invalid_index_detection_is_schema_scoped_and_catalog_backed(monkeypatch) -> None:
    module = load_migration_module()
    bind = _Bind(True)
    monkeypatch.setattr(module.op, "get_bind", lambda: bind)

    assert module._index_is_invalid("example_idx") is True
    assert len(bind.calls) == 1
    statement, parameters = bind.calls[0]
    sql = str(statement)
    assert "pg_catalog.pg_index" in sql
    assert "indisvalid" in sql
    assert "current_schema()" in sql
    assert parameters == {"index_name": "example_idx"}


def test_pending_confirmation_index_matches_actionable_invariants() -> None:
    module = load_migration_module()
    joined = "\n".join(module._CONCURRENT_INDEX_STATEMENTS)
    assert "status = 'needs_review'" in joined
    assert "confirmation_status = 'unconfirmed'" in joined
    assert "confirmation,status" in joined


def test_downgrade_drops_concurrent_indexes_before_claim_columns(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    monkeypatch.setattr(module.op, "get_context", lambda: _MigrationContext(executed))

    module.downgrade()

    joined = "\n".join(executed)
    assert joined.index("DROP INDEX CONCURRENTLY") < joined.index("DROP COLUMN IF EXISTS claim_token")
    assert "previous_status" not in joined
    assert "DROP CONSTRAINT IF EXISTS memories_status_check" in joined
