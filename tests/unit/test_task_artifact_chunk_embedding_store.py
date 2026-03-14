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


def test_task_artifact_chunk_embedding_store_methods_use_expected_queries() -> None:
    task_artifact_id = uuid4()
    task_artifact_chunk_id = uuid4()
    embedding_config_id = uuid4()
    embedding_id = uuid4()
    created_at = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
    updated_at = datetime(2026, 3, 14, 12, 5, tzinfo=UTC)
    cursor = RecordingCursor(
        fetchone_results=[
            {
                "id": task_artifact_chunk_id,
                "user_id": uuid4(),
                "task_artifact_id": task_artifact_id,
                "sequence_no": 2,
                "char_start": 10,
                "char_end_exclusive": 20,
                "text": "chunk-2",
                "created_at": created_at,
                "updated_at": created_at,
            },
            {
                "id": embedding_id,
                "user_id": uuid4(),
                "task_artifact_id": task_artifact_id,
                "task_artifact_chunk_id": task_artifact_chunk_id,
                "task_artifact_chunk_sequence_no": 2,
                "embedding_config_id": embedding_config_id,
                "dimensions": 3,
                "vector": [0.1, 0.2, 0.3],
                "created_at": created_at,
                "updated_at": created_at,
            },
            {
                "id": embedding_id,
                "user_id": uuid4(),
                "task_artifact_id": task_artifact_id,
                "task_artifact_chunk_id": task_artifact_chunk_id,
                "task_artifact_chunk_sequence_no": 2,
                "embedding_config_id": embedding_config_id,
                "dimensions": 3,
                "vector": [0.3, 0.2, 0.1],
                "created_at": created_at,
                "updated_at": updated_at,
            },
            {
                "id": embedding_id,
                "user_id": uuid4(),
                "task_artifact_id": task_artifact_id,
                "task_artifact_chunk_id": task_artifact_chunk_id,
                "task_artifact_chunk_sequence_no": 2,
                "embedding_config_id": embedding_config_id,
                "dimensions": 3,
                "vector": [0.3, 0.2, 0.1],
                "created_at": created_at,
                "updated_at": updated_at,
            },
            {
                "id": embedding_id,
                "user_id": uuid4(),
                "task_artifact_id": task_artifact_id,
                "task_artifact_chunk_id": task_artifact_chunk_id,
                "task_artifact_chunk_sequence_no": 2,
                "embedding_config_id": embedding_config_id,
                "dimensions": 3,
                "vector": [0.3, 0.2, 0.1],
                "created_at": created_at,
                "updated_at": updated_at,
            },
        ],
        fetchall_results=[
            [
                {
                    "id": embedding_id,
                    "task_artifact_id": task_artifact_id,
                    "task_artifact_chunk_id": task_artifact_chunk_id,
                    "task_artifact_chunk_sequence_no": 2,
                    "embedding_config_id": embedding_config_id,
                }
            ],
            [
                {
                    "id": embedding_id,
                    "task_artifact_id": task_artifact_id,
                    "task_artifact_chunk_id": task_artifact_chunk_id,
                    "task_artifact_chunk_sequence_no": 2,
                    "embedding_config_id": embedding_config_id,
                }
            ],
        ],
    )
    store = ContinuityStore(RecordingConnection(cursor))

    fetched_chunk = store.get_task_artifact_chunk_optional(task_artifact_chunk_id)
    created = store.create_task_artifact_chunk_embedding(
        task_artifact_chunk_id=task_artifact_chunk_id,
        embedding_config_id=embedding_config_id,
        dimensions=3,
        vector=[0.1, 0.2, 0.3],
    )
    updated = store.update_task_artifact_chunk_embedding(
        task_artifact_chunk_embedding_id=embedding_id,
        dimensions=3,
        vector=[0.3, 0.2, 0.1],
    )
    fetched_embedding = store.get_task_artifact_chunk_embedding_optional(embedding_id)
    existing = store.get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        task_artifact_chunk_id=task_artifact_chunk_id,
        embedding_config_id=embedding_config_id,
    )
    listed_for_chunk = store.list_task_artifact_chunk_embeddings_for_chunk(task_artifact_chunk_id)
    listed_for_artifact = store.list_task_artifact_chunk_embeddings_for_artifact(task_artifact_id)

    assert fetched_chunk is not None
    assert fetched_chunk["id"] == task_artifact_chunk_id
    assert created["id"] == embedding_id
    assert updated["updated_at"] == updated_at
    assert fetched_embedding is not None
    assert existing is not None
    assert listed_for_chunk == [
        {
            "id": embedding_id,
            "task_artifact_id": task_artifact_id,
            "task_artifact_chunk_id": task_artifact_chunk_id,
            "task_artifact_chunk_sequence_no": 2,
            "embedding_config_id": embedding_config_id,
        }
    ]
    assert listed_for_artifact == [
        {
            "id": embedding_id,
            "task_artifact_id": task_artifact_id,
            "task_artifact_chunk_id": task_artifact_chunk_id,
            "task_artifact_chunk_sequence_no": 2,
            "embedding_config_id": embedding_config_id,
        }
    ]

    get_chunk_query, get_chunk_params = cursor.executed[0]
    assert "FROM task_artifact_chunks" in get_chunk_query
    assert get_chunk_params == (task_artifact_chunk_id,)

    create_query, create_params = cursor.executed[1]
    assert "INSERT INTO task_artifact_chunk_embeddings" in create_query
    assert "JOIN task_artifact_chunks AS chunks" in create_query
    assert create_params is not None
    assert create_params[:3] == (task_artifact_chunk_id, embedding_config_id, 3)
    assert isinstance(create_params[3], Jsonb)
    assert create_params[3].obj == [0.1, 0.2, 0.3]

    update_query, update_params = cursor.executed[2]
    assert "UPDATE task_artifact_chunk_embeddings" in update_query
    assert update_params is not None
    assert update_params[0] == 3
    assert isinstance(update_params[1], Jsonb)
    assert update_params[1].obj == [0.3, 0.2, 0.1]
    assert update_params[2] == embedding_id

    get_embedding_query, get_embedding_params = cursor.executed[3]
    assert "FROM task_artifact_chunk_embeddings AS embeddings" in get_embedding_query
    assert get_embedding_params == (embedding_id,)

    get_existing_query, get_existing_params = cursor.executed[4]
    assert "WHERE embeddings.task_artifact_chunk_id = %s" in get_existing_query
    assert "AND embeddings.embedding_config_id = %s" in get_existing_query
    assert get_existing_params == (task_artifact_chunk_id, embedding_config_id)

    list_chunk_query, list_chunk_params = cursor.executed[5]
    assert "WHERE embeddings.task_artifact_chunk_id = %s" in list_chunk_query
    assert "ORDER BY chunks.sequence_no ASC, embeddings.created_at ASC, embeddings.id ASC" in list_chunk_query
    assert list_chunk_params == (task_artifact_chunk_id,)

    list_artifact_query, list_artifact_params = cursor.executed[6]
    assert "WHERE chunks.task_artifact_id = %s" in list_artifact_query
    assert "ORDER BY chunks.sequence_no ASC, embeddings.created_at ASC, embeddings.id ASC" in list_artifact_query
    assert list_artifact_params == (task_artifact_id,)


def test_task_artifact_chunk_embedding_store_optional_reads_return_none_when_row_is_missing() -> None:
    cursor = RecordingCursor(fetchone_results=[])
    store = ContinuityStore(RecordingConnection(cursor))

    assert store.get_task_artifact_chunk_optional(uuid4()) is None
    assert store.get_task_artifact_chunk_embedding_optional(uuid4()) is None
    assert store.get_task_artifact_chunk_embedding_by_chunk_and_config_optional(
        task_artifact_chunk_id=uuid4(),
        embedding_config_id=uuid4(),
    ) is None
