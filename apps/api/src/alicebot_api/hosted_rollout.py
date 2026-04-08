from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID


class RolloutFlagBlockedError(RuntimeError):
    """Raised when a hosted rollout flag blocks the requested operation."""


class FeatureFlagRow(TypedDict):
    id: UUID
    flag_key: str
    cohort_key: str | None
    enabled: bool
    description: str | None
    created_at: datetime
    updated_at: datetime


class RolloutFlagResolution(TypedDict):
    flag_key: str
    enabled: bool
    source_scope: str
    source_cohort_key: str | None
    description: str | None
    updated_at: str


class RolloutFlagPatch(TypedDict):
    flag_key: str
    enabled: bool
    cohort_key: str | None
    description: str | None


def _get_user_cohort(conn, *, user_account_id: UUID) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT beta_cohort_key
            FROM user_accounts
            WHERE id = %s
            LIMIT 1
            """,
            (user_account_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return row["beta_cohort_key"]


def _normalize_flag_key(flag_key: str, *, hosted_only: bool = False) -> str:
    normalized = flag_key.strip()
    if normalized == "":
        raise ValueError("rollout flag key is required")
    if len(normalized) > 120:
        raise ValueError("rollout flag key must be 120 characters or less")
    if hosted_only and not normalized.startswith("hosted_"):
        raise ValueError("rollout flag key must start with 'hosted_'")
    return normalized


def _normalize_cohort_key(cohort_key: str | None) -> str | None:
    if cohort_key is None:
        return None
    normalized = cohort_key.strip()
    if normalized == "":
        return None
    if len(normalized) > 120:
        raise ValueError("cohort key must be 120 characters or less")
    return normalized


def resolve_rollout_flag(
    conn,
    *,
    user_account_id: UUID,
    flag_key: str,
) -> RolloutFlagResolution:
    normalized_flag_key = _normalize_flag_key(flag_key)
    cohort_key = _get_user_cohort(conn, user_account_id=user_account_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,
                   flag_key,
                   cohort_key,
                   enabled,
                   description,
                   created_at,
                   updated_at
            FROM feature_flags
            WHERE flag_key = %s
              AND (cohort_key IS NULL OR cohort_key = %s)
            ORDER BY CASE WHEN cohort_key = %s THEN 0 ELSE 1 END,
                     updated_at DESC,
                     id DESC
            LIMIT 1
            """,
            (normalized_flag_key, cohort_key, cohort_key),
        )
        row = cur.fetchone()

    if row is None:
        return {
            "flag_key": normalized_flag_key,
            "enabled": False,
            "source_scope": "missing",
            "source_cohort_key": None,
            "description": None,
            "updated_at": "",
        }

    source_scope = "cohort" if row["cohort_key"] is not None else "global"
    return {
        "flag_key": row["flag_key"],
        "enabled": bool(row["enabled"]),
        "source_scope": source_scope,
        "source_cohort_key": row["cohort_key"],
        "description": row["description"],
        "updated_at": row["updated_at"].isoformat(),
    }


def ensure_rollout_flag_enabled(
    conn,
    *,
    user_account_id: UUID,
    flag_key: str,
) -> RolloutFlagResolution:
    resolution = resolve_rollout_flag(
        conn,
        user_account_id=user_account_id,
        flag_key=flag_key,
    )
    if not resolution["enabled"]:
        raise RolloutFlagBlockedError(
            f"rollout flag '{resolution['flag_key']}' is disabled for this account"
        )
    return resolution


def list_rollout_flags_for_admin(
    conn,
    *,
    user_account_id: UUID,
    include_non_hosted_flags: bool = False,
) -> list[RolloutFlagResolution]:
    cohort_key = _get_user_cohort(conn, user_account_id=user_account_id)

    with conn.cursor() as cur:
        if include_non_hosted_flags:
            cur.execute(
                """
                SELECT id,
                       flag_key,
                       cohort_key,
                       enabled,
                       description,
                       created_at,
                       updated_at
                FROM feature_flags
                WHERE cohort_key IS NULL OR cohort_key = %s
                ORDER BY flag_key ASC,
                         CASE WHEN cohort_key = %s THEN 0 ELSE 1 END,
                         updated_at DESC,
                         id DESC
                """,
                (cohort_key, cohort_key),
            )
        else:
            cur.execute(
                """
                SELECT id,
                       flag_key,
                       cohort_key,
                       enabled,
                       description,
                       created_at,
                       updated_at
                FROM feature_flags
                WHERE flag_key LIKE 'hosted_%%'
                  AND (cohort_key IS NULL OR cohort_key = %s)
                ORDER BY flag_key ASC,
                         CASE WHEN cohort_key = %s THEN 0 ELSE 1 END,
                         updated_at DESC,
                         id DESC
                """,
                (cohort_key, cohort_key),
            )
        rows = cur.fetchall()

    selected: dict[str, FeatureFlagRow] = {}
    for row in rows:
        key = str(row["flag_key"])
        if key in selected:
            continue
        selected[key] = row

    payload: list[RolloutFlagResolution] = []
    for key in sorted(selected):
        row = selected[key]
        payload.append(
            {
                "flag_key": row["flag_key"],
                "enabled": bool(row["enabled"]),
                "source_scope": "cohort" if row["cohort_key"] is not None else "global",
                "source_cohort_key": row["cohort_key"],
                "description": row["description"],
                "updated_at": row["updated_at"].isoformat(),
            }
        )

    return payload


def patch_rollout_flags(
    conn,
    *,
    patches: list[RolloutFlagPatch],
    allowed_cohort_key: str | None = None,
) -> list[RolloutFlagResolution]:
    updated: list[RolloutFlagResolution] = []
    with conn.cursor() as cur:
        for patch in patches:
            flag_key = _normalize_flag_key(patch["flag_key"], hosted_only=True)
            cohort_key = _normalize_cohort_key(patch.get("cohort_key"))
            description = patch.get("description")
            enabled = bool(patch["enabled"])
            if cohort_key != allowed_cohort_key:
                raise ValueError("rollout flag cohort must match caller cohort")

            if cohort_key is not None:
                cur.execute(
                    """
                    SELECT 1
                    FROM beta_cohorts
                    WHERE cohort_key = %s
                    LIMIT 1
                    """,
                    (cohort_key,),
                )
                if cur.fetchone() is None:
                    raise ValueError(f"cohort {cohort_key!r} was not found")

            cur.execute(
                """
                UPDATE feature_flags
                SET enabled = %s,
                    description = COALESCE(%s, description),
                    updated_at = clock_timestamp()
                WHERE flag_key = %s
                  AND cohort_key IS NOT DISTINCT FROM %s
                RETURNING flag_key, cohort_key, enabled, description, updated_at
                """,
                (enabled, description, flag_key, cohort_key),
            )
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    """
                    INSERT INTO feature_flags (flag_key, cohort_key, enabled, description)
                    VALUES (%s, %s, %s, %s)
                    RETURNING flag_key, cohort_key, enabled, description, updated_at
                    """,
                    (flag_key, cohort_key, enabled, description),
                )
                row = cur.fetchone()

            if row is None:
                raise RuntimeError("failed to patch rollout flag")

            updated.append(
                {
                    "flag_key": row["flag_key"],
                    "enabled": bool(row["enabled"]),
                    "source_scope": "cohort" if row["cohort_key"] is not None else "global",
                    "source_cohort_key": row["cohort_key"],
                    "description": row["description"],
                    "updated_at": row["updated_at"].isoformat(),
                }
            )

    return updated
