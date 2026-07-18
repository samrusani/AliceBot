from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

from alicebot_api.routers import legacy_gated as legacy_gated_router
from alicebot_api.config import Settings
from alicebot_api.calendar import (
    CalendarAccountAlreadyExistsError,
    CalendarAccountNotFoundError,
    CalendarCredentialInvalidError,
    CalendarCredentialNotFoundError,
    CalendarCredentialPersistenceError,
    CalendarCredentialValidationError,
    CalendarEventFetchError,
    CalendarEventListValidationError,
    CalendarEventNotFoundError,
    CalendarEventUnsupportedError,
)
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


def _settings() -> Settings:
    return Settings(
        database_url="postgresql://app",
        calendar_secret_manager_url="file:///tmp/test-calendar-secrets",
    )


def test_list_calendar_accounts_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        legacy_gated_router,
        "list_calendar_account_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = legacy_gated_router.list_calendar_accounts(user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
    }


def test_connect_calendar_account_endpoint_maps_duplicate_to_409(monkeypatch) -> None:
    user_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        legacy_gated_router,
        "create_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarAccountAlreadyExistsError("calendar account acct-001 is already connected")
        ),
    )

    response = legacy_gated_router.connect_calendar_account(
        legacy_gated_router.ConnectCalendarAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": {"code": "conflict", "message": "The request conflicts with the current resource state"}
    }


def test_connect_calendar_account_endpoint_maps_validation_and_persistence_errors(monkeypatch) -> None:
    user_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)

    monkeypatch.setattr(
        legacy_gated_router,
        "create_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialValidationError("calendar access token must be non-empty")
        ),
    )
    response = legacy_gated_router.connect_calendar_account(
        legacy_gated_router.ConnectCalendarAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )
    assert response.status_code == 400
    assert json.loads(response.body) == {"detail": {"code": "invalid_request", "message": "The request is invalid"}}

    monkeypatch.setattr(
        legacy_gated_router,
        "create_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialPersistenceError("calendar protected credentials could not be persisted")
        ),
    )
    response = legacy_gated_router.connect_calendar_account(
        legacy_gated_router.ConnectCalendarAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": {
            "code": "conflict",
            "message": "The request conflicts with the current resource state",
        }
    }


def test_get_calendar_account_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        legacy_gated_router,
        "get_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarAccountNotFoundError(f"calendar account {calendar_account_id} was not found")
        ),
    )

    response = legacy_gated_router.get_calendar_account(calendar_account_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": {"code": "not_found", "message": "The requested resource was not found"}
    }


def test_list_calendar_events_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        legacy_gated_router,
        "list_calendar_event_records",
        lambda *_args, **_kwargs: {
            "account": {
                "id": str(calendar_account_id),
                "provider": "google_calendar",
                "auth_kind": "oauth_access_token",
                "provider_account_id": "acct-001",
                "email_address": "owner@example.com",
                "display_name": "Owner",
                "scope": "https://www.googleapis.com/auth/calendar.readonly",
                "created_at": "2026-03-19T10:00:00+00:00",
                "updated_at": "2026-03-19T10:00:00+00:00",
            },
            "items": [
                {
                    "provider_event_id": "evt-001",
                    "status": "confirmed",
                    "summary": "Sprint Planning",
                    "start_time": "2026-03-20T09:00:00+00:00",
                    "end_time": "2026-03-20T09:30:00+00:00",
                    "html_link": "https://calendar.google.com/event?eid=evt-001",
                    "updated_at": "2026-03-19T10:00:00+00:00",
                }
            ],
            "summary": {
                "total_count": 1,
                "limit": 20,
                "order": ["start_time_asc", "provider_event_id_asc"],
                "time_min": None,
                "time_max": None,
            },
        },
    )

    response = legacy_gated_router.list_calendar_events(calendar_account_id, user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "account": {
            "id": str(calendar_account_id),
            "provider": "google_calendar",
            "auth_kind": "oauth_access_token",
            "provider_account_id": "acct-001",
            "email_address": "owner@example.com",
            "display_name": "Owner",
            "scope": "https://www.googleapis.com/auth/calendar.readonly",
            "created_at": "2026-03-19T10:00:00+00:00",
            "updated_at": "2026-03-19T10:00:00+00:00",
        },
        "items": [
            {
                "provider_event_id": "evt-001",
                "status": "confirmed",
                "summary": "Sprint Planning",
                "start_time": "2026-03-20T09:00:00+00:00",
                "end_time": "2026-03-20T09:30:00+00:00",
                "html_link": "https://calendar.google.com/event?eid=evt-001",
                "updated_at": "2026-03-19T10:00:00+00:00",
            }
        ],
        "summary": {
            "total_count": 1,
            "limit": 20,
            "order": ["start_time_asc", "provider_event_id_asc"],
            "time_min": None,
            "time_max": None,
        },
    }


def test_list_calendar_events_endpoint_maps_errors(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)

    monkeypatch.setattr(
        legacy_gated_router,
        "list_calendar_event_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarAccountNotFoundError(f"calendar account {calendar_account_id} was not found")
        ),
    )
    response = legacy_gated_router.list_calendar_events(calendar_account_id, user_id)
    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": {"code": "not_found", "message": "The requested resource was not found"}
    }

    monkeypatch.setattr(
        legacy_gated_router,
        "list_calendar_event_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialNotFoundError(f"calendar account {calendar_account_id} is missing protected credentials")
        ),
    )
    response = legacy_gated_router.list_calendar_events(calendar_account_id, user_id)
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": {
            "code": "conflict",
            "message": "The request conflicts with the current resource state",
        }
    }

    monkeypatch.setattr(
        legacy_gated_router,
        "list_calendar_event_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventListValidationError("calendar event time_min must be less than or equal to time_max")
        ),
    )
    response = legacy_gated_router.list_calendar_events(calendar_account_id, user_id)
    assert response.status_code == 400
    assert json.loads(response.body) == {"detail": {"code": "invalid_request", "message": "The request is invalid"}}

    monkeypatch.setattr(
        legacy_gated_router,
        "list_calendar_event_records",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventFetchError("calendar events could not be fetched")
        ),
    )
    response = legacy_gated_router.list_calendar_events(calendar_account_id, user_id)
    assert response.status_code == 502
    assert json.loads(response.body) == {
        "detail": {"code": "upstream_failure", "message": "An upstream service failed"}
    }


def test_ingest_calendar_event_endpoint_maps_workspace_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    task_workspace_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        legacy_gated_router,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TaskWorkspaceNotFoundError(f"task workspace {task_workspace_id} was not found")
        ),
    )

    response = legacy_gated_router.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        legacy_gated_router.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": {"code": "not_found", "message": "The requested resource was not found"}
    }


def test_ingest_calendar_event_endpoint_maps_upstream_errors(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    task_workspace_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(legacy_gated_router, "get_settings", lambda: settings)
    monkeypatch.setattr(legacy_gated_router, "user_connection", fake_user_connection)

    monkeypatch.setattr(
        legacy_gated_router,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventNotFoundError("calendar event evt-missing was not found")
        ),
    )
    response = legacy_gated_router.ingest_calendar_event(
        calendar_account_id,
        "evt-missing",
        legacy_gated_router.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": {"code": "not_found", "message": "The requested resource was not found"}
    }

    monkeypatch.setattr(
        legacy_gated_router,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventUnsupportedError("calendar event evt-unsupported is not supported for ingestion")
        ),
    )
    response = legacy_gated_router.ingest_calendar_event(
        calendar_account_id,
        "evt-unsupported",
        legacy_gated_router.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 400
    assert json.loads(response.body) == {"detail": {"code": "invalid_request", "message": "The request is invalid"}}

    monkeypatch.setattr(
        legacy_gated_router,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialNotFoundError(f"calendar account {calendar_account_id} is missing protected credentials")
        ),
    )
    response = legacy_gated_router.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        legacy_gated_router.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": {
            "code": "conflict",
            "message": "The request conflicts with the current resource state",
        }
    }

    monkeypatch.setattr(
        legacy_gated_router,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialInvalidError(f"calendar account {calendar_account_id} has invalid protected credentials")
        ),
    )
    response = legacy_gated_router.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        legacy_gated_router.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": {
            "code": "conflict",
            "message": "The request conflicts with the current resource state",
        }
    }

    monkeypatch.setattr(
        legacy_gated_router,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialPersistenceError(
                f"calendar account {calendar_account_id} protected credentials could not be persisted"
            )
        ),
    )
    response = legacy_gated_router.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        legacy_gated_router.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": {
            "code": "conflict",
            "message": "The request conflicts with the current resource state",
        }
    }

    monkeypatch.setattr(
        legacy_gated_router,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventFetchError("calendar event evt-001 could not be fetched")
        ),
    )
    response = legacy_gated_router.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        legacy_gated_router.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 502
    assert json.loads(response.body) == {
        "detail": {"code": "upstream_failure", "message": "An upstream service failed"}
    }
