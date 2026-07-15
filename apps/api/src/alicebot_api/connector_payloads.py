from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any, TypedDict


class ConnectorPayloadValidationError(ValueError):
    """Raised when a raw connector item cannot be normalized."""


class NormalizedTelegramSourceItem(TypedDict):
    provider_update_id: str
    provider_message_id: str
    external_chat_id: str
    external_user_id: str
    external_username: str | None
    message_text: str
    sent_at: datetime
    idempotency_key: str
    normalized_payload: dict[str, Any]


def normalize_telegram_source_item(payload: dict[str, Any]) -> NormalizedTelegramSourceItem:
    """Normalize a Telegram export/poll item for raw memory-source ingestion.

    This helper intentionally knows nothing about channel linking, webhooks,
    outbound delivery, approvals, or hosted workspaces.
    """

    raw_update_id = payload.get("update_id")
    if not isinstance(raw_update_id, int):
        raise ConnectorPayloadValidationError("telegram source item requires integer update_id")
    raw_message = payload.get("message")
    if not isinstance(raw_message, dict):
        raise ConnectorPayloadValidationError("telegram source item requires message object")
    raw_chat = raw_message.get("chat")
    if not isinstance(raw_chat, dict) or "id" not in raw_chat:
        raise ConnectorPayloadValidationError("telegram source message requires chat.id")
    raw_from = raw_message.get("from")
    if not isinstance(raw_from, dict) or "id" not in raw_from:
        raise ConnectorPayloadValidationError("telegram source message requires from.id")
    raw_message_id = raw_message.get("message_id")
    if not isinstance(raw_message_id, int):
        raise ConnectorPayloadValidationError("telegram source message requires integer message_id")

    raw_text = raw_message.get("text")
    message_text = raw_text.strip() if isinstance(raw_text, str) else ""
    raw_date = raw_message.get("date")
    sent_at = (
        datetime.fromtimestamp(raw_date, tz=UTC)
        if isinstance(raw_date, int)
        else datetime.now(tz=UTC)
    )
    external_chat_id = str(raw_chat["id"])
    external_user_id = str(raw_from["id"])
    username = raw_from.get("username")
    external_username = username.strip() if isinstance(username, str) and username.strip() else None
    idempotency_key = hashlib.sha256(f"telegram:update:{raw_update_id}".encode()).hexdigest()
    normalized_payload = {
        "update_id": raw_update_id,
        "message_id": raw_message_id,
        "chat": {"id": external_chat_id, "type": raw_chat.get("type")},
        "from": {"id": external_user_id, "username": external_username},
        "text": message_text,
        "received_kind": "telegram_source_ingest",
    }
    return {
        "provider_update_id": str(raw_update_id),
        "provider_message_id": str(raw_message_id),
        "external_chat_id": external_chat_id,
        "external_user_id": external_user_id,
        "external_username": external_username,
        "message_text": message_text,
        "sent_at": sent_at,
        "idempotency_key": idempotency_key,
        "normalized_payload": normalized_payload,
    }


__all__ = [
    "ConnectorPayloadValidationError",
    "NormalizedTelegramSourceItem",
    "normalize_telegram_source_item",
]
