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


def test_embedding_store_methods_use_expected_queries_and_serialization() -> None:
    config_id = uuid4()
    memory_id = uuid4()
    embedding_id = uuid4()
    created_at = datetime(2026, 3, 12, 9, 0, tzinfo=UTC)
    updated_at = datetime(2026, 3, 12, 9, 5, tzinfo=UTC)
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": config_id,
                "user_id": uuid4(),
                "provider": "openai",
                "model": "text-embedding-3-large",
                "version": "2026-03-12",
                "dimensions": 3,
                "status": "active",
                "metadata": {"task": "memory_retrieval"},
                "created_at": created_at,
            },
            {
                "id": embedding_id,
                "user_id": uuid4(),
                "memory_id": memory_id,
                "embedding_config_id": config_id,
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": created_at,
                "updated_at": created_at,
            },
            {
                "id": embedding_id,
                "user_id": uuid4(),
                "memory_id": memory_id,
                "embedding_config_id": config_id,
                "dimensions": 3,
                "vector": [0.3, 0.2, 0.1],
                "created_at": created_at,
                "updated_at": updated_at,
            },
        ],
        fetchall_results=[
            [
                {
                    "id": config_id,
                    "provider": "openai",
                    "version": "2026-03-12",
                }
            ],
            [
                {
                    "id": embedding_id,
                    "memory_id": memory_id,
                    "embedding_config_id": config_id,
                }
            ],
            [
                {
                    "id": memory_id,
                    "user_id": uuid4(),
                    "memory_key": "user.preference.coffee",
                    "value": {"likes": "oat milk"},
                    "status": "active",
                    "source_event_ids": [str(uuid4())],
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "deleted_at": None,
                    "score": 1.0,
                }
            ],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    created_config = store.create_embedding_config(
        provider="openai",
        model="text-embedding-3-large",
        version="2026-03-12",
        dimensions=3,
        status="active",
        metadata={"task": "memory_retrieval"},
    )
    listed_configs = store.list_embedding_configs()
    created_embedding = store.create_memory_embedding(
        memory_id=memory_id,
        embedding_config_id=config_id,
        dimensions=3,
        vector=[0.1, 0.2, 0.3],
    )
    updated_embedding = store.update_memory_embedding(
        memory_embedding_id=embedding_id,
        dimensions=3,
        vector=[0.3, 0.2, 0.1],
    )
    listed_embeddings = store.list_memory_embeddings_for_memory(memory_id)
    retrieval_matches = store.retrieve_semantic_memory_matches(
        embedding_config_id=config_id,
        query_vector=[0.1, 0.2, 0.3],
        limit=5,
    )

    assert created_config["id"] == config_id
    assert listed_configs == [{"id": config_id, "provider": "openai", "version": "2026-03-12"}]
    assert created_embedding["id"] == embedding_id
    assert updated_embedding["updated_at"] == updated_at
    assert listed_embeddings == [
        {"id": embedding_id, "memory_id": memory_id, "embedding_config_id": config_id}
    ]
    assert len(retrieval_matches) == 1
    assert retrieval_matches[0]["id"] == memory_id
    assert retrieval_matches[0]["memory_key"] == "user.preference.coffee"
    assert retrieval_matches[0]["status"] == "active"
    assert retrieval_matches[0]["score"] == 1.0

    create_config_query, create_config_params = cursor.executed[0]
    assert "INSERT INTO embedding_configs" in create_config_query
    assert create_config_params is not None
    assert create_config_params[:5] == (
        "openai",
        "text-embedding-3-large",
        "2026-03-12",
        3,
        "active",
    )
    assert isinstance(create_config_params[5], Jsonb)
    assert create_config_params[5].obj == {"task": "memory_retrieval"}

    list_config_query, list_config_params = cursor.executed[1]
    assert "FROM embedding_configs" in list_config_query
    assert "ORDER BY created_at ASC, id ASC" in list_config_query
    assert list_config_params is None

    create_embedding_query, create_embedding_params = cursor.executed[2]
    assert "INSERT INTO memory_embeddings" in create_embedding_query
    assert create_embedding_params is not None
    assert create_embedding_params[:3] == (memory_id, config_id, 3)
    assert isinstance(create_embedding_params[3], Jsonb)
    assert create_embedding_params[3].obj == [0.1, 0.2, 0.3]

    update_embedding_query, update_embedding_params = cursor.executed[3]
    assert "UPDATE memory_embeddings" in update_embedding_query
    assert update_embedding_params is not None
    assert update_embedding_params[0] == 3
    assert isinstance(update_embedding_params[1], Jsonb)
    assert update_embedding_params[1].obj == [0.3, 0.2, 0.1]
    assert update_embedding_params[2] == embedding_id

    list_embedding_query, list_embedding_params = cursor.executed[4]
    assert "FROM memory_embeddings" in list_embedding_query
    assert "ORDER BY created_at ASC, id ASC" in list_embedding_query
    assert list_embedding_params == (memory_id,)

    retrieval_query, retrieval_params = cursor.executed[5]
    assert "replace(memory_embeddings.vector::text, ' ', '')::vector <=> %s::vector" in retrieval_query
    assert "JOIN memories" in retrieval_query
    assert "memories.status = 'active'" in retrieval_query
    assert "ORDER BY score DESC, memories.created_at ASC, memories.id ASC" in retrieval_query
    assert retrieval_params == ("[0.1,0.2,0.3]", config_id, 3, 5)


def test_embedding_store_optional_reads_return_none_when_row_is_missing() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    assert store.get_embedding_config_optional(uuid4()) is None
    assert store.get_embedding_config_by_identity_optional(
        provider="openai",
        model="text-embedding-3-large",
        version="2026-03-12",
    ) is None
    assert store.get_memory_embedding_optional(uuid4()) is None
    assert store.get_memory_embedding_by_memory_and_config_optional(
        memory_id=uuid4(),
        embedding_config_id=uuid4(),
    ) is None
