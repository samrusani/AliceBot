from __future__ import annotations

from pathlib import Path
from uuid import UUID

from alicebot_api.importer_models import (
    ImporterNormalizedBatch,
    ImporterNormalizedItem,
    ImporterWorkspaceContext,
)
from alicebot_api.importers.common import ImportPersistenceConfig, import_normalized_batch
from alicebot_api.openclaw_adapter import load_openclaw_payload
from alicebot_api.store import ContinuityStore, JsonObject


_OPENCLAW_DEDUPE_POSTURE = "workspace_and_payload_fingerprint"


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
        ),
    )


__all__ = ["import_openclaw_source"]
