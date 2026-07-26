"""Reviewed lexical vocabulary for signed occurrence predicates.

Nothing in this module infers a relationship from unreviewed text.  Every
action and object relationship it asserts is declared explicitly in the tables
below, so a reviewer can read the complete vocabulary and audit each edge.  A
surface that is absent from the tables keeps its exact lexical form and proves
nothing: an exact-match miss is safer than an invented lexical merge.

Two separate declarations live here.

``_ACTION_VOCABULARY_GROUPS``
    Maps exact surface forms to one canonical action leaf.  Most groups only
    fold inflections of a single verb ("baked" and "bake" are the same verb),
    which asserts no synonymy at all.  A small number of groups additionally
    declare reviewed synonymy between distinct verbs; each carries the review
    note that admits it.  Folding matters beyond synonymy: without it a stored
    "baked" predicate and a "how many times did I bake ..." query never meet.

``_OBJECT_VOCABULARY_GROUPS`` / ``OBJECT_CATEGORY_VALUES``
    Reviewed object leaves, folded the same way.

**Distinct canonical leaves are NOT mutually exclusive.**  This vocabulary
folds inflections and a few reviewed synonyms; it does not partition English.
``bake``, ``make`` and ``cook`` are three leaves that routinely describe one
event, as are ``get`` and ``acquire``, or ``see`` and ``watch``.  Nothing here
may therefore be read as proof that two predicates denote different events.
Establishing that would need a genuine partition of the action space with
reviewed disjointness edges, which this module does not attempt; until it
exists, a non-matching accepted unit records an unknown relation and the reader
answers "at least N" rather than a confidently wrong exact count.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re

from alicebot_api.vnext_occurrence_predicates import (
    OCCURRENCE_PREDICATE_SCHEMA,
    OCCURRENCE_PREDICATE_TAXONOMY,
    canonicalize_occurrence_predicate,
)
from alicebot_api.vnext_repositories import JsonObject


_COMPONENT_CLEAN = re.compile(r"[^a-z0-9_-]+")


def _component(value: str) -> str:
    return _COMPONENT_CLEAN.sub("_", value.casefold().replace("-", "_")).strip("_")


# Reviewed action vocabulary.
#
# Each row is ``(canonical leaf, surface forms)``.  Rows whose canonical leaf
# equals the verb's base form only fold inflections.  Rows whose canonical leaf
# differs from every listed verb declare reviewed synonymy and are called out
# individually.
#
# Deliberate exclusions, so the omissions read as decisions rather than gaps:
#
# * ``service``, ``repair`` and ``maintain`` are not admitted.  "Service" alone
#   spans servicing a bicycle, serving a customer and a church service, so a
#   reviewer cannot declare it closed against the other maintenance verbs.
# * ``bake``, ``cook`` and ``make`` are kept as three separate leaves and
#   ``prepare`` is left out of the vocabulary entirely.  They are related but
#   not interchangeable: folding them into one food category would answer "how
#   many times did I bake" with cooking and making events, which over-counts.
#   Being separate leaves also does not make them disjoint; see the module
#   docstring.
# * ``use``, ``work``, ``do``, ``have`` and ``try`` are omitted as too generic
#   or non-eventive to carry a countable predicate.
# * Multiword actions ("went to", "picked up") are omitted because the parser
#   only ever hands this module a single verb token; admitting them here would
#   declare an edge nothing can reach.
_ACTION_VOCABULARY_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Reviewed synonymy: buying, purchasing, acquiring and ordering describe
    # the same completed acquisition of an object by the speaker.
    (
        "acquire",
        (
            "buy",
            "buys",
            "buying",
            "bought",
            "purchase",
            "purchases",
            "purchasing",
            "purchased",
            "acquire",
            "acquires",
            "acquiring",
            "acquired",
            "order",
            "orders",
            "ordering",
            "ordered",
        ),
    ),
    # Reviewed synonymy: visiting and touring a place are the same completed
    # visit for counting purposes.
    (
        "visit",
        ("visit", "visits", "visiting", "visited", "tour", "tours", "touring", "toured"),
    ),
    # Reviewed synonymy: speaking with and talking to someone are the same
    # completed conversation.
    (
        "speak",
        ("speak", "speaks", "speaking", "spoke", "spoken", "talk", "talks", "talking", "talked"),
    ),
    # Inflection folding only from here down.
    ("bake", ("bake", "bakes", "baking", "baked")),
    ("cook", ("cook", "cooks", "cooking", "cooked")),
    ("make", ("make", "makes", "making", "made")),
    ("paint", ("paint", "paints", "painting", "painted")),
    ("clean", ("clean", "cleans", "cleaning", "cleaned")),
    ("wash", ("wash", "washes", "washing", "washed")),
    ("attend", ("attend", "attends", "attending", "attended")),
    ("watch", ("watch", "watches", "watching", "watched")),
    ("read", ("read", "reads", "reading")),
    ("write", ("write", "writes", "writing", "wrote", "written")),
    ("eat", ("eat", "eats", "eating", "ate", "eaten")),
    ("drink", ("drink", "drinks", "drinking", "drank", "drunk")),
    ("run", ("run", "runs", "running", "ran")),
    ("walk", ("walk", "walks", "walking", "walked")),
    ("swim", ("swim", "swims", "swimming", "swam", "swum")),
    ("ride", ("ride", "rides", "riding", "rode", "ridden")),
    ("drive", ("drive", "drives", "driving", "drove", "driven")),
    ("fly", ("fly", "flies", "flying", "flew", "flown")),
    ("travel", ("travel", "travels", "traveling", "travelling", "traveled", "travelled")),
    ("see", ("see", "sees", "seeing", "saw", "seen")),
    ("meet", ("meet", "meets", "meeting", "met")),
    ("take", ("take", "takes", "taking", "took", "taken")),
    ("give", ("give", "gives", "giving", "gave", "given")),
    ("pay", ("pay", "pays", "paying", "paid")),
    ("spend", ("spend", "spends", "spending", "spent")),
    ("send", ("send", "sends", "sending", "sent")),
    ("bring", ("bring", "brings", "bringing", "brought")),
    ("teach", ("teach", "teaches", "teaching", "taught")),
    ("catch", ("catch", "catches", "catching", "caught")),
    ("build", ("build", "builds", "building", "built")),
    ("sell", ("sell", "sells", "selling", "sold")),
    ("tell", ("tell", "tells", "telling", "told")),
    ("find", ("find", "finds", "finding", "found")),
    ("hold", ("hold", "holds", "holding", "held")),
    ("leave", ("leave", "leaves", "leaving", "left")),
    ("keep", ("keep", "keeps", "keeping", "kept")),
    ("sleep", ("sleep", "sleeps", "sleeping", "slept")),
    ("win", ("win", "wins", "winning", "won")),
    ("lose", ("lose", "loses", "losing", "lost")),
    ("begin", ("begin", "begins", "beginning", "began", "begun")),
    ("choose", ("choose", "chooses", "choosing", "chose", "chosen")),
    ("play", ("play", "plays", "playing", "played")),
    ("join", ("join", "joins", "joining", "joined")),
    ("finish", ("finish", "finishes", "finishing", "finished")),
    ("book", ("book", "books", "booking", "booked")),
    ("call", ("call", "calls", "calling", "called")),
    ("get", ("get", "gets", "getting", "got", "gotten")),
    ("go", ("go", "goes", "going", "went", "gone")),
    ("feel", ("feel", "feels", "feeling", "felt")),
    ("become", ("become", "becomes", "becoming", "became")),
    ("come", ("come", "comes", "coming", "came")),
    ("throw", ("throw", "throws", "throwing", "threw", "thrown")),
    ("grow", ("grow", "grows", "growing", "grew", "grown")),
    ("draw", ("draw", "draws", "drawing", "drew", "drawn")),
    ("blow", ("blow", "blows", "blowing", "blew", "blown")),
    ("break", ("break", "breaks", "breaking", "broke", "broken")),
    ("wake", ("wake", "wakes", "waking", "woke", "woken")),
    ("rise", ("rise", "rises", "rising", "rose", "risen")),
    ("sing", ("sing", "sings", "singing", "sang", "sung")),
    ("sink", ("sink", "sinks", "sinking", "sank", "sunk")),
    ("sit", ("sit", "sits", "sitting", "sat")),
    ("fall", ("fall", "falls", "falling", "fell", "fallen")),
    ("hide", ("hide", "hides", "hiding", "hid", "hidden")),
    ("bite", ("bite", "bites", "biting", "bit", "bitten")),
    ("slide", ("slide", "slides", "sliding", "slid")),
    ("lead", ("lead", "leads", "leading", "led")),
    ("feed", ("feed", "feeds", "feeding", "fed")),
    ("steal", ("steal", "steals", "stealing", "stole", "stolen")),
    ("wear", ("wear", "wears", "wearing", "wore", "worn")),
    ("tear", ("tear", "tears", "tearing", "tore", "torn")),
    ("freeze", ("freeze", "freezes", "freezing", "froze", "frozen")),
    ("forget", ("forget", "forgets", "forgetting", "forgot", "forgotten")),
    ("lend", ("lend", "lends", "lending", "lent")),
    ("bend", ("bend", "bends", "bending", "bent")),
    ("sweep", ("sweep", "sweeps", "sweeping", "swept")),
    ("dig", ("dig", "digs", "digging", "dug")),
    ("hang", ("hang", "hangs", "hanging", "hung")),
    ("shoot", ("shoot", "shoots", "shooting", "shot")),
    ("strike", ("strike", "strikes", "striking", "struck")),
    ("ring", ("ring", "rings", "ringing", "rang", "rung")),
    ("swear", ("swear", "swears", "swearing", "swore", "sworn")),
    ("light", ("light", "lights", "lighting", "lit")),
    ("creep", ("creep", "creeps", "creeping", "crept")),
    ("weep", ("weep", "weeps", "weeping", "wept")),
    ("deal", ("deal", "deals", "dealing", "dealt")),
    ("stand", ("stand", "stands", "standing", "stood")),
    ("stick", ("stick", "sticks", "sticking", "stuck")),
    ("sting", ("sting", "stings", "stinging", "stung")),
    ("spin", ("spin", "spins", "spinning", "spun")),
    ("swing", ("swing", "swings", "swinging", "swung")),
    ("speed", ("speed", "speeds", "speeding", "sped")),
    ("shine", ("shine", "shines", "shining", "shone")),
    ("spring", ("spring", "springs", "springing", "sprang", "sprung")),
    ("kneel", ("kneel", "kneels", "kneeling", "knelt")),
    ("leap", ("leap", "leaps", "leaping", "leapt", "leaped")),
    ("burn", ("burn", "burns", "burning", "burnt", "burned")),
    ("forgive", ("forgive", "forgives", "forgiving", "forgave", "forgiven")),
    ("mistake", ("mistake", "mistakes", "mistaking", "mistook", "mistaken")),
    ("withdraw", ("withdraw", "withdraws", "withdrawing", "withdrew", "withdrawn")),
    ("overcome", ("overcome", "overcomes", "overcoming", "overcame")),
    ("undertake", ("undertake", "undertakes", "undertaking", "undertook", "undertaken")),
    ("rebuild", ("rebuild", "rebuilds", "rebuilding", "rebuilt")),
)


def _build_vocabulary(
    groups: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    label: str,
) -> dict[str, str]:
    vocabulary: dict[str, str] = {}
    for canonical, surfaces in groups:
        canonical_leaf = _component(canonical)
        if not canonical_leaf:
            raise ValueError(f"reviewed {label} vocabulary has an empty canonical leaf")
        for surface in surfaces:
            key = _component(surface)
            if not key:
                raise ValueError(f"reviewed {label} vocabulary has an empty surface form")
            if key in vocabulary and vocabulary[key] != canonical_leaf:
                raise ValueError(f"reviewed {label} vocabulary maps {key!r} to two canonical leaves")
            vocabulary[key] = canonical_leaf
    return vocabulary


# Reviewed object vocabulary.  Only leaves whose mutual distinctness has been
# checked belong here; an object outside the table proves nothing, which keeps
# "vinyl" from being declared disjoint from "record" by omission alone.
_OBJECT_VOCABULARY_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("movie", ("movie", "film")),
    ("museum", ("museum",)),
    ("restaurant", ("restaurant",)),
    ("concert", ("concert",)),
    ("flight", ("flight",)),
    ("hotel", ("hotel",)),
    ("apartment", ("apartment", "flat")),
    ("car", ("car",)),
    ("cake", ("cake",)),
    ("bread", ("bread",)),
    ("pizza", ("pizza",)),
    ("coffee", ("coffee",)),
    ("marathon", ("marathon",)),
    ("conference", ("conference",)),
    ("gym", ("gym",)),
)

OCCURRENCE_ACTION_VOCABULARY: Mapping[str, str] = _build_vocabulary(
    _ACTION_VOCABULARY_GROUPS,
    label="action",
)
OCCURRENCE_OBJECT_VOCABULARY: Mapping[str, str] = _build_vocabulary(
    _OBJECT_VOCABULARY_GROUPS,
    label="object",
)
ACTION_CATEGORY_VALUES: frozenset[str] = frozenset(OCCURRENCE_ACTION_VOCABULARY.values())
OBJECT_CATEGORY_VALUES: frozenset[str] = frozenset(OCCURRENCE_OBJECT_VOCABULARY.values())


def canonical_action_leaf(value: str) -> str:
    """Return the reviewed canonical action leaf, or the exact surface.

    The vocabulary is consulted from both the write path and the query path,
    so a stored "baked" predicate and a "how many times did I bake ..." query
    resolve to the same leaf.  A surface outside the reviewed vocabulary is
    returned unchanged and remains an exact lexical leaf.
    """

    normalized = _component("_".join(value.split()))
    return OCCURRENCE_ACTION_VOCABULARY.get(normalized, normalized)


def canonical_object_leaf(value: str) -> str:
    """Return a conservative singular object head, folded when reviewed."""

    normalized = _component(value)
    # Without a reviewed lexicon, ``-ies`` is ambiguous between a plural of
    # ``-y`` and a singular ending in ``-ie`` plus ``s``. Leave it unchanged:
    # an exact-match miss is safer than inventing a false lexical merge.
    if normalized.endswith("ies") and len(normalized) > 3:
        singular = normalized
    elif normalized.endswith("sses") and len(normalized) > 4:
        singular = normalized[:-2]
    elif normalized.endswith("s") and not normalized.endswith(("ss", "us")):
        singular = normalized[:-1]
    else:
        singular = normalized
    return OCCURRENCE_OBJECT_VOCABULARY.get(singular, singular)


def _canonical_qualifiers(values: Iterable[str]) -> list[str]:
    return sorted(
        {
            normalized
            for value in values
            if (normalized := _component(value))
        }
    )


def build_occurrence_predicate_atom(
    *,
    action: str,
    object_leaf: str,
    object_qualifiers: Iterable[str] = (),
) -> JsonObject:
    """Build one lexical atom over reviewed canonical leaves.

    Both leaves are canonicalized through the reviewed vocabulary, so the write
    path and the query path produce the same selector for the same predicate.
    The atom's ``closure_complete`` stays false; see the note on that field.
    """

    action_leaf = canonical_action_leaf(action)
    canonical_object = canonical_object_leaf(object_leaf)
    action_ancestors: list[str] = []
    qualifiers = _canonical_qualifiers(object_qualifiers)
    sorted_object_ancestors: list[str] = []
    selector_keys = [
        f"v1|a=exact:{action_leaf}|o=exact:{canonical_object}",
        f"v1|a=exact:{action_leaf}|o=*",
        *(
            f"v1|a=category:{ancestor}|o=exact:{canonical_object}"
            for ancestor in action_ancestors
        ),
        *(
            f"v1|a=exact:{action_leaf}|o=category:{ancestor}"
            for ancestor in sorted_object_ancestors
        ),
        *(
            f"v1|a=category:{action_ancestor}|o=category:{object_ancestor}"
            for action_ancestor in action_ancestors
            for object_ancestor in sorted_object_ancestors
        ),
    ]
    return canonicalize_occurrence_predicate(
        {
            "schema": OCCURRENCE_PREDICATE_SCHEMA,
            "taxonomy": OCCURRENCE_PREDICATE_TAXONOMY,
            "op": "atom",
            "subject": "self",
            "polarity": "completed",
            "action": {
                "leaf": action_leaf,
                "ancestors": action_ancestors,
            },
            "object": {
                "leaf": canonical_object,
                "qualifiers": qualifiers,
                "ancestors": sorted_object_ancestors,
            },
            "selector_keys": selector_keys,
            # Deliberately and permanently false for a lexical atom, on two
            # independent grounds.
            #
            # 1. Qualifier narrowing. A query may narrow by object qualifiers
            #    ("... the museum with Bob"). An atom that does not record
            #    whether Bob was there is silent about it, not contradicting it,
            #    so a non-match cannot be read as disjointness.
            # 2. Near-synonym leaves. This vocabulary folds inflections and a
            #    few reviewed synonyms; it does not partition English. ``bake``,
            #    ``make`` and ``cook``, or ``get`` and ``acquire``, are distinct
            #    leaves that routinely describe the same event, so distinct
            #    leaves are NOT mutually exclusive and must never be treated as
            #    proof of disjointness.
            #
            # Either way the consequence is the same: a non-matching accepted
            # unit records an unknown relation, which forgoes exactness. Alice
            # answers "at least N" instead of a confidently wrong exact count.
            "closure_complete": False,
        },
        allow_claim_ops=False,
    )


def occurrence_selector_kind(value: str, *, object_selector: bool = False) -> str:
    """Return ``category`` for a reviewed leaf and ``exact`` otherwise."""

    component = canonical_object_leaf(value) if object_selector else canonical_action_leaf(value)
    categories = OBJECT_CATEGORY_VALUES if object_selector else ACTION_CATEGORY_VALUES
    return "category" if component in categories else "exact"


__all__ = [
    "ACTION_CATEGORY_VALUES",
    "OBJECT_CATEGORY_VALUES",
    "OCCURRENCE_ACTION_VOCABULARY",
    "OCCURRENCE_OBJECT_VOCABULARY",
    "build_occurrence_predicate_atom",
    "canonical_action_leaf",
    "canonical_object_leaf",
    "occurrence_selector_kind",
]
