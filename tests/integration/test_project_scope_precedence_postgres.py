"""PostgreSQL regressions for authoritative canonical project scope."""

from __future__ import annotations

from uuid import uuid4

from psycopg.types.json import Jsonb

from alicebot_api.db import user_connection
from alicebot_api.store import ContinuityStore
from alicebot_api.vnext_store import PostgresVNextStore


def _ids(rows: list[dict[str, object]]) -> set[str]:
    return {str(row["id"]) for row in rows}


def test_canonical_project_scope_precedes_empty_and_stale_legacy_values(
    migrated_database_urls,
) -> None:
    app_url = migrated_database_urls["app"]
    user_id = uuid4()
    stale_project = str(uuid4())
    canonical_project = str(uuid4())
    marker = f"canonical scope precedence {uuid4().hex}"

    with user_connection(app_url, user_id) as conn:
        ContinuityStore(conn).create_user(
            user_id,
            f"scope-precedence-{user_id}@example.invalid",
            "Scope precedence",
        )
        store = PostgresVNextStore(conn)
        store.create_project({"id": stale_project, "name": "Stale project", "slug": f"stale-{stale_project}"})
        store.create_project(
            {
                "id": canonical_project,
                "name": "Canonical project",
                "slug": f"canonical-{canonical_project}",
            }
        )
        empty_metadata = {
            "project_scope": [],
            "project_id": stale_project,
            "agentic_memory": {"project_scope": [stale_project]},
        }
        canonical_metadata = {
            "project_scope": [canonical_project],
            "project_id": stale_project,
            "agentic_memory": {"project_scope": [stale_project]},
        }

        with conn.cursor() as cur:
            memory_ids: list[str] = []
            for suffix, metadata in (("empty", empty_metadata), ("canonical", canonical_metadata)):
                cur.execute(
                    """
                    INSERT INTO memories (
                      user_id, memory_key, value, status, source_event_ids,
                      memory_type, title, canonical_text, domain, sensitivity,
                      project_id, metadata_json
                    ) VALUES (
                      %s, %s, '{}'::jsonb, 'active', '[]'::jsonb,
                      'semantic', %s, %s, 'project', 'internal',
                      %s::uuid, %s
                    )
                    RETURNING id
                    """,
                    (
                        user_id,
                        f"scope.precedence.memory.{suffix}.{uuid4().hex}",
                        marker,
                        f"{marker} {suffix}",
                        stale_project,
                        Jsonb(metadata),
                    ),
                )
                memory_ids.append(str(cur.fetchone()["id"]))

        source_ids = [
            str(
                store.create_source(
                    {
                        "source_type": "manual_text",
                        "title": marker,
                        "content_hash": f"sha256:{uuid4().hex}",
                        "domain": "project",
                        "sensitivity": "internal",
                        "metadata_json": metadata,
                    }
                )["id"]
            )
            for metadata in (empty_metadata, canonical_metadata)
        ]
        artifact_ids = [
            str(
                store.create_artifact(
                    {
                        "artifact_type": "daily_brief",
                        "title": marker,
                        "content_markdown": marker,
                        "domain": "project",
                        "sensitivity": "internal",
                        "metadata_json": metadata,
                    }
                )["id"]
            )
            for metadata in (empty_metadata, canonical_metadata)
        ]
        open_loop_ids = [
            str(
                store.create_open_loop(
                    {
                        "title": marker,
                        "project_id": stale_project,
                        "domain": "project",
                        "sensitivity": "internal",
                        "metadata_json": metadata,
                    }
                )["id"]
            )
            for metadata in (empty_metadata, canonical_metadata)
        ]

        stale_results = {
            "memory": _ids(store.list_memories(projects=(stale_project,), limit=10)),
            "source": _ids(store.search_sources(query=marker, scope_projects=(stale_project,), limit=10)),
            "artifact": _ids(store.list_artifacts(scope_projects=(stale_project,), limit=10)),
            "open_loop": _ids(store.list_open_loops(scope_projects=(stale_project,), limit=10)),
        }
        canonical_results = {
            "memory": _ids(store.list_memories(projects=(canonical_project,), limit=10)),
            "source": _ids(store.search_sources(query=marker, scope_projects=(canonical_project,), limit=10)),
            "artifact": _ids(store.list_artifacts(scope_projects=(canonical_project,), limit=10)),
            "open_loop": _ids(store.list_open_loops(scope_projects=(canonical_project,), limit=10)),
        }

    resource_ids = {
        "memory": memory_ids,
        "source": source_ids,
        "artifact": artifact_ids,
        "open_loop": open_loop_ids,
    }
    for resource_type, (empty_id, canonical_id) in resource_ids.items():
        assert empty_id not in stale_results[resource_type]
        assert canonical_id not in stale_results[resource_type]
        assert empty_id not in canonical_results[resource_type]
        assert canonical_results[resource_type] == {canonical_id}
