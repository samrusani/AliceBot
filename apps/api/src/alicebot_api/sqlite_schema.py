"""SQLite DDL bootstrap for the zero-infrastructure vNext on-ramp.

Mirrors the Postgres vNext memory-kernel schema for exactly the store
surface the nine core MCP tools use. Allowed enum values mirror
``apps/api/alembic/versions/20260510_0067_vnext_memory_kernel_schema.py``
(plus ``procedure`` from ``20260621_0071``) and
``alicebot_api.vnext_memory_commit``.

Conventions:
- UUIDs are stored as TEXT (``str(uuid4())``).
- Timestamps are ISO-8601 TEXT in UTC with a trailing ``Z``.
- JSON columns are TEXT holding ``json.dumps(json_safe(value))``.
- ``event_log`` (and ``memory_revisions``, mirroring Postgres) are
  append-only, enforced by triggers.
- ``memories_fts`` is an external-content FTS5 index over
  memories(title, canonical_text, summary, memory_key), kept in sync by
  AFTER INSERT/UPDATE/DELETE triggers. It uses the ``porter unicode61``
  tokenizer so inflected query terms match the way stemmed Postgres FTS
  (``websearch_to_tsquery('english', ...)``) does.
"""

from __future__ import annotations

import sqlite3

DOMAINS = (
    "professional",
    "personal",
    "family",
    "health",
    "spiritual",
    "financial",
    "legal",
    "learning",
    "relationship",
    "project",
    "agent_run",
    "system",
    "unknown",
)

SENSITIVITY_LEVELS = (
    "public",
    "internal",
    "private",
    "confidential",
    "highly_sensitive",
    "sacred",
    "regulated",
    "unknown",
)

MEMORY_TYPES = (
    "preference",
    "identity_fact",
    "relationship_fact",
    "project_fact",
    "decision",
    "commitment",
    "routine",
    "procedure",
    "constraint",
    "working_style",
    "episode",
    "semantic",
    "project_state",
    "belief",
    "thesis",
    "person",
    "relationship",
    "open_loop",
    "value",
    "pattern",
    "contradiction",
    "question",
    "answer",
    "artifact_summary",
    "agent_run",
    "system",
)

MEMORY_STATUSES = (
    "candidate",
    "active",
    "accepted",
    "rejected",
    "superseded",
    # Demoted-but-kept memories (e.g. long-unconfirmed facts). Excluded
    # from retrieval by default alongside superseded/rejected.
    "stale",
    "archived",
    "needs_review",
    "private_only",
)

MEMORY_CONFIRMATION_STATUSES = (
    "unconfirmed",
    "confirmed",
    "contested",
)

MEMORY_TRUST_CLASSES = (
    "deterministic",
    "llm_single_source",
    "llm_corroborated",
    "human_curated",
)

MEMORY_PROMOTION_ELIGIBILITIES = (
    "promotable",
    "not_promotable",
)

REVISION_TYPES = (
    "created",
    "edited",
    "corrected",
    "promoted",
    "rejected",
    "superseded",
    "merged",
    "split",
    "archived",
    "restored",
)

EVIDENCE_ROLES = (
    "supports",
    "contradicts",
    "mentions",
    "inferred_from",
    "quoted_from",
    "summarizes",
    "background",
)

OPEN_LOOP_STATUSES = (
    "open",
    "resolved",
    "dismissed",
)

OPEN_LOOP_PRIORITIES = ("low", "normal", "high", "urgent")

EDGE_TYPES = (
    "supports",
    "contradicts",
    "caused_by",
    "influenced_by",
    "similar_to",
    "supersedes",
    "depends_on",
    "mentions",
    "asks",
    "answers",
    "reframes",
    "predicts",
    "invalidates",
    "reopens",
    "same_problem",
    "same_principle",
    "cross_domain_pattern",
    "old_idea_now_relevant",
    "belief_reinforcement",
    "belief_challenge",
    "owned_by",
    "belongs_to_project",
    "related_to_person",
)

AGENT_TYPES = (
    "personal_assistant",
    "coding_agent",
    "research_agent",
    "workflow_agent",
    "unknown",
)

PERMISSION_PROFILES = (
    "read_only_agent",
    "project_scoped_agent",
    "trusted_local_agent",
    "memory_proposal_agent",
    "admin_agent",
)


def _sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


_DOMAINS_SQL = _sql_list(DOMAINS)
_SENSITIVITY_SQL = _sql_list(SENSITIVITY_LEVELS)
_MEMORY_TYPES_SQL = _sql_list(MEMORY_TYPES)
_MEMORY_STATUSES_SQL = _sql_list(MEMORY_STATUSES)
_MEMORY_CONFIRMATION_STATUSES_SQL = _sql_list(MEMORY_CONFIRMATION_STATUSES)
_MEMORY_TRUST_CLASSES_SQL = _sql_list(MEMORY_TRUST_CLASSES)
_MEMORY_PROMOTION_ELIGIBILITIES_SQL = _sql_list(MEMORY_PROMOTION_ELIGIBILITIES)
_REVISION_TYPES_SQL = _sql_list(REVISION_TYPES)
_EVIDENCE_ROLES_SQL = _sql_list(EVIDENCE_ROLES)
_OPEN_LOOP_STATUSES_SQL = _sql_list(OPEN_LOOP_STATUSES)
_OPEN_LOOP_PRIORITIES_SQL = _sql_list(OPEN_LOOP_PRIORITIES)
_EDGE_TYPES_SQL = _sql_list(EDGE_TYPES)
_AGENT_TYPES_SQL = _sql_list(AGENT_TYPES)
_PERMISSION_PROFILES_SQL = _sql_list(PERMISSION_PROFILES)

# Default matches the store's Python-generated ISO-8601 UTC "Z" convention
# closely enough for lexicographic ordering (milliseconds vs microseconds).
_NOW_UTC_ISO_SQL = "(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"

_TABLE_STATEMENTS: tuple[str, ...] = (
    f"""
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT NOT NULL UNIQUE,
      display_name TEXT NULL,
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL}
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS sources (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      source_type TEXT NOT NULL,
      title TEXT NULL,
      author TEXT NULL,
      uri TEXT NULL,
      raw_path TEXT NULL,
      content_hash TEXT NOT NULL,
      captured_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      source_created_at TEXT NULL,
      source_modified_at TEXT NULL,
      connector_name TEXT NULL,
      external_id TEXT NULL,
      domain TEXT NOT NULL DEFAULT 'unknown',
      sensitivity TEXT NOT NULL DEFAULT 'unknown',
      metadata_json TEXT NOT NULL DEFAULT '{{}}',
      deleted_at TEXT NULL,
      UNIQUE (id, user_id),
      CONSTRAINT sources_source_type_length_check
        CHECK (length(source_type) BETWEEN 1 AND 120),
      CONSTRAINT sources_content_hash_length_check
        CHECK (length(content_hash) BETWEEN 1 AND 200),
      CONSTRAINT sources_domain_check
        CHECK (domain IN ({_DOMAINS_SQL})),
      CONSTRAINT sources_sensitivity_check
        CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
      CONSTRAINT sources_metadata_json_object_check
        CHECK (json_type(metadata_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS source_chunks (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      source_id TEXT NOT NULL,
      chunk_index INTEGER NOT NULL,
      text TEXT NOT NULL,
      token_count INTEGER NULL,
      metadata_json TEXT NOT NULL DEFAULT '{{}}',
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      UNIQUE (id, user_id),
      UNIQUE (user_id, source_id, chunk_index),
      CONSTRAINT source_chunks_source_fkey
        FOREIGN KEY (source_id, user_id)
        REFERENCES sources(id, user_id)
        ON DELETE CASCADE,
      CONSTRAINT source_chunks_chunk_index_check
        CHECK (chunk_index >= 0),
      CONSTRAINT source_chunks_token_count_check
        CHECK (token_count IS NULL OR token_count >= 0),
      CONSTRAINT source_chunks_metadata_json_object_check
        CHECK (json_type(metadata_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS memories (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      agent_profile_id TEXT NOT NULL DEFAULT 'assistant_default',
      memory_key TEXT NOT NULL,
      value TEXT NOT NULL,
      status TEXT NOT NULL,
      source_event_ids TEXT NOT NULL,
      memory_type TEXT NOT NULL DEFAULT 'preference',
      confidence REAL NULL,
      salience REAL NULL,
      confirmation_status TEXT NOT NULL DEFAULT 'unconfirmed',
      trust_class TEXT NOT NULL DEFAULT 'deterministic',
      promotion_eligibility TEXT NOT NULL DEFAULT 'promotable',
      evidence_count INTEGER NULL,
      independent_source_count INTEGER NULL,
      extracted_by_model TEXT NULL,
      trust_reason TEXT NULL,
      valid_from TEXT NULL,
      valid_to TEXT NULL,
      last_confirmed_at TEXT NULL,
      title TEXT NULL,
      canonical_text TEXT NOT NULL DEFAULT '',
      summary TEXT NULL,
      domain TEXT NOT NULL DEFAULT 'unknown',
      sensitivity TEXT NOT NULL DEFAULT 'unknown',
      first_seen_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      last_seen_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      last_reviewed_at TEXT NULL,
      metadata_json TEXT NOT NULL DEFAULT '{{}}',
      commit_digest TEXT NULL,
      confirmation_id TEXT NULL,
      project_id TEXT NULL,
      created_by_agent_id TEXT NULL,
      run_id TEXT NULL,
      superseded_by TEXT NULL,
      supersedes TEXT NULL,
      embedding BLOB NULL,
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      updated_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      deleted_at TEXT NULL,
      UNIQUE (id, user_id),
      CONSTRAINT memories_user_profile_memory_key_key
        UNIQUE (user_id, agent_profile_id, memory_key),
      CONSTRAINT memories_memory_type_check
        CHECK (memory_type IN ({_MEMORY_TYPES_SQL})),
      CONSTRAINT memories_status_check
        CHECK (status IN ({_MEMORY_STATUSES_SQL})),
      CONSTRAINT memories_confirmation_status_check
        CHECK (confirmation_status IN ({_MEMORY_CONFIRMATION_STATUSES_SQL})),
      CONSTRAINT memories_trust_class_check
        CHECK (trust_class IN ({_MEMORY_TRUST_CLASSES_SQL})),
      CONSTRAINT memories_promotion_eligibility_check
        CHECK (promotion_eligibility IN ({_MEMORY_PROMOTION_ELIGIBILITIES_SQL})),
      CONSTRAINT memories_domain_check
        CHECK (domain IN ({_DOMAINS_SQL})),
      CONSTRAINT memories_sensitivity_check
        CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
      CONSTRAINT memories_confidence_range_check
        CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
      CONSTRAINT memories_salience_range_check
        CHECK (salience IS NULL OR (salience >= 0.0 AND salience <= 1.0)),
      CONSTRAINT memories_evidence_count_non_negative_check
        CHECK (evidence_count IS NULL OR evidence_count >= 0),
      CONSTRAINT memories_independent_source_count_non_negative_check
        CHECK (independent_source_count IS NULL OR independent_source_count >= 0),
      CONSTRAINT memories_valid_range_check
        CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from),
      CONSTRAINT memories_seen_range_check
        CHECK (last_seen_at >= first_seen_at),
      CONSTRAINT memories_value_json_check
        CHECK (json_valid(value)),
      CONSTRAINT memories_source_event_ids_array_check
        CHECK (json_type(source_event_ids) = 'array'),
      CONSTRAINT memories_metadata_json_object_check
        CHECK (json_type(metadata_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS memory_revisions (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      memory_id TEXT NOT NULL,
      sequence_no INTEGER NOT NULL,
      action TEXT NOT NULL,
      memory_key TEXT NOT NULL,
      previous_value TEXT NULL,
      new_value TEXT NULL,
      source_event_ids TEXT NOT NULL,
      candidate TEXT NOT NULL,
      revision_number INTEGER NOT NULL,
      revision_type TEXT NOT NULL,
      text_before TEXT NULL,
      text_after TEXT NOT NULL,
      reason TEXT NULL,
      actor_type TEXT NOT NULL DEFAULT 'system',
      actor_id TEXT NULL,
      metadata_json TEXT NOT NULL DEFAULT '{{}}',
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      UNIQUE (id, user_id),
      UNIQUE (memory_id, sequence_no),
      CONSTRAINT memory_revisions_memory_fkey
        FOREIGN KEY (memory_id, user_id)
        REFERENCES memories(id, user_id)
        ON DELETE CASCADE,
      CONSTRAINT memory_revisions_revision_type_check
        CHECK (revision_type IN ({_REVISION_TYPES_SQL})),
      CONSTRAINT memory_revisions_revision_number_positive_check
        CHECK (revision_number >= 1),
      CONSTRAINT memory_revisions_metadata_json_object_check
        CHECK (json_type(metadata_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS provenance_links (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      target_type TEXT NOT NULL,
      target_id TEXT NOT NULL,
      source_id TEXT NULL,
      source_chunk_id TEXT NULL,
      quote TEXT NULL,
      evidence_role TEXT NOT NULL,
      confidence REAL NOT NULL DEFAULT 0.5,
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      UNIQUE (id, user_id),
      CONSTRAINT provenance_links_source_fkey
        FOREIGN KEY (source_id, user_id)
        REFERENCES sources(id, user_id)
        ON DELETE SET NULL,
      CONSTRAINT provenance_links_source_chunk_fkey
        FOREIGN KEY (source_chunk_id, user_id)
        REFERENCES source_chunks(id, user_id)
        ON DELETE SET NULL,
      CONSTRAINT provenance_links_evidence_role_check
        CHECK (evidence_role IN ({_EVIDENCE_ROLES_SQL})),
      CONSTRAINT provenance_links_confidence_range_check
        CHECK (confidence >= 0.0 AND confidence <= 1.0)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS graph_edges (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      from_type TEXT NOT NULL,
      from_id TEXT NOT NULL,
      to_type TEXT NOT NULL,
      to_id TEXT NOT NULL,
      edge_type TEXT NOT NULL,
      confidence REAL NOT NULL DEFAULT 0.5,
      explanation TEXT NULL,
      created_by TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      observed_at TEXT NULL,
      valid_from TEXT NULL,
      valid_to TEXT NULL,
      metadata_json TEXT NOT NULL DEFAULT '{{}}',
      UNIQUE (id, user_id),
      CONSTRAINT graph_edges_edge_type_check
        CHECK (edge_type IN ({_EDGE_TYPES_SQL})),
      CONSTRAINT graph_edges_confidence_range_check
        CHECK (confidence >= 0.0 AND confidence <= 1.0),
      CONSTRAINT graph_edges_valid_range_check
        CHECK (valid_from IS NULL OR valid_to IS NULL OR valid_to >= valid_from),
      CONSTRAINT graph_edges_metadata_json_object_check
        CHECK (json_type(metadata_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS open_loops (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      memory_id TEXT NULL,
      title TEXT NOT NULL,
      status TEXT NOT NULL,
      opened_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      due_at TEXT NULL,
      resolved_at TEXT NULL,
      resolution_note TEXT NULL,
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      updated_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      description TEXT NULL,
      priority TEXT NOT NULL DEFAULT 'normal',
      project_id TEXT NULL,
      person_id TEXT NULL,
      source_id TEXT NULL,
      closed_at TEXT NULL,
      domain TEXT NOT NULL DEFAULT 'unknown',
      sensitivity TEXT NOT NULL DEFAULT 'unknown',
      metadata_json TEXT NOT NULL DEFAULT '{{}}',
      UNIQUE (id, user_id),
      CONSTRAINT open_loops_memory_fkey
        FOREIGN KEY (memory_id, user_id)
        REFERENCES memories(id, user_id)
        ON DELETE SET NULL,
      CONSTRAINT open_loops_source_fkey
        FOREIGN KEY (source_id, user_id)
        REFERENCES sources(id, user_id)
        ON DELETE SET NULL,
      CONSTRAINT open_loops_status_check
        CHECK (status IN ({_OPEN_LOOP_STATUSES_SQL})),
      CONSTRAINT open_loops_priority_check
        CHECK (priority IN ({_OPEN_LOOP_PRIORITIES_SQL})),
      CONSTRAINT open_loops_title_length_check
        CHECK (length(title) <= 280),
      CONSTRAINT open_loops_resolution_note_length_check
        CHECK (resolution_note IS NULL OR length(resolution_note) <= 2000),
      CONSTRAINT open_loops_resolved_state_check
        CHECK (
          (status = 'open' AND resolved_at IS NULL AND resolution_note IS NULL)
          OR (status IN ('resolved', 'dismissed') AND resolved_at IS NOT NULL)
        ),
      CONSTRAINT open_loops_domain_check
        CHECK (domain IN ({_DOMAINS_SQL})),
      CONSTRAINT open_loops_sensitivity_check
        CHECK (sensitivity IN ({_SENSITIVITY_SQL})),
      CONSTRAINT open_loops_metadata_json_object_check
        CHECK (json_type(metadata_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS event_log (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      event_type TEXT NOT NULL,
      actor_type TEXT NOT NULL,
      actor_id TEXT NULL,
      target_type TEXT NULL,
      target_id TEXT NULL,
      occurred_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      payload_json TEXT NOT NULL DEFAULT '{{}}',
      trace_id TEXT NULL,
      run_id TEXT NULL,
      integrity_hash TEXT NULL,
      UNIQUE (id, user_id),
      CONSTRAINT event_log_event_type_length_check
        CHECK (length(event_type) BETWEEN 1 AND 160),
      CONSTRAINT event_log_actor_type_length_check
        CHECK (length(actor_type) BETWEEN 1 AND 80),
      CONSTRAINT event_log_payload_json_object_check
        CHECK (json_type(payload_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS agent_identities (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      agent_id TEXT NOT NULL,
      agent_type TEXT NOT NULL DEFAULT 'unknown',
      permission_profile TEXT NOT NULL DEFAULT 'read_only_agent',
      display_name TEXT NULL,
      project_scope_json TEXT NOT NULL DEFAULT '[]',
      metadata_json TEXT NOT NULL DEFAULT '{{}}',
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      updated_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      UNIQUE (id, user_id),
      UNIQUE (user_id, agent_id),
      CONSTRAINT agent_identities_agent_type_check
        CHECK (agent_type IN ({_AGENT_TYPES_SQL})),
      CONSTRAINT agent_identities_permission_profile_check
        CHECK (permission_profile IN ({_PERMISSION_PROFILES_SQL})),
      CONSTRAINT agent_identities_project_scope_json_array_check
        CHECK (json_type(project_scope_json) = 'array'),
      CONSTRAINT agent_identities_metadata_json_object_check
        CHECK (json_type(metadata_json) = 'object')
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS agent_api_keys (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      agent_id TEXT NOT NULL,
      permission_profile TEXT NOT NULL,
      project_scope TEXT NULL,
      key_hash TEXT NOT NULL UNIQUE,
      key_prefix TEXT NOT NULL,
      label TEXT NULL,
      created_at TEXT NOT NULL DEFAULT {_NOW_UTC_ISO_SQL},
      revoked_at TEXT NULL,
      last_used_at TEXT NULL,
      UNIQUE (id, user_id),
      CONSTRAINT agent_api_keys_permission_profile_check
        CHECK (permission_profile IN ({_PERMISSION_PROFILES_SQL}))
    )
    """,
)

# Columns added to existing tables after their CREATE TABLE first shipped
# (mirrors Postgres migrations 20260704_0076 and 20260704_0077). The
# bootstrap's idempotent CREATE TABLE IF NOT EXISTS never alters an existing
# table, so pre-existing database files get these via a PRAGMA
# table_info-guarded ALTER TABLE in bootstrap_sqlite_schema. Runs before the
# index statements because memories_user_project_idx references
# memories.project_id (and memories_user_superseded_by_idx references
# memories.superseded_by).
_ADDITIVE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("memories", "project_id", "TEXT NULL"),
    ("memories", "created_by_agent_id", "TEXT NULL"),
    ("memories", "run_id", "TEXT NULL"),
    ("memories", "superseded_by", "TEXT NULL"),
    ("memories", "supersedes", "TEXT NULL"),
    ("agent_api_keys", "project_scope", "TEXT NULL"),
)

# One-shot backfills that run only when the paired additive column was just
# added to a pre-existing file (mirrors the Postgres 20260704_0077 backfill:
# supersession pointers were previously recorded only in metadata_json; the
# metadata copies are kept for backward compatibility).
_ADDITIVE_COLUMN_BACKFILLS: dict[tuple[str, str], str] = {
    ("memories", "superseded_by"): """
        UPDATE memories
        SET superseded_by = json_extract(metadata_json, '$.superseded_by')
        WHERE superseded_by IS NULL
          AND json_type(metadata_json, '$.superseded_by') = 'text'
        """,
    ("memories", "supersedes"): """
        UPDATE memories
        SET supersedes = json_extract(metadata_json, '$.supersedes')
        WHERE supersedes IS NULL
          AND json_type(metadata_json, '$.supersedes') = 'text'
        """,
}

_INDEX_AND_TRIGGER_STATEMENTS: tuple[str, ...] = (
    # Indexes mirroring the hot Postgres access paths.
    """
    CREATE INDEX IF NOT EXISTS sources_user_content_hash_idx
      ON sources (user_id, content_hash)
    """,
    """
    CREATE INDEX IF NOT EXISTS sources_user_captured_idx
      ON sources (user_id, captured_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS source_chunks_source_index_idx
      ON source_chunks (source_id, chunk_index)
    """,
    """
    CREATE INDEX IF NOT EXISTS memories_user_status_updated_idx
      ON memories (user_id, status, updated_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS memories_user_domain_sensitivity_updated_idx
      ON memories (user_id, domain, sensitivity, updated_at DESC, id DESC)
    """,
    # Partial project-scope index (mirrors memories_user_project_idx from
    # Postgres migration 20260704_0076).
    """
    CREATE INDEX IF NOT EXISTS memories_user_project_idx
      ON memories (user_id, project_id)
      WHERE project_id IS NOT NULL
    """,
    # Partial supersession index (mirrors memories_user_superseded_by_idx
    # from Postgres migration 20260704_0077).
    """
    CREATE INDEX IF NOT EXISTS memories_user_superseded_by_idx
      ON memories (user_id, superseded_by)
      WHERE superseded_by IS NOT NULL
    """,
    # Mirrors graph_edges_user_edge_idx from Postgres migration 20260510_0067.
    """
    CREATE INDEX IF NOT EXISTS graph_edges_user_edge_idx
      ON graph_edges (user_id, edge_type, created_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS memory_revisions_memory_created_idx
      ON memory_revisions (memory_id, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS provenance_links_target_idx
      ON provenance_links (user_id, target_type, target_id, created_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS open_loops_user_status_opened_idx
      ON open_loops (user_id, status, opened_at DESC, created_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS event_log_user_type_occurred_idx
      ON event_log (user_id, event_type, occurred_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS event_log_user_target_occurred_idx
      ON event_log (user_id, target_type, target_id, occurred_at DESC, id DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS agent_api_keys_user_agent_idx
      ON agent_api_keys (user_id, agent_id)
    """,
    # Append-only enforcement (mirrors app.reject_event_log_mutation and
    # app.reject_memory_revision_mutation in Postgres).
    """
    CREATE TRIGGER IF NOT EXISTS event_log_append_only_update
    BEFORE UPDATE ON event_log
    BEGIN
      SELECT RAISE(ABORT, 'event_log is append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS event_log_append_only_delete
    BEFORE DELETE ON event_log
    BEGIN
      SELECT RAISE(ABORT, 'event_log is append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS memory_revisions_append_only_update
    BEFORE UPDATE ON memory_revisions
    BEGIN
      SELECT RAISE(ABORT, 'memory_revisions is append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS memory_revisions_append_only_delete
    BEFORE DELETE ON memory_revisions
    BEGIN
      SELECT RAISE(ABORT, 'memory_revisions is append-only');
    END
    """,
    # External-content FTS5 index over the same fields as the Postgres
    # search_tsv column (plus memory_key), synced by triggers. The porter
    # stemmer mirrors the 'english' text-search configuration Postgres FTS
    # uses, so "approved" matches a query for "approve".
    """
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
      title,
      canonical_text,
      summary,
      memory_key,
      content='memories',
      tokenize='porter unicode61'
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS memories_fts_after_insert
    AFTER INSERT ON memories
    BEGIN
      INSERT INTO memories_fts(rowid, title, canonical_text, summary, memory_key)
      VALUES (new.rowid, new.title, new.canonical_text, new.summary, new.memory_key);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS memories_fts_after_delete
    AFTER DELETE ON memories
    BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, title, canonical_text, summary, memory_key)
      VALUES ('delete', old.rowid, old.title, old.canonical_text, old.summary, old.memory_key);
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS memories_fts_after_update
    AFTER UPDATE ON memories
    BEGIN
      INSERT INTO memories_fts(memories_fts, rowid, title, canonical_text, summary, memory_key)
      VALUES ('delete', old.rowid, old.title, old.canonical_text, old.summary, old.memory_key);
      INSERT INTO memories_fts(rowid, title, canonical_text, summary, memory_key)
      VALUES (new.rowid, new.title, new.canonical_text, new.summary, new.memory_key);
    END
    """,
)


# Full statement list, kept for introspection; bootstrap_sqlite_schema
# interleaves the additive-column guard between the two halves.
_SCHEMA_STATEMENTS: tuple[str, ...] = _TABLE_STATEMENTS + _INDEX_AND_TRIGGER_STATEMENTS


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    # Tolerate any row_factory the caller installed (tuples, sqlite3.Row,
    # or the store's dict rows): resolve the "name" column positionally
    # from the cursor description instead of hardcoding an index.
    cursor = conn.execute(f"PRAGMA table_info({table})")
    name_index = next(
        index for index, description in enumerate(cursor.description) if description[0] == "name"
    )
    columns: set[str] = set()
    for row in cursor.fetchall():
        if isinstance(row, dict):
            columns.add(str(row["name"]))
        else:
            columns.add(str(row[name_index]))
    return columns


def _ensure_additive_columns(conn: sqlite3.Connection) -> None:
    """Upgrade pre-existing database files with columns added after v1 DDL.

    A column's backfill (if any) runs exactly once, in the same bootstrap
    that adds the column; fresh files whose CREATE TABLE already carries the
    column never re-run it.
    """
    for table, column, declaration in _ADDITIVE_COLUMNS:
        if column not in _table_columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
            backfill = _ADDITIVE_COLUMN_BACKFILLS.get((table, column))
            if backfill is not None:
                conn.execute(backfill)


def bootstrap_sqlite_schema(conn: sqlite3.Connection) -> None:
    """Create or upgrade the vNext SQLite schema. Safe to call repeatedly."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    for statement in _TABLE_STATEMENTS:
        conn.execute(statement)
    # Existing files created before the scope columns shipped need ALTERs
    # before the index statements reference the new columns.
    _ensure_additive_columns(conn)
    for statement in _INDEX_AND_TRIGGER_STATEMENTS:
        conn.execute(statement)


__all__ = [
    "AGENT_TYPES",
    "DOMAINS",
    "EDGE_TYPES",
    "EVIDENCE_ROLES",
    "MEMORY_CONFIRMATION_STATUSES",
    "MEMORY_PROMOTION_ELIGIBILITIES",
    "MEMORY_STATUSES",
    "MEMORY_TRUST_CLASSES",
    "MEMORY_TYPES",
    "OPEN_LOOP_PRIORITIES",
    "OPEN_LOOP_STATUSES",
    "PERMISSION_PROFILES",
    "REVISION_TYPES",
    "SENSITIVITY_LEVELS",
    "bootstrap_sqlite_schema",
]
