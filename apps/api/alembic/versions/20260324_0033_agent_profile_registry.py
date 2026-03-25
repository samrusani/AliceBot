"""Create durable agent profile registry and bind thread profile FK."""

from __future__ import annotations

from alembic import op


revision = "20260324_0033"
down_revision = "20260324_0032"
branch_labels = None
depends_on = None

AGENT_PROFILE_SEED_ROWS = (
    (
        "assistant_default",
        "Assistant Default",
        "General-purpose assistant profile for baseline conversations.",
    ),
    (
        "coach_default",
        "Coach Default",
        "Coaching-oriented profile focused on guidance and accountability.",
    ),
)

AGENT_PROFILE_IDS = tuple(profile_id for profile_id, *_ in AGENT_PROFILE_SEED_ROWS)
_AGENT_PROFILE_IDS_SQL = ", ".join(f"'{value}'" for value in AGENT_PROFILE_IDS)
_AGENT_PROFILE_SEED_VALUES_SQL = ", ".join(
    f"('{profile_id}', '{name}', '{description}')"
    for profile_id, name, description in AGENT_PROFILE_SEED_ROWS
)

_UPGRADE_STATEMENTS = (
    """
        CREATE TABLE agent_profiles (
          id text PRIMARY KEY,
          name text NOT NULL,
          description text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT agent_profiles_id_nonempty_check
            CHECK (char_length(id) > 0),
          CONSTRAINT agent_profiles_name_nonempty_check
            CHECK (char_length(name) > 0),
          CONSTRAINT agent_profiles_description_nonempty_check
            CHECK (char_length(description) > 0)
        )
        """,
    f"""
        INSERT INTO agent_profiles (id, name, description)
        VALUES {_AGENT_PROFILE_SEED_VALUES_SQL}
        """,
    "GRANT SELECT ON agent_profiles TO alicebot_app",
    "ALTER TABLE threads DROP CONSTRAINT IF EXISTS threads_agent_profile_id_check",
    """
        ALTER TABLE threads
          ADD CONSTRAINT threads_agent_profile_id_fkey
          FOREIGN KEY (agent_profile_id)
          REFERENCES agent_profiles(id)
        """,
)

_DOWNGRADE_STATEMENTS = (
    "ALTER TABLE threads DROP CONSTRAINT IF EXISTS threads_agent_profile_id_fkey",
    f"""
        ALTER TABLE threads
          ADD CONSTRAINT threads_agent_profile_id_check
          CHECK (agent_profile_id IN ({_AGENT_PROFILE_IDS_SQL}))
        """,
    "DROP TABLE IF EXISTS agent_profiles",
)


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
