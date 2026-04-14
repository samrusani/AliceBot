"""Add Phase 12 task-adaptive briefing persistence and model-pack strategy fields."""

from __future__ import annotations

from alembic import op


revision = "20260414_0061"
down_revision = "20260414_0060"
branch_labels = None
depends_on = None

_RLS_TABLES = ("task_briefs",)

_UPGRADE_MODEL_PACK_STATEMENTS = (
    """
        ALTER TABLE model_packs
        ADD COLUMN briefing_strategy text NOT NULL DEFAULT 'balanced',
        ADD COLUMN briefing_max_tokens integer NULL,
        ADD CONSTRAINT model_packs_briefing_strategy_check
          CHECK (briefing_strategy IN ('balanced', 'compact', 'detailed')),
        ADD CONSTRAINT model_packs_briefing_max_tokens_check
          CHECK (briefing_max_tokens IS NULL OR (briefing_max_tokens >= 32 AND briefing_max_tokens <= 4000))
    """,
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE task_briefs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          mode text NOT NULL,
          query_text text NULL,
          scope jsonb NOT NULL DEFAULT '{}'::jsonb,
          provider_strategy text NOT NULL,
          model_pack_strategy text NOT NULL,
          token_budget integer NOT NULL,
          estimated_tokens integer NOT NULL,
          item_count integer NOT NULL,
          deterministic_key text NOT NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          CONSTRAINT task_briefs_mode_check
            CHECK (mode IN ('user_recall', 'resume', 'worker_subtask', 'agent_handoff')),
          CONSTRAINT task_briefs_query_text_length_check
            CHECK (query_text IS NULL OR char_length(query_text) <= 4000),
          CONSTRAINT task_briefs_scope_object_check
            CHECK (jsonb_typeof(scope) = 'object'),
          CONSTRAINT task_briefs_provider_strategy_length_check
            CHECK (char_length(provider_strategy) >= 1 AND char_length(provider_strategy) <= 80),
          CONSTRAINT task_briefs_model_pack_strategy_length_check
            CHECK (char_length(model_pack_strategy) >= 1 AND char_length(model_pack_strategy) <= 40),
          CONSTRAINT task_briefs_token_budget_check
            CHECK (token_budget >= 1 AND token_budget <= 4000),
          CONSTRAINT task_briefs_estimated_tokens_check
            CHECK (estimated_tokens >= 0),
          CONSTRAINT task_briefs_item_count_check
            CHECK (item_count >= 0),
          CONSTRAINT task_briefs_deterministic_key_length_check
            CHECK (char_length(deterministic_key) = 64),
          CONSTRAINT task_briefs_payload_object_check
            CHECK (jsonb_typeof(payload) = 'object')
        );

        CREATE INDEX task_briefs_user_created_idx
          ON task_briefs (user_id, created_at DESC, id DESC);
        CREATE INDEX task_briefs_user_mode_created_idx
          ON task_briefs (user_id, mode, created_at DESC, id DESC);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON task_briefs TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY task_briefs_read_own ON task_briefs
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY task_briefs_insert_own ON task_briefs
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS task_briefs",
    "ALTER TABLE model_packs DROP CONSTRAINT IF EXISTS model_packs_briefing_max_tokens_check",
    "ALTER TABLE model_packs DROP CONSTRAINT IF EXISTS model_packs_briefing_strategy_check",
    "ALTER TABLE model_packs DROP COLUMN IF EXISTS briefing_max_tokens",
    "ALTER TABLE model_packs DROP COLUMN IF EXISTS briefing_strategy",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _execute_statements(_UPGRADE_MODEL_PACK_STATEMENTS)
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
