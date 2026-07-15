from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

from alicebot_api import contracts


PACKAGE_ROOT = Path(contracts.__file__).resolve().parent
STORE_PATH = PACKAGE_ROOT / "store.py"

REMOVED_RUNTIME_MODULES = (
    "telegram_channels",
    "telegram_continuity",
    "telegram_notifications",
    "hosted_admin",
    "hosted_auth",
    "hosted_devices",
    "hosted_preferences",
    "hosted_rate_limits",
    "hosted_rollout",
    "hosted_telemetry",
    "hosted_workspace",
    "design_partners",
    "chief_of_staff",
    "model_packs",
)

REMOVED_CHANNEL_STORE_ROWS = (
    "ChannelIdentityRow",
    "ChannelLinkChallengeRow",
    "ChannelThreadRow",
    "ChannelMessageRow",
    "ChatIntentRow",
    "ChannelDeliveryReceiptRow",
    "ApprovalChallengeRow",
    "OpenLoopReviewRow",
    "NotificationSubscriptionRow",
    "ContinuityBriefRow",
    "DailyBriefJobRow",
    "ChatTelemetryRow",
)


@pytest.mark.parametrize("module_name", REMOVED_RUNTIME_MODULES)
def test_permanently_removed_runtime_module_is_not_importable_or_packaged(module_name: str) -> None:
    qualified_name = f"alicebot_api.{module_name}"

    assert importlib.util.find_spec(qualified_name) is None
    assert not (PACKAGE_ROOT / f"{module_name}.py").exists()


def test_permanently_removed_public_contracts_are_not_exported() -> None:
    public_names = {name for name in vars(contracts) if not name.startswith("_")}

    deleted_family_prefixes = (
        "ChiefOfStaff",
        "CHIEF_OF_STAFF_",
        "DEFAULT_CHIEF_OF_STAFF_",
        "MAX_CHIEF_OF_STAFF_",
        "Hosted",
        "DesignPartner",
        "ModelPack",
        "WorkspaceModelPack",
        "MODEL_PACK_",
        "DEFAULT_MODEL_PACK_",
        "MAX_MODEL_PACK_",
    )
    assert not {
        name
        for name in public_names
        if name.startswith(deleted_family_prefixes)
    }

    deleted_hosted_channel_names = {
        "ChannelTransportType",
        "ChannelIdentityStatus",
        "ChannelLinkChallengeStatus",
        "ChannelMessageDirection",
        "ChannelMessageRouteStatus",
        "ChatIntentKind",
        "ChatIntentStatus",
        "ChannelDeliveryReceiptStatus",
        "TelegramSchedulerJobKind",
        "TelegramSchedulerPromptKind",
        "TelegramSchedulerJobStatus",
        "DEFAULT_CHANNEL_MESSAGE_LIMIT",
        "MAX_CHANNEL_MESSAGE_LIMIT",
        "CHANNEL_IDENTITY_LIST_ORDER",
        "CHANNEL_LINK_CHALLENGE_LIST_ORDER",
        "CHANNEL_THREAD_LIST_ORDER",
        "CHANNEL_MESSAGE_LIST_ORDER",
        "CHANNEL_DELIVERY_RECEIPT_LIST_ORDER",
        "NotificationSubscriptionRecord",
        "ChannelIdentityRecord",
        "ChannelLinkChallengeRecord",
        "ChannelThreadRecord",
        "ChannelMessageRecord",
        "ChatIntentRecord",
        "ChannelDeliveryReceiptRecord",
        "TelegramContinuityBriefRecord",
        "TelegramDailyBriefJobRecord",
        "ChatTelemetryRecord",
        "ApprovalChallengeRecord",
        "OpenLoopReviewRecord",
    }
    assert public_names.isdisjoint(deleted_hosted_channel_names)


def test_permanently_removed_channel_store_rows_are_absent_from_source_and_ast() -> None:
    store_source = STORE_PATH.read_text(encoding="utf-8")
    class_names = {
        node.name
        for node in ast.walk(ast.parse(store_source))
        if isinstance(node, ast.ClassDef)
    }

    assert class_names.isdisjoint(REMOVED_CHANNEL_STORE_ROWS)
    assert not [
        class_name
        for class_name in REMOVED_CHANNEL_STORE_ROWS
        if f"class {class_name}(" in store_source
    ]
