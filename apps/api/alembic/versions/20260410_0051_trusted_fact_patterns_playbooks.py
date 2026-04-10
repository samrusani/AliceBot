"""Add derived trusted-fact pattern and playbook tables."""

from __future__ import annotations

from alembic import op


revision = "20260410_0051"
down_revision = "20260410_0050"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE fact_patterns (
          id uuid PRIMARY KEY,
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          pattern_key text NOT NULL,
          title text NOT NULL,
          memory_type text NOT NULL,
          namespace_key text NOT NULL,
          fact_count integer NOT NULL,
          source_fact_ids jsonb NOT NULL,
          evidence_chain jsonb NOT NULL,
          explanation text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, pattern_key),
          CONSTRAINT fact_patterns_pattern_key_length_check
            CHECK (char_length(pattern_key) >= 1 AND char_length(pattern_key) <= 280),
          CONSTRAINT fact_patterns_title_length_check
            CHECK (char_length(title) >= 1 AND char_length(title) <= 280),
          CONSTRAINT fact_patterns_memory_type_length_check
            CHECK (char_length(memory_type) >= 1 AND char_length(memory_type) <= 100),
          CONSTRAINT fact_patterns_namespace_key_length_check
            CHECK (char_length(namespace_key) >= 1 AND char_length(namespace_key) <= 280),
          CONSTRAINT fact_patterns_fact_count_positive_check
            CHECK (fact_count >= 1)
        );
        """,
    """
        CREATE TABLE fact_playbooks (
          id uuid PRIMARY KEY,
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          playbook_key text NOT NULL,
          pattern_id uuid NOT NULL,
          pattern_key text NOT NULL,
          title text NOT NULL,
          memory_type text NOT NULL,
          source_fact_ids jsonb NOT NULL,
          source_pattern_ids jsonb NOT NULL,
          steps jsonb NOT NULL,
          explanation text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, playbook_key),
          CONSTRAINT fact_playbooks_pattern_fkey
            FOREIGN KEY (pattern_id, user_id)
            REFERENCES fact_patterns(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT fact_playbooks_playbook_key_length_check
            CHECK (char_length(playbook_key) >= 1 AND char_length(playbook_key) <= 280),
          CONSTRAINT fact_playbooks_pattern_key_length_check
            CHECK (char_length(pattern_key) >= 1 AND char_length(pattern_key) <= 280),
          CONSTRAINT fact_playbooks_title_length_check
            CHECK (char_length(title) >= 1 AND char_length(title) <= 280),
          CONSTRAINT fact_playbooks_memory_type_length_check
            CHECK (char_length(memory_type) >= 1 AND char_length(memory_type) <= 100)
        );
        """,
    """
        CREATE INDEX fact_patterns_user_memory_type_namespace_idx
          ON fact_patterns (user_id, memory_type, namespace_key, id);
        CREATE INDEX fact_playbooks_user_memory_type_pattern_idx
          ON fact_playbooks (user_id, memory_type, pattern_key, id);
        """,
    "GRANT SELECT, INSERT, UPDATE, DELETE ON fact_patterns TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON fact_playbooks TO alicebot_app",
    "ALTER TABLE fact_patterns ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE fact_patterns FORCE ROW LEVEL SECURITY",
    "ALTER TABLE fact_playbooks ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE fact_playbooks FORCE ROW LEVEL SECURITY",
    """
        CREATE POLICY fact_patterns_read_own ON fact_patterns
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY fact_patterns_insert_own ON fact_patterns
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY fact_patterns_update_own ON fact_patterns
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY fact_patterns_delete_own ON fact_patterns
          FOR DELETE
          USING (user_id = app.current_user_id());

        CREATE POLICY fact_playbooks_read_own ON fact_playbooks
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY fact_playbooks_insert_own ON fact_playbooks
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY fact_playbooks_update_own ON fact_playbooks
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY fact_playbooks_delete_own ON fact_playbooks
          FOR DELETE
          USING (user_id = app.current_user_id());
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS fact_playbooks",
    "DROP TABLE IF EXISTS fact_patterns",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
