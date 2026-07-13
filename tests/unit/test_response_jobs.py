from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb
import pytest

from alicebot_api.response_jobs import (
    RESPONSE_JOB_ENDPOINT_V0,
    ResponseGenerationJobStore,
    ResponseJobFenceLostError,
    idempotency_key_hash,
    normalize_idempotency_key,
    request_fingerprint,
)


class RecordingCursor:
    def __init__(self, rows: list[dict[str, Any] | None]) -> None:
        self.rows = list(rows)
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        return self.rows.pop(0) if self.rows else None


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def _job_row(*, state: str = "pending") -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "id": uuid4(),
        "user_id": uuid4(),
        "workspace_id": None,
        "endpoint": RESPONSE_JOB_ENDPOINT_V0,
        "idempotency_key_hash": "a" * 64,
        "idempotency_key_preview": "stable-key",
        "request_fingerprint_sha256": "b" * 64,
        "state": state,
        "lease_token": None,
        "lease_expires_at": None,
        "provider_call_started_at": None,
        "user_event_id": None,
        "user_event_sequence_no": None,
        "response_status_code": None,
        "response_payload": None,
        "error_payload": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }


def test_idempotency_key_and_request_fingerprint_are_canonical() -> None:
    assert normalize_idempotency_key("  stable-key  ") == "stable-key"
    with pytest.raises(ValueError, match="Idempotency-Key is required"):
        normalize_idempotency_key("contains spaces")
    assert idempotency_key_hash("stable-key") == idempotency_key_hash("stable-key")
    assert request_fingerprint({"a": 1, "b": [2, 3]}) == request_fingerprint({"b": [2, 3], "a": 1})


def test_create_or_get_response_job_hashes_key_and_locks_conflict_row() -> None:
    row = _job_row()
    user_id = row["user_id"]
    raw_key = "stable-key-secret-material"
    cursor = RecordingCursor([None, row])
    store = ResponseGenerationJobStore(RecordingConnection(cursor))  # type: ignore[arg-type]

    lookup = store.create_or_get_for_update(
        user_id=user_id,
        workspace_id=None,
        endpoint=RESPONSE_JOB_ENDPOINT_V0,
        idempotency_key=raw_key,
        request_fingerprint_sha256="b" * 64,
    )

    assert lookup.created is False
    assert lookup.job["id"] == row["id"]
    insert_sql, insert_params = cursor.executed[0]
    select_sql, select_params = cursor.executed[1]
    assert "ON CONFLICT (user_id, endpoint, idempotency_key_hash) DO NOTHING" in insert_sql
    assert insert_params is not None
    assert insert_params[2] == idempotency_key_hash(raw_key)
    assert insert_params[3] == raw_key[:12]
    assert raw_key not in insert_params
    assert "FOR UPDATE" in select_sql
    assert select_params == (RESPONSE_JOB_ENDPOINT_V0, idempotency_key_hash(raw_key))


def test_get_response_job_locks_existing_identity_without_creating_work() -> None:
    row = _job_row(state="succeeded")
    raw_key = "stable-runtime-replay-key"
    cursor = RecordingCursor([row])
    store = ResponseGenerationJobStore(RecordingConnection(cursor))  # type: ignore[arg-type]

    existing = store.get_for_update(
        user_id=row["user_id"],
        endpoint=RESPONSE_JOB_ENDPOINT_V0,
        idempotency_key=raw_key,
    )

    assert existing == row
    assert len(cursor.executed) == 1
    sql, params = cursor.executed[0]
    assert sql.lstrip().startswith("SELECT")
    assert "INSERT" not in sql
    assert "FOR UPDATE" in sql
    assert params == (RESPONSE_JOB_ENDPOINT_V0, idempotency_key_hash(raw_key))


def test_finalize_response_job_is_fenced_by_running_state_and_lease_token() -> None:
    row = _job_row(state="succeeded")
    lease_token = uuid4()
    payload = {"status": "ok"}
    cursor = RecordingCursor([row])
    store = ResponseGenerationJobStore(RecordingConnection(cursor))  # type: ignore[arg-type]

    finalized = store.finalize(
        job_id=row["id"],
        lease_token=lease_token,
        state="succeeded",
        status_code=200,
        payload=payload,
    )

    sql, params = cursor.executed[0]
    assert finalized["state"] == "succeeded"
    assert "state = 'running'" in sql
    assert "lease_token = %s" in sql
    assert params is not None
    assert isinstance(params[2], Jsonb)
    assert params[2].obj == payload
    assert params[-1] == lease_token

    stale = ResponseGenerationJobStore(RecordingConnection(RecordingCursor([None])))  # type: ignore[arg-type]
    with pytest.raises(ResponseJobFenceLostError, match="lost its lease fence"):
        stale.finalize(
            job_id=uuid4(),
            lease_token=uuid4(),
            state="failed",
            status_code=502,
            payload={"detail": "failed"},
        )


def test_abandoned_response_job_fails_closed_without_reclaiming_provider_work() -> None:
    job_id: UUID = uuid4()
    row = _job_row(state="failed")
    cursor = RecordingCursor([row])
    store = ResponseGenerationJobStore(RecordingConnection(cursor))  # type: ignore[arg-type]

    abandoned = store.fail_if_abandoned(
        job_id=job_id,
        error_payload={"detail": {"code": "provider_outcome_unknown"}},
    )

    sql, params = cursor.executed[0]
    assert abandoned is not None
    assert "response_status_code = 503" in sql
    assert "state = 'running'" in sql
    assert "lease_expires_at <= clock_timestamp()" in sql
    assert "state = 'pending'" not in sql
    assert params is not None
    assert isinstance(params[0], Jsonb)
    assert params[1] == job_id
