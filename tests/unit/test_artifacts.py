from __future__ import annotations

import io
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4
from xml.sax.saxutils import escape
import zipfile

import pytest

from alicebot_api.artifacts import (
    TASK_ARTIFACT_CHUNKING_RULE,
    TASK_ARTIFACT_CHUNK_RETRIEVAL_MATCHING_RULE,
    TaskArtifactAlreadyExistsError,
    TaskArtifactChunkRetrievalValidationError,
    TaskArtifactNotFoundError,
    TaskArtifactValidationError,
    build_workspace_relative_artifact_path,
    chunk_normalized_artifact_text,
    ensure_artifact_path_is_rooted,
    extract_unique_lexical_terms,
    get_task_artifact_record,
    ingest_task_artifact_record,
    list_task_artifact_chunk_records,
    list_task_artifact_records,
    match_artifact_chunk_text,
    normalize_artifact_text,
    register_task_artifact_record,
    retrieve_artifact_scoped_artifact_chunk_records,
    retrieve_task_scoped_artifact_chunk_records,
    serialize_task_artifact_row,
)
from alicebot_api.contracts import (
    ArtifactScopedArtifactChunkRetrievalInput,
    TaskArtifactIngestInput,
    TaskArtifactRegisterInput,
    TaskScopedArtifactChunkRetrievalInput,
)
from alicebot_api.tasks import TaskNotFoundError
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


def _escape_pdf_literal_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf_bytes(
    pages: list[list[str]],
    *,
    compress_streams: bool = True,
    textless: bool = False,
) -> bytes:
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    page_refs: list[str] = []
    next_object_id = 4
    for page_lines in pages:
        page_object_id = next_object_id
        content_object_id = next_object_id + 1
        next_object_id += 2
        page_refs.append(f"{page_object_id} 0 R")

        if textless:
            content_stream = b"q 10 10 100 100 re S Q\n"
        else:
            commands = [b"BT", b"/F1 12 Tf", b"72 720 Td"]
            for index, line in enumerate(page_lines):
                if index > 0:
                    commands.append(b"T*")
                commands.append(f"({_escape_pdf_literal_string(line)}) Tj".encode("latin-1"))
            commands.append(b"ET")
            content_stream = b"\n".join(commands) + b"\n"

        if compress_streams:
            encoded_stream = zlib.compress(content_stream)
            content_body = (
                f"<< /Length {len(encoded_stream)} /Filter /FlateDecode >>\n".encode("ascii")
                + b"stream\n"
                + encoded_stream
                + b"\nendstream"
            )
        else:
            content_body = (
                f"<< /Length {len(content_stream)} >>\n".encode("ascii")
                + b"stream\n"
                + content_stream
                + b"endstream"
            )

        objects[page_object_id] = (
            f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {content_object_id} 0 R >>"
        ).encode("ascii")
        objects[content_object_id] = content_body

    objects[2] = (
        f"<< /Type /Pages /Count {len(page_refs)} /Kids [{' '.join(page_refs)}] >>"
    ).encode("ascii")

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    max_object_id = max(objects)
    offsets = [0] * (max_object_id + 1)
    for object_id in range(1, max_object_id + 1):
        offsets[object_id] = len(document)
        document.extend(f"{object_id} 0 obj\n".encode("ascii"))
        document.extend(objects[object_id])
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {max_object_id + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for object_id in range(1, max_object_id + 1):
        document.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {max_object_id + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


def _build_docx_bytes(
    paragraphs: list[str],
    *,
    include_document_xml: bool = True,
    malformed_document_xml: bool = False,
) -> bytes:
    document_xml = (
        b"<w:document"
        if malformed_document_xml
        else (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            + "".join(
                (
                    "<w:p><w:r><w:t xml:space=\"preserve\">"
                    f"{escape(paragraph)}"
                    "</w:t></w:r></w:p>"
                )
                for paragraph in paragraphs
            )
            + (
                "<w:sectPr>"
                "<w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
                "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" "
                "w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
                "</w:sectPr>"
                "</w:body>"
                "</w:document>"
            )
        )
    )

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        entries = {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ).encode("utf-8"),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                "</Relationships>"
            ).encode("utf-8"),
        }
        if include_document_xml:
            entries["word/document.xml"] = document_xml

        for name, payload in entries.items():
            info = zipfile.ZipInfo(filename=name)
            info.date_time = (2026, 3, 13, 10, 0, 0)
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, payload)

    return archive_buffer.getvalue()


class ArtifactStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 13, 10, 0, tzinfo=UTC)
        self.tasks: list[dict[str, object]] = []
        self.workspaces: list[dict[str, object]] = []
        self.artifacts: list[dict[str, object]] = []
        self.artifact_chunks: list[dict[str, object]] = []
        self.locked_workspace_ids: list[UUID] = []
        self.locked_artifact_ids: list[UUID] = []

    def create_task(self, *, task_id: UUID, user_id: UUID) -> dict[str, object]:
        task = {
            "id": task_id,
            "user_id": user_id,
            "thread_id": uuid4(),
            "tool_id": uuid4(),
            "status": "approved",
            "request": {},
            "tool": {},
            "latest_approval_id": None,
            "latest_execution_id": None,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.tasks.append(task)
        return task

    def get_task_optional(self, task_id: UUID) -> dict[str, object] | None:
        return next((task for task in self.tasks if task["id"] == task_id), None)

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

    def list_task_artifacts_for_task(self, task_id: UUID) -> list[dict[str, object]]:
        return sorted(
            (artifact for artifact in self.artifacts if artifact["task_id"] == task_id),
            key=lambda artifact: (artifact["created_at"], artifact["id"]),
        )

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


def test_ingest_task_artifact_record_persists_deterministic_pdf_chunks(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.pdf"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(_build_pdf_bytes([["A" * 998, "B" * 5, "C"]]))
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
            "relative_path": "docs/spec.pdf",
            "media_type_hint": "application/pdf",
            "created_at": "2026-03-13T10:00:00+00:00",
            "updated_at": "2026-03-13T10:30:00+00:00",
        },
        "summary": {
            "total_count": 2,
            "total_characters": 1006,
            "media_type": "application/pdf",
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


def test_ingest_task_artifact_record_persists_deterministic_docx_chunks(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "spec.docx"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(_build_docx_bytes(["A" * 998, "B" * 5, "C"]))
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
        relative_path="docs/spec.docx",
        media_type_hint="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
            "relative_path": "docs/spec.docx",
            "media_type_hint": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "created_at": "2026-03-13T10:00:00+00:00",
            "updated_at": "2026-03-13T10:30:00+00:00",
        },
        "summary": {
            "total_count": 2,
            "total_characters": 1006,
            "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
    artifact_path = workspace_path / "docs" / "spec.bin"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"\x00\x01\x02")
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
        relative_path="docs/spec.bin",
        media_type_hint="application/octet-stream",
    )

    with pytest.raises(
        TaskArtifactValidationError,
        match=(
            "artifact docs/spec.bin has unsupported media type application/octet-stream; "
            "supported types: text/plain, text/markdown, application/pdf, "
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    ):
        ingest_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
        )


def test_ingest_task_artifact_record_rejects_textless_pdf(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "scanned.pdf"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(_build_pdf_bytes([[]], textless=True))
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
        relative_path="docs/scanned.pdf",
        media_type_hint="application/pdf",
    )

    with pytest.raises(
        TaskArtifactValidationError,
        match="artifact docs/scanned.pdf does not contain extractable PDF text",
    ):
        ingest_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
        )


def test_ingest_task_artifact_record_rejects_textless_docx(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "empty.docx"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(_build_docx_bytes(["", ""]))
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
        relative_path="docs/empty.docx",
        media_type_hint="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    with pytest.raises(
        TaskArtifactValidationError,
        match="artifact docs/empty.docx does not contain extractable DOCX text",
    ):
        ingest_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
        )


def test_ingest_task_artifact_record_rejects_malformed_docx(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    artifact_path = workspace_path / "docs" / "broken.docx"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(_build_docx_bytes(["broken"], malformed_document_xml=True))
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
        relative_path="docs/broken.docx",
        media_type_hint="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    with pytest.raises(
        TaskArtifactValidationError,
        match="artifact docs/broken.docx is not a valid DOCX",
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
    outside_path = tmp_path / "escape.pdf"
    outside_path.write_bytes(_build_pdf_bytes([["escape"]]))
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
        relative_path="../escape.pdf",
        media_type_hint="application/pdf",
    )

    with pytest.raises(TaskArtifactValidationError, match="escapes workspace root"):
        ingest_task_artifact_record(
            store,
            user_id=user_id,
            request=TaskArtifactIngestInput(task_artifact_id=artifact["id"]),
        )


def test_ingest_task_artifact_record_rejects_docx_paths_outside_workspace(tmp_path) -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    workspace_path = tmp_path / "workspaces" / str(user_id) / str(task_id)
    workspace_path.mkdir(parents=True)
    outside_path = tmp_path / "escape.docx"
    outside_path.write_bytes(_build_docx_bytes(["escape"]))
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
        relative_path="../escape.docx",
        media_type_hint="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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


def test_extract_unique_lexical_terms_preserves_first_occurrence_order() -> None:
    assert extract_unique_lexical_terms("Alpha beta, alpha\nbeta gamma") == [
        "alpha",
        "beta",
        "gamma",
    ]


def test_match_artifact_chunk_text_returns_explicit_metadata() -> None:
    assert match_artifact_chunk_text(
        query_terms=["alpha", "beta", "delta"],
        chunk_text="beta alpha release",
    ) == {
        "matched_query_terms": ["alpha", "beta"],
        "matched_query_term_count": 2,
        "first_match_char_start": 0,
    }


def test_task_scoped_chunk_retrieval_orders_matches_deterministically_and_skips_pending() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task(task_id=task_id, user_id=user_id)
    store.create_task_workspace(
        task_workspace_id=task_workspace_id,
        task_id=task_id,
        user_id=user_id,
        local_path="/tmp/alicebot/task-workspaces/user/task",
    )
    docs_artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="ingested",
        relative_path="docs/a.txt",
        media_type_hint="text/plain",
    )
    notes_artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="ingested",
        relative_path="notes/b.md",
        media_type_hint="text/markdown",
    )
    pending_artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="pending",
        relative_path="notes/hidden.txt",
        media_type_hint="text/plain",
    )
    weak_match_artifact = store.create_task_artifact(
        task_id=task_id,
        task_workspace_id=task_workspace_id,
        status="registered",
        ingestion_status="ingested",
        relative_path="notes/c.txt",
        media_type_hint="text/plain",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=docs_artifact["id"],
        sequence_no=1,
        char_start=0,
        char_end_exclusive=14,
        text="beta alpha doc",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=notes_artifact["id"],
        sequence_no=1,
        char_start=0,
        char_end_exclusive=15,
        text="alpha beta note",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=pending_artifact["id"],
        sequence_no=1,
        char_start=0,
        char_end_exclusive=17,
        text="alpha beta hidden",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=weak_match_artifact["id"],
        sequence_no=1,
        char_start=0,
        char_end_exclusive=9,
        text="beta only",
    )

    assert retrieve_task_scoped_artifact_chunk_records(
        store,
        user_id=user_id,
        request=TaskScopedArtifactChunkRetrievalInput(
            task_id=task_id,
            query="Alpha beta",
        ),
    ) == {
        "items": [
            {
                "id": str(store.artifact_chunks[0]["id"]),
                "task_id": str(task_id),
                "task_artifact_id": str(docs_artifact["id"]),
                "relative_path": "docs/a.txt",
                "media_type": "text/plain",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 14,
                "text": "beta alpha doc",
                "match": {
                    "matched_query_terms": ["alpha", "beta"],
                    "matched_query_term_count": 2,
                    "first_match_char_start": 0,
                },
            },
            {
                "id": str(store.artifact_chunks[1]["id"]),
                "task_id": str(task_id),
                "task_artifact_id": str(notes_artifact["id"]),
                "relative_path": "notes/b.md",
                "media_type": "text/markdown",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 15,
                "text": "alpha beta note",
                "match": {
                    "matched_query_terms": ["alpha", "beta"],
                    "matched_query_term_count": 2,
                    "first_match_char_start": 0,
                },
            },
            {
                "id": str(store.artifact_chunks[3]["id"]),
                "task_id": str(task_id),
                "task_artifact_id": str(weak_match_artifact["id"]),
                "relative_path": "notes/c.txt",
                "media_type": "text/plain",
                "sequence_no": 1,
                "char_start": 0,
                "char_end_exclusive": 9,
                "text": "beta only",
                "match": {
                    "matched_query_terms": ["beta"],
                    "matched_query_term_count": 1,
                    "first_match_char_start": 0,
                },
            },
        ],
        "summary": {
            "total_count": 3,
            "searched_artifact_count": 3,
            "query": "Alpha beta",
            "query_terms": ["alpha", "beta"],
            "matching_rule": TASK_ARTIFACT_CHUNK_RETRIEVAL_MATCHING_RULE,
            "order": [
                "matched_query_term_count_desc",
                "first_match_char_start_asc",
                "relative_path_asc",
                "sequence_no_asc",
                "id_asc",
            ],
            "scope": {
                "kind": "task",
                "task_id": str(task_id),
            },
        },
    }


def test_artifact_scoped_chunk_retrieval_returns_empty_for_non_ingested_artifact() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task(task_id=task_id, user_id=user_id)
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
        ingestion_status="pending",
        relative_path="docs/spec.txt",
        media_type_hint="text/plain",
    )
    store.create_task_artifact_chunk(
        task_artifact_id=artifact["id"],
        sequence_no=1,
        char_start=0,
        char_end_exclusive=10,
        text="alpha beta",
    )

    assert retrieve_artifact_scoped_artifact_chunk_records(
        store,
        user_id=user_id,
        request=ArtifactScopedArtifactChunkRetrievalInput(
            task_artifact_id=artifact["id"],
            query="alpha",
        ),
    ) == {
        "items": [],
        "summary": {
            "total_count": 0,
            "searched_artifact_count": 0,
            "query": "alpha",
            "query_terms": ["alpha"],
            "matching_rule": TASK_ARTIFACT_CHUNK_RETRIEVAL_MATCHING_RULE,
            "order": [
                "matched_query_term_count_desc",
                "first_match_char_start_asc",
                "relative_path_asc",
                "sequence_no_asc",
                "id_asc",
            ],
            "scope": {
                "kind": "artifact",
                "task_id": str(task_id),
                "task_artifact_id": str(artifact["id"]),
            },
        },
    }


def test_task_scoped_chunk_retrieval_returns_empty_when_no_chunks_match() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task(task_id=task_id, user_id=user_id)
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
        char_end_exclusive=11,
        text="release plan",
    )

    response = retrieve_task_scoped_artifact_chunk_records(
        store,
        user_id=user_id,
        request=TaskScopedArtifactChunkRetrievalInput(
            task_id=task_id,
            query="alpha",
        ),
    )

    assert response == {
        "items": [],
        "summary": {
            "total_count": 0,
            "searched_artifact_count": 1,
            "query": "alpha",
            "query_terms": ["alpha"],
            "matching_rule": TASK_ARTIFACT_CHUNK_RETRIEVAL_MATCHING_RULE,
            "order": [
                "matched_query_term_count_desc",
                "first_match_char_start_asc",
                "relative_path_asc",
                "sequence_no_asc",
                "id_asc",
            ],
            "scope": {
                "kind": "task",
                "task_id": str(task_id),
            },
        },
    }


def test_task_scoped_chunk_retrieval_raises_when_task_is_missing() -> None:
    with pytest.raises(TaskNotFoundError, match="was not found"):
        retrieve_task_scoped_artifact_chunk_records(
            ArtifactStoreStub(),
            user_id=uuid4(),
            request=TaskScopedArtifactChunkRetrievalInput(
                task_id=uuid4(),
                query="alpha",
            ),
        )


def test_artifact_chunk_retrieval_rejects_query_without_words() -> None:
    store = ArtifactStoreStub()
    user_id = uuid4()
    task_id = uuid4()
    task_workspace_id = uuid4()
    store.create_task(task_id=task_id, user_id=user_id)
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

    with pytest.raises(
        TaskArtifactChunkRetrievalValidationError,
        match="must include at least one word",
    ):
        retrieve_artifact_scoped_artifact_chunk_records(
            store,
            user_id=user_id,
            request=ArtifactScopedArtifactChunkRetrievalInput(
                task_artifact_id=artifact["id"],
                query="   ...   ",
            ),
        )


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
