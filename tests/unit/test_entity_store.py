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
