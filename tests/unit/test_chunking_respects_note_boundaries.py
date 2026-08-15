"""Chunking must not pack across an author-declared section boundary.

Reported from a real Obsidian import on 2026-08-15. A whole-vault quotes library
came in as 6 sources and 107 candidate memories, and `alice_recall` returned
nothing for an exact quote the vault definitely contained. The agent doing the
import noticed the shape of it: "candidate extraction sometimes spans adjacent
notes rather than producing one clean quote per memory".

The cause is here. `chunk_text` split on blank lines and then greedily packed
paragraphs up to `max_chars` (2400), treating a markdown heading as ordinary
prose. Short notes are far below that limit, so dozens of unrelated quotes
collapsed into a single chunk, one candidate memory was extracted spanning all of
them, and searching for any single quote matched a soup of others.

Reproduced before the fix: four quotes under their own `##` headings produced
exactly one chunk.

The rule is narrow on purpose. Headings and thematic breaks end the current
chunk; nothing else changes, so prose still packs to `max_chars` and the
speaker-tagged turn shape the LongMemEval harness depends on is untouched.
"""

from __future__ import annotations

import pytest

from alicebot_api.vnext_capture import DEFAULT_CHUNK_MAX_CHARS, chunk_text


QUOTES_VAULT = """# Discipline

> Discipline is the art of not betraying yourself.

— Unknown

## Solitude

> The capacity to be alone is the capacity to love.

— Osho

## Risk

> Ships are safe in harbour, but that is not what ships are for.

— John A. Shedd
"""


def test_each_note_becomes_its_own_chunk() -> None:
    chunks = chunk_text(QUOTES_VAULT)

    assert len(chunks) == 3, f"expected one chunk per heading, got {len(chunks)}: {chunks}"


def test_an_exact_quote_lands_in_exactly_one_chunk_with_no_neighbours() -> None:
    """The property the failed recall actually needed."""

    chunks = chunk_text(QUOTES_VAULT)
    quote = "Discipline is the art of not betraying yourself"

    matching = [chunk for chunk in chunks if quote in chunk]
    assert len(matching) == 1

    contaminated = [author for author in ("Osho", "John A. Shedd") if author in matching[0]]
    assert not contaminated, (
        f"the chunk holding one quote also carries {contaminated}; a candidate memory "
        "extracted from it would span unrelated notes"
    )


@pytest.mark.parametrize("break_marker", ("---", "***", "___", "-----"))
def test_thematic_breaks_also_end_a_chunk(break_marker: str) -> None:
    text = f"First note body.\n\n{break_marker}\n\nSecond note body."

    chunks = chunk_text(text)

    assert len(chunks) == 2
    assert "Second note body." not in chunks[0]


def test_prose_without_headings_still_packs_to_the_budget() -> None:
    """The narrowness of the rule. Ordinary prose must be unaffected."""

    prose = "\n\n".join(f"Paragraph {index} of ordinary prose." for index in range(6))

    assert len(chunk_text(prose)) == 1


def test_speaker_tagged_turns_are_unchanged() -> None:
    """The LongMemEval harness renders one paragraph per turn and relies on packing.

    If this splits, the benchmark's ingest shape changes and the published score
    stops describing the shipped code.
    """

    turns = "\n\n".join(
        f"{'user' if index % 2 else 'assistant'}: turn number {index}." for index in range(8)
    )

    assert len(chunk_text(turns)) == 1


def test_a_heading_stays_with_the_body_it_introduces() -> None:
    chunks = chunk_text(QUOTES_VAULT)

    assert chunks[0].startswith("# Discipline")
    assert "not betraying yourself" in chunks[0]


def test_the_max_chars_budget_is_still_enforced_within_a_section() -> None:
    body = "\n\n".join("A sentence of filler prose." for _ in range(400))
    text = f"## One heading\n\n{body}"

    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= DEFAULT_CHUNK_MAX_CHARS for chunk in chunks)


def test_a_hash_inside_a_line_is_not_a_heading() -> None:
    """`#` only opens a section at the start of a line, followed by a space."""

    text = "Ticket #42 was closed today.\n\nIt shipped in release #7."

    assert len(chunk_text(text)) == 1
