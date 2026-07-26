from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from alicebot_api.cli import capture
from alicebot_api.store import ContinuityStoreInvariantError


class _DemoResetCursor:
    def __init__(self, events: list[object]) -> None:
        self.events = events
        self.result_kind = ""

    def __enter__(self) -> _DemoResetCursor:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: object) -> None:
        normalized = " ".join(query.split())
        if normalized.startswith("SELECT id::text AS id FROM sources"):
            assert "deleted_at IS NULL" in normalized
            assert normalized.endswith("ORDER BY id ASC")
            self.result_kind = "sources"
        elif "SELECT id::text AS id FROM memories" in normalized:
            assert "deleted_at IS NULL" in normalized
            assert normalized.endswith("ORDER BY id ASC")
            self.result_kind = "memories"
        elif normalized.startswith("SELECT chunk.id::text AS id FROM source_chunks AS chunk"):
            assert normalized.endswith("ORDER BY chunk.id ASC")
            self.result_kind = "source_chunks"
        else:
            assert "reset_sources AS" in normalized
            assert "reset_memories AS" in normalized
            self.result_kind = "reset"
        self.events.append((f"query:{self.result_kind}", params))

    def fetchall(self) -> list[dict[str, str]]:
        if self.result_kind == "sources":
            return [{"id": "source-a"}, {"id": "source-b"}]
        if self.result_kind == "memories":
            return [{"id": "memory-a"}, {"id": "memory-b"}]
        if self.result_kind == "source_chunks":
            return [{"id": "chunk-shared"}, {"id": "chunk-source"}]
        raise AssertionError(f"unexpected fetchall for {self.result_kind}")

    def fetchone(self) -> dict[str, int]:
        assert self.result_kind == "reset"
        return {
            "sources": 2,
            "memories": 2,
            "artifacts": 1,
            "open_loops": 0,
            "projects": 1,
        }


class _DemoResetConnection:
    def __init__(self, events: list[object]) -> None:
        self.events = events

    def cursor(self) -> _DemoResetCursor:
        return _DemoResetCursor(self.events)


class _DemoResetStore:
    def __init__(self, *, missing_chunk_id: str | None = None) -> None:
        self.events: list[object] = []
        self.conn = _DemoResetConnection(self.events)
        self.missing_chunk_id = missing_chunk_id
        self.memories = {
            "memory-a": {
                "id": "memory-a",
                "metadata_json": {"source_chunk_id": "chunk-shared"},
            },
            "memory-b": {
                "id": "memory-b",
                "metadata_json": {
                    "occurrence_proposal": {"source_chunk_id": "chunk-memory"},
                },
            },
        }

    def lock_graph_mutation(self) -> None:
        self.events.append("lock_graph")

    def get_memory(self, memory_id: str) -> dict[str, object] | None:
        self.events.append(f"get_memory:{memory_id}")
        return self.memories.get(memory_id)

    def get_source_chunk_for_occurrence_accounting(
        self,
        source_chunk_id: str,
    ) -> dict[str, object] | None:
        self.events.append(f"get_chunk:{source_chunk_id}")
        if source_chunk_id == self.missing_chunk_id:
            return None
        return {"id": source_chunk_id}


def test_demo_reset_retires_occurrence_carriers_before_bulk_archive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _DemoResetStore()

    class _OccurrenceService:
        def __init__(self, actual_store: object) -> None:
            assert actual_store is store

        def retire_source_occurrence_state(
            self,
            source_id: str,
            *,
            stage: str,
            reason: str,
            _defer_occurrence_accounting: bool = False,
        ) -> list[str]:
            store.events.append(
                (
                    "retire_source",
                    source_id,
                    stage,
                    reason,
                    _defer_occurrence_accounting,
                )
            )
            return []

        def retire_memory_occurrence_state(
            self,
            memory: Mapping[str, object],
            *,
            stage: str,
            reason: str,
            preserve_claim: bool,
            _defer_occurrence_accounting: bool,
        ) -> list[str]:
            store.events.append(
                (
                    "retire_memory",
                    str(memory["id"]),
                    stage,
                    reason,
                    preserve_claim,
                    _defer_occurrence_accounting,
                )
            )
            return []

    def _invalidate(actual_store: object, **kwargs: Any) -> None:
        assert actual_store is store
        store.events.append(("invalidate", kwargs))

    def _append_event(actual_store: object, **kwargs: Any) -> None:
        assert actual_store is store
        store.events.append(("event", kwargs))

    monkeypatch.setattr(capture, "VNextMemoryCommitService", _OccurrenceService)
    monkeypatch.setattr(capture, "_invalidate_occurrence_accounting", _invalidate)
    monkeypatch.setattr(capture, "append_event", _append_event)

    result = capture._reset_vnext_demo_dataset(  # pyright: ignore[reportPrivateUsage]
        store,  # type: ignore[arg-type]
        dataset_id="phase6-demo",
    )

    labels = [event if isinstance(event, str) else event[0] for event in store.events]
    assert labels == [
        "lock_graph",
        "query:sources",
        "query:memories",
        "query:source_chunks",
        "get_memory:memory-a",
        "get_memory:memory-b",
        "get_chunk:chunk-memory",
        "get_chunk:chunk-shared",
        "get_chunk:chunk-source",
        "retire_source",
        "retire_source",
        "retire_memory",
        "retire_memory",
        "invalidate",
        "invalidate",
        "invalidate",
        "query:reset",
        "invalidate",
        "event",
    ]
    assert [event[1] for event in store.events if isinstance(event, tuple) and event[0] == "retire_source"] == [
        "source-a",
        "source-b",
    ]
    assert [event[1] for event in store.events if isinstance(event, tuple) and event[0] == "retire_memory"] == [
        "memory-a",
        "memory-b",
    ]
    assert all(event[4] is True for event in store.events if isinstance(event, tuple) and event[0] == "retire_source")
    assert all(event[4] is True for event in store.events if isinstance(event, tuple) and event[0] == "retire_memory")
    assert all(event[5] is True for event in store.events if isinstance(event, tuple) and event[0] == "retire_memory")
    invalidations = [event[1] for event in store.events if isinstance(event, tuple) and event[0] == "invalidate"]
    assert [invalidation.get("source_chunk_id") for invalidation in invalidations] == [
        "chunk-memory",
        "chunk-shared",
        "chunk-source",
        None,
    ]
    assert [invalidation.get("_defer_occurrence_coverage", False) for invalidation in invalidations] == [
        True,
        True,
        True,
        False,
    ]
    assert result == {
        "status": "reset",
        "dataset_id": "phase6-demo",
        "reset_counts": {
            "sources": 2,
            "memories": 2,
            "artifacts": 1,
            "open_loops": 0,
            "projects": 1,
        },
    }


def test_demo_reset_fails_closed_before_retirement_for_a_stale_chunk_reference() -> None:
    store = _DemoResetStore(missing_chunk_id="chunk-shared")

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="every referenced source chunk to remain current",
    ):
        capture._reset_vnext_demo_dataset(  # pyright: ignore[reportPrivateUsage]
            store,  # type: ignore[arg-type]
            dataset_id="phase6-demo",
        )

    labels = [event if isinstance(event, str) else event[0] for event in store.events]
    assert labels == [
        "lock_graph",
        "query:sources",
        "query:memories",
        "query:source_chunks",
        "get_memory:memory-a",
        "get_memory:memory-b",
        "get_chunk:chunk-memory",
        "get_chunk:chunk-shared",
    ]
