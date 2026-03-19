from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.artifacts import TaskArtifactAlreadyExistsError
from alicebot_api.calendar import (
    CALENDAR_EVENT_ARTIFACT_MEDIA_TYPE,
    CalendarAccountAlreadyExistsError,
    CalendarAccountNotFoundError,
    CalendarCredentialInvalidError,
    CalendarCredentialNotFoundError,
    CalendarEventListValidationError,
    CalendarEventUnsupportedError,
    build_calendar_event_artifact_relative_path,
    build_calendar_protected_credential_blob,
    build_calendar_secret_ref,
    create_calendar_account_record,
    get_calendar_account_record,
    ingest_calendar_event_record,
    list_calendar_account_records,
    list_calendar_event_records,
    resolve_calendar_access_token,
)
from alicebot_api.calendar_secret_manager import (
    CALENDAR_SECRET_MANAGER_KIND_FILE_V1,
    CalendarSecretManagerError,
)
from alicebot_api.contracts import CALENDAR_PROTECTED_CREDENTIAL_KIND, CALENDAR_READONLY_SCOPE
from alicebot_api.contracts import (
    CalendarAccountConnectInput,
    CalendarEventIngestInput,
    CalendarEventListInput,
)
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


class CalendarStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 19, 10, 0, tzinfo=UTC)
        self.calendar_accounts: list[dict[str, object]] = []
        self.calendar_account_credentials: dict[UUID, dict[str, object]] = {}
        self.task_workspaces: list[dict[str, object]] = []
        self.task_artifacts: list[dict[str, object]] = []
        self.operations: list[tuple[str, object]] = []

    def create_calendar_account(
        self,
        *,
        provider_account_id: str,
        email_address: str,
        display_name: str | None,
        scope: str,
    ) -> dict[str, object]:
        row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "provider_account_id": provider_account_id,
            "email_address": email_address,
            "display_name": display_name,
            "scope": scope,
            "created_at": self.base_time + timedelta(minutes=len(self.calendar_accounts)),
            "updated_at": self.base_time + timedelta(minutes=len(self.calendar_accounts)),
        }
        self.calendar_accounts.append(row)
        return row

    def create_calendar_account_credential(
        self,
        *,
        calendar_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: dict[str, object] | None,
    ) -> dict[str, object]:
        row = {
            "calendar_account_id": calendar_account_id,
            "user_id": next(
                account["user_id"]
                for account in self.calendar_accounts
                if account["id"] == calendar_account_id
            ),
            "auth_kind": auth_kind,
            "credential_kind": credential_kind,
            "secret_manager_kind": secret_manager_kind,
            "secret_ref": secret_ref,
            "credential_blob": credential_blob,
            "created_at": self.base_time + timedelta(minutes=len(self.calendar_account_credentials)),
            "updated_at": self.base_time + timedelta(minutes=len(self.calendar_account_credentials)),
        }
        self.calendar_account_credentials[calendar_account_id] = row
        self.operations.append(("create_calendar_account_credential", calendar_account_id))
        return row

    def get_calendar_account_optional(self, calendar_account_id: UUID) -> dict[str, object] | None:
        return next(
            (row for row in self.calendar_accounts if row["id"] == calendar_account_id),
            None,
        )

    def get_calendar_account_credential_optional(
        self,
        calendar_account_id: UUID,
    ) -> dict[str, object] | None:
        self.operations.append(("get_calendar_account_credential_optional", calendar_account_id))
        return self.calendar_account_credentials.get(calendar_account_id)

    def get_calendar_account_by_provider_account_id_optional(
        self,
        provider_account_id: str,
    ) -> dict[str, object] | None:
        return next(
            (
                row
                for row in self.calendar_accounts
                if row["provider_account_id"] == provider_account_id
            ),
            None,
        )

    def list_calendar_accounts(self) -> list[dict[str, object]]:
        return sorted(
            self.calendar_accounts,
            key=lambda row: (row["created_at"], row["id"]),
        )

    def create_task_workspace(self, *, task_workspace_id: UUID, local_path: str) -> dict[str, object]:
        row = {
            "id": task_workspace_id,
            "user_id": uuid4(),
            "task_id": uuid4(),
            "status": "active",
            "local_path": local_path,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.task_workspaces.append(row)
        return row

    def get_task_workspace_optional(self, task_workspace_id: UUID) -> dict[str, object] | None:
        return next(
            (row for row in self.task_workspaces if row["id"] == task_workspace_id),
            None,
        )

    def lock_task_artifacts(self, task_workspace_id: UUID) -> None:
        self.operations.append(("lock_task_artifacts", task_workspace_id))

    def create_task_artifact(
        self,
        *,
        task_workspace_id: UUID,
        relative_path: str,
    ) -> dict[str, object]:
        row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "task_id": uuid4(),
            "task_workspace_id": task_workspace_id,
            "status": "registered",
            "ingestion_status": "ingested",
            "relative_path": relative_path,
            "media_type_hint": CALENDAR_EVENT_ARTIFACT_MEDIA_TYPE,
            "created_at": self.base_time,
            "updated_at": self.base_time,
        }
        self.task_artifacts.append(row)
        return row

    def get_task_artifact_by_workspace_relative_path_optional(
        self,
        *,
        task_workspace_id: UUID,
        relative_path: str,
    ) -> dict[str, object] | None:
        self.operations.append(
            ("get_task_artifact_by_workspace_relative_path_optional", task_workspace_id)
        )
        return next(
            (
                row
                for row in self.task_artifacts
                if row["task_workspace_id"] == task_workspace_id
                and row["relative_path"] == relative_path
            ),
            None,
        )


class CalendarSecretManagerStub:
    def __init__(self) -> None:
        self.secrets: dict[str, dict[str, object]] = {}
        self.operations: list[tuple[str, str]] = []

    @property
    def kind(self) -> str:
        return CALENDAR_SECRET_MANAGER_KIND_FILE_V1

    def load_secret(self, *, secret_ref: str) -> dict[str, object]:
        self.operations.append(("load_secret", secret_ref))
        try:
            return dict(self.secrets[secret_ref])
        except KeyError as exc:
            raise CalendarSecretManagerError(f"calendar secret {secret_ref} was not found") from exc

    def write_secret(self, *, secret_ref: str, payload: dict[str, object]) -> None:
        self.operations.append(("write_secret", secret_ref))
        self.secrets[secret_ref] = dict(payload)

    def delete_secret(self, *, secret_ref: str) -> None:
        self.operations.append(("delete_secret", secret_ref))
        self.secrets.pop(secret_ref, None)


def test_create_list_and_get_calendar_account_records_are_deterministic() -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    user_id = uuid4()

    first = create_calendar_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )
    second = create_calendar_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=CalendarAccountConnectInput(
            provider_account_id="acct-002",
            email_address="owner+2@example.com",
            display_name=None,
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-2",
        ),
    )

    assert list_calendar_account_records(store, user_id=user_id) == {
        "items": [first["account"], second["account"]],
        "summary": {"total_count": 2, "order": ["created_at_asc", "id_asc"]},
    }
    assert get_calendar_account_record(
        store,
        user_id=user_id,
        calendar_account_id=UUID(second["account"]["id"]),
    ) == {"account": second["account"]}


def test_create_calendar_account_record_persists_protected_credential_and_hides_secret() -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    user_id = uuid4()

    response = create_calendar_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )

    account_id = UUID(response["account"]["id"])
    assert response["account"]["provider"] == "google_calendar"
    secret_ref = build_calendar_secret_ref(
        user_id=store.calendar_account_credentials[account_id]["user_id"],
        calendar_account_id=account_id,
    )
    assert store.calendar_account_credentials[account_id]["credential_blob"] is None
    assert store.calendar_account_credentials[account_id]["credential_kind"] == (
        CALENDAR_PROTECTED_CREDENTIAL_KIND
    )
    assert store.calendar_account_credentials[account_id]["secret_ref"] == secret_ref
    assert secret_manager.secrets[secret_ref] == {
        "credential_kind": CALENDAR_PROTECTED_CREDENTIAL_KIND,
        "access_token": "token-1",
    }


def test_create_calendar_account_record_rejects_duplicate_provider_account_id() -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    request = CalendarAccountConnectInput(
        provider_account_id="acct-001",
        email_address="owner@example.com",
        display_name="Owner",
        scope=CALENDAR_READONLY_SCOPE,
        access_token="token-1",
    )
    create_calendar_account_record(store, secret_manager, user_id=uuid4(), request=request)

    with pytest.raises(
        CalendarAccountAlreadyExistsError,
        match="calendar account acct-001 is already connected",
    ):
        create_calendar_account_record(store, secret_manager, user_id=uuid4(), request=request)


def test_get_calendar_account_record_raises_when_account_is_missing() -> None:
    with pytest.raises(CalendarAccountNotFoundError, match="was not found"):
        get_calendar_account_record(
            CalendarStoreStub(),
            user_id=uuid4(),
            calendar_account_id=uuid4(),
        )


def test_list_calendar_event_records_enforces_deterministic_utc_order_and_shape(monkeypatch) -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    user_id = uuid4()
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    monkeypatch.setattr(
        "alicebot_api.calendar.fetch_calendar_event_list_payload",
        lambda **_kwargs: [
            {
                "id": "evt-c",
                "summary": "Third",
                "start": {"dateTime": "2026-03-25T10:00:00+02:00"},
                "end": {"dateTime": "2026-03-25T10:30:00+02:00"},
                "status": "confirmed",
                "htmlLink": "https://calendar.google.com/event?eid=evt-c",
                "updated": "2026-03-24T10:00:00+00:00",
            },
            {
                "id": "evt-a",
                "summary": "First",
                "start": {"date": "2026-03-20"},
                "end": {"date": "2026-03-21"},
                "status": "tentative",
                "updated": "2026-03-19T10:00:00+00:00",
            },
            {
                "id": "evt-b",
                "summary": "Second",
                "start": {"dateTime": "2026-03-25T08:30:00+00:00"},
                "end": {"dateTime": "2026-03-25T09:30:00+00:00"},
                "status": "confirmed",
                "updated": "2026-03-24T11:00:00+00:00",
            },
            {"summary": "Missing id should be skipped"},
        ],
    )

    response = list_calendar_event_records(
        store,
        secret_manager,
        user_id=user_id,
        request=CalendarEventListInput(
            calendar_account_id=UUID(account["id"]),
            limit=2,
            time_min=datetime(2026, 3, 20, 0, 0, tzinfo=UTC),
            time_max=datetime(2026, 3, 27, 0, 0, tzinfo=UTC),
        ),
    )

    assert response["account"] == account
    assert response["items"] == [
        {
            "provider_event_id": "evt-a",
            "status": "tentative",
            "summary": "First",
            "start_time": "2026-03-20",
            "end_time": "2026-03-21",
            "html_link": None,
            "updated_at": "2026-03-19T10:00:00+00:00",
        },
        {
            "provider_event_id": "evt-c",
            "status": "confirmed",
            "summary": "Third",
            "start_time": "2026-03-25T10:00:00+02:00",
            "end_time": "2026-03-25T10:30:00+02:00",
            "html_link": "https://calendar.google.com/event?eid=evt-c",
            "updated_at": "2026-03-24T10:00:00+00:00",
        },
    ]
    assert response["summary"] == {
        "total_count": 2,
        "limit": 2,
        "order": ["start_time_asc", "provider_event_id_asc"],
        "time_min": "2026-03-20T00:00:00+00:00",
        "time_max": "2026-03-27T00:00:00+00:00",
    }


def test_list_calendar_event_records_enforces_hard_max_limit(monkeypatch) -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    monkeypatch.setattr(
        "alicebot_api.calendar.fetch_calendar_event_list_payload",
        lambda **_kwargs: [
            {
                "id": f"evt-{index:03d}",
                "start": {"dateTime": f"2026-03-20T09:{index % 60:02d}:00+00:00"},
            }
            for index in range(60)
        ],
    )

    response = list_calendar_event_records(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarEventListInput(
            calendar_account_id=UUID(account["id"]),
            limit=999,
        ),
    )

    assert response["summary"]["limit"] == 50
    assert response["summary"]["total_count"] == 50
    assert len(response["items"]) == 50


def test_list_calendar_event_records_raises_for_not_found_account() -> None:
    with pytest.raises(CalendarAccountNotFoundError, match="was not found"):
        list_calendar_event_records(
            CalendarStoreStub(),
            CalendarSecretManagerStub(),
            user_id=uuid4(),
            request=CalendarEventListInput(
                calendar_account_id=uuid4(),
                limit=10,
            ),
        )


def test_list_calendar_event_records_rejects_invalid_time_window() -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    with pytest.raises(
        CalendarEventListValidationError,
        match="calendar event time_min must be less than or equal to time_max",
    ):
        list_calendar_event_records(
            store,
            secret_manager,
            user_id=uuid4(),
            request=CalendarEventListInput(
                calendar_account_id=UUID(account["id"]),
                time_min=datetime(2026, 3, 22, tzinfo=UTC),
                time_max=datetime(2026, 3, 21, tzinfo=UTC),
            ),
        )


def test_resolve_calendar_access_token_reads_protected_credential() -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    assert resolve_calendar_access_token(
        store,
        secret_manager,
        calendar_account_id=UUID(account["id"]),
    ) == "token-1"


def test_resolve_calendar_access_token_rejects_missing_and_invalid_protected_credentials() -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    account_id = UUID(account["id"])

    store.calendar_account_credentials.pop(account_id)
    with pytest.raises(
        CalendarCredentialNotFoundError,
        match=f"calendar account {account_id} is missing protected credentials",
    ):
        resolve_calendar_access_token(store, secret_manager, calendar_account_id=account_id)

    secret_ref = build_calendar_secret_ref(
        user_id=uuid4(),
        calendar_account_id=account_id,
    )
    store.calendar_account_credentials[account_id] = {
        "calendar_account_id": account_id,
        "user_id": uuid4(),
        "auth_kind": "oauth_access_token",
        "credential_kind": CALENDAR_PROTECTED_CREDENTIAL_KIND,
        "secret_manager_kind": CALENDAR_SECRET_MANAGER_KIND_FILE_V1,
        "secret_ref": secret_ref,
        "credential_blob": None,
        "created_at": store.base_time,
        "updated_at": store.base_time,
    }
    secret_manager.secrets[secret_ref] = {
        "credential_kind": CALENDAR_PROTECTED_CREDENTIAL_KIND,
        "access_token": "",
    }

    with pytest.raises(
        CalendarCredentialInvalidError,
        match=f"calendar account {account_id} has invalid protected credentials",
    ):
        resolve_calendar_access_token(store, secret_manager, calendar_account_id=account_id)


def test_ingest_calendar_event_record_writes_text_artifact_and_reuses_artifact_seam(
    monkeypatch,
    tmp_path,
) -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace = store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str((tmp_path / "workspace").resolve()),
    )
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    monkeypatch.setattr(
        "alicebot_api.calendar.fetch_calendar_event_payload",
        lambda **_kwargs: {
            "id": "evt-001",
            "summary": "Sprint planning",
            "description": "Discuss sprint goals",
            "status": "confirmed",
            "start": {"dateTime": "2026-03-20T09:00:00+00:00"},
            "end": {"dateTime": "2026-03-20T09:30:00+00:00"},
        },
    )

    def fake_register(_store, *, user_id: UUID, request):
        path = Path(request.local_path)
        assert "Summary: Sprint planning" in path.read_text(encoding="utf-8")
        return {
            "artifact": {
                "id": "00000000-0000-0000-0000-000000000123",
                "task_id": str(workspace["task_id"]),
                "task_workspace_id": str(workspace_id),
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": path.relative_to(Path(workspace["local_path"])).as_posix(),
                "media_type_hint": CALENDAR_EVENT_ARTIFACT_MEDIA_TYPE,
                "created_at": "2026-03-19T10:00:00+00:00",
                "updated_at": "2026-03-19T10:00:00+00:00",
            }
        }

    monkeypatch.setattr("alicebot_api.calendar.register_task_artifact_record", fake_register)
    monkeypatch.setattr(
        "alicebot_api.calendar.ingest_task_artifact_record",
        lambda _store, *, user_id, request: {
            "artifact": {
                "id": "00000000-0000-0000-0000-000000000123",
                "task_id": str(workspace["task_id"]),
                "task_workspace_id": str(workspace_id),
                "status": "registered",
                "ingestion_status": "ingested",
                "relative_path": build_calendar_event_artifact_relative_path(
                    provider_account_id="acct-001",
                    provider_event_id="evt-001",
                ),
                "media_type_hint": CALENDAR_EVENT_ARTIFACT_MEDIA_TYPE,
                "created_at": "2026-03-19T10:00:00+00:00",
                "updated_at": "2026-03-19T10:00:01+00:00",
            },
            "summary": {
                "total_count": 1,
                "total_characters": 32,
                "media_type": CALENDAR_EVENT_ARTIFACT_MEDIA_TYPE,
                "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
                "order": ["sequence_no_asc", "id_asc"],
            },
        },
    )

    response = ingest_calendar_event_record(
        store,
        secret_manager,
        user_id=user_id,
        request=CalendarEventIngestInput(
            calendar_account_id=UUID(account["id"]),
            task_workspace_id=workspace_id,
            provider_event_id="evt-001",
        ),
    )

    assert response["account"] == account
    assert response["event"] == {
        "provider_event_id": "evt-001",
        "artifact_relative_path": "calendar/acct-001/evt-001.txt",
        "media_type": CALENDAR_EVENT_ARTIFACT_MEDIA_TYPE,
    }
    assert response["artifact"]["relative_path"] == "calendar/acct-001/evt-001.txt"


def test_ingest_calendar_event_record_rejects_duplicate_sanitized_path_before_fetch_or_write(
    monkeypatch,
    tmp_path,
) -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    workspace_id = uuid4()
    workspace_path = (tmp_path / "workspace").resolve()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str(workspace_path),
    )
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    relative_path = build_calendar_event_artifact_relative_path(
        provider_account_id="acct-001",
        provider_event_id="evt/001",
    )
    store.create_task_artifact(
        task_workspace_id=workspace_id,
        relative_path=relative_path,
    )

    monkeypatch.setattr(
        "alicebot_api.calendar.fetch_calendar_event_payload",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("fetch_calendar_event_payload should not be called")
        ),
    )

    with pytest.raises(
        TaskArtifactAlreadyExistsError,
        match=f"artifact {relative_path} is already registered for task workspace {workspace_id}",
    ):
        ingest_calendar_event_record(
            store,
            secret_manager,
            user_id=uuid4(),
            request=CalendarEventIngestInput(
                calendar_account_id=UUID(account["id"]),
                task_workspace_id=workspace_id,
                provider_event_id="evt:001",
            ),
        )


def test_ingest_calendar_event_record_requires_visible_workspace() -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    with pytest.raises(TaskWorkspaceNotFoundError, match="task workspace .* was not found"):
        ingest_calendar_event_record(
            store,
            secret_manager,
            user_id=uuid4(),
            request=CalendarEventIngestInput(
                calendar_account_id=UUID(account["id"]),
                task_workspace_id=uuid4(),
                provider_event_id="evt-001",
            ),
        )


def test_ingest_calendar_event_record_rejects_unsupported_event(monkeypatch, tmp_path) -> None:
    store = CalendarStoreStub()
    secret_manager = CalendarSecretManagerStub()
    workspace_id = uuid4()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str((tmp_path / "workspace").resolve()),
    )
    account = create_calendar_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=CalendarAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=CALENDAR_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    monkeypatch.setattr(
        "alicebot_api.calendar.fetch_calendar_event_payload",
        lambda **_kwargs: {"id": "evt-unsupported", "start": {"dateTime": "2026-03-20T09:00:00+00:00"}},
    )

    with pytest.raises(
        CalendarEventUnsupportedError,
        match="calendar event evt-unsupported is not supported for ingestion",
    ):
        ingest_calendar_event_record(
            store,
            secret_manager,
            user_id=uuid4(),
            request=CalendarEventIngestInput(
                calendar_account_id=UUID(account["id"]),
                task_workspace_id=workspace_id,
                provider_event_id="evt-unsupported",
            ),
        )


def test_build_calendar_protected_credential_blob_rejects_empty_token() -> None:
    with pytest.raises(
        ValueError,
        match="calendar access token must be non-empty",
    ):
        build_calendar_protected_credential_blob(access_token="")
