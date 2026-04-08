from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from alicebot_api.chatgpt_import import import_chatgpt_source
from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import ContinuityRecallQueryInput, ContinuityResumptionBriefRequestInput
from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore


REPO_ROOT = Path(__file__).resolve().parents[2]
CHATGPT_FIXTURE_PATH = REPO_ROOT / "fixtures" / "importers" / "chatgpt" / "workspace_v1.json"
THREAD_ID = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def test_chatgpt_import_supports_recall_resumption_and_idempotent_dedupe(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="chatgpt-import@example.com")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)

        first_import = import_chatgpt_source(
            store,
            user_id=user_id,
            source=CHATGPT_FIXTURE_PATH,
        )

        assert first_import["status"] == "ok"
        assert first_import["fixture_id"] == "chatgpt-s37-workspace-v1"
        assert first_import["workspace_id"] == "chatgpt-workspace-demo-001"
        assert first_import["total_candidates"] == 5
        assert first_import["imported_count"] == 4
        assert first_import["skipped_duplicates"] == 1
        assert first_import["provenance_source_kind"] == "chatgpt_import"

        recall = query_continuity_recall(
            store,
            user_id=user_id,
            request=ContinuityRecallQueryInput(
                thread_id=THREAD_ID,
                project="ChatGPT Import Project",
                query="ChatGPT import provenance explicit",
                limit=20,
            ),
        )

        assert recall["summary"]["returned_count"] == 4
        assert all(item["provenance"]["source_kind"] == "chatgpt_import" for item in recall["items"])
        assert all(
            item["provenance"].get("chatgpt_workspace_id") == "chatgpt-workspace-demo-001"
            for item in recall["items"]
        )

        resumption = compile_continuity_resumption_brief(
            store,
            user_id=user_id,
            request=ContinuityResumptionBriefRequestInput(
                thread_id=THREAD_ID,
                project="ChatGPT Import Project",
                query="ChatGPT import provenance explicit",
                max_recent_changes=10,
                max_open_loops=10,
            ),
        )

        brief = resumption["brief"]
        assert brief["last_decision"]["item"] is not None
        assert brief["last_decision"]["item"]["provenance"]["source_kind"] == "chatgpt_import"
        assert brief["next_action"]["item"] is not None
        assert brief["next_action"]["item"]["provenance"]["source_kind"] == "chatgpt_import"

        second_import = import_chatgpt_source(
            store,
            user_id=user_id,
            source=CHATGPT_FIXTURE_PATH,
        )

        assert second_import["status"] == "noop"
        assert second_import["total_candidates"] == 5
        assert second_import["imported_count"] == 0
        assert second_import["skipped_duplicates"] == 5
