"""Write receipts: one printed line for capture and commit.

Each test names the edit that makes it fail.
"""

from __future__ import annotations

from pathlib import Path

from alicebot_api.mcp_tools import MCPRuntimeContext
from alicebot_api.onramp import bootstrap_database, resolve_db_path, sqlite_url_for_path
from alicebot_api.vnext_capture import CaptureResult


USER_ID = "00000000-0000-0000-0000-000000000001"
SOURCE_NOTE = "Fact: The indigo-lighthouse-42 canary stays in the vault."
FACT_TITLE = "Public acme launch"
FACT_TEXT = "We will keep the public acme launch checklist on Thursday."
SAVED_AS_A_FACT = "saved as a fact."
SEARCHABLE_NOW = "searchable now"


def _context(tmp_path: Path) -> MCPRuntimeContext:
    database = resolve_db_path(data_dir=str(tmp_path), db=None)
    bootstrap_database(database, user_id=USER_ID, user_email="local@alice")
    return MCPRuntimeContext(database_url=sqlite_url_for_path(database), user_id=USER_ID)


def _call(context: MCPRuntimeContext, name: str, arguments: dict[str, object]) -> dict:
    from alicebot_api.mcp.registry import call_mcp_tool

    return call_mcp_tool(context, name=name, arguments=arguments)


def test_alice_capture_returns_a_source_receipt_with_chunk_count(tmp_path: Path) -> None:
    """A real alice_capture (flag on) prints what became searchable.

    Mutation: drop ``receipt`` from ``CaptureResult.to_record``. This test
    fails.
    """

    payload = _call(
        _context(tmp_path),
        "alice_capture",
        {
            "raw_text": SOURCE_NOTE,
            "title": "Vault canary",
            "domain": "personal",
            "sensitivity": "private",
        },
    )

    assert payload["status"] == "imported", payload
    receipt = payload.get("receipt")
    assert isinstance(receipt, str) and receipt, "capture no longer returns a receipt"
    assert "saved as source" in receipt
    assert f"{payload['chunk_count']} chunks searchable now" in receipt
    expected = f"saved as source, {payload['chunk_count']} chunks searchable now"
    if payload["candidate_memory_count"] > 0:
        expected += f", {payload['candidate_memory_count']} candidates waiting in review"
    assert receipt == expected
    assert SAVED_AS_A_FACT not in receipt


def test_zero_chunk_and_duplicate_receipts_do_not_claim_searchable_or_a_fact() -> None:
    """Empty and duplicate captures must not pretend the text is findable.

    Mutation: emit the imported searchable line for ``chunk_count == 0``
    or for ``status == duplicate``. This test fails.
    """

    zero = CaptureResult(status="imported", source_id="src-1", content_hash="h", chunk_count=0).to_record()
    duplicate = CaptureResult(status="duplicate", source_id="src-1", content_hash="h", duplicate=True).to_record()
    failed = CaptureResult(
        status="failed", source_id=None, content_hash="h", errors=("source_import_failed",)
    ).to_record()

    for record in (zero, duplicate, failed):
        receipt = record["receipt"]
        assert SEARCHABLE_NOW not in receipt
        assert SAVED_AS_A_FACT not in receipt
        assert "saved as a fact" not in receipt

    assert "saved as source" in zero["receipt"]
    assert SEARCHABLE_NOW not in zero["receipt"]
    assert "duplicate" in duplicate["receipt"]
    assert "saved" not in duplicate["receipt"]
    assert "saved" not in failed["receipt"]


def test_alice_capture_duplicate_receipt_does_not_claim_a_new_save(tmp_path: Path) -> None:
    """A second capture of the same text is a duplicate, not a new save."""

    context = _context(tmp_path)
    arguments = {
        "raw_text": SOURCE_NOTE,
        "title": "Vault canary",
        "domain": "personal",
        "sensitivity": "private",
    }
    first = _call(context, "alice_capture", arguments)
    second = _call(context, "alice_capture", arguments)

    assert first["status"] == "imported", first
    assert second["status"] == "duplicate", second
    assert "duplicate" in second["receipt"]
    assert SEARCHABLE_NOW not in second["receipt"]
    assert "saved" not in second["receipt"]
    assert SAVED_AS_A_FACT not in second["receipt"]


def test_alice_memory_commit_of_a_fact_returns_saved_as_a_fact(tmp_path: Path) -> None:
    """Ordinary commit receipt is the line a host will echo.

    Mutation: omit ``receipt`` on the committed path. This test fails.
    """

    context = _context(tmp_path)
    arguments: dict[str, object] = {
        "title": FACT_TITLE,
        "canonical_text": FACT_TEXT,
        "memory_type": "decision",
        "domain": "project",
        "sensitivity": "public",
        "confidence": 0.96,
        "project_scope": ["acme"],
        "rationale": "User said: remember this",
        "idempotency_key": "write-receipt-fact-1",
    }
    payload = _call(context, "alice_memory_commit", arguments)

    assert payload["status"] == "committed", payload
    assert payload.get("receipt") == SAVED_AS_A_FACT

    replay = _call(context, "alice_memory_commit", arguments)
    assert replay["idempotent_replay"] is True
    assert replay["receipt"] == SAVED_AS_A_FACT


def test_gated_commit_receipts_do_not_say_saved_as_a_fact(tmp_path: Path) -> None:
    """Confirmation and rejection must not claim a fact was stored."""

    context = _context(tmp_path)
    pending = _call(
        context,
        "alice_memory_commit",
        {
            "title": "Private health note",
            "canonical_text": "The user is starting a confidential health plan on Monday.",
            "domain": "health",
            "sensitivity": "confidential",
            "confidence": 0.96,
        },
    )
    rejected = _call(
        context,
        "alice_memory_commit",
        {
            "title": "Staging secret",
            "canonical_text": "The staging api_key=hunter2 is tucked in here.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.96,
        },
    )
    review = _call(
        context,
        "alice_memory_commit",
        {
            "title": "Browser clip note",
            "canonical_text": "A page said the launch window moved to Friday.",
            "domain": "professional",
            "sensitivity": "internal",
            "confidence": 0.4,
            "source_type": "browser_clip",
        },
    )

    assert pending["status"] == "confirmation_required", pending
    assert rejected["status"] == "rejected", rejected
    assert review["status"] == "review_required", review
    for payload in (pending, rejected, review):
        receipt = payload.get("receipt")
        assert isinstance(receipt, str) and receipt, payload
        assert SAVED_AS_A_FACT not in receipt
        assert "saved as a fact" not in receipt
