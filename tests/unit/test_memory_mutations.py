from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from alicebot_api.contracts import MemoryOperationGenerateInput
from alicebot_api.memory_mutations import MemoryMutationValidationError, generate_memory_operation_candidates


class MemoryMutationStoreStub:
    def __init__(self) -> None:
        self.user_id = UUID("11111111-1111-4111-8111-111111111111")
        self.base_time = datetime(2026, 4, 14, 9, 0, tzinfo=UTC)
        self.objects: dict[UUID, dict[str, object]] = {}
        self.memory_operation_candidates: dict[UUID, dict[str, object]] = {}
        self.memory_operation_candidates_by_sync_source: dict[tuple[str, str], UUID] = {}

    def add_object(
        self,
        *,
        object_type: str,
        title: str,
        body: dict[str, object],
        provenance: dict[str, object],
        status: str = "active",
    ) -> dict[str, object]:
        object_id = uuid4()
        capture_event_id = uuid4()
        row = {
            "id": object_id,
            "user_id": self.user_id,
            "capture_event_id": capture_event_id,
            "object_type": object_type,
            "status": status,
            "is_preserved": True,
            "is_searchable": True,
            "is_promotable": True,
            "title": title,
            "body": body,
            "provenance": provenance,
            "confidence": 0.95,
            "last_confirmed_at": None,
            "supersedes_object_id": None,
            "superseded_by_object_id": None,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.objects[object_id] = row
        return row

    def list_continuity_recall_candidates(self):
        rows: list[dict[str, object]] = []
        for row in self.objects.values():
            rows.append(
                {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "capture_event_id": row["capture_event_id"],
                    "object_type": row["object_type"],
                    "status": row["status"],
                    "is_preserved": row["is_preserved"],
                    "is_searchable": row["is_searchable"],
                    "is_promotable": row["is_promotable"],
                    "title": row["title"],
                    "body": row["body"],
                    "provenance": row["provenance"],
                    "confidence": row["confidence"],
                    "last_confirmed_at": row["last_confirmed_at"],
                    "supersedes_object_id": row["supersedes_object_id"],
                    "superseded_by_object_id": row["superseded_by_object_id"],
                    "object_created_at": row["created_at"],
                    "object_updated_at": row["updated_at"],
                    "admission_posture": "DERIVED",
                    "admission_reason": "seed",
                    "explicit_signal": None,
                    "capture_created_at": row["created_at"],
                }
            )
        return rows

    def get_continuity_object_optional(self, continuity_object_id: UUID):
        row = self.objects.get(continuity_object_id)
        return None if row is None else dict(row)

    def get_memory_operation_candidate_by_sync_source_optional(
        self,
        *,
        sync_fingerprint: str,
        source_candidate_id: str,
    ):
        candidate_id = self.memory_operation_candidates_by_sync_source.get((sync_fingerprint, source_candidate_id))
        if candidate_id is None:
            return None
        return dict(self.memory_operation_candidates[candidate_id])

    def create_memory_operation_candidate(
        self,
        *,
        sync_fingerprint: str,
        source_kind: str,
        source_candidate_id: str,
        source_candidate_type: str,
        candidate_payload,
        source_scope,
        operation_type: str,
        operation_reason: str,
        policy_action: str,
        policy_reason: str,
        target_continuity_object_id: UUID | None,
        target_snapshot,
    ):
        candidate_id = uuid4()
        row = {
            "id": candidate_id,
            "user_id": self.user_id,
            "sync_fingerprint": sync_fingerprint,
            "source_kind": source_kind,
            "source_candidate_id": source_candidate_id,
            "source_candidate_type": source_candidate_type,
            "candidate_payload": candidate_payload,
            "source_scope": source_scope,
            "operation_type": operation_type,
            "operation_reason": operation_reason,
            "policy_action": policy_action,
            "policy_reason": policy_reason,
            "target_continuity_object_id": target_continuity_object_id,
            "target_snapshot": target_snapshot,
            "applied_operation_id": None,
            "created_at": self.base_time,
            "applied_at": None,
        }
        self.memory_operation_candidates[candidate_id] = row
        self.memory_operation_candidates_by_sync_source[(sync_fingerprint, source_candidate_id)] = candidate_id
        return dict(row)


def test_generate_memory_operation_candidates_routes_explicit_correction_to_supersede() -> None:
    store = MemoryMutationStoreStub()
    current = store.add_object(
        object_type="MemoryFact",
        title="Memory Fact: deployment mode is manual",
        body={"fact_text": "deployment mode is manual"},
        provenance={"thread_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"},
    )

    payload = generate_memory_operation_candidates(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=MemoryOperationGenerateInput(
            user_content="Correction: deployment mode is assist",
            assistant_content="",
            mode="assist",
            sync_fingerprint="mutation-sync-001",
            thread_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ),
    )

    assert payload["summary"] == {
        "candidate_count": 1,
        "auto_apply_count": 1,
        "review_required_count": 0,
        "noop_count": 0,
        "operation_types": ["SUPERSEDE"],
    }
    item = payload["items"][0]
    assert item["operation_type"] == "SUPERSEDE"
    assert item["policy_action"] == "auto_apply"
    assert item["target_continuity_object_id"] == str(current["id"])


def test_generate_memory_operation_candidates_routes_low_confidence_turns_to_review() -> None:
    store = MemoryMutationStoreStub()

    payload = generate_memory_operation_candidates(
        store,  # type: ignore[arg-type]
        user_id=store.user_id,
        request=MemoryOperationGenerateInput(
            user_content="We are waiting for the design review",
            assistant_content="",
            mode="assist",
            sync_fingerprint="mutation-sync-002",
            thread_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ),
    )

    assert payload["summary"]["candidate_count"] == 1
    assert payload["items"][0]["operation_type"] == "ADD"
    assert payload["items"][0]["policy_action"] == "review_required"
    assert payload["items"][0]["policy_reason"] == "low_confidence_requires_review"


def test_generate_memory_operation_candidates_rejects_unknown_mode() -> None:
    store = MemoryMutationStoreStub()

    try:
        generate_memory_operation_candidates(
            store,  # type: ignore[arg-type]
            user_id=store.user_id,
            request=MemoryOperationGenerateInput(
                user_content="Decision: Keep the review short",
                assistant_content="",
                mode="banana",
                sync_fingerprint="mutation-sync-003",
            ),
        )
    except MemoryMutationValidationError as exc:
        assert str(exc) == "mode must be one of: manual, assist, auto"
    else:
        raise AssertionError("expected MemoryMutationValidationError")
