from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, TypedDict
from uuid import UUID

from alicebot_api.config import Settings


HostedFlowKind = Literal["chat_handle", "scheduler_daily_brief", "scheduler_open_loop_prompt"]


@dataclass(frozen=True)
class RateLimitPolicy:
    key: str
    window_seconds: int
    max_requests: int


class RateLimitDecision(TypedDict):
    allowed: bool
    code: str | None
    message: str
    retry_after_seconds: int
    rate_limit_key: str
    window_seconds: int
    max_requests: int
    observed_requests: int
    abuse_signal: str | None


def utc_now() -> datetime:
    return datetime.now(UTC)


def _policy_for_flow(settings: Settings, *, flow_kind: HostedFlowKind) -> RateLimitPolicy:
    if flow_kind == "chat_handle":
        return RateLimitPolicy(
            key="hosted_chat_handle",
            window_seconds=settings.hosted_chat_rate_limit_window_seconds,
            max_requests=settings.hosted_chat_rate_limit_max_requests,
        )

    return RateLimitPolicy(
        key="hosted_scheduler_delivery",
        window_seconds=settings.hosted_scheduler_rate_limit_window_seconds,
        max_requests=settings.hosted_scheduler_rate_limit_max_requests,
    )


def evaluate_hosted_flow_limits(
    conn,
    *,
    settings: Settings,
    user_account_id: UUID,
    workspace_id: UUID,
    flow_kind: HostedFlowKind,
    now: datetime | None = None,
) -> RateLimitDecision:
    del user_account_id
    timestamp = utc_now() if now is None else now
    policy = _policy_for_flow(settings, flow_kind=flow_kind)

    if not settings.hosted_rate_limits_enabled_by_default:
        return {
            "allowed": True,
            "code": None,
            "message": "hosted rate limits are disabled by configuration",
            "retry_after_seconds": 0,
            "rate_limit_key": policy.key,
            "window_seconds": policy.window_seconds,
            "max_requests": policy.max_requests,
            "observed_requests": 0,
            "abuse_signal": None,
        }

    window_start = timestamp - timedelta(seconds=policy.window_seconds)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) AS total_count,
                   min(created_at) AS oldest_created_at
            FROM chat_telemetry
            WHERE workspace_id = %s
              AND flow_kind = %s
              AND event_kind = 'attempt'
              AND created_at >= %s
            """,
            (workspace_id, flow_kind, window_start),
        )
        attempts_row = cur.fetchone()

    observed_requests = int(attempts_row["total_count"]) if attempts_row is not None else 0

    abuse_window_start = timestamp - timedelta(seconds=settings.hosted_abuse_window_seconds)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(*) AS blocked_count,
                   min(created_at) AS oldest_created_at
            FROM chat_telemetry
            WHERE workspace_id = %s
              AND flow_kind = %s
              AND status IN ('rate_limited', 'abuse_blocked')
              AND created_at >= %s
            """,
            (workspace_id, flow_kind, abuse_window_start),
        )
        blocked_row = cur.fetchone()

    blocked_count = int(blocked_row["blocked_count"]) if blocked_row is not None else 0
    if settings.hosted_abuse_controls_enabled_by_default and blocked_count >= settings.hosted_abuse_block_threshold:
        oldest = blocked_row["oldest_created_at"]
        retry_after = settings.hosted_abuse_window_seconds
        if oldest is not None:
            elapsed = int((timestamp - oldest).total_seconds())
            retry_after = max(1, settings.hosted_abuse_window_seconds - elapsed)
        return {
            "allowed": False,
            "code": "hosted_abuse_limit_exceeded",
            "message": (
                "hosted abuse controls blocked this flow after repeated rate-limit violations"
            ),
            "retry_after_seconds": retry_after,
            "rate_limit_key": policy.key,
            "window_seconds": settings.hosted_abuse_window_seconds,
            "max_requests": settings.hosted_abuse_block_threshold,
            "observed_requests": blocked_count,
            "abuse_signal": "repeated_rate_limit_violations",
        }

    if observed_requests >= policy.max_requests:
        oldest = attempts_row["oldest_created_at"] if attempts_row is not None else None
        retry_after = policy.window_seconds
        if oldest is not None:
            elapsed = int((timestamp - oldest).total_seconds())
            retry_after = max(1, policy.window_seconds - elapsed)

        return {
            "allowed": False,
            "code": "hosted_rate_limit_exceeded",
            "message": (
                "hosted flow rate limit exceeded; "
                f"max {policy.max_requests} requests per {policy.window_seconds} seconds"
            ),
            "retry_after_seconds": retry_after,
            "rate_limit_key": policy.key,
            "window_seconds": policy.window_seconds,
            "max_requests": policy.max_requests,
            "observed_requests": observed_requests,
            "abuse_signal": None,
        }

    return {
        "allowed": True,
        "code": None,
        "message": "within hosted flow rate limits",
        "retry_after_seconds": 0,
        "rate_limit_key": policy.key,
        "window_seconds": policy.window_seconds,
        "max_requests": policy.max_requests,
        "observed_requests": observed_requests,
        "abuse_signal": None,
    }
