# Current State

## Canonical Truth

- The working repo state is current through Sprint 5J, including compile-path semantic artifact retrieval and deterministic hybrid lexical-plus-semantic artifact merge in compile.
- Use [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md) for product scope, [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md) for implemented technical boundaries, [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md) for forward planning, and [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md) for durable operating rules.
- Historical build and review reports remain the source of sprint-by-sprint detail; the active handoff should stay compact and current.

## Implemented Repo Slice

- `apps/api` is the only shipped product surface. It implements continuity, tracing, deterministic context compilation, governed memory admission and review, embeddings, semantic retrieval, entities, policy and tool governance, approval persistence and resolution, approved-only `proxy.echo` execution, execution budgets, task/task-step lifecycle reads and mutations, explicit manual continuation lineage, explicit task-step linkage for approval and execution synchronization, deterministic rooted local task-workspace provisioning, explicit task-artifact registration, narrow local text-artifact ingestion into durable chunk rows, artifact-chunk embeddings, direct lexical and semantic artifact retrieval, compile-path semantic artifact retrieval, and deterministic hybrid lexical-plus-semantic artifact merge inside the compile response.
- The live schema includes continuity, trace, memory, embedding, entity, governance, `tasks`, `task_steps`, `task_workspaces`, `task_artifacts`, `task_artifact_chunks`, and `task_artifact_chunk_embeddings` tables with row-level security on user-owned data.
- `apps/web` and `workers` remain starter scaffolds only.

## Current Boundaries

- Task workspaces are implemented only as deterministic rooted local directories plus durable `task_workspaces` records.
- Task artifacts are implemented only as explicit rooted local-file registrations under those workspaces plus narrow deterministic ingestion for `text/plain` and `text/markdown`.
- Artifact retrieval operates only over persisted chunk rows and persisted chunk embeddings for one visible task or one visible artifact at a time; compile does not read raw files directly.
- Compile can now include artifact chunks from lexical retrieval, semantic retrieval, or a deterministic hybrid merge of both into one artifact section with explicit per-chunk source provenance.
- The shipped multi-step task path is still explicit and narrow: later steps are appended manually with lineage, while approval and execution synchronization use explicit linked `task_step_id` references.
- The only execution handler in the repo is the in-process no-external-I/O `proxy.echo` path.

## Not Implemented

- Rich document parsing beyond the narrow local text ingestion seam.
- Read-only Gmail or Calendar connectors.
- Runner-style orchestration or automatic multi-step progression.
- Artifact reranking or weighted fusion beyond the current lexical-first hybrid compile merge.
- Auth beyond the current database user-context model.

## Active Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth is still incomplete beyond database user context.
- Artifact ingestion and retrieval are intentionally narrow and local; richer document parsing, connectors, and any retrieval changes beyond the shipped hybrid compile contract still need their own accepted seams.

## Latest Accepted Verification

- Latest accepted runtime verification totals for the shipped Sprint 5J seams were:
  - `./.venv/bin/python -m pytest tests/unit` -> `380 passed`
  - `./.venv/bin/python -m pytest tests/integration` -> `118 passed`
- Sprint 5K is documentation-only truth synchronization; it does not change runtime, schema, or API behavior.

## Planning Guardrails

- Plan from the implemented Sprint 5J repo state, not from older milestone narratives.
- Do not describe richer document parsing, connectors, runner work, UI work, or artifact reranking beyond the current lexical-first hybrid compile merge as shipped.
- The immediate next move after this truth-sync sprint is a narrow richer-document-parsing sprint that builds on the existing rooted workspace, durable chunk, and shipped hybrid artifact compile baseline.
