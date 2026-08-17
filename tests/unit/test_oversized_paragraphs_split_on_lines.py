"""An oversized paragraph splits on its own lines before it splits on words.

Found 2026-08-17 by inspecting a real 226-document vault import after v0.15.6.
The heading-boundary fix worked: 710 chunks, lengths from 9 to 2398, structure
preserved in 698 of them. But five chunks carried no newline at all and two sat
at the character ceiling, one ending mid-sentence inside item 22 of a quote list.

The cause is `_split_large_part`, which only sees paragraphs that alone exceed
`max_chars`. It did `part.split()` and `" ".join(...)`, which splits on every
whitespace character and rejoins with single spaces. So it cut at an arbitrary
word *and* discarded the paragraph's internal newlines.

That is wrong for the shape it actually meets in notes: a numbered or bulleted
list written one item per line with no blank line between items. Markdown reads
that as a single paragraph, so a long list arrived here and left as flattened
word-count slices with items cut in half.

Splitting on lines first fixes it. The word splitter stays as the fallback for a
paragraph that genuinely is one long line, and prose is untouched, because only
oversized paragraphs reach this function at all.
"""

from __future__ import annotations

import re

import pytest

from alicebot_api.vnext_capture import DEFAULT_CHUNK_MAX_CHARS, chunk_text


def _numbered_list(count: int) -> list[str]:
    return [
        f'{index}. "Quote number {index} about discipline and the long road to '
        f'mastery, said plainly and at some length."'
        for index in range(1, count + 1)
    ]


LIST_ITEMS = _numbered_list(40)
LIST_NOTE = "## Collected quotes\n\n" + "\n".join(LIST_ITEMS)


def test_the_note_is_actually_oversized() -> None:
    """Guards the guard: if this stops exceeding the budget, nothing below tests anything."""

    body = "\n".join(LIST_ITEMS)
    assert len(body) > DEFAULT_CHUNK_MAX_CHARS, (
        "the fixture no longer exceeds max_chars, so _split_large_part is never reached"
    )
    assert "\n\n" not in body, "the fixture must be ONE paragraph for this to be the real case"


def test_no_list_item_is_cut_across_a_chunk_boundary() -> None:
    """The user-visible defect: a quote split in half cannot be found by either half."""

    chunks = chunk_text(LIST_NOTE)
    joined = "\n".join(chunks)

    intact = [item for item in LIST_ITEMS if item in joined]
    assert len(intact) == len(LIST_ITEMS), (
        f"{len(LIST_ITEMS) - len(intact)} list items were cut across a chunk boundary"
    )


def test_line_structure_survives_an_oversized_paragraph() -> None:
    chunks = chunk_text(LIST_NOTE)
    multi_line = [chunk for chunk in chunks if "\n" in chunk]

    assert multi_line, "every chunk was flattened to a single line"


def test_chunks_still_respect_the_budget() -> None:
    for chunk in chunk_text(LIST_NOTE):
        assert len(chunk) <= DEFAULT_CHUNK_MAX_CHARS


def test_a_genuinely_single_long_line_still_word_splits() -> None:
    """The fallback must remain. One enormous line has no line structure to use."""

    one_line = "word " * 900
    chunks = chunk_text(one_line)

    assert len(chunks) > 1
    assert all(len(chunk) <= DEFAULT_CHUNK_MAX_CHARS for chunk in chunks)


def test_a_single_token_longer_than_the_budget_is_still_hard_split() -> None:
    """No line structure and no word boundary; the character splitter must survive."""

    chunks = chunk_text("x" * (DEFAULT_CHUNK_MAX_CHARS * 2 + 50))

    assert len(chunks) >= 2
    assert all(len(chunk) <= DEFAULT_CHUNK_MAX_CHARS for chunk in chunks)


@pytest.mark.parametrize("bullet", ("- ", "* ", "+ ", "1. "))
def test_bulleted_lists_behave_the_same_as_numbered_ones(bullet: str) -> None:
    items = [f"{bullet}A list item with enough text on it to matter, number {n}." for n in range(90)]
    body = "\n".join(items)
    assert len(body) > DEFAULT_CHUNK_MAX_CHARS

    joined = "\n".join(chunk_text(body))

    assert all(item in joined for item in items), "a bullet item was cut across a boundary"


def test_one_oversized_item_does_not_flatten_the_rest_of_the_list() -> None:
    """The mixed case. Review caught that the first draft got this wrong.

    That draft required *every* line to fit before packing by line, so a single
    long item disqualified the whole paragraph and flattened all its neighbours
    with it. Only the oversized line should lose its structure.
    """

    short_items = _numbered_list(30)
    monster = "99. " + ("a very long unbroken clause about persistence " * 80)
    assert len(monster) > DEFAULT_CHUNK_MAX_CHARS, "the fixture must contain an oversized line"

    body = "\n".join([*short_items[:15], monster, *short_items[15:]])
    chunks = chunk_text(body)
    joined = "\n".join(chunks)

    intact = [item for item in short_items if item in joined]
    assert len(intact) == len(short_items), (
        f"one oversized line flattened its neighbours: only {len(intact)} of "
        f"{len(short_items)} short items survived intact"
    )
    assert any("\n" in chunk for chunk in chunks), "line structure was lost entirely"
    assert all(len(chunk) <= DEFAULT_CHUNK_MAX_CHARS for chunk in chunks)


def test_an_oversized_line_is_itself_word_split_not_dropped() -> None:
    """The oversized line must still be stored, just without its own structure."""

    monster = "one " * (DEFAULT_CHUNK_MAX_CHARS // 2)
    body = "1. short leading item\n" + monster + "\n2. short trailing item"

    joined = " ".join(chunk_text(body))

    assert "short leading item" in joined
    assert "short trailing item" in joined
    assert joined.count("one") > 100, "the oversized line's content was dropped"


def test_prose_and_turn_shapes_are_unchanged() -> None:
    """The narrowness of the change: only oversized paragraphs reach the splitter."""

    prose = "\n\n".join(f"Paragraph {index} of ordinary prose." for index in range(6))
    assert len(chunk_text(prose)) == 1

    turns = "\n\n".join(
        f"{'user' if index % 2 else 'assistant'}: turn number {index}." for index in range(8)
    )
    assert len(chunk_text(turns)) == 1


def test_the_heading_rule_from_v0_15_6_still_holds() -> None:
    vault = (
        "# Discipline\n\n> Discipline is the art of not betraying yourself.\n\n"
        "## Solitude\n\n> The capacity to be alone is the capacity to love.\n\n"
        "## Risk\n\n> Ships are safe in harbour.\n"
    )

    assert len(chunk_text(vault)) == 3


def test_a_reconstructed_real_vault_list_keeps_every_item() -> None:
    """Shaped from the actual chunk found in the user's store, not invented."""

    raw = " ".join(
        f'{index}. "A collected line of the kind this vault stores, entry {index}."'
        for index in range(1, 60)
    )
    reconstructed = re.sub(r"\s(\d{1,3}\.\s)", r"\n\1", raw).strip()
    items = re.findall(r"(?m)^\d{1,3}\..*$", reconstructed)
    assert len(items) > 1

    joined = "\n".join(chunk_text(reconstructed))

    assert all(item in joined for item in items)
