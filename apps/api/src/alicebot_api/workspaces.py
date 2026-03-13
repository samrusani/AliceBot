from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import UUID

from alicebot_api.config import Settings
from alicebot_api.contracts import (
    TASK_WORKSPACE_LIST_ORDER,
    TaskWorkspaceCreateInput,
    TaskWorkspaceCreateResponse,
    TaskWorkspaceDetailResponse,
    TaskWorkspaceListResponse,
    TaskWorkspaceRecord,
    TaskWorkspaceStatus,
)
from alicebot_api.tasks import TaskNotFoundError
from alicebot_api.store import ContinuityStore, TaskWorkspaceRow


class TaskWorkspaceNotFoundError(LookupError):
    """Raised when a task workspace record is not visible inside the current user scope."""


class TaskWorkspaceAlreadyExistsError(RuntimeError):
    """Raised when an active task workspace already exists for a task."""


class TaskWorkspaceProvisioningError(RuntimeError):
    """Raised when local workspace provisioning cannot satisfy rooted path rules."""


def resolve_workspace_root(workspace_root: str) -> Path:
    return Path(workspace_root).expanduser().resolve()


def build_task_workspace_path(
    *,
    workspace_root: Path,
    user_id: UUID,
    task_id: UUID,
) -> Path:
    return workspace_root / str(user_id) / str(task_id)


def ensure_workspace_path_is_rooted(
    *,
    workspace_root: Path,
    workspace_path: Path,
) -> None:
    resolved_root = workspace_root.resolve()
    resolved_path = workspace_path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise TaskWorkspaceProvisioningError(
            f"workspace path {resolved_path} escapes configured root {resolved_root}"
        ) from exc


def serialize_task_workspace_row(row: TaskWorkspaceRow) -> TaskWorkspaceRecord:
    return {
        "id": str(row["id"]),
        "task_id": str(row["task_id"]),
        "status": cast(TaskWorkspaceStatus, row["status"]),
        "local_path": row["local_path"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def create_task_workspace_record(
    store: ContinuityStore,
    *,
    settings: Settings,
    user_id: UUID,
    request: TaskWorkspaceCreateInput,
) -> TaskWorkspaceCreateResponse:
    task = store.get_task_optional(request.task_id)
    if task is None:
        raise TaskNotFoundError(f"task {request.task_id} was not found")

    workspace_root = resolve_workspace_root(settings.task_workspace_root)
    workspace_path = build_task_workspace_path(
        workspace_root=workspace_root,
        user_id=user_id,
        task_id=request.task_id,
    )
    ensure_workspace_path_is_rooted(
        workspace_root=workspace_root,
        workspace_path=workspace_path,
    )

    store.lock_task_workspaces(request.task_id)
    existing_workspace = store.get_active_task_workspace_for_task_optional(request.task_id)
    if existing_workspace is not None:
        raise TaskWorkspaceAlreadyExistsError(
            f"task {request.task_id} already has active workspace {existing_workspace['id']}"
        )

    try:
        workspace_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TaskWorkspaceProvisioningError(
            f"workspace path {workspace_path} could not be provisioned"
        ) from exc

    row = store.create_task_workspace(
        task_id=request.task_id,
        status=request.status,
        local_path=str(workspace_path),
    )
    return {"workspace": serialize_task_workspace_row(row)}


def list_task_workspace_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> TaskWorkspaceListResponse:
    del user_id

    items = [serialize_task_workspace_row(row) for row in store.list_task_workspaces()]
    return {
        "items": items,
        "summary": {
            "total_count": len(items),
            "order": list(TASK_WORKSPACE_LIST_ORDER),
        },
    }


def get_task_workspace_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_workspace_id: UUID,
) -> TaskWorkspaceDetailResponse:
    del user_id

    row = store.get_task_workspace_optional(task_workspace_id)
    if row is None:
        raise TaskWorkspaceNotFoundError(f"task workspace {task_workspace_id} was not found")
    return {"workspace": serialize_task_workspace_row(row)}
