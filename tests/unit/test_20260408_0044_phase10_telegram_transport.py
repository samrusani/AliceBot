from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260408_0044_phase10_telegram_transport"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_upgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert executed == [
        *module._UPGRADE_STATEMENTS,
        *module._UPGRADE_GRANT_STATEMENTS,
    ]


def test_downgrade_executes_expected_statements_in_order(monkeypatch) -> None:
    module = load_migration_module()
    executed: list[str] = []

    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == list(module._DOWNGRADE_STATEMENTS)


def test_migration_mentions_phase10_s2_channel_tables() -> None:
    module = load_migration_module()

    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)
    for table_name in (
        "channel_identities",
        "channel_link_challenges",
        "channel_messages",
        "channel_threads",
        "channel_delivery_receipts",
        "chat_intents",
    ):
        assert table_name in joined_upgrade_sql


def test_migration_hashes_challenge_tokens_and_enforces_webhook_idempotency() -> None:
    module = load_migration_module()
    joined_upgrade_sql = "\n".join(module._UPGRADE_STATEMENTS)

    assert "challenge_token_hash text NOT NULL UNIQUE" in joined_upgrade_sql
    assert "challenge_token text NOT NULL UNIQUE" not in joined_upgrade_sql
    assert "UNIQUE (channel_type, direction, idempotency_key)" in joined_upgrade_sql
    assert "ON channel_identities (channel_type, external_chat_id)" in joined_upgrade_sql
