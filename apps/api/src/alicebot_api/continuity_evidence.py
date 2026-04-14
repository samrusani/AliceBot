from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from psycopg.conninfo import make_conninfo

from alicebot_api.continuity_contradictions import sync_contradiction_state_for_objects
from alicebot_api.continuity_explainability import build_continuity_item_explanation
from alicebot_api.continuity_objects import serialize_continuity_lifecycle_state_from_record
from alicebot_api.contracts import (
    ContinuityArtifactDetailRecord,
    ContinuityArtifactDetailResponse,
    ContinuityEvidenceArtifactCopyRecord,
    ContinuityEvidenceArtifactRecord,
    ContinuityEvidenceArtifactSegmentRecord,
    ContinuityEvidenceLinkRecord,
    ContinuityExplainRecord,
    ContinuityExplainResponse,
    ContinuityReviewObjectRecord,
    isoformat_or_none,
)
from alicebot_api.db import user_connection
from alicebot_api.store import (
    ContinuityArtifactCopyRow,
    ContinuityArtifactRow,
    ContinuityArtifactSegmentRow,
    ContinuityObjectEvidenceRow,
    ContinuityObjectRow,
    ContinuityStore,
    JsonObject,
)


class ContinuityEvidenceNotFoundError(LookupError):
    """Raised when a continuity evidence resource is not visible in scope."""


_REDACTED_EVIDENCE_CONTENT = "[redacted]"


@dataclass(frozen=True, slots=True)
class SourceArtifactArchiveInput:
    relative_path: str
    display_name: str
    media_type: str
    content_text: str


@dataclass(frozen=True, slots=True)
class ArchivedArtifactRef:
    artifact_id: UUID
    artifact_copy_id: UUID
    relative_path: str
    checksum_sha256: str


def _checksum_sha256(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def archive_import_source_files(
    store: ContinuityStore,
    *,
    user_id: UUID,
    source_kind: str,
    import_source_path: str,
    files: list[SourceArtifactArchiveInput],
) -> dict[str, ArchivedArtifactRef]:
    if not files:
        return {}

    archived: dict[str, ArchivedArtifactRef] = {}
    info = store.conn.info
    archive_database_url = make_conninfo(
        "",
        dbname=info.dbname,
        user=info.user,
        password=info.password,
        host=info.host,
        port=str(info.port),
    )

    with user_connection(archive_database_url, user_id) as archive_conn:
        archive_store = ContinuityStore(archive_conn)
        for file in files:
            artifact = archive_store.upsert_continuity_artifact(
                source_kind=source_kind,
                import_source_path=import_source_path,
                relative_path=file.relative_path,
                display_name=file.display_name,
                media_type=file.media_type,
            )
            checksum = _checksum_sha256(file.content_text)
            artifact_copy = archive_store.upsert_continuity_artifact_copy(
                artifact_id=artifact["id"],
                checksum_sha256=checksum,
                content_text=file.content_text,
                content_length_bytes=len(file.content_text.encode("utf-8")),
                content_encoding="utf-8",
            )
            archived[file.relative_path] = ArchivedArtifactRef(
                artifact_id=artifact["id"],
                artifact_copy_id=artifact_copy["id"],
                relative_path=file.relative_path,
                checksum_sha256=checksum,
            )
    return archived


def checksum_sha256_for_text(value: str) -> str:
    return _checksum_sha256(value)


def _serialize_review_object(record: ContinuityObjectRow) -> ContinuityReviewObjectRecord:
    return {
        "id": str(record["id"]),
        "capture_event_id": str(record["capture_event_id"]),
        "object_type": record["object_type"],
        "status": record["status"],
        "lifecycle": serialize_continuity_lifecycle_state_from_record(record),
        "title": record["title"],
        "body": record["body"],
        "provenance": record["provenance"],
        "confidence": float(record["confidence"]),
        "last_confirmed_at": isoformat_or_none(record["last_confirmed_at"]),
        "supersedes_object_id": (
            None if record["supersedes_object_id"] is None else str(record["supersedes_object_id"])
        ),
        "superseded_by_object_id": (
            None if record["superseded_by_object_id"] is None else str(record["superseded_by_object_id"])
        ),
        "created_at": record["created_at"].isoformat(),
        "updated_at": record["updated_at"].isoformat(),
    }


def _serialize_artifact(record: ContinuityArtifactRow) -> ContinuityEvidenceArtifactRecord:
    return {
        "id": str(record["id"]),
        "source_kind": record["source_kind"],
        "import_source_path": record["import_source_path"],
        "relative_path": record["relative_path"],
        "display_name": record["display_name"],
        "media_type": record["media_type"],
        "created_at": record["created_at"].isoformat(),
    }


def _serialize_artifact_copy(record: ContinuityArtifactCopyRow) -> ContinuityEvidenceArtifactCopyRecord:
    return {
        "id": str(record["id"]),
        "checksum_sha256": record["checksum_sha256"],
        "content_length_bytes": record["content_length_bytes"],
        "content_encoding": record["content_encoding"],
        "content_text": record["content_text"],
        "created_at": record["created_at"].isoformat(),
    }


def _serialize_artifact_segment(
    record: ContinuityArtifactSegmentRow,
) -> ContinuityEvidenceArtifactSegmentRecord:
    return {
        "id": str(record["id"]),
        "source_item_id": record["source_item_id"],
        "sequence_no": record["sequence_no"],
        "segment_kind": record["segment_kind"],
        "locator": record["locator"],
        "raw_content": record["raw_content"],
        "checksum_sha256": record["checksum_sha256"],
        "created_at": record["created_at"].isoformat(),
    }


def _sensitive_evidence_content(
    value: str,
    *,
    include_raw_content: bool,
) -> str:
    if include_raw_content:
        return value
    return _REDACTED_EVIDENCE_CONTENT


def serialize_continuity_evidence_rows(
    rows: list[ContinuityObjectEvidenceRow],
    *,
    include_raw_content: bool = True,
) -> list[ContinuityEvidenceLinkRecord]:
    serialized: list[ContinuityEvidenceLinkRecord] = []
    for row in rows:
        artifact: ContinuityEvidenceArtifactRecord = {
            "id": str(row["artifact_id"]),
            "source_kind": row["source_kind"],
            "import_source_path": row["import_source_path"],
            "relative_path": row["relative_path"],
            "display_name": row["display_name"],
            "media_type": row["media_type"],
            "created_at": row["artifact_created_at"].isoformat(),
        }
        artifact_copy: ContinuityEvidenceArtifactCopyRecord = {
            "id": str(row["artifact_copy_id"]),
            "checksum_sha256": row["artifact_copy_checksum_sha256"],
            "content_length_bytes": row["artifact_copy_content_length_bytes"],
            "content_encoding": row["artifact_copy_content_encoding"],
            "content_text": _sensitive_evidence_content(
                row["artifact_copy_content_text"],
                include_raw_content=include_raw_content,
            ),
            "created_at": row["artifact_copy_created_at"].isoformat(),
        }
        artifact_segment = None
        if row["artifact_segment_id"] is not None:
            artifact_segment = {
                "id": str(row["artifact_segment_id"]),
                "source_item_id": row["segment_source_item_id"] or "",
                "sequence_no": row["segment_sequence_no"] or 0,
                "segment_kind": row["segment_kind"] or "unknown",
                "locator": row["segment_locator"] or {},
                "raw_content": _sensitive_evidence_content(
                    row["segment_raw_content"] or "",
                    include_raw_content=include_raw_content,
                ),
                "checksum_sha256": row["segment_checksum_sha256"] or "",
                "created_at": (
                    row["segment_created_at"].isoformat()
                    if row["segment_created_at"] is not None
                    else ""
                ),
            }
        serialized.append(
            {
                "id": str(row["id"]),
                "relationship": row["relationship"],
                "created_at": row["created_at"].isoformat(),
                "artifact": artifact,
                "artifact_copy": artifact_copy,
                "artifact_segment": artifact_segment,
            }
        )
    return serialized


def build_continuity_explain(
    store: ContinuityStore,
    *,
    user_id: UUID,
    continuity_object_id: UUID,
    include_raw_content: bool = True,
) -> ContinuityExplainResponse:
    del user_id

    continuity_object = store.get_continuity_object_optional(continuity_object_id)
    if continuity_object is None:
        raise ContinuityEvidenceNotFoundError(
            f"continuity object {continuity_object_id} was not found"
        )
    sync_contradiction_state_for_objects(
        store,
        continuity_object_ids=[continuity_object["id"]],
    )
    continuity_object = store.get_continuity_object_optional(continuity_object_id)
    if continuity_object is None:
        raise ContinuityEvidenceNotFoundError(
            f"continuity object {continuity_object_id} was not found"
        )

    explain: ContinuityExplainRecord = {
        "continuity_object": _serialize_review_object(continuity_object),
        "explanation": build_continuity_item_explanation(
            store,
            continuity_object_id=continuity_object["id"],
            capture_event_id=continuity_object["capture_event_id"],
            title=continuity_object["title"],
            body=continuity_object["body"],
            provenance=continuity_object["provenance"],
            status=continuity_object["status"],
            confidence=float(continuity_object["confidence"]),
            last_confirmed_at=continuity_object["last_confirmed_at"],
            supersedes_object_id=continuity_object["supersedes_object_id"],
            superseded_by_object_id=continuity_object["superseded_by_object_id"],
            created_at=continuity_object["created_at"],
            updated_at=continuity_object["updated_at"],
        ),
        "evidence_chain": serialize_continuity_evidence_rows(
            store.list_continuity_object_evidence(continuity_object_id),
            include_raw_content=include_raw_content,
        ),
    }
    return {"explain": explain}


def get_continuity_artifact_detail(
    store: ContinuityStore,
    *,
    user_id: UUID,
    artifact_id: UUID,
    include_raw_content: bool = True,
) -> ContinuityArtifactDetailResponse:
    del user_id

    artifact = store.get_continuity_artifact_optional(artifact_id)
    if artifact is None:
        raise ContinuityEvidenceNotFoundError(f"continuity artifact {artifact_id} was not found")

    detail: ContinuityArtifactDetailRecord = {
        "artifact": _serialize_artifact(artifact),
        "copies": [
            {
                **_serialize_artifact_copy(copy),
                "content_text": _sensitive_evidence_content(
                    copy["content_text"],
                    include_raw_content=include_raw_content,
                ),
            }
            for copy in store.list_continuity_artifact_copies(artifact_id)
        ],
        "segments": [
            {
                **_serialize_artifact_segment(segment),
                "raw_content": _sensitive_evidence_content(
                    segment["raw_content"],
                    include_raw_content=include_raw_content,
                ),
            }
            for segment in store.list_continuity_artifact_segments(artifact_id)
        ],
    }
    return {"artifact_detail": detail}


__all__ = [
    "ArchivedArtifactRef",
    "ContinuityEvidenceNotFoundError",
    "SourceArtifactArchiveInput",
    "archive_import_source_files",
    "build_continuity_explain",
    "checksum_sha256_for_text",
    "get_continuity_artifact_detail",
    "serialize_continuity_evidence_rows",
]
