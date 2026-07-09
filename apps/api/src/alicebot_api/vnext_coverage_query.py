"""Coverage-mode helpers for aggregation-shaped retrieval queries.

Aggregation questions ("how many times…", "list every…", "which of my …
was the most…") need every distinct instance of a topic in the context
pack, not the single best match. Standard ranked retrieval loses these
because near-duplicate or filler items outrank the tail instances for the
pack's fixed slot budget. This module supplies the three deterministic,
pure pieces ``VNextRetrievalService`` composes into "coverage mode":

1. ``detect_aggregation_intent`` — a conservative query-surface gate.
   ``None`` keeps the entire feature dormant and the retrieval pipeline
   byte-identical to the ungated path. Triggers look ONLY at the query
   text (enumeration words, comparative scaffolds); they never read
   stored rows, request metadata, or any external taxonomy.
2. ``decompose_clauses`` — splits multi-clause aggregations ("X and Y",
   comparative pairs) into sub-queries so each clause can run its own
   capped FTS sub-retrieval. Single-clause aggregations return
   ``[query]`` unchanged. Clause rows join the candidate pool as
   BACKFILL only — interleaved fairly via ``interleave_clause_rows`` and
   inserted behind the fused winners — never as extra RRF score lists:
   measured on the free coverage probe, score-fused clause fragments let
   generic sub-phrases displace evidence and coverage regressed.
3. ``apply_instance_diversity`` — a post-fusion demotion pass over fused
   candidates: near-verbatim duplicates (token-set Jaccard at or above
   ``NEAR_DUPLICATE_JACCARD``, when the caller opts into text checks)
   and — when a ``group_key_for`` accessor is given — candidates
   re-stating an already-kept candidate's provenance group (memories
   extracted from the same source) are pushed behind distinct same-topic
   instances so the instances fill the selection slots. Membership of
   the candidate pool never changes — only order and selection — and the
   pass keeps the input untouched whenever it would make no difference
   (pool no larger than the slot budget, or nothing demoted). Because
   the first candidate of every group is never demoted, the selected
   set's provenance coverage is always a superset of the undiversified
   selection's.

Everything here is deterministic string/set arithmetic: no model calls,
no store writes, no benchmark awareness (house no-fake-intelligence and
honesty rules).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any, Callable, Mapping, Sequence

from alicebot_api.vnext_repositories import JsonObject


# Aggregation intent kinds, in detection priority order.
AGGREGATION_KIND_COUNT = "count"
AGGREGATION_KIND_TOTAL = "total"
AGGREGATION_KIND_ENUMERATE = "enumerate"
AGGREGATION_KIND_ORDERING = "ordering"
AGGREGATION_KIND_COMPARATIVE = "comparative"
AGGREGATION_KINDS = (
    AGGREGATION_KIND_COUNT,
    AGGREGATION_KIND_TOTAL,
    AGGREGATION_KIND_ENUMERATE,
    AGGREGATION_KIND_ORDERING,
    AGGREGATION_KIND_COMPARATIVE,
)
# Trace stage key for the coverage-mode record; absent when dormant.
COVERAGE_STAGE = "coverage_mode"
# stage_ranks key prefix for per-clause sub-retrieval lists in RRF fusion.
COVERAGE_CLAUSE_STAGE_PREFIX = "coverage_clause_"
# Decomposition never yields more sub-queries than this.
COVERAGE_MAX_CLAUSES = 4
# Hard cap on rows fetched per clause sub-retrieval (callers may cap lower).
COVERAGE_CLAUSE_FETCH_LIMIT = 8
# Under detected intent the memory- and source-stage candidate pools are
# deepened by this factor (selection slots stay unchanged) so the diversity
# pass has distinct instances to promote; a pool no deeper than the slot
# count can only ever reorder the same items.
COVERAGE_POOL_MULTIPLIER = 3
# Token-set Jaccard at or above this marks two candidates near-verbatim
# duplicates. Deliberately high: distinct instances of the same topic
# (different sessions about the same activity) share topic words but differ
# in details and stay well below it; only redundant re-captures cross it.
NEAR_DUPLICATE_JACCARD = 0.9
# The diversity pass only inspects the first ``slots * multiplier``
# admissible fused candidates; deeper tail items keep their fused order.
DIVERSITY_CANDIDATE_MULTIPLIER = 3
# Per-source signature text cap so signatures stay cheap for long sources.
DIVERSITY_SIGNATURE_MAX_CHARS = 4000
# Honest trace exclusion_reason for a candidate the diversity pass demoted
# out of the selection slots (near-verbatim duplicate or a re-statement of
# an already-kept candidate's provenance group).
EXCLUSION_REASON_COVERAGE_REDUNDANT = "coverage_redundant_demoted"
# Honest diversity_status values for the coverage-mode stage record.
DIVERSITY_ENABLED = "enabled"
DIVERSITY_DISABLED_NO_STORE_SUPPORT = "disabled: store does not support source chunks"

# Mirrors the reasons ``vnext_retrieval._fused_candidates`` leaves on
# candidates that ranking (not policy) excluded: only these are re-rankable.
_REORDERABLE_EXCLUSION_REASONS = (None, "trimmed_by_limit")

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]+")
# Clause fragments must carry at least one token of 3+ characters outside
# this scaffold vocabulary to run as a sub-query; pure question scaffolding
# ("what did i", "the most") is dropped instead of querying for noise.
_CLAUSE_SCAFFOLD_TOKENS = frozenset(
    {
        "about", "all", "and", "any", "are", "can", "could", "did", "does",
        "each", "every", "for", "from", "had", "has", "have", "how",
        "into", "least", "less", "list", "many", "more", "most", "much",
        "name", "our", "should", "than", "that", "the", "their", "them",
        "then", "there", "these", "they", "this", "those", "time", "times",
        "total", "was", "were", "what", "when", "where", "which", "who",
        "why", "will", "with", "would", "you", "your",
    }
)
_CLAUSE_SPLIT_PATTERN = re.compile(r",\s+|;\s+|\s+and\s+|\s+or\s+", re.IGNORECASE)

_COUNT_PATTERN = re.compile(r"\bhow many\b")
_HOW_MUCH_PATTERN = re.compile(r"\bhow much\b")
_TOTALITY_PATTERN = re.compile(r"\b(?:total|altogether|combined|in all|overall)\b")
_ENUMERATE_PATTERNS = (
    re.compile(r"\ball (?:the|of the|of my|my)\b"),
    re.compile(r"\b(?:list|name) (?:every|all|each)\b"),
    re.compile(r"\beach of\b"),
)
_ORDERING_PATTERN = re.compile(r"\bin (?:what|which) order\b")
_COMPARATIVE_PATTERN = re.compile(
    r"\bwhich of (?:my|the|these|those|them|us)\b.*?"
    r"\b(?:most|least|best|worst|first|last|earliest|latest|biggest|smallest|"
    r"highest|lowest|longest|shortest|largest|greatest|fewest|more|less)\b"
)


@dataclass(frozen=True, slots=True)
class AggregationIntent:
    """A detected aggregation query shape: ``kind`` plus the matched trigger text."""

    kind: str
    trigger: str


def detect_aggregation_intent(query: str) -> AggregationIntent | None:
    """Conservative query-surface aggregation gate; ``None`` means dormant.

    Matches ONLY enumeration/comparative phrasing in the query text itself.
    A plain fact question ("what did Marcus say", "how much did the ticket
    cost") stays ``None`` so retrieval takes the standard single-target
    path unchanged. Detection order follows ``AGGREGATION_KINDS``.
    """
    lowered = " ".join(query.split()).casefold()
    if lowered == "":
        return None
    count_match = _COUNT_PATTERN.search(lowered)
    if count_match is not None:
        return AggregationIntent(kind=AGGREGATION_KIND_COUNT, trigger=count_match.group(0))
    how_much_match = _HOW_MUCH_PATTERN.search(lowered)
    if how_much_match is not None:
        # "how much" alone is a single-fact question; it only aggregates
        # when the query also asks for a total.
        totality_match = _TOTALITY_PATTERN.search(lowered)
        if totality_match is not None:
            return AggregationIntent(
                kind=AGGREGATION_KIND_TOTAL,
                trigger=f"{how_much_match.group(0)} ... {totality_match.group(0)}",
            )
    for pattern in _ENUMERATE_PATTERNS:
        enumerate_match = pattern.search(lowered)
        if enumerate_match is not None:
            return AggregationIntent(kind=AGGREGATION_KIND_ENUMERATE, trigger=enumerate_match.group(0))
    ordering_match = _ORDERING_PATTERN.search(lowered)
    if ordering_match is not None:
        return AggregationIntent(kind=AGGREGATION_KIND_ORDERING, trigger=ordering_match.group(0))
    comparative_match = _COMPARATIVE_PATTERN.search(lowered)
    if comparative_match is not None:
        return AggregationIntent(kind=AGGREGATION_KIND_COMPARATIVE, trigger=comparative_match.group(0))
    return None


def _has_clause_content(fragment: str) -> bool:
    """True when the fragment carries at least one non-scaffold content token."""
    return any(
        len(token) >= 3 and token not in _CLAUSE_SCAFFOLD_TOKENS
        for token in _TOKEN_PATTERN.findall(fragment.casefold())
    )


def decompose_clauses(query: str, max_clauses: int = COVERAGE_MAX_CLAUSES) -> list[str]:
    """Split a multi-clause aggregation question into sub-queries.

    Splits on coordination boundaries (commas, semicolons, " and ",
    " or ") and keeps fragments that carry real content tokens; the first
    fragment naturally retains the question scaffold ("how many hours did
    I spend on hiking" / "swimming"). Single-clause questions — no
    boundary, or every other fragment pure scaffold — return the
    (whitespace-normalized) query itself as the only clause, so callers
    can treat ``len(clauses) >= 2`` as "sub-retrievals are worth running".
    """
    normalized = " ".join(query.split()).strip().rstrip("?").strip()
    if normalized == "":
        return []
    fragments: list[str] = []
    seen: set[str] = set()
    for raw_fragment in _CLAUSE_SPLIT_PATTERN.split(normalized):
        fragment = raw_fragment.strip(" .,;:!?-")
        key = fragment.casefold()
        if fragment == "" or key in seen or not _has_clause_content(fragment):
            continue
        seen.add(key)
        fragments.append(fragment)
    if len(fragments) < 2:
        return [normalized]
    return fragments[: max(1, max_clauses)]


def clause_stage_name(index: int) -> str:
    """Trace stage key for the ``index``-th (1-based) clause sub-retrieval."""
    return f"{COVERAGE_CLAUSE_STAGE_PREFIX}{index}"


def interleave_clause_rows(
    clause_lists: Mapping[str, Sequence[JsonObject]],
) -> list[tuple[str, int, JsonObject]]:
    """Round-robin ``(stage_name, stage_rank, row)`` over clause result lists.

    Each clause's best row leads before any clause's second row, so when
    clause candidates backfill freed pack slots every clause gets a fair
    shot at representation (an aggregation over "X and Y" wants X's best
    instance and Y's best instance, not four rows of X). Deterministic:
    follows the mapping's insertion order (clause 1, clause 2, ...).
    """
    ordered = [(stage_name, list(rows)) for stage_name, rows in clause_lists.items()]
    interleaved: list[tuple[str, int, JsonObject]] = []
    longest = max((len(rows) for _stage_name, rows in ordered), default=0)
    for position in range(longest):
        for stage_name, rows in ordered:
            if position < len(rows):
                interleaved.append((stage_name, position + 1, rows[position]))
    return interleaved


def coverage_stage_record(
    *,
    intent: AggregationIntent,
    clause_count: int,
    clause_candidate_count: int,
    source_diversity_enabled: bool,
    memory_demotions: int,
    source_demotions: int,
) -> JsonObject:
    """Honest trace record for the coverage-mode stage (absent when dormant)."""
    return {
        "source": COVERAGE_STAGE,
        "intent": intent.kind,
        "trigger": intent.trigger,
        "clauses": clause_count,
        "clause_candidate_count": clause_candidate_count,
        "diversity_status": DIVERSITY_ENABLED if source_diversity_enabled else DIVERSITY_DISABLED_NO_STORE_SUPPORT,
        "diversity_demotions": memory_demotions + source_demotions,
        "memory_demotions": memory_demotions,
        "source_demotions": source_demotions,
    }


def memory_signature_text(memory: JsonObject) -> str:
    """Near-duplicate signature text for a memory row (content fields only)."""
    for key in ("canonical_text", "summary", "title"):
        value = memory.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def memory_provenance_group_key(memory: JsonObject) -> object:
    """Provenance group for a memory: the source it was extracted from.

    Memories captured from one source re-state that source's content; for
    aggregation queries a second memory from an already-represented source
    adds no new instance, so it yields its slot to a distinct source.
    ``None`` (no provenance metadata) never groups.
    """
    metadata = memory.get("metadata_json")
    if not isinstance(metadata, dict):
        return None
    source_id = metadata.get("source_id")
    return str(source_id) if isinstance(source_id, str) and source_id else None


def source_chunk_text_provider(
    list_source_chunks: object,
    *,
    max_chars: int = DIVERSITY_SIGNATURE_MAX_CHARS,
) -> Callable[[JsonObject], str] | None:
    """Adapt a store's ``list_source_chunks`` into a signature-text callable.

    Returns ``None`` when the store does not expose ``list_source_chunks``
    (minimal stores, legacy fakes) so the diversity pass degrades to an
    honest disabled status instead of failing. Text is capped at
    ``max_chars`` per source; signatures need shape, not completeness.
    """
    if not callable(list_source_chunks):
        return None

    def text_for(source_row: JsonObject) -> str:
        parts: list[str] = []
        size = 0
        for chunk in list_source_chunks(str(source_row.get("id"))):
            text = str(chunk.get("text") or "") if isinstance(chunk, dict) else ""
            if text == "":
                continue
            parts.append(text)
            size += len(text)
            if size >= max_chars:
                break
        return "\n".join(parts)

    return text_for


def _signature_tokens(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_PATTERN.findall(text[:DIVERSITY_SIGNATURE_MAX_CHARS].casefold()))


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    """Token-set Jaccard similarity; missing text is never "similar" (0.0)."""
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    return intersection / (len(left) + len(right) - intersection)


def apply_instance_diversity(
    candidates: Sequence[Any],
    *,
    text_for: Callable[[JsonObject], str] | None = None,
    limit: int,
    group_key_for: Callable[[JsonObject], object] | None = None,
    threshold: float = NEAR_DUPLICATE_JACCARD,
    consider_multiplier: int = DIVERSITY_CANDIDATE_MULTIPLIER,
) -> tuple[list[Any], int]:
    """Demote redundant fused candidates behind distinct instances.

    ``candidates`` are fused-order ``RetrievalCandidate``-shaped dataclass
    instances (fields ``item``/``rank``/``selected``/``exclusion_reason``;
    rebuilt generically via ``dataclasses.replace`` so this module needs no
    import from the retrieval service). Walking the fused order, the first
    ``limit`` mutually-distinct re-rankable candidates keep the selection
    slots; a candidate is demoted behind them (original order otherwise
    preserved) when it is redundant with an already-kept candidate:

    * near-verbatim text — token-set Jaccard of ``text_for`` output at or
      above ``threshold`` (skipped when ``text_for`` is ``None``: two
      distinct instances of the same fact may legitimately share text, so
      callers opt in per target type); or
    * same provenance group — ``group_key_for`` (when given) returns the
      same non-``None`` key, e.g. memories extracted from one source
      re-stating content a kept memory already covers.

    Policy-excluded candidates (domain/sensitivity) are never re-admitted
    and re-rank after the pool.

    Returns ``(candidates, demotion_count)``. The input list is returned
    untouched — same objects, same ranks — whenever the pass cannot change
    selection: pool not deeper than ``limit``, no redundancy criterion
    given, or nothing redundant found. Demoted candidates that still win a
    slot (slots left over) stay selected; demoted candidates pushed out of
    selection carry ``EXCLUSION_REASON_COVERAGE_REDUNDANT`` in the trace.
    """
    if limit < 1 or not candidates or (text_for is None and group_key_for is None):
        return list(candidates), 0
    reorderable = [
        candidate for candidate in candidates if candidate.exclusion_reason in _REORDERABLE_EXCLUSION_REASONS
    ]
    if len(reorderable) <= limit:
        return list(candidates), 0
    policy_excluded = [
        candidate for candidate in candidates if candidate.exclusion_reason not in _REORDERABLE_EXCLUSION_REASONS
    ]
    consider = reorderable[: max(limit * consider_multiplier, limit)]
    tail = reorderable[len(consider) :]

    signatures: dict[int, frozenset[str]] = {}

    def signature(index: int) -> frozenset[str]:
        if index not in signatures:
            item = consider[index].item
            signatures[index] = _signature_tokens(
                text_for(item) if text_for is not None and isinstance(item, dict) else ""
            )
        return signatures[index]

    def group_key(index: int) -> object:
        if group_key_for is None:
            return None
        item = consider[index].item
        return group_key_for(item) if isinstance(item, dict) else None

    kept: list[int] = []
    kept_group_keys: set[object] = set()
    demoted: list[int] = []
    visited = 0
    for index in range(len(consider)):
        if len(kept) >= limit:
            break
        visited = index + 1
        candidate_group_key = group_key(index)
        redundant_group = candidate_group_key is not None and candidate_group_key in kept_group_keys
        redundant_text = text_for is not None and any(
            _jaccard(signature(index), signature(kept_index)) >= threshold for kept_index in kept
        )
        if redundant_group or redundant_text:
            demoted.append(index)
            continue
        kept.append(index)
        if candidate_group_key is not None:
            kept_group_keys.add(candidate_group_key)
    if not demoted:
        return list(candidates), 0

    demoted_set = set(demoted)
    unvisited = list(range(visited, len(consider)))
    displaced = sorted(demoted_set | set(unvisited))
    reordered = [consider[index] for index in kept] + [consider[index] for index in displaced] + tail

    rebuilt: list[Any] = []
    selected_slots = min(limit, len(reordered))
    demoted_items = {id(consider[index]) for index in demoted}
    for position, candidate in enumerate([*reordered, *policy_excluded], start=1):
        is_reorderable = candidate.exclusion_reason in _REORDERABLE_EXCLUSION_REASONS
        selected = is_reorderable and position <= selected_slots
        if selected:
            exclusion_reason = None
        elif not is_reorderable:
            exclusion_reason = candidate.exclusion_reason
        elif id(candidate) in demoted_items:
            exclusion_reason = EXCLUSION_REASON_COVERAGE_REDUNDANT
        else:
            exclusion_reason = "trimmed_by_limit"
        rebuilt.append(replace(candidate, rank=position, selected=selected, exclusion_reason=exclusion_reason))
    return rebuilt, len(demoted)


__all__ = [
    "AGGREGATION_KINDS",
    "AGGREGATION_KIND_COMPARATIVE",
    "AGGREGATION_KIND_COUNT",
    "AGGREGATION_KIND_ENUMERATE",
    "AGGREGATION_KIND_ORDERING",
    "AGGREGATION_KIND_TOTAL",
    "AggregationIntent",
    "COVERAGE_CLAUSE_FETCH_LIMIT",
    "COVERAGE_CLAUSE_STAGE_PREFIX",
    "COVERAGE_MAX_CLAUSES",
    "COVERAGE_POOL_MULTIPLIER",
    "COVERAGE_STAGE",
    "DIVERSITY_CANDIDATE_MULTIPLIER",
    "DIVERSITY_DISABLED_NO_STORE_SUPPORT",
    "DIVERSITY_ENABLED",
    "DIVERSITY_SIGNATURE_MAX_CHARS",
    "EXCLUSION_REASON_COVERAGE_REDUNDANT",
    "NEAR_DUPLICATE_JACCARD",
    "apply_instance_diversity",
    "clause_stage_name",
    "coverage_stage_record",
    "decompose_clauses",
    "detect_aggregation_intent",
    "interleave_clause_rows",
    "memory_provenance_group_key",
    "memory_signature_text",
    "source_chunk_text_provider",
]
