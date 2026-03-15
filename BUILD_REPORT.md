# BUILD_REPORT

## sprint objective

Implement Sprint 5H: Semantic Artifact Chunk Retrieval Primitive by adding a deterministic, explicit-config semantic retrieval path over durable `task_artifact_chunk_embeddings`, scoped to one task or one artifact, without changing compile behavior or introducing hybrid retrieval, connectors, runners, or UI work.

## completed work

- Added semantic artifact retrieval contracts:
  - `TaskScopedSemanticArtifactChunkRetrievalInput`
    - `task_id`
    - `embedding_config_id`
    - `query_vector`
    - `limit`
  - `ArtifactScopedSemanticArtifactChunkRetrievalInput`
    - `task_artifact_id`
    - `embedding_config_id`
    - `query_vector`
    - `limit`
  - `TaskArtifactChunkSemanticRetrievalItem`
    - `id`
    - `task_id`
    - `task_artifact_id`
    - `relative_path`
    - `media_type`
    - `sequence_no`
    - `char_start`
    - `char_end_exclusive`
    - `text`
    - `score`
  - `TaskArtifactChunkSemanticRetrievalSummary`
    - `embedding_config_id`
    - `query_vector_dimensions`
    - `limit`
    - `returned_count`
    - `searched_artifact_count`
    - `similarity_metric`
    - `order`
    - `scope`
  - `TaskArtifactChunkSemanticRetrievalResponse`
  - `TASK_ARTIFACT_CHUNK_SEMANTIC_RETRIEVAL_ORDER = ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"]`
- Implemented semantic artifact retrieval validation and service logic:
  - validates that `embedding_config_id` resolves to a visible embedding config
  - validates that every query-vector element is finite numeric input
  - validates `len(query_vector) == embedding_config.dimensions`
  - requires one explicit scope:
    - task-scoped retrieval via visible `task_id`
    - artifact-scoped retrieval via visible `task_artifact_id`
  - excludes artifacts whose `ingestion_status` is not `ingested`
  - preserves user isolation through the existing visible-row store lookups
- Added deterministic store queries over durable artifact embedding rows only:
  - task scope joins:
    - `task_artifact_chunk_embeddings`
    - `task_artifact_chunks`
    - `task_artifacts`
  - artifact scope joins the same durable tables with a narrower artifact filter
  - no compile-path semantic use was added
  - no second embedding store was introduced
- Added minimal API surface:
  - `POST /v0/tasks/{task_id}/artifact-chunks/semantic-retrieval`
  - `POST /v0/task-artifacts/{task_artifact_id}/chunks/semantic-retrieval`
- Added tests for:
  - dimension validation
  - deterministic ordering and tie-breaking
  - task-scoped retrieval
  - artifact-scoped retrieval
  - empty-result behavior
  - exclusion of non-ingested artifacts
  - per-user isolation
  - stable response shape

## similarity metric and ordering rule used

- Similarity metric:
  - `cosine_similarity`
  - computed in SQL as `1 - (embeddings.vector <=> query_vector)` via pgvector cosine distance
- Ordering rule:
  - `score DESC`
  - `relative_path ASC`
  - `sequence_no ASC`
  - `id ASC`
- Durable source restriction:
  - retrieval reads only from persisted `task_artifact_chunk_embeddings`, `task_artifact_chunks`, and `task_artifacts`

## incomplete work

- None within Sprint 5H scope.

## files changed

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/semantic_retrieval.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/integration/test_semantic_artifact_chunk_retrieval_api.py`
- `tests/unit/test_artifacts_main.py`
- `tests/unit/test_main.py`
- `tests/unit/test_semantic_retrieval.py`
- `tests/unit/test_task_artifact_chunk_embedding_store.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_semantic_retrieval.py tests/unit/test_task_artifact_chunk_embedding_store.py tests/unit/test_artifacts_main.py tests/unit/test_main.py`
  - result: `65 passed in 0.55s`
- `./.venv/bin/python -m pytest tests/integration/test_semantic_artifact_chunk_retrieval_api.py`
  - first sandboxed attempt failed because local Postgres access to `localhost:5432` was blocked by the sandbox
- `./.venv/bin/python -m pytest tests/integration/test_semantic_artifact_chunk_retrieval_api.py`
  - result after allowing local Postgres access: `3 passed in 1.23s`
- `./.venv/bin/python -m pytest tests/unit`
  - result: `377 passed in 0.59s`
- `./.venv/bin/python -m pytest tests/integration`
  - result: `114 passed in 34.94s`

## example task-scoped semantic retrieval response

```json
{
  "items": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "task_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "task_artifact_id": "22222222-2222-2222-2222-222222222222",
      "relative_path": "docs/a.txt",
      "media_type": "text/plain",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 9,
      "text": "alpha doc",
      "score": 1.0
    },
    {
      "id": "33333333-3333-3333-3333-333333333333",
      "task_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "task_artifact_id": "44444444-4444-4444-4444-444444444444",
      "relative_path": "notes/b.md",
      "media_type": "text/markdown",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 10,
      "text": "alpha note",
      "score": 1.0
    }
  ],
  "summary": {
    "embedding_config_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "query_vector_dimensions": 3,
    "limit": 10,
    "returned_count": 2,
    "searched_artifact_count": 3,
    "similarity_metric": "cosine_similarity",
    "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
    "scope": {
      "kind": "task",
      "task_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    }
  }
}
```

## example artifact-scoped semantic retrieval response

```json
{
  "items": [
    {
      "id": "33333333-3333-3333-3333-333333333333",
      "task_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "task_artifact_id": "44444444-4444-4444-4444-444444444444",
      "relative_path": "notes/b.md",
      "media_type": "text/markdown",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 10,
      "text": "alpha note",
      "score": 1.0
    }
  ],
  "summary": {
    "embedding_config_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "query_vector_dimensions": 3,
    "limit": 10,
    "returned_count": 1,
    "searched_artifact_count": 1,
    "similarity_metric": "cosine_similarity",
    "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"],
    "scope": {
      "kind": "artifact",
      "task_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "task_artifact_id": "44444444-4444-4444-4444-444444444444"
    }
  }
}
```

## blockers/issues

- No code blocker remained after implementation.
- Integration verification required access to the local Postgres instance because sandboxed localhost TCP connections were blocked.

## what remains intentionally deferred to later milestones

- compile-path semantic artifact retrieval
- lexical plus semantic hybrid artifact retrieval
- reranking beyond direct similarity ordering
- query embedding generation through a model or external API
- connectors
- runner orchestration
- UI work

## recommended next step

Adopt this new semantic artifact retrieval primitive in a follow-up sprint that explicitly decides how compile should consume semantic artifact chunks, without combining that change with hybrid retrieval or reranking in the same step.
