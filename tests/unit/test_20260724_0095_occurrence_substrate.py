from __future__ import annotations

import importlib
import re

from alicebot_api import sqlite_schema


MODULE_NAME = "apps.api.alembic.versions.20260724_0095_occurrence_substrate"


def load_migration_module():
    return importlib.import_module(MODULE_NAME)


def test_revision_chain_extends_browser_clip_capabilities() -> None:
    module = load_migration_module()

    assert module.revision == "20260724_0095"
    assert module.down_revision == "20260721_0094"


def test_upgrade_is_empty_review_gated_occurrence_schema_with_rls(
    monkeypatch,
) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.upgrade()

    schema = executed[0]
    for table in (
        "occurrence_coverage",
        "occurrence_claims",
        "occurrence_units",
        "occurrence_evidence",
        "occurrence_extraction_dispositions",
    ):
        assert f"CREATE TABLE {table}" in schema
        assert (f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY") in executed
        assert (f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY") in executed
        assert f"CREATE POLICY {table}_is_owner" in executed[-1]
        assert (f"GRANT SELECT, INSERT, UPDATE ON {table} TO alicebot_app") in executed

    assert "unit_value smallint NOT NULL DEFAULT 1" in schema
    assert "CHECK (unit_value = 1)" in schema
    assert "review_receipt_digest ~ '^[0-9a-f]{64}$'" in schema
    assert "review_receipt_action" in schema
    assert "'accepted', 'refresh_evidence'" in schema
    assert "'reestablished'" in schema
    assert ("complete_through IS NULL\n              OR complete_through >= coverage_started_at") in schema
    assert "OR coverage_mode <> 'forward_only'" not in schema
    assert "resolution_decision = 'new'" in schema
    assert "resolved_occurrence_id IS NULL" in schema
    assert "resolution_decision = 'link_existing'" in schema
    assert "resolved_occurrence_id IS NOT NULL" in schema
    assert "UNIQUE (id, user_id, count_key)" in schema
    assert (
        "FOREIGN KEY (claim_id, user_id, count_key)\n            REFERENCES occurrence_claims(id, user_id, count_key)"
    ) in schema
    assert (
        "FOREIGN KEY (resolved_occurrence_id, user_id, count_key)\n"
        "          REFERENCES occurrence_units(id, user_id, count_key)"
    ) in schema
    assert (
        "FOREIGN KEY (superseded_by, user_id, count_key)\n"
        "            REFERENCES occurrence_units(id, user_id, count_key)"
    ) in schema

    ambiguous_check = schema.split(
        "CONSTRAINT occurrence_claims_ambiguous_state_check",
        1,
    )[1].split("CREATE TABLE occurrence_units", 1)[0]
    assert "identity_basis = 'ambiguous'" not in ambiguous_check
    assert "resolution_status = 'pending'" in ambiguous_check
    assert "review_status = 'candidate'" in ambiguous_check
    assert "resolution_status = 'rejected'" in ambiguous_check
    assert "review_status = 'rejected'" in ambiguous_check

    assert "INSERT INTO" not in schema
    assert re.search(r"\bUPDATE\s+(memories|sources|event_log)\b", schema) is None
    assert re.search(r"\bOR\s*\(\s*OR\b", schema) is None


def test_evidence_carriers_are_annotations_not_destructive_foreign_keys() -> None:
    module = load_migration_module()
    schema = module._UPGRADE_SCHEMA
    evidence = schema.split("CREATE TABLE occurrence_evidence", 1)[1].split(
        "CREATE TABLE occurrence_extraction_dispositions",
        1,
    )[0]

    assert "occurrence_evidence_claim_fkey" in evidence
    assert "occurrence_evidence_unit_fkey" in evidence
    assert "FOREIGN KEY (source_id" not in evidence
    assert "FOREIGN KEY (source_chunk_id" not in evidence
    assert "FOREIGN KEY (memory_id" not in evidence
    assert "CONSTRAINT occurrence_evidence_authorization_carrier_check" in evidence
    assert "CHECK (memory_id IS NOT NULL OR source_id IS NOT NULL)" in evidence
    assert "CONSTRAINT occurrence_evidence_source_chunk_parent_check" in evidence
    assert "CHECK (source_chunk_id IS NULL OR source_id IS NOT NULL)" in evidence
    assert "CONSTRAINT occurrence_evidence_quote_check" in evidence
    assert "btrim(quote, chr(9) || chr(10)" in evidence
    assert "chr(28)" in evidence
    assert "chr(160)" in evidence
    assert "char_length(btrim(quote))" not in evidence
    assert "OR (quote IS NOT NULL" not in evidence

    sqlite_evidence = next(
        statement
        for statement in sqlite_schema._TABLE_STATEMENTS
        if "CREATE TABLE IF NOT EXISTS occurrence_evidence" in statement
    )
    assert "CONSTRAINT occurrence_evidence_authorization_carrier_check" in sqlite_evidence
    assert "(memory_id IS NOT NULL AND length(trim(memory_id)) > 0)" in sqlite_evidence
    assert "(source_id IS NOT NULL AND length(trim(source_id)) > 0)" in sqlite_evidence
    assert "CONSTRAINT occurrence_evidence_source_chunk_parent_check" in sqlite_evidence
    assert "CONSTRAINT occurrence_evidence_quote_check" in sqlite_evidence
    assert "trim(quote, char(9, 10" in sqlite_evidence
    assert "28" in sqlite_schema._PYTHON_312_STRIP_CHARS_SQL
    assert "160" in sqlite_schema._PYTHON_312_STRIP_CHARS_SQL
    assert "length(trim(quote))" not in sqlite_evidence
    assert "OR (quote IS NOT NULL" not in sqlite_evidence
    assert module._PYTHON_312_STRIP_CODEPOINTS == sqlite_schema._PYTHON_312_STRIP_CODEPOINTS

    sqlite_schema_sql = "\n".join(sqlite_schema._TABLE_STATEMENTS)
    assert "UNIQUE (id, user_id, count_key)" in sqlite_schema_sql
    assert (
        "FOREIGN KEY (claim_id, user_id, count_key)\n        REFERENCES occurrence_claims(id, user_id, count_key)"
    ) in sqlite_schema_sql
    assert (
        "FOREIGN KEY (resolved_occurrence_id, user_id, count_key)\n"
        "        REFERENCES occurrence_units(id, user_id, count_key)"
    ) in sqlite_schema_sql
    assert (
        "FOREIGN KEY (superseded_by, user_id, count_key)\n        REFERENCES occurrence_units(id, user_id, count_key)"
    ) in sqlite_schema_sql


def test_reconciliation_lookup_indexes_match_postgres_and_sqlite_predicates() -> None:
    postgres_schema = load_migration_module()._UPGRADE_SCHEMA
    sqlite_indexes = "\n".join(sqlite_schema._INDEX_AND_TRIGGER_STATEMENTS)

    assert (
        """
        CREATE INDEX memories_occurrence_source_chunk_idx
          ON memories (
            user_id,
            (metadata_json ->> 'source_chunk_id'),
            (metadata_json #>> '{occurrence_proposal,source_chunk_id}'),
            id
          )
          WHERE deleted_at IS NULL
            AND metadata_json ->> 'source_chunk_id' IS NOT NULL
            AND metadata_json #>> '{occurrence_proposal,source_chunk_id}' IS NOT NULL;
        """.strip()
        in postgres_schema
    )
    assert (
        """
    CREATE INDEX IF NOT EXISTS memories_occurrence_source_chunk_idx
      ON memories (
        user_id,
        json_extract(metadata_json, '$.source_chunk_id'),
        json_extract(
          metadata_json,
          '$.occurrence_proposal.source_chunk_id'
        ),
        id
      )
      WHERE deleted_at IS NULL
        AND json_extract(metadata_json, '$.source_chunk_id') IS NOT NULL
        AND json_extract(
          metadata_json,
          '$.occurrence_proposal.source_chunk_id'
        ) IS NOT NULL
    """.strip()
        in sqlite_indexes
    )
    for schema in (postgres_schema, sqlite_indexes):
        assert "occurrence_evidence_memory_idx" in schema
        assert "ON occurrence_evidence (user_id, memory_id)" in schema
        assert "WHERE memory_id IS NOT NULL" in schema


def test_downgrade_drops_only_occurrence_tables_in_dependency_order(
    monkeypatch,
) -> None:
    module = load_migration_module()
    executed: list[str] = []
    monkeypatch.setattr(module.op, "execute", executed.append)

    module.downgrade()

    assert executed == [
        "DROP INDEX IF EXISTS memories_occurrence_source_chunk_idx",
        "DROP TABLE IF EXISTS occurrence_extraction_dispositions",
        "DROP TABLE IF EXISTS occurrence_evidence",
        "ALTER TABLE occurrence_units DROP CONSTRAINT IF EXISTS occurrence_units_claim_fkey",
        "DROP TABLE IF EXISTS occurrence_claims",
        "DROP TABLE IF EXISTS occurrence_units",
        "DROP TABLE IF EXISTS occurrence_coverage",
    ]
    assert all("CASCADE" not in statement for statement in executed)
