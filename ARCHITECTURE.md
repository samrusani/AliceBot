# Architecture

## Current Implemented Slice

AliceBot now implements the accepted repo slice through Sprint 6K.

- `apps/api` is the core shipped surface. It provides continuity storage and review over `users`, `threads`, `sessions`, and append-only `events`; deterministic context compilation; governed memory admission and review; embeddings and semantic retrieval; entities and entity edges; policy, tool, approval, and execution governance; the no-tools assistant-response seam at `POST /v0/responses`; explicit task and task-step lifecycle reads and mutations; rooted local task workspaces and artifact ingestion; artifact chunk retrieval and embeddings; and the narrow read-only Gmail seam with external-secret-backed credentials plus selected-message ingestion into the RFC822 artifact pipeline.
- `apps/web` is a shipped operator shell over those backend seams, not a scaffold-only placeholder. The current routes are `/`, `/chat`, `/approvals`, `/tasks`, and `/traces`. The shell can read live backend seams when configured and otherwise falls back to explicit fixture states instead of pretending the backend is connected.
- `/chat` now carries both shipped operator modes: governed request composition and assistant-response mode. It uses visible thread selection instead of a raw typed thread id, supports compact thread creation through the continuity API, renders a selected-thread transcript from immutable continuity events, and keeps supporting session and operational review bounded in the right rail.
- `workers` remains scaffold-only. No background runner, automatic multi-step progression, or asynchronous job system is implemented.

The repo is intentionally still narrow. Document ingestion remains local and deterministic. The only live execution handler is the no-external-I/O `proxy.echo` path. Gmail remains read-only and selected-message-only. Rich parsing, mailbox sync, attachments, Calendar, broader proxying, and runner-style orchestration are still planned later.

## Implemented Now

### Runtime

- `docker-compose.yml` starts local Postgres with `pgvector`, Redis, and MinIO.
- `scripts/dev_up.sh`, `scripts/migrate.sh`, and `scripts/api_dev.sh` provide the local startup path.
- `apps/api` exposes FastAPI endpoints for:
  - continuity and response generation: `/healthz`, `POST /v0/threads`, `GET /v0/threads`, `GET /v0/threads/{thread_id}`, `GET /v0/threads/{thread_id}/sessions`, `GET /v0/threads/{thread_id}/events`, `POST /v0/context/compile`, `POST /v0/responses`
  - memory, embeddings, and graph seams
  - policy, tool, approval, execution-budget, and proxy execution governance
  - task, task-step, task-workspace, task-artifact, artifact-chunk, and trace review reads and mutations
  - narrow Gmail account connect/read plus selected-message ingestion
- `apps/web` exposes the current operator shell:
  - `/`: bounded home view over the shipped shell surfaces
  - `/chat`: assistant mode, governed request mode, thread selection, thread creation, transcript-first continuity review, and bounded supporting operational review
  - `/approvals`: approval inbox and execution review
  - `/tasks`: task summary and ordered task-step review
  - `/traces`: trace summary, detail, and ordered event review
- `tests` cover both the backend seams and the web shell. Durable repo evidence includes integration coverage for continuity and responses plus Vitest coverage for `/chat`, thread selection, bounded continuity review, and assistant-response submission.

### Data And Safety Boundaries

- Postgres is the system of record.
- Row-level security is enforced on user-owned continuity, trace, memory, governance, task, workspace, artifact, and Gmail tables.
- `events`, `trace_events`, and `memory_revisions` are append-only by contract.
- Task-step lineage and execution linkage stay explicit through `parent_step_id`, `source_approval_id`, `source_execution_id`, and `tool_executions.task_step_id`.
- Task workspaces are rooted local directories under `TASK_WORKSPACE_ROOT`.
- Task artifacts are explicit rooted local-file registrations only; compile and retrieval read persisted chunk rows, not raw files.
- Gmail credential material stays off normal metadata tables and flows through the dedicated secret-manager seam.

## Core Flows Implemented Now

### Continuity And Chat

1. `POST /v0/threads` creates one visible thread.
2. `GET /v0/threads`, `GET /v0/threads/{thread_id}`, `GET /v0/threads/{thread_id}/sessions`, and `GET /v0/threads/{thread_id}/events` expose bounded continuity review over persisted records.
3. `POST /v0/responses` compiles context deterministically, persists the submitted user message plus the assistant reply as immutable events, and returns linked compile and response trace metadata.
4. `/chat` consumes those shipped seams directly. Selected-thread identity stays explicit across assistant and governed-request modes, immutable thread events drive the primary transcript surface, and non-conversation continuity stays in bounded supporting review instead of polluting the main conversation record.

### Governance, Tasks, And Explainability

1. `POST /v0/approvals/requests` creates one task and one initial task step for each governed request.
2. Approval resolution and approved execution reuse explicit task-step linkage instead of inferring from first-step-only assumptions.
3. `GET /v0/approvals`, `GET /v0/tasks`, `GET /v0/tasks/{task_id}/steps`, `GET /v0/traces`, and related detail reads expose durable review state through the web shell.
4. The shipped explainability surface is calm and bounded: summary first, detail second, ordered trace events last.

### Workspaces, Artifacts, And Gmail

1. Tasks can provision one rooted local workspace and register local artifacts under that boundary.
2. Artifact ingestion supports the narrow current set only: plain text, markdown, narrow local PDF text extraction, narrow DOCX text extraction from `word/document.xml`, and narrow RFC822 email extraction.
3. Artifact retrieval works over persisted chunk rows and persisted chunk embeddings, including deterministic lexical retrieval, direct semantic retrieval, and the current lexical-first hybrid compile merge.
4. Gmail remains narrow: one read-only account seam, secret-free account reads, external-secret-backed primary credentials, refresh-token renewal and rotation handling, and one selected-message ingestion path that lands in the existing RFC822 artifact workflow.

## Testing Coverage Implemented Now

- Backend continuity and response seams are covered in `tests/integration/test_continuity_api.py`, `tests/integration/test_continuity_store.py`, `tests/integration/test_responses_api.py`, and related unit coverage under `tests/unit`.
- Web continuity adoption is covered in `apps/web/app/chat/page.test.tsx`, `apps/web/components/thread-list.test.tsx`, `apps/web/components/thread-summary.test.tsx`, `apps/web/components/thread-event-list.test.tsx`, `apps/web/components/thread-create.test.tsx`, and `apps/web/components/response-composer.test.tsx`.
- The shell also has route and API-client coverage for approvals, tasks, traces, and shared API utilities under `apps/web`.

## Planned Later

The following remain planned later and must not be described as implemented:

- runner-style orchestration and automatic multi-step progression
- auth beyond the current database user-context model
- richer document parsing, OCR, image extraction, or layout reconstruction
- Gmail search, mailbox sync, attachment ingestion, write-capable Gmail actions, and Calendar connectors
- broader proxy execution breadth or real-world side effects beyond `proxy.echo`
- retrieval reranking or weighted fusion beyond the current lexical-first hybrid compile merge

Future planning should start from the shipped API-plus-web-shell baseline above, not from older Gmail-era or scaffold-era descriptions.
