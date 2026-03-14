from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import UUID

import psycopg

from alicebot_api.contracts import (
    TASK_ARTIFACT_LIST_ORDER,
    TASK_ARTIFACT_CHUNK_LIST_ORDER,
    TaskArtifactCreateResponse,
    TaskArtifactDetailResponse,
    TaskArtifactChunkListResponse,
    TaskArtifactChunkListSummary,
    TaskArtifactChunkRecord,
    TaskArtifactListResponse,
    TaskArtifactRecord,
    TaskArtifactIngestInput,
    TaskArtifactIngestionResponse,
    TaskArtifactRegisterInput,
    TaskArtifactStatus,
    TaskArtifactIngestionStatus,
)
from alicebot_api.store import ContinuityStore, TaskArtifactChunkRow, TaskArtifactRow
from alicebot_api.workspaces import TaskWorkspaceNotFoundError

SUPPORTED_TEXT_ARTIFACT_MEDIA_TYPES = ("text/plain", "text/markdown")
SUPPORTED_TEXT_ARTIFACT_EXTENSIONS = {
    ".txt": "text/plain",
    ".text": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
TASK_ARTIFACT_CHUNK_MAX_CHARS = 1000
TASK_ARTIFACT_CHUNKING_RULE = "normalized_utf8_text_fixed_window_1000_chars_v1"


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


def serialize_task_artifact_chunk_row(row: TaskArtifactChunkRow) -> TaskArtifactChunkRecord:
    return {
        "id": str(row["id"]),
        "task_artifact_id": str(row["task_artifact_id"]),
        "sequence_no": row["sequence_no"],
        "char_start": row["char_start"],
        "char_end_exclusive": row["char_end_exclusive"],
        "text": row["text"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def infer_task_artifact_media_type(row: TaskArtifactRow) -> str | None:
    if row["media_type_hint"] is not None:
        return row["media_type_hint"]

    artifact_path = Path(row["relative_path"])
    return SUPPORTED_TEXT_ARTIFACT_EXTENSIONS.get(artifact_path.suffix.lower())


def resolve_supported_task_artifact_media_type(row: TaskArtifactRow) -> str:
    media_type = infer_task_artifact_media_type(row)
    if media_type in SUPPORTED_TEXT_ARTIFACT_MEDIA_TYPES:
        return cast(str, media_type)

    supported_types = ", ".join(SUPPORTED_TEXT_ARTIFACT_MEDIA_TYPES)
    raise TaskArtifactValidationError(
        f"artifact {row['relative_path']} has unsupported media type "
        f"{media_type or 'unknown'}; supported types: {supported_types}"
    )


def normalize_artifact_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def chunk_normalized_artifact_text(
    text: str,
    *,
    chunk_size: int = TASK_ARTIFACT_CHUNK_MAX_CHARS,
) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    for char_start in range(0, len(text), chunk_size):
        char_end_exclusive = min(char_start + chunk_size, len(text))
        chunks.append((char_start, char_end_exclusive, text[char_start:char_end_exclusive]))
    return chunks


def resolve_registered_artifact_path(*, workspace_path: Path, relative_path: str) -> Path:
    artifact_path = (workspace_path / relative_path).resolve()
    ensure_artifact_path_is_rooted(
        workspace_path=workspace_path,
        artifact_path=artifact_path,
    )
    return artifact_path


def build_task_artifact_chunk_list_summary(
    chunk_rows: list[TaskArtifactChunkRow],
    *,
    media_type: str,
) -> TaskArtifactChunkListSummary:
    total_characters = sum(len(row["text"]) for row in chunk_rows)
    return {
        "total_count": len(chunk_rows),
        "total_characters": total_characters,
        "media_type": media_type,
        "chunking_rule": TASK_ARTIFACT_CHUNKING_RULE,
        "order": list(TASK_ARTIFACT_CHUNK_LIST_ORDER),
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


def ingest_task_artifact_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TaskArtifactIngestInput,
) -> TaskArtifactIngestionResponse:
    del user_id

    row = store.get_task_artifact_optional(request.task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {request.task_artifact_id} was not found")

    store.lock_task_artifact_ingestion(row["id"])
    row = store.get_task_artifact_optional(request.task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {request.task_artifact_id} was not found")

    media_type = resolve_supported_task_artifact_media_type(row)
    chunk_rows = store.list_task_artifact_chunks(row["id"])
    if row["ingestion_status"] == "ingested":
        return {
            "artifact": serialize_task_artifact_row(row),
            "summary": build_task_artifact_chunk_list_summary(chunk_rows, media_type=media_type),
        }

    workspace = store.get_task_workspace_optional(row["task_workspace_id"])
    if workspace is None:
        raise TaskWorkspaceNotFoundError(
            f"task workspace {row['task_workspace_id']} was not found"
        )

    workspace_path = Path(workspace["local_path"]).expanduser().resolve()
    artifact_path = resolve_registered_artifact_path(
        workspace_path=workspace_path,
        relative_path=row["relative_path"],
    )
    _require_existing_file(artifact_path)

    try:
        text = artifact_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TaskArtifactValidationError(
            f"artifact {row['relative_path']} is not valid UTF-8 text"
        ) from exc

    normalized_text = normalize_artifact_text(text)
    for index, (char_start, char_end_exclusive, chunk_text) in enumerate(
        chunk_normalized_artifact_text(normalized_text),
        start=1,
    ):
        store.create_task_artifact_chunk(
            task_artifact_id=row["id"],
            sequence_no=index,
            char_start=char_start,
            char_end_exclusive=char_end_exclusive,
            text=chunk_text,
        )

    artifact_row = store.update_task_artifact_ingestion_status(
        task_artifact_id=row["id"],
        ingestion_status="ingested",
    )
    chunk_rows = store.list_task_artifact_chunks(row["id"])
    return {
        "artifact": serialize_task_artifact_row(artifact_row),
        "summary": build_task_artifact_chunk_list_summary(chunk_rows, media_type=media_type),
    }


def list_task_artifact_chunk_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
    task_artifact_id: UUID,
) -> TaskArtifactChunkListResponse:
    del user_id

    row = store.get_task_artifact_optional(task_artifact_id)
    if row is None:
        raise TaskArtifactNotFoundError(f"task artifact {task_artifact_id} was not found")

    chunk_rows = store.list_task_artifact_chunks(task_artifact_id)
    media_type = infer_task_artifact_media_type(row) or "unknown"
    return {
        "items": [serialize_task_artifact_chunk_row(chunk_row) for chunk_row in chunk_rows],
        "summary": build_task_artifact_chunk_list_summary(chunk_rows, media_type=media_type),
    }
