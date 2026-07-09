from __future__ import annotations

import pytest

from alicebot_api.memory_provenance import (
    ASSERTION_CLASS_ASSISTANT_ESTIMATE,
    ASSERTION_CLASS_USER_ASSERTED,
    PROMOTION_RANK_ASSISTANT_ESTIMATE,
    PROMOTION_RANK_NEUTRAL,
    PROMOTION_RANK_USER,
    PROMOTION_RANK_USER_ASSERTED,
    PROVENANCE_ROLE_ASSISTANT,
    PROVENANCE_ROLE_USER,
    classify_assertion,
    derive_speaker_role,
    order_by_provenance,
    provenance_promotion_rank,
)


# -- role derivation ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[USER]: I paid $50 for the taxi.", PROVENANCE_ROLE_USER),
        ("[ASSISTANT]: That fare is usually about $60.", PROVENANCE_ROLE_ASSISTANT),
        ("[user]: lowercase tags still count", PROVENANCE_ROLE_USER),
        ("USER: bare tags without brackets count too", PROVENANCE_ROLE_USER),
        ("Assistant: bare assistant tag", PROVENANCE_ROLE_ASSISTANT),
        ("  [USER] : leading whitespace and spaced colon", PROVENANCE_ROLE_USER),
    ],
)
def test_derive_speaker_role_recognizes_transcript_tags(text: str, expected: str) -> None:
    assert derive_speaker_role(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "The user said the fare was $50.",  # mid-sentence mention, not a tag
        "username: not a speaker tag",
        "I paid $50 for the taxi.",  # untagged content derives nothing
        "Userland: tools",
        "",
    ],
)
def test_derive_speaker_role_returns_none_for_untagged_content(text: str) -> None:
    assert derive_speaker_role(text) is None


# -- assertion classification ---------------------------------------------------------


def test_user_first_person_concrete_value_is_user_asserted() -> None:
    text = "[USER]: I paid $50 for the taxi from the airport."
    assert classify_assertion(text, PROVENANCE_ROLE_USER) == ASSERTION_CLASS_USER_ASSERTED


def test_user_statement_without_concrete_value_is_neutral() -> None:
    text = "[USER]: I really enjoyed the train ride into the city."
    assert classify_assertion(text, PROVENANCE_ROLE_USER) is None


def test_assistant_hedged_range_is_an_estimate() -> None:
    text = "[ASSISTANT]: The fare is usually ¥20,000-30,000 (approximately $180-270)."
    assert classify_assertion(text, PROVENANCE_ROLE_ASSISTANT) == ASSERTION_CLASS_ASSISTANT_ESTIMATE


def test_assistant_plain_statement_with_value_is_neutral() -> None:
    text = "[ASSISTANT]: Your booking reference is 48213."
    assert classify_assertion(text, PROVENANCE_ROLE_ASSISTANT) is None


def test_no_role_is_always_neutral() -> None:
    assert classify_assertion("I paid $50 for the taxi.", None) is None


# -- promotion rank -------------------------------------------------------------------


def test_promotion_rank_orders_user_asserted_above_assistant_estimates() -> None:
    user_asserted = provenance_promotion_rank(
        provenance_role=PROVENANCE_ROLE_USER,
        assertion_class=ASSERTION_CLASS_USER_ASSERTED,
    )
    plain_user = provenance_promotion_rank(
        provenance_role=PROVENANCE_ROLE_USER,
        assertion_class=None,
    )
    neutral = provenance_promotion_rank(provenance_role=None, assertion_class=None)
    plain_assistant = provenance_promotion_rank(
        provenance_role=PROVENANCE_ROLE_ASSISTANT,
        assertion_class=None,
    )
    estimate = provenance_promotion_rank(
        provenance_role=PROVENANCE_ROLE_ASSISTANT,
        assertion_class=ASSERTION_CLASS_ASSISTANT_ESTIMATE,
    )

    assert user_asserted == PROMOTION_RANK_USER_ASSERTED
    assert plain_user == PROMOTION_RANK_USER
    assert neutral == PROMOTION_RANK_NEUTRAL
    assert plain_assistant == PROMOTION_RANK_NEUTRAL  # bias, not suppression
    assert estimate == PROMOTION_RANK_ASSISTANT_ESTIMATE
    assert user_asserted < plain_user < neutral < estimate


def test_order_by_provenance_is_stable_and_identity_for_neutral_items() -> None:
    items = ["a", "b", "c"]
    assert order_by_provenance(items, rank_of=lambda _item: PROMOTION_RANK_NEUTRAL) == items

    ranked = ["estimate", "neutral", "user"]
    ranks = {
        "estimate": PROMOTION_RANK_ASSISTANT_ESTIMATE,
        "neutral": PROMOTION_RANK_NEUTRAL,
        "user": PROMOTION_RANK_USER_ASSERTED,
    }
    assert order_by_provenance(ranked, rank_of=lambda item: ranks[item]) == [
        "user",
        "neutral",
        "estimate",
    ]
