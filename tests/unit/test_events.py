from __future__ import annotations

import pytest

from alicebot_api.store import AppendOnlyViolation, ContinuityStore


def test_event_updates_are_rejected_by_contract():
    store = ContinuityStore(conn=None)  # type: ignore[arg-type]

    with pytest.raises(AppendOnlyViolation, match="append-only"):
        store.update_event("event-id", {"text": "mutated"})


def test_event_deletes_are_rejected_by_contract():
    store = ContinuityStore(conn=None)  # type: ignore[arg-type]

    with pytest.raises(AppendOnlyViolation, match="append-only"):
        store.delete_event("event-id")

