from __future__ import annotations

import pytest

from alicebot_api.telegram_channels import (
    TelegramWebhookValidationError,
    build_inbound_idempotency_key,
    extract_telegram_link_code,
    normalize_telegram_update,
    resolve_telegram_thread_key,
)


def test_build_inbound_idempotency_key_is_deterministic() -> None:
    assert build_inbound_idempotency_key(update_id=1001) == build_inbound_idempotency_key(update_id=1001)
    assert len(build_inbound_idempotency_key(update_id=1001)) == 64


def test_extract_telegram_link_code_supports_link_and_start_commands() -> None:
    assert extract_telegram_link_code("/link ABC12345", bot_username="alicebot") == "ABC12345"
    assert extract_telegram_link_code("/start zx90aa11", bot_username="alicebot") == "ZX90AA11"
    assert extract_telegram_link_code("/link@alicebot CODE2026", bot_username="alicebot") == "CODE2026"
    assert extract_telegram_link_code("/link@otherbot CODE2026", bot_username="alicebot") is None
    assert extract_telegram_link_code("hello", bot_username="alicebot") is None


def test_normalize_telegram_update_returns_stable_contract() -> None:
    normalized = normalize_telegram_update(
        {
            "update_id": 2026001,
            "message": {
                "message_id": 77,
                "date": 1710000000,
                "chat": {"id": 999001, "type": "private"},
                "from": {"id": 555001, "username": "builder"},
                "text": "/link p10s2abc",
            },
        },
        bot_username="alicebot",
    )

    assert normalized["provider_update_id"] == "2026001"
    assert normalized["provider_message_id"] == "77"
    assert normalized["external_chat_id"] == "999001"
    assert normalized["external_user_id"] == "555001"
    assert normalized["external_username"] == "builder"
    assert normalized["link_code"] == "P10S2ABC"
    assert normalized["idempotency_key"] == build_inbound_idempotency_key(update_id=2026001)
    assert resolve_telegram_thread_key(external_chat_id=normalized["external_chat_id"]) == "telegram-chat:999001"


def test_normalize_telegram_update_rejects_missing_required_fields() -> None:
    with pytest.raises(TelegramWebhookValidationError, match="requires integer update_id"):
        normalize_telegram_update({"message": {}}, bot_username="alicebot")

    with pytest.raises(TelegramWebhookValidationError, match="requires message object"):
        normalize_telegram_update({"update_id": 1}, bot_username="alicebot")

    with pytest.raises(TelegramWebhookValidationError, match="requires chat.id"):
        normalize_telegram_update(
            {
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "from": {"id": 2},
                },
            },
            bot_username="alicebot",
        )
