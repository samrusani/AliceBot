from __future__ import annotations

from pathlib import Path
from uuid import UUID

from alicebot_api.openclaw_adapter import load_openclaw_payload
from alicebot_api.store import ContinuityStore, JsonObject


_OBJECT_TYPE_TO_SIGNAL: dict[str, str] = {
    "Decision": "decision",
    "NextAction": "next_action",
    "Commitment": "commitment",
    "WaitingFor": "waiting_for",
    "Blocker": "blocker",
    "MemoryFact": "remember_this",
    "Note": "note",
}


def _existing_openclaw_dedupe_keys(store: ContinuityStore) -> set[str]:
    dedupe_keys: set[str] = set()
    for row in store.list_continuity_recall_candidates():
        provenance = row["provenance"]
        if not isinstance(provenance, dict):
            continue
        if provenance.get("source_kind") != "openclaw_import":
            continue
        dedupe_key = provenance.get("openclaw_dedupe_key")
        if isinstance(dedupe_key, str) and dedupe_key.strip() != "":
            dedupe_keys.add(dedupe_key)
    return dedupe_keys


def _deterministic_source_event_id(*, workspace_id: str, source_item_id: str) -> str:
    return f"openclaw:{workspace_id}:{source_item_id}"


def import_openclaw_source(
    store: ContinuityStore,
    *,
    user_id: UUID,
    source: str | Path,
) -> JsonObject:
    del user_id

    batch = load_openclaw_payload(source)
    existing_dedupe_keys = _existing_openclaw_dedupe_keys(store)
    run_dedupe_keys: set[str] = set()

    imported_object_ids: list[str] = []
    imported_capture_ids: list[str] = []
    skipped_duplicates = 0

    for item in batch.items:
        if item.dedupe_key in existing_dedupe_keys or item.dedupe_key in run_dedupe_keys:
            skipped_duplicates += 1
            continue

        run_dedupe_keys.add(item.dedupe_key)

        capture = store.create_continuity_capture_event(
            raw_content=item.raw_content,
            explicit_signal=_OBJECT_TYPE_TO_SIGNAL[item.object_type],
            admission_posture="DERIVED",
            admission_reason="openclaw_import",
        )

        source_event_ids = item.source_provenance.get("source_event_ids")
        if not isinstance(source_event_ids, list) or len(source_event_ids) == 0:
            source_event_ids = [
                _deterministic_source_event_id(
                    workspace_id=batch.context.workspace_id,
                    source_item_id=item.source_item_id,
                )
            ]

        provenance: JsonObject = {
            **item.source_provenance,
            "source_event_ids": source_event_ids,
            "source_kind": "openclaw_import",
            "openclaw_workspace_id": batch.context.workspace_id,
            "openclaw_workspace_name": batch.context.workspace_name,
            "openclaw_fixture_id": batch.context.fixture_id,
            "openclaw_source_path": batch.context.source_path,
            "openclaw_source_file": item.source_file,
            "openclaw_source_item_id": item.source_item_id,
            "openclaw_dedupe_key": item.dedupe_key,
            "openclaw_dedupe_posture": "workspace_and_payload_fingerprint",
        }

        continuity_object = store.create_continuity_object(
            capture_event_id=capture["id"],
            object_type=item.object_type,
            status=item.status,
            title=item.title,
            body=item.body,
            provenance=provenance,
            confidence=item.confidence,
        )

        imported_capture_ids.append(str(capture["id"]))
        imported_object_ids.append(str(continuity_object["id"]))

    imported_count = len(imported_object_ids)
    status = "ok" if imported_count > 0 else "noop"

    return {
        "status": status,
        "source_path": batch.context.source_path,
        "fixture_id": batch.context.fixture_id,
        "workspace_id": batch.context.workspace_id,
        "workspace_name": batch.context.workspace_name,
        "total_candidates": len(batch.items),
        "imported_count": imported_count,
        "skipped_duplicates": skipped_duplicates,
        "dedupe_posture": "workspace_and_payload_fingerprint",
        "provenance_source_kind": "openclaw_import",
        "imported_capture_event_ids": imported_capture_ids,
        "imported_object_ids": imported_object_ids,
    }


__all__ = ["import_openclaw_source"]
