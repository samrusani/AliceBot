from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict
from uuid import NAMESPACE_URL, UUID, uuid5

from alicebot_api.db import set_current_user, set_current_user_account


LOCAL_WORKSPACE_NAME = "Alice local workspace"
LOCAL_WORKSPACE_NAMESPACE = "https://alicebot.dev/local-workspace/"


class LocalWorkspaceRow(TypedDict):
    id: UUID
    owner_user_account_id: UUID
    slug: str
    name: str
    bootstrap_status: str
    bootstrapped_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LocalWorkspaceContext(TypedDict):
    user_account_id: UUID
    workspace: LocalWorkspaceRow


def local_workspace_id(user_account_id: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"{LOCAL_WORKSPACE_NAMESPACE}{user_account_id}")


def _set_local_identity_context(conn: Any, user_account_id: UUID) -> None:
    # Core memory RLS and the inert hosted-era provider tables use different
    # context names. Local identity deliberately sets both to the same actor.
    set_current_user(conn, user_account_id)
    set_current_user_account(conn, user_account_id)


def ensure_local_workspace(conn: Any, *, user_account_id: UUID) -> LocalWorkspaceContext:
    """Ensure the one deterministic local provider workspace for an Alice identity."""

    _set_local_identity_context(conn, user_account_id)
    workspace_id = local_workspace_id(user_account_id)
    local_email = f"local+{user_account_id.hex}@alicebot.invalid"
    local_slug = f"local-{user_account_id.hex}"

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE id = %s", (user_account_id,))
        if cur.fetchone() is None:
            raise LookupError(f"local Alice user {user_account_id} was not found")
        cur.execute(
            """
            INSERT INTO user_accounts (id, email, display_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (user_account_id, local_email, "Alice local operator"),
        )
        cur.execute(
            """
            INSERT INTO workspaces (
              id, owner_user_account_id, slug, name, bootstrap_status, bootstrapped_at
            )
            VALUES (%s, %s, %s, %s, 'ready', clock_timestamp())
            ON CONFLICT (id) DO UPDATE
            SET owner_user_account_id = EXCLUDED.owner_user_account_id,
                name = EXCLUDED.name,
                bootstrap_status = 'ready',
                bootstrapped_at = COALESCE(workspaces.bootstrapped_at, clock_timestamp()),
                updated_at = clock_timestamp()
            RETURNING id, owner_user_account_id, slug, name, bootstrap_status,
                      bootstrapped_at, created_at, updated_at
            """,
            (workspace_id, user_account_id, local_slug, LOCAL_WORKSPACE_NAME),
        )
        workspace = cur.fetchone()
        if workspace is None:  # pragma: no cover - INSERT ... RETURNING invariant
            raise RuntimeError("failed to ensure local workspace")
        cur.execute(
            """
            INSERT INTO workspace_members (workspace_id, user_account_id, role)
            VALUES (%s, %s, 'owner')
            ON CONFLICT (workspace_id, user_account_id) DO UPDATE
            SET role = 'owner'
            """,
            (workspace_id, user_account_id),
        )

    return {"user_account_id": user_account_id, "workspace": workspace}


def get_local_workspace(conn: Any, *, user_account_id: UUID) -> LocalWorkspaceContext | None:
    _set_local_identity_context(conn, user_account_id)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, owner_user_account_id, slug, name, bootstrap_status,
                   bootstrapped_at, created_at, updated_at
            FROM workspaces
            WHERE id = %s
              AND owner_user_account_id = %s
            LIMIT 1
            """,
            (local_workspace_id(user_account_id), user_account_id),
        )
        workspace = cur.fetchone()
    if workspace is None:
        return None
    return {"user_account_id": user_account_id, "workspace": workspace}


def serialize_local_workspace(workspace: LocalWorkspaceRow) -> dict[str, object]:
    return {
        "id": str(workspace["id"]),
        "owner_user_account_id": str(workspace["owner_user_account_id"]),
        "slug": workspace["slug"],
        "name": workspace["name"],
        "bootstrap_status": workspace["bootstrap_status"],
        "bootstrapped_at": (
            None if workspace["bootstrapped_at"] is None else workspace["bootstrapped_at"].isoformat()
        ),
        "created_at": workspace["created_at"].isoformat(),
        "updated_at": workspace["updated_at"].isoformat(),
    }


__all__ = [
    "LOCAL_WORKSPACE_NAME",
    "LocalWorkspaceContext",
    "LocalWorkspaceRow",
    "ensure_local_workspace",
    "get_local_workspace",
    "local_workspace_id",
    "serialize_local_workspace",
]
