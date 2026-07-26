from __future__ import annotations

import pytest

from alicebot_api.vnext_occurrence_taxonomy import (
    ACTION_CATEGORY_VALUES,
    OCCURRENCE_ACTION_VOCABULARY,
    build_occurrence_predicate_atom,
    canonical_action_leaf,
    canonical_object_leaf,
    occurrence_selector_kind,
)
from alicebot_api.vnext_occurrence_write import _IRREGULAR_COMPLETED_VERBS


def test_taxonomy_folds_a_reviewed_inflection_onto_one_canonical_leaf() -> None:
    atom = build_occurrence_predicate_atom(
        action="baked",
        object_leaf="cookies",
    )

    assert atom["action"] == {
        "leaf": "bake",
        "ancestors": [],
    }
    assert atom["object"] == {
        "leaf": "cookies",
        "qualifiers": [],
        "ancestors": [],
    }
    assert atom["selector_keys"] == [
        "v1|a=exact:bake|o=exact:cookies",
        "v1|a=exact:bake|o=*",
    ]
    assert "aliases" not in atom


def test_write_and_query_verb_forms_meet_on_the_same_selector() -> None:
    stored = build_occurrence_predicate_atom(action="visited", object_leaf="museums")
    asked_past = build_occurrence_predicate_atom(action="visit", object_leaf="museums")
    asked_synonym = build_occurrence_predicate_atom(action="toured", object_leaf="museums")

    assert stored["selector_keys"] == asked_past["selector_keys"] == asked_synonym["selector_keys"]


def test_reviewed_acquisition_synonyms_share_one_canonical_leaf() -> None:
    atom = build_occurrence_predicate_atom(
        action="purchased",
        object_leaf="necklaces",
        object_qualifiers=("pearl",),
    )

    assert atom["taxonomy"] == "alice-occurrence-exact-v1"
    assert atom["action"] == {
        "leaf": "acquire",
        "ancestors": [],
    }
    assert atom["object"] == {
        "leaf": "necklace",
        "qualifiers": ["pearl"],
        "ancestors": [],
    }
    assert atom["selector_keys"] == [
        "v1|a=exact:acquire|o=exact:necklace",
        "v1|a=exact:acquire|o=*",
    ]
    assert atom["closure_complete"] is False


def test_a_lexical_atom_never_declares_its_closure_complete() -> None:
    # Two independent reasons, both permanent for this predicate shape: a query
    # may narrow by qualifiers the atom does not record, and distinct canonical
    # leaves are near-synonyms rather than a partition. Either one makes a
    # non-match unprovable as disjointness.
    for atom in (
        build_occurrence_predicate_atom(action="visited", object_leaf="museums"),
        build_occurrence_predicate_atom(action="visited", object_leaf="vinyl"),
        build_occurrence_predicate_atom(action="polished", object_leaf="meteorites"),
        build_occurrence_predicate_atom(action="bought", object_leaf="cake"),
    ):
        assert atom["closure_complete"] is False


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("baked", "made"),
        ("baked", "cooked"),
        ("got", "bought"),
        ("saw", "watched"),
        ("went", "visited"),
    ],
)
def test_near_synonym_leaves_are_not_declared_mutually_exclusive(
    left: str,
    right: str,
) -> None:
    """Distinct canonical leaves must never imply distinct events.

    ``bake`` and ``make`` are separate leaves so a bake query does not silently
    count every cooking event, but they routinely describe the same event. If
    anything ever reads "different leaf" as "different event", a store holding
    only "I made a cake" would answer "how many cakes did I bake?" with an
    exact zero. The only thing standing between the substrate and that answer
    is that neither atom claims a complete closure.
    """

    left_atom = build_occurrence_predicate_atom(action=left, object_leaf="cake")
    right_atom = build_occurrence_predicate_atom(action=right, object_leaf="cake")

    assert canonical_action_leaf(left) != canonical_action_leaf(right)
    assert not set(left_atom["selector_keys"]).intersection(right_atom["selector_keys"])
    assert left_atom["closure_complete"] is False
    assert right_atom["closure_complete"] is False


def test_inflection_normalization_does_not_assert_maintenance_synonymy() -> None:
    # ``service``, ``repair`` and ``maintain`` are deliberately absent from the
    # reviewed vocabulary: none of them is closed against the others.
    atom = build_occurrence_predicate_atom(
        action="repaired",
        object_leaf="bicycles",
    )

    assert atom["action"] == {
        "leaf": "repaired",
        "ancestors": [],
    }
    assert atom["object"]["leaf"] == "bicycle"
    assert occurrence_selector_kind("maintain") == "exact"
    assert occurrence_selector_kind("serviced") == "exact"
    assert occurrence_selector_kind("bicycles", object_selector=True) == "exact"


def test_unreviewed_surfaces_remain_exact_lexical_leaves() -> None:
    atom = build_occurrence_predicate_atom(
        action="polished",
        object_leaf="meteorites",
    )

    assert canonical_action_leaf("polished") == "polished"
    assert canonical_action_leaf("shrove") == "shrove"
    assert canonical_object_leaf("meteorites") == "meteorite"
    assert atom["action"]["ancestors"] == []
    assert atom["object"]["ancestors"] == []
    assert atom["selector_keys"] == [
        "v1|a=exact:polished|o=exact:meteorite",
        "v1|a=exact:polished|o=*",
    ]


@pytest.mark.parametrize(
    "surface",
    [
        "completed",
        "created",
        "serviced",
        "used",
        "locked",
        "looked",
        "worked",
        "banged",
        "treated",
        "tried",
        "stopped",
    ],
)
def test_unreviewed_action_inflections_keep_their_exact_surface(
    surface: str,
) -> None:
    assert canonical_action_leaf(surface) == surface


@pytest.mark.parametrize(
    ("surface", "canonical"),
    [
        ("baked", "bake"),
        ("purchased", "acquire"),
        ("bought", "acquire"),
        ("ordered", "acquire"),
        ("booked", "book"),
        ("cooked", "cook"),
        ("walked", "walk"),
        ("went", "go"),
        ("gone", "go"),
        ("visited", "visit"),
        ("toured", "visit"),
        ("talked", "speak"),
        ("wrote", "write"),
        ("flew", "fly"),
        ("stood", "stand"),
        ("drunk", "drink"),
        ("swung", "swing"),
    ],
)
def test_reviewed_action_inflections_fold_onto_their_canonical_leaf(
    surface: str,
    canonical: str,
) -> None:
    assert canonical_action_leaf(surface) == canonical
    assert canonical in ACTION_CATEGORY_VALUES


def test_reviewed_vocabulary_is_a_single_valued_declaration() -> None:
    # Every surface maps to exactly one canonical leaf, and every canonical
    # leaf is itself a surface of its own group, so the table is idempotent.
    for surface, canonical in OCCURRENCE_ACTION_VOCABULARY.items():
        assert canonical_action_leaf(surface) == canonical
        assert canonical_action_leaf(canonical) == canonical


def test_every_admitted_irregular_surface_folds_to_a_reviewed_leaf() -> None:
    """The extractor's lexicon and this vocabulary must not drift apart.

    An irregular surface the extractor admits but this table cannot fold would
    be stored under its raw surface and could never be reached by a query using
    any other form of the same verb. The reverse gap is what let ``go`` exist
    as a canonical leaf while ``went`` stayed inextractable.
    """

    unfoldable = sorted(
        surface for surface in _IRREGULAR_COMPLETED_VERBS if surface not in OCCURRENCE_ACTION_VOCABULARY
    )

    assert unfoldable == []
    assert {"went", "gone"} <= _IRREGULAR_COMPLETED_VERBS


def test_ambiguous_ies_surfaces_are_not_guessed_from_a_word_list() -> None:
    assert {
        value: canonical_object_leaf(value)
        for value in ("brownies", "movies", "ties", "zombies")
    } == {
        "brownies": "brownies",
        "movies": "movies",
        "ties": "ties",
        "zombies": "zombies",
    }
