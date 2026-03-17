from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
from uuid import UUID, uuid4

import pytest

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.traces import (
    TraceNotFoundError,
    get_trace_record,
    list_trace_event_records,
    list_trace_records,
)


class TraceStoreStub:
    def __init__(self, *, current_user_id: UUID) -> None:
        self.current_user_id = current_user_id
        self.base_time = datetime(2026, 3, 17, 9, 0, tzinfo=UTC)
        self.traces: list[dict[str, object]] = []
        self.trace_events: list[dict[str, object]] = []

    def add_trace(
        self,
        *,
        trace_id: UUID,
        user_id: UUID,
        thread_id: UUID,
        kind: str,
        compiler_version: str,
        status: str,
        limits: dict[str, object],
        created_at: datetime | None = None,
    ) -> dict[str, object]:
        trace = {
            "id": trace_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "kind": kind,
            "compiler_version": compiler_version,
            "status": status,
            "limits": limits,
            "created_at": created_at or self.base_time,
        }
        self.traces.append(trace)
        return trace

    def add_trace_event(
        self,
        *,
        event_id: UUID,
        user_id: UUID,
        trace_id: UUID,
        sequence_no: int,
        kind: str,
        payload: dict[str, object],
        created_at: datetime | None = None,
    ) -> dict[str, object]:
        event = {
            "id": event_id,
            "user_id": user_id,
            "trace_id": trace_id,
            "sequence_no": sequence_no,
            "kind": kind,
            "payload": payload,
            "created_at": created_at or self.base_time,
        }
        self.trace_events.append(event)
        return event

    def list_trace_reviews(self) -> list[dict[str, object]]:
        visible_traces = [
            trace
            for trace in self.traces
            if trace["user_id"] == self.current_user_id
        ]
        rows = []
        for trace in visible_traces:
            rows.append(
                {
                    **trace,
                    "trace_event_count": len(
                        [
                            event
                            for event in self.trace_events
                            if event["user_id"] == self.current_user_id
                            and event["trace_id"] == trace["id"]
                        ]
                    ),
                }
            )
        return sorted(rows, key=lambda row: (row["created_at"], row["id"]), reverse=True)

    def get_trace_review_optional(self, trace_id: UUID) -> dict[str, object] | None:
        return next((trace for trace in self.list_trace_reviews() if trace["id"] == trace_id), None)

    def list_trace_events(self, trace_id: UUID) -> list[dict[str, object]]:
        visible_events = [
            event
            for event in self.trace_events
            if event["user_id"] == self.current_user_id and event["trace_id"] == trace_id
        ]
        return sorted(visible_events, key=lambda event: (event["sequence_no"], event["id"]))


def test_trace_review_records_preserve_deterministic_order_isolation_and_shape() -> None:
    owner_id = uuid4()
    intruder_id = uuid4()
    first_trace_id = UUID("00000000-0000-4000-8000-000000000001")
    second_trace_id = UUID("00000000-0000-4000-8000-000000000002")
    hidden_trace_id = UUID("00000000-0000-4000-8000-000000000003")
    owner_thread_id = uuid4()
    hidden_thread_id = uuid4()
    store = TraceStoreStub(current_user_id=owner_id)

    store.add_trace(
        trace_id=first_trace_id,
        user_id=owner_id,
        thread_id=owner_thread_id,
        kind="context.compile",
        compiler_version="continuity_v0",
        status="completed",
        limits={"max_sessions": 3, "max_events": 8},
    )
    store.add_trace(
        trace_id=second_trace_id,
        user_id=owner_id,
        thread_id=owner_thread_id,
        kind="tool.proxy.execute",
        compiler_version="response_generation_v0",
        status="completed",
        limits={"max_sessions": 1, "max_events": 2},
    )
    store.add_trace(
        trace_id=hidden_trace_id,
        user_id=intruder_id,
        thread_id=hidden_thread_id,
        kind="approval.request",
        compiler_version="approval_request_v0",
        status="completed",
        limits={"max_sessions": 1, "max_events": 1},
    )

    store.add_trace_event(
        event_id=UUID("10000000-0000-4000-8000-000000000001"),
        user_id=owner_id,
        trace_id=second_trace_id,
        sequence_no=2,
        kind="tool.proxy.execute.summary",
        payload={"approval_id": "approval-2"},
    )
    store.add_trace_event(
        event_id=UUID("10000000-0000-4000-8000-000000000002"),
        user_id=owner_id,
        trace_id=second_trace_id,
        sequence_no=1,
        kind="tool.proxy.execute.request",
        payload={"approval_id": "approval-2"},
    )
    store.add_trace_event(
        event_id=UUID("10000000-0000-4000-8000-000000000003"),
        user_id=owner_id,
        trace_id=first_trace_id,
        sequence_no=1,
        kind="context.summary",
        payload={"thread_id": str(owner_thread_id)},
    )
    store.add_trace_event(
        event_id=UUID("10000000-0000-4000-8000-000000000004"),
        user_id=intruder_id,
        trace_id=hidden_trace_id,
        sequence_no=1,
        kind="approval.request.summary",
        payload={"approval_id": "approval-hidden"},
    )

    listed = list_trace_records(
        store,  # type: ignore[arg-type]
        user_id=owner_id,
    )
    detail = get_trace_record(
        store,  # type: ignore[arg-type]
        user_id=owner_id,
        trace_id=second_trace_id,
    )
    events = list_trace_event_records(
        store,  # type: ignore[arg-type]
        user_id=owner_id,
        trace_id=second_trace_id,
    )

    assert listed == {
        "items": [
            {
                "id": str(second_trace_id),
                "thread_id": str(owner_thread_id),
                "kind": "tool.proxy.execute",
                "compiler_version": "response_generation_v0",
                "status": "completed",
                "created_at": store.base_time.isoformat(),
                "trace_event_count": 2,
            },
            {
                "id": str(first_trace_id),
                "thread_id": str(owner_thread_id),
                "kind": "context.compile",
                "compiler_version": "continuity_v0",
                "status": "completed",
                "created_at": store.base_time.isoformat(),
                "trace_event_count": 1,
            },
        ],
        "summary": {
            "total_count": 2,
            "order": ["created_at_desc", "id_desc"],
        },
    }
    assert detail == {
        "trace": {
            "id": str(second_trace_id),
            "thread_id": str(owner_thread_id),
            "kind": "tool.proxy.execute",
            "compiler_version": "response_generation_v0",
            "status": "completed",
            "limits": {"max_sessions": 1, "max_events": 2},
            "created_at": store.base_time.isoformat(),
            "trace_event_count": 2,
        }
    }
    assert events == {
        "items": [
            {
                "id": "10000000-0000-4000-8000-000000000002",
                "trace_id": str(second_trace_id),
                "sequence_no": 1,
                "kind": "tool.proxy.execute.request",
                "payload": {"approval_id": "approval-2"},
                "created_at": store.base_time.isoformat(),
            },
            {
                "id": "10000000-0000-4000-8000-000000000001",
                "trace_id": str(second_trace_id),
                "sequence_no": 2,
                "kind": "tool.proxy.execute.summary",
                "payload": {"approval_id": "approval-2"},
                "created_at": store.base_time.isoformat(),
            },
        ],
        "summary": {
            "trace_id": str(second_trace_id),
            "total_count": 2,
            "order": ["sequence_no_asc", "id_asc"],
        },
    }


def test_trace_review_records_raise_not_found_for_invisible_traces() -> None:
    owner_id = uuid4()
    intruder_id = uuid4()
    hidden_trace_id = uuid4()
    store = TraceStoreStub(current_user_id=intruder_id)
    store.add_trace(
        trace_id=hidden_trace_id,
        user_id=owner_id,
        thread_id=uuid4(),
        kind="context.compile",
        compiler_version="continuity_v0",
        status="completed",
        limits={"max_sessions": 3},
    )
    store.add_trace_event(
        event_id=uuid4(),
        user_id=owner_id,
        trace_id=hidden_trace_id,
        sequence_no=1,
        kind="context.summary",
        payload={"scope": "owner-only"},
    )

    listed = list_trace_records(
        store,  # type: ignore[arg-type]
        user_id=intruder_id,
    )

    assert listed == {
        "items": [],
        "summary": {
            "total_count": 0,
            "order": ["created_at_desc", "id_desc"],
        },
    }
    with pytest.raises(TraceNotFoundError, match=f"trace {hidden_trace_id} was not found"):
        get_trace_record(
            store,  # type: ignore[arg-type]
            user_id=intruder_id,
            trace_id=hidden_trace_id,
        )
    with pytest.raises(TraceNotFoundError, match=f"trace {hidden_trace_id} was not found"):
        list_trace_event_records(
            store,  # type: ignore[arg-type]
            user_id=intruder_id,
            trace_id=hidden_trace_id,
        )


def test_list_traces_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_trace_records(store, *, user_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        return {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_desc", "id_desc"]},
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_trace_records", fake_list_trace_records)

    response = main_module.list_traces(user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_desc", "id_desc"]},
    }
    assert captured == {
        "database_url": "postgresql://app",
        "current_user_id": user_id,
        "store_type": "ContinuityStore",
        "user_id": user_id,
    }


def test_get_trace_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    trace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_trace_record(*_args, **_kwargs):
        raise TraceNotFoundError(f"trace {trace_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_trace_record", fake_get_trace_record)

    response = main_module.get_trace(trace_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"trace {trace_id} was not found"}


def test_list_trace_events_endpoint_returns_payload_and_maps_not_found(monkeypatch) -> None:
    user_id = uuid4()
    trace_id = uuid4()
    settings = Settings(database_url="postgresql://app")
    captured: dict[str, object] = {}

    @contextmanager
    def fake_user_connection(database_url: str, current_user_id):
        captured["database_url"] = database_url
        captured["current_user_id"] = current_user_id
        yield object()

    def fake_list_trace_event_records(store, *, user_id, trace_id):
        captured["store_type"] = type(store).__name__
        captured["user_id"] = user_id
        captured["trace_id"] = trace_id
        if captured.get("fail"):
            raise TraceNotFoundError(f"trace {trace_id} was not found")
        return {
            "items": [],
            "summary": {
                "trace_id": str(trace_id),
                "total_count": 0,
                "order": ["sequence_no_asc", "id_asc"],
            },
        }

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "list_trace_event_records", fake_list_trace_event_records)

    success_response = main_module.list_trace_events(trace_id, user_id)
    captured["fail"] = True
    not_found_response = main_module.list_trace_events(trace_id, user_id)

    assert success_response.status_code == 200
    assert json.loads(success_response.body) == {
        "items": [],
        "summary": {
            "trace_id": str(trace_id),
            "total_count": 0,
            "order": ["sequence_no_asc", "id_asc"],
        },
    }
    assert not_found_response.status_code == 404
    assert json.loads(not_found_response.body) == {"detail": f"trace {trace_id} was not found"}
    assert captured["database_url"] == "postgresql://app"
    assert captured["current_user_id"] == user_id
    assert captured["store_type"] == "ContinuityStore"
    assert captured["user_id"] == user_id
    assert captured["trace_id"] == trace_id
