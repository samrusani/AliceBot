from __future__ import annotations

from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb
import pytest

from alicebot_api.store import ContinuityStore, ContinuityStoreInvariantError


class RecordingCursor:
    def __init__(
        self, fetchone_results: list[dict[str, Any]], fetchall_result: list[dict[str, Any]] | None = None
    ) -> None:
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


def test_append_event_if_tail_compares_under_lock_before_insert() -> None:
    thread_id = uuid4()
    session_id = uuid4()
    user_event_id = uuid4()
    assistant_event_id = uuid4()
    payload = {"text": "answer"}
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": user_event_id,
                "thread_id": thread_id,
                "sequence_no": 7,
                "kind": "message.user",
                "payload": {"text": "question"},
            },
            {
                "id": assistant_event_id,
                "thread_id": thread_id,
                "session_id": session_id,
                "sequence_no": 8,
                "kind": "message.assistant",
                "payload": payload,
            },
        ]
    )
    store = ContinuityStore(RecordingConnection(cursor))

    event = store.append_event_if_tail(
        thread_id,
        session_id,
        "message.assistant",
        payload,
        expected_event_id=user_event_id,
        expected_sequence_no=7,
    )

    assert event is not None
    assert event["id"] == assistant_event_id
    assert cursor.executed[0] == (
        "SELECT pg_advisory_xact_lock(hashtextextended(%s::text, 0))",
        (str(thread_id),),
    )
    assert "ORDER BY sequence_no DESC" in cursor.executed[1][0]
    insert_query, insert_params = cursor.executed[2]
    assert "WITH next_sequence AS" in insert_query
    assert insert_params is not None
    assert insert_params[:4] == (thread_id, thread_id, session_id, "message.assistant")
    assert isinstance(insert_params[4], Jsonb)
    assert insert_params[4].obj == payload


def test_append_event_if_tail_rejects_a_superseded_turn_without_insert() -> None:
    thread_id = uuid4()
    prepared_event_id = uuid4()
    newer_event_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": newer_event_id,
                "thread_id": thread_id,
                "sequence_no": 8,
                "kind": "message.user",
                "payload": {"text": "newer question"},
            }
        ]
    )
    store = ContinuityStore(RecordingConnection(cursor))

    event = store.append_event_if_tail(
        thread_id,
        None,
        "message.assistant",
        {"text": "stale answer"},
        expected_event_id=prepared_event_id,
        expected_sequence_no=7,
    )

    assert event is None
    assert len(cursor.executed) == 2
    assert "pg_advisory_xact_lock" in cursor.executed[0][0]
    assert "ORDER BY sequence_no DESC" in cursor.executed[1][0]


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


def test_update_model_provider_advances_configuration_revision() -> None:
    provider_id = uuid4()
    workspace_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": provider_id,
                "workspace_id": workspace_id,
                "config_revision": 2,
                "config_fingerprint_sha256": "b" * 64,
            }
        ]
    )
    store = ContinuityStore(RecordingConnection(cursor))

    updated = store.update_model_provider(
        provider_id=provider_id,
        workspace_id=workspace_id,
        provider_key="openai_compatible",
        model_provider="openai_responses",
        display_name="Provider",
        base_url="https://provider.example/v1",
        api_key="",
        auth_mode="bearer",
        default_model="gpt-5-mini",
        status="active",
        model_list_path="/models",
        healthcheck_path="/models",
        invoke_path="/responses",
        azure_api_version="",
        azure_auth_secret_ref="",
        metadata={},
        config_fingerprint_sha256="b" * 64,
        expected_config_revision=1,
        expected_config_fingerprint_sha256="a" * 64,
    )

    sql, params = cursor.executed[0]
    assert updated["config_revision"] == 2
    assert "config_revision = config_revision + 1" in sql
    assert "config_fingerprint_sha256 = %s" in sql
    assert "AND config_revision = %s" in sql
    assert "AND config_fingerprint_sha256 = %s" in sql
    assert params is not None
    assert params[-5:] == (
        "b" * 64,
        provider_id,
        workspace_id,
        1,
        "a" * 64,
    )


def test_provider_capability_upsert_is_configuration_fenced() -> None:
    provider_id = uuid4()
    workspace_id = uuid4()
    user_id = uuid4()
    capability_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": capability_id,
                "workspace_id": workspace_id,
                "provider_id": provider_id,
                "provider_config_revision": 7,
                "provider_config_fingerprint_sha256": "c" * 64,
            }
        ]
    )
    store = ContinuityStore(RecordingConnection(cursor))

    capability = store.upsert_provider_capability_if_current(
        workspace_id=workspace_id,
        provider_id=provider_id,
        discovered_by_user_account_id=user_id,
        adapter_key="openai_compatible",
        discovery_status="ready",
        capability_snapshot={"models": ["gpt-5-mini"]},
        discovery_error=None,
        expected_config_revision=7,
        expected_config_fingerprint_sha256="c" * 64,
    )

    sql, params = cursor.executed[0]
    assert capability is not None
    assert capability["id"] == capability_id
    assert "WITH current_provider AS" in sql
    assert "config_revision = %s" in sql
    assert "config_fingerprint_sha256 = %s" in sql
    assert "FOR SHARE" in sql
    assert params is not None
    assert params[:4] == (provider_id, workspace_id, 7, "c" * 64)
    assert isinstance(params[7], Jsonb)

    stale_store = ContinuityStore(RecordingConnection(RecordingCursor(fetchone_results=[])))
    assert (
        stale_store.upsert_provider_capability_if_current(
            workspace_id=workspace_id,
            provider_id=provider_id,
            discovered_by_user_account_id=user_id,
            adapter_key="openai_compatible",
            discovery_status="ready",
            capability_snapshot={},
            discovery_error=None,
            expected_config_revision=6,
            expected_config_fingerprint_sha256="d" * 64,
        )
        is None
    )


def test_provider_capability_read_rejects_stale_configuration_rows() -> None:
    provider_id = uuid4()
    workspace_id = uuid4()
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    capability = store.get_provider_capability_for_provider_optional(
        provider_id=provider_id,
        workspace_id=workspace_id,
    )

    assert capability is None
    sql, params = cursor.executed[0]
    assert "JOIN model_providers AS provider" in sql
    assert "provider.config_revision = capability.provider_config_revision" in sql
    assert "provider.config_fingerprint_sha256 = capability.provider_config_fingerprint_sha256" in sql
    assert params == (provider_id, workspace_id)


def test_provider_secret_reference_check_covers_both_reference_columns() -> None:
    workspace_id = uuid4()
    reference = "provider_secret_ref:workspaces/example/secret.json"
    cursor = RecordingCursor(fetchone_results=[{"in_use": True}])
    store = ContinuityStore(RecordingConnection(cursor))

    assert store.is_provider_secret_reference_in_use(
        workspace_id=workspace_id,
        encoded_reference=reference,
    )
    sql, params = cursor.executed[0]
    assert "api_key = %s OR azure_auth_secret_ref = %s" in sql
    assert params == (workspace_id, reference, reference)
