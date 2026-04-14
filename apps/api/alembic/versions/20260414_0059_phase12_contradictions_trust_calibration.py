"""Add Phase 12 contradiction case and trust signal tables."""

from __future__ import annotations

from alembic import op


revision = "20260414_0059"
down_revision = "20260414_0058"
branch_labels = None
depends_on = None

_RLS_TABLES = (
    "contradiction_cases",
    "trust_signals",
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE contradiction_cases (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          canonical_key text NOT NULL,
          continuity_object_id uuid NOT NULL,
          counterpart_object_id uuid NOT NULL,
          kind text NOT NULL,
          status text NOT NULL,
          rationale text NOT NULL,
          detection_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          resolution_action text NULL,
          resolution_note text NULL,
          continuity_object_updated_at timestamptz NOT NULL,
          counterpart_object_updated_at timestamptz NOT NULL,
          resolved_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, canonical_key),
          CONSTRAINT contradiction_cases_continuity_object_fkey
            FOREIGN KEY (continuity_object_id, user_id)
            REFERENCES continuity_objects(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT contradiction_cases_counterpart_object_fkey
            FOREIGN KEY (counterpart_object_id, user_id)
            REFERENCES continuity_objects(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT contradiction_cases_canonical_key_length_check
            CHECK (char_length(canonical_key) >= 1 AND char_length(canonical_key) <= 500),
          CONSTRAINT contradiction_cases_kind_check
            CHECK (
              kind IN (
                'direct_fact_conflict',
                'preference_conflict',
                'temporal_conflict',
                'source_hierarchy_conflict'
              )
            ),
          CONSTRAINT contradiction_cases_status_check
            CHECK (status IN ('open', 'resolved', 'dismissed')),
          CONSTRAINT contradiction_cases_rationale_length_check
            CHECK (char_length(rationale) >= 1 AND char_length(rationale) <= 1000),
          CONSTRAINT contradiction_cases_detection_payload_object_check
            CHECK (jsonb_typeof(detection_payload) = 'object'),
          CONSTRAINT contradiction_cases_resolution_action_length_check
            CHECK (resolution_action IS NULL OR char_length(resolution_action) <= 60),
          CONSTRAINT contradiction_cases_resolution_note_length_check
            CHECK (resolution_note IS NULL OR char_length(resolution_note) <= 1000),
          CONSTRAINT contradiction_cases_distinct_object_check
            CHECK (continuity_object_id <> counterpart_object_id)
        );

        CREATE TABLE trust_signals (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          continuity_object_id uuid NOT NULL,
          signal_key text NOT NULL,
          signal_type text NOT NULL,
          signal_state text NOT NULL,
          direction text NOT NULL,
          magnitude double precision NOT NULL,
          reason text NOT NULL,
          contradiction_case_id uuid NULL,
          related_continuity_object_id uuid NULL,
          payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, signal_key),
          CONSTRAINT trust_signals_continuity_object_fkey
            FOREIGN KEY (continuity_object_id, user_id)
            REFERENCES continuity_objects(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT trust_signals_contradiction_case_fkey
            FOREIGN KEY (contradiction_case_id, user_id)
            REFERENCES contradiction_cases(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT trust_signals_related_object_fkey
            FOREIGN KEY (related_continuity_object_id, user_id)
            REFERENCES continuity_objects(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT trust_signals_signal_key_length_check
            CHECK (char_length(signal_key) >= 1 AND char_length(signal_key) <= 500),
          CONSTRAINT trust_signals_signal_type_check
            CHECK (signal_type IN ('correction', 'corroboration', 'contradiction', 'weak_inference')),
          CONSTRAINT trust_signals_signal_state_check
            CHECK (signal_state IN ('active', 'inactive')),
          CONSTRAINT trust_signals_direction_check
            CHECK (direction IN ('positive', 'negative', 'neutral')),
          CONSTRAINT trust_signals_magnitude_range_check
            CHECK (magnitude >= 0.0 AND magnitude <= 1.0),
          CONSTRAINT trust_signals_reason_length_check
            CHECK (char_length(reason) >= 1 AND char_length(reason) <= 500),
          CONSTRAINT trust_signals_payload_object_check
            CHECK (jsonb_typeof(payload) = 'object')
        );

        CREATE INDEX contradiction_cases_user_status_idx
          ON contradiction_cases (user_id, status, updated_at DESC, id DESC);
        CREATE INDEX contradiction_cases_user_object_idx
          ON contradiction_cases (user_id, continuity_object_id, updated_at DESC, id DESC);
        CREATE INDEX contradiction_cases_user_counterpart_idx
          ON contradiction_cases (user_id, counterpart_object_id, updated_at DESC, id DESC);
        CREATE INDEX trust_signals_user_state_idx
          ON trust_signals (user_id, signal_state, updated_at DESC, id DESC);
        CREATE INDEX trust_signals_user_object_idx
          ON trust_signals (user_id, continuity_object_id, updated_at DESC, id DESC);
        CREATE INDEX trust_signals_case_idx
          ON trust_signals (user_id, contradiction_case_id, updated_at DESC, id DESC);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE ON contradiction_cases TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE ON trust_signals TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY contradiction_cases_read_own ON contradiction_cases
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY contradiction_cases_insert_own ON contradiction_cases
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY contradiction_cases_update_own ON contradiction_cases
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY trust_signals_read_own ON trust_signals
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY trust_signals_insert_own ON trust_signals
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY trust_signals_update_own ON trust_signals
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS trust_signals",
    "DROP TABLE IF EXISTS contradiction_cases",
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
