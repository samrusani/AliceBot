"""Import a document, then read it back through the tools an agent actually calls.

The defect these tests pin, found 2026-08-17 by inspecting a real 226-document
vault import: capture was write-only. A user could import their notes and then
retrieve nothing from them by any route the MCP surface offered.

Three independent causes, each sufficient on its own:

1. A packed source carried ``metadata_json``, and capture stores the entire
   document in there as evidence. ``estimate_item_tokens`` JSON-dumps the item
   to price it, so a 235KB source was charged roughly 59k tokens against a 50k
   ceiling, was rejected, and *latched* the pack's truncation flag, dropping
   every later section too. Above roughly 30k characters sources vanished, and
   no setting could raise the ceiling far enough.
2. The MCP compaction emitted only id/type/title/date/domain/sensitivity, so a
   source that did survive the budget reached the agent as a bibliography entry.
   Retrieval ranked the right chunks and then threw the text away.
3. ``alice_recall`` searched memories only. Since capture stores candidates and
   candidates are unsearchable by design, the natural agent sequence (import,
   then recall) answered ``count=0`` for content the store held.

The benchmark could not see any of this: the LongMemEval harness renders
excerpts itself by calling ``list_source_chunks`` directly, a capability the
shipped tools never exposed. So 81.2% measured a retrieval path no user had.

Each test below is one of those causes. They assert on what an agent receives,
not on internals, because every one of these defects was invisible from inside
the component that caused it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

USER_ID = "00000000-0000-0000-0000-000000000001"

QUOTE = "Discipline is the art of not betraying yourself."

# Shaped from the real vault. The "## Related" block is the trap: it repeats
# every query term inside wikilink paths, so a naive `term in text` scorer
# ranks it above the note that actually contains the sentence.
QUOTE_NOTE = f"""---
Added: 2026-07-28
Tags: #quote #discipline #habits
---

# "{QUOTE[:-1]}"

**Theme:** Discipline and Self-Mastery
**Author:** Unknown

> {QUOTE}

## Why it resonates

Keeping a promise to yourself is the whole of it.

## Related

- [[themes/discipline-and-self-mastery/discipline-is-the-art-of-not-betraying-yourself]]
- [[themes/discipline-and-self-mastery/discipline-is-not-betraying-yourself-again]]
- [[themes/discipline-and-self-mastery/the-art-of-discipline-and-not-betraying]]
- [[themes/discipline-and-self-mastery/betraying-yourself-is-the-opposite-of-discipline]]
"""


def _fresh_context(tmp_path: Path):
    from alicebot_api.mcp_tools import MCPRuntimeContext
    from alicebot_api.onramp import bootstrap_database, resolve_db_path, sqlite_url_for_path

    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    bootstrap_database(database, user_id=USER_ID, user_email="local@alice")
    return MCPRuntimeContext(database_url=sqlite_url_for_path(database), user_id=USER_ID)


def _capture(context, raw_text: str, *, title: str = "Vault") -> dict:
    from alicebot_api.mcp.registry import call_mcp_tool

    return call_mcp_tool(
        context,
        name="alice_capture",
        arguments={
            "raw_text": raw_text,
            "title": title,
            "domain": "personal",
            "sensitivity": "private",
        },
    )


def _recall(context, query: str) -> dict:
    from alicebot_api.mcp.registry import call_mcp_tool

    return call_mcp_tool(context, name="alice_recall", arguments={"query": query})


def _pack(context, query: str) -> dict:
    from alicebot_api.mcp.registry import call_mcp_tool

    return call_mcp_tool(context, name="alice_context_pack", arguments={"query": query})


# --------------------------------------------------------------------------
# Cause 3: recall never looked at sources at all.
# --------------------------------------------------------------------------


def test_recall_returns_the_imported_document_it_just_captured(tmp_path: Path) -> None:
    """Import, then recall. The sequence every agent performs first."""

    context = _fresh_context(tmp_path)
    _capture(context, QUOTE_NOTE)

    payload = _recall(context, QUOTE)
    sources = payload.get("sources") or []

    assert sources, (
        "alice_recall returned nothing for a document captured moments earlier. "
        "Capture is write-only again."
    )
    assert payload["source_count"] == len(sources)
    assert any(QUOTE in (source.get("excerpt") or "") for source in sources), (
        "a source came back but its excerpt does not contain the sentence that was searched for"
    )


def test_recall_keeps_asserted_facts_and_read_only_material_apart(tmp_path: Path) -> None:
    """The labelling is the safety property, not decoration.

    Source text is material to read and quote. It must never arrive looking like
    a fact Alice stands behind, and capture must not have promoted anything.
    """

    context = _fresh_context(tmp_path)
    _capture(context, QUOTE_NOTE)

    payload = _recall(context, QUOTE)

    assert payload["count"] == 0, (
        "capture promoted a memory to searchable. Candidates must stay unsearchable "
        "until a reviewer promotes them; this path must not have become a way around that."
    )
    for source in payload["sources"]:
        assert source.get("excerpt_kind") == "imported_source_material"
    assert "sources" in payload and "results" in payload, "the two channels were merged"


# --------------------------------------------------------------------------
# Cause 1: the duplicated document blew the token budget.
# --------------------------------------------------------------------------


def test_a_large_import_does_not_truncate_the_context_pack(tmp_path: Path) -> None:
    """The latching failure: one fat source used to drop every later section.

    Sized past the point where the old code broke. The document is stored once
    as chunks and once more inside metadata_json; pricing the second copy is
    what blew a 50k ceiling on a single item.
    """

    context = _fresh_context(tmp_path)
    big = "\n\n".join(
        f"## Note {index}\n\n> {QUOTE}\n\nSome supporting prose for note {index}."
        for index in range(400)
    )
    assert len(big) > 30_000, "fixture is smaller than the size where sources used to disappear"
    _capture(context, big, title="Big vault")

    pack = _pack(context, QUOTE)

    assert pack.get("sources"), "a large import packs zero sources, the budget defect is back"
    budget = pack.get("budget") or {}
    assert budget.get("truncated") is not True, (
        "one oversized source latched the pack's truncation flag again"
    )


def _compile_pack_uncompacted(tmp_path: Path, raw_text: str, query: str) -> dict:
    """Compile through the service, below the MCP layer.

    This distinction is the whole point of the test that follows. MCP compaction
    keeps an allowlist of six fields, so ``metadata_json`` can never appear in a
    tool payload whether or not anything removed it. Asserting up there proves
    nothing: the first version of this test passed with the fix reverted.

    The token budget runs *below* compaction, on the service's own pack, and
    that is where a duplicated document costs 59k tokens.
    """

    from alicebot_api.onramp import bootstrap_database, resolve_db_path
    from alicebot_api.sqlite_store import SQLiteVNextStore, sqlite_user_connection
    from alicebot_api.vnext_capture import VNextCaptureService
    from alicebot_api.vnext_retrieval import VNextRetrievalRequest, VNextRetrievalService

    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    bootstrap_database(database, user_id=USER_ID, user_email="local@alice")

    with sqlite_user_connection(database, USER_ID) as connection:
        store = SQLiteVNextStore(connection, USER_ID)
        VNextCaptureService(store, actor_type="user_or_system").capture_text(
            raw_text, title="Vault", domain="personal", sensitivity="private"
        )
        return VNextRetrievalService(store).compile_context_pack(
            VNextRetrievalRequest(query=query)
        )


def test_a_packed_source_never_carries_the_whole_document(tmp_path: Path) -> None:
    """The mechanism, pinned where it lives, so a regression is diagnosable.

    Review caught the first fix dropping ``metadata_json`` wholesale, which
    silently un-dated every imported source because ``_source_event_time`` reads
    ``session_date`` out of it. Only the duplicated document may be removed, so
    this asserts both halves: the document is gone, the rest of the blob stays.
    """

    from alicebot_api.vnext_retrieval import SOURCE_EXCERPT_MAX_CHARS, estimate_item_tokens

    pack = _compile_pack_uncompacted(tmp_path, QUOTE_NOTE, QUOTE)
    sources = pack.get("sources") or []
    assert sources, "the service packed no sources at all"

    for source in sources:
        metadata = source.get("metadata_json")
        if isinstance(metadata, dict):
            assert "raw_text" not in metadata, (
                "the packed source still carries the whole document, which is what "
                "priced a single item past the entire pack budget"
            )
        # The cost, not just the shape: pricing is what actually broke.
        assert estimate_item_tokens(source) < 5_000, (
            "a packed source is expensive enough to threaten the budget again"
        )
        excerpt = source.get("excerpt")
        if excerpt:
            assert len(excerpt) <= SOURCE_EXCERPT_MAX_CHARS


def test_imported_sources_still_get_their_event_time_stamped(tmp_path: Path) -> None:
    """The regression review caught: metadata_json must survive, minus the document."""

    from alicebot_api.vnext_retrieval import _source_event_time

    context = _fresh_context(tmp_path)
    _capture(context, QUOTE_NOTE)

    pack = _pack(context, QUOTE)
    sources = pack.get("sources") or []
    assert sources

    # The compaction must not have stripped what temporal precompute reads. A
    # source with no derivable time is exactly the silent breakage review found.
    assert any(_source_event_time(source) is not None for source in sources), (
        "no packed source has a derivable event time; metadata_json was stripped too far"
    )


# --------------------------------------------------------------------------
# Cause 2: the agent received a bibliography entry with no text.
# --------------------------------------------------------------------------


def test_the_mcp_surface_delivers_the_excerpt_not_just_a_citation(tmp_path: Path) -> None:
    """Compaction runs between retrieval and the agent, and used to drop the text."""

    context = _fresh_context(tmp_path)
    _capture(context, QUOTE_NOTE)

    pack = _pack(context, QUOTE)
    sources = pack.get("sources") or []
    assert sources, "no sources in the pack at all"

    with_text = [source for source in sources if source.get("excerpt")]
    assert with_text, (
        "every packed source arrived as a citation with no text. The compaction "
        "field list dropped the excerpt again."
    )
    for source in with_text:
        assert source["excerpt_kind"] == "imported_source_material"


# --------------------------------------------------------------------------
# The windowing case review asked for by name.
# --------------------------------------------------------------------------


def test_the_excerpt_shows_the_quote_not_the_related_links_block(tmp_path: Path) -> None:
    """A wikilink block repeating every query term must not win the window.

    The first draft re-derived a "best" chunk here with ``term in text`` and
    picked the ``## Related`` block, because the query terms all appear inside
    its URLs. Retrieval had already ranked a winner; the fix keeps it and scores
    lines by token overlap rather than substring.
    """

    context = _fresh_context(tmp_path)
    _capture(context, QUOTE_NOTE)

    payload = _recall(context, QUOTE)
    sources = payload.get("sources") or []
    assert sources

    excerpt = sources[0].get("excerpt") or ""
    assert QUOTE in excerpt, f"the excerpt does not contain the quote. Got: {excerpt[:200]!r}"

    link_lines = [line for line in excerpt.splitlines() if line.strip().startswith("- [[")]
    quote_lines = [line for line in excerpt.splitlines() if QUOTE in line]
    assert quote_lines, "no line of the excerpt carries the sentence"
    assert len(link_lines) < len(excerpt.splitlines()), (
        "the excerpt is nothing but the Related links block"
    )


@pytest.mark.parametrize(
    "query",
    (
        "discipline",
        "not betraying yourself",
        "what did I save about keeping promises to myself",
    ),
)
def test_several_phrasings_all_reach_the_document(tmp_path: Path, query: str) -> None:
    """One query working could be luck. The user does not know the magic words."""

    context = _fresh_context(tmp_path)
    _capture(context, QUOTE_NOTE)

    payload = _recall(context, query)

    assert payload.get("sources"), f"query {query!r} returned no source material"


# --------------------------------------------------------------------------
# The capture receipt: what the agent tells its user.
# --------------------------------------------------------------------------


def test_capture_reports_what_became_searchable(tmp_path: Path) -> None:
    """``chunk_count`` and ``candidate_memory_count`` read as two counts of the
    same stored thing. They are not, and the difference is what an agent repeats
    to its user."""

    context = _fresh_context(tmp_path)
    record = _capture(context, QUOTE_NOTE)

    retrieval = record.get("retrieval")
    assert isinstance(retrieval, dict), "capture no longer says what became retrievable"
    assert retrieval["searchable_now"] == "source_material"
    assert retrieval["searchable_chunks"] == record["chunk_count"]
    assert retrieval["awaiting_review"] == record["candidate_memory_count"]
    assert "alice_recall" in retrieval["how"]


def test_capture_does_not_claim_searchability_when_nothing_was_indexed() -> None:
    """The honest empty case, asserted on the record itself."""

    from alicebot_api.vnext_capture import CaptureResult

    record = CaptureResult(status="duplicate", source_id=None, content_hash="x").to_record()

    assert record["retrieval"]["searchable_now"] == "nothing"
    assert record["retrieval"]["searchable_chunks"] == 0
    assert "alice_recall" not in record["retrieval"]["how"]
