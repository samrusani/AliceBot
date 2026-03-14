from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import UUID

import psycopg

from alicebot_api.contracts import (
    TASK_ARTIFACT_LIST_ORDER,
    TaskArtifactCreateResponse,
    TaskArtifactDetailResponse,
    TaskArtifactListResponse,
    TaskArtifactRecord,
    TaskArtifactRegisterInput,
    TaskArtifactStatus,
    TaskArtifactIngestionStatus,
)
from alicebot_api.store import ContinuityStore, TaskArtifactRow
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


class TaskArtifactNotFoundError(LookupError):
    """Raised when a task artifact is not visible inside the current user scope."""


class TaskArtifactAlreadyExistsError(RuntimeError):
    """Raised when the same workspace-relative artifact path is registered twice."""


class TaskArtifactValidationError(ValueError):
    """Raised when a local artifact path cannot satisfy registration constraints."""


def resolve_artifact_path(local_path: str) -> Path:
    return Path(local_path).expanduser().resolve()


def ensure_artifact_path_is_rooted(*, workspace_path: Path, artifact_path: Path) -> None:
    resolved_workspace_path = workspace_path.resolve()
    resolved_artifact_path = artifact_path.resolve()
    try:
        resolved_artifact_path.relative_to(resolved_workspace_path)
    except ValueError as exc:
        raise TaskArtifactValidationError(
            f"artifact path {resolved_artifact_path} escapes workspace root {resolved_workspace_path}"
        ) from exc


def build_workspace_relative_artifact_path(*, workspace_path: Path, artifact_path: Path) -> str:
    relative_path = artifact_path.relative_to(workspace_path).as_posix()
    if relative_path in ("", "."):
        raise TaskArtifactValidationError(
            f"artifact path {artifact_path} must point to a file beneath workspace root {workspace_path}"
        )
    return relative_path


def _require_existing_file(artifact_path: Path) -> None:
    if not artifact_path.exists():
        raise TaskArtifactValidationError(f"artifact path {artifact_path} was not found")
    if not artifact_path.is_file():
        raise TaskArtifactValidationError(f"artifact path {artifact_path} is not a regular file")


def _duplicate_registration_message(*, task_workspace_id: UUID, relative_path: str) -> str:
    return (
        f"artifact {relative_path} is already registered for task workspace {task_workspace_id}"
    )


def serialize_task_artifact_row(row: TaskArtifactRow) -> TaskArtifactRecord:
    return {
        "id": str(row["id"]),
        "task_id": str(row["task_id"]),
        "task_workspace_id": str(row["task_workspace_id"]),
        "status": cast(TaskArtifactStatus, row["status"]),
        "ingestion_status": cast(TaskArtifactIngestionStatus, row["ingestion_status"]),
        "relative_path": row["relative_path"],
        "media_type_hint": row["media_type_hint"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def register_task_artifact_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskArtifactRegisterInput,
) -> TaskArtifactCreateResponse:
    del user_id

    workspace = store.get_task_workspace_optional(request.task_workspace_id)
    if workspace is None:
        raise TaskWorkspaceNotFoundError(
            f"task workspace {request.task_workspace_id} was not found"
        )

    workspace_path = Path(workspace["local_path"]).expanduser().resolve()
    artifact_path = resolve_artifact_path(request.local_path)
    _require_existing_file(artifact_path)
    ensure_artifact_path_is_rooted(
        workspace_path=workspace_path,
        artifact_path=artifact_path,
    )
    relative_path = build_workspace_relative_artifact_path(
        workspace_path=workspace_path,
        artifact_path=artifact_path,
    )

    store.lock_task_artifacts(workspace["id"])
    existing = store.get_task_artifact_by_workspace_relative_path_optional(
        task_workspace_id=workspace["id"],
        relative_path=relative_path,
    )
    if existing is not None:
        raise TaskArtifactAlreadyExistsError(
            _duplicate_registration_message(
                task_workspace_id=workspace["id"],
                relative_path=relative_path,
            )
        )

    try:
        row = store.create_task_artifact(
            task_id=workspace["task_id"],
            task_workspace_id=workspace["id"],
            status="registered",
            ingestion_status="pending",
            relative_path=relative_path,
            media_type_hint=request.media_type_hint,
        )
    except psycopg.errors.UniqueViolation as exc:
        raise TaskArtifactAlreadyExistsError(
            _duplicate_registration_message(
                task_workspace_id=workspace["id"],
                relative_path=relative_path,
            )
        ) from exc

    return {"artifact": serialize_task_artifact_row(row)}


def list_task_artifact_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> TaskArtifactListResponse:
    del user_id

    items = [serialize_task_artifact_row(row) for row in store.list_task_artifacts()]
    return {
        "items": items,
        "summary": {
            "total_count": len(items),
            "order": list(TASK_ARTIFACT_LIST_ORDER),
        },
    }


def get_task_artifact_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_artifact_id: UUID,
) -> TaskArtifactDetailResponse:
    del user_id

    row = store.get_task_artifact_optional(task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")
    return {"artifact": serialize_task_artifact_row(row)}
