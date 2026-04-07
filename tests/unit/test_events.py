from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import json
from uuid import UUID, uuid4

import pytest

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.store import AppendOnlyViolation, ContinuityStore


class ContinuityApiStoreStub:
    def __init__(self, *, current_user_id: UUID) -> None:
        self.current_user_id = current_user_id
        self.base_time = datetime(2026, 3, 17, 9, 0, tzinfo=UTC)
        self.agent_profiles = [
            {
                "id": "assistant_default",
                "name": "Assistant Default",
                "description": "Default profile for tests",
                "model_provider": None,
                "model_name": None,
            }
        ]
        self.threads: list[dict[str, object]] = []
        self.sessions: list[dict[str, object]] = []
        self.events: list[dict[str, object]] = []

    def add_thread(
        self,
        *,
        thread_id: UUID,
        user_id: UUID,
        title: str,
        agent_profile_id: str = "assistant_default",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> dict[str, object]:
        thread = {
            "id": thread_id,
            "user_id": user_id,
            "title": title,
            "agent_profile_id": agent_profile_id,
            "created_at": created_at or self.base_time,
            "updated_at": updated_at or created_at or self.base_time,
        }
        self.threads.append(thread)
        return thread

    def add_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        thread_id: UUID,
        status: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, object]:
        session = {
            "id": session_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "status": status,
            "started_at": started_at or self.base_time,
            "ended_at": ended_at,
            "created_at": created_at or started_at or self.base_time,
        }
        self.sessions.append(session)
        return session

    def add_event(
        self,
        *,
        event_id: UUID,
        user_id: UUID,
        thread_id: UUID,
        session_id: UUID | None,
        sequence_no: int,
        kind: str,
        payload: dict[str, object],
        created_at: datetime | None = None,
    ) -> dict[str, object]:
        event = {
            "id": event_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "session_id": session_id,
            "sequence_no": sequence_no,
            "kind": kind,
            "payload": payload,
            "created_at": created_at or self.base_time,
        }
        self.events.append(event)
        return event

    def create_thread(self, title: str, agent_profile_id: str = "assistant_default") -> dict[str, object]:
        created_at = self.base_time + timedelta(minutes=len(self.threads))
        return self.add_thread(
            thread_id=uuid4(),
            user_id=self.current_user_id,
            title=title,
            agent_profile_id=agent_profile_id,
            created_at=created_at,
            updated_at=created_at,
        )

    def list_threads(self) -> list[dict[str, object]]:
        visible_threads = [
            thread for thread in self.threads if thread["user_id"] == self.current_user_id
        ]
        return sorted(visible_threads, key=lambda thread: (thread["created_at"], thread["id"]), reverse=True)

    def get_thread_optional(self, thread_id: UUID) -> dict[str, object] | None:
        return next((thread for thread in self.list_threads() if thread["id"] == thread_id), None)

    def list_agent_profiles(self) -> list[dict[str, object]]:
        return list(self.agent_profiles)

    def get_agent_profile_optional(self, profile_id: str) -> dict[str, object] | None:
        return next(
            (profile for profile in self.agent_profiles if profile["id"] == profile_id),
            None,
        )

    def list_thread_sessions(self, thread_id: UUID) -> list[dict[str, object]]:
        visible_sessions = [
            session
            for session in self.sessions
            if session["user_id"] == self.current_user_id and session["thread_id"] == thread_id
        ]
        return sorted(
            visible_sessions,
            key=lambda session: (session["started_at"], session["created_at"], session["id"]),
        )

    def list_thread_events(self, thread_id: UUID) -> list[dict[str, object]]:
        visible_events = [
            event
            for event in self.events
            if event["user_id"] == self.current_user_id and event["thread_id"] == thread_id
        ]
        return sorted(visible_events, key=lambda event: (event["sequence_no"], event["id"]))


def install_continuity_api_stubs(
    monkeypatch: pytest.MonkeyPatch,
    stores: dict[UUID, ContinuityApiStoreStub],
) -> None:
    settings = Settings(database_url="postgresql://app")

    class FakeConnection:
        def __init__(self, current_user_id: UUID) -> None:
            self.current_user_id = current_user_id

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id: UUID):
        assert database_url == settings.database_url
        yield FakeConnection(current_user_id)

    def fake_store_factory(conn: FakeConnection) -> ContinuityApiStoreStub:
        return stores.setdefault(
            conn.current_user_id,
            ContinuityApiStoreStub(current_user_id=conn.current_user_id),
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "ContinuityStore", fake_store_factory)


def test_event_updates_are_rejected_by_contract():
    store = ContinuityStore(conn=None)  # type: ignore[arg-type]

    with pytest.raises(AppendOnlyViolation, match="append-only"):
        store.update_event("event-id", {"text": "mutated"})


def test_event_deletes_are_rejected_by_contract():
    store = ContinuityStore(conn=None)  # type: ignore[arg-type]

    with pytest.raises(AppendOnlyViolation, match="append-only"):
        store.delete_event("event-id")


def test_thread_create_endpoint_persists_one_visible_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    owner_id = uuid4()
    stores: dict[UUID, ContinuityApiStoreStub] = {}
    install_continuity_api_stubs(monkeypatch, stores)

    response = main_module.create_thread(
        main_module.CreateThreadRequest(user_id=owner_id, title="Operator Inbox")
    )

    assert response.status_code == 201
    assert json.loads(response.body) == {
        "thread": {
            "id": json.loads(response.body)["thread"]["id"],
            "title": "Operator Inbox",
            "agent_profile_id": "assistant_default",
            "created_at": "2026-03-17T09:00:00+00:00",
            "updated_at": "2026-03-17T09:00:00+00:00",
        }
    }
    assert [thread["title"] for thread in stores[owner_id].threads] == ["Operator Inbox"]


def test_thread_review_endpoints_preserve_shape_order_and_user_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = uuid4()
    intruder_id = uuid4()
    owner_store = ContinuityApiStoreStub(current_user_id=owner_id)
    intruder_store = ContinuityApiStoreStub(current_user_id=intruder_id)
    stores = {
        owner_id: owner_store,
        intruder_id: intruder_store,
    }
    install_continuity_api_stubs(monkeypatch, stores)

    shared_created_at = owner_store.base_time
    first_thread = owner_store.add_thread(
        thread_id=UUID("00000000-0000-4000-8000-000000000001"),
        user_id=owner_id,
        title="Alpha thread",
        created_at=shared_created_at,
        updated_at=shared_created_at,
    )
    second_thread = owner_store.add_thread(
        thread_id=UUID("00000000-0000-4000-8000-000000000002"),
        user_id=owner_id,
        title="Beta thread",
        created_at=shared_created_at,
        updated_at=shared_created_at,
    )
    first_session = owner_store.add_session(
        session_id=UUID("10000000-0000-4000-8000-000000000001"),
        user_id=owner_id,
        thread_id=second_thread["id"],
        status="completed",
        started_at=shared_created_at,
        ended_at=shared_created_at + timedelta(minutes=5),
        created_at=shared_created_at,
    )
    second_session = owner_store.add_session(
        session_id=UUID("10000000-0000-4000-8000-000000000002"),
        user_id=owner_id,
        thread_id=second_thread["id"],
        status="active",
        started_at=shared_created_at + timedelta(hours=1),
        ended_at=None,
        created_at=shared_created_at + timedelta(hours=1),
    )
    first_event = owner_store.add_event(
        event_id=UUID("20000000-0000-4000-8000-000000000001"),
        user_id=owner_id,
        thread_id=second_thread["id"],
        session_id=second_session["id"],
        sequence_no=2,
        kind="message.assistant",
        payload={"text": "Hello back"},
        created_at=shared_created_at + timedelta(hours=1, minutes=1),
    )
    second_event = owner_store.add_event(
        event_id=UUID("20000000-0000-4000-8000-000000000002"),
        user_id=owner_id,
        thread_id=second_thread["id"],
        session_id=second_session["id"],
        sequence_no=1,
        kind="message.user",
        payload={"text": "Hello"},
        created_at=shared_created_at + timedelta(hours=1),
    )

    list_response = main_module.list_threads(owner_id)
    detail_response = main_module.get_thread(second_thread["id"], owner_id)
    sessions_response = main_module.list_thread_sessions(second_thread["id"], owner_id)
    events_response = main_module.list_thread_events(second_thread["id"], owner_id)
    intruder_list_response = main_module.list_threads(intruder_id)
    intruder_detail_response = main_module.get_thread(second_thread["id"], intruder_id)
    intruder_sessions_response = main_module.list_thread_sessions(second_thread["id"], intruder_id)
    intruder_events_response = main_module.list_thread_events(second_thread["id"], intruder_id)

    assert json.loads(list_response.body) == {
        "items": [
            {
                "id": str(second_thread["id"]),
                "title": "Beta thread",
                "agent_profile_id": "assistant_default",
                "created_at": shared_created_at.isoformat(),
                "updated_at": shared_created_at.isoformat(),
            },
            {
                "id": str(first_thread["id"]),
                "title": "Alpha thread",
                "agent_profile_id": "assistant_default",
                "created_at": shared_created_at.isoformat(),
                "updated_at": shared_created_at.isoformat(),
            },
        ],
        "summary": {
            "total_count": 2,
            "order": ["created_at_desc", "id_desc"],
        },
    }
    assert json.loads(detail_response.body) == {
        "thread": {
            "id": str(second_thread["id"]),
            "title": "Beta thread",
            "agent_profile_id": "assistant_default",
            "created_at": shared_created_at.isoformat(),
            "updated_at": shared_created_at.isoformat(),
        }
    }
    assert json.loads(sessions_response.body) == {
        "items": [
            {
                "id": str(first_session["id"]),
                "thread_id": str(second_thread["id"]),
                "status": "completed",
                "started_at": shared_created_at.isoformat(),
                "ended_at": (shared_created_at + timedelta(minutes=5)).isoformat(),
                "created_at": shared_created_at.isoformat(),
            },
            {
                "id": str(second_session["id"]),
                "thread_id": str(second_thread["id"]),
                "status": "active",
                "started_at": (shared_created_at + timedelta(hours=1)).isoformat(),
                "ended_at": None,
                "created_at": (shared_created_at + timedelta(hours=1)).isoformat(),
            },
        ],
        "summary": {
            "thread_id": str(second_thread["id"]),
            "total_count": 2,
            "order": ["started_at_asc", "created_at_asc", "id_asc"],
        },
    }
    assert json.loads(events_response.body) == {
        "items": [
            {
                "id": str(second_event["id"]),
                "thread_id": str(second_thread["id"]),
                "session_id": str(second_session["id"]),
                "sequence_no": 1,
                "kind": "message.user",
                "payload": {"text": "Hello"},
                "created_at": (shared_created_at + timedelta(hours=1)).isoformat(),
            },
            {
                "id": str(first_event["id"]),
                "thread_id": str(second_thread["id"]),
                "session_id": str(second_session["id"]),
                "sequence_no": 2,
                "kind": "message.assistant",
                "payload": {"text": "Hello back"},
                "created_at": (shared_created_at + timedelta(hours=1, minutes=1)).isoformat(),
            },
        ],
        "summary": {
            "thread_id": str(second_thread["id"]),
            "total_count": 2,
            "order": ["sequence_no_asc"],
        },
    }
    assert json.loads(intruder_list_response.body) == {
        "items": [],
        "summary": {
            "total_count": 0,
            "order": ["created_at_desc", "id_desc"],
        },
    }
    assert intruder_detail_response.status_code == 404
    assert intruder_sessions_response.status_code == 404
    assert intruder_events_response.status_code == 404
    assert json.loads(intruder_detail_response.body) == {
        "detail": f"thread {second_thread['id']} was not found"
    }
    assert json.loads(intruder_sessions_response.body) == {
        "detail": f"thread {second_thread['id']} was not found"
    }
    assert json.loads(intruder_events_response.body) == {
        "detail": f"thread {second_thread['id']} was not found"
    }
