"""Add Phase 12 explicit memory mutation candidate and operation tables."""

from __future__ import annotations

from alembic import op


revision = "20260414_0058"
down_revision = "20260414_0057"
branch_labels = None
depends_on = None

_RLS_TABLES = (
    "memory_operation_candidates",
    "memory_operations",
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE memory_operation_candidates (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          sync_fingerprint text NOT NULL,
          source_kind text NOT NULL,
          source_candidate_id text NOT NULL,
          source_candidate_type text NOT NULL,
          candidate_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          source_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
          operation_type text NOT NULL,
          operation_reason text NOT NULL,
          policy_action text NOT NULL,
          policy_reason text NOT NULL,
          target_continuity_object_id uuid NULL,
          target_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
          applied_operation_id uuid NULL,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          applied_at timestamptz NULL,
          UNIQUE (id, user_id),
          UNIQUE (user_id, sync_fingerprint, source_candidate_id),
          CONSTRAINT memory_operation_candidates_sync_fingerprint_length_check
            CHECK (char_length(sync_fingerprint) >= 1 AND char_length(sync_fingerprint) <= 200),
          CONSTRAINT memory_operation_candidates_source_kind_length_check
            CHECK (char_length(source_kind) >= 1 AND char_length(source_kind) <= 80),
          CONSTRAINT memory_operation_candidates_source_candidate_id_length_check
            CHECK (char_length(source_candidate_id) >= 1 AND char_length(source_candidate_id) <= 120),
          CONSTRAINT memory_operation_candidates_source_candidate_type_length_check
            CHECK (char_length(source_candidate_type) >= 1 AND char_length(source_candidate_type) <= 40),
          CONSTRAINT memory_operation_candidates_candidate_payload_object_check
            CHECK (jsonb_typeof(candidate_payload) = 'object'),
          CONSTRAINT memory_operation_candidates_source_scope_object_check
            CHECK (jsonb_typeof(source_scope) = 'object'),
          CONSTRAINT memory_operation_candidates_operation_type_check
            CHECK (operation_type IN ('ADD', 'UPDATE', 'SUPERSEDE', 'DELETE', 'NOOP')),
          CONSTRAINT memory_operation_candidates_operation_reason_length_check
            CHECK (char_length(operation_reason) >= 1 AND char_length(operation_reason) <= 200),
          CONSTRAINT memory_operation_candidates_policy_action_check
            CHECK (policy_action IN ('auto_apply', 'review_required', 'skip')),
          CONSTRAINT memory_operation_candidates_policy_reason_length_check
            CHECK (char_length(policy_reason) >= 1 AND char_length(policy_reason) <= 200)
        );

        CREATE TABLE memory_operations (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          candidate_id uuid NOT NULL,
          operation_type text NOT NULL,
          status text NOT NULL,
          sync_fingerprint text NOT NULL,
          target_continuity_object_id uuid NULL,
          resulting_continuity_object_id uuid NULL,
          correction_event_id uuid NULL,
          before_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
          after_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
          details jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          CONSTRAINT memory_operations_candidate_fkey
            FOREIGN KEY (candidate_id, user_id)
            REFERENCES memory_operation_candidates(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT memory_operations_operation_type_check
            CHECK (operation_type IN ('ADD', 'UPDATE', 'SUPERSEDE', 'DELETE', 'NOOP')),
          CONSTRAINT memory_operations_status_check
            CHECK (status IN ('applied', 'no_op', 'skipped', 'duplicate')),
          CONSTRAINT memory_operations_sync_fingerprint_length_check
            CHECK (char_length(sync_fingerprint) >= 1 AND char_length(sync_fingerprint) <= 200),
          CONSTRAINT memory_operations_before_snapshot_object_check
            CHECK (jsonb_typeof(before_snapshot) = 'object'),
          CONSTRAINT memory_operations_after_snapshot_object_check
            CHECK (jsonb_typeof(after_snapshot) = 'object'),
          CONSTRAINT memory_operations_details_object_check
            CHECK (jsonb_typeof(details) = 'object')
        );

        CREATE INDEX memory_operation_candidates_user_created_idx
          ON memory_operation_candidates (user_id, created_at DESC, id DESC);
        CREATE INDEX memory_operation_candidates_policy_idx
          ON memory_operation_candidates (user_id, policy_action, created_at DESC, id DESC);
        CREATE INDEX memory_operation_candidates_target_idx
          ON memory_operation_candidates (user_id, target_continuity_object_id, created_at DESC, id DESC);
        CREATE INDEX memory_operations_user_created_idx
          ON memory_operations (user_id, created_at DESC, id DESC);
        CREATE INDEX memory_operations_candidate_idx
          ON memory_operations (user_id, candidate_id, created_at DESC, id DESC);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON memory_operation_candidates TO alicebot_app",
    "GRANT SELECT, INSERT ON memory_operations TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY memory_operation_candidates_read_own ON memory_operation_candidates
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY memory_operation_candidates_insert_own ON memory_operation_candidates
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY memory_operation_candidates_update_own ON memory_operation_candidates
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY memory_operations_read_own ON memory_operations
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY memory_operations_insert_own ON memory_operations
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS memory_operations",
    "DROP TABLE IF EXISTS memory_operation_candidates",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def _enable_row_level_security() -> None:
    for table_name in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.execute(_UPGRADE_SCHEMA_STATEMENT)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
