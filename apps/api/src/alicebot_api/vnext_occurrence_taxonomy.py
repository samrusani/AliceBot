"""Conservative lexical normalization for signed occurrence predicates.

This module deliberately asserts no synonym, inflection, or category
relationships from unreviewed text.  Action surfaces remain exact unless a
separately reviewed structured predicate supplies a governed leaf.  Semantic
closure is available only to structured inputs backed by an independently
governed taxonomy.
"""

from __future__ import annotations

from collections.abc import Iterable
import re

from alicebot_api.vnext_occurrence_predicates import (
    OCCURRENCE_PREDICATE_SCHEMA,
    OCCURRENCE_PREDICATE_TAXONOMY,
    canonicalize_occurrence_predicate,
)
from alicebot_api.vnext_repositories import JsonObject


ACTION_CATEGORY_VALUES: frozenset[str] = frozenset()
OBJECT_CATEGORY_VALUES: frozenset[str] = frozenset()

_COMPONENT_CLEAN = re.compile(r"[^a-z0-9_-]+")


def _component(value: str) -> str:
    return _COMPONENT_CLEAN.sub("_", value.casefold().replace("-", "_")).strip("_")


def canonical_action_leaf(value: str) -> str:
    """Return one normalized exact action surface without lemmatization."""

    return _component("_".join(value.split()))


def canonical_object_leaf(value: str) -> str:
    """Return a conservative singular object head."""

    normalized = _component(value)
    # Without a reviewed lexicon, ``-ies`` is ambiguous between a plural of
    # ``-y`` and a singular ending in ``-ie`` plus ``s``. Leave it unchanged:
    # an exact-match miss is safer than inventing a false lexical merge.
    if normalized.endswith("ies") and len(normalized) > 3:
        return normalized
    if normalized.endswith("sses") and len(normalized) > 4:
        return normalized[:-2]
    if normalized.endswith("s") and not normalized.endswith(("ss", "us")):
        return normalized[:-1]
    return normalized


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
    """Build one exact lexical atom with deliberately incomplete closure."""

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
            # Exact lexical mismatch cannot prove semantic disjointness:
            # ``buy`` and ``purchase`` may describe the same predicate even
            # though no unreviewed synonym edge is permitted here.
            "closure_complete": False,
        },
        allow_claim_ops=False,
    )


def occurrence_selector_kind(value: str, *, object_selector: bool = False) -> str:
    """Return ``exact``; unreviewed text never establishes a category."""

    component = canonical_object_leaf(value) if object_selector else canonical_action_leaf(value)
    categories = OBJECT_CATEGORY_VALUES if object_selector else ACTION_CATEGORY_VALUES
    return "category" if component in categories else "exact"


__all__ = [
    "ACTION_CATEGORY_VALUES",
    "OBJECT_CATEGORY_VALUES",
    "build_occurrence_predicate_atom",
    "canonical_action_leaf",
    "canonical_object_leaf",
    "occurrence_selector_kind",
]
