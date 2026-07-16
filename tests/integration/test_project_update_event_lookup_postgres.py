"""Live PostgreSQL coverage for bounded project-update terminal evidence reads."""

from __future__ import annotations

from uuid import uuid4

import psycopg

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_store import PostgresVNextStore, _PROJECT_UPDATE_EVENT_LOOKUP_SQL


def test_live_postgres_project_update_event_lookup_is_exact_and_indexed(
    migrated_database_urls,
) -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    artifact_id = str(uuid4())
    candidate_memory_id = str(uuid4())
    expected_event_ids = [str(uuid4()) for _ in range(4)]
    expected_ids = set(expected_event_ids)
    events = (
        {
            "id": expected_event_ids[0],
            "event_type": "project.update_candidate_created",
            "target_type": "artifact",
            "target_id": artifact_id,
            "payload_json": {
                "artifact_id": artifact_id,
                "candidate_memory_id": candidate_memory_id,
                "memory_id": candidate_memory_id,
            },
            "occurred_at": "2030-07-10T12:00:00Z",
        },
        {
            "id": expected_event_ids[1],
            "event_type": "project.update_candidate_created",
            "target_type": "artifact",
            "target_id": str(uuid4()),
            "payload_json": {"memory_id": candidate_memory_id},
            "occurred_at": "2030-07-10T12:01:00Z",
        },
        {
            "id": expected_event_ids[2],
            "event_type": "project.update_candidate_accepted",
            "target_type": "memory",
            "target_id": candidate_memory_id,
            "payload_json": {},
            "occurred_at": "2030-07-10T12:02:00Z",
        },
        {
            "id": expected_event_ids[3],
            "event_type": "project.update_candidate_rejected",
            "target_type": "project",
            "target_id": str(uuid4()),
            "payload_json": {"artifact_id": artifact_id},
            "occurred_at": "2030-07-10T12:03:00Z",
        },
        {
            "id": str(uuid4()),
            "event_type": "project.update_candidate_rejected",
            "target_type": "artifact",
            "target_id": str(uuid4()),
            "payload_json": {"candidate_memory_id": str(uuid4())},
        },
        {
            "id": str(uuid4()),
            "event_type": "memory.reviewed",
            "target_type": "artifact",
            "target_id": artifact_id,
            "payload_json": {"candidate_memory_id": candidate_memory_id},
        },
    )

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"project-event-lookup-{user_id}@example.invalid",
            "Project event lookup",
        )
        store = PostgresVNextStore(conn)
        for event in events:
            store.append_event({**event, "actor_type": "system"})
        event_types = (
            "project.update_candidate_created",
            "project.update_candidate_accepted",
            "project.update_candidate_rejected",
        )
        for index in range(512):
            unrelated_artifact_id = str(uuid4())
            unrelated_memory_id = str(uuid4())
            store.append_event(
                {
                    "event_type": event_types[index % len(event_types)],
                    "actor_type": "system",
                    "target_type": "artifact",
                    "target_id": unrelated_artifact_id,
                    "payload_json": {
                        "artifact_id": unrelated_artifact_id,
                        "candidate_memory_id": unrelated_memory_id,
                        "memory_id": unrelated_memory_id,
                    },
                }
            )

    with user_connection(migrated_database_urls["app"], other_user_id) as conn:
        ContinuityStore(conn).create_user(
            other_user_id,
            f"project-event-lookup-{other_user_id}@example.invalid",
            "Other project event lookup",
        )
        PostgresVNextStore(conn).append_event(
            {
                "event_type": "project.update_candidate_created",
                "actor_type": "system",
                "target_type": "artifact",
                "target_id": artifact_id,
                "payload_json": {
                    "artifact_id": artifact_id,
                    "candidate_memory_id": candidate_memory_id,
                    "memory_id": candidate_memory_id,
                },
                "occurred_at": "2030-07-10T12:04:00Z",
            }
        )

    # Give PostgreSQL representative statistics so the exact production
    # union proves the selective target and payload indexes instead of the
    # generic per-user fallback that wins only on a six-row empty-table plan.
    with psycopg.connect(migrated_database_urls["admin"]) as admin_conn:
        admin_conn.execute("ANALYZE event_log")

    with user_connection(migrated_database_urls["app"], user_id) as conn:
        store = PostgresVNextStore(conn)
        rows = store.list_project_update_events(
            artifact_id=artifact_id,
            candidate_memory_id=candidate_memory_id,
        )
        assert {str(row["id"]) for row in rows} == expected_ids
        assert len(rows) == len(expected_ids)
        assert [str(row["id"]) for row in rows] == list(reversed(expected_event_ids))

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname IN (
                    'event_log_project_update_target_idx',
                    'event_log_project_update_artifact_id_idx',
                    'event_log_project_update_candidate_memory_id_idx',
                    'event_log_project_update_memory_id_idx'
                  )
                ORDER BY indexname
                """
            )
            index_rows = {str(row["indexname"]): str(row["indexdef"]) for row in cur.fetchall()}
            assert set(index_rows) == {
                "event_log_project_update_target_idx",
                "event_log_project_update_artifact_id_idx",
                "event_log_project_update_candidate_memory_id_idx",
                "event_log_project_update_memory_id_idx",
            }
            target_index_definition = index_rows["event_log_project_update_target_idx"]
            assert "event_type = ANY" in target_index_definition
            assert "target_type IS NOT NULL" in target_index_definition
            assert "target_id IS NOT NULL" in target_index_definition
            for index_name, column_name in (
                ("event_log_project_update_artifact_id_idx", "payload_artifact_id"),
                (
                    "event_log_project_update_candidate_memory_id_idx",
                    "payload_candidate_memory_id",
                ),
                ("event_log_project_update_memory_id_idx", "payload_memory_id"),
            ):
                definition = index_rows[index_name]
                assert f"user_id, event_type, {column_name}, occurred_at DESC, id DESC" in definition
                assert f"{column_name} IS NOT NULL" in definition

            cur.execute("SET LOCAL enable_seqscan = off")
            cur.execute(
                f"EXPLAIN (FORMAT TEXT) {_PROJECT_UPDATE_EVENT_LOOKUP_SQL}",
                (
                    artifact_id,
                    candidate_memory_id,
                    artifact_id,
                    candidate_memory_id,
                    candidate_memory_id,
                ),
            )
            plan = "\n".join(str(row["QUERY PLAN"]) for row in cur.fetchall())
            assert plan.count("event_log_project_update_target_idx") == 2, plan
            assert plan.count("event_log_project_update_artifact_id_idx") == 1, plan
            assert plan.count("event_log_project_update_candidate_memory_id_idx") == 1, plan
            assert plan.count("event_log_project_update_memory_id_idx") == 1, plan
            assert "event_log_user_type_occurred_idx" not in plan, plan
            assert "event_log_user_target_occurred_idx" not in plan, plan
            assert "event_log_user_occurred_idx" not in plan, plan
