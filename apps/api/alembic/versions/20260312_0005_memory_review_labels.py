"""Add append-only memory review labels for human evaluation."""

from __future__ import annotations

from alembic import op


revision = "20260312_0005"
down_revision = "20260311_0004"
branch_labels = None
depends_on = None

_RLS_TABLES = ("memory_review_labels",)

_UPGRADE_BOOTSTRAP_STATEMENTS = (
    """
        CREATE OR REPLACE FUNCTION app.reject_memory_review_label_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'memory review labels are append-only';
        END;
        $$;
        """,
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE memory_review_labels (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          memory_id uuid NOT NULL,
          label text NOT NULL,
          note text,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          FOREIGN KEY (memory_id, user_id)
            REFERENCES memories(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT memory_review_labels_label_check
            CHECK (label IN ('correct', 'incorrect', 'outdated', 'insufficient_evidence')),
          CONSTRAINT memory_review_labels_note_length_check
            CHECK (note IS NULL OR char_length(note) <= 280)
        );

        CREATE INDEX memory_review_labels_memory_created_idx
          ON memory_review_labels (memory_id, created_at, id);
        """

_UPGRADE_TRIGGER_STATEMENT = """
        CREATE TRIGGER memory_review_labels_append_only
        BEFORE UPDATE OR DELETE ON memory_review_labels
        FOR EACH ROW
        EXECUTE FUNCTION app.reject_memory_review_label_mutation();
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON memory_review_labels TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY memory_review_labels_read_own ON memory_review_labels
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY memory_review_labels_insert_own ON memory_review_labels
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TRIGGER IF EXISTS memory_review_labels_append_only ON memory_review_labels",
    "DROP TABLE IF EXISTS memory_review_labels",
    "DROP FUNCTION IF EXISTS app.reject_memory_review_label_mutation()",
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
