"""Speaker-provenance derivation and promotion-rank bias for captured memories.

Conversational transcripts tag turns with a speaker label (``[USER]:`` /
``[ASSISTANT]:``, with or without brackets). Capture derives a
``provenance_role`` from that *content shape alone* — no benchmark metadata,
question types, or labels are ever consulted — and classifies how assertive
the content is:

* ``user_asserted`` — the user states a concrete value about themselves in
  the first person ("I paid $50 for the taxi"). These are ground truth the
  user vouched for.
* ``assistant_estimate`` — the assistant offers hedged or ranged figures
  ("approximately $180-270", "typically costs around ¥20,000-30,000").
  These are model chatter, not user facts.

``provenance_promotion_rank`` turns those classes into a small ordinal used
to ORDER same-topic candidates at promotion time: user-asserted facts sort
before neutral content, and assistant estimates sort after it. This is a
bias, not suppression — assistant-derived memories still capture, promote,
and recall; they only lose ordering ties against a first-person user
assertion for the same slot.

Content without a recognizable speaker tag derives no role, gets no
adjustment anywhere, and follows the byte-identical pre-existing code path.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import re
from typing import TypeVar

PROVENANCE_ROLE_USER = "user"
PROVENANCE_ROLE_ASSISTANT = "assistant"

ASSERTION_CLASS_USER_ASSERTED = "user_asserted"
ASSERTION_CLASS_ASSISTANT_ESTIMATE = "assistant_estimate"

# Promotion-rank ordinals (lower sorts first / wins the slot).
PROMOTION_RANK_USER_ASSERTED = 0
PROMOTION_RANK_USER = 1
PROMOTION_RANK_NEUTRAL = 2
PROMOTION_RANK_ASSISTANT_ESTIMATE = 3

# Speaker tag at the start of a line: "[USER]:", "USER:", "[Assistant]: ",
# case-insensitive. Matching is anchored so mid-sentence mentions of the
# words "user"/"assistant" never derive a role.
_SPEAKER_TAG_PATTERN = re.compile(
    r"^\s*(?:\[(?P<bracketed>user|assistant)\]|(?P<bare>user|assistant))\s*:\s*",
    re.IGNORECASE,
)

# First-person subject pronouns: the speaker is talking about themselves.
_FIRST_PERSON_PATTERN = re.compile(r"\b(?:i|i'm|i've|i'd|my|me|we|our)\b", re.IGNORECASE)

# Assertion verbs that bind a concrete value to the speaker (broader than
# the generic claim_sentence verb list; includes common past-tense forms).
_ASSERTION_VERB_PATTERN = re.compile(
    r"\b(?:is|are|was|were|am|paid|pay|pays|bought|buy|spent|spend|cost|costs|"
    r"earned|earn|earns|raised|raise|got|get|gets|have|has|had|own|owns|owned|"
    r"weigh|weighs|weighed|work|works|worked|saved|save|charges?|charged|"
    r"told|said)\b",
    re.IGNORECASE,
)

# A concrete value: currency amounts, percentages, unit-bearing quantities,
# or thousands-separated numbers. Deliberately NOT any bare digit — loose
# digit matching turns ordinary chatter ("my iPhone 13", "chapter 4") into
# asserted-value memories and drowns retrieval in noise.
_CONCRETE_VALUE_PATTERN = re.compile(
    r"[$€£¥]\s*\d"  # currency-symbol amounts: $50, ¥20,000
    r"|\d[\d,]*(?:\.\d+)?\s*%"  # percentages: 15%
    r"|\d[\d,]*(?:\.\d+)?\s*(?:dollars?|bucks|usd|euros?|eur|gbp|yen|jpy)\b"  # currency words
    r"|\d[\d,]*(?:\.\d+)?\s*(?:hours?|hrs?|minutes?|mins?|seconds?|days?|weeks?|months?|years?|yrs?"
    r"|miles?|km|kilometers?|meters?|feet|ft|inches?|kg|kilograms?|grams?|lbs?|pounds?|ounces?|oz"
    r"|gb|mb|tb|mph|kph|calories?|steps?|dollars?)\b"  # quantity + unit
    r"|\d{1,3}(?:,\d{3})+",  # thousands-separated numbers: 20,000
    re.IGNORECASE,
)

# Hedged/estimate phrasing that marks assistant figures as approximations.
_HEDGE_PATTERN = re.compile(
    r"\b(?:approximately|approx\.?|around|roughly|about|estimated?|estimates?|"
    r"typically|usually|likely|generally|on average|up to|between)\b",
    re.IGNORECASE,
)

# A numeric range like "$180-270", "¥20,000-30,000", or "20 - 30".
_NUMERIC_RANGE_PATTERN = re.compile(r"\d(?:[\d,.]*)\s*[-–—]\s*[$€£¥]?\s*\d")

_T = TypeVar("_T")


def derive_speaker_role(text: str) -> str | None:
    """Speaker role from a leading transcript tag, or ``None`` when untagged."""
    match = _SPEAKER_TAG_PATTERN.match(text)
    if match is None:
        return None
    role = (match.group("bracketed") or match.group("bare") or "").casefold()
    if role == PROVENANCE_ROLE_USER:
        return PROVENANCE_ROLE_USER
    if role == PROVENANCE_ROLE_ASSISTANT:
        return PROVENANCE_ROLE_ASSISTANT
    return None


def classify_assertion(text: str, role: str | None) -> str | None:
    """Assertion class for speaker-tagged content; ``None`` when neutral.

    * USER + first-person pronoun + assertion verb + concrete value →
      ``user_asserted``.
    * ASSISTANT + concrete value + (hedge word or numeric range) →
      ``assistant_estimate``.

    Anything else (no role, no concrete value, plain assistant statements)
    stays neutral so unrelated content is never re-ranked.
    """
    if role is None:
        return None
    if not _CONCRETE_VALUE_PATTERN.search(text):
        return None
    if role == PROVENANCE_ROLE_USER:
        if _FIRST_PERSON_PATTERN.search(text) and _ASSERTION_VERB_PATTERN.search(text):
            return ASSERTION_CLASS_USER_ASSERTED
        return None
    if role == PROVENANCE_ROLE_ASSISTANT:
        if _HEDGE_PATTERN.search(text) or _NUMERIC_RANGE_PATTERN.search(text):
            return ASSERTION_CLASS_ASSISTANT_ESTIMATE
        return None
    return None


def provenance_promotion_rank(
    *,
    provenance_role: str | None,
    assertion_class: str | None,
) -> int:
    """Ordinal promotion rank; lower wins ordering for the same topic slot.

    ``user_asserted`` (0) < plain user statement (1) < neutral/unknown and
    plain assistant content (2) < ``assistant_estimate`` (3). Content with
    no derived role always ranks neutral, so provenance-free stores keep
    their existing order byte-for-byte.
    """
    if assertion_class == ASSERTION_CLASS_USER_ASSERTED:
        return PROMOTION_RANK_USER_ASSERTED
    if assertion_class == ASSERTION_CLASS_ASSISTANT_ESTIMATE:
        return PROMOTION_RANK_ASSISTANT_ESTIMATE
    if provenance_role == PROVENANCE_ROLE_USER:
        return PROMOTION_RANK_USER
    return PROMOTION_RANK_NEUTRAL


def order_by_provenance(
    items: Sequence[_T],
    *,
    rank_of: Callable[[_T], int],
) -> list[_T]:
    """Stable provenance ordering: rank ascending, original order preserved.

    When every item ranks neutral (the ungated case) the result is the
    input order unchanged.
    """
    decorated = sorted(
        ((rank_of(item), index) for index, item in enumerate(items)),
    )
    return [items[index] for _rank, index in decorated]


__all__ = [
    "ASSERTION_CLASS_ASSISTANT_ESTIMATE",
    "ASSERTION_CLASS_USER_ASSERTED",
    "PROMOTION_RANK_ASSISTANT_ESTIMATE",
    "PROMOTION_RANK_NEUTRAL",
    "PROMOTION_RANK_USER",
    "PROMOTION_RANK_USER_ASSERTED",
    "PROVENANCE_ROLE_ASSISTANT",
    "PROVENANCE_ROLE_USER",
    "classify_assertion",
    "derive_speaker_role",
    "order_by_provenance",
    "provenance_promotion_rank",
]
