# BUILD_REPORT

## sprint objective

Implement Sprint 5J: merge the existing lexical and semantic artifact chunk retrieval paths inside `POST /v0/context/compile` into one deterministic hybrid artifact section with explicit provenance, deduplication, limits, and trace visibility.

## completed work

- Replaced the compile-time split artifact output with one merged `context_pack.artifact_chunks` section.
- Added hybrid artifact contracts for:
  - per-chunk source provenance
  - merged artifact summary metadata
  - hybrid artifact decision trace payloads
- Implemented deterministic hybrid artifact merge logic that:
  - reuses the existing lexical and semantic retrieval seams
  - deduplicates by durable chunk id
  - preserves dual-source provenance
  - applies lexical-first precedence under the shared compile output limit
  - excludes non-ingested artifacts
  - emits explicit dedup/include/exclude trace events
- Updated compile summary trace payloads to report hybrid artifact request state, candidate counts, dedup counts, dual-source counts, and limit exclusions.
- Updated prompt assembly to serialize only the merged compile-time artifact section.
- Added unit and integration coverage for:
  - lexical-only artifact compile behavior
  - semantic-only artifact compile behavior
  - hybrid dual-source provenance
  - deterministic merge ordering
  - limit enforcement across merged candidates
  - non-ingested exclusion
  - per-user isolation
  - response-shape stability

## exact hybrid artifact merge contract changes introduced

- Added `ArtifactSelectionSource = Literal["lexical", "semantic"]`.
- Updated `ContextPackArtifactChunk` to carry:
  - `source_provenance.sources`
  - `source_provenance.lexical_match`
  - `source_provenance.semantic_score`
- Expanded `ContextPackArtifactChunkSummary` to include:
  - `lexical_requested`
  - `semantic_requested`
  - `embedding_config_id`
  - `query_vector_dimensions`
  - `lexical_limit`
  - `semantic_limit`
  - `lexical_candidate_count`
  - `semantic_candidate_count`
  - `merged_candidate_count`
  - `deduplicated_count`
  - `included_lexical_only_count`
  - `included_semantic_only_count`
  - `included_dual_source_count`
  - `source_precedence`
  - `lexical_order`
  - `semantic_order`
  - `merged_order`
- Added `HybridArtifactRetrievalDecisionTracePayload`.
- Removed compile-time `semantic_artifact_chunks` and `semantic_artifact_chunk_summary` from `CompiledContextPack`.

## merge precedence and deduplication rule used

- Dedup key: durable artifact chunk id.
- Source precedence: `lexical` before `semantic`.
- Merged ordering:
  - source precedence
  - lexical rank
  - semantic rank
  - `relative_path`
  - `sequence_no`
  - `id`
- Final compile limit:
  - use `artifact_retrieval.limit` when lexical retrieval is present
  - otherwise use `semantic_artifact_retrieval.limit`
- When the same chunk appears in both candidate sets:
  - keep one item
  - set `source_provenance.sources` to `["lexical", "semantic"]`
  - preserve the lexical match payload
  - preserve the semantic score
  - emit `hybrid_artifact_chunk_deduplicated`

## incomplete work

- None within Sprint 5J scope.

## files changed

- `apps/api/src/alicebot_api/compiler.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/response_generation.py`
- `tests/integration/test_context_compile.py`
- `tests/unit/test_compiler.py`
- `tests/unit/test_main.py`
- `tests/unit/test_response_generation.py`
- `BUILD_REPORT.md`

## tests run

- `./.venv/bin/python -m pytest tests/unit/test_compiler.py tests/unit/test_main.py tests/unit/test_response_generation.py`
  - `50 passed in 0.50s`
- `./.venv/bin/python -m pytest tests/unit`
  - `380 passed in 0.56s`
- `./.venv/bin/python -m pytest tests/integration/test_context_compile.py`
  - initial sandboxed run failed because local Postgres on `localhost:5432` was blocked
- `./.venv/bin/python -m pytest tests/integration`
  - `118 passed in 35.59s`

## unit and integration test results

- Unit suite: pass
- Integration suite: pass

## example compile request and merged response

```json
{
  "request": {
    "user_id": "11111111-1111-1111-8111-111111111111",
    "thread_id": "22222222-2222-2222-8222-222222222222",
    "artifact_retrieval": {
      "kind": "task",
      "task_id": "33333333-3333-3333-8333-333333333333",
      "query": "Alpha beta",
      "limit": 2
    },
    "semantic_artifact_retrieval": {
      "kind": "task",
      "task_id": "33333333-3333-3333-8333-333333333333",
      "embedding_config_id": "44444444-4444-4444-8444-444444444444",
      "query_vector": [1.0, 0.0, 0.0],
      "limit": 2
    }
  },
  "response": {
    "context_pack": {
      "artifact_chunks": [
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
          "source_provenance": {
            "sources": ["lexical", "semantic"],
            "lexical_match": {
              "matched_query_terms": ["alpha", "beta"],
              "matched_query_term_count": 2,
              "first_match_char_start": 0
            },
            "semantic_score": 1.0
          }
        }
      ],
      "artifact_chunk_summary": {
        "requested": true,
        "lexical_requested": true,
        "semantic_requested": true,
        "scope": {
          "kind": "task",
          "task_id": "33333333-3333-3333-8333-333333333333"
        },
        "query": "Alpha beta",
        "query_terms": ["alpha", "beta"],
        "embedding_config_id": "44444444-4444-4444-8444-444444444444",
        "query_vector_dimensions": 3,
        "limit": 2,
        "lexical_limit": 2,
        "semantic_limit": 2,
        "searched_artifact_count": 3,
        "lexical_candidate_count": 3,
        "semantic_candidate_count": 3,
        "merged_candidate_count": 3,
        "deduplicated_count": 3,
        "included_count": 2,
        "included_lexical_only_count": 0,
        "included_semantic_only_count": 0,
        "included_dual_source_count": 2,
        "excluded_uningested_artifact_count": 1,
        "excluded_limit_count": 1,
        "matching_rule": "casefolded_unicode_word_overlap_unique_query_terms_v1",
        "similarity_metric": "cosine_similarity"
      }
    }
  }
}
```

## example hybrid artifact trace events inside one compile run

```json
[
  {
    "kind": "context.included",
    "payload": {
      "entity_type": "artifact_chunk",
      "entity_id": "55555555-5555-5555-8555-555555555555",
      "reason": "hybrid_artifact_chunk_deduplicated",
      "position": 1,
      "scope_kind": "task",
      "task_id": "33333333-3333-3333-8333-333333333333",
      "task_artifact_id": "66666666-6666-6666-8666-666666666666",
      "relative_path": "docs/a.txt",
      "ingestion_status": "ingested",
      "selected_sources": ["lexical", "semantic"],
      "matched_query_terms": ["alpha", "beta"],
      "score": 1.0
    }
  },
  {
    "kind": "context.excluded",
    "payload": {
      "entity_type": "artifact_chunk",
      "entity_id": "77777777-7777-7777-8777-777777777777",
      "reason": "hybrid_artifact_chunk_limit_exceeded",
      "position": 3,
      "scope_kind": "task",
      "task_id": "33333333-3333-3333-8333-333333333333",
      "task_artifact_id": "88888888-8888-8888-8888-888888888888",
      "relative_path": "notes/c.txt",
      "ingestion_status": "ingested",
      "selected_sources": ["lexical", "semantic"],
      "score": 0.0
    }
  }
]
```

## blockers/issues

- No product blocker.
- Integration tests required elevated localhost access because the sandbox blocked Postgres connections to `localhost:5432`.

## what remains intentionally deferred to later milestones

- Reranking across lexical and semantic artifact candidates
- Weighted or learned fusion
- Model-generated query embeddings
- Connector-backed artifact retrieval
- Richer document parsing
- Runner orchestration
- UI changes

## recommended next step

Run review against the new merged compile artifact contract, with attention on downstream consumers that may still expect the removed compile-time `semantic_artifact_chunks` section.
