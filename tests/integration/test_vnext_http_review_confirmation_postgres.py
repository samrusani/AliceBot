from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

import apps.api.src.alicebot_api.main as main_module
from apps.api.src.alicebot_api.config import Settings
from alicebot_api.db import user_connection
from alicebot_api.vnext_store import PostgresVNextStore
from tests.integration.test_vnext_live_workspace_api import invoke_request, seed_user


def _seed_pending_confirmation(database_url: str, user_id: UUID, *, label: str) -> str:
    with user_connection(database_url, user_id) as conn:
        row = PostgresVNextStore(conn).create_memory(
            {
                "memory_key": f"http-review-confirmation.{label}.{uuid4()}",
                "value": {"text": f"Pending confirmation for {label}."},
                "status": "needs_review",
                "memory_type": "semantic",
                "title": f"Pending confirmation {label}",
                "canonical_text": f"Pending confirmation for {label}.",
                "summary": f"Pending confirmation for {label}.",
                "domain": "professional",
                "sensitivity": "internal",
                "confirmation_status": "unconfirmed",
                "metadata_json": {
                    "review_required": True,
                    "agentic_memory": {
                        "status": "confirmation_required",
                        "write_mode": "confirm_inline",
                        "lifecycle_status": "pending_inline_confirmation",
                        "requires_dashboard_review": True,
                        "confirmation": {
                            "confirmation_id": str(uuid4()),
                            "status": "pending",
                        },
                    },
                },
            }
        )
    return str(row["id"])


def _parsed_timestamp(value: object) -> datetime:
    assert isinstance(value, str)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.mark.parametrize("action", ["accept", "edit", "promote", "reject"])
def test_public_http_terminal_reviews_close_postgres_confirmation_metadata(
    migrated_database_urls,
    monkeypatch,
    action: str,
) -> None:
    database_url = migrated_database_urls["app"]
    user_id = seed_user(database_url, email="http-review-confirmation@example.com")
    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(database_url=database_url))

    memory_id = _seed_pending_confirmation(database_url, user_id, label=action)
    payload: dict[str, object] = {
        "user_id": str(user_id),
        "action": action,
        "reason": f"Exercise public HTTP {action} terminal metadata.",
    }
    if action == "edit":
        payload["canonical_text"] = "Edited and confirmed through public HTTP."

    status, response = invoke_request(
        "POST",
        f"/v0/vnext/memories/{memory_id}/review",
        payload=payload,
    )

    assert status == 200, response
    with user_connection(database_url, user_id) as conn:
        memory = PostgresVNextStore(conn).get_memory(memory_id)
    assert memory is not None
    assert memory["last_reviewed_at"] is not None
    metadata = memory["metadata_json"]
    assert metadata["review_required"] is False
    agentic = metadata["agentic_memory"]
    assert agentic["requires_dashboard_review"] is False
    confirmation = agentic["confirmation"]

    if action == "reject":
        assert memory["status"] == "rejected"
        assert memory["confirmation_status"] == "unconfirmed"
        assert memory["last_confirmed_at"] is None
        assert agentic["status"] == "rejected"
        assert agentic["lifecycle_status"] == "review_rejected"
        assert confirmation["status"] == "rejected"
        assert _parsed_timestamp(confirmation["rejected_at"]) == memory["last_reviewed_at"]
    else:
        assert memory["status"] == "active"
        assert memory["confirmation_status"] == "confirmed"
        assert memory["last_confirmed_at"] is not None
        assert agentic["status"] == "committed"
        assert agentic["lifecycle_status"] == "dashboard_review_accepted"
        assert confirmation["status"] == "confirmed"
        assert _parsed_timestamp(confirmation["confirmed_at"]) == memory["last_confirmed_at"]
        if action == "edit":
            assert memory["canonical_text"] == "Edited and confirmed through public HTTP."
