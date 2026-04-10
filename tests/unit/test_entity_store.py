from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from alicebot_api.store import ContinuityStore


class RecordingCursor:
    def __init__(
        self,
        fetchone_results: list[dict[str, Any]],
        fetchall_results: list[list[dict[str, Any]]] | None = None,
    ) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetchone_results = list(fetchone_results)
        self.fetchall_results = list(fetchall_results or [])

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict[str, Any] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, Any]]:
        if not self.fetchall_results:
            return []
        return self.fetchall_results.pop(0)


class RecordingConnection:
    def __init__(self, cursor: RecordingCursor) -> None:
        self.cursor_instance = cursor

    def cursor(self) -> RecordingCursor:
        return self.cursor_instance


def test_entity_methods_use_expected_queries_and_deterministic_order() -> None:
    entity_id = uuid4()
    first_memory_id = uuid4()
    second_memory_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": entity_id,
                "user_id": uuid4(),
                "entity_type": "project",
                "name": "AliceBot",
                "source_memory_ids": [str(first_memory_id), str(second_memory_id)],
                "created_at": "ignored",
            }
        ],
        fetchall_results=[
            [{"id": first_memory_id}, {"id": second_memory_id}],
            [{"id": entity_id, "name": "AliceBot"}],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_entity(
        entity_type="project",
        name="AliceBot",
        source_memory_ids=[str(first_memory_id), str(second_memory_id)],
    )
    listed_memories = store.list_memories_by_ids([first_memory_id, second_memory_id])
    listed_entities = store.list_entities()

    assert created["id"] == entity_id
    assert listed_memories == [{"id": first_memory_id}, {"id": second_memory_id}]
    assert listed_entities == [{"id": entity_id, "name": "AliceBot"}]

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO entities" in create_query
    assert create_params is not None
    assert create_params[0] == "project"
    assert create_params[1] == "AliceBot"
    assert isinstance(create_params[2], Jsonb)
    assert create_params[2].obj == [str(first_memory_id), str(second_memory_id)]

    assert cursor.executed[1] == (
        """
                SELECT
                  id,
                  user_id,
                  agent_profile_id,
                  memory_key,
                  value,
                  status,
                  source_event_ids,
                  memory_type,
                  confidence,
                  salience,
                  confirmation_status,
                  trust_class,
                  promotion_eligibility,
                  evidence_count,
                  independent_source_count,
                  extracted_by_model,
                  trust_reason,
                  valid_from,
                  valid_to,
                  last_confirmed_at,
                  created_at,
                  updated_at,
                  deleted_at
                FROM memories
                WHERE id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """,
        ([first_memory_id, second_memory_id],),
    )
    assert cursor.executed[2] == (
        """
                SELECT id, user_id, entity_type, name, source_memory_ids, created_at
                FROM entities
                ORDER BY created_at ASC, id ASC
                """,
        None,
    )


def test_get_entity_optional_returns_none_when_row_is_missing() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    assert store.get_entity_optional(uuid4()) is None


def test_entity_edge_methods_use_expected_queries_and_deterministic_order() -> None:
    edge_id = uuid4()
    from_entity_id = uuid4()
    to_entity_id = uuid4()
    related_entity_id = uuid4()
    source_memory_id = uuid4()
    valid_from = datetime(2026, 3, 12, 10, 0, tzinfo=UTC)
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": edge_id,
                "user_id": uuid4(),
                "from_entity_id": from_entity_id,
                "to_entity_id": to_entity_id,
                "relationship_type": "works_on",
                "valid_from": valid_from,
                "valid_to": None,
                "source_memory_ids": [str(source_memory_id)],
                "created_at": "ignored",
            }
        ],
        fetchall_results=[
            [{"id": edge_id, "relationship_type": "works_on"}],
            [{"id": edge_id, "relationship_type": "works_on"}],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created = store.create_entity_edge(
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        relationship_type="works_on",
        valid_from=valid_from,
        valid_to=None,
        source_memory_ids=[str(source_memory_id)],
    )
    listed_edges = store.list_entity_edges_for_entity(from_entity_id)
    listed_edges_for_entities = store.list_entity_edges_for_entities([from_entity_id, related_entity_id])

    assert created["id"] == edge_id
    assert listed_edges == [{"id": edge_id, "relationship_type": "works_on"}]
    assert listed_edges_for_entities == [{"id": edge_id, "relationship_type": "works_on"}]

    create_query, create_params = cursor.executed[0]
    assert "INSERT INTO entity_edges" in create_query
    assert create_params is not None
    assert create_params[0] == from_entity_id
    assert create_params[1] == to_entity_id
    assert create_params[2] == "works_on"
    assert create_params[3] == valid_from
    assert create_params[4] is None
    assert isinstance(create_params[5], Jsonb)
    assert create_params[5].obj == [str(source_memory_id)]

    assert cursor.executed[1] == (
        """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = %s OR to_entity_id = %s
                ORDER BY created_at ASC, id ASC
                """,
        (from_entity_id, from_entity_id),
    )
    assert cursor.executed[2] == (
        """
                SELECT
                  id,
                  user_id,
                  from_entity_id,
                  to_entity_id,
                  relationship_type,
                  valid_from,
                  valid_to,
                  source_memory_ids,
                  created_at
                FROM entity_edges
                WHERE from_entity_id = ANY(%s) OR to_entity_id = ANY(%s)
                ORDER BY created_at ASC, id ASC
                """,
        ([from_entity_id, related_entity_id], [from_entity_id, related_entity_id]),
    )


def test_entity_alias_and_merge_methods_use_expected_queries() -> None:
    entity_id = uuid4()
    source_entity_id = uuid4()
    target_entity_id = uuid4()
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": uuid4(),
                "user_id": uuid4(),
                "entity_id": entity_id,
                "alias": "Project Orion",
                "normalized_alias": "project orion",
                "created_at": "ignored",
            },
            {
                "id": uuid4(),
                "user_id": uuid4(),
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "reason": "duplicate import identity",
                "created_at": "ignored",
            },
            {
                "id": uuid4(),
                "user_id": uuid4(),
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "reason": "duplicate import identity",
                "created_at": "ignored",
            },
        ],
        fetchall_results=[
            [
                {
                    "id": uuid4(),
                    "user_id": uuid4(),
                    "entity_id": entity_id,
                    "alias": "Project Orion",
                    "normalized_alias": "project orion",
                    "created_at": "ignored",
                }
            ],
            [
                {
                    "entity_id": entity_id,
                    "entity_type": "project",
                    "entity_name": "Project Orion",
                    "created_at": "ignored",
                }
            ],
            [{"id": uuid4()}, {"id": uuid4()}],
            [
                {
                    "id": uuid4(),
                    "user_id": uuid4(),
                    "source_entity_id": source_entity_id,
                    "target_entity_id": target_entity_id,
                    "reason": "duplicate import identity",
                    "created_at": "ignored",
                }
            ],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created_alias = store.create_entity_alias(
        entity_id=entity_id,
        alias="Project Orion",
        normalized_alias="project orion",
    )
    listed_aliases = store.list_entity_aliases_for_entity(entity_id)
    alias_matches = store.find_entity_alias_matches(
        entity_type="project",
        normalized_alias="project orion",
    )
    merge_record = store.create_entity_merge_log(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        reason="duplicate import identity",
    )
    latest_merge = store.get_latest_entity_merge_for_source_optional(source_entity_id)
    rebound_count = store.rebind_continuity_object_entity_references(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
    )
    merge_history = store.list_entity_merge_logs_for_entity(source_entity_id)

    assert created_alias["entity_id"] == entity_id
    assert listed_aliases[0]["alias"] == "Project Orion"
    assert alias_matches[0]["entity_name"] == "Project Orion"
    assert merge_record["source_entity_id"] == source_entity_id
    assert latest_merge is not None
    assert latest_merge["target_entity_id"] == target_entity_id
    assert rebound_count == 2
    assert merge_history[0]["target_entity_id"] == target_entity_id

    assert cursor.executed[0] == (
        """
                INSERT INTO entity_aliases (user_id, entity_id, alias, normalized_alias, created_at)
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp())
                ON CONFLICT (user_id, entity_id, normalized_alias)
                DO UPDATE SET alias = EXCLUDED.alias
                RETURNING id, user_id, entity_id, alias, normalized_alias, created_at
                """,
        (entity_id, "Project Orion", "project orion"),
    )
    assert cursor.executed[1] == (
        """
                SELECT id, user_id, entity_id, alias, normalized_alias, created_at
                FROM entity_aliases
                WHERE entity_id = %s
                ORDER BY created_at ASC, id ASC
                """,
        (entity_id,),
    )
    assert cursor.executed[2] == (
        """
                SELECT
                  matches.entity_id,
                  entities.entity_type,
                  entities.name AS entity_name,
                  entities.created_at
                FROM (
                  SELECT entity_id
                  FROM entity_aliases
                  WHERE normalized_alias = %s
                  UNION
                  SELECT id AS entity_id
                  FROM entities
                  WHERE entity_type = %s
                    AND regexp_replace(lower(name), '\\s+', ' ', 'g') = %s
                ) AS matches
                JOIN entities
                  ON entities.id = matches.entity_id
                 AND entities.user_id = app.current_user_id()
                WHERE entities.entity_type = %s
                ORDER BY entities.created_at ASC, matches.entity_id ASC
                """,
        ("project orion", "project", "project orion", "project"),
    )
    assert cursor.executed[3] == (
        """
                INSERT INTO entity_merge_log (
                  user_id,
                  source_entity_id,
                  target_entity_id,
                  reason,
                  created_at
                )
                VALUES (app.current_user_id(), %s, %s, %s, clock_timestamp())
                RETURNING id, user_id, source_entity_id, target_entity_id, reason, created_at
                """,
        (source_entity_id, target_entity_id, "duplicate import identity"),
    )
    assert cursor.executed[4] == (
        """
                SELECT id, user_id, source_entity_id, target_entity_id, reason, created_at
                FROM entity_merge_log
                WHERE source_entity_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
        (source_entity_id,),
    )
    assert cursor.executed[5] == (
        """
                UPDATE continuity_objects
                SET project_entity_id = CASE WHEN project_entity_id = %s THEN %s ELSE project_entity_id END,
                    person_entity_id = CASE WHEN person_entity_id = %s THEN %s ELSE person_entity_id END,
                    topic_entity_id = CASE WHEN topic_entity_id = %s THEN %s ELSE topic_entity_id END,
                    updated_at = clock_timestamp()
                WHERE project_entity_id = %s OR person_entity_id = %s OR topic_entity_id = %s
                RETURNING id
                """,
        (
            source_entity_id,
            target_entity_id,
            source_entity_id,
            target_entity_id,
            source_entity_id,
            target_entity_id,
            source_entity_id,
            source_entity_id,
            source_entity_id,
        ),
    )
    assert cursor.executed[6] == (
        """
                SELECT id, user_id, source_entity_id, target_entity_id, reason, created_at
                FROM entity_merge_log
                WHERE source_entity_id = %s OR target_entity_id = %s
                ORDER BY created_at DESC, id DESC
                """,
        (source_entity_id, source_entity_id),
    )
