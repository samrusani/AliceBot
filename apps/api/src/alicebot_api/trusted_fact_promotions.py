from __future__ import annotations

from collections import defaultdict
import json
from typing import cast
from uuid import NAMESPACE_URL, UUID, uuid5

from alicebot_api.contracts import (
    TRUSTED_FACT_PATTERN_ORDER,
    TRUSTED_FACT_PLAYBOOK_ORDER,
    TemporalTrustRecord,
    TrustedFactEvidenceLinkRecord,
    TrustedFactPatternExplainResponse,
    TrustedFactPatternListQueryInput,
    TrustedFactPatternListResponse,
    TrustedFactPatternRecord,
    TrustedFactPlaybookExplainResponse,
    TrustedFactPlaybookListQueryInput,
    TrustedFactPlaybookListResponse,
    TrustedFactPlaybookRecord,
    TrustedFactPlaybookStepRecord,
    isoformat_or_none,
)
from alicebot_api.store import (
    ContinuityStore,
    FactPatternRow,
    FactPlaybookRow,
    MemoryRevisionRow,
    MemoryRow,
)

_TRUSTED_PATTERN_CLASSES = frozenset({"deterministic", "llm_corroborated", "human_curated"})
_ACTION_TYPE_BY_MEMORY_TYPE = {
    "preference": "prefer",
    "working_style": "work_with",
    "constraint": "constrain",
    "routine": "repeat",
    "commitment": "follow_through",
    "decision": "apply_decision",
    "project_fact": "apply_project_fact",
    "identity_fact": "respect_identity",
    "relationship_fact": "respect_relationship",
}


class TrustedFactPromotionNotFoundError(LookupError):
    """Raised when a trusted-fact promotion record is not visible in scope."""


def _fact_is_single_source_model_output(memory: MemoryRow) -> bool:
    extracted_by_model = memory.get("extracted_by_model")
    if extracted_by_model is None or extracted_by_model == "":
        return False
    return (memory.get("independent_source_count") or 0) <= 1


def _is_promotable_trusted_fact(memory: MemoryRow) -> bool:
    if memory["status"] != "active":
        return False
    if memory["promotion_eligibility"] != "promotable":
        return False
    if memory["trust_class"] not in _TRUSTED_PATTERN_CLASSES:
        return False
    # Guardrail: single-source model output cannot become a durable pattern on its own.
    if _fact_is_single_source_model_output(memory):
        return False
    return True


def _namespace_key(memory_key: str) -> str:
    segments = [segment for segment in memory_key.split(".") if segment]
    if len(segments) <= 1:
        return memory_key
    return ".".join(segments[:-1])


def _stable_id(user_id: UUID, kind: str, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"alicebot://{user_id}/{kind}/{key}")


def _json_inline(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _trust_record(memory: MemoryRow) -> TemporalTrustRecord:
    return {
        "trust_class": memory["trust_class"],
        "trust_reason": memory["trust_reason"],
        "confirmation_status": memory["confirmation_status"],
        "confidence": memory["confidence"],
    }


def _latest_revision(memory: MemoryRow, revisions: list[MemoryRevisionRow]) -> MemoryRevisionRow | None:
    if revisions:
        return revisions[-1]
    return None


def _evidence_link(memory: MemoryRow, latest_revision: MemoryRevisionRow | None) -> TrustedFactEvidenceLinkRecord:
    return {
        "fact_id": str(memory["id"]),
        "memory_key": memory["memory_key"],
        "memory_type": memory["memory_type"],
        "value": memory["value"],
        "trust": _trust_record(memory),
        "promotion_eligibility": memory["promotion_eligibility"],
        "evidence_count": memory["evidence_count"],
        "independent_source_count": memory["independent_source_count"],
        "extracted_by_model": memory["extracted_by_model"],
        "source_event_ids": list(memory["source_event_ids"]),
        "revision_sequence_no": None if latest_revision is None else latest_revision["sequence_no"],
        "revision_action": None if latest_revision is None else latest_revision["action"],
        "revision_created_at": (
            None if latest_revision is None else isoformat_or_none(latest_revision["created_at"])
        ),
    }


def _pattern_title(memory_type: str, namespace_key: str) -> str:
    return f"{memory_type.replace('_', ' ')} pattern: {namespace_key}"


def _pattern_explanation(memory_type: str, namespace_key: str, fact_count: int) -> str:
    return (
        f"Derived from {fact_count} active promotable trusted facts sharing memory type "
        f"{memory_type} and namespace {namespace_key}. Evidence links show the source fact IDs, "
        "source events, and current fact revisions."
    )


def _playbook_instruction(memory: MemoryRow) -> str:
    action_type = _ACTION_TYPE_BY_MEMORY_TYPE.get(memory["memory_type"], "apply_fact")
    if action_type in {"prefer", "work_with", "constrain"}:
        return f"Honor {memory['memory_key']} with value {_json_inline(memory['value'])}."
    if action_type in {"repeat", "follow_through"}:
        return f"Carry forward {memory['memory_key']} with value {_json_inline(memory['value'])}."
    return f"Use {memory['memory_key']} with value {_json_inline(memory['value'])} when acting."


def _playbook_explanation(pattern_key: str) -> str:
    return (
        f"Transparent rendering of pattern {pattern_key}. Each step maps directly to one trusted "
        "promotable fact; no opaque synthesis is used."
    )


def _serialize_pattern_row(row: FactPatternRow) -> TrustedFactPatternRecord:
    return {
        "id": str(row["id"]),
        "pattern_key": row["pattern_key"],
        "title": row["title"],
        "memory_type": row["memory_type"],
        "namespace_key": row["namespace_key"],
        "fact_count": row["fact_count"],
        "source_fact_ids": cast(list[str], row["source_fact_ids"]),
        "evidence_chain": cast(list[TrustedFactEvidenceLinkRecord], row["evidence_chain"]),
        "explanation": row["explanation"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _serialize_playbook_row(row: FactPlaybookRow) -> TrustedFactPlaybookRecord:
    return {
        "id": str(row["id"]),
        "playbook_key": row["playbook_key"],
        "pattern_id": str(row["pattern_id"]),
        "pattern_key": row["pattern_key"],
        "title": row["title"],
        "memory_type": row["memory_type"],
        "source_fact_ids": cast(list[str], row["source_fact_ids"]),
        "source_pattern_ids": cast(list[str], row["source_pattern_ids"]),
        "steps": cast(list[TrustedFactPlaybookStepRecord], row["steps"]),
        "explanation": row["explanation"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def sync_trusted_fact_promotions(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> None:
    del user_id

    memories = sorted(
        (memory for memory in store.list_memories() if _is_promotable_trusted_fact(memory)),
        key=lambda memory: (memory["memory_type"], _namespace_key(memory["memory_key"]), memory["memory_key"], str(memory["id"])),
    )
    revisions_by_memory_id = {
        memory["id"]: store.list_memory_revisions(memory["id"])
        for memory in memories
    }

    grouped: dict[tuple[str, str], list[MemoryRow]] = defaultdict(list)
    for memory in memories:
        grouped[(memory["memory_type"], _namespace_key(memory["memory_key"]))].append(memory)

    pattern_ids: list[UUID] = []
    playbook_ids: list[UUID] = []
    for (memory_type, namespace_key), grouped_memories in sorted(grouped.items()):
        if not grouped_memories:
            continue

        group_user_id = grouped_memories[0]["user_id"]
        pattern_key = f"{memory_type}:{namespace_key}"
        pattern_id = _stable_id(group_user_id, "fact-pattern", pattern_key)
        evidence_chain = [
            _evidence_link(memory, _latest_revision(memory, revisions_by_memory_id[memory["id"]]))
            for memory in grouped_memories
        ]
        store.upsert_fact_pattern(
            pattern_id=pattern_id,
            pattern_key=pattern_key,
            title=_pattern_title(memory_type, namespace_key),
            memory_type=memory_type,
            namespace_key=namespace_key,
            fact_count=len(grouped_memories),
            source_fact_ids=[str(memory["id"]) for memory in grouped_memories],
            evidence_chain=evidence_chain,
            explanation=_pattern_explanation(memory_type, namespace_key, len(grouped_memories)),
        )
        pattern_ids.append(pattern_id)

        playbook_key = f"{pattern_key}:playbook"
        playbook_id = _stable_id(group_user_id, "fact-playbook", playbook_key)
        steps: list[TrustedFactPlaybookStepRecord] = []
        for step_no, memory in enumerate(grouped_memories, start=1):
            steps.append(
                {
                    "step_no": step_no,
                    "fact_id": str(memory["id"]),
                    "memory_key": memory["memory_key"],
                    "action_type": _ACTION_TYPE_BY_MEMORY_TYPE.get(memory["memory_type"], "apply_fact"),
                    "instruction": _playbook_instruction(memory),
                    "value": memory["value"],
                    "trust": _trust_record(memory),
                }
            )
        store.upsert_fact_playbook(
            playbook_id=playbook_id,
            playbook_key=playbook_key,
            pattern_id=pattern_id,
            pattern_key=pattern_key,
            title=_pattern_title(memory_type, namespace_key).replace("pattern", "playbook", 1),
            memory_type=memory_type,
            source_fact_ids=[str(memory["id"]) for memory in grouped_memories],
            source_pattern_ids=[str(pattern_id)],
            steps=steps,
            explanation=_playbook_explanation(pattern_key),
        )
        playbook_ids.append(playbook_id)

    store.delete_fact_playbooks_not_in(playbook_ids)
    store.delete_fact_patterns_not_in(pattern_ids)


def list_trusted_fact_patterns(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TrustedFactPatternListQueryInput,
) -> TrustedFactPatternListResponse:
    sync_trusted_fact_promotions(store, user_id=user_id)
    rows = store.list_fact_patterns(limit=request.limit)
    total_count = store.count_fact_patterns()
    return {
        "items": [_serialize_pattern_row(row) for row in rows],
        "summary": {
            "returned_count": len(rows),
            "total_count": total_count,
            "limit": request.limit,
            "order": list(TRUSTED_FACT_PATTERN_ORDER),
        },
    }


def get_trusted_fact_pattern(
    store: ContinuityStore,
    *,
    user_id: UUID,
    pattern_id: UUID,
) -> TrustedFactPatternExplainResponse:
    sync_trusted_fact_promotions(store, user_id=user_id)
    row = store.get_fact_pattern_optional(pattern_id)
    if row is None:
        raise TrustedFactPromotionNotFoundError(f"pattern {pattern_id} was not found")
    return {"pattern": _serialize_pattern_row(row)}


def list_trusted_fact_playbooks(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: TrustedFactPlaybookListQueryInput,
) -> TrustedFactPlaybookListResponse:
    sync_trusted_fact_promotions(store, user_id=user_id)
    rows = store.list_fact_playbooks(limit=request.limit)
    total_count = store.count_fact_playbooks()
    return {
        "items": [_serialize_playbook_row(row) for row in rows],
        "summary": {
            "returned_count": len(rows),
            "total_count": total_count,
            "limit": request.limit,
            "order": list(TRUSTED_FACT_PLAYBOOK_ORDER),
        },
    }


def get_trusted_fact_playbook(
    store: ContinuityStore,
    *,
    user_id: UUID,
    playbook_id: UUID,
) -> TrustedFactPlaybookExplainResponse:
    sync_trusted_fact_promotions(store, user_id=user_id)
    row = store.get_fact_playbook_optional(playbook_id)
    if row is None:
        raise TrustedFactPromotionNotFoundError(f"playbook {playbook_id} was not found")
    return {"playbook": _serialize_playbook_row(row)}


__all__ = [
    "TrustedFactPromotionNotFoundError",
    "get_trusted_fact_pattern",
    "get_trusted_fact_playbook",
    "list_trusted_fact_patterns",
    "list_trusted_fact_playbooks",
    "sync_trusted_fact_promotions",
]
