"""Move Gmail access tokens into a protected credential table."""

from __future__ import annotations

from alembic import op


revision = "20260316_0027"
down_revision = "20260316_0026"
branch_labels = None
depends_on = None

GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN = "oauth_access_token"
GMAIL_PROTECTED_CREDENTIAL_KIND = "gmail_oauth_access_token_v1"

_RLS_TABLES = ("gmail_account_credentials",)

_UPGRADE_SCHEMA_STATEMENT = f"""
        CREATE TABLE gmail_account_credentials (
          gmail_account_id uuid PRIMARY KEY REFERENCES gmail_accounts(id) ON DELETE CASCADE,
          user_id uuid NOT NULL,
          auth_kind text NOT NULL,
          credential_blob jsonb NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (gmail_account_id, user_id)
            REFERENCES gmail_accounts (id, user_id)
            ON DELETE CASCADE,
          CONSTRAINT gmail_account_credentials_auth_kind_check
            CHECK (auth_kind = '{GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN}'),
          CONSTRAINT gmail_account_credentials_blob_shape_check
            CHECK (
              jsonb_typeof(credential_blob) = 'object'
              AND credential_blob ? 'credential_kind'
              AND credential_blob ? 'access_token'
              AND credential_blob ->> 'credential_kind' = '{GMAIL_PROTECTED_CREDENTIAL_KIND}'
              AND jsonb_typeof(credential_blob -> 'access_token') = 'string'
              AND length(credential_blob ->> 'access_token') > 0
            )
        );

        CREATE INDEX gmail_account_credentials_user_created_idx
          ON gmail_account_credentials (user_id, created_at, gmail_account_id);
        """

_UPGRADE_BACKFILL_STATEMENT = f"""
        INSERT INTO gmail_account_credentials (
          gmail_account_id,
          user_id,
          auth_kind,
          credential_blob,
          created_at,
          updated_at
        )
        SELECT
          id,
          user_id,
          '{GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN}',
          jsonb_build_object(
            'credential_kind', '{GMAIL_PROTECTED_CREDENTIAL_KIND}',
            'access_token', access_token
          ),
          created_at,
          updated_at
        FROM gmail_accounts;
        """

_UPGRADE_DROP_PLAINTEXT_STATEMENTS = (
    "ALTER TABLE gmail_accounts DROP CONSTRAINT gmail_accounts_access_token_nonempty_check",
    "ALTER TABLE gmail_accounts DROP COLUMN access_token",
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT ON gmail_account_credentials TO alicebot_app",
)

_UPGRADE_POLICY_STATEMENT = """
        CREATE POLICY gmail_account_credentials_is_owner ON gmail_account_credentials
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """

_DOWNGRADE_ADD_PLAINTEXT_STATEMENTS = (
    "ALTER TABLE gmail_accounts ADD COLUMN access_token text",
)

_DOWNGRADE_BACKFILL_STATEMENT = """
        UPDATE gmail_accounts AS accounts
        SET access_token = credentials.credential_blob ->> 'access_token'
        FROM gmail_account_credentials AS credentials
        WHERE credentials.gmail_account_id = accounts.id
        """

_DOWNGRADE_RESTORE_CONSTRAINT_STATEMENTS = (
    "ALTER TABLE gmail_accounts ALTER COLUMN access_token SET NOT NULL",
    """
        ALTER TABLE gmail_accounts
        ADD CONSTRAINT gmail_accounts_access_token_nonempty_check
          CHECK (length(access_token) > 0)
    """,
    "DROP TABLE IF EXISTS gmail_account_credentials",
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
    op.execute(_UPGRADE_BACKFILL_STATEMENT)
    _execute_statements(_UPGRADE_DROP_PLAINTEXT_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)
    _enable_row_level_security()
    op.execute(_UPGRADE_POLICY_STATEMENT)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_ADD_PLAINTEXT_STATEMENTS)
    op.execute(_DOWNGRADE_BACKFILL_STATEMENT)
    _execute_statements(_DOWNGRADE_RESTORE_CONSTRAINT_STATEMENTS)
