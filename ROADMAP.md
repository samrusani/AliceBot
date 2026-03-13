# Roadmap

## Current State

- The repo has shipped the implementation slices originally planned as Milestones 1 through 4.
- Sprint 4O added the latest accepted backend seam: durable `tasks` and `task_steps` with explicit manual continuation lineage and deterministic task-step transitions.
- The project is no longer at Foundation. The current repo state is a post-Milestone-4 checkpoint, and this sprint is synchronizing project-truth docs before Milestone 5 work begins.
- No task runner, workspace/artifact layer, document ingestion, read-only connector, or broader side-effect surface has landed yet.

## Completed Milestones

### Milestone 1: Foundation

- Repo scaffold, local Docker Compose infra, FastAPI app shell, config loading, migration tooling, and backend test harness.
- Postgres continuity primitives: `users`, `threads`, `sessions`, and append-only `events`.
- Row-level-security foundation and concurrent event sequencing hardening.

Status on March 13, 2026:
- Complete.

### Milestone 2: Context Compiler and Tracing

- Deterministic context compilation over durable continuity records.
- Persisted `traces` and append-only `trace_events`.
- Trace-visible inclusion and exclusion reasoning for compiled context.

Status on March 13, 2026:
- Complete.

### Milestone 3: Memory and Retrieval

- Governed memory admission with append-only revisions.
- Narrow deterministic explicit-preference extraction from stored user events.
- Memory review labels, review queue reads, and evaluation summary reads.
- Explicit entities and temporal entity edges backed by cited memories.
- Versioned embedding configs, durable memory embeddings, direct semantic retrieval, and deterministic hybrid compile-path memory merge.

Status on March 13, 2026:
- Complete.

### Milestone 4: Governance and Safe Action

- Deterministic response generation over compiled context.
- User-scoped consents, policies, policy evaluation, tool registry, allowlist evaluation, and tool routing.
- Durable approval requests and explicit approval resolution.
- Approved-only proxy execution through the in-process `proxy.echo` handler.
- Durable execution review, execution-budget enforcement, lifecycle mutations, and optional rolling-window limits.
- Durable `tasks` and `task_steps`, deterministic task-step reads, explicit task-step transitions, and explicit manual continuation with lineage.

Status on March 13, 2026:
- Complete through Sprint 4O.

## Current Milestone Position

- The repo is at the boundary after Milestone 4.
- Milestone 5 has not started in shipped code yet.
- The immediate work is documentation synchronization and narrow lifecycle-boundary hardening so Milestone 5 planning and review start from truthful artifacts.

## Next Milestones

### Immediate Next Narrow Boundary

- Preserve the current manual-continuation seam as the only shipped multi-step task path.
- Remove or explicitly constrain the remaining approval/execution helpers that still synchronize against `task_steps.sequence_no = 1` before starting runner-style orchestration or workspace-heavy task flows.

### Milestone 5: Documents, Workspaces, and Read-Only Connectors

- Add document ingestion and chunk retrieval.
- Add scoped task workspaces and artifact handling.
- Add read-only Gmail and Calendar sync.
- Keep connector scope read-only and approval-aware.

### Sequencing After Milestone 5

- Generalize task lifecycle handling beyond the current manual continuation seam.
- Introduce runner-style orchestration only after the first-step lifecycle assumption is removed.
- Expand tool execution breadth only after the governance and task seams stay deterministic under multi-step flows.

## Dependencies

- Truth artifacts must stay synchronized before milestone planning and review work can be trusted.
- The current first-step lifecycle assumption must be resolved before broader runner or workspace work can safely depend on `tasks` / `task_steps`.
- Scoped workspace and artifact boundaries should land before document-heavy or connector-heavy flows rely on them.
- Connector scope should remain deferred until the core memory, governance, and task seams stay stable under the shipped workload.

## Blockers and Risks

- Memory extraction and retrieval quality remain the biggest product risk.
- Auth beyond DB user context is still unimplemented.
- The remaining first-step approval/execution synchronization helpers are a forward-compatibility risk for broader multi-step orchestration.
- Workspace or connector work could create hidden scope drift if it starts before the current task-lifecycle boundary is hardened.

## Recently Completed

- Durable approval, execution review, and execution-budget seams over the approved proxy path.
- Durable `tasks` and `task_steps` with deterministic reads and status transitions.
- Explicit task-step lineage and manual continuation, including adversarial validation for cross-task, cross-user, and parent-step mismatch cases.
