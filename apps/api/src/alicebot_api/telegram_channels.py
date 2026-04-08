from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
import string
from typing import Any, TypedDict
from uuid import UUID

from psycopg.types.json import Jsonb

from alicebot_api.hosted_auth import generate_token, hash_token, utc_now


TELEGRAM_CHANNEL_TYPE = "telegram"

_LINK_PATTERN = re.compile(r"^/link(?:@(?P<mention>[A-Za-z0-9_]+))?\s+(?P<code>[A-Za-z0-9]{6,32})$")
_START_PATTERN = re.compile(r"^/start\s+(?P<code>[A-Za-z0-9]{6,32})$")


class TelegramLinkTokenInvalidError(ValueError):
    """Raised when a Telegram link token is invalid or already consumed."""


class TelegramLinkTokenExpiredError(ValueError):
    """Raised when a Telegram link token has expired."""


class TelegramLinkPendingError(RuntimeError):
    """Raised when link confirmation has not yet been observed via webhook."""


class TelegramIdentityConflictError(RuntimeError):
    """Raised when a Telegram chat is already linked to a different workspace."""


class TelegramIdentityNotFoundError(LookupError):
    """Raised when a linked Telegram identity is not visible for the workspace."""


class TelegramMessageNotFoundError(LookupError):
    """Raised when a Telegram message is not visible for dispatch."""


class TelegramRoutingError(RuntimeError):
    """Raised when Telegram routing cannot be resolved deterministically."""


class TelegramWebhookValidationError(ValueError):
    """Raised when incoming webhook payload is missing required Telegram fields."""


class TelegramChannelIdentityRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID
    channel_type: str
    external_user_id: str
    external_chat_id: str
    external_username: str | None
    status: str
    linked_at: datetime
    unlinked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TelegramChannelLinkChallengeRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID
    channel_type: str
    challenge_token_hash: str
    link_code: str
    status: str
    expires_at: datetime
    confirmed_at: datetime | None
    channel_identity_id: UUID | None
    created_at: datetime


class IssuedTelegramChannelLinkChallengeRow(TelegramChannelLinkChallengeRow):
    challenge_token: str


class TelegramChannelThreadRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    external_thread_key: str
    channel_identity_id: UUID | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TelegramChannelMessageRow(TypedDict):
    id: UUID
    workspace_id: UUID | None
    channel_thread_id: UUID | None
    channel_identity_id: UUID | None
    channel_type: str
    direction: str
    provider_update_id: str | None
    provider_message_id: str | None
    external_chat_id: str | None
    external_user_id: str | None
    message_text: str | None
    normalized_payload: dict[str, Any]
    route_status: str
    idempotency_key: str
    created_at: datetime
    received_at: datetime


class TelegramDeliveryReceiptRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_message_id: UUID
    channel_type: str
    status: str
    provider_receipt_id: str | None
    failure_code: str | None
    failure_detail: str | None
    scheduled_job_id: UUID | None
    scheduler_job_kind: str | None
    scheduled_for: datetime | None
    schedule_slot: str | None
    notification_policy: dict[str, Any]
    rollout_flag_state: str
    support_evidence: dict[str, Any]
    rate_limit_evidence: dict[str, Any]
    incident_evidence: dict[str, Any]
    recorded_at: datetime
    created_at: datetime


class NormalizedTelegramInboundMessage(TypedDict):
    provider_update_id: str
    provider_message_id: str
    external_chat_id: str
    external_user_id: str
    external_username: str | None
    message_text: str
    sent_at: datetime
    link_code: str | None
    idempotency_key: str
    normalized_payload: dict[str, Any]


class TelegramWebhookIngestResult(TypedDict):
    duplicate: bool
    route_status: str
    link_status: str | None
    unknown_chat_routing: bool
    message: TelegramChannelMessageRow
    thread: TelegramChannelThreadRow | None


def build_inbound_idempotency_key(*, update_id: int) -> str:
    payload = f"telegram:update:{update_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_telegram_thread_key(*, external_chat_id: str) -> str:
    return f"telegram-chat:{external_chat_id}"


def extract_telegram_link_code(
    text: str,
    *,
    bot_username: str | None,
) -> str | None:
    normalized_text = text.strip()
    if normalized_text == "":
        return None

    for pattern in (_LINK_PATTERN, _START_PATTERN):
        match = pattern.match(normalized_text)
        if match is None:
            continue
        mention = match.groupdict().get("mention")
        if mention is not None and bot_username and mention.lower() != bot_username.lower():
            return None
        code = match.group("code").strip().upper()
        if code == "":
            return None
        return code

    return None


def normalize_telegram_update(
    payload: dict[str, Any],
    *,
    bot_username: str | None,
) -> NormalizedTelegramInboundMessage:
    raw_update_id = payload.get("update_id")
    if not isinstance(raw_update_id, int):
        raise TelegramWebhookValidationError("telegram webhook payload requires integer update_id")

    raw_message = payload.get("message")
    if not isinstance(raw_message, dict):
        raise TelegramWebhookValidationError("telegram webhook payload requires message object")

    raw_chat = raw_message.get("chat")
    if not isinstance(raw_chat, dict) or "id" not in raw_chat:
        raise TelegramWebhookValidationError("telegram webhook message requires chat.id")

    raw_from = raw_message.get("from")
    if not isinstance(raw_from, dict) or "id" not in raw_from:
        raise TelegramWebhookValidationError("telegram webhook message requires from.id")

    raw_message_id = raw_message.get("message_id")
    if not isinstance(raw_message_id, int):
        raise TelegramWebhookValidationError("telegram webhook message requires integer message_id")

    text = raw_message.get("text")
    normalized_text = text.strip() if isinstance(text, str) else ""

    sent_at: datetime
    raw_date = raw_message.get("date")
    if isinstance(raw_date, int):
        sent_at = datetime.fromtimestamp(raw_date, tz=timezone.utc)
    else:
        sent_at = utc_now()

    external_chat_id = str(raw_chat["id"])
    external_user_id = str(raw_from["id"])
    username = raw_from.get("username")
    external_username = username.strip() if isinstance(username, str) and username.strip() else None

    link_code = extract_telegram_link_code(normalized_text, bot_username=bot_username)

    normalized_payload = {
        "update_id": raw_update_id,
        "message_id": raw_message_id,
        "chat": {
            "id": external_chat_id,
            "type": raw_chat.get("type"),
        },
        "from": {
            "id": external_user_id,
            "username": external_username,
        },
        "text": normalized_text,
        "received_kind": "telegram_webhook",
        "link_code": link_code,
    }

    return {
        "provider_update_id": str(raw_update_id),
        "provider_message_id": str(raw_message_id),
        "external_chat_id": external_chat_id,
        "external_user_id": external_user_id,
        "external_username": external_username,
        "message_text": normalized_text,
        "sent_at": sent_at,
        "link_code": link_code,
        "idempotency_key": build_inbound_idempotency_key(update_id=raw_update_id),
        "normalized_payload": normalized_payload,
    }


def _generate_link_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def start_telegram_link_challenge(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    ttl_seconds: int,
) -> IssuedTelegramChannelLinkChallengeRow:
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE channel_link_challenges
            SET status = 'expired'
            WHERE user_account_id = %s
              AND workspace_id = %s
              AND channel_type = %s
              AND status = 'pending'
              AND expires_at > %s
            """,
            (user_account_id, workspace_id, TELEGRAM_CHANNEL_TYPE, now),
        )

        challenge_token = generate_token()
        challenge_token_hash = hash_token(challenge_token)
        link_code = _generate_link_code()
        expires_at = now + timedelta(seconds=ttl_seconds)

        cur.execute(
            """
            INSERT INTO channel_link_challenges (
              user_account_id,
              workspace_id,
              channel_type,
              challenge_token_hash,
              link_code,
              status,
              expires_at
            )
            VALUES (%s, %s, %s, %s, %s, 'pending', %s)
            RETURNING id, user_account_id, workspace_id, channel_type, challenge_token_hash,
                      link_code, status, expires_at, confirmed_at, channel_identity_id, created_at
            """,
            (
                user_account_id,
                workspace_id,
                TELEGRAM_CHANNEL_TYPE,
                challenge_token_hash,
                link_code,
                expires_at,
            ),
        )
        challenge = cur.fetchone()

    if challenge is None:
        raise RuntimeError("failed to create telegram link challenge")

    challenge["challenge_token"] = challenge_token
    return challenge


def _lookup_link_challenge_for_update(
    conn,
    *,
    user_account_id: UUID,
    challenge_token: str,
) -> TelegramChannelLinkChallengeRow | None:
    token = challenge_token.strip()
    if token == "":
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, channel_type, challenge_token_hash, link_code,
                   status, expires_at, confirmed_at, channel_identity_id, created_at
            FROM channel_link_challenges
            WHERE user_account_id = %s
              AND channel_type = %s
              AND challenge_token_hash = %s
            FOR UPDATE
            """,
            (user_account_id, TELEGRAM_CHANNEL_TYPE, hash_token(token)),
        )
        return cur.fetchone()


def _fetch_channel_identity_by_id(conn, *, channel_identity_id: UUID) -> TelegramChannelIdentityRow | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, channel_type, external_user_id, external_chat_id,
                   external_username, status, linked_at, unlinked_at, created_at, updated_at
            FROM channel_identities
            WHERE id = %s
            """,
            (channel_identity_id,),
        )
        return cur.fetchone()


def confirm_telegram_link_challenge(
    conn,
    *,
    user_account_id: UUID,
    challenge_token: str,
) -> tuple[TelegramChannelLinkChallengeRow, TelegramChannelIdentityRow]:
    now = utc_now()
    challenge = _lookup_link_challenge_for_update(
        conn,
        user_account_id=user_account_id,
        challenge_token=challenge_token,
    )
    if challenge is None:
        raise TelegramLinkTokenInvalidError("telegram link token is invalid")

    if challenge["status"] == "confirmed" and challenge["channel_identity_id"] is not None:
        identity = _fetch_channel_identity_by_id(conn, channel_identity_id=challenge["channel_identity_id"])
        if identity is not None:
            return challenge, identity

    if challenge["status"] != "pending":
        raise TelegramLinkTokenInvalidError("telegram link token is no longer valid")

    if challenge["expires_at"] <= now:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE channel_link_challenges
                SET status = 'expired'
                WHERE id = %s
                """,
                (challenge["id"],),
            )
        raise TelegramLinkTokenExpiredError("telegram link token has expired")

    if challenge["channel_identity_id"] is None:
        raise TelegramLinkPendingError("telegram link is pending webhook confirmation")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE channel_link_challenges
            SET status = 'confirmed',
                confirmed_at = COALESCE(confirmed_at, %s)
            WHERE id = %s
            RETURNING id, user_account_id, workspace_id, channel_type, challenge_token_hash,
                      link_code, status, expires_at, confirmed_at, channel_identity_id, created_at
            """,
            (now, challenge["id"]),
        )
        updated = cur.fetchone()

    if updated is None or updated["channel_identity_id"] is None:
        raise TelegramLinkPendingError("telegram link is pending webhook confirmation")

    identity = _fetch_channel_identity_by_id(conn, channel_identity_id=updated["channel_identity_id"])
    if identity is None:
        raise TelegramLinkPendingError("telegram link is pending webhook confirmation")

    return updated, identity


def _upsert_linked_identity(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    external_chat_id: str,
    external_user_id: str,
    external_username: str | None,
) -> TelegramChannelIdentityRow:
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, channel_type, external_user_id, external_chat_id,
                   external_username, status, linked_at, unlinked_at, created_at, updated_at
            FROM channel_identities
            WHERE channel_type = %s
              AND external_chat_id = %s
              AND status = 'linked'
            ORDER BY updated_at DESC, created_at DESC, id DESC
            LIMIT 1
            FOR UPDATE
            """,
            (TELEGRAM_CHANNEL_TYPE, external_chat_id),
        )
        linked = cur.fetchone()

        if linked is not None:
            if linked["workspace_id"] != workspace_id:
                raise TelegramIdentityConflictError(
                    "telegram chat is already linked to another workspace"
                )

            cur.execute(
                """
                UPDATE channel_identities
                SET user_account_id = %s,
                    external_user_id = %s,
                    external_username = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING id, user_account_id, workspace_id, channel_type, external_user_id,
                          external_chat_id, external_username, status, linked_at, unlinked_at,
                          created_at, updated_at
                """,
                (
                    user_account_id,
                    external_user_id,
                    external_username,
                    now,
                    linked["id"],
                ),
            )
            refreshed = cur.fetchone()
            if refreshed is None:
                raise RuntimeError("failed to refresh linked telegram identity")
            return refreshed

        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, channel_type, external_user_id, external_chat_id,
                   external_username, status, linked_at, unlinked_at, created_at, updated_at
            FROM channel_identities
            WHERE workspace_id = %s
              AND channel_type = %s
              AND external_chat_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            FOR UPDATE
            """,
            (workspace_id, TELEGRAM_CHANNEL_TYPE, external_chat_id),
        )
        prior = cur.fetchone()

        if prior is not None:
            cur.execute(
                """
                UPDATE channel_identities
                SET user_account_id = %s,
                    external_user_id = %s,
                    external_username = %s,
                    status = 'linked',
                    linked_at = %s,
                    unlinked_at = NULL,
                    updated_at = %s
                WHERE id = %s
                RETURNING id, user_account_id, workspace_id, channel_type, external_user_id,
                          external_chat_id, external_username, status, linked_at, unlinked_at,
                          created_at, updated_at
                """,
                (
                    user_account_id,
                    external_user_id,
                    external_username,
                    now,
                    now,
                    prior["id"],
                ),
            )
            relinked = cur.fetchone()
            if relinked is None:
                raise RuntimeError("failed to relink telegram identity")
            return relinked

        cur.execute(
            """
            INSERT INTO channel_identities (
              user_account_id,
              workspace_id,
              channel_type,
              external_user_id,
              external_chat_id,
              external_username,
              status,
              linked_at,
              updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'linked', %s, %s)
            RETURNING id, user_account_id, workspace_id, channel_type, external_user_id,
                      external_chat_id, external_username, status, linked_at, unlinked_at,
                      created_at, updated_at
            """,
            (
                user_account_id,
                workspace_id,
                TELEGRAM_CHANNEL_TYPE,
                external_user_id,
                external_chat_id,
                external_username,
                now,
                now,
            ),
        )
        inserted = cur.fetchone()

    if inserted is None:
        raise RuntimeError("failed to insert linked telegram identity")
    return inserted


def _apply_link_code_if_present(
    conn,
    *,
    normalized: NormalizedTelegramInboundMessage,
) -> tuple[str | None, TelegramChannelIdentityRow | None]:
    link_code = normalized["link_code"]
    if link_code is None:
        return None, None

    now = utc_now()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, channel_type, challenge_token_hash, link_code,
                   status, expires_at, confirmed_at, channel_identity_id, created_at
            FROM channel_link_challenges
            WHERE channel_type = %s
              AND link_code = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            FOR UPDATE
            """,
            (TELEGRAM_CHANNEL_TYPE, link_code),
        )
        challenge = cur.fetchone()

    if challenge is None:
        return "invalid_link_code", None

    if challenge["status"] != "pending":
        if challenge["status"] == "confirmed" and challenge["channel_identity_id"] is not None:
            identity = _fetch_channel_identity_by_id(
                conn,
                channel_identity_id=challenge["channel_identity_id"],
            )
            if (
                identity is not None
                and identity["status"] == "linked"
                and identity["external_chat_id"] == normalized["external_chat_id"]
            ):
                return "already_confirmed", identity
            return "invalid_link_code", None
        return "invalid_link_code", None

    if challenge["expires_at"] <= now:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE channel_link_challenges
                SET status = 'expired'
                WHERE id = %s
                """,
                (challenge["id"],),
            )
        return "expired_link_code", None

    try:
        identity = _upsert_linked_identity(
            conn,
            user_account_id=challenge["user_account_id"],
            workspace_id=challenge["workspace_id"],
            external_chat_id=normalized["external_chat_id"],
            external_user_id=normalized["external_user_id"],
            external_username=normalized["external_username"],
        )
    except TelegramIdentityConflictError:
        return "identity_conflict", None

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE channel_link_challenges
            SET status = 'confirmed',
                confirmed_at = %s,
                channel_identity_id = %s
            WHERE id = %s
            """,
            (now, identity["id"], challenge["id"]),
        )

    return "confirmed", identity


def _resolve_workspace_and_identity_for_inbound(
    conn,
    *,
    normalized: NormalizedTelegramInboundMessage,
    linked_identity: TelegramChannelIdentityRow | None,
) -> tuple[UUID | None, UUID | None]:
    if linked_identity is not None:
        return linked_identity["workspace_id"], linked_identity["id"]

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, workspace_id
            FROM channel_identities
            WHERE channel_type = %s
              AND external_chat_id = %s
              AND status = 'linked'
            ORDER BY updated_at DESC, created_at DESC, id DESC
            LIMIT 1
            """,
            (TELEGRAM_CHANNEL_TYPE, normalized["external_chat_id"]),
        )
        row = cur.fetchone()

    if row is None:
        return None, None
    return row["workspace_id"], row["id"]


def _ensure_channel_thread(
    conn,
    *,
    workspace_id: UUID,
    channel_identity_id: UUID | None,
    external_chat_id: str,
    sent_at: datetime,
) -> TelegramChannelThreadRow:
    external_thread_key = resolve_telegram_thread_key(external_chat_id=external_chat_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channel_threads (
              workspace_id,
              channel_type,
              external_thread_key,
              channel_identity_id,
              last_message_at,
              updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (workspace_id, channel_type, external_thread_key) DO UPDATE
            SET channel_identity_id = COALESCE(EXCLUDED.channel_identity_id, channel_threads.channel_identity_id),
                last_message_at = EXCLUDED.last_message_at,
                updated_at = EXCLUDED.updated_at
            RETURNING id, workspace_id, channel_type, external_thread_key,
                      channel_identity_id, last_message_at, created_at, updated_at
            """,
            (
                workspace_id,
                TELEGRAM_CHANNEL_TYPE,
                external_thread_key,
                channel_identity_id,
                sent_at,
                utc_now(),
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to resolve telegram thread")
    return row


def _insert_or_get_channel_message(
    conn,
    *,
    workspace_id: UUID | None,
    channel_thread_id: UUID | None,
    channel_identity_id: UUID | None,
    normalized: NormalizedTelegramInboundMessage,
    route_status: str,
) -> tuple[TelegramChannelMessageRow, bool]:
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channel_messages (
              workspace_id,
              channel_thread_id,
              channel_identity_id,
              channel_type,
              direction,
              provider_update_id,
              provider_message_id,
              external_chat_id,
              external_user_id,
              message_text,
              normalized_payload,
              route_status,
              idempotency_key,
              received_at
            )
            VALUES (%s, %s, %s, %s, 'inbound', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (channel_type, direction, idempotency_key) DO NOTHING
            RETURNING id, workspace_id, channel_thread_id, channel_identity_id,
                      channel_type, direction, provider_update_id, provider_message_id,
                      external_chat_id, external_user_id, message_text,
                      normalized_payload, route_status, idempotency_key, created_at, received_at
            """,
            (
                workspace_id,
                channel_thread_id,
                channel_identity_id,
                TELEGRAM_CHANNEL_TYPE,
                normalized["provider_update_id"],
                normalized["provider_message_id"],
                normalized["external_chat_id"],
                normalized["external_user_id"],
                normalized["message_text"],
                Jsonb(normalized["normalized_payload"]),
                route_status,
                normalized["idempotency_key"],
                now,
            ),
        )
        inserted = cur.fetchone()

        if inserted is not None:
            return inserted, False

        cur.execute(
            """
            SELECT id, workspace_id, channel_thread_id, channel_identity_id, channel_type, direction,
                   provider_update_id, provider_message_id, external_chat_id, external_user_id,
                   message_text, normalized_payload, route_status, idempotency_key,
                   created_at, received_at
            FROM channel_messages
            WHERE channel_type = %s
              AND direction = 'inbound'
              AND idempotency_key = %s
            LIMIT 1
            """,
            (TELEGRAM_CHANNEL_TYPE, normalized["idempotency_key"]),
        )
        existing = cur.fetchone()

    if existing is None:
        raise RuntimeError("failed to resolve idempotent telegram channel message")
    return existing, True


def ingest_telegram_webhook(
    conn,
    *,
    payload: dict[str, Any],
    bot_username: str | None,
) -> TelegramWebhookIngestResult:
    normalized = normalize_telegram_update(payload, bot_username=bot_username)

    link_status, linked_identity = _apply_link_code_if_present(conn, normalized=normalized)
    workspace_id, channel_identity_id = _resolve_workspace_and_identity_for_inbound(
        conn,
        normalized=normalized,
        linked_identity=linked_identity,
    )

    route_status = "resolved" if workspace_id is not None else "unresolved"
    thread: TelegramChannelThreadRow | None = None

    if workspace_id is not None:
        thread = _ensure_channel_thread(
            conn,
            workspace_id=workspace_id,
            channel_identity_id=channel_identity_id,
            external_chat_id=normalized["external_chat_id"],
            sent_at=normalized["sent_at"],
        )

    message, duplicate = _insert_or_get_channel_message(
        conn,
        workspace_id=workspace_id,
        channel_thread_id=None if thread is None else thread["id"],
        channel_identity_id=channel_identity_id,
        normalized=normalized,
        route_status=route_status,
    )

    if not duplicate and workspace_id is not None:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_intents (
                  workspace_id,
                  channel_message_id,
                  channel_thread_id,
                  intent_kind,
                  status
                )
                VALUES (%s, %s, %s, 'inbound_message', 'recorded')
                ON CONFLICT (channel_message_id, intent_kind) DO NOTHING
                """,
                (
                    workspace_id,
                    message["id"],
                    None if thread is None else thread["id"],
                ),
            )

    return {
        "duplicate": duplicate,
        "route_status": route_status,
        "link_status": link_status,
        "unknown_chat_routing": workspace_id is None,
        "message": message,
        "thread": thread,
    }


def list_workspace_telegram_messages(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    limit: int,
) -> list[TelegramChannelMessageRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id,
                   m.workspace_id,
                   m.channel_thread_id,
                   m.channel_identity_id,
                   m.channel_type,
                   m.direction,
                   m.provider_update_id,
                   m.provider_message_id,
                   m.external_chat_id,
                   m.external_user_id,
                   m.message_text,
                   m.normalized_payload,
                   m.route_status,
                   m.idempotency_key,
                   m.created_at,
                   m.received_at
            FROM channel_messages AS m
            JOIN workspace_members AS wm
              ON wm.workspace_id = m.workspace_id
            WHERE m.channel_type = %s
              AND m.workspace_id = %s
              AND wm.user_account_id = %s
            ORDER BY m.created_at DESC, m.id DESC
            LIMIT %s
            """,
            (TELEGRAM_CHANNEL_TYPE, workspace_id, user_account_id, limit),
        )
        rows = cur.fetchall()

    return rows


def list_workspace_telegram_threads(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    limit: int,
) -> list[TelegramChannelThreadRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.id,
                   t.workspace_id,
                   t.channel_type,
                   t.external_thread_key,
                   t.channel_identity_id,
                   t.last_message_at,
                   t.created_at,
                   t.updated_at
            FROM channel_threads AS t
            JOIN workspace_members AS wm
              ON wm.workspace_id = t.workspace_id
            WHERE t.channel_type = %s
              AND t.workspace_id = %s
              AND wm.user_account_id = %s
            ORDER BY COALESCE(t.last_message_at, t.created_at) DESC, t.id DESC
            LIMIT %s
            """,
            (TELEGRAM_CHANNEL_TYPE, workspace_id, user_account_id, limit),
        )
        rows = cur.fetchall()

    return rows


def _get_latest_linked_identity(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
) -> TelegramChannelIdentityRow | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, channel_type, external_user_id, external_chat_id,
                   external_username, status, linked_at, unlinked_at, created_at, updated_at
            FROM channel_identities
            WHERE user_account_id = %s
              AND workspace_id = %s
              AND channel_type = %s
              AND status = 'linked'
            ORDER BY updated_at DESC, created_at DESC, id DESC
            LIMIT 1
            """,
            (user_account_id, workspace_id, TELEGRAM_CHANNEL_TYPE),
        )
        return cur.fetchone()


def get_latest_linked_telegram_identity(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
) -> TelegramChannelIdentityRow | None:
    return _get_latest_linked_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )


def get_telegram_link_status(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
) -> dict[str, Any]:
    identity = _get_latest_linked_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, channel_type, challenge_token_hash, link_code,
                   status, expires_at, confirmed_at, channel_identity_id, created_at
            FROM channel_link_challenges
            WHERE user_account_id = %s
              AND workspace_id = %s
              AND channel_type = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_account_id, workspace_id, TELEGRAM_CHANNEL_TYPE),
        )
        latest_challenge = cur.fetchone()

        cur.execute(
            """
            SELECT id, route_status, direction, created_at
            FROM channel_messages
            WHERE workspace_id = %s
              AND channel_type = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (workspace_id, TELEGRAM_CHANNEL_TYPE),
        )
        recent_message = cur.fetchone()

    return {
        "workspace_id": str(workspace_id),
        "channel_type": TELEGRAM_CHANNEL_TYPE,
        "linked": identity is not None,
        "identity": None if identity is None else serialize_channel_identity(identity),
        "latest_challenge": None
        if latest_challenge is None
        else serialize_channel_link_challenge(latest_challenge, include_token=False),
        "recent_transport": None
        if recent_message is None
        else {
            "message_id": str(recent_message["id"]),
            "direction": recent_message["direction"],
            "route_status": recent_message["route_status"],
            "observed_at": recent_message["created_at"].isoformat(),
        },
    }


def unlink_telegram_identity(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
) -> TelegramChannelIdentityRow:
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE channel_identities
            SET status = 'unlinked',
                unlinked_at = %s,
                updated_at = %s
            WHERE id = (
                SELECT id
                FROM channel_identities
                WHERE user_account_id = %s
                  AND workspace_id = %s
                  AND channel_type = %s
                  AND status = 'linked'
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT 1
            )
            RETURNING id, user_account_id, workspace_id, channel_type, external_user_id,
                      external_chat_id, external_username, status, linked_at, unlinked_at,
                      created_at, updated_at
            """,
            (now, now, user_account_id, workspace_id, TELEGRAM_CHANNEL_TYPE),
        )
        identity = cur.fetchone()

        if identity is None:
            raise TelegramIdentityNotFoundError("telegram channel is not linked for this workspace")

        cur.execute(
            """
            UPDATE channel_link_challenges
            SET status = 'cancelled'
            WHERE user_account_id = %s
              AND workspace_id = %s
              AND channel_type = %s
              AND status = 'pending'
            """,
            (user_account_id, workspace_id, TELEGRAM_CHANNEL_TYPE),
        )

    return identity


def dispatch_telegram_message(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    source_message_id: UUID,
    text: str,
    dispatch_idempotency_key: str | None,
    bot_token: str,
    rollout_flag_state: str = "enabled",
    support_evidence: dict[str, Any] | None = None,
    rate_limit_evidence: dict[str, Any] | None = None,
    incident_evidence: dict[str, Any] | None = None,
) -> tuple[TelegramChannelMessageRow, TelegramDeliveryReceiptRow]:
    normalized_text = text.strip()
    if normalized_text == "":
        raise ValueError("dispatch text is required")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id,
                   m.workspace_id,
                   m.channel_thread_id,
                   m.channel_identity_id,
                   m.channel_type,
                   m.direction,
                   m.provider_update_id,
                   m.provider_message_id,
                   m.external_chat_id,
                   m.external_user_id,
                   m.message_text,
                   m.normalized_payload,
                   m.route_status,
                   m.idempotency_key,
                   m.created_at,
                   m.received_at
            FROM channel_messages AS m
            JOIN workspace_members AS wm
              ON wm.workspace_id = m.workspace_id
            WHERE m.id = %s
              AND wm.user_account_id = %s
              AND m.workspace_id = %s
              AND m.channel_type = %s
            LIMIT 1
            """,
            (source_message_id, user_account_id, workspace_id, TELEGRAM_CHANNEL_TYPE),
        )
        source = cur.fetchone()

    if source is None:
        raise TelegramMessageNotFoundError("telegram source message was not found")

    if source["route_status"] != "resolved":
        raise TelegramRoutingError("telegram source message does not have resolved routing")

    external_chat_id = source["external_chat_id"]
    if external_chat_id is None:
        raise TelegramRoutingError("telegram source message is missing external chat id")

    resolved_idempotency_key = dispatch_idempotency_key
    if resolved_idempotency_key is None:
        resolved_idempotency_key = hashlib.sha256(
            f"telegram:dispatch:{source_message_id}:{normalized_text}".encode("utf-8")
        ).hexdigest()

    provider_message_id = f"simulated:{secrets.token_hex(10)}"
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channel_messages (
              workspace_id,
              channel_thread_id,
              channel_identity_id,
              channel_type,
              direction,
              provider_update_id,
              provider_message_id,
              external_chat_id,
              external_user_id,
              message_text,
              normalized_payload,
              route_status,
              idempotency_key,
              received_at
            )
            VALUES (%s, %s, %s, %s, 'outbound', NULL, %s, %s, %s, %s, %s, 'resolved', %s, %s)
            ON CONFLICT (channel_type, direction, idempotency_key) DO NOTHING
            RETURNING id, workspace_id, channel_thread_id, channel_identity_id,
                      channel_type, direction, provider_update_id, provider_message_id,
                      external_chat_id, external_user_id, message_text,
                      normalized_payload, route_status, idempotency_key, created_at, received_at
            """,
            (
                workspace_id,
                source["channel_thread_id"],
                source["channel_identity_id"],
                TELEGRAM_CHANNEL_TYPE,
                provider_message_id,
                external_chat_id,
                source["external_user_id"],
                normalized_text,
                Jsonb(
                    {
                        "dispatch": {
                            "source_message_id": str(source_message_id),
                            "mode": "simulated" if bot_token.strip() == "" else "deterministic_failure",
                        }
                    }
                ),
                resolved_idempotency_key,
                now,
            ),
        )
        outbound = cur.fetchone()

        if outbound is None:
            cur.execute(
                """
                SELECT id, workspace_id, channel_thread_id, channel_identity_id, channel_type,
                       direction, provider_update_id, provider_message_id, external_chat_id,
                       external_user_id, message_text, normalized_payload, route_status,
                       idempotency_key, created_at, received_at
                FROM channel_messages
                WHERE workspace_id = %s
                  AND channel_type = %s
                  AND direction = 'outbound'
                  AND idempotency_key = %s
                LIMIT 1
                """,
                (workspace_id, TELEGRAM_CHANNEL_TYPE, resolved_idempotency_key),
            )
            outbound = cur.fetchone()

    if outbound is None:
        raise RuntimeError("failed to create outbound telegram message")

    receipt_status = "simulated"
    failure_code: str | None = None
    failure_detail: str | None = None
    provider_receipt_id: str | None = outbound["provider_message_id"]

    if bot_token.strip() != "":
        receipt_status = "failed"
        failure_code = "telegram_transport_not_enabled"
        failure_detail = "live telegram dispatch is not enabled in this environment"
        provider_receipt_id = None

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channel_delivery_receipts (
              workspace_id,
              channel_message_id,
              channel_type,
              status,
              provider_receipt_id,
              failure_code,
              failure_detail,
              rollout_flag_state,
              support_evidence,
              rate_limit_evidence,
              incident_evidence,
              recorded_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (channel_message_id) DO UPDATE
            SET status = EXCLUDED.status,
                provider_receipt_id = EXCLUDED.provider_receipt_id,
                failure_code = EXCLUDED.failure_code,
                failure_detail = EXCLUDED.failure_detail,
                rollout_flag_state = EXCLUDED.rollout_flag_state,
                support_evidence = EXCLUDED.support_evidence,
                rate_limit_evidence = EXCLUDED.rate_limit_evidence,
                incident_evidence = EXCLUDED.incident_evidence,
                recorded_at = EXCLUDED.recorded_at
            RETURNING id, workspace_id, channel_message_id, channel_type,
                      status, provider_receipt_id, failure_code, failure_detail,
                      scheduled_job_id, scheduler_job_kind, scheduled_for, schedule_slot,
                      notification_policy, rollout_flag_state, support_evidence,
                      rate_limit_evidence, incident_evidence, recorded_at, created_at
            """,
            (
                workspace_id,
                outbound["id"],
                TELEGRAM_CHANNEL_TYPE,
                receipt_status,
                provider_receipt_id,
                failure_code,
                failure_detail,
                rollout_flag_state,
                Jsonb(support_evidence or {}),
                Jsonb(rate_limit_evidence or {}),
                Jsonb(incident_evidence or {}),
                utc_now(),
            ),
        )
        receipt = cur.fetchone()

    if receipt is None:
        raise RuntimeError("failed to persist telegram delivery receipt")

    return outbound, receipt


def dispatch_telegram_workspace_message(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    text: str,
    dispatch_idempotency_key: str,
    bot_token: str,
    dispatch_payload: dict[str, Any] | None = None,
    receipt_status_override: str | None = None,
    failure_code_override: str | None = None,
    failure_detail_override: str | None = None,
    scheduled_job_id: UUID | None = None,
    scheduler_job_kind: str | None = None,
    scheduled_for: datetime | None = None,
    schedule_slot: str | None = None,
    notification_policy: dict[str, Any] | None = None,
    rollout_flag_state: str = "enabled",
    support_evidence: dict[str, Any] | None = None,
    rate_limit_evidence: dict[str, Any] | None = None,
    incident_evidence: dict[str, Any] | None = None,
) -> tuple[TelegramChannelMessageRow, TelegramDeliveryReceiptRow]:
    normalized_text = text.strip()
    if normalized_text == "":
        raise ValueError("dispatch text is required")

    resolved_idempotency_key = dispatch_idempotency_key.strip()
    if resolved_idempotency_key == "":
        raise ValueError("dispatch idempotency key is required")

    identity = _get_latest_linked_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    if identity is None:
        raise TelegramIdentityNotFoundError("telegram channel is not linked for this workspace")

    now = utc_now()
    external_thread_key = resolve_telegram_thread_key(external_chat_id=identity["external_chat_id"])

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channel_threads (
              workspace_id,
              channel_type,
              external_thread_key,
              channel_identity_id,
              last_message_at,
              updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (workspace_id, channel_type, external_thread_key) DO UPDATE
            SET channel_identity_id = EXCLUDED.channel_identity_id,
                last_message_at = EXCLUDED.last_message_at,
                updated_at = EXCLUDED.updated_at
            RETURNING id
            """,
            (
                workspace_id,
                TELEGRAM_CHANNEL_TYPE,
                external_thread_key,
                identity["id"],
                now,
                now,
            ),
        )
        thread = cur.fetchone()

    if thread is None:
        raise RuntimeError("failed to resolve telegram channel thread for workspace dispatch")

    provider_message_id = f"simulated:{hashlib.sha256(resolved_idempotency_key.encode('utf-8')).hexdigest()[:20]}"
    normalized_dispatch_payload = dispatch_payload or {}
    dispatch_mode = "suppressed" if receipt_status_override == "suppressed" else (
        "simulated" if bot_token.strip() == "" else "deterministic_failure"
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channel_messages (
              workspace_id,
              channel_thread_id,
              channel_identity_id,
              channel_type,
              direction,
              provider_update_id,
              provider_message_id,
              external_chat_id,
              external_user_id,
              message_text,
              normalized_payload,
              route_status,
              idempotency_key,
              received_at
            )
            VALUES (%s, %s, %s, %s, 'outbound', NULL, %s, %s, %s, %s, %s, 'resolved', %s, %s)
            ON CONFLICT (channel_type, direction, idempotency_key) DO NOTHING
            RETURNING id, workspace_id, channel_thread_id, channel_identity_id,
                      channel_type, direction, provider_update_id, provider_message_id,
                      external_chat_id, external_user_id, message_text,
                      normalized_payload, route_status, idempotency_key, created_at, received_at
            """,
            (
                workspace_id,
                thread["id"],
                identity["id"],
                TELEGRAM_CHANNEL_TYPE,
                provider_message_id,
                identity["external_chat_id"],
                identity["external_user_id"],
                normalized_text,
                Jsonb(
                    {
                        "dispatch": {
                            "source": "workspace_notification",
                            "mode": dispatch_mode,
                        },
                        "scheduler": normalized_dispatch_payload,
                    }
                ),
                resolved_idempotency_key,
                now,
            ),
        )
        outbound = cur.fetchone()

        if outbound is None:
            cur.execute(
                """
                SELECT id, workspace_id, channel_thread_id, channel_identity_id, channel_type,
                       direction, provider_update_id, provider_message_id, external_chat_id,
                       external_user_id, message_text, normalized_payload, route_status,
                       idempotency_key, created_at, received_at
                FROM channel_messages
                WHERE workspace_id = %s
                  AND channel_type = %s
                  AND direction = 'outbound'
                  AND idempotency_key = %s
                LIMIT 1
                """,
                (workspace_id, TELEGRAM_CHANNEL_TYPE, resolved_idempotency_key),
            )
            outbound = cur.fetchone()

    if outbound is None:
        raise RuntimeError("failed to create outbound telegram workspace notification message")

    if receipt_status_override is not None:
        receipt_status = receipt_status_override
        provider_receipt_id: str | None = None
        failure_code = failure_code_override
        failure_detail = failure_detail_override
    else:
        receipt_status = "simulated"
        failure_code = None
        failure_detail = None
        provider_receipt_id = outbound["provider_message_id"]
        if bot_token.strip() != "":
            receipt_status = "failed"
            provider_receipt_id = None
            failure_code = "telegram_transport_not_enabled"
            failure_detail = "live telegram dispatch is not enabled in this environment"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO channel_delivery_receipts (
              workspace_id,
              channel_message_id,
              channel_type,
              status,
              provider_receipt_id,
              failure_code,
              failure_detail,
              scheduled_job_id,
              scheduler_job_kind,
              scheduled_for,
              schedule_slot,
              notification_policy,
              rollout_flag_state,
              support_evidence,
              rate_limit_evidence,
              incident_evidence,
              recorded_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (channel_message_id) DO UPDATE
            SET status = EXCLUDED.status,
                provider_receipt_id = EXCLUDED.provider_receipt_id,
                failure_code = EXCLUDED.failure_code,
                failure_detail = EXCLUDED.failure_detail,
                scheduled_job_id = EXCLUDED.scheduled_job_id,
                scheduler_job_kind = EXCLUDED.scheduler_job_kind,
                scheduled_for = EXCLUDED.scheduled_for,
                schedule_slot = EXCLUDED.schedule_slot,
                notification_policy = EXCLUDED.notification_policy,
                rollout_flag_state = EXCLUDED.rollout_flag_state,
                support_evidence = EXCLUDED.support_evidence,
                rate_limit_evidence = EXCLUDED.rate_limit_evidence,
                incident_evidence = EXCLUDED.incident_evidence,
                recorded_at = EXCLUDED.recorded_at
            RETURNING id, workspace_id, channel_message_id, channel_type,
                      status, provider_receipt_id, failure_code, failure_detail,
                      scheduled_job_id, scheduler_job_kind, scheduled_for, schedule_slot,
                      notification_policy, rollout_flag_state, support_evidence,
                      rate_limit_evidence, incident_evidence, recorded_at, created_at
            """,
            (
                workspace_id,
                outbound["id"],
                TELEGRAM_CHANNEL_TYPE,
                receipt_status,
                provider_receipt_id,
                failure_code,
                failure_detail,
                scheduled_job_id,
                scheduler_job_kind,
                scheduled_for,
                schedule_slot,
                Jsonb(notification_policy or {}),
                rollout_flag_state,
                Jsonb(support_evidence or {}),
                Jsonb(rate_limit_evidence or {}),
                Jsonb(incident_evidence or {}),
                utc_now(),
            ),
        )
        receipt = cur.fetchone()

    if receipt is None:
        raise RuntimeError("failed to persist telegram workspace notification delivery receipt")

    return outbound, receipt


def list_workspace_telegram_delivery_receipts(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    limit: int,
) -> list[TelegramDeliveryReceiptRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.id,
                   r.workspace_id,
                   r.channel_message_id,
                   r.channel_type,
                   r.status,
                   r.provider_receipt_id,
                   r.failure_code,
                   r.failure_detail,
                   r.scheduled_job_id,
                   r.scheduler_job_kind,
                   r.scheduled_for,
                   r.schedule_slot,
                   r.notification_policy,
                   r.rollout_flag_state,
                   r.support_evidence,
                   r.rate_limit_evidence,
                   r.incident_evidence,
                   r.recorded_at,
                   r.created_at
            FROM channel_delivery_receipts AS r
            JOIN workspace_members AS wm
              ON wm.workspace_id = r.workspace_id
            WHERE r.channel_type = %s
              AND r.workspace_id = %s
              AND wm.user_account_id = %s
            ORDER BY r.recorded_at DESC, r.id DESC
            LIMIT %s
            """,
            (TELEGRAM_CHANNEL_TYPE, workspace_id, user_account_id, limit),
        )
        rows = cur.fetchall()

    return rows


def serialize_channel_identity(identity: TelegramChannelIdentityRow) -> dict[str, object]:
    return {
        "id": str(identity["id"]),
        "user_account_id": str(identity["user_account_id"]),
        "workspace_id": str(identity["workspace_id"]),
        "channel_type": identity["channel_type"],
        "external_user_id": identity["external_user_id"],
        "external_chat_id": identity["external_chat_id"],
        "external_username": identity["external_username"],
        "status": identity["status"],
        "linked_at": identity["linked_at"].isoformat(),
        "unlinked_at": None if identity["unlinked_at"] is None else identity["unlinked_at"].isoformat(),
        "created_at": identity["created_at"].isoformat(),
        "updated_at": identity["updated_at"].isoformat(),
    }


def serialize_channel_link_challenge(
    challenge: TelegramChannelLinkChallengeRow | IssuedTelegramChannelLinkChallengeRow,
    *,
    include_token: bool,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": str(challenge["id"]),
        "user_account_id": str(challenge["user_account_id"]),
        "workspace_id": str(challenge["workspace_id"]),
        "channel_type": challenge["channel_type"],
        "link_code": challenge["link_code"],
        "status": challenge["status"],
        "expires_at": challenge["expires_at"].isoformat(),
        "confirmed_at": None
        if challenge["confirmed_at"] is None
        else challenge["confirmed_at"].isoformat(),
        "channel_identity_id": None
        if challenge["channel_identity_id"] is None
        else str(challenge["channel_identity_id"]),
        "created_at": challenge["created_at"].isoformat(),
    }
    if include_token:
        token = challenge.get("challenge_token")
        if not isinstance(token, str):
            raise ValueError("challenge token is required for issued link challenge serialization")
        payload["challenge_token"] = token
    return payload


def serialize_channel_thread(thread: TelegramChannelThreadRow) -> dict[str, object]:
    return {
        "id": str(thread["id"]),
        "workspace_id": str(thread["workspace_id"]),
        "channel_type": thread["channel_type"],
        "external_thread_key": thread["external_thread_key"],
        "channel_identity_id": None
        if thread["channel_identity_id"] is None
        else str(thread["channel_identity_id"]),
        "last_message_at": None
        if thread["last_message_at"] is None
        else thread["last_message_at"].isoformat(),
        "created_at": thread["created_at"].isoformat(),
        "updated_at": thread["updated_at"].isoformat(),
    }


def serialize_channel_message(message: TelegramChannelMessageRow) -> dict[str, object]:
    return {
        "id": str(message["id"]),
        "workspace_id": None if message["workspace_id"] is None else str(message["workspace_id"]),
        "channel_thread_id": None
        if message["channel_thread_id"] is None
        else str(message["channel_thread_id"]),
        "channel_identity_id": None
        if message["channel_identity_id"] is None
        else str(message["channel_identity_id"]),
        "channel_type": message["channel_type"],
        "direction": message["direction"],
        "provider_update_id": message["provider_update_id"],
        "provider_message_id": message["provider_message_id"],
        "external_chat_id": message["external_chat_id"],
        "external_user_id": message["external_user_id"],
        "message_text": message["message_text"],
        "normalized_payload": message["normalized_payload"],
        "route_status": message["route_status"],
        "idempotency_key": message["idempotency_key"],
        "created_at": message["created_at"].isoformat(),
        "received_at": message["received_at"].isoformat(),
    }


def serialize_delivery_receipt(receipt: TelegramDeliveryReceiptRow) -> dict[str, object]:
    return {
        "id": str(receipt["id"]),
        "workspace_id": str(receipt["workspace_id"]),
        "channel_message_id": str(receipt["channel_message_id"]),
        "channel_type": receipt["channel_type"],
        "status": receipt["status"],
        "provider_receipt_id": receipt["provider_receipt_id"],
        "failure_code": receipt["failure_code"],
        "failure_detail": receipt["failure_detail"],
        "scheduled_job_id": None
        if receipt["scheduled_job_id"] is None
        else str(receipt["scheduled_job_id"]),
        "scheduler_job_kind": receipt["scheduler_job_kind"],
        "scheduled_for": None if receipt["scheduled_for"] is None else receipt["scheduled_for"].isoformat(),
        "schedule_slot": receipt["schedule_slot"],
        "notification_policy": receipt["notification_policy"],
        "rollout_flag_state": receipt["rollout_flag_state"],
        "support_evidence": receipt["support_evidence"],
        "rate_limit_evidence": receipt["rate_limit_evidence"],
        "incident_evidence": receipt["incident_evidence"],
        "recorded_at": receipt["recorded_at"].isoformat(),
        "created_at": receipt["created_at"].isoformat(),
    }


def serialize_webhook_ingest_result(result: TelegramWebhookIngestResult) -> dict[str, object]:
    return {
        "duplicate": result["duplicate"],
        "route_status": result["route_status"],
        "link_status": result["link_status"],
        "unknown_chat_routing": result["unknown_chat_routing"],
        "message": serialize_channel_message(result["message"]),
        "thread": None if result["thread"] is None else serialize_channel_thread(result["thread"]),
    }
