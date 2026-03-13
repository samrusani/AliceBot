# Current State

## What Exists Today

- Canonical project docs now describe the shipped repo state through Sprint 4O.
- `apps/api` implements the accepted backend seams for continuity, tracing, context compilation, governed memory, memory review, embeddings, semantic retrieval, entities, policies, tools, approvals, approved proxy execution, execution budgets, execution review, tasks, task steps, and explicit manual continuation lineage.
- The live schema now includes continuity tables, trace tables, memory tables, embedding tables, entity tables, governance tables, plus `tasks` and `task_steps`.
- `apps/web` and `workers` remain starter scaffolds only; no workspace UI, runner, or background-job orchestration is shipped.

## Stable / Trusted Areas

- Immutable event log and persisted trace model with per-user isolation.
- Deterministic context compilation and deterministic prompt assembly over durable sources.
- Governed memory admission, narrow deterministic explicit-preference extraction, explicit embedding storage, semantic retrieval, and deterministic hybrid memory merge during compile.
- Deterministic policy evaluation, tool allowlist evaluation, tool routing, approval persistence, approval resolution, approved-only `proxy.echo` execution, durable execution review, and execution-budget enforcement.
- Durable task and task-step reads, deterministic task-step sequencing, explicit task-step transitions, and explicit manual continuation with lineage validated against the parent step outcome.
- Sprint 4O review verification:
  - `./.venv/bin/python -m pytest tests/unit` -> `284 passed`
  - `./.venv/bin/python -m pytest tests/integration` -> `95 passed`

## Incomplete / At-Risk Areas

- Auth beyond DB user context is still unimplemented.
- Memory extraction and retrieval quality remain major ship-gating risks.
- Document ingestion, scoped task workspaces, artifact handling, and read-only connectors have not started in code.
- The current multi-step boundary is still narrow: approval-resolution and execution-synchronization helpers continue to target `task_steps.sequence_no = 1`, even though manual continuation is now implemented for later steps.

## Current Milestone Position

- The repo has completed the implementation planned through Milestone 4.
- Milestone 5 has not started in shipped code.
- The project is at a truth-sync checkpoint before Milestone 5 entry.

## Latest State Summary

- Local runtime assets exist for Docker Compose, Postgres bootstrap, API startup, migrations, and backend tests.
- `POST /v0/approvals/requests` now creates one durable task plus one initial task step for each routed governed request, with task and task-step lifecycle traces.
- `GET /v0/tasks`, `GET /v0/tasks/{task_id}`, `GET /v0/tasks/{task_id}/steps`, and `GET /v0/task-steps/{task_step_id}` expose durable task/task-step review reads with deterministic ordering.
- `POST /v0/tasks/{task_id}/steps` now appends exactly one manual continuation step when the latest step is appendable and explicit lineage points to that latest visible parent step.
- `POST /v0/task-steps/{task_step_id}/transition` now advances only the latest visible step through the explicit status graph and keeps the parent task status synchronized.
- Task-step lineage is trace-visible through `task.step.continuation.request`, `task.step.continuation.lineage`, and `task.step.continuation.summary` events.

## Critical Constraints

- Do not treat planned workspace, connector, runner, or broader side-effect work as implemented.
- Do not bypass approval boundaries for consequential actions.
- Do not replace compiled durable context with raw transcript stuffing.
- Appended task steps must carry explicit lineage; do not infer provenance heuristically from task history.
- Keep the current multi-step boundary explicit until the first-step lifecycle helpers are removed or constrained.

## Immediate Next Move

- Take the smallest follow-up sprint that removes or explicitly constrains the remaining `task_steps.sequence_no = 1` approval/execution synchronization assumptions before any runner, workspace, or connector work begins.
