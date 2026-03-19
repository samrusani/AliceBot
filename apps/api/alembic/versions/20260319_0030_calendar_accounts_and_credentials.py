"""Add user-scoped Calendar account records with protected credentials."""

from __future__ import annotations

from alembic import op


revision = "20260319_0030"
down_revision = "20260316_0029"
branch_labels = None
depends_on = None

CALENDAR_AUTH_KIND_OAUTH_ACCESS_TOKEN = "oauth_access_token"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
CALENDAR_PROTECTED_CREDENTIAL_KIND = "calendar_oauth_access_token_v1"
CALENDAR_SECRET_MANAGER_KIND_FILE_V1 = "file_v1"

_RLS_TABLES = ("calendar_accounts", "calendar_account_credentials")

_UPGRADE_SCHEMA_STATEMENT = f"""
        CREATE TABLE calendar_accounts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider_account_id text NOT NULL,
          email_address text NOT NULL,
          display_name text,
          scope text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT calendar_accounts_provider_account_id_nonempty_check
            CHECK (length(provider_account_id) > 0),
          CONSTRAINT calendar_accounts_email_address_nonempty_check
            CHECK (length(email_address) > 0),
          CONSTRAINT calendar_accounts_display_name_nonempty_check
            CHECK (display_name IS NULL OR length(display_name) > 0),
          CONSTRAINT calendar_accounts_scope_readonly_check
            CHECK (scope = '{CALENDAR_READONLY_SCOPE}')
        );

        CREATE INDEX calendar_accounts_user_created_idx
          ON calendar_accounts (user_id, created_at, id);

        CREATE UNIQUE INDEX calendar_accounts_provider_account_idx
          ON calendar_accounts (user_id, provider_account_id);

        CREATE TABLE calendar_account_credentials (
          calendar_account_id uuid PRIMARY KEY REFERENCES calendar_accounts(id) ON DELETE CASCADE,
          user_id uuid NOT NULL,
          auth_kind text NOT NULL,
          credential_kind text NOT NULL,
          secret_manager_kind text NOT NULL,
          secret_ref text,
          credential_blob jsonb,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (calendar_account_id, user_id)
            REFERENCES calendar_accounts (id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT calendar_account_credentials_auth_kind_check
            CHECK (auth_kind = '{CALENDAR_AUTH_KIND_OAUTH_ACCESS_TOKEN}'),
          CONSTRAINT calendar_account_credentials_storage_shape_check
            CHECK (
              credential_kind = '{CALENDAR_PROTECTED_CREDENTIAL_KIND}'
              AND secret_manager_kind = '{CALENDAR_SECRET_MANAGER_KIND_FILE_V1}'
              AND secret_ref IS NOT NULL
              AND length(secret_ref) > 0
              AND credential_blob IS NULL
            )
        );

        CREATE INDEX calendar_account_credentials_user_created_idx
          ON calendar_account_credentials (user_id, created_at, calendar_account_id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON calendar_accounts TO alicebot_app",
    "GRANT SELECT, INSERT ON calendar_account_credentials TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENTS = (
    """
        CREATE POLICY calendar_accounts_is_owner ON calendar_accounts
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
    """,
    """
        CREATE POLICY calendar_account_credentials_is_owner ON calendar_account_credentials
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
    """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS calendar_account_credentials",
    "DROP TABLE IF EXISTS calendar_accounts",
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
    _execute_statements(_UPGRADE_POLICY_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
