from __future__ import annotations

from alembic import command
import psycopg

from alicebot_api.migrations import make_alembic_config


def test_tool_execution_task_step_linkage_migration_backfills_existing_rows(database_urls):
    config = make_alembic_config(database_urls["admin"])
    user_id = "00000000-0000-0000-0000-000000000001"
    thread_id = "00000000-0000-0000-0000-000000000002"
    trace_id = "00000000-0000-0000-0000-000000000003"
    tool_id = "00000000-0000-0000-0000-000000000004"
    approval_id = "00000000-0000-0000-0000-000000000005"
    task_id = "00000000-0000-0000-0000-000000000006"
    task_step_id = "00000000-0000-0000-0000-000000000007"
    execution_id = "00000000-0000-0000-0000-000000000008"

    command.upgrade(config, "20260313_0020")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, 'migration@example.com', 'Migration User')
                """,
                (user_id,),
            )
            cur.execute(
                """
                INSERT INTO threads (id, user_id, title)
                VALUES (%s, %s, 'Migration Thread')
                """,
                (thread_id, user_id),
            )
            cur.execute(
                """
                INSERT INTO traces (
                  id,
                  user_id,
                  thread_id,
                  kind,
                  compiler_version,
                  status,
                  limits
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  'migration.seed',
                  'v0',
                  'completed',
                  '{}'::jsonb
                )
                """,
                (trace_id, user_id, thread_id),
            )
            cur.execute(
                """
                INSERT INTO tools (
                  id,
                  user_id,
                  tool_key,
                  name,
                  description,
                  version,
                  metadata_version,
                  active,
                  tags,
                  action_hints,
                  scope_hints,
                  domain_hints,
                  risk_hints,
                  metadata
                )
                VALUES (
                  %s,
                  %s,
                  'proxy.echo',
                  'Proxy Echo',
                  'Seed tool for migration coverage',
                  '1.0.0',
                  'tool_metadata_v0',
                  TRUE,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '[]'::jsonb,
                  '{}'::jsonb
                )
                """,
                (tool_id, user_id),
            )
            cur.execute(
                """
                INSERT INTO approvals (
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  task_step_id,
                  status,
                  request,
                  tool,
                  routing,
                  routing_trace_id,
                  resolved_at,
                  resolved_by_user_id
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  NULL,
                  'approved',
                  '{"action":"echo"}'::jsonb,
                  '{"id":"tool"}'::jsonb,
                  '{"decision":"approval_required"}'::jsonb,
                  %s,
                  now(),
                  %s
                )
                """,
                (approval_id, user_id, thread_id, tool_id, trace_id, user_id),
            )
            cur.execute(
                """
                INSERT INTO tasks (
                  id,
                  user_id,
                  thread_id,
                  tool_id,
                  status,
                  request,
                  tool,
                  latest_approval_id,
                  latest_execution_id
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  'approved',
                  '{"action":"echo"}'::jsonb,
                  '{"id":"tool"}'::jsonb,
                  %s,
                  NULL
                )
                """,
                (task_id, user_id, thread_id, tool_id, approval_id),
            )
            cur.execute(
                """
                INSERT INTO task_steps (
                  id,
                  user_id,
                  task_id,
                  sequence_no,
                  kind,
                  status,
                  request,
                  outcome,
                  trace_id,
                  trace_kind
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  1,
                  'governed_request',
                  'approved',
                  '{"action":"echo"}'::jsonb,
                  '{"routing_decision":"approval_required","approval_id":"00000000-0000-0000-0000-000000000005","approval_status":"approved","execution_id":null,"execution_status":null,"blocked_reason":null}'::jsonb,
                  %s,
                  'migration.seed'
                )
                """,
                (task_step_id, user_id, task_id, trace_id),
            )
            cur.execute(
                """
                INSERT INTO tool_executions (
                  id,
                  user_id,
                  approval_id,
                  thread_id,
                  tool_id,
                  trace_id,
                  request_event_id,
                  result_event_id,
                  status,
                  handler_key,
                  request,
                  tool,
                  result
                )
                VALUES (
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  %s,
                  NULL,
                  NULL,
                  'blocked',
                  NULL,
                  '{"action":"echo"}'::jsonb,
                  '{"id":"tool"}'::jsonb,
                  '{"blocked_reason":"seed"}'::jsonb
                )
                """,
                (execution_id, user_id, approval_id, thread_id, tool_id, trace_id),
            )
        conn.commit()

    command.upgrade(config, "head")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT task_step_id
                FROM tool_executions
                WHERE id = %s
                """,
                (execution_id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert str(row[0]) == task_step_id
            cur.execute(
                """
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'tool_executions'
                  AND column_name = 'task_step_id'
                """
            )
            assert cur.fetchone() == ("NO",)


def test_gmail_account_credentials_migration_round_trip_preserves_tokens(database_urls):
    config = make_alembic_config(database_urls["admin"])
    user_id = "00000000-0000-0000-0000-000000000101"
    gmail_account_id = "00000000-0000-0000-0000-000000000102"

    command.upgrade(config, "20260316_0026")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, 'gmail-migration@example.com', 'Gmail Migration User')
                """,
                (user_id,),
            )
            cur.execute(
                """
                INSERT INTO gmail_accounts (
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope,
                  access_token
                )
                VALUES (
                  %s,
                  %s,
                  'acct-migration-001',
                  'owner@gmail.example',
                  'Owner',
                  'https://www.googleapis.com/auth/gmail.readonly',
                  'token-before-hardening'
                )
                """,
                (gmail_account_id, user_id),
            )
        conn.commit()

    command.upgrade(config, "20260316_0027")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'gmail_accounts'
                  AND column_name = 'access_token'
                """
            )
            assert cur.fetchone() is None
            cur.execute(
                """
                SELECT
                  auth_kind,
                  credential_blob ->> 'credential_kind',
                  credential_blob ->> 'access_token'
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """,
                (gmail_account_id,),
            )
            assert cur.fetchone() == (
                "oauth_access_token",
                "gmail_oauth_access_token_v1",
                "token-before-hardening",
            )

    command.downgrade(config, "20260316_0026")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'gmail_accounts'
                  AND column_name = 'access_token'
                """
            )
            assert cur.fetchone() == ("access_token",)
            cur.execute(
                """
                SELECT access_token
                FROM gmail_accounts
                WHERE id = %s
                """,
                (gmail_account_id,),
            )
            assert cur.fetchone() == ("token-before-hardening",)
            cur.execute("SELECT to_regclass('public.gmail_account_credentials')")
            assert cur.fetchone() == (None,)


def test_gmail_refresh_token_lifecycle_migration_round_trip_preserves_downgrade_compatibility(
    database_urls,
):
    config = make_alembic_config(database_urls["admin"])
    user_id = "00000000-0000-0000-0000-000000000201"
    gmail_account_id = "00000000-0000-0000-0000-000000000202"

    command.upgrade(config, "20260316_0027")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, 'gmail-refresh@example.com', 'Gmail Refresh User')
                """,
                (user_id,),
            )
            cur.execute(
                """
                INSERT INTO gmail_accounts (
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope
                )
                VALUES (
                  %s,
                  %s,
                  'acct-refresh-001',
                  'owner@gmail.example',
                  'Owner',
                  'https://www.googleapis.com/auth/gmail.readonly'
                )
                """,
                (gmail_account_id, user_id),
            )
            cur.execute(
                """
                INSERT INTO gmail_account_credentials (
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_blob
                )
                VALUES (
                  %s,
                  %s,
                  'oauth_access_token',
                  jsonb_build_object(
                    'credential_kind', 'gmail_oauth_access_token_v1',
                    'access_token', 'token-before-refresh-lifecycle'
                  )
                )
                """,
                (gmail_account_id, user_id),
            )
        conn.commit()

    command.upgrade(config, "20260316_0028")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE gmail_account_credentials
                SET credential_blob = jsonb_build_object(
                  'credential_kind', 'gmail_oauth_refresh_token_v2',
                  'access_token', 'token-after-refresh',
                  'refresh_token', 'refresh-001',
                  'client_id', 'client-001',
                  'client_secret', 'secret-001',
                  'access_token_expires_at', '2030-01-01T00:05:00+00:00'
                )
                WHERE gmail_account_id = %s
                """,
                (gmail_account_id,),
            )
            cur.execute(
                """
                SELECT
                  credential_blob ->> 'credential_kind',
                  credential_blob ->> 'access_token',
                  credential_blob ->> 'refresh_token'
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """,
                (gmail_account_id,),
            )
            assert cur.fetchone() == (
                "gmail_oauth_refresh_token_v2",
                "token-after-refresh",
                "refresh-001",
            )
        conn.commit()

    command.downgrade(config, "20260316_0027")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  credential_blob ->> 'credential_kind',
                  credential_blob ->> 'access_token',
                  credential_blob ? 'refresh_token'
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """,
                (gmail_account_id,),
            )
            assert cur.fetchone() == (
                "gmail_oauth_access_token_v1",
                "token-after-refresh",
                False,
            )


def test_gmail_external_secret_manager_migration_round_trip_preserves_legacy_transition_rows(
    database_urls,
):
    config = make_alembic_config(database_urls["admin"])
    user_id = "00000000-0000-0000-0000-000000000301"
    gmail_account_id = "00000000-0000-0000-0000-000000000302"

    command.upgrade(config, "20260316_0028")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, 'gmail-secret-manager@example.com', 'Gmail Secret Manager User')
                """,
                (user_id,),
            )
            cur.execute(
                """
                INSERT INTO gmail_accounts (
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope
                )
                VALUES (
                  %s,
                  %s,
                  'acct-secret-manager-001',
                  'owner@gmail.example',
                  'Owner',
                  'https://www.googleapis.com/auth/gmail.readonly'
                )
                """,
                (gmail_account_id, user_id),
            )
            cur.execute(
                """
                INSERT INTO gmail_account_credentials (
                  gmail_account_id,
                  user_id,
                  auth_kind,
                  credential_blob
                )
                VALUES (
                  %s,
                  %s,
                  'oauth_access_token',
                  jsonb_build_object(
                    'credential_kind', 'gmail_oauth_refresh_token_v2',
                    'access_token', 'token-before-externalization',
                    'refresh_token', 'refresh-001',
                    'client_id', 'client-001',
                    'client_secret', 'secret-001',
                    'access_token_expires_at', '2030-01-01T00:05:00+00:00'
                  )
                )
                """,
                (gmail_account_id, user_id),
            )
        conn.commit()

    command.upgrade(config, "20260316_0029")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob ->> 'access_token'
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """,
                (gmail_account_id,),
            )
            assert cur.fetchone() == (
                "gmail_oauth_refresh_token_v2",
                "legacy_db_v0",
                None,
                "token-before-externalization",
            )

    command.downgrade(config, "20260316_0028")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  credential_blob ->> 'credential_kind',
                  credential_blob ->> 'access_token',
                  credential_blob ->> 'refresh_token'
                FROM gmail_account_credentials
                WHERE gmail_account_id = %s
                """,
                (gmail_account_id,),
            )
            assert cur.fetchone() == (
                "gmail_oauth_refresh_token_v2",
                "token-before-externalization",
                "refresh-001",
            )


def test_calendar_account_migration_round_trip_preserves_table_shape(database_urls):
    config = make_alembic_config(database_urls["admin"])
    user_id = "00000000-0000-0000-0000-000000000401"
    calendar_account_id = "00000000-0000-0000-0000-000000000402"

    command.upgrade(config, "20260316_0029")
    command.upgrade(config, "20260319_0030")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, 'calendar-migration@example.com', 'Calendar Migration User')
                """,
                (user_id,),
            )
            cur.execute(
                """
                INSERT INTO calendar_accounts (
                  id,
                  user_id,
                  provider_account_id,
                  email_address,
                  display_name,
                  scope
                )
                VALUES (
                  %s,
                  %s,
                  'acct-calendar-001',
                  'owner@gmail.example',
                  'Owner',
                  'https://www.googleapis.com/auth/calendar.readonly'
                )
                """,
                (calendar_account_id, user_id),
            )
            cur.execute(
                """
                INSERT INTO calendar_account_credentials (
                  calendar_account_id,
                  user_id,
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob
                )
                VALUES (
                  %s,
                  %s,
                  'oauth_access_token',
                  'calendar_oauth_access_token_v1',
                  'file_v1',
                  'users/00000000-0000-0000-0000-000000000401/calendar-account-credentials/cred.json',
                  NULL
                )
                """,
                (calendar_account_id, user_id),
            )
        conn.commit()

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  auth_kind,
                  credential_kind,
                  secret_manager_kind,
                  secret_ref,
                  credential_blob IS NULL
                FROM calendar_account_credentials
                WHERE calendar_account_id = %s
                """,
                (calendar_account_id,),
            )
            assert cur.fetchone() == (
                "oauth_access_token",
                "calendar_oauth_access_token_v1",
                "file_v1",
                "users/00000000-0000-0000-0000-000000000401/calendar-account-credentials/cred.json",
                True,
            )

    command.downgrade(config, "20260316_0029")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.calendar_account_credentials')")
            assert cur.fetchone() == (None,)
            cur.execute("SELECT to_regclass('public.calendar_accounts')")
            assert cur.fetchone() == (None,)


def test_migrations_upgrade_and_downgrade(database_urls):
    config = make_alembic_config(database_urls["admin"])

    command.upgrade(config, "head")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.users')")
            assert cur.fetchone()[0] == "users"
            cur.execute("SELECT to_regclass('public.threads')")
            assert cur.fetchone()[0] == "threads"
            cur.execute("SELECT to_regclass('public.sessions')")
            assert cur.fetchone()[0] == "sessions"
            cur.execute("SELECT to_regclass('public.events')")
            assert cur.fetchone()[0] == "events"
            cur.execute("SELECT to_regclass('public.memories')")
            assert cur.fetchone()[0] == "memories"
            cur.execute("SELECT to_regclass('public.memory_revisions')")
            assert cur.fetchone()[0] == "memory_revisions"
            cur.execute("SELECT to_regclass('public.memory_review_labels')")
            assert cur.fetchone()[0] == "memory_review_labels"
            cur.execute("SELECT to_regclass('public.entities')")
            assert cur.fetchone()[0] == "entities"
            cur.execute("SELECT to_regclass('public.entity_edges')")
            assert cur.fetchone()[0] == "entity_edges"
            cur.execute("SELECT to_regclass('public.embedding_configs')")
            assert cur.fetchone()[0] == "embedding_configs"
            cur.execute("SELECT to_regclass('public.memory_embeddings')")
            assert cur.fetchone()[0] == "memory_embeddings"
            cur.execute("SELECT to_regclass('public.consents')")
            assert cur.fetchone()[0] == "consents"
            cur.execute("SELECT to_regclass('public.policies')")
            assert cur.fetchone()[0] == "policies"
            cur.execute("SELECT to_regclass('public.tools')")
            assert cur.fetchone()[0] == "tools"
            cur.execute("SELECT to_regclass('public.approvals')")
            assert cur.fetchone()[0] == "approvals"
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'approvals'
                  AND column_name = 'task_step_id'
                """
            )
            assert cur.fetchall() == [("task_step_id",)]
            cur.execute("SELECT to_regclass('public.tasks')")
            assert cur.fetchone()[0] == "tasks"
            cur.execute("SELECT to_regclass('public.task_workspaces')")
            assert cur.fetchone()[0] == "task_workspaces"
            cur.execute("SELECT to_regclass('public.task_artifacts')")
            assert cur.fetchone()[0] == "task_artifacts"
            cur.execute("SELECT to_regclass('public.task_artifact_chunks')")
            assert cur.fetchone()[0] == "task_artifact_chunks"
            cur.execute("SELECT to_regclass('public.task_artifact_chunk_embeddings')")
            assert cur.fetchone()[0] == "task_artifact_chunk_embeddings"
            cur.execute("SELECT to_regclass('public.task_steps')")
            assert cur.fetchone()[0] == "task_steps"
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'task_steps'
                  AND column_name IN (
                    'parent_step_id',
                    'source_approval_id',
                    'source_execution_id'
                  )
                ORDER BY column_name
                """
            )
            assert cur.fetchall() == [
                ("parent_step_id",),
                ("source_approval_id",),
                ("source_execution_id",),
            ]
            cur.execute("SELECT to_regclass('public.tool_executions')")
            assert cur.fetchone()[0] == "tool_executions"
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'tool_executions'
                  AND column_name = 'task_step_id'
                """
            )
            assert cur.fetchall() == [("task_step_id",)]
            cur.execute("SELECT to_regclass('public.execution_budgets')")
            assert cur.fetchone()[0] == "execution_budgets"
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'execution_budgets'
                  AND column_name IN (
                    'status',
                    'deactivated_at',
                    'superseded_by_budget_id',
                    'supersedes_budget_id'
                  )
                ORDER BY column_name
                """
            )
            assert cur.fetchall() == [
                ("deactivated_at",),
                ("status",),
                ("superseded_by_budget_id",),
                ("supersedes_budget_id",),
            ]
            cur.execute(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class AS c
                JOIN pg_namespace AS n
                  ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname IN (
                    'users',
                    'threads',
                    'sessions',
                    'events',
                    'memories',
                    'memory_revisions',
                    'memory_review_labels',
                    'entities',
                    'entity_edges',
                    'embedding_configs',
                    'memory_embeddings',
                    'consents',
                    'policies',
                    'tools',
                    'approvals',
                    'tasks',
                    'task_workspaces',
                    'task_artifacts',
                    'task_artifact_chunks',
                    'task_artifact_chunk_embeddings',
                    'task_steps',
                    'execution_budgets',
                    'tool_executions'
                  )
                ORDER BY c.relname
                """
            )
            assert cur.fetchall() == [
                ("approvals", True, True),
                ("consents", True, True),
                ("embedding_configs", True, True),
                ("entities", True, True),
                ("entity_edges", True, True),
                ("events", True, True),
                ("execution_budgets", True, True),
                ("memories", True, True),
                ("memory_embeddings", True, True),
                ("memory_review_labels", True, True),
                ("memory_revisions", True, True),
                ("policies", True, True),
                ("sessions", True, True),
                ("task_artifact_chunk_embeddings", True, True),
                ("task_artifact_chunks", True, True),
                ("task_artifacts", True, True),
                ("task_steps", True, True),
                ("task_workspaces", True, True),
                ("tasks", True, True),
                ("threads", True, True),
                ("tool_executions", True, True),
                ("tools", True, True),
                ("users", True, True),
            ]
            cur.execute(
                """
                SELECT tgname
                FROM pg_trigger
                WHERE tgrelid = 'events'::regclass
                  AND NOT tgisinternal
                """
            )
            assert cur.fetchall() == [("events_append_only",)]
            cur.execute(
                """
                SELECT tgname
                FROM pg_trigger
                WHERE tgrelid = 'memory_revisions'::regclass
                  AND NOT tgisinternal
                """
            )
            assert cur.fetchall() == [("memory_revisions_append_only",)]
            cur.execute(
                """
                SELECT tgname
                FROM pg_trigger
                WHERE tgrelid = 'memory_review_labels'::regclass
                  AND NOT tgisinternal
                """
            )
            assert cur.fetchall() == [("memory_review_labels_append_only",)]
            cur.execute(
                """
                SELECT
                  has_table_privilege('alicebot_app', 'users', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'threads', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'sessions', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'memories', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'memory_revisions', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'memory_revisions', 'DELETE'),
                  has_table_privilege('alicebot_app', 'memory_review_labels', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'memory_review_labels', 'DELETE'),
                  has_table_privilege('alicebot_app', 'entities', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'entities', 'DELETE'),
                  has_table_privilege('alicebot_app', 'entity_edges', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'entity_edges', 'DELETE'),
                  has_table_privilege('alicebot_app', 'embedding_configs', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'embedding_configs', 'DELETE'),
                  has_table_privilege('alicebot_app', 'memory_embeddings', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'memory_embeddings', 'DELETE'),
                  has_table_privilege('alicebot_app', 'consents', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'consents', 'DELETE'),
                  has_table_privilege('alicebot_app', 'policies', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'policies', 'DELETE'),
                  has_table_privilege('alicebot_app', 'tools', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'tools', 'DELETE'),
                  has_table_privilege('alicebot_app', 'approvals', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'approvals', 'DELETE'),
                  has_table_privilege('alicebot_app', 'tasks', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'tasks', 'DELETE'),
                  has_table_privilege('alicebot_app', 'task_workspaces', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'task_workspaces', 'DELETE'),
                  has_table_privilege('alicebot_app', 'task_artifacts', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'task_artifacts', 'DELETE'),
                  has_table_privilege('alicebot_app', 'task_artifact_chunks', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'task_artifact_chunks', 'DELETE'),
                  has_table_privilege('alicebot_app', 'task_artifact_chunk_embeddings', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'task_artifact_chunk_embeddings', 'DELETE'),
                  has_table_privilege('alicebot_app', 'task_steps', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'task_steps', 'DELETE'),
                  has_table_privilege('alicebot_app', 'execution_budgets', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'execution_budgets', 'DELETE'),
                  has_table_privilege('alicebot_app', 'tool_executions', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'tool_executions', 'DELETE')
                """
            )
            assert cur.fetchone() == (
                False,
                False,
                False,
                True,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                False,
                True,
                False,
                True,
                False,
                False,
                False,
                False,
                False,
                True,
                False,
                True,
                False,
                False,
                False,
                True,
                False,
                False,
                False,
                True,
                False,
                True,
                False,
                True,
                False,
                False,
                False,
            )

    command.downgrade(config, "20260314_0024")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.task_artifact_chunk_embeddings')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.task_artifact_chunks')")
            assert cur.fetchone()[0] == "task_artifact_chunks"
            cur.execute("SELECT to_regclass('public.task_artifacts')")
            assert cur.fetchone()[0] == "task_artifacts"
            cur.execute("SELECT to_regclass('public.task_workspaces')")
            assert cur.fetchone()[0] == "task_workspaces"

    command.downgrade(config, "20260313_0021")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.task_artifact_chunks')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.task_artifact_chunk_embeddings')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.task_artifacts')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.task_workspaces')")
            assert cur.fetchone()[0] is None
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'approvals'
                  AND column_name = 'task_step_id'
                """
            )
            assert cur.fetchall() == [("task_step_id",)]

    command.downgrade(config, "20260313_0018")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'approvals'
                  AND column_name = 'task_step_id'
                """
            )
            assert cur.fetchall() == []
            cur.execute("SELECT to_regclass('public.task_steps')")
            assert cur.fetchone()[0] == "task_steps"
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'tool_executions'
                  AND column_name = 'task_step_id'
                """
            )
            assert cur.fetchall() == []
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'task_steps'
                  AND column_name IN (
                    'parent_step_id',
                    'source_approval_id',
                    'source_execution_id'
                  )
                ORDER BY column_name
                """
            )
            assert cur.fetchall() == []
            cur.execute("SELECT to_regclass('public.tasks')")
            assert cur.fetchone()[0] == "tasks"

    command.downgrade(config, "20260313_0017")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.task_steps')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.tasks')")
            assert cur.fetchone()[0] == "tasks"

    command.downgrade(config, "20260313_0014")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.execution_budgets')")
            assert cur.fetchone()[0] == "execution_budgets"
            cur.execute("SELECT to_regclass('public.tasks')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.task_steps')")
            assert cur.fetchone()[0] is None
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'execution_budgets'
                  AND column_name IN (
                    'status',
                    'deactivated_at',
                    'superseded_by_budget_id',
                    'supersedes_budget_id'
                  )
                ORDER BY column_name
                """
            )
            assert cur.fetchall() == []
            cur.execute(
                "SELECT has_table_privilege('alicebot_app', 'execution_budgets', 'UPDATE')"
            )
            assert cur.fetchone()[0] is False

    command.downgrade(config, "20260313_0013")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.execution_budgets')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.tool_executions')")
            assert cur.fetchone()[0] == "tool_executions"

    command.downgrade(config, "20260312_0012")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.tool_executions')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.approvals')")
            assert cur.fetchone()[0] == "approvals"

    command.downgrade(config, "20260312_0011")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.approvals')")
            assert cur.fetchone()[0] == "approvals"
            cur.execute(
                """
                SELECT
                  has_table_privilege('alicebot_app', 'approvals', 'UPDATE'),
                  EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'approvals'
                      AND column_name = 'resolved_at'
                  ),
                  EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'approvals'
                      AND column_name = 'resolved_by_user_id'
                  )
                """
            )
            assert cur.fetchone() == (
                False,
                False,
                False,
            )

    command.downgrade(config, "20260312_0010")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.approvals')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.tools')")
            assert cur.fetchone()[0] == "tools"
            cur.execute("SELECT to_regclass('public.consents')")
            assert cur.fetchone()[0] == "consents"
            cur.execute("SELECT to_regclass('public.policies')")
            assert cur.fetchone()[0] == "policies"

    command.downgrade(config, "20260312_0009")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.approvals')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.tools')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.consents')")
            assert cur.fetchone()[0] == "consents"
            cur.execute("SELECT to_regclass('public.policies')")
            assert cur.fetchone()[0] == "policies"

    command.downgrade(config, "20260312_0008")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.consents')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.policies')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.tools')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.approvals')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.embedding_configs')")
            assert cur.fetchone()[0] == "embedding_configs"
            cur.execute("SELECT to_regclass('public.memory_embeddings')")
            assert cur.fetchone()[0] == "memory_embeddings"

    command.downgrade(config, "20260312_0007")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.embedding_configs')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memory_embeddings')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.consents')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.policies')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.tools')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.approvals')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memories')")
            assert cur.fetchone()[0] == "memories"
            cur.execute("SELECT to_regclass('public.entity_edges')")
            assert cur.fetchone()[0] == "entity_edges"

    command.downgrade(config, "20260311_0003")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.memories')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memory_revisions')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memory_review_labels')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.entities')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.entity_edges')")
            assert cur.fetchone()[0] is None
            cur.execute(
                """
                SELECT
                  has_table_privilege('alicebot_app', 'users', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'threads', 'UPDATE'),
                  has_table_privilege('alicebot_app', 'sessions', 'UPDATE')
                """
            )
            # Revision 20260310_0001 already leaves the runtime role without UPDATE
            # access, so downgrading from head must preserve that same privilege floor.
            assert cur.fetchone() == (False, False, False)

    command.downgrade(config, "20260310_0001")

    command.downgrade(config, "base")

    with psycopg.connect(database_urls["admin"]) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.users')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.threads')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.sessions')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.events')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memories')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memory_revisions')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memory_review_labels')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.entities')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.entity_edges')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.embedding_configs')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.memory_embeddings')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.consents')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.policies')")
            assert cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.tools')")
            assert cur.fetchone()[0] is None
            cur.execute(
                """
                SELECT extname
                FROM pg_extension
                WHERE extname IN ('pgcrypto', 'vector')
                ORDER BY extname
                """
            )
            assert [row[0] for row in cur.fetchall()] == ["pgcrypto", "vector"]
