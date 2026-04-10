from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from alicebot_api.continuity_evidence import build_continuity_explain
from alicebot_api.continuity_recall import query_continuity_recall
from alicebot_api.continuity_resumption import compile_continuity_resumption_brief
from alicebot_api.contracts import ContinuityRecallQueryInput, ContinuityResumptionBriefRequestInput
from alicebot_api.db import user_connection
from alicebot_api.markdown_import import MarkdownImportValidationError, import_markdown_source
from alicebot_api.store import ContinuityStore


REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_FIXTURE_PATH = REPO_ROOT / "fixtures" / "importers" / "markdown" / "workspace_v1.md"
THREAD_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")


def seed_user(database_url: str, *, email: str) -> UUID:
    user_id = uuid4()
    with user_connection(database_url, user_id) as conn:
        ContinuityStore(conn).create_user(user_id, email, email.split("@", 1)[0].title())
    return user_id


def test_markdown_import_supports_recall_resumption_and_idempotent_dedupe(migrated_database_urls) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="markdown-import@example.com")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = ContinuityStore(conn)

        first_import = import_markdown_source(
            store,
            user_id=user_id,
            source=MARKDOWN_FIXTURE_PATH,
        )

        assert first_import["status"] == "ok"
        assert first_import["fixture_id"] == "markdown-s37-workspace-v1"
        assert first_import["workspace_id"] == "markdown-workspace-demo-001"
        assert first_import["total_candidates"] == 5
        assert first_import["imported_count"] == 4
        assert first_import["skipped_duplicates"] == 1
        assert first_import["provenance_source_kind"] == "markdown_import"

        recall = query_continuity_recall(
            store,
            user_id=user_id,
            request=ContinuityRecallQueryInput(
                thread_id=THREAD_ID,
                project="Markdown Import Project",
                query="markdown importer deterministic",
                limit=20,
            ),
        )

        assert recall["summary"]["returned_count"] == 4
        assert all(item["provenance"]["source_kind"] == "markdown_import" for item in recall["items"])
        assert all(
            item["provenance"].get("markdown_workspace_id") == "markdown-workspace-demo-001"
            for item in recall["items"]
        )
        assert all(item["provenance"].get("artifact_id") is not None for item in recall["items"])
        assert all(item["provenance"].get("artifact_segment_id") is not None for item in recall["items"])

        explain = build_continuity_explain(
            store,
            user_id=user_id,
            continuity_object_id=UUID(first_import["imported_object_ids"][0]),
        )
        assert len(explain["explain"]["evidence_chain"]) == 1
        assert explain["explain"]["evidence_chain"][0]["artifact"]["source_kind"] == "markdown_import"
        assert explain["explain"]["evidence_chain"][0]["artifact_segment"] is not None
        assert (
            explain["explain"]["evidence_chain"][0]["artifact_segment"]["segment_kind"]
            == "markdown_line"
        )
        assert explain["explain"]["evidence_chain"][0]["artifact_copy"]["content_text"] != ""

        resumption = compile_continuity_resumption_brief(
            store,
            user_id=user_id,
            request=ContinuityResumptionBriefRequestInput(
                thread_id=THREAD_ID,
                project="Markdown Import Project",
                query="markdown importer deterministic",
                max_recent_changes=10,
                max_open_loops=10,
            ),
        )

        brief = resumption["brief"]
        assert brief["last_decision"]["item"] is not None
        assert brief["last_decision"]["item"]["provenance"]["source_kind"] == "markdown_import"
        assert brief["next_action"]["item"] is not None
        assert brief["next_action"]["item"]["provenance"]["source_kind"] == "markdown_import"

        second_import = import_markdown_source(
            store,
            user_id=user_id,
            source=MARKDOWN_FIXTURE_PATH,
        )

        assert second_import["status"] == "noop"
        assert second_import["total_candidates"] == 5
        assert second_import["imported_count"] == 0
        assert second_import["skipped_duplicates"] == 5


def test_markdown_import_archives_source_before_failed_extraction(migrated_database_urls, tmp_path: Path) -> None:
    user_id = seed_user(migrated_database_urls["app"], email="markdown-import-failure@example.com")
    broken_source = tmp_path / "broken.md"
    broken_source.write_text("---\nfixture_id: broken\n- Decision: missing frontmatter close\n", encoding="utf-8")

    with pytest.raises(MarkdownImportValidationError, match="frontmatter"):
        with user_connection(migrated_database_urls["app"], user_id) as conn:
            import_markdown_source(
                ContinuityStore(conn),
                user_id=user_id,
                source=broken_source,
            )

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT relative_path FROM continuity_artifacts ORDER BY relative_path ASC")
            artifacts = cur.fetchall()
            cur.execute("SELECT content_text FROM continuity_artifact_copies ORDER BY created_at ASC, id ASC")
            copies = cur.fetchall()
            cur.execute("SELECT COUNT(*) AS count FROM continuity_artifact_segments")
            segments_row = cur.fetchone()

    assert artifacts == [{"relative_path": "broken.md"}]
    assert copies == [{"content_text": broken_source.read_text(encoding="utf-8")}]
    assert segments_row == {"count": 0}
