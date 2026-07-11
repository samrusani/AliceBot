"""Enforce unique memory retry and confirmation identifiers.

The original semantic-retrieval migration added partial lookup indexes for
``commit_digest`` and ``confirmation_id`` but did not make them unique. Two
concurrent retries could therefore create more than one replay target, and a
reused idempotency key with different content could silently return the first
row.

This revision also closes the last legacy project-scope compatibility gap.
Early agentic commits stored scope only at
``metadata_json.agentic_memory.project_scope``.  The upgrade normalizes that
array into the canonical top-level ``metadata_json.project_scope`` without
overwriting an existing non-empty canonical array, and fills ``project_id``
only for an unambiguous singleton scope.  Multi-project rows remain metadata
scoped and keep ``project_id`` NULL.  Downgrade deliberately retains these
canonical metadata copies because it cannot distinguish them from top-level
scope that predated this revision without risking data loss.

Upgrade posture for pre-existing duplicates is lossless for memory content:
the earliest row remains the canonical lookup target, later rows retain their
content/history but relinquish the ambiguous identifier, and their metadata
records the canonical row id. New partial UNIQUE indexes make the invariant
atomic for future writes. Downgrade restores non-unique indexes; it does not
re-introduce identifiers removed from ambiguous duplicate rows.

Revision ID: 20260711_0083
Revises: 20260707_0082
"""

from __future__ import annotations

from alembic import op


revision = "20260711_0083"
down_revision = "20260707_0082"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    WITH legacy_scopes AS (
      SELECT
        memory.id,
        to_jsonb(array_agg(scope.normalized ORDER BY scope.first_ordinal))
          AS normalized_scope
      FROM memories AS memory
      CROSS JOIN LATERAL (
        SELECT
          normalized_element.normalized,
          MIN(normalized_element.ordinality) AS first_ordinal
        FROM (
          SELECT
            regexp_replace(
              btrim(element.value #>> '{}'),
              '[[:space:]]+',
              ' ',
              'g'
            ) AS normalized,
            element.ordinality
          FROM jsonb_array_elements(
            CASE
              WHEN jsonb_typeof(
                memory.metadata_json #> '{agentic_memory,project_scope}'
              ) = 'array'
                THEN memory.metadata_json #> '{agentic_memory,project_scope}'
              ELSE '[]'::jsonb
            END
          ) WITH ORDINALITY AS element(value, ordinality)
          WHERE jsonb_typeof(element.value) = 'string'
        ) AS normalized_element
        WHERE normalized_element.normalized <> ''
        GROUP BY normalized_element.normalized
      ) AS scope
      WHERE jsonb_typeof(
              memory.metadata_json #> '{agentic_memory,project_scope}'
            ) = 'array'
        AND (
          jsonb_typeof(memory.metadata_json -> 'project_scope')
            IS DISTINCT FROM 'array'
          OR jsonb_array_length(memory.metadata_json -> 'project_scope') = 0
        )
      GROUP BY memory.id
    )
    UPDATE memories AS memory
    SET
      metadata_json = jsonb_set(
        memory.metadata_json,
        '{project_scope}',
        legacy_scopes.normalized_scope,
        true
      ),
      project_id = CASE
        WHEN memory.project_id IS NULL
             AND jsonb_array_length(legacy_scopes.normalized_scope) = 1
          THEN legacy_scopes.normalized_scope #>> '{0}'
        ELSE memory.project_id
      END
    FROM legacy_scopes
    WHERE memory.id = legacy_scopes.id
      AND jsonb_array_length(legacy_scopes.normalized_scope) > 0
    """,
    """
    WITH ranked AS (
      SELECT
        id,
        FIRST_VALUE(id) OVER (
          PARTITION BY user_id, commit_digest
          ORDER BY created_at ASC, id ASC
        ) AS canonical_id,
        ROW_NUMBER() OVER (
          PARTITION BY user_id, commit_digest
          ORDER BY created_at ASC, id ASC
        ) AS duplicate_rank
      FROM memories
      WHERE commit_digest IS NOT NULL
    )
    UPDATE memories AS memory
    SET
      commit_digest = NULL,
      metadata_json = jsonb_set(
        memory.metadata_json #- '{agentic_memory,idempotency_key}',
        '{lifecycle_migration}',
        COALESCE(memory.metadata_json -> 'lifecycle_migration', '{}'::jsonb)
          || jsonb_build_object(
            'duplicate_commit_digest_canonical_memory_id', ranked.canonical_id::text
          ),
        true
      )
    FROM ranked
    WHERE memory.id = ranked.id
      AND ranked.duplicate_rank > 1
    """,
    """
    WITH ranked AS (
      SELECT
        id,
        FIRST_VALUE(id) OVER (
          PARTITION BY user_id, confirmation_id
          ORDER BY created_at ASC, id ASC
        ) AS canonical_id,
        ROW_NUMBER() OVER (
          PARTITION BY user_id, confirmation_id
          ORDER BY created_at ASC, id ASC
        ) AS duplicate_rank
      FROM memories
      WHERE confirmation_id IS NOT NULL
    )
    UPDATE memories AS memory
    SET
      confirmation_id = NULL,
      metadata_json = jsonb_set(
        memory.metadata_json #- '{agentic_memory,confirmation,confirmation_id}',
        '{lifecycle_migration}',
        COALESCE(memory.metadata_json -> 'lifecycle_migration', '{}'::jsonb)
          || jsonb_build_object(
            'duplicate_confirmation_id_canonical_memory_id', ranked.canonical_id::text
          ),
        true
      )
    FROM ranked
    WHERE memory.id = ranked.id
      AND ranked.duplicate_rank > 1
    """,
    "DROP INDEX IF EXISTS memories_commit_digest_idx",
    "DROP INDEX IF EXISTS memories_confirmation_id_idx",
    """
    CREATE UNIQUE INDEX memories_commit_digest_idx
      ON memories (user_id, commit_digest)
      WHERE commit_digest IS NOT NULL
    """,
    """
    CREATE UNIQUE INDEX memories_confirmation_id_idx
      ON memories (user_id, confirmation_id)
      WHERE confirmation_id IS NOT NULL
    """,
    """
    CREATE OR REPLACE FUNCTION app.expire_memory_derived_entity_edges()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      IF ROW(NEW.title, NEW.canonical_text, NEW.summary, NEW.value)
         IS DISTINCT FROM
         ROW(OLD.title, OLD.canonical_text, OLD.summary, OLD.value) THEN
        UPDATE graph_edges
        SET valid_to = GREATEST(clock_timestamp(), valid_from)
        WHERE user_id = OLD.user_id
          AND from_type = 'memory'
          AND from_id = OLD.id::text
          AND edge_type IN ('mentions', 'related_to_person')
          AND valid_to IS NULL;
      END IF;
      RETURN NEW;
    END;
    $$
    """,
    """
    CREATE TRIGGER memories_expire_derived_entity_edges
    BEFORE UPDATE OF title, canonical_text, summary, value ON memories
    FOR EACH ROW
    EXECUTE FUNCTION app.expire_memory_derived_entity_edges()
    """,
)

_DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TRIGGER IF EXISTS memories_expire_derived_entity_edges ON memories",
    "DROP FUNCTION IF EXISTS app.expire_memory_derived_entity_edges()",
    "DROP INDEX IF EXISTS memories_confirmation_id_idx",
    "DROP INDEX IF EXISTS memories_commit_digest_idx",
    """
    CREATE INDEX memories_commit_digest_idx
      ON memories (user_id, commit_digest)
      WHERE commit_digest IS NOT NULL
    """,
    """
    CREATE INDEX memories_confirmation_id_idx
      ON memories (user_id, confirmation_id)
      WHERE confirmation_id IS NOT NULL
    """,
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
