from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.artifacts import TaskArtifactAlreadyExistsError
from alicebot_api.contracts import GMAIL_READONLY_SCOPE, GmailAccountConnectInput, GmailMessageIngestInput
from alicebot_api.gmail import (
    GmailAccountAlreadyExistsError,
    GmailAccountNotFoundError,
    GmailMessageUnsupportedError,
    build_gmail_message_artifact_relative_path,
    create_gmail_account_record,
    get_gmail_account_record,
    ingest_gmail_message_record,
    list_gmail_account_records,
)
from alicebot_api.workspaces import TaskWorkspaceNotFoundError


def _build_rfc822_email_bytes(*, plain_body: str) -> bytes:
    return (
        "\r\n".join(
            [
                "From: Alice <alice@example.com>",
                "To: Bob <bob@example.com>",
                "Subject: Sprint Update",
                'Content-Type: text/plain; charset="utf-8"',
                "Content-Transfer-Encoding: 8bit",
                "",
                plain_body,
            ]
        ).encode("utf-8")
    )


class GmailStoreStub:
    def __init__(self) -> None:
        self.base_time = datetime(2026, 3, 16, 10, 0, tzinfo=UTC)
        self.gmail_accounts: list[dict[str, object]] = []
        self.task_workspaces: list[dict[str, object]] = []
        self.task_artifacts: list[dict[str, object]] = []
        self.operations: list[tuple[str, object]] = []

    def create_gmail_account(
        self,
        *,
        provider_account_id: str,
        email_address: str,
        display_name: str | None,
        scope: str,
        access_token: str,
    ) -> dict[str, object]:
        row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "provider_account_id": provider_account_id,
            "email_address": email_address,
            "display_name": display_name,
            "scope": scope,
            "access_token": access_token,
            "created_at": self.base_time + timedelta(minutes=len(self.gmail_accounts)),
            "updated_at": self.base_time + timedelta(minutes=len(self.gmail_accounts)),
        }
        self.gmail_accounts.append(row)
        return row

    def get_gmail_account_optional(self, gmail_account_id: UUID) -> dict[str, object] | None:
        return next(
            (row for row in self.gmail_accounts if row["id"] == gmail_account_id),
            None,
        )

    def get_gmail_account_by_provider_account_id_optional(
        self,
        provider_account_id: str,
    ) -> dict[str, object] | None:
        return next(
            (
                row
                for row in self.gmail_accounts
                if row["provider_account_id"] == provider_account_id
            ),
            None,
        )

    def list_gmail_accounts(self) -> list[dict[str, object]]:
        return sorted(
            self.gmail_accounts,
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
            "media_type_hint": "message/rfc822",
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


def test_create_list_and_get_gmail_account_records_are_deterministic() -> None:
    store = GmailStoreStub()
    user_id = uuid4()

    first = create_gmail_account_record(
        store,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )
    second = create_gmail_account_record(
        store,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-002",
            email_address="owner+2@example.com",
            display_name=None,
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-2",
        ),
    )

    assert list_gmail_account_records(store, user_id=user_id) == {
        "items": [first["account"], second["account"]],
        "summary": {"total_count": 2, "order": ["created_at_asc", "id_asc"]},
    }
    assert get_gmail_account_record(
        store,
        user_id=user_id,
        gmail_account_id=UUID(second["account"]["id"]),
    ) == {"account": second["account"]}


def test_create_gmail_account_record_rejects_duplicate_provider_account_id() -> None:
    store = GmailStoreStub()
    user_id = uuid4()
    request = GmailAccountConnectInput(
        provider_account_id="acct-001",
        email_address="owner@example.com",
        display_name="Owner",
        scope=GMAIL_READONLY_SCOPE,
        access_token="token-1",
    )
    create_gmail_account_record(store, user_id=user_id, request=request)

    with pytest.raises(
        GmailAccountAlreadyExistsError,
        match="gmail account acct-001 is already connected",
    ):
        create_gmail_account_record(store, user_id=user_id, request=request)


def test_get_gmail_account_record_raises_when_account_is_missing() -> None:
    with pytest.raises(GmailAccountNotFoundError, match="was not found"):
        get_gmail_account_record(
            GmailStoreStub(),
            user_id=uuid4(),
            gmail_account_id=uuid4(),
        )


def test_ingest_gmail_message_record_writes_rfc822_artifact_and_reuses_artifact_seam(
    monkeypatch,
    tmp_path,
) -> None:
    store = GmailStoreStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace = store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str((tmp_path / "workspace").resolve()),
    )
    account = create_gmail_account_record(
        store,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    raw_bytes = _build_rfc822_email_bytes(plain_body="hello from gmail")
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "alicebot_api.gmail.fetch_gmail_message_raw_bytes",
        lambda **_kwargs: raw_bytes,
    )

    def fake_register(_store, *, user_id: UUID, request):
        calls["register_user_id"] = user_id
        calls["register_request"] = request
        path = Path(request.local_path)
        assert path.read_bytes() == raw_bytes
        assert path.is_file()
        return {
            "artifact": {
                "id": "00000000-0000-0000-0000-000000000123",
                "task_id": str(workspace["task_id"]),
                "task_workspace_id": str(workspace_id),
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": path.relative_to(Path(workspace["local_path"])).as_posix(),
                "media_type_hint": "message/rfc822",
                "created_at": "2026-03-16T10:00:00+00:00",
                "updated_at": "2026-03-16T10:00:00+00:00",
            }
        }

    def fake_ingest(_store, *, user_id: UUID, request):
        calls["ingest_user_id"] = user_id
        calls["ingest_request"] = request
        return {
            "artifact": {
                "id": "00000000-0000-0000-0000-000000000123",
                "task_id": str(workspace["task_id"]),
                "task_workspace_id": str(workspace_id),
                "status": "registered",
                "ingestion_status": "ingested",
                "relative_path": build_gmail_message_artifact_relative_path(
                    provider_account_id="acct-001",
                    provider_message_id="msg-001",
                ),
                "media_type_hint": "message/rfc822",
                "created_at": "2026-03-16T10:00:00+00:00",
                "updated_at": "2026-03-16T10:00:01+00:00",
            },
            "summary": {
                "total_count": 1,
                "total_characters": 16,
                "media_type": "message/rfc822",
                "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
                "order": ["sequence_no_asc", "id_asc"],
            },
        }

    monkeypatch.setattr("alicebot_api.gmail.register_task_artifact_record", fake_register)
    monkeypatch.setattr("alicebot_api.gmail.ingest_task_artifact_record", fake_ingest)

    response = ingest_gmail_message_record(
        store,
        user_id=user_id,
        request=GmailMessageIngestInput(
            gmail_account_id=UUID(account["id"]),
            task_workspace_id=workspace_id,
            provider_message_id="msg-001",
        ),
    )

    assert response == {
        "account": account,
        "message": {
            "provider_message_id": "msg-001",
            "artifact_relative_path": "gmail/acct-001/msg-001.eml",
            "media_type": "message/rfc822",
        },
        "artifact": {
            "id": "00000000-0000-0000-0000-000000000123",
            "task_id": str(workspace["task_id"]),
            "task_workspace_id": str(workspace_id),
            "status": "registered",
            "ingestion_status": "ingested",
            "relative_path": "gmail/acct-001/msg-001.eml",
            "media_type_hint": "message/rfc822",
            "created_at": "2026-03-16T10:00:00+00:00",
            "updated_at": "2026-03-16T10:00:01+00:00",
        },
        "summary": {
            "total_count": 1,
            "total_characters": 16,
            "media_type": "message/rfc822",
            "chunking_rule": "normalized_utf8_text_fixed_window_1000_chars_v1",
            "order": ["sequence_no_asc", "id_asc"],
        },
    }
    assert calls["register_user_id"] == user_id
    assert calls["ingest_user_id"] == user_id


def test_ingest_gmail_message_record_rejects_unsupported_message(monkeypatch, tmp_path) -> None:
    store = GmailStoreStub()
    user_id = uuid4()
    workspace_id = uuid4()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str((tmp_path / "workspace").resolve()),
    )
    account = create_gmail_account_record(
        store,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    monkeypatch.setattr(
        "alicebot_api.gmail.fetch_gmail_message_raw_bytes",
        lambda **_kwargs: b"not-a-valid-rfc822-email",
    )

    with pytest.raises(
        GmailMessageUnsupportedError,
        match="gmail message msg-unsupported is not a supported RFC822 email",
    ):
        ingest_gmail_message_record(
            store,
            user_id=user_id,
            request=GmailMessageIngestInput(
                gmail_account_id=UUID(account["id"]),
                task_workspace_id=workspace_id,
                provider_message_id="msg-unsupported",
            ),
        )


def test_ingest_gmail_message_record_rejects_duplicate_sanitized_path_before_fetch_or_write(
    monkeypatch,
    tmp_path,
) -> None:
    store = GmailStoreStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace_path = (tmp_path / "workspace").resolve()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str(workspace_path),
    )
    account = create_gmail_account_record(
        store,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    relative_path = build_gmail_message_artifact_relative_path(
        provider_account_id="acct-001",
        provider_message_id="msg/001",
    )
    existing_file = workspace_path / relative_path
    existing_file.parent.mkdir(parents=True, exist_ok=True)
    existing_file.write_bytes(b"original")
    store.create_task_artifact(
        task_workspace_id=workspace_id,
        relative_path=relative_path,
    )

    def fail_fetch(**_kwargs):
        raise AssertionError("fetch_gmail_message_raw_bytes should not be called")

    monkeypatch.setattr("alicebot_api.gmail.fetch_gmail_message_raw_bytes", fail_fetch)

    with pytest.raises(
        TaskArtifactAlreadyExistsError,
        match=f"artifact {relative_path} is already registered for task workspace {workspace_id}",
    ):
        ingest_gmail_message_record(
            store,
            user_id=user_id,
            request=GmailMessageIngestInput(
                gmail_account_id=UUID(account["id"]),
                task_workspace_id=workspace_id,
                provider_message_id="msg:001",
            ),
        )

    assert existing_file.read_bytes() == b"original"
    assert store.operations[:2] == [
        ("lock_task_artifacts", workspace_id),
        ("get_task_artifact_by_workspace_relative_path_optional", workspace_id),
    ]


def test_ingest_gmail_message_record_requires_visible_workspace(monkeypatch) -> None:
    store = GmailStoreStub()
    user_id = uuid4()
    account = create_gmail_account_record(
        store,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    monkeypatch.setattr(
        "alicebot_api.gmail.fetch_gmail_message_raw_bytes",
        lambda **_kwargs: _build_rfc822_email_bytes(plain_body="hello"),
    )

    with pytest.raises(TaskWorkspaceNotFoundError, match="task workspace .* was not found"):
        ingest_gmail_message_record(
            store,
            user_id=user_id,
            request=GmailMessageIngestInput(
                gmail_account_id=UUID(account["id"]),
                task_workspace_id=uuid4(),
                provider_message_id="msg-001",
            ),
        )
