# SPRINT_PACKET.md

## Sprint Title

Sprint 5I: Compile-Path Semantic Artifact Retrieval Adoption

## Sprint Type

feature

## Sprint Reason

Milestone 5 now has deterministic lexical artifact retrieval in the compile path and a separate direct semantic artifact retrieval primitive over durable chunk embeddings. The next safe step is to adopt semantic artifact retrieval into the compiler as a separate context section, while still deferring hybrid lexical-plus-semantic artifact merging, reranking, connectors, and UI.

## Sprint Intent

Extend the existing context-compile path so it can optionally retrieve semantic artifact chunks using the shipped `task_artifact_chunk_embeddings` retrieval primitive, while keeping semantic artifact results separate from lexical artifact retrieval and deferring hybrid artifact fusion.

## Git Instructions

- Branch Name: `codex/sprint-5i-compile-semantic-artifact-retrieval`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5C shipped explicit task-artifact registration.
- Sprint 5D shipped deterministic local artifact ingestion into durable chunk rows.
- Sprint 5E shipped deterministic lexical artifact-chunk retrieval.
- Sprint 5F shipped compile-path lexical artifact chunk inclusion.
- Sprint 5G shipped durable artifact-chunk embedding persistence.
- Sprint 5H shipped direct semantic artifact retrieval over those durable chunk embeddings.
- The next narrow Milestone 5 seam is compile-path adoption of semantic artifact retrieval only, so later hybrid artifact retrieval can build on an explicit compile-time semantic section instead of collapsing lexical and semantic behavior in one sprint.

## In Scope

- Define typed contracts for:
  - optional semantic artifact retrieval input on compile requests
  - semantic artifact chunk result items inside the compiled context pack
  - semantic artifact retrieval summary metadata inside compile responses
  - semantic artifact retrieval trace payloads
- Extend the compile path so it can:
  - accept an explicit semantic artifact retrieval request scoped to one visible task or one visible artifact
  - accept an explicit `embedding_config_id` and caller-supplied query vector
  - reuse the existing semantic artifact retrieval primitive during compile
  - include semantic artifact chunks in a separate context-pack section
  - record semantic artifact include/exclude decisions in `trace_events`
  - preserve deterministic output for the same stored data and inputs
- Ensure compile behavior:
  - leaves current continuity, memory, entity, lexical artifact, and other context sections intact
  - does not merge lexical and semantic artifact sections
  - excludes non-ingested artifacts
  - scopes strictly by user ownership
  - uses deterministic ordering and explicit per-section limits
- Add unit and integration tests for:
  - compile request validation for semantic artifact retrieval input
  - deterministic semantic artifact section ordering
  - exclusion of non-ingested artifacts
  - trace logging for included and excluded semantic artifact chunks
  - per-user isolation through the compile path
  - response-shape stability for the new semantic artifact section

## Out of Scope

- No hybrid lexical plus semantic artifact retrieval.
- No reranking across semantic artifact chunks.
- No lexical-plus-semantic deduplication or fusion.
- No model or external API calls to generate query embeddings.
- No richer document parsing beyond the already-shipped local text ingestion seam.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No UI work.

## Required Deliverables

- Stable compile-request and compile-response contract updates for semantic artifact retrieval input and output.
- Compile-path integration with the existing semantic artifact retrieval primitive.
- Trace coverage for semantic artifact retrieval decisions inside compile runs.
- Unit and integration coverage for compile-path semantic artifact behavior, ordering, exclusion rules, validation, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- `POST /v0/context/compile` can optionally accept semantic artifact retrieval input and return a separate semantic artifact chunk section in the context pack.
- Compile-path semantic artifact retrieval uses only durable `task_artifact_chunk_embeddings`, `task_artifact_chunks`, and artifact records already persisted in the repo.
- Compile-path semantic artifact retrieval rejects missing configs, dimension mismatches, and cross-user access deterministically.
- Non-ingested artifacts are excluded from semantic artifact compile results.
- Semantic artifact include/exclude decisions are persisted in `trace_events`.
- Result ordering is deterministic within the semantic artifact section.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No hybrid retrieval, reranking, connector, runner, UI, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep compile-path adoption narrow and boring.
- Reuse the existing semantic artifact retrieval primitive; do not read raw files during compile.
- Keep semantic artifact chunks in a separate response section from lexical artifact chunks and from memory/entity context.
- Require explicit semantic artifact input; do not auto-enable semantic retrieval.
- Do not merge semantic and lexical artifact retrieval in the same sprint.

## Suggested Work Breakdown

1. Define compile contract updates for optional semantic artifact retrieval input and output.
2. Integrate the existing semantic artifact retrieval primitive into the compile path.
3. Add semantic artifact result summaries and trace-event payloads.
4. Preserve current context sections while adding a separate semantic artifact section.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact compile contract changes introduced
- the semantic artifact similarity metric and ordering rule used
- exact commands run
- unit and integration test results
- one example compile request and response showing the semantic artifact section
- one example of semantic artifact retrieval trace events inside one compile run
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to compile-path semantic artifact retrieval adoption
- semantic artifact retrieval is explicit-input, durable-source-only, and validation-backed
- lexical and semantic artifact results remain separate rather than merged
- ordering, exclusion rules, trace visibility, and isolation are test-backed
- no hidden hybrid retrieval, reranking, connector, runner, UI, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can optionally include semantic artifact chunks inside `POST /v0/context/compile`, trace those semantic inclusion decisions, and verify the full path with Postgres-backed tests, while still deferring hybrid artifact retrieval, reranking, connectors, and UI.
