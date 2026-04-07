from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb
import pytest

from alicebot_api.store import ContinuityStore, ContinuityStoreInvariantError


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


def test_create_methods_return_cursor_rows_and_use_expected_parameters() -> None:
    user_id = uuid4()
    thread_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {"id": user_id, "email": "owner@example.com", "display_name": "Owner"},
            {"id": thread_id, "title": "Starter thread", "agent_profile_id": "assistant_default"},
            {"id": uuid4(), "thread_id": thread_id, "status": "active"},
        ]
    )
    store = ContinuityStore(RecordingConnection(cursor))

    user = store.create_user(user_id, "owner@example.com", "Owner")
    thread = store.create_thread("Starter thread")
    session = store.create_session(thread_id)

    assert user["id"] == user_id
    assert thread["id"] == thread_id
    assert session["thread_id"] == thread_id
    assert cursor.executed == [
        (
            """
                INSERT INTO users (id, email, display_name)
                VALUES (%s, %s, %s)
                RETURNING id, email, display_name, created_at
                """,
            (user_id, "owner@example.com", "Owner"),
        ),
        (
            """
                INSERT INTO threads (user_id, title, agent_profile_id)
                VALUES (app.current_user_id(), %s, %s)
                RETURNING id, user_id, title, agent_profile_id, created_at, updated_at
                """,
            ("Starter thread", "assistant_default"),
        ),
        (
            """
                INSERT INTO sessions (user_id, thread_id, status)
                VALUES (app.current_user_id(), %s, %s)
                RETURNING id, user_id, thread_id, status, started_at, ended_at, created_at
                """,
            (thread_id, "active"),
        ),
    ]


def test_append_event_locks_thread_and_serializes_payload() -> None:
    thread_id = uuid4()
    session_id = uuid4()
    payload = {"text": "hello"}
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": uuid4(),
                "thread_id": thread_id,
                "session_id": session_id,
                "sequence_no": 1,
                "kind": "message.user",
                "payload": payload,
            }
        ]
    )
    store = ContinuityStore(RecordingConnection(cursor))

    event = store.append_event(thread_id, session_id, "message.user", payload)

    assert event["sequence_no"] == 1
    assert cursor.executed[0] == (
        "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 0))",
        (str(thread_id),),
    )
    insert_query, insert_params = cursor.executed[1]
    assert "WITH next_sequence AS" in insert_query
    assert insert_params is not None
    assert insert_params[:4] == (thread_id, thread_id, session_id, "message.user")
    assert isinstance(insert_params[4], Jsonb)
    assert insert_params[4].obj == payload


def test_append_event_raises_clear_error_when_returning_row_is_missing() -> None:
    store = ContinuityStore(RecordingConnection(RecordingCursor(fetchone_results=[])))

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="append_event did not return a row",
    ):
        store.append_event(uuid4(), uuid4(), "message.user", {"text": "hello"})


def test_list_thread_events_returns_all_rows_in_order() -> None:
    thread_id = uuid4()
    events = [
        {"sequence_no": 1, "kind": "message.user"},
        {"sequence_no": 2, "kind": "message.assistant"},
    ]
    cursor = RecordingCursor(fetchone_results=[], fetchall_result=events)
    store = ContinuityStore(RecordingConnection(cursor))

    result = store.list_thread_events(thread_id)

    assert result == events
    assert cursor.executed == [
        (
            """
                SELECT id, user_id, thread_id, session_id, sequence_no, kind, payload, created_at
                FROM events
                WHERE thread_id = %s
                ORDER BY sequence_no ASC
                """,
            (thread_id,),
        ),
    ]


def test_create_user_raises_clear_error_when_returning_row_is_missing() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    with pytest.raises(
        ContinuityStoreInvariantError,
        match="create_user did not return a row",
    ):
        store.create_user(uuid4(), "owner@example.com")
