"""SQLite persistence for one-time browser clip capabilities."""

from __future__ import annotations

from uuid import uuid4


BROWSER_CLIP_CAPABILITY_COLUMNS = """
                  id,
                  user_id,
                  origin,
                  expires_at,
                  consumed_at,
                  created_at
                """


def create_browser_clip_capability(
    self,
    *,
    capability_hash: str,
    origin: str,
    ttl_seconds: int,
) -> dict[str, object]:
    """Persist only a digest, with expiry derived from the database clock."""

    if not 1 <= ttl_seconds <= 300:
        raise ValueError("browser clip capability TTL must be between 1 and 300 seconds")

    self._execute(
        """
        DELETE FROM browser_clip_capabilities
        WHERE user_id = ?
          AND (
            julianday(expires_at) < julianday('now', '-1 day')
            OR julianday(consumed_at) < julianday('now', '-1 day')
          )
        """,
        (self.user_id,),
    )
    return self._fetch_one(
        "create_browser_clip_capability",
        f"""
                INSERT INTO browser_clip_capabilities (
                  id,
                  user_id,
                  capability_hash,
                  origin,
                  expires_at,
                  created_at
                )
                VALUES (
                  ?,
                  ?,
                  ?,
                  ?,
                  strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?),
                  strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                )
                RETURNING {BROWSER_CLIP_CAPABILITY_COLUMNS}
                """,
        (
            str(uuid4()),
            self.user_id,
            capability_hash,
            origin,
            f"+{ttl_seconds} seconds",
        ),
    )


def consume_browser_clip_capability(
    self,
    *,
    capability_hash: str,
    origin: str,
) -> dict[str, object] | None:
    """Atomically redeem one live capability for the bound SQLite user."""

    return self._fetch_optional_one(
        f"""
                UPDATE browser_clip_capabilities
                SET consumed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE user_id = ?
                  AND capability_hash = ?
                  AND origin = ?
                  AND consumed_at IS NULL
                  AND julianday(expires_at) > julianday('now')
                RETURNING {BROWSER_CLIP_CAPABILITY_COLUMNS}
                """,
        (self.user_id, capability_hash, origin),
    )


for _method in (create_browser_clip_capability, consume_browser_clip_capability):
    _method.__module__ = "alicebot_api.sqlite_store"
    _method.__qualname__ = f"SQLiteVNextStore.{_method.__name__}"
del _method


__all__ = [
    "BROWSER_CLIP_CAPABILITY_COLUMNS",
    "consume_browser_clip_capability",
    "create_browser_clip_capability",
]
