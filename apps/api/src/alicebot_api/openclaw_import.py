from __future__ import annotations

from pathlib import Path
from uuid import UUID

from alicebot_api.continuity_evidence import SourceArtifactArchiveInput, archive_import_source_files
from alicebot_api.importer_models import (
    ImporterNormalizedBatch,
    ImporterNormalizedItem,
    ImporterWorkspaceContext,
)
from alicebot_api.importers.common import ImportPersistenceConfig, import_normalized_batch
from alicebot_api.openclaw_adapter import list_openclaw_source_files, load_openclaw_payload
from alicebot_api.store import ContinuityStore, JsonObject


_OPENCLAW_DEDUPE_POSTURE = "workspace_and_payload_fingerprint"


def _relative_source_file(source_root: Path, file_path: Path) -> str:
    if source_root.is_dir():
        return str(file_path.relative_to(source_root))
    return file_path.name


def _to_generic_batch(source: str | Path) -> ImporterNormalizedBatch:
    batch = load_openclaw_payload(source)
    return ImporterNormalizedBatch(
        context=ImporterWorkspaceContext(
            fixture_id=batch.context.fixture_id,
            workspace_id=batch.context.workspace_id,
            workspace_name=batch.context.workspace_name,
            source_path=batch.context.source_path,
        ),
        items=[
            ImporterNormalizedItem(
                source_item_id=item.source_item_id,
                source_file=item.source_file,
                source_locator=item.source_locator,
                source_segment_text=item.source_segment_text,
                source_segment_kind=item.source_segment_kind,
                object_type=item.object_type,
                status=item.status,
                raw_content=item.raw_content,
                title=item.title,
                body=item.body,
                confidence=item.confidence,
                source_provenance=item.source_provenance,
                dedupe_key=item.dedupe_key,
            )
            for item in batch.items
        ],
    )


def import_openclaw_source(
    store: ContinuityStore,
    *,
    user_id: UUID,
    source: str | Path,
) -> JsonObject:
    source_path, source_files = list_openclaw_source_files(source)
    archived_artifacts = archive_import_source_files(
        store,
        user_id=user_id,
        source_kind="openclaw_import",
        import_source_path=str(source_path),
        files=[
            SourceArtifactArchiveInput(
                relative_path=_relative_source_file(source_path, file_path),
                display_name=file_path.name,
                media_type="application/json",
                content_text=file_path.read_text(encoding="utf-8"),
            )
            for file_path in source_files
        ],
    )
    generic_batch = _to_generic_batch(source)
    return import_normalized_batch(
        store,
        user_id=user_id,
        batch=generic_batch,
        config=ImportPersistenceConfig(
            source_kind="openclaw_import",
            source_prefix="openclaw",
            admission_reason="openclaw_import",
            dedupe_key_field="openclaw_dedupe_key",
            dedupe_posture=_OPENCLAW_DEDUPE_POSTURE,
            source_label="OpenClaw",
        ),
        archived_artifacts=archived_artifacts,
    )


__all__ = ["import_openclaw_source"]
