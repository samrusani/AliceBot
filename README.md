# AliceBot

AliceBot is a private, permissioned personal AI operating system. The repository now includes the runnable foundation slice plus the first tracing/context-compilation seam, the first governed memory/admissions-and-embeddings slice, the first deterministic response-generation seam, the first governance routing seam for non-executing tool requests, the first durable approval-request persistence seam for `approval_required` routing outcomes, the explicit approval-resolution seam, the first minimal approved-only proxy-execution seam, the first durable execution-review seam over that proxy path, the narrow execution-budget lifecycle seam over approved proxy execution, and the first deterministic task-workspace provisioning seam: local infrastructure, an API scaffold, migration tooling, continuity primitives, persisted traces, a deterministic continuity-only compiler, explicit memory admission, a narrow deterministic explicit-preference extraction path, explicit embedding-config and memory-embedding storage paths, a direct semantic memory retrieval primitive, deterministic hybrid compile-path memory merge, a no-tools model invocation path over deterministically assembled prompts, deterministic policy and tool-governance seams, a narrow no-side-effect proxy handler path, durable `tool_executions` records, durable `execution_budgets` records, durable `task_workspaces` records, execution-budget create/list/detail reads, budget deactivate/supersede lifecycle operations, active-only budget enforcement, budget-blocked execution persistence, task-workspace create/list/detail reads, and backend verification coverage.

## Status

- Local Docker Compose infrastructure is defined for Postgres with `pgvector`, Redis, and MinIO.
- `apps/api` contains FastAPI health, compile, response-generation, memory-admission, explicit-preference extraction, semantic-memory-retrieval, policy, tool-registry, tool-allowlist, tool-routing, approval-request, approval-resolution, proxy-execution, execution-budget, execution-review, task, and task-workspace endpoints, configuration loading, Alembic migrations, continuity storage primitives, the Sprint 2A trace/compiler path, the Sprint 3A memory-admission path, the Sprint 3I deterministic extraction path, the Sprint 3K embedding substrate, the Sprint 3L semantic retrieval primitive, the Sprint 3M compile-path semantic retrieval adoption, the Sprint 3N deterministic hybrid memory merge, the Sprint 4A deterministic prompt-assembly and no-tools response path, the Sprint 4D deterministic non-executing tool-routing seam, the Sprint 4E durable approval-request persistence seam, the Sprint 4F approval-resolution seam, the Sprint 4G minimal approved-only proxy-execution seam, the Sprint 4H durable execution-review seam, the Sprint 4I execution-budget guard seam, the Sprint 4J execution-budget lifecycle seam, the Sprint 4K time-windowed execution-budget seam, the Sprint 4S explicit execution-to-task-step linkage seam, and the Sprint 5A task-workspace provisioning seam.
- `apps/web` and `workers` contain minimal starter scaffolds for later milestone work.
- The active sprint is documented in [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md).

## Quick Start

1. Create a local env file: `cp .env.example .env`
2. Start required infrastructure with one command: `docker compose up -d`
3. Create a project virtualenv and install Python dependencies: `python3 -m venv .venv && ./.venv/bin/python -m pip install -e '.[dev]'`
4. Run database migrations: `./scripts/migrate.sh`
5. Start the API locally: `./scripts/api_dev.sh`

The health endpoint is exposed at [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz).
The minimal context-compilation API path is `POST /v0/context/compile`.
The minimal response-generation API path is `POST /v0/responses`.
The minimal memory-admission API path is `POST /v0/memories/admit`.
The explicit-preference extraction API path is `POST /v0/memories/extract-explicit-preferences`.
The minimal non-executing tool-routing API path is `POST /v0/tools/route`.
The minimal approval API paths are `POST /v0/approvals/requests`, `GET /v0/approvals`, `GET /v0/approvals/{approval_id}`, `POST /v0/approvals/{approval_id}/approve`, `POST /v0/approvals/{approval_id}/reject`, and `POST /v0/approvals/{approval_id}/execute`.
The execution-budget API paths are `POST /v0/execution-budgets`, `GET /v0/execution-budgets`, `GET /v0/execution-budgets/{execution_budget_id}`, `POST /v0/execution-budgets/{execution_budget_id}/deactivate`, and `POST /v0/execution-budgets/{execution_budget_id}/supersede`.
The execution-review API paths are `GET /v0/tool-executions` and `GET /v0/tool-executions/{execution_id}`.
The task-workspace API paths are `POST /v0/tasks/{task_id}/workspace`, `GET /v0/task-workspaces`, and `GET /v0/task-workspaces/{task_workspace_id}`.
The helper scripts load the repo-root `.env` automatically and prefer `.venv/bin/python` when that virtualenv exists, falling back to `python3` otherwise. The default migration/admin URL targets the same local `alicebot` database as the app runtime.
`/healthz` currently performs a live Postgres check only. Redis and MinIO are reported as configured endpoints with `not_checked` status.
`TASK_WORKSPACE_ROOT` controls the single rooted base directory used for deterministic local task-workspace provisioning. By default it is `/tmp/alicebot/task-workspaces`, and each workspace path is created as `<TASK_WORKSPACE_ROOT>/<user_id>/<task_id>`.
The current backend path has been verified in a local developer environment with `docker compose up -d`, `./scripts/migrate.sh`, `./.venv/bin/python -m pytest tests/unit tests/integration`, a live `GET /healthz`, and the Postgres-backed `POST /v0/context/compile`, `POST /v0/responses`, `POST /v0/memories/admit`, `POST /v0/memories/extract-explicit-preferences`, `POST /v0/memories/semantic-retrieval`, `POST /v0/tools/allowlist/evaluate`, `POST /v0/tools/route`, `POST /v0/approvals/requests`, `POST /v0/approvals/{approval_id}/execute`, `POST /v0/execution-budgets`, `GET /v0/execution-budgets`, `POST /v0/execution-budgets/{execution_budget_id}/deactivate`, `POST /v0/execution-budgets/{execution_budget_id}/supersede`, `GET /v0/tool-executions`, and `GET /v0/tool-executions/{execution_id}` integration paths, including compile requests that explicitly enable the hybrid memory merge, response requests that persist assistant events and response traces, deterministic non-executing tool-routing requests that persist `tool.route.*` traces, approval-request persistence requests that persist `approval.request.*` traces plus durable approval rows only for `approval_required` outcomes, approved proxy execution that persists `tool.proxy.execute.*` traces plus durable `tool_executions` rows for approved execution attempts, deterministic budget-management requests over durable `execution_budgets` rows, lifecycle requests that persist `execution_budget.lifecycle.*` traces and change budget status deterministically, budget-prechecked proxy execution that emits `tool.proxy.execute.budget` trace events against active budgets only, and execution-review reads over those durable records including budget-blocked attempts.

## Repo Structure

- [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md): permanent product truth.
- [ARCHITECTURE.md](ARCHITECTURE.md): permanent technical truth.
- [ROADMAP.md](ROADMAP.md): milestone sequence and delivery risks.
- [RULES.md](RULES.md): durable engineering and scope rules.
- [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md): fresh-thread recovery snapshot.
- [.ai/active/SPRINT_PACKET.md](.ai/active/SPRINT_PACKET.md): current builder sprint.
- `docker-compose.yml`: local Postgres, Redis, and MinIO stack.
- `infra/postgres/init/`: Postgres bootstrap SQL, including the non-superuser app role.
- `apps/api/`: FastAPI app, config, continuity store, and Alembic migrations.
- `apps/web/`: minimal Next.js shell for later dashboard work.
- `workers/`: placeholder Python worker package for future background jobs.
- `tests/`: unit and Postgres-backed integration tests for the foundation slice.
- `scripts/`: local development and migration entrypoints.

## Essential Commands

- `docker compose up -d`: start Postgres, Redis, and MinIO on `127.0.0.1`.
- `./scripts/dev_up.sh`: start local infrastructure, wait for Postgres and role bootstrap readiness, and apply Alembic migrations.
- `./scripts/migrate.sh`: apply Alembic migrations with the admin database URL from `.env` or the built-in defaults.
- `./scripts/api_dev.sh`: run the FastAPI service with auto-reload.
- `./.venv/bin/python -m pytest tests/unit tests/integration`: run backend tests from the project virtualenv.
- `pnpm --dir apps/web dev`: start the web shell after frontend dependencies are installed.

## Environment Notes

- Postgres is the system of record and the live schema now includes continuity tables, trace tables, policy-governance tables including `approvals`, `tool_executions`, and `execution_budgets`, task lifecycle tables including `tasks`, `task_steps`, and `task_workspaces`, memory tables, entity tables, and the embedding substrate tables `embedding_configs` and `memory_embeddings`.
- Sprint 2A adds persisted `traces` and `trace_events` plus a deterministic continuity-only context compiler over existing durable continuity records.
- Sprint 3A adds governed `memories` and append-only `memory_revisions` plus an explicit `NOOP`-first admission path over cited source events.
- The app and migration defaults both target the local `alicebot` database to keep quick-start behavior deterministic.
- `TASK_WORKSPACE_ROOT` defaults to `/tmp/alicebot/task-workspaces` and defines the only allowed root for deterministic local task-workspace provisioning.
- Local service ports are bound to `127.0.0.1` by default to avoid exposing fixed development credentials on non-loopback interfaces.
- Redis is reserved for future queue, lock, and cache work; no retrieval or orchestration features are enabled in this sprint.
- MinIO provides the local S3-compatible endpoint for future document and artifact storage.
- Continuity tables enforce row-level security from the start and `events` are append-only by application contract plus database trigger, with concurrent appends serialized per thread.
- Trace tables follow the same per-user isolation model, with append-only `trace_events` for compiler explainability.
- Memory admission remains explicit and evidence-backed, automatic extraction is currently limited to a narrow deterministic explicit-preference path over stored user messages, and the repo now includes explicit versioned embedding-config storage, direct memory-embedding persistence, a direct semantic retrieval API over active durable memories, compile-path hybrid memory merge into one `context_pack["memories"]` section with `memory_summary.hybrid_retrieval` metadata, one deterministic no-tools response path that assembles prompts from durable compiled context and persists assistant replies plus response traces, one deterministic approval-request persistence path over `approval_required` tool-routing outcomes, explicit approval resolution, one minimal approved-only proxy execution path through the no-side-effect `proxy.echo` handler, durable execution-review records plus list/detail reads for approved execution attempts, one narrow deterministic execution-budget seam that can activate, deactivate, supersede, and enforce both lifetime and rolling-window limits using durable `tool_executions` history while keeping blocked attempts reviewable, and one narrow deterministic task-workspace seam that provisions rooted local workspace directories and persists durable `task_workspaces` rows. Broader extraction, reranking, external-connector tool execution, artifact indexing, document ingestion, orchestration, and review UI remain deferred.
- The runtime database role is limited to `SELECT`/`INSERT` on continuity and trace tables, `SELECT`/`INSERT` on `memory_revisions`, `memory_review_labels`, `embedding_configs`, `entities`, and `entity_edges`, plus `SELECT`/`INSERT`/`UPDATE` on `consents`, `memories`, `memory_embeddings`, and `execution_budgets`.
