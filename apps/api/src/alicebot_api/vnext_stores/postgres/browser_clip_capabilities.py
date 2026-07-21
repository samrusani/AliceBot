"""PostgreSQL persistence for one-time browser clip capabilities."""

from __future__ import annotations

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

    with self.conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM browser_clip_capabilities
            WHERE user_id = app.current_user_id()
              AND (
                expires_at < clock_timestamp() - interval '1 day'
                OR consumed_at < clock_timestamp() - interval '1 day'
              )
            """
        )
    return self._fetch_one(
        "create_browser_clip_capability",
        f"""
                WITH issue_clock AS MATERIALIZED (
                  SELECT clock_timestamp() AS issued_at
                )
                INSERT INTO browser_clip_capabilities (
                  user_id,
                  capability_hash,
                  origin,
                  expires_at,
                  created_at
                )
                SELECT
                  app.current_user_id(),
                  %s,
                  %s,
                  issue_clock.issued_at + make_interval(secs => %s),
                  issue_clock.issued_at
                FROM issue_clock
                RETURNING {BROWSER_CLIP_CAPABILITY_COLUMNS}
                """,
        (capability_hash, origin, ttl_seconds),
    )


def consume_browser_clip_capability(
    self,
    *,
    capability_hash: str,
    origin: str,
) -> dict[str, object] | None:
    """Atomically redeem one live capability for the current RLS user."""

    return self._fetch_optional_one(
        f"""
                WITH redemption_clock AS MATERIALIZED (
                  SELECT clock_timestamp() AS redeemed_at
                )
                UPDATE browser_clip_capabilities
                SET consumed_at = redemption_clock.redeemed_at
                FROM redemption_clock
                WHERE user_id = app.current_user_id()
                  AND capability_hash = %s
                  AND origin = %s
                  AND consumed_at IS NULL
                  AND expires_at > redemption_clock.redeemed_at
                RETURNING {BROWSER_CLIP_CAPABILITY_COLUMNS}
                """,
        (capability_hash, origin),
    )


for _method in (create_browser_clip_capability, consume_browser_clip_capability):
    _method.__module__ = "alicebot_api.vnext_store"
    _method.__qualname__ = f"PostgresVNextStore.{_method.__name__}"
del _method


__all__ = [
    "BROWSER_CLIP_CAPABILITY_COLUMNS",
    "consume_browser_clip_capability",
    "create_browser_clip_capability",
]
