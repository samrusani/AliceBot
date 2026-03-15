# BUILD_REPORT

## sprint objective

Implement Sprint 5I: adopt semantic artifact retrieval into `POST /v0/context/compile` as an explicit, separate compile-time section backed only by durable `task_artifact_chunk_embeddings`, `task_artifact_chunks`, and `task_artifacts`, while keeping lexical and semantic artifact retrieval separate.

## completed work

- Added compile-request contracts for `semantic_artifact_retrieval` with explicit task-scoped and artifact-scoped variants:
  - `kind`
  - `task_id` or `task_artifact_id`
  - `embedding_config_id`
  - `query_vector`
  - `limit`
- Added compile-response contracts for:
  - `context_pack.semantic_artifact_chunks`
  - `context_pack.semantic_artifact_chunk_summary`
- Added semantic artifact trace contracts for per-item include/exclude decisions with:
  - scope
  - artifact identity
  - ingestion status
  - embedding config id
  - query vector dimensions
  - limit
  - similarity metric
  - score and chunk coordinates when applicable
- Integrated semantic artifact retrieval into the compiler as an explicit optional path.
- Reused the shipped semantic artifact retrieval primitive for compile-path section assembly, then evaluated the full deterministic candidate set for compile-only include/exclude tracing and counts.
- Preserved existing compile sections and behavior for:
  - continuity scope
  - hybrid memory
  - lexical artifact retrieval
  - entities
  - entity edges
- Kept lexical artifact chunks and semantic artifact chunks in separate response sections.
- Added trace coverage for:
  - `within_semantic_artifact_chunk_limit`
  - `semantic_artifact_chunk_limit_exceeded`
  - `semantic_artifact_not_ingested`
- Added summary trace fields for semantic artifact retrieval request state, scope, candidate count, included count, limit exclusions, and non-ingested exclusions.
- Updated prompt-assembly context serialization so compiled context packs include the new semantic artifact section shape.
- Added unit and integration coverage for:
  - request-shape validation
  - config existence validation
  - query-vector dimension validation
  - deterministic ordering
  - exclusion of non-ingested artifacts
  - trace logging for included and excluded semantic artifact results
  - per-user isolation
  - response-shape stability

## exact compile contract changes introduced

- Request:
  - `CompileContextRequest.semantic_artifact_retrieval`
  - `CompileContextTaskScopedSemanticArtifactRetrievalRequest`
  - `CompileContextArtifactScopedSemanticArtifactRetrievalRequest`
  - `CompileContextTaskScopedSemanticArtifactRetrievalInput`
  - `CompileContextArtifactScopedSemanticArtifactRetrievalInput`
- Response:
  - `CompiledContextPack.semantic_artifact_chunks`
  - `CompiledContextPack.semantic_artifact_chunk_summary`
  - `ContextPackSemanticArtifactChunk`
  - `ContextPackSemanticArtifactChunkSummary`
- Trace payloads:
  - `SemanticArtifactRetrievalDecisionTracePayload`
- Summary event additions:
  - `semantic_artifact_retrieval_requested`
  - `semantic_artifact_retrieval_scope_kind`
  - `semantic_artifact_chunk_candidate_count`
  - `included_semantic_artifact_chunk_count`
  - `excluded_semantic_artifact_chunk_limit_count`
  - `excluded_semantic_uningested_artifact_count`

## similarity metric and ordering rule used

- Similarity metric: `cosine_similarity`
- Ordering rule: `score_desc`, `relative_path_asc`, `sequence_no_asc`, `id_asc`
- Compile candidate evaluation stays deterministic by using the durable semantic retrieval ordering and then applying explicit compile-time slicing by `limit`.

## incomplete work

- None within Sprint 5I scope.

## files changed

- `apps/api/src/alicebot_api/compiler.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/response_generation.py`
- `apps/api/src/alicebot_api/semantic_retrieval.py`
- `tests/integration/test_context_compile.py`
- `tests/unit/test_compiler.py`
- `tests/unit/test_main.py`
- `tests/unit/test_response_generation.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_compiler.py tests/unit/test_main.py tests/unit/test_response_generation.py`
  - result: `50 passed in 0.48s`
- `./.venv/bin/python -m pytest tests/integration/test_context_compile.py`
  - sandboxed attempt failed because localhost Postgres access was blocked
  - rerun with local DB access allowed: `11 passed in 3.85s`
- `./.venv/bin/python -m pytest tests/unit`
  - result: `380 passed in 0.61s`
- `./.venv/bin/python -m pytest tests/integration`
  - result: `117 passed in 36.46s`

## unit and integration test results

- Unit suite status: pass
- Integration suite status: pass
- Acceptance-criteria verification:
  - compile request validation: covered and passing
  - deterministic semantic artifact ordering: covered and passing
  - exclusion of non-ingested artifacts: covered and passing
  - include/exclude trace logging: covered and passing
  - per-user isolation: covered and passing
  - response-shape stability: covered and passing

## example compile request

```json
{
  "user_id": "11111111-1111-1111-8111-111111111111",
  "thread_id": "22222222-2222-2222-8222-222222222222",
  "semantic_artifact_retrieval": {
    "kind": "task",
    "task_id": "33333333-3333-3333-8333-333333333333",
    "embedding_config_id": "44444444-4444-4444-8444-444444444444",
    "query_vector": [1.0, 0.0, 0.0],
    "limit": 2
  }
}
```

## example compile response showing semantic artifact section

```json
{
  "context_pack": {
    "semantic_artifact_chunks": [
      {
        "id": "55555555-5555-5555-8555-555555555555",
        "task_id": "33333333-3333-3333-8333-333333333333",
        "task_artifact_id": "66666666-6666-6666-8666-666666666666",
        "relative_path": "docs/a.txt",
        "media_type": "text/plain",
        "sequence_no": 1,
        "char_start": 0,
        "char_end_exclusive": 14,
        "text": "beta alpha doc",
        "score": 1.0
      },
      {
        "id": "77777777-7777-7777-8777-777777777777",
        "task_id": "33333333-3333-3333-8333-333333333333",
        "task_artifact_id": "88888888-8888-8888-8888-888888888888",
        "relative_path": "notes/b.md",
        "media_type": "text/markdown",
        "sequence_no": 1,
        "char_start": 0,
        "char_end_exclusive": 15,
        "text": "alpha beta note",
        "score": 1.0
      }
    ],
    "semantic_artifact_chunk_summary": {
      "requested": true,
      "scope": {
        "kind": "task",
        "task_id": "33333333-3333-3333-8333-333333333333"
      },
      "embedding_config_id": "44444444-4444-4444-8444-444444444444",
      "query_vector_dimensions": 3,
      "limit": 2,
      "searched_artifact_count": 3,
      "candidate_count": 3,
      "included_count": 2,
      "excluded_uningested_artifact_count": 1,
      "excluded_limit_count": 1,
      "similarity_metric": "cosine_similarity",
      "order": ["score_desc", "relative_path_asc", "sequence_no_asc", "id_asc"]
    }
  }
}
```

## example semantic artifact retrieval trace events inside one compile run

```json
[
  {
    "kind": "context.included",
    "payload": {
      "entity_type": "semantic_artifact_chunk",
      "entity_id": "55555555-5555-5555-8555-555555555555",
      "reason": "within_semantic_artifact_chunk_limit",
      "position": 1,
      "scope_kind": "task",
      "task_id": "33333333-3333-3333-8333-333333333333",
      "task_artifact_id": "66666666-6666-6666-8666-666666666666",
      "relative_path": "docs/a.txt",
      "media_type": "text/plain",
      "ingestion_status": "ingested",
      "embedding_config_id": "44444444-4444-4444-8444-444444444444",
      "query_vector_dimensions": 3,
      "limit": 2,
      "similarity_metric": "cosine_similarity",
      "score": 1.0,
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 14
    }
  },
  {
    "kind": "context.excluded",
    "payload": {
      "entity_type": "task_artifact",
      "entity_id": "99999999-9999-9999-8999-999999999999",
      "reason": "semantic_artifact_not_ingested",
      "position": 3,
      "scope_kind": "task",
      "task_id": "33333333-3333-3333-8333-333333333333",
      "task_artifact_id": "99999999-9999-9999-8999-999999999999",
      "relative_path": "notes/hidden.txt",
      "media_type": "text/plain",
      "ingestion_status": "pending",
      "embedding_config_id": "44444444-4444-4444-8444-444444444444",
      "query_vector_dimensions": 3,
      "limit": 2,
      "similarity_metric": "cosine_similarity"
    }
  }
]
```

## blockers/issues

- No implementation blockers remained.
- Integration verification required local Postgres access outside the default sandbox because sandboxed TCP access to `localhost:5432` is not permitted.

## what remains intentionally deferred to later milestones

- hybrid lexical-plus-semantic artifact retrieval
- lexical/semantic deduplication or fusion
- reranking across semantic artifact chunks
- model-generated query embeddings
- connectors
- runner orchestration
- UI work

## recommended next step

Implement the follow-up sprint for hybrid compile-path artifact fusion only after agreeing on explicit merge, deduplication, and reranking rules between lexical and semantic artifact sections.
