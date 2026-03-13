from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from alicebot_api.contracts import (
    AdmissionDecisionOutput,
    ExplicitPreferenceAdmissionRecord,
    ExplicitPreferenceExtractionRequestInput,
    ExplicitPreferenceExtractionResponse,
    ExplicitPreferenceExtractionSummary,
    ExplicitPreferencePattern,
    ExtractedPreferenceCandidateRecord,
    MemoryCandidateInput,
)
from alicebot_api.memory import admit_memory_candidate
from alicebot_api.store import ContinuityStore, EventRow, JsonObject

PreferenceKind = Literal["like", "dislike", "prefer"]
_DIRECT_PATTERNS: tuple[tuple[ExplicitPreferencePattern, PreferenceKind, re.Pattern[str]], ...] = (
    ("i_like", "like", re.compile(r"^i like (?P<subject>.+)$", re.IGNORECASE)),
    ("i_dont_like", "dislike", re.compile(r"^i don't like (?P<subject>.+)$", re.IGNORECASE)),
    ("i_prefer", "prefer", re.compile(r"^i prefer (?P<subject>.+)$", re.IGNORECASE)),
)
_REMEMBER_PREFIX = "remember that "
_TRAILING_PUNCTUATION = ".!?"
_MEMORY_KEY_PREFIX = "user.preference."
_MAX_MEMORY_KEY_LENGTH = 200
_MEMORY_KEY_HASH_LENGTH = 12
_MAX_SUBJECT_TOKENS = 6
_ALLOWED_SUBJECT_TOKEN = re.compile(r"^[a-z0-9][a-z0-9+#&./+'-]*$", re.IGNORECASE)
_DISALLOWED_SUBJECT_PREFIX_TOKENS = {
    "that",
    "to",
    "if",
    "when",
    "because",
    "whether",
    "we",
    "you",
    "they",
    "he",
    "she",
    "it",
    "there",
    "this",
}
_REMEMBER_PATTERN_MAP: dict[ExplicitPreferencePattern, ExplicitPreferencePattern] = {
    "i_like": "remember_that_i_like",
    "i_dont_like": "remember_that_i_dont_like",
    "i_prefer": "remember_that_i_prefer",
    "remember_that_i_like": "remember_that_i_like",
    "remember_that_i_dont_like": "remember_that_i_dont_like",
    "remember_that_i_prefer": "remember_that_i_prefer",
}


class ExplicitPreferenceExtractionValidationError(ValueError):
    """Raised when an explicit-preference extraction request is invalid."""


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_subject(subject: str) -> str:
    normalized = _normalize_whitespace(subject)
    normalized = normalized.rstrip(_TRAILING_PUNCTUATION).strip()
    return normalized


def _canonicalize_subject_for_key(subject: str) -> str:
    return subject.casefold()


def _subject_has_supported_shape(subject: str) -> bool:
    tokens = subject.split(" ")
    if not tokens or len(tokens) > _MAX_SUBJECT_TOKENS:
        return False

    if tokens[0].casefold() in _DISALLOWED_SUBJECT_PREFIX_TOKENS:
        return False

    return all(_ALLOWED_SUBJECT_TOKEN.fullmatch(token) is not None for token in tokens)


def _slugify_subject(subject: str, *, max_length: int) -> str:
    slug = subject.casefold()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("_")
    return slug


def _build_memory_key(subject: str) -> str:
    canonical_subject = _canonicalize_subject_for_key(subject)
    digest = hashlib.sha256(canonical_subject.encode("utf-8")).hexdigest()[:_MEMORY_KEY_HASH_LENGTH]
    max_slug_length = _MAX_MEMORY_KEY_LENGTH - len(_MEMORY_KEY_PREFIX) - len("__") - len(digest)
    slug = _slugify_subject(canonical_subject, max_length=max_slug_length)
    if not slug:
        return f"{_MEMORY_KEY_PREFIX}{digest}"
    return f"{_MEMORY_KEY_PREFIX}{slug}__{digest}"


def _build_candidate(
    *,
    source_event_id: UUID,
    pattern: ExplicitPreferencePattern,
    preference: PreferenceKind,
    subject_text: str,
) -> ExtractedPreferenceCandidateRecord | None:
    normalized_subject = _normalize_subject(subject_text)
    if not normalized_subject:
        return None

    if not _subject_has_supported_shape(normalized_subject):
        return None

    value: JsonObject = {
        "kind": "explicit_preference",
        "preference": preference,
        "text": normalized_subject,
    }
    return {
        "memory_key": _build_memory_key(normalized_subject),
        "value": value,
        "source_event_ids": [str(source_event_id)],
        "delete_requested": False,
        "pattern": pattern,
        "subject_text": normalized_subject,
    }


def extract_explicit_preference_candidates(
    *,
    source_event_id: UUID,
    text: str,
) -> list[ExtractedPreferenceCandidateRecord]:
    normalized_text = _normalize_whitespace(text)
    if not normalized_text:
        return []

    for pattern_name, preference, pattern in _DIRECT_PATTERNS:
        match = pattern.fullmatch(normalized_text)
        if match is not None:
            candidate = _build_candidate(
                source_event_id=source_event_id,
                pattern=pattern_name,
                preference=preference,
                subject_text=match.group("subject"),
            )
            return [] if candidate is None else [candidate]

    lowered_text = normalized_text.lower()
    if lowered_text.startswith(_REMEMBER_PREFIX):
        nested_text = normalized_text[len(_REMEMBER_PREFIX) :]
        nested_candidates = extract_explicit_preference_candidates(
            source_event_id=source_event_id,
            text=nested_text,
        )
        if not nested_candidates:
            return []
        candidate = dict(nested_candidates[0])
        candidate["pattern"] = _REMEMBER_PATTERN_MAP[candidate["pattern"]]
        return [candidate]

    return []


def _get_single_source_event(store: ContinuityStore, source_event_id: UUID) -> EventRow:
    events = store.list_events_by_ids([source_event_id])
    if not events:
        raise ExplicitPreferenceExtractionValidationError(
            "source_event_id must reference an existing message.user event owned by the user"
        )
    return events[0]


def _extract_text_payload(event: EventRow) -> str:
    if event["kind"] != "message.user":
        raise ExplicitPreferenceExtractionValidationError(
            "source_event_id must reference an existing message.user event owned by the user"
        )

    payload_text = event["payload"].get("text")
    if not isinstance(payload_text, str):
        raise ExplicitPreferenceExtractionValidationError(
            "source_event_id must reference a message.user event with string payload.text"
        )

    return payload_text


def _serialize_admission(decision: AdmissionDecisionOutput) -> ExplicitPreferenceAdmissionRecord:
    return {
        "decision": decision.action,
        "reason": decision.reason,
        "memory": decision.memory,
        "revision": decision.revision,
    }


def _build_summary(
    *,
    source_event_id: UUID,
    source_event_kind: str,
    admissions: Sequence[ExplicitPreferenceAdmissionRecord],
    candidates: Sequence[ExtractedPreferenceCandidateRecord],
) -> ExplicitPreferenceExtractionSummary:
    noop_count = sum(1 for admission in admissions if admission["decision"] == "NOOP")
    return {
        "source_event_id": str(source_event_id),
        "source_event_kind": source_event_kind,
        "candidate_count": len(candidates),
        "admission_count": len(admissions),
        "persisted_change_count": len(admissions) - noop_count,
        "noop_count": noop_count,
    }


def extract_and_admit_explicit_preferences(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: ExplicitPreferenceExtractionRequestInput,
) -> ExplicitPreferenceExtractionResponse:
    source_event = _get_single_source_event(store, request.source_event_id)
    payload_text = _extract_text_payload(source_event)
    candidates = extract_explicit_preference_candidates(
        source_event_id=request.source_event_id,
        text=payload_text,
    )

    admissions: list[ExplicitPreferenceAdmissionRecord] = []
    for candidate in candidates:
        decision = admit_memory_candidate(
            store,
            user_id=user_id,
            candidate=MemoryCandidateInput(
                memory_key=candidate["memory_key"],
                value=candidate["value"],
                source_event_ids=(request.source_event_id,),
                delete_requested=candidate["delete_requested"],
            ),
        )
        admissions.append(_serialize_admission(decision))

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
