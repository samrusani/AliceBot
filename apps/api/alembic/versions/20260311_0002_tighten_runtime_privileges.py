"""Tighten the runtime role to insert/select-only continuity access."""

from __future__ import annotations

from alembic import op


revision = "20260311_0002"
down_revision = "20260310_0001"
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = (
    "REVOKE UPDATE ON users FROM alicebot_app",
    "REVOKE UPDATE ON threads FROM alicebot_app",
    "REVOKE UPDATE ON sessions FROM alicebot_app",
)

# Revision 20260310_0001 already leaves the runtime role with no UPDATE grants
# on these tables. Downgrading back to that revision should therefore preserve
# the same privilege floor explicitly rather than re-introducing broader access.
_DOWNGRADE_STATEMENTS = (
    "REVOKE UPDATE ON users FROM alicebot_app",
    "REVOKE UPDATE ON threads FROM alicebot_app",
    "REVOKE UPDATE ON sessions FROM alicebot_app",
)


def _execute_statements(statements: tuple[str, ...]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_statements(_UPGRADE_STATEMENTS)


def downgrade() -> None:
    _execute_statements(_DOWNGRADE_STATEMENTS)
