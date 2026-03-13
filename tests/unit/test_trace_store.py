from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb
import pytest

from alicebot_api.store import AppendOnlyViolation, ContinuityStore, ContinuityStoreInvariantError


class RecordingCursor:
    def __init__(self, fetchone_results: list[dict[str, Any]], fetchall_result: list[dict[str, Any]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_result = fetchall_result or []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        return self.fetchall_result


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def test_trace_methods_use_expected_queries_and_payload_serialization() -> None:
    user_id = uuid4()
    thread_id = uuid4()
    trace_id = uuid4()
    payload = {"reason": "within_event_limit"}
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": user_id, "email": "owner@example.com", "display_name": "Owner"},
            {"id": thread_id, "user_id": user_id, "title": "Thread"},
            {"id": trace_id, "user_id": user_id, "thread_id": thread_id, "kind": "context.compile"},
            {
                "id": uuid4(),
                "user_id": user_id,
                "trace_id": trace_id,
                "sequence_no": 1,
                "kind": "context.include",
                "payload": payload,
            },
        ],
        fetchall_result=[
            {"sequence_no": 1, "kind": "context.include", "payload": payload},
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    user = store.get_user(user_id)
    thread = store.get_thread(thread_id)
    trace = store.create_trace(
        user_id=user_id,
        thread_id=thread_id,
        kind="context.compile",
        compiler_version="continuity_v0",
        status="completed",
        limits={"max_sessions": 3, "max_events": 8},
    )
    trace_event = store.append_trace_event(
        trace_id=trace_id,
        sequence_no=1,
        kind="context.include",
        payload=payload,
    )
    listed_trace_events = store.list_trace_events(trace_id)

    assert user["id"] == user_id
    assert thread["id"] == thread_id
    assert trace["id"] == trace_id
    assert trace_event["sequence_no"] == 1
    assert listed_trace_events == [{"sequence_no": 1, "kind": "context.include", "payload": payload}]

    assert cursor.executed[0] == (
        """
                SELECT id, email, display_name, created_at
                FROM users
                WHERE id = %s
                """,
        (user_id,),
    )
    assert cursor.executed[1] == (
        """
                SELECT id, user_id, title, created_at, updated_at
                FROM threads
                WHERE id = %s
                """,
        (thread_id,),
    )
    create_trace_query, create_trace_params = cursor.executed[2]
    assert "INSERT INTO traces" in create_trace_query
    assert create_trace_params is not None
    assert create_trace_params[:5] == (
        user_id,
        thread_id,
        "context.compile",
        "continuity_v0",
        "completed",
    )
    assert isinstance(create_trace_params[5], Jsonb)
    assert create_trace_params[5].obj == {"max_sessions": 3, "max_events": 8}

    append_trace_query, append_trace_params = cursor.executed[3]
    assert "INSERT INTO trace_events" in append_trace_query
    assert append_trace_params is not None
    assert append_trace_params[:3] == (trace_id, 1, "context.include")
    assert isinstance(append_trace_params[3], Jsonb)
    assert append_trace_params[3].obj == payload


def test_trace_event_updates_and_deletes_are_rejected_by_contract() -> None:
    store = ContinuityStore(conn=None)  # type: ignore[arg-type]

    with pytest.raises(AppendOnlyViolation, match="append-only"):
        store.update_trace_event("trace-event-id", {"text": "mutated"})

    with pytest.raises(AppendOnlyViolation, match="append-only"):
        store.delete_trace_event("trace-event-id")


def test_get_trace_raises_clear_error_when_missing() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="get_trace did not return a row",
    ):
        store.get_trace(uuid4())
