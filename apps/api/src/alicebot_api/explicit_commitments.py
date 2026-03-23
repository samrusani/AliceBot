from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from uuid import UUID

from alicebot_api.contracts import (
    AdmissionDecisionOutput,
    ExplicitCommitmentAdmissionRecord,
    ExplicitCommitmentExtractionRequestInput,
    ExplicitCommitmentExtractionResponse,
    ExplicitCommitmentExtractionSummary,
    ExplicitCommitmentOpenLoopOutcome,
    ExplicitCommitmentPattern,
    ExtractedCommitmentCandidateRecord,
    MemoryCandidateInput,
    OpenLoopRecord,
)
from alicebot_api.memory import admit_memory_candidate
from alicebot_api.store import ContinuityStore, EventRow, OpenLoopRow

_DIRECT_PATTERNS: tuple[tuple[ExplicitCommitmentPattern, re.Pattern[str]], ...] = (
    ("remind_me_to", re.compile(r"^remind me to (?P<commitment>.+)$", re.IGNORECASE)),
    ("i_need_to", re.compile(r"^i need to (?P<commitment>.+)$", re.IGNORECASE)),
    (
        "dont_let_me_forget_to",
        re.compile(r"^don'?t let me forget to (?P<commitment>.+)$", re.IGNORECASE),
    ),
    ("remember_to", re.compile(r"^remember to (?P<commitment>.+)$", re.IGNORECASE)),
)
_TRAILING_PUNCTUATION = ".!?"
_MEMORY_KEY_PREFIX = "user.commitment."
_MAX_MEMORY_KEY_LENGTH = 200
_MEMORY_KEY_HASH_LENGTH = 12
_MAX_COMMITMENT_TOKENS = 20
_MAX_COMMITMENT_CHARACTERS = 180
_ALLOWED_COMMITMENT_TOKEN = re.compile(r"^[a-z0-9][a-z0-9+#&./+'-]*$", re.IGNORECASE)
_DISALLOWED_COMMITMENT_PREFIX_TOKENS = {
    "that",
    "if",
    "when",
    "because",
    "whether",
}


class ExplicitCommitmentExtractionValidationError(ValueError):
    """Raised when an explicit-commitment extraction request is invalid."""


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_commitment_text(commitment_text: str) -> str:
    normalized = _normalize_whitespace(commitment_text)
    normalized = normalized.rstrip(_TRAILING_PUNCTUATION).strip()
    return normalized


def _canonicalize_commitment_for_key(commitment_text: str) -> str:
    return commitment_text.casefold()


def _commitment_has_supported_shape(commitment_text: str) -> bool:
    if len(commitment_text) > _MAX_COMMITMENT_CHARACTERS:
        return False

    tokens = commitment_text.split(" ")
    if not tokens or len(tokens) > _MAX_COMMITMENT_TOKENS:
        return False

    if tokens[0].casefold() in _DISALLOWED_COMMITMENT_PREFIX_TOKENS:
        return False

    return all(_ALLOWED_COMMITMENT_TOKEN.fullmatch(token) is not None for token in tokens)


def _slugify_commitment(commitment_text: str, *, max_length: int) -> str:
    slug = commitment_text.casefold()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("_")
    return slug


def _build_memory_key(commitment_text: str) -> str:
    canonical_commitment = _canonicalize_commitment_for_key(commitment_text)
    digest = hashlib.sha256(canonical_commitment.encode("utf-8")).hexdigest()[:_MEMORY_KEY_HASH_LENGTH]
    max_slug_length = _MAX_MEMORY_KEY_LENGTH - len(_MEMORY_KEY_PREFIX) - len("__") - len(digest)
    slug = _slugify_commitment(canonical_commitment, max_length=max_slug_length)
    if not slug:
        return f"{_MEMORY_KEY_PREFIX}{digest}"
    return f"{_MEMORY_KEY_PREFIX}{slug}__{digest}"


def _build_open_loop_title(commitment_text: str) -> str:
    return f"Remember to {commitment_text}"


def _build_candidate(
    *,
    source_event_id: UUID,
    pattern: ExplicitCommitmentPattern,
    commitment_text: str,
) -> ExtractedCommitmentCandidateRecord | None:
    normalized_commitment = _normalize_commitment_text(commitment_text)
    if not normalized_commitment:
        return None

    if not _commitment_has_supported_shape(normalized_commitment):
        return None

    return {
        "memory_key": _build_memory_key(normalized_commitment),
        "value": {
            "kind": "explicit_commitment",
            "text": normalized_commitment,
        },
        "source_event_ids": [str(source_event_id)],
        "delete_requested": False,
        "pattern": pattern,
        "commitment_text": normalized_commitment,
        "open_loop_title": _build_open_loop_title(normalized_commitment),
    }


def extract_explicit_commitment_candidates(
    *,
    source_event_id: UUID,
    text: str,
) -> list[ExtractedCommitmentCandidateRecord]:
    normalized_text = _normalize_whitespace(text)
    if not normalized_text:
        return []

    for pattern_name, pattern in _DIRECT_PATTERNS:
        match = pattern.fullmatch(normalized_text)
        if match is None:
            continue
        candidate = _build_candidate(
            source_event_id=source_event_id,
            pattern=pattern_name,
            commitment_text=match.group("commitment"),
        )
        return [] if candidate is None else [candidate]

    return []


def _get_single_source_event(store: ContinuityStore, source_event_id: UUID) -> EventRow:
    events = store.list_events_by_ids([source_event_id])
    if not events:
        raise ExplicitCommitmentExtractionValidationError(
            "source_event_id must reference an existing message.user event owned by the user"
        )
    return events[0]


def _extract_text_payload(event: EventRow) -> str:
    if event["kind"] != "message.user":
        raise ExplicitCommitmentExtractionValidationError(
            "source_event_id must reference an existing message.user event owned by the user"
        )

    payload_text = event["payload"].get("text")
    if not isinstance(payload_text, str):
        raise ExplicitCommitmentExtractionValidationError(
            "source_event_id must reference a message.user event with string payload.text"
        )

    return payload_text


def _serialize_open_loop(open_loop: OpenLoopRow) -> OpenLoopRecord:
    return {
        "id": str(open_loop["id"]),
        "memory_id": None if open_loop["memory_id"] is None else str(open_loop["memory_id"]),
        "title": open_loop["title"],
        "status": open_loop["status"],
        "opened_at": open_loop["opened_at"].isoformat(),
        "due_at": None if open_loop["due_at"] is None else open_loop["due_at"].isoformat(),
        "resolved_at": (
            None if open_loop["resolved_at"] is None else open_loop["resolved_at"].isoformat()
        ),
        "resolution_note": open_loop["resolution_note"],
        "created_at": open_loop["created_at"].isoformat(),
        "updated_at": open_loop["updated_at"].isoformat(),
    }


def _find_active_open_loop_for_memory(store: ContinuityStore, memory_id: UUID) -> OpenLoopRow | None:
    for open_loop in store.list_open_loops(status="open"):
        if open_loop["memory_id"] == memory_id:
            return open_loop
    return None


def _extract_memory_id(decision: AdmissionDecisionOutput) -> UUID | None:
    if decision.memory is None:
        return None
    return UUID(decision.memory["id"])


def _resolve_open_loop_outcome(
    store: ContinuityStore,
    *,
    memory_id: UUID | None,
    open_loop_title: str,
) -> ExplicitCommitmentOpenLoopOutcome:
    if memory_id is None:
        return {
            "decision": "NOOP_MEMORY_NOT_PERSISTED",
            "reason": "memory_not_persisted",
            "open_loop": None,
        }

    existing = _find_active_open_loop_for_memory(store, memory_id)
    if existing is not None:
        return {
            "decision": "NOOP_ACTIVE_EXISTS",
            "reason": "active_open_loop_exists_for_memory",
            "open_loop": _serialize_open_loop(existing),
        }

    created = store.create_open_loop(
        memory_id=memory_id,
        title=open_loop_title,
        status="open",
        opened_at=None,
        due_at=None,
        resolved_at=None,
        resolution_note=None,
    )
    return {
        "decision": "CREATED",
        "reason": "created_open_loop_for_memory",
        "open_loop": _serialize_open_loop(created),
    }


def _serialize_admission(
    decision: AdmissionDecisionOutput,
    open_loop_outcome: ExplicitCommitmentOpenLoopOutcome,
) -> ExplicitCommitmentAdmissionRecord:
    return {
        "decision": decision.action,
        "reason": decision.reason,
        "memory": decision.memory,
        "revision": decision.revision,
        "open_loop": open_loop_outcome,
    }


def _build_summary(
    *,
    source_event_id: UUID,
    source_event_kind: str,
    admissions: Sequence[ExplicitCommitmentAdmissionRecord],
    candidates: Sequence[ExtractedCommitmentCandidateRecord],
) -> ExplicitCommitmentExtractionSummary:
    noop_count = sum(1 for admission in admissions if admission["decision"] == "NOOP")
    open_loop_created_count = sum(
        1
        for admission in admissions
        if admission["open_loop"]["decision"] == "CREATED"
    )
    return {
        "source_event_id": str(source_event_id),
        "source_event_kind": source_event_kind,
        "candidate_count": len(candidates),
        "admission_count": len(admissions),
        "persisted_change_count": len(admissions) - noop_count,
        "noop_count": noop_count,
        "open_loop_created_count": open_loop_created_count,
        "open_loop_noop_count": len(admissions) - open_loop_created_count,
    }


def extract_and_admit_explicit_commitments(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ExplicitCommitmentExtractionRequestInput,
) -> ExplicitCommitmentExtractionResponse:
    source_event = _get_single_source_event(store, request.source_event_id)
    payload_text = _extract_text_payload(source_event)
    candidates = extract_explicit_commitment_candidates(
        source_event_id=request.source_event_id,
        text=payload_text,
    )

    admissions: list[ExplicitCommitmentAdmissionRecord] = []
    for candidate in candidates:
        decision = admit_memory_candidate(
            store,
            user_id=user_id,
            candidate=MemoryCandidateInput(
                memory_key=candidate["memory_key"],
                value=candidate["value"],
                source_event_ids=(request.source_event_id,),
                delete_requested=candidate["delete_requested"],
                memory_type="commitment",
            ),
        )
        open_loop_outcome = _resolve_open_loop_outcome(
            store,
            memory_id=_extract_memory_id(decision),
            open_loop_title=candidate["open_loop_title"],
        )
        admissions.append(_serialize_admission(decision, open_loop_outcome))

    return {
        "candidates": list(candidates),
        "admissions": admissions,
        "summary": _build_summary(
            source_event_id=request.source_event_id,
            source_event_kind=source_event["kind"],
            admissions=admissions,
            candidates=candidates,
        ),
    }
