from __future__ import annotations

import pytest

from alicebot_api.vnext_occurrence_taxonomy import (
    build_occurrence_predicate_atom,
    canonical_action_leaf,
    canonical_object_leaf,
    occurrence_selector_kind,
)


def test_taxonomy_builds_exact_and_wildcard_selectors_without_semantic_closure() -> None:
    atom = build_occurrence_predicate_atom(
        action="baked",
        object_leaf="cookies",
    )

    assert atom["action"] == {
        "leaf": "baked",
        "ancestors": [],
    }
    assert atom["object"] == {
        "leaf": "cookies",
        "qualifiers": [],
        "ancestors": [],
    }
    assert atom["selector_keys"] == [
        "v1|a=exact:baked|o=exact:cookies",
        "v1|a=exact:baked|o=*",
    ]
    assert "aliases" not in atom


def test_taxonomy_never_infers_acquisition_or_object_categories() -> None:
    atom = build_occurrence_predicate_atom(
        action="purchased",
        object_leaf="necklaces",
        object_qualifiers=("pearl",),
    )

    assert atom["taxonomy"] == "alice-occurrence-exact-v1"
    assert atom["action"] == {
        "leaf": "purchased",
        "ancestors": [],
    }
    assert atom["object"] == {
        "leaf": "necklace",
        "qualifiers": ["pearl"],
        "ancestors": [],
    }
    assert atom["selector_keys"] == [
        "v1|a=exact:purchased|o=exact:necklace",
        "v1|a=exact:purchased|o=*",
    ]
    assert atom["closure_complete"] is False


def test_inflection_normalization_does_not_assert_maintenance_synonymy() -> None:
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
    assert occurrence_selector_kind("bicycles", object_selector=True) == "exact"


def test_unknown_and_irregular_surfaces_remain_exact_lexical_leaves() -> None:
    atom = build_occurrence_predicate_atom(
        action="polished",
        object_leaf="meteorites",
    )

    assert canonical_action_leaf("polished") == "polished"
    assert canonical_action_leaf("went") == "went"
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
        "baked",
        "completed",
        "created",
        "purchased",
        "serviced",
        "used",
        "booked",
        "cooked",
        "locked",
        "looked",
        "walked",
        "worked",
        "banged",
        "treated",
        "bought",
        "tried",
        "stopped",
    ],
)
def test_unreviewed_action_inflections_keep_their_exact_surface(
    surface: str,
) -> None:
    assert canonical_action_leaf(surface) == surface


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
