from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypedDict
from uuid import UUID

from psycopg.types.json import Jsonb


HostedFlowKind = Literal["chat_handle", "scheduler_daily_brief", "scheduler_open_loop_prompt"]
HostedTelemetryEventKind = Literal[
    "attempt",
    "result",
    "rollout_block",
    "rate_limited",
    "abuse_block",
    "incident",
]
HostedTelemetryStatus = Literal[
    "ok",
    "failed",
    "blocked_rollout",
    "rate_limited",
    "abuse_blocked",
    "suppressed",
    "simulated",
    "delivered",
]


class ChatTelemetryRow(TypedDict):
    id: UUID
    user_account_id: UUID
    workspace_id: UUID | None
    channel_message_id: UUID | None
    daily_brief_job_id: UUID | None
    delivery_receipt_id: UUID | None
    flow_kind: HostedFlowKind
    event_kind: HostedTelemetryEventKind
    status: HostedTelemetryStatus
    route_path: str
    rollout_flag_key: str | None
    rollout_flag_state: str | None
    rate_limit_key: str | None
    rate_limit_window_seconds: int | None
    rate_limit_max_requests: int | None
    retry_after_seconds: int | None
    abuse_signal: str | None
    evidence: dict[str, Any]
    created_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def record_chat_telemetry(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID | None,
    flow_kind: HostedFlowKind,
    event_kind: HostedTelemetryEventKind,
    status: HostedTelemetryStatus,
    route_path: str,
    channel_message_id: UUID | None = None,
    daily_brief_job_id: UUID | None = None,
    delivery_receipt_id: UUID | None = None,
    rollout_flag_key: str | None = None,
    rollout_flag_state: str | None = None,
    rate_limit_key: str | None = None,
    rate_limit_window_seconds: int | None = None,
    rate_limit_max_requests: int | None = None,
    retry_after_seconds: int | None = None,
    abuse_signal: str | None = None,
    evidence: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> ChatTelemetryRow:
    normalized_route_path = route_path.strip()
    if normalized_route_path == "":
        raise ValueError("route_path is required for chat telemetry")

    timestamp = utc_now() if created_at is None else created_at

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_telemetry (
              user_account_id,
              workspace_id,
              channel_message_id,
              daily_brief_job_id,
              delivery_receipt_id,
              flow_kind,
              event_kind,
              status,
              route_path,
              rollout_flag_key,
              rollout_flag_state,
              rate_limit_key,
              rate_limit_window_seconds,
              rate_limit_max_requests,
              retry_after_seconds,
              abuse_signal,
              evidence,
              created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id,
                      user_account_id,
                      workspace_id,
                      channel_message_id,
                      daily_brief_job_id,
                      delivery_receipt_id,
                      flow_kind,
                      event_kind,
                      status,
                      route_path,
                      rollout_flag_key,
                      rollout_flag_state,
                      rate_limit_key,
                      rate_limit_window_seconds,
                      rate_limit_max_requests,
                      retry_after_seconds,
                      abuse_signal,
                      evidence,
                      created_at
            """,
            (
                user_account_id,
                workspace_id,
                channel_message_id,
                daily_brief_job_id,
                delivery_receipt_id,
                flow_kind,
                event_kind,
                status,
                normalized_route_path,
                rollout_flag_key,
                rollout_flag_state,
                rate_limit_key,
                rate_limit_window_seconds,
                rate_limit_max_requests,
                retry_after_seconds,
                abuse_signal,
                Jsonb(evidence or {}),
                timestamp,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to persist hosted chat telemetry")
    return row


def serialize_chat_telemetry(row: ChatTelemetryRow) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "user_account_id": str(row["user_account_id"]),
        "workspace_id": None if row["workspace_id"] is None else str(row["workspace_id"]),
        "channel_message_id": None if row["channel_message_id"] is None else str(row["channel_message_id"]),
        "daily_brief_job_id": None if row["daily_brief_job_id"] is None else str(row["daily_brief_job_id"]),
        "delivery_receipt_id": None
        if row["delivery_receipt_id"] is None
        else str(row["delivery_receipt_id"]),
        "flow_kind": row["flow_kind"],
        "event_kind": row["event_kind"],
        "status": row["status"],
        "route_path": row["route_path"],
        "rollout_flag_key": row["rollout_flag_key"],
        "rollout_flag_state": row["rollout_flag_state"],
        "rate_limit_key": row["rate_limit_key"],
        "rate_limit_window_seconds": row["rate_limit_window_seconds"],
        "rate_limit_max_requests": row["rate_limit_max_requests"],
        "retry_after_seconds": row["retry_after_seconds"],
        "abuse_signal": row["abuse_signal"],
        "evidence": row["evidence"],
        "created_at": row["created_at"].isoformat(),
    }


def list_recent_chat_telemetry(
    conn,
    *,
    limit: int,
    workspace_id: UUID | None = None,
) -> list[ChatTelemetryRow]:
    bounded_limit = max(1, min(limit, 200))

    with conn.cursor() as cur:
        if workspace_id is None:
            cur.execute(
                """
                SELECT id,
                       user_account_id,
                       workspace_id,
                       channel_message_id,
                       daily_brief_job_id,
                       delivery_receipt_id,
                       flow_kind,
                       event_kind,
                       status,
                       route_path,
                       rollout_flag_key,
                       rollout_flag_state,
                       rate_limit_key,
                       rate_limit_window_seconds,
                       rate_limit_max_requests,
                       retry_after_seconds,
                       abuse_signal,
                       evidence,
                       created_at
                FROM chat_telemetry
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (bounded_limit,),
            )
        else:
            cur.execute(
                """
                SELECT id,
                       user_account_id,
                       workspace_id,
                       channel_message_id,
                       daily_brief_job_id,
                       delivery_receipt_id,
                       flow_kind,
                       event_kind,
                       status,
                       route_path,
                       rollout_flag_key,
                       rollout_flag_state,
                       rate_limit_key,
                       rate_limit_window_seconds,
                       rate_limit_max_requests,
                       retry_after_seconds,
                       abuse_signal,
                       evidence,
                       created_at
                FROM chat_telemetry
                WHERE workspace_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (workspace_id, bounded_limit),
            )
        rows = cur.fetchall()

    return rows


def aggregate_chat_telemetry(
    conn,
    *,
    window_hours: int,
) -> dict[str, object]:
    bounded_hours = max(1, min(window_hours, 168))
    start_at = utc_now() - timedelta(hours=bounded_hours)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT flow_kind,
                   status,
                   count(*) AS total_count
            FROM chat_telemetry
            WHERE created_at >= %s
            GROUP BY flow_kind, status
            ORDER BY flow_kind ASC, status ASC
            """,
            (start_at,),
        )
        rows = cur.fetchall()

    flow_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    matrix: dict[str, dict[str, int]] = {}

    for row in rows:
        flow_kind = str(row["flow_kind"])
        status = str(row["status"])
        count = int(row["total_count"])

        flow_counts[flow_kind] = flow_counts.get(flow_kind, 0) + count
        status_counts[status] = status_counts.get(status, 0) + count

        bucket = matrix.setdefault(flow_kind, {})
        bucket[status] = count

    total_events = sum(status_counts.values())

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT date_trunc('hour', created_at) AS hour_bucket,
                   count(*) AS total_count,
                   count(*) FILTER (WHERE status = 'ok') AS ok_count,
                   count(*) FILTER (WHERE status = 'failed') AS failed_count,
                   count(*) FILTER (WHERE status = 'blocked_rollout') AS blocked_rollout_count,
                   count(*) FILTER (WHERE status = 'rate_limited') AS rate_limited_count,
                   count(*) FILTER (WHERE status = 'abuse_blocked') AS abuse_blocked_count
            FROM chat_telemetry
            WHERE created_at >= %s
            GROUP BY hour_bucket
            ORDER BY hour_bucket DESC
            LIMIT 48
            """,
            (start_at,),
        )
        hourly_rows = cur.fetchall()

    hourly: list[dict[str, object]] = []
    for row in hourly_rows:
        hourly.append(
            {
                "hour": row["hour_bucket"].isoformat(),
                "total_count": int(row["total_count"]),
                "ok_count": int(row["ok_count"]),
                "failed_count": int(row["failed_count"]),
                "blocked_rollout_count": int(row["blocked_rollout_count"]),
                "rate_limited_count": int(row["rate_limited_count"]),
                "abuse_blocked_count": int(row["abuse_blocked_count"]),
            }
        )

    return {
        "window_hours": bounded_hours,
        "window_start": start_at.isoformat(),
        "total_events": total_events,
        "flow_counts": flow_counts,
        "status_counts": status_counts,
        "flow_status_matrix": matrix,
        "hourly": hourly,
    }
