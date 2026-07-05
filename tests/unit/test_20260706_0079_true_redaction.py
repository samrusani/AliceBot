from __future__ import annotations

import importlib

from alicebot_api import sqlite_schema, sqlite_store, vnext_store


MODULE_NAME = "apps.api.alembic.versions.20260706_0079_true_redaction_triggers"

_EVENT_LOG_IMMUTABLE_COLUMNS = (
    "id",
    "user_id",
    "event_type",
    "actor_type",
    "actor_id",
    "target_type",
    "target_id",
    "occurred_at",
    "trace_id",
    "run_id",
)

_REVISION_IMMUTABLE_COLUMNS = (
    "id",
    "user_id",
    "memory_id",
    "sequence_no",
    "action",
    "memory_key",
    "source_event_ids",
    "revision_number",
    "revision_type",
    "actor_type",
    "actor_id",
    "created_at",
)


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def _recorded_upgrade(monkeypatch) -> list[str]:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    module.upgrade()
    return executed


def _recorded_downgrade(monkeypatch) -> list[str]:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)
    module.downgrade()
    return executed


def test_revision_chain_extends_entity_substrate() -> None:
    module = load_migration_module()

    assert module.revision == "20260706_0079"
    assert module.down_revision == "20260705_0078"


def test_redaction_marker_is_canonical_across_migration_and_stores() -> None:
    module = load_migration_module()

    assert module.REDACTION_MARKER == "[REDACTED]"
    assert vnext_store.REDACTION_MARKER == module.REDACTION_MARKER
    assert sqlite_store.REDACTION_MARKER == module.REDACTION_MARKER
    assert sqlite_schema.REDACTION_MARKER == module.REDACTION_MARKER


def test_upgrade_replaces_both_append_only_trigger_functions(monkeypatch) -> None:
    joined = "\n".join(_recorded_upgrade(monkeypatch))

    assert "CREATE OR REPLACE FUNCTION app.reject_event_log_mutation()" in joined
    assert "CREATE OR REPLACE FUNCTION app.reject_memory_revision_mutation()" in joined
    # Redaction is gated on the explicit session flag.
    assert joined.count("current_setting('app.redaction_in_progress', true) = 'on'") == 2
    # Only UPDATE gets the privileged path; DELETE stays rejected.
    assert joined.count("TG_OP = 'UPDATE'") == 2


def test_upgrade_keeps_append_only_as_the_default_posture(monkeypatch) -> None:
    joined = "\n".join(_recorded_upgrade(monkeypatch))

    assert "RAISE EXCEPTION 'event_log is append-only'" in joined
    assert "RAISE EXCEPTION 'memory revisions are append-only'" in joined


def test_upgrade_pins_every_immutable_skeleton_column(monkeypatch) -> None:
    executed = _recorded_upgrade(monkeypatch)
    event_log_fn = next(s for s in executed if "reject_event_log_mutation" in s)
    revision_fn = next(s for s in executed if "reject_memory_revision_mutation" in s)

    for column in _EVENT_LOG_IMMUTABLE_COLUMNS:
        assert f"OLD.{column} IS NOT DISTINCT FROM NEW.{column}" in event_log_fn
    for column in _REVISION_IMMUTABLE_COLUMNS:
        assert f"OLD.{column} IS NOT DISTINCT FROM NEW.{column}" in revision_fn


def test_upgrade_only_admits_marker_shaped_content(monkeypatch) -> None:
    module = load_migration_module()
    executed = _recorded_upgrade(monkeypatch)
    event_log_fn = next(s for s in executed if "reject_event_log_mutation" in s)
    revision_fn = next(s for s in executed if "reject_memory_revision_mutation" in s)

    # event_log: payload must be the redaction shape with no extra keys,
    # and the content-derived integrity hash must be cleared.
    assert "NEW.integrity_hash IS NULL" in event_log_fn
    assert """NEW.payload_json @> '{"redacted": true}'::jsonb""" in event_log_fn
    assert "NEW.payload_json - 'redacted' - 'memory_id' - 'event_type'" in event_log_fn

    # memory_revisions: text columns must hold the literal marker (or stay
    # NULL) and JSON payloads must be exactly the redacted shape. Reasons
    # can carry content, so reason is redacted too.
    marker = module.REDACTION_MARKER
    assert f"NEW.text_after = '{marker}'" in revision_fn
    assert f"NEW.text_before = '{marker}'" in revision_fn
    assert f"NEW.reason = '{marker}'" in revision_fn
    for column in ("previous_value", "new_value", "candidate", "metadata_json"):
        assert f"""NEW.{column} = '{{"redacted": true}}'::jsonb""" in revision_fn


def test_upgrade_grants_update_with_owner_scoped_policies(monkeypatch) -> None:
    executed = _recorded_upgrade(monkeypatch)
    joined = "\n".join(executed)

    assert "GRANT UPDATE ON event_log TO alicebot_app" in executed
    assert "GRANT UPDATE ON memory_revisions TO alicebot_app" in executed
    assert "CREATE POLICY event_log_redact_own ON event_log" in joined
    assert "CREATE POLICY memory_revisions_redact_own ON memory_revisions" in joined
    # Every policy is scoped to the owner: one USING + one WITH CHECK each.
    assert joined.count("USING (user_id = app.current_user_id())") == 2
    assert joined.count("WITH CHECK (user_id = app.current_user_id())") == 2


def test_downgrade_restores_strict_functions_and_removes_grants(monkeypatch) -> None:
    module = load_migration_module()
    executed = _recorded_downgrade(monkeypatch)
    joined = "\n".join(executed)

    assert executed == list(module._DOWNGRADE_STATEMENTS)
    assert "DROP POLICY IF EXISTS event_log_redact_own ON event_log" in executed
    assert "DROP POLICY IF EXISTS memory_revisions_redact_own ON memory_revisions" in executed
    assert "REVOKE UPDATE ON event_log FROM alicebot_app" in executed
    assert "REVOKE UPDATE ON memory_revisions FROM alicebot_app" in executed
    # The restored functions are the strict originals: unconditional
    # rejection, no redaction escape hatch left behind.
    assert "CREATE OR REPLACE FUNCTION app.reject_event_log_mutation()" in joined
    assert "CREATE OR REPLACE FUNCTION app.reject_memory_revision_mutation()" in joined
    assert "redaction_in_progress" not in joined
    assert "RAISE EXCEPTION 'event_log is append-only'" in joined
    assert "RAISE EXCEPTION 'memory revisions are append-only'" in joined
