from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from psycopg.types.json import Jsonb


class HostedPreferencesValidationError(ValueError):
    """Raised when hosted preference input is invalid."""


class UserPreferencesRow(TypedDict):
    id: UUID
    user_account_id: UUID
    timezone: str
    brief_preferences: dict[str, object]
    quiet_hours: dict[str, object]
    created_at: datetime
    updated_at: datetime


DEFAULT_TIMEZONE = "UTC"
DEFAULT_BRIEF_PREFERENCES: dict[str, object] = {
    "daily_brief": {
        "enabled": False,
        "window_start": "07:00",
    }
}
DEFAULT_QUIET_HOURS: dict[str, object] = {
    "enabled": False,
    "start": "22:00",
    "end": "07:00",
}


def validate_timezone(timezone: str) -> str:
    normalized = timezone.strip()
    if normalized == "":
        raise HostedPreferencesValidationError("timezone must not be empty")

    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise HostedPreferencesValidationError(f"timezone {timezone!r} is not recognized") from exc

    return normalized


def _default_brief_preferences() -> dict[str, object]:
    return {
        "daily_brief": {
            "enabled": False,
            "window_start": "07:00",
        }
    }


def _default_quiet_hours() -> dict[str, object]:
    return {
        "enabled": False,
        "start": "22:00",
        "end": "07:00",
    }


def ensure_user_preferences(
    conn,
    *,
    user_account_id: UUID,
) -> UserPreferencesRow:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_preferences (user_account_id, timezone, brief_preferences, quiet_hours)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_account_id) DO NOTHING
            """,
            (
                user_account_id,
                DEFAULT_TIMEZONE,
                Jsonb(_default_brief_preferences()),
                Jsonb(_default_quiet_hours()),
            ),
        )
        cur.execute(
            """
            SELECT id,
                   user_account_id,
                   timezone,
                   brief_preferences,
                   quiet_hours,
                   created_at,
                   updated_at
            FROM user_preferences
            WHERE user_account_id = %s
            """,
            (user_account_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to load hosted user preferences")

    return row


def patch_user_preferences(
    conn,
    *,
    user_account_id: UUID,
    timezone: str | None,
    brief_preferences: dict[str, object] | None,
    quiet_hours: dict[str, object] | None,
) -> UserPreferencesRow:
    existing = ensure_user_preferences(conn, user_account_id=user_account_id)

    resolved_timezone = existing["timezone"] if timezone is None else validate_timezone(timezone)
    resolved_brief = existing["brief_preferences"] if brief_preferences is None else brief_preferences
    resolved_quiet = existing["quiet_hours"] if quiet_hours is None else quiet_hours

    if not isinstance(resolved_brief, dict):
        raise HostedPreferencesValidationError("brief_preferences must be an object")
    if not isinstance(resolved_quiet, dict):
        raise HostedPreferencesValidationError("quiet_hours must be an object")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE user_preferences
            SET timezone = %s,
                brief_preferences = %s,
                quiet_hours = %s,
                updated_at = clock_timestamp()
            WHERE user_account_id = %s
            RETURNING id,
                      user_account_id,
                      timezone,
                      brief_preferences,
                      quiet_hours,
                      created_at,
                      updated_at
            """,
            (
                resolved_timezone,
                Jsonb(resolved_brief),
                Jsonb(resolved_quiet),
                user_account_id,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to update hosted user preferences")

    return row


def serialize_user_preferences(preferences: UserPreferencesRow) -> dict[str, object]:
    return {
        "id": str(preferences["id"]),
        "user_account_id": str(preferences["user_account_id"]),
        "timezone": preferences["timezone"],
        "brief_preferences": preferences["brief_preferences"],
        "quiet_hours": preferences["quiet_hours"],
        "created_at": preferences["created_at"].isoformat(),
        "updated_at": preferences["updated_at"].isoformat(),
    }
