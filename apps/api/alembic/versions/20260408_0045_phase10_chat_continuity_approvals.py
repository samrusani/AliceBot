"""Add Phase 10 Sprint 3 Telegram continuity routing, approvals, and review persistence."""

from __future__ import annotations

from alembic import op


revision = "20260408_0045"
down_revision = "20260408_0044"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE chat_intents
        ADD COLUMN intent_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN result_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
        ADD COLUMN handled_at timestamptz NULL
        """,
    "ALTER TABLE chat_intents DROP CONSTRAINT IF EXISTS chat_intents_intent_kind_check",
    """
        ALTER TABLE chat_intents
        ADD CONSTRAINT chat_intents_intent_kind_check
        CHECK (
          intent_kind IN (
            'inbound_message',
            'capture',
            'recall',
            'resume',
            'correction',
            'open_loops',
            'open_loop_review',
            'approvals',
            'approval_approve',
            'approval_reject',
            'unknown'
          )
        )
        """,
    "ALTER TABLE chat_intents DROP CONSTRAINT IF EXISTS chat_intents_status_check",
    """
        ALTER TABLE chat_intents
        ADD CONSTRAINT chat_intents_status_check
        CHECK (status IN ('pending', 'recorded', 'handled', 'failed'))
        """,
    """
        CREATE TABLE approval_challenges (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          approval_id uuid NOT NULL REFERENCES approvals(id) ON DELETE CASCADE,
          channel_message_id uuid NULL REFERENCES channel_messages(id) ON DELETE SET NULL,
          status text NOT NULL,
          challenge_prompt text NOT NULL,
          challenge_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
          resolved_at timestamptz NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT approval_challenges_status_check
            CHECK (status IN ('pending', 'approved', 'rejected', 'dismissed'))
        )
        """,
    (
        "CREATE UNIQUE INDEX approval_challenges_workspace_approval_pending_uidx "
        "ON approval_challenges (workspace_id, approval_id) "
        "WHERE status = 'pending'"
    ),
    (
        "CREATE INDEX approval_challenges_workspace_created_idx "
        "ON approval_challenges (workspace_id, created_at DESC, id DESC)"
    ),
    """
        CREATE TABLE open_loop_reviews (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
          continuity_object_id uuid NOT NULL REFERENCES continuity_objects(id) ON DELETE CASCADE,
          channel_message_id uuid NULL REFERENCES channel_messages(id) ON DELETE SET NULL,
          correction_event_id uuid NULL REFERENCES continuity_correction_events(id) ON DELETE SET NULL,
          review_action text NOT NULL,
          note text NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT open_loop_reviews_action_check
            CHECK (review_action IN ('done', 'deferred', 'still_blocked'))
        )
        """,
    (
        "CREATE INDEX open_loop_reviews_workspace_created_idx "
        "ON open_loop_reviews (workspace_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX open_loop_reviews_object_created_idx "
        "ON open_loop_reviews (continuity_object_id, created_at DESC, id DESC)"
    ),
)

_UPGRADE_GRANT_STATEMENTS = (
    "GRANT SELECT, INSERT, UPDATE, DELETE ON approval_challenges TO alicebot_app",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON open_loop_reviews TO alicebot_app",
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS open_loop_reviews_object_created_idx",
    "DROP INDEX IF EXISTS open_loop_reviews_workspace_created_idx",
    "DROP TABLE IF EXISTS open_loop_reviews",
    "DROP INDEX IF EXISTS approval_challenges_workspace_created_idx",
    "DROP INDEX IF EXISTS approval_challenges_workspace_approval_pending_uidx",
    "DROP TABLE IF EXISTS approval_challenges",
    "ALTER TABLE chat_intents DROP CONSTRAINT IF EXISTS chat_intents_status_check",
    """
        UPDATE chat_intents
        SET status = 'recorded'
        WHERE status IN ('handled', 'failed')
        """,
    """
        ALTER TABLE chat_intents
        ADD CONSTRAINT chat_intents_status_check
        CHECK (status IN ('pending', 'recorded'))
        """,
    "ALTER TABLE chat_intents DROP CONSTRAINT IF EXISTS chat_intents_intent_kind_check",
    """
        DELETE FROM chat_intents
        WHERE intent_kind <> 'inbound_message'
        """,
    """
        ALTER TABLE chat_intents
        ADD CONSTRAINT chat_intents_intent_kind_check
        CHECK (intent_kind IN ('inbound_message'))
        """,
    """
        ALTER TABLE chat_intents
        DROP COLUMN IF EXISTS handled_at,
        DROP COLUMN IF EXISTS result_payload,
        DROP COLUMN IF EXISTS intent_payload
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)
    _execute_statements(_UPGRADE_GRANT_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
