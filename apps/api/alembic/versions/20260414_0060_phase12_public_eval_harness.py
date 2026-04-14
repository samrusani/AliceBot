"""Add Phase 12 public eval harness tables."""

from __future__ import annotations

from alembic import op


revision = "20260414_0060"
down_revision = "20260414_0059"
branch_labels = None
depends_on = None

_RLS_TABLES = (
    "eval_suites",
    "eval_cases",
    "eval_runs",
    "eval_results",
)

_UPGRADE_SCHEMA_STATEMENT = """
        CREATE TABLE eval_suites (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          suite_key text NOT NULL,
          title text NOT NULL,
          description text NOT NULL,
          evaluator_kind text NOT NULL,
          fixture_schema_version text NOT NULL,
          fixture_source_path text NOT NULL,
          case_count integer NOT NULL,
          suite_order integer NOT NULL,
          metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, suite_key),
          CONSTRAINT eval_suites_suite_key_length_check
            CHECK (char_length(suite_key) >= 1 AND char_length(suite_key) <= 120),
          CONSTRAINT eval_suites_title_length_check
            CHECK (char_length(title) >= 1 AND char_length(title) <= 200),
          CONSTRAINT eval_suites_description_length_check
            CHECK (char_length(description) >= 1 AND char_length(description) <= 1000),
          CONSTRAINT eval_suites_evaluator_kind_length_check
            CHECK (char_length(evaluator_kind) >= 1 AND char_length(evaluator_kind) <= 80),
          CONSTRAINT eval_suites_fixture_schema_version_length_check
            CHECK (char_length(fixture_schema_version) >= 1 AND char_length(fixture_schema_version) <= 80),
          CONSTRAINT eval_suites_fixture_source_path_length_check
            CHECK (char_length(fixture_source_path) >= 1 AND char_length(fixture_source_path) <= 200),
          CONSTRAINT eval_suites_case_count_non_negative_check
            CHECK (case_count >= 0),
          CONSTRAINT eval_suites_suite_order_positive_check
            CHECK (suite_order >= 1),
          CONSTRAINT eval_suites_metadata_object_check
            CHECK (jsonb_typeof(metadata) = 'object')
        );

        CREATE TABLE eval_cases (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          suite_id uuid NOT NULL,
          case_key text NOT NULL,
          title text NOT NULL,
          evaluator_kind text NOT NULL,
          case_order integer NOT NULL,
          fixture jsonb NOT NULL DEFAULT '{}'::jsonb,
          expectations jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          UNIQUE (user_id, suite_id, case_key),
          CONSTRAINT eval_cases_suite_fkey
            FOREIGN KEY (suite_id, user_id)
            REFERENCES eval_suites(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT eval_cases_case_key_length_check
            CHECK (char_length(case_key) >= 1 AND char_length(case_key) <= 120),
          CONSTRAINT eval_cases_title_length_check
            CHECK (char_length(title) >= 1 AND char_length(title) <= 200),
          CONSTRAINT eval_cases_evaluator_kind_length_check
            CHECK (char_length(evaluator_kind) >= 1 AND char_length(evaluator_kind) <= 80),
          CONSTRAINT eval_cases_case_order_positive_check
            CHECK (case_order >= 1),
          CONSTRAINT eval_cases_fixture_object_check
            CHECK (jsonb_typeof(fixture) = 'object'),
          CONSTRAINT eval_cases_expectations_object_check
            CHECK (jsonb_typeof(expectations) = 'object')
        );

        CREATE TABLE eval_runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          fixture_schema_version text NOT NULL,
          fixture_source_path text NOT NULL,
          requested_suite_keys jsonb NOT NULL DEFAULT '[]'::jsonb,
          status text NOT NULL,
          summary jsonb NOT NULL DEFAULT '{}'::jsonb,
          report jsonb NOT NULL DEFAULT '{}'::jsonb,
          report_digest text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          CONSTRAINT eval_runs_fixture_schema_version_length_check
            CHECK (char_length(fixture_schema_version) >= 1 AND char_length(fixture_schema_version) <= 80),
          CONSTRAINT eval_runs_fixture_source_path_length_check
            CHECK (char_length(fixture_source_path) >= 1 AND char_length(fixture_source_path) <= 200),
          CONSTRAINT eval_runs_requested_suite_keys_array_check
            CHECK (jsonb_typeof(requested_suite_keys) = 'array'),
          CONSTRAINT eval_runs_status_check
            CHECK (status IN ('pass', 'fail')),
          CONSTRAINT eval_runs_summary_object_check
            CHECK (jsonb_typeof(summary) = 'object'),
          CONSTRAINT eval_runs_report_object_check
            CHECK (jsonb_typeof(report) = 'object'),
          CONSTRAINT eval_runs_report_digest_length_check
            CHECK (char_length(report_digest) = 64)
        );

        CREATE TABLE eval_results (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          eval_run_id uuid NOT NULL,
          suite_key text NOT NULL,
          case_key text NOT NULL,
          status text NOT NULL,
          score double precision NOT NULL,
          summary jsonb NOT NULL DEFAULT '{}'::jsonb,
          details jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
          UNIQUE (id, user_id),
          CONSTRAINT eval_results_run_fkey
            FOREIGN KEY (eval_run_id, user_id)
            REFERENCES eval_runs(id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT eval_results_suite_key_length_check
            CHECK (char_length(suite_key) >= 1 AND char_length(suite_key) <= 120),
          CONSTRAINT eval_results_case_key_length_check
            CHECK (char_length(case_key) >= 1 AND char_length(case_key) <= 120),
          CONSTRAINT eval_results_status_check
            CHECK (status IN ('pass', 'fail')),
          CONSTRAINT eval_results_score_range_check
            CHECK (score >= 0.0 AND score <= 1.0),
          CONSTRAINT eval_results_summary_object_check
            CHECK (jsonb_typeof(summary) = 'object'),
          CONSTRAINT eval_results_details_object_check
            CHECK (jsonb_typeof(details) = 'object')
        );

        CREATE INDEX eval_suites_user_order_idx
          ON eval_suites (user_id, suite_order ASC, suite_key ASC);
        CREATE INDEX eval_cases_suite_order_idx
          ON eval_cases (user_id, suite_id, case_order ASC, case_key ASC);
        CREATE INDEX eval_runs_user_created_idx
          ON eval_runs (user_id, created_at DESC, id DESC);
        CREATE INDEX eval_results_run_suite_case_idx
          ON eval_results (user_id, eval_run_id, suite_key, case_key, created_at ASC, id ASC);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON eval_suites TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON eval_cases TO alicebot_app",
    "GRANT SELECT, INSERT ON eval_runs TO alicebot_app",
    "GRANT SELECT, INSERT ON eval_results TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY eval_suites_read_own ON eval_suites
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY eval_suites_insert_own ON eval_suites
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY eval_suites_update_own ON eval_suites
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY eval_suites_delete_own ON eval_suites
          FOR DELETE
          USING (user_id = app.current_user_id());

        CREATE POLICY eval_cases_read_own ON eval_cases
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY eval_cases_insert_own ON eval_cases
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY eval_cases_update_own ON eval_cases
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY eval_cases_delete_own ON eval_cases
          FOR DELETE
          USING (user_id = app.current_user_id());

        CREATE POLICY eval_runs_read_own ON eval_runs
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY eval_runs_insert_own ON eval_runs
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());

        CREATE POLICY eval_results_read_own ON eval_results
          FOR SELECT
          USING (user_id = app.current_user_id());

        CREATE POLICY eval_results_insert_own ON eval_results
          FOR INSERT
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS eval_results",
    "DROP TABLE IF EXISTS eval_runs",
    "DROP TABLE IF EXISTS eval_cases",
    "DROP TABLE IF EXISTS eval_suites",
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
