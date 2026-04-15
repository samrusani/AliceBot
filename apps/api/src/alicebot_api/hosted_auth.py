from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
from typing import TypedDict
from uuid import UUID

from psycopg.types.json import Jsonb

from alicebot_api.db import set_current_user_account


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class MagicLinkTokenInvalidError(ValueError):
    """Raised when a magic-link challenge token is unknown or already consumed."""


class MagicLinkTokenExpiredError(ValueError):
    """Raised when a magic-link challenge token has expired."""


class AuthSessionInvalidError(ValueError):
    """Raised when an auth session token is missing or invalid."""


class AuthSessionExpiredError(ValueError):
    """Raised when an auth session is expired."""


class AuthSessionRevokedDeviceError(ValueError):
    """Raised when the auth session is bound to a revoked device."""


class UserAccountRow(TypedDict):
    id: UUID
    email: str
    display_name: str | None
    beta_cohort_key: str | None
    created_at: datetime


class MagicLinkChallengeRow(TypedDict):
    id: UUID
    email: str
    status: str
    expires_at: datetime
    consumed_at: datetime | None
    created_at: datetime


class IssuedMagicLinkChallengeRow(MagicLinkChallengeRow):
    challenge_token: str


class AuthSessionRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID | None
    device_id: UUID | None
    session_token_hash: str
    status: str
    expires_at: datetime
    revoked_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime


class SessionResolution(TypedDict):
    session: AuthSessionRow
    user_account: UserAccountRow
    device_status: str | None
    device_label: str | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("email must be valid for magic-link authentication")
    return normalized


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def _default_display_name(email: str) -> str:
    stem = email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    if stem == "":
        return "Alice User"
    words = [word for word in stem.split(" ") if word]
    return " ".join(word.capitalize() for word in words[:3])


def ensure_beta_cohort(conn, cohort_key: str = "p10-beta") -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO beta_cohorts (cohort_key, description)
            VALUES (%s, %s)
            ON CONFLICT (cohort_key) DO NOTHING
            """,
            (cohort_key, "Phase 10 hosted beta cohort"),
        )


def get_or_create_user_account_by_email(conn, *, email: str) -> UserAccountRow:
    normalized_email = normalize_email(email)
    ensure_beta_cohort(conn)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_accounts (email, display_name, beta_cohort_key)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE
            SET email = EXCLUDED.email
            RETURNING id, email, display_name, beta_cohort_key, created_at
            """,
            (normalized_email, _default_display_name(normalized_email), "p10-beta"),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to load or create hosted user account")
    return row


def start_magic_link_challenge(
    conn,
    *,
    email: str,
    ttl_seconds: int,
) -> IssuedMagicLinkChallengeRow:
    normalized_email = normalize_email(email)
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE magic_link_challenges
            SET status = 'expired'
            WHERE email = %s
              AND status = 'pending'
              AND expires_at > %s
            """,
            (normalized_email, now),
        )
        challenge_token = generate_token()
        challenge_token_hash = hash_token(challenge_token)
        expires_at = now + timedelta(seconds=ttl_seconds)
        cur.execute(
            """
            INSERT INTO magic_link_challenges (email, challenge_token_hash, status, expires_at)
            VALUES (%s, %s, 'pending', %s)
            RETURNING id, email, status, expires_at, consumed_at, created_at
            """,
            (normalized_email, challenge_token_hash, expires_at),
        )
        created = cur.fetchone()

    if created is None:
        raise RuntimeError("failed to create magic-link challenge")
    created["challenge_token"] = challenge_token
    return created


def _lookup_magic_link_challenge_for_update(
    conn,
    *,
    challenge_token: str,
) -> MagicLinkChallengeRow | None:
    token = challenge_token.strip()
    if token == "":
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, email, status, expires_at, consumed_at, created_at
            FROM magic_link_challenges
            WHERE challenge_token_hash = %s
            FOR UPDATE
            """,
            (hash_token(token),),
        )
        return cur.fetchone()


def _derive_device_key(user_account_id: UUID, device_label: str) -> str:
    token_source = f"{user_account_id}:{device_label.strip().lower()}"
    return hashlib.sha256(token_source.encode("utf-8")).hexdigest()[:48]


def _upsert_device(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID | None,
    device_label: str,
    device_key: str,
) -> dict[str, object]:
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


def _get_current_workspace_id(conn, *, user_account_id: UUID) -> UUID | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT workspace_id
            FROM workspace_members
            WHERE user_account_id = %s
            ORDER BY CASE WHEN role = 'owner' THEN 0 ELSE 1 END, created_at ASC, id ASC
            LIMIT 1
            """,
            (user_account_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None
    return row["workspace_id"]


def verify_magic_link_challenge(
    conn,
    *,
    challenge_token: str,
    session_ttl_seconds: int,
    device_label: str,
    device_key: str | None,
) -> tuple[UserAccountRow, AuthSessionRow, str, dict[str, object]]:
    now = utc_now()
    challenge = _lookup_magic_link_challenge_for_update(conn, challenge_token=challenge_token)

    if challenge is None:
        raise MagicLinkTokenInvalidError("magic-link token is invalid")

    if challenge["status"] != "pending":
        raise MagicLinkTokenInvalidError("magic-link token is no longer valid")

    if challenge["expires_at"] <= now:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE magic_link_challenges
                SET status = 'expired'
                WHERE id = %s
                """,
                (challenge["id"],),
            )
        raise MagicLinkTokenExpiredError("magic-link token has expired")

    user_account = get_or_create_user_account_by_email(conn, email=challenge["email"])
    set_current_user_account(conn, user_account["id"])
    workspace_id = _get_current_workspace_id(conn, user_account_id=user_account["id"])
    normalized_device_label = device_label.strip() or "Primary device"
    resolved_device_key = (device_key or "").strip() or _derive_device_key(
        user_account["id"], normalized_device_label
    )
    device = _upsert_device(
        conn,
        user_account_id=user_account["id"],
        workspace_id=workspace_id,
        device_label=normalized_device_label,
        device_key=resolved_device_key,
    )

    raw_session_token = generate_token()
    session_expires_at = now + timedelta(seconds=session_ttl_seconds)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO auth_sessions (
              user_account_id,
              workspace_id,
              device_id,
              session_token_hash,
              status,
              expires_at,
              last_seen_at
            )
            VALUES (%s, %s, %s, %s, 'active', %s, %s)
            RETURNING id, user_account_id, workspace_id, device_id, session_token_hash, status,
                      expires_at, revoked_at, last_seen_at, created_at
            """,
            (
                user_account["id"],
                workspace_id,
                device["id"],
                hash_token(raw_session_token),
                session_expires_at,
                now,
            ),
        )
        session = cur.fetchone()
        cur.execute(
            """
            UPDATE magic_link_challenges
            SET status = 'consumed',
                consumed_at = %s
            WHERE id = %s
            """,
            (now, challenge["id"]),
        )

    if session is None:
        raise RuntimeError("failed to create auth session")

    return user_account, session, raw_session_token, device


def resolve_auth_session(conn, *, session_token: str) -> SessionResolution:
    token = session_token.strip()
    if token == "":
        raise AuthSessionInvalidError("session token is required")

    token_hash = hash_token(token)
    now = utc_now()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              s.id,
              s.user_account_id,
              s.workspace_id,
              s.device_id,
              s.session_token_hash,
              s.status,
              s.expires_at,
              s.revoked_at,
              s.last_seen_at,
              s.created_at,
              u.email AS user_email,
              u.display_name AS user_display_name,
              u.beta_cohort_key AS user_beta_cohort_key,
              u.created_at AS user_created_at,
              d.status AS device_status,
              d.device_label AS device_label
            FROM auth_sessions AS s
            JOIN user_accounts AS u
              ON u.id = s.user_account_id
            LEFT JOIN devices AS d
              ON d.id = s.device_id
            WHERE s.session_token_hash = %s
            LIMIT 1
            """,
            (token_hash,),
        )
        row = cur.fetchone()

    if row is None:
        raise AuthSessionInvalidError("session token is invalid")

    if row["status"] != "active":
        if row["device_status"] == "revoked":
            raise AuthSessionRevokedDeviceError("session device has been revoked")
        raise AuthSessionInvalidError("session is not active")

    if row["expires_at"] <= now:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE auth_sessions
                SET status = 'expired'
                WHERE id = %s
                  AND status = 'active'
                """,
                (row["id"],),
            )
        raise AuthSessionExpiredError("session token has expired")

    if row["device_status"] == "revoked":
        raise AuthSessionRevokedDeviceError("session device has been revoked")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE auth_sessions
            SET last_seen_at = %s
            WHERE id = %s
            """,
            (now, row["id"]),
        )
        if row["device_id"] is not None:
            cur.execute(
                """
                UPDATE devices
                SET last_seen_at = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (now, now, row["device_id"]),
            )

    session: AuthSessionRow = {
        "id": row["id"],
        "user_account_id": row["user_account_id"],
        "workspace_id": row["workspace_id"],
        "device_id": row["device_id"],
        "session_token_hash": row["session_token_hash"],
        "status": row["status"],
        "expires_at": row["expires_at"],
        "revoked_at": row["revoked_at"],
        "last_seen_at": now,
        "created_at": row["created_at"],
    }
    user_account: UserAccountRow = {
        "id": row["user_account_id"],
        "email": row["user_email"],
        "display_name": row["user_display_name"],
        "beta_cohort_key": row["user_beta_cohort_key"],
        "created_at": row["user_created_at"],
    }
    set_current_user_account(conn, user_account["id"])
    return {
        "session": session,
        "user_account": user_account,
        "device_status": row["device_status"],
        "device_label": row["device_label"],
    }


def logout_auth_session(conn, *, session_token: str) -> None:
    token = session_token.strip()
    if token == "":
        raise AuthSessionInvalidError("session token is required")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE auth_sessions
            SET status = 'revoked',
                revoked_at = %s
            WHERE session_token_hash = %s
              AND status = 'active'
            RETURNING id
            """,
            (utc_now(), hash_token(token)),
        )
        row = cur.fetchone()

    if row is None:
        raise AuthSessionInvalidError("session token is invalid")


def list_feature_flags_for_user(conn, *, user_account_id: UUID) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT beta_cohort_key
            FROM user_accounts
            WHERE id = %s
            """,
            (user_account_id,),
        )
        user = cur.fetchone()

    if user is None:
        return []

    cohort_key = user["beta_cohort_key"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT flag_key
            FROM feature_flags
            WHERE enabled = true
              AND (cohort_key IS NULL OR cohort_key = %s)
            ORDER BY flag_key ASC
            """,
            (cohort_key,),
        )
        rows = cur.fetchall()

    return [str(row["flag_key"]) for row in rows]


def serialize_user_account(user_account: UserAccountRow) -> dict[str, object]:
    return {
        "id": str(user_account["id"]),
        "email": user_account["email"],
        "display_name": user_account["display_name"],
        "beta_cohort_key": user_account["beta_cohort_key"],
        "created_at": user_account["created_at"].isoformat(),
    }


def serialize_auth_session(session: AuthSessionRow) -> dict[str, object]:
    return {
        "id": str(session["id"]),
        "user_account_id": str(session["user_account_id"]),
        "workspace_id": None if session["workspace_id"] is None else str(session["workspace_id"]),
        "device_id": None if session["device_id"] is None else str(session["device_id"]),
        "status": session["status"],
        "expires_at": session["expires_at"].isoformat(),
        "revoked_at": None if session["revoked_at"] is None else session["revoked_at"].isoformat(),
        "last_seen_at": None if session["last_seen_at"] is None else session["last_seen_at"].isoformat(),
        "created_at": session["created_at"].isoformat(),
    }


def serialize_magic_link_challenge(challenge: IssuedMagicLinkChallengeRow) -> dict[str, object]:
    return {
        "id": str(challenge["id"]),
        "email": challenge["email"],
        "challenge_token": challenge["challenge_token"],
        "status": challenge["status"],
        "expires_at": challenge["expires_at"].isoformat(),
        "consumed_at": None if challenge["consumed_at"] is None else challenge["consumed_at"].isoformat(),
        "created_at": challenge["created_at"].isoformat(),
    }


def ensure_user_preferences_row(conn, *, user_account_id: UUID) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_preferences (
              user_account_id,
              timezone,
              brief_preferences,
              quiet_hours
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_account_id) DO NOTHING
            """,
            (
                user_account_id,
                "UTC",
                Jsonb({"daily_brief": {"enabled": False, "window_start": "07:00"}}),
                Jsonb({"start": "22:00", "end": "07:00", "enabled": False}),
            ),
        )
