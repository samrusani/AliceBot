"""Teach the append-only triggers a narrowly-scoped true-redaction mode.

Alice's ``forget`` is a soft delete: content survives in ``memories``
(status ``archived``), in ``memory_revisions`` (``text_before`` /
``text_after`` / value payloads), and in ``event_log`` payloads. Both
``memory_revisions`` and ``event_log`` are append-only, enforced by
trigger functions that unconditionally reject UPDATE and DELETE.

True redaction must expunge CONTENT while preserving the audit SKELETON:
ids, timestamps, event types, revision types, and actor columns remain,
so the trail still proves something existed and was redacted, without
retaining what it said.

Mechanism
---------
Append-only stays the DEFAULT posture: the replaced trigger functions
still raise for every DELETE and for every ordinary UPDATE. Redaction is
an explicit privileged mode: an UPDATE passes only when

1. the session flag ``app.redaction_in_progress`` is ``'on'``
   (``current_setting('app.redaction_in_progress', true)``; the store
   sets it via ``set_config`` immediately around the redaction statement
   and resets it even on error paths -- a rolled-back transaction
   discards the flag with it), AND
2. every immutable skeleton column is unchanged
   (``OLD.x IS NOT DISTINCT FROM NEW.x``), AND
3. the content columns hold nothing but the literal redaction marker
   (or, for JSON payload columns, the ``{"redacted": true}`` shape).

This keeps casual and buggy writers locked out -- without the session
flag nothing changes versus the strict triggers -- while giving the
store's ``redact_memory_revisions`` / ``redact_memory_events`` methods a
narrow, auditable path to destroy content in place.

``REDACTION_MARKER = '[REDACTED]'`` is the canonical marker constant.
The store modules (``alicebot_api.vnext_store`` and
``alicebot_api.sqlite_store``) carry the same constant; the house test
asserts they stay in lockstep.

The upgrade also grants UPDATE and adds FOR UPDATE row-level-security
policies on ``event_log`` and ``memory_revisions`` (both previously only
allowed SELECT/INSERT), scoped to ``app.current_user_id()`` so a user
can only ever redact their own rows. The downgrade restores the strict
trigger functions and removes the grants/policies.
"""

from __future__ import annotations

from alembic import op


revision = "20260706_0079"
down_revision = "20260705_0078"
branch_labels = None
depends_on = None

# Canonical redaction marker. Keep in lockstep with
# alicebot_api.vnext_store.REDACTION_MARKER (sqlite_store re-exports it).
REDACTION_MARKER = "[REDACTED]"

_UPGRADE_STATEMENTS: tuple[str, ...] = (
    # event_log: skeleton = id, user_id, event_type, actor columns,
    # target columns, occurred_at, trace/run references. Content =
    # payload_json (must become the {"redacted": true, ...} shape with no
    # extra keys) and integrity_hash (derived from the payload content,
    # so it must be cleared -- keeping it would allow confirming guesses
    # of the redacted payload).
    f"""
        CREATE OR REPLACE FUNCTION app.reject_event_log_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          -- Append-only is the default posture; redaction is an explicit
          -- privileged mode gated on a session flag plus proof that only
          -- content columns changed, and changed to the marker shape.
          IF TG_OP = 'UPDATE'
             AND current_setting('app.redaction_in_progress', true) = 'on'
             AND OLD.id IS NOT DISTINCT FROM NEW.id
             AND OLD.user_id IS NOT DISTINCT FROM NEW.user_id
             AND OLD.event_type IS NOT DISTINCT FROM NEW.event_type
             AND OLD.actor_type IS NOT DISTINCT FROM NEW.actor_type
             AND OLD.actor_id IS NOT DISTINCT FROM NEW.actor_id
             AND OLD.target_type IS NOT DISTINCT FROM NEW.target_type
             AND OLD.target_id IS NOT DISTINCT FROM NEW.target_id
             AND OLD.occurred_at IS NOT DISTINCT FROM NEW.occurred_at
             AND OLD.trace_id IS NOT DISTINCT FROM NEW.trace_id
             AND OLD.run_id IS NOT DISTINCT FROM NEW.run_id
             AND NEW.integrity_hash IS NULL
             AND NEW.payload_json @> '{{"redacted": true}}'::jsonb
             AND NEW.payload_json - 'redacted' - 'memory_id' - 'event_type'
                 = '{{}}'::jsonb
          THEN
            RETURN NEW;
          END IF;
          RAISE EXCEPTION 'event_log is append-only';
        END;
        $$;
        """,
    # memory_revisions: skeleton = id, user_id, memory_id, sequence_no,
    # action, memory_key, source_event_ids (event-id references),
    # revision_number, revision_type, actor columns, created_at.
    # Content = text_before/text_after/reason (reasons can carry content,
    # so they are redacted too) and the previous_value/new_value/
    # candidate/metadata_json JSON payloads. NULL content stays NULL so
    # the created-vs-edited shape of the trail survives.
    f"""
        CREATE OR REPLACE FUNCTION app.reject_memory_revision_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          -- Append-only is the default posture; redaction is an explicit
          -- privileged mode gated on a session flag plus proof that only
          -- content columns changed, and changed to the marker shape.
          IF TG_OP = 'UPDATE'
             AND current_setting('app.redaction_in_progress', true) = 'on'
             AND OLD.id IS NOT DISTINCT FROM NEW.id
             AND OLD.user_id IS NOT DISTINCT FROM NEW.user_id
             AND OLD.memory_id IS NOT DISTINCT FROM NEW.memory_id
             AND OLD.sequence_no IS NOT DISTINCT FROM NEW.sequence_no
             AND OLD.action IS NOT DISTINCT FROM NEW.action
             AND OLD.memory_key IS NOT DISTINCT FROM NEW.memory_key
             AND OLD.source_event_ids IS NOT DISTINCT FROM NEW.source_event_ids
             AND OLD.revision_number IS NOT DISTINCT FROM NEW.revision_number
             AND OLD.revision_type IS NOT DISTINCT FROM NEW.revision_type
             AND OLD.actor_type IS NOT DISTINCT FROM NEW.actor_type
             AND OLD.actor_id IS NOT DISTINCT FROM NEW.actor_id
             AND OLD.created_at IS NOT DISTINCT FROM NEW.created_at
             AND NEW.text_after = '{REDACTION_MARKER}'
             AND (NEW.text_before IS NULL
                  OR NEW.text_before = '{REDACTION_MARKER}')
             AND (NEW.reason IS NULL OR NEW.reason = '{REDACTION_MARKER}')
             AND (NEW.previous_value IS NULL
                  OR NEW.previous_value = '{{"redacted": true}}'::jsonb)
             AND (NEW.new_value IS NULL
                  OR NEW.new_value = '{{"redacted": true}}'::jsonb)
             AND NEW.candidate = '{{"redacted": true}}'::jsonb
             AND NEW.metadata_json = '{{"redacted": true}}'::jsonb
          THEN
            RETURN NEW;
          END IF;
          RAISE EXCEPTION 'memory revisions are append-only';
        END;
        $$;
        """,
    # Both tables previously only granted SELECT, INSERT; redaction needs
    # UPDATE. The BEFORE UPDATE triggers above still reject everything
    # that is not marker-shaped redaction under the session flag.
    "GRANT UPDATE ON event_log TO alicebot_app",
    "GRANT UPDATE ON memory_revisions TO alicebot_app",
    # RLS: users can only redact their own rows.
    """
        CREATE POLICY event_log_redact_own ON event_log
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """,
    """
        CREATE POLICY memory_revisions_redact_own ON memory_revisions
          FOR UPDATE
          USING (user_id = app.current_user_id())
          WITH CHECK (user_id = app.current_user_id());
        """,
)

# Downgrade restores the strict, unconditional append-only functions
# exactly as migrations 20260510_0067 (event_log) and 20260311_0004
# (memory_revisions) defined them, and removes the UPDATE grant/policies.
_DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP POLICY IF EXISTS memory_revisions_redact_own ON memory_revisions",
    "DROP POLICY IF EXISTS event_log_redact_own ON event_log",
    "REVOKE UPDATE ON memory_revisions FROM alicebot_app",
    "REVOKE UPDATE ON event_log FROM alicebot_app",
    """
        CREATE OR REPLACE FUNCTION app.reject_event_log_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'event_log is append-only';
        END;
        $$;
        """,
    """
        CREATE OR REPLACE FUNCTION app.reject_memory_revision_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          RAISE EXCEPTION 'memory revisions are append-only';
        END;
        $$;
        """,
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
