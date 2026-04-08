from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
import hashlib
import re
from typing import Any, Literal, TypedDict
from uuid import UUID
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

from alicebot_api.chief_of_staff import compile_chief_of_staff_priority_brief
from alicebot_api.continuity_open_loops import (
    compile_continuity_daily_brief,
    compile_continuity_open_loop_dashboard,
)
from alicebot_api.contracts import (
    DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT,
    MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT,
    MAX_CONTINUITY_DAILY_BRIEF_LIMIT,
    MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    ChiefOfStaffPriorityBriefRequestInput,
    ContinuityDailyBriefRequestInput,
    ContinuityOpenLoopDashboardQueryInput,
)
from alicebot_api.db import set_current_user
from alicebot_api.hosted_preferences import (
    DEFAULT_BRIEF_PREFERENCES,
    DEFAULT_QUIET_HOURS,
    DEFAULT_TIMEZONE,
    ensure_user_preferences,
    validate_timezone,
)
from alicebot_api.store import ContinuityStore
from alicebot_api.telegram_channels import (
    TELEGRAM_CHANNEL_TYPE,
    TelegramDeliveryReceiptRow,
    TelegramIdentityNotFoundError,
    dispatch_telegram_workspace_message,
    get_latest_linked_telegram_identity,
    serialize_delivery_receipt,
)


_HHMM_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")

_TERMINAL_JOB_STATUSES = {
    "delivered",
    "simulated",
    "suppressed_quiet_hours",
    "suppressed_disabled",
    "suppressed_outside_window",
    "failed",
}


class TelegramNotificationPreferenceValidationError(ValueError):
    """Raised when Telegram notification preferences are invalid."""


class TelegramOpenLoopPromptNotFoundError(LookupError):
    """Raised when a Telegram open-loop prompt id does not map to a scoped item."""


class NotificationSubscriptionRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    channel_identity_id: UUID
    notifications_enabled: bool
    daily_brief_enabled: bool
    daily_brief_window_start: str
    open_loop_prompts_enabled: bool
    waiting_for_prompts_enabled: bool
    stale_prompts_enabled: bool
    timezone: str
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    created_at: datetime
    updated_at: datetime


class ContinuityBriefRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    channel_identity_id: UUID
    brief_kind: str
    assembly_version: str
    summary: dict[str, Any]
    brief_payload: dict[str, Any]
    message_text: str
    compiled_at: datetime
    created_at: datetime


class DailyBriefJobRow(TypedDict):
    id: UUID
    workspace_id: UUID
    channel_type: str
    channel_identity_id: UUID
    job_kind: str
    prompt_kind: str | None
    prompt_id: str | None
    continuity_object_id: UUID | None
    continuity_brief_id: UUID | None
    schedule_slot: str
    idempotency_key: str
    due_at: datetime
    status: str
    suppression_reason: str | None
    attempt_count: int
    delivery_receipt_id: UUID | None
    payload: dict[str, Any]
    result_payload: dict[str, Any]
    rollout_flag_state: str
    support_evidence: dict[str, Any]
    rate_limit_evidence: dict[str, Any]
    incident_evidence: dict[str, Any]
    attempted_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OpenLoopPromptCandidate(TypedDict):
    prompt_id: str
    prompt_kind: Literal["waiting_for", "stale"]
    continuity_object_id: str
    title: str
    continuity_status: str
    review_action_hint: Literal["still_blocked", "deferred"]
    due_at: str
    message_text: str


@dataclass(frozen=True)
class DeliveryPolicyEvaluation:
    allowed: bool
    suppression_status: str | None
    reason: str
    window_open: bool
    quiet_hours_active: bool
    timezone: str
    local_time: str

    def as_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "suppression_status": self.suppression_status,
            "reason": self.reason,
            "window_open": self.window_open,
            "quiet_hours_active": self.quiet_hours_active,
            "timezone": self.timezone,
            "local_time": self.local_time,
        }


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_hhmm(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TelegramNotificationPreferenceValidationError(f"{field_name} must be a string in HH:MM format")
    normalized = value.strip()
    if _HHMM_PATTERN.fullmatch(normalized) is None:
        raise TelegramNotificationPreferenceValidationError(f"{field_name} must use HH:MM 24-hour format")
    return normalized


def _hhmm_to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":", maxsplit=1)
    return int(hours) * 60 + int(minutes)


def _local_now(now: datetime, timezone_name: str) -> datetime:
    return now.astimezone(ZoneInfo(timezone_name))


def _quiet_hours_active(*, local_now: datetime, start: str, end: str) -> bool:
    start_minutes = _hhmm_to_minutes(start)
    end_minutes = _hhmm_to_minutes(end)
    current_minutes = local_now.hour * 60 + local_now.minute

    if start_minutes == end_minutes:
        return False
    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def _window_open(*, local_now: datetime, start: str) -> bool:
    return (local_now.hour * 60 + local_now.minute) >= _hhmm_to_minutes(start)


def _daily_slot_for_now(*, now: datetime, timezone_name: str) -> str:
    return _local_now(now, timezone_name).date().isoformat()


def _daily_due_at(*, slot: str, timezone_name: str, window_start: str) -> datetime:
    local_date = date.fromisoformat(slot)
    hour, minute = window_start.split(":", maxsplit=1)
    local_due = datetime.combine(
        local_date,
        time(int(hour), int(minute), tzinfo=ZoneInfo(timezone_name)),
    )
    return local_due.astimezone(UTC)


def _resolve_internal_idempotency_key(
    *,
    workspace_id: UUID,
    job_kind: Literal["daily_brief", "open_loop_prompt"],
    schedule_slot: str,
    prompt_id: str | None,
    client_idempotency_key: str | None,
) -> str:
    if client_idempotency_key is None:
        if job_kind == "daily_brief":
            return f"telegram:daily-brief:{workspace_id}:{schedule_slot}"
        if prompt_id is None:
            raise TelegramNotificationPreferenceValidationError("prompt_id is required for open-loop prompt delivery")
        return f"telegram:open-loop-prompt:{workspace_id}:{prompt_id}:{schedule_slot}"

    normalized_key = client_idempotency_key.strip()
    if normalized_key == "":
        raise TelegramNotificationPreferenceValidationError("idempotency_key must not be empty")

    digest_payload = (
        f"workspace={workspace_id}|job_kind={job_kind}|prompt_id={prompt_id or ''}|client_key={normalized_key}"
    )
    digest = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()
    return f"telegram:{job_kind}:custom:{digest}"


def _job_columns_sql() -> str:
    return (
        "id, workspace_id, channel_type, channel_identity_id, job_kind, prompt_kind, prompt_id, "
        "continuity_object_id, continuity_brief_id, schedule_slot, idempotency_key, due_at, status, "
        "suppression_reason, attempt_count, delivery_receipt_id, payload, result_payload, "
        "rollout_flag_state, support_evidence, rate_limit_evidence, incident_evidence, "
        "attempted_at, completed_at, created_at, updated_at"
    )


def _receipt_columns_sql() -> str:
    return (
        "id, workspace_id, channel_message_id, channel_type, status, provider_receipt_id, failure_code, "
        "failure_detail, scheduled_job_id, scheduler_job_kind, scheduled_for, schedule_slot, "
        "notification_policy, rollout_flag_state, support_evidence, rate_limit_evidence, "
        "incident_evidence, recorded_at, created_at"
    )


def _brief_columns_sql() -> str:
    return (
        "id, workspace_id, channel_type, channel_identity_id, brief_kind, assembly_version, "
        "summary, brief_payload, message_text, compiled_at, created_at"
    )


def _resolve_linked_identity(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
):
    identity = get_latest_linked_telegram_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    if identity is None:
        raise TelegramIdentityNotFoundError("telegram channel is not linked for this workspace")
    return identity


def _subscription_defaults(
    *,
    timezone: str,
    brief_preferences: dict[str, object],
    quiet_hours: dict[str, object],
) -> dict[str, object]:
    daily_brief = brief_preferences.get("daily_brief")
    if not isinstance(daily_brief, dict):
        daily_brief = DEFAULT_BRIEF_PREFERENCES["daily_brief"]

    quiet = quiet_hours if isinstance(quiet_hours, dict) else DEFAULT_QUIET_HOURS

    daily_brief_enabled = bool(daily_brief.get("enabled", False))
    daily_brief_window_start = _normalize_hhmm(
        daily_brief.get("window_start", "07:00"),
        field_name="daily_brief.window_start",
    )

    quiet_hours_enabled = bool(quiet.get("enabled", False))
    quiet_hours_start = _normalize_hhmm(quiet.get("start", "22:00"), field_name="quiet_hours.start")
    quiet_hours_end = _normalize_hhmm(quiet.get("end", "07:00"), field_name="quiet_hours.end")

    return {
        "notifications_enabled": True,
        "daily_brief_enabled": daily_brief_enabled,
        "daily_brief_window_start": daily_brief_window_start,
        "open_loop_prompts_enabled": True,
        "waiting_for_prompts_enabled": True,
        "stale_prompts_enabled": True,
        "timezone": validate_timezone(timezone),
        "quiet_hours_enabled": quiet_hours_enabled,
        "quiet_hours_start": quiet_hours_start,
        "quiet_hours_end": quiet_hours_end,
    }


def ensure_workspace_notification_subscription(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
) -> NotificationSubscriptionRow:
    identity = _resolve_linked_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    preferences = ensure_user_preferences(conn, user_account_id=user_account_id)
    defaults = _subscription_defaults(
        timezone=preferences.get("timezone", DEFAULT_TIMEZONE),
        brief_preferences=preferences.get("brief_preferences", DEFAULT_BRIEF_PREFERENCES),
        quiet_hours=preferences.get("quiet_hours", DEFAULT_QUIET_HOURS),
    )

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO notification_subscriptions (
              workspace_id,
              channel_type,
              channel_identity_id,
              notifications_enabled,
              daily_brief_enabled,
              daily_brief_window_start,
              open_loop_prompts_enabled,
              waiting_for_prompts_enabled,
              stale_prompts_enabled,
              timezone,
              quiet_hours_enabled,
              quiet_hours_start,
              quiet_hours_end,
              updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp())
            ON CONFLICT (workspace_id, channel_type) DO UPDATE
            SET channel_identity_id = EXCLUDED.channel_identity_id,
                updated_at = clock_timestamp()
            RETURNING id,
                      workspace_id,
                      channel_type,
                      channel_identity_id,
                      notifications_enabled,
                      daily_brief_enabled,
                      daily_brief_window_start,
                      open_loop_prompts_enabled,
                      waiting_for_prompts_enabled,
                      stale_prompts_enabled,
                      timezone,
                      quiet_hours_enabled,
                      quiet_hours_start,
                      quiet_hours_end,
                      created_at,
                      updated_at
            """,
            (
                workspace_id,
                TELEGRAM_CHANNEL_TYPE,
                identity["id"],
                defaults["notifications_enabled"],
                defaults["daily_brief_enabled"],
                defaults["daily_brief_window_start"],
                defaults["open_loop_prompts_enabled"],
                defaults["waiting_for_prompts_enabled"],
                defaults["stale_prompts_enabled"],
                defaults["timezone"],
                defaults["quiet_hours_enabled"],
                defaults["quiet_hours_start"],
                defaults["quiet_hours_end"],
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to ensure telegram notification subscription")
    return row


def _validate_patch_fields(patch: dict[str, object]) -> dict[str, object]:
    validated: dict[str, object] = {}

    boolean_fields = (
        "notifications_enabled",
        "daily_brief_enabled",
        "open_loop_prompts_enabled",
        "waiting_for_prompts_enabled",
        "stale_prompts_enabled",
        "quiet_hours_enabled",
    )
    for field_name in boolean_fields:
        if field_name in patch:
            value = patch[field_name]
            if not isinstance(value, bool):
                raise TelegramNotificationPreferenceValidationError(f"{field_name} must be a boolean")
            validated[field_name] = value

    if "daily_brief_window_start" in patch:
        validated["daily_brief_window_start"] = _normalize_hhmm(
            patch["daily_brief_window_start"],
            field_name="daily_brief_window_start",
        )
    if "quiet_hours_start" in patch:
        validated["quiet_hours_start"] = _normalize_hhmm(
            patch["quiet_hours_start"],
            field_name="quiet_hours_start",
        )
    if "quiet_hours_end" in patch:
        validated["quiet_hours_end"] = _normalize_hhmm(
            patch["quiet_hours_end"],
            field_name="quiet_hours_end",
        )
    if "timezone" in patch:
        value = patch["timezone"]
        if not isinstance(value, str):
            raise TelegramNotificationPreferenceValidationError("timezone must be a string")
        validated["timezone"] = validate_timezone(value)

    return validated


def patch_workspace_notification_subscription(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    patch: dict[str, object],
) -> NotificationSubscriptionRow:
    existing = ensure_workspace_notification_subscription(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    if not patch:
        return existing

    validated = _validate_patch_fields(patch)

    merged = {
        "notifications_enabled": existing["notifications_enabled"],
        "daily_brief_enabled": existing["daily_brief_enabled"],
        "daily_brief_window_start": existing["daily_brief_window_start"],
        "open_loop_prompts_enabled": existing["open_loop_prompts_enabled"],
        "waiting_for_prompts_enabled": existing["waiting_for_prompts_enabled"],
        "stale_prompts_enabled": existing["stale_prompts_enabled"],
        "timezone": existing["timezone"],
        "quiet_hours_enabled": existing["quiet_hours_enabled"],
        "quiet_hours_start": existing["quiet_hours_start"],
        "quiet_hours_end": existing["quiet_hours_end"],
    }
    merged.update(validated)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE notification_subscriptions
            SET notifications_enabled = %s,
                daily_brief_enabled = %s,
                daily_brief_window_start = %s,
                open_loop_prompts_enabled = %s,
                waiting_for_prompts_enabled = %s,
                stale_prompts_enabled = %s,
                timezone = %s,
                quiet_hours_enabled = %s,
                quiet_hours_start = %s,
                quiet_hours_end = %s,
                updated_at = clock_timestamp()
            WHERE id = %s
            RETURNING id,
                      workspace_id,
                      channel_type,
                      channel_identity_id,
                      notifications_enabled,
                      daily_brief_enabled,
                      daily_brief_window_start,
                      open_loop_prompts_enabled,
                      waiting_for_prompts_enabled,
                      stale_prompts_enabled,
                      timezone,
                      quiet_hours_enabled,
                      quiet_hours_start,
                      quiet_hours_end,
                      created_at,
                      updated_at
            """,
            (
                merged["notifications_enabled"],
                merged["daily_brief_enabled"],
                merged["daily_brief_window_start"],
                merged["open_loop_prompts_enabled"],
                merged["waiting_for_prompts_enabled"],
                merged["stale_prompts_enabled"],
                merged["timezone"],
                merged["quiet_hours_enabled"],
                merged["quiet_hours_start"],
                merged["quiet_hours_end"],
                existing["id"],
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to patch telegram notification subscription")
    return row


def _evaluate_delivery_policy(
    subscription: NotificationSubscriptionRow,
    *,
    mode: Literal["daily_brief", "open_loop_prompt"],
    prompt_kind: Literal["waiting_for", "stale"] | None,
    now: datetime,
    force: bool,
) -> DeliveryPolicyEvaluation:
    timezone_name = subscription["timezone"]
    local_now = _local_now(now, timezone_name)
    local_time = local_now.strftime("%Y-%m-%d %H:%M:%S %Z")
    window_open = _window_open(local_now=local_now, start=subscription["daily_brief_window_start"])
    quiet_active = False
    if subscription["quiet_hours_enabled"]:
        quiet_active = _quiet_hours_active(
            local_now=local_now,
            start=subscription["quiet_hours_start"],
            end=subscription["quiet_hours_end"],
        )

    if force:
        return DeliveryPolicyEvaluation(
            allowed=True,
            suppression_status=None,
            reason="forced delivery bypassed notification gating",
            window_open=window_open,
            quiet_hours_active=quiet_active,
            timezone=timezone_name,
            local_time=local_time,
        )

    if not subscription["notifications_enabled"]:
        return DeliveryPolicyEvaluation(
            allowed=False,
            suppression_status="suppressed_disabled",
            reason="telegram notifications are disabled",
            window_open=window_open,
            quiet_hours_active=quiet_active,
            timezone=timezone_name,
            local_time=local_time,
        )

    if mode == "daily_brief" and not subscription["daily_brief_enabled"]:
        return DeliveryPolicyEvaluation(
            allowed=False,
            suppression_status="suppressed_disabled",
            reason="daily brief notifications are disabled",
            window_open=window_open,
            quiet_hours_active=quiet_active,
            timezone=timezone_name,
            local_time=local_time,
        )

    if mode == "open_loop_prompt":
        if not subscription["open_loop_prompts_enabled"]:
            return DeliveryPolicyEvaluation(
                allowed=False,
                suppression_status="suppressed_disabled",
                reason="open-loop prompts are disabled",
                window_open=window_open,
                quiet_hours_active=quiet_active,
                timezone=timezone_name,
                local_time=local_time,
            )
        if prompt_kind == "waiting_for" and not subscription["waiting_for_prompts_enabled"]:
            return DeliveryPolicyEvaluation(
                allowed=False,
                suppression_status="suppressed_disabled",
                reason="waiting-for prompts are disabled",
                window_open=window_open,
                quiet_hours_active=quiet_active,
                timezone=timezone_name,
                local_time=local_time,
            )
        if prompt_kind == "stale" and not subscription["stale_prompts_enabled"]:
            return DeliveryPolicyEvaluation(
                allowed=False,
                suppression_status="suppressed_disabled",
                reason="stale-item prompts are disabled",
                window_open=window_open,
                quiet_hours_active=quiet_active,
                timezone=timezone_name,
                local_time=local_time,
            )

    if not window_open:
        return DeliveryPolicyEvaluation(
            allowed=False,
            suppression_status="suppressed_outside_window",
            reason="current local time is before the configured daily brief window",
            window_open=window_open,
            quiet_hours_active=quiet_active,
            timezone=timezone_name,
            local_time=local_time,
        )

    if quiet_active:
        return DeliveryPolicyEvaluation(
            allowed=False,
            suppression_status="suppressed_quiet_hours",
            reason="delivery is deferred due to quiet hours",
            window_open=window_open,
            quiet_hours_active=quiet_active,
            timezone=timezone_name,
            local_time=local_time,
        )

    return DeliveryPolicyEvaluation(
        allowed=True,
        suppression_status=None,
        reason="delivery allowed",
        window_open=window_open,
        quiet_hours_active=quiet_active,
        timezone=timezone_name,
        local_time=local_time,
    )


def serialize_notification_subscription(
    row: NotificationSubscriptionRow,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    effective_now = _utcnow() if now is None else now
    local_now = _local_now(effective_now, row["timezone"])
    quiet_active = False
    if row["quiet_hours_enabled"]:
        quiet_active = _quiet_hours_active(
            local_now=local_now,
            start=row["quiet_hours_start"],
            end=row["quiet_hours_end"],
        )

    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "channel_type": row["channel_type"],
        "channel_identity_id": str(row["channel_identity_id"]),
        "notifications_enabled": row["notifications_enabled"],
        "daily_brief_enabled": row["daily_brief_enabled"],
        "daily_brief_window_start": row["daily_brief_window_start"],
        "open_loop_prompts_enabled": row["open_loop_prompts_enabled"],
        "waiting_for_prompts_enabled": row["waiting_for_prompts_enabled"],
        "stale_prompts_enabled": row["stale_prompts_enabled"],
        "timezone": row["timezone"],
        "quiet_hours": {
            "enabled": row["quiet_hours_enabled"],
            "start": row["quiet_hours_start"],
            "end": row["quiet_hours_end"],
            "active_now": quiet_active,
            "local_time": local_now.isoformat(),
        },
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _serialize_brief_row(row: ContinuityBriefRow | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "channel_type": row["channel_type"],
        "channel_identity_id": str(row["channel_identity_id"]),
        "brief_kind": row["brief_kind"],
        "assembly_version": row["assembly_version"],
        "summary": row["summary"],
        "brief_payload": row["brief_payload"],
        "message_text": row["message_text"],
        "compiled_at": row["compiled_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
    }


def _serialize_job(
    row: DailyBriefJobRow,
    *,
    now: datetime,
) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["workspace_id"]),
        "channel_type": row["channel_type"],
        "channel_identity_id": str(row["channel_identity_id"]),
        "job_kind": row["job_kind"],
        "prompt_kind": row["prompt_kind"],
        "prompt_id": row["prompt_id"],
        "continuity_object_id": None
        if row["continuity_object_id"] is None
        else str(row["continuity_object_id"]),
        "continuity_brief_id": None
        if row["continuity_brief_id"] is None
        else str(row["continuity_brief_id"]),
        "schedule_slot": row["schedule_slot"],
        "idempotency_key": row["idempotency_key"],
        "due_at": row["due_at"].isoformat(),
        "status": row["status"],
        "suppression_reason": row["suppression_reason"],
        "attempt_count": row["attempt_count"],
        "delivery_receipt_id": None
        if row["delivery_receipt_id"] is None
        else str(row["delivery_receipt_id"]),
        "payload": row["payload"],
        "result_payload": row["result_payload"],
        "rollout_flag_state": row["rollout_flag_state"],
        "support_evidence": row["support_evidence"],
        "rate_limit_evidence": row["rate_limit_evidence"],
        "incident_evidence": row["incident_evidence"],
        "attempted_at": None if row["attempted_at"] is None else row["attempted_at"].isoformat(),
        "completed_at": None if row["completed_at"] is None else row["completed_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "is_due": row["status"] == "scheduled" and row["due_at"] <= now,
    }


def _format_daily_brief_message(
    *,
    brief: dict[str, Any],
    chief_brief: dict[str, Any],
    timezone_name: str,
    now: datetime,
) -> str:
    local_day = _local_now(now, timezone_name).strftime("%Y-%m-%d")
    waiting_count = int(brief["waiting_for_highlights"]["summary"]["total_count"])
    blocker_count = int(brief["blocker_highlights"]["summary"]["total_count"])
    stale_count = int(brief["stale_items"]["summary"]["total_count"])

    next_item = brief["next_suggested_action"]["item"]
    next_title = "None"
    if isinstance(next_item, dict):
        next_title = str(next_item.get("title", "None"))

    recommended = chief_brief.get("recommended_next_action")
    recommended_title = "No chief-of-staff recommendation"
    if isinstance(recommended, dict):
        recommended_title = str(recommended.get("title", recommended_title))

    return "\n".join(
        [
            f"Daily Brief ({local_day})",
            f"Waiting-for: {waiting_count}",
            f"Blockers: {blocker_count}",
            f"Stale: {stale_count}",
            f"Next suggested action: {next_title}",
            f"Chief-of-staff recommendation: {recommended_title}",
            "Review open loops with /open-loops and /open-loop <id> done|deferred|still_blocked.",
        ]
    )


def _build_daily_brief_bundle(
    conn,
    *,
    user_account_id: UUID,
    timezone_name: str,
    now: datetime,
) -> dict[str, object]:
    set_current_user(conn, user_account_id)
    store = ContinuityStore(conn)
    daily_payload = compile_continuity_daily_brief(
        store,
        user_id=user_account_id,
        request=ContinuityDailyBriefRequestInput(
            limit=min(DEFAULT_CONTINUITY_DAILY_BRIEF_LIMIT, MAX_CONTINUITY_DAILY_BRIEF_LIMIT),
        ),
    )
    chief_payload = compile_chief_of_staff_priority_brief(
        store,
        user_id=user_account_id,
        request=ChiefOfStaffPriorityBriefRequestInput(
            limit=min(DEFAULT_CHIEF_OF_STAFF_PRIORITY_LIMIT, MAX_CHIEF_OF_STAFF_PRIORITY_LIMIT),
        ),
    )

    daily_brief = daily_payload["brief"]
    chief_brief = chief_payload["brief"]
    message_text = _format_daily_brief_message(
        brief=daily_brief,
        chief_brief=chief_brief,
        timezone_name=timezone_name,
        now=now,
    )

    chief_summary = {
        "trust_confidence_posture": chief_brief["summary"].get("trust_confidence_posture"),
        "follow_through_total_count": chief_brief["summary"].get("follow_through_total_count"),
        "recommended_next_action": chief_brief.get("recommended_next_action"),
    }

    return {
        "brief": daily_brief,
        "chief_of_staff_summary": chief_summary,
        "message_text": message_text,
    }


def _create_continuity_brief_row(
    conn,
    *,
    workspace_id: UUID,
    channel_identity_id: UUID,
    brief_payload: dict[str, Any],
    chief_summary: dict[str, Any],
    message_text: str,
    now: datetime,
) -> ContinuityBriefRow:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO continuity_briefs (
              workspace_id,
              channel_type,
              channel_identity_id,
              brief_kind,
              assembly_version,
              summary,
              brief_payload,
              message_text,
              compiled_at
            )
            VALUES (%s, %s, %s, 'daily_brief', %s, %s, %s, %s, %s)
            RETURNING
              id,
              workspace_id,
              channel_type,
              channel_identity_id,
              brief_kind,
              assembly_version,
              summary,
              brief_payload,
              message_text,
              compiled_at,
              created_at
            """,
            (
                workspace_id,
                TELEGRAM_CHANNEL_TYPE,
                channel_identity_id,
                brief_payload.get("assembly_version", "continuity_daily_brief_v0"),
                Jsonb(chief_summary),
                Jsonb(brief_payload),
                message_text,
                now,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to persist continuity brief")
    return row


def _fetch_job_by_idempotency(
    conn,
    *,
    workspace_id: UUID,
    job_kind: Literal["daily_brief", "open_loop_prompt"],
    idempotency_key: str,
) -> DailyBriefJobRow | None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_job_columns_sql()}
            FROM daily_brief_jobs
            WHERE workspace_id = %s
              AND channel_type = %s
              AND job_kind = %s
              AND idempotency_key = %s
            LIMIT 1
            """,
            (workspace_id, TELEGRAM_CHANNEL_TYPE, job_kind, idempotency_key),
        )
        return cur.fetchone()


def _fetch_jobs_by_workspace(
    conn,
    *,
    workspace_id: UUID,
    limit: int,
) -> list[DailyBriefJobRow]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_job_columns_sql()}
            FROM daily_brief_jobs
            WHERE workspace_id = %s
              AND channel_type = %s
            ORDER BY due_at DESC, id DESC
            LIMIT %s
            """,
            (workspace_id, TELEGRAM_CHANNEL_TYPE, limit),
        )
        return cur.fetchall()


def _fetch_receipt_by_id(
    conn,
    *,
    receipt_id: UUID,
) -> TelegramDeliveryReceiptRow | None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_receipt_columns_sql()}
            FROM channel_delivery_receipts
            WHERE id = %s
            LIMIT 1
            """,
            (receipt_id,),
        )
        return cur.fetchone()


def _fetch_brief_by_id(
    conn,
    *,
    brief_id: UUID,
) -> ContinuityBriefRow | None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_brief_columns_sql()}
            FROM continuity_briefs
            WHERE id = %s
            LIMIT 1
            """,
            (brief_id,),
        )
        return cur.fetchone()


def _upsert_scheduled_job(
    conn,
    *,
    workspace_id: UUID,
    channel_identity_id: UUID,
    job_kind: Literal["daily_brief", "open_loop_prompt"],
    prompt_kind: Literal["waiting_for", "stale"] | None,
    prompt_id: str | None,
    continuity_object_id: UUID | None,
    continuity_brief_id: UUID | None,
    schedule_slot: str,
    idempotency_key: str,
    due_at: datetime,
    payload: dict[str, object],
) -> DailyBriefJobRow:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO daily_brief_jobs (
              workspace_id,
              channel_type,
              channel_identity_id,
              job_kind,
              prompt_kind,
              prompt_id,
              continuity_object_id,
              continuity_brief_id,
              schedule_slot,
              idempotency_key,
              due_at,
              status,
              payload,
              result_payload,
              updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'scheduled', %s, '{{}}'::jsonb, clock_timestamp())
            ON CONFLICT (workspace_id, channel_type, idempotency_key) DO UPDATE
            SET updated_at = daily_brief_jobs.updated_at
            RETURNING {_job_columns_sql()}
            """,
            (
                workspace_id,
                TELEGRAM_CHANNEL_TYPE,
                channel_identity_id,
                job_kind,
                prompt_kind,
                prompt_id,
                continuity_object_id,
                continuity_brief_id,
                schedule_slot,
                idempotency_key,
                due_at,
                Jsonb(payload),
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to upsert scheduled daily brief job")
    return row


def _update_job_result(
    conn,
    *,
    job_id: UUID,
    status: str,
    suppression_reason: str | None,
    delivery_receipt_id: UUID | None,
    continuity_brief_id: UUID | None,
    result_payload: dict[str, object],
    now: datetime,
) -> DailyBriefJobRow:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            UPDATE daily_brief_jobs
            SET status = %s,
                suppression_reason = %s,
                delivery_receipt_id = %s,
                continuity_brief_id = COALESCE(%s, continuity_brief_id),
                result_payload = %s,
                attempted_at = %s,
                completed_at = %s,
                attempt_count = attempt_count + 1,
                updated_at = clock_timestamp()
            WHERE id = %s
            RETURNING {_job_columns_sql()}
            """,
            (
                status,
                suppression_reason,
                delivery_receipt_id,
                continuity_brief_id,
                Jsonb(result_payload),
                now,
                now,
                job_id,
            ),
        )
        row = cur.fetchone()

    if row is None:
        raise RuntimeError("failed to update daily brief job result")
    return row


def _build_open_loop_prompt_candidates(
    conn,
    *,
    user_account_id: UUID,
    now: datetime,
    limit: int,
) -> list[OpenLoopPromptCandidate]:
    set_current_user(conn, user_account_id)
    bounded_limit = min(max(limit, 1), MAX_CONTINUITY_OPEN_LOOP_LIMIT)
    dashboard = compile_continuity_open_loop_dashboard(
        ContinuityStore(conn),
        user_id=user_account_id,
        request=ContinuityOpenLoopDashboardQueryInput(limit=bounded_limit),
    )["dashboard"]

    def _build(
        kind: Literal["waiting_for", "stale"],
        *,
        review_action_hint: Literal["still_blocked", "deferred"],
        section_items: list[dict[str, object]],
    ) -> list[OpenLoopPromptCandidate]:
        prompts: list[OpenLoopPromptCandidate] = []
        for item in section_items:
            continuity_object_id = str(item["id"])
            title = str(item.get("title", continuity_object_id))
            prompt_id = f"{kind}:{continuity_object_id}"
            message_text = (
                f"Open-loop prompt ({kind}): {title}\n"
                f"Review via /open-loop {continuity_object_id} {review_action_hint}."
            )
            prompts.append(
                {
                    "prompt_id": prompt_id,
                    "prompt_kind": kind,
                    "continuity_object_id": continuity_object_id,
                    "title": title,
                    "continuity_status": str(item.get("status", "active")),
                    "review_action_hint": review_action_hint,
                    "due_at": now.isoformat(),
                    "message_text": message_text,
                }
            )
        return prompts

    waiting_prompts = _build(
        "waiting_for",
        review_action_hint="still_blocked",
        section_items=dashboard["waiting_for"]["items"],
    )
    stale_prompts = _build(
        "stale",
        review_action_hint="deferred",
        section_items=dashboard["stale"]["items"],
    )
    return stale_prompts + waiting_prompts


def _prompt_key(prompt_kind: str, continuity_object_id: str) -> str:
    payload = f"telegram:{prompt_kind}:{continuity_object_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _fetch_latest_prompt_jobs(
    conn,
    *,
    workspace_id: UUID,
    prompt_ids: list[str],
) -> dict[str, DailyBriefJobRow]:
    if not prompt_ids:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_job_columns_sql()}
            FROM daily_brief_jobs
            WHERE workspace_id = %s
              AND channel_type = %s
              AND job_kind = 'open_loop_prompt'
              AND prompt_id = ANY(%s)
            ORDER BY created_at DESC, id DESC
            """,
            (workspace_id, TELEGRAM_CHANNEL_TYPE, prompt_ids),
        )
        rows = cur.fetchall()

    latest: dict[str, DailyBriefJobRow] = {}
    for row in rows:
        prompt_id = row["prompt_id"]
        if prompt_id is None:
            continue
        if prompt_id not in latest:
            latest[prompt_id] = row
    return latest


def get_workspace_notification_preferences(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    now: datetime | None = None,
) -> dict[str, object]:
    effective_now = _utcnow() if now is None else now
    subscription = ensure_workspace_notification_subscription(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    return {
        "workspace_id": str(workspace_id),
        "notification_preferences": serialize_notification_subscription(subscription, now=effective_now),
    }


def get_workspace_daily_brief_preview(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    now: datetime | None = None,
) -> dict[str, object]:
    effective_now = _utcnow() if now is None else now
    subscription = ensure_workspace_notification_subscription(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    bundle = _build_daily_brief_bundle(
        conn,
        user_account_id=user_account_id,
        timezone_name=subscription["timezone"],
        now=effective_now,
    )
    policy = _evaluate_delivery_policy(
        subscription,
        mode="daily_brief",
        prompt_kind=None,
        now=effective_now,
        force=False,
    )
    return {
        "workspace_id": str(workspace_id),
        "brief": bundle["brief"],
        "chief_of_staff_summary": bundle["chief_of_staff_summary"],
        "preview_message_text": bundle["message_text"],
        "delivery_policy": policy.as_dict(),
    }


def _existing_delivery_artifacts(
    conn,
    *,
    job: DailyBriefJobRow,
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    receipt_payload: dict[str, object] | None = None
    brief_payload: dict[str, object] | None = None

    if job["delivery_receipt_id"] is not None:
        receipt = _fetch_receipt_by_id(conn, receipt_id=job["delivery_receipt_id"])
        if receipt is not None:
            receipt_payload = serialize_delivery_receipt(receipt)

    if job["continuity_brief_id"] is not None:
        brief = _fetch_brief_by_id(conn, brief_id=job["continuity_brief_id"])
        brief_payload = _serialize_brief_row(brief)

    return receipt_payload, brief_payload


def deliver_workspace_daily_brief(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    bot_token: str,
    force: bool,
    idempotency_key: str | None,
    now: datetime | None = None,
) -> dict[str, object]:
    effective_now = _utcnow() if now is None else now
    subscription = ensure_workspace_notification_subscription(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    identity = _resolve_linked_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )

    schedule_slot = _daily_slot_for_now(now=effective_now, timezone_name=subscription["timezone"])
    due_at = _daily_due_at(
        slot=schedule_slot,
        timezone_name=subscription["timezone"],
        window_start=subscription["daily_brief_window_start"],
    )
    resolved_idempotency = _resolve_internal_idempotency_key(
        workspace_id=workspace_id,
        job_kind="daily_brief",
        schedule_slot=schedule_slot,
        prompt_id=None,
        client_idempotency_key=idempotency_key,
    )
    existing = _fetch_job_by_idempotency(
        conn,
        workspace_id=workspace_id,
        job_kind="daily_brief",
        idempotency_key=resolved_idempotency,
    )
    if existing is not None and existing["status"] in _TERMINAL_JOB_STATUSES:
        receipt_payload, brief_payload = _existing_delivery_artifacts(conn, job=existing)
        return {
            "workspace_id": str(workspace_id),
            "job": _serialize_job(existing, now=effective_now),
            "brief_record": brief_payload,
            "delivery_receipt": receipt_payload,
            "idempotent_replay": True,
        }

    bundle = _build_daily_brief_bundle(
        conn,
        user_account_id=user_account_id,
        timezone_name=subscription["timezone"],
        now=effective_now,
    )
    brief_record = _create_continuity_brief_row(
        conn,
        workspace_id=workspace_id,
        channel_identity_id=identity["id"],
        brief_payload=bundle["brief"],
        chief_summary=bundle["chief_of_staff_summary"],
        message_text=str(bundle["message_text"]),
        now=effective_now,
    )

    policy = _evaluate_delivery_policy(
        subscription,
        mode="daily_brief",
        prompt_kind=None,
        now=effective_now,
        force=force,
    )

    job = _upsert_scheduled_job(
        conn,
        workspace_id=workspace_id,
        channel_identity_id=identity["id"],
        job_kind="daily_brief",
        prompt_kind=None,
        prompt_id=None,
        continuity_object_id=None,
        continuity_brief_id=brief_record["id"],
        schedule_slot=schedule_slot,
        idempotency_key=resolved_idempotency,
        due_at=due_at,
        payload={
            "scope": "workspace",
            "delivery_policy": policy.as_dict(),
            "message_text_preview": bundle["message_text"],
        },
    )

    if job["status"] in _TERMINAL_JOB_STATUSES:
        receipt_payload, brief_payload = _existing_delivery_artifacts(conn, job=job)
        return {
            "workspace_id": str(workspace_id),
            "job": _serialize_job(job, now=effective_now),
            "brief_record": brief_payload,
            "delivery_receipt": receipt_payload,
            "idempotent_replay": True,
        }

    if policy.allowed:
        outbound, receipt = dispatch_telegram_workspace_message(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            text=str(bundle["message_text"]),
            dispatch_idempotency_key=resolved_idempotency,
            bot_token=bot_token,
            dispatch_payload={"job_kind": "daily_brief", "schedule_slot": schedule_slot},
            scheduled_job_id=job["id"],
            scheduler_job_kind="daily_brief",
            scheduled_for=due_at,
            schedule_slot=schedule_slot,
            notification_policy=policy.as_dict(),
        )
        del outbound
        next_status = receipt["status"]
        suppression_reason = None
    else:
        _, receipt = dispatch_telegram_workspace_message(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            text=str(bundle["message_text"]),
            dispatch_idempotency_key=resolved_idempotency,
            bot_token=bot_token,
            dispatch_payload={"job_kind": "daily_brief", "schedule_slot": schedule_slot},
            receipt_status_override="suppressed",
            failure_code_override=policy.suppression_status,
            failure_detail_override=policy.reason,
            scheduled_job_id=job["id"],
            scheduler_job_kind="daily_brief",
            scheduled_for=due_at,
            schedule_slot=schedule_slot,
            notification_policy=policy.as_dict(),
        )
        next_status = policy.suppression_status or "suppressed_disabled"
        suppression_reason = policy.reason

    updated_job = _update_job_result(
        conn,
        job_id=job["id"],
        status=next_status,
        suppression_reason=suppression_reason,
        delivery_receipt_id=receipt["id"],
        continuity_brief_id=brief_record["id"],
        result_payload={
            "delivery_policy": policy.as_dict(),
            "delivery_receipt_id": str(receipt["id"]),
            "status": next_status,
        },
        now=effective_now,
    )

    return {
        "workspace_id": str(workspace_id),
        "job": _serialize_job(updated_job, now=effective_now),
        "brief_record": _serialize_brief_row(brief_record),
        "delivery_receipt": serialize_delivery_receipt(receipt),
        "idempotent_replay": False,
    }


def list_workspace_open_loop_prompts(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    now: datetime | None = None,
    limit: int = 20,
) -> dict[str, object]:
    effective_now = _utcnow() if now is None else now
    subscription = ensure_workspace_notification_subscription(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    prompts = _build_open_loop_prompt_candidates(
        conn,
        user_account_id=user_account_id,
        now=effective_now,
        limit=limit,
    )
    prompt_ids = [prompt["prompt_id"] for prompt in prompts]
    latest_jobs = _fetch_latest_prompt_jobs(conn, workspace_id=workspace_id, prompt_ids=prompt_ids)

    today_slot = _daily_slot_for_now(now=effective_now, timezone_name=subscription["timezone"])

    items: list[dict[str, object]] = []
    for prompt in prompts:
        latest = latest_jobs.get(prompt["prompt_id"])
        items.append(
            {
                **prompt,
                "prompt_key": _prompt_key(prompt["prompt_kind"], prompt["continuity_object_id"]),
                "latest_job_status": None if latest is None else latest["status"],
                "already_delivered_today": False
                if latest is None
                else latest["schedule_slot"] == today_slot and latest["status"] in _TERMINAL_JOB_STATUSES,
            }
        )

    return {
        "workspace_id": str(workspace_id),
        "notification_preferences": serialize_notification_subscription(subscription, now=effective_now),
        "items": items,
        "summary": {
            "total_count": len(items),
            "returned_count": len(items),
            "prompt_kind_order": ["stale", "waiting_for"],
            "item_order": ["kind_order", "created_at_desc", "id_desc"],
        },
    }


def _resolve_prompt_candidate(
    conn,
    *,
    user_account_id: UUID,
    prompt_id: str,
    now: datetime,
) -> OpenLoopPromptCandidate:
    normalized = prompt_id.strip()
    if normalized == "":
        raise TelegramOpenLoopPromptNotFoundError("prompt_id must not be empty")

    candidates = _build_open_loop_prompt_candidates(
        conn,
        user_account_id=user_account_id,
        now=now,
        limit=MAX_CONTINUITY_OPEN_LOOP_LIMIT,
    )
    for candidate in candidates:
        if candidate["prompt_id"] == normalized:
            return candidate

    raise TelegramOpenLoopPromptNotFoundError(f"open-loop prompt {normalized!r} was not found")


def deliver_workspace_open_loop_prompt(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    prompt_id: str,
    bot_token: str,
    force: bool,
    idempotency_key: str | None,
    now: datetime | None = None,
) -> dict[str, object]:
    effective_now = _utcnow() if now is None else now
    subscription = ensure_workspace_notification_subscription(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    identity = _resolve_linked_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    prompt = _resolve_prompt_candidate(
        conn,
        user_account_id=user_account_id,
        prompt_id=prompt_id,
        now=effective_now,
    )

    continuity_object_id = UUID(prompt["continuity_object_id"])
    schedule_slot = _daily_slot_for_now(now=effective_now, timezone_name=subscription["timezone"])
    due_at = _daily_due_at(
        slot=schedule_slot,
        timezone_name=subscription["timezone"],
        window_start=subscription["daily_brief_window_start"],
    )
    resolved_idempotency = _resolve_internal_idempotency_key(
        workspace_id=workspace_id,
        job_kind="open_loop_prompt",
        schedule_slot=schedule_slot,
        prompt_id=prompt["prompt_id"],
        client_idempotency_key=idempotency_key,
    )
    existing = _fetch_job_by_idempotency(
        conn,
        workspace_id=workspace_id,
        job_kind="open_loop_prompt",
        idempotency_key=resolved_idempotency,
    )
    if existing is not None and existing["status"] in _TERMINAL_JOB_STATUSES:
        receipt_payload, _ = _existing_delivery_artifacts(conn, job=existing)
        return {
            "workspace_id": str(workspace_id),
            "job": _serialize_job(existing, now=effective_now),
            "delivery_receipt": receipt_payload,
            "prompt": prompt,
            "idempotent_replay": True,
        }

    policy = _evaluate_delivery_policy(
        subscription,
        mode="open_loop_prompt",
        prompt_kind=prompt["prompt_kind"],
        now=effective_now,
        force=force,
    )

    job = _upsert_scheduled_job(
        conn,
        workspace_id=workspace_id,
        channel_identity_id=identity["id"],
        job_kind="open_loop_prompt",
        prompt_kind=prompt["prompt_kind"],
        prompt_id=prompt["prompt_id"],
        continuity_object_id=continuity_object_id,
        continuity_brief_id=None,
        schedule_slot=schedule_slot,
        idempotency_key=resolved_idempotency,
        due_at=due_at,
        payload={
            "prompt": prompt,
            "delivery_policy": policy.as_dict(),
        },
    )

    if job["status"] in _TERMINAL_JOB_STATUSES:
        receipt_payload, _ = _existing_delivery_artifacts(conn, job=job)
        return {
            "workspace_id": str(workspace_id),
            "job": _serialize_job(job, now=effective_now),
            "delivery_receipt": receipt_payload,
            "prompt": prompt,
            "idempotent_replay": True,
        }

    if policy.allowed:
        _, receipt = dispatch_telegram_workspace_message(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            text=prompt["message_text"],
            dispatch_idempotency_key=resolved_idempotency,
            bot_token=bot_token,
            dispatch_payload={
                "job_kind": "open_loop_prompt",
                "prompt_id": prompt["prompt_id"],
                "schedule_slot": schedule_slot,
            },
            scheduled_job_id=job["id"],
            scheduler_job_kind="open_loop_prompt",
            scheduled_for=due_at,
            schedule_slot=schedule_slot,
            notification_policy=policy.as_dict(),
        )
        next_status = receipt["status"]
        suppression_reason = None
    else:
        _, receipt = dispatch_telegram_workspace_message(
            conn,
            user_account_id=user_account_id,
            workspace_id=workspace_id,
            text=prompt["message_text"],
            dispatch_idempotency_key=resolved_idempotency,
            bot_token=bot_token,
            dispatch_payload={
                "job_kind": "open_loop_prompt",
                "prompt_id": prompt["prompt_id"],
                "schedule_slot": schedule_slot,
            },
            receipt_status_override="suppressed",
            failure_code_override=policy.suppression_status,
            failure_detail_override=policy.reason,
            scheduled_job_id=job["id"],
            scheduler_job_kind="open_loop_prompt",
            scheduled_for=due_at,
            schedule_slot=schedule_slot,
            notification_policy=policy.as_dict(),
        )
        next_status = policy.suppression_status or "suppressed_disabled"
        suppression_reason = policy.reason

    updated_job = _update_job_result(
        conn,
        job_id=job["id"],
        status=next_status,
        suppression_reason=suppression_reason,
        delivery_receipt_id=receipt["id"],
        continuity_brief_id=None,
        result_payload={
            "delivery_policy": policy.as_dict(),
            "delivery_receipt_id": str(receipt["id"]),
            "status": next_status,
        },
        now=effective_now,
    )

    return {
        "workspace_id": str(workspace_id),
        "job": _serialize_job(updated_job, now=effective_now),
        "delivery_receipt": serialize_delivery_receipt(receipt),
        "prompt": prompt,
        "idempotent_replay": False,
    }


def _materialize_due_jobs(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    subscription: NotificationSubscriptionRow,
    now: datetime,
    prompt_limit: int,
) -> None:
    identity = _resolve_linked_identity(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    schedule_slot = _daily_slot_for_now(now=now, timezone_name=subscription["timezone"])
    due_at = _daily_due_at(
        slot=schedule_slot,
        timezone_name=subscription["timezone"],
        window_start=subscription["daily_brief_window_start"],
    )

    daily_policy = _evaluate_delivery_policy(
        subscription,
        mode="daily_brief",
        prompt_kind=None,
        now=now,
        force=False,
    )
    if daily_policy.window_open and daily_policy.suppression_status != "suppressed_disabled":
        daily_key = f"telegram:daily-brief:{workspace_id}:{schedule_slot}"
        _upsert_scheduled_job(
            conn,
            workspace_id=workspace_id,
            channel_identity_id=identity["id"],
            job_kind="daily_brief",
            prompt_kind=None,
            prompt_id=None,
            continuity_object_id=None,
            continuity_brief_id=None,
            schedule_slot=schedule_slot,
            idempotency_key=daily_key,
            due_at=due_at,
            payload={"materialized_by": "scheduler_jobs", "delivery_policy": daily_policy.as_dict()},
        )

    prompts = _build_open_loop_prompt_candidates(
        conn,
        user_account_id=user_account_id,
        now=now,
        limit=prompt_limit,
    )
    for prompt in prompts:
        prompt_policy = _evaluate_delivery_policy(
            subscription,
            mode="open_loop_prompt",
            prompt_kind=prompt["prompt_kind"],
            now=now,
            force=False,
        )
        if not prompt_policy.window_open:
            continue
        if prompt_policy.suppression_status == "suppressed_disabled":
            continue

        prompt_key = f"telegram:open-loop-prompt:{workspace_id}:{prompt['prompt_id']}:{schedule_slot}"
        _upsert_scheduled_job(
            conn,
            workspace_id=workspace_id,
            channel_identity_id=identity["id"],
            job_kind="open_loop_prompt",
            prompt_kind=prompt["prompt_kind"],
            prompt_id=prompt["prompt_id"],
            continuity_object_id=UUID(prompt["continuity_object_id"]),
            continuity_brief_id=None,
            schedule_slot=schedule_slot,
            idempotency_key=prompt_key,
            due_at=due_at,
            payload={
                "materialized_by": "scheduler_jobs",
                "prompt": prompt,
                "delivery_policy": prompt_policy.as_dict(),
            },
        )


def list_workspace_scheduler_jobs(
    conn,
    *,
    user_account_id: UUID,
    workspace_id: UUID,
    now: datetime | None = None,
    limit: int = 50,
    prompt_limit: int = 20,
) -> dict[str, object]:
    effective_now = _utcnow() if now is None else now
    bounded_limit = min(max(limit, 1), 200)
    bounded_prompt_limit = min(max(prompt_limit, 1), MAX_CONTINUITY_OPEN_LOOP_LIMIT)

    subscription = ensure_workspace_notification_subscription(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
    )
    _materialize_due_jobs(
        conn,
        user_account_id=user_account_id,
        workspace_id=workspace_id,
        subscription=subscription,
        now=effective_now,
        prompt_limit=bounded_prompt_limit,
    )
    jobs = _fetch_jobs_by_workspace(conn, workspace_id=workspace_id, limit=bounded_limit)
    serialized = [_serialize_job(row, now=effective_now) for row in jobs]

    return {
        "workspace_id": str(workspace_id),
        "notification_preferences": serialize_notification_subscription(subscription, now=effective_now),
        "items": serialized,
        "summary": {
            "total_count": len(serialized),
            "due_count": sum(1 for item in serialized if bool(item["is_due"])),
            "order": ["due_at_desc", "id_desc"],
        },
    }


__all__ = [
    "TelegramNotificationPreferenceValidationError",
    "TelegramOpenLoopPromptNotFoundError",
    "deliver_workspace_daily_brief",
    "deliver_workspace_open_loop_prompt",
    "ensure_workspace_notification_subscription",
    "get_workspace_daily_brief_preview",
    "get_workspace_notification_preferences",
    "list_workspace_open_loop_prompts",
    "list_workspace_scheduler_jobs",
    "patch_workspace_notification_subscription",
    "serialize_notification_subscription",
]
