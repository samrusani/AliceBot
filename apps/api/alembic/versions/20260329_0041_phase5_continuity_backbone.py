"""Add Phase 5 continuity capture backbone and typed continuity objects."""

from __future__ import annotations

from alembic import op


revision = "20260329_0041"
down_revision = "20260327_0040"
branch_labels = None
depends_on = None

CONTINUITY_OBJECT_TYPES = (
    "Note",
    "MemoryFact",
    "Decision",
    "Commitment",
    "WaitingFor",
    "Blocker",
    "NextAction",
)

CAPTURE_EXPLICIT_SIGNALS = (
    "remember_this",
    "task",
    "decision",
    "commitment",
    "waiting_for",
    "blocker",
    "next_action",
    "note",
)

CAPTURE_ADMISSION_POSTURES = (
    "DERIVED",
    "TRIAGE",
)

_CONTINUITY_OBJECT_TYPES_SQL = ", ".join(f"'{value}'" for value in CONTINUITY_OBJECT_TYPES)
_CAPTURE_EXPLICIT_SIGNALS_SQL = ", ".join(f"'{value}'" for value in CAPTURE_EXPLICIT_SIGNALS)
_CAPTURE_ADMISSION_POSTURES_SQL = ", ".join(f"'{value}'" for value in CAPTURE_ADMISSION_POSTURES)

_RLS_TABLES = (
    "continuity_capture_events",
    "continuity_objects",
)

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.reject_continuity_capture_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'continuity capture events are append-only';
        END;
        $$;
        """,
)

_UPGRADE_SCHEMA_STATEMENT = f"""
        CREATE TABLE continuity_capture_events (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          raw_content text NOT NULL,
          explicit_signal text NULL,
          admission_posture text NOT NULL,
          admission_reason text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT continuity_capture_events_raw_content_length_check
            CHECK (char_length(raw_content) >= 1 AND char_length(raw_content) <= 4000),
          CONSTRAINT continuity_capture_events_explicit_signal_check
            CHECK (explicit_signal IS NULL OR explicit_signal IN ({_CAPTURE_EXPLICIT_SIGNALS_SQL})),
          CONSTRAINT continuity_capture_events_admission_posture_check
            CHECK (admission_posture IN ({_CAPTURE_ADMISSION_POSTURES_SQL})),
          CONSTRAINT continuity_capture_events_admission_reason_length_check
            CHECK (char_length(admission_reason) >= 1 AND char_length(admission_reason) <= 200)
        );

        CREATE TABLE continuity_objects (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          capture_event_id uuid NOT NULL,
          object_type text NOT NULL,
          status text NOT NULL,
          title text NOT NULL,
          body jsonb NOT NULL,
          provenance jsonb NOT NULL,
          confidence double precision NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, capture_event_id),
          CONSTRAINT continuity_objects_capture_event_fkey
            FOREIGN KEY (capture_event_id, user_id)
            REFERENCES continuity_capture_events(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT continuity_objects_object_type_check
            CHECK (object_type IN ({_CONTINUITY_OBJECT_TYPES_SQL})),
          CONSTRAINT continuity_objects_status_check
            CHECK (status IN ('active', 'completed', 'cancelled', 'superseded', 'stale')),
          CONSTRAINT continuity_objects_title_length_check
            CHECK (char_length(title) >= 1 AND char_length(title) <= 280),
          CONSTRAINT continuity_objects_confidence_range_check
            CHECK (confidence >= 0.0 AND confidence <= 1.0)
        );

        CREATE INDEX continuity_capture_events_user_created_idx
          ON continuity_capture_events (user_id, created_at DESC, id DESC);
        CREATE INDEX continuity_capture_events_user_posture_created_idx
          ON continuity_capture_events (user_id, admission_posture, created_at DESC, id DESC);
        CREATE INDEX continuity_objects_user_capture_idx
          ON continuity_objects (user_id, capture_event_id, created_at DESC, id DESC);
        CREATE INDEX continuity_objects_user_type_created_idx
          ON continuity_objects (user_id, object_type, created_at DESC, id DESC);
        """

_UPGRADE_TRIGGER_STATEMENT = """
        CREATE TRIGGER continuity_capture_events_append_only
        BEFORE UPDATE OR DELETE ON continuity_capture_events
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_continuity_capture_mutation();
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON continuity_capture_events TO alicebot_app",
    "GRANT SELECT, INSERT ON continuity_objects TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY continuity_capture_events_read_own ON continuity_capture_events
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY continuity_capture_events_insert_own ON continuity_capture_events
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY continuity_objects_read_own ON continuity_objects
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY continuity_objects_insert_own ON continuity_objects
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TRIGGER IF EXISTS continuity_capture_events_append_only ON continuity_capture_events",
    "DROP TABLE IF EXISTS continuity_objects",
    "DROP TABLE IF EXISTS continuity_capture_events",
    "DROP FUNCTION IF EXISTS app.reject_continuity_capture_mutation()",
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
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    op.execute(_UPGRADE_TRIGGER_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
