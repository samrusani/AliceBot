from __future__ import annotations

import importlib


MODULE_NAME = "apps.api.alembic.versions.20260716_0092_project_update_artifact_redaction"


def test_upgrade_installs_exact_guarded_redaction_and_bounded_backfill(monkeypatch) -> None:
    module = importlib.import_module(MODULE_NAME)
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    assert module.revision == "20260716_0092"
    assert module.down_revision == "20260715_0091"
    sql = "\n".join(executed)
    assert "GRANT UPDATE ON provenance_links TO alicebot_app" in sql
    assert "GRANT UPDATE ON artifact_quality_ratings TO alicebot_app" in sql
    assert "current_setting('app.redaction_in_progress', true) = 'on'" in sql
    assert "invalid project-update artifact redaction shape" in sql
    assert "redacted artifacts are immutable" in sql
    assert "FOR SHARE" in sql
    assert "FOR KEY SHARE" not in sql
    assert "NEW.target_type = 'memory'" in sql
    assert "memory.memory_key = 'redacted.' || memory.id::text" in sql
    assert "quoted provenance cannot be added to a redacted target" in sql
    assert "NEW.memory_key = 'redacted.' || NEW.memory_id::text" in sql
    assert "NEW.source_event_ids = '[]'::jsonb" in sql
    assert "OLD.text_before IS NULL AND NEW.text_before IS NULL" in sql
    assert "OLD.text_before IS NOT NULL AND NEW.text_before = '[REDACTED]'" in sql
    assert "OLD.previous_value IS NULL AND NEW.previous_value IS NULL" in sql
    assert "OLD.previous_value IS NOT NULL" in sql
    assert "NEW.payload_json = jsonb_build_object" in sql
    assert "NEW.integrity_hash IS NULL" in sql
    assert "OLD.target_id = NEW.payload_json ->> 'memory_id'" in sql
    assert "OLD.payload_memory_id = NEW.payload_json ->> 'memory_id'" in sql
    assert "OLD.payload_candidate_memory_id = NEW.payload_json ->> 'memory_id'" in sql
    assert "artifact.id::text = OLD.payload_artifact_id" in sql
    assert "artifact.user_id = OLD.user_id" in sql
    assert "OLD.metadata_json ->> 'workflow' = 'project_auto_update'" in sql
    assert "OLD.metadata_json -> 'project_scope'" in sql
    artifact_guard_sql = next(
        statement
        for statement in executed
        if "CREATE OR REPLACE FUNCTION app.guard_generated_artifact_redaction()" in statement
    )
    canonical_predicate_sql = next(
        statement
        for statement in executed
        if "CREATE OR REPLACE FUNCTION app.is_redacted_project_update_artifact(" in statement
    )
    assert "artifact_type_value = 'project_update'" in canonical_predicate_sql
    assert "status_value IN ('accepted', 'rejected')" in canonical_predicate_sql
    assert "prompt_hash_value IS NULL" in canonical_predicate_sql
    assert "metadata_json_value = jsonb_build_object" in canonical_predicate_sql
    assert "new_is_redacted boolean" in artifact_guard_sql
    assert artifact_guard_sql.count("app.is_redacted_project_update_artifact(") == 2
    assert "IF TG_OP = 'INSERT'" in artifact_guard_sql
    assert "redacted project-update artifacts cannot be inserted" in artifact_guard_sql
    assert artifact_guard_sql.index("IF TG_OP = 'INSERT'") < artifact_guard_sql.index(
        "OLD.artifact_type"
    )
    assert "IF new_is_redacted" in artifact_guard_sql
    assert "IS DISTINCT FROM 'on'" in artifact_guard_sql
    assert "project-update artifact redaction requires authorized redaction mode" in artifact_guard_sql
    assert artifact_guard_sql.index("IF new_is_redacted") < artifact_guard_sql.index(
        "IF current_setting('app.redaction_in_progress', true) = 'on'"
    )
    trigger_sql = next(
        statement
        for statement in executed
        if "CREATE TRIGGER generated_artifacts_redaction_guard" in statement
    )
    assert "BEFORE INSERT OR UPDATE ON generated_artifacts" in trigger_sql
    provenance_guard_sql = next(
        statement
        for statement in executed
        if "CREATE OR REPLACE FUNCTION app.guard_provenance_link_redaction()" in statement
    )
    rating_guard_sql = next(
        statement
        for statement in executed
        if "CREATE OR REPLACE FUNCTION app.guard_artifact_quality_rating_redaction()" in statement
    )
    assert "app.is_redacted_project_update_artifact(" in provenance_guard_sql
    assert "app.is_redacted_project_update_artifact(" in rating_guard_sql
    assert "artifact.metadata_json -> 'redacted' = 'true'::jsonb" not in rating_guard_sql

    backfill = "\n".join(module._BACKFILL_STATEMENTS)
    assert "alice_0092_redacted_memories" in backfill
    assert "canonical_text = '[REDACTED]'" in backfill
    assert "value = '{\"redacted\": true}'::jsonb" in backfill
    assert "metadata_json -> 'redacted' = 'true'::jsonb" in backfill
    assert "metadata_json ->> 'redacted_at'" in backfill
    assert "payload_artifact_id" in backfill
    assert "payload_candidate_memory_id" in backfill
    assert "payload_memory_id" in backfill
    assert "payload_json::text" not in backfill
    assert "artifact.metadata_json ->> 'workflow' = 'project_auto_update'" in backfill
    assert "artifact.metadata_json -> 'project_scope'" in backfill
    assert "commit_digest = NULL" in backfill
    assert "confirmation_id = NULL" in backfill
    assert "source_event_ids = '[]'::jsonb" in backfill
    # Executable-shape guard: the original draft accidentally emitted the
    # rating UPDATE keyword twice before SET, which makes the migration fail
    # before any carrier can boot.  Keep exactly one bounded rating repair.
    rating_repairs = [
        statement
        for statement in module._BACKFILL_STATEMENTS
        if "UPDATE artifact_quality_ratings AS rating" in statement
    ]
    assert len(rating_repairs) == 1
    assert rating_repairs[0].lstrip().startswith("UPDATE artifact_quality_ratings AS rating\n    SET ")
    assert "UPDATE artifact_quality_ratings AS rating\n    UPDATE" not in rating_repairs[0]
    memory_repair = module._BACKFILL_STATEMENTS[-2]
    assert "jsonb_build_object('source_refs'" not in memory_repair
    assert "jsonb_build_object('consolidation_digest'" not in memory_repair


def test_downgrade_revokes_only_new_grants_and_restores_0079_redaction(monkeypatch) -> None:
    module = importlib.import_module(MODULE_NAME)
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    sql = "\n".join(executed)
    assert "REVOKE UPDATE ON artifact_quality_ratings FROM alicebot_app" in sql
    assert "REVOKE UPDATE ON provenance_links FROM alicebot_app" in sql
    assert "REVOKE UPDATE ON event_log" not in sql
    assert "REVOKE UPDATE ON memory_revisions" not in sql
    assert "DROP POLICY" not in sql
    assert "NEW.payload_json @> '{\"redacted\": true}'::jsonb" in sql
    assert "OLD.memory_key IS NOT DISTINCT FROM NEW.memory_key" in sql
    assert "OLD.source_event_ids IS NOT DISTINCT FROM NEW.source_event_ids" in sql
    assert sql.count("DROP TRIGGER IF EXISTS artifact_quality_ratings_redaction_guard") == 1
    assert "DROP FUNCTION IF EXISTS app.is_redacted_project_update_artifact(" in sql
