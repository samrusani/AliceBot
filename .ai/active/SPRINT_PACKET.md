# SPRINT_PACKET.md

## Sprint Title

Sprint 5C: Task Artifact Records and Registration

## Sprint Type

feature

## Sprint Reason

Milestone 5 should continue on top of the shipped task-workspace boundary. Before document ingestion or connectors can safely rely on workspaces, the repo needs explicit, reviewable artifact records tied to those workspaces instead of ad hoc filesystem assumptions.

## Sprint Intent

Add durable task-artifact records plus a narrow local artifact registration path on top of existing `task_workspaces`, so later document ingestion and retrieval can consume explicit artifact metadata instead of raw workspace scanning.

## Git Instructions

- Branch Name: `codex/sprint-5c-task-artifacts`
- Base Branch: `main`
- PR Strategy: one sprint branch, one PR, no stacked PRs unless Control Tower explicitly opens a follow-up sprint
- Merge Policy: squash merge only after reviewer `PASS` and explicit Control Tower merge approval

## Why This Sprint

- Sprint 5A shipped deterministic rooted task-workspace provisioning.
- Sprint 5B cleaned and synchronized live project truth, so Milestone 5 planning can proceed from current facts.
- The roadmap says artifact and workspace boundaries should be explicit before document-heavy work lands.
- The narrowest next step is artifact records and registration only, not ingestion, chunking, connectors, or UI.

## In Scope

- Add schema and migration support for:
  - `task_artifacts`
- Define typed contracts for:
  - artifact registration requests
  - artifact create responses
  - artifact list responses
  - artifact detail responses
- Implement a narrow artifact seam that:
  - registers one local file path under an existing visible task workspace
  - persists one user-scoped artifact record linked to that workspace and task
  - validates that the artifact path stays rooted under the workspace local path
  - stores explicit artifact metadata such as relative path, media type hint if supplied, and status fields needed for later ingestion
  - exposes deterministic list and detail reads
- Implement the minimal API or service paths needed for:
  - registering one artifact for a task workspace
  - listing artifacts
  - reading one artifact by id
- Add unit and integration tests for:
  - artifact registration
  - rooted path validation against the workspace boundary
  - duplicate registration behavior for the same workspace-relative path
  - per-user isolation
  - stable response shape

## Out of Scope

- No document ingestion.
- No chunking, embeddings, or document retrieval.
- No background scanning of workspace directories.
- No Gmail or Calendar connector scope.
- No runner-style orchestration.
- No new proxy handlers or broader side-effect expansion.
- No UI work.

## Required Deliverables

- Migration for `task_artifacts`.
- Stable artifact register/list/detail contracts.
- Minimal deterministic artifact-registration and persistence path over existing task workspaces.
- Unit and integration coverage for rooted-path safety, duplicate handling, ordering, and isolation.
- Updated `BUILD_REPORT.md` with exact verification results and explicit deferred scope.

## Acceptance Criteria

- A client can register one artifact under an existing visible task workspace.
- Every artifact record stores a workspace-relative path and remains rooted under the persisted workspace local path.
- Duplicate registration behavior for the same workspace-relative path is deterministic and documented.
- Artifact list and detail reads are deterministic and user-scoped.
- `./.venv/bin/python -m pytest tests/unit` passes.
- `./.venv/bin/python -m pytest tests/integration` passes.
- No document ingestion, connector, runner, handler-expansion, or broader side-effect scope enters the sprint.

## Implementation Constraints

- Keep the artifact seam narrow and boring.
- Reuse the existing `task_workspaces` boundary; do not invent a parallel storage contract.
- Prefer explicit artifact registration over implicit directory scanning in this sprint.
- Keep rooted-path validation deterministic and local-filesystem-only.
- Do not parse, chunk, embed, or retrieve artifact contents in the same sprint.

## Suggested Work Breakdown

1. Add `task_artifacts` schema and migration.
2. Define artifact register/list/detail contracts.
3. Implement deterministic rooted artifact-path validation against the persisted workspace path.
4. Implement artifact registration, list, and detail behavior.
5. Add unit and integration tests.
6. Update `BUILD_REPORT.md` with executed verification.

## Build Report Requirements

`BUILD_REPORT.md` must include:
- the exact artifact schema and contract changes introduced
- the artifact-path rooting and duplicate-handling rule used
- exact commands run
- unit and integration test results
- one example artifact registration response
- one example artifact detail response
- what remains intentionally deferred to later milestones

## Review Focus

`REVIEW_REPORT.md` should verify:
- the sprint stayed limited to task artifact records and registration
- artifact paths are deterministic, rooted safely under existing workspaces, and user-scoped
- duplicate handling, ordering, and isolation are test-backed
- no hidden document ingestion, connector, runner, UI, handler-expansion, or broader side-effect scope entered the sprint

## Exit Condition

This sprint is complete when the repo can persist deterministic user-scoped task-artifact records rooted under existing task workspaces, expose stable artifact reads, and verify the full path with Postgres-backed tests, while still deferring document ingestion, retrieval, and connector work.
