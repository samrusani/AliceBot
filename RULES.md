# Rules

## Product / Scope Rules

- The active sprint packet is the top priority scope boundary for implementation work and overrides broader roadmap intent when they conflict.
- Never represent planned architecture as implemented behavior in docs, handoffs, or build reports.
- Never execute a consequential external action without explicit user approval.
- Always treat explainability as a product feature, not an internal debugging aid.
- Treat the repeat magnesium reorder as the v1 ship-gate scenario.
- Never expand v1 scope with proactive automation, write-capable connectors, voice, or browser automation without an explicit roadmap change.
- Do not start runner, workspace/artifact, document-ingestion, or connector work unless the active sprint explicitly opens that boundary.

## Architecture Rules

- Treat the immutable event store as ground truth; memories, tasks, and summaries are derived or governed views over durable records.
- Always compile context per invocation from durable sources.
- Keep prompt prefixes, tool schemas, and serialized context ordering deterministic.
- Treat Postgres as the v1 system of record unless measured constraints justify a platform split.
- Appended task steps must carry explicit lineage to a prior visible task step. Do not relink approvals or executions heuristically from broader task history.
- Manual continuation is the current multi-step boundary. Until the older first-step lifecycle helpers are removed or constrained, do not describe broader automatic multi-step orchestration as implemented.

## Coding Rules

- Always build against typed contracts and migration-backed schemas first.
- Never mutate tool schemas mid-session; enforce access through policy and proxy layers.
- Keep changes small, module-scoped, and test-backed.
- Stop long-running tasks with a clear progress summary when budgets or circuit breakers trip.
- Sprint-scoped docs must clearly separate what exists now from what is only planned later.

## Data / Schema Rules

- Enforce row-level security on every user-owned table from the start.
- Default memory admission to `NOOP`; promote only evidence-backed changes.
- Always keep memory revision history for non-`NOOP` changes.
- Task-step lineage references must stay inside the current user scope and must validate against the intended parent step and its recorded outcome.
- Apply domain and sensitivity filters before semantic retrieval.

## Deployment / Ops Rules

- Keep v1 operations simple: one modular monolith, one primary database, one cache, one object store.
- Never store secrets in source control, committed config, or logs.
- Any repo-advertised bootstrap script that starts dependencies and then runs dependent commands must wait for service readiness before proceeding.
- When external side effects are introduced, route them through approval-aware tool execution paths.
- Backups and object versioning are required before production use.

## Testing Rules

- Schema changes are not complete without forward and rollback coverage.
- Every module needs unit tests and at least one integration boundary test.
- Approval boundaries, RLS isolation, and audit logging require adversarial tests.
- Lineage changes require adversarial tests for cross-task, cross-user, and parent-step mismatch cases.
- Memory quality and retrieval quality need labeled evaluations before release claims.
