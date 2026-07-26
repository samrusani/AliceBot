"""Occurrence-query parsing and signed occurrence-reader seam.

This module is a mechanical extraction from :mod:`alicebot_api.vnext_retrieval`.
The public retrieval service remains ``alicebot_api.vnext_retrieval``; the
assembly module re-exports the private parser helpers retained for its
fail-on-old tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import TYPE_CHECKING, Callable, Mapping, Sequence, cast

from alicebot_api import vnext_coverage_query, vnext_occurrences
from alicebot_api.vnext_occurrence_taxonomy import (
    build_occurrence_predicate_atom,
    canonical_action_leaf,
    canonical_object_leaf,
)
from alicebot_api.vnext_project_scope import project_scope_identity
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_temporal_query import TemporalAnchor

if TYPE_CHECKING:
    from alicebot_api.vnext_retrieval import (
        VNextRetrievalRequest,
        VNextRetrievalStore,
        _ResolvedRetrievalScope,
    )


OCCURRENCE_SEARCH_PAGE_LIMIT = 200
OCCURRENCE_SEARCH_MAX_UNITS = 10_000
OCCURRENCE_EVIDENCE_BATCH_LIMIT = 200
OCCURRENCE_EVIDENCE_PAGE_LIMIT = 200
OCCURRENCE_EVIDENCE_MAX_ROWS = 10_000
OCCURRENCE_UNRESOLVED_PAGE_LIMIT = 200
OCCURRENCE_UNRESOLVED_MAX_CLAIMS = 10_000
_OCCURRENCE_QUERY_GRAMMAR_PREFIX = re.compile(
    r"^\s*(?:(?:time|times)\s+)?(?:what\s+)?"
    r"(?:(?:did|do|does|have|has|had|am|is|are|was|were)\s+)?"
    r"(?:i|we)\b",
    re.IGNORECASE,
)
_OCCURRENCE_QUERY_DETERMINERS = frozenset({"a", "an", "my", "our", "the"})
_OCCURRENCE_LEXICAL_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def _occurrence_snapshot_lifecycle_as_of(
    proof: Mapping[str, object],
) -> datetime | None:
    """Validate and normalize the lifecycle clock bound to a store snapshot."""

    if proof.get("proof") != "occurrence_read_snapshot_v1" or proof.get("acquired") is not True:
        return None
    backend = proof.get("backend")
    mode = proof.get("mode")
    if backend == "postgres":
        snapshot_id = proof.get("snapshot_id")
        if mode != "repeatable_read_read_only" or not isinstance(snapshot_id, str) or not snapshot_id.strip():
            return None
    elif backend == "sqlite":
        if mode != "transaction_snapshot":
            return None
    else:
        return None

    raw_value = proof.get("lifecycle_as_of")
    if isinstance(raw_value, datetime):
        parsed = raw_value
    elif isinstance(raw_value, str) and raw_value.strip():
        try:
            parsed = datetime.fromisoformat(raw_value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    try:
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(UTC)
    except (OverflowError, ValueError):
        return None


def _normalize_query(query: str) -> str:
    # Lazy by design: the façade owns the established validation exception.
    from alicebot_api.vnext_retrieval import normalize_query

    return normalize_query(query)


def _occurrence_token_root(token: str) -> str:
    """Small deterministic inflection fold for count-key lexical guards."""

    value = token.casefold()
    if len(value) > 4 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 5 and value.endswith("ing"):
        return value[:-3]
    if len(value) > 4 and value.endswith("ed"):
        stem = value[:-2]
        if stem.endswith(("ss", "zz")):
            return stem
        return stem + "e" if stem.endswith(("c", "s", "v", "z")) else stem
    if len(value) > 3 and value.endswith("s"):
        return value[:-1]
    return value


def _occurrence_query_matches_count_key(
    query: str,
    *,
    intent: vnext_coverage_query.AggregationIntent,
    count_key: str,
    anchor: TemporalAnchor | None = None,
) -> bool:
    """Require exact lexical agreement with one persisted count predicate.

    Store lookup is deliberately recall-oriented (phrase OR token LIKE).
    This fail-closed guard prevents a lone generic overlap such as
    ``service`` from turning a bike-service question into a car-service
    count. Only proven query grammar is removed: the exact count trigger,
    a parsed temporal span, and the leading first-person auxiliary/subject
    phrase. Persisted count-key tokens are never treated as scaffolding;
    words such as ``time``, ``month``, and ``year`` may be real objects.
    """

    topic_query = re.sub(
        re.escape(intent.trigger),
        " ",
        query,
        count=1,
        flags=re.IGNORECASE,
    )
    if anchor is not None and anchor.parsed_from:
        topic_query = re.sub(
            re.escape(anchor.parsed_from),
            " ",
            topic_query,
            count=1,
            flags=re.IGNORECASE,
        )
    topic_query = _OCCURRENCE_QUERY_GRAMMAR_PREFIX.sub(
        " ",
        topic_query,
        count=1,
    )
    query_roots = {
        _occurrence_token_root(token)
        for token in _OCCURRENCE_LEXICAL_TOKEN_PATTERN.findall(topic_query)
        if token.casefold() not in _OCCURRENCE_QUERY_DETERMINERS
    }
    count_key_roots = {_occurrence_token_root(token) for token in _OCCURRENCE_LEXICAL_TOKEN_PATTERN.findall(count_key)}
    return bool(query_roots and count_key_roots and query_roots == count_key_roots)


def _occurrence_query_has_unsupported_polarity(query: str) -> bool:
    """Return true when a positive occurrence count would be ambiguous.

    Phase 6 persists positive event units only. Negation and avoidance
    predicates, counterfactuals, plans, and failed/cancelled events therefore
    stay on the legacy retrieval path instead of reusing a signed
    positive-event total as a false answer.
    """

    normalized = _normalize_query(query).casefold().replace("’", "'")
    return bool(
        re.search(
            r"\b(?:"
            r"not|never|without|cannot|almost|unable|"
            r"avoid(?:ance|ed|ing|s)?|"
            r"skip(?:ped|ping|s)?|"
            r"miss(?:ed|ing|es)?|"
            r"cancel(?:led|ing|s)?|"
            r"refus(?:e|ed|ing)|"
            r"intend(?:ed|ing|s)?|"
            r"plan(?:ned|ning|s)?|"
            r"attempt(?:ed|ing|s)?|"
            r"tr(?:y|ied|ying|ies)|"
            r"fail(?:ed|ing|s)?\s+to|"
            r"(?:want|hope|expect)(?:ed|ing|s)?\s+to|"
            r"going\s+to|will|might|may|could|would|should|"
            r"(?:did|does|do|was|were|is|are|have|has|had|"
            r"would|could|should)n'?t|can'?t|won'?t"
            r")\b",
            normalized,
        )
    )


def _occurrence_query_supports_signed_count(
    query: str,
    intent: vnext_coverage_query.AggregationIntent | None,
) -> bool:
    """Gate signed units to discrete first-person count questions."""

    return bool(
        intent is not None
        and intent.kind == vnext_coverage_query.AGGREGATION_KIND_COUNT
        and intent.sub_intent
        in {
            vnext_coverage_query.COUNT_SUB_INTENT_CARDINALITY,
            vnext_coverage_query.COUNT_SUB_INTENT_FREQUENCY,
        }
        and re.search(r"\b(?:i|we)\b", _normalize_query(query), re.IGNORECASE)
        and not _occurrence_query_has_unsupported_polarity(query)
    )


@dataclass(frozen=True, slots=True)
class _OccurrenceQueryPlan:
    selector_keys: tuple[str, ...]
    predicate_atoms: tuple[JsonObject, ...]
    aggregation_basis: str


_OCCURRENCE_QUERY_WORD = r"[A-Za-z][A-Za-z0-9_-]*"
_OCCURRENCE_QUERY_UNSUPPORTED_SHAPE = re.compile(
    r"\b(?:distinct|unique|different|types?|kinds?|categories|"
    r"per|each|every|usually|often|currently|now)\b",
    re.IGNORECASE,
)
_OCCURRENCE_QUERY_OBJECT_DETERMINERS = {
    "a",
    "an",
    "the",
    "my",
    "our",
    "this",
    "that",
    "these",
    "those",
}
_OCCURRENCE_QUERY_OBJECT_PREPOSITIONS = {
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


def _occurrence_query_without_anchor(
    query: str,
    anchor: TemporalAnchor | None,
) -> str | None:
    """Remove only an exact, trailing temporal phrase parsed by the anchor."""

    normalized = _normalize_query(query).strip().rstrip("?").strip()
    if anchor is None or not anchor.parsed_from:
        return normalized
    parsed = anchor.parsed_from.strip()
    matches = list(
        re.finditer(
            rf"(?<![A-Za-z0-9_]){re.escape(parsed)}(?![A-Za-z0-9_])",
            normalized,
            re.IGNORECASE,
        )
    )
    if not matches:
        return None
    match = matches[-1]
    if normalized[match.end() :].strip(" ,.;:"):
        return None
    prefix = normalized[: match.start()].rstrip()
    relative = re.match(
        r"^(?:last|this|previous|next|yesterday|today)\b",
        parsed,
        re.IGNORECASE,
    )
    if relative is None:
        prep = re.search(
            r"(?:^|\s)(?:on|in|during|before|after|since)\s*$",
            prefix,
            re.IGNORECASE,
        )
        if prep is None:
            # A month-like object (for example a person named May) is not
            # silently discarded merely because it looks temporal.
            return None
        prefix = prefix[: prep.start()].rstrip()
    return prefix.strip(" ,.;:")


def _occurrence_query_object(
    value: str,
) -> tuple[str, tuple[str, ...]] | None:
    value = re.sub(
        r"(?i)(?P<owner>[A-Za-z])['’]s\b",
        r"\g<owner>",
        value,
    )
    raw_tokens = [token.casefold() for token in re.findall(_OCCURRENCE_QUERY_WORD, value)]
    while raw_tokens and raw_tokens[0] in _OCCURRENCE_QUERY_OBJECT_DETERMINERS:
        raw_tokens.pop(0)
    if not raw_tokens or any(token in {"and", "or"} for token in raw_tokens):
        return None
    if raw_tokens in (["anything"], ["something"]):
        return "*", ()
    first_preposition = next(
        (index for index, token in enumerate(raw_tokens) if token in _OCCURRENCE_QUERY_OBJECT_PREPOSITIONS),
        None,
    )
    head_index = len(raw_tokens) - 1 if first_preposition is None else first_preposition - 1
    if head_index < 0:
        return None
    object_leaf = canonical_object_leaf(raw_tokens[head_index])
    qualifiers = tuple(
        sorted(
            {
                canonical_object_leaf(token)
                for index, token in enumerate(raw_tokens)
                if index != head_index and token not in _OCCURRENCE_QUERY_OBJECT_DETERMINERS
            }
        )
    )
    return object_leaf, qualifiers


def _occurrence_query_plan(
    query: str,
    intent: vnext_coverage_query.AggregationIntent | None,
    *,
    anchor: TemporalAnchor | None,
) -> _OccurrenceQueryPlan | None:
    """Parse a bounded exact/wildcard/OR occurrence formula from query text."""

    if not _occurrence_query_supports_signed_count(query, intent):
        return None
    normalized = _occurrence_query_without_anchor(query, anchor)
    if (
        normalized is None
        or _OCCURRENCE_QUERY_UNSUPPORTED_SHAPE.search(normalized)
        or re.search(r"\band\b", normalized, re.IGNORECASE)
    ):
        return None
    assert intent is not None
    action_text: str
    object_text: str
    aggregation_basis = "event_instance"
    if intent.sub_intent == vnext_coverage_query.COUNT_SUB_INTENT_FREQUENCY:
        match = re.fullmatch(
            rf"how\s+many\s+times\s+(?:did|have)\s+(?:i|we)\s+"
            rf"(?P<action>{_OCCURRENCE_QUERY_WORD}"
            rf"(?:\s+(?:to|up|out|in|on|off))?"
            rf"(?:\s+or\s+{_OCCURRENCE_QUERY_WORD}"
            rf"(?:\s+(?:to|up|out|in|on|off))?)?)\s+"
            rf"(?P<object>.+)",
            normalized,
            re.IGNORECASE,
        )
        if match is None:
            return None
        action_text = match.group("action")
        object_text = match.group("object")
    else:
        match = re.fullmatch(
            rf"how\s+many\s+(?P<object>.+?)\s+"
            rf"(?:did|have)\s+(?:i|we)\s+"
            rf"(?P<action>{_OCCURRENCE_QUERY_WORD}"
            rf"(?:\s+(?:to|up|out|in|on|off))?"
            rf"(?:\s+or\s+{_OCCURRENCE_QUERY_WORD}"
            rf"(?:\s+(?:to|up|out|in|on|off))?)?)",
            normalized,
            re.IGNORECASE,
        )
        if match is None:
            return None
        object_text = match.group("object")
        action_text = match.group("action")
        aggregation_basis = "object_member"

    raw_actions = tuple(
        part.strip() for part in re.split(r"\s+or\s+", action_text, flags=re.IGNORECASE) if part.strip()
    )
    raw_objects = tuple(
        part.strip() for part in re.split(r"\s+or\s+", object_text, flags=re.IGNORECASE) if part.strip()
    )
    if not raw_actions or not raw_objects or len(raw_actions) * len(raw_objects) > 8:
        return None

    selectors: list[str] = []
    atoms: list[JsonObject] = []
    for raw_action in raw_actions:
        action = canonical_action_leaf(raw_action)
        for raw_object in raw_objects:
            parsed_object = _occurrence_query_object(raw_object)
            if parsed_object is None:
                return None
            object_leaf, object_qualifiers = parsed_object
            if object_leaf == "*":
                selector = f"v1|a=exact:{action}|o=*"
            else:
                try:
                    atom = build_occurrence_predicate_atom(
                        action=action,
                        object_leaf=object_leaf,
                        object_qualifiers=object_qualifiers,
                    )
                except ValueError:
                    # The predicate constructor stays strict. A natural query
                    # outside its bounded contract is simply ineligible for
                    # signed occurrence retrieval.
                    return None
                atoms.append(atom)
                selector = f"v1|a=exact:{action}|o=exact:{object_leaf}"
            if selector not in selectors:
                selectors.append(selector)
    if not selectors:
        return None
    return _OccurrenceQueryPlan(
        selector_keys=tuple(selectors),
        predicate_atoms=tuple(atoms),
        aggregation_basis=aggregation_basis,
    )


@dataclass(frozen=True, slots=True)
class _OccurrenceReaderRows:
    """Raw, scope-filtered occurrence rows awaiting pure contract validation."""

    units: tuple[JsonObject, ...]
    evidence: tuple[JsonObject, ...]
    coverage: JsonObject | None
    unresolved: tuple[JsonObject, ...]
    unresolved_dispositions: tuple[JsonObject, ...]
    accounting_summary: JsonObject | None
    requested_start: datetime | None
    requested_end: datetime | None
    all_time: bool
    unit_search_saturated: bool
    evidence_search_saturated: bool
    unresolved_search_saturated: bool
    query_plan: _OccurrenceQueryPlan


class OccurrenceRetrievalMixin:
    """Mechanical occurrence-reader methods for VNextRetrievalService."""

    if TYPE_CHECKING:
        store: VNextRetrievalStore

    def _occurrence_records_by_ids(
        self,
        record_ids: Sequence[str],
        *,
        bulk_method_name: str,
        single_method_name: str,
    ) -> dict[str, JsonObject] | None:
        """Hydrate an exact ID set without exceeding backend bind limits."""

        from alicebot_api import vnext_retrieval as _retrieval

        OCCURRENCE_EVIDENCE_BATCH_LIMIT = _retrieval.OCCURRENCE_EVIDENCE_BATCH_LIMIT

        normalized_ids = tuple(dict.fromkeys(str(record_id) for record_id in record_ids if record_id))
        if not normalized_ids:
            return {}
        bulk = getattr(self.store, bulk_method_name, None)
        single = getattr(self.store, single_method_name, None)
        if not callable(bulk) and not callable(single):
            return None
        hydrated: dict[str, JsonObject] = {}
        for offset in range(
            0,
            len(normalized_ids),
            OCCURRENCE_EVIDENCE_BATCH_LIMIT,
        ):
            requested_ids = normalized_ids[offset : offset + OCCURRENCE_EVIDENCE_BATCH_LIMIT]
            if callable(bulk):
                raw_rows = bulk(requested_ids)
                if not isinstance(raw_rows, Sequence) or isinstance(
                    raw_rows,
                    (str, bytes, bytearray),
                ):
                    return None
                rows = [dict(row) for row in raw_rows if isinstance(row, Mapping)]
                if len(rows) != len(raw_rows):
                    return None
            else:
                rows = []
                for record_id in requested_ids:
                    row = cast(Callable[[str], object], single)(record_id)
                    if row is not None:
                        if not isinstance(row, Mapping):
                            return None
                        rows.append(dict(row))
            returned_ids = [str(row.get("id") or "") for row in rows]
            if (
                any(not record_id for record_id in returned_ids)
                or len(returned_ids) != len(set(returned_ids))
                or set(returned_ids) != set(requested_ids)
                or any(record_id in hydrated for record_id in returned_ids)
            ):
                return None
            hydrated.update(
                {
                    record_id: cast(JsonObject, row)
                    for record_id, row in zip(
                        returned_ids,
                        rows,
                        strict=True,
                    )
                }
            )
        return hydrated

    def _occurrence_reader_rows(
        self,
        request: VNextRetrievalRequest,
        *,
        scope: _ResolvedRetrievalScope,
        anchor: TemporalAnchor | None,
        as_of: datetime,
        intent: vnext_coverage_query.AggregationIntent | None,
        domains: list[str],
        sensitivity_allowed: list[str],
    ) -> _OccurrenceReaderRows | None:
        """Collect the complete scoped occurrence substrate without inference.

        This optional seam is deliberately dormant for unsupported query
        shapes, legacy stores, empty occurrence stores, and filters the
        occurrence schema cannot enforce. Bundled stores apply every supplied
        predicate before LIMIT; keyset paging then proves exhaustion instead
        of counting a top-N retrieval prefix.
        """

        # Import the assembly module lazily so this mechanical extraction does
        # not introduce an import cycle. Reading these symbols at call time
        # also preserves the existing test seam that monkeypatches the façade.
        from alicebot_api import vnext_retrieval as _retrieval

        OCCURRENCE_SEARCH_PAGE_LIMIT = _retrieval.OCCURRENCE_SEARCH_PAGE_LIMIT
        OCCURRENCE_SEARCH_MAX_UNITS = _retrieval.OCCURRENCE_SEARCH_MAX_UNITS
        OCCURRENCE_EVIDENCE_BATCH_LIMIT = _retrieval.OCCURRENCE_EVIDENCE_BATCH_LIMIT
        OCCURRENCE_EVIDENCE_PAGE_LIMIT = _retrieval.OCCURRENCE_EVIDENCE_PAGE_LIMIT
        OCCURRENCE_EVIDENCE_MAX_ROWS = _retrieval.OCCURRENCE_EVIDENCE_MAX_ROWS
        OCCURRENCE_UNRESOLVED_PAGE_LIMIT = _retrieval.OCCURRENCE_UNRESOLVED_PAGE_LIMIT
        OCCURRENCE_UNRESOLVED_MAX_CLAIMS = _retrieval.OCCURRENCE_UNRESOLVED_MAX_CLAIMS
        _ResolvedRetrievalScope = _retrieval._ResolvedRetrievalScope
        _allowed = _retrieval._allowed
        _parse_timestamp = _retrieval._parse_timestamp
        _row_matches_scope = _retrieval._row_matches_scope
        _row_project_scope_values = _retrieval._row_project_scope_values
        _source_project_scope_values = _retrieval._source_project_scope_values

        if not vnext_coverage_query.supports_candidate_instance_count(intent):
            return None
        query_plan = _occurrence_query_plan(
            request.query,
            intent,
            anchor=anchor,
        )
        if query_plan is None:
            return None
        if scope.people or request.memory_types or request.created_by_agent_ids or request.filter_run_id is not None:
            # Occurrence units do not currently carry these memory-only scope
            # dimensions. Omitting the aggregate is safer than broadening.
            return None
        search_units = getattr(
            self.store,
            "search_accepted_occurrence_units_by_selector",
            None,
        )
        list_all_units = getattr(
            self.store,
            "list_accepted_occurrence_units",
            None,
        )
        list_evidence = getattr(self.store, "list_occurrence_evidence_for_units", None)
        get_coverage = getattr(self.store, "get_occurrence_coverage", None)
        list_unresolved = getattr(self.store, "list_unresolved_occurrence_claims", None)
        list_disposition_proofs = getattr(
            self.store,
            "list_accepted_occurrence_extraction_dispositions_for_claims",
            None,
        )
        summarize_accounting = getattr(
            self.store,
            "summarize_occurrence_extraction_accounting",
            None,
        )
        begin_snapshot = getattr(self.store, "begin_occurrence_read_snapshot", None)
        end_snapshot = getattr(self.store, "end_occurrence_read_snapshot", None)
        if not all(
            callable(method)
            for method in (
                search_units,
                list_all_units,
                list_evidence,
                get_coverage,
                list_unresolved,
                list_disposition_proofs,
                summarize_accounting,
                begin_snapshot,
                end_snapshot,
            )
        ):
            return None
        search_units = cast(Callable[..., object], search_units)
        list_all_units = cast(Callable[..., object], list_all_units)
        list_evidence = cast(Callable[..., object], list_evidence)
        get_coverage = cast(Callable[..., object], get_coverage)
        list_unresolved = cast(Callable[..., object], list_unresolved)
        list_disposition_proofs = cast(
            Callable[..., object],
            list_disposition_proofs,
        )
        summarize_accounting = cast(
            Callable[..., object],
            summarize_accounting,
        )
        begin_snapshot = cast(Callable[..., object], begin_snapshot)
        end_snapshot = cast(Callable[..., object], end_snapshot)

        explicit_temporal_bounds = (
            scope.window_start,
            scope.window_end,
            anchor.window_start if anchor is not None else None,
            anchor.window_end if anchor is not None else None,
        )
        all_time = all(value is None for value in explicit_temporal_bounds)
        starts = [
            value
            for value in (
                scope.window_start,
                anchor.window_start if anchor is not None else None,
            )
            if value is not None
        ]
        ends = [
            value
            for value in (
                scope.window_end,
                anchor.window_end if anchor is not None else None,
                as_of,
            )
            if value is not None
        ]
        requested_start = max(starts, default=None)
        requested_end = min(ends, default=None)
        if requested_start is not None and requested_end is not None and requested_end < requested_start:
            return None

        result: _OccurrenceReaderRows | None = None
        snapshot_started = False
        try:
            snapshot_proof = begin_snapshot()
            snapshot_started = True
            if not isinstance(snapshot_proof, Mapping):
                return None
            lifecycle_as_of = _occurrence_snapshot_lifecycle_as_of(snapshot_proof)
            if lifecycle_as_of is None:
                return None

            # ``as_of`` above is only the event/reference clock used to derive
            # the requested occurrence window. Lifecycle visibility comes
            # only from the clock bound to this transaction snapshot.
            # Pass one captured clock to every paged read so a validity boundary
            # cannot move between the page, exhaustion probe, evidence, and
            # unresolved-claim reads.
            def page_units(
                selector_key: str | None,
            ) -> tuple[list[JsonObject], bool] | None:
                paged_units: list[JsonObject] = []
                seen_unit_ids: set[str] = set()
                after_id: str | None = None
                saturated = False
                probe_expected_next_id: str | None = None
                while len(paged_units) < OCCURRENCE_SEARCH_MAX_UNITS:
                    page_limit = min(
                        OCCURRENCE_SEARCH_PAGE_LIMIT,
                        OCCURRENCE_SEARCH_MAX_UNITS - len(paged_units),
                    )
                    read_units = list_all_units if selector_key is None else search_units
                    selector_kwargs = {} if selector_key is None else {"selector_key": selector_key}
                    raw_page = read_units(
                        **selector_kwargs,
                        projects=tuple(sorted(scope.projects)) or None,
                        domains=tuple(domains) or None,
                        sensitivity_allowed=tuple(sensitivity_allowed),
                        occurred_at_start=requested_start,
                        occurred_at_end=requested_end,
                        include_timeless=True,
                        as_of=lifecycle_as_of,
                        after_id=after_id,
                        limit=page_limit,
                    )
                    if not isinstance(raw_page, Sequence) or isinstance(
                        raw_page,
                        (str, bytes, bytearray),
                    ):
                        return None
                    page = [dict(row) for row in raw_page if isinstance(row, Mapping)]
                    if len(page) != len(raw_page) or len(page) > page_limit:
                        return None
                    if not page:
                        if probe_expected_next_id is not None:
                            return None
                        break
                    page_ids = [str(row.get("id") or "") for row in page]
                    if (
                        any(not unit_id for unit_id in page_ids)
                        or page_ids != sorted(page_ids)
                        or any(unit_id in seen_unit_ids for unit_id in page_ids)
                        or (after_id is not None and page_ids[0] <= after_id)
                        or (probe_expected_next_id is not None and page_ids[0] != probe_expected_next_id)
                    ):
                        return None
                    probe_expected_next_id = None
                    paged_units.extend(cast(list[JsonObject], page))
                    seen_unit_ids.update(page_ids)
                    after_id = page_ids[-1]
                    if len(paged_units) >= OCCURRENCE_SEARCH_MAX_UNITS:
                        raw_probe = read_units(
                            **selector_kwargs,
                            projects=(tuple(sorted(scope.projects)) or None),
                            domains=tuple(domains) or None,
                            sensitivity_allowed=tuple(sensitivity_allowed),
                            occurred_at_start=requested_start,
                            occurred_at_end=requested_end,
                            include_timeless=True,
                            as_of=lifecycle_as_of,
                            after_id=after_id,
                            limit=1,
                        )
                        if not isinstance(
                            raw_probe,
                            Sequence,
                        ) or isinstance(
                            raw_probe,
                            (str, bytes, bytearray),
                        ):
                            return None
                        probe_rows = [dict(row) for row in raw_probe if isinstance(row, Mapping)]
                        if len(probe_rows) != len(raw_probe) or len(probe_rows) > 1:
                            return None
                        if probe_rows:
                            probe_id = str(probe_rows[0].get("id") or "")
                            if not probe_id or probe_id in seen_unit_ids or probe_id <= after_id:
                                return None
                            saturated = True
                        break
                    if len(page) < page_limit:
                        raw_probe = read_units(
                            **selector_kwargs,
                            projects=(tuple(sorted(scope.projects)) or None),
                            domains=tuple(domains) or None,
                            sensitivity_allowed=tuple(sensitivity_allowed),
                            occurred_at_start=requested_start,
                            occurred_at_end=requested_end,
                            include_timeless=True,
                            as_of=lifecycle_as_of,
                            after_id=after_id,
                            limit=1,
                        )
                        if not isinstance(
                            raw_probe,
                            Sequence,
                        ) or isinstance(
                            raw_probe,
                            (str, bytes, bytearray),
                        ):
                            return None
                        probe_rows = [dict(row) for row in raw_probe if isinstance(row, Mapping)]
                        if len(probe_rows) != len(raw_probe) or len(probe_rows) > 1:
                            return None
                        if not probe_rows:
                            break
                        probe_id = str(probe_rows[0].get("id") or "")
                        if not probe_id or probe_id in seen_unit_ids or probe_id <= after_id:
                            return None
                        probe_expected_next_id = probe_id
                return paged_units, saturated

            complete_units_page = page_units(None)
            if complete_units_page is None:
                return None
            complete_units, unit_search_saturated = complete_units_page
            all_units_by_id = {str(unit.get("id") or ""): unit for unit in complete_units}
            if any(not unit_id for unit_id in all_units_by_id) or len(all_units_by_id) != len(complete_units):
                return None
            units_by_selector: dict[str, JsonObject] = {}
            for selector_key in query_plan.selector_keys:
                selected = page_units(selector_key)
                if selected is None:
                    return None
                selected_units, selector_saturated = selected
                unit_search_saturated = unit_search_saturated or selector_saturated
                for unit in selected_units:
                    unit_id = str(unit.get("id") or "")
                    if not unit_id:
                        return None
                    existing = units_by_selector.get(unit_id)
                    if existing is not None and existing != unit:
                        return None
                    units_by_selector[unit_id] = unit
            query_selector_set = set(query_plan.selector_keys)
            expected_selected_ids: set[str] = set()
            for unit_id, unit in all_units_by_id.items():
                predicate = unit.get("predicate_json")
                selector_keys = predicate.get("selector_keys") if isinstance(predicate, Mapping) else None
                if (
                    isinstance(selector_keys, Sequence)
                    and not isinstance(
                        selector_keys,
                        (str, bytes),
                    )
                    and query_selector_set.intersection(str(value) for value in selector_keys)
                ):
                    expected_selected_ids.add(unit_id)
            if set(units_by_selector) != expected_selected_ids or any(
                unit_id not in all_units_by_id or all_units_by_id[unit_id] != unit
                for unit_id, unit in units_by_selector.items()
            ):
                return None
            # The pure contract receives the complete scoped accepted set, not
            # only selector hits. A reviewed predicate with incomplete closure
            # that does not intersect the query is semantically unknown, so its
            # presence must prevent a selector-only false exact answer.
            units = [all_units_by_id[unit_id] for unit_id in sorted(all_units_by_id)]
            evidence: list[JsonObject] = []
            unit_ids = [str(unit["id"]) for unit in units]
            units_by_id = {str(unit["id"]): unit for unit in units}
            evidence_unit_batches = [
                unit_ids[offset : offset + OCCURRENCE_EVIDENCE_BATCH_LIMIT]
                for offset in range(
                    0,
                    len(unit_ids),
                    OCCURRENCE_EVIDENCE_BATCH_LIMIT,
                )
            ]
            seen_evidence_ids: set[str] = set()
            evidence_search_saturated = False
            evidence_limit_reached = False
            for batch_index, evidence_unit_ids in enumerate(evidence_unit_batches):
                evidence_after_id: str | None = None
                evidence_probe_expected_next_id: str | None = None
                while len(evidence) < OCCURRENCE_EVIDENCE_MAX_ROWS:
                    page_limit = min(
                        OCCURRENCE_EVIDENCE_PAGE_LIMIT,
                        OCCURRENCE_EVIDENCE_MAX_ROWS - len(evidence),
                    )
                    raw_evidence = list_evidence(
                        evidence_unit_ids,
                        as_of=lifecycle_as_of,
                        after_id=evidence_after_id,
                        limit=page_limit,
                    )
                    if not isinstance(raw_evidence, Sequence) or isinstance(
                        raw_evidence,
                        (str, bytes, bytearray),
                    ):
                        return None
                    evidence_page = [dict(row) for row in raw_evidence if isinstance(row, Mapping)]
                    if len(evidence_page) != len(raw_evidence) or len(evidence_page) > page_limit:
                        return None
                    if not evidence_page:
                        if evidence_probe_expected_next_id is not None:
                            return None
                        break
                    evidence_page_ids = [str(row.get("id") or "") for row in evidence_page]
                    if (
                        any(not evidence_id for evidence_id in evidence_page_ids)
                        or evidence_page_ids != sorted(evidence_page_ids)
                        or any(evidence_id in seen_evidence_ids for evidence_id in evidence_page_ids)
                        or (evidence_after_id is not None and evidence_page_ids[0] <= evidence_after_id)
                        or (
                            evidence_probe_expected_next_id is not None
                            and evidence_page_ids[0] != evidence_probe_expected_next_id
                        )
                        or any(str(row.get("occurrence_id") or "") not in evidence_unit_ids for row in evidence_page)
                    ):
                        return None
                    evidence_probe_expected_next_id = None
                    evidence.extend(cast(list[JsonObject], evidence_page))
                    seen_evidence_ids.update(evidence_page_ids)
                    evidence_after_id = evidence_page_ids[-1]
                    if len(evidence) >= OCCURRENCE_EVIDENCE_MAX_ROWS:
                        probe_batches = [
                            (
                                evidence_unit_ids,
                                evidence_after_id,
                            ),
                            *[(remaining_batch, None) for remaining_batch in evidence_unit_batches[batch_index + 1 :]],
                        ]
                        for probe_unit_ids, probe_after_id in probe_batches:
                            raw_probe = list_evidence(
                                probe_unit_ids,
                                as_of=lifecycle_as_of,
                                after_id=probe_after_id,
                                limit=1,
                            )
                            if not isinstance(
                                raw_probe,
                                Sequence,
                            ) or isinstance(
                                raw_probe,
                                (str, bytes, bytearray),
                            ):
                                return None
                            probe_rows = [dict(row) for row in raw_probe if isinstance(row, Mapping)]
                            if len(probe_rows) != len(raw_probe) or len(probe_rows) > 1:
                                return None
                            if not probe_rows:
                                continue
                            probe_id = str(probe_rows[0].get("id") or "")
                            if (
                                not probe_id
                                or probe_id in seen_evidence_ids
                                or (probe_after_id is not None and probe_id <= probe_after_id)
                                or str(probe_rows[0].get("occurrence_id") or "") not in probe_unit_ids
                            ):
                                return None
                            evidence_search_saturated = True
                            break
                        evidence_limit_reached = True
                        break
                    if len(evidence_page) < page_limit:
                        raw_probe = list_evidence(
                            evidence_unit_ids,
                            as_of=lifecycle_as_of,
                            after_id=evidence_after_id,
                            limit=1,
                        )
                        if not isinstance(
                            raw_probe,
                            Sequence,
                        ) or isinstance(
                            raw_probe,
                            (str, bytes, bytearray),
                        ):
                            return None
                        probe_rows = [dict(row) for row in raw_probe if isinstance(row, Mapping)]
                        if len(probe_rows) != len(raw_probe) or len(probe_rows) > 1:
                            return None
                        if not probe_rows:
                            break
                        probe_id = str(probe_rows[0].get("id") or "")
                        if (
                            not probe_id
                            or probe_id in seen_evidence_ids
                            or probe_id <= evidence_after_id
                            or str(probe_rows[0].get("occurrence_id") or "") not in evidence_unit_ids
                        ):
                            return None
                        evidence_probe_expected_next_id = probe_id
                if evidence_limit_reached:
                    break

            evidence_memory_ids = tuple(
                dict.fromkeys(str(row.get("memory_id")) for row in evidence if row.get("memory_id") is not None)
            )
            evidence_source_ids = tuple(
                dict.fromkeys(str(row.get("source_id")) for row in evidence if row.get("source_id") is not None)
            )
            evidence_source_chunk_ids = tuple(
                dict.fromkeys(
                    str(row.get("source_chunk_id")) for row in evidence if row.get("source_chunk_id") is not None
                )
            )
            memories_by_id = self._occurrence_records_by_ids(
                evidence_memory_ids,
                bulk_method_name="get_memories_by_ids",
                single_method_name="get_memory",
            )
            sources_by_id = self._occurrence_records_by_ids(
                evidence_source_ids,
                bulk_method_name="get_sources_by_ids",
                single_method_name="get_source",
            )
            if memories_by_id is None or sources_by_id is None:
                return None
            source_chunks_by_id: dict[str, JsonObject] = {}
            if evidence_source_chunk_ids:
                get_source_chunks = getattr(self.store, "get_source_chunks_by_ids", None)
                if not callable(get_source_chunks):
                    return None
                for offset in range(
                    0,
                    len(evidence_source_chunk_ids),
                    OCCURRENCE_EVIDENCE_BATCH_LIMIT,
                ):
                    requested_chunk_ids = evidence_source_chunk_ids[offset : offset + OCCURRENCE_EVIDENCE_BATCH_LIMIT]
                    raw_chunks = get_source_chunks(requested_chunk_ids)
                    if not isinstance(raw_chunks, Sequence) or isinstance(
                        raw_chunks,
                        (str, bytes, bytearray),
                    ):
                        return None
                    chunk_rows = [dict(row) for row in raw_chunks if isinstance(row, Mapping)]
                    if len(chunk_rows) != len(raw_chunks):
                        return None
                    requested = set(requested_chunk_ids)
                    returned_ids = [str(row.get("id") or "") for row in chunk_rows]
                    if (
                        any(not chunk_id for chunk_id in returned_ids)
                        or len(returned_ids) != len(set(returned_ids))
                        or set(returned_ids) != requested
                    ):
                        return None
                    source_chunks_by_id.update(
                        {
                            chunk_id: cast(JsonObject, row)
                            for chunk_id, row in zip(
                                returned_ids,
                                chunk_rows,
                                strict=True,
                            )
                        }
                    )
            evidence_scope = _ResolvedRetrievalScope(
                projects=scope.projects,
                people=frozenset(),
                window_start=None,
                window_end=None,
            )
            for row in evidence:
                occurrence_id = str(row.get("occurrence_id") or "")
                memory_id = str(row.get("memory_id") or "")
                source_id = str(row.get("source_id") or "")
                source_chunk_id = str(row.get("source_chunk_id") or "")
                evidence_unit = units_by_id.get(occurrence_id)
                if evidence_unit is None:
                    return None
                unit_user_id = str(evidence_unit.get("user_id") or "")
                unit_claim_id = str(evidence_unit.get("claim_id") or "")
                unit_count_key = vnext_occurrences.normalize_count_key(evidence_unit.get("count_key"))
                unit_domain = str(evidence_unit.get("domain") or "unknown")
                unit_sensitivity = str(evidence_unit.get("sensitivity") or "unknown")
                unit_projects = set(project_scope_identity(evidence_unit.get("project_scope")))
                evidence_claim_id = str(row.get("claim_id") or "")
                evidence_claim_authorized = evidence_claim_id == unit_claim_id or (
                    row.get("evidence_claim_review_status") == "accepted"
                    and row.get("evidence_claim_resolution_status") == "resolved"
                    and row.get("evidence_claim_resolution_decision") == "link_existing"
                    and str(row.get("evidence_claim_resolved_occurrence_id") or "") == occurrence_id
                )
                if (
                    (row.get("user_id") is not None and str(row.get("user_id")) != unit_user_id)
                    or not evidence_claim_id
                    or not evidence_claim_authorized
                    or (
                        row.get("occurrence_count_key") is not None
                        and vnext_occurrences.normalize_count_key(row.get("occurrence_count_key")) != unit_count_key
                    )
                    or (row.get("occurrence_domain") is not None and str(row.get("occurrence_domain")) != unit_domain)
                    or (
                        row.get("occurrence_sensitivity") is not None
                        and str(row.get("occurrence_sensitivity")) != unit_sensitivity
                    )
                    or (
                        row.get("occurrence_project_scope") is not None
                        and set(project_scope_identity(row.get("occurrence_project_scope"))) != unit_projects
                    )
                ):
                    return None
                if not memory_id and not source_id:
                    # A quote or opaque chunk identifier alone cannot prove
                    # the request's authorization envelope.
                    return None
                if source_chunk_id and not source_id:
                    return None
                if memory_id:
                    memory = memories_by_id.get(memory_id)
                    valid_to = _parse_timestamp(memory.get("valid_to")) if memory is not None else None
                    if (
                        memory is None
                        or (memory.get("user_id") is not None and str(memory.get("user_id")) != unit_user_id)
                        or memory.get("deleted_at") is not None
                        or memory.get("status") not in {"active", "accepted"}
                        or (memory.get("valid_to") is not None and (valid_to is None or valid_to < lifecycle_as_of))
                        or str(memory.get("domain") or "unknown") != unit_domain
                        or str(memory.get("sensitivity") or "unknown") != unit_sensitivity
                        or _row_project_scope_values(memory) != unit_projects
                        or _allowed(
                            memory,
                            domains=domains,
                            sensitivity_allowed=sensitivity_allowed,
                        )
                        is not None
                        or not _row_matches_scope(memory, evidence_scope)
                    ):
                        return None
                if source_id:
                    source = sources_by_id.get(source_id)
                    if (
                        source is None
                        or (source.get("user_id") is not None and str(source.get("user_id")) != unit_user_id)
                        or source.get("deleted_at") is not None
                        or str(source.get("domain") or "unknown") != unit_domain
                        or str(source.get("sensitivity") or "unknown") != unit_sensitivity
                        or _source_project_scope_values(source) != unit_projects
                        or _allowed(
                            source,
                            domains=domains,
                            sensitivity_allowed=sensitivity_allowed,
                        )
                        is not None
                        or not _row_matches_scope(
                            source,
                            evidence_scope,
                            source_scope_envelope=True,
                        )
                    ):
                        return None
                if source_chunk_id:
                    chunk = source_chunks_by_id.get(source_chunk_id)
                    if (
                        chunk is None
                        or (chunk.get("user_id") is not None and str(chunk.get("user_id")) != unit_user_id)
                        or str(chunk.get("source_id") or "") != source_id
                    ):
                        return None

            unresolved: list[JsonObject] = []
            seen_unresolved_ids: set[str] = set()
            unresolved_search_saturated = False
            # A compound or ambiguously keyed pending claim in the same
            # authorization/time envelope can still affect this predicate.
            # Read the complete scoped pending set and let the pure contract
            # fail closed on any key mismatch; exact-key filtering here can
            # manufacture an exact answer by hiding such a claim.
            count_key: str | None = None
            unresolved_after_id: str | None = None
            unresolved_probe_expected_next_id: str | None = None
            while len(unresolved) < OCCURRENCE_UNRESOLVED_MAX_CLAIMS:
                page_limit = min(
                    OCCURRENCE_UNRESOLVED_PAGE_LIMIT,
                    OCCURRENCE_UNRESOLVED_MAX_CLAIMS - len(unresolved),
                )
                raw_claims = list_unresolved(
                    count_key=count_key,
                    projects=tuple(sorted(scope.projects)) or None,
                    domains=tuple(domains) or None,
                    sensitivity_allowed=tuple(sensitivity_allowed),
                    occurred_at_start=requested_start,
                    occurred_at_end=requested_end,
                    include_timeless=True,
                    as_of=lifecycle_as_of,
                    after_id=unresolved_after_id,
                    limit=page_limit,
                )
                if not isinstance(raw_claims, Sequence) or isinstance(raw_claims, (str, bytes, bytearray)):
                    return None
                claims = [dict(row) for row in raw_claims if isinstance(row, Mapping)]
                if len(claims) != len(raw_claims) or len(claims) > page_limit:
                    return None
                if not claims:
                    if unresolved_probe_expected_next_id is not None:
                        return None
                    break
                claim_ids = [str(claim.get("id") or "") for claim in claims]
                if (
                    any(not claim_id for claim_id in claim_ids)
                    or claim_ids != sorted(claim_ids)
                    or any(claim_id in seen_unresolved_ids for claim_id in claim_ids)
                    or (unresolved_after_id is not None and claim_ids[0] <= unresolved_after_id)
                    or (
                        unresolved_probe_expected_next_id is not None
                        and claim_ids[0] != unresolved_probe_expected_next_id
                    )
                ):
                    return None
                unresolved_probe_expected_next_id = None
                seen_unresolved_ids.update(claim_ids)
                unresolved.extend(cast(list[JsonObject], claims))
                unresolved_after_id = claim_ids[-1]
                if len(unresolved) >= OCCURRENCE_UNRESOLVED_MAX_CLAIMS:
                    probe = list_unresolved(
                        count_key=count_key,
                        projects=tuple(sorted(scope.projects)) or None,
                        domains=tuple(domains) or None,
                        sensitivity_allowed=tuple(sensitivity_allowed),
                        occurred_at_start=requested_start,
                        occurred_at_end=requested_end,
                        include_timeless=True,
                        as_of=lifecycle_as_of,
                        after_id=unresolved_after_id,
                        limit=1,
                    )
                    if not isinstance(probe, Sequence) or isinstance(probe, (str, bytes, bytearray)):
                        return None
                    unresolved_search_saturated = bool(probe)
                    break
                if len(claims) < page_limit:
                    raw_probe = list_unresolved(
                        count_key=count_key,
                        projects=tuple(sorted(scope.projects)) or None,
                        domains=tuple(domains) or None,
                        sensitivity_allowed=tuple(sensitivity_allowed),
                        occurred_at_start=requested_start,
                        occurred_at_end=requested_end,
                        include_timeless=True,
                        as_of=lifecycle_as_of,
                        after_id=unresolved_after_id,
                        limit=1,
                    )
                    if not isinstance(raw_probe, Sequence) or isinstance(
                        raw_probe,
                        (str, bytes, bytearray),
                    ):
                        return None
                    probe_rows = [dict(row) for row in raw_probe if isinstance(row, Mapping)]
                    if len(probe_rows) != len(raw_probe) or len(probe_rows) > 1:
                        return None
                    if not probe_rows:
                        break
                    probe_id = str(probe_rows[0].get("id") or "")
                    if not probe_id or probe_id in seen_unresolved_ids or probe_id <= unresolved_after_id:
                        return None
                    unresolved_probe_expected_next_id = probe_id

            raw_coverage = get_coverage()
            coverage = cast(JsonObject, dict(raw_coverage)) if isinstance(raw_coverage, Mapping) else None
            accounting_summary: JsonObject | None = None
            if coverage is not None and coverage.get("coverage_mode") == "complete_history":
                accounting_metadata = coverage.get("metadata_json")
                if isinstance(accounting_metadata, Mapping):
                    extractor_version = str(accounting_metadata.get("extractor_version") or "")
                    raw_summary = summarize_accounting(
                        extractor_version=extractor_version,
                        source_ids=None,
                    )
                    if not isinstance(raw_summary, Mapping):
                        return None
                    accounting_summary = cast(
                        JsonObject,
                        dict(raw_summary),
                    )
                    if accounting_summary.get("complete") is not True:
                        return None
                    for field in (
                        "extractor_version",
                        "source_ids",
                        "source_chunk_ids",
                        "snapshot_digest",
                        "disposition_digest",
                    ):
                        if accounting_summary.get(field) != accounting_metadata.get(field):
                            return None
                else:
                    return None
            elif coverage is not None and coverage.get("metadata_json") not in (
                None,
                {},
            ):
                return None

            unresolved_dispositions_by_id: dict[str, JsonObject] = {}
            unresolved_ids = [str(claim.get("id") or "") for claim in unresolved]
            if any(not claim_id for claim_id in unresolved_ids):
                return None
            raw_accounting_items = cast(
                Sequence[object],
                accounting_summary.get("items") if accounting_summary is not None else (),
            )
            allowed_dispositions = {
                str(item.get("disposition_id") or ""): item
                for item in raw_accounting_items
                if isinstance(item, Mapping)
                and item.get("status") == "complete_with_unresolved_claims"
                and str(item.get("disposition_id") or "")
            }
            proof_batches = (
                range(
                    0,
                    len(unresolved_ids),
                    OCCURRENCE_EVIDENCE_BATCH_LIMIT,
                )
                if allowed_dispositions
                else ()
            )
            accounting_summary_for_proofs = cast(JsonObject, accounting_summary)
            for offset in proof_batches:
                claim_batch = unresolved_ids[offset : offset + OCCURRENCE_EVIDENCE_BATCH_LIMIT]
                raw_proofs = list_disposition_proofs(
                    claim_batch,
                    limit=201,
                )
                if not isinstance(raw_proofs, Sequence) or isinstance(
                    raw_proofs,
                    (str, bytes, bytearray),
                ):
                    return None
                proofs = [dict(row) for row in raw_proofs if isinstance(row, Mapping)]
                if len(proofs) != len(raw_proofs) or len(proofs) > 200:
                    return None
                batch_set = set(claim_batch)
                for proof in proofs:
                    proof_id = str(proof.get("id") or "")
                    accounting_item = allowed_dispositions.get(proof_id)
                    if accounting_item is None:
                        # Older accepted extractor rows can contain the same
                        # claim. They are not members of this signed current
                        # corpus and must not reach the pure proof validator.
                        continue
                    proof_claim_ids = proof.get("claim_ids")
                    if (
                        not proof_id
                        or proof.get("extractor_version") != accounting_summary_for_proofs.get("extractor_version")
                        or str(proof.get("source_chunk_id") or "") != str(accounting_item.get("source_chunk_id") or "")
                        or str(proof.get("snapshot_sha256") or "") != str(accounting_item.get("snapshot_sha256") or "")
                        or not isinstance(proof_claim_ids, Sequence)
                        or isinstance(proof_claim_ids, (str, bytes))
                        or not batch_set.intersection(str(value) for value in proof_claim_ids)
                    ):
                        return None
                    existing = unresolved_dispositions_by_id.get(proof_id)
                    if existing is not None and existing != proof:
                        return None
                    unresolved_dispositions_by_id[proof_id] = cast(
                        JsonObject,
                        proof,
                    )
            result = _OccurrenceReaderRows(
                units=tuple(units),
                evidence=tuple(evidence),
                coverage=coverage,
                unresolved=tuple(unresolved),
                unresolved_dispositions=tuple(
                    unresolved_dispositions_by_id[proof_id] for proof_id in sorted(unresolved_dispositions_by_id)
                ),
                accounting_summary=accounting_summary,
                requested_start=requested_start,
                requested_end=requested_end,
                all_time=all_time,
                unit_search_saturated=unit_search_saturated,
                evidence_search_saturated=evidence_search_saturated,
                unresolved_search_saturated=unresolved_search_saturated,
                query_plan=query_plan,
            )
        except Exception:
            # Occurrence retrieval is an optional read path. Any malformed
            # adapter or operational failure fails closed to the established
            # pack rather than emitting an unauditable partial count.
            result = None
        finally:
            if snapshot_started:
                try:
                    end_snapshot()
                except Exception:
                    result = None
        return result
