from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.artifacts import (
    TASK_ARTIFACT_CHUNKING_RULE,
    TaskArtifactAlreadyExistsError,
    TaskArtifactNotFoundError,
    TaskArtifactValidationError,
    build_workspace_relative_artifact_path,
    chunk_normalized_artifact_text,
    ensure_artifact_path_is_rooted,
    get_task_artifact_record,
    ingest_task_artifact_record,
    list_task_artifact_chunk_records,
    list_task_artifact_records,
    normalize_artifact_text,
    register_task_artifact_record,
    serialize_task_artifact_row,
)
from alicebot_api.contracts import TaskArtifactIngestInput, TaskArtifactRegisterInput
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


class ArtifactStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 10, 0, tzinfo=UTC)
        self.workspaces: list[dict[str, object]] = []
        self.artifacts: list[dict[str, object]] = []
        self.artifact_chunks: list[dict[str, object]] = []
        self.locked_workspace_ids: list[UUID] = []
        self.locked_artifact_ids: list[UUID] = []

    def create_task_workspace(self, *, task_workspace_id: UUID, task_id: UUID, user_id: UUID, local_path: str) -> dict[str, object]:
        workspace = {
            "id": task_workspace_id,
            "user_id": user_id,
            "task_id": task_id,
            "status": "active",
            "local_path": local_path,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.workspaces.append(workspace)
        return workspace

    def get_task_workspace_optional(self, task_workspace_id: UUID) -> dict[str, object] | None:
        return next((workspace for workspace in self.workspaces if workspace["id"] == task_workspace_id), None)

    def lock_task_artifacts(self, task_workspace_id: UUID) -> None:
        self.locked_workspace_ids.append(task_workspace_id)

    def get_task_artifact_by_workspace_relative_path_optional(
        self,
        *,
        task_workspace_id: UUID,
        relative_path: str,
    ) -> dict[str, object] | None:
        return next(
            (
                artifact
                for artifact in self.artifacts
                if artifact["task_workspace_id"] == task_workspace_id
                and artifact["relative_path"] == relative_path
            ),
            None,
        )

    def create_task_artifact(
        self,
        *,
        task_id: UUID,
        task_workspace_id: UUID,
        status: str,
        ingestion_status: str,
        relative_path: str,
        media_type_hint: str | None,
    ) -> dict[str, object]:
        artifact = {
            "id": uuid4(),
            "user_id": self.workspaces[0]["user_id"],
            "task_id": task_id,
            "task_workspace_id": task_workspace_id,
            "status": status,
            "ingestion_status": ingestion_status,
            "relative_path": relative_path,
            "media_type_hint": media_type_hint,
            "created_at": self.base_time + timedelta(minutes=len(self.artifacts)),
            "updated_at": self.base_time + timedelta(minutes=len(self.artifacts)),
        }
        self.artifacts.append(artifact)
        return artifact

    def list_task_artifacts(self) -> list[dict[str, object]]:
        return sorted(self.artifacts, key=lambda artifact: (artifact["created_at"], artifact["id"]))

    def get_task_artifact_optional(self, task_artifact_id: UUID) -> dict[str, object] | None:
        return next((artifact for artifact in self.artifacts if artifact["id"] == task_artifact_id), None)

    def lock_task_artifact_ingestion(self, task_artifact_id: UUID) -> None:
        self.locked_artifact_ids.append(task_artifact_id)

    def create_task_artifact_chunk(
        self,
        *,
        task_artifact_id: UUID,
        sequence_no: int,
        char_start: int,
        char_end_exclusive: int,
        text: str,
    ) -> dict[str, object]:
        chunk = {
            "id": uuid4(),
            "user_id": self.workspaces[0]["user_id"],
            "task_artifact_id": task_artifact_id,
            "sequence_no": sequence_no,
            "char_start": char_start,
            "char_end_exclusive": char_end_exclusive,
            "text": text,
            "created_at": self.base_time + timedelta(seconds=len(self.artifact_chunks)),
            "updated_at": self.base_time + timedelta(seconds=len(self.artifact_chunks)),
        }
        self.artifact_chunks.append(chunk)
        return chunk

    def list_task_artifact_chunks(self, task_artifact_id: UUID) -> list[dict[str, object]]:
        return sorted(
            (
                chunk
                for chunk in self.artifact_chunks
                if chunk["task_artifact_id"] == task_artifact_id
            ),
            key=lambda chunk: (chunk["sequence_no"], chunk["id"]),
        )

    def update_task_artifact_ingestion_status(
        self,
        *,
        task_artifact_id: UUID,
        ingestion_status: str,
    ) -> dict[str, object]:
        artifact = self.get_task_artifact_optional(task_artifact_id)
        assert artifact is not None
        artifact["ingestion_status"] = ingestion_status
        artifact["updated_at"] = self.base_time + timedelta(minutes=30)
        return artifact


def test_ensure_artifact_path_is_rooted_rejects_escape() -> None:
    with pytest.raises(TaskArtifactValidationError, match="escapes workspace root"):
        ensure_artifact_path_is_rooted(
            workspace_path=Path("/tmp/alicebot/task-workspaces/user/task"),
            artifact_path=Path("/tmp/alicebot/task-workspaces/user/task/../escape.txt"),
        )


def test_build_workspace_relative_artifact_path_returns_posix_path() -> None:
    relative_path = build_workspace_relative_artifact_path(
        workspace_path=Path("/tmp/alicebot/task-workspaces/user/task"),
        artifact_path=Path("/tmp/alicebot/task-workspaces/user/task/docs/spec.txt"),
    )

    assert relative_path == "docs/spec.txt"


def test_register_task_artifact_record_persists_relative_path_and_returns_record(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("spec")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )

    response = register_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactRegisterInput(
            task_workspace_id=task_workspace_id,
            local_path=str(artifact_path),
            media_type_hint="text/plain",
        ),
    )

    assert response == {
        "artifact": {
            "id": response["artifact"]["id"],
            "task_id": str(task_id),
            "task_workspace_id": str(task_workspace_id),
            "status": "registered",
            "ingestion_status": "pending",
            "relative_path": "docs/spec.txt",
            "media_type_hint": "text/plain",
            "created_at": "2026-03-13T10:00:00+00:00",
            "updated_at": "2026-03-13T10:00:00+00:00",
        }
    }
    assert store.locked_workspace_ids == [task_workspace_id]


def test_register_task_artifact_record_rejects_duplicate_relative_path(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("spec")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )

    register_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactRegisterInput(
            task_workspace_id=task_workspace_id,
            local_path=str(artifact_path),
            media_type_hint="text/plain",
        ),
    )

    with pytest.raises(
        TaskArtifactAlreadyExistsError,
        match=f"artifact docs/spec.txt is already registered for task workspace {task_workspace_id}",
    ):
        register_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactRegisterInput(
                task_workspace_id=task_workspace_id,
                local_path=str(artifact_path),
                media_type_hint="text/plain",
            ),
        )


def test_register_task_artifact_record_requires_visible_workspace(tmp_path) -> None:
    artifact_path = tmp_path / "spec.txt"
    artifact_path.write_text("spec")

    with pytest.raises(TaskWorkspaceNotFoundError, match="was not found"):
        register_task_artifact_record(
            ArtifactStoreStub(),
            user_id=uuid4(),
            request=TaskArtifactRegisterInput(
                task_workspace_id=uuid4(),
                local_path=str(artifact_path),
                media_type_hint=None,
            ),
        )


def test_register_task_artifact_record_rejects_paths_outside_workspace(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    outside_path = tmp_path / "escape.txt"
    outside_path.write_text("escape")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )

    with pytest.raises(TaskArtifactValidationError, match="escapes workspace root"):
        register_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactRegisterInput(
                task_workspace_id=task_workspace_id,
                local_path=str(outside_path),
                media_type_hint=None,
            ),
        )


def test_normalize_and_chunk_artifact_text_are_deterministic() -> None:
    normalized = normalize_artifact_text("ab\r\ncd\ref")

    assert normalized == "ab\ncd\nef"
    assert chunk_normalized_artifact_text(normalized, chunk_size=4) == [
        (0, 4, "ab\nc"),
        (4, 8, "d\nef"),
    ]


def test_ingest_task_artifact_record_persists_deterministic_chunks(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text(("A" * 998) + "\r\n" + ("B" * 5) + "\rC")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )
    artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/spec.txt",
        media_type_hint="text/plain",
    )

    response = ingest_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
    )

    assert response == {
        "artifact": {
            "id": str(artifact["id"]),
            "task_id": str(task_id),
            "task_workspace_id": str(task_workspace_id),
            "status": "registered",
            "ingestion_status": "ingested",
            "relative_path": "docs/spec.txt",
            "media_type_hint": "text/plain",
            "created_at": "2026-03-13T10:00:00+00:00",
            "updated_at": "2026-03-13T10:30:00+00:00",
        },
        "summary": {
            "total_count": 2,
            "total_characters": 1006,
            "media_type": "text/plain",
            "chunking_rule": TASK_ARTIFACT_CHUNKING_RULE,
            "order": ["sequence_no_asc", "id_asc"],
        },
    }
    assert store.locked_artifact_ids == [artifact["id"]]
    assert store.list_task_artifact_chunks(artifact["id"]) == [
        {
            "id": store.artifact_chunks[0]["id"],
            "user_id": user_id,
            "task_artifact_id": artifact["id"],
            "sequence_no": 1,
            "char_start": 0,
            "char_end_exclusive": 1000,
            "text": ("A" * 998) + "\n" + "B",
            "created_at": datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
        },
        {
            "id": store.artifact_chunks[1]["id"],
            "user_id": user_id,
            "task_artifact_id": artifact["id"],
            "sequence_no": 2,
            "char_start": 1000,
            "char_end_exclusive": 1006,
            "text": "BBBB\nC",
            "created_at": datetime(2026, 3, 13, 10, 0, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 13, 10, 0, 1, tzinfo=UTC),
        },
    ]


def test_ingest_task_artifact_record_supports_markdown(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "notes" / "plan.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("# Plan\r\n\r\n- Ship ingestion\n- Keep scope narrow\r")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )
    artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="notes/plan.md",
        media_type_hint="text/markdown",
    )

    response = ingest_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
    )

    assert response["artifact"]["ingestion_status"] == "ingested"
    assert response["summary"] == {
        "total_count": 1,
        "total_characters": 45,
        "media_type": "text/markdown",
        "chunking_rule": TASK_ARTIFACT_CHUNKING_RULE,
        "order": ["sequence_no_asc", "id_asc"],
    }
    assert store.list_task_artifact_chunks(artifact["id"]) == [
        {
            "id": store.artifact_chunks[0]["id"],
            "user_id": user_id,
            "task_artifact_id": artifact["id"],
            "sequence_no": 1,
            "char_start": 0,
            "char_end_exclusive": 45,
            "text": "# Plan\n\n- Ship ingestion\n- Keep scope narrow\n",
            "created_at": datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
        }
    ]


def test_ingest_task_artifact_record_is_idempotent_for_already_ingested_artifact() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path="/tmp/alicebot/task-workspaces/user/task",
    )
    artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="ingested",
        relative_path="docs/spec.txt",
        media_type_hint="text/plain",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=artifact["id"],
        sequence_no=1,
        char_start=0,
        char_end_exclusive=4,
        text="spec",
    )

    response = ingest_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
    )

    assert response == {
        "artifact": {
            "id": str(artifact["id"]),
            "task_id": str(task_id),
            "task_workspace_id": str(task_workspace_id),
            "status": "registered",
            "ingestion_status": "ingested",
            "relative_path": "docs/spec.txt",
            "media_type_hint": "text/plain",
            "created_at": "2026-03-13T10:00:00+00:00",
            "updated_at": "2026-03-13T10:00:00+00:00",
        },
        "summary": {
            "total_count": 1,
            "total_characters": 4,
            "media_type": "text/plain",
            "chunking_rule": TASK_ARTIFACT_CHUNKING_RULE,
            "order": ["sequence_no_asc", "id_asc"],
        },
    }
    assert store.locked_artifact_ids == [artifact["id"]]
    assert len(store.artifact_chunks) == 1


def test_ingest_task_artifact_record_rejects_unsupported_media_type(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.pdf"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("not really a pdf")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )
    artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/spec.pdf",
        media_type_hint="application/pdf",
    )

    with pytest.raises(
        TaskArtifactValidationError,
        match="artifact docs/spec.pdf has unsupported media type application/pdf",
    ):
        ingest_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
        )


def test_ingest_task_artifact_record_rejects_invalid_utf8_content(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "broken.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"\xff\xfe\xfd")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )
    artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/broken.txt",
        media_type_hint="text/plain",
    )

    with pytest.raises(
        TaskArtifactValidationError,
        match="artifact docs/broken.txt is not valid UTF-8 text",
    ):
        ingest_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
        )


def test_ingest_task_artifact_record_rejects_paths_outside_workspace(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    outside_path = tmp_path / "escape.txt"
    outside_path.write_text("escape")
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path=str(workspace_path),
    )
    artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="../escape.txt",
        media_type_hint="text/plain",
    )

    with pytest.raises(TaskArtifactValidationError, match="escapes workspace root"):
        ingest_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
        )


def test_list_task_artifact_chunk_records_are_deterministic() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path="/tmp/alicebot/task-workspaces/user/task",
    )
    artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="ingested",
        relative_path="docs/spec.txt",
        media_type_hint="text/plain",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=artifact["id"],
        sequence_no=1,
        char_start=0,
        char_end_exclusive=4,
        text="spec",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=artifact["id"],
        sequence_no=2,
        char_start=4,
        char_end_exclusive=8,
        text="plan",
    )

    assert list_task_artifact_chunk_records(
        store,
        user_id=user_id,
        task_artifact_id=artifact["id"],
    ) == {
        "items": [
            {
                "id": str(store.artifact_chunks[0]["id"]),
                "task_artifact_id": str(artifact["id"]),
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 4,
                "text": "spec",
                "created_at": "2026-03-13T10:00:00+00:00",
                "updated_at": "2026-03-13T10:00:00+00:00",
            },
            {
                "id": str(store.artifact_chunks[1]["id"]),
                "task_artifact_id": str(artifact["id"]),
                "sequence_no": 2,
                "char_start": 4,
                "char_end_exclusive": 8,
                "text": "plan",
                "created_at": "2026-03-13T10:00:01+00:00",
                "updated_at": "2026-03-13T10:00:01+00:00",
            },
        ],
        "summary": {
            "total_count": 2,
            "total_characters": 8,
            "media_type": "text/plain",
            "chunking_rule": TASK_ARTIFACT_CHUNKING_RULE,
            "order": ["sequence_no_asc", "id_asc"],
        },
    }


def test_list_and_get_task_artifact_records_are_deterministic() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path="/tmp/alicebot/task-workspaces/user/task",
    )
    first = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/a.txt",
        media_type_hint="text/plain",
    )
    second = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="docs/b.txt",
        media_type_hint=None,
    )

    assert list_task_artifact_records(store, user_id=user_id) == {
        "items": [
            serialize_task_artifact_row(first),
            serialize_task_artifact_row(second),
        ],
        "summary": {
            "total_count": 2,
            "order": ["created_at_asc", "id_asc"],
        },
    }
    assert get_task_artifact_record(
        store,
        user_id=user_id,
        task_artifact_id=first["id"],
    ) == {"artifact": serialize_task_artifact_row(first)}


def test_get_task_artifact_record_raises_when_artifact_is_missing() -> None:
    with pytest.raises(TaskArtifactNotFoundError, match="was not found"):
        get_task_artifact_record(
            ArtifactStoreStub(),
            user_id=uuid4(),
            task_artifact_id=uuid4(),
        )
