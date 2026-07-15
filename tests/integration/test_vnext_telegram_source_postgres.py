from __future__ import annotations

from uuid import uuid4

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_connectors import VNextConnectorService
from alicebot_api.vnext_store import PostgresVNextStore


def _telegram_update(update_id: int, *, chat_id: int) -> dict[str, object]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id + 100,
            "date": 1_778_400_000,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": 1001, "username": "operator"},
            "text": "Fact: Postgres preserves allowlisted Telegram source evidence.",
        },
    }


def test_postgres_telegram_raw_source_preserves_allowlist_cursor_and_dedupe(
    migrated_database_urls: dict[str, str],
) -> None:
    user_id = uuid4()
    with user_connection(migrated_database_urls["app"], user_id) as conn:
        ContinuityStore(conn).create_user(user_id, "telegram-source@example.com", "Telegram source")
        store = PostgresVNextStore(conn)
        service = VNextConnectorService(store)

        first = service.sync_telegram_updates(
            [_telegram_update(70, chat_id=999001), _telegram_update(71, chat_id=777)],
            allowed_chat_ids=("999001",),
        )
        replay = service.sync_telegram_updates(
            [_telegram_update(70, chat_id=999001)],
            allowed_chat_ids=("999001",),
        )

        assert first.imported_count == 1
        assert first.skipped_count == 1
        assert first.sync_cursor == "71"
        assert replay.imported_count == 0
        assert replay.skipped_count == 1
        state = store.get_connector_state("telegram")
        assert state is not None
        assert state["cursor_value"] == "71"
        source = store.get_source(first.source_ids[0])
        assert source is not None
        assert source["source_type"] == "telegram_message"
        assert source["metadata_json"]["chat_id"] == "999001"
        assert any(event["event_type"] == "connector.item_rejected" for event in store.list_events())
