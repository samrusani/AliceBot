"""Review-gated write integration for the occurrence substrate.

The pure identity rules live in :mod:`alicebot_api.vnext_occurrences`.  This
module is the transactional adapter that:

* conservatively recognizes completed-event statements at capture time;
* persists candidate claims, one-unit proposals, and provenance;
* materializes only proposals accepted through an existing memory decision;
* retires stale units when their governing memory or source is retired.

Every entry point is optional for third-party stores.  A store without the
complete occurrence write seam is left byte-for-byte unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import re
from typing import Any, Protocol, TypeGuard, cast
import unicodedata
from uuid import UUID

from alicebot_api.store import ContinuityStoreInvariantError
from alicebot_api.vnext_occurrences import (
    build_occurrence_proposal,
    normalize_count_key,
)
from alicebot_api.vnext_occurrence_predicates import (
    OCCURRENCE_AGGREGATION_SCHEMA,
    OCCURRENCE_PREDICATE_SCHEMA,
    OCCURRENCE_PREDICATE_TAXONOMY,
    canonicalize_occurrence_claim_aggregation,
    canonicalize_occurrence_predicate,
    occurrence_claim_facts_digest,
)
from alicebot_api.vnext_occurrence_taxonomy import (
    build_occurrence_predicate_atom,
    canonical_action_leaf,
)
from alicebot_api.vnext_project_scope import (
    project_scope_identity,
    resolve_project_scope,
)
from alicebot_api.vnext_repositories import JsonObject


OCCURRENCE_PROPOSAL_METADATA_KEY = "occurrence_proposal"
OCCURRENCE_INVALIDATION_METADATA_KEY = "occurrence_invalidation"
OCCURRENCE_CARRIER_METADATA_KEY = "occurrence_carrier"
OCCURRENCE_EXTRACTOR_VERSION = "natural-completed-event-v3"
OCCURRENCE_EXTRACTION_MEMORY_LIMIT = 200
_USE_CARRIER_MEMORY_ID = object()

_WRITE_METHODS = (
    "update_memory",
    "ensure_occurrence_coverage",
    "get_or_create_occurrence_claim",
    "get_occurrence_claim",
    "review_occurrence_claim",
    "get_or_create_occurrence_unit",
    "get_occurrence_unit_by_key",
    "create_occurrence_evidence",
    "review_occurrence_unit",
    "list_occurrence_units_for_claim",
    "list_occurrence_units_for_memory",
    "list_occurrence_evidence_for_units",
    "refresh_occurrence_unit_evidence",
    "reconcile_occurrence_evidence_carrier",
    "reconcile_occurrence_claim_evidence",
    "invalidate_occurrence_coverage",
    "invalidate_occurrence_extraction_dispositions",
    "list_occurrence_claims_for_source_chunk",
    "list_source_chunks",
)
_DISPOSITION_METHODS = (
    "get_source_chunks_by_ids",
    "get_source_chunk_for_occurrence_accounting",
    "list_source_chunks",
    "list_memories",
    "record_occurrence_extraction_disposition",
    "review_occurrence_extraction_disposition",
)


class _OccurrenceDispositionStore(Protocol):
    """Store methods proved by ``occurrence_dispositions_supported``."""

    def get_source_chunks_by_ids(self, *args: Any, **kwargs: Any) -> Any: ...

    def get_source_chunk_for_occurrence_accounting(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_source_chunks(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_memories(self, *args: Any, **kwargs: Any) -> Any: ...

    def record_occurrence_extraction_disposition(self, *args: Any, **kwargs: Any) -> Any: ...

    def review_occurrence_extraction_disposition(self, *args: Any, **kwargs: Any) -> Any: ...


class _OccurrenceDispositionReconciliationStore(_OccurrenceDispositionStore, Protocol):
    """Disposition surface plus occurrence reads supplied by full stores."""

    def get_occurrence_claim(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_evidence_for_units(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_claims_for_source_chunk(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_units_for_claim(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_units_for_memory(self, *args: Any, **kwargs: Any) -> Any: ...


class _OccurrenceWriteStore(Protocol):
    """Dynamically detected complete occurrence write surface."""

    def ensure_occurrence_coverage(self, *args: Any, **kwargs: Any) -> Any: ...

    def get_or_create_occurrence_claim(self, *args: Any, **kwargs: Any) -> Any: ...

    def get_occurrence_claim(self, *args: Any, **kwargs: Any) -> Any: ...

    def review_occurrence_claim(self, *args: Any, **kwargs: Any) -> Any: ...

    def get_or_create_occurrence_unit(self, *args: Any, **kwargs: Any) -> Any: ...

    def get_occurrence_unit_by_key(self, *args: Any, **kwargs: Any) -> Any: ...

    def create_occurrence_evidence(self, *args: Any, **kwargs: Any) -> Any: ...

    def review_occurrence_unit(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_units_for_claim(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_units_for_memory(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_evidence_for_units(self, *args: Any, **kwargs: Any) -> Any: ...

    def refresh_occurrence_unit_evidence(self, *args: Any, **kwargs: Any) -> Any: ...

    def reconcile_occurrence_evidence_carrier(self, *args: Any, **kwargs: Any) -> Any: ...

    def reconcile_occurrence_claim_evidence(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_occurrence_claims_for_source_chunk(self, *args: Any, **kwargs: Any) -> Any: ...

    def list_source_chunks(self, *args: Any, **kwargs: Any) -> Any: ...

    def lock_source_occurrence_envelope(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...


_SPEAKER_TAG = re.compile(
    r"^\s*\[(?P<role>user|human|assistant|system|tool|agent)\]\s*:\s*",
    re.IGNORECASE,
)
_SPEAKER_PREFIX = re.compile(r"^\s*\[(?:user|human)\]\s*:\s*", re.IGNORECASE)
_NEGATED_EVENT = re.compile(
    r"\b(?:did\s+not|didn['’]t|have\s+not|haven['’]t|has\s+not|"
    r"hasn['’]t|had\s+not|hadn['’]t|never)\b",
    re.IGNORECASE,
)
_ACTION_WORD_PATTERN = r"[a-z][a-z'-]{1,38}"
_PLAUSIBLE_FIRST_PERSON_EVENT_ASSERTION = re.compile(
    rf"""
    \b(?:i|we)(?P<contraction>['’](?:ve|d))?\s+
    (?:(?P<auxiliary>have|had|did)\s+)?
    (?P<verb>{_ACTION_WORD_PATTERN})\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
_SUBJECTLESS_COMPLETED_ASSERTION = re.compile(
    rf"^\s*(?P<verb>{_ACTION_WORD_PATTERN})\b",
    re.IGNORECASE | re.VERBOSE,
)
_SUBJECTLESS_DID_ASSERTION = re.compile(
    r"^\s*did\s+(?!i\b|we\b|not\b|n['’]t\b)[a-z][a-z'-]*\b",
    re.IGNORECASE,
)
_SUBJECTLESS_PASSIVE_ASSERTION = re.compile(
    r"^\s*(?:was|were)\s+"
    r"(?:[a-z][a-z'-]*(?:ed|en)|built|made|seen|done|eaten|bought|"
    r"caught|written|driven|flown|taken|given|found|lost|read|sent|paid)\b",
    re.IGNORECASE,
)
_NOMINAL_EVENT_ASSERTION = re.compile(
    r"\b(?:my|our)\s+[^.!?;\n]{1,120}?"
    r"\b(?:happened|occurred|took\s+place|was\s+(?:on|at|in))\b",
    re.IGNORECASE,
)
_PERSONAL_NOMINAL_STATE_ASSERTION = re.compile(
    r"\b(?:my|our)\s+[^.!?;\n]{1,120}?\b(?:was|were)\b",
    re.IGNORECASE,
)
_PAST_EVENT_CONTEXT = re.compile(
    r"(?:"
    r"\b20\d{2}[/-](?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])\b|"
    r"\b(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])"
    r"(?:/\d{2,4})?\b|"
    r"\b(?:yesterday|last\s+(?:week|month|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b|"
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:days?|weeks?|months?)\s+ago\b|"
    r"^\s*(?:after|before|during)\b[^,]{1,80},"
    r")",
    re.IGNORECASE,
)
_PERSONAL_PASSIVE_EVENT_ASSERTION = re.compile(
    r"\b(?:was|were)\s+"
    r"(?:[a-z][a-z'-]*(?:ed|en)|built|made|seen|done|eaten|bought|"
    r"caught|written|driven|flown|taken|given|found|lost|read|sent|paid)"
    r"\s+(?:[^.!?;\n]{0,60}\s+)?by\s+(?:me|us)\b",
    re.IGNORECASE,
)
_ZERO_EVENT_OBJECT = re.compile(
    r"^\s*(?:no|zero|nil|nought|neither|none(?:\s+of)?|"
    r"not\s+(?:one|a\s+single|one\s+single))\b",
    re.IGNORECASE,
)
_AMBIGUOUS_EVENT_OBJECT_CARDINALITY = re.compile(
    r"^\s*(?:(?:hardly|scarcely|barely)\s+any|"
    r"a\s+few|few|several|many|some|multiple|various)\b",
    re.IGNORECASE,
)
_SUBJECT_EVENT_START = rf"""
    \b(?:i|we)\s+
    (?:(?:recently|just|also|already)\s+)*
"""
_COMPLETED_EVENT = re.compile(
    r"""^\s*
    """
    + _SUBJECT_EVENT_START
    + rf"""
    (?P<verb>{_ACTION_WORD_PATTERN})
    \s+(?P<object>[^.!?;\n]+)
    """,
    re.IGNORECASE | re.VERBOSE,
)
_NESTED_COMPLETED_EVENT = re.compile(
    r"""^\s*
    """
    + _SUBJECT_EVENT_START
    + r"""
    used\s+
    (?P<instrument>(?!to\b)[^.!?;\n]+?)\s+
    to\s+
    (?P<verb>[a-z][a-z'-]{1,38})\s+
    (?P<object>[^.!?;\n]+)
    """,
    re.IGNORECASE | re.VERBOSE,
)
_PERFECT_COMPLETED_EVENT = re.compile(
    r"""^\s*
    """
    + _SUBJECT_EVENT_START
    + rf"""
    (?:have|had)\s+
    (?P<verb>{_ACTION_WORD_PATTERN})
    \s+(?P<object>[^.!?;\n]+)
    """,
    re.IGNORECASE | re.VERBOSE,
)
_EMPHATIC_COMPLETED_EVENT = re.compile(
    r"""^\s*
    """
    + _SUBJECT_EVENT_START
    + r"""
    did\s+
    (?P<verb>[a-z][a-z'-]{1,38})
    \s+(?P<object>[^.!?;\n]+)
    """,
    re.IGNORECASE | re.VERBOSE,
)
_EVENT_CLAUSE_START = re.compile(
    _SUBJECT_EVENT_START + rf"(?P<verb>{_ACTION_WORD_PATTERN})\b",
    re.IGNORECASE | re.VERBOSE,
)
_COORDINATED_EVENT_START = re.compile(
    rf"""
    \b(?:and|then)\s+
    (?:(?:i|we)\s+)?
    (?:(?:recently|just|also|already)\s+)*
    (?P<verb>{_ACTION_WORD_PATTERN})\b
    """,
    re.IGNORECASE | re.VERBOSE,
)
_OBJECT_DETERMINERS = {
    "a",
    "an",
    "another",
    "my",
    "our",
    "that",
    "the",
    "their",
    "these",
    "this",
    "those",
}
_OBJECT_RELATION_WORDS = {
    "at",
    "during",
    "for",
    "from",
    "in",
    "near",
    "of",
    "on",
    "to",
    "with",
}
_QUANTITY_VALUE_PATTERN = r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
_QUANTITY_TIMES = re.compile(
    rf"\b(?P<at_least>at\s+least\s+)?(?P<exactly>exactly\s+)?"
    rf"(?:(?P<standalone>once|twice)|(?P<value>{_QUANTITY_VALUE_PATTERN})"
    r"\s+times?)\b",
    re.IGNORECASE,
)
_QUANTITY_RANGE = re.compile(
    rf"\bbetween\s+(?P<low>{_QUANTITY_VALUE_PATTERN})\s*"
    rf"(?:-|to|and)\s*(?P<high>{_QUANTITY_VALUE_PATTERN})\s+times?\b",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(
    r"\b(?P<year>20\d{2})[/-](?P<month>0?[1-9]|1[0-2])[/-]"
    r"(?P<day>0?[1-9]|[12]\d|3[01])\b"
)
_SLASH_DATE = re.compile(
    r"\b(?P<month>0?[1-9]|1[0-2])/(?P<day>0?[1-9]|[12]\d|3[01])"
    r"(?:/(?P<year>\d{2,4}))?\b"
)
_MONTH_DATE = re.compile(
    r"\b(?P<month>"
    r"january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|"
    r"oct|nov|dec"
    r")\s+(?P<day>[0-3]?\d)(?:st|nd|rd|th)?(?:,\s*|\s+)?"
    r"(?P<year>20\d{2})?\b",
    re.IGNORECASE,
)
_REFERENCE_DATE = re.compile(
    r"\b(?P<year>20\d{2})[/-](?P<month>0?[1-9]|1[0-2])[/-]"
    r"(?P<day>0?[1-9]|[12]\d|3[01])\b"
)
_TEMPORAL_TAIL = re.compile(
    r"\b(?:once|twice|one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
    r"\s+times?\b.*$|"
    r"\b(?:on|at|during|in|yesterday|today|last)\b.*$|"
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:days?|weeks?|months?)\s+ago\b.*$",
    re.IGNORECASE,
)
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_NUMBER_WORDS = {
    "zero": 0,
    "once": 1,
    "one": 1,
    "twice": 2,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
_RELATIVE_WEEKDAY = re.compile(
    r"\b(?P<relative>last|this)\s+"
    r"(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
_RELATIVE_PERIOD = re.compile(
    r"\b(?P<relative>last|this)\s+(?P<period>week|month)\b",
    re.IGNORECASE,
)
_AGO_PERIOD = re.compile(
    r"\b(?P<value>\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?P<period>days?|weeks?|months?)\s+ago\b",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])(?:\s+|$)|\n+")
_QUESTION_INVERSION = re.compile(
    r"^(?:(?:who|what|when|where|why|how|which)\b|"
    r"(?:am|are|is|was|were|do|does|did|have|has|had|can|could|will|"
    r"would|shall|should|may|might|must)\s+"
    r"(?:i|we|you|he|she|it|they|there)\b)",
    re.IGNORECASE,
)
_CONDITIONAL_LANGUAGE = re.compile(
    r"\b(?:if|unless|provided(?:\s+that)?|assuming|supposing|in\s+case|"
    r"as\s+long\s+as|even\s+if|whether)\b",
    re.IGNORECASE,
)
_COUNTERFACTUAL_LANGUAGE = re.compile(
    r"\b(?:would|could|might|should|almost|nearly|planned|intended|"
    r"hoped|wanted|tried|attempted|supposed|meant|maybe|perhaps|possibly|"
    r"probably|allegedly)\b",
    re.IGNORECASE,
)
_MODAL_MAY = re.compile(r"\bmay\b", re.IGNORECASE)
_ATTRIBUTION_PREFIX = re.compile(
    r"^(?:according\s+to\b|apparently\b|reportedly\b|"
    r"(?:someone|somebody|they|he|she|you|alice|bob)\s+"
    r"(?:said|told|reported|claimed|thought|believed|remembered|recalled|"
    r"heard|read|wrote)\b)",
    re.IGNORECASE,
)
_FIRST_PERSON_ATTRIBUTION_PREFIX = re.compile(
    r"^(?:i|we)(?:['’](?:ve|d))?\s+"
    r"(?:(?:have|had)\s+)?"
    r"(?:said|told|reported|claimed|thought|believed|remembered|recalled|"
    r"heard|read|wrote)\b"
    r"(?=\s+(?:that\b|[\"“'‘])|\s*:)",
    re.IGNORECASE,
)
_ATTRIBUTION_TRAILER = re.compile(
    r",?\s+(?:according\s+to|per)\b",
    re.IGNORECASE,
)
_TRAILING_TAG_QUESTION = re.compile(
    r",\s*(?:right|correct|remember|do\s+you\s+remember|"
    r"did(?:n't|\s+not)\s+i|is(?:n't|\s+not)\s+that\s+right)\?\s*$",
    re.IGNORECASE,
)
_ALTERNATIVE_MONTH_DAY = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|"
    r"oct|nov|dec)\s+[0-3]?\d(?:st|nd|rd|th)?\s+(?:or|/)\s+"
    r"[0-3]?\d(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)
_CLAUSE_CONTEXT_BOUNDARY = re.compile(
    r",?\s+\b(?:which|who|because|although|though|while|whereas|before|after)\b",
    re.IGNORECASE,
)
_UNPARSED_COORDINATION = re.compile(
    r",?\s+\b(?:and|then|but)\s+"
    r"(?:(?:i|we|it|he|she|they)\b|[a-z][a-z'-]{1,38}(?:ed|ied)\b)",
    re.IGNORECASE,
)
_COMPARATIVE_QUANTITY = re.compile(
    rf"\b(?:no\s+more|more|less|fewer)\s+than\s+"
    rf"(?:once|twice|{_QUANTITY_VALUE_PATTERN}\s+times?)\b|"
    r"\b(?:about|around|roughly|approximately|up\s+to|at\s+most|nearly)\s+"
    rf"(?:once|twice|{_QUANTITY_VALUE_PATTERN}\s+times?)\b|"
    rf"\b{_QUANTITY_VALUE_PATTERN}\s+(?:or|and)\s+"
    rf"{_QUANTITY_VALUE_PATTERN}\s+times?\b",
    re.IGNORECASE,
)
_VAGUE_QUANTITY = re.compile(
    r"\b(?:several|many|dozens\s+of|a\s+few|a\s+couple(?:\s+of)?)\s+times?\b"
    rf"|\b{_QUANTITY_VALUE_PATTERN}\s*(?:-|–)?\s*ish\s+times?\b",
    re.IGNORECASE,
)
_ANY_QUANTITY_CUE = re.compile(
    rf"\b(?:at\s+least\s+|exactly\s+)?(?:once|twice|"
    rf"{_QUANTITY_VALUE_PATTERN}\s+times?)\b|"
    rf"\bbetween\s+{_QUANTITY_VALUE_PATTERN}\s+(?:and|to|-)\s+"
    rf"{_QUANTITY_VALUE_PATTERN}\s+times?\b|"
    r"\b(?:several|many|dozens\s+of|a\s+few|a\s+couple(?:\s+of)?)\s+times?\b|"
    rf"\b{_QUANTITY_VALUE_PATTERN}\s*(?:-|–)?\s*ish\s+times?\b",
    re.IGNORECASE,
)
_QUANTITY_OBJECT_TAIL = re.compile(
    rf"\s+\b(?:"
    rf"between\s+{_QUANTITY_VALUE_PATTERN}\s*(?:and|to|-)\s*"
    rf"{_QUANTITY_VALUE_PATTERN}\s+times?|"
    rf"(?:(?:at\s+least|exactly|about|around|roughly|approximately|up\s+to|"
    rf"at\s+most|nearly|no\s+more\s+than|more\s+than|less\s+than|"
    rf"fewer\s+than)\s+)?(?:once|twice)(?:\s+times?)?|"
    rf"(?:(?:at\s+least|exactly|about|around|roughly|approximately|up\s+to|"
    rf"at\s+most|nearly|no\s+more\s+than|more\s+than|less\s+than|"
    rf"fewer\s+than)\s+)?{_QUANTITY_VALUE_PATTERN}"
    rf"(?:\s+(?:or|and)\s+{_QUANTITY_VALUE_PATTERN})?\s+times?|"
    rf"(?:several|many|dozens\s+of|a\s+few|a\s+couple(?:\s+of)?)\s+times?|"
    rf"{_QUANTITY_VALUE_PATTERN}\s*(?:-|–)?\s*ish\s+times?"
    rf")\b.*$",
    re.IGNORECASE,
)


def occurrence_writes_supported(store: object) -> TypeGuard[_OccurrenceWriteStore]:
    """Whether ``store`` implements the complete truth-critical write seam."""

    return all(callable(getattr(store, method, None)) for method in _WRITE_METHODS)


def occurrence_dispositions_supported(store: object) -> TypeGuard[_OccurrenceDispositionStore]:
    """Whether ``store`` can persist and sign current-chunk scan outcomes."""

    return all(callable(getattr(store, method, None)) for method in _DISPOSITION_METHODS)


def _lock_occurrence_write_graph(store: object) -> None:
    """Enter the bundled per-user mutation boundary before any graph read."""

    lock_graph_mutation = getattr(store, "lock_graph_mutation", None)
    if callable(lock_graph_mutation):
        lock_graph_mutation()


def invalidate_occurrence_accounting(
    store: object,
    *,
    reason: str,
    actor_type: str,
    actor_id: str | None = None,
    source_chunk_id: str | None = None,
    effective_at: datetime | str | None = None,
    _defer_occurrence_coverage: bool = False,
) -> None:
    """Revoke signed exactness before a fact-affecting write."""

    invalidate_dispositions = getattr(store, "invalidate_occurrence_extraction_dispositions", None)
    if source_chunk_id is not None and callable(invalidate_dispositions):
        invalidate_dispositions(
            source_chunk_id=str(source_chunk_id),
            reason=reason,
            extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
            effective_at=effective_at,
            actor_type=actor_type,
            actor_id=actor_id,
            _defer_occurrence_coverage=_defer_occurrence_coverage,
        )
        return
    invalidate_coverage = getattr(store, "invalidate_occurrence_coverage", None)
    if callable(invalidate_coverage):
        invalidate_coverage(
            reason=reason,
            effective_at=effective_at,
            actor_type=actor_type,
            actor_id=actor_id,
        )


def _chunk_has_plausible_unaccounted_user_assertion(
    chunk: Mapping[str, object],
    *,
    accounted_predicate_counts: Mapping[str, int],
) -> bool:
    source_title: str | None = None
    raw_title = chunk.get("source_title")
    if isinstance(raw_title, str) and raw_title.strip():
        source_title = " ".join(raw_title.split()).strip().rstrip(".")
    remaining_predicates = dict(accounted_predicate_counts)
    speaker_blocks = _speaker_text_blocks(str(chunk.get("text") or ""))
    has_tagged_user_block = any(role in {"user", "human"} for role, _block in speaker_blocks)
    for active_role, block in speaker_blocks:
        if active_role in {"assistant", "system", "tool", "agent"}:
            continue
        for raw_sentence in _quote_aware_sentence_texts(block):
            sentence = raw_sentence.strip()
            normalized_sentence = " ".join(sentence.split()).strip().rstrip(".")
            if (
                active_role is None
                and has_tagged_user_block
                and source_title is not None
                and normalized_sentence == source_title
            ):
                # Connector-rendered title/provenance framing is not a user
                # event assertion. This is content-derived (exact source-title
                # equality), not a connector- or benchmark-specific phrase.
                continue
            sentence = re.sub(
                r"^(?:fact|happened|event|note|memory)\s*:\s*",
                "",
                sentence,
                flags=re.IGNORECASE,
            )
            lowered = sentence.casefold()
            if (
                not sentence
                or sentence.endswith("?")
                or _NEGATED_EVENT.search(sentence)
                or _QUESTION_INVERSION.match(lowered)
                or _CONDITIONAL_LANGUAGE.search(lowered)
                or _contains_counterfactual_language(lowered)
                or _ATTRIBUTION_PREFIX.match(lowered)
                or _FIRST_PERSON_ATTRIBUTION_PREFIX.match(lowered)
                or _ATTRIBUTION_TRAILER.search(lowered)
            ):
                continue
            natural_hint = _natural_event_sentence_hint(
                sentence,
                source=None,
            )
            if natural_hint is not None:
                signature = _predicate_signature(str(natural_hint.get("count_key") or ""))
                remaining = remaining_predicates.get(signature, 0)
                if remaining > 0:
                    remaining_predicates[signature] = remaining - 1
                    continue
                return True
            if _natural_zero_event_assertion(sentence):
                continue
            subjectless_completed = _SUBJECTLESS_COMPLETED_ASSERTION.match(sentence)
            if (
                _has_plausible_first_person_event_assertion(sentence)
                or (
                    subjectless_completed is not None
                    and (
                        _natural_completed_verb_allowed(str(subjectless_completed.group("verb")))
                        or _has_past_event_context(sentence)
                    )
                )
                or _SUBJECTLESS_DID_ASSERTION.match(sentence)
                or _SUBJECTLESS_PASSIVE_ASSERTION.match(sentence)
                or _NOMINAL_EVENT_ASSERTION.search(sentence)
                or _PERSONAL_NOMINAL_STATE_ASSERTION.search(sentence)
                or _PERSONAL_PASSIVE_EVENT_ASSERTION.search(sentence)
            ):
                return True
    return False


def _predicate_signature(value: str) -> str:
    normalized = normalize_count_key(value)
    return " ".join(sorted(normalized.split()))


def _memories_for_source_chunk(
    store: _OccurrenceDispositionReconciliationStore,
    source_chunk_id: str,
) -> Sequence[object]:
    bounded_lookup = getattr(store, "list_memories_for_source_chunk", None)
    if not callable(bounded_lookup):
        # Compatibility path for third-party stores predating the bounded
        # occurrence lookup. Production PostgreSQL/SQLite stores never enter it.
        return cast(Sequence[object], store.list_memories(status=None))
    rows = bounded_lookup(str(source_chunk_id))
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ContinuityStoreInvariantError("source chunk occurrence lookup returned an invalid result")
    if len(rows) > OCCURRENCE_EXTRACTION_MEMORY_LIMIT:
        raise ContinuityStoreInvariantError("source chunk occurrence reconciliation exceeds the bounded memory limit")
    return rows


def _accounted_occurrence_record(
    store: _OccurrenceDispositionReconciliationStore,
    raw_memory: Mapping[str, object],
    record: Mapping[str, object],
    *,
    source_chunk_id: str,
) -> tuple[str, str, str, set[str]] | None:
    """Validate one durable proposal record for extraction accounting."""

    if str(record.get("source_chunk_id") or "") != source_chunk_id:
        return None
    claim_id = str(record.get("claim_id") or "")
    if not claim_id:
        return None
    claim = store.get_occurrence_claim(claim_id)
    if not isinstance(claim, Mapping):
        raise ContinuityStoreInvariantError("chunk extraction accounting references a missing occurrence claim")
    count_key = str(record.get("count_key") or claim.get("count_key") or "")
    if claim.get("review_status") == "candidate" and claim.get("resolution_status") == "pending":
        return "unresolved", claim_id, count_key, set()
    if claim.get("review_status") != "accepted" or claim.get("resolution_status") != "resolved":
        return None

    claim_occurrence_ids = {
        str(value)
        for value in cast(
            Sequence[object],
            record.get("occurrence_unit_ids") or (),
        )
        if str(value)
    }
    if not claim_occurrence_ids:
        raise ContinuityStoreInvariantError("resolved chunk occurrence claim has no materialized units")
    evidence_rows: list[Mapping[str, object]] = []
    ordered_occurrence_ids = sorted(claim_occurrence_ids)
    evidence_as_of = datetime.now(UTC)
    for offset in range(0, len(ordered_occurrence_ids), 200):
        occurrence_id_batch = ordered_occurrence_ids[offset : offset + 200]
        after_evidence_id: str | None = None
        while True:
            page = [
                row
                for row in store.list_occurrence_evidence_for_units(
                    occurrence_id_batch,
                    as_of=evidence_as_of,
                    after_id=after_evidence_id,
                    limit=200,
                )
                if isinstance(row, Mapping)
            ]
            evidence_rows.extend(page)
            if len(page) < 200:
                break
            next_after_id = str(page[-1].get("id") or "")
            if not next_after_id or next_after_id == after_evidence_id:
                raise ContinuityStoreInvariantError("occurrence evidence pagination did not advance")
            after_evidence_id = next_after_id
    source_supported_ids = {
        str(row.get("occurrence_id") or "")
        for row in evidence_rows
        if str(row.get("claim_id") or "") == claim_id
        and str(row.get("source_chunk_id") or "") == source_chunk_id
        and row.get("review_status") in {"candidate", "accepted"}
    }
    if source_supported_ids != claim_occurrence_ids:
        # The claim may still be valid through another memory or source, but
        # it no longer accounts for this source chunk.
        return None
    units_by_id = {
        str(row.get("id") or ""): row
        for row in store.list_occurrence_units_for_memory(str(raw_memory["id"]))
        if isinstance(row, Mapping)
    }
    for occurrence_id in claim_occurrence_ids:
        unit = units_by_id.get(occurrence_id)
        if (
            not isinstance(unit, Mapping)
            or unit.get("review_status") != "accepted"
            or unit.get("identity_status") != "resolved"
        ):
            raise ContinuityStoreInvariantError("resolved chunk occurrence claim is only partially materialized")
    return "accepted", claim_id, count_key, claim_occurrence_ids


def _accounted_source_claim(
    store: _OccurrenceDispositionReconciliationStore,
    claim: Mapping[str, object],
    *,
    source_chunk_id: str,
) -> tuple[str, str, str, set[str]]:
    """Validate one claim carried directly by current source-chunk evidence."""

    claim_id = str(claim.get("id") or "")
    count_key = str(claim.get("count_key") or "")
    if not claim_id or not count_key:
        raise ContinuityStoreInvariantError("source chunk occurrence claim lacks durable identity")
    if claim.get("review_status") == "candidate" and claim.get("resolution_status") == "pending":
        return "unresolved", claim_id, count_key, set()
    if claim.get("review_status") != "accepted" or claim.get("resolution_status") != "resolved":
        raise ContinuityStoreInvariantError("source chunk occurrence claim has an invalid reviewed lifecycle")
    if claim.get("resolution_decision") != "new":
        resolved_id = str(claim.get("resolved_occurrence_id") or "")
        if not resolved_id:
            raise ContinuityStoreInvariantError("linked source occurrence claim lacks its resolved unit")
        occurrence_ids = {resolved_id}
    else:
        occurrence_ids = {
            str(row.get("id") or "")
            for row in store.list_occurrence_units_for_claim(claim_id)
            if isinstance(row, Mapping)
            and row.get("review_status") == "accepted"
            and row.get("identity_status") == "resolved"
        }
        occurrence_ids.discard("")
    if not occurrence_ids:
        raise ContinuityStoreInvariantError("resolved source occurrence claim has no accepted unit")

    evidence_rows: list[Mapping[str, object]] = []
    evidence_as_of = datetime.now(UTC)
    ordered_ids = sorted(occurrence_ids)
    for offset in range(0, len(ordered_ids), 200):
        batch = ordered_ids[offset : offset + 200]
        after_id: str | None = None
        while True:
            page = [
                row
                for row in store.list_occurrence_evidence_for_units(
                    batch,
                    as_of=evidence_as_of,
                    after_id=after_id,
                    limit=200,
                )
                if isinstance(row, Mapping)
            ]
            evidence_rows.extend(page)
            if len(page) < 200:
                break
            next_after = str(page[-1].get("id") or "")
            if not next_after or next_after == after_id:
                raise ContinuityStoreInvariantError("source occurrence evidence pagination did not advance")
            after_id = next_after
    supported = {
        str(row.get("occurrence_id") or "")
        for row in evidence_rows
        if str(row.get("claim_id") or "") == claim_id
        and str(row.get("source_chunk_id") or "") == source_chunk_id
        and row.get("review_status") in {"candidate", "accepted"}
    }
    if supported != occurrence_ids:
        raise ContinuityStoreInvariantError("source occurrence claim is not fully supported by its chunk")
    return "accepted", claim_id, count_key, occurrence_ids


def reconcile_chunk_extraction_disposition(
    store: object,
    *,
    source_chunk_id: str,
    actor_type: str,
    reviewer_id: str | None = None,
    reason: str | None = None,
) -> JsonObject | None:
    """Rebuild one chunk's accounting result from its durable proposals.

    A reviewer may sign exhaustive extraction accounting even when a durable
    claim remains unresolved. Query-specific exactness still treats matching or
    unknown unresolved predicates as bounds, never as absent events.
    """

    if not occurrence_dispositions_supported(store):
        return None
    _lock_occurrence_write_graph(store)
    # Disposition reconciliation is reached only through a store that can
    # supply the signed chunk envelope used by the raw-assertion guard.
    store = cast(_OccurrenceDispositionReconciliationStore, store)
    predicate_keys: set[str] = set()
    unresolved_claim_ids: set[str] = set()
    accepted_claim_ids: set[str] = set()
    accepted_occurrence_ids: set[str] = set()
    accounted_predicate_counts: dict[str, int] = {}
    memory_ids: set[str] = set()
    for raw_memory in _memories_for_source_chunk(store, str(source_chunk_id)):
        if not isinstance(raw_memory, Mapping):
            continue
        metadata = _metadata(raw_memory)
        if str(metadata.get("source_chunk_id") or "") != str(source_chunk_id):
            continue
        for record in _occurrence_proposal_records(metadata):
            state = _accounted_occurrence_record(
                store,
                raw_memory,
                record,
                source_chunk_id=str(source_chunk_id),
            )
            if state is None:
                continue
            status, claim_id, count_key, claim_occurrence_ids = state
            memory_ids.add(str(raw_memory.get("id") or ""))
            predicate_keys.add(count_key)
            if status == "unresolved":
                if claim_id not in unresolved_claim_ids:
                    signature = _predicate_signature(count_key)
                    accounted_predicate_counts[signature] = accounted_predicate_counts.get(signature, 0) + 1
                unresolved_claim_ids.add(claim_id)
                continue
            accepted_occurrence_ids.update(claim_occurrence_ids)
            if claim_id not in accepted_claim_ids:
                signature = _predicate_signature(count_key)
                accounted_predicate_counts[signature] = accounted_predicate_counts.get(signature, 0) + 1
            accepted_claim_ids.add(claim_id)

    source_claim_lookup = getattr(
        store,
        "list_occurrence_claims_for_source_chunk",
        None,
    )
    if callable(source_claim_lookup):
        source_claims = source_claim_lookup(
            str(source_chunk_id),
            limit=201,
        )
        if (
            not isinstance(source_claims, Sequence)
            or isinstance(source_claims, (str, bytes))
            or len(source_claims) > OCCURRENCE_EXTRACTION_MEMORY_LIMIT
        ):
            raise ContinuityStoreInvariantError(
                "source chunk occurrence reconciliation exceeds the bounded claim limit"
            )
        for raw_claim in source_claims:
            if not isinstance(raw_claim, Mapping):
                raise ContinuityStoreInvariantError("source chunk occurrence lookup returned an invalid claim")
            state = _accounted_source_claim(
                store,
                raw_claim,
                source_chunk_id=str(source_chunk_id),
            )
            status, claim_id, count_key, claim_occurrence_ids = state
            predicate_keys.add(count_key)
            if status == "unresolved":
                if claim_id not in unresolved_claim_ids and claim_id not in accepted_claim_ids:
                    signature = _predicate_signature(count_key)
                    accounted_predicate_counts[signature] = accounted_predicate_counts.get(signature, 0) + 1
                unresolved_claim_ids.add(claim_id)
                continue
            accepted_occurrence_ids.update(claim_occurrence_ids)
            if claim_id not in accepted_claim_ids and claim_id not in unresolved_claim_ids:
                signature = _predicate_signature(count_key)
                accounted_predicate_counts[signature] = accounted_predicate_counts.get(signature, 0) + 1
            accepted_claim_ids.add(claim_id)

    predicate_keys.discard("")
    memory_ids.discard("")
    if unresolved_claim_ids:
        disposition = "unresolved_claims"
        claim_ids = sorted(unresolved_claim_ids | accepted_claim_ids)
        occurrence_ids: list[str] = sorted(accepted_occurrence_ids)
    elif accepted_occurrence_ids:
        disposition = "accepted_occurrences"
        claim_ids = sorted(accepted_claim_ids)
        occurrence_ids = sorted(accepted_occurrence_ids)
    else:
        disposition = "no_occurrence"
        claim_ids = []
        occurrence_ids = []
        predicate_keys.clear()
    accounting_chunk = store.get_source_chunk_for_occurrence_accounting(str(source_chunk_id))
    raw_source_id = accounting_chunk.get("source_id") if isinstance(accounting_chunk, Mapping) else None
    source_id = str(raw_source_id).strip() if isinstance(raw_source_id, (str, UUID)) else ""
    expected_snapshot_sha256 = (
        str(accounting_chunk.get("snapshot_sha256") or "") if isinstance(accounting_chunk, Mapping) else ""
    )
    if (
        not isinstance(accounting_chunk, Mapping)
        or str(accounting_chunk.get("id") or "") != str(source_chunk_id)
        or not source_id
        or not isinstance(accounting_chunk.get("text"), str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_snapshot_sha256) is None
    ):
        raise ContinuityStoreInvariantError(
            "extraction disposition could not resolve its source chunk or signed snapshot"
        )
    raw_no_occurrence_guard = _chunk_has_plausible_unaccounted_user_assertion(
        accounting_chunk,
        accounted_predicate_counts=accounted_predicate_counts,
    )
    bound_claim_ids = sorted(unresolved_claim_ids | accepted_claim_ids)
    claim_facts_digests: dict[str, str] = {}
    for claim_id in bound_claim_ids:
        claim = store.get_occurrence_claim(claim_id)
        if not isinstance(claim, Mapping):
            raise ContinuityStoreInvariantError("extraction disposition lost a bound occurrence claim")
        claim_facts_digests[claim_id] = occurrence_claim_facts_digest(claim)
    row, _created = store.record_occurrence_extraction_disposition(
        source_chunk_id=str(source_chunk_id),
        expected_snapshot_sha256=expected_snapshot_sha256,
        extractor_version=OCCURRENCE_EXTRACTOR_VERSION,
        disposition=disposition,
        predicate_keys=sorted(predicate_keys),
        claim_ids=claim_ids,
        occurrence_ids=occurrence_ids,
        metadata_json={
            "memory_ids": sorted(memory_ids),
            "claim_facts_digests": claim_facts_digests,
            "producer": "vnext_occurrence_write",
            "raw_no_occurrence_guard": raw_no_occurrence_guard,
            "raw_no_occurrence_guard_reason": (
                "plausible_user_assertion_without_durable_occurrence_proposal" if raw_no_occurrence_guard else None
            ),
        },
        actor_type=actor_type,
    )
    if (
        reviewer_id is not None
        and reason is not None
        and row.get("review_status") == "candidate"
        and not raw_no_occurrence_guard
    ):
        row = store.review_occurrence_extraction_disposition(
            disposition_id=str(row["id"]),
            action="accepted",
            reviewer_id=reviewer_id,
            reason=reason,
            expected_review_version=int(cast(int, row.get("review_version", 0))),
            actor_type=actor_type,
        )
    return dict(cast(Mapping[str, object], row))


def _metadata(row: Mapping[str, object]) -> JsonObject:
    value = row.get("metadata_json")
    return dict(cast(Mapping[str, object], value)) if isinstance(value, Mapping) else {}


def _occurrence_proposal_records(metadata: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    """Return the one supported explicit structured proposal record."""

    single = metadata.get(OCCURRENCE_PROPOSAL_METADATA_KEY)
    return (single,) if isinstance(single, Mapping) else ()


def _iso_date(year: int, month: int, day: int) -> str | None:
    try:
        value = datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None
    return value.date().isoformat()


def _reference_datetime(source: Mapping[str, object] | None) -> datetime | None:
    if source is None:
        return None
    metadata = _metadata(source)
    session_date = metadata.get("session_date")
    if isinstance(session_date, datetime):
        return datetime(
            session_date.year,
            session_date.month,
            session_date.day,
            tzinfo=UTC,
        )
    if isinstance(session_date, str) and session_date.strip():
        try:
            stated = datetime.fromisoformat(session_date.strip().replace("Z", "+00:00"))
        except ValueError:
            match = _REFERENCE_DATE.search(session_date)
            if match is not None:
                iso = _iso_date(
                    int(match.group("year")),
                    int(match.group("month")),
                    int(match.group("day")),
                )
                if iso is not None:
                    return datetime.fromisoformat(iso).replace(tzinfo=UTC)
        else:
            # ``session_date`` is a calendar label supplied by the source.
            # Preserve its stated date even when its offset represents a
            # different UTC day.
            return datetime(
                stated.year,
                stated.month,
                stated.day,
                tzinfo=UTC,
            )

    created_at = source.get("source_created_at")
    if isinstance(created_at, datetime):
        parsed = created_at
    elif isinstance(created_at, str) and created_at.strip():
        try:
            parsed = datetime.fromisoformat(created_at.strip().replace("Z", "+00:00"))
        except ValueError:
            match = _REFERENCE_DATE.search(created_at)
            if match is None:
                return None
            iso = _iso_date(
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
            if iso is None:
                return None
            parsed = datetime.fromisoformat(iso).replace(tzinfo=UTC)
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _event_date_range(
    text: str,
    *,
    reference: datetime | None,
) -> tuple[str | None, str | None, bool]:
    """Resolve only dates carried by one event clause.

    The boolean is true for a bounded week/month expression. Such a range is
    useful query evidence, but it is not a reviewed ordinal and therefore must
    remain unmaterialized until a human supplies a stable identity.
    """

    match = _ISO_DATE.search(text)
    if match is not None:
        iso_date_value = _iso_date(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
        )
        if (
            iso_date_value is not None
            and reference is not None
            and datetime.fromisoformat(iso_date_value).date() > reference.date()
        ):
            return None, None, False
        return iso_date_value, iso_date_value, False

    match = _MONTH_DATE.search(text)
    if match is not None:
        year_text = match.group("year")
        if year_text is None and reference is None:
            return None, None, False
        month_date_value = _iso_date(
            int(year_text) if year_text is not None else cast(datetime, reference).year,
            _MONTHS[match.group("month").casefold()],
            int(match.group("day")),
        )
        if (
            month_date_value is not None
            and reference is not None
            and datetime.fromisoformat(month_date_value).date() > reference.date()
        ):
            # A completed event with a yearless future calendar date is
            # ambiguous around year rollover. Never silently choose either
            # the current or previous year.
            return None, None, False
        return month_date_value, month_date_value, False

    match = _SLASH_DATE.search(text)
    if match is not None:
        year_text = match.group("year")
        if year_text is None and reference is None:
            return None, None, False
        month = int(match.group("month"))
        day = int(match.group("day"))
        if month <= 12 and day <= 12:
            # Without an explicit locale, 03/04 is equally March 4 or April 3.
            return None, None, False
        year = int(year_text) if year_text is not None else cast(datetime, reference).year
        if year < 100:
            year += 2000
        slash_date_value = _iso_date(year, month, day)
        if (
            slash_date_value is not None
            and reference is not None
            and datetime.fromisoformat(slash_date_value).date() > reference.date()
        ):
            return None, None, False
        return slash_date_value, slash_date_value, False

    if reference is not None:
        lowered = text.casefold()
        ago = _AGO_PERIOD.search(lowered)
        if ago is not None:
            raw_value = ago.group("value").casefold()
            period_value = int(raw_value) if raw_value.isdigit() else _NUMBER_WORDS[raw_value]
            period = ago.group("period").casefold()
            if period.startswith("day"):
                resolved = reference - timedelta(days=period_value)
            elif period.startswith("week"):
                resolved = reference - timedelta(days=7 * period_value)
            else:
                month_index = reference.year * 12 + (reference.month - 1) - period_value
                year, zero_month = divmod(month_index, 12)
                month = zero_month + 1
                day = min(
                    reference.day,
                    (datetime(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)).day,
                )
                resolved = reference.replace(year=year, month=month, day=day)
            iso = _iso_date(resolved.year, resolved.month, resolved.day)
            return iso, iso, False
        if re.search(r"\byesterday\b", lowered):
            yesterday_value = reference - timedelta(days=1)
            iso = _iso_date(yesterday_value.year, yesterday_value.month, yesterday_value.day)
            return iso, iso, False
        if re.search(r"\btoday\b", lowered):
            iso = _iso_date(reference.year, reference.month, reference.day)
            return iso, iso, False
        weekday = _RELATIVE_WEEKDAY.search(lowered)
        if weekday is not None:
            target = _WEEKDAYS[weekday.group("weekday").casefold()]
            if weekday.group("relative").casefold() == "last":
                delta = (reference.weekday() - target) % 7
                delta = delta or 7
                weekday_value = reference - timedelta(days=delta)
            else:
                weekday_value = reference + timedelta(days=target - reference.weekday())
                if weekday_value.date() > reference.date():
                    return None, None, False
            iso = _iso_date(weekday_value.year, weekday_value.month, weekday_value.day)
            return iso, iso, False
        period = _RELATIVE_PERIOD.search(lowered)
        if period is not None:
            relative = period.group("relative").casefold()
            if period.group("period").casefold() == "week":
                current_start = reference - timedelta(days=reference.weekday())
                start = current_start - timedelta(days=7) if relative == "last" else current_start
                end = start + timedelta(days=6) if relative == "last" else reference
            else:
                if relative == "last":
                    previous_last = reference.replace(day=1) - timedelta(days=1)
                    start = previous_last.replace(day=1)
                    end = previous_last
                else:
                    start = reference.replace(day=1)
                    end = reference
            return (
                _iso_date(start.year, start.month, start.day),
                _iso_date(end.year, end.month, end.day),
                True,
            )
    return None, None, False


def _event_date_is_ambiguous(text: str) -> bool:
    spans = {
        match.span()
        for pattern in (
            _ISO_DATE,
            _MONTH_DATE,
            _SLASH_DATE,
            _RELATIVE_WEEKDAY,
            _RELATIVE_PERIOD,
            _AGO_PERIOD,
        )
        for match in pattern.finditer(text)
    }
    spans.update(
        match.span()
        for match in re.finditer(
            r"\b(?:today|yesterday)\b",
            text,
            re.IGNORECASE,
        )
    )
    return len(spans) > 1 or _ALTERNATIVE_MONTH_DAY.search(text) is not None


def _event_datetime(text: str, *, reference: datetime | None) -> str | None:
    """Backward-compatible exact-date helper used by focused tests."""

    start, _end, _bounded = _event_date_range(text, reference=reference)
    return start


def _natural_quantity(text: str) -> tuple[int, int | None, str]:
    """Parse a natural quantity without treating malformed cues as one.

    ``status`` is ``valid``, ``no_event`` (zero occurrences), or
    ``ambiguous``. Natural text never raises a quantity validation exception;
    structured ``occurrence_input`` retains the strict contract.
    """

    def quantity_value(raw: str) -> int:
        normalized = raw.casefold()
        return int(normalized) if normalized.isdigit() else _NUMBER_WORDS[normalized]

    bounded = _QUANTITY_RANGE.search(text)
    if bounded is not None:
        low = quantity_value(bounded.group("low"))
        high = quantity_value(bounded.group("high"))
        if low == 0 and high == 0:
            return 0, 0, "no_event"
        if low < 1 or high < low or high > 1000:
            return max(low, 1), None, "ambiguous"
        return low, high, "valid"
    if _COMPARATIVE_QUANTITY.search(text) or _VAGUE_QUANTITY.search(text):
        return 1, None, "ambiguous"
    exact_matches = list(_QUANTITY_TIMES.finditer(text))
    if len(exact_matches) > 1:
        return 1, None, "ambiguous"
    if not exact_matches:
        if _ANY_QUANTITY_CUE.search(text):
            return 1, None, "ambiguous"
        return 1, 1, "valid"
    match = exact_matches[0]
    if match.group("at_least") and match.group("exactly"):
        return 1, None, "ambiguous"
    standalone = match.group("standalone")
    value = (
        _NUMBER_WORDS[str(standalone).casefold()]
        if standalone is not None
        else quantity_value(str(match.group("value")))
    )
    if value == 0:
        return 0, 0, "no_event"
    if value > 1000:
        return 1, None, "ambiguous"
    return value, None if match.group("at_least") else value, "valid"


def _quantity(text: str) -> tuple[int, int | None]:
    """Compatibility wrapper for the prior internal helper."""

    quantity_min, quantity_max, status = _natural_quantity(text)
    if status == "no_event":
        return 0, 0
    return quantity_min, quantity_max


def _natural_completed_verb_allowed(value: str) -> bool:
    """Admit one bounded regular-past surface without lemmatizing it.

    The parser intentionally owns no verb-topic allowlist or semantic aliases.
    A syntactic ``-ed``/``-ied`` form may become a review candidate while its
    exact surface remains the predicate leaf.  Ambiguous non-``-ed`` forms
    require structured reviewed input.  Words ending in ``-eed`` are
    base-form morphology (for example ``feed`` and ``seed``), not regular
    past tense.
    """

    verb = " ".join(value.casefold().split())
    if (
        " " in verb
        or re.fullmatch(_ACTION_WORD_PATTERN, verb, re.IGNORECASE) is None
        or verb.endswith("eed")
        or verb == "had"
    ):
        return False
    return len(verb) > 3 and verb.endswith("ed")


def _natural_zero_event_assertion(value: str) -> bool:
    """Return true only for a direct assertion whose object says zero."""

    match = (
        _PERFECT_COMPLETED_EVENT.match(value) or _EMPHATIC_COMPLETED_EVENT.match(value) or _COMPLETED_EVENT.match(value)
    )
    return bool(match is not None and _ZERO_EVENT_OBJECT.match(str(match.group("object"))) is not None)


def _contains_counterfactual_language(value: str) -> bool:
    """Treat ``May`` as a month only when it belongs to a parsed month-date."""

    if _COUNTERFACTUAL_LANGUAGE.search(value):
        return True
    month_spans = [
        match.span("month") for match in _MONTH_DATE.finditer(value) if match.group("month").casefold() == "may"
    ]
    return any(
        not any(start <= match.start() and match.end() <= end for start, end in month_spans)
        for match in _MODAL_MAY.finditer(value)
    )


def _has_past_event_context(value: str) -> bool:
    """Recognize generic past-time syntax without an event-topic lexicon."""

    return _PAST_EVENT_CONTEXT.search(value) is not None or _MONTH_DATE.search(value) is not None


def _has_plausible_first_person_event_assertion(value: str) -> bool:
    """Detect an unparsed past assertion without an action-topic allowlist."""

    return any(
        _natural_completed_verb_allowed(str(match.group("verb")))
        or match.group("contraction") is not None
        or match.group("auxiliary") is not None
        or _has_past_event_context(value)
        for match in _PLAUSIBLE_FIRST_PERSON_EVENT_ASSERTION.finditer(value)
    )


def _predicate_verb(value: str) -> str:
    return canonical_action_leaf(value)


def _predicate_object_projection(
    value: str,
) -> tuple[str, tuple[str, ...], bool]:
    """Project a lexical object head and modifiers without semantic guessing.

    Qualifiers retain every normalized lexical token other than determiners and
    the selected final head.  Because the predicate schema does not encode
    relation structure or word order, prepositional object phrases are marked
    complex so their natural-language claims remain unresolved.
    """

    try:
        tokens = normalize_count_key(value).split()
    except ValueError:
        return "", (), True
    words = [token for token in tokens if not token.isdigit() and token not in _OBJECT_DETERMINERS]
    if not words:
        return "", (), True
    return (
        words[-1],
        tuple(words[:-1]),
        any(token in _OBJECT_RELATION_WORDS for token in words),
    )


def _stable_event_object_referent(value: str) -> str | None:
    """Return a bounded full-phrase event anchor without semantic aliases."""

    normalized = " ".join(unicodedata.normalize("NFKC", value).split()).strip(" ,;:-")
    if not normalized or len(normalized) > 240:
        return None
    try:
        lexical = normalize_count_key(normalized)
    except ValueError:
        return None
    lexical = " ".join(token for token in lexical.split() if token not in _OBJECT_DETERMINERS)
    if not lexical:
        return None
    if lexical in {
        "it",
        "one",
        "one of them",
        "something",
        "anything",
        "that",
        "this",
        "them",
    }:
        return None
    return lexical


def _completed_event_clause_verbs(text: str) -> list[str]:
    """Find subject-led and coordinated completed predicates without guessing."""

    matches: dict[int, str] = {}
    for pattern in (_EVENT_CLAUSE_START, _COORDINATED_EVENT_START):
        for match in pattern.finditer(text):
            verb = " ".join(match.group("verb").casefold().split())
            if _natural_completed_verb_allowed(verb):
                matches.setdefault(match.start(), verb)
    return [matches[position] for position in sorted(matches)]


def _quote_aware_sentence_texts(text: str) -> list[str]:
    """Split sentences without detaching text from its quotation context."""

    sentences: list[str] = []
    quote_stack: list[str] = []
    start = 0

    def word_internal(position: int) -> bool:
        return (
            position > 0 and position + 1 < len(text) and text[position - 1].isalnum() and text[position + 1].isalnum()
        )

    def boundary_after(position: int) -> bool:
        return position + 1 == len(text) or text[position + 1].isspace()

    def append_through(position: int) -> None:
        nonlocal start
        sentence = text[start : position + 1].strip()
        if sentence:
            sentences.append(sentence)
        start = position + 1

    for position, character in enumerate(text):
        closed_quote = False
        if character == "“":
            quote_stack.append("”")
        elif character == "‘":
            quote_stack.append("’")
        elif character in {"”", "’"} and not word_internal(position):
            if quote_stack and quote_stack[-1] == character:
                quote_stack.pop()
                closed_quote = True
        elif character in {'"', "'"} and not word_internal(position):
            if quote_stack and quote_stack[-1] == character:
                quote_stack.pop()
                closed_quote = True
            else:
                quote_stack.append(character)

        if character in ".!?" and not quote_stack and boundary_after(position):
            append_through(position)
        elif (
            closed_quote
            and not quote_stack
            and position > 0
            and text[position - 1] in ".!?"
            and boundary_after(position)
        ):
            append_through(position)

    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _speaker_text_blocks(text: str) -> list[tuple[str | None, str]]:
    """Keep quote state across continuation lines, never across role changes."""

    blocks: list[tuple[str | None, str]] = []
    active_role: str | None = None
    lines: list[str] = []

    def flush() -> None:
        nonlocal lines
        rendered = "\n".join(lines).strip()
        if rendered:
            blocks.append((active_role, rendered))
        lines = []

    for raw_line in text.splitlines() or [text]:
        if not raw_line.strip():
            flush()
            active_role = None
            continue
        tagged = _SPEAKER_TAG.match(raw_line)
        if tagged is not None:
            flush()
            active_role = tagged.group("role").casefold()
            raw_line = raw_line[tagged.end() :]
        lines.append(raw_line)
    flush()
    return blocks


def _natural_sentence_texts(text: str) -> list[str]:
    """Return independently reviewable sentences from user-authored text."""

    sentences: list[str] = []
    for role, block in _speaker_text_blocks(text):
        if role is not None and role not in {"user", "human"}:
            continue
        for raw_sentence in _quote_aware_sentence_texts(block):
            sentence = raw_sentence.strip()
            if sentence:
                sentences.append(sentence)
    return sentences


def _natural_event_sentence_hint(
    sentence: str,
    *,
    source: Mapping[str, object] | None,
) -> JsonObject | None:
    """Extract one direct first-person completed assertion, fail-closed."""

    normalized = sentence.strip()
    if not normalized:
        return None
    if normalized.endswith("?"):
        return None
    lowered = normalized.casefold()
    if (
        _QUESTION_INVERSION.match(lowered)
        or _CONDITIONAL_LANGUAGE.search(lowered)
        or _contains_counterfactual_language(lowered)
        or _ATTRIBUTION_PREFIX.match(lowered)
        or _FIRST_PERSON_ATTRIBUTION_PREFIX.match(lowered)
        or _ATTRIBUTION_TRAILER.search(lowered)
        or re.search(
            r"(?:[\"“][^\"”]*|(?<![a-z0-9])['‘][^'’]*)"
            r"(?:\bi\b|\bwe\b)\s+",
            normalized,
            re.IGNORECASE,
        )
    ):
        return None
    if _NEGATED_EVENT.search(normalized):
        return None

    clause_verbs = _completed_event_clause_verbs(normalized)
    if len(clause_verbs) > 1:
        return {
            "count_key": "compound completed event " + " ".join(clause_verbs),
            "quantity_min": 1,
            "quantity_max": None,
            "force_ambiguous": True,
        }

    nested = _NESTED_COMPLETED_EVENT.match(normalized)
    if nested is not None:
        # "used to VERB" is habitual; only a non-empty instrument/object
        # followed by an action complement entails a completed nested event.
        instrument = " ".join(nested.group("instrument").split()).casefold()
        if instrument == "to" or instrument.endswith(" used"):
            return None
        verb = " ".join(nested.group("verb").casefold().split())
        event_tail = nested.group("object").strip()
    else:
        match = (
            _PERFECT_COMPLETED_EVENT.match(normalized)
            or _EMPHATIC_COMPLETED_EVENT.match(normalized)
            or _COMPLETED_EVENT.match(normalized)
        )
        if match is None:
            return None
        verb = " ".join(match.group("verb").casefold().split())
        if not _natural_completed_verb_allowed(verb):
            return None
        event_tail = match.group("object").strip()

    if _ZERO_EVENT_OBJECT.match(event_tail):
        return None
    ambiguous_object_cardinality = bool(_AMBIGUOUS_EVENT_OBJECT_CARDINALITY.match(event_tail))

    # Context and subordinate clauses are not part of the event object, date,
    # or quantity. An unparsed coordinated predicate is deliberately
    # ambiguous rather than being folded into the first event.
    coordination = _UNPARSED_COORDINATION.search(event_tail)
    force_ambiguous = coordination is not None or ambiguous_object_cardinality
    if coordination is not None:
        event_tail = event_tail[: coordination.start()]
    context = _CLAUSE_CONTEXT_BOUNDARY.search(event_tail)
    context_tail = ""
    if context is not None:
        context_tail = event_tail[context.start() :]
        event_tail = event_tail[: context.start()]
        if _ANY_QUANTITY_CUE.search(context_tail):
            force_ambiguous = True

    quantity_min, quantity_max, quantity_status = _natural_quantity(event_tail)
    if quantity_status == "no_event":
        return None
    if quantity_status == "ambiguous":
        force_ambiguous = True

    event_object = _QUANTITY_OBJECT_TAIL.sub("", event_tail)
    event_object = _TEMPORAL_TAIL.sub("", event_object).strip(" ,;:-")
    if not event_object or event_object.casefold().startswith(("to ", "been ")):
        return None
    predicate_object, predicate_object_qualifiers, complex_object = _predicate_object_projection(event_object)
    if not predicate_object:
        return None
    if complex_object:
        force_ambiguous = True
    stable_referent = _stable_event_object_referent(event_object)
    count_key = f"{_predicate_verb(verb)} {predicate_object}"
    date_ambiguous = _event_date_is_ambiguous(event_tail)
    if date_ambiguous:
        occurred_at_start = occurred_at_end = None
        bounded_date = False
        force_ambiguous = True
    else:
        occurred_at_start, occurred_at_end, bounded_date = _event_date_range(
            event_tail,
            reference=_reference_datetime(source),
        )
    if bounded_date:
        force_ambiguous = True
    return {
        "count_key": count_key,
        "predicate_action": _predicate_verb(verb),
        "predicate_object": predicate_object,
        "predicate_object_qualifiers": list(predicate_object_qualifiers),
        "quantity_min": quantity_min,
        "quantity_max": quantity_max,
        "occurred_at_start": occurred_at_start,
        "occurred_at_end": occurred_at_end,
        "force_ambiguous": force_ambiguous,
        "stable_object": (stable_referent if occurred_at_start is not None and not bounded_date else None),
    }


def _completed_event_hint(
    text: str,
    *,
    source: Mapping[str, object] | None,
) -> JsonObject | None:
    hints = [
        hint
        for sentence in _natural_sentence_texts(text)
        if (hint := _natural_event_sentence_hint(sentence, source=source)) is not None
    ]
    if not hints:
        return None
    if len(hints) > 1:
        return {
            "count_key": "compound completed event " + " ".join(str(hint["count_key"]) for hint in hints),
            "quantity_min": 1,
            "quantity_max": None,
            "force_ambiguous": True,
        }
    return hints[0]


def natural_occurrence_candidate_text(text: str) -> bool:
    """Whether trusted user text contains a conservative event assertion.

    Capture uses this only to retain an otherwise-unrecognized user line as a
    review candidate. It does not materialize a unit and deliberately resolves
    no relative date without the source row.
    """

    return _completed_event_hint(text, source=None) is not None


def natural_occurrence_candidate_sentences(text: str) -> tuple[str, ...]:
    """Return independently reviewable direct-event sentences from user text.

    This is a capture-time carrier split only. It neither accepts a claim nor
    invents an identity: each returned sentence still passes through the
    ordinary proposal and review path. Speaker tags are retained on derived
    carriers so assistant/system text cannot acquire user provenance.
    """

    candidates: list[str] = []
    for role, block in _speaker_text_blocks(text):
        if role is not None and role not in {"user", "human"}:
            continue
        for sentence in _quote_aware_sentence_texts(block):
            sentence = sentence.strip()
            if not sentence or _natural_event_sentence_hint(sentence, source=None) is None:
                continue
            rendered = f"[{role.upper()}]: {sentence}" if role is not None else sentence
            candidates.append(rendered)
    return tuple(dict.fromkeys(candidates))


def _text_digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def occurrence_source_title_snapshot_value(value: object) -> str | None:
    """Mirror the source-title projection bound into extraction snapshots."""

    if not isinstance(value, str) or not value.strip():
        return None
    return " ".join(value.split()).strip().rstrip(".")


def _value_digest(value: object) -> str:
    payload = json.dumps(
        value,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return _text_digest(payload)


def _matching_explicit_hint(
    memory: Mapping[str, object],
    *,
    source: Mapping[str, object] | None,
) -> JsonObject | None:
    memory_metadata = _metadata(memory)
    direct = memory_metadata.get("occurrence_input")
    if isinstance(direct, Mapping):
        return dict(cast(Mapping[str, object], direct))
    if source is None:
        return None
    source_metadata = _metadata(source)
    candidates = source_metadata.get("occurrence_inputs")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        single = source_metadata.get("occurrence_input")
        return dict(cast(Mapping[str, object], single)) if isinstance(single, Mapping) else None
    canonical_text = str(memory.get("canonical_text") or "")
    digest = _text_digest(canonical_text)
    matches: list[JsonObject] = []
    for raw in candidates:
        if not isinstance(raw, Mapping):
            continue
        text_match = raw.get("canonical_text")
        digest_match = raw.get("canonical_text_sha256")
        if text_match is not None and str(text_match) != canonical_text:
            continue
        if digest_match is not None and str(digest_match) != digest:
            continue
        if text_match is None and digest_match is None:
            continue
        matches.append(dict(cast(Mapping[str, object], raw)))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # This carrier deliberately has one proposal slot. Never pick the
        # first structured predicate and imply the memory was fully counted.
        return {
            "count_key": "compound structured occurrence",
            "quantity_min": 1,
            "quantity_max": None,
            "_compound_occurrence_input": True,
        }
    return None


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(text for item in value if (text := " ".join(str(item).split()).strip()))


def _unknown_occurrence_predicate() -> JsonObject:
    return canonicalize_occurrence_predicate(
        {
            "schema": OCCURRENCE_PREDICATE_SCHEMA,
            "taxonomy": OCCURRENCE_PREDICATE_TAXONOMY,
            "op": "unknown",
            "subject": "self",
            "polarity": "completed",
            "selector_keys": [],
            "closure_complete": False,
        },
        allow_claim_ops=True,
    )


def _predicate_for_hint(
    hint: Mapping[str, object],
    *,
    force_ambiguous: bool,
) -> JsonObject:
    supplied = hint.get("predicate_json")
    if supplied is not None:
        return canonicalize_occurrence_predicate(
            supplied,
            allow_claim_ops=True,
        )
    action = str(hint.get("predicate_action") or "").strip()
    event_object = str(hint.get("predicate_object") or "").strip()
    if force_ambiguous or not action or not event_object:
        return _unknown_occurrence_predicate()
    raw_qualifiers = hint.get("predicate_object_qualifiers", ())
    if not isinstance(raw_qualifiers, Sequence) or isinstance(
        raw_qualifiers,
        (str, bytes, bytearray),
    ):
        return _unknown_occurrence_predicate()
    object_qualifiers: list[str] = []
    for raw_qualifier in raw_qualifiers:
        if not isinstance(raw_qualifier, str) or not raw_qualifier.strip():
            return _unknown_occurrence_predicate()
        object_qualifiers.append(raw_qualifier)
    return build_occurrence_predicate_atom(
        action=action,
        object_leaf=event_object,
        object_qualifiers=object_qualifiers,
    )


def _aggregation_for_hint(hint: Mapping[str, object]) -> JsonObject:
    supplied = hint.get("aggregation_json")
    if supplied is not None:
        return canonicalize_occurrence_claim_aggregation(supplied)
    bases: list[JsonObject] = [
        {
            "basis": "event_instance",
            "identity_basis": "occurrence_key",
        }
    ]
    if hint.get("reviewed_stable_object_key") is not None or _string_sequence(hint.get("reviewed_stable_object_keys")):
        bases.append(
            {
                "basis": "object_member",
                "identity_basis": "reviewed_stable_object_v1",
            }
        )
    return canonicalize_occurrence_claim_aggregation(
        {
            "schema": OCCURRENCE_AGGREGATION_SCHEMA,
            "bases": bases,
        }
    )


def _proposal_for_memory(
    memory: Mapping[str, object],
    *,
    source: Mapping[str, object] | None,
    source_chunk_id: str | None,
    existing_occurrence: Mapping[str, object] | None = None,
    proposal_memory_id: str | None | object = _USE_CARRIER_MEMORY_ID,
    allow_natural: bool = False,
) -> JsonObject | None:
    text = str(memory.get("canonical_text") or "").strip()
    memory_metadata = _metadata(memory)
    if not text or isinstance(memory_metadata.get("consolidation"), Mapping):
        return None
    explicit = _matching_explicit_hint(memory, source=source)
    if explicit is None and not allow_natural:
        return None
    provenance_role = str(memory_metadata.get("provenance_role") or "").casefold()
    if explicit is None and provenance_role and provenance_role not in {"user", "human"}:
        return None
    hint = explicit or _completed_event_hint(text, source=source)
    if hint is None:
        return None
    force_ambiguous = bool(hint.get("_compound_occurrence_input")) or (
        explicit is None and bool(hint.get("force_ambiguous"))
    )
    manual_identity = hint.get("reviewed_manual_identity") if explicit is not None else None
    if manual_identity is not None and (not isinstance(manual_identity, str) or not manual_identity.strip()):
        raise ValueError("reviewed_manual_identity must be a non-empty string")
    count_key = str(hint.get("count_key") or "").strip()
    if not count_key:
        return None
    try:
        predicate = _predicate_for_hint(hint, force_ambiguous=force_ambiguous)
    except ValueError:
        if explicit is not None:
            # Structured occurrence inputs remain subject to the strict
            # predicate contract. Natural extraction is only a proposal
            # boundary: an unrepresentable lexical projection must not abort
            # the enclosing source import.
            raise
        predicate = _unknown_occurrence_predicate()
        force_ambiguous = True
    if predicate.get("op") != "atom":
        force_ambiguous = True
    aggregation = _aggregation_for_hint(hint)
    object_member_identities = _string_sequence(hint.get("reviewed_stable_object_keys"))
    source_id = str(source.get("id")) if source is not None and source.get("id") else None
    return build_occurrence_proposal(
        canonical_text=text,
        count_key=count_key,
        predicate_json=predicate,
        aggregation_json=aggregation,
        object_member_identity=cast(
            str | None,
            hint.get("reviewed_stable_object_key"),
        ),
        object_member_identities=object_member_identities,
        domain=str(memory.get("domain") or "unknown"),
        sensitivity=str(memory.get("sensitivity") or "unknown"),
        project_scope=resolve_project_scope(memory).identity,
        occurred_at_start=(None if force_ambiguous else cast(str | None, hint.get("occurred_at_start"))),
        occurred_at_end=(None if force_ambiguous else cast(str | None, hint.get("occurred_at_end"))),
        external_event_id=(None if force_ambiguous else cast(str | None, hint.get("external_event_id"))),
        external_event_namespace=cast(str | None, None if force_ambiguous else hint.get("external_event_namespace")),
        stable_actors=(() if force_ambiguous else _string_sequence(hint.get("stable_actors"))),
        stable_object=(None if force_ambiguous else cast(str | None, hint.get("stable_object"))),
        reviewed_manual_identity=cast(str | None, manual_identity),
        # A single natural event with a resolved date proposes ordinal 1 as a
        # candidate identity. It is not countable until the surrounding
        # memory review accepts the unit, and any same-anchor collision makes
        # the later proposal ambiguous instead of auto-linking.
        reviewed_date_ordinal=cast(
            int | None,
            (
                hint.get("reviewed_date_ordinal")
                if explicit is not None
                else 1
                if not force_ambiguous
                and hint.get("occurred_at_start") is not None
                and hint.get("stable_object") is not None
                else None
            ),
        ),
        quantity_min=cast(int, hint.get("quantity_min", 1)),
        quantity_max=cast(int | None, hint.get("quantity_max", 1)),
        memory_id=(
            str(memory["id"]) if proposal_memory_id is _USE_CARRIER_MEMORY_ID else cast(str | None, proposal_memory_id)
        ),
        source_id=source_id,
        source_chunk_id=source_chunk_id,
        quote=text,
        existing_occurrence=existing_occurrence,
    )


def _datetime_or_none(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _existing_occurrence(
    store: _OccurrenceWriteStore,
    proposal: Mapping[str, object],
) -> Mapping[str, object] | None:
    units = proposal.get("unit_proposals")
    if not isinstance(units, list) or not units:
        return None
    wanted_keys = {str(unit.get("occurrence_key") or "") for unit in units if isinstance(unit, Mapping)}
    wanted_keys.discard("")
    if not wanted_keys:
        return None
    direct = getattr(store, "get_occurrence_unit_by_key", None)
    if callable(direct):
        for occurrence_key in sorted(wanted_keys):
            row = direct(occurrence_key)
            if not isinstance(row, Mapping):
                continue
            claim = store.get_occurrence_claim(str(row.get("claim_id") or ""))
            if isinstance(claim, Mapping) and claim.get("claim_key") == proposal.get("claim_key"):
                continue
            return row
        return None
    search = getattr(store, "search_accepted_occurrence_units", None)
    if not callable(search):
        return None
    rows = search(
        query=str(proposal["count_key"]),
        projects=cast(Sequence[str], proposal.get("project_scope") or ()),
        domains=(str(proposal["domain"]),),
        sensitivity_allowed=(str(proposal["sensitivity"]),),
        occurred_at_start=_datetime_or_none(proposal.get("occurred_at_start")),
        occurred_at_end=_datetime_or_none(proposal.get("occurred_at_end")),
        limit=200,
    )
    for row in rows:
        if isinstance(row, Mapping) and str(row.get("occurrence_key") or "") in wanted_keys:
            claim = store.get_occurrence_claim(str(row.get("claim_id") or ""))
            if isinstance(claim, Mapping) and claim.get("claim_key") == proposal.get("claim_key"):
                continue
            return row
    return None


def _row_and_created(value: object) -> tuple[JsonObject, bool]:
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], Mapping):
        return dict(cast(Mapping[str, object], value[0])), bool(value[1])
    if isinstance(value, Mapping):
        return dict(cast(Mapping[str, object], value)), True
    raise ContinuityStoreInvariantError("occurrence store returned an invalid row")


def _evidence_rows(
    proposal: Mapping[str, object],
    *,
    claim_id: str,
    occurrence_id: str | None,
    occurrence_key: str | None,
    source_snapshot_sha256: str | None = None,
    source_reestablishment_stage: str | None = None,
) -> list[JsonObject]:
    raw_proposals = proposal.get("evidence_proposals")
    if not isinstance(raw_proposals, list) or not raw_proposals:
        raise ContinuityStoreInvariantError("occurrence proposal lacks evidence")
    matches = [
        raw
        for raw in raw_proposals
        if isinstance(raw, Mapping)
        and (
            (occurrence_key is not None and str(raw.get("occurrence_key") or "") == occurrence_key)
            or (occurrence_key is None and str(raw.get("occurrence_id") or "") == str(occurrence_id or ""))
        )
    ]
    if len(matches) != 1:
        raise ContinuityStoreInvariantError("occurrence proposal evidence does not map one-to-one to its target")
    base = dict(cast(Mapping[str, object], matches[0]))
    base_key = str(base["evidence_key"])
    if source_snapshot_sha256 is not None:
        if (
            re.fullmatch(r"[0-9a-f]{64}", source_snapshot_sha256) is None
            or base.get("source_id") is None
            or base.get("source_chunk_id") is None
            or base.get("memory_id") is not None
        ):
            raise ContinuityStoreInvariantError("source occurrence evidence requires a valid current source snapshot")
        base_key = sha256(f"{base_key}:source-snapshot-v1:{source_snapshot_sha256}".encode("utf-8")).hexdigest()
    rows: list[JsonObject] = []

    def add(kind: str, **references: object) -> None:
        rows.append(
            {
                "claim_id": claim_id,
                "occurrence_id": occurrence_id,
                "evidence_key": sha256(f"{base_key}:{kind}:{occurrence_id or 'claim'}".encode("utf-8")).hexdigest(),
                "evidence_role": "supports",
                "quote": base.get("quote"),
                "quote_sha256": base.get("quote_sha256"),
                **references,
                # Evidence identity must replay unchanged when a capture
                # proposal is later accepted. The review stage belongs on the
                # claim/memory receipt, not in this immutable evidence row.
                "metadata_json": {
                    "reference_kind": kind,
                    **(
                        {
                            "source_snapshot_sha256": source_snapshot_sha256,
                            "source_reestablishment_stage": source_reestablishment_stage,
                        }
                        if source_snapshot_sha256 is not None
                        else {}
                    ),
                },
            }
        )

    if base.get("source_id") is not None or base.get("source_chunk_id") is not None:
        add(
            "source",
            source_id=base.get("source_id"),
            source_chunk_id=base.get("source_chunk_id"),
        )
    if base.get("memory_id") is not None:
        add("memory", memory_id=base.get("memory_id"))
    if not rows:
        add("quote")
    return rows


def _current_source_snapshot_sha256(
    store: _OccurrenceWriteStore,
    *,
    source_id: str,
    source_chunk_id: str,
) -> str:
    """Read the store-computed source snapshot used by extraction accounting."""

    read_snapshot = getattr(
        store,
        "get_source_chunk_for_occurrence_accounting",
        None,
    )
    if not callable(read_snapshot):
        raise ContinuityStoreInvariantError("source occurrence evidence requires the current extraction snapshot seam")
    current = read_snapshot(str(source_chunk_id))
    if (
        not isinstance(current, Mapping)
        or str(current.get("id") or "") != str(source_chunk_id)
        or str(current.get("source_id") or "") != str(source_id)
    ):
        raise ContinuityStoreInvariantError("source occurrence evidence is not bound to the current owned chunk")
    snapshot_sha256 = str(current.get("snapshot_sha256") or "")
    if re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256) is None:
        raise ContinuityStoreInvariantError("source occurrence evidence lacks a valid current extraction snapshot")
    return snapshot_sha256


def _persist_evidence(store: _OccurrenceWriteStore, evidence: JsonObject, *, actor_type: str) -> JsonObject:
    metadata = evidence.get("metadata_json")
    source_reestablishment_snapshot_sha256: str | None = None
    if (
        isinstance(metadata, Mapping)
        and metadata.get("source_reestablishment_stage") == "http_source_review_envelope_change"
    ):
        candidate = str(metadata.get("source_snapshot_sha256") or "")
        if re.fullmatch(r"[0-9a-f]{64}", candidate) is not None:
            source_reestablishment_snapshot_sha256 = candidate
    value = store.create_occurrence_evidence(
        evidence,
        actor_type=actor_type,
        _source_reestablishment_snapshot_sha256=(source_reestablishment_snapshot_sha256),
    )
    if isinstance(value, tuple):
        row, _created = _row_and_created(value)
        return row
    if not isinstance(value, Mapping):
        raise ContinuityStoreInvariantError("occurrence evidence store returned an invalid row")
    return dict(cast(Mapping[str, object], value))


def _proposal_record(
    proposal: Mapping[str, object],
    *,
    claim_id: str,
    occurrence_ids: Sequence[str],
    value_sha256: str,
    source_chunk_id: str | None,
    stage: str,
    materialization_status: str,
) -> JsonObject:
    return {
        "claim_id": claim_id,
        "claim_key": proposal["claim_key"],
        "count_key": proposal["count_key"],
        "canonical_text_sha256": _text_digest(str(proposal["canonical_text"])),
        "value_sha256": value_sha256,
        "quantity_min": proposal["quantity_min"],
        "quantity_max": proposal.get("quantity_max"),
        "range_kind": proposal["range_kind"],
        "resolution_decision": proposal["resolution_decision"],
        "resolution_status": proposal["resolution_status"],
        "identity_basis": proposal["identity_basis"],
        "identity_anchor": proposal.get("identity_anchor"),
        "occurred_at_start": proposal.get("occurred_at_start"),
        "occurred_at_end": proposal.get("occurred_at_end"),
        "source_chunk_id": source_chunk_id,
        "occurrence_unit_ids": list(occurrence_ids),
        "materialization_status": materialization_status,
        "stage": stage,
    }


def _write_proposal_metadata(
    store: object,
    memory: Mapping[str, object],
    record: JsonObject,
    *,
    actor_type: str,
) -> JsonObject:
    metadata = _metadata(memory)
    return _persist_occurrence_memory_metadata(
        store,
        memory,
        {
            **metadata,
            OCCURRENCE_PROPOSAL_METADATA_KEY: record,
        },
        actor_type=actor_type,
    )


def _persist_occurrence_memory_metadata(
    store: object,
    memory: Mapping[str, object],
    metadata: Mapping[str, object],
    *,
    actor_type: str,
) -> JsonObject:
    """CAS-write internal occurrence metadata without changing memory recency."""

    expected = memory.get("_occurrence_expected_metadata_json")
    expected_metadata = (
        dict(cast(Mapping[str, object], expected)) if isinstance(expected, Mapping) else _metadata(memory)
    )
    occurrence_update = getattr(store, "write_occurrence_memory_metadata", None)
    if callable(occurrence_update):
        updated = occurrence_update(
            memory_id=str(memory["id"]),
            metadata_json=dict(metadata),
            expected_metadata_json=expected_metadata,
            actor_type=actor_type,
        )
    else:
        update = getattr(store, "update_memory", None)
        if not callable(update):
            raise ContinuityStoreInvariantError("occurrence-capable store lacks the memory metadata update seam")
        updated = update(
            memory_id=str(memory["id"]),
            patch={"metadata_json": dict(metadata)},
            actor_type=actor_type,
        )
    if not isinstance(updated, Mapping):
        raise ContinuityStoreInvariantError("occurrence memory metadata update returned an invalid row")
    return dict(cast(Mapping[str, object], updated))


def _invalidate_occurrence_metadata(
    store: object,
    memory: Mapping[str, object],
    previous_record: Mapping[str, object],
    *,
    stage: str,
    actor_type: str,
) -> JsonObject:
    """Remove stale write hints and leave a deterministic invalidation receipt."""

    metadata = _metadata(memory)
    metadata.pop("occurrence_input", None)
    metadata.pop(OCCURRENCE_PROPOSAL_METADATA_KEY, None)
    metadata.pop("occurrence_proposals", None)
    metadata.pop("occurrence_candidate_texts", None)
    metadata[OCCURRENCE_INVALIDATION_METADATA_KEY] = {
        "claim_id": previous_record.get("claim_id"),
        "claim_key": previous_record.get("claim_key"),
        "canonical_text_sha256": previous_record.get("canonical_text_sha256"),
        "value_sha256": previous_record.get("value_sha256"),
        "replacement_canonical_text_sha256": _text_digest(str(memory.get("canonical_text") or "")),
        "replacement_value_sha256": _value_digest(memory.get("value")),
        "reason": "memory_content_changed",
        "stage": stage,
    }
    updated = _persist_occurrence_memory_metadata(
        store,
        memory,
        metadata,
        actor_type=actor_type,
    )
    if not isinstance(updated, Mapping):
        raise ContinuityStoreInvariantError("occurrence metadata invalidation returned an invalid row")
    return dict(cast(Mapping[str, object], updated))


def _review_new_units(
    store: _OccurrenceWriteStore,
    *,
    claim: Mapping[str, object],
    units: Sequence[Mapping[str, object]],
    reviewer_id: str,
    reason: str,
    actor_type: str,
) -> None:
    if not units:
        raise ContinuityStoreInvariantError("resolved new occurrence claim has no units")
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="new",
        identity_basis=str(claim["identity_basis"]),
        reviewer_id=reviewer_id,
        reason=reason,
        expected_review_version=int(cast(int, claim.get("review_version", 0))),
        # A resolved ``new`` claim owns all of its proposed units.  Pointing
        # at the first unit silently singularizes plural statements and is
        # rejected by the persistence invariant.
        resolved_occurrence_id=None,
        actor_type=actor_type,
    )
    for unit in units:
        store.review_occurrence_unit(
            occurrence_id=str(unit["id"]),
            action="accepted",
            reason=reason,
            reviewer_id=reviewer_id,
            expected_status="candidate",
            expected_review_version=int(cast(int, unit.get("review_version", 0))),
            actor_type=actor_type,
        )


def _review_link_existing(
    store: _OccurrenceWriteStore,
    *,
    claim: Mapping[str, object],
    occurrence: Mapping[str, object],
    reviewer_id: str,
    reason: str,
    actor_type: str,
) -> None:
    store.review_occurrence_claim(
        claim_id=str(claim["id"]),
        resolution_status="resolved",
        resolution_decision="link_existing",
        identity_basis=str(claim["identity_basis"]),
        reviewer_id=reviewer_id,
        reason=reason,
        expected_review_version=int(cast(int, claim.get("review_version", 0))),
        resolved_occurrence_id=str(occurrence["id"]),
        actor_type=actor_type,
    )
    refresh = getattr(store, "refresh_occurrence_unit_evidence", None)
    if not callable(refresh):
        raise ContinuityStoreInvariantError("link_existing requires an accepted-unit evidence refresh seam")
    refresh(
        occurrence_id=str(occurrence["id"]),
        reason=reason,
        reviewer_id=reviewer_id,
        expected_review_version=int(cast(int, occurrence.get("review_version", 0))),
        actor_type=actor_type,
    )


def establish_memory_occurrences(
    store: object,
    memory: Mapping[str, object],
    *,
    source: Mapping[str, object] | None = None,
    source_chunk_id: str | None = None,
    accepted: bool,
    reviewer_id: str,
    reason: str,
    actor_type: str,
    stage: str,
    _reconciled_source_chunk_ids: set[str] | None = None,
) -> JsonObject:
    """Persist and optionally materialize one memory's occurrence proposal.

    A non-occurrence memory or a legacy store is returned unchanged.  Once the
    occurrence seam exists, persistence/review failures propagate so the
    surrounding memory transaction rolls back instead of leaving a false
    accepted memory without its truth-critical occurrence decision.
    """

    if not occurrence_writes_supported(store):
        return dict(memory)
    _lock_occurrence_write_graph(store)
    metadata = _metadata(memory)
    if any(key in metadata for key in ("occurrence_candidate_texts", "occurrence_proposals")):
        # Strip obsolete user-injectable internal keys without interpreting
        # their content.
        metadata.pop("occurrence_candidate_texts", None)
        metadata.pop("occurrence_proposals", None)
        memory = _persist_occurrence_memory_metadata(
            store,
            memory,
            metadata,
            actor_type=actor_type,
        )
    existing_record = _metadata(memory).get(OCCURRENCE_PROPOSAL_METADATA_KEY)
    existing_materialization = (
        str(existing_record.get("materialization_status") or "") if isinstance(existing_record, Mapping) else ""
    )
    accounting_invalidation_required = accepted and existing_materialization not in {
        "accepted",
        "linked_existing",
    }
    accounting_invalidation_chunk_id = str(_metadata(memory).get("source_chunk_id") or source_chunk_id or "")
    text_digest = _text_digest(str(memory.get("canonical_text") or ""))
    value_digest = _value_digest(memory.get("value"))
    content_changed = False
    if isinstance(existing_record, Mapping):
        old_digest = str(existing_record.get("canonical_text_sha256") or "")
        old_value_digest = str(existing_record.get("value_sha256") or "")
        content_changed = bool(
            (old_digest and old_digest != text_digest) or (old_value_digest and old_value_digest != value_digest)
        )
        if content_changed:
            retire_memory_occurrences(
                store,
                memory,
                reviewer_id=reviewer_id,
                reason="Occurrence proposal retired because accepted memory text changed.",
                actor_type=actor_type,
            )
            memory = _invalidate_occurrence_metadata(
                store,
                memory,
                existing_record,
                stage=stage,
                actor_type=actor_type,
            )
            # The prior source and any unbound structured hint describe the
            # pre-edit assertion. A corrected memory must earn its next
            # proposal from the corrected text itself.
            source = None
            source_chunk_id = None
            existing_record = None

    proposal = _proposal_for_memory(
        memory,
        source=source,
        source_chunk_id=source_chunk_id,
    )
    if proposal is None:
        if accounting_invalidation_required:
            invalidate_occurrence_accounting(
                store,
                reason=(f"Accepted memory occurrence accounting changed during {stage}."),
                actor_type=actor_type,
                actor_id=reviewer_id,
                source_chunk_id=accounting_invalidation_chunk_id or None,
            )
        return dict(memory)
    if (
        isinstance(existing_record, Mapping)
        and existing_record.get("claim_key")
        and existing_record.get("claim_key") != proposal.get("claim_key")
    ):
        retire_memory_occurrences(
            store,
            memory,
            reviewer_id=reviewer_id,
            reason="Pending occurrence identity was replaced by the accepted review decision.",
            actor_type=actor_type,
        )
    existing_occurrence = _existing_occurrence(store, proposal)
    if existing_occurrence is not None:
        proposal = _proposal_for_memory(
            memory,
            source=source,
            source_chunk_id=source_chunk_id,
            existing_occurrence=existing_occurrence,
        )
        if proposal is None:
            raise ContinuityStoreInvariantError("occurrence proposal disappeared during dedupe")

    store.ensure_occurrence_coverage(actor_type=actor_type)
    claim_payload = {
        key: value
        for key, value in proposal.items()
        if key
        not in {
            "unit_proposals",
            "evidence_proposals",
            "identity_anchor",
            "resolved_occurrence_id",
        }
    }
    claim_payload["metadata_json"] = {
        "memory_id": str(memory["id"]),
        "stage": stage,
        "canonical_text_sha256": text_digest,
        "identity_anchor": proposal.get("identity_anchor"),
    }
    claim, _created = _row_and_created(
        store.get_or_create_occurrence_claim(
            claim_payload,
            actor_type=actor_type,
        )
    )

    unit_rows: list[JsonObject] = []
    unit_occurrence_keys: list[str] = []
    raw_units = proposal.get("unit_proposals")
    if isinstance(raw_units, list):
        for raw_unit in raw_units:
            if not isinstance(raw_unit, Mapping):
                raise ContinuityStoreInvariantError("occurrence proposal returned an invalid unit")
            unit_payload = {
                **dict(cast(Mapping[str, object], raw_unit)),
                "claim_id": str(claim["id"]),
                "metadata_json": {
                    "memory_id": str(memory["id"]),
                    "stage": stage,
                },
            }
            unit, _unit_created = _row_and_created(
                store.get_or_create_occurrence_unit(
                    unit_payload,
                    actor_type=actor_type,
                )
            )
            unit_rows.append(unit)
            unit_occurrence_keys.append(str(raw_unit["occurrence_key"]))

    resolved_existing = existing_occurrence if proposal.get("resolution_decision") == "link_existing" else None
    evidence_targets: list[tuple[str | None, str | None]]
    if unit_rows:
        evidence_targets = [
            (str(unit["id"]), occurrence_key)
            for unit, occurrence_key in zip(
                unit_rows,
                unit_occurrence_keys,
                strict=True,
            )
        ]
    elif resolved_existing is not None:
        evidence_targets = [(str(resolved_existing["id"]), None)]
    else:
        evidence_targets = [(None, None)]
    for occurrence_id, occurrence_key in evidence_targets:
        for evidence in _evidence_rows(
            proposal,
            claim_id=str(claim["id"]),
            occurrence_id=occurrence_id,
            occurrence_key=occurrence_key,
        ):
            _persist_evidence(store, evidence, actor_type=actor_type)

    materialization_status = "pending_review"
    occurrence_ids = [
        *(str(unit["id"]) for unit in unit_rows),
        *([str(resolved_existing["id"])] if resolved_existing is not None else []),
    ]
    if accepted:
        current_claim = store.get_occurrence_claim(str(claim["id"])) or claim
        if str(current_claim.get("review_status") or "") == "accepted":
            materialization_status = "accepted"
        elif proposal.get("resolution_decision") == "new":
            _review_new_units(
                store,
                claim=current_claim,
                units=unit_rows,
                reviewer_id=reviewer_id,
                reason=reason,
                actor_type=actor_type,
            )
            materialization_status = "accepted"
        elif proposal.get("resolution_decision") == "link_existing":
            if resolved_existing is None:
                raise ContinuityStoreInvariantError("link_existing occurrence proposal lacks its target")
            _review_link_existing(
                store,
                claim=current_claim,
                occurrence=resolved_existing,
                reviewer_id=reviewer_id,
                reason=reason,
                actor_type=actor_type,
            )
            materialization_status = "linked_existing"
        else:
            if int(cast(int, current_claim.get("review_version", 0))) == 0:
                store.review_occurrence_claim(
                    claim_id=str(current_claim["id"]),
                    resolution_status="pending",
                    resolution_decision="ambiguous",
                    identity_basis="ambiguous",
                    reviewer_id=reviewer_id,
                    reason=reason,
                    expected_review_version=0,
                    resolved_occurrence_id=None,
                    actor_type=actor_type,
                )
            materialization_status = "ambiguous"

    record = _proposal_record(
        proposal,
        claim_id=str(claim["id"]),
        occurrence_ids=occurrence_ids,
        value_sha256=value_digest,
        source_chunk_id=source_chunk_id,
        stage=stage,
        materialization_status=materialization_status,
    )
    updated = _write_proposal_metadata(
        store,
        memory,
        record,
        actor_type=actor_type,
    )
    if accounting_invalidation_required:
        invalidate_occurrence_accounting(
            store,
            reason=(f"Accepted memory occurrence accounting changed during {stage}."),
            actor_type=actor_type,
            actor_id=reviewer_id,
            source_chunk_id=accounting_invalidation_chunk_id or None,
        )
    accounting_chunk_id = str(_metadata(updated).get("source_chunk_id") or source_chunk_id or "")
    if accepted and accounting_chunk_id:
        disposition = reconcile_chunk_extraction_disposition(
            store,
            source_chunk_id=accounting_chunk_id,
            actor_type=actor_type,
            reviewer_id=reviewer_id,
            reason=f"{reason} Extraction disposition reviewed with accepted memory.",
        )
        if disposition is not None and _reconciled_source_chunk_ids is not None:
            _reconciled_source_chunk_ids.add(accounting_chunk_id)
    return updated


def establish_source_chunk_occurrences(
    store: object,
    *,
    source: Mapping[str, object],
    source_chunk: Mapping[str, object],
    actor_type: str,
    stage: str = "source_capture",
) -> list[JsonObject]:
    """Persist dormant occurrence proposals directly on source evidence.

    This path intentionally creates no ordinary memory and performs no
    acceptance. A later explicit source-review pass may resolve the candidate
    claims and units through the same receipt-bearing review seams.
    """

    if not occurrence_writes_supported(store):
        return []
    _lock_occurrence_write_graph(store)
    typed_store = cast(_OccurrenceWriteStore, store)
    source_id = str(source.get("id") or "")
    source_chunk_id = str(source_chunk.get("id") or "")
    if not source_id or not source_chunk_id or str(source_chunk.get("source_id") or "") != source_id:
        raise ContinuityStoreInvariantError("source occurrence carrier is not owned by its source")
    candidate_texts = natural_occurrence_candidate_sentences(str(source_chunk.get("text") or ""))
    if not candidate_texts:
        return []

    source_metadata = _metadata(source)
    source_provenance_role = str(source_metadata.get("provenance_role") or "").casefold()
    source_scope = resolve_project_scope(source).identity
    source_snapshot_sha256 = _current_source_snapshot_sha256(
        typed_store,
        source_id=source_id,
        source_chunk_id=source_chunk_id,
    )
    records: list[JsonObject] = []
    for candidate_text in candidate_texts:
        tagged = _SPEAKER_TAG.match(candidate_text)
        provenance_role = tagged.group("role").casefold() if tagged is not None else source_provenance_role
        if provenance_role not in {"user", "human"}:
            # Unknown untagged connector prose is not owner-authored merely
            # because it happens to use first person.
            continue
        carrier: JsonObject = {
            # The synthetic id is never persisted or hashed into occurrence
            # identity; it exists only to satisfy the in-memory carrier shape.
            "id": f"source-chunk:{source_chunk_id}:{_text_digest(candidate_text)}",
            "canonical_text": candidate_text,
            "value": {
                "text": candidate_text,
                "source_id": source_id,
                "source_chunk_id": source_chunk_id,
            },
            "domain": str(source.get("domain") or "unknown"),
            "sensitivity": str(source.get("sensitivity") or "unknown"),
            "project_id": source_scope[0] if len(source_scope) == 1 else None,
            "metadata_json": {
                "source_id": source_id,
                "source_chunk_id": source_chunk_id,
                "provenance_role": provenance_role,
                "project_scope": list(source_scope),
                "session_date": source_metadata.get("session_date"),
            },
        }
        proposal = _proposal_for_memory(
            carrier,
            source=source,
            source_chunk_id=source_chunk_id,
            proposal_memory_id=None,
            allow_natural=True,
        )
        if proposal is None:
            continue
        existing_occurrence = _existing_occurrence(typed_store, proposal)
        if existing_occurrence is not None:
            proposal = _proposal_for_memory(
                carrier,
                source=source,
                source_chunk_id=source_chunk_id,
                existing_occurrence=existing_occurrence,
                proposal_memory_id=None,
                allow_natural=True,
            )
            if proposal is None:
                raise ContinuityStoreInvariantError("source occurrence proposal disappeared during dedupe")

        typed_store.ensure_occurrence_coverage(actor_type=actor_type)
        claim_payload = {
            key: value
            for key, value in proposal.items()
            if key
            not in {
                "unit_proposals",
                "evidence_proposals",
                "identity_anchor",
                "resolved_occurrence_id",
            }
        }
        claim_payload["metadata_json"] = {
            "carrier_kind": "source_chunk",
            "source_id": source_id,
            "source_chunk_id": source_chunk_id,
            "stage": stage,
            "canonical_text_sha256": _text_digest(candidate_text),
            "identity_anchor": proposal.get("identity_anchor"),
            "proposed_resolved_occurrence_id": proposal.get("resolved_occurrence_id"),
        }
        claim, _created = _row_and_created(
            typed_store.get_or_create_occurrence_claim(
                claim_payload,
                actor_type=actor_type,
            )
        )

        unit_rows: list[JsonObject] = []
        raw_units = proposal.get("unit_proposals")
        if isinstance(raw_units, list):
            for raw_unit in raw_units:
                if not isinstance(raw_unit, Mapping):
                    raise ContinuityStoreInvariantError("source occurrence proposal returned an invalid unit")
                unit, _unit_created = _row_and_created(
                    typed_store.get_or_create_occurrence_unit(
                        {
                            **dict(cast(Mapping[str, object], raw_unit)),
                            "claim_id": str(claim["id"]),
                            "metadata_json": {
                                "carrier_kind": "source_chunk",
                                "source_id": source_id,
                                "source_chunk_id": source_chunk_id,
                                "stage": stage,
                            },
                        },
                        actor_type=actor_type,
                    )
                )
                unit_rows.append(unit)

        resolved_existing = existing_occurrence if proposal.get("resolution_decision") == "link_existing" else None
        evidence_targets: list[tuple[str | None, str | None]]
        if unit_rows:
            evidence_targets = [
                (str(unit["id"]), str(raw_unit["occurrence_key"]))
                for unit, raw_unit in zip(
                    unit_rows,
                    cast(list[Mapping[str, object]], raw_units),
                    strict=True,
                )
            ]
        elif resolved_existing is not None:
            evidence_targets = [(str(resolved_existing["id"]), None)]
        else:
            evidence_targets = [(None, None)]
        for occurrence_id, occurrence_key in evidence_targets:
            for evidence in _evidence_rows(
                proposal,
                claim_id=str(claim["id"]),
                occurrence_id=occurrence_id,
                occurrence_key=occurrence_key,
                source_snapshot_sha256=source_snapshot_sha256,
                source_reestablishment_stage=stage,
            ):
                if evidence.get("memory_id") is not None:
                    raise ContinuityStoreInvariantError("source occurrence evidence acquired a memory carrier")
                _persist_evidence(
                    typed_store,
                    evidence,
                    actor_type=actor_type,
                )
        records.append(
            _proposal_record(
                proposal,
                claim_id=str(claim["id"]),
                occurrence_ids=[
                    *(str(unit["id"]) for unit in unit_rows),
                    *([str(resolved_existing["id"])] if resolved_existing is not None else []),
                ],
                value_sha256=_value_digest(carrier["value"]),
                source_chunk_id=source_chunk_id,
                stage=stage,
                materialization_status="pending_review",
            )
        )
    return records


def review_source_chunk_occurrences(
    store: object,
    *,
    source_chunk_id: str,
    reviewer_id: str,
    reason: str,
    actor_type: str,
    stage: str = "source_review",
    _defer_occurrence_accounting: bool = False,
) -> list[str]:
    """Review every bounded direct source claim without creating memories."""

    if not occurrence_writes_supported(store):
        return []
    _lock_occurrence_write_graph(store)
    typed_store = cast(_OccurrenceWriteStore, store)
    claims = typed_store.list_occurrence_claims_for_source_chunk(
        str(source_chunk_id),
        limit=201,
    )
    if len(claims) > OCCURRENCE_EXTRACTION_MEMORY_LIMIT:
        raise ContinuityStoreInvariantError("source chunk occurrence review exceeds the bounded claim limit")
    reviewed_ids: list[str] = []
    for raw_claim in claims:
        if not isinstance(raw_claim, Mapping):
            raise ContinuityStoreInvariantError("source chunk occurrence review returned an invalid claim")
        claim = dict(cast(Mapping[str, object], raw_claim))
        claim_id = str(claim.get("id") or "")
        if not claim_id:
            raise ContinuityStoreInvariantError("source chunk occurrence review returned an id-less claim")
        if claim.get("review_status") == "accepted":
            units = [
                dict(cast(Mapping[str, object], row))
                for row in typed_store.list_occurrence_units_for_claim(claim_id)
                if isinstance(row, Mapping)
            ]
            for unit in units:
                unit_status = str(unit.get("review_status") or "")
                if unit_status == "accepted":
                    continue
                if unit_status != "retired":
                    raise ContinuityStoreInvariantError("accepted source occurrence claim owns a non-reviewable unit")
                reestablish = getattr(
                    typed_store,
                    "reestablish_source_occurrence_unit",
                    None,
                )
                if not callable(reestablish):
                    raise ContinuityStoreInvariantError(
                        "source occurrence replay requires the guarded re-establishment seam"
                    )
                reestablish(
                    occurrence_id=str(unit["id"]),
                    source_chunk_id=str(source_chunk_id),
                    stage=stage,
                    reason=reason,
                    reviewer_id=reviewer_id,
                    expected_review_version=int(cast(int, unit.get("review_version", 0))),
                    actor_type=actor_type,
                )
            reviewed_ids.append(claim_id)
            continue
        if claim.get("review_status") != "candidate" or claim.get("resolution_status") != "pending":
            continue
        units = [
            dict(cast(Mapping[str, object], row))
            for row in typed_store.list_occurrence_units_for_claim(claim_id)
            if isinstance(row, Mapping)
        ]
        decision = str(claim.get("resolution_decision") or "ambiguous")
        if decision == "new" and units:
            _review_new_units(
                typed_store,
                claim=claim,
                units=units,
                reviewer_id=reviewer_id,
                reason=reason,
                actor_type=actor_type,
            )
        elif decision == "ambiguous":
            linked = _review_source_collision_as_existing(
                typed_store,
                claim=claim,
                source_chunk_id=str(source_chunk_id),
                reviewer_id=reviewer_id,
                reason=reason,
                actor_type=actor_type,
                stage=stage,
            )
            if not linked:
                typed_store.review_occurrence_claim(
                    claim_id=claim_id,
                    resolution_status="pending",
                    resolution_decision="ambiguous",
                    identity_basis=str(claim.get("identity_basis") or "ambiguous"),
                    reviewer_id=reviewer_id,
                    reason=reason,
                    expected_review_version=int(cast(int, claim.get("review_version", 0))),
                    resolved_occurrence_id=None,
                    actor_type=actor_type,
                )
        else:
            # Source-only automatic review deliberately does not guess a link
            # target or repair a malformed strong proposal.
            continue
        reviewed_ids.append(claim_id)

    if not _defer_occurrence_accounting:
        reconcile_chunk_extraction_disposition(
            typed_store,
            source_chunk_id=str(source_chunk_id),
            actor_type=actor_type,
            reviewer_id=reviewer_id,
            reason=f"{reason} Extraction disposition reviewed during {stage}.",
        )
    return reviewed_ids


def _review_source_collision_as_existing(
    store: _OccurrenceWriteStore,
    *,
    claim: Mapping[str, object],
    source_chunk_id: str,
    reviewer_id: str,
    reason: str,
    actor_type: str,
    stage: str,
) -> bool:
    """Revalidate a strong-key collision after earlier chunks were reviewed."""

    get_chunk = getattr(
        store,
        "get_source_chunk_for_occurrence_accounting",
        None,
    )
    get_source = getattr(store, "get_source", None)
    if not callable(get_chunk) or not callable(get_source):
        return False
    chunk = get_chunk(source_chunk_id)
    if not isinstance(chunk, Mapping):
        return False
    source_id = str(chunk.get("source_id") or "")
    source = get_source(source_id) if source_id else None
    if not isinstance(source, Mapping):
        return False
    canonical_text = str(claim.get("canonical_text") or "").strip()
    if not canonical_text:
        return False
    tagged = _SPEAKER_TAG.match(canonical_text)
    provenance_role = (
        tagged.group("role").casefold()
        if tagged is not None
        else str(_metadata(source).get("provenance_role") or "").casefold()
    )
    if provenance_role not in {"user", "human"}:
        return False
    source_scope = resolve_project_scope(source).identity
    carrier: JsonObject = {
        "id": (f"source-chunk:{source_chunk_id}:{_text_digest(canonical_text)}"),
        "canonical_text": canonical_text,
        "value": {
            "text": canonical_text,
            "source_id": source_id,
            "source_chunk_id": source_chunk_id,
        },
        "domain": str(claim.get("domain") or "unknown"),
        "sensitivity": str(claim.get("sensitivity") or "unknown"),
        "project_id": source_scope[0] if len(source_scope) == 1 else None,
        "metadata_json": {
            "source_id": source_id,
            "source_chunk_id": source_chunk_id,
            "provenance_role": provenance_role,
            "project_scope": list(source_scope),
            "session_date": _metadata(source).get("session_date"),
        },
    }
    candidate = _proposal_for_memory(
        carrier,
        source=source,
        source_chunk_id=source_chunk_id,
        proposal_memory_id=None,
        allow_natural=True,
    )
    if candidate is None or candidate.get("claim_key") != claim.get("claim_key"):
        return False
    existing = _existing_occurrence(store, candidate)
    if not isinstance(existing, Mapping) or existing.get("review_status") != "accepted":
        return False
    linked = _proposal_for_memory(
        carrier,
        source=source,
        source_chunk_id=source_chunk_id,
        existing_occurrence=existing,
        proposal_memory_id=None,
        allow_natural=True,
    )
    if (
        linked is None
        or linked.get("claim_key") != claim.get("claim_key")
        or linked.get("resolution_decision") != "link_existing"
        or linked.get("resolved_occurrence_id") != existing.get("id")
    ):
        return False
    for evidence in _evidence_rows(
        linked,
        claim_id=str(claim["id"]),
        occurrence_id=str(existing["id"]),
        occurrence_key=None,
        source_snapshot_sha256=_current_source_snapshot_sha256(
            store,
            source_id=source_id,
            source_chunk_id=source_chunk_id,
        ),
        source_reestablishment_stage=stage,
    ):
        if evidence.get("memory_id") is not None:
            return False
        evidence_metadata = evidence.get("metadata_json")
        evidence["metadata_json"] = {
            **(dict(cast(Mapping[str, object], evidence_metadata)) if isinstance(evidence_metadata, Mapping) else {}),
            "stage": stage,
        }
        _persist_evidence(store, evidence, actor_type=actor_type)
    _review_link_existing(
        store,
        claim=claim,
        occurrence=existing,
        reviewer_id=reviewer_id,
        reason=reason,
        actor_type=actor_type,
    )
    return True


def _retire_units(
    store: _OccurrenceWriteStore,
    rows: Sequence[Mapping[str, object]],
    *,
    reviewer_id: str,
    reason: str,
    actor_type: str,
    _defer_occurrence_accounting: bool = False,
) -> list[str]:
    retired: list[str] = []
    for row in rows:
        status = str(row.get("review_status") or "")
        occurrence_id = str(row.get("id") or "")
        if not occurrence_id or status in {"retired", "rejected", "superseded"}:
            continue
        action = "retired" if status == "accepted" else "rejected"
        if status not in {"accepted", "candidate"}:
            raise ContinuityStoreInvariantError(f"cannot retire occurrence unit from status {status or 'unknown'}")
        store.review_occurrence_unit(
            occurrence_id=occurrence_id,
            action=action,
            reason=reason,
            reviewer_id=reviewer_id,
            expected_status=status,
            expected_review_version=int(cast(int, row.get("review_version", 0))),
            actor_type=actor_type,
            _defer_occurrence_accounting=_defer_occurrence_accounting,
        )
        retired.append(occurrence_id)
    return retired


def retire_memory_occurrences(
    store: object,
    memory: Mapping[str, object],
    *,
    reviewer_id: str,
    reason: str,
    actor_type: str,
    reconcile_claim_evidence: bool = True,
    _defer_occurrence_accounting: bool = False,
) -> list[str]:
    """Retire every proposed/accepted unit governed by ``memory``."""

    if not occurrence_writes_supported(store):
        return []
    _lock_occurrence_write_graph(store)
    metadata = _metadata(memory)
    proposals = _occurrence_proposal_records(metadata)
    claim_ids = list(
        dict.fromkeys(
            str(proposal.get("claim_id") or "") for proposal in proposals if str(proposal.get("claim_id") or "")
        )
    )
    accounting_chunk_id = str(
        next(
            (str(proposal.get("source_chunk_id")) for proposal in proposals if proposal.get("source_chunk_id")),
            "",
        )
        or metadata.get("source_chunk_id")
        or ""
    )
    if claim_ids and reconcile_claim_evidence:
        outcomes = [
            outcome
            for claim_id in claim_ids
            for outcome in store.reconcile_occurrence_claim_evidence(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                reason=reason,
                actor_type=actor_type,
                _defer_occurrence_accounting=_defer_occurrence_accounting,
            )
        ]
    else:
        # Consolidation promotion deliberately preserves the reviewed claim:
        # the accepted candidate is attached first, then only the retiring
        # member carrier is detached and the unit is re-signed.
        outcomes = store.reconcile_occurrence_evidence_carrier(
            memory_id=str(memory["id"]),
            reviewer_id=reviewer_id,
            reason=reason,
            actor_type=actor_type,
            _defer_occurrence_accounting=_defer_occurrence_accounting,
        )
    retired = [
        str(outcome["occurrence_id"])
        for outcome in outcomes
        if isinstance(outcome, Mapping) and outcome.get("occurrence_id")
    ]
    for claim_id in claim_ids:
        claim = store.get_occurrence_claim(claim_id)
        if (
            reconcile_claim_evidence
            and isinstance(claim, Mapping)
            and claim.get("review_status") == "candidate"
            and claim.get("resolution_status") == "pending"
        ):
            # Strong pre-review proposals may already own candidate units.
            # Reject those claim-owned units even when an independent source
            # evidence row survives the memory carrier reconciliation.
            retired.extend(
                _retire_units(
                    store,
                    store.list_occurrence_units_for_claim(claim_id),
                    reviewer_id=reviewer_id,
                    reason=reason,
                    actor_type=actor_type,
                    _defer_occurrence_accounting=_defer_occurrence_accounting,
                )
            )
            store.review_occurrence_claim(
                claim_id=claim_id,
                resolution_status="rejected",
                resolution_decision=str(claim.get("resolution_decision") or "ambiguous"),
                identity_basis=str(claim.get("identity_basis") or "ambiguous"),
                reviewer_id=reviewer_id,
                reason=reason,
                expected_review_version=int(cast(int, claim.get("review_version", 0))),
                resolved_occurrence_id=None,
                actor_type=actor_type,
                _defer_occurrence_accounting=_defer_occurrence_accounting,
            )
    if not _defer_occurrence_accounting:
        invalidate_occurrence_accounting(
            store,
            reason=reason,
            actor_type=actor_type,
            actor_id=reviewer_id,
            source_chunk_id=accounting_chunk_id or None,
        )
        if accounting_chunk_id:
            reconcile_chunk_extraction_disposition(
                store,
                source_chunk_id=accounting_chunk_id,
                actor_type=actor_type,
                reviewer_id=reviewer_id,
                reason=f"{reason} Extraction disposition reconciled.",
            )
    return list(dict.fromkeys(retired))


def retire_source_occurrences(
    store: object,
    source_id: str,
    *,
    reviewer_id: str,
    reason: str,
    actor_type: str,
    _defer_occurrence_accounting: bool = False,
) -> list[str]:
    """Retire units whose reviewed proposal is governed by a deleted source."""

    if not occurrence_writes_supported(store):
        return []
    _lock_occurrence_write_graph(store)
    chunks = store.list_source_chunks(str(source_id))
    outcomes = store.reconcile_occurrence_evidence_carrier(
        source_id=source_id,
        reviewer_id=reviewer_id,
        reason=reason,
        actor_type=actor_type,
        _defer_occurrence_accounting=_defer_occurrence_accounting,
    )
    if not _defer_occurrence_accounting and chunks:
        for chunk in chunks:
            invalidate_occurrence_accounting(
                store,
                reason=reason,
                actor_type=actor_type,
                actor_id=reviewer_id,
                source_chunk_id=str(chunk["id"]),
            )
    elif not _defer_occurrence_accounting:
        invalidate_occurrence_accounting(
            store,
            reason=reason,
            actor_type=actor_type,
            actor_id=reviewer_id,
        )
    return [
        str(outcome["occurrence_id"])
        for outcome in outcomes
        if isinstance(outcome, Mapping) and outcome.get("occurrence_id")
    ]


def transfer_consolidated_occurrence_evidence(
    store: object,
    memory: Mapping[str, object],
    members: Sequence[Mapping[str, object]],
    *,
    reviewer_id: str,
    reason: str,
    actor_type: str,
    stage: str,
) -> JsonObject:
    """Attach one accepted consolidation carrier to every distinct member unit.

    Consolidated prose is not re-parsed into new occurrence identities. The
    accepted candidate instead becomes an additional reviewed evidence carrier
    for each already-reviewed member unit before those members are retired.
    """

    if not occurrence_writes_supported(store):
        return dict(memory)
    _lock_occurrence_write_graph(store)
    if str(memory.get("status") or "") not in {"active", "accepted"}:
        raise ContinuityStoreInvariantError("occurrence consolidation carrier must be accepted before transfer")

    member_ids_by_unit: dict[str, set[str]] = {}
    units_by_id: dict[str, JsonObject] = {}
    for member in members:
        member_id = str(member.get("id") or "")
        if not member_id:
            continue
        for raw_unit in store.list_occurrence_units_for_memory(member_id):
            if not isinstance(raw_unit, Mapping):
                raise ContinuityStoreInvariantError("occurrence consolidation returned an invalid member unit")
            unit = dict(cast(Mapping[str, object], raw_unit))
            if (
                unit.get("review_status") != "accepted"
                or unit.get("identity_status") != "resolved"
                or unit.get("unit_value") != 1
            ):
                continue
            occurrence_id = str(unit.get("id") or "")
            if not occurrence_id:
                raise ContinuityStoreInvariantError("occurrence consolidation unit lacks an id")
            units_by_id[occurrence_id] = unit
            member_ids_by_unit.setdefault(occurrence_id, set()).add(member_id)

    if not units_by_id:
        return dict(memory)

    memory_scope = resolve_project_scope(memory).identity
    memory_domain = str(memory.get("domain") or "unknown")
    memory_sensitivity = str(memory.get("sensitivity") or "unknown")
    transferred_ids: list[str] = []
    for occurrence_id in sorted(units_by_id):
        unit = units_by_id[occurrence_id]
        if (
            str(unit.get("domain") or "unknown") != memory_domain
            or str(unit.get("sensitivity") or "unknown") != memory_sensitivity
            or project_scope_identity(unit.get("project_scope")) != memory_scope
        ):
            raise ContinuityStoreInvariantError(
                "consolidation candidate cannot carry occurrence evidence across an access-control envelope"
            )
        quote = str(unit.get("canonical_text") or "")
        quote_digest = _text_digest(quote)
        member_ids = sorted(member_ids_by_unit[occurrence_id])
        evidence_key = _text_digest(
            json.dumps(
                {
                    "kind": "occurrence-consolidation-carrier-v1",
                    "memory_id": str(memory["id"]),
                    "occurrence_id": occurrence_id,
                    "quote_sha256": quote_digest,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        _persist_evidence(
            store,
            {
                "claim_id": str(unit["claim_id"]),
                "occurrence_id": occurrence_id,
                "memory_id": str(memory["id"]),
                "evidence_key": evidence_key,
                "evidence_role": "supports",
                "quote": quote,
                "quote_sha256": quote_digest,
                "metadata_json": {
                    "reference_kind": "consolidation_memory",
                    "transferred_from_memory_ids": member_ids,
                },
            },
            actor_type=actor_type,
        )
        current = store.get_occurrence_unit_by_key(str(unit["occurrence_key"]))
        if not isinstance(current, Mapping) or current.get("review_status") != "accepted":
            raise ContinuityStoreInvariantError("consolidation occurrence unit changed before evidence refresh")
        store.refresh_occurrence_unit_evidence(
            occurrence_id=occurrence_id,
            reason=reason,
            reviewer_id=reviewer_id,
            expected_review_version=int(cast(int, current.get("review_version", 0))),
            actor_type=actor_type,
        )
        transferred_ids.append(occurrence_id)

    metadata = _metadata(memory)
    metadata[OCCURRENCE_CARRIER_METADATA_KEY] = {
        "kind": "consolidation",
        "member_memory_ids": sorted(str(member.get("id")) for member in members if member.get("id") is not None),
        "occurrence_unit_ids": transferred_ids,
        "stage": stage,
    }
    update = getattr(store, "update_memory", None)
    if not callable(update):
        raise ContinuityStoreInvariantError("occurrence-capable store lacks the memory metadata update seam")
    updated = update(
        memory_id=str(memory["id"]),
        patch={"metadata_json": metadata},
        actor_type=actor_type,
    )
    if not isinstance(updated, Mapping):
        raise ContinuityStoreInvariantError("occurrence consolidation carrier update returned an invalid row")
    return dict(cast(Mapping[str, object], updated))


__all__ = [
    "OCCURRENCE_EXTRACTOR_VERSION",
    "OCCURRENCE_PROPOSAL_METADATA_KEY",
    "establish_memory_occurrences",
    "establish_source_chunk_occurrences",
    "natural_occurrence_candidate_sentences",
    "natural_occurrence_candidate_text",
    "occurrence_source_title_snapshot_value",
    "occurrence_writes_supported",
    "reconcile_chunk_extraction_disposition",
    "retire_memory_occurrences",
    "retire_source_occurrences",
    "review_source_chunk_occurrences",
    "transfer_consolidated_occurrence_evidence",
]
