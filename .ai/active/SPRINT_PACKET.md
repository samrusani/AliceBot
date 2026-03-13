# SPRINT_PACKET.md

## Sprint Title

Sprint 5A: Task Workspace Records and Provisioning

## Sprint Type

feature

## Sprint Reason

Milestone 5 should start at the workspace boundary, not at document ingestion or connectors. The repo now has the task and execution substrate needed to add one deterministic, user-scoped task workspace seam without expanding product scope.

## Sprint Intent

Begin Milestone 5 by adding user-scoped task workspace records plus deterministic local workspace provisioning, so later artifact handling, document ingestion, and read-only connectors have a governed workspace boundary to build on.

## Git Instructions

- Branch Name: `codex/sprint-5a-task-workspaces`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint on top of this branch
- Merge Policy: squash merge only after reviewer `PASS`; if review fails, repair on the same branch until pass or explicit abandonment

## Why This Sprint

- Sprint 4S is implemented and passed: approvals and executions now both use explicit task-step linkage, so the Milestone 4 lifecycle substrate is in place.
- The roadmap says workspace and artifact boundaries should land before document-heavy or connector-heavy flows rely on them.
- The narrowest safe Milestone 5 entry slice is workspace provisioning only, not artifact indexing, document ingestion, or connectors.
- This keeps sequencing boring and maintainable by establishing the workspace boundary first.

## In Scope

- Add schema and migration support for:
  - `task_workspaces`
- Define typed contracts for:
  - workspace create responses
  - workspace list responses
  - workspace detail responses
- Implement a minimal workspace seam that:
  - provisions one deterministic local workspace path for a visible task
  - persists one user-scoped workspace record linked to that task
  - validates the workspace path is rooted under one configured workspace base directory
  - prevents duplicate active workspace creation for the same task
  - exposes deterministic list and detail reads
- Implement the minimal API or service paths needed for:
  - creating a workspace for a task
  - listing workspaces
  - reading one workspace by id
- Add unit and integration tests for:
  - workspace creation
  - deterministic path generation
  - duplicate-create rejection for the same task
  - per-user isolation
  - stable response shape

## Out of Scope

- No artifact inventory or artifact metadata table yet.
- No document ingestion.
- No chunking, embeddings, or document retrieval.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No new proxy handlers or broader side-effect expansion.

## Required Deliverables

- Migration for `task_workspaces`.
- Stable workspace create/list/detail contracts.
- Minimal deterministic task-workspace provisioning and persistence path.
- Unit and integration coverage for provisioning, path safety, duplicate protection, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can provision one user-scoped workspace for a visible task.
- Every workspace record stores a deterministic local path under the configured workspace root.
- Duplicate active workspace creation for the same task is rejected deterministically.
- Workspace list and detail reads are deterministic and user-scoped.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No artifact indexing, document ingestion, connector, runner, handler-expansion, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep the workspace seam narrow and boring.
- Provision only local workspace boundaries; do not invent remote storage abstractions in this sprint.
- Keep workspace paths deterministic, explicit, and rooted under one configured base directory.
- Reuse existing task ownership and isolation seams rather than creating a parallel authorization path.
- Do not add artifact scanning, file sync, or document parsing in the same sprint.

## Suggested Work Breakdown

1. Add `task_workspaces` schema and migration.
2. Define workspace create/list/detail contracts.
3. Implement deterministic workspace path generation rooted under the configured base directory.
4. Implement workspace create, list, and detail behavior with duplicate protection.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact workspace schema and contract changes introduced
- the configured workspace root and path-generation rule used
- exact commands run
- unit and integration test results
- one example workspace create response
- one example workspace detail response
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to task workspace records and provisioning
- workspace paths are deterministic, rooted safely, and user-scoped
- duplicate protection, ordering, and isolation are test-backed
- no hidden artifact indexing, document ingestion, connector, runner, handler-expansion, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can provision deterministic user-scoped task workspace records under a configured local workspace root, expose stable workspace reads, and verify the full path with Postgres-backed tests, while still deferring artifact handling, document ingestion, and connector work.
