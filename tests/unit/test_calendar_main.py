from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.calendar import (
    CalendarAccountAlreadyExistsError,
    CalendarAccountNotFoundError,
    CalendarCredentialInvalidError,
    CalendarCredentialNotFoundError,
    CalendarCredentialPersistenceError,
    CalendarCredentialValidationError,
    CalendarEventFetchError,
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

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_calendar_account_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = main_module.list_calendar_accounts(user_id)

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

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "create_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarAccountAlreadyExistsError("calendar account acct-001 is already connected")
        ),
    )

    response = main_module.connect_calendar_account(
        main_module.ConnectCalendarAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": "calendar account acct-001 is already connected"
    }


def test_connect_calendar_account_endpoint_maps_validation_and_persistence_errors(monkeypatch) -> None:
    user_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)

    monkeypatch.setattr(
        main_module,
        "create_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialValidationError("calendar access token must be non-empty")
        ),
    )
    response = main_module.connect_calendar_account(
        main_module.ConnectCalendarAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )
    assert response.status_code == 400
    assert json.loads(response.body) == {"detail": "calendar access token must be non-empty"}

    monkeypatch.setattr(
        main_module,
        "create_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialPersistenceError("calendar protected credentials could not be persisted")
        ),
    )
    response = main_module.connect_calendar_account(
        main_module.ConnectCalendarAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": "calendar protected credentials could not be persisted"
    }


def test_get_calendar_account_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "get_calendar_account_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarAccountNotFoundError(f"calendar account {calendar_account_id} was not found")
        ),
    )

    response = main_module.get_calendar_account(calendar_account_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"calendar account {calendar_account_id} was not found"
    }


def test_ingest_calendar_event_endpoint_maps_workspace_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    task_workspace_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TaskWorkspaceNotFoundError(f"task workspace {task_workspace_id} was not found")
        ),
    )

    response = main_module.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        main_module.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"task workspace {task_workspace_id} was not found"
    }


def test_ingest_calendar_event_endpoint_maps_upstream_errors(monkeypatch) -> None:
    user_id = uuid4()
    calendar_account_id = uuid4()
    task_workspace_id = uuid4()
    settings = _settings()

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)

    monkeypatch.setattr(
        main_module,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventNotFoundError("calendar event evt-missing was not found")
        ),
    )
    response = main_module.ingest_calendar_event(
        calendar_account_id,
        "evt-missing",
        main_module.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "calendar event evt-missing was not found"}

    monkeypatch.setattr(
        main_module,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventUnsupportedError("calendar event evt-unsupported is not supported for ingestion")
        ),
    )
    response = main_module.ingest_calendar_event(
        calendar_account_id,
        "evt-unsupported",
        main_module.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "calendar event evt-unsupported is not supported for ingestion"
    }

    monkeypatch.setattr(
        main_module,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialNotFoundError(
                f"calendar account {calendar_account_id} is missing protected credentials"
            )
        ),
    )
    response = main_module.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        main_module.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"calendar account {calendar_account_id} is missing protected credentials"
    }

    monkeypatch.setattr(
        main_module,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialInvalidError(
                f"calendar account {calendar_account_id} has invalid protected credentials"
            )
        ),
    )
    response = main_module.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        main_module.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"calendar account {calendar_account_id} has invalid protected credentials"
    }

    monkeypatch.setattr(
        main_module,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarCredentialPersistenceError(
                f"calendar account {calendar_account_id} protected credentials could not be persisted"
            )
        ),
    )
    response = main_module.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        main_module.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"calendar account {calendar_account_id} protected credentials could not be persisted"
    }

    monkeypatch.setattr(
        main_module,
        "ingest_calendar_event_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CalendarEventFetchError("calendar event evt-001 could not be fetched")
        ),
    )
    response = main_module.ingest_calendar_event(
        calendar_account_id,
        "evt-001",
        main_module.IngestCalendarEventRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 502
    assert json.loads(response.body) == {
        "detail": "calendar event evt-001 could not be fetched"
    }
