"""Add Phase 12 hybrid retrieval run and candidate trace tables."""

from __future__ import annotations

from alembic import op


revision = "20260414_0057"
down_revision = "20260412_0056"
branch_labels = None
depends_on = None

_RLS_TABLES = (
    "retrieval_runs",
    "retrieval_candidates",
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE retrieval_runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source_surface text NOT NULL,
          ranking_strategy text NOT NULL,
          query_text text NULL,
          request_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
          result_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
          exclusion_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
          candidate_count integer NOT NULL,
          selected_count integer NOT NULL,
          debug_enabled boolean NOT NULL DEFAULT FALSE,
          retention_until timestamptz NOT NULL,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          CONSTRAINT retrieval_runs_source_surface_length_check
            CHECK (char_length(source_surface) >= 1 AND char_length(source_surface) <= 80),
          CONSTRAINT retrieval_runs_ranking_strategy_check
            CHECK (ranking_strategy IN ('legacy_v1', 'hybrid_v2')),
          CONSTRAINT retrieval_runs_query_text_length_check
            CHECK (query_text IS NULL OR char_length(query_text) <= 4000),
          CONSTRAINT retrieval_runs_request_scope_object_check
            CHECK (jsonb_typeof(request_scope) = 'object'),
          CONSTRAINT retrieval_runs_result_ids_array_check
            CHECK (jsonb_typeof(result_ids) = 'array'),
          CONSTRAINT retrieval_runs_exclusion_summary_object_check
            CHECK (jsonb_typeof(exclusion_summary) = 'object'),
          CONSTRAINT retrieval_runs_candidate_count_nonnegative_check
            CHECK (candidate_count >= 0),
          CONSTRAINT retrieval_runs_selected_count_nonnegative_check
            CHECK (selected_count >= 0),
          CONSTRAINT retrieval_runs_selected_count_within_candidates_check
            CHECK (selected_count <= candidate_count)
        );

        CREATE TABLE retrieval_candidates (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          retrieval_run_id uuid NOT NULL,
          continuity_object_id uuid NOT NULL,
          rank integer NULL,
          selected boolean NOT NULL DEFAULT FALSE,
          exclusion_reason text NULL,
          lexical_score double precision NOT NULL,
          semantic_score double precision NOT NULL,
          entity_edge_score double precision NOT NULL,
          temporal_score double precision NOT NULL,
          trust_score double precision NOT NULL,
          relevance double precision NOT NULL,
          scope_matches jsonb NOT NULL DEFAULT '[]'::jsonb,
          stage_details jsonb NOT NULL DEFAULT '{}'::jsonb,
          ordering jsonb NOT NULL DEFAULT '{}'::jsonb,
          title text NOT NULL,
          object_type text NOT NULL,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          CONSTRAINT retrieval_candidates_run_fkey
            FOREIGN KEY (retrieval_run_id, user_id)
            REFERENCES retrieval_runs(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT retrieval_candidates_scope_matches_array_check
            CHECK (jsonb_typeof(scope_matches) = 'array'),
          CONSTRAINT retrieval_candidates_stage_details_object_check
            CHECK (jsonb_typeof(stage_details) = 'object'),
          CONSTRAINT retrieval_candidates_ordering_object_check
            CHECK (jsonb_typeof(ordering) = 'object'),
          CONSTRAINT retrieval_candidates_rank_positive_check
            CHECK (rank IS NULL OR rank >= 1),
          CONSTRAINT retrieval_candidates_exclusion_reason_length_check
            CHECK (exclusion_reason IS NULL OR char_length(exclusion_reason) <= 200),
          CONSTRAINT retrieval_candidates_title_length_check
            CHECK (char_length(title) >= 1 AND char_length(title) <= 280),
          CONSTRAINT retrieval_candidates_object_type_length_check
            CHECK (char_length(object_type) >= 1 AND char_length(object_type) <= 64),
          CONSTRAINT retrieval_candidates_status_length_check
            CHECK (char_length(status) >= 1 AND char_length(status) <= 32)
        );

        CREATE INDEX retrieval_runs_user_created_idx
          ON retrieval_runs (user_id, created_at DESC, id DESC);
        CREATE INDEX retrieval_runs_user_retention_idx
          ON retrieval_runs (user_id, retention_until ASC, id ASC);
        CREATE INDEX retrieval_candidates_run_rank_idx
          ON retrieval_candidates (retrieval_run_id, selected DESC, rank ASC, id ASC);
        CREATE INDEX retrieval_candidates_object_idx
          ON retrieval_candidates (user_id, continuity_object_id, created_at DESC, id DESC);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON retrieval_runs TO alicebot_app",
    "GRANT SELECT, INSERT ON retrieval_candidates TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY retrieval_runs_read_own ON retrieval_runs
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY retrieval_runs_insert_own ON retrieval_runs
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY retrieval_candidates_read_own ON retrieval_candidates
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY retrieval_candidates_insert_own ON retrieval_candidates
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS retrieval_candidates",
    "DROP TABLE IF EXISTS retrieval_runs",
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
