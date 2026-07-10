"""Derived retrieval keys (``fact_keys``) join the memory FTS stream.

Strict lexical search cannot bridge category-phrased questions to
instance-phrased memories: "charity event fundraising total" shares no
token with a memory that only says "Bike-a-Thon raised $5,000".
``alicebot_api.vnext_fact_keys`` derives capped hypernym/attribute/unit
phrasings per memory; this migration gives them a home and folds them
into full-text search:

- ``memories.fact_keys text NULL`` -- NULL means "never derived" (the
  backfill target), ``''`` means "derived, nothing to add".
- ``memories.search_tsv`` is a stored GENERATED column (from
  ``20260704_0072``), so its expression cannot be altered in place: drop
  and re-add it with a fourth ``setweight(..., 'D')`` term over
  ``fact_keys``. ``ts_rank``'s default weights score ``'D'`` lexemes at
  0.1 versus title's 1.0, so derived keys make rows FINDABLE without
  outranking direct text matches. ADD COLUMN computes the generated
  column for existing rows, and the GIN index is rebuilt on top.

The SQLite mirror is the ``fact_keys`` column on the ``memories_fts``
FTS5 table in ``alicebot_api.sqlite_schema`` (bm25 weight 0.1).

Revision ID: 20260707_0082
Revises: 20260707_0081
"""

from __future__ import annotations

from alembic import op


revision = "20260707_0082"
down_revision = "20260707_0081"
branch_labels = None
depends_on = None


_SEARCH_TSV_WITH_FACT_KEYS_SQL = """
        ALTER TABLE memories
          ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A')
            || setweight(to_tsvector('english', coalesce(canonical_text, '')), 'B')
            || setweight(to_tsvector('english', coalesce(summary, '')), 'C')
            || setweight(to_tsvector('english', coalesce(fact_keys, '')), 'D')
          ) STORED
        """

# The pre-0082 expression from 20260704_0072, restored on downgrade.
_SEARCH_TSV_WITHOUT_FACT_KEYS_SQL = """
        ALTER TABLE memories
          ADD COLUMN search_tsv tsvector
          GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A')
            || setweight(to_tsvector('english', coalesce(canonical_text, '')), 'B')
            || setweight(to_tsvector('english', coalesce(summary, '')), 'C')
          ) STORED
        """

_CREATE_SEARCH_TSV_INDEX_SQL = """
        CREATE INDEX memories_search_tsv_gin_idx
          ON memories USING gin (search_tsv)
        """

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE memories
          ADD COLUMN fact_keys text NULL
        """,
    "DROP INDEX IF EXISTS memories_search_tsv_gin_idx",
    "ALTER TABLE memories DROP COLUMN IF EXISTS search_tsv",
    _SEARCH_TSV_WITH_FACT_KEYS_SQL,
    _CREATE_SEARCH_TSV_INDEX_SQL,
)

_DOWNGRADE_STATEMENTS = (
    "DROP INDEX IF EXISTS memories_search_tsv_gin_idx",
    "ALTER TABLE memories DROP COLUMN IF EXISTS search_tsv",
    _SEARCH_TSV_WITHOUT_FACT_KEYS_SQL,
    _CREATE_SEARCH_TSV_INDEX_SQL,
    "ALTER TABLE memories DROP COLUMN IF EXISTS fact_keys",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
