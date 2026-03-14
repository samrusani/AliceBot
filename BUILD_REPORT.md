# BUILD_REPORT

## sprint objective

Implement Sprint 5F: Artifact Chunk Compile Integration V0 by extending `POST /v0/context/compile` so it can optionally retrieve durable artifact chunks through the existing lexical retrieval seam, return them in a separate context-pack section, and trace artifact include/exclude decisions without adding embeddings, semantic retrieval, connectors, runners, or UI work.

## completed work

- Added optional compile-request artifact retrieval input with one explicit scope per request:
  - `artifact_retrieval.kind = "task"` with `task_id`, `query`, `limit`
  - `artifact_retrieval.kind = "artifact"` with `task_artifact_id`, `query`, `limit`
- Added internal typed compile contracts for artifact retrieval:
  - `CompileContextTaskScopedArtifactRetrievalInput`
  - `CompileContextArtifactScopedArtifactRetrievalInput`
  - `CompileContextArtifactRetrievalInput`
- Added compile response contracts for a separate artifact section:
  - `context_pack.artifact_chunks`
  - `context_pack.artifact_chunk_summary`
  - `ArtifactRetrievalDecisionTracePayload`
- Kept the artifact section response-shape stable even when retrieval is not requested:
  - `artifact_chunks` returns `[]`
  - `artifact_chunk_summary.requested` is `false`
- Integrated compile-time artifact retrieval into `compile_and_persist_trace()` using only durable `task_artifact_chunks` rows and the shipped lexical retrieval seam.
- Preserved existing continuity, memory, entity, and entity-edge behavior unchanged.
- Recorded compile trace decisions for:
  - included artifact chunks
  - artifact chunks excluded by the compile limit
  - artifacts excluded because `ingestion_status != "ingested"`
- Added summary trace fields for artifact retrieval counts and scope kind.
- Added unit and integration coverage for:
  - artifact compile request routing and validation
  - deterministic artifact chunk ordering
  - non-ingested artifact exclusion
  - included and excluded artifact trace events
  - per-user isolation through compile path
  - stable compile response shape with the new section

## incomplete work

- None within Sprint 5F scope.

## files changed

- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/compiler.py`
- `apps/api/src/alicebot_api/main.py`
- `tests/unit/test_compiler.py`
- `tests/unit/test_main.py`
- `tests/integration/test_context_compile.py`
- `BUILD_REPORT.md`

## exact compile contract changes introduced

- `CompileContextRequest` now accepts optional `artifact_retrieval`.
- `artifact_retrieval` is a discriminated union:
  - task scope: `{ "kind": "task", "task_id": "<uuid>", "query": "<text>", "limit": <int> }`
  - artifact scope: `{ "kind": "artifact", "task_artifact_id": "<uuid>", "query": "<text>", "limit": <int> }`
- Artifact retrieval limits:
  - default: `5`
  - max: `50`
- `CompiledContextPack` now includes:
  - `artifact_chunks: list[ContextPackArtifactChunk]`
  - `artifact_chunk_summary: ContextPackArtifactChunkSummary`
- `artifact_chunk_summary` fields:
  - `requested`
  - `scope`
  - `query`
  - `query_terms`
  - `matching_rule`
  - `limit`
  - `searched_artifact_count`
  - `candidate_count`
  - `included_count`
  - `excluded_uningested_artifact_count`
  - `excluded_limit_count`
  - `order`

## artifact retrieval matching and ordering rule used

- Matching rule id: `casefolded_unicode_word_overlap_unique_query_terms_v1`
- Query normalization:
  - casefold query text
  - extract unique `\w+` terms in first-occurrence order
  - reject queries that contain no lexical terms
- Matching source:
  - only persisted `task_artifact_chunks` rows attached to visible artifacts
  - no raw file reads in compile path
- Exclusion rule:
  - artifacts with `ingestion_status != "ingested"` are excluded from artifact chunk results
- Ordering:
  - `matched_query_term_count_desc`
  - `first_match_char_start_asc`
  - `relative_path_asc`
  - `sequence_no_asc`
  - `id_asc`
- Compile limit behavior:
  - ordering is applied first
  - the first `limit` chunk matches are included
  - remaining matches are traced as `artifact_chunk_limit_exceeded`

## example compile request

```json
{
  "user_id": "11111111-1111-1111-1111-111111111111",
  "thread_id": "22222222-2222-2222-2222-222222222222",
  "artifact_retrieval": {
    "kind": "task",
    "task_id": "33333333-3333-3333-3333-333333333333",
    "query": "Alpha beta",
    "limit": 2
  }
}
```

## example compile response with artifact section

```json
{
  "trace_id": "44444444-4444-4444-4444-444444444444",
  "trace_event_count": 18,
  "context_pack": {
    "compiler_version": "continuity_v0",
    "artifact_chunks": [
      {
        "id": "55555555-5555-5555-5555-555555555555",
        "task_id": "33333333-3333-3333-3333-333333333333",
        "task_artifact_id": "66666666-6666-6666-6666-666666666666",
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
      },
      {
        "id": "77777777-7777-7777-7777-777777777777",
        "task_id": "33333333-3333-3333-3333-333333333333",
        "task_artifact_id": "88888888-8888-8888-8888-888888888888",
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
    "artifact_chunk_summary": {
      "requested": true,
      "scope": {
        "kind": "task",
        "task_id": "33333333-3333-3333-3333-333333333333"
      },
      "query": "Alpha beta",
      "query_terms": ["alpha", "beta"],
      "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
      "limit": 2,
      "searched_artifact_count": 3,
      "candidate_count": 3,
      "included_count": 2,
      "excluded_uningested_artifact_count": 1,
      "excluded_limit_count": 1,
      "order": [
        "matched_query_term_count_desc",
        "first_match_char_start_asc",
        "relative_path_asc",
        "sequence_no_asc",
        "id_asc"
      ]
    }
  }
}
```

## example artifact-retrieval trace events inside one compile run

```json
[
  {
    "kind": "context.included",
    "payload": {
      "entity_type": "artifact_chunk",
      "entity_id": "55555555-5555-5555-5555-555555555555",
      "reason": "within_artifact_chunk_limit",
      "position": 1,
      "scope_kind": "task",
      "task_id": "33333333-3333-3333-3333-333333333333",
      "task_artifact_id": "66666666-6666-6666-6666-666666666666",
      "relative_path": "docs/a.txt",
      "media_type": "text/plain",
      "ingestion_status": "ingested",
      "limit": 2,
      "matched_query_terms": ["alpha", "beta"],
      "matched_query_term_count": 2,
      "first_match_char_start": 0,
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 14
    }
  },
  {
    "kind": "context.excluded",
    "payload": {
      "entity_type": "artifact_chunk",
      "entity_id": "99999999-9999-9999-9999-999999999999",
      "reason": "artifact_chunk_limit_exceeded",
      "position": 3,
      "scope_kind": "task",
      "task_id": "33333333-3333-3333-3333-333333333333",
      "task_artifact_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "relative_path": "notes/c.txt",
      "media_type": "text/plain",
      "ingestion_status": "ingested",
      "limit": 2,
      "matched_query_terms": ["beta"],
      "matched_query_term_count": 1,
      "first_match_char_start": 0,
      "sequence_no": 1,
      "char_start": 0,
      "char_end_exclusive": 9
    }
  },
  {
    "kind": "context.excluded",
    "payload": {
      "entity_type": "task_artifact",
      "entity_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "reason": "artifact_not_ingested",
      "position": 3,
      "scope_kind": "task",
      "task_id": "33333333-3333-3333-3333-333333333333",
      "task_artifact_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "relative_path": "notes/hidden.txt",
      "media_type": "text/plain",
      "ingestion_status": "pending",
      "limit": 2
    }
  }
]
```

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_compiler.py`
  - result: `4 passed in 0.21s`
- `./.venv/bin/python -m pytest tests/unit/test_main.py`
  - result: `38 passed in 0.39s`
- `./.venv/bin/python -m pytest tests/integration/test_context_compile.py`
  - sandboxed attempt failed to reach local Postgres on `localhost:5432` with `Operation not permitted`
- `./.venv/bin/python -m pytest tests/integration/test_context_compile.py`
  - rerun with local database access: `7 passed in 2.17s`
- `./.venv/bin/python -m pytest tests/unit`
  - result: `360 passed in 0.56s`
- `./.venv/bin/python -m pytest tests/integration`
  - rerun with local database access: `107 passed in 31.19s`

## blockers/issues

- No remaining implementation blockers.
- Postgres-backed integration verification required elevated local database access because sandboxed localhost connections were denied.

## recommended next step

Use this compile-path artifact section as the only seam for later retrieval upgrades, then add semantic retrieval or richer document handling in a separate sprint without changing this deterministic lexical contract.

## what remains intentionally deferred to later milestones

- Artifact chunk embeddings
- Semantic retrieval or reranking for artifact chunks
- Compile-path merging of artifact chunks into memory or entity sections
- PDF, DOCX, OCR, or richer document parsing
- Gmail or Calendar connectors
- Runner or orchestration work
- UI work
