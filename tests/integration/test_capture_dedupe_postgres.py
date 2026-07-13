"""Atomic source capture identity against a real PostgreSQL database."""

from __future__ import annotations

import threading
from uuid import uuid4

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_capture import VNextCaptureService
from alicebot_api.vnext_store import PostgresVNextStore


def test_two_connections_claim_one_source_dedupe_identity(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    user_id = uuid4()
    with user_connection(app_url, user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"capture-{user_id}@example.invalid",
            "Capture dedupe",
        )

    start = threading.Barrier(2)
    outcomes: list[tuple[str, bool] | Exception] = []
    outcomes_lock = threading.Lock()
    source = {
        "source_type": "note",
        "title": "Concurrent capture",
        "content_hash": "raw-text-digest",
        "dedupe_key": "project-scope-dedupe-identity",
        "domain": "project",
        "sensitivity": "internal",
        "metadata_json": {"project_scope": ["alpha"]},
    }

    def capture() -> None:
        try:
            with user_connection(app_url, user_id) as conn:
                start.wait(timeout=10)
                row, created = PostgresVNextStore(conn).get_or_create_source(source)
                outcome: tuple[str, bool] | Exception = (str(row["id"]), created)
        except Exception as exc:  # noqa: BLE001 - surfaced by assertions below
            outcome = exc
        with outcomes_lock:
            outcomes.append(outcome)

    workers = [threading.Thread(target=capture), threading.Thread(target=capture)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
        assert not worker.is_alive(), "capture dedupe worker did not finish"

    assert not any(isinstance(outcome, Exception) for outcome in outcomes), outcomes
    rows = [outcome for outcome in outcomes if isinstance(outcome, tuple)]
    assert len(rows) == 2
    assert len({row_id for row_id, _created in rows}) == 1
    assert sorted(created for _row_id, created in rows) == [False, True]

    with user_connection(app_url, user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) AS count FROM sources WHERE dedupe_key = %s",
                (source["dedupe_key"],),
            )
            count = int(cur.fetchone()["count"])
    assert count == 1


def test_exact_recapture_with_changed_classification_preserves_postgres_source_and_candidate(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    user_id = uuid4()
    with user_connection(app_url, user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"capture-classification-{user_id}@example.invalid",
            "Capture classification",
        )
        store = PostgresVNextStore(conn)
        service = VNextCaptureService(store)
        text = "Fact: The release rehearsal is scheduled for Friday."

        first = service.capture_text(
            text,
            domain="project",
            sensitivity="public",
            project_scope=("Alpha",),
        )
        reclassified = service.capture_text(
            text,
            domain="professional",
            sensitivity="private",
            project_scope=("Alpha",),
        )
        repeated = service.capture_text(
            text,
            domain="professional",
            sensitivity="private",
            project_scope=("Alpha",),
        )

        assert first.status == "imported"
        assert reclassified.status == "imported"
        assert reclassified.source_id != first.source_id
        assert repeated.status == "duplicate"
        assert repeated.source_id == reclassified.source_id

        first_source = store.get_source(first.source_id)
        reclassified_source = store.get_source(reclassified.source_id)
        assert first_source is not None and reclassified_source is not None
        assert (first_source["domain"], first_source["sensitivity"]) == ("project", "public")
        assert (reclassified_source["domain"], reclassified_source["sensitivity"]) == (
            "professional",
            "private",
        )

        classified_candidates = {
            (str(row["domain"]), str(row["sensitivity"]))
            for row in store.list_memories(status="candidate")
            if row["metadata_json"].get("source_id") in {first.source_id, reclassified.source_id}
        }
        assert classified_candidates == {("project", "public"), ("professional", "private")}
