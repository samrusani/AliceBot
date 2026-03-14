# BUILD_REPORT

## sprint objective

Implement Sprint 5G: Artifact Chunk Embedding Substrate by adding durable, user-scoped `task_artifact_chunk_embeddings` records tied to existing `embedding_configs`, with strict vector validation, deterministic reads, and no semantic retrieval, compile-path semantic use, connector, runner, or UI changes.

## completed work

- Added Alembic revision `20260314_0025_task_artifact_chunk_embeddings` for a new `task_artifact_chunk_embeddings` table.
- Added schema for `task_artifact_chunk_embeddings`:
  - columns: `id`, `user_id`, `task_artifact_chunk_id`, `embedding_config_id`, `dimensions`, `vector`, `created_at`, `updated_at`
  - uniqueness:
    - `UNIQUE (id, user_id)`
    - `UNIQUE (user_id, task_artifact_chunk_id, embedding_config_id)`
  - foreign keys:
    - `(task_artifact_chunk_id, user_id) -> task_artifact_chunks(id, user_id)`
    - `(embedding_config_id, user_id) -> embedding_configs(id, user_id)`
  - checks:
    - `dimensions > 0`
    - `vector` is a JSON array
    - `vector` is non-empty
    - `jsonb_array_length(vector) = dimensions`
  - index:
    - `task_artifact_chunk_embeddings_user_chunk_created_idx (user_id, task_artifact_chunk_id, created_at, id)`
  - security/runtime:
    - owner-only RLS
    - `GRANT SELECT, INSERT, UPDATE ON task_artifact_chunk_embeddings TO alicebot_app`
- Added stable contracts:
  - `TaskArtifactChunkEmbeddingUpsertInput`
  - `TaskArtifactChunkEmbeddingRecord`
  - `TaskArtifactChunkEmbeddingWriteResponse`
  - `TaskArtifactChunkEmbeddingDetailResponse`
  - `TaskArtifactChunkEmbeddingListScope`
  - `TaskArtifactChunkEmbeddingListSummary`
  - `TaskArtifactChunkEmbeddingListResponse`
  - `TASK_ARTIFACT_CHUNK_EMBEDDING_LIST_ORDER = ["task_artifact_chunk_sequence_no_asc", "created_at_asc", "id_asc"]`
- Implemented artifact-chunk embedding service behavior:
  - validates `task_artifact_chunk_id` against visible `task_artifact_chunks`
  - validates `embedding_config_id` against visible `embedding_configs`
  - reuses the existing versioned `embedding_configs` seam without a second config/version model
  - validates every vector element as finite numeric input
  - enforces `len(vector) == embedding_config.dimensions`
  - upserts one embedding per `(task_artifact_chunk_id, embedding_config_id)` pair
  - exposes deterministic reads by:
    - artifact scope
    - chunk scope
    - embedding id
- Added minimal API surface:
  - `POST /v0/task-artifact-chunk-embeddings`
  - `GET /v0/task-artifacts/{task_artifact_id}/chunk-embeddings`
  - `GET /v0/task-artifact-chunks/{task_artifact_chunk_id}/embeddings`
  - `GET /v0/task-artifact-chunk-embeddings/{task_artifact_chunk_embedding_id}`
- Added unit and integration coverage for:
  - persistence
  - deterministic ordering
  - dimension validation
  - invalid config and invalid chunk references
  - cross-user isolation
  - stable response shape
  - migration presence, RLS, grants, and downgrade behavior

## embedding-config reuse rule and dimension-validation rule used

- Reuse rule:
  - every artifact-chunk embedding must reference an existing visible `embedding_config`
  - no new embedding versioning model was introduced
- Dimension-validation rule:
  - vector normalization accepts only finite numeric values
  - write requests fail unless `len(vector) == embedding_config.dimensions`
  - database and service validation both enforce the dimensions rule

## incomplete work

- None within Sprint 5G scope.

## files changed

- `apps/api/alembic/versions/20260314_0025_task_artifact_chunk_embeddings.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/embedding.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/integration/test_migrations.py`
- `tests/integration/test_task_artifact_chunk_embeddings_api.py`
- `tests/unit/test_20260314_0025_task_artifact_chunk_embeddings.py`
- `tests/unit/test_task_artifact_chunk_embedding.py`
- `tests/unit/test_task_artifact_chunk_embedding_store.py`
- `tests/unit/test_main.py`
- `BUILD_REPORT.md`

## example artifact-chunk embedding write response

```json
{
  "embedding": {
    "id": "4d5d0a3b-6a8a-4bf4-bb7c-d1df3d6d84c8",
    "task_artifact_id": "6dc8f07d-19f6-4667-b9f3-4573b9cf2b66",
    "task_artifact_chunk_id": "fd3dc999-a4d3-4bb0-a287-4f4950dfd7e0",
    "task_artifact_chunk_sequence_no": 2,
    "embedding_config_id": "42dbab76-1e02-4b5f-a18b-f59c1b19d1d4",
    "dimensions": 3,
    "vector": [0.9, 0.8, 0.7],
    "created_at": "2026-03-14T12:00:00+00:00",
    "updated_at": "2026-03-14T12:10:00+00:00"
  },
  "write_mode": "updated"
}
```

## example artifact-chunk embedding list response

```json
{
  "items": [
    {
      "id": "4d5d0a3b-6a8a-4bf4-bb7c-d1df3d6d84c8",
      "task_artifact_id": "6dc8f07d-19f6-4667-b9f3-4573b9cf2b66",
      "task_artifact_chunk_id": "fd3dc999-a4d3-4bb0-a287-4f4950dfd7e0",
      "task_artifact_chunk_sequence_no": 2,
      "embedding_config_id": "42dbab76-1e02-4b5f-a18b-f59c1b19d1d4",
      "dimensions": 3,
      "vector": [0.9, 0.8, 0.7],
      "created_at": "2026-03-14T12:00:00+00:00",
      "updated_at": "2026-03-14T12:10:00+00:00"
    }
  ],
  "summary": {
    "total_count": 1,
    "order": ["task_artifact_chunk_sequence_no_asc", "created_at_asc", "id_asc"],
    "scope": {
      "kind": "chunk",
      "task_artifact_id": "6dc8f07d-19f6-4667-b9f3-4573b9cf2b66",
      "task_artifact_chunk_id": "fd3dc999-a4d3-4bb0-a287-4f4950dfd7e0"
    }
  }
}
```

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_20260314_0025_task_artifact_chunk_embeddings.py tests/unit/test_task_artifact_chunk_embedding.py tests/unit/test_task_artifact_chunk_embedding_store.py tests/unit/test_main.py`
  - result: `48 passed in 0.41s`
- `./.venv/bin/python -m pytest tests/integration/test_task_artifact_chunk_embeddings_api.py tests/integration/test_migrations.py`
  - first sandboxed attempt failed to reach local Postgres on `localhost:5432` due sandbox restrictions
- `./.venv/bin/python -m pytest tests/integration/test_migrations.py::test_migrations_upgrade_and_downgrade tests/integration/test_task_artifact_chunk_embeddings_api.py`
  - result: `4 passed in 1.99s`
- `./.venv/bin/python -m pytest tests/unit`
  - result: `370 passed in 0.59s`
- `./.venv/bin/python -m pytest tests/integration`
  - result: `111 passed in 34.92s`

## blockers/issues

- No code blockers remained.
- Integration verification required elevated access to the local Postgres instance because sandboxed localhost connections were blocked.

## what remains intentionally deferred to later milestones

- semantic retrieval over artifact chunks
- lexical plus semantic hybrid artifact retrieval
- compile-path semantic use of artifact embeddings
- embedding generation via model or external API calls
- connectors, runners, orchestration, and UI work

## recommended next step

Use the new durable `task_artifact_chunk_embeddings` substrate to add a separate, narrowly scoped semantic artifact retrieval sprint that reads these stored vectors without changing compile-path behavior in the same step.
