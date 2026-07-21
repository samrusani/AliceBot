"""Add one-time, origin-bound browser clip capabilities.

Only a SHA-256 digest is persisted.  Expiry is derived from the database
clock and redemption is a single conditional UPDATE so concurrent requests
cannot both consume the same capability.

Revision ID: 20260721_0094
Revises: 20260721_0093
"""

from __future__ import annotations

from alembic import op


revision = "20260721_0094"
down_revision = "20260721_0093"
branch_labels = None
depends_on = None


_UPGRADE_SCHEMA = """
        CREATE TABLE browser_clip_capabilities (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          capability_hash text NOT NULL UNIQUE,
          origin text NOT NULL,
          expires_at timestamptz NOT NULL,
          consumed_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          CONSTRAINT browser_clip_capabilities_hash_check
            CHECK (capability_hash ~ '^[0-9a-f]{64}$'),
          CONSTRAINT browser_clip_capabilities_origin_length_check
            CHECK (length(origin) BETWEEN 8 AND 2048),
          CONSTRAINT browser_clip_capabilities_expiry_range_check
            CHECK (
              expires_at > created_at
              AND expires_at <= created_at + interval '5 minutes'
            ),
          CONSTRAINT browser_clip_capabilities_consumed_range_check
            CHECK (consumed_at IS NULL OR consumed_at >= created_at)
        );

        CREATE INDEX browser_clip_capabilities_live_expiry_idx
          ON browser_clip_capabilities (user_id, expires_at)
          WHERE consumed_at IS NULL;

        CREATE INDEX browser_clip_capabilities_consumed_idx
          ON browser_clip_capabilities (user_id, consumed_at)
          WHERE consumed_at IS NOT NULL;
        """

_GRANTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON browser_clip_capabilities TO alicebot_app",
)

_POLICY = """
        CREATE POLICY browser_clip_capabilities_is_owner
          ON browser_clip_capabilities
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA)
    for statement in _GRANTS:
        op.execute(statement)
    op.execute("ALTER TABLE browser_clip_capabilities ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE browser_clip_capabilities FORCE ROW LEVEL SECURITY")
    op.execute(_POLICY)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS browser_clip_capabilities")
