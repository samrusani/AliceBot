"""Neutral deterministic ranking helpers shared by retrieval and reranking.

This module intentionally depends on neither pipeline. Keeping the stable
tie-break here prevents the retrieval -> reranker -> retrieval import cycle
while preserving one canonical ordering contract.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping

from alicebot_api.vnext_repositories import JsonObject
from alicebot_api.vnext_temporal_query import parse_event_datetime


TIE_BREAK_CONTENT_STABLE = "content_stable_v1"
CONTENT_EVENT_METADATA_KEYS = ("session_date", "event_date", "date")
_TIEBREAK_UNDATED = datetime(9999, 12, 31, tzinfo=UTC)
_TIEBREAK_EVENT_KEYS = ("valid_from", "source_created_at")
_TIEBREAK_TEXT_KEYS = ("canonical_text", "text", "summary", "title")


def content_stable_event_time(item: JsonObject) -> datetime | None:
    """Return a content-stamped event/session time without write-clock fallbacks."""
    for key in _TIEBREAK_EVENT_KEYS:
        parsed = parse_event_datetime(item.get(key))
        if parsed is not None:
            return parsed
    metadata = item.get("metadata_json")
    if isinstance(metadata, Mapping):
        for key in CONTENT_EVENT_METADATA_KEYS:
            parsed = parse_event_datetime(metadata.get(key))
            if parsed is not None:
                return parsed
    return None


def _content_text(item: JsonObject) -> str:
    for key in _TIEBREAK_TEXT_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _content_fingerprint(item: JsonObject) -> str:
    content_hash = item.get("content_hash")
    if isinstance(content_hash, str) and content_hash:
        return content_hash
    metadata = item.get("metadata_json")
    if isinstance(metadata, Mapping):
        capture_hash = metadata.get("capture_content_hash")
        if isinstance(capture_hash, str) and capture_hash:
            return f"{capture_hash}:{metadata.get('source_chunk_index')}"
    return ""


def content_stable_tiebreak(item: JsonObject) -> tuple[datetime, int, str, str]:
    """Content-stable ascending key for equal-score rows.

    Older content-stamped events sort first, then longer content, text, and a
    content-derived fingerprint. Callers append the row id for a total order.
    """
    text = _content_text(item)
    return (
        content_stable_event_time(item) or _TIEBREAK_UNDATED,
        -len(text),
        text,
        _content_fingerprint(item),
    )


__all__ = [
    "CONTENT_EVENT_METADATA_KEYS",
    "TIE_BREAK_CONTENT_STABLE",
    "content_stable_event_time",
    "content_stable_tiebreak",
]
