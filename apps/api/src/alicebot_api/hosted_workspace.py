from __future__ import annotations

from datetime import datetime
import re
from typing import TypedDict
from uuid import UUID

import psycopg


SLUG_SANITIZE_PATTERN = re.compile(r"[^a-z0-9-]+")
SLUG_COLLAPSE_PATTERN = re.compile(r"-+")


class HostedWorkspaceNotFoundError(LookupError):
    """Raised when a hosted workspace is not visible for the current account."""


class HostedWorkspaceBootstrapConflictError(RuntimeError):
    """Raised when hosted bootstrap is requested after completion."""


class WorkspaceRow(TypedDict):
    id: UUID
    owner_user_account_id: UUID
    slug: str
    name: str
    bootstrap_status: str
    bootstrapped_at: datetime | None
    created_at: datetime
    updated_at: datetime


def slugify_workspace_name(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "-")
    normalized = SLUG_SANITIZE_PATTERN.sub("-", normalized)
    normalized = SLUG_COLLAPSE_PATTERN.sub("-", normalized).strip("-")
    if normalized == "":
        return "alice-workspace"
    return normalized[:120]


def _iter_candidate_slugs(*, preferred_slug: str):
    base_slug = slugify_workspace_name(preferred_slug)
    for suffix in range(1, 201):
        yield base_slug if suffix == 1 else f"{base_slug}-{suffix}"


def create_workspace(
    conn,
    *,
    user_account_id: UUID,
    name: str,
    slug: str | None,
) -> WorkspaceRow:
    workspace_name = name.strip()
    if workspace_name == "":
        raise ValueError("workspace name is required")

    preferred_slug = slug if slug is not None and slug.strip() != "" else workspace_name
    for workspace_slug in _iter_candidate_slugs(preferred_slug=preferred_slug):
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO workspaces (owner_user_account_id, slug, name, bootstrap_status)
                        VALUES (%s, %s, %s, 'pending')
                        RETURNING id, owner_user_account_id, slug, name, bootstrap_status, bootstrapped_at,
                                  created_at, updated_at
                        """,
                        (user_account_id, workspace_slug, workspace_name),
                    )
                    workspace = cur.fetchone()

                    if workspace is None:
                        raise RuntimeError("failed to create workspace")

                    cur.execute(
                        """
                        INSERT INTO workspace_members (workspace_id, user_account_id, role)
                        VALUES (%s, %s, 'owner')
                        ON CONFLICT (workspace_id, user_account_id) DO UPDATE
                        SET role = EXCLUDED.role
                        """,
                        (workspace["id"], user_account_id),
                    )
                return workspace
        except psycopg.errors.UniqueViolation as exc:
            if exc.diag.constraint_name != "workspaces_slug_key":
                raise

    raise RuntimeError("unable to allocate unique workspace slug")


def get_workspace_for_member(
    conn,
    *,
    workspace_id: UUID,
    user_account_id: UUID,
) -> WorkspaceRow | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT w.id,
                   w.owner_user_account_id,
                   w.slug,
                   w.name,
                   w.bootstrap_status,
                   w.bootstrapped_at,
                   w.created_at,
                   w.updated_at
            FROM workspaces AS w
            JOIN workspace_members AS wm
              ON wm.workspace_id = w.id
            WHERE w.id = %s
              AND wm.user_account_id = %s
            LIMIT 1
            """,
            (workspace_id, user_account_id),
        )
        row = cur.fetchone()

    return row


def get_current_workspace(
    conn,
    *,
    user_account_id: UUID,
    preferred_workspace_id: UUID | None,
) -> WorkspaceRow | None:
    if preferred_workspace_id is not None:
        preferred = get_workspace_for_member(
            conn,
            workspace_id=preferred_workspace_id,
            user_account_id=user_account_id,
        )
        if preferred is not None:
            return preferred

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT w.id,
                   w.owner_user_account_id,
                   w.slug,
                   w.name,
                   w.bootstrap_status,
                   w.bootstrapped_at,
                   w.created_at,
                   w.updated_at
            FROM workspaces AS w
            JOIN workspace_members AS wm
              ON wm.workspace_id = w.id
            WHERE wm.user_account_id = %s
            ORDER BY CASE WHEN wm.role = 'owner' THEN 0 ELSE 1 END,
                     w.created_at ASC,
                     w.id ASC
            LIMIT 1
            """,
            (user_account_id,),
        )
        row = cur.fetchone()

    return row


def set_session_workspace(
    conn,
    *,
    session_id: UUID,
    user_account_id: UUID,
    workspace_id: UUID,
) -> None:
    workspace = get_workspace_for_member(
        conn,
        workspace_id=workspace_id,
        user_account_id=user_account_id,
    )
    if workspace is None:
        raise HostedWorkspaceNotFoundError(f"workspace {workspace_id} was not found")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE auth_sessions
            SET workspace_id = %s
            WHERE id = %s
              AND user_account_id = %s
            """,
            (workspace_id, session_id, user_account_id),
        )


def complete_workspace_bootstrap(
    conn,
    *,
    workspace_id: UUID,
    user_account_id: UUID,
) -> WorkspaceRow:
    workspace = get_workspace_for_member(
        conn,
        workspace_id=workspace_id,
        user_account_id=user_account_id,
    )
    if workspace is None:
        raise HostedWorkspaceNotFoundError(f"workspace {workspace_id} was not found")

    if workspace["bootstrap_status"] == "ready":
        raise HostedWorkspaceBootstrapConflictError(
            f"workspace {workspace_id} bootstrap is already complete"
        )

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE workspaces
            SET bootstrap_status = 'ready',
                bootstrapped_at = clock_timestamp(),
                updated_at = clock_timestamp()
            WHERE id = %s
            RETURNING id, owner_user_account_id, slug, name, bootstrap_status, bootstrapped_at,
                      created_at, updated_at
            """,
            (workspace_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise HostedWorkspaceNotFoundError(f"workspace {workspace_id} was not found")
    return row


def get_bootstrap_status(
    conn,
    *,
    workspace_id: UUID,
    user_account_id: UUID,
) -> dict[str, object]:
    workspace = get_workspace_for_member(
        conn,
        workspace_id=workspace_id,
        user_account_id=user_account_id,
    )
    if workspace is None:
        raise HostedWorkspaceNotFoundError(f"workspace {workspace_id} was not found")

    return {
        "workspace_id": str(workspace["id"]),
        "status": workspace["bootstrap_status"],
        "bootstrapped_at": None
        if workspace["bootstrapped_at"] is None
        else workspace["bootstrapped_at"].isoformat(),
        "ready_for_next_phase_telegram_linkage": workspace["bootstrap_status"] == "ready",
        "telegram_state": "available_in_p10_s2_transport",
    }


def serialize_workspace(workspace: WorkspaceRow) -> dict[str, object]:
    return {
        "id": str(workspace["id"]),
        "owner_user_account_id": str(workspace["owner_user_account_id"]),
        "slug": workspace["slug"],
        "name": workspace["name"],
        "bootstrap_status": workspace["bootstrap_status"],
        "bootstrapped_at": None
        if workspace["bootstrapped_at"] is None
        else workspace["bootstrapped_at"].isoformat(),
        "created_at": workspace["created_at"].isoformat(),
        "updated_at": workspace["updated_at"].isoformat(),
    }
