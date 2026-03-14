# BUILD_REPORT

## sprint objective

Implement Sprint 5E: Artifact Chunk Retrieval V0 by adding a narrow, deterministic lexical retrieval path over durable `task_artifact_chunks`, scoped to one visible task or one visible artifact, without adding embeddings, semantic ranking, compile-path integration, connectors, runners, or UI work.

## completed work

- Added retrieval contracts in `apps/api/src/alicebot_api/contracts.py`:
  - `TaskScopedArtifactChunkRetrievalInput(task_id, query)`
  - `ArtifactScopedArtifactChunkRetrievalInput(task_artifact_id, query)`
  - `TaskArtifactChunkRetrievalMatch`
  - `TaskArtifactChunkRetrievalItem`
  - `TaskArtifactChunkRetrievalScope`
  - `TaskArtifactChunkRetrievalSummary`
  - `TaskArtifactChunkRetrievalResponse`
  - `TASK_ARTIFACT_CHUNK_RETRIEVAL_ORDER = ["matched_query_term_count_desc", "first_match_char_start_asc", "relative_path_asc", "sequence_no_asc", "id_asc"]`
- Added retrieval behavior in `apps/api/src/alicebot_api/artifacts.py`:
  - explicit query validation requiring at least one lexical word
  - query normalization via casefolded unique `\w+` terms in first-occurrence order
  - chunk matching against persisted chunk text only
  - task-scoped retrieval across ingested artifacts for one visible task
  - artifact-scoped retrieval for one visible artifact
  - exclusion of artifacts whose `ingestion_status != "ingested"`, even if chunk rows exist
  - deterministic response ordering with explicit per-item match metadata
- Added the minimal API routes in `apps/api/src/alicebot_api/main.py`:
  - `POST /v0/tasks/{task_id}/artifact-chunks/retrieve`
  - `POST /v0/task-artifacts/{task_artifact_id}/chunks/retrieve`
- Added store support in `apps/api/src/alicebot_api/store.py`:
  - `list_task_artifacts_for_task(task_id)`
- Added unit and integration coverage for:
  - deterministic retrieval ordering
  - task-scoped retrieval
  - artifact-scoped retrieval
  - empty-result behavior
  - exclusion of non-ingested artifacts
  - per-user isolation
  - stable response shape

Exact retrieval contracts introduced:

- Request inputs:
  - `TaskScopedArtifactChunkRetrievalInput(task_id: UUID, query: str)`
  - `ArtifactScopedArtifactChunkRetrievalInput(task_artifact_id: UUID, query: str)`
- Result item:
  - `id`
  - `task_id`
  - `task_artifact_id`
  - `relative_path`
  - `media_type`
  - `sequence_no`
  - `char_start`
  - `char_end_exclusive`
  - `text`
  - `match = {matched_query_terms, matched_query_term_count, first_match_char_start}`
- Summary metadata:
  - `total_count`
  - `searched_artifact_count`
  - `query`
  - `query_terms`
  - `matching_rule`
  - `order`
  - `scope = {kind, task_id, task_artifact_id?}`

Lexical matching rule used:

- Rule id: `casefolded_unicode_word_overlap_unique_query_terms_v1`
- Query normalization:
  - casefold the query
  - extract `\w+` terms
  - deduplicate in first-occurrence order
  - reject queries that produce zero terms
- Chunk match rule:
  - casefold the stored chunk text
  - extract `\w+` chunk terms
  - a chunk matches when at least one normalized query term is present in the chunk term set
  - `matched_query_terms` are returned in normalized query order
  - `matched_query_term_count` is the count of distinct matched query terms
  - `first_match_char_start` is the earliest start offset in the chunk text of any matched term

Ordering rule used:

- `matched_query_term_count` descending
- `first_match_char_start` ascending
- `relative_path` ascending
- `sequence_no` ascending
- `id` ascending

Example task-scoped retrieval response:

```json
{
  "items": [
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "task_id": "22222222-2222-2222-2222-222222222222",
      "task_artifact_id": "33333333-3333-3333-3333-333333333333",
      "relative_path": "docs/a.txt",
      "media_type": "text/plain",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 14,
      "text": "beta alpha doc",
      "match": {
        "matched_query_terms": ["alpha", "beta"],
        "matched_query_term_count": 2,
        "first_match_char_start": 0
      }
    }
  ],
  "summary": {
    "total_count": 1,
    "searched_artifact_count": 1,
    "query": "Alpha beta",
    "query_terms": ["alpha", "beta"],
    "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
    "order": [
      "matched_query_term_count_desc",
      "first_match_char_start_asc",
      "relative_path_asc",
      "sequence_no_asc",
      "id_asc"
    ],
    "scope": {
      "kind": "task",
      "task_id": "22222222-2222-2222-2222-222222222222"
    }
  }
}
```

Example artifact-scoped retrieval response:

```json
{
  "items": [
    {
      "id": "44444444-4444-4444-4444-444444444444",
      "task_id": "22222222-2222-2222-2222-222222222222",
      "task_artifact_id": "55555555-5555-5555-5555-555555555555",
      "relative_path": "notes/b.md",
      "media_type": "text/markdown",
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 15,
      "text": "alpha beta note",
      "match": {
        "matched_query_terms": ["alpha", "beta"],
        "matched_query_term_count": 2,
        "first_match_char_start": 0
      }
    }
  ],
  "summary": {
    "total_count": 1,
    "searched_artifact_count": 1,
    "query": "Alpha beta",
    "query_terms": ["alpha", "beta"],
    "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
    "order": [
      "matched_query_term_count_desc",
      "first_match_char_start_asc",
      "relative_path_asc",
      "sequence_no_asc",
      "id_asc"
    ],
    "scope": {
      "kind": "artifact",
      "task_id": "22222222-2222-2222-2222-222222222222",
      "task_artifact_id": "55555555-5555-5555-5555-555555555555"
    }
  }
}
```

## incomplete work

- None within Sprint 5E scope.

## files changed

- `apps/api/src/alicebot_api/artifacts.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `tests/integration/test_task_artifacts_api.py`
- `tests/unit/test_artifacts.py`
- `tests/unit/test_artifacts_main.py`
- `tests/unit/test_task_artifact_store.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py tests/unit/test_artifacts_main.py tests/unit/test_task_artifact_store.py`
  - result: `37 passed in 0.44s`
- `./.venv/bin/python -m pytest tests/unit/test_artifacts.py tests/unit/test_artifacts_main.py`
  - result: `35 passed in 0.25s`
- `./.venv/bin/python -m pytest tests/integration/test_task_artifacts_api.py`
  - sandboxed attempt failed to reach local Postgres on `localhost:5432` with `Operation not permitted`
- `./.venv/bin/python -m pytest tests/unit`
  - result: `358 passed in 0.56s`
- `./.venv/bin/python -m pytest tests/integration`
  - rerun with local access: `105 passed in 29.62s`
- `git diff --check`
  - result: passed

## blockers/issues

- No remaining implementation blockers.
- Postgres-backed integration verification required unsandboxed localhost access. After rerun with local access, the full integration suite passed.

## recommended next step

Build the next milestone on top of this deterministic read contract by adding richer retrieval quality or compile-path usage in a separate sprint, while keeping those changes explicitly scoped and test-backed.

## intentionally deferred

- Embeddings for artifact chunks
- Semantic retrieval or reranking
- Compile-path integration of artifact chunks
- PDF, DOCX, OCR, or richer document parsing
- Connector work
- Runner or orchestration work
- UI work
