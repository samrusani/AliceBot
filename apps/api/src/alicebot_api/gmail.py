from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID

import psycopg

from alicebot_api.artifacts import (
    SUPPORTED_RFC822_ARTIFACT_MEDIA_TYPE,
    TaskArtifactAlreadyExistsError,
    TaskArtifactValidationError,
    ensure_artifact_path_is_rooted,
    extract_artifact_text_from_bytes,
    ingest_task_artifact_record,
    register_task_artifact_record,
)
from alicebot_api.contracts import (
    GMAIL_ACCOUNT_LIST_ORDER,
    GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN,
    GMAIL_PROTECTED_CREDENTIAL_KIND,
    GMAIL_PROVIDER,
    GMAIL_READONLY_SCOPE,
    GmailAccountConnectInput,
    GmailAccountConnectResponse,
    GmailAccountDetailResponse,
    GmailAccountListResponse,
    GmailAccountRecord,
    GmailMessageIngestInput,
    GmailMessageIngestionResponse,
    TaskArtifactIngestInput,
    TaskArtifactRegisterInput,
)
from alicebot_api.store import ContinuityStore, GmailAccountRow
from alicebot_api.workspaces import TaskWorkspaceNotFoundError

GMAIL_MESSAGE_FETCH_TIMEOUT_SECONDS = 30
GMAIL_MESSAGE_ARTIFACT_ROOT = "gmail"
_PATH_SEGMENT_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class GmailAccountNotFoundError(LookupError):
    """Raised when a Gmail account is not visible inside the current user scope."""


class GmailAccountAlreadyExistsError(RuntimeError):
    """Raised when the same provider account is connected twice for one user."""


class GmailMessageNotFoundError(LookupError):
    """Raised when a Gmail message cannot be found in the current account."""


class GmailMessageUnsupportedError(ValueError):
    """Raised when Gmail content cannot be converted into the RFC822 artifact seam."""


class GmailMessageFetchError(RuntimeError):
    """Raised when the Gmail API call fails for non-deterministic upstream reasons."""


class GmailCredentialNotFoundError(RuntimeError):
    """Raised when Gmail protected credentials are missing for a visible account."""


class GmailCredentialInvalidError(RuntimeError):
    """Raised when Gmail protected credentials are malformed for a visible account."""


def serialize_gmail_account_row(row: GmailAccountRow) -> GmailAccountRecord:
    return {
        "id": str(row["id"]),
        "provider": GMAIL_PROVIDER,
        "auth_kind": GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN,
        "provider_account_id": row["provider_account_id"],
        "email_address": row["email_address"],
        "display_name": row["display_name"],
        "scope": row["scope"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def build_gmail_protected_credential_blob(*, access_token: str) -> dict[str, str]:
    return {
        "credential_kind": GMAIL_PROTECTED_CREDENTIAL_KIND,
        "access_token": access_token,
    }


def resolve_gmail_access_token(
    store: ContinuityStore,
    *,
    gmail_account_id: UUID,
) -> str:
    credential = store.get_gmail_account_credential_optional(gmail_account_id)
    if credential is None:
        raise GmailCredentialNotFoundError(
            f"gmail account {gmail_account_id} is missing protected credentials"
        )

    if credential["auth_kind"] != GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN:
        raise GmailCredentialInvalidError(
            f"gmail account {gmail_account_id} has invalid protected credentials"
        )

    credential_blob = credential["credential_blob"]
    if not isinstance(credential_blob, dict):
        raise GmailCredentialInvalidError(
            f"gmail account {gmail_account_id} has invalid protected credentials"
        )

    credential_kind = credential_blob.get("credential_kind")
    access_token = credential_blob.get("access_token")
    if (
        credential_kind != GMAIL_PROTECTED_CREDENTIAL_KIND
        or not isinstance(access_token, str)
        or access_token == ""
    ):
        raise GmailCredentialInvalidError(
            f"gmail account {gmail_account_id} has invalid protected credentials"
        )

    return access_token


def create_gmail_account_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: GmailAccountConnectInput,
) -> GmailAccountConnectResponse:
    del user_id

    existing = store.get_gmail_account_by_provider_account_id_optional(request.provider_account_id)
    if existing is not None:
        raise GmailAccountAlreadyExistsError(
            f"gmail account {request.provider_account_id} is already connected"
        )

    try:
        row = store.create_gmail_account(
            provider_account_id=request.provider_account_id,
            email_address=request.email_address,
            display_name=request.display_name,
            scope=request.scope,
        )
        store.create_gmail_account_credential(
            gmail_account_id=row["id"],
            auth_kind=GMAIL_AUTH_KIND_OAUTH_ACCESS_TOKEN,
            credential_blob=build_gmail_protected_credential_blob(
                access_token=request.access_token,
            ),
        )
    except psycopg.errors.UniqueViolation as exc:
        raise GmailAccountAlreadyExistsError(
            f"gmail account {request.provider_account_id} is already connected"
        ) from exc

    return {"account": serialize_gmail_account_row(row)}


def list_gmail_account_records(
    store: ContinuityStore,
    *,
    user_id: UUID,
) -> GmailAccountListResponse:
    del user_id

    items = [serialize_gmail_account_row(row) for row in store.list_gmail_accounts()]
    return {
        "items": items,
        "summary": {
            "total_count": len(items),
            "order": list(GMAIL_ACCOUNT_LIST_ORDER),
        },
    }


def get_gmail_account_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    gmail_account_id: UUID,
) -> GmailAccountDetailResponse:
    del user_id

    row = store.get_gmail_account_optional(gmail_account_id)
    if row is None:
        raise GmailAccountNotFoundError(f"gmail account {gmail_account_id} was not found")
    return {"account": serialize_gmail_account_row(row)}


def _sanitize_path_segment(value: str) -> str:
    sanitized = _PATH_SEGMENT_PATTERN.sub("_", value.strip())
    return sanitized.strip("._") or "message"


def build_gmail_message_artifact_relative_path(
    *,
    provider_account_id: str,
    provider_message_id: str,
) -> str:
    return (
        f"{GMAIL_MESSAGE_ARTIFACT_ROOT}/"
        f"{_sanitize_path_segment(provider_account_id)}/"
        f"{_sanitize_path_segment(provider_message_id)}.eml"
    )


def fetch_gmail_message_raw_bytes(*, access_token: str, provider_message_id: str) -> bytes:
    request = Request(
        (
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/"
            f"{quote(provider_message_id, safe='')}?format=raw"
        ),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=GMAIL_MESSAGE_FETCH_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            raise GmailMessageNotFoundError(
                f"gmail message {provider_message_id} was not found"
            ) from exc
        raise GmailMessageFetchError(
            f"gmail message {provider_message_id} could not be fetched"
        ) from exc
    except (OSError, URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GmailMessageFetchError(
            f"gmail message {provider_message_id} could not be fetched"
        ) from exc

    raw_payload = payload.get("raw")
    if not isinstance(raw_payload, str) or raw_payload == "":
        raise GmailMessageUnsupportedError(
            f"gmail message {provider_message_id} did not include RFC822 raw content"
        )

    padding = "=" * (-len(raw_payload) % 4)
    try:
        return base64.urlsafe_b64decode(raw_payload + padding)
    except (ValueError, TypeError) as exc:
        raise GmailMessageUnsupportedError(
            f"gmail message {provider_message_id} did not include valid RFC822 raw content"
        ) from exc


def ingest_gmail_message_record(
    store: ContinuityStore,
    *,
    user_id: UUID,
    request: GmailMessageIngestInput,
) -> GmailMessageIngestionResponse:
    account = store.get_gmail_account_optional(request.gmail_account_id)
    if account is None:
        raise GmailAccountNotFoundError(f"gmail account {request.gmail_account_id} was not found")

    workspace = store.get_task_workspace_optional(request.task_workspace_id)
    if workspace is None:
        raise TaskWorkspaceNotFoundError(
            f"task workspace {request.task_workspace_id} was not found"
        )

    access_token = resolve_gmail_access_token(
        store,
        gmail_account_id=request.gmail_account_id,
    )

    store.lock_task_artifacts(workspace["id"])
    relative_path = build_gmail_message_artifact_relative_path(
        provider_account_id=account["provider_account_id"],
        provider_message_id=request.provider_message_id,
    )
    existing_artifact = store.get_task_artifact_by_workspace_relative_path_optional(
        task_workspace_id=request.task_workspace_id,
        relative_path=relative_path,
    )
    if existing_artifact is not None:
        raise TaskArtifactAlreadyExistsError(
            f"artifact {relative_path} is already registered for task workspace {request.task_workspace_id}"
        )

    raw_bytes = fetch_gmail_message_raw_bytes(
        access_token=access_token,
        provider_message_id=request.provider_message_id,
    )

    try:
        extract_artifact_text_from_bytes(
            relative_path=relative_path,
            payload=raw_bytes,
            media_type=SUPPORTED_RFC822_ARTIFACT_MEDIA_TYPE,
        )
    except TaskArtifactValidationError as exc:
        raise GmailMessageUnsupportedError(
            f"gmail message {request.provider_message_id} is not a supported RFC822 email"
        ) from exc

    workspace_path = Path(workspace["local_path"]).expanduser().resolve()
    artifact_path = (workspace_path / relative_path).resolve()
    ensure_artifact_path_is_rooted(
        workspace_path=workspace_path,
        artifact_path=artifact_path,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        raise TaskArtifactValidationError(
            f"artifact path {artifact_path} already exists before Gmail ingestion registration"
        )
    artifact_path.write_bytes(raw_bytes)

    artifact_payload = register_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactRegisterInput(
            task_workspace_id=request.task_workspace_id,
            local_path=str(artifact_path),
            media_type_hint=SUPPORTED_RFC822_ARTIFACT_MEDIA_TYPE,
        ),
    )
    ingestion_payload = ingest_task_artifact_record(
        store,
        user_id=user_id,
        request=TaskArtifactIngestInput(task_artifact_id=UUID(artifact_payload["artifact"]["id"])),
    )
    return {
        "account": serialize_gmail_account_row(account),
        "message": {
            "provider_message_id": request.provider_message_id,
            "artifact_relative_path": ingestion_payload["artifact"]["relative_path"],
            "media_type": SUPPORTED_RFC822_ARTIFACT_MEDIA_TYPE,
        },
        "artifact": ingestion_payload["artifact"],
        "summary": ingestion_payload["summary"],
    }
