from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from alicebot_api.config import Settings
import alicebot_api.hosted_rate_limits as hosted_rate_limits
import alicebot_api.hosted_rollout as hosted_rollout
import alicebot_api.hosted_telemetry as hosted_telemetry


class RecordingCursor:
    def __init__(
        self,
        *,
        fetchone_results: list[dict[str, Any] | None] | None = None,
        fetchall_results: list[list[dict[str, Any]]] | None = None,
    ) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self._fetchone_results:
            return None
        return self._fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        if not self._fetchall_results:
            return []
        return self._fetchall_results.pop(0)


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def _base_settings() -> Settings:
    return Settings(
        app_env="test",
        hosted_chat_rate_limit_window_seconds=60,
        hosted_chat_rate_limit_max_requests=1,
        hosted_scheduler_rate_limit_window_seconds=300,
        hosted_scheduler_rate_limit_max_requests=1,
        hosted_abuse_window_seconds=120,
        hosted_abuse_block_threshold=2,
        hosted_rate_limits_enabled_by_default=True,
        hosted_abuse_controls_enabled_by_default=True,
    )


def test_resolve_rollout_flag_returns_missing_when_flag_is_absent() -> None:
    cursor = RecordingCursor(
        fetchone_results=[
            {"beta_cohort_key": "p10-beta"},
            None,
        ]
    )
    conn = RecordingConnection(cursor)

    resolved = hosted_rollout.resolve_rollout_flag(
        conn,
        user_account_id=uuid4(),
        flag_key="hosted_chat_handle_enabled",
    )

    assert resolved == {
        "flag_key": "hosted_chat_handle_enabled",
        "enabled": False,
        "source_scope": "missing",
        "source_cohort_key": None,
        "description": None,
        "updated_at": "",
    }
    assert "FROM user_accounts" in cursor.executed[0][0]
    assert "FROM feature_flags" in cursor.executed[1][0]


def test_ensure_rollout_flag_enabled_raises_when_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        hosted_rollout,
        "resolve_rollout_flag",
        lambda *_args, **_kwargs: {
            "flag_key": "hosted_scheduler_delivery_enabled",
            "enabled": False,
            "source_scope": "global",
            "source_cohort_key": None,
            "description": None,
            "updated_at": "2026-04-09T00:00:00+00:00",
        },
    )

    with pytest.raises(hosted_rollout.RolloutFlagBlockedError, match="disabled"):
        hosted_rollout.ensure_rollout_flag_enabled(
            object(),
            user_account_id=uuid4(),
            flag_key="hosted_scheduler_delivery_enabled",
        )


def test_list_rollout_flags_for_admin_prefers_cohort_over_global() -> None:
    now = datetime(2026, 4, 9, 8, 0, tzinfo=UTC)
    cursor = RecordingCursor(
        fetchone_results=[{"beta_cohort_key": "p10-beta"}],
        fetchall_results=[
            [
                {
                    "id": uuid4(),
                    "flag_key": "hosted_chat_handle_enabled",
                    "cohort_key": "p10-beta",
                    "enabled": True,
                    "description": "cohort override",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": uuid4(),
                    "flag_key": "hosted_chat_handle_enabled",
                    "cohort_key": None,
                    "enabled": False,
                    "description": "global",
                    "created_at": now,
                    "updated_at": now - timedelta(minutes=1),
                },
                {
                    "id": uuid4(),
                    "flag_key": "hosted_rate_limits_enabled",
                    "cohort_key": None,
                    "enabled": True,
                    "description": "global",
                    "created_at": now,
                    "updated_at": now,
                },
            ]
        ],
    )
    conn = RecordingConnection(cursor)

    items = hosted_rollout.list_rollout_flags_for_admin(conn, user_account_id=uuid4())

    assert [item["flag_key"] for item in items] == [
        "hosted_chat_handle_enabled",
        "hosted_rate_limits_enabled",
    ]
    assert items[0]["enabled"] is True
    assert items[0]["source_scope"] == "cohort"


def test_patch_rollout_flags_rejects_unknown_cohort() -> None:
    cursor = RecordingCursor(fetchone_results=[None])
    conn = RecordingConnection(cursor)

    with pytest.raises(ValueError, match="was not found"):
        hosted_rollout.patch_rollout_flags(
            conn,
            patches=[
                {
                    "flag_key": "hosted_admin_read",
                    "enabled": True,
                    "cohort_key": "missing-cohort",
                    "description": "test",
                }
            ],
            allowed_cohort_key="missing-cohort",
        )


def test_patch_rollout_flags_rejects_non_hosted_flag_keys() -> None:
    cursor = RecordingCursor()
    conn = RecordingConnection(cursor)

    with pytest.raises(ValueError, match="must start with 'hosted_'"):
        hosted_rollout.patch_rollout_flags(
            conn,
            patches=[
                {
                    "flag_key": "calendar_ingest_enabled",
                    "enabled": True,
                    "cohort_key": "p10-beta",
                    "description": "out-of-scope flag",
                }
            ],
            allowed_cohort_key="p10-beta",
        )


def test_evaluate_hosted_flow_limits_blocks_when_rate_limit_is_exceeded() -> None:
    now = datetime(2026, 4, 9, 9, 0, tzinfo=UTC)
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "total_count": 1,
                "oldest_created_at": now - timedelta(seconds=10),
            },
            {
                "blocked_count": 0,
                "oldest_created_at": None,
            },
        ]
    )
    conn = RecordingConnection(cursor)

    decision = hosted_rate_limits.evaluate_hosted_flow_limits(
        conn,
        settings=_base_settings(),
        user_account_id=uuid4(),
        workspace_id=uuid4(),
        flow_kind="chat_handle",
        now=now,
    )

    assert decision["allowed"] is False
    assert decision["code"] == "hosted_rate_limit_exceeded"
    assert decision["observed_requests"] == 1
    assert decision["retry_after_seconds"] == 50


def test_evaluate_hosted_flow_limits_blocks_when_abuse_threshold_is_reached() -> None:
    now = datetime(2026, 4, 9, 9, 0, tzinfo=UTC)
    settings = Settings(
        app_env="test",
        hosted_chat_rate_limit_window_seconds=60,
        hosted_chat_rate_limit_max_requests=1,
        hosted_scheduler_rate_limit_window_seconds=300,
        hosted_scheduler_rate_limit_max_requests=1,
        hosted_abuse_window_seconds=120,
        hosted_abuse_block_threshold=1,
        hosted_rate_limits_enabled_by_default=True,
        hosted_abuse_controls_enabled_by_default=True,
    )

    cursor = RecordingCursor(
        fetchone_results=[
            {
                "total_count": 0,
                "oldest_created_at": None,
            },
            {
                "blocked_count": 1,
                "oldest_created_at": now - timedelta(seconds=15),
            },
        ]
    )
    conn = RecordingConnection(cursor)

    decision = hosted_rate_limits.evaluate_hosted_flow_limits(
        conn,
        settings=settings,
        user_account_id=uuid4(),
        workspace_id=uuid4(),
        flow_kind="chat_handle",
        now=now,
    )

    assert decision["allowed"] is False
    assert decision["code"] == "hosted_abuse_limit_exceeded"
    assert decision["abuse_signal"] == "repeated_rate_limit_violations"
    assert decision["retry_after_seconds"] == 105


def test_record_chat_telemetry_requires_non_empty_route_path() -> None:
    with pytest.raises(ValueError, match="route_path is required"):
        hosted_telemetry.record_chat_telemetry(
            object(),
            user_account_id=uuid4(),
            workspace_id=None,
            flow_kind="chat_handle",
            event_kind="attempt",
            status="ok",
            route_path="   ",
        )


def test_aggregate_chat_telemetry_rolls_up_flow_status_and_hourly_rows(monkeypatch) -> None:
    now = datetime(2026, 4, 9, 10, 0, tzinfo=UTC)
    cursor = RecordingCursor(
        fetchall_results=[
            [
                {
                    "flow_kind": "chat_handle",
                    "status": "ok",
                    "total_count": 3,
                },
                {
                    "flow_kind": "chat_handle",
                    "status": "failed",
                    "total_count": 1,
                },
                {
                    "flow_kind": "scheduler_daily_brief",
                    "status": "rate_limited",
                    "total_count": 2,
                },
            ],
            [
                {
                    "hour_bucket": now - timedelta(hours=1),
                    "total_count": 6,
                    "ok_count": 3,
                    "failed_count": 1,
                    "blocked_rollout_count": 0,
                    "rate_limited_count": 2,
                    "abuse_blocked_count": 0,
                }
            ],
        ]
    )
    conn = RecordingConnection(cursor)

    monkeypatch.setattr(hosted_telemetry, "utc_now", lambda: now)

    payload = hosted_telemetry.aggregate_chat_telemetry(conn, window_hours=24)

    assert payload["window_hours"] == 24
    assert payload["total_events"] == 6
    assert payload["flow_counts"] == {
        "chat_handle": 4,
        "scheduler_daily_brief": 2,
    }
    assert payload["status_counts"] == {
        "ok": 3,
        "failed": 1,
        "rate_limited": 2,
    }
    assert payload["flow_status_matrix"]["chat_handle"]["ok"] == 3
    assert payload["hourly"][0]["total_count"] == 6
