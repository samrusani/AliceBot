from __future__ import annotations

from datetime import datetime, timedelta
from typing import TypedDict
from uuid import UUID

from alicebot_api.hosted_auth import generate_token, hash_token, utc_now


class DeviceLinkTokenInvalidError(ValueError):
    """Raised when a device-link challenge token is invalid."""


class DeviceLinkTokenExpiredError(ValueError):
    """Raised when a device-link challenge has expired."""


class HostedDeviceNotFoundError(LookupError):
    """Raised when a hosted device is not visible for the account."""


class DeviceRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID | None
    device_key: str
    device_label: str
    status: str
    last_seen_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeviceLinkChallengeRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID | None
    device_key: str
    device_label: str
    status: str
    expires_at: datetime
    confirmed_at: datetime | None
    device_id: UUID | None
    created_at: datetime


class IssuedDeviceLinkChallengeRow(DeviceLinkChallengeRow):
    challenge_token: str


def _normalize_device_label(device_label: str) -> str:
    normalized = device_label.strip()
    if normalized == "":
        raise ValueError("device_label is required")
    return normalized[:120]


def _normalize_device_key(device_key: str) -> str:
    normalized = device_key.strip()
    if normalized == "":
        raise ValueError("device_key is required")
    return normalized[:160]


def _upsert_device(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID | None,
    device_key: str,
    device_label: str,
) -> DeviceRow:
    now = utc_now()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO devices (
              user_account_id,
              workspace_id,
              device_key,
              device_label,
              status,
              last_seen_at,
              updated_at
            )
            VALUES (%s, %s, %s, %s, 'active', %s, %s)
            ON CONFLICT (user_account_id, device_key) DO UPDATE
            SET workspace_id = EXCLUDED.workspace_id,
                device_label = EXCLUDED.device_label,
                status = 'active',
                revoked_at = NULL,
                last_seen_at = EXCLUDED.last_seen_at,
                updated_at = EXCLUDED.updated_at
            RETURNING id, user_account_id, workspace_id, device_key, device_label, status,
                      last_seen_at, revoked_at, created_at, updated_at
            """,
            (user_account_id, workspace_id, device_key, device_label, now, now),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to upsert hosted device")
    return row


def start_device_link_challenge(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID | None,
    device_key: str,
    device_label: str,
    ttl_seconds: int,
) -> IssuedDeviceLinkChallengeRow:
    normalized_key = _normalize_device_key(device_key)
    normalized_label = _normalize_device_label(device_label)
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE device_link_challenges
            SET status = 'expired'
            WHERE user_account_id = %s
              AND device_key = %s
              AND status = 'pending'
              AND expires_at > %s
            """,
            (user_account_id, normalized_key, now),
        )
        challenge_token = generate_token()
        challenge_token_hash = hash_token(challenge_token)
        expires_at = now + timedelta(seconds=ttl_seconds)
        cur.execute(
            """
            INSERT INTO device_link_challenges (
              user_account_id,
              workspace_id,
              device_key,
              device_label,
              challenge_token_hash,
              status,
              expires_at
            )
            VALUES (%s, %s, %s, %s, %s, 'pending', %s)
            RETURNING id, user_account_id, workspace_id, device_key, device_label,
                      status, expires_at, confirmed_at, device_id, created_at
            """,
            (
                user_account_id,
                workspace_id,
                normalized_key,
                normalized_label,
                challenge_token_hash,
                expires_at,
            ),
        )
        challenge = cur.fetchone()

    if challenge is None:
        raise RuntimeError("failed to create device-link challenge")
    challenge["challenge_token"] = challenge_token
    return challenge


def _lookup_device_link_challenge_for_update(
    conn,
    *,
    user_account_id: UUID,
    challenge_token: str,
) -> DeviceLinkChallengeRow | None:
    token = challenge_token.strip()
    if token == "":
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, user_account_id, workspace_id, device_key, device_label,
                   status, expires_at, confirmed_at, device_id, created_at
            FROM device_link_challenges
            WHERE user_account_id = %s
              AND challenge_token_hash = %s
            FOR UPDATE
            """,
            (user_account_id, hash_token(token)),
        )
        return cur.fetchone()


def confirm_device_link_challenge(
    conn,
    *,
    user_account_id: UUID,
    challenge_token: str,
) -> DeviceRow:
    now = utc_now()
    challenge = _lookup_device_link_challenge_for_update(
        conn,
        user_account_id=user_account_id,
        challenge_token=challenge_token,
    )

    if challenge is None:
        raise DeviceLinkTokenInvalidError("device-link token is invalid")

    if challenge["status"] == "confirmed" and challenge["device_id"] is not None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_account_id, workspace_id, device_key, device_label, status,
                       last_seen_at, revoked_at, created_at, updated_at
                FROM devices
                WHERE id = %s
                """,
                (challenge["device_id"],),
            )
            existing_device = cur.fetchone()
        if existing_device is not None:
            return existing_device

    if challenge["status"] != "pending":
        raise DeviceLinkTokenInvalidError("device-link token is no longer valid")

    if challenge["expires_at"] <= now:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE device_link_challenges
                SET status = 'expired'
                WHERE id = %s
                """,
                (challenge["id"],),
            )
        raise DeviceLinkTokenExpiredError("device-link token has expired")

    device = _upsert_device(
        conn,
        user_account_id=user_account_id,
        workspace_id=challenge["workspace_id"],
        device_key=challenge["device_key"],
        device_label=challenge["device_label"],
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE device_link_challenges
            SET status = 'confirmed',
                confirmed_at = %s,
                device_id = %s
            WHERE id = %s
            """,
            (now, device["id"], challenge["id"]),
        )

    return device


def list_devices(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID | None,
) -> list[DeviceRow]:
    with conn.cursor() as cur:
        if workspace_id is None:
            cur.execute(
                """
                SELECT id, user_account_id, workspace_id, device_key, device_label, status,
                       last_seen_at, revoked_at, created_at, updated_at
                FROM devices
                WHERE user_account_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (user_account_id,),
            )
        else:
            cur.execute(
                """
                SELECT id, user_account_id, workspace_id, device_key, device_label, status,
                       last_seen_at, revoked_at, created_at, updated_at
                FROM devices
                WHERE user_account_id = %s
                  AND (workspace_id = %s OR workspace_id IS NULL)
                ORDER BY created_at DESC, id DESC
                """,
                (user_account_id, workspace_id),
            )
        rows = cur.fetchall()

    return rows


def revoke_device(
    conn,
    *,
    user_account_id: UUID,
    device_id: UUID,
) -> DeviceRow:
    now = utc_now()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE devices
            SET status = 'revoked',
                revoked_at = %s,
                updated_at = %s
            WHERE id = %s
              AND user_account_id = %s
            RETURNING id, user_account_id, workspace_id, device_key, device_label, status,
                      last_seen_at, revoked_at, created_at, updated_at
            """,
            (now, now, device_id, user_account_id),
        )
        row = cur.fetchone()

        if row is None:
            raise HostedDeviceNotFoundError(f"device {device_id} was not found")

        cur.execute(
            """
            UPDATE auth_sessions
            SET status = 'revoked',
                revoked_at = %s
            WHERE device_id = %s
              AND status = 'active'
            """,
            (now, device_id),
        )

    return row


def serialize_device(device: DeviceRow) -> dict[str, object]:
    return {
        "id": str(device["id"]),
        "user_account_id": str(device["user_account_id"]),
        "workspace_id": None if device["workspace_id"] is None else str(device["workspace_id"]),
        "device_key": device["device_key"],
        "device_label": device["device_label"],
        "status": device["status"],
        "last_seen_at": None if device["last_seen_at"] is None else device["last_seen_at"].isoformat(),
        "revoked_at": None if device["revoked_at"] is None else device["revoked_at"].isoformat(),
        "created_at": device["created_at"].isoformat(),
        "updated_at": device["updated_at"].isoformat(),
    }


def serialize_device_link_challenge(challenge: IssuedDeviceLinkChallengeRow) -> dict[str, object]:
    return {
        "id": str(challenge["id"]),
        "user_account_id": str(challenge["user_account_id"]),
        "workspace_id": None if challenge["workspace_id"] is None else str(challenge["workspace_id"]),
        "device_key": challenge["device_key"],
        "device_label": challenge["device_label"],
        "challenge_token": challenge["challenge_token"],
        "status": challenge["status"],
        "expires_at": challenge["expires_at"].isoformat(),
        "confirmed_at": None if challenge["confirmed_at"] is None else challenge["confirmed_at"].isoformat(),
        "device_id": None if challenge["device_id"] is None else str(challenge["device_id"]),
        "created_at": challenge["created_at"].isoformat(),
    }
