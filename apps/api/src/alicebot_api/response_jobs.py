from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from typing import TypedDict, cast
from uuid import UUID

from psycopg.types.json import Jsonb

from alicebot_api.db import UserConnection
from alicebot_api.store import JsonObject


RESPONSE_JOB_ENDPOINT_RUNTIME = "v1_runtime_invoke"
RESPONSE_JOB_LEASE_SECONDS = 30 * 60
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~:+/=-]{1,200}$")


class ResponseGenerationJobRow(TypedDict):
    id: UUID
    user_id: UUID
    workspace_id: UUID | None
    endpoint: str
    idempotency_key_hash: str
    idempotency_key_preview: str
    request_fingerprint_sha256: str
    state: str
    lease_token: UUID | None
    lease_expires_at: datetime | None
    provider_call_started_at: datetime | None
    user_event_id: UUID | None
    user_event_sequence_no: int | None
    response_status_code: int | None
    response_payload: JsonObject | None
    error_payload: JsonObject | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResponseJobFenceLostError(RuntimeError):
    """Raised when a stale worker attempts to finalize a response job."""


@dataclass(frozen=True, slots=True)
class ResponseJobLookup:
    job: ResponseGenerationJobRow
    created: bool


_RETURNING_COLUMNS = """
    id,
    user_id,
    workspace_id,
    endpoint,
    idempotency_key_hash,
    idempotency_key_preview,
    request_fingerprint_sha256,
    state,
    lease_token,
    lease_expires_at,
    provider_call_started_at,
    user_event_id,
    user_event_sequence_no,
    response_status_code,
    response_payload,
    error_payload,
    completed_at,
    created_at,
    updated_at
"""


def normalize_idempotency_key(value: str | None) -> str:
    key = "" if value is None else value.strip()
    if not _IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
        raise ValueError(
            "Idempotency-Key is required and must contain 1-200 URL-safe visible characters"
        )
    return key


def idempotency_key_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_fingerprint(payload: JsonObject) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ResponseGenerationJobStore:
    def __init__(self, conn: UserConnection):
        self.conn = conn

    def create_or_get_for_update(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None,
        endpoint: str,
        idempotency_key: str,
        request_fingerprint_sha256: str,
    ) -> ResponseJobLookup:
        key_hash = idempotency_key_hash(idempotency_key)
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO response_generation_jobs (
                  user_id,
                  workspace_id,
                  endpoint,
                  idempotency_key_hash,
                  idempotency_key_preview,
                  request_fingerprint_sha256
                )
                VALUES (app.current_user_id(), %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, endpoint, idempotency_key_hash) DO NOTHING
                RETURNING {_RETURNING_COLUMNS}
                """,
                (
                    workspace_id,
                    endpoint,
                    key_hash,
                    idempotency_key[:12],
                    request_fingerprint_sha256,
                ),
            )
            row = cur.fetchone()
            if row is not None:
                if row["user_id"] != user_id:
                    raise RuntimeError("response job tenant identity did not match the request")
                return ResponseJobLookup(
                    job=cast(ResponseGenerationJobRow, row),
                    created=True,
                )
            cur.execute(
                f"""
                SELECT {_RETURNING_COLUMNS}
                FROM response_generation_jobs
                WHERE user_id = app.current_user_id()
                  AND endpoint = %s
                  AND idempotency_key_hash = %s
                FOR UPDATE
                """,
                (endpoint, key_hash),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("response job conflict row was not visible")
        return ResponseJobLookup(
            job=cast(ResponseGenerationJobRow, row),
            created=False,
        )

    def get_for_update(
        self,
        *,
        user_id: UUID,
        endpoint: str,
        idempotency_key: str,
    ) -> ResponseGenerationJobRow | None:
        """Lock an existing request identity without creating mutable work.

        This lookup lets API entrypoints replay terminal jobs before resolving
        provider credentials or any other mutable runtime configuration.
        """

        key_hash = idempotency_key_hash(idempotency_key)
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {_RETURNING_COLUMNS}
                FROM response_generation_jobs
                WHERE user_id = app.current_user_id()
                  AND endpoint = %s
                  AND idempotency_key_hash = %s
                FOR UPDATE
                """,
                (endpoint, key_hash),
            )
            row = cur.fetchone()
        if row is None:
            return None
        if row["user_id"] != user_id:
            raise RuntimeError("response job tenant identity did not match the request")
        return cast(ResponseGenerationJobRow, row)

    def claim_pending(
        self,
        *,
        job_id: UUID,
        lease_token: UUID,
        lease_seconds: int,
        user_event_id: UUID,
        user_event_sequence_no: int,
    ) -> ResponseGenerationJobRow:
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE response_generation_jobs
                SET state = 'running',
                    lease_token = %s,
                    lease_expires_at = clock_timestamp() + make_interval(secs => %s),
                    provider_call_started_at = clock_timestamp(),
                    user_event_id = %s,
                    user_event_sequence_no = %s,
                    updated_at = clock_timestamp()
                WHERE id = %s
                  AND user_id = app.current_user_id()
                  AND state = 'pending'
                RETURNING {_RETURNING_COLUMNS}
                """,
                (
                    lease_token,
                    lease_seconds,
                    user_event_id,
                    user_event_sequence_no,
                    job_id,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise ResponseJobFenceLostError("response job could not be claimed from pending state")
        return cast(ResponseGenerationJobRow, row)

    def fail_pending(
        self,
        *,
        job_id: UUID,
        status_code: int,
        error_payload: JsonObject,
    ) -> ResponseGenerationJobRow:
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE response_generation_jobs
                SET state = 'failed',
                    response_status_code = %s,
                    error_payload = %s,
                    completed_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = %s
                  AND user_id = app.current_user_id()
                  AND state = 'pending'
                RETURNING {_RETURNING_COLUMNS}
                """,
                (status_code, Jsonb(error_payload), job_id),
            )
            row = cur.fetchone()
        if row is None:
            raise ResponseJobFenceLostError("pending response job failure lost its state fence")
        return cast(ResponseGenerationJobRow, row)

    def finalize(
        self,
        *,
        job_id: UUID,
        lease_token: UUID,
        state: str,
        status_code: int,
        payload: JsonObject,
    ) -> ResponseGenerationJobRow:
        if state not in {"succeeded", "failed"}:
            raise ValueError("response job terminal state must be succeeded or failed")
        response_payload = payload if state == "succeeded" else None
        error_payload = payload if state == "failed" else None
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE response_generation_jobs
                SET state = %s,
                    response_status_code = %s,
                    response_payload = %s,
                    error_payload = %s,
                    completed_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = %s
                  AND user_id = app.current_user_id()
                  AND state = 'running'
                  AND lease_token = %s
                RETURNING {_RETURNING_COLUMNS}
                """,
                (
                    state,
                    status_code,
                    None if response_payload is None else Jsonb(response_payload),
                    None if error_payload is None else Jsonb(error_payload),
                    job_id,
                    lease_token,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise ResponseJobFenceLostError("response job finalization lost its lease fence")
        return cast(ResponseGenerationJobRow, row)

    def fail_if_abandoned(
        self,
        *,
        job_id: UUID,
        error_payload: JsonObject,
    ) -> ResponseGenerationJobRow | None:
        """Fail closed after an expired provider fence; never re-invoke the provider."""

        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE response_generation_jobs
                SET state = 'failed',
                    response_status_code = 503,
                    error_payload = %s,
                    completed_at = clock_timestamp(),
                    updated_at = clock_timestamp()
                WHERE id = %s
                  AND user_id = app.current_user_id()
                  AND state = 'running'
                  AND lease_expires_at <= clock_timestamp()
                RETURNING {_RETURNING_COLUMNS}
                """,
                (Jsonb(error_payload), job_id),
            )
            return cast(ResponseGenerationJobRow | None, cur.fetchone())


__all__ = [
    "RESPONSE_JOB_ENDPOINT_RUNTIME",
    "RESPONSE_JOB_LEASE_SECONDS",
    "ResponseGenerationJobRow",
    "ResponseGenerationJobStore",
    "ResponseJobFenceLostError",
    "ResponseJobLookup",
    "normalize_idempotency_key",
    "request_fingerprint",
]
