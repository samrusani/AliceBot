"""Add Phase 5 continuity correction ledger and lifecycle/freshness fields."""

from __future__ import annotations

from alembic import op


revision = "20260330_0042"
down_revision = "20260329_0041"
branch_labels = None
depends_on = None

CONTINUITY_CORRECTION_ACTIONS = (
    "confirm",
    "edit",
    "delete",
    "supersede",
    "mark_stale",
)

CONTINUITY_OBJECT_STATUSES = (
    "active",
    "completed",
    "cancelled",
    "superseded",
    "stale",
    "deleted",
)

_CORRECTION_ACTIONS_SQL = ", ".join(f"'{value}'" for value in CONTINUITY_CORRECTION_ACTIONS)
_OBJECT_STATUSES_SQL = ", ".join(f"'{value}'" for value in CONTINUITY_OBJECT_STATUSES)

_RLS_TABLES = (
    "continuity_correction_events",
)

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.reject_continuity_correction_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'continuity correction events are append-only';
        END;
        $$;
        """,
)

_UPGRADE_SCHEMA_STATEMENTS = (
    "ALTER TABLE continuity_objects ADD COLUMN last_confirmed_at timestamptz NULL",
    "ALTER TABLE continuity_objects ADD COLUMN supersedes_object_id uuid NULL",
    "ALTER TABLE continuity_objects ADD COLUMN superseded_by_object_id uuid NULL",
    "ALTER TABLE continuity_objects DROP CONSTRAINT continuity_objects_status_check",
    (
        "ALTER TABLE continuity_objects "
        "ADD CONSTRAINT continuity_objects_status_check "
        f"CHECK (status IN ({_OBJECT_STATUSES_SQL}))"
    ),
    (
        "ALTER TABLE continuity_objects "
        "ADD CONSTRAINT continuity_objects_supersedes_fkey "
        "FOREIGN KEY (supersedes_object_id, user_id) "
        "REFERENCES continuity_objects(id, user_id) "
        "ON DELETE SET NULL"
    ),
    (
        "ALTER TABLE continuity_objects "
        "ADD CONSTRAINT continuity_objects_superseded_by_fkey "
        "FOREIGN KEY (superseded_by_object_id, user_id) "
        "REFERENCES continuity_objects(id, user_id) "
        "ON DELETE SET NULL"
    ),
    (
        "ALTER TABLE continuity_objects "
        "ADD CONSTRAINT continuity_objects_supersedes_not_self_check "
        "CHECK (supersedes_object_id IS NULL OR supersedes_object_id <> id)"
    ),
    (
        "ALTER TABLE continuity_objects "
        "ADD CONSTRAINT continuity_objects_superseded_by_not_self_check "
        "CHECK (superseded_by_object_id IS NULL OR superseded_by_object_id <> id)"
    ),
    (
        "CREATE INDEX continuity_objects_user_status_updated_idx "
        "ON continuity_objects (user_id, status, updated_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX continuity_objects_user_supersedes_idx "
        "ON continuity_objects (user_id, supersedes_object_id)"
    ),
    (
        "CREATE INDEX continuity_objects_user_superseded_by_idx "
        "ON continuity_objects (user_id, superseded_by_object_id)"
    ),
    """
        CREATE TABLE continuity_correction_events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          continuity_object_id uuid NOT NULL,
          action text NOT NULL,
          reason text NULL,
          before_snapshot jsonb NOT NULL,
          after_snapshot jsonb NOT NULL,
          payload jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT continuity_correction_events_object_fkey
            FOREIGN KEY (continuity_object_id, user_id)
            REFERENCES continuity_objects(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_correction_events_action_check
            CHECK (action IN (""" + _CORRECTION_ACTIONS_SQL + """)),
          CONSTRAINT continuity_correction_events_reason_length_check
            CHECK (reason IS NULL OR (char_length(reason) >= 1 AND char_length(reason) <= 500))
        )
        """,
    (
        "CREATE INDEX continuity_correction_events_user_object_created_idx "
        "ON continuity_correction_events (user_id, continuity_object_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX continuity_correction_events_user_action_created_idx "
        "ON continuity_correction_events (user_id, action, created_at DESC, id DESC)"
    ),
)

_UPGRADE_TRIGGER_STATEMENTS = (
    """
        CREATE TRIGGER continuity_correction_events_append_only
        BEFORE UPDATE OR DELETE ON continuity_correction_events
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_continuity_correction_mutation();
        """,
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT UPDATE ON continuity_objects TO alicebot_app",
    "GRANT SELECT, INSERT ON continuity_correction_events TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENTS = (
    """
        CREATE POLICY continuity_objects_update_own ON continuity_objects
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """,
    """
        CREATE POLICY continuity_correction_events_read_own ON continuity_correction_events
          FOR SELECT
          USING (user_id = app.current_user_id());
        """,
    """
        CREATE POLICY continuity_correction_events_insert_own ON continuity_correction_events
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP POLICY IF EXISTS continuity_correction_events_insert_own ON continuity_correction_events",
    "DROP POLICY IF EXISTS continuity_correction_events_read_own ON continuity_correction_events",
    "DROP POLICY IF EXISTS continuity_objects_update_own ON continuity_objects",
    "REVOKE UPDATE ON continuity_objects FROM alicebot_app",
    "DROP TRIGGER IF EXISTS continuity_correction_events_append_only ON continuity_correction_events",
    "DROP TABLE IF EXISTS continuity_correction_events",
    "DROP FUNCTION IF EXISTS app.reject_continuity_correction_mutation()",
    "DROP INDEX IF EXISTS continuity_objects_user_superseded_by_idx",
    "DROP INDEX IF EXISTS continuity_objects_user_supersedes_idx",
    "DROP INDEX IF EXISTS continuity_objects_user_status_updated_idx",
    "ALTER TABLE continuity_objects DROP CONSTRAINT IF EXISTS continuity_objects_superseded_by_not_self_check",
    "ALTER TABLE continuity_objects DROP CONSTRAINT IF EXISTS continuity_objects_supersedes_not_self_check",
    "ALTER TABLE continuity_objects DROP CONSTRAINT IF EXISTS continuity_objects_superseded_by_fkey",
    "ALTER TABLE continuity_objects DROP CONSTRAINT IF EXISTS continuity_objects_supersedes_fkey",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS superseded_by_object_id",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS supersedes_object_id",
    "ALTER TABLE continuity_objects DROP COLUMN IF EXISTS last_confirmed_at",
    "ALTER TABLE continuity_objects DROP CONSTRAINT continuity_objects_status_check",
    (
        "ALTER TABLE continuity_objects "
        "ADD CONSTRAINT continuity_objects_status_check "
        "CHECK (status IN ('active', 'completed', 'cancelled', 'superseded', 'stale'))"
    ),
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_BOOTSTRAP_STATEMENTS)
    _execute_statements(_UPGRADE_SCHEMA_STATEMENTS)
    _execute_statements(_UPGRADE_TRIGGER_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    _execute_statements(_UPGRADE_POLICY_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
