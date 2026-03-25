"""Add profile-scoped runtime model provider/name configuration."""

from __future__ import annotations

from alembic import op


revision = "20260325_0036"
down_revision = "20260325_0035"
branch_labels = None
depends_on = None

AGENT_PROFILE_RUNTIME_SEED_ROWS = (
    ("assistant_default", "openai_responses", "gpt-5-mini"),
    ("coach_default", "openai_responses", "gpt-5"),
)

_AGENT_PROFILE_RUNTIME_SEED_VALUES_SQL = ", ".join(
    f"('{profile_id}', '{model_provider}', '{model_name}')"
    for profile_id, model_provider, model_name in AGENT_PROFILE_RUNTIME_SEED_ROWS
)

_UPGRADE_STATEMENTS = (
    """
        ALTER TABLE agent_profiles
          ADD COLUMN model_provider text NULL
        """,
    """
        ALTER TABLE agent_profiles
          ADD COLUMN model_name text NULL
        """,
    """
        ALTER TABLE agent_profiles
          ADD CONSTRAINT agent_profiles_model_provider_check
          CHECK (model_provider IS NULL OR model_provider = 'openai_responses')
        """,
    """
        ALTER TABLE agent_profiles
          ADD CONSTRAINT agent_profiles_model_runtime_pairing_check
          CHECK (
            (model_provider IS NULL AND model_name IS NULL)
            OR
            (model_provider IS NOT NULL AND char_length(model_name) > 0)
          )
        """,
    f"""
        UPDATE agent_profiles
        SET model_provider = seeded.model_provider,
            model_name = seeded.model_name
        FROM (
          VALUES {_AGENT_PROFILE_RUNTIME_SEED_VALUES_SQL}
        ) AS seeded (id, model_provider, model_name)
        WHERE agent_profiles.id = seeded.id
        """,
)

_DOWNGRADE_STATEMENTS = (
    "ALTER TABLE agent_profiles DROP CONSTRAINT IF EXISTS agent_profiles_model_runtime_pairing_check",
    "ALTER TABLE agent_profiles DROP CONSTRAINT IF EXISTS agent_profiles_model_provider_check",
    "ALTER TABLE agent_profiles DROP COLUMN IF EXISTS model_name",
    "ALTER TABLE agent_profiles DROP COLUMN IF EXISTS model_provider",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
