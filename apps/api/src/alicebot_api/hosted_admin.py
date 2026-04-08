from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from alicebot_api.hosted_telemetry import serialize_chat_telemetry


def utc_now() -> datetime:
    return datetime.now(UTC)


def list_hosted_workspaces_for_admin(
    conn,
    *,
    limit: int,
) -> list[dict[str, object]]:
    bounded_limit = max(1, min(limit, 200))

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT w.id,
                   w.owner_user_account_id,
                   w.slug,
                   w.name,
                   w.bootstrap_status,
                   w.bootstrapped_at,
                   w.support_status,
                   w.support_notes,
                   w.onboarding_last_error_code,
                   w.onboarding_last_error_detail,
                   w.onboarding_last_error_at,
                   w.onboarding_error_count,
                   w.rollout_evidence,
                   w.rate_limit_evidence,
                   w.incident_evidence,
                   w.created_at,
                   w.updated_at,
                   count(DISTINCT wm.user_account_id) AS member_count,
                   count(DISTINCT CASE WHEN ci.status = 'linked' THEN ci.id END) AS linked_identity_count,
                   max(cm.created_at) AS last_message_at,
                   max(dr.recorded_at) AS last_delivery_receipt_at
            FROM workspaces AS w
            LEFT JOIN workspace_members AS wm
              ON wm.workspace_id = w.id
            LEFT JOIN channel_identities AS ci
              ON ci.workspace_id = w.id
             AND ci.channel_type = 'telegram'
            LEFT JOIN channel_messages AS cm
              ON cm.workspace_id = w.id
             AND cm.channel_type = 'telegram'
            LEFT JOIN channel_delivery_receipts AS dr
              ON dr.workspace_id = w.id
             AND dr.channel_type = 'telegram'
            GROUP BY w.id
            ORDER BY w.updated_at DESC, w.id DESC
            LIMIT %s
            """,
            (bounded_limit,),
        )
        rows = cur.fetchall()

    payload: list[dict[str, object]] = []
    for row in rows:
        payload.append(
            {
                "id": str(row["id"]),
                "owner_user_account_id": str(row["owner_user_account_id"]),
                "slug": row["slug"],
                "name": row["name"],
                "bootstrap_status": row["bootstrap_status"],
                "bootstrapped_at": None
                if row["bootstrapped_at"] is None
                else row["bootstrapped_at"].isoformat(),
                "support_status": row["support_status"],
                "support_notes": row["support_notes"],
                "onboarding_last_error_code": row["onboarding_last_error_code"],
                "onboarding_last_error_detail": row["onboarding_last_error_detail"],
                "onboarding_last_error_at": None
                if row["onboarding_last_error_at"] is None
                else row["onboarding_last_error_at"].isoformat(),
                "onboarding_error_count": row["onboarding_error_count"],
                "rollout_evidence": row["rollout_evidence"],
                "rate_limit_evidence": row["rate_limit_evidence"],
                "incident_evidence": row["incident_evidence"],
                "member_count": int(row["member_count"]),
                "linked_identity_count": int(row["linked_identity_count"]),
                "last_message_at": None
                if row["last_message_at"] is None
                else row["last_message_at"].isoformat(),
                "last_delivery_receipt_at": None
                if row["last_delivery_receipt_at"] is None
                else row["last_delivery_receipt_at"].isoformat(),
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
        )

    return payload


def list_hosted_delivery_receipts_for_admin(
    conn,
    *,
    limit: int,
    workspace_id: UUID | None = None,
) -> list[dict[str, object]]:
    bounded_limit = max(1, min(limit, 400))

    with conn.cursor() as cur:
        if workspace_id is None:
            cur.execute(
                """
                SELECT r.id,
                       r.workspace_id,
                       r.channel_message_id,
                       r.channel_type,
                       r.status,
                       r.provider_receipt_id,
                       r.failure_code,
                       r.failure_detail,
                       r.scheduled_job_id,
                       r.scheduler_job_kind,
                       r.scheduled_for,
                       r.schedule_slot,
                       r.notification_policy,
                       r.rollout_flag_state,
                       r.support_evidence,
                       r.rate_limit_evidence,
                       r.incident_evidence,
                       r.recorded_at,
                       r.created_at,
                       w.slug AS workspace_slug,
                       w.name AS workspace_name,
                       m.direction AS message_direction
                FROM channel_delivery_receipts AS r
                JOIN workspaces AS w
                  ON w.id = r.workspace_id
                LEFT JOIN channel_messages AS m
                  ON m.id = r.channel_message_id
                WHERE r.channel_type = 'telegram'
                ORDER BY r.recorded_at DESC, r.id DESC
                LIMIT %s
                """,
                (bounded_limit,),
            )
        else:
            cur.execute(
                """
                SELECT r.id,
                       r.workspace_id,
                       r.channel_message_id,
                       r.channel_type,
                       r.status,
                       r.provider_receipt_id,
                       r.failure_code,
                       r.failure_detail,
                       r.scheduled_job_id,
                       r.scheduler_job_kind,
                       r.scheduled_for,
                       r.schedule_slot,
                       r.notification_policy,
                       r.rollout_flag_state,
                       r.support_evidence,
                       r.rate_limit_evidence,
                       r.incident_evidence,
                       r.recorded_at,
                       r.created_at,
                       w.slug AS workspace_slug,
                       w.name AS workspace_name,
                       m.direction AS message_direction
                FROM channel_delivery_receipts AS r
                JOIN workspaces AS w
                  ON w.id = r.workspace_id
                LEFT JOIN channel_messages AS m
                  ON m.id = r.channel_message_id
                WHERE r.channel_type = 'telegram'
                  AND r.workspace_id = %s
                ORDER BY r.recorded_at DESC, r.id DESC
                LIMIT %s
                """,
                (workspace_id, bounded_limit),
            )
        rows = cur.fetchall()

    payload: list[dict[str, object]] = []
    for row in rows:
        payload.append(
            {
                "id": str(row["id"]),
                "workspace_id": str(row["workspace_id"]),
                "workspace_slug": row["workspace_slug"],
                "workspace_name": row["workspace_name"],
                "channel_message_id": str(row["channel_message_id"]),
                "message_direction": row["message_direction"],
                "channel_type": row["channel_type"],
                "status": row["status"],
                "provider_receipt_id": row["provider_receipt_id"],
                "failure_code": row["failure_code"],
                "failure_detail": row["failure_detail"],
                "scheduled_job_id": None
                if row["scheduled_job_id"] is None
                else str(row["scheduled_job_id"]),
                "scheduler_job_kind": row["scheduler_job_kind"],
                "scheduled_for": None if row["scheduled_for"] is None else row["scheduled_for"].isoformat(),
                "schedule_slot": row["schedule_slot"],
                "notification_policy": row["notification_policy"],
                "rollout_flag_state": row["rollout_flag_state"],
                "support_evidence": row["support_evidence"],
                "rate_limit_evidence": row["rate_limit_evidence"],
                "incident_evidence": row["incident_evidence"],
                "recorded_at": row["recorded_at"].isoformat(),
                "created_at": row["created_at"].isoformat(),
            }
        )

    return payload


def _workspace_onboarding_incidents(conn) -> list[dict[str, object]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,
                   slug,
                   name,
                   support_status,
                   onboarding_last_error_code,
                   onboarding_last_error_detail,
                   onboarding_last_error_at,
                   onboarding_error_count,
                   incident_evidence,
                   updated_at
            FROM workspaces
            WHERE onboarding_error_count > 0
              AND onboarding_last_error_at IS NOT NULL
            ORDER BY onboarding_last_error_at DESC, id DESC
            """,
        )
        rows = cur.fetchall()

    incidents: list[dict[str, object]] = []
    for row in rows:
        evidence = row["incident_evidence"] or {}
        resolved = bool(evidence.get("resolved", False))
        incidents.append(
            {
                "incident_id": f"workspace-onboarding:{row['id']}",
                "workspace_id": str(row["id"]),
                "workspace_slug": row["slug"],
                "workspace_name": row["name"],
                "source": "workspace_onboarding",
                "severity": "critical" if row["support_status"] == "blocked" else "warning",
                "status": "resolved" if resolved else "open",
                "code": row["onboarding_last_error_code"] or "onboarding_error",
                "detail": row["onboarding_last_error_detail"]
                or "workspace onboarding encountered an error",
                "evidence": {
                    "onboarding_error_count": int(row["onboarding_error_count"]),
                    "support_status": row["support_status"],
                    **evidence,
                },
                "occurred_at": row["onboarding_last_error_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
            }
        )

    return incidents


def _delivery_incidents(conn) -> list[dict[str, object]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.id,
                   r.workspace_id,
                   w.slug,
                   w.name,
                   r.status,
                   r.failure_code,
                   r.failure_detail,
                   r.scheduler_job_kind,
                   r.incident_evidence,
                   r.recorded_at
            FROM channel_delivery_receipts AS r
            JOIN workspaces AS w
              ON w.id = r.workspace_id
            WHERE r.channel_type = 'telegram'
              AND (
                r.status IN ('failed', 'suppressed')
                OR r.incident_evidence <> '{}'::jsonb
              )
            ORDER BY r.recorded_at DESC, r.id DESC
            LIMIT 400
            """,
        )
        rows = cur.fetchall()

    incidents: list[dict[str, object]] = []
    for row in rows:
        evidence = row["incident_evidence"] or {}
        resolved = bool(evidence.get("resolved", False))
        incidents.append(
            {
                "incident_id": f"delivery-receipt:{row['id']}",
                "workspace_id": str(row["workspace_id"]),
                "workspace_slug": row["slug"],
                "workspace_name": row["name"],
                "source": "delivery_receipt",
                "severity": "critical" if row["status"] == "failed" else "warning",
                "status": "resolved" if resolved else "open",
                "code": row["failure_code"] or f"delivery_{row['status']}",
                "detail": row["failure_detail"] or "delivery receipt indicates a non-delivered status",
                "evidence": {
                    "scheduler_job_kind": row["scheduler_job_kind"],
                    **evidence,
                },
                "occurred_at": row["recorded_at"].isoformat(),
                "updated_at": row["recorded_at"].isoformat(),
            }
        )

    return incidents


def _telemetry_incidents(conn) -> list[dict[str, object]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT t.id,
                   t.workspace_id,
                   w.slug,
                   w.name,
                   t.flow_kind,
                   t.event_kind,
                   t.status,
                   t.route_path,
                   t.evidence,
                   t.created_at
            FROM chat_telemetry AS t
            LEFT JOIN workspaces AS w
              ON w.id = t.workspace_id
            WHERE t.status IN ('failed', 'blocked_rollout', 'rate_limited', 'abuse_blocked')
               OR t.event_kind = 'incident'
            ORDER BY t.created_at DESC, t.id DESC
            LIMIT 400
            """,
        )
        rows = cur.fetchall()

    incidents: list[dict[str, object]] = []
    for row in rows:
        evidence = row["evidence"] or {}
        resolved = bool(evidence.get("resolved", False))
        incidents.append(
            {
                "incident_id": f"chat-telemetry:{row['id']}",
                "workspace_id": None if row["workspace_id"] is None else str(row["workspace_id"]),
                "workspace_slug": row["slug"],
                "workspace_name": row["name"],
                "source": "chat_telemetry",
                "severity": "critical"
                if row["status"] in {"failed", "abuse_blocked"}
                else "warning",
                "status": "resolved" if resolved else "open",
                "code": str(row["status"]),
                "detail": f"{row['flow_kind']} {row['event_kind']} via {row['route_path']}",
                "evidence": {
                    "flow_kind": row["flow_kind"],
                    "event_kind": row["event_kind"],
                    "route_path": row["route_path"],
                    **evidence,
                },
                "occurred_at": row["created_at"].isoformat(),
                "updated_at": row["created_at"].isoformat(),
            }
        )

    return incidents


def list_hosted_incidents_for_admin(
    conn,
    *,
    limit: int,
    status_filter: Literal["open", "resolved", "all"] = "open",
    workspace_id: UUID | None = None,
) -> list[dict[str, object]]:
    bounded_limit = max(1, min(limit, 500))

    incidents = [
        *_workspace_onboarding_incidents(conn),
        *_delivery_incidents(conn),
        *_telemetry_incidents(conn),
    ]

    filtered: list[dict[str, object]] = []
    for incident in incidents:
        if workspace_id is not None and incident["workspace_id"] != str(workspace_id):
            continue
        if status_filter != "all" and incident["status"] != status_filter:
            continue
        filtered.append(incident)

    filtered.sort(key=lambda item: str(item["occurred_at"]), reverse=True)
    return filtered[:bounded_limit]


def get_hosted_overview_for_admin(
    conn,
    *,
    window_hours: int,
) -> dict[str, object]:
    bounded_hours = max(1, min(window_hours, 168))
    window_start = utc_now() - timedelta(hours=bounded_hours)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) AS total_count,
                   count(*) FILTER (WHERE bootstrap_status = 'ready') AS ready_count,
                   count(*) FILTER (WHERE bootstrap_status = 'pending') AS pending_count,
                   count(*) FILTER (WHERE support_status = 'blocked') AS blocked_support_count,
                   count(*) FILTER (WHERE support_status = 'needs_attention') AS attention_support_count
            FROM workspaces
            """,
        )
        workspace_counts = cur.fetchone()

        cur.execute(
            """
            SELECT count(DISTINCT workspace_id) AS linked_workspace_count
            FROM channel_identities
            WHERE channel_type = 'telegram'
              AND status = 'linked'
            """,
        )
        linked_counts = cur.fetchone()

        cur.execute(
            """
            SELECT count(*) AS total_count,
                   count(*) FILTER (WHERE status = 'failed') AS failed_count,
                   count(*) FILTER (WHERE status = 'suppressed') AS suppressed_count,
                   count(*) FILTER (WHERE status IN ('simulated', 'delivered')) AS delivered_or_simulated_count
            FROM channel_delivery_receipts
            WHERE channel_type = 'telegram'
              AND recorded_at >= %s
            """,
            (window_start,),
        )
        delivery_counts = cur.fetchone()

        cur.execute(
            """
            SELECT count(*) AS total_count,
                   count(*) FILTER (WHERE status = 'ok') AS ok_count,
                   count(*) FILTER (WHERE status = 'failed') AS failed_count,
                   count(*) FILTER (WHERE status = 'blocked_rollout') AS rollout_blocked_count,
                   count(*) FILTER (WHERE status = 'rate_limited') AS rate_limited_count,
                   count(*) FILTER (WHERE status = 'abuse_blocked') AS abuse_blocked_count
            FROM chat_telemetry
            WHERE created_at >= %s
            """,
            (window_start,),
        )
        telemetry_counts = cur.fetchone()

        cur.execute(
            """
            SELECT count(*) AS total_count,
                   count(*) FILTER (WHERE enabled = true) AS enabled_count,
                   count(*) FILTER (WHERE enabled = false) AS disabled_count
            FROM feature_flags
            WHERE flag_key LIKE 'hosted_%%'
            """,
        )
        rollout_counts = cur.fetchone()

    incident_count = len(
        list_hosted_incidents_for_admin(
            conn,
            limit=500,
            status_filter="open",
            workspace_id=None,
        )
    )

    return {
        "window_hours": bounded_hours,
        "window_start": window_start.isoformat(),
        "workspaces": {
            "total_count": int(workspace_counts["total_count"]),
            "ready_count": int(workspace_counts["ready_count"]),
            "pending_count": int(workspace_counts["pending_count"]),
            "blocked_support_count": int(workspace_counts["blocked_support_count"]),
            "attention_support_count": int(workspace_counts["attention_support_count"]),
            "linked_telegram_workspace_count": int(linked_counts["linked_workspace_count"]),
        },
        "delivery_receipts": {
            "total_count": int(delivery_counts["total_count"]),
            "failed_count": int(delivery_counts["failed_count"]),
            "suppressed_count": int(delivery_counts["suppressed_count"]),
            "delivered_or_simulated_count": int(delivery_counts["delivered_or_simulated_count"]),
        },
        "chat_telemetry": {
            "total_count": int(telemetry_counts["total_count"]),
            "ok_count": int(telemetry_counts["ok_count"]),
            "failed_count": int(telemetry_counts["failed_count"]),
            "rollout_blocked_count": int(telemetry_counts["rollout_blocked_count"]),
            "rate_limited_count": int(telemetry_counts["rate_limited_count"]),
            "abuse_blocked_count": int(telemetry_counts["abuse_blocked_count"]),
        },
        "rollout_flags": {
            "total_count": int(rollout_counts["total_count"]),
            "enabled_count": int(rollout_counts["enabled_count"]),
            "disabled_count": int(rollout_counts["disabled_count"]),
        },
        "incidents": {
            "open_count": incident_count,
        },
    }


def get_hosted_rate_limits_for_admin(
    conn,
    *,
    window_hours: int,
    limit: int,
) -> dict[str, object]:
    bounded_hours = max(1, min(window_hours, 168))
    bounded_limit = max(1, min(limit, 200))
    window_start = utc_now() - timedelta(hours=bounded_hours)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT flow_kind,
                   status,
                   count(*) AS total_count
            FROM chat_telemetry
            WHERE created_at >= %s
              AND status IN ('rate_limited', 'abuse_blocked')
            GROUP BY flow_kind, status
            ORDER BY flow_kind ASC, status ASC
            """,
            (window_start,),
        )
        grouped_rows = cur.fetchall()

    summary: dict[str, dict[str, int]] = {}
    for row in grouped_rows:
        flow_kind = str(row["flow_kind"])
        status = str(row["status"])
        bucket = summary.setdefault(flow_kind, {})
        bucket[status] = int(row["total_count"])

    with conn.cursor() as cur:
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
            WHERE created_at >= %s
              AND status IN ('rate_limited', 'abuse_blocked')
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (window_start, bounded_limit),
        )
        recent_rows = cur.fetchall()

    return {
        "window_hours": bounded_hours,
        "window_start": window_start.isoformat(),
        "summary": summary,
        "items": [serialize_chat_telemetry(row) for row in recent_rows],
    }
