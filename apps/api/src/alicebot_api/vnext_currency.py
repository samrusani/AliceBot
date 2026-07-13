"""Read-time same-slot update chains ("currency chains") for context packs.

The measured residue on saturated retrieval is STALE-VALUE SELECTION: the
pack contains both the old and the new value of one user-state slot
("$5,000 raised" ... "$6,200 raised"), and the reader picks the old one.
This module groups retrieved memories that describe the same slot, orders
them by supersession edges and event dates, and annotates each member so
renderers can show one compact chain block — oldest first, every entry
labeled ``[SUPERSEDED as of <date>]`` except the value that is current,
labeled ``[CURRENT as of <date>]`` and positioned last (recency-position
effect). Everything is derived from stored rows; no query or benchmark
metadata is ever read, so the trigger is question-agnostic by
construction.

Safety model (a wrong CURRENT label is worse than no label):

* Chain membership requires a SHARED derived fact key (the slot) AND, per
  temporally-adjacent pair, either an explicit supersession edge
  (``memories.superseded_by``/``supersedes``, migration 20260704_0077) or
  the same-slot value shape — both members carry exactly one value of the
  group's unit/currency class (``vnext_fact_keys`` value machinery), share
  at least one distinctive topic token, AND each state the value in
  STATIVE/CUMULATIVE terms ("I now have", "reached", "total", "raised so
  far" — see ``_STATIVE_CUE_PATTERN``) near the value in the same
  sentence. The stative cue is what separates a mutable user-state slot
  ("just reached 500 followers" -> "now at 600 followers") from episodic
  event mentions that merely share a noun ("caught 7 largemouth bass on
  the trip" vs "caught 9 largemouth bass" are two events, not an update;
  "$30 per night in Tokyo" vs "$45 per night in Kyoto" are two prices).
  So "37 coins in my collection" chains with "my collection is now 38
  coins" but never with "5 coins in the fountain".
* Two refinements keep the shape gate honest against measured failure
  modes: a prospective marker before the value vetoes the cue ("initially
  aimed to raise $200", "a goal of six to eight stories" are aspirations,
  not values — ``_PROSPECTIVE_PATTERN``), and topic tokens shared by half
  the pack are the retrieval THEME, not a slot subject, so they cannot
  carry a pair by themselves (a $600 yoga event and a $5,000 bike-a-thon
  must not chain on "charity" alone — ``_theme_anchors``).
* Ambiguous groups emit NO chain and are only counted
  (``skipped_ambiguous`` in the trace): unorderable ties (equal event
  dates across sources with different values), members without a
  resolvable event date and no edge order, multi-valued members, edge
  cycles or edge/date contradictions, overlapping candidate chains, and
  oversized groups all skip.
* Groups whose members all assert the SAME value carry no update signal
  and stay silent (no chain, no skip count) — labels only appear where a
  stale value actually coexists with a newer one.

Slot keys come from the same derivation the FTS fact keys use
(``vnext_fact_keys``): hypernym-lexicon categories ("vehicle car"),
value-stripped amount phrasings ("dollars total amount", "kilograms
weight"), plus two content shapes the value machinery implies — counted
nouns ("37 coins" -> ``count:coin``) and habitual times of day ("usually
... at 6:00 pm" -> shape only, never a grouping key on its own).

Write-side counterpart: :func:`supersession_event_time` gives the
approved-supersession path in ``vnext_memory_commit`` the replacement's
event time so the retired row's ``valid_to`` records WHEN the value
stopped being current — currency stored, not inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import re
from typing import Callable, Mapping, Sequence, cast

# Deliberate reuse of the fact-key derivation internals: slot identity must
# match the phrasings the fact keys index, and the value machinery (currency
# words, unit expansions, percent shapes) IS the definition of "same-slot
# value shape". Unlike derive_deterministic_fact_keys, slot grouping must
# not lose value keys to the novelty filter or the key cap, so it reads the
# building blocks directly.
from alicebot_api.vnext_fact_keys import (
    _CURRENCY_PATTERN,
    _CURRENCY_WORDS,
    _LEXICON_PATTERNS,
    _PERCENT_PATTERN,
    _UNIT_EXPANSIONS,
    _UNIT_PATTERN,
    _memory_text_fields,
)
from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_temporal_query import parse_event_datetime


# Trace stage key in compile_context_pack's trace["stages"].
CURRENCY_STAGE = "currency_chains"
# Pack annotation key on chain-member memories.
CURRENCY_ANNOTATION_KEY = "currency"
CURRENT_STATUS = "current"
SUPERSEDED_STATUS = "superseded"
# Groups larger than this are treated as ambiguous (a pack-wide slot-key
# pile-up is a collision smell, not an update chain).
MAX_CHAIN_MEMBERS = 8

# Memory metadata keys that carry the content's own event date (same set the
# retrieval source stage trusts, vnext_retrieval.SOURCE_EVENT_METADATA_KEYS).
_EVENT_METADATA_KEYS = ("session_date", "event_date", "date")

_NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_NUMBER_WORD_PATTERN = "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True))

# "<number> <noun>" count shape: digits or spelled numbers (incl. hyphenated
# tens compounds) followed by a plain word. The noun is filtered below.
_COUNT_PATTERN = re.compile(
    r"\b(\d{1,4}(?:,\d{3})*|(?:" + _NUMBER_WORD_PATTERN + r")(?:-(?:" + _NUMBER_WORD_PATTERN + r"))?)"
    r"\s+([A-Za-z][A-Za-z-]{2,})\b",
)

# Bare 4-digit numbers in this range are read as calendar years ("pre-1920
# American coins", "1913 Liberty Head nickel", "2019 Toyota"), never as
# counts: a "count" keyed on a year token would chain any two mentions of
# same-noun items from different years. Genuine counts this large are
# written with a thousands separator ("1,920 coins"), which stays a count.
_YEARLIKE_RANGE = (1600, 2099)

# Nouns that never name a countable possession slot: measure/currency words
# (owned by their own value classes), calendar words (durations/ages attach
# to too many different facts), function words that follow numbers in prose
# ("$75 per person", "1 for the road"), and assistant listicle nouns
# ("here are 5 tips") whose counts are not user state.
_COUNT_NOUN_EXCLUSIONS = frozenset({
    "am", "pm",
    "dollars", "euros", "pounds", "percent", "percentage",
    "dollar", "euro", "pound", "buck", "bucks", "cent", "cents", "grand",
    "usd", "eur", "gbp", "jpy", "yen", "cad", "aud", "chf", "cny", "inr",
    "km", "mi", "kg", "lb", "lbs", "hr", "hrs", "min", "mins",
    "kilometers", "kilometres", "kilograms", "miles", "grams",
    "second", "seconds", "minute", "minutes", "hour", "hours",
    "day", "days", "week", "weeks", "month", "months", "year", "years",
    "time", "times", "date", "dates",
    "per", "for", "off", "out", "the", "and", "but", "was", "were", "are",
    "will", "would", "can", "could", "should", "may", "might", "with",
    "from", "that", "this", "then", "than", "when", "into", "onto",
    "over", "under", "about", "after", "before", "between", "against",
    "ago", "away", "left", "later", "earlier", "old", "young", "each",
    "way", "ways", "tip", "tips", "option", "options", "step", "steps",
    "example", "examples", "reason", "reasons", "question", "questions",
    "idea", "ideas", "recommendation", "recommendations", "suggestion",
    "suggestions", "method", "methods", "strategy", "strategies",
    "benefit", "benefits", "feature", "features", "factor", "factors",
    "point", "points", "rule", "rules", "principle", "principles",
    "thing", "things", "item", "items", "people", "person", "types",
    "kind", "kinds", "sort", "sorts", "part", "parts", "place", "places",
    "more", "less", "other", "others", "new", "different", "additional",
})

# Stative/cumulative cues: language that asserts a CURRENT-STATE value of a
# mutable slot ("I now have", "just reached", "total is", "raised so far",
# "my collection"), as opposed to episodic event mentions ("caught 7 bass on
# the trip", "cost $30 per night when I stayed"). Shape-confirmed chain
# membership requires one of these near the value (same sentence, close by);
# deliberately absent: price/purchase verbs (cost, paid, bought, spent) and
# past-tense "had"/"was", whose values are typically one-off events. Chains
# ordered by explicit supersession edges never need cues.
_STATIVE_CUE_PATTERN = re.compile(
    r"\b(?:have|has|having|own|owns|owned|owning|hold|holds|holding|keep|keeps"
    r"|total|totals|totaling|totalling|tally|altogether"
    r"|reach|reached|reaching|reaches|hit|hits|grew|grown|grow|gained"
    r"|raise|raised|raises|raising|saved|accumulated|added|adding"
    r"|collection|inventory"
    r"|weigh|weighs|weighing|weighed"
    r"|currently|now|so far|up to|up from|update|updated|milestone)\b",
    re.IGNORECASE,
)
# The cue must sit in the same sentence as the value and within this many
# characters of it (sentence bounds cut at ./!/? followed by whitespace, so
# decimals like "$1,200.50" do not split).
_STATIVE_WINDOW = 90
_SENTENCE_BOUNDARY = re.compile(r"[.!?](?=\s|$)")

# Prospective markers VETO stativeness when they precede the value in its
# sentence: "initially aimed to raise $200", "setting a goal of six to
# eight stories" state aspirations, not the slot's value — labeling a goal
# CURRENT is exactly the wrong-label failure this module must never risk.
# Direction matters: trailing aspiration after a real state ("reached 500
# followers ... hoping to keep the momentum") does not veto.
_PROSPECTIVE_PATTERN = re.compile(
    r"\b(?:goal|goals|aim|aims|aimed|aiming|target|targets|targeted|targeting"
    r"|plan|plans|planned|planning|hope|hopes|hoped|hoping"
    r"|aspire|aspires|aspired|aspiring|wish|wishes|wished|wishing"
    r"|intend|intends|intended|intending|want|wants|wanted|wanting)\b",
    re.IGNORECASE,
)


def _has_stative_cue(text: str, start: int, end: int) -> bool:
    """True when a stative cue appears near text[start:end], same sentence.

    A prospective marker BEFORE the value in the window vetoes the cue —
    the number is a goal/target, not the slot's current value.
    """
    sentence_start = 0
    sentence_end = len(text)
    for boundary in _SENTENCE_BOUNDARY.finditer(text):
        if boundary.start() < start:
            sentence_start = boundary.end()
        elif boundary.start() >= end:
            sentence_end = boundary.start()
            break
    window_start = max(sentence_start, start - _STATIVE_WINDOW)
    window_end = min(sentence_end, end + _STATIVE_WINDOW)
    if _PROSPECTIVE_PATTERN.search(text, window_start, start) is not None:
        return False
    return _STATIVE_CUE_PATTERN.search(text, window_start, window_end) is not None


# Time-of-day shape: "6:00 pm", "7 am", "18:30". Bare 24h times require the
# colon AND an hour of 13-23 so date fragments ("2023") and counts never
# match. Times are a VALUE SHAPE only — they never group on their own, and
# they only participate at all when the text carries a habitual marker (a
# routine slot), because episodic times (a meeting time, a flight time) are
# not update chains.
_TIME_PATTERN = re.compile(
    r"\b(\d{1,2})(?::([0-5]\d))?\s*(am|pm|a\.m\.|p\.m\.)|\b(1[3-9]|2[0-3]):([0-5]\d)\b",
    re.IGNORECASE,
)
_HABITUAL_PATTERN = re.compile(
    r"\b(usually|normally|typically|always|every|each|regularly|routine|routinely|habit|habitually|daily|weekly)\b",
    re.IGNORECASE,
)

# Distinctive topic tokens for the shared-anchor requirement: 4+ letter
# words minus stopwords, speaker tags, measure/currency vocabulary, and the
# group's own noun (added per group at check time).
_ANCHOR_TOKEN_PATTERN = re.compile(r"[a-z][a-z'-]{3,}")
_ANCHOR_STOPWORDS = frozenset({
    "user", "assistant", "about", "above", "actually", "after", "again",
    "against", "along", "already", "also", "although", "always", "another",
    "anything", "around", "back", "based", "because", "been", "before",
    "being", "below", "besides", "best", "better", "between", "both",
    "cannot", "certain", "come", "could", "currently", "does", "doing",
    "done", "down", "during", "each", "either", "else", "enough", "even",
    "ever", "every", "everything", "feel", "find", "first", "found",
    "from", "getting", "give", "going", "gonna", "good", "great", "have",
    "having", "hello", "help", "here", "high", "however", "idea", "into",
    "just", "keep", "know", "last", "later", "least", "less", "like",
    "likely", "little", "long", "look", "looking", "made", "make",
    "making", "many", "maybe", "mean", "mentioned", "might", "mine",
    "more", "most", "much", "must", "need", "never", "next", "nice",
    "normally", "nothing", "often", "okay", "once", "only", "other",
    "others", "over", "own", "perfect", "please", "pretty", "quite",
    "really", "recently", "recommend", "right", "said", "same", "says",
    "should", "since", "some", "something", "sometimes", "soon", "still",
    "such", "sure", "take", "taking", "talk", "tell", "than", "thank",
    "thanks", "that", "their", "them", "then", "there", "these", "they",
    "thing", "things", "think", "thinking", "this", "those", "though",
    "thought", "through", "time", "times", "today", "told", "total",
    "trying", "under", "until", "upon", "usually", "very", "want",
    "wanted", "week", "well", "were", "what", "when", "where", "whether",
    "which", "while", "will", "with", "within", "without", "work",
    "would", "year", "years", "your", "yours",
    # Calendar/time-of-day words: shared scheduling vocabulary is not a
    # shared topic.
    "afternoon", "daily", "days", "evening", "hour", "hours", "minute",
    "minutes", "month", "months", "morning", "night", "tonight",
    "tomorrow", "weekday", "weekdays", "weekend", "weekends", "weekly",
    "weeks", "yesterday",
})


# --------------------------------------------------------------------------
# Slot signatures
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SlotSignature:
    """Content-derived slot identity of one memory row.

    ``slot_keys``: grouping keys (category phrases, value-stripped amount
    keys, count nouns). ``values``: exactly-one normalized value per value
    class; classes where the text asserts MORE than one distinct value are
    recorded in ``ambiguous_classes`` instead (a multi-valued member can
    never shape-confirm a chain). ``stative_classes``: value classes whose
    value is asserted in stative/cumulative terms (see
    ``_STATIVE_CUE_PATTERN``) — only these can shape-confirm chain
    membership without a supersession edge. ``anchors``: distinctive topic
    tokens for the shared-anchor requirement.
    """

    slot_keys: frozenset[str]
    values: Mapping[str, str]
    ambiguous_classes: frozenset[str]
    stative_classes: frozenset[str]
    anchors: frozenset[str]


def _normalize_amount(raw: str) -> str:
    """Canonical numeric text: strip separators, drop integral '.0'."""
    text = raw.replace(",", "").strip()
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return str(int(number))
    return repr(number)


def _count_number(raw: str) -> str | None:
    text = raw.replace(",", "").strip().lower()
    if text.isdigit():
        return str(int(text))
    if "-" in text:
        tens_word, _, unit_word = text.partition("-")
        tens, unit = _NUMBER_WORDS.get(tens_word), _NUMBER_WORDS.get(unit_word)
        if tens is not None and unit is not None and tens % 10 == 0 and unit < 10:
            return str(tens + unit)
        return None
    value = _NUMBER_WORDS.get(text)
    return str(value) if value is not None else None


def _singular(noun: str) -> str:
    """Crude plural fold so "bike"/"bikes" share one slot key."""
    lowered = noun.lower()
    if lowered.endswith("ies") and len(lowered) > 4:
        return lowered[:-3] + "y"
    if lowered.endswith("s") and not lowered.endswith("ss") and len(lowered) > 3:
        return lowered[:-1]
    return lowered


def _collect_value(
    values: dict[str, str],
    ambiguous: set[str],
    stative: set[str],
    value_class: str,
    value: str,
    *,
    is_stative: bool,
) -> None:
    if value_class in ambiguous:
        return
    existing = values.get(value_class)
    if existing is None:
        values[value_class] = value
    elif existing != value:
        del values[value_class]
        ambiguous.add(value_class)
        stative.discard(value_class)
        return
    if is_stative:
        stative.add(value_class)


def derive_slot_signature(memory: Mapping[str, object]) -> SlotSignature:
    """Slot keys, class values, and anchor tokens for one memory row.

    Derived from the memory's own text fields only (title, canonical_text,
    summary, value.text) with the fact-key machinery's lexicon and value
    patterns — no store reads, no query input, deterministic.
    """
    text = "\n".join(_memory_text_fields(memory))
    slot_keys: set[str] = set()
    values: dict[str, str] = {}
    ambiguous: set[str] = set()
    stative: set[str] = set()

    # Matched lexicon trigger words double as anchor tokens: the triggers
    # are curated topical vocabulary, so two members that matched the SAME
    # trigger ("gym"/"gym") share a topic even when the word is shorter
    # than the generic anchor threshold, while different triggers of one
    # category ("golden retriever" vs "poodle") stay distinct.
    trigger_anchors: set[str] = set()
    for category, pattern in _LEXICON_PATTERNS:
        matches = [match.group(0).lower() for match in pattern.finditer(text)]
        if matches:
            slot_keys.add(f"category:{category}")
            for matched in matches:
                trigger_anchors.update(token for token in matched.split() if len(token) >= 3)

    for match in _CURRENCY_PATTERN.finditer(text):
        value_class = f"currency:{_CURRENCY_WORDS[match.group(1)]}"
        slot_keys.add(value_class)
        _collect_value(
            values, ambiguous, stative, value_class, _normalize_amount(match.group(2)),
            is_stative=_has_stative_cue(text, match.start(), match.end()),
        )

    for match in _PERCENT_PATTERN.finditer(text):
        slot_keys.add("percent")
        _collect_value(
            values, ambiguous, stative, "percent", _normalize_amount(match.group(1)),
            is_stative=_has_stative_cue(text, match.start(), match.end()),
        )

    for match in _UNIT_PATTERN.finditer(text):
        _expanded, hypernym = _UNIT_EXPANSIONS[match.group(2).lower()]
        value_class = f"measure:{hypernym}"
        slot_keys.add(value_class)
        _collect_value(
            values, ambiguous, stative, value_class, _normalize_amount(match.group(1)),
            is_stative=_has_stative_cue(text, match.start(), match.end()),
        )

    count_nouns: set[str] = set()
    for match in _COUNT_PATTERN.finditer(text):
        number = _count_number(match.group(1))
        noun = match.group(2).lower()
        if number is None or noun in _COUNT_NOUN_EXCLUSIONS or noun in _NUMBER_WORDS:
            continue
        raw_number = match.group(1)
        if (
            "," not in raw_number
            and raw_number.isdigit()
            and _YEARLIKE_RANGE[0] <= int(raw_number) <= _YEARLIKE_RANGE[1]
        ):
            continue  # "pre-1920 American coins": a year, not a count
        value_class = f"count:{_singular(noun)}"
        slot_keys.add(value_class)
        count_nouns.add(noun)
        count_nouns.add(_singular(noun))
        _collect_value(
            values, ambiguous, stative, value_class, number,
            is_stative=_has_stative_cue(text, match.start(), match.end()),
        )

    if _HABITUAL_PATTERN.search(text) is not None:
        times: set[str] = set()
        for match in _TIME_PATTERN.finditer(text):
            if match.group(3) is not None:
                hour = int(match.group(1)) % 12
                if match.group(3).lower().startswith("p"):
                    hour += 12
                minute = int(match.group(2) or 0)
            else:
                hour, minute = int(match.group(4)), int(match.group(5))
            times.add(f"{hour:02d}:{minute:02d}")
        if len(times) == 1:
            values["timeofday"] = next(iter(times))
            # The habitual marker IS the stative cue for a routine slot.
            stative.add("timeofday")
        elif len(times) > 1:
            ambiguous.add("timeofday")
        # timeofday is shape-only: deliberately NOT a slot key.

    anchors = {
        token
        for token in _ANCHOR_TOKEN_PATTERN.findall(text.lower())
        if token not in _ANCHOR_STOPWORDS
        and token not in _COUNT_NOUN_EXCLUSIONS
        and token not in _NUMBER_WORDS
        and token not in count_nouns
        # Assertion vocabulary ("raised", "reached", "aiming") is how a
        # value is stated, not what it is about: two different events that
        # both "raised" money share no topic.
        and _STATIVE_CUE_PATTERN.fullmatch(token) is None
        and _PROSPECTIVE_PATTERN.fullmatch(token) is None
    } | trigger_anchors
    return SlotSignature(
        slot_keys=frozenset(slot_keys),
        values=values,
        ambiguous_classes=frozenset(ambiguous),
        stative_classes=frozenset(stative),
        anchors=frozenset(anchors),
    )


# --------------------------------------------------------------------------
# Event dates
# --------------------------------------------------------------------------


def memory_event_datetime(
    memory: Mapping[str, object],
    *,
    source_lookup: Callable[[str], Mapping[str, object] | None] | None = None,
) -> datetime | None:
    """Content-stamped event time of a memory row, or ``None``.

    Precedence mirrors the retrieval tiebreak's content-honest signals:
    the row's explicit ``valid_from``, then connector-stamped metadata
    dates, then — via ``source_lookup`` — the provenance source's
    ``source_created_at``/metadata dates. Deliberately NO write-clock
    fallback (created_at/first_seen_at): replayed or imported rows all
    share one ingest moment, and a wall-clock order between them could
    label the WRONG value current. Undated is undated.
    """
    event = parse_event_datetime(memory.get("valid_from"))
    if event is not None:
        return event
    metadata = memory.get("metadata_json")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    for key in _EVENT_METADATA_KEYS:
        event = parse_event_datetime(metadata.get(key))
        if event is not None:
            return event
    source_id = str(metadata.get("source_id") or "")
    if source_id and source_lookup is not None:
        source = source_lookup(source_id)
        if isinstance(source, Mapping):
            event = parse_event_datetime(source.get("source_created_at"))
            if event is not None:
                return event
            source_metadata = source.get("metadata_json")
            if isinstance(source_metadata, Mapping):
                for key in _EVENT_METADATA_KEYS:
                    event = parse_event_datetime(source_metadata.get(key))
                    if event is not None:
                        return event
    return None


def supersession_event_time(
    successor: Mapping[str, object],
    *,
    source_lookup: Callable[[str], Mapping[str, object] | None] | None = None,
) -> str | None:
    """ISO instant a replacement row took effect, for ``valid_to`` stamping.

    The write path (unlike read-time chains) may fall back to the
    successor's ``created_at``: in the product the replacement is written
    at correction time, so its write clock IS the correction's event time.
    Returns ``None`` only when the successor carries no readable moment.
    """
    event = memory_event_datetime(successor, source_lookup=source_lookup)
    if event is None:
        event = parse_event_datetime(successor.get("created_at"))
    if event is None:
        return None
    return event.isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------
# Chain construction
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CurrencyChain:
    chain_id: str
    slot_key: str
    member_ids: tuple[str, ...]  # render order: oldest first, current last


@dataclass(frozen=True, slots=True)
class CurrencyChainResult:
    chains: tuple[CurrencyChain, ...]
    annotations: Mapping[str, JsonObject]  # memory id -> currency annotation
    skipped_ambiguous: int
    label_chars: int

    @property
    def member_count(self) -> int:
        return sum(len(chain.member_ids) for chain in self.chains)

    @property
    def considered(self) -> bool:
        return bool(self.chains) or self.skipped_ambiguous > 0


@dataclass(frozen=True, slots=True)
class _Member:
    memory_id: str
    index: int  # position in the incoming pack order
    signature: SlotSignature
    event: datetime | None
    source_id: str
    chunk_index: int | None
    superseded_by: str | None
    supersedes: str | None


def _member_from_memory(memory: Mapping[str, object], index: int, signature: SlotSignature, event: datetime | None) -> _Member:
    metadata = memory.get("metadata_json")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    raw_chunk = metadata.get("source_chunk_index")
    chunk_index = raw_chunk if isinstance(raw_chunk, int) and not isinstance(raw_chunk, bool) else None
    return _Member(
        memory_id=str(memory.get("id")),
        index=index,
        signature=signature,
        event=event,
        source_id=str(metadata.get("source_id") or ""),
        chunk_index=chunk_index,
        superseded_by=str(memory.get("superseded_by")) if memory.get("superseded_by") else None,
        supersedes=str(memory.get("supersedes")) if memory.get("supersedes") else None,
    )


def _is_rollup_card(memory: Mapping[str, object]) -> bool:
    """Consolidation cards aggregate many instances; they are not point-in-time values."""
    metadata = memory.get("metadata_json")
    return isinstance(metadata, Mapping) and isinstance(metadata.get("consolidation"), Mapping)


def _group_edges(members: Sequence[_Member]) -> set[tuple[str, str]] | None:
    """Directed (ancestor_id, successor_id) edges among members; None on a cycle."""
    ids = {member.memory_id for member in members}
    edges: set[tuple[str, str]] = set()
    for member in members:
        if member.superseded_by and member.superseded_by in ids and member.superseded_by != member.memory_id:
            edges.add((member.memory_id, member.superseded_by))
        if member.supersedes and member.supersedes in ids and member.supersedes != member.memory_id:
            edges.add((member.supersedes, member.memory_id))
    # Cycle guard (tiny graphs: walk each start).
    adjacency: dict[str, set[str]] = {}
    for ancestor, successor in edges:
        adjacency.setdefault(ancestor, set()).add(successor)
    for start in ids:
        seen: set[str] = set()
        frontier = [start]
        while frontier:
            node = frontier.pop()
            for nxt in adjacency.get(node, ()):
                if nxt == start:
                    return None
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
    return edges


def _edge_total_order(members: Sequence[_Member], edges: set[tuple[str, str]]) -> list[_Member] | None:
    """Unique edge-induced total order (a path a->b->c), or None."""
    if not edges:
        return None
    successor_of: dict[str, str] = {}
    predecessor_of: dict[str, str] = {}
    for ancestor, successor in edges:
        if successor_of.setdefault(ancestor, successor) != successor:
            return None  # branching: two different successors
        if predecessor_of.setdefault(successor, ancestor) != ancestor:
            return None  # branching: two different predecessors
    by_id = {member.memory_id: member for member in members}
    starts = [mid for mid in by_id if mid not in predecessor_of]
    if len(starts) != 1:
        return None
    ordered: list[_Member] = []
    cursor: str | None = starts[0]
    while cursor is not None:
        ordered.append(by_id[cursor])
        cursor = successor_of.get(cursor)
    if len(ordered) != len(members):
        return None  # disconnected members: edges do not order the whole group
    return ordered


def _date_order(members: Sequence[_Member], group_class: str | None) -> list[_Member] | None:
    """Event-date order with same-source document-order ties, or None (ambiguous).

    A tie between two members is resolvable when they assert the same
    value for the group's class (order cannot change which value is
    current) or when both come from the same source with distinct chunk
    indexes (document order). Anything else is ambiguous.
    """
    if any(member.event is None for member in members):
        return None

    def value_of(member: _Member) -> str | None:
        return member.signature.values.get(group_class) if group_class else None

    ordered = sorted(
        members,
        key=lambda member: (
            cast(datetime, member.event),
            member.source_id,
            member.chunk_index if member.chunk_index is not None else -1,
            member.memory_id,
        ),
    )
    for left, right in zip(ordered, ordered[1:]):
        if left.event != right.event:
            continue
        if value_of(left) is not None and value_of(left) == value_of(right):
            continue
        same_source = left.source_id and left.source_id == right.source_id
        distinct_chunks = (
            left.chunk_index is not None
            and right.chunk_index is not None
            and left.chunk_index != right.chunk_index
        )
        if same_source and distinct_chunks:
            continue
        return None
    return ordered


def _theme_anchors(signatures: Sequence[SlotSignature]) -> frozenset[str]:
    """Anchor tokens that ARE the pack's theme, not any slot's subject.

    A token present in at least half the pack's memories (and at least
    four of them, so small packs never demote) is the retrieval theme —
    e.g. "charity" across a charity-themed pack — and two memories that
    share nothing else are about the theme, not about one slot: a $600
    yoga event and a $5,000 bike-a-thon must not chain on "charity" alone.
    """
    frequency: dict[str, int] = {}
    for signature in signatures:
        for token in signature.anchors:
            frequency[token] = frequency.get(token, 0) + 1
    total = len(signatures)
    return frozenset(
        token
        for token, count in frequency.items()
        if count >= 4 and count * 2 >= total
    )


def _pair_supported(
    left: _Member,
    right: _Member,
    *,
    group_class: str | None,
    edges: set[tuple[str, str]],
    theme_anchors: frozenset[str],
) -> bool:
    """Design gate: supersession edge OR same-slot value shape.

    Value shape means BOTH members carry exactly one value of the group's
    class, share a distinctive topic token that is not merely the pack's
    theme, and assert their value in stative/cumulative terms ("now at 600
    followers") — episodic mentions ("caught 9 bass") never shape-confirm;
    an explicit edge is the only way to chain them.
    """
    if (left.memory_id, right.memory_id) in edges or (right.memory_id, left.memory_id) in edges:
        return True
    if group_class is None:
        return False
    if group_class not in left.signature.values or group_class not in right.signature.values:
        return False
    if group_class not in left.signature.stative_classes or group_class not in right.signature.stative_classes:
        return False
    return bool((left.signature.anchors & right.signature.anchors) - theme_anchors)


def _order_consistent_with_edges(ordered: Sequence[_Member], edges: set[tuple[str, str]]) -> bool:
    positions = {member.memory_id: position for position, member in enumerate(ordered)}
    return all(positions[ancestor] < positions[successor] for ancestor, successor in edges)


def _chain_id(slot_key: str, member_ids: Sequence[str]) -> str:
    digest = hashlib.sha256(("\n".join([slot_key, *member_ids])).encode("utf-8"))
    return digest.hexdigest()[:12]


def _iso_date(event: datetime | None) -> str | None:
    return event.date().isoformat() if event is not None else None


def _annotate_chain(
    slot_key: str,
    ordered: Sequence[_Member],
    group_class: str | None,
    edge_only: bool,
) -> tuple[CurrencyChain, dict[str, JsonObject]]:
    def value_of(member: _Member) -> str | None:
        if group_class is None:
            return None
        return member.signature.values.get(group_class)

    member_ids = tuple(member.memory_id for member in ordered)
    chain_id = _chain_id(slot_key, member_ids)
    last = ordered[-1]
    current_value = value_of(last)
    current_as_of = _iso_date(last.event)
    annotations: dict[str, JsonObject] = {}
    for position, member in enumerate(ordered):
        if edge_only or current_value is None:
            is_current = position == len(ordered) - 1
        else:
            is_current = value_of(member) == current_value
        if is_current:
            status, as_of = CURRENT_STATUS, current_as_of
        else:
            status = SUPERSEDED_STATUS
            as_of = next(
                (
                    _iso_date(later.event)
                    for later in ordered[position + 1 :]
                    if edge_only
                    or current_value is None
                    or value_of(later) != value_of(member)
                ),
                None,
            )
        label = status.upper() + (f" as of {as_of}" if as_of else "")
        annotations[member.memory_id] = {
            "chain_id": chain_id,
            "slot_key": slot_key,
            "position": position + 1,
            "chain_size": len(ordered),
            "status": status,
            "as_of": as_of,
            "label": label,
        }
    return CurrencyChain(chain_id=chain_id, slot_key=slot_key, member_ids=member_ids), annotations


def build_currency_chains(
    memories: Sequence[JsonObject],
    *,
    signature_for: Callable[[Mapping[str, object]], SlotSignature] = derive_slot_signature,
    source_lookup: Callable[[str], Mapping[str, object] | None] | None = None,
) -> CurrencyChainResult:
    """Group pack memories into same-slot update chains (see module docstring).

    Pure function of the given rows (plus optional provenance-source date
    lookups): deterministic for identical inputs, no mutation. Returns the
    chains in slot-key order together with per-member annotations, the
    ambiguous-group skip count, and the total label characters (the pack
    trace reports all three so growth stays disclosed).
    """
    members: list[_Member] = []
    pack_signatures: list[SlotSignature] = []
    for index, memory in enumerate(memories):
        if not isinstance(memory, Mapping) or not memory.get("id") or _is_rollup_card(memory):
            continue
        signature = signature_for(memory)
        pack_signatures.append(signature)
        if not signature.slot_keys:
            continue
        event = memory_event_datetime(memory, source_lookup=source_lookup)
        members.append(_member_from_memory(memory, index, signature, event))
    theme_anchors = _theme_anchors(pack_signatures)

    groups: dict[str, list[_Member]] = {}
    for member in members:
        for slot_key in member.signature.slot_keys:
            groups.setdefault(slot_key, []).append(member)

    skipped = 0
    candidates: list[tuple[CurrencyChain, dict[str, JsonObject]]] = []
    decided_member_sets: set[frozenset[str]] = set()
    for slot_key in sorted(groups):
        group = groups[slot_key]
        if len(group) < 2:
            continue
        member_set = frozenset(member.memory_id for member in group)
        if member_set in decided_member_sets:
            continue  # identical membership already chained/skipped under an earlier key
        # Silent outcomes below (no comparable values, same value restated)
        # do NOT decide the set: a later key over the same members may
        # still carry the group's real value class ("category:..." sorts
        # before "currency:...") and must get its chance to chain or to
        # disclose an ambiguity skip.
        if len(group) > MAX_CHAIN_MEMBERS:
            decided_member_sets.add(member_set)
            skipped += 1
            continue

        # The group's value class: value-derived slot keys carry their own
        # class; category keys use the single class every member shares.
        if slot_key.startswith("category:"):
            common = set(group[0].signature.values)
            for member in group[1:]:
                common &= set(member.signature.values)
            group_class = sorted(common)[0] if common else None
        else:
            group_class = slot_key

        # A member that asserts multiple distinct values for the class can
        # never shape-confirm; with no edges to carry it, the slot's
        # currency is unknowable -> ambiguous.
        edges = _group_edges(group)
        if edges is None:  # cycle
            decided_member_sets.add(member_set)
            skipped += 1
            continue
        if group_class is not None and any(
            group_class in member.signature.ambiguous_classes for member in group
        ):
            decided_member_sets.add(member_set)
            skipped += 1
            continue

        ordered = _date_order(group, group_class)
        if ordered is None:
            ordered = _edge_total_order(group, edges)
            edge_only = ordered is not None
            if ordered is not None:
                # The edge order must not contradict whatever event dates
                # the (partially dated) members do carry.
                dated = [member.event for member in ordered if member.event is not None]
                if any(later < earlier for earlier, later in zip(dated, dated[1:])):
                    decided_member_sets.add(member_set)
                    skipped += 1
                    continue
        else:
            edge_only = False
            if not _order_consistent_with_edges(ordered, edges):
                decided_member_sets.add(member_set)
                skipped += 1
                continue
        if ordered is None:
            decided_member_sets.add(member_set)
            skipped += 1
            continue

        if not edge_only:
            # No update signal: the same value restated carries nothing to
            # label, so the group stays silent (not an ambiguity skip) —
            # checked before pair support so restatements never register.
            values = [member.signature.values.get(group_class) for member in ordered if group_class]
            distinct = {value for value in values if value is not None}
            if len(distinct) < 2:
                continue

        if not all(
            _pair_supported(
                left, right,
                group_class=group_class, edges=edges, theme_anchors=theme_anchors,
            )
            for left, right in zip(ordered, ordered[1:])
        ):
            decided_member_sets.add(member_set)
            skipped += 1
            continue

        decided_member_sets.add(member_set)
        candidates.append(_annotate_chain(slot_key, ordered, group_class, edge_only))

    # Overlap safety: a memory claimed by two DIFFERENT chains would carry
    # contradictory currency labels; every chain involved is dropped.
    claimed: dict[str, int] = {}
    overlapping: set[int] = set()
    for position, (chain, _annotations) in enumerate(candidates):
        for member_id in chain.member_ids:
            if member_id in claimed:
                overlapping.add(claimed[member_id])
                overlapping.add(position)
            else:
                claimed[member_id] = position
    kept = [entry for position, entry in enumerate(candidates) if position not in overlapping]
    skipped += len(overlapping)

    annotations: dict[str, JsonObject] = {}
    chains: list[CurrencyChain] = []
    for chain, chain_annotations in kept:
        chains.append(chain)
        annotations.update(chain_annotations)
    label_chars = sum(len(str(annotation.get("label") or "")) + 3 for annotation in annotations.values())
    return CurrencyChainResult(
        chains=tuple(chains),
        annotations=annotations,
        skipped_ambiguous=skipped,
        label_chars=label_chars,
    )


# --------------------------------------------------------------------------
# Pack application and rendering helpers
# --------------------------------------------------------------------------


def apply_currency_chains(
    memories: list[JsonObject],
    result: CurrencyChainResult,
) -> list[JsonObject]:
    """Annotate chain members and regroup them into contiguous chain blocks.

    Each chain renders as one block anchored at its best-ranked member's
    pack position, ordered oldest first so the CURRENT entry sits LAST
    among the chain's lines (recency-position effect). Non-members keep
    their relative order exactly. With no chains the input list is
    returned unchanged (same object) so dormant packs stay byte-identical.
    """
    if not result.chains:
        return memories
    by_id: dict[str, JsonObject] = {}
    for memory in memories:
        memory_id = str(memory.get("id"))
        if memory_id in result.annotations:
            by_id[memory_id] = memory
    chain_of: dict[str, CurrencyChain] = {}
    for chain in result.chains:
        for member_id in chain.member_ids:
            chain_of[member_id] = chain
    for memory_id, memory in by_id.items():
        memory[CURRENCY_ANNOTATION_KEY] = dict(result.annotations[memory_id])

    emitted: set[str] = set()
    reordered: list[JsonObject] = []
    for memory in memories:
        memory_id = str(memory.get("id"))
        resolved_chain = chain_of.get(memory_id)
        if resolved_chain is None:
            reordered.append(memory)
            continue
        if memory_id in emitted:
            continue
        for member_id in resolved_chain.member_ids:
            member = by_id.get(member_id)
            if member is not None and member_id not in emitted:
                reordered.append(member)
                emitted.add(member_id)
    return reordered


def currency_stage_record(result: CurrencyChainResult) -> JsonObject:
    """Trace disclosure: chain/member counts, skips, and label growth."""
    return {
        "chains": len(result.chains),
        "members": result.member_count,
        "skipped_ambiguous": result.skipped_ambiguous,
        "label_chars": result.label_chars,
    }


def currency_label_suffix(memory: Mapping[str, object]) -> str:
    """Bracketed chain label for one rendered pack line, or ``""``.

    Factual metadata quoted from the pack annotation — never instruction
    text. Memories without the annotation render exactly as before.
    """
    annotation = memory.get(CURRENCY_ANNOTATION_KEY)
    if not isinstance(annotation, Mapping):
        return ""
    label = annotation.get("label")
    if not isinstance(label, str) or not label:
        return ""
    return f" [{label}]"


__all__ = [
    "CURRENCY_ANNOTATION_KEY",
    "CURRENCY_STAGE",
    "CURRENT_STATUS",
    "CurrencyChain",
    "CurrencyChainResult",
    "MAX_CHAIN_MEMBERS",
    "SUPERSEDED_STATUS",
    "SlotSignature",
    "apply_currency_chains",
    "build_currency_chains",
    "currency_label_suffix",
    "currency_stage_record",
    "derive_slot_signature",
    "memory_event_datetime",
    "supersession_event_time",
]
