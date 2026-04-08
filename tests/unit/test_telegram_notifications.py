from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import alicebot_api.telegram_notifications as notifications


def _subscription_row(**overrides):
    row = {
        "id": uuid4(),
        "workspace_id": uuid4(),
        "channel_type": "telegram",
        "channel_identity_id": uuid4(),
        "notifications_enabled": True,
        "daily_brief_enabled": True,
        "daily_brief_window_start": "07:00",
        "open_loop_prompts_enabled": True,
        "waiting_for_prompts_enabled": True,
        "stale_prompts_enabled": True,
        "timezone": "Europe/Stockholm",
        "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00",
        "created_at": datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
    }
    row.update(overrides)
    return row


def test_delivery_policy_enforces_quiet_hours_deterministically() -> None:
    subscription = _subscription_row()

    policy = notifications._evaluate_delivery_policy(
        subscription,
        mode="daily_brief",
        prompt_kind=None,
        now=datetime(2026, 4, 8, 21, 30, tzinfo=UTC),
        force=False,
    )

    assert policy.allowed is False
    assert policy.suppression_status == "suppressed_quiet_hours"
    assert policy.quiet_hours_active is True


def test_materialize_due_jobs_selects_daily_and_prompt_jobs(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    monkeypatch.setattr(
        notifications,
        "_resolve_linked_identity",
        lambda *_args, **_kwargs: {"id": uuid4()},
    )
    monkeypatch.setattr(
        notifications,
        "_build_open_loop_prompt_candidates",
        lambda *_args, **_kwargs: [
            {
                "prompt_id": "stale:11111111-1111-4111-8111-111111111111",
                "prompt_kind": "stale",
                "continuity_object_id": "11111111-1111-4111-8111-111111111111",
                "title": "Stale item",
                "continuity_status": "stale",
                "review_action_hint": "deferred",
                "due_at": datetime(2026, 4, 8, 8, 0, tzinfo=UTC).isoformat(),
                "message_text": "prompt",
            },
            {
                "prompt_id": "waiting_for:22222222-2222-4222-8222-222222222222",
                "prompt_kind": "waiting_for",
                "continuity_object_id": "22222222-2222-4222-8222-222222222222",
                "title": "Waiting for item",
                "continuity_status": "active",
                "review_action_hint": "still_blocked",
                "due_at": datetime(2026, 4, 8, 8, 0, tzinfo=UTC).isoformat(),
                "message_text": "prompt",
            },
        ],
    )

    def _capture_upsert(_conn, **kwargs):
        captured.append(kwargs)
        return {
            "id": uuid4(),
            "workspace_id": kwargs["workspace_id"],
            "channel_type": "telegram",
            "channel_identity_id": kwargs["channel_identity_id"],
            "job_kind": kwargs["job_kind"],
            "prompt_kind": kwargs["prompt_kind"],
            "prompt_id": kwargs["prompt_id"],
            "continuity_object_id": kwargs["continuity_object_id"],
            "continuity_brief_id": kwargs["continuity_brief_id"],
            "schedule_slot": kwargs["schedule_slot"],
            "idempotency_key": kwargs["idempotency_key"],
            "due_at": kwargs["due_at"],
            "status": "scheduled",
            "suppression_reason": None,
            "attempt_count": 0,
            "delivery_receipt_id": None,
            "payload": kwargs["payload"],
            "result_payload": {},
            "attempted_at": None,
            "completed_at": None,
            "created_at": datetime(2026, 4, 8, 8, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 4, 8, 8, 0, tzinfo=UTC),
        }

    monkeypatch.setattr(notifications, "_upsert_scheduled_job", _capture_upsert)

    workspace_id = uuid4()
    subscription = _subscription_row(
        workspace_id=workspace_id,
        quiet_hours_enabled=False,
        timezone="UTC",
        daily_brief_window_start="07:00",
    )

    notifications._materialize_due_jobs(
        conn=object(),
        user_account_id=uuid4(),
        workspace_id=workspace_id,
        subscription=subscription,
        now=datetime(2026, 4, 8, 8, 0, tzinfo=UTC),
        prompt_limit=5,
    )

    assert len(captured) == 3
    assert [item["job_kind"] for item in captured] == [
        "daily_brief",
        "open_loop_prompt",
        "open_loop_prompt",
    ]


def test_daily_brief_bundle_uses_continuity_and_chief_of_staff_sources(monkeypatch) -> None:
    monkeypatch.setattr(notifications, "set_current_user", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        notifications,
        "compile_continuity_daily_brief",
        lambda *_args, **_kwargs: {
            "brief": {
                "assembly_version": "continuity_daily_brief_v0",
                "waiting_for_highlights": {"summary": {"total_count": 2}},
                "blocker_highlights": {"summary": {"total_count": 1}},
                "stale_items": {"summary": {"total_count": 1}},
                "next_suggested_action": {"item": {"title": "Next Action: Ship P10-S4"}},
            }
        },
    )
    monkeypatch.setattr(
        notifications,
        "compile_chief_of_staff_priority_brief",
        lambda *_args, **_kwargs: {
            "brief": {
                "summary": {
                    "trust_confidence_posture": "medium",
                    "follow_through_total_count": 3,
                },
                "recommended_next_action": {"title": "Follow up waiting-for dependency"},
            }
        },
    )

    bundle = notifications._build_daily_brief_bundle(
        conn=object(),
        user_account_id=uuid4(),
        timezone_name="UTC",
        now=datetime(2026, 4, 8, 8, 0, tzinfo=UTC),
    )

    assert bundle["brief"]["assembly_version"] == "continuity_daily_brief_v0"
    assert bundle["chief_of_staff_summary"]["trust_confidence_posture"] == "medium"
    assert "Waiting-for: 2" in bundle["message_text"]
    assert "Chief-of-staff recommendation: Follow up waiting-for dependency" in bundle["message_text"]


def test_internal_idempotency_key_scopes_custom_values_by_workspace() -> None:
    shared_client_key = "same-client-key"
    workspace_a = uuid4()
    workspace_b = uuid4()

    key_a = notifications._resolve_internal_idempotency_key(
        workspace_id=workspace_a,
        job_kind="daily_brief",
        schedule_slot="2026-04-08",
        prompt_id=None,
        client_idempotency_key=shared_client_key,
    )
    key_b = notifications._resolve_internal_idempotency_key(
        workspace_id=workspace_b,
        job_kind="daily_brief",
        schedule_slot="2026-04-08",
        prompt_id=None,
        client_idempotency_key=shared_client_key,
    )

    assert key_a != key_b
    assert key_a.startswith("telegram:daily_brief:custom:")
    assert key_b.startswith("telegram:daily_brief:custom:")
