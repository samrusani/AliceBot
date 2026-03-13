# Architecture

## Current Implemented Slice

AliceBot now implements the accepted repo slice through Sprint 5A. The shipped backend includes:

- foundation continuity storage over `users`, `threads`, `sessions`, and append-only `events`
- deterministic tracing and context compilation over durable continuity, memory, entity, and entity-edge records
- governed memory admission, explicit-preference extraction, memory review labels, review queue reads, evaluation summary reads, explicit embedding config and memory-embedding storage, direct semantic retrieval, and deterministic hybrid compile-path memory merge
- deterministic prompt assembly and one no-tools response path that persists assistant replies as immutable continuity events
- user-scoped consents, policies, policy evaluation, tool registry, allowlist evaluation, tool routing, approval request persistence, approval resolution, approved-only proxy execution through the in-process `proxy.echo` handler, durable execution review, and execution-budget lifecycle plus enforcement
- durable `tasks`, `task_steps`, and `task_workspaces`, deterministic task-step sequencing, explicit task-step transitions, explicit manual continuation with lineage through `parent_step_id`, `source_approval_id`, and `source_execution_id`, explicit `tool_executions.task_step_id` linkage for execution synchronization, and deterministic rooted local task-workspace provisioning

The current multi-step boundary is narrow and explicit. Manual continuation is implemented and review-passed. Approval resolution and proxy execution now both use explicit task-step linkage rather than first-step inference. Task workspaces are now implemented only as deterministic rooted local boundaries. Broader runner-style orchestration, automatic multi-step progression, artifact indexing, document ingestion, connectors, and new side-effect surfaces are still planned later and must not be described as live behavior.

## Implemented Now

### Runtime

- `docker-compose.yml` starts local Postgres with `pgvector`, Redis, and MinIO.
- `scripts/dev_up.sh`, `scripts/migrate.sh`, and `scripts/api_dev.sh` provide the local startup path, with readiness gating before migrations.
- `apps/api` exposes FastAPI endpoints for:
  - health and compile: `/healthz`, `POST /v0/context/compile`, `POST /v0/responses`
  - memory and retrieval: `POST /v0/memories/admit`, `POST /v0/memories/extract-explicit-preferences`, `GET /v0/memories`, `GET /v0/memories/review-queue`, `GET /v0/memories/evaluation-summary`, `POST /v0/memories/semantic-retrieval`, `GET /v0/memories/{memory_id}`, `GET /v0/memories/{memory_id}/revisions`, `POST /v0/memories/{memory_id}/labels`, `GET /v0/memories/{memory_id}/labels`
  - embeddings and graph seams: `POST /v0/embedding-configs`, `GET /v0/embedding-configs`, `POST /v0/memory-embeddings`, `GET /v0/memories/{memory_id}/embeddings`, `GET /v0/memory-embeddings/{memory_embedding_id}`, `POST /v0/entities`, `GET /v0/entities`, `GET /v0/entities/{entity_id}`, `POST /v0/entity-edges`, `GET /v0/entities/{entity_id}/edges`
  - governance: `POST /v0/consents`, `GET /v0/consents`, `POST /v0/policies`, `GET /v0/policies`, `GET /v0/policies/{policy_id}`, `POST /v0/policies/evaluate`, `POST /v0/tools`, `GET /v0/tools`, `GET /v0/tools/{tool_id}`, `POST /v0/tools/allowlist/evaluate`, `POST /v0/tools/route`, `POST /v0/approvals/requests`, `GET /v0/approvals`, `GET /v0/approvals/{approval_id}`, `POST /v0/approvals/{approval_id}/approve`, `POST /v0/approvals/{approval_id}/reject`, `POST /v0/approvals/{approval_id}/execute`
  - task and execution review: `GET /v0/tasks`, `GET /v0/tasks/{task_id}`, `POST /v0/tasks/{task_id}/workspace`, `GET /v0/task-workspaces`, `GET /v0/task-workspaces/{task_workspace_id}`, `GET /v0/tasks/{task_id}/steps`, `GET /v0/task-steps/{task_step_id}`, `POST /v0/tasks/{task_id}/steps`, `POST /v0/task-steps/{task_step_id}/transition`, `POST /v0/execution-budgets`, `GET /v0/execution-budgets`, `GET /v0/execution-budgets/{execution_budget_id}`, `POST /v0/execution-budgets/{execution_budget_id}/deactivate`, `POST /v0/execution-budgets/{execution_budget_id}/supersede`, `GET /v0/tool-executions`, `GET /v0/tool-executions/{execution_id}`
- `apps/web` and `workers` remain starter shells only.

### Data Foundation

- Postgres is the current system of record.
- Alembic manages schema changes through `apps/api/alembic`.
- The live schema includes:
  - continuity tables: `users`, `threads`, `sessions`, `events`
  - trace tables: `traces`, `trace_events`
  - memory and retrieval tables: `memories`, `memory_revisions`, `memory_review_labels`, `embedding_configs`, `memory_embeddings`
  - graph tables: `entities`, `entity_edges`
  - governance tables: `consents`, `policies`, `tools`, `approvals`, `tool_executions`, `execution_budgets`
  - task lifecycle tables: `tasks`, `task_steps`, `task_workspaces`
- `events`, `trace_events`, and `memory_revisions` are append-only by application contract and database enforcement.
- `memory_review_labels` are append-only by database enforcement.
- `tasks` are explicit user-scoped lifecycle records keyed to one thread and one tool, with durable request/tool snapshots, status in `pending_approval | approved | executed | denied | blocked`, and latest approval/execution pointers for the current narrow lifecycle seam.
- `task_steps` are explicit user-scoped ordered lifecycle records keyed by `(user_id, task_id, sequence_no)`, with `kind = 'governed_request'`, status in `created | approved | executed | blocked | denied`, durable request/outcome snapshots, and one trace reference describing the latest mutation.
- Sprint 4O added lineage columns on `task_steps`:
  - `parent_step_id`
  - `source_approval_id`
  - `source_execution_id`
- Lineage fields are guarded by composite user-scoped foreign keys and a self-reference check so a step cannot cite itself as its parent.
- `tool_executions` now persist an explicit `task_step_id` linked by a composite foreign key to `task_steps(id, user_id)`.
- `task_workspaces` persist one active workspace record per visible task and user, store a deterministic `local_path`, and enforce that active uniqueness through a partial unique index on `(user_id, task_id)`.
- `execution_budgets` enforce at most one active budget per `(user_id, tool_key, domain_hint)` selector scope through a partial unique index.
- Per-request user context is set in the database through `app.current_user_id()`.
- `TASK_WORKSPACE_ROOT` defines the only allowed base directory for workspace provisioning, and the live path rule is `resolved_root / user_id / task_id`.

### Repo Boundaries In This Slice

- `apps/api`: implemented API, store, contracts, service logic, and migrations for continuity, tracing, memory, embeddings, entities, policies, tools, approvals, proxy execution, execution budgets, tasks, task steps, and task workspaces.
- `apps/web`: minimal shell only; no shipped workflow UI.
- `workers`: scaffold only; no background jobs or runner logic are implemented.
- `infra`: local development bootstrap assets only.
- `tests`: unit and Postgres-backed integration coverage for the shipped seams above, including Sprint 4O task-step lineage/manual continuation, Sprint 4S step-linked execution synchronization, and Sprint 5A task-workspace provisioning.

## Core Flows Implemented Now

### Deterministic Context Compilation

1. Accept a user-scoped `POST /v0/context/compile` request.
2. Read durable continuity records in deterministic order.
3. Merge in active memories, entities, and entity edges through the currently shipped symbolic and optional semantic retrieval paths.
4. Persist a `context.compile` trace plus explicit inclusion and exclusion events.
5. Return one deterministic `context_pack` describing scope, limits, selected context, and trace metadata.

### Governed Memory And Retrieval

1. Accept explicit memory candidates through `POST /v0/memories/admit`.
2. Require cited source events, default to `NOOP`, and persist `memory_revisions` only for evidence-backed non-`NOOP` mutations.
3. Support a narrow deterministic explicit-preference extractor over stored `message.user` events.
4. Persist user-scoped embedding configs and memory embeddings explicitly.
5. Support direct semantic retrieval over active memories for a caller-selected embedding config.
6. Merge symbolic and semantic memory results deterministically into the compile path with trace-visible source provenance.
7. Expose review reads, unlabeled review queue reads, evaluation summary reads, and append-only memory-review labels.

### Policy, Tool, Approval, And Execution Governance

1. Evaluate policies deterministically over active user-scoped policy and consent state.
2. Evaluate tool allowlists against active tool metadata plus policy decisions.
3. Route one requested invocation deterministically to `ready`, `denied`, or `approval_required`.
4. Persist durable approval rows only for `approval_required` outcomes.
5. Resolve approvals explicitly through approve and reject endpoints.
6. Execute approved requests only through the registered proxy-handler map.
7. In the current repo, only `proxy.echo` is enabled, and it performs no external I/O.
8. Persist one durable `tool_executions` row for every approved execution attempt, including budget-blocked attempts.
9. Enforce narrow execution budgets by selector scope and optional rolling window before approved dispatch.

### Task Lifecycle Creation

1. `POST /v0/approvals/requests` always creates one durable `tasks` row and one initial `task_steps` row, even when no approval row is persisted.
2. The initial task and task step reflect the routing decision:
  - `approval_required` creates `task.status = pending_approval` and `task_step.status = created`
  - `ready` creates `task.status = approved` and `task_step.status = approved`
  - `denied` creates `task.status = denied` and `task_step.status = denied`
3. The initial task step is always `sequence_no = 1`.
4. Approval-request traces include task lifecycle and task-step lifecycle events alongside the approval request events.

### Approval Resolution And Proxy Execution Synchronization

1. Approval resolution reuses the existing task seam and updates the durable task plus the explicitly linked task step from `approvals.task_step_id`.
2. Approval resolution rejects missing, invisible, cross-task, and inconsistent approval-to-step linkage deterministically.
3. Approved proxy execution validates the approval’s linked task step before dispatch and persists `tool_executions.task_step_id` on every durable execution row.
4. Execution synchronization now reuses `tool_executions.task_step_id` and updates the explicitly linked step by id rather than inferring `sequence_no = 1`.
5. Execution synchronization rejects missing, invisible, cross-task, and inconsistent execution-to-step linkage deterministically before mutating task or task-step state.

### Task-Step Manual Continuation

1. Accept a user-scoped `POST /v0/tasks/{task_id}/steps` request to append exactly one next step to an existing task.
2. Lock the task-step sequence before allocating the next `sequence_no`.
3. Require the task to already have visible steps.
4. Allow append only when the latest visible step is in `executed`, `blocked`, or `denied`.
5. Require explicit lineage:
  - `lineage.parent_step_id` must be present
  - the parent step must belong to the same visible task
  - the parent step must be the latest visible task step
6. Optionally allow `lineage.source_approval_id` and `lineage.source_execution_id`, but only when:
  - the referenced records are visible in the current user scope
  - the referenced records already appear on the parent step outcome
7. Persist the new `task_steps` row with the lineage fields and incremented `sequence_no`.
8. Update the parent `tasks` row to the task status implied by the appended step status.
9. Persist one `task.step.continuation` trace plus request, lineage, summary, task lifecycle, and task-step lifecycle events.
10. Return the updated task, the appended step, deterministic sequencing metadata, and trace summary.

### Task-Step Transition

1. Accept a user-scoped `POST /v0/task-steps/{task_step_id}/transition` request.
2. Require the referenced step to be the latest visible step on its task.
3. Enforce the explicit status graph:
  - `created -> approved | denied`
  - `approved -> executed | blocked`
  - terminal states have no further transitions
4. Require approval linkage when the step must reflect approval state and execution linkage when the step must reflect execution state.
5. Update the target step in place with a new trace reference and outcome snapshot.
6. Update the parent task status and latest approval/execution pointers consistently.
7. Persist one `task.step.transition` trace plus request, state, summary, task lifecycle, and task-step lifecycle events.

### Task And Task-Step Reads

1. `GET /v0/tasks` lists durable task rows in deterministic `created_at ASC, id ASC` order.
2. `GET /v0/tasks/{task_id}` returns one user-visible task detail record.
3. `GET /v0/tasks/{task_id}/steps` returns task steps in deterministic `sequence_no ASC, created_at ASC, id ASC` order plus sequencing summary metadata.
4. `GET /v0/task-steps/{task_step_id}` returns one user-visible task-step detail record.
5. Task-step list and detail reads expose lineage fields directly.

### Task Workspace Provisioning

1. Accept a user-scoped `POST /v0/tasks/{task_id}/workspace` request for one visible task.
2. Resolve the configured `TASK_WORKSPACE_ROOT`.
3. Build the deterministic local path as `resolved_root / user_id / task_id`.
4. Reject provisioning if the resolved workspace path escapes the resolved workspace root.
5. Lock workspace creation for the target task before checking for an existing active workspace.
6. Reject duplicate active workspace creation for the same visible task deterministically.
7. Create the local directory boundary and persist one `task_workspaces` row with `status = active` and the rooted `local_path`.
8. `GET /v0/task-workspaces` lists visible workspaces in deterministic `created_at ASC, id ASC` order.
9. `GET /v0/task-workspaces/{task_workspace_id}` returns one user-visible workspace detail record.

## Security Model Implemented Now

- User-owned continuity, trace, memory, embedding, entity, governance, task, task-step, and task-workspace tables enforce row-level security.
- The runtime role is limited to the narrow `SELECT` / `INSERT` / `UPDATE` permissions required by the shipped seams; there is no broad DDL or unrestricted table access at runtime.
- Cross-user references are constrained through composite foreign keys on `(id, user_id)` where the schema needs ownership-linked joins.
- Approval, execution, memory, entity, task/task-step, and task-workspace reads all operate only inside the current user scope.
- Task-step manual continuation adds both schema-level and service-level lineage protection:
  - schema-level: user-scoped foreign keys and parent-not-self check
  - service-level: same-task, latest-step, visible-approval, visible-execution, and parent-outcome-match validation
- In-place updates and deletes remain blocked for append-only continuity and trace records.

## Testing Coverage Implemented Now

- Unit and integration tests cover continuity, compiler, response generation, memory admission, review labels, review queue, embeddings, semantic retrieval, entities, policies, tools, approvals, proxy execution, execution budgets, and execution review.
- Sprint 4O, Sprint 4S, and Sprint 5A added explicit task lifecycle coverage:
  - migrations for `tasks`, `task_steps`, and task-step lineage
  - staged/backfilled migration coverage for `tool_executions.task_step_id`
  - task and task-step store contracts
  - task list/detail and task-step list/detail reads
  - deterministic sequencing summaries
  - manual continuation success paths
  - task-step transition success paths
  - explicit later-step execution synchronization by linked `task_step_id`
  - deterministic task-workspace path generation and rooted-path enforcement
  - workspace create/list/detail response shape
  - duplicate active workspace rejection
  - task-workspace per-user isolation
  - trace visibility for continuation and transition events
  - user isolation for task and task-step reads and mutations
  - adversarial lineage validation for cross-task, cross-user, and parent-step mismatch cases

## Planned Later

The following areas remain planned later and must not be described as implemented:

- runner-style orchestration and automatic multi-step progression beyond the current explicit manual continuation seam
- artifact storage, artifact indexing, and document ingestion beyond the current rooted local workspace boundary
- read-only Gmail and Calendar connectors
- broader tool proxying and real-world side effects beyond the current no-I/O `proxy.echo` handler
- model-driven extraction, reranking, and broader memory review automation
- production deployment automation beyond the local developer stack

Future docs and code should continue to distinguish the implemented seams above from these later milestones.
