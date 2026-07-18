from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sys as _sys
from typing import TypedDict
from uuid import UUID

from alicebot_api._contracts.common import DEFAULT_CALENDAR_EVENT_LIST_LIMIT
from alicebot_api._contracts.tasks import TaskArtifactChunkListSummary, TaskArtifactRecord


_CARRIER_MODULE_NAME = __name__
_CONTRACTS_MODULE_WAS_PRESENT = "alicebot_api.contracts" in _sys.modules
if not _CONTRACTS_MODULE_WAS_PRESENT:
    _sys.modules["alicebot_api.contracts"] = _sys.modules[__name__]
__name__ = "alicebot_api.contracts"


@dataclass(frozen=True, slots=True)
class GmailAccountConnectInput:
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    access_token: str
    refresh_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    access_token_expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class GmailMessageIngestInput:
    gmail_account_id: UUID
    task_workspace_id: UUID
    provider_message_id: str


class GmailAccountRecord(TypedDict):
    id: str
    provider: str
    auth_kind: str
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: str
    updated_at: str


class GmailAccountConnectResponse(TypedDict):
    account: GmailAccountRecord


class GmailAccountListSummary(TypedDict):
    total_count: int
    order: list[str]


class GmailAccountListResponse(TypedDict):
    items: list[GmailAccountRecord]
    summary: GmailAccountListSummary


class GmailAccountDetailResponse(TypedDict):
    account: GmailAccountRecord


class GmailMessageIngestionRecord(TypedDict):
    provider_message_id: str
    artifact_relative_path: str
    media_type: str


class GmailMessageIngestionResponse(TypedDict):
    account: GmailAccountRecord
    message: GmailMessageIngestionRecord
    artifact: TaskArtifactRecord
    summary: TaskArtifactChunkListSummary


@dataclass(frozen=True, slots=True)
class CalendarAccountConnectInput:
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    access_token: str


@dataclass(frozen=True, slots=True)
class CalendarEventIngestInput:
    calendar_account_id: UUID
    task_workspace_id: UUID
    provider_event_id: str


@dataclass(frozen=True, slots=True)
class CalendarEventListInput:
    calendar_account_id: UUID
    limit: int = DEFAULT_CALENDAR_EVENT_LIST_LIMIT
    time_min: datetime | None = None
    time_max: datetime | None = None


class CalendarAccountRecord(TypedDict):
    id: str
    provider: str
    auth_kind: str
    provider_account_id: str
    email_address: str
    display_name: str | None
    scope: str
    created_at: str
    updated_at: str


class CalendarAccountConnectResponse(TypedDict):
    account: CalendarAccountRecord


class CalendarAccountListSummary(TypedDict):
    total_count: int
    order: list[str]


class CalendarAccountListResponse(TypedDict):
    items: list[CalendarAccountRecord]
    summary: CalendarAccountListSummary


class CalendarAccountDetailResponse(TypedDict):
    account: CalendarAccountRecord


class CalendarEventIngestionRecord(TypedDict):
    provider_event_id: str
    artifact_relative_path: str
    media_type: str


class CalendarEventIngestionResponse(TypedDict):
    account: CalendarAccountRecord
    event: CalendarEventIngestionRecord
    artifact: TaskArtifactRecord
    summary: TaskArtifactChunkListSummary


class CalendarEventSummaryRecord(TypedDict):
    provider_event_id: str
    status: str | None
    summary: str | None
    start_time: str | None
    end_time: str | None
    html_link: str | None
    updated_at: str | None


class CalendarEventListSummary(TypedDict):
    total_count: int
    limit: int
    order: list[str]
    time_min: str | None
    time_max: str | None


class CalendarEventListResponse(TypedDict):
    account: CalendarAccountRecord
    items: list[CalendarEventSummaryRecord]
    summary: CalendarEventListSummary


__name__ = _CARRIER_MODULE_NAME
if not _CONTRACTS_MODULE_WAS_PRESENT:
    del _sys.modules["alicebot_api.contracts"]
