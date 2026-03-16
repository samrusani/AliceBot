from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.artifacts import TaskArtifactAlreadyExistsError
from alicebot_api.contracts import (
    GMAIL_PROTECTED_CREDENTIAL_KIND,
    GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND,
    GMAIL_READONLY_SCOPE,
    GmailAccountConnectInput,
    GmailMessageIngestInput,
)
from alicebot_api.gmail import (
    GmailAccountAlreadyExistsError,
    GmailAccountNotFoundError,
    GmailCredentialInvalidError,
    GmailCredentialNotFoundError,
    GmailCredentialPersistenceError,
    GmailCredentialValidationError,
    GmailMessageUnsupportedError,
    GMAIL_SECRET_MANAGER_KIND_FILE_V1,
    GMAIL_SECRET_MANAGER_KIND_LEGACY_DB_V0,
    RefreshedGmailCredential,
    build_gmail_secret_ref,
    build_gmail_message_artifact_relative_path,
    build_gmail_protected_credential_blob,
    create_gmail_account_record,
    get_gmail_account_record,
    ingest_gmail_message_record,
    list_gmail_account_records,
    resolve_gmail_access_token,
)
from alicebot_api.gmail_secret_manager import GmailSecretManagerError
from alicebot_api.store import ContinuityStoreInvariantError
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
        self.gmail_account_credentials: dict[UUID, dict[str, object]] = {}
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
    ) -> dict[str, object]:
        row = {
            "id": uuid4(),
            "user_id": uuid4(),
            "provider_account_id": provider_account_id,
            "email_address": email_address,
            "display_name": display_name,
            "scope": scope,
            "created_at": self.base_time + timedelta(minutes=len(self.gmail_accounts)),
            "updated_at": self.base_time + timedelta(minutes=len(self.gmail_accounts)),
        }
        self.gmail_accounts.append(row)
        return row

    def create_gmail_account_credential(
        self,
        *,
        gmail_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: dict[str, object] | None,
    ) -> dict[str, object]:
        row = {
            "gmail_account_id": gmail_account_id,
            "user_id": next(
                account["user_id"]
                for account in self.gmail_accounts
                if account["id"] == gmail_account_id
            ),
            "auth_kind": auth_kind,
            "credential_kind": credential_kind,
            "secret_manager_kind": secret_manager_kind,
            "secret_ref": secret_ref,
            "credential_blob": credential_blob,
            "created_at": self.base_time + timedelta(minutes=len(self.gmail_account_credentials)),
            "updated_at": self.base_time + timedelta(minutes=len(self.gmail_account_credentials)),
        }
        self.gmail_account_credentials[gmail_account_id] = row
        self.operations.append(("create_gmail_account_credential", gmail_account_id))
        return row

    def get_gmail_account_optional(self, gmail_account_id: UUID) -> dict[str, object] | None:
        return next(
            (row for row in self.gmail_accounts if row["id"] == gmail_account_id),
            None,
        )

    def get_gmail_account_credential_optional(
        self,
        gmail_account_id: UUID,
    ) -> dict[str, object] | None:
        self.operations.append(("get_gmail_account_credential_optional", gmail_account_id))
        return self.gmail_account_credentials.get(gmail_account_id)

    def update_gmail_account_credential(
        self,
        *,
        gmail_account_id: UUID,
        auth_kind: str,
        credential_kind: str,
        secret_manager_kind: str,
        secret_ref: str | None,
        credential_blob: dict[str, object] | None,
    ) -> dict[str, object]:
        existing = self.gmail_account_credentials[gmail_account_id]
        updated = {
            **existing,
            "auth_kind": auth_kind,
            "credential_kind": credential_kind,
            "secret_manager_kind": secret_manager_kind,
            "secret_ref": secret_ref,
            "credential_blob": credential_blob,
            "updated_at": self.base_time + timedelta(hours=1),
        }
        self.gmail_account_credentials[gmail_account_id] = updated
        self.operations.append(("update_gmail_account_credential", gmail_account_id))
        return updated

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


class GmailSecretManagerStub:
    def __init__(self) -> None:
        self.secrets: dict[str, dict[str, object]] = {}
        self.operations: list[tuple[str, str]] = []

    @property
    def kind(self) -> str:
        return GMAIL_SECRET_MANAGER_KIND_FILE_V1

    def load_secret(self, *, secret_ref: str) -> dict[str, object]:
        self.operations.append(("load_secret", secret_ref))
        try:
            return dict(self.secrets[secret_ref])
        except KeyError as exc:
            raise GmailSecretManagerError(f"gmail secret {secret_ref} was not found") from exc

    def write_secret(self, *, secret_ref: str, payload: dict[str, object]) -> None:
        self.operations.append(("write_secret", secret_ref))
        self.secrets[secret_ref] = dict(payload)

    def delete_secret(self, *, secret_ref: str) -> None:
        self.operations.append(("delete_secret", secret_ref))
        self.secrets.pop(secret_ref, None)


def test_create_list_and_get_gmail_account_records_are_deterministic() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()

    first = create_gmail_account_record(
        store,
        secret_manager,
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
        secret_manager,
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
    assert "access_token" not in first["account"]
    assert "access_token" not in second["account"]


def test_create_gmail_account_record_persists_protected_credential_and_hides_secret() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()

    response = create_gmail_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )

    account_id = UUID(response["account"]["id"])
    assert response == {
        "account": {
            "id": str(account_id),
            "provider": "gmail",
            "auth_kind": "oauth_access_token",
            "provider_account_id": "acct-001",
            "email_address": "owner@example.com",
            "display_name": "Owner",
            "scope": GMAIL_READONLY_SCOPE,
            "created_at": response["account"]["created_at"],
            "updated_at": response["account"]["updated_at"],
        }
    }
    secret_ref = build_gmail_secret_ref(
        user_id=store.gmail_account_credentials[account_id]["user_id"],
        gmail_account_id=account_id,
    )
    assert store.gmail_account_credentials[account_id] == {
        "gmail_account_id": account_id,
        "user_id": store.gmail_account_credentials[account_id]["user_id"],
        "auth_kind": "oauth_access_token",
        "credential_kind": GMAIL_PROTECTED_CREDENTIAL_KIND,
        "secret_manager_kind": GMAIL_SECRET_MANAGER_KIND_FILE_V1,
        "secret_ref": secret_ref,
        "credential_blob": None,
        "created_at": store.gmail_account_credentials[account_id]["created_at"],
        "updated_at": store.gmail_account_credentials[account_id]["updated_at"],
    }
    assert secret_manager.secrets[secret_ref] == {
        "credential_kind": GMAIL_PROTECTED_CREDENTIAL_KIND,
        "access_token": "token-1",
    }
    assert store.operations == [("create_gmail_account_credential", account_id)]
    assert secret_manager.operations == [("write_secret", secret_ref)]


def test_create_gmail_account_record_persists_refreshable_protected_credential_and_hides_secret() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    expires_at = datetime(2030, 1, 1, 0, 0, tzinfo=UTC)

    response = create_gmail_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-refresh-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
            refresh_token="refresh-1",
            client_id="client-1",
            client_secret="secret-1",
            access_token_expires_at=expires_at,
        ),
    )

    account_id = UUID(response["account"]["id"])
    assert response == {
        "account": {
            "id": str(account_id),
            "provider": "gmail",
            "auth_kind": "oauth_access_token",
            "provider_account_id": "acct-refresh-001",
            "email_address": "owner@example.com",
            "display_name": "Owner",
            "scope": GMAIL_READONLY_SCOPE,
            "created_at": response["account"]["created_at"],
            "updated_at": response["account"]["updated_at"],
        }
    }
    secret_ref = build_gmail_secret_ref(
        user_id=store.gmail_account_credentials[account_id]["user_id"],
        gmail_account_id=account_id,
    )
    assert store.gmail_account_credentials[account_id]["credential_blob"] is None
    assert store.gmail_account_credentials[account_id]["credential_kind"] == (
        GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND
    )
    assert store.gmail_account_credentials[account_id]["secret_manager_kind"] == (
        GMAIL_SECRET_MANAGER_KIND_FILE_V1
    )
    assert store.gmail_account_credentials[account_id]["secret_ref"] == secret_ref
    assert secret_manager.secrets[secret_ref] == {
        "credential_kind": GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND,
        "access_token": "token-1",
        "refresh_token": "refresh-1",
        "client_id": "client-1",
        "client_secret": "secret-1",
        "access_token_expires_at": expires_at.isoformat(),
    }
    assert store.operations == [("create_gmail_account_credential", account_id)]


def test_build_gmail_protected_credential_blob_rejects_partial_refresh_bundle() -> None:
    with pytest.raises(
        GmailCredentialValidationError,
        match=(
            "gmail refresh credentials must include refresh_token, client_id, client_secret, "
            "and access_token_expires_at"
        ),
    ):
        build_gmail_protected_credential_blob(
            access_token="token-1",
            refresh_token="refresh-1",
            client_id="client-1",
        )


def test_create_gmail_account_record_rejects_duplicate_provider_account_id() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    request = GmailAccountConnectInput(
        provider_account_id="acct-001",
        email_address="owner@example.com",
        display_name="Owner",
        scope=GMAIL_READONLY_SCOPE,
        access_token="token-1",
    )
    create_gmail_account_record(store, secret_manager, user_id=user_id, request=request)

    with pytest.raises(
        GmailAccountAlreadyExistsError,
        match="gmail account acct-001 is already connected",
    ):
        create_gmail_account_record(store, secret_manager, user_id=user_id, request=request)


def test_get_gmail_account_record_raises_when_account_is_missing() -> None:
    with pytest.raises(GmailAccountNotFoundError, match="was not found"):
        get_gmail_account_record(
            GmailStoreStub(),
            user_id=uuid4(),
            gmail_account_id=uuid4(),
        )


def test_resolve_gmail_access_token_reads_protected_credential() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]

    assert resolve_gmail_access_token(
        store,
        secret_manager,
        gmail_account_id=UUID(account["id"]),
    ) == "token-1"


def test_resolve_gmail_access_token_rejects_missing_and_invalid_protected_credentials() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    account_id = UUID(account["id"])

    store.gmail_account_credentials.pop(account_id)
    with pytest.raises(
        GmailCredentialNotFoundError,
        match=f"gmail account {account_id} is missing protected credentials",
    ):
        resolve_gmail_access_token(store, secret_manager, gmail_account_id=account_id)

    store.gmail_account_credentials[account_id] = {
        "gmail_account_id": account_id,
        "user_id": uuid4(),
        "auth_kind": "oauth_access_token",
        "credential_kind": GMAIL_PROTECTED_CREDENTIAL_KIND,
        "secret_manager_kind": GMAIL_SECRET_MANAGER_KIND_LEGACY_DB_V0,
        "secret_ref": None,
        "credential_blob": {"credential_kind": GMAIL_PROTECTED_CREDENTIAL_KIND},
        "created_at": store.base_time,
        "updated_at": store.base_time,
    }
    with pytest.raises(
        GmailCredentialInvalidError,
        match=f"gmail account {account_id} has invalid protected credentials",
    ):
        resolve_gmail_access_token(store, secret_manager, gmail_account_id=account_id)


def test_resolve_gmail_access_token_externalizes_legacy_db_credentials_on_first_read() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=GmailAccountConnectInput(
            provider_account_id="acct-legacy-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    account_id = UUID(account["id"])
    credential_row = store.gmail_account_credentials[account_id]
    legacy_blob = {
        "credential_kind": GMAIL_PROTECTED_CREDENTIAL_KIND,
        "access_token": "token-legacy-001",
    }
    secret_ref = credential_row["secret_ref"]
    assert secret_ref is not None
    credential_row["secret_manager_kind"] = GMAIL_SECRET_MANAGER_KIND_LEGACY_DB_V0
    credential_row["secret_ref"] = None
    credential_row["credential_blob"] = legacy_blob
    secret_manager.secrets.pop(secret_ref)

    assert resolve_gmail_access_token(store, secret_manager, gmail_account_id=account_id) == (
        "token-legacy-001"
    )
    assert store.gmail_account_credentials[account_id]["secret_manager_kind"] == (
        GMAIL_SECRET_MANAGER_KIND_FILE_V1
    )
    assert store.gmail_account_credentials[account_id]["secret_ref"] == secret_ref
    assert store.gmail_account_credentials[account_id]["credential_blob"] is None
    assert secret_manager.secrets[secret_ref] == legacy_blob


def test_resolve_gmail_access_token_renews_expired_refreshable_credential(monkeypatch) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    expired_at = datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
    refreshed_at = datetime(2030, 1, 1, 0, 5, tzinfo=UTC)
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
            refresh_token="refresh-1",
            client_id="client-1",
            client_secret="secret-1",
            access_token_expires_at=expired_at,
        ),
    )["account"]
    account_id = UUID(account["id"])

    monkeypatch.setattr(
        "alicebot_api.gmail.refresh_gmail_access_token",
        lambda **_kwargs: RefreshedGmailCredential(
            access_token="token-2",
            access_token_expires_at=refreshed_at,
        ),
    )

    secret_ref = store.gmail_account_credentials[account_id]["secret_ref"]
    assert resolve_gmail_access_token(store, secret_manager, gmail_account_id=account_id) == "token-2"
    assert secret_ref is not None
    assert secret_manager.secrets[secret_ref] == {
        "credential_kind": GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND,
        "access_token": "token-2",
        "refresh_token": "refresh-1",
        "client_id": "client-1",
        "client_secret": "secret-1",
        "access_token_expires_at": refreshed_at.isoformat(),
    }
    assert store.operations[-2:] == [
        ("get_gmail_account_credential_optional", account_id),
        ("update_gmail_account_credential", account_id),
    ]


def test_resolve_gmail_access_token_persists_rotated_refresh_token(monkeypatch) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    expired_at = datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
    refreshed_at = datetime(2030, 1, 1, 0, 5, tzinfo=UTC)
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
            refresh_token="refresh-1",
            client_id="client-1",
            client_secret="secret-1",
            access_token_expires_at=expired_at,
        ),
    )["account"]
    account_id = UUID(account["id"])

    monkeypatch.setattr(
        "alicebot_api.gmail.refresh_gmail_access_token",
        lambda **_kwargs: RefreshedGmailCredential(
            access_token="token-2",
            access_token_expires_at=refreshed_at,
            refresh_token="refresh-2",
        ),
    )

    secret_ref = store.gmail_account_credentials[account_id]["secret_ref"]
    assert resolve_gmail_access_token(store, secret_manager, gmail_account_id=account_id) == "token-2"
    assert secret_ref is not None
    assert secret_manager.secrets[secret_ref] == {
        "credential_kind": GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND,
        "access_token": "token-2",
        "refresh_token": "refresh-2",
        "client_id": "client-1",
        "client_secret": "secret-1",
        "access_token_expires_at": refreshed_at.isoformat(),
    }


def test_resolve_gmail_access_token_fails_deterministically_when_persisting_refresh_update_fails(
    monkeypatch,
) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    expired_at = datetime(2020, 1, 1, 0, 0, tzinfo=UTC)
    refreshed_at = datetime(2030, 1, 1, 0, 5, tzinfo=UTC)
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
            refresh_token="refresh-1",
            client_id="client-1",
            client_secret="secret-1",
            access_token_expires_at=expired_at,
        ),
    )["account"]
    account_id = UUID(account["id"])
    secret_ref = store.gmail_account_credentials[account_id]["secret_ref"]
    assert secret_ref is not None
    original_blob = dict(secret_manager.secrets[secret_ref])

    monkeypatch.setattr(
        "alicebot_api.gmail.refresh_gmail_access_token",
        lambda **_kwargs: RefreshedGmailCredential(
            access_token="token-2",
            access_token_expires_at=refreshed_at,
            refresh_token="refresh-2",
        ),
    )

    def fail_update(**_kwargs):
        raise ContinuityStoreInvariantError("update_gmail_account_credential did not return a row")

    monkeypatch.setattr(store, "update_gmail_account_credential", fail_update)

    with pytest.raises(
        GmailCredentialPersistenceError,
        match=f"gmail account {account_id} renewed protected credentials could not be persisted",
    ):
        resolve_gmail_access_token(store, secret_manager, gmail_account_id=account_id)

    assert secret_manager.secrets[secret_ref] == original_blob


def test_resolve_gmail_access_token_rejects_invalid_refreshable_protected_credentials() -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=uuid4(),
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    account_id = UUID(account["id"])
    secret_ref = store.gmail_account_credentials[account_id]["secret_ref"]
    assert secret_ref is not None
    secret_manager.secrets[secret_ref] = {
        "credential_kind": GMAIL_REFRESHABLE_PROTECTED_CREDENTIAL_KIND,
        "access_token": "token-1",
        "client_id": "client-1",
        "client_secret": "secret-1",
        "access_token_expires_at": "2020-01-01T00:00:00+00:00",
    }

    with pytest.raises(
        GmailCredentialInvalidError,
        match=f"gmail account {account_id} has invalid protected credentials",
    ):
        resolve_gmail_access_token(store, secret_manager, gmail_account_id=account_id)


def test_ingest_gmail_message_record_writes_rfc822_artifact_and_reuses_artifact_seam(
    monkeypatch,
    tmp_path,
) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace = store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str((tmp_path / "workspace").resolve()),
    )
    account = create_gmail_account_record(
        store,
        secret_manager,
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
        secret_manager,
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
    assert store.operations[:2] == [
        ("create_gmail_account_credential", UUID(account["id"])),
        ("get_gmail_account_credential_optional", UUID(account["id"])),
    ]


def test_ingest_gmail_message_record_renews_expired_access_token_before_fetch(
    monkeypatch,
    tmp_path,
) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace = store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str((tmp_path / "workspace").resolve()),
    )
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-expired",
            refresh_token="refresh-1",
            client_id="client-1",
            client_secret="secret-1",
            access_token_expires_at=datetime(2020, 1, 1, 0, 0, tzinfo=UTC),
        ),
    )["account"]
    raw_bytes = _build_rfc822_email_bytes(plain_body="hello from gmail")
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "alicebot_api.gmail.refresh_gmail_access_token",
        lambda **_kwargs: RefreshedGmailCredential(
            access_token="token-refreshed",
            access_token_expires_at=datetime(2030, 1, 1, 0, 5, tzinfo=UTC),
        ),
    )

    def fake_fetch(**kwargs):
        calls["fetch_access_token"] = kwargs["access_token"]
        return raw_bytes

    monkeypatch.setattr("alicebot_api.gmail.fetch_gmail_message_raw_bytes", fake_fetch)

    monkeypatch.setattr(
        "alicebot_api.gmail.register_task_artifact_record",
        lambda _store, *, user_id, request: {
            "artifact": {
                "id": "00000000-0000-0000-0000-000000000123",
                "task_id": str(workspace["task_id"]),
                "task_workspace_id": str(workspace_id),
                "status": "registered",
                "ingestion_status": "pending",
                "relative_path": Path(request.local_path)
                .relative_to(Path(workspace["local_path"]))
                .as_posix(),
                "media_type_hint": "message/rfc822",
                "created_at": "2026-03-16T10:00:00+00:00",
                "updated_at": "2026-03-16T10:00:00+00:00",
            }
        },
    )
    monkeypatch.setattr(
        "alicebot_api.gmail.ingest_task_artifact_record",
        lambda _store, *, user_id, request: {
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
        },
    )

    response = ingest_gmail_message_record(
        store,
        secret_manager,
        user_id=user_id,
        request=GmailMessageIngestInput(
            gmail_account_id=UUID(account["id"]),
            task_workspace_id=workspace_id,
            provider_message_id="msg-001",
        ),
    )

    assert response["message"]["artifact_relative_path"] == "gmail/acct-001/msg-001.eml"
    assert calls["fetch_access_token"] == "token-refreshed"
    assert store.operations[:3] == [
        ("create_gmail_account_credential", UUID(account["id"])),
        ("get_gmail_account_credential_optional", UUID(account["id"])),
        ("update_gmail_account_credential", UUID(account["id"])),
    ]


def test_ingest_gmail_message_record_rejects_unsupported_message(monkeypatch, tmp_path) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    workspace_id = uuid4()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str((tmp_path / "workspace").resolve()),
    )
    account = create_gmail_account_record(
        store,
        secret_manager,
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
            secret_manager,
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
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace_path = (tmp_path / "workspace").resolve()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str(workspace_path),
    )
    account = create_gmail_account_record(
        store,
        secret_manager,
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
            secret_manager,
            user_id=user_id,
            request=GmailMessageIngestInput(
                gmail_account_id=UUID(account["id"]),
                task_workspace_id=workspace_id,
                provider_message_id="msg:001",
            ),
        )

    assert existing_file.read_bytes() == b"original"
    assert store.operations[-3:] == [
        ("get_gmail_account_credential_optional", UUID(account["id"])),
        ("lock_task_artifacts", workspace_id),
        ("get_task_artifact_by_workspace_relative_path_optional", workspace_id),
    ]


def test_ingest_gmail_message_record_requires_visible_workspace(monkeypatch) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    account = create_gmail_account_record(
        store,
        secret_manager,
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
            secret_manager,
            user_id=user_id,
            request=GmailMessageIngestInput(
                gmail_account_id=UUID(account["id"]),
                task_workspace_id=uuid4(),
                provider_message_id="msg-001",
            ),
        )


def test_ingest_gmail_message_record_rejects_missing_protected_credentials_before_artifact_work(
    monkeypatch,
    tmp_path,
) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace_path = (tmp_path / "workspace").resolve()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str(workspace_path),
    )
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    account_id = UUID(account["id"])
    store.gmail_account_credentials.pop(account_id)

    def fail_fetch(**_kwargs):
        raise AssertionError("fetch_gmail_message_raw_bytes should not be called")

    monkeypatch.setattr("alicebot_api.gmail.fetch_gmail_message_raw_bytes", fail_fetch)

    with pytest.raises(
        GmailCredentialNotFoundError,
        match=f"gmail account {account_id} is missing protected credentials",
    ):
        ingest_gmail_message_record(
            store,
            secret_manager,
            user_id=user_id,
            request=GmailMessageIngestInput(
                gmail_account_id=account_id,
                task_workspace_id=workspace_id,
                provider_message_id="msg-001",
            ),
        )

    assert store.task_artifacts == []
    assert not workspace_path.exists()
    assert ("lock_task_artifacts", workspace_id) not in store.operations


def test_ingest_gmail_message_record_rejects_invalid_protected_credentials_before_artifact_work(
    monkeypatch,
    tmp_path,
) -> None:
    store = GmailStoreStub()
    secret_manager = GmailSecretManagerStub()
    user_id = uuid4()
    workspace_id = uuid4()
    workspace_path = (tmp_path / "workspace").resolve()
    store.create_task_workspace(
        task_workspace_id=workspace_id,
        local_path=str(workspace_path),
    )
    account = create_gmail_account_record(
        store,
        secret_manager,
        user_id=user_id,
        request=GmailAccountConnectInput(
            provider_account_id="acct-001",
            email_address="owner@example.com",
            display_name="Owner",
            scope=GMAIL_READONLY_SCOPE,
            access_token="token-1",
        ),
    )["account"]
    account_id = UUID(account["id"])
    secret_ref = store.gmail_account_credentials[account_id]["secret_ref"]
    assert secret_ref is not None
    secret_manager.secrets[secret_ref] = {
        "credential_kind": GMAIL_PROTECTED_CREDENTIAL_KIND,
        "access_token": "",
    }

    def fail_fetch(**_kwargs):
        raise AssertionError("fetch_gmail_message_raw_bytes should not be called")

    monkeypatch.setattr("alicebot_api.gmail.fetch_gmail_message_raw_bytes", fail_fetch)

    with pytest.raises(
        GmailCredentialInvalidError,
        match=f"gmail account {account_id} has invalid protected credentials",
    ):
        ingest_gmail_message_record(
            store,
            secret_manager,
            user_id=user_id,
            request=GmailMessageIngestInput(
                gmail_account_id=account_id,
                task_workspace_id=workspace_id,
                provider_message_id="msg-001",
            ),
        )

    assert store.task_artifacts == []
    assert not workspace_path.exists()
    assert ("lock_task_artifacts", workspace_id) not in store.operations
