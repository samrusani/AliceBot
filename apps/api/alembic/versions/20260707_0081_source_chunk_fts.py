"""Full-text search over source_chunks content.

``search_sources`` was content-blind: it LIKE-matched only
title/author/uri/raw_path/content_hash/metadata_json ordered by
captured_at DESC, so the source that actually SAYS the thing lost to
whatever was captured most recently. This adds the chunk-level substrate
``PostgresVNextStore.search_source_chunks`` queries: a stored generated
tsvector over ``source_chunks.text`` with a GIN index, following the
``memories.search_tsv`` pattern from ``20260704_0072``. Generated
columns are computed for existing rows at ADD COLUMN time, so historical
chunks are searchable immediately (the SQLite mirror is the
``source_chunks_fts`` FTS5 table in ``alicebot_api.sqlite_schema``).

Revision ID: 20260707_0081
Revises: 20260706_0080
"""

from __future__ import annotations

from alembic import op


revision = "20260707_0081"
down_revision = "20260706_0080"
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE source_chunks
          ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED
        """,
    """
        CREATE INDEX source_chunks_search_tsv_gin_idx
          ON source_chunks USING gin (search_tsv)
        """,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS source_chunks_search_tsv_gin_idx",
    "ALTER TABLE source_chunks DROP COLUMN IF EXISTS search_tsv",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
