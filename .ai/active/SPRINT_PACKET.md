# SPRINT_PACKET.md

## Sprint Title

Sprint 5H: Semantic Artifact Chunk Retrieval Primitive

## Sprint Type

feature

## Sprint Reason

Milestone 5 now has deterministic artifact chunk ingestion, lexical retrieval, compile-path lexical artifact inclusion, and durable artifact-chunk embedding storage. The next safe step is a direct semantic retrieval primitive over those stored chunk embeddings, while still deferring compile-path semantic use, hybrid artifact retrieval, connectors, and UI.

## Sprint Intent

Add the first read-side semantic retrieval primitive over stored `task_artifact_chunk_embeddings`, with explicit embedding-config selection and deterministic result ordering, without yet wiring semantic artifact retrieval into the compile path or combining it with lexical artifact retrieval.

## Git Instructions

- Branch Name: `codex/sprint-5h-semantic-artifact-chunk-retrieval`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration.
- Sprint 5D shipped deterministic local artifact ingestion into durable chunk rows.
- Sprint 5E shipped deterministic lexical retrieval over those chunk rows.
- Sprint 5F shipped compile-path lexical artifact chunk inclusion.
- Sprint 5G shipped durable artifact-chunk embedding persistence tied to existing embedding configs.
- The next narrow Milestone 5 seam is semantic artifact retrieval over those stored vectors only, so later compile adoption and hybrid artifact retrieval can build on an explicit retrieval primitive instead of hidden assumptions.

## In Scope

- Define typed contracts for:
  - semantic artifact retrieval requests
  - semantic artifact retrieval result items
  - retrieval summary metadata
- Implement a narrow semantic retrieval seam that:
  - accepts an explicit `embedding_config_id`
  - accepts a caller-supplied query vector
  - searches only durable `task_artifact_chunk_embeddings`
  - joins to visible `task_artifact_chunks` and visible `task_artifacts`
  - scopes retrieval by the current user plus one explicit task or one explicit artifact
  - validates query-vector dimension against the chosen embedding config
  - computes similarity using the stored vectors already persisted in the repo
  - returns deterministic ordered chunk results with explicit score metadata
  - excludes artifacts that are not yet ingested
- Implement the minimal API or service paths needed for:
  - semantic retrieval for one task
  - semantic retrieval for one artifact when the caller wants a narrower scope
- Add unit and integration tests for:
  - dimension validation
  - deterministic retrieval ordering and tie-breaking
  - scoped retrieval by task and by artifact
  - empty-result behavior
  - exclusion of non-ingested artifacts
  - per-user isolation
  - stable response shape

## Out of Scope

- No compile-path semantic artifact retrieval yet.
- No hybrid lexical plus semantic artifact retrieval.
- No reranking layer beyond direct similarity ordering.
- No model or external API calls to generate query embeddings.
- No richer document parsing beyond the already-shipped local text ingestion seam.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Stable semantic artifact retrieval request and response contracts.
- Minimal deterministic semantic retrieval path over existing `task_artifact_chunk_embeddings`.
- Unit and integration coverage for ordering, validation, scoping, exclusion rules, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can submit a query vector plus `embedding_config_id` and retrieve relevant visible artifact chunks for one task.
- A client can submit a query vector plus `embedding_config_id` and retrieve relevant visible artifact chunks for one artifact.
- Retrieval uses only durable `task_artifact_chunk_embeddings`, `task_artifact_chunks`, and artifact records already persisted in the repo.
- Retrieval rejects missing configs, dimension mismatches, and cross-user access deterministically.
- Non-ingested artifacts are excluded from semantic retrieval results.
- Result ordering is deterministic and documented.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No compile integration changes, hybrid retrieval, connector, runner, UI, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep semantic retrieval narrow and boring.
- Reuse existing embedding configs and durable artifact chunk embeddings; do not introduce a second embedding store.
- Use explicit caller-selected config and query vector input; do not auto-pick configs.
- Keep scope explicit: one task or one artifact per request.
- Do not merge semantic artifact retrieval into the main compiler in the same sprint.

## Suggested Work Breakdown

1. Define semantic artifact retrieval request and response contracts.
2. Implement deterministic similarity search over existing artifact chunk embeddings.
3. Add explicit task-scoped and artifact-scoped semantic retrieval paths.
4. Enforce config validation, non-ingested exclusion, and current-user isolation.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact semantic artifact retrieval contracts introduced
- the similarity metric and ordering rule used
- exact commands run
- unit and integration test results
- one example task-scoped semantic retrieval response
- one example artifact-scoped semantic retrieval response
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to the semantic artifact chunk retrieval primitive
- retrieval is explicit-config, durable-source-only, and validation-backed
- ordering, exclusion rules, and isolation are test-backed
- no hidden compile integration changes, hybrid retrieval, connector, runner, UI, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can retrieve relevant ingested artifact chunks through a deterministic semantic read path scoped to one task or one artifact, verify the full path with Postgres-backed tests, and still defer compile-path semantic use, hybrid artifact retrieval, connectors, and UI.
