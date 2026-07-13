"""Fence workflow-produced graph edges by logical idempotency digest.

Revision ID: 20260713_0089
Revises: 20260713_0088
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text


revision = "20260713_0089"
down_revision = "20260713_0088"
branch_labels = None
depends_on = None


INDEX_NAME = "graph_edges_user_idempotency_digest_uidx"
_INDEX_INVALIDITY_QUERY = """
    SELECT NOT index_metadata.indisvalid
    FROM pg_catalog.pg_class AS index_class
    JOIN pg_catalog.pg_index AS index_metadata
      ON index_metadata.indexrelid = index_class.oid
    JOIN pg_catalog.pg_namespace AS index_namespace
      ON index_namespace.oid = index_class.relnamespace
    WHERE index_class.relkind = 'i'
      AND index_namespace.nspname = current_schema()
      AND index_class.relname = :index_name
    """


def _index_is_invalid() -> bool:
    invalid = op.get_bind().execute(text(_INDEX_INVALIDITY_QUERY), {"index_name": INDEX_NAME}).scalar_one_or_none()
    return invalid is True


def upgrade() -> None:
    with op.get_context().autocommit_block():
        if _index_is_invalid():
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}")
        op.execute(
            f"""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME}
              ON graph_edges (user_id, (metadata_json ->> 'idempotency_digest'))
              WHERE metadata_json ->> 'idempotency_digest' IS NOT NULL
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}")
