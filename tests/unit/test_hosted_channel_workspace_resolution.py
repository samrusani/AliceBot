from __future__ import annotations

import inspect
from uuid import uuid4

import alicebot_api.main as main_module


WORKSPACE_QUERY_HANDLERS = (
    main_module.list_v1_telegram_messages,
    main_module.list_v1_telegram_threads,
    main_module.dispatch_v1_telegram_message,
    main_module.list_v1_telegram_delivery_receipts,
    main_module.get_v1_telegram_notification_preferences,
    main_module.patch_v1_telegram_notification_preferences,
    main_module.get_v1_telegram_daily_brief,
    main_module.post_v1_telegram_daily_brief_deliver,
    main_module.list_v1_telegram_open_loop_prompts,
    main_module.post_v1_telegram_open_loop_prompt_deliver,
    main_module.list_v1_telegram_scheduler_jobs,
    main_module.handle_v1_telegram_message,
    main_module.get_v1_telegram_message_result,
    main_module.list_v1_telegram_recall,
    main_module.get_v1_telegram_resumption_brief,
    main_module.get_v1_telegram_open_loops,
    main_module.review_action_v1_telegram_open_loop,
    main_module.list_v1_telegram_approvals,
    main_module.approve_v1_telegram_approval,
    main_module.reject_v1_telegram_approval,
)


def test_all_hosted_telegram_workspace_handlers_expose_explicit_selection() -> None:
    assert "workspace_id" in main_module.TelegramLinkStartRequest.model_fields
    assert "workspace_id" in main_module.TelegramUnlinkRequest.model_fields
    assert "workspace_id" in inspect.signature(main_module.get_v1_telegram_status).parameters

    for handler in WORKSPACE_QUERY_HANDLERS:
        parameter = inspect.signature(handler).parameters.get("workspace_id")
        assert parameter is not None, handler.__name__
        assert parameter.default is None, handler.__name__


def test_explicit_hosted_channel_workspace_resolution_does_not_change_session(monkeypatch) -> None:
    user_account_id = uuid4()
    session_id = uuid4()
    current_workspace_id = uuid4()
    requested_workspace_id = uuid4()
    requested_workspace = {"id": requested_workspace_id}

    def get_requested_workspace(_conn, *, workspace_id, user_account_id):
        assert workspace_id == requested_workspace_id
        assert user_account_id == user_account_id_for_request
        return requested_workspace

    user_account_id_for_request = user_account_id
    monkeypatch.setattr(main_module, "get_workspace_for_member", get_requested_workspace)

    def fail_if_session_changes(*_args, **_kwargs) -> None:
        raise AssertionError("hosted channel workspace resolution must not change session selection")

    monkeypatch.setattr(main_module, "set_session_workspace", fail_if_session_changes)

    resolved = main_module._resolve_workspace_for_hosted_channel_request(
        object(),
        user_account_id=user_account_id,
        session_id=session_id,
        preferred_workspace_id=current_workspace_id,
        requested_workspace_id=requested_workspace_id,
    )

    assert resolved is requested_workspace
