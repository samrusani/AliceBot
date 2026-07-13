from __future__ import annotations

from pathlib import Path

import alicebot_api.vnext_reranker as reranker_module
from alicebot_api.vnext_ranking import (
    TIE_BREAK_CONTENT_STABLE,
    content_stable_event_time,
    content_stable_tiebreak,
)


def test_shared_tiebreak_prefers_content_event_time_then_longer_text() -> None:
    older = {
        "id": "new-uuid",
        "canonical_text": "short",
        "metadata_json": {"session_date": "2025-01-01T00:00:00Z"},
    }
    newer = {
        "id": "old-uuid",
        "canonical_text": "a much longer row",
        "metadata_json": {"session_date": "2025-02-01T00:00:00Z"},
    }
    undated_short = {"canonical_text": "short"}
    undated_long = {"canonical_text": "a much longer row"}

    assert TIE_BREAK_CONTENT_STABLE == "content_stable_v1"
    assert content_stable_event_time(older) is not None
    assert content_stable_tiebreak(older) < content_stable_tiebreak(newer)
    assert content_stable_tiebreak(undated_long) < content_stable_tiebreak(undated_short)


def test_reranker_no_longer_imports_retrieval_to_break_ties() -> None:
    source = Path(reranker_module.__file__).read_text(encoding="utf-8")
    assert "from alicebot_api.vnext_retrieval import content_stable_tiebreak" not in source
