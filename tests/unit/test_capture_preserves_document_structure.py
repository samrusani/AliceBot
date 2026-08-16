"""Capture a document through the MCP tool, then read the stored rows back.

This test exists because of a specific process failure, and the shape of the test
is the lesson rather than the assertion.

On 2026-08-16 v0.15.5 shipped a chunker fix for exactly this symptom: a markdown
vault imported through `alice_capture` produced memories spanning unrelated notes,
so searching for a quote the vault contained returned nothing. The fix worked when
`chunk_text` was called directly, and it was inert in production.

The reason nothing caught it: two test layers sandwiched the bug. Unit tests
called `chunk_text` with real newlines and passed. Schema tests validated MCP
payloads and passed. Neither followed a document through the MCP boundary into
storage, and the defect lived exactly there. `_parse_required_text` collapses
every whitespace run to a single space, `capture_automation` used it for
`raw_text`, and a file with 17 newlines was stored with 0. `chunk_text` splits on
blank lines, so a flattened document is one paragraph and gets cut on word count
instead, straddling notes.

Introduced in v0.12.0 (`2b3cd5d`), so it survived every release since, an external
audit, and my own review.

**Assert on stored rows, not on the tool's own report.** The capture response said
`chunk_count: 1` and was telling the truth about a wrong outcome. Only the
database showed why.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


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

CODE_NOTE = """# Setup

Run the server:

```bash
    uvx alice-memory mcp --data-dir ~/.alice
```

Then talk to your agent.
"""


USER_ID = "00000000-0000-0000-0000-000000000001"


def _capture_and_read_chunks(tmp_path: Path, raw_text: str) -> list[str]:
    """Drive the real parser and capture service, then read source_chunks from SQLite."""

    from alicebot_api.mcp.arguments import _parse_required_document_text
    from alicebot_api.onramp import bootstrap_database, resolve_db_path
    from alicebot_api.sqlite_store import SQLiteVNextStore, sqlite_user_connection

    from alicebot_api.vnext_capture import VNextCaptureService

    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    bootstrap_database(database, user_id=USER_ID, user_email="local@alice")

    # The MCP argument parser is the layer that was destroying structure, so the
    # test must go through it rather than around it.
    parsed = _parse_required_document_text({"raw_text": raw_text}, "raw_text")

    with sqlite_user_connection(database, USER_ID) as connection:
        store = SQLiteVNextStore(connection, USER_ID)
        VNextCaptureService(store, actor_type="user_or_system").capture_text(
            parsed, title="Vault", domain="personal", sensitivity="private"
        )

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT text FROM source_chunks ORDER BY chunk_index"
        ).fetchall()
    return [row[0] for row in rows]


def _dispatch_alice_capture_and_read_chunks(tmp_path: Path, raw_text: str) -> list[str]:
    """Dispatch `alice_capture` through the registry, then read the stored rows.

    This is the version that pins the wiring. The helper above proves the document
    parser behaves; only this one proves `alice_capture` actually calls it.
    """

    from alicebot_api.mcp.registry import call_mcp_tool
    from alicebot_api.mcp_tools import MCPRuntimeContext
    from alicebot_api.onramp import bootstrap_database, resolve_db_path, sqlite_url_for_path

    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    bootstrap_database(database, user_id=USER_ID, user_email="local@alice")
    context = MCPRuntimeContext(database_url=sqlite_url_for_path(database), user_id=USER_ID)

    call_mcp_tool(
        context,
        name="alice_capture",
        arguments={
            "raw_text": raw_text,
            "title": "Vault",
            "domain": "personal",
            "sensitivity": "private",
        },
    )

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT text FROM source_chunks ORDER BY chunk_index"
        ).fetchall()
    return [row[0] for row in rows]


def test_alice_capture_dispatched_through_the_registry_preserves_structure(
    tmp_path: Path,
) -> None:
    """The wiring test. Reverting the call site alone must fail something.

    A review on 2026-08-16 found that every other test here passed with
    `capture_automation` switched back to `_parse_required_text`, because they all
    called the parser directly. That is the same sandwich that let the original
    defect ship: proving a part works is not proving the product uses it.
    """

    chunks = _dispatch_alice_capture_and_read_chunks(tmp_path, QUOTES_VAULT)

    assert len(chunks) == 3, (
        f"alice_capture stored {len(chunks)} chunk(s) for a three-heading vault. "
        "The handler is not using the document parser."
    )
    assert any("\n" in chunk for chunk in chunks), "stored chunks carry no newlines"


def test_alice_capture_keeps_one_quote_free_of_its_neighbours(tmp_path: Path) -> None:
    chunks = _dispatch_alice_capture_and_read_chunks(tmp_path, QUOTES_VAULT)
    quote = "Discipline is the art of not betraying yourself"

    holding = [chunk for chunk in chunks if quote in chunk]
    assert len(holding) == 1
    assert "Osho" not in holding[0]
    assert "John A. Shedd" not in holding[0]


def test_the_mcp_argument_parser_preserves_newlines(tmp_path: Path) -> None:
    """The narrowest statement of the defect, at the exact layer it lived."""

    from alicebot_api.mcp.arguments import _parse_required_document_text

    parsed = _parse_required_document_text({"raw_text": QUOTES_VAULT}, "raw_text")

    assert parsed.count("\n") == QUOTES_VAULT.strip().count("\n"), (
        "raw_text lost line structure at the MCP boundary; chunking cannot recover it"
    )


def test_a_markdown_vault_becomes_one_chunk_per_note(tmp_path: Path) -> None:
    chunks = _capture_and_read_chunks(tmp_path, QUOTES_VAULT)

    assert len(chunks) == 3, (
        f"expected one stored chunk per heading, got {len(chunks)}. "
        "A single chunk means the document was flattened before chunking."
    )


def test_an_exact_quote_is_stored_without_its_neighbours(tmp_path: Path) -> None:
    """The property the user's failed recall actually needed."""

    chunks = _capture_and_read_chunks(tmp_path, QUOTES_VAULT)
    quote = "Discipline is the art of not betraying yourself"

    holding = [chunk for chunk in chunks if quote in chunk]
    assert len(holding) == 1

    contaminated = [name for name in ("Osho", "John A. Shedd") if name in holding[0]]
    assert not contaminated, (
        f"the stored chunk holding one quote also carries {contaminated}; a candidate "
        "memory extracted from it would span unrelated notes"
    )


def test_stored_chunks_keep_their_internal_line_structure(tmp_path: Path) -> None:
    chunks = _capture_and_read_chunks(tmp_path, QUOTES_VAULT)

    assert any("\n" in chunk for chunk in chunks), (
        "no stored chunk contains a newline, so the document was flattened"
    )


def test_indentation_inside_a_code_block_survives(tmp_path: Path) -> None:
    """Whitespace collapsing destroyed more than paragraph breaks."""

    chunks = _capture_and_read_chunks(tmp_path, CODE_NOTE)
    joined = "\n".join(chunks)

    assert "```bash" in joined
    assert "    uvx alice-memory" in joined, "leading indentation was collapsed"


@pytest.mark.parametrize("line_ending", ("\r\n", "\r"))
def test_foreign_line_endings_are_normalised_not_flattened(
    tmp_path: Path, line_ending: str
) -> None:
    from alicebot_api.mcp.arguments import _parse_required_document_text

    source = QUOTES_VAULT.replace("\n", line_ending)
    parsed = _parse_required_document_text({"raw_text": source}, "raw_text")

    assert "\r" not in parsed
    assert parsed == QUOTES_VAULT.strip()


def test_an_empty_or_whitespace_document_is_still_rejected(tmp_path: Path) -> None:
    """The looser parser must not become a way to store nothing."""

    from alicebot_api.mcp.arguments import _parse_required_document_text
    from alicebot_api.mcp_tools import MCPToolError

    for empty in ("", "   ", "\n\n\n", "\r\n \r\n"):
        with pytest.raises(MCPToolError):
            _parse_required_document_text({"raw_text": empty}, "raw_text")


def test_short_scalar_fields_still_collapse_whitespace() -> None:
    """The narrowness of the change. A title is not a document."""

    from alicebot_api.mcp.arguments import _parse_required_text

    assert _parse_required_text({"title": "  Release   gate\n decision "}, "title") == (
        "Release gate decision"
    )
