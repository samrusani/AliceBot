from __future__ import annotations

from uuid import UUID

from alicebot_api.continuity_contradictions import sync_contradiction_state_for_objects
from alicebot_api.contracts import (
    TRUST_SIGNAL_LIST_ORDER,
    TrustSignalListQueryInput,
    TrustSignalListResponse,
    TrustSignalListSummary,
    TrustSignalRecord,
)
from alicebot_api.store import ContinuityStore, TrustSignalRow


def _serialize_signal(row: TrustSignalRow) -> TrustSignalRecord:
    return {
        "id": str(row["id"]),
        "continuity_object_id": str(row["continuity_object_id"]),
        "signal_key": row["signal_key"],
        "signal_type": row["signal_type"],  # type: ignore[typeddict-item]
        "signal_state": row["signal_state"],  # type: ignore[typeddict-item]
        "direction": row["direction"],  # type: ignore[typeddict-item]
        "magnitude": float(row["magnitude"]),
        "reason": row["reason"],
        "contradiction_case_id": (
            None if row["contradiction_case_id"] is None else str(row["contradiction_case_id"])
        ),
        "related_continuity_object_id": (
            None
            if row["related_continuity_object_id"] is None
            else str(row["related_continuity_object_id"])
        ),
        "payload": row["payload"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def list_trust_signals(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TrustSignalListQueryInput,
    sync_first: bool = True,
) -> TrustSignalListResponse:
    del user_id
    if sync_first:
        sync_contradiction_state_for_objects(
            store,
            continuity_object_ids=(
                None if request.continuity_object_id is None else [request.continuity_object_id]
            ),
        )

    rows = store.list_trust_signals(
        limit=request.limit,
        continuity_object_id=request.continuity_object_id,
        signal_state=request.signal_state,
        signal_type=request.signal_type,
    )
    total_count = store.count_trust_signals(
        continuity_object_id=request.continuity_object_id,
        signal_state=request.signal_state,
        signal_type=request.signal_type,
    )
    summary: TrustSignalListSummary = {
        "continuity_object_id": (
            None if request.continuity_object_id is None else str(request.continuity_object_id)
        ),
        "signal_state": request.signal_state,
        "signal_type": request.signal_type,
        "limit": request.limit,
        "returned_count": len(rows),
        "total_count": total_count,
        "order": list(TRUST_SIGNAL_LIST_ORDER),
    }
    return {
        "items": [_serialize_signal(row) for row in rows],
        "summary": summary,
    }


__all__ = [
    "list_trust_signals",
]
