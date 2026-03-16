"""Add user-scoped Gmail account records."""

from __future__ import annotations

from alembic import op


revision = "20260316_0026"
down_revision = "20260314_0025"
branch_labels = None
depends_on = None

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

_RLS_TABLES = ("gmail_accounts",)

_UPGRADE_SCHEMA_STATEMENT = f"""
        CREATE TABLE gmail_accounts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider_account_id text NOT NULL,
          email_address text NOT NULL,
          display_name text,
          scope text NOT NULL,
          access_token text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (id, user_id),
          CONSTRAINT gmail_accounts_provider_account_id_nonempty_check
            CHECK (length(provider_account_id) > 0),
          CONSTRAINT gmail_accounts_email_address_nonempty_check
            CHECK (length(email_address) > 0),
          CONSTRAINT gmail_accounts_display_name_nonempty_check
            CHECK (display_name IS NULL OR length(display_name) > 0),
          CONSTRAINT gmail_accounts_scope_readonly_check
            CHECK (scope = '{GMAIL_READONLY_SCOPE}'),
          CONSTRAINT gmail_accounts_access_token_nonempty_check
            CHECK (length(access_token) > 0)
        );

        CREATE INDEX gmail_accounts_user_created_idx
          ON gmail_accounts (user_id, created_at, id);

        CREATE UNIQUE INDEX gmail_accounts_provider_account_idx
          ON gmail_accounts (user_id, provider_account_id);
        """

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON gmail_accounts TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY gmail_accounts_is_owner ON gmail_accounts
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS gmail_accounts",
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
