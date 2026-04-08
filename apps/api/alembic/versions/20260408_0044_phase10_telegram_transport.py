"""Add Phase 10 Sprint 2 Telegram transport tables and routing receipts."""

from __future__ import annotations

from alembic import op


revision = "20260408_0044"
down_revision = "20260408_0043"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE channel_identities (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_type text NOT NULL,
          external_user_id text NOT NULL,
          external_chat_id text NOT NULL,
          external_username text NULL,
          status text NOT NULL DEFAULT 'linked',
          linked_at timestamptz NOT NULL DEFAULT now(),
          unlinked_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT channel_identities_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT channel_identities_status_check
            CHECK (status IN ('linked', 'unlinked')),
          CONSTRAINT channel_identities_external_user_id_length_check
            CHECK (char_length(external_user_id) >= 1 AND char_length(external_user_id) <= 160),
          CONSTRAINT channel_identities_external_chat_id_length_check
            CHECK (char_length(external_chat_id) >= 1 AND char_length(external_chat_id) <= 160)
        )
        """,
    (
        "CREATE UNIQUE INDEX channel_identities_linked_external_chat_uidx "
        "ON channel_identities (channel_type, external_chat_id) "
        "WHERE status = 'linked'"
    ),
    (
        "CREATE INDEX channel_identities_user_workspace_idx "
        "ON channel_identities (user_account_id, workspace_id, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE channel_link_challenges (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_account_id uuid NOT NULL REFERENCES user_accounts(id) ON DELETE CASCADE,
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_type text NOT NULL,
          challenge_token_hash text NOT NULL UNIQUE,
          link_code text NOT NULL UNIQUE,
          status text NOT NULL,
          expires_at timestamptz NOT NULL,
          confirmed_at timestamptz NULL,
          channel_identity_id uuid NULL REFERENCES channel_identities(id) ON DELETE SET NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT channel_link_challenges_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT channel_link_challenges_status_check
            CHECK (status IN ('pending', 'confirmed', 'expired', 'cancelled')),
          CONSTRAINT channel_link_challenges_link_code_length_check
            CHECK (char_length(link_code) >= 6 AND char_length(link_code) <= 32)
        )
        """,
    (
        "CREATE INDEX channel_link_challenges_user_workspace_status_idx "
        "ON channel_link_challenges (user_account_id, workspace_id, channel_type, status, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE channel_threads (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_type text NOT NULL,
          external_thread_key text NOT NULL,
          channel_identity_id uuid NULL REFERENCES channel_identities(id) ON DELETE SET NULL,
          last_message_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (workspace_id, channel_type, external_thread_key),
          CONSTRAINT channel_threads_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT channel_threads_external_thread_key_length_check
            CHECK (char_length(external_thread_key) >= 1 AND char_length(external_thread_key) <= 240)
        )
        """,
    (
        "CREATE INDEX channel_threads_workspace_last_message_idx "
        "ON channel_threads (workspace_id, channel_type, last_message_at DESC, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE channel_messages (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NULL REFERENCES workspaces(id) ON DELETE SET NULL,
          channel_thread_id uuid NULL REFERENCES channel_threads(id) ON DELETE SET NULL,
          channel_identity_id uuid NULL REFERENCES channel_identities(id) ON DELETE SET NULL,
          channel_type text NOT NULL,
          direction text NOT NULL,
          provider_update_id text NULL,
          provider_message_id text NULL,
          external_chat_id text NULL,
          external_user_id text NULL,
          message_text text NULL,
          normalized_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          route_status text NOT NULL,
          idempotency_key text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          received_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (channel_type, direction, idempotency_key),
          CONSTRAINT channel_messages_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT channel_messages_direction_check
            CHECK (direction IN ('inbound', 'outbound')),
          CONSTRAINT channel_messages_route_status_check
            CHECK (route_status IN ('resolved', 'unresolved')),
          CONSTRAINT channel_messages_idempotency_key_length_check
            CHECK (char_length(idempotency_key) >= 16 AND char_length(idempotency_key) <= 160)
        )
        """,
    (
        "CREATE UNIQUE INDEX channel_messages_inbound_update_uidx "
        "ON channel_messages (channel_type, provider_update_id) "
        "WHERE direction = 'inbound' AND provider_update_id IS NOT NULL"
    ),
    (
        "CREATE INDEX channel_messages_workspace_created_idx "
        "ON channel_messages (workspace_id, channel_type, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX channel_messages_thread_created_idx "
        "ON channel_messages (channel_thread_id, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE chat_intents (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_message_id uuid NOT NULL REFERENCES channel_messages(id) ON DELETE CASCADE,
          channel_thread_id uuid NULL REFERENCES channel_threads(id) ON DELETE SET NULL,
          intent_kind text NOT NULL,
          status text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (channel_message_id, intent_kind),
          CONSTRAINT chat_intents_intent_kind_check
            CHECK (intent_kind IN ('inbound_message')),
          CONSTRAINT chat_intents_status_check
            CHECK (status IN ('pending', 'recorded'))
        )
        """,
    (
        "CREATE INDEX chat_intents_workspace_created_idx "
        "ON chat_intents (workspace_id, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE channel_delivery_receipts (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          channel_message_id uuid NOT NULL UNIQUE REFERENCES channel_messages(id) ON DELETE CASCADE,
          channel_type text NOT NULL,
          status text NOT NULL,
          provider_receipt_id text NULL,
          failure_code text NULL,
          failure_detail text NULL,
          recorded_at timestamptz NOT NULL DEFAULT now(),
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT channel_delivery_receipts_channel_type_check
            CHECK (channel_type IN ('telegram')),
          CONSTRAINT channel_delivery_receipts_status_check
            CHECK (status IN ('delivered', 'failed', 'simulated'))
        )
        """,
    (
        "CREATE INDEX channel_delivery_receipts_workspace_recorded_idx "
        "ON channel_delivery_receipts (workspace_id, channel_type, recorded_at DESC, id DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON channel_identities TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON channel_link_challenges TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON channel_threads TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON channel_messages TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON chat_intents TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON channel_delivery_receipts TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP TABLE IF EXISTS channel_delivery_receipts",
    "DROP TABLE IF EXISTS chat_intents",
    "DROP INDEX IF EXISTS channel_messages_thread_created_idx",
    "DROP INDEX IF EXISTS channel_messages_workspace_created_idx",
    "DROP INDEX IF EXISTS channel_messages_inbound_update_uidx",
    "DROP TABLE IF EXISTS channel_messages",
    "DROP INDEX IF EXISTS channel_threads_workspace_last_message_idx",
    "DROP TABLE IF EXISTS channel_threads",
    "DROP INDEX IF EXISTS channel_link_challenges_user_workspace_status_idx",
    "DROP TABLE IF EXISTS channel_link_challenges",
    "DROP INDEX IF EXISTS channel_identities_user_workspace_idx",
    "DROP INDEX IF EXISTS channel_identities_linked_external_chat_uidx",
    "DROP TABLE IF EXISTS channel_identities",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
