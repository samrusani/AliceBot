# Current State

## Canonical Truth

- The working repo state is current through Sprint 5D, including post-review follow-up fixes for artifact-ingestion coverage and stale docs.
- Use [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md) for product scope, [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md) for implemented technical boundaries, [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md) for forward planning, and [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md) for durable operating rules.
- Historical build and review reports have been moved under [docs/archive/sprints](/Users/samirusani/Desktop/Codex/AliceBot/docs/archive/sprints).

## Implemented Repo Slice

- `apps/api` is the only shipped product surface. It implements continuity, tracing, deterministic context compilation, governed memory admission and review, embeddings, semantic retrieval, entities, policy and tool governance, approval persistence and resolution, approved-only `proxy.echo` execution, execution budgets, task/task-step lifecycle reads and mutations, explicit manual continuation lineage, explicit task-step linkage for approval and execution synchronization, deterministic rooted local task-workspace provisioning, explicit task-artifact registration, and narrow local text-artifact ingestion into durable chunk rows.
- The live schema includes continuity, trace, memory, embedding, entity, governance, `tasks`, `task_steps`, `task_workspaces`, `task_artifacts`, and `task_artifact_chunks` tables with row-level security on user-owned data.
- `apps/web` and `workers` remain starter scaffolds only.

## Current Boundaries

- Task workspaces are implemented only as deterministic rooted local directories plus durable `task_workspaces` records.
- Task artifacts are implemented only as explicit rooted local-file registrations under those workspaces plus narrow deterministic ingestion for `text/plain` and `text/markdown`.
- The shipped multi-step task path is still explicit and narrow: later steps are appended manually with lineage, while approval and execution synchronization use explicit linked `task_step_id` references.
- The only execution handler in the repo is the in-process no-external-I/O `proxy.echo` path.

## Not Implemented

- Retrieval, ranking, or embeddings over artifact chunks.
- Rich document parsing beyond the narrow local text ingestion seam.
- Read-only Gmail or Calendar connectors.
- Runner-style orchestration or automatic multi-step progression.
- Auth beyond the current database user-context model.

## Active Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth is still incomplete beyond database user context.
- Workspace provisioning and artifact ingestion are intentionally narrow and local; broader retrieval, embedding, connector, and rich-document flows still need their own accepted seams.

## Latest Local Verification

- Latest review artifact: `PASS WITH FIXES`.
- Post-review local verification on March 14, 2026:
  - `./.venv/bin/python -m pytest tests/unit` -> `347 passed`
  - `./.venv/bin/python -m pytest tests/integration` -> `104 passed`

## Planning Guardrails

- Plan from the implemented Sprint 5D repo state, not from older milestone narratives.
- Do not describe retrieval, embeddings, connectors, runner work, or broader rich-document handling as shipped.
- Keep live truth files compact; archive historical detail instead of re-expanding the active context set.
