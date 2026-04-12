"""Expand model-pack family constraint for Phase 11 tier-2 packs."""

from __future__ import annotations

from alembic import op


revision = "20260412_0056"
down_revision = "20260412_0055"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    "ALTER TABLE model_packs DROP CONSTRAINT IF EXISTS model_packs_family_check",
    (
        "ALTER TABLE model_packs ADD CONSTRAINT model_packs_family_check "
        "CHECK (family IN ('llama', 'qwen', 'gemma', 'gpt-oss', 'deepseek', 'kimi', 'mistral', 'custom'))"
    ),
)

_DOWNGRADE_STATEMENTS = (
    "ALTER TABLE model_packs DROP CONSTRAINT IF EXISTS model_packs_family_check",
    (
        "ALTER TABLE model_packs ADD CONSTRAINT model_packs_family_check "
        "CHECK (family IN ('llama', 'qwen', 'gemma', 'gpt-oss', 'custom'))"
    ),
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
