from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import ContinuityRecallQueryInput, ContinuityResumptionBriefRequestInput
from alicebot_api.db import user_connection
from alicebot_api.openclaw_import import import_openclaw_source
from alicebot_api.store import ContinuityStore


REPO_ROOT = Path(__file__).resolve().parents[2]
OPENCLAW_FIXTURE_PATH = REPO_ROOT / "fixtures" / "openclaw" / "workspace_v1.json"
OPENCLAW_DIRECTORY_FIXTURE_PATH = REPO_ROOT / "fixtures" / "openclaw" / "workspace_dir_v1"
THREAD_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


@pytest.mark.parametrize(
    ("source_path", "expected_fixture_id", "expected_workspace_id", "expected_total_candidates", "expected_imported_count"),
    [
        (
            OPENCLAW_FIXTURE_PATH,
            "openclaw-s36-workspace-v1",
            "openclaw-workspace-demo-001",
            5,
            4,
        ),
        (
            OPENCLAW_DIRECTORY_FIXTURE_PATH,
            "openclaw-s39-workspace-dir-v1",
            "openclaw-workspace-dir-demo-001",
            4,
            3,
        ),
    ],
)
def test_openclaw_import_supports_recall_resumption_and_idempotent_dedupe(
    migrated_database_urls,
    source_path: Path,
    expected_fixture_id: str,
    expected_workspace_id: str,
    expected_total_candidates: int,
    expected_imported_count: int,
) -> None:
    user_id = seed_user(
        migrated_database_urls["app"],
        email=f"openclaw-import-{expected_fixture_id}@example.com",
    )

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)

        first_import = import_openclaw_source(
            store,
            user_id=user_id,
            source=source_path,
        )

        assert first_import["status"] == "ok"
        assert first_import["fixture_id"] == expected_fixture_id
        assert first_import["workspace_id"] == expected_workspace_id
        assert first_import["total_candidates"] == expected_total_candidates
        assert first_import["imported_count"] == expected_imported_count
        assert first_import["skipped_duplicates"] == 1
        assert first_import["provenance_source_kind"] == "openclaw_import"
        assert first_import["provenance_source_label"] == "OpenClaw"

        recall = query_continuity_recall(
            store,
            user_id=user_id,
            request=ContinuityRecallQueryInput(
                thread_id=THREAD_ID,
                project="Alice Public Core",
                limit=20,
            ),
        )

        assert recall["summary"]["returned_count"] == expected_imported_count
        assert all(item["provenance"]["source_kind"] == "openclaw_import" for item in recall["items"])
        assert all(item["provenance"]["source_label"] == "OpenClaw" for item in recall["items"])
        assert all(
            item["provenance"].get("openclaw_workspace_id") == expected_workspace_id
            for item in recall["items"]
        )

        resumption = compile_continuity_resumption_brief(
            store,
            user_id=user_id,
            request=ContinuityResumptionBriefRequestInput(
                thread_id=THREAD_ID,
                max_recent_changes=10,
                max_open_loops=10,
            ),
        )

        brief = resumption["brief"]
        assert brief["last_decision"]["item"] is not None
        assert brief["last_decision"]["item"]["provenance"]["source_kind"] == "openclaw_import"
        assert brief["last_decision"]["item"]["provenance"]["source_label"] == "OpenClaw"
        assert brief["next_action"]["item"] is not None
        assert brief["next_action"]["item"]["provenance"]["source_kind"] == "openclaw_import"
        assert brief["next_action"]["item"]["provenance"]["source_label"] == "OpenClaw"

        second_import = import_openclaw_source(
            store,
            user_id=user_id,
            source=source_path,
        )

        assert second_import["status"] == "noop"
        assert second_import["total_candidates"] == expected_total_candidates
        assert second_import["imported_count"] == 0
        assert second_import["skipped_duplicates"] == expected_total_candidates
