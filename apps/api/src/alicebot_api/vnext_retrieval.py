"""Context Pack retrieval service (Context API v2).

Everything in this module is deterministic: ranking is reciprocal rank
fusion over store-provided stages, the token budget is a greedy packer,
budget strategies only reorder which sections/items are offered to that
packer, and depth tiers only switch stages and sections on or off. NO
depth tier, strategy, or section performs LLM synthesis, summarization,
or any other model call — the pack is a pure function of stored rows
plus the request (house no-fake-intelligence rule). Equal-score ordering
ties resolve through a content-stable cascade (``content_stable_tiebreak``,
disclosed in the trace as ``fusion.tie_break``) so re-ingesting the same
content — new uuids, same rows — reproduces the same pack composition;
the id remains the final total-order key.

Budget strategies (``VNextRetrievalRequest.budget_strategy``) change the
greedy packer's section order; ``recent_first`` and ``facts_first``
additionally reorder the memories list before packing. Depth tiers
(``VNextRetrievalRequest.context_depth``) trade cost for coverage:
``minimal`` (FTS only, no sources/contradictions/typed sections/recent
changes, max_items capped), ``low`` (today's default hybrid behavior),
``medium`` (low with the contradictions stage forced on for every query
type), and ``high`` (medium plus supersession chain notes). Explicit
``include_sources``/``include_contradictions`` flags always override the
tier default — the caller wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import json
import re
from typing import Mapping, Protocol, Sequence
from uuid import uuid4

# Read-only reuse of the contradiction-detection machinery that backs
# VNextContradictionService. compile_context_pack must not mutate state,
# so it calls the pure candidate finder directly instead of
# generate_contradiction_report (which persists edges/artifacts/events).
from alicebot_api import vnext_contradictions

# Coverage mode (aggregation-shaped queries): pure detection, clause
# decomposition, source near-duplicate demotion, and accepted roll-up card
# promotion helpers. Dormant unless detect_aggregation_intent fires on the
# query surface — see the marked "coverage mode" blocks in
# compile_context_pack.
from alicebot_api import vnext_coverage_query
from alicebot_api.vnext_entity_names import normalize_entity_name
from alicebot_api.vnext_embeddings import (
    EmbeddingProvider,
    VNextEmbeddingConfigurationError,
    VNextEmbeddingProviderError,
    get_embedding_provider,
)
from alicebot_api.vnext_event_log import append_event
from alicebot_api.vnext_grounding import compute_query_grounding
from alicebot_api.vnext_json import json_safe
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_store import fts_fallback_tokens
from alicebot_api.vnext_temporal_query import TemporalAnchor, parse_event_datetime, parse_temporal_anchor


DEFAULT_CONTEXT_PACK_LIMIT = 8
DEFAULT_SOURCE_LIMIT = 8
DEFAULT_OPEN_LOOP_LIMIT = 8
DEFAULT_RECENT_CHANGES_LIMIT = 5
DEFAULT_SENSITIVITY_ALLOWED = ("public", "internal", "private", "unknown")
STRATEGIC_QUERY_TYPES = {"strategic_synthesis", "contradiction_check", "project_status", "agent_context"}
RRF_K = 60
VECTOR_STAGE_ENABLED = "enabled"
VECTOR_STAGE_DISABLED_NO_PROVIDER = "disabled: no embedding provider configured"
VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT = "disabled: store does not support vector search"
# Crude token estimate: ~4 characters of serialized JSON per token. Used by
# the greedy context-pack budget packer; precision is not required, only a
# stable, monotone proxy for payload size.
TOKEN_ESTIMATE_CHARS_PER_TOKEN = 4
# A memory whose last_confirmed_at is older than this many days gets a
# "staleness" note attached in the context pack so agents can weigh it.
STALENESS_NOTE_AFTER_DAYS = 90
# valid_to values in year 9999+ are the far-future stand-in for "no expiry"
# (vnext_memory_commit.VALID_TO_UNBOUNDED_SENTINEL, written when a
# COALESCE-style update_memory cannot patch valid_to back to NULL; keep the
# two in sync). An unbounded window carries no validity signal, so pack
# "validity" annotations omit it.
VALID_TO_UNBOUNDED_YEAR = 9999
# Trace exclusion_reason for items selected by ranking but dropped by the
# token budget packer.
EXCLUSION_REASON_TOKEN_BUDGET = "token_budget"
# -- budget strategies ---------------------------------------------------------
# A strategy changes only the ORDER in which sections are offered to the
# greedy packer (and, for recent_first/facts_first, the order of the
# memories list itself). It never changes what was retrieved or ranked.
BUDGET_STRATEGY_BALANCED = "balanced"
BUDGET_STRATEGY_FACTS_FIRST = "facts_first"
BUDGET_STRATEGY_RECENT_FIRST = "recent_first"
BUDGET_STRATEGY_CONTRADICTIONS_FIRST = "contradictions_first"
BUDGET_STRATEGY_SOURCES_FIRST = "sources_first"
BUDGET_STRATEGIES = (
    BUDGET_STRATEGY_BALANCED,
    BUDGET_STRATEGY_FACTS_FIRST,
    BUDGET_STRATEGY_RECENT_FIRST,
    BUDGET_STRATEGY_CONTRADICTIONS_FIRST,
    BUDGET_STRATEGY_SOURCES_FIRST,
)
# Section names double as allocation-report keys and pack section keys.
SECTION_RELEVANT_MEMORIES = "relevant_memories"
SECTION_OPEN_LOOPS = "open_loops"
SECTION_SOURCES = "sources"
SECTION_SUPPORTING_EVIDENCE = "supporting_evidence"
SECTION_CONTRADICTING_EVIDENCE = "contradicting_evidence"
# Invariant: supporting_evidence always packs after relevant_memories
# because provenance quotes are derived from the packed memories. The
# contradicting_evidence section derives from the memories packed so far;
# under contradictions_first it packs before memories, so it derives from
# the ranking-selected (pre-budget) memories instead — the trade a caller
# opts into by prioritizing contradictions over the memories themselves.
_BALANCED_SECTION_ORDER = (
    SECTION_RELEVANT_MEMORIES,
    SECTION_OPEN_LOOPS,
    SECTION_SOURCES,
    SECTION_SUPPORTING_EVIDENCE,
    SECTION_CONTRADICTING_EVIDENCE,
)
BUDGET_STRATEGY_SECTION_ORDERS: dict[str, tuple[str, ...]] = {
    BUDGET_STRATEGY_BALANCED: _BALANCED_SECTION_ORDER,
    BUDGET_STRATEGY_FACTS_FIRST: _BALANCED_SECTION_ORDER,
    BUDGET_STRATEGY_RECENT_FIRST: _BALANCED_SECTION_ORDER,
    BUDGET_STRATEGY_CONTRADICTIONS_FIRST: (
        SECTION_CONTRADICTING_EVIDENCE,
        SECTION_RELEVANT_MEMORIES,
        SECTION_OPEN_LOOPS,
        SECTION_SOURCES,
        SECTION_SUPPORTING_EVIDENCE,
    ),
    BUDGET_STRATEGY_SOURCES_FIRST: (
        SECTION_SOURCES,
        SECTION_RELEVANT_MEMORIES,
        SECTION_OPEN_LOOPS,
        SECTION_SUPPORTING_EVIDENCE,
        SECTION_CONTRADICTING_EVIDENCE,
    ),
}
# facts_first boosts these memory_types to the front of the memories list
# (stable within each partition, so fused rank still breaks ties).
FACTS_FIRST_MEMORY_TYPES = frozenset({"semantic", "decision", "preference"})
# -- depth tiers ---------------------------------------------------------------
CONTEXT_DEPTH_MINIMAL = "minimal"
CONTEXT_DEPTH_LOW = "low"
CONTEXT_DEPTH_MEDIUM = "medium"
CONTEXT_DEPTH_HIGH = "high"
CONTEXT_DEPTHS = (
    CONTEXT_DEPTH_MINIMAL,
    CONTEXT_DEPTH_LOW,
    CONTEXT_DEPTH_MEDIUM,
    CONTEXT_DEPTH_HIGH,
)
# minimal caps max_items at min(CONTEXT_DEPTH_MINIMAL_MAX_ITEMS, requested).
CONTEXT_DEPTH_MINIMAL_MAX_ITEMS = 4
# Honest stage status when a tier (not a store limitation) skips a stage.
STAGE_DISABLED_MINIMAL = "disabled: context_depth=minimal"
# Honest stage status when the caller explicitly turned sources off.
SOURCES_STAGE_DISABLED_BY_FLAG = "disabled: include_sources=false"
# -- source stage ----------------------------------------------------------
# The sources section is RRF fusion over up to three ranked lists (keys
# below double as stage_ranks keys in the trace): sources ranked by their
# best chunk-level content hit, provenance sources of the winning memory
# hits in fused rank order, and the legacy title/recency lexical list.
SOURCE_STAGE_CHUNK_FTS = "chunk_fts"
SOURCE_STAGE_PROVENANCE = "provenance"
SOURCE_STAGE_TITLE_RECENCY = "title_recency"
# Honest chunk-list status for stores without search_source_chunks (or
# without the get_source resolver the chunk/provenance lists need).
SOURCE_CHUNK_STAGE_DISABLED_NO_STORE_SUPPORT = "disabled: store does not support source-chunk search"
# Chunk rows fetched per source slot: several chunks of one source may
# outrank the best chunk of another, so the chunk pass over-fetches
# before deduplicating down to distinct parent sources.
SOURCE_CHUNK_CANDIDATE_MULTIPLIER = 4
# Supersession chain notes (high tier): walk supersedes/superseded_by
# pointers at most this many hops in each direction, with a cycle guard.
SUPERSESSION_CHAIN_HOP_LIMIT = 5
SUPERSESSION_STAGE_ENABLED = "enabled"
CONTRADICTIONS_STAGE_ENABLED = "enabled"
CONTRADICTIONS_STAGE_NOT_REQUESTED = "disabled: not requested"
CONTRADICTIONS_STAGE_NO_STORE_SUPPORT = "disabled: store does not support beliefs"
# Entity-hop graph stage: query text -> resolved entities -> memories
# connected to those entities via mentions/about edges. Joins RRF as a third
# ranked list ("graph") next to fts/vector, so a memory with zero lexical
# overlap with the query can still surface through a shared entity.
GRAPH_STAGE_ENABLED = "enabled"
GRAPH_STAGE_DISABLED_NO_ENTITY_MATCH = "disabled: no entity match"
GRAPH_STAGE_DISABLED_NO_STORE_SUPPORT = "disabled: store does not support entities"
# At most this many resolved entities seed the hop; find_entities_by_names
# orders by mention_count DESC, so these are the most-established matches.
GRAPH_ENTITY_MATCH_LIMIT = 5
# Edge types that connect a memory node to an entity node in graph_edges.
MEMORY_ENTITY_EDGE_TYPES = ("mentions", "about")
# Mirror of the stores' _MEMORY_SEARCHABLE_STATUSES_SQL ('active',
# 'accepted'): get_memory does not enforce the searchable-status discipline
# the search_* SQL bakes in, so the graph stage re-applies it in Python.
MEMORY_SEARCHABLE_STATUSES = ("active", "accepted")
# Temporal-anchor stage: when parse_temporal_anchor finds a date-bearing
# phrase in the query ("in March 2023", "two months ago"), memories whose
# event window intersects the parsed [start, end) window join RRF as one
# more ranked list ("temporal_anchor") next to fts/vector/graph — never a
# hard filter, so a wrong parse cannot evict lexical/vector/graph hits.
# The stage record (and the list) exist only when an anchor parses; the
# anchor keys on generic query text alone.
TEMPORAL_STAGE_ENABLED = "enabled"
TEMPORAL_STAGE_DISABLED_NO_STORE_SUPPORT = "disabled: store does not support time-window search"
# The same anchor window re-ranks the fused sources stage: candidates the
# chunk/provenance/lexical lists already surfaced whose event date falls
# inside the window form a fourth ranked list (a rank boost, never a new
# recall path). A source's event date is its source_created_at, then the
# first parseable connector-stamped metadata date below, then captured_at
# (write time, the least honest fallback) — mirroring the capture
# service's source_created_at-then-captured_at event-time convention.
SOURCE_STAGE_TEMPORAL = "temporal_anchor"
SOURCE_EVENT_METADATA_KEYS = ("session_date", "event_date", "date")
# Tiny stopword set for entity-name candidate generation: n-grams whose
# first or last token is one of these never name an entity on their own.
ENTITY_NAME_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "about", "at", "be", "by", "did", "do",
        "does", "for", "from", "how", "i", "in", "is", "it", "me", "my",
        "of", "on", "or", "our", "should", "that", "the", "this", "to",
        "was", "we", "were", "what", "when", "where", "which", "who",
        "with", "your",
    }
)
# Bound on candidate names per query so the single find_entities_by_names
# round-trip stays small even for long queries.
ENTITY_NAME_CANDIDATE_LIMIT = 64


class VNextRetrievalValidationError(ValueError):
    """Raised when a vNext retrieval request is invalid."""


class VNextRetrievalStore(Protocol):
    """Minimum store surface for context-pack retrieval.

    Stores may additionally expose ``search_memories_fts`` and
    ``search_memories_vector`` (see ``PostgresVNextStore``); the service
    detects them at runtime and degrades to ``search_memories`` otherwise.
    ``search_memories_fts`` implementations should accept
    ``match_any: bool = False`` (the OR-fallback pass for multi-word
    queries the strict AND pass missed); stores that predate the kwarg
    simply never get the fallback.
    The same applies to ``list_events`` (recent_changes section),
    ``list_beliefs`` (contradicting_evidence section), the entity
    substrate ``find_entities_by_names``/``get_memory`` (entity-hop graph
    stage), ``search_source_chunks``/``get_source`` (the chunk-content
    and provenance lists of the fused sources stage), and
    ``search_memories_by_time`` (the temporal-anchor stage for
    date-bearing queries): stores without them yield empty sections / an
    honest disabled stage status instead of failing.

    ``memory_types``/``projects``/``created_by_agent_ids``/``run_id`` are
    only forwarded to the store when the request sets them, so minimal
    stores that predate those keyword arguments keep working for unfiltered
    requests.
    """

    def append_event(self, event: JsonObject) -> JsonObject: ...

    def search_memories(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_CONTEXT_PACK_LIMIT,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
        include_expired: bool = False,
    ) -> list[JsonObject]: ...

    def search_sources(
        self,
        *,
        query: str,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_SOURCE_LIMIT,
    ) -> list[JsonObject]: ...

    def list_open_loops(
        self,
        *,
        status: str | None = "open",
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        limit: int = DEFAULT_OPEN_LOOP_LIMIT,
    ) -> list[JsonObject]: ...

    def list_provenance_links(self, *, target_type: str, target_id: str) -> list[JsonObject]: ...

    def list_edges(self, *, from_id: str | None = None, to_id: str | None = None) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class VNextRetrievalRequest:
    query: str
    domains: tuple[str, ...] = ()
    projects: tuple[str, ...] = ()
    people: tuple[str, ...] = ()
    memory_types: tuple[str, ...] = ()
    # Scope filters over the first-class memory columns: restrict retrieval
    # to memories written by these agents / this agent run. filter_run_id is
    # distinct from ``run_id`` below, which attributes the retrieval *event*
    # to the caller's run in the event log.
    created_by_agent_ids: tuple[str, ...] = ()
    filter_run_id: str | None = None
    time_window: str = "all"
    sensitivity_allowed: tuple[str, ...] = DEFAULT_SENSITIVITY_ALLOWED
    # None means "let the depth tier decide" (sources/contradictions on for
    # low/medium/high, off for minimal; contradictions additionally gated to
    # strategic query types at low). An explicit True/False always wins over
    # the tier default.
    include_sources: bool | None = None
    include_contradictions: bool | None = None
    max_items: int = DEFAULT_CONTEXT_PACK_LIMIT
    # None means "no token budget": nothing is dropped, but the pack still
    # reports its token estimate. When set, the greedy packer enforces it.
    max_tokens: int | None = None
    # How the greedy packer spends max_tokens; see BUDGET_STRATEGIES.
    budget_strategy: str = BUDGET_STRATEGY_BALANCED
    # Cost/coverage tier; see CONTEXT_DEPTHS. "low" is today's default
    # hybrid behavior. No tier performs LLM synthesis.
    context_depth: str = CONTEXT_DEPTH_LOW
    actor_type: str = "system"
    actor_id: str | None = None
    agent_identity: JsonObject | None = None
    policy_decision: JsonObject | None = None
    trace_id: str | None = None
    run_id: str | None = None
    # The caller's "now" for resolving relative temporal phrases in the
    # query ("last week", "two months ago"). None means the service uses
    # the current UTC time; parsing itself never reads the wall clock.
    reference_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    item: JsonObject
    target_type: str
    rank: int
    rrf_score: float
    stage_ranks: dict[str, int]
    selected: bool
    exclusion_reason: str | None = None

    def to_trace_record(self) -> JsonObject:
        return {
            "target_type": self.target_type,
            "target_id": str(self.item.get("id")),
            "rank": self.rank,
            "rrf_score": round(self.rrf_score, 6),
            "stage_ranks": dict(self.stage_ranks),
            "selected": self.selected,
            "exclusion_reason": self.exclusion_reason,
        }


def normalize_query(query: str) -> str:
    normalized = " ".join(query.split()).strip()
    if normalized == "":
        raise VNextRetrievalValidationError("query must not be empty")
    return normalized


def query_terms(query: str) -> list[str]:
    terms = [term.casefold() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", normalize_query(query))]
    stopwords = {"about", "what", "when", "where", "which", "with", "from", "this", "that", "should", "could"}
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in stopwords or term in seen:
            continue
        deduped.append(term)
        seen.add(term)
    return deduped


def entity_name_candidates(query: str) -> list[str]:
    """Candidate normalized entity names generated from the query text.

    Unigrams, bigrams, and trigrams over the ``normalize_entity_name`` form
    of the query, skipping any n-gram whose first or last token is a
    stopword (a stopword can sit inside a longer name, e.g. "bank of
    america"). Deduplicated, order-preserving, and bounded to
    ``ENTITY_NAME_CANDIDATE_LIMIT`` so the resolution lookup stays one
    small round-trip.
    """
    tokens = normalize_entity_name(query).split()
    candidates: list[str] = []
    seen: set[str] = set()
    for size in (1, 2, 3):
        for start in range(len(tokens) - size + 1):
            gram = tokens[start : start + size]
            if gram[0] in ENTITY_NAME_STOPWORDS or gram[-1] in ENTITY_NAME_STOPWORDS:
                continue
            name = " ".join(gram)
            if name in seen:
                continue
            seen.add(name)
            candidates.append(name)
            if len(candidates) >= ENTITY_NAME_CANDIDATE_LIMIT:
                return candidates
    return candidates


def _contains_any(query: str, words: tuple[str, ...]) -> bool:
    lowered = query.casefold()
    return any(word in lowered for word in words)


def _validate_choice(value: str, *, field_name: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        raise VNextRetrievalValidationError(
            f"{field_name} must be one of: {', '.join(choices)} (got {value!r})"
        )


def _resolve_section_flags(request: VNextRetrievalRequest, *, query_type: str) -> tuple[bool, bool]:
    """Resolve (requires_sources, requires_contradictions) — caller wins.

    Explicit ``include_sources``/``include_contradictions`` always take
    precedence. When unset (None), the depth tier decides: minimal turns
    both off; low keeps today's defaults (sources on, contradictions only
    for strategic query types); medium/high force contradictions on for
    every query type — that gate is the only low/medium difference.
    """
    depth = request.context_depth
    if request.include_sources is not None:
        requires_sources = request.include_sources
    else:
        requires_sources = depth != CONTEXT_DEPTH_MINIMAL
    if request.include_contradictions is not None:
        requires_contradictions = request.include_contradictions
    elif depth == CONTEXT_DEPTH_MINIMAL:
        requires_contradictions = False
    elif depth in (CONTEXT_DEPTH_MEDIUM, CONTEXT_DEPTH_HIGH):
        requires_contradictions = True
    else:
        requires_contradictions = query_type in STRATEGIC_QUERY_TYPES
    return requires_sources, requires_contradictions


def classify_query(request: VNextRetrievalRequest) -> JsonObject:
    _validate_choice(request.context_depth, field_name="context_depth", choices=CONTEXT_DEPTHS)
    query = normalize_query(request.query)
    lowered = query.casefold()

    if _contains_any(lowered, ("contradict", "conflict", "inconsistent", "disagree")):
        query_type = "contradiction_check"
    elif _contains_any(lowered, ("open loop", "todo", "waiting", "blocked", "unresolved")):
        query_type = "open_loop_review"
    elif _contains_any(lowered, ("project", "status", "roadmap", "milestone", "next step")):
        query_type = "project_status"
    elif _contains_any(lowered, ("who is", "person", "people", "relationship")):
        query_type = "people_context"
    elif _contains_any(lowered, ("when", "timeline", "history", "changed", "since")):
        query_type = "temporal_recall"
    elif _contains_any(lowered, ("draft", "write", "compose")):
        query_type = "draft_generation"
    elif _contains_any(lowered, ("agent", "context pack", "handoff", "resume")):
        query_type = "agent_context"
    elif query.startswith('"') and query.endswith('"'):
        query_type = "exact_recall"
    else:
        query_type = "strategic_synthesis"

    domains = list(request.domains) or _infer_domains(lowered)
    sensitivity_allowed = list(request.sensitivity_allowed) or list(DEFAULT_SENSITIVITY_ALLOWED)
    requires_sources, requires_contradictions = _resolve_section_flags(request, query_type=query_type)
    return {
        "query": query,
        "query_type": query_type,
        "terms": query_terms(query),
        "domains": domains,
        "projects": list(request.projects),
        "people": list(request.people),
        "memory_types": list(request.memory_types),
        "time_window": request.time_window,
        "sensitivity_allowed": sensitivity_allowed,
        "requires_sources": requires_sources,
        "requires_contradictions": requires_contradictions,
        "requires_raw_evidence": _contains_any(lowered, ("quote", "source", "evidence", "prove", "where did")),
    }


def _infer_domains(lowered_query: str) -> list[str]:
    domains: list[str] = []
    if _contains_any(lowered_query, ("alice", "project", "roadmap", "sprint", "build")):
        domains.extend(["project", "professional"])
    if _contains_any(lowered_query, ("family", "health", "spiritual", "money", "legal")):
        domains.append("personal")
    return domains


def _allowed(item: JsonObject, *, domains: list[str], sensitivity_allowed: list[str]) -> str | None:
    item_domain = item.get("domain")
    item_sensitivity = item.get("sensitivity")
    if domains and isinstance(item_domain, str) and item_domain not in domains and item_domain != "unknown":
        return "domain_filtered"
    if isinstance(item_sensitivity, str) and item_sensitivity not in sensitivity_allowed:
        return "sensitivity_filtered"
    return None


_GRAPH_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _compact_entity(entity: JsonObject) -> JsonObject:
    return {
        "id": str(entity.get("id")),
        "name": entity.get("name"),
        "entity_type": entity.get("entity_type"),
        "mention_count": entity.get("mention_count"),
    }


def _graph_memory_admissible(
    row: JsonObject,
    *,
    now: datetime,
    domains: list[str],
    sensitivity_allowed: list[str],
    memory_types: tuple[str, ...],
    projects: tuple[str, ...],
    created_by_agent_ids: tuple[str, ...],
    run_id: str | None,
) -> bool:
    """Apply the search stages' row discipline to a hop-sourced memory row.

    ``get_memory`` returns any non-deleted row, but the fts/vector stages
    only ever see searchable-status, unexpired rows that pass the request's
    scope filters. The graph stage must not smuggle in rows the other
    stages would never return, so it re-applies the same rules here.
    """
    if str(row.get("status")) not in MEMORY_SEARCHABLE_STATUSES:
        return False
    valid_to = _parse_timestamp(row.get("valid_to"))
    if valid_to is not None and valid_to < now:
        return False
    if _allowed(row, domains=domains, sensitivity_allowed=sensitivity_allowed) is not None:
        return False
    if memory_types and row.get("memory_type") not in memory_types:
        return False
    if projects:
        metadata = row.get("metadata_json")
        project_id = row.get("project_id") or (
            metadata.get("project_id") if isinstance(metadata, Mapping) else None
        )
        if project_id not in projects:
            return False
    if created_by_agent_ids and row.get("created_by_agent_id") not in created_by_agent_ids:
        return False
    if run_id is not None and row.get("run_id") != run_id:
        return False
    return True


# -- content-stable tie-breaks -------------------------------------------------
# Equal-score ordering decisions (equal RRF fused scores, equal graph-stage
# timestamps, equal temporal-boost distances) used to fall straight through
# to the row id — a uuid minted at ingest. Within one store that is
# deterministic, but across two ingests of the SAME content the uuids
# differ, so every such tie was a coin flip re-rolled per ingest (measured
# as pure pack churn between identical-config benchmark runs). The cascade
# below decides those ties on row CONTENT instead: older event/session date
# first, then longer content, then the content text, then a content
# fingerprint; the id stays as the FINAL key — the total-order guarantee —
# but no longer casts the deciding vote between near-equals. Every key is a
# pure function of values the row already carries: no randomness, no store
# lookups, no clock reads. Deliberately NO write-clock fallbacks
# (created_at/first_seen_at/captured_at): a wall-clock key that collides in
# one ingest but not another would re-introduce seed-dependent ordering.
TIE_BREAK_CONTENT_STABLE = "content_stable_v1"
# Rows with no parseable content event signal sort after any dated row.
_TIEBREAK_UNDATED = datetime(9999, 12, 31, tzinfo=UTC)
# Content-honest event signals only: explicit validity start (memories),
# the source's own creation time, then connector-stamped metadata dates —
# the same signals search_memories_by_time and _source_event_time trust,
# minus their write-time fallbacks (see the seed-dependence note above).
_TIEBREAK_EVENT_KEYS = ("valid_from", "source_created_at")
_TIEBREAK_TEXT_KEYS = ("canonical_text", "text", "summary", "title")


def _tiebreak_event_time(item: JsonObject) -> datetime | None:
    """Content-stamped event/session time of a row, or None."""
    for key in _TIEBREAK_EVENT_KEYS:
        parsed = parse_event_datetime(item.get(key))
        if parsed is not None:
            return parsed
    metadata = item.get("metadata_json")
    if isinstance(metadata, Mapping):
        for key in SOURCE_EVENT_METADATA_KEYS:
            parsed = parse_event_datetime(metadata.get(key))
            if parsed is not None:
                return parsed
    return None


def _tiebreak_content_text(item: JsonObject) -> str:
    for key in _TIEBREAK_TEXT_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _tiebreak_content_fingerprint(item: JsonObject) -> str:
    """Stable content-derived discriminator for rows whose text also ties.

    Sources carry ``content_hash`` (digest of the captured content); capture-
    written memories carry the originating capture's digest and chunk index
    in metadata. Two rows with identical text extracted from different
    captures stay distinguishable by content, not by uuid.
    """
    content_hash = item.get("content_hash")
    if isinstance(content_hash, str) and content_hash:
        return content_hash
    metadata = item.get("metadata_json")
    if isinstance(metadata, Mapping):
        capture_hash = metadata.get("capture_content_hash")
        if isinstance(capture_hash, str) and capture_hash:
            return f"{capture_hash}:{metadata.get('source_chunk_index')}"
    return ""


def content_stable_tiebreak(item: JsonObject) -> tuple[datetime, int, str, str]:
    """Content-stable sort key for equal-score ties (ascending sorts first).

    Cascade: older content-stamped event/session date first (undated rows
    last), longer content first, then the content text itself, then the
    content fingerprint. Callers append the id as the final key.
    """
    text = _tiebreak_content_text(item)
    return (
        _tiebreak_event_time(item) or _TIEBREAK_UNDATED,
        -len(text),
        text,
        _tiebreak_content_fingerprint(item),
    )


def _stabilize_scored_rows(
    rows: Sequence[JsonObject],
    *,
    score_key: str = "fts_score",
    descending: bool = True,
) -> list[JsonObject]:
    """Reorder equal-score runs of a scored stage list content-stably.

    The stores' FTS stages order by ``fts_score DESC`` and then write-clock
    columns with the row id as the last key, so rows with EQUAL scores
    (identical term statistics — restated facts, near-duplicate turns) can
    arrive in ingest-dependent order: their relative rank re-rolls per
    ingest even though the content is identical. The Postgres vector stage
    is worse — ``ORDER BY embedding_vector <=> query`` alone, so equal
    distances get undefined database order within a single store. Distinct
    scores keep the store's order exactly (``descending`` says which way the
    stage ranks); equal scores fall through the content-stable cascade with
    the id as the final total-order key. Lists where any row lacks a
    numeric score are returned unchanged — an unknown store contract keeps
    its own order.
    """
    if not all(isinstance(row.get(score_key), (int, float)) for row in rows):
        return list(rows)
    sign = -1.0 if descending else 1.0
    return sorted(
        rows,
        key=lambda row: (
            sign * float(row[score_key]),  # type: ignore[arg-type]
            *content_stable_tiebreak(row),
            str(row.get("id")),
        ),
    )


def reciprocal_rank_fusion(
    ranked_lists: Mapping[str, Sequence[JsonObject]],
    *,
    k: int = RRF_K,
) -> list[tuple[JsonObject, float, dict[str, int]]]:
    """Fuse per-stage ranked result lists with Reciprocal Rank Fusion.

    Each item scores ``sum(1 / (k + rank))`` over the stages it appears in.
    Returns ``(item, rrf_score, stage_ranks)`` tuples ordered by descending
    score; equal scores fall through the content-stable cascade
    (``content_stable_tiebreak``) with the id as the final total-order key.
    """
    if k < 1:
        raise VNextRetrievalValidationError("reciprocal rank fusion k must be at least 1")
    items: dict[str, JsonObject] = {}
    scores: dict[str, float] = {}
    stage_ranks: dict[str, dict[str, int]] = {}
    for stage, rows in ranked_lists.items():
        for rank, row in enumerate(rows, start=1):
            item_id = str(row.get("id"))
            if item_id not in items:
                items[item_id] = row
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            stage_ranks.setdefault(item_id, {})[stage] = rank
    ordered_ids = sorted(
        items,
        key=lambda item_id: (-scores[item_id], *content_stable_tiebreak(items[item_id]), item_id),
    )
    return [(items[item_id], scores[item_id], stage_ranks[item_id]) for item_id in ordered_ids]


def _fused_candidates(
    ranked_lists: Mapping[str, Sequence[JsonObject]],
    *,
    target_type: str,
    domains: list[str],
    sensitivity_allowed: list[str],
    limit: int,
) -> list[RetrievalCandidate]:
    candidates: list[RetrievalCandidate] = []
    selected_count = 0
    for rank, (item, rrf_score, stage_ranks) in enumerate(reciprocal_rank_fusion(ranked_lists), start=1):
        exclusion_reason = _allowed(item, domains=domains, sensitivity_allowed=sensitivity_allowed)
        selected = exclusion_reason is None and selected_count < limit
        if selected:
            selected_count += 1
        elif exclusion_reason is None:
            exclusion_reason = "trimmed_by_limit"
        candidates.append(
            RetrievalCandidate(
                item=item,
                target_type=target_type,
                rank=rank,
                rrf_score=rrf_score,
                stage_ranks=stage_ranks,
                selected=selected,
                exclusion_reason=exclusion_reason,
            )
        )
    return candidates


def _compact_item(item: JsonObject) -> JsonObject:
    return {key: value for key, value in item.items() if key != "deleted_at"}


def estimate_item_tokens(item: JsonObject) -> int:
    """Estimate the token cost of one pack item (chars/4 heuristic)."""
    try:
        text = json.dumps(json_safe(item), ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        text = str(item)
    chars = len(text)
    return max(1, (chars + TOKEN_ESTIMATE_CHARS_PER_TOKEN - 1) // TOKEN_ESTIMATE_CHARS_PER_TOKEN)


@dataclass(slots=True)
class _TokenBudget:
    """Greedy token-budget packer state.

    Items are offered section by section in the strategy's section order.
    Once one item does not fit, the budget is marked truncated and every
    later item is dropped too, keeping the packed prefix aligned with the
    offer order. ``allocation`` records the admitted token estimate per
    section so agents can see where the budget went; the values always sum
    to ``token_estimate``.
    """

    token_budget: int | None
    strategy: str = BUDGET_STRATEGY_BALANCED
    token_estimate: int = 0
    truncated: bool = False
    dropped_item_count: int = 0
    allocation: dict[str, int] = field(default_factory=dict)

    def open_section(self, section: str) -> None:
        """Register a section so the allocation report has stable keys."""
        self.allocation.setdefault(section, 0)

    def admit(self, item: JsonObject, *, section: str) -> bool:
        self.open_section(section)
        cost = estimate_item_tokens(item)
        if self.truncated or (
            self.token_budget is not None and self.token_estimate + cost > self.token_budget
        ):
            self.truncated = True
            self.dropped_item_count += 1
            return False
        self.token_estimate += cost
        self.allocation[section] += cost
        return True

    def to_record(self) -> JsonObject:
        return {
            "token_budget": self.token_budget,
            "token_estimate": self.token_estimate,
            "truncated": self.truncated,
            "dropped_item_count": self.dropped_item_count,
            "strategy": self.strategy,
            "allocation": dict(self.allocation),
        }


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _staleness_note(memory: JsonObject, *, now: datetime) -> JsonObject | None:
    """Note for memories not confirmed within STALENESS_NOTE_AFTER_DAYS days."""
    last_confirmed = _parse_timestamp(memory.get("last_confirmed_at"))
    if last_confirmed is None:
        return None
    age_days = (now - last_confirmed).days
    if age_days <= STALENESS_NOTE_AFTER_DAYS:
        return None
    return {
        "days_since_last_confirmed": age_days,
        "threshold_days": STALENESS_NOTE_AFTER_DAYS,
        "note": f"last confirmed {age_days} days ago (over the {STALENESS_NOTE_AFTER_DAYS}-day threshold)",
    }


def _last_corrected_at(memory: JsonObject) -> datetime | None:
    """Newest ``corrected_at`` in the agentic in-place correction history.

    The agentic correct flow (vnext_memory_commit) appends
    ``{"corrected_at", "reason", "previous_text"}`` entries under
    ``metadata_json.agentic_memory.corrections``; the row's canonical text
    is already the corrected value, so the timestamp tells a reader when
    the current wording took effect.
    """
    metadata = memory.get("metadata_json")
    if not isinstance(metadata, Mapping):
        return None
    agentic = metadata.get("agentic_memory")
    if not isinstance(agentic, Mapping):
        return None
    corrections = agentic.get("corrections")
    if not isinstance(corrections, Sequence) or isinstance(corrections, (str, bytes)):
        return None
    moments = [
        parsed
        for entry in corrections
        if isinstance(entry, Mapping)
        if (parsed := _parse_timestamp(entry.get("corrected_at"))) is not None
    ]
    return max(moments, default=None)


def _validity_annotation(memory: JsonObject, *, superseded_by_hint: str | None = None) -> JsonObject | None:
    """Compact validity summary for rows carrying temporal/supersession signal.

    Derived purely from values the row already carries -- the
    ``valid_from``/``valid_to`` window columns, the supersession pointer
    columns from migration 20260704_0077 (plus the row status those flows
    set), and the in-place correction history read by
    ``_last_corrected_at`` -- so annotating costs no extra store queries.
    ``superseded_by_hint`` is a pack-local back-pointer: when a pack-mate's
    ``supersedes`` names this row, the row is annotated as superseded even
    if it never received the ``superseded_by`` column (one-sided patches).
    Rows without any signal return ``None`` so plain memories keep their
    exact shape, and the far-future unbounded ``valid_to`` sentinel (see
    ``VALID_TO_UNBOUNDED_YEAR``) is treated as no signal.
    """
    validity: JsonObject = {}
    valid_from = _parse_timestamp(memory.get("valid_from"))
    if valid_from is not None:
        validity["valid_from"] = valid_from.isoformat()
    valid_to = _parse_timestamp(memory.get("valid_to"))
    if valid_to is not None and valid_to.year < VALID_TO_UNBOUNDED_YEAR:
        validity["valid_to"] = valid_to.isoformat()
    superseded_by = memory.get("superseded_by") or superseded_by_hint
    if superseded_by or str(memory.get("status")) == "superseded":
        validity["superseded"] = True
    if superseded_by:
        validity["superseded_by_memory_id"] = str(superseded_by)
    if memory.get("supersedes"):
        validity["supersedes_memory_id"] = str(memory.get("supersedes"))
    corrected_at = _last_corrected_at(memory)
    if corrected_at is not None:
        validity["corrected_at"] = corrected_at.isoformat()
    return validity or None


def _memory_recency(memory: JsonObject) -> datetime:
    """Best-effort recency timestamp for recent_first ordering."""
    for key in ("updated_at", "last_seen_at", "created_at", "first_seen_at"):
        parsed = _parse_timestamp(memory.get(key))
        if parsed is not None:
            return parsed
    return _GRAPH_EPOCH


def _order_memories_for_strategy(memories: list[JsonObject], strategy: str) -> list[JsonObject]:
    """Reorder the ranking-selected memories list for the budget strategy.

    recent_first: recency DESC before fused rank (stable sort keeps fused
    order on recency ties). facts_first: memory_types in
    FACTS_FIRST_MEMORY_TYPES boosted to the front, fused order preserved
    inside each partition. Every other strategy keeps the fused order.
    """
    if strategy == BUDGET_STRATEGY_RECENT_FIRST:
        return sorted(memories, key=_memory_recency, reverse=True)
    if strategy == BUDGET_STRATEGY_FACTS_FIRST:
        facts = [item for item in memories if item.get("memory_type") in FACTS_FIRST_MEMORY_TYPES]
        rest = [item for item in memories if item.get("memory_type") not in FACTS_FIRST_MEMORY_TYPES]
        return [*facts, *rest]
    return list(memories)


def _prefer_current_versions(memories: list[JsonObject]) -> tuple[list[JsonObject], int]:
    """Demote-not-drop: move a replacement directly above its superseded ancestor.

    The store search stages already exclude retired rows (status outside
    active/accepted, closed validity windows), so both sides of a
    supersession pair can only co-occur in a pack when the pointer state is
    one-sided -- e.g. an ``update_memory`` patch set ``superseded_by``
    without retiring the row, or only the replacement's ``supersedes``
    pointer exists. Fused (RRF) order is preserved for every other item;
    only the offending (ancestor, replacement) pair is reordered,
    replacement first, and each replacement moves at most once so corrupt
    pointer cycles terminate. Returns the reordered list plus the move
    count reported in the pack trace as ``supersession_reorders``.
    """
    if len(memories) < 2:
        return list(memories), 0
    ids_in_list = {str(memory.get("id")) for memory in memories}
    # ancestor id -> replacement id, from both pointer directions; a row's
    # own superseded_by pointer wins over a pack-mate's supersedes claim.
    successor_of: dict[str, str] = {}
    for memory in memories:
        memory_id = str(memory.get("id"))
        supersedes = memory.get("supersedes")
        if supersedes and str(supersedes) in ids_in_list and str(supersedes) != memory_id:
            successor_of.setdefault(str(supersedes), memory_id)
    for memory in memories:
        memory_id = str(memory.get("id"))
        superseded_by = memory.get("superseded_by")
        if superseded_by and str(superseded_by) in ids_in_list and str(superseded_by) != memory_id:
            successor_of[memory_id] = str(superseded_by)
    if not successor_of:
        return list(memories), 0
    items = list(memories)
    moved: set[str] = set()
    reorders = 0
    index = 0
    while index < len(items):
        ancestor_id = str(items[index].get("id"))
        successor_id = successor_of.get(ancestor_id)
        if successor_id is None or successor_id in moved:
            index += 1
            continue
        successor_index = next(
            (position for position, item in enumerate(items) if str(item.get("id")) == successor_id),
            None,
        )
        if successor_index is None or successor_index <= index:
            index += 1
            continue
        items.insert(index, items.pop(successor_index))
        moved.add(successor_id)
        reorders += 1
        # Stay on this index: the replacement now sits here and may itself
        # be a superseded ancestor of a later pack-mate (chains reorder
        # newest-first in one pass).
    return items, reorders


def _memory_title(memory: JsonObject) -> str:
    for key in ("title", "canonical_text", "summary", "memory_key"):
        value = memory.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().splitlines()[0][:120]
    return str(memory.get("id"))


def _memory_reference(memory: JsonObject) -> JsonObject:
    return {
        "id": str(memory.get("id")),
        "title": _memory_title(memory),
        "memory_type": memory.get("memory_type"),
    }


def _source_event_time(source: JsonObject) -> datetime | None:
    """Best-effort event timestamp of a source row, or None.

    Precedence: ``source_created_at`` (the source's own event time, when
    the connector recorded one), then the first parseable
    ``SOURCE_EVENT_METADATA_KEYS`` value in ``metadata_json`` (connectors
    that only stamp dates into metadata, e.g. imported chat sessions),
    then ``captured_at`` (ingest write time — the least honest signal,
    kept last so imported historical sources are not dated "today").
    """
    event = parse_event_datetime(source.get("source_created_at"))
    if event is not None:
        return event
    metadata = source.get("metadata_json")
    if isinstance(metadata, Mapping):
        for key in SOURCE_EVENT_METADATA_KEYS:
            event = parse_event_datetime(metadata.get(key))
            if event is not None:
                return event
    return parse_event_datetime(source.get("captured_at"))


def _optional_search_filters(
    memory_types: tuple[str, ...],
    projects: tuple[str, ...],
    created_by_agent_ids: tuple[str, ...] = (),
    run_id: str | None = None,
) -> dict[str, object]:
    """Only forward filter kwargs when set, so minimal stores keep working."""
    filters: dict[str, object] = {}
    if memory_types:
        filters["memory_types"] = tuple(memory_types)
    if projects:
        filters["projects"] = tuple(projects)
    if created_by_agent_ids:
        filters["created_by_agent_ids"] = tuple(created_by_agent_ids)
    if run_id is not None:
        filters["run_id"] = run_id
    return filters


def _apply_budget_exclusions(
    candidates: list[RetrievalCandidate],
    kept_items: list[JsonObject],
) -> list[RetrievalCandidate]:
    """Deselect ranking-selected candidates the token budget dropped."""
    kept_ids = {str(item.get("id")) for item in kept_items}
    updated: list[RetrievalCandidate] = []
    for candidate in candidates:
        if candidate.selected and str(candidate.item.get("id")) not in kept_ids:
            updated.append(replace(candidate, selected=False, exclusion_reason=EXCLUSION_REASON_TOKEN_BUDGET))
        else:
            updated.append(candidate)
    return updated


class VNextRetrievalService:
    def __init__(
        self,
        store: VNextRetrievalStore,
        *,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.store = store
        self.embedding_provider = embedding_provider if embedding_provider is not None else get_embedding_provider()

    def _memory_fts_rows(
        self,
        *,
        query: str,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
    ) -> tuple[list[JsonObject], str]:
        filters = _optional_search_filters(memory_types, projects, created_by_agent_ids, run_id)
        search_memories_fts = getattr(self.store, "search_memories_fts", None)
        if callable(search_memories_fts):
            rows = search_memories_fts(
                query=query,
                domains=domains or None,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit,
                **filters,
            )
            # Display-only trace label; SQLite stores override it via
            # ``fts_stage_source`` so traces do not claim a Postgres stage.
            fts_source = str(getattr(self.store, "fts_stage_source", "postgres_fts"))
            if not rows and len(fts_fallback_tokens(query)) >= 2:
                # Strict AND semantics found nothing for a multi-word query.
                # With no embeddings configured (the default first-hour
                # setup) FTS is the whole recall path, so a natural-language
                # question would return zero results against memories a
                # keyword query finds instantly. Retry once with OR
                # semantics; the source string keeps the trace honest about
                # the relaxed pass, and fallback rows join RRF fusion
                # exactly like strict FTS rows. Single-token queries skip
                # the retry (OR and AND are identical there), and a strict
                # hit above never reaches this branch.
                try:
                    rows = search_memories_fts(
                        query=query,
                        domains=domains or None,
                        sensitivity_allowed=sensitivity_allowed,
                        limit=limit,
                        match_any=True,
                        **filters,
                    )
                except TypeError:
                    # Store predates the match_any kwarg; keep the strict
                    # (empty) result rather than guessing.
                    return [], fts_source
                return _stabilize_scored_rows(rows), f"{fts_source}_or_fallback"
            return _stabilize_scored_rows(rows), fts_source
        rows = self.store.search_memories(
            query=query,
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=limit,
            **filters,
        )
        return list(rows), "store_lexical"

    def _memory_vector_rows(
        self,
        *,
        query: str,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
    ) -> tuple[list[JsonObject], str]:
        if self.embedding_provider is None:
            return [], VECTOR_STAGE_DISABLED_NO_PROVIDER
        search_memories_vector = getattr(self.store, "search_memories_vector", None)
        if not callable(search_memories_vector):
            return [], VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT
        try:
            query_vector = self.embedding_provider.embed_text(query)
            rows = search_memories_vector(
                query_vector=query_vector,
                domains=domains or None,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit,
                **_optional_search_filters(memory_types, projects, created_by_agent_ids, run_id),
            )
        except (VNextEmbeddingConfigurationError, VNextEmbeddingProviderError) as exc:
            return [], f"disabled: query embedding failed ({exc})"
        # Ascending stage: smaller distance ranks first. Equal distances
        # (identical texts embed identically) stabilize content-first.
        return _stabilize_scored_rows(rows, score_key="vector_distance", descending=False), VECTOR_STAGE_ENABLED

    def _memory_graph_rows(
        self,
        *,
        query: str,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
    ) -> tuple[list[JsonObject], str, list[JsonObject]]:
        """Entity-hop graph stage: ``(rows, stage_status, matched_entities)``.

        Resolution: n-gram candidate names from the query (see
        ``entity_name_candidates``) go through ONE ``find_entities_by_names``
        round-trip; the top ``GRAPH_ENTITY_MATCH_LIMIT`` matches (by
        mention_count, the store's ordering) seed the hop. One hop: edges of
        type mentions/about between those entities and memory nodes, walked
        in both directions. Connected memories are fetched through
        ``get_memory`` and re-filtered with the same status/expiry/scope
        discipline the fts/vector stages honor, then ranked by edge
        observed_at DESC (recency proxy) and memory recency.

        Duck-typed via getattr so legacy/minimal stores without the entity
        substrate degrade to an honest disabled status instead of failing.
        """
        find_entities_by_names = getattr(self.store, "find_entities_by_names", None)
        list_edges = getattr(self.store, "list_edges", None)
        get_memory = getattr(self.store, "get_memory", None)
        if not (callable(find_entities_by_names) and callable(list_edges) and callable(get_memory)):
            return [], GRAPH_STAGE_DISABLED_NO_STORE_SUPPORT, []
        candidate_names = entity_name_candidates(query)
        entities = list(find_entities_by_names(tuple(candidate_names))) if candidate_names else []
        entities = entities[:GRAPH_ENTITY_MATCH_LIMIT]
        if not entities:
            return [], GRAPH_STAGE_DISABLED_NO_ENTITY_MATCH, []
        matched_entities = [_compact_entity(entity) for entity in entities]

        # One hop: newest edge observed_at per connected memory.
        observed_at_by_memory: dict[str, datetime] = {}
        for entity in entities:
            entity_id = str(entity.get("id"))
            edge_sides = (
                (list_edges(to_id=entity_id), "memory", "entity", "from_id"),
                (list_edges(from_id=entity_id), "entity", "memory", "to_id"),
            )
            for edges, from_type, to_type, memory_key in edge_sides:
                for edge in edges:
                    if edge.get("edge_type") not in MEMORY_ENTITY_EDGE_TYPES:
                        continue
                    if str(edge.get("from_type")) != from_type or str(edge.get("to_type")) != to_type:
                        continue
                    memory_id = str(edge.get(memory_key))
                    observed_at = _parse_timestamp(edge.get("observed_at")) or _GRAPH_EPOCH
                    previous = observed_at_by_memory.get(memory_id)
                    if previous is None or observed_at > previous:
                        observed_at_by_memory[memory_id] = observed_at

        now = datetime.now(UTC)
        ranked: list[tuple[datetime, datetime, str, JsonObject]] = []
        for memory_id, observed_at in observed_at_by_memory.items():
            row = get_memory(memory_id)
            if row is None:
                continue
            if not _graph_memory_admissible(
                row,
                now=now,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                memory_types=memory_types,
                projects=projects,
                created_by_agent_ids=created_by_agent_ids,
                run_id=run_id,
            ):
                continue
            recency = (
                _parse_timestamp(row.get("updated_at"))
                or _parse_timestamp(row.get("created_at"))
                or _GRAPH_EPOCH
            )
            ranked.append((observed_at, recency, str(row.get("id")), row))
        # Deterministic order: edge observed_at DESC, memory recency DESC,
        # then the content-stable cascade with id ASC as the final key (the
        # ascending pre-sort survives the stable reverse timestamp sort).
        ranked.sort(key=lambda entry: (*content_stable_tiebreak(entry[3]), entry[2]))
        ranked.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
        rows = [entry[3] for entry in ranked[:limit]]
        return rows, GRAPH_STAGE_ENABLED, matched_entities

    def _memory_temporal_rows(
        self,
        *,
        anchor: TemporalAnchor,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
        memory_types: tuple[str, ...] = (),
        projects: tuple[str, ...] = (),
        created_by_agent_ids: tuple[str, ...] = (),
        run_id: str | None = None,
    ) -> tuple[list[JsonObject], str]:
        """Temporal-anchor stage: ``(rows, stage_status)``.

        Memories whose event window intersects the parsed anchor window,
        via the store's ``search_memories_by_time`` (proximity-to-center
        order). Duck-typed like the other optional stages: stores without
        the method degrade to an honest disabled status instead of
        failing. The rows join RRF as one more ranked list, so the anchor
        is a ranking signal, never a filter.
        """
        search_memories_by_time = getattr(self.store, "search_memories_by_time", None)
        if not callable(search_memories_by_time):
            return [], TEMPORAL_STAGE_DISABLED_NO_STORE_SUPPORT
        rows = search_memories_by_time(
            window_start=anchor.window_start,
            window_end=anchor.window_end,
            window_center=anchor.window_center,
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=limit,
            **_optional_search_filters(memory_types, projects, created_by_agent_ids, run_id),
        )
        return list(rows), TEMPORAL_STAGE_ENABLED

    def _source_stage_lists(
        self,
        *,
        query: str,
        domains: list[str],
        sensitivity_allowed: list[str],
        limit: int,
        winning_memories: Sequence[JsonObject],
        anchor: TemporalAnchor | None = None,
    ) -> tuple[dict[str, Sequence[JsonObject]], JsonObject]:
        """Ranked source lists for RRF fusion plus the honest stage record.

        Up to three lists (see SOURCE_STAGE_* constants):

        - ``chunk_fts``: parent sources of the best chunk-content hits, in
          best-chunk order. When the strict pass finds nothing for a
          multi-token query, retried once with ``match_any=True`` — the
          same one-shot OR-fallback the memory FTS stage uses — and the
          record's ``chunk_fts_source`` label reports the relaxed pass.
        - ``provenance``: sources the winning memories' provenance links
          point at, in fused memory-rank order, so evidence backing a
          retrieved memory surfaces even with zero lexical overlap.
        - ``title_recency``: the legacy ``search_sources`` lexical list
          (title/author/uri/metadata LIKE, recency-ordered).
        - ``temporal_anchor`` (only when ``anchor`` is set): the sources
          the other lists already surfaced whose event date (see
          ``_source_event_time``) falls inside the anchor window, ordered
          by proximity to the window center — a rank boost over existing
          candidates, never a new recall path.

        Lists whose store capability is missing (``search_source_chunks``
        / ``get_source``) are skipped with an honest label instead of
        failing, so minimal stores and test fakes keep working. The stage
        record reports each list's candidate count under its stage key.
        """
        get_source = getattr(self.store, "get_source", None)
        resolve_source = get_source if callable(get_source) else None

        def _resolve_sources(source_ids: list[str]) -> list[JsonObject]:
            rows: list[JsonObject] = []
            for source_id in source_ids:
                row = resolve_source(source_id) if resolve_source is not None else None
                if row is not None:
                    rows.append(row)
            return rows

        ranked_lists: dict[str, Sequence[JsonObject]] = {}

        # (a) Content: sources ranked by their best chunk-FTS hit.
        search_source_chunks = getattr(self.store, "search_source_chunks", None)
        chunk_sources: list[JsonObject] = []
        if callable(search_source_chunks) and resolve_source is not None:
            chunk_fts_source = str(getattr(self.store, "fts_stage_source", "postgres_fts"))
            chunk_rows = search_source_chunks(
                query=query,
                domains=domains or None,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit * SOURCE_CHUNK_CANDIDATE_MULTIPLIER,
            )
            if not chunk_rows and len(fts_fallback_tokens(query)) >= 2:
                # Same one-shot OR retry as _memory_fts_rows, same honesty
                # rule: the label reports the relaxed pass.
                try:
                    chunk_rows = search_source_chunks(
                        query=query,
                        domains=domains or None,
                        sensitivity_allowed=sensitivity_allowed,
                        limit=limit * SOURCE_CHUNK_CANDIDATE_MULTIPLIER,
                        match_any=True,
                    )
                except TypeError:
                    # Store predates the match_any kwarg; keep the strict
                    # (empty) result rather than guessing.
                    chunk_rows = []
                else:
                    chunk_fts_source = f"{chunk_fts_source}_or_fallback"
            # Equal-score chunk runs decide WHICH parent source enters the
            # deduplicated chunk list first; stabilize them content-first so
            # the list is ingest-invariant (distinct scores keep store order).
            chunk_rows = _stabilize_scored_rows(chunk_rows)
            ordered_source_ids: list[str] = []
            seen_source_ids: set[str] = set()
            for row in chunk_rows:
                source_id = row.get("source_id")
                if source_id is None or str(source_id) in seen_source_ids:
                    continue
                seen_source_ids.add(str(source_id))
                ordered_source_ids.append(str(source_id))
            chunk_sources = _resolve_sources(ordered_source_ids[:limit])
            ranked_lists[SOURCE_STAGE_CHUNK_FTS] = chunk_sources
        else:
            chunk_fts_source = SOURCE_CHUNK_STAGE_DISABLED_NO_STORE_SUPPORT

        # (b) Provenance of the winning memory hits, in fused rank order.
        provenance_sources: list[JsonObject] = []
        if resolve_source is not None:
            provenance_ids: list[str] = []
            seen_provenance: set[str] = set()
            for memory in winning_memories:
                for link in self.store.list_provenance_links(
                    target_type="memory", target_id=str(memory.get("id"))
                ):
                    source_id = link.get("source_id")
                    if source_id is None or str(source_id) in seen_provenance:
                        continue
                    seen_provenance.add(str(source_id))
                    provenance_ids.append(str(source_id))
            provenance_sources = _resolve_sources(provenance_ids[:limit])
            ranked_lists[SOURCE_STAGE_PROVENANCE] = provenance_sources

        # (c) Legacy title/recency lexical list.
        lexical_rows = list(
            self.store.search_sources(
                query=query,
                domains=domains or None,
                sensitivity_allowed=sensitivity_allowed,
                limit=limit,
            )
        )
        ranked_lists[SOURCE_STAGE_TITLE_RECENCY] = lexical_rows

        # (d) Temporal-anchor rank boost: re-rank the candidates the lists
        # above already found by proximity to the anchor window's center.
        # Only sources with a parseable event date inside the window join;
        # everything stays fusion-honest (a wrong window cannot evict the
        # content/provenance/lexical hits, only fail to boost).
        temporal_sources: list[JsonObject] = []
        if anchor is not None:
            center = anchor.window_center
            dated: list[tuple[float, str, JsonObject]] = []
            seen_dated: set[str] = set()
            for rows in (chunk_sources, provenance_sources, lexical_rows):
                for row in rows:
                    source_id = str(row.get("id"))
                    if source_id in seen_dated:
                        continue
                    seen_dated.add(source_id)
                    event = _source_event_time(row)
                    if event is None or not (anchor.window_start <= event < anchor.window_end):
                        continue
                    dated.append((abs((event - center).total_seconds()), source_id, row))
            # Distance ties are the norm here (day-resolution session dates
            # share a window distance), so they fall through the
            # content-stable cascade before the id total-order key.
            dated.sort(key=lambda entry: (entry[0], *content_stable_tiebreak(entry[2]), entry[1]))
            temporal_sources = [row for _distance, _source_id, row in dated]
            ranked_lists[SOURCE_STAGE_TEMPORAL] = temporal_sources

        unique_candidate_ids = {
            str(row.get("id")) for rows in ranked_lists.values() for row in rows
        }
        stage_record: JsonObject = {
            "source": "rrf(" + "+".join(ranked_lists) + ")",
            "candidate_count": len(unique_candidate_ids),
            SOURCE_STAGE_CHUNK_FTS: len(chunk_sources),
            SOURCE_STAGE_PROVENANCE: len(provenance_sources),
            SOURCE_STAGE_TITLE_RECENCY: len(lexical_rows),
            "chunk_fts_source": chunk_fts_source,
        }
        if anchor is not None:
            stage_record[SOURCE_STAGE_TEMPORAL] = len(temporal_sources)
        return ranked_lists, stage_record

    def compile_context_pack(self, request: VNextRetrievalRequest) -> JsonObject:
        if request.max_tokens is not None and request.max_tokens < 1:
            raise VNextRetrievalValidationError("max_tokens must be a positive integer when set")
        _validate_choice(request.budget_strategy, field_name="budget_strategy", choices=BUDGET_STRATEGIES)
        _validate_choice(request.context_depth, field_name="context_depth", choices=CONTEXT_DEPTHS)
        strategy = request.budget_strategy
        depth = request.context_depth
        interpretation = classify_query(request)
        terms = list(interpretation["terms"])  # type: ignore[arg-type]
        domains = list(interpretation["domains"])  # type: ignore[arg-type]
        sensitivity_allowed = list(interpretation["sensitivity_allowed"])  # type: ignore[arg-type]
        sources_enabled = bool(interpretation["requires_sources"])
        contradictions_requested = bool(interpretation["requires_contradictions"])
        memory_types = tuple(request.memory_types)
        projects = tuple(request.projects)
        created_by_agent_ids = tuple(request.created_by_agent_ids)
        filter_run_id = request.filter_run_id
        trace_id = request.trace_id or str(uuid4())
        context_pack_id = str(uuid4())
        max_items = request.max_items
        if depth == CONTEXT_DEPTH_MINIMAL:
            max_items = min(CONTEXT_DEPTH_MINIMAL_MAX_ITEMS, max_items)
        memory_candidate_limit = max(max_items * 2, max_items)
        # Temporal anchor from generic query text only. The reference time
        # for relative phrases is the caller's now (request.reference_time)
        # or the current UTC time; the parser itself never reads the clock.
        anchor = parse_temporal_anchor(
            request.query,
            reference_time=(
                request.reference_time if request.reference_time is not None else datetime.now(UTC)
            ),
        )

        # ---- coverage mode (aggregation intent) begin --------------------
        # Gated by the query surface ONLY (vnext_coverage_query.detect_
        # aggregation_intent); when the gate stays None — every ordinary
        # query — no coverage block in this method runs and the pack is
        # byte-identical to the ungated pipeline. When it fires, the
        # memory candidate POOL deepens here (selection slot counts never
        # change) so the instance-diversity pass below has distinct
        # instances to promote into the slots. The source pool is NOT
        # deepened: measured on the free coverage probe, a deeper source
        # pool lets tail items that appear in two ranked lists outscore
        # single-list evidence and all-coverage regressed. minimal depth
        # keeps its cheapest-useful-call promise: no detection, no
        # coverage work.
        coverage_intent = (
            None
            if depth == CONTEXT_DEPTH_MINIMAL
            else vnext_coverage_query.detect_aggregation_intent(str(interpretation["query"]))
        )
        if coverage_intent is not None:
            memory_candidate_limit *= vnext_coverage_query.COVERAGE_POOL_MULTIPLIER
        # ---- coverage mode (aggregation intent) end ----------------------

        fts_rows, fts_source = self._memory_fts_rows(
            query=request.query,
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=memory_candidate_limit,
            memory_types=memory_types,
            projects=projects,
            created_by_agent_ids=created_by_agent_ids,
            run_id=filter_run_id,
        )
        if depth == CONTEXT_DEPTH_MINIMAL:
            # The cheapest useful call: FTS only. No query embedding, no
            # entity resolution or graph hop; honest tier status instead.
            vector_rows, vector_stage = [], STAGE_DISABLED_MINIMAL
            graph_rows, graph_stage, matched_entities = [], STAGE_DISABLED_MINIMAL, []
        else:
            vector_rows, vector_stage = self._memory_vector_rows(
                query=str(interpretation["query"]),
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=memory_candidate_limit,
                memory_types=memory_types,
                projects=projects,
                created_by_agent_ids=created_by_agent_ids,
                run_id=filter_run_id,
            )
            graph_rows, graph_stage, matched_entities = self._memory_graph_rows(
                query=request.query,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=memory_candidate_limit,
                memory_types=memory_types,
                projects=projects,
                created_by_agent_ids=created_by_agent_ids,
                run_id=filter_run_id,
            )
        # Temporal-anchor stage: only exists when the query carried a
        # parseable date phrase. One more RRF list (never a filter), plus
        # an honest trace record; both are absent when no anchor parses.
        temporal_rows: list[JsonObject] = []
        temporal_stage_record: JsonObject | None = None
        if anchor is not None:
            if depth == CONTEXT_DEPTH_MINIMAL:
                temporal_stage = STAGE_DISABLED_MINIMAL
            else:
                temporal_rows, temporal_stage = self._memory_temporal_rows(
                    anchor=anchor,
                    domains=domains,
                    sensitivity_allowed=sensitivity_allowed,
                    limit=memory_candidate_limit,
                    memory_types=memory_types,
                    projects=projects,
                    created_by_agent_ids=created_by_agent_ids,
                    run_id=filter_run_id,
                )
            temporal_stage_record = {
                "source": "temporal_anchor",
                "status": temporal_stage,
                "window": [anchor.window_start.isoformat(), anchor.window_end.isoformat()],
                "parsed_from": anchor.parsed_from,
                "candidate_count": len(temporal_rows),
            }
        memory_lists: dict[str, Sequence[JsonObject]] = {"fts": fts_rows}
        if vector_stage == VECTOR_STAGE_ENABLED:
            memory_lists["vector"] = vector_rows
        if graph_stage == GRAPH_STAGE_ENABLED:
            memory_lists["graph"] = graph_rows
        if temporal_stage_record is not None and temporal_stage_record["status"] == TEMPORAL_STAGE_ENABLED:
            memory_lists["temporal_anchor"] = temporal_rows

        # ---- coverage mode (aggregation intent) begin --------------------
        # Multi-clause aggregations ("X and Y", comparative pairs) run
        # capped FTS-only sub-retrievals per clause. The rows do NOT join
        # the RRF score fight (measured on the free coverage probe, naive
        # fused clause lists let generic clause fragments displace evidence
        # — all-coverage regressed); instead they backfill below: clause
        # rows enter the candidate pool right behind the fused winners, so
        # they can only fill slots the diversity pass frees. Dormant unless
        # the intent gate fired above.
        coverage_clauses: list[str] = []
        coverage_clause_lists: dict[str, list[JsonObject]] = {}
        coverage_clause_candidate_count = 0
        if coverage_intent is not None:
            coverage_clauses = vnext_coverage_query.decompose_clauses(str(interpretation["query"]))
            if len(coverage_clauses) >= 2:
                for clause_index, clause in enumerate(coverage_clauses, start=1):
                    clause_rows, _clause_fts_source = self._memory_fts_rows(
                        query=clause,
                        domains=domains,
                        sensitivity_allowed=sensitivity_allowed,
                        limit=min(max_items, vnext_coverage_query.COVERAGE_CLAUSE_FETCH_LIMIT),
                        memory_types=memory_types,
                        projects=projects,
                        created_by_agent_ids=created_by_agent_ids,
                        run_id=filter_run_id,
                    )
                    if clause_rows:
                        coverage_clause_lists[vnext_coverage_query.clause_stage_name(clause_index)] = list(
                            clause_rows
                        )
                        coverage_clause_candidate_count += len(clause_rows)
        # ---- coverage mode (aggregation intent) end ----------------------

        # Memories fuse before the source stage runs: the provenance list
        # of the fused sources stage follows the winning memory hits.
        memory_candidates = _fused_candidates(
            memory_lists,
            target_type="memory",
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=max_items,
        )

        # The provenance list of the fused sources stage follows these
        # winners; captured here, before any coverage-mode reordering, so
        # the source stage sees the same winners with or without coverage.
        provenance_memories = [candidate.item for candidate in memory_candidates if candidate.selected]

        # ---- coverage mode (aggregation intent) begin --------------------
        # (1) Clause backfill: sub-retrieval rows enter the candidate pool
        #     immediately behind the fused winners (unselected), so each
        #     clause's best instances are first in line for any slot the
        #     diversity pass frees — without ever displacing a fused
        #     winner on score.
        # (2) Instance diversity over the memories: re-statements of an
        #     already-kept memory's provenance source are demoted behind
        #     memories from distinct sources, so an aggregation pack
        #     carries every instance instead of one instance restated.
        #     Group-key only — NO text-similarity demotion here, because
        #     two instances of the same recurring fact captured from
        #     different sources legitimately share text and are exactly
        #     what aggregation questions need.
        # The pass reorders pack slots only: provenance_memories above is
        # captured pre-diversity, so the source stage stays decoupled and
        # a demotion can never knock a session out of the pack's source
        # slots. Every baseline-selected memory's source stays represented
        # (first memory per source is never demoted), so the pack's
        # session coverage is a superset of the ungated pack's. Dormant
        # unless the gate fired.
        coverage_memory_demotions = 0
        if coverage_intent is not None:
            if coverage_clause_lists:
                seen_candidate_ids = {str(candidate.item.get("id")) for candidate in memory_candidates}
                backfill_candidates: list[RetrievalCandidate] = []
                for stage_name, stage_rank, row in vnext_coverage_query.interleave_clause_rows(
                    coverage_clause_lists
                ):
                    row_id = str(row.get("id"))
                    if row_id in seen_candidate_ids:
                        continue
                    if _allowed(row, domains=domains, sensitivity_allowed=sensitivity_allowed) is not None:
                        continue
                    seen_candidate_ids.add(row_id)
                    backfill_candidates.append(
                        RetrievalCandidate(
                            item=row,
                            target_type="memory",
                            rank=0,  # reassigned below
                            rrf_score=0.0,  # honest: not part of RRF fusion
                            stage_ranks={stage_name: stage_rank},
                            selected=False,
                            exclusion_reason="trimmed_by_limit",
                        )
                    )
                if backfill_candidates:
                    winners = [candidate for candidate in memory_candidates if candidate.selected]
                    rest = [candidate for candidate in memory_candidates if not candidate.selected]
                    memory_candidates = [
                        replace(candidate, rank=position)
                        for position, candidate in enumerate(
                            [*winners, *backfill_candidates, *rest], start=1
                        )
                    ]
            # Window spans the whole deepened pool (baseline pool is
            # 2 x slots, coverage deepens it x POOL_MULTIPLIER), so the
            # walk can reach distinct-source instances however deep FTS
            # ranked them; group-key checks are O(1) per candidate.
            memory_candidates, coverage_memory_demotions = vnext_coverage_query.apply_instance_diversity(
                memory_candidates,
                group_key_for=vnext_coverage_query.memory_provenance_group_key,
                limit=max_items,
                consider_multiplier=2 * vnext_coverage_query.COVERAGE_POOL_MULTIPLIER,
            )
        # ---- coverage mode (aggregation intent) end ----------------------

        # ---- coverage mode (roll-up card ranking) begin -------------------
        # An ACCEPTED roll-up card pre-aggregates its member instances, so
        # for an aggregation query the card is the aggregate answer and the
        # members are its receipts — yet RRF ranks the card below its own
        # members (each member matches the query about as well and there
        # are more of them), so the receipts eat the selection slots and
        # the card never packs. When >= COVERAGE_MIN_SLOTTED_MEMBERS of a
        # card's members hold selection slots (the receipts pile-up is
        # real; a lone slotted member is an ordinary hit and, measured on
        # the free probe, promoting on one only spent tail slots), the
        # card is promoted to the best member's rank; members stay in the
        # pool directly below it (demote-not-drop — only the last slot
        # holder loses selection). Runs AFTER the diversity pass so the
        # promoted order is final, and at most
        # COVERAGE_MAX_CARD_PROMOTIONS cards promote per pack. Dormant
        # (memory_candidates untouched, byte-identical pack) unless the
        # intent gate fired above AND an accepted card co-occurs with
        # enough slot-holding members; disclosed as card_promotions on the
        # coverage_mode trace stage.
        coverage_card_promotions = 0
        if coverage_intent is not None:
            memory_candidates, coverage_card_promotions = vnext_coverage_query.promote_rollup_cards(
                memory_candidates
            )
        # ---- coverage mode (roll-up card ranking) end ---------------------

        if sources_enabled:
            source_lists, sources_stage_record = self._source_stage_lists(
                query=request.query,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
                limit=max(DEFAULT_SOURCE_LIMIT, max_items),
                winning_memories=provenance_memories,
                anchor=anchor,
            )
        else:
            source_lists = {}
            sources_stage_status = (
                SOURCES_STAGE_DISABLED_BY_FLAG if request.include_sources is False else STAGE_DISABLED_MINIMAL
            )
            sources_stage_record = {"candidate_count": 0, "status": sources_stage_status}
        open_loop_rows = self.store.list_open_loops(
            status="open",
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_OPEN_LOOP_LIMIT,
        )

        source_candidates = _fused_candidates(
            source_lists,
            target_type="source",
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_SOURCE_LIMIT,
        )
        # ---- coverage mode (aggregation intent) begin --------------------
        # Instance-diversity pass over the fused sources: near-verbatim
        # duplicate sources are demoted behind distinct same-topic
        # instances so aggregation questions see every instance instead of
        # the same content repeated. Dormant (coverage_record is None, no
        # trace stage) unless the intent gate fired above.
        coverage_record: JsonObject | None = None
        if coverage_intent is not None:
            coverage_text_for = vnext_coverage_query.source_chunk_text_provider(
                getattr(self.store, "list_source_chunks", None)
            )
            coverage_source_demotions = 0
            if coverage_text_for is not None:
                source_candidates, coverage_source_demotions = vnext_coverage_query.apply_instance_diversity(
                    source_candidates,
                    text_for=coverage_text_for,
                    limit=DEFAULT_SOURCE_LIMIT,
                )
            coverage_record = vnext_coverage_query.coverage_stage_record(
                intent=coverage_intent,
                clause_count=len(coverage_clauses),
                clause_candidate_count=coverage_clause_candidate_count,
                source_diversity_enabled=coverage_text_for is not None,
                memory_demotions=coverage_memory_demotions,
                source_demotions=coverage_source_demotions,
                # roll-up card ranking (see the marked block above).
                card_promotions=coverage_card_promotions,
            )
        # ---- coverage mode (aggregation intent) end ----------------------
        open_loop_candidates = _fused_candidates(
            {"listing": open_loop_rows},
            target_type="open_loop",
            domains=domains,
            sensitivity_allowed=sensitivity_allowed,
            limit=DEFAULT_OPEN_LOOP_LIMIT,
        )

        ranked_memories = [_compact_item(candidate.item) for candidate in memory_candidates if candidate.selected]
        ordered_memories = _order_memories_for_strategy(ranked_memories, strategy)
        # Current-version preference (demote-not-drop): when a supersession
        # pair leaks into the same pack, the replacement packs directly
        # above its superseded ancestor; every other item keeps its order.
        ordered_memories, supersession_reorders = _prefer_current_versions(ordered_memories)
        ranked_sources = [_compact_item(candidate.item) for candidate in source_candidates if candidate.selected]
        ranked_open_loops = [_compact_item(candidate.item) for candidate in open_loop_candidates if candidate.selected]

        # Greedy token-budget packing, section by section in the strategy's
        # order (balanced: memories, open loops, sources, provenance quotes,
        # contradictions). Derived sections (supporting/contradicting
        # evidence) come from the memories packed so far; when a strategy
        # packs contradictions before memories, they derive from the
        # ranking-selected (pre-budget) memories instead.
        contradictions_not_requested_status = (
            STAGE_DISABLED_MINIMAL
            if depth == CONTEXT_DEPTH_MINIMAL and request.include_contradictions is None
            else CONTRADICTIONS_STAGE_NOT_REQUESTED
        )
        budget = _TokenBudget(token_budget=request.max_tokens, strategy=strategy)
        selected_memories: list[JsonObject] = []
        selected_open_loops: list[JsonObject] = []
        selected_sources: list[JsonObject] = []
        supporting_evidence: list[JsonObject] = []
        contradicting_evidence: list[JsonObject] = []
        contradictions_stage = contradictions_not_requested_status
        memories_packed = False
        for section in BUDGET_STRATEGY_SECTION_ORDERS[strategy]:
            budget.open_section(section)
            if section == SECTION_RELEVANT_MEMORIES:
                selected_memories = [item for item in ordered_memories if budget.admit(item, section=section)]
                memories_packed = True
            elif section == SECTION_OPEN_LOOPS:
                selected_open_loops = [item for item in ranked_open_loops if budget.admit(item, section=section)]
            elif section == SECTION_SOURCES:
                selected_sources = [item for item in ranked_sources if budget.admit(item, section=section)]
            elif section == SECTION_SUPPORTING_EVIDENCE:
                evidence_base = selected_memories if memories_packed else ordered_memories
                supporting_evidence = [
                    evidence
                    for evidence in self._supporting_evidence(evidence_base)
                    if budget.admit(evidence, section=section)
                ]
            elif section == SECTION_CONTRADICTING_EVIDENCE:
                contradiction_base = selected_memories if memories_packed else ordered_memories
                contradiction_records, contradictions_stage = self._contradicting_evidence(
                    contradiction_base,
                    requested=contradictions_requested,
                    domains=domains,
                    sensitivity_allowed=sensitivity_allowed,
                    not_requested_status=contradictions_not_requested_status,
                )
                contradicting_evidence = [
                    record for record in contradiction_records if budget.admit(record, section=section)
                ]
        memory_candidates = _apply_budget_exclusions(memory_candidates, selected_memories)
        open_loop_candidates = _apply_budget_exclusions(open_loop_candidates, selected_open_loops)
        source_candidates = _apply_budget_exclusions(source_candidates, selected_sources)

        now = datetime.now(UTC)
        # Pack-local back-pointers: a pack-mate's supersedes pointer marks
        # its ancestor as superseded even when the ancestor row never
        # received the superseded_by column (one-sided patches). First
        # claim wins, mirroring _prefer_current_versions.
        superseded_by_packmate: dict[str, str] = {}
        for memory in selected_memories:
            supersedes_pointer = memory.get("supersedes")
            if supersedes_pointer:
                superseded_by_packmate.setdefault(str(supersedes_pointer), str(memory.get("id")))
        for memory in selected_memories:
            staleness = _staleness_note(memory, now=now)
            if staleness is not None:
                memory["staleness"] = staleness
            validity = _validity_annotation(
                memory,
                superseded_by_hint=superseded_by_packmate.get(str(memory.get("id"))),
            )
            if validity is not None:
                memory["validity"] = validity

        supersession_context: list[JsonObject] | None = None
        if depth == CONTEXT_DEPTH_HIGH:
            supersession_context = self._supersession_context(selected_memories)

        if depth == CONTEXT_DEPTH_MINIMAL:
            recent_changes: list[JsonObject] | None = None
            recent_changes_stage_record: JsonObject = {"status": STAGE_DISABLED_MINIMAL, "candidate_count": 0}
        else:
            recent_changes = self._recent_changes()
            recent_changes_stage_record = {"candidate_count": len(recent_changes)}

        warnings = self._warnings(
            memory_candidates=memory_candidates,
            source_candidates=source_candidates,
            open_loop_candidates=open_loop_candidates,
        )
        all_candidates = [*memory_candidates, *source_candidates, *open_loop_candidates]
        excluded_counts: dict[str, int] = {}
        for candidate in all_candidates:
            if candidate.exclusion_reason is None:
                continue
            excluded_counts[candidate.exclusion_reason] = excluded_counts.get(candidate.exclusion_reason, 0) + 1
        selected_trace = [candidate.to_trace_record() for candidate in all_candidates if candidate.selected]
        trace = {
            "trace_id": trace_id,
            "candidate_count": len(all_candidates),
            "selected_count": len(selected_trace),
            "query_terms": terms,
            "filters": {
                "domains": domains,
                "sensitivity_allowed": sensitivity_allowed,
                "time_window": request.time_window,
                "memory_types": list(memory_types),
                "projects": list(projects),
                "created_by_agent_ids": list(created_by_agent_ids),
                "run_id": filter_run_id,
            },
            "fusion": {
                "algorithm": "reciprocal_rank_fusion",
                "k": RRF_K,
                # Honest disclosure: equal-score ties resolve on row content
                # (see content_stable_tiebreak), no longer on the raw id.
                "tie_break": TIE_BREAK_CONTENT_STABLE,
            },
            "vector_stage": vector_stage,
            "context_depth": depth,
            "budget_strategy": strategy,
            "budget": budget.to_record(),
            "supersession_reorders": supersession_reorders,
            "stages": {
                "fts": {"source": fts_source, "candidate_count": len(fts_rows)},
                "vector": {"status": vector_stage, "candidate_count": len(vector_rows)},
                "graph": {
                    "status": graph_stage,
                    "matched_entities": matched_entities,
                    "candidate_count": len(graph_rows),
                },
                "sources": sources_stage_record,
                "open_loops": {"candidate_count": len(open_loop_rows)},
                "contradictions": {"status": contradictions_stage, "candidate_count": len(contradicting_evidence)},
                "recent_changes": recent_changes_stage_record,
            },
            "selected": selected_trace,
            "excluded_counts": excluded_counts,
        }
        if temporal_stage_record is not None:
            trace["stages"]["temporal_anchor"] = temporal_stage_record  # type: ignore[index]
        if supersession_context is not None:
            trace["stages"]["supersession"] = {  # type: ignore[index]
                "status": SUPERSESSION_STAGE_ENABLED,
                "candidate_count": len(supersession_context),
            }
        if coverage_record is not None:
            # coverage mode (aggregation intent): absent when dormant so
            # ungated traces stay byte-identical.
            trace["stages"][vnext_coverage_query.COVERAGE_STAGE] = coverage_record  # type: ignore[index]
        pack: JsonObject = {
            "context_pack_id": context_pack_id,
            "query_interpretation": interpretation,
        }
        if matched_entities:
            # WHO the pack is about: compact resolved entities from the
            # graph stage. Only present when the query matched entities.
            pack["entities"] = matched_entities
        pack.update({
            # Compact references only; the full rows appear once, in
            # relevant_memories.
            "current_known_state": [_memory_reference(item) for item in selected_memories],
            "relevant_memories": selected_memories,
        })
        if depth != CONTEXT_DEPTH_MINIMAL:
            # Typed sections are views over relevant_memories; minimal
            # keeps only the memories themselves.
            pack.update({
                "relevant_beliefs": [
                    item for item in selected_memories if item.get("memory_type") in {"belief", "thesis"}
                ],
                "decisions": [item for item in selected_memories if item.get("memory_type") == "decision"],
                "procedures": [
                    item for item in selected_memories if item.get("memory_type") in {"procedure", "routine"}
                ],
            })
        pack.update({
            "open_loops": selected_open_loops,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": contradicting_evidence,
        })
        if recent_changes is not None:
            pack["recent_changes"] = recent_changes
        if supersession_context is not None:
            pack["supersession_context"] = supersession_context
        pack.update({
            "missing_information": self._missing_information(
                selected_memories, selected_sources, sources_enabled=sources_enabled
            ),
            "sources": selected_sources,
            "warnings": warnings,
            "budget": budget.to_record(),
            "context_depth": depth,
            "trace_id": trace_id,
            "trace": trace,
            "agent_identity": request.agent_identity,
            "policy_decision": request.policy_decision,
        })
        # -- entity grounding (vnext_grounding integration; single block) ------
        # Pack-level retrieval statistic: salient query entities with ZERO
        # corpus support (entity substrate miss AND one-row FTS probe miss).
        # Read-only, additive, and absent for every ungated query -- packs
        # without unsupported entities are byte-identical to the old path.
        # Skipped at minimal depth to preserve its cheapest-call promise.
        if depth != CONTEXT_DEPTH_MINIMAL:
            grounding = compute_query_grounding(
                self.store,
                request.query,
                domains=domains,
                sensitivity_allowed=sensitivity_allowed,
            )
            if grounding is not None:
                pack["grounding"] = grounding
                trace["grounding"] = dict(grounding)
        # -- end entity grounding ----------------------------------------------
        append_event(
            self.store,
            event_type="retrieval.context_pack_compiled",
            actor_type=request.actor_type,
            actor_id=request.actor_id,
            target_type="context_pack",
            target_id=context_pack_id,
            trace_id=trace_id,
            run_id=request.run_id,
            payload={
                "query": request.query,
                "query_type": interpretation["query_type"],
                "candidate_count": trace["candidate_count"],
                "selected_count": trace["selected_count"],
                "vector_stage": vector_stage,
                "graph_stage": graph_stage,
                "context_depth": depth,
                "budget_strategy": strategy,
                "budget": budget.to_record(),
                "warnings": warnings,
                "agent_identity": request.agent_identity,
                "policy_decision": request.policy_decision,
            },
        )
        if request.actor_type == "agent" and request.actor_id is not None:
            append_event(
                self.store,
                event_type="agent.context_pack_requested",
                actor_type="agent",
                actor_id=request.actor_id,
                target_type="context_pack",
                target_id=context_pack_id,
                trace_id=trace_id,
                run_id=request.run_id,
                payload={
                    "query": request.query,
                    "query_type": interpretation["query_type"],
                    "selected_count": trace["selected_count"],
                    "agent_identity": request.agent_identity,
                    "policy_decision": request.policy_decision,
                },
            )
        return pack

    def _contradicting_evidence(
        self,
        memories: list[JsonObject],
        *,
        requested: bool,
        domains: list[str],
        sensitivity_allowed: list[str],
        not_requested_status: str = CONTRADICTIONS_STAGE_NOT_REQUESTED,
    ) -> tuple[list[JsonObject], str]:
        """Contradiction candidates between the selected memories and active beliefs.

        Reuses the pure detection helpers behind VNextContradictionService
        without persisting edges, artifacts, or events (read-only path).
        Stores without ``list_beliefs`` (e.g. the SQLite on-ramp) degrade
        to an empty section with an honest stage status.
        """
        if not requested:
            return [], not_requested_status
        list_beliefs = getattr(self.store, "list_beliefs", None)
        if not callable(list_beliefs):
            return [], CONTRADICTIONS_STAGE_NO_STORE_SUPPORT
        limit = vnext_contradictions.DEFAULT_CONTRADICTION_LIMIT
        new_items = [memory for memory in memories if memory.get("memory_type") not in {"belief", "thesis"}]
        if not new_items:
            return [], CONTRADICTIONS_STAGE_ENABLED
        beliefs = list_beliefs(
            status="active",
            domains=domains or None,
            sensitivity_allowed=sensitivity_allowed,
            limit=max(limit * 2, limit),
        )
        candidates = vnext_contradictions._find_candidates(  # noqa: SLF001 - deliberate read-only reuse
            new_items=new_items,
            beliefs=list(beliefs),
            limit=limit,
        )
        return [candidate.to_record() for candidate in candidates], CONTRADICTIONS_STAGE_ENABLED

    def _recent_changes(self, *, limit: int = DEFAULT_RECENT_CHANGES_LIMIT) -> list[JsonObject]:
        """Most recent ``memory.*`` events from the store event log."""
        list_events = getattr(self.store, "list_events", None)
        if not callable(list_events):
            return []
        # Fetch a few extra rows: memory-targeted events that are not
        # memory.* (e.g. provenance_link.created) are filtered out below.
        events = list_events(target_type="memory", limit=limit * 4)
        changes: list[JsonObject] = []
        for event in events:
            event_type = str(event.get("event_type") or "")
            if not event_type.startswith("memory."):
                continue
            changes.append(
                {
                    "event_id": str(event.get("id")),
                    "event_type": event_type,
                    "target_id": event.get("target_id"),
                    "occurred_at": event.get("occurred_at"),
                    "actor_type": event.get("actor_type"),
                }
            )
            if len(changes) >= limit:
                break
        return changes

    def _supporting_evidence(self, memories: list[JsonObject]) -> list[JsonObject]:
        evidence: list[JsonObject] = []
        for memory in memories:
            memory_id = str(memory.get("id"))
            for link in self.store.list_provenance_links(target_type="memory", target_id=memory_id):
                evidence.append(
                    {
                        "target_type": "memory",
                        "target_id": memory_id,
                        "source_id": link.get("source_id"),
                        "source_chunk_id": link.get("source_chunk_id"),
                        "quote": link.get("quote"),
                        "evidence_role": link.get("evidence_role"),
                        "confidence": link.get("confidence"),
                    }
                )
        return evidence

    @staticmethod
    def _warnings(
        *,
        memory_candidates: list[RetrievalCandidate],
        source_candidates: list[RetrievalCandidate],
        open_loop_candidates: list[RetrievalCandidate],
    ) -> list[str]:
        candidates = [*memory_candidates, *source_candidates, *open_loop_candidates]
        warnings: list[str] = []
        if not any(candidate.selected for candidate in memory_candidates):
            warnings.append("no_relevant_memories_selected")
        if any(candidate.exclusion_reason == "sensitivity_filtered" for candidate in candidates):
            warnings.append("sensitive_items_filtered")
        if any(candidate.exclusion_reason == "domain_filtered" for candidate in candidates):
            warnings.append("domain_items_filtered")
        return warnings

    @staticmethod
    def _missing_information(
        memories: list[JsonObject],
        sources: list[JsonObject],
        *,
        sources_enabled: bool = True,
    ) -> list[JsonObject]:
        missing: list[JsonObject] = []
        if not memories:
            missing.append({"kind": "memory", "reason": "No matching memory was selected."})
        if sources_enabled and not sources:
            missing.append({"kind": "source", "reason": "No matching source was selected."})
        return missing

    def _supersession_context(self, memories: list[JsonObject]) -> list[JsonObject]:
        """Compact supersession chain notes (context_depth=high only).

        For each packed memory carrying a ``supersedes`` or
        ``superseded_by`` pointer, walk each direction through
        ``get_memory`` (duck-typed; unresolvable pointers degrade to
        id-only references) up to SUPERSESSION_CHAIN_HOP_LIMIT hops with a
        cycle guard. Deterministic — chain notes quote stored rows only.
        """
        get_memory = getattr(self.store, "get_memory", None)
        resolver = get_memory if callable(get_memory) else None
        notes: list[JsonObject] = []
        for memory in memories:
            supersedes_pointer = memory.get("supersedes")
            superseded_by_pointer = memory.get("superseded_by")
            if not supersedes_pointer and not superseded_by_pointer:
                continue
            memory_id = str(memory.get("id"))
            newer = (
                self._walk_supersession_chain(
                    str(superseded_by_pointer), pointer_key="superseded_by", resolver=resolver, seen={memory_id}
                )
                if superseded_by_pointer
                else []
            )
            older = (
                self._walk_supersession_chain(
                    str(supersedes_pointer), pointer_key="supersedes", resolver=resolver, seen={memory_id}
                )
                if supersedes_pointer
                else []
            )
            note_parts: list[str] = []
            if newer:
                note_parts.append(f"superseded by {len(newer)} newer revision(s)")
            if older:
                note_parts.append(f"supersedes {len(older)} older revision(s)")
            notes.append(
                {
                    "memory_id": memory_id,
                    "superseded_by": newer,
                    "supersedes": older,
                    "note": "; ".join(note_parts),
                }
            )
        return notes

    @staticmethod
    def _walk_supersession_chain(
        start_id: str,
        *,
        pointer_key: str,
        resolver: object,
        seen: set[str],
    ) -> list[JsonObject]:
        chain: list[JsonObject] = []
        current: str | None = start_id
        while current and current not in seen and len(chain) < SUPERSESSION_CHAIN_HOP_LIMIT:
            seen.add(current)
            row = resolver(current) if callable(resolver) else None
            if row is None:
                chain.append({"id": current})
                break
            chain.append(
                {
                    "id": current,
                    "title": _memory_title(row),
                    "memory_type": row.get("memory_type"),
                    "status": row.get("status"),
                }
            )
            next_pointer = row.get(pointer_key)
            current = str(next_pointer) if next_pointer else None
        return chain


__all__ = [
    "BUDGET_STRATEGIES",
    "BUDGET_STRATEGY_BALANCED",
    "BUDGET_STRATEGY_CONTRADICTIONS_FIRST",
    "BUDGET_STRATEGY_FACTS_FIRST",
    "BUDGET_STRATEGY_RECENT_FIRST",
    "BUDGET_STRATEGY_SECTION_ORDERS",
    "BUDGET_STRATEGY_SOURCES_FIRST",
    "CONTEXT_DEPTHS",
    "CONTEXT_DEPTH_HIGH",
    "CONTEXT_DEPTH_LOW",
    "CONTEXT_DEPTH_MEDIUM",
    "CONTEXT_DEPTH_MINIMAL",
    "CONTEXT_DEPTH_MINIMAL_MAX_ITEMS",
    "CONTRADICTIONS_STAGE_ENABLED",
    "CONTRADICTIONS_STAGE_NOT_REQUESTED",
    "CONTRADICTIONS_STAGE_NO_STORE_SUPPORT",
    "DEFAULT_CONTEXT_PACK_LIMIT",
    "DEFAULT_RECENT_CHANGES_LIMIT",
    "DEFAULT_SENSITIVITY_ALLOWED",
    "FACTS_FIRST_MEMORY_TYPES",
    "ENTITY_NAME_CANDIDATE_LIMIT",
    "ENTITY_NAME_STOPWORDS",
    "EXCLUSION_REASON_TOKEN_BUDGET",
    "GRAPH_ENTITY_MATCH_LIMIT",
    "GRAPH_STAGE_DISABLED_NO_ENTITY_MATCH",
    "GRAPH_STAGE_DISABLED_NO_STORE_SUPPORT",
    "GRAPH_STAGE_ENABLED",
    "MEMORY_ENTITY_EDGE_TYPES",
    "MEMORY_SEARCHABLE_STATUSES",
    "RRF_K",
    "SECTION_CONTRADICTING_EVIDENCE",
    "SECTION_OPEN_LOOPS",
    "SECTION_RELEVANT_MEMORIES",
    "SECTION_SOURCES",
    "SECTION_SUPPORTING_EVIDENCE",
    "SOURCES_STAGE_DISABLED_BY_FLAG",
    "SOURCE_CHUNK_CANDIDATE_MULTIPLIER",
    "SOURCE_CHUNK_STAGE_DISABLED_NO_STORE_SUPPORT",
    "SOURCE_EVENT_METADATA_KEYS",
    "SOURCE_STAGE_CHUNK_FTS",
    "SOURCE_STAGE_PROVENANCE",
    "SOURCE_STAGE_TEMPORAL",
    "SOURCE_STAGE_TITLE_RECENCY",
    "STAGE_DISABLED_MINIMAL",
    "STALENESS_NOTE_AFTER_DAYS",
    "SUPERSESSION_CHAIN_HOP_LIMIT",
    "SUPERSESSION_STAGE_ENABLED",
    "TEMPORAL_STAGE_DISABLED_NO_STORE_SUPPORT",
    "TEMPORAL_STAGE_ENABLED",
    "TIE_BREAK_CONTENT_STABLE",
    "TOKEN_ESTIMATE_CHARS_PER_TOKEN",
    "VALID_TO_UNBOUNDED_YEAR",
    "VECTOR_STAGE_DISABLED_NO_PROVIDER",
    "VECTOR_STAGE_DISABLED_NO_STORE_SUPPORT",
    "VECTOR_STAGE_ENABLED",
    "VNextRetrievalRequest",
    "VNextRetrievalService",
    "VNextRetrievalStore",
    "VNextRetrievalValidationError",
    "classify_query",
    "content_stable_tiebreak",
    "entity_name_candidates",
    "estimate_item_tokens",
    "normalize_query",
    "query_terms",
    "reciprocal_rank_fusion",
]
