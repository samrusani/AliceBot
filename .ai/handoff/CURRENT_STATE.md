# Current State

## Canonical Truth

- The accepted repo state is current through Sprint 5A.
- Use [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) for product scope, [ARCHITECTURE.md](ARCHITECTURE.md) for implemented technical boundaries, [ROADMAP.md](ROADMAP.md) for forward planning, and [RULES.md](RULES.md) for durable operating rules.
- Historical build and review reports have been moved under [docs/archive/sprints](docs/archive/sprints).

## Implemented Repo Slice

- `apps/api` is the only shipped product surface. It implements continuity, tracing, deterministic context compilation, governed memory admission and review, embeddings, semantic retrieval, entities, policy and tool governance, approval persistence and resolution, approved-only `proxy.echo` execution, execution budgets, task/task-step lifecycle reads and mutations, explicit manual continuation lineage, explicit task-step linkage for approval and execution synchronization, and deterministic rooted local task-workspace provisioning.
- The live schema includes continuity, trace, memory, embedding, entity, governance, `tasks`, `task_steps`, and `task_workspaces` tables with row-level security on user-owned data.
- `apps/web` and `workers` remain starter scaffolds only.

## Current Boundaries

- Task workspaces are implemented only as deterministic rooted local directories plus durable `task_workspaces` records.
- The shipped multi-step task path is still explicit and narrow: later steps are appended manually with lineage, while approval and execution synchronization use explicit linked `task_step_id` references.
- The only execution handler in the repo is the in-process no-external-I/O `proxy.echo` path.

## Not Implemented

- Artifact storage or indexing beyond the local workspace boundary.
- Document ingestion, chunking, or document retrieval.
- Read-only Gmail or Calendar connectors.
- Runner-style orchestration or automatic multi-step progression.
- Auth beyond the current database user-context model.

## Active Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth is still incomplete beyond database user context.
- Workspace provisioning is intentionally narrow and local; broader artifact and document flows still need their own accepted seams.

## Latest Accepted Verification

- Sprint 5A review status: `PASS`.
- Accepted verification on March 13, 2026:
  - `./.venv/bin/python -m pytest tests/unit` -> `315 passed`
  - `./.venv/bin/python -m pytest tests/integration` -> `99 passed`

## Planning Guardrails

- Plan from the implemented Sprint 5A repo state, not from older milestone narratives.
- Do not describe Milestone 5 document, artifact, connector, or runner work as shipped.
- Keep live truth files compact; archive historical detail instead of re-expanding the active context set.
