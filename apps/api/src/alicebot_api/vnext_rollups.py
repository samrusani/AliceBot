"""Roll-up cards: review-gated pre-aggregation of same-topic memories.

A roll-up card is ONE canonical memory whose text lists every same-topic
instance ("played — 5 instances: The Last of Us Part II (30 hours,
2023-05-10); ..."), so an aggregation-phrased recall ("summarize / count
everything about X") can hit a single card instead of needing every
instance to win a context-pack slot.

Position in the pipeline
------------------------
The roll-up pass rides the existing ``memory_consolidation`` scheduled
workflow (``VNextConsolidationService.generate_memory_consolidation``
invokes ``VNextRollupService.propose_rollups``). Nothing here runs on the
memory commit/capture path: a new memory arriving in a rolled-up topic
costs O(1) at commit time and is only picked up by the next scheduled
consolidation run, which then proposes a roll-up *revision*.

Review gate (Alice's brand, preserved)
--------------------------------------
Roll-up cards are created as ``status="candidate"`` memories carrying the
same ``metadata_json.consolidation`` block the near-duplicate proposals
use, so the existing review surface and
``VNextMemoryCommitService.accept_consolidation_candidate`` handle them
unchanged:

- ``proposal_kind`` is ``"rollup"`` and ``proposed_supersede`` is EMPTY
  for a first proposal: accepting promotes the card to a first-class
  ``active`` memory (embedding attached, entities linked, FTS/vector
  indexed like any memory) and supersedes NOTHING — members stay active
  and individually recallable. Member linkage lives in
  ``cluster_member_ids`` and per-instance records in
  ``value.rollup.instances`` (memory id, label, date, amounts, role).
- A *revision* proposal (new members arrived in an accepted roll-up's
  topic) sets ``proposed_supersede=[previous_card_id]``: accepting the
  revision retires only the outdated CARD, never the member memories.
- Candidates are invisible to retrieval (``search_memories*`` only match
  active/accepted) and to trusted-fact auto-promotion (which requires
  ``status == "active"``), so nothing auto-promotes past human review.

Deterministic grouping (no LLM required)
----------------------------------------
Two documented rules, both pure functions of the member rows:

- same-entity: members whose text mentions the same entity (via the
  deterministic ``vnext_entities`` extraction substrate, alias-folded
  through one bulk ``find_entities_by_names`` call when the store has an
  entity surface);
- lexical-topic: members sharing an anchor content token (stopword-
  filtered, lightly plural-folded) with support >= ``min_members``.

Groups whose member texts are near-identical (high mean pairwise token
Jaccard) are left to the near-duplicate dedup/merge pipeline — a roll-up
aggregates DISTINCT instances of one topic, it does not dedupe copies.

The optional model seam (``generation_mode="model_backed"`` through the
existing routing seam in ``vnext_model_intelligence``) only refines the
card's one-line summary; the deterministic instance list is always
present, complete, and correct on its own, and refusals fall back to the
deterministic card. No API key, endpoint, or model call is required for
any behavior in this module.

Storage: no new tables or columns. Cards reuse the memories table
(candidate rows + ``value``/``metadata_json`` JSON) and the existing
``memory_consolidation`` artifact/report, so no migration is needed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
import json
import re
from typing import Protocol

from alicebot_api.vnext_entities import extract_entity_candidates
from alicebot_api.vnext_model_intelligence import (
    NON_SYNTHESIZING_PROVIDERS,
    BrainModelProvider,
    VNextModelIntelligenceError,
    provider_for_route,
)
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_store import FTS_QUERY_STOPWORDS


ROLLUP_CANDIDATE_KIND = "memory_rollup"
ROLLUP_PROPOSAL_KIND = "rollup"
ROLLUP_SUMMARY_WORKFLOW = "rollup_summary"

DEFAULT_ROLLUP_MIN_MEMBERS = 3
DEFAULT_MAX_ROLLUPS = 8
DEFAULT_MAX_INSTANCES_PER_CARD = 40
MAX_GROUPABLE_MEMORIES_HARD_CAP = 5000

# Groups larger than this are skipped outright: a "topic" shared by
# hundreds of memories is a vocabulary artifact, not an aggregation
# subject, and its member list would bloat the candidate's metadata.
MAX_ROLLUP_GROUP_MEMBERS = 500

# Pairwise Jaccard for the duplicate-group guard is computed over at most
# this many members (deterministic prefix of the sorted group) so a huge
# group cannot turn the guard quadratic.
JACCARD_SAMPLE_MEMBERS = 20

# Mean pairwise token-set Jaccard at or above this marks a group as a
# near-duplicate cluster (same sentence restated), which the dedup/merge
# pipeline owns; roll-ups only aggregate distinct instances.
DUPLICATE_GROUP_JACCARD_THRESHOLD = 0.75

# Minimum token overlap between a model-refined summary and the member
# texts; below it the summary is refused as ungrounded (mirrors the
# consolidation-merge grounding guard).
ROLLUP_SUMMARY_GROUNDING_MIN_OVERLAP = 0.5

# Topic tokens that are conversational plumbing rather than topics; the
# speaker tags cover LongMemEval-style "[USER]: ..." transcripts.
_TOPIC_TOKEN_BLOCKLIST = frozenset(
    {
        "user", "assistant", "alice", "memory", "memories", "session",
        "chat", "remember", "today", "yesterday", "tomorrow", "really",
        "recently", "think", "thanks", "thank", "please", "would", "like",
        "want", "wanted", "going", "got", "get", "also", "one", "two",
        "new", "time", "lot", "bit",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'-]*")
_SURFACE_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")
# Quantities worth carrying per instance: currency-prefixed numbers and
# numbers followed by a small unit vocabulary. Bare numbers are too noisy.
_AMOUNT_RE = re.compile(
    r"(?<![\w.])("
    r"[$€£]\s?\d[\d,]*(?:\.\d+)?"
    r"|\d[\d,]*(?:\.\d+)?\s*(?:hours?|hrs?|h\b|minutes?|mins?|days?|weeks?|months?|years?|"
    r"km|kilometers?|miles?|mi\b|kg|kilograms?|lbs?|pounds?|dollars?|usd|eur|gbp|percent|%|times)"
    r")",
    re.IGNORECASE,
)
_SPEAKER_TAG_RE = re.compile(r"^\s*\[(USER|ASSISTANT)\]\s*:?", re.IGNORECASE)


class VNextRollupValidationError(ValueError):
    """Raised when roll-up options are invalid."""


class VNextRollupStore(Protocol):
    """Store surface the roll-up pass needs. ``find_entities_by_names`` is
    optional (checked via ``getattr``); without it entity grouping falls
    back to the raw extracted names (no alias folding)."""

    def create_memory(self, memory: JsonObject, *, actor_type: str = "system") -> JsonObject: ...

    def list_memories(self, *, status: str | None = None) -> list[JsonObject]: ...


@dataclass(frozen=True, slots=True)
class RollupOptions:
    """Knobs for the roll-up pass, overridable via
    ``metadata_json["rollup_options"]`` on the consolidation request."""

    min_members: int = DEFAULT_ROLLUP_MIN_MEMBERS
    max_rollups: int = DEFAULT_MAX_ROLLUPS
    max_instances_per_card: int = DEFAULT_MAX_INSTANCES_PER_CARD
    max_groupable_memories: int = MAX_GROUPABLE_MEMORIES_HARD_CAP

    @classmethod
    def from_metadata(cls, metadata_json: object) -> RollupOptions:
        overrides = metadata_json.get("rollup_options") if isinstance(metadata_json, dict) else None
        overrides = overrides if isinstance(overrides, dict) else {}

        def _int(key: str, default: int) -> int:
            value = overrides.get(key, default)
            if isinstance(value, bool) or not isinstance(value, int):
                raise VNextRollupValidationError(f"rollup_options.{key} must be an integer")
            return value

        options = cls(
            min_members=_int("min_members", DEFAULT_ROLLUP_MIN_MEMBERS),
            max_rollups=_int("max_rollups", DEFAULT_MAX_ROLLUPS),
            max_instances_per_card=_int("max_instances_per_card", DEFAULT_MAX_INSTANCES_PER_CARD),
            max_groupable_memories=_int("max_groupable_memories", MAX_GROUPABLE_MEMORIES_HARD_CAP),
        )
        if not (2 <= options.min_members <= 100):
            raise VNextRollupValidationError("rollup_options.min_members must be between 2 and 100")
        if not (1 <= options.max_rollups <= 50):
            raise VNextRollupValidationError("rollup_options.max_rollups must be between 1 and 50")
        if not (options.min_members <= options.max_instances_per_card <= 500):
            raise VNextRollupValidationError(
                "rollup_options.max_instances_per_card must be between min_members and 500"
            )
        if not (2 <= options.max_groupable_memories <= MAX_GROUPABLE_MEMORIES_HARD_CAP):
            raise VNextRollupValidationError(
                f"rollup_options.max_groupable_memories must be between 2 and {MAX_GROUPABLE_MEMORIES_HARD_CAP}"
            )
        return options

    def to_record(self) -> JsonObject:
        return {
            "min_members": self.min_members,
            "max_rollups": self.max_rollups,
            "max_instances_per_card": self.max_instances_per_card,
            "max_groupable_memories": self.max_groupable_memories,
        }


@dataclass(frozen=True, slots=True)
class _RollupGroup:
    rollup_key: str
    group_kind: str  # "entity" | "topic"
    label: str
    members: tuple[JsonObject, ...]


@dataclass(slots=True)
class RollupOutcome:
    """JSON-safe result of one roll-up pass, embedded in the consolidation
    artifact's metadata and rendered as a report section."""

    options: JsonObject = field(default_factory=dict)
    groups: list[JsonObject] = field(default_factory=list)
    proposals: list[JsonObject] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    candidate_ids: list[str] = field(default_factory=list)
    groupable_count: int = 0
    bounded: bool = False

    def to_metadata(self) -> JsonObject:
        return {
            "grouping": "deterministic_entity_and_lexical_topic",
            "options": dict(self.options),
            "groupable_memories": self.groupable_count,
            "bounded": self.bounded,
            "groups": list(self.groups),
            "proposals": list(self.proposals),
            "skipped": list(self.skipped),
        }

    def markdown_lines(self) -> list[str]:
        lines: list[str] = []
        for proposal in self.proposals:
            supersede = ", ".join(proposal.get("proposed_supersede") or []) or "none"
            lines.append(
                f"- `{proposal['rollup_digest']}` roll-up proposal "
                f"({proposal['candidate_state']}, candidate: {proposal['candidate_memory_id']}) - "
                f"topic: {proposal['label']} ({proposal['group_kind']}); "
                f"{proposal['instance_count']} instances; members stay active; "
                f"proposed supersede after acceptance: {supersede}"
                + (
                    f"; revises accepted roll-up {proposal['revises_memory_id']}"
                    if proposal.get("revises_memory_id")
                    else ""
                )
            )
        if not lines:
            lines = ["- No roll-up proposals were created this run."]
        for reason in self.skipped:
            lines.append(f"- Skipped: {reason}")
        return lines


# -- small deterministic helpers -----------------------------------------------


def _digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()[:16]


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _member_text(row: JsonObject) -> str:
    for key in ("canonical_text", "summary", "title", "memory_key"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    value = row.get("value")
    if isinstance(value, dict):
        raw = value.get("text")
        if isinstance(raw, str) and raw.strip():
            return " ".join(raw.split())
    return str(row.get("id", "item"))


def _light_stem(token: str) -> str:
    """Deliberately crude plural fold used ONLY for grouping keys (never
    displayed): 'games' and 'game' share one topic anchor."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _topic_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in _TOKEN_RE.findall(text.casefold()):
        # A topic token needs at least one letter: bare numbers and dates
        # ("2023-06-02") are instance data, not aggregation subjects.
        if len(raw) < 3 or not any(char.isalpha() for char in raw):
            continue
        if raw in FTS_QUERY_STOPWORDS or raw in _TOPIC_TOKEN_BLOCKLIST:
            continue
        stemmed = _light_stem(raw)
        if stemmed in FTS_QUERY_STOPWORDS or stemmed in _TOPIC_TOKEN_BLOCKLIST:
            continue
        tokens.add(stemmed)
    return tokens


def _surface_form(members: tuple[JsonObject, ...], anchor: str) -> str:
    """Most frequent original surface form whose light stem equals
    ``anchor`` (ties break alphabetically) — labels show real words."""
    counts: Counter[str] = Counter()
    for member in members:
        for raw in _SURFACE_TOKEN_RE.findall(_member_text(member)):
            lowered = raw.casefold()
            if _light_stem(lowered) == anchor:
                counts[lowered] += 1
    if not counts:
        return anchor
    return min(counts, key=lambda token: (-counts[token], token))


def _mean_pairwise_jaccard(token_sets: list[set[str]]) -> float:
    pairs: list[float] = []
    for index, left in enumerate(token_sets):
        for right in token_sets[index + 1 :]:
            union = left | right
            pairs.append(len(left & right) / len(union) if union else 1.0)
    return sum(pairs) / len(pairs) if pairs else 0.0


def _member_date(row: JsonObject) -> str | None:
    """Best-effort per-instance date: explicit content dates first
    (``metadata_json.session_date``, ``value.date``), then row event time."""
    metadata = row.get("metadata_json")
    if isinstance(metadata, dict):
        session_date = metadata.get("session_date")
        if isinstance(session_date, str) and len(session_date) >= 8:
            return session_date[:10]
    value = row.get("value")
    if isinstance(value, dict):
        content_date = value.get("date")
        if isinstance(content_date, str) and len(content_date) >= 8:
            return content_date[:10]
    for key in ("first_seen_at", "created_at", "last_seen_at"):
        stamp = row.get(key)
        if isinstance(stamp, datetime):
            return stamp.date().isoformat()
        if isinstance(stamp, date):
            return stamp.isoformat()
        if isinstance(stamp, str) and len(stamp) >= 10:
            return stamp[:10]
    return None


def _member_role(row: JsonObject) -> str | None:
    """USER/ASSISTANT provenance when the member carries it (metadata keys
    or a leading speaker tag in the text)."""
    metadata = row.get("metadata_json")
    for container in (metadata, row.get("value")):
        if isinstance(container, dict):
            for key in ("speaker", "speaker_role", "role"):
                value = container.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().upper()
    for key in ("canonical_text", "title"):
        text = row.get(key)
        if isinstance(text, str):
            match = _SPEAKER_TAG_RE.match(text)
            if match:
                return match.group(1).upper()
    value = row.get("value")
    if isinstance(value, dict) and isinstance(value.get("text"), str):
        match = _SPEAKER_TAG_RE.match(value["text"])
        if match:
            return match.group(1).upper()
    return None


def _member_amounts(text: str, *, limit: int = 4) -> list[str]:
    amounts: list[str] = []
    for match in _AMOUNT_RE.finditer(text):
        surface = " ".join(match.group(1).split())
        if surface not in amounts:
            amounts.append(surface)
        if len(amounts) >= limit:
            break
    return amounts


def _strip_speaker_tag(text: str) -> str:
    return _SPEAKER_TAG_RE.sub("", text, count=1).strip()


def _instance_label(row: JsonObject, *, exclude_normalized: str | None = None) -> str:
    """Entity surface when extraction finds one, else the member title,
    else the truncated text — short, deterministic, display-safe.

    ``exclude_normalized`` skips the group's own entity so an entity-group
    card labels each instance by its distinguishing content, not by the
    shared entity name repeated N times."""
    text = _strip_speaker_tag(_member_text(row))
    candidates = [
        candidate
        for candidate in extract_entity_candidates(text)
        if candidate.normalized != exclude_normalized
    ]
    if candidates:
        best = max(candidates, key=lambda candidate: (candidate.confidence, candidate.occurrences))
        return best.name
    title = row.get("title")
    if isinstance(title, str) and title.strip():
        return _strip_speaker_tag(" ".join(title.split()))[:80]
    return text[:80]


def _instance_record(row: JsonObject, *, exclude_normalized: str | None = None) -> JsonObject:
    text = _strip_speaker_tag(_member_text(row))
    record: JsonObject = {
        "memory_id": str(row.get("id")),
        "label": _instance_label(row, exclude_normalized=exclude_normalized),
        "date": _member_date(row),
        "amounts": _member_amounts(text),
        "text": text[:200],
    }
    role = _member_role(row)
    if role is not None:
        record["role"] = role
    return record


def _render_instance(instance: JsonObject) -> str:
    details: list[str] = []
    amounts = instance.get("amounts")
    if isinstance(amounts, list) and amounts:
        details.append(", ".join(str(amount) for amount in amounts))
    if instance.get("date"):
        details.append(str(instance["date"]))
    if instance.get("role"):
        details.append(str(instance["role"]))
    label = str(instance["label"])
    return f"{label} ({'; '.join(details)})" if details else label


def _sorted_members(members: list[JsonObject]) -> tuple[JsonObject, ...]:
    return tuple(
        sorted(
            members,
            key=lambda row: (
                _member_date(row) or "9999-99-99",
                str(row.get("created_at") or ""),
                str(row.get("id")),
            ),
        )
    )


def _scoped_rows(
    rows: list[JsonObject],
    *,
    domains: list[str] | None,
    sensitivity_allowed: list[str],
) -> list[JsonObject]:
    """Domain/sensitivity scoping, mirroring the consolidation service."""
    allowed = set(sensitivity_allowed)
    scoped: list[JsonObject] = []
    for row in rows:
        sensitivity = str(row.get("sensitivity") or "unknown")
        if sensitivity not in allowed:
            continue
        if domains:
            domain = str(row.get("domain") or "unknown")
            if domain not in domains and domain != "unknown":
                continue
        scoped.append(row)
    return scoped


def _is_rollup_card(row: JsonObject) -> bool:
    metadata = row.get("metadata_json")
    return isinstance(metadata, dict) and metadata.get("candidate_kind") == ROLLUP_CANDIDATE_KIND


def _highest_sensitivity(rows: tuple[JsonObject, ...]) -> str:
    rank = {
        "public": 1,
        "internal": 2,
        "unknown": 2,
        "private": 3,
        "confidential": 4,
        "highly_sensitive": 5,
        "sacred": 6,
        "regulated": 6,
    }
    sensitivities = [str(row.get("sensitivity", "unknown")) for row in rows]
    if not sensitivities:
        return "unknown"
    return max(sensitivities, key=lambda value: rank.get(value, rank["unknown"]))


def _dominant_domain(rows: tuple[JsonObject, ...]) -> str:
    domains = {row.get("domain") for row in rows if isinstance(row.get("domain"), str)}
    if len(domains) == 1:
        return str(next(iter(domains)))
    return "unknown"


def _dominant_memory_type(rows: tuple[JsonObject, ...]) -> str:
    counts = Counter(str(row.get("memory_type")) for row in rows if isinstance(row.get("memory_type"), str))
    return counts.most_common(1)[0][0] if counts else "semantic"


# -- optional model refinement (existing routing seam, deterministic fallback) --


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(text.casefold())
        if len(token) >= 3 and token not in FTS_QUERY_STOPWORDS
    }


def _grounding_overlap(summary: str, members: tuple[JsonObject, ...]) -> float:
    summary_tokens = _content_tokens(summary)
    if not summary_tokens:
        return 0.0
    member_tokens: set[str] = set()
    for member in members:
        member_tokens |= _content_tokens(_member_text(member))
    if not member_tokens:
        return 0.0
    return len(summary_tokens & member_tokens) / len(summary_tokens)


def _clean_untrusted_line(text: str) -> str:
    cleaned = "".join(char for char in text if char == " " or char.isprintable())
    cleaned = cleaned.replace("```", "").replace("[UNTRUSTED_CONTEXT_JSON]", "")
    return " ".join(cleaned.split())[:400]


def _build_rollup_summary_prompt(context_json: str) -> str:
    return "\n\n".join(
        [
            f"Workflow: {ROLLUP_SUMMARY_WORKFLOW}",
            "The context lists DISTINCT same-topic memory instances (not duplicates).",
            "Write ONE short sentence summarizing the aggregate (counts, totals, span).",
            "Rules: use only facts present in the instances; do not invent names, dates,"
            " numbers, or totals that cannot be read directly from them.",
            'Return strict JSON only, shaped exactly as {"summary": "..."}'
            " with no markdown fences and no additional keys.",
            "[UNTRUSTED_CONTEXT_JSON]",
            context_json,
        ]
    )


def _refine_summary_with_model(
    *,
    group: _RollupGroup,
    instances: list[JsonObject],
    route,
    provider: BrainModelProvider | None,
    temperature: float,
    trace_id: str | None,
) -> tuple[str | None, JsonObject | None, str | None]:
    """(summary, provenance, refusal_reason). Deterministic refusal paths
    mirror ``generate_consolidation_merge``: routing disallows, provider is
    non-synthesizing, output unparseable, or output fails grounding."""
    context_json = json.dumps(
        {"workflow_type": ROLLUP_SUMMARY_WORKFLOW, "topic": group.label, "instances": instances},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=str,
    )
    prompt = _build_rollup_summary_prompt(context_json)
    provenance: JsonObject = {
        "workflow_type": ROLLUP_SUMMARY_WORKFLOW,
        "prompt_hash": f"sha256:{sha256(prompt.encode('utf-8')).hexdigest()}",
        "trace_id": trace_id,
        "created_at": _utc_iso(),
        "prompt_injection_guard": "source_content_untrusted_no_tool_execution",
    }
    if route is None or getattr(route, "approval_required", False) or getattr(route, "route_mode", "") == "model_disabled":
        return None, None, "model_route_disallows_synthesis"
    provider = provider or provider_for_route(route)
    provenance = {**provenance, "provider": provider.provider, "model": provider.model, "routing": route.to_record()}
    if provider.provider in NON_SYNTHESIZING_PROVIDERS:
        return None, provenance, "deterministic_provider_refuses_rollup_summary"
    try:
        raw = provider.chat(prompt=prompt, temperature=temperature)
    except VNextModelIntelligenceError as exc:
        return None, provenance, f"provider_error: {exc}"
    try:
        parsed = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```"))
    except json.JSONDecodeError:
        return None, provenance, "unparseable_model_output"
    if not isinstance(parsed, dict):
        return None, provenance, "unparseable_model_output"
    summary = _clean_untrusted_line(str(parsed.get("summary") or ""))
    if not summary:
        return None, provenance, "empty_model_output"
    overlap = _grounding_overlap(summary, group.members)
    if overlap < ROLLUP_SUMMARY_GROUNDING_MIN_OVERLAP:
        return None, provenance, f"ungrounded_model_output: token_overlap={overlap:.2f}"
    return summary, {**provenance, "grounding_token_overlap": round(overlap, 4)}, None


# -- service --------------------------------------------------------------------


class VNextRollupService:
    def __init__(
        self,
        store: VNextRollupStore,
        *,
        merge_provider: BrainModelProvider | None = None,
    ) -> None:
        self.store = store
        self.merge_provider = merge_provider

    # -- grouping ---------------------------------------------------------------

    def _collect_rows(
        self,
        *,
        domains: list[str] | None,
        sensitivity_allowed: list[str],
        options: RollupOptions,
    ) -> tuple[list[JsonObject], bool]:
        rows = [
            *self.store.list_memories(status="active"),
            *self.store.list_memories(status="accepted"),
        ]
        rows = _scoped_rows(rows, domains=domains, sensitivity_allowed=sensitivity_allowed)
        # Roll-up cards never re-enter grouping: a card's text lists every
        # instance label and would re-anchor its own topic each run.
        rows = [row for row in rows if not _is_rollup_card(row)]
        # Insertion-order independent: grouping sees one canonical order.
        rows.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("id"))))
        bounded = len(rows) > options.max_groupable_memories
        if bounded:
            rows = rows[-options.max_groupable_memories :]
        return rows, bounded

    def _entity_key_maps(
        self, row_candidates: list[tuple[JsonObject, tuple]]
    ) -> dict[str, tuple[str, str]]:
        """member normalized-entity-name -> (canonical key, display name).

        One bulk ``find_entities_by_names`` call folds aliases onto their
        canonical entity when the store has an entity surface; otherwise
        the extracted normalized name is its own key.
        """
        extracted: dict[str, str] = {}
        for _row, candidates in row_candidates:
            for candidate in candidates:
                extracted.setdefault(candidate.normalized, candidate.name)
        if not extracted:
            return {}
        mapping = {normalized: (normalized, display) for normalized, display in extracted.items()}
        finder = getattr(self.store, "find_entities_by_names", None)
        if callable(finder):
            for entity in finder(tuple(sorted(extracted))):
                canonical = str(entity.get("normalized_name") or "")
                if not canonical:
                    continue
                display = str(entity.get("name") or extracted.get(canonical, canonical))
                names = [canonical]
                aliases = entity.get("aliases")
                if isinstance(aliases, (list, tuple)):
                    names.extend(str(alias) for alias in aliases)
                for name in names:
                    if name in mapping:
                        mapping[name] = (canonical, display)
        return mapping

    def _group_members(
        self,
        rows: list[JsonObject],
        *,
        options: RollupOptions,
        exclude_member_id_sets: list[set[str]],
    ) -> tuple[list[_RollupGroup], list[str]]:
        skipped: list[str] = []
        claimed: set[str] = set()
        groups: list[_RollupGroup] = []

        def _admit(key: str, kind: str, label: str, members: list[JsonObject]) -> None:
            if len(members) > MAX_ROLLUP_GROUP_MEMBERS:
                skipped.append(f"group_too_large: {key} (members={len(members)})")
                return
            member_ids = {str(member.get("id")) for member in members}
            # Groups fully covered by a near-duplicate cluster belong to the
            # dedup/merge pipeline; a roll-up aggregates distinct instances.
            if any(member_ids <= excluded for excluded in exclude_member_id_sets):
                skipped.append(f"covered_by_near_duplicate_cluster: {key} (members={len(members)})")
                return
            token_sets = [
                _topic_tokens(_member_text(member)) for member in members[:JACCARD_SAMPLE_MEMBERS]
            ]
            jaccard = _mean_pairwise_jaccard(token_sets)
            if jaccard >= DUPLICATE_GROUP_JACCARD_THRESHOLD:
                skipped.append(
                    f"near_duplicate_group_left_to_dedup: {key} "
                    f"(mean_jaccard={jaccard:.2f}, members={len(members)})"
                )
                return
            claimed.update(member_ids)
            groups.append(
                _RollupGroup(rollup_key=key, group_kind=kind, label=label, members=_sorted_members(members))
            )

        # One extraction pass per row; both grouping passes reuse it.
        row_candidates = [
            (row, extract_entity_candidates(_strip_speaker_tag(_member_text(row)))) for row in rows
        ]

        # Pass 1 — same-entity groups (more precise; they claim members first).
        entity_map = self._entity_key_maps(row_candidates)
        entity_members: dict[str, list[JsonObject]] = {}
        entity_display: dict[str, str] = {}
        for row, candidates in row_candidates:
            seen_keys: set[str] = set()
            for candidate in candidates:
                key, display = entity_map.get(candidate.normalized, (candidate.normalized, candidate.name))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                entity_members.setdefault(key, []).append(row)
                entity_display.setdefault(key, display)
        for key in sorted(entity_members, key=lambda name: (-len(entity_members[name]), name)):
            members = [row for row in entity_members[key] if str(row.get("id")) not in claimed]
            if len(members) < options.min_members:
                continue
            _admit(f"entity:{key}", "entity", entity_display[key], members)

        # Pass 2 — lexical-topic anchors over members no entity group claimed.
        remaining = [row for row in rows if str(row.get("id")) not in claimed]
        anchor_members: dict[str, list[JsonObject]] = {}
        for row in remaining:
            for token in sorted(_topic_tokens(_member_text(row))):
                anchor_members.setdefault(token, []).append(row)
        for anchor in sorted(anchor_members, key=lambda token: (-len(anchor_members[token]), token)):
            members = [row for row in anchor_members[anchor] if str(row.get("id")) not in claimed]
            if len(members) < options.min_members:
                continue
            # Label: up to two topic stems shared by EVERY member (surface
            # forms), so the card carries the words an aggregation query
            # would use ("hours played"), not just the single anchor.
            shared = set.intersection(*(_topic_tokens(_member_text(member)) for member in members))
            ordered = sorted(shared, key=lambda token: (-len(anchor_members.get(token, ())), token)) or [anchor]
            label = " ".join(_surface_form(tuple(members), stem) for stem in ordered[:2])
            _admit(f"topic:{anchor}", "topic", label, members)

        return groups, skipped

    # -- accepted / pending state -------------------------------------------------

    def _existing_rollup_state(self) -> tuple[dict[str, str], dict[str, JsonObject]]:
        """(pending candidate by rollup_digest, accepted card by rollup_key)."""
        pending: dict[str, str] = {}
        for row in self.store.list_memories(status="candidate"):
            metadata = row.get("metadata_json")
            if not isinstance(metadata, dict) or row.get("id") is None:
                continue
            digest = metadata.get("rollup_digest")
            if isinstance(digest, str) and digest:
                pending.setdefault(digest, str(row["id"]))
        accepted: dict[str, JsonObject] = {}
        for status in ("active", "accepted"):
            for row in self.store.list_memories(status=status):
                metadata = row.get("metadata_json")
                if not isinstance(metadata, dict) or metadata.get("candidate_kind") != ROLLUP_CANDIDATE_KIND:
                    continue
                key = metadata.get("rollup_key")
                if isinstance(key, str) and key and key not in accepted:
                    accepted[key] = row
        return pending, accepted


    # -- card assembly --------------------------------------------------------------

    def _render_card(
        self,
        *,
        group: _RollupGroup,
        instances: list[JsonObject],
        model_summary: str | None,
    ) -> tuple[str, str, str]:
        """(title, canonical_text, summary) — deterministic; the optional
        model summary is appended as a clearly-labelled extra sentence."""
        rendered = "; ".join(_render_instance(instance) for instance in instances)
        title = f"Roll-up: {group.label} ({len(instances)} instances in total)"
        canonical_text = f"{group.label} — {len(instances)} instances in total: {rendered}."
        if model_summary:
            canonical_text = f"{canonical_text} Summary: {model_summary}"
        summary = canonical_text[:280]
        return title, canonical_text, summary

    def _create_rollup_candidate(
        self,
        *,
        group: _RollupGroup,
        instances: list[JsonObject],
        rollup_digest: str,
        title: str,
        canonical_text: str,
        summary: str,
        revises_memory_id: str | None,
        proposed_supersede: list[str],
        model_provenance: JsonObject | None,
        merge_refusal: str | None,
        generated_by: str,
        trace_id: str | None,
    ) -> JsonObject:
        member_ids = [str(instance["memory_id"]) for instance in instances]
        source_refs = [f"memory:{member_id}" for member_id in member_ids]
        # Provenance parity with the merge/dedup proposals: the card carries
        # the union of its LISTED instances' source events (bounded by the
        # per-card instance cap).
        listed = {str(instance["memory_id"]) for instance in instances}
        source_event_ids: list[str] = []
        for member in group.members:
            if str(member.get("id")) not in listed:
                continue
            events = member.get("source_event_ids")
            if isinstance(events, list):
                source_event_ids.extend(str(item) for item in events if item is not None)
        source_event_ids = list(dict.fromkeys(source_event_ids))
        reviewer_instructions = [
            f"Review roll-up card for topic '{group.label}'; accepting it is the promotion decision.",
            "Accepting through the memory commit service (accept_consolidation_candidate) promotes this "
            "card to a first-class memory. Members are NOT superseded: they stay active and individually "
            "recallable; the card only pre-aggregates them for aggregation-style recall.",
        ]
        if revises_memory_id is not None:
            reviewer_instructions.append(
                f"This is a REVISION of accepted roll-up {revises_memory_id} (new members arrived in its "
                "topic). Accepting supersedes only that previous card, never the member memories."
            )
        reviewer_instructions.append(
            "Roll-ups never promote or supersede anything automatically; nothing changes until a reviewer accepts."
        )
        rollup_value: JsonObject = {
            "rollup_key": group.rollup_key,
            "group_kind": group.group_kind,
            "topic_label": group.label,
            "member_count": len(member_ids),
            "member_ids": member_ids,
            "instances": instances,
        }
        if revises_memory_id is not None:
            rollup_value["revises_memory_id"] = revises_memory_id
        return self.store.create_memory(
            {
                "memory_key": f"vnext.rollup.{rollup_digest}",
                "value": {"kind": ROLLUP_CANDIDATE_KIND, "text": canonical_text, "rollup": rollup_value},
                "status": "candidate",
                "memory_type": _dominant_memory_type(group.members),
                "confidence": 0.6 if model_provenance and merge_refusal is None else 0.75,
                "trust_class": "llm_single_source" if model_provenance and merge_refusal is None else "deterministic",
                "promotion_eligibility": "promotable",
                "title": title,
                "canonical_text": canonical_text,
                "summary": summary,
                "domain": _dominant_domain(group.members),
                "sensitivity": _highest_sensitivity(group.members),
                "source_event_ids": source_event_ids,
                "metadata_json": {
                    "candidate_kind": ROLLUP_CANDIDATE_KIND,
                    "rollup_digest": rollup_digest,
                    "rollup_key": group.rollup_key,
                    "review_required": True,
                    "source_refs": source_refs,
                    "trace_id": trace_id,
                    # accept_consolidation_candidate compatibility: the
                    # existing review/acceptance path reads this block.
                    "consolidation": {
                        "proposal_kind": ROLLUP_PROPOSAL_KIND,
                        "cluster_member_ids": member_ids,
                        "proposed_supersede": proposed_supersede,
                        "survivor_memory_id": None,
                        "model_provenance": model_provenance,
                        "merge_refusal": merge_refusal,
                        "reviewer_instructions": reviewer_instructions,
                        "rollup": {
                            "rollup_key": group.rollup_key,
                            "group_kind": group.group_kind,
                            "topic_label": group.label,
                            "revises_memory_id": revises_memory_id,
                        },
                    },
                },
            },
            actor_type=generated_by,
        )

    # -- entry point ------------------------------------------------------------------

    def propose_rollups(
        self,
        *,
        domains: list[str] | None = None,
        sensitivity_allowed: list[str] | None = None,
        options: RollupOptions | None = None,
        create_candidate_memories: bool = True,
        generated_by: str = "system",
        trace_id: str | None = None,
        generation_mode: str = "deterministic",
        route=None,
        model_temperature: float = 0.2,
        exclude_member_id_sets: list[set[str]] | None = None,
    ) -> RollupOutcome:
        """One review-only roll-up pass over the in-scope memories.

        Never mutates existing memories: the only writes are new
        ``status="candidate"`` roll-up cards (and only when
        ``create_candidate_memories`` is true). ``exclude_member_id_sets``
        carries the caller's near-duplicate cluster memberships so groups
        the dedup/merge pipeline already covers are not re-proposed here.
        """
        options = options or RollupOptions()
        sensitivity = list(sensitivity_allowed or ("public", "internal", "private", "unknown"))
        outcome = RollupOutcome(options=options.to_record())

        rows, bounded = self._collect_rows(domains=domains, sensitivity_allowed=sensitivity, options=options)
        outcome.groupable_count = len(rows)
        outcome.bounded = bounded
        if bounded:
            outcome.skipped.append(
                f"grouping bounded to the {options.max_groupable_memories} most recently created memories"
            )
        if len(rows) < options.min_members:
            outcome.skipped.append("fewer_memories_than_min_members")
            return outcome

        groups, group_skips = self._group_members(
            rows, options=options, exclude_member_id_sets=exclude_member_id_sets or []
        )
        outcome.skipped.extend(group_skips)
        if len(groups) > options.max_rollups:
            outcome.skipped.append(
                f"rollup_bound: {len(groups) - options.max_rollups} groups beyond "
                f"max_rollups={options.max_rollups} were not proposed this run"
            )
            groups = groups[: options.max_rollups]

        pending, accepted = self._existing_rollup_state()

        for group in groups:
            member_ids = [str(row.get("id")) for row in group.members]
            rollup_digest = _digest({"rollup_key": group.rollup_key, "member_ids": sorted(member_ids)})
            group_record: JsonObject = {
                "rollup_key": group.rollup_key,
                "group_kind": group.group_kind,
                "label": group.label,
                "member_ids": member_ids,
                "rollup_digest": rollup_digest,
            }

            accepted_card = accepted.get(group.rollup_key)
            revises_memory_id: str | None = None
            proposed_supersede: list[str] = []
            if accepted_card is not None:
                accepted_metadata = accepted_card.get("metadata_json")
                accepted_consolidation = (
                    accepted_metadata.get("consolidation") if isinstance(accepted_metadata, dict) else None
                )
                accepted_members = set()
                if isinstance(accepted_consolidation, dict):
                    accepted_members = {
                        str(member)
                        for member in (accepted_consolidation.get("cluster_member_ids") or [])
                    }
                if accepted_members == set(member_ids):
                    group_record["state"] = "already_covered_by_accepted"
                    group_record["accepted_memory_id"] = str(accepted_card.get("id"))
                    outcome.groups.append(group_record)
                    continue
                # Member set changed: propose a revision that retires only
                # the previous CARD on acceptance (never the members).
                revises_memory_id = str(accepted_card.get("id"))
                proposed_supersede = [revises_memory_id]

            if rollup_digest in pending:
                group_record["state"] = "existing_candidate"
                group_record["candidate_memory_id"] = pending[rollup_digest]
                outcome.groups.append(group_record)
                outcome.candidate_ids.append(pending[rollup_digest])
                continue

            group_entity = group.rollup_key.removeprefix("entity:") if group.group_kind == "entity" else None
            instances = [
                _instance_record(row, exclude_normalized=group_entity)
                for row in group.members[: options.max_instances_per_card]
            ]
            if len(group.members) > options.max_instances_per_card:
                outcome.skipped.append(
                    f"instance_bound: {group.rollup_key} truncated to "
                    f"{options.max_instances_per_card} of {len(group.members)} instances"
                )

            model_summary: str | None = None
            model_provenance: JsonObject | None = None
            merge_refusal: str | None = None
            if generation_mode == "model_backed":
                model_summary, model_provenance, merge_refusal = _refine_summary_with_model(
                    group=group,
                    instances=instances,
                    route=route,
                    provider=self.merge_provider,
                    temperature=model_temperature,
                    trace_id=trace_id,
                )

            title, canonical_text, summary = self._render_card(
                group=group, instances=instances, model_summary=model_summary
            )

            proposal: JsonObject = {
                **group_record,
                "instance_count": len(instances),
                "revises_memory_id": revises_memory_id,
                "proposed_supersede": proposed_supersede,
                "model_refined": model_summary is not None,
                "merge_refusal": merge_refusal,
                "source_refs": [f"memory:{member_id}" for member_id in member_ids],
            }
            if create_candidate_memories:
                candidate = self._create_rollup_candidate(
                    group=group,
                    instances=instances,
                    rollup_digest=rollup_digest,
                    title=title,
                    canonical_text=canonical_text,
                    summary=summary,
                    revises_memory_id=revises_memory_id,
                    proposed_supersede=proposed_supersede,
                    model_provenance=model_provenance,
                    merge_refusal=merge_refusal,
                    generated_by=generated_by,
                    trace_id=trace_id,
                )
                proposal["candidate_memory_id"] = str(candidate["id"])
                proposal["candidate_state"] = "created" if revises_memory_id is None else "revision_proposed"
                outcome.candidate_ids.append(str(candidate["id"]))
            else:
                proposal["candidate_memory_id"] = None
                proposal["candidate_state"] = "not_created (create_candidate_memories=false)"

            group_record["state"] = proposal["candidate_state"]
            outcome.groups.append(group_record)
            outcome.proposals.append(proposal)

        return outcome


__all__ = [
    "DEFAULT_MAX_ROLLUPS",
    "DEFAULT_ROLLUP_MIN_MEMBERS",
    "DUPLICATE_GROUP_JACCARD_THRESHOLD",
    "ROLLUP_CANDIDATE_KIND",
    "ROLLUP_PROPOSAL_KIND",
    "RollupOptions",
    "RollupOutcome",
    "VNextRollupService",
    "VNextRollupStore",
    "VNextRollupValidationError",
]
