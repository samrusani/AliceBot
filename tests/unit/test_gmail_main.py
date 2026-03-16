from __future__ import annotations

import json
from contextlib import contextmanager
from uuid import uuid4

import pytest
import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.gmail import (
    GmailAccountAlreadyExistsError,
    GmailAccountNotFoundError,
    GmailCredentialInvalidError,
    GmailCredentialNotFoundError,
    GmailCredentialPersistenceError,
    GmailCredentialRefreshError,
    GmailCredentialValidationError,
    GmailMessageFetchError,
    GmailMessageNotFoundError,
    GmailMessageUnsupportedError,
)
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


def test_list_gmail_accounts_endpoint_returns_payload(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(
        main_module,
        "list_gmail_account_records",
        lambda *_args, **_kwargs: {
            "items": [],
            "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
        },
    )

    response = main_module.list_gmail_accounts(user_id)

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "items": [],
        "summary": {"total_count": 0, "order": ["created_at_asc", "id_asc"]},
    }


def test_connect_gmail_account_endpoint_maps_duplicate_to_409(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_gmail_account_record(*_args, **_kwargs):
        raise GmailAccountAlreadyExistsError("gmail account acct-001 is already connected")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_gmail_account_record", fake_create_gmail_account_record)

    response = main_module.connect_gmail_account(
        main_module.ConnectGmailAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )

    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": "gmail account acct-001 is already connected"
    }


def test_connect_gmail_account_request_requires_complete_refresh_bundle() -> None:
    with pytest.raises(ValueError, match="gmail refresh credentials must include refresh_token"):
        main_module.ConnectGmailAccountRequest(
            user_id=uuid4(),
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
            refresh_token="refresh-1",
        )


def test_connect_gmail_account_endpoint_maps_invalid_refresh_bundle_to_400(monkeypatch) -> None:
    user_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_create_gmail_account_record(*_args, **_kwargs):
        raise GmailCredentialValidationError(
            "gmail refresh credentials must include refresh_token, client_id, client_secret, "
            "and access_token_expires_at"
        )

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "create_gmail_account_record", fake_create_gmail_account_record)

    response = main_module.connect_gmail_account(
        main_module.ConnectGmailAccountRequest(
            user_id=user_id,
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            access_token="token-1",
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": (
            "gmail refresh credentials must include refresh_token, client_id, client_secret, "
            "and access_token_expires_at"
        )
    }


def test_get_gmail_account_endpoint_maps_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    gmail_account_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_get_gmail_account_record(*_args, **_kwargs):
        raise GmailAccountNotFoundError(f"gmail account {gmail_account_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "get_gmail_account_record", fake_get_gmail_account_record)

    response = main_module.get_gmail_account(gmail_account_id, user_id)

    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": f"gmail account {gmail_account_id} was not found"}


def test_ingest_gmail_message_endpoint_maps_workspace_not_found_to_404(monkeypatch) -> None:
    user_id = uuid4()
    gmail_account_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    def fake_ingest_gmail_message_record(*_args, **_kwargs):
        raise TaskWorkspaceNotFoundError(f"task workspace {task_workspace_id} was not found")

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)
    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_ingest_gmail_message_record)

    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )

    assert response.status_code == 404
    assert json.loads(response.body) == {
        "detail": f"task workspace {task_workspace_id} was not found"
    }


def test_ingest_gmail_message_endpoint_maps_upstream_errors(monkeypatch) -> None:
    user_id = uuid4()
    gmail_account_id = uuid4()
    task_workspace_id = uuid4()
    settings = Settings(database_url="postgresql://app")

    @contextmanager
    def fake_user_connection(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(main_module, "user_connection", fake_user_connection)

    def fake_missing(*_args, **_kwargs):
        raise GmailMessageNotFoundError("gmail message msg-001 was not found")

    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_missing)
    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 404
    assert json.loads(response.body) == {"detail": "gmail message msg-001 was not found"}

    def fake_unsupported(*_args, **_kwargs):
        raise GmailMessageUnsupportedError("gmail message msg-001 is not a supported RFC822 email")

    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_unsupported)
    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "gmail message msg-001 is not a supported RFC822 email"
    }

    def fake_missing_credentials(*_args, **_kwargs):
        raise GmailCredentialNotFoundError(
            f"gmail account {gmail_account_id} is missing protected credentials"
        )

    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_missing_credentials)
    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"gmail account {gmail_account_id} is missing protected credentials"
    }

    def fake_invalid_credentials(*_args, **_kwargs):
        raise GmailCredentialInvalidError(
            f"gmail account {gmail_account_id} has invalid protected credentials"
        )

    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_invalid_credentials)
    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"gmail account {gmail_account_id} has invalid protected credentials"
    }

    def fake_persistence_error(*_args, **_kwargs):
        raise GmailCredentialPersistenceError(
            f"gmail account {gmail_account_id} renewed protected credentials could not be persisted"
        )

    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_persistence_error)
    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 409
    assert json.loads(response.body) == {
        "detail": f"gmail account {gmail_account_id} renewed protected credentials could not be persisted"
    }

    def fake_fetch_error(*_args, **_kwargs):
        raise GmailMessageFetchError("gmail message msg-001 could not be fetched")

    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_fetch_error)
    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 502
    assert json.loads(response.body) == {
        "detail": "gmail message msg-001 could not be fetched"
    }

    def fake_refresh_error(*_args, **_kwargs):
        raise GmailCredentialRefreshError(
            f"gmail account {gmail_account_id} access token could not be renewed"
        )

    monkeypatch.setattr(main_module, "ingest_gmail_message_record", fake_refresh_error)
    response = main_module.ingest_gmail_message(
        gmail_account_id,
        "msg-001",
        main_module.IngestGmailMessageRequest(
            user_id=user_id,
            task_workspace_id=task_workspace_id,
        ),
    )
    assert response.status_code == 502
    assert json.loads(response.body) == {
        "detail": f"gmail account {gmail_account_id} access token could not be renewed"
    }
